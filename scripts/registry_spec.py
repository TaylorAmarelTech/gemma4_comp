#!/usr/bin/env python3
"""Config-driven registry resolver -- turn a YAML spec into entity records.

This is the engine that lets the long tail of catalogued data-endpoints be
onboarded as CONFIG instead of code. A spec names a URL, a format, and a
``fields`` map; the engine fetches, dispatches to the right ``registry_parsers``
parser, and stamps canonical entity dicts (the same shape the hand-written
resolvers emit, so they flow straight into entity_kb + entity_screen).

Spec shape (configs/duecare/research_monitor/registry_specs.yaml):

    - id: bd_oep_cfg
      url: https://www.oep.gov.bd/agencies
      format: html_table            # json | csv | xlsx | pdf
      entity_type: recruitment_agency
      jurisdiction: BD
      fields: {name: "Agent Name", license_no: "License No", status: "License Status"}
      row_filter: {field: license_no, pattern: "^RL"}   # optional
      default_status: licensed                          # optional
      note_fields: [license_validity]                   # optional -> appended to notes
      source: "BD OEP/BMET licensed recruiting-agency register"

The three hand-written resolvers bd_oep / bd_mra / cn_mara are reproduced as
specs in the shipped YAML, which is exactly how the engine is validated: config
must reproduce their live counts (2,834 / 904 / 167). The fetcher is injectable
so parsing is tested offline.

Usage:
    python scripts/registry_spec.py --list
    python scripts/registry_spec.py --id bd_oep_cfg
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
_SPECS = _ROOT / "configs" / "duecare" / "research_monitor" / "registry_specs.yaml"
USER_AGENT = ("Mozilla/5.0 (compatible; duecare-recruitment-screen/1.0; "
              "+defensive anti-trafficking review; respects robots.txt)")

_TEXT_FORMATS = {"html_table", "csv", "json"}
_BYTE_FORMATS = {"xlsx", "pdf"}


def _rp():
    spec = importlib.util.spec_from_file_location(
        "dc_registry_parsers", str(_ROOT / "scripts" / "registry_parsers.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_specs(path: Path = _SPECS) -> dict[str, dict]:
    """id -> spec for every entry in the registry-specs YAML ({} if absent)."""
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return {}
    if not Path(path).exists():
        return {}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {str(s["id"]): s for s in (data.get("specs") or []) if s.get("id")}


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(data)).pages)


def parse_spec(spec: dict, content: Any) -> list[dict]:
    """Dispatch a spec + already-fetched content to the right parser -> records.

    ``content`` is text for html_table/csv/json, bytes for xlsx, bytes-or-text
    for pdf, or an already-parsed object for json (tests pass content directly).
    """
    rp = _rp()
    fmt = spec.get("format")
    fields = spec.get("fields", {})
    kw = {"row_filter": spec.get("row_filter"), "name_field": spec.get("name_field", "name")}
    if fmt == "html_table":
        return rp.parse_html_table(content, fields, **kw)
    if fmt == "csv":
        return rp.parse_csv(content, fields, **kw)
    if fmt == "xlsx":
        return rp.parse_xlsx(content, fields, **kw)
    if fmt == "json":
        data = json.loads(content) if isinstance(content, (str, bytes)) else content
        return rp.parse_json(data, fields, list_path=spec.get("list_path"), **kw)
    if fmt == "pdf":
        text = _pdf_text(content) if isinstance(content, (bytes, bytearray)) else content
        return rp.parse_pdf_lines(text, spec["row_regex"], spec["groups"])
    raise ValueError(f"unknown format: {fmt!r}")


def to_entities(records: list[dict], spec: dict) -> list[dict]:
    """Stamp canonical entity dicts from parsed records + spec metadata."""
    et = spec.get("entity_type", "company")
    jz = spec.get("jurisdiction", "")
    src = spec.get("source") or spec.get("id", "registry")
    default_status = spec.get("default_status", "")
    note_fields = spec.get("note_fields", [])
    out = []
    for r in records:
        name = str(r.get("name", "")).strip()
        if not name:
            continue
        notes = []
        if r.get("license_no"):
            notes.append(f"License {r['license_no']}")
        for nf in note_fields:
            if r.get(nf):
                notes.append(f"{nf}: {r[nf]}")
        out.append({
            "entity_type": et, "name": name, "jurisdiction": jz,
            "status": str(r.get("status", "")).strip() or default_status,
            "address": str(r.get("address", "")).strip(),
            "license_no": str(r.get("license_no", "")).strip(),
            "source": src, "source_tier": "official",
            "notes": "; ".join(notes),
        })
    return out


def _default_fetch(url: str, binary: bool):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=90) as r:  # noqa: S310
        raw = r.read(16_000_000)
    return raw if binary else raw.decode("utf-8", "ignore")


def resolve(spec: dict, *, fetch=None) -> list[dict]:
    """Fetch + parse + stamp a spec into entity dicts. ``fetch(url, binary)`` injectable."""
    fetch = fetch or _default_fetch
    binary = spec.get("format") in _BYTE_FORMATS
    content = fetch(spec["url"], binary)
    return to_entities(parse_spec(spec, content), spec)


def resolve_id(spec_id: str, *, fetch=None, specs: dict | None = None) -> list[dict]:
    """Resolve a single spec by id (raises KeyError if unknown)."""
    specs = specs if specs is not None else load_specs()
    return resolve(specs[spec_id], fetch=fetch)


def validate_spec(spec: dict) -> list[str]:
    """Return a list of problems with a spec ([] = valid)."""
    problems = []
    for req in ("id", "url", "format", "entity_type"):
        if not spec.get(req):
            problems.append(f"missing {req}")
    if spec.get("format") not in (_TEXT_FORMATS | _BYTE_FORMATS):
        problems.append(f"bad format {spec.get('format')!r}")
    if spec.get("format") == "pdf":
        if not spec.get("row_regex") or not spec.get("groups"):
            problems.append("pdf needs row_regex + groups")
    elif not spec.get("fields"):
        problems.append("missing fields")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="list spec ids")
    ap.add_argument("--validate", action="store_true", help="validate all specs")
    ap.add_argument("--id", help="resolve one spec live")
    ap.add_argument("--out", help="write entities jsonl to this path")
    args = ap.parse_args(argv)
    specs = load_specs()

    if args.list or args.validate:
        for sid, spec in specs.items():
            problems = validate_spec(spec) if args.validate else []
            tag = "OK" if not problems else "BAD: " + "; ".join(problems)
            print(f"  [{spec.get('format','?'):10}] {sid:22} {spec.get('jurisdiction',''):3} {tag}")
        print(f"\n{len(specs)} specs")
        return 0

    if args.id:
        ents = resolve_id(args.id, specs=specs)
        print(f"{args.id}: {len(ents)} entities", file=sys.stderr)
        if args.out:
            ekb_spec = importlib.util.spec_from_file_location(
                "dc_entity_kb_for_spec", str(_ROOT / "scripts" / "entity_kb.py"))
            ekb = importlib.util.module_from_spec(ekb_spec)
            sys.modules[ekb_spec.name] = ekb
            ekb_spec.loader.exec_module(ekb)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            ekb.save_entities(out, ekb.merge_entities([ekb.record_from_dict(e) for e in ents]))
            print(f"  -> {out}", file=sys.stderr)
        for e in ents[:5]:
            print(f"  {e['name'][:44]:44} {e['jurisdiction']:3} {e['status'][:16]}", file=sys.stderr)
        return 0 if ents else 1

    ap.error("provide --list, --validate, or --id")


if __name__ == "__main__":
    raise SystemExit(main())
