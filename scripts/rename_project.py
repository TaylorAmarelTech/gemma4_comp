#!/usr/bin/env python3
"""Rename the project namespace across the entire codebase.

This script does a comprehensive rename from one namespace to another.
It handles:
  - Python source files (imports, strings, docstrings)
  - pyproject.toml files (package names, dependencies, tool config)
  - Markdown files (references, badges, install commands)
  - YAML/JSON config files (package references)
  - Kaggle kernel metadata (slugs, titles, dataset names)
  - CI config (.github/workflows/)
  - Dockerfile, Makefile
  - Directory names (packages/duecare-llm-* -> packages/sentinel-*)
  - Notebook generator script

Usage:
    python scripts/rename_project.py --old forge --new sentinel --dry-run
    python scripts/rename_project.py --old forge --new sentinel
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Directories to skip
SKIP_DIRS = {".git", "__pycache__", ".mypy_cache", ".ruff_cache", "node_modules",
             "_reference", "_archive", ".venv", "venv", "dist", "*.egg-info"}

# File extensions to process
TEXT_EXTS = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".jsonl",
             ".cfg", ".ini", ".txt", ".sh", ".bat", ".ps1", ".ipynb",
             ".dockerfile", ""}  # "" for Makefile, Dockerfile


def should_skip(path: Path) -> bool:
    for part in path.parts:
        for skip in SKIP_DIRS:
            if skip.startswith("*"):
                if part.endswith(skip[1:]):
                    return True
            elif part == skip:
                return True
    return False


def is_text_file(path: Path) -> bool:
    if path.name in ("Makefile", "Dockerfile", ".gitignore", ".gitattributes"):
        return True
    return path.suffix.lower() in TEXT_EXTS


class Renamer:
    def __init__(self, old: str, new: str, *, dry_run: bool = False):
        self.old = old
        self.new = new
        self.dry_run = dry_run
        self.files_changed: list[str] = []
        self.dirs_renamed: list[tuple[str, str]] = []

    def _replacements(self) -> list[tuple[str, str]]:
        """Generate all replacement pairs, ordered longest-first to avoid
        partial matches."""
        o, n = self.old, self.new
        O, N = o.capitalize(), n.capitalize()
        OU, NU = o.upper(), n.upper()

        pairs = [
            # PyPI package names (with -llm- infix)
            (f"{o}-llm-core", f"{n}-llm-core"),
            (f"{o}-llm-models", f"{n}-llm-models"),
            (f"{o}-llm-domains", f"{n}-llm-domains"),
            (f"{o}-llm-tasks", f"{n}-llm-tasks"),
            (f"{o}-llm-agents", f"{n}-llm-agents"),
            (f"{o}-llm-workflows", f"{n}-llm-workflows"),
            (f"{o}-llm-publishing", f"{n}-llm-publishing"),
            (f"{o}-llm", f"{n}-llm"),

            # Wheel filenames (underscored)
            (f"{o}_llm_core", f"{n}_llm_core"),
            (f"{o}_llm_models", f"{n}_llm_models"),
            (f"{o}_llm_domains", f"{n}_llm_domains"),
            (f"{o}_llm_tasks", f"{n}_llm_tasks"),
            (f"{o}_llm_agents", f"{n}_llm_agents"),
            (f"{o}_llm_workflows", f"{n}_llm_workflows"),
            (f"{o}_llm_publishing", f"{n}_llm_publishing"),
            (f"{o}_llm", f"{n}_llm"),

            # Python imports and namespace
            (f"{o}.observability", f"{n}.observability"),
            (f"{o}.publishing", f"{n}.publishing"),
            (f"{o}.workflows", f"{n}.workflows"),
            (f"{o}.domains", f"{n}.domains"),
            (f"{o}.models", f"{n}.models"),
            (f"{o}.agents", f"{n}.agents"),
            (f"{o}.tasks", f"{n}.tasks"),
            (f"{o}.core", f"{n}.core"),
            (f"{o}.cli", f"{n}.cli"),

            # Standalone references
            (f"import {o}", f"import {n}"),
            (f"from {o}", f"from {n}"),
            (f'"{o}"', f'"{n}"'),
            (f"'{o}'", f"'{n}'"),

            # Display names / titles
            (f"{O} Run Report", f"{N} Run Report"),
            (f"{O} —", f"{N} —"),
            (f"{O} -", f"{N} -"),
            (f"{O} LLM", f"{N} LLM"),
            (f"# {O}", f"# {N}"),
            (f"**{O}**", f"**{N}**"),
            (f"`{o}`", f"`{n}`"),

            # Config paths
            (f"configs/{o}/", f"configs/{n}/"),

            # Structlog logger names
            (f"{o}.agents", f"{n}.agents"),
            (f"{o}.core", f"{n}.core"),

            # Kaggle
            (f"{o}-quickstart", f"{n}-quickstart"),
            (f"{o}-cross-domain", f"{n}-cross-domain"),
            (f"{o}-agent-swarm", f"{n}-agent-swarm"),
            (f"{o}-submission", f"{n}-submission"),
            (f"{o}-eval-results", f"{n}-eval-results"),
            (f"{o}-safety-harness", f"{n}-safety-harness"),
            (f"{o}-llm-wheels", f"{n}-llm-wheels"),

            # README badges etc.
            (f"{O} Safety Harness", f"{N} Safety Harness"),

            # CLI entry point
            (f"{o} test", f"{n} test"),
            (f"{o} run", f"{n} run"),
            (f"{o} tree", f"{n} tree"),
            (f"{o} status", f"{n} status"),
            (f"{o} review", f"{n} review"),
            (f"{o} deps", f"{n} deps"),
            (f"{o} dependents", f"{n} dependents"),

            # Generic lowercase (LAST — catches remaining refs)
            (O, N),
        ]
        return pairs

    def rename_content(self, path: Path) -> bool:
        """Replace all occurrences in a single file. Returns True if changed."""
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            return False

        original = content
        for old_str, new_str in self._replacements():
            content = content.replace(old_str, new_str)

        if content != original:
            if not self.dry_run:
                path.write_text(content, encoding="utf-8")
            self.files_changed.append(str(path.relative_to(REPO_ROOT)))
            return True
        return False

    def rename_directories(self) -> None:
        """Rename package directories and config directories."""
        o, n = self.old, self.new

        # Package directories: packages/duecare-llm-* -> packages/sentinel-llm-*
        pkg_dir = REPO_ROOT / "packages"
        if pkg_dir.exists():
            for d in sorted(pkg_dir.iterdir(), reverse=True):
                if d.is_dir() and d.name.startswith(f"{o}-llm"):
                    new_name = d.name.replace(f"{o}-llm", f"{n}-llm", 1)
                    new_path = d.parent / new_name
                    print(f"  dir: {d.name} -> {new_name}")
                    if not self.dry_run:
                        d.rename(new_path)
                    self.dirs_renamed.append((str(d), str(new_path)))

        # Source namespace directories: src/forge/ -> src/sentinel/
        for pkg_path in (REPO_ROOT / "packages").rglob("src"):
            old_ns = pkg_path / o
            if old_ns.exists() and old_ns.is_dir():
                new_ns = pkg_path / n
                print(f"  ns:  {old_ns.relative_to(REPO_ROOT)} -> {new_ns.relative_to(REPO_ROOT)}")
                if not self.dry_run:
                    old_ns.rename(new_ns)
                self.dirs_renamed.append((str(old_ns), str(new_ns)))

        # Config directory: configs/duecare/ -> configs/sentinel/
        old_cfg = REPO_ROOT / "configs" / o
        if old_cfg.exists():
            new_cfg = REPO_ROOT / "configs" / n
            print(f"  cfg: configs/{o} -> configs/{n}")
            if not self.dry_run:
                old_cfg.rename(new_cfg)
            self.dirs_renamed.append((str(old_cfg), str(new_cfg)))

        # Kaggle dataset dirs
        for kaggle_sub in ["datasets", "kernels"]:
            kaggle_dir = REPO_ROOT / "kaggle" / kaggle_sub
            if not kaggle_dir.exists():
                continue
            for d in sorted(kaggle_dir.iterdir(), reverse=True):
                if d.is_dir() and o in d.name:
                    new_name = d.name.replace(o, n)
                    new_path = d.parent / new_name
                    print(f"  kaggle: {d.name} -> {new_name}")
                    if not self.dry_run:
                        d.rename(new_path)
                    self.dirs_renamed.append((str(d), str(new_path)))

    def run(self) -> int:
        print(f"# Renaming: {self.old} -> {self.new}")
        if self.dry_run:
            print("  (DRY RUN — no changes will be written)")
        print()

        # Phase 1: Rename file contents BEFORE moving directories
        print("## Phase 1: Updating file contents")
        for root_path in [REPO_ROOT]:
            for path in sorted(root_path.rglob("*")):
                if not path.is_file():
                    continue
                if should_skip(path):
                    continue
                if not is_text_file(path):
                    continue
                self.rename_content(path)

        print(f"  {len(self.files_changed)} files updated")
        print()

        # Phase 2: Rename directories
        print("## Phase 2: Renaming directories")
        self.rename_directories()
        print(f"  {len(self.dirs_renamed)} directories renamed")
        print()

        # Summary
        print("## Summary")
        print(f"  Files changed:      {len(self.files_changed)}")
        print(f"  Directories renamed: {len(self.dirs_renamed)}")
        if self.dry_run:
            print("\n  Run without --dry-run to apply changes.")
        else:
            print("\n  DONE. Next steps:")
            print("  1. Rebuild all 8 wheels")
            print("  2. Run tests:  python -m pytest packages tests -q")
            print("  3. Re-push Kaggle dataset + notebooks")

        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--old", required=True, help="Current namespace (e.g. 'duecare')")
    parser.add_argument("--new", required=True, help="New namespace (e.g. 'sentinel')")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args(argv)

    renamer = Renamer(args.old, args.new, dry_run=args.dry_run)
    return renamer.run()


if __name__ == "__main__":
    sys.exit(main())
