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
import shutil
import subprocess
import sys
from pathlib import Path


# Build order matters because some packages declare local deps on others
# in their pyproject.toml; we install/build dependencies first.
DEFAULT_BUILD_ORDER = [
    "duecare-llm-core",
    "duecare-llm-evidence-db",
    "duecare-llm-engine",
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


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(cmd: list[str], cwd: Path) -> bool:
    print(f"  $ {' '.join(cmd)}    (in {cwd.name})")
    proc = subprocess.run(cmd, cwd=cwd)
    return proc.returncode == 0


def build_one(pkg_dir: Path, dist_dir: Path,
                 no_isolation: bool) -> bool:
    if _have("uv"):
        ok = _run(["uv", "build", "--wheel",
                   "--out-dir", str(dist_dir.resolve())], cwd=pkg_dir)
        if ok:
            return True
        print("  [warn] uv build failed; falling back to python -m build")
    cmd = [sys.executable, "-m", "build", "--wheel",
            "--outdir", str(dist_dir.resolve())]
    if no_isolation:
        cmd.append("--no-isolation")
    return _run(cmd, cwd=pkg_dir)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--packages",
                     help="comma-separated list (default: all)")
    ap.add_argument("--clean", action="store_true",
                     help="delete dist/ and per-package dist/ first")
    ap.add_argument("--dist-dir", default="dist",
                     help="output directory (default: ./dist)")
    ap.add_argument("--no-isolation", action="store_true",
                     help="build using already-installed hatchling "
                          "(workaround for Python 3.14 venv issues)")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    packages_dir = repo_root / "packages"
    dist_dir = (repo_root / args.dist_dir).resolve()

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
            print(f"  [skip] no pyproject.toml")
            continue
        ok = build_one(pkg_dir, dist_dir, no_isolation=args.no_isolation)
        if not ok:
            failed.append(pkg)

    print("\n  built wheels:")
    for w in sorted(dist_dir.glob("*.whl")):
        size_kb = w.stat().st_size // 1024
        print(f"    {w.name}  ({size_kb} KB)")

    if failed:
        print(f"\n  FAILED: {failed}")
        return 1
    print(f"\n  done. {len(list(dist_dir.glob('*.whl')))} wheels in {dist_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
