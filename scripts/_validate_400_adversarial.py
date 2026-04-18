"""Adversarial validation for the 400 Function Calling + Multimodal rebuild.

Canonical-shape checks on the notebook emitted by
``scripts/build_showcase_notebooks.py::FC_CELLS``. Mirrors the shape of
``_validate_230_adversarial.py``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_400_function_calling_multimodal" / "400_function_calling_multimodal.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_400_function_calling_multimodal" / "kernel-metadata.json"


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

    # 1. metadata id targets the canonical 400 live slug.
    if meta.get("id") != "taylorsamarel/duecare-400-function-calling-multimodal":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    # 2. metadata title canonical.
    if meta.get("title") != "400: DueCare Function Calling and Multimodal":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    # 3. dataset sources cover wheels + trafficking-prompts.
    expected_datasets = {"taylorsamarel/duecare-llm-wheels", "taylorsamarel/duecare-trafficking-prompts"}
    if set(meta.get("dataset_sources") or []) & expected_datasets != expected_datasets:
        fail(f"dataset_sources missing expected datasets: {meta.get('dataset_sources')!r}")
    ok("dataset_sources covers wheels + trafficking-prompts")

    # 4. enable_gpu is False (scripted-scenario kernel).
    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu expected False (400 is CPU kernel): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (CPU kernel)")

    # 5. cell 0 opens with canonical H1 (no em dash).
    cell0 = src(md_cells[0])
    if not cell0.startswith("# 400: DueCare Function Calling and Multimodal"):
        fail("cell 0 does not open with canonical H1 title")
    if "\u2014" in cell0.split("\n", 1)[0]:
        fail("cell 0 H1 still contains an em dash")
    ok("cell 0 has canonical H1 title (no em dash)")

    # 6. HTML header table with all five rows.
    if "<table" not in cell0:
        fail("cell 0 is missing the HTML header table")
    for tag in ("<b>Inputs</b>", "<b>Outputs</b>", "<b>Prerequisites</b>", "<b>Runtime</b>", "<b>Pipeline position</b>"):
        if tag not in cell0:
            fail(f"cell 0 HTML header missing {tag}")
    ok("cell 0 header has all five expected Field/Value rows")

    # 7. required cross-link slugs present (300, 335, 410, 420, 499, 000).
    required_links = [
        "duecare-300-adversarial-resistance",
        "335-duecare-attack-vector-inspector",
        "duecare-410-llm-judge-grading",
        "duecare-420-conversation-testing",
        "499-duecare-advanced-evaluation-conclusion",
        "duecare-000-index",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 300, 335, 410, 420, 499, 000 present")

    # 8. exactly one install cell (hardener-injected).
    install_cells = [c for c in code_cells if "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    # 9. "Privacy is non-negotiable" banned in advanced-evaluation-notebook text.
    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 400; reserve for 610/899")
    ok("no 'Privacy is non-negotiable' phrase (reserved for 610/899)")

    # 10. no "| | |" markdown pseudo-table anywhere.
    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    # 11. HTML Troubleshooting table present with Symptom/Resolution columns.
    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    # 12. URL-bearing final print hands off to 410 and 499 verbatim.
    final_print_cells = [c for c in code_cells if "Function-calling handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Function-calling handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-410-llm-judge-grading" not in final_print:
        fail("final print missing 410 slug")
    if "499-duecare-advanced-evaluation-conclusion" not in final_print:
        fail("final print missing 499 slug")
    default_marker = "Function-calling and multimodal demo complete"
    for c in code_cells:
        if default_marker in src(c):
            fail("hardener default print was NOT patched")
    ok("final print is URL-bearing and links to 410 and 499; default print patched out")

    # 13. "What just happened" + Key findings canonical trailing block.
    if "## What just happened" not in final_md:
        fail("trailing cell missing '## What just happened' block")
    if "### Key findings" not in final_md:
        fail("trailing cell missing '### Key findings' block")
    ok("trailing cell has 'What just happened' + 'Key findings' blocks")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
