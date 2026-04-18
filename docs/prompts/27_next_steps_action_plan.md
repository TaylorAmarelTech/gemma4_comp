# 27: DueCare next steps and specific actions

Date captured: 2026-04-16
Source of truth: `docs/prompts/26_suite_status_snapshot.md`
Audience: Claude Code or a human engineer continuing the work.

Actions below are ordered so an earlier block does not depend on a
later block. Each action names exact file paths, exact CLI commands,
and the gate that must pass before moving on.

## A. Publish the push queue as soon as the Kaggle cap resets

Actions to perform in one push session.

1. Confirm the cap is clear.

   ```
   $env:PYTHONIOENCODING = "utf-8"
   $env:KAGGLE_API_TOKEN = "KGAT_cae9959f7adc60ceb6d52746bd3fd807"
   kaggle kernels status taylorsamarel/duecare-gemma-vs-oss-comparison
   ```

   Expect `COMPLETE`. If it returns `429`, stop and retry in an hour.

2. Push in this exact order.

   ```
   kaggle kernels push -p kaggle/kernels/duecare_220_ollama_cloud_comparison
   kaggle kernels push -p kaggle/kernels/duecare_130_prompt_corpus_exploration
   kaggle kernels push -p kaggle/kernels/duecare_399_baseline_text_comparisons_conclusion
   kaggle kernels push -p kaggle/kernels/duecare_299_baseline_text_evaluation_framework_conclusion
   kaggle kernels push -p kaggle/kernels/duecare_005_glossary
   ```

3. If `130`, `220`, or `399` return `Notebook not found` twice in a
   row, adopt the title-derived slug Kaggle auto-creates.

   - Edit `KERNEL_ID` in each affected builder, drop the `NNN-`
     prefix, keep the canonical `NNN: DueCare ...` title.
   - Rebuild the builder.
   - Retry the push once.
   - Record the new slug in `PUBLIC_SLUG_OVERRIDES` across all three
     copies:
     - `scripts/build_index_notebook.py`
     - `scripts/build_notebook_005_glossary.py`
     - `scripts/build_section_conclusion_notebooks.py`
   - Rebuild the index, glossary, and all nine conclusion notebooks so
     their cross-links point at the live slug.

4. Confirm each kernel runs.

   ```
   kaggle kernels status taylorsamarel/220-duecare-gemma-4-vs-6-oss-models-via-ollama-cloud
   kaggle kernels status taylorsamarel/130-duecare-prompt-corpus-exploration
   kaggle kernels status taylorsamarel/399-duecare-baseline-text-comparisons-conclusion
   ```

   If any reports `ERROR`, fetch the log with
   `kaggle kernels output <slug> -p /tmp/<slug>` and fix the first
   failing cell before any further canonical rewrites.

## B. Unblock the validator baseline (42 of 42 OK)

The three playground notebooks block a clean validator sweep and a
clean writeup claim.

1. Read each builder.

   - `scripts/build_notebook_150_free_form_gemma_playground.py`
   - `scripts/build_notebook_155_tool_calling_playground.py`
   - `scripts/build_notebook_160_image_processing_playground.py`

2. Add a single `print(...)` final summary code cell to each, using
   the pattern already used in 210 and 220:

   - `150`: handoff to `155` and `100`.
   - `155`: handoff to `160` and `199`.
   - `160`: handoff to `199` and `200`.

3. Rebuild each notebook.

4. Run the gate.

   ```
   python scripts/validate_notebooks.py
   ```

   Expect `42 of 42 OK`.

5. Commit. Do not proceed to section C until this gate is green.

## C. Canonicalize the 200 band: 230, 240, 270

Each is a dedicated builder. The plotly fill drift is already fixed.
This step finishes the canonical rewrite so prose, header, install,
and final print match 210 and 220.

1. For each of:

   - `scripts/build_notebook_230_mistral_family_comparison.py`
   - `scripts/build_notebook_240_openrouter_frontier_comparison.py`
   - `scripts/build_notebook_270_gemma_generations.py`

   apply the same 9 structural fixes landed in 210 and 220:

   1. Canonical HTML header block with Inputs / Outputs /
      Prerequisites / Runtime / Pipeline position table.
   2. Remove em-dash H1 and `| | |` pseudo-table.
   3. Remove `Privacy is non-negotiable` footer.
   4. Cross-link to 100 rubric.
   5. Single hardener install cell. Delete any legacy wheel-walk.
   6. Shared `SAFETY_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())`.
   7. `_hex_to_rgba` helper at the top of the radar cell (already
      landed; keep).
   8. HTML troubleshooting table at the end.
   9. URL-bearing final print replacing the hardener default; hand off
      to the next notebook and to 399.

