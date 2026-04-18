# 31a: DueCare repo truth and publish inventory

Date: 2026-04-16
Scope: repo truth reconciliation. Validator state confirmed. Live-slug
contradictions resolved. Next-stage inputs named.

## 1. Verified repo truths

- `python scripts/validate_notebooks.py` returns `Validated 42 notebooks
  successfully`. Gate green.
- `kaggle/kernels/` contains 42 directories; all 42 mirror the local
  build outputs.
- `docs/current_kaggle_notebook_state.md` (generated 2026-04-15 20:12)
  tracks 29 live Kaggle kernels with `29 OK, 0 FAIL` last verification.
- 13 local kernel directories are NOT live on Kaggle yet: 130, 150,
  155, 160, 099, 199, 299, 399, 499, 599, 699, 799, 899.
- `scripts/kaggle_live_slug_map.json` records only 7 populated live-slug
  entries; the rest are `null`. Needs population during 31e.
- There is no `scripts/build_notebook_600_results_dashboard.py`. The
  600 source-of-truth gap is confirmed. The live kernel JSON exists at
  `kaggle/kernels/duecare_600_results_dashboard/600_results_dashboard.ipynb`
  (21 KB, contains the pre-canonical `| | |` pseudo-table header).
- There is no `scripts/_public_slugs.py` helper. `PUBLIC_SLUG_OVERRIDES`
  is hand-copied in 3 builders: `build_index_notebook.py`,
  `build_notebook_005_glossary.py`, `build_section_conclusion_notebooks.py`.
- There is no `scripts/_canonical_notebook.py` helper. The canonical
  header + troubleshooting table + URL hand-off print + `_hex_to_rgba`
  pattern is inlined in each builder (210, 220, 230, 240, 270).

## 2. Contradictions resolved

### 220 is live, not blocked

- Checkpoint 31 section 5 claims `220: 400 Bad Request on two consecutive
  attempts` and implies the kernel is not live.
- Repo truth: `current_kaggle_notebook_state.md` lists 220 at
  `taylorsamarel/duecare-ollama-cloud-oss-comparison` with title
  `DueCare Ollama Cloud OSS Comparison`. This kernel is live.
- Cause of the recent push failures: local metadata was changed to the
  canonical `taylorsamarel/220-duecare-gemma-4-vs-6-oss-models-via-ollama-cloud`
  slug, so `kaggle kernels push` tries to CREATE a new kernel rather
  than UPDATE the existing one. Kaggle rejects the new-slug creation
  with `400 Bad Request` because a user-hidden redirect already points
  at the live slug.
- Fix: revert 220's `KERNEL_ID` and `kernel-metadata.json.id` to
  `taylorsamarel/duecare-ollama-cloud-oss-comparison`. Add 220 to
  `PUBLIC_SLUG_OVERRIDES` so link generation continues to resolve.
- The checkpoint-31 fallback suggestion for 220
  (`duecare-gemma-4-vs-6-oss-models-via-ollama-cloud`) would also fail
  because Kaggle already owns the redirect chain. Use the actual live
  slug.

### 600 uses the `600-duecare-*` live slug, not the legacy slug

- Checkpoint 31 section 3 notes
  `taylorsamarel/600-duecare-results-dashboard v? (HTTP 200; legacy
  600-interactive-safety-evaluation-dashboard redirects)`.
- Repo truth: local metadata has `id:
  taylorsamarel/600-duecare-results-dashboard`, which matches the
  canonical live slug. The older
  `600-interactive-safety-evaluation-dashboard` currently redirects.
- `current_kaggle_notebook_state.md` line 56 still prints the redirect
  legacy URL in the state inventory. That inventory row should be
  regenerated so both the id and the public URL align on
  `600-duecare-results-dashboard`.

### 005 is live and canonical

- Live slug is `taylorsamarel/duecare-005-glossary`. Local metadata id
  matches. No action needed here beyond keeping the title
  (`005: DueCare Glossary and Reading Map`) stable.

