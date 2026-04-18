# 300-390 Data Pipeline Review

## 0. Band scope and grounding

Band 300-390 should turn source material into a training-ready corpus: ingest documents, classify and distill them, generate or remix prompts, enforce the Anonymizer gate, and hand off split JSONL plus summary metrics. The package boundary is already defined in code: duecare.domains.pipeline exports fetch_url, fetch_convention, extract_facts, classify_fact, and DocumentStore from one module surface at packages/duecare-llm-domains/src/duecare/domains/pipeline/__init__.py:14-18, while the concrete scraper, extractor, classifier, and store live at packages/duecare-llm-domains/src/duecare/domains/pipeline/scraper.py:24,96, packages/duecare-llm-domains/src/duecare/domains/pipeline/extractor.py:35,114, packages/duecare-llm-domains/src/duecare/domains/pipeline/classifier.py:58,165, and packages/duecare-llm-domains/src/duecare/domains/pipeline/document_store.py:45,88,145. Current kernels already consume package surfaces rather than raw repo internals: 00a imports duecare.domains at kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:139, 00b does the same at kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:150, and 12 imports duecare.tasks.generators, PromptValidator, and ImportanceRanker at kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb:203,249,274. The safety contract is explicit: raw PII cannot enter training data and audit logs must store hashes, not plaintext, per .claude/rules/10_safety_gate.md:18,29; the current Anonymizer implementation writes original_hash and emits clean_probes, anon_audit, and quarantine at packages/duecare-llm-agents/src/duecare/agents/anonymizer/anonymizer.py:36,50,78-80.

## 1. Per-notebook audit of existing kernels in the band

| Kernel | Principle B header audit | Notebook audit | Logic to extract into duecare.* | Safety / provenance | Mapping |
|---|---|---|---|---|---|
| 00a | Question: which seed prompts deserve the first GPU budget. Inputs/outputs/runtime are explicit in the header at kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:33,38-41. Decision impact is downstream to 00b and 00 at kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:41,80. Kind=`build`, modality=`text`, runtime=`CPU/no GPU`. | 21 cells, about 406 notebook-Python lines, so it breaches Principle C's 300-line cap from docs/prompts/_shared_discipline.md:86-94. | Extract `map_primary_categories`, `get_primary_category`, `score_source_priority`, `select_curated_prompts`, and `write_curated_prompts` from the inline category map and selection logic at kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:139,178,274,334,495 into duecare.domains.pipeline.curation. | No raw-doc handling here, but provenance is still thin: output is just curated_prompts.jsonl at kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:39,495-500 and carries prompt ids/source tags rather than run_id/git_sha/checksum. | Stay in band as 300. |
| 00b | Question: how do curated prompts change under deterministic adversarial wrappers. Inputs/outputs/runtime are explicit at kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:33,40-43. Decision impact is downstream to 00 at kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:43,87-89. Kind=`build`, modality=`text`, runtime=`CPU/no GPU`. | 16 cells, about 278 notebook-Python lines. It stays under the 300-line cap but has overlong code cells. | Extract `mutate_academic`, `mutate_roleplay`, `mutate_corporate`, `mutate_urgency`, `mutate_corridor`, and `generate_remixed_prompts` from kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:178,287,392 into duecare.domains.pipeline.remixer or duecare.tasks.generators.remixer. | Provenance is partial: mutations keep category, difficulty, source, and base_prompt_id/mutation_strategy at kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:312-319, but they drop graded_responses entirely at kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:316, which violates the prompt's requirement that remixes preserve the 5-band mapping. | Stay in band as 370, but only after graded-response preservation is restored. |
| 12 | Question: what does the full generator suite produce after validation and ranking. The notebook states it is in the grading pipeline, not the data pipeline, at kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb:26,34-37. Its own summary says the output is ready for model evaluation and Phase 3 fine-tuning at kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb:107,302,334. Kind=`build/eval bridge`, modality=`text`, runtime=`CPU/no GPU`. | 18 cells, about 193 notebook-Python lines. No total-line breach, but the main generator cell is just over the 60-line limit. | Remove the fallback generator, validator, and ranker definitions from the notebook and rely only on duecare.tasks.generators.ALL_GENERATORS, PromptValidator, and ImportanceRanker at kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb:203,249,274. | It claims privacy at the narrative level at kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb:233,302,318, but it does not wire the Anonymizer package directly. It also does not persist a canonical artifact path, so provenance stops at in-memory `all_variations`. | Move inside this band to 375 as the advanced factory, not 340-360. |
| 19 | Question: how should one judge precomputed model responses with per-prompt rubrics. It consumes precomputed Gemma results and API secrets at kaggle/kernels/duecare_19_rubric_generator/19_per_prompt_rubric_generator.ipynb:66-71,111-123,158-160, and writes findings/results JSON at kaggle/kernels/duecare_19_rubric_generator/19_per_prompt_rubric_generator.ipynb:691,701,705. That is evaluation, not corpus construction. Kind=`eval`, modality=`text`, runtime=`API + CPU, no GPU`. | 22 cells, about 479 notebook-Python lines, with two very large code cells; this is the worst Principle C breach in the current set. | Extract `generate_rubric_via_api`, `fallback_rubric`, `grade_criterion`, and `classify_failure_band` from kaggle/kernels/duecare_19_rubric_generator/19_per_prompt_rubric_generator.ipynb:213-324,344-478 into duecare.tasks or prompt 03's evaluation layer. | No raw-document PII path here; provenance is response-level, not data-pipeline provenance. The kernel is also a legacy alias in the inventory at docs/current_kaggle_notebook_state.md:28,63. | Move out to band 430 in prompt 03. |

