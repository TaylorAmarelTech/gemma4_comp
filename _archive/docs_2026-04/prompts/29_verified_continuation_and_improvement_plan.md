# 29: DueCare verified continuation and improvement plan

Date captured: 2026-04-16
Derived from:

- `docs/prompts/28_confirmed_detailed_action_plan.md`
- current worktree inspection on 2026-04-16

Audience: Claude Code or a human engineer continuing after a Claude pass
that attempted `28`.

Use this file after `28` has been run once. It does two things `28` did
not do strongly enough:

1. it verifies what actually changed in the repo before trusting any
   notebook as done
2. it moves a small number of shared fixes earlier when they clearly
   reduce repeated cleanup

Verified local facts from this review:

- Current local kernel artifacts already exist for `230`, `240`, `250`,
  `260`, `270`, `299`, `300`, `310`, `320`, and `399`.
- Those emitted artifacts still show multiple pre-canonical patterns
  that `28` was intended to remove: markdown pseudo-tables, notebook-
  local install logic instead of a cleaner hardener-managed structure,
  and older section-handoff language/slugs.
- Therefore, treat those notebook artifacts as draft emissions until the
  owning builders are verified and can reproduce corrected output.

What this file improves relative to `28`:

1. Adds a mandatory post-Claude verification sweep before any new push.
2. Treats builder proof as more important than emitted notebook files.
3. Pulls slug-centralization work earlier if `005`, `130`, `299`, or
   `399` still drift.
4. Pulls the first canonical-helper extraction earlier if it will save
   duplicated work across `230`, `240`, `250`, `260`, `270`, `300`, and
   `310`.
5. Moves the `600` source-of-truth investigation earlier, before the
   closing arc depends on it.

## 0. Global conventions for this post-28 pass

Reuse the same setup block from `28`, plus one extra evidence folder.

```powershell
$repo = "C:\Users\amare\OneDrive\Documents\gemma4_comp"
$py = "c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe"
$logsRoot = Join-Path $env:TEMP "duecare_kaggle_logs"
$proofRoot = Join-Path $logsRoot "post_28_verification"

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"

if (-not $env:KAGGLE_API_TOKEN) {
    throw "Set KAGGLE_API_TOKEN in the environment before Kaggle status checks or pushes."
}

New-Item -ItemType Directory -Force -Path $logsRoot | Out-Null
New-Item -ItemType Directory -Force -Path $proofRoot | Out-Null
```

Execution invariants:

- Do not trust a generated `.ipynb` only because it exists in
  `kaggle/kernels/`.
- A notebook is only "done" when its source-of-truth builder changed,
  the notebook was rebuilt from that source, and validation is green.
- If a shared builder changed, rebuild every notebook in that builder's
  blast radius before judging the result.
- Record evidence after each batch: changed files, rebuild commands,
  validator result, and Kaggle status.

## A. Re-establish truth from the actual repo, not from Claude's summary

### A1. Capture the real delta from the Claude pass

```powershell
git status --short | Tee-Object -FilePath (Join-Path $proofRoot "git_status_short.txt")
git diff --name-only -- scripts notebooks kaggle/kernels docs/prompts | Tee-Object -FilePath (Join-Path $proofRoot "changed_paths.txt")
git diff --name-only -- scripts | Tee-Object -FilePath (Join-Path $proofRoot "changed_scripts.txt")
git diff --name-only -- notebooks kaggle/kernels | Tee-Object -FilePath (Join-Path $proofRoot "changed_notebook_artifacts.txt")
```

Interpretation rule:

- If a notebook changed under `notebooks/` or `kaggle/kernels/` but its
  owning builder did not change, that notebook is not complete.
- If only a shared builder changed, do not inspect one emitted sibling
  in isolation. Rebuild and validate the full blast radius first.

### A2. Use this ownership map to verify source-of-truth coverage

| Notebook | Source of truth | Blast radius |
|---|---|---|
| `230` | `scripts/build_notebook_230_mistral_family_comparison.py` | `230` only |
| `240` | `scripts/build_notebook_240_openrouter_frontier_comparison.py` | `240` only |
| `250` | `scripts/build_grading_notebooks.py` (`NB11_CELLS`) | `250`, `310`, `410`, `420`, `430` |
| `260` | `scripts/build_showcase_notebooks.py` (`RAG_CELLS`) | `260`, `300`, `400`, `500` |
| `270` | `scripts/build_notebook_270_gemma_generations.py` | `270` only |
| `299` | `scripts/build_section_conclusion_notebooks.py` | all section conclusions |
| `300` | `scripts/build_showcase_notebooks.py` (`ADVERSARIAL_CELLS`) | `260`, `300`, `400`, `500` |
| `310` | `scripts/build_grading_notebooks.py` (`NB12_CELLS`) | `250`, `310`, `410`, `420`, `430` |
| `320` | `scripts/build_notebook_320_supergemma_safety_gap.py` | `320` only |
| `399` | `scripts/build_section_conclusion_notebooks.py` | all section conclusions |

