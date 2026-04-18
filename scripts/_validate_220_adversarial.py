"""Adversarial validation for the 220 Ollama Cloud rebuild."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_220_ollama_cloud_comparison" / "220_ollama_cloud_comparison.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_220_ollama_cloud_comparison" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/duecare-ollama-cloud-oss-comparison":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id matches live slug")

    if meta.get("title") != "220: DueCare Gemma 4 vs 7 OSS Models via Ollama Cloud":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    expected_datasets = {"taylorsamarel/duecare-llm-wheels", "taylorsamarel/duecare-trafficking-prompts"}
    if set(meta.get("dataset_sources") or []) & expected_datasets != expected_datasets:
        fail(f"dataset_sources missing expected datasets: {meta.get('dataset_sources')!r}")
    ok("dataset_sources covers wheels + trafficking-prompts")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 220: DueCare Gemma 4 vs 7 OSS Models via Ollama Cloud"):
        fail("cell 0 does not open with canonical H1 title")
    ok("cell 0 has canonical H1 title")

    if "<table" not in cell0:
        fail("cell 0 is missing the HTML header table")
    for tag in ("<b>Inputs</b>", "<b>Outputs</b>", "<b>Prerequisites</b>", "<b>Runtime</b>", "<b>Pipeline position</b>"):
        if tag not in cell0:
            fail(f"cell 0 HTML header missing {tag}")
    ok("cell 0 header has all five expected rows")

    required_links = [
        "duecare-real-gemma-4-on-50-trafficking-prompts",
        "duecare-gemma-vs-oss-comparison",
        "duecare-230-mistral-family-comparison",
        "duecare-baseline-text-comparisons-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 100, 210, 230, 399 present")

    install_cells = [c for c in code_cells if "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    for i, c in enumerate(code_cells):
        s = src(c)
        if "PACKAGES = [" in s:
            continue
        if "duecare-llm-wheels" in s and "glob.glob" in s:
            fail(f"code cell {i} has legacy wheel-walk outside install cell")
    ok("no duplicate wheel-walk")

    if "SAFETY_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())" not in all_code:
        fail("SAFETY_DIMENSIONS constant not derived from DIMENSION_WEIGHTS")
    ok("SAFETY_DIMENSIONS derived from DIMENSION_WEIGHTS")

    if all_code.count("SAFETY_DIMENSIONS") < 3:
        fail("SAFETY_DIMENSIONS not reused across plots")
    ok("SAFETY_DIMENSIONS reused across plots")

    if "_hex_to_rgba" not in all_code:
        fail("missing _hex_to_rgba helper for plotly fill")
    ok("_hex_to_rgba helper present")

    if "color + '15'" in all_code or "+ '15'" in all_code:
        fail("stale appended-hex-alpha remains in plotly fill")
    ok("no appended-hex-alpha drift")

    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    final_print_cells = [c for c in code_cells if "Ollama Cloud OSS comparison complete" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'Ollama Cloud OSS comparison complete' final print")
    final_print = src(final_print_cells[-1])
    if "duecare-230-mistral-family-comparison" not in final_print:
        fail("final print missing 230 slug")
    if "duecare-baseline-text-comparisons-conclusion" not in final_print:
        fail("final print missing 399 slug")
    ok("final print is URL-bearing and links to 230 and 399")

    default_marker = "Review the Ollama Cloud comparison above and re-run"
    for c in code_cells:
        if default_marker in src(c):
            fail("hardener default print was NOT patched")
    ok("hardener default print was patched out")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
