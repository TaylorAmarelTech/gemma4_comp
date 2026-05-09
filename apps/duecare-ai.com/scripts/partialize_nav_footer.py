"""Replace inline <nav> + <footer> blocks across templates with Jinja includes.

Why: the same nav and footer markup is duplicated in all 38 templates. Every
copy-edit (drop a stamp, add a link, change an active state) currently means a
38-file sweep or a brittle bulk-replace script. After this refactor:

- shared markup lives in `_nav.html` and `_footer.html`
- every page does `{% set active_nav = "..." %}` then `{% include "_nav.html" %}`
- single source of truth, future fixes are one edit

Idempotent: if a template already has the include directive, it's skipped.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"

# Map each template filename to its active-nav slug (the top-level nav item that
# should render with class="on" while the user is on this page).
ACTIVE_NAV: dict[str, str] = {
    "index.html": "",
    "mission.html": "mission",
    "demo.html": "demo",
    "use-cases.html": "use-cases",
    "hub.html": "hub",
    "knowledge-packs.html": "hub",
    "tools-registry.html": "hub",
    "research-monitor.html": "hub",
    "submit-information.html": "hub",
    "alerts.html": "hub",
    "newsletter.html": "hub",
    "email-feedback.html": "hub",
    "privacy-boundary.html": "hub",
    "docs.html": "docs",
    "technical-docs.html": "docs",
    "components.html": "docs",
    "why-gemma.html": "docs",
    "evaluation.html": "docs",
    "harness.html": "docs",
    "setup.html": "docs",
    "intelligence.html": "docs",
    "sentinel.html": "docs",
    "tools.html": "docs",
    "context.html": "docs",
    "grep-rules.html": "docs",
    "deployments.html": "docs",
    "client-connect.html": "docs",
    "packages.html": "docs",
    "packages-detail.html": "docs",
    "stats.html": "stats",
    "dashboard.html": "stats",
    "submissions.html": "stats",
    "contribute.html": "",
    "contact.html": "",
    "partners.html": "",
    "volunteer.html": "",
    "login.html": "",
    "privacy.html": "",
}

NAV_RE = re.compile(r"<nav class=\"nav\">[\s\S]*?</nav>\s*", re.MULTILINE)
FOOTER_RE = re.compile(r"<footer>[\s\S]*?</footer>\s*", re.MULTILINE)
NAV_INCLUDE_MARK = "{% include \"_nav.html\" %}"


def transform(html: str, active_nav: str) -> str:
    if NAV_INCLUDE_MARK in html:
        return html  # already partialized
    nav_block = ""
    if active_nav:
        nav_block = f'{{% set active_nav = "{active_nav}" %}}\n{NAV_INCLUDE_MARK}\n'
    else:
        nav_block = f"{NAV_INCLUDE_MARK}\n"
    html = NAV_RE.sub(nav_block, html, count=1)
    html = FOOTER_RE.sub('{% include "_footer.html" %}\n', html, count=1)
    return html


def main() -> int:
    if not TEMPLATES.is_dir():
        print(f"ERROR: templates dir not found: {TEMPLATES}", file=sys.stderr)
        return 1
    edited = 0
    for src in sorted(TEMPLATES.glob("*.html")):
        if src.name.startswith("_"):
            continue
        before = src.read_text(encoding="utf-8")
        active_nav = ACTIVE_NAV.get(src.name, "")
        after = transform(before, active_nav)
        if after != before:
            src.write_text(after, encoding="utf-8")
            edited += 1
    print(f"Partialized {edited} templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
