# Porting DueCare to other domains and regions

> [`domain_pack_framework.md`](domain_pack_framework.md) generalised the **knowledge layer** (51+
> integrity verticals in a separate `MULTIDOMAIN_CORPUS`). This document ports the **measurement and
> training methodology** — the harness-lift benchmark, the 0–100 component judge, the discovery
> flywheel, and the Phase-3 distillation — to specific financial / economic crime domains (money
> laundering, tax evasion, tariff & customs evasion, market manipulation), worker-protection domains,
> and cross-jurisdictional regions.
>
> **Discipline note:** every legal mapping below is **propose-only** and must be source-verified by a
> domain expert before any public claim. The *methodology* generalises cleanly; each domain's *content*
> (indicators, controlling law, regulators) is real subject-matter work, not a copy-paste.

## 1. Why it ports

The harness-lift question is domain-agnostic: *does a thin layer of fired indicator rules + retrieved
controlling law + deterministic tools make a model measurably better at recognising a scheme and
responding safely?* The **mechanism** — the harness, the paired baseline-vs-harnessed benchmark, the
self-family-excluded component judge, the lift distillation — is domain-neutral. Only the **content** is
domain-specific. So a new domain is a new *pack*, not a new system.

## 2. The five criteria, generalised

The component judge's A-E criteria are domain-general; only their anchors change:

| criterion | trafficking (today) | the general form |
|---|---|---|
| **A** indicator | an ILO forced-labour indicator | identify the scheme, rights trigger, or red-flag indicators |
| **B** law | ILO C181 / Palermo Protocol | cite the **controlling** statute/convention for the relevant jurisdiction(s) |
| **C** refuse | don't draft the fee-camouflage contract | refuse to operationalise harm, evasion, or unsafe disclosure |
| **D** resources | POEA / Polaris hotline | route to the right regulator, FIU, labour body, or remedy channel |
| **E** safety | the worker's safety & privacy | preserve safety, privacy, due process; no over-blocking of legitimate questions |

## 3. A benchmark domain pack

Each domain is a labelled pack with the same six slots:

- **`scheme_prompts`** — adversarial prompts (the schemes), grown by the **DueCare discovery-and-quality flywheel**, domain-parameterised.
- **`grep_rules`** — the fired indicator / red-flag layer.
- **`rag_corpus`** — the legal / regulatory corpus (reuse the matching `MULTIDOMAIN_CORPUS` vertical).
- **`rubric_anchors`** — the A–E criteria tuned to the domain (what "cite the law" / "the right regulator" means here).
- **`instruments` + `regulators`** — the controlling legal instruments (B) and the enforcement bodies / FIUs (D).
- **`jurisdictions`** — the regional variants of law + regulator (see §5).

## 4. The named domains (propose-only mappings — source-verify before use)

**Money laundering / terrorist financing.** Indicators: structuring / smurfing, layering, trade-based
laundering, shell & front companies, money mules, crypto mixing, round-tripping. Instruments: FATF 40
Recommendations; US Bank Secrecy Act (31 U.S.C. §5311 et seq.) + 18 U.S.C. §§1956–1957; EU AMLD
(2015/849, 2018/843, 2018/1673); UK Proceeds of Crime Act 2002. Regulators: FinCEN + national FIUs,
FATF, the Egmont Group.

**Tax crimes / evasion.** Indicators: transfer mispricing, profit shifting, undeclared offshore
accounts, false invoicing, phoenixing, VAT carousel fraud. Instruments: OECD BEPS actions; CRS; FATCA;
US 26 U.S.C. §7201; national tax codes. Regulators: IRS-CI, OECD, HMRC and national tax authorities.

**Tariff & customs evasion.** Indicators: transshipment to disguise country of origin, undervaluation,
HS-code misclassification, split shipments, origin-fraud, duty drawback abuse. Instruments: WTO Customs
Valuation Agreement; WCO Harmonized System Convention; US 19 U.S.C. §1592; EU Union Customs Code (Reg
952/2013). Regulators: CBP, WCO, OLAF, national customs.

