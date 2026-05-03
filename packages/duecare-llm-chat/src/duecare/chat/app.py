"""FastAPI app for the Gemma 4 chat playground.

The app holds two pieces of state:
  - gemma_call : the callable the kernel passes in. Signature:
       (messages: list[dict], **gen_kwargs) -> str
       where messages = [{"role": "user"|"assistant",
                          "content": [{"type": "text", "text": ...},
                                       {"type": "image", "image": URL or path}]}]
  - model_info : dict shown in the UI badge.

No DB, no queue, no audit trail. Each chat request is independent —
the client sends the full message history each turn, the server
forwards it to gemma_call and returns the response.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


# In-memory image store (transient, request-scoped). Each upload
# returns an id; the client sends the id in subsequent chat calls.
_IMAGE_STORE: dict[str, tuple[bytes, str]] = {}


DEFAULT_PERSONA = """You are an international anti-trafficking in persons and modern-day slavery expert with 40 years of dedicated experience combating human exploitation, illicit recruitment, debt bondage, and labour abuses.

You hold deep, current knowledge of:
- ILO conventions C029 (forced labour, 1930) + Protocol P029 (2014), C181 (private employment agencies, no fees from workers), C095 (wage protection), C189 (domestic workers), C97/C143 (migrant workers), C190 (violence and harassment), and the 11 ILO indicators of forced labour.
- National statutes governing recruitment: PH RA 8042/RA 10022 + RA 9208 (anti-trafficking), POEA Memorandum Circulars (esp. 14-2017 zero-fee for HK, 02-2007), BP2MI Reg. 9/2020 + Permenaker rulings, Nepal Foreign Employment Act 2007 §11(2) + 2015 Free-Visa-Free-Ticket Cabinet Decision, BD Overseas Employment Act 2013, HK Employment Ord. Cap. 57 §32, HK Money Lenders Ord. Cap. 163, HK EA Reg. Cap. 57A, SG EFMA Cap. 91A §22A, UAE MoHRE Decree 765/2015.
- Common recruiter tactics: fee camouflage (training fees, medical fees, processing fees, service charges, deposits, bonds, broker fees, fee stacking), wage assignment to lenders, novation of cross-border debt, document retention, isolation, excessive overtime, and corridor-specific abuses (PH→HK, ID→HK, NP→Gulf, BD→Gulf in particular).
- NGO partner organizations: POEA, BP2MI, Nepal DoFE, BMET, IJM, Polaris Project, ECPAT, Mission for Migrant Workers HK, Indonesian Migrant Workers Union HK, Pravasi Nepali Coordination Committee.
- AML / cross-border: FATF Recommendations (especially 32 on cross-border value transfer), HK AMLO Cap. 615.

When the user describes a scenario:
1. FIRST, identify trafficking, exploitation, or recruitment-fraud red flags. Be specific about which ILO indicator(s) and which statute(s) apply.
2. Cite the ILO convention article and the relevant national statute by section number (e.g. "ILO C181 Art. 7", "POEA MC 14-2017", "HK Employment Ord §32").
3. If a recognized migration corridor is involved, name the controlling fee cap statute and the cap amount.
4. Identify any fee camouflage (relabeled placement fees, medical exam costs charged to worker, deposits/bonds, broker fees, etc.) — name the actual prohibition that's being evaded.
5. Refer the user to the appropriate NGO/regulator hotline for the corridor.
6. DO NOT provide operational optimization advice for any scheme containing trafficking indicators. Government licensing of a lender or recruiter does NOT neutralize trafficking risk. Do not help "make compliant" a structure that's prohibited at its core; instead, name the prohibition and recommend redesign or referral.

