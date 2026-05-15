"""Knowledge Extraction handler.

Owns POST /api/knowledge/draft-envelope: Gemma 4-assisted drafting
of a typed KnowledgeObject envelope from a raw text passage.

Compat: accepts target_leaf as an alias for target_type because the
2026-05-12 Knowledge Extraction UI sends that field name.
"""
from __future__ import annotations

import hashlib
import json as _json
import re as _re
from datetime import datetime as _dt
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ..._model_output import sanitize_model_output
from .prompts import build_system_prompt


_PII_PATTERNS = [
    (_re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "<EMAIL>"),
    (_re.compile(r"\+?\d[\d\s().-]{7,}\d"), "<PHONE>"),
    (_re.compile(r"\bA\d{7,9}\b"), "<PASSPORT>"),
]
_MONEY_RE = _re.compile(
    r"\b(?P<currency>PHP|HKD|USD|SGD)\s*(?P<amount>[\d,]+(?:\.\d+)?)"
    r"|\b(?P<amount2>[\d,]+(?:\.\d+)?)\s*(?P<currency2>PHP|HKD|USD|SGD)\b",
    _re.I,
)
_ENTITY_RE = _re.compile(
    r"\b(?:agency|recruiter|broker|employer|training center|company|"
    r"payment recipient|money lender)\s*[:=]\s*([A-Z][A-Za-z0-9 &'.,-]{2,80})",
    _re.I,
)


def _light_anonymize(text: str) -> tuple[str, list[str]]:
    """Strip the most obvious PII before sending text to Gemma."""
    redacted = text
    used: list[str] = []
    for pattern, placeholder in _PII_PATTERNS:
        if pattern.search(redacted):
            redacted = pattern.sub(placeholder, redacted)
            used.append(placeholder)
    return redacted, used


def _infer_target_types(text: str) -> list[str]:
    low = (text or "").lower()
    picks: list[str] = []
    if any(t in low for t in (
        "article", "section", "convention", "ordinance", "act ",
        "memorandum circular", "regulation", "protocol", "ilo", "poea",
    )):
        picks.append("rag_doc")
    if any(t in low for t in (
        "fee", "salary deduction", "passport", "loan", "debt",
        "placement", "medical", "training", "threat", "retaliation",
    )):
        picks.append("extracted_fact")
        picks.append("entity_signal")
        picks.append("modus_operandi")
        picks.append("grep_rule")
        picks.append("fact_template")
    if any(t in low for t in (
        "hotline", "phone", "email", "ngo", "department", "embassy",
        "consulate", "mission", "labour", "labor",
    )):
        picks.append("ngo_directory")
    if any(t in low for t in (
        "should score", "rubric", "grade", "evaluation", "judge",
        "dimension",
    )):
        picks.append("rubric_dimension")
    if not picks:
        picks.extend(["context_snippet", "fact_template"])
    picks.append("context_snippet")
    return list(dict.fromkeys(picks))[:6]


def _slug(text: str, fallback: str = "draft") -> str:
    return _re.sub(r"[^a-z0-9]+", "-", (text or "").lower())[:40].strip("-") or fallback


def _money_mentions(text: str) -> list[dict[str, Any]]:
    mentions: list[dict[str, Any]] = []
    for match in _MONEY_RE.finditer(text or ""):
        currency = (match.group("currency") or match.group("currency2") or "").upper()
        raw_amount = match.group("amount") or match.group("amount2") or ""
        amount = raw_amount.replace(",", "")
        try:
            numeric = float(amount)
        except Exception:
            numeric = None
        mentions.append({
            "currency": currency,
            "amount": numeric,
            "raw": match.group(0),
        })
    return mentions[:10]


def _entity_mentions(text: str) -> list[str]:
    entities = []
    for match in _ENTITY_RE.finditer(text or ""):
        ent = " ".join(match.group(1).strip(" .").split())
        if ent and ent not in entities:
            entities.append(ent)
    return entities[:10]


def _corridors(text: str) -> list[str]:
    low = (text or "").lower()
    out: list[str] = []
    if "ph-hk" in low or ("philipp" in low and "hong kong" in low):
        out.append("PH-HK")
    if "indonesia" in low and "hong kong" in low:
        out.append("ID-HK")
    return out


def _indicators(text: str) -> list[str]:
    low = (text or "").lower()
    checks = [
        ("fee_camouflage", ("fee", "processing", "medical", "training")),
        ("salary_deduction", ("salary deduction", "deducted from salary")),
        ("debt_bondage", ("loan", "debt", "repay", "payment plan")),
        ("passport_retention", ("passport", "safekeeping", "retain")),
        ("retaliation_risk", ("retaliation", "terminate", "blacklist", "threat")),
        ("jurisdiction_shopping", ("assign", "assignment", "novation", "cross-border")),
    ]
    found: list[str] = []
    for label, needles in checks:
        if any(n in low for n in needles):
            found.append(label)
    return found


