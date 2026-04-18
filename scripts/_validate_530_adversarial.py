"""Adversarial validation for the 530 Phase 3 Unsloth Fine-Tune notebook.

Structural checks for the notebook emitted by
``scripts/build_notebook_530_phase3_unsloth_finetune.py``. 530 is the
GPU-only bridge between curriculum generation in 520 and the charted
before/after story in 540 and 600, so the validator focuses on
canonical metadata, honest data-source handling, and a correct final
handoff.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_530_phase3_unsloth_finetune" / "530_phase3_unsloth_finetune.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_530_phase3_unsloth_finetune" / "kernel-metadata.json"


def fail(message: str) -> None:
    print(f"FAIL  {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"OK    {message}")


def _src(cell: dict) -> str:
    source = cell.get("source", [])
    return "".join(source) if isinstance(source, list) else str(source)


def main() -> None:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    cells = nb["cells"]
    md_cells = [cell for cell in cells if cell["cell_type"] == "markdown"]
    code_cells = [cell for cell in cells if cell["cell_type"] == "code"]
    all_md = "\n\n".join(_src(cell) for cell in md_cells)
    all_code = "\n\n".join(_src(cell) for cell in code_cells)
    all_text = all_md + "\n\n" + all_code

    if meta.get("id") != "taylorsamarel/duecare-530-phase3-unsloth-finetune":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 530 slug")

    if meta.get("title") != "530: DueCare Phase 3 Unsloth Fine-Tune":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not True:
        fail(f"enable_gpu is not True: {meta.get('enable_gpu')!r}")
    ok("enable_gpu is True")

    cell0 = _src(md_cells[0])
    if not cell0.startswith("# 530: DueCare Phase 3 Unsloth Fine-Tune"):
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

    for slug in (
        "duecare-520-phase3-curriculum-builder",
        "duecare-540-finetune-delta-visualizer",
        "599-duecare-model-improvement-opportunities-conclusion",
        "600-duecare-results-dashboard",
    ):
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 520, 540, 599, and 600 present")

    first_code = _src(code_cells[0])
    if "duecare-llm-core==0.1.0" not in first_code:
        fail("first code cell does not pin duecare-llm-core==0.1.0")
    ok("first code cell pins the DueCare package version")

    gpu_guard_cells = [cell for cell in code_cells if "This notebook requires a T4 GPU. Enable it in Kaggle settings." in _src(cell)]
    if len(gpu_guard_cells) != 1:
        fail(f"expected exactly one GPU guard cell, found {len(gpu_guard_cells)}")
    ok("exactly one GPU guard cell")

    if "phase3_curriculum.jsonl" not in all_code:
        fail("phase3_curriculum.jsonl path is not referenced in code")
    if "seed_prompts.jsonl" not in all_code:
        fail("seed_prompts.jsonl fallback is not referenced in code")
    ok("real curriculum input plus seed-prompt fallback are both wired")

    if "phase3_artifact_manifest.json" not in all_code:
        fail("artifact manifest output is missing")
    if "stock_vs_finetuned.json" not in all_text:
        fail("downstream stock_vs_finetuned.json handoff is missing")
    ok("artifact manifest and downstream comparison-json handoff are present")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 530")
    ok("no reserved privacy phrase")

    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still present")
    ok("no markdown pseudo-table")

    final_md = _src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    final_print_cells = [cell for cell in code_cells if "Phase 3 handoff >>>" in _src(cell)]
    if not final_print_cells:
        fail("no URL-bearing 'Phase 3 handoff >>>' final print")
    final_print = _src(final_print_cells[-1])
    for slug in (
        "duecare-540-finetune-delta-visualizer",
        "599-duecare-model-improvement-opportunities-conclusion",
        "600-duecare-results-dashboard",
    ):
        if slug not in final_print:
            fail(f"final print missing {slug}")
    ok("final print is URL-bearing and links to 540, 599, and 600")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()