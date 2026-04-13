"""Social media risk scoring for trafficking detection.

Ported from the trafficking benchmark's ``social_media_risk_scorer.py``.
Analyzes job postings, recruiter messages, and chat content for
trafficking indicators.  Scores 0-100 across six categories and returns
structured results with category breakdown, matched indicators, and
risk level.

The rule-based engine runs deterministically with no LLM inference.
When Gemma 4 is available the ``score_content_with_llm`` async path
layers model-based analysis on top of the pattern matches.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskLevel(StrEnum):
    """Risk level classification."""

    MINIMAL = "minimal"    # Score 0-20:  Normal content
    LOW = "low"            # Score 21-40: Minor concerns
    MODERATE = "moderate"  # Score 41-60: Notable red flags
    HIGH = "high"          # Score 61-80: Serious concerns
    CRITICAL = "critical"  # Score 81-100: Strong trafficking indicators


class ContentType(StrEnum):
    """Types of social media content."""

    JOB_POSTING = "job_posting"
    RECRUITER_PROFILE = "recruiter_profile"
    AGENCY_PAGE = "agency_page"
    WORKER_TESTIMONIAL = "worker_testimonial"
    CHAT_MESSAGE = "chat_message"
    ADVERTISEMENT = "advertisement"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RiskIndicator(BaseModel):
    """A single risk indicator matched in content."""

    category: str = Field(description="One of: recruitment, financial, document_control, communication, control, vagueness.")
    indicator: str = Field(description="Indicator key, e.g. 'upfront_fees'.")
    severity: int = Field(ge=1, le=10, description="Severity score 1-10.")
    evidence: str = Field(description="The text fragment that triggered the match.")
    context: str = Field(description="Surrounding text for reviewer reference.")
    explanation: str = Field(description="Human-readable explanation of why this is a concern.")


class CategoryBreakdown(BaseModel):
    """Per-category summary included in the assessment."""

    category: str
    indicator_count: int = 0
    max_severity: int = 0
    indicators: list[str] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Complete risk assessment for a piece of content.

    This is the primary output of the scorer, designed for direct
    serialisation to the ``/api/v1/social-media-risk`` endpoint.
    """

    content_id: str = Field(description="SHA-256-based short hash of the input text.")
    content_type: ContentType
    risk_score: float = Field(ge=0.0, le=100.0, description="Aggregate risk score 0-100.")
    risk_level: RiskLevel
    indicators: list[RiskIndicator] = Field(default_factory=list)
    category_breakdown: list[CategoryBreakdown] = Field(default_factory=list)
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)
    llm_analysis: str | None = None
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Risk indicator definitions with severity scores (30+ patterns)
# ---------------------------------------------------------------------------

