"""The worker surface is an installable, offline-capable PWA (deployment mode 2).

Guards the manifest/service-worker/icon contract + the page wiring + the
correct-media-type route. No model load, no network. Synthetic content only.
"""
from __future__ import annotations

import json
import pathlib

import duecare.chat.app as chat_app
from duecare.chat.app import create_app
from fastapi.testclient import TestClient

_STATIC = pathlib.Path(chat_app.__file__).parent / "static"


def test_manifest_is_valid_and_installable():
    mf = json.loads((_STATIC / "manifest.webmanifest").read_text(encoding="utf-8"))
    # The fields a browser needs to offer "install" / add-to-home-screen.
    for key in ("name", "short_name", "start_url", "scope", "display", "icons"):
        assert mf.get(key), f"manifest missing {key}"
    assert mf["display"] in {"standalone", "fullscreen", "minimal-ui"}
    assert mf["start_url"].startswith("/static/")
    assert mf["scope"] == "/static/"
    # every declared icon file actually exists on disk
    assert mf["icons"], "no icons declared"
    for icon in mf["icons"]:
        rel = icon["src"].lstrip("/")
        assert (pathlib.Path(chat_app.__file__).parent / rel).exists(), f"missing {icon['src']}"


def test_service_worker_caches_shell_but_never_api():
    sw = (_STATIC / "sw.js").read_text(encoding="utf-8")
    assert "duecare-worker-v1" in sw                       # versioned cache
    assert "/static/showcase-worker.html" in sw            # app shell precached
    assert "/static/hotlines.html" in sw                   # offline hotlines (critical for a worker)
    assert 'startsWith("/api/")' in sw                     # api is special-cased
    # Privacy boundary: API responses (worker message + model answer) are
    # network-only, never precached -- the shell list must not contain /api.
    shell = sw.split("const SHELL")[1].split("]")[0]
    assert "/api/" not in shell


def test_worker_page_wires_manifest_and_service_worker():
    html = (_STATIC / "showcase-worker.html").read_text(encoding="utf-8")
    assert 'rel="manifest"' in html and "manifest.webmanifest" in html
    assert "serviceWorker.register" in html and "/static/sw.js" in html
    assert 'name="theme-color"' in html
    assert 'rel="apple-touch-icon"' in html
    assert 'id="dcInstallBtn"' in html                     # custom install affordance


def test_manifest_route_serves_correct_media_type():
    client = TestClient(create_app())
    r = client.get("/static/manifest.webmanifest")
    assert r.status_code == 200
    assert "application/manifest+json" in r.headers.get("content-type", "")
    assert r.json()["start_url"] == "/static/showcase-worker.html"
