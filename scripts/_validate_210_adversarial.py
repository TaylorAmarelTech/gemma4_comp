"""Adversarial validation for the 210 rebuild.

Checks every concrete claim from the 13-item fix list. Fails loudly if any
check regresses so the next push does not ship a subtle content drop.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_210_oss_model_comparison" / "210_oss_model_comparison.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_210_oss_model_comparison" / "kernel-metadata.json"
EXPECTED_TITLES = {
    "DueCare Gemma vs OSS Comparison",
    "210: DueCare Gemma 4 vs OSS Models",
}


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

    def src(cell: dict) -> str:
        s = cell.get("source", [])
        return "".join(s) if isinstance(s, list) else str(s)

    all_md = "\n\n".join(src(c) for c in md_cells)
    all_code = "\n\n".join(src(c) for c in code_cells)
    all_text = all_md + "\n\n" + all_code

    # --- metadata checks -----------------------------------------------------
    # Live Kaggle kernel lives at the pre-renumber slug; we target the existing
    # slug so push updates the live kernel in place. Canonical "210:" is in the title.
    if meta.get("id") != "taylorsamarel/duecare-gemma-vs-oss-comparison":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    if meta.get("title") not in EXPECTED_TITLES:
        fail(f"metadata title wrong: {meta.get('title')!r} (expected one of {sorted(EXPECTED_TITLES)})")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    # --- header check --------------------------------------------------------
    cell0 = src(md_cells[0])
    if not cell0.startswith("# 210: DueCare Gemma 4 vs OSS Models"):
        fail("cell 0 does not open with canonical H1 title")
    ok("cell 0 has canonical H1 title")

    if "<table" not in cell0:
        fail("cell 0 is missing the HTML header table")
    ok("cell 0 has HTML header table")

    for tag in ("<b>Inputs</b>", "<b>Outputs</b>", "<b>Prerequisites</b>", "<b>Runtime</b>", "<b>Pipeline position</b>"):
        if tag not in cell0:
            fail(f"cell 0 HTML header table missing row: {tag}")
    ok("cell 0 HTML header table has Inputs/Outputs/Prerequisites/Runtime/Pipeline position rows")

    # --- cross-links ---------------------------------------------------------
    required_urls = {
        "100": "duecare-real-gemma-4-on-50-trafficking-prompts",
        "140": "140-duecare-evaluation-mechanics",
        "200": "duecare-cross-domain-proof",
        "220": "duecare-ollama-cloud-oss-comparison",
        "270": "duecare-270-gemma-generations",
        "299": "299-duecare-text-evaluation-conclusion",
        "399": "duecare-baseline-text-comparisons-conclusion",
    }
    for nb_id, slug in required_urls.items():
        if slug not in all_text:
            fail(f"missing cross-link to {nb_id} (slug {slug!r})")
    ok("all required cross-links present (100, 140, 200, 220, 270, 299, 399)")

    if "rubric from" not in all_text.lower() and "rubric defined in 100" not in all_text.lower() and "6-dimension rubric from" not in all_text.lower():
        fail("cell 0 does not reference the rubric from 100")
    ok("cell 0 references the rubric from 100")

    # --- single install cell -------------------------------------------------
    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell (hardener-injected, no duplicate wheel-walk)")

    # No legacy wheel-walk in the content cells.
    for i, c in enumerate(code_cells):
        s = src(c)
        if "PACKAGES = [" in s:
            continue
        if "duecare-llm-wheels" in s and "glob.glob" in s:
            fail(f"code cell {i} contains a legacy wheel-walk outside the install cell")
    ok("no duplicate wheel-walk in non-install code cells")

    # --- phase 1 baseline loading -------------------------------------------
    if "gemma_baseline_findings.json" not in all_code:
        fail("no reference to gemma_baseline_findings.json in code cells")
    ok("code loads gemma_baseline_findings.json")

    if "PUBLISHED_BASELINE" not in all_code:
        fail("no PUBLISHED_BASELINE fallback defined")
    ok("PUBLISHED_BASELINE fallback is defined")

    if "PUBLISHED_BASELINE_DATE" not in all_code:
        fail("PUBLISHED_BASELINE_DATE is missing")
    ok("PUBLISHED_BASELINE_DATE is set (citation)")

    # --- "load the Phase 1 baseline" heading in Cell 1 md -------------------
    if not any("Load the Phase 1 baseline" in src(cell) for cell in md_cells):
        fail("first step markdown does not say 'Load the Phase 1 baseline'")
    ok("step 1 heading says 'Load the Phase 1 baseline'")

    # --- SAFETY_DIMENSIONS constant and reuse --------------------------------
    if "SAFETY_DIMENSIONS = [" not in all_code:
        fail("SAFETY_DIMENSIONS constant is not defined")
    ok("SAFETY_DIMENSIONS constant is defined")

    reuses = all_code.count("SAFETY_DIMENSIONS")
    if reuses < 3:
        fail(f"SAFETY_DIMENSIONS is not reused enough across plots (count={reuses})")
    ok(f"SAFETY_DIMENSIONS is reused across plots (count={reuses})")

    # --- baseline source/date citation in MODELS dict -----------------------
    if "OSS_BASELINE_SOURCE" not in all_code or "OSS_BASELINE_DATE" not in all_code:
        fail("OSS peer scoreline missing source/date citation")
    ok("OSS peer scoreline has source/date citation")

    if "'measured_on'" not in all_code:
        fail("MODELS entries do not record measured_on")
    ok("MODELS entries record measured_on")

    # --- overall-is-not-None assertion --------------------------------------
    if "overall') is not None" not in all_code:
        fail("missing assertion `overall') is not None` before plotting")
    ok("assertion on overall-is-not-None is present before plotting")

    # --- HTML gap table ------------------------------------------------------
    # Check the gap analysis cell renders HTML rather than plain text.
    gap_candidates = [c for c in code_cells if "delta" in src(c).lower() and ("gap" in src(c).lower() or "competitors" in src(c).lower())]
    if not gap_candidates:
        fail("no gap analysis code cell found")
    gap_src = src(gap_candidates[-1])
    if "<table" not in gap_src or "display(HTML" not in gap_src:
        fail("gap analysis cell does not render an HTML table via display(HTML(...))")
    ok("gap analysis cell renders an HTML table")

    # --- troubleshooting table in final markdown ----------------------------
    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md:
        fail("final markdown has no Troubleshooting section")
    ok("final markdown has a Troubleshooting section")

    if final_md.count("<table") < 1 or "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting section is not an HTML Symptom/Resolution table")
    ok("troubleshooting section is an HTML Symptom/Resolution table")

    # --- explicit make_subplots import --------------------------------------
    if "from plotly.subplots import make_subplots" not in all_code:
        fail("explicit make_subplots import is missing")
    ok("explicit make_subplots import is present")

    # --- URL-bearing final print --------------------------------------------
    final_print_cells = [c for c in code_cells if "Gemma 4 vs OSS complete" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing final print with 'Gemma 4 vs OSS complete' handoff")
    final_print_src = src(final_print_cells[-1])
    if "220" not in final_print_src or "duecare-ollama-cloud-oss-comparison" not in final_print_src:
        fail("final print does not link to 220")
    if "399" not in final_print_src or "baseline-text-comparisons-conclusion" not in final_print_src:
        fail("final print does not link to 399")
    ok("final print is URL-bearing and links to 220 and 399")

    # --- default hardener print is no longer present ------------------------
    default_hardener = "Review the charts above for Gemma versus peer open-source mode"
    for c in code_cells:
        if default_hardener in src(c):
            fail("hardener default print was NOT patched")
    ok("hardener default print was patched out")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
