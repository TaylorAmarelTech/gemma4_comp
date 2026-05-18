"""Small helpers for demo replay metadata.

The API responses remain the source of truth for full outputs.  These
helpers add a compact, privacy-aware replay description so recording
sessions can show how to reproduce a call without depending on the
browser activity log alone.
"""
from __future__ import annotations

import hashlib
import json as _json
from datetime import UTC as _UTC, datetime as _dt
from typing import Any


def sha256_json(value: Any) -> str:
    blob = _json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8", errors="replace")).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()


def demo_replay(
    *,
    lane: str,
    endpoint: str,
    method: str = "POST",
    request: dict[str, Any] | None = None,
    response_summary: dict[str, Any] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    request = request or {}
    return {
        "schema_version": "duecare.demo_replay.v1",
        "captured_at": _dt.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": lane,
        "method": method.upper(),
        "endpoint": endpoint,
        "request": request,
        "request_sha256": sha256_json(request),
        "response_summary": response_summary or {},
        "artifacts": artifacts or [],
        "replay_steps": [{
            "method": method.upper(),
            "path": endpoint,
            "body": request,
            "expect_json": True,
        }],
        "note": note or (
            "This replay block is metadata. The full response JSON remains in "
            "the API response or browser replay download."
        ),
    }
