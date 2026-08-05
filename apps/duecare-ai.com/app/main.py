"""Public Duecare AI hub for anonymized safety coordination.

The service is intentionally CPU-only. It does not load Gemma 4. It provides
anonymized signal intake, public-source update proposals, knowledge-pack
metadata, and aggregate trend counters for the public duecare-ai.com website.
The marketing surface is rendered from Jinja templates exported by
claude.ai/design and lives under app/templates/ + app/static/.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from . import __version__, automation, local_kb, outreach, runtime_packs
from . import packs as pack_registry
from .pii import detect_pii, redact_pii
from .public_schemas import PUBLIC_SCHEMAS, SCHEMA_CONTEXT_DOCUMENT
from .ratelimit import RateLimitMiddleware

SignalSource = Literal[
    "ngo_case_intake",
    "government_regulator",
    "platform_moderation",
    "research_evaluation",
    "worker_mobile_opt_in",
    "synthetic_demo",
]
PackKind = Literal[
    "rag_docs",
    "grep_rules",
    "contacts",
    "rubrics",
    "examples",
    "tools",
    "jurisdictions",
]
UpdateStatus = Literal["proposed", "needs_review", "approved", "rejected", "retracted"]

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
DEMO_PRIORITY_EXAMPLES_PATH = APP_DIR / "data" / "demo_priority_examples.json"
MAX_CLIENT_PAYLOAD_BYTES = 100_000
MAX_CLIENT_PAYLOAD_DEPTH = 20
PACK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$")
RENDER_GIT_COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{7,64}$")


def _render_git_commit_prefix() -> str | None:
    """Return a display-safe Render commit prefix, or ``None`` off Render."""

    value = os.environ.get("RENDER_GIT_COMMIT", "").strip()
    if not RENDER_GIT_COMMIT_PATTERN.fullmatch(value):
        return None
    return value[:12].lower()

# Every clean URL on the public site maps to a template file in app/templates/.
# The slug ("/" or "/foo") is the route; the value is the template filename.
# Add a row here when a new design page lands and it will route automatically.
PAGE_ROUTES: dict[str, str] = {
    "/": "index.html",
    "/alerts": "alerts.html",
    "/benchmark": "benchmark.html",
    "/client-connect": "client-connect.html",
    "/components": "components.html",
    "/contact": "contact.html",
    "/context": "context.html",
    "/contribute": "contribute.html",
    "/dashboard": "dashboard.html",
    "/data": "data-downloads.html",
    "/demo": "demo.html",
    "/demo-recording": "demo-recording.html",
    "/deployments": "deployments.html",
    "/docs": "docs.html",
    "/email-feedback": "email-feedback.html",
    "/evaluation": "evaluation.html",
    "/finetuning": "finetuning.html",
    "/grep-rules": "grep-rules.html",
    "/harness": "harness.html",
    "/harness-study": "harness-study.html",
    "/study-2026-07": "study-2026-07.html",
    "/egregious-cases": "egregious-cases.html",
    "/hub": "hub.html",
    "/intelligence": "intelligence.html",
    "/kernels": "kernels.html",
    "/knowledge-packs": "knowledge-packs.html",
    "/login": "login.html",
    "/mission": "mission.html",
    "/newsletter": "newsletter.html",
    "/outreach": "outreach.html",
    "/local-kb": "local-kb.html",
    "/server-automation": "server-automation.html",
    "/packages": "packages.html",
    "/packages-detail": "packages-detail.html",
    "/partners": "partners.html",
    "/privacy": "privacy.html",
    "/privacy-boundary": "privacy-boundary.html",
    "/project-status": "project-status.html",
    "/research-monitor": "research-monitor.html",
    # /sentinel is owned by the auth-gated handler in create_app
    # (Phase 12) — see sentinel_admin_page below. Do not add it here.
    "/setup": "setup.html",
    "/source-verification": "source-verification.html",
    "/stats": "stats.html",
    "/submissions": "submissions.html",
    "/submit-information": "submit-information.html",
    "/technical-docs": "technical-docs.html",
    "/training-data-flywheel": "training-data-flywheel.html",
    "/tools": "tools.html",
    "/tools-registry": "tools-registry.html",
    "/use-cases": "use-cases.html",
    "/volunteer": "volunteer.html",
    "/why-gemma": "why-gemma.html",
}


class FileHubStore:
    """Small JSONL-backed store for single-instance Render deployments."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.signals_path = root / "signals.jsonl"
        self.updates_path = root / "updates.jsonl"
        self.health_path = root / ".healthcheck"

    def ensure_ready(self) -> None:
        """Create storage files and verify the mounted disk is writable."""
        self.root.mkdir(parents=True, exist_ok=True)
        for path in (self.signals_path, self.updates_path):
            path.touch(exist_ok=True)
        self.health_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")

    def append(self, filename: Literal["signals.jsonl", "updates.jsonl"], payload: dict[str, object]) -> None:
        """Append a JSON-serializable payload to the requested JSONL file."""
        path = self.root / filename
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
            handle.write("\n")

    def update_by_id(
        self,
        filename: Literal["signals.jsonl", "updates.jsonl"],
        record_id: str,
        mutate: object,
    ) -> dict[str, object] | None:
        """Find a record by id and rewrite it in-place via ``mutate(record)``.

        ``mutate`` is a callable that receives the existing dict and returns
        the new dict (or the same dict mutated). Returns the new record on
        success, or ``None`` if no matching id was found. The whole file is
        rewritten; for the hackathon-scale store this is fine.
        """
        path = self.root / filename
        if not path.exists():
            return None
        records = self.read_all(filename)
        updated: dict[str, object] | None = None
        for index, record in enumerate(records):
            if record.get("id") == record_id:
                new_record = mutate(record)  # type: ignore[operator]
                records[index] = new_record
                updated = new_record
                break
        if updated is None:
            return None
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
                handle.write("\n")
        return updated

    def read_all(self, filename: Literal["signals.jsonl", "updates.jsonl"]) -> list[dict[str, object]]:
        """Read every valid JSON object from a JSONL file."""
        path = self.root / filename
        if not path.exists():
            return []
        records: list[dict[str, object]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
        return records

    def counts(self) -> tuple[int, int]:
        """Return signal and update proposal counts."""
        return (len(self.read_all("signals.jsonl")), len(self.read_all("updates.jsonl")))

    def trends(self) -> Counter[str]:
        """Build aggregate counters from stored anonymized records."""
        counters: Counter[str] = Counter()
        for record in self.read_all("signals.jsonl"):
            source = str(record.get("source", "unknown"))
            jurisdiction = str(record.get("jurisdiction", "unknown")).lower()
            counters[f"source:{source}"] += 1
            counters[f"jurisdiction:{jurisdiction}"] += 1
            risk_tags = record.get("risk_tags", [])
            if isinstance(risk_tags, list):
                for tag in risk_tags:
                    counters[f"risk:{str(tag).lower()}"] += 1
        for record in self.read_all("updates.jsonl"):
            kind = str(record.get("proposed_pack_kind", "unknown"))
            jurisdiction = str(record.get("jurisdiction", "unknown")).lower()
            counters[f"update_kind:{kind}"] += 1
            counters[f"update_jurisdiction:{jurisdiction}"] += 1
        return counters



# ===== Phase 21: knowledge submission models =================================

class KnowledgeSubmissionIn(BaseModel):
    """Inbound knowledge submission from a DueCare kernel client."""

    model_config = ConfigDict(extra="allow")

    submission_id: Optional[str] = None
    ts: Optional[str] = None
    items: list[dict] = Field(default_factory=list)


class KnowledgeSubmissionReceipt(BaseModel):
    """Hub receipt for a knowledge submission."""

    ok: bool
    submission_id: str
    n_items: int
    n_accepted: int
    n_rejected_schema: int
    n_rejected_pii: int
    n_duplicates: int = 0
    sha256_blob: str
    status: str = "proposed"
    audit_path: str
    note: str


# ===== Phase 22-26: curator + subscriber models ======================

class CuratorDecisionIn(BaseModel):
    decision: str = Field(..., description='"accept" | "reject" | "request_changes"')
    reason: Optional[str] = None
    curator_key: Optional[str] = None


class CuratorDecisionReceipt(BaseModel):
    ok: bool
    submission_id: str
    item_index: int
    decision: str
    promoted_to_vetted: bool
    audit_path: str
    note: str


class SubscriberIn(BaseModel):
    email: str
    topics: list[str] = Field(default_factory=list)
    organization: Optional[str] = None
    role: Optional[str] = None
    consent_to_outreach: bool = True


class SubscriberReceipt(BaseModel):
    ok: bool
    subscriber_id: str
    email_sha256: str
    n_topics: int
    note: str


class OutreachCampaignIn(BaseModel):
    """Request a drafted solicitation campaign for a detected context gap."""
    gap_id: str


class OutreachObserveIn(BaseModel):
    """A civil-society observation reply to fold into context prioritization.
    Reachable directly or from the inbound-email gateway."""
    gap_id: str
    subject: str = ""
    body: str
    sender_email: str = ""
    sender_domain: str = ""


class OutreachProposeGapsIn(BaseModel):
    """LLM-drafted outreach questions to add as PROPOSED context gaps (human-reviewable).

    Each draft is ``{topic, question, target_role}`` (the shape produced by
    ``scripts/llm_generate.py --task outreach-drafts``). The hub converts them to proposed
    gaps a curator can choose to draft a (still draft-only, human-sent) campaign for."""
    drafts: list[dict] = Field(default_factory=list, max_length=50)
    model: str = "llm"

class HealthStatus(BaseModel):
    """Health status for Render and external smoke checks."""

    status: Literal["ok"]
    service: str
    version: str
    storage: Literal["file"]
    storage_ok: bool
    data_dir: str
    git_commit: str | None = None


class HubStatus(BaseModel):
    """Public service status payload."""

    service: str
    version: str
    uptime_seconds: int
    privacy_mode: str
    signal_count: int
    update_proposal_count: int
    counters: dict[str, int]


class KnowledgePackSummary(BaseModel):
    """Summary of a hub-discoverable knowledge pack."""

    id: str
    kind: PackKind
    title: str
    version: str
    description: str
    status: Literal["live", "prototype", "planned"]
    contains_raw_pii: bool = False
    update_channel: str


class AnonymizedSignalIn(BaseModel):
    """Inbound anonymized safety signal.

    The summary must describe a pattern, not a person. Evidence should be
    represented by hashes or synthetic IDs, never raw worker content.
    """

    source: SignalSource
    jurisdiction: str = Field(min_length=2, max_length=80)
    corridor: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=40)
    risk_tags: list[str] = Field(default_factory=list, max_length=12)
    summary: str = Field(min_length=20, max_length=1200)
    evidence_hashes: list[str] = Field(default_factory=list, max_length=20)
    consent_basis: Literal[
        "synthetic_demo",
        "aggregate_only",
        "explicit_opt_in",
        "public_record",
        "partner_curated",
    ]
    pack_version: str | None = Field(default=None, max_length=80)

    @field_validator("risk_tags", "evidence_hashes")
    @classmethod
    def _strip_empty_values(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]

    @field_validator("summary")
    @classmethod
    def _reject_pii(cls, value: str) -> str:
        findings = detect_pii(value)
        if findings:
            labels = ", ".join(sorted(findings))
            raise ValueError(f"summary appears to contain prohibited PII: {labels}")
        return value


