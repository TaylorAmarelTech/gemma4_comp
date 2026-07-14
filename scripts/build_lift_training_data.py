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
  * quality   -- harnessed mean score >= --min-target
  * signal    -- (harnessed - baseline) mean lift >= --min-lift   (a clear teaching signal, not noise)
  * grounded  -- the teacher (gold) reply must be a GROUNDED answer, not a bare refusal: its A/B/D
                 components (identifies the indicator + cites the law + gives concrete resources) clear
                 --min-grounding, and it cites at least some law (--min-cite on the B component). A reply
                 that scores via "refuse" (C) alone -- "a refusal without details or citations" -- is
                 NOT a good gold target. (Component scores come from panel.jsonl; when a panel record
                 carries no components, this gate is skipped and selection falls back to score+lift.)
  * lift adds grounding -- the lift must come (partly) from BETTER grounding, not refusal alone:
                 teacher(A+B+D) - baseline(A+B+D) >= --min-grounding-delta. Drops pairs whose only
                 improvement was refusing harder (C up, A/B/D flat) -- exactly the "refusal without
                 added details/citations" a model should not learn (skipped if baseline has no components).
  * answered  -- the teacher reply is a real answer, not a format failure (empty / reasoning-trace /
                 too-short non-answer), via scripts/refusal_detector.py. A context-dependent "refusal"
                 is NOT blanket-dropped here -- the grounding gate already rejects bare refusals while
                 keeping well-grounded ones.
  * citation  -- the teacher cites no hallucinated statute section / out-of-range ILO convention, via
                 scripts/citation_accuracy.py (never teach a fabricated citation), and no real-but-
                 irrelevant ILO convention for the exploitation signal, via palermo_screening.py
                 (never teach citation theatre).
  * privacy   -- a conservative PII / volatile-contact scrub (emails, phone-like, long digit runs), so
                 targets teach the response SHAPE, not a specific (volatile) hotline number -- statute
                 refs like "C181" or "RA 8042" are preserved.

The teacher arm defaults to harness_core (--teacher-arm): the cheap offline GREP + retrieved-law core
captures essentially all the measured lift (full-vs-core ~ 0 on the board), and teaching from it
rather than harness_full avoids memorizing volatile tool facts (live hotline numbers, current fee
caps) that belong in tools / RAG, not in the weights.

Propose-only: writes to the gitignored reports/training/ store + a manifest; never trains, never
mutates the benchmark. Distinct from prepare_training_data.py (which converts the seed corpus's
manual worst->best grades); this distils the benchmark's *measured* harness-lift.

    python scripts/build_lift_training_data.py --min-target 70 --min-lift 20
    python scripts/build_lift_training_data.py --validate          # print the manifest, write nothing
Design: docs/phase3_training_framework.md ; rationale: docs/research/benchmark_findings_and_roadmap.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
import sys
from collections import defaultdict
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
# Sibling scripts (refusal + citation gates) -- importable however this script is run or imported.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from refusal_detector import classify as _classify, FORMAT_FAILURE  # noqa: E402
from citation_accuracy import citation_stats as _citation_stats  # noqa: E402
from palermo_screening import citation_coherence as _citation_coherence  # noqa: E402

PANEL = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
RESULTS = _ROOT / "reports" / "rich_lift" / "results.jsonl"
OUT_DIR = _ROOT / "reports" / "training"
BASELINE_ARM = "baseline"
DEFAULT_TEACHER_ARM = "harness_core"   # cheap offline core captures the lift; avoids volatile facts
DEFAULT_MIN_GROUNDING = 24.0           # teacher A+B+D (max 60) -- a bare refusal scores ~0 here
DEFAULT_MIN_CITE = 4.0                 # teacher B (max 20) -- the gold target must cite at least some law
DEFAULT_MIN_GROUNDING_DELTA = 2.0      # teacher(A+B+D) - baseline(A+B+D) -- the lift must add grounding,
#                                        not come from refusing harder (C) alone (skipped if no baseline comps)

# Conservative PII / volatile-contact scrub. Targets emails, phone-like sequences, and long digit
# runs (passport / account / case ids) -- NOT statute refs like "C181" or "RA 8042" (no 7+ digit run).
_SCRUB = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[email]"),
    (re.compile(r"\+?\d[\d\s().\-]{8,}\d"), "[phone]"),
    (re.compile(r"(?<!\d)\d{6,}(?!\d)"), "[id-number]"),
]
_EMAIL = _SCRUB[0][0]
_PHONE = _SCRUB[1][0]
_LONG_DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_PROMPT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _has_sensitive_display_text(text: str) -> bool:
    return bool(
        _EMAIL.search(text)
        or _PHONE.search(text)
        or _LOCAL_PATH_HINT.search(text)
        or _LONG_DIGITS.search(text)
    )


