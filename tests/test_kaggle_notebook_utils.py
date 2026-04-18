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

    assert len(entries) == 29
    assert all(entry.mirror_path is not None for entry in entries)
    assert any(entry.dir_name == "duecare_000_index" for entry in entries)
    assert any(entry.dir_name == "duecare_005_glossary" for entry in entries)
    assert any(entry.code_file == "270_gemma_generations.ipynb" for entry in entries)
    assert all(entry.notebook_number.isdigit() and len(entry.notebook_number) == 3 for entry in entries)
    assert all(entry.kaggle_url.startswith("https://www.kaggle.com/code/taylorsamarel/") for entry in entries)


def test_render_inventory_markdown_reports_extra_local_notebook() -> None:
    markdown = render_inventory_markdown(discover_kernel_notebooks())

    assert "Tracked Kaggle kernels: 29" in markdown
    assert "Missing local mirrors: 0" in markdown
    assert "Title/id slug divergences:" in markdown
    assert "29 OK, 0 FAIL" in markdown
    assert "| Kernel directory | Notebook ID | Kaggle id | Metadata title | Code file | Local mirror | Live URL |" in markdown