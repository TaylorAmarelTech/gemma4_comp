# Regulatory Miss Pattern Sister Benchmark

This note captures the broader sister-project idea: evaluate whether models can
handle local laws, protections, complaint paths, and regulatory uncertainty in
developing-country or low-documentation settings without hallucinating
authority.

The shared miss pattern is not limited to trafficking or migrant labour. Models
often recognize a broad harm but miss the controlling local rule, the right
forum, the cross-border split, the source date, or the worker/community safety
caveat.

## Candidate Domains

The propose-only catalog lives at
`configs/duecare/benchmarks/regulatory_miss_patterns.json`. It currently maps
these adjacent benchmark candidates:

- cross-border worker protections and remedies;
- fisheries, maritime labour, and port-state remedies;
- private security, guarding, and conflict-zone labour;
- artisanal mining, quarrying, and supply-chain protections;
- digital consumer credit, wage advances, and worker debt;
- informal housing, tenancy, and eviction protections;
- education, training, and recruitment-fee intermediaries.

These are not legal claims. They are source-gated benchmark candidates. Each
row describes the domain scope, legal dimensions, common model misses, prompt
families, expected source channels, and the conditions that must block
comparable scoring.

## Plan Builder

Generate the research-planning artifact with:

```bash
python scripts/build_regulatory_miss_pattern_plan.py
```

The default output is gitignored under:

- `reports/benchmark/regulatory_miss_pattern_plan.json`
- `reports/benchmark/regulatory_miss_pattern_plan.md`

Use validation-only mode when checking the catalog without writing generated
artifacts:

```bash
python scripts/build_regulatory_miss_pattern_plan.py --validate
```

The builder is deliberately conservative. It rejects URL-like strings, contact
details, local paths, sensitive field names, malformed IDs, duplicate IDs,
missing required sections, and unexpected fields. The output is only a planning
artifact; it does not fetch sources, verify law, build prompts, or authorize
scores. It also emits a ranked `expansion_queue`; the blank intake packet,
global next-actions backlog, and curator sprint preserve that rank as triage
metadata only.

Build the blank candidate-domain intake packet with:

```bash
python scripts/build_regulatory_domain_intake_packet.py
```

The default output is gitignored under:

- `reports/benchmark/regulatory_domain_intake_packet.json`
- `reports/benchmark/regulatory_domain_intake_packet.md`

This packet is the curator handoff between "this industry has the right miss
pattern" and "create a propose-only benchmark domain seed." Candidate rows
start with blank scope/artifact fields, review gates set to `not_started`, and
all readiness flags set to `false`.

Validate a curator-filled intake packet with:

```bash
python scripts/validate_regulatory_domain_intake_packet.py
```

The default output is gitignored under:

- `reports/benchmark/regulatory_domain_intake_validation.json`
- `reports/benchmark/regulatory_domain_intake_validation.md`

The validator accepts rows only as domain-seed proposals when the curator has
approved scope, canonical future artifact paths, privacy review, source-path
review, expert review, and domain-registry review. It still keeps prompt
generation and comparable scoring blocked.

Build a non-mutating domain-seed scaffold proposal from the validation report:

```bash
python scripts/build_regulatory_domain_seed_proposal.py
```

The default output is gitignored under:

- `reports/benchmark/regulatory_domain_seed_proposal.json`
- `reports/benchmark/regulatory_domain_seed_proposal.md`

This proposal contains a registry-preview entry and file-scaffold checklist for
accepted rows only. It still does not create files, edit the domain registry,
generate prompts, or authorize comparable scoring. In the default blank state,
it is a no-op with zero accepted operations.

Build the end-to-end regulatory curation bundle with:

```bash
python scripts/build_regulatory_curation_bundle.py --write-components
```

The default bundle output is gitignored under:

- `reports/benchmark/regulatory_curation_bundle.json`
- `reports/benchmark/regulatory_curation_bundle.md`

With `--write-components`, the command refreshes the plan, blank intake packet,
intake validation, seed proposal, and bundle artifacts in one offline pass. The
bundle reports local consistency across the sister-benchmark curation chain; it
still does not source-verify law, create domain files, generate prompts, or
authorize comparable scoring.

Validate a saved regulatory curation bundle with:

```bash
python scripts/validate_regulatory_curation_bundle.py
```

The default output is gitignored under:

- `reports/benchmark/regulatory_curation_bundle_validation.json`
- `reports/benchmark/regulatory_curation_bundle_validation.md`

