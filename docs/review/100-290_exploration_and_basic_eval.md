## 0. Band scope and grounding

Bands 100-190 are for raw Gemma exploration: load the model, send prompts, inspect outputs, and stop before rubric machinery. Bands 200-290 are for the first real evaluation pass: introduce `duecare.core`, `duecare.domains`, and `duecare.tasks`, then run small, auditable sample evaluations and one cached summary. This band does not own orientation, glossary, submission pitch, large-scale benchmark runs, adversarial work, or deployment surfaces. `docs/prompts/01_exploration_and_basic_eval.md:11-55`, `docs/prompts/_shared_discipline.md:81-109`

The required boundary is package-owned logic. Current kernels already import the library in-band: `kaggle/kernels/duecare_00_gemma_exploration/00_gemma_exploration.ipynb:169`, `kaggle/kernels/duecare_01_quickstart/01_quickstart.ipynb:88-112`, `kaggle/kernels/duecare_11_comparative/11_comparative_grading.ipynb:214`. But the band is not compliant yet: 00, 05, 11, 15, 16, and 17 still define notebook-inline scorers or transport clients, which violates the packages-vs-notebooks split and Principle C. `docs/prompts/_shared_discipline.md:52-66`, `docs/prompts/_shared_discipline.md:92-101`

## 1. Per-notebook audit of existing kernels in the band

