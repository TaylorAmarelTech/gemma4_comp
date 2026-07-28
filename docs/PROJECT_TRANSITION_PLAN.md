# 30-Day Project Transition Plan

This plan turns the final month of primary-maintainer involvement into a
verifiable transfer rather than an informal document dump. Operational pickup
for coding agents is defined in the
[Claude Code handoff](CLAUDE_CODE_HANDOFF.md), human operations are in the
[Maintainer handoff](MAINTAINER_HANDOFF.md), and the public release
boundary, limitations, dataset plan, and model-work backlog remain in
[Publication readiness](PUBLICATION_READINESS.md).
Every unfinished action is normalized in the generated
[Deferred work register](DEFERRED_WORK.md); that register wins if a duplicated
status, owner, boundary, or acceptance test drifts.
The immutable outcome of the inherited queue is the
[2026-07-28 closeout resolution receipt](CLOSEOUT_RESOLUTIONS_2026_07_28.md).
The repeatable technical exercise is the
[successor pickup rehearsal](SUCCESSOR_REHEARSAL.md).

**Status:** maintenance mode enacted; zero current deferred items
**Start date:** 2026-07-26
**Target handoff date:** 2026-08-25
**Model-quota posture:** whole model/flywheel stack cost-stopped; deterministic
work only unless a separate frozen, budgeted run is approved

## Enacted Closeout Decision - 2026-07-28

The repository owner delegated the remaining bounded decisions, and maintenance
mode is now effective. Keep Render production, the independent read-only
continuity site, GitHub Pages documentation, the source repository, and existing
published research artifacts running. Keep all recurring model/flywheel tasks
disabled and planned model calls at zero.

All 11 inherited register items have explicit outcomes rather than silent
deferral: one current source-freshness cycle completed; the release disposition
was decided; private ownership was retained by the current owner; historical
provider usage closed with an explicit unknown residual risk; and package,
model, notebook, per-dimension, training-curation, provenance, and human-study
work was declined or excluded from claims where its evidence did not exist.
No package, model, dataset, notebook, image, chart, or private account was
published or transferred to manufacture a completed checklist.

The dated schedule below remains the tested successor-transfer playbook if a
maintainer later accepts the project. It is not an open requirement to spend
credits, recruit reviewers, or publish artifacts before the current owner moves
on. The next scheduled source-freshness review is 2026-10-28.

If the actual departure date changes, move the calendar dates together while
preserving the sequence, evidence requirements, and final rehearsal window.

## Definition Of Done

The project has reached a good stopping point when:

- a named successor can establish live state, explain system boundaries, run
  the handoff and core release gates, and recover from common incidents;
- or, if no successor is available, DueCare is deliberately placed in a
  documented maintenance mode with the whole model/flywheel stack stopped and
  no implied support or fresh-model promise;
- an exact commit/tag and bounded claim set are chosen, or a written no-release
  decision is recorded;
- package versions, `CITATION.cff`, changelog, release notes, datasets, active
  Kaggle references, and public docs agree at that exact revision;
- access, recovery, domain/hosting, registries, provider billing, outreach, and
  archive ownership have private transfer receipts, or the current owner is
  explicitly retained as the private maintenance/recovery authority;
- core, handoff, and relevant focused gates have saved receipts, while any red
  training or experimental lane is plainly described and isolated;
- no raw worker data, private case material, credentials, ignored staging
  reports, or unreviewed entity allegations are published; and
- a future successor's first reopened item must have a clear owner, acceptance
  test, and explicit model-credit budget; and
- `DEFERRED_WORK.md` is current, placeholder-free, and agrees with the public
  status, release boundary, and owner-only checklist.

## Workstreams And Deliverables

| Workstream | Required deliverable | Evidence |
|---|---|---|
| Current truth | Live-state inventory and deliberate-stops register | Handoff/core receipts, whole-stack cost-stop status, engine status, branch/status snapshot |
| Product boundary | Maintainer can explain active, optional, archived, and propose-only surfaces | Handoff rehearsal notes and architecture walkthrough |
| Release | Exact release or no-release decision | Commit/tag, release notes, version/citation reconciliation receipt |
| Data and research | Accepted datasets separated from candidate, quarantine, and experimental evidence | Manifests, lineage/audit results, limitations register |
| Operations | Access, recovery, alerts, backups, and publishing authority transferred | Private least-privilege transfer receipts |
| Public deployment | Render production, independent read-only continuity Pages, and MkDocs Pages have distinct, tested ownership | Website health, continuity `source_revision`, docs workflow receipt, and no competing deployer in this source repository |
| Documentation | Public entry points and purpose maps lead to current handoff/release truth | Handoff validation and public-surface audit |
| Continuity | Successor completes a fresh-shell pickup, safe change, and restore rehearsal | Signed or dated rehearsal record outside the public repo if it names people |

