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
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from . import __version__
from . import openclaw
from .pii import detect_pii

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

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

# Every clean URL on the public site maps to a template file in app/templates/.
# The slug ("/" or "/foo") is the route; the value is the template filename.
# Add a row here when a new design page lands and it will route automatically.
PAGE_ROUTES: dict[str, str] = {
    "/": "index.html",
    "/alerts": "alerts.html",
    "/client-connect": "client-connect.html",
    "/components": "components.html",
    "/contact": "contact.html",
    "/context": "context.html",
    "/contribute": "contribute.html",
    "/dashboard": "dashboard.html",
    "/demo": "demo.html",
    "/deployments": "deployments.html",
    "/docs": "docs.html",
    "/email-feedback": "email-feedback.html",
    "/evaluation": "evaluation.html",
    "/grep-rules": "grep-rules.html",
    "/harness": "harness.html",
    "/hub": "hub.html",
    "/intelligence": "intelligence.html",
    "/knowledge-packs": "knowledge-packs.html",
    "/login": "login.html",
    "/mission": "mission.html",
    "/newsletter": "newsletter.html",
    "/openclaw": "openclaw.html",
    "/packages": "packages.html",
    "/packages-detail": "packages-detail.html",
    "/partners": "partners.html",
    "/privacy": "privacy.html",
    "/privacy-boundary": "privacy-boundary.html",
    "/research-monitor": "research-monitor.html",
    "/sentinel": "sentinel.html",
    "/setup": "setup.html",
    "/stats": "stats.html",
    "/submissions": "submissions.html",
    "/submit-information": "submit-information.html",
    "/technical-docs": "technical-docs.html",
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


class HealthStatus(BaseModel):
    """Health status for Render and external smoke checks."""

    status: Literal["ok"]
    service: str
    version: str
    storage: Literal["file"]
    storage_ok: bool
    data_dir: str


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
    openclaw_verdict: str | None = None
    openclaw_intent: str | None = None
    openclaw_model: str | None = None


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


class AggregateTrend(BaseModel):
    """Simple anonymized aggregate trend for the hub dashboard."""

    key: str
    count: int


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
            description="Public ILO, Palermo, corridor, and pattern-brief context for grounded Gemma 4 answers.",
            status="live",
            update_channel="Sentinel proposals then curator review",
        ),
        KnowledgePackSummary(
            id="duecare-grep-rules-v0",
            kind="grep_rules",
            title="Exploitation and jailbreak detection rules",
            version="0.14.x",
            description="Deterministic indicators for fees, document retention, debt pressure, evasion, and jailbreak attempts.",
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


def create_app(*, data_dir: Path | None = None) -> FastAPI:
    """Create the Duecare AI public hub FastAPI application."""
    store = FileHubStore((data_dir or default_data_dir()).resolve())
    store.ensure_ready()
    application = FastAPI(
        title="Duecare AI Hub",
        description=(
            "Public coordination hub for anonymized migrant-worker safety signals, vetted knowledge packs, "
            "public-source update proposals, and evaluation metadata. Privacy is non-negotiable."
        ),
        version=__version__,
        docs_url="/api-docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
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
        )

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
        # OpenClaw's edge filter runs alongside the schema-level PII regex so we
        # never store an update that the LLM evaluator outright rejects.
        findings = detect_pii(body.change_summary)
        if findings:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Update rejected because the summary appears to contain raw PII.",
            )
        verdict = openclaw.evaluate_submission(body.change_summary, kind="context")
        if verdict.verdict == "reject":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"OpenClaw rejected this update: {'; '.join(verdict.reasons) or 'policy violation'}.",
            )
        state = _state(request)
        proposal = UpdateProposalRecord(
            **body.model_dump(),
            id=f"upd_{uuid.uuid4().hex[:12]}",
            status="proposed" if verdict.verdict == "needs_curator_review" else "needs_review",
            received_at=datetime.now(UTC),
        )
        record = proposal.model_dump(mode="json")
        record["openclaw"] = {
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
            openclaw_verdict=verdict.verdict,
            openclaw_intent=verdict.intent,
            openclaw_model=verdict.model,
        )

    @application.get("/api/hub/opencrawl/updates", response_model=list[UpdateProposalRecord], tags=["updates"])
    async def list_opencrawl_updates(request: Request) -> list[UpdateProposalRecord]:
        state = _state(request)
        return [UpdateProposalRecord.model_validate(record) for record in state.store.read_all("updates.jsonl")]

    @application.post(
        "/api/hub/openclaw/inbound-email",
        response_model=InboundEmailReceipt,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["openclaw"],
    )
    async def submit_inbound_email(request: Request, body: InboundEmailIn) -> InboundEmailReceipt:
        """Email-gateway webhook: an expert replied to a solicitation.

        OpenClaw classifies intent + extracts public-source facts from the
        body. The structured record lands in inbound.jsonl for curator
        review; nothing auto-publishes.
        """
        verdict = openclaw.vet_inbound_email(body.subject, body.body, body.sender_domain)
        state = _state(request)
        record_id = f"inb_{uuid.uuid4().hex[:12]}"
        record = {
            "id": record_id,
            "received_at": body.received_at.isoformat(),
            "sender_domain": body.sender_domain,
            "subject": body.subject,
            "body_sha256": _sha256_text(body.body),
            "in_reply_to": body.in_reply_to,
            "openclaw": {
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
        return templates.TemplateResponse(request, template_name, {"version": __version__})

    def _make_route(template_name: str):
        async def _handler(request: Request) -> HTMLResponse:
            return _render(template_name, request)

        return _handler

    for path, template_name in PAGE_ROUTES.items():
        application.add_api_route(
            path,
            _make_route(template_name),
            response_class=HTMLResponse,
            tags=["ui"],
            name=f"page::{template_name}",
            include_in_schema=False,
        )

    @application.get("/robots.txt", response_class=Response, tags=["ui"])
    async def robots_txt() -> Response:
        return Response(content=_robots_txt(), media_type="text/plain; charset=utf-8")

    @application.get("/sitemap.xml", response_class=Response, tags=["ui"])
    async def sitemap_xml() -> Response:
        return Response(content=_sitemap_xml(), media_type="application/xml; charset=utf-8")

    return application


def _robots_txt() -> str:
    return """User-agent: *
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
