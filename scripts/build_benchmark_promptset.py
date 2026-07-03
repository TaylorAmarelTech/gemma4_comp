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
import re
import sys
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
_BENCH = _ROOT / "configs" / "duecare" / "benchmarks"
SCHEME = _BENCH / "scheme_prompts.json"
EXPANSION = _BENCH / "harness_lift_prompts_expansion.jsonl"
MAJOR_CASE = _BENCH / "major_case_patterns" / "harness_lift_prompts_major_case.jsonl"
# Pretext-framed adversarial prompts (gen_pretext_prompts.py) -- the third-party-wrapper framing gap
# the findings measured (operator-voice +48 vs journalist/consultant pretext +24).
PRETEXT = _BENCH / "pretext_framing_prompts.jsonl"
# Multipath prompts (gen_multipath_prompts.py) -- 3-stage schemes chained across a corridor; closes the
# measured multipath coverage gap (findings: multipath 0/10).
MULTIPATH = _BENCH / "multipath_prompts.jsonl"
SEED_CORPUS = _ROOT / "configs" / "duecare" / "domains" / "trafficking" / "seed_prompts.jsonl"
SEED = 13
# seed-corpus categories that are export/meta artifacts, not gradeable adversarial prompts.
SEED_EXCLUDE = ("unknown", "database_export", "checkpoint_export", "output_conditioning")
# Hermes flywheel output (propose-only) + OpenClaw verdicts -- the supervised merge input.
HERMES_PROPOSALS = _ROOT / "reports" / "hermes" / "proposals.jsonl"
OPENCLAW_VETTED = _ROOT / "reports" / "openclaw" / "vetted.jsonl"
# The FULL prompt set (all gradeable seed prompts, unlimited per category) for the exhaustive
# registry sweep -- written to a gitignored path so the 64MB+ artifact never bloats git.
FULL_OUT = _ROOT / "reports" / "benchmark" / "full_promptset.json"
DOMAIN_OUT_DIR = _ROOT / "reports" / "benchmark"
_SAFE_DOMAIN_ID = re.compile(r"^[a-z0-9_:-]{1,80}$")


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
    out = {
        "id": p["id"],
        "text": p["text"],
        "category": p.get("category", "?"),
        "corridor": p.get("corridor", "various"),
        "difficulty": p.get("difficulty", "hard"),
        "source": source,
    }
    if p.get("framing"):  # preserved for the pretext source so the framing-gap analysis can group by it
        out["framing"] = p["framing"]
    return out


def _norm_domain_seed(p: dict[str, Any], domain_id: str) -> dict[str, Any]:
    out = _norm(p, f"domain_seed:{domain_id}")
    out["domain"] = domain_id
    if p.get("source"):
        out["seed_source"] = p.get("source")
    return out


def _domain_report_path(domain_id: str) -> pathlib.Path:
    if not _SAFE_DOMAIN_ID.fullmatch(domain_id):
        raise ValueError(f"unsafe domain id for output path: {domain_id!r}")
    return DOMAIN_OUT_DIR / f"{domain_id}_promptset.json"


def build_domain_promptset(domain_id: str, *, max_prompt_chars: int) -> dict[str, Any]:
    """Build a runnable promptset from a registered JSONL benchmark domain seed pack.

    The trafficking/default promptset has a richer widening path and stays on
    ``build()``. This helper is the conservative cross-domain MVP: it resolves a
    registry seed pack, validates the rows, text-dedupes them, and attaches the
    domain rubric metadata needed by downstream runners.
    """
    from domain_grounding import load_domain_grounding
    from domain_registry import get_domain, resolve_scheme_pack

    spec = get_domain(domain_id)
    grounding = load_domain_grounding(domain_id)
    pack_format = spec.get("scheme_pack_format")
    if pack_format != "jsonl":
        raise ValueError(
            f"domain {domain_id!r} uses scheme_pack_format={pack_format!r}; "
            "only jsonl seed packs are supported by --domain MVP"
        )
    pack = resolve_scheme_pack(domain_id)
    rows = _load_jsonl(pack)
    prompts: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    seen_id: set[str] = set()
    dropped = Counter()
    for row in rows:
        prompt_id = row.get("id")
        text = row.get("text")
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            dropped["missing_id"] += 1
            continue
        if not isinstance(text, str) or not text.strip():
            dropped["missing_text"] += 1
            continue
        if 0 < max_prompt_chars < len(text.strip()):
            dropped["over_max_prompt_chars"] += 1
            continue
        h = _text_hash(text)
        if h in seen_text:
            dropped["duplicate_text"] += 1
            continue
        if prompt_id in seen_id:
            dropped["duplicate_id"] += 1
            continue
        seen_text.add(h)
        seen_id.add(prompt_id)
        prompts.append(_norm_domain_seed(row, domain_id))
    domain_spec = {
        "display_name": spec.get("display_name"),
        "status": spec.get("status"),
        "rag_vertical": spec.get("rag_vertical"),
        "rubric_anchors": spec.get("rubric_anchors", {}),
        "instruments": spec.get("instruments", []),
        "regulators": spec.get("regulators", []),
        "jurisdictions": spec.get("jurisdictions", []),
    }
    if grounding:
        domain_spec["grounding"] = grounding
    doc = {
        "version": "domain-seed-0.1",
        "domain": domain_id,
        "_build": {
            "domain": domain_id,
            "scheme_pack": str(pack.relative_to(_ROOT)),
            "scheme_pack_format": pack_format,
            "seed_rows": len(rows),
            "kept": len(prompts),
            "dropped": {k: dropped[k] for k in sorted(dropped)},
            "max_prompt_chars": max_prompt_chars,
        },
        "_domain_spec": domain_spec,
        "prompts": prompts,
    }
    if grounding:
        doc["_grounding"] = grounding
    return doc


