"""Extract <script> blocks from the chat package's static HTML files and
syntax-check them via `node --check`. Catches the kind of typo that
won't surface until the kernel is already running and a judge clicks
the modal.

Run:
    py -3.10 scripts/v141_check_static_js.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATIC = REPO / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "static"

TARGETS = [
    STATIC / "index.html",
    STATIC / "rag-graph.html",
    STATIC / "harness.html",
    STATIC / "grep-rules.html",
    STATIC / "rag-corpus.html",
    STATIC / "tools.html",
    STATIC / "online.html",
    STATIC / "persona.html",
    STATIC / "grep-tester.html",
    STATIC / "search.html",
    STATIC / "hotlines.html",
]


SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)


def check_one(html_path: Path) -> int:
    if not html_path.exists():
        print(f"  MISSING: {html_path}")
        return 1
    text = html_path.read_text(encoding="utf-8")
    blocks = SCRIPT_RE.findall(text)
    if not blocks:
        print(f"  NO SCRIPT BLOCKS: {html_path.name}")
        return 0
    failures = 0
    for i, block in enumerate(blocks):
        # Skip blocks that are non-JS (e.g. JSON-LD, ld+json) — but ours are JS.
        with tempfile.NamedTemporaryFile(
            "w", suffix=f".{html_path.stem}.{i}.mjs", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(block)
            tmp_path = tmp.name
        try:
            r = subprocess.run(
                ["node", "--check", tmp_path],
                capture_output=True,
                text=True,
            )
            if r.returncode != 0:
                print(f"  FAIL block #{i} of {html_path.name}:")
                print(r.stderr)
                failures += 1
            else:
                lines = block.count("\n") + 1
                print(f"  OK   block #{i} of {html_path.name} ({lines} lines)")
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    return failures


def main() -> int:
    fails = 0
    for t in TARGETS:
        print(f"\nChecking {t.relative_to(REPO)}...")
        fails += check_one(t)
    print()
    if fails:
        print(f"FAILED: {fails} script blocks have syntax errors.")
        return 2
    print("All script blocks parse cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
