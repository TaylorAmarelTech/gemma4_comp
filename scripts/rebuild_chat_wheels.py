"""Rebuild every duecare_llm_chat wheel in kaggle/<notebook>/wheels/
from the current source tree without going through pip.

Why: the local Python 3.14 env has a broken pip (`_pytest.fixtures`
ModuleNotFoundError). Pure-Python packages don't need pip — a wheel
is just a zip with metadata. This script:

  1. Reads the source from packages/duecare-llm-chat/src/duecare/chat/
  2. Opens each existing wheel
  3. Replaces every file under duecare/chat/ with the current source
  4. Rewrites the RECORD file with new sha256 + size for changed files

Run:
    python scripts/rebuild_chat_wheels.py

Idempotent. Safe to re-run after every chat package edit.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import sys
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CHAT_SRC = REPO / "packages" / "duecare-llm-chat" / "src"
WHEEL_NAME = "duecare_llm_chat-0.1.0-py3-none-any.whl"


def _hash_b64(data: bytes) -> str:
    """Compute the wheel-RECORD-style sha256 hash (urlsafe base64, no padding)."""
    h = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(h).rstrip(b"=").decode("ascii")


def _collect_source_files() -> dict[str, bytes]:
    """Walk the chat source tree and return {arcname: bytes} for every file."""
    out: dict[str, bytes] = {}
    chat_root = CHAT_SRC / "duecare" / "chat"
    if not chat_root.is_dir():
        raise FileNotFoundError(f"Chat source not found: {chat_root}")
    for f in sorted(chat_root.rglob("*")):
        if not f.is_file():
            continue
        # Skip build artifacts + meta files we don't ship in the wheel
        if "__pycache__" in f.parts or f.suffix in (".pyc", ".pyo"):
            continue
        # Skip module meta files (PURPOSE.md, AGENTS.md, etc.) — internal docs
        if f.name in {
            "PURPOSE.md", "AGENTS.md", "INPUTS_OUTPUTS.md",
            "HIERARCHY.md", "DIAGRAM.md", "TESTS.md", "STATUS.md",
        }:
            continue
        rel = f.relative_to(CHAT_SRC).as_posix()
        out[rel] = f.read_bytes()
    return out


def _patch_wheel(wheel_path: Path, source_files: dict[str, bytes]) -> tuple[int, int]:
    """Replace every duecare/chat/ entry in the wheel with the current source.

    Returns (entries_replaced, entries_added).
    """
    with zipfile.ZipFile(wheel_path, "r") as z:
        original = {info.filename: z.read(info.filename) for info in z.infolist()}

    # Find the .dist-info folder (single root dir)
    dist_info = None
    for name in original:
        if "/" in name and name.split("/", 1)[0].endswith(".dist-info"):
            dist_info = name.split("/", 1)[0]
            break
    if dist_info is None:
        raise RuntimeError(f"No .dist-info in wheel {wheel_path}")

    # Build the new file map: keep dist-info entries (RECORD is rebuilt below),
    # replace every duecare/ entry with current source.
    new_map: dict[str, bytes] = {}
    replaced = 0
    added = 0
    for name, data in original.items():
        if name.startswith(f"{dist_info}/"):
            # Keep dist-info; we'll regenerate RECORD specifically below
            new_map[name] = data
        elif name.startswith("duecare/"):
            if name in source_files:
                new_data = source_files[name]
                new_map[name] = new_data
                if new_data != data:
                    replaced += 1
            # else: file removed from source — drop it
    # Add any source files not previously in the wheel
    for name, data in source_files.items():
        if name not in new_map:
            new_map[name] = data
            added += 1

    # Rebuild RECORD: every non-RECORD entry gets sha256 + size
    record_lines = []
    for name in sorted(new_map):
        if name.endswith("/RECORD"):
            continue  # placeholder, written last
        data = new_map[name]
        record_lines.append(f"{name},{_hash_b64(data)},{len(data)}\n")
    # RECORD itself has no hash and no size
    record_lines.append(f"{dist_info}/RECORD,,\n")
    new_map[f"{dist_info}/RECORD"] = "".join(record_lines).encode("utf-8")

    # Write the new wheel atomically
    tmp = wheel_path.with_suffix(".whl.tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name in sorted(new_map):
            z.writestr(name, new_map[name])
    tmp.replace(wheel_path)
    return replaced, added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be changed without writing.",
    )
    parser.add_argument(
        "--target",
        action="append",
        help="Restrict to a specific notebook folder name (e.g., chat-playground). May be repeated.",
    )
    args = parser.parse_args()

    print("Loading chat source...")
    source_files = _collect_source_files()
    print(f"  {len(source_files)} source files found under {CHAT_SRC}/duecare/chat/")

    # Sanity: verify the new harness has 42 rules before we touch any wheel
    init_src = source_files.get("duecare/chat/harness/__init__.py", b"").decode("utf-8")
    if init_src:
        import ast
        tree = ast.parse(init_src)
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id == "GREP_RULES":
                        count = len(n.value.elts)
                        print(f"  Source GREP_RULES count: {count}")
                        if count != 42:
                            print(f"  WARNING expected 42 GREP rules, got {count}")
                        break

    # Find every chat wheel under kaggle/
    wheels = sorted((REPO / "kaggle").rglob(WHEEL_NAME))
    if args.target:
        wheels = [w for w in wheels if w.parent.parent.name in args.target]
    print(f"\nFound {len(wheels)} chat wheel(s) to rebuild:")
    total_replaced = 0
    total_added = 0
    for w in wheels:
        rel = w.relative_to(REPO)
        if args.dry_run:
            print(f"  WOULD PATCH {rel}")
            continue
        replaced, added = _patch_wheel(w, source_files)
        # Verify the patched wheel
        with zipfile.ZipFile(w) as z:
            new_init = z.read("duecare/chat/harness/__init__.py").decode("utf-8")
        try:
            import ast
            tree = ast.parse(new_init)
            new_count = next(
                (len(n.value.elts) for n in ast.walk(tree)
                 if isinstance(n, ast.Assign)
                 for t in n.targets
                 if isinstance(t, ast.Name) and t.id == "GREP_RULES"),
                None,
            )
        except Exception:
            new_count = "?"
        print(
            f"  PATCHED {rel}  (+{added} added, ~{replaced} replaced, "
            f"now ships {new_count} GREP rules)"
        )
        total_replaced += replaced
        total_added += added

    if not args.dry_run:
        print(
            f"\nDone: {total_added} file(s) added, {total_replaced} file(s) "
            f"replaced across {len(wheels)} wheel(s)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