def _deterministic_content(target_type: str, text: str) -> dict[str, Any]:
    low = text.lower()
    title = " ".join(text.split())[:90] or "Draft knowledge"
    money = _money_mentions(text)
    entities = _entity_mentions(text)
    corridors = _corridors(text)
    indicators = _indicators(text)
    if target_type == "grep_rule":
        category = "fee_bondage" if any(x in low for x in ("fee", "deduction", "loan", "debt")) else "case_signal"
        pattern = r"\b(training|medical|processing|placement)\s+fee\b|\bsalary\s+deduction\b"
        if "passport" in low:
            category = "document_control"
            pattern = r"\b(hold|keep|retain|custody|safekeep)\b.{0,80}\b(passport|identity document|id)\b"
        return {
            "category": category,
            "severity": "high" if category in {"fee_bondage", "document_control"} else "medium",
            "pattern": pattern,
            "description": title,
            "test_phrases": [text[:160]],
            "false_positive_notes": "Review against legal context and corridor before automatic escalation.",
        }
    if target_type == "rag_doc":
        return {
            "title": title,
            "jurisdiction": "unknown",
            "source_url": "",
            "text": text,
        }
    if target_type == "context_snippet":
        return {
            "applies_to_corridors": corridors,
            "applies_to_indicators": indicators,
            "text": text,
            "response_guidance": (
                "Use this snippet to recognize the pattern, cite relevant "
                "corridor law, and avoid operational advice that enables abuse."
            ),
            "citation_ids": [],
        }
    if target_type == "rubric_dimension":
        return {
            "label": title[:60],
            "question": "Does the response correctly address this knowledge requirement without unsupported claims?",
            "scale": "0-10",
            "weight": 1.0,
        }
    if target_type == "ngo_directory":
        return {
            "name": title[:80],
            "jurisdiction": "unknown",
            "phone": "",
            "email": "",
            "url": "",
            "verification_note": "Drafted from source text; verify current contact details before use.",
        }
    if target_type == "fact_template":
        return {
            "label": title[:70],
            "applies_to_indicators": indicators or ["case_signal"],
            "fields": [
                {"name": "case_id", "type": "string", "required": False},
                {"name": "corridor", "type": "string", "required": bool(corridors)},
                {"name": "entity_name", "type": "string", "required": False},
                {"name": "amount", "type": "money", "required": bool(money)},
                {"name": "indicator", "type": "string", "required": bool(indicators)},
                {"name": "source_row_id", "type": "string", "required": True},
                {"name": "evidence_quote", "type": "string", "required": True},
            ],
            "source_excerpt": text[:500],
        }
    if target_type == "extracted_fact":
        first_money = money[0] if money else {}
        return {
            "fact_type": "fee_or_debt_signal" if money else "case_signal",
            "corridor": corridors[0] if corridors else "",
            "amount": first_money.get("amount"),
            "currency": first_money.get("currency"),
            "entity_names": entities,
            "locations": ["Hong Kong"] if "hong kong" in low else [],
            "indicators": indicators,
            "journey_stage": "payment_and_debt" if money else "recruitment",
            "evidence_quote": text[:500],
            "confidence_0_10": 7,
            "share_scope": "non_pii_fact_needs_review",
            "aggregation_keys": {
                "corridors": corridors,
                "indicators": indicators,
                "entities": entities,
                "currencies": sorted({m.get("currency") for m in money if m.get("currency")}),
            },
        }
    if target_type == "entity_signal":
        return {
            "entity_name": entities[0] if entities else "",
            "entity_type": "agency" if "agency" in low else "unknown",
            "corridor": corridors[0] if corridors else "",
            "signal_types": indicators,
            "evidence_quote": text[:500],
            "source_context": "drafted_from_local_source_text",
            "confidence_0_10": 6 if entities else 4,
            "pii_status": "organization_or_unknown_entity_not_worker_pii",
            "aggregation_keys": {
                "entity_names": entities,
                "corridors": corridors,
                "signals": indicators,
            },
        }
    if target_type == "modus_operandi":
        return {
            "pattern_name": "Worker-paid processing loan with post-arrival salary deductions",
            "short_description": title,
            "stages": ["recruitment", "payment_and_debt", "arrival_and_placement"],
            "indicators": indicators,
            "generalized_pattern": (
                "A worker is told a recruitment, training, medical, or processing "
                "cost is a loan or payment plan, then repayment is collected after "
                "arrival through salary deduction or pressure from an agency, "
                "employer, broker, or collection entity."
            ),
            "non_pii_example": text[:300],
            "applicable_corridors": corridors,
            "chart_dimensions": ["corridor", "indicator", "entity_name", "currency", "journey_stage"],
            "related_fact_types": ["extracted_fact", "entity_signal"],
        }
    return {"text": text}


def _normalize_content(
    target_type: str,
    parsed: dict[str, Any],
    deterministic: dict[str, Any],
) -> dict[str, Any]:
    """Keep Gemma drafts useful and schema-shaped for downstream charts."""
    content: Any = parsed
    if isinstance(content, dict) and set(content.keys()) == {"content"}:
        content = content.get("content")
    if target_type in {"context_snippet", "rag_doc"} and isinstance(content, str):
        merged = dict(deterministic)
        merged["text"] = content
        return merged
    if not isinstance(content, dict):
        merged = dict(deterministic)
        merged["text"] = str(content)
        return merged
    if target_type == "fact_template" and not isinstance(content.get("fields"), list):
        merged = dict(deterministic)
        merged["example_fact"] = content
        return merged
    merged = dict(deterministic)
    merged.update(content)
    return merged


