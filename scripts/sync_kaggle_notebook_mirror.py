"""Sync `notebooks/` from the authoritative Kaggle kernel sources."""

from __future__ import annotations

import shutil
from pathlib import Path

from kaggle_notebook_utils import NOTEBOOKS_DIR, discover_kernel_notebooks


def main() -> int:
    NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    updated = 0

    for entry in discover_kernel_notebooks():
        source_path = entry.dir_path / entry.code_file
        target_path = NOTEBOOKS_DIR / entry.code_file

        if not target_path.exists():
            shutil.copy2(source_path, target_path)
            copied += 1
            print(f"created {target_path.name}")
            continue

        if source_path.read_bytes() != target_path.read_bytes():
            shutil.copy2(source_path, target_path)
            updated += 1
            print(f"updated {target_path.name}")

    print(f"mirror sync complete: created={copied} updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())