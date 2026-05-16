# Claude Code Continuation Prompt: DueCare Cleanup, Polish, Alignment

## Mission

You are continuing autonomous cleanup and polish work on **DueCare**, the Gemma 4 Good Hackathon submission in this repository.

Current date: **2026-05-10**. Submission deadline: **2026-05-18**.

The goal is not to add speculative features. The goal is to make the existing project **consistent, truthful, runnable, validated, and submission-ready** across:

- public website / FastAPI hub
- Kaggle notebooks and kernels
- PyPI package workspace
- deployment examples
- setup scripts
- documentation
- public-surface audits
- repository hygiene

Every action should advance at least one of the hackathon rubric goals:

1. **Impact & Vision** — DueCare protects migrant workers with private, local-first AI safety tooling.
2. **Video Pitch & Storytelling** — polished components create clean demo material later.
3. **Technical Depth & Execution** — repository must be real, reproducible, and not faked for a demo.

## Operating Principle

Polish what exists before inventing new surfaces.

Prefer:

- small, high-confidence fixes
- truthful documentation
- runnable examples
- validation gates
- consistency across names, commands, routes, package docs, and notebook text

Avoid:

- speculative architecture
- adding large new features without tests
- overclaiming production readiness
- touching archived notebooks or private references
- auto-publishing to Kaggle or any public service

## Critical Project Rules

### Archive boundaries

Do **not** read, review, lint, summarize, regenerate, or validate these archive/private folders unless Taylor explicitly asks for historical context or restore work:

- `_archive/legacy-research-2026-05-09/`
- `_archive/legacy_src/`
- `_reference/`
- root `legacy_notebooks/` if regenerated locally
- root `skunkworks/` if regenerated locally

Active notebook work is under:

- `kaggle/kernels/`
- `kaggle/datasets/`
- `kaggle/models/`
- notebook builder scripts under `scripts/`

### Manual Kaggle publishing

Do **not** push, publish, upload, create, or rewrite Kaggle assets automatically.

Allowed by default:

- local edits
- validation scripts
- dry-runs
- copy/paste-ready metadata or instructions
- link checklists

Taylor handles Kaggle UI publishing manually unless explicitly saying to publish/push/upload.

### No PII / no secrets

Do not commit or generate raw PII, credentials, API keys, real names, phone numbers, addresses, passport IDs, or case-specific sensitive data.

Use composite names only when clearly labeled as composites. Public NGO names are okay.

Concrete privacy wording is preferred:

> Raw worker chats, IDs, contact details, and private documents stay on the worker device or inside the private deployment unless the user explicitly creates an authorized sanitized submission.

Avoid vague slogans like “privacy is non-negotiable” unless immediately backed by concrete data-flow details.

## Current Known State

Recent cleanup and hardening work already happened:

- `CLAUDE.md` documents archive boundaries and manual Kaggle publishing.
- Root legacy notebook mirrors and skunkworks were moved out of active scope.
- Notebook validation treats `kaggle/kernels/` as authoritative.
- `scripts/validate_public_surface.py` prints skipped allowlisted files and has tighter drift allowlist behavior.
- `scripts/validate_public_messaging.py` is wired into public validation flows.
- `.gitignore` ignores root `legacy_notebooks/`, root `skunkworks/`, `.env.enterprise`, `.env.enterprise.local`, `.claude/sessions/`, and nested app-local `.claude/` state.
- `scripts/setup_consumer.py` exists and uses the actual CLI flow:
  - `duecare init`
  - `duecare demo-stage`
  - `duecare serve --port 8080`
