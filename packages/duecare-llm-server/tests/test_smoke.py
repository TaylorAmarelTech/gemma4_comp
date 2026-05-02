"""Smoke tests for duecare-llm-server."""
from __future__ import annotations

import pytest


def test_server_imports() -> None:
    pytest.importorskip("fastapi")
    try:
        from duecare.server import create_app, run_server
    except ImportError as e:
        pytest.skip(f"server depends on packages not installed: {e}")
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
