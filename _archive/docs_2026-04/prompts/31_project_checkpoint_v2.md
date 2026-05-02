# 31: DueCare project checkpoint v2

Date captured: 2026-04-16 (end of session that ran Steps A, B, and
partial C from checkpoint 30).
Purpose: self-contained handoff for the next Claude Code or GPT 5.4x
session. Supersedes `30_project_checkpoint.md`.

If the repo contradicts anything below, trust the repo and update this
file in the same edit pass.

## 0. Quick summary

- **Project.** DueCare, an on-device LLM safety system for migrant
  worker anti-trafficking evaluation, built on Gemma 4 and named for
  California Civil Code section 1714(a) duty of care.
- **Competition.** Kaggle Gemma 4 Good Hackathon. Due `2026-05-18`.
  Prize pool targets: Impact / Safety and Trust, Unsloth special,
  llama.cpp or LiteRT special, Main track.
- **Deliverables.** Public GitHub repo, 7 PyPI packages under the
  `duecare-llm-*` namespace, 42 published Kaggle notebooks, one
  fine-tuned model on HF Hub, a 3-minute YouTube video, a public live
  demo, a writeup under 1,500 words.
- **Repo root.** `C:\Users\amare\OneDrive\Documents\gemma4_comp`.
- **Shell.** PowerShell. Unix-style paths supported by Git Bash but
  prefer Windows paths in commands.
- **Venv Python.** `c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe`.
- **Kaggle auth.** `KAGGLE_API_TOKEN` env var only. Never commit the
  token. Never write a `kaggle.json` file for this new-format token.
- **Daily cap.** Kaggle new-kernel creation and update both share a
  per-day cap. When hit, update pushes return `400 Bad Request` and
  new-kernel creation returns `Notebook not found`.

## 1. Delta since checkpoint 30

### Green gate maintained

- `python scripts/validate_notebooks.py`: `Validated 42 notebooks
  successfully`. Green throughout 31a/31b/31c/31d.

### Shared helpers extracted (Step J)

- `scripts/_public_slugs.py`: single source of truth for
  `PUBLIC_SLUG_OVERRIDES`. Lifted out of `build_index_notebook.py`,
  `build_notebook_005_glossary.py`, and
  `build_section_conclusion_notebooks.py`. Fixed the 600 override to
  point at the canonical `600-duecare-results-dashboard` instead of
  the legacy `600-interactive-safety-evaluation-dashboard` redirect.
- `scripts/_canonical_notebook.py`: `HEX_TO_RGBA_SRC`,
  `canonical_header_table`, `troubleshooting_table_html`,
  `patch_final_print_cell`. Used by 230/240/270/600 canonicalizations.

### 31b slug reverts + fallbacks

- 220 metadata id reverted to live `duecare-ollama-cloud-oss-comparison`.
- 230 metadata id reverted to live `duecare-230-mistral-family-comparison`.
- 240 metadata id reverted to live `duecare-openrouter-frontier-comparison`.
- 270 metadata id reverted to live `duecare-270-gemma-generations`.
- 130 KERNEL_ID switched to fallback `duecare-prompt-corpus-exploration`.
- 299 and 399 section-conclusion kernel ids now flow through
  `PUBLIC_SLUG_OVERRIDES` so both fall back to their non-prefixed
  slugs (`duecare-baseline-text-evaluation-framework-conclusion` and
  `duecare-baseline-text-comparisons-conclusion`).
- `_validate_210_adversarial.py` and `_validate_220_adversarial.py`
  refreshed to match the new fallback slugs.

### 31c canonicalization landed

- 230 Mistral Family Comparison, 240 OpenRouter Frontier Comparison,
  270 Gemma Generations builders rewritten to the canonical shape:
  canonical H1, canonical HTML header table with the five rows,
  `_hex_to_rgba(...)` radar fills, HTML troubleshooting table, and
  URL-bearing final `print(...)` cell patched via
  `patch_final_print_cell`.
- 270 gained a `PUBLISHED_BASELINE` fallback dict (source/date cited)
  so the V3 6-band stacked-bar plot renders real numbers even when
  the prompts dataset is not attached.
