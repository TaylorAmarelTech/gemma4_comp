# 30: DueCare full project checkpoint

Date captured: 2026-04-16
Purpose: single self-contained handoff for Claude Code or GPT 5.4x to
resume DueCare submission work without rereading the earlier 24 through
29 prompts. This file is the source of truth for the current state,
the exact next actions, and the gates that separate them.

If the repo contradicts anything below, trust the repo and update this
file in the same edit pass.

## 0. Quick summary

- **Project.** DueCare, an on-device LLM safety system for migrant
  worker anti-trafficking evaluation, built on Gemma 4 and named for
  California Civil Code section 1714(a) duty of care.
- **Competition.** Kaggle Gemma 4 Good Hackathon. Due
  `2026-05-18`. Prize pool targets: Impact / Safety and Trust, Unsloth
  special, llama.cpp or LiteRT special, Main track.
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
  per-day cap. When hit, update pushes return `400 Bad Request` and new
  kernel creation returns `Notebook not found`.

## 1. What changed in the most recent sessions

### Builders rebuilt to canonical `NNN: DueCare ...` style

- `scripts/build_notebook_210_oss_model_comparison.py`
- `scripts/build_notebook_220_ollama_cloud_comparison.py`
- `scripts/build_notebook_130_prompt_corpus_exploration.py` (new)

### Plotly fillcolor drift patched, headers still pre-canonical

- `scripts/build_notebook_230_mistral_family_comparison.py`
- `scripts/build_notebook_240_openrouter_frontier_comparison.py`

### Shared index, glossary, and section-conclusion builders

- `scripts/build_index_notebook.py` slots 130; adds `"210":
  "duecare-gemma-vs-oss-comparison"` to `PUBLIC_SLUG_OVERRIDES`.
- `scripts/build_notebook_005_glossary.py` adds the same `"210"`
  override.
- `scripts/build_section_conclusion_notebooks.py` adds the same
  `"210"` override, names 130 in 299 recap, rewrites 399 recap and key
  points to tell the post-210 / post-220 story.

### Hardener

- `scripts/notebook_hardening_utils.py` registers
  `130_prompt_corpus_exploration.ipynb` in `INSTALL_PACKAGES` and
  `SUMMARY_MESSAGES`.

### Adversarial validators

- `scripts/_validate_210_adversarial.py` (17 checks).
- `scripts/_validate_220_adversarial.py` (17 checks).

### Live Kaggle state this session

- `210` live and `COMPLETE` as v3 at
  `taylorsamarel/duecare-gemma-vs-oss-comparison` after rgba radar fix.
- `000` Index pushed live as v16.
- `220`, `130`, `399`, `299`, `005` all push-attempted and all failed
  today with `400 Bad Request` or `Notebook not found`. Treat as
  cap-blocked or slug-mismatch; see section 5.

## 2. Canonical conventions to enforce across every notebook

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
- Reading order bullet list with full Kaggle URLs.
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
- The print is notebook-specific, URL-bearing, and hands off forward in
  the pipeline and to the closing section conclusion.

### Troubleshooting table

- Any notebook that runs code ends its last markdown cell with an HTML
  `<table>` of `Symptom` -> `Resolution` rows.

### "Privacy is non-negotiable"

- Reserved for framing prose and the submission walkthrough. Do not
  put it in comparison-notebook footers.

## 3. Full live-kernel inventory

Every kernel has a canonical `NNN:` title in kernel-metadata.json. The
Kaggle slug may differ from the canonical when the kernel pre-dates the
renumber. Treat the live slug as source of truth; the canonical prefix
lives in prose only.

