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

    # Optional backend-info display, set by the kernel bootstrap when it
    # registers a Gemma callable. Surfaced via /api/model-info so the UI
    # can show a "Backend: <model>" badge.
    model_name: Optional[str] = field(default_factory=lambda: os.environ.get(
        "DUECARE_MODEL_NAME"))
    model_size_b: Optional[float] = None      # parameter count in billions
    model_quantization: Optional[str] = None  # "4-bit", "fp16", etc.
    model_device: Optional[str] = None        # "cuda:0", "balanced (2x T4)", "cpu"

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

    def set_gemma_call(self, fn, *,
                       model_name: Optional[str] = None,
                       model_size_b: Optional[float] = None,
                       model_quantization: Optional[str] = None,
                       model_device: Optional[str] = None) -> None:
        """Register a callable(prompt: str, max_new_tokens: int) -> str.
        When set, NL2SQL falls back to free-form Gemma generation if no
        template matches. When None, only template matching is used.
        Optional model-info fields populate the /api/model-info endpoint
        so the UI can display which model is currently serving."""
        self._gemma_call = fn
        self._translator = None  # rebuild on next access
        if model_name:
            self.model_name = model_name
        if model_size_b is not None:
            self.model_size_b = model_size_b
        if model_quantization:
            self.model_quantization = model_quantization
        if model_device:
            self.model_device = model_device

    def model_info(self) -> dict:
        """Snapshot of what's currently serving Gemma calls."""
        if self._gemma_call is None:
            return {
                "loaded": False,
                "name": None,
                "display": "Heuristic-only (no Gemma loaded)",
                "size_b": None,
                "quantization": None,
                "device": None,
            }
        name = self.model_name or "unknown"
        size = (f"{self.model_size_b:.1f}B"
                if self.model_size_b is not None else None)
        quant = self.model_quantization
        parts = [name]
        if size: parts.append(size)
        if quant: parts.append(quant)
        return {
            "loaded": True,
            "name": name,
            "display": " · ".join(parts),
            "size_b": self.model_size_b,
            "quantization": quant,
            "device": self.model_device,
        }