- New adversarial validators `scripts/_validate_230_adversarial.py`,
  `_validate_240_adversarial.py`, `_validate_270_adversarial.py`
  (17 checks each). All 5 validators now report ALL CHECKS PASSED.

### 31d canonicalization in progress

- Shared-builder cell blocks `NB11_CELLS` (250) and `RAG_CELLS` (260)
  being rewritten to canonical shape inside `build_grading_notebooks.py`
  and `build_showcase_notebooks.py`. Sibling cell blocks untouched.
- 299 and 399 `SECTIONS` recap and `key_points` being refreshed to
  match what the canonicalized 110/120/130/200-270 notebooks now
  deliver.

### Step H: 600 Results Dashboard source-of-truth gap resolved

- New builder: `scripts/build_notebook_600_results_dashboard.py`.
  Preserves the existing dashboard logic (mode comparison, grade
  distribution, heatmap, RAG/guided deltas, radar, failure-mode pie).
  Canonical header, HTML troubleshooting table, URL-bearing final
  print. Metadata id aligned to live `600-duecare-results-dashboard`.
  Kernel JSON no longer hand-edited.

### Scope expansion in this session (2026-04-17)

Added 9 new notebooks + 12 new adversarial validators:

- `140 Evaluation Mechanics` (CPU)
- `170 Live Context Injection Playground` (T4 GPU)
- `180 Multimodal Document Inspector` (T4 GPU)
- `190 RAG Retrieval Inspector` (CPU)
- `335 Attack Vector Inspector` (CPU)
- `460 Citation Verifier` (CPU)
- `540 Fine-tune Delta Visualizer` (CPU)
- `620 Demo API Endpoint Tour` (CPU)
- `650 Custom Domain Walkthrough` (CPU)

Local gate at 51 of 51 validated + 17 of 17 adversarial validators
`ALL CHECKS PASSED`.

### Push session in progress

Running `scripts/push_all_sequential.py` with `KAGGLE_API_TOKEN`
exported. 20-second inter-push delay + 90-second rate-limit backoff
handled by the script. Estimated wall time: 20-40 minutes depending on
per-push response time. Results will land in
`docs/current_kaggle_notebook_state.md` and the 31e publish report
after URL verification.

## 2. Canonical conventions (unchanged from 30)

### Title

- Format: `NNN: DueCare <Descriptive Title>`.
- Three-digit zero-padded number. No em dashes. No emojis.

### First markdown cell

- `# NNN: DueCare <Title>` H1.
- One short paragraph stating what the notebook does.
- HTML `<table>` with fixed column widths (`22% / 78%`) containing:
  `Inputs`, `Outputs`, `Prerequisites`, `Runtime`, `Pipeline position`.
- "Why this notebook matters" or "Why CPU-only" explainer block when
  relevant.
- Reading-order bullet list with full Kaggle URLs.
- Numbered "What this notebook does" list.

### Install cell

- Exactly one install cell, produced by
  `notebook_hardening_utils.harden_notebook(...)`.
- Pins `duecare-llm-*==0.1.0` packages declared in `INSTALL_PACKAGES`.
- Reserves the meta `duecare-llm==0.1.0` pin for `000`, `005`, `010`,
  `200`, `500`, `610` only.
- No inline wheel-walk anywhere else.

### Rubric conventions

- `DIMENSION_WEIGHTS` dict (6 keys) and `SAFETY_DIMENSIONS =
  list(DIMENSION_WEIGHTS.keys())` defined together at the top of the
  first rubric cell. Reused downstream.

### Plots

- `_hex_to_rgba(hex_color, alpha=0.08)` helper at the top of any cell
  that sets a plotly `fillcolor`. Never append `'15'` to a 6-digit hex;
  current plotly rejects it.

### Final cell

- Last cell is a `code` cell whose source contains `print(`.
- The print is notebook-specific, URL-bearing, and hands off forward
  in the pipeline and to the closing section conclusion.

### Troubleshooting table

- Any notebook that runs code ends its last markdown cell with an
  HTML `<table>` of `Symptom` -> `Resolution` rows.

