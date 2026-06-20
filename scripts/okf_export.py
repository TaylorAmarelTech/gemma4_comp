#!/usr/bin/env python3
"""Export DueCare KnowledgeObjects as Open Knowledge Format (OKF) v0.1 bundles.

OKF (Google Cloud, published 2026-06-12, Apache-2.0) packages knowledge as a
directory of markdown files with YAML frontmatter, so ANY agent framework can
consume an organisation's curated knowledge without translation. The only
required frontmatter field is ``type``; ``title`` / ``description`` / ``resource``
/ ``tags`` / ``timestamp`` are optional. Spec:
https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf

DueCare's KnowledgeObject v1.0 envelope (``knowledge_taxonomy.py``) maps cleanly:

    knowledge_object_type -> type (required)     provenance.created_at -> timestamp
    content.description   -> description          id / type            -> title + file path
    content.{category,..} -> tags                 content + sha256     -> markdown body

So DueCare's shared, anonymised knowledge becomes OKF-consumable by any OKF-aware
agent -- the same interoperability play as ``ftm_schema.py`` for FollowTheMoney.
Pure + offline; pyyaml only.

Usage:
    python scripts/okf_export.py --in knowledge_bundle.json --out reports/_scratch/okf
    python scripts/okf_export.py --validate reports/_scratch/okf
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

OKF_VERSION = "0.1"
#: OKF v0.1 frontmatter: `type` is the only required field.
OKF_OPTIONAL_FIELDS = ("title", "description", "resource", "tags", "timestamp")
_ISO_DASH_TIME = re.compile(r"T(\d{2})-(\d{2})-(\d{2})")


def _yaml():
    import yaml
    return yaml


def _norm_timestamp(ts: str) -> str:
    """DueCare stamps filename-safe times (``T00-00-00Z``); OKF wants ISO colons."""
    return _ISO_DASH_TIME.sub(r"T\1:\2:\3", str(ts or "").strip())


def _title(env: dict) -> str:
    content = env.get("content") or {}
    for k in ("title", "name", "label"):
        if content.get(k):
            return str(content[k])
    base = str(env.get("id") or env.get("knowledge_object_type") or "knowledge object")
    return (base.replace("-", " ").replace("_", " ").strip().capitalize()) or "Knowledge object"


def _tags(env: dict) -> list[str]:
    content = env.get("content") or {}
    raw = [env.get("knowledge_object_type")]
    for k in ("category", "severity", "corridor", "sector", "ilo_indicator", "domain"):
        v = content.get(k)
        if isinstance(v, str) and v:
            raw.append(v)
    seen, out = set(), []
    for t in raw:
        if t and t not in seen:
            seen.add(t)
            out.append(str(t))
    return out


def okf_frontmatter(env: dict) -> dict:
    """Build OKF v0.1 frontmatter from a KnowledgeObject envelope. `type` is required."""
    ko_type = str(env.get("knowledge_object_type") or "").strip()
    if not ko_type:
        raise ValueError("envelope missing knowledge_object_type (OKF requires `type`)")
    content = env.get("content") or {}
    prov = env.get("provenance") or {}
    fm: dict = {"type": ko_type, "title": _title(env)}
    desc = (content.get("description") or content.get("summary")
            or (env.get("source") or {}).get("provenance"))
    if desc:
        fm["description"] = str(desc)
    resource = prov.get("source_url") or content.get("url") or content.get("citation")
    if resource:
        fm["resource"] = str(resource)
    tags = _tags(env)
    if tags:
        fm["tags"] = tags
    ts = _norm_timestamp(prov.get("created_at") or "")
    if ts:
        fm["timestamp"] = ts
    return fm


def _body(env: dict) -> str:
    """Markdown body: the content rendered, plus provenance for verifiability."""
    content = env.get("content") or {}
    lines: list[str] = []
    desc = content.get("description") or content.get("summary")
    if desc:
        lines += [str(desc), ""]
    skip = {"description", "summary", "title", "name", "label"}
    rows = [(k, v) for k, v in content.items() if k not in skip]
    if rows:
        lines += ["## Content", ""]
        for k, v in rows:
            vs = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            lines.append(f"- **{k}**: {vs}")
        lines.append("")
    prov = env.get("provenance") or {}
    sha = prov.get("content_sha256") or hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    lines += ["## Provenance", "",
              f"- **id**: `{env.get('id', '')}`",
              f"- **schema_version**: {env.get('schema_version', '')}",
              f"- **content_sha256**: `{sha}`"]
    if prov.get("source_note"):
        lines.append(f"- **source**: {prov['source_note']}")
    return "\n".join(lines).strip() + "\n"


def render_okf(env: dict) -> str:
    """One KnowledgeObject -> one OKF markdown document (YAML frontmatter + body)."""
    front = _yaml().safe_dump(okf_frontmatter(env), sort_keys=False,
                              default_flow_style=False, allow_unicode=True).strip()
    return f"---\n{front}\n---\n\n{_body(env)}"


def okf_path(env: dict) -> str:
    """File path = the concept's identity (OKF convention): ``<type>/<id>.md``."""
    t = re.sub(r"[^a-z0-9_]+", "_", str(env.get("knowledge_object_type") or "concept").lower())
    i = re.sub(r"[^a-z0-9_\-]+", "_", str(env.get("id") or "object").lower())
    return f"{t}/{i}.md"


