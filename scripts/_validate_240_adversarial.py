"""Adversarial validation for the 240 OpenRouter Frontier Comparison rebuild.

Seventeen canonical checks that mirror ``_validate_220_adversarial.py``.
Fails loudly so the next push never ships a regressed structural
element (em-dash H1, pseudo-table intro, broken hex fill, missing
URL hand-off, etc.).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_240_openrouter_frontier_comparison" / "240_openrouter_frontier_comparison.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_240_openrouter_frontier_comparison" / "kernel-metadata.json"


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

    # 1. metadata id is the canonical 240 live slug.
    if meta.get("id") != "taylorsamarel/duecare-openrouter-frontier-comparison":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    # 2. metadata title canonical.
    if meta.get("title") != "240: DueCare Gemma 4 vs Frontier Cloud Models":
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
    if not cell0.startswith("# 240: DueCare Gemma 4 vs Frontier Cloud Models"):
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

    # 7. required cross-link slugs present (100, 210, 220, 230, 270, 399).
    required_links = [
        "duecare-real-gemma-4-on-50-trafficking-prompts",
        "duecare-gemma-vs-oss-comparison",
        "duecare-ollama-cloud-oss-comparison",
        "duecare-230-mistral-family-comparison",
        "duecare-270-gemma-generations",
        "duecare-baseline-text-comparisons-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 100, 210, 220, 230, 270, 399 present")

    # 8. exactly one install cell (hardener-injected).
    install_cells = [c for c in code_cells if "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    # 9. no legacy wheel-walk in non-install code cells.
    for i, c in enumerate(code_cells):
        s = src(c)
        if "PACKAGES = [" in s:
            continue
        if "duecare-llm-wheels" in s and "glob.glob" in s:
            fail(f"code cell {i} has legacy wheel-walk outside install cell")
    ok("no duplicate wheel-walk")

    # 10. SAFETY_DIMENSIONS derived from DIMENSION_WEIGHTS.
    if "SAFETY_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())" not in all_code:
        fail("SAFETY_DIMENSIONS constant not derived from DIMENSION_WEIGHTS")
    ok("SAFETY_DIMENSIONS derived from DIMENSION_WEIGHTS")

    # 11. DIMENSION_WEIGHTS dict defined.
    if "DIMENSION_WEIGHTS = {" not in all_code:
        fail("DIMENSION_WEIGHTS dict is not defined")
    ok("DIMENSION_WEIGHTS dict is defined")

    # 12. SAFETY_DIMENSIONS reused across plots (min 3 occurrences).
    if all_code.count("SAFETY_DIMENSIONS") < 3:
        fail("SAFETY_DIMENSIONS not reused across plots")
    ok("SAFETY_DIMENSIONS reused across plots")

    # 13. _hex_to_rgba helper present; no appended-hex-alpha drift.
    if "_hex_to_rgba" not in all_code:
        fail("missing _hex_to_rgba helper for plotly fill")
    if "color + '15'" in all_code or "+ '15'" in all_code:
        fail("stale appended-hex-alpha remains in plotly fill")
    ok("_hex_to_rgba helper present; no appended-hex-alpha drift")

    # 14. "Privacy is non-negotiable" banned in comparison-notebook text.
    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 240; reserve for 610/899")
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

    # 17. URL-bearing final print hands off to 270 and 399 verbatim.
    final_print_cells = [c for c in code_cells if "Frontier comparison complete" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Frontier comparison complete' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-270-gemma-generations" not in final_print:
        fail("final print missing 270 slug")
    if "duecare-baseline-text-comparisons-conclusion" not in final_print:
        fail("final print missing 399 slug")
    default_marker = "Review the frontier comparison above and re-run"
    for c in code_cells:
        if default_marker in src(c):
            fail("hardener default print was NOT patched")
    ok("final print is URL-bearing and links to 270 and 399; default print patched out")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