The validator is read-only. It checks that the saved bundle still matches the
current deterministic curation chain, preserves the ranked candidate queue,
keeps prompt generation and comparable scoring blocked, avoids raw payload
sections, and does not contain source URLs, private case text, or other
disallowed source fields. Bundle artifact paths are handoff metadata only:
in-repo reports stay repo-relative, and caller-provided output directories are
recorded as `external/<file>` rather than machine-local absolute paths.

## Scoring Rule

No candidate domain should enter comparable benchmark scoring until:

- concrete jurisdictions, forums, or regulators are identified;
- dated source objects cover the local rule or complaint path being tested;
- public-source and privacy review has removed names, contact details, private
  cases, addresses, and small-community identifiers;
- an expert or practitioner has reviewed the mapping;
- the domain-specific runner has a source-verified RAG or tool-grounding layer.

The active `developing_country_worker_protections` seed is the first concrete
implementation of this pattern. The remaining rows are expansion candidates,
not finished benchmark domains.

## Sister-Project Charter

The broader program-level charter now lives at
`configs/duecare/benchmarks/sister_projects/global_protections_regulatory_benchmark.json`
and is rendered by:

```bash
python scripts/build_global_protections_project_plan.py
```

That builder checks the charter against the registered worker-protections seed
and the regulatory miss-pattern catalog, then writes gitignored JSON and
Markdown reports under `reports/benchmark/`. It is a readiness and scope
artifact only. It does not source-verify law, create prompts, edit manifests,
or authorize comparable scoring.

Validate that saved plan with:

```bash
python scripts/validate_global_protections_project_plan.py
```

This read-only gate keeps the root sister-project handoff compact,
privacy-safe, linked to the current seed/catalog state, and blocked from prompt
generation, worker-facing use, and comparable scoring.

The composed readiness bundle is generated by:

```bash
python scripts/build_global_protections_readiness_bundle.py
```

Validate a saved readiness bundle with:

```bash
python scripts/validate_global_protections_readiness_bundle.py
```

This read-only validator keeps the composed project/domain/regulatory summary
compact, blocks prompt generation and comparable scoring, rejects raw payload
sections or source URL dumps, and checks drift against the current readiness
chain.

It reports whether the project charter, the worker-protections source-curation
chain, and this regulatory candidate chain still agree on the important safety
state: planning is allowed, but prompt generation and comparable scoring remain
blocked.

The pilot jurisdiction-pack matrix is generated by:

```bash
python scripts/build_global_protections_jurisdiction_pack_matrix.py
```

It turns the sister-project idea into concrete, still-blocked pack cells:
selected jurisdiction scopes crossed with selected regulatory domain lenses,
each carrying blank source-object slots and review gates. It does not verify
law, store source locators, generate prompts, or authorize comparable scoring.

Validate that saved matrix with:

```bash
python scripts/validate_global_protections_jurisdiction_pack_matrix.py
```

The validator is read-only. It keeps the cross-product complete, source-object
slots unpromoted, URL/raw source fields absent, privacy scans clean, and every
prompt/scoring readiness flag blocked. The generated summary records pilot
jurisdiction scope IDs and domain-lens IDs, and the validator rejects drift in
those compact coverage lists.

The source-channel matrix is generated by:

```bash
python scripts/build_global_protections_source_channel_matrix.py
```

It gives curators a repeatable map of source channels for lower-documentation
jurisdictions, including official gazettes, ministry notices, regulator
registries, courts, rights bodies, consular advisories, social-channel notices,
public-interest reports, local-language archives, and expert-review notes.
Informal publications stay lead-only until archived, dated, public-interest
reviewed, privacy reviewed, and backed by a real source path.

Validate that saved matrix with:

```bash
python scripts/validate_global_protections_source_channel_matrix.py
```

This read-only gate keeps the jurisdiction-family/source-channel matrix
complete, informal publications lead-only, legal-claim anchors limited to
official law or administrative sources, and every prompt/scoring readiness flag
blocked. The matrix module exposes the official legal-claim anchor channel IDs
that downstream benchmark blueprints must reuse. The saved matrix summary now
also records that channel count and ID list so validators can reject summary
drift before a later artifact broadens legal-claim support.

The blank source-channel review packet is generated by:

```bash
python scripts/build_global_protections_source_channel_review_packet.py
```

It gives curators one not-started intake row for each source-channel matrix row
without storing source locators, raw text, private case details, or legal
claims.

Validate that saved packet with:

```bash
python scripts/validate_global_protections_source_channel_review_packet.py
```

This read-only gate keeps informal publications lead-only, local-law claim
anchors limited to official law or administrative sources, source-intake dates
ISO-formatted when filled, and every prompt/scoring readiness flag blocked. Its
summary preserves the same legal-claim anchor source-channel count and IDs as
the matrix.

The source-gated benchmark blueprint is generated by:

