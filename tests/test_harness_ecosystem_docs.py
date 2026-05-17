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
