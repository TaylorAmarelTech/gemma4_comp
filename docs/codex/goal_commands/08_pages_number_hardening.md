# GitHub Pages and magic-number hardening

Use this when the project needs same-day GitHub Pages launch pressure plus a
continued polish pass that avoids fragile public metrics and hard-coded counts.

This is intentionally a long-form instruction file. The `/goal` objective
should reference this file instead of pasting the full text, because `/goal`
objectives have a 4,000 character limit.

## Copy-paste `/goal`

```text
/goal In C:\Users\amare\OneDrive\Documents\gemma4_comp, work on master without switching branches and follow docs/codex/goal_commands/08_pages_number_hardening.md. Same-day priority: get GitHub Pages enabled/deploying for the project docs, or report the exact GitHub/token/settings blocker with evidence. Continue Kaggle-safe polish, remove fragile public magic numbers unless a generated artifact or validation contract owns them, keep active Kaggle kernel.py files compatible, run the documented gates, commit only scoped fixes, push, and report Pages status, CI status, Kaggle readiness, changed files, tests, and unresolved risks.
```

## Mission

Launch or unblock GitHub Pages as the top operational priority, while continuing
source-first polish that makes DueCare read as a portable Gemma 4 ecosystem.

The public story should emphasize:

- many local deployments can process sensitive worker-support material locally
- reviewed deployments can anonymize fact objects, graph edges, risk signals,
  benchmark rows, and knowledge-pack updates
- shared intelligence should not centralize raw worker files, PII, secrets, or
  volatile legal claims
- metrics are useful only when tied to generated artifacts, validation scripts,
  or dated run bundles

## Read first

1. `AGENTS.md`
2. `docs/codex/README.md`
3. `docs/codex/00_do_not_break.md`
4. `docs/codex/00_kernel_compatibility_gate.md`
5. `docs/codex/00_execution_order.md`
6. `docs/codex/goal_commands/07_verification_showcase_hardening.md`
7. current `git status --short --branch`
8. current GitHub Actions and Pages status via `gh`

Do not switch branches. Do not edit active published Kaggle `kernel.py` files
unless a proven blocking bug requires it and every main Kaggle gate passes
afterward.

## GitHub Pages priority

Same-day goal: make the docs site publish from GitHub Pages.

1. Inspect `.github/workflows/` for the docs deploy workflow.
2. Run or rerun the docs build locally if practical.
3. Push scoped fixes before judging remote deployment.
4. Use `gh run list`, `gh run view`, and `gh run watch` to inspect the latest
   docs deploy run.
5. If deploy fails because Pages is disabled, try the narrow GitHub API enable
   path for workflow-built Pages. If the token lacks permission or the repo
   setting blocks it, capture the exact error and final manual setting URL.
6. Do not claim the site is published until the deploy action succeeds or the
   Pages URL returns the built site.

## Magic-number and metric discipline

Avoid fragile hard-coded public counts in narrative docs. Prefer:

- `200+ prompt proxy rubric` instead of exact prompt counts in prose
- `nearly all checked prompts` instead of exact helped/hurt counts in prose
- `current generated report` or `docs/harness_lift_data.json` for exact counts
- `100+ GREP rules` and `50+ RAG documents` unless runtime inventory is rendered
  by code
- `smoke / proxy evidence` for current harness-lift numbers
- `live Gemma outputs required` before claiming production traceability,
  long-run reliability, field performance, or weeks-long model behavior

Exact numbers are acceptable inside generated artifacts such as
`docs/harness_lift_report.md`, `docs/harness_lift_data.json`, coverage tables,
or validation scripts when the generator or test owns the update path.

## Polish scope

Continue source-first improvements to:

- `docs/index.md`, install/onboarding docs, press/reproducibility docs, and
  scenario pages
- `packages/duecare-llm-chat` workbench pages and README surfaces
- benchmark docs/scripts where they help users start without paid/live calls
- portable local-node onboarding for Kaggle judges, NGOs/regulators,
  researchers, developers, integrators, and benchmark users

Keep the six public setup lanes exactly:

1. Platform safety
2. NGO & regulator
3. Individual worker / mobile
4. Researcher
5. Anonymized knowledge sharing
6. Developer / integration partner

## Verification

Run the smallest relevant scope plus public/Kaggle gates:

```powershell
python scripts/validate_main_kaggle_kernels.py
python scripts/validate_kaggle_page_sources.py
python scripts/validate_public_surface.py
python scripts/validate_public_messaging.py
python scripts/validate_benchmark.py
python -m pytest packages --collect-only -q
```

Also run focused tests for changed package code. For docs-only edits, still run
the public surface/link and messaging validators.

Before commit:

```powershell
git diff --check
git status --short --branch
```

Commit and push only scoped files. Do not stage unrelated deletions, generated
cache/data removals, archived notebook churn, or user changes.

## Final report

Report:

- GitHub Pages result and URL, or exact remaining blocker
- latest GitHub Actions status for docs deploy, CI, and contract checks
- Kaggle compatibility gates
- public metric/magic-number cleanup performed
- changed files and commit/push hash
- unrelated dirty worktree risks left untouched
