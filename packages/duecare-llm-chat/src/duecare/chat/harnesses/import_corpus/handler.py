"""Import Corpus handler.

Owns:
  - POST   /api/import/upload  -- multipart upload (ZIP / single text)
  - POST   /api/import/snippet -- paste a text snippet
  - GET    /api/import/list    -- metadata for the store
  - GET    /api/import/{doc_id} -- full text of one doc
  - DELETE /api/import/{doc_id} -- remove one doc
  - DELETE /api/import          -- clear the store

State lives in app.py module-level globals (_IMPORT_STORE, _IMPORT_LOCK,
_import_* helpers); this module wires FastAPI routes to them.
"""
from __future__ import annotations

import io
import zipfile
from typing import Any

from fastapi import File, HTTPException, UploadFile


def register_routes(app: Any) -> None:
    from ...app import (
        _IMPORT_LOCK,
        _IMPORT_MAX_DOCS,
        _IMPORT_MAX_DOC_BYTES,
        _IMPORT_MAX_TOTAL_BYTES,
        _IMPORT_STORE,
        _IMPORT_TEXT_EXTENSIONS,
        _import_add,
        _import_decode,
        _import_total_bytes,
    )

    @app.post("/api/import/upload")
    async def api_import_upload(file: UploadFile = File(...)) -> Any:
        """Accept .zip / .txt / .md / .html / .json / .csv etc. upload."""
        data = await file.read()
        if not data:
            raise HTTPException(400, "empty file")
        if len(data) > _IMPORT_MAX_TOTAL_BYTES:
            raise HTTPException(
                413,
                f"upload too large ({len(data)} bytes > "
                f"{_IMPORT_MAX_TOTAL_BYTES} cap)",
            )
        filename = file.filename or "uploaded"
        name_low = filename.lower()
        added: list[dict] = []
        skipped: list[dict] = []

        if name_low.endswith(".zip"):
            try:
                zf = zipfile.ZipFile(io.BytesIO(data))
            except zipfile.BadZipFile:
                raise HTTPException(400, "not a valid zip archive")
            with zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    inner = info.filename
                    inner_low = inner.lower()
                    if not any(inner_low.endswith(ext)
                               for ext in _IMPORT_TEXT_EXTENSIONS):
                        skipped.append({"name": inner, "reason": "non-text extension"})
                        continue
                    if info.file_size > _IMPORT_MAX_DOC_BYTES:
                        skipped.append({"name": inner,
                                        "reason": f"too large ({info.file_size} bytes)"})
                        continue
                    try:
                        raw = zf.read(info)
                    except Exception as exc:  # noqa: BLE001
                        skipped.append({"name": inner, "reason": f"read error: {exc}"})
                        continue
                    text = _import_decode(raw)
                    if not text or not text.strip():
                        skipped.append({"name": inner, "reason": "empty or binary"})
                        continue
                    doc_id = _import_add(
                        title=inner,
                        source=f"from {filename}",
                        text=text,
                    )
                    if doc_id:
                        added.append({"id": doc_id, "title": inner,
                                      "size_bytes": len(text)})
            if not added and not skipped:
                raise HTTPException(400, "zip contained no readable text files")
        else:
            text = _import_decode(data)
            if not text or not text.strip():
                raise HTTPException(
                    400,
                    "file does not appear to be text. ZIP archives are "
                    "extracted automatically; for PDFs / DOCX export "
                    "to .txt or .md first.",
                )
            doc_id = _import_add(
                title=filename,
                source=f"uploaded: {filename}",
                text=text,
            )
            if doc_id:
                added.append({"id": doc_id, "title": filename,
                              "size_bytes": len(text)})

        try:
            from duecare.chat._dc_log import dc_log as _dc
            _dc("import.upload",
                f"{len(added)} added, {len(skipped)} skipped",
                n_added=len(added), n_skipped=len(skipped),
                n_total=len(_IMPORT_STORE),
                total_bytes=_import_total_bytes())
        except Exception:
            pass
        return {
            "added": added,
            "skipped": skipped,
            "n_total": len(_IMPORT_STORE),
            "total_bytes": _import_total_bytes(),
        }

    @app.post("/api/import/snippet")
    def api_import_snippet(req: dict) -> Any:
        """Add one manually-typed text snippet (title + body)."""
        title = ((req or {}).get("title") or "").strip()
        source = ((req or {}).get("source") or "pasted").strip()
        text = ((req or {}).get("text") or "").strip()
        if not title:
            raise HTTPException(400, "title is required")
        if not text:
            raise HTTPException(400, "text is required")
        doc_id = _import_add(title=title, source=source, text=text)
        if not doc_id:
            raise HTTPException(400, "snippet rejected (empty after trim)")
        return {
            "id": doc_id,
            "n_total": len(_IMPORT_STORE),
            "total_bytes": _import_total_bytes(),
        }

    @app.get("/api/import/list")
    def api_import_list() -> Any:
        """Return import-store metadata (text truncated to 240-char preview)."""
        with _IMPORT_LOCK:
            docs = sorted(_IMPORT_STORE.values(),
                          key=lambda d: -d.get("uploaded_at", 0))
            metas = [{
                "id": d["id"],
                "title": d["title"],
                "source": d["source"],
                "size_bytes": d["size_bytes"],
                "uploaded_at": d["uploaded_at"],
                "preview": d["text"][:240],
            } for d in docs]
            total = _import_total_bytes()
        return {
            "docs": metas,
            "n": len(metas),
            "total_bytes": total,
            "max_docs": _IMPORT_MAX_DOCS,
            "max_bytes": _IMPORT_MAX_TOTAL_BYTES,
        }

    @app.get("/api/import/{doc_id}")
    def api_import_get(doc_id: str) -> Any:
        """Return the full body of one imported doc."""
        with _IMPORT_LOCK:
            d = _IMPORT_STORE.get(doc_id)
            if d is None:
                raise HTTPException(404, "imported document not found")
            return dict(d)

    @app.delete("/api/import/{doc_id}")
    def api_import_delete(doc_id: str) -> Any:
        with _IMPORT_LOCK:
            removed = _IMPORT_STORE.pop(doc_id, None)
        return {"ok": removed is not None,
                "n_total": len(_IMPORT_STORE)}

    @app.delete("/api/import")
    def api_import_clear() -> Any:
        with _IMPORT_LOCK:
            _IMPORT_STORE.clear()
        return {"ok": True, "n_total": 0}
