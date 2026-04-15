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

## The 23 Kaggle notebooks — organized by purpose

> The raw kernel slugs use legacy numbers (`00`, `00a`, `00b`, `01`–`18`,
> plus `Phase 2`, `Phase 3`). The logical flow is captured in the
> canonical guide at [`docs/NOTEBOOK_GUIDE.md`](./NOTEBOOK_GUIDE.md).
> This table groups by category.

### 🚀 START — Where a judge should begin (4 notebooks)

| Slug | Notebook | What it proves |
|------|----------|----------------|
| [`01-duecare-quickstart-generalized-framework`](https://www.kaggle.com/code/taylorsamarel/01-duecare-quickstart-generalized-framework) | S1 Framework Quickstart | 5-min smoke test |
| [`duecare-submission-walkthrough`](https://www.kaggle.com/code/taylorsamarel/duecare-submission-walkthrough) | S2 Submission Walkthrough | End-to-end overview |
| [`duecare-cross-domain-proof`](https://www.kaggle.com/code/taylorsamarel/duecare-cross-domain-proof) | S3 Cross-Domain Proof | Same harness on trafficking + tax + finance |
| [`duecare-12-agent-gemma-4-safety-pipeline`](https://www.kaggle.com/code/taylorsamarel/duecare-12-agent-gemma-4-safety-pipeline) | S4 Agent Swarm Deep Dive | 12-agent orchestration |

### 📊 BASELINE — Real Gemma 4 measurements (3 notebooks)

| Slug | Notebook | What it proves |
|------|----------|----------------|
| [`duecare-real-gemma-4-on-50-trafficking-prompts`](https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts) | **B1 Gemma 4 E4B / 50 prompts** | **Primary result:** 0.610 mean, 20% pass, 0% harmful |
| [`duecare-rag-comparison`](https://www.kaggle.com/code/taylorsamarel/duecare-rag-comparison) | B2 RAG vs Plain vs Guided | Context lift 23–28%, no training needed |
| [`duecare-phase-2-model-comparison`](https://www.kaggle.com/code/taylorsamarel/duecare-phase-2-model-comparison) | B3 Phase 2 E2B vs E4B | Size vs quality within Gemma 4 family |

### 🔍 TASK — Capability-specific evaluations (5 notebooks)

| Slug | Notebook | What it tests |
|------|----------|----------------|
| [`duecare-adversarial-resistance`](https://www.kaggle.com/code/taylorsamarel/duecare-adversarial-resistance) | T1 Adversarial Resistance | 15 attack vectors |
| [`duecare-function-calling-multimodal`](https://www.kaggle.com/code/taylorsamarel/duecare-function-calling-multimodal) | T2 Function Calling + Multimodal | Gemma 4's unique features |
| [`duecare-llm-judge-grading`](https://www.kaggle.com/code/taylorsamarel/duecare-llm-judge-grading) | T3 LLM-as-Judge | 6-dimension 0-100 scoring |
| [`duecare-conversation-testing`](https://www.kaggle.com/code/taylorsamarel/duecare-conversation-testing) | T4 Conversation Testing | Multi-turn escalation |
| [`duecare-rubric-anchored-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-rubric-anchored-evaluation) | T5 Rubric Evaluation | 54 per-criterion checks |

### ⚖️ COMPARE — Multi-model comparisons (5 notebooks)

| Slug | Notebook | What it compares |
|------|----------|------------------|
| [`gemma-4-vs-llama-vs-mistral-on-trafficking-safety`](https://www.kaggle.com/code/taylorsamarel/gemma-4-vs-llama-vs-mistral-on-trafficking-safety) | C1 Gemma 4 vs 3 OSS (CPU) | CPU analysis from real NB 00 data |
| [`duecare-gemma-4-vs-6-oss-models-via-ollama-cloud`](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-vs-6-oss-models-via-ollama-cloud) | **C2 Gemma 4 vs 6 OSS** (Ollama) | Broad OSS live comparison |
| [`duecare-gemma-4-vs-mistral-family`](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-vs-mistral-family) | **C3 Gemma 4 vs Mistral family** | 5 Mistral variants |
| [`duecare-openrouter-frontier-comparison`](https://www.kaggle.com/code/taylorsamarel/duecare-openrouter-frontier-comparison) | **C4 Gemma 4 vs Frontier** | Claude, GPT-4o, Gemini, Llama 405B, DeepSeek V3 |
| [`duecare-comparative-grading`](https://www.kaggle.com/code/taylorsamarel/duecare-comparative-grading) | C5 Comparative Grading | Best/worst anchored methodology |

### 🛡️ SAFETY — Red-team research (1 notebook)

| Slug | Notebook | What it shows |
|------|----------|---------------|
| [`duecare-finding-gemma-4-safety-line`](https://www.kaggle.com/code/taylorsamarel/duecare-finding-gemma-4-safety-line) | **SF1 Finding Safety Line** | Stock Gemma 4 vs uncensored → refusal is load-bearing |

### ⚙️ PIPELINE — Custom prompts & test generation (3 notebooks)

| Slug | Notebook | What it does |
|------|----------|--------------|
| [`duecare-curating-2k-trafficking-prompts-from-74k`](https://www.kaggle.com/code/taylorsamarel/duecare-curating-2k-trafficking-prompts-from-74k) | P1 Curation (2K from 74K) | Selects balanced test prompts |
| [`00b-duecare-prompt-remixer-data-pipeline`](https://www.kaggle.com/code/taylorsamarel/00b-duecare-prompt-remixer-data-pipeline) | P2 Adversarial Remixer | 15 attack generators |
| [`duecare-adversarial-prompt-factory`](https://www.kaggle.com/code/taylorsamarel/duecare-adversarial-prompt-factory) | P3 Prompt Factory | Generate → validate → rank |

### 🎯 FINE-TUNE — Phase 3 training (1 notebook)

| Slug | Notebook | What it does |
|------|----------|--------------|
| [`duecare-phase3-finetune`](https://www.kaggle.com/code/taylorsamarel/duecare-phase3-finetune) | F1 Phase 3 Unsloth | LoRA fine-tune + GGUF export |

### 📈 REPORT — Results dashboards (1 notebook)

| Slug | Notebook | What it shows |
|------|----------|---------------|
| [`duecare-results-dashboard`](https://www.kaggle.com/code/taylorsamarel/duecare-results-dashboard) | R1 Results Dashboard | Interactive Plotly dashboard |

**All 23 notebooks are publicly visible on Kaggle.** The kernel slugs
are stable URLs and will not change. See
[`docs/NOTEBOOK_GUIDE.md`](./NOTEBOOK_GUIDE.md) for the flow diagram
and a note on why the legacy numbering looks the way it does.

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
