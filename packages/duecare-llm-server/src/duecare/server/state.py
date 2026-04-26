"""Shared server state: lazy-built engine + evidence store + translator."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ServerState:
    """Mutable runtime state held in `app.state`. Lazy because not
    every endpoint needs every component (e.g. the homepage doesn't
    need the GPU-loaded backend)."""

    db_path: str = field(default_factory=lambda: os.environ.get(
        "DUECARE_DB", "duecare.duckdb"))
    pipeline_output_dir: str = field(default_factory=lambda: os.environ.get(
        "DUECARE_PIPELINE_OUT", "./multimodal_v1_output"))
    pipeline_script_path: str = field(default_factory=lambda: os.environ.get(
        "DUECARE_PIPELINE_SCRIPT",
        "raw_python/gemma4_docling_gliner_graph_v1.py"))
    project_root: Optional[str] = None
    public_url: Optional[str] = None

    _store: Any = None
    _engine: Any = None
    _translator: Any = None
    _gemma_call: Any = None
    _openclaw: Any = None
    # batches[batch_id] = {"created": iso, "kind": "moderate"|"worker_check",
    #                       "files": [{"path", "task_id", "size_bytes"}, ...]}
    _batches: dict = field(default_factory=dict)

    # -- lazy accessors -----------------------------------------------------
    @property
    def store(self):
        if self._store is None:
            from duecare.evidence import EvidenceStore
            self._store = EvidenceStore.open(self.db_path)
        return self._store

    @property
    def engine(self):
        if self._engine is None:
            from duecare.engine import Engine
            self._engine = Engine(project_root=self.project_root)
        return self._engine

    @property
    def translator(self):
        if self._translator is None:
            from duecare.nl2sql import Translator
            self._translator = Translator(
                self.store, gemma_call=self._gemma_call)
        return self._translator

    @property
    def openclaw(self):
        if self._openclaw is None:
            from duecare.research_tools import OpenClawTool
            self._openclaw = OpenClawTool.from_env()
        return self._openclaw

    def set_gemma_call(self, fn) -> None:
        """Register a callable(prompt: str, max_new_tokens: int) -> str.
        When set, NL2SQL falls back to free-form Gemma generation if no
        template matches. When None, only template matching is used."""
        self._gemma_call = fn
        self._translator = None  # rebuild on next access
