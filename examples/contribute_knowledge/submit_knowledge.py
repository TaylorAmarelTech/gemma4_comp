#!/usr/bin/env python3
"""Submit a DueCare KnowledgeObject v1.0 envelope to a central hub.

This is a small, dependency-light client for the "contribute knowledge"
flow. It does exactly what the in-kernel share page does, in a script you
can read end to end:

    build envelope  ->  validate locally  ->  stamp provenance  ->
    POST /api/submit/knowledge  ->  print the receipt

The envelope contract and the receiving endpoint are the real ones:

  * Schema:   <repo>/packages/duecare-llm-chat/src/duecare/chat/static/envelope_schema.json
              (also served live at  <hub>/static/envelope_schema.json )
  * Receiver: apps/duecare-ai.com  ->  POST /api/submit/knowledge
              body {"submission_id", "ts", "items": [<envelope>, ...]}
              (the model allows extra keys, so a "knowledge" alias is also
               sent for self-hosted kernel forwarders that read that key).

Nothing here invents server logic; it only builds a request the existing
hub already accepts.

Environment variables (all optional):

    DUECARE_HUB_URL       base URL of the hub      (default https://duecare-ai.com)
    DUECARE_SUBMIT_TOKEN  bearer token, if the hub requires one (default none)
    DUECARE_NODE_ID       id stamped into provenance.created_by (default kernel-01)
    DUECARE_SCHEMA_PATH   override the envelope_schema.json location

Usage:

    # validate the bundled example locally, print it, do NOT send:
    python submit_knowledge.py --dry-run

    # validate and POST it to the default hub:
    python submit_knowledge.py

    # send your own envelope to your own hub:
    DUECARE_HUB_URL=https://hub.example.org python submit_knowledge.py --envelope my_rule.json

Exit codes: 0 ok, 1 network/send failure, 2 envelope invalid.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ENVELOPE = HERE / "example_envelope.json"
DEFAULT_HUB = os.environ.get("DUECARE_HUB_URL", "https://duecare-ai.com").rstrip("/")
SUBMIT_PATH = "/api/submit/knowledge"

# Candidate locations for the canonical schema artifact, in priority order.
_SCHEMA_CANDIDATES = [
    os.environ.get("DUECARE_SCHEMA_PATH", ""),
    str(HERE.parent.parent
        / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat"
        / "static" / "envelope_schema.json"),
]


def node_id() -> str:
    """Identity stamped into provenance.created_by (mirrors the kernel)."""
    return os.environ.get("DUECARE_NODE_ID", "").strip() or "kernel-01"


def content_sha256(content: dict) -> str:
    """Canonical content hash: sha256 over sorted-key compact JSON.

    Identical to duecare.chat.knowledge_taxonomy.content_sha256 so any
    recipient recomputes the same digest and can verify integrity.
    """
    body = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_schema() -> dict | None:
    """Load the envelope JSON Schema from the first candidate that exists."""
    for cand in _SCHEMA_CANDIDATES:
        if cand and Path(cand).is_file():
            with open(cand, encoding="utf-8") as fh:
                return json.load(fh)
    return None


def per_type_required(schema: dict) -> dict[str, list[str]]:
    """Extract {knowledge_object_type: [required content keys]} from allOf."""
    out: dict[str, list[str]] = {}
    for clause in schema.get("allOf", []):
        const = (
            clause.get("if", {})
            .get("properties", {})
            .get("knowledge_object_type", {})
            .get("const")
        )
        req = (
            clause.get("then", {})
            .get("properties", {})
            .get("content", {})
            .get("required", [])
        )
        if const:
            out[const] = list(req)
    return out


def validate_envelope(env: dict, schema: dict | None) -> tuple[bool, str, str]:
    """Return (ok, method, error). Prefers the real validators.

    Order: (1) the app's validator if duecare.chat is importable,
    (2) jsonschema against the schema artifact, (3) a stdlib manual check
    grounded in the same schema. Every path enforces the wrapper contract
    plus per-type required content keys.
    """
    # (1) The app's own validator, if the package is installed.
    try:
        from duecare.chat.knowledge_taxonomy import validate_envelope as _app_validate

        known = set((schema or {}).get("properties", {})
                    .get("knowledge_object_type", {}).get("enum", []))
        catalog = {t: {"required_content_keys": keys}
                   for t, keys in per_type_required(schema or {}).items()}
        ok, err = _app_validate(env, known_types=known, catalog=catalog or None)
        return ok, "duecare.chat.knowledge_taxonomy.validate_envelope", err
    except Exception:
        pass

    if schema is None:
        return False, "none", (
            "envelope_schema.json not found; set DUECARE_SCHEMA_PATH to the "
            "schema location so the envelope can be validated"
        )

    # (2) jsonschema (draft 2020-12) against the canonical artifact.
    try:
        import jsonschema

        jsonschema.validate(env, schema)
        return True, "jsonschema", ""
    except ImportError:
        pass
    except Exception as exc:  # jsonschema.ValidationError and friends
        msg = getattr(exc, "message", None) or str(exc)
        return False, "jsonschema", msg

    # (3) Manual, stdlib-only, grounded in the same schema.
    if not isinstance(env, dict):
        return False, "manual", "envelope must be a JSON object"
    for key in ("schema_version", "knowledge_object_type", "id", "content"):
        if key not in env:
            return False, "manual", f"missing required key: {key}"
    if env.get("schema_version") != "1.0":
        return False, "manual", 'schema_version must be "1.0"'
    types = set(schema.get("properties", {})
                .get("knowledge_object_type", {}).get("enum", []))
    ko_type = env.get("knowledge_object_type")
    if ko_type not in types:
        return False, "manual", f"knowledge_object_type must be one of {sorted(types)}"
    ko_id = env.get("id")
    pattern = schema.get("properties", {}).get("id", {}).get("pattern", r"^[a-z0-9][a-z0-9\-_]*$")
    if not isinstance(ko_id, str) or not re.match(pattern, ko_id):
        return False, "manual", "`id` must be kebab-case (lowercase + digits + hyphen/underscore)"
    content = env.get("content")
    if not isinstance(content, dict):
        return False, "manual", "`content` must be a JSON object"
    missing = [k for k in per_type_required(schema).get(ko_type, []) if k not in content]
    if missing:
        return False, "manual", (
            f"content for `{ko_type}` is missing required key(s): {', '.join(missing)}"
        )
    return True, "manual", ""


def stamp_provenance(env: dict) -> list[str]:
    """Fill provenance defaults and recompute content_sha256 in place.

    Returns a list of human-readable notes (e.g. an integrity warning if
    a pre-existing hash did not match the content).
    """
    notes: list[str] = []
    prov = env.setdefault("provenance", {})
    prov.setdefault("created_at",
                    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    prov.setdefault("created_by", node_id())
    recomputed = content_sha256(env.get("content") or {})
    existing = prov.get("content_sha256")
    if existing and existing != recomputed:
        notes.append(
            "integrity: stored content_sha256 did not match the content and "
            "was corrected (the content changed after it was last hashed)"
        )
    prov["content_sha256"] = recomputed
    return notes


def load_envelopes(path: Path) -> list[dict]:
    """Load one envelope object or a list of them from a JSON file."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else [data]


