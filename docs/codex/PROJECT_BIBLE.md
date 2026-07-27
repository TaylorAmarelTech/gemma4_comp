# DueCare project bible for AI pickup

> Last refreshed: 2026-07-26.
> Audience: Claude Code, Codex, Fable 5-style agents, and other coding agents
> picking up long-running DueCare improvement work after a dense session.

## One-sentence mission

DueCare is a privacy-first LLM safety and worker-protection project: it tests
and improves model behavior on migrant-worker exploitation, trafficking,
cross-border recruitment, labor-law, evidence-review, and human-rights failure
modes where ordinary LLMs miss rules, jurisdictions, informal records, and
life-cycle risk.

## Read first

1. `AGENTS.md` - active repo rules, validation commands, and safety claims.
2. `docs/MAINTAINER_HANDOFF.md` - fresh-shell operations, boundaries, access,
   recovery, and acceptance for a human successor.
3. `docs/PROJECT_TRANSITION_PLAN.md` - dated 2026-07-26 through 2026-08-25
   closeout, rehearsal, release decision, and maintenance-mode fallback.
4. `docs/PUBLICATION_READINESS.md` - canonical release/evidence boundary and
   prioritized model/data work.
5. `CLAUDE.md` - Claude Code index and project memory map.
6. `docs/codex/00_do_not_break.md` - recording-critical contract.
7. `docs/codex/00_execution_order.md` - historical goal order and dependencies.
8. `docs/FILE_PURPOSE_GUIDE.md` and `docs/REPO_LAYOUT.md` - update these when
   adding public surfaces or long-lived docs outside an existing indexed area.

Claude Code also auto-loads `.claude/rules/05_project_bible_pickup.md`, a
small hidden pointer back to this file. That hidden rule also names `Plans.md`
as a compatibility bridge for older handoffs.
The root `PROJECT_BIBLE.md` is the repo-root discovery bridge for Claude Code,
Codex, Fable 5-style agents, and other tools that look for a handoff file
before opening deeper docs.
The root `Plans.md` file is only a compatibility bridge for older hidden Claude
handoffs that mention `Plans.md`; it points back to the Project Bible and
pause-safe loop priorities, not to a separate planning source.

Do not treat older archived notebook-era files as active blockers unless Taylor
explicitly asks to restore them.

## Current operating state

> **Re-verified 2026-07-26 -- read this box before trusting the 2026-07-14 snapshot below.**
>
> - **Branch integration is still open.** Root `AGENTS.md` names `master` as the
>   active branch, while this workspace is on
>   `codex/full-flywheel-training-20260714` with mixed uncommitted work. Scope
>   and commit each change intentionally, integrate it onto the exact release
>   revision, and rerun all release gates there; do not reset the tree.
> - **Canonical stopping point:** start with
>   `docs/PUBLICATION_READINESS.md`. Its model-free core lane passed 8/8 checks
>   on 2026-07-26; the separate training lane intentionally remains red on five
>   dense generic-corridor typologies, with a privacy-safe 25-task / 75-row
>   curation plan. No new model or adapter-improvement claim is ready.
> - **Succession is now an explicit 30-day workstream.** Use
>   `docs/MAINTAINER_HANDOFF.md` for operational pickup and
>   `docs/PROJECT_TRANSITION_PLAN.md` for the 2026-08-25 target. The read-only
>   `validate_publication_readiness.py --scope handoff` composes document/link/
>   privacy checks with live pickup consistency. It passed 2/2 gates on
>   2026-07-26 (16/16 succession checks and the 65-check pickup validator with
>   zero findings); it never authorizes model calls or engine resume.
> - **Generation is COMPLETE.** `reports/rich_lift/panel_perdim.coverage.json` reports
>   `response_cells 236,157 / 236,157, 0 missing`. Every Gemma response for 78,719 prompts x 3 arms
>   is on disk. Only judge calls remain: `panel_cells 47,813 / 708,471` (6.7%),
>   `dimension_outputs 239,065 / 3,542,355`. The 2026-07-14 line below saying `0 / 708,471` is
>   superseded. **Consequence: model-free analysis over the full response set is always available,
>   even while Ollama is capped.**
> - **The last verified engine block was an Ollama WEEKLY usage cap, not a code fault.** The
>   generation probe returned HTTP 429 "reached your weekly usage limit". `/api/tags` can still
>   return 200 while capped, so reachability is NOT a quota test; explicit `-Run` rechecks provider
>   readiness with a real `POST /api/chat` before launch.
> - **Read engine liveness and successful progress separately.** The coverage manifest is the
>   aggregate-only runner heartbeat, including phase/failure counts even when no judge call can
>   complete. The SQLite sidecar is successful component progress; its mtime remained frozen at
>   2026-07-21 00:25 through 2026-07-26. The flywheel manager now watches both signals, so a live
>   provider-failure pass is not force-restarted merely because no panel row was appended. Nothing
>   is lost: the sweep is resumable and the seeded shuffle keeps any completed prefix unbiased.
> - **The engine is now cleanly PAUSED and will NOT auto-resume.** `reports/autonomous_engine.stop`
>   was created 2026-07-24 21:28; the engine ran to `2026-07-25T05:28Z` and has been stopped since.
>   `python scripts/autonomous_engine.py --status` reports `paused=true` with a stale lock (pid
>   40920). Scheduled watchdog ticks now exit 0 before preflight while the sentinel exists, so they
>   neither call Ollama nor rewrite paused readiness evidence. **Resuming requires an explicit
>   `scripts/autonomous_engine.ps1 -Run`** -- Taylor's call; the wrapper rechecks provider readiness
>   and removes the sentinel only after launch preflight succeeds. A state-only, no-Ollama preflight
>   was refreshed on 2026-07-26; `validate_project_bible_pickup.py` reports 65 checks, 0 findings.
> - **Full suite re-verified green on 2026-07-26:** the combined `packages tests`
>   run passed **4,601 tests, 4 skipped** before final branch integration. The
>   three pandas Styler constant-range warnings were then fixed and a focused
>   43-test package run passed with `RuntimeWarning` promoted to an error. Rerun
>   the combined command on the integrated revision. This supersedes the earlier separate counts and the
>   `4147 passed, 12 skipped` line below. Two tests had been failing silently for days and were fixed
>   (`test_next_notebooks_inherit_reusable_contracts_without_redeclaring_lists` broke when the
>   headless A-30 GPU trainer landed at the Kaggle root before being archived;
>   `test_no_python_scripts_live_in_repository_root` broke when
>   `launch.py` landed). Do not claim a full pass without rerunning both commands.

