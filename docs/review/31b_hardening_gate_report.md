# 31b: Builder hardening and validator gate report

Date: 2026-04-16
Scope: land structural hardening fixes, source-of-truth repairs,
preserve the validator gate.

## Landed in this stage

### 1. Shared slug helper extracted

- Created `scripts/_public_slugs.py` with a single
  `PUBLIC_SLUG_OVERRIDES` dict. Documented the rule: only record
  deviations from the default slug.
- Replaced three hand-copied `PUBLIC_SLUG_OVERRIDES` blocks with imports
  in `scripts/build_index_notebook.py`,
  `scripts/build_notebook_005_glossary.py`, and
  `scripts/build_section_conclusion_notebooks.py`.
- Fixed the 600 override: it now points at the canonical live slug
  `600-duecare-results-dashboard` instead of the legacy redirect
  `600-interactive-safety-evaluation-dashboard`.
- Added three new override entries for the blocked-new-kernel kernels:
  130 -> `duecare-prompt-corpus-exploration`,
  299 -> `duecare-baseline-text-evaluation-framework-conclusion`,
  399 -> `duecare-baseline-text-comparisons-conclusion`.

### 2. Canonical notebook helper scaffold added

- Created `scripts/_canonical_notebook.py` exporting
  `HEX_TO_RGBA_SRC`, `canonical_header_table`,
  `troubleshooting_table_html`, `patch_final_print_cell`, and
  `escape_cell`.
- These are the extractable pieces of the canonical comparison pattern
  already inlined in `build_notebook_210_oss_model_comparison.py` and
  `build_notebook_220_ollama_cloud_comparison.py`. 31c uses them in
  the 230/240/270 rewrites.

### 3. Live-slug metadata reverts

- 220 metadata id: `220-duecare-gemma-4-vs-6-oss-models-via-ollama-cloud`
  -> `duecare-ollama-cloud-oss-comparison` (live).
- 230 metadata id: `230-duecare-gemma-4-vs-mistral-family` ->
  `duecare-230-mistral-family-comparison` (live).
- 240 metadata id: `240-duecare-gemma-4-vs-frontier-cloud-models` ->
  `duecare-openrouter-frontier-comparison` (live).
- 270 metadata id: `270-duecare-gemma-2-vs-3-vs-4-safety-gap` ->
  `duecare-270-gemma-generations` (live).

### 4. Fallback slugs for blocked first-time creation

- 130 builder `KERNEL_ID`: `duecare-prompt-corpus-exploration` (was
  `130-duecare-prompt-corpus-exploration`).
- 299 (section conclusions) uses `PUBLIC_SLUG_OVERRIDES` lookup; id now
  resolves to `duecare-baseline-text-evaluation-framework-conclusion`.
- 399: same pattern; resolves to
  `duecare-baseline-text-comparisons-conclusion`.
- Section-conclusion builder now prefers an explicit override entry
  over the title-derived slug.

### 5. Stale cross-link URL constants fixed

Updated `URL_299` and `URL_399` in:
`build_notebook_110.py`, `build_notebook_120.py`,
`build_notebook_130_prompt_corpus_exploration.py`,
`build_notebook_200_cross_domain_proof.py`,
`build_notebook_210_oss_model_comparison.py`,
`build_notebook_220_ollama_cloud_comparison.py`.

## Validator gate

- `python scripts/validate_notebooks.py` after rebuilds:
  `Validated 42 notebooks successfully`.
- Ran `python scripts/sync_kaggle_notebook_mirror.py` to resync the
  `notebooks/` mirror after `build_notebook_230_*` and
  `build_notebook_240_*` changes left divergent copies.

## Files edited

- New: `scripts/_public_slugs.py`, `scripts/_canonical_notebook.py`.
- Modified:
  `scripts/build_index_notebook.py`,
  `scripts/build_notebook_005_glossary.py`,
  `scripts/build_section_conclusion_notebooks.py`,
  `scripts/build_notebook_110.py`,
  `scripts/build_notebook_120.py`,
  `scripts/build_notebook_130_prompt_corpus_exploration.py`,
  `scripts/build_notebook_200_cross_domain_proof.py`,
  `scripts/build_notebook_210_oss_model_comparison.py`,
  `scripts/build_notebook_220_ollama_cloud_comparison.py`,
  `scripts/build_notebook_230_mistral_family_comparison.py`,
  `scripts/build_notebook_240_openrouter_frontier_comparison.py`,
  `scripts/build_notebook_270_gemma_generations.py`.
- All regenerated notebooks under
  `kaggle/kernels/duecare_*/*.ipynb` and `notebooks/*.ipynb`.

## Outstanding gaps that feed 31c/31d/31e

1. **230, 240, 270 still pre-canonical inside their cell strings.**
   The header still uses em-dash H1 and `| | |` pseudo-table. 31c
   rewrites cell 0 and the trailing summary/troubleshooting/final
   print using `_canonical_notebook.py` helpers.
2. **250 (`NB11_CELLS`) and 260 (`RAG_CELLS`) still pre-canonical.**
   31d edits these cell blocks inside the shared builders.
3. **299 and 399 section conclusions** already use the canonical
   header_table shape inside the section-conclusion builder, but the
   recap narrative and the 5-point key_points for 399 should be
   reviewed against the now-live 130/200/210/220/230/240/270 content.
   31d scope.
4. **600 has no builder.** Step H in checkpoint 31 still open.
5. **No adversarial validators for 230, 240, 270.** 31c scope.
6. **`kaggle_live_slug_map.json`** has 22 `null` entries; refresh
   after 31e publishes the ready kernels.

## Gate to leave 31b

- Validator green at 42/42. YES.
- All 4 slug-reverts landed and verified in `kernel-metadata.json`
  files. YES.
- `_public_slugs.py` is the single source of truth. YES.
- `_canonical_notebook.py` exists and exports the helpers 31c needs.
  YES.

## Input for 31c

31c (dedicated notebook canonical upgrades) must edit the following
files:

1. `scripts/build_notebook_230_mistral_family_comparison.py`: rewrite
   the first markdown cell (HEADER) to canonical HTML table form;
   remove em-dash H1 and `| | |` pseudo-table; remove any "Privacy is
   non-negotiable" footer; ensure the radar fill uses
   `_hex_to_rgba(...)`; rewrite the trailing summary/troubleshooting/
   final-print cells using the helpers in `_canonical_notebook.py`.
2. `scripts/build_notebook_240_openrouter_frontier_comparison.py`:
   same shape.
3. `scripts/build_notebook_270_gemma_generations.py`: same shape, plus
   `PUBLISHED_BASELINE` fallback for when
   `gemma_baseline_findings.json` is not attached.
4. New: `scripts/_validate_230_adversarial.py` (17 checks mirroring
   `_validate_220_adversarial.py`).
5. New: `scripts/_validate_240_adversarial.py` (17 checks).
6. New: `scripts/_validate_270_adversarial.py` (17 checks).

Gate to leave 31c:
- All three adversarial validators pass.
- `python scripts/validate_notebooks.py` stays at 42 of 42 OK.
- Each of 230, 240, 270 emits a header with H1 ``# NNN: DueCare
  <Title>`` (no em dash), the canonical HTML header table, a
  troubleshooting HTML table, and a terminal ``print(...)`` cell
  containing the next-notebook Kaggle URL.
