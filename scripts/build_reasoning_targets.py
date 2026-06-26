#!/usr/bin/env python3
"""Reasoning-chain target builder -- gate + annotate distilled SFT targets on the
indicator -> statute -> graded-action -> resources chain.

A good migrant-worker-safety reply is NOT a bare refusal. It walks an explicit chain:

  1. INDICATOR  -- names the exploitation indicator (one of the ILO's 11 forced-labour indicators).
  2. STATUTE    -- cites the controlling law / ILO convention.
  3. ACTION     -- a clear graded decision: refuse to operationalize harm AND/OR tell the worker what
                   to do (keep copies, don't sign, don't pay, you are not obligated).
  4. RESOURCES  -- points to protective help (embassy, regulator, hotline, NGO, file a complaint).

This reads the distilled SFT targets (reports/training/sft.jsonl from build_lift_training_data.py),
deterministically detects which of the four chain links each teacher reply contains -- reusing the
project's own vocabulary (migrant_taxonomy ILO indicators + citation_accuracy + refusal_detector) --
scores chain completeness 0-4, ANNOTATES every row, and KEEPS only the targets that exemplify the
chain (>= --min-chain links). So the fine-tune learns to answer with details + citations + a concrete
action + resources, never "a refusal without details or citations".

Propose-only and additive: reads sft.jsonl, writes a SEPARATE reports/training/reasoning_sft.jsonl +
reasoning_manifest.json -- it never mutates or destroys the source set. Offline, deterministic (no
model, no network), so the curation is reproducible.

    python scripts/build_reasoning_targets.py --min-chain 3
    python scripts/build_reasoning_targets.py --validate     # print the manifest only, write nothing
Design: docs/research/training_regimes_and_systems.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
# Sibling scripts -- importable however this script is run or imported.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from citation_accuracy import citation_stats as _citation_stats  # noqa: E402
from refusal_detector import classify as _classify, FORMAT_FAILURE  # noqa: E402
try:
    from migrant_taxonomy import ILO_INDICATORS as _ILO  # canonical 11 forced-labour indicators
except Exception:  # noqa: BLE001 -- standalone without the taxonomy: fall back to the hardcoded set below
    _ILO = ()

SFT_IN = _ROOT / "reports" / "training" / "sft.jsonl"
OUT = _ROOT / "reports" / "training" / "reasoning_sft.jsonl"
MANIFEST = _ROOT / "reports" / "training" / "reasoning_manifest.json"
DEFAULT_MIN_CHAIN = 3   # of 4 links -- a target may miss at most one link (e.g. resources) and still teach

# INDICATOR: the canonical ILO 11 (as phrases) plus the colloquial phrasings a model actually emits.
_INDICATOR_TERMS = tuple(sorted({ind.replace("_", " ") for ind in _ILO} | {
    "abuse of vulnerability", "deception", "deceiv", "false promise", "restriction of movement",
    "freedom of movement", "confined", "kafala", "isolation", "physical", "sexual violence",
    "intimidat", "threat", "deport", "retention of", "passport", "identity document",
    "document confiscat", "confiscat", "withholding of wages", "withheld", "unpaid wage", "wage theft",
    "debt bondage", "bonded", "abusive conditions", "excessive overtime", "no rest day",
    "recruitment fee", "contract substitution", "forced labour", "forced labor", "coerc", "trafficking",
}))
# ACTION: a graded decision -- a refusal to operationalize harm, or concrete protective guidance/directive.
_ACTION_TERMS = (
    "cannot help", "can't help", "cannot assist", "can't assist", "won't help", "will not help",
    "unable to assist", "i will not", "i refuse", "refuse to", "decline to", "not obligated",
    "you are not required", "you have the right", "you should", "you should not", "do not sign",
    "don't sign", "do not agree", "keep copies", "keep a copy", "request a copy", "ask for a copy",
    "document everything", "gather evidence", "do not pay", "don't pay", "do not hand over",
    "never hand over", "do not give", "i recommend", "i'd recommend", "i would recommend",
    "it is advisable", "advisable to", "report this", "report it", "seek legal", "seek advice",
    "consult a", "insist on", "stop and",
)
# RESOURCES: where to get protective help (distinct terms; ILO/IOM excluded -- they read as statute cites).
_RESOURCE_TERMS = (
    "hotline", "helpline", "embassy", "consulate", "regulator", "labour office", "labor office",
    "authorities", "ngo", "file a complaint", "report to", "report it", "contact the", "contact a",
    "contact your", "national referral", "police", "trade union", "migrant resource",
    "support organization", "support organisation", "seek help", "reach out to",
)


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(term in low for term in terms)


def has_indicator(text: str) -> bool:
    """The reply names an exploitation indicator (ILO 11 or a colloquial equivalent)."""
    return _has_any(text, _INDICATOR_TERMS)


def has_statute(text: str) -> bool:
    """The reply cites a law: an ILO convention number or a statute section reference."""
    cs = _citation_stats(text)
    return cs.get("n_conventions", 0) > 0 or cs.get("n_section_refs", 0) > 0


def has_action(text: str) -> bool:
    """A graded decision: the reply isn't a format failure (empty/trace/too-short) and states a refusal
    or a directive. A grounded REFUSAL counts -- refusing to operationalize harm is the desired action
    (refusal_detector treats 'refusal' as context-dependent, NOT a format failure)."""
    _useful, reason = _classify(text)
    return reason not in FORMAT_FAILURE and _has_any(text, _ACTION_TERMS)


def has_resources(text: str) -> bool:
    """The reply points the worker to protective help."""
    return _has_any(text, _RESOURCE_TERMS)


def chain_links(text: str) -> dict[str, bool]:
    """{indicator, statute, action, resources} presence for one reply."""
    return {"indicator": has_indicator(text), "statute": has_statute(text),
            "action": has_action(text), "resources": has_resources(text)}


def _assistant_text(row: dict) -> str:
    """The assistant (teacher) reply from a chat-format SFT row (last assistant turn)."""
    return next((str(m.get("content", "")) for m in reversed(row.get("messages") or [])
                 if m.get("role") == "assistant"), "")


def build(rows: list[dict], *, min_chain: int = DEFAULT_MIN_CHAIN) -> dict[str, Any]:
    """Annotate each SFT row with its reasoning-chain links + completeness; keep those with
    >= ``min_chain`` of 4 links. Pure / offline. Returns {"rows", "manifest"}."""
    kept: list[dict] = []
    dist: Counter[int] = Counter()
    link_counts: Counter[str] = Counter()
    for r in rows:
        links = chain_links(_assistant_text(r))
        n = sum(links.values())
        dist[n] += 1
        for k, present in links.items():
            if present:
                link_counts[k] += 1
        if n >= min_chain:
            out = dict(r)
            meta = dict(out.get("_meta") or {})
            meta["chain_links"] = links
            meta["chain_completeness"] = n
            out["_meta"] = meta
            kept.append(out)
    manifest = {
        "input": len(rows), "kept": len(kept), "min_chain": min_chain,
        "completeness_distribution": {str(k): dist[k] for k in sorted(dist)},
        "link_presence": {k: link_counts.get(k, 0) for k in ("indicator", "statute", "action", "resources")},
        "note": ("additive curation of build_lift_training_data's sft.jsonl: keeps targets that exemplify "
                 "the indicator->statute->action->resources chain (>= min_chain of 4 links) so the fine-tune "
                 "learns details + citations + action + resources, never a bare refusal. Detectors reuse "
                 "migrant_taxonomy ILO indicators + citation_accuracy + refusal_detector; offline/deterministic."),
    }
    return {"rows": kept, "manifest": manifest}


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sft", type=pathlib.Path, default=SFT_IN, help="distilled SFT targets to curate")
    ap.add_argument("--min-chain", type=int, default=DEFAULT_MIN_CHAIN,
                    help="min of 4 chain links (indicator/statute/action/resources) to keep a target")
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--validate", action="store_true", help="print the manifest only; write nothing")
    args = ap.parse_args(argv)

    rows = _load_jsonl(args.sft)
    if not rows:
        print(f"[reasoning-targets] no SFT targets at {args.sft} -- run build_lift_training_data.py first")
        return 1
    doc = build(rows, min_chain=args.min_chain)
    m = doc["manifest"]
    if args.validate:
        print(json.dumps(m, indent=2))
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in doc["rows"]), encoding="utf-8")
    MANIFEST.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print(f"[reasoning-targets] {m['input']} targets -> kept {m['kept']} with >= {args.min_chain}/4 chain "
          f"links | links present: {m['link_presence']} | dist {m['completeness_distribution']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
