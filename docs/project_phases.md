# Project Phases — Gemma 4 Good Hackathon

> Authoritative execution plan for the Gemma 4 hackathon submission.
> This document is the canonical "what we're building and in what order."
>
> For the component-level technical design, see `architecture.md`.
> For the mapping of existing assets into this plan, see `integration_plan.md`.
> For the hackathon rules and tracks, see `project_overview.md`.
>
> Last updated: 2026-04-11.

## Executive summary

**The project is a 4-phase investigation-and-delivery pipeline for Gemma 4
as an LLM safety tool for migrant-worker trafficking scenarios.** Each
phase builds on the previous one, and each phase produces an independently
publishable artifact that strengthens the submission narrative.

| Phase | Question it answers | Deliverable | Duration |
|---|---|---|---|
| **1. Exploration** | What can Gemma 4 do out of the box on our test categories? | Gemma 4 Baseline Report + failure taxonomy | **~6 days** |
| **2. Comparison** | How does Gemma 4 compare to GPT-OSS, Qwen, Llama, Mistral, DeepSeek on the same tests? | Cross-model Comparison Report + public benchmark repo | **~5 days** |
| **3. Enhancement** | Can we improve Gemma 4 on the categories where it fails, via RAG + fine-tuning? | Fact database, fine-tuned model weights (HF Hub), ablation study | **~10 days** |
| **4. Implementation** | Can the enhanced Gemma 4 power a real-world protective deployment? | 2–3 demo applications + public UI + public API endpoint | **~8 days** |
| **Wrap** | Writeup + video + polish | Kaggle submission | **~3 days** |

**Total budget: ~32 days. Available window: Apr 14 – May 18 = 35 days.**
3 days of buffer for slippage.

### The four test categories (consistent across all phases)

Every phase runs the **same four capability tests** against whatever model
is under evaluation. This is the through-line that makes the phases
comparable and the video narrative clean.

1. **Response policy guardrails** — does the model refuse appropriately,
   cite ILO / Palermo / national labor law, surface red flags, and redirect
   to protective resources?
2. **Anonymization** — can the model detect and redact PII (names,
   addresses, phone numbers, passport numbers, case identifiers) in
   migrant-worker case documents?
3. **Document classification** — can the model classify a document by
   sector, migration corridor, ILO forced-labor indicators, and attack
   category?
4. **Key fact extraction** — can the model extract structured facts (dates,
   entities, amounts, employer names, fee structures, indicator counts)
   from free-text source documents?

**Why these four.** They cover the full NGO workflow:
intake (classification) → preprocessing (anonymization) → analysis (fact
extraction) → output (guardrails on downstream LLM responses). A tool that
passes all four can slot into an organization's existing pipeline; a tool
that only passes one is a demo.

---

## Phase 1 — Gemma 4 Exploration

### 1.1 Objective

**Establish the out-of-the-box baseline for Gemma 4 (E2B and E4B) on all
four capability tests, with zero fine-tuning, zero RAG, and zero prompt
engineering beyond the minimum needed to elicit a reasonable response.**

This is the "naive reality check" phase. We need to know exactly where
Gemma starts before we claim to improve it.

### 1.2 Method

- **Free-form probing** (human-driven, recorded as Jupyter notebooks):
  start with the hardest known prompts from the author's prior
  `legacy_kaggle_tests/my_red_team_tests.json` (5K+ cases from the
  gpt-oss-20b Red-Teaming Challenge). Capture interesting failure modes
  qualitatively.
- **Automated probing** (runner-driven): run the full 21K-test public
  benchmark (`trafficking-llm-benchmark-gitlab`) against Gemma E2B and
  Gemma E4B. Score each response with the existing evaluation harness
  from `_reference/framework/src/evaluation/`.
- **Iterative failure-mode mining**: after the first automated pass,
  cluster the failure cases by sector / corridor / attack category / ILO
  indicator. Identify the 5-10 dominant failure modes. Add targeted probes
  for each.

### 1.3 Test categories — what we measure

For each prompt + response pair, we compute:

