# 30-Day Project Transition Plan

This plan turns the final month of primary-maintainer involvement into a
verifiable transfer rather than an informal document dump. Operational pickup
is defined in the [Maintainer handoff](MAINTAINER_HANDOFF.md); the public release
boundary, limitations, dataset plan, and model-work backlog remain in
[Publication readiness](PUBLICATION_READINESS.md).

**Status:** active closeout
**Start date:** 2026-07-26
**Target handoff date:** 2026-08-25
**Model-quota posture:** locked by default; deterministic work only unless a
separate frozen, budgeted run is approved

If the actual departure date changes, move the calendar dates together while
preserving the sequence, evidence requirements, and final rehearsal window.

## Definition Of Done

The project has reached a good stopping point when:

- a named successor can establish live state, explain system boundaries, run
  the handoff and core release gates, and recover from common incidents;
- or, if no successor is available, DueCare is deliberately placed in a
  documented maintenance mode with the engine paused and no implied support or
  fresh-model promise;
- an exact commit/tag and bounded claim set are chosen, or a written no-release
  decision is recorded;
- package versions, `CITATION.cff`, changelog, release notes, datasets, active
  Kaggle references, and public docs agree at that exact revision;
- access, recovery, domain/hosting, registries, provider billing, outreach, and
  archive ownership have private transfer receipts;
- core, handoff, and relevant focused gates have saved receipts, while any red
  training or experimental lane is plainly described and isolated;
- no raw worker data, private case material, credentials, ignored staging
  reports, or unreviewed entity allegations are published; and
- the successor's first small backlog item has a clear owner, acceptance test,
  and explicit model-credit budget.

## Workstreams And Deliverables

| Workstream | Required deliverable | Evidence |
|---|---|---|
| Current truth | Live-state inventory and deliberate-stops register | Handoff/core receipts, engine status, branch/status snapshot |
| Product boundary | Maintainer can explain active, optional, archived, and propose-only surfaces | Handoff rehearsal notes and architecture walkthrough |
| Release | Exact release or no-release decision | Commit/tag, release notes, version/citation reconciliation receipt |
| Data and research | Accepted datasets separated from candidate, quarantine, and experimental evidence | Manifests, lineage/audit results, limitations register |
| Operations | Access, recovery, alerts, backups, and publishing authority transferred | Private least-privilege transfer receipts |
| Public deployment | Render website and MkDocs Pages have distinct, tested ownership | Website health, docs workflow receipt, and absence of a competing Pages deployer |
| Documentation | Public entry points and purpose maps lead to current handoff/release truth | Handoff validation and public-surface audit |
| Continuity | Successor completes a fresh-shell pickup, safe change, and restore rehearsal | Signed or dated rehearsal record outside the public repo if it names people |

## Week 1 - Inventory And Freeze Candidate

**2026-07-26 through 2026-08-01**

- Freeze scope: no broad new features, datasets, judging sweeps, or model runs.
- Inventory live Git/process/engine state and compare it with saved `.claude`
  state, ignored reports, status docs, and public claims.
- The reconciled `codex/full-flywheel-training-20260714` closeout branch was
  merged through pull request 2 to `master` as
  `07cfdbfd00e1bc304ffc1f8b2736c4d93bbf0eab`. Post-merge CI, MkDocs Pages,
  the artifact-only website build, and the Render project-status route were
  verified on 2026-07-26. Pull request 4 then merged the final public-surface,
  package-release, Kaggle-link, and handoff reconciliation as
  `dc313814d9f42e127b24191b7912fd521083fadd` on 2026-07-27. Its post-merge CI
  and both public deployment paths passed; all six schema routes returned 200
  and the refreshed 577-link audit found zero confirmed breakage. Use current
  `master` as the integrated base.
- Land this handoff, transition plan, deterministic handoff validator, purpose
  maps, and navigation links.
- Confirm the canonical active Kaggle surfaces and keep optional/archived lanes
  labeled correctly.
