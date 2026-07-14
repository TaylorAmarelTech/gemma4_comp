# DueCare Fine-tuning and Evaluation

> Control-plane appendix for the Gemma 4 Good submission. This notebook is the
> single UI for running batches, rerunning exports, comparing harnesses,
> generating synthetic data, training adapters, processing local research
> bundles, and launching every appendix workflow.

<!-- duecare:lane-label -->
> **Serves lanes:** Researcher; Developer / integration partner; Platform safety; NGO & regulator.

## Judge Quick Path

| Section | This notebook |
|---|---|
| Lede | One interactive workbench that proves what improves quality across harnessing, synthetic data, research graphing, retraining, or combined runs. |
| What it does | Loads one selected model per Kaggle run, runs bulk prompt sets through any harness profile, exports results, imports earlier exports, evaluates with rule and LLM judges, generates synthetic SFT/DPO data, launches LoRA fine-tuning when dependencies are available, processes local case/research bundles into graphs, and exposes A-01 through A-24 as workflows. |
| Demo path | Run all, open the printed Cloudflare URL, load Gemma 4 E2B or a custom model path, run Chat Safety prompts with harness off and on, generate the report, then export the JSON bundle. |
| Audience | Researcher, developer, platform safety, NGO/regulator. |
| Inputs | Prompt libraries, prior run exports, vetted knowledge packs, a manifest-bound SFT/DPO bundle, and an optional custom model directory or exact Hugging Face model id/revision. |
| Outputs | Run/report exports, split SFT and DPO JSONL, row and artifact hashes, a quarantine report, a training-validation manifest, resumable SFT→DPO scripts, completion manifests, and optional LoRA adapter folders. |

## Why A-00 Exists

The other appendix notebooks are intentionally narrow. A-00 is the experiment
workbench. It exists because Kaggle sessions usually hold one loaded model
at a time. Instead of loading and unloading models in one process, A-00 exports
portable bundles:

1. Run the same prompt set on stock Gemma 4 with no harness.
2. Export the results.
3. Restart or rerun with harness enabled, a fine-tuned model, or a fine-tuned
   model plus harness.
4. Import all bundles into A-00 and produce the comparison report.

That report is the technical proof referenced by the writeup: quality lift,
dimension-level deltas, grounding gains, research graph extraction, latency,
throughput, and estimated inference cost.

## Proof Recipes

Use these recipes as the minimum pre-submission validation set:

The page exposes them in the **Quantitative proof profiles** panel so the
same shared contract can be run from the UI or through
`POST /api/a00/quantitative/run`.

1. **Harness lift:** run the shared `bulk_text_25` profile: `chat_safety_core`
   with `No harness`, then the same 25 prompts with `Chat safety harness`, then
   build the HTML/Markdown/JSON report.
2. **Prior red-team regression:** run `anti_tip_redteam_regressions`. This
   prompt set converts the 2025 GPT OSS failure modes into reusable checks:
   business-framed exploitation, jurisdiction shopping, predatory debt,
   prompt-attack formatting, and worker revictimization.
3. **Synthetic training:** run the shared `tiny_lora_smoke` path: generate 24
   rubric-polished SFT/DPO rows, create the tiny LoRA handoff, optionally train
   on GPU, then compare stock, stock+harness, fine-tuned, and fine-tuned+harness.
4. **Research graph:** run the sample local research graph or upload a ZIP with
   notes, CSV, JSONL, images, and documents. Confirm documents, entities, risk
   edges, media queue, and timeline artifacts are exported.
5. **Contact grounding:** use a worker or NGO prompt that asks what to do next.
   The grader should activate civil-society contact, regulator contact,
   contact currency, and consent-aware referral dimensions.

## Supported Workflows

1. **Model loading:** Kaggle-attached model path, Hugging Face id, local upload,
   custom fine-tuned adapter path, or abliterated model id for adversarial
   generation.
2. **Bulk prompt runs:** Run prompt libraries across chat, process,
   extraction, anonymization, search safety, search, and import-corpus
   profiles.
3. **Export and rerun:** Export prompts, responses, metadata, trace, timing,
   and model info. Re-import the same bundle to rerun against another model or
   another harness profile.
4. **Evaluation:** Rule judge, LLM judge, or combined judge with 0 to 10
   dimension scores and dynamic weights based on prompt and harness context.
5. **Knowledge packs:** Sync vetted and unvetted packs from the hub, import
   local packs, and include pack versions in every export.
6. **Synthetic data:** Generate prompt-test scenarios, knowledge facts,
   SFT rows, DPO pairs, and adversarial negatives using harnessed or
   abliterated model runs.
7. **Fine-tuning:** Create and optionally execute a resumable Unsloth LoRA
   job that runs response-only SFT followed by DPO. A requested DPO stage is
   never silently skipped.
8. **Rubric-polished SFT/DPO data:** Use `rubric_polisher` mode to turn
   harness responses into ideal training targets. The generated rows include
   the response blueprint, rubric dimensions, and a memory-versus-tool policy
   so small models learn structure while volatile facts remain tool calls.
