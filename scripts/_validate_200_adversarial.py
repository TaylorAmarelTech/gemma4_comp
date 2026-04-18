"""Adversarial validation for the 200 Cross-Domain Proof rebuild.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_200_cross_domain_proof.py``. 200 opens the
Baseline Text Comparisons section; this validator enforces the same
structural invariants ``_validate_230_adversarial.py`` does, adapted
to 200's CPU-only scripted-model workflow (no DIMENSION_WEIGHTS or
plotly radar are required).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_200_cross_domain_proof" / "200_cross_domain_proof.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_200_cross_domain_proof" / "kernel-metadata.json"


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

    # 1. metadata id is the canonical 200 live slug.
    if meta.get("id") != "taylorsamarel/200-duecare-cross-domain-proof":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    # 2. metadata title canonical.
    if meta.get("title") != "200: DueCare Cross-Domain Proof":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    # 3. is_private is False.
    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    # 4. dataset sources include wheels + trafficking-prompts.
    expected_datasets = {"taylorsamarel/duecare-llm-wheels", "taylorsamarel/duecare-trafficking-prompts"}
    if set(meta.get("dataset_sources") or []) & expected_datasets != expected_datasets:
        fail(f"dataset_sources missing expected datasets: {meta.get('dataset_sources')!r}")
    ok("dataset_sources covers wheels + trafficking-prompts")

    # 5. enable_gpu is False (CPU section opener).
    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu expected False (200 is CPU kernel): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (CPU kernel)")

    # 6. cell 0 opens with canonical H1 (no em dash).
    cell0 = src(md_cells[0])
    if not cell0.startswith("# 200: DueCare Cross-Domain Proof"):
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

    # 8. required cross-link slugs (199, 210, 270, 399, 500 + 000).
    required_links = [
        "199-duecare-free-form-exploration-conclusion",
        "duecare-gemma-vs-oss-comparison",
        "duecare-270-gemma-generations",
        "duecare-baseline-text-comparisons-conclusion",
        "duecare-500-agent-swarm-deep-dive",
        "duecare-000-index",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 199, 210, 270, 399, 500, 000 present")

    # 9. exactly one install cell (hardener-injected).
    install_cells = [c for c in code_cells if "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    # 10. no duplicate wheel-walk outside install cell.
    for i, c in enumerate(code_cells):
        s = src(c)
        if "PACKAGES = [" in s:
            continue
        if "duecare-llm-wheels" in s and "glob.glob" in s:
            fail(f"code cell {i} has legacy wheel-walk outside install cell")
    ok("no duplicate wheel-walk")

    # 11. cross-domain invariant: all three packs referenced in code.
    for domain in ("'trafficking'", "'tax_evasion'", "'financial_crime'"):
        if domain not in all_code:
            fail(f"missing cross-domain reference in code: {domain}")
    ok("all three domain packs (trafficking, tax_evasion, financial_crime) referenced in code")

    # 12. rapid_probe workflow defined and runner invoked three times.
    if "rapid_probe" not in all_code:
        fail("rapid_probe workflow not defined in code")
    if "WorkflowRunner" not in all_code or "runner.run" not in all_code:
        fail("WorkflowRunner is missing or never invoked")
    ok("rapid_probe workflow defined and WorkflowRunner invoked")

    # 13. run_id uniqueness assertion present.
    if "run_ids = {r.run_id for r in workflow_runs.values()}" not in all_code:
        fail("run_id uniqueness set-building line is missing")
    if "assert len(run_ids) == len(workflow_runs)" not in all_code:
        fail("assert for distinct run_ids is missing")
    ok("distinct run_ids invariant asserted")

    # 14. "Privacy is non-negotiable" banned (reserved for 610/899).
    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 200; reserve for 610/899")
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

    # 17. URL-bearing final print hands off to 210 and 399 verbatim.
    final_print_cells = [c for c in code_cells if "Cross-domain proof handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Cross-domain proof handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-gemma-vs-oss-comparison" not in final_print:
        fail("final print missing 210 slug")
    if "duecare-baseline-text-comparisons-conclusion" not in final_print:
        fail("final print missing 399 slug")
    default_marker = "Cross-domain proof complete. Review the workflow runs above"
    for c in code_cells:
        if default_marker in src(c):
            fail("hardener default print was NOT patched")
    ok("final print is URL-bearing and links to 210 and 399; default print patched out")

    # 18. trailing "What just happened" + "Key findings" blocks present.
    if "## What just happened" not in final_md:
        fail("trailing cell missing '## What just happened' block")
    if "### Key findings" not in final_md:
        fail("trailing cell missing '### Key findings' block")
    ok("trailing cell has 'What just happened' + 'Key findings' blocks")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
