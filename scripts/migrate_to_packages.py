#!/usr/bin/env python3
"""
migrate_to_packages.py - Restructure src/forge/ into packages/duecare-llm-*/.

Splits the monorepo into 7 PyPI packages + 1 meta package, sharing the
`duecare` Python namespace via PEP 420 implicit namespace packages.

Mapping:
  src/forge/core/         -> packages/duecare-llm-core/src/forge/core/
  src/forge/observability/ -> packages/duecare-llm-core/src/forge/observability/
  src/forge/models/       -> packages/duecare-llm-models/src/forge/models/
  src/forge/domains/      -> packages/duecare-llm-domains/src/forge/domains/
  src/forge/tasks/        -> packages/duecare-llm-tasks/src/forge/tasks/
  src/forge/agents/       -> packages/duecare-llm-agents/src/forge/agents/
  src/forge/workflows/    -> packages/duecare-llm-workflows/src/forge/workflows/
  src/forge/publishing/   -> packages/duecare-llm-publishing/src/forge/publishing/
  src/forge/cli.py        -> packages/duecare-llm/src/forge/cli/__init__.py
  src/forge/__main__.py   -> packages/duecare-llm/src/forge/__main__.py
  src/forge/__init__.py   -> (deleted; namespace packages have no __init__.py)
  src/forge/<root meta>   -> packages/duecare-llm/src/forge/<root meta>

After move, creates:
  packages/<pkg>/pyproject.toml  for each of the 8 packages
  packages/<pkg>/README.md       for each package
  pyproject.toml                 workspace root using uv workspaces
  Migration is non-destructive in the "no data loss" sense - files move
  inside the same project tree. The source layout (src/forge/) is empty
  after the move. There is no git in this directory, so re-run by hand
  if needed.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent.parent


# ===========================================================================
# Layer -> package mapping
# ===========================================================================

# observability is folded into duecare-llm-core because it's small and
# every other layer depends on it (logging, metrics, audit).
LAYER_TO_PACKAGE: dict[str, str] = {
    "core": "duecare-llm-core",
    "observability": "duecare-llm-core",
    "models": "duecare-llm-models",
    "domains": "duecare-llm-domains",
    "tasks": "duecare-llm-tasks",
    "agents": "duecare-llm-agents",
    "workflows": "duecare-llm-workflows",
    "publishing": "duecare-llm-publishing",
}

ALL_LIBRARY_PACKAGES = sorted(set(LAYER_TO_PACKAGE.values()))
META_PACKAGE = "duecare-llm"
ALL_PACKAGES = ALL_LIBRARY_PACKAGES + [META_PACKAGE]


# ===========================================================================
# Per-package metadata (pyproject.toml content)
# ===========================================================================

PACKAGES: dict[str, dict] = {
    "duecare-llm-core": {
        "description": "Duecare core: contracts, schemas, enums, registries, provenance, observability.",
        "deps": [
            "pydantic>=2.9.0",
            "structlog>=24.0.0",
            "pyyaml>=6.0",
        ],
        "extras": {},
        "imports": ["duecare.core", "duecare.observability"],
        "src_dirs": ["src/forge/core", "src/forge/observability"],
    },
    "duecare-llm-models": {
        "description": "Duecare model adapters: HF Transformers, llama.cpp, Unsloth, Ollama, OpenAI, Anthropic, Google Gemini, HF Inference Endpoints.",
        "deps": [
            "duecare-llm-core>=0.1.0,<0.2.0",
        ],
        "extras": {
            "transformers": [
                "transformers>=4.50.0",
                "accelerate>=1.2.0",
                "bitsandbytes>=0.46.0",
                "torch>=2.4.0",
                "sentencepiece>=0.2.0",
                "tokenizers>=0.21.0",
            ],
            "unsloth": [
                "unsloth>=2025.10",
                "peft>=0.15.0",
                "trl>=0.15.0",
                "datasets>=3.0.0",
            ],
            "llama-cpp": ["llama-cpp-python>=0.3.0"],
            "ollama": ["ollama>=0.4.0"],
            "openai": ["openai>=1.50.0"],
            "anthropic": ["anthropic>=0.40.0"],
            "google": ["google-generativeai>=0.8.0"],
            "hf-endpoint": ["huggingface_hub>=0.27.0"],
            "all": [
                "duecare-llm-models[transformers]",
                "duecare-llm-models[unsloth]",
                "duecare-llm-models[llama-cpp]",
                "duecare-llm-models[ollama]",
                "duecare-llm-models[openai]",
                "duecare-llm-models[anthropic]",
                "duecare-llm-models[google]",
                "duecare-llm-models[hf-endpoint]",
            ],
        },
        "imports": ["duecare.models"],
        "src_dirs": ["src/forge/models"],
    },
    "duecare-llm-domains": {
        "description": "Duecare domain pack system: pluggable taxonomy + evidence + rubric loaders.",
        "deps": [
            "duecare-llm-core>=0.1.0,<0.2.0",
            "pyyaml>=6.0",
        ],
        "extras": {},
        "imports": ["duecare.domains"],
        "src_dirs": ["src/forge/domains"],
    },
    "duecare-llm-tasks": {
        "description": "Duecare capability tests: guardrails, anonymization, classification, fact extraction, grounding, multimodal classification, adversarial multi-turn, tool use, cross-lingual.",
        "deps": [
            "duecare-llm-core>=0.1.0,<0.2.0",
            "duecare-llm-models>=0.1.0,<0.2.0",
            "duecare-llm-domains>=0.1.0,<0.2.0",
        ],
        "extras": {
            "anonymization": [
                "presidio-analyzer>=2.2.0",
                "presidio-anonymizer>=2.2.0",
            ],
            "embedding": ["sentence-transformers>=3.0.0", "faiss-cpu>=1.8.0"],
        },
        "imports": ["duecare.tasks"],
        "src_dirs": ["src/forge/tasks"],
    },
    "duecare-llm-agents": {
        "description": "Duecare 12-agent autonomous swarm: Scout, DataGenerator, Adversary, Anonymizer, Curator, Judge, Validator, CurriculumDesigner, Trainer, Exporter, Historian, Coordinator.",
        "deps": [
            "duecare-llm-core>=0.1.0,<0.2.0",
            "duecare-llm-models>=0.1.0,<0.2.0",
            "duecare-llm-tasks>=0.1.0,<0.2.0",
        ],
        "extras": {
            "trainer": ["duecare-llm-models[unsloth]"],
        },
        "imports": ["duecare.agents"],
        "src_dirs": ["src/forge/agents"],
    },
    "duecare-llm-workflows": {
        "description": "Duecare workflow DAG orchestration: YAML loader, runner, dependency walker.",
        "deps": [
            "duecare-llm-core>=0.1.0,<0.2.0",
            "duecare-llm-agents>=0.1.0,<0.2.0",
            "pyyaml>=6.0",
        ],
        "extras": {},
        "imports": ["duecare.workflows"],
        "src_dirs": ["src/forge/workflows"],
    },
    "duecare-llm-publishing": {
        "description": "Duecare publication: HF Hub, Kaggle Datasets/Models/Kernels, markdown reports, model cards.",
        "deps": [
            "duecare-llm-core>=0.1.0,<0.2.0",
        ],
        "extras": {
            "hf-hub": ["huggingface_hub>=0.27.0"],
            "kaggle": ["kaggle>=2.0.0"],
            "all": [
                "duecare-llm-publishing[hf-hub]",
                "duecare-llm-publishing[kaggle]",
            ],
        },
        "imports": ["duecare.publishing"],
        "src_dirs": ["src/forge/publishing"],
    },
    "duecare-llm": {
        "description": "Duecare - agentic, universal LLM safety harness. Meta-package that pulls in every Duecare component and exposes the `duecare` CLI.",
        "deps": [
            "duecare-llm-core>=0.1.0,<0.2.0",
            "duecare-llm-models>=0.1.0,<0.2.0",
            "duecare-llm-domains>=0.1.0,<0.2.0",
            "duecare-llm-tasks>=0.1.0,<0.2.0",
            "duecare-llm-agents>=0.1.0,<0.2.0",
            "duecare-llm-workflows>=0.1.0,<0.2.0",
            "duecare-llm-publishing>=0.1.0,<0.2.0",
            "typer>=0.12.0",
            "rich>=13.0.0",
        ],
        "extras": {
            "all": [
                "duecare-llm-models[all]",
                "duecare-llm-tasks[anonymization,embedding]",
                "duecare-llm-agents[trainer]",
                "duecare-llm-publishing[all]",
            ],
            "dev": [
                "pytest>=8.3.0",
                "pytest-asyncio>=0.24.0",
                "ruff>=0.8.0",
                "mypy>=1.13.0",
            ],
        },
        "imports": ["duecare.cli"],
        "src_dirs": ["src/forge/cli"],  # cli is a subpackage; created during move
        "is_meta": True,
        "scripts": {
            "duecare": "duecare.cli:main",
        },
    },
}


# ===========================================================================
# Templates
# ===========================================================================

PYPROJECT_TEMPLATE = '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
license = {{text = "MIT"}}
requires-python = ">=3.11"
authors = [{{name = "Taylor Amarel"}}]
keywords = ["llm", "safety", "gemma", "duecare", "agentic"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
dependencies = [
{deps_block}
]

{extras_block}
{scripts_block}

[project.urls]
Homepage = "https://github.com/taylorsamarel/gemma4_comp"
Documentation = "https://github.com/taylorsamarel/gemma4_comp/blob/main/docs/the_forge.md"
Issues = "https://github.com/taylorsamarel/gemma4_comp/issues"
Repository = "https://github.com/taylorsamarel/gemma4_comp"

[tool.hatch.build.targets.wheel]
packages = ["src/forge"]

[tool.hatch.build.targets.wheel.shared-data]
"PURPOSE.md" = "PURPOSE.md"
"AGENTS.md" = "AGENTS.md"

[tool.hatch.build.targets.sdist]
include = [
    "src/**/*.py",
    "src/**/*.md",
    "src/**/*.yaml",
    "src/**/*.yml",
    "src/**/*.json",
    "tests/**/*.py",
    "README.md",
    "PURPOSE.md",
    "AGENTS.md",
    "pyproject.toml",
]
'''

WORKSPACE_PYPROJECT_TEMPLATE = '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "forge-workspace"
version = "0.1.0"
description = "Workspace root for the Duecare multi-package monorepo"
requires-python = ">=3.11"

# Dev dependencies for the whole workspace
[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "jupytext>=1.16.0",
    "repomix>=0.2.0",
]

# uv workspace - one workspace member per package directory
[tool.uv.workspace]
members = [
    "packages/duecare-llm-core",
    "packages/duecare-llm-models",
    "packages/duecare-llm-domains",
    "packages/duecare-llm-tasks",
    "packages/duecare-llm-agents",
    "packages/duecare-llm-workflows",
    "packages/duecare-llm-publishing",
    "packages/duecare-llm",
]

# Internal sources for development - resolves Duecare packages from each
# other inside the workspace instead of pulling from PyPI
[tool.uv.sources]
duecare-llm-core = {{ workspace = true }}
duecare-llm-models = {{ workspace = true }}
duecare-llm-domains = {{ workspace = true }}
duecare-llm-tasks = {{ workspace = true }}
duecare-llm-agents = {{ workspace = true }}
duecare-llm-workflows = {{ workspace = true }}
duecare-llm-publishing = {{ workspace = true }}
duecare-llm = {{ workspace = true }}

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true
disallow_untyped_defs = true
namespace_packages = true
explicit_package_bases = true

[tool.pytest.ini_options]
testpaths = ["packages/*/tests", "packages/*/src/forge/*/tests", "tests"]
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "e2e: marks tests as end-to-end tests",
]
'''

PACKAGE_README_TEMPLATE = '''# {name}

> {description}

Part of the **Duecare** multi-package distribution. See the
[main project README](../../README.md) and
[the_forge.md architecture doc](../../docs/the_forge.md) for the full
context.

## Install

```bash
pip install {name}
```

{extras_install}

## What's in this package

Python imports provided:
{import_list}

## Position in the Duecare stack

{position_diagram}

## Source

- Repository: https://github.com/taylorsamarel/gemma4_comp
- Documentation: https://github.com/taylorsamarel/gemma4_comp/blob/main/docs/the_forge.md
- License: MIT

## How to develop on this package

This package lives inside the Duecare workspace
(`gemma4_comp/packages/{name}/`). The workspace root has a `uv` workspace
config that resolves all `duecare-llm-*` dependencies from sibling
packages instead of from PyPI, so editable installs work out of the box:

```bash
# from the workspace root
uv sync
uv run pytest packages/{name}
```

You can also pip-install in editable mode without uv:

```bash
pip install -e packages/{name}
```
'''


# ===========================================================================
# Helpers
# ===========================================================================


def render_deps_block(deps: list[str]) -> str:
    if not deps:
        return ""
    return "\n".join(f'    "{d}",' for d in deps)


def render_extras_block(extras: dict) -> str:
    if not extras:
        return ""
    lines = ["[project.optional-dependencies]"]
    for name, items in extras.items():
        lines.append(f"{name} = [")
        for item in items:
            lines.append(f'    "{item}",')
        lines.append("]")
    return "\n".join(lines) + "\n"


def render_scripts_block(scripts: dict | None) -> str:
    if not scripts:
        return ""
    lines = ["[project.scripts]"]
    for name, target in scripts.items():
        lines.append(f'{name} = "{target}"')
    return "\n".join(lines) + "\n"


def render_pyproject(name: str, info: dict) -> str:
    return PYPROJECT_TEMPLATE.format(
        name=name,
        description=info["description"].replace('"', '\\"'),
        deps_block=render_deps_block(info.get("deps", [])),
        extras_block=render_extras_block(info.get("extras", {})),
        scripts_block=render_scripts_block(info.get("scripts")),
    )


def render_extras_install(extras: dict, name: str) -> str:
    if not extras:
        return ""
    lines = ["## Optional extras", ""]
    for extra, _items in extras.items():
        lines.append(f"```bash")
        lines.append(f"pip install {name}[{extra}]")
        lines.append(f"```")
        lines.append("")
    return "\n".join(lines)


def render_position(name: str) -> str:
    return dedent("""
    ```
    duecare-llm (meta)
        |
        +-- duecare-llm-publishing
        +-- duecare-llm-workflows
        |       |
        +-------+ duecare-llm-agents
                    |
                    +-- duecare-llm-tasks
                            |
                            +-- duecare-llm-models
                            +-- duecare-llm-domains
                                    |
                                    +-- duecare-llm-core *
    ```
    """).strip()


def render_readme(name: str, info: dict) -> str:
    import_list = "\n".join(f"- `{imp}`" for imp in info.get("imports", []))
    return PACKAGE_README_TEMPLATE.format(
        name=name,
        description=info["description"],
        extras_install=render_extras_install(info.get("extras", {}), name),
        import_list=import_list or "(none)",
        position_diagram=render_position(name),
    )


# ===========================================================================
# Migration
# ===========================================================================


def move_layer(layer: str, package: str) -> int:
    src = ROOT / "src" / "duecare" / layer
    if not src.exists():
        print(f"  SKIP layer={layer}: source does not exist at {src}")
        return 0
    target = ROOT / "packages" / package / "src" / "duecare" / layer
    if target.exists():
        print(f"  SKIP layer={layer}: target already populated at {target}")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(target))
    print(f"  MOVE src/forge/{layer}/ -> packages/{package}/src/forge/{layer}/")
    return 1


def move_meta_files() -> int:
    """Move root-level meta files (PURPOSE.md, AGENTS.md, etc.) and __init__.py
    / cli.py / __main__.py from src/forge/ into the meta package."""
    count = 0
    src_root = ROOT / "src" / "duecare"
    if not src_root.exists():
        return 0

    meta_target = ROOT / "packages" / META_PACKAGE / "src" / "duecare"
    meta_target.mkdir(parents=True, exist_ok=True)

    # Move root meta files
    meta_files = [
        "PURPOSE.md", "AGENTS.md", "INPUTS_OUTPUTS.md",
        "HIERARCHY.md", "DIAGRAM.md", "TESTS.md", "STATUS.md",
    ]
    for f in meta_files:
        src = src_root / f
        if src.exists():
            dst = meta_target / f
            if not dst.exists():
                shutil.move(str(src), str(dst))
                count += 1
                print(f"  MOVE src/forge/{f} -> packages/{META_PACKAGE}/src/forge/{f}")

    # Move cli.py into a duecare.cli subpackage
    cli_src = src_root / "cli.py"
    if cli_src.exists():
        cli_dir = meta_target / "cli"
        cli_dir.mkdir(parents=True, exist_ok=True)
        cli_init = cli_dir / "__init__.py"
        if not cli_init.exists():
            shutil.move(str(cli_src), str(cli_init))
            count += 1
            print(f"  MOVE src/forge/cli.py -> packages/{META_PACKAGE}/src/forge/cli/__init__.py")

    # Move __main__.py
    main_src = src_root / "__main__.py"
    if main_src.exists():
        main_dst = meta_target / "__main__.py"
        if not main_dst.exists():
            shutil.move(str(main_src), str(main_dst))
            count += 1
            print(f"  MOVE src/forge/__main__.py -> packages/{META_PACKAGE}/src/forge/__main__.py")

    # Delete (do not move) src/forge/__init__.py - namespace packages have no
    # __init__.py at the namespace level. Same for any tests/__init__.py at
    # the bare src/forge level.
    init_src = src_root / "__init__.py"
    if init_src.exists():
        init_src.unlink()
        print(f"  DELETE src/forge/__init__.py (namespace packages have no __init__)")

    return count


def write_pyproject_files() -> int:
    count = 0
    for name, info in PACKAGES.items():
        pkg_dir = ROOT / "packages" / name
        pkg_dir.mkdir(parents=True, exist_ok=True)

        pyproj = pkg_dir / "pyproject.toml"
        if not pyproj.exists():
            pyproj.write_text(render_pyproject(name, info), encoding="utf-8")
            count += 1
            print(f"  WRITE packages/{name}/pyproject.toml")

        readme = pkg_dir / "README.md"
        if not readme.exists():
            readme.write_text(render_readme(name, info), encoding="utf-8")
            count += 1
            print(f"  WRITE packages/{name}/README.md")

        # Each package needs at least an empty tests/ directory so the
        # workspace pytest config doesn't error
        tests_dir = pkg_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        tests_init = tests_dir / "__init__.py"
        if not tests_init.exists():
            tests_init.write_text(
                f'"""Package-level tests for {name}.\n\n'
                f'Per-module unit tests live alongside each module under\n'
                f'src/forge/<module>/tests/ - this folder is for cross-module\n'
                f'integration tests inside the same package."""\n',
                encoding="utf-8",
            )
            count += 1

    return count