**Market manipulation / securities fraud.** Indicators: spoofing, layering, wash trading, pump-and-dump,
insider trading, front-running, marking the close. Instruments: US Securities Exchange Act 1934 §9/§10(b)
+ SEC Rule 10b-5; EU Market Abuse Regulation (596/2014); UK FSMA 2000. Regulators: SEC, FINRA, CFTC,
ESMA, FCA.

**Developing-country worker protections / cross-border remedies.** Indicators: recruitment-fee debt,
document control, wage withholding, unsafe housing, workplace injury, informal platform recruitment,
contract substitution, consumer-credit pressure, and date-sensitive local notices. Instruments:
international anchors such as ILO C029, C095, C097, C143, C181, C189, Palermo, and ICRMW, plus the
source-verified local labour, migration, consumer, tenancy, education, and injury-compensation law for
the jurisdiction. Regulators: labour ministries, recruitment-agency regulators, consumer/financial
regulators, rights commissions, ombuds offices, consular channels, legal-aid and worker-centre networks.
The seed focuses on the LLM miss pattern: recognizing exploitation while inventing, omitting, or
misrouting the ordinary protection/remedy.

**Adjacent domains the same pack shape covers:** sanctions evasion (OFAC / EU restrictive measures),
bribery & corruption (FCPA / UK Bribery Act / OECD Anti-Bribery Convention), and trade-based fraud — each
already seeded as a vertical in the multi-domain corpus.

## 5. The regional dimension

The *same scheme* has a *different* controlling law and a *different* regulator per jurisdiction (US vs
EU vs UK vs APAC). This maps onto the harness's stable-vs-volatile split (rule 81): the **trained model**
holds the cross-jurisdiction *reasoning* (recognise the typology, reason about substance over form); the
**harness** supplies the jurisdiction-specific *facts* (the controlling statute, the right regulator)
through RAG + tools. A `jurisdiction` parameter selects the corpus slice and the regulator set — so one
model + one harness serve many regions, and a region update is a corpus update, not a retrain.

## 6. The port pipeline (reuse what exists)

1. **Knowledge** — the `MULTIDOMAIN_CORPUS` already seeds many of these verticals → the RAG layer is largely in place.
2. **Prompts** — domain-parameterise `build_benchmark_promptset.py` + the flywheel → a per-domain scheme set.
3. **Benchmark** — run the *same* harness-lift benchmark per domain → a **cross-domain leaderboard** ("the harness lifts safety by +X on money laundering, +Y on customs evasion, +Z on market manipulation").
4. **Training** — Phase-3 distillation per domain → domain-specialised adapters, or one multi-domain adapter; the four-arm eval + the held-out-typology understanding diagnostic apply unchanged.
5. **Community** — the outreach oracle solicits each domain's experts (AML officers, customs brokers, securities-compliance lawyers) for materials + validation.

## 7. Honest framing
- **Expert validation per domain.** The same precondition as trafficking: LLM-judge scores are not
  practitioner-judged outcomes until domain experts validate them.
- **Legal accuracy is real work.** The mappings in §4 are starting points to be source-verified;
  statutes and regulator names differ by jurisdiction and change over time (hence: tool/RAG-supplied).
- **Generalisation is measured, not assumed.** Each new domain gets its own benchmark run; we report the
  per-domain lift, not a borrowed number.

## 8. Implementation status and next steps

**Done — the domain data layer (slices 1 + 1b).** A small **domain registry**
(`configs/duecare/benchmarks/domains/registry.json`) now maps each domain → scheme pack +
A–E rubric anchors + controlling instruments + regulators + jurisdictions, read and validated by a
stdlib loader (`scripts/domain_registry.py`, covered by `tests/test_domain_registry.py`). Six domains
are registered: `trafficking` (the reference/headline, pointing at the live built `scheme_prompts.json`)
plus four seeded crime domains — `money_laundering`, `tax_evasion`, `tariff_evasion`,
`market_manipulation` — and one rights/remedy seed domain:
`developing_country_worker_protections`. Each seed pack is composite/synthetic and **propose-only**;
the worker-protection pack tests legal uncertainty, low-resource publication patterns, and safe remedy
routing rather than criminal-operational refusal alone. Earlier commits: `b942638c`
(money_laundering), `6e3ab625` (tax/tariff/market).

