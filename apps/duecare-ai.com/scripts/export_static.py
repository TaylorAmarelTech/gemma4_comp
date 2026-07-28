#!/usr/bin/env python3
"""Export the DueCare public site for a live-backend or read-only static host.

The exporter renders every public page through the real FastAPI application,
copies committed assets, and writes pretty-URL files. It never calls a model or
network service.

Examples::

    python scripts/export_static.py --out dist --api-base https://backend.example
    python scripts/export_static.py --out dist-fallback --fallback \
        --base-path /duecare-ai-site \
        --site-url https://tayloramareltech.github.io/duecare-ai-site \
        --omit-cname

``--fallback`` is a fail-closed continuity build. It renders against an empty
temporary hub store, bakes only an allowlist of public read endpoints, installs
the static-boundary client before page scripts execute, disables state-changing
controls, and never proxies an API request to the live Render service.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent.parent
CNAME = "duecare-ai.com"
DEFAULT_SITE_URL = "https://duecare-ai.com"
FALLBACK_SCRIPT = "static/duecare-static-fallback.js"
SNAPSHOT_ROUTES = {
    "/api/hub/packs": "hub-packs.json",
    "/api/hub/knowledge-packs": "hub-knowledge-packs.json",
    "/api/knowledge/packs": "runtime-knowledge-packs.json",
    "/api/hub/status": "hub-status.json",
    "/api/hub/trends": "hub-trends.json",
}

_ROOT_ATTR_RE = re.compile(
    r"(?P<prefix>(?<![-\w])(?:href|src|action)\s*=\s*(?P<quote>['\"]))"
    r"(?P<path>/(?!/)[^'\"]*)",
    re.IGNORECASE,
)
_API_ANCHOR_RE = re.compile(
    r"(?P<prefix><a\b[^>]*?\bhref\s*=\s*)(?P<quote>['\"])(?P<url>"
    r"(?:https://(?:www\.)?duecare-ai\.com)?/"
    r"(?:admin[^'\"]*|api(?:/[^'\"]*|-docs[^'\"]*)|curator[^'\"]*|"
    r"openapi\.json[^'\"]*|redoc[^'\"]*|sentinel[^'\"]*))"
    r"(?P=quote)",
    re.IGNORECASE,
)


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _normalize_base_path(value: str) -> str:
    text = str(value or "").strip()
    if not text or text == "/":
        return ""
    if not text.startswith("/"):
        text = "/" + text
    return text.rstrip("/")


def _prefix_root_attributes(text: str, base_path: str) -> str:
    if not base_path:
        return text

    def _replace(match: re.Match[str]) -> str:
        path = match.group("path")
        if path == base_path or path.startswith(base_path + "/"):
            return match.group(0)
        return f"{match.group('prefix')}{base_path}{path}"

    return _ROOT_ATTR_RE.sub(_replace, text)


def _disable_api_anchors(text: str) -> str:
    """Make server-only links honest in a backend-free bundle."""

    def _replace(match: re.Match[str]) -> str:
        quote = match.group("quote")
        original = html.escape(match.group("url"), quote=True)
        return (
            f"{match.group('prefix')}{quote}/project-status{quote} "
            f'data-dc-static-disabled="api" data-dc-original-href="{original}"'
        )

    return _API_ANCHOR_RE.sub(_replace, text)


def _fallback_script_tag(base_path: str, snapshot_date: str) -> str:
    attributes = {
        "src": f"{base_path}/{FALLBACK_SCRIPT}",
        "data-base-path": base_path,
        "data-snapshot-date": snapshot_date,
        "data-live-url": DEFAULT_SITE_URL,
    }
    rendered = " ".join(
        f'{name}="{html.escape(value, quote=True)}"' for name, value in attributes.items()
    )
    return (
        '<meta name="duecare-static-mode" content="read-only-fallback" />\n'
        f"<script {rendered}></script>\n"
    )


def _static_sitemap(routes: list[str], site_url: str, snapshot_date: str) -> bytes:
    entries = []
    for route in routes:
        url = site_url.rstrip("/") + ("/" if route == "/" else route)
        entries.append(
            "  <url>\n"
            f"    <loc>{html.escape(url)}</loc>\n"
            f"    <lastmod>{snapshot_date}</lastmod>\n"
            "    <changefreq>monthly</changefreq>\n"
            f"    <priority>{'1.0' if route == '/' else '0.7'}</priority>\n"
            "  </url>"
        )
    body = "\n".join(entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    ).encode()


def _static_404(base_path: str, snapshot_date: str) -> bytes:
    prefix = base_path or ""
    script = _fallback_script_tag(prefix, snapshot_date)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Page not found · DueCare AI</title>
<link rel="stylesheet" href="{prefix}/static/styles.css" />
{script}</head><body><main class="wrap" style="padding:72px 0;min-height:65vh">
<span class="eyebrow">Static continuity site</span>
<h1>That page is not in the public archive.</h1>
<p class="lede">Return to the read-only DueCare site or use the maintained
project documentation.</p>
<p><a class="btn" href="{prefix}/">Return home</a>
<a class="btn btn-ghost" href="https://tayloramareltech.github.io/gemma4_comp/">Project docs</a></p>
</main></body></html>""".encode()


def _snapshot_payload(route: str, payload: Any, snapshot_date: str) -> Any:
    if route != "/api/hub/status" or not isinstance(payload, dict):
        return payload
    sanitized = dict(payload)
    sanitized["uptime_seconds"] = 0
    sanitized["static_snapshot"] = True
    sanitized["snapshot_date"] = snapshot_date
    return sanitized


