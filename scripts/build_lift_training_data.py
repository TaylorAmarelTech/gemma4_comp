#!/usr/bin/env python3
"""Phase 3 keystone -- distil the benchmark's harness-lift into vetted SFT + DPO training data.

Reads the live 0-100 benchmark grades (reports/rich_lift/panel.jsonl) and the raw responses
(reports/rich_lift/results.jsonl), finds prompts where the harness clearly fixed a baseline gap
(the harnessed reply scores high AND the baseline->harnessed lift is large), and emits
ready-to-train pairs that teach a model to produce the harnessed-quality answer on its own:

  * SFT  reports/training/sft.jsonl : {"messages": [user, {"role":"assistant", harnessed reply}]}
  * DPO  reports/training/dpo.jsonl : {"prompt", "chosen": harnessed reply, "rejected": baseline reply}

This is the data-vetting subsystem's first gate (see docs/phase3_training_framework.md). Each pair
must pass, before inclusion:
  * quality -- harnessed mean score >= --min-target
  * signal  -- (harnessed - baseline) mean lift >= --min-lift   (a clear teaching signal, not noise)
  * privacy -- a conservative PII / volatile-contact scrub (emails, phone-like, long digit runs), so
               targets teach the response SHAPE, not a specific (volatile) hotline number -- statute
               refs like "C181" or "RA 8042" are preserved.

Propose-only: writes to the gitignored reports/training/ store + a manifest; never trains, never
mutates the benchmark. Distinct from prepare_training_data.py (which converts the seed corpus's
manual worst->best grades); this distils the benchmark's *measured* harness-lift.

    python scripts/build_lift_training_data.py --min-target 70 --min-lift 20
Design: docs/phase3_training_framework.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
from collections import defaultdict
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
PANEL = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
RESULTS = _ROOT / "reports" / "rich_lift" / "results.jsonl"
OUT_DIR = _ROOT / "reports" / "training"
BASELINE_ARM = "baseline"
TARGET_ARM = "harness_full"

# Conservative PII / volatile-contact scrub. Targets emails, phone-like sequences, and long digit
# runs (passport / account / case ids) -- NOT statute refs like "C181" or "RA 8042" (no 7+ digit run).
_SCRUB = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[email]"),
    (re.compile(r"\+?\d[\d\s().\-]{8,}\d"), "[phone]"),
    (re.compile(r"\b\d{6,}\b"), "[id-number]"),
]


def _load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return out


def scrub(text: str) -> tuple[str, int]:
    """Replace emails / phone-like / long-digit runs with tags. Returns (clean_text, n_redactions)."""
    n = 0
    for pat, tag in _SCRUB:
        text, k = pat.subn(tag, text)
        n += k
    return text, n


def mean_scores(panel: list[dict]) -> dict[tuple[str, str, str], float]:
    """Mean 0-100 score per (model, prompt_id, arm) over the judge panel."""
    by: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for r in panel:
        try:
            by[(str(r["model"]), str(r["prompt_id"]), str(r["arm"]))].append(float(r["score_0_100"]))
        except (KeyError, TypeError, ValueError):
            continue
    return {k: round(statistics.mean(v), 1) for k, v in by.items() if v}


def responses(results: list[dict]) -> dict[tuple[str, str, str], dict[str, str]]:
    """{(model, prompt_id, arm): {response, prompt_text}} from the raw response log (last write wins)."""
    out: dict[tuple[str, str, str], dict[str, str]] = {}
    for r in results:
        try:
            out[(str(r["model"]), str(r["prompt_id"]), str(r["arm"]))] = {
                "response": str(r.get("response", "")),
                "prompt_text": str(r.get("prompt_text", "")),
            }
        except (KeyError, TypeError):
            continue
    return out


def build(*, min_target: float, min_lift: float,
          panel_path: pathlib.Path = PANEL, results_path: pathlib.Path = RESULTS) -> dict[str, Any]:
    """Select high-lift (baseline, harnessed) pairs and build vetted SFT + DPO records + a manifest."""
    score = mean_scores(_load_jsonl(panel_path))
    resp = responses(_load_jsonl(results_path))
    by_pair: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for (model, pid, arm), s in score.items():
        by_pair[(model, pid)][arm] = s

    sft: list[dict[str, Any]] = []
    dpo: list[dict[str, Any]] = []
    considered = selected = redactions = 0
    for (model, pid), arms in by_pair.items():
        if BASELINE_ARM not in arms or TARGET_ARM not in arms:
            continue
        considered += 1
        base_s, full_s = arms[BASELINE_ARM], arms[TARGET_ARM]
        lift = round(full_s - base_s, 1)
        if full_s < min_target or lift < min_lift:
            continue
        base_r = resp.get((model, pid, BASELINE_ARM))
        full_r = resp.get((model, pid, TARGET_ARM))
        if not base_r or not full_r or not full_r["response"].strip() or not base_r["response"].strip():
            continue
        prompt, k1 = scrub(full_r["prompt_text"] or base_r["prompt_text"])
        chosen, k2 = scrub(full_r["response"])
        rejected, k3 = scrub(base_r["response"])
        if not prompt.strip():
            continue
        redactions += k1 + k2 + k3
        selected += 1
        meta = {"model": model, "prompt_id": pid, "baseline_score": base_s,
                "target_score": full_s, "lift": lift}
        sft.append({"messages": [{"role": "user", "content": prompt},
                                 {"role": "assistant", "content": chosen}], "_meta": meta})
        dpo.append({"prompt": prompt, "chosen": chosen, "rejected": rejected, "_meta": meta})

    manifest = {
        "source": {"panel": str(panel_path), "results": str(results_path)},
        "arms": {"baseline": BASELINE_ARM, "target": TARGET_ARM},
        "thresholds": {"min_target": min_target, "min_lift": min_lift},
        "considered_pairs": considered, "selected_pairs": selected,
        "sft_examples": len(sft), "dpo_examples": len(dpo), "pii_redactions": redactions,
        "note": "propose-only; conservative regex PII scrub (the full anonymizer is a later vetting gate)",
    }
    return {"sft": sft, "dpo": dpo, "manifest": manifest}


def _write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-target", type=float, default=70.0, help="min harnessed 0-100 score to teach")
    ap.add_argument("--min-lift", type=float, default=20.0,
                    help="min baseline->harnessed lift (the teaching signal)")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    args = ap.parse_args(argv)
    doc = build(min_target=args.min_target, min_lift=args.min_lift)
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out / "sft.jsonl", doc["sft"])
    _write_jsonl(out / "dpo.jsonl", doc["dpo"])
    (out / "manifest.json").write_text(json.dumps(doc["manifest"], indent=2) + "\n", encoding="utf-8")
    m = doc["manifest"]
    print(f"[lift-training-data] considered {m['considered_pairs']} pairs -> selected "
          f"{m['selected_pairs']} (target>={args.min_target}, lift>={args.min_lift})")
    print(f"[lift-training-data] wrote {m['sft_examples']} SFT + {m['dpo_examples']} DPO to {out} "
          f"({m['pii_redactions']} PII redactions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
