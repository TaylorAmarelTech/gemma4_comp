# Global Protections Regulatory Benchmark

This note is the sister-project charter for testing whether models can handle
laws, regulations, protections, complaint paths, and source uncertainty in
developing-country or low-documentation contexts.

The project is not a legal advice product and not worker-facing. It is a
source-gated benchmark program: measure when a model overgeneralizes from
better documented regimes, invents local law, misses cross-border responsibility,
or routes people to unsafe or non-jurisdictional remedies.

## Charter

The versioned charter lives at:

`configs/duecare/benchmarks/sister_projects/global_protections_regulatory_benchmark.json`

It links the active `developing_country_worker_protections` seed domain to the
broader regulatory miss-pattern catalog. The charter records:

- target jurisdiction families;
- benchmark axes such as local-law discipline, source-date sensitivity, informal
  publication handling, and remedy routing;
- source admission rules;
- scored capabilities;
- readiness gates;
- explicit non-goals.

## Plan Builder

Generate the non-mutating project plan with:

```bash
python scripts/build_global_protections_project_plan.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_project_plan.json`
- `reports/benchmark/global_protections_project_plan.md`

Use validation-only mode when checking the charter without writing generated
artifacts:

```bash
python scripts/build_global_protections_project_plan.py --validate
```

The builder validates that the charter is propose-only, privacy-safe, linked to
the registered worker-protections seed, and linked to known regulatory candidate
patterns. It rejects URL-like strings, contact details, sensitive field names,
absolute/local paths, duplicate or unsafe IDs, and readiness phases that claim
public scoring or worker-facing use.

Validate a saved project-plan artifact with:

```bash
python scripts/validate_global_protections_project_plan.py
```

The validator is read-only. It checks the saved plan shape, section counts,
seed-domain and regulatory-candidate links, embedded builder checks, blocked
downstream readiness flags, phase-output path hygiene, privacy/disallowed-text
findings, empty issue maps, and drift against the current deterministic
project-plan chain.

## Jurisdiction-Pack Matrix

Generate the propose-only pilot jurisdiction-pack matrix with:

```bash
python scripts/build_global_protections_jurisdiction_pack_matrix.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_jurisdiction_pack_matrix.json`
- `reports/benchmark/global_protections_jurisdiction_pack_matrix.md`

The matrix combines concrete pilot jurisdiction scopes with selected regulatory
domain lenses and emits source-object slots for later curator work. It does not
verify law, name source locators, create prompts, or authorize scoring. Every
slot starts `not_started`, requires dated source objects, archive status,
privacy review, source-path review, and expert review, and leaves prompt
generation and comparable scoring blocked. The summary records the pilot
jurisdiction scope IDs and domain-lens IDs, so reviewers can audit exact pilot
coverage without scanning every pack cell.

Validate a saved jurisdiction-pack matrix with:

```bash
python scripts/validate_global_protections_jurisdiction_pack_matrix.py
```

The validator is read-only. It checks the jurisdiction/domain cross-product,
source-slot shape, not-started source coverage, blocked readiness flags,
privacy scan results, disallowed raw source fields, and drift against the
current deterministic matrix chain. It also rejects summary drift in the compact
scope-ID and domain-lens-ID lists.

## Source-Channel Matrix

Generate the source-channel matrix with:

```bash
python scripts/build_global_protections_source_channel_matrix.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_source_channel_matrix.json`
- `reports/benchmark/global_protections_source_channel_matrix.md`

The matrix turns target jurisdiction families into source-discovery work across
official gazettes, ministry notices, regulator registries, courts or tribunals,
ombuds or rights bodies, consular advisories, social-channel notices or scanned
circulars, NGO/ILO/IOM/UN public-interest reports, local-language archives, and
expert review notes. Informal publications remain source leads only until they
are archived, dated, public-interest reviewed, privacy reviewed, and backed by a
proper source path.

Validate a saved source-channel matrix with:

```bash
python scripts/validate_global_protections_source_channel_matrix.py
```

The validator is read-only. It checks matrix shape, source-channel row counts,
jurisdiction-family/source-channel coverage, informal-publication lead-only
boundaries, legal-claim anchor limits, blocked readiness flags, privacy scan
results, disallowed raw source fields, and drift against the current
deterministic source-channel matrix chain. The matrix module exposes the
official legal-claim anchor channel IDs, and downstream benchmark blueprints
must use that matrix-derived set rather than a separate hardcoded list. The
saved matrix summary also records the legal-claim anchor source-channel count
and IDs, so validators can reject summary drift before downstream artifacts are
built.

