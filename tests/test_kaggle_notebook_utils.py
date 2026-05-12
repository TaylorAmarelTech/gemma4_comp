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
    expected_count = len(
        list((REPO_ROOT / "kaggle" / "kernels").glob("*/kernel-metadata.json"))
    )

    assert len(entries) == expected_count
    assert expected_count >= 9
    assert all((entry.dir_path / entry.code_file).exists() for entry in entries)
    assert any(entry.dir_name == "duecare_010_quickstart" for entry in entries)
    assert any(entry.dir_name == "duecare_695_custom_domain_adoption" for entry in entries)
    assert any(entry.code_file == "610_submission_walkthrough.ipynb" for entry in entries)
    assert all(
        entry.notebook_number.isdigit() and len(entry.notebook_number) == 3
        for entry in entries
    )
    assert all(
        entry.kaggle_url.startswith("https://www.kaggle.com/code/taylorsamarel/")
        for entry in entries
    )


def test_render_inventory_markdown_reports_extra_local_notebook() -> None:
    entries = discover_kernel_notebooks()
    markdown = render_inventory_markdown(entries)

    assert f"Tracked Kaggle kernels: {len(entries)}" in markdown
    assert "Optional local/archive mirror notebooks:" in markdown
    assert "Kernels without optional mirrors:" in markdown
    assert "Title/id slug divergences:" in markdown
    assert "duecare_010_quickstart" in markdown
    assert "duecare_695_custom_domain_adoption" in markdown
    assert (
        "| Kernel directory | Notebook ID | Kaggle id | Metadata title | "
        "Code file | Optional mirror | Live URL |"
    ) in markdown


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
    assert f"Tracked kernels: **{len(entries)}**" in committed
    assert "Public-live notebooks in `kaggle_live_slug_map.json`:" in committed
    for entry in entries:
        assert f"| `{entry.notebook_number}` | {entry.title} |" in committed