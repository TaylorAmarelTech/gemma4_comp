# Gemma 4 feature showcase across DueCare kernels

> Sister to [`gemma4_model_guide.md`](gemma4_model_guide.md).
> That doc tells you *which variant* to pick; this one tells you
> *which Gemma 4 capability is exercised in each kernel*. Built
> specifically for the Hackathon Technical Depth rubric (30 pts)
> which calls out "innovative use of Gemma 4's unique features
> (native function calling, multimodal understanding)".

## The 7 Gemma 4 capabilities DueCare exercises

| Capability | What Gemma 4 brings | Kernels that exercise it |
|---|---|---|
| **Native function calling** | Structured tool-call JSON natively emitted by the model -- no glue protocol needed | A-02, A-09, A-13 |
| **Multimodal vision** | Image-aware text generation in a single forward pass | A-13 |
| **Multilingual reach** | 5 corridors covered without per-language fine-tune | A-19, A-13 (OCR), A-15 (UGC moderation across languages) |
| **On-device quantization** | INT4 / Q4_K_M paths that produce real GGUF and LiteRT artifacts a user can run on a laptop or phone | A-14, A-19 (mobile-class fallback) |
| **Long context (128K)** | Whole-document grounding without retrieval | A-04 (knowledge builder), A-16 (NGO local-KB) |
| **Instruction-following at small scale** | E2B + E4B variants produce high-quality outputs at sub-2 B and sub-4 B parameter counts | A-01, A-02, A-19, A-20 (all run on E2B by default) |
| **Adapter compatibility** | LoRA fine-tune via Unsloth + PEFT merge-and-export pipeline | A-12 (PrivacyRedactor), A-07 (SafetyJudge), A-14 (export) |

## Per-kernel capability map

The "rubric earn" column is the specific Technical Depth point
each kernel collects.

| Kernel | Primary Gemma 4 feature | Rubric earn |
|---|---|---|
| 01-duecare-exploration-workbench | All 6 harness layers + 9-variant model picker | "Unified surface across all features" |
| 02-live-demo | Instruction-following on E4B + harness orchestration | "+56.5pp lift on compound-indicator prompts" |
| 03-duecare-video-pitch | Zero-inference replay (showcases harness traces) | Video-pitch enabler |
| A-01 chat-playground | Raw E2B / E4B baseline (control case) | Stock comparator for lift claims |
| A-02 grep-rag-tools | Persona / GREP / RAG / **Tools** toggles (function calling on `Tools=ON`) | Native function calling demonstration |
| A-03 content-classification | Comparison harness reading A-01 + A-02 bundles | Reproducible delta artifact |
| A-04 knowledge-builder | Long-context document grounding | 128K context window in practice |
| A-05 classification-eval | Batch evaluation at scale | E2B latency / cost profile |
| A-06 prompt-generation | Self-supervised synthetic training data | Bootstrapping with Gemma-as-teacher |
| A-07 bench-and-tune | **Unsloth LoRA fine-tune** + DPO + benchmark | LoRA adapter compatibility |
| A-08 research-graphs | Cross-prompt analysis (CPU-only) | Insight visualization |
| A-09 agentic-research | Native function calling + Playwright web tools (BYOK) | Tool use with real-world web search |
| A-10 jailbroken-models | Side-by-side abliterated baselines | Safety lift against worst-case adversary |
| A-11 grading-evaluation | Runtime harness lift regenerator | OFF/ON lift on held-constant weights |
| A-12 pii-fine-tune-eval | PrivacyRedactor LoRA on A-10 synth data | Privacy-specific adapter |
| A-13 multimodal-document-analyzer | **Multimodal vision** + native function calling | Image-aware tool use |
| A-14 on-device-export | **GGUF (llama.cpp)** + **LiteRT (mobile)** | On-device quantization ($10K Special Tech) |
| A-15 ugc-batch-moderator | Multilingual platform-safety classification | Batch moderation across 5 languages |
| A-16 ngo-local-kb | Long-context case-file ingestion + PrivacyRedactor adapter | 128K context for whole-case grounding |
| A-17 knowledge-pack-builder | Signed pack registry mechanics | Reproducibility (researcher pull + verify) |
| A-18 demo-replay | Zero-inference scripted demo | Video-recording surface |
| A-18 sentinel-research-monitor | Diff-monitor over the pack registry | Trend signaling |
| A-19 multilingual-demo | **Multilingual** 5-corridor scenario playback | "in their language" Lane 03 |
| A-20 privacy-boundary | Local-vs-aggregate side-by-side | Privacy claim made concrete |

## Where each Special Tech Track is closed

The hackathon rules name three Special Tech sub-tracks at $10K each.

| Special Tech Track | Closed by | Concrete artifact reviewers can run |
|---|---|---|
| **Unsloth** | A-07 bench-and-tune (SFT + DPO); A-12 (PrivacyRedactor) | `taylorscottamarel/duecare-gemma-4-*-SafetyJudge-*` on HF Hub |
| **llama.cpp** | A-14 on-device-export | `<RUN>_safetyjudge_q4km.gguf` (single `llama-server -m ...` away from a working chat) |
| **LiteRT** | A-14 on-device-export | `<RUN>_safetyjudge.tflite` (drops into the Android demo app at `apps/duecare-android-app/`) |

## Where each capability is **not** showcased yet

Honest gap analysis -- worth filling in a future appendix:

- **Coordinator-as-function-calling-router.** Per CLAUDE.md rule 4
  ("Gemma 4's unique features must be load-bearing, not decorative"),
  the Coordinator agent should orchestrate via native function-call
  JSON. A-02 / A-09 / A-13 each call tools individually; a future
  Coordinator demo would chain multiple tools in one Gemma 4 thinking
  step.
- **Long-context demonstration at 128K boundary.** A-04 + A-16 use
  long context but no kernel deliberately benchmarks at 128K.
  Adding a "load 100-page POEA Memorandum + ask for citations across
  the doc" demo would close this.
- **Streaming generation.** Gemma 4 supports token streaming; the
  workbench shell currently returns whole responses. A streaming
  demo would make the latency-on-mobile story more concrete.

## How this doc is meant to be used

1. Reading the writeup or watching the video, a reviewer or
   first-pass viewer checks the 30-pt Technical Depth box by cross-
   referencing the per-kernel capability map against this Gemma 4
   feature inventory.
2. New contributors deciding which appendix slot to extend can pick
   a capability that's under-showcased above.
3. Future Tier-5 standardization should add a `**Gemma 4 features**`
   row to each kernel's judge-quick-path table so the kernel README
   self-documents which capability it earns.

## Links

- Hackathon rubric: see CLAUDE.md "Three overarching goals" section.
- Per-kernel detail: each `kaggle/*/README.md`.
- Data primitives (BundleEnvelope etc.):
  [`data_primitives.md`](data_primitives.md).
- Model variant picker: [`gemma4_model_guide.md`](gemma4_model_guide.md).
