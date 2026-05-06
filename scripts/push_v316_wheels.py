#!/usr/bin/env python3
"""Push the v3.16 wheels to all 13 Kaggle dataset slugs.

Each notebook under `kaggle/<slug>/` has a `wheels/` subdirectory holding
the duecare wheels it ships with. This script iterates through all 13
notebooks, runs `kaggle datasets version` for each, and reports
success / failure / rate-limit per slug.

USAGE
    python scripts/push_v316_wheels.py              # push all 13
    python scripts/push_v316_wheels.py duecare-harness-chat live-demo
                                                    # push only listed
    python scripts/push_v316_wheels.py --dry-run    # show what would push

REQUIREMENTS
    - Kaggle CLI installed (pip install kaggle)
    - ~/.kaggle/kaggle.json present with valid token
    - Internet connectivity

RATE LIMIT
    Kaggle's daily push rate limit is ~5-10 versions per UTC day. If
    you hit 429 (Too Many Requests), the script reports it and you
    can resume tomorrow with the remaining slugs.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
KAGGLE_DIR = REPO_ROOT / "kaggle"

# Submission notebooks. Order matters: 2 CORE first (most important
# for judges), then appendix in canonical order.
NOTEBOOKS = [
    # 2 CORE
    "duecare-harness-chat",         # ★ omni playground
    "live-demo",                     # ★ focused thesis demo
    # 11 APPENDIX
    "chat-playground",
    "chat-playground-with-grep-rag-tools",
    "chat-playground-jailbroken-models",
    "chat-playground-with-agentic-research",
    "content-classification-playground",
    "content-knowledge-builder-playground",
    "gemma-content-classification-evaluation",
    "prompt-generation",
    "bench-and-tune",
    "research-graphs",
    "grading-evaluation",
]


def push_dataset(slug: str, dry_run: bool = False) -> tuple[bool, str]:
    """Push the wheels/ for `slug` as a new dataset version.

    Returns (success, message). On rate-limit, success=False and message
    contains '429' so caller can stop early.
    """
    wheels_dir = KAGGLE_DIR / slug / "wheels"
    if not wheels_dir.exists():
        return False, f"no wheels/ dir at {wheels_dir}"

    # Verify dataset-metadata.json present
    meta = wheels_dir / "dataset-metadata.json"
    if not meta.exists():
        return False, f"no dataset-metadata.json at {meta}"

    if dry_run:
        wheel_count = len(list(wheels_dir.glob("*.whl")))
        return True, f"DRY-RUN — would push {wheel_count} wheel(s) from {wheels_dir}"

    msg = f"v3.16 — GREP rules expanded 49 to 108 across 16 categories"
    cmd = [
        "kaggle", "datasets", "version",
        "-p", str(wheels_dir),
        "-m", msg,
        "--dir-mode", "zip",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout (600s)"
    except FileNotFoundError:
        return False, "kaggle CLI not found in PATH (pip install kaggle)"

    # Decode bytes manually so we can handle non-utf8 / non-cp1252 output
    def _decode(b):
        if b is None:
            return ""
        if isinstance(b, str):
            return b
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            return b.decode("utf-8", errors="replace")
    output = (_decode(result.stdout) + _decode(result.stderr)).strip()
    if result.returncode == 0:
        return True, output[:200] or "ok"
    if "429" in output or "rate limit" in output.lower():
        return False, f"429 RATE LIMITED: {output[:200]}"
    return False, output[:300]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "slugs", nargs="*", default=None,
        help="dataset slugs to push (default: all 13)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="show what would push, do not actually push",
    )
    parser.add_argument(
        "--sleep", type=float, default=2.0,
        help="seconds to sleep between pushes (default 2)",
    )
    args = parser.parse_args()

    targets = args.slugs or NOTEBOOKS
    unknown = [s for s in targets if s not in NOTEBOOKS]
    if unknown:
        print(f"WARNING: unknown slugs (not in canonical list): {unknown}",
              file=sys.stderr)

    print(f"Pushing v3.16 wheels to {len(targets)} dataset(s)")
    print(f"Order: {targets}")
    print()

    succeeded: list[str] = []
    failed: list[tuple[str, str]] = []
    rate_limited = False

    for i, slug in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {slug}", end=" ", flush=True)
        ok, msg = push_dataset(slug, dry_run=args.dry_run)
        if ok:
            print("OK")
            print(f"    {msg[:140]}")
            succeeded.append(slug)
        else:
            print("FAIL")
            print(f"    {msg[:280]}")
            failed.append((slug, msg))
            if "429" in msg:
                rate_limited = True
                print("    RATE LIMITED — stopping (resume tomorrow)")
                break
        if i < len(targets) and not args.dry_run:
            time.sleep(args.sleep)

    print()
    print("=" * 60)
    print(f"SUCCEEDED ({len(succeeded)}):")
    for s in succeeded:
        print(f"  [ok] {s}")
    if failed:
        print(f"FAILED ({len(failed)}):")
        for s, m in failed:
            print(f"  [FAIL] {s}: {m[:120]}")
    if rate_limited:
        remaining = [s for s in targets if s not in succeeded
                      and s not in [f[0] for f in failed]]
        if remaining:
            print(f"\nNot attempted (rate-limited): {remaining}")
            print(f"Resume with: python {Path(__file__).name} {' '.join(remaining)}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
