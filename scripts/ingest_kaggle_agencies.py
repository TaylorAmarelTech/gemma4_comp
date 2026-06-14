#!/usr/bin/env python3
"""Ingest the operator's published Kaggle agency datasets into the entity KB.

The author already scraped + published the DMW data on Kaggle, richer than a
live pull:
  * taylorsamarel/philippines-employment-agency-database  (~7,500 agencies x 20)
  * taylorsamarel/philippines-employment-agency-data       (~3,732 agencies x 15)
  * taylorsamarel/philippines-employment-agency-job-order-database (~24,000 job
    orders x 19) -- which name the FOREIGN PRINCIPALS/EMPLOYERS, a whole entity
    type the registry pull does not give.

This maps those CSV exports into EntityRecord rows (recruitment agencies from the
agency files; EMPLOYERS from the job-order PRINCIPALNAME column, with the
destination JOBSITE as the corridor), dedups/merges via entity_kb, and stages
the result propose-only. Download the CSVs first with the Kaggle API (see
--help); this tool only reads local CSVs, so it is fully offline + testable.

Usage:
    # after `kaggle datasets download -d taylorsamarel/...-database --unzip`
    python scripts/ingest_kaggle_agencies.py \
        --agencies reports/kaggle_datasets/agency-db/*.csv \
        --job-orders reports/kaggle_datasets/job-orders/*.csv \
        --out reports/entity_kb/kaggle_entities.jsonl
"""
from __future__ import annotations

import argparse
import csv
import glob
import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_entity_kb():
    spec = importlib.util.spec_from_file_location(
        "dc_entity_kb_for_kaggle", str(_ROOT / "scripts" / "entity_kb.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # frozen-dataclass exec needs registration
    spec.loader.exec_module(mod)
    return mod


# destination jobsite -> ISO-ish code (best effort; unknown -> first token upper)
_JOBSITE_CC = {
    "saudi arabia": "SA", "ksa": "SA", "united arab emirates": "AE", "uae": "AE", "u.a.e.": "AE",
    "qatar": "QA", "kuwait": "KW", "bahrain": "BH", "oman": "OM", "hong kong": "HK", "hongkong": "HK",
    "taiwan": "TW", "japan": "JP", "south korea": "KR", "korea": "KR", "singapore": "SG",
    "malaysia": "MY", "canada": "CA", "italy": "IT", "israel": "IL", "poland": "PL", "cyprus": "CY",
    "united kingdom": "GB", "united states": "US", "usa": "US", "u.s.a.": "US", "brunei": "BN",
    "macau": "MO", "macao": "MO", "lebanon": "LB", "jordan": "JO", "papua new guinea": "PG",
    "maldives": "MV", "guam": "GU", "germany": "DE",
}


def _country_code(jobsite: str) -> str:
    s = (jobsite or "").strip().lower()
    if s in _JOBSITE_CC:
        return _JOBSITE_CC[s]
    return (jobsite or "").strip()[:16]


def _first(row: dict, *keys: str) -> str:
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            return str(v).strip()
    return ""


def agency_csv_to_records(path: str, *, source: str = "") -> list[dict]:
    """Map a DMW agency CSV export to recruitment_agency entity dicts."""
    src = source or f"Kaggle: {Path(path).name}"
    out = []
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            name = _first(row, "Agency", "AgencyName", "name")
            if not name:
                continue
            addr = ", ".join(x for x in (
                _first(row, "AgencyAddress", "address"),
                _first(row, "MunicipalityCity", "Municipality"),
                _first(row, "CityProvince")) if x)
            rep = _first(row, "Representative")
            out.append({
                "entity_type": "recruitment_agency", "name": name, "jurisdiction": "PH",
                "status": _first(row, "LicenseStatus", "status") or "unknown",
                "status_as_of": _first(row, "DataAsOf", "LicenseStatusDate")[:10],
                "address": addr, "phones": _first(row, "ContactNo", "phone"),
                "email": _first(row, "eMail", "email"), "website": _first(row, "Website"),
                "sector": _first(row, "AgencyClassification"), "source": src,
                "source_tier": "official",  # DMW-derived
                "notes": (f"rep: {rep}" if rep else ""),
            })
    return out


def joborder_csv_to_entities(path: str, *, source: str = "") -> tuple[list[dict], list[dict]]:
    """Map a DMW job-order CSV to EMPLOYER entity dicts (from PRINCIPALNAME) +
    a list of agency->principal->jobsite->position relationships."""
    src = source or f"Kaggle: {Path(path).name}"
    employers: dict[str, dict] = {}
    relationships = []
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            principal = _first(row, "PRINCIPALNAME", "PrincipalName")
            jobsite = _first(row, "JOBSITE", "Jobsite")
            agency = _first(row, "AGENCY", "Agency")
            position = _first(row, "POSITION", "Position")
            cc = _country_code(jobsite)
            if principal:
                key = principal.lower()
                if key not in employers:
                    employers[key] = {
                        "entity_type": "employer", "name": principal,
                        "jurisdiction": cc, "corridor": f"PH-{cc}" if cc else "",
                        "source": src, "source_tier": "secondary",
                        "notes": f"foreign principal; jobsite {jobsite}"[:160],
                    }
            if principal or agency:
                relationships.append({"agency": agency, "principal": principal,
                                      "jobsite": jobsite, "position": position})
    return list(employers.values()), relationships


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agencies", nargs="*", default=[], help="agency CSV path(s) / globs")
    ap.add_argument("--job-orders", nargs="*", default=[], help="job-order CSV path(s) / globs")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "entity_kb" / "kaggle_entities.jsonl"))
    ap.add_argument("--rel-out", default=str(_ROOT / "reports" / "entity_kb" / "kaggle_job_order_relationships.jsonl"))
    args = ap.parse_args(argv)

    ekb = _load_entity_kb()

    def expand(globs):
        out = []
        for g in globs:
            out.extend(sorted(glob.glob(g)))
        return out

    raw: list[dict] = []
    for p in expand(args.agencies):
        recs = agency_csv_to_records(p)
        raw.extend(recs)
        print(f"agencies: {len(recs)} from {Path(p).name}", file=sys.stderr)
    rels = []
    for p in expand(args.job_orders):
        emps, r = joborder_csv_to_entities(p)
        raw.extend(emps)
        rels.extend(r)
        print(f"job-orders: {len(emps)} unique employers + {len(r)} relationships from {Path(p).name}",
              file=sys.stderr)

    records = [ekb.record_from_dict(d) for d in raw]
    merged = ekb.merge_entities(records)
    ekb.save_entities(args.out, merged)
    print(f"\nmerged -> {len(merged)} entities -> {args.out}", file=sys.stderr)
    from collections import Counter
    print("by_type:", dict(Counter(r.entity_type for r in merged)), file=sys.stderr)
    print("by_status:", dict(Counter(r.status for r in merged)), file=sys.stderr)

    if rels:
        import json
        rel_path = Path(args.rel_out)
        rel_path.parent.mkdir(parents=True, exist_ok=True)
        with rel_path.open("w", encoding="utf-8") as f:
            for r in rels:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{len(rels)} job-order relationships -> {rel_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