| Current | Proposed | Decision | Inputs / outputs / impact / runtime | Size | Extract to `duecare.*` | Evidence |
|---|---|---|---|---|---|---|
| `duecare_00_gemma_exploration` | split to `duecare_100_gemma_text_playground` and `duecare_220_gemma_text_sample_eval` | Split. Current notebook answers two questions and should become the 220 notebook after extraction; 100 is a new lightweight shell. | Inputs: Gemma 4 model mounts, wheels, prompt JSONL, rubric YAML. Output: `gemma_baseline_findings.json` schema 2.0. Decision impact: baseline feeds 260, 280, 700. Runtime: single T4, CPU fallback. | 40 cells, about 760 notebook-Python lines, several cells >60 lines. Principle C breach. | Replace inline `score_response` with `duecare.tasks.score_against_rubric`; add `duecare.tasks.batch.select_prompt_subset`; add `duecare.reporting.findings.build_findings_payload`. | `kaggle/kernels/duecare_00_gemma_exploration/00_gemma_exploration.ipynb:10-92`, `kaggle/kernels/duecare_00_gemma_exploration/00_gemma_exploration.ipynb:278-311`, `kaggle/kernels/duecare_00_gemma_exploration/00_gemma_exploration.ipynb:435-655`, `kaggle/kernels/duecare_00_gemma_exploration/00_gemma_exploration.ipynb:1292-1335`, `scripts/build_notebook_00.py:1-120` |
| `duecare_01_quickstart` | `duecare_200_framework_quickstart` | Keep in band. This is the right first framework notebook. | Inputs: wheels only. Outputs: none cached today. Decision impact: pass routes to 220 and 260; failure routes to packaging fixes. Runtime: CPU/free Kaggle. | 14 cells, about 103 notebook-Python lines. No Principle C breach. | No adapter logic to extract. Add cached registry snapshot and dedicated build script. | `kaggle/kernels/duecare_01_quickstart/01_quickstart.ipynb:10-239`, `scripts/build_kaggle_notebooks.py:861-890` |
| `duecare_05_rag_comparison` | `duecare_240_gemma_context_ablation` | Keep, but demote from "full enhanced comparison" to a Gemma-only context ablation. | Inputs: wheels, prompt pack, rubric-derived RAG entries, Gemma mount. Outputs: charts only today. Decision impact: if context helps, build 280; if not, route to 400/700. Runtime: T4. | 20 cells, about 226 notebook-Python lines. Fits Principle C. | Replace inline `generate` with `duecare.models.transformers_adapter.TransformersModel`; replace inline `score` with `duecare.tasks.score_against_rubric`; add `duecare.domains.rag.build_rag_context_from_rubrics`. | `kaggle/kernels/duecare_05_rag_comparison/05_rag_comparison.ipynb:10-69`, `kaggle/kernels/duecare_05_rag_comparison/05_rag_comparison.ipynb:147-174`, `kaggle/kernels/duecare_05_rag_comparison/05_rag_comparison.ipynb:247-290`, `kaggle/kernels/duecare_05_rag_comparison/05_rag_comparison.ipynb:470-510`, `scripts/build_showcase_notebooks.py:850-875` |
| `duecare_07_oss_comparison` | `duecare_260_vs_others_plain` | Keep, but tighten the claim. It is the right plain comparison slot, not the whole advanced comparison band. | Inputs: `gemma_baseline_findings.json` plus published OSS baseline numbers. Outputs: charts only today. Decision impact: if Gemma leads, route to 290 and 900; if not, route to 400 and 700. Runtime: CPU. | 17 cells, about 228 notebook-Python lines. Fits Principle C. | Move hard-coded `MODELS` baseline payload to `duecare.reporting.baselines.load_published_model_baselines`; add cached JSON output and 95% CI block. | `kaggle/kernels/duecare_07_oss_comparison/07_oss_model_comparison.ipynb:10-36`, `kaggle/kernels/duecare_07_oss_comparison/07_oss_model_comparison.ipynb:73-181`, `kaggle/kernels/duecare_07_oss_comparison/07_oss_model_comparison.ipynb:327-406`, `scripts/build_notebook_07_oss_comparison.py:1-120` |
| `duecare_11_comparative` | move to `duecare_420_comparative_grading` | Move out. Anchored LLM-as-judge calibration is advanced evaluation methodology, not a first sample run. | Inputs: graded prompts with best/worst references. Outputs: charts only. Decision impact: routes to advanced judge-method notebooks, not 100-290. Runtime: CPU. | 16 cells, about 158 notebook-Python lines. Fits Principle C. | Add `duecare.tasks.comparative_grading.build_prompt` and `duecare.tasks.comparative_grading.score_against_references`. | `kaggle/kernels/duecare_11_comparative/11_comparative_grading.ipynb:10-71`, `kaggle/kernels/duecare_11_comparative/11_comparative_grading.ipynb:153-266`, `kaggle/kernels/duecare_11_comparative/11_comparative_grading.ipynb:368-398`, `scripts/build_grading_notebooks.py:1714-1718` |
| `duecare_15_ollama_cloud` | move to `duecare_450_ollama_cloud_plain_compare` | Move out. Same-corpus live cloud comparison is useful, but secrets plus cloud egress make it advanced, not early-band. | Inputs: `OLLAMA_API_KEY`, 20 prompts, wheels. Output: `ollama_cloud_comparison_results.json`. Decision impact: advanced comparison only. Runtime: CPU + cloud. | 26 cells, about 315 notebook-Python lines. Principle C breach. | Replace `ollama_chat` with `duecare.models.ollama_adapter.OllamaModel`; replace inline `score_response` with `duecare.tasks.score_against_rubric`. | `kaggle/kernels/duecare_15_ollama_cloud/15_ollama_cloud_comparison.ipynb:10-40`, `kaggle/kernels/duecare_15_ollama_cloud/15_ollama_cloud_comparison.ipynb:155-240`, `kaggle/kernels/duecare_15_ollama_cloud/15_ollama_cloud_comparison.ipynb:319-354`, `kaggle/kernels/duecare_15_ollama_cloud/15_ollama_cloud_comparison.ipynb:570-582`, `scripts/build_notebook_15_ollama_cloud.py:1-120` |
| `duecare_16_mistral_family` | move to `duecare_460_mistral_family_compare` | Move out. Family deep-dive belongs in advanced comparison, not sample eval. | Inputs: `MISTRAL_API_KEY`, 20 prompts, NB00 baseline. Output: `mistral_family_comparison_results.json`. Runtime: CPU + cloud. | 26 cells, about 343 notebook-Python lines. Principle C breach. | Replace inline client with `duecare.models.openai_compatible_adapter.OpenAICompatibleModel`; replace inline scorer with `duecare.tasks.score_against_rubric`. | `kaggle/kernels/duecare_16_mistral_family/16_mistral_family_comparison.ipynb:10-34`, `kaggle/kernels/duecare_16_mistral_family/16_mistral_family_comparison.ipynb:153-232`, `kaggle/kernels/duecare_16_mistral_family/16_mistral_family_comparison.ipynb:309-400`, `kaggle/kernels/duecare_16_mistral_family/16_mistral_family_comparison.ipynb:596-608`, `scripts/build_notebook_16_mistral_family.py:1-120` |
| `duecare_17_openrouter_frontier` | move to `duecare_470_frontier_compare` | Move out. Frontier-vs-on-device is a headline advanced-comparison notebook, not the first evaluation band. | Inputs: `OPENROUTER_API_KEY`, 20 prompts, NB00 baseline. Output: `frontier_comparison_results.json`. Runtime: CPU + cloud. | 25 cells, about 346 notebook-Python lines, one 70-line code cell. Principle C breach. | Replace inline client with `duecare.models.openai_compatible_adapter.OpenAICompatibleModel`; replace inline scorer with `duecare.tasks.score_against_rubric`. | `kaggle/kernels/duecare_17_openrouter_frontier/17_openrouter_frontier_comparison.ipynb:10-35`, `kaggle/kernels/duecare_17_openrouter_frontier/17_openrouter_frontier_comparison.ipynb:166-235`, `kaggle/kernels/duecare_17_openrouter_frontier/17_openrouter_frontier_comparison.ipynb:316-403`, `kaggle/kernels/duecare_17_openrouter_frontier/17_openrouter_frontier_comparison.ipynb:595-607`, `scripts/build_notebook_17_openrouter_frontier.py:1-120` |
| `forge_llm_core_demo.ipynb` | delete | Delete. It is a package-surface exercise notebook, not a judge-facing story, and its quickstart/protocol/registry overlap is already covered more concisely by 01. | Inputs: local wheel or PyPI install. Outputs: none. Decision impact: none for the Kaggle curriculum. Runtime: local only. | 22 cells, about 297 notebook-Python lines, one 65-line code cell. Principle C near-breach. | Move any valuable snippets into package docs or tests, not a new kernel. | `notebooks/forge_llm_core_demo.ipynb:10-34`, `notebooks/forge_llm_core_demo.ipynb:229-293`, `notebooks/forge_llm_core_demo.ipynb:469-533`, `kaggle/kernels/duecare_01_quickstart/01_quickstart.ipynb:10-239`, `docs/prompts/01_exploration_and_basic_eval.md:85-101` |

