# 28: DueCare confirmed detailed action plan

Date captured: 2026-04-16
Derived from:

- `docs/prompts/26_suite_status_snapshot.md`
- `docs/prompts/27_next_steps_action_plan.md`

Audience: Claude Code or a human engineer continuing the work.

Use this file instead of `27_next_steps_action_plan.md` when resuming.
It keeps the same overall order but tightens the commands, replaces
Unix-only paths with Windows-safe commands, removes hardcoded secrets,
and calls out two important repo-shape facts:

1. `000 Index` is already live according to `26`, so it is **not** in
   the first retry queue unless a slug-override edit forces a rebuild.
2. `610 Submission Walkthrough` still appears to be sourced from
   `scripts/build_kaggle_notebooks.py`, and no dedicated `600 Results
   Dashboard` builder was found during this review. Treat `600` as a
   source-of-truth gap to resolve before prompt `22` work.

## 0. Global conventions for every section

Run this setup block once at the start of a terminal session and reuse
its variables in every later command.

```powershell
$repo = "C:\Users\amare\OneDrive\Documents\gemma4_comp"
$py = "c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe"
$logsRoot = Join-Path $env:TEMP "duecare_kaggle_logs"

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"

if (-not $env:KAGGLE_API_TOKEN) {
    throw "Set KAGGLE_API_TOKEN in the environment before any Kaggle push or status check. Do not hardcode secrets into repo files or notes."
}

New-Item -ItemType Directory -Force -Path $logsRoot | Out-Null
```

Execution invariants:

- Edit source-of-truth builders, not generated notebook JSON.
- Rebuild only after the builder edit is complete.
- After every rebuild, verify both `notebooks/` and the matching
  `kaggle/kernels/` copy changed together.
- Do not move past a section until its gate is green.
- If a shared builder regresses a sibling notebook, fix the shared
  builder and rebuild again. Do not hand-edit the sibling `.ipynb`.

## A. Publish the current push queue when the Kaggle cap resets

### A1. Confirm the cap is clear

Use an already-live kernel as the cheapest probe.

```powershell
kaggle kernels status taylorsamarel/duecare-gemma-vs-oss-comparison
```

Expected result: `COMPLETE`.

Stop rules:

- If the command returns `429`, stop immediately and retry the whole
  section later.
- If the command returns anything other than `COMPLETE` or `RUNNING`, do
  not push anything until that status is understood.

### A2. Push in this exact order

`000` is already live per `26`, so the first retry queue is the five
cap-blocked kernels from the status snapshot.

```powershell
kaggle kernels push -p kaggle/kernels/duecare_220_ollama_cloud_comparison
kaggle kernels push -p kaggle/kernels/duecare_130_prompt_corpus_exploration
kaggle kernels push -p kaggle/kernels/duecare_399_baseline_text_comparisons_conclusion
kaggle kernels push -p kaggle/kernels/duecare_299_baseline_text_evaluation_framework_conclusion
kaggle kernels push -p kaggle/kernels/duecare_005_glossary
```

Do not insert other pushes between these five.

### A3. Handle `Notebook not found` correctly

If `130`, `220`, or `399` return `Notebook not found` twice in a row:

1. Change only the affected builder's `KERNEL_ID` to the title-derived
   slug Kaggle actually accepts. Drop the `NNN-` prefix from the slug.
   Keep the canonical notebook title unchanged.
2. Rebuild the affected builder.
3. Update `PUBLIC_SLUG_OVERRIDES` in all three copies:
   - `scripts/build_index_notebook.py`
   - `scripts/build_notebook_005_glossary.py`
   - `scripts/build_section_conclusion_notebooks.py`
4. Rebuild the index, glossary, and all nine section conclusions.
5. Retry the failed push once.

Rebuild commands for override drift:

```powershell
& $py scripts/build_index_notebook.py
& $py scripts/build_notebook_005_glossary.py
& $py scripts/build_section_conclusion_notebooks.py
```

Only re-push `000` if step A3 changed overrides or index content.

### A4. Confirm each kernel runs

```powershell
kaggle kernels status taylorsamarel/220-duecare-gemma-4-vs-6-oss-models-via-ollama-cloud
kaggle kernels status taylorsamarel/130-duecare-prompt-corpus-exploration
kaggle kernels status taylorsamarel/399-duecare-baseline-text-comparisons-conclusion
kaggle kernels status taylorsamarel/299-duecare-baseline-text-evaluation-framework-conclusion
kaggle kernels status taylorsamarel/005-duecare-glossary-and-reading-map
```

If any returns `ERROR`, fetch logs to a Windows-safe directory:

```powershell
$slug = "taylorsamarel/220-duecare-gemma-4-vs-6-oss-models-via-ollama-cloud"
$outDir = Join-Path $logsRoot ($slug -replace "/", "__")
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
kaggle kernels output $slug -p $outDir
```

