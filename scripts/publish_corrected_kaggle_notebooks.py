# ruff: noqa: E501
"""Publish the three corrected DueCare reproduction notebooks to Kaggle, robustly.

Why this exists: Kaggle's `SaveKernel` endpoint has a per-account DAILY push cap
(resets at 00:00 UTC). When it is hit every `kernels push` returns HTTP 429 and no
amount of retrying helps until the reset. This script makes the publish step:

  * idempotent + re-runnable (safe to run repeatedly; each success is a new version),
  * resilient to the Kaggle CLI 2.2.x temp-path bug (stages each notebook at a SHORT
    path and pre-creates the %TEMP% upload mirror the CLI expects),
  * honest about 429 vs real failure (parses the CLI output, exits non-zero only on a
    genuine error so a scheduler can tell "rate-limited, try later" from "broken"),
  * optionally self-throttling (`--wait-for-reset` sleeps until just after 00:00 UTC).

It pushes the notebooks that were already BUILT + locally executed by
`build_benchmark_results_kaggle.py` and `build_rulecards_kaggle.py`; pass
`--rebuild` to regenerate them from the live panel/deck first.

Run (from the clean venv, because the system Python is OneDrive-corrupted):
    %LOCALAPPDATA%\\gemma4-testenv\\venv\\Scripts\\python.exe scripts/publish_corrected_kaggle_notebooks.py
    ... --wait-for-reset      # block until the daily cap resets, then push
    ... --rebuild             # regenerate the notebooks from source first
    ... --dry-run             # stage + show what would push, but do not call Kaggle
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE_ROOT = Path.home() / "kgpush"  # short path, dodges the CLI temp-path bug

# (build script, its --output dir, [notebook subdirs relative to that output]).
BUILDS = [
    ("build_benchmark_results_kaggle.py",
     ROOT / "reports" / "kaggle_publish" / "benchmark_results_v1",
     ["notebooks/duecare-judge-agreement", "notebooks/duecare-reproduce-harness-lift"]),
    ("build_rulecards_kaggle.py",
     ROOT / "reports" / "kaggle_publish" / "rulecard_supervision_fabric_v1",
     ["notebook"]),
]


def _kaggle_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("KAGGLE_USERNAME", "taylorsamarel")
    return env


def _printable(text: str) -> str:
    return "".join(ch for ch in (text or "") if ch.isprintable() or ch in "\r\n")


def _pre_create_temp_mirror() -> None:
    # Kaggle CLI 2.2.x mirrors the absolute upload path under %TEMP%\.kaggle\uploads;
    # the leading drive letter becomes "C_" and the tree must already exist.
    tmp = Path(os.environ.get("TEMP", os.environ.get("TMP", str(Path.home() / "AppData/Local/Temp"))))
    (tmp / ".kaggle" / "uploads" / "C_" / "Users" / os.environ.get("USERNAME", "amare")).mkdir(parents=True, exist_ok=True)


def _seconds_to_utc_reset() -> float:
    now = datetime.now(timezone.utc)
    reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (reset - now).total_seconds()


def _wait_for_reset(pad_seconds: int = 120) -> None:
    secs = _seconds_to_utc_reset() + pad_seconds
    reset_at = datetime.now(timezone.utc) + timedelta(seconds=secs)
    print(f"[wait] sleeping {secs/60:.1f} min until ~{reset_at:%Y-%m-%d %H:%M} UTC (past the daily reset)...", flush=True)
    time.sleep(max(0, secs))


def _rebuild() -> None:
    for script, _out, _subs in BUILDS:
        print(f"[rebuild] {script} --execute-local --force", flush=True)
        subprocess.run([sys.executable, str(ROOT / "scripts" / script), "--execute-local", "--force"],
                       check=True, cwd=ROOT)


def _stage(notebook_dir: Path) -> tuple[str, Path]:
    meta = json.loads((notebook_dir / "kernel-metadata.json").read_text(encoding="utf-8"))
    slug = meta["id"].split("/", 1)[1]
    code_file = meta.get("code_file", "notebook.ipynb")
    dest = STAGE_ROOT / slug
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(notebook_dir / "kernel-metadata.json", dest / "kernel-metadata.json")
    shutil.copyfile(notebook_dir / code_file, dest / code_file)
    return meta["id"], dest


def _push_one(staged: Path, *, dry_run: bool) -> str:
    """Return one of: 'ok', 'rate_limited', 'dry_run', 'error:<detail>'."""
    if dry_run:
        return "dry_run"
    proc = subprocess.run([sys.executable, "-m", "kaggle", "kernels", "push", "-p", str(staged)],
                          capture_output=True, text=True, cwd=str(staged), env=_kaggle_env())
    out = _printable((proc.stdout or "") + "\n" + (proc.stderr or ""))
    low = out.lower()
    if "429" in out or "too many requests" in low:
        return "rate_limited"
    if "successfully pushed" in low or "your kernel" in low or "kernel version" in low:
        return "ok"
    if proc.returncode == 0 and "error" not in low and "traceback" not in low:
        return "ok"
    detail = " ".join(line.strip() for line in out.splitlines() if line.strip())[-300:]
    return f"error:{detail or 'unknown'}"


def _live_slugs() -> set[str]:
    """Best-effort set of the account's live kernel slugs (part after 'user/')."""
    try:
        proc = subprocess.run([sys.executable, "-m", "kaggle", "kernels", "list", "--user",
                               _kaggle_env()["KAGGLE_USERNAME"], "--page-size", "80"],
                              capture_output=True, text=True, env=_kaggle_env())
    except Exception:  # noqa: BLE001 - verification is best-effort
        return set()
    slugs: set[str] = set()
    for line in _printable(proc.stdout).splitlines():
        parts = line.split()
        if parts and "/" in parts[0]:
            slugs.add(parts[0].split("/", 1)[1])
    return slugs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true", help="regenerate the notebooks from the live panel/deck first")
    ap.add_argument("--wait-for-reset", action="store_true", help="sleep until just after the 00:00 UTC daily reset, then push")
    ap.add_argument("--dry-run", action="store_true", help="stage but do not call Kaggle")
    args = ap.parse_args(argv)

    print(f"[info] {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC | daily reset in {_seconds_to_utc_reset()/3600:.1f} h", flush=True)
    if args.rebuild:
        _rebuild()
    if args.wait_for_reset and not args.dry_run:
        _wait_for_reset()
    _pre_create_temp_mirror()

    targets: list[Path] = []
    for _script, out, subs in BUILDS:
        for sub in subs:
            nb = out / sub
            if (nb / "kernel-metadata.json").is_file():
                targets.append(nb)
            else:
                print(f"[warn] missing built notebook: {nb} (run with --rebuild)", flush=True)

    results: dict[str, str] = {}
    for nb in targets:
        kernel_id, staged = _stage(nb)
        status = _push_one(staged, dry_run=args.dry_run)
        results[kernel_id] = status
        print(f"[push] {kernel_id:45s} -> {status}", flush=True)

    if not args.dry_run and results:
        live = _live_slugs()
        for kernel_id in results:
            slug = kernel_id.split("/", 1)[1]
            mark = "LIVE" if slug in live else "not-yet-listed"
            print(f"[verify] {kernel_id:45s} -> {mark}", flush=True)

    rate_limited = [k for k, v in results.items() if v == "rate_limited"]
    errored = {k: v for k, v in results.items() if v.startswith("error:")}
    print("\n=== summary ===")
    print(json.dumps(results, indent=2))
    if errored:
        print("[FAIL] genuine push errors (not rate-limit).", flush=True)
        return 2
    if rate_limited:
        print(f"[RATE-LIMITED] {len(rate_limited)} notebook(s) hit the daily 429 cap. "
              "Re-run after 00:00 UTC (or use --wait-for-reset).", flush=True)
        return 3
    print("[OK] all targeted notebooks pushed (or dry-run).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
