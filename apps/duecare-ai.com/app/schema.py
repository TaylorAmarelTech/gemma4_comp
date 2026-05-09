"""Knowledge-object schema: schema.org-style hierarchy for everything the hub
stores and serves.

Every artifact the hub knows about descends from :class:`KnowledgeObject`.
The shared envelope carries identity, provenance, vetting status, and an
open ``extensions`` dict so partners can add fields without forking the
schema. Subtypes specialize the ``content`` payload.

Hierarchy::

    KnowledgeObject
        Pack                       a versioned, curator-vetted artifact
            ContextPack            RAG-ready prose with citations
            GrepRulePack           deterministic detection rules
            ToolPack               tool definitions
            ContactPack            verified NGO/regulator contacts
            RubricPack             evaluation rubrics
            EvalPromptPack         evaluation prompts
            TrainingExamplePack    curated training examples
        Submission                 a proposal, before vetting
            SignalSubmission       anonymized usage signal
            ProposalSubmission     public-source proposal
            EmailReply             expert reply via email gateway
        Run                        a single hub action (audit log entry)

JSON-LD-style envelope::

    {
        "@context": "https://duecare-ai.com/schema/v1",
        "@type": "ContextPack",
        "id": "phl-kwt-domestic",
        "version": "1.7.2",
        "schema_version": 1,
        "status": "vetted",
        "jurisdictions": ["PHL", "KWT"],
        "corridors": ["PHL-KWT"],
        "tags": ["domestic-work", "fees"],
        "source": {"kind": "public_url", "url": "https://gov.example/..."},
        "provenance": {
            "submitted_by": "automation:public_source_crawler",
            "vetted_by": "curator:k.maharjan",
            "vetted_at": "2026-04-12T09:14:00Z"
        },
        "content_hash": "sha256:9ab3...",
        "content": { ... shape varies by @type ... },
        "extensions": { "partner.policy_id": "..." }
    }

Why this matters
================

* Inheritance lets clients write code against ``KnowledgeObject`` and pick
  up new pack kinds without changes.
* The ``extensions`` dict is open: any partner can add ``"<vendor>.<key>"``
  fields without breaking validation. Validators only enforce the core
  envelope.
* ``schema_version`` is monotonically increasing. Old packs stay valid as
  the schema evolves; clients can choose to honor or ignore newer fields.
* ``content_hash`` is computed over the canonical-JSON serialization of
  ``content`` only, so a pack's hash is stable even when envelope
  metadata (like vetting timestamps) is updated.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

SCHEMA_CONTEXT = "https://duecare-ai.com/schema/v1"
SCHEMA_VERSION = 1


# ---------------------------------------------------------------- shared

class Provenance(BaseModel):
    """Who touched the object, and when. Required on every pack."""

    submitted_by: str = Field(
        description="Identifier of the originator: 'form:contribute', "
        "'automation:public_source_crawler', 'partner:<id>', etc.",
    )
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    vetted_by: str | None = Field(
        default=None,
        description="Curator key id that vetted this version. Null until vetted.",
    )
    vetted_at: datetime | None = None
    review_notes: list[str] = Field(default_factory=list)


class Source(BaseModel):
    """Where the content came from. Public-source only for hub-stored packs."""

    kind: Literal[
        "public_url",
        "regulator_publication",
        "ngo_publication",
        "court_filing",
        "academic_paper",
        "partner_curated",
        "synthetic_demo",
        "deployment_signal",
        "email_reply",
    ]
    url: HttpUrl | None = None
    fetched_at: datetime | None = None
    citation: str | None = Field(default=None, max_length=600)


class KnowledgeObject(BaseModel):
    """Base envelope every hub artifact carries.

    Subtypes override :class:`type_` (the JSON ``@type`` field) and the
    shape of ``content``. Validators only enforce the envelope; the
    ``content`` payload is intentionally schema.org-extensible.
    """

    model_config = ConfigDict(populate_by_name=True)

    context: str = Field(default=SCHEMA_CONTEXT, alias="@context")
    type_: str = Field(alias="@type")
    id: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9_\-]+$")
    version: str = Field(min_length=1, max_length=40)
    schema_version: int = SCHEMA_VERSION
    status: Literal["proposed", "needs_review", "vetted", "deprecated"] = "proposed"
    jurisdictions: list[str] = Field(default_factory=list, max_length=12)
    corridors: list[str] = Field(default_factory=list, max_length=12)
    tags: list[str] = Field(default_factory=list, max_length=20)
    source: Source
    provenance: Provenance
    content_hash: str | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------- packs

class Pack(KnowledgeObject):
    """A versioned, downloadable artifact."""

    title: str = Field(min_length=2, max_length=160)
    summary: str = Field(min_length=10, max_length=600)
    deprecates: str | None = Field(
        default=None,
        description="ID of a pack this one supersedes; clients should migrate.",
    )


class ContextPack(Pack):
    """RAG-ready prose with citations.

    ``content.sections`` are the chunks the harness retrieves over.
    """

    type_: Literal["ContextPack"] = Field(default="ContextPack", alias="@type")
    content: "ContextPackContent"


class ContextPackContent(BaseModel):
    sections: list["ContextSection"] = Field(default_factory=list)


class ContextSection(BaseModel):
    heading: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=8000)
    citations: list[HttpUrl] = Field(default_factory=list)
    last_verified_at: datetime | None = None


class GrepRulePack(Pack):
    """Deterministic detection rules that fire before the model speaks."""

    type_: Literal["GrepRulePack"] = Field(default="GrepRulePack", alias="@type")
    content: "GrepRulePackContent"


class GrepRulePackContent(BaseModel):
    rules: list["GrepRule"] = Field(default_factory=list)


class GrepRule(BaseModel):
    rule_id: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9_\-]+$")
    pattern: str = Field(min_length=1, max_length=2000, description="Regex (Python re).")
    flags: list[Literal["i", "m", "s", "u"]] = Field(default_factory=lambda: ["i"])
    fires_for: Literal["block", "warn", "log"] = "warn"
    label: str = Field(min_length=1, max_length=120)
    rationale: str = Field(min_length=1, max_length=400)
    target_false_positive_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    citations: list[HttpUrl] = Field(default_factory=list)


class ToolPack(Pack):
    """Tool definitions the harness can invoke."""

    type_: Literal["ToolPack"] = Field(default="ToolPack", alias="@type")
    content: "ToolPackContent"


class ToolPackContent(BaseModel):
    tools: list["ToolDefinition"] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    tool_id: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=1, max_length=400)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    safety_boundary: Literal["draft_only", "read_only", "external_call"] = "draft_only"
    audit_required: bool = True


class ContactPack(Pack):
    """Verified NGO / regulator / hotline contacts."""

    type_: Literal["ContactPack"] = Field(default="ContactPack", alias="@type")
    content: "ContactPackContent"


class ContactPackContent(BaseModel):
    contacts: list["ContactEntry"] = Field(default_factory=list)


class ContactEntry(BaseModel):
    contact_id: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    role: Literal["ngo", "regulator", "hotline", "embassy", "consulate", "ministry", "legal_aid"]
    web_url: HttpUrl | None = None
    public_phone: str | None = Field(default=None, max_length=40)
    languages: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)
    last_verified_at: datetime | None = None


class RubricPack(Pack):
    """Evaluation rubric used to grade model answers."""

    type_: Literal["RubricPack"] = Field(default="RubricPack", alias="@type")
    content: "RubricPackContent"


class RubricPackContent(BaseModel):
    dimensions: list["RubricDimension"] = Field(default_factory=list)


class RubricDimension(BaseModel):
    dimension_id: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    question: str = Field(min_length=1, max_length=400)
    scale: Literal["binary", "0_to_1", "0_to_5"] = "binary"
    weight: float = Field(default=1.0, ge=0.0, le=10.0)


class EvalPromptPack(Pack):
    """A bundle of evaluation prompts. Composite-only, no real PII."""

    type_: Literal["EvalPromptPack"] = Field(default="EvalPromptPack", alias="@type")
    content: "EvalPromptPackContent"


class EvalPromptPackContent(BaseModel):
    prompts: list["EvalPrompt"] = Field(default_factory=list)


class EvalPrompt(BaseModel):
    prompt_id: str = Field(min_length=2, max_length=80)
    text: str = Field(min_length=1, max_length=4000)
    expected_intent: str = Field(min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=400)


class TrainingExamplePack(Pack):
    """Curator-approved training examples for adapter fine-tuning."""

    type_: Literal["TrainingExamplePack"] = Field(default="TrainingExamplePack", alias="@type")
    content: "TrainingExamplePackContent"


class TrainingExamplePackContent(BaseModel):
    examples: list["TrainingExample"] = Field(default_factory=list)


class TrainingExample(BaseModel):
    example_id: str = Field(min_length=2, max_length=80)
    input_text: str = Field(min_length=1, max_length=8000)
    target_text: str = Field(min_length=1, max_length=8000)
    rationale: str = Field(min_length=1, max_length=400)
    consent_basis: Literal["public_record", "synthetic", "explicit_opt_in", "partner_curated"] = "public_record"


# Discriminated union for client decoders.
AnyPack = Annotated[
    Union[
        ContextPack,
        GrepRulePack,
        ToolPack,
        ContactPack,
        RubricPack,
        EvalPromptPack,
        TrainingExamplePack,
    ],
    Field(discriminator="type_"),
]


# ---------------------------------------------------------------- helpers

def canonical_content_hash(content: BaseModel | dict[str, Any]) -> str:
    """Return ``sha256:...`` over canonical JSON of the content payload only.

    Stable across envelope changes, so two clients that downloaded the same
    pack body get the same hash even if the curator updated review notes.
    """
    payload = content.model_dump(mode="json") if isinstance(content, BaseModel) else content
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(blob).hexdigest()}"


# Resolve forward references (Pydantic v2 needs this for self-referential models).
ContextPackContent.model_rebuild()
GrepRulePackContent.model_rebuild()
ToolPackContent.model_rebuild()
ContactPackContent.model_rebuild()
RubricPackContent.model_rebuild()
EvalPromptPackContent.model_rebuild()
TrainingExamplePackContent.model_rebuild()


__all__ = [
    "SCHEMA_CONTEXT",
    "SCHEMA_VERSION",
    "AnyPack",
    "ContactEntry",
    "ContactPack",
    "ContactPackContent",
    "ContextPack",
    "ContextPackContent",
    "ContextSection",
    "EvalPrompt",
    "EvalPromptPack",
    "EvalPromptPackContent",
    "GrepRule",
    "GrepRulePack",
    "GrepRulePackContent",
    "KnowledgeObject",
    "Pack",
    "Provenance",
    "RubricDimension",
    "RubricPack",
    "RubricPackContent",
    "Source",
    "ToolDefinition",
    "ToolPack",
    "ToolPackContent",
    "TrainingExample",
    "TrainingExamplePack",
    "TrainingExamplePackContent",
    "canonical_content_hash",
]
