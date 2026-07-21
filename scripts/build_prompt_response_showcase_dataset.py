#!/usr/bin/env python3
# ruff: noqa: E501
"""Build a vetted, public-safe sample of raw prompt + raw responses (baseline / harness_core /
harness_full) for the DueCare harness-lift benchmark, for NLP / sentiment / keyword notebooks.

Source: reports/rich_lift/results.jsonl (the raw sweep outputs; fields prompt_id, prompt_text,
arm, model, response). We keep only the headline model, only SYNTHETIC/composite prompt ids, scrub
kernel run-metadata (paths, RUN/job ids, zip names) while PRESERVING response structure (newlines,
bullets -- they matter for NLP), drop the rare row that trips a conservative PII scan, and stage a
small stratified sample as a public Kaggle dataset.

Why this is safe: the prompts are synthetic/composite scenarios (no real individual), the responses
are model outputs to those synthetic prompts, kernel metadata is scrubbed, and rows with e-mail /
long account-number / IBAN patterns are dropped outright. Composite first names (Maria, Ramesh) are
allowed per the safety gate; public NGO hotline numbers in a harnessed answer are public resources.

    python scripts/build_prompt_response_showcase_dataset.py
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "reports" / "rich_lift" / "results.jsonl"
PROMPTSET = ROOT / "reports" / "benchmark" / "full_promptset.json"
OUT = ROOT / "reports" / "kaggle_publish" / "prompt_response_showcase"
DATASET_ID = "taylorsamarel/duecare-prompt-response-showcase"
TITLE = "DueCare Prompt and Response Showcase"
MODEL = "gemma4:31b"
ARMS = ("baseline", "harness_core", "harness_full")
SYNTHETIC_PREFIXES = ("GEN-", "SCHEME-", "SEED-", "SYN-", "COMP-", "CASE-")
MAX_TRIPLES_SCAN = 4000       # stop streaming once we have this many complete triples
PER_CATEGORY = 22             # stratified cap so no category dominates
SEED = 20260720

# ---- structure-preserving kernel-metadata scrub (keeps newlines / bullets for NLP) ----
_NOISE = [re.compile(p, re.I) for p in (
    r"/kaggle/[^\s`\"']*", r"[A-Za-z]:\\\\[^\s`\"']*", r"\bRUN[-_][A-Za-z0-9]{4,}\b",
    r"\bjob[-_][A-Za-z0-9]{4,}\b", r"\b[\w-]+\.zip\b", r"/tmp/[^\s`\"']*",
)]
# ---- conservative PII drop (email / 12+ digit account runs / IBAN-like) ----
_PII = [re.compile(p) for p in (
    r"[\w.+-]+@[\w-]+\.[\w.-]{2,}", r"\b\d[\d ]{10,}\d\b", r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
)]


def scrub(text: str | None) -> str:
    out = str(text or "")
    for pat in _NOISE:
        out = pat.sub("[case material]", out)
    return out.strip()


def has_pii(text: str) -> bool:
    return any(p.search(text) for p in _PII)


def is_synthetic(prompt_id: str) -> bool:
    pid = (prompt_id or "").upper()
    return any(pid.startswith(pre) for pre in SYNTHETIC_PREFIXES)


def load_metadata() -> dict[str, dict]:
    meta: dict[str, dict] = {}
    if PROMPTSET.is_file():
        data = json.loads(PROMPTSET.read_text(encoding="utf-8"))
        for p in data.get("prompts", data if isinstance(data, list) else []):
            pid = p.get("id") or p.get("prompt_id")
            if pid:
                meta[pid] = {"category": p.get("category", "uncategorized"),
                             "corridor": p.get("corridor", ""), "difficulty": p.get("difficulty", "")}
    return meta


def collect() -> dict[str, dict]:
    """Stream results.jsonl -> {prompt_id: {"prompt_text":..., arm: response, ...}} for complete triples."""
    triples: dict[str, dict] = defaultdict(dict)
    complete: set[str] = set()
    if not RESULTS.is_file():
        raise SystemExit(f"missing {RESULTS} (the raw sweep output)")
    with RESULTS.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i % 200000 == 0 and i:
                print(f"  scanned {i:,} lines, {len(complete):,} complete triples")
            if len(complete) >= MAX_TRIPLES_SCAN:
                break
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("model") != MODEL:
                continue
            pid, arm = r.get("prompt_id"), r.get("arm")
            if not pid or arm not in ARMS or not is_synthetic(pid):
                continue
            rec = triples[pid]
            rec.setdefault("prompt_text", r.get("prompt_text", ""))
            rec[arm] = r.get("response", "")
            if all(a in rec for a in ARMS):
                complete.add(pid)
    return {pid: triples[pid] for pid in complete}


def build(out_dir: Path) -> dict:
    import random
    rng = random.Random(SEED)
    meta = load_metadata()
    print(f"streaming {RESULTS.name} for model {MODEL} ...")
    triples = collect()
    print(f"collected {len(triples):,} complete synthetic triples")

    # scrub + PII-drop + attach metadata
    rows = []
    for pid, rec in triples.items():
        prompt = scrub(rec.get("prompt_text", ""))
        resp = {a: scrub(rec.get(a, "")) for a in ARMS}
        blob = " ".join([prompt, *resp.values()])
        if not prompt or not all(resp.values()) or has_pii(blob):
            continue
        m = meta.get(pid, {"category": "uncategorized", "corridor": "", "difficulty": ""})
        rows.append({"prompt_id": pid, "category": m["category"], "corridor": m["corridor"],
                     "difficulty": m["difficulty"], "prompt_text": prompt,
                     "baseline_response": resp["baseline"], "harness_core_response": resp["harness_core"],
                     "harness_full_response": resp["harness_full"]})

    # stratified sample by category (deterministic)
    by_cat: dict[str, list] = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    sample = []
    for cat in sorted(by_cat):
        items = sorted(by_cat[cat], key=lambda r: r["prompt_id"])
        rng.shuffle(items)
        sample.extend(items[:PER_CATEGORY])
    sample.sort(key=lambda r: (r["category"], r["prompt_id"]))
    print(f"vetted sample: {len(sample):,} prompts across {len(by_cat)} categories "
          f"(dropped {len(rows) - len(sample):,} to the per-category cap; "
          f"{len(triples) - len(rows):,} rows failed scrub/PII)")

    out_dir.mkdir(parents=True, exist_ok=True)
    cols = ["prompt_id", "category", "corridor", "difficulty", "prompt_text",
            "baseline_response", "harness_core_response", "harness_full_response"]
    with (out_dir / "prompt_response_showcase.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader(); w.writerows(sample)
    with (out_dir / "prompt_response_showcase.jsonl").open("w", encoding="utf-8") as fh:
        for r in sample:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # final safety assert: no PII pattern and no real kernel-path token survived in the staged files
    staged = (out_dir / "prompt_response_showcase.jsonl").read_text(encoding="utf-8")
    leaks = [p.pattern for p in _PII if p.search(staged)]
    assert not leaks, f"PII pattern leaked into staged file: {leaks}"
    low = staged.lower()
    path_leaks = [tok for tok in ("/kaggle/", "/tmp/", "gemma4_comp",
                                  "\\amare", "users\\amare", "run_id") if tok in low]
    assert not path_leaks, f"kernel path token leaked into staged file: {path_leaks}"

    (out_dir / "dataset-metadata.json").write_text(json.dumps({
        "title": TITLE, "id": DATASET_ID,
        "licenses": [{"name": "CC0-1.0"}],
        "keywords": ["nlp", "llm-safety", "text-analysis", "anti-trafficking", "gemma"],
    }, indent=2), encoding="utf-8")
    _write_card(out_dir, sample, by_cat)
    print(f"wrote {out_dir}")
    return {"prompts": len(sample), "categories": len(by_cat)}


def _write_card(out_dir: Path, sample: list, by_cat: dict) -> None:
    avg = lambda key: sum(len(r[key]) for r in sample) / max(len(sample), 1)
    card = f"""# DueCare Prompt and Response Showcase

