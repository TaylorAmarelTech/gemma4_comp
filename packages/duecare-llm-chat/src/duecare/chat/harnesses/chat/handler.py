"""Chat harness handler -- image endpoints (Phase 5a)."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import File, HTTPException, UploadFile
from fastapi.responses import Response


_MAX_IMAGE_BYTES = 12 * 1024 * 1024
_LRU_MAX = 50


def register_routes(app: Any) -> None:
    from ...app import _IMAGE_STORE, _IMAGE_STORE_LOCK

    @app.post("/api/chat/upload-image")
    async def api_upload_image(file: UploadFile = File(...)) -> Any:
        """Accept an image upload. Returns an opaque id the client sends
        as ``{"type": "image", "image": "store://<id>"}``."""
        data = await file.read()
        if not data:
            raise HTTPException(400, "empty file")
        if len(data) > _MAX_IMAGE_BYTES:
            raise HTTPException(413, "image too large (12 MB cap)")
        mime = file.content_type or "image/png"
        if not mime.startswith("image/"):
            raise HTTPException(400, f"not an image: {mime}")
        sid = uuid4().hex[:12]
        with _IMAGE_STORE_LOCK:
            _IMAGE_STORE[sid] = (data, mime)
            while len(_IMAGE_STORE) > _LRU_MAX:
                oldest = next(iter(list(_IMAGE_STORE)))
                _IMAGE_STORE.pop(oldest, None)
        return {"id": sid, "mime": mime, "bytes": len(data)}

    @app.get("/api/chat/image/{sid}")
    def api_get_image(sid: str) -> Any:
        """Fetch a previously uploaded image by opaque id."""
        with _IMAGE_STORE_LOCK:
            item = _IMAGE_STORE.get(sid)
        if item is None:
            raise HTTPException(404, "image not found")
        return Response(content=item[0], media_type=item[1])
