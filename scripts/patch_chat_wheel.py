"""scripts/patch_chat_wheel.py

In-place patch the duecare_llm_chat-0.1.0-py3-none-any.whl in every
kaggle/<notebook>/wheels/ folder with the latest source files from
packages/duecare-llm-chat/src/.

Why this exists: the local Python build toolchain is broken on every
installed interpreter (Python 3.12/3.13/3.14 all have the
pip._vendor.rich.console ModuleNotFoundError). Until that's fixed in a
fresh venv, we patch the wheel zip directly: extract, overwrite the
files we changed, recompute RECORD, repack.

Files that get patched if changed:
- duecare/chat/app.py
- duecare/chat/static/index.html
- duecare/chat/harness/__init__.py
- duecare/chat/harness/_rubrics_required.json
- duecare/chat/harness/_rubrics_5tier.json
- duecare/chat/harness/_examples.json
- duecare/chat/harness/_classifier_examples.json

Usage:
    python scripts/patch_chat_wheel.py                # patch all wheels
    python scripts/patch_chat_wheel.py --dry-run      # show what would change
    python scripts/patch_chat_wheel.py --target kaggle/chat-playground
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import shutil
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "packages" / "duecare-llm-chat" / "src"

# Files to patch in the wheel: src path -> path inside the wheel
PATCH_FILES = {
    SRC_ROOT / "duecare" / "chat" / "app.py":
        "duecare/chat/app.py",
    SRC_ROOT / "duecare" / "chat" / "__init__.py":
        "duecare/chat/__init__.py",
    SRC_ROOT / "duecare" / "chat" / "static" / "index.html":
        "duecare/chat/static/index.html",
    SRC_ROOT / "duecare" / "chat" / "harness" / "__init__.py":
        "duecare/chat/harness/__init__.py",
    SRC_ROOT / "duecare" / "chat" / "harness" / "_rubrics_required.json":
        "duecare/chat/harness/_rubrics_required.json",
    SRC_ROOT / "duecare" / "chat" / "harness" / "_rubrics_5tier.json":
        "duecare/chat/harness/_rubrics_5tier.json",
    SRC_ROOT / "duecare" / "chat" / "harness" / "_examples.json":
        "duecare/chat/harness/_examples.json",
    SRC_ROOT / "duecare" / "chat" / "harness" / "_classifier_examples.json":
        "duecare/chat/harness/_classifier_examples.json",
    SRC_ROOT / "duecare" / "chat" / "classifier.py":
        "duecare/chat/classifier.py",
    SRC_ROOT / "duecare" / "chat" / "classifier_static" / "index.html":
        "duecare/chat/classifier_static/index.html",
}

WHEEL_NAME = "duecare_llm_chat-0.1.0-py3-none-any.whl"
DIST_INFO = "duecare_llm_chat-0.1.0.dist-info"
RECORD_PATH = f"{DIST_INFO}/RECORD"


def _record_hash(data: bytes) -> str:
    """Compute the urlsafe-base64 sha256 hash with no padding, the exact
    format the wheel RECORD uses."""
    h = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(h).rstrip(b"=").decode()


def patch_wheel(wheel_path: Path, dry_run: bool = False) -> bool:
    """Patch the wheel at `wheel_path` in place. Returns True if any file
    was actually changed."""
    print(f"\n--- {wheel_path} ---")
    with zipfile.ZipFile(wheel_path, "r") as zin:
        old_names = list(zin.namelist())
        old_data = {n: zin.read(n) for n in old_names}

    changed = False
    new_data = dict(old_data)
    for src_path, wheel_path_in in PATCH_FILES.items():
        if not src_path.exists():
            continue
        latest = src_path.read_bytes()
        existing = old_data.get(wheel_path_in)
        if existing == latest:
            continue
        size_before = len(existing) if existing else 0
        size_after = len(latest)
        diff = size_after - size_before
        diff_s = f"+{diff}" if diff > 0 else str(diff)
        marker = "[NEW]" if existing is None else "[CHG]"
        print(f"  {marker} {wheel_path_in}: "
              f"{size_before:,} -> {size_after:,} ({diff_s} bytes)")
        new_data[wheel_path_in] = latest
        changed = True

    if not changed:
        print("  (no changes)")
        return False

    # Rebuild RECORD: hash every file except RECORD itself
    record_lines = []
    for n in sorted(new_data):
        if n == RECORD_PATH:
            continue
        b = new_data[n]
        record_lines.append(f"{n},{_record_hash(b)},{len(b)}")
    record_lines.append(f"{RECORD_PATH},,")
    new_record = ("\n".join(record_lines) + "\n").encode()
    new_data[RECORD_PATH] = new_record

    if dry_run:
        print("  (dry run -- not writing)")
        return True

    # Write to temp + atomic rename
    tmp = wheel_path.with_suffix(".whl.tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for n in sorted(new_data):
            zout.writestr(n, new_data[n])
    shutil.move(str(tmp), str(wheel_path))
    print(f"  wrote {wheel_path.stat().st_size:,} bytes")
    return True


def find_targets(target: str | None) -> list[Path]:
    """Locate every kaggle/<notebook>/wheels/<chat-wheel>."""
    if target:
        candidates = [Path(target)]
    else:
        candidates = sorted(p for p in (REPO_ROOT / "kaggle").glob("*/wheels"))
    out = []
    for wheels_dir in candidates:
        wp = wheels_dir / WHEEL_NAME
        if wp.exists():
            out.append(wp)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                     help="show what would change without writing")
    ap.add_argument("--target",
                     help="patch only one wheels dir (e.g. "
                          "kaggle/chat-playground/wheels)")
    args = ap.parse_args()

    targets = find_targets(args.target)
    if not targets:
        raise SystemExit("no chat wheels found")
    print(f"found {len(targets)} chat wheel(s) to consider:")
    for t in targets:
        print(f"  - {t}")

    n_changed = 0
    for wp in targets:
        if patch_wheel(wp, dry_run=args.dry_run):
            n_changed += 1

    print(f"\n[patch_chat_wheel] {n_changed} of {len(targets)} wheels patched"
          f"{' (dry run)' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
