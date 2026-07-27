# DueCare Project Status

Current as of 2026-07-27.

## Active Submission Scope

The active Kaggle path is exactly three script-kernel folders:

| Kernel | Role | Live status checked 2026-07-27 |
|---|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Broad interactive workbench for chat, harness comparison, extraction, search controls, knowledge packs, traces, and activity logs. | `COMPLETE` |
| `kaggle/02-live-demo/` | Focused live demo and video narrative path. | `CANCEL_ACKNOWLEDGED` |
| `kaggle/A-00-omni-experiment-workbench/` | Quantitative proof path: baseline vs harnessed arms, synthetic data, fine-tune, judging, and report artifacts. | `CANCEL_ACKNOWLEDGED` |

The public A-00 Kaggle page attaches
`taylorsamarel/duecare-proof-finetuning-data`. That dataset is a guarded
preview, not the full advanced corpus, and Kaggle reports it ready. The latest
A-00 execution is canceled; a fresh successful run and artifact review are
required before it is cited as completed proof. No production adapter is
published.

The interim training collection is public: the SFT and preference dataset views
both report ready, and the integrity, CPU training-plan, and four-arm evaluation
notebooks all completed on 2026-07-15. These are exact-row companions to the
small approved proof release. The completed training starter emitted a plan but
did not execute GPU training, so this does not close the adapter or model-lift
work.

The retired A-series notebook ladder other than active A-00, task-notebook
snapshots, and older checklist/status docs are archived under
`docs/_archive/2026-05-16-legacy-notebook-era/` or
`kaggle/_archive/notebooks/`. Root `kaggle/` should not contain appendix
`A-*` folders other than `A-00-omni-experiment-workbench`, and the only root `04-*` folder should be
`04-kaggle-community-benchmark`.

## Current Technical Posture

