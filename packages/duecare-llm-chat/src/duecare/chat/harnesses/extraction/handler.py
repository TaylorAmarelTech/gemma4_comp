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
import threading as _threading
from datetime import UTC as _UTC, datetime as _dt
from typing import Any
from uuid import uuid4 as _uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ..._model_output import sanitize_model_output
from .._replay import demo_replay
from .._safe_text import (
    clean_for_knowledge_fact as _clean_for_knowledge_fact,
    fact_excerpt as _fact_excerpt,
    standardize_fact_envelope as _standardize_fact_envelope,
    was_scrubbed as _was_scrubbed,
)
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


# Noise scrubbing (kernel run IDs, /kaggle/working/... paths, ZIP /
# JSONL filenames, synthetic case folder names) is provided by the
# shared `_safe_text` module so every fact / share / search handler
# applies the same contract. See harnesses/_safe_text.py.


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
    # Strip operational noise (kernel run IDs, /kaggle/working/...
    # paths, ZIP filenames, synthetic case folder names) before any
    # excerpt or title is computed. This is the single chokepoint
    # downstream envelopes go through, so cleaning here makes every
    # target_type branch produce reader-facing prose instead of
    # build-log fragments.
    clean = _clean_for_knowledge_fact(text)
    low = clean.lower()
    title = " ".join(clean.split())[:90] or "Draft knowledge"
    money = _money_mentions(clean)
    entities = _entity_mentions(clean)
    corridors = _corridors(clean)
    indicators = _indicators(clean)
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
            "test_phrases": [_fact_excerpt(clean, 160)],
            "false_positive_notes": "Review against legal context and corridor before automatic escalation.",
        }
    if target_type == "rag_doc":
        return {
            "title": title,
            "jurisdiction": "unknown",
            "source_url": "",
            "text": clean,
        }
    if target_type == "context_snippet":
        return {
            "applies_to_corridors": corridors,
            "applies_to_indicators": indicators,
            "text": clean,
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
            "source_excerpt": _fact_excerpt(clean, 500),
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
            "evidence_quote": _fact_excerpt(clean, 500),
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
            "evidence_quote": _fact_excerpt(clean, 500),
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
            "non_pii_example": _fact_excerpt(clean, 300),
            "applicable_corridors": corridors,
            "chart_dimensions": ["corridor", "indicator", "entity_name", "currency", "journey_stage"],
            "related_fact_types": ["extracted_fact", "entity_signal"],
        }
    return {"text": clean}


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


