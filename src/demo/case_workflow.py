"""NGO-focused multi-document migration case workflow for the DueCare demo."""

from __future__ import annotations

import re
from collections import Counter
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

_CASE_CATEGORY_ORDER = {
    "employment_agency_misconduct": 0,
    "worker_fee_overcharge": 1,
    "medical_clinic_fee_abuse": 2,
    "money_lender_debt_pressure": 3,
    "document_retention": 4,
    "contract_substitution": 5,
}

_CASE_CATEGORY_LABELS = {
    "employment_agency_misconduct": "employment agency misconduct",
    "worker_fee_overcharge": "worker fee overcharge",
    "medical_clinic_fee_abuse": "medical clinic fee abuse",
    "money_lender_debt_pressure": "money lender debt pressure",
    "document_retention": "document retention",
    "contract_substitution": "contract substitution",
}

_CATEGORY_NAME_KEYWORDS = {
    "employment_agency_misconduct": ("agency", "recruitment", "manpower", "services"),
    "medical_clinic_fee_abuse": ("clinic", "hospital", "laboratory", "medical"),
    "money_lender_debt_pressure": ("lending", "loans", "finance", "credit", "collection"),
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
    "agency_record": "Agency paperwork reviewed",
    "chat_transcript": "Recruitment conversation captured",
    "employment_contract": "Contract terms recorded",
    "government_letter": "Government or enforcement letter reviewed",
    "identity_document": "Identity document referenced",
    "job_posting": "Recruitment offer documented",
    "legal_intake_form": "Legal intake questions reviewed",
    "loan_agreement": "Loan or debt instrument reviewed",
    "medical_record": "Medical fee document reviewed",
    "payment_receipt": "Payment demand recorded",
    "recruitment_document": "Recruitment paperwork reviewed",
    "worker_statement": "Worker interview recorded",
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


def _case_category_laws(corridor: str, case_categories: list[str]) -> list[str]:
    laws: list[str] = []
    normalized = _normalize_corridor(corridor)
    corridor_codes = normalized.split("_") if normalized else []

    if "employment_agency_misconduct" in case_categories:
        laws.append("POEA Rules and Regulations on Recruitment")
    if "medical_clinic_fee_abuse" in case_categories:
        laws.append("ILO C181 Art. 7")
    if "money_lender_debt_pressure" in case_categories and "HK" in corridor_codes:
        laws.append("Money Lenders Ordinance (Cap. 163)")

    return laws


def _aggregate_legal_refs(
    document_analyses: list[CaseDocumentFinding],
    tool_results: list[dict[str, object]],
    retrieved_context: str,
    corridor: str,
    case_categories: list[str],
) -> list[str]:
    refs: list[str] = []
    for document in document_analyses:
        refs.extend(document.legal_refs)
    refs.extend(_legal_refs_from_context(retrieved_context))
    refs.extend(_case_category_laws(corridor, case_categories))

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
    case_categories: list[str],
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
    if case_categories:
        category_labels = [_CASE_CATEGORY_LABELS.get(category, category.replace("_", " ")) for category in case_categories[:4]]
        parts.append(f"Case themes include {', '.join(category_labels)}.")
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
    case_categories: list[str],
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
    if "employment_agency_misconduct" in case_categories:
        actions.append("Verify the recruitment agency license and preserve all receipts, chat messages, and deduction schedules tied to deployment.")
    if "medical_clinic_fee_abuse" in case_categories:
        actions.append("Request an itemized clinic invoice and determine whether medical screening costs should have been paid by the employer or recruiter.")
    if "money_lender_debt_pressure" in case_categories:
        actions.append("Preserve the loan note and collection messages, and review whether the interest, deductions, or collection method breaches lending or anti-trafficking rules.")
    if "passport_retention" in indicators:
        actions.append("Escalate any passport or identity-document retention language immediately; do not surrender original documents without legal review.")
    if risk_level == "HIGH":
        actions.append("Move the case into urgent NGO or legal triage and preserve the complaint-ready timeline below.")
    if hotlines:
        actions.append(f"Escalate with a hotline or support office such as {hotlines[0].name}.")
    return _dedupe(actions)


def _risk_reasons(
    *,
    case_categories: list[str],
    document_analyses: list[CaseDocumentFinding],
    indicators: list[str],
    tool_results: list[dict[str, object]],
) -> list[str]:
    reasons: list[str] = []
    high_risk_count = sum(1 for document in document_analyses if document.risk_level == "HIGH")
    if high_risk_count:
        reasons.append(f"{high_risk_count} uploaded document(s) were individually classified high risk.")

    indicator_reason_map = {
        "worker_paid_placement_fee": "The bundle contains worker-paid recruitment or placement fees.",
        "salary_deduction_scheme": "The bundle shows salary deductions tied to recruitment or debt repayment.",
        "passport_retention": "The bundle includes passport or identity-document retention language.",
        "debt_bondage_risk": "The bundle reflects debt or advance structures that could trap the worker.",
        "contract_substitution": "The bundle suggests the final contract differs from the original promise.",
        "wage_withholding": "The bundle references withheld or delayed wages.",
        "coercion_or_penalty": "The bundle contains coercive or penalty language that restricts worker choice.",
    }
    category_reason_map = {
        "employment_agency_misconduct": "The bundle points to agency-side misconduct or broker involvement in the recruitment flow.",
        "medical_clinic_fee_abuse": "The bundle routes migration-related costs through a clinic or medical provider.",
        "money_lender_debt_pressure": "The bundle ties migration or deployment to a loan, lender, or collection pressure.",
    }
    for category in case_categories:
        reason = category_reason_map.get(category)
        if reason:
            reasons.append(reason)
    for indicator in indicators:
        reason = indicator_reason_map.get(indicator)
        if reason:
            reasons.append(reason)

    for tool_call in tool_results:
        if tool_call.get("tool") != "score_exploitation_risk":
            continue
        result = tool_call.get("result", {})
        if not isinstance(result, dict):
            continue
        matched_keywords = result.get("matched_keywords")
        if isinstance(matched_keywords, list) and matched_keywords:
            reasons.append(
                "Risk scoring matched exploitation keywords such as "
                + ", ".join(str(item) for item in matched_keywords[:4])
                + "."
            )
        break

    return _dedupe(reasons)


def _indicator_counts(document_analyses: list[CaseDocumentFinding]) -> dict[str, int]:
    counter = Counter()
    for document in document_analyses:
        counter.update(document.indicator_flags)
    return dict(counter.most_common())


def _document_type_counts(document_analyses: list[CaseDocumentFinding]) -> dict[str, int]:
    counter = Counter(document.document_type for document in document_analyses)
    return dict(counter.most_common())


def _risk_distribution(document_analyses: list[CaseDocumentFinding]) -> dict[str, int]:
    counter = Counter(document.risk_level for document in document_analyses)
    ordered_levels = ("HIGH", "MEDIUM", "LOW")
    return {level: counter[level] for level in ordered_levels if counter[level]}


def _aggregate_extracted_entities(document_analyses: list[CaseDocumentFinding]) -> dict[str, list[str]]:
    fields = {
        "amounts": [],
        "business_entities": [],
        "countries": [],
        "dates": [],
        "organisations": [],
        "corridor_candidates": [],
    }
    for document in document_analyses:
        for field_name in fields:
            raw_values = document.extracted_fields.get(field_name, [])
            if isinstance(raw_values, list):
                fields[field_name].extend(str(value) for value in raw_values)
    return {name: _dedupe(values)[:25] for name, values in fields.items() if values}


def _case_categories(
    document_analyses: list[CaseDocumentFinding],
    indicators: list[str],
) -> list[str]:
    categories: list[str] = []
    for document in document_analyses:
        raw_hints = document.extracted_fields.get("scenario_hints", [])
        if isinstance(raw_hints, list):
            categories.extend(str(value) for value in raw_hints)

    if any(flag in indicators for flag in {"worker_paid_placement_fee", "salary_deduction_scheme"}):
        categories.append("worker_fee_overcharge")
    if "passport_retention" in indicators:
        categories.append("document_retention")
    if "contract_substitution" in indicators:
        categories.append("contract_substitution")

    deduped = _dedupe(categories)
    return sorted(deduped, key=lambda category: (_CASE_CATEGORY_ORDER.get(category, 99), category))


def _category_target_names(
    document_analyses: list[CaseDocumentFinding],
    category: str,
) -> list[str]:
    keywords = _CATEGORY_NAME_KEYWORDS.get(category, ())
    if not keywords:
        return []

    names: list[str] = []
    for document in document_analyses:
        raw_values = document.extracted_fields.get("business_entities", [])
        if not isinstance(raw_values, list):
            continue
        for value in raw_values:
            text = str(value).strip()
            lowered = text.lower()
            if text and any(keyword in lowered for keyword in keywords):
                names.append(text)
    return _dedupe(names)


def _target_label(names: list[str], fallback: str) -> str:
    if not names:
        return fallback
    if len(names) == 1:
        return names[0]
    return f"{names[0]} and {names[1]}"


def _follow_up_items(
    *,
    case_categories: list[str],
    document_analyses: list[CaseDocumentFinding],
    indicators: list[str],
    extracted_entities: dict[str, list[str]],
) -> list[str]:
    document_types = {document.document_type for document in document_analyses}
    items: list[str] = []

    if "worker_statement" not in document_types:
        items.append("Collect or transcribe a worker interview narrative that states who recruited the worker, what was promised, and what happened after travel or attempted deployment.")
    if "employment_agency_misconduct" in case_categories and not document_types.intersection({"agency_record", "agency_certificate"}):
        items.append("Capture the recruiter or agency identity, license number, and any official letterhead or registration records tied to the case.")
    if "worker_fee_overcharge" in case_categories and "payment_receipt" not in document_types:
        items.append("Obtain receipts, ledgers, bank transfers, or payroll slips that show every worker-paid fee or salary deduction.")
    if "medical_clinic_fee_abuse" in case_categories and "medical_record" not in document_types:
        items.append("Attach the clinic invoice, referral note, or repeat-test paperwork so the medical-fee chain is documented.")
    if "money_lender_debt_pressure" in case_categories and "loan_agreement" not in document_types:
        items.append("Preserve the promissory note, collection messages, and any payroll-deduction records tied to the lender.")
    if "passport_retention" in indicators and "identity_document" not in document_types:
        items.append("Record where the passport or ID is currently held and attach a copy or image of the document if it is safe to do so.")
    if not extracted_entities.get("dates"):
        items.append("Pin down the key dates: first recruiter contact, payment, contract signing, travel, and any police or regulator filing.")
    if not extracted_entities.get("business_entities"):
        items.append("Confirm the names of the agency, employer, clinic, lender, or other business actors appearing in the file.")
    if "government_letter" not in document_types:
        items.append("If the case has already reached police, embassy, or labor-office review, attach that correspondence so deadlines and requested evidence are preserved.")

    return _dedupe(items)


def _complaint_templates(
    *,
    case_id: str,
    case_categories: list[str],
    corridor: str,
    document_analyses: list[CaseDocumentFinding],
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
    category_lines = "\n".join(
        f"- {_CASE_CATEGORY_LABELS.get(category, category.replace('_', ' '))}"
        for category in case_categories
    )
    extracted_entities = _aggregate_extracted_entities(document_analyses)
    follow_up_items = _follow_up_items(
        case_categories=case_categories,
        document_analyses=document_analyses,
        indicators=[
            flag
            for document in document_analyses
            for flag in document.indicator_flags
        ],
        extracted_entities=extracted_entities,
    )
    actor_values = extracted_entities.get("business_entities") or extracted_entities.get("organisations") or []
    amount_values = extracted_entities.get("amounts", [])
    date_values = extracted_entities.get("dates", [])
    exhibit_lines = "\n".join(
        f"- {document.title or document.document_id} ({document.document_type}; risk {document.risk_level.lower()})"
        for document in document_analyses
    )
    actor_line = ", ".join(actor_values[:4]) if actor_values else "Need confirmation from the file or interviewer"
    amount_line = ", ".join(amount_values[:6]) if amount_values else "Amounts still need confirmation from receipts, ledgers, or payroll records"
    date_line = ", ".join(date_values[:6]) if date_values else "Dates still need confirmation from the documents or interviewer"
    follow_up_lines = "\n".join(f"- {item}" for item in follow_up_items)

    drafts = [
        ComplaintDraft(
            name="ngo_intake_summary",
            audience="NGO case worker",
            text=(
                f"Case ID: {case_id}\n"
                f"Corridor: {corridor_label}\n\n"
                f"Executive summary:\n{executive_summary}\n\n"
                + (f"Case categories:\n{category_lines}\n\n" if category_lines else "")
                + f"Narrative:\n{narrative}\n\n"
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
                + (f"Case categories:\n{category_lines}\n\n" if category_lines else "")
                + f"Documented timeline:\n{timeline_lines}\n\n"
                "Requested next step:\n"
                "- Review the recruitment fee, salary deduction, and document-control evidence attached to this complaint.\n"
                "- Confirm whether the agency, clinic, lender, or employer named in the records is compliant with the listed laws and conventions."
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
        ComplaintDraft(
            name="written_interrogatory_prep",
            audience="NGO legal intake or written interrogatory drafter",
            text=(
                f"Case reference: {case_id}\n"
                f"Corridor: {corridor_label}\n\n"
                "Use this packet to answer written interrogatories, intake questionnaires, or affidavit-prep templates without re-reading the full bundle.\n\n"
                "Answer-ready facts:\n"
                + (f"Case categories:\n{category_lines}\n" if category_lines else "")
                + f"- Known actors: {actor_line}\n"
                f"- Known amounts: {amount_line}\n"
                f"- Known dates: {date_line}\n"
                "\n"
                "Suggested answer blocks:\n"
                "1. Recruitment pathway and who was involved\n"
                f"{narrative}\n\n"
                "2. Payments, deductions, and debt\n"
                f"Amounts documented in the file: {amount_line}.\n\n"
                "3. Document control, threats, or movement restrictions\n"
                f"Risk indicators reflected in the timeline:\n{timeline_lines}\n\n"
                "4. Laws and legal grounding to cite\n"
                f"{law_lines}\n\n"
                "5. Exhibits to cite when answering\n"
                f"{exhibit_lines}\n\n"
                "6. Follow-up questions or missing evidence\n"
                f"{follow_up_lines}"
            ),
        ),
    ]

    if "employment_agency_misconduct" in case_categories:
        target = _target_label(
            _category_target_names(document_analyses, "employment_agency_misconduct"),
            "the recruitment agency",
        )
        drafts.append(
            ComplaintDraft(
                name="employment_agency_complaint",
                audience="Recruitment regulator or labor ministry",
                text=(
                    f"Subject: Complaint regarding {target} and migration-related recruitment misconduct\n\n"
                    f"Case reference: {case_id}\n"
                    f"Corridor: {corridor_label}\n\n"
                    "Requested review:\n"
                    f"- Assess whether {target} collected or arranged unlawful fees from the worker.\n"
                    f"- Review any passport handling, deduction schedules, or coercive deployment messages linked to {target}.\n"
                    "- Confirm license or registration status and preserve the attached evidence.\n\n"
                    f"Supporting timeline:\n{timeline_lines}"
                ),
            )
        )

    if "worker_fee_overcharge" in case_categories:
        drafts.append(
            ComplaintDraft(
                name="fee_overcharge_recovery_request",
                audience="Agency, employer, or compliance officer",
                text=(
                    f"Case reference: {case_id}\n"
                    f"Corridor: {corridor_label}\n\n"
                    "Request:\n"
                    "- Provide a full accounting of every worker-paid fee, deduction, and service charge in this file.\n"
                    "- Identify which charges were authorized by law and which party should legally bear them.\n"
                    "- Suspend any further deductions or collections until the review is complete.\n\n"
                    f"Supporting evidence:\n{timeline_lines}"
                ),
            )
        )

    if "medical_clinic_fee_abuse" in case_categories:
        target = _target_label(
            _category_target_names(document_analyses, "medical_clinic_fee_abuse"),
            "the clinic or medical provider",
        )
        drafts.append(
            ComplaintDraft(
                name="medical_clinic_fee_complaint",
                audience="Clinic management or health regulator",
                text=(
                    f"Subject: Request for review of migration-related charges imposed by {target}\n\n"
                    f"Case reference: {case_id}\n"
                    f"Corridor: {corridor_label}\n\n"
                    "Requested review:\n"
                    f"- Provide an itemized explanation for every exam, repeat test, and certificate fee charged by {target}.\n"
                    "- Explain whether the clinic coordinated with an agency or recruiter to condition deployment on payment.\n"
                    "- Preserve billing, referral, and release records tied to the attached case bundle.\n\n"
                    f"Supporting timeline:\n{timeline_lines}"
                ),
            )
        )

    if "money_lender_debt_pressure" in case_categories:
        target = _target_label(
            _category_target_names(document_analyses, "money_lender_debt_pressure"),
            "the lender or debt collector",
        )
        drafts.append(
            ComplaintDraft(
                name="money_lender_debt_complaint",
                audience="Financial regulator or consumer protection office",
                text=(
                    f"Subject: Complaint regarding migration-linked debt collection by {target}\n\n"
                    f"Case reference: {case_id}\n"
                    f"Corridor: {corridor_label}\n\n"
                    "Requested review:\n"
                    f"- Review the interest, repayment structure, and payroll-linked collection activity associated with {target}.\n"
                    "- Determine whether the debt arrangement contributes to debt bondage, unlawful deductions, or coercive control over the worker.\n"
                    "- Preserve the promissory note, deduction schedule, and collection messages included with this complaint.\n\n"
                    f"Supporting timeline:\n{timeline_lines}"
                ),
            )
        )

    return drafts


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
        case_categories = _case_categories(document_analyses, detected_indicators)
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
        applicable_laws = _aggregate_legal_refs(
            document_analyses,
            tool_results,
            retrieved_context,
            resolved_corridor,
            case_categories,
        )
        risk_level = _overall_risk_level(document_analyses, tool_results, detected_indicators)
        risk_reasons = _risk_reasons(
            case_categories=case_categories,
            document_analyses=document_analyses,
            indicators=detected_indicators,
            tool_results=tool_results,
        )
        indicator_counts = _indicator_counts(document_analyses)
        document_type_counts = _document_type_counts(document_analyses)
        risk_distribution = _risk_distribution(document_analyses)
        extracted_entities = _aggregate_extracted_entities(document_analyses)
        executive_summary = _executive_summary(
            corridor=resolved_corridor,
            risk_level=risk_level,
            case_categories=case_categories,
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
            case_categories=case_categories,
            indicators=detected_indicators,
            risk_level=risk_level,
            hotlines=hotlines,
        )
        complaint_templates = []
        if request.include_complaint_templates:
            complaint_templates = _complaint_templates(
                case_id=request.case_id or "case-demo-001",
                case_categories=case_categories,
                corridor=resolved_corridor,
                document_analyses=document_analyses,
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
            case_categories=case_categories,
            risk_reasons=risk_reasons,
            detected_indicators=detected_indicators,
            indicator_counts=indicator_counts,
            document_type_counts=document_type_counts,
            risk_distribution=risk_distribution,
            extracted_entities=extracted_entities,
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