def write_workspace_root() -> int:
    """Write the workspace root pyproject.toml using uv workspaces."""
    target = ROOT / "pyproject.toml"
    if target.exists():
        # Move the existing one out of the way as a backup
        backup = ROOT / "pyproject.toml.pre-workspace.bak"
        if not backup.exists():
            shutil.copy(target, backup)
            print(f"  BACKUP pyproject.toml -> pyproject.toml.pre-workspace.bak")
    target.write_text(WORKSPACE_PYPROJECT_TEMPLATE, encoding="utf-8")
    print(f"  WRITE pyproject.toml (workspace root)")
    return 1


def cleanup_empty_src() -> int:
    """If src/forge/ is now empty, remove it. Same for src/ if also empty."""
    count = 0
    src_forge = ROOT / "src" / "duecare"
    if src_forge.exists() and not any(src_forge.iterdir()):
        src_forge.rmdir()
        print(f"  REMOVE empty src/forge/")
        count += 1

    # We may also have src/__init__.py, src/__main__.py, src/cli.py left
    # over from earlier flat-file scaffolds. Don't auto-remove those - leave
    # them for the user to inspect.
    src = ROOT / "src"
    if src.exists():
        remaining = list(src.iterdir())
        if not remaining:
            src.rmdir()
            print(f"  REMOVE empty src/")
            count += 1
        else:
            print(
                f"  NOTE  src/ still contains: "
                f"{', '.join(p.name for p in remaining)}"
            )
    return count


