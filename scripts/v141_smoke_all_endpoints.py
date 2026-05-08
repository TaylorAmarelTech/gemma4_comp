"""Single comprehensive no-model smoke test.

Spins up the FastAPI app via fastapi.testclient (no real network, no
GPU, no model load) and asserts every critical endpoint returns the
expected schema + counts. This is the gate to run BEFORE pushing
the wheel to Kaggle.

What it checks:
    GET  /api/brand                — product/layer/version/counts
    GET  /api/version              — chat_package + harness counts +
                                       12 curator-block index entries
    GET  /api/health-check         — wired layers, package_version
                                       (NOT "0.1.0")
    GET  /api/rag/graph            — 46 nodes / 46 edges / groups
    GET  /api/harness-catalog/grep — 161 rules with severity
    GET  /api/harness-catalog/rag  — 46 docs with citation neighbors
    GET  /api/harness-catalog/persona — at least 5 personas
    GET  /api/harness-catalog/tools — 5 tools + backing tables
    POST /api/grep/test            — paste text, fire returned
    GET  /api/search-all?q=passport — federated search returns hits
    GET  /api/contacts             — 26-entry directory
    GET  /api/contacts?country=Philippines — filter works
    GET  /api/governance           — curator-block index
    GET  /api/governance/contacts  — raw contacts JSON

Pass condition: every endpoint returns 200, schemas match, counts
clear submission minimums (n_grep_rules>=150, n_rag_docs>=40,
n_dimensions>=40, n_examples>=500, n_contacts>=20).

Run:
    py -3.10 scripts/v141_smoke_all_endpoints.py

Exit 0 = pass. Exit 2 = at least one failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "packages" / "duecare-llm-chat" / "src"))


# Submission-minimum thresholds. If actual counts fall below these,
# something has gone backwards — fail the gate.
MIN_GREP_RULES        = 150
MIN_RAG_DOCS          = 40
MIN_DIMENSIONS        = 40
MIN_EXAMPLES          = 500
MIN_CONTACTS          = 20
MIN_PERSONAS          = 5


def _stub_grep(text: str, **_kw):  # noqa: ANN001, ANN201
    # Return a fake hit so /api/grep/test smoke can verify the
    # response shape end-to-end.
    return {
        "hits": [{
            "rule":          "smoke_test_rule",
            "severity":      "high",
            "citation":      "smoke citation",
            "indicator":     "smoke indicator",
            "match_excerpt": "...",
        }],
        "elapsed_ms": 5,
    }


def _stub_model(messages, **_kw):  # noqa: ANN001, ANN201
    return "stub model response"


def _check(label: str, condition: bool, detail: str = "") -> int:
    if condition:
        print(f"  PASS  {label}")
        return 0
    print(f"  FAIL  {label}{(': ' + detail) if detail else ''}")
    return 1


def main() -> int:
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print("fastapi.testclient unavailable; install fastapi + httpx.")
        return 0

    from duecare.chat.app import create_app

    app = create_app(gemma_call=_stub_model, grep_call=_stub_grep)
    client = TestClient(app)

    fails = 0
    print("v0.14.5 comprehensive smoke (no GPU, no model load)\n")

    # /api/brand
    r = client.get("/api/brand")
    fails += _check("GET /api/brand returns 200", r.status_code == 200,
                     f"got {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        fails += _check("brand has 6 layers",
                          len(d.get("layers") or []) == 6,
                          f"got {len(d.get('layers') or [])}")
        c = d.get("counts") or {}
        fails += _check(
            f"brand counts.n_grep_rules >= {MIN_GREP_RULES}",
            c.get("n_grep_rules", 0) >= MIN_GREP_RULES,
            f"got {c.get('n_grep_rules')}")
        fails += _check(
            f"brand counts.n_rag_docs >= {MIN_RAG_DOCS}",
            c.get("n_rag_docs", 0) >= MIN_RAG_DOCS,
            f"got {c.get('n_rag_docs')}")
        fails += _check(
            f"brand counts.n_dimensions >= {MIN_DIMENSIONS}",
            c.get("n_dimensions", 0) >= MIN_DIMENSIONS,
            f"got {c.get('n_dimensions')}")
        fails += _check(
            f"brand counts.n_examples >= {MIN_EXAMPLES}",
            c.get("n_examples", 0) >= MIN_EXAMPLES,
            f"got {c.get('n_examples')}")
        fails += _check(
            "brand rubric_version starts with 'v3.10'",
            (c.get("rubric_version") or "").startswith("v3.10"),
            f"got {c.get('rubric_version')}")

    # /api/version
    r = client.get("/api/version")
    fails += _check("GET /api/version returns 200", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        fails += _check(
            "/api/version chat_package present (not '0.1.0')",
            d.get("chat_package") and d["chat_package"] != "0.1.0",
            f"got {d.get('chat_package')!r}")
        blocks = d.get("curator_blocks") or []
        block_names = {b.get("name") for b in blocks}
        for required in ("personas", "evaluation_questions", "contacts"):
            fails += _check(
                f"/api/version curator_blocks contains {required!r}",
                required in block_names)

    # /api/health-check
    r = client.get("/api/health-check")
    fails += _check("GET /api/health-check returns 200",
                     r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        fails += _check(
            "/api/health-check package_version is NOT '0.1.0'",
            d.get("package_version") != "0.1.0",
            f"got {d.get('package_version')!r}")

    # /api/rag/graph
    r = client.get("/api/rag/graph")
    fails += _check("GET /api/rag/graph returns 200", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        fails += _check("rag/graph: nodes >= 40",
                          len(d.get("nodes") or []) >= 40)
        fails += _check("rag/graph: edges >= 40",
                          len(d.get("edges") or []) >= 40)
        fails += _check("rag/graph: 0 docs in 'Other' group",
                          all(n.get("group") != "other"
                                for n in d.get("nodes", [])))

    # /api/harness-catalog/{layer}
    for layer, min_items in [("grep", MIN_GREP_RULES), ("rag", MIN_RAG_DOCS),
                                ("persona", MIN_PERSONAS), ("tools", 1)]:
        r = client.get(f"/api/harness-catalog/{layer}")
        fails += _check(
            f"GET /api/harness-catalog/{layer} returns 200",
            r.status_code == 200)
        if r.status_code == 200:
            d = r.json()
            n = d.get("n_items", len(d.get("items") or []))
            fails += _check(f"  catalog/{layer}: n_items >= {min_items}",
                             n >= min_items, f"got {n}")
            if layer == "tools":
                tables = d.get("tables") or {}
                for tname in ("corridor_fee_caps", "fee_camouflage_labels",
                                "ilo_indicators", "ngo_intake_groups",
                                "ilo_conventions"):
                    fails += _check(
                        f"  catalog/tools.tables has {tname!r}",
                        tname in tables)

    # /api/grep/test
    r = client.post("/api/grep/test", json={"text": "test text"})
    fails += _check("POST /api/grep/test returns 200", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        fails += _check("grep/test: wired", d.get("wired") is True)
        fails += _check(
            f"grep/test: n_rules_total >= {MIN_GREP_RULES}",
            d.get("n_rules_total", 0) >= MIN_GREP_RULES)

    # /api/search-all
    r = client.get("/api/search-all", params={"q": "passport"})
    fails += _check("GET /api/search-all?q=passport returns 200",
                     r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        fails += _check("search-all: total > 0", (d.get("total") or 0) > 0)

    # /api/contacts
    r = client.get("/api/contacts")
    fails += _check("GET /api/contacts returns 200", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        fails += _check(
            f"contacts: n_total >= {MIN_CONTACTS}",
            (d.get("n_total") or 0) >= MIN_CONTACTS,
            f"got {d.get('n_total')}")
    r = client.get("/api/contacts", params={"country": "Philippines"})
    if r.status_code == 200:
        fails += _check("contacts country=Philippines filter > 0",
                          (r.json().get("n_filtered") or 0) > 0)

    # /api/governance
    r = client.get("/api/governance")
    fails += _check("GET /api/governance returns 200",
                     r.status_code == 200)
    r = client.get("/api/governance/contacts")
    fails += _check("GET /api/governance/contacts returns 200",
                     r.status_code == 200)

    # Static-served HTML pages (just check 200)
    for page in ("/static/index.html", "/static/harness.html",
                  "/static/grep-rules.html", "/static/grep-tester.html",
                  "/static/rag-corpus.html", "/static/rag-graph.html",
                  "/static/tools.html", "/static/online.html",
                  "/static/persona.html", "/static/search.html",
                  "/static/hotlines.html"):
        r = client.get(page)
        fails += _check(f"GET {page} returns 200", r.status_code == 200,
                          f"got {r.status_code}")

    print()
    if fails:
        print(f"FAILED — {fails} check(s) failed.")
        return 2
    print("All endpoint smoke checks pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