- Classify every open item as release-blocking, successor backlog, experimental,
  or deliberately stopped.
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
- Verify `duecare-ai.com/project-status` from Render and the MkDocs handoff pages
  from GitHub Pages after the release revision reaches `master`; do not deploy a
  marketing bundle into the documentation Pages environment.
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
5. Leave the autonomous engine paused. A future maintainer may resume it only
   through an explicit budgeted plan and current authorization.
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
- authorize any nonzero model-credit budget or removal of the engine stop
  sentinel; and
- decide whether to retain, transfer, or retire public support commitments.

The repository may document commands and public identifiers, but must never
store the private receipt's secrets, recovery answers, personal contact details,
or billing information.

## Decision Register

| Decision | Current disposition | Revisit trigger |
|---|---|---|
| Core release versus new training claim | A bounded core release may proceed while training stays red, provided it explicitly makes no new training/model-improvement claim | Strict quality and provenance gates pass on a new append-only record |
| Model usage during closeout | Zero planned calls by default; no Ollama or hosted-model spend is needed for closeout | Owner approves a frozen sampled plan with finite allowance and stop condition |
| Autonomous engine | Intentionally paused; no automatic resume | Explicit current authorization plus live preflight, budget, and review plan |
| Comparable benchmark board | Keep v1/h1 batched evidence as default | A versioned successor board is complete and independently documented |
| Exhaustive per-dimension lane | Generation complete, judging incomplete, experimental and isolated | Exact coverage manifest reaches closure under a frozen budget |
| Entity-intelligence pipeline | Propose-only, curator-reviewed, separate from worker-facing and training paths | A reviewed governance and evidence-admission change is approved |
| Kaggle surface inventory | `01`, `02`, and `A-00` active; `03` and `04` optional; notebook-era variants archived | Root `AGENTS.md` and `kaggle/_INDEX.md` change together |
| Release version/tag | Pending a deliberate owner decision | Week 2 release-candidate reconciliation is reviewed |
| Target branch | Root rules name `master`; pull request 4 merged the final reconciliation as `dc313814d9f42e127b24191b7912fd521083fadd`, and post-merge CI plus both public deployment paths were verified | Continue from current `master`; rerun gates on the exact candidate before any tag |
| Successor | Transfer path preferred; maintenance mode is the safe fallback | A successor accepts and completes the rehearsal |

## Exit Criteria

Before declaring the transition complete, retain evidence that:

- [ ] `validate_publication_readiness.py --scope handoff` passes on the final
      revision.
- [ ] `validate_publication_readiness.py --scope core` passes on the final
      revision.
- [ ] Focused and broad regression commands, skips, warnings, platform caveats,
      and any intentionally red training gate are recorded exactly.
- [ ] Public docs, purpose maps, Project Bible, status, roadmap, Kaggle index,
      changelog, versions, citation, tag, and release notes agree.
- [ ] A category/count-only sensitive-data scan and a secret scanner have been
      run without printing matched payloads into the receipt.
- [ ] Release artifacts and critical evidence have checksums and a tested
      isolated restore.
- [ ] Each platform has a privately retained access, recovery, least-privilege,
      and revocation receipt.
- [ ] The successor passed fresh-shell pickup, safe-change, architecture,
      incident, and restore rehearsals; or maintenance mode was enacted.
- [ ] The engine remains paused and model work has no implied authorization.
- [ ] The final release/no-release/maintenance decision and effective date are
      recorded.

## If No Successor Is Available

Use maintenance mode rather than leaving an ambiguous live project:

1. Keep the engine paused and the zero-call default documented.
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
by the Decision Register.

### Reliability and maintenance

1. Add the handoff/core gates to continuous integration with pinned Python
   versions and artifact receipts.
2. Automate version/citation/changelog consistency checks and reproducible
   release builds without automating publication authority.
3. Isolate legacy Ruff cleanup into small behavior-preserving changes.
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

1. Put every provider attempt behind one atomic ledger that reserves and settles
   calls, input/output tokens, estimated cash, retries, and cancellation.
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

### Dataset and evaluation quality

1. Close the current 25-task / minimum 75-row corridor-diversification plan with
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
