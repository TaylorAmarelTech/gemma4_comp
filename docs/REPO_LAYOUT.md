# Repo layout — what lives where

> One-screen map of every top-level directory. If you opened this repo
> cold, read this first. For deeper context see [`README.md`](../README.md)
> + [`CLAUDE.md`](../CLAUDE.md).

## Active competition surfaces (the things judges see)

| Path | Purpose | Status |
|---|---|---|
| [`apps/duecare-ai.com/`](../apps/duecare-ai.com/) | The public coordination hub. FastAPI + Jinja templates. CPU-only, no Gemma inference. Renders + serves the website at [duecare-ai.com](https://duecare-ai.com) (currently [gemma4-comp.onrender.com](https://gemma4-comp.onrender.com)) via Render auto-deploy from `master`. | Live |
| [`packages/`](../packages/) | 17 PyPI packages under the `duecare` namespace (PEP 420). The *source of truth* for the wheels that Kaggle script kernels install. Each subfolder is one publishable package. The chat playground lives at `packages/duecare-llm-chat/`. | Live |
| [`kaggle/`](../kaggle/) | Everything prepared for manual Kaggle publication — 3 core + 22 appendix script-kernel folders (numbered `01-`, `02-`, `03-`, `A-01-`..`A-22-`), per-folder wheels, datasets, and root metadata. Former generated/research notebook mirrors now live under `_archive/kaggle-notebook-previews-2026-05-11/`; older 52/74/77-kernel notes are historical archive context. Source of truth: [`kaggle/_INDEX.md`](../kaggle/_INDEX.md). | Live |
| [`hf_space/`](../hf_space/) | Hugging Face Space for the **Harness Chat** Space. CPU-only (cloud-Gemini API). Separate from `hf-space/`. | Live |
| [`hf-space/`](../hf-space/) | Hugging Face Space for the **Live Demo** Space. CPU-only. Separate from `hf_space/`. The naming convention (underscore vs hyphen) is unfortunate; both are real and serve different demo URLs. | Live |
| [`docs/`](../docs/) | Submission writeup + video script + judge guides + per-component design docs + cleanup/readiness notes. The single most important judge-facing path here is `docs/FOR_PEER_REVIEW.md`. Old handoff and prompt-ladder docs are archived under `_archive/cleanup-2026-05-10/`. | Live |
| [`render.yaml`](../render.yaml) | Repo-root Render Blueprint. Render reads this to deploy `apps/duecare-ai.com/` from `master` on every push. | Live |

## Supporting infrastructure

| Path | Purpose |
|---|---|
| [`infra/`](../infra/) | Multi-cloud deployment recipes (AKS / AWS / Azure / EKS / Fly / GCP / GKE / Helm) for self-hosting the hub or the wheel runtime. Each subfolder is one cloud target. |
| [`deployment/`](../deployment/) | Validated private compose support files plus channel-specific helpers (Discord bot, Telegram bot, browser extension). Roadmap features must stay labeled unless freshly validated. |
| [`configs/`](../configs/) | YAML configuration: model registry, workflows, domain packs (trafficking + tax_evasion + financial_crime). |
| [`scripts/`](../scripts/) | Implementation + maintenance scripts (notebook builders, polish passes, validators). 200+ files; run individually as needed. |
| [`tests/`](../tests/) | Repo-wide integration tests (notebook utilities, kaggle-folder layout, etc.). Per-package unit tests live inside each `packages/duecare-llm-*/tests/`. |
| [`Makefile`](../Makefile) | Common entry points: `make test`, `make demo`, `make build`. |
| [`docker-compose*.yml`](../docker-compose.yml), [`Dockerfile*`](../Dockerfile) | Three flavors: prod (`docker-compose.yml`), dev (`docker-compose.dev.yml`), auth-enabled demo (`docker-compose.auth.yml`). |
| [`mkdocs.yml`](../mkdocs.yml) | MkDocs config for the docs site (separate from the website hub at `apps/duecare-ai.com/`). |

## Data + reference

| Path | Purpose |
|---|---|
| [`data/`](../data/) | Curated public-source corpora, multimodal test sets, generated training data. Some subdirs are gitignored (raw / processed / interim). 1657 tracked files. |
| [`examples/`](../examples/) | Runnable deployment and embedding examples. Start with [`examples/README.md`](../examples/README.md). |
| `_reference/` | **Gitignored.** The author's proprietary 21K-test trafficking benchmark + framework. Do not commit. |
| `evidence_raw/` | **Gitignored.** Raw evidence assets that have not been redacted yet. |

## Research mirrors + archive

| Path | Purpose |
|---|---|
| [`_archive/legacy-research-2026-05-09/`](../_archive/legacy-research-2026-05-09/) | Archived legacy local notebook mirrors plus skunkworks experiments. Out of default review scope; restore only for historical context, provenance checks, or migration work. |
| [`_archive/`](../_archive/) | Dated snapshots of superseded folders (`data_generated_2026-04/`, `docs_2026-04/`, `hub_first_pass_2026-05/`, `legacy_src/`, `notebooks_2026-04/`, `reports_2026-04/`, `scripts_one_off_2026-04/`, `tests_2026-04/`). Frozen for audit; do not modify. |
| [`_archive/cleanup-2026-05-10/`](../_archive/cleanup-2026-05-10/) | Non-destructive cleanup archive for stale HF Spaces deployment notes and old handoff prompts moved out of active docs. |
| `dist/`, `build/` | **Gitignored.** Build artifacts. |
| `release/duecare_demo_v1/` | An older release artifact bundle. Likely stale; review before next push. |
| `raw_python/` | **Gitignored.** Per-component source files Kaggle deliverables are built from. Contains hardcoded API keys. |

## Standard repo files

| Path | Purpose |
|---|---|
| [`README.md`](../README.md) | Project overview for visitors. ~40 KB; the front door. |
| [`CLAUDE.md`](../CLAUDE.md) | AI-assistant context (loaded by Claude Code automatically). |
| [`CHANGELOG.md`](../CHANGELOG.md) | Versioned changelog. |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md) | How to contribute. |
| [`CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) | Community standards. |
| [`SECURITY.md`](../SECURITY.md) | Security policy + vulnerability reporting. |
| [`LICENSE`](../LICENSE) | MIT. |
| [`LICENSES.md`](../LICENSES.md) | Per-asset license attribution (synthetic images, RAG corpus sources, etc.). |
| [`CITATION.cff`](../CITATION.cff) | How to cite this work. |
| [`pyproject.toml`](../pyproject.toml) | uv workspace root + project metadata. |
| [`requirements.txt`](../requirements.txt), [`requirements-docs.txt`](../requirements-docs.txt) | Pip-style requirement pins for environments that don't use uv. |
| [`copy_framework.py`](../copy_framework.py), [`copy_reference.py`](../copy_reference.py) | One-shot helpers that populate `_reference/` from the author's external source folder. Documented in CLAUDE.md. |
| [`robots.txt`](../robots.txt) | Top-level robots policy referenced by `apps/duecare-ai.com/render.yaml`. |
| [`repomix.config.json`](../repomix.config.json) | Repomix config for one-shot codebase exports. |

## Hidden / dev-only

| Path | Purpose |
|---|---|
| [`.github/`](../.github/) | Issue + PR templates, 7 CI workflows: `ci.yml`, `claude.yml`, `docker-publish.yml`, `docs-deploy.yml`, `helm-publish.yml`, `pypi-publish.yml`, `release.yml`. |
| [`.claude/`](../.claude/) | Claude Code project rules (auto-loaded) + slash-command definitions. The 7 rules under `.claude/rules/*.md` are the enforced project conventions. |
| [`.devcontainer/`](../.devcontainer/) | VS Code dev-container spec. |
| [`.vscode/`](../.vscode/) | Editor config (gitignored except for shared settings). |
| `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | **Gitignored.** Local tool caches. |
| `.duecare/`, `apps/duecare-ai.com/.duecare/` | **Gitignored.** Hub runtime data (signal intake JSONL + healthcheck). |
| `.env` | **Gitignored.** Local API keys + secrets. Use `.env.example` as the template. |
| [`.mcp.json`](../.mcp.json), [`.mcp.json.example`](../.mcp.json.example) | Claude Code MCP server config. |
| [`.dockerignore`](../.dockerignore) | Build-time exclusions. |

## Where to start, by role

- **Hackathon judge / first-time visitor**: [`README.md`](../README.md) → [`docs/FOR_PEER_REVIEW.md`](./FOR_PEER_REVIEW.md) → live demo at [gemma4-comp.onrender.com](https://gemma4-comp.onrender.com) → core Kaggle script kernels at [`kaggle/01-duecare-exploration-workbench/`](../kaggle/01-duecare-exploration-workbench/) and [`kaggle/02-live-demo/`](../kaggle/02-live-demo/).
- **Developer integrating the API**: [`docs/FOR_KAGGLE_JUDGES.md`](./FOR_KAGGLE_JUDGES.md) → [`apps/duecare-ai.com/app/main.py`](../apps/duecare-ai.com/app/main.py) → [`apps/duecare-ai.com/app/hub_client.py`](../apps/duecare-ai.com/app/hub_client.py) (reference client protocol).
- **Wheel re-user**: `pip install duecare-llm` → [`packages/duecare-llm/`](../packages/duecare-llm/) (meta package) → individual sub-packages.
- **Operator running their own hub**: [`apps/duecare-ai.com/README.md`](../apps/duecare-ai.com/README.md) + [`apps/duecare-ai.com/docs/RENDER.md`](../apps/duecare-ai.com/docs/RENDER.md) + [`infra/`](../infra/) for non-Render targets.
- **AI assistant picking up the project**: [`CLAUDE.md`](../CLAUDE.md) + [`.claude/rules/*.md`](../.claude/rules/) + current root continuation prompts when present. Historical handoff prompts live in `_archive/cleanup-2026-05-10/docs_handoff_prompts/`.
