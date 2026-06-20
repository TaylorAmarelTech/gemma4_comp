"""Tests for scripts/okf_export.py -- DueCare KnowledgeObject -> Open Knowledge Format v0.1.

Pure/offline. Verifies the OKF v0.1 contract: every emitted markdown file has YAML
frontmatter with the required `type`, the optional fields map from the envelope, and
the round-trip (envelope -> OKF md -> parsed frontmatter) preserves the type.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


okf = _load("okf_export", _ROOT / "scripts" / "okf_export.py")

ENV = {
    "schema_version": "1.0",
    "knowledge_object_type": "grep_rule",
    "id": "sample-passport-retention-v1",
    "provenance": {
        "created_at": "2026-05-12T00-00-00Z",            # DueCare filename-safe time
        "created_by": "duecare-workbench-sample",
        "content_sha256": "abc123",
        "source_note": "duecare workbench sample bundle (judge-safe synthetic)",
    },
    "source": {"kind": "composite", "provenance": "duecare workbench sample"},
    "content": {
        "category": "document_retention",
        "severity": "high",
        "pattern": r"\b(hold|keep)\b",
        "description": "Flags passport-retention language. ILO Forced Labour Indicator #6.",
    },
}


def test_frontmatter_required_type_and_optional_mapping():
    fm = okf.okf_frontmatter(ENV)
    assert fm["type"] == "grep_rule"                              # required field
    assert fm["description"].startswith("Flags passport-retention")
    assert "grep_rule" in fm["tags"] and "document_retention" in fm["tags"] and "high" in fm["tags"]
    assert fm["timestamp"] == "2026-05-12T00:00:00Z"             # dashes -> ISO colons
    assert fm["title"]                                            # derived, non-empty


def test_frontmatter_requires_type():
    import pytest
    with pytest.raises(ValueError):
        okf.okf_frontmatter({"id": "x", "content": {}})         # no knowledge_object_type


def test_render_has_frontmatter_block_and_body():
    md = okf.render_okf(ENV)
    assert md.startswith("---\n") and "\n---\n" in md
    assert "## Content" in md and "## Provenance" in md
    assert "content_sha256" in md and "abc123" in md            # provenance carried for verifiability


def test_validate_okf_contract():
    md = okf.render_okf(ENV)
    ok, why = okf.validate_okf(md)
    assert ok and why == "ok"
    # non-conformant cases
    assert okf.validate_okf("no frontmatter here")[0] is False
    assert okf.validate_okf("---\ntitle: x\n---\nbody\n")[0] is False        # missing `type`
    bad_tags = "---\ntype: t\ntags: notalist\n---\nbody\n"
    assert okf.validate_okf(bad_tags)[0] is False                            # tags must be a list


def test_round_trip_envelope_to_okf_to_frontmatter():
    md = okf.render_okf(ENV)
    fm = okf.parse_frontmatter(md)
    assert fm is not None and fm["type"] == ENV["knowledge_object_type"]
    assert fm["title"] == okf.okf_frontmatter(ENV)["title"]


def test_okf_path_is_type_slash_id():
    assert okf.okf_path(ENV) == "grep_rule/sample-passport-retention-v1.md"


def test_export_bundle_writes_conformant_files(tmp_path):
    objs = [ENV,
            {**ENV, "id": "rule-2", "knowledge_object_type": "corridor_fact"},
            {"id": "skipme", "content": {}}]                    # no type -> skipped
    written = okf.export_bundle(objs, tmp_path)
    assert len(written) == 2                                     # the typeless one skipped
    for p in written:
        ok, why = okf.validate_okf(p.read_text(encoding="utf-8"))
        assert ok, (p, why)
    # the real DueCare sample bundle (if present) must also export conformant OKF
    sample = (_ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat"
              / "static" / "samples" / "knowledge_object_sample.json")
    if sample.exists():
        import json
        env = json.loads(sample.read_text(encoding="utf-8"))
        ok, why = okf.validate_okf(okf.render_okf(env))
        assert ok, why
