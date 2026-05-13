"""Knowledge-pack manifest for the search harness."""
from __future__ import annotations


CONSUMES: tuple[str, ...] = (
    "corridor_profile",
    "ngo_directory",
    "context_snippet",
    "prompt_template",
)

EMITS: tuple[str, ...] = (
    "context_snippet",
    "citation_edge",
)


def manifest() -> dict:
    return {"emits": list(EMITS), "consumes": list(CONSUMES)}
