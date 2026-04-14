# DueCare Project Status

> Last updated: Session ending April 12-13, 2026
> Deadline: May 18, 2026 (35 days remaining)

## Local Baseline (Gemma 3 4B via Ollama -- preliminary)

```
Model:      gemma3:4b (stock, via Ollama, no fine-tuning)
Prompts:    5 evaluated (from 74,567 corpus)
Mean score: 0.40
Pass rate:  0%
Fail rate:  100%
Runtime:    ~60s on local CPU

Comparison (n=5, gemma3:4b):
  Plain:     0.484 mean, 20% pass
  + RAG:     0.594 mean, 40% pass (+23%)
  + Guided:  0.620 mean, 40% pass (+28%)
```

**Stock Gemma produces inadequate trafficking safety responses.**
Context injection improves scores significantly even without fine-tuning.
Full Gemma 4 E4B evaluation at scale is the Phase 1 deliverable.

## Component Inventory

### Packages (8 PyPI)
| Package | What it has |
|---|---|
| duecare-llm-core | 12 Pydantic schemas, Protocol contracts, Registry, Provenance |
| duecare-llm-models | 8 model adapters (incl. Ollama for local Gemma) |
| duecare-llm-domains | Domain pack loader, 3 domain packs, document pipeline (6 modules) |
| duecare-llm-tasks | 9 capability tests, 15 generators, 7 evaluators |
| duecare-llm-agents | 12 agents, AgentSupervisor, Evolution engine (4 modules) |
| duecare-llm-workflows | YAML DAG loader + topological runner |
| duecare-llm-publishing | HF Hub + Kaggle publisher, markdown reports |
| duecare-llm (meta) | CLI + re-exports |

### Generators (15)
evasion, coercion, financial, regulatory, corridor, multi_turn,
document_injection, persona (31 personas), interactive (10 formats),
case_challenge, informed_followup, creative_attacks (12 strategies),
obfuscation (5 strategies), output_conditioning (5 formats),
document_quiz (5 question types)

### Evaluators (7)
weighted_scorer (54 criteria), multi_layer (6 evaluation stages),
llm_judge, FATF compliance ratings, TIPS tier ratings,
failure_analyzer (6 failure modes), citation_verifier

### Demo App (12 API endpoints)
analyze, batch, evaluate (Gemma-powered), function-call,
analyze-document, rag-context, quick-check, domains, rubrics,
stats, health, HTML dashboard

### Pipeline (8 stages)
acquire → classify → extract → knowledge_base → generate_prompts →
rate_evaluate → remix → baseline_test

### Data Assets
- 74,567 trafficking prompts
- 5 evaluation rubrics (54 criteria)
- 31 verified legal provisions (15 jurisdictions)
- 26 + 32 migration corridors
- 29 scheme fingerprints
- 111-entry RAG knowledge base

### Tests: 173 passing (core: 77, models: 22, domains: 23, tasks: 16, agents: 17, workflows: 9, publishing: 9)
### Total Python LOC: 47,351

## Kaggle Notebooks (18)

| Notebook | Status | URL |
|---|---|---|
| 00 Gemma Exploration | COMPLETE (v18) | taylorsamarel/duecare-gemma-exploration |
| 00a Prompt Prioritizer | Live | 00a-duecare-prompt-prioritizer-data-pipeline |
| 00b Prompt Remixer | Live | 00b-duecare-prompt-remixer-data-pipeline |
| 01 Quickstart | Live | duecare-quickstart |
| 02 Cross-Domain Proof | Live | duecare-cross-domain-proof |
| 03 Agent Swarm Deep Dive | Live | duecare-agent-swarm-deep-dive |
| 04 Submission Walkthrough | Live | duecare-submission-walkthrough |
| 05 RAG Comparison | Live | duecare-rag-comparison |
| 06 Adversarial | Live | duecare-adversarial |
| 08 FC + Multimodal | Live | duecare-fc-multimodal |
| 09 LLM Judge | Live | duecare-llm-judge |
| 10 Conversations | Live | duecare-conversations |
| 11 Comparative | Live | duecare-comparative |
| 12 Prompt Factory | Live | duecare-prompt-factory |
| 13 Rubric Eval | Live | duecare-rubric-eval |
| 14 Dashboard | Live | duecare-dashboard |
| Phase 2 Model Comparison | Live | duecare-phase-2-model-comparison |
| Phase 3 Unsloth Finetune | Pushed | duecare-phase3-finetune |

> **Note:** Gemma 4 E2B/E4B Kaggle results are pending. The baseline
> numbers above are from Gemma 3 4B via local Ollama only.

## Kaggle Datasets (2)

| Dataset | Contents | URL |
|---|---|---|
| duecare-llm-wheels | 8 package wheels (v0.3.0) | taylorsamarel/duecare-llm-wheels |
| duecare-trafficking-prompts | 74,567 prompts + 5 rubrics | taylorsamarel/duecare-trafficking-prompts |

## What's Next (Priority Order)

### P0 — Blocks submission
- [ ] Run Notebook 00 on T4 x2 GPU (user can set in Kaggle UI)
- [ ] Phase 3 fine-tuning (run after baseline on T4)
- [ ] Record video demo (3 minutes)
- [ ] Finalize writeup (update with Phase 3 results)
- [ ] Git commit + push to public repo

### P1 — Significantly improves score
- [ ] Phase 2 comparison results (E2B vs E4B)
- [ ] RAG vs plain vs guided comparison numbers
- [ ] Fine-tuned model on HF Hub
- [ ] GGUF export for llama.cpp track

### P2 — Nice to have
- [ ] Run full 74K prompt evaluation (via Ollama locally)
- [ ] Browser extension prototype
- [ ] Additional domain packs (medical misinformation)
- [ ] Interactive HTML report for writeup
