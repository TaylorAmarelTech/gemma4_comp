from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "mkdocs_repo_links.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("mkdocs_repo_links", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rewrites_existing_repository_file_and_directory(tmp_path: Path) -> None:
    module = _load_module()
    repo = tmp_path / "repo"
    docs = repo / "docs"
    source = docs / "guide.md"
    package = repo / "packages" / "sample"
    package.mkdir(parents=True)
    docs.mkdir(exist_ok=True)
    source.write_text("guide", encoding="utf-8")
    (package / "README.md").write_text("sample", encoding="utf-8")

    markdown = "[file](../packages/sample/README.md#install) [dir](../packages/sample/)"
    result = module.rewrite_repo_links(
        markdown,
        source,
        repo_root=repo,
        docs_root=docs,
    )

    assert "blob/master/packages/sample/README.md#install" in result
    assert "tree/master/packages/sample" in result


def test_preserves_docs_links_missing_targets_and_code(tmp_path: Path) -> None:
    module = _load_module()
    repo = tmp_path / "repo"
    docs = repo / "docs"
    source = docs / "nested" / "guide.md"
    source.parent.mkdir(parents=True)
    source.write_text("guide", encoding="utf-8")
    (docs / "other.md").write_text("other", encoding="utf-8")

    markdown = "\n".join(
        (
            "[docs](../other.md)",
            "[missing](../../missing.txt)",
            "`[inline](../../README.md)`",
            "```md\n[fenced](../../README.md)\n```",
        )
    )
    result = module.rewrite_repo_links(
        markdown,
        source,
        repo_root=repo,
        docs_root=docs,
    )

    assert result == markdown


def test_rewrites_existing_docs_file_when_pages_excludes_it(tmp_path: Path) -> None:
    module = _load_module()
    repo = tmp_path / "repo"
    docs = repo / "docs"
    source = docs / "guide.md"
    excluded = docs / "legacy.md"
    docs.mkdir(parents=True)
    source.write_text("guide", encoding="utf-8")
    excluded.write_text("legacy", encoding="utf-8")

    result = module.rewrite_repo_links(
        "[legacy](legacy.md)",
        source,
        repo_root=repo,
        docs_root=docs,
        included_docs={source.resolve()},
    )

    assert "blob/master/docs/legacy.md" in result