Verified locally on 2026-07-14 with:

```powershell
python scripts\autonomous_engine.py --status
```

Snapshot:

- Autonomous benchmark engine process: alive, with a live lock and no pause sentinel.
- Current queue job: index 13 of 49, `gemma4:31b`, `n=all`, full prompt set,
  grader `perdim`. The queue counts are coherent: `done == cursor == 12`, and
  `current_job.index == cursor + 1`.
- Full prompt set: `reports/benchmark/full_promptset.json`, 78,719 prompts.
- Active per-dimension scope: 236,157 response cells, 708,471 panel cells,
  and up to 3,542,355 independent A-E judge calls (five per panel cell).
  Pairwise preference grading is disabled for this exhaustive job so resources
  remain focused on completing every calibrated component.
- Exact closure audit at 2026-07-14T15:17:38Z: Gemma has 120,185 / 236,157
  valid response cells, 0 / 708,471 complete panel cells, and 0 / 3,542,355
  A-E outputs consolidated into valid panel cells. The aggregate-only live
  artifact is `reports/rich_lift/panel_perdim.coverage.json`.
- Required `n=all` / `full` / `perdim` jobs are completion-gated: generation
  and judging failures produce an incomplete retry outcome, never cursor
  advancement; required jobs are exempt from the legacy three-failure skip.
  Judging is restricted to the active model and exact selected prompt texts.
- Individual successful A-E calls are transactionally checkpointed in the
  gitignored `panel_perdim.jsonl.components.sqlite3` sidecar by exact request
  hash. A later repair pass calls only missing/invalid dimensions, and panel
  rows carry `grade_input_sha256` so stale prompt/response grades cannot close
  coverage.
- Candidate dimension source: 201 rows in
  `configs/duecare/benchmarks/research_spider/dimension_candidates.jsonl`.
- Candidate-dimension review gate: `validated_zero_proposals`.
- Candidate-dimension mass grading: not active and not ready.
- Latest saved manual preflight: launch-scoped, Ollama checked, ready `false`
  only because the verified live engine lock is present; dimension-review
  status remains `validated_zero_proposals`.
- Active loop scope: `active_loop_scope.rubric_version` is `v1`,
  `opt_in_rubric_versions_excluded` is `["v2"]`, and
  `rubric_version_mixing_allowed` is `false`; `active_loop_scope.harness_version`
  is `h1`, `opt_in_harness_versions_excluded` is `["h2"]`, and
  `harness_version_mixing_allowed` is `false`. The v2 rubric and h2 harness are
  opt-in research evidence only and must not be mixed into active v1/h1 board
  runs.

The long-running loop was intentionally active when this 2026-07-14 snapshot
was recorded. It is now intentionally paused as described in the re-verification
box above. Do not resume, reorder, or reset it unless Taylor explicitly asks in
the current session; the pause-safe watchdog behavior is part of the current
contract.

Paused-mode control contract: paused status queue counts must be coherent; `lock.state: "stale"` or `"absent"` is
expected rather than a live process, and the saved diagnostic reports
`latest_preflight.saved_lock_state.state: "stale"`, `state_only`, and Ollama not checked. Those are the current pause-safe diagnostics above.

## Recent improvement theme

The recent work tightened the boundary between "candidate ideas found by
research" and "active rubric dimensions used for mass grading." The system must
fail closed until a privacy-safe review packet and its validation report are
fresh, well-formed, and tied to the exact source artifact by row count and hash.

High-signal files in this thread:

- `scripts/artifact_path_policy.py` - standardizes handoff artifact paths so
  in-repo paths stay repo-relative while hidden or external paths are redacted
  to safe `external/<name>` labels; private-looking repo-relative segments and
  private-looking or malformed external names collapse to
  `external/custom_or_invalid`.
- `scripts/build_dimension_candidate_review_packet.py` - builds the
  privacy-safe candidate-dimension review packet; source-candidate privacy
  scans reject email-like, phone-like, local-path-like, and 8+ digit copied
  case-like values before a blank review packet can be trusted.
- `scripts/validate_dimension_candidate_review_packet.py` - validates review
  packets before any promotion proposal can be trusted, including 8+ digit
  copied case-like values in curator-filled promotion rows.
- `scripts/build_domain_source_review_packet.py` and
  `scripts/validate_domain_source_review_packet.py` - keep domain-source intake
  and manifest-proposal validation propose-only; source-review privacy scans
  reject email-like, phone-like, local-path-like, and 8+ digit copied case-like
  values before any source can become a grounding manifest proposal.
