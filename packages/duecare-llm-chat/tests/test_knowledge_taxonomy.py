"""Tests for the KnowledgeObject envelope contract helpers."""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import zipfile

from fastapi.testclient import TestClient

from duecare.chat.app import KO_BRANCHES, KO_TYPE_CATALOG, KO_TYPES, create_app
from duecare.chat.knowledge_taxonomy import (
    build_envelope_json_schema,
    content_sha256,
    node_id,
    stamp_provenance,
    validate_envelope,
)


def _envelope(**overrides) -> dict:
    env = {
        "schema_version": "1.0",
        "knowledge_object_type": "rag_doc",
        "id": "test-doc",
        "content": {"title": "T", "text": "Body"},
    }
    env.update(overrides)
    return env


def test_validate_envelope_accepts_wellformed() -> None:
    ok, err = validate_envelope(_envelope(), known_types=KO_TYPES, catalog=KO_TYPE_CATALOG)
    assert ok, err


def test_validate_envelope_rejects_wrapper_problems() -> None:
    cases = [
        ("not-a-dict", []),
        (_envelope(schema_version="2.0"), ["schema_version"]),
        (_envelope(knowledge_object_type="nope"), ["knowledge_object_type"]),
        (_envelope(id="Bad Id"), ["kebab-case"]),
        (_envelope(content="nope"), ["content"]),
    ]
    for env, needles in cases:
        ok, err = validate_envelope(env, known_types=KO_TYPES, catalog=KO_TYPE_CATALOG)
        assert not ok
        for needle in needles:
            assert needle in err


def test_validate_envelope_enforces_required_content_keys() -> None:
    env = _envelope(content={"title": "missing text key"})
    ok, err = validate_envelope(env, known_types=KO_TYPES, catalog=KO_TYPE_CATALOG)
    assert not ok
    assert "text" in err and "rag_doc" in err
    # Without a catalog the wrapper-only contract still passes.
    ok, _ = validate_envelope(env, known_types=KO_TYPES)
    assert ok


def test_content_sha256_is_key_order_independent() -> None:
    a = content_sha256({"x": 1, "y": [1, 2]})
    b = content_sha256({"y": [1, 2], "x": 1})
    assert a == b
    assert len(a) == 64


def test_stamp_provenance_recomputes_hash_and_uses_node_id(monkeypatch) -> None:
    monkeypatch.setenv("DUECARE_NODE_ID", "ngo-node-7")
    env = _envelope(provenance={"content_sha256": "stale"})
    prov = stamp_provenance(env, created_at="2026-06-09T00-00-00Z")
    assert prov["content_sha256"] == content_sha256(env["content"])
    assert prov["created_by"] == "ngo-node-7"
    assert prov["created_at"] == "2026-06-09T00-00-00Z"
    monkeypatch.delenv("DUECARE_NODE_ID")
    assert node_id() == "kernel-01"


def test_json_schema_covers_every_type() -> None:
    schema = build_envelope_json_schema(KO_TYPE_CATALOG, KO_BRANCHES)
    assert schema["properties"]["knowledge_object_type"]["enum"] == sorted(KO_BRANCHES)
    clause_types = {
        c["if"]["properties"]["knowledge_object_type"]["const"] for c in schema["allOf"]
    }
    assert clause_types == set(KO_BRANCHES)
    # grep_rule's required content keys surface in its clause
    grep_clause = next(
        c for c in schema["allOf"]
        if c["if"]["properties"]["knowledge_object_type"]["const"] == "grep_rule"
    )
    assert grep_clause["then"]["properties"]["content"]["required"] == ["pattern"]


def test_promote_stamps_hash_and_node_identity(monkeypatch) -> None:
    # System temp, not the repo tree: the OneDrive-synced workspace can lock
    # fresh dirs, which would silently fall back to the shared local cache.
    knowledge_root = tempfile.mkdtemp(prefix="duecare-taxonomy-promote-")
    monkeypatch.setenv("DUECARE_KNOWLEDGE_ROOT", knowledge_root)
    monkeypatch.setenv("DUECARE_NODE_ID", "test-node-42")
    client = TestClient(create_app())
    try:
        r = client.post("/api/knowledge/promote", json=_envelope(id="promote-stamp-check"))
        assert r.status_code == 200, r.text
        env = r.json()["envelope"]
        assert env["provenance"]["created_by"] == "test-node-42"
        assert env["provenance"]["content_sha256"] == content_sha256(env["content"])
        # Required-key enforcement applies at promote too.
        bad = client.post(
            "/api/knowledge/promote",
            json=_envelope(id="promote-missing-keys", content={"title": "no text"}),
        )
        assert bad.status_code == 400
        assert "required key" in bad.text
    finally:
        shutil.rmtree(knowledge_root, ignore_errors=True)


def test_schema_endpoint_serves_contract() -> None:
    client = TestClient(create_app())
    r = client.get("/api/knowledge/schema")
    assert r.status_code == 200
    body = r.json()
    assert body["properties"]["schema_version"]["const"] == "1.0"
    assert "allOf" in body


def test_export_zip_entries_pass_validation(monkeypatch) -> None:
    knowledge_root = tempfile.mkdtemp(prefix="duecare-taxonomy-export-")
    monkeypatch.setenv("DUECARE_KNOWLEDGE_ROOT", knowledge_root)
    client = TestClient(create_app())
    try:
        assert client.post(
            "/api/knowledge/promote", json=_envelope(id="export-roundtrip")
        ).status_code == 200
        exported = client.get("/api/knowledge/export")
        assert exported.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(exported.content))
        entries = [n for n in zf.namelist() if n.endswith(".json") and "/" in n]
        assert entries
        for name in entries:
            env = json.loads(zf.read(name))
            ok, err = validate_envelope(env, known_types=KO_TYPES, catalog=KO_TYPE_CATALOG)
            assert ok, f"{name}: {err}"
            assert "content_sha256" in env.get("provenance", {}), f"{name}: {json.dumps(env)}"
            assert env["provenance"]["content_sha256"] == content_sha256(env["content"])
    finally:
        shutil.rmtree(knowledge_root, ignore_errors=True)
