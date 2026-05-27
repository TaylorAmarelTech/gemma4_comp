# Local test environment — corruption + one-command recovery

> **TL;DR.** The system Python under this OneDrive-synced repo gets corrupted by
> sync. Do not fight it. Run **`pwsh scripts/recover_test_env.ps1 -Run`** — it
> builds a clean, uv-managed Python *outside* OneDrive, installs the
> known-working pinned deps, and runs the grading suite. Verified green:
> **408 grading tests passed (2026-05-27, Python 3.12.13).**

## The problem

This repository lives under `C:\Users\…\OneDrive\Documents\gemma4_comp`. OneDrive
file-sync intermittently **corrupts the system Python install** by stripping
files out from under it — and not just packages. During the 2026-05-27 episode
the following were missing, discovered one layer at a time:

| Missing | Layer |
|---|---|
| `typing_extensions` | pure-Python dependency |
| `pydantic_core._pydantic_core` | **compiled** extension (`.pyd`) |
| `pydantic.main` | pure-Python dependency |
| `html.entities` | **Python standard library** |

Once the **standard library itself** is Swiss-cheesed, the interpreter cannot
import the app (`duecare.chat.app`) or run `pytest`, and there is no way to fix
it by shadowing individual packages — you cannot predict which stdlib files are
gone. `pip` is also broken (its own `pip._vendor` is stripped), so you cannot
simply reinstall.

This is the same breakage `CLAUDE.md` records as "Local pip + venv currently
broken (OneDrive-sync corruption)". `scripts/verify_knowledge_surfaces.py` works
around it with pure-stdlib parsing; **this** doc is the fix for actually running
pytest.

## The fix: an isolated interpreter outside OneDrive

`scripts/recover_test_env.ps1` builds a Python interpreter that OneDrive cannot
touch, then runs the tests in it. Everything it creates lives under
`%LOCALAPPDATA%\gemma4-testenv\` (which is **never synced**) — nothing is written
into the repo:

```
%LOCALAPPDATA%\gemma4-testenv\
├── uv\uv.exe          # standalone uv (downloaded if not already on PATH)
└── venv\              # clean venv built from a uv-MANAGED CPython (intact stdlib)
```

What the script does, in order:

1. **Ensure `uv`.** Uses `uv` on `PATH` if present; otherwise downloads the
   standalone Windows binary from the official GitHub release. `uv` is a single
   Rust binary and does **not** depend on the broken system `pip`.
2. **Download a managed CPython** with `--python-preference only-managed`. This
   is a fresh interpreter with an **intact standard library** — never the
   corrupted system Python (uv will otherwise reuse the system one).
3. **Create a clean venv outside OneDrive** and `uv pip install` the pinned
   deps from [`requirements-testenv.txt`](../requirements-testenv.txt).
4. **Verify** the interpreter imports `html.entities` (a stdlib module the
   corruption ate) plus the fastapi/pydantic stack.
5. With `-Run`, **run the grading suite** with the `duecare` PEP 420 namespace
   `packages/*/src` roots on `PYTHONPATH`.

### Usage

```powershell
# Build / refresh the clean interpreter:
pwsh scripts/recover_test_env.ps1

# Build (if needed) and run the grading test suite:
pwsh scripts/recover_test_env.ps1 -Run

# The venv itself got corrupted (it can, if ever placed under OneDrive) —
# nuke and rebuild from scratch:
pwsh scripts/recover_test_env.ps1 -Regenerate -Run

# Run a custom set of tests:
pwsh scripts/recover_test_env.ps1 -Run -Tests packages/duecare-llm-chat/tests/test_compare.py
```

The script is **idempotent** — re-run it any time. `-Regenerate` is the
"redownload known-good packages and regenerate the venv" recovery path.

## Known-working pins

[`requirements-testenv.txt`](../requirements-testenv.txt) holds the direct,
top-level pins. The set verified green on 2026-05-27:

| Package | Version |
|---|---|
| pytest | 9.0.3 |
| pytest-timeout | 2.4.0 |
| fastapi | 0.136.3 |
| httpx | 0.28.1 |
| python-multipart | 0.0.29 |
| jinja2 | 3.1.6 |
| pydantic | 2.13.4 |
| pydantic-core (resolved) | 2.46.4 |
| starlette (resolved) | 1.1.0 |
| typing-extensions (resolved) | 4.15.0 |

This is a **test/dev** interpreter — it deliberately installs only the light
deps the grading + harness tests need (fastapi, pydantic, httpx, …), **not**
torch/transformers/unsloth. The grading logic is pure Python; tests inject fake
`model_call`s, so no GPU stack is required. For full model runs, boot via Kaggle
(see [`.claude/rules/83_kaggle_workflow.md`](../.claude/rules/83_kaggle_workflow.md)).

## Why not just fix the system Python?

You can (`py -3.12 -m ensurepip` + reinstall, or reinstall Python), but OneDrive
will eventually corrupt it again because the repo + any venv inside it are
synced. Keeping the interpreter in `%LOCALAPPDATA%` (outside the synced tree) is
the durable fix. If you prefer a system-wide repair, also consider moving the
repo out of OneDrive or excluding it from sync.

## Scope this verifies

The default `-Run` target is the grading + harness suite that exercises the
timeout caps, resumable grading, judge-fingerprint cache key, and
single-dimension grading integrity:

```
packages/duecare-llm-chat/tests/test_compare.py
packages/duecare-llm-chat/tests/test_harness_behavior.py
packages/duecare-llm-chat/tests/test_harness_v3_6.py
packages/duecare-llm-chat/tests/test_benchmark.py
packages/duecare-llm-chat/tests/test_design_tooltip_migration.py
tests/test_route_contract.py
```
