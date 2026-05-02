"""Regenerate TRUSTED_SOURCES in multimodal_fetch_public_samples.py from
the curator's JSON manifest.

Pipeline:
    data/curated_test_set.json
        -> filter out file:// / drive-local URLs (keep HTTPS only)
        -> group by category, sort by score desc then url asc
        -> emit Python literal block
        -> splice into raw_python/multimodal_fetch_public_samples.py,
           replacing the existing TRUSTED_SOURCES list verbatim.

Also writes data/_trusted_sources_snippet.py for inspection.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CURATED_JSON = REPO_ROOT / "data" / "curated_test_set.json"
SNIPPET_OUT = REPO_ROOT / "data" / "_trusted_sources_snippet.py"
FETCH_HELPER = REPO_ROOT / "raw_python" / "multimodal_fetch_public_samples.py"

KEEP_FIELDS = ("url", "category", "source", "license", "attribution", "score")


def _keep(entry: dict) -> bool:
    url = entry.get("url", "")
    if not isinstance(url, str):
        return False
    return url.startswith("https://") or url.startswith("http://")


def _py_literal(entries: list[dict]) -> str:
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_cat[e.get("category", "unknown")].append(e)
    for cat in by_cat:
        by_cat[cat].sort(
            key=lambda e: (-float(e.get("score", 0.0)), e.get("url", ""))
        )

    lines: list[str] = ["TRUSTED_SOURCES: list[dict] = ["]
    for cat in sorted(by_cat.keys()):
        rows = by_cat[cat]
        lines.append(f"    # ---- {cat} ({len(rows)}) ----")
        for row in rows:
            lines.append("    {")
            for field in KEEP_FIELDS:
                if field not in row:
                    continue
                val = row[field]
                if field == "score":
                    lines.append(f'        "score": {float(val):.1f},')
                else:
                    s = str(val).replace("\\", "\\\\").replace('"', '\\"')
                    lines.append(f'        "{field}": "{s}",')
            lines.append("    },")
    lines.append("]")
    return "\n".join(lines) + "\n"


def _splice(helper_path: Path, snippet: str) -> tuple[int, int]:
    original = helper_path.read_text(encoding="utf-8")
    # Match: 'TRUSTED_SOURCES: list[dict] = [' ... up to the first top-level
    # closing ']' that sits on its own line at column 0.
    pattern = re.compile(
        r"^TRUSTED_SOURCES:\s*list\[dict\]\s*=\s*\[\n.*?^\]\n",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(original)
    if not m:
        raise RuntimeError("TRUSTED_SOURCES block not found in " + str(helper_path))
    old_len = m.end() - m.start()
    new_text = original[: m.start()] + snippet + original[m.end():]
    helper_path.write_text(new_text, encoding="utf-8")
    return old_len, len(snippet)


def main() -> int:
    if not CURATED_JSON.exists():
        print(f"[splice] missing {CURATED_JSON}")
        return 1
    data = json.loads(CURATED_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print(f"[splice] unexpected JSON shape: {type(data).__name__}")
        return 1
    kept = [e for e in data if _keep(e)]
    dropped = len(data) - len(kept)
    print(f"[splice] total {len(data)} -> kept {len(kept)} (dropped {dropped})")

    snippet = _py_literal(kept)
    SNIPPET_OUT.write_text(snippet, encoding="utf-8")
    print(f"[splice] wrote snippet -> {SNIPPET_OUT} ({len(snippet)} bytes)")

    old_bytes, new_bytes = _splice(FETCH_HELPER, snippet)
    print(
        f"[splice] patched {FETCH_HELPER}: "
        f"{old_bytes} -> {new_bytes} bytes"
    )

    from collections import Counter
    counts = Counter(e.get("category", "unknown") for e in kept)
    print("[splice] per-category:")
    for cat, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {cat:<28s} {n:4d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
