# DueCare Checkpoint — 2026-04-18

Current verified state of the DueCare submission for the Gemma 4 Good Hackathon.

## Verified now

- `python scripts/verify_kaggle_urls.py` reports `All 76 notebooks resolve.` Public Kaggle reachability is green across the tracked suite.
- `python scripts/validate_notebooks.py` reports `Validated 76 notebooks successfully.` The full tracked suite passes the structural notebook gate.
- The shared navigation layer was refreshed after the slug-map repair: `000`, `005`, `099`, and `199` were rebuilt so they no longer point at dead public URLs.
- `scripts/_push_pending_playgrounds.sh` no longer embeds a plaintext Kaggle token; it requires external credentials and delegates to `scripts/publish_kaggle.py`.

## What changed earlier today (first half of 2026-04-18)

- Reconciled repo truth against the live public layer instead of trusting older checkpoint claims.
- Updated `scripts/_public_slugs.py` so the live public slug map matches actual Kaggle URLs for the notebooks whose live slug deviates from the local default, including `110`, `181`-`189`, `250`, `260`, `300`, `400`, `420`, and `500`.
- Rebuilt `notebooks/000_index.ipynb`, `notebooks/005_glossary.ipynb`, `notebooks/099_*.ipynb`, and `notebooks/199_*.ipynb` from source after the slug-map correction.
- Extended the suite: 15 new builders (015 Background Literature, 020 Current Events, 102 E2B Baseline, 105 Prompt Corpus Introduction, 140 Evaluation Mechanics, 165 Thinking-Budget Sweep, 175 Temperature Sweep, 190 RAG Retrieval Inspector, 245 Gemini API Comparison, 335 Attack Vector Inspector, 460 Citation Verifier, 525 Uncensored Grade Generator, 527 Uncensored Rubric Generator, 540 Fine-tune Delta Visualizer, 550 NGO Partner Survey Pipeline).
- Introduced the shared `canonical_hero_banner` helper in `scripts/_canonical_notebook.py`; 005, 010, 015, 020, and 100 now use the same header surface as the 099-band section-conclusion notebooks.

## Cleanup pass (second half of 2026-04-18)

Archived, not deleted, to `_archive/`:

- **30+ one-off maintenance scripts** moved to `_archive/scripts_one_off_2026-04/` with a README cataloguing why each was retired. Includes `align_kaggle_kernel_metadata.py`, `align_metadata_from_push_log.py`, `align_metadata_to_slug_map.py`, `normalize_canonical_slugs.py`, the `push_all_*` family, `update_builders_to_canonical.py`, the seven `implement_*.py` scaffolders, `reclassify_nb00_with_v3.py`, `generate_forge.py`, and six root-level `_inject_*.py` / `_align_titles.py` / `_audit_kernels.py` one-offs. Also the three root audit dumps (`_audit_results.json`, `_duecare_live.txt`, `_url_diff.txt`).
- **Four stale planning docs** (`notebook_renumbering_plan.md`, `the_forge.md`, `copilot_review_prompt.md`, `publishing_plan_jailbreak_family.md`) and thirteen review-report artifacts under `docs/review/` moved to `_archive/docs_2026-04/` (the `docs/review/` directory is now empty and removed).
- **Historian workflow outputs** under `reports/` plus four generated HTML viewers under `data/` relocated to `_archive/reports_2026-04/` and `_archive/data_generated_2026-04/`. The empty `reports/` and `data/full_evaluation/` directories were removed.
- **Historical prompt-ladder drafts** 06 through 34 moved to `_archive/docs_2026-04/prompts/`. The five band-scoped review prompts (`_shared_discipline.md`, `README.md`, `01`-`05`) remain in `docs/prompts/`.
- **One orphan notebook** (`notebooks/forge_kaggle_submission.ipynb`, pre-renumber capstone draft) moved to `_archive/notebooks_2026-04/`.
- **One orphan test** (`tests/unit/test_ingest_google_drive_reference_material.py`) moved to `_archive/tests_2026-04/` after its source script was archived.
- Dead contradictions removed from `CLAUDE.md`: stray `forge.*` package-namespace claim, `src/ (to be built)` line (superseded by active `src/demo/`), pre-renumber builder commands (`build_notebook_00.py` / `00a` / `00b`), and the 2026-04-10 "Open questions" block (now "Resolved decisions").
- Dead `the_forge.md` pointers in `docs/project_status.md` and `docs/claude_code_integration.md` redirected to `docs/architecture.md` / `docs/project_phases.md`.

