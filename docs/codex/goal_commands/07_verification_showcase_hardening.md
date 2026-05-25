# Verification, path tracing, and Gemma 4 showcase hardening

Use this when the implementation looks feature-complete but the local Python
environment, runtime smoke coverage, manual route tracing, or submission
showcase still needs deeper proof.

This is intentionally a long-form instruction file. The `/goal` objective
should reference this file instead of pasting the full text, because `/goal`
objectives have a 4,000 character limit.

## Copy-paste `/goal`

```text
/goal In C:\Users\amare\OneDrive\Documents\gemma4_comp, work on master without switching branches and follow docs/codex/goal_commands/07_verification_showcase_hardening.md. Run the verification-first environment hardening, runtime smoke tests, manual path tracing, and Gemma 4 ecosystem showcase review described there. Do not stop for ordinary failures; diagnose, repair, rerun, and continue. Stop only for required approval, destructive actions, secrets risk, or unsafe user-change conflict. Commit and push only scoped fixes; if no fixes are needed, do not commit. Final report must include env details, pass/fail table, path-tracing findings, showcase/design findings, push status, blockers, and Kaggle readiness.
```

## Mission

Run a no-routine-stop DueCare verification, environment hardening, manual
path-tracing, and Gemma 4 showcase polish pass.

This repo is for a Kaggle / Gemma 4 competition submission. The product should
showcase a coherent Gemma 4 ecosystem for migrant-worker safety, including:

- exploration workbench
- live demo and recording path
- hierarchical evidence graph extraction
- templates
- knowledge extraction
- search
- anonymization and sharing
- universal LLM benchmarking
- Kaggle Community Benchmark readiness
- standardized packaging and setup paths for different user groups
- portable, copyable local-node processes for Kaggle judges, NGOs/regulators,
  individual worker/mobile use, researchers, developers/integrators, and
  benchmark users
- GitHub-facing onboarding instructions and showcase surfaces
- GitHub Pages that presents DueCare as a true Gemma 4 ecosystem: many local
  nodes can anonymize and share fact objects, graph edges, and aggregate
  intelligence without centralizing raw worker files

Do not pause for ordinary test failures, missing packages, broken local Python
installs, import errors, route smoke failures, or UI inconsistencies. Diagnose,
repair, rerun, and continue.

Pause only for:

- required approval to install or download dependencies
- destructive filesystem actions
- credential, token, or secrets exposure risk
- a user change that makes safe continuation impossible

## Read first

Read these before making changes:

1. `AGENTS.md`
2. `docs/codex/README.md`
3. `docs/codex/00_do_not_break.md`
4. `docs/codex/00_kernel_compatibility_gate.md`
5. `docs/codex/00_execution_order.md`
6. `docs/codex/01_next_phase_kaggle_surface_goals.md`
7. `docs/REPO_LAYOUT.md` if present
8. `docs/FILE_PURPOSE_GUIDE.md` if present
9. `kaggle/_INDEX.md` if present
10. Goal handoffs for Goals 11 through 15

Preserve approved DueCare wording unless a source-level contradiction requires
a narrow correction.

The public setup lanes are exactly six, in this order:

1. Platform safety
2. NGO & regulator
3. Individual worker / mobile
4. Researcher
5. Anonymized knowledge sharing
6. Developer / integration partner

Do not add unsupported "local" claims. Do not use the word "substrate" in
public submission copy. Prefer "worker support", "anonymized knowledge
sharing", and "content moderation" where applicable.

## Environment hardening

Audit Python with:

```powershell
py -0p
where python
where py
python --version
py -3.12 --version
```

Avoid Python 3.14. Prefer Python 3.12 because current Kaggle docker-python
templates use Python 3.12 paths.

Create a fresh isolated verification environment outside the repo:

```text
C:\tmp\gemma4_comp_py312_venv
```

Do not delete or mutate the existing repo `.venv` unless explicitly necessary
and approved.

If `py -3.12 venv` or pip is broken:

1. Try `ensurepip` and pip repair inside the new venv.
2. Try `uv` if available.
3. Try another clean Python 3.12 provision path if available.
4. Use Python 3.13 only as a fallback and label it non-Kaggle-parity.

Install only dependencies needed for verification. Inspect repo
`pyproject.toml`, `setup.py`, `setup.cfg`, and requirements files. Install
editable local packages as needed. Prefer a reproducible command log and avoid
global installs. If network or package download is required, request escalation
and continue after approval.

## Runtime verification

Run these from the clean verification environment:

```powershell
python scripts/validate_main_kaggle_kernels.py
python scripts/validate_kaggle_page_sources.py
python scripts/validate_public_surface.py
python -m pytest packages --collect-only -q
python -m pytest packages/duecare-llm-chat/tests/test_benchmark.py -q
python -m pytest packages/duecare-llm-chat/tests/test_process_bulk_review.py -q
python -m pytest packages/duecare-llm-server/tests/test_slides_surface.py -q
```