class AnonymizedSignalRecord(AnonymizedSignalIn):
    """Stored anonymized signal with server-side metadata."""

    id: str
    received_at: datetime
    summary_sha256: str


class SignalReceipt(BaseModel):
    """Receipt returned after accepting an anonymized signal."""

    id: str
    accepted: bool
    received_at: datetime
    summary_sha256: str
    message: str


class OpenCrawlUpdateIn(BaseModel):
    """Public-source update proposal (form post or crawler payload)."""

    source_name: str = Field(min_length=2, max_length=120)
    source_url: HttpUrl
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    proposed_pack_kind: PackKind
    jurisdiction: str = Field(min_length=2, max_length=80)
    change_summary: str = Field(min_length=20, max_length=1600)
    extracted_public_facts: list[str] = Field(default_factory=list, max_length=20)
    content_hash: str = Field(min_length=8, max_length=128)
    crawler_version: str = Field(default="external", max_length=80)

    @field_validator("change_summary")
    @classmethod
    def _reject_pii_in_summary(cls, value: str) -> str:
        findings = detect_pii(value)
        if findings:
            labels = ", ".join(sorted(findings))
            raise ValueError(f"change_summary appears to contain prohibited PII: {labels}")
        return value


class UpdateProposalRecord(OpenCrawlUpdateIn):
    """Stored public-source update proposal."""

    id: str
    status: UpdateStatus
    received_at: datetime


class UpdateReceipt(BaseModel):
    """Receipt returned after accepting an update proposal."""

    id: str
    accepted: bool
    status: UpdateStatus
    message: str
    automation_verdict: str | None = None
    automation_intent: str | None = None
    automation_model: str | None = None


class InboundEmailIn(BaseModel):
    """Inbound email payload from the email gateway (Mailgun-style webhook)."""

    sender_domain: str = Field(min_length=2, max_length=120)
    subject: str = Field(min_length=1, max_length=400)
    body: str = Field(min_length=1, max_length=20000)
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    in_reply_to: str | None = Field(default=None, max_length=200)


class InboundEmailReceipt(BaseModel):
    """Receipt returned after vetting an inbound email."""

    id: str
    accepted: bool
    verdict: str
    intent: str
    summary: str
    extracted_facts: list[str]
    pii_findings: list[str]
    model: str


ClientSubmissionKind = Literal[
    "context",
    "grep",
    "tool",
    "contact",
    "rubric",
    "prompt",
    "partner",
    "volunteer",
    "custom",
]
SubmissionVisibility = Literal[
    "local_only",
    "private_review",
    "consortium_private",
    "aggregate_only",
    "benchmark_public",
    "pack_public",
]
AttributionMode = Literal[
    "anonymous",
    "pseudonymous_deployment",
    "organization_tagged",
    "verified_organization",
    "public_source_only",
]
LabelSource = Literal[
    "manual_submitter",
    "tenant_default",
    "local_model_suggested",
    "server_inferred",
    "verified_registry",
]


ATTRIBUTION_LABEL_KEYS = {
    "organization",
    "organization_registry_id",
    "org",
    "submitter",
    "tenant",
    "tenant_id",
    "tenant_id_hash",
}


class SubmitterInfo(BaseModel):
    """Privacy-preserving submitter metadata for client-controlled labels."""

    tenant_id_hash: str | None = Field(default=None, max_length=160)
    organization_registry_id: str | None = Field(default=None, max_length=160)
    display_name: str | None = Field(default=None, max_length=160)
    public_attribution: bool = False


class SubmissionLabel(BaseModel):
    """One client-provided or machine-suggested metadata label."""

    key: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=240)
    source: LabelSource
    confidence: float = Field(ge=0.0, le=1.0)
    public_safe: bool = False

    @field_validator("key")
    @classmethod
    def _normalize_key(cls, value: str) -> str:
        return value.strip().lower().replace(" ", "_")

    @field_validator("value")
    @classmethod
    def _reject_label_pii(cls, value: str) -> str:
        findings = detect_pii(value)
        if findings:
            labels = ", ".join(sorted(findings))
            raise ValueError(f"label value appears to contain prohibited PII: {labels}")
        return value.strip()


class SubmissionConsent(BaseModel):
    """Granular consent flags controlling sanitized object use."""

    share_sanitized_object: bool = True
    share_aggregate_trends: bool = True
    allow_recontact: bool = False
    allow_training_use: bool = False
    allow_public_display: bool = False
    contact_publication_consent: bool = False


def _is_valid_email(value: str) -> bool:
    """Return True for a simple, dependency-free email shape check."""
    if any(char.isspace() for char in value):
        return False
    local, marker, domain = value.partition("@")
    return bool(local and marker and "." in domain and not domain.startswith(".") and not domain.endswith("."))


def _payload_pii_findings(value: object, *, path: str = "payload", depth: int = 0) -> set[str]:
    """Recursively scan free-form payload values for detector-class PII."""
    if depth > MAX_CLIENT_PAYLOAD_DEPTH:
        raise ValueError(f"payload nesting exceeds maximum depth of {MAX_CLIENT_PAYLOAD_DEPTH}")
    findings: set[str] = set()
    if isinstance(value, str):
        findings.update(detect_pii(value))
        normalized_path = path.lower().replace("_", "-")
        if value.strip() and any(token in normalized_path for token in ("passport", "visa", "national-id", "id-number")):
            findings.add("identity_document")
    elif isinstance(value, dict):
        for key, child in value.items():
            findings.update(detect_pii(str(key)))
            findings.update(_payload_pii_findings(child, path=f"{path}.{key}", depth=depth + 1))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.update(_payload_pii_findings(child, path=f"{path}[{index}]", depth=depth + 1))
    return findings


def _validate_pack_id(pack_id: str) -> str:
    """Validate the public pack id path parameter before registry lookup."""
    if not PACK_ID_PATTERN.fullmatch(pack_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pack_id must be 3-80 lowercase letters, numbers, or hyphens and start and end with a letter or number.",
        )
    return pack_id


class ClientSubmissionIn(BaseModel):
    """A submission from a deployed client (or the website's contribute form).

    Generic envelope: pick a ``kind`` to say what you are proposing, and
    drop the structured payload in ``payload``. The server-side automation
    triages ``summary`` for safety + PII; ``payload`` rides through to the
    curator queue verbatim. No raw worker case content allowed in either.
    """

    kind: ClientSubmissionKind
    visibility: SubmissionVisibility = Field(default="private_review")
    attribution_mode: AttributionMode = Field(default="anonymous")
    submitter: SubmitterInfo = Field(default_factory=SubmitterInfo)
    labels: list[SubmissionLabel] = Field(default_factory=list, max_length=30)
    consent: SubmissionConsent = Field(default_factory=SubmissionConsent)
    deployment_id: str | None = Field(
        default=None,
        max_length=80,
        description="Opaque partner-assigned identifier; appears in audit only.",
    )
    organization: str | None = Field(default=None, max_length=160)
    contact_email: str | None = Field(default=None, max_length=200)
    jurisdiction: str | None = Field(default=None, max_length=80)
    corridor: str | None = Field(default=None, max_length=120)
    public_source_url: HttpUrl | None = None
    summary: str = Field(min_length=10, max_length=2000)
    payload: dict[str, object] = Field(default_factory=dict)
    consent_public_proposal: bool = Field(
        default=True,
        description="Required True. Anything submitted here can be a public proposal.",
    )
    contact_publication_consent: bool = Field(
        default=False,
        description="If True, contact_email may be published in pack manifest.",
    )

    @model_validator(mode="before")
    @classmethod
    def _infer_legacy_attribution_mode(cls, data: object) -> object:
        """Preserve older clients that sent organization metadata before labels."""
        if not isinstance(data, dict) or "attribution_mode" in data:
            return data
        submitter = data.get("submitter")
        has_submitter_org = isinstance(submitter, dict) and bool(
            submitter.get("organization_registry_id") or submitter.get("display_name")
        )
        if data.get("organization") or has_submitter_org:
            return {**data, "attribution_mode": "organization_tagged"}
        if isinstance(submitter, dict) and submitter.get("tenant_id_hash"):
            return {**data, "attribution_mode": "pseudonymous_deployment"}
        return data

    @field_validator("summary")
    @classmethod
    def _reject_pii_in_summary(cls, value: str) -> str:
        findings = detect_pii(value)
        if findings:
            labels = ", ".join(sorted(findings))
            raise ValueError(f"summary appears to contain prohibited PII: {labels}")
        return value

    @field_validator("contact_email")
    @classmethod
    def _validate_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not _is_valid_email(trimmed):
            raise ValueError("contact_email must be a valid email address")
        return trimmed

    @field_validator("payload")
    @classmethod
    def _bound_payload_size(cls, value: dict[str, object]) -> dict[str, object]:
        serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > MAX_CLIENT_PAYLOAD_BYTES:
            raise ValueError(f"payload exceeds {MAX_CLIENT_PAYLOAD_BYTES} bytes")
        return value

    @field_validator("payload")
    @classmethod
    def _reject_pii_in_payload(cls, value: dict[str, object]) -> dict[str, object]:
        findings = _payload_pii_findings(value)
        if findings:
            labels = ", ".join(sorted(findings))
            raise ValueError(f"payload appears to contain prohibited PII: {labels}")
        return value

    @model_validator(mode="after")
    def _validate_submission_envelope(self) -> "ClientSubmissionIn":
        if self.visibility == "local_only":
            raise ValueError("local_only objects must remain on the client and cannot be sent to the hub")
        if self.visibility in {"benchmark_public", "pack_public"} and not self.consent.allow_public_display:
            raise ValueError("public visibility requires consent.allow_public_display=True")
        if self.contact_publication_consent:
            self.consent.contact_publication_consent = True
        if self.contact_publication_consent and not self.contact_email:
            raise ValueError("contact_publication_consent requires contact_email")
        if self.attribution_mode == "anonymous":
            if self.organization:
                raise ValueError("anonymous submissions cannot include organization metadata")
            if self.submitter.organization_registry_id or self.submitter.display_name or self.submitter.public_attribution:
                raise ValueError("anonymous submissions cannot include public submitter attribution")
            attribution_labels = [label.key for label in self.labels if label.key in ATTRIBUTION_LABEL_KEYS]
            if attribution_labels:
                raise ValueError("anonymous submissions cannot include attribution labels")
        if self.attribution_mode == "organization_tagged" and not (
            self.organization or self.submitter.organization_registry_id or self.submitter.display_name
        ):
            raise ValueError("organization_tagged submissions require organization metadata")
        if self.attribution_mode == "verified_organization" and not self.submitter.organization_registry_id:
            raise ValueError("verified_organization submissions require submitter.organization_registry_id")
        return self


class ClientSubmissionReceipt(BaseModel):
    """Receipt returned after a client submission."""

    id: str
    accepted: bool
    status: UpdateStatus
    automation_verdict: str
    automation_intent: str
    automation_model: str
    message: str


