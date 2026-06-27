#!/usr/bin/env python3
"""Contract-derived DPO pairs -- minimal-pair HARD NEGATIVES that teach a model to prefer the complete
reasoning chain, targeting the two weak links (statute, action).

Our existing DPO set (build_lift_training_data.py) pairs chosen=harnessed vs rejected=baseline -- a broad
"harness vs bare" preference. This builds a SHARPER signal: from a gold trace that satisfies the reasoning
contract (reasoning_contract.py), construct the rejected by ABLATING exactly one chain link -- delete the
sentence(s) that carry the statute citation, or the protective action -- leaving everything else identical.

    chosen   = full gold trace (indicator + statute + action + resources)
    rejected = same trace MINUS the statute sentence   (or MINUS the action sentence)

So the only difference between chosen and rejected is the presence of the link we want the model to never
drop. That isolates the exact behaviour the board says is weakest (statute 76% / action 75% chain
presence) into a clean contrastive pair. The rejected is synthetic-by-DELETION only -- no fabricated
content is introduced (safe for a safety model); the contract verifier confirms the ablation actually
removed the link (chosen has it, rejected does not) so every pair is a genuine, clean contrast.

Propose-only + offline + deterministic: reads reports/training/reasoning_sft.jsonl, writes a SEPARATE
reports/training/contract_dpo.jsonl (+ manifest). No model, no network, no credits.

    python scripts/build_contract_dpo.py                 # build pairs over the gold reasoning set
    python scripts/build_contract_dpo.py --links statute # only the statute hard-negatives
Design: docs/research/training_methodology.md (reasoning contract)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))   # sibling-script imports
from reasoning_contract import verify_reasoning  # noqa: E402
from build_reasoning_targets import has_statute, _has_any, _ACTION_TERMS  # noqa: E402

REASONING_SFT = _ROOT / "reports" / "training" / "reasoning_sft.jsonl"
OUT = _ROOT / "reports" / "training" / "contract_dpo.jsonl"
MANIFEST = _ROOT / "reports" / "training" / "contract_dpo_manifest.json"
ABLATABLE = ("statute", "action")   # the two weak, sentence-localised links

# Split into sentences but DON'T break on the "No." in "ILO Convention No. 29" (next char is a digit, not
# an uppercase letter / quote), so a citation sentence stays intact and is ablated as one unit.
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z"“])')


def _sentences(text: str) -> list[str]:
    return [s for s in _SENT_SPLIT.split(text.strip()) if s.strip()]


def _carries(sentence: str, link: str) -> bool:
    if link == "statute":
        return has_statute(sentence)
    if link == "action":
        return _has_any(sentence, _ACTION_TERMS)
    raise ValueError(f"unsupported ablation link: {link}")


def ablate_link(text: str, link: str) -> "str | None":
    """Drop the sentence(s) carrying ``link`` from ``text``. Returns the reduced text only if at least one
    sentence was removed AND the link is genuinely gone from the result (a clean removal); else None."""
    sents = _sentences(text)
    kept = [s for s in sents if not _carries(s, link)]
    if len(kept) == len(sents) or not kept:
        return None                                   # nothing carried the link, or it was the whole reply
    reduced = " ".join(kept)
    return reduced if not _carries(reduced, link) else None


def _user_text(row: dict) -> str:
    return next((str(m.get("content", "")) for m in (row.get("messages") or [])
                if m.get("role") == "user"), "")


def _assistant_text(row: dict) -> str:
    return next((str(m.get("content", "")) for m in reversed(row.get("messages") or [])
                if m.get("role") == "assistant"), "")


def build_pairs(rows: list[dict], *, links: tuple[str, ...] = ABLATABLE, min_steps: int = 4) -> dict[str, Any]:
    """For each gold trace that satisfies the contract, emit one hard-negative DPO pair per ablatable link
    that is present (chosen=full, rejected=trace minus that link). Pure / offline."""
    pairs: list[dict] = []
    by_link: Counter[str] = Counter()
    n_eligible = 0
    for r in rows:
        chosen = _assistant_text(r)
        prompt = _user_text(r)
        if not chosen or not prompt:
            continue
        v = verify_reasoning(chosen, min_steps=min_steps)
        if not v.satisfied:
            continue                                  # only ablate from clean, full-chain gold traces
        n_eligible += 1
        pid = (r.get("_meta") or {}).get("prompt_id")
        for link in links:
            if not v.steps.get(link):
                continue
            rejected = ablate_link(chosen, link)
            if rejected is None or rejected.strip() == chosen.strip():
                continue
            rv = verify_reasoning(rejected, min_steps=min_steps)
            pairs.append({
                "prompt": prompt, "chosen": chosen, "rejected": rejected,
                "_meta": {"prompt_id": pid, "ablated_link": link, "source": "contract_ablation",
                          "chain_chosen": v.n_steps, "chain_rejected": rv.n_steps},
            })
            by_link[link] += 1
    manifest = {
        "input": len(rows), "eligible_gold": n_eligible, "pairs": len(pairs),
        "min_steps": min_steps, "by_ablated_link": dict(by_link),
        "note": ("contract-derived hard-negative DPO: chosen = a contract-satisfying gold trace, rejected = "
                 "the same trace with the statute or action sentence(s) deleted (verified gone). Isolates the "
                 "weakest chain links (statute/action) into minimal contrastive pairs; rejected is "
                 "deletion-only (no fabricated content). Offline/deterministic; reuses reasoning_contract."),
    }
    return {"pairs": pairs, "manifest": manifest}


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
    ap.add_argument("--sft", type=pathlib.Path, default=REASONING_SFT, help="gold reasoning traces")
    ap.add_argument("--links", nargs="+", default=list(ABLATABLE), choices=list(ABLATABLE),
                    help="which chain links to ablate into hard negatives")
    ap.add_argument("--min-steps", type=int, default=4, help="contract strictness for an eligible gold trace")
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--validate", action="store_true", help="print the manifest only; write nothing")
    args = ap.parse_args(argv)

    rows = _load_jsonl(args.sft)
    if not rows:
        print(f"[contract-dpo] no reasoning traces at {args.sft} -- run build_reasoning_targets.py first")
        return 1
    doc = build_pairs(rows, links=tuple(args.links), min_steps=args.min_steps)
    m = doc["manifest"]
    if args.validate:
        print(json.dumps(m, indent=2))
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in doc["pairs"]), encoding="utf-8")
    MANIFEST.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print(f"[contract-dpo] {m['eligible_gold']} eligible gold traces -> {m['pairs']} hard-negative pairs "
          f"{m['by_ablated_link']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
