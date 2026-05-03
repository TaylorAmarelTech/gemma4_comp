# AGENTS — guidance for AI assistants working on `duecare.evidence`

This file is the standards-compliant agentic-AI contract for the **Evidence** module. Tools that read AGENTS.md natively (Claude Code, Cursor, Copilot, Windsurf, Aider, Zed, Warp, RooCode) will pick this up automatically.

## What this module is

See [`PURPOSE.md`](PURPOSE.md) for the one-line + long-form description.

## How to work on this module

- **Read order:** `PURPOSE.md` → `INPUTS_OUTPUTS.md` → `HIERARCHY.md` → source files → `tests/`
- **Tests:** see [`TESTS.md`](TESTS.md). Every behavior-bearing function should have at least one test.
- **Cross-module imports:** flow downward only (`duecare.agents` → `duecare.tasks` → `duecare.core`). Never import siblings at the same layer; never import upward.
- **Style:** see `.claude/rules/20_code_style.md` at the repo root. Pydantic v2, `typing.Protocol` for contracts, `pathlib.Path` for paths.
- **Privacy gate:** see `.claude/rules/10_safety_gate.md`. No raw PII may flow through this module.

## Public API

Exports are defined in `__init__.py`. Import from `duecare.evidence` (the module path), not from internal submodules.