class RetractRequestIn(BaseModel):
    """Body for the retract endpoint. Must echo the submission id for safety."""

    submission_id: str = Field(min_length=4, max_length=40)
    deployment_id: str | None = Field(default=None, max_length=80)
    reason: str | None = Field(default=None, max_length=400)


class RetractReceipt(BaseModel):
    """Receipt returned after a retract attempt."""

    id: str
    retracted: bool
    new_status: UpdateStatus
    message: str


class IngestTextIn(BaseModel):
    """Single-file ingest payload for the local-KB endpoint."""

    text: str = Field(min_length=10, max_length=200_000)
    source_filename: str = Field(min_length=1, max_length=400)
    corridor: str | None = Field(default=None, max_length=80)
    sector: str | None = Field(default=None, max_length=80)


class AggregateTrend(BaseModel):
    """Simple anonymized aggregate trend for the hub dashboard."""

    key: str
    count: int


class HubToolExample(BaseModel):
    """Example parameters for a Gemma 4-callable public hub tool."""

    description: str
    parameters: dict[str, object]


class HubToolDefinition(BaseModel):
    """Read-only public hub tool definition for local Gemma 4 orchestration."""

    name: str
    description: str
    method: Literal["GET"]
    path: str
    safety_level: Literal["read_only_public"] = "read_only_public"
    parameters: dict[str, object]
    response_schema: dict[str, str]
    examples: list[HubToolExample]


class HubToolManifest(BaseModel):
    """Allow-listed public hub tools exposed for native function calling."""

    version: str
    orchestration_model: str
    privacy_boundary: str
    tools: list[HubToolDefinition]


class AppState(BaseModel):
    """Typed app state attached to FastAPI."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    started_at: datetime
    store: FileHubStore


def default_data_dir() -> Path:
    """Return the configured file-store directory."""
    return Path(os.environ.get("DUECARE_DATA_DIR", ".duecare")).resolve()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


ADMIN_REDACTED_KEYS = {
    "body",
    "contact_email",
    "email",
    "phone",
    "raw_text",
    "source_filename",
    "text",
}


def _admin_token() -> str | None:
    """Return the configured admin token, including the legacy alias."""
    return os.environ.get("DUECARE_ADMIN_TOKEN") or os.environ.get("DUECARE_HUB_ADMIN_TOKEN")


def _require_admin_access(request: Request) -> None:
    """Gate the troubleshooting API behind an explicit bearer-style token."""
    expected = _admin_token()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin API disabled. Set DUECARE_ADMIN_TOKEN on the deployment to enable it.",
        )
    provided = request.headers.get("x-duecare-admin-token") or request.query_params.get("token")
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid admin token.",
        )


def _admin_file_info(path: Path) -> dict[str, object]:
    """Return file metadata without reading file contents."""
    if not path.exists():
        return {"exists": False, "bytes": 0, "updated_at": None}
    stat = path.stat()
    return {
        "exists": True,
        "bytes": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


def _safe_admin_value(key: str, value: Any) -> object:
    """Return a PII-safe projection for the admin dashboard."""
    normalized_key = key.lower()
    if normalized_key == "payload":
        keys = sorted(value.keys()) if isinstance(value, dict) else []
        return {"suppressed": True, "keys": keys}
    if normalized_key in ADMIN_REDACTED_KEYS or normalized_key.endswith("_email"):
        return "[REDACTED]" if value else None
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, dict):
        return {str(child_key): _safe_admin_value(str(child_key), child_value) for child_key, child_value in value.items()}
    if isinstance(value, list):
        return [_safe_admin_value(normalized_key, item) for item in value]
    return value


def _safe_admin_record(record: dict[str, object]) -> dict[str, object]:
    """Return a redacted record suitable for troubleshooting display."""
    return {key: _safe_admin_value(key, value) for key, value in record.items()}


def _tail(records: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
    """Return newest-first records bounded to a small admin display limit."""
    bounded_limit = max(1, min(limit, 200))
    return list(reversed(records[-bounded_limit:]))


def _state(request: Request) -> AppState:
    state = getattr(request.app.state, "duecare", None)
    if not isinstance(state, AppState):
        store = FileHubStore(default_data_dir())
        store.ensure_ready()
        state = AppState(started_at=datetime.now(UTC), store=store)
        request.app.state.duecare = state
    return state


def _knowledge_packs() -> list[KnowledgePackSummary]:
    return [
        KnowledgePackSummary(
            id="duecare-global-rag-v0",
            kind="rag_docs",
            title="Global migrant-worker protection RAG pack",
            version="0.14.x",
            description=(
                "Public ILO, Palermo, corridor, and pattern-brief context for "
                "grounded Gemma 4 answers: 846 trafficking-domain documents, plus "
                "a separate 610-document corpus spanning 51 integrity verticals "
                "(corruption, financial crime, elder care, and more). Coverage across "
                "those verticals is evidence that the architecture is not "
                "single-domain; it is not a measured generalization claim."
            ),
            status="live",
            update_channel="Public-source proposals then curator review",
        ),
        KnowledgePackSummary(
            id="duecare-grep-rules-v0",
            kind="grep_rules",
            title="Exploitation and jailbreak detection rules",
            version="0.14.x",
            description=(
                "417 deterministic rules across 96 families: relabeled fees, "
                "document retention, debt pressure, sham employment status, "
                "euphemism laundering, equivocation, and jailbreak attempts. "
                "Every rule carries a citation and trigger examples."
            ),
            status="live",
            update_channel="Partner PR or public-source proposal",
        ),
        KnowledgePackSummary(
            id="duecare-contacts-v0",
            kind="contacts",
            title="Verified public contacts and complaint channels",
            version="0.14.x",
            description=(
                "36 NGO intake bundles, 38 corridor fee-cap entries, and 16 ILO "
                "convention references covering regulators, consulates, hotlines, "
                "and complaint mechanisms. Draft-only use; volatile numbers live "
                "here, never in model weights."
            ),
            status="live",
            update_channel="Human verification plus freshness checks",
        ),
        KnowledgePackSummary(
            id="duecare-trainer-adapters-v0",
            kind="examples",
            title="Approved examples for Gemma 4 adaptation",
            version="planned",
            description="Anonymized, consented, provenance-tracked examples for LoRA/adapters.",
            status="planned",
            update_channel="Trainer manifest and evaluation gate",
        ),
    ]


_ENVELOPE_CONTRACT_CACHE: tuple[frozenset[str], dict[str, list[str]]] | None = None


def _envelope_contract() -> tuple[frozenset[str], dict[str, list[str]]]:
    """Load (known types, required content keys) from the committed schema.

    The hub container does not install the duecare packages, so the
    generated ``static/envelope_schema.json`` is its single source for the
    KnowledgeObject contract (kept in sync by
    ``scripts/build_envelope_schema.py`` + ``tests/test_envelope_schema_sync.py``).
    """
    global _ENVELOPE_CONTRACT_CACHE
    if _ENVELOPE_CONTRACT_CACHE is not None:
        return _ENVELOPE_CONTRACT_CACHE
    types: set[str] = set()
    required: dict[str, list[str]] = {}
    try:
        schema = json.loads(
            (APP_DIR / "static" / "envelope_schema.json").read_text(encoding="utf-8")
        )
        types = set(schema.get("properties", {}).get("knowledge_object_type", {}).get("enum") or [])
        for clause in schema.get("allOf") or []:
            ko_type = (
                clause.get("if", {}).get("properties", {})
                .get("knowledge_object_type", {}).get("const")
            )
            keys = (
                clause.get("then", {}).get("properties", {})
                .get("content", {}).get("required") or []
            )
            if ko_type:
                required[str(ko_type)] = [str(k) for k in keys]
    except Exception:
        # Fail open to the historical hub set: the submit endpoint must not
        # 500 because a schema file is missing in a stale deployment.
        types = {
            "grep_rule", "glob_rule", "classifier_rule", "heuristic_rule",
            "rag_doc", "citation_edge", "corridor_profile", "ngo_directory",
            "persona_block", "context_snippet", "reasoning_step", "rubric_dimension",
            "tool_definition", "tool_example", "tool_chain",
            "fact_template", "upload_schema", "prompt_template",
            "envelope_schema", "audit_template", "submission_schema",
        }
        required = {}
    _ENVELOPE_CONTRACT_CACHE = (frozenset(types), required)
    return _ENVELOPE_CONTRACT_CACHE


def _object_parameters(properties: dict[str, object], required: list[str] | None = None) -> dict[str, object]:
    """Return a JSON-schema object parameter block for a tool definition."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required or [],
    }


def _hub_tool_manifest() -> HubToolManifest:
    """Return the explicit allow-list Gemma 4 can use to query the hub."""
    return HubToolManifest(
        version=__version__,
        orchestration_model=(
            "Local or Kaggle-hosted Gemma 4 may call these read-only public "
            "hub endpoints via native function calling. The Render hub does "
            "not expose a generic executor."
        ),
        privacy_boundary=(
            "Only public metadata, vetted packs, and aggregate counters are "
            "included. Admin routes, local-KB ingest, email automation, "
            "submissions, signals, and update writes are intentionally absent."
        ),
        tools=[
            HubToolDefinition(
                name="get_hub_status",
                description="Read public hub version, uptime, and aggregate record counts.",
                method="GET",
                path="/api/hub/status",
                parameters=_object_parameters({}),
                response_schema={"model": "HubStatus"},
                examples=[HubToolExample(description="Check whether the hub is live.", parameters={})],
            ),
            HubToolDefinition(
                name="list_pack_summaries",
                description="List high-level public knowledge-pack summaries for the hub landing pages.",
                method="GET",
                path="/api/hub/knowledge-packs",
                parameters=_object_parameters({}),
                response_schema={"model": "list[KnowledgePackSummary]"},
                examples=[HubToolExample(description="Show the public pack overview.", parameters={})],
            ),
            HubToolDefinition(
                name="list_packs",
                description="Search vetted public pack bodies by kind, status, jurisdiction, corridor, or tag.",
                method="GET",
                path="/api/hub/packs",
                parameters=_object_parameters(
                    {
                        "kind": {
                            "type": "string",
                            "description": "Optional pack type such as ContextPack, GrepRulePack, ToolPack, ContactPack, RubricPack, EvalPromptPack, or TrainingExamplePack.",
                        },
                        "status": {
                            "type": "string",
                            "description": "Optional pack status such as vetted, proposed, needs_review, or deprecated.",
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Optional ISO-style jurisdiction filter such as PHL or KWT.",
                        },
                        "corridor": {
                            "type": "string",
                            "description": "Optional migration corridor filter such as PHL-KWT.",
                        },
                        "tag": {
                            "type": "string",
                            "description": "Optional public pack tag such as fees or passport_retention.",
                        },
                        "latest_only": {
                            "type": "boolean",
                            "description": "Return only the latest matching version when true.",
                            "default": True,
                        },
                    }
                ),
                response_schema={"model": "PackListResponse"},
                examples=[
                    HubToolExample(
                        description="Find fee-related packs for the Philippines to Kuwait corridor.",
                        parameters={"corridor": "PHL-KWT", "tag": "fees", "latest_only": True},
                    )
                ],
            ),
            HubToolDefinition(
                name="get_pack_details",
                description="Fetch the latest public body for a specific pack id.",
                method="GET",
                path="/api/hub/packs/{pack_id}",
                parameters=_object_parameters(
                    {
                        "pack_id": {
                            "type": "string",
                            "pattern": "^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$",
                            "description": "Public pack identifier, 3-80 lowercase letters, numbers, or hyphens, starting and ending with a letter or number; for example phl-kwt-domestic.",
                        }
                    },
                    required=["pack_id"],
                ),
                response_schema={"model": "PackBody"},
                examples=[
                    HubToolExample(
                        description="Fetch the latest Philippines to Kuwait domestic-work pack.",
                        parameters={"pack_id": "phl-kwt-domestic"},
                    )
                ],
            ),
            HubToolDefinition(
                name="list_pack_versions",
                description="List public versions available for a specific pack id.",
                method="GET",
                path="/api/hub/packs/{pack_id}/versions",
                parameters=_object_parameters(
                    {
                        "pack_id": {
                            "type": "string",
                            "pattern": "^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$",
                            "description": "Public pack identifier, 3-80 lowercase letters, numbers, or hyphens, starting and ending with a letter or number; for example phl-kwt-domestic.",
                        }
                    },
                    required=["pack_id"],
                ),
                response_schema={"model": "PackVersionList"},
                examples=[
                    HubToolExample(
                        description="Check which versions can be pinned for reproducibility.",
                        parameters={"pack_id": "phl-kwt-domestic"},
                    )
                ],
            ),
            HubToolDefinition(
                name="sync_packs",
                description="Read vetted public pack changes since an optional ISO-8601 cursor.",
                method="GET",
                path="/api/hub/sync",
                parameters=_object_parameters(
                    {
                        "since": {
                            "type": "string",
                            "description": "Optional ISO-8601 timestamp cursor from a previous sync response.",
                        }
                    }
                ),
                response_schema={"model": "PackSyncResponse"},
                examples=[
                    HubToolExample(description="Initial sync of every vetted public pack.", parameters={})
                ],
            ),
            HubToolDefinition(
                name="get_aggregate_trends",
                description="Read aggregate, anonymized trend counters from public hub records.",
                method="GET",
                path="/api/hub/trends",
                parameters=_object_parameters({}),
                response_schema={"model": "list[AggregateTrend]"},
                examples=[HubToolExample(description="Summarize public aggregate trend counters.", parameters={})],
            ),
        ],
    )