Gate to leave section A:

- All push-ready kernels above are either `COMPLETE` or the first
  failing cell is diagnosed and assigned to the next edit batch.

Important 005 slug-alignment note:

- Local kernel metadata for `005` already uses
   `taylorsamarel/005-duecare-glossary-and-reading-map`.
- `scripts/build_notebook_010_quickstart.py` already links to that
   title-derived slug.
- Two files still appear to assume the older short slug
   `duecare-005-glossary`:
   - `scripts/build_index_notebook.py`
   - `scripts/build_notebook_130_prompt_corpus_exploration.py`
- After the first successful `005` push, align those references before
   relying on glossary cross-links as stable live URLs.

## B. Unblock the validator baseline: get `42 of 42 OK`

Target builders:

- `scripts/build_notebook_150_free_form_gemma_playground.py`
- `scripts/build_notebook_155_tool_calling_playground.py`
- `scripts/build_notebook_160_image_processing_playground.py`

Required change in each builder:

- Add one explicit final summary code cell near the end.
- The final print must be URL-bearing or at least notebook-bearing and
  must not rely only on the hardener default.
- Handoff targets:
  - `150` -> `155` and `100`
  - `155` -> `160` and `199`
  - `160` -> `199` and `200`

Rebuild commands:

```powershell
& $py scripts/build_notebook_150_free_form_gemma_playground.py
& $py scripts/build_notebook_155_tool_calling_playground.py
& $py scripts/build_notebook_160_image_processing_playground.py
```

Validation gate:

```powershell
& $py scripts/validate_notebooks.py
```

Expected result: `42 of 42 OK`.

Stop rule:

- Do not start section C until this gate is green. If other failures
  appear, list them explicitly and fix them before moving on.

## C. Canonicalize the remaining dedicated 200-band notebooks: 230, 240, 270

Target builders:

- `scripts/build_notebook_230_mistral_family_comparison.py`
- `scripts/build_notebook_240_openrouter_frontier_comparison.py`
- `scripts/build_notebook_270_gemma_generations.py`

Use `210` and `220` as the template. The required structural target is:

1. Canonical HTML header with Inputs, Outputs, Prerequisites, Runtime,
   and Pipeline position.
2. Remove the em-dash H1 and the old `| | |` markdown pseudo-table.
3. Remove the `Privacy is non-negotiable` footer from these comparison
   notebooks.
4. Cross-link back to `100` for the rubric and baseline context.
5. Keep only the hardener-managed install path. Delete legacy
   wheel-walk or duplicate install cells.
6. Use `SAFETY_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())` when the
   notebook derives radar dimensions from weights.
7. Use `_hex_to_rgba(...)` for radar fillcolors.
   - `230` and `240` already appear to have this drift fixed.
   - Verify `270`; add it if still missing.
8. Add HTML troubleshooting tables.
9. Replace the hardener default summary with a notebook-specific,
   URL-bearing final print that hands off forward and to `399`.

`270` has one extra requirement:

- Load `gemma_baseline_findings.json` with a `PUBLISHED_BASELINE`
  fallback so the Gemma 3 band is derived from real findings instead of
  placeholders.

Create these validator files by mirroring `scripts/_validate_220_adversarial.py`:

- `scripts/_validate_230_adversarial.py`
- `scripts/_validate_240_adversarial.py`
- `scripts/_validate_270_adversarial.py`

Rebuild and validate in this order:

```powershell
& $py scripts/build_notebook_230_mistral_family_comparison.py
& $py scripts/build_notebook_240_openrouter_frontier_comparison.py
& $py scripts/build_notebook_270_gemma_generations.py

& $py scripts/_validate_220_adversarial.py
& $py scripts/_validate_230_adversarial.py
& $py scripts/_validate_240_adversarial.py
& $py scripts/_validate_270_adversarial.py
& $py scripts/validate_notebooks.py
```

Push batch after the gate is green:

```powershell
kaggle kernels push -p kaggle/kernels/duecare_230_mistral_family_comparison
kaggle kernels push -p kaggle/kernels/duecare_240_openrouter_frontier_comparison
kaggle kernels push -p kaggle/kernels/duecare_270_gemma_generations
```

## D. Canonicalize `250` inside the shared grading builder

Source of truth:

- `scripts/build_grading_notebooks.py`

Shared-builder blast radius:

- `250`, `310`, `410`, `420`, `430`

Action discipline:

1. Read the `NB11_CELLS` block first.
2. Do not edit `NB09_CELLS`, `NB10_CELLS`, `NB12_CELLS`, or
   `NB13_CELLS` unless the shared helper extraction in section H makes
   it unavoidable.