- `docker-compose.enterprise.yml` exists and is tied to checked-in deployment config files.
- `deployment/docker/api.Dockerfile` exists for the enterprise compose stack.
- `deployment/nginx/nginx.enterprise.conf` exists with local HTTP reverse proxy, TLS guidance, and security headers.
- `deployment/monitoring/` contains Prometheus and Grafana starter configs.
- `.env.enterprise.example` exists and should stay trackable; real `.env.enterprise` files must remain ignored.
- `packages/duecare-llm-server/src/duecare/server/__init__.py` exports `ServerState` because `duecare serve` imports it.
- `tests/test_setup_consumer.py` covers setup dry-run, model manifest, launcher command, and local source resolution.
- `scripts/build_all_wheels.py` includes all 17 package directories in its default build order.
- Local 17-wheel build passes with `--no-isolation`; clean-environment build/install validation remains a release gate.
- `duecare-llm-cli` isolated install from local wheels passes for `duecare --help`, `duecare init`, and `duecare demo-stage`.
- `duecare-llm` isolated install from local wheels passes for `duecare --help`, `duecare domains list`, and end-to-end `duecare run rapid_probe` against a local OpenAI-compatible fake backend; real Gemma/Ollama/API runs still need their configured backends.
- `duecare-llm-models` lazy-loads the optional Ollama HTTP dependency so `import duecare.models` works without `httpx` unless the Ollama adapter is actually used.
- Version policy decision: infrastructure packages remain `0.1.0`; `duecare-llm-chat` intentionally keeps its v0.14.x harness cadence and should be called out in release notes.
- `deployment/README.md` documents the current private compose path, hardware guidance, and roadmap boundaries.
- `docs/PACKAGE_INVENTORY.md` records package names, versions, scripts, and extras.
- `docs/SUBMISSION_READINESS_AUDIT.md` tracks cleanup findings and remaining release decisions.

Validation recently run successfully:

```powershell
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe -m py_compile scripts/setup_consumer.py packages/duecare-llm-server/src/duecare/server/__init__.py tests/test_setup_consumer.py packages/duecare-llm-server/tests/test_smoke.py
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/setup_consumer.py --dry-run --source local --mode desktop
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe -m pytest tests/test_setup_consumer.py packages/duecare-llm-server/tests/test_smoke.py -q
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/validate_public_messaging.py
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/validate_public_surface.py
docker compose --env-file .env.enterprise.example -f docker-compose.enterprise.yml config
docker compose --env-file .env.enterprise.example -f docker-compose.enterprise.yml --profile monitoring config
```

## Actual CLI Reality

Do not invent CLI commands.

The checked-in CLI package is `duecare-llm-cli` and exposes:

```text
duecare init
duecare doctor
duecare demo-stage
duecare serve
duecare moderate
duecare worker
```

There is no known supported `duecare start` command. If docs mention `duecare start`, fix them or confirm a real implementation exists before keeping the reference.

The aspirational meta-package story may be `pip install duecare-llm`, but the currently reliable install story for the CLI is:

```text
pip install duecare-llm-cli
duecare init
duecare demo-stage
duecare serve --port 8080
```

## First Things To Do

Start by inspecting the current worktree without dumping huge diffs:

```powershell
git status -sb
git status --short --untracked-files=normal
```

Then review only focused diffs for active files you intend to touch. Avoid full diffs that include archived/deleted notebooks.

Recommended path-limited checks:

```powershell
git diff -- .gitignore CLAUDE.md README.md docs kaggle scripts packages tests deployment docker-compose.enterprise.yml .env.enterprise.example COPILOT_AUTONOMOUS_PROMPT.md CLAUDE_CODE_CONTINUATION_PROMPT.md
```

## Priority Work Queue

### P0 — Repository hygiene and truthfulness

- Ensure no local agent state is untracked or accidentally commit-ready.
- Ensure real env files are ignored and example env files are trackable.
- Ensure docs and prompts do not reference nonexistent commands, nonexistent files, or unvalidated production claims.
- Replace overclaims with validated wording.
- Confirm archive policy is consistent across `CLAUDE.md`, `README.md`, `docs/REPO_LAYOUT.md`, `kaggle/README.md`, and prompt files.

### P0 — Validation gates

Run targeted validation after every meaningful edit:

```powershell
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe -m py_compile <touched-python-files>
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe -m pytest <targeted-tests> -q
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/validate_public_messaging.py
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/validate_public_surface.py
```