def _demo_priority_examples() -> dict[str, object]:
    """Load synthetic, no-wait demo examples for recording walkthroughs."""
    return json.loads(DEMO_PRIORITY_EXAMPLES_PATH.read_text(encoding="utf-8"))


def _benchmark_page_context() -> dict[str, object]:
    """Load the DueCare Harness-Lift Benchmark leaderboard for the /benchmark page.

    The leaderboard JSON is regenerated by scripts/benchmark_leaderboard.py and committed under
    static/, so the page renders the current standings without any live model call. Degrades to an
    empty board if the file is missing or unreadable."""
    path = APP_DIR / "static" / "benchmark_leaderboard.json"
    try:
        return {"leaderboard": json.loads(path.read_text(encoding="utf-8"))}
    except Exception:  # noqa: BLE001
        return {"leaderboard": None}


def _harness_study_context() -> dict[str, object]:
    """0-100 board numbers for the /harness-study headline + per-model chart, so the study stays
    consistent with /benchmark as the live board fills.

    Reuses the committed leaderboard. Only adequately-sampled models (>= ``min_n`` graded prompts)
    are featured so a just-started run doesn't show a misleading partial bar. ``study`` is None when
    the board is unavailable, in which case the page renders its static 0-10 origin fallback."""
    ctx = _benchmark_page_context()
    lb = ctx.get("leaderboard") or {}
    min_n = 20  # only feature adequately-sampled models (a just-started run has too few prompts)
    models = [m for m in (lb.get("models") or []) if (m.get("n_prompts") or 0) >= min_n]
    if not models:
        ctx["study"] = None
        return ctx
    head = next((m for m in models if m.get("model") == "gemma4:31b"), models[0])
    ctx["study"] = {
        "featured": models,
        "headline": head,
        "avg_lift": round(sum(m.get("lift", 0.0) for m in models) / len(models), 1),
        "n_featured": len(models),
        "all_positive": all(m.get("lift", 0.0) > 0 for m in models),
        "alpha": lb.get("inter_judge_alpha"),
        "n_judges": len(lb.get("judges") or []),
    }
    return ctx


def _stats_page_context(request: Request) -> dict[str, object]:
    """Return live counters plus an explicit beta-data disclosure for /stats."""
    state = _state(request)
    signal_count, update_count = state.store.counts()
    return {
        "stats_live": {
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
            "pack_count": pack_registry.index_size(),
            "tool_count": len(_hub_tool_manifest().tools),
            "signal_count": signal_count,
            "update_proposal_count": update_count,
            "public_record_count": signal_count + update_count,
        },
        "stats_data_notice": (
            "Beta page: the headline counters are live counts from this deployment. "
            "Charts, corridor examples, review funnels, release timelines, and audit rows "
            "are synthetic/composite demo previews until production ingestion and curator "
            "governance are fully live."
        ),
    }


