# DueCare: A Gemma 4 Safety Ecosystem for Migrant-Worker Protection

> **Main server website / public hub:** [duecare-ai.com](https://duecare-ai.com) |
> **GitHub source repo:** [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp) |
> **GitHub Pages docs:** [tayloramareltech.github.io/gemma4_comp](https://tayloramareltech.github.io/gemma4_comp/) |
> **DueCare App on Kaggle:** [kaggle.com/code/taylorsamarel/duecare-app](https://www.kaggle.com/code/taylorsamarel/duecare-app) |
> **Benchmark collection (Kaggle):** [Start here](https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here) &mdash; the index notebook links reproduce / breakdowns / statistical-robustness / judge notebooks + the [grades](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades) & [leaderboard](https://www.kaggle.com/datasets/taylorsamarel/duecare-cross-model-harness-leaderboard) datasets |
> **Fine-tuning &amp; Evaluation:** [Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation) + [proof training dataset](https://www.kaggle.com/datasets/taylorsamarel/duecare-proof-finetuning-data) |
> **Android APK:** [github.com/TaylorAmarelTech/duecare-journey-android/releases](https://github.com/TaylorAmarelTech/duecare-journey-android/releases) |
> **License:** MIT
>
> **Headline result (2026-05-18 smoke matrix):** Stock Gemma 4 2B **29.5%** ·
> Stock + chat-offline harness **35.6%** (+6.1pp) · Fine-tuned **26.4%** ·
> Fine-tuned + harness **41.2%** (+14.8pp over fine-tuning alone, +11.7pp over stock).
> Separately, an independent gpt-oss:120b judge over 911 prompts scored the
> harness at **+1.73/10** mean paired lift on gemma4:31b (95% CI [+1.57, +1.89],
> 73.3% win rate). The harness supplies the facts, citations, tools,
> data-minimization checks, and forced-labor indicators that fine-tuning alone
> cannot. These are dated benchmark results, not field-deployment,
> production-traffic, or weeks-long local Gemma reliability claims.
>
> **Current training-data and training status (2026-07-15):** five
> manifest-bound Kaggle learning datasets are public. The
> [multiperspective corpus](https://www.kaggle.com/datasets/taylorsamarel/duecare-multiperspective-finetuning-corpus)
> contains 25,600 supervised fine-tuning training rows, 25,600 preference
> training rows, and 2,048 rows in each held-out split. The
> [measured-response corpus](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus)
> contains 791 accepted supervised fine-tuning rows, 791 preference pairs,
> 1,582 reward labels, and raw-text-free inventory and quarantine lanes. The
> [207,680-row grounded-remix curriculum](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-review-curriculum-200k)
> has 207,680 supervised rows and 207,680 preference pairs while retaining
> parent hashes and lineage-family splits. The
> [Gemma 4 adapter learning study](https://www.kaggle.com/datasets/taylorsamarel/duecare-gemma4-adapter-learning-study)
> publishes two real graphics-processing-unit runs, relative Low-Rank
> Adaptation weights, learning curves, before/after generations, a four-arm
> harness comparison, and frozen frontier-judge audits. On six recorded
> high-severity harmful-request pairs, the same frozen judge preferred the
> real DueCare harness response in all six pairs and both presentation orders:
> mean harness delta +9.67/10, pair-bootstrap 95% interval [+9.0, +10.0], and
> zero mean order gap. This is evidence of improved harmful-request handling on
> that recorded benchmark lane, not improved victim identification or field
> detection. The public
> [evidence-to-triage system showcase](https://www.kaggle.com/code/taylorsamarel/duecare-training-publication-toolchain)
> puts the corpus, training, harness, examples, judge results, and claim ladder
> together. Public notebooks
> verify, load, explain, visualize, and run bounded diagnostics on the
> releases. Downloaded Kaggle outputs prove
> 11 charts plus 10 review tables for the response explorer, 15 charts plus 7
> review tables for the multiperspective explorer, and additional loading,
> split-isolation, and small-classifier reports. Supervised fine-tuning means
> training from inputs paired with reviewed desired answers; preference
> training learns from preferred and nonpreferred answers. This is a
> professional Kaggle / Gemma 4 hackathon learning artifact. The stronger
> Gemma 4 E2B run completed 60 optimizer steps and produced a relative adapter;
> its structural holdout score changed by +0.15 on eight grounded-remix rows.
> A separate frozen 32-verdict frontier-judge audit of that same adapter did
> not support a positive training-lift claim, so the adapter is published as a
> bounded learning artifact rather than an improved model; the +9.67/10 result
> above measures the deterministic harness, not the trained weights.
> A separate central-processing-unit fallback initialized two byte-level
> transformers from random weights, trained both on lineage-separated grounded
> remixes, saved full reloadable parameter archives, and reduced held-out
> next-byte loss from 5.5479 to 5.1164 and from 5.5990 to 4.7361. That two-step
> mechanism run is published in the
> [Grounded Byte Model Learning Study](https://www.kaggle.com/datasets/taylorsamarel/duecare-grounded-byte-model-learning-study)
> and is not a useful-language or domain-lift claim.
> A checksummed system-evidence receipt also reproduces a **+1.73/10**
> model-judge change over 911 paired synthetic/composite trafficking-safety
> prompts, a **+0.18/10** deterministic cross-check over 998 pairs, and a
> **+4.39/10** model-judge change over 140 declared adversarial transforms.
> The larger live panel read (2026-07-16 snapshot) now covers **7,953 paired
> real registry prompts** for `gemma4:31b` under a three-judge panel:
> baseline 48.4 → harnessed 89.1 on the 0-100 component rubric (**+40.7**,
> seeded bootstrap 95% interval [+40.2, +41.2], win rate 99.8%, and the lift
> holds within each judge independently). Regenerate the current read with
> `python scripts/analyze_full_results.py` →
> [`docs/research/full_results.md`](docs/research/full_results.md).
> These are benchmark response-quality results, not field-detection metrics.
> Across the multi-model board every one of the seven flagship/frontier models
> graded so far gains (raw lift roughly +16 to +43 on the 0-100 rubric), and a
> ceiling-adjusted **normalized-gain** column now on the
> [public leaderboard](https://duecare-ai.com/benchmark) shows the largest raw
> lifts mostly reflect the most baseline headroom rather than the strongest
> harness effect (`gpt-oss:120b` leads on raw lift but ranks last on normalized
> gain). The per-model, per-dimension, honest helps-and-hurts deep-dive is the
> [reproduce-harness-lift notebook](https://www.kaggle.com/code/taylorsamarel/duecare-reproduce-harness-lift);
> the exhaustive per-dimension sweep grades in seed-shuffled order so any interim
> read is an unbiased random sample (`scripts/perdim_interim_goals.py`).
> **No merged weights, independently demonstrated victim-identification or
> real-world field-detection lift,
> legal-quality result, production-ready model, or field-effectiveness claim
> is made.**
> See [Training and fine-tuning](docs/training_and_finetuning.md).
>
> **DueCare is Gemma 4-powered safety infrastructure for migrant-worker
> protection.** It does three things: **prevents exploitation before it
> spreads** through platform and organization moderation; **assists victims
> and at-risk workers** through NGO/government case analysis and the worker mobile
> app; and **helps stakeholders understand what is happening and why**
> through research notebooks, knowledge packs, trend signals, and shared
> analysis. The public product is organized into six setup lanes:
> **Platform safety**, **NGO & regulator**, **Individual worker / mobile**,
> **Researcher**, **Anonymized knowledge sharing**, and
> **Developer / integration partner**.
> **Core platform pieces:** Gemma 4 Model Layer, Safety Guidance Layer,
> Knowledge Packs, Quality Testing Framework, Central Knowledge Server,
> Local Anonymization, Information Submission, Public Information Research,
> Stakeholder Engagement, Newsletter and Alerts, Fine-Tuning, Channel and
> Deployment Package. **Live core** for the Kaggle submission is Gemma 4 +
> Safety Guidance + Knowledge Packs + Bulk File Review + Quality Testing.
> **Proof pipeline:**
> Fine-tuning and benchmarking (`kaggle/A-00-omni-experiment-workbench/`). **Roadmap:** Central server
> modules, research monitor, stakeholder engagement, newsletter, and channel
> deployment. **Sibling repo (live):** Mobile (DueCare Journey
> v0.9.0). Full canonical definition:
> [`docs/product_definition.md`](docs/product_definition.md). Plain-language
> use-case and component wording:
> [`docs/canonical_use_cases_and_components.md`](docs/canonical_use_cases_and_components.md).
>
> Named for Cal. Civ. Code section 1714(a), the duty of care standard that
> a California jury applied to find Meta and Google negligent for
> defective platform design in March 2026. DueCare applies the same
> standard to LLM safety: does the model exercise *due care* when
> responding to prompts about trafficking, exploitation, and financial crime?
>
> **North star: inform AND document.** A migrant worker can follow
> the chatbot's advice (don't pay the illegal fee) or pay anyway
> under their corridor's real constraints, with the journal
> capturing every receipt + statute citation + recipient so the
> same harness ecosystem pre-stages the refund claim. Harm reduction, not
> paternalism. Fully offline.
>
> **Large trafficking prompt corpus, weighted rubrics, hundreds of GREP
> detection rules, hundreds of RAG knowledge documents, complaint and
> narrative templates, review personas, fee-camouflage labels, corridor
> fee-cap entries, NGO contact bundles, and ILO convention coverage.
> A separate propose-only entity-intelligence layer verifies recruiters and
> employers against 34 official government registries, backed by a 1,111-source
> catalogue and 532 migrant-support organisations.
> Reproducible CLI and notebook surfaces. On your laptop or in your
> pocket.** Re-run current counts via `python scripts/verify_knowledge_surfaces.py`
> (pure stdlib, no pip) before copying an exact figure into public copy.
>
> **Built for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon).**
> Gemma 4 is DueCare's first published benchmark.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Pytest collection](https://img.shields.io/badge/pytest%20collection-checked-blue.svg)](#tests)
[![Packages](https://img.shields.io/badge/packages-17-blue.svg)](#packages)

## Try DueCare on Kaggle

Two demo Kaggle script kernels are the fastest way to try DueCare. Each one is a single `kernel.py` file: copy it into a fresh Kaggle Notebook, set **Accelerator: GPU T4 x2** + **Internet: On**, click **+ Add Input → Models → `google/gemma-4`**, then **Run All**. After install, package verification, model setup, and tunnel startup, the kernel prints a public `https://*.trycloudflare.com` URL. Timing varies by Kaggle worker, selected Gemma 4 variant, package install path, model cache state, and Cloudflare quick-tunnel availability. A-00 is the active proof kernel for longer fine-tuning, evaluation, and report-bundle runs.

| | Kernel | What you see when it starts |
|---|---|---|
| 🟢 | **DueCare App** &nbsp;·&nbsp; [Kaggle](https://www.kaggle.com/code/taylorsamarel/duecare-app) &nbsp;·&nbsp; [`kaggle/01-duecare-exploration-workbench/kernel.py`](./kaggle/01-duecare-exploration-workbench/kernel.py) | The broad reviewer workbench. Open `/` for the audience showcase, then click into chat / Bulk File Review / harness comparison / grading. |
| 🎬 | **DueCare Live Demo** &nbsp;·&nbsp; [Kaggle](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) &nbsp;·&nbsp; [`kaggle/02-live-demo/kernel.py`](./kaggle/02-live-demo/kernel.py) | Focused demo + the recording-grade pitch deck. Open `/start` → click **Project slides** → 23-slide deck loads (works without a model). |

Optional benchmark surfaces:

- [`kaggle/03-universal-llm-benchmark`](./kaggle/03-universal-llm-benchmark/) benchmarks arbitrary OpenAI-compatible, Anthropic Messages, or raw JSON endpoints against DueCare prompts and rubric cues, with Claude Opus judging only when an Anthropic key is configured. Fixture/self-test paths do not require paid model calls.
- [`kaggle/04-kaggle-community-benchmark`](./kaggle/04-kaggle-community-benchmark/) defines DueCare rows as `kaggle_benchmarks` tasks so runs can use Kaggle's model proxy/quota and produce Community Benchmark artifacts. The current task combines corridor, fee, policy, and composite vulnerability scenarios with DueCare's universal rubric, including hard-veto dimensions such as `harm_enablement_check` and `no_operational_optimization`. The notebook pip-installs `duecare-llm-chat` from a pinned commit so the rubric is synced to a reproducible source snapshot. See [`COVERAGE.md`](./kaggle/04-kaggle-community-benchmark/COVERAGE.md) for the current row and dimension breakdown.

Neither optional benchmark is required for the primary recording path.

Heuristic-only mode (no model attached) still serves `/start`, `/slides`, deterministic GREP / RAG / tools, and the cached worker-question slot — the model only matters for the live `/chat` endpoint and the optional Gemma edge pass on Bulk File Review.

**Verify locally:**

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp.git
cd gemma4_comp
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e packages/duecare-llm-server
python -c "from duecare.server import create_app; from duecare.server.state import ServerState; import tempfile, pathlib, uvicorn; tmp=tempfile.mkdtemp(); pathlib.Path(tmp,'out').mkdir(parents=True,exist_ok=True); s=ServerState(db_path=str(pathlib.Path(tmp)/'t.duckdb'),pipeline_output_dir=str(pathlib.Path(tmp)/'out')); uvicorn.run(create_app(s), host='127.0.0.1', port=8771)"
# Open http://127.0.0.1:8771/start in a browser → click Project slides → 23-slide deck.
# Open http://127.0.0.1:8771/slides/setup → Generate → Save for slides → the worker-question slide is now cached.
```

> ### Submitted to the Gemma 4 Good Hackathon (2026-05-18)
>
> **Active Kaggle path: 01 + 02 + A-00.** Judges land on
> the exploration workbench, then proceed to the focused live
> demo. A-00 remains the active proof and training/evaluation path.
> The former video-pitch and A-01 through A-24 appendix notebooks are
> archived under `kaggle/_archive/notebooks` to keep the submission
> path testable.
>
> **Core (judges evaluate first, in this order):**
>
> 1. **DueCare App** — [`duecare-app`](https://www.kaggle.com/code/taylorsamarel/duecare-app) — the broad workbench. Chat, Harness Comparison, Bulk File Review, Knowledge Extraction, Search, Anonymization and Sharing, Sync, Status, UI Audit, live layer catalogs, global model selector, A/B comparison, retrieval trace, grading, local imports, and RAG graph views.
> 2. **DueCare Live Demo** — [`duecare-live-demo`](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) — focused live product demo with real Gemma 4 inference, the recording-grade pitch deck at `/start` and `/slides`, and a curated safety-harness scenario.
>
> **Proof and optional benchmark surfaces:**
>
> - **DueCare Fine-tuning and Evaluation** — [`duecare-fine-tuning-and-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation) ([active source](./kaggle/A-00-omni-experiment-workbench/)) is the proof path for baseline vs harness vs fine-tuned vs fine-tuned-plus-harness exports, rule and LLM grading, manifest-bound SFT/DPO train/validation/test artifacts, resumable LoRA smoke runs, local research graphs, and HTML/PDF reports. The source attaches the public proof dataset [`duecare-proof-finetuning-data`](https://www.kaggle.com/datasets/taylorsamarel/duecare-proof-finetuning-data). The current source accepts final answers, citations, visible rationales, and deliberately authored reasoning structures; it rejects hidden chain-of-thought and refuses training until the dataset and held-out-lineage gates are clean.
> - **DueCare Universal LLM Benchmark** — [`kaggle/03-universal-llm-benchmark`](./kaggle/03-universal-llm-benchmark/) is optional: it tests arbitrary API endpoints against DueCare prompt/rubric/evidence cues and can use Claude Opus as an external judge.
> - **DueCare Kaggle Community Benchmark** — [`kaggle/04-kaggle-community-benchmark`](./kaggle/04-kaggle-community-benchmark/) is optional: it converts DueCare rows into `kaggle_benchmarks` tasks so Kaggle-hosted model quota and leaderboard artifacts can be used.
> - Archived A-01 through A-24 plus the former video-pitch kernel remain available as reference material, but they are not part of the active validation or recording path.
>
> **Judges start here:** [`docs/FOR_KAGGLE_JUDGES.md`](./docs/FOR_KAGGLE_JUDGES.md) (hackathon-specific quick path).
> Or: [`docs/FOR_PEER_REVIEW.md`](./docs/FOR_PEER_REVIEW.md) (full verification roster).
> **Writeup (1500 words max):** [`docs/writeup_draft.md`](./docs/writeup_draft.md).
> **Copy-ready networked knowledge-sharing Kaggle post:** [`docs/kaggle_post_networked_knowledge_sharing.md`](./docs/kaggle_post_networked_knowledge_sharing.md).
> **Video script (~2:50):** [`docs/video_script.md`](./docs/video_script.md).
> **Audit / readiness:** [`docs/readiness_dashboard.md`](./docs/readiness_dashboard.md).
> **Harness lift report:** [`docs/harness_lift_report.md`](./docs/harness_lift_report.md) - quantifies how the safety layers change rubric scores.
> **Corpus coverage:** [`docs/corpus_coverage.md`](./docs/corpus_coverage.md) - coverage matrices across category, sector, corridor, and ILO indicator.
> **Stretch Android path:** [`docs/android_app_architecture.md`](./docs/android_app_architecture.md) - DueCare Journey, the on-device companion.
> **Provenance:** [`RESULTS.md`](./RESULTS.md) - every metric pinned to `(git_sha, dataset_version, model_revision)`.
>
> **Three headline benefits shown in the demo:**
>
> - **Prevent exploitation before it spreads** - platform and marketplace moderation with explained risk envelopes. Setup: [`docs/deployment_enterprise.md`](./docs/deployment_enterprise.md).
> - **Assist victims and at-risk workers** - NGO/regulator case analysis plus worker-facing mobile workflows. Setup: [`docs/scenarios/ngo-office-deployment.md`](./docs/scenarios/ngo-office-deployment.md) and [`docs/scenarios/worker-self-help.md`](./docs/scenarios/worker-self-help.md).
> - **Understand what is happening and why** - reproducible Kaggle notebooks, knowledge packs, trend signals, and provenance. Start with [`docs/FOR_PEER_REVIEW.md`](./docs/FOR_PEER_REVIEW.md) (canonical reviewer entry) or [`docs/FOR_KAGGLE_JUDGES.md`](./docs/FOR_KAGGLE_JUDGES.md) for the hackathon-specific quick path.

---


## Architecture: multi-harness pattern

DueCare is built around **six self-describing harness modules** on the kernel
side and **five** on the hub side. Each owns one safety task:

| Side | Harness | Responsibility |
|---|---|---|
| Kernel | `chat` | full multimodal orchestrator (persona / grep / rag / tools / online) |
| Kernel | `process` | bulk case-bundle analysis + graph-chat |
| Kernel | `extraction` | drafts typed KnowledgeObject envelopes from raw text |
| Kernel | `anonymization` | PII gate (regex-only by design; never sees raw PII through Gemma) |
| Kernel | `import_corpus` | user-attached evidence CRUD |
| Kernel | `search` | server + client web search via SearXNG or legacy backends |
| Hub | `curator` | human-in-the-loop vetting queue |
| Hub | `sentinel` | scheduled web harvest of new laws / trends / NGO advisories |
| Hub | `submit` | knowledge-intake gateway from kernels |
| Hub | `packs` | public pack registry |
| Hub | `pii_anonymize` | server-side defensive PII scan |

Each harness self-describes via uniform exports: `name`, `applied_layers`,
`consumes`, `emits`, `capabilities`, `register_routes(app)`, plus optional
`tools.py`, `knowledge.py`, `evaluation.py`, `prompts.py`.

The harness boundary is also the **per-task candidate-data export boundary**.
Gemma-bearing handlers can emit one JSONL row per call under
`/kaggle/working/training/`, but those rows are not automatically ready for a
trainer. The A-00 handoff and `duecare.chat.training_contract` must attach
source references, hashes, licensing/provenance, reasoning-policy labels, and
lineage-isolated splits; a clean quality audit and both held-out prompt-hash and
lineage-ID checks are required before Unsloth ingestion.

### Research data acquisition layer (entity intelligence)

Alongside the harnesses runs a propose-only **entity-intelligence pipeline** that
verifies recruiters, employers, and the companies behind them against **34 official
government registries** — 12 offline-tested connectors (GLEIF corporate identity +
ownership, OpenOwnership beneficial ownership, OpenSanctions, DOJ prosecutions, DOL
labour enforcement, domain OSINT, splink LEI linkage + cross-registry clustering)
feeding a **1,111-source** licensed-entity catalogue and **532** migrant-support
organisations. Everything stages to gitignored `reports/` for curator review; it is
separate from the live model and the GREP/RAG knowledge layer. **Map:**
[docs/entity_intelligence_pipeline.md](docs/entity_intelligence_pipeline.md).

**Full architecture spec:** [docs/harness_pattern.md](docs/harness_pattern.md).
**Migration note for returning contributors:** [docs/MIGRATION_HARNESS_PATTERN.md](docs/MIGRATION_HARNESS_PATTERN.md).

## Start here by role

**[Setup requirements](docs/SETUP_REQUIREMENTS.md)** - GPU, environment setup, and dependencies for all platforms

| Lane | You are | Read first |
|---|---|---|
| 01 Platform safety | A trust & safety team or recruitment marketplace integrating moderation | [Enterprise pilot](./docs/scenarios/enterprise_pilot.md) / [Recruiter self-audit](./docs/scenarios/recruiter-self-audit.md) / [Enterprise deployment](./docs/deployment_enterprise.md) |
| 02 NGO & regulator | An NGO caseworker, legal aid organization, regulator, or embassy desk | [NGO office workflow](./docs/scenarios/ngo-office-deployment.md) / [Edge deployment example](./examples/deployment/ngo-office-edge/README.md) |
| 03 Individual worker / mobile | A migrant worker, peer supporter, or community helper using the Android app | [Worker self-help](./docs/scenarios/worker-self-help.md) / [Mobile component](./docs/architecture/duecare_mobile.md) / [Android app architecture](./docs/android_app_architecture.md) |
| 04 Researcher | An academic, journalist, policy analyst, or peer reviewer | [Peer review guide](./docs/FOR_PEER_REVIEW.md) / [Kaggle judge guide](./docs/FOR_KAGGLE_JUDGES.md) / [Researcher scenario](./docs/scenarios/researcher-analysis.md) / [Workbench README](./kaggle/01-duecare-exploration-workbench/README.md) |
| 05 Anonymized knowledge sharing | A partner sharing reviewed, sanitized facts without exposing workers or raw case files | [Hub use cases](./apps/duecare-ai.com/app/templates/use-cases.html) / [Submit information](./apps/duecare-ai.com/app/templates/submit-information.html) / [Submission queue](./apps/duecare-ai.com/app/templates/submissions.html) |
| 06 Developer / integration partner | A team embedding DueCare into your own product, bot, dashboard, or internal workflow | [Install guide](./docs/install.md) / [Embedding guide](./docs/embedding_guide.md) / [Meta package](./packages/duecare-llm/README.md) / [Client integration](./apps/duecare-ai.com/app/templates/client-connect.html) |

> **Implementation paths by audience:** see
> [`docs/deployment/`](./docs/deployment/README.md) for the four
> audience-first deployment paths (Single NGO, NGO Network,
> Government office, Platform safety) and the cross-cutting email
> oracle for civil society contribution. Complements the lane table
> above; same system, audience-first framing.

## Why this exists

Frontier LLMs fail predictably on **migrant-worker trafficking**
scenarios — documented in the author's prior
[OpenAI gpt-oss-20b Red-Teaming Challenge writeup](https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/llm-complicity-in-modern-slavery-from-native-blind).
The people and institutions closest to the harm need practical tools:
platforms need earlier moderation signals, frontline NGOs and regulators
need faster case analysis and evidence organization, workers need guidance
they control, and researchers need reproducible ways to explain patterns.

DueCare is that shared harness. Because it is built as a **universal**
safety and evidence framework, the same architecture can also evaluate
tax evasion, money laundering, medical misinformation, and any other
safety domain that can describe itself with a taxonomy, evidence base,
and rubric.

## What ships

**17 package surfaces** share the `duecare` Python namespace (PEP 420). The
source workspace installs them together; the `duecare-llm` meta package is the
public pip entry point for the workflow-oriented stack.

| Package | Role | Test surface |
|---|---|---|
| [`duecare-llm-core`](./docs/components/duecare_llm_core.md) | Contracts, schemas, enums, registries, provenance, observability | Unit tests |
| [`duecare-llm-models`](./docs/components/duecare_llm_models.md) | 8 model adapters (Transformers+Gemma 4 function calling, llama.cpp, Unsloth, Ollama, OpenAI-compatible, Anthropic, Gemini, HF Endpoint) | Adapter tests |
| [`duecare-llm-domains`](./docs/components/duecare_llm_domains.md) | Pluggable domain packs + 3 shipped (trafficking, tax_evasion, financial_crime) | Domain-pack tests |
| [`duecare-llm-tasks`](./docs/components/duecare_llm_tasks.md) | 9 capability tests (guardrails, anon, classify, extract, grounding, multimodal, multi-turn, tool-use, cross-lingual) | Capability tests |
| [`duecare-llm-agents`](./docs/components/duecare_llm_agents.md) | 12-agent swarm + AgentSupervisor with retry/budget/harm-abort + Gemma 4 function-calling orchestration | Agent tests |
| [`duecare-llm-workflows`](./docs/components/duecare_llm_workflows.md) | YAML DAG loader + topological runner | Workflow tests |
| [`duecare-llm-publishing`](./docs/components/duecare_llm_publishing.md) | HF Hub + Kaggle publisher, markdown reports, HF model cards | Publishing tests |
| `duecare-llm-engine` | Heuristic prescan + GREP KB + RAG + tool-call + Gemma verdict pipeline (the core content-safety harness) | Pipeline smoke tests |
| `duecare-llm-server` | FastAPI app that hosts the pipeline + audit dashboard (the live demo) | Route + audit-trail tests |
| `duecare-llm-evidence-db` | Redacted-evidence corpus + audit trail SQLite store | Schema + integrity tests |
| `duecare-llm-benchmark` | `smoke_25` + `score_row` + `aggregate` scoring helpers (zero deps) | Scoring + aggregation tests |
| `duecare-llm-training` | Fail-closed dataset/training plans; execution delegates to the strict engine or active A-00 Kaggle handoff | Training-contract and plan tests |
| `duecare-llm-research-tools` | Playwright scrapers + document extractors for domain corpora | Scraper + extractor tests |
| `duecare-llm-nl2sql` | NL → SQL translator for evidence DB queries | NL→SQL roundtrip tests |
| `duecare-llm-chat` | DueCare reviewer workbench: FastAPI app, shared chrome, static pages, harness contracts, and Gemma 4 runtime hooks | 18 test files: harness contract, route, workbench UI, JSON parser, anonymization, design-tooltip migration, model-output sanitizer, process bulk review, etc. |
| `duecare-llm-cli` | The `duecare` command-line tool (tree, test, review, status, deps) | CLI command tests |
| [`duecare-llm`](./docs/components/duecare_llm_meta.md) (meta) | Public pip entry point for the workflow stack and `duecare` CLI | Re-export + import tests |
| **Current local pytest collection gate** | | Run `python -m pytest packages --collect-only -q` before publishing an exact count. |

## Quick start

**One command per audience:** `python launch.py` lists launch profiles for NGOs
(Dockerized, one command), developers (local workbench), researchers (offline
benchmark), and notebook users (Colab/Kaggle with a public URL). See
[`docs/QUICK_LAUNCH.md`](docs/QUICK_LAUNCH.md).

### Install

```bash
# Public meta-package for the workflow-oriented stack
pip install duecare-llm

# Or, granular: install only what a Kaggle notebook needs
pip install duecare-llm-core duecare-llm-domains duecare-llm-tasks duecare-llm-agents

# Source checkout: install all 17 workspace packages together
uv sync --all-packages
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
| **Individual worker** wanting it on your phone | [`docs/scenarios/worker-self-help.md`](./docs/scenarios/worker-self-help.md) |
| **Caseworker** at an NGO using DueCare | [`docs/scenarios/caseworker_workflow.md`](./docs/scenarios/caseworker_workflow.md) |
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
- [**Harness ecosystem**](./docs/harness_ecosystem.md) — the current
  inventory of content, privacy, search, graph, synthetic-data,
  fine-tuning, judging, and report harnesses
- [**Ecosystem overview**](./docs/ecosystem_overview.md) — how the
  3 outcomes and 5 setup lanes compose around the shared harness
  ecosystem, with Mermaid diagrams
- [**Maria's case end-to-end**](./docs/marias_case_end_to_end.md)
  — composite case traced through every layer of the ecosystem
  (writeup + video + pitch material)
- [**Cross-NGO trends federation**](./docs/cross_ngo_trends_federation.md)
  — privacy-preserving aggregation protocol for sharing patterns
  across NGOs without sharing PII
- [**Comparison vs alternatives**](./docs/comparison_to_alternatives.md)
  — when DueCare fits vs when Hive / Sift / Azure / OpenAI / Llama
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

### Kaggle submission — judge reading order

The active submission path is intentionally narrow: two Kaggle folders under
`kaggle/`. Each active kernel installs the DueCare packages from GitHub, writes
outputs under `/kaggle/working`, launches a local server, and must print a
public `https://*.trycloudflare.com` URL for browser access. The former video
pitch kernel and A-01 through A-24 appendix notebooks are archived under
`kaggle/_archive/notebooks/` as reference material.

#### Start here

| Order | Folder | Role |
|---|---|---|
| 01 | [`kaggle/01-duecare-exploration-workbench/`](./kaggle/01-duecare-exploration-workbench/) | Core omni workbench with model picker, layer toggles, traces, and A/B comparison |
| 02 | [`kaggle/02-live-demo/`](./kaggle/02-live-demo/) | Focused screen-recording surface and public-hub demo |

#### Public training-learning route

For the evidence behind the training-data and adapter work, start with the
[207,680-row curriculum atlas](https://www.kaggle.com/code/taylorsamarel/duecare-200k-curriculum-visual-atlas),
then read the
[Gemma 4 optimization curves](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-learning-curves)
and the
[four-arm before/after comparison](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-four-arm-before-after).
The latter shows base and trained Gemma, each with and without the deterministic
harness, plus fictional controlled failure examples. The
[Tensor Processing Unit training lab](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-tpu-lora-training-lab)
continues the small real training study on Kaggle's eight-core accelerator.

See [`kaggle/_INDEX.md`](./kaggle/_INDEX.md) for the active folder list and
archive note.

Root `kaggle/` intentionally has no `A-*` folders, and the only root `04-*`
folder should be `04-kaggle-community-benchmark`; appendix and task-notebook
snapshots belong under `kaggle/_archive/notebooks/`.

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

### Key results (dated Kaggle and proxy runs)

| Metric | Value | Source |
|---|---|---|
| Stock Gemma 4 E4B mean score | **0.610** | [100 - Gemma Exploration](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-exploration) |
| Stock Gemma 4 E4B pass rate | **20%** | 100 (50 graded prompts) |
| Harmful phrase rate | **0.0% in this checked run** | No harmful phrase hits in the 50-prompt graded run; not a global safety guarantee |
| Refusal rate | **36%** | Clear refusal on exploitation requests |
| With RAG context | **0.59** (+23% over plain) | [260 - RAG Comparison](https://www.kaggle.com/code/taylorsamarel/duecare-260-rag-comparison) |
| With guided prompt | **0.62** (+28% over plain) | [260 - RAG Comparison](https://www.kaggle.com/code/taylorsamarel/duecare-260-rag-comparison) |
| Trafficking prompt corpus | **Large corpus; regenerate exact count** | [110 - Prompt Prioritizer](https://www.kaggle.com/code/taylorsamarel/00a-duecare-prompt-prioritizer-data-pipeline) plus `python scripts/verify_knowledge_surfaces.py` |
| Adversarial generators | **15** | [310 - Prompt Factory](https://www.kaggle.com/code/taylorsamarel/duecare-310-prompt-factory) |
| Evaluation frameworks | **7** | |
| Pytest collection | **Collect-only gate** | Run `python -m pytest packages --collect-only -q`; do not publish a static count without the current output. |
| GREP detection rules | **Hundreds; regenerate exact count** | Categories A-ZZ + SCREENING + later category packs; see [`docs/KNOWLEDGE_SURFACE_VERIFICATION.md`](docs/KNOWLEDGE_SURFACE_VERIFICATION.md) |
| RAG knowledge documents | **Hundreds; regenerate exact count** | ILO + UN + regional treaties + statutes + bilateral MOUs + screening tools + complaint procedures + case studies + case law + public enforcement and oversight sources |
| Complaint / narrative templates | **Dozens; regenerate exact count** | Origin-country, destination-country, referral pathway, scenario-letter, affidavit, and worksheet templates |
| Review personas | **Dozens; regenerate exact count** | NGO, lawyer, regulator, clinician, survivor advocate, engineer, FIU, maritime HR, and adjacent reviewer roles |
| Fee-camouflage labels | **Dozens; regenerate exact count** | Training / medical / process / placement / broker / document / loan-novation patterns |
| Corridor fee-cap entries | **Dozens; regenerate exact count** | Source and destination corridor entries, with volatile fee rules kept versioned rather than hardcoded into model answers |
| NGO contact bundles | **Dozens; regenerate exact count** | Per-corridor and regional bundles; verify volatile contact data before public reuse |
| ILO conventions (lookup table) | **15** | C029, C087, C095, C097, C098, C100, C111, C138, C143, C181, C182, C188, C189, C190, P029 |

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

## Domain packs

**Primary domain: migrant-worker safety / human trafficking.** That's
what DueCare is built to do. The trafficking pack is the
load-bearing corpus, the architecture, the rubric, the harness
contract, and the published Kaggle benchmark all target this domain
directly.

The pack system is also intentionally **abstract**: every pack ships
a YAML card, a taxonomy file, a rubric file, a PII spec, a seed-prompt
JSONL, and an evidence JSONL, all loaded by the same generic
`FileDomainPack`. That makes the pipeline reusable on adjacent
problems without changing the harness.

| Pack | Status | Seed prompts | Evidence items | Categories | Taxonomy dimensions |
|---|---|---|---|---|---|
| `trafficking` | **Primary** | Large generated corpus; regenerate exact count before quoting | Evidence-backed examples and public-source-derived scenarios | Multi-category | sector, corridor, ILO indicator, attack category, difficulty |
| `financial_crime` | Adjacency proof | 13 | 3 | 4 | laundering stage, typology, FATF indicator, jurisdiction |
| `tax_evasion` | Adjacency proof | 14 | 4 | 4 | scheme type, jurisdiction, FATF indicator, sophistication |

The full trafficking prompt corpus lives in
`configs/duecare/domains/trafficking/seed_prompts.jsonl`; the PyPI
domain wheel bundles a lightweight sample so installs stay small. All
three packs are discoverable via `duecare domains list` and
hot-swappable in the workflow runner.

### Why adjacent crime patterns are included

Migrant-worker exploitation **is** a financial crime when you look at
the money. Recruitment-fee debt bondage, salary deduction schemes,
cross-border loan novation, and side-letter contract substitution all
have direct analogues in the FATF money-laundering typology:

- **Predatory recruitment loans at 18%–68% APR** are textbook
  forced-labour indicators under ILO C029 AND can be predicate
  offences for AML under 18 USC 1956 / FATF Recommendation 3.
- **Cross-jurisdictional fee rerouting** through affiliate companies
  (Philippines training center → Hong Kong collection company) is
  both a POEA MC 14-2017 violation AND a structuring / TBML
  pattern under FATF Recommendation 20.
- **Wage deductions for "training" fees** post-arrival are ILO C181
  Art. 7 violations AND can constitute wage theft, racketeering
  (18 USC 1961-1968), or peonage (18 USC 1581).
- **Recruitment proceeds routed through cash-intensive businesses**
  (training centers, accredited clinics) are placement-stage
  laundering.

The `financial_crime` and `tax_evasion` packs exist to prove the
detection architecture generalizes to those adjacent problem spaces
when a partner needs them. They are NOT the product narrative.

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
# Run all package tests across the workspace
python -m pytest packages -v

# Or verify collection quickly
python -m pytest packages --collect-only -q

# Single package
python -m pytest packages/duecare-llm-core -v

# Single module folder (folder-per-module pattern)
python -m pytest packages/duecare-llm-core/src/forge/core/enums -v
```

Collection gate:

```
python -m pytest packages --collect-only -q
```

## Demo notebooks

The active notebook sources live under `kaggle/`. For the final hackathon
submission path, use `01-duecare-exploration-workbench` and `02-live-demo`.
The former video-pitch notebook and A-01 through
A-24 appendix notebooks are archived under `kaggle/_archive/notebooks/`.

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
> highlights the most important entries. See [`ROOT_FILES.md`](./ROOT_FILES.md)
> for why each root-level file remains in the GitHub landing directory.

```
gemma4_comp/
├── packages/                     # 17 package surfaces (workspace members)
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
│   ├── duecare-llm-chat/         # DueCare workbench app and Gemma 4 harnesses
│   ├── duecare-llm-cli/          # the `duecare` CLI
│   └── duecare-llm/              # meta package and workflow CLI entry point
├── kaggle/                       # Kaggle deliverables (per-notebook bundles)
│   ├── 01-duecare-exploration-workbench/  # CORE #01: omni playground (script kernel)
│   ├── 02-live-demo/             # CORE #02: focused live URL
│   ├── 03-universal-llm-benchmark/ # optional external endpoint benchmark
│   ├── 04-kaggle-community-benchmark/ # optional Kaggle benchmark surface
│   ├── _archive/notebooks/        # archived video pitch and A-01 through A-24
│   ├── shared-datasets/          # prompts, evaluation metadata, and training-data contracts
│   ├── kernels/                  # 9 generated/research kernels (separate from submission folders)
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
├── ROOT_FILES.md                 # root-file manifest and cleanup policy
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
  title={{DueCare: A Gemma 4 Safety Ecosystem for Migrant-Worker Protection}},
  author={Amarel, Taylor},
  year={2026},
  howpublished={Kaggle Gemma 4 Good Hackathon},
  url={https://github.com/TaylorAmarelTech/gemma4_comp},
}
```

## Acknowledgements

DueCare is the harness layer on top of a substantial existing body of
migrant-worker safety research. Historical benchmark, corpus, and
case-pattern inventories helped shape the current project, but those
old counts are not public product guarantees. Treat any exact corpus,
prompt, rubric, corridor, or seed-module number as an artifact that must
be re-measured from the cited script, manifest, or A-00 export before it
is reused in public copy.

The reusable contribution is the shape of the system: trafficking-aware
prompts and rubrics, corridor and fee-rule knowledge, evidence graphs,
anonymization gates, and review workflows that help Gemma 4 operate as
part of a safer local-node ecosystem.

The harness is grounded in:

- **ILO Conventions**: C029 (Forced Labour), C095 (Protection of
  Wages), C097 (Migration for Employment), C181 (Private Employment
  Agencies — the workhorse "no fees from workers" rule), C189
  (Domestic Workers), C188 (Work in Fishing), P029 (2014 Forced
  Labour Protocol)
- **UN Palermo Protocol** (Protocol to Prevent, Suppress and Punish
  Trafficking in Persons, 2000) for the canonical trafficking
  definition and State Party obligations
- **U.S. TVPRA** (Trafficking Victims Protection Reauthorization
  Act) — 22 U.S.C. 7102 forced-labour definition + 20 CFR 655.135(j)
  H-2A prohibited-fee rule
- **18 years of POEA / DMW enforcement data** (Philippines), the
  largest single-country corpus of recruitment-agency licensing
  actions in this space
- **FATF 40 Recommendations** for the financial-crime side of the
  graph: predicate offence framing, beneficial ownership tracing,
  and STR thresholds
- Source-country statute sets: **Nepal Foreign Employment Act 2007**,
  **Indonesia UU 18/2017 + BP2MI Reg. 09/2020**, **Bangladesh
  Overseas Employment and Migrants Act 2013**, **Vietnam Decree
  38/2020/ND-CP**, **HK Cap. 57 / 57A**

The public claim rule is simple: explain the six-lane ecosystem and the
local-to-anonymized-sharing boundary clearly, but publish exact metrics
only when the dated artifact and verification command are named beside
the number.
