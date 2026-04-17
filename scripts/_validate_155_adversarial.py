"""Adversarial validation for the 155 Tool Calling Playground."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = (
    ROOT
    / "kaggle"
    / "kernels"
    / "duecare_155_tool_calling_playground"
    / "155_tool_calling_playground.ipynb"
)
META_PATH = (
    ROOT
    / "kaggle"
    / "kernels"
    / "duecare_155_tool_calling_playground"
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

    def src(cell: dict) -> str:
        s = cell.get("source", [])
        return "".join(s) if isinstance(s, list) else str(s)

    all_md = "\n\n".join(src(c) for c in md_cells)
    all_code = "\n\n".join(src(c) for c in code_cells)
    all_text = all_md + "\n\n" + all_code

    if meta.get("id") != "taylorsamarel/155-duecare-tool-calling-playground":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 155 slug")

    if meta.get("title") != "155: DueCare Tool Calling Playground":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not True:
        fail(f"enable_gpu expected True: {meta.get('enable_gpu')!r}")
    ok("enable_gpu is True")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 155: DueCare Tool Calling Playground"):
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

    for slug in (
        "150-duecare-free-form-gemma-playground",
        "160-duecare-image-processing-playground",
        "duecare-400-function-calling-multimodal",
        "199-duecare-free-form-exploration-conclusion",
    ):
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 150, 160, 400, and 199 present")

    install_cells = [
        c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)
    ]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    for marker in (
        "MODEL_AVAILABLE = False",
        "TOOLS = [",
        "SCENARIO_PRESETS = {",
        "safety_refusal",
        "def _heuristic_tool_call",
        "def route_tool_call",
    ):
        if marker not in all_code:
            fail(f"missing notebook marker: {marker}")
    ok("tool catalog, refusal path, fallback router, and live router all defined in-notebook")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 155; reserve for deployment/story notebooks")
    ok("no reserved privacy tagline in 155")

    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still present")
    ok("no markdown pseudo-table remnants")

    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    final_print_cells = [c for c in code_cells if "Tool-calling handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Tool-calling handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    for slug in (
        "160-duecare-image-processing-playground",
        "duecare-400-function-calling-multimodal",
        "199-duecare-free-form-exploration-conclusion",
    ):
        if slug not in final_print:
            fail(f"final print missing slug {slug}")
    ok("final print is URL-bearing and links to 160, 400, and 199")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
