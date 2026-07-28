"""export_static: render the duecare-ai.com FastAPI site to a static GitHub Pages bundle."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_APP = _ROOT / "apps" / "duecare-ai.com"


def _load():
    if str(_APP) not in sys.path:
        sys.path.insert(0, str(_APP))
    spec = importlib.util.spec_from_file_location(
        "export_static", _APP / "scripts" / "export_static.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["export_static"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_validator():
    name = "validate_static_fallback"
    spec = importlib.util.spec_from_file_location(
        name, _APP / "scripts" / "validate_static_fallback.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _deps_ok() -> bool:
    try:
        import fastapi  # noqa: F401
        import httpx  # noqa: F401
        import jinja2  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.skipif(not _deps_ok(), reason="site deps (fastapi/jinja2/httpx) not installed")
def test_export_produces_static_bundle(tmp_path):
    es = _load()
    out = tmp_path / "dist"
    result = es.export(out, api_base=None)
    # Roughly 50 public routes; remain tolerant of intentional additions.
    assert result["pages"] >= 40
    assert (out / "index.html").is_file()  # '/' -> index.html
    assert (out / "mission" / "index.html").is_file()  # pretty URL for '/mission'
    assert (out / "project-status" / "index.html").is_file()
    assert (out / "CNAME").read_text(encoding="utf-8").strip() == "duecare-ai.com"
    assert (out / ".nojekyll").is_file()
    assert (out / "static" / "styles.css").is_file()  # assets copied
    assert (out / "static" / "demo_priority_examples.json").is_file()  # committed data baked
    # the demo page's api fetch is repointed to the baked static json
    demo = out / "demo-recording" / "index.html"
    if demo.is_file():
        text = demo.read_text(encoding="utf-8", errors="ignore")
        assert "/api/demo/priority-examples" not in text

    css = (out / "static" / "styles.css").read_text(encoding="utf-8")
    assert "@media (max-width: 760px)" in css
    assert ".nav-mobile-panel" in css
    assert ".nav-links { display: none; }" in css
    assert 'class="nav-mobile"' in (out / "index.html").read_text(encoding="utf-8")


@pytest.mark.skipif(not _deps_ok(), reason="site deps (fastapi/jinja2/httpx) not installed")
def test_api_base_rewrites_relative_api_fetches(tmp_path):
    es = _load()
    out = tmp_path / "dist"
    es.export(out, api_base="https://backend.test")
    joined = "".join(
        path.read_text(encoding="utf-8", errors="ignore") for path in out.rglob("index.html")
    )
    # With --api-base set, no page keeps a relative fetch('/api/...').
    assert "fetch('/api/" not in joined and 'fetch("/api/' not in joined
    assert "fetch(`/api/" not in joined


@pytest.mark.skipif(not _deps_ok(), reason="site deps (fastapi/jinja2/httpx) not installed")
def test_fallback_export_is_project_path_safe_and_fail_closed(tmp_path):
    es = _load()
    validator = _load_validator()
    out = tmp_path / "fallback"
    result = es.export(
        out,
        api_base=None,
        fallback=True,
        base_path="/duecare-ai-site/",
        site_url="https://tayloramareltech.github.io/duecare-ai-site/",
        cname=None,
        snapshot_date="2026-07-28",
        source_revision="a" * 40,
    )

    assert result == {
        "pages": 51,
        "out": str(out),
        "api_base": None,
        "mode": "read-only-fallback",
        "base_path": "/duecare-ai-site",
        "site_url": "https://tayloramareltech.github.io/duecare-ai-site",
        "cname": None,
        "snapshot_entries": 5,
    }
    assert not (out / "CNAME").exists()
    assert (out / "404.html").is_file()
    assert (out / "static" / "duecare-static-fallback.js").is_file()

    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="/duecare-ai-site/"' in index
    assert 'src="/duecare-ai-site/static/duecare-static-fallback.js"' in index
    assert 'name="duecare-static-mode" content="read-only-fallback"' in index

    contribute = (out / "contribute" / "index.html").read_text(encoding="utf-8")
    assert 'data-dc-static-disabled="api"' in contribute
    assert "fetch('/api/hub/client/submission'" in contribute

    manifest = json.loads(
        (out / "static" / "snapshots" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["contains_private_submissions"] is False
    assert manifest["source_revision"] == "a" * 40
    assert {entry["route"] for entry in manifest["entries"]} == set(es.SNAPSHOT_ROUTES)

    findings = validator.validate(
        out,
        base_path="/duecare-ai-site",
        site_url="https://tayloramareltech.github.io/duecare-ai-site",
        expect_cname=None,
    )
    assert findings == []


def test_fallback_cannot_proxy_to_live_api(tmp_path):
    es = _load()
    with pytest.raises(ValueError, match="mutually exclusive"):
        es.export(tmp_path / "invalid", "https://backend.test", fallback=True)
