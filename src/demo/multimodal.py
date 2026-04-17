"""Gemma 4 Multimodal Document Analysis for DueCare.

Workers photograph suspicious contracts, job postings, or chat
messages. Gemma 4's multimodal understanding analyzes the image
and identifies exploitation indicators.

This is the second Technical Depth differentiator. The hackathon
explicitly calls out "multimodal understanding" as a unique Gemma 4
feature that should be load-bearing.

Use cases:
  1. Contract photo → identify illegal fee clauses
  2. Job posting screenshot → detect exploitation red flags
  3. Chat message screenshot → analyze for coercion patterns
  4. Recruitment agency document → verify compliance

Usage:
    from src.demo.multimodal import DocumentAnalyzer

    analyzer = DocumentAnalyzer(model=my_gemma_model)
    result = analyzer.analyze_image(image_bytes, context="contract")
"""

from __future__ import annotations

import re
from typing import Any


DOCUMENT_ANALYSIS_PROMPT = """You are DueCare, a migrant worker safety analyzer with multimodal capability.

Bad actors deliberately use IMAGES instead of text to evade content filters:
- Screenshots of fee structures (to bypass keyword detection)
- Photos of contracts with exploitative clauses
- QR codes linking to illegal payment portals
- Bank transfer receipts showing illegal deductions
- Fake agency certificates or POEA clearances
- WhatsApp/Viber screenshots of coercive conversations
- Job posting images with manipulated salary figures

YOUR ADVANTAGE: You can read these images. Text-only filters cannot.

Analyze this document image for exploitation indicators. Look for:

1. **Illegal fees**: Any mention of placement fees, recruitment fees, processing fees, training fees charged to the WORKER (not employer). Under ILO C181 Art. 7 and Philippine RA 10022, workers should not pay recruitment fees.

2. **Salary deductions**: Excessive deductions from wages, especially for housing, food, or "services" that reduce pay below minimum wage.

3. **Document retention**: Any clause about surrendering passport, visa, or other identity documents to the employer or agency.

4. **Contract terms**: Look for contract substitution indicators — different terms than what was promised, especially regarding salary, working hours, or job description.

5. **Debt bondage**: Any loan or advance that creates a debt the worker must "work off" before receiving full wages.

6. **Coercion language**: Penalties for leaving, restrictions on movement, threats, or clauses that give the employer excessive control.

For each finding, cite the applicable law (ILO convention, national law, or international standard).

Output a structured analysis:
- RISK LEVEL: HIGH / MEDIUM / LOW
- FINDINGS: numbered list of specific concerns
- LEGAL REFERENCES: applicable laws for each finding
- RECOMMENDATION: what the worker should do
- RESOURCES: who to contact (POEA, POLO, IOM, etc.)"""


CONTEXT_PROMPTS = {
    "contract": "This is a photograph of an employment contract for a migrant worker. Analyze it for exploitation indicators — especially fee clauses, salary deductions, passport retention, and contract substitution.",
    "job_posting": "This is a screenshot of a job posting targeting migrant workers. Analyze it for red flags — unrealistic salary promises, hidden fees, vague job descriptions, and unlicensed agencies.",
    "chat": "This is a screenshot of a chat conversation (WhatsApp, Viber, Messenger) about overseas employment. Analyze it for coercion, urgency pressure, fee demands, or threats. Bad actors often use chat screenshots to evade text filters.",
    "document": "This is a photograph of a document related to migrant worker recruitment. Analyze it for compliance issues and exploitation indicators.",
    "receipt": "This is a photograph of a payment receipt or bank transfer related to recruitment. Check if the fees are legal under applicable jurisdiction (ILO C181: workers should not pay recruitment fees).",
    "qr_code": "This image contains a QR code related to recruitment payment. Flag it as potentially dangerous — QR codes are used to direct workers to unregulated payment channels that bypass legal oversight.",
    "certificate": "This is a photograph of an agency certificate, license, or POEA clearance. Check for signs of forgery — expired dates, incorrect formatting, missing hologram descriptions, or unlisted agency names.",
    "bank_screenshot": "This is a screenshot of a bank transfer or mobile payment. Check the amount against legal fee caps (Philippine RA 10022: zero fees to domestic workers). Any amount charged to the worker for recruitment is illegal.",
}

_AMOUNT_PATTERN = re.compile(
    r"(?:USD|PHP|HKD|SGD|MYR|SAR|AED|EUR|GBP|\$|P)\s?[\d,]+(?:\.\d{1,2})?"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?\s*(?:pesos?|dollars?|USD|PHP|HKD)",
    re.IGNORECASE,
)