## 2. Target section map for band 300 to 390

- 300. Seed corpus triage and prioritization. Advances coverage, reproducibility, and evaluation efficiency before any GPU run. Existing 00a already fits here: docs/current_kaggle_notebook_state.md:43; kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:33,38-41.
- 310-330. Acquire and categorize documents, then distill ExtractedFact records. This is the missing load-bearing path the package layer already exposes through fetch_url, fetch_convention, classify_fact, and extract_facts at packages/duecare-llm-domains/src/duecare/domains/pipeline/__init__.py:14-18.
- 340-360. Generate prompts from facts, dedupe/link provenance, and synthesize graded references using the trafficking rubric/taxonomy surfaces at configs/duecare/domains/trafficking/card.yaml:17-18, configs/duecare/domains/trafficking/taxonomy.yaml:29,42,54,66, and configs/duecare/domains/trafficking/rubric.yaml:4,11,14,42-43.
- 370-380. Remix and amplify prompts, then assemble final train/val/test JSONL. 00b belongs at 370, 12 belongs at 375, and 380 should wrap scripts/extract_benchmark_prompts.py:4-5,372 plus scripts/prepare_training_data.py:15-18,270,297-322.
- 390. Summary notebook only. It reads cached corpus stats and emits one chart plus one paragraph, per docs/prompts/_shared_discipline.md:95-97.
- Free insertion slots after the renumber pass: 310, 320, 330, 340, 350, 360, 380, 390. Slot 375 is reserved for the current 12 notebook after it moves off the monolithic grading builder.

## 3. Full notebook table for the band

