"""Per-harness grading rubric + golden examples for chat.

A knowledge-builder or bench-and-tune kernel picks ``rubric`` and
``examples`` from this module to run targeted evaluations on this
harness's safety task.
"""
from __future__ import annotations


# Each rubric dim: {name, weight, description, pass_criteria}
rubric: list[dict] = []

# Each example: {input, expected_output, expected_layers_fired, notes}
examples: list[dict] = []


def summary() -> dict:
    return {
        "harness": "chat",
        "n_rubric_dims": len(rubric),
        "n_examples": len(examples),
    }