### "Privacy is non-negotiable"

- Reserved for framing prose and the submission walkthrough. Do not
  put it in comparison-notebook footers.

## 3. Live-kernel inventory (current)

The live Kaggle slug is source of truth when it differs from the
canonical `NNN-duecare-*` pattern. `PUBLIC_SLUG_OVERRIDES` maps NNN to
the actual live slug.

Current `PUBLIC_SLUG_OVERRIDES` entries (now in `scripts/_public_slugs.py`
and imported by `scripts/build_index_notebook.py`,
`scripts/build_notebook_005_glossary.py`, and
`scripts/build_section_conclusion_notebooks.py`):

- `"110": "00a-duecare-prompt-prioritizer-data-pipeline"` (legacy live slug)
- `"130": "duecare-prompt-corpus-exploration"` (fallback, NNN- prefix rejected)
- `"299": "duecare-baseline-text-evaluation-framework-conclusion"` (fallback)
- `"300": "300-gemma-4-against-15-adversarial-attack-vectors"` (live)
- `"399": "duecare-baseline-text-comparisons-conclusion"` (fallback)
- `"420": "420-multi-turn-conversation-escalation-detection"` (live)
- `"430": "430-54-criterion-pass-fail-rubric-evaluation"` (live)
- `"600": "600-duecare-results-dashboard"` (canonical; legacy
  `600-interactive-safety-evaluation-dashboard` redirects here)

Live kernels observed this session:

- `taylorsamarel/duecare-000-index` v16 (index).
- `taylorsamarel/duecare-005-glossary` v2 (pushed this session).
- `taylorsamarel/duecare-gemma-vs-oss-comparison` v3 (210 canonical
  body, live slug is legacy).
- `taylorsamarel/600-duecare-results-dashboard` (HTTP 200; legacy
  `600-interactive-safety-evaluation-dashboard` redirects).

Not yet live:

- `130`, `220`, `299`, `399`. All push attempts in this session
  failed on first-time kernel creation.

See the full 42-row table in checkpoint 30 section 3. Nothing below
the 200 band changed this session.

## 4. Source-of-truth ownership map (unchanged from 30)

### Dedicated builders

- `build_notebook_100.py`, `110.py`, `120.py`, `130_prompt_corpus_exploration.py`,
  `150_free_form_gemma_playground.py`, `155_tool_calling_playground.py`,
  `160_image_processing_playground.py`, `200_cross_domain_proof.py`,
  `210_oss_model_comparison.py`, `220_ollama_cloud_comparison.py`,
  `230_mistral_family_comparison.py`, `240_openrouter_frontier_comparison.py`,
  `270_gemma_generations.py`, `320_supergemma_safety_gap.py`,
  `440_per_prompt_rubric_generator.py`, `450_contextual_worst_response_judge.py`,
  `510_phase2_model_comparison.py`, `520_phase3_curriculum_builder.py`,
  `530_phase3_unsloth_finetune.py`, `010_quickstart.py`, `005_glossary.py`.

### Shared builders

- `build_grading_notebooks.py` emits `250` (`NB11_CELLS`), `310`
  (`NB12_CELLS`), `410` (`NB09_CELLS`), `420` (`NB10_CELLS`), `430`
  (`NB13_CELLS`). Shared blast radius: 5 notebooks.
- `build_showcase_notebooks.py` emits `260` (`RAG_CELLS`, GPU), `300`
  (`ADVERSARIAL_CELLS`), `400` (`FC_CELLS`), `500` (`SWARM_CELLS`).
  Shared blast radius: 4 notebooks.
- `build_section_conclusion_notebooks.py` emits `099`, `199`, `299`,
  `399`, `499`, `599`, `699`, `799`, `899`.
- `build_kaggle_notebooks.py` emits `610` from `SUBMISSION_CELLS` plus
  older sample notebooks.
- `build_index_notebook.py` emits `000`.

### Source-of-truth gap (carried over from 30)

