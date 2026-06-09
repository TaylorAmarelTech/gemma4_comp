"""Emit the KnowledgeObject envelope JSON Schema to every serving surface.

One generator, two committed copies of the same artifact:

  * ``packages/duecare-llm-chat/src/duecare/chat/static/envelope_schema.json``
    -- served by every kernel at /static/envelope_schema.json (the live
    equivalent is GET /api/knowledge/schema).
  * ``apps/duecare-ai.com/app/static/envelope_schema.json`` -- served by the
    public hub, which also loads it at startup to enforce per-type required
    content keys on submissions (the hub container does not install the
    duecare packages, so the JSON file IS its contract source).

Run after any KO_TYPE_CATALOG change: ``python scripts/build_envelope_schema.py``
``tests/test_envelope_schema_sync.py`` fails if the committed copies drift.
"""
from __future__ import annotations

import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "packages" / "duecare-llm-chat" / "src"))

_TARGETS = [
    _ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat"
    / "static" / "envelope_schema.json",
    _ROOT / "apps" / "duecare-ai.com" / "app" / "static" / "envelope_schema.json",
]


def build() -> dict:
    from duecare.chat.app import KO_BRANCHES, KO_TYPE_CATALOG
    from duecare.chat.knowledge_taxonomy import build_envelope_json_schema

    return build_envelope_json_schema(KO_TYPE_CATALOG, KO_BRANCHES)


def main() -> None:
    schema = build()
    text = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    for target in _TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"[envelope-schema] wrote {target} ({len(text):,} bytes)")


if __name__ == "__main__":
    main()
