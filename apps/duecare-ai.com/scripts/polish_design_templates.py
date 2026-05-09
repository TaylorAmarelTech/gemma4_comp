"""Apply the post-launch polish pass across every design template.

Covers feedback collected after the first deploy:
- footer: drop "v0.4 · public hub draft" stamp
- nav: add Mission link to the left of Demo
- nav: "Get involved" CTA goes to /contribute, not /login
- copy: kill em-dashes (replace ` — ` with `. `, ` – ` with `, `)
- copy: replace "signed pack(s)/manifests" wording with "vetted ..."
        across user-facing prose; "Curator-signed" -> "Curator-vetted"

Re-runnable: every transform is idempotent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"

NAV_OLD = """    <div class="nav-links">
      <a href="/demo">Demo</a>"""
NAV_NEW = """    <div class="nav-links">
      <a href="/mission">Mission</a>
      <a href="/demo">Demo</a>"""

# Several pages mark a nav link "active" with class="on" (e.g., on /demo the demo link is on)
NAV_OLD_ACTIVE_DEMO = """    <div class="nav-links">
      <a href="/demo" class="on">Demo</a>"""
NAV_NEW_ACTIVE_DEMO = """    <div class="nav-links">
      <a href="/mission">Mission</a>
      <a href="/demo" class="on">Demo</a>"""

CTA_OLD = 'href="/login?next=/contribute" class="nav-cta"'
CTA_NEW = 'href="/contribute" class="nav-cta"'

# Drop the version stamp + collapse the foot-bottom to a single span.
FOOT_OLD = '<span>&copy; 2026 DueCare AI</span><span>v0.4 &middot; public hub draft</span>'
FOOT_NEW = '<span>&copy; 2026 DueCare AI</span>'

# The "v0.4 · public hub draft" appears in a few non-foot-bottom places too.
EXTRA_VERSION_DROPS = [
    "v0.4 &middot; public hub draft",
    "v0.4 · public hub draft",
]

# Em-dash and en-dash replacements (only the spaced forms — keep hyphens in compounds).
DASH_REWRITES = [
    (" — ", ". "),
    (" – ", ", "),
    (" — ", ". "),
    (" – ", ", "),
]

# "signed" wording → "vetted" / "curated" in user-facing prose.
# Be conservative: only touch the spaced phrases that show up as nouns/labels in copy.
SIGNED_REWRITES = [
    ("Curator-signed", "Curator-vetted"),
    ("curator-signed", "curator-vetted"),
    ("signed pack manifests", "vetted pack manifests"),
    ("signed manifests", "vetted manifests"),
    ("signed packs", "vetted packs"),
    ("signed pack release", "vetted pack release"),
    ("signed pack", "vetted pack"),
    ("Signed pack", "Vetted pack"),
    ("Signed packs", "Vetted packs"),
    ("Distribute signed context packs", "Distribute vetted context packs"),
]


def transform(html: str) -> str:
    # Nav: add Mission. Two variants depending on whether Demo is the active page.
    if NAV_OLD in html and NAV_NEW not in html:
        html = html.replace(NAV_OLD, NAV_NEW)
    if NAV_OLD_ACTIVE_DEMO in html and NAV_NEW_ACTIVE_DEMO not in html:
        html = html.replace(NAV_OLD_ACTIVE_DEMO, NAV_NEW_ACTIVE_DEMO)

    # CTA target.
    html = html.replace(CTA_OLD, CTA_NEW)

    # Footer version stamp.
    html = html.replace(FOOT_OLD, FOOT_NEW)
    for stamp in EXTRA_VERSION_DROPS:
        html = html.replace(stamp, "")

    # Em / en-dashes.
    for needle, replacement in DASH_REWRITES:
        html = html.replace(needle, replacement)

    # "Signed" wording.
    for needle, replacement in SIGNED_REWRITES:
        html = html.replace(needle, replacement)

    return html


def main() -> int:
    if not TEMPLATES.is_dir():
        print(f"ERROR: templates dir not found: {TEMPLATES}", file=sys.stderr)
        return 1
    sources = sorted(TEMPLATES.glob("*.html"))
    edited = 0
    for src in sources:
        before = src.read_text(encoding="utf-8")
        after = transform(before)
        if after != before:
            src.write_text(after, encoding="utf-8")
            edited += 1
    print(f"Polished {edited} of {len(sources)} templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
