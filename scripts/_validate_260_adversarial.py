"""Adversarial validation for the 260 RAG Comparison rebuild.

Canonical-shape checks on the notebook emitted by
``scripts/build_showcase_notebooks.py::RAG_CELLS``. Mirrors the shape
of ``_validate_230_adversarial.py``. 260 is a GPU kernel; the checks
here are structural only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_260_rag_comparison" / "260_rag_comparison.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_260_rag_comparison" / "kernel-metadata.json"


def fail(msg: str) -> None:
    print(f"FAIL  {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"OK    {msg}")


def main() -> None:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    cells = nb["cells"]
    md_cells = [c for c in cells if c["cell_type"] == "markdown"]
    code_cells = [c for c in cells if c["cell_type"] == "code"]

    def src(cell):
        s = cell.get("source", [])
        return "".join(s) if isinstance(s, list) else str(s)

    all_md = "\n\n".join(src(c) for c in md_cells)
    all_code = "\n\n".join(src(c) for c in code_cells)
    all_text = all_md + "\n\n" + all_code

    if meta.get("id") != "taylorsamarel/duecare-260-rag-comparison":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    if meta.get("title") != "260: DueCare RAG Comparison":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("enable_gpu") is not True:
        fail(f"enable_gpu expected True (260 is GPU kernel): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is True (GPU kernel)")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 260: DueCare RAG Comparison"):
        fail("cell 0 does not open with canonical H1 title")
    if "\u2014" in cell0.split("\n", 1)[0]:
        fail("cell 0 H1 still contains an em dash")
    ok("cell 0 has canonical H1 title (no em dash)")

    if "<table" not in cell0:
        fail("cell 0 is missing the HTML header table")
    for tag in ("<b>Inputs</b>", "<b>Outputs</b>", "<b>Prerequisites</b>", "<b>Runtime</b>", "<b>Pipeline position</b>"):
        if tag not in cell0:
            fail(f"cell 0 HTML header missing {tag}")
    ok("cell 0 header has all five expected Field/Value rows")

    required_links = [
        "duecare-250-comparative-grading",
        "duecare-270-gemma-generations",
        "duecare-baseline-text-comparisons-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 250, 270, 399 present")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 260; reserve for 610/899")
    ok("no 'Privacy is non-negotiable' phrase (reserved for 610/899)")

    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    final_print_cells = [c for c in code_cells if "RAG comparison complete" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'RAG comparison complete' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-270-gemma-generations" not in final_print:
        fail("final print missing 270 slug")
    if "duecare-baseline-text-comparisons-conclusion" not in final_print:
        fail("final print missing 399 slug")
    ok("final print is URL-bearing and links to 270 and 399")

    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