- **600 Results Dashboard.** No dedicated builder. No cells block in
  `build_kaggle_notebooks.py`. Kernel is live on Kaggle but regenerating
  from source is not possible today. Before any edit that touches
  `610`, `899`, the writeup, or the submission video, either locate
  the true generator or create
  `scripts/build_notebook_600_results_dashboard.py`.

### Supporting modules

- `scripts/notebook_hardening_utils.py` owns the install cell pattern,
  `INSTALL_PACKAGES`, `SUMMARY_MESSAGES`, `harden_notebook(...)`.
- `scripts/kaggle_notebook_utils.py` provides `discover_kernel_notebooks()`.
- `scripts/sync_kaggle_notebook_mirror.py` copies
  `kaggle/kernels/<dir>/<file>.ipynb` to `notebooks/`.
- `scripts/validate_notebooks.py` is the repo-wide gate.
- `scripts/_validate_210_adversarial.py`, `scripts/_validate_220_adversarial.py`
  are the canonical-notebook adversarial validators (17 checks each).

## 5. Known drift and open blockers

### 220 was never blocked; reality reconciled during 31a

- 220 has always been live at `duecare-ollama-cloud-oss-comparison`.
  The "blocked" symptom in earlier sessions was caused by local
  metadata being changed to a new canonical slug, which made pushes
  try to create a new kernel instead of updating the live one. The
  metadata id has been reverted to the live slug during 31b; the next
  update push should work as a version bump.

### Still-blocked first-time kernel creation

- `130`: first-time creation under `130-duecare-*` slug failed. Builder
  `KERNEL_ID` now points at fallback `duecare-prompt-corpus-exploration`.
- `299`: first-time creation under `299-duecare-*` failed. Builder uses
  `PUBLIC_SLUG_OVERRIDES["299"]` = `duecare-baseline-text-evaluation-framework-conclusion`.
- `399`: same as 299; fallback `duecare-baseline-text-comparisons-conclusion`.

First push attempt for each of these three is the first 31e action.

### Validator gate

- Green: `Validated 42 notebooks successfully` as of this session.
- Any future change to `150_*`, `155_*`, `160_*` must preserve the
  terminal `_code(FINAL_PRINT)` cell or the validator reverts to the
  pre-session 39 of 42.

### Pre-canonical content still in place

- `230`, `240`, `270` notebook emissions still carry em-dash H1,
  `| | |` markdown pseudo-tables, `Privacy is non-negotiable` footer,
  hardener default final print.
- `250` (inside grading builder `NB11_CELLS`) and `260` (inside
  showcase builder `RAG_CELLS`) carry the same pre-canonical shape.
- Canonical rewrite plan for all five is Steps D through F below.

### Hardener legacy-text replacement (trap)

- `scripts/notebook_hardening_utils.LEGACY_TEXT_REPLACEMENTS` rewrites
  `NB 00`, `NB 00a`, `NB 00b` to `NB 100`, `NB 110`, `NB 120`.
  New notebooks must never contain the literal `NB 00<digit>` token.

### Full-corpus privacy

- `configs/duecare/domains/trafficking/seed_prompts.jsonl` is 74,567
  rows of the proprietary benchmark. Verify `.gitignore` coverage
  before any PR:
  `git check-ignore -v configs/duecare/domains/trafficking/seed_prompts.jsonl`.

## 6. Immediate next actions (ordered)

### Step C-bis: drop `NNN-` prefix on four blocked builders and retry push

1. Edit each builder's `KERNEL_ID`:

   - `scripts/build_notebook_130_prompt_corpus_exploration.py` ->
     `taylorsamarel/duecare-prompt-corpus-exploration`.
   - `scripts/build_notebook_220_ollama_cloud_comparison.py` ->
     `taylorsamarel/duecare-gemma-4-vs-6-oss-models-via-ollama-cloud`.
   - `scripts/build_section_conclusion_notebooks.py` 299 entry ->
     `taylorsamarel/duecare-baseline-text-evaluation-framework-conclusion`.
   - `scripts/build_section_conclusion_notebooks.py` 399 entry ->
     `taylorsamarel/duecare-baseline-text-comparisons-conclusion`.
   - (The conclusions builder may already honor slug overrides; if so,
     the cleaner move is to add four new override entries in
     `PUBLIC_SLUG_OVERRIDES` and have the builder pick them up rather
     than hand-edit per-notebook IDs. Check the builder source before
     editing.)

