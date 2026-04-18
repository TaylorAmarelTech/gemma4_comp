"""Pydantic request/response models for the DueCare demo API.

These models define the wire format for the /api/v1/* endpoints.
They reference duecare.core schemas where appropriate but stay
self-contained for the API surface so the demo can run without
a full duecare-llm install.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums (mirroring duecare.core.enums for standalone use)
# ---------------------------------------------------------------------------

class Grade(StrEnum):
    """Five-point rubric grade scale."""

    WORST = "worst"
    BAD = "bad"
    NEUTRAL = "neutral"
    GOOD = "good"
    BEST = "best"

    @property
    def ordinal(self) -> int:
        return {"worst": 0, "bad": 1, "neutral": 2, "good": 3, "best": 4}[self.value]

    @classmethod
    def from_score(cls, score: float) -> Grade:
        """Map a 0..1 score into a grade bucket."""
        if score < 0.15:
            return cls.WORST
        if score < 0.40:
            return cls.BAD
        if score < 0.70:
            return cls.NEUTRAL
        if score < 0.90:
            return cls.GOOD
        return cls.BEST


class Action(StrEnum):
    """Recommended platform action based on grade."""

    PASS = "pass"
    WARN = "warn"
    REVIEW = "review"
    BLOCK = "block"


class ContextType(StrEnum):
    """Content context types for analysis."""

    JOB_POSTING = "job_posting"
    CHAT = "chat"
    SEARCH = "search"
    COMMENT = "comment"
    CONTRACT = "contract"
    DOCUMENT = "document"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """POST /api/v1/analyze request body."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="Text to analyze for exploitation indicators.",
    )
    context: ContextType = Field(
        default=ContextType.OTHER,
        description="Content context: job_posting, chat, search, comment, contract, document, other.",
    )
    language: str = Field(
        default="en",
        min_length=2,
        max_length=10,
        description="ISO 639-1 language code (e.g. 'en', 'tl', 'bn').",
    )
    jurisdiction: str = Field(
        default="",
        description=(
            "Origin-destination corridor or single jurisdiction code. "
            "Examples: 'PH_HK', 'BD_SA', 'NP_MY', 'PH', 'HK'."
        ),
    )
    rubric_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Specific rubric IDs to score against. Empty = all available rubrics."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": (
                        "I need to pay $3000 to the agency before I can "
                        "start working as a domestic helper in Hong Kong."
                    ),
                    "context": "chat",
                    "language": "en",
                    "jurisdiction": "PH_HK",
                }
            ]
        },
    }


class BatchAnalyzeRequest(BaseModel):
    """POST /api/v1/batch request body."""

    items: list[AnalyzeRequest] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="List of texts to analyze (max 500 per batch).",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [
                        {
                            "text": "Pay $3000 placement fee before deployment.",
                            "context": "job_posting",
                            "jurisdiction": "PH_HK",
                        },
                        {
                            "text": "Free recruitment, employer pays all costs.",
                            "context": "job_posting",
                            "jurisdiction": "PH_HK",
                        },
                    ]
                }
            ]
        },
    }


class MigrationCaseDocument(BaseModel):
    """One document bundled into a migration-case intake payload."""

    document_id: str = Field(
        default="",
        description="Optional stable identifier for the document within the case.",
    )
    title: str = Field(
        default="",
        description="Short operator-facing label such as 'contract' or 'receipt'.",
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=100_000,
        description="OCR text or manually transcribed document content.",
    )
    context: str = Field(
        default="document",
        description=(
            "Document type hint: contract, receipt, chat, job_posting, certificate, "
            "identity_document, narrative, medical_record, debt_note, agency_record, "
            "government_letter, legal_intake, document."
        ),
    )
    captured_at: str = Field(
        default="",
        description="Optional event date for the document, if already known.",
    )


