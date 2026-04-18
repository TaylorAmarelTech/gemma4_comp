"""Force every kernel-metadata.json `id` to the canonical pattern.

Canonical: `NNN-duecare-<title-derive>` — the slug Kaggle naturally
creates from the `NNN: DueCare <Descriptive>` title convention. Every
notebook in the DueCare suite uses this title format, so a single
title-derive rule produces a uniform slug nomenclature.

What this does:
1. Reads each `kaggle/kernels/*/kernel-metadata.json`.
2. Extracts the NNN from the directory name (e.g., `duecare_140_*` -> 140).
3. Computes the canonical slug from the title by:
   - Lowercasing
   - Replacing non-alphanumeric characters with hyphens
   - Collapsing multiple hyphens
   - Trimming leading/trailing hyphens
4. Sets `"id": "taylorsamarel/<canonical_slug>"`.
5. Reports every change.

This overrides older legacy slugs (`duecare-gemma-vs-oss-comparison`,
`00a-duecare-prompt-prioritizer-data-pipeline`, etc.). After running,
push all kernels — Kaggle will either UPDATE an existing kernel at
the canonical slug (if it already created one via title-derive) or
CREATE a fresh kernel at the canonical slug. The old legacy kernels
will remain as orphans in the Kaggle UI until manually deleted.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KERNELS_DIR = REPO_ROOT / "kaggle" / "kernels"


def canonical_slug_from_title(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def main() -> int:
    changes = []
    for kd in sorted(KERNELS_DIR.iterdir()):
        if not kd.is_dir():
            continue
        meta_path = kd / "kernel-metadata.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        title = meta.get("title", "")
        canonical = canonical_slug_from_title(title)
        new_id = f"taylorsamarel/{canonical}"
        if meta.get("id") != new_id:
            changes.append((kd.name, meta.get("id"), new_id, title))
            meta["id"] = new_id
            meta_path.write_text(
                json.dumps(meta, indent=2) + "\n", encoding="utf-8"
            )

    print(f"Changed {len(changes)} kernel metadata files:\n")
    for dir_name, old, new, title in changes:
        print(f"  {dir_name}")
        print(f"    title: {title}")
        print(f"    old id: {old}")
        print(f"    new id: {new}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
