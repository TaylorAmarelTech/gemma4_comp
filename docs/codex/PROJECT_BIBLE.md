# DueCare project bible for AI pickup

> Last refreshed: 2026-07-01.
> Audience: Claude Code, Codex, and other coding agents picking up long-running
> DueCare improvement work after a dense session.

## One-sentence mission

DueCare is a privacy-first LLM safety and worker-protection project: it tests
and improves model behavior on migrant-worker exploitation, trafficking,
cross-border recruitment, labor-law, evidence-review, and human-rights failure
modes where ordinary LLMs miss rules, jurisdictions, informal records, and
life-cycle risk.

## Read first

1. `AGENTS.md` - active repo rules, validation commands, and safety claims.
2. `CLAUDE.md` - Claude Code index and project memory map.
3. `docs/codex/00_do_not_break.md` - recording-critical contract.
4. `docs/codex/00_execution_order.md` - historical goal order and dependencies.
5. `docs/FILE_PURPOSE_GUIDE.md` and `docs/REPO_LAYOUT.md` - update these when
   adding public surfaces or long-lived docs outside an existing indexed area.

Claude Code also auto-loads `.claude/rules/05_project_bible_pickup.md`, a
small hidden pointer back to this file.

Do not treat older archived notebook-era files as active blockers unless Taylor
explicitly asks to restore them.

## Current operating state

Verified locally on 2026-07-01 with:

```powershell
python scripts\autonomous_engine.py --status
```

Snapshot:

- Autonomous benchmark engine process: not alive.
- Pause sentinel: `reports/autonomous_engine.stop` exists.
- Lock file: `reports/autonomous_engine.lock` exists but is stale when
  `python scripts\autonomous_engine.py --status` reports `lock.state: "stale"`.
  The saved preflight snapshot may also report
  `latest_preflight.saved_lock_state.state: "stale"`; that is handoff evidence,
  not proof that the engine is currently running.
- Current queue job: index 12 of 41, `gemma4:31b`, `n=10000`, full prompt set.
- Full prompt set: `reports/benchmark/full_promptset.json`, 76,442 prompts.
- Candidate dimension source: 201 rows in
  `configs/duecare/benchmarks/research_spider/dimension_candidates.jsonl`.
- Candidate-dimension review gate: `validated_zero_proposals`.
- Candidate-dimension mass grading: not active and not ready.
- Latest saved preflight: `state_only`, ready `false`, blocker
  `stop_sentinel_present`, Ollama not checked.

This means the repo is safe for code/docs improvement work, but the long-running
judging loop is intentionally paused. Do not remove the stop sentinel, start the
engine, or call Ollama unless Taylor explicitly asks for that action in the
current session.

## Recent improvement theme

The recent work tightened the boundary between "candidate ideas found by
research" and "active rubric dimensions used for mass grading." The system must
fail closed until a privacy-safe review packet and its validation report are
fresh, well-formed, and tied to the exact source artifact by row count and hash.

High-signal files in this thread:

- `scripts/artifact_path_policy.py` - standardizes handoff artifact paths so
  in-repo paths stay repo-relative while hidden or external paths are redacted
  to `external/<name>`.
- `scripts/build_dimension_candidate_review_packet.py` - builds the
  privacy-safe candidate-dimension review packet.
- `scripts/validate_dimension_candidate_review_packet.py` - validates review
  packets before any promotion proposal can be trusted.
- `scripts/autonomous_engine.py` - status, preflight, pause-safe engine wrapper,
  candidate-dimension sweep estimates, and review-gate blockers.
- `tests/test_build_dimension_candidate_review_packet.py` and
  `tests/test_autonomous_engine.py` - focused regression coverage for the
  review/promotion gate.

## Current global-protections pickup

The sister-project/global-protections work is still offline planning. It is not
public benchmark evidence, not training data, not worker-facing guidance, and
not ready for comparable model scoring.

Current validated shape on 2026-07-01:

- Regulatory miss catalog: 11 patterns, 10 candidate patterns, 0 scaffold
  operations, comparable scoring blocked.