def build_payload(envelopes: list[dict]) -> dict:
    """Build the hub submission body. `items` is the hub key; `knowledge`
    is an alias so a self-hosted kernel forwarder accepts it too."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    return {
        "submission_id": f"contrib_{ts}",
        "ts": ts,
        "items": envelopes,
        "knowledge": envelopes,
    }


def post(url: str, payload: dict, token: str | None) -> tuple[int, str]:
    """POST JSON with stdlib urllib. Returns (status_code, body_text)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit a KnowledgeObject envelope to a DueCare hub.")
    parser.add_argument("--envelope", type=Path, default=DEFAULT_ENVELOPE,
                        help=f"envelope JSON file (default: {DEFAULT_ENVELOPE.name})")
    parser.add_argument("--hub", default=DEFAULT_HUB,
                        help=f"hub base URL (default: {DEFAULT_HUB}; or set DUECARE_HUB_URL)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate + stamp + print, but do NOT send")
    args = parser.parse_args()

    if not args.envelope.is_file():
        print(f"error: envelope not found: {args.envelope}", file=sys.stderr)
        return 2

    schema = load_schema()
    envelopes = load_envelopes(args.envelope)

    all_notes: list[str] = []
    for i, env in enumerate(envelopes):
        ok, method, err = validate_envelope(env, schema)
        if not ok:
            print(f"INVALID (item {i}, via {method}): {err}", file=sys.stderr)
            return 2
        notes = stamp_provenance(env)
        all_notes.extend(notes)
        print(f"OK    item {i}: {env['knowledge_object_type']}/{env['id']} "
              f"(validated via {method}, content_sha256="
              f"{env['provenance']['content_sha256'][:12]}...)")

    for note in all_notes:
        print(f"note: {note}")

    payload = build_payload(envelopes)

    if args.dry_run:
        print("\n--- dry run: the following would be POSTed "
              f"to {args.hub}{SUBMIT_PATH} ---")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"\ndry run complete: {len(envelopes)} envelope(s) valid, nothing sent.")
        return 0

    token = os.environ.get("DUECARE_SUBMIT_TOKEN") or None
    url = f"{args.hub}{SUBMIT_PATH}"
    print(f"\nPOST {url}  ({len(envelopes)} item(s)"
          f"{', with bearer token' if token else ''})")
    status, body = post(url, payload, token)
    print(f"HTTP {status}")
    try:
        print(json.dumps(json.loads(body), ensure_ascii=False, indent=2))
    except Exception:
        print(body)
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
