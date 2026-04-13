# DueCare Notebook Guide

> Complete reference for all 17 DueCare Kaggle notebooks.
> Each notebook is a self-contained experiment with clear inputs, outputs,
> and position in the evaluation pipeline.

## Pipeline Flow

```
                         ┌─────────────────────────┐
                         │   74,567 SEED PROMPTS    │
                         │   (seed_prompts.jsonl)   │
                         └───────────┬─────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              ┌──────────┐   ┌──────────┐   ┌──────────────┐
              │ NB 00a   │   │ NB 12    │   │ NB 00b       │
              │ Prioritize│   │ Prompt   │   │ Remix        │
              │ (select  │   │ Factory  │   │ (15 gens)    │
              │  2000)   │   │ (15 gens │   │              │
              └────┬─────┘   │ +validate│   └──────┬───────┘
                   │         │ +rank)   │          │
                   │         └────┬─────┘          │
                   └──────────────┼────────────────┘
                                  │
                         ┌────────▼────────┐
                         │  CURATED PROMPTS │
                         │  (validated,     │
                         │   ranked,        │
                         │   diverse)       │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
        ┌──────────┐       ┌──────────┐       ┌──────────┐
        │ NB 00    │       │ NB 05    │       │ NB P2    │
        │ Gemma    │       │ RAG vs   │       │ Model    │
        │ Baseline │       │ Plain vs │       │ Compare  │
        │ (stock)  │       │ Guided   │       │ E2B/E4B  │
        └────┬─────┘       └────┬─────┘       └────┬─────┘
             │                  │                   │
             └──────────────────┼───────────────────┘
                                │
                       ┌────────▼────────┐
                       │  MODEL RESPONSES │
                       └────────┬────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │              │              │               │
         ▼              ▼              ▼               ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ NB 09    │  │ NB 11    │  │ NB 13    │  │ NB 10    │
   │ LLM Judge│  │ Compare  │  │ Rubric   │  │ Converse │
   │ (0-100   │  │ Grading  │  │ Per-Crit │  │ Thread   │
   │  6 dims) │  │ (anchor) │  │ (54 crit)│  │ (escal.) │
   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
        │              │              │              │
        └──────────────┼──────────────┼──────────────┘
                       │              │
                ┌──────▼──────┐  ┌────▼─────┐
                │ FAILURE     │  │ CURRICULUM│
                │ ANALYSIS    │  │ DESIGN    │
                │ (6 modes)   │  │ (tags)    │
                └──────┬──────┘  └────┬──────┘
                       │              │
                       └──────┬───────┘
                              │
                     ┌────────▼────────┐
                     │ NB P3           │
                     │ Unsloth         │
                     │ Fine-tune       │
                     │ (LoRA + GGUF)   │
                     └─────────────────┘
```

## Notebook Catalog

### Data Pipeline Notebooks

| # | Title | Input | Output | GPU? |
|---|---|---|---|---|
| **00a** | Prompt Prioritizer | 74,567 seed prompts | curated_prompts.jsonl (~2,000) | No |
| **00b** | Prompt Remixer | curated prompts | remixed_prompts.jsonl (15x amplified) | No |
| **12** | Prompt Factory | base prompts | validated + ranked prompt set | No |

### Model Evaluation Notebooks

| # | Title | Input | Output | GPU? |
|---|---|---|---|---|
| **00** | Gemma Exploration | curated prompts + Gemma 4 | baseline_findings.json (scores, failures) | **Yes** |
| **05** | RAG Comparison | prompts + Gemma + KB | plain/RAG/guided comparison table | **Yes** |
| **P2** | Phase 2 Comparison | prompts + E2B + E4B | cross-model comparison | **Yes** |

### Grading & Evaluation Notebooks

