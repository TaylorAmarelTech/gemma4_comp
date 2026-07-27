# Publication Readiness And Next Work

This is the model-free wrap-up path for DueCare. It separates what can be
published from what still needs curation or a later, deliberately budgeted
model run. Current as of 2026-07-26.

## Current Posture

| Track | Current state | Publication rule |
|---|---|---|
| Core code, docs, active Kaggle surfaces, and published dataset claims | **8/8 core gates passed offline; the merged closeout then passed the complete `master` CI workflow on 2026-07-26** | Re-run on the exact release commit; publish only while it remains green. |
| Maintainer succession and live pickup | **2/2 handoff gates passed offline; public handoff and deployment receipts are live on the merged closeout** | Re-run from a fresh shell and complete the private/manual acceptance steps before ownership transfer. |
| Existing dated benchmark and learning-study results | Retained as bounded evidence with their original model, dataset, rubric, and date | Do not silently relabel an old result as a new model or field-effectiveness result. |
| New fine-tuning dataset | **Not clean yet:** the strict audit reports five dense single/generic-corridor typologies | Curate the expansion queue, rerun the audit, then refresh provenance before training or a new model claim. |
| Exhaustive per-dimension judging | Experimental, isolated, and incomplete | Keep it out of the default comparable board until its own exact closure gate passes. |
| Local/hosted Ollama work | Optional and deferred | Plan offline first; unlock a small allowance only for a frozen, bounded run. |

The quality audit currently has zero SFT split leaks, zero DPO split leaks,
zero incoherent citations, and zero phone-like hits in gold text. Its blocker is
coverage shape: five typologies have enough rows to learn a generic-corridor
shortcut. The resulting curation plan contains 25 metadata-only tasks in five
batches and recommends at least 75 reviewed rows. The queue contains no raw
prompt or answer text and passes its privacy checks.

Refreshing the audit and corridor plan invalidates fingerprints in the older
append-only planned fine-tune record. That is expected: do not rewrite history
or append a replacement record until the quality audit is clean. The strict
training-provenance gate should remain red in the meantime.

## One-Command Offline Review

Run from the repository root:

```powershell
python scripts/validate_publication_readiness.py --scope core
```

This runs public-surface and messaging audits, the source-checkout harness
smoke test, published dataset-claim verification, fallback-registry validation,
both active Kaggle static gates, and package test collection. The runner sets
Ollama's planned-call allowance to zero and forces common Hugging Face and
Weights & Biases integrations offline for its child checks.

Current audit receipt: all eight core gates passed on 2026-07-26 without a
model or network call. The same tree landed through pull request 2 as
`07cfdbfd00e1bc304ffc1f8b2736c4d93bbf0eab`, after which the complete
[master CI workflow](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30235104435)
passed. These receipts are not a substitute for rerunning the command on an
eventual release tag.

Training readiness is intentionally separate:

```powershell
python scripts/validate_publication_readiness.py --scope training
```

It runs the strict quality audit, validates the corridor plan, and verifies the
fine-tune registry/model-card/trainer provenance chain. A nonzero result is the
honest expected state until the corridor queue is curated.

For local handoff state and live automation status, also run:

```powershell
python scripts/validate_project_bible_pickup.py
```

That command is workspace-specific evidence; it is not part of the portable
publication gate.

## Transition And Succession

This file remains the release and evidence boundary. For human ownership
transfer, use the operational [Maintainer handoff](MAINTAINER_HANDOFF.md) and
the dated [30-day transition plan](PROJECT_TRANSITION_PLAN.md). Their read-only
gate is:

```powershell
python scripts/validate_publication_readiness.py --scope handoff
```

That scope validates succession structure, discovery and local links,
category/count-only privacy checks, public website/Pages ownership, the public
continuity route, and live Project Bible pickup consistency.
It does not make the strict training lane portable or green, and it does not
authorize publication, credential transfer, provider spend, or engine resume.
The current working-tree receipt is 2/2 handoff gates passed, including 16/16
succession-document checks and the 65-check pickup validator with zero findings.