- Global-protections project plan: 11 declared candidate patterns and 11
  regulatory candidates found across the source-gated planning artifacts.
- Jurisdiction-pack matrix: 8 pilot jurisdiction scopes, 5 queued jurisdiction
  scopes, 3 domain lenses, 24 active pack cells, and 120 source-object slots.
  Queued scopes are explicit backlog only and must stay blocked from pack-cell
  generation, prompt generation, and comparable scoring.
- Source-channel matrix/review: 70 source-channel rows, 14 legal-claim-anchor
  rows, 7 informal-publication lead rows, and 0 rows ready for manifest
  promotion.
- Legal-claim anchors remain limited to
  `official_gazette_or_law_portal` and
  `labour_or_migration_ministry_notice`. Social posts, forums, scanned
  circulars, NGO pages, and media reports can create leads or source-gap
  evidence, but cannot stand alone as verified legal claims.
- Next-actions/curator handoff: 34 next actions, 24 immediate curator sprint
  items, 10 blocked-later items, 5 execution phases, and all public/scoring/use
  flags false.

High-signal files for this branch:

- `configs/duecare/benchmarks/regulatory_miss_patterns.json` - propose-only
  regulatory miss pattern catalog.
- `configs/duecare/benchmarks/sister_projects/global_protections_regulatory_benchmark.json`
  - sister-project charter and candidate pattern references.
- `configs/duecare/benchmarks/sister_projects/global_protections_jurisdiction_packs.json`
  - pilot and queued jurisdiction scope planning.
- `scripts/build_global_protections_jurisdiction_pack_matrix.py` and
  `scripts/validate_global_protections_jurisdiction_pack_matrix.py` - active
  pilot-cell matrix plus queued-scope blockers.
- `scripts/validate_global_protections_saved_artifacts.py` - aggregate saved
  artifact validator for the global-protections component chain.
- `tests/test_build_global_protections_*.py`,
  `tests/test_validate_global_protections_*.py`, and
  `tests/test_build_regulatory_miss_pattern_plan.py` - focused regression
  coverage for this branch.

The saved-artifact aggregate validator keeps artifact-path mismatch diagnostics
privacy-safe: expected repo-relative keys stay visible, while unknown extra
keys and invalid/path-like actual values are reported as `custom_or_invalid`
instead of copying local paths or curator-supplied strings.
Its jurisdiction-pack, domain-lens, and legal-anchor channel mismatch
diagnostics follow the same rule: known enum IDs remain visible, while
unrecognized copied IDs are summarized as `custom_or_invalid` in JSON and
Markdown.

Focused validation for this branch:

```powershell
python scripts\validate_global_protections_saved_artifacts.py
python -m pytest tests -q -k "global_protections or regulatory_miss_pattern"
```

Current evidence from the latest local run:

- `python scripts\validate_global_protections_saved_artifacts.py`:
  `valid=true`, `failed_artifacts=0/13`, `failed_checks=0/157`,
  `suite_checks=0/21`, `phase_coverage=next:5/34,curator:5/34`,
  `phase_mismatches=0`, `legal_anchor_mismatches=0`,
  `readiness_blocker_mismatches=0`,
  `ready_for_comparable_scoring=false`.
- `python -m pytest tests -q -k "global_protections or regulatory_miss_pattern or project_bible"`:
  `377 passed, 1 skipped, 2090 deselected`.
- `python scripts\validate_project_bible_pickup.py`:
  `38 checks, 0 findings`, with the global-protections saved-artifact
  snapshot accepted only when the aggregate report is valid, covers all 13
  artifacts, reports all 13 artifacts and Markdown handoffs valid/readable,
  reports zero failed artifacts, missing artifacts, unsafe Markdown reports,
  artifact-path mismatches, failed checks, and failed suite checks, preserves
  the current check-count floors of `total_check_count>=157` and
  `suite_check_count>=21`, has both next-action and curator phase coverage at
  `5/34`, and reports zero phase-coverage, legal-anchor-channel, and
  readiness-blocker mismatches.