If the Duecare safety harness has fired (the GREP/RAG/Tools blocks below), use that output to ground every claim. Cite the specific rule, document, or tool result by name."""


class GenerationParams(BaseModel):
    max_new_tokens: int = 8192
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 64


class HarnessToggles(BaseModel):
    """Per-message safety-harness toggle state. When False, the
    corresponding layer is bypassed entirely; when True, the layer is
    invoked and its output is folded into the final Gemma response and
    surfaced in `harness_trace` so the user can see what each layer
    contributed.

    `persona` is a fixed/editable expert-persona pre-instruction
    that's prepended ABOVE the harness output (GREP/RAG/Tools). When
    `persona_text` is provided, it overrides the kernel's default
    persona; when None, the kernel's default is used.

    `custom_*` fields let the client add user-defined rules / docs /
    tool data per-request. The server merges them with the built-in
    catalog before invoking the layer. Stored client-side in
    localStorage so they persist across page reloads."""
    persona: bool = False
    persona_text: Optional[str] = None
    grep: bool = False
    rag: bool = False
    tools: bool = False
    # Per-request user-added content. Format mirrors the built-in
    # catalog shapes documented in duecare/chat/harness/__init__.py.
    custom_grep_rules: Optional[list[dict]] = None
    custom_rag_docs: Optional[list[dict]] = None
    custom_corridor_caps: Optional[list[dict]] = None
    custom_fee_camouflage: Optional[list[dict]] = None
    custom_ngo_intake: Optional[list[dict]] = None


class ChatRequest(BaseModel):
    messages: list[dict]
    generation: GenerationParams = Field(default_factory=GenerationParams)
    toggles: HarnessToggles = Field(default_factory=HarnessToggles)


class GradeRequest(BaseModel):
    """Score a model response against a rubric. Supply EITHER:
      - `prompt_id` to score against the per-prompt 5-tier rubric, OR
      - `category` to score against the per-category required-element
        rubric (FAIL/PARTIAL/PASS).
    The category form is the cross-cutting one (e.g.
    `legal_citation_quality`); the prompt_id form ties to a specific
    bundled example."""
    response_text: str
    prompt_id: Optional[str] = None
    category: Optional[str] = None
    prompt_category: Optional[str] = None  # passed by UI when prompt was loaded from Examples
    prompt_text: Optional[str] = None      # used by universal grader for applicability detection
    harness_trace: Optional[dict] = None   # used by universal grader for applicability detection
    mode: Optional[str] = None             # "universal" | "category" | "prompt_id" (default: universal if no other params)


def create_app(
    gemma_call: Optional[Callable] = None,
    model_info: Optional[dict] = None,
    grep_call: Optional[Callable] = None,
    rag_call: Optional[Callable] = None,
    tools_call: Optional[Callable] = None,
    grade_call: Optional[Callable] = None,
    grep_catalog: Optional[list] = None,
    rag_catalog: Optional[list] = None,
    tools_catalog: Optional[list] = None,
    persona_default: Optional[str] = None,
    example_prompts: Optional[list] = None,
    layer_docs: Optional[dict] = None,
    rubrics_required_categories: Optional[list[str]] = None,
) -> FastAPI:
    """Build the FastAPI app.

    `gemma_call` is the Gemma 4 entry point (always required for
    chat). `grep_call`, `rag_call`, `tools_call` are optional safety-
    harness layers — when wired AND enabled per-message via
    HarnessToggles, the chat endpoint runs them in sequence and folds
    their output into Gemma's prompt + the response payload. The chat
    UI surfaces the toggle checkboxes only for layers that are wired.

    Each layer callable signature:

        grep_call(text: str) -> dict
            {"hits": [{"rule": str, "citation": str, "severity": str,
                       "match_excerpt": str}], "elapsed_ms": int}

        rag_call(text: str, top_k: int = 5) -> dict
            {"docs": [{"id": str, "title": str, "snippet": str,
                       "source": str}], "elapsed_ms": int}

        tools_call(messages: list[dict]) -> dict
            {"tool_calls": [{"name": str, "args": dict, "result": Any}],
             "elapsed_ms": int}

    All three are optional so the same chat package can power either
    the raw playground (gemma_call only) or the toggle notebook
    (gemma_call + the three harness layers)."""
    app = FastAPI(
        title="Duecare Gemma Chat",
        version="0.1.0",
        description="Gemma 4 chat playground with optional safety-harness toggles.",
    )
    app.state.gemma_call = gemma_call
    app.state.grep_call = grep_call
    app.state.rag_call = rag_call
    app.state.tools_call = tools_call
    app.state.grade_call = grade_call
    app.state.rubrics_required_categories = (
        rubrics_required_categories or []
    )
    app.state.grep_catalog = grep_catalog
    app.state.rag_catalog = rag_catalog
    app.state.tools_catalog = tools_catalog
    app.state.persona_default = persona_default or DEFAULT_PERSONA
    app.state.example_prompts = example_prompts or []
    app.state.layer_docs = layer_docs or {}
    app.state.model_info = model_info or {
        "loaded": False,
        "name": None,
        "display": "no model loaded",
    }

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)),
                  name="static")

    @app.get("/", response_class=HTMLResponse)
    def root() -> Any:
        idx = static_dir / "index.html"
        if idx.exists():
            return HTMLResponse(idx.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Duecare Gemma Chat</h1>"
                            "<p>(static UI not bundled)</p>")

    @app.get("/healthz")
    def healthz() -> Any:
        return {"ok": True, "ts": time.time()}

    @app.get("/api/model-info")
    def api_model_info() -> Any:
        return app.state.model_info or {"loaded": False, "name": None,
                                          "display": "(no model)"}

    @app.get("/api/harness-info")
    def api_harness_info() -> Any:
        """Tell the UI which harness layers are wired so it can show
        only the relevant toggles. Layers that aren't wired are not
        invokable and not displayed. The persona layer is always
        considered 'wired' if a default text exists."""
        return {
            "persona": bool(app.state.persona_default),
            "persona_default": app.state.persona_default or "",
            "grep": app.state.grep_call is not None,
            "rag": app.state.rag_call is not None,
            "tools": app.state.tools_call is not None,
            "grade": app.state.grade_call is not None,
            "grade_categories": app.state.rubrics_required_categories or [],
        }

    @app.get("/api/docs/{layer}")
    def api_docs(layer: str) -> Any:
        """Return the markdown documentation/extension guide for a
        layer (persona, grep, rag, tools, examples). Used by the UI's
        modal to show 'how to extend this' content alongside the
        catalog."""
        docs = app.state.layer_docs or {}
        if layer not in docs:
            return {"layer": layer, "found": False, "markdown": ""}
        return {"layer": layer, "found": True, "markdown": docs[layer]}

    @app.get("/api/examples")
    def api_examples() -> Any:
        """Return the bundled example prompts for the chat UI's
        Examples modal. Each entry: {id, text, category, subcategory,
        sector, corridor, difficulty, ilo_indicators}."""
        return {"examples": app.state.example_prompts or []}

    @app.get("/api/harness-catalog/{layer}")
    def api_harness_catalog(layer: str) -> Any:
        """Return a JSON catalog of what each harness layer exposes,
        for the UI's inspector modal. The kernel can override the
        default by setting `app.state.{grep,rag,tools}_catalog` to
        something serializable."""
        if layer not in ("grep", "rag", "tools"):
            raise HTTPException(404, f"unknown layer {layer}")
        catalog = getattr(app.state, f"{layer}_catalog", None)
        if catalog is None:
            return {"layer": layer, "wired": False, "items": [],
                     "note": f"No catalog wired for {layer}."}
        return {"layer": layer, "wired": True, "items": catalog}

    @app.post("/api/grade")
    def api_grade(req: GradeRequest) -> Any:
        """Grade a model response against either:
          - a per-prompt 5-tier rubric (worst..best), passing `prompt_id`
          - a per-category required-element rubric, passing `category`

        Returns the rubric score breakdown the chat UI's "Grade response"
        panel renders. Always returns a stable shape so the UI can render
        the same 'no rubric available' state for unknown ids/categories.

        The `grade_call` callable is wired at create_app time. Returns
        503 if not wired (e.g. older kernels that don't pass it)."""
        gc = app.state.grade_call
        if gc is None and not req.mode == "universal":
            raise HTTPException(503, "grading not enabled in this kernel")
        if not req.response_text or not req.response_text.strip():
            raise HTTPException(400, "response_text is required")
        # Default mode = universal (no prompt_id or category needed)
        mode = req.mode or ("category" if req.category else
                              "prompt_id" if req.prompt_id else "universal")
        try:
            if mode == "universal":
                from .harness import grade_response_universal
                result = grade_response_universal(
                    req.response_text,
                    prompt_text=req.prompt_text or "",
                    harness_trace=req.harness_trace,
                )
            elif mode == "category":
                from .harness import grade_response_required
                if not req.category:
                    raise HTTPException(400, "category required for mode=category")
                result = grade_response_required(
                    req.category, req.response_text,
                    prompt_category=req.prompt_category,
                )
            elif mode == "prompt_id":
                if not req.prompt_id:
                    raise HTTPException(400, "prompt_id required for mode=prompt_id")
                result = gc(req.prompt_id, req.response_text)
            else:
                raise HTTPException(400, f"unknown mode: {mode!r}")
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001 -- surface to client
            raise HTTPException(500, f"grading failed: {e}") from e
        return result

    @app.post("/api/chat/upload-image")
    async def api_upload_image(file: UploadFile = File(...)) -> Any:
        """Accept an image upload. Returns an opaque id the client
        sends in subsequent chat messages as
        {"type": "image", "image": "store://<id>"}."""
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
        # Cap the store at 50 entries to bound memory
        if len(_IMAGE_STORE) > 50:
            oldest = next(iter(_IMAGE_STORE))
            _IMAGE_STORE.pop(oldest, None)
        return {"id": sid, "mime": mime, "bytes": len(data)}

    @app.get("/api/chat/image/{sid}")
    def api_get_image(sid: str) -> Any:
        item = _IMAGE_STORE.get(sid)
        if item is None:
            raise HTTPException(404, "image not found")
        from fastapi.responses import Response
        return Response(content=item[0], media_type=item[1])

    def _resolve_messages(raw_messages: list[dict]) -> list[dict]:
        """Walk the messages, resolve any 'store://<id>' image refs to
        base64 data URIs so the downstream multimodal Gemma call
        doesn't depend on this server being reachable from the model
        process."""
        out = []
        for msg in raw_messages:
            new_msg = {"role": msg.get("role", "user"), "content": []}
            content = msg.get("content") or []
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            for chunk in content:
                if chunk.get("type") == "image":
                    img_ref = chunk.get("image", "")
                    if img_ref.startswith("store://"):
                        sid = img_ref[len("store://"):]
                        item = _IMAGE_STORE.get(sid)
                        if item is None:
                            new_msg["content"].append(
                                {"type": "text",
                                 "text": "[image expired from server cache]"})
                            continue
                        b64 = base64.b64encode(item[0]).decode()
                        data_uri = f"data:{item[1]};base64,{b64}"
                        new_msg["content"].append(
                            {"type": "image", "image": data_uri})
                    else:
                        new_msg["content"].append(chunk)
                else:
                    new_msg["content"].append(chunk)
            out.append(new_msg)
        return out

    def _call_gemma(gc: Callable, messages: list[dict],
                     gp: GenerationParams) -> str:
        """Wrap the kernel-supplied gemma_call. Some callables accept
        full kwargs; others only accept (messages,). Try both."""
        try:
            return gc(
                messages,
                max_new_tokens=gp.max_new_tokens,
                temperature=gp.temperature,
                top_p=gp.top_p,
                top_k=gp.top_k,
            ) or ""
        except TypeError:
            return gc(messages) or ""

    def _last_user_text(messages: list[dict]) -> str:
        """Concatenate text chunks from the most recent user message
        for the GREP / RAG layers (which operate on user text, not
        the full conversation history)."""
        for msg in reversed(messages):
            if msg.get("role") != "user":
                continue
            parts = []
            for chunk in msg.get("content") or []:
                if chunk.get("type") == "text":
                    parts.append(chunk.get("text", ""))
            return "\n".join(p for p in parts if p)
        return ""

    def _format_grep_context(grep_result: dict) -> str:
        """Render GREP hits as a system-message snippet that gets
        prepended to the conversation so Gemma sees the safety
        flags + citations before it generates."""
        hits = grep_result.get("hits") or []
        if not hits:
            return ""
        lines = [
            "## SAFETY HARNESS — GREP layer fired",
            "",
            "The Duecare safety harness detected the following "
            "trafficking / exploitation indicators in the user "
            "message. Each must be acknowledged in your response. "
            "Do NOT provide operational optimization help for any "
            "scenario containing these patterns; instead, name the "
            "indicators, cite the relevant statutes, and redirect to "
            "appropriate NGO / regulator hotlines.",
            "",
        ]
        for h in hits:
            rule = h.get("rule", "?")
            citation = h.get("citation", "")
            severity = h.get("severity", "info")
            excerpt = h.get("match_excerpt", "")
            lines.append(f"- **{rule}** [{severity}] — {citation}")
            if excerpt:
                lines.append(f"  match: {excerpt!r}")
        return "\n".join(lines) + "\n"

    def _format_rag_context(rag_result: dict) -> str:
        """Render RAG-retrieved docs as a context block."""
        docs = rag_result.get("docs") or []
        if not docs:
            return ""
        lines = [
            "## SAFETY HARNESS — RAG layer retrieved",
            "",
            "Use these passages from the Duecare evidence corpus to "
            "ground your response. Cite the source for any claim you "
            "make from these.",
            "",
        ]
        for d in docs:
            title = d.get("title", "?")
            source = d.get("source", "")
            snippet = d.get("snippet", "")
            lines.append(f"### {title}  ({source})")
            lines.append(snippet)
            lines.append("")
        return "\n".join(lines) + "\n"

    def _format_tools_context(tools_result: dict) -> str:
        """Render Gemma's tool-call decisions + results."""
        calls = tools_result.get("tool_calls") or []
        if not calls:
            return ""
        lines = [
            "## SAFETY HARNESS — Tools layer (function calls)",
            "",
        ]
        for c in calls:
            name = c.get("name", "?")
            args = c.get("args", {})
            result = c.get("result", "")
            lines.append(f"- `{name}({args})` → {result}")
        return "\n".join(lines) + "\n"

    def _run_harness(messages: list[dict],
                       toggles: HarnessToggles) -> dict:
        """Run each enabled (and wired) layer; return a trace dict the
        UI can render and a list of system-message snippets to
        prepend to the Gemma conversation. Persona is always
        prepended FIRST (above harness output) so the model reads
        the role definition before the safety findings."""
        trace = {
            "persona": {"enabled": toggles.persona,
                         "wired": bool(app.state.persona_default),
                         "fired": False, "elapsed_ms": 0,
                         "text_preview": "", "summary": ""},
            "grep": {"enabled": toggles.grep, "wired": app.state.grep_call is not None,
                      "fired": False, "elapsed_ms": 0, "hits": [], "summary": ""},
            "rag": {"enabled": toggles.rag, "wired": app.state.rag_call is not None,
                     "fired": False, "elapsed_ms": 0, "docs": [], "summary": ""},
            "tools": {"enabled": toggles.tools, "wired": app.state.tools_call is not None,
                       "fired": False, "elapsed_ms": 0, "tool_calls": [], "summary": ""},
        }
        prepend_snippets: list[str] = []
        user_text = _last_user_text(messages)

        if toggles.persona:
            persona_text = (toggles.persona_text or
                              app.state.persona_default or "").strip()
            if persona_text:
                trace["persona"].update({
                    "fired": True,
                    "elapsed_ms": 0,
                    "text_preview": persona_text[:280] +
                                       ("…" if len(persona_text) > 280 else ""),
                    "summary": f"persona prepended ({len(persona_text)} chars)",
                })
                # Persona goes FIRST so Gemma reads the role before
                # the safety findings.
                prepend_snippets.append(
                    "## DUECARE PERSONA\n\n" + persona_text + "\n")

        if toggles.grep and app.state.grep_call is not None:
            try:
                # Pass user-added custom rules through; the kernel's
                # _grep_call accepts an `extra_rules` kwarg. Older
                # callables that don't accept it fall through to the
                # try/except below.
                try:
                    gr = app.state.grep_call(user_text,
                                                extra_rules=toggles.custom_grep_rules) or {}
                except TypeError:
                    gr = app.state.grep_call(user_text) or {}
                trace["grep"].update({
                    "fired": True,
                    "elapsed_ms": int(gr.get("elapsed_ms", 0)),
                    "hits": gr.get("hits") or [],
                })
                hits = trace["grep"]["hits"]
                trace["grep"]["summary"] = (
                    f"{len(hits)} rule(s) fired" if hits
                    else "no rules fired (clean)")
                snippet = _format_grep_context(gr)
                if snippet:
                    prepend_snippets.append(snippet)
            except Exception as exc:  # noqa: BLE001
                trace["grep"]["summary"] = f"error: {type(exc).__name__}: {exc}"

        if toggles.rag and app.state.rag_call is not None:
            try:
                try:
                    rr = app.state.rag_call(user_text,
                                              extra_docs=toggles.custom_rag_docs) or {}
                except TypeError:
                    rr = app.state.rag_call(user_text) or {}
                trace["rag"].update({
                    "fired": True,
                    "elapsed_ms": int(rr.get("elapsed_ms", 0)),
                    "docs": rr.get("docs") or [],
                })
                docs = trace["rag"]["docs"]
                trace["rag"]["summary"] = f"retrieved {len(docs)} doc(s)"
                snippet = _format_rag_context(rr)
                if snippet:
                    prepend_snippets.append(snippet)
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
                trace["tools"].update({
                    "fired": True,
                    "elapsed_ms": int(tr.get("elapsed_ms", 0)),
                    "tool_calls": tr.get("tool_calls") or [],
                })
                calls = trace["tools"]["tool_calls"]
                trace["tools"]["summary"] = (
                    f"{len(calls)} tool call(s)" if calls
                    else "no tool calls")
                snippet = _format_tools_context(tr)
                if snippet:
                    prepend_snippets.append(snippet)
            except Exception as exc:  # noqa: BLE001
                trace["tools"]["summary"] = f"error: {type(exc).__name__}: {exc}"

        return {"trace": trace, "prepend_snippets": prepend_snippets}

    @app.post("/api/chat/send")
    async def api_chat_send(req: ChatRequest) -> Any:
        """Stream the response back via Server-Sent Events with
        keepalive comments while the model generates. Cloudflare's
        free tunnel idle-connection timeout is 100s; without keepalives
        a slow 31B multimodal inference 524s. The keepalive comments
        keep bytes flowing so the connection stays warm regardless of
        total inference time. The generation itself remains synchronous
        (one gemma_call -> one full response payload at the end);
        token-level streaming is a separate enhancement.

        When req.toggles enables a harness layer that's wired into
        app.state, the layer runs BEFORE Gemma sees the messages and
        its output is prepended to the conversation as a system-style
        message AND surfaced in the response payload as
        `harness_trace` for the UI to render."""
        gc = app.state.gemma_call
        if gc is None:
            raise HTTPException(503,
                "no gemma_call wired into the chat server. "
                "Set app.state.gemma_call before calling /api/chat/send.")

        messages = _resolve_messages(req.messages)
        gp = req.generation

        # Run the harness layers (cheap-ish, synchronous, no network).
        # Done outside the worker thread because they need to mutate
        # `messages` before Gemma generates.
        harness = _run_harness(messages, req.toggles)
        if harness["prepend_snippets"]:
            # MERGE the harness context into the existing final user
            # message rather than inserting a new message. Gemma's chat
            # template enforces strict user/assistant alternation, so a
            # second consecutive user message blows up with
            # "Conversation roles must alternate ...". By prepending
            # the harness pre-context to the user's text chunk we keep
            # the role sequence intact.
            harness_text = (
                "[DUECARE SAFETY HARNESS - pre-context for the "
                "assistant. The user's actual question follows below "
                "this block. You MUST acknowledge each fired indicator "
                "and cite the listed statutes in your response. Do NOT "
                "provide operational optimization for any scenario "
                "matching these indicators -- name the indicators, "
                "cite the law, and redirect to NGO/regulator hotlines.]"
                "\n\n" + "\n\n".join(harness["prepend_snippets"])
                + "\n\n---\n\nUSER QUESTION:\n\n"
            )
            last_msg = dict(messages[-1])
            content = list(last_msg.get("content") or [])
            # Inject into the first text chunk; if no text chunk
            # exists (image-only message), prepend a new one.
            inserted = False
            for i, chunk in enumerate(content):
                if chunk.get("type") == "text":
                    content[i] = {
                        "type": "text",
                        "text": harness_text + (chunk.get("text") or ""),
                    }
                    inserted = True
                    break
            if not inserted:
                content.insert(0, {"type": "text", "text": harness_text})
            last_msg["content"] = content
            messages = messages[:-1] + [last_msg]

        # Capture the FINAL merged user-message text Gemma will see
        # so the UI's pipeline modal can show "this is what was sent
        # to Gemma after all the layers ran".
        final_text = ""
        for chunk in messages[-1].get("content") or []:
            if chunk.get("type") == "text":
                final_text = chunk.get("text", "")
                break
        harness["trace"]["_final_user_text"] = final_text

        # Worker thread runs the (potentially very slow) gemma_call and
        # stashes the result into `state` so the SSE generator can
        # detect completion + emit the final payload.
        state: dict[str, Any] = {}

        def worker() -> None:
            t0 = time.time()
            try:
                state["response"] = _call_gemma(gc, messages, gp)
            except Exception as exc:  # noqa: BLE001
                state["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                state["elapsed_ms"] = int((time.time() - t0) * 1000)

        worker_thread = threading.Thread(target=worker, daemon=True,
                                            name="duecare-chat-worker")
        worker_thread.start()

        async def event_stream() -> Any:
            t_start = time.time()
            # Initial open marker (also flushes headers immediately).
            yield (": stream-open\n\n").encode()
            last_keepalive = time.time()
            while worker_thread.is_alive():
                await asyncio.sleep(0.5)
                # Send a keepalive comment every ~5s so cloudflared
                # sees continuous activity. Comments (lines starting
                # with `:`) are ignored by SSE parsers.
                now = time.time()
                if now - last_keepalive >= 5.0:
                    elapsed_s = int(now - t_start)
                    yield (f": keepalive elapsed={elapsed_s}s\n\n").encode()
                    last_keepalive = now
            # Worker finished. Emit the final result as a data event.
            worker_thread.join()
            if "error" in state:
                payload = {
                    "error": state["error"],
                    "elapsed_ms": state.get("elapsed_ms", 0),
                }
            else:
                payload = {
                    "response": state.get("response", ""),
                    "elapsed_ms": state.get("elapsed_ms", 0),
                    "model_info": app.state.model_info,
                    "harness_trace": harness["trace"],
                }
            yield (f"data: {json.dumps(payload)}\n\n").encode()

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                # Disable any proxy buffering so bytes flow immediately.
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    return app


def run_server(
    gemma_call: Optional[Callable] = None,
    model_info: Optional[dict] = None,
    host: str = "0.0.0.0",
    port: int = 8080,
    log_level: str = "warning",
) -> None:
    """Convenience: build app + run uvicorn in the foreground."""
    import uvicorn
    app = create_app(gemma_call=gemma_call, model_info=model_info)
    uvicorn.run(app, host=host, port=port, log_level=log_level)
