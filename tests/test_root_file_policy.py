from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


# The only Python permitted at the repository root. `launch.py` is the deliberate one-command
# entry point (`python launch.py`, see docs/QUICK_LAUNCH.md); implementation helpers belong in
# scripts/ and one-off historical helpers in _archive/.
EXPECTED_ROOT_PYTHON = {
    "launch.py",
}

EXPECTED_ROOT_MARKDOWN = {
    "AGENTS.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSES.md",
    "Plans.md",
    "PROJECT_BIBLE.md",
    "README.md",
    "RESULTS.md",
    "ROOT_FILES.md",
    "SECURITY.md",
    "THIRD_PARTY_LICENSES.md",
}


def test_root_markdown_files_are_manifested() -> None:
    root_markdown = {path.name for path in ROOT.glob("*.md")}
    assert root_markdown == EXPECTED_ROOT_MARKDOWN

    manifest = (ROOT / "ROOT_FILES.md").read_text(encoding="utf-8")
    missing = sorted(name for name in root_markdown if f"`{name}`" not in manifest)
    assert missing == []


def test_one_off_copy_helpers_are_archived_not_root_level() -> None:
    assert not (ROOT / "copy_framework.py").exists()
    assert not (ROOT / "copy_reference.py").exists()

    archive = ROOT / "_archive" / "scripts_one_off_2026-04"
    assert (archive / "copy_framework.py").exists()
    assert (archive / "copy_reference.py").exists()


def test_root_python_entry_points_are_allowlisted_and_manifested() -> None:
    """Root Python follows the same allowlist+manifest rule as root markdown.

    The policy is 'no STRAY scripts at the root', not 'no Python at the root': `launch.py` is the
    deliberate one-command entry point and root placement is its whole purpose. A blanket
    `== []` could not express that, so it silently failed from the day the launcher landed.
    Anything new must be added here AND documented in ROOT_FILES.md, which keeps the manifest
    honest instead of letting helpers accumulate at the top level.
    """
    root_python = {path.name for path in ROOT.glob("*.py")}
    assert root_python == EXPECTED_ROOT_PYTHON

    manifest = (ROOT / "ROOT_FILES.md").read_text(encoding="utf-8")
    missing = sorted(name for name in root_python if f"`{name}`" not in manifest)
    assert missing == []
