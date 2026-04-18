"""Adversarial validation for the 005 DueCare glossary notebook."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_005_glossary" / "005_glossary.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_005_glossary" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/duecare-005-glossary":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 005 slug")

    if meta.get("title") != "005: DueCare Glossary and Reading Map":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if not _src(md_cells[0]).startswith("# 005: DueCare Glossary and Reading Map"):
        fail("cell 1 does not open with the glossary H1 title")
    ok("cell 1 opens with the glossary H1 title")

    if "https://www.kaggle.com/code/taylorsamarel/duecare-010-quickstart" in all_text:
        fail("stale 010 public slug is still present")
    ok("no stale 010 public slug remains")

    if "https://www.kaggle.com/code/taylorsamarel/010-duecare-quickstart-in-5-minutes" not in all_text:
        fail("live 010 public slug missing")
    ok("live 010 public slug is present")

    if "2</td><td style=\"padding: 6px 10px;\"><b>Free Form Exploration</b>" not in all_md:
        fail("section order row 2 is not Free Form Exploration")
    if "3</td><td style=\"padding: 6px 10px;\"><b>Baseline Text Evaluation Framework</b>" not in all_md:
        fail("section order row 3 is not Baseline Text Evaluation Framework")
    ok("section order matches the 000 phase registry")

    # After the 2026-04-17 restructure, Solution Surfaces holds only
    # 610/620/650; 600 sits in its own Results Dashboard section and 899
    # sits in its own Suite Conclusion section.
    if "610 Submission Walkthrough, 620 Demo API Endpoint Tour, 650 Custom Domain Walkthrough" not in all_md:
        fail("solution surfaces row is missing 610 / 620 / 650")
    if "600 Results Dashboard" not in all_md:
        fail("results dashboard section is missing 600")
    ok("Results Dashboard and Solution Surfaces sections are split correctly")

    for label in ("Judge fast path", "Technical proof path", "Adopter path", "Interactive demos"):
        if label not in all_text:
            fail(f"reading-path label missing: {label}")
    ok("current reading-path labels are present")

    if "620 Demo API Endpoint Tour" not in all_text:
        fail("NGO API surface still does not point to 620")
    if "650 Custom Domain Walkthrough" not in all_text:
        fail("case analysis surface still does not point to 650")
    ok("solution-surface glossary terms point to 620 and 650")

    install_cells = [
        cell
        for cell in code_cells
        if "Install the pinned DueCare packages" in _src(cell)
        and "DUECARE_PACKAGES = [package for package in PACKAGES if package.startswith('duecare-')]" in _src(cell)
    ]
    if len(install_cells) != 1:
        fail(f"expected exactly one install cell, found {len(install_cells)}")
    ok("exactly one install cell")

    final_print_cells = [cell for cell in code_cells if "Glossary handoff >>>" in _src(cell)]
    if len(final_print_cells) != 1:
        fail(f"expected exactly one URL-bearing final print cell, found {len(final_print_cells)}")
    final_print = _src(final_print_cells[0])
    if "010-duecare-quickstart-in-5-minutes" not in final_print or "099-duecare-orientation-and-background-and-package-setup-conclusion" not in final_print:
        fail("final print does not link to both 010 and 099")
    ok("final print links to 010 and 099")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()