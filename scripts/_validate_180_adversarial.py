"""Adversarial validation for the 180 Multimodal Document Inspector.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_180_multimodal_document_inspector.py``. 180 is
the multimodal document inspector between 170 and 199 in the Free Form
Exploration section; the checks here verify the multimodal load cell,
the extraction schema, the twelve-indicator ruleset, and the
three-panel HTML render are all in place.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = (
    ROOT
    / "kaggle"
    / "kernels"
    / "duecare_180_multimodal_document_inspector"
    / "180_multimodal_document_inspector.ipynb"
)
META_PATH = (
    ROOT
    / "kaggle"
    / "kernels"
    / "duecare_180_multimodal_document_inspector"
    / "kernel-metadata.json"
)


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

    if meta.get("id") != "taylorsamarel/duecare-180-multimodal-document-inspector":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 180 slug")

    if meta.get("title") != "180: DueCare Multimodal Document Inspector":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not True:
        fail(f"enable_gpu expected True (180 is T4 kernel): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is True (T4 kernel)")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 180: DueCare Multimodal Document Inspector"):
        fail("cell 0 does not open with canonical H1 title")
    if "\u2014" in cell0.split("\n", 1)[0]:
        fail("cell 0 H1 still contains an em dash")
    ok("cell 0 has canonical H1 title (no em dash)")

    if "<table" not in cell0:
        fail("cell 0 is missing the HTML header table")
    for tag in (
        "<b>Inputs</b>",
        "<b>Outputs</b>",
        "<b>Prerequisites</b>",
        "<b>Runtime</b>",
        "<b>Pipeline position</b>",
    ):
        if tag not in cell0:
            fail(f"cell 0 HTML header missing {tag}")
    ok("cell 0 header has all five expected Field/Value rows")

    required_links = [
        "duecare-170-live-context-injection-playground",
        "199-duecare-free-form-exploration-conclusion",
        "duecare-400-function-calling-multimodal",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 170, 199, 400 present")

    install_cells = [
        c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)
    ]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    if "EXTRACTION_SCHEMA = {" not in all_code:
        fail("EXTRACTION_SCHEMA dict is not defined")
    ok("EXTRACTION_SCHEMA dict is defined")

    if "TRAFFICKING_INDICATORS = [" not in all_code:
        fail("TRAFFICKING_INDICATORS list is not defined")
    ok("TRAFFICKING_INDICATORS list is defined")

    if "def extract_fields(" not in all_code:
        fail("extract_fields function is not defined")
    ok("extract_fields function is defined")

    if "def flag_indicators(" not in all_code:
        fail("flag_indicators function is not defined")
    ok("flag_indicators function is defined")

    indicator_ids = (
        "placement_fee_to_worker",
        "passport_retention",
        "contract_swap",
        "excessive_probation",
        "wage_deduction_beyond_cap",
        "dispute_jurisdiction_abroad",
        "prohibited_broker",
        "age_fraud",
        "language_barrier",
        "confined_housing",
        "document_confiscation",
        "debt_bondage",
    )
    indicator_count = sum(1 for iid in indicator_ids if f"'id': '{iid}'" in all_code)
    if indicator_count < 12:
        fail(
            f"expected 12 named indicator ids in TRAFFICKING_INDICATORS, found {indicator_count}"
        )
    ok(f"TRAFFICKING_INDICATORS has {indicator_count} named indicator ids (>= 12)")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 180; reserve for 610/899")
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

    final_print_cells = [c for c in code_cells if "Multimodal inspection handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Multimodal inspection handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "199-duecare-free-form-exploration-conclusion" not in final_print:
        fail("final print missing 199 slug")
    if "duecare-400-function-calling-multimodal" not in final_print:
        fail("final print missing 400 slug")
    ok("final print is URL-bearing and links to 199 and 400")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