9. **Appendix workflow registry:** Select any appendix capability from A-01
   through A-24. A-00 runs lightweight workflows directly and writes handoff
   manifests for focused heavy-GPU reproductions.
10. **Local research graph:** Upload case files, document bundles, images, CSV,
   JSONL, or ZIP files. A-00 extracts documents, entities, people, locations,
   amounts, risk-rule hits, timeline events, and edges into JSON, CSV, HTML,
   and ZIP artifacts.
11. **Local multimodal edge plan:** For large case histories, inventory files
   first, split documents into pages and page items, run local OCR/layout/ASR
   where installed, then use Gemma 4 to propose typed edges over bounded text,
   OCR, metadata, and, for larger multimodal variants, page images. Cloud or
   frontier models can be noted as future enhancement, but the demo path keeps
   raw case material local.
12. **Prompt-tree experimentation:** Start each document/page/page-item with
   classification, then branch into targeted prompts for receipts, chat
   screenshots, contracts, cross-document linking, and knowledge-object
   synthesis. A-00 can compare quick, standard, and exhaustive local budgets
   before and after importing reviewed knowledge files.
13. **Model-fit checks:** Record which Gemma variant was loaded and keep
   deterministic edges as the baseline. Smaller text models are suitable for
   compact text-edge proposals; multimodal edge extraction requires local
   OCR/layout/ASR plus a model/runtime that can consume the relevant media.

## Small-Model Fine-Tune Smoke Path

Use this path before recording if you plan to fine-tune the smallest Gemma 4
variant for a quick demo:

1. Run A-00 on Kaggle with GPU and internet enabled.
2. Open the UI and keep `dry_run` if you only want artifact validation, or load
   the smallest selected Gemma 4 model. The training panel defaults to
   `google/gemma-4-E2B-it`; adjust the exact Hugging Face/Unsloth model path
   to match the Kaggle image before executing.
3. If you already have an artifact, use `Already have a file?` first. A-00 can
   inspect synthetic training bundles, prompt sets, prompt-response exports,
   combined run ZIPs, and knowledge packs, then suggest whether to fine-tune,
   rerun prompts under a different harness, grade/compare existing responses,
   or load packs for later runs.
4. In Synthetic Data, use the default `rubric_polisher_24` profile.
5. In Train Adapter, click `Tiny fine-tune smoke bundle`. This writes separate
   train/validation/test rows, SFT and DPO train files, row SHA-256 values,
   artifact checksums, a raw-text-free quarantine report, and a bundle
   manifest. A-00 refuses a lone JSONL: uploaded data must include the
   manifest, frozen held-out prompt hashes, license/lineage fields, privacy
   clearance, passing quality gates, and zero train/held-out lineage overlap.
6. Click `Check training preflight` to verify CUDA and required packages.
7. Run the baseline eval on the frozen prompt set, then after verifying paths
   switch `Execute now` to `true` for the real Unsloth run on the Kaggle GPU.
   Training runs asynchronously; the UI polls `/api/a00/jobs/{job_id}` and
   shows the job status, log tail, generated script, verified SFT/DPO paths,
   checkpoints, and output dir. The run writes
   `training_completion_manifest.json` with executed stages, model revision,
   data hashes, and library versions.
   The official E2B and E4B presets resolve to immutable Hugging Face commit
   revisions; a different remote model must provide its own immutable revision
   before `Execute now=true` is accepted.
8. Reload the base model plus adapter and rerun the same eval prompts to show
   before/after lift in legal specificity, contact-pack/tool-call behavior,
   refusal grounding, and retaliation-risk dimensions.

## Advanced Model-Switching Presets

The A-00 UI includes an **Advanced pipeline presets** section for users who
want the notebook to orchestrate several steps without manually jumping between
panels. These presets are background jobs and are intentionally visible in the
Jobs list.

- **Compare two models one at a time:** unload current model, load Model A,
  run the prompt set, unload, load Model B, run the same prompt set, then build
  a comparison report.
- **Four-arm fine-tune proof path:** load the selected small Gemma 4 model,
  run base/no-harness and base+harness on the same configurable prompt count
  (default 5), generate a configurable number of rubric-polished SFT/DPO rows
  (default 5), unload before training, create or execute the LoRA job, then
  load the adapter and benchmark fine-tuned/no-harness and
  fine-tuned+harness arms on the same prompts.

For T4 x2 sessions, start with E2B/E4B or dry-run validation. Keep
`Unload between steps=true` unless you are deliberately testing memory reuse.
If `Execute training=false`, A-00 still exports the synthetic data, job JSON,
training script, and report handoff without trying to keep a long GPU job in
the browser request path. Use `Grade outputs=now` for a finished four-arm
report in one pass, or `Grade outputs=later` when you want to run generation
first and grade the uploaded run exports in a later session or with a stronger
judge model.

Expected artifacts after step 4:

- `a00_synthetic_*_sft_train.jsonl`
- `a00_synthetic_*_dpo_train.jsonl`
- `a00_synthetic_*_sft_validation.jsonl`
- `a00_synthetic_*_sft_test.jsonl`
- `a00_synthetic_*_quarantine.json`
- `a00_synthetic_*_manifest.json`
- `a00_synthetic_*_bundle.zip`
- `a00_train_*_job.json`
- `a00_train_*.py`