- Root `AGENTS.md` names `master` as the release branch. The integrated
  closeout advanced through pull requests 2, 4, 5, 6, 7, and
  [8](https://github.com/TaylorAmarelTech/gemma4_comp/pull/8). Pull request 8 is
  the latest validated substantive baseline at merge commit
  `9385a837879209e18f8e013cf969a3e1ecbcfc91`; all 16 PR checks and all six
  merge-triggered workflows passed. A release/tag remains a separate owner
  decision, and every later candidate must rerun its own gates.
- The wrap-up started from clean `master`, confirmed no model was loaded in
  local Ollama, and its validation commands made no Ollama, hosted-model, or
  Kaggle-quota calls. The
  [post-merge CI](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30306149302),
  [MkDocs Pages deployment](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30306149235),
  [portable website build](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30306149166),
  and [build-only Docker run](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30306149136)
  all passed. Render serves the updated project status, and the new handoff,
  provider-budgeting, and successor-rehearsal Pages routes were verified live.
- A later 2026-07-27 live audit corrected the operational boundary: Hermes,
  the server-automation vetter, and orchestrator watchdogs/processes were still
  active independently of the paused autonomous engine. No local provider ledger existed for that
  period, so historical background provider usage is unknown and must be
  reconciled privately at the provider. The whole stack is now cost-stopped:
  all five recurring tasks are disabled, four stop sentinels are present, and
  zero verified repository daemon processes remain. The ignored receipt is
  `reports/cost_stop_status.json`; the public runbook is
  [`MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md).
- The repository has a single model-free publication entry point:
  [`PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md) and
  `python scripts/validate_publication_readiness.py --scope core`. All eleven
  core gates passed in the closeout candidate on 2026-07-27; rerun them on the
  exact release commit.
- [`DEFERRED_WORK.md`](DEFERRED_WORK.md) is the generated, validated source for
  every unfinished item's owner role, prerequisites, authorization boundary,
  ordered actions, evidence, and acceptance gates.
- All 18 Python distributions remain unpublished on PyPI. One fail-closed OIDC
  workflow owns package publication; a reviewed independent-SemVer manifest
  now reconciles the intentionally mixed versions and selects one package per
  production tag.
- Maintainer succession is now explicit: [`MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md)
  is the operational pickup, and
  [`PROJECT_TRANSITION_PLAN.md`](PROJECT_TRANSITION_PLAN.md) schedules the
  2026-07-26 through 2026-08-25 closeout. The separate `--scope handoff` gate is
  read-only and keeps both documents linked to live pickup evidence.
- Public deployment ownership is reconciled: `duecare-ai.com` deploys from
  `apps/duecare-ai.com` on Render; GitHub Pages deploys MkDocs through
  `docs-deploy.yml`; the website static exporter remains an artifact workflow
  and cannot overwrite Pages. The website exposes `/project-status` as the
  public continuity entry point. Post-merge Pages, artifact, and live Render
  route checks all passed on 2026-07-27.
- The website's advertised schema URLs now have local route tests instead of
  pointing at 404s. Kaggle pages show point-in-time run status and distinguish
  public notebooks from private owner-side drafts.
- New local/hosted Ollama work is deferred. The rich harness supports a
  non-mutating `--plan` and a startup ceiling through
  `--max-planned-model-calls` / `DUECARE_MAX_PLANNED_MODEL_CALLS`.
- Calls entering the primary `llm_generate.py` router now also pass through a
  shared SQLite attempt/token/cash ledger. Offline tests prove zero-call mode
  blocks before HTTP transport and that retries consume separate reservations.
  This does not yet intercept direct package/application/standalone clients or
  self-contained Kaggle kernels; the exact contract is
  [`PROVIDER_BUDGETING.md`](PROVIDER_BUDGETING.md).
- All three scheduled model-call wrappers now fail closed unless the shared router has
  a positive attempt cap, finite input/output/cash caps, a stable run ID, and
  reviewed pricing or an explicit recorded unknown-cost override. Their
  watchdog registration and `-Run` paths no longer remove pause sentinels.
- The strict training-data audit is not clean: five dense generic-corridor
  typologies produced 25 metadata-only curation tasks and a 75-row minimum
  expansion target. A deterministic workbook now defines all 75 risk,
  benign-neighbour, and counterfactual slots with split-safe lineage,
  language, perspective, source, and two-person-review requirements. Its 12
  official-source candidates remain quarantined and all 75 content slots are
  honestly unfilled. Existing published learning artifacts remain bounded by
  their original manifests; this blocks a new training claim, not review of
  the core repository.
- Local Gemma inference is standardized through `Gemma4Runtime.load()`.
- Active A-00 uses the same offline default harness as the Kernel 01 comparison path:
  Persona + GREP + RAG/context + deterministic tools, with internet/import off.
- Active A-00 can run local Gemma judging by default and optional external judge paths
  when credentials are present.
- Active A-00 training supports checkpoint/resume, adapter save/load, and final report
  export.
- The harness system is documented as an ecosystem rather than a single
  monolithic harness.

## Current Docs To Trust

- [`MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md) - fresh-shell operations,
  system boundaries, access transfer, recovery, and acceptance.
- [`PROJECT_TRANSITION_PLAN.md`](PROJECT_TRANSITION_PLAN.md) - dated 30-day
  closeout, successor rehearsal, release decision, and maintenance fallback.
- [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md) - reviewer verification path.
- [`PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md) - offline release gate,
  Ollama-credit plan, dataset roadmap, and additional source candidates.
- [`DEFERRED_WORK.md`](DEFERRED_WORK.md) - canonical unfinished-work register;
  this supersedes duplicated backlog tables in narrative docs.
- [`USER_TODO.md`](USER_TODO.md) - manual actions before submission.
- [`readiness_dashboard.md`](readiness_dashboard.md) - current status snapshot.
- [`two_week_submission_plan.md`](two_week_submission_plan.md) - final execution
  plan.
- [`current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md) -
  active versus archived Kaggle inventory.
- [`harness_ecosystem.md`](harness_ecosystem.md),
  [`harness_pattern.md`](harness_pattern.md), and
  [`harness_standard_contract.md`](harness_standard_contract.md) - harness
  contract and inventory.
- [`model_loading_trace.md`](model_loading_trace.md) - Gemma 4 runtime contract.

## Remaining Work

The canonical queue is [`DEFERRED_WORK.md`](DEFERRED_WORK.md). The numbered
summary below is directional only; the register controls status and acceptance.

1. Complete the 30-day access, recovery, release/no-release, successor rehearsal,
   and final acceptance actions in the transition plan.
2. Keep the three active Kaggle source surfaces runnable; rerun 02 only when a
   new recording is needed and A-00 only for a deliberately funded proof.
3. Approve source snapshots, then fill and independently adjudicate the 75-row
   corridor workbook before making a new fine-tuning or adapter-improvement
   claim.
4. When model quota is intentionally reopened, freeze and plan a small run,
   configure the primary-router ledger with finite attempt/input/output/cash
   caps and reviewed pricing, then deliberately resume the whole stack or only
   the required caller and preserve checkpoint/resume state.
5. Attach exact report, activity, prompt/response, training-metadata, chart,
   and evidence artifacts to any new claim.
6. Keep A-00 as the active optional proof path. A-30 and the other appendix
   notebooks remain archived under `kaggle/_archive/notebooks/`.

## Verification

Use the focused commands in [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). The docs
contract tests intentionally fail if current entry docs drift back toward the
retired appendix-ladder framing.

Latest offline working-tree receipt on 2026-07-27:

- publication handoff: 2/2 gates passed, including 17/17 succession-document
  checks and 65/65 live pickup checks;
- publication core: 11/11 gates passed, including provider-budget coverage,
  deferred-work integrity, and the 18-package release-ownership/install-truth
  gate;
- combined `packages tests` regression in the closeout 18-package workspace:
  4,637 passed and 9 skipped with no warning summary under the zero-call
  transport lock; the focused
  43-test package run also passes with pandas `RuntimeWarning` promoted to an
  error;
- MkDocs strict build: passed with zero warnings; existing repository-relative
  source links are resolved to canonical GitHub URLs without suppressing
  genuinely missing targets;
- training readiness: strict quality and provenance failed as documented,
  while the 25-task corridor plan and 75-slot scaffold passed privacy/safety
  validation; strict completion remains red at `0/75`, as intended;
- focused deferred-work/handoff/publication/site tests: 96 passed, including
  the complete 78-test website suite;
- curator-block governance: all 75 universal rubric dimensions have inline
  guidance; strict validation reports zero errors and zero warnings;
- post-deploy external network audit: 592 links checked, zero confirmed broken,
  and nine transient/unverified hosts kept separate from confirmed failures;
- the polish/validation commands initiated no Ollama or hosted-model call; the
  separate background-daemon usage correction above supersedes any broader
  reading of that receipt.
