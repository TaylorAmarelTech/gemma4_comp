"""Real-not-faked guard: the canonical knowledge-surface counts in
docs/KNOWLEDGE_SURFACE_VERIFICATION.md must match the LIVE surfaces.

Counts drift constantly as rules/docs are added; this test fails the moment a
documented count diverges from the code, so a judge running
`scripts/verify_knowledge_surfaces.py` can never see a number the docs
contradict. When a surface grows, update the doc row and this test passes.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from duecare.chat.harness import GREP_RULES, RAG_CORPUS

_DOC = (
    pathlib.Path(__file__).resolve().parents[1]
    / "docs" / "KNOWLEDGE_SURFACE_VERIFICATION.md"
)


def _doc_count(label: str) -> int:
    """Pull the integer from the `| `LABEL` | NNN ...|` counts-table row."""
    text = _DOC.read_text(encoding="utf-8")
    m = re.search(rf"\|\s*`{re.escape(label)}`[^|]*\|\s*(\d[\d,]*)", text)
    assert m, f"no counts-table row for `{label}` in {_DOC.name}"
    return int(m.group(1).replace(",", ""))


@pytest.mark.parametrize(
    "label, live",
    [
        ("GREP_RULES", len(GREP_RULES)),
        ("RAG_CORPUS", len(RAG_CORPUS)),
    ],
)
def test_doc_counts_match_live_surfaces(label: str, live: int) -> None:
    documented = _doc_count(label)
    assert documented == live, (
        f"docs/KNOWLEDGE_SURFACE_VERIFICATION.md says {label}={documented} "
        f"but the live surface has {live}. Update the doc row (and any other "
        f"count-bearing docs) so the published numbers stay real-not-faked."
    )


def test_grep_section_heading_count_matches() -> None:
    """The `### GREP_RULES (NNN detection patterns)` heading must also match."""
    text = _DOC.read_text(encoding="utf-8")
    m = re.search(r"###\s+`GREP_RULES`\s+\((\d+)\s+detection patterns\)", text)
    assert m, "GREP_RULES section heading with a pattern count not found"
    assert int(m.group(1)) == len(GREP_RULES), (
        f"GREP_RULES section heading says {m.group(1)} but live is {len(GREP_RULES)}."
    )