def _write_snapshots(
    client: Any,
    out: Path,
    snapshot_date: str,
    source_revision: str,
) -> dict[str, Any]:
    snapshot_dir = out / "static" / "snapshots"
    entries: list[dict[str, Any]] = []
    for route, filename in SNAPSHOT_ROUTES.items():
        response = client.get(route)
        if response.status_code != 200:
            raise RuntimeError(f"safe snapshot route {route} returned HTTP {response.status_code}")
        payload = _snapshot_payload(route, response.json(), snapshot_date)
        serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        encoded = (serialized + "\n").encode()
        _write(snapshot_dir / filename, encoded)
        entries.append(
            {
                "route": route,
                "file": f"static/snapshots/{filename}",
                "sha256": hashlib.sha256(encoded).hexdigest(),
            }
        )
    manifest = {
        "schema": "duecare.static-fallback-snapshots.v1",
        "snapshot_date": snapshot_date,
        "source_revision": source_revision,
        "source": "committed public registries rendered with an isolated empty hub store",
        "contains_private_submissions": False,
        "contains_admin_state": False,
        "contains_raw_logs": False,
        "entries": entries,
    }
    encoded_manifest = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode()
    _write(snapshot_dir / "manifest.json", encoded_manifest)
    return manifest


def export(
    out: Path,
    api_base: str | None,
    *,
    fallback: bool = False,
    base_path: str = "",
    site_url: str = DEFAULT_SITE_URL,
    cname: str | None = CNAME,
    snapshot_date: str | None = None,
    source_revision: str = "working-tree",
) -> dict[str, Any]:
    if fallback and api_base:
        raise ValueError("--fallback and --api-base are mutually exclusive")

    base_path = _normalize_base_path(base_path)
    site_url = site_url.rstrip("/")
    snapshot_date = snapshot_date or datetime.now(UTC).date().isoformat()
    source_revision = source_revision.strip() or "working-tree"

    sys.path.insert(0, str(APP_DIR))
    from app.main import PAGE_ROUTES, create_app
    from fastapi.testclient import TestClient

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="duecare-static-export-") as data_dir:
        client = TestClient(create_app(data_dir=Path(data_dir)))

        def _post_process(content: bytes) -> bytes:
            text = content.decode("utf-8", "ignore")
            text = text.replace(
                "/api/demo/priority-examples", "/static/demo_priority_examples.json"
            )
            if api_base:
                backend = api_base.rstrip("/")
                text = re.sub(
                    r"fetch\(\s*(['\"`])/api/",
                    lambda match: f"fetch({match.group(1)}{backend}/api/",
                    text,
                )
            if fallback:
                text = _disable_api_anchors(text)
                script = _fallback_script_tag(base_path, snapshot_date)
                text = text.replace("</head>", script + "</head>", 1)
            text = _prefix_root_attributes(text, base_path)
            return text.encode()

        pages: list[str] = []
        for route in PAGE_ROUTES:
            response = client.get(route)
            if response.status_code != 200:
                raise RuntimeError(f"public page {route} returned HTTP {response.status_code}")
            rel = "index.html" if route == "/" else route.strip("/") + "/index.html"
            _write(out / rel, _post_process(response.content))
            pages.append(route)

        static_src = APP_DIR / "app" / "static"
        if static_src.is_dir():
            shutil.copytree(static_src, out / "static", dirs_exist_ok=True)
        demo = APP_DIR / "app" / "data" / "demo_priority_examples.json"
        if demo.is_file():
            _write(out / "static" / "demo_priority_examples.json", demo.read_bytes())

        snapshot_manifest = None
        if fallback:
            snapshot_manifest = _write_snapshots(
                client,
                out,
                snapshot_date,
                source_revision,
            )
            _write(out / "sitemap.xml", _static_sitemap(pages, site_url, snapshot_date))
            robots = f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n"
            _write(out / "robots.txt", robots.encode())
            _write(out / "404.html", _static_404(base_path, snapshot_date))
        else:
            for extra, name in (("/robots.txt", "robots.txt"), ("/sitemap.xml", "sitemap.xml")):
                response = client.get(extra)
                if response.status_code == 200:
                    _write(out / name, response.content)

    if cname:
        (out / "CNAME").write_text(cname.strip() + "\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return {
        "pages": len(pages),
        "out": str(out),
        "api_base": api_base or None,
        "mode": "read-only-fallback" if fallback else "live-backend",
        "base_path": base_path,
        "site_url": site_url,
        "cname": cname,
        "snapshot_entries": len(snapshot_manifest["entries"]) if snapshot_manifest else 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=APP_DIR / "dist")
    parser.add_argument(
        "--api-base",
        default=None,
        help="absolute live origin used by dynamic /api fetches",
    )
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="build a fail-closed read-only continuity site with safe snapshots",
    )
    parser.add_argument(
        "--base-path",
        default="",
        help="project-site prefix such as /duecare-ai-site (empty for a domain root)",
    )
    parser.add_argument(
        "--site-url",
        default=DEFAULT_SITE_URL,
        help="canonical deployment URL, including any project path",
    )
    parser.add_argument("--cname", default=CNAME, help="custom domain file value")
    parser.add_argument("--omit-cname", action="store_true", help="do not emit CNAME")
    parser.add_argument(
        "--snapshot-date",
        default=None,
        help="YYYY-MM-DD receipt date (defaults to current UTC date)",
    )
    parser.add_argument(
        "--source-revision",
        default="working-tree",
        help="source commit recorded in the fallback snapshot manifest",
    )
    args = parser.parse_args(argv)
    result = export(
        args.out,
        args.api_base,
        fallback=args.fallback,
        base_path=args.base_path,
        site_url=args.site_url,
        cname=None if args.omit_cname else args.cname,
        snapshot_date=args.snapshot_date,
        source_revision=args.source_revision,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