## 2. Target section map for bands 100 to 290

| Band | Section | Scope | Rubric dimensions advanced | Summary notebook goal | Free slots |
|---|---|---|---|---|---|
| 100-190 | Exploration | Raw Gemma text and multimodal play on the same trafficking prompts, with no rubric yet. | Video, Impact, Tech | Show judges what Gemma actually sounds like before grading starts. | 120, 130, 140, 150, 160, 170, 180 |
| 200-290 | Evaluation framework and sample runs | Introduce registries, domain packs, tasks, then run small text, multimodal, plain-comparison, and enhanced-comparison notebooks. | Tech, Video, Impact | Read cached outputs from 220-280 and produce one chart and one paragraph for the writeup. | 210, 250, 270 |

## 3. Full notebook table for the band

| # | Section | Slug | Filename | Old slug if mapped | Kind | Modality | Question | Inputs | Outputs | Decision impact | Dependencies | Runtime | Status | Must/Should/Nice | Build source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | Exploration | `duecare_100_gemma_text_playground` | `100_gemma_text_playground.ipynb` | partial from `duecare_00_gemma_exploration` | demo | text | What do E2B and E4B actually say before we score them? | local Ollama + Kaggle transformers, trafficking prompts | cached prompt/response transcript JSON | routes to 190 and 220 | 000 | local or T4 | gap | Must | `scripts/build_notebook_100_gemma_text_playground.py` |
| 110 | Exploration | `duecare_110_multimodal_playground` | `110_multimodal_playground.ipynb` | none | demo | multimodal | Can Gemma read image and voice trafficking signals in one pass? | `src/demo/multimodal.py`, `src/demo/function_calling.py`, sample media | cached multimodal transcript JSON | routes to 190 and 230 | 100 | local or T4 | gap | Must | `scripts/build_notebook_110_multimodal_playground.py` |
| 190 | Exploration | `duecare_190_exploration_summary` | `190_exploration_summary.ipynb` | none | summary | text | What did raw exploration show before the rubric turned on? | cached outputs from 100/110 | one chart + one paragraph | routes to 200 | 100, 110 | CPU | gap | Must | `scripts/build_notebook_190_exploration_summary.py` |
| 200 | Framework | `duecare_200_framework_quickstart` | `200_framework_quickstart.ipynb` | `duecare_01_quickstart` | demo | text | Can a reader install DueCare, inspect registries, and run one smoke test in 5 minutes? | wheels, `duecare.core`, `duecare.models`, `duecare.domains`, `duecare.tasks` | cached registry snapshot JSON | routes to 220 and 260 | 190 | CPU | exists | Must | new dedicated script; current source is `scripts/build_kaggle_notebooks.py:861-890` |
| 220 | Framework | `duecare_220_gemma_text_sample_eval` | `220_gemma_text_sample_eval.ipynb` | `duecare_00_gemma_exploration` | eval | text | How does stock Gemma 4 score on a 50-prompt trafficking sample? | wheels, Gemma mount, prompt JSONL, rubric YAML | `gemma_baseline_findings.json` + CI summary JSON | routes to 240, 260, 280, 700 | 200 | single T4 | partial | Must | `git mv scripts/build_notebook_00.py -> scripts/build_notebook_220_gemma_text_sample_eval.py` |
| 230 | Framework | `duecare_230_gemma_multimodal_sample_eval` | `230_gemma_multimodal_sample_eval.ipynb` | none | eval | multimodal | Does Gemma keep the same safety quality when the input is image or voice? | media set + multimodal adapter + domain pack | cached multimodal findings JSON | routes to 290 and 700 | 110, 200 | single T4 | gap | Must | `scripts/build_notebook_230_gemma_multimodal_sample_eval.py` |
| 240 | Framework | `duecare_240_gemma_context_ablation` | `240_gemma_context_ablation.ipynb` | `duecare_05_rag_comparison` | eval | text | Does context help Gemma because the problem is knowledge, not capability? | Gemma mount, 20 graded prompts, rubric-derived context | new `gemma_context_ablation.json` | positive delta routes to 280; flat delta routes to 400/700 | 220 | single T4 | partial | Should | new dedicated script; current source is `scripts/build_showcase_notebooks.py:850-875` |
| 260 | Framework | `duecare_260_vs_others_plain` | `260_vs_others_plain.ipynb` | `duecare_07_oss_comparison` | eval | text | On the same small corpus, how does Gemma compare to a few baseline models with no enhancement? | cached 220 outputs + same-corpus competitor outputs | new `vs_others_plain.json` | routes to 280 and 290 | 220 | CPU or cloud cache | partial | Must | `git mv scripts/build_notebook_07_oss_comparison.py -> scripts/build_notebook_260_vs_others_plain.py` |
| 280 | Framework | `duecare_280_vs_others_enhanced` | `280_vs_others_enhanced.ipynb` | none | eval | text | If we add the same prompt engineering and RAG to every model, what changes? | same corpus as 260 + shared enhancement layer | new `vs_others_enhanced.json` | routes to 290 and 700 | 240, 260 | CPU or cloud cache | gap | Must | `scripts/build_notebook_280_vs_others_enhanced.py` |
| 290 | Framework | `duecare_290_basic_eval_summary` | `290_basic_eval_summary.ipynb` | none | summary | text | What is the one chart and one paragraph Taylor should reuse in the writeup? | cached outputs from 220, 230, 240, 260, 280 | one chart PNG + one markdown paragraph | routes to 300 and writeup | 220, 230, 240, 260, 280 | CPU | gap | Must | `scripts/build_notebook_290_basic_eval_summary.py` |