| # | Title | Input | Output | GPU? |
|---|---|---|---|---|
| **09** | LLM-as-Judge (0-100) | prompt + response | 6-dimension scores (refusal, legal, completeness, safety, cultural, actionability) | No* |
| **10** | Conversation Testing | multi-turn threads | per-turn risk + cumulative escalation detection | No |
| **11** | Comparative Grading | response + best/worst references | anchored 0-100 score with gap analysis | No* |
| **13** | Rubric-Anchored Eval | response + 5 rubrics | 54 per-criterion pass/fail with evidence | No |

*When connected to Gemma via Ollama or Kaggle GPU, these use real LLM-as-judge scoring

### Adversarial & Feature Notebooks

| # | Title | Input | Output | GPU? |
|---|---|---|---|---|
| **06** | Adversarial Resistance | base prompts | 15 attack vectors demonstrated | No |
| **08** | Function Calling + Multimodal | text/images | tool calls + document analysis | No |

### Framework Demo Notebooks

| # | Title | Input | Output | GPU? |
|---|---|---|---|---|
| **01** | Quickstart | wheels dataset | smoke test (registries, scoring) | No |
| **02** | Cross-Domain Proof | 3 domain packs | identical workflows across trafficking/tax/financial | No |
| **03** | Agent Swarm Deep Dive | agent registry | 12 agents + supervisor retry/harm/budget | No |

### Fine-tuning Notebook

| # | Title | Input | Output | GPU? |
|---|---|---|---|---|
| **P3** | Unsloth Fine-tune | 1,158 training examples | LoRA adapter + GGUF (Q4_K_M) | **Yes** |

### Submission Notebook (Private)

| # | Title | Input | Output | GPU? |
|---|---|---|---|---|
| **04** | Submission Walkthrough | all prior results | compact narrative for writeup | No |

## Module Usage Map

| Module | Used in notebooks |
|---|---|
| `duecare.domains` (domain packs) | 00, 00a, 01, 02, 03, 04, 05, 06, 12, 13 |
| `duecare.tasks.generators` (15 generators) | 00b, 06, 10, 12 |
| `duecare.tasks.guardrails.weighted_scorer` | 00, 05, 13 |
| `duecare.tasks.guardrails.failure_analysis` | 00 |
| `duecare.tasks.guardrails.citation_verifier` | 00 |
| `duecare.tasks.guardrails.compliance_ratings` | (writeup) |
| `duecare.tasks.guardrails.llm_judge` | 09 |
| `duecare.agents` (12 agents) | 02, 03 |
| `duecare.agents.evolution` (mutation engine) | (pipeline stage 8) |
| `duecare.workflows` (DAG runner) | 02 |
| `duecare.models.ollama_adapter` | (local scripts) |
| `src.demo.rag` (111-entry KB) | 05 |
| `src.demo.function_calling` (5 tools) | 08 |
| `src.demo.quick_filter` (0.02ms triage) | (demo app) |
| `src.demo.visual_evasion` (5 patterns) | 08 |
| `src.demo.social_media_scorer` (30+ indicators) | (demo app) |

## Key Datasets

| Dataset | Kaggle Slug | Contents |
|---|---|---|
| DueCare Wheels | `taylorsamarel/duecare-llm-wheels` | 8 package wheels |
| Trafficking Prompts | `taylorsamarel/duecare-trafficking-prompts` | 74,567 prompts + 5 rubrics |

## Running Locally

All CPU notebooks can run locally without Kaggle:

```bash
# Install DueCare
pip install packages/duecare-llm/dist/*.whl

# Run any notebook
jupyter notebook notebooks/06_adversarial_resistance.ipynb

# Or use the scripts directly
python scripts/run_local_gemma.py --model gemma3:4b --max-prompts 10
python scripts/pipeline/run_pipeline.py --stages 4,5,6,7 --heuristic --quick
```

GPU notebooks require either Kaggle T4 x2 or a local GPU with Ollama:

```bash
ollama pull gemma4:e4b
python scripts/run_full_evaluation.py --model gemma4:e4b --max-prompts 20 --mode compare
```
