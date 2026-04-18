"""Helpers for discovering and summarizing Kaggle kernel notebooks.

This module keeps notebook inventory logic in one place so publishing,
reporting, and docs generation all read the same source of truth:
`kaggle/kernels/*/kernel-metadata.json`.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
KERNELS_DIR = REPO_ROOT / "kaggle" / "kernels"
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"

TITLE_TOKEN_OVERRIDES = {
    "api": "API",
    "duecare": "DueCare",
    "gguf": "GGUF",
    "llm": "LLM",
    "oss": "OSS",
    "rag": "RAG",
}


@dataclass(frozen=True)
class KaggleNotebook:
    """One Kaggle kernel plus its local metadata and mirror state."""

    dir_path: Path
    kernel_id: str
    title: str
    code_file: str
    slug: str
    mirror_path: Path | None

    @property
    def dir_name(self) -> str:
        return self.dir_path.name

    @property
    def notebook_number(self) -> str:
        return Path(self.code_file).stem.split("_", 1)[0]

    @property
    def aligned_title(self) -> str:
        return title_from_slug(self.slug)

    @property
    def title_slug(self) -> str:
        return slugify_title(self.title)

    @property
    def title_matches_slug(self) -> bool:
        return self.title_slug == self.slug

    @property
    def kaggle_url(self) -> str:
        return f"https://www.kaggle.com/code/{self.kernel_id}"


def slugify_title(text: str) -> str:
    """Convert a notebook title into the slug Kaggle will typically derive."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def title_from_slug(slug: str) -> str:
    """Build a slug-aligned title string for kernel metadata."""
    words: list[str] = []
    for token in slug.split("-"):
        if token in TITLE_TOKEN_OVERRIDES:
            words.append(TITLE_TOKEN_OVERRIDES[token])
        elif token.isdigit():
            words.append(token)
        else:
            words.append(token.capitalize())
    return " ".join(words)


def load_kernel_metadata(dir_path: Path) -> dict:
    """Load and validate `kernel-metadata.json` for one kernel directory."""
    meta_path = dir_path / "kernel-metadata.json"
    raw = json.loads(meta_path.read_text(encoding="utf-8"))
    required = {"id", "title", "code_file", "kernel_type", "language"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"{meta_path}: missing required fields {sorted(missing)}")

    code_path = dir_path / raw["code_file"]
    if not code_path.exists():
        raise FileNotFoundError(
            f"{meta_path}: code_file {raw['code_file']!r} does not exist in {dir_path}"
        )
    return raw


def discover_kernel_notebooks(
    kernels_dir: Path = KERNELS_DIR,
    notebooks_dir: Path = NOTEBOOKS_DIR,
) -> list[KaggleNotebook]:
    """Return every tracked Kaggle kernel discovered from metadata files."""
    entries: list[KaggleNotebook] = []
    for dir_path in sorted(child for child in kernels_dir.iterdir() if child.is_dir()):
        meta_path = dir_path / "kernel-metadata.json"
        if not meta_path.exists():
            continue
        meta = load_kernel_metadata(dir_path)
        mirror_path = notebooks_dir / meta["code_file"]
        if not mirror_path.exists():
            mirror_path = None

        kernel_id = meta["id"]
        slug = kernel_id.split("/", 1)[1] if "/" in kernel_id else kernel_id
        entries.append(
            KaggleNotebook(
                dir_path=dir_path,
                kernel_id=kernel_id,
                title=meta["title"],
                code_file=meta["code_file"],
                slug=slug,
                mirror_path=mirror_path,
            )
        )
    return entries


def render_inventory_markdown(entries: list[KaggleNotebook]) -> str:
    """Render a markdown summary of current Kaggle kernel state."""
    mirrored = [entry for entry in entries if entry.mirror_path is not None]
    missing_mirrors = [entry for entry in entries if entry.mirror_path is None]
    legacy_aliases = [
        entry for entry in entries if Path(entry.code_file).stem not in entry.dir_name
    ]
    title_divergences = [entry for entry in entries if not entry.title_matches_slug]
    tracked_mirror_names = {entry.code_file for entry in entries}
    extra_local_notebooks = sorted(
        path.name for path in NOTEBOOKS_DIR.glob("*.ipynb") if path.name not in tracked_mirror_names
    )

    lines: list[str] = []
    lines.append("# Current Kaggle Notebook State")
    lines.append("")
    lines.append("Generated from `kaggle/kernels/*/kernel-metadata.json`. This is the authoritative notebook inventory for the repo.")
    lines.append("Public live-state verification is not embedded in this generated file. Rerun `python scripts/verify_kaggle_urls.py` or check Kaggle kernel status directly for current live results.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Tracked Kaggle kernels: {len(entries)}")
    lines.append(f"- Local mirror notebooks: {len(mirrored)}")
    lines.append(f"- Missing local mirrors: {len(missing_mirrors)}")
    lines.append(f"- Legacy directory/code-file aliases: {len(legacy_aliases)}")
    lines.append(f"- Title/id slug divergences: {len(title_divergences)}")
    lines.append(f"- Extra local notebooks not backed by a kernel: {len(extra_local_notebooks)}")
    lines.append("")

    if missing_mirrors:
        lines.append("## Missing Local Mirrors")
        lines.append("")
        for entry in missing_mirrors:
            lines.append(
                f"- `{entry.dir_name}` -> `{entry.code_file}` ({entry.kernel_id})"
            )
        lines.append("")

    if legacy_aliases:
        lines.append("## Legacy Directory Aliases")
        lines.append("")
        lines.append("These are not necessarily broken, but they are where folder names and notebook filenames diverge.")
        lines.append("")
        for entry in legacy_aliases:
            lines.append(
                f"- `{entry.dir_name}` contains `{entry.code_file}`"
            )
        lines.append("")

    if title_divergences:
        lines.append("## Title and Slug Divergences")
        lines.append("")
        lines.append("These are expected when an already-live Kaggle slug must be preserved even though the display title has been improved.")
        lines.append("")
        for entry in title_divergences:
            lines.append(
                f"- `{entry.dir_name}` title `{entry.title}` -> slug `{entry.title_slug}`; expected `{entry.slug}` (suggested title: `{entry.aligned_title}`)"
            )
        lines.append("")

    if extra_local_notebooks:
        lines.append("## Extra Local Notebooks")
        lines.append("")
        for name in extra_local_notebooks:
            lines.append(f"- `{name}`")
        lines.append("")

    lines.append("## Inventory")
    lines.append("")
    lines.append("| Kernel directory | Notebook ID | Kaggle id | Metadata title | Code file | Local mirror | Live URL |")
    lines.append("|---|---|---|---|---|---|---|")
    for entry in entries:
        mirror_value = entry.mirror_path.name if entry.mirror_path else "missing"
        lines.append(
            f"| `{entry.dir_name}` | `{entry.notebook_number}` | `{entry.kernel_id}` | `{entry.title}` | `{entry.code_file}` | `{mirror_value}` | `{entry.kaggle_url}` |"
        )
    lines.append("")
    return "\n".join(lines)