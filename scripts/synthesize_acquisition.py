"""Mine the staged acquisition corpus for TRENDS and synthesize MORE envelope
types (grep_rule detection patterns + context_snippet fee-euphemism facts), not
just rag_doc.

Reads reports/acquisition/staged_chunks.jsonl, runs the trend detectors +
novel-fee-euphemism miner against the existing known labels, and writes:
  - trend_report.json        -- which tactics appear, how often, novel euphemisms
  - synthesis_envelopes.jsonl -- grep_rule + context_snippet candidate envelopes

Propose-only: candidates for curator review, never auto-promoted. Env: ACQ_OUT.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in sorted((ROOT / "packages").glob("*/src")):
    sys.path.insert(0, str(_p))

from duecare.research_tools.synthesize import synthesize  # noqa: E402

OUT = Path(os.environ.get("ACQ_OUT", ROOT / "reports/acquisition"))


def _utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _known_fee_labels() -> set[str]:
    """Existing fee-camouflage euphemisms, so we only surface NOVEL ones."""
    try:
        from duecare.chat.harness import FEE_CAMOUFLAGE_LABELS  # noqa: E402
        if isinstance(FEE_CAMOUFLAGE_LABELS, dict):
            return {str(k).lower() for k in FEE_CAMOUFLAGE_LABELS}
        return {str(x).lower() for x in FEE_CAMOUFLAGE_LABELS}
    except Exception:
        return set()


def main() -> None:
    _utf8()
    staged = OUT / "staged_chunks.jsonl"
    if not staged.exists():
        print(f"[synth] no staged chunks at {staged} -- run acquisition first.", flush=True)
        return
    chunks = []
    with open(staged, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    chunks.append(json.loads(ln))
                except Exception:
                    pass

    known = _known_fee_labels()
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = synthesize(chunks, known_fee_labels=known, created_at=created_at)

    (OUT / "trend_report.json").write_text(json.dumps(out["report"], indent=2), encoding="utf-8")
    with open(OUT / "synthesis_envelopes.jsonl", "w", encoding="utf-8") as f:
        for env in out["envelopes"]:
            f.write(json.dumps(env, ensure_ascii=False) + "\n")

    rep = out["report"]
    print(f"[synth] scanned {rep['chunks_scanned']} chunks | known_fee_labels={len(known)}", flush=True)
    print("[synth] trend categories (chunks / distinct sources):", flush=True)
    for cat, d in rep["trend_categories"].items():
        print(f"          {cat:20s} {d['chunks']:5d} / {d['sources']:4d}  e.g. {d['example'][:70]!r}", flush=True)
    print(f"[synth] novel fee euphemisms (top): "
          f"{[l for l, _ in rep['novel_fee_euphemisms'][:15]]}", flush=True)
    print(f"[synth] DONE generated {rep['envelopes_generated']} candidate envelopes "
          f"({rep['grep_rules_generated']} grep_rule + {rep['fee_labels_generated']} context_snippet) "
          f"-> {OUT / 'synthesis_envelopes.jsonl'}", flush=True)


if __name__ == "__main__":
    main()