### 130, 299, 399 are genuinely NOT live

- These three kernel directories exist locally with metadata ids that
  carry the NNN- prefix (`130-duecare-...`, `299-duecare-...`,
  `399-duecare-...`). Kaggle new-kernel creation returns
  `Notebook not found` or `400 Bad Request` for these slug shapes.
- Working hypothesis from checkpoint 31: Kaggle blocks first-time
  creation when the slug starts with a digit-prefix for at least these
  IDs.
- Fallback slugs to apply before retrying (already documented in
  checkpoint 31):
  - 130 -> `taylorsamarel/duecare-prompt-corpus-exploration`
  - 299 -> `taylorsamarel/duecare-baseline-text-evaluation-framework-conclusion`
  - 399 -> `taylorsamarel/duecare-baseline-text-comparisons-conclusion`

## 3. Current builder ownership and gaps

### Dedicated builders (1 notebook each)

`build_notebook_005_glossary.py`, `build_notebook_010_quickstart.py`,
`build_notebook_100.py`, `build_notebook_110.py`, `build_notebook_120.py`,
`build_notebook_130_prompt_corpus_exploration.py`,
`build_notebook_150_free_form_gemma_playground.py`,
`build_notebook_155_tool_calling_playground.py`,
`build_notebook_160_image_processing_playground.py`,
`build_notebook_200_cross_domain_proof.py`,
`build_notebook_210_oss_model_comparison.py` (canonical),
`build_notebook_220_ollama_cloud_comparison.py` (canonical),
`build_notebook_230_mistral_family_comparison.py` (pre-canonical),
`build_notebook_240_openrouter_frontier_comparison.py` (pre-canonical),
`build_notebook_270_gemma_generations.py` (pre-canonical),
`build_notebook_320_supergemma_safety_gap.py`,
`build_notebook_440_per_prompt_rubric_generator.py`,
`build_notebook_450_contextual_worst_response_judge.py`,
`build_notebook_510_phase2_model_comparison.py`,
`build_notebook_520_phase3_curriculum_builder.py`,
`build_notebook_530_phase3_unsloth_finetune.py`.

### Shared builders

- `build_grading_notebooks.py`: emits 250 (`NB11_CELLS`), 310
  (`NB12_CELLS`), 410 (`NB09_CELLS`), 420 (`NB10_CELLS`), 430
  (`NB13_CELLS`).
- `build_showcase_notebooks.py`: emits 260 (`RAG_CELLS`, GPU), 300
  (`ADVERSARIAL_CELLS`), 400 (`FC_CELLS`), 500 (`SWARM_CELLS`).
- `build_section_conclusion_notebooks.py`: emits 099, 199, 299, 399,
  499, 599, 699, 799, 899.
- `build_kaggle_notebooks.py`: emits 610.
- `build_index_notebook.py`: emits 000.

### Source-of-truth gap

- **600 Results Dashboard**: no builder. Any future refresh must either
  locate a hidden generator or create
  `scripts/build_notebook_600_results_dashboard.py` from the current
  kernel JSON.

### Cross-cutting duplication

- `PUBLIC_SLUG_OVERRIDES` appears in 3 builders. Extract to
  `scripts/_public_slugs.py` before any 31b slug changes so the new
  entries only land in one place.
- Canonical header + troubleshooting table + URL hand-off print +
  `_hex_to_rgba` are inlined in at least 5 comparison builders. Extract
  to `scripts/_canonical_notebook.py` before 31c rewrites.

## 4. Live slug table

