# For Judges — Verify DueCare in 5 Minutes

> A focused walkthrough for Gemma 4 Good Hackathon judges. This document
> exists so you don't have to spelunk the codebase to verify our claims.
> Every claim in the writeup and video is backed by a file or a Kaggle
> kernel link below.

---

## The 30-second pitch

DueCare is an agentic safety harness that fine-tunes Gemma 4 to evaluate
LLM responses on migrant-worker trafficking safety. NGOs can't send
sensitive case data to frontier APIs, so DueCare runs entirely on a
laptop. It ships as 8 `pip install`-able packages and 19 Kaggle notebooks.
Real Gemma 4 E4B baseline on Kaggle T4: **0.610 mean score, 20% pass rate,
0% harmful output** across 50 graded trafficking prompts.

---

## Two-minute verification path

If you have two minutes to decide if this is real:

1. **Read the writeup.** `docs/writeup_draft.md` (1,490 words, under the 1,500 limit).
   Frames the problem, the approach, the 6-dimension rubric, the real numbers.

2. **Watch the video.** Script at `docs/video_script.md` (2:45 target).
   Opens with Maria (a composite character, labeled as such). Closes with
   named NGO partners (Polaris, IJM, POEA, BP2MI, HRD Nepal).

3. **Check one completed Kaggle run.**
   [Notebook 00 — Real Gemma 4 on 50 Trafficking Prompts (COMPLETE)](https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts).
   Real Gemma 4 E4B on Kaggle T4. Outputs `gemma_baseline_findings.json`
   saved in `data/gemma_baseline_findings.json` — 50 prompts, 6 dimensions,
   full provenance.

---

## Five-minute verification path