Stop rule:

- Do not push any notebook from this list until the matching source
  builder is confirmed changed or deliberately re-edited now.

### A3. Confirm the original A-queue status before re-pushing anything

Ask Kaggle first; do not blindly repeat the queue.

```powershell
kaggle kernels status taylorsamarel/220-duecare-gemma-4-vs-6-oss-models-via-ollama-cloud
kaggle kernels status taylorsamarel/130-duecare-prompt-corpus-exploration
kaggle kernels status taylorsamarel/399-duecare-baseline-text-comparisons-conclusion
kaggle kernels status taylorsamarel/299-duecare-baseline-text-evaluation-framework-conclusion
kaggle kernels status taylorsamarel/005-duecare-glossary-and-reading-map
```

If any returns `ERROR`, fetch logs before editing further:

```powershell
$slug = "taylorsamarel/130-duecare-prompt-corpus-exploration"
$outDir = Join-Path $proofRoot ($slug -replace "/", "__")
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
kaggle kernels output $slug -p $outDir
```

## B. Re-run the hard gates before accepting any draft emission

### B1. Full notebook validator

```powershell
& $py scripts/validate_notebooks.py | Tee-Object -FilePath (Join-Path $proofRoot "validate_notebooks.txt")
```

Expected result: `42 of 42 OK`.

If this is still red, `150`, `155`, and `160` remain the first repair
target exactly as in `28`.

### B2. Targeted comparison validators when present

```powershell
& $py scripts/_validate_220_adversarial.py
if (Test-Path scripts/_validate_230_adversarial.py) { & $py scripts/_validate_230_adversarial.py }
if (Test-Path scripts/_validate_240_adversarial.py) { & $py scripts/_validate_240_adversarial.py }
if (Test-Path scripts/_validate_270_adversarial.py) { & $py scripts/_validate_270_adversarial.py }
```

Gate:

- Every validator file that exists must pass.
- If a validator does not exist for a newly touched notebook, create it
  before publication if the notebook is one of the comparison kernels.

### B3. Re-sync the local mirror after any shared-builder rebuild

```powershell
& $py scripts/sync_kaggle_notebook_mirror.py
```

Only do this after builder-driven rebuilds, not before.

## C. Close the highest-risk gaps first

### C1. If `42 of 42` is still not green, finish the validator baseline now

Do not let flashy 200-band work hide an unresolved structural gate.
Return to the exact `28` section B task:

- `scripts/build_notebook_150_free_form_gemma_playground.py`
- `scripts/build_notebook_155_tool_calling_playground.py`
- `scripts/build_notebook_160_image_processing_playground.py`

These three must end with explicit, notebook-specific final summary code
cells and a green validator run before any more comparison pushes.

### C2. Fix the `005` slug drift as soon as the first successful `005` push exists

This should move earlier than it was in `28` if any of these files are
already being touched in the same pass:

- `scripts/build_index_notebook.py`
- `scripts/build_notebook_130_prompt_corpus_exploration.py`
- `scripts/build_section_conclusion_notebooks.py`

If two or more of those files are changing anyway, do not keep copying
slug overrides locally. Jump directly to section E1 below and
centralize them.

### C3. Resolve the `600` source-of-truth gap before the closing arc depends on it

Do not wait until prompt `22` if the current pass is already touching
section conclusions or submission-path notebooks.

Search now:

```powershell
rg "600_results_dashboard|Results Dashboard|interactive safety evaluation dashboard" scripts kaggle notebooks
```

Decision rule:

- If a real source builder exists, record it in `29`-style notes and use
  it.
- If no builder exists, create a dedicated `scripts/build_notebook_600_*.py`
  source-of-truth file before touching `610`, `799`, `899`, or any final
  writeup copy that depends on `600`.

## D. Canonicalize draft emissions from source, not from emitted notebooks

The current emitted `230`, `240`, `250`, `260`, and `270` artifacts
still look like draft outputs, not finished canonical notebooks.

### D1. `230`, `240`, and `270` still come first

Keep `28` section C as the structural target. Do not invent a new
pattern. Required shape still includes:

1. Canonical HTML header with Inputs, Outputs, Prerequisites, Runtime,
   and Pipeline position.
2. No em-dash H1 and no markdown pseudo-table header block.
3. No `Privacy is non-negotiable` footer in comparison notebooks.
4. Back-link to `100` for rubric and baseline context.
5. Hardener-managed install path only.
6. `SAFETY_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())` when radar
   dimensions derive from weights.
7. `_hex_to_rgba(...)` for radar fill colors.
8. HTML troubleshooting tables.
9. Notebook-specific URL-bearing final print.
10. For `270`, real `gemma_baseline_findings.json` loading with a
    published fallback.

Rebuild and validate in the same order as `28`:

