#!/usr/bin/env python3
"""Training-data quality audit -- guard against overfitting, false patterns, fragile-fact memorization,
and jurisdiction-bound shortcuts BEFORE the GPU fine-tune.

A fine-tune is only as good as its data. This audits the assembled SFT/DPO splits
(organize_training_data.py output) for the failure modes a safety judge must avoid:

  1. OVERFITTING -- cross-split near-dup LEAKAGE: a held-out example that has a SimHash near-duplicate in
     train means the "generalisation" diagnostic is measuring memorisation, not transfer. Want 0.
  2. FALSE PATTERN (length shortcut) -- if DPO `chosen` is systematically much longer than `rejected`,
     the model learns "longer = preferred" instead of "grounded = preferred". Want a modest ratio.
  3. JURISDICTION-INDEPENDENCE -- does each typology appear across MULTIPLE corridors? A typology seen in
     only one corridor lets the model bind the pattern to that jurisdiction instead of learning the
     universal (ILO) indicator. Want broad corridor spread; flag single-corridor typologies.
  4. FRAGILE-FACT memorization -- gold (`chosen`) replies asserting volatile specifics (phone/hotline
     numbers, exact fee amounts, explicit dates) teach the model to memorise facts that go stale; those
     belong in tools/RAG. Want ~0 phone-like (the privacy scrub should catch them) + visibility on
     money/date specifics.

Informational + propose-only: reads the splits, writes reports/training/quality_audit.json with metrics
+ risk flags. Offline/deterministic. Run before `training_engine.py --with-gpu`. Reuses
research_tools.dedup (SimHash) + the prompt sets for corridor/typology.

    python scripts/audit_training_quality.py
Design: docs/research/training_methodology.md (quality gates)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
import sys
from collections import Counter, defaultdict
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_TRAIN = _ROOT / "reports" / "training"
FULL_SET = _ROOT / "reports" / "benchmark" / "full_promptset.json"
CURATED_SET = _ROOT / "configs" / "duecare" / "benchmarks" / "scheme_prompts.json"
OUT = _TRAIN / "quality_audit.json"
NEAR_DUP_DIST = 3   # SimHash Hamming distance counted as a leak (matches organize_training_data)

# Reuse the deterministic SimHash near-dup (DRY); bridge the package src so this runs standalone.
_RT_SRC = _ROOT / "packages" / "duecare-llm-research-tools" / "src"
if _RT_SRC.exists() and str(_RT_SRC) not in sys.path:
    sys.path.insert(0, str(_RT_SRC))
try:
    from duecare.research_tools.dedup import simhash64, SimHashIndex
    _HAVE_SIMHASH = True
except Exception:  # noqa: BLE001
    _HAVE_SIMHASH = False

# Fragile-fact patterns: volatile specifics a model should NOT memorize (they belong in tools/RAG).
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_MONEY = re.compile(r"(?:\$|usd|eur|php|aed|sar)\s?\d[\d,]*", re.I)
_DATE = re.compile(r"\b(?:20\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return out


def load_pid_meta(*paths: pathlib.Path) -> dict[str, dict]:
    """{prompt_id: {category, corridor}} from the first prompt set that exists."""
    for path in paths:
        if not path.exists():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        prompts = doc.get("prompts", doc)
        return {str(p["id"]): {"category": str(p.get("category", "unknown")),
                               "corridor": str(p.get("corridor", "unknown"))}
                for p in prompts if isinstance(p, dict) and p.get("id")}
    return {}


def _sft_user(row: dict) -> str:
    return next((str(m.get("content", "")) for m in (row.get("messages") or [])
                if m.get("role") == "user"), "")


def _sft_assistant(row: dict) -> str:
    return next((str(m.get("content", "")) for m in reversed(row.get("messages") or [])
                if m.get("role") == "assistant"), "")


def near_dup_leakage(train_texts: list[str], heldout_texts: list[str], *, max_dist: int = NEAR_DUP_DIST) -> dict:
    """Held-out texts with a SimHash near-dup in train (=> memorisation leak; want 0)."""
    if not _HAVE_SIMHASH:
        return {"available": False}
    idx = SimHashIndex((simhash64(t) for t in train_texts if t), bands=4)
    leaked = sum(1 for t in heldout_texts if t and idx.query_near(simhash64(t), max_dist=max_dist))
    n = len([t for t in heldout_texts if t])
    return {"available": True, "heldout": n, "leaked": leaked,
            "leak_rate": round(leaked / n, 4) if n else None,
            "ok": leaked == 0}


def length_bias(dpo_rows: list[dict]) -> dict:
    """DPO chosen-vs-rejected length: a big chosen>>rejected gap is a length shortcut the model can game."""
    pairs = [(len(str(r.get("chosen", ""))), len(str(r.get("rejected", "")))) for r in dpo_rows]
    pairs = [(c, j) for c, j in pairs if c and j]
    if not pairs:
        return {"n": 0}
    c_mean = statistics.mean(c for c, _ in pairs)
    j_mean = statistics.mean(j for _, j in pairs)
    return {"n": len(pairs), "chosen_chars_mean": round(c_mean), "rejected_chars_mean": round(j_mean),
            "chosen_over_rejected_ratio": round(c_mean / j_mean, 2) if j_mean else None,
            "frac_chosen_longer": round(sum(c > j for c, j in pairs) / len(pairs), 3),
            # a ratio >~2.0 means length is a strong confound -- the DPO trunc fix keeps both sides full
            "ok": (c_mean / j_mean) <= 2.0 if j_mean else None}


def corridor_diversity(rows: list[dict], pid_meta: dict[str, dict], *, min_rows: int = 10) -> dict:
    """Per-typology corridor spread -- the jurisdiction-shortcut guard.

    Only a typology with >= `min_rows` training rows ALL sitting in a single real corridor is a genuine
    shortcut risk: dense enough for the model to bind the pattern to that jurisdiction. Sparse typologies
    (< min_rows) and attack-STYLE categories (corridor not applicable -> 'unknown') can't span corridors
    meaningfully, so they are reported, not flagged. (The universal layer the model should learn is the
    ILO-11 indicator, which the distilled targets carry regardless of corridor; this guards against the
    data accidentally letting a corridor stand in for an indicator.)"""
    rows_by_cat: Counter = Counter()
    corr_by_cat: dict[str, set] = defaultdict(set)
    corridors: set = set()
    for r in rows:
        pid = str((r.get("_meta") or {}).get("prompt_id"))
        meta = pid_meta.get(pid)
        if not meta:
            continue
        rows_by_cat[meta["category"]] += 1
        if meta["corridor"] != "unknown":
            corr_by_cat[meta["category"]].add(meta["corridor"])
            corridors.add(meta["corridor"])
    dense_single = sorted(c for c, n in rows_by_cat.items()
                          if n >= min_rows and len(corr_by_cat.get(c, set())) == 1)
    multi = sum(1 for cs in corr_by_cat.values() if len(cs) >= 2)
    sparse = sum(1 for n in rows_by_cat.values() if n < min_rows)
    return {"distinct_corridors": len(corridors), "typologies": len(rows_by_cat),
            "multi_corridor_typologies": multi, "sparse_typologies": sparse, "min_rows": min_rows,
            "dense_single_corridor_typologies": dense_single[:20],
            "n_dense_single_corridor": len(dense_single),
            "ok": len(dense_single) == 0}


def fragile_fact_assertions(gold_texts: list[str]) -> dict:
    """Gold replies asserting volatile specifics (phone/money/date) -- fragile facts that should be hedged
    / deferred to tools, not memorised. phone should be ~0 (privacy scrub); money/date are informational."""
    n = len([t for t in gold_texts if t])
    phone = sum(1 for t in gold_texts if t and _PHONE.search(t))
    money = sum(1 for t in gold_texts if t and _MONEY.search(t))
    date = sum(1 for t in gold_texts if t and _DATE.search(t))
    return {"n": n, "with_phone_like": phone, "with_money_amount": money, "with_explicit_date": date,
            "phone_rate": round(phone / n, 4) if n else None,
            "ok_phone": phone == 0}   # phones must be scrubbed; money/date are visibility-only


def audit() -> dict[str, Any]:
    pid_meta = load_pid_meta(FULL_SET, CURATED_SET)
    sft_tr, sft_ho = _load_jsonl(_TRAIN / "sft_train.jsonl"), _load_jsonl(_TRAIN / "sft_heldout.jsonl")
    dpo_tr, dpo_ho = _load_jsonl(_TRAIN / "dpo_train.jsonl"), _load_jsonl(_TRAIN / "dpo_heldout.jsonl")
    sft_leak = near_dup_leakage([_sft_user(r) for r in sft_tr], [_sft_user(r) for r in sft_ho])
    dpo_leak = near_dup_leakage([str(r.get("prompt", "")) for r in dpo_tr],
                                [str(r.get("prompt", "")) for r in dpo_ho])
    gold = [_sft_assistant(r) for r in sft_tr] + [str(r.get("chosen", "")) for r in dpo_tr]
    report = {
        "inputs": {"sft_train": len(sft_tr), "sft_heldout": len(sft_ho),
                   "dpo_train": len(dpo_tr), "dpo_heldout": len(dpo_ho), "pid_meta": len(pid_meta)},
        "overfitting_leakage": {"sft": sft_leak, "dpo": dpo_leak},
        "false_pattern_length_bias": length_bias(dpo_tr),
        "jurisdiction_corridor_diversity": corridor_diversity(sft_tr + dpo_tr, pid_meta),
        "fragile_fact_assertions": fragile_fact_assertions(gold),
        "note": ("pre-train quality audit: leak (overfit) want 0; length ratio (false pattern) want <=2.0; "
                 "single-corridor typologies (jurisdiction shortcut) want few; phone-like in gold (fragile "
                 "fact) want 0. Universal ILO indicators are taught; volatile facts belong in tools/RAG."),
    }
    flags = []
    if sft_leak.get("available") and not sft_leak.get("ok"):
        flags.append(f"SFT cross-split leakage: {sft_leak['leaked']} heldout near-dups in train")
    if dpo_leak.get("available") and not dpo_leak.get("ok"):
        flags.append(f"DPO cross-split leakage: {dpo_leak['leaked']}")
    lb = report["false_pattern_length_bias"]
    if lb.get("ok") is False:
        flags.append(f"DPO length bias: chosen/rejected ratio {lb.get('chosen_over_rejected_ratio')}")
    cd = report["jurisdiction_corridor_diversity"]
    if cd.get("ok") is False:
        flags.append(f"{cd['n_dense_single_corridor']} dense single-corridor typologies "
                     f"(>={cd['min_rows']} rows, jurisdiction shortcut risk): "
                     f"{', '.join(cd['dense_single_corridor_typologies'][:5])}")
    ff = report["fragile_fact_assertions"]
    if ff.get("ok_phone") is False:
        flags.append(f"{ff['with_phone_like']} gold replies assert phone-like fragile facts")
    report["risk_flags"] = flags
    report["clean"] = not flags
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stdout", action="store_true", help="print full JSON; else write the report file")
    args = ap.parse_args(argv)
    rep = audit()
    if args.stdout:
        print(json.dumps(rep, indent=2))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    inp = rep["inputs"]
    if not (inp["sft_train"] or inp["dpo_train"]):
        print("[quality-audit] no training splits -- run scripts/organize_training_data.py first")
        return 1
    print(f"[quality-audit] sft {inp['sft_train']}tr/{inp['sft_heldout']}ho dpo {inp['dpo_train']}tr/"
          f"{inp['dpo_heldout']}ho | leak(sft)={rep['overfitting_leakage']['sft'].get('leaked')} "
          f"len-ratio={rep['false_pattern_length_bias'].get('chosen_over_rejected_ratio')} "
          f"dense-single-corridor={rep['jurisdiction_corridor_diversity'].get('n_dense_single_corridor')} "
          f"gold-phone={rep['fragile_fact_assertions'].get('with_phone_like')}")
    print(f"[quality-audit] {'CLEAN' if rep['clean'] else 'FLAGS: ' + '; '.join(rep['risk_flags'])} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