Also run any additional targeted tests implicated by Goals 11 through 15 or by
files changed during this pass.

## Runtime smoke tests

Run `kaggle/03-universal-llm-benchmark/kernel.py` offline without live paid API
calls, writing output only under `C:\tmp`. Verify:

- `results.json` exists
- `calls.jsonl` exists
- `summary.md` exists
- `report.html` exists
- test API-key strings are not persisted in generated artifacts
- single-target config remains backward compatible
- multi-target config produces per-target summaries

Run `kaggle/04-kaggle-community-benchmark/kernel.py` local preview under
`C:\tmp`. Verify:

- schema is `duecare.kaggle_community_benchmark.v3`
- execution mode is `local_preview_no_model`
- no Kaggle model proxy call is made
- fee-limit coverage is present
- corridor coverage is present
- assertion cap is respected
- judge availability is explicit
- registration notes separate manual and automated steps

If practical, start the relevant FastAPI app locally on an alternate port and
smoke key routes without live model calls.

## Manual path tracing

Trace Kernel 01 startup from:

```text
kaggle/01-duecare-exploration-workbench/kernel.py
```

Follow it into install/bootstrap, static serving, these pages, and their
backend endpoints:

- `/static/process.html`
- `/static/knowledge.html`
- `/static/search.html`
- `/static/share.html`
- `/static/templates.html`
- relevant `/api/process`, `/api/knowledge`, `/api/search`, `/api/templates`,
  and `/api/share` endpoints

Trace Bulk File Review from upload/job creation through:

- deterministic extraction
- linking
- case brief
- hierarchical Gemma graph pass
- media pass
- artifact writing
- UI progress logs
- export and replay surfaces

Confirm `gemma_case_brief` is not described as per-document, per-page, or
per-paragraph analysis. Confirm the hierarchical pass is the specific-level
node/edge path across folder, document, page, paragraph/chunk, table row,
extracted image/media item, person/case, and rollup levels.

Trace Knowledge Extraction, Search, Anonymization & Sharing, and Templates
from frontend controls through backend endpoints and artifacts. Confirm each
page visibly shows:

- progress
- activity logs
- replay/export artifacts
- trust boundaries

Trace Kernel 02 startup from:

```text
kaggle/02-live-demo/kernel.py
```

Follow it into:

- `/start`
- `/slides`
- `/slides/setup`
- cached replay APIs
- recording pack APIs
- workbench links

Trace Kernel 03:

- `/api/catalog`
- `/api/run`
- `/api/jobs/{job_id}`
- `/api/runs/{run_id}`
- `/api/runs/{run_id}/download/{name}`

Verify single-target backward compatibility and multi-target behavior from
source.

Trace Kernel 04:

- `read_seed_rows`
- coverage-balanced row selection
- kbench task wrappers
- `local_preview`
- `write_report`
- registration guidance

For every traced path, record source file/function references, expected
inputs/outputs, and any mismatch between docs, UI text, logs, and backend
behavior.

## Gemma 4 ecosystem showcase review

Review whether the submission clearly communicates that Gemma 4 is used across
a coherent safety workbench, not as a single chatbot demo.

Check that Bulk File Review emphasizes hierarchical Gemma node/edge creation
across:

- folder
- document
- page
- paragraph/chunk
- table row
- extracted image/media item
- person/case
- rollup levels

Check that Knowledge Extraction, Search, Templates, and Anonymization &
Sharing show how extracted graph/evidence artifacts become reusable knowledge,
case materials, safer search, and shareable redacted outputs.

Check that Kernel 02 recording pages explain the six-lane story and route
viewers into the strongest workbench pages.

Check that optional Kernel 03 and Kernel 04 benchmarks read as evaluation proof
surfaces, not as the main recording path.

Review whether the repository itself helps different users get started without
copying private local assumptions. Look for concrete improvement opportunities
across:

- Kaggle judges copying `kernel.py` from the active folders
- NGO / regulator reviewers using the live demo or a local workbench
- individual worker / mobile users who need a private first-run path
- developers installing the packages and running targeted tests
- benchmark users running the universal LLM benchmark or Kaggle Community
  Benchmark without paid/live model calls
- researchers exploring reusable evidence, template, graph, and anonymization
  artifacts
- packageable local-node processes that can be repeated in different
  deployments without relying on Taylor's machine, local virtualenv, secrets,
  or current Cloudflare tunnel

Identify places where packaging could be more standard across these use cases:

- package names, extras, CLI entrypoints, and README install commands
- local development versus Kaggle copy-paste versus published wheel paths
- shared sample data, replay artifacts, and no-secrets test fixtures
- clear boundaries between active submission kernels, optional benchmarks,
  archived notebooks, and reusable Python packages
- versioned artifacts and release notes that would help users reproduce a demo

Review the GitHub onboarding surface. If gaps are found, prefer improving or
proposing small, durable docs rather than adding a new top-level surface unless
the purpose map is updated. Check:

