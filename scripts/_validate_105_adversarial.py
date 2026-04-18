"""Adversarial validation for the 105 Prompt Corpus Introduction notebook.

105 is the pre-110 entry point for the Baseline Text Evaluation
Framework section. Its job is to make the trafficking prompt corpus
legible BEFORE any selection, remixing, or scoring happens. This
validator enforces the canonical structural shape and the data-source
discipline (pack preferred, dataset fallback, built-in fallback) that
keep 105 useful on a standalone Kaggle kernel.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_105_prompt_corpus_introduction" / "105_prompt_corpus_introduction.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_105_prompt_corpus_introduction" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/105-duecare-prompt-corpus-introduction":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the canonical 105 slug")

    if meta.get("title") != "105: DueCare Prompt Corpus Introduction":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu expected False: {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (CPU-only)")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 105: DueCare Prompt Corpus Introduction"):
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
        "099-duecare-orientation-and-background-and-package-setup-conclusion",
        "00a-duecare-prompt-prioritizer-data-pipeline",  # 110 live slug
        "duecare-prompt-remixer",
        "140-duecare-evaluation-mechanics",
        "190-duecare-rag-retrieval-inspector",
        "duecare-baseline-text-evaluation-framework-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 099, 110, 120, 140, 190, 299 present")

    # Data-source discipline: three-path loader.
    if "load_domain_pack('trafficking')" not in all_code and "load_domain_pack(\"trafficking\")" not in all_code:
        fail("missing trafficking domain-pack load attempt")
    if "built-in fallback" not in all_text and "SAMPLE_PROMPTS" not in all_code:
        fail("missing built-in fallback path")
    ok("three-path data-source loader (domain pack / dataset / built-in) present")

    if "CORPUS_SOURCE" not in all_code:
        fail("missing CORPUS_SOURCE banner variable")
    ok("CORPUS_SOURCE banner variable present")

    # Reading-handoff table must name each downstream notebook.
    if "SECTION_HANDOFF" not in all_code and "Next" not in all_text:
        fail("missing reading-order handoff table/section")
    ok("reading-order handoff visible to reader")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 105; reserve for 610/899")
    ok("no 'Privacy is non-negotiable' phrase")

    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table still present")
    ok("no '| | |' markdown pseudo-table")

    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    final_print_cells = [c for c in code_cells if "Corpus introduction handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Corpus introduction handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    for required in (
        "00a-duecare-prompt-prioritizer-data-pipeline",  # URL_110
        "140-duecare-evaluation-mechanics",              # URL_140
    ):
        if required not in final_print:
            fail(f"final print missing slug {required}")
    ok("final print is URL-bearing and links to 110 and 140")

    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
