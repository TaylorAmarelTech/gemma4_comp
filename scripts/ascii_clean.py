#!/usr/bin/env python3
"""Replace non-ASCII punctuation with ASCII in a file (in place) to avoid Kaggle mojibake (e.g. 'Â·').

    python scripts/ascii_clean.py <file> [<file> ...]
"""
from __future__ import annotations
import sys
from pathlib import Path

MAP = {
    "—": "-", "–": "-", "−": "-", "·": "-", "•": "*",
    "×": "x", "≥": ">=", "≤": "<=", "→": "->", "←": "<-",
    "…": "...", "⬦": "", "◆": "", "±": "+/-", " ": " ",
    "“": '"', "”": '"', "‘": "'", "’": "'",
    "°": " deg", "≈": "~", "≠": "!=", "≡": "=", "é": "e",
}


def clean_text(t: str) -> tuple[str, int]:
    for k, v in MAP.items():
        t = t.replace(k, v)
    # any remaining non-ASCII -> strip, and report how many
    stray = sum(1 for c in t if ord(c) > 127)
    if stray:
        t = t.encode("ascii", "ignore").decode("ascii")
    return t, stray


def clean_file(p: Path) -> None:
    orig = p.read_text(encoding="utf-8")
    cleaned, stray = clean_text(orig)
    if cleaned != orig:
        p.write_text(cleaned, encoding="utf-8")
        print(f"cleaned {p} (stray non-ascii stripped: {stray})")
    else:
        print(f"already ascii: {p}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        clean_file(Path(arg))
