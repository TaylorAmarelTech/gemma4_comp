# Duecare — Gemma 4-powered safety infrastructure for migrant-worker protection

> 🌐 **Public hub:** [duecare-ai.com](https://duecare-ai.com) ·
> 📓 **Kaggle submission:** [kaggle.com/code/taylorsamarel/duecare-harness-chat](https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat) ·
> 📦 **Source:** this repo (MIT)
>
> **Duecare is Gemma 4-powered safety infrastructure for migrant-worker
> protection.** It does three things: **prevents exploitation before it
> spreads** through platform and organization moderation; **assists victims
> and at-risk workers** through NGO/government intake and the worker mobile
> app; and **helps stakeholders understand what is happening and why**
> through research notebooks, knowledge packs, trend signals, and shared
> analysis. The public product is organized into five setup lanes:
> **Platform safety**, **NGO & regulator**, **Individual worker / mobile**,
> **Researcher**, and **Developer / integration partner**.
> **Core platform pieces:** Gemma 4 Model Layer · Safety Guidance Layer ·
> Knowledge Packs · Quality Testing Framework · Central Knowledge Server ·
> Local Anonymization · Information Submission · Public Information Research ·
> Stakeholder Engagement · Newsletter and Alerts · Fine-Tuning · Channel and
> Deployment Package. **Live core** for the Kaggle submission is Gemma 4 +
> Safety Guidance + Knowledge Packs + Quality Testing. **Prototype:**
> Fine-Tuning (`kaggle/A-07-bench-and-tune/`). **Roadmap:** Central server
> modules, research monitor, stakeholder engagement, newsletter, and channel
> deployment. **Sibling repo (live):** Mobile (Duecare Journey
> v0.9.0). Full canonical definition:
> [`docs/product_definition.md`](docs/product_definition.md). Plain-language
> use-case and component wording:
> [`docs/canonical_use_cases_and_components.md`](docs/canonical_use_cases_and_components.md).
>
> Named for Cal. Civ. Code § 1714(a) — the duty of care standard that
> a California jury applied to find Meta and Google negligent for
> defective platform design in March 2026. Duecare applies the same
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
> **74,567 repo-config prompts. 6 weighted rubrics. 66 evaluation criteria.
> Reproducible CLI and notebook surfaces. On your laptop or in your pocket.**
>
> **Built for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon).**
> Gemma 4 is DueCare's first published benchmark.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-194%20passing-brightgreen.svg)](#tests)
[![Packages](https://img.shields.io/badge/packages-17-blue.svg)](#packages)

> ### 🚀 Submission state (Gemma 4 Good Hackathon, due 2026-05-18)
>
> **2 core + 11 appendix = 13 Kaggle notebooks.** Judges land on
> the unified omni playground, then proceed to the focused live
> demo. The 11 appendix notebooks add depth-of-engineering signal
> without competing for the first 5 minutes.
>
> **Core (judges evaluate first — in this order):**
>
> 1. [`duecare-harness-chat`](https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat) ★ **The omni playground.** All 6 harness toggles (Persona / GREP 161 rules / RAG 46 docs + 46-edge citation graph / Imports / Tools 5 lookups / Online live web search with deep-fetch) + 4 grade modes (Universal / Expert / **Deep LLM-as-judge** / Combined) + **9-variant Gemma 4 model selector** (E2B / E4B / 26B-A4B / 31B / 2 jailbroken / 3 cloud BYOK) + A/B Compare tab + retrieval-config panel + retrieval path-trace card + **interactive RAG graph viewer** (in-modal + standalone full-screen at `/static/rag-graph.html`). One configurable interface for the whole capability surface.
> 2. [`duecare-live-demo`](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) — focused, scripted live URL. Polished classification + knowledge-building product with the +56.5pp lift demonstration.
>
> **Appendix (11):**
>
> - A1. [`duecare-chat-playground`](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-chat-playground) — raw Gemma 4 chat baseline (no harness)
> - A2. [`duecare-chat-playground-with-grep-rag-tools`](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools) — original 4-toggle subset
> - A3. `duecare-content-classification-playground` — hands-on classifier sandbox (4 schemas)
> - A4. `duecare-content-knowledge-builder-playground` — hands-on KB builder + JSON export
> - A5. [`duecare-gemma-content-classification-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation) — NGO dashboard with risk vectors + queue
> - A6. `duecare-prompt-generation` — Gemma 4 generates new evaluation prompts + 5 graded responses each
> - A7. `duecare-bench-and-tune` — Unsloth SFT → DPO → GGUF Q8_0 → HF Hub push
> - A8. `duecare-research-graphs` — 6 interactive Plotly charts (CPU-only)
> - A9. `duecare-chat-playground-with-agentic-research` — Playwright real-browser BYOK agentic web search (the deeper version of Online layer)
> - A10. `duecare-chat-playground-jailbroken-models` — loads abliterated/cracked Gemma 4 variants; proves harness still works even when refusals are ablated
> - A11. `duecare-grading-evaluation` — **the lift regenerator.** Runs N prompts × 2 conditions, grades both, emits MD+JSON with provenance tuple `(model, git_sha, dataset_version)`. The +56.5pp number, regenerated live from a git SHA.
>
> **Judges start here:** [`docs/peer_review_5min_test_plan.md`](./docs/peer_review_5min_test_plan.md) (one-page click-by-click guide).
> Or: [`docs/FOR_PEER_REVIEW.md`](./docs/FOR_PEER_REVIEW.md) (full verification roster).
> **Writeup (≤1500 words):** [`docs/writeup_draft.md`](./docs/writeup_draft.md).
> **Video script (~2:50):** [`docs/video_script.md`](./docs/video_script.md).
> **Audit / report card:** [`docs/REPORT_CARD.md`](./docs/REPORT_CARD.md).
> **Harness lift report:** [`docs/harness_lift_report.md`](./docs/harness_lift_report.md) — quantifies how RAG/GREP/Tools change rubric scores (mean **+56.5 pp** on the cross-cutting `legal_citation_quality` rubric, 207/207 prompts).
> **Corpus coverage:** [`docs/corpus_coverage.md`](./docs/corpus_coverage.md) — 2D coverage matrices across category × sector × corridor × ILO indicator.
> **Stretch — Android (LiteRT track):** [`docs/android_app_architecture.md`](./docs/android_app_architecture.md) — Duecare Journey, the on-device companion. v1 architecture published here; **APK skeleton + GitHub Actions APK build pipeline live in the sibling repo `duecare-journey-android/`** (separated so Android tooling doesn't collide with the Python research workflow). v1 MVP build lands week of 2026-05-19.
> **Provenance:** [`RESULTS.md`](./RESULTS.md) — every metric pinned to `(git_sha, dataset_version, model_revision)`.
>
> **Three headline benefits shown in the demo:**
>
> - **Prevent exploitation before it spreads** — platform and marketplace moderation with explained risk envelopes. Setup: [`docs/deployment_enterprise.md`](./docs/deployment_enterprise.md).
> - **Assist victims and at-risk workers** — NGO/regulator intake plus worker-facing mobile workflows. Setup: [`docs/scenarios/ngo-office-deployment.md`](./docs/scenarios/ngo-office-deployment.md) and [`docs/scenarios/worker-self-help.md`](./docs/scenarios/worker-self-help.md).
> - **Understand what is happening and why** — reproducible Kaggle notebooks, knowledge packs, trend signals, and provenance. Start with [`docs/FOR_KAGGLE_JUDGES.md`](./docs/FOR_KAGGLE_JUDGES.md).

---

## Start here by role

📋 **[Setup Requirements](docs/SETUP_REQUIREMENTS.md)** — GPU, environment setup, and dependencies for all platforms

| Lane | You are | Read first |
|---|---|---|
| 01 Platform safety | A trust & safety team or recruitment marketplace integrating moderation | [`docs/scenarios/enterprise_pilot.md`](./docs/scenarios/enterprise_pilot.md) · [`docs/scenarios/recruiter-self-audit.md`](./docs/scenarios/recruiter-self-audit.md) · [`docs/deployment_enterprise.md`](./docs/deployment_enterprise.md) |
| 02 NGO & regulator | An NGO caseworker, legal aid organization, regulator, or embassy desk | [`docs/scenarios/ngo-office-deployment.md`](./docs/scenarios/ngo-office-deployment.md) · [`examples/deployment/ngo-office-edge/README.md`](./examples/deployment/ngo-office-edge/README.md) |
| 03 Individual worker / mobile | A migrant worker, peer supporter, or community helper using the Android app | [`docs/scenarios/worker-self-help.md`](./docs/scenarios/worker-self-help.md) · [`docs/architecture/duecare_mobile.md`](./docs/architecture/duecare_mobile.md) · [`docs/android_app_architecture.md`](./docs/android_app_architecture.md) |
| 04 Researcher | An academic, journalist, policy analyst, or Kaggle judge | [`docs/FOR_KAGGLE_JUDGES.md`](./docs/FOR_KAGGLE_JUDGES.md) · [`docs/FOR_PEER_REVIEW.md`](./docs/FOR_PEER_REVIEW.md) · [`docs/scenarios/researcher-analysis.md`](./docs/scenarios/researcher-analysis.md) · [`kaggle/01-duecare-exploration-workbench/README.md`](./kaggle/01-duecare-exploration-workbench/README.md) |
| 05 Developer / integration partner | A team embedding DueCare into your own product, bot, dashboard, or internal workflow | [`docs/install.md`](./docs/install.md) · [`docs/embedding_guide.md`](./docs/embedding_guide.md) · [`packages/duecare-llm/README.md`](./packages/duecare-llm/README.md) · [`apps/duecare-ai.com/app/templates/client-connect.html`](./apps/duecare-ai.com/app/templates/client-connect.html) |

## Why this exists

Frontier LLMs fail predictably on **migrant-worker trafficking**
scenarios — documented in the author's prior
[OpenAI gpt-oss-20b Red-Teaming Challenge writeup](https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/llm-complicity-in-modern-slavery-from-native-blind).
The people and institutions closest to the harm need practical tools:
platforms need earlier moderation signals, frontline NGOs and regulators
need faster case intake and evidence organization, workers need guidance
they control, and researchers need reproducible ways to explain patterns.

Duecare is that shared harness. Because it is built as a **universal**
safety and evidence framework, the same architecture can also evaluate
tax evasion, money laundering, medical misinformation, and any other
safety domain that can describe itself with a taxonomy, evidence base,
and rubric.

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

- 🌐 **[Browse the docs site](https://tayloramareltech.github.io/gemma4_comp/)**
  — full searchable site, no install, persistent. Diagrams render
  via Mermaid; nav by persona / topology / surface.
- [**Try in 2 minutes**](./docs/try_in_2_minutes.md) — fastest path
  per persona, no install required for most options
- [**Ecosystem overview**](./docs/ecosystem_overview.md) — how the
  3 outcomes and 5 setup lanes compose around one harness, with
  Mermaid diagrams
- [**Maria's case end-to-end**](./docs/marias_case_end_to_end.md)
  — composite case traced through every layer of the ecosystem
  (writeup + video + pitch material)
- [**Cross-NGO trends federation**](./docs/cross_ngo_trends_federation.md)
  — privacy-preserving aggregation protocol for sharing patterns
  across NGOs without sharing PII
- [**Comparison vs alternatives**](./docs/comparison_to_alternatives.md)
  — when Duecare fits vs when Hive / Sift / Azure / OpenAI / Llama
  Guard fit better
- [**Press kit**](./docs/press_kit.md) — one-pager + facts + quotes
  for journalists, NGO comms, academics
- [**Educator resources**](./docs/educator_resources.md) — drop-in
  lesson plans for AI-ethics / social-work / migration-studies courses
- [**First-deployer feedback template**](./docs/first_deployer_feedback.md)
  — if you tried it in your real environment, your input shapes v0.10

### Run on Kaggle (GPU)

Open the notebook, set Accelerator to **GPU T4 x2**, and run:
- [100 — Gemma Exploration](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-exploration) — real Gemma inference + scoring

### Run the validated local CLI bootstrap

The clean install path currently smoke-tested from local wheels is:

```bash
pip install duecare-llm-cli
duecare init
duecare demo-stage
duecare serve --port 8080
```

### Run a workflow with the meta package

The `duecare-llm` meta-package exposes the workflow-oriented CLI. Its
lightweight discovery path and an end-to-end `rapid_probe` workflow were
smoke-tested from local wheels against a local OpenAI-compatible backend.
Real Gemma/Ollama/API runs still require the selected target-model backend
to be installed and configured.

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
The DueCare suite ships as 77 notebooks (77 of 77 validated locally by
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
for the full 77-notebook ordered table.

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

| Pack | Seed prompts in repo config | Evidence items | Categories | Taxonomy dimensions |
|---|---|---|---|---|
| `trafficking` | 74,567 | 10 | 5 | sector, corridor, ILO indicator, attack category, difficulty |
| `tax_evasion` | 4 | 4 | 4 | scheme type, jurisdiction, FATF indicator, sophistication |
| `financial_crime` | 3 | 3 | 4 | laundering stage, typology, FATF indicator, jurisdiction |

The full trafficking prompt corpus lives in
`configs/duecare/domains/trafficking/seed_prompts.jsonl`; the PyPI
domain wheel bundles a lightweight sample so installs stay small.

All three use the same `FileDomainPack` implementation. All three are
discoverable through the meta-package CLI (`duecare domains list`) and
are hot-swappable in the workflow runner once a target-model backend is
installed.

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

## Demo notebooks

The active notebook sources live under `kaggle/`. For the 77-notebook
research pipeline, use the per-kernel bundles in `kaggle/kernels/*/`.
For the final hackathon submission path, use the 2 core + 11 appendix
folders listed in `kaggle/_INDEX.md`.

The old `legacy_notebooks/` and `skunkworks/` root folders have been
archived under `_archive/legacy-research-2026-05-09/` and are not part
of the default review, validation, or submission workflow.

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
[`.env.example`](./.env.example).

## Repository layout

> See [`docs/REPO_LAYOUT.md`](./docs/REPO_LAYOUT.md) for a one-screen
> map of every top-level directory — including supporting
> infrastructure (`infra/`, `deployment/`, `configs/`), data folders,
> archived snapshots, and hidden dev-only paths. The sketch below
> highlights the most important entries.

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
│   ├── 01-duecare-exploration-workbench/  # CORE #01: omni playground (script kernel)
│   ├── 02-live-demo/             # CORE #02: focused live URL
│   ├── A-01-chat-playground/     # appendix: stock Gemma 4 baseline (no harness)
│   ├── A-02-chat-playground-with-grep-rag-tools/  # appendix: 4-toggle subset
│   ├── A-03-content-classification-playground/    # appendix: classifier sandbox
│   ├── A-04-content-knowledge-builder-playground/ # appendix: KB builder
│   ├── A-05-gemma-content-classification-evaluation/  # appendix: NGO dashboard
│   ├── A-06-prompt-generation/   # appendix: Gemma generates eval prompts
│   ├── A-07-bench-and-tune/      # appendix: Unsloth SFT/DPO/GGUF/HF Hub
│   ├── A-08-research-graphs/     # appendix: 6 Plotly charts
│   ├── A-09-chat-playground-with-agentic-research/  # appendix: Playwright BYOK
│   ├── A-10-chat-playground-jailbroken-models/      # appendix: abliterated proof
│   ├── A-11-grading-evaluation/  # appendix: lift regenerator
│   ├── shared-datasets/          # cross-notebook: trafficking-prompts, eval-results
│   ├── kernels/                  # the 77-notebook research pipeline (separate)
│   └── models/                   # Kaggle Models artifacts
├── configs/duecare/              # YAML configuration (models, workflows, domains)
├── docs/                         # architecture, component docs, writeup, video script
│   └── components/               # per-package component docs
├── _archive/                     # archived legacy notebooks/skunkworks + superseded snapshots
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

## Third Party Attribution

This project builds upon excellent open source software. Key dependencies include:

- **FastAPI** (MIT) - Web framework for the demo application
- **Pydantic** (MIT) - Data validation and settings management
- **Transformers** (Apache 2.0) - Hugging Face model adapters
- **Unsloth** (Apache 2.0) - Fine-tuning framework
- **PyTorch** (BSD-3-Clause) - Deep learning framework
- **Uvicorn** (BSD-3-Clause) - ASGI server
- **Jinja2** (BSD-3-Clause) - Template engine
- **Requests** (Apache 2.0) - HTTP library
- **Gemma** (Custom License) - Google's language model family

For complete licensing information, see [`THIRD_PARTY_LICENSES.md`](./THIRD_PARTY_LICENSES.md).

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