def parse_frontmatter(text: str) -> dict | None:
    """Parse the YAML frontmatter block of an OKF md file (None if absent/invalid)."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return None
    try:
        data = _yaml().safe_load(m.group(1))
    except Exception:  # noqa: BLE001 -- malformed frontmatter is non-conformant, not fatal
        return None
    return data if isinstance(data, dict) else None


def validate_okf(text: str) -> tuple[bool, str]:
    """OKF v0.1 conformance for one md file: YAML frontmatter present + a `type` field."""
    fm = parse_frontmatter(text)
    if fm is None:
        return False, "no YAML frontmatter block"
    if not str(fm.get("type") or "").strip():
        return False, "missing required `type` field"
    if "tags" in fm and not isinstance(fm["tags"], list):
        return False, "`tags` must be a list"
    return True, "ok"


def export_bundle(objects, out_dir) -> list[Path]:
    """Write a directory of OKF markdown files. Skips entries without a `type`."""
    out_dir = Path(out_dir)
    written: list[Path] = []
    for env in objects:
        if not isinstance(env, dict) or not env.get("knowledge_object_type"):
            continue
        p = out_dir / okf_path(env)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_okf(env), encoding="utf-8")
        written.append(p)
    return written


def _load_objects(path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for k in ("objects", "items", "knowledge_objects"):
            if isinstance(data.get(k), list):
                return data[k]
        return [data]
    return data if isinstance(data, list) else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", help="KnowledgeObject JSON (a bundle or a single envelope)")
    ap.add_argument("--out", help="output OKF directory")
    ap.add_argument("--validate", help="validate every *.md under this dir for OKF v0.1 conformance")
    args = ap.parse_args(argv)

    if args.validate:
        files = glob.glob(str(Path(args.validate) / "**" / "*.md"), recursive=True)
        bad = []
        for f in files:
            ok, why = validate_okf(Path(f).read_text(encoding="utf-8"))
            if not ok:
                bad.append((f, why))
        print(f"OKF v{OKF_VERSION}: {len(files) - len(bad)}/{len(files)} file(s) conform", file=sys.stderr)
        for f, why in bad:
            print(f"  NONCONFORMING {f}: {why}", file=sys.stderr)
        return 1 if bad else 0

    if not (args.inp and args.out):
        ap.error("provide --in <json> --out <dir>, or --validate <dir>")
    written = export_bundle(_load_objects(args.inp), args.out)
    print(f"wrote {len(written)} OKF v{OKF_VERSION} markdown file(s) -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