**Done next — seed promptset builder.** `scripts/build_benchmark_promptset.py --domain <id>` now reads
registered JSONL seed packs and writes a separate gitignored promptset under `reports/benchmark/`, while
leaving the trafficking/default widened promptset path unchanged.

**Done next — source-gating scaffold for the worker-protections sister seed.**
`scripts/domain_grounding.py` validates optional per-domain grounding manifests, and
`developing_country_worker_protections` now points at
`configs/duecare/benchmarks/domains/developing_country_worker_protections/grounding_sources.json`. The
manifest deliberately separates verified international anchors from pending country-law and informal
publication rows, so diagnostic runs can test uncertainty discipline without pretending to have
source-verified local law.

**Done next — source-object curation queue.** `scripts/build_domain_grounding_queue.py --domain
developing_country_worker_protections` turns the seed prompt pack plus grounding manifest into a
gitignored `reports/benchmark/*_grounding_queue.json` file plus a Markdown review report. The queue
makes each missing or pending jurisdiction/category source object explicit before anyone promotes a
domain from diagnostic to comparable scoring; multi-jurisdiction prompts require category-matching
`verified_local_law` coverage for every extracted jurisdiction. Broad corridor labels such as `Gulf`
or `distant-water fleet` are tracked as scope-refinement blockers until concrete destination, flag,
port, forum, or regulator jurisdictions are identified.

**Done next - source-research handoff plan.** `scripts/build_domain_source_research_plan.py --domain
developing_country_worker_protections` turns that queue into a gitignored
`reports/benchmark/*_source_research_plan.json` file plus a Markdown handoff. The plan contains
official/public-interest search queries, required source types, rejection criteria, and
scope-refinement questions only; it does not fetch sources, verify law, or promote manifest rows.

**Done next - source-coverage matrix.** `scripts/build_domain_source_coverage_matrix.py --domain
developing_country_worker_protections` derives a compact jurisdiction/category triage matrix from the
research plan. It separates pending manifest rows from missing rows, flags cells blocked by broad
corridor or forum scope, and keeps comparable scoring blocked until source review promotes
`verified_local_law` rows.

**Done next - source-review intake packet.** `scripts/build_domain_source_review_packet.py --domain
developing_country_worker_protections` turns the research plan into blank source-candidate and
scope-resolution intake rows under `reports/benchmark/*_source_review_packet.json`. Every candidate
starts as `needs_review` with `ready_for_manifest_promotion: false`, keeping curation separate from
verified local-law promotion until privacy and expert review are complete.

**Done next - source-review sprint packet.** `scripts/build_domain_source_review_sprint.py --domain
developing_country_worker_protections` turns the coverage matrix plus blank review packet into a
compact operations worklist. It puts broad-scope resolution first, selects only non-scope-blocked
source rows for immediate review, and defers rows that still depend on corridor/forum resolution.

**Done next - source-review progress ledger.** `scripts/build_domain_source_review_ledger.py --domain
developing_country_worker_protections` summarizes the blank or curator-filled review packet by gate
status: not started, in progress, ready-claimed, accepted, or blocked by validation. It gives curators
a compact status view before they run the validation gate.

**Done next - source-review validation gate.** `scripts/validate_domain_source_review_packet.py
--domain developing_country_worker_protections` validates curator-filled review packets and emits
manifest-shaped proposed rows only when source metadata, HTTPS URL, date, privacy, and expert-review
gates pass. It never mutates the grounding manifest.

**Done next - grounding-manifest proposal preview.** `scripts/build_domain_grounding_manifest_proposal.py
--domain developing_country_worker_protections` compares validated rows against the current grounding
manifest, classifies them as pending-row promotions or new source rows, rejects conflicts, validates a
preview manifest, and still leaves `grounding_sources.json` untouched.

