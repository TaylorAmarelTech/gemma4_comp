#!/usr/bin/env python3
"""Build the DueCare harness-lift benchmark prompt set (v1.2) by merging the curated + registry sources.

The benchmark began as the 210-prompt "scheme" set (all ``hard``, 7 typologies). This widens it for
construct validity + scale by folding in, stratified and text-deduped against what's already chosen:

  * the harness-lift EXPANSION set (68 typologies incl. jailbreaks, evasion probes, worker/employer
    queries; easy/medium/hard),
  * the MAJOR-CASE set (casefile-derived worker-support / caseworker-triage scenarios), and
  * a large stratified draw from the **74,640-prompt trafficking seed registry**
    (``seed_prompts.jsonl``), excluding export/meta categories.

The original 210 scheme prompts are preserved FIRST and in order, and the expansion+major-case picks
are deterministic (seeded), so the first 776 ids match v1.1 exactly: existing graded results stay
aligned by prompt_id and a re-grade only ADDS the new prompts (the runner is resumable).

Pipeline: ``gen_scheme_prompts.py`` produces the base 210 -> this script widens it.
Idempotent: re-running reads back only the ``source == "scheme"`` base, so it never compounds.

    python scripts/build_benchmark_promptset.py
    python scripts/build_benchmark_promptset.py --per-category-seed 100 --max-prompt-chars 6000
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_BENCH = _ROOT / "configs" / "duecare" / "benchmarks"
SCHEME = _BENCH / "scheme_prompts.json"
EXPANSION = _BENCH / "harness_lift_prompts_expansion.jsonl"
MAJOR_CASE = _BENCH / "major_case_patterns" / "harness_lift_prompts_major_case.jsonl"
SEED_CORPUS = _ROOT / "configs" / "duecare" / "domains" / "trafficking" / "seed_prompts.jsonl"
SEED = 13
# seed-corpus categories that are export/meta artifacts, not gradeable adversarial prompts.
SEED_EXCLUDE = ("unknown", "database_export", "checkpoint_export", "output_conditioning")


def _text_hash(text: str) -> str:
    return hashlib.sha1(text.strip().lower().encode("utf-8")).hexdigest()


def _load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _norm(p: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "id": p["id"],
        "text": p["text"],
        "category": p.get("category", "?"),
        "corridor": p.get("corridor", "various"),
        "difficulty": p.get("difficulty", "hard"),
        "source": source,
    }


def _stratified(pool: list[dict[str, Any]], source: str, per_category: int,
                seen_text: set[str], seen_id: set[str], rng: random.Random) -> list[dict[str, Any]]:
    """Up to ``per_category`` text-unique prompts per category, deduped against what's already seen."""
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for p in pool:
        if not p.get("text") or not p.get("id"):
            continue
        by_cat.setdefault(str(p.get("category", "?")), []).append(p)
    out: list[dict[str, Any]] = []
    for _cat, ps in sorted(by_cat.items()):
        rng.shuffle(ps)
        kept = 0
        for p in ps:
            if kept >= per_category:
                break
            h = _text_hash(p["text"])
            if h in seen_text or p["id"] in seen_id:
                continue
            seen_text.add(h)
            seen_id.add(p["id"])
            out.append(_norm(p, source))
            kept += 1
    return out


def _seed_pool(max_prompt_chars: int) -> list[dict[str, Any]]:
    """The trafficking seed registry, minus export/meta categories and over-long prompts."""
    pool = []
    for p in _load_jsonl(SEED_CORPUS):
        cat = str(p.get("category", "")).lower()
        text = p.get("text")
        if cat in SEED_EXCLUDE or not isinstance(text, str):
            continue
        if 0 < len(text.strip()) <= max_prompt_chars:
            pool.append(p)
    return pool


def build(*, per_category_expansion: int, per_category_majorcase: int,
          per_category_seed: int, max_prompt_chars: int) -> dict[str, Any]:
    current = json.loads(SCHEME.read_text(encoding="utf-8"))
    prompts = current.get("prompts", current)
    base = [p for p in prompts if p.get("source", "scheme") == "scheme"]  # idempotent base
    seen_text = {_text_hash(p["text"]) for p in base}
    seen_id = {p["id"] for p in base}
    rng = random.Random(SEED)
    add_exp = _stratified(_load_jsonl(EXPANSION), "expansion", per_category_expansion,
                          seen_text, seen_id, rng)
    add_mc = _stratified(_load_jsonl(MAJOR_CASE), "major_case", per_category_majorcase,
                        seen_text, seen_id, rng)
    add_seed = _stratified(_seed_pool(max_prompt_chars), "seed", per_category_seed,
                          seen_text, seen_id, rng)
    merged = ([_norm(p, "scheme") for p in base] + add_exp + add_mc + add_seed)
    return {
        "version": "1.2",
        "_build": {"scheme": len(base), "expansion": len(add_exp), "major_case": len(add_mc),
                   "seed_corpus": len(add_seed), "total": len(merged), "seed": SEED,
                   "per_category_expansion": per_category_expansion,
                   "per_category_majorcase": per_category_majorcase,
                   "per_category_seed": per_category_seed, "max_prompt_chars": max_prompt_chars},
        "prompts": merged,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-category-expansion", type=int, default=8)
    ap.add_argument("--per-category-majorcase", type=int, default=45)
    ap.add_argument("--per-category-seed", type=int, default=100)
    ap.add_argument("--max-prompt-chars", type=int, default=6000)
    ap.add_argument("--out", default=str(SCHEME))
    args = ap.parse_args(argv)
    doc = build(per_category_expansion=args.per_category_expansion,
                per_category_majorcase=args.per_category_majorcase,
                per_category_seed=args.per_category_seed,
                max_prompt_chars=args.max_prompt_chars)
    pathlib.Path(args.out).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ps = doc["prompts"]
    b = doc["_build"]
    print(f"wrote {args.out}: {len(ps)} prompts "
          f"(scheme {b['scheme']} + expansion {b['expansion']} + major_case {b['major_case']} "
          f"+ seed_corpus {b['seed_corpus']})")
    print("difficulty:", dict(Counter(p["difficulty"] for p in ps)))
    print("distinct categories:", len({p["category"] for p in ps}))
    print("by source:", dict(Counter(p["source"] for p in ps)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
