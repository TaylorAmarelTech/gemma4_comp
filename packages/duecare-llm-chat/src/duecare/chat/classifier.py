"""Content classifier mode for the Duecare chat package.

Structured-output companion to the chat playground. Instead of
free-form chat, the user submits a single piece of content (text +
optional image) and Gemma returns a strict JSON envelope:

    {
      "classification": "predatory_recruitment_debt_bondage",
      "classification_label": "Predatory recruitment with debt bondage risk",
      "confidence": 0.92,
      "overall_risk": 0.88,
      "risk_vectors": [
        {
          "dimension": "ilo_forced_labor_indicators",
          "magnitude": 0.95,
          "direction": "high",
          "evidence": "ILO indicators 4 (debt bondage) + 7 (withheld wages)..."
        },
        ...
      ],
      "recommended_action": "escalate_to_regulator",
      "rationale": "...",
      "ngo_referrals": ["POEA", "BP2MI", "MfMW HK"]
    }

The same Persona / GREP / RAG / Tools harness layers fire (when
toggled). The classifier persona is more aggressive about forcing
structured output, but otherwise the pipeline is identical.

Reuses the chat package's harness, /api/harness-info, /api/examples,
/api/docs/{layer}, and image upload endpoints. Adds:

    POST /api/classifier/evaluate   # structured-output endpoint
    GET  /                          # classifier UI
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from duecare.chat.app import (
    DEFAULT_PERSONA, GenerationParams, HarnessToggles, _IMAGE_STORE,
)


CLASSIFIER_PERSONA = """You are a content risk classifier for migrant-worker exploitation, trafficking, predatory recruitment, debt bondage, and labour-rights scenarios.

For the provided content, output ONLY a valid JSON object matching this exact schema. Do not include any text before or after the JSON. Do not use markdown code fences.

{
  "classification": "<snake_case_label e.g. predatory_recruitment_debt_bondage, legitimate_recruitment, ambiguous_needs_review, off_topic>",
  "classification_label": "<Short Human-Readable Title 3-7 words>",
  "confidence": <float 0.0 to 1.0 — how confident this classification is>,
  "overall_risk": <float 0.0 to 1.0 — aggregate risk score>,
  "risk_vectors": [
    {
      "dimension": "<one of: ilo_forced_labor_indicators, fee_violation, wage_protection_violation, jurisdictional_evasion, deception, document_retention, isolation, abusive_conditions, debt_bondage, predatory_lending, identity_concealment, vulnerability_targeting>",
      "magnitude": <float 0.0 to 1.0>,
      "direction": "<low | medium | high>",
      "evidence": "<one sentence specific to the content; cite ILO conventions / national statutes if applicable>"
    }
  ],
  "recommended_action": "<one of: allow, log_only, review, escalate_to_ngo, escalate_to_regulator, urgent_safety_referral>",
  "rationale": "<2-3 sentence explanation citing specific statutes / ILO indicators that drove the assessment>",
  "ngo_referrals": [<list of relevant NGO / regulator short names e.g. "POEA", "BP2MI", "IJM", "Polaris", "MfMW HK">]
}

Rules:
- Return AT LEAST ONE risk_vector, even for low-risk content (use direction: "low" + low magnitude).
- magnitude and overall_risk MUST be floats between 0.0 and 1.0.
- confidence reflects YOUR certainty in the classification, not the risk level.
- If the harness output below shows fired GREP rules / retrieved RAG docs / tool results, USE that grounding for the evidence + rationale fields. Cite by rule name / source slug / tool name.
- If the content is NOT about migration / labour / recruitment, classify as "off_topic" with overall_risk: 0.0.
- recommended_action escalation ladder: allow < log_only < review < escalate_to_ngo < escalate_to_regulator < urgent_safety_referral.