### Verify the technology is real (Technical Depth = 30pts)

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp
pip install duecare-llm                         # or: pip install packages/duecare-llm
python -m pytest packages -v                    # 194 tests
```

You should see **194 passed**. The README claims match the actual count
(we previously had inflated numbers; those are fixed).

### Verify Gemma 4's unique features are load-bearing, not decorative

Gemma 4's distinguishing features per Google's docs: **native function
calling** and **multimodal understanding**. Both are load-bearing in
DueCare:

| Claim | File to verify | What you'll see |
|---|---|---|
| Function calling in the Transformers adapter | `packages/duecare-llm-models/src/duecare/models/transformers_adapter/adapter.py` | `_generate_impl` passes `tools` via `apply_chat_template`; `_parse_tool_calls` extracts Gemma's `<tool_call>...</tool_call>` output |
| Coordinator orchestrated by Gemma 4 | `packages/duecare-llm-agents/src/duecare/agents/coordinator/coordinator.py` | `use_gemma_orchestration=True` dispatches Gemma's `tool_calls` to agents — each agent exposed as `run_<agent_id>` tool |
| Multimodal document classification | `packages/duecare-llm-tasks/src/duecare/tasks/multimodal_classification/multimodal_classification.py` | `_load_images` loads from domain's `images/` dir; `model.generate(images=...)` processes contract photos |
| ToolSpec.to_gemma() | `packages/duecare-llm-core/src/duecare/core/schemas/chat.py` | Renders tools in Gemma 4's native function-calling format |

### Verify reproducibility

Every result in the writeup has a provenance chain:

| Result | Where it came from | How to reproduce |
|---|---|---|
| Gemma 4 E4B mean score = 0.610 | [Kaggle NB 00](https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts) | Fork the kernel, click Run. Output `gemma_baseline_findings.json` matches ours in `data/`. |
| 74,567 trafficking prompts | `packages/duecare-llm-domains/src/duecare/domains/_data/trafficking/seed_prompts.jsonl` | `wc -l packages/duecare-llm-domains/src/duecare/domains/_data/trafficking/seed_prompts.jsonl` |
| 15 adversarial generators | `packages/duecare-llm-tasks/src/duecare/tasks/generators/` | `ls packages/duecare-llm-tasks/src/duecare/tasks/generators/ \| grep -v __` |
| 12 agents | `packages/duecare-llm-agents/src/duecare/agents/` | `ls packages/duecare-llm-agents/src/duecare/agents/` |
| 8 PyPI packages | `packages/` | `ls packages/` |

### Verify cross-domain generalization

The same harness runs on three domains. Swap `--domain` and it works:

```bash
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain trafficking
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain tax_evasion
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain financial_crime
```

Each produces a structurally identical markdown report in `reports/`.

---

## The 22 Kaggle notebooks at a glance

| # | Notebook | What it proves | Status |
|---|----------|----------------|--------|
| 00 | [Gemma Exploration](https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts) | Real Gemma 4 E4B on 50 graded trafficking prompts (T4 GPU) | ✅ COMPLETE |
| 00a | [Prompt Prioritizer](https://www.kaggle.com/code/taylorsamarel/duecare-curating-2k-trafficking-prompts-from-74k) | Curates 2K prompts from 74K corpus | ✅ COMPLETE |
| 00b | [Prompt Remixer](https://www.kaggle.com/code/taylorsamarel/00b-duecare-prompt-remixer-data-pipeline) | 15 adversarial generators expand prompt space | ✅ COMPLETE |
| 01 | [Quickstart](https://www.kaggle.com/code/taylorsamarel/01-duecare-quickstart-generalized-framework) | 5-minute smoke test of the framework | ✅ COMPLETE |
| 02 | [Cross-Domain Proof](https://www.kaggle.com/code/taylorsamarel/duecare-cross-domain-proof) | Same harness, 3 domains, zero code changes | ✅ COMPLETE |
| 03 | [Agent Swarm Deep Dive](https://www.kaggle.com/code/taylorsamarel/duecare-12-agent-gemma-4-safety-pipeline) | 12 agents + Supervisor in action | ✅ COMPLETE |
| 04 | [Submission Walkthrough](https://www.kaggle.com/code/taylorsamarel/duecare-submission-walkthrough) | End-to-end submission overview | ✅ COMPLETE |
| 05 | [RAG Comparison](https://www.kaggle.com/code/taylorsamarel/duecare-rag-comparison) | Plain vs RAG vs Guided on Gemma 4 | ✅ COMPLETE |
| 06 | [Adversarial Resistance](https://www.kaggle.com/code/taylorsamarel/duecare-adversarial-resistance) | 15 attack vectors tested | ✅ COMPLETE |
| 07 | [Gemma 4 vs OSS](https://www.kaggle.com/code/taylorsamarel/gemma-4-vs-llama-vs-mistral-on-trafficking-safety) | Head-to-head vs Llama 3.1, Mistral 7B | 🔄 pending |
| 08 | [Function Calling + Multimodal](https://www.kaggle.com/code/taylorsamarel/duecare-function-calling-multimodal) | Gemma 4's two unique features in action | ✅ COMPLETE |
| 09 | [LLM-as-Judge Grading](https://www.kaggle.com/code/taylorsamarel/duecare-llm-judge-grading) | 6-dimension 0-100 scoring | 🔄 pending |
| 10 | [Conversation Testing](https://www.kaggle.com/code/taylorsamarel/duecare-conversation-testing) | Multi-turn escalation detection | ✅ COMPLETE |
| 11 | [Comparative Grading](https://www.kaggle.com/code/taylorsamarel/duecare-comparative-grading) | Best/worst reference anchoring | ✅ COMPLETE |
| 12 | [Prompt Factory](https://www.kaggle.com/code/taylorsamarel/duecare-adversarial-prompt-factory) | Generate → validate → rank | 🔄 pending |
| 13 | [Rubric Evaluation](https://www.kaggle.com/code/taylorsamarel/duecare-rubric-anchored-evaluation) | 54 criteria, per-criterion pass/fail | ✅ COMPLETE |
| 14 | [Results Dashboard](https://www.kaggle.com/code/taylorsamarel/duecare-results-dashboard) | Interactive Plotly dashboard | ✅ COMPLETE |
| P2 | [Phase 2 Comparison](https://www.kaggle.com/code/taylorsamarel/duecare-phase-2-model-comparison) | E2B vs E4B head-to-head | 🔄 pending |
| 15 | [Ollama Cloud OSS (7 models)](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-vs-6-oss-models-via-ollama-cloud) | Broadest OSS comparison: Gemma 4 + 6 OSS models via Ollama Cloud API | 🆕 new |
| 16 | [Mistral Family](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-vs-mistral-family) | 5 Mistral variants (Large 2, Small, Nemo, Ministral, 7B) vs Gemma 4 | 🆕 new |
| 17 | [Frontier Models](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-vs-frontier) | Gemma 4 vs Claude, GPT-4o, Gemini, Llama 405B, DeepSeek V3 via OpenRouter | 🆕 new |
| P3 | [Phase 3 Fine-tune](https://www.kaggle.com/code/taylorsamarel/duecare-phase3-finetune) | Unsloth LoRA + GGUF export | 🔄 pending |

**14 of 19 notebooks verified COMPLETE on Kaggle.** The five still
running/queued include Phase 3 (Unsloth fine-tuning), which is
a long-running GPU workload, and two CPU notebooks whose Kaggle status
was cached ERROR from previous versions before the fixes were pushed.

---

## Special Technology Track alignment

| Track | Prize | Evidence |
|---|---|---|
| **Unsloth** | $10K | `scripts/build_notebook_phase3.py` + `kaggle/kernels/duecare_phase3_finetune/` — uses official Kaggle Unsloth install (xformers + git HEAD) and SFTTrainer |
| **llama.cpp** | $10K | GGUF Q4_K_M export in Phase 3 notebook; adapter at `packages/duecare-llm-models/src/duecare/models/llama_cpp_adapter/` |
| **LiteRT** | $10K | Exporter agent scaffolds LiteRT output path; on-device mobile deployment is the "Worker-Side Tool" deployment mode in `docs/deployment_modes.md` |
| **Impact & Trust** | $10K | 12 named NGO partners (Polaris, IJM, POEA, BP2MI, HRD Nepal, etc.); concrete before/after workflow in writeup § 5 |

---

## What to look at first (by role)

- **Engineer on the jury?** `packages/duecare-llm-core/src/duecare/core/contracts/` — Protocol-based contracts, no ABCs. Clean.
- **NGO partner on the jury?** `configs/duecare/domains/trafficking/` — Real taxonomy + evidence + rubric YAML.
- **ML researcher on the jury?** [NB 00](https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts) — Real Gemma 4 E4B baseline, 6 interactive Plotly charts.
- **Product person on the jury?** `docs/video_script.md` — 2:45 story arc with Maria and the named NGOs.

---

## Known gaps (honesty)

1. **Phase 3 fine-tuning hasn't completed on Kaggle yet.** The notebook
   is real code (real Unsloth + SFTTrainer) but takes 2-4 hours on T4 and
   the published Gemma 4 E4B model terms need to be accepted before the
   kernel can run. Expected completion before submission.

2. **HuggingFace Hub model page is pending.** It exists as a publishing
   target in `duecare-llm-publishing`; weights will be uploaded once
   Phase 3 completes.

3. **Live demo at src/demo/** is functional locally; a hosted HF Spaces
   deployment is in progress.

4. **Video is currently a script, not a produced video.** Recording and
   editing scheduled for Week 4 (May 4-10) per the project plan in
   `docs/project_phases.md`.

We're noting these up front because "real, not faked for the demo" is
the invariant we care most about. Everything that claims to be real is
real. Everything in progress is labeled as such.

---

## Contact

- **Repo:** github.com/TaylorAmarelTech/gemma4_comp (public before submission per plan)
- **Kaggle:** kaggle.com/taylorsamarel (19 public notebooks before submission)
- **Author:** Taylor Amarel, author of the 21K-test migrant-worker trafficking benchmark that is the foundation of this submission

---

**Privacy is non-negotiable. The lab runs on your machine.**