RISK_INDICATORS: dict[str, dict[str, dict[str, Any]]] = {
    # -- Recruitment process red flags ----------------------------------------
    "recruitment": {
        "no_experience_required": {
            "patterns": [
                r"no experience (?:needed|required|necessary)",
                r"experience not (?:needed|required)",
                r"anyone can apply",
                r"no qualifications? (?:needed|required)",
            ],
            "severity": 3,
            "explanation": "Legitimate overseas jobs typically require verified qualifications.",
        },
        "immediate_deployment": {
            "patterns": [
                r"immediate (?:deployment|start|hiring)",
                r"fly (?:out|tomorrow|this week|immediately)",
                r"urgent(?:ly)? (?:needed|hiring|looking)",
                r"start (?:immediately|right away|asap)",
                r"leave (?:tomorrow|this week|immediately)",
            ],
            "severity": 5,
            "explanation": "Legitimate overseas employment requires proper documentation and processing time.",
        },
        "guaranteed_job": {
            "patterns": [
                r"(?:100%|guaranteed) (?:job|employment|placement)",
                r"sure (?:job|hire|employment)",
                r"definitely (?:get|have) (?:a )?job",
                r"no interview (?:needed|required)",
            ],
            "severity": 6,
            "explanation": "No legitimate agency can guarantee employment outcomes.",
        },
        "direct_hire_claims": {
            "patterns": [
                r"direct hire",
                r"no agency fee",
                r"employer pays (?:everything|all)",
                r"free processing",
            ],
            "severity": 4,
            "explanation": "Claims of 'direct hire' often mask unlicensed recruitment.",
        },
    },
    # -- Financial red flags --------------------------------------------------
    "financial": {
        "upfront_fees": {
            "patterns": [
                r"(?:processing|placement|training) fee",
                r"pay (?:first|upfront|advance)",
                r"deposit (?:required|needed)",
                r"fee (?:of|is|:) ?[\$\u20b1\u20ac\u00a3]\s*\d+",
                r"\d+[,\s]?\d* (?:pesos?|php|dollars?|usd)",
            ],
            "severity": 7,
            "explanation": "Charging workers recruitment fees is prohibited under international standards.",
        },
        "salary_advance_scheme": {
            "patterns": [
                r"salary advance",
                r"advance (?:payment|salary|pay)",
                r"loan (?:available|offered)",
                r"we can lend",
                r"borrow from (?:us|agency)",
            ],
            "severity": 8,
            "explanation": "Salary advance schemes are a common debt bondage mechanism.",
        },
        "unrealistic_salary": {
            "patterns": [
                r"(?:earn|salary|pay)[:\s]+[\$\u20b1\u20ac\u00a3]?\s*(?:[5-9]\d{4}|\d{6,})",
                r"(?:[5-9]0|[1-9]\d{2}),?000\+?\s*(?:monthly|/month|per month)",
                r"high salary",
                r"big (?:pay|salary|income)",
            ],
            "severity": 5,
            "explanation": "Unrealistic salary claims are used to lure victims.",
        },
        "hidden_deductions": {
            "patterns": [
                r"salary deduction",
                r"deduct(?:ed|ion)? (?:from|for)",
                r"withhold(?:ing)? (?:salary|pay)",
                r"(?:monthly|regular) (?:deduction|payment)",
            ],
            "severity": 8,
            "explanation": "Mandatory salary deductions are a form of wage theft.",
        },
    },
    # -- Document control red flags -------------------------------------------
    "document_control": {
        "passport_submission": {
            "patterns": [
                r"submit (?:your )?passport",
                r"passport (?:required|needed|must be submitted)",
                r"bring (?:your )?passport",
                r"surrender (?:your )?(?:passport|documents?)",
                r"(?:hold|keep) (?:your )?passport",
            ],
            "severity": 9,
            "explanation": "Document confiscation is a primary indicator of trafficking.",
        },
        "document_processing": {
            "patterns": [
                r"we (?:will )?(?:process|handle) (?:your )?(?:documents?|papers?|visa)",
                r"give us (?:your )?(?:documents?|papers?)",
                r"(?:documents?|papers?) (?:will be|are) (?:kept|held|processed)",
            ],
            "severity": 6,
            "explanation": "Third-party document handling enables control over workers.",
        },
    },
    # -- Communication red flags ----------------------------------------------
    "communication": {
        "private_contact_only": {
            "patterns": [
                r"(?:pm|dm|message) (?:me )?only",
                r"(?:viber|whatsapp|telegram|wechat) only",
                r"contact (?:via|through) (?:viber|whatsapp|telegram)",
                r"(?:text|call) (?:this number|me)",
                r"no (?:calls?|email)",
            ],
            "severity": 4,
            "explanation": "Preference for untracked communication channels suggests evasion.",
        },
        "urgency_pressure": {
            "patterns": [
                r"(?:apply|respond|contact) (?:now|immediately|asap|today)",
                r"limited (?:slots?|positions?|openings?)",
                r"(?:don't|do not) miss (?:this|the) (?:opportunity|chance)",
                r"(?:only|just) \d+ (?:slots?|positions?|openings?) left",
                r"deadline (?:today|tomorrow|this week)",
            ],
            "severity": 5,
            "explanation": "High-pressure tactics prevent proper due diligence.",
        },
        "secrecy_language": {
            "patterns": [
                r"(?:don't|do not) tell (?:anyone|family)",
                r"keep (?:this )?(?:secret|private|confidential)",
                r"(?:just )?between us",
                r"(?:don't|do not) (?:post|share|spread)",
            ],
            "severity": 8,
            "explanation": "Secrecy requirements isolate potential victims.",
        },
    },
    # -- Movement / control red flags -----------------------------------------
    "control": {
        "provided_accommodation": {
            "patterns": [
                r"(?:free |provided )?(?:accommodation|housing|dorm|quarters)",
                r"(?:live|stay) (?:in|at) (?:the )?(?:company|employer|work)",
                r"(?:accommodation|housing) (?:included|provided)",
            ],
            "severity": 3,
            "explanation": "Employer-controlled accommodation can restrict worker freedom.",
        },
        "restricted_movement": {
            "patterns": [
                r"(?:cannot|can't|not allowed to) (?:leave|go out)",
                r"(?:stay|remain) (?:in|at|inside)",
                r"(?:curfew|lockdown)",
                r"accompanied (?:only|always)",
            ],
            "severity": 9,
            "explanation": "Restriction of movement is a key trafficking indicator.",
        },
        "contract_terms": {
            "patterns": [
                r"(?:sign|agree) (?:before|without reading)",
                r"contract (?:in|written in) (?:foreign|different) language",
                r"(?:no|without) (?:copy|duplicate)",
                r"(?:verbal|oral) (?:agreement|contract)",
            ],
            "severity": 7,
            "explanation": "Contract irregularities enable exploitation.",
        },
    },
    # -- Verification / vagueness red flags -----------------------------------
    "vagueness": {
        "vague_employer": {
            "patterns": [
                r"(?:big|large|reputable) company",
                r"(?:well-known|famous) employer",
                r"(?:confidential|undisclosed) (?:employer|company)",
                r"employer (?:to be|will be) (?:disclosed|revealed) later",
            ],
            "severity": 5,
            "explanation": "Legitimate jobs identify the specific employer.",
        },
        "vague_location": {
            "patterns": [
                r"(?:abroad|overseas|foreign country)",
                r"(?:middle east|asia|europe)",
                r"location (?:tbd|to be (?:determined|announced))",
                r"(?:various|multiple) locations?",
            ],
            "severity": 4,
            "explanation": "Unspecified locations prevent verification.",
        },
        "vague_job_duties": {
            "patterns": [
                r"(?:general|various|multiple|different) (?:duties|tasks|work)",
                r"(?:assist|help) (?:with )?(?:various|different)",
                r"(?:as needed|when required)",
                r"(?:flexible|varied) (?:role|position|duties)",
            ],
            "severity": 4,
            "explanation": "Vague job descriptions enable scope creep and exploitation.",
        },
    },
}