## Preserve Ollama Credits

Keep the current shell locked while doing deterministic work:

```powershell
$env:DUECARE_MAX_PLANNED_MODEL_CALLS='0'
```

For the rich harness, always inspect the exact incremental plan before a run:

```powershell
python scripts/rich_harness_lift.py --n 40 --plan --require-complete
```

`--plan` now exits before heartbeat or result files are written. The rich
harness also accepts `--max-planned-model-calls N`; it exits with code 4 before
any model call or run-artifact write when the offline estimate exceeds `N`.
The command-line value overrides the environment lock.

This guard counts planned **logical** generation, judging, and pairwise calls.
It is not yet a strict transport-attempt, provider-credit, or token cap because
transient retries and resilient generation can add requests. It also protects
the rich harness only; direct Ollama helper scripts are not centrally locked.

When model work resumes, use this order:

1. Freeze the prompt-set hash, model IDs/revisions, harness/rubric versions,
   shuffle seed, maximum output tokens, and expected artifact paths.
2. Run deterministic gates and `--plan` first.
3. Unlock only the sampled allowance needed for a small stratified smoke run.
4. Reuse successful generation and component checkpoints. Never discard a
   resumable cache merely to restart cleanly.
5. Retry only transient timeouts or service failures. Do not retry quota,
   authentication, permission, or invalid-request failures.
6. Escalate judge disagreements or borderline cases to extra judges; do not
   spend a full panel on every easy cell.
7. Keep v2/h2/per-dimension experiments in versioned files, separate from the
   v1/h1 batched board.

The next transport improvement should be a shared atomic budget ledger in
`llm_generate.py`: reserve before every provider attempt, count retries and
tokens, store a sanitized receipt, and refuse when either call, token, or cash
allowance is exhausted. That would extend the lock to every Ollama caller and
turn the current startup estimate into an enforceable run-wide budget.

## Dataset Improvement Plan

The current curation plan applies each of five under-diversified typologies to
five proposed corridors. At three reviewed rows per task, that is 25 tasks and
75 new rows.

| Expansion corridor | Why it is useful |
|---|---|
| Bangladesh to Malaysia | Recruitment-fee, manufacturing, and intermediary variation |
| Bangladesh to Saudi Arabia | Domestic-work and Gulf recruitment-chain variation |
| Ethiopia to Gulf destinations, maritime | Origin, route, and sector variation outside the dominant examples |
| Ghana to Qatar | West African origin and construction/service-chain variation |
| India to Kuwait | South Asian origin with a distinct destination-law context |

The row review should add diversity without creating a new shortcut:

- split held-out data by lineage/mechanism family, not random row alone;
- balance worker, recruiter, employer, platform, investigator, and bystander
  perspectives;
- include benign near-neighbours and corridor-swapped counterfactuals to test
  over-refusal;
- cover relevant languages and code-switching, with bilingual human review;
- keep statute, fee, hotline, office, and URL claims in dated knowledge objects;
- require two-person adjudication for disputed labels and high-severity gold
  answers;
- attach source URL, retrieval date, license/terms, checksum, transformation,
  parent hash, and split family to every admitted source-derived row;
- publish a data card and machine-readable metadata alongside row manifests;
- keep private complaints, contact lists, identity documents, and raw case
  narratives out of the training corpus.

After curation, run these in order:

```powershell
python scripts/audit_training_quality.py --require-clean
python scripts/build_corridor_expansion_plan.py
python scripts/validate_training_provenance.py --json
```

Only after a clean audit should the normal training engine append a new
provenance record. Do not edit an older append-only registry entry to make its
hashes look current.

## Additional Public Resources

These are candidate inputs for curated knowledge objects, context features, or
evaluation strata. They are not an instruction to bulk-ingest everything.
Links were verified against the official publishers on 2026-07-26.