| NNN | Kernel dir | Live Kaggle slug | Live? | Metadata id matches live? |
|---|---|---|---|---|
| 000 | `duecare_000_index` | `taylorsamarel/duecare-000-index` | YES | YES |
| 005 | `duecare_005_glossary` | `taylorsamarel/duecare-005-glossary` | YES | YES |
| 010 | `duecare_010_quickstart` | `taylorsamarel/duecare-010-quickstart` | YES | YES |
| 099 | `duecare_099_orientation_background_package_setup_conclusion` | (none) | NO | -- |
| 100 | `duecare_100_gemma_exploration` | `taylorsamarel/duecare-gemma-exploration` | YES | YES |
| 110 | `duecare_110_prompt_prioritizer` | `taylorsamarel/00a-duecare-prompt-prioritizer-data-pipeline` | YES | YES |
| 120 | `duecare_120_prompt_remixer` | `taylorsamarel/duecare-prompt-remixer` | YES | YES |
| 130 | `duecare_130_prompt_corpus_exploration` | (none) | NO | N/A, needs fallback slug |
| 150 | `duecare_150_free_form_gemma_playground` | (none) | NO | -- |
| 155 | `duecare_155_tool_calling_playground` | (none) | NO | -- |
| 160 | `duecare_160_image_processing_playground` | (none) | NO | -- |
| 199 | `duecare_199_free_form_exploration_conclusion` | (none) | NO | -- |
| 200 | `duecare_200_cross_domain_proof` | `taylorsamarel/duecare-200-cross-domain-proof` | YES | YES |
| 210 | `duecare_210_oss_model_comparison` | `taylorsamarel/duecare-gemma-vs-oss-comparison` | YES | YES |
| 220 | `duecare_220_ollama_cloud_comparison` | `taylorsamarel/duecare-ollama-cloud-oss-comparison` | YES | **NO, needs revert** |
| 230 | `duecare_230_mistral_family_comparison` | `taylorsamarel/duecare-230-mistral-family-comparison` | YES | NO, metadata says `230-duecare-gemma-4-vs-mistral-family` |
| 240 | `duecare_240_openrouter_frontier_comparison` | `taylorsamarel/duecare-openrouter-frontier-comparison` | YES | NO, metadata says `240-duecare-gemma-4-vs-frontier-cloud-models` |
| 250 | `duecare_250_comparative_grading` | `taylorsamarel/duecare-250-comparative-grading` | YES | YES |
| 260 | `duecare_260_rag_comparison` | `taylorsamarel/duecare-260-rag-comparison` | YES | YES |
| 270 | `duecare_270_gemma_generations` | `taylorsamarel/duecare-270-gemma-generations` | YES | NO, metadata says `270-duecare-gemma-2-vs-3-vs-4-safety-gap` |
| 299 | `duecare_299_*` | (none) | NO | N/A, needs fallback slug |
| 300 | `duecare_300_adversarial_resistance` | `taylorsamarel/300-gemma-4-against-15-adversarial-attack-vectors` | YES | YES |
| 310 | `duecare_310_prompt_factory` | `taylorsamarel/duecare-310-prompt-factory` | YES | YES |
| 320 | `duecare_320_supergemma_safety_gap` | `taylorsamarel/duecare-finding-gemma-4-safety-line` | YES | YES |
| 399 | `duecare_399_*` | (none) | NO | N/A, needs fallback slug |
| 400 | `duecare_400_function_calling_multimodal` | `taylorsamarel/duecare-400-function-calling-multimodal` | YES | YES |
| 410 | `duecare_410_llm_judge_grading` | `taylorsamarel/duecare-410-llm-judge-grading` | YES | YES |
| 420 | `duecare_420_conversation_testing` | `taylorsamarel/420-multi-turn-conversation-escalation-detection` | YES | YES |
| 430 | `duecare_430_rubric_evaluation` | `taylorsamarel/430-54-criterion-pass-fail-rubric-evaluation` | YES | YES |
| 440 | `duecare_440_per_prompt_rubric_generator` | `taylorsamarel/duecare-per-prompt-rubric-generator` | YES | YES |
| 450 | `duecare_450_contextual_worst_response_judge` | `taylorsamarel/duecare-contextual-judge` | YES | YES |
| 499 | `duecare_499_advanced_evaluation_conclusion` | (none) | NO | -- |
| 500 | `duecare_500_agent_swarm_deep_dive` | `taylorsamarel/duecare-500-agent-swarm-deep-dive` | YES | YES |
| 510 | `duecare_510_phase2_model_comparison` | `taylorsamarel/duecare-phase2-comparison` | YES | YES |
| 520 | `duecare_520_phase3_curriculum_builder` | `taylorsamarel/duecare-520-phase3-curriculum-builder` | YES | YES |
| 530 | `duecare_530_phase3_unsloth_finetune` | `taylorsamarel/duecare-530-phase3-unsloth-finetune` | YES | YES |
| 599 | `duecare_599_model_improvement_opportunities_conclusion` | (none) | NO | -- |
| 600 | `duecare_600_results_dashboard` | `taylorsamarel/600-duecare-results-dashboard` | YES | YES |
| 610 | `duecare_610_submission_walkthrough` | `taylorsamarel/duecare-610-submission-walkthrough` | YES | YES |
| 699 | `duecare_699_advanced_prompt_test_generation_conclusion` | (none) | NO | -- |
| 799 | `duecare_799_adversarial_prompt_test_evaluation_conclusion` | (none) | NO | -- |
| 899 | `duecare_899_solution_surfaces_conclusion` | (none) | NO | -- |

