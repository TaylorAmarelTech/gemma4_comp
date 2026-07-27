#!/usr/bin/env python3
"""Build wheels for every duecare-llm-* package into ./dist/.

Tries `uv build` first (faster, matches the workspace tooling); falls
back to `python -m build` if uv is missing.

Usage:
    python scripts/build_all_wheels.py
    python scripts/build_all_wheels.py --packages duecare-llm-evidence-db,duecare-llm-cli
    python scripts/build_all_wheels.py --clean
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# Build order matters because some packages declare local deps on others
# in their pyproject.toml; we install/build dependencies first.
DEFAULT_BUILD_ORDER = [
    "duecare-llm-core",
    "duecare-llm-benchmark",
    "duecare-llm-chat",
    "duecare-llm-evidence-db",
    "duecare-llm-engine",
    "duecare-llm-kit",
    "duecare-llm-nl2sql",
    "duecare-llm-research-tools",
    "duecare-llm-server",
    "duecare-llm-training",
    "duecare-llm-cli",
    "duecare-llm-models",
    "duecare-llm-domains",
    "duecare-llm-tasks",
    "duecare-llm-agents",
    "duecare-llm-workflows",
    "duecare-llm-publishing",
    "duecare-llm",
]

CRITICAL_WHEEL_CONTENTS = {
    "duecare-llm-domains": [
        "duecare/domains/_data/financial_crime/card.yaml",
        "duecare/domains/_data/tax_evasion/card.yaml",
        "duecare/domains/_data/trafficking/card.yaml",
    ],
}


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(cmd: list[str], cwd: Path) -> bool:
    print(f"  $ {' '.join(cmd)}    (in {cwd.name})")
    proc = subprocess.run(cmd, cwd=cwd)
    return proc.returncode == 0


def build_one(
    pkg_dir: Path,
    dist_dir: Path,
    no_isolation: bool,
    include_sdist: bool,
) -> bool:
    if _have("uv"):
        cmd = ["uv", "build", "--wheel"]
        if include_sdist:
            cmd.append("--sdist")
        cmd.extend(["--out-dir", str(dist_dir.resolve())])
        ok = _run(cmd, cwd=pkg_dir)
        if ok:
            return True
        print("  [warn] uv build failed; falling back to python -m build")
    cmd = [sys.executable, "-m", "build", "--wheel",
           "--outdir", str(dist_dir.resolve())]
    if include_sdist:
        cmd.insert(4, "--sdist")
    if no_isolation:
        cmd.append("--no-isolation")
    return _run(cmd, cwd=pkg_dir)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_receipt(path: Path, *, dist_dir: Path, targets: list[str]) -> None:
    artifacts = []
    for artifact in sorted((*dist_dir.glob("*.whl"), *dist_dir.glob("*.tar.gz"))):
        artifacts.append(
            {
                "name": artifact.name,
                "bytes": artifact.stat().st_size,
                "sha256": _sha256(artifact),
            }
        )
    repo_root = Path(__file__).resolve().parents[1]
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    git_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    payload = {
        "schema": "duecare.python-release-candidate.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "git_sha": git_sha,
        "git_dirty": bool(git_status.strip()),
        "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH", ""),
        "package_directories": targets,
        "package_count": len(targets),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "network_calls": None,
        "network_note": "build isolation may resolve declared build backends",
        "model_calls": 0,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  receipt: {path} ({len(artifacts)} artifacts)")


def _wheel_prefix(package_name: str) -> str:
    return package_name.replace("-", "_") + "-"


def _latest_wheel(dist_dir: Path, package_name: str) -> Path | None:
    matches = list(dist_dir.glob(f"{_wheel_prefix(package_name)}*.whl"))
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def verify_wheel_contents(dist_dir: Path, targets: list[str]) -> list[str]:
    failed: list[str] = []
    for package_name, expected_paths in CRITICAL_WHEEL_CONTENTS.items():
        if package_name not in targets:
            continue
        wheel_path = _latest_wheel(dist_dir, package_name)
        if wheel_path is None:
            print(f"  [verify] {package_name}: wheel not found")
            failed.append(package_name)
            continue
        with zipfile.ZipFile(wheel_path) as archive:
            names = archive.namelist()
        missing = [path for path in expected_paths if path not in names]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if missing or duplicates:
            print(f"  [verify] {wheel_path.name}: FAILED")
            if missing:
                print(f"    missing: {missing}")
            if duplicates:
                print(f"    duplicate entries: {duplicates[:10]}")
            failed.append(package_name)
            continue
        print(f"  [verify] {wheel_path.name}: critical contents OK")
    return failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--packages",
                     help="comma-separated list (default: all)")
    ap.add_argument("--clean", action="store_true",
                     help="delete the selected output directory first")
    ap.add_argument("--dist-dir", default="dist",
                     help="output directory (default: ./dist)")
    ap.add_argument("--no-isolation", action="store_true",
                     help="build using already-installed hatchling "
                     "(workaround for Python 3.14 venv issues)")
    ap.add_argument("--sdist", action="store_true",
                    help="build source distributions alongside wheels")
    ap.add_argument("--receipt",
                    help="write a JSON receipt containing artifact SHA-256 hashes")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    packages_dir = repo_root / "packages"
    dist_dir = (repo_root / args.dist_dir).resolve()

    if not os.environ.get("SOURCE_DATE_EPOCH"):
        commit_epoch = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if commit_epoch.isdigit():
            os.environ["SOURCE_DATE_EPOCH"] = commit_epoch

    if args.clean and dist_dir.exists():
        print(f"  cleaning {dist_dir}")
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    targets = [p.strip() for p in args.packages.split(",")] if args.packages \
              else DEFAULT_BUILD_ORDER
    targets = [t for t in targets if (packages_dir / t).exists()]
    if not targets:
        print("  no packages to build")
        return 1
    print(f"  building {len(targets)} package(s) -> {dist_dir}")

    failed: list[str] = []
    for pkg in targets:
        pkg_dir = packages_dir / pkg
        print(f"\n[{pkg}]")
        if not (pkg_dir / "pyproject.toml").exists():
            print("  [skip] no pyproject.toml")
            continue
        ok = build_one(
            pkg_dir,
            dist_dir,
            no_isolation=args.no_isolation,
            include_sdist=args.sdist,
        )
        if not ok:
            failed.append(pkg)

    print("\n  built wheels:")
    for w in sorted(dist_dir.glob("*.whl")):
        size_kb = w.stat().st_size // 1024
        print(f"    {w.name}  ({size_kb} KB)")

    verify_failed = verify_wheel_contents(dist_dir, targets)

    if failed:
        print(f"\n  FAILED: {failed}")
        return 1
    if verify_failed:
        print(f"\n  FAILED verification: {verify_failed}")
        return 1
    if args.receipt:
        receipt_path = (repo_root / args.receipt).resolve()
        write_receipt(receipt_path, dist_dir=dist_dir, targets=targets)
    print(f"\n  done. {len(list(dist_dir.glob('*.whl')))} wheels in {dist_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
