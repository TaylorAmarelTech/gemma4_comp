"""Freeze every Kaggle kernel to the current HEAD SHA for submission.

Run this once, right before the final hackathon submission.

  1. Reads ``git rev-parse --short HEAD`` -> SHA.
  2. Rewrites ``COMMIT_SHA`` / ``DUECARE_COMMIT_SHA`` = "<SHA>" in every
     ``kaggle/*/kernel.py``.
  3. Flips ``configs/submission_freeze.json`` -> ``{"frozen": true, "ref": "<SHA>"}``.

Does not auto-commit. After running, review the diff, then commit + push.

To re-enter dev mode after submission, pass ``--unfreeze``.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE_FILE = REPO_ROOT / "configs" / "submission_freeze.json"
KERNEL_GLOB = "kaggle/*/kernel.py"
PIN_RE = re.compile(
    r'(\b(?:COMMIT_SHA|DUECARE_COMMIT_SHA)\s*=\s*)"[^"]*"',
    re.IGNORECASE,
)


def _git_head_short() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _rewrite_pins(target: str) -> list[str]:
    rewritten: list[str] = []
    for kp in sorted(REPO_ROOT.glob(KERNEL_GLOB)):
        text = kp.read_text(encoding="utf-8")
        new_text, n = PIN_RE.subn(lambda m, t=target: f'{m.group(1)}"{t}"', text)
        if n:
            kp.write_text(new_text, encoding="utf-8")
            rewritten.append(f"{kp.relative_to(REPO_ROOT).as_posix()} ({n})")
    return rewritten


def freeze() -> int:
    sha = _git_head_short()
    rewritten = _rewrite_pins(sha)
    FREEZE_FILE.parent.mkdir(parents=True, exist_ok=True)
    FREEZE_FILE.write_text(
        json.dumps(
            {
                "frozen": True,
                "ref": sha,
                "note": f"Frozen at {sha} for final submission. Re-paste every "
                "kaggle/*/kernel.py into Kaggle to lock in this SHA.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Frozen to {sha}. Rewrote {len(rewritten)} kernels:")
    for line in rewritten:
        print(f"  - {line}")
    print("\nNext steps:")
    print("  1. Review the diff: git diff")
    print("  2. Run: pytest tests/test_kaggle_install_policy.py -q")
    print("  3. Commit + push.")
    print("  4. Re-paste every kaggle/*/kernel.py into Kaggle.")
    return 0


def unfreeze() -> int:
    rewritten = _rewrite_pins("main")
    FREEZE_FILE.write_text(
        json.dumps(
            {
                "frozen": False,
                "ref": None,
                "note": "Dev mode — kernels track main. Run this script without --unfreeze before final submission.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Unfrozen (dev mode). Rewrote {len(rewritten)} kernels to track main:")
    for line in rewritten:
        print(f"  - {line}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--unfreeze",
        action="store_true",
        help="Flip back to dev mode (kernels track main).",
    )
    args = parser.parse_args()
    return unfreeze() if args.unfreeze else freeze()


if __name__ == "__main__":
    sys.exit(main())