## Week 1 - Inventory And Freeze Candidate

**2026-07-26 through 2026-08-01**

- Freeze scope: no broad new features, datasets, judging sweeps, or model runs.
- Inventory live Git/process/engine state and compare it with saved `.claude`
  state, ignored reports, status docs, and public claims.
- Preserve the 2026-07-27 correction: a paused autonomous engine did not stop
  the independent discovery and server-automation watchdogs. The verified
  closeout disables all five recurring tasks, keeps four daemon sentinels, and
  requires zero verified repository daemon processes; historical unmetered
  background usage is reconciled privately at the provider.
- The pre-closeout sequence advanced through pull requests 11 through 16. Pull
  request 16 is the immediate fully merged predecessor to this maintenance
  receipt at `1c8f6b25729da869b2775a29321ab3b74bd4715f`; all 16 checks passed.
  Pull request 15's 4,646-pass local run remains older historical evidence.
  Render stayed live, the independent `duecare-ai-site` continuity
  repository published the reviewed 51-route backend-free export without a
  production `CNAME`, and this monorepo retained MkDocs as its Pages site. Pull
  request 14 also corrected the homepage worker-story grid that had squeezed
  body text into the 28-pixel number column. Use live `master` as the base and
  rerun gates on every later candidate.
- Keep the handoff, transition plan, deferred-work registry, purpose maps, and
  navigation links reconciled through their deterministic validators.
- Confirm the canonical active Kaggle surfaces and keep optional/archived lanes
  labeled correctly.
- Classify every open item as release-blocking, successor backlog, experimental,
  or deliberately stopped in `configs/duecare/deferred_work.json`.
- Choose a release candidate claim set. The default is a core/docs/data release
  with no new training/model-improvement claim while the strict training gate
  remains red.
- Start the private access inventory without copying credentials into tickets,
  chat logs, or the repository.

**Exit evidence:** handoff and core gates green in the working environment;
known red lanes recorded; candidate release boundary agreed.

## Week 2 - Release Candidate And Transfer Package

**2026-08-02 through 2026-08-08**

- Reconcile package/workspace versions, `CITATION.cff`, changelog, dataset
  versions, Kaggle pins, and release notes as one proposed release decision.
- Run focused regressions, the full practical regression suite, public-surface
  checks, package collection, Kaggle validators, and privacy-safe secret/data
  scans. Preserve exact warnings and skips.
- Build the source/release artifacts reproducibly and record hashes; do not
  upload them yet unless external publication is separately authorized.
- Verify a durable archive and isolated restore, including generated evidence
  needed to support published claims.
- Complete private access-transfer invitations using least privilege, and test
  recovery/second-factor paths without sharing recovery material in Git.
- Prepare a one-hour architecture/evidence walkthrough using one benchmark
  trace and one dataset-lineage trace end to end.

**Exit evidence:** release-candidate receipt, artifact hashes, restore receipt,
and access-transfer matrix ready for successor rehearsal.

## Week 3 - Successor Rehearsal And Knowledge Transfer

**2026-08-09 through 2026-08-15**

- Have the successor execute the First 30 Minutes sequence from a fresh shell
  without relying on the outgoing maintainer's command history.
- Rehearse a documentation-only change through review, focused tests, public
  validation, commit, and rollback/recovery planning without publishing.
- Walk active workbench behavior, shared model loading, deterministic/model
  boundaries, benchmark comparability, dataset admission, entity-intelligence
  quarantine, and archived Kaggle surfaces.
- Rehearse incident responses for unexpected provider traffic, a suspected
  secret, a worker-data leak, stale generated state, and a failed core gate.
- Let the successor identify one confusing or fragile area; improve the docs or
  test that would have prevented the confusion.
- Decide maintenance cadence, issue/security intake, release authority, and the
  first 30-day successor backlog.

**Exit evidence:** successor pickup receipt, safe-change rehearsal, incident
walkthrough, and documented corrections from rehearsal feedback.

## Week 4 - Final Fixes And Release Decision

**2026-08-16 through 2026-08-22**

