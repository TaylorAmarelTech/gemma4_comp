"""Force every kernel-metadata.json `id` to match the live-slug map.

Source of truth: `scripts/kaggle_live_slug_map.json`.

- If the map has a non-null slug for a kernel dir, that is the id.
- If the map has null, leave the existing metadata id alone (it is
  either a first-time creation target or a placeholder).

Run AFTER `align_metadata_from_push_log.py` to undo its over-correction
on the already-live kernels.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KERNELS_DIR = REPO_ROOT / "kaggle" / "kernels"
SLUG_MAP_PATH = REPO_ROOT / "scripts" / "kaggle_live_slug_map.json"


def main() -> int:
    slug_map = json.loads(SLUG_MAP_PATH.read_text(encoding="utf-8"))
    changed = 0
    for dir_name, live_slug in slug_map.items():
        if live_slug is None:
            continue
        meta_path = KERNELS_DIR / dir_name / "kernel-metadata.json"
        if not meta_path.exists():
            print(f"skip {dir_name}: no metadata file")
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("id") != live_slug:
            print(f"{dir_name}: {meta.get('id')} -> {live_slug}")
            meta["id"] = live_slug
            meta_path.write_text(
                json.dumps(meta, indent=2) + "\n", encoding="utf-8"
            )
            changed += 1
    print(f"Aligned {changed} metadata files to slug map")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
