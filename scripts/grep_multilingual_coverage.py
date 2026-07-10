"""Does the harness's GREP indicator layer fire on NON-ENGLISH / slang prompts?

Runs the deterministic GREP layer (no LLM, no network) over a multilingual prompt batch and reports how
many indicator rules fire per (language, variant_kind) versus the English source, so the multilingual
detection gap is a REPRODUCIBLE, tracked metric rather than a one-off observation. Measured 2026-07-09:
GREP fires on code-switch/slang nearly as well as English (the English trigger terms survive in real
workers' romanized text) but degrades on pure full-translations, worst for non-Latin scripts. Re-run
this after adding multilingual/transliterated GREP patterns to confirm the gap closes.

Run:
    python scripts/grep_multilingual_coverage.py    # over reports/llm_proposals/multilingual_prompts.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BATCH = _ROOT / "reports" / "llm_proposals" / "multilingual_prompts.json"
OUT = _ROOT / "reports" / "grep_multilingual_coverage.json"


def load_variants(path: Path) -> list[dict[str, Any]]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return d.get("items") or d.get("prompts") or (d if isinstance(d, list) else [])


def _default_grep_call() -> Callable[[str], Any]:
    sys.path.insert(0, str(_ROOT / "scripts"))
    for s in _ROOT.glob("packages/*/src"):
        sys.path.insert(0, str(s))
    from duecare.chat.harness import default_harness
    return default_harness()["grep_call"]


def n_fired(grep_call: Callable[[str], Any], text: str) -> int:
    """Count indicator rules that fired on ``text`` (defensive across the grep return shape). NOTE: use
    ``is None``, not truthiness -- an EMPTY hits list ``[]`` is a real 0-fire result and must not fall
    through to ``len(the dict)`` (which would count an empty result as 1)."""
    try:
        out = grep_call(text)
    except Exception:  # noqa: BLE001 -- a bad rule must not crash the whole coverage sweep
        return 0
    if isinstance(out, list):
        return len(out)
    if isinstance(out, dict):
        hits = out.get("hits")
        if hits is None:
            hits = out.get("matches")
        return len(hits) if isinstance(hits, (list, dict)) else 0
    return 0


def coverage(items: list[dict[str, Any]], grep_call: Callable[[str], Any]) -> dict:
    """Per (language, variant_kind): mean rules fired, and the ratio to the English source's fire count
    (1.0 = fires as well as English; <1.0 = the multilingual variant loses triggers)."""
    # english fire count per source_id (from source_text_en; computed once)
    en_fired: dict[str, int] = {}
    for it in items:
        sid = str(it.get("source_id", ""))
        if sid and sid not in en_fired:
            en_fired[sid] = n_fired(grep_call, str(it.get("source_text_en", "")))
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    ratios: dict[tuple[str, str], list[float]] = defaultdict(list)
    for it in items:
        key = (str(it.get("language", "?")), str(it.get("variant_kind", "?")))
        fired = n_fired(grep_call, str(it.get("text", "")))
        groups[key].append(fired)
        base = en_fired.get(str(it.get("source_id", "")), 0)
        if base > 0:
            ratios[key].append(fired / base)
    rows = []
    for key in sorted(groups):
        lang, kind = key
        rows.append({
            "language": lang, "variant_kind": kind, "n": len(groups[key]),
            "mean_fired": round(statistics.mean(groups[key]), 2),
            "fire_ratio_vs_english": round(statistics.mean(ratios[key]), 2) if ratios[key] else None,
        })
    en_mean = round(statistics.mean(list(en_fired.values())), 2) if en_fired else 0.0
    return {"english_mean_fired": en_mean, "n_sources": len(en_fired), "by_group": rows}


def format_report(cov: dict) -> str:
    lines = [f"GREP indicator coverage on multilingual variants (English mean fired = {cov['english_mean_fired']}):",
             f"{'language':12s} {'variant':18s} {'mean_fired':>10s} {'ratio_vs_EN':>12s}  n"]
    for r in cov["by_group"]:
        ratio = "n/a" if r["fire_ratio_vs_english"] is None else f"{r['fire_ratio_vs_english']:.2f}"
        lines.append(f"{r['language']:12s} {r['variant_kind']:18s} {r['mean_fired']:>10.2f} {ratio:>12s}  {r['n']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GREP fire-rate on multilingual/slang prompt variants.")
    ap.add_argument("--batch", type=Path, default=DEFAULT_BATCH)
    args = ap.parse_args(argv)
    if not args.batch.exists():
        print(f"no multilingual batch at {args.batch} -- generate one first "
              f"(build_multilingual_multimodal_prompts.py --mode multilingual)")
        return 1
    items = load_variants(args.batch)
    cov = coverage(items, _default_grep_call())
    cov["_synthetic"] = True
    cov["_propose_only"] = True
    OUT.write_text(json.dumps(cov, indent=2), encoding="utf-8")
    print(format_report(cov))
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
