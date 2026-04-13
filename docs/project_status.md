# DueCare Project Status

> Last updated: Session ending April 12-13, 2026
> Deadline: May 18, 2026 (35 days remaining)

## Real Gemma Results (Phase 1 Complete)

```
Model:      Gemma 4 E2B-IT (stock, no fine-tuning)
Prompts:    50 graded (from 74,567 corpus)
Mean score: 0.6096
Pass rate:  20% (good + best grades)
Fail rate:  80%
Runtime:    CPU on Kaggle P100 (~3.5 hours)
```

**Stock Gemma fails 80% of trafficking safety prompts.** This is the
baseline that Phase 3 fine-tuning will improve.

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

### Tests: 368+ passing
### Total Python LOC: 136,618

## Kaggle Notebooks (10)

| Notebook | Status | URL |
|---|---|---|
| 00 Gemma Exploration | COMPLETE (v18) | taylorsamarel/duecare-gemma-exploration |
| 00a Prompt Prioritizer | Live | 00a-duecare-prompt-prioritizer-data-pipeline |
| 00b Prompt Remixer | Live | 00b-duecare-prompt-remixer-data-pipeline |
| 01 Quickstart | Live | duecare-quickstart |
| 02 Cross-Domain Proof | Live | duecare-cross-domain-proof |
| 03 Agent Swarm Deep Dive | Live | duecare-agent-swarm-deep-dive |
| 04 Submission Walkthrough | Live | duecare-submission-walkthrough |
| Phase 2 Model Comparison | Live | duecare-phase-2-model-comparison |
| Phase 3 Unsloth Finetune | Pushed | duecare-phase3-finetune |

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