Net: 29 live, 13 not yet live. Of the 29 live, 4 have metadata-id
drift that must be reverted before the next update push (220, 230,
240, 270).

## 5. Validation state

- `python scripts/validate_notebooks.py`: `Validated 42 notebooks
  successfully` (repo-wide gate green).
- `scripts/_validate_210_adversarial.py`: present, 17 checks.
- `scripts/_validate_220_adversarial.py`: present, 17 checks.
- `scripts/_validate_230_adversarial.py`: **not present**, needs creation in 31c.
- `scripts/_validate_240_adversarial.py`: **not present**, needs creation in 31c.
- `scripts/_validate_270_adversarial.py`: **not present**, needs creation in 31c.
- `scripts/verify_kaggle_urls.py`: last reported `29 OK, 0 FAIL` on
  2026-04-15.

## 6. Exact push-ready queue

Push-ready means the local build validates, the metadata matches a
live slug or the first-time creation is expected to succeed, and
structural canonicalization is complete.

- **Currently push-ready as updates**: 000, 005, 010, 100, 110, 120,
  200, 210, 250, 260, 300, 310, 320, 400, 410, 420, 430, 440, 450,
  500, 510, 520, 530, 600, 610 (25 kernels).
  - These are all live with matching metadata ids. A push is a version
    bump unless the builder has changed content.
- **Push-ready after metadata revert** (31b): 220, 230, 240, 270.
  Revert their metadata `id` back to the live slug.
- **Push-ready after canonicalization** (31c/31d): same 230, 240, 270
  (dedicated) and 250, 260 (shared).

## 7. Exact edit-first queue

Edit-first means the builder must change before the next push or the
outcome is wrong. Ordered for minimum rework:

1. **Extract shared helpers** (Step J, now).
   - Create `scripts/_public_slugs.py` with `PUBLIC_SLUG_OVERRIDES`
     including new 220/230/240/270/130/299/399/600 entries as needed.
   - Create `scripts/_canonical_notebook.py` with `canonical_header`,
     `troubleshooting_table`, `url_handoff_print`, `_hex_to_rgba`,
     `load_phase1_baseline_with_fallback`.
   - Update the 3 builders that hand-copied `PUBLIC_SLUG_OVERRIDES` to
     import from `_public_slugs`.
2. **Slug reverts for 220/230/240/270** (31b).
   - Edit each builder's `KERNEL_ID`/`SLUG` and the corresponding
     `kernel-metadata.json.id` to match the live slug.
