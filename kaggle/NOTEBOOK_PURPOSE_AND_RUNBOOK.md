# DueCare Kaggle Notebook Purpose and Runbook

This file is the plain-language map for the Kaggle submission. Each notebook
should be runnable on a Kaggle T4 x2 session unless its README says GPU is not
required. Interactive notebooks start a FastAPI app and print a Cloudflare URL
or localhost fallback. Raw case material should remain local to the kernel.

## Primary Notebooks

| Notebook | Purpose | User-facing result | Cloudflare URL | Main actions |
|---|---|---|---|---|
| `01-duecare-exploration-workbench` | Full product workbench and source-of-truth harness surface. | Multi-page UI for chat, comparison, bulk case review, knowledge extraction, search, sharing, status, harnesses, and audit. | Yes. | Load model, compare harness/no-harness, process source case files, inspect graph edges, draft knowledge objects, sanitize/search/share. |
| `02-live-demo` | Focused live product demo with real Gemma 4 inference. | Small product surface for judges to click and inspect live harness behavior. | Yes. | Load selected Gemma 4 path, send curated PH-HK prompt, inspect trace and audit events. |
| `03-duecare-video-pitch` | Recording-first video surface. | Slide deck plus cached replay lanes and exportable evidence bundle. | Yes. | Record slides, replay worker/caseworker/platform/researcher/developer scenes, export scenes/traces/scorecards/media. |
| `A-00-omni-experiment-workbench` | Technical proof control plane. | One UI for quantitative runs, synthetic data, LoRA handoff/execution, research graphing, and appendix workflows. | Yes. | Run baseline vs harness benchmarks, generate SFT/DPO data, upload/inspect training bundles, run training preflight, queue async LoRA jobs, compare reports, import/export packs. |

## A-00 Guided Path

1. Open the printed Cloudflare URL.
2. Use dry-run mode for UI inspection or load one model for real runs.
3. If you already have an artifact, start with `Already have a file?`.
   A-00 classifies synthetic training bundles, prompt sets, prompt-response
   exports, combined run ZIPs, and knowledge packs, then suggests the next
   action.
4. Click `Create baseline + harness proof` for a text-only benchmark report.
5. Generate rubric-polished SFT/DPO data in `Synthetic data`.
6. Confirm the generated SFT path is copied into `Train adapter`, or upload a
   prior `*_sft.jsonl` / synthetic ZIP with `Upload and inspect training data`.
7. Click `Check training preflight` to verify CUDA and package availability.
8. Click `Create training job`; if `Execute now=true`, the job runs
   asynchronously and the page polls `/api/a00/jobs/{job_id}` for status/logs.
9. After training, load the adapter path and rerun the same prompt set to
   compare stock, stock+harness, fine-tuned, and fine-tuned+harness arms.
10. For automated multi-step runs, open `Advanced pipeline presets`. Use
    `Compare two models one at a time` for controlled model switching, or
    `Four-arm fine-tune proof path` for the full base/no-harness,
    base+harness, synthetic data -> unload -> LoRA job ->
    fine-tuned/no-harness, fine-tuned+harness cycle. The default smoke path is
    5 prompts and 5 synthetic rows, with grading/reporting selectable as
    `now` or `later`.

The A-00 UI should not require users to infer hidden file paths. Generated and
uploaded training files are inspected for JSONL shape and metadata, and the UI
fills the training path, base model, and max-step suggestion when available.

## Appendix Notebooks