- `python scripts\validate_sister_project_planning.py`:
  `27 checks, 0 findings`, with the direct snapshot reporting
  `source_admission_missing=0` and
  `privacy_issues=project:0,packs:0,grounding:0`. Any nonzero value in those
  fields is an aggregate-only safety signal to inspect before continuing.

## Non-negotiable safety rules

- Never commit raw PII, real worker contact details, private case files,
  unredacted hidden logs, API keys, Kaggle tokens, or raw production data.
- Do not hardcode volatile hotlines, wage caps, fee caps, office names, or legal
  claims into model outputs or training data unless they are versioned knowledge
  objects.
- Candidate dimensions from the research spider are propose-only until the
  packet builder, validator, and human review path say otherwise.
- Artifact paths in handoff JSON/Markdown must not expose local hidden paths.
- A broad test claim requires the actual broad test run. If only focused tests
  ran, say that.

## Current loop priorities

When asked to "continue improving," prefer these loops before broad rewrites:

1. Strengthen validators that sit between generated research artifacts and
   active model/rubric behavior.
2. Add aggregate-only diagnostics that tell the next agent what failed without
   copying row text, case text, or hidden path contents.
3. Keep handoff docs in sync with the actual runtime state and validation
   evidence.
4. Expand sister-project/domain work only as offline, privacy-safe benchmark
   planning until sources and curation gates exist.
5. Avoid changing Kaggle kernels or workbench UI contracts unless the request is
   specifically about those surfaces.

## Useful commands

Copy-paste long-loop continuation prompt:

```text
docs/codex/goal_commands/13_project_bible_continuation.md
```

Focused review-gate tests:

```powershell
python -m pytest tests\test_autonomous_engine.py tests\test_build_dimension_candidate_review_packet.py -q
```

Project-bible pickup validator:

```powershell
python scripts\validate_project_bible_pickup.py
```

Copied handoff trees must include `scripts/validate_project_bible_pickup.py`
and `scripts/validate_global_protections_saved_artifacts.py`; missing either
validator script, or the global validator's direct helper validators/builders,
fails the required-file pickup check. The pickup validator also parses its own,
the global validator's, the sister-project validator's, and the autonomous engine's
direct local imports so this helper list cannot silently drift. Copied trees must
also include autonomous engine helper modules such as `scripts/_atomic.py`. This validator is read-only. It prints
pass/fail wiring checks plus an
aggregate snapshot of pause state, lock state, saved preflight scope,
Ollama-check status, current queue job, candidate-dimension readiness, and any
hidden Claude handoff artifact counts such as open-risk count and recent-edit
count. Its Claude handoff line includes aggregate open-risk severity counts
and the high/critical blocking-risk count, and validates the open_risks shape
without copying risk text. Its global-protections line includes aggregate mismatch counts as
`mismatches=phase:<n> legal_anchor:<n> readiness:<n>`. A clean pickup requires
a state-only preflight with ready `false`,
`stop_sentinel_present` still listed as a blocker, and no ignored blockers. If
the hidden handoff artifact is present, it must parse as a JSON object, use the
`structured-handoff` artifact type, and must not report failed checks; parse failures are reported without copying private path details. failed-check presence is treated the same way.
Use `--root <path>` to validate a copied checkout or handoff tree while still
keeping the status check read-only. Use `--status-json <path>` with a saved
`python scripts\autonomous_engine.py --status` payload when the pickup tree
should be checked without probing the local engine state; do not pass
`reports/autonomous_engine_preflight.json`, which has a different shape. Use
`--global-protections-report-json <path>` with a saved
`reports/benchmark/global_protections_saved_artifacts_validation.json` report,
a full JSON report emitted by
`python scripts\validate_global_protections_saved_artifacts.py --json`, or a
summary JSON emitted by
`python scripts\validate_global_protections_saved_artifacts.py --validate`,
when a copied tree should be checked without reading local `reports/benchmark`
artifacts. Global-protections pickup remains fail-closed unless the report
includes the full artifact/Markdown/check-count coverage fields, zero
phase-coverage mismatches, zero legal-anchor-channel mismatches, and zero
readiness-blocker mismatches.
Hidden handoff string fields use allowlisted labels only; custom labels are
reported as `custom_or_invalid`, and unknown hidden handoff labels fail closed
by field name instead of copied hidden-state text. The handoff summary reports
timestamp presence, timestamp validity, and `validated_after_handoff=<bool>` so stale
open-risk counts can be read against current validator evidence without editing
hidden session logs. A clean handoff requires the hidden timestamp to be valid
and not newer than the validation run.
High or critical hidden open-risk severities fail closed through aggregate
counts; unknown hidden open-risk severities fail closed as `custom_or_invalid`.
Low and medium historical risks stay visible but do not block the pickup
validator by themselves. A malformed `open_risks` value also fails closed as a
shape problem.
Saved status string fields use the same pattern: known status labels stay
visible, unsafe model/path-like values and custom blocker or mismatch labels are
reported as `custom_or_invalid`, and unknown status labels fail closed by field
name while keeping the useful counts and booleans needed for pickup decisions.