- root `README.md`
- `kaggle/_INDEX.md`
- `docs/REPO_LAYOUT.md`
- `docs/FILE_PURPOSE_GUIDE.md`
- package READMEs for the primary install/run/test paths
- scripts that validate public docs and Kaggle copy-paste contracts

Consider whether the project should add or strengthen a GitHub Pages-style
showcase that helps users understand and start the project from GitHub. Treat
this as an opportunity review unless the fix is obviously small and low-risk.
Any GitHub Pages recommendation should preserve the Kaggle judging path and
should explain:

- what the public page would show first
- how it links to the active Kaggle kernels and live demo
- how it points developers to package install and test commands
- how it presents DueCare as an ecosystem of components, not a single chatbot
- how local nodes can anonymize case material into shareable fact objects and
  graph evidence without exposing raw worker files
- how aggregated, anonymized fact objects from many trusted local nodes can
  improve intelligence against trafficking and recruitment-abuse patterns
- how different user groups can start from portable packages, scripts,
  validation commands, and sample artifacts instead of one-off notebook state
- how it avoids raw PII, secrets, volatile legal claims, and unverified metrics
- whether it can reuse existing static/site assets instead of creating a
  separate marketing-only page

Improve copy only where it makes the Gemma 4 ecosystem more concrete, more
specific, and more truthful. Do not inflate claims beyond verified source
behavior.

## Layout, formatting, and design consistency

Keep shared workbench chrome as the owner of model loading:

- `packages/duecare-llm-chat/src/duecare/chat/static/_nav.html`
- `packages/duecare-llm-chat/src/duecare/chat/static/_nav.js`
- `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css`

Do not add per-page model-loading popovers.

Adopt consistent section hierarchy, card density, button language, progress
boxes, activity-log placement, export/replay affordances, and trust-boundary
callouts across:

- `process.html`
- `knowledge.html`
- `search.html`
- `share.html`
- `templates.html`
- `compare.html`
- `status.html`

Preserve route names, DOM IDs, localStorage keys, activity-log handles, sample
artifact paths, API endpoint contracts, and Kaggle boot tokens.

Avoid marketing-only pages. The first screen should expose usable workbench or
demo functions.

Use restrained, utilitarian SaaS/workbench styling:

- dense but organized information
- predictable navigation
- clear progress
- clear tables
- clear artifacts

Avoid decorative gradient/orb/bokeh backgrounds, one-note palettes, oversized
hero sections on workbench pages, nested cards, and UI text that explains
obvious controls.

Keep cards at 8px radius or less unless existing CSS already differs. Avoid
cards inside cards. Keep page sections full-width or unframed except for
repeated items, modals, and actual tool panels.

Ensure text does not overflow or overlap on desktop/mobile. Do not scale font
size with viewport width. Letter spacing should be 0, not negative.

Use existing icons/libraries if already present. Do not introduce a new icon
system unless necessary.

For every UI edit, inspect surrounding patterns first and reuse existing
classes/components before adding new ones.

## Safety and repo constraints

Keep root `kaggle/` layout clean:

- active `01` and `02`
- optional `03` and `04`
- no root `A-*` folders
- no extra root `04-*` snapshots

Appendix/archive notebooks under `kaggle/_archive` are provenance only unless
explicitly requested.

Do not stage unrelated dirty deletions, generated data, wheels, untracked
notebooks, `.claude` folders, raw PII, secrets, Kaggle tokens, or unredacted
logs.

Do not hardcode volatile hotlines, fee caps, wage rules, office names, URLs, or
legal claims into model outputs unless they exist as versioned knowledge
objects.

If adding any top-level directory, Kaggle kernel, package surface, or
long-lived public doc, update the relevant purpose map:

- `README.md`
- `kaggle/_INDEX.md`
- `docs/REPO_LAYOUT.md`
- `docs/FILE_PURPOSE_GUIDE.md`

## Fix and commit policy

If tests, smoke tests, manual tracing, or showcase review reveal defects, fix
them narrowly.

After every fix:

1. Rerun the smallest failing check.
2. Rerun the main kernel gate.
3. Rerun the page-source gate when pages or benchmark kernels changed.

Commit and push only scoped code/docs changes. If no code changes are needed,
do not create a commit.

Continue until:

- the clean verification environment works
- runtime gates have been run
- manual path tracing is complete
- showcase/design issues are either fixed or documented with exact
  file/function references
- the repo is ready to test in Kaggle, or the remaining blocker is exact and
  external

## Final report requirements

The final report must include:

- Python executable used
- environment creation and install commands
- verification pass/fail table
- runtime smoke-test results
- manual path-tracing findings
- Gemma 4 ecosystem showcase findings
- UI/layout consistency findings
- packaging and GitHub onboarding findings
- GitHub Pages / public showcase recommendation, if applicable
- commits and push status
- unresolved blockers
- whether the repo is ready to test in Kaggle