def create_app(*, data_dir: Path | None = None) -> FastAPI:
    """Create the Duecare AI public hub FastAPI application."""
    store = FileHubStore((data_dir or default_data_dir()).resolve())
    store.ensure_ready()
    application = FastAPI(
        title="Duecare AI Hub",
        description=(
            "Public coordination hub for anonymized migrant-worker safety signals, vetted knowledge packs, "
            "public-source update proposals, and evaluation metadata. Raw case content stays in "
            "worker-controlled or tenant-controlled deployments; this hub stores anonymized signals, "
            "public-source proposals, and metadata."
        ),
        version=__version__,
        docs_url="/api-docs",
        redoc_url="/redoc",
    )
    # CORS allowlist. Explicitly includes the existing Render hostname
    # (https://gemma4-comp.onrender.com) so all current callers — including
    # Kaggle-kernel browsers that POST to /api/submit/knowledge from
    # *.trycloudflare.com — keep working unchanged. The new apex/www
    # duecare-ai.com origins are additively allowed. allow_origin_regex
    # matches ephemeral Cloudflare tunnel and Render preview hostnames.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://duecare-ai.com",
            "https://www.duecare-ai.com",
            "https://gemma4-comp.onrender.com",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_origin_regex=r"^https://([a-z0-9-]+\.)*(trycloudflare\.com|onrender\.com)$",
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    # TrustedHostMiddleware: reject requests with a Host header that
    # doesn't match an expected hostname. Includes the Render fallback,
    # the new duecare-ai.com domain, *.onrender.com previews, local dev,
    # and 'testserver' (the default Host header used by FastAPI's
    # TestClient — must be present or pytest fails).
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "duecare-ai.com",
            "www.duecare-ai.com",
            "gemma4-comp.onrender.com",
            "*.onrender.com",
            "localhost",
            "127.0.0.1",
            "testserver",
        ],
    )
    # Per-IP rate limiting on the public mutation endpoints (subscribe,
    # outreach observe/campaign, signal intake, opencrawl). Those are
    # unauthenticated by design, so throttling is the abuse control — it
    # bounds priority-ranking pumping and store flooding. Configure via
    # DUECARE_RATE_LIMIT="requests/window_seconds" ("0" disables; default
    # 30/300). See app/ratelimit.py.
    application.add_middleware(RateLimitMiddleware)

    # Baseline security response headers. The hub serves public read-only
    # content plus a few unauthenticated intake endpoints, so these are cheap
    # defence-in-depth rather than a substitute for the auth and rate limiting
    # above. The set mirrors the project's own web security rule.
    #
    # Deliberately NOT set here:
    #   - Content-Security-Policy. The templates and the embedded workbench use
    #     inline styles and scripts, so a meaningful CSP needs per-request
    #     nonces threaded through the templates. Shipping a permissive
    #     'unsafe-inline' policy would look like protection while providing
    #     approximately none, so it is left to be done properly.
    @application.middleware("http")
    async def _security_headers(request: Request, call_next):
        response = await call_next(request)
        # Deployed behind TLS at duecare-ai.com; instructs browsers to refuse
        # plaintext for a year. Harmless on localhost, which browsers exempt.
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
        # Stop MIME sniffing turning an uploaded or generated file into script.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # No page here is meant to be framed; blocks clickjacking overlays.
        response.headers.setdefault("X-Frame-Options", "DENY")
        # Send the origin, not the full path, to third parties. Hub URLs can
        # carry knowledge-pack and campaign identifiers worth not leaking.
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        # The hub needs none of these device capabilities.
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response

    application.state.duecare = AppState(started_at=datetime.now(UTC), store=store)

    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @application.get("/api/health", response_model=HealthStatus, tags=["system"])
    async def api_health(request: Request) -> HealthStatus:
        state = _state(request)
        state.store.ensure_ready()
        return HealthStatus(
            status="ok",
            service="duecare-ai-hub",
            version=__version__,
            storage="file",
            storage_ok=True,
            data_dir=str(state.store.root),
            git_commit=_render_git_commit_prefix(),
        )

    @application.get("/api/demo/priority-examples", tags=["demo"])
    async def demo_priority_examples() -> dict[str, object]:
        """Return the synthetic example catalog used by the no-wait recording deck."""
        return _demo_priority_examples()

    @application.get("/schema/v1", include_in_schema=False)
    async def public_schema_context() -> dict[str, object]:
        """Return the stable JSON-LD context used by public knowledge objects."""
        return SCHEMA_CONTEXT_DOCUMENT

    @application.get("/schema/{kind}/1.json", include_in_schema=False)
    async def public_schema(kind: str) -> dict[str, object]:
        """Return one of the versioned transport schemas linked from the docs."""
        schema = PUBLIC_SCHEMAS.get(kind)
        if schema is None:
            raise HTTPException(status_code=404, detail="Unknown public schema")
        return schema

    @application.get("/healthz", response_model=HealthStatus, tags=["system"])
    async def healthz(request: Request) -> HealthStatus:
        return await api_health(request)

    @application.get("/api/hub/status", response_model=HubStatus, tags=["hub"])
    async def hub_status(request: Request) -> HubStatus:
        state = _state(request)
        signal_count, update_count = state.store.counts()
        return HubStatus(
            service="duecare-ai-hub",
            version=__version__,
            uptime_seconds=int((datetime.now(UTC) - state.started_at).total_seconds()),
            privacy_mode="anonymized_signals_only_no_raw_pii",
            signal_count=signal_count,
            update_proposal_count=update_count,
            counters=dict(state.store.trends()),
        )

    @application.get("/api/hub/tools/manifest", response_model=HubToolManifest, tags=["tools"])
    async def hub_tools_manifest() -> HubToolManifest:
        """Return read-only public hub tools for local Gemma 4 orchestration."""
        return _hub_tool_manifest()

    @application.get(
        "/api/hub/knowledge-packs",
        response_model=list[KnowledgePackSummary],
        tags=["knowledge-packs"],
    )
    async def list_knowledge_packs() -> list[KnowledgePackSummary]:
        return _knowledge_packs()

    @application.get(
        "/api/hub/knowledge/download",
        tags=["knowledge-packs"],
        summary="Download anonymized knowledge bundle (ZIP)",
    )
    async def hub_knowledge_download(vetted: bool = True) -> Response:
        """Stream a ZIP of public KnowledgeObject envelopes.

        With ``vetted=true`` (default) only curator-approved packs are
        included. With ``vetted=false`` proposed / needs_review packs
        are included too, each entry carrying a ``status`` field so the
        recipient can distinguish. All entries are pre-anonymized at
        ingest; the hub stores no raw worker identifiers.
        """
        import hashlib as _hashlib
        import io as _io
        import json as _json
        import zipfile as _zipfile
        from datetime import UTC as _UTC
        from datetime import datetime as _dt
        packs = _knowledge_packs()
        if vetted:
            packs = [p for p in packs if p.status == "live"]
        buf = _io.BytesIO()
        with _zipfile.ZipFile(buf, "w", _zipfile.ZIP_DEFLATED) as zf:
            for p in packs:
                content = {
                    "title": p.title,
                    "kind": p.kind,
                    "description": p.description,
                    "update_channel": p.update_channel,
                }
                envelope = {
                    "schema_version": "1.0",
                    "knowledge_object_type": "knowledge_pack_summary",
                    "id": p.id,
                    "version": p.version,
                    "provenance": {
                        "created_by": "duecare-ai.com hub",
                        "served_at": _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ"),
                        "vetted": p.status == "live",
                        "status": p.status,
                        # Tamper-detection handle: sha256 over sorted-key
                        # compact JSON of `content` (same recipe as the
                        # kernel's knowledge_taxonomy.content_sha256).
                        "content_sha256": _hashlib.sha256(
                            _json.dumps(content, ensure_ascii=False, sort_keys=True,
                                          separators=(",", ":")).encode("utf-8")
                        ).hexdigest(),
                    },
                    "content": content,
                    "tags": [],
                    "extensions": {},
                }
                zf.writestr(f"{p.kind}/{p.id}.json",
                              _json.dumps(envelope, indent=2, sort_keys=True))
            manifest = {
                "schema_version": "1.0",
                "exported_at": _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ"),
                "exporter": "duecare-ai.com/api/hub/knowledge/download",
                "vetted_only": bool(vetted),
                "n_entries": len(packs),
                "anonymization_invariant": (
                    "All entries are pre-anonymized at ingest. The hub "
                    "stores no raw worker identifiers; PII would have "
                    "been rejected at the schema boundary before any pack "
                    "reached this download."
                ),
            }
            zf.writestr("manifest.json", _json.dumps(manifest, indent=2))
        buf.seek(0)
        fname = ("duecare_knowledge_vetted.zip" if vetted
                  else "duecare_knowledge_all.zip")
        return Response(
            content=buf.read(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )

    @application.get("/api/curator/queue", tags=["curator"])
    async def curator_queue(request: Request) -> dict:
        """Stage 04 queue. No raw content -- only metadata + sha256."""
        _require_admin_access(request)
        import json as _json
        state = _state(request)
        root = state.store.root
        items: list[dict] = []
        decided: set[tuple[str, int]] = set()
        dpath = root / "curator_decisions.jsonl"
        if dpath.exists():
            for line in dpath.read_text(encoding="utf-8").splitlines():
                try:
                    d = _json.loads(line)
                    decided.add((d.get("submission_id"), int(d.get("item_index", -1))))
                except Exception:
                    continue
        spath = root / "knowledge_submissions.jsonl"
        if spath.exists():
            for line in spath.read_text(encoding="utf-8").splitlines():
                try:
                    sub = _json.loads(line)
                except Exception:
                    continue
                sid = sub.get("submission_id")
                for i, a in enumerate(sub.get("accepted", [])):
                    items.append({
                        "submission_id": sid,
                        "item_index": i,
                        "type": a.get("type"),
                        "id": a.get("id"),
                        "content_sha256": a.get("content_sha256"),
                        "submitted_at": sub.get("ts"),
                        "decision": "decided" if (sid, i) in decided else "pending",
                    })
        return {
            "pending": [r for r in items if r["decision"] == "pending"],
            "decided": [r for r in items if r["decision"] == "decided"],
            "n_pending": sum(1 for r in items if r["decision"] == "pending"),
            "n_decided": sum(1 for r in items if r["decision"] == "decided"),
        }

    @application.post(
        "/api/curator/decide/{submission_id}/{item_index}",
        response_model=CuratorDecisionReceipt,
        tags=["curator"],
    )
    async def curator_decide(
        request: Request, submission_id: str, item_index: int,
        body: CuratorDecisionIn,
    ) -> CuratorDecisionReceipt:
        """Stage 04 -- curator accepts / rejects / requests changes."""
        _require_admin_access(request)
        import hashlib as _hashlib
        import json as _json
        from datetime import UTC as _UTC
        from datetime import datetime as _dt
        if body.decision not in {"accept", "reject", "request_changes"}:
            raise HTTPException(400, "decision must be accept|reject|request_changes")
        state = _state(request)
        root = state.store.root
        ts = _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        key_hash = None
        if body.curator_key:
            key_hash = _hashlib.sha256(body.curator_key.encode()).hexdigest()[:16]
        entry = {
            "ts": ts,
            "submission_id": submission_id,
            "item_index": item_index,
            "decision": body.decision,
            "reason": body.reason,
            "curator_key_sha256_prefix": key_hash,
        }
        dpath = root / "curator_decisions.jsonl"
        try:
            with open(dpath, "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
        except Exception as e:
            raise HTTPException(500, f"decision log write failed: {e}")
        promoted = False
        published_pack = None
        if body.decision == "accept":
            vpath = root / "vetted_items.jsonl"
            try:
                with open(vpath, "a", encoding="utf-8") as f:
                    f.write(_json.dumps({
                        "promoted_at": ts,
                        "submission_id": submission_id,
                        "item_index": item_index,
                    }) + "\n")
                promoted = True
            except Exception:
                pass
            # Complete the distribution pipeline: write the accepted item body
            # (retained at submit in proposed_items/) into PACKS_DIR as a vetted
            # pack and hot-reload the registry, so /api/hub/sync actually serves
            # it. Without this, an accept was a no-op from the syncing kernel's
            # perspective. Best-effort: a missing proposed_items file (older
            # submission) leaves vetted_items.jsonl as the only record.
            try:
                proposed = root / "proposed_items" / f"{submission_id}.json"
                if proposed.exists():
                    bundle = _json.loads(proposed.read_text(encoding="utf-8"))
                    bodies = bundle.get("items") or []
                    if 0 <= item_index < len(bodies):
                        item_body = bodies[item_index]
                        pack_id = str(item_body.get("id") or submission_id)
                        version = ts.replace(":", "-")
                        pack_payload = {
                            "@type": item_body.get("knowledge_object_type", "ContextPack"),
                            "id": pack_id,
                            "version": version,
                            "status": "vetted",
                            "provenance": {
                                "vetted_at": ts,
                                "submission_id": submission_id,
                                "curator_key_sha256_prefix": key_hash,
                            },
                            "content": item_body,
                        }
                        pack_file = pack_registry.PACKS_DIR / f"{pack_id}__{version}.json"
                        pack_file.parent.mkdir(parents=True, exist_ok=True)
                        pack_file.write_text(_json.dumps(pack_payload, indent=2), encoding="utf-8")
                        pack_registry.reload()
                        published_pack = f"{pack_id}__{version}"
            except Exception:
                pass
        return CuratorDecisionReceipt(
            ok=True, submission_id=submission_id, item_index=item_index,
            decision=body.decision, promoted_to_vetted=promoted,
            audit_path=str(dpath),
            note=(
                (f"Promoted to vetted and published pack {published_pack}; "
                 "now served by /api/hub/sync." if published_pack
                 else "Promoted to vetted.") if promoted else
                f"Decision recorded: {body.decision}."
            ),
        )

    @application.post(
        "/api/newsletter/subscribe",
        response_model=SubscriberReceipt,
        tags=["automation"],
    )
    async def newsletter_subscribe(request: Request, body: SubscriberIn) -> SubscriberReceipt:
        """OpenClaw-style subscriber intake. The raw email is hashed
        (sha256) and discarded in this handler; only the hash + topics +
        organization persist on the hub per the privacy invariant.
        """
        import hashlib as _hashlib
        import json as _json
        import uuid as _uuid
        from datetime import UTC as _UTC
        from datetime import datetime as _dt
        if "@" not in (body.email or ""):
            raise HTTPException(400, "invalid email")
        state = _state(request)
        root = state.store.root
        ts = _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        sid = f"sub_{_uuid.uuid4().hex[:12]}"
        email_sha = _hashlib.sha256(body.email.encode()).hexdigest()
        entry = {
            "ts": ts,
            "subscriber_id": sid,
            "email_sha256": email_sha,
            "topics": body.topics,
            "organization": body.organization,
            "role": body.role,
            "consent_to_outreach": bool(body.consent_to_outreach),
        }
        spath = root / "subscribers.jsonl"
        try:
            with open(spath, "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
        except Exception as e:
            raise HTTPException(500, f"subscriber log write failed: {e}")
        return SubscriberReceipt(
            ok=True, subscriber_id=sid, email_sha256=email_sha,
            n_topics=len(body.topics),
            note=(
                "Subscription queued. The raw email is not stored on the "
                "hub; only the sha256 + topics + organization persist for "
                "curator outreach planning."
            ),
        )


    def _load_subscribers(root) -> list[dict]:
        import json as _json
        spath = root / "subscribers.jsonl"
        if not spath.exists():
            return []
        out: list[dict] = []
        for line in spath.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(_json.loads(line))
            except Exception:
                continue
        return out

    @application.get("/api/outreach/gaps", tags=["outreach"])
    async def outreach_gaps(request: Request) -> dict:
        """The prioritized context gaps the hub wants civil society to help
        verify. Priority rises as field observations corroborate a gap."""
        from dataclasses import asdict as _asdict
        state = _state(request)
        gaps = outreach.detect_context_gaps(state.store.root)
        subs = _load_subscribers(state.store.root)
        return {
            "count": len(gaps),
            "n_subscribers": len(subs),
            "smtp_configured": outreach._smtp_configured(),
            "delivery_mode": "draft_only",
            "can_send": False,
            "stores_recipient_addresses": False,
            "gaps": [_asdict(g) for g in gaps],
        }

    @application.post("/api/outreach/campaign", tags=["outreach"])
    async def outreach_campaign(request: Request, body: OutreachCampaignIn) -> dict:
        """Draft a targeted solicitation campaign for one gap: pick opted-in
        subscribers whose topics match, draft the email via the automation
        engine, and record an audit row. Campaigns are draft-only — the hub
        stores no raw addresses; a curator needs a separately owned, consented
        address book to resolve hashes before using their own mailer."""
        from dataclasses import asdict as _asdict
        from datetime import UTC as _UTC
        from datetime import datetime as _dt
        state = _state(request)
        gap = outreach.gap_by_id(state.store.root, body.gap_id)
        if gap is None:
            raise HTTPException(404, f"unknown gap_id: {body.gap_id}")
        subs = _load_subscribers(state.store.root)
        campaign = outreach.draft_campaign(
            state.store.root, gap, subs,
            compose=automation.compose_outbound_request,
        )
        ts = _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        outreach.record_campaign(state.store.root, campaign, ts)
        return {"ok": True, "campaign": _asdict(campaign)}

    @application.post("/api/outreach/observe", tags=["outreach"])
    async def outreach_observe(request: Request, body: OutreachObserveIn) -> dict:
        """Fold a civil-society observation reply into context prioritization.
        Vets the reply through the same PII/intent gate as the inbound-email
        path, then records a weighted context signal for the named gap."""
        from dataclasses import asdict as _asdict
        from datetime import UTC as _UTC
        from datetime import datetime as _dt
        state = _state(request)
        if outreach.gap_by_id(state.store.root, body.gap_id) is None:
            raise HTTPException(404, f"unknown gap_id: {body.gap_id}")
        verdict = automation.vet_inbound_email(body.subject, body.body, body.sender_domain)
        ts = _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        sig = outreach.ingest_observation(
            state.store.root, body.gap_id, verdict=verdict,
            sender_email=body.sender_email, ts=ts,
        )
        return {"ok": True, "signal": _asdict(sig),
                "vet": {"verdict": verdict.verdict, "intent": verdict.intent,
                        "summary": verdict.summary, "pii_findings": verdict.pii_findings}}

    @application.get("/api/outreach/priorities", tags=["outreach"])
    async def outreach_priorities(request: Request) -> dict:
        """Ranked context priorities derived from accumulated observations,
        each with a candidate ranking/rubric dimension so outreach feeds the
        grading surface, not just the RAG corpus."""
        state = _state(request)
        priorities = outreach.prioritized_context(state.store.root)
        return {"count": len(priorities), "priorities": priorities}

    @application.post("/api/outreach/propose-gaps", tags=["outreach"])
    async def outreach_propose_gaps(request: Request, body: OutreachProposeGapsIn) -> dict:
        """Add LLM-drafted outreach questions as PROPOSED context gaps (human-reviewable).

        The drafts come from `scripts/llm_generate.py --task outreach-drafts`. They become
        solicitable gaps a curator can choose to draft a campaign for; sending stays
        draft-only and human-gated (the hub stores no raw addresses), so nothing is
        auto-sent. The LLM only proposes WHICH questions to ask."""
        from datetime import UTC as _UTC
        from datetime import datetime as _dt
        state = _state(request)
        ts = _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        added = outreach.ingest_proposed_gaps(
            state.store.root, body.drafts, model=body.model, ts=ts)
        return {"ok": True, "n_proposed": len(added), "proposed_gaps": added,
                "note": "proposed gaps are human-reviewable; campaigns remain draft-only."}

    @application.get("/api/outreach/experts/{gap_id}", tags=["outreach"])
    async def outreach_experts(request: Request, gap_id: str) -> dict:
        """Scan the vetted support-org directory for experts best placed to answer a gap.

        Returns a ranked shortlist of PUBLIC organisations (NGO hotlines, unions, shelters,
        IOM/ILO desks) with their public contact -- so a curator has someone to reach out to
        for a gap, rather than only waiting for inbound subscribers. Suggestion only: a human
        does the actual outreach."""
        from app import experts
        state = _state(request)
        gap = outreach.gap_by_id(state.store.root, gap_id)
        if gap is None:
            raise HTTPException(404, f"unknown gap_id: {gap_id}")
        matches = experts.match_experts(gap)
        return {
            "gap_id": gap_id, "topic": gap.topic, "corridor": gap.corridor,
            "n_directory": len(experts.load_orgs()),
            "n_matches": len(matches), "experts": matches,
            "note": "public support orgs suggested for outreach; a human reaches out.",
        }


    @application.post(
        "/api/submit/knowledge",
        response_model=KnowledgeSubmissionReceipt,
        tags=["knowledge-packs"],
        summary="Receive anonymized knowledge submissions from kernel clients",
    )
    async def submit_knowledge(
        request: Request, body: KnowledgeSubmissionIn,
    ) -> KnowledgeSubmissionReceipt:
        """Stages 01-03 of the vetting process:
          1. Receive payload from a kernel client
          2. Validate every KnowledgeObject envelope shape
          3. Re-run server-side PII regex (Stage 03 hard gate)
        Accepted items land in <state>/knowledge_submissions.jsonl with
        status="proposed". A curator picks them up (Stage 04) and signs
        vetted releases (Stage 05).
        """
        import hashlib as _hashlib
        import json as _json
        import re as _re
        from datetime import UTC as _UTC
        from datetime import datetime as _dt

        ts = _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        run_id = body.submission_id or f"hub_submit_{ts}"
        items = body.items or []

        schema_types, required_keys = _envelope_contract()
        # knowledge_pack_summary is hub-only metadata, not a kernel leaf type.
        KO_TYPES_HUB = set(schema_types) | {"knowledge_pack_summary"}

        PII_PATTERNS = [
            ("EMAIL",  _re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
            ("PHONE",  _re.compile(r"\+?\d[\d\-\s]{7,}\d")),
            ("ID",     _re.compile(r"\b[A-Z]{1,3}-?\d{6,}\b")),
            ("PERSON", _re.compile(r"\b(?:Ms\.|Mr\.|Mrs\.|Dr\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")),
        ]

        def _contains_pii(blob: str) -> Optional[str]:
            for label, pat in PII_PATTERNS:
                if pat.search(blob):
                    return label
            return None

        accepted: list[dict] = []
        accepted_bodies: list[dict] = []
        rejected_schema: list[dict] = []
        rejected_pii: list[dict] = []
        duplicates: list[dict] = []

        # Idempotency: a resubmission of identical content is acknowledged,
        # not re-queued for curation.
        state = _state(request)
        seen: set[tuple[str, str, str]] = set()
        prior_path = state.store.root / "knowledge_submissions.jsonl"
        if prior_path.exists():
            for line in prior_path.read_text(encoding="utf-8").splitlines():
                try:
                    prior = _json.loads(line)
                except Exception:
                    continue
                for a in prior.get("accepted") or []:
                    seen.add((str(a.get("type")), str(a.get("id")), str(a.get("content_sha256"))))

        for i, item in enumerate(items):
            if not isinstance(item, dict):
                rejected_schema.append({"i": i, "reason": "not a JSON object"})
                continue
            if item.get("schema_version") != "1.0":
                rejected_schema.append({"i": i, "reason": 'schema_version must be "1.0"'})
                continue
            ko_type = item.get("knowledge_object_type")
            if ko_type not in KO_TYPES_HUB:
                rejected_schema.append({"i": i, "reason": f"unknown type: {ko_type}"})
                continue
            ko_id = item.get("id")
            if not isinstance(ko_id, str) or not _re.match(r"^[a-z0-9][a-z0-9\-_]*$", ko_id or ""):
                rejected_schema.append({"i": i, "reason": "id must be kebab-case non-empty"})
                continue
            content = item.get("content") or {}
            if not isinstance(content, dict):
                rejected_schema.append({"i": i, "reason": "content must be a JSON object"})
                continue
            missing = [k for k in required_keys.get(ko_type, []) if k not in content]
            if missing:
                rejected_schema.append({
                    "i": i,
                    "id": ko_id,
                    "reason": (
                        f"content for `{ko_type}` is missing required key(s): "
                        f"{', '.join(missing)} (see /static/envelope_schema.json)"
                    ),
                })
                continue
            blob = _json.dumps(content, ensure_ascii=False)
            hit = _contains_pii(blob)
            if hit:
                rejected_pii.append({"i": i, "id": ko_id, "label": hit})
                continue
            chash = _hashlib.sha256(blob.encode()).hexdigest()
            if (str(ko_type), str(ko_id), chash) in seen:
                duplicates.append({"i": i, "id": ko_id})
                continue
            seen.add((str(ko_type), str(ko_id), chash))
            accepted.append({
                "type": ko_type,
                "id": ko_id,
                "content_sha256": chash,
            })
            accepted_bodies.append(item)

        # Retain the accepted item BODIES (already client-anonymized AND past
        # the hub PII gate above — these are non-PII knowledge objects, not raw
        # worker content) in a separate proposed_items store so a curator
        # `accept` can promote them into a distributable pack. The audit log
        # (knowledge_submissions.jsonl) stays hash-only; full content lives
        # only here, keyed by submission, until a human vets it.
        if accepted_bodies:
            try:
                proposed_dir = state.store.root / "proposed_items"
                proposed_dir.mkdir(parents=True, exist_ok=True)
                (proposed_dir / f"{run_id}.json").write_text(
                    _json.dumps({"submission_id": run_id, "ts": ts, "items": accepted_bodies},
                                ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception:
                pass

        audit_dir = state.store.root
        try:
            audit_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        audit_path = audit_dir / "knowledge_submissions.jsonl"

        payload_blob = _json.dumps(
            {"run_id": run_id, "ts": ts, "items": items},
            sort_keys=True, ensure_ascii=False,
        ).encode("utf-8")
        sha = _hashlib.sha256(payload_blob).hexdigest()

        entry = {
            "ts": ts,
            "submission_id": run_id,
            "action": "hub/submit/knowledge",
            "n_items": len(items),
            "n_accepted": len(accepted),
            "n_rejected_schema": len(rejected_schema),
            "n_rejected_pii": len(rejected_pii),
            "n_duplicates": len(duplicates),
            "sha256_blob": sha,
            "accepted": accepted,
            "rejected_schema": rejected_schema,
            "rejected_pii": rejected_pii,
            "duplicates": duplicates,
            "client_ts": body.ts,
        }
        try:
            with open(audit_path, "a", encoding="utf-8") as f:
                f.write(_json.dumps(entry) + "\n")
        except Exception:
            pass

        note = (
            f"Accepted {len(accepted)} of {len(items)} items into Stage 01 "
            "(Proposed). They will be reviewed by a curator (Stage 04) before "
            "publication as vetted (Stage 05). See /hub#hub-vetting."
        )
        if rejected_pii:
            note += (
                f" {len(rejected_pii)} item(s) rejected at the Stage 03 PII "
                "hard gate -- re-anonymize and resubmit."
            )
        if duplicates:
            note += (
                f" {len(duplicates)} item(s) were exact duplicates of prior "
                "accepted submissions and were acknowledged without re-queueing."
            )

        return KnowledgeSubmissionReceipt(
            ok=True,
            submission_id=run_id,
            n_items=len(items),
            n_accepted=len(accepted),
            n_rejected_schema=len(rejected_schema),
            n_rejected_pii=len(rejected_pii),
            n_duplicates=len(duplicates),
            sha256_blob=sha,
            status="proposed",
            audit_path=str(audit_path),
            note=note,
        )



    # ---- Pack registry (real downloadable content) ---------------------

    @application.get("/api/hub/packs", tags=["knowledge-packs"])
    async def list_packs(
        kind: str | None = None,
        status_: str | None = None,
        status: str | None = None,
        jurisdiction: str | None = None,
        corridor: str | None = None,
        tag: str | None = None,
        latest_only: bool = True,
    ) -> dict[str, object]:
        """Filtered pack list. Returns the latest version of each match by default.

        Filters compose: pass any subset of ``kind`` (ContextPack /
        GrepRulePack / ToolPack / ContactPack / RubricPack / EvalPromptPack
        / TrainingExamplePack), status (``status`` or its legacy alias
        ``status_``: vetted / proposed / needs_review / deprecated),
        ``jurisdiction`` (ISO code), ``corridor`` (e.g. ``PHL-KWT``), ``tag``.
        Set ``latest_only=false`` to get every version that matches.

        ``status`` is the canonical query key (matches the tool manifest);
        ``status_`` is accepted for back-compat with the reference hub_client.
        """
        status_filter = status if status is not None else status_
        bodies = pack_registry.list_packs(
            kind=kind,
            status=status_filter,
            jurisdiction=jurisdiction,
            corridor=corridor,
            tag=tag,
            latest_only=latest_only,
        )
        return {
            "count": len(bodies),
            "filters": {
                "kind": kind,
                "status": status_filter,
                "jurisdiction": jurisdiction,
                "corridor": corridor,
                "tag": tag,
                "latest_only": latest_only,
            },
            "available_kinds": pack_registry.known_kinds(),
            "available_corridors": pack_registry.known_corridors(),
            "available_jurisdictions": pack_registry.known_jurisdictions(),
            "available_tags": pack_registry.known_tags(),
            "packs": bodies,
        }

    @application.get("/api/hub/packs/{pack_id}", tags=["knowledge-packs"])
    async def get_latest_pack(pack_id: str) -> dict[str, object]:
        """Resolve the latest version of a pack by id."""
        pack_id = _validate_pack_id(pack_id)
        body = pack_registry.get_pack(pack_id)
        if body is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No pack with id '{pack_id}' is registered.",
            )
        return body

    @application.get("/api/hub/packs/{pack_id}/versions", tags=["knowledge-packs"])
    async def list_pack_versions(pack_id: str) -> dict[str, object]:
        """List every known version of a pack (newest first)."""
        pack_id = _validate_pack_id(pack_id)
        versions = pack_registry.list_versions(pack_id)
        if not versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No pack with id '{pack_id}' is registered.",
            )
        return {"id": pack_id, "count": len(versions), "versions": versions}

    @application.get("/api/hub/packs/{pack_id}/{version}", tags=["knowledge-packs"])
    async def get_pinned_pack(pack_id: str, version: str) -> dict[str, object]:
        """Resolve a specific version of a pack. Pin this in production."""
        pack_id = _validate_pack_id(pack_id)
        body = pack_registry.get_pack(pack_id, version)
        if body is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pack '{pack_id}' has no version '{version}'.",
            )
        return body

    @application.get("/api/hub/sync", tags=["knowledge-packs"])
    async def sync_packs(since: str | None = None) -> dict[str, object]:
        """Incremental sync: list every vetted pack vetted after ``since``.

        ``since`` is an ISO-8601 timestamp. Use the ``next_cursor`` value
        from a previous response as the next ``since`` to get only the
        deltas. ``since=None`` returns every vetted pack.
        """
        cursor: datetime | None = None
        if since:
            try:
                cursor = datetime.fromisoformat(since.replace("Z", "+00:00"))
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid ISO timestamp for `since`: {exc}",
                ) from exc
        return pack_registry.sync_since(cursor)

    @application.get(
        "/api/knowledge/packs",
        tags=["knowledge-packs"],
        summary="Runtime-ready knowledge packs for on-device / kernel consumers",
    )
    async def knowledge_packs(
        vetted: bool = True,
        kind: str | None = None,
        jurisdiction: str | None = None,
        corridor: str | None = None,
        tag: str | None = None,
    ) -> dict[str, object]:
        """Registry packs projected into the flat runtime shape on-device
        consumers execute: ``{slug, version, trust, rules, facts, ...}``.

        Same single registry source of truth as ``/api/hub/packs`` — that
        route returns the rich JSON-LD envelopes for federation / curation;
        this one returns the runtime projection (``rules`` for deterministic
        GREP, ``facts`` for local RAG) so a kernel can sync and execute
        without re-implementing the pack schema. The projection lives in
        :mod:`app.runtime_packs`, the single place that knows each
        ``@type``'s content layout.

        Defaults to vetted-only (the safe default for on-device consumers);
        pass ``vetted=false`` to include proposed / community-submitted
        packs, each tagged ``trust:"unvetted"`` so a consumer can fail
        closed. The same ``kind`` / ``jurisdiction`` / ``corridor`` / ``tag``
        filters as ``/api/hub/packs`` compose here.
        """
        bodies = pack_registry.list_packs(
            kind=kind,
            status="vetted" if vetted else None,
            jurisdiction=jurisdiction,
            corridor=corridor,
            tag=tag,
        )
        packs = [runtime_packs.to_runtime_pack(body).model_dump() for body in bodies]
        return {"count": len(packs), "vetted_only": vetted, "packs": packs}

    @application.post(
        "/api/hub/signals",
        response_model=SignalReceipt,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["signals"],
    )
    async def submit_signal(request: Request, body: AnonymizedSignalIn) -> SignalReceipt:
        findings = detect_pii(body.summary)
        if findings:
            raise HTTPException(
                status_code=422,
                detail="Signal rejected because it appears to contain raw PII.",
            )
        state = _state(request)
        now = datetime.now(UTC)
        summary_hash = _sha256_text(body.summary)
        record = AnonymizedSignalRecord(
            **body.model_dump(),
            id=f"sig_{uuid.uuid4().hex[:12]}",
            received_at=now,
            summary_sha256=summary_hash,
        )
        state.store.append("signals.jsonl", record.model_dump(mode="json"))
        return SignalReceipt(
            id=record.id,
            accepted=True,
            received_at=now,
            summary_sha256=summary_hash,
            message="Accepted anonymized signal. Raw PII is not stored by Duecare AI.",
        )

    @application.get("/api/hub/trends", response_model=list[AggregateTrend], tags=["signals"])
    async def aggregate_trends(request: Request) -> list[AggregateTrend]:
        state = _state(request)
        return [
            AggregateTrend(key=key, count=value)
            for key, value in sorted(state.store.trends().items(), key=lambda item: (-item[1], item[0]))
        ]

    @application.post(
        "/api/hub/opencrawl/updates",
        response_model=UpdateReceipt,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["updates"],
    )
    async def submit_opencrawl_update(request: Request, body: OpenCrawlUpdateIn) -> UpdateReceipt:
        # The automation's edge filter runs alongside the schema-level PII
        # regex so we never store an update that the LLM evaluator rejects.
        findings = detect_pii(body.change_summary)
        if findings:
            raise HTTPException(
                status_code=422,
                detail="Update rejected because the summary appears to contain raw PII.",
            )
        verdict = automation.evaluate_submission(body.change_summary, kind="context")
        if verdict.verdict == "reject":
            raise HTTPException(
                status_code=422,
                detail=f"Server automation rejected this update: {'; '.join(verdict.reasons) or 'policy violation'}.",
            )
        state = _state(request)
        proposal = UpdateProposalRecord(
            **body.model_dump(),
            id=f"upd_{uuid.uuid4().hex[:12]}",
            status="proposed" if verdict.verdict == "needs_curator_review" else "needs_review",
            received_at=datetime.now(UTC),
        )
        record = proposal.model_dump(mode="json")
        record["automation"] = {
            "verdict": verdict.verdict,
            "intent": verdict.intent,
            "reasons": verdict.reasons,
            "safety_findings": verdict.safety_findings,
            "model": verdict.model,
        }
        state.store.append("updates.jsonl", record)
        return UpdateReceipt(
            id=proposal.id,
            accepted=True,
            status=proposal.status,
            message="Accepted as a proposed update. A curator must approve before any pack changes.",
            automation_verdict=verdict.verdict,
            automation_intent=verdict.intent,
            automation_model=verdict.model,
        )

    @application.get("/api/hub/opencrawl/updates", response_model=list[UpdateProposalRecord], tags=["updates"])
    async def list_opencrawl_updates(request: Request, limit: int = 200) -> list[UpdateProposalRecord]:
        # Admin-only + bounded: the raw proposal log can carry submitter contact
        # emails (when consented) and grows unbounded as the Sentinel harvests,
        # so it must not be a public, full-table dump.
        _require_admin_access(request)
        state = _state(request)
        records = state.store.read_all("updates.jsonl")
        if limit and limit > 0:
            records = records[-limit:]
        return [UpdateProposalRecord.model_validate(record) for record in records]

    @application.post(
        "/api/hub/automation/inbound-email",
        response_model=InboundEmailReceipt,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["automation"],
    )
    async def submit_inbound_email(request: Request, body: InboundEmailIn) -> InboundEmailReceipt:
        """Email-gateway webhook: an expert replied to a solicitation.

        The server automation classifies intent + extracts public-source
        facts from the body. The structured record lands in updates.jsonl
        for curator review; nothing auto-publishes.
        """
        verdict = automation.vet_inbound_email(body.subject, body.body, body.sender_domain)
        state = _state(request)
        record_id = f"inb_{uuid.uuid4().hex[:12]}"
        record = {
            "id": record_id,
            "received_at": body.received_at.isoformat(),
            "sender_domain": body.sender_domain,
            "subject": body.subject,
            "body_sha256": _sha256_text(body.body),
            "in_reply_to": body.in_reply_to,
            "automation": {
                "verdict": verdict.verdict,
                "intent": verdict.intent,
                "summary": verdict.summary,
                "extracted_facts": verdict.extracted_facts,
                "pii_findings": verdict.pii_findings,
                "model": verdict.model,
            },
        }
        state.store.append("updates.jsonl", record)
        return InboundEmailReceipt(
            id=record_id,
            accepted=verdict.verdict != "reject",
            verdict=verdict.verdict,
            intent=verdict.intent,
            summary=verdict.summary,
            extracted_facts=verdict.extracted_facts,
            pii_findings=verdict.pii_findings,
            model=verdict.model,
        )

    def _render(template_name: str, request: Request) -> HTMLResponse:
        context: dict[str, object] = {"version": __version__}
        if template_name == "stats.html":
            context.update(_stats_page_context(request))
        elif template_name == "benchmark.html":
            context.update(_benchmark_page_context())
        elif template_name in ("harness-study.html", "evaluation.html", "study-2026-07.html"):
            context.update(_harness_study_context())
        return templates.TemplateResponse(request, template_name, context)

    def _make_route(template_name: str):
        async def _handler(request: Request) -> HTMLResponse:
            return _render(template_name, request)

        return _handler

    @application.get("/admin", response_class=HTMLResponse, tags=["ui"], include_in_schema=False)
    async def admin_page(request: Request) -> HTMLResponse:
        """Render the token-gated troubleshooting page outside the public sitemap."""
        return _render("admin.html", request)

    for path, template_name in PAGE_ROUTES.items():
        application.add_api_route(
            path,
            _make_route(template_name),
            response_class=HTMLResponse,
            tags=["ui"],
            name=f"page::{template_name}",
            include_in_schema=False,
        )

    @application.post(
        "/api/hub/client/submission",
        response_model=ClientSubmissionReceipt,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["client"],
    )
    async def submit_client(request: Request, body: ClientSubmissionIn) -> ClientSubmissionReceipt:
        """Generic deployment-side submission endpoint.

        The website's /contribute form posts here. A deployed DueCare
        client posts here from inside the runtime when an operator
        accepts a "share this update" prompt. Server-side automation runs
        the same content-safety + PII triage either way; the curator
        queue is shared.
        """
        if not body.consent_public_proposal:
            raise HTTPException(
                status_code=422,
                detail="consent_public_proposal must be True; the hub only accepts public proposals.",
            )
        verdict = automation.evaluate_submission(body.summary, kind=body.kind)
        if verdict.verdict == "reject":
            raise HTTPException(
                status_code=422,
                detail=f"Server automation rejected this submission: {'; '.join(verdict.reasons) or 'policy violation'}.",
            )
        state = _state(request)
        record_id = f"cli_{uuid.uuid4().hex[:12]}"
        proposal_status: UpdateStatus = (
            "needs_review" if verdict.verdict == "needs_curator_review" else "proposed"
        )
        contact_can_publish = body.contact_publication_consent or body.consent.contact_publication_consent
        record = {
            "id": record_id,
            "received_at": datetime.now(UTC).isoformat(),
            "kind": body.kind,
            "visibility": body.visibility,
            "attribution_mode": body.attribution_mode,
            "submitter": body.submitter.model_dump(mode="json"),
            "labels": [label.model_dump(mode="json") for label in body.labels],
            "consent": body.consent.model_dump(mode="json"),
            "deployment_id": body.deployment_id,
            "organization": body.organization,
            "jurisdiction": body.jurisdiction,
            "corridor": body.corridor,
            "public_source_url": str(body.public_source_url) if body.public_source_url else None,
            "summary": body.summary,
            "payload": body.payload,
            "status": proposal_status,
            "contact_email": body.contact_email if contact_can_publish else None,
            "contact_email_sha256": _sha256_text(body.contact_email) if body.contact_email and not contact_can_publish else None,
            "contact_publication_consent": contact_can_publish,
            "automation": {
                "verdict": verdict.verdict,
                "intent": verdict.intent,
                "reasons": verdict.reasons,
                "safety_findings": verdict.safety_findings,
                "model": verdict.model,
            },
        }
        state.store.append("updates.jsonl", record)
        return ClientSubmissionReceipt(
            id=record_id,
            accepted=True,
            status=proposal_status,
            automation_verdict=verdict.verdict,
            automation_intent=verdict.intent,
            automation_model=verdict.model,
            message=(
                "Accepted as a proposed submission. A curator will review before "
                "any vetted pack is updated. Track at /submissions."
            ),
        )

    @application.post(
        "/api/hub/client/submission/retract",
        response_model=RetractReceipt,
        status_code=status.HTTP_200_OK,
        tags=["client"],
    )
    async def retract_submission(request: Request, body: RetractRequestIn) -> RetractReceipt:
        """Retract an unvetted submission.

        Only succeeds while the submission is still ``proposed`` or
        ``needs_review``. Once a curator has approved or rejected it, the
        record is immutable. Wheel-side clients call this when the
        operator clicks "Cancel my submission" before a curator has
        reviewed.
        """
        state = _state(request)

        def _mutate(record: dict[str, object]) -> dict[str, object]:
            current_status = record.get("status")
            if current_status not in {"proposed", "needs_review"}:
                # Marker so the route can detect "found but not retractable".
                record["__retract_blocked__"] = current_status
                return record
            record["status"] = "retracted"
            record["retracted_at"] = datetime.now(UTC).isoformat()
            if body.deployment_id:
                record["retracted_by"] = body.deployment_id
            if body.reason:
                record["retracted_reason"] = body.reason
            return record

        updated = state.store.update_by_id("updates.jsonl", body.submission_id, _mutate)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No submission with id '{body.submission_id}' was found.",
            )
        if "__retract_blocked__" in updated:
            blocked_status = updated.pop("__retract_blocked__")
            # Re-rewrite the file without the marker so storage stays clean.
            state.store.update_by_id("updates.jsonl", body.submission_id, lambda rec: rec)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Submission '{body.submission_id}' is in status '{blocked_status}' "
                    "and can no longer be retracted by the client."
                ),
            )
        return RetractReceipt(
            id=body.submission_id,
            retracted=True,
            new_status="retracted",
            message="Submission retracted. It will not be reviewed or published.",
        )

    # --- Local knowledge base (operator-side ingest) ---------------------

    _kb = local_kb.LocalKB()

    @application.post("/api/local-kb/ingest", tags=["local-kb"])
    async def ingest_text(body: IngestTextIn) -> dict[str, object]:
        """Ingest one file's content into the operator's local KB."""
        result = _kb.ingest(
            text=body.text,
            source_filename=body.source_filename,
            corridor=body.corridor,
            sector=body.sector,
        )
        return result

    @application.get("/api/local-kb/cases", tags=["local-kb"])
    async def list_local_cases(
        corridor: str | None = None,
        sector: str | None = None,
        status_: str | None = None,
        limit: int = 200,
    ) -> dict[str, object]:
        cases = _kb.list_cases(
            corridor=corridor, sector=sector, status=status_, limit=limit  # type: ignore[arg-type]
        )
        return {"count": len(cases), "cases": cases}

    @application.get("/api/local-kb/cases/{case_id}", tags=["local-kb"])
    async def get_local_case(case_id: str) -> dict[str, object]:
        case = _kb.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"No case '{case_id}' found.")
        return case

    @application.get("/api/local-kb/graph", tags=["local-kb"])
    async def get_local_graph() -> dict[str, object]:
        return _kb.graph()

    @application.get("/api/local-kb/stats", tags=["local-kb"])
    async def get_local_stats() -> dict[str, object]:
        return _kb.stats()

    @application.post("/api/local-kb/forget", tags=["local-kb"])
    async def forget_local_kb() -> dict[str, object]:
        return _kb.forget_everything()

    @application.get("/api/admin/logs", tags=["admin"])
    async def admin_logs(request: Request, limit: int = 50) -> dict[str, object]:
        """Return token-gated, PII-redacted troubleshooting logs."""
        _require_admin_access(request)
        state = _state(request)
        state.store.ensure_ready()
        signals = state.store.read_all("signals.jsonl")
        updates = state.store.read_all("updates.jsonl")
        signal_count, update_count = state.store.counts()
        return {
            "service": "duecare-ai-hub",
            "version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "privacy_note": (
                "Admin output is redacted for detector-class PII. Free-form payloads are suppressed; "
                "audit rows expose hashes, status, automation verdicts, and public-source metadata only."
            ),
            "storage": {
                "root": str(state.store.root),
                "signals": _admin_file_info(state.store.signals_path),
                "updates": _admin_file_info(state.store.updates_path),
                "healthcheck": _admin_file_info(state.store.health_path),
            },
            "counts": {
                "signals": signal_count,
                "updates": update_count,
                "local_kb_cases": _kb.stats().get("n_cases", 0),
            },
            "counters": dict(state.store.trends()),
            "signals": [_safe_admin_record(record) for record in _tail(signals, limit)],
            "updates": [_safe_admin_record(record) for record in _tail(updates, limit)],
            "local_kb": _safe_admin_value("local_kb", _kb.stats()),
        }

    @application.get("/openclaw", include_in_schema=False)
    async def openclaw_redirect() -> Response:
        # Legacy URL kept for any external link that still points to /openclaw.
        return Response(status_code=307, headers={"location": "/server-automation"})

    @application.post("/api/hub/openclaw/inbound-email", include_in_schema=False)
    async def openclaw_inbound_redirect() -> Response:
        # Legacy API path; new clients should call /api/hub/automation/inbound-email.
        return Response(status_code=308, headers={"location": "/api/hub/automation/inbound-email"})

    @application.get("/robots.txt", response_class=Response, tags=["ui"])
    async def robots_txt() -> Response:
        return Response(content=_robots_txt(), media_type="text/plain; charset=utf-8")

    @application.get("/sitemap.xml", response_class=Response, tags=["ui"])
    async def sitemap_xml() -> Response:
        return Response(content=_sitemap_xml(), media_type="application/xml; charset=utf-8")

    
    # Curator admin UI (Phase 13c) — token-gated wrapper for the
    # existing /api/curator/queue + /api/curator/decide/{...} endpoints.
    @application.get("/curator", response_class=HTMLResponse, tags=["curator"])
    def curator_admin_page(request: Request, token: str | None = None):
        _require_admin_access(request)
        return templates.TemplateResponse(request, "curator.html", {
            "token": token or "",
        })

    # Sentinel: server-side scheduled queries (Phase 12)
    from . import sentinel as _sentinel

    @application.get("/sentinel", response_class=HTMLResponse, tags=["sentinel"])
    def sentinel_admin_page(request: Request, token: str | None = None):
        _require_admin_access(request)
        summary = _sentinel.status_summary()
        return templates.TemplateResponse(request, "sentinel.html", {
            "token": token or "",
            "queries": summary["queries"],
            "searxng_configured": summary["searxng_configured"],
            "ollama_configured": summary["ollama_configured"],
        })

    @application.get("/api/sentinel/status", tags=["sentinel"])
    def sentinel_status():
        return _sentinel.status_summary()

    @application.get("/api/sentinel/queries", tags=["sentinel"])
    def sentinel_queries():
        return {"queries": _sentinel.list_queries()}

    @application.post("/api/sentinel/trigger/{slug}", tags=["sentinel"])
    def sentinel_trigger(slug: str, request: Request):
        _require_admin_access(request)
        return _sentinel.run_query(slug)

    @application.post("/api/sentinel/run-due", tags=["sentinel"])
    def sentinel_run_due(request: Request):
        _require_admin_access(request)
        return _sentinel.run_due()

    @application.get("/api/sentinel/drafts", tags=["sentinel"])
    def sentinel_drafts(request: Request, limit: int = 50):
        _require_admin_access(request)
        return _sentinel.recent_drafts(limit=limit)

    return application


def _robots_txt() -> str:
    return """User-agent: *
Disallow: /admin
Allow: /

Sitemap: https://duecare-ai.com/sitemap.xml
"""


def _sitemap_xml() -> str:
    today = datetime.now(UTC).date().isoformat()
    urls = [f"https://duecare-ai.com{path}" if path != "/" else "https://duecare-ai.com/" for path in PAGE_ROUTES]
    urls.extend(
        [
            "https://duecare-ai.com/api-docs",
            "https://duecare-ai.com/api/hub/knowledge-packs",
        ]
    )
    entries = "\n".join(
        f"""  <url>
    <loc>{url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>{'1.0' if url.endswith('//') or url.rstrip('/') == 'https://duecare-ai.com' else '0.7'}</priority>
  </url>"""
        for url in urls
    )
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
{entries}
</urlset>
"""


app = create_app()