| Notebook | Purpose | Expected interaction |
|---|---|---|
| `A-01-chat-playground` | Minimal chat playground baseline. | Run, open URL, send chat prompt, inspect baseline behavior. |
| `A-02-chat-playground-with-grep-rag-tools` | Chat with deterministic safety layers, RAG, and tools. | Compare plain answer against harnessed answer with citations/tool calls. |
| `A-03-content-classification-playground` | Content classification comparison surface. | Upload or use bundled classification examples and compare outputs. |
| `A-04-content-knowledge-builder-playground` | Knowledge-object builder playground. | Draft, inspect, and export simple knowledge objects from text. |
| `A-05-gemma-content-classification-evaluation` | Classification evaluation appendix. | Run/evaluate classification bundles and export metrics. |
| `A-06-prompt-generation` | Synthetic prompt and scenario generation. | Generate prompt sets, adversarial variants, and privacy-safe training seeds. |
| `A-07-bench-and-tune` | Focused benchmark and tuning workflow. | Run benchmark phases, upload A-04 artifacts, create fine-tuning/eval artifacts. |
| `A-08-research-graphs` | Static research graph visualizations. | Inspect charts and graph metadata; chart 3 falls back to a labeled placeholder if optional eval data is absent. |
| `A-09-chat-playground-with-agentic-research` | Agentic research and privacy-redaction scenario generation. | Generate composite case/redaction examples; no real PII required. |
| `A-10-chat-playground-jailbroken-models` | Adversarial/jailbroken-model comparison. | Test harmful prompt behavior and harness resistance. |
| `A-11-grading-evaluation` | Grading and harness-lift evaluation. | Upload baseline/harness bundles or use examples, run comparison. |
| `A-12-pii-fine-tune-eval` | PII/redaction fine-tune evaluation. | Evaluate redaction behavior and fine-tune-ready privacy rows. |
| `A-13-multimodal-document-analyzer` | Multimodal/local document analyzer demo. | Upload media/document bundles and inspect deterministic plus model-assisted extraction where available. |
| `A-14-on-device-export` | On-device/export path. | Inspect small-model/export artifacts and local deployment constraints. |
| `A-15-ugc-batch-moderator` | Platform UGC batch moderation. | Upload or use sample posts, moderate in batch, inspect state. |
| `A-16-ngo-local-kb` | NGO local knowledge base. | Ingest local notes, query by hash, view aggregate local-only signals. |
| `A-17-knowledge-pack-builder` | Knowledge pack authoring and verification. | Build/import/verify corridor packs and export pack artifacts. |
| `A-18-sentinel-research-monitor` | Public-source/research monitor. | Propose public source items and inspect local monitor state. |
| `A-19-multilingual-demo` | Multilingual cached worker guidance. | Show in-language answers that point to vetted contacts packs for volatile details. |
| `A-20-privacy-boundary` | Privacy boundary visualization. | Demonstrate local redaction and raw-PII rejection boundaries. |
| `A-21-long-context-demo` | Long-context safety demonstration. | Inspect long-context prompt handling and grounded response behavior. |
| `A-22-streaming-demo` | Streaming response demonstration. | Open stream UI and confirm first useful tokens arrive progressively. |
| `A-23-coordinator-demo` | Function-calling/coordinator demonstration. | Inspect one-turn tool planning and synthesis; contact details route through vetted packs. |
| `A-24-demo-replay` | Appendix replay surface. | Replay cached demo scenes when live inference is not needed. |

## Product Narrative

DueCare is not one chatbot. It is local-first safety infrastructure for migrant
worker exploitation risk: deterministic rules, RAG over vetted corridor packs,
tool calls, graph extraction, anonymization, and evaluation harnesses around
Gemma 4. The core product claim is that the same primitives can serve platform
moderation, NGO/regulator intake, individual worker guidance, researcher
benchmarks, and developer integrations without centralizing raw private case
data.

## UI Expectations

- Every interactive notebook should either open a Cloudflare URL or clearly
  state why it is static/cached.
- Heavy work should be queued or progress-visible rather than hidden behind a
  long blocking request.
- Activity logs should show the API call, response summary, artifact links, and
  error details.
- Contacts, phone numbers, current URLs, and office names should come from
  versioned knowledge/contacts packs, not hardcoded demo text.
- Training and benchmark flows should preserve metadata: prompt set, harness
  profile, model ref, pack hash, generation settings, and output artifact paths.
- Synthetic data should teach stable response structure and tool-use policy,
  not memorize volatile facts.
- Model switching should be explicit and progress-visible: unload between
  heavy phases, serialize model runtime access, queue long pipelines as jobs,
  and show step-by-step job traces in the UI.
