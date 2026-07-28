# Maintainer Handoff

This is the operational handoff for a person taking responsibility for DueCare.
It explains how to establish current truth, preserve the project's safety
boundaries, run routine checks, and decide what is safe to publish. The dated
coding-agent pickup is in the
[Claude Code handoff](CLAUDE_CODE_HANDOFF.md), the closeout schedule is in the
[30-day transition plan](PROJECT_TRANSITION_PLAN.md),
while the release boundary and evidence backlog remain in
[Publication readiness](PUBLICATION_READINESS.md). The dated
[closeout resolution receipt](CLOSEOUT_RESOLUTIONS_2026_07_28.md) records every
inherited disposition, while the [Deferred work register](DEFERRED_WORK.md) is
reserved for genuinely reopened work and currently contains zero items.

**Handoff posture:** maintenance mode enacted; current owner retained
**Prepared:** 2026-07-28
**Target transfer:** 2026-08-25
**Default model posture:** whole model/flywheel stack cost-stopped; zero planned model calls

## 2026-07-28 Final Repository And Continuity Receipt

The 11 inherited closeout decisions are now resolved in the dated
[`CLOSEOUT_RESOLUTIONS_2026_07_28.md`](CLOSEOUT_RESOLUTIONS_2026_07_28.md)
receipt. The zero-item outstanding register means there is no current action
waiting; it does not relabel declined model/package/notebook work, excluded
training/human claims, unknown historical provider usage, or an unperformed
private transfer as completed.

