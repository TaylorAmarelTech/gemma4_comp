# Deferred Work Register

This document is generated from
[`configs/duecare/deferred_work.json`](../configs/duecare/deferred_work.json).
It is the canonical boundary between work that can be completed in a
model-free repository change and work that requires private access, human
review, owner authorization, provider spend, or Kaggle quota.

**Current as of:** 2026-07-27

**Maintenance posture:** Core source, documentation, public deployments, and deterministic gates are maintained; model spending, new training claims, and registry publication remain separately authorized activities.

## Completion Policy

An item may move to completed only after every acceptance gate has dated evidence.

A deferred or blocked item must not be described as shipped, published, transferred, reconciled, or scientifically complete.

No item authorizes removal of stop sentinels, re-enabling scheduled tasks, provider calls, Kaggle quota use, or registry publication.

Private receipts retain account, billing, recovery, and reviewer identity details outside Git; public evidence records only dates, categories, decisions, hashes, and pass or fail state.

A status records why work is not complete; it is not permission to bypass
the listed boundary. Empty fields, fabricated approvals, guessed versions,
and undated completion claims are rejected by
`python scripts/validate_deferred_work.py`.

## Summary

| Priority | Work item | Status | Owner role | Model-credit policy |
|---|---|---|---|---|
| P0 | [Reconcile historical provider usage privately](#provider-usage-reconciliation) | Blocked: private access | Model-provider account owner | zero_only |
| P0 | [Transfer platform access and recovery authority](#private-platform-transfer) | Blocked: private access | Current owner and authorized successor | zero_only |
| P0 | [Choose release, dated deferral, or maintenance mode](#release-disposition) | Deferred: owner decision | Release owner | zero_only |
| P1 | [Publish the first independently versioned Python package](#first-package-publication) | Deferred: owner decision | Release owner | zero_only |
| P1 | [Complete the 75-row corridor-diversification workbook](#corridor-curation) | Blocked: human review | Two independent data curators | zero_only |
| P1 | [Refresh training quality and append-only provenance](#training-provenance-refresh) | Blocked: human review | Training-data curator and release reviewer | zero_only |
| P1 | [Run a small frozen frontier model smoke matrix](#bounded-model-smoke) | Deferred: budget or quota | Model-spend approver and benchmark maintainer | nonzero_requires_owner_approval |
| P3 | [Complete the isolated exhaustive per-dimension judge lane](#per-dimension-judging) | Deferred: budget or quota | Research lead and model-spend approver | nonzero_requires_owner_approval |
| P2 | [Run only justified Kaggle evidence jobs](#optional-kaggle-reruns) | Deferred: budget or quota | Kaggle account owner and evidence reviewer | nonzero_requires_owner_approval |
| P2 | [Extend budget enforcement beyond the primary router](#direct-client-budget-migration) | Ready: local and model-free | Maintainer | zero_only |
| P2 | [Create a human gold set and agreement monitor](#human-gold-calibration) | Blocked: human review | Qualified domain reviewers and evaluation lead | zero_only |
| P3 | [Clear legacy lint debt in behavior-preserving slices](#legacy-ruff-cleanup) | Ready: local and model-free | Maintainer | zero_only |
| P1 | [Review volatile legal and operational sources on a cadence](#source-freshness-maintenance) | Recurring maintenance | Knowledge curator | zero_only |

## Pickup Order

The safe sequence is:

1. Preserve the whole-stack cost stop and establish live Git, process,
   scheduler, provider, and publication truth.
2. Complete local model-free items in small reviewable changes.
3. Continue recurring source-freshness work without silently replacing
   older evidence.
4. Start a gated item only when its owner, prerequisites, and authorization
   are present; then retain every acceptance artifact.

**Ready for model-free repository work:** `direct-client-budget-migration`, `legacy-ruff-cleanup`.

**Recurring maintenance:** `source-freshness-maintenance`.

**Externally or human gated:** `provider-usage-reconciliation`, `private-platform-transfer`, `release-disposition`, `first-package-publication`, `corridor-curation`, `training-provenance-refresh`, `bounded-model-smoke`, `per-dimension-judging`, `optional-kaggle-reruns`, `human-gold-calibration`.

## Reconcile historical provider usage privately
<a id="provider-usage-reconciliation"></a>

- **ID:** `provider-usage-reconciliation`
- **Priority:** P0
- **Status:** Blocked: private access
- **Owner role:** Model-provider account owner
- **Target:** Before any model caller is resumed or any provider-spend claim is published
- **Model-credit policy:** `zero_only`
- **Network/write policy:** `private_read_only`
- **Depends on:** No other register item

**Why it remains open:** Auxiliary scheduled callers ran after the main engine pause, and no repository-local provider ledger covered that interval.

### Prerequisites

- Authorized access to the provider usage, quota, and billing dashboard
- The latest ignored reports/cost_stop_status.json receipt from the Windows automation host

### Ordered next actions

1. Review account-side usage from the last owner-verified budget receipt through the checked_at timestamp in reports/cost_stop_status.json.
2. Compare calls, tokens, quota changes, and charges with account alerts and any retained private receipts.
3. Retain the detailed reconciliation privately and record only completion date, reviewer role, provider category, and discrepancy count in the transfer receipt.

### Done only when

- A private dated reconciliation covers the full unmetered interval.
- Any unexplained usage has an owner-approved incident disposition.
- No credential, invoice, account identifier, or billing detail is committed to Git.

### Evidence and controls

- [`docs/PROVIDER_BUDGETING.md`](PROVIDER_BUDGETING.md)
- [`docs/PRIVATE_TRANSFER_RECEIPT_TEMPLATE.md`](PRIVATE_TRANSFER_RECEIPT_TEMPLATE.md)
- [`scripts/stop_ollama_stack.ps1`](../scripts/stop_ollama_stack.ps1)

## Transfer platform access and recovery authority
<a id="private-platform-transfer"></a>

- **ID:** `private-platform-transfer`
- **Priority:** P0
- **Status:** Blocked: private access
- **Owner role:** Current owner and authorized successor
- **Target:** Before 2026-08-25 or before outgoing access is removed
- **Model-credit policy:** `zero_only`
- **Network/write policy:** `owner_authorized_write`
- **Depends on:** No other register item

**Why it remains open:** GitHub, Kaggle, hosting, domain, package, model-provider, monitoring, mailbox, and recovery controls cannot be proven by repository edits.

### Prerequisites

- A named authorized successor or a named private maintenance owner
- Least-privilege access to every platform listed in the private transfer receipt
- A reviewed hosting disposition that keeps Render, moves the public domain to a backend-free GitHub Pages fallback, or retains both during a timed rollback window

### Ordered next actions

1. Invite the successor with least privilege and verify login, recovery, billing visibility, audit-log access, and revocation paths one platform at a time.
2. Complete the private transfer receipt without copying personal contacts, recovery answers, credentials, or billing records into Git.
3. Before retiring Render, publish the backend-free static bundle from a dedicated GitHub Pages repository at a domain root, label or disable stateful features, verify the public route set, and retain a tested DNS rollback window.
4. Remove outgoing access only after the successor demonstrates recovery and the successor rehearsal passes on the final revision.

### Done only when

- Every platform row in the private receipt has a dated owner and tested recovery path.
- If Render is retired, duecare-ai.com serves the reviewed static fallback without calling the retired backend, while the existing MkDocs project site remains available.
- The successor rehearsal passes from a fresh shell on the final revision.
- Outgoing access removal has a retained private audit record.

### Evidence and controls

- [`apps/duecare-ai.com/DEPLOY_STATIC.md`](../apps/duecare-ai.com/DEPLOY_STATIC.md)
- [`docs/PRIVATE_TRANSFER_RECEIPT_TEMPLATE.md`](PRIVATE_TRANSFER_RECEIPT_TEMPLATE.md)
- [`docs/MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md)
- [`docs/SUCCESSOR_REHEARSAL.md`](SUCCESSOR_REHEARSAL.md)

## Choose release, dated deferral, or maintenance mode
<a id="release-disposition"></a>

- **ID:** `release-disposition`
- **Priority:** P0
- **Status:** Deferred: owner decision
- **Owner role:** Release owner
- **Target:** By the 2026-08-22 final-decision window
- **Model-credit policy:** `zero_only`
- **Network/write policy:** `owner_authorized_write`
- **Depends on:** No other register item

**Why it remains open:** The repository is release-capable, but version, support, registry, and public-claim authority remain owner decisions.

### Prerequisites

- A clean exact candidate revision with core, handoff, secret, package, and deployment receipts
- A written choice among bounded release, dated no-release deferral, and maintenance mode

### Ordered next actions

1. Select one disposition and record its effective date, supported surfaces, security intake posture, and excluded claims.
2. If releasing, reconcile package versions, changelog, citation, tag, and release notes against one exact commit.
3. If deferring or entering maintenance mode, publish the support and freshness boundary without implying that model, dataset, or registry artifacts were released.

### Done only when

- The disposition and effective date are explicit in the transition decision register.
- Public status, citation, changelog, package manifest, and release notes do not conflict.
- The training lane is either green or explicitly excluded from the release claim.

### Evidence and controls

- [`docs/PROJECT_TRANSITION_PLAN.md`](PROJECT_TRANSITION_PLAN.md)
- [`docs/PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md)
- [`configs/duecare/package_release.toml`](../configs/duecare/package_release.toml)

## Publish the first independently versioned Python package
<a id="first-package-publication"></a>

- **ID:** `first-package-publication`
- **Priority:** P1
- **Status:** Deferred: owner decision
- **Owner role:** Release owner
- **Target:** Only after release-disposition selects a bounded package release
- **Model-credit policy:** `zero_only`
- **Network/write policy:** `owner_authorized_write`
- **Depends on:** `release-disposition`

**Why it remains open:** All 18 distributions build and clean-install, but production PyPI publication is an irreversible external write with package-specific version authority.

### Prerequisites

- One selected row from configs/duecare/package_release.toml
- An exact production tag matching the selected package name and version
- A green trusted-publisher dry validation on the tagged commit

### Ordered next actions

1. Select one package rather than treating the mixed-version workspace as a monolithic release.
2. Run python scripts/validate_package_release.py and the core publication gate on the exact candidate.
3. Create the matching package-specific production tag and let the sole OIDC workflow publish; do not use a direct twine upload.

### Done only when

- The selected package exists on PyPI at the manifest version with expected metadata.
- The published wheel and source archive match the retained build evidence.
- No second workflow or manual credential can publish the same package path.

### Evidence and controls

- [`configs/duecare/package_release.toml`](../configs/duecare/package_release.toml)
- [`docs/PACKAGE_INVENTORY.md`](PACKAGE_INVENTORY.md)
- [`scripts/validate_package_release.py`](../scripts/validate_package_release.py)
- [`.github/workflows/pypi-publish.yml`](../.github/workflows/pypi-publish.yml)

## Complete the 75-row corridor-diversification workbook
<a id="corridor-curation"></a>

- **ID:** `corridor-curation`
- **Priority:** P1
- **Status:** Blocked: human review
- **Owner role:** Two independent data curators
- **Target:** Before any new training or model-improvement claim
- **Model-credit policy:** `zero_only`
- **Network/write policy:** `read_only_verification`
- **Depends on:** No other register item

**Why it remains open:** The strict audit identifies five dense single-corridor shortcut risks, and all 75 source-bound content slots remain intentionally unfilled.

### Prerequisites

- Compatible source rights and immutable dated snapshots with SHA-256
- Native-language review capacity for the assigned language lanes
- Two independent reviewers for severe cases and disagreement resolution

### Ordered next actions

1. Approve or reject each candidate source using rights, privacy, retrieval-date, and checksum evidence.
2. Author exactly 25 risk cases, 25 benign near-neighbours, and 25 corridor counterfactuals with lineage-family split isolation.
3. Run python scripts/validate_corridor_curation.py --require-complete and resolve findings without weakening thresholds.

### Done only when

- The completion validator reports 75 of 75 valid rows and zero privacy findings.
- Two-person adjudication and native-language attestations satisfy the workbook contract.
- No exact, near-duplicate, lineage-family, or source-rights leakage crosses splits.

### Evidence and controls

- [`configs/duecare/training/corridor_curation_sources.json`](../configs/duecare/training/corridor_curation_sources.json)
- [`scripts/build_corridor_curation_workbook.py`](../scripts/build_corridor_curation_workbook.py)
- [`scripts/validate_corridor_curation.py`](../scripts/validate_corridor_curation.py)
- [`docs/PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md)

## Refresh training quality and append-only provenance
<a id="training-provenance-refresh"></a>

- **ID:** `training-provenance-refresh`
- **Priority:** P1
- **Status:** Blocked: human review
- **Owner role:** Training-data curator and release reviewer
- **Target:** After corridor-curation passes and before training starts
- **Model-credit policy:** `zero_only`
- **Network/write policy:** `offline_only`
- **Depends on:** `corridor-curation`

**Why it remains open:** The current quality audit is red and refreshed artifacts intentionally no longer match an older planned fine-tune record.

### Prerequisites

- A complete, accepted corridor workbook
- Frozen training, held-out, preference, reward, and quarantine inputs

### Ordered next actions

1. Run python scripts/audit_training_quality.py --require-clean.
2. Regenerate the corridor expansion plan and related manifests sequentially after the clean audit.
3. Append a new provenance record through the normal training engine and run python scripts/validate_training_provenance.py; never rewrite the older record.

### Done only when

- The strict quality audit has zero risk flags.
- Registry fingerprints match every current artifact.
- The verified model card renders from the new append-only record.

### Evidence and controls

- [`scripts/audit_training_quality.py`](../scripts/audit_training_quality.py)
- [`scripts/build_corridor_expansion_plan.py`](../scripts/build_corridor_expansion_plan.py)
- [`scripts/validate_training_provenance.py`](../scripts/validate_training_provenance.py)
- [`scripts/training_engine.py`](../scripts/training_engine.py)

## Run a small frozen frontier model smoke matrix
<a id="bounded-model-smoke"></a>

- **ID:** `bounded-model-smoke`
- **Priority:** P1
- **Status:** Deferred: budget or quota
- **Owner role:** Model-spend approver and benchmark maintainer
- **Target:** Only after provider reconciliation and an approved finite run plan
- **Model-credit policy:** `nonzero_requires_owner_approval`
- **Network/write policy:** `owner_authorized_write`
- **Depends on:** `provider-usage-reconciliation`

**Why it remains open:** Kimi K3 and Meta Muse Spark 1.1 are important new comparison targets, but a live smoke matrix consumes provider quota and is unnecessary for repository maintenance closure.

### Prerequisites

- At execution time, reverify the dated catalog identities and pricing for Kimi K3 (currently kimi-k3:cloud on Ollama or moonshotai/kimi-k3 on OpenRouter) and Meta Muse Spark 1.1 (currently meta/muse-spark-1.1 on OpenRouter or the then-current Meta Model API identifier)
- A unique run ID with finite attempt, input-token, output-token, and cash caps
- A frozen prompt, rubric, harness, decoding, cache, and stop-condition manifest

### Ordered next actions

1. Generate and review a no-call plan before changing any stop or budget setting.
2. Configure the shared provider ledger and prove its sanitized receipt with python scripts/provider_budget.py --json.
3. Include Kimi K3 and Meta Muse Spark 1.1 as required candidate lanes on the same frozen text slice; stage any multimodal extension separately, and record unavailable access instead of silently substituting another model.
4. Run only the approved matrix, preserve checkpoints and cache keys, then restore the whole-stack cost stop.

### Done only when

- Reserved and actual attempts, tokens, and cost reconcile to the approved allowance.
- Every output is bound to immutable inputs and can resume without duplicate calls.
- The report contains an immutable result receipt for both Kimi K3 and Meta Muse Spark 1.1, or dated provider evidence that a required lane was unavailable.
- scripts/stop_ollama_stack.ps1 -Status reports the complete cost stop after the run.

### Evidence and controls

- [`docs/PROVIDER_BUDGETING.md`](PROVIDER_BUDGETING.md)
- [`scripts/provider_budget.py`](../scripts/provider_budget.py)
- [`scripts/rich_harness_lift.py`](../scripts/rich_harness_lift.py)
- [`scripts/stop_ollama_stack.ps1`](../scripts/stop_ollama_stack.ps1)

## Complete the isolated exhaustive per-dimension judge lane
<a id="per-dimension-judging"></a>

- **ID:** `per-dimension-judging`
- **Priority:** P3
- **Status:** Deferred: budget or quota
- **Owner role:** Research lead and model-spend approver
- **Target:** Only if its research value justifies the remaining high call volume
- **Model-credit policy:** `nonzero_requires_owner_approval`
- **Network/write policy:** `owner_authorized_write`
- **Depends on:** `provider-usage-reconciliation`, `bounded-model-smoke`

**Why it remains open:** The latest local coverage snapshot has all 236157 response cells but only 47813 of 708471 panel cells; 660658 panel cells remain, so the lane is partial and non-comparable.

### Prerequisites

- A reviewed value-of-information decision for the remaining judge cells
- A priced closure plan using the existing seeded order, component cache, and resumable checkpoint

### Ordered next actions

1. Re-read reports/rich_lift/panel_perdim.coverage.json as live local evidence rather than trusting this dated snapshot.
2. Plan only missing valid cells and exclude the partial lane from the default v1/h1 comparable board throughout execution.
3. Resume under the shared finite budget and stop immediately on budget, quota, authentication, or validity breach.

### Done only when

- The exact coverage manifest reports 708471 of 708471 valid panel cells with zero missing or invalid cells.
- All 3542355 dimension outputs are valid and hash-bound to the frozen scope.
- A separately versioned report documents judge agreement, limitations, cost, and board isolation.

### Evidence and controls

- [`docs/research/frontier_panel_perdim.md`](research/frontier_panel_perdim.md)
- [`docs/research/perdim_granular_lift.md`](research/perdim_granular_lift.md)
- [`scripts/rich_harness_lift.py`](../scripts/rich_harness_lift.py)

## Run only justified Kaggle evidence jobs
<a id="optional-kaggle-reruns"></a>

- **ID:** `optional-kaggle-reruns`
- **Priority:** P2
- **Status:** Deferred: budget or quota
- **Owner role:** Kaggle account owner and evidence reviewer
- **Target:** Only for a named recording or evidence gap
- **Model-credit policy:** `nonzero_requires_owner_approval`
- **Network/write policy:** `owner_authorized_write`
- **Depends on:** No other register item

**Why it remains open:** Active 01 is complete, active 02 and A-00 are canceled, optional 04 is complete, and optional 03 lacks a verified public URL; no additional notebook is required for repository closure.

### Prerequisites

- A named audience, evidence gap, runtime shape, quota ceiling, and artifact-retention plan
- A source revision that passes both Kaggle static validators

### Ordered next actions

1. Rerun 02 only when a new recording is required and rerun A-00 only for a funded proof artifact.
2. Keep optional 03 source-only until account access and a public slug are verified; do not infer completion from local source.
3. Download and inspect every required working-directory artifact before updating any public completion claim.

### Done only when

- The selected Kaggle run reaches COMPLETE rather than a canceled terminal state.
- Artifacts, logs, commit reference, model revision, and quota use are reviewed and retained.
- docs/NOTEBOOKS.md, kaggle/_INDEX.md, and public links agree with authenticated and anonymous status.

### Evidence and controls

- [`docs/NOTEBOOKS.md`](NOTEBOOKS.md)
- [`kaggle/_INDEX.md`](../kaggle/_INDEX.md)
- [`scripts/validate_main_kaggle_kernels.py`](../scripts/validate_main_kaggle_kernels.py)
- [`scripts/validate_kaggle_page_sources.py`](../scripts/validate_kaggle_page_sources.py)

## Extend budget enforcement beyond the primary router
<a id="direct-client-budget-migration"></a>

- **ID:** `direct-client-budget-migration`
- **Priority:** P2
- **Status:** Ready: local and model-free
- **Owner role:** Maintainer
- **Target:** One direct client per reviewable change before broad funded evaluation
- **Model-credit policy:** `zero_only`
- **Network/write policy:** `offline_only`
- **Depends on:** No other register item

**Why it remains open:** The primary llm_generate.py router is enforced, while package adapters, application integrations, standalone scripts, and self-contained notebooks are not universally intercepted.

### Prerequisites

- An exact direct-call inventory with one selected caller and its public behavior contract
- A fake or loopback transport test that proves denial before network access

### Ordered next actions

1. Select one direct client and route its attempt through the shared budget interface without changing unrelated providers.
2. Add tests for zero-call denial, retry reservation, unknown pricing, and sanitized receipts.
3. Run python scripts/validate_provider_budget_coverage.py and document the expanded but still exact coverage boundary.

### Done only when

- The selected caller cannot reach transport without an approved reservation.
- Its tests pass with DUECARE_MAX_PLANNED_MODEL_CALLS set to zero and never require a live credential.
- Public documentation names covered and uncovered clients without claiming universal interception.

### Evidence and controls

- [`scripts/llm_generate.py`](../scripts/llm_generate.py)
- [`scripts/provider_budget.py`](../scripts/provider_budget.py)
- [`scripts/validate_provider_budget_coverage.py`](../scripts/validate_provider_budget_coverage.py)
- [`docs/PROVIDER_BUDGETING.md`](PROVIDER_BUDGETING.md)

## Create a human gold set and agreement monitor
<a id="human-gold-calibration"></a>

- **ID:** `human-gold-calibration`
- **Priority:** P2
- **Status:** Blocked: human review
- **Owner role:** Qualified domain reviewers and evaluation lead
- **Target:** Before claiming judge validity or field effectiveness
- **Model-credit policy:** `zero_only`
- **Network/write policy:** `offline_only`
- **Depends on:** No other register item

**Why it remains open:** Existing model-panel and deterministic evidence does not substitute for qualified human grading or prospective deployment evidence.

### Prerequisites

- A documented reviewer qualification, conflict, consent, privacy, and compensation policy
- A stratified severe-case and benign-control sample isolated from training

### Ordered next actions

1. Define the grading protocol, adjudication policy, disagreement taxonomy, and permissible public aggregates.
2. Collect independent grades without exposing reviewer identities or case-level private data.
3. Report agreement, calibration, abstention, and failure slices without tuning the frozen held-out set.

### Done only when

- The reviewed sample and protocol are versioned and excluded from training.
- Agreement and uncertainty metrics include confidence intervals and disagreement reasons.
- Claims remain limited to the reviewed sample and do not imply field effectiveness.

### Evidence and controls

- [`docs/research/judge_calibration.md`](research/judge_calibration.md)
- [`docs/research/evaluation_methodology.md`](research/evaluation_methodology.md)
- [`docs/research/convergent_validity.md`](research/convergent_validity.md)

## Clear legacy lint debt in behavior-preserving slices
<a id="legacy-ruff-cleanup"></a>

- **ID:** `legacy-ruff-cleanup`
- **Priority:** P3
- **Status:** Ready: local and model-free
- **Owner role:** Maintainer
- **Target:** Separate pull requests after closeout-critical work
- **Model-credit policy:** `zero_only`
- **Network/write policy:** `offline_only`
- **Depends on:** No other register item

**Why it remains open:** Long benchmark and verification files retain broad style debt; a mass rewrite would obscure behavioral review and is not a release blocker.

### Prerequisites

- A frozen regression baseline for each selected file
- A change limited to one mechanical category or one small semantic finding

### Ordered next actions

1. Run ruff check on scripts/rich_harness_lift.py, scripts/verify.py, and tests/test_plan.py and record the current categories.
2. Fix one bounded category without broad suppression, then run focused and full deterministic tests.
3. Repeat in separate reviewable changes until the repository lint command can be expanded safely.

### Done only when

- The selected Ruff scope passes without a file-wide ignore for useful rules.
- No benchmark plan, score, output schema, or fixture changes unexpectedly.
- The full zero-call regression and public gates remain green.

### Evidence and controls

- [`scripts/rich_harness_lift.py`](../scripts/rich_harness_lift.py)
- [`scripts/verify.py`](../scripts/verify.py)
- [`tests/test_plan.py`](../tests/test_plan.py)
- [`pyproject.toml`](../pyproject.toml)

## Review volatile legal and operational sources on a cadence
<a id="source-freshness-maintenance"></a>

- **ID:** `source-freshness-maintenance`
- **Priority:** P1
- **Status:** Recurring maintenance
- **Owner role:** Knowledge curator
- **Target:** At each source expiry or scheduled freshness review
- **Model-credit policy:** `zero_only`
- **Network/write policy:** `read_only_verification`
- **Depends on:** No other register item

**Why it remains open:** Hotlines, fees, wage rules, offices, URLs, laws, and provider or platform contracts can change after a valid release.

### Prerequisites

- A versioned knowledge object or source registry entry with retrieval date and checksum
- An official or otherwise admitted source and a curator assigned to the affected jurisdiction

### Ordered next actions

1. Re-fetch the exact admitted source, record retrieval date and checksum, and compare controlling facts.
2. Propose a new version with supersession metadata; never silently overwrite an older knowledge object.
3. Run source, public-surface, privacy, and affected benchmark gates before publication.

### Done only when

- Changed facts have reviewed versioned replacements and unchanged facts have dated review evidence.
- Expired, unreachable, or superseded sources are labeled without deleting provenance.
- No volatile operational fact is promoted directly into model output or training data without a governed knowledge object.

### Evidence and controls

- [`docs/KNOWLEDGE_SURFACE_VERIFICATION.md`](KNOWLEDGE_SURFACE_VERIFICATION.md)
- [`docs/entity_intelligence_pipeline.md`](entity_intelligence_pipeline.md)
- [`scripts/check_external_links.py`](../scripts/check_external_links.py)
- [`docs/FILE_PURPOSE_GUIDE.md`](FILE_PURPOSE_GUIDE.md)

## Updating This Register

1. Edit `configs/duecare/deferred_work.json`.
2. Run `python scripts/build_deferred_work_register.py`.
3. Run `python scripts/validate_deferred_work.py`.
4. Run `python scripts/validate_publication_readiness.py --scope core`
   and the smallest tests for any affected surface.
5. Change an item to a completed historical receipt only in a separate
   dated document after every acceptance gate has evidence; remove it from
   this outstanding-work registry in the same reviewed change.
