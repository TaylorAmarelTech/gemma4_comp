"""Pull candidates from diverse source connectors (GDELT news + ReliefWeb reports)
and write them as a candidates file the acquisition runner stages.

Two-step, DRY: this generates ``connector_candidates.jsonl`` (url-only candidates
for GDELT -> acquire fetches them; text-carrying for ReliefWeb -> acquire skips the
fetch), then:

    ACQ_CANDIDATES=reports/acquisition/connector_candidates.jsonl \\
    ACQ_OUT=reports/acquisition python scripts/run_acquisition.py

routes them through the same store-backed, polite, gated pipeline.

Env: CONN_QUERY, CONN_TIMESPAN (days), CONN_GDELT_MAX, CONN_RW_LIMIT,
CONN_SOURCES (csv of gdelt,reliefweb), CONN_OUT.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in sorted((ROOT / "packages").glob("*/src")):
    sys.path.insert(0, str(_p))

from duecare.research_tools.connectors import (  # noqa: E402
    DEFAULT_QUERY, gdelt_candidates, reliefweb_documents,
)

QUERY = os.environ.get("CONN_QUERY", DEFAULT_QUERY)
TIMESPAN = int(os.environ.get("CONN_TIMESPAN", "30"))
GDELT_MAX = int(os.environ.get("CONN_GDELT_MAX", "100"))
RW_LIMIT = int(os.environ.get("CONN_RW_LIMIT", "75"))
SOURCES = [s.strip() for s in os.environ.get("CONN_SOURCES", "gdelt,reliefweb").split(",") if s.strip()]
OUT = Path(os.environ.get("CONN_OUT", ROOT / "reports/acquisition/connector_candidates.jsonl"))


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"[connectors] query={QUERY!r} sources={SOURCES} timespan={TIMESPAN}d", flush=True)

    candidates: list[dict] = []
    if "gdelt" in SOURCES:
        g = gdelt_candidates(QUERY, timespan_days=TIMESPAN, max_records=GDELT_MAX,
                             signals=["news", "trafficking"])
        print(f"[connectors] gdelt -> {len(g)} news url candidates", flush=True)
        candidates.extend(g)
    if "reliefweb" in SOURCES:
        r = reliefweb_documents(QUERY, limit=RW_LIMIT, signals=["ngo_report", "trafficking"])
        print(f"[connectors] reliefweb -> {len(r)} report documents (with body)", flush=True)
        candidates.extend(r)

    with open(OUT, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    n_text = sum(1 for c in candidates if c.get("text"))
    print(f"[connectors] DONE wrote {len(candidates)} candidates "
          f"({n_text} text-carrying, {len(candidates) - n_text} url-only) -> {OUT}", flush=True)
    print(f"[connectors] next: ACQ_CANDIDATES={OUT} ACQ_OUT={OUT.parent} "
          f"python scripts/run_acquisition.py", flush=True)


if __name__ == "__main__":
    main()
