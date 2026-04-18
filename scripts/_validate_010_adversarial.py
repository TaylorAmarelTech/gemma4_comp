"""Adversarial validation for the 010 DueCare Quickstart notebook.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_010_quickstart.py``. 010 is the first
notebook a new user opens; this validator enforces the same
structural invariants as ``_validate_200_adversarial.py`` and
``_validate_230_adversarial.py``, adapted to 010's quickstart
workflow (CPU-only, no DIMENSION_WEIGHTS).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_010_quickstart" / "010_quickstart.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_010_quickstart" / "kernel-metadata.json"


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

    # 1. metadata id is the canonical 010 live slug.
    if meta.get("id") != "taylorsamarel/010-duecare-quickstart-in-5-minutes":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    # 2. metadata title canonical.
    if meta.get("title") != "010: DueCare Quickstart in 5 Minutes":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    # 3. is_private is False.
    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    # 4. cell 0 opens with canonical H1 (no em dash).
    cell0 = src(md_cells[0])
    if not (cell0.startswith("# 010:") or cell0.startswith("# DueCare 010")):
        fail("cell 0 does not open with canonical '# 010:' or '# DueCare 010' H1 title")
    if "\u2014" in cell0.split("\n", 1)[0]:
        fail("cell 0 H1 still contains an em dash")
    ok("cell 0 has canonical H1 title (no em dash)")

    # 5. HTML header table with all five rows.
    if "<table" not in cell0:
        fail("cell 0 is missing the HTML header table")
    for tag in ("<b>Inputs</b>", "<b>Outputs</b>", "<b>Prerequisites</b>", "<b>Runtime</b>", "<b>Pipeline position</b>"):
        if tag not in cell0:
            fail(f"cell 0 HTML header missing {tag}")
    ok("cell 0 header has all five expected Field/Value rows")

    # 6. required cross-link slugs (000, 099, 100, 110, 200).
    required_links = [
        "duecare-000-index",
        "099-duecare-orientation-and-background-and-package-setup-conclusion",
        "duecare-real-gemma-4-on-50-trafficking-prompts",
        "00a-duecare-prompt-prioritizer-data-pipeline",
        "duecare-200-cross-domain-proof",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 000, 099, 100, 110, 200 present")

    # 7. "Privacy is non-negotiable" banned outside 610/899.
    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 010; reserve for 610/899")
    ok("no 'Privacy is non-negotiable' phrase (reserved for 610/899)")

    # 8. no "| | |" markdown pseudo-table anywhere.
    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    # 9. HTML Troubleshooting table present in the final markdown cell.
    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    # 10. URL-bearing final print: at least one code cell prints a kaggle URL
    # that references a downstream cross-link slug.
    url_print_cells = [
        c for c in code_cells
        if "print(" in src(c) and any(slug in src(c) for slug in required_links)
    ]
    if not url_print_cells:
        fail("no URL-bearing final print referencing a cross-link slug")
    ok("URL-bearing final print references at least one cross-link slug")

    # 11. exactly one install cell (hardener-injected).
    install_cells = [
        c for c in code_cells
        if "pip install" in src(c).lower()
        or "PACKAGES = [" in src(c)
        or ("duecare-llm" in src(c) and "subprocess.check_call" in src(c))
    ]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