2. Rebuild:

```powershell
& $py scripts/build_notebook_130_prompt_corpus_exploration.py
& $py scripts/build_notebook_220_ollama_cloud_comparison.py
& $py scripts/build_section_conclusion_notebooks.py
```

3. Add each resulting slug to `PUBLIC_SLUG_OVERRIDES` in all three
   copies.

4. Rebuild index and glossary:

```powershell
& $py scripts/build_index_notebook.py
& $py scripts/build_notebook_005_glossary.py
```

5. Gate: `python scripts/validate_notebooks.py` stays green.

6. Probe cap then push one at a time:

```powershell
kaggle kernels status taylorsamarel/duecare-gemma-vs-oss-comparison
kaggle kernels push -p kaggle/kernels/duecare_130_prompt_corpus_exploration
kaggle kernels push -p kaggle/kernels/duecare_220_ollama_cloud_comparison
kaggle kernels push -p kaggle/kernels/duecare_299_baseline_text_evaluation_framework_conclusion
kaggle kernels push -p kaggle/kernels/duecare_399_baseline_text_comparisons_conclusion
```

7. Confirm each kernel runs:

```powershell
kaggle kernels status <each slug above>
```

### Step D: canonicalize `230`, `240`, `270`

Before starting, strongly consider extracting the helper first (plan 29
E2 threshold is met: the same canonical-header plus
troubleshooting-table plus URL-handoff print plus `_hex_to_rgba` pattern
now targets five or more builders).

Option 1 (helper first):

- Create `scripts/_canonical_notebook.py` exporting
  `canonical_header`, `troubleshooting_table`, `url_handoff_print`,
  `hex_to_rgba`, `load_phase1_baseline_with_fallback`.
- Migrate `210`, `220`, `130` to use it.
- Then use it in `230`, `240`, `270`.

Option 2 (surgical, no helper):

- Rewrite each of 230, 240, 270's builder `CELLS` list in the canonical
  form. Preserve all middle comparison / plot logic. Only touch cell 0,
  the install cell (drop any duplicate wheel-walk), and the trailing
  summary / troubleshooting / final print.

Whichever path is chosen, the structural target is identical:

1. Canonical HTML header with Inputs, Outputs, Prerequisites, Runtime,
   Pipeline position.
2. Remove em-dash H1 and `| | |` pseudo-tables.
3. Remove `Privacy is non-negotiable` footer.
4. Cross-link back to 100 rubric.
5. Single hardener install. No duplicate wheel-walk.
6. `SAFETY_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())`.
7. `_hex_to_rgba(...)` radar fills (already landed in 230 and 240;
   verify 270 and add if missing).
8. HTML troubleshooting table.
9. Notebook-specific URL-bearing final print.

270-specific: load `gemma_baseline_findings.json` with a
`PUBLISHED_BASELINE` fallback so the V3 band is real.

Create three adversarial validators mirroring
`scripts/_validate_220_adversarial.py`:

- `scripts/_validate_230_adversarial.py`
- `scripts/_validate_240_adversarial.py`
- `scripts/_validate_270_adversarial.py`

Gate: all three pass and `python scripts/validate_notebooks.py` stays
green. Then push.

### Step E: canonicalize `250` inside shared grading builder

1. Edit `scripts/build_grading_notebooks.py`, `NB11_CELLS` block only.
2. Apply the 9 canonical fixes. Do not touch `NB09_CELLS`,
   `NB10_CELLS`, `NB12_CELLS`, `NB13_CELLS`.
3. Rebuild the full builder so every sibling regenerates.
4. Run `python scripts/sync_kaggle_notebook_mirror.py` then the
   validator. Expect green and no sibling regression.
5. Push only `250`.

### Step F: canonicalize `260` inside shared showcase builder