- `scripts/autonomous_engine.py` - status, preflight, pause-safe engine wrapper,
  exact-closure manifest reporting, non-skippable required jobs, Gemma-first
  model sequencing, candidate-dimension sweep estimates, and review-gate
  blockers. After Gemma, gpt-oss, GLM, and DeepSeek each prove exact closure,
  it writes the pause sentinel before optional legacy/breadth work.
- `tests/test_build_dimension_candidate_review_packet.py`,
  `tests/test_build_domain_source_review_packet.py`,
  `tests/test_validate_domain_source_review_packet.py`,
  `tests/test_build_domain_grounding_manifest_proposal.py`, and
  `tests/test_autonomous_engine.py` - focused regression coverage for the
  review/promotion gates.
- `scripts/multi_judge.py` and `scripts/rich_harness_lift.py` - keep the
  default board rubric at v1, while the opt-in `--rubric-version v2` path uses
  separate panel/report artifacts, reports F as an over-refusal channel outside
  the 0-100 total, and applies the deterministic citation gate. Never mix v2
  rows into v1 leaderboard or Project Bible evidence.
  The `--require-complete` runner mode writes an atomic aggregate-only coverage
  manifest and exits 3 while any selected response or cross-family judge cell
  is missing; per-dimension subgrades use a report-local SQLite sidecar that
  stores hashes and numeric values only, never prompt or response text.
- `scripts/benchmark_leaderboard.py` - the public board is the default comparable `v1`/`h1` surface over adversarial prompts only; tagged opt-in `rubric`, `harness`, or benign-control `intent` rows are ignored by leaderboard rows, judge lists, stats, breakdowns, latency, and contract metrics. Malformed explicit rubric/harness/intent tags fail closed instead of defaulting to v1/h1 adversarial board rows.
  Public artifact keys also pass a
  benchmark-ID guard so email-like values, whitespace, path traversal, and
  8+ digit long numeric case-like identifiers or markup-like strings cannot leak from malformed scored rows into JSON or
  Markdown output; copied URL-scheme strings such as `file:`, `http:`,
  `ftp:`, `s3:`, and `mailto:` are rejected. Model and judge IDs are sanitized
  separately so normal 8-digit release-date model tags can still rank while
  copied case-like model labels fail closed. Category/corridor/difficulty breakdown labels are sanitized
  separately so legitimate labels like `India->Saudi Arabia` survive while
  copied private strings collapse to `custom_or_invalid`. The returned board is
  also sanitized to strict JSON so helper `NaN` or `Infinity` values become null
  before the site artifact is written, and stats/contract metric blocks expose
  only allowlisted numeric fields so helper debug strings cannot enter the
  public JSON. The public `generated` and `git_sha` provenance fields are also
  sanitized before JSON or Markdown rendering; `generated` must be a timezone-aware ISO timestamp, and caller-supplied private paths, contact strings, or non-timestamp labels collapse to safe placeholders.
  Pairwise, latency, and contract metrics require safe prompt, judge when present, and arm provenance before they can affect the public board.
- `tests/test_rubric_v2.py` - compact opt-in rubric-v2 regression coverage for
  the grounded-refusal cap, F channel, citation gate, isolated panel/report
  files, v1 byte compatibility, and aggregation version filtering.
- `tests/test_harness_v2.py` - compact opt-in harness-h2 regression coverage
  for the refusal-collapse fix behind `--harness-version h2`; h2 responses are
  NOT comparable with h1, reuse only the baseline arm, and write separate
  results/panel/report artifacts.
- Intent-aware benchmark split (opt-in): `scripts/rich_harness_lift.py` now
  keeps the headline under-refusal lift over adversarial prompts only, while
  `configs/duecare/benchmarks/benign_control_prompts.json` supplies 16
  synthetic legitimate worker questions for a separate over-refusal block.
  The split is enabled with
  `--benign-control configs/duecare/benchmarks/benign_control_prompts.json`.
  The over-refusal block uses rubric v2's F channel when available, stays
  separate from the 0-100 safety lift, and is never merged into active board
  evidence, public leaderboard rows, or autonomous-loop evidence.
  `tests/test_intent_split.py` covers benign intent propagation,
  adversarial-only lift aggregation, v1 score-proxy fallback, report rendering,
  fail-closed benign-control loading, and the committed control-set shape.
- Offline re-grade sizing: `rich_harness_lift.py --plan` prints the incremental
  generation, judge, and pairwise-call estimate before any opt-in rubric v2,
  harness h2, or benign-control re-grade. Its output must state `NO model was called`;
  `tests/test_plan.py` covers reuse accounting, on-disk credit,
  self-family judge exclusion, opt-in scope labeling, pairwise/skip-judge
  counts, unknown-version rejection, and the no-write/no-model-call invariant.

## Current training and fine-tuning contract

The harness can generate candidate SFT and preference data, but harness output
is not automatically approved training data. The executable boundary is
`packages/duecare-llm-chat/src/duecare/chat/training_contract.py`, and the
operator guide is `docs/training_and_finetuning.md`.

- SFT rows carry source references, prompt and lineage IDs, row hashes,
  reasoning-policy labels, provenance/licensing metadata, and explicit
  `safe_to_train` evidence. Preference rows carry the same contract plus
  `chosen` and `rejected` outputs.
- Split isolation is lineage-level, not just row-level: all variations of one
  seed stay in one split. Both held-out prompt hashes and held-out lineage IDs
  are required, and either kind of overlap blocks training.
- Hidden chain-of-thought is never collected or approved. Allowed targets are
  final answers, concise visible rationales, citations/source references, and
  structured reasoning fields that were intentionally exposed for training.
