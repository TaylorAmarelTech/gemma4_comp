"""End-to-end smoke test for /api/rag/graph.

Spins up the FastAPI app via TestClient (no real network), hits the
endpoint, asserts the schema matches what the JS viewer expects:
  * meta.n_nodes == 54
  * meta.n_edges == 46
  * every edge.from / edge.to is a valid node id
  * every node has {id, label, source, snippet, group}
  * groups[<id>] has {label, color}

This catches the kind of regression where the JS viewer would silently
render an empty canvas because the response shape drifted.

Run:
    py -3.10 scripts/v141_smoke_rag_graph_endpoint.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "packages" / "duecare-llm-chat" / "src"))
sys.path.insert(0, str(REPO / "packages" / "duecare-llm-core" / "src"))
sys.path.insert(0, str(REPO / "packages" / "duecare-llm-models" / "src"))


def main() -> int:
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print("fastapi.testclient not available — skipping end-to-end smoke.")
        print("Install with: py -3.10 -m pip install fastapi httpx")
        return 0

    from duecare.chat.app import create_app

    # Stub model call — endpoint under test is /api/rag/graph which doesn't
    # call the model.
    def stub_call(messages, **kwargs):  # noqa: ANN001
        return "stub"

    app = create_app(gemma_call=stub_call)
    client = TestClient(app)
    r = client.get("/api/rag/graph")
    if r.status_code != 200:
        print(f"FAIL: GET /api/rag/graph returned {r.status_code}")
        print(r.text)
        return 2

    data = r.json()

    issues: list[str] = []

    meta = data.get("meta") or {}
    if meta.get("n_nodes") != 54:
        issues.append(f"meta.n_nodes = {meta.get('n_nodes')} (expected 54)")
    if meta.get("n_edges") != 46:
        issues.append(f"meta.n_edges = {meta.get('n_edges')} (expected 46)")

    nodes = data.get("nodes") or []
    if len(nodes) != 54:
        issues.append(f"nodes count = {len(nodes)} (expected 54)")

    node_ids = {n["id"] for n in nodes if "id" in n}

    expected_node_keys = {"id", "label", "source", "snippet", "group"}
    for n in nodes:
        missing = expected_node_keys - set(n.keys())
        if missing:
            issues.append(f"node {n.get('id', '?')} missing keys: {missing}")

    edges = data.get("edges") or []
    if len(edges) != 46:
        issues.append(f"edges count = {len(edges)} (expected 46)")

    bad_edges = 0
    for e in edges:
        if e.get("from") not in node_ids:
            bad_edges += 1
            print(f"  edge.from='{e.get('from')}' not in nodes")
        if e.get("to") not in node_ids:
            bad_edges += 1
            print(f"  edge.to='{e.get('to')}' not in nodes")
    if bad_edges:
        issues.append(f"{bad_edges} edge endpoints reference unknown nodes")

    groups = data.get("groups") or {}
    used_groups = {n.get("group") for n in nodes}
    for gid in used_groups:
        if gid not in groups:
            issues.append(f"node uses group '{gid}' but groups dict has no entry")
        else:
            g = groups[gid]
            if not g.get("label") or not g.get("color"):
                issues.append(f"groups['{gid}'] missing label or color")

    if issues:
        print("\nFAIL — schema issues:")
        for i in issues:
            print(f"  - {i}")
        return 2

    # All good — print a summary.
    by_group: dict[str, int] = {}
    for n in nodes:
        by_group[n["group"]] = by_group.get(n["group"], 0) + 1

    print("OK — /api/rag/graph response is well-formed.")
    print(f"  nodes: {len(nodes)}")
    print(f"  edges: {len(edges)}")
    print(f"  groups (with counts):")
    for gid, count in sorted(by_group.items(), key=lambda kv: -kv[1]):
        g = groups.get(gid, {})
        print(f"    {gid:18s} {count:3d}  {g.get('label', '?')}")
    print(f"  meta:  {meta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