Generate the blank source-channel review packet with:

```bash
python scripts/build_global_protections_source_channel_review_packet.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_source_channel_review_packet.json`
- `reports/benchmark/global_protections_source_channel_review_packet.md`

The packet gives curators one blank intake row for every matrix row. All rows
start `not_started`, with manifest promotion, prompt generation, training use,
public claims, worker-facing use, and comparable scoring set to false.

Validate a saved source-channel review packet with:

```bash
python scripts/validate_global_protections_source_channel_review_packet.py
```

The validator is read-only. It checks row counts, status counts, blocked
readiness flags, informal-publication lead-only boundaries, legal-claim anchor
limits, ISO date format for filled date fields, privacy scan results, and
drift against the current deterministic source-channel review chain. The saved
packet summary carries the same legal-claim anchor source-channel count and IDs
as the matrix, and the validator rejects any broadening toward informal or
context-only channels.

## Benchmark Blueprint

Generate the source-gated benchmark blueprint with:

```bash
python scripts/build_global_protections_benchmark_blueprint.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_benchmark_blueprint.json`
- `reports/benchmark/global_protections_benchmark_blueprint.md`

The blueprint is the bridge between source curation and future model tests. It
defines task blueprints, scoring-dimension blueprints, and abstention rules for
the project without creating prompt text or legal claims. Each task blueprint is
blocked pending source review and requires reviewed source objects, privacy
review, expert review, scope resolution, and the source-verified grounding
layer before it can be instantiated.

Validate a saved benchmark blueprint with:

```bash
python scripts/validate_global_protections_benchmark_blueprint.py
```

The validator is read-only. It checks task-blueprint shape, source-grounding
contracts, abstention rules, scoring-dimension readiness, blocked prompt and
scoring flags, privacy scan results, raw source/prompt-field exclusions, and
drift against the current deterministic blueprint chain. It also rejects any
saved blueprint whose legal-claim anchor source-channel IDs no longer match the
source-channel matrix.

## Evaluation Contract

Generate the source-gated evaluation contract with:

```bash
python scripts/build_global_protections_eval_contract.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_eval_contract.json`
- `reports/benchmark/global_protections_eval_contract.md`

The contract defines the future model-response record schema, judge-output
schema, required run gates, and failure taxonomy for this project. The
model-response schema records both legal-claim anchor source-object IDs and the
matrix-derived legal-claim anchor source-channel IDs, so reviewed source
objects cannot silently broaden the official-only anchor policy downstream. It
is still non-running and non-scoring: it does not instantiate prompts, call
models, grade responses, publish claims, or authorize comparable scoring.

Validate a saved evaluation contract with:

```bash
python scripts/validate_global_protections_eval_contract.py
```

The validator is read-only. It checks model-response and judge-output field
schemas, judge dimension contracts, failure modes, run gates, embedded builder
checks, matrix-derived legal-anchor source-channel continuity, blocked
readiness flags, privacy scan results, raw source/prompt-field exclusions, and
drift against the current deterministic evaluation-contract chain.

## Diagnostic Run Plan

Generate the blocked diagnostic run plan with:

```bash
python scripts/build_global_protections_diagnostic_run_plan.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_diagnostic_run_plan.json`
- `reports/benchmark/global_protections_diagnostic_run_plan.md`

The run plan creates one dry-run diagnostic cell per task blueprint. Each cell
records the required run gates, model-response fields, matrix-derived
legal-claim anchor source-channel IDs, judge-output fields, and failure modes
to check later, but every cell stays blocked pending source review. It does not
instantiate prompts, call models, capture responses, grade outputs, or
authorize comparable scoring.

Validate a saved diagnostic run plan with:

```bash
python scripts/validate_global_protections_diagnostic_run_plan.py
```

The validator is read-only. It checks diagnostic-cell shape, run-gate coverage,
required model-response fields, legal-anchor source-channel continuity,
required judge-output fields, failure checks, embedded builder checks, blocked
execution/capture/scoring flags, privacy scan results, raw source/prompt-field
exclusions, and drift against the current deterministic diagnostic-run-plan
chain.

