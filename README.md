# DueCare — exercising due care in LLM safety design

> Named for Cal. Civ. Code § 1714(a) — the duty of care standard that
> a California jury applied to find Meta and Google negligent for
> defective platform design in March 2026. DueCare applies the same
> standard to LLM safety: does the model exercise *due care* when
> responding to prompts about trafficking, exploitation, and financial crime?
>
> **North star: inform AND document.** A migrant worker can follow
> the chatbot's advice (don't pay the illegal fee) — or pay anyway
> under their corridor's real constraints, with the journal
> capturing every receipt + statute citation + recipient so the
> same harness pre-stages the refund claim. Harm reduction, not
> paternalism. Fully offline.
>
> **74,567 prompts. 6 weighted rubrics. 66 evaluation criteria.
> One CLI command. On your laptop or in your pocket.**
>
> **Built for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon).**
> Gemma 4 is DueCare's first published benchmark.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-194%20passing-brightgreen.svg)](#tests)
[![Packages](https://img.shields.io/badge/packages-17-blue.svg)](#packages)

> ### 🚀 Submission state (Gemma 4 Good Hackathon, due 2026-05-18)
>
> **6 core + 5 appendix = 11 Kaggle notebooks** (the submission surface).
> Walk the core in canonical order — each builds context for the next.
> Single-page index with one-line summaries:
> [`docs/notebook_index.md`](./docs/notebook_index.md).
>
> **Core (judges evaluate first):**
>
> 1. [`duecare-chat-playground`](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground) — raw Gemma 4, no harness. Baseline.
> 2. [`duecare-chat-playground-with-grep-rag-tools`](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools) — same chat UI + 4 toggleable safety layers + per-response Pipeline modal. *Headline demo.*
> 3. `duecare-content-classification-playground` *(publish pending)* — hands-on classification sandbox; 4 schema modes (single/multi-label, risk-vector, custom JSON Schema).
> 4. `duecare-content-knowledge-builder-playground` *(publish pending)* — hands-on KB builder; add GREP rules, RAG docs, lookup tables; export full JSON.
> 5. [`duecare-gemma-content-classification-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation) — polished NGO/agency dashboard with risk vectors + threshold-filtered queue.
> 6. [`duecare-live-demo`](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) — full deployed product. Combines #3 + #4 in one polished surface.
>
> **Appendix (advanced extension + research, optional):**
>
> - A1. `duecare-prompt-generation` — Gemma 4 generates new evaluation prompts + 5 graded responses each
> - A2. `duecare-bench-and-tune` — Unsloth SFT → DPO → GGUF Q8_0 → HF Hub push
> - A3. `duecare-research-graphs` — 6 interactive Plotly charts (CPU-only, ~30 sec)
> - A4. `duecare-chat-playground-with-agentic-research` — 5th toggle: **online agentic research** (the only layer that touches the network — all others are local, in-process); BYOK panel (Tavily / Brave / Serper) or Playwright real-browser fallback; PII-filtered before any outbound call, audit-logged as sha256 hashes only
> - A5. `duecare-chat-playground-jailbroken-models` — loads abliterated/cracked Gemma 4 variants; proves the harness works even when refusals are ablated
>
> **Judges start here:** [`docs/FOR_JUDGES.md`](./docs/FOR_JUDGES.md) (5-min verification path).
> **Writeup (≤1500 words):** [`docs/writeup_draft.md`](./docs/writeup_draft.md).
> **Video script (~2:50):** [`docs/video_script.md`](./docs/video_script.md).
> **Audit / report card:** [`docs/REPORT_CARD.md`](./docs/REPORT_CARD.md).
> **Harness lift report:** [`docs/harness_lift_report.md`](./docs/harness_lift_report.md) — quantifies how RAG/GREP/Tools change rubric scores (mean **+56.5 pp** on the cross-cutting `legal_citation_quality` rubric, 207/207 prompts).
> **Corpus coverage:** [`docs/corpus_coverage.md`](./docs/corpus_coverage.md) — 2D coverage matrices across category × sector × corridor × ILO indicator.
> **Stretch — Android (LiteRT track):** [`docs/android_app_architecture.md`](./docs/android_app_architecture.md) — Duecare Journey, the on-device companion. v1 architecture published here; **APK skeleton + GitHub Actions APK build pipeline live in the sibling repo `duecare-journey-android/`** (separated so Android tooling doesn't collide with the Python research workflow). v1 MVP build lands week of 2026-05-19.
> **Provenance:** [`RESULTS.md`](./RESULTS.md) — every metric pinned to `(git_sha, dataset_version, model_revision)`.
>
> **Three deployment modes:**
>
> - **Worker-side / local** — chat playground on Kaggle free T4 or your own GPU; get back ILO citations + corridor fee caps + NGO hotlines. Setup: [`docs/deployment_local.md`](./docs/deployment_local.md).
> - **Agency / NGO dashboard** — form-based content submission → structured JSON risk envelope (Core #5).
> - **Enterprise integration** — `POST /api/classifier/evaluate` from your existing service. Dockerized API: [`docs/deployment_enterprise.md`](./docs/deployment_enterprise.md).
>
> No data leaves the device. Privacy is non-negotiable.

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

**17 PyPI packages** sharing the `duecare` Python namespace (PEP 420), all
installable from a single `pip install duecare-llm`:

| Package | Role | Tests |
|---|---|---|
| [`duecare-llm-core`](./docs/components/duecare_llm_core.md) | Contracts, schemas, enums, registries, provenance, observability | 77 ✅ |
| [`duecare-llm-models`](./docs/components/duecare_llm_models.md) | 8 model adapters (Transformers+Gemma 4 function calling, llama.cpp, Unsloth, Ollama, OpenAI-compatible, Anthropic, Gemini, HF Endpoint) | 28 ✅ |
| [`duecare-llm-domains`](./docs/components/duecare_llm_domains.md) | Pluggable domain packs + 3 shipped (trafficking, tax_evasion, financial_crime) | 23 ✅ |
| [`duecare-llm-tasks`](./docs/components/duecare_llm_tasks.md) | 9 capability tests (guardrails, anon, classify, extract, grounding, multimodal, multi-turn, tool-use, cross-lingual) | 16 ✅ |
| [`duecare-llm-agents`](./docs/components/duecare_llm_agents.md) | 12-agent swarm + AgentSupervisor with retry/budget/harm-abort + Gemma 4 function-calling orchestration | 26 ✅ |
| [`duecare-llm-workflows`](./docs/components/duecare_llm_workflows.md) | YAML DAG loader + topological runner | 9 ✅ |
| [`duecare-llm-publishing`](./docs/components/duecare_llm_publishing.md) | HF Hub + Kaggle publisher, markdown reports, HF model cards | 9 ✅ |
| `duecare-llm-engine` | Heuristic prescan + GREP KB + RAG + tool-call + Gemma verdict pipeline (the safety harness) | — |
| `duecare-llm-server` | FastAPI app that hosts the pipeline + audit dashboard (the live demo) | — |
| `duecare-llm-evidence-db` | Redacted-evidence corpus + audit trail SQLite store | — |
| `duecare-llm-benchmark` | `smoke_25` + `score_row` + `aggregate` scoring helpers (zero deps) | — |
| `duecare-llm-training` | Unsloth SFT + DPO scripts, GGUF export | — |
| `duecare-llm-research-tools` | Playwright scrapers + document extractors for domain corpora | — |
| `duecare-llm-nl2sql` | NL → SQL translator for evidence DB queries | — |
| `duecare-llm-chat` | Minimal Gemma 4 chat playground (UI + FastAPI shell, no harness) | — |
| `duecare-llm-cli` | The `duecare` command-line tool (tree, test, review, status, deps) | — |
| [`duecare-llm`](./docs/components/duecare_llm_meta.md) (meta) | Pulls in all 16 siblings + the CLI | — |
| **Total** | | **194 ✅** |

## Quick start

### Install

```bash
# Everything (meta package pulls in all 16 siblings)
pip install duecare-llm

# Or, granular: install only what a Kaggle notebook needs
pip install duecare-llm-core duecare-llm-domains duecare-llm-tasks duecare-llm-agents
```

### Run locally with Ollama (recommended for development)

```bash
# 1. Install Ollama: https://ollama.com/download
# 2. Pull Gemma 4
ollama pull gemma4:e2b          # ~1.5GB INT8 (default)
# or
ollama pull gemma4:e4b          # ~3.5GB INT8 (higher quality)

# 3. Run the evaluation
python scripts/run_local_gemma.py --max-prompts 10   # quick test
python scripts/run_local_gemma.py --graded-only       # 204 graded prompts
python scripts/run_local_gemma.py --model gemma4:e2b   # smaller model

# Output: per-prompt scores, headline metrics, findings JSON
```

### Deploy in 60 seconds

```bash
# One-command bring-up: Docker stack + Gemma 4 pull + smoke test.
make demo

# After it finishes:
open http://localhost:8080
```

After deploy: `make doctor` for a one-screen health report,
`make backup` for a journal/audit snapshot.

### Pick your deployment shape (by persona)

| You are... | Read |
|---|---|
| **OFW / migrant worker** wanting it on your phone | [`docs/scenarios/worker-self-help.md`](./docs/scenarios/worker-self-help.md) |
| **Caseworker** at an NGO using Duecare | [`docs/scenarios/caseworker_workflow.md`](./docs/scenarios/caseworker_workflow.md) |
| **NGO director** running it at the office | [`docs/scenarios/ngo-office-deployment.md`](./docs/scenarios/ngo-office-deployment.md) |
| **Legal aid lawyer** preparing a case | [`docs/scenarios/lawyer-evidence-prep.md`](./docs/scenarios/lawyer-evidence-prep.md) |
| **Government regulator** doing pattern analysis | [`docs/scenarios/regulator-pattern-analysis.md`](./docs/scenarios/regulator-pattern-analysis.md) |
| **Recruitment-agency compliance officer** | [`docs/scenarios/recruiter-self-audit.md`](./docs/scenarios/recruiter-self-audit.md) |
| **Individual researcher** (academic / journalist) | [`docs/scenarios/researcher-analysis.md`](./docs/scenarios/researcher-analysis.md) |
| **IT director** evaluating ops + TCO | [`docs/scenarios/it-director.md`](./docs/scenarios/it-director.md) |
| **Chief architect** designing integration | [`docs/scenarios/chief-architect.md`](./docs/scenarios/chief-architect.md) |
| **VP of Engineering** at a product org | [`docs/scenarios/vp-engineering.md`](./docs/scenarios/vp-engineering.md) |
| **Platform CTO** at Big Tech | [`docs/scenarios/enterprise_pilot.md`](./docs/scenarios/enterprise_pilot.md) |
| Solo developer evaluating on a laptop | [`docs/deployment_local.md`](./docs/deployment_local.md) |
| Skim the topology choices | [`docs/deployment_topologies.md`](./docs/deployment_topologies.md) |
| Deploy on a specific cloud | [`docs/cloud_deployment.md`](./docs/cloud_deployment.md) |
| Pick a Gemma 4 variant | [`docs/gemma4_model_guide.md`](./docs/gemma4_model_guide.md) |

Five runnable topology examples at [`examples/deployment/`](./examples/deployment/).
Optional enterprise governance supplements (SLOs, runbook,
compliance crosswalk, threat model, vendor questionnaire) at
[`docs/considerations/`](./docs/considerations/) — read only if you need them.

### Just want to look at it?

- [**Try in 2 minutes**](./docs/try_in_2_minutes.md) — fastest path
  per persona, no install required for most options
- [**Comparison vs alternatives**](./docs/comparison_to_alternatives.md)
  — when Duecare fits vs when Hive / Sift / Azure / OpenAI / Llama
  Guard fit better
- [**Press kit**](./docs/press_kit.md) — one-pager + facts + quotes
  for journalists, NGO comms, academics
- [**Educator resources**](./docs/educator_resources.md) — drop-in
  lesson plans for AI-ethics / social-work / migration-studies courses
- [**First-deployer feedback template**](./docs/first_deployer_feedback.md)
  — if you tried it in your real environment, your input shapes v0.8

### Run on Kaggle (GPU)

Open the notebook, set Accelerator to **GPU T4 x2**, and run:
- [100 — Gemma Exploration](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-exploration) — real Gemma inference + scoring

### Run a workflow

```bash
# Trafficking domain, rapid smoke-test workflow
duecare run rapid_probe --target-model gemma_4_e4b_stock --domain trafficking

# Output when the target-model backend is installed and configured:
#   scout      - Domain 'trafficking' ready (score=1.00)
#   judge      - Ran capability tests for the configured target model
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

### 76 Kaggle Notebooks — numbered reading order

The notebook suite now uses three-digit reading-order IDs instead of the
old historical `NB XX` scheme.

- Full table and one-line purposes: [`docs/notebook_guide.md`](./docs/notebook_guide.md)
- Exact kernel inventory and mirror map: [`docs/current_kaggle_notebook_state.md`](./docs/current_kaggle_notebook_state.md)
The DueCare suite ships as 76 notebooks (76 of 76 validated locally by
`scripts/validate_notebooks.py`, 42 targeted adversarial validators green).
The full inventory is regenerated into
[`docs/current_kaggle_notebook_state.md`](./docs/current_kaggle_notebook_state.md)
after each session.

#### Start here

| ID | Notebook | GPU | Kaggle Link |
|---|---|---|---|
| 000 | Start Here: All Notebooks and Writeup | - | [duecare-000-index](https://www.kaggle.com/code/taylorsamarel/duecare-000-index) |
| 005 | Glossary and Reading Map | - | [duecare-005-glossary](https://www.kaggle.com/code/taylorsamarel/duecare-005-glossary) |
| 010 | 5-Minute Setup and First Safety Evaluation | - | [duecare-010-quickstart](https://www.kaggle.com/code/taylorsamarel/duecare-010-quickstart) |
| 100 | Gemma Exploration (Phase 1 Baseline) | T4 | [duecare-gemma-exploration](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-exploration) |
| 200 | Cross-Domain Proof | - | [duecare-200-cross-domain-proof](https://www.kaggle.com/code/taylorsamarel/duecare-200-cross-domain-proof) |
| 500 | Agent Swarm Deep Dive | - | [duecare-500-agent-swarm-deep-dive](https://www.kaggle.com/code/taylorsamarel/duecare-500-agent-swarm-deep-dive) |
| 610 | Submission Walkthrough | - | [duecare-submission-walkthrough](https://www.kaggle.com/code/taylorsamarel/duecare-submission-walkthrough) |

The remaining notebooks cover the `100`-`600` bands for evaluation,
comparison, adversarial testing, pipeline construction, fine-tuning, and
reporting. The `000` band is now the orientation layer: index, glossary,
and quickstart. See [`docs/notebook_guide.md`](./docs/notebook_guide.md)
for the full 76-notebook ordered table.

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

### Key results (real Kaggle GPU runs)

| Metric | Value | Source |
|---|---|---|
| Stock Gemma 4 E4B mean score | **0.610** | [100 - Gemma Exploration](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-exploration) |
| Stock Gemma 4 E4B pass rate | **20%** | 100 (50 graded prompts) |
| Harmful phrase rate | **0.0%** | Gemma 4 never produced harmful content |
| Refusal rate | **36%** | Clear refusal on exploitation requests |
| With RAG context | **0.59** (+23% over plain) | [260 - RAG Comparison](https://www.kaggle.com/code/taylorsamarel/duecare-260-rag-comparison) |
| With guided prompt | **0.62** (+28% over plain) | [260 - RAG Comparison](https://www.kaggle.com/code/taylorsamarel/duecare-260-rag-comparison) |
| Trafficking prompt corpus | **74,567** | [110 - Prompt Prioritizer](https://www.kaggle.com/code/taylorsamarel/00a-duecare-prompt-prioritizer-data-pipeline) |
| Adversarial generators | **15** | [310 - Prompt Factory](https://www.kaggle.com/code/taylorsamarel/duecare-310-prompt-factory) |
| Evaluation frameworks | **7** | |
| Tests passing | **194** | Across 17 packages |

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
3. **PEP 420 namespace packages.** All 17 packages share the `duecare`
   Python namespace. Install one or all seventeen; imports work identically.
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
# All 194 tests across all 17 packages
python -m pytest packages -v

# Single package
python -m pytest packages/duecare-llm-core -v

# Single module folder (folder-per-module pattern)
python -m pytest packages/duecare-llm-core/src/forge/core/enums -v
```

Latest full run:

```
========================= 194 passed in 42.3s =========================
```

## Demo notebook

`notebooks/010_quickstart.ipynb` is the local mirror of the numbered
quickstart notebook and is the best place to exercise the public
DueCare package surface from a clean install.

`notebooks/610_submission_walkthrough.ipynb` is the local mirror of the
Kaggle submission walkthrough and is the shortest path from install to
report-generation.

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
├── packages/                     # 17 PyPI packages (workspace members)
│   ├── duecare-llm-core/         # contracts, schemas, observability
│   ├── duecare-llm-models/       # 8 model adapters
│   ├── duecare-llm-domains/      # pluggable domain packs
│   ├── duecare-llm-tasks/        # 9 capability tests
│   ├── duecare-llm-agents/       # 12-agent swarm
│   ├── duecare-llm-workflows/    # YAML DAG runner
│   ├── duecare-llm-publishing/   # HF Hub + Kaggle uploaders
│   ├── duecare-llm-engine/       # heuristic + GREP + RAG + tools pipeline
│   ├── duecare-llm-server/       # FastAPI app for the live demo
│   ├── duecare-llm-evidence-db/  # redacted evidence + audit trail
│   ├── duecare-llm-benchmark/    # smoke_25 + score_row + aggregate
│   ├── duecare-llm-training/     # Unsloth SFT + DPO scripts
│   ├── duecare-llm-research-tools/ # Playwright scrapers + extractors
│   ├── duecare-llm-nl2sql/       # NL → SQL for evidence DB
│   ├── duecare-llm-chat/         # minimal Gemma 4 chat playground
│   ├── duecare-llm-cli/          # the `duecare` CLI
│   └── duecare-llm/              # meta package (pulls in all 16 above)
├── kaggle/                       # Kaggle deliverables (per-notebook bundles)
│   ├── live-demo/                # Notebook 1: kernel.py + wheels/*.whl
│   ├── bench-and-tune/           # Notebook 2: kernel.py (TBD) + wheels/*.whl
│   ├── gemma-chat/               # Notebook 3: kernel.py + wheels/*.whl
│   ├── shared-datasets/          # cross-notebook: trafficking-prompts, eval-results
│   ├── kernels/                  # the 76-notebook research pipeline (separate)
│   └── models/                   # Kaggle Models artifacts
├── configs/duecare/              # YAML configuration (models, workflows, domains)
├── docs/                         # architecture, component docs, writeup, video script
│   └── components/               # per-package component docs
├── notebooks/                    # canonical .ipynb sources for the 76-notebook pipeline
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
  url={https://github.com/TaylorAmarelTech/gemma4_comp},
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