def _safe_prompt_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or _has_sensitive_display_text(text):
        return None
    return text if _SAFE_PROMPT_ID.fullmatch(text) else None


def _safe_relative_report_path(path: pathlib.PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("../") or "/../" in display:
        return "redacted"
    if _has_sensitive_display_text(display):
        return "redacted"
    if not _SAFE_RELATIVE_PATH.fullmatch(display):
        return "redacted"
    return display


def _display_report_path(raw_path: Any) -> str:
    if not raw_path:
        return "n/a"
    raw = str(raw_path)
    try:
        path = pathlib.Path(raw)
        if path.is_absolute():
            try:
                return _safe_relative_report_path(path.relative_to(_ROOT))
            except ValueError:
                return "external"
        return _safe_relative_report_path(pathlib.PurePosixPath(pathlib.PureWindowsPath(raw).as_posix()))
    except (OSError, RuntimeError, ValueError):
        return "redacted"


def _load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
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
        if not isinstance(r, dict):
            continue
        try:
            by[(str(r["model"]), str(r["prompt_id"]), str(r["arm"]))].append(float(r["score_0_100"]))
        except (KeyError, TypeError, ValueError):
            continue
    return {k: round(statistics.mean(v), 1) for k, v in by.items() if v}


def mean_components(panel: list[dict]) -> dict[tuple[str, str, str], dict[str, float]]:
    """Mean per-component {A,B,C,D,E} per (model, prompt_id, arm) over the panel (skips records with
    no ``components`` block, so old/component-less panels degrade gracefully)."""
    by: dict[tuple[str, str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in panel:
        if not isinstance(r, dict):
            continue
        comp = r.get("components")
        if not isinstance(comp, dict):
            continue
        try:
            key = (str(r["model"]), str(r["prompt_id"]), str(r["arm"]))
        except (KeyError, TypeError):
            continue
        for k in ("A", "B", "C", "D", "E"):
            try:
                by[key][k].append(float(comp[k]))
            except (KeyError, TypeError, ValueError):
                continue
    return {key: {k: round(statistics.mean(v), 1) for k, v in comps.items() if v}
            for key, comps in by.items()}


def responses(results: list[dict]) -> dict[tuple[str, str, str], dict[str, str]]:
    """{(model, prompt_id, arm): {response, prompt_text}} from the raw response log (last write wins)."""
    out: dict[tuple[str, str, str], dict[str, str]] = {}
    for r in results:
        if not isinstance(r, dict):
            continue
        try:
            response = r.get("response", "")
            if not isinstance(response, str):
                continue
            prompt_text = r.get("prompt_text", "")
            if not isinstance(prompt_text, str):
                prompt_text = ""
            out[(str(r["model"]), str(r["prompt_id"]), str(r["arm"]))] = {
                "response": response,
                "prompt_text": prompt_text,
            }
        except (KeyError, TypeError):
            continue
    return out


def _safe_citation_example(*, model: str, prompt_id: str | None, coherence: dict[str, Any]) -> dict[str, Any]:
    """Structured citation metadata only; never include raw prompts or responses."""
    return {
        "model": model,
        "prompt_id": prompt_id,
        "mapped_signals": coherence.get("mapped_signals", []),
        "cited_conventions": coherence.get("cited_conventions", []),
        "expected_conventions": coherence.get("expected_conventions", []),
        "matched": coherence.get("matched", []),
        "coherent": coherence.get("coherent", False),
    }


def build(*, min_target: float, min_lift: float, teacher_arm: str = DEFAULT_TEACHER_ARM,
          min_grounding: float = DEFAULT_MIN_GROUNDING, min_cite: float = DEFAULT_MIN_CITE,
          min_grounding_delta: float = DEFAULT_MIN_GROUNDING_DELTA,
          panel_path: pathlib.Path = PANEL, results_path: pathlib.Path = RESULTS,
          require_citation_relevance: bool = True) -> dict[str, Any]:
    """Select high-lift (baseline, harnessed) pairs and build vetted SFT + DPO records + a manifest.

    The teacher (gold) arm defaults to ``harness_core``. Beyond score + lift, each pair's teacher reply
    must be a real answer (not a format failure), grounded (A+B+D >= ``min_grounding`` and B >=
    ``min_cite`` -- never a bare refusal), and free of hallucinated or irrelevant citations.
    """
    panel = _load_jsonl(panel_path)
    score = mean_scores(panel)
    comps = mean_components(panel)
    resp = responses(_load_jsonl(results_path))
    by_pair: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for (model, pid, arm), s in score.items():
        by_pair[(model, pid)][arm] = s

    sft: list[dict[str, Any]] = []
    dpo: list[dict[str, Any]] = []
    considered = selected = redactions = 0
    dropped_format = dropped_grounding = dropped_citation = dropped_grounding_delta = 0
    dropped_irrelevant_citation = 0
    metadata_sanitized_prompt_ids = 0
    irrelevant_citation_examples: list[dict[str, Any]] = []
    for (model, pid), arms in by_pair.items():
        if BASELINE_ARM not in arms or teacher_arm not in arms:
            continue
        considered += 1
        safe_pid = _safe_prompt_id(pid)
        prompt_id_sanitized = safe_pid != pid
        base_s, teach_s = arms[BASELINE_ARM], arms[teacher_arm]
        lift = round(teach_s - base_s, 1)
        if teach_s < min_target or lift < min_lift:
            continue
        base_r = resp.get((model, pid, BASELINE_ARM))
        teach_r = resp.get((model, pid, teacher_arm))
        if not base_r or not teach_r or not teach_r["response"].strip() or not base_r["response"].strip():
            continue
        # answered: the gold target must be a real answer, not an empty/reasoning-trace/too-short non-answer
        _useful, _reason = _classify(teach_r["response"])
        if _reason in FORMAT_FAILURE:
            dropped_format += 1
            continue
        # grounded: the gold target must score on indicator+law+resources (A/B/D), not refuse (C) alone
        comp = comps.get((model, pid, teacher_arm))
        if comp:
            grounding = comp.get("A", 0.0) + comp.get("B", 0.0) + comp.get("D", 0.0)
            if grounding < min_grounding or comp.get("B", 0.0) < min_cite:
                dropped_grounding += 1
                continue
        # lift adds grounding: the improvement must include better indicator+law+resources (A+B+D), not
        # refusal (C) alone -- never teach a pair whose only gain was refusing harder. Skipped if baseline
        # carries no components (graceful degradation, same as the absolute grounding gate).
        base_comp = comps.get((model, pid, BASELINE_ARM))
        grounding_delta: "float | None" = None
        if comp and base_comp:
            grounding_delta = round(
                (comp.get("A", 0.0) + comp.get("B", 0.0) + comp.get("D", 0.0))
                - (base_comp.get("A", 0.0) + base_comp.get("B", 0.0) + base_comp.get("D", 0.0)), 1)
            if grounding_delta < min_grounding_delta:
                dropped_grounding_delta += 1
                continue
        # citation: never teach a hallucinated statute section / out-of-range ILO convention
        cs = _citation_stats(teach_r["response"])
        if cs["n_section_implausible"] > 0 or cs["n_conventions_implausible"] > 0:
            dropped_citation += 1
            continue
        if require_citation_relevance:
            coherence = _citation_coherence(teach_r["response"])
            if not coherence["coherent"]:
                dropped_irrelevant_citation += 1
                if prompt_id_sanitized:
                    metadata_sanitized_prompt_ids += 1
                if len(irrelevant_citation_examples) < 10:
                    irrelevant_citation_examples.append(
                        _safe_citation_example(model=model, prompt_id=safe_pid, coherence=coherence)
                    )
                continue
        prompt, k1 = scrub(teach_r["prompt_text"] or base_r["prompt_text"])
        chosen, k2 = scrub(teach_r["response"])
        rejected, k3 = scrub(base_r["response"])
        if not prompt.strip():
            continue
        redactions += k1 + k2 + k3
        selected += 1
        if prompt_id_sanitized:
            metadata_sanitized_prompt_ids += 1
        meta = {"model": model, "prompt_id": safe_pid, "baseline_score": base_s,
                "target_score": teach_s, "lift": lift}
        if comp:
            meta["target_components"] = comp
        if grounding_delta is not None:
            meta["grounding_delta"] = grounding_delta
        sft.append({"messages": [{"role": "user", "content": prompt},
                                 {"role": "assistant", "content": chosen}], "_meta": meta})
        dpo.append({"prompt": prompt, "chosen": chosen, "rejected": rejected, "_meta": meta})

    manifest = {
        "source": {"panel": _display_report_path(panel_path), "results": _display_report_path(results_path)},
        "arms": {"baseline": BASELINE_ARM, "teacher": teacher_arm},
        "thresholds": {"min_target": min_target, "min_lift": min_lift,
                       "min_grounding": min_grounding, "min_cite": min_cite,
                       "min_grounding_delta": min_grounding_delta},
        "considered_pairs": considered, "selected_pairs": selected,
        "dropped_format_failure": dropped_format,
        "dropped_low_grounding": dropped_grounding,
        "dropped_low_grounding_delta": dropped_grounding_delta,
        "dropped_bad_citation": dropped_citation,
        "require_citation_relevance": require_citation_relevance,
        "dropped_irrelevant_citation": dropped_irrelevant_citation,
        "irrelevant_citation_examples": irrelevant_citation_examples,
        "metadata_sanitized_prompt_ids": metadata_sanitized_prompt_ids,
        "sft_examples": len(sft), "dpo_examples": len(dpo), "pii_redactions": redactions,
        "note": (f"propose-only; teacher={teacher_arm}; gold targets are grounded answers "
                 f"(A+B+D>={min_grounding:g}, B>={min_cite:g}), never bare refusals; the lift must add "
                 f"grounding (delta A+B+D>={min_grounding_delta:g}, not refusal alone); format-failures and "
                 f"hallucinated or irrelevant citations dropped; conservative regex PII scrub (full "
                 f"anonymizer is a later vetting gate)"),
    }
    return {"sft": sft, "dpo": dpo, "manifest": manifest}


def _write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-target", type=float, default=70.0, help="min harnessed 0-100 score to teach")
    ap.add_argument("--min-lift", type=float, default=20.0,
                    help="min baseline->harnessed lift (the teaching signal)")
    ap.add_argument("--teacher-arm", default=DEFAULT_TEACHER_ARM,
                    help="harnessed arm to teach from (harness_core | harness_full); core avoids volatile facts")
    ap.add_argument("--min-grounding", type=float, default=DEFAULT_MIN_GROUNDING,
                    help="min teacher A+B+D component sum -- rejects bare refusals (lift on C alone)")
    ap.add_argument("--min-cite", type=float, default=DEFAULT_MIN_CITE,
                    help="min teacher B (cites-law) component -- the gold target must cite some law")
    ap.add_argument("--min-grounding-delta", type=float, default=DEFAULT_MIN_GROUNDING_DELTA,
                    help="min teacher-minus-baseline A+B+D -- the lift must add grounding, not refusal alone")
    ap.add_argument("--allow-incoherent-citations", action="store_true",
                    help="legacy mode: keep high-lift rows even when cited ILO conventions do not govern "
                         "the named exploitation indicator")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--validate", action="store_true",
                    help="run + print the manifest only; write nothing (a CPU-safe dry run)")
    args = ap.parse_args(argv)
    doc = build(min_target=args.min_target, min_lift=args.min_lift, teacher_arm=args.teacher_arm,
                min_grounding=args.min_grounding, min_cite=args.min_cite,
                min_grounding_delta=args.min_grounding_delta,
                require_citation_relevance=not args.allow_incoherent_citations)
    m = doc["manifest"]
    if args.validate:
        print(json.dumps(m, indent=2))
        return 0
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out / "sft.jsonl", doc["sft"])
    _write_jsonl(out / "dpo.jsonl", doc["dpo"])
    (out / "manifest.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print(f"[lift-training-data] considered {m['considered_pairs']} pairs -> selected "
          f"{m['selected_pairs']} (teacher={args.teacher_arm}, target>={args.min_target}, "
          f"lift>={args.min_lift}); dropped format={m['dropped_format_failure']} "
          f"grounding={m['dropped_low_grounding']} delta={m['dropped_low_grounding_delta']} "
          f"citation={m['dropped_bad_citation']} irrelevant-citation={m['dropped_irrelevant_citation']}")
    print(f"[lift-training-data] wrote {m['sft_examples']} SFT + {m['dpo_examples']} DPO to "
          f"{_display_report_path(out)} "
          f"({m['pii_redactions']} PII redactions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