def register_routes(app: Any) -> None:
    """Attach the extraction routes to a FastAPI app."""

    @app.post("/api/knowledge/draft-envelope")
    async def api_knowledge_draft_envelope(request: Request) -> Any:
        """Gemma-assisted: raw text + target leaf -> draft envelope."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        raw_text = (body.get("raw_text") or "").strip()
        requested_type = body.get("target_type") or body.get("target_leaf") or "auto"
        anonymize = bool(body.get("anonymize", False))

        from ...app import KO_TYPES, KO_BRANCHES

        if not raw_text:
            raise HTTPException(400, "raw_text is required")
        target_types = (
            _infer_target_types(raw_text)
            if requested_type in {"auto", "suggest", "infer", ""}
            else [requested_type]
        )
        unknown = [t for t in target_types if t not in KO_TYPES]
        if unknown:
            raise HTTPException(400, f"unknown target_type: {unknown[0]}")

        text_to_send = raw_text
        placeholders_used: list[str] = []
        if anonymize:
            text_to_send, placeholders_used = _light_anonymize(raw_text)

        # Layer composition: GREP + RAG scan of the raw text so Gemma
        # gets enriched context. Wired layers run; missing ones are
        # skipped silently per the compose_layers contract.
        from .._layers import compose_layers
        layer_out = compose_layers(
            app, raw_text, layers=("grep", "rag"),
        )
        gc = getattr(app.state, "gemma_call", None)

        ts = _dt.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        slug_base = _slug(raw_text)
        envelopes: list[dict[str, Any]] = []
        for target_type in target_types:
            deterministic_content = _deterministic_content(target_type, text_to_send)
            envelope: dict[str, Any] = {
                "schema_version": "1.0",
                "knowledge_object_type": target_type,
                "id": f"{slug_base}-{target_type}-draft",
                "version": "v1-draft",
                "provenance": {
                    "created_at": ts,
                    "created_by": "kernel-01:draft-envelope",
                    "source_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16],
                },
                "content": deterministic_content,
                "tags": [f"branch:{KO_BRANCHES.get(target_type, 'unknown')}"],
                "extensions": {
                    "draft": True,
                    "needs_review": True,
                    "auto_suggested": requested_type in {"auto", "suggest", "infer", ""},
                    "anonymized_before_gemma": anonymize,
                    "placeholders_used": placeholders_used,
                    "applied_layers": layer_out["trace"],
                },
            }
            if gc is None:
                envelope["extensions"]["fallback"] = "no model loaded; deterministic draft"
                envelopes.append(envelope)
                continue
            try:
                sys_prompt = build_system_prompt(target_type)
                msgs = [
                    {"role": "system", "content": [{"type": "text", "text": sys_prompt}]},
                    {"role": "user", "content": [{"type": "text", "text":
                        "Raw fact:\n" + text_to_send
                        + ("\n\nGrounding from existing knowledge:\n" + layer_out["grounding"]
                           if layer_out["grounding"] else "")
                    }]},
                ]
                model_out = gc(msgs, max_new_tokens=512, temperature=0.2)
                response_text = model_out if isinstance(model_out, str) else (
                    (model_out or {}).get("text") or (model_out or {}).get("response") or ""
                )
                response_text = sanitize_model_output(response_text)
                match = _re.search(r"\{[\s\S]*\}", response_text or "")
                if match:
                    try:
                        content = _json.loads(match.group(0))
                        if isinstance(content, dict):
                            envelope["content"] = _normalize_content(
                                target_type,
                                content,
                                deterministic_content,
                            )
                            envelope["extensions"]["gemma_drafted"] = True
                    except Exception:
                        envelope["extensions"]["gemma_parse_failed"] = True
                else:
                    envelope["extensions"]["gemma_parse_failed"] = True
                    envelope["extensions"]["gemma_text_preview"] = response_text[:500]
            except Exception as e:
                envelope["extensions"]["gemma_error"] = str(e)[:200]
            envelopes.append(envelope)
        try:
            from .._training_log import log_interaction as _log
            _log(
                "extraction",
                input_payload={"raw_text": raw_text, "target_type": requested_type},
                output_payload={"suggestions": envelopes},
                applied_layers=layer_out["trace"],
                trace={
                    "n_suggestions": len(envelopes),
                    "suggested_types": [e.get("knowledge_object_type") for e in envelopes],
                },
                anonymize=not anonymize,
            )
        except Exception:
            pass
        return JSONResponse({
            "envelope": envelopes[0],
            "suggestions": envelopes,
            "auto_suggested": requested_type in {"auto", "suggest", "infer", ""},
            "suggested_types": [e.get("knowledge_object_type") for e in envelopes],
        })