2. For `270` specifically, load
   `gemma_baseline_findings.json` with a `PUBLISHED_BASELINE` fallback
   so the V3 band reflects real numbers, not hardcoded placeholders.

3. Write adversarial validators next to the existing pair:

   - `scripts/_validate_230_adversarial.py`
   - `scripts/_validate_240_adversarial.py`
   - `scripts/_validate_270_adversarial.py`

   Each should mirror `scripts/_validate_220_adversarial.py` with the
   correct metadata id, cross-links, and final-print marker.

4. Rebuild, run all four validators, run
   `python scripts/validate_notebooks.py`.

5. Push as a single batch.

   ```
   kaggle kernels push -p kaggle/kernels/duecare_230_mistral_family_comparison
   kaggle kernels push -p kaggle/kernels/duecare_240_openrouter_frontier_comparison
   kaggle kernels push -p kaggle/kernels/duecare_270_gemma_generations
   ```

## D. Canonicalize 250 inside the shared grading builder

`scripts/build_grading_notebooks.py` emits `250`, `310`, `410`, `420`,
and `430`. Editing it touches five notebooks at once.

1. Read the `NB11_CELLS` block only. Leave the other four alone.

2. Apply the 9 structural fixes from section C to `NB11_CELLS`.

3. Run the full builder so every emitted file is regenerated:

   ```
   python scripts/build_grading_notebooks.py
   ```

4. Sync mirrors and run the validator gate.

   ```
   python scripts/sync_kaggle_notebook_mirror.py
   python scripts/validate_notebooks.py
   ```

   Expect 42 of 42 OK. If a sibling regressed, revert the sibling
   cells block and try again.

5. Push only `250` this cycle.

   ```
   kaggle kernels push -p kaggle/kernels/duecare_250_comparative_grading
   ```

## E. Canonicalize 260 inside the shared showcase builder

`scripts/build_showcase_notebooks.py` emits `260`, `300`, `400`, and
`500`. GPU kernel.

1. Read the `RAG_CELLS` block only.

2. Apply the 9 structural fixes to `RAG_CELLS`.

3. Build and sync.

   ```
   python scripts/build_showcase_notebooks.py
   python scripts/sync_kaggle_notebook_mirror.py
   python scripts/validate_notebooks.py
   ```

4. Push only `260` this cycle.

## F. Rewrite 399, then close the 200 band

1. After sections C, D, E have landed, reread
   `scripts/build_section_conclusion_notebooks.py` and confirm the
   rewritten 399 recap still reflects the actual notebooks (it
   already names 130, 200, 210, 220, 230, 240, 270).

2. If any of C, D, E changed the story, update the 399 entry in
   `SECTIONS`.

3. Rebuild all conclusions. Push only 399.

   ```
   python scripts/build_section_conclusion_notebooks.py
   kaggle kernels push -p kaggle/kernels/duecare_399_baseline_text_comparisons_conclusion
   ```

## G. Move into prompts 18 through 22

Execute one prompt at a time. Batch pushes to respect the Kaggle daily
cap (approximately 8 pushes per day).

1. Prompt 18 (`docs/prompts/18_claudecode_cleanup_300_400_410_420_499.md`):

   - `300` inside `scripts/build_showcase_notebooks.py`
     (`ADVERSARIAL_CELLS`).
   - `400` inside `scripts/build_showcase_notebooks.py` (`FC_CELLS`).
   - `410` inside `scripts/build_grading_notebooks.py` (`NB09_CELLS`).
   - `420` inside `scripts/build_grading_notebooks.py` (`NB10_CELLS`).
   - `499` inside `scripts/build_section_conclusion_notebooks.py`.

2. Prompt 19 (`docs/prompts/19_claudecode_cleanup_310_430_440_699.md`):

   - `310` inside grading builder (`NB12_CELLS`).
   - `430` inside grading builder (`NB13_CELLS`).
   - `440` dedicated builder.
   - `699` inside conclusions.

3. Prompt 20 (`docs/prompts/20_claudecode_cleanup_320_450_799.md`):

   - `320` inside `scripts/build_notebook_320_supergemma_safety_gap.py`.
   - `450` dedicated builder.
   - `799` inside conclusions.

4. Prompt 21 (`docs/prompts/21_claudecode_cleanup_500_510_520_530_599.md`):

   - `500` inside showcase builder (`SWARM_CELLS`).
   - `510`, `520`, `530` (verify which builder owns each before edit).
   - `599` inside conclusions.