| NNN | Canonical title | Live Kaggle slug | Builder |
|---|---|---|---|
| 000 | `DueCare 000 Index` | `duecare-000-index` | `build_index_notebook.py` |
| 005 | `005: DueCare Glossary and Reading Map` | `duecare-005-glossary` (LIVE) vs metadata `005-duecare-glossary-and-reading-map` (DRIFT) | `build_notebook_005_glossary.py` |
| 010 | `010: DueCare Quickstart in 5 Minutes` | `010-duecare-quickstart-in-5-minutes` | `build_notebook_010_quickstart.py` |
| 099 | section conclusion | `099-duecare-orientation-and-background-and-package-setup-conclusion` | `build_section_conclusion_notebooks.py` |
| 100 | `100: DueCare Gemma 4 Exploration (Phase 1 Baseline)` | `duecare-gemma-exploration` (legacy, override) | `build_notebook_100.py` |
| 110 | `110: DueCare Prompt Prioritizer` | `00a-duecare-prompt-prioritizer-data-pipeline` (legacy, override) | `build_notebook_110.py` |
| 120 | `120: DueCare Prompt Remixer` | `duecare-prompt-remixer` (legacy) | `build_notebook_120.py` |
| 130 | `130: DueCare Prompt Corpus Exploration` | not live yet (first-push blocked) | `build_notebook_130_prompt_corpus_exploration.py` |
| 150 | `150: DueCare Free Form Gemma Playground` | `150-duecare-free-form-gemma-playground` | `build_notebook_150_free_form_gemma_playground.py` |
| 155 | `155: DueCare Tool Calling Playground` | `155-duecare-tool-calling-playground` | `build_notebook_155_tool_calling_playground.py` |
| 160 | `160: DueCare Image Processing Playground` | `160-duecare-image-processing-playground` | `build_notebook_160_image_processing_playground.py` |
| 199 | section conclusion | `199-duecare-free-form-exploration-conclusion` | `build_section_conclusion_notebooks.py` |
| 200 | `200: DueCare Cross-Domain Proof` | `duecare-200-cross-domain-proof` | `build_notebook_200_cross_domain_proof.py` |
| 210 | `210: DueCare Gemma 4 vs OSS Models` | `duecare-gemma-vs-oss-comparison` (override) | `build_notebook_210_oss_model_comparison.py` |
| 220 | `220: DueCare Gemma 4 vs 6 OSS Models via Ollama Cloud` | not live yet (first-push blocked) | `build_notebook_220_ollama_cloud_comparison.py` |
| 230 | `230: DueCare Gemma 4 vs Mistral Family` | canonical `230-duecare-gemma-4-vs-mistral-family` | `build_notebook_230_mistral_family_comparison.py` |
| 240 | `240: DueCare Gemma 4 vs Frontier Cloud Models` | canonical | `build_notebook_240_openrouter_frontier_comparison.py` |
| 250 | `250: DueCare Anchored Grading vs Reference Responses` | canonical | `build_grading_notebooks.py` (`NB11_CELLS`) |
| 260 | `260: DueCare Plain vs Retrieval-Augmented vs System-Guided` | canonical | `build_showcase_notebooks.py` (`RAG_CELLS`) |
| 270 | `270: DueCare Gemma 2 vs 3 vs 4 Safety Gap` | canonical | `build_notebook_270_gemma_generations.py` |
| 299 | section conclusion | canonical, not yet live | `build_section_conclusion_notebooks.py` |
| 300 | `300: DueCare Adversarial Resistance Against 15 Attack Vectors` | `300-gemma-4-against-15-adversarial-attack-vectors` (override) | `build_showcase_notebooks.py` (`ADVERSARIAL_CELLS`) |
| 310 | `310: DueCare Adversarial Prompt Factory` | canonical | `build_grading_notebooks.py` (`NB12_CELLS`) |
| 320 | `320: DueCare Red-Team Safety Gap` | canonical | `build_notebook_320_supergemma_safety_gap.py` |
| 399 | section conclusion | canonical, not yet live | `build_section_conclusion_notebooks.py` |
| 400 | `400: DueCare Gemma 4 Native Tool Calls and Multimodal` | canonical | `build_showcase_notebooks.py` (`FC_CELLS`) |
| 410 | `410: DueCare Six-Dimension LLM Judge Grading` | canonical | `build_grading_notebooks.py` (`NB09_CELLS`) |
| 420 | `420: DueCare Multi-Turn Conversation Escalation` | `420-multi-turn-conversation-escalation-detection` (override) | `build_grading_notebooks.py` (`NB10_CELLS`) |
| 430 | `430: DueCare 54-Criterion Pass/Fail Rubric Evaluation` | `430-54-criterion-pass-fail-rubric-evaluation` (override) | `build_grading_notebooks.py` (`NB13_CELLS`) |
| 440 | `440: DueCare Per-Prompt Rubric Generator` | canonical | `build_notebook_440_per_prompt_rubric_generator.py` |
| 450 | `450: DueCare Contextual Worst-Response Judge` | canonical | `build_notebook_450_contextual_worst_response_judge.py` |
| 499 | section conclusion | canonical | `build_section_conclusion_notebooks.py` |
| 500 | `500: DueCare 12-Agent Gemma 4 Safety Swarm` | canonical | `build_showcase_notebooks.py` (`SWARM_CELLS`) |
| 510 | `510: DueCare Phase 2 Model Comparison` | canonical | `build_notebook_510_phase2_model_comparison.py` |
| 520 | `520: DueCare Phase 3 Curriculum Builder` | canonical | `build_notebook_520_phase3_curriculum_builder.py` |
| 530 | `530: DueCare Phase 3 Unsloth Fine-Tune` | canonical | `build_notebook_530_phase3_unsloth_finetune.py` |
| 599 | section conclusion | canonical | `build_section_conclusion_notebooks.py` |
| 600 | `600: DueCare Results Dashboard` | `600-duecare-results-dashboard` (live HTTP 200). Legacy `600-interactive-safety-evaluation-dashboard` redirects. | **no dedicated builder found; source-of-truth gap** |
| 610 | `610: DueCare End-to-End Submission Walkthrough` | canonical | `build_kaggle_notebooks.py` (`SUBMISSION_CELLS`) |
| 699 | section conclusion | canonical | `build_section_conclusion_notebooks.py` |
| 799 | section conclusion | canonical | `build_section_conclusion_notebooks.py` |
| 899 | section conclusion | canonical | `build_section_conclusion_notebooks.py` |