| Resource | Best use in DueCare | Admission note |
|---|---|---|
| [ILO NATLEX](https://natlex.ilo.org/dyn/natlex2/r/natlex/fe/home) | National labour, social-security, and related human-rights legislation | Snapshot the exact instrument and date; a database match is not legal advice. |
| [ILO SDG 10.7.1 recruitment-cost resources](https://www.ilo.org/topics-and-sectors/fair-recruitment/regulating-and-measuring-recruitment-fees-and-costs) | Recruitment-cost definitions, survey design, and fee-burden evaluation features | Keep country/sample limitations with each statistic. |
| [UNODC Data Portal](https://data.unodc.org/) | Aggregate trafficking-in-persons indicators and evaluation context | Use metadata and aggregate strata, not inferred case labels. |
| [IOM Displacement Tracking Matrix API](https://dtm.iom.int/data-and-analysis/dtm-api) | Aggregated mobility and displacement context | Treat as contextual administrative data; review API terms and geographic granularity. |
| [World Bank WDR 2023 migration data](https://www.worldbank.org/en/publication/wdr2023/data) | Bilateral migration matrices and country-level context | Record the original table/figure source and transformation. |
| [U.S. DOL ILAB List of Goods](https://www.dol.gov/agencies/ilab/reports/child-labor/list-of-goods) | Country-good forced/child-labour risk strata and hard-negative design | It is a risk source, not proof about a particular company or worker. |
| [Global Fishing Watch vessel-identity data](https://globalfishingwatch.org/datasets-and-code-vessel-identity/) | Vessel identity and maritime-sector entity linkage | Preserve dataset version, license, identity confidence, and match rationale. |
| [Open Supply Hub API](https://info.opensupplyhub.org/resources/api-documentation) | Facility matching, sector/facility context, and supply-chain entity resolution | API access may require a trial/subscription and token; review terms before acquisition. |
| [Open Ownership BODS analysis tools](https://www.openownership.org/en/publications/beneficial-ownership-data-analysis-tools/user-guidance/) | Beneficial-ownership entity linkage in the propose-only intelligence pipeline | Preserve BODS source, jurisdiction, publication date, and open-license attribution. |

Every source must pass the same admission checklist: lawful access, compatible
license/terms, minimum necessary fields, privacy review, source snapshot,
`retrieved_at`, checksum, transformation record, and curator approval. External
entity data belongs in the propose-only entity-intelligence pipeline until
reviewed; it must not flow directly into worker-facing answers or training rows.

## Pickup In Ten Minutes

A new maintainer or agent should use this order. None of these commands calls a
model:

```powershell
git status --short
python scripts/validate_publication_readiness.py --scope handoff
python scripts/validate_project_bible_pickup.py
python scripts/autonomous_engine.py --status
python scripts/validate_publication_readiness.py --scope core
```

Then read:

1. [`AGENTS.md`](../AGENTS.md) for safety, active surfaces, and required gates.
2. [`MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md) for operations, boundaries,
   access transfer, recovery, and acceptance.
3. [`PROJECT_TRANSITION_PLAN.md`](PROJECT_TRANSITION_PLAN.md) for the dated
   closeout sequence and maintenance-mode fallback.
4. This file for the release boundary and prioritized next work.
5. [`project_status.md`](project_status.md) for the concise active-surface
   snapshot.
6. [`kaggle/_INDEX.md`](../kaggle/_INDEX.md) for active, optional, and archived
   notebook surfaces.
7. [`codex/PROJECT_BIBLE.md`](codex/PROJECT_BIBLE.md) for the deep historical
   and autonomous-engine handoff.

The authoritative live/generated evidence is:

| Question | Artifact or command |
|---|---|
| Is the public repository coherent? | `validate_publication_readiness.py --scope core` |
| Is local automation paused and internally coherent? | `validate_project_bible_pickup.py` plus `autonomous_engine.py --status` |
| Is the new training dataset safe to advance? | `reports/training/quality_audit.json` and `--scope training` |
| What must curators add? | `reports/training/corridor_expansion_plan.json` and its manifest |
| Is the exhaustive judge lane complete? | `reports/rich_lift/panel_perdim.coverage.json` |
| What Kaggle surfaces are active? | `kaggle/_INDEX.md` and the two Kaggle static validators |

Generated reports under `reports/` are generally local/ignored evidence. Do
not assume a saved report is current: compare its hashes/timestamps to live
status and rerun the read-only validator when possible.

## System Map For The Next Maintainer

The three major flows intentionally remain separate:

```text
worker/reviewer input
  -> workbench + shared model service
  -> deterministic GREP / RAG / tools / privacy boundary
  -> optional Gemma generation
  -> versioned evaluation + replay/export evidence

benchmark responses
  -> resumable generation cache
  -> isolated batched or per-dimension judging
  -> exact coverage manifest
  -> dated reports / comparable board

curated data
  -> organize + lineage split
  -> strict quality audit
  -> corridor curation plan
  -> optional train/evaluate
  -> append-only fine-tune registry + verified model card
```

The entity-intelligence pipeline is a fourth, **propose-only** flow. It can
stage public registry/entity matches for curator review, but it must not feed
worker-facing answers, benchmark labels, or training rows automatically.

## Deliberate Stops And Known Non-Blockers

- The autonomous engine is intentionally paused. A stale lock is normal while
  the stop sentinel exists; do not remove the sentinel or run `-Run` merely to
  make status look cleaner.
- Generation for the exhaustive per-dimension lane is complete, but judging is
  incomplete. Its partial coverage is useful research evidence, not default
  board closure and not a core-publication blocker.
- The training gate is red because of corridor coverage and the resulting
  stale fingerprints in an older planned registry record. This is a truthful
  provenance stop, not a reason to rewrite the ledger.
- The integrated `packages tests` regression passed 4,582 tests with nine
  skips and no warning summary in the clean, locked 18-package workspace. The
  focused package follow-up also passes 43 tests with `RuntimeWarning`
  promoted to an error, proving the former
  constant-value pandas Styler warnings are removed rather than hidden.
- The new publication gate and its tests pass their scoped Ruff check. A wider
  Ruff check of the legacy `rich_harness_lift.py`, `verify.py`, and
  `test_plan.py` surfaces still reports 281 style findings (261 are line
  length). Do not call repo-wide lint green; handle that mechanical cleanup in
  a separate, reviewable change rather than mixing it with model/data work.
- MkDocs builds normally, and the two succession pages emit zero diagnostics,
  but `mkdocs build --strict` still stops on 84 legacy documentation warnings:
  unlisted/excluded pages, repo-external relative targets, and stale anchors.
  The model-free public-surface/link gate is green; do not call the broader
  strict-site lane green until those warnings are classified and cleared.
- The deployment boundary is now unambiguous: Render owns `duecare-ai.com`,
  `docs-deploy.yml` owns the repository's single MkDocs GitHub Pages site, and
  `duecare-site-build.yml` emits a downloadable marketing-site artifact only.
  A competing manual Pages deployer was removed. Post-merge Pages, artifact,
  and live Render project-status checks passed on 2026-07-26.
- The green Pages receipt emits GitHub's Node.js 20 action-runtime deprecation
  annotation for currently pinned action majors. This is not a publication
  blocker, but the next maintainer should verify official current majors and
  refresh them in a narrow dependency-only change.
- Workspace/package version metadata and `CITATION.cff` are not being bumped by
  this polish pass. Reconcile them only as part of a deliberate release/tag
  decision.
- Root `AGENTS.md` names `master` as the active release branch. Pull request 2
  merged the closeout as `07cfdbfd00e1bc304ffc1f8b2736c4d93bbf0eab`;
  post-merge CI, MkDocs Pages, the artifact-only website build, and the live
  Render project-status route were verified before this receipt was recorded.
  A release tag/version remains a separate owner decision.
- Archived notebook-era surfaces are provenance. Do not restore them to the
  Kaggle root to satisfy old references; update the reference or archive map.
- Never treat a dirty working tree as disposable. Inspect and preserve
  unrelated edits instead of trying to manufacture a clean status.

## Prioritized Backlog

| Priority | Work item | Model credits | Effort | Done when |
|---|---|---:|---:|---|
| P0 | Freeze a release commit, reconcile versions/citation/changelog, run privacy-safe secret scan, rerun core gate | 0 | Low | Exact tag/commit and bounded release notes exist; 8/8 core gates pass there |
| P1 | Curate the 25 corridor tasks / minimum 75 rows with sources, lineage, and adjudication | 0 if human/deterministic | Medium | Strict quality audit is clean without weakening a threshold |
| P1 | Add a shared atomic call/token/cash ledger around every provider attempt | 0 during implementation | Medium | All callers fail closed against one run budget; retries appear in a sanitized receipt |
| P1 | Refresh training provenance through the normal append-only engine path | 0 | Low after curation | Registry fingerprints and verified model-card gate pass |
| P2 | Human-adjudicate a stratified high-severity and benign-control slice | 0 model credits | Medium | Agreement, disagreement reasons, and adjudication policy are published |
| P2 | Run a frozen small Ollama smoke matrix with finite output cap and cache reuse | Small, explicit | Low | Planned allowance equals receipt; all artifacts are hash-bound |
| P2 | Add calibration, abstention, and disagreement-escalation reporting | Optional small judging | Medium | Reports show calibration and route only ambiguous cells to extra judges |
| P3 | Complete the isolated exhaustive per-dimension lane | High | High | Coverage manifest closes exactly with zero missing/invalid cells |
| P3 | Isolate and clear legacy Ruff debt in long benchmark files | 0 | Medium | `make lint` can run without a mass behavioral diff or suppressing useful rules |
| P3 | Classify and clear the 84 legacy strict-MkDocs warnings | 0 | Medium | `mkdocs build --strict` passes without hiding intentionally public pages or broken anchors |
| P3 | Refresh GitHub Action majors after verifying official current releases | 0 | Low | Pages, website, and CI runs stay green without the Node.js 20 runtime deprecation annotation |

Good research extensions after the release boundary is stable include a
cross-corridor counterfactual benchmark, temporal legal-freshness tests,
language/code-switch calibration, source-ablation experiments, selective judge
escalation, and a small prospective NGO reviewer study. Each should start as a
new versioned evidence lane rather than changing the existing board in place.

## Release Checklist

- [ ] `--scope core` passes on the exact release commit.
- [ ] The release notes name the exact commit/tag, package versions, datasets,
      rubrics, harness versions, and dated evidence artifacts.
- [ ] `--scope training` either passes or the release clearly states that no new
      training/model-improvement claim is being made.
- [ ] The incomplete per-dimension lane remains labeled experimental and
      isolated from the default board.
- [ ] Secret and sensitive-data scans report categories/counts without printing
      matched payloads.
- [ ] Generated manifests, purpose maps, project status, and handoff artifacts
      agree with the code and current active Kaggle inventory.
- [ ] A deliberate release-version decision reconciles workspace package
      versions, `CITATION.cff`, changelog, and tag; do not bump them implicitly
      during cleanup.

## Recommended Next Sequence

1. Curate and adjudicate the 75-row corridor expansion with full lineage and
   source metadata.
2. Clear the strict quality and provenance gates and append a new planned
   fine-tune record through the normal engine.
3. Add the shared transport/token budget ledger, then run a small frozen Ollama
   smoke matrix with checkpoint reuse.
4. Expand only the cells justified by confidence intervals or disagreement,
   complete the isolated per-dimension lane, and obtain human adjudication on a
   representative high-severity slice.
5. Re-run the core publication gate, choose versions, tag the exact commit, and
   publish the bounded artifacts plus this limitations register.
