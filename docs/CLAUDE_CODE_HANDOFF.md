# Claude Code Handoff

This is the durable, tracked pickup document for Claude Code and other coding
agents taking over DueCare during the closeout period.

**Prepared:** 2026-07-28

**Target human handoff:** 2026-08-25

**Repository branch:** `master`
**Default model posture:** whole model/flywheel stack cost-stopped; zero planned
model calls

This file records repository truth and safe next actions. It is not proof of
live Git, process, provider, Kaggle, Render, or GitHub state. Re-run the checks
below in the current checkout. Saved `.claude/state/` files and ignored reports
are historical evidence only.

## Read Order

1. Root [`AGENTS.md`](../AGENTS.md) for active surfaces, safety rules, and the
   required validation ladder.
2. This handoff for the closeout state and immediate pickup sequence.
3. Root [`PROJECT_BIBLE.md`](../PROJECT_BIBLE.md) for the canonical handoff map.
4. [`MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md) for human operations,
   recovery, access transfer, and acceptance.
5. [`PROJECT_TRANSITION_PLAN.md`](PROJECT_TRANSITION_PLAN.md) for the dated
   closeout and maintenance-mode fallback.
6. [`PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md) for the bounded
   release claim and intentionally red training lane.
7. [`CLOSEOUT_RESOLUTIONS_2026_07_28.md`](CLOSEOUT_RESOLUTIONS_2026_07_28.md)
   for the final item-by-item disposition and claim boundaries.
8. [`DEFERRED_WORK.md`](DEFERRED_WORK.md) for genuinely reopened work; it
   contains zero current items at this handoff.
9. [`codex/PROJECT_BIBLE.md`](codex/PROJECT_BIBLE.md) only when deeper benchmark,
   dataset, or autonomous-engine history is needed.

Root [`Plans.md`](../Plans.md) exists only as a compatibility bridge for older
Claude Code handoffs. It is not a second planning source. The auto-loaded
[`05_project_bible_pickup.md`](../.claude/rules/05_project_bible_pickup.md)
preserves the same boundary.

## First 30 Minutes

Use Python 3.12 with the repository development dependencies. These commands
are read-only or validation-only and make no model call:

```powershell
git status --short --branch
git log -5 --oneline
$env:DUECARE_MAX_PLANNED_MODEL_CALLS = '0'
python scripts/validate_maintainer_handoff.py
python scripts/validate_deferred_work.py
python scripts/validate_publication_readiness.py --scope handoff
python scripts/validate_publication_readiness.py --scope core
python scripts/validate_project_bible_pickup.py
python scripts/autonomous_engine.py --status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/stop_ollama_stack.ps1 -Status
```

Then run the smallest tests for the files you will touch. Before publishing a
current package-test claim, run:

```powershell
python -m pytest packages --collect-only -q
```

Do not reuse the counts in this document as proof for a later revision.

## Current Repository Truth

- `master` is the active branch. Always start from live Git; do not reset or
  erase a dirty worktree merely because a handoff expected it to be clean.
