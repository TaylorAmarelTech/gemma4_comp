"""Adversarial validation for the 540 Fine-tune Delta Visualizer builder.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_540_finetune_delta_visualizer.py``. 540 is the
Phase 3 before/after visualizer in the Model Improvement Opportunities
section; the checks here verify that every video-ready chart the
notebook promises is actually produced, the PUBLISHED_FINETUNE_BASELINE
fallback is present, and the handoff to 599 / 600 is URL-bearing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_540_finetune_delta_visualizer" / "540_finetune_delta_visualizer.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_540_finetune_delta_visualizer" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/duecare-540-finetune-delta-visualizer":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 540 slug")

    if meta.get("title") != "540: DueCare Fine-tune Delta Visualizer":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu is not False: {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (CPU-only)")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 540: DueCare Fine-tune Delta Visualizer"):
        fail("cell 0 does not open with canonical H1 title")
    if "\u2014" in cell0.split("\n", 1)[0]:
        fail("cell 0 H1 still contains an em dash")
    ok("cell 0 has canonical H1 title (no em dash)")

    if "<table" not in cell0:
        fail("cell 0 is missing the HTML header table")
    for tag in ("<b>Inputs</b>", "<b>Outputs</b>", "<b>Prerequisites</b>",
                "<b>Runtime</b>", "<b>Pipeline position</b>"):
        if tag not in cell0:
            fail(f"cell 0 HTML header missing {tag}")
    ok("cell 0 header has all five expected Field/Value rows")

    required_links = [
        "duecare-530-phase3-unsloth-finetune",
        "599-duecare-model-improvement-opportunities-conclusion",
        "600-duecare-results-dashboard",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 530, 599, 600 present")

    if "PUBLISHED_FINETUNE_BASELINE = {" not in all_code:
        fail("PUBLISHED_FINETUNE_BASELINE dict is not defined in code")
    if "PUBLISHED_FINETUNE_BASELINE_SOURCE" not in all_code:
        fail("PUBLISHED_FINETUNE_BASELINE_SOURCE provenance string missing")
    if "PUBLISHED_FINETUNE_BASELINE_DATE" not in all_code:
        fail("PUBLISHED_FINETUNE_BASELINE_DATE provenance string missing")
    ok("PUBLISHED_FINETUNE_BASELINE dict defined with provenance comment")

    if "_hex_to_rgba" not in all_code:
        fail("missing _hex_to_rgba helper for plotly radar fill")
    if "+ '15'" in all_code or "color + '15'" in all_code:
        fail("stale appended-hex-alpha remains in plotly fill")
    ok("_hex_to_rgba helper present; no appended-hex-alpha drift")

    if "SAFETY_DIMENSIONS" not in all_code:
        fail("SAFETY_DIMENSIONS not referenced in code")
    dimension_labels = [
        "Refusal Quality",
        "Legal Accuracy",
        "Completeness",
        "Victim Safety",
        "Cultural Sensitivity",
        "Actionability",
    ]
    for label in dimension_labels:
        if label not in all_text:
            fail(f"missing dimension label {label!r}")
    ok("SAFETY_DIMENSIONS referenced and all six dimension labels present")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 540; reserve for 610/899")
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

    if "DATA SOURCE:" not in all_code:
        fail("data-source banner string 'DATA SOURCE:' missing from code")
    ok("data-source banner string present")

    final_print_cells = [c for c in code_cells if "Finetune delta handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Finetune delta handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "599-duecare-model-improvement-opportunities-conclusion" not in final_print:
        fail("final print missing 599 slug")
    if "600-duecare-results-dashboard" not in final_print:
        fail("final print missing 600 slug")
    ok("final print is URL-bearing and links to 599 and 600")

    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
