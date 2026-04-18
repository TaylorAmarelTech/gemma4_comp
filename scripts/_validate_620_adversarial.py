"""Adversarial validation for the 620 Demo API Endpoint Tour notebook.

Canonical-shape checks on the notebook emitted by
``scripts/build_notebook_620_demo_api_endpoint_tour.py``. 620 is the
solution-surfaces tour between 610 Submission Walkthrough and 650
Custom Domain Walkthrough; the checks here verify that every FastAPI
route called out in the task spec is described in the catalog and
that the eight required representative routes are exercised in-notebook.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "kaggle" / "kernels" / "duecare_620_demo_api_endpoint_tour" / "620_demo_api_endpoint_tour.ipynb"
META_PATH = ROOT / "kaggle" / "kernels" / "duecare_620_demo_api_endpoint_tour" / "kernel-metadata.json"


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

    if meta.get("id") != "taylorsamarel/620-duecare-demo-api-endpoint-tour":
        fail(f"metadata id wrong: {meta.get('id')!r}")
    ok("metadata id is canonical 620 slug")

    if meta.get("title") != "620: DueCare Demo API Endpoint Tour":
        fail(f"metadata title wrong: {meta.get('title')!r}")
    ok("metadata title is canonical")

    if meta.get("is_private") is not False:
        fail(f"is_private is not False: {meta.get('is_private')!r}")
    ok("is_private is False")

    if meta.get("enable_gpu") is not False:
        fail(f"enable_gpu is not False: {meta.get('enable_gpu')!r}")
    ok("enable_gpu is False")

    cell0 = src(md_cells[0])
    if not cell0.startswith("# 620: DueCare Demo API Endpoint Tour"):
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
        "610-duecare-submission-walkthrough",
        "650-duecare-custom-domain-walkthrough",
        "duecare-solution-surfaces-conclusion",
    ]
    for slug in required_links:
        if slug not in all_text:
            fail(f"missing cross-link slug {slug}")
    ok("cross-links to 610, 650, 899 present")

    install_cells = [c for c in code_cells if "pip install" in src(c).lower() or "PACKAGES = [" in src(c)]
    if len(install_cells) != 1:
        fail(f"expected exactly 1 install cell, found {len(install_cells)}")
    ok("exactly 1 install cell")

    if "ENDPOINTS = [" not in all_code and "ENDPOINTS = json.loads" not in all_code:
        fail("ENDPOINTS list is not defined")
    ok("ENDPOINTS list is defined")

    # Count "'path':" occurrences in the code; each endpoint dict in the
    # catalog carries a single path key, so at least 17 means the full
    # seventeen-endpoint surface is present. The catalog may be emitted as
    # a Python literal or via json.loads(...), so accept both styles.
    path_occurrences = all_code.count("'path':") + all_code.count('"path":')
    if path_occurrences < 17:
        fail(f"expected at least 17 ENDPOINTS entries (counted {path_occurrences} 'path': occurrences)")
    ok(f"ENDPOINTS list has at least 17 entries ({path_occurrences} 'path': occurrences)")

    representative_routes = [
        "/api/v1/analyze",
        "/api/v1/rag-context",
        "/api/v1/function-call",
        "/api/v1/analyze-document",
        "/api/v1/migration-case",
        "/api/v1/migration-case-upload",
        "/api/v1/evaluate",
        "/api/v1/quick-check",
    ]
    missing_representative_routes = [r for r in representative_routes if r not in all_code]
    if missing_representative_routes:
        fail(f"missing required representative endpoint paths in code: {missing_representative_routes}")
    ok("all 8 representative endpoint paths are exercised in code (/analyze, /rag-context, /function-call, /analyze-document, /migration-case, /migration-case-upload, /evaluate, /quick-check)")

    required_catalog_routes = [
        "/api/v1/case-examples",
        "/api/v1/case-examples/{example_id}",
        "/viewer",
        "/",
    ]
    missing_catalog_routes = [r for r in required_catalog_routes if r not in all_code]
    if missing_catalog_routes:
        fail(f"missing required catalog-only routes in code: {missing_catalog_routes}")
    ok("catalog includes case-example endpoints plus the viewer and root HTML surfaces")

    if "TestClient" not in all_code:
        fail("missing TestClient reference (required for in-process call path)")
    if "CLIENT_AVAILABLE" not in all_code:
        fail("missing CLIENT_AVAILABLE flag (required for TestClient fallback wiring)")
    if "Catalog-only routes:" not in all_code or "App-only routes:" not in all_code:
        fail("missing live catalog-vs-app drift audit printout")
    ok("TestClient + CLIENT_AVAILABLE wiring present, with live catalog-vs-app drift audit")

    if "Privacy is non-negotiable" in all_text:
        fail("'Privacy is non-negotiable' should not appear in 620; reserve for 610/899")
    ok("no 'Privacy is non-negotiable' phrase (reserved for 610/899)")

    if "| | |" in all_md:
        fail("pre-canonical '| | |' markdown pseudo-table is still in a markdown cell")
    ok("no '| | |' markdown pseudo-table")

    # Final markdown must contain the HTML Troubleshooting table.
    final_md = src(md_cells[-1])
    if "Troubleshooting" not in final_md or "<table" not in final_md:
        fail("final markdown missing HTML Troubleshooting table")
    if "Symptom" not in final_md or "Resolution" not in final_md:
        fail("troubleshooting table missing Symptom/Resolution columns")
    ok("HTML Troubleshooting table present")

    final_print_cells = [c for c in code_cells if "API tour handoff >>>" in src(c)]
    if not final_print_cells:
        fail("no URL-bearing 'API tour handoff >>>' final print")
    final_print = src(final_print_cells[-1])
    if "650-duecare-custom-domain-walkthrough" not in final_print:
        fail("final print missing 650 slug")
    if "duecare-solution-surfaces-conclusion" not in final_print:
        fail("final print missing 899 slug")
    ok("final print is URL-bearing and links to 650 and 899")

    # Sankey / call-graph sanity: at least one plotly Sankey reference
    # in the notebook body, plus at least two downstream agent labels.
    if "Sankey" not in all_code:
        fail("call-graph Sankey missing (expected go.Sankey)")
    if "Coordinator agent" not in all_code or "Judge agent" not in all_code:
        fail("call-graph must label downstream agents (Coordinator, Judge)")
    ok("Plotly Sankey call-graph with agent labels present")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
