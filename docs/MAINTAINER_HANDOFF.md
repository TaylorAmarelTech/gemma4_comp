# Maintainer Handoff

This is the operational handoff for a person taking responsibility for DueCare.
It explains how to establish current truth, preserve the project's safety
boundaries, run routine checks, and decide what is safe to publish. The dated
closeout schedule is in the [30-day transition plan](PROJECT_TRANSITION_PLAN.md),
while the release boundary and evidence backlog remain in
[Publication readiness](PUBLICATION_READINESS.md).

**Handoff posture:** active closeout
**Prepared:** 2026-07-27
**Target transfer:** 2026-08-25
**Default model posture:** paused and zero planned model calls

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
- no Ollama or hosted-model calls were made for the closeout or these receipts.

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

## First 30 Minutes

Use a Python 3.12 environment with the repository's development dependencies.
These checks are read-only or validation-only and do not call Ollama, a hosted
model, or the network:

```powershell
git status --short
$env:DUECARE_MAX_PLANNED_MODEL_CALLS='0'
python scripts/validate_maintainer_handoff.py
python scripts/validate_publication_readiness.py --scope handoff
python scripts/validate_publication_readiness.py --scope core
python scripts/validate_project_bible_pickup.py
python scripts/autonomous_engine.py --status
```

Expected stopping posture:

- the handoff scope and core publication scope are green;
- the autonomous engine reports stopped or paused, and
  `reports/autonomous_engine.stop` remains present;
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
3. [Publication readiness](PUBLICATION_READINESS.md) for the release boundary,
   known limitations, and prioritized model/data work.
4. [`project_status.md`](project_status.md) and root `kaggle/_INDEX.md` for
   current public inventory.
5. [`codex/PROJECT_BIBLE.md`](codex/PROJECT_BIBLE.md) for deep historical and
   autonomous-engine context.
6. Saved `.claude/state/` files and ignored reports as historical evidence only.

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
| GitHub Pages documentation | `docs/`, `mkdocs.yml`, and `requirements-docs.txt` on `master` | `.github/workflows/docs-deploy.yml` | This is the repository's only Pages deployer |
| Portable marketing-site bundle | Same FastAPI templates through `apps/duecare-ai.com/scripts/export_static.py` | `.github/workflows/duecare-site-build.yml` artifact | Build/download only; it must not call `actions/deploy-pages` in this repository |

The former manual `.github/workflows/pages.yml` marketing-site deploy was
removed because it could overwrite the MkDocs Pages site. If a static marketing
mirror is needed later, publish its bundle from a separate root-domain repository
or explicitly replace the docs site through a reviewed architecture decision.
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
| Core release | `python scripts/validate_publication_readiness.py --scope core` | Ten model-free public, claim, provider-budget, Kaggle, source-smoke, package-release, and package-collection gates |
| Focused tests | `python -m pytest path/to/affected/tests -q` | Behavioral evidence for the edited area |
| Package collection | `python -m pytest packages --collect-only -q` | Published package-test inventory remains discoverable |
| Kaggle | `python scripts/validate_main_kaggle_kernels.py` and `py -3.12 scripts/validate_kaggle_page_sources.py` | Active kernel and generated-page contracts |
| Provider budget | `python scripts/validate_provider_budget_coverage.py` | All four primary-router HTTP transports remain inside atomic reservations; this makes no provider call |
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

| Priority | State at 2026-07-27 | Safe next action |
|---|---|---|
| P0 | Independent package-version policy is frozen; all 18 wheels and source archives build reproducibly and clean-install as a cohort, but no release commit/tag exists and every distribution remains unpublished | Choose the first package, then rerun privacy-safe scans plus core/handoff gates on the exact release commit before creating its manifest-matched tag |
| P0 | Ownership and platform access still belong to the current maintainer | Complete the private transfer receipt and successor rehearsal; do not place credentials in Git |
| P1 | Active Kaggle 02 and A-00 latest runs are canceled; optional 03 has no verified public URL | Rerun 02 only for a needed recording and A-00 only for a funded proof; inspect artifacts before updating claims; keep 03 source-only |
| P1 | Five dense generic-corridor typologies need diversification; a deterministic 75-slot workbook and 12-source candidate registry now exist, with all slots unfilled and all sources training-blocked | Approve lawful immutable source snapshots, then fill the exact risk/benign/counterfactual slots with lineage and two-person adjudication; do not fabricate review |
| P1 | Strict training quality and provenance are red | Close the curation queue, regenerate dependent artifacts sequentially, then append a new registry record through the normal path |
| P2 | The primary generation router has an enforceable ledger, but direct package/application/standalone and self-contained notebook clients are not universally intercepted | Migrate one caller at a time with a zero-transport test; design a portable notebook receipt before broad live evaluation |
| P2 | Per-dimension generation is complete but judging is incomplete | Keep it isolated; resume only with a frozen allowance and close the exact coverage manifest |
| P2 | Human review evidence is limited | Adjudicate a stratified high-severity and benign-control slice and publish agreement/disagreement policy |
| P3 | Legacy Ruff debt remains in long benchmark files | Isolate mechanical cleanup into behavior-preserving changes with regression evidence; the former constant-value pandas Styler warnings are fixed |
| P3 | Refreshed actions passed the triggered CI, Pages, website-artifact, harness, and evaluation lanes; Docker, Helm, and PyPI publishing remain release-triggered | Validate those release-only lanes on the first approved release candidate/tag; do not dispatch a production publisher merely as a smoke test |

The detailed dataset/source ideas and ordered research backlog are maintained in
[Publication readiness](PUBLICATION_READINESS.md), not duplicated here.

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
| Unexpected model traffic or credit use | Stop the caller, restore the zero-call guard, leave the engine stop sentinel in place, and do not retry | Identify the exact caller and retry path from sanitized metadata; reconcile provider usage privately before any resume |
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
- [ ] Live paused state has been checked; no saved handoff was treated as proof
      of current engine/process state.
- [ ] Active, optional, and archived Kaggle surfaces are correctly identified.
- [ ] The successor can explain the workbench, benchmark, data, and propose-only
      entity-intelligence boundaries.
- [ ] GitHub, Kaggle, hosting/domain, registry, model-provider, outreach, and
      backup access have private transfer receipts and tested recovery paths.
- [ ] The release claim is frozen, or the project is explicitly placed into the
      maintenance mode defined by the transition plan.
- [ ] A restore rehearsal and a documentation-only change rehearsal succeeded.
- [ ] The first 30-day successor backlog has an owner, evidence target, and
      model-credit budget of zero unless separately approved.

Until acceptance is complete, the safe default is preservation mode: keep the
engine paused, make deterministic maintenance changes only, publish no new model
or training claim, and retain all provenance.
