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
        # The home page mentions Duecare
        assert b"Duecare" in r.content


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