```bash
python scripts/build_global_protections_benchmark_blueprint.py
```

It converts the charter's benchmark axes and scored capabilities into task
blueprints, scoring-dimension blueprints, and abstention rules. It still does
not create prompt text: every task blueprint is blocked pending reviewed source
objects, privacy review, expert review, scope resolution, and the future
source-verified grounding layer.

Validate that saved blueprint with:

```bash
python scripts/validate_global_protections_benchmark_blueprint.py
```

This read-only validator keeps task blueprints blocked, source-grounding
contracts intact, source-gap abstention explicit, raw source/prompt fields
absent, and comparable scoring false. It also rejects any saved blueprint whose
legal-claim anchor source-channel IDs drift away from the source-channel
matrix.

The evaluation contract is generated by:

```bash
python scripts/build_global_protections_eval_contract.py
```

It defines the future model-response record fields, judge-output fields, run
gates, and failure modes for regulatory miss testing. Model-response records
must carry both legal-claim anchor source-object IDs and the matrix-derived
legal-claim anchor source-channel IDs, keeping official legal anchors distinct
from lead-only informal sources. It does not call models, grade responses, or
turn diagnostic results into comparable benchmark evidence.

Validate a saved evaluation contract with:

```bash
python scripts/validate_global_protections_eval_contract.py
```

This read-only validator keeps the record schemas, judge contracts, failure
taxonomy, run gates, legal-anchor source-channel continuity,
privacy/disallowed-text checks, and blocked scoring flags intact.

The blocked diagnostic run plan is generated by:

```bash
python scripts/build_global_protections_diagnostic_run_plan.py
```

It creates one dry-run diagnostic cell per task blueprint and carries forward
the required run gates, record schemas, legal-claim anchor source-channel IDs,
and failure checks. It still does not instantiate prompts, call models, capture
responses, or authorize comparable benchmark evidence.

Validate a saved diagnostic run plan with:

```bash
python scripts/validate_global_protections_diagnostic_run_plan.py
```

This read-only validator keeps diagnostic cells blocked, run-gate coverage
complete, model-response and judge-output fields intact, legal-anchor
source-channel IDs aligned with the source-channel matrix, failure checks
present, privacy/disallowed-text checks clean, and comparable scoring false.

The judge-calibration plan is generated by:

```bash
python scripts/build_global_protections_judge_calibration_plan.py
```

It creates one blocked calibration case per failure mode and requires reviewed
positive/negative example references, source-object or source-gap identifiers,
matrix-derived legal-claim anchor source-channel IDs, privacy review, and
expert review before any judge calibration can begin.

Validate a saved judge-calibration plan with:

```bash
python scripts/validate_global_protections_judge_calibration_plan.py
```

This read-only validator keeps calibration cases blocked, failure-mode coverage
complete, source controls and legal-anchor source-channel IDs intact, judge
obligations present, privacy and disallowed-text checks clean, and comparable
scoring false.

The blocked transition gate is generated by:

```bash
python scripts/build_global_protections_transition_gate.py
```

It is the go/no-go matrix for source promotion, prompt instantiation,
model-response capture, judge output, judge calibration, public claims,
worker-facing use, and comparable scoring. Every transition remains blocked in
the default source-gap state, and every row preserves the matrix-derived
legal-claim anchor source-channel IDs.

Validate that saved gate with:

```bash
python scripts/validate_global_protections_transition_gate.py
```

This read-only validator keeps the transition rows blocked, preserves the
source-grounding, legal-anchor source-channel, date, language, entity, remedy,
authority, coverage, jurisdiction, implementation, and procedure gate counts,
rejects raw source/prompt/response dumps, and confirms the saved gate still
matches the deterministic chain.

For the operational worklist across both the worker-protections seed and the
regulatory candidates, run:

```bash
python scripts/build_global_protections_next_actions.py
```

That backlog keeps candidate-domain intake as review work only; it does not
create seed files, generate prompts, or authorize scoring. It includes a compact
`execution_phases` sequence that covers every backlog action once while keeping
prompt generation, worker-facing use, public claims, and comparable scoring
blocked after every phase. The readiness layer and each backlog action preserve
the matrix-derived legal-claim anchor source-channel IDs so legal claims cannot
fall back to informal notices or social-channel leads.

Validate the saved backlog with:

```bash
python scripts/validate_global_protections_next_actions.py
```

This read-only gate keeps action counts, execution-phase coverage, candidate
rank order, privacy checks, artifact paths, prompt-generation readiness, and
comparable-scoring readiness consistent before the backlog is used as an
operator handoff. Its JSON, Markdown, and CLI summaries report the
execution-phase count and phase-covered action count directly.