## Publication state

- All 76 tracked notebook URLs are publicly reachable on Kaggle, except for the pending-publication slots tracked in `UNPUBLISHED_IDS` inside `scripts/_public_slugs.py`.
- The earlier "blocked on daily new-kernel cap" state for `150`, `155`, `160`, `170`, `180`, `199`, and the `181`-`189` jailbreak band is partially cleared; remaining gaps are reported by `UNPUBLISHED_IDS`.
- The old push-failure inventory from earlier in the day is superseded and should not be used as current truth.

## Important distinction

Public reachability is green, but that does not prove every GPU or API-heavy notebook has been executed end to end on Kaggle with the latest build. The current repo gates prove:

- the notebooks exist,
- their public URLs resolve,
- their metadata is aligned,
- their local structure passes validation.

They do not yet prove that every runtime path has been exercised successfully with live model loads, live hosted endpoints, or live attached Kaggle secrets.

## Remaining high-value work

### P0

1. Run the Phase 3 improvement spine end to end: `520` / `525` / `527` / `550` into `530`, then `540`. This is still the most important `real, not faked` gap.
2. Re-verify the live public demo surface against the current package version and current notebook story.
3. Record the public 3-minute video and finalize the writeup so they match the now-live 76-notebook suite.

### P1

1. Execute live Kaggle runtime validation on the most credibility-sensitive notebooks: `100`, `150`, `155`, `160`, `170`, `180`, `183`, `185`-`189`, `245`, `525`, `527`, `530`, `540`, and `550`.
2. Confirm `100` no longer hits the earlier `KernelWorkerStatus.ERROR` failure mode on the current build content.
3. Validate that the uncensored-generator fallback path (`183` / `525` / `527`) behaves correctly on a real T4 with the required artifact bundle present.

### P2

1. Finish the publication story for the `660`-`695` Deployment Applications band so every tracked URL is live, not just structurally validated.
2. Close the remaining Kaggle "Notebook not found" create-time failures for first-time pushes of certain Free Form Exploration slugs; the private-draft orphans at `duecare-15N-*`, `duecare-16N-*`, `duecare-17N-*`, and `duecare-18N-*` can only be cleaned via the Kaggle UI.

## Security note

- `scripts/_push_pending_playgrounds.sh` was sanitized in the first pass and remains credential-free.
- A separate local-only credential risk exists in `.claude/settings.local.json` (hardcoded Kaggle credentials); that file is not tracked by git and was not auto-edited here because it is user-local tool configuration rather than repository source of truth. Rotate/remove those credentials separately.

## Recommended audit commands

Use these as the current quick truth set before any future publish wave:

```bash
python scripts/verify_kaggle_urls.py
python scripts/validate_notebooks.py
```

If both are green, the next bottleneck is runtime evidence, not notebook publication hygiene.

## Hackathon checklist

- [x] 76 tracked Kaggle kernels with structurally valid metadata.
- [x] Shared navigation layer (`000`, `005`, `099`, `199`) rebuilt against the current slug map.
- [x] `_push_pending_playgrounds.sh` free of plaintext tokens.
- [x] Cleanup pass: 60+ files archived under `_archive/` with per-directory READMEs.
- [x] CLAUDE.md contradictions resolved.
- [ ] Phase 3 spine end-to-end run landed.
- [ ] Public 3-minute video recorded.
- [ ] Live public demo surface re-verified.
