"""Unit tests for the canonical-envelope -> runtime-pack projection.

These exercise :func:`app.runtime_packs.to_runtime_pack` directly (no HTTP),
one case per pack ``@type`` plus the totality / round-trip guarantees the
``/api/knowledge/packs`` route relies on.
"""

from __future__ import annotations

from app.runtime_packs import RuntimePack, to_runtime_pack


def test_grep_rule_pack_projects_executable_rules() -> None:
    body = {
        "@type": "GrepRulePack",
        "id": "fee-rules",
        "version": "2.1.0",
        "status": "vetted",
        "tags": ["fees"],
        "content_hash": "sha256:demo",
        "content": {
            "rules": [
                {
                    "rule_id": "fee_explicit",
                    "pattern": r"fee\s+of\s+\$?\d",
                    "fires_for": "warn",
                    "label": "Explicit fee",
                },
                {"rule_id": "no_pattern", "fires_for": "block"},  # dropped: no pattern
            ]
        },
    }
    pack = to_runtime_pack(body)
    assert pack.slug == "fee-rules"
    assert pack.trust == "vetted"
    assert pack.content_hash == "sha256:demo"
    assert [rule.id for rule in pack.rules] == ["fee_explicit"]
    assert pack.rules[0].severity == "medium"  # warn -> medium
    assert pack.rules[0].category == "Explicit fee"
    assert pack.rules[0].pattern.startswith("fee")
    assert pack.facts == []


def test_grep_severity_maps_block_and_info() -> None:
    body = {
        "@type": "GrepRulePack",
        "id": "p",
        "version": "1",
        "status": "vetted",
        "content": {
            "rules": [
                {"rule_id": "a", "pattern": "x", "fires_for": "block"},
                {"rule_id": "b", "pattern": "y", "fires_for": "info"},
                {"rule_id": "c", "pattern": "z", "fires_for": "unknown"},
            ]
        },
    }
    severities = {rule.id: rule.severity for rule in to_runtime_pack(body).rules}
    assert severities == {"a": "high", "b": "low", "c": "medium"}


def test_context_pack_projects_sections_to_facts() -> None:
    body = {
        "@type": "ContextPack",
        "id": "corridor",
        "version": "1.0.0",
        "status": "vetted",
        "tags": ["domestic-work"],
        "source": {"citation": "regulator pub"},
        "content": {
            "sections": [
                {
                    "heading": "Legal placement-fee cap",
                    "body": "Fee should be zero.",
                    "citations": ["https://example.gov/cap"],
                },
                {"heading": "Empty", "body": ""},  # dropped: no body
            ]
        },
    }
    pack = to_runtime_pack(body)
    assert pack.rules == []
    assert len(pack.facts) == 1
    fact = pack.facts[0]
    assert fact.id == "legal-placement-fee-cap"
    assert fact.text == "Fee should be zero."
    assert fact.citation == "https://example.gov/cap"
    assert "domestic-work" in fact.tags


def test_context_section_without_citation_falls_back_to_source() -> None:
    body = {
        "@type": "ContextPack",
        "id": "p",
        "version": "1",
        "status": "vetted",
        "source": {"citation": "fallback cite"},
        "content": {"sections": [{"heading": "H", "body": "B"}]},
    }
    assert to_runtime_pack(body).facts[0].citation == "fallback cite"


def test_contact_pack_projects_contacts_to_facts() -> None:
    body = {
        "@type": "ContactPack",
        "id": "contacts",
        "version": "1.0.0",
        "status": "vetted",
        "content": {
            "contacts": [
                {
                    "contact_id": "ph-dmw",
                    "name": "DMW",
                    "role": "regulator",
                    "web_url": "https://example.gov/dmw",
                }
            ]
        },
    }
    fact = to_runtime_pack(body).facts[0]
    assert fact.id == "ph-dmw"
    assert "DMW (regulator)" in fact.text
    assert "https://example.gov/dmw" in fact.text
    assert "regulator" in fact.tags


def test_rubric_pack_projects_dimensions_to_facts() -> None:
    body = {
        "@type": "RubricPack",
        "id": "rubric",
        "version": "3.0.0",
        "status": "vetted",
        "content": {
            "dimensions": [
                {"dimension_id": "has_citation", "name": "Has citation", "question": "Cited?"}
            ]
        },
    }
    fact = to_runtime_pack(body).facts[0]
    assert fact.id == "has_citation"
    assert "Has citation" in fact.text and "Cited?" in fact.text
    assert "rubric" in fact.tags


def test_non_vetted_status_maps_to_unvetted_trust() -> None:
    base = {"id": "p", "version": "1"}
    assert to_runtime_pack({**base, "status": "vetted"}).trust == "vetted"
    assert to_runtime_pack({**base, "status": "proposed"}).trust == "unvetted"
    assert to_runtime_pack({**base, "status": "needs_review"}).trust == "unvetted"
    assert to_runtime_pack({**base, "status": "deprecated"}).trust == "unvetted"


def test_projection_is_total_over_unknown_shape() -> None:
    # Unknown @type / missing content -> a valid empty pack, never raises.
    pack = to_runtime_pack(
        {"id": "weird", "version": "9", "status": "vetted", "@type": "ToolPack"}
    )
    assert isinstance(pack, RuntimePack)
    assert pack.rules == [] and pack.facts == []
    # A totally empty body still yields a usable default-slug pack.
    assert to_runtime_pack({}).slug == "pack"


def test_already_runtime_shaped_body_round_trips() -> None:
    # A body that already carries slug + content.facts survives the projection
    # (so an exported runtime pack re-imported through the hub is stable).
    body = {
        "slug": "ph-hk",
        "version": "1.4.0",
        "status": "vetted",
        "content": {
            "facts": [
                {"id": "f1", "text": "Fee is zero", "citation": "pack", "tags": ["fee"]}
            ]
        },
    }
    pack = to_runtime_pack(body)
    assert pack.slug == "ph-hk"  # falls back to slug when no id
    assert pack.facts[0].id == "f1"
    assert pack.facts[0].text == "Fee is zero"
    assert pack.facts[0].tags == ["fee"]
