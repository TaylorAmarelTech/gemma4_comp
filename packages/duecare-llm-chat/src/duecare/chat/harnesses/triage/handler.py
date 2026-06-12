"""Triage harness handler — waterfall screening for platform-scale content.

Deployment mode 1 (platform safety) needs to screen large volumes of job
ads / recruiter messages cheaply, then spend deep-model time only on the
risky few. The waterfall:

    GREP rules         deterministic, microseconds, catches known patterns
      -> fast model    one quick flag/clear verdict per item. Designed for a
                       DiffusionGemma-class endpoint (parallel-block diffusion
                       decode, up to 4x faster than autoregressive Gemma 4) or
                       any OpenAI-compatible model the operator configures.
      -> deep model    full harnessed analysis ONLY for escalated items.

The fast tier ROUTES, it never answers: a "clear" verdict means "no signal
worth deep review", not "safe". Without any model configured the result is
``passed_grep_only`` — explicitly not "cleared" — so a reviewer can always
tell whether a model actually looked at an item.

Fast-tier backend resolution order:
  1. ``DUECARE_FAST_MODEL_BASE_URL`` (+ ``DUECARE_FAST_MODEL_ID``,
     optional ``DUECARE_FAST_MODEL_API_KEY``) — an OpenAI-compatible
     endpoint, e.g. ``vllm serve google/diffusiongemma-26B-A4B-it``.
  2. The in-process loaded Gemma model (``app.state.gemma_call``).
  3. None — GREP-only honest mode.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.request
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

MAX_ITEMS = 200
MAX_ITEM_CHARS = 20_000
FAST_MAX_TOKENS = 160
DEEP_MAX_TOKENS = 768
DEFAULT_FAST_MODEL_ID = "google/diffusiongemma-26B-A4B-it"
DEFAULT_CLEAR_THRESHOLD = 0.7

_HIGH_SEVERITIES = frozenset({"high", "critical"})
_SEVERITY_ORDER = ("critical", "high", "medium", "low")

POLICY = (
    "The fast tier only routes; it never produces user-facing answers. "
    "Items with status 'flagged' or 'review' must go to the deep model and/or "
    "human review. 'passed_grep_only' means no model looked at the item."
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


def _parse_fast_verdict(raw: str) -> dict[str, Any]:
    """Parse the fast model's JSON verdict; degrade to 'review' on any failure.

    A malformed fast-model reply must never silently clear an item, so every
    parse failure becomes verdict='review' with the error recorded.
    """
    cleaned = re.sub(r"```(?:json)?", "", str(raw or "")).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return {"verdict": "review",
                "parse_error": f"no JSON object in fast-model reply: {cleaned[:120]!r}"}
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


def _openai_compat_caller(
    base_url: str,
    model_id: str,
    *,
    api_key: str = "",
    timeout: float = 60.0,
) -> Callable[[str], str]:
    """Return a prompt->text callable for an OpenAI-compatible endpoint.

    Plain urllib (no new dependencies) against POST {base}/chat/completions —
    the shape vLLM, Ollama, SGLang, and llama.cpp servers all expose.
    """
    base = base_url.rstrip("/")

    def call(prompt: str) -> str:
        body = json.dumps({
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.0,
            "max_tokens": FAST_MAX_TOKENS,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(f"{base}/chat/completions", data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8", "replace"))
        message = (out.get("choices") or [{}])[0].get("message") or {}
        return str(message.get("content") or "")

    return call


def resolve_fast_backend(app: Any) -> tuple[Callable[[str], str] | None, str, str]:
    """Resolve the fast-tier backend.

    Returns ``(caller, label, source)`` where source is one of
    ``openai_compatible_endpoint`` / ``gemma4_runtime`` / ``not_configured``.
    """
    base = os.environ.get("DUECARE_FAST_MODEL_BASE_URL", "").strip()
    if base:
        model_id = os.environ.get("DUECARE_FAST_MODEL_ID", "").strip() or DEFAULT_FAST_MODEL_ID
        api_key = os.environ.get("DUECARE_FAST_MODEL_API_KEY", "")
        return (
            _openai_compat_caller(base, model_id, api_key=api_key),
            model_id,
            "openai_compatible_endpoint",
        )
    gemma = getattr(app.state, "gemma_call", None) if app is not None else None
    if gemma is not None:
        from ..model_interface import call_model_backend

        def call(prompt: str) -> str:
            return call_model_backend(
                gemma, prompt, max_new_tokens=FAST_MAX_TOKENS, temperature=0.0,
            ).text

        return call, "in-process Gemma (loaded model)", "gemma4_runtime"
    return None, "", "not_configured"


def _deep_caller(app: Any) -> Callable[[str], str] | None:
    """Deep tier = the loaded Gemma model WITH the full grounding layers.

    Escalated items get the harnessed treatment: GREP + RAG + tools grounding
    composed into the prompt, exactly like the chat harness comparison arm.
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
    fast_call: Callable[[str], str] | None = None,
    deep_call: Callable[[str], str] | None = None,
    fast_label: str = "",
    clear_threshold: float = DEFAULT_CLEAR_THRESHOLD,
    run_deep: bool = False,
) -> dict[str, Any]:
    """Run the GREP -> fast model -> deep escalation waterfall over items.

    Pure function: all backends are injected callables so tests can use fakes
    and the route handler can wire real ones. Items are ``{"id": ..., "text": str}``.
    Returns the response dict (summary / items / policy). Raw item text is
    never echoed back — items carry ``text_sha256`` for correlation.
    """
    t_start = time.time()
    grep_ms = fast_ms = deep_ms = 0.0
    n_fast_calls = 0
    rows: list[dict[str, Any]] = []

    for idx, item in enumerate(items):
        text = item["text"]
        row: dict[str, Any] = {
            "index": idx,
            "id": str(item.get("id") or f"item_{idx}"),
            "text_sha256": _sha256(text),
            "grep": {"fired": False, "n_hits": 0, "rule_ids": [], "max_severity": ""},
            "fast": None,
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
                rule_ids = [
                    rid for rid in (h.get("rule_id") or h.get("id") for h in hits) if rid
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

        # ── Stage 2: fast-model verdict (skipped when GREP already caught it) ──
        if grep_flagged:
            row["status"], row["flagged_by"] = "flagged", "grep"
            row["fast"] = {"skipped": "grep already flagged (high severity)"}
        elif fast_call is not None:
            t0 = time.time()
            n_fast_calls += 1
            try:
                raw = fast_call(_SCREEN_PROMPT + text)
                verdict = _parse_fast_verdict(raw)
            except Exception as exc:  # noqa: BLE001 — backend failure routes to review
                verdict = {"verdict": "review",
                           "error": f"{type(exc).__name__}: {exc}"[:200]}
            latency = (time.time() - t0) * 1000
            fast_ms += latency
            verdict["latency_ms"] = round(latency)
            row["fast"] = verdict
            v = verdict.get("verdict")
            confidence = float(verdict.get("confidence") or 0.0)
            if v == "flag":
                row["status"] = "flagged"
                row["flagged_by"] = "grep+fast_model" if grep_soft_signal else "fast_model"
            elif v == "clear" and confidence >= clear_threshold and not grep_soft_signal:
                row["status"], row["flagged_by"] = "cleared", ""
            else:
                row["status"] = "review"
                row["flagged_by"] = "grep_soft_signal" if grep_soft_signal else "low_confidence"
        else:
            row["fast"] = {"skipped": "no fast model configured"}
            if grep_soft_signal:
                row["status"], row["flagged_by"] = "review", "grep_soft_signal"
            else:
                row["status"], row["flagged_by"] = "passed_grep_only", ""

        row["escalate"] = row["status"] in ("flagged", "review")

        # ── Stage 3: deep analysis of escalated items (opt-in) ────────
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
        "fast_model": {
            "configured": fast_call is not None,
            "label": fast_label,
            "n_calls": n_fast_calls,
        },
        "timings_ms": {
            "grep": round(grep_ms),
            "fast_model": round(fast_ms),
            "deep": round(deep_ms),
            "total": round((time.time() - t_start) * 1000),
        },
    }
    if n_fast_calls and fast_ms > 0:
        summary["fast_model"]["measured_items_per_min"] = round(
            n_fast_calls / (fast_ms / 1000.0) * 60.0, 1)
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

        use_fast = body.get("use_fast_model", True) is not False
        run_deep = bool(body.get("run_deep", False))
        try:
            clear_threshold = max(0.0, min(1.0, float(
                body.get("clear_threshold", DEFAULT_CLEAR_THRESHOLD))))
        except Exception:
            raise HTTPException(400, "clear_threshold must be a number in [0, 1]")

        grep_call = getattr(app.state, "grep_call", None)
        fast_call: Callable[[str], str] | None = None
        fast_label, fast_source = "", "disabled"
        if use_fast:
            fast_call, fast_label, fast_source = resolve_fast_backend(app)
        deep_call = _deep_caller(app) if run_deep else None

        out = screen_items(
            items,
            grep_call=grep_call,
            fast_call=fast_call,
            deep_call=deep_call,
            fast_label=fast_label,
            clear_threshold=clear_threshold,
            run_deep=run_deep,
        )
        out["summary"]["fast_model"]["source"] = fast_source

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
                    "fast_model": fast_source,
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
        fast_call, fast_label, fast_source = resolve_fast_backend(app)
        return {
            "harness": "triage",
            "purpose": (
                "Waterfall screening for platform-scale content: GREP rules -> "
                "fast model verdict -> deep-model escalation."
            ),
            "grep_wired": getattr(app.state, "grep_call", None) is not None,
            "fast_model": {
                "configured": fast_call is not None,
                "label": fast_label,
                "source": fast_source,
                "env": {
                    "DUECARE_FAST_MODEL_BASE_URL": (
                        "OpenAI-compatible base URL, e.g. http://localhost:8000/v1 "
                        "from: vllm serve " + DEFAULT_FAST_MODEL_ID
                    ),
                    "DUECARE_FAST_MODEL_ID": f"model id (default {DEFAULT_FAST_MODEL_ID})",
                    "DUECARE_FAST_MODEL_API_KEY": "optional bearer token",
                },
            },
            "deep_model_available": getattr(app.state, "gemma_call", None) is not None,
            "statuses": ["flagged", "review", "cleared", "passed_grep_only"],
            "policy": POLICY,
        }


__all__ = [
    "DEFAULT_FAST_MODEL_ID",
    "POLICY",
    "register_routes",
    "resolve_fast_backend",
    "screen_items",
]
