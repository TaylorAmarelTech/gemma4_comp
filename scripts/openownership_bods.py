#!/usr/bin/env python3
"""OpenOwnership / BODS connector -- parse Beneficial Ownership Data Standard records.

OpenOwnership publishes beneficial-ownership data (UK PSC, Register of Overseas
Entities, GLEIF-BODS, ...) as **BODS** bulk on S3 (``oo-bodsdata.s3.amazonaws.com``,
CC0) in CSV/JSON/Parquet. This connector parses BODS **statements** into our entity
records: a registered entity (``recordType: entity``) or a beneficial owner
(``recordType: person``) each become an entity; ownership edges
(``recordType: relationship``) are surfaced separately.

It handles both BODS **0.4** (``recordType`` + ``recordDetails``) and legacy **0.2**
(``statementType`` + ``entityStatement``/``personStatement``/...). It parses whatever
BODS slice you point it at (a downloaded bulk file or a URL; JSON array or
newline-delimited JSON) -- propose-only, no giant default pull. The OpenOwnership
central register closed Nov-2024, so use the per-source bulk files.

Usage:
    python scripts/openownership_bods.py --file path/to/statements.json
    python scripts/openownership_bods.py --url https://.../dataset.json --out reports/entity_kb/bods.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"


# ---------------------------------------------------------------------------
# Field helpers (tolerant of 0.2 + 0.4 shapes)
# ---------------------------------------------------------------------------

def _first_identifier(ids) -> str:
    for i in ids or []:
        if isinstance(i, dict) and i.get("id"):
            scheme = i.get("scheme") or i.get("schemeName") or ""
            return f"{scheme}:{i['id']}" if scheme else str(i["id"])
    return ""


def _address(addresses) -> str:
    for a in addresses or []:
        if isinstance(a, dict) and a.get("address"):
            return ", ".join(str(a[k]) for k in ("address", "postCode", "country") if a.get(k))
    return ""


def _jurisdiction(rd: dict) -> str:
    j = rd.get("incorporatedInJurisdiction") or {}
    if isinstance(j, dict):
        return (j.get("code") or j.get("name") or "").strip()
    return str(j or "").strip()


def _person_name(names) -> str:
    names = names or []
    for n in names:  # prefer the legal name
        if isinstance(n, dict) and n.get("type") == "legal" and n.get("fullName"):
            return n["fullName"].strip()
    for n in names:
        if isinstance(n, dict) and n.get("fullName"):
            return n["fullName"].strip()
        if isinstance(n, dict) and (n.get("givenName") or n.get("familyName")):
            return " ".join(p for p in (n.get("givenName"), n.get("familyName")) if p).strip()
    return ""


def _nationality(nats) -> str:
    for n in nats or []:
        if isinstance(n, dict) and n.get("code"):
            return n["code"]
    return ""


# ---------------------------------------------------------------------------
# Statement -> entity (pure; handles BODS 0.4 and 0.2)
# ---------------------------------------------------------------------------

def parse_bods_statement(stmt: dict) -> dict | None:
    """Map one BODS statement to a canonical entity dict.

    Returns ``None`` for ownership/relationship statements (not an entity) and for
    nameless records. Detects 0.4 (``recordType``+``recordDetails``) vs 0.2
    (``statementType`` with top-level fields).
    """
    if not isinstance(stmt, dict):
        return None
    rtype = stmt.get("recordType")
    if rtype:  # BODS 0.4
        rd = stmt.get("recordDetails") or {}
        rec_id = stmt.get("recordId") or stmt.get("statementId") or ""
        status = stmt.get("recordStatus") or ""
    else:  # BODS 0.2
        st = stmt.get("statementType") or ""
        rtype = {"entityStatement": "entity", "personStatement": "person"}.get(st)
        rd = stmt
        rec_id = stmt.get("statementID") or stmt.get("statementId") or ""
        status = ""
    if rtype == "entity":
        name = (rd.get("name") or "").strip()
        if not name:
            return None
        return {
            "name": name, "entity_type": "company", "jurisdiction": _jurisdiction(rd),
            "license_no": _first_identifier(rd.get("identifiers")),
            "address": _address(rd.get("addresses")), "record_id": rec_id,
            "status": status, "source": "OpenOwnership BODS (CC0)",
        }
    if rtype == "person":
        name = _person_name(rd.get("names"))
        if not name:
            return None
        return {
            "name": name, "entity_type": "individual", "jurisdiction": _nationality(rd.get("nationalities")),
            "address": _address(rd.get("addresses")), "record_id": rec_id,
            "status": status, "source": "OpenOwnership BODS (CC0)",
        }
    return None  # relationship / ownershipOrControlStatement -> not an entity


def parse_bods(statements) -> list[dict]:
    """Map a stream of BODS statements to entity records (skips relationships/nameless)."""
    out = []
    for stmt in statements:
        ent = parse_bods_statement(stmt)
        if ent:
            out.append(ent)
    return out


# ---------------------------------------------------------------------------
# Loading (JSON array or newline-delimited JSON; file or URL)
# ---------------------------------------------------------------------------

def iter_statements(text: str):
    """Yield statements from a BODS payload: a JSON array, or one JSON object per line."""
    text = text.strip()
    if not text:
        return
    if text[0] == "[":
        yield from json.loads(text)
        return
    for line in text.splitlines():  # newline-delimited JSON (the bulk format)
        line = line.strip()
        if line:
            yield json.loads(line)


def load_text(*, file: str | None = None, url: str | None = None, fetch=None) -> str:
    if file:
        return Path(file).read_text(encoding="utf-8")
    if url:
        if fetch:
            return fetch(url)
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - https bulk data
            return r.read().decode("utf-8", "replace")
    raise ValueError("give file= or url=")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="local BODS file (JSON array or newline-delimited)")
    src.add_argument("--url", help="BODS data URL")
    ap.add_argument("--out", help="propose-only JSONL output path (under reports/)")
    args = ap.parse_args(argv)

    ents = parse_bods(iter_statements(load_text(file=args.file, url=args.url)))
    by_type = Counter(e["entity_type"] for e in ents)
    print(f"BODS: {len(ents)} entities ({dict(by_type)})", file=sys.stderr)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in ents), encoding="utf-8")
        print(f"wrote {out} -- PROPOSE-ONLY")
    else:
        for e in ents[:10]:
            print(f"  [{e['entity_type']:8}] {e['name'][:46]}  {e.get('license_no','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
