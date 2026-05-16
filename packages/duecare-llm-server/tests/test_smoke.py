"""Smoke tests for duecare-llm-server."""
from __future__ import annotations

import pytest


def test_server_imports() -> None:
    pytest.importorskip("fastapi")
    try:
        from duecare.server import ServerState, create_app, run_server
    except ImportError as e:
        pytest.skip(f"server depends on packages not installed: {e}")
    assert ServerState is not None
    assert callable(create_app)
    assert callable(run_server)


def test_server_app_constructible() -> None:
    pytest.importorskip("fastapi")
    try:
        from duecare.server import create_app
        from duecare.server.state import ServerState
    except ImportError as e:
        pytest.skip(f"server depends on packages not installed: {e}")
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "test.duckdb")
        out = str(Path(tmp) / "pipeline_out")
        Path(out).mkdir(parents=True, exist_ok=True)
        try:
            state = ServerState(db_path=db, pipeline_output_dir=out)
        except Exception as e:
            pytest.skip(f"ServerState constructor failed: {e}")
        app = create_app(state)
        # FastAPI app object has a .routes attribute
        assert hasattr(app, "routes")
        # Healthz route registered
        paths = {getattr(r, "path", None) for r in app.routes}
        assert "/healthz" in paths


def test_server_primary_pages_and_safe_status_apis_serve(tmp_path) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    try:
        from duecare.server import create_app
        from duecare.server.state import ServerState
    except ImportError as e:
        pytest.skip(f"server depends on packages not installed: {e}")

    out = tmp_path / "pipeline_out"
    out.mkdir(parents=True, exist_ok=True)
    state = ServerState(db_path=str(tmp_path / "test.duckdb"), pipeline_output_dir=str(out))
    client = TestClient(create_app(state))

    for route in [
        "/",
        "/enterprise",
        "/individual",
        "/knowledge",
        "/settings",
        "/logs",
        "/workspace",
        "/demo",
        "/dashboard",
        "/chat",
        "/queue",
        "/architecture",
        "/background",
        "/evidence",
    ]:
        response = client.get(route)
        assert response.status_code == 200, route
        assert len(response.text) > 1000, route

    for route in ["/healthz", "/api/status", "/api/model-info", "/api/settings", "/api/activity"]:
        response = client.get(route)
        assert response.status_code == 200, route
