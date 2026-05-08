"""Duecare central hub for anonymized updates and knowledge packs.

This service is intentionally lightweight: it is designed for a CPU-only
Render deployment at duecare-ai.com and does not load Gemma 4 directly.
It receives anonymized safety signals, exposes current knowledge-pack
metadata, and accepts OpenClaw/OpenCrawl-style public-source update
proposals for curator review.
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from . import __version__

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
UpdateStatus = Literal["proposed", "needs_review", "approved", "rejected"]

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
_PASSPORT_RE = re.compile(r"\b(?:passport|visa|national\s+id|id\s+number)[:#\s-]*[A-Z0-9-]{5,}\b", re.IGNORECASE)
_ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9.'-]+\s+"
    r"(?:street|st\.?|road|rd\.?|avenue|ave\.?|lane|ln\.?|drive|dr\.?)\b",
    re.IGNORECASE,
)


class HubState(BaseModel):
    """Mutable in-memory state for the public hub prototype."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    anonymized_signals: list["AnonymizedSignalRecord"] = Field(default_factory=list)
    update_proposals: list["UpdateProposalRecord"] = Field(default_factory=list)
    counters: Counter[str] = Field(default_factory=Counter)


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
    """OpenClaw/OpenCrawl-style public-source update proposal."""

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


class AggregateTrend(BaseModel):
    """Simple anonymized aggregate trend for the hub dashboard."""

    key: str
    count: int


def detect_pii(text: str) -> set[str]:
    """Return PII detector labels found in text.

    Args:
        text: Candidate user or partner-supplied text.

    Returns:
        A set of PII labels. Empty means no detector fired.
    """
    findings: set[str] = set()
    if _EMAIL_RE.search(text):
        findings.add("email")
    if _PHONE_RE.search(text):
        findings.add("phone")
    if _PASSPORT_RE.search(text):
        findings.add("identity_document")
    if _ADDRESS_RE.search(text):
        findings.add("street_address")
    return findings


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _state(request: Request) -> HubState:
    state = getattr(request.app.state, "hub", None)
    if state is None:
        state = HubState()
        request.app.state.hub = state
    return state


