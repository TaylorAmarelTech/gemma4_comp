"""Generation result + embedding + healthcheck schemas for Model adapters."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .chat import ToolCall


class GenerationResult(BaseModel):
    """The output of a single Model.generate() call."""

    text: str
    finish_reason: str = "stop"
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    tool_calls: list[ToolCall] = Field(default_factory=list)
    model_id: str
    model_version: str = ""
    cost_usd: float = 0.0
    raw: dict = Field(default_factory=dict)  # provider-specific extras


class Embedding(BaseModel):
    """An embedding vector for a piece of text."""

    text: str
    vector: list[float]
    dimension: int
    model_id: str


class ModelHealth(BaseModel):
    """Healthcheck result for a Model adapter."""

    model_id: str
    healthy: bool
    details: dict = Field(default_factory=dict)
