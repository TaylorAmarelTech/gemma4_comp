"""Push all 29 kernels sequentially with rate-limit awareness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

KERNELS = Path("kaggle/kernels")
DELAY_BETWEEN = 20  # seconds
RATE_LIMIT_BACKOFF = 90  # seconds


def push(kernel_dir: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        ["kaggle", "kernels", "push", "-p", str(kernel_dir)],
        capture_output=True,
        env=env,
    )
    out = (proc.stdout or b"").decode("utf-8", errors="replace") + "\n" + \
          (proc.stderr or b"").decode("utf-8", errors="replace")
    return proc.returncode, out.strip()


def main() -> int:
    if not os.environ.get("KAGGLE_API_TOKEN"):
        print("ERROR: KAGGLE_API_TOKEN env var must be set", file=sys.stderr)
        return 2

    dirs = sorted(d for d in KERNELS.iterdir() if d.is_dir())
    results = []

    for i, kd in enumerate(dirs):
        meta = json.loads((kd / "kernel-metadata.json").read_text("utf-8"))
        print(f"\n[{i+1}/{len(dirs)}] {kd.name}")
        print(f"    id:    {meta['id']}")
        print(f"    title: {meta['title']}")

        attempt = 0
        while attempt < 3:
            rc, out = push(kd)
            last = (out.splitlines()[-1] if out else "(no output)")[:200]
            if "429" in out or "Too Many Requests" in out:
                attempt += 1
                print(f"    rate limited, backing off {RATE_LIMIT_BACKOFF}s (attempt {attempt}/3)")
                time.sleep(RATE_LIMIT_BACKOFF)
                continue
            if "Notebook not found" in out:
                print(f"    RESULT: notebook-not-found (new kernel creation path)")
                results.append((kd.name, "NEW_CREATE_ISSUE", last))
            elif rc == 0:
                print(f"    RESULT: {last}")
                results.append((kd.name, "OK", last))
            else:
                print(f"    RESULT FAIL: {last}")
                results.append((kd.name, "FAIL", last))
            break
        else:
            results.append((kd.name, "RATE_EXHAUSTED", "could not push after 3 backoffs"))

        if i < len(dirs) - 1:
            time.sleep(DELAY_BETWEEN)

    print(f"\n{'='*60}\nSUMMARY\n{'='*60}")
    counts = {}
    for name, status, note in results:
        counts[status] = counts.get(status, 0) + 1
        print(f"{status:<25} {name}")
    print()
    for status, n in sorted(counts.items()):
        print(f"  {status}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