- `scripts/training_engine.py` is the canonical local orchestrator. It requires
  a clean quality audit before train, evaluate, or register; records immutable
  model revisions; and does not report completion unless requested stages
  actually finish. `scripts/train_lift_distill.py` implements the resumable
  SFT-to-DPO path and treats missing DPO support as fatal unless DPO was
  explicitly not requested.
- `kaggle/A-00-omni-experiment-workbench` is the active portable notebook path.
  It exports manifest-bound SFT/DPO train, validation, and test artifacts,
  verifies every declared hash before upload/training, and can emit a
  resumable Unsloth trainer for the official Gemma 4 E2B/E4B checkpoints or a
  custom remote model with an immutable revision.
- `scripts/four_arm_eval.py` checks adapter base-model identity and revision
  before the stock/trained x harness-off/on comparison. GGUF export, when
  deliberately enabled later, is for llama.cpp-compatible runtimes; LiteRT is
  a separate deployment path.
- `scripts/finetune_unsloth.py`, the old package trainer, and notebook 530 are
  legacy-disabled or plan-only surfaces. Do not bypass the strict engine or
  A-00 handoff through them.
- No adapter, merged checkpoint, Generative Pre-trained Transformer Generated
  Unified Format file, or other trained weights are currently published.
  Future generated candidates remain subject to the clean audit, curator,
  privacy, provenance, and held-out-contamination gates above.
- Public Kaggle training-data publication completed on 2026-07-15 after exact
  manifest-bound approval. The large multiperspective corpus has 25,600
  supervised fine-tuning train rows,
  25,600 preference train rows, and 2,048 rows in each held-out split
  (`candidate-manifest` SHA-256
  `7cc7573e34aa9300abf9858fb72e47d23964e4b0bc1cf64535b8b17250230481`).
  Its public release-manifest SHA-256 is
  `ea644df422d9e8c43003805f49a227d441e3a952d6deb3ea3e6fb3b6b579211d`.
  The measured-response corpus has 791 supervised/preference pairs split
  649/66/76 plus 1,582 reward rows (`candidate-manifest` SHA-256
  `7fc563c8d583fd7abd5f2baf95fda384069a6f82a61367abd530984eb79a5490`).
  Its public release-manifest SHA-256 is
  `56fa69c19990c524002e4f91b833faef58648a66d87729a8f4c61dd56722b74b`.
  Both Kaggle datasets and nine central-processing-unit notebooks are public;
  downloaded remote outputs verify the promised charts, tables, summaries,
  and reports. The dataset IDs are
  `taylorsamarel/duecare-multiperspective-finetuning-corpus` and
  `taylorsamarel/duecare-measured-response-training-corpus`; both have
  `safe_to_publish=true` for their stated releases. No graphics-processing-unit
  training was performed, and the
  measured-response contamination ledger prohibits reusing its source
  benchmark as independent improvement evidence.

## Current global-protections pickup

The sister-project/global-protections work is still offline planning. It is not
public benchmark evidence, not training data, not worker-facing guidance, and
not ready for comparable model scoring.

Current validated shape on 2026-07-02:

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
- `scripts/build_global_protections_project_plan.py` and
  `scripts/validate_global_protections_project_plan.py` - source-gated
  sister-project root plan and saved-plan validator; privacy scans reject
  email-like, phone-like, URL/path-like, and 8+ digit copied case-like values
  before downstream planning artifacts can trust the root plan.
- `scripts/build_regulatory_miss_pattern_plan.py` - source-gated adjacent
  domain expansion plan; pattern input and raw privacy scans reject email-like,
  phone-like, URL/path-like, and 8+ digit copied case-like values before a
  candidate domain can enter downstream planning.
- `scripts/build_global_protections_jurisdiction_pack_matrix.py` and
  `scripts/validate_global_protections_jurisdiction_pack_matrix.py` - active
  pilot-cell matrix plus queued-scope blockers.
- `scripts/validate_global_protections_saved_artifacts.py` - aggregate saved
  artifact validator for the global-protections component chain.
- `tests/test_validate_global_protections_saved_artifacts.py` - focused
  regression coverage for saved-artifact aggregate summaries, path redaction,
  and Markdown privacy safety.
- `tests/test_validate_sister_project_planning.py` - focused regression
  coverage for the sister-project planning validator's aggregate-only privacy
  and readiness gates.
- `tests/test_build_global_protections_project_plan.py` and
  `tests/test_validate_global_protections_project_plan.py` - focused
  regression coverage for the source-gated root-plan privacy and validation
  gates.
