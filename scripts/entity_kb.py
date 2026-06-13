#!/usr/bin/env python3
"""Migration-world entity knowledge base.

A generalized, propose-only store for the entities a migrant-worker
investigator needs to know about across the whole recruitment lifecycle --
recruitment / manning agencies, employers / sponsors, accredited medical
clinics, training centers, brokers, lenders, sanctioned / debarred entities,
regulators, NGOs, and hotlines. It is the destination database the recruitment
pipeline feeds: the scrapers (scrape_agency_sources, extract_agency_facts) and
the scheduled monitor produce records; this module dedupes, merges by
provenance tier, and answers queries.

Real-not-faked: records carry their `source` + `source_tier` + `fetched_at`,
and the committed default store is a clearly-labelled SYNTHETIC sample. Real
records are the operator's, ingested from official public sources and staged
propose-only (reports/entity_kb/, gitignored). This module fabricates nothing.

Merge policy: two records with the same (entity_type, normalized name,
jurisdiction) are the same entity. On merge, the higher-tier source
(official > secondary > community) wins scalar fields; list fields (phones,
aliases, sources) union.

Usage:
    python scripts/entity_kb.py --stats
    python scripts/entity_kb.py --query --type medical_clinic --jurisdiction PH
    python scripts/entity_kb.py --query --name "sunrise" --status cancelled

    # ingest a scraper export (propose-only). The scrapers emit {"records": [...]}
    # of AgencyProfile dicts; --as sets the type and --jurisdiction/--corridor/
    # --sector stamp the origin a regulator export leaves implicit:
    python scripts/scrape_agency_sources.py --from-html dmw_list.html      # -> reports/agency_registry/scraped.json
    python scripts/entity_kb.py --ingest reports/agency_registry/scraped.json \
        --as recruitment_agency --jurisdiction PH --out reports/entity_kb/ph_agencies.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = _ROOT / "data" / "entity_kb" / "sample_entities.jsonl"

# Entity types across the migration lifecycle.
ENTITY_TYPES = (
    "recruitment_agency",   # licensed land-based recruiter
    "manning_agency",       # seabased / crewing agency
    "employer",             # foreign principal / sponsor / household
    "medical_clinic",       # pre-deployment / GAMCA medical facility
    "training_center",      # TESDA-style skills / orientation center
    "broker",               # sub-agent / illegal recruiter / fixer
    "lender",               # salary-loan / placement-fee financier
    "sanctioned_entity",    # debarred / blacklisted / watch-listed
    "regulator",            # govt labour / migration authority
    "ngo",                  # civil-society support org
    "hotline",              # helpline / reporting contact
)

# Source provenance tiers (governs merge precedence).
TIER_OFFICIAL = "official"      # govt registry / regulator publication
TIER_SECONDARY = "secondary"    # IGO/NGO/press with editorial standards
TIER_COMMUNITY = "community"    # field reports, opt-in submissions
_TIER_RANK = {TIER_OFFICIAL: 3, TIER_SECONDARY: 2, TIER_COMMUNITY: 1, "": 0}

_STATUS_MAP = {
    "valid": "valid", "active": "valid", "licensed": "valid", "accredited": "valid",
    "good standing": "valid", "in good standing": "valid",
    "expired": "expired", "lapsed": "expired",
    "cancelled": "cancelled", "canceled": "cancelled", "revoked": "cancelled",
    "delisted": "delisted", "banned": "delisted", "blacklisted": "delisted",
    "debarred": "delisted", "suspended": "suspended",
    "watchlisted": "watchlisted", "sanctioned": "watchlisted",
}

# Strip ONLY legal-form suffixes + punctuation when building the merge key.
# Industry words (overseas, manpower, recruitment, medical, diagnostics, ...)
# are deliberately KEPT: they distinguish genuinely different entities, and for
# a watchlist a false split (two records to review) is far safer than a false
# merge (a clean agency collapsed into a flagged one).
_SUFFIXES = re.compile(
    r"\b(incorporated|inc|corporation|corp|company|co|limited|ltd|"
    r"llc|llp|plc|pte|pvt|sdn|bhd|gmbh)\b", re.I)


def normalize_name(name: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    s = _SUFFIXES.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_status(raw: str) -> str:
    return _STATUS_MAP.get((raw or "").strip().lower(), (raw or "").strip().lower() or "unknown")


def normalize_type(raw: str) -> str:
    t = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    if t in ENTITY_TYPES:
        return t
    if t in {"agent", "subagent", "sub_agent", "fixer"}:
        return "broker"
    return t


@dataclass(frozen=True)
class EntityRecord:
    entity_type: str
    name: str
    jurisdiction: str = ""          # ISO-ish country code (PH, HK, SA, ...)
    corridor: str = ""              # e.g. PH-HK
    sector: str = ""                # domestic_work / construction / fishing / healthcare
    license_no: str = ""
    status: str = "unknown"
    status_as_of: str = ""          # YYYY-MM-DD
    address: str = ""
    phones: tuple[str, ...] = ()
    email: str = ""
    website: str = ""
    aliases: tuple[str, ...] = ()
    source: str = ""                # provenance: registry / url / export name
    source_tier: str = TIER_COMMUNITY
    fetched_at: str = ""            # YYYY-MM-DD
    confidence: float = 0.5
    notes: str = ""

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.entity_type, normalize_name(self.name), self.jurisdiction.upper())


def record_from_dict(d: dict, *, default_type: str = "") -> EntityRecord:
    def first(*keys, default=""):
        for k in keys:
            if d.get(k) not in (None, ""):
                return d[k]
        return default

    phones = d.get("phones") or d.get("phone") or []
    if isinstance(phones, str):
        phones = [p.strip() for p in re.split(r"[;,/]", phones) if p.strip()]
    aliases = d.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [a.strip() for a in re.split(r"[;,/]", aliases) if a.strip()]
    try:
        confidence = max(0.0, min(1.0, float(d.get("confidence", 0.5))))
    except Exception:
        confidence = 0.5
    return EntityRecord(
        entity_type=normalize_type(str(first("entity_type", "type", default=default_type))),
        name=str(first("name", "agency_name", "company_name")),
        jurisdiction=str(first("jurisdiction", "country", "region")).upper()[:8],
        corridor=str(first("corridor")),
        sector=str(first("sector")),
        license_no=str(first("license_no", "license", "licence_no", "accreditation_no", "poea_no")),
        status=normalize_status(str(first("status", "license_status", default="unknown"))),
        status_as_of=str(first("status_as_of", "as_of")),
        address=str(first("address", "office_address")),
        phones=tuple(str(p) for p in phones),
        email=str(first("email", "official_email")),
        website=str(first("website", "url")),
        aliases=tuple(str(a) for a in aliases),
        source=str(first("source", "official_source")),
        source_tier=str(first("source_tier", default=TIER_COMMUNITY)),
        fetched_at=str(first("fetched_at")),
        confidence=confidence,
        notes=str(first("notes")),
    )


def _merge_two(a: EntityRecord, b: EntityRecord) -> EntityRecord:
    """Merge two records for the same entity. Higher-tier source wins scalars;
    list fields union; confidence is the max."""
    hi, lo = (a, b) if _TIER_RANK.get(a.source_tier, 0) >= _TIER_RANK.get(b.source_tier, 0) else (b, a)

    def pick(field_name):
        return getattr(hi, field_name) or getattr(lo, field_name)

    phones = tuple(dict.fromkeys([*a.phones, *b.phones]))
    # Keep the lower-tier RAW surface form as an alias when it differs literally
    # (e.g. "Blue Horizon Crewing" vs "...Crewing Inc."), so search still finds
    # the variant even though both collapse to the same merge key.
    extra_alias = (lo.name,) if lo.name and lo.name != hi.name else ()
    aliases = tuple(dict.fromkeys([*a.aliases, *b.aliases, *extra_alias]))
    sources = " | ".join(dict.fromkeys(s for s in (hi.source, lo.source) if s))
    return replace(
        hi,
        corridor=pick("corridor"), sector=pick("sector"), license_no=pick("license_no"),
        status_as_of=pick("status_as_of"), address=pick("address"), email=pick("email"),
        website=pick("website"), notes=pick("notes"),
        phones=phones, aliases=aliases, source=sources,
        confidence=max(a.confidence, b.confidence),
    )


def merge_entities(records: list[EntityRecord]) -> list[EntityRecord]:
    """Dedupe + merge records by (type, normalized name, jurisdiction)."""
    by_key: dict[tuple, EntityRecord] = {}
    for rec in records:
        if not rec.name.strip():
            continue
        by_key[rec.key] = _merge_two(by_key[rec.key], rec) if rec.key in by_key else rec
    return list(by_key.values())


def load_entities(path: Path | str = DEFAULT_STORE) -> list[EntityRecord]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[EntityRecord] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "//")):
            continue
        try:
            out.append(record_from_dict(json.loads(line)))
        except Exception:
            continue
    return out


def save_entities(path: Path | str, records: list[EntityRecord]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for rec in sorted(records, key=lambda r: (r.entity_type, r.jurisdiction, normalize_name(r.name))):
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")


def query_entities(records: list[EntityRecord], *, entity_type: str = "",
                   jurisdiction: str = "", name: str = "", status: str = "",
                   sector: str = "") -> list[EntityRecord]:
    nq = normalize_name(name) if name else ""
    out = []
    for r in records:
        if entity_type and r.entity_type != normalize_type(entity_type):
            continue
        if jurisdiction and r.jurisdiction.upper() != jurisdiction.upper():
            continue
        if status and r.status != normalize_status(status):
            continue
        if sector and sector.lower() not in r.sector.lower():
            continue
        if nq and nq not in normalize_name(r.name) and not any(nq in normalize_name(a) for a in r.aliases):
            continue
        out.append(r)
    return out


def stats(records: list[EntityRecord]) -> dict:
    from collections import Counter
    return {
        "n_entities": len(records),
        "by_type": dict(Counter(r.entity_type for r in records)),
        "by_jurisdiction": dict(Counter(r.jurisdiction for r in records if r.jurisdiction)),
        "by_status": dict(Counter(r.status for r in records)),
        "by_source_tier": dict(Counter(r.source_tier for r in records)),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store", default=str(DEFAULT_STORE), help="entity JSONL store")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--query", action="store_true")
    ap.add_argument("--type", default="", help="filter by entity_type")
    ap.add_argument("--jurisdiction", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--status", default="")
    ap.add_argument("--sector", default="")
    ap.add_argument("--ingest", help="merge records from a scraper JSON/JSONL into the store (propose-only)")
    ap.add_argument("--as", dest="as_type", default="", help="default entity_type for --ingest records")
    ap.add_argument("--corridor", default="", help="stamp corridor on --ingest records lacking one (e.g. PH-SA)")
    ap.add_argument("--source-tier", default="", choices=["", TIER_OFFICIAL, TIER_SECONDARY, TIER_COMMUNITY],
                    help="stamp provenance tier on --ingest records (e.g. official for a govt registry)")
    ap.add_argument("--out", default="", help="where --ingest writes (default: propose-only staging)")
    args = ap.parse_args(argv)

    records = load_entities(args.store)

    if args.ingest:
        raw = json.loads(Path(args.ingest).read_text(encoding="utf-8"))
        items = raw.get("records", raw) if isinstance(raw, dict) else raw
        # Origin stamps: scraper exports (e.g. a PH DMW list) carry a sub-region,
        # not a country, and no entity_type. With --query these flags filter; with
        # --ingest they LABEL the source (each record's own value still wins).
        stamps = {k: v for k, v in (("jurisdiction", args.jurisdiction),
                                    ("sector", args.sector), ("corridor", args.corridor),
                                    ("source_tier", args.source_tier)) if v}
        new = [record_from_dict({**stamps, **d}, default_type=args.as_type) for d in items]
        merged = merge_entities([*records, *new])
        out = Path(args.out) if args.out else (_ROOT / "reports" / "entity_kb" / "staged.jsonl")
        save_entities(out, merged)
        print(json.dumps({"ingested": len(new), "total_after_merge": len(merged),
                          "staged_to": str(out)}, indent=2))
        return 0

    if args.query:
        hits = query_entities(records, entity_type=args.type, jurisdiction=args.jurisdiction,
                              name=args.name, status=args.status, sector=args.sector)
        print(json.dumps([asdict(r) for r in hits], indent=2, ensure_ascii=False))
        return 0

    # default: stats
    print(json.dumps(stats(records), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
