"""Triage harness handler — batch safety screening on ONE loaded Gemma.

Platform safety (deployment mode 1) needs to screen batches of job ads /
recruiter messages. Two stages, one model — the same loaded Gemma the chat
page uses, so there is no second model, no endpoint, and no model switch:

    GREP rules    deterministic, microseconds, catches known patterns
      -> Gemma    one flag/clear verdict (+ reason) per item the GREP rules
                  did not already high-severity flag. Optionally, a deeper
                  GREP/RAG/tools-grounded pass on the flagged items (same model).

The model verdict ROUTES, it never answers: a "clear" verdict means "no signal
worth deeper review", not "safe". With no model loaded the result is
``passed_grep_only`` — explicitly not "cleared" — so a reviewer can always tell
whether the model actually looked at an item.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

MAX_ITEMS = 200
MAX_ITEM_CHARS = 20_000
SCREEN_MAX_TOKENS = 160
DEEP_MAX_TOKENS = 768
DEFAULT_CLEAR_THRESHOLD = 0.7

_HIGH_SEVERITIES = frozenset({"high", "critical"})
_SEVERITY_ORDER = ("critical", "high", "medium", "low")

POLICY = (
    "The model verdict only routes; it never produces user-facing answers. "
    "Items with status 'flagged' or 'review' go to deeper analysis and/or human "
    "review. 'passed_grep_only' means no model looked at the item."
)

_SCREEN_PROMPT = (
    "You are a FIRST-PASS safety screen for job advertisements and recruiter "
    "messages shown to migrant workers. Decide whether the content shows "
    "recruitment-exploitation risk signals: illegal placement fees, passport or "
    "document retention, contract substitution, debt bondage, deceptive 'free "
    "visa' offers, wage withholding, isolation or movement control, or "
    "too-good-to-be-true pay for unskilled overseas work.\n"
    "Reply with ONLY compact JSON, no prose: "
    '{"verdict": "flag" | "clear", "confidence": <0.0-1.0>, '
    '"category": "<one short risk label or empty>", '
    '"reason": "<one sentence>"}\n\n'
    "CONTENT:\n"
)

_DEEP_PROMPT = (
    "You are DueCare's deep reviewer for escalated recruitment content. "
    "Analyze the content for labour-exploitation indicators (use the ILO "
    "forced-labour indicator vocabulary), quote the exact phrases that are "
    "evidence, cite applicable law or ILO conventions where relevant, and end "
    "with a recommended action: block / warn / monitor / clear, with one "
    "sentence of reasoning."
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _max_severity(severities: list[str]) -> str:
    for level in _SEVERITY_ORDER:
        if level in severities:
            return level
    return severities[0] if severities else ""


def _parse_verdict(raw: str) -> dict[str, Any]:
    """Parse the model's JSON verdict; degrade to 'review' on any failure.

    A malformed reply must never silently clear an item, so every parse failure
    becomes verdict='review' with the error recorded.
    """
    cleaned = re.sub(r"```(?:json)?", "", str(raw or "")).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return {"verdict": "review",
                "parse_error": f"no JSON object in model reply: {cleaned[:120]!r}"}
    try:
        data = json.loads(match.group(0))
    except Exception as exc:  # noqa: BLE001 — any parse failure routes to review
        return {"verdict": "review", "parse_error": f"{type(exc).__name__}: {exc}"}
    verdict = str(data.get("verdict") or "").strip().lower()
    if verdict not in {"flag", "clear"}:
        return {"verdict": "review", "parse_error": f"unknown verdict {verdict!r}"}
    try:
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
    except Exception:  # noqa: BLE001 — non-numeric confidence is a soft failure
        confidence = 0.0
    return {
        "verdict": verdict,
        "confidence": confidence,
        "category": str(data.get("category") or "")[:80],
        "reason": str(data.get("reason") or "")[:300],
    }


def resolve_screen_model(app: Any) -> tuple[Callable[[str], str] | None, str, str]:
    """Resolve the screening model: the ONE already-loaded in-process Gemma -- the same model
    the chat page uses. No second model, no endpoint, no model switch.

    Returns ``(caller, label, source)`` where source is ``gemma4_runtime`` or ``not_configured``.
    """
    gemma = getattr(app.state, "gemma_call", None) if app is not None else None
    if gemma is None:
        return None, "", "not_configured"
    from ..model_interface import call_model_backend

    def call(prompt: str) -> str:
        return call_model_backend(
            gemma, prompt, max_new_tokens=SCREEN_MAX_TOKENS, temperature=0.0,
        ).text

    return call, "loaded Gemma (in-process)", "gemma4_runtime"


def _deep_caller(app: Any) -> Callable[[str], str] | None:
    """Deeper pass = the SAME loaded Gemma with the full grounding layers.

    Escalated items get the harnessed treatment: GREP + RAG + tools grounding
    composed into the prompt, exactly like the chat page — one model, no switch.
    """
    gemma = getattr(app.state, "gemma_call", None) if app is not None else None
    if gemma is None:
        return None
    from .._layers import compose_layers
    from ..model_interface import call_model_backend

    def call(text: str) -> str:
        composed = compose_layers(app, text, layers=("grep", "rag", "tools"))
        grounding = composed.get("grounding") or ""
        prompt = _DEEP_PROMPT
        if grounding:
            prompt += "\n\nGROUNDING (from local DueCare layers):\n" + grounding
        prompt += "\n\nCONTENT:\n" + text
        return call_model_backend(
            gemma, prompt, max_new_tokens=DEEP_MAX_TOKENS, temperature=0.0,
        ).text

    return call


def screen_items(
    items: list[dict[str, Any]],
    *,
    grep_call: Callable[..., dict[str, Any]] | None = None,
    model_call: Callable[[str], str] | None = None,
    deep_call: Callable[[str], str] | None = None,
    model_label: str = "",
    clear_threshold: float = DEFAULT_CLEAR_THRESHOLD,
    run_deep: bool = False,
) -> dict[str, Any]:
    """Run the GREP -> Gemma verdict (-> optional deeper pass) screen over items.

    Pure function: all backends are injected callables so tests can use fakes
    and the route handler can wire real ones. Items are ``{"id": ..., "text": str}``.
    Returns the response dict (summary / items / policy). Raw item text is
    never echoed back — items carry ``text_sha256`` for correlation.
    """
    t_start = time.time()
    grep_ms = model_ms = deep_ms = 0.0
    n_model_calls = 0
    rows: list[dict[str, Any]] = []

    for idx, item in enumerate(items):
        text = item["text"]
        row: dict[str, Any] = {
            "index": idx,
            "id": str(item.get("id") or f"item_{idx}"),
            "text_sha256": _sha256(text),
            "grep": {"fired": False, "n_hits": 0, "rule_ids": [], "max_severity": ""},
            "screen": None,
            "deep": None,
        }

        # ── Stage 1: deterministic GREP ────────────────────────────────
        grep_flagged = False
        if grep_call is not None:
            t0 = time.time()
            try:
                out = grep_call(text) or {}
                hits = out.get("hits") or []
                severities = [str(h.get("severity") or "medium").lower() for h in hits]
                # Accept every rule-id key shape: test fakes use "rule_id"/"id";
                # the real default_harness grep_call uses "rule". Without the
                # "rule" fallback the live triage page shows fired rules with
                # blank ids.
                rule_ids = [
                    rid for rid in
                    (h.get("rule_id") or h.get("id") or h.get("rule") for h in hits)
                    if rid
                ][:10]
                row["grep"] = {
                    "fired": bool(hits),
                    "n_hits": len(hits),
                    "rule_ids": rule_ids,
                    "max_severity": _max_severity(severities),
                }
                grep_flagged = any(s in _HIGH_SEVERITIES for s in severities)
            except Exception as exc:  # noqa: BLE001 — a layer failure degrades, never raises
                row["grep"] = {"fired": False, "error": f"{type(exc).__name__}: {exc}"[:200]}
            grep_ms += (time.time() - t0) * 1000
        grep_soft_signal = bool(row["grep"].get("fired")) and not grep_flagged

        # ── Stage 2: Gemma verdict (skipped when GREP already high-flagged it) ──
        if grep_flagged:
            row["status"], row["flagged_by"] = "flagged", "grep"
            row["screen"] = {"skipped": "grep already flagged (high severity)"}
        elif model_call is not None:
            t0 = time.time()
            n_model_calls += 1
            try:
                raw = model_call(_SCREEN_PROMPT + text)
                verdict = _parse_verdict(raw)
            except Exception as exc:  # noqa: BLE001 — backend failure routes to review
                verdict = {"verdict": "review",
                           "error": f"{type(exc).__name__}: {exc}"[:200]}
            latency = (time.time() - t0) * 1000
            model_ms += latency
            verdict["latency_ms"] = round(latency)
            row["screen"] = verdict
            v = verdict.get("verdict")
            confidence = float(verdict.get("confidence") or 0.0)
            if v == "flag":
                row["status"] = "flagged"
                row["flagged_by"] = "grep+model" if grep_soft_signal else "model"
            elif v == "clear" and confidence >= clear_threshold and not grep_soft_signal:
                row["status"], row["flagged_by"] = "cleared", ""
            else:
                row["status"] = "review"
                row["flagged_by"] = "grep_soft_signal" if grep_soft_signal else "low_confidence"
        else:
            row["screen"] = {"skipped": "no model loaded"}
            if grep_soft_signal:
                row["status"], row["flagged_by"] = "review", "grep_soft_signal"
            else:
                row["status"], row["flagged_by"] = "passed_grep_only", ""

        row["escalate"] = row["status"] in ("flagged", "review")

        # ── Stage 3: deeper grounded pass on escalated items (opt-in) ──
        if run_deep and row["escalate"] and deep_call is not None:
            t0 = time.time()
            try:
                analysis = deep_call(text)
                row["deep"] = {"analysis": analysis,
                               "latency_ms": round((time.time() - t0) * 1000)}
            except Exception as exc:  # noqa: BLE001 — deep failure leaves item escalated
                row["deep"] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
            deep_ms += (time.time() - t0) * 1000

        rows.append(row)

    def by_status(status: str) -> int:
        return sum(1 for r in rows if r["status"] == status)

    summary: dict[str, Any] = {
        "n_items": len(rows),
        "n_flagged": by_status("flagged"),
        "n_review": by_status("review"),
        "n_cleared": by_status("cleared"),
        "n_passed_grep_only": by_status("passed_grep_only"),
        "n_escalated": sum(1 for r in rows if r["escalate"]),
        "model": {
            "available": model_call is not None,
            "label": model_label,
            "n_calls": n_model_calls,
        },
        "timings_ms": {
            "grep": round(grep_ms),
            "model": round(model_ms),
            "deep": round(deep_ms),
            "total": round((time.time() - t_start) * 1000),
        },
    }
    if n_model_calls and model_ms > 0:
        summary["model"]["measured_items_per_min"] = round(
            n_model_calls / (model_ms / 1000.0) * 60.0, 1)
    return {"summary": summary, "items": rows, "policy": POLICY}


def register_routes(app: Any) -> None:
    """Attach POST /api/triage/screen and GET /api/triage/status."""

    @app.post("/api/triage/screen")
    async def api_triage_screen(request: Request) -> Any:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        raw_items = body.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise HTTPException(400, "items must be a non-empty list")
        if len(raw_items) > MAX_ITEMS:
            raise HTTPException(400, f"max {MAX_ITEMS} items per call")
        items: list[dict[str, Any]] = []
        for i, raw in enumerate(raw_items):
            if isinstance(raw, str):
                raw = {"text": raw}
            if not isinstance(raw, dict) or not isinstance(raw.get("text"), str) \
                    or not raw["text"].strip():
                raise HTTPException(400, f"items[{i}] must have a non-empty string 'text'")
            if len(raw["text"]) > MAX_ITEM_CHARS:
                raise HTTPException(400, f"items[{i}] exceeds {MAX_ITEM_CHARS} chars")
            items.append({"id": raw.get("id"), "text": raw["text"]})

        # One model: the already-loaded Gemma screens every item by default (no switch).
        # `use_model: false` forces GREP-only; `run_deep` adds the grounded pass on flagged items.
        use_model = body.get("use_model", True) is not False
        run_deep = bool(body.get("run_deep", False))
        try:
            clear_threshold = max(0.0, min(1.0, float(
                body.get("clear_threshold", DEFAULT_CLEAR_THRESHOLD))))
        except Exception:
            raise HTTPException(400, "clear_threshold must be a number in [0, 1]")

        grep_call = getattr(app.state, "grep_call", None)
        model_call: Callable[[str], str] | None = None
        model_label, model_source = "", "off"
        if use_model:
            model_call, model_label, model_source = resolve_screen_model(app)
        deep_call = _deep_caller(app) if run_deep else None

        out = screen_items(
            items,
            grep_call=grep_call,
            model_call=model_call,
            deep_call=deep_call,
            model_label=model_label,
            clear_threshold=clear_threshold,
            run_deep=run_deep,
        )
        out["summary"]["model"]["source"] = model_source

        try:
            from .._training_log import log_interaction
            log_interaction(
                "triage",
                input_payload={
                    "n_items": len(items),
                    "text_sha256s": [r["text_sha256"] for r in out["items"][:10]],
                },
                output_payload={
                    key: out["summary"][key]
                    for key in ("n_items", "n_flagged", "n_review", "n_cleared",
                                "n_passed_grep_only", "n_escalated")
                },
                applied_layers={
                    "grep": grep_call is not None,
                    "model": model_source,
                    "deep": run_deep and deep_call is not None,
                },
                trace={"timings_ms": out["summary"]["timings_ms"]},
                extra={},
            )
        except Exception:  # noqa: BLE001 — logging must never break the route
            pass
        return JSONResponse(out)

    @app.get("/api/triage/status")
    def api_triage_status() -> Any:
        model_call, model_label, model_source = resolve_screen_model(app)
        return {
            "harness": "triage",
            "purpose": (
                "Batch safety screening: GREP rules -> one loaded Gemma verdict "
                "-> optional deeper grounded pass on flagged items."
            ),
            "grep_wired": getattr(app.state, "grep_call", None) is not None,
            "model": {
                "available": model_call is not None,
                "label": model_label,
                "source": model_source,
            },
            "statuses": ["flagged", "review", "cleared", "passed_grep_only"],
            "policy": POLICY,
        }


__all__ = [
    "POLICY",
    "register_routes",
    "resolve_screen_model",
    "screen_items",
]
