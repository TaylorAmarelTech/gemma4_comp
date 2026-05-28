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

    # discover_kernel_notebooks() returns the active set only. The kaggle/
    # tree also carries optional benchmark kernels (03, 04) that have their
    # own kernel-metadata.json, so the active count is pinned explicitly
    # rather than by counting every metadata file under kaggle/.
    assert len(entries) == 3
    for name in (
        "01-duecare-exploration-workbench",
        "02-live-demo",
        "A-00-omni-experiment-workbench",
    ):
        assert (REPO_ROOT / "kaggle" / name / "kernel-metadata.json").exists()
    assert all((entry.dir_path / entry.code_file).exists() for entry in entries)
    assert {entry.dir_name for entry in entries} == {
        "01-duecare-exploration-workbench",
        "02-live-demo",
        "A-00-omni-experiment-workbench",
    }
    assert all(entry.code_file == "kernel.py" for entry in entries)
    assert all(entry.notebook_number == "kernel" for entry in entries)
    assert all(
        entry.kaggle_url.startswith("https://www.kaggle.com/code/taylorsamarel/")
        for entry in entries
    )


def test_render_inventory_markdown_reports_extra_local_notebook() -> None:
    entries = discover_kernel_notebooks()
    markdown = render_inventory_markdown(entries)

    assert f"Active Kaggle script kernels: {len(entries)}" in markdown
    assert "Optional local/archive mirror notebooks:" in markdown
    assert "Kernels without optional mirrors:" in markdown
    assert "Title/id slug divergences:" in markdown
    assert "01-duecare-exploration-workbench" in markdown
    assert "02-live-demo" in markdown
    assert "A-00-omni-experiment-workbench" in markdown
    assert (
        "| Kernel directory | Notebook ID | Kaggle id | Metadata title | "
        "Code file | Optional mirror | Live URL |"
    ) in markdown


def test_kaggle_index_documents_three_active_script_kernels() -> None:
    text = (REPO_ROOT / "kaggle" / "_INDEX.md").read_text(encoding="utf-8")
    assert "Only three Kaggle script kernels are active" in text
    assert "`01-duecare-exploration-workbench`" in text
    assert "`02-live-demo`" in text
    assert "`A-00-omni-experiment-workbench`" in text
    assert "A-01" in text and "not part of active validation" in text


def test_notebook_guide_is_generated_from_current_inventory() -> None:
    from generate_notebook_guide import OUTPUT_PATH, render_notebook_guide

    rendered = render_notebook_guide(existing_path=OUTPUT_PATH)
    committed = OUTPUT_PATH.read_text(encoding="utf-8")
    entries = discover_kernel_notebooks()

    assert committed == rendered
    assert f"Active script kernels: **{len(entries)}**" in committed
    assert "Public-live active kernels in `kaggle_live_slug_map.json`:" in committed
    for entry in entries:
        display_id = entry.notebook_number if entry.notebook_number != "kernel" else entry.dir_name
        assert f"| `{display_id}` | {entry.title} |" in committed
