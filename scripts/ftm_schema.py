#!/usr/bin/env python3
"""FollowTheMoney (FtM) -- the canonical entity schema for the DueCare entity KB.

Every connector emits its own record dict (``{name, entity_type, jurisdiction, lei,
license_no, status, source, ...}``). This module normalises those into the **FtM**
entity model (``alephdata/followthemoney``) -- the same schema OpenSanctions, Aleph, and
nomenklatura speak -- so our knowledge base is interoperable with that whole ecosystem:
an FtM ``EntityProxy`` dict (``{"id", "schema", "properties": {prop: [values]}}``) that
loads straight into Aleph or screens with nomenklatura.

The FtM **library** (``followthemoney``) pulls in PyICU, which cannot build on this
Windows box (no ICU C library), so this serialiser is **pure-Python** and emits the FtM
shape directly using the real schema property names (verified from the upstream schema
YAMLs: Thing -> LegalEntity -> Organization/Company, Person, PublicBody, Vessel). When
the library *is* installed (e.g. a Linux deploy), :func:`to_ftm` ``validate=True`` routes
through ``model.make_entity`` for library-validated output -- identical shape either way.

Propose-only; no PII beyond the public-register entity names the connectors already hold.

Usage:
    python scripts/ftm_schema.py --in reports/entity_kb/gleif_np.jsonl --out reports/entity_kb/gleif_np.ftm.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

#: our entity_type -> FtM schema (real FtM schema names)
_SCHEMA_FOR = {
    "individual": "Person", "person": "Person",
    "company": "Company", "employer": "Company", "lender": "Company",
    "recruitment_agency": "Organization", "manning_agency": "Organization",
    "training_center": "Organization", "medical_clinic": "Organization",
    "broker": "Organization", "ngo": "Organization", "organization": "Organization",
    "hotline": "Organization",
    "regulator": "PublicBody",
    "vessel": "Vessel",
    "sanctioned_entity": "LegalEntity", "entity": "LegalEntity",
}
#: FtM properties valid only on LegalEntity-derived schemas (i.e. everything but Vessel)
_LEGAL_ENTITY_SCHEMAS = {"Person", "Company", "Organization", "PublicBody", "LegalEntity"}
_WS = re.compile(r"\s+")
_ISO2 = re.compile(r"^[A-Za-z]{2}$")
#: status/keyword -> FtM topic (controlled vocab; only the confident mappings)
_TOPIC_RULES = (
    ("sanction", "sanction"), ("debar", "debarment"), ("blacklist", "debarment"),
    ("forced_labor", "export.control"), ("uflpa", "export.control"), ("wro", "export.control"),
)


def ftm_schema(entity_type: str) -> str:
    return _SCHEMA_FOR.get(str(entity_type or "").lower(), "LegalEntity")


def _clean(v) -> str:
    return _WS.sub(" ", str(v)).strip()


def entity_id(record: dict, schema: str) -> str:
    """Stable FtM id: the LEI if present (canonical), else a deterministic content hash."""
    lei = _clean(record.get("lei") or "")
    if lei:
        return f"lei-{lei}"
    key = f"{schema}|{_clean(record.get('name','')).lower()}|{_clean(record.get('jurisdiction','')).lower()}"
    return "dc-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]  # noqa: S324 - id, not security


def topics_for(record: dict) -> list[str]:
    """FtM topics for the record's status / entity_type (conservative; deduped)."""
    blob = f"{record.get('status','')} {record.get('entity_type','')} {record.get('default_status','')}".lower()
    out: list[str] = []
    for needle, topic in _TOPIC_RULES:
        if needle in blob and topic not in out:
            out.append(topic)
    return out


def _add(props: dict, prop: str, value) -> None:
    """Append a non-empty string value to an FtM property list (FtM props are lists)."""
    if value is None:
        return
    values = value if isinstance(value, (list, tuple)) else [value]
    for v in values:
        s = _clean(v)
        if s:
            props.setdefault(prop, [])
            if s not in props[prop]:
                props[prop].append(s)


