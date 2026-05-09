"""Convert the design-bundle HTML files into Jinja templates.

The design bundle (claude.ai/design export) ships flat HTML files where every
internal link is `href="something.html"` and CSS is `href="styles.css"`. The
production hub mounts CSS at `/static/...` and serves clean URLs (`/`, `/hub`,
`/use-cases`, ...). This script applies those rewrites across every file.

Run once after dropping a fresh design export under DESIGN_SRC.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DESIGN_SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/dc_design")
TEMPLATES_DST = Path(__file__).resolve().parent.parent / "app" / "templates"

CSS_REWRITES: list[tuple[str, str]] = [
    ('href="styles.css"', 'href="/static/styles.css"'),
    ('href="hub-pages.css"', 'href="/static/hub-pages.css"'),
]

# Internal page links: convert href="foo.html" to href="/foo" and href="index.html" to href="/".
# Skip anchors (#...), absolute URLs, mailto:, and login query-string variant.
LINK_RE = re.compile(r'href="(?!https?://|#|mailto:|/)(?P<page>[a-z0-9-]+)\.html(?P<rest>(?:[#?][^"]*)?)"')


def transform_link(match: re.Match[str]) -> str:
    page = match.group("page")
    rest = match.group("rest")
    # Strip trailing .html from any next= or anchor params too.
    rest = re.sub(r"([?&]next=)([a-z0-9-]+)\.html", r"\1/\2", rest)
    if page == "index":
        href = "/" + rest
    else:
        href = f"/{page}{rest}"
    return f'href="{href}"'


def transform(html: str) -> str:
    for needle, replacement in CSS_REWRITES:
        html = html.replace(needle, replacement)
    html = LINK_RE.sub(transform_link, html)
    return html


def main() -> int:
    if not DESIGN_SRC.is_dir():
        print(f"ERROR: design source dir not found: {DESIGN_SRC}", file=sys.stderr)
        return 1
    TEMPLATES_DST.mkdir(parents=True, exist_ok=True)
    sources = sorted(DESIGN_SRC.glob("*.html"))
    if not sources:
        print(f"ERROR: no .html files in {DESIGN_SRC}", file=sys.stderr)
        return 1
    written = 0
    for src in sources:
        dst = TEMPLATES_DST / src.name
        dst.write_text(transform(src.read_text(encoding="utf-8")), encoding="utf-8")
        written += 1
    print(f"Wrote {written} templates to {TEMPLATES_DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
