"""Adversarial validation for the 440 Per-Prompt Rubric Generator rebuild.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_440_per_prompt_rubric_generator.py``. Mirrors the
shape of ``_validate_230_adversarial.py`` and ``_validate_460_adversarial.py``.
440 is the last notebook of the Advanced Prompt-Test Generation section;
the checks here verify that every structural invariant (canonical H1,
HTML header table, cross-links, single install cell, no pseudo-tables,
no "Privacy is non-negotiable", HTML Troubleshooting, URL-bearing final
print with the unique marker) is intact so the next push does not
regress the live Kaggle kernel.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_440_per_prompt_rubric_generator" / "440_per_prompt_rubric_generator.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_440_per_prompt_rubric_generator" / "kernel-metadata.json"


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

    # 1. metadata id targets the canonical 440 live slug.
    if meta.get("id") != "taylorsamarel/duecare-per-prompt-rubric-generator":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    # 2. metadata title canonical.
    if meta.get("title") != "440: DueCare Per-Prompt Rubric Generator":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    # 3. is_private is False.
    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    # 4. enable_gpu is False (CPU kernel).
    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu is not False (440 is CPU-only): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (CPU-only)")

    # 5. dataset sources cover wheels + trafficking-prompts.
    expected_datasets = {"taylorsamarel/duecare-llm-wheels", "taylorsamarel/duecare-trafficking-prompts"}
    if set(meta.get("dataset_sources") or []) & expected_datasets != expected_datasets:
        fail(f"dataset_sources missing expected datasets: {meta.get('dataset_sources')!r}")
    ok("dataset_sources covers wheels + trafficking-prompts")

    # 6. cell 0 opens with canonical H1 (no em dash).
    cell0 = src(md_cells[0])
    if not cell0.startswith("# 440: DueCare Per-Prompt Rubric Generator"):
        fail("cell 0 does not open with canonical H1 title")
    if "\u2014" in cell0.split("\n", 1)[0]:
        fail("cell 0 H1 still contains an em dash")
    ok("cell 0 has canonical H1 title (no em dash)")

    # 7. HTML header table with all five rows.
    if "<table" not in cell0:
        fail("cell 0 is missing the HTML header table")
    for tag in ("<b>Inputs</b>", "<b>Outputs</b>", "<b>Prerequisites</b>", "<b>Runtime</b>", "<b>Pipeline position</b>"):
        if tag not in cell0:
            fail(f"cell 0 HTML header missing {tag}")
    ok("cell 0 header has all five expected Field/Value rows")

    # 8. required cross-link slugs present (100, 410, 430, 460, 520, 530, 699).
    required_links = [
        "duecare-real-gemma-4-on-50-trafficking-prompts",
        "duecare-410-llm-judge-grading",
        "duecare-430-rubric-evaluation",
        "460-duecare-citation-verifier",
        "duecare-520-phase3-curriculum-builder",
        "duecare-530-phase3-unsloth-finetune",
        "duecare-advanced-prompt-test-generation-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 100, 410, 430, 460, 520, 530, 699 present")

    # 9. exactly one install cell (hardener-injected).
    install_cells = [c for c in code_cells if "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    # 10. "Privacy is non-negotiable" banned (reserved for 610/899).
    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 440; reserve for 610/899")
    ok("no 'Privacy is non-negotiable' phrase (reserved for 610/899)")

    # 11. no "| | |" markdown pseudo-table anywhere.
    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    # 12. HTML Troubleshooting table present with Symptom/Resolution columns.
    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    # 13. URL-bearing final print hands off to 699 and 520 verbatim.
    final_print_cells = [c for c in code_cells if "Per-prompt rubric handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Per-prompt rubric handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-advanced-prompt-test-generation-conclusion" not in final_print:
        fail("final print missing 699 slug")
    if "duecare-520-phase3-curriculum-builder" not in final_print:
        fail("final print missing 520 slug")
    default_marker = "Per-prompt rubric generation complete"
    for c in code_cells:
        if default_marker in src(c):
            fail("hardener default print was NOT patched")
    ok("final print is URL-bearing and links to 699 and 520; default print patched out")

    # 14. marker 'Per-prompt rubric handoff >>>' is unique across code cells.
    marker_count = all_code.count("Per-prompt rubric handoff >>>")
    if marker_count != 1:
        fail(f"marker 'Per-prompt rubric handoff >>>' should appear exactly once in code cells; found {marker_count}")
    ok("marker 'Per-prompt rubric handoff >>>' is unique")

    # 15. "What just happened" + Key findings canonical trailing block.
    if "## What just happened" not in final_md:
        fail("trailing cell missing '## What just happened' block")
    if "### Key findings" not in final_md:
        fail("trailing cell missing '### Key findings' block")
    ok("trailing cell has 'What just happened' + 'Key findings' blocks")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
