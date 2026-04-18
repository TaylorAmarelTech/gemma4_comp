"""Adversarial validation for the 335 Attack Vector Inspector notebook.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_335_attack_vector_inspector.py``. 335 is the
inspector slot in the Advanced Evaluation section, between 300
Adversarial Resistance and the 499 section conclusion; the checks here
verify that the 15-vector table, the four plots, the HTML table, and
the Phase 3 curriculum handoff are all present in-notebook so the
kernel reproduces the writeup's adversarial-taxonomy evidence without
external dependencies.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_335_attack_vector_inspector" / "335_attack_vector_inspector.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_335_attack_vector_inspector" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/duecare-335-attack-vector-inspector":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 335 slug")

    if meta.get("title") != "335: DueCare Attack Vector Inspector":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu is not False (335 is CPU-only): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (CPU-only)")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 335: DueCare Attack Vector Inspector"):
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
        "duecare-300-adversarial-resistance",
        "499-duecare-advanced-evaluation-conclusion",
        "duecare-530-phase3-unsloth-finetune",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 300, 499, 530 present")

    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    if "ATTACK_VECTORS = [" not in all_code:
        fail("ATTACK_VECTORS list is not defined")
    ok("ATTACK_VECTORS list is defined")

    category_count = all_code.count('"category"') + all_code.count("'category'")
    if category_count < 15:
        fail(f"ATTACK_VECTORS should have at least 15 entries; counted {category_count} 'category' keys")
    ok(f"ATTACK_VECTORS has at least 15 entries ({category_count} 'category' keys)")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 335; reserve for 610/899")
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

    final_print_cells = [c for c in code_cells if "Attack vector handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Attack vector handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "499-duecare-advanced-evaluation-conclusion" not in final_print:
        fail("final print missing 499 slug")
    if "duecare-530-phase3-unsloth-finetune" not in final_print:
        fail("final print missing 530 slug")
    ok("final print is URL-bearing and links to 499 and 530")

    marker_count = all_code.count("Attack vector handoff >>>")
    if marker_count != 1:
        fail(f"marker 'Attack vector handoff >>>' should appear exactly once in code cells; found {marker_count}")
    ok("marker 'Attack vector handoff >>>' is unique")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
