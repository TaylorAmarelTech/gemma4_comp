"""Validate canonical public messaging across judge-facing surfaces.

This is a drift check, not a content generator. Canonical outcomes, lanes,
public component names, counts, and concrete sensitive-data wording live in
``configs/duecare/canonical_messaging.yaml``. When those concepts change,
update the config first, then update rendered docs/templates until this check
passes.
"""

from __future__ import annotations

import sys
from html import unescape
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "duecare" / "canonical_messaging.yaml"


def _load_config() -> dict[str, Any]:
    """Load the canonical messaging contract."""
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise TypeError("canonical_messaging.yaml must contain a mapping")
    return value


def _read(relative_path: str) -> str:
    """Read a workspace-relative text file."""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _glob_files(pattern: str) -> list[Path]:
    """Return files matching a workspace-relative glob pattern."""
    if "*" not in pattern and "?" not in pattern and "[" not in pattern:
        path = ROOT / pattern
        return [path] if path.exists() else []
    return sorted(path for path in ROOT.glob(pattern) if path.is_file())


def _is_allowed_route_reference(line: str) -> bool:
    """Allow the legacy route slug while banning it as visible explanatory copy."""
    lowered = line.lower()
    return "/privacy-boundary" in lowered and "privacy boundary" not in lowered


def _validate_forbidden_phrases(config: dict[str, Any]) -> list[str]:
    """Find vague or deprecated wording in active public surfaces."""
    validation = config.get("validation", {})
    data_handling = config.get("data_handling", {})
    phrases = [str(item).lower() for item in data_handling.get("avoid_as_visible_copy", [])]
    failures: list[str] = []

    for pattern in validation.get("forbidden_phrase_globs", []):
        for path in _glob_files(str(pattern)):
            relative = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if _is_allowed_route_reference(line):
                    continue
                lowered = line.lower()
                for phrase in phrases:
                    if phrase in lowered:
                        failures.append(f"{relative}:{line_number}: avoid vague/deprecated copy: {phrase}")
    return failures


def _validate_lane_order(config: dict[str, Any]) -> list[str]:
    """Ensure the five lane labels appear in canonical order where required."""
    labels = [str(item["label"]) for item in config.get("lanes", [])]
    failures: list[str] = []
    for relative_path in config.get("validation", {}).get("lane_order_files", []):
        text = unescape(_read(str(relative_path)))
        positions = [text.find(label) for label in labels]
        missing = [label for label, index in zip(labels, positions, strict=True) if index < 0]
        if missing:
            failures.append(f"{relative_path}: missing lane label(s): {', '.join(missing)}")
            continue
        if positions != sorted(positions):
            failures.append(f"{relative_path}: lane labels are not in canonical order")
    return failures


def _validate_required_substrings(config: dict[str, Any]) -> list[str]:
    """Check required source-of-truth and concrete data-handling phrases."""
    failures: list[str] = []
    required = config.get("validation", {}).get("required_substrings", {})
    for relative_path, substrings in required.items():
        text = _read(str(relative_path))
        for substring in substrings:
            if str(substring) not in text:
                failures.append(f"{relative_path}: missing required phrase: {substring}")
    return failures


def _validate_globs(config: dict[str, Any]) -> list[str]:
    """Fail fast if a configured glob stops matching files."""
    failures: list[str] = []
    validation = config.get("validation", {})
    for key in ("forbidden_phrase_globs",):
        for pattern in validation.get(key, []):
            if not _glob_files(str(pattern)):
                failures.append(f"{key}: pattern matched no files: {pattern}")
    for relative_path in validation.get("lane_order_files", []):
        if not (ROOT / str(relative_path)).exists():
            failures.append(f"lane_order_files: missing file: {relative_path}")
    for relative_path in validation.get("required_substrings", {}):
        if not (ROOT / str(relative_path)).exists():
            failures.append(f"required_substrings: missing file: {relative_path}")
    return failures


def main() -> int:
    """Run the public messaging validation checks."""
    config = _load_config()
    failures = []
    failures.extend(_validate_globs(config))
    failures.extend(_validate_forbidden_phrases(config))
    failures.extend(_validate_lane_order(config))
    failures.extend(_validate_required_substrings(config))

    if failures:
        print("Public messaging validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Public messaging validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
