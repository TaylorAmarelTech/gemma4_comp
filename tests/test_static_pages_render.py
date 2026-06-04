"""Every workbench static page must serve a real HTML body (HTTP 200).

A render sweep over all static/*.html — catches a page that a refactor broke
into a 404/500 or emptied out. Parametrized so a failure names the exact page.
No model load. Complements the per-page UI contract tests.
"""
from __future__ import annotations

import pathlib

import duecare.chat.app as chat_app
import pytest
from duecare.chat.app import create_app
from fastapi.testclient import TestClient

_STATIC = pathlib.Path(chat_app.__file__).parent / "static"
_PAGES = sorted(p.name for p in _STATIC.glob("*.html"))


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.mark.parametrize("page", _PAGES)
def test_static_page_renders(client: TestClient, page: str) -> None:
    r = client.get(f"/static/{page}")
    assert r.status_code == 200, f"{page} -> HTTP {r.status_code}"
    body = r.text
    assert "<" in body and len(body) > 80, f"{page} served no real markup"


def test_sweep_covers_the_full_surface() -> None:
    # guard against the glob silently returning nothing
    assert len(_PAGES) >= 30, f"expected the full workbench surface, found {len(_PAGES)}"