Output NOTHING but the JSON object."""


class ClassifyRequest(BaseModel):
    """One content-classification request. `content` is the text to
    classify (raw social-media post, recruitment ad, message thread,
    etc.); `image` is an optional store:// reference to a previously-
    uploaded screenshot. Toggles + custom_* mirror the chat endpoint."""
    content: str
    image: Optional[str] = None
    generation: GenerationParams = Field(default_factory=GenerationParams)
    toggles: HarnessToggles = Field(default_factory=HarnessToggles)


def _resolve_image_ref(img_ref: str) -> Optional[dict]:
    """Resolve a 'store://<id>' image reference to a content chunk."""
    if not img_ref or not img_ref.startswith("store://"):
        return None
    sid = img_ref[len("store://"):]
    item = _IMAGE_STORE.get(sid)
    if item is None:
        return None
    b64 = base64.b64encode(item[0]).decode()
    return {"type": "image", "image": f"data:{item[1]};base64,{b64}"}


def _build_messages(req: ClassifyRequest) -> list[dict]:
    """Build a single-turn user message for the classifier. The
    harness pre-context (persona / GREP / RAG / Tools) gets prepended
    by _run_harness, just like the chat endpoint."""
    content = []
    if req.image:
        img = _resolve_image_ref(req.image)
        if img:
            content.append(img)
    content.append({
        "type": "text",
        "text": ("Classify the following content. Output ONLY the "
                  "JSON object per the schema in the persona above.\n\n"
                  "---CONTENT---\n\n" + req.content),
    })
    return [{"role": "user", "content": content}]


def _strip_to_json(text: str) -> Optional[dict]:
    """Best-effort extract a JSON object from Gemma's response.
    Handles: leading/trailing prose, markdown code fences, trailing
    commas. Returns None if no parseable JSON found."""
    if not text:
        return None
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")
    # Find the first '{' and matching '}'
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return None
    candidate = text[first:last + 1]
    # Try parse as-is
    for tries in range(3):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Common fix: trailing commas before } or ]
            candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
            if tries == 2:
                return None
    return None


def create_classifier_app(
    gemma_call: Optional[Callable] = None,
    model_info: Optional[dict] = None,
    grep_call: Optional[Callable] = None,
    rag_call: Optional[Callable] = None,
    tools_call: Optional[Callable] = None,
    grep_catalog: Optional[list] = None,
    rag_catalog: Optional[list] = None,
    tools_catalog: Optional[list] = None,
    persona_default: Optional[str] = None,
    example_prompts: Optional[list] = None,
    layer_docs: Optional[dict] = None,
) -> FastAPI:
    """Build the content-classifier FastAPI app. Same wiring contract
    as create_app() — the same harness layers + catalogs + examples
    flow through, just with a different persona default and a
    structured-output endpoint."""
    app = FastAPI(
        title="Duecare Content Classifier",
        version="0.1.0",
        description="Structured-output content risk classifier "
                      "powered by Gemma 4 + Duecare safety harness.",
    )
    app.state.gemma_call = gemma_call
    app.state.grep_call = grep_call
    app.state.rag_call = rag_call
    app.state.tools_call = tools_call
    app.state.grep_catalog = grep_catalog
    app.state.rag_catalog = rag_catalog
    app.state.tools_catalog = tools_catalog
    # The classifier OVERRIDES the persona default with a structured-
    # output instruction. The user can still override per-message.
    app.state.persona_default = (persona_default or
                                    CLASSIFIER_PERSONA)
    app.state.example_prompts = example_prompts or []
    app.state.layer_docs = layer_docs or {}
    app.state.model_info = model_info or {
        "loaded": False, "name": None, "display": "no model loaded",
    }

    static_dir = Path(__file__).parent / "classifier_static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)),
                    name="static")

    @app.get("/", response_class=HTMLResponse)
    def root() -> Any:
        idx = static_dir / "index.html"
        if idx.exists():
            return HTMLResponse(idx.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Duecare Content Classifier</h1>"
                              "<p>(static UI not bundled)</p>")

    @app.get("/healthz")
    def healthz() -> Any:
        return {"ok": True, "ts": time.time()}

    @app.get("/api/model-info")
    def api_model_info() -> Any:
        return app.state.model_info

    @app.get("/api/harness-info")
    def api_harness_info() -> Any:
        return {
            "persona": bool(app.state.persona_default),
            "persona_default": app.state.persona_default or "",
            "grep": app.state.grep_call is not None,
            "rag": app.state.rag_call is not None,
            "tools": app.state.tools_call is not None,
        }

    @app.get("/api/harness-catalog/{layer}")
    def api_harness_catalog(layer: str) -> Any:
        if layer not in ("grep", "rag", "tools"):
            raise HTTPException(404, f"unknown layer {layer}")
        catalog = getattr(app.state, f"{layer}_catalog", None)
        if catalog is None:
            return {"layer": layer, "wired": False, "items": [],
                     "note": f"No catalog wired for {layer}."}
        return {"layer": layer, "wired": True, "items": catalog}

    @app.get("/api/docs/{layer}")
    def api_docs(layer: str) -> Any:
        docs = app.state.layer_docs or {}
        if layer not in docs:
            return {"layer": layer, "found": False, "markdown": ""}
        return {"layer": layer, "found": True, "markdown": docs[layer]}

    @app.get("/api/examples")
    def api_examples() -> Any:
        return {"examples": app.state.example_prompts or []}

    @app.post("/api/classifier/upload-image")
    async def api_upload_image(file: UploadFile = File(...)) -> Any:
        data = await file.read()
        if not data:
            raise HTTPException(400, "empty file")
        if len(data) > 12 * 1024 * 1024:
            raise HTTPException(413, "image too large (12 MB cap)")
        mime = file.content_type or "image/png"
        if not mime.startswith("image/"):
            raise HTTPException(400, f"not an image: {mime}")
        sid = uuid4().hex[:12]
        _IMAGE_STORE[sid] = (data, mime)
        if len(_IMAGE_STORE) > 50:
            _IMAGE_STORE.pop(next(iter(_IMAGE_STORE)), None)
        return {"id": sid, "mime": mime, "bytes": len(data)}

    def _run_harness(messages, toggles) -> Any:
        """Same harness logic as chat.app._run_harness, kept inline
        here so the classifier app is self-contained. Captures the
        final merged user-message text for the pipeline view."""
        trace = {
            "persona": {"enabled": toggles.persona,
                          "wired": bool(app.state.persona_default),
                          "fired": False, "elapsed_ms": 0,
                          "text_preview": "", "summary": ""},
            "grep": {"enabled": toggles.grep,
                       "wired": app.state.grep_call is not None,
                       "fired": False, "elapsed_ms": 0,
                       "hits": [], "summary": ""},
            "rag": {"enabled": toggles.rag,
                      "wired": app.state.rag_call is not None,
                      "fired": False, "elapsed_ms": 0,
                      "docs": [], "summary": ""},
            "tools": {"enabled": toggles.tools,
                        "wired": app.state.tools_call is not None,
                        "fired": False, "elapsed_ms": 0,
                        "tool_calls": [], "summary": ""},
        }
        prepend_snippets: list[str] = []
        # Extract last user text
        user_text = ""
        for msg in reversed(messages):
            if msg.get("role") != "user":
                continue
            for chunk in msg.get("content") or []:
                if chunk.get("type") == "text":
                    user_text = chunk.get("text", "")
                    break
            break

        if toggles.persona:
            persona_text = (toggles.persona_text or
                              app.state.persona_default or "").strip()
            if persona_text:
                trace["persona"].update({
                    "fired": True,
                    "text_preview": persona_text[:280] +
                        ("…" if len(persona_text) > 280 else ""),
                    "summary": f"persona prepended ({len(persona_text)} chars)",
                })
                prepend_snippets.append(
                    "## DUECARE PERSONA\n\n" + persona_text + "\n")

        if toggles.grep and app.state.grep_call is not None:
            try:
                try:
                    gr = app.state.grep_call(
                        user_text,
                        extra_rules=toggles.custom_grep_rules) or {}
                except TypeError:
                    gr = app.state.grep_call(user_text) or {}
                hits = gr.get("hits") or []
                trace["grep"].update({
                    "fired": True,
                    "elapsed_ms": int(gr.get("elapsed_ms", 0)),
                    "hits": hits,
                    "summary": (f"{len(hits)} rule(s) fired" if hits
                                  else "no rules fired (clean)"),
                })
                if hits:
                    snippet = ["## SAFETY HARNESS — GREP layer fired\n"]
                    for h in hits:
                        snippet.append(
                            f"- **{h.get('rule')}** [{h.get('severity')}]"
                            f" — {h.get('citation')}")
                    prepend_snippets.append("\n".join(snippet) + "\n")
            except Exception as exc:  # noqa: BLE001
                trace["grep"]["summary"] = f"error: {type(exc).__name__}: {exc}"

        if toggles.rag and app.state.rag_call is not None:
            try:
                try:
                    rr = app.state.rag_call(
                        user_text,
                        extra_docs=toggles.custom_rag_docs) or {}
                except TypeError:
                    rr = app.state.rag_call(user_text) or {}
                docs = rr.get("docs") or []
                trace["rag"].update({
                    "fired": True,
                    "elapsed_ms": int(rr.get("elapsed_ms", 0)),
                    "docs": docs,
                    "summary": f"retrieved {len(docs)} doc(s)",
                })
                if docs:
                    snippet = ["## SAFETY HARNESS — RAG retrieved\n"]
                    for d in docs:
                        snippet.append(
                            f"### {d.get('title')}  ({d.get('source')})\n"
                            f"{d.get('snippet')}\n")
                    prepend_snippets.append("\n".join(snippet) + "\n")
            except Exception as exc:  # noqa: BLE001
                trace["rag"]["summary"] = f"error: {type(exc).__name__}: {exc}"

        if toggles.tools and app.state.tools_call is not None:
            try:
                try:
                    tr = app.state.tools_call(
                        messages,
                        extra_corridor_caps=toggles.custom_corridor_caps,
                        extra_fee_camouflage=toggles.custom_fee_camouflage,
                        extra_ngo_intake=toggles.custom_ngo_intake,
                    ) or {}
                except TypeError:
                    tr = app.state.tools_call(messages) or {}
                calls = tr.get("tool_calls") or []
                trace["tools"].update({
                    "fired": True,
                    "elapsed_ms": int(tr.get("elapsed_ms", 0)),
                    "tool_calls": calls,
                    "summary": (f"{len(calls)} tool call(s)" if calls
                                  else "no tool calls"),
                })
                if calls:
                    snippet = ["## SAFETY HARNESS — Tools layer\n"]
                    for c in calls:
                        snippet.append(
                            f"- `{c.get('name')}({c.get('args')})` -> "
                            f"{c.get('result')}")
                    prepend_snippets.append("\n".join(snippet) + "\n")
            except Exception as exc:  # noqa: BLE001
                trace["tools"]["summary"] = f"error: {type(exc).__name__}: {exc}"

        return {"trace": trace, "prepend_snippets": prepend_snippets,
                 "user_text": user_text}

    @app.post("/api/classifier/evaluate")
    async def api_classifier_evaluate(req: ClassifyRequest) -> Any:
        """Run the harness layers + Gemma + JSON parse, return a
        structured response with the parsed classification, the raw
        text Gemma generated, and the harness trace."""
        gc = app.state.gemma_call
        if gc is None:
            raise HTTPException(503, "no gemma_call wired")

        messages = _build_messages(req)
        harness = _run_harness(messages, req.toggles)
        if harness["prepend_snippets"]:
            harness_text = (
                "[DUECARE SAFETY HARNESS - pre-context for the "
                "classifier. The content to classify follows below.]\n\n"
                + "\n\n".join(harness["prepend_snippets"])
                + "\n\n---\n\n"
            )
            last_msg = dict(messages[-1])
            content = list(last_msg.get("content") or [])
            for i, chunk in enumerate(content):
                if chunk.get("type") == "text":
                    content[i] = {
                        "type": "text",
                        "text": harness_text + (chunk.get("text") or ""),
                    }
                    break
            else:
                content.insert(0, {"type": "text", "text": harness_text})
            last_msg["content"] = content
            messages = messages[:-1] + [last_msg]

        # Capture the final merged user text for the pipeline view
        final_text = ""
        for chunk in messages[-1].get("content") or []:
            if chunk.get("type") == "text":
                final_text = chunk.get("text", "")
                break
        harness["trace"]["_final_user_text"] = final_text

        # Run Gemma in a worker thread + SSE-keepalive the response so
        # cloudflared doesn't 524 on long inferences.
        gp = req.generation
        state: dict[str, Any] = {}

        def worker() -> None:
            t0 = time.time()
            try:
                try:
                    text = gc(messages,
                                max_new_tokens=gp.max_new_tokens,
                                temperature=gp.temperature,
                                top_p=gp.top_p, top_k=gp.top_k)
                except TypeError:
                    text = gc(messages)
                state["raw_text"] = text or ""
            except Exception as exc:  # noqa: BLE001
                state["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                state["elapsed_ms"] = int((time.time() - t0) * 1000)

        wt = threading.Thread(target=worker, daemon=True,
                                name="duecare-classifier-worker")
        wt.start()

        async def event_stream() -> Any:
            t0 = time.time()
            yield (": stream-open\n\n").encode()
            last_keep = time.time()
            while wt.is_alive():
                await asyncio.sleep(0.5)
                if time.time() - last_keep >= 5.0:
                    yield (f": keepalive elapsed={int(time.time()-t0)}s\n\n").encode()
                    last_keep = time.time()
            wt.join()
            if "error" in state:
                payload = {"error": state["error"],
                            "elapsed_ms": state.get("elapsed_ms", 0),
                            "harness_trace": harness["trace"]}
            else:
                raw = state.get("raw_text", "")
                parsed = _strip_to_json(raw)
                payload = {
                    "raw": raw,
                    "parsed": parsed,
                    "parse_ok": parsed is not None,
                    "elapsed_ms": state.get("elapsed_ms", 0),
                    "model_info": app.state.model_info,
                    "harness_trace": harness["trace"],
                }
            yield (f"data: {json.dumps(payload)}\n\n").encode()

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    return app


def run_server(gemma_call=None, model_info=None, host="0.0.0.0",
                port=8080, log_level="warning", **harness_kwargs) -> None:
    import uvicorn
    app = create_classifier_app(gemma_call=gemma_call,
                                  model_info=model_info,
                                  **harness_kwargs)
    uvicorn.run(app, host=host, port=port, log_level=log_level)
