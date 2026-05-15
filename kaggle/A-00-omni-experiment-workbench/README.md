# DueCare A-00 Omni Experiment Workbench

> Control-plane appendix for the Gemma 4 Good submission. This notebook is the
> single UI for running batches, rerunning exports, comparing harnesses,
> generating synthetic data, training adapters, processing local research
> bundles, and launching every appendix workflow.

## Judge Quick Path

| Section | This notebook |
|---|---|
| Lede | One interactive workbench that proves what improves quality across harnessing, synthetic data, research graphing, retraining, or combined runs. |
| What it does | Loads one selected model per Kaggle run, runs bulk prompt sets through any harness profile, exports results, imports earlier exports, evaluates with rule and LLM judges, generates synthetic SFT/DPO data, launches LoRA fine-tuning when dependencies are available, processes local case/research bundles into graphs, and exposes A-01 through A-24 as workflows. |
| Demo path | Run all, open the printed Cloudflare URL, load Gemma 4 E2B or a custom model path, run Chat Safety prompts with harness off and on, generate the report, then export the JSON bundle. |
| Audience | Researcher, developer, platform safety, NGO/regulator. |
| Inputs | Prompt libraries, previous A-00/A-01/A-02/A-07 exports, knowledge packs, optional custom model directory or Hugging Face model id. |
| Outputs | `a00_*_results.json`, `a00_*_results.csv`, `a00_*_report.html`, `a00_*_report.md`, `a00_*_sft.jsonl`, `a00_*_dpo.jsonl`, training scripts, and optional LoRA adapter folders. |

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

1. **Harness lift:** run `chat_safety_core` with `No harness`, run the same set
   with `Chat safety harness`, then build the HTML report.
2. **Prior red-team regression:** run `anti_tip_redteam_regressions`. This
   prompt set converts the 2025 GPT OSS failure modes into reusable checks:
   business-framed exploitation, jurisdiction shopping, predatory debt,
   prompt-attack formatting, and worker revictimization.
3. **Synthetic training:** choose `rubric_polisher`, generate SFT/DPO rows, and
   create a tiny training handoff before any full fine-tune.
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
7. **Fine-tuning:** Create and optionally execute an Unsloth or PEFT LoRA
   training job from exported synthetic data.
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

## Small-Model Fine-Tune Smoke Path

Use this path before recording if you plan to fine-tune the smallest Gemma 4
variant for a quick demo:

1. Run A-00 on Kaggle with GPU and internet enabled.
2. Open the UI and keep `dry_run` if you only want artifact validation, or load
   the smallest selected Gemma 4 model. The training panel defaults to
   `google/gemma-4-e2b-it`; adjust the exact Hugging Face/Unsloth model path
   to match the Kaggle image before executing.
3. In Synthetic Data, choose `rubric_polisher` and generate 8 to 40 rows.
4. In Train Adapter, click `Tiny fine-tune smoke bundle`. This writes a valid
   SFT JSONL, DPO JSONL, manifest, bundle ZIP, and a 5-step training script.
5. Run the baseline eval on the same prompt set, then after verifying paths
   switch `Execute now` to `true` for the real Unsloth run on the Kaggle GPU.
6. Reload the base model plus adapter and rerun the same eval prompts to show
   before/after lift in legal specificity, contact-pack/tool-call behavior,
   refusal grounding, and retaliation-risk dimensions.

Expected artifacts after step 4:

- `a00_synthetic_*_sft.jsonl`
- `a00_synthetic_*_dpo.jsonl`
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

## Relationship to the Other Appendix Notebooks

A-00 intentionally has the full capability surface of the appendix set. The
other notebooks still remain useful because they are narrow verification
slices. A judge can use A-00 as the command center or open a focused notebook
when they want to validate only one claim, such as harness lift, prompt
generation, fine-tuning, privacy redaction, multimodal analysis, or streaming.

## Notes

- This is a script kernel. `kernel.py` is the source of truth.
- GPU is recommended. CPU mode can still import, evaluate, compare, and
  generate reports from previous exports.
- Internet is required for GitHub package install, Hugging Face model downloads,
  and optional knowledge-pack sync.
- The notebook defaults to a dry-run generator if no model is loaded, so judges
  can inspect the UI and artifact contracts without waiting for weights.

## Related Notebooks

- `../01-duecare-exploration-workbench/`: the polished product UI.
- `../02-live-demo/`: the public live-demo story.
- `../A-06-prompt-generation/`: narrow synthetic-data generator.
- `../A-07-bench-and-tune/`: narrow trainer and benchmark runner.
- `../A-11-grading-evaluation/`: narrow harness-lift regenerator.
