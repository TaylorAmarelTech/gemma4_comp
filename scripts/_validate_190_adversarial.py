"""Adversarial validation for the 190 RAG Retrieval Inspector notebook.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_190_rag_retrieval_inspector.py``. 190 is the
pre-flight retrieval inspector between 140 Evaluation Mechanics and the
section conclusion 299 in the Baseline Text Evaluation Framework
section; the checks here verify that the corpus, retriever, coverage
heatmap, and per-prompt breakdown are all present in-notebook.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_190_rag_retrieval_inspector" / "190_rag_retrieval_inspector.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_190_rag_retrieval_inspector" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/duecare-190-rag-retrieval-inspector":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 190 slug")

    if meta.get("title") != "190: DueCare RAG Retrieval Inspector":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu is not False: {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (CPU-only)")

    if meta.get("enable_tpu") is not False:
        fail(f"enable_tpu is not False: {meta.get('enable_tpu')!r}")
    ok("enable_tpu is False")

    expected_datasets = {"taylorsamarel/duecare-llm-wheels", "taylorsamarel/duecare-trafficking-prompts"}
    if set(meta.get("dataset_sources") or []) & expected_datasets != expected_datasets:
        fail(f"dataset_sources missing expected datasets: {meta.get('dataset_sources')!r}")
    ok("dataset_sources covers wheels + trafficking-prompts")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 190: DueCare RAG Retrieval Inspector"):
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
        "140-duecare-evaluation-mechanics",
        "duecare-260-rag-comparison",
        "duecare-baseline-text-evaluation-framework-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 140, 260, 299 present")

    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    if "LEGAL_CORPUS = [" not in all_code:
        fail("LEGAL_CORPUS list is not defined in code")
    ok("LEGAL_CORPUS list is defined")

    if "def retrieve(" not in all_code:
        fail("retrieve() function is not defined")
    ok("retrieve() function is defined")

    # Require at least 10 citations in LEGAL_CORPUS; count 'jurisdiction' entries.
    jurisdiction_count = all_code.count("'jurisdiction'")
    if jurisdiction_count < 10:
        fail(f"LEGAL_CORPUS has too few citations: only {jurisdiction_count} 'jurisdiction' entries found")
    ok(f"LEGAL_CORPUS has at least 10 citations ({jurisdiction_count} 'jurisdiction' entries)")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 190; reserve for 610/899")
    ok("no 'Privacy is non-negotiable' phrase (reserved for 610/899)")

    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table with Symptom/Resolution present")

    final_print_cells = [c for c in code_cells if "Retrieval inspection handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Retrieval inspection handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-260-rag-comparison" not in final_print:
        fail("final print missing 260 slug")
    if "duecare-baseline-text-evaluation-framework-conclusion" not in final_print:
        fail("final print missing 299 slug")
    ok("final print is URL-bearing and links to 260 and 299")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
