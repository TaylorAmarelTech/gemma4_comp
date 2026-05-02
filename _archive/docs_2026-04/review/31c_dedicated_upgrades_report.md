# 31c: Dedicated notebook canonical upgrades report

Date: 2026-04-16
Scope: canonicalize the three pre-canonical dedicated comparison
builders (230, 240, 270) and add dedicated adversarial validators.

## 1. Notebook upgrades

All three builders were rewritten cell 0 + trailing summary / trouble-
shooting / final print only; middle logic (model load, inference,
scoring, plotting) is preserved byte-for-byte. Each builder now imports
`canonical_header_table`, `troubleshooting_table_html`, and
`patch_final_print_cell` from `scripts/_canonical_notebook.py`.

Files rewritten:

- `scripts/build_notebook_230_mistral_family_comparison.py`
  - New canonical H1 `# 230: DueCare Gemma 4 vs Mistral Family` (no em dash).
  - 22%/78% HTML header table with Inputs, Outputs, Prerequisites, Runtime,
    Pipeline position.
  - Reading-order bullets link 100, 210, 220, 240, 270, 399 with live
    Kaggle URLs.
  - Defines `SAFETY_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())`.
  - `_hex_to_rgba` handles every radar `fillcolor`.
  - HTML troubleshooting table + URL-bearing final print patched in via
    `patch_final_print_cell`.
  - Removed the duplicate wheel-walk block at step 3; hardener owns the
    only install path.
- `scripts/build_notebook_240_openrouter_frontier_comparison.py`
  - Same canonical shape as 230. H1: `# 240: DueCare Gemma 4 vs Frontier Cloud Models`.
  - Reading-order links 100, 210, 220, 230, 270, 399. No
    "Privacy is non-negotiable" footer; that phrasing is reserved for 610/899.
  - Duplicate wheel-walk block at step 3 removed.
- `scripts/build_notebook_270_gemma_generations.py`
  - H1: `# 270: DueCare Gemma 2 vs 3 vs 4 Safety Gap`.
  - New `PUBLISHED_BASELINE` fallback dict with `PUBLISHED_BASELINE_SOURCE`
    + `PUBLISHED_BASELINE_DATE` citations; populates the V3 6-band
    summary when the prompts dataset is not attached so the headline
    stacked-bar chart still renders. Numbers carry the last successful
    Kaggle T4 x2 run at `MAX_PROMPTS=50`.
  - `BANDS` tuple defined and reused across classifier, summary cell,
    and headline chart.
  - HTML troubleshooting table + URL-bearing final print linking 399 and 100.

## 2. Validators created

Three new adversarial validators that mirror
`_validate_220_adversarial.py` (17 checks each):

- `scripts/_validate_230_adversarial.py`
- `scripts/_validate_240_adversarial.py`
- `scripts/_validate_270_adversarial.py`

Each checks: metadata id + title + `is_private=False` + dataset sources;
H1 shape (no em dash); the five HTML header rows; required cross-link
slugs; single install cell; no legacy wheel-walk drift; weighted-rubric
constants (230/240) or `BANDS`/`PUBLISHED_BASELINE` (270); `_hex_to_rgba`
usage; absence of "Privacy is non-negotiable" phrase in the body;
absence of `| | |` pseudo-tables; HTML troubleshooting table; URL-
bearing final print with both forward and section-close slugs;
hardener default print patched out.

## 3. Validation results

```
.venv/Scripts/python.exe scripts/_validate_230_adversarial.py
  ...
  ALL CHECKS PASSED

.venv/Scripts/python.exe scripts/_validate_240_adversarial.py
  ...
  ALL CHECKS PASSED

.venv/Scripts/python.exe scripts/_validate_270_adversarial.py
  ...
  ALL CHECKS PASSED

.venv/Scripts/python.exe scripts/validate_notebooks.py
  ...
  Validated 42 notebooks successfully.
```

Mirror sync after each rebuild: `scripts/sync_kaggle_notebook_mirror.py`
reported `updated 230/240/270_*.ipynb`, then a subsequent run showed no
divergence (`updated=0`).

## 4. Push-ready dedicated batch

With 230/240/270 now canonical, the dedicated batch ready for 31e to
push (update pushes against existing live kernels) is:

1. `taylorsamarel/duecare-230-mistral-family-comparison`
2. `taylorsamarel/duecare-openrouter-frontier-comparison`
3. `taylorsamarel/duecare-270-gemma-generations`

No metadata drift, no title drift, no slug drift.

## 5. Inputs for 31d

31d (shared-builder canonicalization) must:

- Canonicalize `250` via `NB11_CELLS` in
  `scripts/build_grading_notebooks.py`; do not touch `NB09/10/12/13`.
- Canonicalize `260` via `RAG_CELLS` in
  `scripts/build_showcase_notebooks.py`; do not touch
  `ADVERSARIAL_CELLS`, `FC_CELLS`, `SWARM_CELLS`.
- Review the `299` and `399` recap narrative in
  `scripts/build_section_conclusion_notebooks.py` so the 5-point key
  points match the now-canonical 130, 200, 210, 220, 230, 240, 270
  content.
- Two pre-existing validator regressions inherited from 31b need
  refresh passes (out of 31c scope):
  - `scripts/_validate_210_adversarial.py`: still expects the
    `399-duecare-baseline-text-comparisons-conclusion` slug; 31b
    updated `URL_399` to `duecare-baseline-text-comparisons-conclusion`.
  - `scripts/_validate_220_adversarial.py`: still expects the
    `220-duecare-gemma-4-vs-6-oss-models-via-ollama-cloud` metadata id;
    31b reverted it to `duecare-ollama-cloud-oss-comparison`.

Neither regression blocks 31c (their validators are diagnostic tools,
not part of the repo-wide gate). 31d should refresh both while it is
already inside the shared-builder canonicalization pass.
