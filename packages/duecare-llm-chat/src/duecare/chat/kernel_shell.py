"""Minimal-shell helper for notebook-only kernels.

Notebooks that compute outputs but don't need the full chat playground
(A-05 evaluation, A-06 prompt-generation, A-07 fine-tune, A-08 graphs,
A-11 grading) still get a workbench-consistent web UI via this helper.

Usage from a kernel.py:

.. code-block:: python

    from duecare.chat.kernel_shell import build_minimal_shell
    from duecare.chat._dc_log import set_kernel_id, dc_log

    set_kernel_id("a-05-evaluation")
    dc_log("kernel.start", "loading data")

    # ... do the kernel's compute work ...
    summary = {
        "title": "Classification evaluation",
        "audience": "researcher",
        "results": [
            {"label": "Prompts run", "value": 100},
            {"label": "Accuracy",    "value": "85.3%"},
            {"label": "Wall time",   "value": "47s"},
        ],
        "artifacts": [
            {"name": "results.json", "path": "/kaggle/working/results.json"},
            {"name": "scorecard.csv", "path": "/kaggle/working/scorecard.csv"},
        ],
        "links": [
            ("Workbench (full)",
             "https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench"),
        ],
        "next_steps": [
            "Open the Logs tab to see every event the run emitted.",
            "Download results.json from /artifact/results.json.",
        ],
    }

    app, url = build_minimal_shell(summary=summary, port=8080)

The shell serves:
  - ``/``                — the summary + artifact + links page
  - ``/static/*``        — the chat-package's static folder (so the
                           workbench nav, Logs page, and shared CSS work)
  - ``/api/dc-logs*``    — the JSON-Lines log endpoints
  - ``/artifact/<path>`` — files from /kaggle/working/ for download
  - ``/healthz``         — liveness check

Every notebook-only kernel ends up looking the same to a judge:
shared workbench top nav, a ``Logs`` tab they can click, a ``Tools``
link to the full workbench, and a focused homepage that explains
what *this* kernel did + how to inspect its outputs.
"""
from __future__ import annotations

import html
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

# Re-export so callers only need one import line.
from duecare.chat._dc_log import (
    dc_log,
    set_kernel_id,
    tail as _dc_tail,
    stats as _dc_stats,
    clear as _dc_clear,
)

__all__ = [
    "build_minimal_shell",
    "dc_log",
    "set_kernel_id",
]


def _resolve_static_dir() -> Path:
    """Locate the chat-package static folder regardless of how the
    package was installed (editable vs wheel)."""
    here = Path(__file__).resolve().parent
    static = here / "static"
    if not static.exists():
        raise RuntimeError(
            f"chat-package static dir not found at {static}; "
            "is duecare-llm-chat installed correctly?"
        )
    return static


