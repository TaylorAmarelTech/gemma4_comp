# Root File Policy

This file explains why the repository root still contains more than a
minimal `README.md` and `LICENSE`. The rule is simple: root files must be
entry points, repository configuration, deployment contracts, or attribution
records that external tools expect at the top level. Longer narrative docs
belong under `docs/`; active implementation helpers belong under `scripts/`;
one-off historical helpers belong under `_archive/`.

## Public Entry Points

| File | Purpose |
|---|---|
| `README.md` | Primary GitHub landing page and judge quick path. |
| `launch.py` | The one intentional root-level Python entry point: `python launch.py` starts the right surface for each audience (see `docs/QUICK_LAUNCH.md`). Root placement is the point -- a launcher a first-time reader has to hunt for is not a launcher. Implementation helpers still belong in `scripts/`. |
| `LICENSE` | MIT license text expected by GitHub and package consumers. |
| `CITATION.cff` | Citation metadata rendered by GitHub. |
| `CHANGELOG.md` | Human-readable release and submission history. |
| `CODE_OF_CONDUCT.md` | GitHub community health file. |
| `CONTRIBUTING.md` | Contributor and review workflow guidance. |
| `SECURITY.md` | Security reporting and privacy posture. |
| `RESULTS.md` | Provenance table for headline metrics cited by the README and docs site. |
| `LICENSES.md` | Competition-facing attribution and license summary. |
| `THIRD_PARTY_LICENSES.md` | Dependency-level attribution referenced by the README. |
| `ROOT_FILES.md` | This root-file manifest and cleanup policy. |

## Agent And Review Context

| File | Purpose |
|---|---|
| `AGENTS.md` | Repository-level AGENTS.md instructions for AI coding tools. |
| `CLAUDE.md` | Slim Claude Code project index pointing to the tracked `docs/CLAUDE_CODE_HANDOFF.md`. |
| `PROJECT_BIBLE.md` | Root pointer to the tracked closeout handoff and deeper `docs/codex/PROJECT_BIBLE.md` history. |
| `Plans.md` | Compatibility bridge for older Claude Code handoffs that pointed at `Plans.md`; redirects to the Project Bible and pause-safe improvement loops. |
| `harness.toml` | Local harness policy source of truth. |
| `.mcp.json.example` | Optional MCP server template. |
| `.mcp.json` | Empty local MCP config shell; no secrets. |
| `repomix.config.json` | Context-pack configuration for code review tools. |
| `.aider.conf.yml` | Ollama-cloud coding-harness config (architect/editor models). See `docs/ollama_coding_harness.md`. |
| `.aider.model.metadata.json` | Context/cost metadata for the harness models (zero-cost; suppresses Aider billing warnings). |
| `.aider.model.settings.yml` | Per-model edit-format / repo-map settings for the harness models. |

## Build, Test, And Deploy Contracts

| File | Purpose |
|---|---|
| `pyproject.toml` | Python workspace, package, and test configuration. |
| `Makefile` | Common local validation and demo commands. |
| `requirements.txt` | Baseline runtime dependency list for simple installs. |
| `requirements-docs.txt` | Documentation site dependency list. |
| `.pre-commit-config.yaml` | Local pre-commit hook configuration. |
| `.dockerignore` | Docker build context filter. |
| `Dockerfile` | Main container build contract. |
| `Dockerfile.demo` | Lightweight demo container build contract. |
| `Dockerfile.dev` | Development container build contract. |
| `docker-compose.yml` | Local baseline stack. |
| `docker-compose.auth.yml` | Local authenticated stack overlay. |
| `docker-compose.dev.yml` | Development stack overlay. |
| `docker-compose.enterprise.yml` | Enterprise-style local stack overlay. |
| `render.yaml` | Render deployment blueprint for the public hub. |
| `mkdocs.yml` | Documentation site configuration. |
| `robots.txt` | Public crawler policy for deployed static surfaces. |

## Environment Templates

| File | Purpose |
|---|---|
| `.env.example` | Safe local environment template. |
| `.env.enterprise.example` | Safe enterprise deployment template. |

Actual `.env` files are ignored and must stay local.

## What Should Not Be Added At Root

- New narrative markdown files. Put them in `docs/` and link them from
  `docs/REPO_LAYOUT.md` or another purpose map.
- One-off migration, copy, or repair scripts. Put active helpers in
  `scripts/`; archive obsolete helpers under `_archive/`.
- Generated databases, logs, reports, notebook byproducts, caches, model
  weights, local replay JSON, or temporary exports.

## Local Files You May See But Should Not Commit

These are already ignored by `.gitignore`: `.env`, `.venv/`, `.duecare*/`,
`.pytest*/`, `.tmp/`, `_local_tmp/`, `debug.log`, `*.duckdb`,
`*.duckdb.wal`, `build/`, `dist/`, and local wheel-test folders.