3. Apply the same canonical 9-fix pattern used in section C.

Rebuild and validate:

```powershell
& $py scripts/build_grading_notebooks.py
& $py scripts/sync_kaggle_notebook_mirror.py
& $py scripts/validate_notebooks.py
```

Gate:

- `42 of 42 OK`
- No unplanned regression in emitted `310`, `410`, `420`, or `430`

Push only `250` in this block:

```powershell
kaggle kernels push -p kaggle/kernels/duecare_250_comparative_grading
```

## E. Canonicalize `260` inside the shared showcase builder

Source of truth:

- `scripts/build_showcase_notebooks.py`

Shared-builder blast radius:

- `260`, `300`, `400`, `500`

Action discipline:

1. Read the `RAG_CELLS` block first.
2. Do not edit `ADVERSARIAL_CELLS`, `FC_CELLS`, or `SWARM_CELLS`
   unless the shared helper extraction in section H makes it necessary.
3. Apply the same canonical 9-fix pattern used in section C.

Rebuild and validate:

```powershell
& $py scripts/build_showcase_notebooks.py
& $py scripts/sync_kaggle_notebook_mirror.py
& $py scripts/validate_notebooks.py
```

Push only `260` after the gate is green:

```powershell
kaggle kernels push -p kaggle/kernels/duecare_260_rag_comparison
```

## F. Finalize `399` only after C, D, and E are stable

Important refinement relative to `27`:

- `399` already has a substantial rewrite per `26`.
- Treat `399` as provisionally modernized.
- Only edit it again if sections C, D, or E change the actual story,
  the live slugs, or the section handoff.

Source of truth:

- `scripts/build_section_conclusion_notebooks.py`

Tasks:

1. Reread the `399` entry inside `SECTIONS`.
2. Confirm it still names the real comparison arc after `230`, `240`,
   `250`, `260`, `270` land.
3. Confirm it still references `130` as the input map if that remains
   true.
4. Confirm the handoff to `300` is still the correct next step.

Rebuild and push:

```powershell
& $py scripts/build_section_conclusion_notebooks.py
kaggle kernels push -p kaggle/kernels/duecare_399_baseline_text_comparisons_conclusion
```

## G. Move into prompts 18 through 22 in strict order

Run one prompt at a time. Do not overlap prompt scopes in the same edit
pass unless the only shared change is a helper introduced in section H.

### Prompt 18

Files and ownership:

- `300` -> `scripts/build_showcase_notebooks.py` (`ADVERSARIAL_CELLS`)
- `400` -> `scripts/build_showcase_notebooks.py` (`FC_CELLS`)
- `410` -> `scripts/build_grading_notebooks.py` (`NB09_CELLS`)
- `420` -> `scripts/build_grading_notebooks.py` (`NB10_CELLS`)
- `499` -> `scripts/build_section_conclusion_notebooks.py`

### Prompt 19

Files and ownership:

- `310` -> `scripts/build_grading_notebooks.py` (`NB12_CELLS`)
- `430` -> `scripts/build_grading_notebooks.py` (`NB13_CELLS`)
- `440` -> `scripts/build_notebook_440_per_prompt_rubric_generator.py`
- `699` -> `scripts/build_section_conclusion_notebooks.py`

### Prompt 20

Files and ownership:

- `320` -> `scripts/build_notebook_320_supergemma_safety_gap.py`
- `450` -> `scripts/build_notebook_450_contextual_worst_response_judge.py`
- `799` -> `scripts/build_section_conclusion_notebooks.py`

### Prompt 21

Files and ownership:

- `500` -> `scripts/build_showcase_notebooks.py` (`SWARM_CELLS`)
- `510` -> `scripts/build_notebook_510_phase2_model_comparison.py`
- `520` -> `scripts/build_notebook_520_phase3_curriculum_builder.py`
- `530` -> `scripts/build_notebook_530_phase3_unsloth_finetune.py`
- `599` -> `scripts/build_section_conclusion_notebooks.py`

### Prompt 22

Files and ownership:

- `610` -> `scripts/build_kaggle_notebooks.py` (`SUBMISSION_CELLS`)
- `899` -> `scripts/build_section_conclusion_notebooks.py`

Important source-of-truth gap:

- No dedicated `scripts/build_notebook_600_*.py` file was found.
- No `600 Results Dashboard` source block was found in
  `scripts/build_kaggle_notebooks.py` during this review.
- Before touching prompt `22`, resolve `600` by either locating its true
  generator or creating a dedicated source-of-truth builder for it.
- Do not hand-edit `notebooks/600_results_dashboard.ipynb` or
  `kaggle/kernels/duecare_600_results_dashboard/600_results_dashboard.ipynb`.

Per-prompt gate:

```powershell
& $py scripts/validate_notebooks.py
```