| # | Section | Slug | Filename | Old slug if mapped | Kind | Modality | Question | Inputs | Outputs | Decision impact | Dependencies | Runtime | Status | Must/Should/Nice | Build source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 300 | Prioritize seed corpus | duecare_300_prompt_prioritizer | 300_prompt_prioritizer.ipynb | duecare_00a_prompt_prioritizer | build | text | Which source prompts should define the first-pass corpus? | seed_prompts.jsonl | curated_prompts.jsonl | Gates 370 and 400 | duecare.domains, curation helpers | CPU | existing, rename + extract | Must | scripts/build_notebook_00a.py:444-447 |
| 310 | Acquire documents | duecare_310_document_acquisition | 310_document_acquisition.ipynb | — | build | text | Which raw documents are fetched and cached? | URLs / source registry | raw_documents.jsonl | Feeds 320 | duecare.domains.pipeline.fetch_url/fetch_convention | CPU + internet | gap | Must | scripts/build_notebook_310_document_acquisition.py |
| 320 | Categorize + anonymize | duecare_320_document_categorization | 320_document_categorization.ipynb | — | build | text | How are raw docs labeled and gated before downstream use? | raw_documents.jsonl | categorized_documents.jsonl, anon_audit.jsonl | Feeds 330-380 | classify_fact, AnonymizerAgent | CPU | gap | Must | scripts/build_notebook_320_document_categorization.py |
| 330 | Distill facts | duecare_330_fact_distillation | 330_fact_distillation.ipynb | — | build | text | Which structured facts are extracted from clean documents? | categorized_documents.jsonl | extracted_facts.jsonl | Feeds 340-360 | extract_facts, DocumentStore | CPU | gap | Must | scripts/build_notebook_330_fact_distillation.py |
| 340 | Generate prompts from facts | duecare_340_prompt_generation | 340_prompt_generation.ipynb | — | build | text | Which new prompts can be generated from extracted facts? | extracted_facts.jsonl | generated_prompts.jsonl | Feeds 350-380 | trafficking taxonomy/rubric + generation helpers | CPU | gap | Must | scripts/build_notebook_340_prompt_generation.py |
| 350 | Dedupe + provenance | duecare_350_prompt_dedup_provenance | 350_prompt_dedup_provenance.ipynb | — | build | text | Which generated prompts survive dedupe and provenance checks? | generated_prompts.jsonl, seed corpus | deduped_generated_prompts.jsonl | Feeds 360-380 | DocumentStore, checksum/provenance helpers | CPU | gap | Must | scripts/build_notebook_350_prompt_dedup_provenance.py |
| 360 | Grade anchor synthesis | duecare_360_graded_response_synthesis | 360_graded_response_synthesis.ipynb | — | build | text | What worst/bad/neutral/good/best references attach to each generated prompt? | deduped prompts, rubric.yaml | graded_generated_prompts.jsonl | Feeds 370-380 | rubric.yaml grade scale and legal-source constraints | CPU/API optional | gap | Must | scripts/build_notebook_360_graded_response_synthesis.py |
| 370 | Deterministic remixer | duecare_370_prompt_remixer | 370_prompt_remixer.ipynb | duecare_00b_prompt_remixer | build | text | Which deterministic adversarial wrappers preserve the original labels? | curated/graded prompts | remixed_prompts.jsonl | Feeds 375 and 400 | remixer helpers | CPU | existing, rename + fix label carryover | Must | scripts/build_notebook_00b.py:372-375 |
| 375 | Advanced factory | duecare_375_prompt_factory | 375_prompt_factory.ipynb | duecare_12_prompt_factory | build | text | Which generator families produce the highest-value valid variants? | graded base prompts | validated_ranked_variations.jsonl | Feeds 380 and 400 | duecare.tasks.generators, PromptValidator, ImportanceRanker | CPU | existing, move + dedicated builder | Should | scripts/build_grading_notebooks.py:1715 |
| 380 | Dataset assembly | duecare_380_dataset_assembly | 380_dataset_assembly.ipynb | — | build | text | What exact train/val/test corpus is handed to downstream evaluation and fine-tuning? | seed + generated + remixed corpus | train.jsonl, val.jsonl, test.jsonl, manifest.json | Hands off to band 400 and 700 | scripts/extract_benchmark_prompts.py, scripts/prepare_training_data.py, TrainingExample/TrainingDatasetManifest | CPU | gap | Must | scripts/build_notebook_380_dataset_assembly.py |
| 390 | Summary | duecare_390_data_pipeline_summary | 390_data_pipeline_summary.ipynb | — | summary | text | What did the pipeline produce and how clean is it? | cached 310-380 outputs | one chart + one paragraph | Feeds writeup/video | cached JSONL + manifest only | CPU | gap | Must | scripts/build_notebook_390_data_pipeline_summary.py |
| 430 | Move out | duecare_430_per_prompt_rubric_evaluator | 430_per_prompt_rubric_evaluator.ipynb | duecare_19_rubric_generator | eval | text | How should precomputed model responses be judged? | gemma_baseline_findings.json, API keys | rubric findings JSON | Owned by prompt 03, not this band | rubric generator + scorer logic | API + CPU | move out | Must | scripts/build_notebook_19_rubric_generator.py:35-38 |

git mv block

```bash
git mv kaggle/kernels/duecare_00a_prompt_prioritizer kaggle/kernels/duecare_300_prompt_prioritizer
git mv notebooks/00a_prompt_prioritizer.ipynb notebooks/300_prompt_prioritizer.ipynb
git mv kaggle/kernels/duecare_00b_prompt_remixer kaggle/kernels/duecare_370_prompt_remixer
git mv notebooks/00b_prompt_remixer.ipynb notebooks/370_prompt_remixer.ipynb
git mv kaggle/kernels/duecare_12_prompt_factory kaggle/kernels/duecare_375_prompt_factory
git mv notebooks/12_prompt_factory.ipynb notebooks/375_prompt_factory.ipynb
git mv kaggle/kernels/duecare_19_rubric_generator kaggle/kernels/duecare_430_per_prompt_rubric_evaluator
git mv notebooks/19_per_prompt_rubric_generator.ipynb notebooks/430_per_prompt_rubric_evaluator.ipynb
```

kernel-metadata.json id edits

```text
duecare_300_prompt_prioritizer -> taylorsamarel/duecare-300-prompt-prioritizer
duecare_370_prompt_remixer -> taylorsamarel/duecare-370-prompt-remixer
duecare_375_prompt_factory -> taylorsamarel/duecare-375-prompt-factory
duecare_430_per_prompt_rubric_evaluator -> taylorsamarel/duecare-430-per-prompt-rubric-evaluator
```

## 4. Data lineage map

