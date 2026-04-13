"""AttackRegistry. See docs/architecture.md section 9.2.

Strategies register themselves on import via @AttackRegistry.register("id").
"""

from __future__ import annotations

from typing import Iterator

from src.attacks.base import BaseAttackStrategy
from src.schemas.prompts import Prompt


class AttackRegistry:
    """Central registry of attack strategies.

    Strategies register themselves on import. The registry is populated at
    application startup by importing src.attacks.strategies.
    """

    _strategies: dict[str, BaseAttackStrategy] = {}

    @classmethod
    def register(cls, strategy_id: str):
        """Decorator: register a strategy class under `strategy_id`."""
        def decorator(strategy_cls):
            cls._strategies[strategy_id] = strategy_cls()
            return strategy_cls
        return decorator

    @classmethod
    def get(cls, strategy_id: str) -> BaseAttackStrategy:
        if strategy_id not in cls._strategies:
            raise KeyError(f"Unknown attack strategy: {strategy_id}")
        return cls._strategies[strategy_id]

    @classmethod
    def all_ids(cls) -> list[str]:
        return sorted(cls._strategies.keys())

    @classmethod
    def all(cls) -> Iterator[BaseAttackStrategy]:
        for sid in cls.all_ids():
            yield cls._strategies[sid]

    @classmethod
    def apply(
        cls,
        prompt: Prompt,
        strategy_ids: list[str],
    ) -> list[Prompt]:
        """Apply each strategy to the base prompt, returning mutated variants."""
        results: list[Prompt] = []
        for sid in strategy_ids:
            strategy = cls.get(sid)
            mutated = strategy.mutate(prompt)
            if not strategy.validate(mutated):
                raise ValueError(f"Strategy {sid} produced invalid mutation")
            results.append(mutated)
        return results