### Routed out of band or deleted

| Current | Action | Reason |
|---|---|---|
| `duecare_02_cross_domain_proof` | Move to `duecare_410_cross_domain_proof` | Uses `WorkflowRunner`, agent registry mutation, and multi-domain proof. That is advanced framework proof, not first-pass evaluation. `kaggle/kernels/duecare_02_cross_domain_proof/02_cross_domain_proof.ipynb:10-311` |
| `duecare_04_submission_walkthrough` | Move to `duecare_040_submission_walkthrough` | This is orientation/meta narrative, not exploration or sample evaluation. `kaggle/kernels/duecare_04_submission_walkthrough/04_submission_walkthrough.ipynb:10-301` |
| `duecare_11_comparative` | Move to `duecare_420_comparative_grading` | Judge calibration belongs in advanced evaluation methods. `kaggle/kernels/duecare_11_comparative/11_comparative_grading.ipynb:10-480` |
| `duecare_15_ollama_cloud` | Move to `duecare_450_ollama_cloud_plain_compare` | Secret-backed cloud comparison is advanced, not early. `kaggle/kernels/duecare_15_ollama_cloud/15_ollama_cloud_comparison.ipynb:10-630` |
| `duecare_16_mistral_family` | Move to `duecare_460_mistral_family_compare` | Family deep dive is advanced comparison. `kaggle/kernels/duecare_16_mistral_family/16_mistral_family_comparison.ipynb:10-652` |
| `duecare_17_openrouter_frontier` | Move to `duecare_470_frontier_compare` | Frontier-vs-on-device is a later headline claim. `kaggle/kernels/duecare_17_openrouter_frontier/17_openrouter_frontier_comparison.ipynb:10-659` |
| `forge_llm_core_demo.ipynb` | Delete | Local package-surface exercise, redundant with 01 for the notebook curriculum. `notebooks/forge_llm_core_demo.ipynb:10-34`, `kaggle/kernels/duecare_01_quickstart/01_quickstart.ipynb:10-239` |