## 4. Source-of-truth ownership map

### Dedicated builders (one notebook each)

- `build_notebook_100.py`, `110.py`, `120.py`, `130_prompt_corpus_exploration.py`,
  `150_free_form_gemma_playground.py`, `155_tool_calling_playground.py`,
  `160_image_processing_playground.py`, `200_cross_domain_proof.py`,
  `210_oss_model_comparison.py`, `220_ollama_cloud_comparison.py`,
  `230_mistral_family_comparison.py`, `240_openrouter_frontier_comparison.py`,
  `270_gemma_generations.py`, `320_supergemma_safety_gap.py`,
  `440_per_prompt_rubric_generator.py`, `450_contextual_worst_response_judge.py`,
  `510_phase2_model_comparison.py`, `520_phase3_curriculum_builder.py`,
  `530_phase3_unsloth_finetune.py`, `010_quickstart.py`,
  `005_glossary.py`.

### Shared builders

- `build_grading_notebooks.py` emits `250` (`NB11_CELLS`), `310`
  (`NB12_CELLS`), `410` (`NB09_CELLS`), `420` (`NB10_CELLS`), `430`
  (`NB13_CELLS`). Shared blast radius: 5 notebooks.
- `build_showcase_notebooks.py` emits `260` (`RAG_CELLS`, GPU), `300`
  (`ADVERSARIAL_CELLS`), `400` (`FC_CELLS`), `500` (`SWARM_CELLS`).
  Shared blast radius: 4 notebooks.
- `build_section_conclusion_notebooks.py` emits `099`, `199`, `299`,
  `399`, `499`, `599`, `699`, `799`, `899`.
