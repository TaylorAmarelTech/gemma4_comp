"""Batch-vet candidate legal claims and APPEND the ones that pass into the corpus (build-upon, reweight).

Fast path for the enrichment loop, per Taylor "move faster, get results without stopping" + "build upon
and reweight when we have verification". Each candidate goes through the SAME guardrails + multi-prompt
convergence vet as legal_corpus_stage; a candidate that passes BOTH is APPENDED to
configs/duecare/legal_claims.json with verification_weight=0.6 and provenance="auto_vetted" -- clearly
BELOW the human-verified core (0.9), reweightable UP when a human verifies it. It is strictly append-only:
a duplicate id is HELD (never overwrites), so nothing existing is destroyed. No fine-tuning, no live board.

Run:
    python scripts/legal_corpus_promote.py --candidates <dir> --today 2026-07-10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from legal_claims import DEFAULT_PATH as CORPUS_PATH  # noqa: E402
from legal_claims import validate_schema  # noqa: E402
from legal_corpus_stage import convergence_vet, guardrail_check  # noqa: E402

AUTO_WEIGHT = 0.6            # auto-vetted (guardrails + convergence); human-verified core is 0.9
PROVENANCE = "auto_vetted_pending_human_verification"


def promote(candidates: list[dict], corpus: dict, *, caller=None, today=None) -> dict:
    """Vet each candidate (guardrails + convergence) against the CURRENT corpus and append the passers.
    Returns the mutated corpus + a per-candidate report. Append-only: duplicates are held, never overwritten."""
    claims = corpus.setdefault("claims", [])
    report = []
    for cand in candidates:
        existing = claims                                   # dup-check against the growing corpus
        g_ok, g_issues = guardrail_check(cand, existing)
        if not g_ok:
            report.append({"id": cand.get("id"), "action": "held", "reason": "; ".join(g_issues)})
            continue
        c_ok, votes = convergence_vet(cand, caller=caller)
        if not c_ok:
            report.append({"id": cand.get("id"), "action": "held", "reason": f"convergence HOLD votes={votes}"})
            continue
        enriched = {**cand, "verification_weight": AUTO_WEIGHT, "provenance": PROVENANCE,
                    "supersedes": cand.get("supersedes"), "superseded_by": cand.get("superseded_by")}
        claims.append(enriched)
        report.append({"id": cand.get("id"), "action": "appended", "verification_weight": AUTO_WEIGHT,
                       "convergence_votes": votes})
    return {"corpus": corpus, "report": report}


def _load_candidates(path: Path) -> list[dict]:
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Batch-vet + append candidate legal claims (append-only, reweighted).")
    ap.add_argument("--candidates", type=Path, required=True, help="a candidate JSON file or a directory of them")
    ap.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    ap.add_argument("--model", default="mistral:mistral-small-latest")
    args = ap.parse_args(argv)
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    before = len(corpus.get("claims", []))
    cands = _load_candidates(args.candidates)
    out = promote(cands, corpus)
    # validate the WHOLE corpus before writing -- never persist a malformed claim
    errs = validate_schema(out["corpus"]["claims"])
    if errs:
        print("ABORT: appended claims break schema:")
        for e in errs[:10]:
            print("  -", e)
        return 1
    args.corpus.write_text(json.dumps(out["corpus"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for r in out["report"]:
        print(f"  {r['action']:9s} {r['id']}" + (f"  ({r['reason']})" if r.get("reason") else
              f"  weight={r.get('verification_weight')} votes={r.get('convergence_votes')}"))
    appended = sum(1 for r in out["report"] if r["action"] == "appended")
    print(f"\ncorpus {before} -> {len(out['corpus']['claims'])} claims ({appended} appended, "
          f"auto_vetted weight {AUTO_WEIGHT}; human-verify to raise). append-only; nothing overwritten.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
