"""Topological sort for the agent DAG.

Pure utility - no I/O, no LLM calls.
"""

from __future__ import annotations


def topological_sort(nodes: list[tuple[str, list[str]]]) -> list[str]:
    """Return an execution order for a DAG given (node_id, deps) pairs.

    Raises ValueError on cycles or unknown dependencies.
    """
    remaining = {node: set(deps) for node, deps in nodes}
    all_ids = set(remaining.keys())

    for node, deps in remaining.items():
        unknown = deps - all_ids
        if unknown:
            raise ValueError(f"Node {node!r} depends on unknown node(s): {sorted(unknown)}")

    ordered: list[str] = []
    while remaining:
        ready = [node for node, deps in remaining.items() if not deps]
        if not ready:
            cycle = list(remaining.keys())
            raise ValueError(f"Cycle detected in DAG involving: {cycle}")
        ready.sort()  # deterministic order
        for node in ready:
            ordered.append(node)
            del remaining[node]
            for deps in remaining.values():
                deps.discard(node)
    return ordered
