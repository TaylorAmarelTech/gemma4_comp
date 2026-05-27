"""Runtime-pack projection: canonical JSON-LD envelopes -> the flat shape
on-device / kernel consumers actually execute.

The hub stores packs as rich JSON-LD envelopes (see ``app/data/packs/*.json``):
identity + provenance + a type-specific ``content`` block whose structure
depends on ``@type`` (a ``GrepRulePack`` keeps ``content.rules``, a
``ContextPack`` keeps ``content.sections``, a ``ContactPack`` keeps
``content.contacts``, a ``RubricPack`` keeps ``content.dimensions``).

On-device consumers (the A-00 omni-workbench kernel, the worker-side
runtime) don't want the envelope — they want a flat, executable pack:

    {slug, version, trust, rules:[{id,pattern,severity,category}],
     facts:[{id,text,citation,tags}], source_url, content_hash}

``rules`` drive deterministic GREP; ``facts`` drive local RAG. This module
is the *single* place that knows how each ``@type`` stores its content, so
no consumer re-implements JSON-LD extraction and the projection can't drift
per client. ``GET /api/knowledge/packs`` serves :func:`to_runtime_pack`
over the same registry that backs ``GET /api/hub/packs`` (which returns the
raw envelopes for federation / curation).

The projection is total: any envelope shape yields a valid ``RuntimePack``
(empty ``rules`` / ``facts`` rather than an error), so a new ``@type`` never
breaks a consumer mid-sync.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# A ``GrepRulePack`` rule declares ``fires_for`` (block / warn / info); the
# runtime GREP layer speaks severity (high / medium / low). Unknown values
# fall back to "medium" so an unrecognised disposition never silently drops.
_SEVERITY_BY_FIRES_FOR: dict[str, str] = {
    "block": "high",
    "warn": "medium",
    "info": "low",
}


class RuntimeRule(BaseModel):
    """One deterministic GREP rule in the shape the runtime executes."""

    id: str
    pattern: str
    severity: str = "medium"
    category: str = "pack_rule"


class RuntimeFact(BaseModel):
    """One retrievable fact in the shape the local RAG layer scores."""

    id: str
    text: str
    citation: str = ""
    tags: list[str] = Field(default_factory=list)


class RuntimePack(BaseModel):
    """A pack flattened for on-device execution.

    ``trust`` is the consumer-facing projection of the envelope ``status``:
    ``"vetted"`` only when a curator has signed off, else ``"unvetted"`` so a
    consumer can fail closed on community-submitted content.
    """

    slug: str
    version: str
    trust: str
    rules: list[RuntimeRule] = Field(default_factory=list)
    facts: list[RuntimeFact] = Field(default_factory=list)
    source_url: str = ""
    content_hash: str = ""


def _slugify(value: str, fallback: str) -> str:
    """Lowercase alnum-with-hyphens id; ``fallback`` when nothing survives."""
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in (value or ""))
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return cleaned or fallback


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _default_citation(body: dict[str, Any]) -> str:
    source = _as_dict(body.get("source"))
    return str(source.get("citation") or source.get("url") or "")


def _source_url(body: dict[str, Any]) -> str:
    source = _as_dict(body.get("source"))
    return str(source.get("url") or source.get("citation") or "")


def _rules_from(content: dict[str, Any], *, default_category: str) -> list[RuntimeRule]:
    """Project ``content.rules`` (GrepRulePack) into runtime GREP rules."""
    rules: list[RuntimeRule] = []
    for raw in content.get("rules") or []:
        if not isinstance(raw, dict):
            continue
        pattern = raw.get("pattern")
        if not pattern:
            continue
        rule_id = (
            raw.get("rule_id")
            or raw.get("id")
            or _slugify(str(raw.get("label", "")), f"rule-{len(rules)}")
        )
        fires_for = str(raw.get("fires_for", "")).lower()
        rules.append(
            RuntimeRule(
                id=str(rule_id),
                pattern=str(pattern),
                severity=_SEVERITY_BY_FIRES_FOR.get(fires_for, "medium"),
                category=str(raw.get("label") or raw.get("category") or default_category),
            )
        )
    return rules


def _facts_from(
    content: dict[str, Any], *, pack_tags: list[str], default_citation: str
) -> list[RuntimeFact]:
    """Project every fact-bearing content block into runtime RAG facts.

    Handles ``ContextPack`` sections, ``ContactPack`` contacts, ``RubricPack``
    dimensions, and any pack that already carries A-00-style ``facts``. A pack
    with none of these simply contributes no facts.
    """
    facts: list[RuntimeFact] = []

    def _next_id(value: str, prefix: str) -> str:
        return _slugify(value, f"{prefix}-{len(facts)}")

    for section in content.get("sections") or []:
        if not isinstance(section, dict):
            continue
        text = section.get("body")
        if not text:
            continue
        citations = section.get("citations") or []
        facts.append(
            RuntimeFact(
                id=_next_id(str(section.get("heading", "")), "section"),
                text=str(text),
                citation=str(citations[0] if citations else default_citation),
                tags=list(pack_tags),
            )
        )

    for contact in content.get("contacts") or []:
        if not isinstance(contact, dict):
            continue
        name = contact.get("name")
        if not name:
            continue
        role = str(contact.get("role", ""))
        url = str(contact.get("web_url", ""))
        label = f"{name} ({role})" if role else str(name)
        detail = " — ".join(part for part in (label, url) if part)
        facts.append(
            RuntimeFact(
                id=str(contact.get("contact_id") or _next_id(str(name), "contact")),
                text=detail,
                citation=str(url or default_citation),
                tags=list(pack_tags) + ([role] if role else []),
            )
        )

    for dimension in content.get("dimensions") or []:
        if not isinstance(dimension, dict):
            continue
        question = dimension.get("question") or dimension.get("name")
        if not question:
            continue
        name = str(dimension.get("name", ""))
        facts.append(
            RuntimeFact(
                id=str(dimension.get("dimension_id") or _next_id(name, "dimension")),
                text=f"{name}: {question}".strip(": ") if name else str(question),
                citation=default_citation,
                tags=list(pack_tags) + ["rubric"],
            )
        )

    for fact in content.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        text = fact.get("text")
        if not text:
            continue
        facts.append(
            RuntimeFact(
                id=str(fact.get("id") or _next_id(str(text)[:40], "fact")),
                text=str(text),
                citation=str(fact.get("citation") or default_citation),
                tags=[str(t) for t in (fact.get("tags") or pack_tags)],
            )
        )

    return facts


def to_runtime_pack(body: dict[str, Any]) -> RuntimePack:
    """Project one canonical JSON-LD pack ``body`` into a :class:`RuntimePack`.

    Total over envelope shape: missing / unknown content yields empty
    ``rules`` / ``facts`` rather than raising. ``slug`` falls back to an
    existing ``slug`` key so an already-runtime pack round-trips unchanged.
    """
    content = _as_dict(body.get("content"))
    pack_tags = [str(tag) for tag in (body.get("tags") or [])]
    default_citation = _default_citation(body)
    return RuntimePack(
        slug=str(body.get("id") or body.get("slug") or "pack"),
        version=str(body.get("version") or ""),
        trust="vetted" if str(body.get("status", "")).lower() == "vetted" else "unvetted",
        rules=_rules_from(content, default_category=str(body.get("@type") or "pack_rule")),
        facts=_facts_from(content, pack_tags=pack_tags, default_citation=default_citation),
        source_url=_source_url(body),
        content_hash=str(body.get("content_hash") or ""),
    )


__all__ = [
    "RuntimeFact",
    "RuntimePack",
    "RuntimeRule",
    "to_runtime_pack",
]
