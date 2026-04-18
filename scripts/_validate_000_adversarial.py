"""Adversarial validation for the 000 DueCare index notebook."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_000_index" / "000_index.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_000_index" / "kernel-metadata.json"


def fail(message: str) -> None:
    print(f"FAIL  {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"OK    {message}")


def _src(cell: dict) -> str:
    source = cell.get("source", [])
    return "".join(source) if isinstance(source, list) else str(source)


def main() -> None:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    cells = nb["cells"]
    md_cells = [cell for cell in cells if cell["cell_type"] == "markdown"]
    code_cells = [cell for cell in cells if cell["cell_type"] == "code"]
    all_md = "\n\n".join(_src(cell) for cell in md_cells)
    all_code = "\n\n".join(_src(cell) for cell in code_cells)
    all_text = all_md + "\n\n" + all_code

    if meta.get("id") != "taylorsamarel/duecare-000-index":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 000 slug")

    if meta.get("title") != "DueCare 000 Index":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    cell0 = _src(md_cells[0])
    if not cell0.startswith("# DueCare 000 Index"):
        fail("cell 0 does not open with the index H1 title")
    ok("cell 0 opens with the index H1 title")

    if "52 Kaggle notebooks" not in cell0:
        fail("cell 0 does not advertise the current tracked notebook count")
    if "11 sections" not in cell0:
        fail("cell 0 does not advertise the current section count")
    ok("cell 0 advertises current notebook and section counts")

    if "coming soon" in all_text.lower():
        fail("stale 'coming soon' copy is still present")
    ok("no stale 'coming soon' copy")

    if "github.com/TaylorAmarelTech/gemma4_comp" not in all_text:
        fail("public GitHub repo link missing")
    if "docs/FOR_JUDGES.md" not in all_text:
        fail("judges guide link missing")
    ok("public repo and judges guide links present")

    for label in ("Judge fast path", "Technical proof path", "Adopter path"):
        if label not in all_text:
            fail(f"recommended route label missing: {label}")
    ok("recommended route table present")

    if "Next section is **Free Form Exploration** (100, 150, 155, 160, 170, 180, 199)." not in all_md:
        fail("background section still has stale next-section continuity")
    ok("background section continuity is current")

    for slug in (
        "620-duecare-demo-api-endpoint-tour",
        "650-duecare-custom-domain-walkthrough",
        "duecare-solution-surfaces-conclusion",
    ):
        if slug not in all_text:
            fail(f"solution-surface link missing: {slug}")
    ok("solution-surface links include 620, 650, and 899")

    install_cells = [cell for cell in code_cells if "duecare-llm-core==0.1.0" in _src(cell)]
    if len(install_cells) != 1:
        fail(f"expected exactly one install cell, found {len(install_cells)}")
    ok("exactly one install cell")

    final_print_cells = [cell for cell in code_cells if "Index handoff >>>" in _src(cell)]
    if not final_print_cells:
        fail("no URL-bearing 'Index handoff >>>' final print")
    final_print = _src(final_print_cells[-1])
    for slug in (
        "010-duecare-quickstart-in-5-minutes",
        "600-duecare-results-dashboard",
        "610-duecare-submission-walkthrough",
    ):
        if slug not in final_print:
            fail(f"final print missing {slug}")
    ok("final print is URL-bearing and links to 010, 600, and 610")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()