"""Weighted rubric scorer for the DueCare demo.

Loads rubric YAML files on startup and scores arbitrary text against
each rubric's criteria using indicator phrase matching.  This is the
deterministic, zero-inference scorer — it runs without any LLM and
produces structured results suitable for the video demo and the
enterprise waterfall pipeline.

When a fine-tuned Gemma 4 model is available, the LLM-as-judge path
can be layered on top by replacing the ``_match_criterion`` method
with an inference call.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from .models import (
    Action,
    AnalyzeRequest,
    AnalyzeResponse,
    CriterionResult,
    Grade,
    Resource,
    RubricInfo,
    RubricResult,
)


# ---------------------------------------------------------------------------
# Internal rubric model (mirrors duecare.core.schemas.EvaluationRubric
# but stays self-contained so the demo runs standalone)
# ---------------------------------------------------------------------------

class _Criterion(BaseModel):
    id: str
    description: str
    weight: float = 1.0
    required: bool = True
    category: str = ""
    pass_indicators: list[str] = Field(default_factory=list)
    fail_indicators: list[str] = Field(default_factory=list)


class _Rubric(BaseModel):
    name: str
    version: str = "1.0"
    category: str
    description: str = ""
    criteria: list[_Criterion] = Field(default_factory=list)
    refusal_phrases: list[str] = Field(default_factory=list)
    harmful_phrases: list[str] = Field(default_factory=list)
    acceptable_sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_weight(self) -> float:
        return sum(c.weight for c in self.criteria)


# ---------------------------------------------------------------------------
# Jurisdiction-aware resource database
# ---------------------------------------------------------------------------

_RESOURCES: dict[str, list[Resource]] = {
    "PH": [
        Resource(name="POEA Hotline", type="hotline", number="1343", jurisdiction="PH"),
        Resource(name="OWWA (Overseas Workers Welfare Administration)", type="office", number="1348", jurisdiction="PH"),
        Resource(name="DOLE (Dept. of Labor & Employment)", type="office", url="https://www.dole.gov.ph", jurisdiction="PH"),
        Resource(name="Commission on Filipinos Overseas", type="office", url="https://www.cfo.gov.ph", jurisdiction="PH"),
    ],
    "HK": [
        Resource(name="Hong Kong Labour Department", type="office", number="2717-1771", url="https://www.labour.gov.hk", jurisdiction="HK"),
        Resource(name="Hong Kong Police (Anti-Trafficking)", type="hotline", number="999", jurisdiction="HK"),
        Resource(name="PathFinders HK", type="ngo", url="https://www.pathfinders.org.hk", jurisdiction="HK"),
        Resource(name="Mission for Migrant Workers", type="ngo", url="https://www.migrants.net", jurisdiction="HK"),
    ],
    "SA": [
        Resource(name="Saudi Ministry of Human Resources", type="office", number="19911", jurisdiction="SA"),
        Resource(name="National Committee for Combating Trafficking", type="office", number="1909", jurisdiction="SA"),
    ],
    "MY": [
        Resource(name="Malaysia MOHR (Ministry of Human Resources)", type="office", url="https://www.mohr.gov.my", jurisdiction="MY"),
        Resource(name="Tenaganita", type="ngo", url="https://www.tenaganita.net", jurisdiction="MY"),
    ],
    "NP": [
        Resource(name="Nepal Department of Foreign Employment", type="office", url="https://www.dofe.gov.np", jurisdiction="NP"),
        Resource(name="HRD Nepal", type="ngo", url="https://www.hrdnepal.org", jurisdiction="NP"),
    ],
    "BD": [
        Resource(name="BMET (Bureau of Manpower, Employment & Training)", type="office", url="https://www.bmet.gov.bd", jurisdiction="BD"),
    ],
    "ID": [
        Resource(name="BP2MI (National Board for Migrant Worker Protection)", type="office", url="https://www.bp2mi.go.id", jurisdiction="ID"),
    ],
    "intl": [
        Resource(name="IOM (International Organization for Migration)", type="website", url="https://www.iom.int", jurisdiction="intl"),
        Resource(name="ILO Helpdesk for Business", type="website", url="https://www.ilo.org/business", jurisdiction="intl"),
        Resource(name="Polaris Project (Global Modern Slavery Directory)", type="ngo", url="https://polarisproject.org", jurisdiction="intl"),
        Resource(name="IJM (International Justice Mission)", type="ngo", url="https://www.ijm.org", jurisdiction="intl"),
        Resource(name="ECPAT International", type="ngo", url="https://www.ecpat.org", jurisdiction="intl"),
        Resource(name="National Human Trafficking Hotline (US)", type="hotline", number="1-888-373-7888", jurisdiction="intl"),
    ],
}


# ---------------------------------------------------------------------------
# Jurisdiction-aware legal reference database
# ---------------------------------------------------------------------------

_LEGAL_REFS: dict[str, list[str]] = {
    "PH": [
        "RA 8042 (Migrant Workers and Overseas Filipinos Act)",
        "RA 10022 (Amended Migrant Workers Act)",
        "RA 9208 (Anti-Trafficking in Persons Act)",
        "RA 10364 (Expanded Anti-Trafficking Act)",
        "POEA Rules and Regulations on Recruitment",
    ],
    "HK": [
        "Employment Ordinance (Cap. 57)",
        "Money Lenders Ordinance (Cap. 163)",
        "Crimes Ordinance (Cap. 200) - trafficking provisions",
    ],
    "SA": [
        "Saudi Anti-Trafficking in Persons Law (Royal Decree M/40)",
        "Saudi Labor Law (Arts. 61-62, recruitment fees)",
    ],
    "intl": [
        "ILO C181 Art. 7 (Private Employment Agencies Convention)",
        "ILO C029 (Forced Labour Convention)",
        "ILO C189 (Domestic Workers Convention)",
        "ILO C095 (Protection of Wages Convention)",
        "Palermo Protocol (Protocol to Prevent, Suppress and Punish Trafficking)",
        "Dhaka Principles for Migration with Dignity",
    ],
}


# ---------------------------------------------------------------------------
# Warning text templates
# ---------------------------------------------------------------------------

_WARNING_TEMPLATES: dict[str, dict[str, str]] = {
    "en": {
        "worst": (
            "CRITICAL WARNING: This content contains strong indicators of "
            "labor exploitation or trafficking. {legal_detail} "
            "If you or someone you know is affected, contact the resources below immediately."
        ),
        "bad": (
            "WARNING: This content shows concerning indicators of potential "
            "exploitation. {legal_detail} "
            "Please review the resources below for guidance."
        ),
        "neutral": (
            "NOTICE: Some elements of this content may warrant further review. "
            "{legal_detail}"
        ),
        "good": "This content appears largely compliant with labor protection standards.",
        "best": "This content demonstrates strong alignment with worker protection principles.",
    },
    "tl": {
        "worst": (
            "BABALA: Ang nilalaman na ito ay may malakas na mga palatandaan ng "
            "pagsasamantala sa paggawa o trafficking. {legal_detail} "
            "Kung ikaw o ang kakilala mo ay apektado, makipag-ugnayan sa mga resources sa ibaba."
        ),
        "bad": (
            "BABALA: Ang nilalaman na ito ay may mga nakababahalang palatandaan ng "
            "posibleng pagsasamantala. {legal_detail}"
        ),
        "neutral": "PAUNAWA: Ang ilang bahagi ng nilalaman na ito ay maaaring kailangan ng karagdagang pagsusuri.",
        "good": "Ang nilalaman na ito ay mukhang sumusunod sa mga pamantayan ng proteksyon sa paggawa.",
        "best": "Ang nilalaman na ito ay nagpapakita ng malakas na pagsunod sa mga prinsipyo ng proteksyon sa manggagawa.",
    },
}


# ---------------------------------------------------------------------------
# WeightedRubricScorer
# ---------------------------------------------------------------------------

class WeightedRubricScorer:
    """Deterministic phrase-matching scorer against loaded rubric YAMLs.

    Usage::

        scorer = WeightedRubricScorer.from_directory(
            Path("configs/duecare/domains/trafficking/rubrics")
        )
        result = scorer.analyze(request)
    """

    def __init__(self, rubrics: list[_Rubric]) -> None:
        self._rubrics: list[_Rubric] = rubrics
        self._stats: Counter[str] = Counter()

    # -- Construction -------------------------------------------------------

    @classmethod
    def from_directory(cls, rubric_dir: Path) -> WeightedRubricScorer:
        """Load all YAML rubric files from *rubric_dir*."""
        rubrics: list[_Rubric] = []
        if not rubric_dir.is_dir():
            return cls(rubrics)
        for path in sorted(rubric_dir.glob("*.yaml")):
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data:
                rubrics.append(_Rubric.model_validate(data))
        return cls(rubrics)

    # -- Public API ---------------------------------------------------------

    @property
    def rubrics(self) -> list[_Rubric]:
        return list(self._rubrics)

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    def list_rubrics(self) -> list[RubricInfo]:
        """Return summary info for each loaded rubric."""
        return [
            RubricInfo(
                name=r.name,
                version=r.version,
                category=r.category,
                n_criteria=len(r.criteria),
                total_weight=r.total_weight,
                description=r.description.strip(),
            )
            for r in self._rubrics
        ]

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """Score *request.text* against all (or selected) rubrics.

        Returns a fully populated ``AnalyzeResponse``.
        """
        text_lower = request.text.lower()

        # Determine which rubrics to run
        rubrics_to_run = self._rubrics
        if request.rubric_ids:
            rubrics_to_run = [
                r for r in self._rubrics if r.category in request.rubric_ids
            ]
            if not rubrics_to_run:
                rubrics_to_run = self._rubrics

        # Score against each rubric
        rubric_results: list[RubricResult] = []
        all_indicators: list[str] = []

        for rubric in rubrics_to_run:
            rr = self._score_rubric(rubric, text_lower)
            rubric_results.append(rr)
            # Collect indicators from failed criteria
            for cr in rr.criteria_results:
                if cr.result == "fail" and cr.required:
                    all_indicators.append(cr.criterion_id)

        # Aggregate score: weighted average across rubrics
        if rubric_results:
            total_weight = sum(r.score * len(r.criteria_results) for r in rubric_results)
            total_criteria = sum(len(r.criteria_results) for r in rubric_results)
            agg_score = total_weight / max(total_criteria, 1)
        else:
            agg_score = 0.5

        grade = Grade.from_score(agg_score)
        action = self._determine_action(grade)

        # Deduplicate indicators and name them readably
        unique_indicators = list(dict.fromkeys(all_indicators))

        # Collect legal refs and resources based on jurisdiction
        legal_refs = self._get_legal_refs(request.jurisdiction)
        resources = self._get_resources(request.jurisdiction)

        # Build warning text
        warning_text = self._build_warning(
            grade=grade,
            language=request.language,
            legal_refs=legal_refs,
        )

        # Update stats
        self._stats["total_analyses"] += 1
        self._stats[f"grade_{grade.value}"] += 1
        self._stats[f"action_{action.value}"] += 1

        return AnalyzeResponse(
            score=round(agg_score, 4),
            grade=grade,
            action=action,
            indicators=unique_indicators,
            legal_refs=legal_refs,
            warning_text=warning_text,
            resources=resources,
            rubric_results=rubric_results,
            language=request.language,
            jurisdiction=request.jurisdiction,
        )

    # -- Internals ----------------------------------------------------------

    def _score_rubric(self, rubric: _Rubric, text_lower: str) -> RubricResult:
        """Score text against a single rubric."""
        criteria_results: list[CriterionResult] = []
        weighted_score = 0.0
        total_weight = 0.0

        for criterion in rubric.criteria:
            cr = self._match_criterion(criterion, text_lower)
            criteria_results.append(cr)

            if cr.result == "pass":
                weighted_score += criterion.weight
            elif cr.result == "partial":
                weighted_score += criterion.weight * 0.5

            total_weight += criterion.weight

        # Check for required-criterion failures
        required_failed = any(
            cr.result == "fail" and cr.required for cr in criteria_results
        )

        raw_score = weighted_score / max(total_weight, 0.001)

        # Cap score at neutral if any required criterion failed
        if required_failed:
            raw_score = min(raw_score, 0.39)

        grade = Grade.from_score(raw_score)

        return RubricResult(
            rubric_name=rubric.name,
            rubric_category=rubric.category,
            score=round(raw_score, 4),
            grade=grade,
            criteria_results=criteria_results,
        )

    @staticmethod
    def _match_criterion(criterion: _Criterion, text_lower: str) -> CriterionResult:
        """Match a single criterion using indicator phrase matching.

        This is the deterministic, zero-inference path.  When the
        fine-tuned Gemma 4 model is available, this method can be
        replaced with an LLM-as-judge call that uses the criterion
        description and indicators as grading context.

        The scorer evaluates the text *as content under review*, not as
        a model response.  For user-submitted text (job postings, chat
        messages, contracts), the presence of fail_indicators (phrases
        that normalize exploitation) is a red flag, while the absence
        of pass_indicators (phrases a good response would contain) is
        expected -- the user's text is not a model response that should
        contain refusals or legal citations.

        Scoring logic:
        - fail_indicator present -> the text actively normalizes or
          facilitates exploitation -> criterion fails
        - pass_indicator present AND no fail_indicator -> text shows
          protective language -> criterion passes
        - Neither present -> partial (ambiguous / needs deeper review)
        """
        matched_pass: list[str] = []
        matched_fail: list[str] = []

        for phrase in criterion.pass_indicators:
            if phrase.lower() in text_lower:
                matched_pass.append(phrase)

        for phrase in criterion.fail_indicators:
            if phrase.lower() in text_lower:
                matched_fail.append(phrase)

        # Determine result
        if matched_fail:
            result = "fail"
        elif matched_pass:
            result = "pass"
        else:
            result = "partial"

        return CriterionResult(
            criterion_id=criterion.id,
            description=criterion.description,
            result=result,
            weight=criterion.weight,
            required=criterion.required,
            matched_indicators=matched_pass + matched_fail,
            category=criterion.category,
        )

    @staticmethod
    def _determine_action(grade: Grade) -> Action:
        """Map a grade to a recommended platform action."""
        if grade == Grade.WORST:
            return Action.BLOCK
        if grade == Grade.BAD:
            return Action.REVIEW
        if grade == Grade.NEUTRAL:
            return Action.WARN
        return Action.PASS

    @staticmethod
    def _get_legal_refs(jurisdiction: str) -> list[str]:
        """Return applicable legal references for a jurisdiction corridor."""
        refs: list[str] = []

        # Parse corridor (e.g. "PH_HK") or single code
        codes = [j.strip().upper() for j in jurisdiction.replace("-", "_").split("_") if j.strip()]

        for code in codes:
            refs.extend(_LEGAL_REFS.get(code, []))

        # Always include international standards
        refs.extend(_LEGAL_REFS.get("intl", []))

        # Deduplicate preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for ref in refs:
            if ref not in seen:
                seen.add(ref)
                unique.append(ref)
        return unique

    @staticmethod
    def _get_resources(jurisdiction: str) -> list[Resource]:
        """Return relevant resources for a jurisdiction corridor."""
        resources: list[Resource] = []

        codes = [j.strip().upper() for j in jurisdiction.replace("-", "_").split("_") if j.strip()]

        for code in codes:
            resources.extend(_RESOURCES.get(code, []))

        # Always include international resources
        resources.extend(_RESOURCES.get("intl", []))

        # Deduplicate by name
        seen: set[str] = set()
        unique: list[Resource] = []
        for r in resources:
            if r.name not in seen:
                seen.add(r.name)
                unique.append(r)
        return unique

    @staticmethod
    def _build_warning(
        *,
        grade: Grade,
        language: str,
        legal_refs: list[str],
    ) -> str:
        """Build a localized warning message."""
        templates = _WARNING_TEMPLATES.get(language, _WARNING_TEMPLATES["en"])
        template = templates.get(grade.value, templates.get("neutral", ""))

        # Build legal detail snippet
        if legal_refs and grade.ordinal <= Grade.NEUTRAL.ordinal:
            top_refs = legal_refs[:3]
            legal_detail = "Potentially relevant laws: " + "; ".join(top_refs) + "."
        else:
            legal_detail = ""

        return template.format(legal_detail=legal_detail).strip()
