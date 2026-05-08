"""Smoke test for /api/harness-catalog/{layer} endpoints.

Spins up the FastAPI app, calls every layer (persona / grep / rag /
tools / online), asserts the schema each static viewer expects.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "packages" / "duecare-llm-chat" / "src"))


def main() -> int:
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print("fastapi.testclient unavailable.")
        return 0

    from duecare.chat.app import create_app

    def stub(messages, **kw):  # noqa: ANN001
        return "stub"

    app = create_app(gemma_call=stub)
    client = TestClient(app)

    failures: list[str] = []

    expectations = {
        "grep":    {"min_n": 100, "first_keys": {"rule", "severity", "citation", "indicator"}},
        "rag":     {"min_n":  40, "first_keys": {"id", "title", "source", "snippet"}},
        "tools":   {"min_n":   1},
        "online":  {"min_n":   0},
        "persona": {"min_n":   0},
    }

    for layer, expect in expectations.items():
        r = client.get(f"/api/harness-catalog/{layer}")
        if r.status_code != 200:
            failures.append(f"{layer}: HTTP {r.status_code}")
            continue
        d = r.json()
        items = d.get("items") or []
        n = d.get("n_items", len(items))
        print(f"  {layer:10s} -> {n:3d} items, wired={d.get('wired')}")
        if expect.get("min_n") and n < expect["min_n"]:
            failures.append(f"{layer}: {n} < min_n={expect['min_n']}")
        first_keys = expect.get("first_keys")
        if first_keys and items:
            missing = first_keys - set(items[0].keys())
            if missing:
                failures.append(f"{layer}: first item missing keys {missing}")
        if layer == "tools":
            tables = d.get("tables") or {}
            for tname in ("corridor_fee_caps", "fee_camouflage_labels",
                           "ilo_indicators", "ngo_intake_groups",
                           "ilo_conventions"):
                if tname not in tables:
                    failures.append(f"tools: missing backing table '{tname}'")
                else:
                    sz = len(tables[tname]) if hasattr(tables[tname], "__len__") else "?"
                    print(f"    table.{tname:25s} = {sz} rows")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 2
    print("\nAll catalog endpoints pass smoke.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