def _render_summary_html(summary: dict[str, Any], kernel_id: str) -> str:
    """Render the kernel's summary page using the workbench shell.
    Loads `_chrome.css` + `showcase.css` + `_nav.js` from the static
    mount so it inherits the same nav as the rest of the workbench."""
    title = html.escape(str(summary.get("title", "Notebook output")))
    audience = html.escape(str(summary.get("audience", "researcher"))).lower()
    lede = html.escape(str(summary.get("lede", "")))

    audience_to_navkey = {
        "platform": "platform", "ngo": "ngo", "worker": "worker",
        "researcher": "researcher", "developer": "developer",
    }
    nav_key = audience_to_navkey.get(audience, "tools")

    results_html = ""
    if results := summary.get("results"):
        cards = []
        for r in results:
            label = html.escape(str(r.get("label", "")))
            value = html.escape(str(r.get("value", "")))
            cards.append(
                f'<div class="tool-card"><div class="desc">{label}</div>'
                f'<div class="name" style="font-size:22px; margin-top:6px;">{value}</div></div>'
            )
        results_html = (
            '<section class="section"><h2>Results</h2>'
            f'<div class="tools-row">{"".join(cards)}</div></section>'
        )

    artifacts_html = ""
    if artifacts := summary.get("artifacts"):
        items = []
        for a in artifacts:
            name = html.escape(str(a.get("name", "")))
            path = html.escape(str(a.get("path", "")))
            items.append(
                f'<a class="tool-card" href="/artifact/{name}" download>'
                f'<div class="name">{name}</div>'
                f'<div class="desc"><code>{path}</code></div></a>'
            )
        artifacts_html = (
            '<section class="section"><h2>Artifacts</h2>'
            f'<div class="tools-row">{"".join(items)}</div></section>'
        )

    links_html = ""
    if links := summary.get("links"):
        items = []
        for ll in links:
            if isinstance(ll, tuple) and len(ll) == 2:
                label, url = ll
            elif isinstance(ll, dict):
                label, url = ll.get("label", ""), ll.get("url", "")
            else:
                continue
            items.append(
                f'<a class="tool-card" href="{html.escape(str(url))}" target="_blank">'
                f'<div class="name">{html.escape(str(label))} <span aria-hidden="true">↗</span></div>'
                '</a>'
            )
        if items:
            links_html = (
                '<section class="section"><h2>Related</h2>'
                f'<div class="tools-row">{"".join(items)}</div></section>'
            )

    next_steps_html = ""
    if next_steps := summary.get("next_steps"):
        items = "".join(f"<li>{html.escape(str(s))}</li>" for s in next_steps)
        next_steps_html = (
            '<section class="section"><h2>Next steps</h2>'
            f'<ul style="font-size:14px; line-height:1.6; color:var(--ink-2);">{items}</ul>'
            '</section>'
        )

    cta_html = (
        '<div class="cta-row">'
        '<a class="cta cta-primary" href="/static/logs.html">Open Logs →</a>'
        '<a class="cta cta-ghost" href="/static/all-tools.html">All workbench tools →</a>'
        '</div>'
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — DueCare Workbench</title>
  <link rel="stylesheet" href="/static/_chrome.css">
  <link rel="stylesheet" href="/static/showcase.css">
  <script src="/static/_nav.js" defer></script>
</head>
<body data-nav="{html.escape(nav_key)}">
<main class="showcase">
  <div class="crumbs">Notebook · {html.escape(kernel_id)}</div>
  <h1>{title}</h1>
  {f'<p class="lede">{lede}</p>' if lede else ''}
  {cta_html}
  {results_html}
  {artifacts_html}
  {next_steps_html}
  {links_html}
</main>
</body>
</html>
"""


def build_minimal_shell(
    summary: dict[str, Any],
    *,
    kernel_id: Optional[str] = None,
    port: int = 8080,
    host: str = "0.0.0.0",
    artifact_root: Path = Path("/kaggle/working"),
    tunnel: bool = True,
    background: bool = True,
    homepage_html: Optional[str] = None,
    extra_routes: Optional[dict] = None,
) -> tuple[Any, Optional[str]]:
    """Build + (optionally) launch a minimal workbench-shell FastAPI app
    for a notebook-only kernel.

    Returns ``(app, url)``. ``url`` is the cloudflared public URL when
    ``tunnel=True`` and the tunnel module is reachable; ``None`` when
    serving locally only.

    The caller is responsible for emitting ``dc_log()`` events around
    its own compute work; this helper only serves the resulting summary
    + the standard /api/dc-logs endpoints + the workbench static.

    Parameters
    ----------
    summary
        Required. The summary dict rendered when ``homepage_html`` is
        not supplied. See the module docstring for shape.
    homepage_html
        Optional. A pre-rendered HTML string for ``GET /``. When
        supplied, replaces the default summary rendering and lets the
        caller embed visualizations, dashboards, inline charts, or
        custom interaction. The shared workbench shell remains active
        because the HTML can still link ``/static/_chrome.css`` and
        ``/static/_nav.js``. The default summary view stays reachable
        at ``/summary`` for the Tools menu.
    extra_routes
        Optional. Dict mapping path → ``(method, handler)`` for adding
        kernel-specific routes (e.g. ``{"/api/lift": ("GET", h)}``).
        Handlers are normal FastAPI handler callables.
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, FileResponse
    from fastapi.staticfiles import StaticFiles

    if kernel_id:
        set_kernel_id(kernel_id)
    kid = kernel_id or os.environ.get("DC_KERNEL_ID", "kernel")

    app = FastAPI(title=f"DueCare workbench — {kid}",
                  description="Minimal-shell wrapper for a notebook kernel.")
    static_dir = _resolve_static_dir()
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        if homepage_html:
            return homepage_html
        return _render_summary_html(summary, kid)

    @app.get("/summary", response_class=HTMLResponse)
    def summary_page() -> str:
        return _render_summary_html(summary, kid)

    @app.get("/healthz")
    def healthz() -> Any:
        return {"ok": True, "ts": time.time(), "kernel": kid}

    @app.get("/api/version")
    def api_version() -> Any:
        try:
            from duecare.chat import _brand
            v = getattr(_brand, "VERSION", "?")
        except Exception:
            v = "?"
        return {"kernel": kid, "kind": "minimal-shell", "chat_package": v}

    @app.get("/api/model-info")
    def api_model_info() -> Any:
        return {"loaded": False, "name": "(no chat model — notebook-only kernel)"}

    @app.get("/api/dc-logs")
    def api_dc_logs(tail: int = 200, level: Optional[str] = None,
                    kind: Optional[str] = None,
                    layer: Optional[str] = None) -> Any:
        n = max(1, min(int(tail or 200), 2000))
        events = _dc_tail(n=n, level=level, kind_prefix=kind, layer=layer)
        return {"events": events, "n": len(events)}

    @app.get("/api/dc-logs/stats")
    def api_dc_logs_stats() -> Any:
        return _dc_stats()

    @app.post("/api/dc-logs/clear")
    def api_dc_logs_clear() -> Any:
        return {"ok": True, "dropped": _dc_clear()}

    @app.get("/artifact/{name:path}")
    def artifact(name: str) -> Any:
        target = (artifact_root / name).resolve()
        try:
            target.relative_to(artifact_root.resolve())
        except ValueError:
            raise HTTPException(400, "path escape")
        if not target.exists() or not target.is_file():
            raise HTTPException(404, "not found")
        return FileResponse(target, filename=target.name)

    # /api/brand mock so the workbench shell renders without errors.
    @app.get("/api/brand")
    def api_brand() -> Any:
        return {
            "kernel": kid, "kind": "minimal-shell",
            "counts": {}, "layers": [], "extras": [],
        }

    # Caller-supplied routes (e.g. /api/lift, /api/charts, /export/csv).
    # Path → (method, handler-callable). Wired AFTER the built-in routes
    # so the standard endpoints can't be silently overridden by accident.
    if extra_routes:
        for path, spec in extra_routes.items():
            try:
                method, handler = spec
            except Exception:
                continue
            app.add_api_route(path, handler, methods=[method.upper()])

    url: Optional[str] = None
    if background:
        import uvicorn
        config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        server = uvicorn.Server(config)
        t = threading.Thread(target=server.run, daemon=True)
        t.start()
        time.sleep(1.5)
        dc_log("kernel.shell.up", f"minimal-shell listening on :{port}",
               kernel=kid, port=port)

    if tunnel:
        try:
            from duecare.chat.extensions.tunnel import start_cloudflared_tunnel
            url = start_cloudflared_tunnel(port=port)
            if url:
                dc_log("kernel.shell.tunnel", f"cloudflared up: {url}",
                       kernel=kid, url=url)
        except Exception as e:
            dc_log("kernel.shell.tunnel", f"cloudflared unavailable: {e}",
                   level="warn", kernel=kid)

    return app, url
