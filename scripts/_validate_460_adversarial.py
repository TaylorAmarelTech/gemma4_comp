"""Adversarial validation for the 460 Citation Verifier notebook.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_460_citation_verifier.py``. 460 is the
citation-audit slot between 410 LLM Judge Grading and the 499
Advanced Evaluation Conclusion; the checks here verify that the
real-citation corpus, the extraction patterns, the six sample
responses, and the REAL / HALLUCINATED / UNKNOWN classification are
all defined in-notebook so the kernel reproduces the writeup's
legal-accuracy evidence without external dependencies.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_460_citation_verifier" / "460_citation_verifier.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_460_citation_verifier" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/duecare-460-citation-verifier":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 460 slug")

    if meta.get("title") != "460: DueCare Citation Verifier":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu is not False (460 is CPU-only): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (CPU-only)")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 460: DueCare Citation Verifier"):
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
        "duecare-410-llm-judge-grading",
        "499-duecare-advanced-evaluation-conclusion",
        "duecare-530-phase3-unsloth-finetune",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 410, 499, 530 present")

    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    if "REAL_CITATIONS = {" not in all_code:
        fail("REAL_CITATIONS dict is not defined")
    ok("REAL_CITATIONS dict is defined")

    if "def extract_citations(" not in all_code:
        fail("extract_citations function is not defined")
    ok("extract_citations function is defined")

    if "def verify_citation(" not in all_code:
        fail("verify_citation function is not defined")
    ok("verify_citation function is defined")

    if "SAMPLE_RESPONSES = [" not in all_code:
        fail("SAMPLE_RESPONSES list is not defined")
    ok("SAMPLE_RESPONSES list is defined")

    jurisdiction_count = all_code.count("'jurisdiction'")
    if jurisdiction_count < 15:
        fail(f"REAL_CITATIONS should have at least 15 entries; counted {jurisdiction_count} 'jurisdiction' keys")
    ok(f"REAL_CITATIONS has at least 15 entries ({jurisdiction_count} 'jurisdiction' keys)")

    if "HALLUCINATED" not in all_code:
        fail("missing HALLUCINATED classification label in code")
    ok("HALLUCINATED classification label present")

    if "'REAL'" not in all_code and '"REAL"' not in all_code:
        fail("missing REAL classification label in code")
    ok("REAL classification label present")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 460; reserve for 610/899")
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

    final_print_cells = [c for c in code_cells if "Citation verifier handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Citation verifier handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "499-duecare-advanced-evaluation-conclusion" not in final_print:
        fail("final print missing 499 slug")
    if "duecare-530-phase3-unsloth-finetune" not in final_print:
        fail("final print missing 530 slug")
    ok("final print is URL-bearing and links to 499 and 530")

    marker_count = all_code.count("Citation verifier handoff >>>")
    if marker_count != 1:
        fail(f"marker 'Citation verifier handoff >>>' should appear exactly once in code cells; found {marker_count}")
    ok("marker 'Citation verifier handoff >>>' is unique")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
