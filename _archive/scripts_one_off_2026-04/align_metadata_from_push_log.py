"""Align each kernel-metadata.json id to its ACTUAL live Kaggle slug.

Strategy:
1. Parse the push log from `push_all_sequential.py`. For every kernel
   that pushed successfully, extract the live slug from the response
   URL (e.g., `https://www.kaggle.com/code/taylorsamarel/140-duecare-evaluation-mechanics`
   -> `taylorsamarel/140-duecare-evaluation-mechanics`).
2. For every kernel that FAILED or got Notebook not found, compute the
   title-derived slug (Kaggle's default when metadata id is unknown) so
   the next push can proceed cleanly as a new-kernel creation.
3. Rewrite each `kaggle/kernels/<dir>/kernel-metadata.json` with the
   correct id. Leave title, keywords, and other fields untouched.
4. Also update `scripts/kaggle_live_slug_map.json` to reflect verified
   live slugs.

Usage: `python scripts/align_metadata_from_push_log.py <push_log_path>`
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KERNELS_DIR = REPO_ROOT / "kaggle" / "kernels"
SLUG_MAP_PATH = REPO_ROOT / "scripts" / "kaggle_live_slug_map.json"


ENTRY_RE = re.compile(
    r"\[\d+/\d+\]\s+(?P<dir>duecare_\S+)\s*\n"
    r"\s+id:\s+(?P<id>\S+)\s*\n"
    r"\s+title:\s+(?P<title>.+?)\s*\n"
    r"\s+RESULT:?\s*(?P<result>.+?)\s*\n",
    re.MULTILINE,
)

URL_RE = re.compile(r"https?://www\.kaggle\.com/(?:code/)?(?P<owner>[^/]+)/(?P<slug>[^\s]+)")


def slugify(title: str) -> str:
    """Match Kaggle's title-to-slug heuristic."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def parse_log(log_text: str) -> list[dict[str, str]]:
    entries = []
    for m in ENTRY_RE.finditer(log_text):
        entries.append({
            "dir": m.group("dir"),
            "id": m.group("id"),
            "title": m.group("title").strip(),
            "result": m.group("result").strip(),
        })
    return entries


def actual_live_slug(entry: dict[str, str]) -> str | None:
    result = entry["result"]
    if "successfully pushed" in result.lower():
        # Extract the check-progress URL.
        m = URL_RE.search(result)
        if m:
            owner = m.group("owner")
            slug = m.group("slug")
            if owner == "taylorsamarel":
                return f"{owner}/{slug}"
    return None


def desired_id_for(entry: dict[str, str]) -> str:
    """Decide the metadata id for this kernel.

    If the push succeeded, use the actual live slug. If it failed,
    fall back to the title-derived slug so the next creation push
    lines up with what Kaggle would have chosen anyway.
    """
    live = actual_live_slug(entry)
    if live:
        return live
    # Failed or not-found: use title-derived
    return f"taylorsamarel/{slugify(entry['title'])}"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: align_metadata_from_push_log.py <push_log_path>", file=sys.stderr)
        return 2
    log_path = Path(sys.argv[1])
    entries = parse_log(log_path.read_text(encoding="utf-8", errors="replace"))
    print(f"Parsed {len(entries)} entries from {log_path}")

    slug_map = {}
    if SLUG_MAP_PATH.exists():
        slug_map = json.loads(SLUG_MAP_PATH.read_text(encoding="utf-8"))

    changed = 0
    for entry in entries:
        kd = KERNELS_DIR / entry["dir"]
        meta_path = kd / "kernel-metadata.json"
        if not meta_path.exists():
            print(f"skip {entry['dir']}: no metadata file")
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        desired_id = desired_id_for(entry)
        live = actual_live_slug(entry)

        if meta.get("id") != desired_id:
            print(f"{entry['dir']}: {meta.get('id')} -> {desired_id}")
            meta["id"] = desired_id
            meta_path.write_text(
                json.dumps(meta, indent=2) + "\n", encoding="utf-8"
            )
            changed += 1

        # Only mark the live-slug map if we know the slug is verified live.
        if live:
            slug_map[entry["dir"]] = live
        # Keep existing entry if we know nothing new.

    SLUG_MAP_PATH.write_text(
        json.dumps(slug_map, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Updated {changed} metadata files; slug map refreshed at {SLUG_MAP_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