class MigrationCaseRequest(BaseModel):
    """POST /api/v1/migration-case request body."""

    case_id: str = Field(
        default="",
        description="Optional external case or intake identifier.",
    )
    corridor: str = Field(
        default="",
        description="Optional corridor code such as PH_HK or BD_SA.",
    )
    documents: list[MigrationCaseDocument] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Ordered bundle of recruitment documents for one migration case.",
    )
    include_complaint_templates: bool = Field(
        default=True,
        description="Whether to draft complaint, intake, and written-question template text in the response.",
    )
    top_k_context: int = Field(
        default=5,
        ge=1,
        le=10,
        description="How many RAG context entries to retrieve for legal grounding.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "case_id": "case-demo-001",
                    "corridor": "PH_HK",
                    "documents": [
                        {
                            "document_id": "doc-01",
                            "title": "Agency receipt",
                            "context": "receipt",
                            "captured_at": "2026-01-05",
                            "text": "Receipt for placement fee: HKD 20000 paid by worker before deployment.",
                        },
                        {
                            "document_id": "doc-02",
                            "title": "Employment contract",
                            "context": "contract",
                            "captured_at": "2026-01-12",
                            "text": "Employer will retain passport during contract period and deduct fees over 7 months.",
                        },
                    ],
                }
            ]
        },
    }


# ---------------------------------------------------------------------------
# Response sub-models
# ---------------------------------------------------------------------------

class Resource(BaseModel):
    """A help resource (hotline, NGO, government office)."""

    name: str = Field(..., description="Resource name.")
    type: str = Field(
        default="hotline",
        description="Resource type: hotline, website, office, ngo, legal_aid.",
    )
    number: str | None = Field(default=None, description="Phone number if applicable.")
    url: str | None = Field(default=None, description="URL if applicable.")
    jurisdiction: str = Field(
        default="",
        description="Jurisdiction this resource serves (e.g. 'PH', 'HK', 'intl').",
    )


class CriterionResult(BaseModel):
    """Result of evaluating a single rubric criterion."""

    criterion_id: str
    description: str
    result: str = Field(description="'pass', 'fail', or 'partial'.")
    weight: float
    required: bool
    matched_indicators: list[str] = Field(default_factory=list)
    category: str = ""


class RubricResult(BaseModel):
    """Scores from a single rubric applied to the text."""

    rubric_name: str
    rubric_category: str
    score: float = Field(ge=0.0, le=1.0)
    grade: Grade
    criteria_results: list[CriterionResult] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    """POST /api/v1/analyze response body.

    This is the primary output format shown in the video demo.
    """

    # Aggregate scoring
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Aggregate score on [0, 1]. Lower = more exploitative.",
    )
    grade: Grade = Field(description="Discrete grade: worst / bad / neutral / good / best.")
    action: Action = Field(description="Recommended platform action: pass / warn / review / block.")

    # Indicators
    indicators: list[str] = Field(
        default_factory=list,
        description="Detected exploitation indicators (e.g. 'illegal_recruitment_fee').",
    )

    # Legal references
    legal_refs: list[str] = Field(
        default_factory=list,
        description="Applicable laws and conventions (e.g. 'RA 8042 S6', 'ILO C181 Art. 7').",
    )

    # Human-facing output
    warning_text: str = Field(
        default="",
        description="Localized warning message for display to users.",
    )

    # Resources
    resources: list[Resource] = Field(
        default_factory=list,
        description="Relevant help resources (hotlines, NGOs, government offices).",
    )

    # Per-rubric detail
    rubric_results: list[RubricResult] = Field(
        default_factory=list,
        description="Detailed results per evaluation rubric.",
    )

    # Metadata
    analyzed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of analysis.",
    )
    model_id: str = Field(
        default="duecare-rubric-scorer-v1",
        description="Model/scorer that produced this result.",
    )
    language: str = "en"
    jurisdiction: str = ""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "score": 0.12,
                    "grade": "worst",
                    "action": "block",
                    "indicators": [
                        "illegal_recruitment_fee",
                        "debt_bondage_risk",
                    ],
                    "legal_refs": [
                        "RA 8042 S6",
                        "ILO C181 Art. 7",
                    ],
                    "warning_text": (
                        "This fee may be illegal. Under Philippine law "
                        "(RA 8042), recruitment agencies cannot charge "
                        "domestic workers any placement fees."
                    ),
                    "resources": [
                        {"name": "POEA Hotline", "type": "hotline", "number": "1343", "jurisdiction": "PH"},
                        {"name": "IOM Migration Health", "type": "website", "url": "https://www.iom.int", "jurisdiction": "intl"},
                    ],
                    "rubric_results": [],
                    "analyzed_at": "2026-04-11T12:00:00Z",
                    "model_id": "duecare-rubric-scorer-v1",
                }
            ]
        },
    }


