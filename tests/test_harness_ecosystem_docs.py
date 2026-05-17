from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_harness_ecosystem_doc_enumerates_broad_harness_families():
    text = _read("docs/harness_ecosystem.md")
    required_phrases = [
        "Registered harness surfaces",
        "Broader harness families",
        "Content safety response harness",
        "Search anonymization harness",
        "Post-search verification harness",
        "Anonymization/deanonymization review harness",
        "Knowledge ingestion harness",
        "Civil-society fact intake harness",
        "Research graph harness",
        "Synthetic data generator harness",
        "Rubric-polish harness",
        "Fine-tuning harness",
        "Evaluation/judge harness",
        "Report/export harness",
        "Model runtime primitive",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_public_copy_uses_harness_ecosystem_language():
    paths = [
        "apps/duecare-ai.com/app/templates/index.html",
        "apps/duecare-ai.com/app/templates/harness.html",
        "apps/duecare-ai.com/app/templates/mission.html",
        "apps/duecare-ai.com/app/templates/why-gemma.html",
        "packages/duecare-llm-server/src/duecare/server/static/index.html",
        "packages/duecare-llm-chat/src/duecare/chat/static/getting-started.html",
        "packages/duecare-llm-chat/src/duecare/chat/static/index.html",
    ]
    combined = "\n".join(_read(path) for path in paths).lower()
    assert "harness ecosystem" in combined
    assert "run the gemma 4 safety harness" not in combined
    assert "duecare is a gemma 4 safety harness" not in combined


def test_ecosystem_overview_no_longer_claims_one_harness():
    text = _read("docs/ecosystem_overview.md")
    assert "single content-safety harness" not in text
    assert "one harness, four user layers" not in text
    assert "harness ecosystem" in text


def test_legacy_notebook_era_docs_are_archived():
    archive = ROOT / "docs" / "_archive" / "2026-05-16-legacy-notebook-era"
    for name in [
        "notebook_index.md",
        "smoke_test_report_2026-05-02.md",
        "SUBMISSION_READINESS_AUDIT.md",
    ]:
        assert not (ROOT / "docs" / name).exists(), name
        assert (archive / name).exists(), name


def test_current_kaggle_state_points_to_three_active_kernels():
    text = _read("docs/current_kaggle_notebook_state.md")
    assert "exactly three script kernels" in text
    assert "kaggle/01-duecare-exploration-workbench/" in text
    assert "kaggle/02-live-demo/" in text
    assert "kaggle/A-00-omni-experiment-workbench/" in text
    assert "not the active submission path" in text


def test_harness_pattern_active_integration_uses_current_three_kernel_scope():
    text = _read("docs/harness_pattern.md")
    assert "## Active Kaggle Integration" in text
    assert "`01-duecare-exploration-workbench`" in text
    assert "`02-live-demo`" in text
    assert "`A-00-omni-experiment-workbench`" in text
    assert "Legacy minimal-shell kernels" in text
    assert "A-10" not in text


def test_current_entry_docs_do_not_present_archived_appendix_scope():
    for path in ["docs/FOR_PEER_REVIEW.md", "docs/USER_TODO.md"]:
        text = _read(path)
        assert "kaggle/01-duecare-exploration-workbench/" in text
        assert "kaggle/02-live-demo/" in text
        assert "kaggle/A-00-omni-experiment-workbench/" in text
        assert "24 appendix" not in text
        assert "2 core public Kaggle notebooks" not in text
        assert "A-01..A-11" not in text
