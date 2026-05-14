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
    return list(dict.fromkeys(picks))[:4]


def _slug(text: str, fallback: str = "draft") -> str:
    return _re.sub(r"[^a-z0-9]+", "-", (text or "").lower())[:40].strip("-") or fallback


def _deterministic_content(target_type: str, text: str) -> dict[str, Any]:
    low = text.lower()
    title = " ".join(text.split())[:90] or "Draft knowledge"
    amount_match = _re.search(r"\b(?:PHP|HKD|USD|SGD)\s*[\d,]+|\b[\d,]+\s*(?:PHP|HKD|USD|SGD)\b", text, _re.I)
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
            "applies_to_corridors": ["PH-HK"] if "hong kong" in low or "ph-hk" in low else [],
            "applies_to_indicators": [
                x for x in ("fee_bondage", "passport_retention", "salary_deduction")
                if x.replace("_", " ") in low
            ],
            "text": text,
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
            "applies_to_indicators": ["fee_bondage"] if amount_match else [],
            "fields": [
                {"name": "case_id", "type": "string", "required": False},
                {"name": "person", "type": "string", "required": False},
                {"name": "amount", "type": "money", "required": bool(amount_match)},
                {"name": "source_row_id", "type": "string", "required": True},
                {"name": "evidence_quote", "type": "string", "required": True},
            ],
            "source_excerpt": text[:500],
        }
    return {"text": text}


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
                "content": _deterministic_content(target_type, text_to_send),
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
                            envelope["content"] = content
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