def _hermes_accepted() -> list[dict[str, Any]]:
    """OpenClaw-accepted Hermes proposals -- the vetted flywheel output for the supervised merge."""
    accepted = {r["id"] for r in _load_jsonl(OPENCLAW_VETTED) if r.get("accept") and r.get("id")}
    return [p for p in _load_jsonl(HERMES_PROPOSALS) if p.get("id") in accepted and p.get("text")]


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
            if per_category and kept >= per_category:   # per_category <= 0 -> unlimited (full draw)
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
          per_category_seed: int, per_category_hermes: int, max_prompt_chars: int,
          per_category_pretext: int = 0, per_category_multipath: int = 0,
          shuffle: bool = False) -> dict[str, Any]:
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
    add_pretext = _stratified(_load_jsonl(PRETEXT), "pretext", per_category_pretext,
                              seen_text, seen_id, rng)
    add_multipath = _stratified(_load_jsonl(MULTIPATH), "multipath", per_category_multipath,
                                seen_text, seen_id, rng)
    add_seed = _stratified(_seed_pool(max_prompt_chars), "seed", per_category_seed,
                          seen_text, seen_id, rng)
    add_hermes = _stratified(_hermes_accepted(), "hermes", per_category_hermes,
                            seen_text, seen_id, rng)
    merged = ([_norm(p, "scheme") for p in base] + add_exp + add_mc + add_pretext + add_multipath
              + add_seed + add_hermes)
    if shuffle:  # representative prefixes so a chunked full-registry sweep grades a random sample
        random.Random(SEED + 1).shuffle(merged)
    return {
        "version": "1.4",
        "_build": {"scheme": len(base), "expansion": len(add_exp), "major_case": len(add_mc),
                   "pretext": len(add_pretext), "multipath": len(add_multipath),
                   "seed_corpus": len(add_seed), "hermes_accepted": len(add_hermes),
                   "total": len(merged), "seed": SEED,
                   "per_category_expansion": per_category_expansion,
                   "per_category_majorcase": per_category_majorcase,
                   "per_category_pretext": per_category_pretext,
                   "per_category_multipath": per_category_multipath,
                   "per_category_seed": per_category_seed,
                   "per_category_hermes": per_category_hermes, "max_prompt_chars": max_prompt_chars},
        "prompts": merged,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-category-expansion", type=int, default=8)
    ap.add_argument("--per-category-majorcase", type=int, default=45)
    ap.add_argument("--per-category-pretext", type=int, default=0,
                    help="pretext-framed prompts per category (0 = all; 12 categories x 154 = 1848 total). "
                         "These target the measured third-party-wrapper framing gap.")
    ap.add_argument("--per-category-multipath", type=int, default=0,
                    help="multipath (3-stage chained) prompts per category (0 = all; 176 total). "
                         "These close the measured multipath coverage gap.")
    ap.add_argument("--per-category-seed", type=int, default=100)
    ap.add_argument("--per-category-hermes", type=int, default=100)
    ap.add_argument("--max-prompt-chars", type=int, default=6000)
    ap.add_argument("--full", action="store_true",
                    help="build the FULL prompt set: unlimited per-category draw from every source "
                         "(all gradeable seed prompts) for the exhaustive registry sweep; defaults "
                         "--out to a gitignored path")
    ap.add_argument("--out", default=None)
    ap.add_argument("--domain", default="trafficking",
                    help="registered benchmark domain id; trafficking uses the canonical widened promptset, "
                         "jsonl seed domains write a separate report promptset")
    args = ap.parse_args(argv)
    if args.domain != "trafficking":
        if args.full:
            ap.error("--full is only supported for the trafficking/default prompt set")
        if args.out is None:
            args.out = str(_domain_report_path(args.domain))
        doc = build_domain_promptset(args.domain, max_prompt_chars=args.max_prompt_chars)
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        ps = doc["prompts"]
        b = doc["_build"]
        print(f"wrote {args.out}: {len(ps)} prompts "
              f"(domain {args.domain}; seed_rows {b['seed_rows']}; dropped {b['dropped']})")
        print("difficulty:", dict(Counter(p["difficulty"] for p in ps)))
        print("distinct categories:", len({p["category"] for p in ps}))
        print("by source:", dict(Counter(p["source"] for p in ps)))
        return 0
    if args.full:
        for _k in ("per_category_expansion", "per_category_majorcase", "per_category_pretext",
                   "per_category_multipath", "per_category_seed", "per_category_hermes"):
            setattr(args, _k, 0)   # 0 -> unlimited (full draw)
    if args.out is None:
        args.out = str(FULL_OUT if args.full else SCHEME)
    doc = build(per_category_expansion=args.per_category_expansion,
                per_category_majorcase=args.per_category_majorcase,
                per_category_pretext=args.per_category_pretext,
                per_category_multipath=args.per_category_multipath,
                per_category_seed=args.per_category_seed,
                per_category_hermes=args.per_category_hermes,
                max_prompt_chars=args.max_prompt_chars,
                shuffle=args.full)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ps = doc["prompts"]
    b = doc["_build"]
    print(f"wrote {args.out}: {len(ps)} prompts "
          f"(scheme {b['scheme']} + expansion {b['expansion']} + major_case {b['major_case']} "
          f"+ pretext {b['pretext']} + multipath {b['multipath']} + seed_corpus {b['seed_corpus']} "
          f"+ hermes {b['hermes_accepted']})")
    print("difficulty:", dict(Counter(p["difficulty"] for p in ps)))
    print("distinct categories:", len({p["category"] for p in ps}))
    print("by source:", dict(Counter(p["source"] for p in ps)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
