"""Base generator protocol and shared utilities for DueCare prompt mutation.

Every generator takes a list of base prompts and produces N variations
per prompt, tracking lineage (base_prompt_id, mutation_type) so the
evaluation pipeline can compare stock-vs-mutated results.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Prompt dict conventions
# ---------------------------------------------------------------------------
# Input:  {"id": str, "text": str, "category": str, ...}
# Output: {"id": str, "text": str, "category": str,
#           "difficulty": "hard",
#           "source": "generated",
#           "metadata": {"base_prompt_id": str, "mutation_type": str, ...}}
# ---------------------------------------------------------------------------

Prompt = dict[str, Any]


@runtime_checkable
class Generator(Protocol):
    """Protocol every DueCare generator implements."""

    name: str

    def generate(
        self,
        prompts: list[Prompt],
        n_variations: int = 1,
        *,
        seed: int | None = None,
    ) -> list[Prompt]:
        """Return *n_variations* mutated copies for each prompt."""
        ...


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def variation_id(base_id: str, mutation_type: str, text: str) -> str:
    """Deterministic short id for a generated variation."""
    digest = hashlib.md5(text[:200].encode("utf-8")).hexdigest()[:8]
    return f"{base_id}_{mutation_type}_{digest}"


def seeded_rng(seed: int | None) -> random.Random:
    """Return an isolated Random instance so generators stay deterministic."""
    return random.Random(seed)


def make_variation(
    base: Prompt,
    *,
    mutated_text: str,
    mutation_type: str,
    extra_meta: dict[str, Any] | None = None,
) -> Prompt:
    """Build a variation dict with full lineage metadata."""
    meta = {
        "base_prompt_id": base.get("id", "unknown"),
        "mutation_type": mutation_type,
        "base_category": base.get("category", "unknown"),
    }
    if extra_meta:
        meta.update(extra_meta)

    return {
        "id": variation_id(base.get("id", "unk"), mutation_type, mutated_text),
        "text": mutated_text,
        "category": base.get("category", "unknown"),
        "difficulty": "hard",
        "source": "generated",
        "metadata": meta,
    }
