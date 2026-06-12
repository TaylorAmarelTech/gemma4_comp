#!/usr/bin/env python3
"""Licensed-recruitment-agency verification registry.

The protective inverse of a "suspicious recruiter" scan: given an agency name
(and optionally a claimed licence number) from a job ad or recruiter message,
check it against a registry of OFFICIALLY LICENSED agencies and return a
legitimacy verdict. A worker's first question is "is this agency real?" — an
unlicensed agency claiming a licence, or a CANCELLED/DELISTED one still
advertising, is a strong exploitation red flag (it pairs with the GREP rule
`licensed_agency_chop_passthrough`).

Source of truth: an official regulator export. The seed/demo registry is the
Philippine DMW "Licensed Recruitment Agencies" inquiry
(https://dmw.gov.ph/inquiry/licensed-recruitment-agencies). This tool is
SOURCE-AGNOSTIC and propose-only:
  * It ingests a JSON/CSV export the operator downloads from the official
    inquiry page — it does NOT mass-scrape a government API, and it embeds no
    API key. (An optional single-query live path can be wired by the operator
    via DMW_VERIFICATION_API_URL / DMW_VERIFICATION_API_KEY env vars; it is
    not enabled here.)
  * The committed default registry is a clearly-labelled SYNTHETIC sample so
    the schema, verification, and tests run offline and judge-safe. Real
    exports are the operator's to stage locally (gitignored).
  * Output is a verification aid, NOT legal advice. Always confirm on the
    official regulator inquiry page; licence status is volatile.

Usage:
    python scripts/agency_registry.py --query "Sunrise Overseas Manpower"
    python scripts/agency_registry.py --query "Acme Recruitment" --license "POEA-1234-LB"
    python scripts/agency_registry.py --ingest dmw_export.json --out data/agency_registry/staged.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = _ROOT / "data" / "agency_registry" / "sample_licensed_agencies.json"

# Licence-status vocabulary, normalized from the many regulator spellings.
STATUS_VALID = "valid"
STATUS_EXPIRED = "expired"
STATUS_CANCELLED = "cancelled"
STATUS_DELISTED = "delisted"
STATUS_SUSPENDED = "suspended"
_STATUS_MAP = {
    "valid": STATUS_VALID, "active": STATUS_VALID, "good standing": STATUS_VALID,
    "licensed": STATUS_VALID, "in good standing": STATUS_VALID,
    "expired": STATUS_EXPIRED, "lapsed": STATUS_EXPIRED,
    "cancelled": STATUS_CANCELLED, "canceled": STATUS_CANCELLED, "revoked": STATUS_CANCELLED,
    "delisted": STATUS_DELISTED, "banned": STATUS_DELISTED, "blacklisted": STATUS_DELISTED,
    "suspended": STATUS_SUSPENDED, "preventive suspension": STATUS_SUSPENDED,
}
# Verdicts that mean "do not trust without independent confirmation".
_RED_STATUSES = {STATUS_EXPIRED, STATUS_CANCELLED, STATUS_DELISTED, STATUS_SUSPENDED}

# Corporate suffixes stripped before name matching.
_SUFFIXES = re.compile(
    r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|llc|"
    r"intl|international|manpower|services?|agency|agencies|"
    r"recruitment|placement|overseas|enterprises?)\b", re.I)


def normalize_status(raw: str) -> str:
    return _STATUS_MAP.get((raw or "").strip().lower(), (raw or "").strip().lower() or "unknown")


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation + corporate suffixes, collapse spaces."""
    s = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    s = _SUFFIXES.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass(frozen=True)
class AgencyProfile:
    """One licensed-agency (or accredited medical-clinic) record."""

    name: str
    license_no: str
    status: str                      # normalized: valid/expired/cancelled/...
    record_type: str = "agency"      # "agency" | "medical_clinic"
    status_as_of: str = ""           # YYYY-MM-DD from the source snapshot
    address: str = ""
    region: str = ""
    phones: tuple[str, ...] = ()
    email: str = ""
    job_markets: tuple[str, ...] = ()   # destination countries the licence covers
    official_source: str = ""           # the inquiry-page URL / export name
    fetched_at: str = ""                # YYYY-MM-DD the operator pulled the export
    notes: str = ""

    @property
    def norm_name(self) -> str:
        return normalize_name(self.name)

    @property
    def norm_license(self) -> str:
        return re.sub(r"[^a-z0-9]", "", (self.license_no or "").lower())