### Proposed `git mv` block

```bash
git mv kaggle/kernels/duecare_00_gemma_exploration kaggle/kernels/duecare_220_gemma_text_sample_eval
git mv notebooks/00_gemma_exploration.ipynb notebooks/220_gemma_text_sample_eval.ipynb
git mv scripts/build_notebook_00.py scripts/build_notebook_220_gemma_text_sample_eval.py

git mv kaggle/kernels/duecare_01_quickstart kaggle/kernels/duecare_200_framework_quickstart
git mv notebooks/01_quickstart.ipynb notebooks/200_framework_quickstart.ipynb

git mv kaggle/kernels/duecare_05_rag_comparison kaggle/kernels/duecare_240_gemma_context_ablation
git mv notebooks/05_rag_comparison.ipynb notebooks/240_gemma_context_ablation.ipynb

git mv kaggle/kernels/duecare_07_oss_comparison kaggle/kernels/duecare_260_vs_others_plain
git mv notebooks/07_oss_model_comparison.ipynb notebooks/260_vs_others_plain.ipynb
git mv scripts/build_notebook_07_oss_comparison.py scripts/build_notebook_260_vs_others_plain.py

git mv kaggle/kernels/duecare_02_cross_domain_proof kaggle/kernels/duecare_410_cross_domain_proof
git mv notebooks/02_cross_domain_proof.ipynb notebooks/410_cross_domain_proof.ipynb

git mv kaggle/kernels/duecare_11_comparative kaggle/kernels/duecare_420_comparative_grading
git mv notebooks/11_comparative_grading.ipynb notebooks/420_comparative_grading.ipynb

git mv kaggle/kernels/duecare_15_ollama_cloud kaggle/kernels/duecare_450_ollama_cloud_plain_compare
git mv notebooks/15_ollama_cloud_comparison.ipynb notebooks/450_ollama_cloud_plain_compare.ipynb
git mv scripts/build_notebook_15_ollama_cloud.py scripts/build_notebook_450_ollama_cloud_plain_compare.py

git mv kaggle/kernels/duecare_16_mistral_family kaggle/kernels/duecare_460_mistral_family_compare
git mv notebooks/16_mistral_family_comparison.ipynb notebooks/460_mistral_family_compare.ipynb
git mv scripts/build_notebook_16_mistral_family.py scripts/build_notebook_460_mistral_family_compare.py

git mv kaggle/kernels/duecare_17_openrouter_frontier kaggle/kernels/duecare_470_frontier_compare
git mv notebooks/17_openrouter_frontier_comparison.ipynb notebooks/470_frontier_compare.ipynb
git mv scripts/build_notebook_17_openrouter_frontier.py scripts/build_notebook_470_frontier_compare.py

git mv kaggle/kernels/duecare_04_submission_walkthrough kaggle/kernels/duecare_040_submission_walkthrough
git mv notebooks/04_submission_walkthrough.ipynb notebooks/040_submission_walkthrough.ipynb

git rm notebooks/forge_llm_core_demo.ipynb
```

