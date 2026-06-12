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


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_RESULTS = _ROOT / "RESULTS.md"
_WRITEUP = _ROOT / "docs" / "writeup_draft.md"

# The four A-00 smoke-matrix arm scores read aloud in the video and quoted in
# the writeup + README headline. RESULTS.md is the provenance file README
# points judges at, so it must carry every headline number.
SMOKE_MATRIX_SCORES = ("29.5", "35.6", "26.4", "41.2")


def test_results_md_carries_the_headline_smoke_matrix() -> None:
    results = _RESULTS.read_text(encoding="utf-8")
    writeup = _WRITEUP.read_text(encoding="utf-8")
    for score in SMOKE_MATRIX_SCORES:
        assert f"{score}%" in writeup, (
            f"docs/writeup_draft.md lost headline arm score {score}% — if the "
            f"headline changed on purpose, update SMOKE_MATRIX_SCORES too."
        )
        assert f"{score}%" in results, (
            f"RESULTS.md is missing headline arm score {score}% quoted in the "
            f"writeup/video. The provenance file must carry every headline number."
        )


def test_results_md_reproduce_path_has_no_phantom_git_tag() -> None:
    """RESULTS.md once told judges to `git checkout v0.1.0` — a tag that was
    never cut, so the documented reproduce path errored on its first command.
    Keep the reproduce path runnable."""
    text = _RESULTS.read_text(encoding="utf-8")
    assert "git checkout v0.1.0" not in text
    assert "git rev-parse v0.1.0" not in text
    # the phantom HF repo id (real one is duecare-gemma-4-e4b-safetyjudge)
    assert "Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0" not in text