def _knowledge_packs() -> list[KnowledgePackSummary]:
    return [
        KnowledgePackSummary(
            id="duecare-global-rag-v0",
            kind="rag_docs",
            title="Global migrant-worker protection RAG pack",
            version="0.14.x",
            description="Public ILO, Palermo, corridor, and pattern-brief context for grounded answers.",
            status="live",
            update_channel="Sentinel proposals then curator review",
        ),
        KnowledgePackSummary(
            id="duecare-grep-rules-v0",
            kind="grep_rules",
            title="Exploitation and jailbreak detection rules",
            version="0.14.x",
            description="Deterministic indicators for fees, document retention, debt pressure, and evasion.",
            status="live",
            update_channel="Partner PR or Sentinel proposal",
        ),
        KnowledgePackSummary(
            id="duecare-contacts-v0",
            kind="contacts",
            title="Verified public contacts and complaint channels",
            version="0.14.x",
            description="Regulators, NGOs, consulates, hotlines, and complaint mechanisms. Draft-only use.",
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


def create_app() -> FastAPI:
    """Create the Duecare hub FastAPI application.

    Returns:
        A configured FastAPI application.
    """
    application = FastAPI(
        title="Duecare LLM Hub",
        description=(
            "Central hub for anonymized migrant-worker safety signals, signed knowledge packs, "
            "public-source update proposals, and evaluation metadata. Privacy is non-negotiable."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.state.hub = HubState()

    @application.get("/healthz", tags=["system"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "duecare-hub", "version": __version__}

    @application.get("/api/hub/status", response_model=HubStatus, tags=["hub"])
    async def hub_status(request: Request) -> HubStatus:
        state = _state(request)
        return HubStatus(
            service="duecare-hub",
            version=__version__,
            uptime_seconds=int((datetime.now(UTC) - state.started_at).total_seconds()),
            privacy_mode="anonymized_signals_only_no_raw_pii",
            signal_count=len(state.anonymized_signals),
            update_proposal_count=len(state.update_proposals),
            counters=dict(state.counters),
        )

    @application.get(
        "/api/hub/knowledge-packs",
        response_model=list[KnowledgePackSummary],
        tags=["knowledge-packs"],
    )
    async def list_knowledge_packs() -> list[KnowledgePackSummary]:
        return _knowledge_packs()

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
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
        state.anonymized_signals.append(record)
        state.counters[f"source:{record.source}"] += 1
        state.counters[f"jurisdiction:{record.jurisdiction.lower()}"] += 1
        for tag in record.risk_tags:
            state.counters[f"risk:{tag.lower()}"] += 1
        return SignalReceipt(
            id=record.id,
            accepted=True,
            received_at=now,
            summary_sha256=summary_hash,
            message="Accepted anonymized signal. Raw PII is not stored by this hub prototype.",
        )

    @application.get("/api/hub/trends", response_model=list[AggregateTrend], tags=["signals"])
    async def aggregate_trends(request: Request) -> list[AggregateTrend]:
        state = _state(request)
        return [
            AggregateTrend(key=key, count=value)
            for key, value in sorted(state.counters.items(), key=lambda item: (-item[1], item[0]))
        ]

    @application.post(
        "/api/hub/opencrawl/updates",
        response_model=UpdateReceipt,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["updates"],
    )
    async def submit_opencrawl_update(
        request: Request,
        body: OpenCrawlUpdateIn,
    ) -> UpdateReceipt:
        findings = detect_pii(body.change_summary)
        if findings:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Update rejected because the summary appears to contain raw PII.",
            )
        state = _state(request)
        proposal = UpdateProposalRecord(
            **body.model_dump(),
            id=f"upd_{uuid.uuid4().hex[:12]}",
            status="proposed",
            received_at=datetime.now(UTC),
        )
        state.update_proposals.append(proposal)
        state.counters[f"update_kind:{proposal.proposed_pack_kind}"] += 1
        state.counters[f"update_jurisdiction:{proposal.jurisdiction.lower()}"] += 1
        return UpdateReceipt(
            id=proposal.id,
            accepted=True,
            status=proposal.status,
            message="Accepted as a proposed update. A curator must approve before any pack changes.",
        )

    @application.get("/api/hub/opencrawl/updates", response_model=list[UpdateProposalRecord], tags=["updates"])
    async def list_opencrawl_updates(request: Request) -> list[UpdateProposalRecord]:
        state = _state(request)
        return state.update_proposals

    @application.get("/", response_class=HTMLResponse, tags=["ui"])
    async def index() -> str:
        return _index_html()

    return application


def _index_html() -> str:
    now = int(time.time())
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Duecare LLM Hub</title>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #111827;
      --muted: #94a3b8;
      --text: #f8fafc;
      --blue: #3b82f6;
      --green: #10b981;
      --amber: #f59e0b;
      --red: #ef4444;
      --line: rgba(148, 163, 184, 0.25);
    }}
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 42px 20px 64px; }}
    .hero {{ border: 1px solid var(--line); background: linear-gradient(135deg, rgba(59,130,246,.20), rgba(16,185,129,.12)); border-radius: 24px; padding: 30px; }}
    h1 {{ font-size: clamp(2rem, 5vw, 4rem); line-height: 1; margin: 0 0 14px; }}
    h2 {{ margin-top: 34px; }}
    p {{ color: #cbd5e1; line-height: 1.65; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; margin-top: 18px; }}
    .card {{ border: 1px solid var(--line); background: rgba(17,24,39,.78); border-radius: 18px; padding: 18px; }}
    .tag {{ display: inline-block; padding: 4px 9px; border-radius: 999px; background: rgba(59,130,246,.18); color: #bfdbfe; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }}
    .ok {{ color: var(--green); font-weight: 800; }}
    .warn {{ color: var(--amber); font-weight: 800; }}
    code {{ color: #bfdbfe; }}
    a {{ color: #93c5fd; }}
    .footer {{ color: var(--muted); margin-top: 34px; font-size: 13px; }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <span class="tag">Duecare LLM Hub</span>
    <h1>Centralized knowledge. Decentralized privacy.</h1>
    <p>
      A public coordination hub for anonymized migrant-worker safety signals, signed knowledge packs,
      OpenClaw/OpenCrawl-style public-source updates, prompt/evaluation manifests, and NGO/government deployment pathways.
    </p>
    <p><strong>Privacy is non-negotiable.</strong> This hub accepts aggregate or anonymized signals only. Raw case details stay local with the worker, NGO, regulator, or platform unless explicitly consented and redacted.</p>
  </section>

  <h2>What this proves for judges and partners</h2>
  <div class="grid">
    <div class="card"><span class="tag">Exchange</span><p>Partners can contribute anonymized patterns, contacts, RAG documents, prompts, and evaluation results without uploading raw cases.</p></div>
    <div class="card"><span class="tag">Sentinel</span><p>OpenClaw/OpenCrawl-style crawlers can propose law, contact, and complaint-channel updates for human curator review.</p></div>
    <div class="card"><span class="tag">Trainer</span><p>Approved signals and evaluation failures become candidates for Gemma 4 adaptation through a separate PII-gated training pipeline.</p></div>
    <div class="card"><span class="tag">Channels</span><p>NGO/government Messenger, WhatsApp, SMS, and web-chat bots can pull verified knowledge packs and draft complaint handoffs.</p></div>
  </div>

  <h2>Live API surface</h2>
  <div class="card">
    <p><span class="ok">GET</span> <code>/api/hub/status</code> — service health, counters, and privacy mode</p>
    <p><span class="ok">GET</span> <code>/api/hub/knowledge-packs</code> — discoverable Duecare pack metadata</p>
    <p><span class="warn">POST</span> <code>/api/hub/signals</code> — submit anonymized pattern signals only</p>
    <p><span class="warn">POST</span> <code>/api/hub/opencrawl/updates</code> — submit public-source update proposals</p>
    <p><span class="ok">GET</span> <code>/docs</code> — OpenAPI documentation</p>
  </div>

  <p class="footer">Build timestamp marker: {now}. Duecare drafts; the user or trusted caseworker decides.</p>
</main>
</body>
</html>
"""


app = create_app()
