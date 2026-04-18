"""Adversarial validation for the 320 Finding Gemma 4 Safety Line rebuild.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_320_supergemma_safety_gap.py``. 320 is the
safety-line slot inside the Adversarial Prompt-Test Evaluation section;
this validator enforces the same structural invariants as
``_validate_230_adversarial.py`` adapted to 320's T4 GPU workflow (no
SAFETY_DIMENSIONS-backed radar, but the 6-dimension weighted rubric
is still required).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_320_supergemma_safety_gap" / "320_supergemma_safety_gap.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_320_supergemma_safety_gap" / "kernel-metadata.json"


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

    # 1. metadata id is the canonical 320 live slug.
    if meta.get("id") != "taylorsamarel/duecare-finding-gemma-4-safety-line":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    # 2. metadata title canonical.
    if meta.get("title") != "320: DueCare Finding Gemma 4 Safety Line":
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

    # 5. enable_gpu is True (T4 required for GGUF inference).
    if meta.get("enable_gpu") is not True:
        fail(f"enable_gpu expected True (320 is GPU T4 kernel): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is True (T4 kernel)")

    # 6. cell 0 opens with canonical H1 (no em dash).
    cell0 = src(md_cells[0])
    if not cell0.startswith("# 320: DueCare Finding Gemma 4 Safety Line"):
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

    # 8. required cross-link slugs (100, 300, 410, 450, 530, 799, 000).
    required_links = [
        "duecare-real-gemma-4-on-50-trafficking-prompts",
        "duecare-300-adversarial-resistance",
        "duecare-410-llm-judge-grading",
        "duecare-contextual-judge",
        "duecare-530-phase3-unsloth-finetune",
        "duecare-adversarial-evaluation-conclusion",
        "duecare-000-index",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 100, 300, 410, 450, 530, 799, 000 present")

    # 9. exactly one install cell (hardener-injected).
    install_cells = [c for c in code_cells if "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    # 10. DIMENSION_WEIGHTS dict defined (320 reuses the 6-dim rubric).
    if "DIMENSION_WEIGHTS = {" not in all_code:
        fail("DIMENSION_WEIGHTS dict is not defined")
    ok("DIMENSION_WEIGHTS dict is defined")

    # 11. llama.cpp load path with GPU offload attempt.
    if "n_gpu_layers=-1" not in all_code:
        fail("llama.cpp n_gpu_layers=-1 (full GPU offload) path missing")
    if "from llama_cpp import Llama" not in all_code:
        fail("llama_cpp import missing; 320 requires llama-cpp-python")
    ok("llama.cpp GPU-offload load path present")

    # 12. MODEL_CANDIDATES with at least one SuperGemma + one Gemma-2 fallback.
    if "MODEL_CANDIDATES = [" not in all_code:
        fail("MODEL_CANDIDATES list is not defined")
    if "supergemma4-26b-uncensored-gguf-v2" not in all_code:
        fail("SuperGemma 4 26B uncensored candidate is missing")
    if "bartowski/gemma-2-9b-it-abliterated-GGUF" not in all_code:
        fail("Gemma 2 9B abliterated fallback candidate is missing")
    ok("MODEL_CANDIDATES includes SuperGemma + Gemma-2 fallback")

    # 13. ethics-redaction: response_preview_redacted present; full text only in JSONL export.
    if "response_preview_redacted" not in all_code:
        fail("ethics redaction marker 'response_preview_redacted' missing; 320 must not display uncensored outputs verbatim")
    if "phase3_worst_references.jsonl" not in all_code:
        fail("Phase 3 worst-references JSONL export path is missing")
    ok("redacted-preview + Phase 3 worst-references export present")

    # 14. "Privacy is non-negotiable" banned (reserved for 610/899).
    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 320; reserve for 610/899")
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

    # 17. URL-bearing final print hands off to 799 and 530 verbatim.
    final_print_cells = [c for c in code_cells if "Safety-line handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Safety-line handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-adversarial-evaluation-conclusion" not in final_print:
        fail("final print missing 799 slug")
    if "duecare-530-phase3-unsloth-finetune" not in final_print:
        fail("final print missing 530 slug")
    default_marker = "Safety-line analysis complete. Review the gap above"
    for c in code_cells:
        if default_marker in src(c):
            fail("hardener default print was NOT patched")
    ok("final print is URL-bearing and links to 799 and 530; default print patched out")

    # 18. trailing "What just happened" + "Key findings" blocks present.
    if "## What just happened" not in final_md:
        fail("trailing cell missing '## What just happened' block")
    if "### Key findings" not in final_md:
        fail("trailing cell missing '### Key findings' block")
    ok("trailing cell has 'What just happened' + 'Key findings' blocks")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
