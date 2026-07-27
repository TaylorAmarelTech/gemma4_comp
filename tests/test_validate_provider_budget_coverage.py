"""Static contract tests for primary provider-budget coverage."""

from __future__ import annotations

from pathlib import Path

from scripts import validate_provider_budget_coverage as coverage


def test_live_primary_router_has_budget_coverage() -> None:
    assert coverage.validate() == []


def test_unguarded_transport_is_rejected(tmp_path: Path) -> None:
    router = tmp_path / "router.py"
    router.write_text(
        "\n".join(
            [
                "def ollama_chat(): _http_post_json('x')",
                "def nvidia_chat(): _http_post_json('x')",
                "def openai_compatible_chat(): _http_post_json('x')",
                "def anthropic_chat(): _http_post_json('x')",
            ]
        ),
        encoding="utf-8",
    )
    findings = coverage.validate(router)
    assert len([finding for finding in findings if "outside _budget_attempt" in finding]) == 4