Raw **prompt + three model responses** for the DueCare harness-lift benchmark, staged for
NLP / sentiment / keyword analysis. Each row is one synthetic, composite migrant-worker-safety
scenario answered by `{MODEL}` under three arms:

| column | meaning |
|---|---|
| `prompt_id` | synthetic scenario id (GEN-/SCHEME-/...) |
| `category` | scenario family |
| `corridor` | migration corridor (may be blank) |
| `difficulty` | scenario difficulty (may be blank) |
| `prompt_text` | the raw adversarial prompt |
| `baseline_response` | the bare model's answer |
| `harness_core_response` | the model wrapped in the DueCare harness (persona + GREP indicator rules + retrieval + tools) |
| `harness_full_response` | the harness with online lookups |

**Rows:** {len(sample):,} prompts x 3 responses. **Categories:** {len(by_cat)}.
Mean response length -- baseline {avg('baseline_response'):.0f} chars, harness_core {avg('harness_core_response'):.0f} chars.

## Safety and provenance
- Prompts are **synthetic / composite** scenarios -- no real individual, no real case.
- Responses are **model outputs** to those synthetic prompts.
- Kernel run-metadata (paths, run/job ids, archive names) is scrubbed; response structure is preserved.
- Rows tripping a conservative PII scan (e-mail / long account-number / IBAN patterns) are dropped.
- Composite first names are allowed; public NGO hotline numbers in a harnessed answer are public resources, not personal data.
- LLM/model outputs are illustrative, not ground truth. License: CC0-1.0.

Companion grades (scores only): `taylorsamarel/duecare-harness-benchmark-grades`.
Repo: https://github.com/TaylorAmarelTech/gemma4_comp
"""
    (out_dir / "DATA_CARD.md").write_text(card, encoding="utf-8")
    (out_dir / "README.md").write_text(card, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    stats = build(args.out)
    print(f"OK -- {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
