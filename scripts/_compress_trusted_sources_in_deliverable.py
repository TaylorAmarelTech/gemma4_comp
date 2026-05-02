"""Post-process: replace the verbose TRUSTED_SOURCES Python literal in
gemma4_multimodal_with_rag_grep_v1.py with a gzip+base64 blob that
decodes at runtime. Shrinks the pasted Kaggle cell by ~120 KB without
changing behavior.

Run after any rebuild of the deliverable.
"""
from __future__ import annotations

import base64
import json
import re
import sys
import zlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DELIVERABLE = REPO_ROOT / "raw_python" / "gemma4_multimodal_with_rag_grep_v1.py"

KEEP = ("url", "category", "source", "license", "attribution", "score")

LITERAL_RE = re.compile(
    r"^TRUSTED_SOURCES:\s*list\[dict\]\s*=\s*\[\n.*?^\]\n",
    re.DOTALL | re.MULTILINE,
)


def _extract_entries(block: str) -> list[dict]:
    import ast
    tree = ast.parse(block)
    for node in ast.walk(tree):
        if (isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "TRUSTED_SOURCES"
                and isinstance(node.value, ast.List)):
            return [ast.literal_eval(el) for el in node.value.elts]
    raise RuntimeError("TRUSTED_SOURCES literal not parsable")


def _chunked_b64(b64: str, width: int = 72) -> str:
    lines = [b64[i:i + width] for i in range(0, len(b64), width)]
    quoted = "\n".join(f'    "{ln}"' for ln in lines)
    return f"(\n{quoted}\n)"


def _build_replacement(entries: list[dict]) -> str:
    slim = [
        {k: e[k] for k in KEEP if k in e}
        for e in entries
    ]
    raw = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
    gz = zlib.compress(raw.encode("utf-8"), 9)
    b64 = base64.b64encode(gz).decode("ascii")
    chunks = _chunked_b64(b64, 72)
    return (
        f"# TRUSTED_SOURCES: {len(entries)} public Wikimedia Commons URLs,\n"
        f"# gzip+base64 compressed ({len(raw)} -> {len(b64)} bytes) to keep\n"
        f"# the pasted Kaggle cell manageable. Decoded once at import.\n"
        f"import base64 as _ts_b64\n"
        f"import json as _ts_json\n"
        f"import zlib as _ts_zlib\n"
        f"_TRUSTED_SOURCES_BLOB = {chunks}\n"
        f"TRUSTED_SOURCES: list[dict] = _ts_json.loads(\n"
        f"    _ts_zlib.decompress(_ts_b64.b64decode(_TRUSTED_SOURCES_BLOB))\n"
        f"    .decode('utf-8')\n"
        f")\n"
        f"del _ts_b64, _ts_json, _ts_zlib, _TRUSTED_SOURCES_BLOB\n"
    )


def main() -> int:
    if not DELIVERABLE.exists():
        print(f"[compress] missing {DELIVERABLE}")
        return 1
    src = DELIVERABLE.read_text(encoding="utf-8")
    m = LITERAL_RE.search(src)
    if not m:
        print("[compress] TRUSTED_SOURCES literal not found; is it already compressed?")
        return 2
    entries = _extract_entries(m.group(0))
    replacement = _build_replacement(entries)
    new_src = src[: m.start()] + replacement + src[m.end():]
    old_size = len(src)
    new_size = len(new_src)
    DELIVERABLE.write_text(new_src, encoding="utf-8")
    print(f"[compress] entries            : {len(entries)}")
    print(f"[compress] literal block      : {m.end() - m.start():>8,} bytes")
    print(f"[compress] replacement block  : {len(replacement):>8,} bytes")
    print(f"[compress] deliverable        : {old_size:>8,} -> {new_size:>8,} bytes")
    print(f"[compress] savings            : {old_size - new_size:>8,} bytes  ({100*(old_size-new_size)/old_size:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
