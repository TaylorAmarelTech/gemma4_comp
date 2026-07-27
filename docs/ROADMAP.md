# DueCare Roadmap

Current as of 2026-07-27.

This is the strategic roadmap. The generated
[`DEFERRED_WORK.md`](DEFERRED_WORK.md) register is the authoritative operational
queue: it names the owner role, authorization boundary, prerequisites, ordered
actions, evidence, and acceptance gates for every unfinished item. If this
roadmap conflicts with that register, the register wins.

Historical and topic-specific plans remain as provenance under `docs/research/`
and `docs/_archive/`; they do not authorize model calls, publication, or the
promotion of candidate data.

## Current Stopping Point

- The source, public website, GitHub Pages documentation, active notebook
  sources, package build contract, and deterministic verification stack are
  maintained from `master`.
- The active Kaggle submission sources are exactly `01`, `02`, and `A-00`.
  The `03` and `04` benchmark surfaces are optional and are not prerequisites
  for repository closure.
- All 18 Python distributions build and clean-install under the release
  contract. No DueCare distribution is claimed as published to PyPI; choosing
  and publishing the first package remains an owner-authorized release action.
- The model/flywheel stack is deliberately cost-stopped. Four sentinels are
  present, five recurring Windows tasks are disabled, and a finite provider
  budget is required before any caller resumes.
- The exhaustive generation phase is complete. The isolated per-dimension
  judging lane remains partial: 47,813 of 708,471 panel cells are present and
  660,658 are still missing in the dated local coverage receipt. It is useful
  experimental evidence, not part of the default comparable board.
- The training scope remains deliberately red until the 75-row corridor
  workbook has human curation and adjudication, the quality audit is clean,
  and append-only provenance is refreshed.

The model-free release command is:

```powershell
$env:DUECARE_MAX_PLANNED_MODEL_CALLS = '0'
python scripts/validate_publication_readiness.py --scope core
```

## Near-Term Maintenance

Two local tasks are safe to pick up without model credits or external writes:

1. Extend shared attempt/token/cash enforcement to direct provider clients,
   one caller at a time, with fail-closed tests.
2. Remove legacy Ruff debt in behavior-preserving slices, never by weakening
   the configured rule set.

The exact work IDs are `direct-client-budget-migration` and
`legacy-ruff-cleanup` in [`DEFERRED_WORK.md`](DEFERRED_WORK.md). A maintainer
should finish each as its own reviewable change and retain the acceptance
evidence named there.

## Evidence And Dataset Priorities

New evidence should deepen validity rather than inflate surface count:

1. Complete the source-bound 75-row corridor-diversification workbook with two
   independent curators and native-language review where required.
2. Create a qualified human gold set and measure judge-human agreement before
   using model-judge scores as a stronger validity claim.
3. After an explicit budget approval, run a small frozen smoke matrix with
   immutable model IDs, prompts, rubric, harness, decoding, and cash/token caps.
   Kimi K3 and Meta Muse Spark 1.1 are required comparison lanes; record an
   inaccessible provider lane rather than silently substituting another model.
4. Continue the isolated per-dimension lane only from its resumable coverage
   receipt; never merge its incomplete metrics into the default board.
5. Version datasets append-only. Preserve source rights, checksums, lineage
   families, quarantine outcomes, and split-isolation evidence with each
   release.

No extra Kaggle notebook is needed merely to make the project look complete.
Publish or rerun a notebook only when it carries a distinct, reviewable evidence
artifact that an existing active surface cannot express.

## Product And Integration Priorities

After release disposition and evidence gates are resolved, the strongest
product extensions are:

- a stable domain-pack and harness-plugin contract with one minimal reference
  implementation;
- measured on-device behavior on a frozen Gemma revision, including latency,
  memory, quantization, and safety deltas;
- a worker-facing multimodal review path that keeps raw documents local and
  exposes provenance and trust boundaries;
- bounded integration recipes for NGO, regulator, platform, and research
  deployments; and
- a versioned, curator-approved knowledge-refresh workflow that stages changes
  but never publishes autonomously.

These are future product programs, not claims about the current release.

## Community And Research Opportunities

- Calibrate the benchmark with anti-trafficking and migrant-rights specialists.
- Publish a citable dataset or package only after the owner selects a release
  disposition, license, support boundary, and exact tagged artifact.
- Use the optional Kaggle Community Benchmark surface only if the account owner
  wants to host a maintained benchmark and can commit to moderation and version
  governance.
- Explore cross-domain ports as separate, source-gated evidence lanes. Do not
  reinterpret a synthetic seed as jurisdictional coverage.
- Retain negative results and no-lift findings; they are part of the scientific
  record, not cleanup candidates.

## Long-Term Maintenance Rules

- Stable behavior belongs in code, tests, and versioned knowledge objects.
  Volatile rules, contacts, fees, office names, and advisories require dated
  source review rather than memorization in training targets.
- Entity intelligence remains propose-only and curator-reviewed, separate from
  worker-facing decisions and the GREP/RAG knowledge layer.
- Every autonomous or scheduled path stays fail-closed on privacy, budget,
  provenance, and publication authority.
- Claims stay attached to exact artifacts and dates. A passing core gate does
  not make the intentionally separate training lane green.

## How To Update This Roadmap

Change the canonical JSON register first when an unfinished item, status,
boundary, or acceptance test changes:

```powershell
python scripts/build_deferred_work_register.py
python scripts/validate_deferred_work.py
```

Then update this roadmap only when the strategic direction changes. Completed
items leave the active register only after their acceptance artifacts exist;
the commit history preserves the prior state.
