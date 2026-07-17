"""export_static: render the duecare-ai.com FastAPI site to a static GitHub Pages bundle."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_APP = _ROOT / "apps" / "duecare-ai.com"


def _load():
    if str(_APP) not in sys.path:
        sys.path.insert(0, str(_APP))
    spec = importlib.util.spec_from_file_location("export_static", _APP / "scripts" / "export_static.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["export_static"] = mod
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
    assert result["pages"] >= 40                          # ~49 public routes; be tolerant of route changes
    assert (out / "index.html").is_file()                 # '/' -> index.html
    assert (out / "mission" / "index.html").is_file()     # pretty URL for '/mission'
    assert (out / "CNAME").read_text(encoding="utf-8").strip() == "duecare-ai.com"
    assert (out / ".nojekyll").is_file()
    assert (out / "static" / "styles.css").is_file()      # assets copied
    assert (out / "static" / "demo_priority_examples.json").is_file()  # committed data baked
    # the demo page's api fetch is repointed to the baked static json
    demo = out / "demo-recording" / "index.html"
    if demo.is_file():
        assert "/api/demo/priority-examples" not in demo.read_text(encoding="utf-8", errors="ignore")


@pytest.mark.skipif(not _deps_ok(), reason="site deps (fastapi/jinja2/httpx) not installed")
def test_api_base_rewrites_relative_api_fetches(tmp_path):
    es = _load()
    out = tmp_path / "dist"
    es.export(out, api_base="https://backend.test")
    joined = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in out.rglob("index.html"))
    # with --api-base set, no page should keep a relative fetch('/api/...') (all rewritten to the origin)
    assert "fetch('/api/" not in joined and 'fetch("/api/' not in joined