**Done next - end-to-end curation bundle.** `scripts/build_domain_curation_bundle.py --domain
developing_country_worker_protections` runs the source-gated curation chain in memory and emits a
compact consistency report. With `--write-components`, it refreshes all generated queue, research-plan,
coverage-matrix, review-packet, sprint, ledger, validation, proposal, and bundle artifacts in one
offline pass.
`scripts/validate_domain_curation_bundle.py --domain developing_country_worker_protections` is the
read-only saved-artifact gate for that bundle. It keeps the handoff compact, rejects raw source or
prompt dumps, preserves blocked source/manifest/scoring readiness, and checks that recorded artifact
paths remain repo-relative or `external/<file>` rather than machine-local paths.

**Guarded — rich harness runner.** `scripts/rich_harness_lift.py` now detects non-trafficking domain
promptsets and refuses to score them as comparable lift evidence by default, because source-verified
domain RAG/tools are not implemented yet. An explicit diagnostic override writes to isolated gitignored
`reports/rich_lift/domains/<domain>/` paths and uses the promptset's registry-derived preamble, attached
grounding summary, and domain-specific judge rubric.

**Next — wiring the data layer into runs (engine-critical, do in a curated-breadth window):**
1. Work the generated grounding queue, source-research handoff, coverage matrix, blank review packet, sprint, ledger, validation
   report, manifest proposal preview, and curation bundle: curate dated source objects for each target jurisdiction,
   resolve broad corridor labels into concrete jurisdictions/forums, promote
   manifest rows from pending to `verified_local_law`, and implement the per-domain source-verified
   RAG/tool grounding layer. Only then should `rich_harness_lift.py --domain <id>` move from guarded
   diagnostic to comparable run evidence and into the engine queue → the **second+ columns** of a
   cross-domain leaderboard.
2. Grow each seeded pack via the domain-parameterised discovery-and-quality flywheel.

The trafficking domain stays the reference implementation and the headline; the others demonstrate the
framework, not a finished product, until each is expert-validated (§7).

## 9. Regulatory Miss Pattern Expansion Map

The broader sister-project idea now has a source-gated candidate catalog at
`configs/duecare/benchmarks/regulatory_miss_patterns.json`, rendered by
`scripts/build_regulatory_miss_pattern_plan.py`. It covers adjacent
low-documentation domains such as fisheries and maritime labour, private
security, artisanal mining, digital consumer credit, informal housing, and
education/training intermediaries.

This expansion map is propose-only. The builder rejects URL-like strings,
contact details, sensitive field names, duplicate IDs, and malformed rows. It
writes only gitignored planning artifacts under `reports/benchmark/` and keeps
every candidate blocked for comparable scoring until dated source objects,
privacy review, and expert review exist.

The next handoff is `scripts/build_regulatory_domain_intake_packet.py`, which
turns safe candidate patterns into blank curator intake rows. It keeps proposed
domain IDs, artifact paths, review notes, and readiness flags empty or false so
the catalog cannot accidentally become a source-verified domain registry.
`scripts/validate_regulatory_domain_intake_packet.py` is the non-mutating gate
for curator-filled rows: accepted rows are only domain-seed proposals, and the
validator still rejects prompt-generation or comparable-scoring readiness.
`scripts/build_regulatory_domain_seed_proposal.py` then turns accepted rows into
a registry-preview and file-scaffold checklist. It remains non-mutating and
keeps manual registry patching blocked until curators create and review the
seed files. `scripts/build_regulatory_curation_bundle.py --write-components`
runs that full regulatory chain in memory and refreshes the gitignored plan,
intake, validation, seed-proposal, and bundle reports. The bundle is only a
local consistency/readiness artifact; it still does not verify law, create seed
files, generate prompts, or authorize comparable scoring.

## 10. Global Protections Sister-Project Charter

The program-level sister project is now captured in
`configs/duecare/benchmarks/sister_projects/global_protections_regulatory_benchmark.json`
and rendered by `scripts/build_global_protections_project_plan.py`. This charter
sits above the active worker-protections seed and the regulatory candidate
catalog. It records the research question, jurisdiction families, benchmark
axes, source-admission rules, readiness gates, non-goals, and the first build
phases.

