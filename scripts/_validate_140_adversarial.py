"""Adversarial validation for the 140 Evaluation Mechanics notebook.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_140_evaluation_mechanics.py``. 140 is the
explainer slot between 130 and 299 in the Baseline Text Evaluation
Framework section; the checks here verify that every scoring method
referenced downstream is defined and exercised in-notebook.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_140_evaluation_mechanics" / "140_evaluation_mechanics.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_140_evaluation_mechanics" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/140-duecare-evaluation-mechanics":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id matches live 140 slug (NNN-duecare-* canonical)")

    if meta.get("title") != "140: DueCare Evaluation Mechanics":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    expected_datasets = {"taylorsamarel/duecare-llm-wheels", "taylorsamarel/duecare-trafficking-prompts"}
    if set(meta.get("dataset_sources") or []) & expected_datasets != expected_datasets:
        fail(f"dataset_sources missing expected datasets: {meta.get('dataset_sources')!r}")
    ok("dataset_sources covers wheels + trafficking-prompts")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 140: DueCare Evaluation Mechanics"):
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
        "duecare-prompt-corpus-exploration",
        "duecare-real-gemma-4-on-50-trafficking-prompts",
        "duecare-250-comparative-grading",
        "duecare-270-gemma-generations",
        "duecare-410-llm-judge-grading",
        "duecare-baseline-text-evaluation-framework-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 130, 100, 250, 270, 410, 299 present")

    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    if "DIMENSION_WEIGHTS = {" not in all_code:
        fail("DIMENSION_WEIGHTS dict is not defined")
    ok("DIMENSION_WEIGHTS dict is defined")

    if "SAFETY_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())" not in all_code:
        fail("SAFETY_DIMENSIONS not derived from DIMENSION_WEIGHTS")
    ok("SAFETY_DIMENSIONS derived from DIMENSION_WEIGHTS")

    if "sum(DIMENSION_WEIGHTS.values()) - 1.0" not in all_code:
        fail("weighted-rubric assertion (sum == 1.0) is missing")
    ok("DIMENSION_WEIGHTS sum is asserted == 1.0")

    for keyword_fn_marker in ("def score_by_keywords", "def classify_v3_teaching"):
        if keyword_fn_marker not in all_code:
            fail(f"missing scoring function: {keyword_fn_marker}")
    ok("keyword scorer + V3 teaching classifier are both defined in-notebook")

    if "_hex_to_rgba" not in all_code:
        fail("missing _hex_to_rgba helper for plotly radar fill")
    ok("_hex_to_rgba helper present")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 140; reserve for 610/899")
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

    final_print_cells = [c for c in code_cells if "Mechanics handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Mechanics handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-baseline-text-evaluation-framework-conclusion" not in final_print:
        fail("final print missing 299 slug")
    if "duecare-real-gemma-4-on-50-trafficking-prompts" not in final_print:
        fail("final print missing 100 slug")
    ok("final print is URL-bearing and links to 299 and 100")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