def _notes(record: dict) -> str:
    """Compact one-line provenance/extra summary for FtM ``notes`` (free text)."""
    bits = []
    for k in ("status", "back_wages", "violations", "migrant_visa_violations",
              "offenses", "turnover", "parent", "rel_type"):
        v = record.get(k)
        if v not in (None, "", 0, [], {}):
            bits.append(f"{k}={v}")
    return "; ".join(str(b)[:120] for b in bits)


def to_ftm(record: dict, *, validate: bool = False) -> dict:
    """One entity record -> an FtM EntityProxy dict (``id`` / ``schema`` / ``properties``).

    ``validate=True`` routes through the ``followthemoney`` library when it is importable
    (library-validated output); otherwise the pure-Python path produces the same shape.
    """
    schema = ftm_schema(record.get("entity_type"))
    props: dict[str, list[str]] = {}
    _add(props, "name", record.get("name"))
    _add(props, "alias", record.get("aliases"))
    _add(props, "previousName", record.get("prev_name"))
    juris = _clean(record.get("jurisdiction") or record.get("country") or "")
    if _ISO2.match(juris):
        _add(props, "country", juris.lower())
    _add(props, "address", record.get("address"))
    _add(props, "publisher", record.get("source"))
    _add(props, "sourceUrl", record.get("url"))
    for t in topics_for(record):
        _add(props, "topics", t)
    if schema in _LEGAL_ENTITY_SCHEMAS:
        if juris and not _ISO2.match(juris):
            _add(props, "jurisdiction", juris)
        _add(props, "leiCode", record.get("lei"))
        _add(props, "licenseNumber", record.get("license_no"))
        _add(props, "registrationNumber", record.get("company_no") or record.get("registered_as"))
        _add(props, "idNumber", record.get("os_id"))
        _add(props, "taxNumber", record.get("tax_no"))
        _add(props, "status", record.get("status"))
        _add(props, "sector", record.get("sector") or record.get("industry")
             or record.get("naics_code_description"))
    elif schema == "Vessel":
        _add(props, "imoNumber", record.get("imo"))
        _add(props, "flag", record.get("flag"))
        _add(props, "callSign", record.get("call_sign"))
        _add(props, "mmsi", record.get("mmsi"))
    notes = _notes(record)
    if notes:
        _add(props, "notes", notes)

    entity = {"id": entity_id(record, schema), "schema": schema, "properties": props}
    if validate:
        validated = _to_ftm_via_library(schema, entity["id"], props)
        if validated is not None:
            return validated
    return entity


def _to_ftm_via_library(schema: str, eid: str, props: dict) -> dict | None:
    """Library-validated build (None if followthemoney is unavailable -- e.g. no PyICU)."""
    try:
        from followthemoney import model
    except Exception:  # noqa: BLE001 - library/PyICU absent -> pure path
        return None
    proxy = model.make_entity(schema)
    proxy.id = eid
    for prop, values in props.items():
        for v in values:
            proxy.add(prop, v, quiet=True)
    return proxy.to_dict()


def convert(records, *, validate: bool = False) -> list[dict]:
    return [to_ftm(r, validate=validate) for r in records if r.get("name")]


def _read_jsonl(path: str):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True, help="JSONL of entity records (connector output)")
    ap.add_argument("--out", help="FtM JSONL output (propose-only, under reports/)")
    ap.add_argument("--validate", action="store_true", help="route through the FtM library if installed")
    args = ap.parse_args(argv)

    ents = convert(_read_jsonl(args.inp), validate=args.validate)
    from collections import Counter
    by = Counter(e["schema"] for e in ents)
    print(f"FtM: {len(ents)} entities {dict(by)}", file=sys.stderr)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in ents), encoding="utf-8")
        print(f"wrote {out} -- PROPOSE-ONLY (FtM EntityProxy JSONL, loadable into Aleph)")
    else:
        for e in ents[:8]:
            print(f"  [{e['schema']:12}] {e['id']}  {e['properties'].get('name', [''])[0][:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
