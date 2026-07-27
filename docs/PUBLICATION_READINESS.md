# Publication Readiness And Next Work

This is the model-free wrap-up path for DueCare. It separates what can be
published from what still needs curation or a later, deliberately budgeted
model run. Current as of 2026-07-27.

## Current Posture

| Track | Current state | Publication rule |
|---|---|---|
| Core code, docs, active Kaggle surfaces, provider-budget coverage, package-release ownership, and published dataset claims | **10/10 core gates passed offline in the closeout candidate; the reconciled 2026-07-27 `master` passed its earlier complete post-merge CI and public deployment checks** | Re-run on the exact release commit before tagging. |
| Maintainer succession and live pickup | **2/2 handoff gates passed offline; public handoff and deployment receipts are live on the merged closeout** | Re-run from a fresh shell and complete the private/manual acceptance steps before ownership transfer. |
| Existing dated benchmark and learning-study results | Retained as bounded evidence with their original model, dataset, rubric, and date | Do not silently relabel an old result as a new model or field-effectiveness result. |
| New fine-tuning dataset | **Not clean yet:** the strict audit reports five dense single/generic-corridor typologies; the deterministic workbook has 75 unfilled slots and no fabricated approvals | Complete source snapshots, rights review, two-person adjudication, and lineage-safe rows; rerun the audit, then refresh provenance before training or a new model claim. |
| Exhaustive per-dimension judging | Experimental, isolated, and incomplete | Keep it out of the default comparable board until its own exact closure gate passes. |
| Local/hosted Ollama work | Optional and deferred; the primary router now has an atomic attempt/token/cash ledger | Plan offline first; unlock a small allowance only for a frozen, priced run, and keep direct/notebook clients outside the router explicitly labeled. |

## Registry And Kaggle Publication Truth

- All 18 `duecare-llm*` distributions are buildable from source, but none had a
  public PyPI project on 2026-07-27. `docs/PACKAGE_INVENTORY.md` is the
  canonical install/version map.
- `.github/workflows/pypi-publish.yml` is the sole publisher. Production PyPI
  has no manual dispatch target and no generic `v*` trigger. A
  `package-NAME-vMAJOR.MINOR.PATCH` tag must match exactly one row in the
  reviewed independent-SemVer manifest. The current `0.1.0` / `0.1.2` /
  `0.17.0` mix is intentional and no longer a policy blocker.
- Live Kaggle status checked 2026-07-27: active 01 is `COMPLETE`; active 02 and
  A-00 are `CANCEL_ACKNOWLEDGED`; optional 04 is `COMPLETE`; optional 03 has no
  verified public URL. A canceled run is not completion evidence.
- No additional notebook is required for repository closure. The private and
  built queue in [`NOTEBOOKS.md`](NOTEBOOKS.md) should advance one item at a
  time only when it closes a named audience or evidence gap.

The quality audit currently has zero SFT split leaks, zero DPO split leaks,
zero incoherent citations, and zero phone-like hits in gold text. Its blocker is
coverage shape: five typologies have enough rows to learn a generic-corridor
shortcut. The resulting curation plan contains 25 metadata-only tasks in five
batches and recommends at least 75 reviewed rows. The queue contains no raw
prompt or answer text and passes its privacy checks.

The deterministic curation workbook now expands those tasks into exactly 75
review slots: 25 risk cases, 25 benign near-neighbours, and 25 corridor
counterfactuals. It balances six perspectives, plans 45/15/15 rows across
train/validation/test by whole lineage family, and assigns English plus relevant
Bangla, Malay, Arabic, Amharic, and Hindi review lanes. The source catalog has
12 official or intergovernmental candidates, but every one is deliberately
blocked from training until a compatible-rights decision, immutable snapshot,
retrieval date, and SHA-256 exist. No source or row is represented as human
approved.

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
both active Kaggle static gates, package-release reconciliation, and package
test collection. The runner sets
Ollama's planned-call allowance to zero and forces common Hugging Face and
Weights & Biases integrations offline for its child checks.