For the video, it is acceptable to show the generated smoke bundle and script
without running a full adapter training job live. Run `Execute now=true` only
after confirming the base model path, CUDA availability, Unsloth dependencies,
and that the SFT rows teach stable response structure rather than volatile
contacts or fee rules.

Local troubleshooting is useful for JSONL shape, import/export, reports, and
script generation. Real training should run on Kaggle or another CUDA host.

## Reasoning and answer data policy

A-00 can train on final answers, judge rationales, and deliberately authored
structured evidence chains such as indicator → source → safe action. It does
not scrape, infer, or publish private hidden chain-of-thought. Rows containing
`<think>`/hidden-thought markup are blocked. Open datasets are candidates only:
their license, provenance, consent basis, lineage split, factual grading, PII
scan, and held-out exclusion must be represented in the same manifest before
they can enter a GPU job.

This keeps the model/harness flywheel useful for training-data generation
without converting production logs or worker case material into automatic
labels. Hub submissions remain ineligible unless `allow_training_use` was
explicitly granted and curator, privacy, license, and correctness gates all
pass.

## Relationship to the Other Appendix Notebooks

A-00 intentionally has the full capability surface of the appendix set. The
other notebooks still remain useful because they are narrow verification
slices. A judge can use A-00 as the command center or open a focused notebook
when they want to validate only one claim, such as harness lift, prompt
generation, fine-tuning, privacy redaction, multimodal analysis, or streaming.

## Reuse From Kernel 01

A-00 should consume the same reusable primitives exposed by Kernel 01 rather
than maintaining a parallel contract:

- Import `duecare.chat.portability` for the required package version,
  endpoints, sample files, and primitive list.
- Import `duecare.chat.experiment_contracts` for harness profiles, the
  `bulk_text_25` comparison profile, synthetic generation profiles, upload
  limits, tiny LoRA defaults, and the four-arm stock/fine-tuned/harness matrix.
- Use `GET /api/a00/experiment-contract` to inspect the active contract and
  `POST /api/a00/quantitative/run` to execute `bulk_text_25` or prepare the
  `tiny_lora_smoke` synthetic/training handoff.
- Use `knowledge_files_sample.zip` as the reference importable knowledge-files
  bundle.
- Use `prompt_eval_training_seed_sample.zip` as the reference prompt,
  grading, and synthetic-training seed.
- Use `case_files_media_rich_sample.zip` as the reference local graph and
  multimodal processing source bundle.
- Keep generated graph edges compatible with the Kernel 01 edge contract:
  source file, page/chunk, extractor, confidence, quote or bbox when
  available, and local-only provenance.
- Include the portability payload or its hash in experiment exports so later
  benchmark and fine-tune results can be traced back to the exact workbench
  contract.

## Run It On Kaggle (5 clicks)

Copy-paste reproduction path so a judge can run the full benchmark
without leaving Kaggle.

1. **New Notebook** on Kaggle (`https://www.kaggle.com/code`). Choose **+ New Notebook**.
2. **Set the accelerator**: **Accelerator: GPU T4 x2**, **Internet: On**.
3. **Add the model**: **+ Add Input → Models → `google/gemma-4`**.
   E2B / E4B both work; larger variants improve grading quality.
4. **Paste `kernel.py`** from this folder into the notebook. For a real
   fine-tune, attach the versioned training bundle as a Kaggle Dataset (or
   upload its ZIP in the UI); A-00 verifies its manifest and SHA-256 values
   before creating a job. Synthetic smoke data can still be generated locally
   inside the workbench.
5. **Run All.** The control plane comes up at the printed
   `https://*.trycloudflare.com` URL. Use **Preconfigured Harness,
   Training, and Evaluation** for the fast guided path (defaults: small
   Gemma + 2 prompts on `chat_safety_core`, baseline + harnessed +
   fine-tuned + fine-tuned + harness arms, combined rule + LLM judging).
   **Custom** exposes every knob.

Heuristic-only mode (no model) can demonstrate UI and artifact shape, but it
does not count as approved training data or a completed adapter.

## Notes

- This is a script kernel. `kernel.py` is the source of truth.
- GPU is recommended. CPU mode can still import, evaluate, compare, and
  generate reports from previous exports.
- Internet is required for GitHub package install, Hugging Face model downloads,
  and optional knowledge-pack sync.

## Related Notebooks

- `../01-duecare-exploration-workbench/`: the broad reviewer workbench.
- `../02-live-demo/`: the focused live demo + recording-grade pitch deck.

## Related research tooling

- [`docs/entity_intelligence_pipeline.md`](../../docs/entity_intelligence_pipeline.md):
  propose-only entity-intelligence tooling (12 connectors feeding a 32-registry cascade)
  that verifies recruiters, employers, and their owners against official government
  registries. Separate from this proof path and the live model; documented for operators
  and curator-reviewed before any worker-facing use.