- Fix only issues discovered by rehearsal or release validation that threaten
  safety, reproducibility, pickup, or the bounded release claim.
- Rerun affected tests, handoff scope, core scope, pickup validation, and public
  surface checks on the proposed final revision.
- Verify `duecare-ai.com/project-status` from Render, the read-only continuity
  export at `tayloramareltech.github.io/duecare-ai-site/` including its
  `source_revision`, and the MkDocs handoff pages after the release revision
  reaches `master`; do not deploy a marketing bundle into the documentation
  Pages environment or assign production DNS to the fallback incidentally.
- Record the training gate as passing or explicitly red. Do not weaken it and do
  not delay a valid no-new-training-claim core release solely to manufacture a
  green training lane.
- Confirm the incomplete per-dimension lane remains isolated from the default
  comparable board and is described as partial evidence.
- Finish private ownership/recovery receipts and remove outgoing access only
  after incoming access has been tested.
- Choose one of three explicit outcomes: publish/tag the bounded release, defer
  release with a dated reason, or enter maintenance mode.

**Exit evidence:** final decision record, exact revision, complete validation
receipt, limitations, and tested successor or maintenance-mode owner.

## Final 72 Hours

**2026-08-23 through 2026-08-25**

1. Freeze nonessential changes and rerun live-state, handoff, core, and pickup
   checks on the exact final revision.
2. Confirm domain/hosting, GitHub, Kaggle, registry, provider, outreach, alerts,
   billing, backup, and recovery ownership from the private receipt.
3. Publish/tag only the previously approved bounded artifacts. Record immutable
   links and hashes without copying secrets or private receipts into the repo.
4. Verify the public landing page, documentation, release, active Kaggle links,
   and citation/version text from an unauthenticated view.
5. Leave the whole model/flywheel stack cost-stopped. A future maintainer may
   resume it only through an explicit budgeted plan and current authorization.
6. Archive the closeout receipts and limitations, then remove outgoing access
   according to the agreed recovery plan.

No new feature, dataset family, provider integration, or broad benchmark run
enters this window.

## Owner-Only Actions

These actions require the current account owner or an explicitly authorized
successor; local repository edits do not complete them:

- approve the release/no-release/maintenance-mode decision and bounded claims;
- transfer or invite GitHub, Kaggle, hosting/domain/DNS, PyPI, Hugging Face,
  monitoring, archive, shared-mailbox, and model-provider access;
- verify billing, recovery, two-factor, security-contact, and revocation paths;
- rotate any credential involved in an incident and review platform audit logs;
- publish a GitHub release, package, model/dataset, Kaggle revision, website
  deployment, or competition submission;
- authorize any nonzero model-credit budget, removal of the four daemon stop
  sentinels, or re-enabling of the recurring tasks; and
- decide whether to retain, transfer, or retire public support commitments.

The resolved owner-decision ledger is [`USER_TODO.md`](USER_TODO.md), the dated
acceptance record is
[`CLOSEOUT_RESOLUTIONS_2026_07_28.md`](CLOSEOUT_RESOLUTIONS_2026_07_28.md), and
[`DEFERRED_WORK.md`](DEFERRED_WORK.md) is reserved for genuinely reopened work.

The repository may document commands and public identifiers, but must never
store the private receipt's secrets, recovery answers, personal contact details,
or billing information.

## Decision Register

| Decision | Current disposition | Revisit trigger |
|---|---|---|
| Core release versus new training claim | Maintenance mode enacted; no new release and no new training/model-improvement claim | A maintainer proposes a named bounded artifact and the relevant strict gates pass on a new append-only record |
| Model usage during closeout | Zero planned calls by default; deterministic closeout commands need no Ollama or hosted-model spend. Historical auxiliary-daemon usage before the whole-stack correction is unknown locally. | Owner reconciles provider-side usage and approves a frozen sampled plan with finite allowance and stop condition |
| Model/flywheel stack | All five recurring tasks disabled, four sentinels present, and zero verified repository daemons; no automatic resume | Explicit current authorization plus live preflight, finite budget, reviewed pricing, and review plan |
| Comparable benchmark board | Keep v1/h1 batched evidence as default | A versioned successor board is complete and independently documented |
| Exhaustive per-dimension lane | Exhaustive closure declined as low-value; partial evidence stays experimental and isolated | A preregistered narrower slice has positive expected information value and a frozen budget |
| Entity-intelligence pipeline | Propose-only, curator-reviewed, separate from worker-facing and training paths | A reviewed governance and evidence-admission change is approved |
| Kaggle surface inventory | `01`, `02`, and `A-00` active; `03` and `04` optional; notebook-era variants archived | Root `AGENTS.md` and `kaggle/_INDEX.md` change together |
| Release version/tag | No release tag or PyPI publication during closeout | A real consumer need and a maintainer-owned package release proposal exist |
| Target branch | Root rules name `master`; pull request 16 at `1c8f6b25729da869b2775a29321ab3b74bd4715f` is the immediate fully merged predecessor, with all 16 checks green | Continue from live `master`; rerun gates on the exact candidate before any tag |
| Successor | Current owner retains private maintenance/recovery authority; no transfer is claimed | A named successor is authorized, accepts, and completes the rehearsal plus private receipt |

