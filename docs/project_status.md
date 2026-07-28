# DueCare Project Status

Current as of 2026-07-28.

## Active Submission Scope

The active Kaggle path is exactly three script-kernel folders:

| Kernel | Role | Live status checked 2026-07-28 |
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

- Root `AGENTS.md` names `master` as the release branch. The pre-closeout
  sequence advanced through pull requests
  [11](https://github.com/TaylorAmarelTech/gemma4_comp/pull/11) through
  [16](https://github.com/TaylorAmarelTech/gemma4_comp/pull/16). Pull request 16
  is the immediate fully merged predecessor to the maintenance closeout at
  `1c8f6b25729da869b2775a29321ab3b74bd4715f`; all 16 checks passed. Pull
  request 15's 4,646-pass run is retained only as older historical evidence.
  Maintenance
  mode was enacted on 2026-07-28 with no release tag; every future release
  candidate must rerun its own gates.
- The wrap-up validation made no Ollama, hosted-model, or Kaggle-quota calls.
  Render remains the production website/API host; the independent
  [`duecare-ai-site`](https://tayloramareltech.github.io/duecare-ai-site/)
  repository preserves a read-only 51-route continuity copy without a
  production `CNAME`; and this repository's Pages site remains MkDocs. Pull
  request 14 also fixed the homepage story grid that had squeezed paragraph
  text into the 28-pixel ordered-list number column.
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
  `python scripts/validate_publication_readiness.py --scope core`. All twelve
  current core gates pass in the maintenance candidate; rerun them on any
  future exact release commit.
- [`CLOSEOUT_RESOLUTIONS_2026_07_28.md`](CLOSEOUT_RESOLUTIONS_2026_07_28.md)
  records the honest outcome and claim boundary for all 11 inherited items.
  [`DEFERRED_WORK.md`](DEFERRED_WORK.md) contains zero current items and is
  reserved for specifically reopened work.
- All 18 Python distributions remain unpublished on PyPI by explicit closeout
  decision. One fail-closed OIDC
  workflow owns package publication; a reviewed independent-SemVer manifest
  now reconciles the intentionally mixed versions and selects one package per
  production tag.
- Maintainer succession is now explicit:
  [`CLAUDE_CODE_HANDOFF.md`](CLAUDE_CODE_HANDOFF.md) is the tracked coding-agent
  pickup, [`MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md) is the human
  operational pickup, and
  [`PROJECT_TRANSITION_PLAN.md`](PROJECT_TRANSITION_PLAN.md) preserves the
  2026-07-26 through 2026-08-25 successor playbook. The separate `--scope handoff` gate is
  read-only and keeps both documents linked to live pickup evidence.
- Public deployment ownership is reconciled: `duecare-ai.com` deploys from
  `apps/duecare-ai.com` on Render; the separate `duecare-ai-site` repository
  deploys the backend-free continuity Pages site; and this repository deploys
  MkDocs through `docs-deploy.yml`. Its website exporter uploads both artifacts
  but cannot overwrite MkDocs Pages. The website exposes `/project-status` as
  the public continuity entry point, and the fallback manifest records its
  `source_revision`.
- A later owner decision now defines the post-competition endpoint: keep Render
  and the current centralized hub available through competition grading, then
  retire centralized Fly/Render-style hosting only after the event-triggered
  [`Post-Competition Hosting Transition`](POST_COMPETITION_HOSTING_TRANSITION.md)
  passes. GitHub Pages will preserve the public presentation; mutable hub APIs,
  submissions, accounts, admin, and automation will no longer be available
  centrally. The runtime and FastAPI hub remain deployable as independently
  governed local or partner nodes.
- The website's advertised schema URLs now have local route tests instead of
  pointing at 404s. Kaggle pages show point-in-time run status and distinguish
  public notebooks from private owner-side drafts.
- Containerization, automation, outreach, and human validation have distinct
  boundaries. The runtime and public hub are containerizable, but Hermes,
  the server-automation vetter, the orchestrator, and the autonomous engine are
  host-scheduled processes and are currently disabled. `scripts/hermes.py` stages
  propose-only synthetic research prompts; it neither contacts civil-society
  members nor collects ratings.
- The public outreach API detects gaps, suggests public support organizations,
  matches consented address-hash/topic profiles, drafts campaigns, and vets
  manually forwarded observations. It cannot send mail because it stores no
  raw recipient addresses. A curator needs a separately owned, consented
  address book to resolve profile hashes. The SMTP/IMAP and Hermes-mail architecture in
  [`deployment/oracle_email_solicitation.md`](deployment/oracle_email_solicitation.md)
  is explicitly a future reference design.
- The human-validation packet contains 364 items across 182 strata and has
  zero qualified independent human ratings. Automated rubric scores and
  LLM-judge outputs are not human input and do not establish agreement or field
  effectiveness.
- The industry-neutral system design is now explicit in the
  [Capability-Gap Harness and Network Blueprint](architecture/capability_gap_blueprint.md).
  It separates the gap/domain pack, evidence, harness, evaluation, human
  governance, public-network, and agent-operations planes so the pattern can be
  replicated outside trafficking without copying trafficking-specific claims.
  The document also distinguishes a container-friendly target topology from
  DueCare's current host-scheduled Hermes, server-automation, orchestrator, and
  autonomous-engine processes.
- Broad local/hosted Ollama work is deferred. The rich harness supports a
  non-mutating `--plan` and a startup ceiling through
  `--max-planned-model-calls` / `DUECARE_MAX_PLANNED_MODEL_CALLS`.
- A later owner-authorized Kimi K3 access check on 2026-07-28 used the verified
  Ollama catalog ID `kimi-k3` and a five-attempt, 20,000-input-token,
  3,840-output-token, US$0.25 ledger cap. All five requests reached Ollama but
  returned HTTP 402 because the account had no extra-usage balance. The local
  receipt records zero successes, provider tokens, and actual cost. These are
  access failures, not Kimi results; the proposed 500-prompt lane was not run.
  Its frozen no-call plan selects 500 public synthetic prompts across 117
  categories (seed `20260728`, selection SHA-256
  `9d4aedf042f5f9d73e8372a8f1bf5538190d9791dbc692c38ca720aed1bc48eb`),
  reserves 158,922 estimated input and 384,000 maximum output tokens, and has a
  US$6.2368 worst-case reservation at the checked rates.
- A subsequent paired Kimi K3 smoke used official tag `kimi-k3:cloud` on one
  hash-bound public prompt, once baseline and once with the full DueCare
  harness. The harness preflight now correctly includes deterministic tools;
  this prompted a real adapter fix and regression test. One GREP rule, eight
  RAG documents, and four tool calls were assembled, but both hosted calls
  returned HTTP 402. The two-attempt receipt reserved 3,491 input tokens, 3,000
  output tokens, and US$0.055473, with zero completions, provider tokens, or
  actual cost. Therefore Kimi quality and Kimi-specific harness lift remain
  unknown. This is a funded-later next step, not a closeout blocker. The exact
  public receipt is
  [`kimi_k3_harness_lift_smoke_20260728.json`](../configs/duecare/benchmarks/kimi_k3_harness_lift_smoke_20260728.json).
- A subsequent frozen campaign now extends that candidate lane with a local
  deterministic grade on every successful answer, 500 cross-family
  `gemini-3.1-pro-preview` contextual judgments, and 500 separately labeled
  Kimi K3 contextual self-judgments. The holistic judge protocol is directional,
  not publication-grade per-dimension adjudication. Across all three hosted
  phases, the exact maximum is 1,500 calls, 7,296,582 estimated input tokens,
  1,152,000 maximum output tokens, and US$34.448916 worst-case. The campaign
  remains `blocked_external_access`: Kimi extra usage is unfunded and no Gemini
  API credential is present. It has zero candidate completions, automated
  judgments, or human ratings. The authoritative receipt is
  [`kimi_k3_500_context_judge_campaign.json`](../configs/duecare/benchmarks/kimi_k3_500_context_judge_campaign.json).
- Calls entering the primary `llm_generate.py` router now also pass through a
  shared SQLite attempt/token/cash ledger. Offline tests prove zero-call mode
  blocks before HTTP transport and that retries consume separate reservations.
  Both the baseline model-failure candidate caller and its contextual judge
  caller are also covered after the Kimi access check. This does not yet
  intercept every other direct package/application/
  standalone client or self-contained Kaggle kernel; the exact contract is
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

- [`architecture/capability_gap_blueprint.md`](architecture/capability_gap_blueprint.md) -
  reusable industry-neutral architecture, domain-pack boundary, evaluation
  triangulation, human network, and agent/container promotion path.
- [`research/model_failure_run_readiness.md`](research/model_failure_run_readiness.md) -
  exact Kimi/Gemini campaign topology, blockers, plans, and execution contract.
- [`kaggle_final_closeout_post.md`](kaggle_final_closeout_post.md) - exact final
  Kaggle community update covering new work, honest gaps, and node-first future.
- [`POST_COMPETITION_HOSTING_TRANSITION.md`](POST_COMPETITION_HOSTING_TRANSITION.md) -
  keep Render running through grading, then perform the validated Pages/DNS/data
  transition without implying that static hosting retains central APIs.
- [`CLAUDE_CODE_HANDOFF.md`](CLAUDE_CODE_HANDOFF.md) - current tracked coding-agent
  pickup, public services, recent receipts, boundaries, and exact safe next work.
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
4. If the frozen Kimi/Gemini campaign is funded, re-run all three no-call plans,
   investigate any selection/context/token drift, then authorize candidate,
   Gemini cross-family judge, and Kimi self-judge phases separately under the
   shared ledger. Preserve checkpoint/resume state and keep Meta Muse Spark 1.1
   as a required future comparison lane after revalidating its exact provider
   identifier, access, capabilities, and pricing.
5. Attach exact report, activity, prompt/response, training-metadata, chart,
   and evidence artifacts to any new claim.
6. Keep A-00 as the active optional proof path. A-30 and the other appendix
   notebooks remain archived under `kaggle/_archive/notebooks/`.
7. When the owner confirms competition grading is complete, publish the final
   Kaggle closeout post and execute the post-competition hosting transition;
   until then, keep Render and all current public URLs running.

## Verification

Use the focused commands in [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). The docs
contract tests intentionally fail if current entry docs drift back toward the
retired appendix-ladder framing.

Latest pre-handoff offline receipt on 2026-07-28:

- publication handoff: 2/2 gates passed, including 23/23 succession-document
  checks and 65/65 live pickup checks;
- publication core: 12/12 gates pass, including provider-budget coverage,
  zero-item deferred-work integrity, the dated 11-item closeout receipt, and the
  18-package release-ownership/install-truth gate;
- combined `packages tests` regression in the closeout 18-package workspace:
  4,669 passed and 9 skipped in 7 minutes 57 seconds with no warning summary under the zero-call
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
