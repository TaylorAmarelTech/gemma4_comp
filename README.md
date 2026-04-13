# DueCare — exercising due care in LLM safety design

> Named for Cal. Civ. Code § 1714(a) — the duty of care standard that
> a California jury applied to find Meta and Google negligent for
> defective platform design in March 2026. DueCare applies the same
> standard to LLM safety: does the model exercise *due care* when
> responding to prompts about trafficking, exploitation, and financial crime?
>
> **74,567 prompts. 5 weighted rubrics. 48+ evaluation criteria.
> 12 autonomous agents. One CLI command. On your laptop.**
>
> **Built for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon).**
> Gemma 4 is DueCare's first published benchmark.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-407%20passing-brightgreen.svg)](#tests)
[![Packages](https://img.shields.io/badge/packages-8-blue.svg)](#packages)

---

## Why this exists

Frontier LLMs fail predictably on **migrant-worker trafficking**
scenarios — documented in the author's prior
[OpenAI gpt-oss-20b Red-Teaming Challenge writeup](https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/llm-complicity-in-modern-slavery-from-native-blind).
The organizations that most need to evaluate LLMs for these scenarios —
frontline NGOs, Gulf/Southeast-Asia recruitment regulators, labor
ministries, ILO field offices — **cannot send sensitive case data to
frontier APIs**. They need a local evaluator that runs on a laptop.

> "A community where privacy is non-negotiable."
> — _Gemma 4 Good Hackathon problem statement_

Duecare is that evaluator. And because it's built as a **universal**
safety harness, the same infrastructure applies to tax evasion, money
laundering, medical misinformation, and any other safety domain that
can describe itself with a taxonomy, an evidence base, and a rubric.

## What ships

**8 PyPI packages** sharing the `duecare` Python namespace (PEP 420), all
installable from a single `pip install duecare-llm`:

| Package | Role | Tests |
|---|---|---|
| [`duecare-llm-core`](./docs/components/duecare_llm_core.md) | Contracts, schemas, enums, registries, provenance, observability | 86 ✅ |
| [`duecare-llm-models`](./docs/components/duecare_llm_models.md) | 8 model adapters (Transformers, llama.cpp, Unsloth, Ollama, OpenAI-compatible, Anthropic, Gemini, HF Endpoint) | 22 ✅ |
| [`duecare-llm-domains`](./docs/components/duecare_llm_domains.md) | Pluggable domain packs + 3 shipped (trafficking, tax_evasion, financial_crime) | 23 ✅ |
| [`duecare-llm-tasks`](./docs/components/duecare_llm_tasks.md) | 9 capability tests (guardrails, anon, classify, extract, grounding, multimodal, multi-turn, tool-use, cross-lingual) | 16 ✅ |
| [`duecare-llm-agents`](./docs/components/duecare_llm_agents.md) | 12-agent swarm + AgentSupervisor with retry/budget/harm-abort | 17 ✅ |
| [`duecare-llm-workflows`](./docs/components/duecare_llm_workflows.md) | YAML DAG loader + topological runner | 9 ✅ |
| [`duecare-llm-publishing`](./docs/components/duecare_llm_publishing.md) | HF Hub + Kaggle publisher, markdown reports, HF model cards | 9 ✅ |
| [`duecare-llm`](./docs/components/duecare_llm_meta.md) (meta) | `duecare` CLI + re-exports from all 7 siblings | 6 ✅ |
| **Total** | | **407 ✅** |

## Quick start

### Install

```bash
# Everything (meta package pulls in all 7 siblings)
pip install duecare-llm

# Or, granular: install only what a Kaggle notebook needs
pip install duecare-llm-core duecare-llm-domains duecare-llm-tasks duecare-llm-agents
```

### Run locally with Ollama (recommended for development)

```bash
# 1. Install Ollama: https://ollama.com/download
# 2. Pull Gemma 4
ollama pull gemma4:e4b          # ~4GB (Q4 quantized)

# 3. Run the evaluation
python scripts/run_local_gemma.py --max-prompts 10   # quick test
python scripts/run_local_gemma.py --graded-only       # 204 graded prompts
python scripts/run_local_gemma.py --model gemma4:e2b   # smaller model

# Output: per-prompt scores, headline metrics, findings JSON
```

### Run on Kaggle (GPU)

Open the notebook, set Accelerator to **GPU T4 x2**, and run:
- [00 — Gemma Exploration](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-exploration) — real Gemma inference + scoring

### Run a workflow

```bash
# Trafficking domain, rapid smoke-test workflow
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain trafficking

# Output:
#   scout      - Domain 'trafficking' ready (score=1.00): 12 prompts, 10 evidence, 5 categories
#   judge      - ...
#   historian  - Wrote run report to reports/20260411160443_...rapid_probe.md
#
#   +-------------+------------------------------------+
#   | run_id      | 20260411160443_..._rapid_probe     |
#   | status      | completed                          |
#   | config_hash | 8337ebd57bb057dc...                |
#   | cost_usd    | $0.0000                            |
#   +-------------+------------------------------------+
```

### Explore the components

```bash
# 15 adversarial generators, 7 evaluators, 12 agents
python -c "from duecare.tasks.generators import ALL_GENERATORS; print(f'{len(ALL_GENERATORS)} generators')"
python -c "from duecare.agents import agent_registry; print(f'{len(agent_registry)} agents')"
python -c "from duecare.tasks import task_registry; print(f'{len(task_registry)} tasks')"

# Run the 8-stage pipeline locally
python scripts/pipeline/run_pipeline.py --stages 4,5,6,7 --heuristic --quick

# Run the demo app
uvicorn src.demo.app:app --port 8080
# Open http://localhost:8080 for the HTML dashboard
```

### 17 Kaggle Notebooks

See [docs/notebook_guide.md](docs/notebook_guide.md) for the complete catalog.

```
Notebooks:
  00    Gemma Baseline (real model, stock evaluation)
  00a   Prompt Prioritizer (select from 74K corpus)
  00b   Prompt Remixer (15 adversarial generators)
  01-04 Framework demos (quickstart, cross-domain, agents, submission)
  05    RAG vs Plain vs Guided comparison
  06    Adversarial attack resistance (15 vectors)
  08    Function calling + multimodal demo
  09    LLM-as-Judge grading (0-100, 6 dimensions)
  10    Conversation thread testing (escalation detection)
  11    Comparative grading (anchored to best/worst references)
  12    Prompt factory (generate → validate → rank)
  13    Rubric-anchored evaluation (54 criteria, per-criterion pass/fail)
  P2    Phase 2 model comparison (E2B vs E4B)
  P3    Phase 3 Unsloth fine-tune (LoRA + GGUF export)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DueCare Pipeline                        │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Acquire  │→ │ Classify │→ │ Extract  │→ │ Build KB │       │
│  │ (Stage 1)│  │ (Stage 2)│  │ (Stage 3)│  │ (Stage 4)│       │
│  │ ILO,POEA │  │ Gemma 4  │  │ Gemma 4  │  │ 111 facts│       │
│  └──────────┘  └──────────┘  └──────────┘  └────┬─────┘       │
│                                                  │              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────▼─────┐       │
│  │ Baseline │← │ Remix    │← │ Rate     │← │ Generate │       │
│  │ (Stage 8)│  │ (Stage 7)│  │ (Stage 6)│  │ (Stage 5)│       │
│  │ 3 modes  │  │ 15 gens  │  │ rank     │  │ from KB  │       │
│  └────┬─────┘  └──────────┘  └──────────┘  └──────────┘       │
│       │                                                         │
│  ┌────▼─────────────────────────────────────────────┐          │
│  │              EVALUATION LAYER                     │          │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │          │
│  │  │Weighted │ │Multi-   │ │LLM-as-  │ │FATF /  │ │          │
│  │  │Rubric   │ │Layer    │ │Judge    │ │TIPS    │ │          │
│  │  │(54 crit)│ │(6 stage)│ │(0-100)  │ │Ratings │ │          │
│  │  └─────────┘ └─────────┘ └─────────┘ └────────┘ │          │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐            │          │
│  │  │Failure  │ │Citation │ │Comparatv│            │          │
│  │  │Analyzer │ │Verifier │ │Grading  │            │          │
│  │  │(6 modes)│ │(31 laws)│ │(anchor) │            │          │
│  │  └─────────┘ └─────────┘ └─────────┘            │          │
│  └──────────────────────────────────────────────────┘          │
│                         │                                       │
│                    ┌────▼─────┐                                │
│                    │ Phase 3  │                                │
│                    │ Fine-tune│                                │
│                    │ (Unsloth)│                                │
│                    └──────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

### Key results

| Metric | Value |
|---|---|
| Stock Gemma 3 4B mean score | **0.40** (local baseline) |
| Stock Gemma 3 4B pass rate | **0%** (local baseline) |
| With RAG context | **0.59** (+23% over plain) |
| With guided prompt | **0.62** (+28% over plain) |
| Trafficking prompt corpus | **74,567** |
| Adversarial generators | **15** |
| Evaluation frameworks | **7** |
| Tests passing | **407** |

### Use it as a library

```python
from duecare.workflows import WorkflowRunner
from duecare.agents import AgentSupervisor
from duecare.agents.base import SupervisorPolicy

runner = WorkflowRunner.from_yaml("configs/duecare/workflows/evaluate_only.yaml")

# Attach a concrete model instance for the Judge to test
from duecare.models.openai_compatible_adapter import OpenAICompatibleModel
target_model = OpenAICompatibleModel(
    model_id="gpt-4o-mini",
    base_url="https://api.openai.com/v1",
    api_key_env="OPENAI_API_KEY",
)

result = runner.run(
    target_model_id="gpt-4o-mini",
    domain_id="trafficking",
    target_model_instance=target_model,
)

print(result.summary())
# evaluate_only [completed] run=... model=gpt-4o-mini domain=trafficking cost=$0.34 duration=89.2s
```

### Add a new domain pack (no code change)

```bash
mkdir -p configs/duecare/domains/my_new_domain
cp configs/duecare/domains/trafficking/*.yaml configs/duecare/domains/my_new_domain/
# Edit card.yaml, taxonomy.yaml, rubric.yaml, pii_spec.yaml for your domain
# Populate seed_prompts.jsonl + evidence.jsonl

forge domains list  # your new domain shows up
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain my_new_domain
```

### Add a new model (no code change)

Edit `configs/duecare/models.yaml` and add a new row:

```yaml
- id: gemma_5_e4b_stock
  display_name: "Gemma 5 E4B (stock)"
  adapter: transformers
  model_id: google/gemma-5-e4b-it
  capabilities: [text, vision, function_calling, fine_tunable]
```

When Gemma 5 ships, that's the entire integration cost: one YAML row.

## Architecture

```
                    ┌───────────────────────────────────┐
                    │  LAYER 6: PUBLICATION             │
                    │  HF Hub, Kaggle, reports, cards   │
                    └──────────────┬────────────────────┘
                                   │
                    ┌──────────────┴────────────────────┐
                    │  LAYER 5: ORCHESTRATION           │
                    │  WorkflowRunner, DAG, AgentSupervisor │
                    └──────────────┬────────────────────┘
                                   │
                    ┌──────────────┴────────────────────┐
                    │  LAYER 4: AGENT SWARM             │
                    │  12 autonomous agents             │
                    │  ┌──────┐┌──────┐┌──────┐        │
                    │  │Scout ││Judge ││Curator│ ...   │
                    │  └──────┘└──────┘└──────┘        │
                    └──────────────┬────────────────────┘
                                   │
                    ┌──────────────┴────────────────────┐
                    │  LAYER 3: TASKS                   │
                    │  9 capability tests per (model,   │
                    │  domain) pair                     │
                    └──────────────┬────────────────────┘
                                   │
                ┌──────────────────┴──────────────────┐
                │                                     │
   ┌────────────┴───────────┐           ┌────────────┴───────────┐
   │ LAYER 2a: MODELS       │           │ LAYER 2b: DOMAINS      │
   │ 8 pluggable adapters   │           │ 3 shipped packs + any  │
   │                        │           │ custom pack            │
   └────────────┬───────────┘           └────────────┬───────────┘
                │                                     │
                └──────────────┬──────────────────────┘
                               │
                ┌──────────────┴───────────────────────┐
                │  LAYER 1: CORE / CONTRACTS           │
                │  Protocols, schemas, Registry,       │
                │  provenance, observability           │
                └──────────────────────────────────────┘
```

### Key design decisions

1. **`typing.Protocol`, not ABCs.** Model adapters, domain packs,
   tasks, agents are all structurally typed. No forced inheritance.
2. **Pydantic v2 for every data model.** JSON round-trips for free,
   strict validation at every layer boundary.
3. **PEP 420 namespace packages.** All 8 packages share the `duecare`
   Python namespace. Install one or all eight; imports work identically.
4. **AgentSupervisor meta-agent** enforces retry, budget, and
   abort-on-harm policies across every agent call. Validator can
   signal `harm_detected=True` to abort a release workflow immediately.
5. **Folder-per-module** — every module is its own folder with 7 meta
   files (PURPOSE, AGENTS, INPUTS_OUTPUTS, HIERARCHY, DIAGRAM, TESTS,
   STATUS) auto-generated from a descriptor list. Changing a module's
   dependencies regenerates cross-references across the whole tree in
   one script run.
6. **Provenance on every record** — `(run_id, git_sha, config_hash,
   dataset_version)` stamped on every artifact so runs are reproducible
   to the byte.
7. **AGENTS.md standard** — the 58 per-module `AGENTS.md` files are
   compliant with the Linux Foundation's
   [AGENTS.md standard](https://agents.md/), which is read natively by
   Claude Code, Cursor, GitHub Copilot, Gemini CLI, Windsurf, Aider,
   Zed, Warp, and RooCode.

## Domain packs (cross-domain proof)

Duecare ships three domain packs out of the box, demonstrating that the
architecture is **genuinely domain-agnostic**:

| Pack | Seed prompts | Evidence items | Categories | Taxonomy dimensions |
|---|---|---|---|---|
| `trafficking` | 74,567 | 10 | 5 | sector, corridor, ILO indicator, attack category, difficulty |
| `tax_evasion` | 4 | 4 | 4 | scheme type, jurisdiction, FATF indicator, sophistication |
| `financial_crime` | 3 | 3 | 4 | laundering stage, typology, FATF indicator, jurisdiction |

All three use the same `FileDomainPack` implementation. All three work
with the same `duecare run` command. All three are hot-swappable at the
CLI.

## Model support (the comparison field)

Ten registered models in `configs/duecare/models.yaml`:

- **Gemma 4** (primary subject): E2B, E4B — local via Transformers
- **Open competition**: GPT-OSS 20B, Qwen 2.5 7B, Llama 3.1 8B — local
- **API**: Mistral Small, DeepSeek V3 — via OpenAI-compatible adapter
- **Reference (closed)**: GPT-4o mini, Claude Haiku 4.5, Gemini 2.0
  Flash — via their native adapters

Eight model adapters in total. New providers = new adapter file + new
YAML row; no changes to any downstream layer.

## The 12-agent swarm

```
Scout → DataGenerator → Adversary → Anonymizer → Curator → Judge →
CurriculumDesigner → Trainer → Validator → Exporter → Historian

                              ▲
                              │
                        Coordinator
                  (Gemma 4 E4B + function calling)
```

Every agent is in its own folder with real code, real tests, and a
stable contract. The Coordinator wraps the others in an
`AgentSupervisor` that enforces retries, hard budget caps, and
abort-on-harm. The Validator can set `harm_detected=True` on the
shared blackboard — the Supervisor raises `HarmDetected` and aborts
the workflow before anything gets published.

See [`docs/components/duecare_llm_agents.md`](./docs/components/duecare_llm_agents.md)
for per-agent documentation.

## Tests

```bash
# All 407 tests across all 8 packages
python -m pytest packages -v

# Single package
python -m pytest packages/duecare-llm-core -v

# Single module folder (folder-per-module pattern)
python -m pytest packages/duecare-llm-core/src/forge/core/enums -v
```

Latest full run:

```
========================= 407 passed, 9 warnings in 525.38s =========================
```

## Demo notebook

`notebooks/duecare_llm_core_demo.ipynb` — a runnable Jupyter notebook
exercising every public surface of `duecare-llm-core`. 22 cells (12
code), verified to execute end-to-end against the installed wheel. A
good starting point for understanding the shape of the Duecare API.

The Kaggle submission notebook that runs the full cross-domain
workflow lives at `notebooks/forge_kaggle_submission.ipynb`.

## Configuration

All configuration lives in `configs/duecare/` as YAML:

```
configs/duecare/
├── models.yaml                   # model registry
├── workflows/
│   ├── rapid_probe.yaml          # 15-min smoke test
│   ├── evaluate_only.yaml        # 2-hour eval
│   ├── evaluate_and_finetune.yaml  # 12-hour full cycle
│   └── evaluate_only_comparison.yaml
└── domains/
    ├── trafficking/
    ├── tax_evasion/
    └── financial_crime/
```

Secrets (API keys) come from environment variables only — see
[`.env.template`](./.env.template).

## Repository layout

```
gemma4_comp/
├── packages/                     # 8 PyPI packages (workspace members)
│   ├── duecare-llm-core/
│   ├── duecare-llm-models/
│   ├── duecare-llm-domains/
│   ├── duecare-llm-tasks/
│   ├── duecare-llm-agents/
│   ├── duecare-llm-workflows/
│   ├── duecare-llm-publishing/
│   └── duecare-llm/                # meta package + CLI
├── configs/duecare/                # YAML configuration (models, workflows, domains)
├── docs/                         # architecture, component docs, writeup, video script
│   └── components/               # per-package component docs
├── notebooks/                    # Jupyter demos
├── scripts/                      # implementation + maintenance scripts
├── tests/                        # integration tests
├── pyproject.toml                # uv workspace root
├── .mcp.json                     # Claude Code MCP servers (empty by default)
├── .mcp.json.example             # example MCP config (GitHub / Claude Context / Repomix)
├── .github/workflows/            # CI (@claude PR review + pytest)
├── .claude/
│   ├── rules/                    # auto-loaded Claude Code rules
│   └── commands/                 # project slash commands
└── CLAUDE.md                     # AI-assistant context
```

## License

MIT. See [`LICENSE`](./LICENSE).

## Citation

```bibtex
@misc{amarel2026forge,
  title={{Duecare: An Agentic Safety Harness for LLMs}},
  author={Amarel, Taylor},
  year={2026},
  howpublished={Kaggle Gemma 4 Good Hackathon},
  url={https://github.com/taylorsamarel/gemma4_comp},
}
```

## Acknowledgements

Built on top of the author's existing *LLM Safety Testing Ecosystem*
for migrant-worker protection: a 21K-test benchmark, 26 migration
corridors, 174 scraper seed modules, 20,460+ facts, and 126 attack
chains. Grounded in ILO Conventions C029 / C097 / C181 / C189, the UN
Palermo Protocol, the TVPA, 18 years of POEA enforcement data, and the
FATF 40 Recommendations.

Judged primarily on a 3-minute video. Built for the people who need
this tool and cannot use the cloud.
