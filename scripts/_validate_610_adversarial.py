"""Adversarial validation for the 610 Submission Walkthrough notebook.

Canonical-shape checks on the notebook emitted by
``scripts/build_kaggle_notebooks.py --only 610``. 610 is the
judge-facing capstone that picks up after 600 Results Dashboard and
hands the reader to 620, 650, and 899.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_610_submission_walkthrough" / "610_submission_walkthrough.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_610_submission_walkthrough" / "kernel-metadata.json"


def fail(msg: str) -> None:
    print(f"FAIL  {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"OK    {msg}")


def main() -> None:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    cells = nb["cells"]
    md_cells = [cell for cell in cells if cell["cell_type"] == "markdown"]
    code_cells = [cell for cell in cells if cell["cell_type"] == "code"]

    def src(cell):
        source = cell.get("source", [])
        return "".join(source) if isinstance(source, list) else str(source)

    all_md = "\n\n".join(src(cell) for cell in md_cells)
    all_code = "\n\n".join(src(cell) for cell in code_cells)
    all_text = all_md + "\n\n" + all_code

    if meta.get("id") != "taylorsamarel/610-duecare-submission-walkthrough":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 610 slug")

    if meta.get("title") != "610: DueCare Submission Walkthrough":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu is not False: {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 610: DueCare Submission Walkthrough"):
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
        "010-duecare-quickstart-in-5-minutes",
        "duecare-200-cross-domain-proof",
        "duecare-500-agent-swarm-deep-dive",
        "duecare-530-phase3-unsloth-finetune",
        "600-duecare-results-dashboard",
        "620-duecare-demo-api-endpoint-tour",
        "650-duecare-custom-domain-walkthrough",
        "duecare-solution-surfaces-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 010, 200, 500, 530, 600, 620, 650, and 899 present")

    if "What ships" not in all_md or "Primary user" not in all_md:
        fail("missing reader-facing surface map table")
    ok("reader-facing surface map table present")

    install_cells = [cell for cell in code_cells if "pip install" in src(cell).lower() or "PACKAGES = [" in src(cell)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    if "modules = [" not in all_code or "duecare.publishing" not in all_code:
        fail("namespace verification cell is missing expected module list")
    ok("namespace verification cell present")

    if "ScriptedModel" not in all_code:
        fail("missing scripted cross-domain proof model")
    for domain_id in ("trafficking", "tax_evasion", "financial_crime"):
        if domain_id not in all_code:
            fail(f"cross-domain proof is missing {domain_id}")
    if "Validated shipped packs:" not in all_code:
        fail("cross-domain proof is missing the shipped-pack summary line")
    ok("cross-domain proof covers the three shipped packs")

    if "Privacy is non-negotiable" not in all_text:
        fail("missing required 'Privacy is non-negotiable' phrase")
    ok("required privacy phrase present")

    for org in ("Polaris Project", "IJM", "ECPAT", "POEA", "BP2MI", "HRD Nepal"):
        if org not in all_text:
            fail(f"missing named organization {org}")
    ok("named deployer organizations present")

    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    final_print_cells = [cell for cell in code_cells if "Submission walkthrough complete." in src(cell)]
    if not final_print_cells:
        fail("no URL-bearing 'Submission walkthrough complete.' final print")
    final_print = src(final_print_cells[-1])
    if "620-duecare-demo-api-endpoint-tour" not in final_print:
        fail("final print missing 620 slug")
    if "650-duecare-custom-domain-walkthrough" not in final_print:
        fail("final print missing 650 slug")
    if "duecare-solution-surfaces-conclusion" not in final_print:
        fail("final print missing 899 slug")
    ok("final print is URL-bearing and links to 620, 650, and 899")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()