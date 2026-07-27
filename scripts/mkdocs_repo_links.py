"""Resolve MkDocs links that intentionally point outside ``docs/``.

Markdown files in this repository link to source, configuration, Kaggle, and
package files. Those relative links work in GitHub's repository view, but
MkDocs treats every target outside ``docs_dir`` as missing. During a Pages
build this hook rewrites only existing targets inside this repository to their
canonical GitHub source URL. Missing targets remain untouched so ``--strict``
continues to fail on genuine link mistakes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, urlsplit, urlunsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
REPO_SOURCE_URL = "https://github.com/TaylorAmarelTech/gemma4_comp"

_MARKDOWN_REPO_LINK = re.compile(
    r"(?<!`)(?P<prefix>!?\[[^\]\n]*\]\()"
    r"(?P<target>(?:(?:\.\.?/)+)?[^)#\s][^)\s]*)"
    r"(?P<suffix>(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\))"
)
_PROTECTED_MARKDOWN = re.compile(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)")


class _Inclusion(Protocol):
    def is_excluded(self) -> bool: ...


class _MkDocsFile(Protocol):
    abs_src_path: str
    inclusion: _Inclusion


class _MkDocsPage(Protocol):
    file: _MkDocsFile


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _github_target(
    target: str,
    source_path: Path,
    repo_root: Path,
    docs_root: Path,
    included_docs: set[Path] | None,
) -> str | None:
    wrapped = target.startswith("<") and target.endswith(">")
    raw_target = target[1:-1] if wrapped else target
    split = urlsplit(raw_target)
    if split.scheme or split.netloc or not split.path:
        return None

    resolved = (source_path.parent / split.path).resolve()
    if not _inside(resolved, repo_root) or not resolved.exists():
        return None
    if _inside(resolved, docs_root) and (
        included_docs is None or resolved in included_docs or resolved.is_dir()
    ):
        return None

    kind = "tree" if resolved.is_dir() else "blob"
    repository_path = quote(resolved.relative_to(repo_root).as_posix(), safe="/")
    repository_url = urlsplit(REPO_SOURCE_URL)
    rewritten = urlunsplit(
        (
            repository_url.scheme,
            repository_url.netloc,
            f"{repository_url.path}/{kind}/master/{repository_path}",
            split.query,
            split.fragment,
        )
    )
    return f"<{rewritten}>" if wrapped else rewritten


def rewrite_repo_links(
    markdown: str,
    source_path: Path,
    *,
    repo_root: Path = REPO_ROOT,
    docs_root: Path = DOCS_ROOT,
    included_docs: set[Path] | None = None,
) -> str:
    """Rewrite valid source links unavailable to Pages while preserving code."""

    def rewrite_segment(segment: str) -> str:
        def replace(match: re.Match[str]) -> str:
            target = match.group("target")
            rewritten = _github_target(
                target,
                source_path,
                repo_root,
                docs_root,
                included_docs,
            )
            if rewritten is None:
                return match.group(0)
            return f"{match.group('prefix')}{rewritten}{match.group('suffix')}"

        return _MARKDOWN_REPO_LINK.sub(replace, segment)

    parts = _PROTECTED_MARKDOWN.split(markdown)
    return "".join(part if index % 2 else rewrite_segment(part) for index, part in enumerate(parts))


def on_page_markdown(
    markdown: str,
    page: _MkDocsPage,
    files: Iterable[_MkDocsFile],
    **_kwargs: object,
) -> str:
    """MkDocs hook entry point."""

    included_docs = {
        Path(file.abs_src_path).resolve() for file in files if not file.inclusion.is_excluded()
    }
    return rewrite_repo_links(
        markdown,
        Path(page.file.abs_src_path),
        included_docs=included_docs,
    )
