"""Shared pytest setup for duecare-llm-kit: force a headless matplotlib backend before import."""
from __future__ import annotations

import os

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")