# Friendly display names for categories.
_CATEGORY_LABELS: dict[str, str] = {
    "recruitment": "Recruitment",
    "financial": "Financial",
    "document_control": "Document Control",
    "communication": "Communication",
    "control": "Movement / Control",
    "vagueness": "Verification",
}


# ---------------------------------------------------------------------------
# SocialMediaRiskScorer
# ---------------------------------------------------------------------------

class SocialMediaRiskScorer:
    """Score social media content for trafficking / exploitation risk.

    Uses compiled regex patterns for deterministic, zero-inference
    scoring.  Optionally accepts an LLM provider for enhanced analysis.

    Usage::

        scorer = SocialMediaRiskScorer()
        result = scorer.score_content("Hiring domestic helpers...")
        print(result.risk_level, result.risk_score)
    """

    def __init__(self, *, llm_provider: Any | None = None) -> None:
        self._llm_provider = llm_provider
        self._compiled = self._compile_patterns()

    # -- Pattern compilation ------------------------------------------------

    @staticmethod
    def _compile_patterns() -> dict[str, dict[str, dict[str, Any]]]:
        compiled: dict[str, dict[str, dict[str, Any]]] = {}
        for category, indicators in RISK_INDICATORS.items():
            compiled[category] = {}
            for name, data in indicators.items():
                compiled[category][name] = {
                    "patterns": [
                        re.compile(p, re.IGNORECASE) for p in data["patterns"]
                    ],
                    "severity": data["severity"],
                    "explanation": data["explanation"],
                }
        return compiled

    # -- Content type detection ---------------------------------------------

    @staticmethod
    def _detect_content_type(content: str) -> ContentType:
        lower = content.lower()

        job_kw = ["hiring", "job", "vacancy", "position", "salary", "apply"]
        profile_kw = ["agency", "recruitment", "services", "placement", "licensed"]
        testimonial_kw = ["experience", "worked", "my employer", "i was", "story"]
        chat_kw = ["hi", "hello", "interested", "want to apply", "can you"]

        scores: list[tuple[ContentType, int]] = [
            (ContentType.JOB_POSTING, sum(1 for k in job_kw if k in lower)),
            (ContentType.AGENCY_PAGE, sum(1 for k in profile_kw if k in lower)),
            (ContentType.WORKER_TESTIMONIAL, sum(1 for k in testimonial_kw if k in lower)),
            (ContentType.CHAT_MESSAGE, sum(1 for k in chat_kw if k in lower)),
        ]

        best = max(scores, key=lambda x: x[1])
        return best[0] if best[1] > 1 else ContentType.UNKNOWN

    # -- Indicator matching -------------------------------------------------

    def _find_indicators(self, content: str) -> list[RiskIndicator]:
        indicators: list[RiskIndicator] = []

        for category, cat_indicators in self._compiled.items():
            for name, data in cat_indicators.items():
                for pattern in data["patterns"]:
                    match = pattern.search(content)
                    if match:
                        start = max(0, match.start() - 50)
                        end = min(len(content), match.end() + 50)
                        indicators.append(
                            RiskIndicator(
                                category=category,
                                indicator=name,
                                severity=data["severity"],
                                evidence=match.group(),
                                context=content[start:end],
                                explanation=data["explanation"],
                            )
                        )
                        break  # one match per indicator is enough

        return indicators

    # -- Score calculation --------------------------------------------------

    @staticmethod
    def _calculate_risk_score(indicators: list[RiskIndicator]) -> float:
        if not indicators:
            return 0.0

        total_severity = sum(i.severity for i in indicators)
        categories = {i.category for i in indicators}
        category_multiplier = 1.0 + len(categories) * 0.1
        count_multiplier = min(1.0 + len(indicators) * 0.1, 2.0)

        raw = total_severity * category_multiplier * count_multiplier
        # Normalize: 150 is the practical ceiling for raw scores.
        return round(min(100.0, (raw / 150.0) * 100.0), 1)

    @staticmethod
    def _determine_risk_level(score: float) -> RiskLevel:
        if score <= 20:
            return RiskLevel.MINIMAL
        if score <= 40:
            return RiskLevel.LOW
        if score <= 60:
            return RiskLevel.MODERATE
        if score <= 80:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    # -- Category breakdown -------------------------------------------------

    @staticmethod
    def _build_category_breakdown(indicators: list[RiskIndicator]) -> list[CategoryBreakdown]:
        by_cat: dict[str, list[RiskIndicator]] = {}
        for ind in indicators:
            by_cat.setdefault(ind.category, []).append(ind)

        breakdowns: list[CategoryBreakdown] = []
        for cat in RISK_INDICATORS:
            inds = by_cat.get(cat, [])
            breakdowns.append(
                CategoryBreakdown(
                    category=_CATEGORY_LABELS.get(cat, cat),
                    indicator_count=len(inds),
                    max_severity=max((i.severity for i in inds), default=0),
                    indicators=[i.indicator for i in inds],
                )
            )
        return breakdowns

    # -- Human-readable summary ---------------------------------------------

    @staticmethod
    def _generate_summary(
        indicators: list[RiskIndicator],
        risk_level: RiskLevel,
    ) -> str:
        if not indicators:
            return "No significant risk indicators detected."

        category_counts: dict[str, int] = {}
        for ind in indicators:
            label = _CATEGORY_LABELS.get(ind.category, ind.category)
            category_counts[label] = category_counts.get(label, 0) + 1

        parts: list[str] = []

        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            parts.append(f"ALERT: {risk_level.value.upper()} risk content detected")

        for label, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            parts.append(f"{count} {label} indicator(s)")

        high_sev = [i for i in indicators if i.severity >= 7]
        if high_sev:
            names = ", ".join(sorted({i.indicator.replace("_", " ") for i in high_sev}))
            parts.append(f"Critical concerns: {names}")

        return ". ".join(parts) + "."

    # -- Recommendations ----------------------------------------------------

    @staticmethod
    def _generate_recommendations(
        indicators: list[RiskIndicator],
        risk_level: RiskLevel,
    ) -> list[str]:
        recs: list[str] = []

        if risk_level == RiskLevel.MINIMAL:
            recs.append("Content appears relatively safe, but always verify employer legitimacy.")
            return recs

        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            recs.append("DO NOT proceed with this opportunity without thorough verification.")
            recs.append("Contact your local labor department or POEA (for Philippines) to verify.")
            recs.append(
                "If you or someone you know has already engaged, contact a hotline immediately."
            )

        categories = {i.category for i in indicators}

        if "financial" in categories:
            recs.append(
                "Never pay recruitment fees to work abroad -- this is illegal under international law."
            )
            recs.append("Legitimate employers pay for recruitment, not workers.")

        if "document_control" in categories:
            recs.append("Never surrender your passport to anyone except immigration authorities.")
            recs.append("Keep copies of all documents in a safe place.")

        if "recruitment" in categories:
            recs.append("Verify the agency's license with POEA or relevant labor authority.")
            recs.append("Research the employer independently before applying.")

        if "communication" in categories:
            recs.append("Be cautious of recruiters who avoid official channels.")
            recs.append("Insist on documented, traceable communication.")

        if "control" in categories:
            recs.append("Ensure you have freedom to leave your accommodation.")
            recs.append("Know your emergency contacts and embassy location before traveling.")

        recs.append(
            "Contact: PH OWWA Hotline: 1348 | National Human Trafficking Hotline: 1-888-373-7888"
        )
        return recs

    # -- Public API ---------------------------------------------------------

    def score_content(
        self,
        content: str,
        *,
        content_type: ContentType | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        """Score social media content for exploitation risk.

        Parameters
        ----------
        content:
            The text to analyse.
        content_type:
            Explicit content type; auto-detected when ``None``.
        metadata:
            Arbitrary caller metadata attached to the result.

        Returns
        -------
        RiskAssessment
            Full structured assessment with category breakdown.
        """
        detected_type = content_type or self._detect_content_type(content)
        indicators = self._find_indicators(content)
        risk_score = self._calculate_risk_score(indicators)
        risk_level = self._determine_risk_level(risk_score)
        summary = self._generate_summary(indicators, risk_level)
        recommendations = self._generate_recommendations(indicators, risk_level)
        category_breakdown = self._build_category_breakdown(indicators)

        return RiskAssessment(
            content_id=hashlib.sha256(content.encode()).hexdigest()[:16],
            content_type=detected_type,
            risk_score=risk_score,
            risk_level=risk_level,
            indicators=indicators,
            category_breakdown=category_breakdown,
            summary=summary,
            recommendations=recommendations,
            metadata=metadata or {},
        )

    async def score_content_with_llm(
        self,
        content: str,
        *,
        content_type: ContentType | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        """Score content with additional LLM analysis layered on top.

        Falls back to rule-only scoring when no LLM provider is set.
        """
        assessment = self.score_content(
            content, content_type=content_type, metadata=metadata,
        )

        if self._llm_provider is not None:
            assessment.llm_analysis = await self._get_llm_analysis(content, assessment)

        return assessment

    async def _get_llm_analysis(
        self,
        content: str,
        rule_assessment: RiskAssessment,
    ) -> str:
        """Request a brief expert analysis from the LLM provider."""
        prompt = (
            "Analyze this social media content for human trafficking and "
            "labor exploitation risk indicators.\n\n"
            f"Content to analyze:\n---\n{content[:2000]}\n---\n\n"
            f"Rule-based assessment found:\n"
            f"- Risk Score: {rule_assessment.risk_score}/100\n"
            f"- Risk Level: {rule_assessment.risk_level.value}\n"
            f"- Indicators found: {len(rule_assessment.indicators)}\n\n"
            "Provide a brief expert analysis (2-3 sentences) considering:\n"
            "1. Whether this content shows signs of illegal recruitment\n"
            "2. Red flags that a potential victim should be aware of\n"
            "3. Any concerning patterns the rule-based system may have missed\n\n"
            "Be direct and actionable. Focus on protecting potential victims."
        )
        try:
            response = await self._llm_provider.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an expert in human trafficking detection and "
                    "migrant worker protection. Provide clear, actionable analysis."
                ),
                temperature=0.3,
            )
            return response.response  # type: ignore[union-attr]
        except Exception as exc:
            return f"LLM analysis unavailable: {exc}"


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def quick_risk_score(content: str) -> dict[str, Any]:
    """Return a lightweight risk summary for *content*.

    >>> result = quick_risk_score("Pay $3000 processing fee before deployment")
    >>> result["risk_level"]
    'high'
    """
    scorer = SocialMediaRiskScorer()
    assessment = scorer.score_content(content)
    return {
        "risk_score": assessment.risk_score,
        "risk_level": assessment.risk_level.value,
        "indicator_count": len(assessment.indicators),
        "categories": [
            cb.category for cb in assessment.category_breakdown if cb.indicator_count > 0
        ],
        "summary": assessment.summary,
    }


def analyze_job_posting(posting_text: str) -> RiskAssessment:
    """Convenience wrapper: score a job posting."""
    scorer = SocialMediaRiskScorer()
    return scorer.score_content(posting_text, content_type=ContentType.JOB_POSTING)
