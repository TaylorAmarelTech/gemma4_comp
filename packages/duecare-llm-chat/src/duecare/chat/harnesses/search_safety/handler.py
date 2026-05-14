"""FastAPI routes for the search-safety harness.

Endpoints:
  POST /api/search/sanitize    -- sanitize a query, return audit record
  GET  /api/search/safety-info -- expose wiring (whether Gemma rephrase
                                   is available) so the UI can show the
                                   right controls

The sanitization pipeline:
  1. Regex layer -- PII patterns (emails, phones, passport numbers,
     national IDs, IBANs, monetary amounts with currency, URLs).
     Each match is replaced with a [REDACTED-KIND] placeholder.
  2. Optional Gemma rephrase -- if `app.state.gemma_call` is wired
     and the user opts in (mode="rephrase"), Gemma is asked to
     rephrase the redacted query into a more general form.
  3. Block check -- reserved for future heuristics that refuse to
     dispatch a query at all.

Audit log:
  Every call appends to /kaggle/working/training/search_safety.jsonl
  via _training_log.log_interaction. The row contains sha256
  fingerprints, not plaintext, so the audit cannot leak the original
  query even if the JSONL is uploaded somewhere.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field


# Regex catalog: ordered most-specific to least-specific so longer
# patterns match before single-token shrapnel.
_REDACTION_PATTERNS = [
    ("email",       re.compile(r"\b[\w.+\-]+@[\w\-]+\.[\w.\-]+\b")),
    ("phone_intl",  re.compile(r"\+\d[\d\-\s().]{7,}\d")),
    ("phone_local", re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("passport",    re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")),
    ("iban",        re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")),
    ("monetary",    re.compile(r"\b\d{1,3}(?:[,.]?\d{3})*(?:\.\d{1,2})?\s*(?:USD|EUR|GBP|PHP|HKD|SGD|QAR|AED|SAR)\b")),
    ("url",         re.compile(r"https?://[^\s]+")),
    ("national_id", re.compile(r"\b\d{9,15}\b")),
]


def _sha16(text: str) -> str:
    """Short hex prefix of sha256 -- enough for an audit reference
    but not a reversal vector."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


class SanitizeRequest(BaseModel):
    query: str = Field(..., description="The user's raw search query.")
    mode: str = Field(
        "strict",
        description=(
            "strict (default): regex-only redaction, fast. "
            "rephrase: also ask Gemma to rephrase the redacted query "
            "into a more general form. Slower; requires gemma_call wired."
        ),
    )


def _regex_redact(text: str) -> tuple[str, list[dict]]:
    """Replace PII matches with [REDACTED-KIND] placeholders.
    Returns (sanitized_text, redactions_list)."""
    out = text
    redactions: list[dict] = []
    for kind, pattern in _REDACTION_PATTERNS:
        def _sub(m: re.Match, _kind: str = kind) -> str:
            redactions.append({
                "kind": _kind,
                "original_sha256": _sha16(m.group(0)),
                "replacement": f"[REDACTED-{_kind.upper()}]",
            })
            return f"[REDACTED-{_kind.upper()}]"
        out = pattern.sub(_sub, out)
    return out, redactions


def register_routes(app) -> None:
    @app.get("/api/search/safety-info")
    def search_safety_info() -> Any:
        """Tell the UI which sanitization modes are available."""
        return {
            "regex_redaction": True,
            "gemma_rephrase_available": getattr(app.state, "gemma_call", None) is not None,
            "patterns": [k for k, _ in _REDACTION_PATTERNS],
        }

    @app.post("/api/search/sanitize")
    def search_sanitize(req: SanitizeRequest) -> Any:
        """Sanitize a search query. Always returns a sanitized form;
        callers should send THAT to any external backend, not the
        original."""
        raw = (req.query or "").strip()
        if not raw:
            raise HTTPException(400, "query is required")

        sanitized, redactions = _regex_redact(raw)

        rephrase_trace = {"fired": False, "wired": False}
        if req.mode == "rephrase":
            gemma_call = getattr(app.state, "gemma_call", None)
            rephrase_trace["wired"] = gemma_call is not None
            if gemma_call is not None:
                prompt = (
                    "You will be given a search query that has already had "
                    "PII redacted with [REDACTED-X] tokens. Rephrase the "
                    "query in a general form that preserves the search "
                    "intent but does NOT carry any specific personal "
                    "information. Output ONLY the rephrased query, no "
                    "preamble.\n\nQuery: " + sanitized + "\n\nRephrased:"
                )
                try:
                    rephrased = str(gemma_call(prompt, max_new_tokens=128)).strip()
                    if rephrased and len(rephrased) <= 400:
                        sanitized = rephrased
                        rephrase_trace["fired"] = True
                except Exception as e:  # noqa: BLE001
                    rephrase_trace["error"] = f"{type(e).__name__}: {e}"

        blocked = False
        reason = None

        try:
            from .._training_log import log_interaction
            log_interaction(
                "search_safety",
                input_payload={
                    "query_sha256": _sha16(raw),
                    "mode": req.mode,
                    "length": len(raw),
                },
                output_payload={
                    "sanitized_sha256": _sha16(sanitized),
                    "redactions_count": len(redactions),
                    "blocked": blocked,
                },
                applied_layers={
                    "regex": {"fired": bool(redactions), "n_hits": len(redactions)},
                    "gemma_rephrase": rephrase_trace,
                },
                trace={"redaction_kinds": sorted({r["kind"] for r in redactions})},
            )
        except Exception:
            pass

        return {
            "sanitized": sanitized,
            "redactions": redactions,
            "blocked": blocked,
            "reason": reason,
            "mode": req.mode,
            "rephrase_fired": rephrase_trace.get("fired", False),
            "rephrase_wired": rephrase_trace.get("wired", False),
        }
