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


# Judge-facing markdown must never carry double-encoded UTF-8 (mojibake).
# README once rendered its headline result as 'Stock Gemma 4 2B 29.5% Â·' on
# GitHub — a cp1252 round-trip in some tool re-corrupts these silently, so
# the guard fails loud. Scoped to the five judge-facing files on purpose.
_JUDGE_FACING_DOCS = (
    "README.md",
    "docs/FOR_KAGGLE_JUDGES.md",
    "docs/FOR_PEER_REVIEW.md",
    "docs/writeup_draft.md",
    "RESULTS.md",
)
_MOJIBAKE_MARKERS = ("â€", "Â·", "â†", "ðŸ")


@pytest.mark.parametrize("rel", _JUDGE_FACING_DOCS)
def test_judge_facing_docs_have_no_mojibake(rel: str) -> None:
    text = (_ROOT / rel).read_text(encoding="utf-8")
    for marker in _MOJIBAKE_MARKERS:
        assert marker not in text, (
            f"{rel} contains double-encoded UTF-8 marker {marker!r}. Re-run a "
            f"byte-level repair (BOM-strip + sloppy-cp1252 re-encode, gate on "
            f"strict UTF-8 decode) and find which tool wrote cp1252."
        )


def test_judges_doc_counts_match_live_surfaces() -> None:
    """docs/FOR_KAGGLE_JUDGES.md quotes the GREP/RAG counts in three
    phrasings; each must equal the live surface (the 165+/55+ era understated
    the writeup's 439/859 by 2.7-15x, which read as inflation)."""
    text = (_ROOT / "docs" / "FOR_KAGGLE_JUDGES.md").read_text(encoding="utf-8")
    grep_counts = re.findall(
        r"(\d[\d,]*)\s+(?:hand-curated trafficking-pattern rules|GREP rules)", text)
    assert grep_counts, "no GREP-rule count phrase found in FOR_KAGGLE_JUDGES.md"
    for found in grep_counts:
        assert int(found.replace(",", "")) == len(GREP_RULES), (
            f"FOR_KAGGLE_JUDGES.md says {found} GREP rules but the live "
            f"surface has {len(GREP_RULES)}."
        )
    rag_counts = re.findall(
        r"(\d[\d,]*)(?:-document (?:curated )?RAG corpus|\s+RAG docs)", text)
    assert rag_counts, "no RAG count phrase found in FOR_KAGGLE_JUDGES.md"
    for found in rag_counts:
        assert int(found.replace(",", "")) == len(RAG_CORPUS), (
            f"FOR_KAGGLE_JUDGES.md says {found} RAG documents but the live "
            f"surface has {len(RAG_CORPUS)}."
        )