3. **Fallback slugs for 130/299/399** (31b).
   - Edit each builder's `KERNEL_ID` to the fallback from section 2.
   - Edit each `kernel-metadata.json.id` to match.
4. **Canonicalize 230, 240, 270** (31c).
   - Apply the 9-point canonical rewrite. Add adversarial validators.
5. **Canonicalize 250 (`NB11_CELLS`) and 260 (`RAG_CELLS`)** (31d).
   - Canonical rewrite inside the shared builders; do not touch
     sibling cell blocks.
6. **Canonicalize 299 and 399 section conclusions** (31d).
   - Inside `build_section_conclusion_notebooks.py`. Keep the 5-point
     recap accurate to the upstream notebooks.
7. **Create 600 builder** (Step H).
   - `scripts/build_notebook_600_results_dashboard.py` starting from
     the existing kernel JSON. Canonicalize in the same pass.

## 8. Inputs for 31b

31b (builder hardening and validator gate) must edit the following
files, in this order:

1. New helper: `scripts/_public_slugs.py`.
2. New helper: `scripts/_canonical_notebook.py`.
3. `scripts/build_index_notebook.py`: replace inline
   `PUBLIC_SLUG_OVERRIDES` with `from _public_slugs import
   PUBLIC_SLUG_OVERRIDES`.
4. `scripts/build_notebook_005_glossary.py`: same.
5. `scripts/build_section_conclusion_notebooks.py`: same.
6. `scripts/build_notebook_220_ollama_cloud_comparison.py`:
   `KERNEL_ID = "taylorsamarel/duecare-ollama-cloud-oss-comparison"`.
7. `kaggle/kernels/duecare_220_ollama_cloud_comparison/kernel-metadata.json`:
   `"id": "taylorsamarel/duecare-ollama-cloud-oss-comparison"`,
   `"title": "220: DueCare Gemma 4 vs 6 OSS Models via Ollama Cloud"`.
8. `scripts/build_notebook_230_mistral_family_comparison.py`:
   `KERNEL_ID = "taylorsamarel/duecare-230-mistral-family-comparison"`.
9. Same pattern for 240 -> `duecare-openrouter-frontier-comparison`,
   270 -> `duecare-270-gemma-generations`.
10. `scripts/build_notebook_130_prompt_corpus_exploration.py`:
    `KERNEL_ID = "taylorsamarel/duecare-prompt-corpus-exploration"`.
11. 299 entry in `build_section_conclusion_notebooks.py`:
    slug `duecare-baseline-text-evaluation-framework-conclusion`.
12. 399 entry: slug `duecare-baseline-text-comparisons-conclusion`.
13. `PUBLIC_SLUG_OVERRIDES` in `_public_slugs.py`: add new entries for
    220, 230, 240, 270, 130, 299, 399.
14. Rebuild 000, 005, and all section-conclusion notebooks so the
    cross-links regenerate.
15. Run `scripts/validate_notebooks.py` -- must stay green.

## Final response

Reconciled truths: validator at 42/42; 29 live / 13 not live; 220 is
live at `duecare-ollama-cloud-oss-comparison` not blocked; 600 has no
builder.

Checkpoint updates: section 5 of `31_project_checkpoint_v2.md` needs a
revision — 220 is NOT blocked; its metadata drifted. 130, 299, 399 are
genuinely blocked. 220's suggested fallback in checkpoint section 6 is
wrong; use the real live slug.

Validation result: `Validated 42 notebooks successfully`.

Push-ready queue: 25 kernels push as version bumps right now. 4 more
(220, 230, 240, 270) push-ready after metadata revert.

Edit-first queue: extract helpers first, then metadata reverts, then
fallback slugs for 130/299/399, then canonicalize 230/240/270 and
250/260 and 299/399, then create the 600 builder.

Input for 31b: the 15-step file edit sequence above.