```text
310 raw_documents
  duecare_310_document_acquisition -> duecare.domains.pipeline.fetch_url / fetch_convention
  checks: fetch success, source allowlist, checksum
  logs: run_id, git_sha, source_url, checksum
  produces: data/generated_prompts/raw_documents.jsonl
    |
    | schema = RawDocument; dedupe = DocumentStore content hash
    v
320 categorized_clean_documents
  duecare_320_document_categorization -> classify_fact + AnonymizerAgent
  checks: sector/corridor/severity labels, PII gate, hash-only audit
  logs: run_id, git_sha, checksum, anon_audit hashes
  produces: categorized_documents.jsonl + anon_audit.jsonl
    |
    | schema = ClassifiedFact + clean document envelope
    v
330 extracted_facts
  duecare_330_fact_distillation -> extract_facts + DocumentStore
  checks: legal citations, money, orgs, dates, duplicate facts
  logs: run_id, git_sha, source_record_id, checksum
  produces: extracted_facts.jsonl
    |
    | schema = ExtractedFact / ClassifiedFact
    v
340 generated_prompts
  duecare_340_prompt_generation -> new prompt generator over facts + trafficking rubric/taxonomy
  checks: category coverage, source linkage, graded shell created
  logs: run_id, git_sha, parent fact ids, checksum
  produces: generated_prompts.jsonl
    |
    | dedupe against seed corpus from scripts/extract_benchmark_prompts.py:4-5,372
    v
350 deduped_generated_prompts
  duecare_350_prompt_dedup_provenance -> DocumentStore + checksum helpers
  checks: duplicate collapse, provenance completeness
  logs: run_id, git_sha, checksum, parent ids
  produces: deduped_generated_prompts.jsonl
    |
    | graded references attached under rubric.yaml grade scale at configs/duecare/domains/trafficking/rubric.yaml:4,11,14
    v
370/375 remixed_prompt_corpus
  duecare_370_prompt_remixer / duecare_375_prompt_factory -> remixer + ALL_GENERATORS
  checks: graded mapping preserved, mutation metadata, validation/ranking
  logs: run_id, git_sha, base_prompt_id, mutation_strategy, checksum
  produces: remixed_prompts.jsonl + validated_ranked_variations.jsonl
    |
    | dataset contract = TrainingExample / TrainingDatasetManifest at packages/duecare-llm-core/src/duecare/core/schemas/pipeline.py:593,711
    v
380 training_ready_jsonl
  duecare_380_dataset_assembly -> scripts/prepare_training_data.py:54-56,138,186,234,270,297-322
  checks: split assignment, source checksum, split checksums
  logs: run_id, git_sha, checksum, split
  produces: data/training/train.jsonl, val.jsonl, test.jsonl, manifest.json
    |
    | hand-off only
    +-> band 400 evaluation
    +-> band 700 fine-tuning
```

## 5. Ticket list for this band

[P0][M][Tech][Boundary] Split duecare_12_prompt_factory out of scripts/build_grading_notebooks.py into a dedicated 375 builder
[P0][M][Tech][Data] Add duecare_310_document_acquisition over fetch_url and fetch_convention with cached raw_documents.jsonl
[P0][M][Tech][Safety] Add duecare_320_document_categorization to run classify_fact then AnonymizerAgent before any downstream read
[P0][M][Tech][Extraction] Add duecare_330_fact_distillation over extract_facts with fee-structure and employer-name extensions
[P0][M][Tech][Generation] Build duecare_340_prompt_generation to create 5-band prompts from ExtractedFact records with source linkage
[P0][S][Repro] Build duecare_350_prompt_dedup_provenance to enforce checksum-backed dedupe before remixing
[P0][S][Safety] Restore graded_responses carryover in duecare_370_prompt_remixer; current mutations null it out
[P0][M][Tech][Assembly] Build duecare_380_dataset_assembly notebook over extract_benchmark_prompts and prepare_training_data
[P0][M][Video][Summary] Build duecare_390_data_pipeline_summary with counts chart, dedupe rate, anonymization hit rate, provenance coverage
[P1][S][Tech][Classifier] Extend classify_fact to emit the 5 attack-category bands, not only exploitation_type/severity
[P1][S][Tech][Notebook] Extract 00a inline curation logic into duecare.domains.pipeline.curation to clear the 300-line cap breach
[P1][S][Tech][Notebook] Extract 00b inline mutators into duecare.domains.pipeline.remixer and cap each code cell at 60 lines
[P1][S][Tech][Notebook] Move duecare_19_rubric_generator to prompt 03 because it consumes model responses and writes evaluation artifacts
[P2][S][Docs][Legacy] Replace the missing direct legacy scraper citation path with a stable reference note to CLAUDE.md and _reference/framework docs# 300-390 Data Pipeline Review

## 0. Band scope and grounding

