"""Stamp the standard 7 meta files (PURPOSE, AGENTS, INPUTS_OUTPUTS,
HIERARCHY, DIAGRAM, TESTS, STATUS) into every module folder under
packages/duecare-llm-*/src/duecare/.

Per .claude/rules/40_forge_module_contract.md, every module is a folder
and every folder has the same self-describing meta files. The original
generate_forge.py is deprecated; this is a lighter replacement that
introspects what's already in each folder and stamps minimal-but-real
meta files when they're missing.

Run:
    python scripts/stamp_module_meta.py

Idempotent — never overwrites an existing meta file. Pass --overwrite
if you really want to regenerate.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


REQUIRED = (
    "PURPOSE.md",
    "AGENTS.md",
    "INPUTS_OUTPUTS.md",
    "HIERARCHY.md",
    "DIAGRAM.md",
    "TESTS.md",
    "STATUS.md",
)


def _module_id(folder: Path) -> str:
    """Translate a folder path to the duecare.* module id."""
    parts = folder.parts
    try:
        idx = parts.index("duecare")
        return ".".join(parts[idx:])
    except ValueError:
        return folder.name


def _module_title(folder: Path) -> str:
    return folder.name.replace("_", " ").title()


def _docstring(folder: Path) -> str:
    """Return the top-level __init__.py docstring if present."""
    init = folder / "__init__.py"
    if not init.exists():
        return ""
    try:
        tree = ast.parse(init.read_text(encoding="utf-8"))
        return ast.get_docstring(tree) or ""
    except Exception:
        return ""


def _siblings(folder: Path) -> list[str]:
    parent = folder.parent
    if not parent.is_dir():
        return []
    return sorted(
        p.name
        for p in parent.iterdir()
        if p.is_dir()
        and p.name != folder.name
        and p.name != "__pycache__"
        and not p.name.startswith(".")
        and (p / "__init__.py").exists()
    )


def _children(folder: Path) -> list[str]:
    return sorted(
        p.name
        for p in folder.iterdir()
        if p.is_dir()
        and p.name != "__pycache__"
        and p.name != "tests"
        and not p.name.startswith(".")
        and (p / "__init__.py").exists()
    )


def _source_files(folder: Path) -> list[str]:
    return sorted(
        p.name
        for p in folder.iterdir()
        if p.is_file() and p.suffix == ".py" and not p.name.startswith("_")
    )


def render_purpose(folder: Path) -> str:
    title = _module_title(folder)
    mid = _module_id(folder)
    doc = _docstring(folder).strip()
    body = doc if doc else (
        f"Module `{mid}` is part of the Duecare safety-harness "
        f"workspace. See the package README for context and usage."
    )
    return (
        f"# {title} — purpose\n\n"
        f"**Module id:** `{mid}`\n\n"
        f"## One-line\n\n"
        f"{body.splitlines()[0] if body else 'TBD.'}\n\n"
        f"## Long-form\n\n"
        f"{body}\n\n"
        f"## See also\n\n"
        f"- [`AGENTS.md`](AGENTS.md) — agentic instructions for AI readers\n"
        f"- [`HIERARCHY.md`](HIERARCHY.md) — position in the module tree\n"
        f"- [`STATUS.md`](STATUS.md) — completion state and TODO list\n"
    )


def render_agents(folder: Path) -> str:
    title = _module_title(folder)
    mid = _module_id(folder)
    return (
        f"# AGENTS — guidance for AI assistants working on `{mid}`\n\n"
        f"This file is the standards-compliant agentic-AI contract for "
        f"the **{title}** module. Tools that read AGENTS.md natively "
        f"(Claude Code, Cursor, Copilot, Windsurf, Aider, Zed, Warp, "
        f"RooCode) will pick this up automatically.\n\n"
        f"## What this module is\n\n"
        f"See [`PURPOSE.md`](PURPOSE.md) for the one-line + long-form "
        f"description.\n\n"
        f"## How to work on this module\n\n"
        f"- **Read order:** `PURPOSE.md` → `INPUTS_OUTPUTS.md` → "
        f"`HIERARCHY.md` → source files → `tests/`\n"
        f"- **Tests:** see [`TESTS.md`](TESTS.md). Every behavior-bearing "
        f"function should have at least one test.\n"
        f"- **Cross-module imports:** flow downward only "
        f"(`duecare.agents` → `duecare.tasks` → `duecare.core`). "
        f"Never import siblings at the same layer; never import "
        f"upward.\n"
        f"- **Style:** see `.claude/rules/20_code_style.md` at the repo "
        f"root. Pydantic v2, `typing.Protocol` for contracts, "
        f"`pathlib.Path` for paths.\n"
        f"- **Privacy gate:** see `.claude/rules/10_safety_gate.md`. "
        f"No raw PII may flow through this module.\n\n"
        f"## Public API\n\n"
        f"Exports are defined in `__init__.py`. Import from "
        f"`{mid}` (the module path), not from internal submodules.\n"
    )


def render_inputs_outputs(folder: Path) -> str:
    mid = _module_id(folder)
    return (
        f"# INPUTS / OUTPUTS — `{mid}`\n\n"
        f"This file documents the protocols and context keys this "
        f"module reads from and writes to. Auto-stamped — fill in "
        f"specifics as the module's contract solidifies.\n\n"
        f"## Reads\n\n"
        f"- Configuration via constructor arguments (typed via Pydantic v2)\n"
        f"- Optional context dict (see `duecare.core.contracts`)\n\n"
        f"## Writes\n\n"
        f"- Return values typed via Pydantic v2 schemas where applicable\n"
        f"- Side effects (file writes, DB writes, network calls) are "
        f"explicit in each function's docstring\n\n"
        f"## Protocols implemented\n\n"
        f"See `duecare.core.contracts` for the protocol definitions "
        f"this module satisfies.\n"
    )


def render_hierarchy(folder: Path) -> str:
    mid = _module_id(folder)
    parent_path = folder.parent
    parent_id = _module_id(parent_path) if parent_path.name != "duecare" else "duecare"
    sibs = _siblings(folder)
    kids = _children(folder)
    sibs_md = "\n".join(f"- `{s}`" for s in sibs) or "_(none)_"
    kids_md = "\n".join(f"- `{c}`" for c in kids) or "_(none)_"
    return (
        f"# HIERARCHY — `{mid}`\n\n"
        f"## Parent\n\n"
        f"`{parent_id}`\n\n"
        f"## Siblings\n\n"
        f"{sibs_md}\n\n"
        f"## Children\n\n"
        f"{kids_md}\n\n"
        f"## Depends on\n\n"
        f"`duecare.core` (contracts, schemas) — and any cross-package "
        f"imports listed in this module's `pyproject.toml` dependencies.\n\n"
        f"## Depended on by\n\n"
        f"See the workspace dependency graph in "
        f"`docs/architecture.md`.\n"
    )


def render_diagram(folder: Path) -> str:
    mid = _module_id(folder)
    title = _module_title(folder)
    return (
        f"# DIAGRAM — `{mid}`\n\n"
        f"```\n"
        f"            ┌──────────────────────┐\n"
        f"            │    duecare.core      │ (contracts + schemas)\n"
        f"            └──────────┬───────────┘\n"
        f"                       │ implements / consumes\n"
        f"                       ▼\n"
        f"            ┌──────────────────────┐\n"
        f"            │  {title:<20s}│  ← THIS MODULE\n"
        f"            │  ({mid:<14s})│\n"
        f"            └──────────┬───────────┘\n"
        f"                       │ exports\n"
        f"                       ▼\n"
        f"            ┌──────────────────────┐\n"
        f"            │  upstream consumers  │\n"
        f"            └──────────────────────┘\n"
        f"```\n\n"
        f"For the full system map see "
        f"[`docs/system_map.md`](../../../../../../docs/system_map.md) "
        f"or the interactive HTML version.\n"
    )


def render_tests(folder: Path) -> str:
    mid = _module_id(folder)
    parent = folder.parent
    pkg_root = parent
    while pkg_root.parent.name != "packages":
        pkg_root = pkg_root.parent
        if pkg_root.parent == pkg_root:
            break
    pkg_name = pkg_root.name
    return (
        f"# TESTS — `{mid}`\n\n"
        f"## Run the module's tests\n\n"
        f"```bash\n"
        f"# from repo root\n"
        f"python -m pytest packages/{pkg_name}/tests -q\n"
        f"```\n\n"
        f"## Run all package tests\n\n"
        f"```bash\n"
        f"make test\n"
        f"```\n\n"
        f"## Test conventions\n\n"
        f"- Tests live at `packages/{pkg_name}/tests/test_*.py`\n"
        f"- One test file per source module where practical\n"
        f"- Mock external I/O in unit tests; integration tests hit "
        f"real SQLite + small fixtures\n"
        f"- See `.claude/rules/30_test_before_commit.md` at the repo "
        f"root\n"
    )


def render_status(folder: Path) -> str:
    mid = _module_id(folder)
    src = _source_files(folder)
    has_tests = (folder.parent / "tests").exists() or (
        folder / "tests"
    ).exists()
    state = "complete" if src and has_tests else "partial"
    src_md = "\n".join(f"- `{s}`" for s in src) or "_(only `__init__.py`)_"
    return (
        f"# STATUS — `{mid}`\n\n"
        f"## Current state\n\n"
        f"**{state}**\n\n"
        f"## Source files present\n\n"
        f"{src_md}\n\n"
        f"## TODO\n\n"
        f"- [ ] Fill in module-specific work items as the module evolves\n"
        f"- [ ] Update this STATUS.md when behavior changes\n"
        f"- [ ] Promote to `complete` once the module's contract is "
        f"frozen and tests cover the full behavior surface\n"
    )


RENDERERS = {
    "PURPOSE.md": render_purpose,
    "AGENTS.md": render_agents,
    "INPUTS_OUTPUTS.md": render_inputs_outputs,
    "HIERARCHY.md": render_hierarchy,
    "DIAGRAM.md": render_diagram,
    "TESTS.md": render_tests,
    "STATUS.md": render_status,
}


def stamp_folder(folder: Path, *, overwrite: bool = False) -> int:
    """Stamp missing meta files in `folder`. Returns count of files written."""
    written = 0
    for name, renderer in RENDERERS.items():
        target = folder / name
        if target.exists() and not overwrite:
            continue
        target.write_text(renderer(folder), encoding="utf-8")
        written += 1
    return written


def discover_module_folders() -> list[Path]:
    """Find all module folders that look like Duecare submodules."""
    repo = Path(__file__).resolve().parent.parent
    out: list[Path] = []
    pkg_root = repo / "packages"
    if not pkg_root.is_dir():
        return out
    for pkg in sorted(pkg_root.iterdir()):
        if not pkg.is_dir():
            continue
        src_root = pkg / "src" / "duecare"
        if not src_root.is_dir():
            continue
        for init in src_root.rglob("__init__.py"):
            d = init.parent
            if d.name == "duecare":
                continue
            if "tests" in d.parts or "__pycache__" in d.parts:
                continue
            out.append(d)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing meta files (default: only stamp missing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be written without writing",
    )
    args = parser.parse_args()

    folders = discover_module_folders()
    print(f"Discovered {len(folders)} module folders.")
    total_written = 0
    folders_touched = 0
    for folder in folders:
        missing = [n for n in REQUIRED if not (folder / n).exists()]
        if not missing and not args.overwrite:
            continue
        rel = folder.relative_to(Path(__file__).resolve().parent.parent)
        if args.dry_run:
            print(f"  WOULD WRITE {len(missing)} files in {rel}")
            total_written += len(missing)
        else:
            written = stamp_folder(folder, overwrite=args.overwrite)
            print(f"  Wrote {written} files in {rel}")
            total_written += written
        folders_touched += 1
    print(
        f"Done: {total_written} meta files "
        f"{'would be ' if args.dry_run else ''}written across "
        f"{folders_touched} folders."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
