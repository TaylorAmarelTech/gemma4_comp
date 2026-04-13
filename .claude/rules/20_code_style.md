# Code style — Python conventions for the Duecare codebase

> Auto-loaded at the project memory level. Applies to every `.py` file
> under `src/forge/` and `packages/duecare-llm-*/`.

## Language and tooling

- **Python 3.11+** (3.11 is the floor; newer is fine). Matches the
  existing author framework and lets us use modern syntax.
- **Pydantic v2** for all data models. Never Pydantic v1, never
  dataclasses when a Pydantic model would be right.
- **`typing.Protocol`** for cross-layer interfaces, not ABCs. Protocols
  are duck-typed and don't force plugins into an inheritance hierarchy.
- **Type hints on every function signature.** `ruff` + `mypy` enforce
  this. No untyped public APIs.
- **`from __future__ import annotations`** at the top of every module
  so type hints are strings, not evaluated at import time.
- **`pathlib.Path`** for every file path. Never bare strings for paths.

## Naming

- `PascalCase` for classes
- `snake_case` for functions, methods, variables
- `UPPER_SNAKE_CASE` for constants
- `_leading_underscore` for private helpers
- Enum values are stable strings — never refactor them casually; they
  end up in database rows and published datasets

## Imports

- **One top-level import per logical group**, blank line between groups:
  stdlib, third-party, local (`forge.*`)
- **Never import from siblings at the same layer.** Cross-layer imports
  flow downward only: `duecare.agents` → `duecare.tasks` → `duecare.core`, never
  the reverse. If you feel the urge to import "up", the type you want
  belongs in `duecare.core`.
- **Never import concrete classes across layers.** Use protocols from
  `duecare.core.contracts`. `duecare.agents.judge` may depend on `Model`,
  but not on `TransformersModel`.

## Functions

- **Pure by default.** A function should return something; side effects
  (file writes, DB writes, HTTP calls) are explicit and documented in
  the docstring.
- **Short.** Aim for <50 lines. If it's longer, split.
- **Docstrings for every public function.** One-line summary + args +
  returns + raises.
- **Keyword-only arguments for anything optional.** Use `*,` to force
  the caller to name them.

## Error handling

- **Fail fast, fail loud.** No silent drops, no bare `except:`, no
  catching `Exception` except at a clearly-documented boundary.
- **Pydantic `ValidationError`** is the contract: if a schema boundary
  receives bad data, it raises, and the caller decides whether to
  retry, quarantine, or abort.
- **Never log PII in an exception message.** Exceptions should describe
  the error type, not the offending content.

## Testing

- **Every module has a `tests/` folder with at least one real test.**
  "Placeholder test" files are fine as scaffolding but should be
  replaced as soon as there's behavior to test.
- **Use pytest**, not unittest.
- **Fixtures in `conftest.py`** per test folder.
- **Mock external I/O** (network, filesystem writes in unit tests).
  Integration tests hit real SQLite + small real fixtures.

## The "never" list

- Never use `os.path` when `pathlib` is available
- Never `print()` in library code; use `structlog` via
  `duecare.observability.logging`
- Never write to `sys.stderr` directly from library code
- Never block on synchronous I/O in an async function
- Never swallow an exception to "keep the pipeline running"; quarantine
  the item and re-raise or bubble
- Never use `tempfile` without a cleanup (`with tempfile.TemporaryDirectory():`)
- Never commit code that doesn't pass `ruff check` and `mypy`
- Never assume a dict key exists; use `.get()` or a Pydantic model
- Never write a helper function that takes 5+ positional arguments; use
  a Pydantic config model instead
