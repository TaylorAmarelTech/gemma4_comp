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

import base64
import os
import time
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


# In-memory image store (transient, request-scoped). Each upload
# returns an id; the client sends the id in subsequent chat calls.
_IMAGE_STORE: dict[str, tuple[bytes, str]] = {}


class GenerationParams(BaseModel):
    max_new_tokens: int = 512
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 64


class ChatRequest(BaseModel):
    messages: list[dict]
    generation: GenerationParams = Field(default_factory=GenerationParams)


def create_app(
    gemma_call: Optional[Callable] = None,
    model_info: Optional[dict] = None,
) -> FastAPI:
    """Build the FastAPI app.

    `gemma_call` and `model_info` are optional so the app can be
    imported without a model (useful for static-asset checks).
    Update them later via `app.state.gemma_call = ...` and
    `app.state.model_info = ...`."""
    app = FastAPI(
        title="Duecare Gemma Chat",
        version="0.1.0",
        description="Minimal Gemma 4 chat playground.",
    )
    app.state.gemma_call = gemma_call
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
    def root():
        idx = static_dir / "index.html"
        if idx.exists():
            return HTMLResponse(idx.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Duecare Gemma Chat</h1>"
                            "<p>(static UI not bundled)</p>")

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "ts": time.time()}

    @app.get("/api/model-info")
    def api_model_info():
        return app.state.model_info or {"loaded": False, "name": None,
                                          "display": "(no model)"}

    @app.post("/api/chat/upload-image")
    async def api_upload_image(file: UploadFile = File(...)):
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
    def api_get_image(sid: str):
        item = _IMAGE_STORE.get(sid)
        if item is None:
            raise HTTPException(404, "image not found")
        from fastapi.responses import Response
        return Response(content=item[0], media_type=item[1])

    @app.post("/api/chat/send")
    def api_chat_send(req: ChatRequest):
        """Forward messages to gemma_call and return the response."""
        gc = app.state.gemma_call
        if gc is None:
            raise HTTPException(503,
                "no gemma_call wired into the chat server. "
                "Set app.state.gemma_call before calling /api/chat/send.")

        # Resolve any "store://<id>" image references to data URIs so
        # the underlying multimodal Gemma call can consume them
        # without depending on this server being reachable.
        messages = []
        for msg in req.messages:
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
            messages.append(new_msg)

        gp = req.generation
        t0 = time.time()
        try:
            text = gc(
                messages,
                max_new_tokens=gp.max_new_tokens,
                temperature=gp.temperature,
                top_p=gp.top_p,
                top_k=gp.top_k,
            )
        except TypeError:
            # Fall back: callable might only accept (messages,)
            text = gc(messages)
        elapsed = int((time.time() - t0) * 1000)
        return {"response": text or "", "elapsed_ms": elapsed,
                "model_info": app.state.model_info}

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
