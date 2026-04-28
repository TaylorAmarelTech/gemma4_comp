"""Kaggle publishing orchestrator.

Wraps the `kaggle` CLI so the whole submission surface — notebooks, eval
datasets, and fine-tuned model artefacts — can be shipped with a single
command.  Every sub-command is safe to run in --dry-run mode, which
prints the commands that *would* be executed without touching the
network.

Sub-commands
------------
    auth-check         Verify kaggle CLI + credentials are in place.
    push-notebooks     Push every tracked duecare kernel via `kaggle kernels push`.
    status-notebooks   Query kernel status for every pushed notebook.
    publish-dataset    Create/version the `duecare-eval-results` dataset.
    publish-model      Create/version the `duecare-safety-harness` model.
    publish-all        Full submission: notebooks + dataset + model.

Exit codes are 0 on success, non-zero on any failure so the script
composes well with CI and shell pipelines.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from kaggle_notebook_utils import discover_kernel_notebooks

REPO_ROOT = Path(__file__).resolve().parents[1]
KAGGLE_ROOT = REPO_ROOT / "kaggle"
KERNELS_DIR = KAGGLE_ROOT / "kernels"
SHARED_DATASETS_DIR = KAGGLE_ROOT / "shared-datasets"
MODELS_DIR = KAGGLE_ROOT / "models"

KAGGLE_CONFIG_PATH = Path.home() / ".kaggle" / "kaggle.json"


# --------------------------- helpers ---------------------------


@dataclass
class RunResult:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _fmt_cmd(cmd: Iterable[str]) -> str:
    return " ".join(shlex.quote(str(c)) for c in cmd)


def run(cmd: list[str], *, dry_run: bool, cwd: Path | None = None) -> RunResult:
    """Run a shell command, or print it in dry-run mode."""
    print(f"$ {_fmt_cmd(cmd)}", flush=True)
    if dry_run:
        return RunResult(cmd=cmd, returncode=0, stdout="(dry-run)", stderr="")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.stdout:
        print(proc.stdout, end="", flush=True)
    if proc.stderr:
        print(proc.stderr, end="", flush=True, file=sys.stderr)
    return RunResult(
        cmd=cmd,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def _kaggle_exe() -> list[str]:
    """Locate the kaggle CLI script.

    The kaggle package (>=2.0) does NOT expose a `__main__`, so
    `python -m kaggle` fails.  Use `shutil.which("kaggle")`, fall back
    to common Windows / POSIX install locations, and as a last resort
    let the operator override via the `DUECARE_KAGGLE_BIN` env var.
    """
    import shutil

    override = os.environ.get("DUECARE_KAGGLE_BIN")
    if override and Path(override).exists():
        return [override]

    found = shutil.which("kaggle")
    if found:
        return [found]

    candidates: list[Path] = []
    if sys.platform == "win32":
        for v in ("Python312", "Python311", "Python313", "Python314"):
            candidates.append(
                Path.home()
                / "AppData"
                / "Local"
                / "Programs"
                / "Python"
                / v
                / "Scripts"
                / "kaggle.exe"
            )
            candidates.append(
                Path.home()
                / "AppData"
                / "Local"
                / "Programs"
                / "Python"
                / v
                / "Scripts"
                / "kaggle"
            )
    else:
        candidates.extend(
            [
                Path("/usr/local/bin/kaggle"),
                Path("/usr/bin/kaggle"),
                Path.home() / ".local" / "bin" / "kaggle",
            ]
        )

    for c in candidates:
        if c.exists():
            return [str(c)]

    raise FileNotFoundError(
        "kaggle CLI not found.  Install with `pip install kaggle` or set "
        "DUECARE_KAGGLE_BIN to the absolute path of the kaggle script."
    )


# --------------------------- auth ------------------------------


def auth_check(*, dry_run: bool) -> int:
    """Verify kaggle CLI is importable and credentials exist.

    Accepts any of the three credential forms the Kaggle CLI supports:

      1. ``~/.kaggle/kaggle.json``  (legacy username/key file)
      2. ``KAGGLE_USERNAME`` + ``KAGGLE_KEY``  (legacy env vars)
      3. ``KAGGLE_API_TOKEN=KGAT_...``  (new bearer token, kaggle >= 2.0)
    """
    print("# auth-check")
    json_present = KAGGLE_CONFIG_PATH.exists()
    env_user = os.environ.get("KAGGLE_USERNAME")
    env_key = os.environ.get("KAGGLE_KEY")
    env_token = os.environ.get("KAGGLE_API_TOKEN")
    print(f"  ~/.kaggle/kaggle.json exists: {json_present}")
    print(f"  KAGGLE_USERNAME set:         {bool(env_user)}")
    print(f"  KAGGLE_KEY set:              {bool(env_key)}")
    print(f"  KAGGLE_API_TOKEN set:        {bool(env_token)}")

    has_creds = json_present or (env_user and env_key) or bool(env_token)
    if not has_creds:
        print(
            "  ! No credentials found.\n"
            "    Provide one of:\n"
            "      - ~/.kaggle/kaggle.json\n"
            "      - KAGGLE_USERNAME + KAGGLE_KEY env vars\n"
            "      - KAGGLE_API_TOKEN=KGAT_... env var",
            file=sys.stderr,
        )
        if not dry_run:
            return 2

    # Probe the live API.  `kaggle config view` confirms the token can
    # actually authenticate (which `--version` does not).
    if dry_run:
        return run(_kaggle_exe() + ["--version"], dry_run=True).returncode
    version = run(_kaggle_exe() + ["--version"], dry_run=False)
    if not version.ok:
        return version.returncode
    cfg = run(_kaggle_exe() + ["config", "view"], dry_run=False)
    return 0 if cfg.ok else cfg.returncode


def _require_auth(*, dry_run: bool, auth_checked: bool = False) -> int:
    """Fail fast for non-dry-run Kaggle operations when auth is unavailable."""
    if dry_run or auth_checked:
        return 0
    return auth_check(dry_run=False)


# --------------------------- notebooks -------------------------


def _validate_notebook_dir(d: Path) -> None:
    if not d.exists():
        raise FileNotFoundError(f"notebook dir missing: {d}")
    meta = d / "kernel-metadata.json"
    if not meta.exists():
        raise FileNotFoundError(f"kernel-metadata.json missing in {d}")
    # validate metadata fields
    data = json.loads(meta.read_text())
    required = {"id", "title", "code_file", "kernel_type", "language", "keywords", "competition_sources", "is_private"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"{meta}: missing required fields {missing}")
    code_file = d / data["code_file"]
    if not code_file.exists():
        raise FileNotFoundError(f"code_file {code_file} referenced by {meta} is missing")
    keywords = data.get("keywords")
    if not isinstance(keywords, list) or not keywords:
        raise ValueError(f"{meta}: keywords must be a non-empty list")
    if data.get("is_private") is not False:
        raise ValueError(f"{meta}: is_private must be false before publishing")
    competition_sources = data.get("competition_sources")
    if "gemma-4-good-hackathon" not in competition_sources:
        raise ValueError(f"{meta}: competition_sources must include gemma-4-good-hackathon")


def _normalize_notebook_ids(raw_ids: list[str] | None) -> set[str] | None:
    if not raw_ids:
        return None
    normalized: set[str] = set()
    for raw in raw_ids:
        for item in raw.split(","):
            stripped = item.strip()
            if stripped:
                normalized.add(stripped)
    return normalized or None


def _selected_notebooks(*, notebook_ids: set[str] | None = None, limit: int | None = None):
    entries = discover_kernel_notebooks(KERNELS_DIR)
    if notebook_ids is not None:
        entries = [
            entry
            for entry in entries
            if entry.notebook_number in notebook_ids
            or entry.dir_name in notebook_ids
            or entry.kernel_id in notebook_ids
        ]
    if limit is not None:
        entries = entries[:limit]
    return entries


def _notebook_dirs(*, notebook_ids: set[str] | None = None, limit: int | None = None) -> list[Path]:
    return [entry.dir_path for entry in _selected_notebooks(notebook_ids=notebook_ids, limit=limit)]


def push_notebooks(
    *,
    dry_run: bool,
    notebook_ids: set[str] | None = None,
    limit: int | None = None,
    auth_checked: bool = False,
) -> int:
    rc = _require_auth(dry_run=dry_run, auth_checked=auth_checked)
    if rc != 0:
        return rc
    notebook_dirs = _notebook_dirs(notebook_ids=notebook_ids, limit=limit)
    print(f"# push-notebooks ({len(notebook_dirs)} kernels)")
    failures = 0
    for d in notebook_dirs:
        try:
            _validate_notebook_dir(d)
        except Exception as e:
            print(f"  ! validation failed for {d.name}: {e}", file=sys.stderr)
            failures += 1
            continue
        result = run(_kaggle_exe() + ["kernels", "push", "-p", str(d)], dry_run=dry_run)
        if not result.ok:
            failures += 1
    return 0 if failures == 0 else 1


def status_notebooks(
    *,
    dry_run: bool,
    notebook_ids: set[str] | None = None,
    limit: int | None = None,
    auth_checked: bool = False,
) -> int:
    rc = _require_auth(dry_run=dry_run, auth_checked=auth_checked)
    if rc != 0:
        return rc
    print("# status-notebooks")
    failures = 0
    for d in _notebook_dirs(notebook_ids=notebook_ids, limit=limit):
        meta_path = d / "kernel-metadata.json"
        if not meta_path.exists():
            print(f"  ! skipping {d.name}: no kernel-metadata.json")
            failures += 1
            continue
        kernel_id = json.loads(meta_path.read_text())["id"]
        result = run(_kaggle_exe() + ["kernels", "status", kernel_id], dry_run=dry_run)
        if not result.ok:
            failures += 1
    return 0 if failures == 0 else 1


# --------------------------- datasets --------------------------


def publish_dataset(*, dry_run: bool, dataset_dir: Path | None = None, auth_checked: bool = False) -> int:
    """Create or version the duecare-eval-results dataset."""
    rc = _require_auth(dry_run=dry_run, auth_checked=auth_checked)
    if rc != 0:
        return rc
    print("# publish-dataset")
    target = dataset_dir or (SHARED_DATASETS_DIR / "eval-results")
    if not target.exists():
        print(f"  ! dataset dir not found: {target}", file=sys.stderr)
        return 2
    meta = target / "dataset-metadata.json"
    if not meta.exists():
        print(f"  ! dataset-metadata.json missing in {target}", file=sys.stderr)
        return 2

    # Probe whether the dataset already exists: if it does, use version; else create.
    # In dry-run mode we can't probe, so we emit both candidates so the operator
    # can see what *would* happen.
    version_note = f"duecare eval results refresh"
    if dry_run:
        print("  (dry-run) would run one of the following:")
        run(
            _kaggle_exe() + ["datasets", "create", "-p", str(target)],
            dry_run=True,
        )
        run(
            _kaggle_exe() + ["datasets", "version", "-p", str(target), "-m", version_note],
            dry_run=True,
        )
        return 0

    # Try version first (more common path once the dataset exists).
    versioned = run(
        _kaggle_exe() + ["datasets", "version", "-p", str(target), "-m", version_note],
        dry_run=False,
    )
    if versioned.ok:
        return 0
    # Fallback: create for first time.
    created = run(
        _kaggle_exe() + ["datasets", "create", "-p", str(target)],
        dry_run=False,
    )
    return 0 if created.ok else created.returncode


# --------------------------- models ----------------------------


def publish_model(*, dry_run: bool, model_dir: Path | None = None, auth_checked: bool = False) -> int:
    rc = _require_auth(dry_run=dry_run, auth_checked=auth_checked)
    if rc != 0:
        return rc
    print("# publish-model")
    target = model_dir or (MODELS_DIR / "duecare_safety_harness")
    if not target.exists():
        print(f"  ! model dir not found: {target}", file=sys.stderr)
        return 2
    meta = target / "model-metadata.json"
    if not meta.exists():
        print(f"  ! model-metadata.json missing in {target}", file=sys.stderr)
        return 2

    # First attempt: create the model.  If it already exists, create an instance version.
    create = run(
        _kaggle_exe() + ["models", "create", "-p", str(target)],
        dry_run=dry_run,
    )
    if create.ok:
        return 0

    instance_meta = target / "model-instance-metadata.json"
    if not instance_meta.exists():
        print(
            "  ! model already existed but no model-instance-metadata.json "
            "found — skipping instance version",
            file=sys.stderr,
        )
        return create.returncode

    inst = run(
        _kaggle_exe() + ["models", "instances", "create", "-p", str(target)],
        dry_run=dry_run,
    )
    if inst.ok:
        return 0

    version = run(
        _kaggle_exe() + ["models", "instances", "versions", "create", "-p", str(target), "-n", "refresh"],
        dry_run=dry_run,
    )
    return 0 if version.ok else version.returncode


# --------------------------- publish-all -----------------------


def publish_all(*, dry_run: bool) -> int:
    print("# publish-all")
    rc = auth_check(dry_run=dry_run)
    if rc != 0:
        return rc
    rc = push_notebooks(dry_run=dry_run, auth_checked=True)
    if rc != 0:
        print("  ! push-notebooks failed, aborting publish-all", file=sys.stderr)
        return rc
    rc = publish_dataset(dry_run=dry_run, auth_checked=True)
    if rc != 0:
        print("  ! publish-dataset failed, aborting publish-all", file=sys.stderr)
        return rc
    rc = publish_model(dry_run=dry_run, auth_checked=True)
    return rc


# --------------------------- CLI -------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print commands but do not execute")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("auth-check")
    push_parser = sub.add_parser("push-notebooks")
    push_parser.add_argument("--ids", nargs="*", help="Notebook ids, kernel dir names, or full kernel ids to push")
    push_parser.add_argument("--limit", type=int, help="Push only the first N tracked kernels after filtering")
    status_parser = sub.add_parser("status-notebooks")
    status_parser.add_argument("--ids", nargs="*", help="Notebook ids, kernel dir names, or full kernel ids to query")
    status_parser.add_argument("--limit", type=int, help="Check only the first N tracked kernels after filtering")
    sub.add_parser("publish-dataset")
    sub.add_parser("publish-model")
    sub.add_parser("publish-all")

    args = parser.parse_args(argv)
    notebook_ids = _normalize_notebook_ids(getattr(args, "ids", None))
    limit = getattr(args, "limit", None)
    dispatch = {
        "auth-check": lambda: auth_check(dry_run=args.dry_run),
        "push-notebooks": lambda: push_notebooks(dry_run=args.dry_run, notebook_ids=notebook_ids, limit=limit),
        "status-notebooks": lambda: status_notebooks(dry_run=args.dry_run, notebook_ids=notebook_ids, limit=limit),
        "publish-dataset": lambda: publish_dataset(dry_run=args.dry_run),
        "publish-model": lambda: publish_model(dry_run=args.dry_run),
        "publish-all": lambda: publish_all(dry_run=args.dry_run),
    }
    return dispatch[args.cmd]()


if __name__ == "__main__":
    sys.exit(main())
