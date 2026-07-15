"""Fail-closed Kaggle publishing orchestrator.

Wraps the ``kaggle`` CLI for individually approved notebooks, datasets, and
model artifacts. Every mutating command validates its local payload before
checking credentials or touching the network. ``--dry-run`` prints the exact
command but does not bypass payload validation.

Sub-commands
------------
    auth-check         Verify kaggle CLI + credentials are in place.
    push-notebooks     Push every tracked duecare kernel via `kaggle kernels push`.
    status-notebooks   Query kernel status for every pushed notebook.
    publish-dataset          Create/version a non-empty evaluation dataset.
    publish-training-dataset Create/version one verified training release.
    publish-model            Publish a completed, weight-bearing model bundle.
    publish-all              Refuse broad publication; select one surface.

Exit codes are 0 on success, non-zero on any failure so the script
composes well with CI and shell pipelines.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from build_kaggle_training_release import ReleaseError, verify_release_dir
from kaggle_notebook_utils import discover_kernel_notebooks

REPO_ROOT = Path(__file__).resolve().parents[1]
KAGGLE_ROOT = REPO_ROOT / "kaggle"
KERNELS_DIR = KAGGLE_ROOT
SHARED_DATASETS_DIR = KAGGLE_ROOT / "shared-datasets"
MODELS_DIR = KAGGLE_ROOT / "models"

KAGGLE_CONFIG_PATH = Path.home() / ".kaggle" / "kaggle.json"

_PLACEHOLDER = re.compile(r"(?i)(?:INSERT_[A-Z0-9_]+_HERE|\bPLACEHOLDER\b|\bTODO\b)")
_PINNED_REVISION = re.compile(r"^[0-9a-f]{40,64}$")
_WEIGHT_SUFFIXES = frozenset({".safetensors", ".gguf", ".bin", ".pt", ".pth", ".onnx", ".params"})
_WEIGHT_NAME = re.compile(r"(?i)(?:adapter|model|pytorch|weight|consolidated)")
_DATASET_NON_PAYLOAD_NAMES = frozenset(
    {
        "dataset-metadata.json",
        "readme.md",
        "data_card.md",
        "license",
        "license.md",
        "license.txt",
        ".gitkeep",
    }
)


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
                Path.home() / "AppData" / "Local" / "Programs" / "Python" / v / "Scripts" / "kaggle"
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


def _kaggle_cmd(*, dry_run: bool) -> list[str]:
    """Return the Kaggle command for real calls, or a printable stand-in.

    Dry runs should validate DueCare packaging logic without requiring the
    caller's machine or CI runner to have Kaggle installed.
    """
    try:
        return _kaggle_exe()
    except FileNotFoundError:
        if dry_run:
            return ["kaggle"]
        raise


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
        return run([*_kaggle_cmd(dry_run=True), "--version"], dry_run=True).returncode
    version = run([*_kaggle_cmd(dry_run=False), "--version"], dry_run=False)
    if not version.ok:
        return version.returncode
    cfg = run([*_kaggle_cmd(dry_run=False), "config", "view"], dry_run=False)
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
    required = {"id", "title", "code_file", "kernel_type", "language", "is_private"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"{meta}: missing required fields {missing}")
    code_file = d / data["code_file"]
    if not code_file.exists():
        raise FileNotFoundError(f"code_file {code_file} referenced by {meta} is missing")
    keywords = data.get("keywords", [])
    if not isinstance(keywords, list):
        raise ValueError(f"{meta}: keywords must be a list when present")
    if data.get("is_private") is not False:
        raise ValueError(f"{meta}: is_private must be false before publishing")


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
    entries = discover_kernel_notebooks(KERNELS_DIR, include_optional=True)
    if notebook_ids is not None:
        selected = []
        for entry in entries:
            parts = entry.dir_name.split("-")
            aliases = {
                entry.notebook_number,
                entry.dir_name,
                entry.kernel_id,
                entry.kernel_id.split("/", 1)[-1],
            }
            if parts and parts[0].isdigit():
                aliases.add(parts[0])
            if len(parts) >= 2 and parts[0] == "A":
                aliases.add("-".join(parts[:2]))
            if aliases & notebook_ids:
                selected.append(entry)
        entries = selected
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
        result = run(
            [*_kaggle_cmd(dry_run=dry_run), "kernels", "push", "-p", str(d)],
            dry_run=dry_run,
        )
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
        result = run(
            [*_kaggle_cmd(dry_run=dry_run), "kernels", "status", kernel_id],
            dry_run=dry_run,
        )
        if not result.ok:
            failures += 1
    return 0 if failures == 0 else 1


# --------------------------- datasets --------------------------


def _read_json_object(path: Path, *, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not readable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return value


def _validate_dataset_payload(target: Path) -> dict:
    """Reject missing, placeholder-only, symlinked, or empty dataset bundles."""
    if not target.exists() or not target.is_dir():
        raise ValueError(f"dataset dir not found: {target}")
    if target.is_symlink():
        raise ValueError(f"dataset dir must not be a symlink: {target}")
    meta_path = target / "dataset-metadata.json"
    if not meta_path.is_file() or meta_path.is_symlink():
        raise ValueError(f"dataset-metadata.json missing or symlinked in {target}")
    metadata = _read_json_object(meta_path, label="dataset metadata")
    for field in ("id", "title", "licenses"):
        if not metadata.get(field):
            raise ValueError(f"dataset metadata is missing {field!r}: {meta_path}")
    if not isinstance(metadata["licenses"], list):
        raise ValueError(f"dataset metadata licenses must be a list: {meta_path}")
    if _PLACEHOLDER.search(json.dumps(metadata, ensure_ascii=False)):
        raise ValueError(f"dataset metadata still contains a placeholder: {meta_path}")

    payloads: list[Path] = []
    for path in target.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"dataset payload must not contain symlinks: {path}")
        if not path.is_file():
            continue
        if path.name.lower() in _DATASET_NON_PAYLOAD_NAMES:
            continue
        if _PLACEHOLDER.search(path.name):
            raise ValueError(f"dataset payload still has a placeholder name: {path}")
        if path.stat().st_size <= 0:
            raise ValueError(f"dataset payload file is empty: {path}")
        payloads.append(path)
    if not payloads:
        raise ValueError(f"dataset has zero payload files: {target}")
    return {"metadata": metadata, "payload_files": payloads}


def _validate_version_note(version_note: str | None) -> str:
    if not isinstance(version_note, str) or not version_note.strip():
        raise ValueError("--version-note is required for a dataset version")
    if "\x00" in version_note or "\r" in version_note or "\n" in version_note:
        raise ValueError("--version-note must be one exact, single-line value")
    return version_note


def _publish_dataset_directory(
    target: Path,
    *,
    dry_run: bool,
    operation: str,
    version_note: str | None,
    public: bool,
) -> int:
    """Run one deterministic Kaggle dataset operation with no fallback."""
    if operation == "create":
        if version_note is not None:
            print(
                "  ! Kaggle dataset creation has no version-note argument; "
                "omit --version-note and use it on later versions",
                file=sys.stderr,
            )
            return 2
        cmd = [*_kaggle_cmd(dry_run=dry_run), "datasets", "create", "-p", str(target)]
        if public:
            cmd.append("--public")
        print(f"  visibility: {'public' if public else 'private'}")
    elif operation == "version":
        if public:
            print(
                "  ! --public is only valid for dataset creation; a version keeps "
                "the existing dataset visibility",
                file=sys.stderr,
            )
            return 2
        try:
            note = _validate_version_note(version_note)
        except ValueError as exc:
            print(f"  ! {exc}", file=sys.stderr)
            return 2
        cmd = [
            *_kaggle_cmd(dry_run=dry_run),
            "datasets",
            "version",
            "-p",
            str(target),
            "-m",
            note,
        ]
        print("  visibility: unchanged")
    else:
        print(f"  ! unsupported dataset operation: {operation}", file=sys.stderr)
        return 2
    result = run(cmd, dry_run=dry_run)
    return 0 if result.ok else result.returncode


def publish_dataset(
    *,
    dry_run: bool,
    operation: str,
    version_note: str | None = None,
    public: bool = False,
    dataset_dir: Path | None = None,
    auth_checked: bool = False,
) -> int:
    """Create or version one non-empty evaluation dataset."""
    print("# publish-dataset")
    target = (dataset_dir or (SHARED_DATASETS_DIR / "eval-results")).resolve()
    try:
        report = _validate_dataset_payload(target)
    except (OSError, ValueError) as exc:
        print(f"  ! validation failed: {exc}", file=sys.stderr)
        return 2
    print(f"  validated payload files: {len(report['payload_files'])}")
    rc = _require_auth(dry_run=dry_run, auth_checked=auth_checked)
    if rc != 0:
        return rc
    return _publish_dataset_directory(
        target,
        dry_run=dry_run,
        operation=operation,
        version_note=version_note,
        public=public,
    )


def publish_training_dataset(
    *,
    release_dir: Path,
    dry_run: bool,
    operation: str,
    version_note: str | None = None,
    public: bool = False,
    auth_checked: bool = False,
) -> int:
    """Publish only a directory accepted by the canonical training verifier."""
    print("# publish-training-dataset")
    try:
        target = release_dir.resolve(strict=True)
        report = verify_release_dir(target)
        payload = _validate_dataset_payload(target)
    except (OSError, ReleaseError, ValueError) as exc:
        print(f"  ! verified training release required: {exc}", file=sys.stderr)
        return 2
    print(
        f"  verified release: {report.get('release_id')} "
        f"({len(payload['payload_files'])} payload files)"
    )
    rc = _require_auth(dry_run=dry_run, auth_checked=auth_checked)
    if rc != 0:
        return rc
    return _publish_dataset_directory(
        target,
        dry_run=dry_run,
        operation=operation,
        version_note=version_note,
        public=public,
    )


# --------------------------- models ----------------------------


def _validate_model_payload(target: Path) -> dict:
    """Require uploadable weights plus Kaggle and DueCare completion metadata."""
    if not target.exists() or not target.is_dir():
        raise ValueError(f"model dir not found: {target}")
    if target.is_symlink():
        raise ValueError(f"model dir must not be a symlink: {target}")

    required_json = {
        "model metadata": target / "model-metadata.json",
        "model-instance metadata": target / "model-instance-metadata.json",
        "training completion manifest": target / "training_completion_manifest.json",
    }
    parsed: dict[str, dict] = {}
    for label, path in required_json.items():
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"{path.name} is required and must not be a symlink")
        value = _read_json_object(path, label=label)
        if not value or _PLACEHOLDER.search(json.dumps(value, ensure_ascii=False)):
            raise ValueError(f"{path.name} is empty or contains a placeholder")
        parsed[label] = value

    model_meta = parsed["model metadata"]
    for field in ("ownerSlug", "title", "slug", "description"):
        if not model_meta.get(field):
            raise ValueError(f"model-metadata.json is missing {field!r}")

    instance_meta = parsed["model-instance metadata"]
    instance_fields = {
        "owner": ("owner_slug", "ownerSlug"),
        "model": ("model_slug", "modelSlug"),
        "instance": ("instance_slug", "instanceSlug"),
        "framework": ("framework",),
    }
    for label, aliases in instance_fields.items():
        if not any(instance_meta.get(alias) for alias in aliases):
            raise ValueError(f"model-instance-metadata.json is missing {label!r}")

    completion = parsed["training completion manifest"]
    if completion.get("schema_version") != "1.0":
        raise ValueError("training completion manifest schema_version must be 1.0")
    if completion.get("handoff_kind") != "duecare.training.completion.v1":
        raise ValueError("training completion manifest handoff_kind is invalid")
    if not completion.get("base_model") or not completion.get("completed_at"):
        raise ValueError("training completion manifest lacks base_model or completed_at")
    stages = completion.get("executed_stages")
    if not isinstance(stages, list) or not stages or not {"sft", "dpo"}.intersection(stages):
        raise ValueError("training completion manifest has no executed SFT/DPO stage")
    revision = str(completion.get("base_model_revision") or "")
    if not _PINNED_REVISION.fullmatch(revision):
        raise ValueError("training completion manifest base_model_revision is not immutable")

    weight_files: list[Path] = []
    for path in target.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"model payload must not contain symlinks: {path}")
        if (
            path.is_file()
            and path.suffix.lower() in _WEIGHT_SUFFIXES
            and _WEIGHT_NAME.search(path.name)
        ):
            if path.stat().st_size < 1024:
                raise ValueError(f"model weight artifact is too small to be credible: {path}")
            weight_files.append(path)
    if not weight_files:
        raise ValueError("model payload has no real weight artifacts")
    return {
        "model_metadata": model_meta,
        "instance_metadata": instance_meta,
        "completion": completion,
        "weight_files": weight_files,
    }


def publish_model(
    *, dry_run: bool, model_dir: Path | None = None, auth_checked: bool = False
) -> int:
    print("# publish-model")
    target = (model_dir or (MODELS_DIR / "duecare_safety_harness")).resolve()
    try:
        report = _validate_model_payload(target)
    except (OSError, ValueError) as exc:
        print(f"  ! validation failed: {exc}", file=sys.stderr)
        return 2
    print(f"  validated weight artifacts: {len(report['weight_files'])}")
    rc = _require_auth(dry_run=dry_run, auth_checked=auth_checked)
    if rc != 0:
        return rc

    # First attempt: create the model.  If it already exists, create an instance version.
    create = run(
        [*_kaggle_cmd(dry_run=dry_run), "models", "create", "-p", str(target)],
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
        [
            *_kaggle_cmd(dry_run=dry_run),
            "models",
            "instances",
            "create",
            "-p",
            str(target),
        ],
        dry_run=dry_run,
    )
    if inst.ok:
        return 0

    version = run(
        [
            *_kaggle_cmd(dry_run=dry_run),
            "models",
            "instances",
            "versions",
            "create",
            "-p",
            str(target),
            "-n",
            "refresh",
        ],
        dry_run=dry_run,
    )
    return 0 if version.ok else version.returncode


# --------------------------- publish-all -----------------------


def publish_all(*, dry_run: bool) -> int:
    print("# publish-all")
    print(
        "  ! disabled: broad publication cannot prove that every notebook, "
        "dataset, and model is independently release-ready. Use one explicit "
        "sub-command and target at a time.",
        file=sys.stderr,
    )
    return 2


# --------------------------- CLI -------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dry-run", action="store_true", help="print commands but do not execute")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("auth-check")
    push_parser = sub.add_parser("push-notebooks")
    push_parser.add_argument(
        "--ids", nargs="*", help="Notebook ids, kernel dir names, or full kernel ids to push"
    )
    push_parser.add_argument(
        "--limit", type=int, help="Push only the first N tracked kernels after filtering"
    )
    status_parser = sub.add_parser("status-notebooks")
    status_parser.add_argument(
        "--ids", nargs="*", help="Notebook ids, kernel dir names, or full kernel ids to query"
    )
    status_parser.add_argument(
        "--limit", type=int, help="Check only the first N tracked kernels after filtering"
    )
    dataset_parser = sub.add_parser("publish-dataset")
    dataset_parser.add_argument(
        "--dataset-dir", type=Path, help="dataset directory (defaults to eval-results)"
    )
    dataset_parser.add_argument("--operation", choices=("create", "version"), required=True)
    dataset_parser.add_argument(
        "--version-note", help="exact, single-line note required for --operation version"
    )
    dataset_parser.add_argument(
        "--public",
        action="store_true",
        help="make a newly created dataset public; create is private by default",
    )
    training_parser = sub.add_parser("publish-training-dataset")
    training_parser.add_argument("--release-dir", type=Path, required=True)
    training_parser.add_argument("--operation", choices=("create", "version"), required=True)
    training_parser.add_argument(
        "--version-note", help="exact, single-line note required for --operation version"
    )
    training_parser.add_argument(
        "--public",
        action="store_true",
        help="make a newly created verified release public; create is private by default",
    )
    model_parser = sub.add_parser("publish-model")
    model_parser.add_argument("--model-dir", type=Path, help="completed model-bundle directory")
    sub.add_parser("publish-all")

    args = parser.parse_args(argv)
    notebook_ids = _normalize_notebook_ids(getattr(args, "ids", None))
    limit = getattr(args, "limit", None)
    dispatch = {
        "auth-check": lambda: auth_check(dry_run=args.dry_run),
        "push-notebooks": lambda: push_notebooks(
            dry_run=args.dry_run, notebook_ids=notebook_ids, limit=limit
        ),
        "status-notebooks": lambda: status_notebooks(
            dry_run=args.dry_run, notebook_ids=notebook_ids, limit=limit
        ),
        "publish-dataset": lambda: publish_dataset(
            dry_run=args.dry_run,
            operation=args.operation,
            version_note=args.version_note,
            public=args.public,
            dataset_dir=args.dataset_dir,
        ),
        "publish-training-dataset": lambda: publish_training_dataset(
            release_dir=args.release_dir,
            dry_run=args.dry_run,
            operation=args.operation,
            version_note=args.version_note,
            public=args.public,
        ),
        "publish-model": lambda: publish_model(dry_run=args.dry_run, model_dir=args.model_dir),
        "publish-all": lambda: publish_all(dry_run=args.dry_run),
    }
    return dispatch[args.cmd]()


if __name__ == "__main__":
    sys.exit(main())