- `build_kaggle_notebooks.py` emits `610` plus the older `200`-style
  samples. Canonical 610 lives in `SUBMISSION_CELLS`.
- `build_index_notebook.py` emits `000`.

### Source-of-truth gaps

- **600 Results Dashboard**: no dedicated builder file exists. No
  cells block in `build_kaggle_notebooks.py`. Kernel is live on Kaggle,
  but regenerating it from source is not possible today. Before any
  edit that touches `610`, `899`, the writeup, or the submission video,
  either locate the true generator or create
  `scripts/build_notebook_600_results_dashboard.py`.

### Supporting modules

- `scripts/notebook_hardening_utils.py` owns the install cell pattern,
  the `INSTALL_PACKAGES` pin map, the `SUMMARY_MESSAGES` fallback
  strings, and the `harden_notebook(...)` transformer.
- `scripts/kaggle_notebook_utils.py` provides
  `discover_kernel_notebooks()` used by the validator.
- `scripts/sync_kaggle_notebook_mirror.py` copies emitted
  `kaggle/kernels/<dir>/<file>.ipynb` into the top-level `notebooks/`
  mirror.
- `scripts/validate_notebooks.py` is the repo-wide gate.

## 5. Known drift and open blockers

### Kaggle push blockers observed today

- `220` first push: `400 Bad Request` on `SaveKernel`. Expected when
  the daily cap is hit or when the canonical slug cannot be created.
- `130` first push: `Notebook not found`. Expected when Kaggle cannot
  resolve the title-derived slug during new-kernel creation.
- `399` first push: `Notebook not found`. Same pattern.
- `299` first push: `400 Bad Request`.
- `005` push: `Notebook not found`. Cause is different: the builder's
  `KERNEL_ID` is `taylorsamarel/005-duecare-glossary-and-reading-map`,
  but the live kernel is at `taylorsamarel/duecare-005-glossary`.
  This is slug drift, not cap.

### Slug-drift resolutions

- Update `scripts/build_notebook_005_glossary.py` `KERNEL_ID` to
  `taylorsamarel/duecare-005-glossary`. Keep the canonical `005:` title.
- Add `"005": "duecare-005-glossary"` to `PUBLIC_SLUG_OVERRIDES` in:
  - `scripts/build_index_notebook.py`
  - `scripts/build_notebook_005_glossary.py`
  - `scripts/build_section_conclusion_notebooks.py`
- Rebuild 000, 005, all 9 section conclusions.

### Validator gate

- `python scripts/validate_notebooks.py` reports `39 of 42 OK`.
- Failures: `duecare_150_free_form_gemma_playground`,
  `duecare_155_tool_calling_playground`,
  `duecare_160_image_processing_playground`. Each ends with a markdown
  cell instead of a `code` cell containing `print(`. The validator rule
  is in `scripts/validate_notebooks.py` lines 54-56.
- Fix: add a final `_code(final_print)` cell in each of the three
  playground builders before the `_md(FOOTER)` cell.

### Pre-canonical content still in place

- `230`, `240`, `270`, `250`, `260` notebook emissions still carry em-
  dash H1, `| | |` markdown pseudo-tables, `Privacy is non-negotiable`
  footer, hardener default final print. Canonical rewrite per section 7
  below.

### Non-obvious legacy replacement in the hardener

- `scripts/notebook_hardening_utils.LEGACY_TEXT_REPLACEMENTS` rewrites
  `NB 00`, `NB 00a`, `NB 00b` to `NB 100`, `NB 110`, `NB 120`. New
  notebooks must never contain the literal `NB 00<digit>` token.

### Full-corpus privacy

- `configs/duecare/domains/trafficking/seed_prompts.jsonl` is 74,567
  rows of the proprietary benchmark. Verify `.gitignore` coverage
  before any PR:
  `git check-ignore -v configs/duecare/domains/trafficking/seed_prompts.jsonl`.

## 6. Immediate next actions (ordered)

