"""Regression tests for Kaggle kernel inventory helpers."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from kaggle_notebook_utils import discover_kernel_notebooks, render_inventory_markdown


def test_discover_kernel_notebooks_finds_current_inventory() -> None:
    entries = discover_kernel_notebooks()

    assert len(entries) == 77
    assert all(entry.mirror_path is not None for entry in entries)
    assert any(entry.dir_name == "duecare_000_index" for entry in entries)
    assert any(entry.dir_name == "duecare_005_glossary" for entry in entries)
    assert any(entry.code_file == "270_gemma_generations.ipynb" for entry in entries)
    assert any(entry.dir_name == "strm_01_prompt_test_generation" for entry in entries)
    assert all(
        entry.notebook_number == "strm"
        or (entry.notebook_number.isdigit() and len(entry.notebook_number) == 3)
        for entry in entries
    )
    assert all(entry.kaggle_url.startswith("https://www.kaggle.com/code/taylorsamarel/") for entry in entries)


def test_render_inventory_markdown_reports_extra_local_notebook() -> None:
    markdown = render_inventory_markdown(discover_kernel_notebooks())

    assert "Tracked Kaggle kernels: 77" in markdown
    assert "Local mirror notebooks: 77" in markdown
    assert "Missing local mirrors: 0" in markdown
    assert "Title/id slug divergences:" in markdown
    assert "strm_01_prompt_test_generation" in markdown
    assert "| Kernel directory | Notebook ID | Kaggle id | Metadata title | Code file | Local mirror | Live URL |" in markdown


def test_index_builder_live_counts_exclude_planned_placeholders() -> None:
    from build_index_notebook import (
        LIVE_KERNEL_SLUGS,
        _coverage_table_rows,
        _live_notebook_count,
    )

    rows = {str(row["section"]): row for row in _coverage_table_rows()}

    assert _live_notebook_count() == len(LIVE_KERNEL_SLUGS)
    assert rows["400 Baseline Image Evaluation Framework"]["live"] == 0
    assert rows["500 Baseline Image Comparisons"]["live"] == 0


def test_notebook_guide_is_generated_from_current_inventory() -> None:
    from generate_notebook_guide import OUTPUT_PATH, render_notebook_guide

    rendered = render_notebook_guide(existing_path=OUTPUT_PATH)
    committed = OUTPUT_PATH.read_text(encoding="utf-8")
    entries = discover_kernel_notebooks()

    assert committed == rendered
    assert "Tracked kernels: **77**" in committed
    assert "Public-live notebooks in `kaggle_live_slug_map.json`: **49**" in committed
    for entry in entries:
        assert f"| `{entry.notebook_number}` | {entry.title} |" in committed