Same pattern in `RAG_CELLS` (GPU kernel). Do not touch
`ADVERSARIAL_CELLS`, `FC_CELLS`, `SWARM_CELLS`. Push only `260`.

### Step G: reconfirm `399` after C-bis/D/E/F land

1. Reread the 399 entry in `SECTIONS` in
   `scripts/build_section_conclusion_notebooks.py`.
2. Confirm the recap still matches reality; the current 5-point recap
   already names 130, 200, 210, 220, 230, 240, 270 and Gemma 2 vs 3
   vs 4 trajectory.
3. Refresh only if the narrative drifted. Push 399 once it is live on
   Kaggle (Step C-bis should have created it).

### Step H: resolve the 600 source-of-truth gap

1. Final search:
   `rg "600_results_dashboard|Results Dashboard" scripts kaggle notebooks`.
2. If a real source appears, record it here and use it.
3. Otherwise create `scripts/build_notebook_600_results_dashboard.py`
   from the existing kernel JSON as a starting point, then
   canonicalize.
4. Do not hand-edit the kernel JSON directly.

### Step I: prompts 18 through 22 in strict order

One prompt, one validator run, one push batch. Ownership:

- Prompt 18: `300` (`ADVERSARIAL_CELLS`), `400` (`FC_CELLS`), `410`
  (`NB09_CELLS`), `420` (`NB10_CELLS`), `499`.
- Prompt 19: `310` (`NB12_CELLS`), `430` (`NB13_CELLS`), `440`, `699`.
- Prompt 20: `320`, `450`, `799`.
- Prompt 21: `500` (`SWARM_CELLS`), `510`, `520`, `530`, `599`.
- Prompt 22: `610`, `899`. `600` blocked until Step H.

### Step J: cross-cutting consolidations

- `scripts/_public_slugs.py`: lift `PUBLIC_SLUG_OVERRIDES` out of
  the three copies and import instead.
- `scripts/_canonical_notebook.py`: helpers used by every comparison
  notebook (covered in Step D option 1).

### Step K: submission hardening

- Rebuild `610` once all comparison notebooks are live.
- `python scripts/verify_kaggle_urls.py`. All canonical links must
  return HTTP 200.
- Rerun `610` end to end on a fresh Kaggle kernel at least once.

### Step L: writeup and video

- `docs/writeup_draft.md` under 1,500 words. Names 130 as the input
  map. Quotes real numbers from 100, 210, 220, 270, 320, 530. Links
  Kaggle, HF Hub, PyPI, GitHub.
- `docs/video_script.md` opens with a named composite worker; closes
  with named NGOs (Polaris, IJM, POEA, BP2MI, HRD Nepal).
- Capture 130 screenshots only from a run with
  `taylorsamarel/duecare-trafficking-prompts` attached so the full
  5-grade walk-through renders.

### Step M: release

Tag `v0.1.0`. Publish the 7 PyPI packages. Publish HF Hub weights.
Confirm the public FastAPI demo endpoint is reachable. Submit on
Kaggle before `2026-05-18`.

## 7. Deferred decisions

### `140 DueCare Evaluation Mechanics`

Created after the earlier deferred-decision checkpoint. `140` now
exists with a dedicated builder, dedicated validator, tracked kernel
metadata, and a live-slug inventory row.

Current source-of-truth and direct continuity files:

- `scripts/build_notebook_140_evaluation_mechanics.py`
- `scripts/_validate_140_adversarial.py`
- `scripts/notebook_hardening_utils.py`
- `scripts/build_index_notebook.py`
- `scripts/build_section_conclusion_notebooks.py`

Use `docs/prompts/32_claudecode_improve_140_evaluation_mechanics.md`
for the next focused improvement pass. Keep the sequence
`130 -> 140 -> 299` intact and do not rename the live slug.

## 8. Useful commands

### Validator and rebuild

```powershell
$py = "c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe"

& $py scripts/validate_notebooks.py
& $py scripts/sync_kaggle_notebook_mirror.py
& $py scripts/_validate_210_adversarial.py
& $py scripts/_validate_220_adversarial.py
```

### Build selected notebooks