Every action names the exact file, the exact rebuild command, and the
exact gate.

### Step A: fix validator gate to `42 of 42 OK`

1. Edit `scripts/build_notebook_150_free_form_gemma_playground.py`,
   `155_tool_calling_playground.py`, `160_image_processing_playground.py`.
2. Replace the trailing `_md(FOOTER)` with a pair of cells: keep the
   markdown footer, then add an explicit `_code(FINAL_PRINT)` cell.
3. Final-print handoffs:
   - 150 -> 155 and 100.
   - 155 -> 160 and 199.
   - 160 -> 199 and 200.
4. Rebuild each builder.
5. Gate: `python scripts/validate_notebooks.py` reports `42 of 42 OK`.

### Step B: fix `005` slug drift

1. Edit `scripts/build_notebook_005_glossary.py`. Change `KERNEL_ID`
   to `taylorsamarel/duecare-005-glossary`. Keep the canonical
   `005: DueCare Glossary and Reading Map` title.
2. Add `"005": "duecare-005-glossary"` to `PUBLIC_SLUG_OVERRIDES`
   in all three builders listed in section 5.
3. Rebuild 000, 005, and all 9 section conclusions.
4. Gate: `python scripts/validate_notebooks.py` stays green.

### Step C: push the existing queue when the Kaggle cap permits

1. Probe:
   `kaggle kernels status taylorsamarel/duecare-gemma-vs-oss-comparison`.
   Expect `COMPLETE` or `RUNNING`. If `429`, stop.
2. Push in exact order:

```powershell
kaggle kernels push -p kaggle/kernels/duecare_220_ollama_cloud_comparison
kaggle kernels push -p kaggle/kernels/duecare_130_prompt_corpus_exploration
kaggle kernels push -p kaggle/kernels/duecare_399_baseline_text_comparisons_conclusion
kaggle kernels push -p kaggle/kernels/duecare_299_baseline_text_evaluation_framework_conclusion
kaggle kernels push -p kaggle/kernels/duecare_005_glossary
```

3. Fallback for `Notebook not found` after two consecutive attempts on
   the same kernel: drop the `NNN-` prefix in that builder's
   `KERNEL_ID`, rebuild, retry once, then record the actual resulting
   slug in `PUBLIC_SLUG_OVERRIDES` across all three copies.

### Step D: canonicalize `230`, `240`, `270`

Use `210`/`220` as the template. Apply:

1. Canonical HTML header with Inputs / Outputs / Prerequisites /
   Runtime / Pipeline position.
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

Create adversarial validators mirroring
`scripts/_validate_220_adversarial.py`:

- `scripts/_validate_230_adversarial.py`
- `scripts/_validate_240_adversarial.py`
- `scripts/_validate_270_adversarial.py`

Gate: all three adversarial validators pass and
`python scripts/validate_notebooks.py` stays green.

Push batch:

```powershell
kaggle kernels push -p kaggle/kernels/duecare_230_mistral_family_comparison
kaggle kernels push -p kaggle/kernels/duecare_240_openrouter_frontier_comparison
kaggle kernels push -p kaggle/kernels/duecare_270_gemma_generations
```

### Step E: canonicalize `250` inside the shared grading builder

1. Edit `scripts/build_grading_notebooks.py`, `NB11_CELLS` block only.
2. Apply the 9 canonical fixes.
3. Rebuild the full builder so every sibling regenerates.
4. Run `python scripts/sync_kaggle_notebook_mirror.py` then
   `python scripts/validate_notebooks.py`. Expect green.
5. Push only `250`.

### Step F: canonicalize `260` inside the shared showcase builder

Same pattern in `RAG_CELLS`. GPU kernel. Push only `260`.

### Step G: reconfirm 399 and push once C/D/E/F land

Validate that the 399 recap in
`scripts/build_section_conclusion_notebooks.py` still matches what
actually shipped. Refresh only if the narrative drifted. Push 399.

