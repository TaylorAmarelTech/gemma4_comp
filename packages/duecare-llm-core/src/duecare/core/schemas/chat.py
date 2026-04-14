"""Chat + tool schemas. Shared by every Model adapter."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """One message in a chat conversation. Maps to every major provider's
    chat format (OpenAI, Anthropic, Gemma, Llama chat templates)."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None             # for tool messages
    tool_call_id: str | None = None     # for tool-result messages


class ToolSpec(BaseModel):
    """A tool declaration an Agent passes to a Model.

    Maps 1:1 to Gemma 4 native function calling. Adapters translate per-
    provider (OpenAI / Anthropic / HF / etc.).
    """

    name: str
    description: str
    parameters: dict = Field(default_factory=dict)    # JSON Schema object

    def to_openai(self) -> dict:
        """Render as an OpenAI-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {"type": "object", "properties": {}},
            },
        }

    def to_anthropic(self) -> dict:
        """Render as an Anthropic-compatible tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters or {"type": "object", "properties": {}},
        }

    def to_gemma(self) -> dict:
        """Render as Gemma 4 native function-calling tool definition.

        Gemma 4 uses the Hugging Face Transformers `tools` format, which
        is itself OpenAI-compatible. The tokenizer's chat template handles
        the Gemma-specific wire format (typically JSON inside
        `<tool_call>...</tool_call>` tags in the generated output).
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {"type": "object", "properties": {}},
            },
        }


class ToolCall(BaseModel):
    """A tool call emitted by a Model."""

    name: str
    arguments: dict = Field(default_factory=dict)
    call_id: str | None = None