### Historical Pre-decision Snapshot - 2026-07-27

This earlier snapshot authorized reconciling and publishing the GitHub
source, documentation, website, and Pages changes after the deterministic gates
pass. The bounded local release-candidate disposition is:

- preserve independent package SemVer and build all 18 wheel/source cohorts,
  but do not publish a Python distribution until its exact package tag and
  trusted-publisher path are deliberately selected;
- validate Docker and Helm locally, but publish container/chart artifacts only
  from the guarded release workflow on an approved tag or explicit publish
  dispatch;
- keep all five root notebook sources executable and model-free in local
  validation, without spending Kaggle or model quota merely to refresh a run;
- make no new trained-model, dataset-quality, or field-effectiveness claim;
- keep the whole model/flywheel stack cost-stopped and planned model calls at
  zero; and
- prefer a tested successor transfer, with documented maintenance mode as the
  automatic safe outcome if no successor accepts by the final-decision window.

It is superseded by the enacted 2026-07-28 maintenance decision above. This
snapshot authorized repository reconciliation; it did not claim that
private accounts have been transferred or that external registries have been
published. Those outcomes require the owner-only evidence listed above.

## Maintenance-Mode Exit Receipt

The no-release maintenance branch is complete when the final published
revision preserves each statement below. These checks close the current
transition; they do not claim a successor transfer, a package/model/dataset
release, independent human review, or reconciliation of historical pre-ledger
provider usage.

- [x] `validate_publication_readiness.py --scope handoff` passes (2/2 checks).
- [x] `validate_publication_readiness.py --scope core` passes (12/12 checks).
- [x] The exact broad regression is recorded: 4,653 passed and 9 skipped in
      8:04, with the intentionally red training and partial experimental lanes
      excluded from release claims.
- [x] Public docs, purpose maps, Project Bible, status, roadmap, Kaggle index,
      generated zero-item deferred-work register, unchanged package versions,
      unchanged citation metadata, and explicit no-release decision agree.
- [x] The handoff validator reports category/count-only sensitive-data results;
      a redacted `gitleaks` scan found no leaks in the 243 KB staged change,
      and the final GitHub revision must also pass the full-history CI job.
- [x] The durable archive reassembled 52/52 checksum-bound files in an isolated
      restore rehearsal. No new release artifact was created by decision.
- [x] Private platform transfer was declined. The current owner remains the
      maintenance and recovery authority; the public repository contains no
      credentials or unverified private access receipt.
- [x] The automated successor rehearsal passed all five scenarios, and the
      no-successor maintenance-mode alternative was enacted.
- [x] The whole model/flywheel stack is cost-stopped, recurring tasks remain
      disabled, planned model calls are zero, and future model work has no
      implied authorization.
- [x] The final decision is maintenance mode effective 2026-07-28, with no new
      package, model, dataset, notebook, or benchmark release.

## If No Successor Is Available

Use maintenance mode rather than leaving an ambiguous live project:

1. Keep the whole model/flywheel stack cost-stopped and the zero-call default
   documented; include the Windows `stop_ollama_stack.ps1 -Status` check in
   successor acceptance.
2. Freeze the last supported commit, release artifacts, checksums, docs, and
   limitations; do not imply that volatile legal/operational facts stay fresh.
3. Add a dated public maintenance notice that names the support and security
   posture without exposing personal contact information.
4. Disable or narrow unattended deployments, provider credentials, write
   integrations, webhooks, and billing only through their owner-authorized
   platform controls.
5. Preserve the repository and public research artifacts unless the owner makes
   a separate archival decision. Repository archival is an external/manual
   action, not an automatic closeout step.