| Category | Specific metrics |
|---|---|
| **1. Response policy guardrails** | grade exact-match against graded examples (5-grade rubric), grade-within-1, ILO indicator recall/precision, documentation reference precision, refusal rate, harmful-phrase rate |
| **2. Anonymization** | PII span recall/precision (Presidio ground truth), false-positive rate on non-PII, handling of edge cases (foreign names, transliterated addresses, non-Latin scripts) |
| **3. Document classification** | sector accuracy, corridor accuracy, ILO indicator multi-label F1, attack category F1, difficulty estimation agreement |
| **4. Key fact extraction** | entity extraction F1 (person, organization, location, currency), numeric extraction accuracy, date extraction accuracy, citation extraction accuracy |

### 1.4 Inputs

- **Models**: `google/gemma-4-e2b-it` (2B), `google/gemma-4-e4b-it` (4B),
  both via `transformers` and via `llama-cpp-python` (GGUF) so we
  characterize both precision settings.
- **Test data**: the 21K public benchmark + the 5K legacy red-team tests.
- **Ground truth**: the benchmark's graded response examples
  (worst/bad/neutral/good/best per prompt), plus a small PII-labeled
  corpus (200 docs) for anonymization evaluation.

### 1.5 Tools used (all already in `_reference/`)

- `_reference/framework/src/evaluation/` — grading infrastructure
- `_reference/framework/src/chain_detection/` — 126 attack chains
- `_reference/framework/src/prompt_injection/` — 631 mutators for
  adversarial stress
- `_reference/framework/src/scraper/seeds/` — 176 seed modules with
  20,460+ facts to draw classification/extraction test cases from
- `_reference/trafficking_llm_benchmark/legacy_kaggle_tests/` — 5K+
  legacy red-team tests from the prior gpt-oss-20b competition
- `_reference/trafficking-llm-benchmark-gitlab/` — 21K public test suite

### 1.6 Deliverables

1. **`reports/phase1/baseline_gemma_e2b.md`** — full metrics + per-category
   breakdown for Gemma 4 E2B
2. **`reports/phase1/baseline_gemma_e4b.md`** — same for E4B
3. **`reports/phase1/failure_taxonomy.md`** — top 10 failure modes with
   worked examples, grouped by category
4. **`notebooks/phase1_exploration.ipynb`** — the free-form probing
   session, published alongside the writeup
5. **`data/phase1/baselines.sqlite`** — all (prompt, response, grade)
   triples in a queryable DB for later phases
6. **Video B-roll**: screen recording of a handful of instructive failures
   (for use in the final video)

### 1.7 Success criteria

- Both model sizes (E2B, E4B) produce complete metric tables across all 4
  categories.
- Failure taxonomy has at least 10 distinct modes with ≥5 examples each.
- Raw data is reproducible via a single CLI command (`python -m src.phases.exploration run`).

### 1.8 Duration: ~6 days (Apr 14 – Apr 19)

### 1.9 Open questions

- Do we also baseline Gemma 3 (E2B and E4B) to show the jump from
  generation to generation? **Leaning no** — out of scope for the
  hackathon's theme.
- Which PII-labeled corpus do we use for the anonymization test? **Leaning
  a custom 200-document corpus** derived from public court filings with
  Presidio-generated ground truth and manual spot-checking.

---

## Phase 2 — Gemma 4 Comparison

### 2.1 Objective

**Run the identical four-category test suite against a field of competing
open-weight and API models, producing a head-to-head comparison that
positions Gemma 4 in the LLM safety landscape.**

This is the "is Gemma actually better than the alternatives?" phase. The
results directly feed the video's headline table.

### 2.2 Method

- **Hold the test suite constant** — same prompts, same scoring harness,
  same ground truth as Phase 1.
- **Run it on every model in the comparison field.**
- **Compute the same metric set and break down by category / sector /
  corridor / difficulty.**
- **Produce a single comparison report with both headline tables and
  detailed per-category breakdowns.**

### 2.3 Comparison field

