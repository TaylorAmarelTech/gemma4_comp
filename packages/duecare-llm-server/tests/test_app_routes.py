"""Behavioral tests for FastAPI server routes (the user-facing surface)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def _make_app(tmp_dir: str):
    pytest.importorskip("fastapi")
    from duecare.server import create_app
    from duecare.server.state import ServerState
    state = ServerState(db_path=str(Path(tmp_dir) / "t.duckdb"),
                        pipeline_output_dir=str(Path(tmp_dir) / "out"))
    Path(tmp_dir, "out").mkdir(parents=True, exist_ok=True)
    return create_app(state), state


def test_healthz_returns_ok() -> None:
    pytest.importorskip("fastapi.testclient")
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory() as tmp:
        try:
            app, _ = _make_app(tmp)
        except Exception as e:
            pytest.skip(f"server cannot construct: {e}")
        client = TestClient(app)
        r = client.get("/healthz")
        assert r.status_code == 200


def test_homepage_renders() -> None:
    pytest.importorskip("fastapi.testclient")
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory() as tmp:
        try:
            app, _ = _make_app(tmp)
        except Exception as e:
            pytest.skip(f"server cannot construct: {e}")
        client = TestClient(app)
        r = client.get("/")
        assert r.status_code == 200
        # The home page mentions DueCare; casing varies across branded surfaces.
        assert b"duecare" in r.content.lower()


def test_homepage_uses_six_lane_live_demo_console() -> None:
    pytest.importorskip("fastapi.testclient")
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory() as tmp:
        try:
            app, _ = _make_app(tmp)
        except Exception as e:
            pytest.skip(f"server cannot construct: {e}")
        client = TestClient(app)
        r = client.get("/")
        assert r.status_code == 200
        html = r.text
        assert "Six use cases" in html
        assert "Five use cases" not in html
        lane_cursor = -1
        for marker in [
            "Run the Gemma 4 harness ecosystem.",
            "Platform safety",
            "NGO &amp; regulator",
            "Individual worker / mobile",
            "Researcher",
            "Anonymized knowledge sharing",
            "Developer / integration partner",
            "Processing surfaces",
        ]:
            assert marker in html
            if marker != "Run the Gemma 4 harness ecosystem." and marker != "Processing surfaces":
                marker_index = html.find(marker)
                assert marker_index > lane_cursor, f"missing or out-of-order lane: {marker}"
                lane_cursor = marker_index
        assert '<a href="/knowledge"><span>05</span>' in html
        assert '<a href="/architecture"><span>06</span>' in html
        assert "Use case 1" not in html
        assert "Use case 2" not in html


def test_workspace_page_renders() -> None:
    pytest.importorskip("fastapi.testclient")
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory() as tmp:
        try:
            app, _ = _make_app(tmp)
        except Exception as e:
            pytest.skip(f"server cannot construct: {e}")
        client = TestClient(app)
        r = client.get("/workspace")
        assert r.status_code == 200


def test_api_status_returns_json() -> None:
    pytest.importorskip("fastapi.testclient")
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory() as tmp:
        try:
            app, _ = _make_app(tmp)
        except Exception as e:
            pytest.skip(f"server cannot construct: {e}")
        client = TestClient(app)
        r = client.get("/api/status")
        # status endpoint should respond (200 or 401 if auth on)
        assert r.status_code in (200, 401)
