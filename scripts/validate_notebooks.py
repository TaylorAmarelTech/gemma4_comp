"""Validate tracked notebook JSON without executing notebooks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from kaggle_notebook_utils import discover_kernel_notebooks


REQUIRED_VERSION = "0.1.0"


def _source_text(cell: dict) -> str:
    source = cell.get("source", [])
    if isinstance(source, list):
        return "".join(source)
    return str(source)


def _validate_entry(entry, *, cpu_only: bool) -> list[str]:
    errors: list[str] = []
    meta_path = entry.dir_path / "kernel-metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if cpu_only and meta.get("enable_gpu"):
        return errors

    kernel_nb_path = entry.dir_path / entry.code_file
    notebook = json.loads(kernel_nb_path.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    if not cells:
        return ["Notebook has no cells"]

    if not any(cell.get("cell_type") == "markdown" for cell in cells):
        errors.append("Notebook is missing a markdown cell")
    if not any(cell.get("cell_type") == "code" for cell in cells):
        errors.append("Notebook is missing a code cell")

    for index, cell in enumerate(cells, start=1):
        language = cell.get("metadata", {}).get("language")
        if language is None:
            errors.append(f"Cell {index} missing metadata.language")

    first_code = next((cell for cell in cells if cell.get("cell_type") == "code"), None)
    if first_code is None:
        errors.append("Notebook has no code cell")
    else:
        first_code_text = _source_text(first_code)
        if REQUIRED_VERSION not in first_code_text:
            errors.append(f"First code cell does not pin DueCare {REQUIRED_VERSION}")

    last_cell = cells[-1]
    last_cell_text = _source_text(last_cell)
    if last_cell.get("cell_type") != "code" or "print(" not in last_cell_text:
        errors.append("Notebook is missing the final summary code cell")

    if entry.mirror_path is None:
        errors.append("Notebook mirror is missing")
    elif kernel_nb_path.read_bytes() != entry.mirror_path.read_bytes():
        errors.append("Kernel notebook and local mirror differ")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tracked notebook JSON without execution.")
    parser.add_argument("--cpu-only", action="store_true", help="Validate only notebooks with enable_gpu=false.")
    args = parser.parse_args()

    failed = 0
    validated = 0
    for entry in discover_kernel_notebooks():
        entry_errors = _validate_entry(entry, cpu_only=args.cpu_only)
        if args.cpu_only:
            meta = json.loads((entry.dir_path / "kernel-metadata.json").read_text(encoding="utf-8"))
            if meta.get("enable_gpu"):
                continue
        validated += 1
        if entry_errors:
            failed += 1
            print(f"FAIL {entry.dir_name}")
            for error in entry_errors:
                print(f"  - {error}")
        else:
            print(f"OK   {entry.dir_name}")

    if failed:
        print(f"\nValidation failed for {failed} of {validated} notebooks.")
        return 1

    print(f"\nValidated {validated} notebooks successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())