#!/usr/bin/env python3
"""Promote PH DMW agency representatives to individual entities.

The DMW licensed-recruitment-agency records each name a *representative* -- the
licensed individual responsible for the agency -- which browser_scrape already
captures into the record's notes as ``rep: <NAME>``. This script lifts those into
their own ``individual`` entity records so the screening engine can answer
"is this PERSON a licensed agency representative, and are their agencies in good
standing?" -- not just "is this COMPANY licensed?".

A person can represent several agencies, so reps are de-duplicated by name and
their agencies aggregated; status is ``active`` if any represented agency holds a
valid licence, else ``inactive`` (a flag-worthy signal).

These are named individuals from a PUBLIC government licensing register
(transparency data, published by the DMW), and the output is written to the
gitignored reports/ tree -- the script and its tests embed no real names. Maps
the ``rep:`` notes left by scripts/browser_scrape.py::_dmw_item_to_record.

Usage:
    python scripts/dmw_representatives.py            # read staged DMW + write individuals
    python scripts/dmw_representatives.py --in path.jsonl --out path.jsonl
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_IN = _ROOT / "reports" / "entity_kb" / "dmw_lra.jsonl"
_DEFAULT_OUT = _ROOT / "reports" / "entity_kb" / "dmw_representatives.jsonl"

_REP_RE = re.compile(r"rep:\s*([^;]+)", re.I)


def parse_rep(notes: str) -> str:
    """Extract the representative name from a DMW record's notes ('' if none)."""
    m = _REP_RE.search(notes or "")
    return m.group(1).strip() if m else ""


def agency_records_to_individuals(records: list[dict]) -> list[dict]:
    """Aggregate agency records into de-duplicated individual-representative entities."""
    by_name: dict[str, dict] = {}
    for r in records:
        rep = parse_rep(r.get("notes", ""))
        if not rep:
            continue
        key = rep.upper()
        e = by_name.setdefault(key, {"name": rep, "agencies": [], "any_valid": False})
        agency = r.get("name", "")
        if agency:
            e["agencies"].append(agency)
        if "valid" in str(r.get("status", "")).lower():
            e["any_valid"] = True

    out = []
    for e in by_name.values():
        ags = e["agencies"]
        plural = "agency" if len(ags) == 1 else "agencies"
        shown = "; ".join(ags[:5]) + (" ..." if len(ags) > 5 else "")
        out.append({
            "entity_type": "individual", "name": e["name"], "jurisdiction": "PH",
            "status": "active" if e["any_valid"] else "inactive",
            "sector": "labour_recruitment", "role": "agency_representative",
            "source": "PH DMW licensed recruitment agency - representative",
            "source_tier": "official",
            "notes": f"Licensed representative of {len(ags)} PH recruitment {plural}: {shown}",
        })
    return out


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", type=Path, default=_DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    args = ap.parse_args(argv)

    records = load_records(args.inp)
    if not records:
        print(f"no DMW records at {args.inp} (run: python scripts/harvest.py --collectors dmw_agencies)",
              file=sys.stderr)
        return 1
    individuals = agency_records_to_individuals(records)

    ekb_spec = importlib.util.spec_from_file_location(
        "dc_entity_kb_for_dmwrep", str(_ROOT / "scripts" / "entity_kb.py"))
    ekb = importlib.util.module_from_spec(ekb_spec)
    sys.modules[ekb_spec.name] = ekb
    ekb_spec.loader.exec_module(ekb)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    ekb.save_entities(args.out, ekb.merge_entities([ekb.record_from_dict(e) for e in individuals]))

    active = sum(1 for e in individuals if e["status"] == "active")
    print(f"DMW representatives: {len(individuals)} individuals ({active} active, "
          f"{len(individuals) - active} inactive) -> {args.out}", file=sys.stderr)
    return 0 if individuals else 1


if __name__ == "__main__":
    raise SystemExit(main())
