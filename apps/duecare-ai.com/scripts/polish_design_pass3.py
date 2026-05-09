"""Third polish pass.

Sweeps the audit punch list across all templates plus main.py:

- ``signed pack(s)`` / ``Signed pack(s)`` / ``Curator-signed`` / ``signed
  knowledge packs`` / ``signed corridor pack(s)`` / ``Signed`` pill text
  -> ``vetted ...``  (terminology drift; "signed" reads as cryptic to
  non-engineers, see audit headline finding 1.1)
- ``Duecare AI`` (in <title> tags only) -> ``DueCare AI``  (brand casing)
- ``coarse_signal.schema.json`` -> ``anonymized_signal.schema.json``  (sweep
  miss from polish_design_pass2)
- six prose em-dashes the audit listed by line (handled here verbatim)

Idempotent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "app" / "templates"
MAIN_PY = ROOT / "app" / "main.py"

SIGNED_REWRITES: list[tuple[str, str]] = [
    ("signed knowledge pack manifests", "vetted knowledge pack manifests"),
    ("signed knowledge packs", "vetted knowledge packs"),
    ("signed knowledge pack", "vetted knowledge pack"),
    ("signed corridor packs", "vetted corridor packs"),
    ("signed corridor pack", "vetted corridor pack"),
    ("Signed corridor packs", "Vetted corridor packs"),
    ("Signed corridor pack", "Vetted corridor pack"),
    ("signed knowledge assets", "vetted knowledge assets"),
    ("signed in batches", "vetted in batches"),
    ("Recently signed", "Recently vetted"),
    ("signed runtime", "vetted runtime"),
    ("Accepted &amp; signed", "Accepted &amp; vetted"),
    ("Accepted & signed", "Accepted & vetted"),
    ("Curator-signed", "Curator-vetted"),
    ("Curator signs;", "Curator vets and signs;"),
    ("Signed-in curator", "A signed-in curator"),
    ('class="badge verified">Signed</span>', 'class="badge verified">Vetted</span>'),
    ('<span class="hp-pill ok">Signed</span>', '<span class="hp-pill ok">Vetted</span>'),
    # registry pill text on knowledge-packs.html and packages.html
    (">Signed</span>", ">Vetted</span>"),
    # "Signed release" verb in stats timeline
    ("Signed release", "Vetted release"),
    # broad noun phrase
    ("signed release", "vetted release"),
    ("Reviewed by curators before signing.", "Reviewed by curators before publication."),
    ("before signing", "before publication"),
]

# Small note: keep the literal cryptographic verb when describing signature
# verification (curator key, ed25519, `duecare verify pack.json`). Those don't
# match any of the SIGNED_REWRITES patterns above.

EM_DASH_REWRITES: list[tuple[str, str]] = [
    ("free-text case fields at the edge —", "free-text case fields at the edge."),
    ("or model conversations —", "or model conversations."),
    ("optionally —", "optionally"),
    ("vetted corridor pack —", "vetted corridor pack."),
    ("registries, regulator pages —", "registries, regulator pages."),
    ("run the harness on Gemma 4 —", "run the harness on Gemma 4."),
]

SCHEMA_REWRITES: list[tuple[str, str]] = [
    ("coarse_signal.schema.json", "anonymized_signal.schema.json"),
]

TITLE_BRAND_RE = re.compile(r"<title>(.*?)Duecare AI(.*?)</title>", re.IGNORECASE)


def fix_titles(html: str) -> str:
    return TITLE_BRAND_RE.sub(lambda m: f"<title>{m.group(1)}DueCare AI{m.group(2)}</title>", html)


def transform(html: str) -> str:
    for needle, replacement in SIGNED_REWRITES:
        html = html.replace(needle, replacement)
    for needle, replacement in EM_DASH_REWRITES:
        html = html.replace(needle, replacement)
    for needle, replacement in SCHEMA_REWRITES:
        html = html.replace(needle, replacement)
    html = fix_titles(html)
    return html


def main() -> int:
    if not TEMPLATES.is_dir():
        print(f"ERROR: templates dir not found: {TEMPLATES}", file=sys.stderr)
        return 1
    edited = 0
    for src in sorted(TEMPLATES.glob("*.html")):
        before = src.read_text(encoding="utf-8")
        after = transform(before)
        if after != before:
            src.write_text(after, encoding="utf-8")
            edited += 1
    # main.py: only the API description string ("signed knowledge packs").
    if MAIN_PY.is_file():
        before = MAIN_PY.read_text(encoding="utf-8")
        after = before.replace("signed knowledge packs", "vetted knowledge packs")
        if after != before:
            MAIN_PY.write_text(after, encoding="utf-8")
            edited += 1
    print(f"Polished {edited} files in pass 3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
