from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_validator() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "validate_public_surface.py"
    spec = importlib.util.spec_from_file_location("validate_public_surface", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_file_allow_marker_accepts_header_html_comment() -> None:
    validator = _load_validator()

    text = "\n".join(
        [
            "# duecare-llm-research-tools",
            "",
            "<!-- audit-allow-file:drift",
            "reason: documents a real legacy symbol.",
            "-->",
            "",
            "Body text can include drift terms like OpenClaw.",
        ]
    )

    assert validator._has_file_allow(text)


def test_file_allow_marker_ignores_body_examples() -> None:
    validator = _load_validator()

    text = "\n".join(
        [
            "# Public-surface audit",
            "",
            "This doc explains how to allowlist a whole file.",
            "",
            "```markdown",
            "<!-- audit-allow-file:drift",
            "reason: example only.",
            "-->",
            "```",
        ]
    )

    assert not validator._has_file_allow(text)


def test_file_allow_marker_ignores_tilde_fence_examples() -> None:
    validator = _load_validator()

    text = "\n".join(
        [
            "# Public-surface audit",
            "",
            "~~~markdown",
            "<!-- audit-allow-file:drift",
            "reason: example only.",
            "-->",
            "~~~",
        ]
    )

    assert not validator._has_file_allow(text)


def test_file_allow_marker_ignores_comment_after_header_window() -> None:
    validator = _load_validator()

    text = "\n".join(
        [
            "# Audit docs",
            "line 2",
            "line 3",
            "line 4",
            "line 5",
            "line 6",
            "line 7",
            "line 8",
            "line 9",
            "line 10",
            "line 11",
            "line 12",
            "<!-- audit-allow-file:drift -->",
        ]
    )

    assert not validator._has_file_allow(text)


def test_file_allow_marker_ignores_non_comment_header_text() -> None:
    validator = _load_validator()

    text = "\n".join(
        [
            "# Audit docs",
            "The literal token audit-allow-file:drift is documented here.",
            "",
            "Body text.",
        ]
    )

    assert not validator._has_file_allow(text)