Band 300-390 should turn source material into a training-ready corpus: ingest documents, classify and distill them, generate or remix prompts, enforce the Anonymizer gate, and hand off split JSONL plus summary metrics. The package boundary is already defined in code: duecare.domains.pipeline exports fetch_url, fetch_convention, extract_facts, classify_fact, and DocumentStore from one module surface at packages/duecare-llm-domains/src/duecare/domains/pipeline/__init__.py:14-18, while the concrete scraper, extractor, classifier, and store live at packages/duecare-llm-domains/src/duecare/domains/pipeline/scraper.py:24,96, packages/duecare-llm-domains/src/duecare/domains/pipeline/extractor.py:35,114, packages/duecare-llm-domains/src/duecare/domains/pipeline/classifier.py:58,165, and packages/duecare-llm-domains/src/duecare/domains/pipeline/document_store.py:45,88,145. Current kernels already consume package surfaces rather than raw repo internals: 00a imports duecare.domains at kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:139, 00b does the same at kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:150, and 12 imports duecare.tasks.generators, PromptValidator, and ImportanceRanker at kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb:203,249,274. The safety contract is explicit: raw PII cannot enter training data and audit logs must store hashes, not plaintext, per .claude/rules/10_safety_gate.md:18,29; the current Anonymizer implementation writes original_hash and emits clean_probes, anon_audit, and quarantine at packages/duecare-llm-agents/src/duecare/agents/anonymizer/anonymizer.py:36,50,78-80.

## 1. Per-notebook audit of existing kernels in the band

| Kernel | Principle B header audit | Notebook audit | Logic to extract into duecare.* | Safety / provenance | Mapping |
|---|---|---|---|---|---|
| 00a | Question: which seed prompts deserve the first GPU budget. Inputs/outputs/runtime are explicit in the header at kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:33,38-41. Decision impact is downstream to 00b and 00 at kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:41,80. Kind=`build`, modality=`text`, runtime=`CPU/no GPU`. | 21 cells, about 406 notebook-Python lines, so it breaches Principle C's 300-line cap from docs/prompts/_shared_discipline.md:86-94. | Extract `map_primary_categories`, `get_primary_category`, `score_source_priority`, `select_curated_prompts`, and `write_curated_prompts` from the inline category map and selection logic at kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:139,178,274,334,495 into duecare.domains.pipeline.curation. | No raw-doc handling here, but provenance is still thin: output is just curated_prompts.jsonl at kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:39,495-500 and carries prompt ids/source tags rather than run_id/git_sha/checksum. | Stay in band as 300. |
| 00b | Question: how do curated prompts change under deterministic adversarial wrappers. Inputs/outputs/runtime are explicit at kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:33,40-43. Decision impact is downstream to 00 at kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:43,87-89. Kind=`build`, modality=`text`, runtime=`CPU/no GPU`. | 16 cells, about 278 notebook-Python lines. It stays under the 300-line cap but has overlong code cells. | Extract `mutate_academic`, `mutate_roleplay`, `mutate_corporate`, `mutate_urgency`, `mutate_corridor`, and `generate_remixed_prompts` from kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:178,287,392 into duecare.domains.pipeline.remixer or duecare.tasks.generators.remixer. | Provenance is partial: mutations keep category, difficulty, source, and base_prompt_id/mutation_strategy at kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:312-319, but they drop graded_responses entirely at kaggle/kernels/duecare_00b_prompt_remixer/00b_prompt_remixer.ipynb:316, which violates the prompt's requirement that remixes preserve the 5-band mapping. | Stay in band as 370, but only after graded-response preservation is restored. |
| 12 | Question: what does the full generator suite produce after validation and ranking. The notebook states it is in the grading pipeline, not the data pipeline, at kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb:26,34-37. Its own summary says the output is ready for model evaluation and Phase 3 fine-tuning at kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb:107,302,334. Kind=`build/eval bridge`, modality=`text`, runtime=`CPU/no GPU`. | 18 cells, about 193 notebook-Python lines. No total-line breach, but the main generator cell is just over the 60-line limit. | Remove the fallback generator, validator, and ranker definitions from the notebook and rely only on duecare.tasks.generators.ALL_GENERATORS, PromptValidator, and ImportanceRanker at kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb:203,249,274. | It claims privacy at the narrative level at kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb:233,302,318, but it does not wire the Anonymizer package directly. It also does not persist a canonical artifact path, so provenance stops at in-memory `all_variations`. | Move inside this band to 375 as the advanced factory, not 340-360. |
| 19 | Question: how should one judge precomputed model responses with per-prompt rubrics. It consumes precomputed Gemma results and API secrets at kaggle/kernels/duecare_19_rubric_generator/19_per_prompt_rubric_generator.ipynb:66-71,111-123,158-160, and writes findings/results JSON at kaggle/kernels/duecare_19_rubric_generator/19_per_prompt_rubric_generator.ipynb:691,701,705. That is evaluation, not corpus construction. Kind=`eval`, modality=`text`, runtime=`API + CPU, no GPU`. | 22 cells, about 479 notebook-Python lines, with two very large code cells; this is the worst Principle C breach in the current set. | Extract `generate_rubric_via_api`, `fallback_rubric`, `grade_criterion`, and `classify_failure_band` from kaggle/kernels/duecare_19_rubric_generator/19_per_prompt_rubric_generator.ipynb:213-324,344-478 into duecare.tasks or prompt 03's evaluation layer. | No raw-document PII path here; provenance is response-level, not data-pipeline provenance. The kernel is also a legacy alias in the inventory at docs/current_kaggle_notebook_state.md:28,63. | Move out to band 430 in prompt 03. |

