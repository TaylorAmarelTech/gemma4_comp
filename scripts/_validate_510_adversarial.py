"""Adversarial validation for the 510 Phase 2 Model Comparison rebuild.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_510_phase2_model_comparison.py``. 510 is the
Phase 2 slot inside the Model Improvement Opportunities section; this
validator enforces the same structural invariants as
``_validate_230_adversarial.py`` adapted to 510's T4 GPU workflow (the
rubric here is a deterministic keyword scorer rather than the shared
6-dimension weighted rubric).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_510_phase2_model_comparison" / "510_phase2_model_comparison.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_510_phase2_model_comparison" / "kernel-metadata.json"


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

    # 1. metadata id is the canonical 510 live slug.
    if meta.get("id") != "taylorsamarel/duecare-phase2-comparison":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    # 2. metadata title canonical.
    if meta.get("title") != "510: DueCare Phase 2 Model Comparison":
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

    # 5. enable_gpu is True (T4 required for Gemma 4 E2B/E4B transformers).
    if meta.get("enable_gpu") is not True:
        fail(f"enable_gpu expected True (510 is GPU T4 kernel): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is True (T4 kernel)")

    # 6. model_sources references both Gemma 4 E-series checkpoints.
    model_sources = meta.get("model_sources") or []
    if not any("gemma-4-e2b-it" in src for src in model_sources):
        fail("model_sources missing gemma-4-e2b-it")
    if not any("gemma-4-e4b-it" in src for src in model_sources):
        fail("model_sources missing gemma-4-e4b-it")
    ok("model_sources covers Gemma 4 E2B + E4B")

    # 7. cell 0 opens with canonical H1 (no em dash).
    cell0 = src(md_cells[0])
    if not cell0.startswith("# 510: DueCare Phase 2 Model Comparison"):
        fail("cell 0 does not open with canonical H1 title")
    if "\u2014" in cell0.split("\n", 1)[0]:
        fail("cell 0 H1 still contains an em dash")
    ok("cell 0 has canonical H1 title (no em dash)")

    # 8. HTML header table with all five rows.
    if "<table" not in cell0:
        fail("cell 0 is missing the HTML header table")
    for tag in ("<b>Inputs</b>", "<b>Outputs</b>", "<b>Prerequisites</b>", "<b>Runtime</b>", "<b>Pipeline position</b>"):
        if tag not in cell0:
            fail(f"cell 0 HTML header missing {tag}")
    ok("cell 0 header has all five expected Field/Value rows")

    # 9. required cross-link slugs (100, 270, 500, 520, 530, 540, 599, 000).
    required_links = [
        "duecare-real-gemma-4-on-50-trafficking-prompts",
        "duecare-270-gemma-generations",
        "duecare-500-agent-swarm-deep-dive",
        "duecare-520-phase3-curriculum-builder",
        "duecare-530-phase3-unsloth-finetune",
        "540-duecare-fine-tune-delta-visualizer",
        "599-duecare-model-improvement-opportunities-conclusion",
        "duecare-000-index",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 100, 270, 500, 520, 530, 540, 599, 000 present")

    # 10. exactly one install cell (hardener-injected).
    install_cells = [c for c in code_cells if "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    # 11. score_response function defined (the Phase 2 deterministic rubric).
    if "def score_response" not in all_code:
        fail("score_response function is not defined")
    ok("score_response deterministic rubric defined")

    # 12. MODEL_PATHS dict defined with both Gemma 4 E-series entries.
    if "MODEL_PATHS = {" not in all_code:
        fail("MODEL_PATHS dict is not defined")
    if "gemma-4-e2b-it" not in all_code or "gemma-4-e4b-it" not in all_code:
        fail("MODEL_PATHS is missing one of the Gemma 4 E-series checkpoints")
    ok("MODEL_PATHS covers Gemma 4 E2B + E4B")

    # 13. BitsAndBytesConfig 4-bit path present for T4 inference.
    if "BitsAndBytesConfig" not in all_code:
        fail("BitsAndBytesConfig import/use missing; 510 requires 4-bit quant on T4")
    if "load_in_4bit=True" not in all_code:
        fail("4-bit quantization config not active")
    ok("4-bit BitsAndBytesConfig path present")

    # 14. phase2_comparison.json persisted for 520 + 540 consumers.
    if "phase2_comparison.json" not in all_code:
        fail("phase2_comparison.json persistence line is missing")
    ok("phase2_comparison.json persisted for downstream notebooks")

    # 15. "Privacy is non-negotiable" banned (reserved for 610/899).
    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 510; reserve for 610/899")
    ok("no 'Privacy is non-negotiable' phrase (reserved for 610/899)")

    # 16. no "| | |" markdown pseudo-table anywhere.
    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    # 17. HTML Troubleshooting table present with Symptom/Resolution columns.
    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    # 18. URL-bearing final print hands off to 520 and 599 verbatim.
    final_print_cells = [c for c in code_cells if "Phase 2 comparison handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Phase 2 comparison handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-520-phase3-curriculum-builder" not in final_print:
        fail("final print missing 520 slug")
    if "599-duecare-model-improvement-opportunities-conclusion" not in final_print:
        fail("final print missing 599 slug")
    default_marker = "Phase 2 comparison complete. Review the side-by-side results"
    for c in code_cells:
        if default_marker in src(c):
            fail("hardener default print was NOT patched")
    ok("final print is URL-bearing and links to 520 and 599; default print patched out")

    # 19. trailing "What just happened" + "Key findings" blocks present.
    if "## What just happened" not in final_md:
        fail("trailing cell missing '## What just happened' block")
    if "### Key findings" not in final_md:
        fail("trailing cell missing '### Key findings' block")
    ok("trailing cell has 'What just happened' + 'Key findings' blocks")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