5. Prompt 22 (`docs/prompts/22_claudecode_cleanup_600_610_899.md`):

   - `600 Results Dashboard`.
   - `610 Submission Walkthrough`.
   - `899` inside conclusions.

   After this step the entire suite should be canonical.

## H. Cross-section consistency work (do in parallel with G)

1. Consolidate `PUBLIC_SLUG_OVERRIDES` into a single module.

   - Create `scripts/_public_slugs.py` exporting `PUBLIC_SLUG_OVERRIDES`
     and a `public_slug(notebook_id, default)` helper.
   - Replace the three local copies in
     `scripts/build_index_notebook.py`,
     `scripts/build_notebook_005_glossary.py`, and
     `scripts/build_section_conclusion_notebooks.py` with imports.
   - Rebuild index, glossary, and conclusions. Validator must stay
     green.

2. Extract the 9-fix canonical pattern into a helper.

   - Create `scripts/_canonical_notebook.py` exposing:
     - `canonical_header(title, rows, reading_order, steps)`.
     - `troubleshooting_table(rows)`.
     - `url_handoff_print(next_url, section_close_url)`.
     - `hex_to_rgba(hex_color, alpha=0.08)`.
     - `load_phase1_baseline_with_fallback(published_summary)`.
   - Migrate 210, 220, 130 to use the helper. Keep both tests green
     after migration.
   - New builders from section G should use the helper from the start.

3. Audit installs.

   - `duecare-llm==0.1.0` meta pin must stay reserved for `000`,
     `005`, `010`, `200`, `500`, `610`.
   - Everything else uses the split pins listed in
     `scripts/notebook_hardening_utils.INSTALL_PACKAGES`.
   - Verify nothing has broadened the meta pin by grepping
     `scripts/notebook_hardening_utils.py`.

## I. 140 evaluation-mechanics notebook

Do not create yet. Revisit after 399 is live and 250 has been
rewritten. If, after that, readers still lack a bridge between the
corpus walk-through in 130 and the scoring machinery in 250 and 430,
create 140 with the same 9-fix pattern and touch:

- `scripts/build_notebook_140_evaluation_mechanics.py` (new).
- `scripts/notebook_hardening_utils.py` (`INSTALL_PACKAGES`,
  `SUMMARY_MESSAGES`).
- `scripts/build_index_notebook.py` (insert between 130 and 299).
- `scripts/build_section_conclusion_notebooks.py` (299 recap).
- `scripts/build_notebook_005_glossary.py` (glossary cross-link).

Do not introduce 140 speculatively; it is a planned conditional.

## J. Submission-path hardening

1. Rebuild `610 Submission Walkthrough` after sections C through G
   land so the walkthrough references the canonical 210, 220, 230,
   240, 270, 399 URLs.

2. Verify the following three claims before submission:

   - Every `PUBLIC_SLUG_OVERRIDES` entry resolves to `HTTP 200`:
     ```
     python scripts/verify_kaggle_urls.py
     ```
   - `configs/duecare/domains/trafficking/seed_prompts.jsonl` is
     gitignored:
     ```
     git check-ignore -v configs/duecare/domains/trafficking/seed_prompts.jsonl
     ```
   - `python scripts/validate_notebooks.py` reports 42 of 42 OK (43
     of 43 if 140 is added).

3. Confirm the meta package installs cleanly on a fresh Kaggle kernel
   by rerunning `610` end to end at least once before submission.

## K. Video and writeup artifacts

1. Generate screenshots for the video from a run that has
   `taylorsamarel/duecare-trafficking-prompts` attached so `130`
   renders the full TAYLOR-001 walk-through with all five grades.

2. Update `docs/writeup_draft.md` to name `130` as the reader's map
   of the inputs, and to quote real numbers from `100`, `210`, `220`,
   `270`, `320`, `530`.

3. Update `docs/video_script.md` opening to lead with a named
   composite worker and close with named NGOs (Polaris, IJM, POEA,
   BP2MI, HRD Nepal).

## L. Release prep

Once A through K land cleanly:

1. Tag `v0.1.0` in git.
2. Publish all 7 PyPI packages at the same version via CI.
3. Publish `TaylorScottAmarel/duecare-gemma-4-e4b-safetyjudge-v0.1.0`
   on HF Hub with model card and GGUF + LiteRT artifacts.
4. Confirm the FastAPI public demo endpoint is reachable.
5. Submit on Kaggle before 2026-05-18.

## Priority order summary

- **Today or tomorrow:** A, B.
- **Next work block:** C, D, E, F.
- **After the 200 band is closed:** G in one-prompt batches.
- **In parallel with G:** H.
- **Conditional:** I.
- **Final week before submission:** J, K, L.