Sister-project planning validator:

```powershell
python scripts\validate_sister_project_planning.py
```

This validator is read-only and aggregate-only. It checks that the
developing-country worker-protections seed and global-protections charter stay
propose-only, source-gated, privacy-gated, and blocked from public scoring or
training use or worker-facing use. It also checks cross-artifact integrity
between the charter, jurisdiction packs, grounding scaffold, and prompt seeds,
including duplicate IDs within each planning namespace and whether every
scheme-prompt category has a pending or verified grounding source slot plus a
declared pilot or queued jurisdiction scope for every local source placeholder.
The source admission rules must preserve the low-documentation safety boundary:
local-law claims need dated source objects, international anchors cannot
substitute for local law, public complaint lists and private identifiers are
rejected, informal social-channel notices remain source leads until reviewed,
and expert review is required before public claims or comparable scoring.
First-build phases and scheme prompts must carry explicit blocked flags, with
public scoring, training use, and worker-facing use all set to `false`.
Scheme prompts must still map to declared candidate pattern IDs and remain
explicit unresolved source-gap rows.
Its JSON report omits raw scheme-prompt IDs, prompt text, source URLs, and
custom issue values; failed checks report rule IDs plus aggregate counts instead
of copying curator-provided identifiers. Source status summaries keep only
known enum labels and group anything else under `invalid_or_unknown`; canonical
project/domain labels stay visible, while copied custom labels are reported as
`custom_or_invalid`; copied phase IDs and other issue values are summarized by
counts. Project-charter, jurisdiction-pack, and grounding metadata privacy
scans report only aggregate issue counts for email-like, phone-like, URL-like,
local-path, and long-digit patterns. Prompt parse-error details are reduced to
safe line numbers and known safe error labels; custom error text or custom error labels
are reported as `invalid_or_unknown` instead of copied into the report.
Use `--project-config`,
`--jurisdiction-packs`, `--grounding-sources`, and `--scheme-prompts` to
validate copied or curator-edited planning artifacts before replacing the
defaults.

Public surface and package collection gates:

```powershell
python scripts\validate_public_surface.py
python -m pytest packages --collect-only -q
```

Kaggle/static-page gates when relevant:

```powershell
python scripts\validate_main_kaggle_kernels.py
py -3.12 scripts\validate_kaggle_page_sources.py
```

Paused engine status, without launching Ollama:

```powershell
python scripts\autonomous_engine.py --status
```

State-only preflight, without launching Ollama:

```powershell
python scripts\autonomous_engine.py --preflight --no-ollama-check
```

## Pickup checklist

Before editing:

1. Run `git status --short` and assume unrelated dirty files belong to Taylor or
   another agent.
2. Read the nearest `AGENTS.md` for the area being touched.
3. Inspect the relevant tests before changing behavior.
4. Keep changes tightly scoped to the requested improvement loop.

Before claiming completion:

1. Run the smallest relevant focused tests.
2. Run public/documentation validators for docs or public-surface changes.
3. Report exact validation coverage and any environment-specific blockers.
4. Leave the autonomous engine paused unless Taylor explicitly asked to resume
   it.
