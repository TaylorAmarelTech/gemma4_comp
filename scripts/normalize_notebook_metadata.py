"""Normalize serialized Jupyter notebook cell metadata in-place."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _normalize_cell(cell: dict[str, Any]) -> bool:
    changed = False
    metadata = cell.setdefault("metadata", {})
    expected_language = "markdown" if cell.get("cell_type") == "markdown" else "python"
    if metadata.get("language") != expected_language:
        metadata["language"] = expected_language
        changed = True

    if cell.get("cell_type") == "code":
        if "execution_count" not in cell:
            cell["execution_count"] = None
            changed = True
        if "outputs" not in cell:
            cell["outputs"] = []
            changed = True

    return changed


def _normalize_notebook(path: Path) -> bool:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    for cell in notebook.get("cells", []):
        changed = _normalize_cell(cell) or changed
    if changed:
        path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize notebook metadata.language fields in-place.")
    parser.add_argument("paths", nargs="+", help="Notebook paths to normalize.")
    args = parser.parse_args()

    changed = 0
    for raw_path in args.paths:
        path = Path(raw_path)
        if _normalize_notebook(path):
            changed += 1
            print(f"normalized {path}")
        else:
            print(f"ok {path}")

    print(f"done: changed={changed} checked={len(args.paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())