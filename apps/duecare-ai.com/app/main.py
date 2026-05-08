"""Public Duecare AI hub for anonymized safety coordination.

The service is intentionally CPU-only. It does not load Gemma 4. It provides
anonymized signal intake, public-source update proposals, knowledge-pack
metadata, and aggregate trend counters for the public duecare-ai.com website.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from . import __version__
from .site_content import components_html, context_html, grep_rules_html, home_html, tools_html, use_cases_html

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
_PASSPORT_RE = re.compile(
    r"\b(?:passport|visa|national\s+id|id\s+number)[:#\s-]*[A-Z0-9-]{5,}\b",
    re.IGNORECASE,
)
_ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9.'-]+\s+"
    r"(?:street|st\.?|road|rd\.?|avenue|ave\.?|lane|ln\.?|drive|dr\.?)\b",
    re.IGNORECASE,
)


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


class AggregateTrend(BaseModel):
    """Simple anonymized aggregate trend for the hub dashboard."""

    key: str
    count: int


class AppState(BaseModel):
    """Typed app state attached to FastAPI."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    started_at: datetime
    store: FileHubStore


def detect_pii(text: str) -> set[str]:
    """Return PII detector labels found in text."""
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
            "Public coordination hub for anonymized migrant-worker safety signals, signed knowledge packs, "
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
    application.state.duecare = AppState(started_at=datetime.now(UTC), store=store)

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
        state.store.append("updates.jsonl", proposal.model_dump(mode="json"))
        return UpdateReceipt(
            id=proposal.id,
            accepted=True,
            status=proposal.status,
            message="Accepted as a proposed update. A curator must approve before any pack changes.",
        )

    @application.get("/api/hub/opencrawl/updates", response_model=list[UpdateProposalRecord], tags=["updates"])
    async def list_opencrawl_updates(request: Request) -> list[UpdateProposalRecord]:
        state = _state(request)
        return [UpdateProposalRecord.model_validate(record) for record in state.store.read_all("updates.jsonl")]

    @application.get("/", response_class=HTMLResponse, tags=["ui"])
    async def index() -> str:
        return home_html()

    @application.get("/dashboard", response_class=HTMLResponse, tags=["ui"])
    async def dashboard() -> str:
        return _index_html()

    @application.get("/components", response_class=HTMLResponse, tags=["ui"])
    async def components_page() -> str:
        return components_html()

    @application.get("/grep-rules", response_class=HTMLResponse, tags=["ui"])
    async def grep_rules_page() -> str:
        return grep_rules_html()

    @application.get("/tools", response_class=HTMLResponse, tags=["ui"])
    async def tools_page() -> str:
        return tools_html()

    @application.get("/context", response_class=HTMLResponse, tags=["ui"])
    async def context_page() -> str:
        return context_html()

    @application.get("/use-cases", response_class=HTMLResponse, tags=["ui"])
    async def use_cases_page() -> str:
        return use_cases_html()

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
    urls = [
        "https://duecare-ai.com/",
        "https://duecare-ai.com/components",
        "https://duecare-ai.com/use-cases",
        "https://duecare-ai.com/grep-rules",
        "https://duecare-ai.com/tools",
        "https://duecare-ai.com/context",
        "https://duecare-ai.com/dashboard",
        "https://duecare-ai.com/docs",
        "https://duecare-ai.com/redoc",
        "https://duecare-ai.com/api/hub/knowledge-packs",
    ]
    entries = "\n".join(
        f"""  <url>
    <loc>{url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>{'1.0' if url.endswith('/') else '0.7'}</priority>
  </url>"""
        for url in urls
    )
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
{entries}
</urlset>
"""


def _index_html() -> str:
    now = int(time.time())
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Duecare AI — Migrant-worker safety hub</title>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #111827;
      --panel-2: #172033;
      --muted: #94a3b8;
      --text: #f8fafc;
      --blue: #3b82f6;
      --green: #10b981;
      --amber: #f59e0b;
      --red: #ef4444;
      --line: rgba(148, 163, 184, 0.25);
      --soft: rgba(59,130,246,.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: radial-gradient(circle at top left, rgba(59,130,246,.24), transparent 30%), var(--bg); color: var(--text); }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 42px 20px 72px; }}
    .hero {{ border: 1px solid var(--line); background: linear-gradient(135deg, rgba(59,130,246,.22), rgba(16,185,129,.13)); border-radius: 28px; padding: 32px; box-shadow: 0 24px 80px rgba(0,0,0,.24); }}
    h1 {{ font-size: clamp(2.3rem, 5vw, 4.6rem); line-height: .95; margin: 0 0 16px; letter-spacing: -.06em; }}
    h2 {{ margin: 38px 0 14px; font-size: 1.55rem; }}
    h3 {{ margin: 0 0 10px; }}
    p {{ color: #cbd5e1; line-height: 1.65; }}
    label {{ display:block; color:#dbeafe; font-size:13px; font-weight:700; margin: 12px 0 6px; }}
    input, select, textarea {{ width:100%; border:1px solid var(--line); border-radius:12px; padding:11px 12px; color:var(--text); background:#0b1220; font:inherit; }}
    textarea {{ min-height: 110px; resize: vertical; }}
    button {{ border: 0; border-radius: 999px; background: linear-gradient(135deg, var(--blue), var(--green)); color:white; padding: 11px 16px; font-weight: 800; cursor:pointer; margin-top: 12px; }}
    button.secondary {{ background: rgba(148,163,184,.16); color:#dbeafe; border:1px solid var(--line); }}
    code {{ color: #bfdbfe; }}
    a {{ color: #93c5fd; }}
    .row {{ display:flex; gap: 10px; flex-wrap: wrap; align-items:center; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; margin-top: 18px; }}
    .two {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
    .card {{ border: 1px solid var(--line); background: rgba(17,24,39,.82); border-radius: 20px; padding: 18px; }}
    .stat {{ font-size: 2rem; font-weight: 900; line-height: 1; }}
    .tag {{ display: inline-block; padding: 5px 10px; border-radius: 999px; background: rgba(59,130,246,.18); color: #bfdbfe; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; }}
    .ok {{ color: var(--green); font-weight: 900; }}
    .warn {{ color: var(--amber); font-weight: 900; }}
    .danger {{ color: #fca5a5; font-weight: 900; }}
    .muted {{ color: var(--muted); }}
    .output {{ white-space: pre-wrap; border:1px solid var(--line); background:#0b1220; border-radius:12px; padding:12px; min-height: 56px; color:#dbeafe; overflow-wrap:anywhere; }}
    .footer {{ color: var(--muted); margin-top: 34px; font-size: 13px; }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <span class="tag">Duecare AI public hub</span>
    <h1>Centralized knowledge. Decentralized privacy.</h1>
    <p>
      Duecare AI is a coordination hub for anonymized migrant-worker safety signals, signed knowledge packs,
      OpenClaw/OpenCrawl-style public-source updates, prompt/evaluation manifests, and NGO/government deployment pathways.
    </p>
    <p><strong>Privacy is non-negotiable.</strong> This hub accepts aggregate or anonymized signals only. Raw case details stay local with the worker, NGO, regulator, or platform unless explicitly consented and redacted.</p>
    <div class="row">
      <a href="/docs">OpenAPI docs</a>
      <a href="/api/hub/status">Status JSON</a>
      <a href="/api/hub/knowledge-packs">Knowledge packs</a>
    </div>
  </section>

  <h2>Live status</h2>
  <div class="grid">
    <div class="card"><span class="tag">Signals</span><p class="stat" id="signalCount">—</p><p>Anonymized pattern signals accepted.</p></div>
    <div class="card"><span class="tag">Updates</span><p class="stat" id="updateCount">—</p><p>Public-source updates pending curator review.</p></div>
    <div class="card"><span class="tag">Privacy mode</span><p class="stat" style="font-size:1.15rem" id="privacyMode">—</p><p>No raw case intake. PII checks run before storage.</p></div>
    <div class="card"><span class="tag">Runtime</span><p class="stat" id="uptime">—</p><p>CPU-only hub. Gemma 4 runs elsewhere.</p></div>
  </div>

  <h2>What this proves</h2>
  <div class="grid">
    <div class="card"><span class="tag">Exchange</span><p>Partners can contribute anonymized patterns, contacts, RAG documents, prompts, and evaluation results without uploading raw cases.</p></div>
    <div class="card"><span class="tag">Sentinel</span><p>OpenClaw/OpenCrawl-style crawlers can propose law, contact, and complaint-channel updates for human curator review.</p></div>
    <div class="card"><span class="tag">Trainer</span><p>Approved signals and evaluation failures become candidates for Gemma 4 adaptation through a separate PII-gated training pipeline.</p></div>
    <div class="card"><span class="tag">Channels</span><p>NGO/government Messenger, WhatsApp, SMS, and web-chat bots can pull verified knowledge packs and draft complaint handoffs.</p></div>
  </div>

  <h2>Try the privacy-preserving flow</h2>
  <div class="two">
    <form class="card" id="signalForm">
      <h3>Submit synthetic anonymized signal</h3>
      <p class="muted">This simulates an NGO/platform sending an aggregate pattern. Do not enter names, phone numbers, emails, addresses, or case IDs.</p>
      <label>Source</label>
      <select name="source"><option>synthetic_demo</option><option>ngo_case_intake</option><option>government_regulator</option><option>platform_moderation</option><option>research_evaluation</option><option>worker_mobile_opt_in</option></select>
      <label>Jurisdiction</label>
      <input name="jurisdiction" value="Philippines / Hong Kong" />
      <label>Corridor</label>
      <input name="corridor" value="PH-HK domestic work" />
      <label>Risk tags, comma-separated</label>
      <input name="risk_tags" value="recruitment_fee, document_retention, coercive_contract" />
      <label>Pattern summary</label>
      <textarea name="summary">Synthetic aggregate pattern: multiple domestic-work recruitment ads describe high placement fees, unclear deductions, and document-handling pressure. No person-specific facts are included.</textarea>
      <button type="submit">Submit anonymized signal</button>
      <pre class="output" id="signalOutput">Waiting…</pre>
    </form>

    <form class="card" id="updateForm">
      <h3>Submit OpenCrawl update proposal</h3>
      <p class="muted">This simulates a public-source crawler proposing a knowledge-pack update. A curator must approve before any pack changes.</p>
      <label>Source name</label>
      <input name="source_name" value="Synthetic public regulator page" />
      <label>Source URL</label>
      <input name="source_url" value="https://example.org/public-advisory" />
      <label>Pack kind</label>
      <select name="proposed_pack_kind"><option>contacts</option><option>rag_docs</option><option>grep_rules</option><option>rubrics</option><option>examples</option><option>tools</option><option>jurisdictions</option></select>
      <label>Jurisdiction</label>
      <input name="jurisdiction" value="Hong Kong" />
      <label>Change summary</label>
      <textarea name="change_summary">Synthetic public-source update: a regulator advisory page appears to clarify complaint-routing language for migrant domestic workers. Curator review is required before release.</textarea>
      <button type="submit">Submit update proposal</button>
      <pre class="output" id="updateOutput">Waiting…</pre>
    </form>
  </div>

  <h2>Aggregate trends</h2>
  <div class="card">
    <button class="secondary" onclick="refreshAll()">Refresh dashboard</button>
    <pre class="output" id="trendOutput">Loading…</pre>
  </div>

  <h2>Live API surface</h2>
  <div class="card">
    <p><span class="ok">GET</span> <code>/api/health</code> — Render health check with file-store verification</p>
    <p><span class="ok">GET</span> <code>/api/hub/status</code> — service health, counters, and privacy mode</p>
    <p><span class="ok">GET</span> <code>/api/hub/knowledge-packs</code> — discoverable Duecare pack metadata</p>
    <p><span class="warn">POST</span> <code>/api/hub/signals</code> — submit anonymized pattern signals only</p>
    <p><span class="warn">POST</span> <code>/api/hub/opencrawl/updates</code> — submit public-source update proposals</p>
    <p><span class="ok">GET</span> <code>/docs</code> — OpenAPI documentation</p>
  </div>

  <p class="footer">Build timestamp marker: {now}. Duecare drafts; the user or trusted caseworker decides.</p>
</main>
<script>
  const toJson = async (response) => {{
    const text = await response.text();
    try {{ return JSON.stringify(JSON.parse(text), null, 2); }} catch {{ return text; }}
  }};
  const splitList = (value) => value.split(',').map((item) => item.trim()).filter(Boolean);
  async function refreshAll() {{
    const status = await fetch('/api/hub/status').then((r) => r.json());
    document.getElementById('signalCount').textContent = status.signal_count;
    document.getElementById('updateCount').textContent = status.update_proposal_count;
    document.getElementById('privacyMode').textContent = status.privacy_mode.replaceAll('_', ' ');
    document.getElementById('uptime').textContent = Math.max(1, Math.round(status.uptime_seconds / 60)) + ' min';
    const trends = await fetch('/api/hub/trends').then((r) => r.json());
    document.getElementById('trendOutput').textContent = trends.length ? JSON.stringify(trends, null, 2) : 'No aggregate trends yet. Submit a synthetic signal above.';
  }}
  document.getElementById('signalForm').addEventListener('submit', async (event) => {{
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = {{
      source: form.get('source'),
      jurisdiction: form.get('jurisdiction'),
      corridor: form.get('corridor'),
      language: 'English',
      risk_tags: splitList(form.get('risk_tags')),
      summary: form.get('summary'),
      evidence_hashes: ['sha256:synthetic-demo-pattern-001'],
      consent_basis: 'synthetic_demo',
      pack_version: '0.14.x'
    }};
    const response = await fetch('/api/hub/signals', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(body) }});
    document.getElementById('signalOutput').textContent = await toJson(response);
    await refreshAll();
  }});
  document.getElementById('updateForm').addEventListener('submit', async (event) => {{
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = {{
      source_name: form.get('source_name'),
      source_url: form.get('source_url'),
      proposed_pack_kind: form.get('proposed_pack_kind'),
      jurisdiction: form.get('jurisdiction'),
      change_summary: form.get('change_summary'),
      extracted_public_facts: ['Synthetic public-source update; curator review required.'],
      content_hash: 'synthetic-public-hash-001',
      crawler_version: 'opencrawl-demo/0.1'
    }};
    const response = await fetch('/api/hub/opencrawl/updates', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(body) }});
    document.getElementById('updateOutput').textContent = await toJson(response);
    await refreshAll();
  }});
  refreshAll();
</script>
</body>
</html>
"""


app = create_app()