The immediate fully merged predecessor to this maintenance closeout is
[pull request 16](https://github.com/TaylorAmarelTech/gemma4_comp/pull/16),
merged to `master` as `1c8f6b25729da869b2775a29321ab3b74bd4715f`.
All 16 checks passed. Pull request 15's **4,646 passed, 9 skipped** local run is
an older historical receipt. Treat both predecessor receipts as context, not
as proof of the checkout you inherit. No Ollama, hosted-model, or Kaggle-quota
call was made.

The final model-free sequence was deliberately reviewable:

- [PR #11](https://github.com/TaylorAmarelTech/gemma4_comp/pull/11), merge
  `3daa8988`, added a validated 51-route backend-free export and established
  the independent
  [`duecare-ai-site`](https://tayloramareltech.github.io/duecare-ai-site/)
  continuity repository without changing Render or production DNS;
- [PR #12](https://github.com/TaylorAmarelTech/gemma4_comp/pull/12), merge
  `c728c06c`, repaired and polished mobile website navigation;
- [PR #13](https://github.com/TaylorAmarelTech/gemma4_comp/pull/13), merge
  `47277c6212cdf953391aa3f67dcc918bb7d42d0d`, brought the optional
  adverse-media verifier inside the atomic provider-budget contract, for five
  covered transports in total;
- [PR #14](https://github.com/TaylorAmarelTech/gemma4_comp/pull/14), merge
  `a56f9d1b84b5513f91b21a0d3368de30a4b33e4a`, fixed the homepage worker-story
  grid: `.step-copy` now keeps each heading and paragraph in the flexible
  `minmax(0, 1fr)` column instead of squeezing body text into the 28-pixel
  number column; and
- PR #15 completed the registered three-file Ruff cleanup without a file-wide
  suppression and reduced the canonical deferred register to 11 items with no
  `ready_local` work.

Render remains the production website/API host. The independent continuity
Pages site is read-only, omits a `CNAME`, disables state-changing controls, and
publishes a `source_revision` receipt in its snapshot manifest. This monorepo's
GitHub Pages deployment remains the MkDocs documentation site. The tracked
[`CLAUDE_CODE_HANDOFF.md`](CLAUDE_CODE_HANDOFF.md) gives Claude Code and other
coding agents the exact pickup prompt and live-state boundary.

The 2026-07-28 maintenance candidate passed **4,653 tests with 9 skips** in 8
minutes 4 seconds for the same broad command under the zero-call lock and
offline provider/model flags. This is the current local receipt. The prior
4,648-pass tracked-handoff result and the 4,646-pass PR #15 result remain exact
historical receipts.

## Integrated Closeout Receipt

The model-free closeout landed through
[pull request 2](https://github.com/TaylorAmarelTech/gemma4_comp/pull/2) on
`master` as merge commit `07cfdbfd00e1bc304ffc1f8b2736c4d93bbf0eab` on
2026-07-26 (PDT). The post-merge evidence is:

- the [master CI run](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30235104435)
  passed both full Python matrices, the 18-wheel build, clean-room install,
  gitleaks, website/privacy, Kaggle, harness, and entity-intelligence jobs;
- the [MkDocs Pages run](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30235104493)
  deployed successfully, including the live
  [maintainer handoff](https://tayloramareltech.github.io/gemma4_comp/MAINTAINER_HANDOFF/);
- the [website artifact run](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30235104433)
  completed without becoming a competing Pages deployer, and Render serves the
  live [project-status route](https://duecare-ai.com/project-status); and
- the closeout and receipt commands themselves made no Ollama or hosted-model
  calls (see the later whole-stack correction for independently scheduled
  background callers).

This proves the integrated code/docs/deployment stopping point. It does not
choose a release tag, publish packages or models, close the strict training
lane, or complete private ownership transfer.

## 2026-07-27 Reconciliation Addendum

A second live, model-free pass started from clean `master` at
`f4bb9c3ef8eaef6f4692813ff77cf16230d5abe6` and reconciled surfaces that the
first closeout deliberately left for live verification:

- `ollama ps` reported no loaded model, the autonomous engine remained paused,
  and the pickup validator still passed all 65 checks;
- authenticated Kaggle status was `COMPLETE` for `duecare-app`,
  `CANCEL_ACKNOWLEDGED` for both `duecare-live-demo` and A-00, and `COMPLETE`
  for the optional Community Benchmark. The Universal Benchmark public slug
  did not resolve. Canceled is terminal, not successful;
- all 18 Python distribution names returned no public PyPI project on
  2026-07-27. The duplicate generic-tag publisher was removed; one OIDC
  workflow now owns publication and fails closed while package versions differ;
- official current GitHub Action majors were checked through GitHub and the
  workflows were refreshed (including checkout/setup, artifacts, Pages, cache,
  Gitleaks, Docker, and Helm). The triggered post-merge CI, Pages,
  website-artifact, harness-contract, and evaluation workflows confirmed the
  refreshed actions without a Node 20 runtime annotation;
- curator-owned inline grading guidance now covers all 75 universal rubric
  dimensions. Its strict validator reports zero errors and zero warnings, and
  CI no longer converts future curator warnings into a passing annotation;
- the website now serves the six schema URLs it advertised, labels Kaggle
  execution state, and links the verified Prompt Intent notebook; and
- the external-link checker now distinguishes confirmed breakage from network
  or bot-blocked hosts, checks concurrently, and no longer mistakes private
  owner listings or API endpoints for verified public pages.

The reconciliation landed through
[pull request 4](https://github.com/TaylorAmarelTech/gemma4_comp/pull/4) as
`dc313814d9f42e127b24191b7912fd521083fadd`. Its
[post-merge CI](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30273583863),
[MkDocs Pages deployment](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30273583750),
and [website artifact build](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30273583802)
passed. The live project-status page and all six advertised schema endpoints
returned 200, and the post-deploy audit checked 577 external links with zero
confirmed broken links and 10 transient/unverified hosts. This supersedes the
pre-deploy observations while retaining the earlier receipt as history.

No Kaggle notebook, PyPI distribution, model, dataset, or release was published
by this reconciliation. Candidate notebooks stay queued until one closes a
named evidence gap and passes the publication checklist in
[`NOTEBOOKS.md`](NOTEBOOKS.md).

## 2026-07-27 Final Wrap-up Receipt

The successor-focused wrap-up began in pull request 5, and its validated
deferred-work closeout landed through
[pull request 8](https://github.com/TaylorAmarelTech/gemma4_comp/pull/8) on
`master` as merge commit `9385a837879209e18f8e013cf969a3e1ecbcfc91`.
All 16 pull-request checks passed. In particular, the active Kaggle kernels,
generated page sources, optional Community Benchmark surface, both full Python
matrices, 18-wheel build, clean-room install, privacy/secret scan, public
website, and build-only multi-architecture image gate remained green.

The merge-triggered evidence also completed successfully:

- [full CI](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30306149302)
  passed the notebook, package, privacy, website, harness, and
  entity-intelligence lanes;
- the [Docker candidate run](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30306149136)
  built both target architectures without logging in, signing, or publishing;
- the [evaluation](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30306149303)
  and [contract](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30306149137)
  workflows passed;
- the [MkDocs Pages deployment](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30306149235)
  and [51-page portable website build](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30306149166)
  passed; and
- the live [project-status route](https://duecare-ai.com/project-status),
  [provider-budgeting guide](https://tayloramareltech.github.io/gemma4_comp/PROVIDER_BUDGETING/),
  [successor rehearsal](https://tayloramareltech.github.io/gemma4_comp/SUCCESSOR_REHEARSAL/),
  and this handoff returned the new closeout content.

This final pass added an atomic attempt/token/cash budget around every primary
generation-router transport, a strict 75-slot curation workbook backed by 12
training-blocked source candidates, reproducible independent-SemVer package
release tooling, guarded release workflows, archive restore rehearsal, and a
single-command successor pickup. Those wrap-up commands made no Ollama,
hosted-model, or Kaggle-quota call and published no package, image, chart,
notebook, model, or dataset.
At that historical point, human rights/snapshot review, 75-row independent
curation and adjudication, private access transfer, and the first release tag
were unfinished. Their final 2026-07-28 dispositions are in the closeout
receipt; none was silently treated as performed.

## 2026-07-27 Whole-stack Cost-stop Correction

A later live process and Task Scheduler audit found that the main autonomous
engine pause was narrower than the complete cost boundary. Hermes, the
server-automation vetter, and the orchestrator still had enabled watchdogs and
live Python process trees; Hermes and the vetter can call the primary
hosted-model router independently.
Their state files continued to advance after the engine was paused.

The repo-local provider-budget ledger did not exist and the daemon environment
had an Ollama credential but none of the finite `DUECARE_*` budget settings.
Therefore this repository cannot reconstruct or honestly claim zero historical
background provider usage. Reconcile that period privately against the Ollama
account dashboard and billing/quota records; do not copy credentials or billing
details into Git.

The verified stopping posture is now broader:

- `DueCareAutonomousEngine`, `DueCareHermes`, `DueCareOpenClaw`,
  `DueCareOrchestrator`, and `DueCareFlywheelManager` are disabled;
- stop sentinels exist for the autonomous engine, Hermes, the
  server-automation vetter, and the orchestrator;
- zero verified repository daemon processes remain; and
- `reports/cost_stop_status.json` records a privacy-minimized, ignored local
  receipt. No benchmark, proposal, verdict, or checkpoint report was deleted.

`scripts/stop_ollama_stack.ps1` now owns the whole-stack boundary. Its default
stop path writes every sentinel, disables all five recurring tasks before
terminating only exact repository daemon process trees, and never regenerates,
commits, or pushes a board unless separate capture/publish switches are given.
The watchdog wrappers preserve stop sentinels; all three scheduled model
callers additionally refuse launch until a positive finite provider budget and
reviewed pricing policy pass preflight.

The 2026-07-27 closeout candidate was then exercised under
`DUECARE_MAX_PLANNED_MODEL_CALLS=0`. The complete package/test regression passed
4,637 tests with 9 skips, the public-surface audit checked 1,144 local links
with no findings, all 11 then-current core and both handoff gates passed, all 3 active
notebook scripts and 31 notebook-focused tests passed, the 5 active/optional
Kaggle kernel checks passed, all 78 website tests passed, the Project Bible
pickup passed 65 checks, the successor rehearsal reassembled all 52 archived
files to their recorded SHA-256 values, and the strict documentation build
completed. The latest external audit checked 592 links with zero confirmed
broken links and nine transient or unverified hosts.

The separate training scope correctly remains red: its deterministic workbook
has 0/75 completed rows, the quality audit still identifies five dense
single-corridor shortcut risks, and the older append-only fine-tune record has
intentionally stale artifact fingerprints. This is curator work, not a reason
to weaken the gate or rewrite provenance history.

The cost-stop correction itself landed through pull request 7. The validated
deferred-work closeout then landed through pull request 8 as merge commit
`9385a837879209e18f8e013cf969a3e1ecbcfc91`; all 16 pull-request checks and all
six merge-triggered workflows passed. Later candidates must establish their own
live receipts rather than inheriting that result.

## First 30 Minutes

Use a Python 3.12 environment with the repository's development dependencies.
These checks are read-only or validation-only and do not call Ollama, a hosted
model, or the network:

```powershell
git status --short
$env:DUECARE_MAX_PLANNED_MODEL_CALLS='0'
python scripts/validate_maintainer_handoff.py
python scripts/validate_deferred_work.py
python scripts/validate_publication_readiness.py --scope handoff
python scripts/validate_publication_readiness.py --scope core
python scripts/validate_project_bible_pickup.py
python scripts/autonomous_engine.py --status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/stop_ollama_stack.ps1 -Status
```

Expected stopping posture:

- the handoff scope and core publication scope are green;
- the autonomous engine reports stopped or paused;
- the whole-stack status reports `cost_stop_active: true`, all five recurring
  tasks disabled, all four stop sentinels present, and zero verified daemon
  processes;
- a dirty working tree is investigated, not erased;
- the strict training scope may remain red for the documented corridor and
  provenance blockers; and
- no model service is started merely to make a status check look complete.

If a command disagrees with a saved report, trust live state and investigate
the disagreement before continuing.

## Sources Of Truth

Use this precedence order when artifacts disagree:

1. Live Git, filesystem, process, and validator output from the current
   workspace.
2. Root `AGENTS.md` for safety rules, active surfaces, and required validation.
3. [Claude Code handoff](CLAUDE_CODE_HANDOFF.md) for the tracked closeout
   pickup, live-service ownership, and recent receipts.
4. [Deferred work register](DEFERRED_WORK.md) for the canonical status, owner,
   authorization boundary, next action, and acceptance evidence for unfinished
   work.
5. [Publication readiness](PUBLICATION_READINESS.md) for the release boundary
   and known limitations.
6. [`project_status.md`](project_status.md) and root `kaggle/_INDEX.md` for
   current public inventory.
7. [`codex/PROJECT_BIBLE.md`](codex/PROJECT_BIBLE.md) for deep historical and
   autonomous-engine context.
8. Saved `.claude/state/` files and ignored reports as historical evidence only.

Do not infer live completion from a handoff summary, an old manifest, or a
healthy container alone. Re-run the smallest relevant read-only validator.

## Architecture And Boundaries

The project has four intentionally separated flows:

```text
worker or reviewer input
  -> workbench and shared model service
  -> deterministic GREP / RAG / tools / privacy checks
  -> optional Gemma synthesis
  -> replayable evaluation and export evidence

benchmark prompt
  -> resumable generation cache
  -> versioned batched or per-dimension judging
  -> exact coverage manifest
  -> dated report and comparable board

curated training data
  -> lineage-aware organization and split
  -> strict quality audit and corridor plan
  -> optional training and evaluation
  -> append-only registry and verified model card

public entity sources
  -> propose-only entity-intelligence pipeline
  -> curator review
  -> approved knowledge update, never an automatic worker-facing claim
```

Important boundaries:

- Shared workbench chrome owns model loading. Pages use
  `window.dcWbModelService`; they do not create independent loaders.
- Deterministic Bulk File Review extraction runs before optional synthesis.
  `hierarchical_gemma_graph` is the distinct hierarchy-level model pass, with
  provenance visible at every reviewed level.
- The entity-intelligence pipeline stages proposals under ignored `reports/`.
  It is not the live harness, GREP/RAG layer, training-data feed, or an automatic
  accusation system.
- The default comparable board remains the versioned v1/h1 batched lane.
  Incomplete per-dimension judging stays isolated as experimental evidence.
- Archived notebook-era surfaces are provenance. Active primary Kaggle surfaces
  are `01-duecare-exploration-workbench`, `02-live-demo`, and
  `A-00-omni-experiment-workbench`; `03` and `04` are optional benchmark lanes.
- Container images package the runtime, public hub, and deployment examples;
  they do not imply that Hermes or another agent autonomously contacts people.
  Hermes, the server-automation vetter, the orchestrator, and the autonomous
  engine are separate host-scheduled processes. All are cost-stopped, and Hermes is only a
  propose-only synthetic research-discovery daemon.
- The public outreach loop is planning plus intake: it detects gaps, suggests
  public support organizations, matches consented hash/topic profiles, drafts
  a campaign, and vets a manually forwarded observation. The hub stores no raw
  addresses and cannot send. A curator must resolve hashes against a separately
  owned, consented address book and use an organization-owned mailer;
  the documented SMTP/IMAP and Hermes-mail adapter is a future reference design.
- The validated 364-item, 182-stratum human-review packet has zero independent
  ratings. Do not describe deterministic grades, LLM-judge results, opt-ins,
  campaign drafts, or API observations as qualified human validation.

## Repository Map

| Area | Purpose | Start here |
|---|---|---|
| `packages/` | Eighteen `duecare-llm*` package directories, including the workbench, reusable kit, and shared services | Package-local `AGENTS.md`, `README.md`, and tests |
| `apps/` | Public hub and deployable application surfaces | App README and route tests |
| `kaggle/` | Active, optional, and archived notebook/kernel surfaces | Root `kaggle/_INDEX.md` |
| `scripts/` | Deterministic validators, builders, research tooling, and opt-in model workflows | Script help, tests, and [File purpose guide](FILE_PURPOSE_GUIDE.md) |
| `data/` and `configs/` | Versioned prompts, knowledge, policy, registry, and training inputs | Manifests, licenses, and schema files beside each dataset |
| `docs/` | Public documentation, reproducibility evidence, status, and handoff | [`index.md`](index.md) and this runbook |
| `reports/` | Usually ignored, generated local evidence and staging | Verify hashes and timestamps before trusting it; do not publish by default |

## Public Deployment Ownership

Each public surface has one deployment owner. Keep this split explicit:

| Surface | Authoritative source | Deployment path | Rule |
|---|---|---|---|
| `duecare-ai.com` website and hub APIs | `apps/duecare-ai.com/` on `master` | Render blueprint in root `render.yaml` | Render owns the live website and API health; the hub does not load Gemma |
| Read-only website continuity | Same reviewed FastAPI templates and five allowlisted public snapshots | Separate `TaylorAmarelTech/duecare-ai-site` repository deploys GitHub Pages daily, on dispatch, or from an explicitly pinned public ref | It has no production `CNAME`, exposes no mutable API, and must retain its `source_revision` receipt |
| GitHub Pages documentation | `docs/`, `mkdocs.yml`, and `requirements-docs.txt` on `master` | `.github/workflows/docs-deploy.yml` | This is the repository's only Pages deployer |
| Website continuity artifacts | Same templates through `apps/duecare-ai.com/scripts/export_static.py` | `.github/workflows/duecare-site-build.yml` uploads both live-backend and backend-free artifacts | Source-repository build only; it must not call `actions/deploy-pages` in this repository |

The former manual `.github/workflows/pages.yml` marketing-site deploy was
removed because it could overwrite the MkDocs Pages site. The separate
`duecare-ai-site` repository now owns the read-only continuity deployment and
does not claim production DNS. A future root-domain cutover remains an explicit
owner decision with the gates in `apps/duecare-ai.com/DEPLOY_STATIC.md`.
The public website exposes `/project-status`, which links this handoff, the
transition plan, and publication boundary without exposing private access data.

## Local Environment

- Primary maintenance environment: Windows PowerShell and Python 3.12.
- Supported public install guidance starts in [`install.md`](install.md). Do not
  encode one maintainer's absolute virtual-environment path in scripts or docs.
- Install the development/test dependencies before relying on `pytest`; a bare
  virtual environment may not contain them.
- Keep credentials in an approved password manager or platform secret store.
  The repository must not contain API keys, Kaggle tokens, raw worker data,
  private case files, or unredacted operational logs.
- Set `DUECARE_MAX_PLANNED_MODEL_CALLS=0` for deterministic maintenance. It is a
  planning lock for guarded harnesses and a transport lock for every attempt
  entering the primary `llm_generate.py` router. It is not a universal network
  interceptor for direct package, application, standalone, or notebook clients;
  see [Provider budgeting](PROVIDER_BUDGETING.md).
- Generated report directories are not a backup. Preserve release artifacts in
  the approved release/archive location with checksums.

## Validation Ladder

Run the smallest applicable scope first, then widen only as needed:

| Scope | Command | Meaning |
|---|---|---|
| Handoff | `python scripts/validate_publication_readiness.py --scope handoff` | Succession docs, cross-links, privacy-safe content, pickup consistency, and paused-state evidence |
| Core release | `python scripts/validate_publication_readiness.py --scope core` | Twelve model-free public, claim, provider-budget, Kaggle, deferred-work, closeout-receipt, source-smoke, package-release, and package-collection gates |
| Closeout decisions | `python scripts/validate_closeout_resolutions.py` | Exact 11-item scope, dated outcomes, evidence paths, claim boundaries, reopen conditions, and absence from the outstanding register |
| Deferred work | `python scripts/validate_deferred_work.py` | Canonical owners, dependencies, boundaries, evidence paths, generated Markdown, and unresolved-token rejection |
| Focused tests | `python -m pytest path/to/affected/tests -q` | Behavioral evidence for the edited area |
| Package collection | `python -m pytest packages --collect-only -q` | Published package-test inventory remains discoverable |
| Kaggle | `python scripts/validate_main_kaggle_kernels.py` and `py -3.12 scripts/validate_kaggle_page_sources.py` | Active kernel and generated-page contracts |
| Provider budget | `python scripts/validate_provider_budget_coverage.py` | All four primary-router transports plus the adverse-media and model-failure study transports remain inside atomic reservations; this makes no provider call |
| External links | `python scripts/check_external_links.py --check --workers 24` | Network audit that separates confirmed 4xx breakage from transient, DNS, SSL, redirect, and bot-blocked hosts |
| Full regression | `python -m pytest packages tests -q` | Broad local regression; report skips and warnings exactly |
| Training | `python scripts/validate_publication_readiness.py --scope training` | Strict dataset/provenance release lane; nonzero is expected until its documented queue closes |

Never turn a red training gate green by weakening thresholds, rewriting an old
ledger entry, blending experimental judging into the default board, or deleting
evidence. Fix the underlying data/provenance chain and append a new record.

## Routine Operations

### Start a maintenance session

1. Read the root and nearest package `AGENTS.md` files.
2. Inspect `git status --short`, branch, recent commits, and relevant live
   processes.
3. Set the zero-call guard and run the handoff gate.
4. Make a narrow change, update the authoritative source and its generated
   artifacts together, then run focused and public-surface validation.
5. Record exact commands, dates, warnings, and intentionally red lanes.

### Change public documentation

Update the relevant purpose map when adding a durable public surface. Run
`validate_public_surface.py`, check local links, and avoid volatile legal,
hotline, office, fee, or policy details unless they are versioned knowledge
objects with source dates.

### Change a dataset or training artifact

Preserve source/license metadata, content hashes, lineage families, quarantine
reasons, and held-out boundaries. Run deterministic audits before any training.
Candidate rows and model outputs are not accepted training data until human or
declared rule-based review admits them.

### Resume model or Ollama work

Model work requires a deliberate budget, frozen model IDs/revisions, prompt and
rubric hashes, output limits, cache paths, and a stop condition. Run a
non-mutating plan first. Unlock only the smallest sampled allowance, reuse
checkpoints, and keep a sanitized receipt. The primary router now has a shared
atomic call/token/cash ledger, so its startup plan and transport receipt can be
compared. Direct package/application/standalone clients and self-contained
notebook runtimes still need their own integration; withhold credentials from them
during maintenance rather than assuming the router intercepts their traffic.
Only after that policy is reviewed should an authorized maintainer run
`scripts/stop_ollama_stack.ps1 -Resume`; it removes the four sentinels and
re-enables the five recurring tasks but launches no process directly. Hermes
and the server-automation vetter still refuse to launch unless the positive
finite budget preflight passes.

Any future comparison plan must treat **Kimi K3** and **Meta Muse Spark 1.1**
as required lanes. Reverify provider identifiers, access, context limits,
modalities, and pricing immediately before spending. If a lane is unavailable,
retain dated evidence of that constraint instead of silently substituting a
different model.

A later, separately authorized Kimi K3 access check on 2026-07-28 used the live
Ollama catalog ID `kimi-k3`. Five transport attempts were protected by a
five-attempt, 20,000-input-token, 3,840-output-token, US$0.25 budget. Ollama
returned HTTP 402 for every attempt because the account's extra-usage balance
was empty. The sanitized local receipt records zero successes, provider tokens,
and actual ledger cost. This produced no model result and did not justify the
proposed 500-prompt lane. Do not retry until the billing owner deliberately
funds extra usage and authorizes a new run ID and limits.

The no-call 500-prompt plan is already frozen: category-balanced seed
`20260728`, 117 categories, selection SHA-256
`9d4aedf042f5f9d73e8372a8f1bf5538190d9791dbc692c38ca720aed1bc48eb`,
158,922 estimated input tokens, 384,000 maximum output tokens, and a US$6.2368
worst-case reservation at the rates checked that day. It produces 500 Kimi
answers plus local deterministic grades only—no hosted judge and no human
rating. Recompute `--plan` and investigate any hash drift before funding it.

### Publish or release

Use [Publication readiness](PUBLICATION_READINESS.md). Packages use the
manifest-backed independent-SemVer policy in ADR-001. Freeze the exact commit,
reconcile the selected package version, changelog, manifest, and tag as one
decision, run the core gate on that commit, retain the receipt, and state
whether the training scope passed. `CITATION.cff` remains intentionally
unversioned until an actual release. Publishing public hosting, Kaggle,
PyPI, Hugging Face, or GitHub releases remains an owner-authorized external
action.

GitHub Pages now builds with `mkdocs build --clean --strict`. The tested
`scripts/mkdocs_repo_links.py` hook converts only existing repository-relative
targets unavailable to Pages (outside `docs/` or intentionally excluded) to
canonical GitHub source links; missing targets stay visible to MkDocs and still
fail the strict build. The 2026-07-27 local strict receipt completed with zero
warnings.

### Archive or recover

Use the durable archive tooling and preserve its transaction boundary: write
chunks, atomically commit the manifest, then prune superseded chunks. Test a
restore before treating an archive as valid. Never use ignored reports or a
working tree as the sole copy of release evidence.

## Current Open Work

The generated [`DEFERRED_WORK.md`](DEFERRED_WORK.md) register is authoritative
and currently contains 0 explicit items. The separate dated
[`closeout resolution receipt`](CLOSEOUT_RESOLUTIONS_2026_07_28.md) names all
11 inherited items and their exact decision, rationale, verification, claim
boundary, evidence, and reopen condition. The next scheduled source-freshness
review is 2026-10-28.

Do not copy resolved history into another hand-maintained queue. When a receipt
reopen condition is truly met, update
`configs/duecare/deferred_work.json`, regenerate the document, and run
both `python scripts/validate_closeout_resolutions.py` and
`python scripts/validate_deferred_work.py`. Strategic themes remain in
[the roadmap](ROADMAP.md); release limitations remain in
[Publication readiness](PUBLICATION_READINESS.md).

## Access And Ownership Transfer

Credentials and recovery material move through a private password manager or
the platform's transfer workflow. The repository records only the completion
receipt, never a secret or personal recovery answer.

| Surface | Transfer evidence to retain privately | Safe repository action |
|---|---|---|
| GitHub organization/repository | Successor role, branch/release permissions, recovery owner, two-factor check | Document canonical repository and release process |
| Kaggle account, notebooks, and datasets | Collaborator/owner access, dataset edit rights, accelerator/quota expectations | Verify slugs and pinned commit references without exposing tokens |
| Public domain, DNS, hosting, and TLS | Registrar, DNS, deployment owner, billing and recovery access | Keep deployment docs and health-check locations current |
| Package registries and model/dataset hosting | PyPI and Hugging Face ownership, scoped publishing rights, recovery route | Record package/dataset names and reproducible build commands |
| Ollama or other model-provider accounts | Billing owner, quota policy, approved models, revocation path | Keep calls locked until a reviewed budget is authorized |
| Outreach, support, and research contacts | Shared mailbox/list ownership, retention policy, consent boundary | Store only public role addresses when publication is necessary |
| Monitoring, backups, and archives | Alert recipient, storage owner, retention and restore evidence | Document sanitized checksums and restore procedure |

The private transfer receipt should record date, surface, outgoing owner,
incoming owner, least-privilege role, recovery check, revocation check, and
where the secret is stored. It should not be committed.

Use the public-safe [private transfer receipt template](PRIVATE_TRANSFER_RECEIPT_TEMPLATE.md)
as a field checklist, but copy it into the approved private records system
before entering identities, account details, or evidence locations. Run the
[successor pickup rehearsal](SUCCESSOR_REHEARSAL.md) from a fresh shell to
produce a sanitized, ignored technical receipt. Neither artifact substitutes
for a real human access and recovery check.

## Incident And Recovery

| Signal | Immediate containment | Recovery and evidence |
|---|---|---|
| Unexpected model traffic or credit use | Run `scripts/stop_ollama_stack.ps1`, confirm its `-Status` is green, restore the zero-call guard, and do not retry | Identify the exact caller and retry path from sanitized metadata; reconcile provider usage privately before any resume |
| Suspected committed secret or private data | Stop publication, restrict access where possible, revoke/rotate credentials out of band, and preserve a minimal incident timeline | Use category/count-only scanning; coordinate any history rewrite explicitly and verify mirrors/releases separately |
| Worker-facing PII in an artifact | Quarantine the artifact and stop its distribution without echoing the payload | Review provenance, remove at the source, regenerate fail-closed, and document category/count and affected artifact hashes |
| Handoff or generated state disagrees with live state | Treat saved state as historical and pause mutation | Re-run pickup, engine-status, Git, process, and artifact-hash checks; regenerate only from authoritative inputs |
| Core gate fails | Do not tag or publish | Reproduce the smallest failing gate, fix the source of truth, then widen validation |
| Archive or restore check fails | Preserve all existing chunks and manifests; do not prune | Restore into an isolated destination, compare checksums, and repair the transaction before retrying retention work |

## First Week For A New Maintainer

1. Run the First 30 Minutes sequence from a fresh shell and save the receipt.
2. Walk the active workbench, live demo, A-00 proof path, optional benchmark
   lanes, and archived boundary with the outgoing maintainer.
3. Rehearse one documentation-only change through focused tests, public-surface
   validation, and a reviewable commit without publishing it.
4. Perform a private access/recovery check for every row in the ownership table.
5. Restore one durable archive into an isolated directory and verify checksums.
6. Review one benchmark result from prompt hash through cached response, judge
   artifact, coverage manifest, report, and bounded claim.
7. Review one dataset row from source/license through lineage, split, audit,
   quarantine/admission, registry, and model-card evidence.
8. Agree on maintenance cadence, security contact, release authority, and the
   first intentionally small backlog item.

## Handoff Acceptance

The transfer is operationally complete when both maintainers can truthfully
check every item:

- [ ] The successor can run the handoff and core scopes in a fresh shell and
      explain every failure, skip, and warning.
- [ ] Live whole-stack cost-stop state has been checked; no saved handoff was
      treated as proof of current task, sentinel, or process state.
- [ ] Active, optional, and archived Kaggle surfaces are correctly identified.
- [ ] The successor can explain the workbench, benchmark, data, and propose-only
      entity-intelligence boundaries.
- [ ] GitHub, Kaggle, hosting/domain, registry, model-provider, outreach, and
      backup access have private transfer receipts and tested recovery paths.
- [x] The project is explicitly in the maintenance mode defined by the
      transition plan; this decision does not itself accept a future successor.
- [ ] A restore rehearsal and a documentation-only change rehearsal succeeded.
- [ ] The first 30-day successor backlog has an owner, evidence target, and
      model-credit budget of zero unless separately approved.
- [x] The zero-item deferred-work register and dated 11-item closeout receipt
      validate; reopened work must acquire a named owner and acceptance evidence.

Until acceptance is complete, the safe default is preservation mode: keep the
whole model/flywheel stack cost-stopped, make deterministic maintenance changes
only, publish no new model or training claim, and retain all provenance.
