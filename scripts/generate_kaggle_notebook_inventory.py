"""Generate the authoritative Kaggle notebook inventory markdown file."""

from __future__ import annotations

from pathlib import Path

from kaggle_notebook_utils import discover_kernel_notebooks, render_inventory_markdown


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "docs" / "current_kaggle_notebook_state.md"


def main() -> int:
    entries = discover_kernel_notebooks()
    OUTPUT_PATH.write_text(render_inventory_markdown(entries), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(entries)} tracked kernels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())