def main() -> int:
    print("=" * 70)
    print("Duecare multi-package migration")
    print("=" * 70)
    print(f"Repo root: {ROOT}")
    print(f"Packages:  {len(PACKAGES)}")
    print(f"Layers:    {sorted(LAYER_TO_PACKAGE.keys())}")
    print("-" * 70)

    print("Phase 1: move layer folders")
    moved = 0
    for layer, package in LAYER_TO_PACKAGE.items():
        moved += move_layer(layer, package)

    print()
    print("Phase 2: move root meta files + cli + __main__")
    moved += move_meta_files()

    print()
    print("Phase 3: write pyproject.toml + README.md + tests/__init__.py per package")
    written = write_pyproject_files()

    print()
    print("Phase 4: write workspace root pyproject.toml")
    written += write_workspace_root()

    print()
    print("Phase 5: cleanup empty src/forge/")
    cleanup_empty_src()

    print("-" * 70)
    print(f"Items moved:   {moved}")
    print(f"Files written: {written}")
    print(f"Packages:      {len(PACKAGES)} ({len(ALL_LIBRARY_PACKAGES)} library + 1 meta)")
    print()
    print("Next steps:")
    print("  1. Update scripts/generate_forge.py to target packages/*/src/forge/*")
    print("  2. Run python scripts/generate_forge.py to refresh meta files")
    print("  3. Run python -c 'from duecare.core.contracts import Model' to smoke test")
    print("     (after pip install -e packages/duecare-llm-core)")
    print("  4. Update CLAUDE.md to reflect packages/ layout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
