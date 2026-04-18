"""Adversarial validation for the 520 Phase 3 Curriculum Builder rebuild.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_520_phase3_curriculum_builder.py``. 520 is
the curriculum slot inside the Model Improvement Opportunities
section; this validator enforces the same structural invariants as
``_validate_230_adversarial.py`` adapted to 520's CPU-only
curriculum-generation workflow (no SAFETY_DIMENSIONS radar; the
contract is the Unsloth-ready JSONL schema).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_520_phase3_curriculum_builder" / "520_phase3_curriculum_builder.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_520_phase3_curriculum_builder" / "kernel-metadata.json"


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

    # 1. metadata id is the canonical 520 live slug.
    if meta.get("id") != "taylorsamarel/duecare-520-phase3-curriculum-builder":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id targets the live Kaggle kernel slug")

    # 2. metadata title canonical.
    if meta.get("title") != "520: DueCare Phase 3 Curriculum Builder":
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

    # 5. enable_gpu is False (all generation via cloud API).
    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu expected False (520 is CPU kernel): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (CPU kernel)")

    # 6. cell 0 opens with canonical H1 (no em dash).
    cell0 = src(md_cells[0])
    if not cell0.startswith("# 520: DueCare Phase 3 Curriculum Builder"):
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

    # 8. required cross-link slugs (100, 410, 450, 510, 530, 540, 599, 000).
    required_links = [
        "duecare-real-gemma-4-on-50-trafficking-prompts",
        "duecare-410-llm-judge-grading",
        "duecare-contextual-judge",
        "duecare-phase2-comparison",
        "duecare-530-phase3-unsloth-finetune",
        "540-duecare-fine-tune-delta-visualizer",
        "599-duecare-model-improvement-opportunities-conclusion",
        "duecare-000-index",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 100, 410, 450, 510, 530, 540, 599, 000 present")

    # 9. exactly one install cell (hardener-injected).
    install_cells = [c for c in code_cells if "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    # 10. BANDS_TO_CORRECT set includes the four V3 failure bands.
    if "BANDS_TO_CORRECT = {" not in all_code:
        fail("BANDS_TO_CORRECT set is not defined")
    for band in ("HARD_VIOLATION", "DETECTION_FAIL", "SOFT_REFUSAL", "POSSIBLE_VIOLATION_VICTIM_PROMPT"):
        if band not in all_code:
            fail(f"BANDS_TO_CORRECT missing failure band: {band}")
    ok("BANDS_TO_CORRECT covers all four V3 failure bands")

    # 11. CORRECTION_PROMPT + BAND_EXPLAIN defined.
    if "CORRECTION_PROMPT" not in all_code:
        fail("CORRECTION_PROMPT template is not defined")
    if "BAND_EXPLAIN = {" not in all_code:
        fail("BAND_EXPLAIN dict is not defined")
    ok("CORRECTION_PROMPT + BAND_EXPLAIN defined")

    # 12. OpenRouter + Mistral dual-generator path + template fallback.
    if "openrouter.ai/api/v1/chat/completions" not in all_code:
        fail("OpenRouter generator URL is missing")
    if "api.mistral.ai/v1/chat/completions" not in all_code:
        fail("Mistral generator URL is missing")
    if "def fallback_correction" not in all_code:
        fail("template-based fallback_correction function is missing")
    ok("OpenRouter + Mistral + template fallback generators defined")

    # 13. Unsloth chat-format JSONL export with GEMMA_CHAT_TEMPLATE.
    if "GEMMA_CHAT_TEMPLATE" not in all_code:
        fail("GEMMA_CHAT_TEMPLATE formatter is missing; Unsloth-ready JSONL cannot be emitted")
    if "phase3_curriculum.jsonl" not in all_code:
        fail("phase3_curriculum.jsonl output path is missing")
    ok("Unsloth-format GEMMA_CHAT_TEMPLATE + phase3_curriculum.jsonl output present")

    # 14. summary JSON persisted.
    if "phase3_curriculum_summary.json" not in all_code:
        fail("phase3_curriculum_summary.json persistence is missing")
    ok("phase3_curriculum_summary.json persisted")

    # 15. "Privacy is non-negotiable" banned (reserved for 610/899).
    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 520; reserve for 610/899")
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

    # 18. URL-bearing final print hands off to 530 and 599 verbatim.
    final_print_cells = [c for c in code_cells if "Curriculum handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Curriculum handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-530-phase3-unsloth-finetune" not in final_print:
        fail("final print missing 530 slug")
    if "599-duecare-model-improvement-opportunities-conclusion" not in final_print:
        fail("final print missing 599 slug")
    default_marker = "Curriculum build complete. Review phase3_curriculum.jsonl"
    for c in code_cells:
        if default_marker in src(c):
            fail("hardener default print was NOT patched")
    ok("final print is URL-bearing and links to 530 and 599; default print patched out")

    # 19. trailing "What just happened" + "Key findings" blocks present.
    if "## What just happened" not in final_md:
        fail("trailing cell missing '## What just happened' block")
    if "### Key findings" not in final_md:
        fail("trailing cell missing '### Key findings' block")
    ok("trailing cell has 'What just happened' + 'Key findings' blocks")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
