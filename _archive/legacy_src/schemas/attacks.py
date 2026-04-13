"""Attack strategy and chain schemas.

Runtime strategy objects live in src/attacks/; these are the data-model
sidecars used for persistence, configuration, and cross-component messaging.

See docs/architecture.md section 3 and section 9.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import AttackCategory


class AttackStrategyMeta(BaseModel):
    """Metadata describing an attack strategy. One per registered strategy."""

    id: str
    name: str
    category: AttackCategory
    description: str
    version: str
    indicators: list[str] = Field(default_factory=list)
    parameters_schema: dict = Field(default_factory=dict)  # JSON Schema


class AttackChainMeta(BaseModel):
    """Metadata describing a multi-turn attack chain."""

    id: str
    name: str
    description: str
    n_turns: int
    strategy_ids: list[str] = Field(default_factory=list)
    version: str