| Model | Size | Access | Why included |
|---|---|---|---|
| **Gemma 4 E2B** (baseline, Phase 1) | ~2B | local | primary subject |
| **Gemma 4 E4B** (baseline, Phase 1) | ~4B | local | primary subject |
| **GPT-OSS-20B** | 20B | local or HF Inference | direct competitor; was the subject of the author's prior red-team writeup |
| **GPT-OSS-120B** | 120B | HF Inference or API | upper bound on the GPT-OSS family |
| **Qwen2.5 7B Instruct** | 7B | local | strongest mid-size open model |
| **Qwen2.5 32B Instruct** | 32B | local or API | next-size-up Qwen |
| **Llama 3.1 8B Instruct** | 8B | local | popular baseline |
| **Mistral Small** | 22B | API | well-regarded small European model |
| **DeepSeek V3** (reasoning) | 671B (MoE) | API | reasoning-model comparison |
| **GPT-4o-mini** | (closed) | API | closed-source upper reference |
| **Claude Haiku 4.5** | (closed) | API | closed-source upper reference |

**Gemma is the primary subject**; closed models and DeepSeek are references
for positioning ("Gemma E4B is within N% of Claude Haiku at $0/1k vs
$0.25/1k"). The comparison is **head-to-head, not absolute**.

### 2.4 Tools used

- `_reference/trafficking_llm_benchmark/src/llm_engine/providers/` — 5 LLM
  provider adapters (OpenAI, Anthropic, Mistral, Ollama, plus free
  providers), already in _reference/
- `_reference/framework/src/api_client.py` — UnifiedAPIClient (for clean
  provider abstraction)
- `_reference/framework/src/evaluation/` — same scoring harness as Phase 1
- `_reference/framework/src/evaluation/pattern_evaluator.py` — deterministic
  rule-based scoring for reproducibility
- `_reference/trafficking_llm_benchmark/src/evaluation/fatf_risk_rating.py`
  and `tips_style_rating.py` — complementary rubrics
- Local inference via `llama-cpp-python` for GGUF; API inference via the
  provider adapters
- **Observability**: structured logs with `(model, test_id, metric, value,
  timestamp)` rows so the comparison is fully traceable

### 2.5 Deliverables

1. **`reports/phase2/comparison_report.md`** — full tables + plots
2. **`reports/phase2/headline_table.md`** — the 6-row, 5-column table
   that goes in the writeup and video
3. **`data/phase2/comparison.sqlite`** — every (model, prompt, response,
   score) row for reproducibility
4. **`reports/phase2/per_corridor_breakdown.md`** — per migration corridor
   (26 corridors) accuracy for each model
5. **`reports/phase2/cost_latency_tradeoff.md`** — a plot of accuracy vs.
   dollars-per-1k-evals vs. p50 latency, with Gemma at zero marginal cost
6. **Plot assets (PNG)** for video/writeup
7. **Public `trafficking-llm-safety-benchmark` Kaggle Dataset** — the
   comparison results published as a standalone Kaggle Dataset, citable
   by other researchers

### 2.6 Success criteria

- Every model in the comparison field has complete metrics for all 4
  categories.
- The headline table has Gemma ranked by a named metric (grade-within-1
  or ILO indicator F1).
- Per-corridor breakdown identifies at least 3 corridors where Gemma
  E4B meaningfully underperforms the best competitor (these become
  Phase 3 training targets).

### 2.7 Duration: ~5 days (Apr 20 – Apr 24)

### 2.8 Open questions

- Do we include closed models (GPT-4o-mini, Claude Haiku)? **Yes** — as
  reference only, to show "Gemma at $0 is within N% of Claude at $0.25".
- API cost budget? **$200 cap** on baseline API calls; cache aggressively,
  reuse across runs.
- DeepSeek V3 — include or skip? **Include** if the API holds up, skip if
  rate limits bite.

---

## Phase 3 — Gemma 4 Enhancement

### 3.1 Objective

**Improve Gemma 4 E4B on the categories where it failed in Phase 1 / Phase
2, using three complementary techniques: (a) RAG with a purpose-built fact
database, (b) Unsloth LoRA fine-tuning on the 21K graded response corpus,
and (c) the combination (RAG + fine-tune). Quantify the gains per
technique.**

This is the "technical depth" phase. It's where the 30-point Technical
Depth & Execution score comes from.

### 3.2 Three enhancement tracks

#### 3.2a Retrieval-Augmented Generation (RAG)

Build a fact database from existing reference material, wire it to a
retriever, and prepend retrieved facts to Gemma's context window.

**Fact database sources** (all already in `_reference/`):
- `_reference/framework/src/scraper/seeds/` — 176 seed modules, 20,460+
  facts (laws, case studies, statistics, advisories, court rulings)
- ILO / IOM / Palermo Protocol texts, Kafala documentation, POEA
  enforcement data
- Corridor-specific files (`migration_corridors_database.py`,
  `bilateral_labor_agreements_expanded.py`)
- Legal framework files (`international_instruments.py`,
  `ilo_indicators.py`, `echr_cases.py`, `eu_directive_transposition.py`)

**Index**: sentence-transformers (`all-mpnet-base-v2`) → FAISS → top-K
retrieval. Chunk by fact object, preserve source attribution so citations
survive retrieval.

**Retriever contract**:
```python
class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 5) -> list[FactHit]: ...

class FactHit(BaseModel):
    text: str
    source_module: str   # e.g. "us_trafficking_cases"
    fact_type: str       # law / case_study / statistic / ...
    score: float
    citation: str
```

**Integration**: the retriever's hits are prepended to Gemma's prompt as a
"RELEVANT REFERENCE MATERIAL" block, with instructions to cite.

#### 3.2b Unsloth LoRA fine-tune

Train Gemma 4 E4B on the graded response corpus to teach it the 5-grade
rubric + correct ILO citations.

- **Base model**: `unsloth/gemma-4-e4b-bnb-4bit`
- **LoRA**: r=16, alpha=32, targeting attn + MLP projections
- **Dataset**: 21K prompts × up to 5 graded responses = up to 105K
  training examples. Use the graded `best` and `good` responses as the
  positive target; use `bad` and `worst` as negative examples in a
  preference-style fine-tune (DPO) if time permits, or simple SFT if
  scope demands.
- **Splits**: 80/10/10, held out by source_case_id to prevent leakage.
- **Infrastructure**: 1 × A100-80GB for ~4-6 hours (via Lambda Labs /
  Modal / Colab Pro+ / Kaggle free GPU).
- **Training curriculum**: start with SFT; if SFT converges well, try
  DPO over the good/bad pairs as a second stage.

#### 3.2c Hybrid: RAG + fine-tune

The fine-tuned model loaded with the RAG retriever on top. This is the
release configuration for Phase 4 deployment.

### 3.3 Ablation study

Compare four configurations on Phase 1's test suite:

| Config | Phase 1 mentions |
|---|---|
| A. Stock Gemma 4 E4B | baseline |
| B. Stock + RAG | "RAG only" |
| C. Fine-tuned Gemma 4 E4B | "fine-tune only" |
| D. Fine-tuned + RAG | "hybrid" |

Report gain over baseline (A) for each metric in each of the 4 categories.
Identify which technique helps which category most.

**Hypothesis** (to test, not presume):
- RAG will help **fact extraction** and **classification** the most, because
  retrieval grounds the model in specific case data.
- Fine-tune will help **policy guardrails** the most, because the graded
  examples teach the refusal-with-education pattern.
- Hybrid will help **anonymization** somewhat, but anonymization is mostly
  a spans-level task that doesn't benefit from either as much as the others.

### 3.4 Tools used

- **Unsloth** (Special Tech track): for the LoRA fine-tune
- **`sentence-transformers`** + **FAISS**: for the RAG index
- **`_reference/framework/src/training/`**: pattern reference (we don't
  reuse the code directly, but the dataset export patterns are useful)
- **`_reference/trafficking_llm_benchmark/src/document_analysis/embedding_generator.py`**:
  embedding generation pattern
- **`_reference/framework/src/chain_detection/scorer.py`**: scoring for
  the ablation comparison

### 3.5 Deliverables

1. **`models/gemma-4-e4b-safetyjudge-v0.1/`** — fine-tuned LoRA adapters
   + merged fp16 + GGUF quantizations (q4_k_m, q5_k_m, q8_0)
2. **`data/rag/fact_db.sqlite`** + **`data/rag/faiss.index`** — the fact
   database and vector index
3. **`reports/phase3/ablation.md`** — 4-config comparison table
4. **`reports/phase3/enhancement_report.md`** — full methodology, training
   curves, training data statistics, intended-use statement
5. **HF Hub repo** — `taylorsamarel/gemma-4-e4b-safetyjudge-v0.1` with
   model card + all artifacts
6. **Model card** (for HF Hub) — following HF guidelines: intended use,
   out-of-scope use, training data summary, evaluation results, risks,
   license (MIT), citation

### 3.6 Success criteria

- Fine-tuned Gemma 4 E4B achieves **at least 2× improvement** over stock
  Gemma on grade exact-match for guardrails (Phase 1's weakest area).
- RAG + fine-tune reaches **within 90% of the top competitor from Phase 2**
  on every category (or better).
- Ablation is clean: each component's individual contribution is
  measurable and reproducible.

### 3.7 Duration: ~10 days (Apr 25 – May 4)

This is the biggest phase. 10 days because it includes the full data prep
+ training + evaluation loop + ablation + model card + HF Hub publish.

### 3.8 Open questions

- **SFT vs. DPO vs. both** — SFT is safer for 1 week. DPO is stronger but
  needs the preference pairs cleanly formatted. **Leaning SFT-first with
  DPO as a stretch goal.**
- **RAG chunk granularity** — fact-object-level or sentence-level? **Leaning
  fact-object-level** to preserve citation metadata.
- **E2B enhanced variant?** Do we also fine-tune E2B as a smaller release?
  **Leaning no** for the hackathon, yes as follow-on work.
- **Compute budget** — aiming for $50 on cloud GPU (Modal or Lambda), $200
  on API baselines, $0 on local inference.

---

## Phase 4 — Gemma 4 Use Case / Implementation

### 4.1 Objective

**Ship two (stretch: three) concrete, demonstrable applications of the
enhanced Gemma 4 safety judge, each hitting a different real-world
deployment surface. Judges should be able to use at least one of them live
on submission day.**

This is the "impact" phase. It's where the 40-point Impact & Vision score
comes from.

### 4.2 Three candidate use cases

#### 4.2a Public API endpoint — **P0, mandatory**

**A REST API that any developer can call to evaluate an LLM response
against the migrant-worker safety rubric.**

- **Endpoints**:
  - `POST /v1/evaluate` — body `{prompt, candidate_response}` →
    `EvaluationResult` JSON (grade, score, missed indicators, documentation
    refs)
  - `POST /v1/classify` — body `{text}` → `{sector, corridor, ilo_indicators,
    attack_category}` classification
  - `POST /v1/anonymize` — body `{text}` → `{redacted_text, spans, actions}`
  - `POST /v1/extract_facts` — body `{text}` → structured fact list
  - `GET /v1/healthz` — model version, uptime
  - `GET /docs` — OpenAPI spec
- **Auth**: anonymous for low-rate requests, API key for higher rates.
  Rate-limit at 10/minute per IP to prevent abuse.
- **Hosting**: HuggingFace Spaces (free tier, FastAPI + Docker).
- **Rationale**: this is the minimum viable "programmatic endpoint" the
  user asked for; every other use case can be built on top of it.

#### 4.2b Web demo UI — **P0, mandatory**

**A public web page where judges can paste text and see the four
capability outputs in real time.**

- **Pages**:
  - `/` — landing page with a large text box and 4 output panels
    (guardrails / anonymization / classification / fact extraction)
  - `/examples` — a gallery of 10-15 curated scenarios (safe / borderline /
    dangerous) judges can load with one click
  - `/compare` — a page where the user can paste a prompt and see
    side-by-side output from stock Gemma vs. enhanced Gemma (the phase 3
    artifact). **This is the killer panel for the judging video.**
  - `/about` — links to writeup, video, HF Hub, Kaggle submission
- **Tech**: FastAPI + Jinja + minimal CSS + minimal JS. No SPA framework.
- **Abuse mitigations**: topic classifier rejects anything outside the
  migrant-worker domain, per-IP rate limit, max input length 4K chars,
  prominent "research demo" disclaimer.

#### 4.2c Social media post monitor — **P1, strong nice-to-have**

**A minimal service that polls a public social media API (Twitter/X via
free tier, Reddit via PRAW, or Bluesky via AT Protocol) and flags posts
that match migrant-worker recruitment / trafficking indicators.**

- **Pipeline**:
  1. Poll a configured list of subreddits / hashtags / keywords
  2. For each new post, call `/v1/classify` and `/v1/extract_facts`
  3. If the post matches high-risk indicators (debt_bondage_math,
     excessive_recruitment_fees, kafala mentions, passport-retention
     threats), write a structured alert to a dashboard
  4. Human moderator reviews the dashboard; nothing is ever auto-acted
- **Scope discipline**: **read-only, alerting-only**, never auto-acts,
  never mass-messages, never scrapes protected data. This is explicitly
  a "human in the loop" tool.
- **Rationale**: shows the judge we can actually see real-world traffic,
  not just hypothetical examples.
- **Rate limits + API costs**: use free tiers only (Reddit: free, Bluesky:
  free). Avoid anything that requires Twitter/X paid API.

#### 4.2d Chat monitor (alternate / stretch) — **P2**

**A Discord / Telegram bot that lurks in a configured channel and flags
messages that match grooming or recruitment patterns.**

- Only active in channels the bot owner explicitly invites it to.
- Only flags to the channel moderator, never responds publicly.
- Strong ethical boundary: opt-in, consent-driven, human-reviewed only.

**Decision**: build **4.2a + 4.2b + one of (4.2c OR 4.2d)**. The third
slot depends on time available at week 4.

### 4.3 Tools used

- **FastAPI**: the API + UI framework
- **llama-cpp-python**: the runtime judge (loads the Phase 3 q5_k_m GGUF)
- **sentence-transformers + FAISS**: for the in-process RAG retrieval
- **structlog**: logging
- **slowapi**: rate limiting
- **HuggingFace Spaces**: hosting
- **Reddit API via PRAW** (if 4.2c goes ahead)

### 4.4 Deliverables

1. **Live public API** — `https://<project>.hf.space/v1/...` with OpenAPI
   spec
2. **Live public web demo** — `https://<project>.hf.space/` with examples
   and comparison pages
3. **`src/phases/implementation/`** — all application code for the demo +
   API + optional monitors
4. **`Dockerfile`** for reproducibility
5. **3-minute screen recording** of the comparison page showing the
   enhanced Gemma judge outperforming stock Gemma on real scenarios
   (this is the B-roll for the video)
6. **Operator guide** — `docs/operator_guide.md` — how an NGO could self-host
   the API on a laptop

### 4.5 Success criteria

- Live demo accessible from any browser on submission day
- API responds to `/healthz` and `/evaluate` within 2s on the free tier
- The `/compare` page shows a clear, judge-friendly qualitative improvement
  for the enhanced Gemma over stock Gemma on at least 5 curated examples
- All abuse mitigations in place and documented

### 4.6 Duration: ~8 days (May 5 – May 12)

### 4.7 Open questions

- **Live demo host** — HF Spaces (free) or Cloud Run (pay-as-you-go)?
  **Leaning HF Spaces** for zero cost + alignment with the hackathon.
- **Social media monitor source** — Reddit (most liberal API) or Bluesky
  (trendier)? **Leaning Reddit** — the API is mature, the content is
  relevant, the rate limits are friendly.
- **Human moderator UI** — minimal dashboard or email digest? **Leaning
  email digest** for scope discipline.

---

## Conclusion

The Gemma Migrant-Worker Safety Judge tells one clear story across four
phases:

**"Here's what Gemma 4 can't do yet, here's how it compares to its peers,
here's how we made it better, and here's how a frontline NGO can use the
better version tomorrow at zero cost."**

Each phase is independently publishable:
- **Phase 1** is a standalone paper: "Out-of-the-Box LLM Safety on
  Migrant-Worker Scenarios: A Gemma 4 Baseline"
- **Phase 2** is a standalone dataset + paper: "Cross-Model LLM Safety
  Comparison on the Trafficking-LLM-Safety-Benchmark"
- **Phase 3** is a standalone model release: "Gemma 4 E4B Safety Judge v0.1"
  on HF Hub, with a model card and ablation study
- **Phase 4** is a standalone public tool: the API + web demo

Any three of the four deliverables, in isolation, would be a credible
hackathon entry. Together they form a complete story that maps cleanly
onto the three judging criteria:

| Hackathon criterion | Pts | Where it's earned |
|---|---|---|
| **Impact & Vision** | 40 | Phase 4 (deployment story) + Phase 1 failure taxonomy (why the problem matters) |
| **Video Pitch & Storytelling** | 30 | The phase narrative arc itself. Hook: the NPR verdict + the POEA statistic. Body: the four-phase journey. Resolution: the live demo. |
| **Technical Depth & Execution** | 30 | Phase 3 (RAG + fine-tune + ablation) + Phase 2 (rigorous comparison methodology) |

---

## Next steps (immediate, next 48 hours)

Once this phased plan is approved:

1. **Finalize the phase runners** — `src/phases/{exploration, comparison,
   enhancement, implementation}/runner.py` stubs + configs
2. **Lock the test harness contract** — the four capability tests must be
   callable as `run_test_suite(model, phase) -> ReportRecord` and produce
   identical metric shapes across all 4 phases
3. **Stand up the Phase 1 baseline pipeline end-to-end** on a 100-sample
   slice — prove the loop works before scaling to 21K
4. **Freeze the model list for Phase 2** — commit to exactly which models
   are in the comparison (budget and time constraint)
5. **Procure compute** — reserve A100 hours for the Phase 3 fine-tune so
   it's not a last-minute scramble
6. **Answer the pending open questions** — E2B vs E4B priority, Unsloth
   experience, live demo host, social media source choice

---

## Hackathon track alignment (recap)

| Track | Prize | Phase that qualifies |
|---|---|---|
| Main Track | $100K (1st–4th) | All phases collectively |
| Impact Track → Safety & Trust | $10K | Phase 1 (failure mode documentation) + Phase 4 (deployment) |
| Special Technology → Unsloth | $10K | Phase 3 (fine-tune) |
| Special Technology → llama.cpp | $10K | Phase 3 (GGUF export) + Phase 4 (runtime) |
| Special Technology → LiteRT | $10K | Phase 4 stretch (mobile demo) |

Projects can win both a Main Track prize and a Special Technology prize
per the hackathon rules, so a strong execution here plausibly lands at
least two payouts.

---

## Deliverables checklist

Everything the submission needs, grouped by artifact:

### Code
- [ ] `gemma4_comp/` public repository (MIT)
- [ ] `src/phases/exploration/` phase 1 runner + configs
- [ ] `src/phases/comparison/` phase 2 runner + configs
- [ ] `src/phases/enhancement/` phase 3 RAG + fine-tune + ablation
- [ ] `src/phases/implementation/` phase 4 API + demo + monitor
- [ ] CI green on every phase's smoke tests
- [ ] MIT license on everything

### Data
- [ ] `data/phase1/baselines.sqlite` — Gemma baseline rows
- [ ] `data/phase2/comparison.sqlite` — cross-model rows
- [ ] `data/rag/fact_db.sqlite` + `data/rag/faiss.index` — fact database
- [ ] `data/phase3/train.jsonl`, `val.jsonl`, `test.jsonl` — training
      splits (held out by source_case_id)

### Models
- [ ] HF Hub repo `taylorsamarel/gemma-4-e4b-safetyjudge-v0.1`
  - [ ] LoRA adapters
  - [ ] Merged fp16 weights
  - [ ] GGUF q4_k_m / q5_k_m / q8_0
  - [ ] Model card with intended use, out-of-scope use, evaluation results
  - [ ] MIT license

### Reports
- [ ] `reports/phase1/baseline_gemma_e2b.md`
- [ ] `reports/phase1/baseline_gemma_e4b.md`
- [ ] `reports/phase1/failure_taxonomy.md`
- [ ] `reports/phase2/comparison_report.md`
- [ ] `reports/phase2/headline_table.md`
- [ ] `reports/phase2/per_corridor_breakdown.md`
- [ ] `reports/phase3/ablation.md`
- [ ] `reports/phase3/enhancement_report.md`
- [ ] `reports/phase4/operator_guide.md`

### Hackathon submission
- [ ] Kaggle writeup ≤1,500 words referencing all 4 phases
- [ ] Public YouTube video ≤3 minutes with the phase narrative
- [ ] Live public demo URL
- [ ] Kaggle submission form completed

---

## Timeline (5 weeks + buffer)

```
Week 1 (Apr 14–20): Phase 1 Exploration
  Mon-Tue   : environment setup, Gemma E2B + E4B loaded locally, framework
              wired as sidecar dep
  Wed-Thu   : Phase 1 automated pipeline end-to-end on 100-sample slice
  Fri-Sun   : Full 21K run + free-form probing + failure taxonomy

Week 2 (Apr 21–27): Phase 2 Comparison
  Mon-Tue   : LLM provider adapters + model list locked + API keys
  Wed       : Automated comparison run (overnight where possible)
  Thu-Fri   : Per-category breakdowns, headline table, corridor analysis
  Sat-Sun   : Phase 2 report + public Kaggle Dataset publish

Week 3 (Apr 28–May 4): Phase 3 Enhancement (1/2)
  Mon-Tue   : RAG fact database + FAISS index
  Wed       : Unsloth training data prep (splits by case_id)
  Thu-Fri   : Fine-tune run on A100 (~6h + iteration)
  Sat-Sun   : GGUF export + first ablation pass

Week 4 (May 5–11): Phase 3 Enhancement (2/2) + Phase 4 Implementation
  Mon-Tue   : Ablation study + model card + HF Hub publish
  Wed-Thu   : FastAPI API endpoints + llama.cpp integration
  Fri-Sat   : Web demo UI (including /compare page)
  Sun       : Social media monitor (if time)

Week 5 (May 12–18): Writeup + video + submit
  Mon       : Writeup draft with real numbers
  Tue       : Video script finalized, B-roll captured
  Wed       : Video recorded and edited
  Thu       : End-to-end dress rehearsal of the live demo
  Fri       : Submit
  Sat-Sun   : Buffer for fixes
```

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Phase 3 fine-tune doesn't beat stock Gemma | Medium | High | Start Phase 3 ablation on a 1K-sample subset early; iterate before full run |
| HF Spaces runs out of memory at startup (q5_k_m ~3.1 GB) | Medium | High | Fall back to q4_k_m (~2.5 GB); pre-load and keep-alive |
| API costs blow through budget during Phase 2 | Low | Medium | Hard cap at $200; cache all responses aggressively |
| Phase 2 model inclusion list too ambitious | Medium | Medium | Commit to the 6 must-have models early; add the rest only if time permits |
| Presidio anonymization is weaker than needed | Medium | Low | Supplement with custom regex rules; accept 85% recall as a reasonable baseline |
| Social media API rate-limit pain in Phase 4 | Medium | Low | Start with Reddit (most generous); have email-digest fallback |
| Unsloth Gemma 4 support is flaky on the chosen GPU | Low | High | Fall back to stock HuggingFace transformers + PEFT; slower but reliable |
| Video production overrun | Medium | Medium | Freeze script by May 13, shoot by May 15, edit by May 17; no improvisation |

---

## What would push this from "good submission" to "winner"

Beyond the four phases, these are the things that tend to differentiate
winning submissions on Kaggle hackathons in our experience:

1. **A real, live demo** that judges can actually use on submission day —
   **Phase 4 covers this**
2. **A quantitative claim that's easy to tweet** — e.g., "Gemma 4 E4B,
   fine-tuned, agrees with human expert graders 68% of the time — 2.2×
   stock Gemma and comparable to Claude Haiku at zero inference cost."
   **Phase 3 ablation produces this.**
3. **Citable external-validity evidence** — evaluate on the legacy gpt-oss
   red-team tests *in addition to* our own benchmark, to claim
   generalization. **Add to Phase 2 deliverables.**
4. **A clear ethics posture** — model card, intended-use statement,
   out-of-scope use, abuse mitigations, opt-in-only monitoring. **Phase
   3 + Phase 4 cover this.**
5. **A clear hand-off story for NGOs** — operator guide with a "run this
   on a laptop" walkthrough. **Phase 4 deliverable.**
6. **Reproducibility to the commit** — every metric in the writeup has a
   `(git_sha, dataset_version)` tuple behind it. **Observability section
   of the architecture covers this.**
7. **A no-harm demonstration** — explicitly red-team the fine-tuned model
   itself and show it doesn't produce new exploitation guidance. **Add
   to Phase 3 deliverables.**

All seven of these are already implicit in the phased plan; the work is
making sure each one actually ships.