- The immediate fully merged predecessor to this maintenance closeout is pull
  request [#16](https://github.com/TaylorAmarelTech/gemma4_comp/pull/16), merge
  commit `1c8f6b25729da869b2775a29321ab3b74bd4715f`. Its 16 checks passed. This
  immutable predecessor receipt is historical context, not a substitute for
  `git rev-parse HEAD` or the checks on live `master`.
- The model-free core publication scope is green at the recorded revision. The
  strict training scope remains intentionally red and excluded from closeout
  claims; a future reopen requires source, rights, lineage, diversity, privacy,
  and independent-adjudication gates to close.
- The generated deferred-work register contains 0 items. All 11 inherited
  items have explicit dated outcomes in the closeout receipt: completed cycle,
  decided, declined, excluded, current-owner retention, or retained risk.
- Maintenance mode is effective 2026-07-28. No release tag, package/model/data
  publication, notebook rerun, new training claim, human study, or private
  account transfer was performed merely to close the queue.

## Public Services Kept Running

| Surface | Current role | Ownership boundary |
|---|---|---|
| [duecare-ai.com](https://duecare-ai.com/) | Render-hosted FastAPI website and mutable public hub APIs | `apps/duecare-ai.com/`, root `render.yaml`, and Render remain production; the app does not load Gemma |
| [Read-only continuity site](https://tayloramareltech.github.io/duecare-ai-site/) | Backend-free copy of all 51 public routes plus five allowlisted snapshots | Separate `TaylorAmarelTech/duecare-ai-site` Pages repository; forms, accounts, automation, mutable APIs, private submissions, admin state, and raw logs are disabled or excluded |
| [GitHub Pages documentation](https://tayloramareltech.github.io/gemma4_comp/) | MkDocs onboarding, operations, architecture, and evidence | This monorepo's `.github/workflows/docs-deploy.yml` is its only Pages deployer |
| [Source repository](https://github.com/TaylorAmarelTech/gemma4_comp) | Canonical code, templates, docs, validators, and workflows | Changes flow through reviewed `master` revisions |

Render and the production DNS remain active. The continuity repository omits a
`CNAME` and must not claim `duecare-ai.com`. It builds from public `master`
daily, on a source-repository dispatch, or from an explicitly pinned public
source ref. Its machine-readable receipt is the
[`static/snapshots/manifest.json`](https://tayloramareltech.github.io/duecare-ai-site/static/snapshots/manifest.json)
file; compare `source_revision` with the intended source commit.

If Render is ever retired, follow
[`apps/duecare-ai.com/DEPLOY_STATIC.md`](../apps/duecare-ai.com/DEPLOY_STATIC.md).
A root-domain cutover requires explicit approval, a root-path build, live crawl,
HTTPS/DNS verification, and a tested rollback. Do not make that cutover as an
incidental documentation change.

## Recent Closeout Receipts

The final model-free sequence was intentionally split into reviewable changes:

| Pull request | Merge receipt | Outcome |
|---|---|---|
| [#11](https://github.com/TaylorAmarelTech/gemma4_comp/pull/11) | `3daa8988` | Added and validated the 51-page backend-free continuity export; created the independent Pages deployment without changing Render or DNS |
| [#12](https://github.com/TaylorAmarelTech/gemma4_comp/pull/12) | `c728c06c` | Polished mobile website navigation and refreshed both website builds |
| [#13](https://github.com/TaylorAmarelTech/gemma4_comp/pull/13) | `47277c62` | Put the optional adverse-media verifier behind the shared atomic provider budget; all five registered transports are covered |
| [#14](https://github.com/TaylorAmarelTech/gemma4_comp/pull/14) | `a56f9d1b` | Fixed the homepage worker-story grid by placing title and body inside `.step-copy`; Render and the continuity site were visually and structurally verified |
| [#15](https://github.com/TaylorAmarelTech/gemma4_comp/pull/15) | `56e7283d` | Cleared the registered three-file Ruff slice without suppressions and reduced the deferred register from 12 to 11 items |
| [#16](https://github.com/TaylorAmarelTech/gemma4_comp/pull/16) | `1c8f6b25` | Finalized the Claude Code handoff, read-only continuity plan, public pickup validation, and pre-closeout reconciliation |

The PR #15 local receipt was `4,646 passed, 9 skipped` for
`python -m pytest packages tests -q`. The source CI matrices, clean-room install,
harness anti-regression, privacy scan, active Kaggle contract, package build,
and container build also passed. No Ollama or hosted-model call was made for
these closeout changes.

The 2026-07-28 maintenance candidate passed `4,653 passed, 9 skipped` for the
same broad command in 8 minutes 4 seconds under
`DUECARE_MAX_PLANNED_MODEL_CALLS=0` and offline provider/model flags. This is
the current local receipt. The earlier `4,648 passed` tracked-handoff result and PR
#15's 4,646-pass result remain dated history.

The homepage layout regression has an explicit acceptance check: live and
fallback HTML must contain `class="step-copy"`, must not contain the old sibling
`<div class="step-title">` structure, and must use a
`28px minmax(0, 1fr)` grid. That prevents the body from being auto-placed into
the narrow number column.

## Active, Optional, And Historical Surfaces

- Primary Kaggle source surfaces are exactly
  `01-duecare-exploration-workbench`, `02-live-demo`, and
  `A-00-omni-experiment-workbench`.
- `03-universal-llm-benchmark` and `04-kaggle-community-benchmark` are optional
  and do not become part of the primary proof path without an explicit decision.
- Notebook-era material under `kaggle/_archive/` is provenance, not a current
  blocker. Do not restore archived root variants merely to increase surface
  count.
- The propose-only entity-intelligence pipeline is separate from live worker
  advice, GREP/RAG, and accepted training data. Curator review is mandatory
  before promotion.
- The default comparable benchmark board remains v1/h1 batched evidence.
  Per-dimension, v2, h2, and benign-control evidence stays isolated unless a
  new versioned board is deliberately completed.

Kaggle execution status is volatile. Use the current status tools and report
`CANCEL_ACKNOWLEDGED` as canceled, not successful. Do not spend Kaggle or model
quota merely to refresh a status badge.

## Model And Ollama Boundary

The expected closeout posture is:

- all five recurring tasks disabled;
- four daemon stop sentinels present;
- zero verified repository daemon processes;
- `DUECARE_MAX_PLANNED_MODEL_CALLS=0` during deterministic maintenance; and
- no removal of a sentinel, scheduler re-enable, provider credential use, or
  model call without explicit current authorization and a finite reviewed
  budget.

The shared ledger covers four primary `llm_generate.py` transports plus the
optional adverse-media verifier. It reserves attempts, input tokens, output
tokens, and reviewed cash allowance before transport. It is not a universal
network interceptor for every adapter or self-contained notebook. Follow
[`PROVIDER_BUDGETING.md`](PROVIDER_BUDGETING.md) and migrate any remaining
direct caller one bounded transport at a time.

Future model comparison work must make testing **Kimi K3** and
**Meta Muse Spark 1.1** a first-class requirement. Reverify immutable provider
identifiers, access, context limits, modalities, and pricing immediately before
the run. If either lane is unavailable, retain dated provider evidence rather
than silently substituting another model. Start with a tiny frozen text slice,
finite attempt/token/cash ceilings, content-addressed caches, exact prompt and
rubric hashes, and a stop-on-error policy. Stage multimodal comparisons
separately.

The later 2026-07-28 Kimi K3 access check reached Ollama with the verified
`kimi-k3` ID, but all five budgeted attempts returned HTTP 402 for empty extra
usage. It produced zero completions, provider tokens, or actual ledger cost.
Treat the model lane as access-blocked, not tested, and do not retry or expand
to 500 prompts without a newly funded, owner-authorized finite run.

## Dataset And Evaluation Boundary

The strongest next dataset work is curation, not raw row-count growth:

1. Complete the exact 75-slot corridor-diversification workbook only from
   admitted, dated, rights-reviewed source snapshots.
2. Require independent adjudication for severe rows and retain disagreement,
   abstention, language, corridor, and evidence-quality labels.
3. Keep model-generated and synthetic candidates labeled and quarantined until
   privacy, provenance, diversity, leakage, and admission gates pass.
4. Recheck lineage-family and near-duplicate leakage across SFT, preference,
   reward, benchmark, quarantine, and held-out splits.
5. Add native-speaker multilingual and code-switch review, temporal legal
   freshness tests, source ablations, and benign controls.
6. Publish a human-review protocol and uncertainty limits before strengthening
   any safety or field-effectiveness claim.

Do not weaken the strict training gate, rewrite an older append-only record, or
move partial experimental metrics onto the default board to manufacture a green
result.

## Current Deferred Work

[`DEFERRED_WORK.md`](DEFERRED_WORK.md) contains 0 items. The dated
[`closeout resolution receipt`](CLOSEOUT_RESOLUTIONS_2026_07_28.md) preserves
all 11 inherited decisions and is authoritative for what was completed,
declined, excluded, retained, or closed with residual risk.

There is no model-free or gated closeout item waiting. Work reopens only when a
specific receipt condition is met—for example, a real package consumer, a
named successor, qualified independent human reviewers, compatible source
rights and snapshots, or a preregistered finite model study. The next scheduled
source-freshness review is 2026-10-28.

## Claude Code Pickup Prompt

Use this exact prompt from the repository root:

```text
Read AGENTS.md, docs/CLAUDE_CODE_HANDOFF.md, PROJECT_BIBLE.md,
.claude/rules/05_project_bible_pickup.md, docs/MAINTAINER_HANDOFF.md,
docs/PUBLICATION_READINESS.md, docs/CLOSEOUT_RESOLUTIONS_2026_07_28.md, and
docs/DEFERRED_WORK.md. Treat live Git,
filesystem, process, validator, and hosting state as authoritative; treat saved
.claude/state and ignored reports as historical evidence only. Set
DUECARE_MAX_PLANNED_MODEL_CALLS=0. Run the handoff, deferred-work, core, Project
Bible pickup, autonomous-engine status, and whole-stack status checks before
editing. Do not start Ollama, resume recurring tasks, spend model or Kaggle
quota, change Render or DNS, publish artifacts, or promote candidate data
without explicit current authorization. Pick only work whose owner and
authorization boundary are satisfied, make a narrow reviewable change, update
generated artifacts and purpose maps, and report exact validation evidence.
```

## Handoff Acceptance

A successor has not accepted the project merely by reading this file. Complete
the fresh-shell rehearsal in [`SUCCESSOR_REHEARSAL.md`](SUCCESSOR_REHEARSAL.md),
the private least-privilege access and recovery transfer, a documentation-only
change rehearsal, an archive restore check, and the acceptance list in
[`MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md).

Maintenance mode is already enacted because no successor has accepted. Keep
Render, the independent read-only continuity site, MkDocs documentation, and
public source available unless the owner makes a separate retirement decision.
Keep model callers stopped, label volatile legal or operational facts as
freshness-limited, and preserve the dated 11-item receipt rather than reviving
declined work as vague promises.