Only push the notebooks in the prompt you just finished.

## H. Cross-section consistency work

Do this in parallel in calendar time, not in the same speculative edit
burst as a big shared-builder rewrite.

### H1. Centralize slug overrides

Create:

- `scripts/_public_slugs.py`

Export:

- `PUBLIC_SLUG_OVERRIDES`
- `public_slug(notebook_id, default_slug)`

Replace local copies in:

- `scripts/build_index_notebook.py`
- `scripts/build_notebook_005_glossary.py`
- `scripts/build_section_conclusion_notebooks.py`

Rebuild after migration:

```powershell
& $py scripts/build_index_notebook.py
& $py scripts/build_notebook_005_glossary.py
& $py scripts/build_section_conclusion_notebooks.py
& $py scripts/validate_notebooks.py
```

### H2. Centralize the canonical notebook pattern

Create:

- `scripts/_canonical_notebook.py`

Extract helpers for:

- canonical HTML headers
- troubleshooting tables
- URL-bearing final prints
- `hex_to_rgba(...)`
- baseline-summary loading with fallback

First migration targets:

- `scripts/build_notebook_210_oss_model_comparison.py`
- `scripts/build_notebook_220_ollama_cloud_comparison.py`
- `scripts/build_notebook_130_prompt_corpus_exploration.py`

Only move later builders after the first three stay green.

### H3. Audit install pins

Meta package pin must remain limited to:

- `000`
- `005`
- `010`
- `200`
- `500`
- `610`

Everything else should use split-package pins in
`scripts/notebook_hardening_utils.py`.

Audit command:

```powershell
rg "duecare-llm==0\.1\.0|duecare-llm-core==0\.1\.0|duecare-llm-domains==0\.1\.0|duecare-llm-tasks==0\.1\.0" scripts/notebook_hardening_utils.py
```

## I. `140` evaluation-mechanics notebook remains conditional

Do not create `140` yet.

Revisit only after all three are true:

1. `399` is live.
2. `250` has been rewritten in canonical style.
3. The narrative still feels abrupt between `130` and `250` or `430`.

Create `140` only if at least one of these remains true after that:

- Judges can inspect the corpus in `130` but still cannot see how the
  deterministic scoring step works.
- `250` still starts too deep in grading without a bridge notebook.
- `430` remains too advanced to serve as the first scoring explainer.

If triggered, touch at minimum:

- `scripts/build_notebook_140_evaluation_mechanics.py`
- `scripts/notebook_hardening_utils.py`
- `scripts/build_index_notebook.py`
- `scripts/build_section_conclusion_notebooks.py`
- `scripts/build_notebook_005_glossary.py`
- optionally `scripts/_validate_140_adversarial.py`

Gate if created:

- builder emits notebook and kernel copy
- `scripts/validate_notebooks.py` stays green
- `299` recap and the index order reflect `110 -> 120 -> 130 -> 140 -> 299`

## J. Submission-path hardening

After sections C through G land:

1. Rebuild `610` from `scripts/build_kaggle_notebooks.py` so the
   submission notebook points at the live canonical comparison URLs.
2. Resolve the `600` source-of-truth gap before rewriting it.
3. Run these pre-submission checks:

```powershell
& $py scripts/verify_kaggle_urls.py
git check-ignore -v configs/duecare/domains/trafficking/seed_prompts.jsonl
& $py scripts/validate_notebooks.py
```

Expected state:

- All public Kaggle URLs return HTTP 200.
- The proprietary full prompt corpus remains ignored.
- Validator reports `42 of 42 OK`, or `43 of 43 OK` only if `140` was
  deliberately added.

## K. Video and writeup artifacts

1. Capture `130` screenshots only from a run with
   `taylorsamarel/duecare-trafficking-prompts` attached.
2. Update `docs/writeup_draft.md` to name `130` as the input map and to
   quote real numbers from generated artifacts, not placeholders.
   Minimum cited notebooks: `100`, `210`, `220`, `270`, `320`, `530`.
3. Update `docs/video_script.md` to open with a named composite worker
   and close with named NGOs: Polaris, IJM, POEA, BP2MI, HRD Nepal.

## L. Release prep

Only after A through K are green:

1. Tag `v0.1.0`.
2. Publish all seven PyPI packages at the same version via CI.
3. Publish the HF Hub model with model card and deployment artifacts.
4. Confirm the public FastAPI demo endpoint is reachable.
5. Submit on Kaggle before `2026-05-18`.

## M. Priority summary

- Immediate: `A`, then `B`.
- Next engineering block: `C`, `D`, `E`, then `F`.
- After the 200 band is closed: `G`, one prompt at a time.
- In parallel but in separate safe commits: `H`.
- Conditional only: `I`.
- Final submission hardening: `J`, `K`, `L`.