"""Adversarial validation for the 600 Results Dashboard builder.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_600_results_dashboard.py``. The 600 notebook
is a Plotly dashboard over the baseline comparison JSON; structural
checks only, since the middle cells are plotting code rather than
rubric logic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_600_results_dashboard" / "600_results_dashboard.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_600_results_dashboard" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/600-duecare-results-dashboard":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the canonical live 600 slug")

    if meta.get("title") != "600: DueCare Results Dashboard":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 600: DueCare Results Dashboard"):
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
        "duecare-260-rag-comparison",
        "duecare-410-llm-judge-grading",
        "duecare-530-phase3-unsloth-finetune",
        "610-duecare-submission-walkthrough",
        "duecare-solution-surfaces-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 260, 410, 530, 610, 899 present")

    if "prompt_pack_context" not in all_code:
        fail("missing prompt_pack_context handling in dashboard code")
    if "full five-grade ladders" not in all_text:
        fail("missing full five-grade ladder corpus context")
    if "exported evaluation slice" not in all_text:
        fail("missing explicit slice-versus-corpus distinction")
    ok("dashboard distinguishes full prompt pack from the exported evaluation slice")

    if "Coverage funnel" not in all_text or "Category share across populations" not in all_text:
        fail("missing corpus coverage panel")
    if "Proof snapshot" not in all_text or "Best current mean score" not in all_text:
        fail("missing headline proof snapshot panel")
    if "One prompt with all five reference responses" not in all_text:
        fail("missing five-grade reference ladder section")
    if "one evaluation path, not the only one" not in all_text:
        fail("missing explicit framing that anchor-ladder comparison is only one evaluation path")
    if "Largest prompt-level movement" not in all_text or "Regression watchlist" not in all_text:
        fail("missing prompt-level movement watchlist")
    if "Curriculum priority proxy" not in all_text:
        fail("missing real category curriculum-priority diagnostics")
    if "illustrative placeholders" in all_text or "Failure Mode Distribution" in all_text:
        fail("stale placeholder failure panel remains in notebook 600")
    ok("proof snapshot, coverage, five-grade ladder, prompt movement, and category-priority panels are present; placeholder failure panel is gone")

    if "_hex_to_rgba" not in all_code:
        fail("missing _hex_to_rgba helper for plotly radar fill")
    if "+ '15'" in all_code or "color + '15'" in all_code:
        fail("stale appended-hex-alpha remains in plotly fill")
    ok("_hex_to_rgba helper present; no appended-hex-alpha drift")

    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    final_print_cells = [c for c in code_cells if "Dashboard review complete" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Dashboard review complete' final print")
    final_print = src(final_print_cells[-1])
    if "610-duecare-submission-walkthrough" not in final_print:
        fail("final print missing 610 slug")
    if "duecare-solution-surfaces-conclusion" not in final_print:
        fail("final print missing 899 slug")
    ok("final print is URL-bearing and links to 610 and 899")

    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
