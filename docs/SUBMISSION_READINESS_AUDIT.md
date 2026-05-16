# Submission readiness audit — 2026-05-10

This audit tracks the cleanup pass requested after the archive transition and install/deployment hardening work. It is intentionally focused on active submission surfaces, not archived notebooks or private reference data.

## Scope

Reviewed active repo state for:

- setup and deployment truthfulness
- stale command references
- package inventory consistency
- active Kaggle kernel validation policy
- public privacy/messaging guardrails
- archive boundary consistency

Out of scope unless explicitly restored:

- `_archive/legacy-research-2026-05-09/`
- `_archive/legacy_src/`
- `_reference/`
- root `legacy_notebooks/` mirrors
- root `skunkworks/` mirrors

## Fixed in this pass

| Area | Fix |
|---|---|
| Package build order | `scripts/build_all_wheels.py` now includes `duecare-llm-benchmark` and `duecare-llm-chat`, bringing the default build list to all 17 package directories. |
| Wheel build verification | `scripts/build_all_wheels.py` now checks critical `duecare-llm-domains` wheel contents after builds and fails if required domain pack files are missing or duplicated. |
| Prompt truthfulness | `COPILOT_AUTONOMOUS_PROMPT.md` now uses the current date instead of stale T-9 wording, removes unsupported bare `+56pp` success language, and marks roadmap deployment surfaces as roadmap unless runnable. |
| Notebook validation wording | `.pre-commit-config.yaml` and `CLAUDE.md` now say active Kaggle kernels must parse instead of implying root legacy notebooks are the validation target. |
| Package demo notebook link | `docs/components/duecare_llm_core.md` now points to the active `kaggle/kernels/duecare_010_quickstart/010_quickstart.ipynb` notebook instead of deleted root `legacy_notebooks/`. |
| Deployment docs | `deployment/README.md` documents the validated private compose path, hardware guidance, secrets rules, and roadmap boundaries. |
| Package inventory | `docs/PACKAGE_INVENTORY.md` records all 17 package names, versions, scripts, extras, and current install truth. |
| Domains wheel packaging | `packages/duecare-llm-domains/pyproject.toml` no longer force-includes domain data a second time; rebuilt wheel contains required domain pack files with no duplicate zip entries. |
| Chat package versioning | `duecare-llm-chat` is documented as intentionally independent on the v0.14.x harness cadence instead of a mistaken version drift. |
| Model import safety | `duecare-llm-models` no longer requires optional Ollama HTTP dependencies at import time; `OllamaModel` lazy-loads `httpx` only when the Ollama adapter is used. |
| Public doc count clarity | `docs/writeup_draft.md` and `docs/FOR_KAGGLE_JUDGES.md` now distinguish the 13 final submission notebooks from the broader 49 public-live research kernels and 77 tracked kernels. |
| Repo cleanup | Older generic HF Spaces deployment notes, old handoff prompt docs, the legacy notebook prompt ladder, and stale checkpoint/action-list docs were moved to `_archive/cleanup-2026-05-10/`; active `hf_space/` and `hf-space/` folders remain because they serve different Spaces. |

## Validation results from this pass

| Check | Result |
|---|---|
| Python syntax compile | Passed for touched setup/build/server/test files. |
| Consumer setup dry-run | Passed; no packages, models, or launchers were installed/written in dry-run mode. |
| Targeted pytest | Passed: 8 passed, 2 skipped for setup, server smoke, and Kaggle notebook utility tests. |
| Public messaging validator | Passed. |
| Public-surface audit | Passed: 4 checks, 0 findings; report includes the 2 skipped allowlisted drift files. |
| Active Kaggle notebook validator | Passed: 77 notebooks parsed successfully. |
| Enterprise compose config | Passed for the base stack and the monitoring profile using `.env.enterprise.example`. |
| Wheel build | Passed locally with `--no-isolation`: all 17 wheels built in `dist/readiness-wheels/` and critical domains-wheel contents verified. |
| Domains wheel integrity | Passed: required trafficking/tax/financial-crime domain data present, 0 duplicate zip entries. |
| Clean-env CLI install | Passed with `virtualenv`: installed `duecare-llm-cli` from local wheels, ran `duecare --help`, `duecare init`, and `duecare demo-stage`. |
| Clean-env meta install | Passed with `virtualenv`: installed `duecare-llm` from local wheels, ran `duecare --help` and `duecare domains list`. |
| Clean-env workflow run | Passed with `virtualenv`: installed `duecare-llm` from local wheels plus PyPI dependencies, ran `duecare run rapid_probe --target-model local_smoke --domain trafficking` against a local OpenAI-compatible fake backend, and completed scout → judge → historian with `status=completed`. |
| Models import safety | Passed: targeted test proves `import duecare.models` succeeds when `httpx` is intentionally unavailable; existing meta CLI smoke tests still pass. |
| Prompt-count provenance | Passed: `configs/duecare/domains/trafficking/seed_prompts.jsonl` contains 74,567 lines; README now labels this as the repo-config corpus, not the lightweight PyPI wheel bundle. |
| Writeup word count | Passed: `scripts/v141_word_count.py docs/writeup_draft.md` reports 992 counted body words / 1,500 cap. |

## Current known findings

| Severity | Finding | Current action |
|---|---|---|
| Low | `duecare run rapid_probe` is validated end-to-end against a local OpenAI-compatible fake backend; real Gemma/Ollama/API runs still require the corresponding target-model backend and credentials/model files. | Document backend setup clearly; keep `duecare-llm-cli` as the simplest demo bootstrap and present `duecare-llm` as the workflow CLI for configured model backends. |
| Medium | Some older docs still discuss Helm, SSO/SAML, mobile LiteRT, browser extensions, or channel integrations. Some are valid roadmap docs; some may overclaim if quoted in public-facing summary pages. | Keep these as roadmap unless validated; prioritize README/FOR_KAGGLE_JUDGES/writeup/rubric docs for final polish. |
| Low | Root legacy/skunkworks deletions are intentional but create a large git status. | `.gitignore` and docs explain that root mirrors are no longer active. Final commit should make this obvious in the commit message. |

## Validation commands to keep green

Python/setup:

```powershell
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe -m py_compile scripts/setup_consumer.py scripts/build_all_wheels.py packages/duecare-llm-server/src/duecare/server/__init__.py tests/test_setup_consumer.py packages/duecare-llm-server/tests/test_smoke.py
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/setup_consumer.py --dry-run --source local --mode desktop
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe -m pytest tests/test_setup_consumer.py packages/duecare-llm-server/tests/test_smoke.py tests/test_kaggle_notebook_utils.py -q
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe -m pytest packages/duecare-llm-models/tests/test_import_safety.py packages/duecare-llm/tests/test_cli_smoke.py -q
```

Public surface:

```powershell
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/validate_public_messaging.py
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/validate_public_surface.py
```

Notebook metadata/JSON:

```powershell
c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/validate_notebooks.py
```

Compose/deployment:

```powershell
docker compose --env-file .env.enterprise.example -f docker-compose.enterprise.yml config
docker compose --env-file .env.enterprise.example -f docker-compose.enterprise.yml --profile monitoring config
```

## Next recommended fixes

1. Repeat the 17-wheel build in a clean environment before claiming final PyPI release readiness; build a complete dependency wheelhouse first if a no-index/offline install is required.
2. Keep Kaggle publishing manual: prepare copy/paste content and dry-run checks only.
