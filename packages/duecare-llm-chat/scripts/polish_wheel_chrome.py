"""Bulk polish for the wheel's static viewer pages.

Goal: visual coherence with the duecare-ai.com website without forcing a
structural rewrite of each viewer. Adds the shared ``_chrome.css``
stylesheet link to every viewer page (which loads Inter + JetBrains Mono
and the shared color tokens), then renames the page titles + h1s into
plain English so they stop saying things like "Harness inspector" and
"Duecare Gemma Chat".

Re-runnable.
"""

from __future__ import annotations

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "src" / "duecare" / "chat" / "static"

# (page-filename, new <title>, old h1 text -> new h1 text)
PAGES: list[tuple[str, str, dict[str, str]]] = [
    (
        "index.html",
        "Migrant-worker safety playground · DueCare",
        {
            "Duecare Gemma Chat": "Migrant-worker safety playground · DueCare",
            ">Duecare</span> · Gemma 4 Chat": ">DueCare</span> · Migrant-worker safety chat",
        },
    ),
    (
        "harness.html",
        "Safety layers · DueCare",
        {
            "Duecare — Harness inspector": "Safety layers",
        },
    ),
    (
        "persona.html",
        "Persona library · DueCare",
        {
            "Duecare — Persona library": "Persona library",
        },
    ),
    (
        "grep-rules.html",
        "GREP rules · DueCare",
        {
            "Duecare — GREP rules": "GREP rules",
        },
    ),
    (
        "grep-tester.html",
        "Live GREP tester · DueCare",
        {
            "Duecare — Live GREP tester": "Live GREP tester",
        },
    ),
    (
        "rag-corpus.html",
        "RAG corpus · DueCare",
        {
            "Duecare — RAG corpus": "RAG corpus",
        },
    ),
    (
        "rag-graph.html",
        "Citation graph · DueCare",
        {
            "Duecare — RAG corpus graph": "Citation graph",
        },
    ),
    (
        "tools.html",
        "Tools layer · DueCare",
        {
            "Duecare — Tools": "Tools layer",
        },
    ),
    (
        "online.html",
        "Online layer · DueCare",
        {
            "Duecare — Online layer": "Online layer",
        },
    ),
    (
        "hotlines.html",
        "Hotlines & contacts · DueCare",
        {
            "Duecare — Hotlines & contacts": "Hotlines & contacts",
        },
    ),
    (
        "search.html",
        "Cross-layer search · DueCare",
        {
            "Duecare — Cross-layer search": "Cross-layer search",
        },
    ),
]

CHROME_LINK = '  <link rel="stylesheet" href="/static/_chrome.css" />'


def transform(html: str, new_title: str, swaps: dict[str, str]) -> str:
    # 1. Update <title> to the plain-English version.
    html = re.sub(r"<title>[^<]*</title>", f"<title>{new_title}</title>", html, count=1)

    # 2. Insert the chrome stylesheet link after <title> if not already there.
    if "/static/_chrome.css" not in html:
        html = html.replace("</title>", f"</title>\n{CHROME_LINK}", 1)

    # 3. Apply h1/textual swaps.
    for old, new in swaps.items():
        html = html.replace(old, new)

    return html


def main() -> int:
    edited = 0
    for filename, new_title, swaps in PAGES:
        path = STATIC / filename
        if not path.is_file():
            print(f"SKIP {filename}: not found")
            continue
        before = path.read_text(encoding="utf-8")
        after = transform(before, new_title, swaps)
        if after != before:
            path.write_text(after, encoding="utf-8")
            edited += 1
            print(f"OK   {filename}")
        else:
            print(f"NOOP {filename}")
    print(f"\nPolished {edited} of {len(PAGES)} viewer pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