The generated plan remains non-mutating and non-scoring. It validates that the
charter is propose-only, privacy-safe, linked to the registered
`developing_country_worker_protections` seed, and linked to known regulatory
candidate patterns. It keeps prompt generation, training use, public claims,
worker-facing use, and comparable scoring blocked until source coverage, scope
resolution, privacy review, expert review, and a source-verified grounding layer
exist for the jurisdiction and protection category being tested.
`scripts/validate_global_protections_project_plan.py` is the matching read-only
gate for saved project-plan artifacts, checking section counts, seed/catalog
links, blocked downstream readiness, phase-output path hygiene,
privacy/disallowed-text findings, empty issue maps, and drift against the
current deterministic project-plan chain.

`scripts/build_global_protections_readiness_bundle.py` composes that charter
with the worker-protections source-curation bundle and the regulatory curation
bundle. It is the program-level readiness snapshot for the sister project: safe
for project planning can be true while worker prompts, candidate-domain
promotion, prompt generation, worker-facing use, and comparable scoring remain
explicitly false. It now also carries the source-channel matrix's official
legal-claim anchor IDs, making readiness the first composed checkpoint that can
reject legal-claim support drift.
`scripts/validate_global_protections_readiness_bundle.py` is the matching
read-only gate for saved readiness bundles, checking compact component
summaries, count integrity, blocked readiness flags, artifact-path hygiene,
raw-payload exclusions, privacy/disallowed-text findings, legal-anchor
source-channel continuity, and drift against the current composed chain.

`scripts/build_global_protections_jurisdiction_pack_matrix.py` adds the first
concrete pilot-pack planning layer above the broad jurisdiction families. It
crosses selected jurisdiction scopes with selected regulatory domain lenses and
creates blank source-object slots; every slot remains source-gap, not started,
and blocked pending dated public sources, archive status, privacy review,
source-path review, expert review, and the future grounding layer.
`scripts/validate_global_protections_jurisdiction_pack_matrix.py` is the
matching read-only gate for saved pack matrices, checking cross-product
completeness, source-slot integrity, compact scope/domain-lens ID summaries,
privacy/disallowed-text findings, and blocked prompt/scoring readiness.

`scripts/build_global_protections_source_channel_matrix.py` turns the charter's
target jurisdiction families into a non-fetching source-discovery matrix. It
covers official gazettes, ministry notices, regulator registries, courts,
rights bodies, consular advisories, social-channel notices, public-interest
reports, local-language archives, and expert-review notes while keeping
informal publications lead-only and all scoring readiness false.
`scripts/validate_global_protections_source_channel_matrix.py` is the matching
read-only gate for saved matrices, checking source-channel coverage,
lead-only informal-publication boundaries, official-only legal-claim anchors,
privacy/disallowed-text findings, and drift against the current deterministic
matrix chain. The matrix module exposes the official legal-claim anchor channel
IDs, and downstream benchmark blueprints must reuse that matrix-derived set.
The saved matrix summary also carries the legal-claim anchor source-channel
count and IDs, so the source layer is self-describing before benchmark artifacts
are generated.

`scripts/build_global_protections_source_channel_review_packet.py` converts that
matrix into blank curator intake rows. It records the metadata fields and review
gates that must be filled later while keeping every row not started and blocked
from manifest promotion, prompt generation, public claims, worker-facing use,
and comparable scoring.

`scripts/validate_global_protections_source_channel_review_packet.py` is the
matching read-only gate for saved source-channel review packets. It checks row
and status counts, informal-publication lead-only boundaries, official-only
legal-claim anchors, ISO source-intake dates when filled, privacy findings, and
drift against the current deterministic packet chain. The packet summary
preserves the matrix's legal-claim anchor source-channel count and IDs and fails
validation if they drift toward informal or context-only channels.