- `tests/test_build_regulatory_miss_pattern_plan.py` - focused regression
  coverage for the adjacent-domain source-gated planner, including 8+ digit
  copied case-like values.
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
python scripts\build_regulatory_miss_pattern_plan.py --validate
python scripts\validate_global_protections_project_plan.py --validate --no-current-chain
python -m pytest tests\test_build_regulatory_miss_pattern_plan.py -q
python -m pytest tests\test_build_global_protections_project_plan.py tests\test_validate_global_protections_project_plan.py -q
python -m pytest tests\test_validate_global_protections_saved_artifacts.py -q
python -m pytest tests -q -k "global_protections or regulatory_miss_pattern"
```

Current evidence from the latest local run:

- `python scripts\validate_global_protections_saved_artifacts.py`:
  `valid=true`, `failed_artifacts=0/13`, `failed_checks=0/157`,
  `suite_checks=0/21`, `phase_coverage=next:5/34,curator:5/34`,
  `phase_mismatches=0`, `legal_anchor_mismatches=0`,
  `readiness_blocker_mismatches=0`,
  `ready_for_comparable_scoring=false`.
- `python scripts\build_regulatory_miss_pattern_plan.py --validate`:
  `safe_for_research_planning=true`, `pattern_count=11`,
  `candidate_count=10`, `candidate_queue_count=10`,
  `ready_for_comparable_scoring=false`, and privacy-scan counts all zero.
- `python -m pytest tests\test_build_regulatory_miss_pattern_plan.py -q`:
  `8 passed`, covering adjacent-domain source gating, URL/private-field
  rejection, duplicate IDs, non-scoring output, and 8+ digit copied case-like
  values without copying the value into output.
- `python -m pytest tests\test_validate_global_protections_saved_artifacts.py -q`:
  `43 passed`.
- `python scripts\validate_global_protections_project_plan.py --validate --no-current-chain`:
  `valid=true`, `failed_check_count=0`, `candidate_pattern_count=11`,
  `regulatory_candidates_found_count=11`, `readiness_gate_count=5`,
  `first_build_phase_count=4`, and `ready_for_comparable_scoring=false`.
- `python -m pytest tests\test_build_global_protections_project_plan.py tests\test_validate_global_protections_project_plan.py -q`:
  `20 passed`, covering root-plan source gating, downstream readiness blockers,
  saved-plan shape/count/link drift, and 8+ digit copied case-like values
  without copying the value into validator output.
- `python scripts\build_corridor_expansion_plan.py --validate`:
  `safe_for_curation=true`, `planned_task_count=25`, `batch_count=5`,
  `recommended_rows=75`, `source_privacy_ok=true`, and generated-plan privacy
  counts all zero.
- `python scripts\build_reasoning_gap_queue.py --validate`:
  `safe_for_repair=true`, `actionable_for_repair=true`, `input=960`,
  `queued=630`, `skipped.missing_prompt_id=26`, and queue privacy-scan counts
  all zero.
- `python scripts\build_reasoning_targets.py --validate`:
  `input=1316`, `kept=960`, `min_chain=3`,
  `citation_relevance_incoherent=0`, and
  `dropped_incoherent_citations=0`.
- `python scripts\build_reasoning_repairs.py --validate`:
  `input_rows=960`, `queue_entries=630`, `repaired_rows=613`,
  `safe_to_train=true`, `repair_manifest_issues=[]`, and
  `source_queue_issues=[]`.
- `python scripts\build_reasoning_sft_variant.py --validate`:
  `base_rows=1316`, `repaired_input_rows=613`, `replaced_rows=613`,
  `same_size_as_base=true`, `one_row_per_base_prompt=true`, and
  `safe_to_train=true`.
- `python scripts\build_contract_dpo.py --validate`:
  `input=960`, `eligible_gold=292`, `pairs=740`,
  `by_ablated_link=action:289,citation_coherence:159,statute:292`,
  `duplicate_output_pair_rows=0`, `pair_integrity_issues=[]`,
  `contract_manifest_issues=[]`, and `safe_to_train=true`.
- `python scripts\build_dpo_mix_variant.py --validate`:
  `base_input_rows=1316`, `contract_input_rows=581`, `pairs=1897`,
  `by_ablated_link=action:289,statute:292`,
  `source_manifest_issues=[]`, and `safe_to_train=true`.
- `python scripts\build_lift_training_data.py --validate`:
  `considered_pairs=3845`, `selected_pairs=2602`, `sft_examples=2602`,
  `dpo_examples=2602`, `dropped_bad_citation=1`,
  `dropped_irrelevant_citation=81`, `metadata_sanitized_prompt_ids=2187`,
  and `pii_redactions=1836`.
- `python -m pytest tests\test_build_corridor_expansion_plan.py tests\test_validate_training_provenance.py tests\test_audit_training_quality.py -q`:
  `57 passed`, covering metadata-only corridor curation, recorded privacy-scan
  provenance, training-provenance redaction, and 8+ digit copied case-like
  values without copying the value into output.
- `python -m pytest tests\test_build_reasoning_targets.py tests\test_build_reasoning_repairs.py tests\test_build_reasoning_sft_variant.py -q`:
  `76 passed`, covering reasoning target citation-example prompt ID redaction,
  reasoning repair queue/category metadata privacy gates, repaired SFT variant
  provenance checks, 8+ digit copied case-like values, and generated date-style
  prompt IDs that must remain matchable.
- `python -m pytest tests\test_build_contract_dpo.py tests\test_build_lift_training_data.py -q`:
  `41 passed`, covering contract-derived hard-negative DPO pair integrity,
  lift-training gold-source gates, prompt-ID/path redaction, underscore-adjacent
  long copied-ID scrubbing, and no-copy privacy regressions.
- `python -m pytest tests\test_build_dpo_mix_variant.py -q`:
  `24 passed`, covering base+contract DPO provenance, stale/unsafe manifest
  fail-closed behavior, invalid contract-link metadata, private nested payload
  redaction, and underscore-separated 8+ digit copied case-like issue codes
  without copying the value into output.
- `python -m pytest tests\test_build_model_card.py tests\test_finetune_registry.py -q`:
  `54 passed`, covering model-card and fine-tune registry provenance rendering,
  artifact fingerprint verification, privacy-safe display helpers, underscore
  8+ digit copied-ID redaction, and preservation of mixed hash-like provenance
  values.
- `python -m pytest tests\test_build_reasoning_gap_queue.py tests\test_audit_training_quality.py tests\test_validate_training_provenance.py tests\test_training_engine.py -q`:
  `91 passed`, covering metadata-only reasoning repair queues, training audit
  summaries, training-provenance redaction, training-engine artifact safety, and
  8+ digit copied case-like values without copying the value into output.
- `python -m pytest tests -q -k "global_protections or regulatory_miss_pattern or project_bible"`:
  `431 passed, 1 skipped, 2181 deselected`.
- `python scripts\validate_project_bible_pickup.py`:
  `65 checks, 0 findings`, with the global-protections saved-artifact
  snapshot accepted only when the aggregate report is valid, covers all 13
  artifacts, reports all 13 artifacts and Markdown handoffs valid/readable,
  reports zero failed artifacts, missing artifacts, unsafe Markdown reports,
  artifact-path mismatches, failed checks, and failed suite checks, preserves
  the current check-count floors of `total_check_count>=157` and
  `suite_check_count>=21`, has both next-action and curator phase coverage at
  `5/34`, and reports zero phase-coverage, legal-anchor-channel, and
  readiness-blocker mismatches. The saved-artifact Markdown safety check also
  fails closed on `markdown_private_hint` for email-like text, URL/file
  schemes, workspace-local path fragments, and 8+ digit case-like IDs without
  copying those values into validator output.
- `python scripts\validate_sister_project_planning.py`:
  `34 checks, 0 findings`, with the direct snapshot reporting
  `readiness_gate_missing=0`, `source_admission_missing=0`,
  `scored_capability_missing=0`, and
  `privacy_issues=project:0,packs:0,grounding:0,prompts:0,grounding_sources:0`. Any nonzero value
  in those fields is an aggregate-only safety signal to inspect before
  continuing.
- `python -m pytest tests\test_autonomous_engine.py tests\test_build_dimension_candidate_review_packet.py tests\test_build_domain_source_review_packet.py tests\test_validate_domain_source_review_packet.py tests\test_build_domain_grounding_manifest_proposal.py tests\test_build_global_protections_project_plan.py tests\test_validate_global_protections_project_plan.py tests\test_build_regulatory_miss_pattern_plan.py tests\test_build_corridor_expansion_plan.py tests\test_build_reasoning_gap_queue.py tests\test_validate_training_provenance.py tests\test_audit_training_quality.py tests\test_training_engine.py tests\test_validate_sister_project_planning.py tests\test_validate_global_protections_saved_artifacts.py tests\test_rubric_v2.py tests\test_benchmark_leaderboard.py tests\test_project_bible_pickup.py tests\test_intent_split.py tests\test_artifact_path_policy.py tests\test_plan.py -q`:
  `453 passed`, covering the autonomous-engine pause/review gate,
  candidate-dimension review-packet gate, domain source-review intake and
  manifest-proposal gate, global-protections root-plan gate,
  regulatory-miss source-gated planning, corridor-expansion metadata-only
  training curation, reasoning-gap metadata-only repair queues,
  sister-project planning validator, rubric-v2
  isolation, public leaderboard leak guards, saved-artifact Markdown/privacy
  safety, project-bible pickup validator, intent-split coverage, artifact-path
  redaction, and offline no-model plan estimates.
- `python -m pytest tests\test_intent_split.py -q`:
  `11 passed`, covering the opt-in intent split and benign-control prompt set.
- `python scripts\build_counterfactual_pairs.py --validate`:
  `total=568`, with `benign_control=137`, `benign_twin=146`, and
  `counterfactual_swap=285`; output remains propose-only anti-shortcut data.
- `python -m pytest tests\test_build_counterfactual_pairs.py -q`:
  `8 passed`, covering benign-control/twin/corridor-swap generation,
  external-path redaction, and 8+ digit copied case-like manifest values
  without copying the value into output.
- `python -m pytest tests\test_artifact_path_policy.py -q`:
  `7 passed`, covering shared handoff artifact path redaction, safe
  repo-relative labels, private-looking repo-relative segments, hidden paths,
  resolver failures, and stale public external-file placeholder wording across
  public and pickup text.
- `python -m pytest tests\test_plan.py -q`:
  `9 passed`, covering the offline `--plan` estimator and no-model-call
  invariant.
- `python scripts\validate_public_surface.py`:
  `7 checks, 0 findings`.
- `python -m pytest packages --collect-only -q`:
  `1300 tests collected`.
- `python scripts\validate_main_kaggle_kernels.py` and
  `py -3.12 scripts\validate_kaggle_page_sources.py`: both passed.
- `python -m pytest -q`: `4147 passed, 12 skipped` on 2026-07-14 after the
  flywheel, training, Kaggle, archive, and public-site integration changes.
- `uv run --no-project --python 3.12 --with-requirements requirements-docs.txt mkdocs build --clean`:
  passed on 2026-07-14. The build retains existing non-strict documentation
  warnings; the new training guide adds no strict-warning debt.

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
5. Keep rubric-generation experiments versioned and isolated.
   `rich_harness_lift.py --rubric-version v2` is opt-in research evidence
   only; it does not replace or restate v1 leaderboard claims.
   `rich_harness_lift.py --harness-version h2` is the opt-in refusal-collapse
   fix; changed preambles mean h2 responses are NOT comparable with h1 board
   claims.
6. Keep the training-data flywheel fail-closed: generation, curation, SFT/DPO,
   evaluation, and registry stages must preserve hashes, immutable revisions,
   lineage-isolated splits, clean quality evidence, and the no-hidden-CoT
   boundary.
7. Avoid changing Kaggle kernels or workbench UI contracts unless the request is
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
validator script, the autonomous-engine status/preflight test
`tests/test_autonomous_engine.py`, the artifact-path policy regression test
`tests/test_artifact_path_policy.py`, the sister-project validator test
`tests/test_validate_sister_project_planning.py`, the intent-split regression
test `tests/test_intent_split.py`, the offline dry-run plan regression test
`tests/test_plan.py`, the benign-control set
`configs/duecare/benchmarks/benign_control_prompts.json`, or the global
validator's direct helper validators/builders, fails the required-file pickup
check. The
pickup validator also parses its own, the global validator's, the
sister-project validator's, and the autonomous engine's direct local imports so
this helper list cannot silently drift. Copied trees must also include
autonomous engine helper modules such as `scripts/_atomic.py` and the
intent-aware runner `scripts/rich_harness_lift.py`. Copied
`Plans.md` files fail closed unless they remain a compatibility bridge back to the Project Bible,
name the safe loop priorities, and preserve the paused-engine boundary. Copied
`CLAUDE.md` handoff pointers fail closed if they still point at an older
long-loop brief, omit the root `PROJECT_BIBLE.md` bridge, or omit the Claude
Code/Codex/Fable 5-style pickup audience. The reusable goal-command read order
also fails closed unless it names `PROJECT_BIBLE.md` before the hidden rule and
canonical `docs/codex/PROJECT_BIBLE.md`; copied goal-command text also fails if
it drops the Fable 5-style pickup audience. This validator is read-only. It prints
pass/fail wiring checks plus an
aggregate snapshot of pause state, lock state, saved preflight scope,
Ollama-check status, current queue job, candidate-dimension readiness, and any
hidden Claude handoff artifact counts such as open-risk count and recent-edit
count. Its Claude handoff line includes aggregate open-risk severity counts,
aggregate open-risk kind counts, and the high/critical blocking-risk count,
and validates the open_risks shape without copying risk text. Open-risk kind labels are allowlisted;
private or unknown kind labels fail closed as `custom_or_invalid`. The context-reset recommendation is aggregate-only:
context_reset.recommended must be boolean if present, and malformed hidden
values fail closed without copying their contents.
context_reset.policy must be an object if present.
context_reset.policy.mode must stay allowlisted.
context_reset.policy.dryRun must be boolean if present.
context_reset.policy.thresholds and context_reset.counters must be objects if present.
context_reset.policy.thresholds and counters keys must stay allowlisted if present.
context_reset.policy.thresholds and counters values must be real integers if present.
context_reset.reasons must be a list if present.
context_reset reason entries must be strings if present.
context_reset.candidates must be a list if present.
context_reset candidate entries must be objects if present.
context_reset candidate triggered fields must be booleans if present.
context_reset triggered candidate counts are aggregate-only if present.
context_reset.recommended must be true when any valid candidate has triggered true.
context_reset candidate keys must stay allowlisted.
context_reset candidate actual and threshold fields must be real integers if present.
context_reset candidate triggered flags must match actual greater than threshold when both numbers are present.
Hidden decision_log and continuity sections are also aggregate-only.
decision_log must be a list if present.
decision_log entries must be objects if present.
decision_log decision labels must stay allowlisted.
decision_log actor labels must stay allowlisted if present.
decision_log timestamps must be valid ISO-8601 strings if present.
planItems and wipTasks must be absent, null, or lists if present.
task container counts are aggregate-only; task text and paths are never copied.
continuity must be an object if present.
continuity boolean fields must remain booleans.
continuity effort_hint must stay one of the allowlisted labels.
summaries, rationale text, paths, and private details are never copied into the
pickup report. Its global-protections line includes aggregate mismatch counts as
`mismatches=phase:<n> legal_anchor:<n> readiness:<n>`. A clean pickup requires
a state-only preflight with ready `false`,
`stop_sentinel_present` still listed as a blocker, and no ignored blockers. If
the hidden handoff artifact is present, it must parse as a JSON object, use the
`structured-handoff` artifact type, and must not report failed checks; missing hidden artifact type fails closed. parse failures are reported without copying private path details. failed-check presence is treated the same way.
malformed hidden failed_checks values fail closed as shape labels without
copying the value; non-empty list or object failed-check containers still block
pickup through the aggregate presence flag.
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
Copied sister/global summary count fields require real integers, not booleans.
That includes global-protections mismatch counters, where `false` must not be
accepted as the same thing as integer `0`.
Copied sister-project reports must meet the current 34-check floor; older
copied summaries that say `ok=true` with fewer checks still fail pickup.
Copied sister failed-id summaries keep only safe rule IDs; malformed or private failed IDs become `custom_or_invalid`.
Long numeric case-like failed IDs also become `custom_or_invalid`.
Copied sister project identity labels are allowlisted; private or unknown identity labels become `custom_or_invalid`.
Boolean hidden recent-edit counts are ignored; malformed hidden recentEdits values fail closed without copying their contents, and only real integers or the safe `recentEdits` length are reported.
previous_state.plan_counts keys must stay allowlisted if present.
previous_state.plan_counts values must be real integers if present.
Hidden handoff nested state containers such as `previous_state`,
`previous_state.session_state`, `previous_state.plan_counts`, and
`next_action` must be JSON objects if present; malformed hidden containers fail
closed as shape labels without copying their values. Hidden handoff string fields use allowlisted labels only; the hidden
`version` and `legacy_version` labels are allowlisted as `1.0.0` or `2.0.0`.
Custom labels are reported as `custom_or_invalid`, and unknown hidden handoff
labels fail closed by field name instead of copied hidden-state text. The
handoff summary reports timestamp presence, timestamp validity, and
`validated_after_handoff=<bool>` so stale
open-risk counts can be read against current validator evidence without editing
hidden session logs. A clean handoff requires the hidden timestamp to be valid
and not newer than the validation run.
For validator pickup, keep the exact rule visible: version and legacy_version labels
are allowlisted by a dedicated hidden handoff version check, and unknown hidden handoff labels fail closed
by field name only.
High or critical hidden open-risk severities fail closed through aggregate
counts; unknown hidden open-risk severities fail closed as `custom_or_invalid`.
Unknown hidden open-risk kind labels also fail closed as `custom_or_invalid`.
Low and medium historical risks stay visible but do not block the pickup
validator by themselves. A malformed `open_risks` value also fails closed as a
shape problem.
Saved status string fields use the same pattern: known status labels stay
visible, unsafe model/path-like values, 8+ digit long numeric case-like labels, and
custom blocker or mismatch labels are reported as `custom_or_invalid`, and
unknown status labels fail closed by field name while keeping the useful counts
and booleans needed for pickup decisions.
Malformed copied status-list fields or entries also become `custom_or_invalid`
instead of being dropped.
For saved `--status-json` payloads, this includes forward-slash local model paths,
URL-scheme model labels such as `file:/C:/Users/...`, and copied case-like model
labels such as `local-case-123456789`.
Boolean values in numeric status count fields fail shape validation instead of
being treated as counts.
saved preflight schema and mode must match manual preflight v1:
`mode=manual_preflight` and `schema_version=autonomous_engine_preflight.v1`.
saved preflight path must stay at reports/autonomous_engine_preflight.json.
The saved preflight must exist and not need refresh before a copied status can
pass pickup.
launch readiness must still require an Ollama check; a copied status with
`launch_ready_requires_ollama_check=false` fails pickup even if
`ollama_checked=false`.
The saved preflight dimension-review status must match candidate-dimension review gate;
pickup remains blocked unless both stay at `validated_zero_proposals`.

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
Malformed project readiness-gate IDs fail closed as aggregate required-gate
and privacy counts instead of copied gate values.
Malformed project phase and jurisdiction-pack row IDs fail closed as aggregate
row-ID shape and privacy counts instead of copied IDs.
Malformed grounding source row IDs fail closed as aggregate row-ID shape counts
instead of copied source IDs.
Malformed or non-list grounding source containers expose
`grounding_source_privacy_issue_count` instead of copied source-row values.
Malformed grounding source URL values are scanned for aggregate privacy counts;
valid public `https://` source anchors stay allowed as source objects.
Private-looking details inside otherwise `https://` source URLs still fail as
aggregate grounding-source privacy counts without copying the URL.
Malformed domain-lens review gates fail closed as aggregate counts instead of
copying curator-provided gate entries.
Readiness gates must also keep explicit aggregate block coverage for public
claims, training use, comparable scoring, and worker-facing use.
Scored capabilities must keep the regulatory-miss pattern coverage visible:
jurisdiction selection, local-law versus international-anchor discipline,
ordinary protection detection, safe remedy/privacy routing, and refusal to
invent volatile legal specifics.
First-build phases and scheme prompts must carry explicit blocked flags, with
public scoring, training use, and worker-facing use all set to `false`.
Scheme prompts must still map to declared candidate pattern IDs and remain
explicit unresolved source-gap rows.
Malformed scheme-prompt rows become aggregate row-shape and privacy counts
instead of copied prompt-row contents.
Non-list scheme-prompt containers fail closed with a safe
`prompt_rows_not_list` parse/shape error while their contents are scanned only
for aggregate privacy counts.
Its JSON report omits raw scheme-prompt IDs, prompt text, source URLs, and
custom issue values; failed checks report rule IDs plus aggregate counts instead
of copying curator-provided identifiers. Source status summaries keep only
known enum labels; missing, malformed, or private source statuses are grouped
under `invalid_or_unknown`; canonical
project/domain labels stay visible, while copied custom labels are reported as
`custom_or_invalid`; copied phase IDs and other issue values are summarized by
counts. Privacy scans inspect both metadata keys and values for
project-charter, jurisdiction-pack, grounding metadata, grounding source rows,
and scheme-prompt rows,
and report only aggregate issue counts for email-like, phone-like, URL-like,
local-path, and long-digit (8+ digit) patterns. URL-like patterns include malformed or copied schemes
such as `http:/`, `ftp:/`, `ftp://`, `s3:/`, `file:/`, and `mailto:`, and
local-path patterns include workspace-relative
fragments such as `OneDrive/Documents/` and `AppData/Local/`. The summary
exposes `grounding_source_privacy_issue_count` and
`scheme_prompt_privacy_issue_count` instead of raw source or prompt rows.
Prompt parse-error details are reduced to safe line numbers and known safe error labels;
custom error text or custom error labels are reported as
`invalid_or_unknown` instead of copied into the report.
Boolean parse-error line values are not treated as line numbers.
Nonpositive parse-error line values are ignored.
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
3. Read `docs/PUBLICATION_READINESS.md` for the current stopping point, strict
   training blocker, and prioritized backlog.
4. Run `python scripts/validate_project_bible_pickup.py` and
   `python scripts/autonomous_engine.py --status`; neither calls Ollama.
5. Inspect the relevant tests before changing behavior.
6. Keep changes tightly scoped to the requested improvement loop.

Before claiming completion:

1. Run the smallest relevant focused tests.
2. Run public/documentation validators for docs or public-surface changes.
3. Report exact validation coverage and any environment-specific blockers.
4. Preserve the verified autonomous-engine state; do not pause, resume, reset,
   or reorder it unless Taylor explicitly asks.
