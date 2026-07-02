# Developing-Country Worker Protections Seed Domain

This is a propose-only benchmark seed for testing whether models can reason
about worker protections, local legal uncertainty, and cross-border remedy
routing in lower-resource jurisdictions and migration corridors.

The prompt rows are synthetic composites. They are not legal advice, not source
verified country law, and not evidence about any real worker, recruiter, or
employer. Before public claims or training use, each jurisdiction-specific
mapping needs a dated source object and expert review.

`grounding_sources.json` is the source-gating scaffold for this sister domain.
It currently marks four ILO instruments as international anchors and keeps
country-law, license-registry, hotline, fee-cap, and informal social-channel
rows pending until they have dated source objects. The benchmark runner may use
the anchors to test uncertainty discipline, but it must not treat pending local
rows as verified law.

The intended failure modes are:

- inventing confident country-law answers where the local source is missing or
  only posted through an informal channel;
- recognizing trafficking or forced-labour indicators but missing ordinary
  labour, recruitment, wage, housing, injury, tenancy, consumer-credit, or
  education-fee protections;
- giving unsafe referrals that expose a worker to retaliation or immigration
  harm;
- treating Facebook, WhatsApp, registry pages, or agency licenses as settled
  facts without verification date, archive, or source provenance.

Build a runnable seed promptset without mutating the canonical trafficking
promptset:

```bash
python scripts/build_benchmark_promptset.py --domain developing_country_worker_protections
```

The default output is gitignored under
`reports/benchmark/developing_country_worker_protections_promptset.json`.
The generated promptset includes a compact `_grounding` summary so diagnostic
runs can distinguish verified international anchors from pending country-law
sources.

Build the source-object curation queue:

```bash
python scripts/build_domain_grounding_queue.py --domain developing_country_worker_protections
```

The default output is gitignored under
`reports/benchmark/developing_country_worker_protections_grounding_queue.json`
with a companion Markdown review report at
`reports/benchmark/developing_country_worker_protections_grounding_queue.md`.
They list the prompt categories and jurisdictions that remain blocked for
comparable scoring until local law, regulator, complaint-channel, archive/date,
and practitioner-review source objects are added. For multi-jurisdiction
prompts, every extracted jurisdiction needs category-matching
`verified_local_law` coverage before the prompt is marked ready. Broad corridor
labels such as `Gulf` or `distant-water fleet` are tracked as scope-refinement
items, not as verified jurisdictions, until the concrete destination, flag,
port, forum, or regulator jurisdiction is identified.

Build the curator-facing source research plan from that queue:

```bash
python scripts/build_domain_source_research_plan.py --domain developing_country_worker_protections
```

The default output is gitignored under
`reports/benchmark/developing_country_worker_protections_source_research_plan.json`
with a companion Markdown handoff at
`reports/benchmark/developing_country_worker_protections_source_research_plan.md`.
This plan contains search queries, source-type requirements, rejection criteria,
and scope-refinement questions only. It does not verify law, fetch sources, or
promote any manifest row.

Build the compact source-coverage matrix from the research plan:

```bash
python scripts/build_domain_source_coverage_matrix.py --domain developing_country_worker_protections
```

The default output is gitignored under
`reports/benchmark/developing_country_worker_protections_source_coverage_matrix.json`
with a companion Markdown matrix at
`reports/benchmark/developing_country_worker_protections_source_coverage_matrix.md`.
The matrix groups source tasks by jurisdiction/category, separates pending
manifest rows from missing rows, and flags cells still blocked by broad corridor
or forum scope. It is triage metadata only; it does not verify law, fetch
sources, or promote rows.

Build the blank source-review intake packet from the plan:

```bash
python scripts/build_domain_source_review_packet.py --domain developing_country_worker_protections
```

The default output is gitignored under
`reports/benchmark/developing_country_worker_protections_source_review_packet.json`
with a companion Markdown summary at
`reports/benchmark/developing_country_worker_protections_source_review_packet.md`.
Every source candidate row starts as `needs_review` with blank candidate source
fields and `ready_for_manifest_promotion: false`, so curation cannot be
mistaken for verified local law before privacy and expert review.

Build the compact source-review sprint packet:

```bash
python scripts/build_domain_source_review_sprint.py --domain developing_country_worker_protections
```

The default output is gitignored under
`reports/benchmark/developing_country_worker_protections_source_review_sprint.json`
with a companion Markdown worklist at
`reports/benchmark/developing_country_worker_protections_source_review_sprint.md`.
The sprint packet separates scope-resolution tasks from non-scope-blocked
source-review rows and defers source rows that still depend on broad corridor or
forum scope. It is an operations worklist only; it does not fill review rows,
verify law, or promote rows.

Build the source-review progress ledger:

```bash
python scripts/build_domain_source_review_ledger.py --domain developing_country_worker_protections
```

The default output is gitignored under
`reports/benchmark/developing_country_worker_protections_source_review_ledger.json`
with a companion Markdown ledger at
`reports/benchmark/developing_country_worker_protections_source_review_ledger.md`.
The ledger summarizes source and scope rows as not started, in progress,
ready-claimed, accepted, or blocked by validation. It is a progress/status
artifact only; it does not fill review rows, verify law, or promote rows.

Validate a curator-filled review packet before proposing manifest updates:

```bash
python scripts/validate_domain_source_review_packet.py --domain developing_country_worker_protections
```

The default output is gitignored under
`reports/benchmark/developing_country_worker_protections_source_review_validation.json`
with a companion Markdown report at
`reports/benchmark/developing_country_worker_protections_source_review_validation.md`.
The validator never edits `grounding_sources.json`; it only emits
manifest-shaped proposed rows for source candidates that pass required
metadata, HTTPS URL, date, privacy, and expert-review gates.

Build a non-mutating grounding-manifest proposal from the validation report:

```bash
python scripts/build_domain_grounding_manifest_proposal.py --domain developing_country_worker_protections
```

The default output is gitignored under
`reports/benchmark/developing_country_worker_protections_grounding_manifest_proposal.json`
with a companion Markdown report at
`reports/benchmark/developing_country_worker_protections_grounding_manifest_proposal.md`.
It classifies validated source rows as either `promote_existing_source_row` or
`add_source_row`, detects conflicts such as replacing an already verified
anchor, and includes a preview manifest for manual curator review. It still
does not edit `grounding_sources.json`.

Build a compact end-to-end curation bundle and consistency report:

```bash
python scripts/build_domain_curation_bundle.py --domain developing_country_worker_protections
```

Add `--write-components` to regenerate the queue, research plan, review packet,
coverage matrix, source-review sprint, ledger, validation report, manifest
proposal, and bundle artifacts in one offline pass.
The default bundle is gitignored under
`reports/benchmark/developing_country_worker_protections_curation_bundle.json`
with a companion Markdown report at
`reports/benchmark/developing_country_worker_protections_curation_bundle.md`.
It proves local consistency across the generated curation chain, but it does not
fetch sources, verify law, edit `grounding_sources.json`, or mark the domain
ready for comparable scoring.