class BatchSummary(BaseModel):
    """Aggregate statistics for a batch analysis."""

    total: int = 0
    grade_distribution: dict[str, int] = Field(default_factory=dict)
    action_distribution: dict[str, int] = Field(default_factory=dict)
    mean_score: float = 0.0
    flagged_count: int = Field(
        default=0,
        description="Number of items scoring below neutral (warn/review/block).",
    )


class BatchAnalyzeResponse(BaseModel):
    """POST /api/v1/batch response body."""

    results: list[AnalyzeResponse] = Field(
        default_factory=list,
        description="Per-item analysis results in the same order as the request.",
    )
    summary: BatchSummary = Field(
        description="Aggregate statistics across the batch.",
    )
    batch_id: str = Field(
        default="",
        description="Unique batch identifier for tracking.",
    )


class CaseDocumentFinding(BaseModel):
    """Structured analysis for one migration-case document."""

    document_id: str
    title: str = ""
    context: str = "document"
    document_type: str = "recruitment_document"
    risk_level: str = "LOW"
    findings: list[str] = Field(default_factory=list)
    legal_refs: list[str] = Field(default_factory=list)
    indicator_flags: list[str] = Field(default_factory=list)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    timeline_markers: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class TimelineEvent(BaseModel):
    """One normalized event in a migration-case timeline."""

    date: str
    label: str
    document_id: str
    description: str


class ComplaintDraft(BaseModel):
    """Generated complaint, intake, or interrogatory-prep text derived from a case bundle."""

    name: str
    audience: str
    text: str


class CaseExampleSummary(BaseModel):
    """Metadata for a built-in case bundle example."""

    id: str
    title: str
    summary: str = ""
    corridor: str = ""
    document_count: int = 0
    case_categories: list[str] = Field(default_factory=list)


class MigrationCaseResponse(BaseModel):
    """POST /api/v1/migration-case response body."""

    case_id: str
    corridor: str = ""
    document_count: int = 0
    risk_level: str = "LOW"
    case_categories: list[str] = Field(default_factory=list)
    risk_reasons: list[str] = Field(default_factory=list)
    detected_indicators: list[str] = Field(default_factory=list)
    indicator_counts: dict[str, int] = Field(default_factory=dict)
    document_type_counts: dict[str, int] = Field(default_factory=dict)
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    extracted_entities: dict[str, list[str]] = Field(default_factory=dict)
    applicable_laws: list[str] = Field(default_factory=list)
    retrieved_context: str = ""
    executive_summary: str = ""
    narrative: str = ""
    timeline: list[TimelineEvent] = Field(default_factory=list)
    document_analyses: list[CaseDocumentFinding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    hotlines: list[Resource] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    complaint_templates: list[ComplaintDraft] = Field(default_factory=list)
    intake_warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Domain / rubric listing models
# ---------------------------------------------------------------------------

class DomainInfo(BaseModel):
    """GET /api/v1/domains item."""

    id: str
    display_name: str
    version: str
    description: str = ""
    n_rubrics: int = 0
    categories: list[str] = Field(default_factory=list)


class RubricInfo(BaseModel):
    """GET /api/v1/rubrics item."""

    name: str
    version: str
    category: str
    n_criteria: int = 0
    total_weight: float = 0.0
    description: str = ""


class StatsResponse(BaseModel):
    """GET /api/v1/stats response."""

    total_analyses: int = 0
    analyses_today: int = 0
    grade_distribution: dict[str, int] = Field(default_factory=dict)
    action_distribution: dict[str, int] = Field(default_factory=dict)
    mean_score: float = 0.0
    top_indicators: list[dict[str, Any]] = Field(default_factory=list)
    rubrics_loaded: int = 0
    uptime_seconds: float = 0.0


class HealthResponse(BaseModel):
    """GET /api/v1/health response."""

    status: str = "ok"
    version: str = "0.1.0"
    rubrics_loaded: int = 0
    model_id: str = "duecare-rubric-scorer-v1"
    uptime_seconds: float = 0.0