## 2. Target section map for band 300 to 390

- 300. Seed corpus triage and prioritization. Advances coverage, reproducibility, and evaluation efficiency before any GPU run. Existing 00a already fits here: docs/current_kaggle_notebook_state.md:43; kaggle/kernels/duecare_00a_prompt_prioritizer/00a_prompt_prioritizer.ipynb:33,38-41.
- 310-330. Acquire and categorize documents, then distill ExtractedFact records. This is the missing load-bearing path the package layer already exposes through fetch_url, fetch_convention, classify_fact, and extract_facts at packages/duecare-llm-domains/src/duecare/domains/pipeline/__init__.py:14-18.
- 340-360. Generate prompts from facts, dedupe/link provenance, and synthesize graded references using the trafficking rubric/taxonomy surfaces at configs/duecare/domains/trafficking/card.yaml:17-18, configs/duecare/domains/trafficking/taxonomy.yaml:29,42,54,66, and configs/duecare/domains/trafficking/rubric.yaml:4,11,14,42-43.
- 370-380. Remix and amplify prompts, then assemble final train/val/test JSONL. 00b belongs at 370, 12 belongs at 375, and 380 should wrap scripts/extract_benchmark_prompts.py:4-5,372 plus scripts/prepare_training_data.py:15-18,270,297-322.
- 390. Summary notebook only. It reads cached corpus stats and emits one chart plus one paragraph, per docs/prompts/_shared_discipline.md:95-97.
- Free insertion slots after the renumber pass: 310, 320, 330, 340, 350, 360, 380, 390. Slot 375 is reserved for the current 12 notebook after it moves off the monolithic grading builder.

## 3. Full notebook table for the band

