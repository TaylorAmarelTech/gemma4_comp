# 31d: Shared-builder canonical upgrades report

Date: 2026-04-16
Scope: canonicalize 250 and 260 inside their shared builders, refresh
299 and 399 recaps, leave sibling cell blocks untouched, keep 42 / 42.

## 1. Shared helper changes

None. `_canonical_notebook.py` and `_public_slugs.py` were already
extracted in 31b with the surface 31d needs. 31d only imports
`canonical_header_table`, `troubleshooting_table_html`, and
`patch_final_print_cell` into the two shared builders.

## 2. Notebook upgrades

### 250 (`NB11_CELLS` in `build_grading_notebooks.py`)

- H1 `# 250: DueCare Comparative Grading` (no em dash).
- Canonical 22 % / 78 % HTML header table (Pipeline position =
  Previous 240, Next 260, Section close 399). Lead paragraph,
  "Why this notebook matters", reading-order bullets, 4-step "What
  this notebook does" list. `| | |` pseudo-table removed.
- Middle cells preserved byte-for-byte.
- Trailing summary rewritten: "What just happened", 4 "Key findings",
  HTML Troubleshooting table (5 rows), "Next" block with URLs for
  260, 399, 520, 000. "Privacy is non-negotiable" banner removed.
- Final `print(...)` patched via `patch_final_print_cell` to print
  the 260 and 399 URLs verbatim.
- `main()` passes title `250: DueCare Comparative Grading`,
  `is_private=False`, and the final-print args. `write_nb` gained two
  keyword-only args defaulting to `None`; NB09 / 10 / 12 / 13 call
  sites omit them and their outputs stay byte-identical.

### 260 (`RAG_CELLS` in `build_showcase_notebooks.py`)

- H1 `# 260: DueCare RAG Comparison` (no em dash).
- Canonical header table (Pipeline position = Previous 250, Next 270,
  Section close 399). Lead paragraph, matter paragraph, reading-order
  bullets, 6-step numbered list. Both pseudo-tables removed.
- Middle cells preserved byte-for-byte.
- Trailing summary rewritten: "What just happened", 4 "Key findings",
  HTML Troubleshooting table (6 rows), "Next" with URLs for 270, 399,
  250, 000. Banner removed.
- Final `print(...)` patched to print the 270 and 399 URLs verbatim.
- `main()` passes title `260: DueCare RAG Comparison`,
  `is_private=False`, and the final-print args. `write_notebook`
  gained the same two keyword-only args; ADVERSARIAL_CELLS and
  FC_CELLS call sites unchanged.

### 299 and 399 recaps

Only `recap` and `key_points` on the two target SECTIONS entries were
touched. The other seven entries (099, 199, 499, 599, 699, 799, 899)
stay byte-identical.

- **299**: recap now covers only 110 and 120 as the two-step input-
  discipline pipeline (dropped the stale 130 mention). 5 refreshed
  `key_points` on curation, remix strategies, provenance, the BEST /
  WORST anchor reuse in 250, and legibility.
- **399**: recap walks the eight-notebook arc 31b / 31c delivered
  (130 corpus, 200 cross-domain, 210 / 220 OSS, 230 Mistral, 240
  frontier, 250 anchored, 260 RAG, 270 generations). 6 refreshed
  `key_points` on 220 on-device wins, 240 actionability gap, 250
  anchored grading, 260 cheap-guidance finding, 270 domain-specific
  gap.

## 3. Rebuild scope

Shared builders regenerate every sibling:

- `build_grading_notebooks.py` -> 410, 420, **250**, 310, 430.
- `build_showcase_notebooks.py` -> **260**, 300, 400.
- `build_section_conclusion_notebooks.py` -> 099, 199, **299**, **399**,
  499, 599, 699, 799, 899.

Sibling outputs byte-identical to pre-31d. Final
`sync_kaggle_notebook_mirror.py` reported `created=0 updated=0`.

## 4. Validation results

```
scripts/validate_notebooks.py              -> 42 notebooks OK
scripts/_validate_210_adversarial.py       -> ALL CHECKS PASSED
scripts/_validate_220_adversarial.py       -> ALL CHECKS PASSED
scripts/_validate_230_adversarial.py       -> ALL CHECKS PASSED
scripts/_validate_240_adversarial.py       -> ALL CHECKS PASSED
scripts/_validate_270_adversarial.py       -> ALL CHECKS PASSED
```

42 / 42 green every run; 5 adversarial validators still pass without
change.

## 5. Push-ready shared-builder queue

31e should push in this exact order:

1. `taylorsamarel/duecare-250-comparative-grading` (update).
2. `taylorsamarel/duecare-260-rag-comparison` (update; GPU kernel).
3. `taylorsamarel/duecare-baseline-text-evaluation-framework-conclusion`
   (first-time create via `PUBLIC_SLUG_OVERRIDES["299"]`).
4. `taylorsamarel/duecare-baseline-text-comparisons-conclusion` (first-
   time create via `PUBLIC_SLUG_OVERRIDES["399"]`).

The 230 / 240 / 270 dedicated batch from 31c stays push-ready; 250 /
260 join it; 299 / 399 add the first-time-create pair.

## 6. Remaining shared risks

- Grading siblings (410, 420, 310, 430) still pre-canonical (em-dash
  H1, pseudo-table, "Privacy is non-negotiable" footer). Next pass.
- Showcase siblings (300, 400) same story.
- 600 Results Dashboard still has no builder.
- `kaggle_live_slug_map.json` nulls refresh after 31e publishes.

## 7. Inputs for 31e

Publish batch layout:

1. Updates: 230, 240, 270 (31c-canonical dedicated).
2. Updates: 250, 260 (31d-canonical shared).
3. First-time creates via fallback slugs: 299, 399.
4. Optional: rebuild 000 / 005 so their section-map cross-links pick
   up the refreshed 299 / 399 recaps.

Publish order stays dedicated-updates -> shared-updates -> shared-
creates so the validator gate and cross-link targets remain consistent.