Current audit receipt: all ten core gates passed in the 2026-07-27 closeout
candidate without a model or network call. The earlier surface reconciliation
landed through [pull request 4](https://github.com/TaylorAmarelTech/gemma4_comp/pull/4)
as `dc313814d9f42e127b24191b7912fd521083fadd`, after which the complete
[master CI workflow](https://github.com/TaylorAmarelTech/gemma4_comp/actions/runs/30273583863)
passed. These receipts are not a substitute for rerunning the command on an
eventual release tag.

Training readiness is intentionally separate:

```powershell
python scripts/validate_publication_readiness.py --scope training
```

It first requires all 75 source-bound and independently adjudicated rows, then
runs the strict quality audit, validates the corridor plan, and verifies the
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

The rich-harness guard counts planned **logical** generation, judging, and
pairwise calls. The primary `llm_generate.py` router now adds a separate atomic
transport ledger: it reserves attempts, estimated input tokens, maximum output
tokens, and reviewed worst-case cost before each HTTP request. Retries, key
rotations, and resilient re-questions consume new reservations. The full
operator contract, positive-budget environment, privacy boundary, and current
coverage matrix are in [Provider budgeting](PROVIDER_BUDGETING.md).

The transport lock is exact for the four primary-router HTTP paths, as enforced
by `validate_provider_budget_coverage.py`. It is not a repository-wide network
interceptor: self-contained Kaggle kernels, package/application adapters, and
standalone scripts with their own HTTP clients remain operator-controlled. Keep provider
credentials unavailable to those paths during deterministic maintenance.

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

The shared primary-router ledger is complete and tested without provider calls.
The remaining transport work is to migrate direct standalone research clients,
then design a portable notebook equivalent and an injectable
package/application-adapter contract without changing existing benchmark
evidence lanes.

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

The executable handoff is:

```powershell
python scripts/build_corridor_curation_workbook.py --validate
python scripts/build_corridor_curation_workbook.py
python scripts/validate_corridor_curation.py
python scripts/validate_corridor_curation.py --require-complete
```

The first three commands currently pass the metadata-only scaffold. The final
command correctly fails with `0/75` valid rows and `75` missing slots. Candidate
content belongs only in ignored
`reports/training/corridor_curation_rows.jsonl`. The validator rejects
unapproved or checksum-mismatched sources, missing or duplicate reviewers,
unresolved disagreements, absent native-language attestation, PII-like text,
exact duplicates, cross-family near-duplicates, and lineage-family split
leakage. Findings contain row identifiers and category/count summaries, never
matched sensitive payloads.

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

The machine-readable candidate registry is
[`configs/duecare/training/corridor_curation_sources.json`](../configs/duecare/training/corridor_curation_sources.json).
It adds corridor-relevant official discovery points for BMET and its live
recruiting-agent registry, Malaysia's labour-policy publications, India MEA's
overseas-employment material, Saudi HRSD's labour-reform guide, and dated ILO
FAIR/FAIRWAY, STREAM, Qatar, and Kuwait material. URL verification is not
license approval: all entries remain candidate-only and training-blocked.

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
| What must curators add? | `reports/training/corridor_curation_workbook.json`, the candidate-only source catalog, and `validate_corridor_curation.py --require-complete` |
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
  -> 75-slot source/review workbook
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
- The integrated `packages tests` regression passed 4,627 tests with nine
  skips and no warning summary in the clean, locked 18-package workspace. The
  focused package follow-up also passes 43 tests with `RuntimeWarning`
  promoted to an error, proving the former
  constant-value pandas Styler warnings are removed rather than hidden.
- The new publication gate and its tests pass their scoped Ruff check. A wider
  Ruff check of the legacy `rich_harness_lift.py`, `verify.py`, and
  `test_plan.py` surfaces still reports 281 style findings (261 are line
  length). Do not call repo-wide lint green; handle that mechanical cleanup in
  a separate, reviewable change rather than mixing it with model/data work.
- MkDocs now passes `mkdocs build --clean --strict` with zero warnings. The
  tested repository-link hook rewrites only existing targets outside `docs/`
  to canonical GitHub source URLs; it leaves missing targets untouched so the
  strict lane remains a meaningful broken-link guard. Informational notices
  for intentionally unlisted/excluded provenance pages are not release
  blockers.
- The deployment boundary is now unambiguous: Render owns `duecare-ai.com`,
  `docs-deploy.yml` owns the repository's single MkDocs GitHub Pages site, and
  `duecare-site-build.yml` emits a downloadable marketing-site artifact only.
  A competing manual Pages deployer was removed. Post-merge Pages, artifact,
  live Render project-status, and schema-route checks passed on 2026-07-27.
- GitHub Action majors were verified against official releases on 2026-07-27
  and refreshed across CI, Pages, website artifacts, scheduled work, Docker,
  Helm, Gitleaks, and package publication. The triggered CI, Pages,
  website-artifact, harness-contract, and evaluation jobs passed with the
  refreshed actions and no Node 20 runtime annotation.
  Docker, Helm, and PyPI publishing remain release-triggered and should be
  validated on an approved release candidate/tag, not dispatched as a
  production smoke test.
- Workspace package versions were not guessed or bumped. ADR-001 now adopts
  independent SemVer, and `configs/duecare/package_release.toml` reconciles the
  intentionally mixed versions with the sole publisher. `CITATION.cff` still
  describes living research software because no registry release exists yet.
- The post-deploy concurrent external audit checked 577 outbound links on
  2026-07-27 with zero confirmed broken links. All six same-site schema URLs
  returned 200; 10 additional hosts were transient, DNS/SSL-blocked,
  redirect-looped, or bot-blocked and remain explicitly unverified rather than
  mislabeled as broken.
- Root `AGENTS.md` names `master` as the active release branch. Pull request 2
  preserves the first integrated closeout, while pull request 4 merged the
  final public-surface reconciliation as
  `dc313814d9f42e127b24191b7912fd521083fadd`. Post-merge CI, MkDocs Pages, the
  artifact-only website build, Render project status, and the advertised schema
  routes were verified before this receipt was recorded. A release tag/version
  remains a separate owner decision.
- Archived notebook-era surfaces are provenance. Do not restore them to the
  Kaggle root to satisfy old references; update the reference or archive map.
- Never treat a dirty working tree as disposable. Inspect and preserve
  unrelated edits instead of trying to manufacture a clean status.

## Prioritized Backlog

| Priority | Work item | Model credits | Effort | Done when |
|---|---|---:|---:|---|
| P0 | Freeze the verified package cohort at a first-package release commit, reconcile changelog/citation, run privacy-safe secret scan, rerun core gate | 0 | Low | Exact package tag/commit and bounded release notes exist; 10/10 core gates pass there |
| P1 | Fill the 75-slot corridor workbook with source-approved rows, lineage, and two-person adjudication | 0 if human/deterministic | Medium | `validate_corridor_curation.py --require-complete` and the strict quality audit pass without weakening a threshold |
| P2 | Extend the primary-router budget contract to direct standalone clients and design a portable notebook equivalent | 0 during implementation | Medium | Each migrated caller has a zero-transport test; no claim implies a repository-wide interceptor |
| P1 | Refresh training provenance through the normal append-only engine path | 0 | Low after curation | Registry fingerprints and verified model-card gate pass |
| P2 | Human-adjudicate a stratified high-severity and benign-control slice | 0 model credits | Medium | Agreement, disagreement reasons, and adjudication policy are published |
| P2 | Run a frozen small Ollama smoke matrix with finite output cap and cache reuse | Small, explicit | Low | Planned allowance equals receipt; all artifacts are hash-bound |
| P2 | Add calibration, abstention, and disagreement-escalation reporting | Optional small judging | Medium | Reports show calibration and route only ambiguous cells to extra judges |
| P3 | Complete the isolated exhaustive per-dimension lane | High | High | Coverage manifest closes exactly with zero missing/invalid cells |
| P3 | Isolate and clear legacy Ruff debt in long benchmark files | 0 | Medium | `make lint` can run without a mass behavioral diff or suppressing useful rules |
| P3 | Validate refreshed actions in the release-triggered Docker, Helm, and package workflows | 0 | Low | The first approved release candidate/tag keeps those release-only lanes green without runtime deprecation annotations |

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
      versions, changelog, tag, and the currently unversioned `CITATION.cff`;
      do not bump them implicitly during cleanup.

## Recommended Next Sequence

1. Approve immutable source snapshots, then fill and adjudicate the 75-row
   corridor workbook with full lineage and source metadata.
2. Clear the strict quality and provenance gates and append a new planned
   fine-tune record through the normal engine.
3. When spend is separately authorized, configure the completed primary-router
   ledger with reviewed pricing and run a small frozen Ollama smoke matrix with
   checkpoint reuse.
4. Expand only the cells justified by confidence intervals or disagreement,
   complete the isolated per-dimension lane, and obtain human adjudication on a
   representative high-severity slice.
5. Re-run the core publication gate, choose versions, tag the exact commit, and
   publish the bounded artifacts plus this limitations register.