6. Retain a private recovery owner for domain, hosting, security reports, and
   backups, with a periodic renewal/expiry calendar.
7. Keep candidate data, unreviewed entity matches, partial judge lanes, and
   ignored reports out of publication.

Maintenance mode is a responsible stopping point, not a claim that every
research lane or product roadmap item is complete.

## Future Improvements

These are ordered for a successor; they are not exit blockers unless promoted
by the Decision Register. Operational ownership, prerequisites, budgets, and
acceptance evidence live in [`DEFERRED_WORK.md`](DEFERRED_WORK.md); the themes
below do not override it.

### Reliability and maintenance

1. Add the handoff/core gates to continuous integration with pinned Python
   versions and artifact receipts.
2. Automate version/citation/changelog consistency checks and reproducible
   release builds without automating publication authority.
3. Keep the completed three-file Ruff cleanup enforced without file-wide
   suppressions or reintroducing its retired deferred-work entry.
4. Keep the strict-MkDocs repository-link resolver test-covered, and reduce
   informational notices only when doing so preserves the intentional
   public-versus-provenance navigation boundary.
5. The refreshed CI, Pages, website-artifact, harness, evaluation, and Gitleaks
   actions passed without the Node 20 annotation on 2026-07-27. Validate the
   release-triggered Docker, Helm, and package actions on the first approved
   release candidate/tag rather than dispatching a production smoke test.
6. Add restore drills, dependency/security review cadence, and a dated legal and
   public-source freshness dashboard.

### Ollama and provider calls

1. Keep the completed ledger mandatory for every `llm_generate.py` attempt and
   the adverse-media verifier; migrate other standalone/application/package
   clients and design a portable notebook equivalent one caller at a time.
2. Make retry classification explicit: retry transient transport/service errors
   only; fail closed on authentication, permission, quota, and invalid requests.
3. Use content-addressed generation/judging caches keyed by provider, immutable
   model revision, prompt, rubric, decoding settings, and harness version.
4. Add preflight capability discovery and a dry-run plan that cannot start a
   daemon, write a heartbeat, or mutate result artifacts.
5. Spend first on a small stratified smoke matrix, then allocate extra judging
   only to disagreement, calibration, and decision-boundary cells.
6. Emit sanitized budget and coverage receipts so an interrupted run can resume
   without duplicate paid calls.
7. Treat **Kimi K3** and **Meta Muse Spark 1.1** as required future comparison
   lanes. Reverify exact provider identifiers, access, modalities, context, and
   pricing before spending; report an unavailable lane rather than silently
   substituting another model.

### Dataset and evaluation quality

1. Close the current 25-task / exact 75-slot corridor-diversification plan with
   lawful dated sources, lineage, two-person adjudication for severe cases, and
   no threshold weakening.
2. Add dataset cards with license/terms snapshots, inclusion/exclusion reasons,
   transformation code, source freshness, language/corridor coverage, and known
   harms for every publishable dataset family.
3. Strengthen near-duplicate and lineage-family leakage detection across
   supervised, preference, reward, benchmark, quarantine, and held-out splits.
4. Add multilingual and code-switch evaluation designed with native speakers,
   including abstention, translation drift, and culturally specific hard
   negatives.
5. Build temporal legal-freshness and source-ablation lanes so the project can
   measure when retrieval is stale or a response depends on one weak source.
6. Publish human-adjudication protocol, agreement, disagreement taxonomy,
   severity stratification, and benign-control performance before stronger
   safety claims.
7. Keep synthetic/model-generated candidates labeled and quarantined until
   provenance, privacy, diversity, and human/rule-based admission gates pass.

### Research and product evidence

1. Complete the isolated per-dimension lane only under a frozen budget and exact
   coverage manifest; never backfill it into v1/h1 silently.
2. Add calibration, abstention, uncertainty, and selective-judge escalation
   reporting rather than relying on aggregate score lift alone.
3. Run a small prospective study with NGO/caseworker review, ethics and privacy
   controls, predeclared outcomes, and a clear boundary between usability and
   field-effectiveness claims.
4. Test cross-corridor counterfactual consistency and subgroup error patterns,
   then publish harms and regressions alongside wins.
5. Convert repeated operational lessons into narrow tests and decision records
   before expanding the application surface.

The best first successor milestone is intentionally modest: keep all model calls
locked, make the handoff/core gates reproducible in a fresh environment, close
one evidence-backed documentation or dataset-quality gap, and preserve the
project's honest claim boundary.