def profile_from_record(rec: dict) -> AgencyProfile:
    """Coerce a loose export record into an AgencyProfile (tolerant of source
    field spellings)."""
    def first(*keys, default=""):
        for k in keys:
            if rec.get(k) not in (None, ""):
                return rec[k]
        return default

    phones = rec.get("phones") or rec.get("phone") or rec.get("contact_no") or []
    if isinstance(phones, str):
        phones = [p.strip() for p in re.split(r"[;,/]", phones) if p.strip()]
    markets = rec.get("job_markets") or rec.get("markets") or rec.get("countries") or []
    if isinstance(markets, str):
        markets = [m.strip() for m in re.split(r"[;,/]", markets) if m.strip()]
    return AgencyProfile(
        name=str(first("name", "agency_name", "company_name")),
        license_no=str(first("license_no", "license", "licence_no", "poea_no")),
        status=normalize_status(str(first("status", "license_status", "standing", default="unknown"))),
        record_type=str(first("record_type", "type", default="agency")),
        status_as_of=str(first("status_as_of", "as_of", "snapshot_date")),
        address=str(first("address", "office_address")),
        region=str(first("region", "area")),
        phones=tuple(str(p) for p in phones),
        email=str(first("email", "official_email")),
        job_markets=tuple(str(m) for m in markets),
        official_source=str(first("official_source", "source")),
        fetched_at=str(first("fetched_at")),
        notes=str(first("notes")),
    )


def load_registry(path: Path | str = DEFAULT_REGISTRY) -> list[AgencyProfile]:
    """Load profiles from a JSON ({"records":[...]} or a bare list) or CSV file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"registry not found: {p}")
    if p.suffix.lower() == ".csv":
        with p.open(encoding="utf-8", newline="") as f:
            records = list(csv.DictReader(f))
    else:
        data = json.loads(p.read_text(encoding="utf-8"))
        records = data.get("records") if isinstance(data, dict) else data
    return [profile_from_record(r) for r in (records or [])]


@dataclass
class Verdict:
    query: str
    status: str                  # licensed_valid | licensed_red | not_found
    matched_name: str = ""
    license_no: str = ""
    license_status: str = ""
    license_match: str = "n/a"   # match | mismatch | n/a (no licence claimed)
    advisory: str = ""
    record_type: str = "agency"


def verify_agency(query: str, registry: list[AgencyProfile],
                  *, claimed_license: str = "") -> Verdict:
    """Return a legitimacy verdict for an agency name (+ optional licence)."""
    qn = normalize_name(query)
    if not qn:
        return Verdict(query=query, status="not_found",
                       advisory="empty query — provide an agency name")
    match = next((p for p in registry if p.norm_name == qn), None)
    if match is None:
        # token-overlap fallback for near-name matches (>=2 shared tokens)
        qtokens = set(qn.split())
        match = next(
            (p for p in registry
             if len(qtokens & set(p.norm_name.split())) >= 2 and len(qtokens) >= 2),
            None)
    if match is None:
        return Verdict(
            query=query, status="not_found",
            advisory=("NOT FOUND in the licensed registry. An agency that is "
                      "not on the official licensed list — especially one "
                      "claiming a licence number — is a strong red flag. "
                      "Confirm directly on the official regulator inquiry page."),
        )
    claim = re.sub(r"[^a-z0-9]", "", (claimed_license or "").lower())
    license_match = "n/a"
    if claim:
        license_match = "match" if claim == match.norm_license else "mismatch"
    is_red = match.status in _RED_STATUSES
    if is_red:
        advisory = (f"Agency is on the registry but its licence is "
                    f"{match.status.upper()} (as of {match.status_as_of or 'unknown'}). "
                    f"Treat any current recruitment by this entity as high-risk.")
        status = "licensed_red"
    elif license_match == "mismatch":
        advisory = ("The claimed licence number does NOT match the registry "
                    "record for this agency name — possible licence pass-through "
                    "or impersonation. Verify on the official inquiry page.")
        status = "licensed_red"
    else:
        advisory = ("Agency appears on the licensed registry with a valid "
                    "licence. This is a positive signal, not a guarantee — "
                    "licence status is volatile; confirm on the official page.")
        status = "licensed_valid"
    return Verdict(
        query=query, status=status, matched_name=match.name,
        license_no=match.license_no, license_status=match.status,
        license_match=license_match, advisory=advisory, record_type=match.record_type,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", help="agency name to verify")
    ap.add_argument("--license", default="", help="claimed licence number (optional)")
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY),
                    help="registry JSON/CSV (default: committed synthetic sample)")
    ap.add_argument("--ingest", help="normalize a raw export into the AgencyProfile schema")
    ap.add_argument("--out", help="write the normalized registry here (propose-only)")
    args = ap.parse_args(argv)

    if args.ingest:
        profiles = load_registry(args.ingest)
        payload = {"_synthetic": False, "n_records": len(profiles),
                   "records": [asdict(p) for p in profiles]}
        out = Path(args.out or (_ROOT / "reports" / "agency_registry" / "staged.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"normalized {len(profiles)} record(s) -> {out}", file=sys.stderr)
        return 0

    if not args.query:
        ap.error("provide --query (to verify) or --ingest (to normalize an export)")
    registry = load_registry(args.registry)
    v = verify_agency(args.query, registry, claimed_license=args.license)
    print(json.dumps(asdict(v), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