_DATE_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b"
    r"|\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b"
    r"|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)

_COUNTRIES = [
    "Philippines",
    "Hong Kong",
    "Saudi Arabia",
    "Singapore",
    "Malaysia",
    "Nepal",
    "Bangladesh",
    "Indonesia",
    "Qatar",
    "Taiwan",
    "United Arab Emirates",
    "UAE",
]

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

_COUNTRY_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(country) for country in sorted(_COUNTRIES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

_ORG_PATTERN = re.compile(
    r"\b(POEA|DMW|DOLE|OWWA|POLO|IOM|ILO|IJM|ECPAT|BP2MI|Polaris\s+Project|Philippine\s+Embassy)\b",
    re.IGNORECASE,
)

_LEGAL_PATTERN = re.compile(
    r"\b(?:ILO\s+C\d+(?:\s+Art\.\s*\d+)?|ILO\s+P\d+|RA\s+\d+|Palermo\s+Protocol|Dhaka\s+Principles)\b",
    re.IGNORECASE,
)

_CORRIDOR_PAIRS = {
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

_DOCUMENT_TYPE_HINTS = {
    "agency_certificate": ["certificate", "licensed", "license no", "registration", "permit"],
    "chat_transcript": ["whatsapp", "viber", "messenger", "chat", "voice note", "pm:"],
    "employment_contract": ["employment contract", "employee", "employer", "salary", "rest day", "contract period"],
    "identity_document": ["passport", "visa", "work permit", "travel document", "nationality"],
    "job_posting": ["apply now", "vacancy", "hiring", "job opening", "benefits"],
    "payment_receipt": ["receipt", "transfer", "deposit", "invoice", "payment", "paid to"],
}

_INDICATOR_RULES = {
    "worker_paid_placement_fee": [
        r"placement fee",
        r"recruitment fee",
        r"processing fee",
        r"training fee",
        r"medical fee",
        r"service charge",
    ],
    "salary_deduction_scheme": [
        r"salary deduction",
        r"deduct(?:ed|ion)?",
        r"installments?",
        r"from wages",
        r"months? of salary",
    ],
    "passport_retention": [
        r"retain (?:the )?passport",
        r"keep your passport",
        r"hold passport",
        r"surrender passport",
        r"confiscat(?:e|ion) (?:your )?(?:passport|documents)",
    ],
    "debt_bondage_risk": [
        r"debt",
        r"loan",
        r"advance",
        r"owe",
        r"interest",
        r"repay",
    ],
    "coercion_or_penalty": [
        r"penalty",
        r"deport",
        r"cannot leave",
        r"not allowed to leave",
        r"blacklist",
        r"punish",
    ],
    "contract_substitution": [
        r"different job",
        r"different salary",
        r"substitut",
        r"not what was promised",
        r"amended after arrival",
    ],
    "document_irregularity": [
        r"expired",
        r"forg(?:e|ed|ery)",
        r"missing seal",
        r"invalid",
        r"not registered",
    ],
    "wage_withholding": [
        r"withhold(?:ing)? wages",
        r"no salary",
        r"didn't pay",
        r"delayed salary",
        r"unpaid wages",
    ],
}

_INDICATOR_LAWS = {
    "coercion_or_penalty": ["Palermo Protocol", "ILO C029"],
    "contract_substitution": ["ILO C181 Art. 8", "ILO C097 Art. 6"],
    "debt_bondage_risk": ["ILO C029", "ILO P029"],
    "document_irregularity": ["Palermo Protocol"],
    "passport_retention": ["Palermo Protocol", "ILO C029"],
    "salary_deduction_scheme": ["ILO C095 Art. 8", "ILO C189 Art. 12"],
    "wage_withholding": ["ILO C095", "ILO C189 Art. 12"],
    "worker_paid_placement_fee": ["ILO C181 Art. 7", "RA 10022"],
}

_CRITICAL_FLAGS = {
    "coercion_or_penalty",
    "debt_bondage_risk",
    "passport_retention",
    "worker_paid_placement_fee",
}

_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


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


def _document_type(text: str, context: str) -> str:
    lowered = text.lower()
    if context in {"contract", "receipt", "chat", "job_posting", "certificate"}:
        return {
            "certificate": "agency_certificate",
            "chat": "chat_transcript",
            "contract": "employment_contract",
            "job_posting": "job_posting",
            "receipt": "payment_receipt",
        }[context]
    for document_type, hints in _DOCUMENT_TYPE_HINTS.items():
        if any(hint in lowered for hint in hints):
            return document_type
    return "recruitment_document"


def _extract_countries(text: str) -> list[str]:
    return _dedupe(match.group(1) for match in _COUNTRY_PATTERN.finditer(text))


def _extract_organisations(text: str) -> list[str]:
    return _dedupe(match.group(1) for match in _ORG_PATTERN.finditer(text))


def _corridor_candidates(countries: list[str]) -> list[str]:
    codes: list[str] = []
    for country in countries:
        code = _COUNTRY_NAME_TO_CODE.get(country.lower())
        if code and code not in codes:
            codes.append(code)

    candidates: list[str] = []
    for index, origin in enumerate(codes):
        for destination in codes[index + 1 :]:
            corridor = _CORRIDOR_PAIRS.get((origin, destination))
            if corridor and corridor not in candidates:
                candidates.append(corridor)
    return candidates


def _indicator_flags(text: str) -> list[str]:
    lowered = text.lower()
    matched: list[str] = []
    for indicator, patterns in _INDICATOR_RULES.items():
        if any(re.search(pattern, lowered) for pattern in patterns):
            matched.append(indicator)
    return matched


def _findings(indicator_flags: list[str], extracted_fields: dict[str, Any], document_type: str) -> list[str]:
    findings: list[str] = []
    amounts = extracted_fields.get("amounts", [])
    if "worker_paid_placement_fee" in indicator_flags:
        amount_text = f" ({', '.join(amounts[:2])})" if amounts else ""
        findings.append(f"Document references worker-paid recruitment or placement fees{amount_text}.")
    if "salary_deduction_scheme" in indicator_flags:
        findings.append("Document describes repayment or deductions taken directly from wages.")
    if "passport_retention" in indicator_flags:
        findings.append("Document includes passport or identity-document retention language.")
    if "debt_bondage_risk" in indicator_flags:
        findings.append("Document creates or acknowledges a debt that could tie the worker to the job.")
    if "contract_substitution" in indicator_flags:
        findings.append("Document language suggests the final terms may differ from the original offer.")
    if "coercion_or_penalty" in indicator_flags:
        findings.append("Document contains penalty or movement-control language that raises coercion concerns.")
    if "wage_withholding" in indicator_flags:
        findings.append("Document references delayed, withheld, or reduced wages.")
    if "document_irregularity" in indicator_flags:
        findings.append("Document shows signs of invalid, expired, or irregular compliance paperwork.")
    if not findings and document_type == "payment_receipt" and amounts:
        findings.append("Receipt records worker-side payment activity that should be checked against zero-fee rules.")
    if not findings:
        findings.append("No explicit exploitation clause was detected, but the document should still be verified against corridor-specific recruitment rules.")
    return findings


def _risk_level(indicator_flags: list[str], quick_filter_score: float) -> str:
    if any(flag in _CRITICAL_FLAGS for flag in indicator_flags) or len(indicator_flags) >= 3 or quick_filter_score >= 0.6:
        return "HIGH"
    if indicator_flags or quick_filter_score >= 0.25:
        return "MEDIUM"
    return "LOW"


def _recommendation(risk_level: str, indicator_flags: list[str]) -> str:
    if risk_level == "HIGH":
        if "passport_retention" in indicator_flags:
            return "Do not surrender original identity documents. Preserve this file and escalate it to a labor office or trusted NGO before signing or traveling."
        return "Pause further payments or contract steps, preserve the document, and escalate it to a labor office or trusted NGO before proceeding."
    if risk_level == "MEDIUM":
        return "Preserve the document, compare it against the original job offer, and verify the terms with a labor office or NGO before continuing."
    return "Keep a copy of the document and verify the issuing agency if additional fees or document-control demands appear later."


def _default_resources(countries: list[str]) -> list[dict[str, str | None]]:
    from .function_calling import execute_tool

    resources: list[dict[str, str | None]] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    country_codes = [_COUNTRY_NAME_TO_CODE[country.lower()] for country in countries if country.lower() in _COUNTRY_NAME_TO_CODE]
    lookup_order = country_codes[:2] or ["INTL"]
    for country_code in lookup_order:
        result = execute_tool("lookup_hotline", {"country": country_code})
        for contact in result.get("contacts", []):
            name = str(contact.get("name", "")).strip()
            number = contact.get("number")
            url = contact.get("url")
            key = (name.lower(), str(number) if number else None, str(url) if url else None)
            if not name or key in seen:
                continue
            seen.add(key)
            resources.append(
                {
                    "name": name,
                    "type": str(contact.get("type", "hotline")),
                    "number": str(number) if number else None,
                    "url": str(url) if url else None,
                    "jurisdiction": country_code,
                }
            )
    return resources


class DocumentAnalysisResult:
    """Structured result from document analysis."""

    def __init__(
        self,
        risk_level: str,
        findings: list[str],
        legal_refs: list[str],
        recommendation: str,
        resources: list[dict[str, str | None]],
        raw_response: str,
        confidence: float = 0.0,
        *,
        document_type: str = "recruitment_document",
        indicator_flags: list[str] | None = None,
        extracted_fields: dict[str, Any] | None = None,
        timeline_markers: list[str] | None = None,
    ) -> None:
        self.risk_level = risk_level
        self.findings = findings
        self.legal_refs = legal_refs
        self.recommendation = recommendation
        self.resources = resources
        self.raw_response = raw_response
        self.confidence = confidence
        self.document_type = document_type
        self.indicator_flags = indicator_flags or []
        self.extracted_fields = extracted_fields or {}
        self.timeline_markers = timeline_markers or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "risk_level": self.risk_level,
            "findings": self.findings,
            "indicator_flags": self.indicator_flags,
            "legal_refs": self.legal_refs,
            "recommendation": self.recommendation,
            "extracted_fields": self.extracted_fields,
            "timeline_markers": self.timeline_markers,
            "resources": self.resources,
            "confidence": self.confidence,
        }


class DocumentAnalyzer:
    """Analyze document images using Gemma 4's multimodal capabilities.

    This component is the multimodal differentiator for the hackathon.
    Workers can photograph contracts in any language and get instant
    exploitation analysis — entirely on-device, no cloud upload.
    """

    def __init__(self, model: Any) -> None:
        self._model = model

    def analyze_image(
        self,
        image_data: bytes,
        *,
        context: str = "document",
        language: str = "en",
    ) -> DocumentAnalysisResult:
        """Analyze a document image for exploitation indicators.

        Args:
            image_data: Raw image bytes (JPEG, PNG)
            context: Type of document (contract, job_posting, chat, receipt)
            language: Preferred response language

        Returns:
            DocumentAnalysisResult with findings, legal refs, resources
        """
        if self._model is None:
            return DocumentAnalysisResult(
                risk_level="MEDIUM",
                findings=["Image analysis requires a multimodal Gemma model or OCR text. Use the text workflow when OCR is already available."],
                legal_refs=["ILO C181 Art. 7", "ILO C029"],
                recommendation="Extract OCR text first, then rerun the document analysis so DueCare can classify the file locally.",
                resources=_default_resources([]),
                raw_response="",
                confidence=0.35,
                document_type="image_only",
            )

        from duecare.core import ChatMessage

        context_prompt = CONTEXT_PROMPTS.get(context, CONTEXT_PROMPTS["document"])

        messages = [
            ChatMessage(role="system", content=DOCUMENT_ANALYSIS_PROMPT),
            ChatMessage(role="user", content=context_prompt),
        ]

        # Pass image via Gemma 4's multimodal interface
        gen_result = self._model.generate(
            messages,
            images=[image_data],
            max_tokens=1024,
            temperature=0.0,
        )

        return self._parse_analysis(gen_result.text)

    def analyze_text_as_document(
        self,
        text: str,
        *,
        context: str = "document",
    ) -> DocumentAnalysisResult:
        """Analyze document text (when OCR is already done or text is available)."""
        heuristic = self._rule_based_analysis(text, context=context)
        if self._model is None:
            return heuristic

        from duecare.core import ChatMessage

        context_prompt = CONTEXT_PROMPTS.get(context, CONTEXT_PROMPTS["document"])

        messages = [
            ChatMessage(role="system", content=DOCUMENT_ANALYSIS_PROMPT),
            ChatMessage(role="user", content=f"{context_prompt}\n\nDocument text:\n{text}"),
        ]

        gen_result = self._model.generate(messages, max_tokens=1024, temperature=0.0)
        parsed = self._parse_analysis(gen_result.text)
        parsed.document_type = heuristic.document_type
        parsed.indicator_flags = heuristic.indicator_flags
        parsed.extracted_fields = heuristic.extracted_fields
        parsed.timeline_markers = heuristic.timeline_markers
        parsed.findings = _dedupe(parsed.findings + heuristic.findings)[:8]
        parsed.legal_refs = _dedupe(parsed.legal_refs + heuristic.legal_refs)
        parsed.resources = heuristic.resources or parsed.resources
        parsed.confidence = max(parsed.confidence, heuristic.confidence)
        if _RISK_ORDER.get(heuristic.risk_level, 0) > _RISK_ORDER.get(parsed.risk_level, 0):
            parsed.risk_level = heuristic.risk_level
            parsed.recommendation = heuristic.recommendation
        return parsed

    def _rule_based_analysis(
        self,
        text: str,
        *,
        context: str = "document",
    ) -> DocumentAnalysisResult:
        """Analyze raw OCR text without depending on a live multimodal model."""
        from .quick_filter import QuickFilter

        document_type = _document_type(text, context)
        countries = _extract_countries(text)
        organisations = _extract_organisations(text)
        amounts = _dedupe(match.group(0).strip() for match in _AMOUNT_PATTERN.finditer(text))
        dates = _dedupe(match.group(0).strip() for match in _DATE_PATTERN.finditer(text))
        indicator_flags = _indicator_flags(text)
        lowered = text.lower()
        if (
            document_type == "employment_contract"
            and amounts
            and "salary_deduction_scheme" in indicator_flags
            and "worker_paid_placement_fee" not in indicator_flags
            and any(token in lowered for token in ["deduct", "months", "salary"])
        ):
            indicator_flags.append("worker_paid_placement_fee")

        quick_filter = QuickFilter().check(text)
        risk_level = _risk_level(indicator_flags, quick_filter.score)
        extracted_fields = {
            "document_type": document_type,
            "amounts": amounts,
            "dates": dates,
            "countries": countries,
            "organisations": organisations,
            "corridor_candidates": _corridor_candidates(countries),
            "quick_filter_score": quick_filter.score,
            "matched_keywords": quick_filter.matched_keywords,
            "matched_patterns": quick_filter.matched_patterns,
            "resources": _default_resources(countries),
        }
        legal_refs = _dedupe(
            [law for indicator in indicator_flags for law in _INDICATOR_LAWS.get(indicator, [])]
            + [match.group(0).strip() for match in _LEGAL_PATTERN.finditer(text)]
        )
        findings = _findings(indicator_flags, extracted_fields, document_type)
        confidence = min(0.95, 0.35 + 0.1 * len(indicator_flags) + 0.04 * len(amounts) + 0.04 * len(dates))

        return DocumentAnalysisResult(
            risk_level=risk_level,
            findings=findings,
            legal_refs=legal_refs or ["ILO C181 Art. 7", "ILO C029"],
            recommendation=_recommendation(risk_level, indicator_flags),
            resources=extracted_fields["resources"],
            raw_response=text,
            confidence=confidence,
            document_type=document_type,
            indicator_flags=indicator_flags,
            extracted_fields=extracted_fields,
            timeline_markers=dates,
        )

    def _parse_analysis(self, raw: str) -> DocumentAnalysisResult:
        """Parse the model's analysis into structured result."""
        raw_lower = raw.lower()

        # Extract risk level
        if "high" in raw_lower[:200]:
            risk = "HIGH"
        elif "medium" in raw_lower[:200]:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        findings = re.findall(r"\d+\.\s*(.+?)(?:\n|$)", raw)
        findings = [f.strip() for f in findings if len(f.strip()) > 10][:10]

        # Extract legal references
        legal_patterns = [
            r"ILO\s+C\d+(?:\s+Art\.\s*\d+)?",
            r"RA\s+\d+",
            r"Palermo\s+Protocol",
            r"Employment\s+Ordinance",
            r"Dhaka\s+Principles",
        ]
        legal_refs = []
        for pattern in legal_patterns:
            legal_refs.extend(re.findall(pattern, raw, re.IGNORECASE))
        legal_refs = list(set(legal_refs))

        # Default resources
        resources = _default_resources([])

        # Confidence based on response quality
        confidence = min(1.0, (len(findings) * 0.15 + len(legal_refs) * 0.1 + 0.3))

        return DocumentAnalysisResult(
            risk_level=risk,
            findings=findings if findings else ["Analysis could not extract specific findings"],
            legal_refs=legal_refs if legal_refs else ["ILO C181 Art. 7", "ILO C029"],
            recommendation=(
                "Contact your local POLO office or call POEA at 1343 before signing."
                if risk == "HIGH"
                else "Review the document carefully with a legal advisor."
            ),
            resources=resources,
            raw_response=raw,
            confidence=confidence,
            document_type="recruitment_document",
        )