### `kernel-metadata.json` id edits

- `kaggle/kernels/duecare_220_gemma_text_sample_eval/kernel-metadata.json`: `taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts` -> `taylorsamarel/duecare-220-gemma-text-sample-eval`
- `kaggle/kernels/duecare_200_framework_quickstart/kernel-metadata.json`: `taylorsamarel/01-duecare-quickstart-generalized-framework` -> `taylorsamarel/duecare-200-framework-quickstart`
- `kaggle/kernels/duecare_240_gemma_context_ablation/kernel-metadata.json`: `taylorsamarel/duecare-rag-comparison` -> `taylorsamarel/duecare-240-gemma-context-ablation`
- `kaggle/kernels/duecare_260_vs_others_plain/kernel-metadata.json`: `taylorsamarel/gemma-4-vs-llama-vs-mistral-on-trafficking-safety` -> `taylorsamarel/duecare-260-vs-others-plain`
- `kaggle/kernels/duecare_410_cross_domain_proof/kernel-metadata.json`: `taylorsamarel/duecare-cross-domain-proof` -> `taylorsamarel/duecare-410-cross-domain-proof`
- `kaggle/kernels/duecare_420_comparative_grading/kernel-metadata.json`: `taylorsamarel/duecare-comparative-grading` -> `taylorsamarel/duecare-420-comparative-grading`
- `kaggle/kernels/duecare_450_ollama_cloud_plain_compare/kernel-metadata.json`: `taylorsamarel/duecare-gemma-4-vs-6-oss-models-via-ollama-cloud` -> `taylorsamarel/duecare-450-ollama-cloud-plain-compare`
- `kaggle/kernels/duecare_460_mistral_family_compare/kernel-metadata.json`: `taylorsamarel/duecare-gemma-4-vs-mistral-family` -> `taylorsamarel/duecare-460-mistral-family-compare`
- `kaggle/kernels/duecare_470_frontier_compare/kernel-metadata.json`: `taylorsamarel/duecare-vs-large-cloud-models` -> `taylorsamarel/duecare-470-frontier-compare`
- `kaggle/kernels/duecare_040_submission_walkthrough/kernel-metadata.json`: `taylorsamarel/duecare-submission-walkthrough` -> `taylorsamarel/duecare-040-submission-walkthrough`

### New build scripts required for gap rows

- `scripts/build_notebook_100_gemma_text_playground.py`
- `scripts/build_notebook_110_multimodal_playground.py`
- `scripts/build_notebook_190_exploration_summary.py`
- `scripts/build_notebook_200_framework_quickstart.py`
- `scripts/build_notebook_230_gemma_multimodal_sample_eval.py`
- `scripts/build_notebook_240_gemma_context_ablation.py`
- `scripts/build_notebook_280_vs_others_enhanced.py`
- `scripts/build_notebook_290_basic_eval_summary.py`

## 4. Gap list

