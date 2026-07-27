"""Versioned public JSON schemas linked from the DueCare hub.

These documents are intentionally small, stable transport contracts. Richer
Python models remain in :mod:`app.schema`; public URLs must stay resolvable so
saved packs and examples do not point at a 404.
"""

from __future__ import annotations

from typing import Any

BASE = "https://duecare-ai.com/schema"
DRAFT = "https://json-schema.org/draft/2020-12/schema"


def _object_schema(kind: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "$schema": DRAFT,
        "$id": f"{BASE}/{kind}/1.json",
        "title": f"DueCare {kind}@1",
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


STRING = {"type": "string"}
STRING_ARRAY = {"type": "array", "items": STRING}

PUBLIC_SCHEMAS: dict[str, dict[str, Any]] = {
    "pack": _object_schema(
        "pack",
        {
            "id": STRING,
            "version": STRING,
            "manifest": {"type": "object"},
            "claims": {"type": "array", "items": {"type": "object"}},
            "citations": {"type": "object"},
            "evals": {"type": "array", "items": {"type": "object"}},
            "signing": {"type": "object"},
        },
        ["id", "version", "manifest", "claims", "citations"],
    ),
    "tool": _object_schema(
        "tool",
        {
            "id": STRING,
            "version": STRING,
            "description": STRING,
            "args_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "tests": {"type": "array", "items": {"type": "object"}},
            "side_effects": STRING,
            "rate_limit": STRING,
            "signing": {"type": "object"},
        },
        ["id", "version", "description", "args_schema", "output_schema", "side_effects"],
    ),
    "signal": _object_schema(
        "signal",
        {
            "pattern_id": STRING,
            "corridor": {
                "type": "object",
                "properties": {"source": STRING, "host": STRING},
                "required": ["source", "host"],
                "additionalProperties": False,
            },
            "sector": STRING,
            "week": {"type": "string", "pattern": r"^[0-9]{4}-W[0-9]{2}$"},
            "k_floor": {"type": "integer", "minimum": 1},
            "deployment_id": STRING,
            "opt_in": {"const": True},
        },
        ["pattern_id", "corridor", "sector", "week", "k_floor", "deployment_id", "opt_in"],
    ),
    "audit": _object_schema(
        "audit",
        {
            "ts": {"type": "string", "format": "date-time"},
            "verb": STRING,
            "object": {"type": "object"},
            "actor": {"type": "object"},
            "batch_id": STRING,
            "batch_signature": STRING,
        },
        ["ts", "verb", "object", "actor", "batch_id"],
    ),
    "feedback": _object_schema(
        "feedback",
        {
            "ticket_id": STRING,
            "type": STRING,
            "subtype": STRING,
            "affected": {"type": "object"},
            "reviewing_curator": STRING,
            "first_reply_due": {"type": "string", "format": "date"},
            "queue_url": STRING,
        },
        ["ticket_id", "type", "subtype", "affected"],
    ),
}

SCHEMA_CONTEXT_DOCUMENT: dict[str, Any] = {
    "@context": {
        "@version": 1.1,
        "@vocab": f"{BASE}/v1#",
        "id": "@id",
        "type": "@type",
        "jurisdictions": {"@container": "@set"},
        "corridors": {"@container": "@set"},
        "tags": {"@container": "@set"},
    },
    "schema_version": 1,
    "documentation": "https://duecare-ai.com/technical-docs",
}


__all__ = ["PUBLIC_SCHEMAS", "SCHEMA_CONTEXT_DOCUMENT"]