### Step H: resolve the 600 source-of-truth gap

1. `rg "600_results_dashboard|Results Dashboard" scripts kaggle notebooks`.
2. If a real source appears, record it in this file and use it.
3. Otherwise create `scripts/build_notebook_600_results_dashboard.py`
   from the existing kernel JSON as a starting point, then
   canonicalize. Do not hand-edit the kernel JSON directly.

### Step I: continue through prompts 18 to 22 one at a time

Run each prompt's cleanup in isolation. One prompt, one validator run,
one push batch. Ownership per prompt is already captured in section 4.

### Step J: cross-cutting consolidations

- Create `scripts/_public_slugs.py` and migrate the three local
  `PUBLIC_SLUG_OVERRIDES` copies to import from it.
- Create `scripts/_canonical_notebook.py` exporting
  `canonical_header`, `troubleshooting_table`, `url_handoff_print`,
  `hex_to_rgba`, `load_phase1_baseline_with_fallback`. Migrate
  `210`, `220`, `130` first. Do not migrate the rest until those three
  stay green.

### Step K: submission hardening

- Rebuild `610` to reference only live canonical URLs.
- Run `python scripts/verify_kaggle_urls.py`; all must return 200.
- Rerun `610` on a fresh Kaggle kernel end-to-end at least once.

### Step L: writeup and video

- `docs/writeup_draft.md` under 1,500 words, names 130 as the input
  map, quotes real numbers from 100, 210, 220, 270, 320, 530, links
  Kaggle, HF Hub, PyPI, GitHub.
- `docs/video_script.md` opens with a named composite worker and
  closes with named NGOs: Polaris, IJM, POEA, BP2MI, HRD Nepal.
- Capture 130 screenshots only from a run with
  `taylorsamarel/duecare-trafficking-prompts` attached so the full
  5-grade walk-through renders.

### Step M: release

Tag `v0.1.0`. Publish the 7 PyPI packages, HF Hub weights, FastAPI
demo endpoint. Submit to Kaggle before `2026-05-18`.

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

## 9. Hackathon rubric mapping

- **Impact and Vision (40).** 130 shows the corpus concretely; 210 /
  220 / 230 / 240 show the on-device argument; 399 closes the section
  honestly. Video opens on a named composite worker; closes on named
  NGOs.
- **Video Pitch and Storytelling (30).** 3-minute YouTube, `pip install
  duecare-llm` one-liner visible, stock-vs-fine-tuned side-by-side from
  `210` and `530`.
- **Technical Depth and Execution (30).** 7 PyPI packages, typed
  protocols, folder-per-module layout, CI-verified tests, 42 Kaggle
  notebooks with canonical titles, fine-tuned model on HF Hub,
  llama.cpp and LiteRT deployment artifacts.

## 10. Done definition

- `python scripts/validate_notebooks.py` -> `43 of 43 OK`.
- Every entry in section 3 returns HTTP 200 via
  `scripts/verify_kaggle_urls.py`.
- `git check-ignore -v
  configs/duecare/domains/trafficking/seed_prompts.jsonl` confirms the
  proprietary full corpus is not in the public tree.
- 7 PyPI packages tagged `v0.1.0` and published.
- HF Hub model `TaylorScottAmarel/duecare-gemma-4-e4b-safetyjudge-v0.1.0`
  public with model card and GGUF + LiteRT artifacts.
- Public FastAPI demo endpoint reachable from the writeup link.
- `docs/writeup_draft.md` under 1,500 words and
  `docs/video_script.md` finalized.
- Kaggle submission filed before `2026-05-18`.

## 11. How to resume

1. Read this file top to bottom.
2. Re-run `python scripts/validate_notebooks.py` and compare against
   section 5.
3. Pick the first unfinished step in section 6 that is not blocked by
   the Kaggle cap. Step A is always safe to run locally.
4. After each batch, update section 1 and section 5 with what actually
   changed. This file is the handoff; keep it current.