def _build_draft_response(app: Any, body: dict[str, Any]) -> dict[str, Any]:
    raw_text = (body.get("raw_text") or "").strip()
    requested_type = body.get("target_type") or body.get("target_leaf") or "auto"
    anonymize = bool(body.get("anonymize", False))
    use_gemma = bool(body.get("use_gemma", True))

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
    # Scrub operational noise (run IDs, /kaggle/working/... paths, ZIP
    # filenames, synthetic case folder names like
    # DC-PH-HK-101_Ana_Cruz/...). We want the Gemma prompt and the
    # deterministic fallback to both see prose that describes the
    # pattern, never the staging filenames a process bundle was built
    # from. Applied AFTER anonymization so the existing PII placeholders
    # are preserved.
    pre_scrub = text_to_send
    text_to_send = _clean_for_knowledge_fact(text_to_send)
    scrubbed_noise = _was_scrubbed(pre_scrub, text_to_send)

    from .._layers import compose_layers
    layer_out = compose_layers(app, raw_text, layers=("grep", "rag"))
    gc = getattr(app.state, "gemma_call", None) if use_gemma else None

    ts = _dt.now(_UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
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
                "noise_scrubbed_before_gemma": scrubbed_noise,
                "applied_layers": layer_out["trace"],
                "model_call_requested": use_gemma,
                "model_call_available": gc is not None,
            },
        }
        if gc is None:
            envelope["extensions"]["fallback"] = (
                "gemma disabled by caller; deterministic draft"
                if not use_gemma else
                "no model loaded; deterministic draft"
            )
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
            # Shared robust JSON extractor: strips markdown fences,
            # balanced-span scans for the first JSON object, applies
            # trailing-comma / Python-literal / single-quote repairs,
            # and surfaces a diagnostic ``attempts`` log on failure.
            from duecare.chat._model_json import extract_json
            extracted = extract_json(response_text)
            content = extracted.payload if isinstance(extracted.payload, dict) else None
            if content is not None:
                envelope["content"] = _normalize_content(
                    target_type,
                    content,
                    deterministic_content,
                )
                envelope["extensions"]["gemma_drafted"] = True
            else:
                envelope["extensions"]["gemma_parse_failed"] = True
                envelope["extensions"]["gemma_parse_attempts"] = list(extracted.attempts)
                envelope["extensions"]["gemma_text_preview"] = response_text[:500]
        except Exception as e:
            envelope["extensions"]["gemma_error"] = str(e)[:200]
        # Last step before append: standardize the envelope content
        # so every page renders the same field order + indicator
        # vocabulary + corridor format, and so any lingering noise in
        # a Gemma-produced string field gets scrubbed once more.
        # Idempotent — safe if the deterministic path already produced
        # canonical content.
        try:
            envelope["content"] = _standardize_fact_envelope(
                envelope.get("content") or {},
                envelope.get("knowledge_object_type") or "",
            )
            envelope["extensions"]["standardized_shape"] = True
        except Exception as _std_err:  # noqa: BLE001
            envelope["extensions"]["standardize_error"] = str(_std_err)[:200]
        envelopes.append(envelope)
    try:
        from .._training_log import log_interaction as _log
        _log(
            "extraction",
            input_payload={"raw_text": raw_text, "target_type": requested_type, "use_gemma": use_gemma},
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
    replay_endpoint = body.get("_replay_endpoint") or "/api/knowledge/draft-envelope"
    return {
        "envelope": envelopes[0],
        "suggestions": envelopes,
        "auto_suggested": requested_type in {"auto", "suggest", "infer", ""},
        "suggested_types": [e.get("knowledge_object_type") for e in envelopes],
        "model_call_requested": use_gemma,
        "model_call_available": gc is not None,
        "demo_replay": demo_replay(
            lane="knowledge_extraction",
            endpoint=replay_endpoint,
            request={
                "target_leaf": requested_type,
                "anonymize": anonymize,
                "use_gemma": use_gemma,
                "raw_text_chars": len(raw_text),
                "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
            },
            response_summary={
                "n_suggestions": len(envelopes),
                "suggested_types": [e.get("knowledge_object_type") for e in envelopes],
                "model_call_available": gc is not None,
            },
            artifacts=[{
                "name": "suggestions",
                "kind": "inline_response_json",
                "count": len(envelopes),
            }],
            note=(
                "The raw source text is represented by sha256/length here. "
                "Use the browser replay download during a synthetic demo if "
                "you need the exact local request body."
            ),
        ),
    }


# Critique prompt: Gemma reads a draft envelope and lists specific
# issues. We keep it terse and strict-JSON so the rewrite pass has a
# structured input. Built once at import time so the polish endpoint
# doesn't reconstruct it per call.
_POLISH_CRITIQUE_SYSTEM = (
    "You are a senior anti-trafficking reviewer auditing a draft "
    "knowledge fact before it's saved to the local knowledge store. "
    "Read the draft. List specific, fixable problems in JSON. Be "
    "concrete about WHICH FIELD and WHY. Categories you should flag:\n"
    " - vague_phrasing: a field uses hedging language where a concrete "
    "verb/noun would be clearer\n"
    " - missing_ilo_indicator: the fact describes a pattern that "
    "should be tagged with a canonical ILO indicator but isn't\n"
    " - non_pattern_quote: evidence_quote / non_pii_example reads as a "
    "build-log fragment or operational metadata, not as the abstract "
    "pattern the fact teaches\n"
    " - missing_corridor: the text references a corridor but the "
    "corridor field is empty or wrong format\n"
    " - missing_stage: the fact describes a stage but journey_stage "
    "is missing or wrong\n"
    " - unsupported_claim: a claim in the text has no evidence in the "
    "fact's other fields\n"
    " - dangling_money: a numeric amount with no currency or context\n"
    " - personally_identifying: a specific person or org name appears "
    "where a role/category would be more durable\n\n"
    "Output STRICT JSON ONLY (no markdown, no prose):\n"
    "{\"issues\": [{\"category\": <one of above>, \"field\": <str>, "
    "\"why\": <one sentence>, \"suggested_fix\": <one sentence>}], "
    "\"overall\": <one sentence summary>}\n"
    "If the draft is already good, return {\"issues\": [], \"overall\": "
    "\"draft reads as a clean, anonymized pattern\"}."
)

_POLISH_REWRITE_SYSTEM = (
    "You are a senior anti-trafficking reviewer rewriting a draft "
    "knowledge fact based on a critique list. Apply EVERY suggested "
    "fix without inventing new facts. Keep the draft's "
    "knowledge_object_type. Preserve any field the critique did not "
    "flag.\n\n"
    "Rules:\n"
    " - Talk about patterns, not specific people. Replace personal "
    "names with role descriptors (worker, recruiter, employer).\n"
    " - Use the canonical ILO indicator vocabulary: fee_camouflage, "
    "fee_bondage, salary_deduction, debt_bondage, passport_retention, "
    "document_control, retaliation_risk, jurisdiction_shopping, "
    "wage_theft, deceptive_recruitment, movement_restriction.\n"
    " - Corridors are XX-YY uppercase (PH-HK, ID-MY, BD-LB).\n"
    " - Journey stages: recruitment, training, payment_and_debt, "
    "departure, transit, arrival_and_placement, employment, exit, "
    "post_return.\n"
    " - Quotes describe the pattern in abstract terms, not 'in this "
    "case the worker'.\n\n"
    "Output STRICT JSON ONLY: the polished content dict with the "
    "same top-level field names as the input draft."
)


def _build_polish_response(app: Any, body: dict[str, Any]) -> dict[str, Any]:
    """Two-pass critique + rewrite polish for an existing draft envelope."""
    envelope = body.get("envelope") or {}
    if not isinstance(envelope, dict) or not envelope.get("content"):
        raise HTTPException(400, "envelope.content is required")
    use_gemma = bool(body.get("use_gemma", True))
    max_passes = int(body.get("max_passes") or 1)
    max_passes = max(1, min(max_passes, 2))

    target_type = (
        envelope.get("knowledge_object_type")
        or envelope.get("target_type")
        or "extracted_fact"
    )
    original_content = dict(envelope.get("content") or {})

    gc = getattr(app.state, "gemma_call", None) if use_gemma else None
    base_extensions = dict(envelope.get("extensions") or {})
    base_extensions["model_call_requested"] = use_gemma
    base_extensions["model_call_available"] = gc is not None

    # Short-circuit when Gemma isn't available: just re-standardize the
    # existing content (idempotent) so the reviewer still gets a
    # cleanly-shaped envelope back without spinning up the model.
    if gc is None:
        polished_content = _standardize_fact_envelope(
            original_content, target_type
        )
        base_extensions["polish_skipped"] = (
            "gemma disabled by caller" if not use_gemma
            else "no model loaded"
        )
        base_extensions["standardized_shape"] = True
        return {
            "envelope": {
                **envelope,
                "content": polished_content,
                "extensions": base_extensions,
            },
            "critique": None,
            "passes": 0,
            "diff": _diff_fields(original_content, polished_content),
        }

    # Pass 1: critique
    critique: dict[str, Any] = {"issues": [], "overall": ""}
    critique_raw = ""
    critique_error: str | None = None
    try:
        crit_msgs = [
            {"role": "system", "content": [{"type": "text", "text": _POLISH_CRITIQUE_SYSTEM}]},
            {"role": "user", "content": [{"type": "text", "text":
                "Draft envelope content (target_type="
                + str(target_type) + "):\n"
                + _json.dumps(original_content, indent=2, default=str)
            }]},
        ]
        crit_out = gc(crit_msgs, max_new_tokens=512, temperature=0.1)
        critique_raw = crit_out if isinstance(crit_out, str) else (
            (crit_out or {}).get("text")
            or (crit_out or {}).get("response")
            or ""
        )
        critique_raw = sanitize_model_output(critique_raw)
        from duecare.chat._model_json import extract_json
        ex = extract_json(critique_raw)
        if isinstance(ex.payload, dict) and isinstance(ex.payload.get("issues"), list):
            critique = ex.payload
        else:
            critique_error = "critique JSON did not parse"
    except Exception as e:  # noqa: BLE001
        critique_error = f"{type(e).__name__}: {str(e)[:160]}"

    # If critique failed OR found no issues, skip rewrite and just
    # re-standardize so the reviewer still gets a clean envelope.
    if critique_error or not critique.get("issues"):
        polished_content = _standardize_fact_envelope(
            original_content, target_type
        )
        base_extensions["standardized_shape"] = True
        if critique_error:
            base_extensions["polish_critique_error"] = critique_error
        else:
            base_extensions["polish_clean_pass"] = True
        return {
            "envelope": {
                **envelope,
                "content": polished_content,
                "extensions": base_extensions,
            },
            "critique": critique if not critique_error else {"error": critique_error},
            "passes": 1,
            "diff": _diff_fields(original_content, polished_content),
        }

    # Pass 2: rewrite
    rewrite_error: str | None = None
    rewritten_content: dict[str, Any] = dict(original_content)
    try:
        critique_text = _json.dumps(critique, indent=2, default=str)
        rw_msgs = [
            {"role": "system", "content": [{"type": "text", "text": _POLISH_REWRITE_SYSTEM}]},
            {"role": "user", "content": [{"type": "text", "text":
                "Current draft (target_type=" + str(target_type) + "):\n"
                + _json.dumps(original_content, indent=2, default=str)
                + "\n\nCritique (apply EVERY fix):\n"
                + critique_text
            }]},
        ]
        rw_out = gc(rw_msgs, max_new_tokens=768, temperature=0.2)
        rw_raw = rw_out if isinstance(rw_out, str) else (
            (rw_out or {}).get("text")
            or (rw_out or {}).get("response")
            or ""
        )
        rw_raw = sanitize_model_output(rw_raw)
        from duecare.chat._model_json import extract_json
        ex = extract_json(rw_raw)
        if isinstance(ex.payload, dict):
            # Merge: keep the original keys but overwrite with the
            # rewritten values. This protects against Gemma dropping a
            # field it didn't explicitly fix.
            merged = dict(original_content)
            merged.update({k: v for k, v in ex.payload.items() if v is not None})
            rewritten_content = merged
        else:
            rewrite_error = "rewrite JSON did not parse"
    except Exception as e:  # noqa: BLE001
        rewrite_error = f"{type(e).__name__}: {str(e)[:160]}"

    polished_content = _standardize_fact_envelope(
        rewritten_content, target_type
    )
    base_extensions["standardized_shape"] = True
    base_extensions["polished_by_gemma"] = True
    base_extensions["polish_passes"] = 2 if not rewrite_error else 1
    if rewrite_error:
        base_extensions["polish_rewrite_error"] = rewrite_error

    return {
        "envelope": {
            **envelope,
            "content": polished_content,
            "extensions": base_extensions,
        },
        "critique": critique,
        "passes": 2 if not rewrite_error else 1,
        "diff": _diff_fields(original_content, polished_content),
    }


def _diff_fields(before: dict, after: dict) -> list[dict[str, Any]]:
    """Produce a compact per-field diff for the UI. Each entry is
    {"key", "before", "after", "changed"}. before/after are stringified
    so the UI can render them without JSON.parse acrobatics."""
    keys = sorted(set(before.keys()) | set(after.keys()))
    out: list[dict[str, Any]] = []
    for k in keys:
        b = before.get(k)
        a = after.get(k)
        out.append({
            "key": k,
            "before": _short_repr(b),
            "after": _short_repr(a),
            "changed": (b != a),
        })
    return out


def _short_repr(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value if len(value) <= 240 else (value[:240] + "…")
    try:
        s = _json.dumps(value, default=str)
    except Exception:
        s = str(value)
    return s if len(s) <= 240 else (s[:240] + "…")


def register_routes(app: Any) -> None:
    """Attach the extraction routes to a FastAPI app."""

    def _draft_jobs() -> tuple[dict[str, dict[str, Any]], _threading.Lock]:
        if not hasattr(app.state, "knowledge_draft_jobs"):
            app.state.knowledge_draft_jobs = {}
        if not hasattr(app.state, "knowledge_draft_jobs_lock"):
            app.state.knowledge_draft_jobs_lock = _threading.Lock()
        return app.state.knowledge_draft_jobs, app.state.knowledge_draft_jobs_lock

    def _draft_job_update(job_id: str, **fields: Any) -> None:
        jobs, lock = _draft_jobs()
        with lock:
            job = jobs.setdefault(job_id, {"job_id": job_id, "events": []})
            now = _dt.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            if job.get("status") in {"abandoned", "cancelled"} and fields.get("status") not in {"abandoned", "cancelled"}:
                incoming_status = str(fields.get("status") or "running")
                if incoming_status == "complete":
                    job["late_status"] = "complete"
                    job["late_completed_at"] = now
                    if fields.get("result") is not None:
                        job["late_result"] = fields.get("result")
                    job.setdefault("events", []).append({
                        "ts": now,
                        "status": "abandoned",
                        "phase": "late_complete",
                        "pct": job.get("pct", 0),
                        "detail": (
                            "Knowledge draft completed after browser polling "
                            "was abandoned; result is retained as late_result."
                        ),
                    })
                elif incoming_status == "error":
                    job["late_status"] = "error"
                    job["late_error"] = fields.get("error") or fields.get("detail") or "worker failed"
                    job.setdefault("events", []).append({
                        "ts": now,
                        "status": "abandoned",
                        "phase": "late_error",
                        "pct": job.get("pct", 0),
                        "detail": str(job["late_error"])[:300],
                    })
                job["updated_at"] = now
                return
            event = {
                "ts": now,
                "status": fields.get("status", job.get("status", "running")),
                "phase": fields.get("phase", job.get("phase", "running")),
                "pct": fields.get("pct", job.get("pct", 0)),
                "detail": fields.get("detail", ""),
            }
            for key in ("error",):
                if key in fields and fields[key] is not None:
                    event[key] = fields[key]
            job.update(fields)
            job.setdefault("events", []).append(event)
            job["updated_at"] = now

    @app.post("/api/knowledge/draft-envelope/start")
    async def api_knowledge_draft_envelope_start(request: Request) -> Any:
        """Start a background KnowledgeObject draft job and return a poll URL."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        raw_text = (body.get("raw_text") or "").strip()
        if not raw_text:
            raise HTTPException(400, "raw_text is required")
        job_id = f"knowledge_draft_{_uuid4().hex[:12]}"
        now = _dt.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        jobs, lock = _draft_jobs()
        with lock:
            jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "phase": "queued",
                "pct": 4,
                "created_at": now,
                "updated_at": now,
                "events": [{
                    "ts": now,
                    "status": "queued",
                    "phase": "queued",
                    "pct": 4,
                    "detail": (
                        "Knowledge drafting queued. Gemma refinement may take "
                        "several minutes for long source text."
                    ),
                }],
            }

        def worker() -> None:
            try:
                _draft_job_update(
                    job_id,
                    status="running",
                    phase="layers",
                    pct=18,
                    detail="Running deterministic GREP/RAG grounding for draft context.",
                )
                _draft_job_update(
                    job_id,
                    status="running",
                    phase="model_or_fallback",
                    pct=42,
                    detail=(
                        "Drafting KnowledgeObject envelopes. If Gemma is enabled "
                        "and loaded, this is the model-call phase."
                    ),
                )
                worker_body = dict(body)
                worker_body["_replay_endpoint"] = "/api/knowledge/draft-envelope/start"
                result = _build_draft_response(app, worker_body)
                n = len(result.get("suggestions") or [])
                _draft_job_update(
                    job_id,
                    status="complete",
                    phase="complete",
                    pct=100,
                    detail=f"Draft suggestions ready: {n}.",
                    result=result,
                )
            except Exception as e:
                _draft_job_update(
                    job_id,
                    status="error",
                    phase="failed",
                    pct=100,
                    detail=str(e),
                    error=f"{type(e).__name__}: {e}"[:300],
                )

        thread = _threading.Thread(target=worker, name=f"duecare-{job_id}", daemon=True)
        thread.start()
        return JSONResponse({
            "job_id": job_id,
            "status": "queued",
            "phase": "queued",
            "pct": 4,
            "poll_url": f"/api/knowledge/draft-envelope/status/{job_id}",
            "cancel_url": f"/api/knowledge/draft-envelope/cancel/{job_id}",
            "demo_replay": demo_replay(
                lane="knowledge_extraction",
                endpoint="/api/knowledge/draft-envelope/start",
                request={
                    "target_leaf": body.get("target_type") or body.get("target_leaf") or "auto",
                    "anonymize": bool(body.get("anonymize", False)),
                    "use_gemma": bool(body.get("use_gemma", True)),
                    "raw_text_chars": len(raw_text),
                    "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                },
                response_summary={
                    "job_id": job_id,
                    "poll_url": f"/api/knowledge/draft-envelope/status/{job_id}",
                    "cancel_url": f"/api/knowledge/draft-envelope/cancel/{job_id}",
                },
                artifacts=[{
                    "name": "knowledge_draft_job_status",
                    "kind": "poll_endpoint",
                    "path": f"/api/knowledge/draft-envelope/status/{job_id}",
                }],
            ),
        })

    @app.post("/api/knowledge/draft-envelope/cancel/{job_id}")
    def api_knowledge_draft_envelope_cancel(job_id: str) -> Any:
        """Abandon browser-side polling for a long Gemma draft job."""
        jobs, lock = _draft_jobs()
        with lock:
            job = jobs.get(job_id)
            if not job:
                raise HTTPException(404, f"unknown knowledge draft job: {job_id}")
            if job.get("status") in {"complete", "error"}:
                job["cancelled"] = False
                job["cancel_detail"] = "Job already reached a terminal state before cancel."
                return JSONResponse(dict(job))
            now = _dt.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            job["status"] = "abandoned"
            job["phase"] = "abandoned"
            job["detail"] = (
                "Browser-side polling was abandoned. Rerun with Gemma refinement "
                "off for a deterministic draft, or check this status endpoint "
                "later for late_result."
            )
            job["cancelled"] = True
            job["abandoned_at"] = now
            job["updated_at"] = now
            job.setdefault("events", []).append({
                "ts": now,
                "status": "abandoned",
                "phase": "abandoned",
                "pct": job.get("pct", 0),
                "detail": job["detail"],
            })
            return JSONResponse(dict(job))

    @app.get("/api/knowledge/draft-envelope/status/{job_id}")
    def api_knowledge_draft_envelope_status(job_id: str) -> Any:
        jobs, lock = _draft_jobs()
        with lock:
            job = dict(jobs.get(job_id) or {})
        if not job:
            raise HTTPException(404, f"unknown knowledge draft job: {job_id}")
        return JSONResponse(job)

    @app.post("/api/knowledge/source-file")
    async def api_knowledge_source_file(request: Request) -> Any:
        """Parse an uploaded source bundle into bounded text for drafting.

        This intentionally reuses the Bulk File Review parser so Knowledge
        Extraction accepts the same practical evidence shapes: ZIP, CSV,
        JSONL, text, extractable PDFs, images, and scan-like media assets.
        The endpoint does not promote anything. It only prepares local source
        text that the reviewer can inspect before drafting envelopes.
        """
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            raise HTTPException(400, "no `file` field in multipart upload")
        filename = getattr(upload, "filename", "uploaded") or "uploaded"
        contents = await upload.read()
        try:
            max_rows = int(form.get("max_rows") or 40)
        except Exception:
            max_rows = 40
        try:
            max_chars = int(form.get("max_chars") or 28000)
        except Exception:
            max_chars = 28000
        max_rows = max(1, min(max_rows, 80))
        max_chars = max(4000, min(max_chars, 60000))

        try:
            from ..process.handler import _ROW_CAP, _parse_upload, _score_rows

            rows = _parse_upload(filename, contents)
            capped = rows[:min(max_rows, _ROW_CAP)]
            results, agg_grep, agg_entity, agg_statute = _score_rows(
                capped, getattr(app.state, "grep_call", None)
            )
        except Exception as e:
            raise HTTPException(400, f"parse failed: {e}")

        by_row = {r.get("row_id"): r for r in results}
        media_rows = [r for r in rows if r.get("processing_level") == "media_asset" or r.get("needs_ocr")]
        lines = [
            f"Knowledge source upload: {filename}",
            f"Rows parsed: {len(rows)}; rows included for drafting: {len(capped)}",
            f"Media or OCR work items queued: {len(media_rows)}",
            "",
        ]
        if agg_grep:
            top_rules = ", ".join(f"{k} x {v}" for k, v in sorted(agg_grep.items(), key=lambda kv: -kv[1])[:8])
            lines.append("Top GREP rules: " + top_rules)
        if agg_statute:
            top_statutes = ", ".join(f"{k} x {v}" for k, v in sorted(agg_statute.items(), key=lambda kv: -kv[1])[:8])
            lines.append("Top statutes: " + top_statutes)
        if agg_entity:
            entity_totals = ", ".join(f"{k} x {v}" for k, v in sorted(agg_entity.items())[:12])
            lines.append("Entity totals: " + entity_totals)
        if agg_grep or agg_statute or agg_entity:
            lines.append("")

        row_summaries: list[dict[str, Any]] = []
        char_budget = max_chars
        for idx, row in enumerate(capped, start=1):
            row_id = str(row.get("row_id") or f"row-{idx}")
            scored = by_row.get(row_id) or {}
            text = str(row.get("text") or "")
            snippet = text[:1200]
            hit_ids = [
                str(h.get("rule") or h.get("rule_id") or h.get("id") or "")
                for h in (scored.get("grep_hits") or [])
            ]
            hit_ids = [h for h in hit_ids if h]
            entity_counts = {
                key: len(value or [])
                for key, value in (scored.get("entities") or {}).items()
                if value
            }
            block = [
                f"[{idx}] row_id: {row_id}",
                f"source_path: {row.get('source_path') or row_id}",
                f"folders: {', '.join(row.get('folders') or []) or '(none)'}",
                f"processing_level: {row.get('processing_level') or 'document'}",
            ]
            if row.get("media_type"):
                block.append(f"media_type: {row.get('media_type')}; status: queued_for_ocr_and_multimodal_extraction")
            if hit_ids:
                block.append("grep_hits: " + ", ".join(hit_ids[:8]))
            if entity_counts:
                block.append("entities: " + _json.dumps(entity_counts, sort_keys=True))
            block.extend(["text:", snippet.strip(), ""])
            block_text = "\n".join(block)
            if len(block_text) > char_budget:
                lines.append(f"[truncated before {row_id}: source upload exceeded {max_chars} characters]")
                break
            lines.append(block_text)
            char_budget -= len(block_text)
            row_summaries.append({
                "row_id": row_id,
                "source_path": row.get("source_path") or row_id,
                "processing_level": row.get("processing_level") or "document",
                "media_type": row.get("media_type"),
                "grep_hits": hit_ids,
                "entity_counts": entity_counts,
                "char_count": len(text),
            })

        return JSONResponse({
            "filename": filename,
            "n_rows_total": len(rows),
            "n_rows_included": len(row_summaries),
            "n_media_assets": len(media_rows),
            "truncated": len(rows) > len(row_summaries),
            "raw_text": "\n".join(lines).strip(),
            "row_summaries": row_summaries,
            "demo_replay": demo_replay(
                lane="knowledge_extraction",
                endpoint="/api/knowledge/source-file",
                request={
                    "filename": filename,
                    "file_bytes": len(contents),
                    "file_sha256": hashlib.sha256(contents).hexdigest(),
                    "max_rows": max_rows,
                    "max_chars": max_chars,
                },
                response_summary={
                    "n_rows_total": len(rows),
                    "n_rows_included": len(row_summaries),
                    "n_media_assets": len(media_rows),
                    "truncated": len(rows) > len(row_summaries),
                },
                artifacts=[{
                    "name": "raw_text",
                    "kind": "inline_response_json",
                    "chars": len("\n".join(lines).strip()),
                }],
                note=(
                    "Reattach the same local file or use the browser replay "
                    "download from a synthetic demo to reconstruct the exact "
                    "multipart request."
                ),
            ),
        })

    @app.post("/api/knowledge/draft-envelope")
    async def api_knowledge_draft_envelope(request: Request) -> Any:
        """Gemma-assisted: raw text + target leaf -> draft envelope."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        return JSONResponse(_build_draft_response(app, body))

    @app.post("/api/knowledge/polish-envelope")
    async def api_knowledge_polish_envelope(request: Request) -> Any:
        """Two-pass Gemma 4 polish of an existing draft envelope.

        Pass 1 (critique): Gemma reads the draft and produces a JSON
        list of specific issues — vague phrasing, unsupported claims,
        missing ILO indicator vocabulary, build-log-flavored quotes,
        operational metadata leakage.

        Pass 2 (rewrite): Gemma applies the critique, returning a
        polished content dict that goes through the standard fact
        normalizer one more time before we hand it back.

        Returns the polished envelope, the critique notes, the
        per-field diff, and provenance flags so the reviewer can see
        what changed and why. If Gemma is unavailable, returns the
        original envelope with a clear `polish_skipped` reason."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        return JSONResponse(_build_polish_response(app, body))
