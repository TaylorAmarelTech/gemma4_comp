"""Attack strategy protocol. See docs/architecture.md section 9.1."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.schemas.base import AttackCategory
from src.schemas.prompts import Prompt


@runtime_checkable
class BaseAttackStrategy(Protocol):
    """An attack strategy that mutates a base Prompt into an adversarial variant.

    Strategies are pure functions over Prompts. They do not call any LLM.
    Multi-turn behavior lives in src/attacks/chains/ instead, where a chain
    is allowed to call a `judge_fn` between turns.
    """

    id: str  # registry key
    name: str  # human-readable
    category: AttackCategory
    description: str
    version: str

    def mutate(self, prompt: Prompt, **kwargs) -> Prompt:
        """Return a new Prompt with the attack strategy applied."""
        ...

    def validate(self, mutated: Prompt) -> bool:
        """Return True if the mutation preserved invariants (length, schema)."""
        ...

    def get_indicators(self) -> list[str]:
        """ILO indicators this strategy is designed to test."""
        ...
