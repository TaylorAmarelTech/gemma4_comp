"""Adversarial validation for the 170 Live Context Injection Playground.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_170_live_context_injection_playground.py``.
170 is the interactive context-injection playground between 160 and 199
in the Free Form Exploration section; the checks here verify the three
generation modes (plain / RAG / guided) are present, the RAG corpus is
defined, and the side-by-side HTML renders.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = (
    ROOT
    / "kaggle"
    / "kernels"
    / "duecare_170_live_context_injection_playground"
    / "170_live_context_injection_playground.ipynb"
)
META_PATH = (
    ROOT
    / "kaggle"
    / "kernels"
    / "duecare_170_live_context_injection_playground"
    / "kernel-metadata.json"
)


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

    if meta.get("id") != "taylorsamarel/170-duecare-live-context-injection-playground":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 170 slug")

    if meta.get("title") != "170: DueCare Live Context Injection Playground":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not True:
        fail(f"enable_gpu expected True (170 is T4 kernel): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is True (T4 kernel)")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 170: DueCare Live Context Injection Playground"):
        fail("cell 0 does not open with canonical H1 title")
    if "\u2014" in cell0.split("\n", 1)[0]:
        fail("cell 0 H1 still contains an em dash")
    ok("cell 0 has canonical H1 title (no em dash)")

    if "<table" not in cell0:
        fail("cell 0 is missing the HTML header table")
    for tag in (
        "<b>Inputs</b>",
        "<b>Outputs</b>",
        "<b>Prerequisites</b>",
        "<b>Runtime</b>",
        "<b>Pipeline position</b>",
    ):
        if tag not in cell0:
            fail(f"cell 0 HTML header missing {tag}")
    ok("cell 0 header has all five expected Field/Value rows")

    required_links = [
        "duecare-real-gemma-4-on-50-trafficking-prompts",
        "199-duecare-free-form-exploration-conclusion",
        "duecare-260-rag-comparison",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 100, 199, 260 present")

    install_cells = [
        c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)
    ]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    if "RAG_STORE = {" not in all_code:
        fail("RAG_STORE dict is not defined")
    ok("RAG_STORE dict is defined")

    if "SYSTEM_PREAMBLE = " not in all_code and "SYSTEM_PREAMBLE=" not in all_code:
        fail("SYSTEM_PREAMBLE string is not defined")
    ok("SYSTEM_PREAMBLE string is defined")

    for fn_marker in ("def generate_plain", "def generate_rag", "def generate_guided"):
        if fn_marker not in all_code:
            fail(f"missing generation function: {fn_marker}")
    ok("generate_plain, generate_rag, generate_guided all defined in-notebook")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 170; reserve for 610/899")
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

    final_print_cells = [c for c in code_cells if "Playground handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Playground handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "199-duecare-free-form-exploration-conclusion" not in final_print:
        fail("final print missing 199 slug")
    if "duecare-260-rag-comparison" not in final_print:
        fail("final print missing 260 slug")
    ok("final print is URL-bearing and links to 199 and 260")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
