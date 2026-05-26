"""Chat send orchestrator (Phase 5b).

``serve_chat_send`` is the body of /api/chat/send extracted out of
create_app. It takes the orchestration helpers (resolve_messages,
call_gemma, run_harness) as keyword arguments so it can live in a
sibling module without monkey-patching the closure scope.
"""
from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from typing import Any, Callable

from fastapi.responses import StreamingResponse

try:  # single source of truth for the per-call wall-clock cap
    from ...inference_queue import MAX_INFERENCE_SECONDS
except Exception:  # pragma: no cover - defensive: keep streaming usable
    MAX_INFERENCE_SECONDS = 45 * 60


async def serve_chat_send(
    req: Any,
    *,
    gemma_call: Callable,
    model_info: dict,
    resolve_messages: Callable[[list[dict]], list[dict]],
    call_gemma: Callable,
    run_harness: Callable,
    dc_log: Callable | None = None,
) -> StreamingResponse:
    """Stream the response via Server-Sent Events with keepalive comments."""

    if dc_log is not None:
        try:
            _last_msg = ""
            for _m in (req.messages or []):
                if isinstance(_m, dict) and _m.get("role") == "user":
                    for _c in _m.get("content") or []:
                        if isinstance(_c, dict) and _c.get("type") == "text":
                            _last_msg = (_c.get("text") or "")[:120]
            dc_log("chat.send", _last_msg or "(no text)",
                   toggles=dict(req.toggles or {}),
                   n_messages=len(req.messages or []))
        except Exception:
            pass

    raw_messages_in = req.messages
    gp = req.generation
    toggles_snapshot = req.toggles

    progress_q: "queue.Queue[dict]" = queue.Queue()
    state: dict[str, Any] = {}

    def worker() -> None:
        try:
            progress_q.put_nowait({"type": "step_start", "step": "resolve"})
            _t0 = time.time()
            messages = resolve_messages(raw_messages_in)
            _n_imgs = 0
            for _m in messages or []:
                if isinstance(_m, dict):
                    for _c in _m.get("content") or []:
                        if (isinstance(_c, dict)
                                and _c.get("type") in ("image", "image_url")):
                            _n_imgs += 1
            _resolve_summary = (
                f"{_n_imgs} image reference{'s' if _n_imgs != 1 else ''} resolved"
                if _n_imgs else "no images attached this turn"
            )
            progress_q.put_nowait({
                "type": "step_done", "step": "resolve",
                "elapsed_ms": int((time.time() - _t0) * 1000),
                "summary": _resolve_summary,
                "fired": _n_imgs > 0, "wired": True, "enabled": True,
            })

            harness = run_harness(
                messages, toggles_snapshot,
                progress_callback=progress_q.put_nowait,
            )
            if harness["prepend_snippets"]:
                harness_text = (
                    "[DUECARE SAFETY HARNESS - pre-context for the "
                    "assistant. The user's actual question follows below "
                    "this block. Return only the final answer, not hidden "
                    "reasoning. You MUST acknowledge each fired indicator "
                    "and cite the listed statutes in your response. Start "
                    "with a direct answer. Then name the canonical pattern, "
                    "explain substance over form, cite origin law, "
                    "destination law, and international standards when "
                    "available, and provide safe next steps. Do NOT provide "
                    "operational optimization for any scenario matching "
                    "these indicators. For worker complaint advice, include "
                    "both formal protection from retaliation and practical "
                    "retaliation risk, then recommend trusted support, safe "
                    "reporting, and evidence preservation. Use the contacts "
                    "tool or vetted contacts pack for volatile phone numbers, "
                    "URLs, office names, and hotlines.]"
                    "\n\n" + "\n\n".join(harness["prepend_snippets"])
                    + "\n\n---\n\nUSER QUESTION:\n\n"
                )
                last_msg = dict(messages[-1])
                content = list(last_msg.get("content") or [])
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

            final_text = ""
            for chunk in messages[-1].get("content") or []:
                if chunk.get("type") == "text":
                    final_text = chunk.get("text", "")
                    break
            harness["trace"]["_final_user_text"] = final_text

            progress_q.put_nowait({"type": "step_start", "step": "model"})
            _t0 = time.time()
            response_text = call_gemma(gemma_call, messages, gp)
            model_ms = int((time.time() - _t0) * 1000)
            progress_q.put_nowait({
                "type": "step_done", "step": "model",
                "elapsed_ms": model_ms,
                "summary": f"generated {len(response_text)} chars",
                "fired": True, "wired": True, "enabled": True,
            })

            state["response"]      = response_text
            state["elapsed_ms"]    = model_ms
            state["harness_trace"] = harness["trace"]
            if dc_log is not None:
                try:
                    _trace = harness.get("trace") or []
                    _layers = []
                    for _t in _trace:
                        if isinstance(_t, dict):
                            _ln = _t.get("layer") or _t.get("name")
                            if _ln: _layers.append(_ln)
                    dc_log("chat.reply",
                           f"{len(response_text)} chars in {model_ms}ms",
                           elapsed_ms=int(model_ms),
                           response_chars=len(response_text),
                           layers_fired=_layers)
                except Exception:
                    pass
            progress_q.put_nowait({
                "type":          "complete",
                "response":      response_text,
                "elapsed_ms":    model_ms,
                "model_info":    model_info,
                "harness_trace": harness["trace"],
            })
            try:
                from .._training_log import log_interaction as _log
                _layer_trace = harness.get("trace") or {}
                _applied = {k: {"fired": v.get("fired"), "enabled": v.get("enabled")}
                            for k, v in _layer_trace.items()
                            if isinstance(v, dict)}
                _log(
                    "chat",
                    input_payload=raw_messages_in,
                    output_payload=response_text,
                    applied_layers=_applied,
                    trace=_layer_trace,
                    extra={"model_info": model_info, "elapsed_ms": model_ms},
                )
            except Exception:
                pass
        except Exception as exc:  # noqa: BLE001
            state["error"] = f"{type(exc).__name__}: {exc}"
            progress_q.put_nowait({"type": "error", "error": state["error"]})

    worker_thread = threading.Thread(
        target=worker, daemon=True, name="duecare-chat-worker"
    )
    worker_thread.start()

    async def event_stream() -> Any:
        yield (": stream-open\n\n").encode()
        t_start = time.time()
        last_keepalive = t_start
        while True:
            try:
                evt = progress_q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.25)
                now = time.time()
                if now - t_start >= MAX_INFERENCE_SECONDS:
                    # Hard per-call wall-clock cap (single source of truth:
                    # inference_queue.MAX_INFERENCE_SECONDS). The worker is a
                    # daemon thread running a non-cancellable CUDA generate;
                    # we stop streaming and emit a structured timeout so the
                    # client records an unsuccessful call instead of waiting
                    # on a possibly-hung generate. The slot's call_lock stays
                    # held until generate actually returns -- the cap bounds
                    # the CLIENT's wait, it cannot kill the kernel-side call.
                    timeout_evt = {
                        "type": "error",
                        "error": (
                            f"inference exceeded the "
                            f"{MAX_INFERENCE_SECONDS // 60}-minute per-call cap"
                        ),
                        "reason": "inference_timeout",
                        "code": 504,
                        "elapsed_s": int(now - t_start),
                    }
                    yield (f"data: {json.dumps(timeout_evt)}\n\n").encode()
                    return
                if now - last_keepalive >= 5.0:
                    elapsed_s = int(now - t_start)
                    yield (f": keepalive elapsed={elapsed_s}s\n\n").encode()
                    last_keepalive = now
                if not worker_thread.is_alive() and progress_q.empty():
                    yield (f"data: {json.dumps({'error': 'worker exited unexpectedly'})}\n\n").encode()
                    return
                continue
            yield (f"data: {json.dumps(evt)}\n\n").encode()
            if evt.get("type") in ("complete", "error"):
                return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
