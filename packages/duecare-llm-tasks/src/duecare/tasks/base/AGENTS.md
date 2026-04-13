# Agent instructions — Base

> If you are an AI assistant inspecting this folder, start here.

## What this module does

Helpers shared by all tasks (fresh_task_result, etc.)

See `PURPOSE.md` for the full description.

## How to read this folder

- `PURPOSE.md` — short + long description
- `INPUTS_OUTPUTS.md` — context keys / protocols this module reads + writes
- `HIERARCHY.md` — parent, siblings, children, dependencies
- `DIAGRAM.md` — local position in the system
- `TESTS.md` — how to run tests, what each test validates
- `STATUS.md` — current completion state and TODO list
- Source files: __init__.py, base.py
- `tests/` — isolated tests for this module

## How to modify this module safely

1. Read `PURPOSE.md` and `INPUTS_OUTPUTS.md` to understand the contract.
2. Look at `tests/` to see what's currently verified.
3. Check `HIERARCHY.md` to see what depends on this module.
4. Make the change.
5. Run `duecare test src/forge/tasks/base` to verify.
6. If the test suite passes, the change is safe.

## Do NOT

- Add dependencies on concrete classes from sibling modules
- Break the protocols declared in `src/forge/core/contracts/`
- Remove or rename public symbols without updating `HIERARCHY.md`
- Log or persist PII under any circumstance

## How to navigate up or down

- Up one level: see `../AGENTS.md`
- Top of the tree: see `src/forge/AGENTS.md`
- Full system overview: see `docs/the_forge.md`
