"""NGO-focused multi-document migration case workflow for the DueCare demo."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .function_calling import execute_tool
from .models import (
    CaseDocumentFinding,
    ComplaintDraft,
    MigrationCaseDocument,
    MigrationCaseRequest,
    MigrationCaseResponse,
    Resource,
    TimelineEvent,
)
from .multimodal import DocumentAnalyzer
from .rag import RAGStore

_COUNTRY_NAME_TO_CODE = {
    "bangladesh": "BD",
    "hong kong": "HK",
    "indonesia": "ID",
    "malaysia": "MY",
    "nepal": "NP",
    "philippines": "PH",
    "qatar": "QA",
    "saudi arabia": "SA",
    "singapore": "SG",
    "taiwan": "TW",
    "united arab emirates": "AE",
    "uae": "AE",
}

_COUNTRY_CODE_TO_NAME = {
    "AE": "United Arab Emirates",
    "BD": "Bangladesh",
    "HK": "Hong Kong",
    "ID": "Indonesia",
    "INTL": "international",
    "MY": "Malaysia",
    "NP": "Nepal",
    "PH": "Philippines",
    "QA": "Qatar",
    "SA": "Saudi Arabia",
    "SG": "Singapore",
    "TW": "Taiwan",
}

_CORRIDOR_LABELS = {
    "BD_MY": "Bangladesh -> Malaysia",
    "BD_SA": "Bangladesh -> Saudi Arabia",
    "ID_MY": "Indonesia -> Malaysia",
    "ID_SA": "Indonesia -> Saudi Arabia",
    "NP_MY": "Nepal -> Malaysia",
    "NP_QA": "Nepal -> Qatar",
    "PH_AE": "Philippines -> United Arab Emirates",
    "PH_HK": "Philippines -> Hong Kong",
    "PH_SA": "Philippines -> Saudi Arabia",
    "PH_SG": "Philippines -> Singapore",
    "VN_TW": "Vietnam -> Taiwan",
}

_COUNTRY_PAIR_TO_CORRIDOR = {
    ("BD", "MY"): "BD_MY",
    ("BD", "SA"): "BD_SA",
    ("ID", "MY"): "ID_MY",
    ("ID", "SA"): "ID_SA",
    ("NP", "MY"): "NP_MY",
    ("NP", "QA"): "NP_QA",
    ("PH", "AE"): "PH_AE",
    ("PH", "HK"): "PH_HK",
    ("PH", "SA"): "PH_SA",
    ("PH", "SG"): "PH_SG",
    ("VN", "TW"): "VN_TW",
}

_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

_INDICATOR_LABELS = {
    "coercion_or_penalty": "coercion or penalty language",
    "contract_substitution": "contract substitution",
    "debt_bondage_risk": "debt bondage risk",
    "document_irregularity": "document irregularity",
    "passport_retention": "passport retention",
    "salary_deduction_scheme": "salary deduction scheme",
    "wage_withholding": "wage withholding",
    "worker_paid_placement_fee": "worker-paid recruitment fee",
}

_FLAG_TO_SCENARIO = {
    "worker_paid_placement_fee": "recruitment_fee",
    "salary_deduction_scheme": "salary_deduction",
    "passport_retention": "passport_retention",
    "debt_bondage_risk": "debt_bondage",
    "contract_substitution": "contract_substitution",
    "wage_withholding": "wage_withholding",
    "coercion_or_penalty": "passport_retention",
}

_DOCUMENT_EVENT_LABELS = {
    "agency_certificate": "Agency credential reviewed",
    "chat_transcript": "Recruitment conversation captured",
    "employment_contract": "Contract terms recorded",
    "identity_document": "Identity document referenced",
    "job_posting": "Recruitment offer documented",
    "payment_receipt": "Payment demand recorded",
    "recruitment_document": "Recruitment paperwork reviewed",
}

_LEGAL_PATTERN = re.compile(
    r"\b(?:ILO\s+C\d+(?:\s+Art\.\s*\d+)?|ILO\s+P\d+|RA\s+\d+|Palermo\s+Protocol|Dhaka\s+Principles)\b",
    re.IGNORECASE,
)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return ordered


def _normalize_corridor(raw: str) -> str:
    return raw.strip().upper().replace("-", "_")


def _coerce_document_id(index: int, document: MigrationCaseDocument) -> str:
    return document.document_id or f"doc-{index:02d}"


def _country_code_from_name(name: str) -> str | None:
    return _COUNTRY_NAME_TO_CODE.get(name.strip().lower())


def _corridor_display(corridor: str) -> str:
    if not corridor:
        return ""
    corridor = _normalize_corridor(corridor)
    if corridor in _CORRIDOR_LABELS:
        return _CORRIDOR_LABELS[corridor]
    if "_" not in corridor:
        return _COUNTRY_CODE_TO_NAME.get(corridor, corridor)
    origin, destination = corridor.split("_", 1)
    return f"{_COUNTRY_CODE_TO_NAME.get(origin, origin)} -> {_COUNTRY_CODE_TO_NAME.get(destination, destination)}"


def _parse_numeric_amount(raw_amount: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", raw_amount)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def _parse_date(raw_date: str) -> datetime | None:
    cleaned = raw_date.strip()
    if not cleaned:
        return None
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def _resolve_corridor(explicit: str, document_analyses: list[CaseDocumentFinding]) -> str:
    normalized = _normalize_corridor(explicit)
    if normalized:
        return normalized

    ordered_codes: list[str] = []
    for document in document_analyses:
        for candidate in document.extracted_fields.get("corridor_candidates", []):
            normalized_candidate = _normalize_corridor(str(candidate))
            if normalized_candidate and normalized_candidate not in ordered_codes:
                return normalized_candidate
        for country_name in document.extracted_fields.get("countries", []):
            code = _country_code_from_name(str(country_name))
            if code and code not in ordered_codes:
                ordered_codes.append(code)

    if len(ordered_codes) >= 2:
        return _COUNTRY_PAIR_TO_CORRIDOR.get((ordered_codes[0], ordered_codes[1]), f"{ordered_codes[0]}_{ordered_codes[1]}")
    if ordered_codes:
        return ordered_codes[0]
    return ""


def _select_primary_scenario(indicators: list[str]) -> str:
    for indicator in indicators:
        scenario = _FLAG_TO_SCENARIO.get(indicator)
        if scenario:
            return scenario
    return "recruitment_fee"


def _largest_fee_amount(document_analyses: list[CaseDocumentFinding]) -> float:
    amounts: list[float] = []
    for document in document_analyses:
        for raw_amount in document.extracted_fields.get("amounts", []):
            value = _parse_numeric_amount(str(raw_amount))
            if value > 0:
                amounts.append(value)
    return max(amounts, default=0.0)


def _hotline_country(corridor: str) -> str:
    corridor = _normalize_corridor(corridor)
    if not corridor:
        return "INTL"
    if "_" in corridor:
        return corridor.split("_", 1)[1]
    return corridor


def _tool_results(
    *,
    combined_text: str,
    corridor: str,
    indicators: list[str],
    largest_fee_amount: float,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    results.append(
        {
            "tool": "score_exploitation_risk",
            "result": execute_tool("score_exploitation_risk", {"text": combined_text}),
        }
    )
    results.append(
        {
            "tool": "identify_trafficking_indicators",
            "result": execute_tool("identify_trafficking_indicators", {"text": combined_text}),
        }
    )
    results.append(
        {
            "tool": "check_legal_framework",
            "result": execute_tool(
                "check_legal_framework",
                {
                    "jurisdiction": corridor or "PH",
                    "scenario": _select_primary_scenario(indicators),
                },
            ),
        }
    )

    if largest_fee_amount > 0:
        fee_country = corridor.split("_", 1)[0] if "_" in corridor else (corridor or "PH")
        results.append(
            {
                "tool": "check_fee_legality",
                "result": execute_tool(
                    "check_fee_legality",
                    {
                        "country": fee_country,
                        "fee_amount": largest_fee_amount,
                        "worker_type": "domestic",
                    },
                ),
            }
        )

    results.append(
        {
            "tool": "lookup_hotline",
            "result": execute_tool("lookup_hotline", {"country": _hotline_country(corridor)}),
        }
    )
    return results


def _resources_from_documents(
    document_analyses: list[CaseDocumentFinding],
    tool_results: list[dict[str, object]],
) -> list[Resource]:
    resources: list[Resource] = []
    seen: set[tuple[str, str | None, str | None]] = set()

    for document in document_analyses:
        for resource in document.extracted_fields.get("resources", []):
            name = str(resource.get("name", "")).strip()
            number = resource.get("number")
            url = resource.get("url")
            key = (name.lower(), str(number) if number else None, str(url) if url else None)
            if not name or key in seen:
                continue
            seen.add(key)
            resources.append(
                Resource(
                    name=name,
                    type=str(resource.get("type", "hotline")),
                    number=str(number) if number else None,
                    url=str(url) if url else None,
                    jurisdiction=str(resource.get("jurisdiction", "")),
                )
            )

    for tool_call in tool_results:
        if tool_call.get("tool") != "lookup_hotline":
            continue
        result = tool_call.get("result", {})
        if not isinstance(result, dict):
            continue
        jurisdiction = str(result.get("country", ""))
        contacts = result.get("contacts", [])
        if not isinstance(contacts, list):
            continue
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            name = str(contact.get("name", "")).strip()
            number = contact.get("number")
            url = contact.get("url")
            key = (name.lower(), str(number) if number else None, str(url) if url else None)
            if not name or key in seen:
                continue
            seen.add(key)
            resources.append(
                Resource(
                    name=name,
                    type=str(contact.get("type", "hotline")),
                    number=str(number) if number else None,
                    url=str(url) if url else None,
                    jurisdiction=jurisdiction,
                )
            )

    return resources


def _legal_refs_from_context(retrieved_context: str) -> list[str]:
    return _dedupe(_LEGAL_PATTERN.findall(retrieved_context))


def _aggregate_legal_refs(
    document_analyses: list[CaseDocumentFinding],
    tool_results: list[dict[str, object]],
    retrieved_context: str,
) -> list[str]:
    refs: list[str] = []
    for document in document_analyses:
        refs.extend(document.legal_refs)
    refs.extend(_legal_refs_from_context(retrieved_context))

    for tool_call in tool_results:
        result = tool_call.get("result", {})
        if not isinstance(result, dict):
            continue
        applicable_laws = result.get("applicable_laws")
        if isinstance(applicable_laws, list):
            refs.extend(str(item) for item in applicable_laws)
        local_law = result.get("local_law")
        if isinstance(local_law, str):
            refs.append(local_law)
        law = result.get("law")
        if isinstance(law, str):
            refs.append(law)

    return _dedupe(refs)


def _overall_risk_level(
    document_analyses: list[CaseDocumentFinding],
    tool_results: list[dict[str, object]],
    detected_indicators: list[str],
) -> str:
    highest_document_risk = max((_RISK_ORDER.get(doc.risk_level, 0) for doc in document_analyses), default=0)

    tool_score = 0.0
    for tool_call in tool_results:
        if tool_call.get("tool") != "score_exploitation_risk":
            continue
        result = tool_call.get("result", {})
        if isinstance(result, dict):
            tool_score = float(result.get("score", 0.0) or 0.0)
        break

    if highest_document_risk >= 2 or tool_score >= 0.6 or len(detected_indicators) >= 3:
        return "HIGH"
    if highest_document_risk >= 1 or tool_score >= 0.3 or detected_indicators:
        return "MEDIUM"
    return "LOW"


def _timeline_for_case(
    request_documents: list[MigrationCaseDocument],
    document_analyses: list[CaseDocumentFinding],
) -> list[TimelineEvent]:
    ordered_events: list[tuple[datetime | None, int, TimelineEvent]] = []
    for index, (document, analysis) in enumerate(zip(request_documents, document_analyses, strict=False), start=1):
        title = analysis.title or document.title or f"Document {index}"
        label = _DOCUMENT_EVENT_LABELS.get(analysis.document_type, "Document reviewed")
        description = analysis.findings[0] if analysis.findings else f"{title} was added to the case bundle."
        markers = analysis.timeline_markers or ([document.captured_at] if document.captured_at else [])
        marker = markers[0] if markers else "Undated"
        sort_key = _parse_date(marker)
        ordered_events.append(
            (
                sort_key,
                index,
                TimelineEvent(
                    date=marker,
                    label=label,
                    document_id=analysis.document_id,
                    description=description,
                ),
            )
        )

    ordered_events.sort(key=lambda item: (item[0] is None, item[0] or datetime.max, item[1]))
    return [event for _, _, event in ordered_events]


def _executive_summary(
    *,
    corridor: str,
    risk_level: str,
    document_analyses: list[CaseDocumentFinding],
    indicators: list[str],
    legal_refs: list[str],
) -> str:
    corridor_text = _corridor_display(corridor) or "an inbound migration corridor"
    indicator_labels = [_INDICATOR_LABELS.get(flag, flag.replace("_", " ")) for flag in indicators[:4]]
    highest_risk_titles = [doc.title for doc in document_analyses if doc.risk_level == "HIGH"][:2]

    parts = [
        f"DueCare reviewed {len(document_analyses)} documents for {corridor_text} and rated the bundle {risk_level.lower()} risk.",
    ]
    if indicator_labels:
        parts.append(f"The strongest signals were {', '.join(indicator_labels)}.")
    if highest_risk_titles:
        parts.append(f"Highest-risk material came from {', '.join(highest_risk_titles)}.")
    if legal_refs:
        parts.append(f"Grounding context centered on {', '.join(legal_refs[:3])}.")
    return " ".join(parts)


def _case_narrative(
    *,
    risk_level: str,
    indicators: list[str],
    timeline: list[TimelineEvent],
    legal_refs: list[str],
) -> str:
    narrative_parts: list[str] = []
    for event in timeline[:4]:
        prefix = event.date if event.date != "Undated" else "At an undated point in the file"
        narrative_parts.append(f"{prefix}, {event.description.rstrip('.')}.")

    if indicators:
        labels = [_INDICATOR_LABELS.get(flag, flag.replace("_", " ")) for flag in indicators[:4]]
        narrative_parts.append(
            f"Across the bundle, DueCare repeatedly detected {', '.join(labels)}, which is consistent with a {risk_level.lower()}-risk recruitment pattern."
        )
    if legal_refs:
        narrative_parts.append(f"The case narrative was grounded against {', '.join(legal_refs[:3])}.")
    return " ".join(narrative_parts)


def _recommended_actions(
    *,
    indicators: list[str],
    risk_level: str,
    hotlines: list[Resource],
) -> list[str]:
    actions = [
        "Preserve the original files, export metadata, and keep a clean index of what each document shows.",
        "Compare recruitment promises against the contract and payment trail before any further payment or travel.",
    ]

    if any(flag in indicators for flag in {"worker_paid_placement_fee", "salary_deduction_scheme", "debt_bondage_risk"}):
        actions.append("Freeze further worker-paid fees or deductions until a labor-law review confirms they are lawful.")
    if "passport_retention" in indicators:
        actions.append("Escalate any passport or identity-document retention language immediately; do not surrender original documents without legal review.")
    if risk_level == "HIGH":
        actions.append("Move the case into urgent NGO or legal triage and preserve the complaint-ready timeline below.")
    if hotlines:
        actions.append(f"Escalate with a hotline or support office such as {hotlines[0].name}.")
    return _dedupe(actions)


def _complaint_templates(
    *,
    case_id: str,
    corridor: str,
    executive_summary: str,
    narrative: str,
    timeline: list[TimelineEvent],
    legal_refs: list[str],
    actions: list[str],
) -> list[ComplaintDraft]:
    timeline_lines = "\n".join(
        f"- {event.date}: {event.label}. {event.description}" for event in timeline
    )
    law_lines = "\n".join(f"- {law}" for law in legal_refs[:6])
    action_lines = "\n".join(f"- {action}" for action in actions)
    corridor_label = _corridor_display(corridor) or corridor or "unspecified corridor"

    return [
        ComplaintDraft(
            name="ngo_intake_summary",
            audience="NGO case worker",
            text=(
                f"Case ID: {case_id}\n"
                f"Corridor: {corridor_label}\n\n"
                f"Executive summary:\n{executive_summary}\n\n"
                f"Narrative:\n{narrative}\n\n"
                f"Timeline:\n{timeline_lines}\n\n"
                f"Immediate actions:\n{action_lines}"
            ),
        ),
        ComplaintDraft(
            name="labor_regulator_outline",
            audience="Labor regulator or embassy labor desk",
            text=(
                f"Subject: Request for review of possible migrant worker exploitation in {corridor_label}\n\n"
                f"Summary:\n{executive_summary}\n\n"
                f"Key legal references:\n{law_lines}\n\n"
                f"Documented timeline:\n{timeline_lines}\n\n"
                "Requested next step:\n"
                "- Review the recruitment fee, salary deduction, and document-control evidence attached to this complaint.\n"
                "- Confirm whether the agency or employer is compliant with the listed laws and conventions."
            ),
        ),
        ComplaintDraft(
            name="worker_affidavit_outline",
            audience="Paralegal or affidavit drafter",
            text=(
                "Use this outline to prepare a worker statement without exposing unnecessary personal data.\n\n"
                f"Case reference: {case_id}\n"
                f"Corridor: {corridor_label}\n\n"
                "Suggested sections:\n"
                "- How the worker was recruited\n"
                "- What payments were requested or deducted\n"
                "- What document-control or coercive language appeared\n"
                "- What happened after travel or contract signing\n\n"
                f"Timeline cues:\n{timeline_lines}"
            ),
        ),
    ]


class MigrationCaseOrchestrator:
    """Analyze a bundle of migration documents and synthesize a case packet."""

    def __init__(
        self,
        *,
        analyzer: DocumentAnalyzer | None = None,
        rag_store: RAGStore | None = None,
    ) -> None:
        self._analyzer = analyzer or DocumentAnalyzer(model=None)
        self._rag_store = rag_store

    def analyze_case(self, request: MigrationCaseRequest) -> MigrationCaseResponse:
        document_analyses: list[CaseDocumentFinding] = []
        combined_text_parts: list[str] = []
        detected_indicators: list[str] = []

        for index, document in enumerate(request.documents, start=1):
            analysis = self._analyzer.analyze_text_as_document(document.text, context=document.context)
            document_id = _coerce_document_id(index, document)
            title = document.title or f"Document {index}"
            document_analyses.append(
                CaseDocumentFinding(
                    document_id=document_id,
                    title=title,
                    context=document.context,
                    document_type=str(analysis.extracted_fields.get("document_type", "recruitment_document")),
                    risk_level=analysis.risk_level,
                    findings=analysis.findings,
                    legal_refs=analysis.legal_refs,
                    indicator_flags=analysis.indicator_flags,
                    extracted_fields=analysis.extracted_fields,
                    timeline_markers=analysis.timeline_markers or ([document.captured_at] if document.captured_at else []),
                    confidence=analysis.confidence,
                )
            )
            combined_text_parts.append(document.text)
            detected_indicators.extend(analysis.indicator_flags)

        detected_indicators = _dedupe(detected_indicators)
        resolved_corridor = _resolve_corridor(request.corridor, document_analyses)
        combined_text = "\n\n".join(combined_text_parts)
        tool_results = _tool_results(
            combined_text=combined_text,
            corridor=resolved_corridor,
            indicators=detected_indicators,
            largest_fee_amount=_largest_fee_amount(document_analyses),
        )
        timeline = _timeline_for_case(request.documents, document_analyses)

        rag_store = self._rag_store or RAGStore.from_configs()
        query_tokens = [resolved_corridor, *detected_indicators[:4]]
        query = " ".join(token for token in query_tokens if token).strip() or combined_text[:240]
        retrieved_context = rag_store.retrieve(query, top_k=request.top_k_context)

        hotlines = _resources_from_documents(document_analyses, tool_results)
        applicable_laws = _aggregate_legal_refs(document_analyses, tool_results, retrieved_context)
        risk_level = _overall_risk_level(document_analyses, tool_results, detected_indicators)
        executive_summary = _executive_summary(
            corridor=resolved_corridor,
            risk_level=risk_level,
            document_analyses=document_analyses,
            indicators=detected_indicators,
            legal_refs=applicable_laws,
        )
        narrative = _case_narrative(
            risk_level=risk_level,
            indicators=detected_indicators,
            timeline=timeline,
            legal_refs=applicable_laws,
        )
        recommended_actions = _recommended_actions(
            indicators=detected_indicators,
            risk_level=risk_level,
            hotlines=hotlines,
        )
        complaint_templates = []
        if request.include_complaint_templates:
            complaint_templates = _complaint_templates(
                case_id=request.case_id or "case-demo-001",
                corridor=resolved_corridor,
                executive_summary=executive_summary,
                narrative=narrative,
                timeline=timeline,
                legal_refs=applicable_laws,
                actions=recommended_actions,
            )

        return MigrationCaseResponse(
            case_id=request.case_id or f"case-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            corridor=resolved_corridor,
            document_count=len(document_analyses),
            risk_level=risk_level,
            detected_indicators=detected_indicators,
            applicable_laws=applicable_laws,
            retrieved_context=retrieved_context,
            executive_summary=executive_summary,
            narrative=narrative,
            timeline=timeline,
            document_analyses=document_analyses,
            recommended_actions=recommended_actions,
            hotlines=hotlines,
            tool_results=tool_results,
            complaint_templates=complaint_templates,
        )