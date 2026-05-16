# Migration note: harness/ (singular) vs harnesses/ (plural)

This note explains the dual naming you will see in the codebase and
which one to use for new work. Written 2026-05-13 after the Phase 0-15
harness refactor.

## TL;DR

| Need | Use |
|---|---|
| Kernel boot / Gemma call wiring / default safety layers | `from duecare.chat.harness import default_harness, GREP_RULES, ...` |
| New FastAPI surface / new safety task / per-task training data | `from duecare.chat.harnesses import <name>` |

Both packages coexist. The plural one is the new pattern; the singular
one is the legacy implementation that all current kernels still depend
on. Do NOT delete the singular module -- many files import from it.

## What changed in Phase 0-15

Before the refactor, `app.py` was a single 5,474-line FastAPI module
with every route inline plus the safety layer dispatch. The legacy
`harness/__init__.py` (singular) held the data (rule definitions,
corpus, tool implementations).

After the refactor, six FastAPI surfaces live in folder modules under
`harnesses/` (plural):

```
packages/duecare-llm-chat/src/duecare/chat/harnesses/
|-- __init__.py            registry: PRIMARY + SECONDARY tuples
|-- base.py                HarnessBase Protocol + opt-in class
|-- _layers.py             compose_layers(app, text, layers=...)
|-- _training_log.py       log_interaction(harness, input, output, ...)
|-- chat/                  full multimodal orchestrator
|-- process/               batch + graph-chat
|-- extraction/            KnowledgeObject drafter
|-- anonymization/         PII gate (regex-only)
|-- import_corpus/         user-attached evidence CRUD
`-- search/                SearXNG + legacy backends
```

Each harness exports `name`, `applied_layers`, `consumes`, `emits`,
`capabilities`, `register_routes(app)` plus optional `tools.py` /
`knowledge.py` / `evaluation.py` / `prompts.py` modules.

A symmetric pattern was applied on the hub side at
`apps/duecare-ai.com/app/harnesses/` (3 PRIMARY + 2 SECONDARY).

## Naming convention

| Term | Refers to |
|---|---|
| **harness module** | A subfolder under `harnesses/<name>/` |
| **safety layer** | One callable in `applied_layers` (persona/grep/rag/tools/online) |
| **Duecare framework** | The whole thing |

Avoid `the harness` alone -- it is ambiguous.

## Adding a new safety task today

```bash
mkdir packages/duecare-llm-chat/src/duecare/chat/harnesses/my_new
```

Then write `__init__.py`:

```python
from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits

name = "my_new"
applied_layers = ("grep", "rag")
capabilities = ()
```

Plus `handler.py` with `register_routes(app)`, `prompts.py` for any
Gemma calls, `knowledge.py` declaring `EMITS` / `CONSUMES` from the
live KO taxonomy. The contract tests
(`tests/test_harness_imports.py`) enforce the shape.

Full 10-step recipe + contract details: [harness_pattern.md](harness_pattern.md).

## Backward compatibility

Every kernel currently in `kaggle/` continues to work without changes.
They all import `default_harness()` and `create_app()` the same way.
The new harness modules are wired transparently inside `create_app`.

## Tests that guard the contract

| File | What it pins |
|---|---|
| `tests/test_route_contract.py` | every (path, method) on the kernel app |
| `tests/test_harness_imports.py` | Assertions across the kernel harness contracts |
| `tests/test_compose_layers.py` | unit tests for the shared layer composer |
| `tests/test_multi_harness_integration.py` | extract -> anonymize -> submit chain |
| `tests/test_per_harness_tools.py` | tool spec shape per harness |
| `tests/test_hub_harness_imports.py` | hub-side contract (5 harnesses) |
| `tests/test_hub_sentinel.py` | sentinel endpoints + admin gating |
| `tests/test_end_to_end_flywheel.py` | sentinel -> curator -> sync flywheel |

Total: 76 cross-cutting tests, CI-enforced via
`.github/workflows/contract.yml`.
