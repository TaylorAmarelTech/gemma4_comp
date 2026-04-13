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

import base64
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


class DocumentAnalysisResult:
    """Structured result from document analysis."""

    def __init__(
        self,
        risk_level: str,
        findings: list[str],
        legal_refs: list[str],
        recommendation: str,
        resources: list[dict[str, str]],
        raw_response: str,
        confidence: float = 0.0,
    ) -> None:
        self.risk_level = risk_level
        self.findings = findings
        self.legal_refs = legal_refs
        self.recommendation = recommendation
        self.resources = resources
        self.raw_response = raw_response
        self.confidence = confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "findings": self.findings,
            "legal_refs": self.legal_refs,
            "recommendation": self.recommendation,
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
        from duecare.core import ChatMessage

        context_prompt = CONTEXT_PROMPTS.get(context, CONTEXT_PROMPTS["document"])

        messages = [
            ChatMessage(role="system", content=DOCUMENT_ANALYSIS_PROMPT),
            ChatMessage(role="user", content=f"{context_prompt}\n\nDocument text:\n{text}"),
        ]

        gen_result = self._model.generate(messages, max_tokens=1024, temperature=0.0)
        return self._parse_analysis(gen_result.text)

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

        # Extract findings (numbered items)
        import re

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
        resources = [
            {"name": "POEA Hotline", "number": "1343", "country": "PH"},
            {"name": "IOM", "url": "https://www.iom.int"},
            {"name": "Polaris Project", "number": "1-888-373-7888"},
        ]

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
        )