| # | Section | Slug | Filename | Old slug if mapped | Kind | Modality | Question | Inputs | Outputs | Decision impact | Dependencies | Runtime | Status | Must/Should/Nice | Build source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 300 | Prioritize seed corpus | duecare_300_prompt_prioritizer | 300_prompt_prioritizer.ipynb | duecare_00a_prompt_prioritizer | build | text | Which source prompts should define the first-pass corpus? | seed_prompts.jsonl | curated_prompts.jsonl | Gates 370 and 400 | duecare.domains, curation helpers | CPU | existing, rename + extract | Must | scripts/build_notebook_00a.py:444-447 |
| 310 | Acquire documents | duecare_310_document_acquisition | 310_document_acquisition.ipynb | — | build | text | Which raw documents are fetched and cached? | URLs / source registry | raw_documents.jsonl | Feeds 320 | duecare.domains.pipeline.fetch_url/fetch_convention | CPU + internet | gap | Must | scripts/build_notebook_310_document_acquisition.py |
| 320 | Categorize + anonymize | duecare_320_document_categorization | 320_document_categorization.ipynb | — | build | text | How are raw docs labeled and gated before downstream use? | raw_documents.jsonl | categorized_documents.jsonl, anon_audit.jsonl | Feeds 330-380 | classify_fact, AnonymizerAgent | CPU | gap | Must | scripts/build_notebook_320_document_categorization.py |
| 330 | Distill facts | duecare_330_fact_distillation | 330_fact_distillation.ipynb | — | build | text | Which structured facts are extracted from clean documents? | categorized_documents.jsonl | extracted_facts.jsonl | Feeds 340-360 | extract_facts, DocumentStore | CPU | gap | Must | scripts/build_notebook_330_fact_distillation.py |
| 340 | Generate prompts from facts | duecare_340_prompt_generation | 340_prompt_generation.ipynb | — | build | text | Which new prompts can be generated from extracted facts? | extracted_facts.jsonl | generated_prompts.jsonl | Feeds 350-380 | trafficking taxonomy/rubric + generation helpers | CPU | gap | Must | scripts/build_notebook_340_prompt_generation.py |
| 350 | Dedupe + provenance | duecare_350_prompt_dedup_provenance | 350_prompt_dedup_provenance.ipynb | — | build | text | Which generated prompts survive dedupe and provenance checks? | generated_prompts.jsonl, seed corpus | deduped_generated_prompts.jsonl | Feeds 360-380 | DocumentStore, checksum/provenance helpers | CPU | gap | Must | scripts/build_notebook_350_prompt_dedup_provenance.py |
| 360 | Grade anchor synthesis | duecare_360_graded_response_synthesis | 360_graded_response_synthesis.ipynb | — | build | text | What worst/bad/neutral/good/best references attach to each generated prompt? | deduped prompts, rubric.yaml | graded_generated_prompts.jsonl | Feeds 370-380 | rubric.yaml grade scale and legal-source constraints | CPU/API optional | gap | Must | scripts/build_notebook_360_graded_response_synthesis.py |
| 370 | Deterministic remixer | duecare_370_prompt_remixer | 370_prompt_remixer.ipynb | duecare_00b_prompt_remixer | build | text | Which deterministic adversarial wrappers preserve the original labels? | curated/graded prompts | remixed_prompts.jsonl | Feeds 375 and 400 | remixer helpers | CPU | existing, rename + fix label carryover | Must | scripts/build_notebook_00b.py:372-375 |
| 375 | Advanced factory | duecare_375_prompt_factory | 375_prompt_factory.ipynb | duecare_12_prompt_factory | build | text | Which generator families produce the highest-value valid variants? | graded base prompts | validated_ranked_variations.jsonl | Feeds 380 and 400 | duecare.tasks.generators, PromptValidator, ImportanceRanker | CPU | existing, move + dedicated builder | Should | scripts/build_grading_notebooks.py:1715 |
| 380 | Dataset assembly | duecare_380_dataset_assembly | 380_dataset_assembly.ipynb | — | build | text | What exact train/val/test corpus is handed to downstream evaluation and fine-tuning? | seed + generated + remixed corpus | train.jsonl, val.jsonl, test.jsonl, manifest.json | Hands off to band 400 and 700 | scripts/extract_benchmark_prompts.py, scripts/prepare_training_data.py, TrainingExample/TrainingDatasetManifest | CPU | gap | Must | scripts/build_notebook_380_dataset_assembly.py |
| 390 | Summary | duecare_390_data_pipeline_summary | 390_data_pipeline_summary.ipynb | — | summary | text | What did the pipeline produce and how clean is it? | cached 310-380 outputs | one chart + one paragraph | Feeds writeup/video | cached JSONL + manifest only | CPU | gap | Must | scripts/build_notebook_390_data_pipeline_summary.py |
| 430 | Move out | duecare_430_per_prompt_rubric_evaluator | 430_per_prompt_rubric_evaluator.ipynb | duecare_19_rubric_generator | eval | text | How should precomputed model responses be judged? | gemma_baseline_findings.json, API keys | rubric findings JSON | Owned by prompt 03, not this band | rubric generator + scorer logic | API + CPU | move out | Must | scripts/build_notebook_19_rubric_generator.py:35-38 |

git mv block

```bash
git mv kaggle/kernels/duecare_00a_prompt_prioritizer kaggle/kernels/duecare_300_prompt_prioritizer
git mv notebooks/00a_prompt_prioritizer.ipynb notebooks/300_prompt_prioritizer.ipynb
git mv kaggle/kernels/duecare_00b_prompt_remixer kaggle/kernels/duecare_370_prompt_remixer
git mv notebooks/00b_prompt_remixer.ipynb notebooks/370_prompt_remixer.ipynb
git mv kaggle/kernels/duecare_12_prompt_factory kaggle/kernels/duecare_375_prompt_factory
git mv notebooks/12_prompt_factory.ipynb notebooks/375_prompt_factory.ipynb
git mv kaggle/kernels/duecare_19_rubric_generator kaggle/kernels/duecare_430_per_prompt_rubric_evaluator
git mv notebooks/19_per_prompt_rubric_generator.ipynb notebooks/430_per_prompt_rubric_evaluator.ipynb
```

kernel-metadata.json id edits

```text
duecare_300_prompt_prioritizer -> taylorsamarel/duecare-300-prompt-prioritizer
duecare_370_prompt_remixer -> taylorsamarel/duecare-370-prompt-remixer
duecare_375_prompt_factory -> taylorsamarel/duecare-375-prompt-factory
duecare_430_per_prompt_rubric_evaluator -> taylorsamarel/duecare-430-per-prompt-rubric-evaluator
```

## 4. Data lineage map