## Judge Calibration Plan

Generate the blocked judge-calibration plan with:

```bash
python scripts/build_global_protections_judge_calibration_plan.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_judge_calibration_plan.json`
- `reports/benchmark/global_protections_judge_calibration_plan.md`

The plan creates one blocked calibration case per failure mode. Each case
requires curator-approved positive and negative example references, reviewed
source-object identifiers or source-gap markers, matrix-derived legal-claim
anchor source-channel IDs, redacted expected findings, privacy review, and
expert review before judge calibration can start.

Validate a saved judge-calibration plan with:

```bash
python scripts/validate_global_protections_judge_calibration_plan.py
```

The validator is read-only. It checks calibration-case shape, failure-mode
coverage, source-grounding coverage, legal-anchor source-channel continuity,
required model-response fields, required judge-output findings,
pre-calibration gates, judge obligations, embedded builder checks, blocked
calibration/scoring flags, privacy scan results, raw response/source-field
exclusions, and drift against the current deterministic judge-calibration
chain.

## Transition Gate

Generate the blocked transition gate with:

```bash
python scripts/build_global_protections_transition_gate.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_transition_gate.json`
- `reports/benchmark/global_protections_transition_gate.md`

The gate is the compact go/no-go matrix for the project. It keeps source
promotion, prompt instantiation, model-response capture, judge output, judge
calibration, training use, public claims, worker-facing use, and comparable
scoring blocked until the required reviewed evidence exists. Every transition
row preserves the matrix-derived legal-claim anchor source-channel IDs.

Validate a saved transition gate with:

```bash
python scripts/validate_global_protections_transition_gate.py
```

The validator is read-only. It checks the saved transition rows, gate counts,
legal-anchor source-channel continuity, embedded builder checks, blocked
status, readiness flags, privacy scan results, raw source/prompt/response-field
exclusions, and drift against the current deterministic transition chain.

## Readiness Rule

The plan can be safe for project planning while still blocking prompt
generation, training use, public claims, worker-facing use, and comparable
scoring. Those uses remain blocked until source coverage, scope resolution,
privacy review, expert review, and a source-verified RAG or tool grounding layer
exist for the actual jurisdiction and protection category being tested.

The current worker-protections curation bundle and regulatory curation bundle
are the first two operational inputs. This project plan sits above them as the
charter/readiness view; it does not fetch sources, verify law, create prompts,
edit manifests, or authorize leaderboard claims.

## Regulatory Expansion Queue

Generate the adjacent-domain expansion plan with:

```bash
python scripts/build_regulatory_miss_pattern_plan.py
```

The default output is gitignored under:

- `reports/benchmark/regulatory_miss_pattern_plan.json`
- `reports/benchmark/regulatory_miss_pattern_plan.md`

The plan now includes a deterministic `expansion_queue` for the developing-country
regulatory sister project. The queue ranks candidate domains by legal
dimension breadth, source-channel complexity, model-miss coverage, source-gate
count, and low-documentation signals such as cross-border scope, informal
publication channels, privacy or retaliation risk, ordinary-protection breadth,
and fragmented source paths. The queue is triage metadata only: every candidate
still remains blocked for domain seeding, prompt generation, public claims,
worker-facing use, and comparable scoring until curator, privacy, source, and
expert-review gates pass.

The regulatory curation bundle and blank intake packet preserve the queue so a
curator can decide whether the next sister domain should be housing/eviction,
maritime labour, consumer-credit debt, education/training fees, mining, private
security, or another reviewed candidate without turning that decision into a
legal claim. The top-level next-actions backlog and curator sprint packet also
preserve the rank, score, priority band, and top-candidate marker, so curator
work starts from the same source-gated queue while prompt generation and
comparable scoring remain blocked.

Validate the saved regulatory expansion bundle with:

```bash
python scripts/validate_regulatory_curation_bundle.py
```

The validator is read-only. It compares the saved bundle to the current
deterministic regulatory chain, checks queue-count and top-candidate drift,
rejects raw payload sections or source URL dumps, and keeps prompt generation
and comparable scoring blocked.

## Readiness Bundle

Generate the composed readiness report with:

```bash
python scripts/build_global_protections_readiness_bundle.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_readiness_bundle.json`
- `reports/benchmark/global_protections_readiness_bundle.md`

