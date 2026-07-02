from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


EXPECTED_ROOT_MARKDOWN = {
    "AGENTS.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSES.md",
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


def test_no_python_scripts_live_in_repository_root() -> None:
    root_scripts = sorted(path.name for path in ROOT.glob("*.py"))
    assert root_scripts == []