`scripts/build_global_protections_benchmark_blueprint.py` defines the future
benchmark shape without instantiating prompts. It creates task blueprints,
scoring-dimension blueprints, and abstention rules from the charter, then keeps
every task blocked until reviewed source objects, scope resolution, privacy
review, expert review, and the source-verified grounding layer exist.
`scripts/validate_global_protections_benchmark_blueprint.py` is the matching
read-only gate for saved blueprints, checking task shape, source-grounding
contracts, abstention rules, privacy/disallowed-text findings, and blocked
prompt/scoring readiness. It also rejects any saved blueprint whose
legal-claim anchor source-channel IDs drift away from the source-channel
matrix.

`scripts/build_global_protections_eval_contract.py` defines the future
evaluation record and judge-output contract. It names the required run gates
and failure modes for model-response capture and judging, and its
model-response schema carries both legal-claim anchor source-object IDs and
the matrix-derived legal-claim anchor source-channel IDs. It does not call
models, grade responses, or authorize comparable scoring.
`scripts/validate_global_protections_eval_contract.py` is the matching
read-only gate for saved contracts, checking record schemas, judge contracts,
failure modes, run gates, legal-anchor source-channel continuity,
privacy/disallowed-text findings, and blocked capture/scoring readiness.

`scripts/build_global_protections_diagnostic_run_plan.py` turns the blueprint
and evaluation contract into blocked dry-run diagnostic cells. It records the
gates, record fields, matrix-derived legal-claim anchor source-channel IDs,
judge fields, and failure checks that future model runs must satisfy while
keeping execution, response capture, and scoring false.
`scripts/validate_global_protections_diagnostic_run_plan.py` is the matching
read-only gate for saved diagnostic plans, checking diagnostic-cell shape,
run-gate coverage, required response/judge fields, legal-anchor source-channel
continuity, failure checks, privacy/disallowed-text findings, and blocked
execution/capture/scoring readiness.

`scripts/build_global_protections_judge_calibration_plan.py` turns the
evaluation contract and diagnostic plan into blocked calibration cases. Each
failure mode gets a calibration case, but example creation and judge
calibration remain false until reviewed positive/negative references, source
object or source-gap IDs, matrix-derived legal-claim anchor source-channel
IDs, privacy review, and expert review exist.
`scripts/validate_global_protections_judge_calibration_plan.py` is the matching
read-only gate for saved calibration plans, checking calibration-case shape,
failure-mode coverage, source-grounding coverage, legal-anchor source-channel
continuity, required response/judge findings, privacy/disallowed-text
findings, and blocked calibration/scoring readiness.

`scripts/build_global_protections_transition_gate.py` is the compact go/no-go
matrix for the sister-project chain. It keeps source promotion, prompt
instantiation, model-response capture, judge output, judge calibration, public
claims, worker-facing use, and comparable scoring blocked until the required
reviewed evidence exists. Every transition row preserves the matrix-derived
legal-claim anchor source-channel IDs.
`scripts/validate_global_protections_transition_gate.py` is the matching
read-only gate for saved transition artifacts, checking blocked transition
rows, gate-count integrity, legal-anchor source-channel continuity,
privacy/disallowed-text findings, and drift against the current deterministic
transition chain.

`scripts/build_global_protections_next_actions.py` turns that readiness snapshot
into an operator backlog. It orders scope-resolution rows, immediate source
review rows, deferred scope-blocked rows, regulatory candidate-intake rows, and
the later source-verified grounding-layer task without copying prompt text,
source URLs, private cases, or legal claims into the report. It also emits a
compact `execution_phases` sequence so reviewers can see which actions are
scope resolution, immediate source review, regulatory intake, deferred
source-review, and later grounding-layer work. Every action and phase preserves
the matrix-derived legal-claim anchor source-channel IDs.
`scripts/validate_global_protections_next_actions.py` is the read-only gate for
saved backlog artifacts, checking action counts, execution-phase coverage,
candidate rank order, artifact-path hygiene, privacy/disallowed-text findings,
blocked readiness flags, legal-anchor source-channel continuity, and drift
against the current deterministic next-actions chain. Its JSON, Markdown, and
CLI summaries report the execution-phase count and phase-covered action count
directly.

