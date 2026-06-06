"""Promote staged acquisition chunks into an importable knowledge bundle.

Reads the staging artifacts produced by ``run_acquisition.py`` and writes a
ZIP that the existing ``/api/knowledge/import`` flow accepts (entries pathed
``<type>/<id>.json``), plus a reviewable ``knowledge_envelopes.jsonl`` and a
summary. Propose-only: the curator reviews the bundle and imports it; nothing
here mutates the live corpus.

Env knobs:
  ACQ_OUT  staging dir holding staged_chunks.jsonl + graph.json
           (default: reports/acquisition)
"""
from __future__ import annotations

import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in sorted((ROOT / "packages").glob("*/src")):
    sys.path.insert(0, str(_p))

from duecare.research_tools.promote import build_envelopes, bundle_entries  # noqa: E402

OUT = Path(os.environ.get("ACQ_OUT", ROOT / "reports/acquisition"))

_README = (
    "DueCare acquisition knowledge bundle\n"
    "====================================\n"
    "Auto-generated from staged public-source chunks. Each entry is a knowledge\n"
    "envelope (rag_doc or citation_edge) importable via /api/knowledge/import.\n"
    "REVIEW before production use: verify each doc against its cited source; do\n"
    "not rely on memorized volatile facts (numbers, contacts) -- use tools.\n"
)


def _load_jsonl(p: Path) -> list[dict]:
    out: list[dict] = []
    if not p.exists():
        return out
    with open(p, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    return out


def _zip_write(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
    """Deterministic archive entry (fixed timestamp / mode)."""
    zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    zf.writestr(zi, data)


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    staged = _load_jsonl(OUT / "staged_chunks.jsonl")
    graph_path = OUT / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8")) if graph_path.exists() else {"edges": []}
    if not staged:
        print(f"[promote] no staged chunks in {OUT} -- run acquisition first.", flush=True)
        return

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelopes = build_envelopes(staged, graph, created_at=created_at)
    entries = bundle_entries(envelopes)

    # reviewable jsonl
    env_path = OUT / "knowledge_envelopes.jsonl"
    with open(env_path, "w", encoding="utf-8") as f:
        for env in envelopes:
            f.write(json.dumps(env, ensure_ascii=False) + "\n")

    # importable deterministic zip
    zip_path = OUT / "knowledge_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        _zip_write(zf, "README.txt", _README.encode("utf-8"))
        for path, raw in entries:
            _zip_write(zf, path, raw)

    by_type: dict[str, int] = {}
    for env in envelopes:
        t = env["knowledge_object_type"]
        by_type[t] = by_type.get(t, 0) + 1
    summary = {
        "created_at": created_at,
        "staged_chunks": len(staged),
        "envelopes_total": len(envelopes),
        "by_type": by_type,
        "bundle_zip": str(zip_path),
        "bundle_bytes": zip_path.stat().st_size,
        "envelopes_jsonl": str(env_path),
    }
    (OUT / "promote_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("[promote] DONE " + json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
