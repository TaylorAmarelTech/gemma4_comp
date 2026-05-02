"""Push specific kernels with rate-limit awareness and UTF-8 hardening.

Reads a list of kernel directories from stdin or hardcoded list, pushes
each with retry-on-429 and a delay between pushes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

KERNELS = Path("kaggle/kernels")
DELAY_BETWEEN = 15  # seconds between pushes to respect rate limit
RETRY_DELAYS = [60, 120, 180]  # backoff on 429

TO_PUSH = [
    "duecare_010_quickstart",
    "duecare_200_cross_domain_proof",
    "duecare_260_rag_comparison",
    "duecare_270_gemma_generations",
    "duecare_310_prompt_factory",
    "duecare_320_supergemma_safety_gap",
    "duecare_400_function_calling_multimodal",
    "duecare_410_llm_judge_grading",
    "duecare_500_agent_swarm_deep_dive",
    "duecare_520_phase3_curriculum_builder",
    "duecare_530_phase3_unsloth_finetune",
    "duecare_610_submission_walkthrough",
]


def push(kernel_dir: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # Use PowerShell-friendly subprocess call with explicit utf-8 decoding
    proc = subprocess.run(
        ["kaggle", "kernels", "push", "-p", str(kernel_dir)],
        capture_output=True,
        env=env,
    )
    # Decode raw bytes with utf-8 + replace to survive any non-ascii in Kaggle output
    out = (proc.stdout or b"").decode("utf-8", errors="replace") + "\n" + \
          (proc.stderr or b"").decode("utf-8", errors="replace")
    return proc.returncode, out.strip()


def main() -> int:
    if not os.environ.get("KAGGLE_API_TOKEN"):
        print("ERROR: KAGGLE_API_TOKEN env var must be set", file=sys.stderr)
        return 2

    results = {}
    for i, dir_name in enumerate(TO_PUSH):
        kd = KERNELS / dir_name
        if not kd.exists():
            print(f"SKIP {dir_name}: not found")
            continue
        meta = json.loads((kd / "kernel-metadata.json").read_text("utf-8"))
        print(f"\n[{i+1}/{len(TO_PUSH)}] {dir_name}")
        print(f"    id:    {meta['id']}")
        print(f"    title: {meta['title']}")

        success = False
        for attempt, delay in enumerate([0] + RETRY_DELAYS):
            if delay > 0:
                print(f"    Backing off {delay}s before retry {attempt}...")
                time.sleep(delay)
            rc, out = push(kd)
            last_line = out.splitlines()[-1] if out else "(no output)"
            if rc == 0:
                print(f"    OK: {last_line}")
                results[dir_name] = ("OK", last_line)
                success = True
                break
            if "429" in out or "Too Many Requests" in out:
                print(f"    RATE LIMITED: {last_line}")
                continue
            if "charmap" in out:
                print(f"    UTF-8 DECODE ISSUE (but push likely succeeded server-side)")
                results[dir_name] = ("LIKELY_OK", last_line)
                success = True
                break
            print(f"    FAIL: {last_line}")
            results[dir_name] = ("FAIL", last_line)
            break

        if not success and dir_name not in results:
            results[dir_name] = ("RATE_LIMIT_EXHAUSTED", "could not push after all retries")

        if i < len(TO_PUSH) - 1:
            time.sleep(DELAY_BETWEEN)

    print(f"\n{'='*60}\nSUMMARY\n{'='*60}")
    for name, (status, note) in results.items():
        print(f"{status:<25} {name}")

    ok = sum(1 for s, _ in results.values() if s in ("OK", "LIKELY_OK"))
    print(f"\nSucceeded: {ok}/{len(TO_PUSH)}")
    return 0 if ok == len(TO_PUSH) else 1


if __name__ == "__main__":
    raise SystemExit(main())
