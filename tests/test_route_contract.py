"""Adversarial regression test: every (path, method) pair the kernel
exposes is recorded here. If the harness refactor changes ANY of them by
mistake -- adds, drops, or renames a route -- this test fails immediately.
"""

from __future__ import annotations

from duecare.chat.app import create_app


EXPECTED_ROUTES: set[tuple[str, str]] = {
    ("/", "GET"),
    ("/healthz", "GET"),
    ("/api/version", "GET"),
    ("/api/health-check", "GET"),
    ("/api/portability", "GET"),
    ("/api/experiment-contract", "GET"),
    ("/api/audit/workbench-inventory", "GET"),
    ("/static/chat.html", "GET"),
    ("/api/dc-logs", "GET"),
    ("/api/dc-logs/stats", "GET"),
    ("/api/dc-logs/clear", "POST"),
    ("/api/brand", "GET"),
    ("/api/model-info", "GET"),
    ("/api/harness-info", "GET"),
    ("/api/harness/inventory", "GET"),
    ("/api/harnesses", "GET"),
    ("/api/docs/{layer}", "GET"),
    ("/api/examples", "GET"),
    ("/api/rubric-hints", "GET"),
    ("/api/personas", "GET"),
    ("/api/baseline", "GET"),
    ("/api/governance", "GET"),
    ("/api/governance/{name}", "GET"),
    ("/api/classify-prompt", "POST"),
    ("/api/evaluation-questions", "GET"),
    ("/api/evaluation/knowledge-pack", "GET"),
    ("/api/rag/graph", "GET"),
    ("/api/grep/test", "POST"),
    ("/api/contacts", "GET"),
    ("/api/search-all", "GET"),
    ("/api/search/safety-info", "GET"),
    ("/api/search/sanitize", "POST"),
    ("/api/harness-catalog/{layer}", "GET"),
    ("/api/grade", "POST"),
    ("/api/grade-deep", "POST"),
    ("/api/grade-combined", "POST"),
    ("/api/grade-benchmark", "POST"),
    ("/api/grade-deep-stream", "POST"),
    ("/api/grade-combined-stream", "POST"),
    ("/api/health", "GET"),
    ("/api/import/upload", "POST"),
    ("/api/import/snippet", "POST"),
    ("/api/import/list", "GET"),
    ("/api/import/{doc_id}", "GET"),
    ("/api/import/{doc_id}", "DELETE"),
    ("/api/import", "DELETE"),
    ("/api/retrieval/config", "GET"),
    ("/api/retrieval/config", "POST"),
    ("/api/retrieval/embed-cache/clear", "POST"),
    ("/api/online/config", "GET"),
    ("/api/online/config", "POST"),
    ("/api/online/test", "POST"),
    ("/api/chat/upload-image", "POST"),
    ("/api/chat/image/{sid}", "GET"),
    ("/api/chat/send", "POST"),
    ("/api/process/batch", "POST"),
    ("/api/process/batch/start", "POST"),
    ("/api/process/batch/status/{job_id}", "GET"),
    ("/api/process/batch/cancel/{job_id}", "POST"),
    ("/api/process/graph-extract", "POST"),
    ("/api/process/graph-extract/start", "POST"),
    ("/api/process/graph-extract/status/{job_id}", "GET"),
    ("/api/process/graph-chat", "POST"),
    ("/api/anonymize", "POST"),
    ("/api/anonymize/start", "POST"),
    ("/api/anonymize/status/{job_id}", "GET"),
    ("/api/anonymize/cancel/{job_id}", "POST"),
    ("/api/submit/knowledge", "POST"),
    ("/api/submit/local", "POST"),
    ("/api/knowledge/promote", "POST"),
    ("/api/knowledge/list", "GET"),
    ("/api/knowledge/taxonomy", "GET"),
    ("/api/knowledge/type-catalog", "GET"),
    ("/api/knowledge/source-file", "POST"),
    ("/api/knowledge/export", "GET"),
    ("/api/knowledge/import", "POST"),
    ("/api/knowledge/{ko_type}/{ko_id}", "GET"),
    ("/api/knowledge/sync", "POST"),
    ("/api/knowledge/draft-envelope", "POST"),
    ("/api/knowledge/draft-envelope/start", "POST"),
    ("/api/knowledge/draft-envelope/status/{job_id}", "GET"),
    ("/api/knowledge/draft-envelope/cancel/{job_id}", "POST"),
    # search harness (Phase 11)
    ("/api/search/server", "POST"),
    ("/api/search/client", "POST"),
    ("/api/search/backends", "GET"),
    # post-search verification harness
    ("/api/search/verify-results", "POST"),
    ("/api/search/verification-info", "GET"),
}


# FastAPI auto-injects these. They are framework chrome, not our surface.
_AUTO_ROUTES: frozenset[tuple[str, str]] = frozenset({
    ("/docs", "GET"),
    ("/docs/oauth2-redirect", "GET"),
    ("/redoc", "GET"),
    ("/openapi.json", "GET"),
})


def _live_routes() -> set[tuple[str, str]]:
    app = create_app()
    out: set[tuple[str, str]] = set()
    for r in app.routes:
        path = getattr(r, "path", None) or getattr(r, "path_format", None)
        methods = getattr(r, "methods", None) or set()
        if not path or not methods:
            continue
        for m in methods:
            if m in {"HEAD", "OPTIONS"}:
                continue
            pair = (path, m)
            if pair in _AUTO_ROUTES:
                continue
            out.add(pair)
    return out


def test_route_contract_unchanged() -> None:
    """Snapshot the live FastAPI route table. Drift = explicit edit needed."""
    live = _live_routes()
    missing = EXPECTED_ROUTES - live
    added = live - EXPECTED_ROUTES
    msg_lines = []
    if missing:
        msg_lines.append(
            "Removed routes (refactor regression?): "
            + ", ".join(sorted(f"{p} {m}" for p, m in missing))
        )
    if added:
        msg_lines.append(
            "Added routes (intentional? bump EXPECTED_ROUTES): "
            + ", ".join(sorted(f"{p} {m}" for p, m in added))
        )
    assert not msg_lines, "\n".join(msg_lines)
