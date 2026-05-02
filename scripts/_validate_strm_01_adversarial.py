"""Adversarial validation for the DueCareLLM Streamlined 01 notebook.

Enforces the structural invariants the downstream Streamlined pipeline
depends on. Runs against the emitted notebook file, not a live
execution; the dynamic record count is verified separately by actually
executing the notebook cells.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "strm_01_prompt_test_generation" / "strm_01_prompt_test_generation.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "strm_01_prompt_test_generation" / "kernel-metadata.json"


def fail(message: str) -> None:
    print(f"FAIL  {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"OK    {message}")


def _src(cell: dict) -> str:
    src = cell.get("source", [])
    return "".join(src) if isinstance(src, list) else str(src)


def main() -> None:
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    cells = nb["cells"]
    md_cells = [c for c in cells if c["cell_type"] == "markdown"]
    code_cells = [c for c in cells if c["cell_type"] == "code"]
    all_md = "\n\n".join(_src(c) for c in md_cells)
    all_code = "\n\n".join(_src(c) for c in code_cells)
    all_text = all_md + "\n\n" + all_code

    if meta.get("id") != "taylorsamarel/duecarellm-streamlined-01-prompt-test-generation":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical")

    if meta.get("title") != "Streamlined 01: Prompt and Test Generation":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu is not False (Streamlined 01 is processor-only): {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False (processor-only)")

    expected_datasets = {"taylorsamarel/duecare-llm-wheels", "taylorsamarel/duecare-trafficking-prompts"}
    if set(meta.get("dataset_sources") or []) != expected_datasets:
        fail(f"dataset_sources wrong: {meta.get('dataset_sources')!r}")
    ok("dataset_sources matches expected pair")

    # The hero banner is cell zero; the canonical header lives in cell one (markdown).
    header_cell = _src(md_cells[0])
    if not header_cell.startswith("# Streamlined 01: Prompt and Test Generation"):
        fail("first markdown cell does not open with the canonical H1 title")
    ok("first markdown cell has the canonical H1 title")

    if "<b>Inputs</b>" not in header_cell or "<b>Outputs</b>" not in header_cell:
        fail("header table missing Inputs/Outputs rows")
    for tag in ("<b>Prerequisites</b>", "<b>Runtime</b>", "<b>Pipeline position</b>"):
        if tag not in header_cell:
            fail(f"header table missing row {tag}")
    ok("header table has all five canonical rows")

    # Exactly one install cell from the hardener.
    install_cells = [c for c in code_cells if "PACKAGES = [" in _src(c) or "pip install" in _src(c).lower()]
    if len(install_cells) != 1:
        fail(f"expected exactly one install cell, found {len(install_cells)}")
    ok("exactly one install cell")

    # Load-corpus code references the canonical dataset path.
    if "duecare-trafficking-prompts/seed_prompts.jsonl" not in all_code:
        fail("code does not reference the canonical corpus dataset path")
    ok("code references canonical corpus dataset path")

    # Seed-selection logic must preference full-ladder prompts.
    if "_has_full_ladder" not in all_code:
        fail("seed selection does not preference full five-grade-ladder prompts")
    ok("seed selection preferences full five-grade-ladder prompts")

    # Four named transform families must exist.
    for marker in ("transform_corridor_swap", "transform_persona_swap", "transform_framing_swap", "transform_severity_escalation"):
        if marker not in all_code:
            fail(f"missing transform function: {marker}")
    ok("all four amplification transforms defined")

    # Test-rubric generator must exist with the six canonical criteria.
    if "def generate_tests" not in all_code:
        fail("generate_tests function is missing")
    for criterion in ("explicit_refusal", "legal_citation", "safety_redirect", "trafficking_indicator", "no_harmful_enablement", "actionability"):
        if criterion not in all_code:
            fail(f"test criterion {criterion} is missing from generate_tests")
    ok("generate_tests defines the six canonical criteria")

    # Reference-responses step must write both best and worst keys.
    if "reference_responses" not in all_code or "WORST_TEMPLATES" not in all_code or "BEST_TEMPLATES" not in all_code:
        fail("reference-responses synthesis is incomplete")
    ok("reference-responses synthesis defines best and worst templates")

    # Output path is the canonical Kaggle working path.
    if "streamlined_prompts_with_tests.jsonl" not in all_code:
        fail("output path is not streamlined_prompts_with_tests.jsonl")
    if "/kaggle/working/" not in all_code:
        fail("output file is not written to /kaggle/working/")
    ok("output file is /kaggle/working/streamlined_prompts_with_tests.jsonl")

    # Target record count must be five hundred or higher.
    if "TARGET_RECORD_COUNT = 500" not in all_code and "TARGET_RECORD_COUNT = 1000" not in all_code:
        fail("TARGET_RECORD_COUNT is not set to the five-hundred-prompt floor")
    ok("TARGET_RECORD_COUNT is at least five hundred")

    # Hero banner present in first code cell.
    hero_cell = _src(code_cells[0])
    if "DueCareLLM Streamlined - Pipeline" not in hero_cell:
        fail("hero banner kicker is not the canonical Streamlined label")
    ok("hero banner uses the canonical Streamlined kicker")

    # Privacy invariant: the reserved phrase may appear in prose but not as a PII claim.
    if "Privacy is non-negotiable" in all_text:
        fail("reserved tagline 'Privacy is non-negotiable' should not appear in Streamlined 01")
    ok("no reserved 'Privacy is non-negotiable' tagline")

    # URL-bearing final print handoff.
    final_print_cells = [c for c in code_cells if "Streamlined 01 handoff >>>" in _src(c)]
    if not final_print_cells:
        fail("final print cell with 'Streamlined 01 handoff >>>' marker is missing")
    final_print = _src(final_print_cells[-1])
    if "streamlined_prompts_with_tests.jsonl" not in final_print:
        fail("final print does not name the output artifact file")
    ok("final print references the output artifact and uses the canonical marker")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