- `duecare_100_gemma_text_playground`: missing raw text-only playground that covers local Ollama plus Kaggle transformers without rubric scoring. Required by target 1. Effort L. `docs/prompts/01_exploration_and_basic_eval.md:26-33`, `kaggle/kernels/duecare_00_gemma_exploration/00_gemma_exploration.ipynb:10-92`
- `duecare_110_multimodal_playground`: missing voice/image exploration notebook grounded in the existing demo surfaces. Required by target 2. Effort M. `docs/prompts/01_exploration_and_basic_eval.md:30-33`
- `duecare_190_exploration_summary`: missing cached exploration rollup. Required by Principle D. Effort S. `docs/prompts/_shared_discipline.md:95-101`
- `duecare_220_gemma_text_sample_eval`: current 00 lacks the band split, 95% CI, and package-owned scoring path. Required by target 4. Effort M. `docs/prompts/01_exploration_and_basic_eval.md:38-45`, `kaggle/kernels/duecare_00_gemma_exploration/00_gemma_exploration.ipynb:679-715`
- `duecare_230_gemma_multimodal_sample_eval`: no current notebook evaluates image/voice safety with the same rubric. Required by target 5. Effort M. `docs/prompts/01_exploration_and_basic_eval.md:40-41`
- `duecare_240_gemma_context_ablation`: current 05 is useful but does not persist a cached artifact and still carries inline generation/scoring logic. Effort M. `kaggle/kernels/duecare_05_rag_comparison/05_rag_comparison.ipynb:247-290`
- `duecare_260_vs_others_plain`: current 07 compares mixed-provenance numbers, not a shared 50-prompt in-band sample with CI. Required by target 6. Effort M. `docs/prompts/01_exploration_and_basic_eval.md:42-43`, `kaggle/kernels/duecare_07_oss_comparison/07_oss_model_comparison.ipynb:73-181`
- `duecare_280_vs_others_enhanced`: completely missing notebook that holds the model set constant and applies identical prompt engineering/RAG across all models. Required by target 7. Effort L. `docs/prompts/01_exploration_and_basic_eval.md:43-44`
- `duecare_290_basic_eval_summary`: missing cached section rollup for 220-280. Required by target 8 and Principle D. Effort S. `docs/prompts/01_exploration_and_basic_eval.md:45-46`, `docs/prompts/_shared_discipline.md:95-101`

## 5. Ticket list for this band

`[P0][L][Tech][Anti-Slop] Split duecare_00_gemma_exploration into duecare_100 and duecare_220`

`[P0][M][Video][Coverage] Build duecare_110_multimodal_playground from src/demo/multimodal.py surfaces`

`[P0][S][Tech][Repro] Add 95% CI block and cached JSON artifact to duecare_220_gemma_text_sample_eval`

`[P0][M][Impact][Coverage] Build duecare_230_gemma_multimodal_sample_eval as the image/voice sibling of 220`

`[P0][M][Tech][Extraction] Replace 00 inline score_response with duecare.tasks.score_against_rubric`

`[P0][M][Tech][Extraction] Replace 05 inline generate/score path with duecare.models + duecare.tasks helpers`

`[P0][M][Tech][Anti-Slop] Rebuild duecare_260_vs_others_plain on one shared corpus, not mixed published baselines`

`[P0][L][Impact][Ablation] Gap-build duecare_280_vs_others_enhanced with identical RAG across every model`

`[P0][S][Video][Summary] Build duecare_290_basic_eval_summary from cached 220-280 outputs only`

`[P0][S][Tech][Principle-H] Add dedicated build_notebook_200 and build_notebook_240 scripts; retire aggregate ownership`

`[P0][S][Tech][Cleanup] Delete notebooks/forge_llm_core_demo.ipynb and remove orphan status from notebook inventory`

`[P1][M][Tech][Anti-Slop] Shrink duecare_15 under 300 notebook-Python lines by moving API/scoring logic into packages`

`[P1][M][Tech][Anti-Slop] Shrink duecare_16 under 300 notebook-Python lines by using OpenAICompatibleModel`

`[P1][M][Tech][Anti-Slop] Shrink duecare_17 under 300 notebook-Python lines and split its 70-line client cell`

`[P1][S][Repro][Mirror] Resync notebooks/ mirror after all kernel renames in bands 100-290 and routed-out moves`