```powershell
& $py scripts/build_notebook_230_mistral_family_comparison.py
& $py scripts/build_notebook_240_openrouter_frontier_comparison.py
& $py scripts/build_notebook_270_gemma_generations.py

& $py scripts/_validate_220_adversarial.py
if (Test-Path scripts/_validate_230_adversarial.py) { & $py scripts/_validate_230_adversarial.py }
if (Test-Path scripts/_validate_240_adversarial.py) { & $py scripts/_validate_240_adversarial.py }
if (Test-Path scripts/_validate_270_adversarial.py) { & $py scripts/_validate_270_adversarial.py }
& $py scripts/validate_notebooks.py
```

Only then push:

```powershell
kaggle kernels push -p kaggle/kernels/duecare_230_mistral_family_comparison
kaggle kernels push -p kaggle/kernels/duecare_240_openrouter_frontier_comparison
kaggle kernels push -p kaggle/kernels/duecare_270_gemma_generations
```

### D2. `250` and `260` stay next, but accept they are not done yet

The emitted outputs currently visible in the worktree still look closer
to their older forms than to the canonical `210`/`220` structure.

So:

- treat `250` and `260` as open work even if a notebook file already
  exists locally
- edit the shared builders, not the emitted notebooks
- rebuild every sibling in the shared-builder blast radius before
  pushing the one target notebook

Re-use the `28` sections D and E gates unchanged.

### D3. `299` and `399` only become final after live slugs and handoffs are stable

Because both section conclusions are generated from the shared section
conclusion builder, do not accept them as done merely because they were
emitted.

Check both after the real comparison URLs stabilize:

- `299` should still bridge the framework arc into `100`
- `399` should reflect the actual comparison arc that landed in `230`,
  `240`, `250`, `260`, and `270`

If `399` still points at older slug forms or outdated narrative order,
refresh it only after the underlying comparison notebooks are final.

## E. Pull two cross-cutting improvements earlier when they reduce duplicate work

### E1. Centralize slug overrides now if slug drift appears in more than one live file

Create early if `005`, `130`, `299`, or `399` are all being touched in
the same pass:

- `scripts/_public_slugs.py`

Export:

- `PUBLIC_SLUG_OVERRIDES`
- `public_slug(notebook_id, default_slug)`

Replace local copies in:

- `scripts/build_index_notebook.py`
- `scripts/build_notebook_005_glossary.py`
- `scripts/build_section_conclusion_notebooks.py`

If `130` needs live-URL alignment in the same pass, migrate its local
URL constants to the helper too.

Rebuild after migration:

```powershell
& $py scripts/build_index_notebook.py
& $py scripts/build_notebook_005_glossary.py
& $py scripts/build_section_conclusion_notebooks.py
& $py scripts/validate_notebooks.py
```

### E2. Extract `_canonical_notebook.py` earlier only when the same structural edit hits 3+ builders

Threshold rule:

- If the same canonical header, troubleshooting-table, final-print, or
  `_hex_to_rgba(...)` change is being repeated across three or more
  builders in the same pass, stop copying it and extract the helper
  first.

Create:

- `scripts/_canonical_notebook.py`

Initial migration order:

1. `scripts/build_notebook_210_oss_model_comparison.py`
2. `scripts/build_notebook_220_ollama_cloud_comparison.py`
3. `scripts/build_notebook_230_mistral_family_comparison.py`
4. `scripts/build_notebook_240_openrouter_frontier_comparison.py`
5. `scripts/build_notebook_270_gemma_generations.py`

Only migrate `250`, `260`, `300`, and `310` after the first five stay
green.

This is the main sequencing improvement over `28`: do the first helper
extraction before more shared-builder churn if it obviously reduces
repeat work.

## F. Continue the prompt ladder only after the comparison arc is genuinely closed

Once the gates above are green, continue into prompts `18` through `22`
in the same strict order as `28`, but with one added rule:

- do not count a locally emitted notebook as complete if the source
  builder proof was never shown

That means the currently emitted local artifacts for `300`, `310`, and
`320` should still be reviewed against their source builders before they
are treated as completed prompt-18-to-20 work.

Per-prompt gate remains:

```powershell
& $py scripts/validate_notebooks.py
```

Push only the notebooks for the prompt that just finished.

## G. Evidence pack to leave behind after each batch

After each safe batch, leave a compact proof pack in `proofRoot` and in
your handoff note:

1. exact builders edited
2. rebuild commands run
3. validator result (`42 of 42 OK` or explicit failures)
4. Kaggle statuses checked or pushes attempted
5. remaining blockers, stated as concrete next actions

Minimum handoff format:

```text
Batch completed:
- builders changed:
- notebooks rebuilt:
- validator result:
- kaggle status / push result:
- blockers left:
- next section to run:
```

## H. Priority summary for the post-28 phase

- Immediate: `A`, then `B`.
- If validator is still red: `C1` before everything else.
- If validator is green: `C2`, `C3`, then `D1`, `D2`, `D3`.
- Pull `E1` or `E2` forward only when they reduce repeated edits in the
  current pass.
- Resume prompt `18` through `22` only after the 200-band comparison arc
  is genuinely source-verified and stable.