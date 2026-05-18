"""Search harness handler.

Owns:
  - POST /api/search/server    server-side automated
  - POST /api/search/client    user-triggered
  - GET  /api/search/backends  list available backends
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .._replay import demo_replay
from .backends import build_registry, pick_backend


_MAX_TOP_N = 20


_BACKEND_META = {
    "searxng": {
        "display_name": "SearXNG",
        "description": "Privacy-preserving meta-search when DUECARE_SEARXNG_URL is configured.",
    },
    "legacy": {
        "display_name": "Kernel search hook",
        "description": "Uses the kernel-provided online_search_call hook, typically Tavily, Brave, or DuckDuckGo.",
    },
}


def _do_search(app: Any, body: dict, kind: str) -> dict:
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(400, "query is required")
    try:
        top_n = int(body.get("top_n") or 5)
    except (TypeError, ValueError):
        raise HTTPException(400, "top_n must be an integer")
    top_n = max(1, min(top_n, _MAX_TOP_N))
    preferred = body.get("backend") or None

    def _with_replay(out: dict) -> dict:
        out["demo_replay"] = demo_replay(
            lane="search",
            endpoint=f"/api/search/{kind}",
            request={
                "query": query,
                "top_n": top_n,
                "backend": preferred,
                "kind": kind,
                "anonymize_query": bool(body.get("anonymize_query", False)),
            },
            response_summary={
                "backend": out.get("backend"),
                "n_results": len(out.get("results") or []),
                "verification_status": out.get("verification_status"),
                "elapsed_ms": out.get("elapsed_ms"),
                "error": out.get("error"),
                "note": out.get("note"),
            },
            artifacts=[{
                "name": "search_results",
                "kind": "inline_response_json",
                "count": len(out.get("results") or []),
            }],
        )
        return out

    backend = pick_backend(app, preferred=preferred)
    if backend is None:
        return _with_replay({
            "query": query,
            "kind": kind,
            "backend": None,
            "results": [],
            "verification_status": "not_applicable",
            "note": "No backend available. Set DUECARE_SEARXNG_URL or wire online_search_call.",
        })

    try:
        out = backend.search(query, top_n=top_n)
    except Exception as exc:  # noqa: BLE001
        return _with_replay({
            "query": query,
            "kind": kind,
            "backend": backend.name,
            "results": [],
            "verification_status": "not_applicable",
            "error": f"{type(exc).__name__}: {exc}",
        })

    out["query"] = query
    out["kind"] = kind
    out["backend"] = backend.name
    out["verification_status"] = "candidate_unverified"
    out["next_step"] = "POST /api/search/verify-results before injecting results into chat, extraction, or knowledge packs."

    try:
        from .._training_log import log_interaction
        log_interaction(
            "search",
            input_payload={"query": query, "kind": kind, "top_n": top_n,
                           "preferred_backend": preferred},
            output_payload={
                "backend": backend.name,
                "n_results": len(out.get("results") or []),
                "elapsed_ms": out.get("elapsed_ms"),
                "titles": [r.get("title", "") for r in out.get("results") or []],
            },
            applied_layers={},
            trace={"source": out.get("source")},
            extra={"kind": kind},
        )
    except Exception:
        pass
    return _with_replay(out)


def register_routes(app: Any) -> None:

    @app.post("/api/search/server")
    async def api_search_server(request: Request) -> Any:
        """Server-automated search (sentinel, batch enrichment, scheduled tasks)."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        return JSONResponse(_do_search(app, body, kind="server"))

    @app.post("/api/search/client")
    async def api_search_client(request: Request) -> Any:
        """User-triggered search from the chat / workbench UI."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        if bool(body.get("anonymize_query", False)):
            from ..anonymization.detector import PII_PATTERNS
            from ..anonymization.redactor import placeholder
            q = body.get("query") or ""
            for label, pat in PII_PATTERNS:
                for m in pat.finditer(q):
                    q = q.replace(m.group(0), placeholder(label, m.group(0)))
            body["query"] = q
        return JSONResponse(_do_search(app, body, kind="client"))

    @app.get("/api/search/backends")
    def api_search_backends() -> Any:
        """List available backends + their state."""
        reg = build_registry(app)
        return {
            "backends": [
                {
                    "name": name,
                    "display_name": _BACKEND_META.get(name, {}).get("display_name", name),
                    "description": _BACKEND_META.get(name, {}).get("description", ""),
                    "available": b.is_available(),
                }
                for name, b in reg.items()
            ],
            "default_preference": list(("searxng", "legacy")),
            "default_preference_labels": [
                _BACKEND_META[name]["display_name"]
                for name in ("searxng", "legacy")
            ],
            "configured_searxng_url": bool(os.environ.get("DUECARE_SEARXNG_URL")),
        }