```text
310 raw_documents
  duecare_310_document_acquisition -> duecare.domains.pipeline.fetch_url / fetch_convention
  checks: fetch success, source allowlist, checksum
  logs: run_id, git_sha, source_url, checksum
  produces: data/generated_prompts/raw_documents.jsonl
    |
    | schema = RawDocument; dedupe = DocumentStore content hash
    v
320 categorized_clean_documents
  duecare_320_document_categorization -> classify_fact + AnonymizerAgent
  checks: sector/corridor/severity labels, PII gate, hash-only audit
  logs: run_id, git_sha, checksum, anon_audit hashes
  produces: categorized_documents.jsonl + anon_audit.jsonl
    |
    | schema = ClassifiedFact + clean document envelope
    v
330 extracted_facts
  duecare_330_fact_distillation -> extract_facts + DocumentStore
  checks: legal citations, money, orgs, dates, duplicate facts
  logs: run_id, git_sha, source_record_id, checksum
  produces: extracted_facts.jsonl
    |
    | schema = ExtractedFact / ClassifiedFact
    v
340 generated_prompts
  duecare_340_prompt_generation -> new prompt generator over facts + trafficking rubric/taxonomy
  checks: category coverage, source linkage, graded shell created
  logs: run_id, git_sha, parent fact ids, checksum
  produces: generated_prompts.jsonl
    |
    | dedupe against seed corpus from scripts/extract_benchmark_prompts.py:4-5,372
    v
350 deduped_generated_prompts
  duecare_350_prompt_dedup_provenance -> DocumentStore + checksum helpers
  checks: duplicate collapse, provenance completeness
  logs: run_id, git_sha, checksum, parent ids
  produces: deduped_generated_prompts.jsonl
    |
    | graded references attached under rubric.yaml grade scale at configs/duecare/domains/trafficking/rubric.yaml:4,11,14
    v
370/375 remixed_prompt_corpus
  duecare_370_prompt_remixer / duecare_375_prompt_factory -> remixer + ALL_GENERATORS
  checks: graded mapping preserved, mutation metadata, validation/ranking
  logs: run_id, git_sha, base_prompt_id, mutation_strategy, checksum
  produces: remixed_prompts.jsonl + validated_ranked_variations.jsonl
    |
    | dataset contract = TrainingExample / TrainingDatasetManifest at packages/duecare-llm-core/src/duecare/core/schemas/pipeline.py:593,711
    v
380 training_ready_jsonl
  duecare_380_dataset_assembly -> scripts/prepare_training_data.py:54-56,138,186,234,270,297-322
  checks: split assignment, source checksum, split checksums
  logs: run_id, git_sha, checksum, split
  produces: data/training/train.jsonl, val.jsonl, test.jsonl, manifest.json
    |
    | hand-off only
    +-> band 400 evaluation
    +-> band 700 fine-tuning
```

## 5. Ticket list for this band

[P0][M][Tech][Boundary] Split duecare_12_prompt_factory out of scripts/build_grading_notebooks.py into a dedicated 375 builder
[P0][M][Tech][Data] Add duecare_310_document_acquisition over fetch_url and fetch_convention with cached raw_documents.jsonl
[P0][M][Tech][Safety] Add duecare_320_document_categorization to run classify_fact then AnonymizerAgent before any downstream read
[P0][M][Tech][Extraction] Add duecare_330_fact_distillation over extract_facts with fee-structure and employer-name extensions
[P0][M][Tech][Generation] Build duecare_340_prompt_generation to create 5-band prompts from ExtractedFact records with source linkage
[P0][S][Repro] Build duecare_350_prompt_dedup_provenance to enforce checksum-backed dedupe before remixing
[P0][S][Safety] Restore graded_responses carryover in duecare_370_prompt_remixer; current mutations null it out
[P0][M][Tech][Assembly] Build duecare_380_dataset_assembly notebook over extract_benchmark_prompts and prepare_training_data
[P0][M][Video][Summary] Build duecare_390_data_pipeline_summary with counts chart, dedupe rate, anonymization hit rate, provenance coverage
[P1][S][Tech][Classifier] Extend classify_fact to emit the 5 attack-category bands, not only exploitation_type/severity
[P1][S][Tech][Notebook] Extract 00a inline curation logic into duecare.domains.pipeline.curation to clear the 300-line cap breach
[P1][S][Tech][Notebook] Extract 00b inline mutators into duecare.domains.pipeline.remixer and cap each code cell at 60 lines
[P1][S][Tech][Notebook] Move duecare_19_rubric_generator to prompt 03 because it consumes model responses and writes evaluation artifacts
[P2][S][Docs][Legacy] Replace the missing direct legacy scraper citation path with a stable reference note to CLAUDE.md and _reference/framework docs