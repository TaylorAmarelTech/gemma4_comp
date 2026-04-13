#!/usr/bin/env python3
"""
copy_framework.py - Selectively copy llm-safety-framework-public into _reference/framework/.

Selective over the full 5.1 GB source: only copies source code, tests, scripts,
docs, and configs. Skips generated data, checkpoints, exports, reports,
archives, venvs, and Python caches.

Non-destructive: does not touch the source folder.
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

SOURCE = Path(
    r"C:\Users\amare\OneDrive\Documents\Migrant_Worker_LLM_Test_Benchmark_Trafficking_Bondage_Etc"
    r"\llm-safety-framework-public"
)
DEST = Path(r"C:\Users\amare\OneDrive\Documents\gemma4_comp\_reference\framework")

# Top-level items to copy. Everything not in this list is skipped.
# Directories and files are both allowed here.
INCLUDE: list[str] = [
    "src",             # all source code (filtered at the file level via NESTED_EXCLUDE)
    "tests",           # pytest + Playwright e2e
    "scripts",         # 18 orchestration scripts
    "docs",            # markdown docs
    "config",          # YAML configs
    "templates",       # template data (small)
    "pyproject.toml",
    "Makefile",
    "requirements.txt",
    ".env.template",
    ".env.example",
    "docker-compose.yml",
    "Dockerfile",
    ".dockerignore",
    "README.md",
    "SETUP.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "LICENSE",
    ".pre-commit-config.yaml",
]

# Top-level items to exclude regardless (some overlap with INCLUDE not being set).
# Used to document intent and belt-and-suspenders against accidental inclusion.
TOP_LEVEL_EXCLUDE = {
    ".git",
    ".venv",
    ".venv310",
    "venv",
    "env",
    "data",        # generated fixtures, pipeline state - skip
    "exports",     # generated
    "reports",     # generated
    "checkpoints", # generated
    "_archive",    # legacy monolith
    "models",      # weights, too large
    "logs",
    "nul",
}

# Items to skip at any depth inside copied directories.
NESTED_EXCLUDE = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "nul",
    ".venv",
    ".venv310",
    "node_modules",
    ".DS_Store",
    "Thumbs.db",
    # Don't copy build artifacts
    "build",
    "dist",
    "htmlcov",
    ".coverage",
    ".tox",
}

# File patterns to skip inside copied tree.
NESTED_EXCLUDE_PATTERNS = (".pyc", ".pyo", ".egg-info", ".so")


# ============================================================================
# IMPLEMENTATION
# ============================================================================


def ignore_nested(src, names):
    skip = []
    for n in names:
        if n in NESTED_EXCLUDE:
            skip.append(n)
            continue
        if any(n.endswith(ext) for ext in NESTED_EXCLUDE_PATTERNS):
            skip.append(n)
    return skip


def copy_one(src_path: Path, dest_path: Path) -> None:
    if src_path.is_dir():
        shutil.copytree(
            src_path,
            dest_path,
            dirs_exist_ok=True,
            symlinks=False,
            ignore=ignore_nested,
            ignore_dangling_symlinks=True,
        )
    else:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path)


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: Source does not exist: {SOURCE}", file=sys.stderr)
        return 1

    DEST.mkdir(parents=True, exist_ok=True)

    print(f"Source : {SOURCE}")
    print(f"Dest   : {DEST}")
    print(f"Started: {datetime.now().isoformat(timespec='seconds')}")
    print("-" * 60)

    copied: list[str] = []
    missing: list[str] = []
    excluded: list[str] = []
    errors: list[tuple[str, str]] = []

    # Always-excluded check first
    for item in sorted(SOURCE.iterdir()):
        if item.name in TOP_LEVEL_EXCLUDE:
            excluded.append(item.name + ("/" if item.is_dir() else ""))

    # Copy items from INCLUDE list
    for rel in INCLUDE:
        src_item = SOURCE / rel
        if not src_item.exists():
            missing.append(rel)
            continue

        if src_item.name in TOP_LEVEL_EXCLUDE:
            excluded.append(rel)
            continue

        dest_item = DEST / rel
        label = rel + ("/" if src_item.is_dir() else "")
        print(f"COPY  {label}", flush=True)
        try:
            copy_one(src_item, dest_item)
            copied.append(label)
        except Exception as e:
            print(f"  FAIL: {e}", flush=True)
            errors.append((label, str(e)))

    print("-" * 60)
    print(f"Copied   : {len(copied)}")
    print(f"Missing  : {len(missing)} -> {', '.join(missing) if missing else '(none)'}")
    print(f"Excluded : {len(excluded)} (never copied)")
    if errors:
        print(f"Errors   : {len(errors)}")
        for name, err in errors:
            print(f"  - {name}: {err}")

    print(f"Done     : {datetime.now().isoformat(timespec='seconds')}")
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