`scripts/build_global_protections_curator_sprint.py` turns the immediate backlog
items into a curator sprint packet with reviewer fields, acceptance checks, exit
gates, blocked-later visibility, and an `execution_phase_summary` tying sprint
IDs back to the source-gated backlog phases. It is still non-mutating and
non-scoring; sprint items, blocked-later rows, and phase summaries preserve the
same legal-anchor source-channel IDs, and its validator summaries report the
execution-phase count and phase-covered action count directly.

`scripts/build_global_protections_curation_bundle.py --write-components` is the
top-level status command for the sister project. It refreshes and summarizes the
project plan, jurisdiction-pack matrix, source-channel matrix, source-channel
review packet, benchmark blueprint, evaluation contract, diagnostic run plan,
judge-calibration plan, transition gate, readiness bundle, next-actions backlog,
and curator sprint packet without filling source rows, promoting manifests,
generating prompts, calling models, or authorizing comparable scoring. It also
summarizes next-actions and curator-sprint phase counts and phase-covered action
totals, so the top-level handoff proves the execution sequence still covers the
same backlog without carrying raw action rows. Add
`--write-all-components` when the same run should also refresh the lower-level
worker-protections and regulatory curation-chain handoff artifacts.
The bundle now also carries jurisdiction-pack scope/domain-lens IDs and the
source-channel matrix/review legal-anchor source-channel IDs as compact summary
fields, plus readiness blocker counts for verified local-law rows,
source-object tasks, scope-refinement tasks, regulatory candidates, and
seed-scaffold operations. That keeps pilot coverage, the official-anchor
boundary, and the still-not-score-ready state visible at the handoff layer.

`scripts/validate_global_protections_curation_bundle.py` is the matching
read-only gate for saved curation bundles. It catches stale summary counts, raw
payload dumps, URL-like source text, privacy findings, and scoring-readiness
drift, including readiness-blocker and phase-coverage drift, before the
artifact is used as a handoff. Its JSON and CLI summaries report the
next-actions and curator-sprint phase coverage directly and include
jurisdiction-pack IDs plus the source-layer legal-anchor channel IDs.
`scripts/validate_global_protections_saved_artifacts.py` is the aggregate
suite to run after `--write-components`; its default mode is read-only, and
`--refresh-components` first regenerates the component set before validating
it. `--refresh-all-components` also regenerates the lower-level handoff
artifacts, validates their recorded paths as optional checked extras,
inventories the lower-level worker-protections/regulatory artifacts exposed by
the component builders, and applies stronger packet/bundle validators where
available, including artifact-path map agreement for lower-level curation
bundles. Its JSON, Markdown, and CLI output also lift the top-level curation
bundle's next-actions and curator-sprint phase counts plus phase-covered action
totals into the one saved-artifact report, then compares them against the direct
next-actions and curator-sprint validation summaries. Any cross-artifact
phase-coverage mismatch fails the suite. It also compares the direct
jurisdiction-pack scope/domain-lens IDs against the curation bundle, then lifts
the benchmark legal-claim anchor source-channel IDs and fails if the evaluation
contract, source-channel matrix, source-channel review packet, diagnostic plan,
judge-calibration plan, transition gate, or curation bundle summaries drift
away from that matrix-derived official-anchor set. It also surfaces readiness
blocker counts for worker prompts, verified local-law rows, source-object
tasks, scope-refinement tasks, regulatory candidates, and seed-scaffold
operations, then fails if those planning-only blockers drift across the
readiness bundle, top-level curation bundle, or direct lower-level curation
bundles. The direct
lower-level curation validators also accept
`--component-dir`, and their Markdown summaries report that directory for
standalone scratch-component reviews. The current generated report lists 14
lower-level artifacts. The
suite loads each saved global-protections JSON artifact, checks the companion
Markdown handoff for basic readability/safety, verifies the top-level bundle's
recorded artifact paths, calls the matching component validator, and emits one
compact pass/fail report without embedding raw payloads.