The bundle composes the project-plan builder, the
`developing_country_worker_protections` source-curation bundle, and the
regulatory candidate curation bundle. It is the quickest current check for the
whole sister-project stack: the charter can be safe for planning while all
worker-protection prompts remain blocked for comparable scoring and all
regulatory candidate domains remain blocked from prompt generation.

Use `--write-components` to refresh the upstream project, domain, and regulatory
bundle artifacts together. Use `--write-all-components` when the lower-level
source-review and regulatory-intake component artifacts should also be
refreshed.

Validate a saved readiness bundle with:

```bash
python scripts/validate_global_protections_readiness_bundle.py
```

The validator is read-only. It checks compact top-level shape, component-summary
shape, summary counts, embedded builder checks, blocked prompt/training/public/
worker-facing/scoring flags, artifact-path hygiene, raw payload exclusions,
privacy scan results, raw source/prompt-field exclusions, and drift against the
current deterministic readiness chain. It also carries and validates the
matrix-derived legal-claim anchor source-channel IDs so later handoff artifacts
cannot silently broaden legal-claim support beyond official gazette/law-portal
and labour/migration-ministry channels. Readiness-bundle artifact paths are
handoff metadata only: they must stay safe repo-relative labels for in-repo generated reports
or privacy-safe external labels for caller-provided output directories, never
machine-local absolute paths. Safe external filenames can appear as
`external/<name>`; private-looking repo-relative path segments and private-looking
or malformed external names collapse to `external/custom_or_invalid`.

## Next-Actions Backlog

Generate the operator backlog with:

```bash
python scripts/build_global_protections_next_actions.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_next_actions.json`
- `reports/benchmark/global_protections_next_actions.md`

The backlog turns the readiness state into ordered work items: scope-resolution
rows, immediate source-review rows, deferred source rows, regulatory candidate
intake rows, and the later source-verified grounding-layer task. It stays
compact and privacy-safe: no prompt text, source URLs, private cases, or legal
claims are copied into the report. It also emits a compact `execution_phases`
sequence that covers every backlog action once, names the phase dependencies,
and keeps prompt generation, training use, public claims, worker-facing use, and
comparable scoring false after every phase. Every action and execution phase
preserves the matrix-derived legal-claim anchor source-channel IDs.

Validate a saved backlog with:

```bash
python scripts/validate_global_protections_next_actions.py
```

The validator is read-only. It checks action shape, execution-phase coverage,
counts by lane/status, embedded builder checks, blocked readiness flags,
regulatory candidate rank order, artifact-path hygiene, raw payload exclusions,
privacy scan results, raw source/prompt-field exclusions, and drift against the
current deterministic next-actions chain. Its JSON, Markdown, and CLI summaries
report the execution-phase count and phase-covered action count directly.

## Curator Sprint Packet

Generate the immediate curator handoff with:

```bash
python scripts/build_global_protections_curator_sprint.py
```

The default output is gitignored under:

- `reports/benchmark/global_protections_curator_sprint.json`
- `reports/benchmark/global_protections_curator_sprint.md`

This packet extracts the immediately reviewable work from the backlog:
scope-resolution rows, source-review rows, and regulatory candidate-intake
rows. It adds reviewer fields, acceptance checks, and exit gates while keeping
blocked-later items visible. It also carries an `execution_phase_summary` that
maps each backlog phase to immediate sprint IDs and blocked-later IDs, so the
human handoff stays tied to the source-gated execution sequence. Sprint items,
blocked-later items, and execution-phase summaries preserve the same legal-claim
anchor source-channel IDs as the readiness and backlog layers.

Validate a saved curator sprint packet with:

```bash
python scripts/validate_global_protections_curator_sprint.py
```

The validator is read-only. It checks that sprint counts match the saved
worklist sections, execution-phase coverage matches the sprint packet, prompt
generation and comparable scoring remain blocked, regulatory candidate ranks
are contiguous with the top candidate first, source-review rows are still
unpromoted, and the saved summary/phase summary match the current deterministic
chain. Its JSON, Markdown, and CLI summaries report the execution-phase count
and phase-covered action count directly.

## Curation Bundle

Generate the top-level curation bundle with:

```bash
python scripts/build_global_protections_curation_bundle.py --write-components
```

