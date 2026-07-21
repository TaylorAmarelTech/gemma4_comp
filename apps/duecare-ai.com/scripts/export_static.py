#!/usr/bin/env python3
"""Export the duecare-ai.com FastAPI site to a static bundle for GitHub Pages / any static host.

Renders every public page through the REAL app via Starlette's TestClient, so the output is
byte-identical to production (including the _nav/_footer includes and the baked leaderboard
JSON), copies /static, bakes the one committed data file a client page fetches, and writes
CNAME + .nojekyll. Pure build step: no network, no live model calls.

    python scripts/export_static.py --out dist
    python scripts/export_static.py --out dist --api-base https://gemma4-comp.onrender.com

--api-base rewrites relative fetch('/api/...') calls in the emitted HTML to that absolute
origin, so dynamic pages (contribute/newsletter/outreach/knowledge-packs) keep working
against a live backend whose CORS already allows the duecare-ai.com origin. Omit it for a
fully static bundle (those pages render, but their backend calls no-op).
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent  # apps/duecare-ai.com
CNAME = "duecare-ai.com"


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def export(out: Path, api_base: str | None) -> dict:
    sys.path.insert(0, str(APP_DIR))
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from app.main import PAGE_ROUTES, create_app  # noqa: PLC0415

    client = TestClient(create_app())
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    def _post_process(html: bytes) -> bytes:
        text = html.decode("utf-8", "ignore")
        # the demo page fetches a committed JSON via an API route -> repoint to the baked static copy
        text = text.replace("/api/demo/priority-examples", "/static/demo_priority_examples.json")
        if api_base:
            base = api_base.rstrip("/")
            text = re.sub(r"fetch\((['\"])/api/", lambda m: f"fetch({m.group(1)}{base}/api/", text)
        return text.encode("utf-8")

    pages = []
    for route in PAGE_ROUTES:
        r = client.get(route)
        if r.status_code != 200:
            print(f"[skip] {route} -> HTTP {r.status_code}")
            continue
        rel = "index.html" if route == "/" else route.strip("/") + "/index.html"
        _write(out / rel, _post_process(r.content))
        pages.append(route)

    for extra, name in (("/robots.txt", "robots.txt"), ("/sitemap.xml", "sitemap.xml")):
        r = client.get(extra)
        if r.status_code == 200:
            _write(out / name, r.content)

    static_src = APP_DIR / "app" / "static"
    if static_src.is_dir():
        shutil.copytree(static_src, out / "static", dirs_exist_ok=True)
    demo = APP_DIR / "app" / "data" / "demo_priority_examples.json"
    if demo.is_file():
        _write(out / "static" / "demo_priority_examples.json", demo.read_bytes())

    (out / "CNAME").write_text(CNAME + "\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return {"pages": len(pages), "out": str(out), "api_base": api_base or "(relative)"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=APP_DIR / "dist")
    ap.add_argument("--api-base", default=None,
                    help="absolute origin to repoint relative /api fetches at (e.g. the Render backend)")
    args = ap.parse_args(argv)
    print(export(args.out, args.api_base))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
