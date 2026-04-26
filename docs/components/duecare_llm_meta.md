# Component — `duecare-llm` (meta)

> **Status: shipped.** The `duecare` CLI + meta-package that pulls in
> all 7 siblings. 6 tests passing, wheel built.

## What it is

The **meta-package** that bundles all 7 DueCare library packages and
provides the `duecare` CLI entry point. This is what judges and users
install when they want "the whole thing."

## Install

```bash
pip install duecare-llm
```

This pulls in:

- `duecare-llm-core>=0.1.0,<0.2.0`
- `duecare-llm-models>=0.1.0,<0.2.0`
- `duecare-llm-domains>=0.1.0,<0.2.0`
- `duecare-llm-tasks>=0.1.0,<0.2.0`
- `duecare-llm-agents>=0.1.0,<0.2.0`
- `duecare-llm-workflows>=0.1.0,<0.2.0`
- `duecare-llm-publishing>=0.1.0,<0.2.0`
- `typer>=0.12.0`, `rich>=13.0.0`

And registers the `duecare` command on your PATH.

With extras:

```bash
# All ML + publishing dependencies
pip install 'duecare-llm[all]'

# Dev tools (pytest, ruff, mypy)
pip install 'duecare-llm[dev]'
```

## CLI reference

```
duecare run <workflow> --target-model <id> --domain <id>
    Run a workflow end-to-end via the WorkflowRunner.

duecare tree
    Show the module tree (folder-per-module view).

duecare review <path>
    Print the 7 meta files for a module folder.

duecare test <path> [-r/--no-recursive]
    Run pytest scoped to a path.

duecare status
    Show module completeness report (counts per layer).

forge agents list
    List all 12 registered agents.

forge models list
    List all 8 registered model adapters.

forge domains list
    List discoverable domain packs.

forge tasks list
    List all 9 registered capability tests.

duecare runs list
    List previous workflow runs by scanning the reports folder.
```

## Quick start via CLI

```bash
# Verify everything is installed and registered
forge agents list
forge models list
forge tasks list
forge domains list

# Run a workflow
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain trafficking

# Cross-domain proof - same command, different domain
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain tax_evasion
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain financial_crime

# Check the reports
duecare runs list
```

## Why a meta-package

Three reasons:

1. **Single pip install** for end users: `pip install duecare-llm` beats
   `pip install duecare-llm-core duecare-llm-models duecare-llm-domains
   duecare-llm-tasks duecare-llm-agents duecare-llm-workflows
   duecare-llm-publishing` every time.
2. **Single entry-point registration** — the `duecare` script is
   declared in exactly one `pyproject.toml`.
3. **Single version pin** — the meta package constrains every sibling
   to `>=0.1.0,<0.2.0`, so `pip install duecare-llm==0.1.0` gets you a
   fully compatible set of 8 packages without mix-and-match risk.

## Design decisions

### 1. No `forge/` `__init__.py` in the meta package

The `duecare` directory in `packages/duecare-llm/src/forge/` has **no**
`__init__.py` at the namespace level. It contains only the `cli/`
subpackage. This is critical for PEP 420 namespace packages to work
— adding an `__init__.py` here would make `duecare` a regular package
and break the seven sibling packages.

### 2. The CLI is `duecare.cli`, not `duecare`

`from duecare.cli import app` works; `from duecare import app` does not
and should not. Keeping `duecare` as a namespace means every sibling
contributes its own subpackage cleanly.

### 3. Typer + rich for the CLI

Typer gives us declarative subcommands and auto-generated help. Rich
gives us pretty tables for `agents list`, `models list`, etc.
Neither is load-bearing — a fallback to argparse + plain print would
work too.

## Tests

6 tests passing:

- `forge --help` exits cleanly
- `forge agents list` shows all 12 agents
- `forge models list` shows all 8 adapters
- `forge tasks list` shows all 9 tasks
- `forge domains list` works even with no domains
- `duecare status` emits a status table without crashing

## Status

- [x] Meta package depends on all 7 siblings
- [x] `duecare` CLI entry point via `[project.scripts]`
- [x] 10 CLI commands implemented
- [x] 6 tests passing
- [x] Wheel built + installed
- [x] End-to-end `duecare run rapid_probe` verified against the trafficking domain

## License

MIT.