The curator-facing sprint packet is generated by:

```bash
python scripts/build_global_protections_curator_sprint.py
```

It gives reviewers the immediate candidate-intake fields and acceptance checks
without promoting any candidate to a domain seed. It preserves the backlog
`execution_phase_summary` as sprint and blocked-later action IDs so reviewers
can see where each candidate-intake row sits in the source-gated sequence. Sprint
items and blocked-later rows carry the same official legal-anchor source-channel
allowlist as the backlog.

Validate the saved sprint packet with:

```bash
python scripts/validate_global_protections_curator_sprint.py
```

This read-only gate keeps the ranked candidate handoff privacy-safe,
phase-covered, and non-scoring before human review work starts. Its JSON,
Markdown, and CLI summaries report the execution-phase count and
phase-covered action count directly.

The top-level curation bundle is generated by:

```bash
python scripts/build_global_protections_curation_bundle.py --write-components
```

Use `--write-all-components` when the top-level run should also refresh the
lower-level worker-protections source-curation and regulatory curation-chain
handoff artifacts behind the readiness bundle.

It refreshes and summarizes the global protections project plan,
jurisdiction-pack matrix, source-channel matrix, source-channel review packet,
benchmark blueprint, evaluation contract, diagnostic run plan,
judge-calibration plan, transition gate, readiness bundle, next-actions
backlog, and curator sprint packet while keeping source verification, prompt
generation, and comparable scoring blocked. It also exposes compact
next-actions and curator-sprint phase counts plus phase-covered action totals,
so the top-level handoff proves the execution sequence still covers the same
30-action backlog without embedding the raw backlog. It also lifts the
jurisdiction-pack scope/domain-lens IDs plus source-channel matrix and
source-channel review legal-anchor source-channel IDs into the bundle summary
and component summaries. The same top-level summary carries readiness blocker
counts for verified local-law rows, source-object tasks, scope-refinement
tasks, regulatory candidates, and seed-scaffold operations.

Validate that saved top-level artifact with:

```bash
python scripts/validate_global_protections_curation_bundle.py
```

The validator is read-only and rejects stale counts, phase-coverage drift, raw
backlog dumps, URL-like source text, privacy findings, and any readiness flag
drift toward scoring. Its JSON and CLI summaries report the next-actions and
curator-sprint phase coverage directly, plus readiness blocker counts and the
source-layer legal-anchor source-channel IDs needed to audit the official-anchor
boundary.

Validate the whole regenerated saved-artifact set with:

```bash
python scripts/validate_global_protections_saved_artifacts.py
```

Use `--refresh-components` for a one-command local refresh and validation pass:

```bash
python scripts/validate_global_protections_saved_artifacts.py --refresh-components
```

Use `--refresh-all-components` to refresh and validate those lower-level
handoff artifacts in the same pass while still validating the canonical saved
global-protections artifact set.

The default suite run is read-only; refresh mode first rewrites the generated
component artifacts. The suite checks companion Markdown reports for basic
readability/safety, verifies the top-level bundle's recorded artifact paths,
calls each global-protections component validator, runs compact validation for
the builder-exposed lower-level worker-protections/regulatory artifacts when
requested, and applies stronger packet/bundle validators where available,
including artifact-path map agreement for lower-level curation bundles. The
aggregate JSON, Markdown, and CLI output also lift the top-level curation
bundle's next-actions and curator-sprint phase counts plus phase-covered action
totals, so reviewers can see the execution-sequence coverage from the one
saved-artifact report. The same suite compares those totals against the direct
next-actions and curator-sprint validation summaries and fails on any
cross-artifact phase-coverage mismatch. It also compares direct
jurisdiction-pack scope/domain-lens IDs against the curation bundle, then lifts
the benchmark legal-claim anchor source-channel IDs and fails if the evaluation
contract, source-channel matrix, source-channel review packet, diagnostic plan,
judge-calibration plan, transition gate, or curation bundle summaries drift
away from that matrix-derived official-anchor set. It also lifts the readiness
blocker counts for worker prompts, verified local-law rows, source-object
tasks, scope-refinement tasks, regulatory candidates, and seed-scaffold
operations, then fails if those planning-only blockers drift between the
readiness bundle, top-level curation bundle, and direct lower-level curation
bundles.
The direct lower-level curation validators also accept `--component-dir`, and
their Markdown summaries report that directory for standalone scratch-component
reviews. The current generated report lists 14 lower-level artifacts. It emits
a compact pass/fail handoff for the project plan, matrices, packets, contracts,
blocked run plans, readiness artifacts, backlog, sprint packet, and top-level
bundle.