Use `--write-all-components` when the same run should also refresh the
lower-level worker-protections source-curation artifacts and regulatory
curation-chain artifacts that feed the readiness bundle.

The default output is gitignored under:

- `reports/benchmark/global_protections_curation_bundle.json`
- `reports/benchmark/global_protections_curation_bundle.md`

This bundle composes the project plan, jurisdiction-pack matrix,
source-channel matrix, source-channel review packet, benchmark blueprint,
evaluation contract, diagnostic run plan, judge-calibration plan, transition
gate, readiness bundle, next-actions backlog, and curator sprint packet into
one consistency/readiness artifact. It carries compact execution-phase counts
and phase-covered action totals for both the next-actions backlog and curator
sprint, jurisdiction-pack scope/domain-lens IDs, plus source-matrix and
source-review legal-claim anchor source-channel counts and IDs, and readiness
blocker counts for verified local-law rows, source-object tasks,
scope-refinement tasks, regulatory candidates, and seed-scaffold operations,
without copying raw action rows into the bundle. It is
non-mutating and non-scoring: it does not verify law, fill source rows, promote
manifests, create prompts, train models, enable worker-facing use, or authorize
comparable benchmark claims.

Validate a saved bundle artifact with:

```bash
python scripts/validate_global_protections_curation_bundle.py
```

The validator is read-only. It checks the saved JSON shape, compact payload
rules, privacy scan, artifact-path hygiene, blocked readiness flags, summary
counts, readiness blocker counts, and phase-coverage counts against the current
source-gated chain. Its
JSON and CLI summaries report the next-actions and curator-sprint phase
coverage directly, and also surface source-layer legal-anchor channel IDs so
source matrix/review drift is visible in the top-level handoff.

Validate the full saved artifact set after `--write-components` with:

```bash
python scripts/validate_global_protections_saved_artifacts.py
```

For a one-command local refresh and validation pass, use:

```bash
python scripts/validate_global_protections_saved_artifacts.py --refresh-components
```

Use `--refresh-all-components` when the refresh should also rebuild and
validate the lower-level worker-protections and regulatory curation-chain
artifacts before the same saved-artifact validation gate runs.

The default suite run is read-only; `--refresh-components` first rewrites the
canonical generated component artifacts before validating them, while
`--refresh-all-components` also rewrites the optional lower-level artifacts,
allows their recorded paths as checked extras, inventories the lower-level
worker-protections/regulatory artifacts exposed by the component builders, and
runs compact validation for the source-review packet, regulatory intake packet,
and both lower-level curation bundles, including their own artifact-path maps.
The aggregate JSON, Markdown, and CLI output also lift the top-level curation
bundle's next-actions and curator-sprint phase counts plus phase-covered action
totals, so reviewers can see the execution-sequence coverage from the one
saved-artifact report. The same suite compares those totals against the direct
next-actions and curator-sprint validation summaries and fails on any
cross-artifact phase-coverage mismatch. It also lifts the direct
jurisdiction-pack scope/domain-lens IDs and fails if the curation bundle drifts
away from that pilot coverage. It also lifts the benchmark legal-claim anchor
source-channel IDs and fails if the evaluation contract, source-channel matrix,
source-channel review packet, diagnostic plan, judge-calibration plan,
transition gate, or curation bundle summaries drift away from that
matrix-derived official-anchor set. It now also surfaces the readiness blocker
counts for worker prompts, verified local-law rows, source-object tasks,
scope-refinement tasks, regulatory candidates, and seed-scaffold operations,
then fails if the readiness bundle, top-level curation bundle, or direct
lower-level curation bundles disagree about those planning-only blockers.
The direct lower-level curation validators also accept `--component-dir`, and
their Markdown summaries report that directory so reviewers can tell whether a
standalone report checked the canonical output directory or a scratch
component set.
The current generated report lists 14 lower-level artifacts. The suite loads
the project plan, matrices, review
packet, blueprint, evaluation contract, diagnostic plan, judge-calibration
plan, transition gate, readiness bundle, next-actions backlog, curator sprint,
and curation bundle, checks their companion Markdown reports for basic
readability/safety, verifies the curation bundle's recorded artifact paths
against the saved files, then calls each component validator and emits one
compact summary without embedding raw payloads.
