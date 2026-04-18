"""Adversarial validation for the 270 Gemma Generations rebuild.

Seventeen canonical checks that mirror ``_validate_220_adversarial.py``.
Check 11 is adapted for 270: the rubric in 270 is the V3 6-band
classifier, not the DIMENSION_WEIGHTS scorer, so the weighted-rubric
check becomes the ``BANDS`` tuple plus a ``PUBLISHED_BASELINE`` fallback
dict check. Every other check is identical in shape to 230/240.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_270_gemma_generations" / "270_gemma_generations.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_270_gemma_generations" / "kernel-metadata.json"


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

    # 1. metadata id is the canonical 270 live slug.
    if meta.get("id") != "taylorsamarel/duecare-270-gemma-generations":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    # 2. metadata title canonical.
    if meta.get("title") != "270: DueCare Gemma 2 vs 3 vs 4 Safety Gap":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    # 3. is_private is False.
    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    # 4. dataset sources cover wheels + trafficking-prompts.
    expected_datasets = {"taylorsamarel/duecare-llm-wheels", "taylorsamarel/duecare-trafficking-prompts"}
    if set(meta.get("dataset_sources") or []) & expected_datasets != expected_datasets:
        fail(f"dataset_sources missing expected datasets: {meta.get('dataset_sources')!r}")
    ok("dataset_sources covers wheels + trafficking-prompts")

    # 5. cell 0 opens with canonical H1 (no em dash).
    cell0 = src(md_cells[0])
    if not cell0.startswith("# 270: DueCare Gemma 2 vs 3 vs 4 Safety Gap"):
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

    # 7. required cross-link slugs present (100, 210, 220, 230, 240, 399).
    required_links = [
        "duecare-real-gemma-4-on-50-trafficking-prompts",
        "duecare-gemma-vs-oss-comparison",
        "duecare-ollama-cloud-oss-comparison",
        "duecare-230-mistral-family-comparison",
        "duecare-openrouter-frontier-comparison",
        "duecare-baseline-text-comparisons-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 100, 210, 220, 230, 240, 399 present")

    # 8. exactly one install cell (hardener-injected).
    install_cells = [c for c in code_cells if "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    # 9. no duplicate wheel-walk outside the install cell. 270 does keep
    # a single wheel install cell at step 1 in addition to the hardener
    # install cell; that is the intentional Kaggle-wheels-for-duecare
    # path. Assert there is at most one such extra block and it is inside
    # a cell that is NOT the pinned PACKAGES install cell.
    extra_wheel_blocks = 0
    for c in code_cells:
        s = src(c)
        if "PACKAGES = [" in s:
            continue
        if "duecare-llm-wheels" in s and "glob.glob" in s:
            extra_wheel_blocks += 1
    if extra_wheel_blocks > 1:
        fail(f"more than one wheel-walk block outside the install cell ({extra_wheel_blocks})")
    ok("at most one auxiliary wheel-walk block outside the install cell")

    # 10. BANDS tuple defined (270 uses the V3 6-band classifier).
    if "BANDS = [" not in all_code:
        fail("BANDS list for V3 6-band classifier is not defined")
    ok("BANDS list (V3 6-band classifier) is defined")

    # 11. PUBLISHED_BASELINE fallback dict defined.
    if "PUBLISHED_BASELINE = {" not in all_code:
        fail("PUBLISHED_BASELINE fallback dict is not defined")
    if "PUBLISHED_BASELINE_DATE" not in all_code or "PUBLISHED_BASELINE_SOURCE" not in all_code:
        fail("PUBLISHED_BASELINE_DATE or PUBLISHED_BASELINE_SOURCE citation is missing")
    ok("PUBLISHED_BASELINE fallback dict with source + date citation is defined")

    # 12. BANDS reused downstream (classify_v3 + headline chart + summary).
    if all_code.count("BANDS") < 3:
        fail("BANDS not reused across classification, summary, and chart")
    ok("BANDS reused across classifier, summary, and chart")

    # 13. classify_v3 function defined and referenced from summary/scoring cells.
    if "def classify_v3" not in all_code:
        fail("classify_v3 function is not defined")
    if "classify_v3(" not in all_code:
        fail("classify_v3 is defined but never called")
    ok("classify_v3 defined and called")

    # 14. "Privacy is non-negotiable" banned in comparison-notebook text.
    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 270; reserve for 610/899")
    ok("no 'Privacy is non-negotiable' phrase (reserved for 610/899)")

    # 15. no "| | |" markdown pseudo-table anywhere.
    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    # 16. HTML Troubleshooting table present with Symptom/Resolution columns.
    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    # 17. URL-bearing final print hands off to 399 and 100 verbatim.
    final_print_cells = [c for c in code_cells if "Gemma generations comparison complete" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Gemma generations comparison complete' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-baseline-text-comparisons-conclusion" not in final_print:
        fail("final print missing 399 slug")
    if "duecare-real-gemma-4-on-50-trafficking-prompts" not in final_print:
        fail("final print missing 100 slug")
    default_marker = "Review the stacked V3 band chart above and continue"
    for c in code_cells:
        if default_marker in src(c):
            fail("hardener default print was NOT patched")
    ok("final print is URL-bearing and links to 399 and 100; default print patched out")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
