"""Knowledge Extraction handler.

Owns POST /api/knowledge/draft-envelope -- Gemma 4-assisted drafting
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
        target_type = body.get("target_type") or body.get("target_leaf") or "grep_rule"
        anonymize = bool(body.get("anonymize", False))

        from ...app import KO_TYPES, KO_BRANCHES

        if target_type not in KO_TYPES:
            raise HTTPException(400, f"unknown target_type: {target_type}")
        if not raw_text:
            raise HTTPException(400, "raw_text is required")

        text_to_send = raw_text
        placeholders_used: list[str] = []
        if anonymize:
            text_to_send, placeholders_used = _light_anonymize(raw_text)

        ts = _dt.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        slug_base = _re.sub(r"[^a-z0-9]+", "-", raw_text.lower())[:40].strip("-") or "draft"
        envelope: dict[str, Any] = {
            "schema_version": "1.0",
            "knowledge_object_type": target_type,
            "id": f"{slug_base}-draft",
            "version": "v1-draft",
            "provenance": {
                "created_at": ts,
                "created_by": "kernel-01:draft-envelope",
                "source_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16],
            },
            "content": {},
            "tags": [f"branch:{KO_BRANCHES.get(target_type, 'unknown')}"],
            "extensions": {
                "draft": True,
                "needs_review": True,
                "anonymized_before_gemma": anonymize,
                "placeholders_used": placeholders_used,
            },
        }

        # Layer composition: GREP + RAG scan of the raw text so Gemma
        # gets enriched context. Wired layers run; missing ones are
        # skipped silently per the compose_layers contract.
        from .._layers import compose_layers
        layer_out = compose_layers(
            app, raw_text, layers=("grep", "rag"),
        )
        envelope["extensions"]["applied_layers"] = layer_out["trace"]

        gc = getattr(app.state, "gemma_call", None)
        if gc is None:
            envelope["extensions"]["fallback"] = "no model loaded; manual content required"
            return JSONResponse({"envelope": envelope})

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
            match = _re.search(r"\{[\s\S]*\}", response_text or "")
            if match:
                try:
                    content = _json.loads(match.group(0))
                    if isinstance(content, dict):
                        envelope["content"] = content
                        envelope["extensions"]["gemma_drafted"] = True
                except Exception:
                    envelope["extensions"]["gemma_parse_failed"] = True
        except Exception as e:
            envelope["extensions"]["gemma_error"] = str(e)[:200]
        try:
            from .._training_log import log_interaction as _log
            _log(
                "extraction",
                input_payload={"raw_text": raw_text, "target_type": target_type},
                output_payload=envelope,
                applied_layers=envelope.get("extensions", {}).get("applied_layers", {}),
                trace={
                    "gemma_drafted": envelope.get("extensions", {}).get("gemma_drafted", False),
                    "parse_failed": envelope.get("extensions", {}).get("gemma_parse_failed", False),
                },
                anonymize=not anonymize,
            )
        except Exception:
            pass
        return JSONResponse({"envelope": envelope})