If notebook-related files changed, also run:

```powershell
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/validate_notebooks.py
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe -m pytest tests/test_kaggle_notebook_utils.py -q
```

If compose/deployment files changed, validate config only unless explicitly asked to build/start:

```powershell
docker compose --env-file .env.enterprise.example -f docker-compose.enterprise.yml config
docker compose --env-file .env.enterprise.example -f docker-compose.enterprise.yml --profile monitoring config
```

Do not run real publish commands.

### P1 — Setup and deployment polish

Review and improve these files for consistency, clarity, and correctness:

- `scripts/setup_consumer.py`
- `tests/test_setup_consumer.py`
- `docker-compose.enterprise.yml`
- `.env.enterprise.example`
- `deployment/docker/api.Dockerfile`
- `deployment/nginx/nginx.enterprise.conf`
- `deployment/monitoring/prometheus.yml`
- `deployment/monitoring/alert-rules.yml`
- `deployment/monitoring/grafana/**`

Look for:

- command references matching actual CLI
- no secret leakage
- no fake production claims
- accurate healthcheck paths (`/healthz` for the DueCare server)
- local-first raw-data policy in wording
- tests for setup behavior
- compose config validation

### P1 — Cross-component terminology

Scan active public files for inconsistent terminology:

- `DueCare`
- `Duecare`
- `duecare`
- `Gemma 4`
- `Gemma4`
- `SuperGemma`

Recommended standard:

- **DueCare** for product/project prose.
- `duecare` for CLI/import/package namespace.
- **Gemma 4** for the model family.
- Avoid introducing `SuperGemma` unless it is already a named artifact in the validated notebooks/docs and is clearly defined.

### P1 — Public docs consistency

Polish active public docs:

- `README.md`
- `docs/FOR_KAGGLE_JUDGES.md`
- `docs/writeup_draft.md`
- `docs/rubric_alignment.md`
- `docs/REPO_LAYOUT.md`
- `docs/deployment_modes.md`
- `kaggle/README.md`
- `apps/duecare-ai.com/README.md`
- package READMEs under `packages/*/README.md`
- `docs/PACKAGE_INVENTORY.md`
- `docs/SUBMISSION_READINESS_AUDIT.md`

Check for:

- dead internal links
- stale counts
- stale paths
- stale commands
- vague privacy language
- conflicting Kaggle instructions
- references to archived notebooks as active surfaces

### P1 — Package consistency

There are 17 workspace packages. Do not assume there are only 7 packages.

Check:

- package versions
- package descriptions
- CLI entry points
- optional extras names
- namespace package imports
- dependency references matching actual package names

If you touch package metadata, run targeted package/build validation where feasible.

### P2 — Web/dashboard polish

If working on the website or FastAPI hub:

- keep the UI intentional, not generic
- prefer concrete deployment/story copy
- avoid unsafe HTML injection
- preserve existing tests
- validate routes with existing public-surface audit

Active website reference:

- `apps/duecare-ai.com/app/main.py`
- `apps/duecare-ai.com/README.md`
- `src/demo/`

### P2 — Notebook polish

If working on notebook builders or generated notebooks:

- prefer editing builder scripts, then regenerating notebooks
- never truncate displayed prompt/response text that readers need to understand
- prefer shared display helpers in `scripts/_notebook_display.py`
- keep Kaggle-safe HTML only
- validate with `scripts/validate_notebooks.py`
- do not touch archived notebook mirrors by default

## Definition of Done For This Session

A good continuation session ends with:

- specific files polished or fixed
- no new fake/unvalidated claims
- no raw PII or secrets introduced
- no accidental archive/private-folder work
- targeted tests passing
- public messaging/surface gates passing if public files changed
- compose config checks passing if compose/deployment files changed
- concise summary of what changed and what still needs Taylor’s decision

## Final Response Format

When finished, report briefly:

1. What was changed.
2. What validations passed.
3. Any non-blocking follow-ups.

Do not include huge diffs or paste full files unless asked.
