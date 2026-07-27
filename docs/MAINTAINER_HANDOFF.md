# Maintainer Handoff

This is the operational handoff for a person taking responsibility for DueCare.
It explains how to establish current truth, preserve the project's safety
boundaries, run routine checks, and decide what is safe to publish. The dated
closeout schedule is in the [30-day transition plan](PROJECT_TRANSITION_PLAN.md),
while the release boundary and evidence backlog remain in
[Publication readiness](PUBLICATION_READINESS.md).

**Handoff posture:** active closeout
**Prepared:** 2026-07-26
**Target transfer:** 2026-08-25
**Default model posture:** paused and zero planned model calls

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
- Set `DUECARE_MAX_PLANNED_MODEL_CALLS=0` for deterministic maintenance. This is
  a planning lock for guarded harnesses, not yet a universal transport budget.
- Generated report directories are not a backup. Preserve release artifacts in
  the approved release/archive location with checksums.

## Validation Ladder

Run the smallest applicable scope first, then widen only as needed:

| Scope | Command | Meaning |
|---|---|---|
| Handoff | `python scripts/validate_publication_readiness.py --scope handoff` | Succession docs, cross-links, privacy-safe content, pickup consistency, and paused-state evidence |
| Core release | `python scripts/validate_publication_readiness.py --scope core` | Eight model-free public, claim, Kaggle, source-smoke, and package-collection gates |
| Focused tests | `python -m pytest path/to/affected/tests -q` | Behavioral evidence for the edited area |
| Package collection | `python -m pytest packages --collect-only -q` | Published package-test inventory remains discoverable |
| Kaggle | `python scripts/validate_main_kaggle_kernels.py` and `py -3.12 scripts/validate_kaggle_page_sources.py` | Active kernel and generated-page contracts |
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
checkpoints, and keep a sanitized receipt. The missing universal control is a
shared atomic call/token/cash ledger around every provider attempt; until that
exists, treat the startup ceiling as an estimate rather than a billing limit.

### Publish or release

Use [Publication readiness](PUBLICATION_READINESS.md). Freeze the exact commit,
reconcile package versions, `CITATION.cff`, changelog, and tag as one decision,
run the core gate on that commit, retain the receipt, and state whether the
training scope passed. Publishing public hosting, Kaggle, PyPI, Hugging Face, or
GitHub releases remains an owner-authorized external action.

### Archive or recover

Use the durable archive tooling and preserve its transaction boundary: write
chunks, atomically commit the manifest, then prune superseded chunks. Test a
restore before treating an archive as valid. Never use ignored reports or a
working tree as the sole copy of release evidence.

## Current Open Work

| Priority | State at 2026-07-26 | Safe next action |
|---|---|---|
| P0 | The closeout branch includes current `origin/master` and passes the integrated gates; pull request 2 is the canonical review boundary, but this document is not proof of its live state | Check PR 2 and the exact `master` SHA; if open, review and merge it, and if merged, verify Actions, Render, and MkDocs Pages receipts before any tag |
| P0 | Release commit/tag and version decision are not frozen | Choose the bounded release claim, reconcile versions/citation/changelog, run privacy-safe scans and core/handoff gates on the exact commit |
| P0 | Ownership and platform access still belong to the current maintainer | Complete the private transfer receipt and successor rehearsal; do not place credentials in Git |
| P1 | Five dense generic-corridor typologies need diversification | Curate the manifest-planned 25 tasks / minimum 75 rows with lawful sources, lineage, and adjudication |
| P1 | Strict training quality and provenance are red | Close the curation queue, regenerate dependent artifacts sequentially, then append a new registry record through the normal path |
| P1 | Provider callers lack one enforceable attempt/token/cash budget | Add a shared atomic ledger in the generation transport and tests before broad model work |
| P2 | Per-dimension generation is complete but judging is incomplete | Keep it isolated; resume only with a frozen allowance and close the exact coverage manifest |
| P2 | Human review evidence is limited | Adjudicate a stratified high-severity and benign-control slice and publish agreement/disagreement policy |
| P3 | Legacy Ruff debt remains in long benchmark files | Isolate mechanical cleanup into behavior-preserving changes with regression evidence; the former constant-value pandas Styler warnings are fixed |
| P3 | Strict MkDocs stops on 84 legacy warnings; the two succession pages emit none | Classify unlisted/excluded pages, repo-external targets, and stale anchors before changing navigation or suppressions |

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
