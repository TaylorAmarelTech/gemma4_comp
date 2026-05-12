"""Duecare FastAPI server."""
from __future__ import annotations

from duecare.server.app import create_app, run_server
from duecare.server.state import ServerState

__all__ = ["ServerState", "create_app", "run_server"]
