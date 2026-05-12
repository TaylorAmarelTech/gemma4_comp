"""Pydantic v2 models for the v1.0 BundleEnvelope contract.

The canonical wrapper every appendix kernel emits to
/kaggle/working/. See docs/data_primitives.md sections 1.1 - 1.3
for the field-by-field spec.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class HarnessLayerStats(BaseModel):
    """Base for the 5 layer trace blocks."""

    enabled: bool = False
    elapsed_ms: float = 0.0

    model_config = {"extra": "allow"}


class HarnessPersona(HarnessLayerStats):
    """Persona / system-prompt layer trace."""

    system_prompt_chars: int = 0


class HarnessGrep(HarnessLayerStats):
    """Lane-1 GREP rules trace."""

    rules_evaluated: int = 0
    rules_fired: list[dict[str, Any]] = Field(default_factory=list)


class HarnessRag(HarnessLayerStats):
    """Lane-2 retrieval (pack + knowledge-base) trace."""

    top_k: int = 5
    docs_retrieved: list[dict[str, Any]] = Field(default_factory=list)


class HarnessTools(HarnessLayerStats):
    """Lane-3 function-calling / tool-use trace."""

    tools_called: list[dict[str, Any]] = Field(default_factory=list)


class HarnessOnline(HarnessLayerStats):
    """Lane-4 online-search trace (chat-with-research kernels)."""

    queries: list[str] = Field(default_factory=list)


class HarnessTrace(BaseModel):
    """Per-prompt trace of what the harness did.

    All 5 layer keys are always present even when a layer is
    disabled (enabled=False with empty arrays). This makes
    downstream consumers (A-03, A-08 compare kernels) keyable
    without per-row presence checks.
    """

    persona: HarnessPersona = Field(default_factory=HarnessPersona)
    grep: HarnessGrep = Field(default_factory=HarnessGrep)
    rag: HarnessRag = Field(default_factory=HarnessRag)
    tools: HarnessTools = Field(default_factory=HarnessTools)
    online: HarnessOnline = Field(default_factory=HarnessOnline)
    merged_prompt_chars: int = 0

    model_config = {"extra": "allow"}


class PerRow(BaseModel):
    """One entry in BundleEnvelope.results[].

    row_id is the kernel-specific stable primary key (prompt_id /
    composite_id / upload_id / post_id / case_id / etc.). The
    extra='allow' config lets kernels carry their own fields
    (verdict, risk_score, indicators, condition, ...).
    """

    row_id: str
    prompt_text: str
    response: str
    elapsed_s: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    harness_trace: Optional[HarnessTrace] = None
    citations: list[str] = Field(default_factory=list)
    error: Optional[str] = None

    model_config = {"extra": "allow"}


class BundleEnvelope(BaseModel):
    """Top-level v1.0 wrapper for every JSON-emitting kernel."""

    schema_version: Literal["1.0"] = "1.0"
    kernel_id: str
    run_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    results: list[PerRow] = Field(default_factory=list)

    model_config = {"extra": "allow"}
