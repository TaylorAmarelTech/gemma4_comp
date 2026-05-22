# Active submission surface — recording-critical kernels, phases, components

> Auto-loaded by Claude Code at the project memory level. Extracted
> from CLAUDE.md so the per-rule files stay scoped.

## Recording-critical surfaces

Before a video recording pass, treat these three Kaggle kernels as the
blocking set:

- `kaggle/01-duecare-exploration-workbench`: broad reviewer workbench.
  Every page should load from a direct URL, share the top model state,
  show an activity log, and expose the trust boundary for its workflow.
- `kaggle/02-live-demo`: focused interactive demo path. Use cached or
  pre-generated scenes when live model latency would weaken the story.
- `kaggle/A-00-omni-experiment-workbench`: technical proof control plane.
  The home page should only offer two navigation cards: Preconfigured
  Harness, Training, and Evaluation; and Custom. The preconfigured page
  should expose only the selected Gemma model and prompt count before
  running the guided proof. Advanced controls belong on Custom only.

`kaggle/03-duecare-video-pitch` and appendix notebooks other than A-00 are
archived for the current submission push. Do not revive or broaden them unless
Taylor explicitly asks.

Do not hardcode volatile phone numbers, URLs, fee caps, wage rules, or
office names into training targets or page copy unless they are also
represented as versioned knowledge objects. Stable response structure,
privacy boundaries, refusal style, ILO indicator reasoning, and evidence
citation habits are appropriate for fine-tuning. Volatile contacts and
current rules should come from tools, RAG, or synced knowledge packs.

## Execution phases (the 4-phase arc)

| Phase | Name | Core Question | Deliverable |
|---|---|---|---|
| 1 | **Exploration** | What can Gemma 4 do out of the box? | Baseline report + failure taxonomy |
| 2 | **Comparison** | How does it compare to GPT-OSS, Qwen, Llama, Mistral, DeepSeek? | Cross-model comparison + public benchmark |
| 3 | **Enhancement** | Can we improve via RAG + fine-tuning (Unsloth)? | Fine-tuned weights on HF Hub + ablation |
| 4 | **Implementation** | Can the enhanced model power real-world deployment? | Demo apps + public UI + on-device runtime |

Each phase tests 4 capabilities: guardrails, anonymization, document
classification, key fact extraction. Details: `docs/project_phases.md`.

## Independent components (the full pipeline)

The project is composed of **independent, testable components** that
form a complete pipeline from raw data to deployed model. Each
component can be developed, tested, and used separately.

### A. Data Pipeline (feeds training + evaluation)

```
[A1] Data Loader        → Load existing 21K OSS benchmark prompts/tests
         │
[A2] Data Scraper       → Scrape domain-specific info (ILO reports,
         │                 court cases, policy docs, news articles)
         │
[A3] Document Processor → Extract facts, entities, legal citations,
         │                 fee structures from raw documents
         │
[A4] Prompt Generator   → Create NEW prompts and tests from extracted
         │                 facts (graded response examples, worst→best)
         │
[A5] Data Labeler       → Label and classify: sector, corridor, ILO
         │                 indicators, attack category, severity grade
         │
[A6] Anonymizer         → Hard gate: detect + redact PII before
         │                 anything downstream sees the data
         │
[A7] Dataset Builder    → Assemble labeled, anonymized data into
                           training-ready JSONL splits (Unsloth chat format)
```

- **A1 — Data Loader**: reads from `_reference/trafficking-llm-benchmark-gitlab/`
  (21K public tests) plus seed prompts from
  `configs/<project>/domains/<id>/seed_prompts.jsonl`.
- **A2 — Data Scraper**: Playwright + stealth stack. Domain-specific
  scrapers for ILO databases, court filings (PACER, AustLII, BAILII),
  FATF/FATCA publications, NGO reports.
- **A3 — Document Processor**: NLP pipeline extracting named entities,
  legal citations (ILO C029, C181, RA 8042), monetary amounts, fee
  structures.
- **A4 — Prompt Generator**: takes `ExtractedFact` records and produces
  graded response examples (harmful → incomplete → adequate → good → best).
- **A5 — Data Labeler**: classifies by sector, corridor, ILO indicators,
  attack category, severity. Can use Gemma 4 itself as a labeler.
- **A6 — Anonymizer**: hard gate. Regex + NER, tagged replacement, audit
  log with `sha256(original)`.
- **A7 — Dataset Builder**: produces training-ready Unsloth chat-format
  JSONL with train/val/test splits + provenance manifest.

### B. Model Pipeline (training + export)

```
[B1] Fine-Tuner  → Unsloth + LoRA on Gemma 4 E4B
[B2] Evaluator   → Run benchmark suite (stock vs. enhanced)
[B3] Exporter    → Merge LoRA → GGUF (llama.cpp) + LiteRT
```

### C. Evaluation Pipeline (the agentic harness)

```
[C1] Model Adapters  → Unified Model protocol across 8 backends
[C2] Domain Packs    → Pluggable safety domains (YAML + JSONL)
[C3] Capability Tests → 9 standardized tests (guardrails, grounding, etc.)
[C4] Agent Swarm     → 12 autonomous agents orchestrated by a supervisor
[C5] Workflow Runner → DAG-based multi-step evaluation workflows
[C6] Reporting       → Historian agent → markdown reports with provenance
```

### D. Delivery Pipeline (publishing + demo)

```
[D1] Kaggle Publisher → Manual copy/paste workflow for kernels + wheels
[D2] HF Hub Publisher → Upload weights + model cards
[D3] Demo App         → FastAPI web app for live evaluation
[D4] Video Materials  → Script, screenshots, demo recordings
```

## Three deployment modes (see docs/deployment_modes.md)

1. **Enterprise Integration** — waterfall detection at social media / job
   board scale. Quick keyword filter → Gemma 4 analysis → warning popup /
   resource links / moderation queue. Like Facebook's suicide-prevention
   prompts but for trafficking.
2. **Worker-Side Tool** — browser extension, WhatsApp bot, or mobile app
   that runs Gemma 4 entirely on-device via LiteRT. Workers paste
   suspicious messages and get localized legal info + hotline numbers.
   Raw worker chats, IDs, contact details, and private documents stay on
   the worker device unless the worker explicitly creates a sanitized
   submission.
3. **Agency/NGO Dashboard** — FastAPI + web UI for batch evaluation,
   compliance monitoring, model comparison, and regulatory reporting.
   Agencies can fine-tune Gemma 4 on their specific regulations.

## Hackathon requirements checklist

- [ ] Kaggle writeup (<=1,500 words) - draft at `docs/writeup_draft.md`
- [ ] Public YouTube video (<=3 minutes) - script at `docs/video_script.md`
- [ ] Public code repo - this repo, minus `_reference/`
- [ ] Live public demo - `src/demo/`, deployment TBD
- [ ] Uses Gemma 4 (E2B or E4B) - yes
- [ ] Bonus: Special Tech Track alignment - Unsloth + (llama.cpp | LiteRT)
