"""Word count for docs/writeup_draft.md body.

Excludes the front-matter blockquote header and the closing
'Going deeper' nav block, since those don't count toward the 1,500
word submission cap.
"""

from __future__ import annotations

import re
from pathlib import Path


def count_body_words(path: Path) -> tuple[int, int, str]:
    src = path.read_text(encoding="utf-8")
    # Header is everything before the first standalone '---'.
    parts = src.split("\n---\n", 1)
    header = parts[0]
    body = parts[1] if len(parts) > 1 else ""
    # Strip closing nav.
    body = body.split("## 8. Going deeper", 1)[0]

    def words(s: str) -> list[str]:
        s = re.sub(r"```.*?```", " ", s, flags=re.DOTALL)
        s = re.sub(r"`[^`]*`", " ", s)
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        s = re.sub(r"[#>*|_\\]", " ", s)
        s = re.sub(r"\s+", " ", s)
        return [w for w in s.split() if w and not all(c in "-=:" for c in w)]

    header_words = words(header)
    body_words = words(body)
    return len(header_words), len(body_words), body


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    path = repo / "docs" / "writeup_draft.md"
    h, b, _ = count_body_words(path)
    print(f"Header words: {h} (not counted toward cap)")
    print(f"Body words:   {b} / 1500 cap")
    print(f"Margin:       {1500 - b} words remaining")


if __name__ == "__main__":
    main()