```powershell
& $py scripts/build_notebook_130_prompt_corpus_exploration.py
& $py scripts/build_notebook_210_oss_model_comparison.py
& $py scripts/build_notebook_220_ollama_cloud_comparison.py
& $py scripts/build_notebook_230_mistral_family_comparison.py
& $py scripts/build_notebook_240_openrouter_frontier_comparison.py
& $py scripts/build_notebook_270_gemma_generations.py
& $py scripts/build_grading_notebooks.py
& $py scripts/build_showcase_notebooks.py
& $py scripts/build_section_conclusion_notebooks.py
& $py scripts/build_index_notebook.py
& $py scripts/build_notebook_005_glossary.py
& $py scripts/build_notebook_150_free_form_gemma_playground.py
& $py scripts/build_notebook_155_tool_calling_playground.py
& $py scripts/build_notebook_160_image_processing_playground.py
```

### Kaggle

```powershell
$env:PYTHONIOENCODING = "utf-8"
if (-not $env:KAGGLE_API_TOKEN) { throw "Set KAGGLE_API_TOKEN first." }

kaggle kernels status taylorsamarel/duecare-gemma-vs-oss-comparison
kaggle kernels push -p kaggle/kernels/<dir_name>
kaggle kernels output <slug> -p <out_dir>
kaggle kernels list --user taylorsamarel --search <term>
```

## 9. Hackathon rubric mapping (unchanged)

- **Impact and Vision (40).** 130 shows the corpus concretely; 210,
  220, 230, 240 show the on-device argument; 399 closes the section
  honestly. Video opens on a named composite worker; closes on named
  NGOs.
- **Video Pitch and Storytelling (30).** 3-minute YouTube,
  `pip install duecare-llm` one-liner visible, stock-vs-fine-tuned
  side-by-side from 210 and 530.
- **Technical Depth and Execution (30).** 7 PyPI packages, typed
  protocols, folder-per-module layout, CI-verified tests, 42 Kaggle
  notebooks with canonical titles, fine-tuned model on HF Hub,
  llama.cpp and LiteRT deployment artifacts.

## 10. Done definition

- `python scripts/validate_notebooks.py` -> `43 of 43 OK` (green now;
  maintain it).
- Every kernel in section 3 returns HTTP 200 via
  `scripts/verify_kaggle_urls.py`.
- `git check-ignore -v configs/duecare/domains/trafficking/seed_prompts.jsonl`
  confirms the proprietary full corpus is not in the public tree.
- 7 PyPI packages tagged `v0.1.0` and published.
- HF Hub model
  `TaylorScottAmarel/duecare-gemma-4-e4b-safetyjudge-v0.1.0`
  public with model card and GGUF + LiteRT artifacts.
- Public FastAPI demo endpoint reachable from the writeup link.
- `docs/writeup_draft.md` under 1,500 words and
  `docs/video_script.md` finalized.
- Kaggle submission filed before `2026-05-18`.

## 11. How to resume

1. Read this file top to bottom. It supersedes 30.
2. Re-run `python scripts/validate_notebooks.py` and confirm 42 of 42
   OK. If red, fix the regression before anything else.
3. Probe the Kaggle cap:
   `kaggle kernels status taylorsamarel/duecare-gemma-vs-oss-comparison`.
4. Pick the first unfinished step in section 6 that the cap does not
   block. Step C-bis is the natural first move since the fallback-slug
   change is local. Step D is always safe to start locally.
5. After each batch, update sections 1, 3, 5 with what actually
   changed. This file is the living handoff; keep it current.

## 12. Session evidence pack

- git working tree: 244 dirty short-status lines captured in
  `$env:TEMP\duecare_kaggle_logs\post_28_verification\git_status_short.txt`.
- Validator run: `Validated 42 notebooks successfully`.
- Adversarial 210: ALL CHECKS PASSED.
- Adversarial 220: ALL CHECKS PASSED.
- Live Kaggle pushes this session: `000` (v16 earlier), `005` (v2 now).
- Failed pushes this session: `220`, `130`, `299`, `399` (see section
  5 for error codes).
