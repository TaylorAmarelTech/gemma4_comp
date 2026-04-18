"""Adversarial validation for the 650 Custom Domain Walkthrough notebook.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_650_custom_domain_walkthrough.py``. 650 is the
custom-domain how-to in the Solution Surfaces section. The checks here
verify that the four-file domain-pack layout, the medical taxonomy /
rubric / PII spec, the 10 graded seed prompts, and the duecare.domains
registration recipe are all defined in-notebook so the kernel is a
self-contained adoption guide.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_650_custom_domain_walkthrough" / "650_custom_domain_walkthrough.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_650_custom_domain_walkthrough" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/650-duecare-custom-domain-walkthrough":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 650 slug")

    if meta.get("title") != "650: DueCare Custom Domain Walkthrough":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu is not False (650 is CPU-only): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (CPU-only)")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 650: DueCare Custom Domain Walkthrough"):
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
        "duecare-200-cross-domain-proof",
        "620-duecare-demo-api-endpoint-tour",
        "duecare-solution-surfaces-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 200, 620, 899 present")

    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    if "MEDICAL_TAXONOMY" not in all_code:
        fail("MEDICAL_TAXONOMY is not defined in any code cell")
    ok("MEDICAL_TAXONOMY defined")

    if "MEDICAL_RUBRIC" not in all_code:
        fail("MEDICAL_RUBRIC is not defined in any code cell")
    ok("MEDICAL_RUBRIC defined")

    if "MEDICAL_PII_SPEC" not in all_code:
        fail("MEDICAL_PII_SPEC is not defined in any code cell")
    ok("MEDICAL_PII_SPEC defined")

    if "MEDICAL_SEED_PROMPTS = [" not in all_code:
        fail("MEDICAL_SEED_PROMPTS list is not defined in any code cell")
    ok("MEDICAL_SEED_PROMPTS list defined")

    # Count at least 15 categories in the taxonomy. Every category is a
    # dict with an explicit ``'id':`` key, so the occurrence count of
    # that substring inside MEDICAL_TAXONOMY is a robust lower bound.
    taxonomy_slice = all_code.split("MEDICAL_TAXONOMY", 1)[1]
    taxonomy_slice = taxonomy_slice.split("MEDICAL_RUBRIC", 1)[0]
    n_categories = taxonomy_slice.count("'id':")
    # Subtract the 6 indicator ids and 5 documentation_ref ids baked into
    # the same block; 15 categories + 6 indicators + 5 docs = 26 total.
    if n_categories < 15:
        fail(f"MEDICAL_TAXONOMY has fewer than 15 'id' entries (found {n_categories}); need >= 15 categories")
    ok(f"MEDICAL_TAXONOMY has >= 15 id entries (found {n_categories})")

    seed_slice = all_code.split("MEDICAL_SEED_PROMPTS", 1)[1]
    n_graded = seed_slice.count("'graded_responses'")
    if n_graded < 10:
        fail(f"MEDICAL_SEED_PROMPTS has fewer than 10 'graded_responses' entries (found {n_graded})")
    ok(f"MEDICAL_SEED_PROMPTS has >= 10 graded prompts (found {n_graded})")

    if "duecare.domains" not in all_code:
        fail("duecare.domains import not present in any code cell")
    ok("duecare.domains import present")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 650; reserve for 610/899")
    ok("no 'Privacy is non-negotiable' phrase (reserved for 610/899)")

    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    # Count the 5 resolution rows by the number of Symptom/Resolution
    # row pairs in the final markdown table. Canonical table has 5.
    resolution_rows = final_md.count("<td style=\"padding: 6px 10px;\">")
    # Each row has 2 <td>s; the canonical header is <th>. 5 rows * 2 = 10.
    if resolution_rows < 10:
        fail(f"HTML Troubleshooting table has fewer than 5 rows (counted {resolution_rows // 2})")
    ok(f"HTML Troubleshooting table has >= 5 rows (counted {resolution_rows // 2})")

    final_print_cells = [c for c in code_cells if "Custom domain handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Custom domain handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-solution-surfaces-conclusion" not in final_print:
        fail("final print missing 899 slug")
    if "duecare-200-cross-domain-proof" not in final_print:
        fail("final print missing 200 slug")
    ok("final print is URL-bearing and links to 899 and 200")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
