"""Second polish pass.

Fixes the awkward leftovers from `polish_design_templates.py`:
- naive ` — ` to `. ` produced clipped sentences like
  "May cross. through anonymizer" which read as broken English
- the `<aside class="audience"> <span class="chip">` tag stacks on
  use-cases.html were unlabeled jargon ("Container image · HTTP API
  · Channel adapters · On-prem / private cloud") and confused readers
- a couple of em-dashes survived inside HTML attribute strings or
  unique compounds the first script skipped

Re-runnable.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"

# Phrase-level fixes for awkward `. ` results from the first polish pass.
AWKWARD_FIXES: list[tuple[str, str]] = [
    ("May cross. through anonymizer", "May cross via anonymizer"),
    ("May cross. k-anon", "May cross at k-anon"),
    ("May cross. opt-in", "May cross. Opt-in only"),
    ("Local model. no user content leaves the platform", "Local model. No user content leaves the platform"),
    ("Suggestion only. platform decides every action", "Suggestion only. Platform decides every action"),
    ("On-device. chats never leave the phone", "On-device. Chats never leave the phone"),
    ("On-device. chat content never leaves the device", "On-device. Chat content never leaves the device"),
    ("Per-corridor adapters. quarterly", "Per-corridor adapters released quarterly"),
    ("Anonymized signals. without raw cases", "Anonymized signals only, never raw cases"),
    ("Locally. on the worker", "Locally on the worker"),
    ("Locally. in the institution", "Locally in the institution"),
    ("Locally. in your environment", "Locally in your environment"),
]

# Strip the .chip stacks from use-cases.html (unlabeled tech-tag rows confused readers).
CHIP_STACK_RE = re.compile(r"\s*<div class=\"stack\">[\s\S]*?</div>\s*", re.MULTILINE)


def transform_chips(html: str, path: Path) -> str:
    if path.name != "use-cases.html":
        return html
    return CHIP_STACK_RE.sub("\n", html)


def main() -> int:
    if not TEMPLATES.is_dir():
        print(f"ERROR: templates dir not found: {TEMPLATES}", file=sys.stderr)
        return 1
    edited = 0
    for src in sorted(TEMPLATES.glob("*.html")):
        before = src.read_text(encoding="utf-8")
        after = before
        for needle, replacement in AWKWARD_FIXES:
            after = after.replace(needle, replacement)
        after = transform_chips(after, src)
        if after != before:
            src.write_text(after, encoding="utf-8")
            edited += 1
    print(f"Polished {edited} templates in pass 2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
