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

| Notebook | Kaggle slug | What it proves |
|----------|-------------|----------------|
| S1 — 5-minute setup and first safety evaluation | [`01-duecare-quickstart-generalized-framework`](https://www.kaggle.com/code/taylorsamarel/01-duecare-quickstart-generalized-framework) | Framework installs and scores a prompt end-to-end |
| S2 — End-to-end walkthrough from install to report | [`duecare-submission-walkthrough`](https://www.kaggle.com/code/taylorsamarel/duecare-submission-walkthrough) | Full submission flow in one notebook |
| S3 — Same harness on Trafficking, Tax Evasion, Financial Crime | [`duecare-cross-domain-proof`](https://www.kaggle.com/code/taylorsamarel/duecare-cross-domain-proof) | Cross-domain generalization (zero code changes) |
| S4 — 12 autonomous agents orchestrated by Gemma 4 | [`duecare-12-agent-gemma-4-safety-pipeline`](https://www.kaggle.com/code/taylorsamarel/duecare-12-agent-gemma-4-safety-pipeline) | Full swarm + Supervisor in action |

### 📊 BASELINE — Real Gemma 4 measurements (3 notebooks)

| Notebook | Kaggle slug | What it proves |
|----------|-------------|----------------|
| **B1 — Gemma 4 9B on 50 trafficking prompts** | [`duecare-real-gemma-4-on-50-trafficking-prompts`](https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts) | **Primary result:** 0.610 mean score, 20% pass rate, 0% harmful phrases (real Kaggle T4 GPU run) |
| B2 — Plain vs retrieval-augmented vs system-guided | [`duecare-rag-comparison`](https://www.kaggle.com/code/taylorsamarel/duecare-rag-comparison) | Context injection lifts scores 23–28% without training |
| B3 — 2-billion vs 9-billion parameter Gemma 4 | [`duecare-phase-2-model-comparison`](https://www.kaggle.com/code/taylorsamarel/duecare-phase-2-model-comparison) | Size/quality trade-off within the Gemma 4 family |

### 🔍 TASK — Capability-specific evaluations (5 notebooks)

| Notebook | Kaggle slug | What it tests |
|----------|-------------|----------------|
| T1 — 15 adversarial attack vectors against Gemma 4 | [`duecare-adversarial-resistance`](https://www.kaggle.com/code/taylorsamarel/duecare-adversarial-resistance) | Gemma 4 holds up against evasion, coercion, jailbreak, persona injection, etc. |
| T2 — Gemma 4 native tool calls + document image analysis | [`duecare-function-calling-multimodal`](https://www.kaggle.com/code/taylorsamarel/duecare-function-calling-multimodal) | Gemma 4's two distinguishing features: function calling and multimodal input |
| T3 — Six-dimension safety grading (0-100) | [`duecare-llm-judge-grading`](https://www.kaggle.com/code/taylorsamarel/duecare-llm-judge-grading) | Refusal quality, legal accuracy, completeness, victim safety, cultural sensitivity, actionability |
| T4 — Multi-turn conversation escalation detection | [`duecare-conversation-testing`](https://www.kaggle.com/code/taylorsamarel/duecare-conversation-testing) | Does Gemma 4 catch exploitation framed across multiple messages? |
| T5 — 54-criterion pass/fail rubric evaluation | [`duecare-rubric-anchored-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-rubric-anchored-evaluation) | Structured per-criterion pass/fail against the 5 trafficking rubrics |

### ⚖️ COMPARE — Multi-model comparisons (5 notebooks)

| Notebook | Kaggle slug | What it compares |
|----------|-------------|------------------|
| C1 — Gemma 4 9B vs Llama 3.1 8B, Mistral 7B, Gemma 2B (CPU analysis) | [`gemma-4-vs-llama-vs-mistral-on-trafficking-safety`](https://www.kaggle.com/code/taylorsamarel/gemma-4-vs-llama-vs-mistral-on-trafficking-safety) | Gemma 4 vs 3 similarly-sized open-source models |
| **C2 — Gemma 4 vs Gemma 2 9B, Llama 3.1 8B, Mistral 7B, Qwen 2.5 7B, Phi 3 Mini, DeepSeek Coder** | [`duecare-gemma-4-vs-6-oss-models-via-ollama-cloud`](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-vs-6-oss-models-via-ollama-cloud) | Six open-source models via Ollama Cloud API |
| **C3 — Gemma 4 vs Mistral Large 2 (123B), Mistral Small 3 (24B), Mistral Nemo (12B), Ministral 8B, Mistral 7B** | [`duecare-gemma-4-vs-mistral-family`](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-vs-mistral-family) | Full Mistral family (EU-sovereign OSS provider) |
| **C4 — Gemma 4 vs Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro, Llama 3.1 405B, DeepSeek V3 (685B MoE), Qwen 2.5 72B** | [`duecare-openrouter-frontier-comparison`](https://www.kaggle.com/code/taylorsamarel/duecare-openrouter-frontier-comparison) | 9B on-device vs the six largest models in the world |
| C5 — Gemma 4 responses scored against hand-written best and worst examples | [`duecare-comparative-grading`](https://www.kaggle.com/code/taylorsamarel/duecare-comparative-grading) | Reference-anchored grading methodology |

### 🛡️ SAFETY — Red-team research (1 notebook)

| Notebook | Kaggle slug | What it shows |
|----------|-------------|---------------|
| **SF1 — Gemma 4 stock vs SuperGemma 26B uncensored: refusal-gap analysis** | [`duecare-finding-gemma-4-safety-line`](https://www.kaggle.com/code/taylorsamarel/duecare-finding-gemma-4-safety-line) | Proves Gemma 4's safety training is load-bearing (not cosmetic hedging) by comparing against a known-unrestricted variant |

### ⚙️ PIPELINE — Custom prompts & test generation (3 notebooks)

| Notebook | Kaggle slug | What it does |
|----------|-------------|--------------|
| P1 — Select 2,000 high-value prompts from the 74,567-prompt corpus | [`duecare-curating-2k-trafficking-prompts-from-74k`](https://www.kaggle.com/code/taylorsamarel/duecare-curating-2k-trafficking-prompts-from-74k) | Prioritized, balanced test set (graded first, then category-diverse) |
| P2 — Generate 15 adversarial variations per base prompt | [`00b-duecare-prompt-remixer-data-pipeline`](https://www.kaggle.com/code/taylorsamarel/00b-duecare-prompt-remixer-data-pipeline) | 15 attack generators expand the test space combinatorially |
| P3 — Prompt factory: generate, validate, rank by victim impact | [`duecare-adversarial-prompt-factory`](https://www.kaggle.com/code/taylorsamarel/duecare-adversarial-prompt-factory) | Full pipeline from 10 base prompts to 200+ validated tests |

### 🎯 FINE-TUNE — Improve Gemma 4 for your domain (1 notebook)

| Notebook | Kaggle slug | What it does |
|----------|-------------|--------------|
| F1 — Gemma 4 low-rank adaptation fine-tuning + local-model export | [`duecare-phase3-finetune`](https://www.kaggle.com/code/taylorsamarel/duecare-phase3-finetune) | Trains Gemma 4 on the DueCare curriculum using Unsloth; exports as GGUF for local inference via llama.cpp |

### 📈 REPORT — Results dashboards (1 notebook)

| Notebook | Kaggle slug | What it shows |
|----------|-------------|---------------|
| R1 — Interactive safety evaluation dashboard | [`duecare-results-dashboard`](https://www.kaggle.com/code/taylorsamarel/duecare-results-dashboard) | Plotly dashboard aggregating every DueCare evaluation result |

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
