# Integration Plan — Existing Assets into gemma4_comp

> Maps the author's existing framework and benchmark assets into the new
> `gemma4_comp` architecture (`docs/architecture.md`). For every source
> module we decide: **reuse as-is**, **adapt**, or **rewrite** — with a
> priority (P0/P1/P2), an effort estimate, and a target location.
>
> **Source 1:** `_reference/framework/` — `llm-safety-framework-public`
> (~29.8K LOC src + 7.2K LOC tests, 627 Python modules, v5.2.0, Python 3.11+)
>
> **Source 2:** `_reference/trafficking_llm_benchmark/` — the 300K+ LOC dev
> benchmark (already copied at scope=medium)
>
> **Source 3:** `_reference/trafficking-llm-benchmark-gitlab/` — public 21K
> test release (already copied)
>
> Last updated: 2026-04-11

## TL;DR

The existing codebase is vastly larger than the hackathon requires. The
integration strategy is **selective adoption, not wholesale port**:

| Scope | What | Integration effort |
|---|---|---|
| **Copy as-is** | Attack chains, prompt injection mutators, scraper seed modules, ILO documentation index | 0 — reference only |
| **Adapt** (thin wrapper) | LLM provider abstraction, chain registry + test engine, graded evaluation system, Playwright scraper stack, autonomous research agents | 1-3 days each |
| **Rewrite** (new for hackathon) | Unsloth fine-tune pipeline, GGUF/LiteRT export, on-device inference runtime, hackathon demo UI, anonymization gate | already scaffolded, 1-2 weeks total |
| **Reference only** | Cartography, dimensional matrix, intelligent attack phases 4-7, 18-plugin dashboard | too heavy for 5-week scope |

Total **P0** integration work (must-have for submission): **~8-10 days**.
Total **P1** integration work (strong nice-to-have): **~4-6 days**.
Total **P2** integration work (stretch goals): **~4-6 days**.

## How to read this plan

Every row has four fields:

- **Decision** — `REUSE` (copy + import), `ADAPT` (copy + refactor), `REWRITE`
  (build new, reference only), or `REFERENCE` (don't copy, link docs).
- **Priority** — P0 (blocking), P1 (strong value-add), P2 (stretch).
- **Effort** — rough hours or days for the integration work itself (not the
  original build).
- **Target** — where in `gemma4_comp/src/` the code lands.

When decisions conflict between the framework and benchmark (both have an
`evaluation/` module, both have a `cli.py`, etc.), the **framework wins**
because it's newer, cleaner, and uses Pydantic v2 throughout.

---

## 1. Schemas and base types

**Already in place.** The gemma4_comp scaffold has `src/schemas/` populated
with Pydantic v2 models for Provenance, item lifecycle, prompts, evaluation,
cases, documentation, attacks, and training records.

**What to do next:**
- Cross-reference against `_reference/framework/src/core/api_specification.py`
  (26+ Pydantic models) and pull in any fields we missed — especially for
  `TestSummary`, `EndpointSpec`, and `AgentRole` variants.
- Cross-reference against `_reference/trafficking_llm_benchmark/src/core/models.py`
  (520 LOC) for `BenchmarkTestCase`, `LLMResponse`, `EvaluationCriterion`.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/core/api_specification.py` | ADAPT — merge fields | P0 | 2h | `src/schemas/evaluation.py` |
| `framework/src/core/base_agent.py` (HarnessAgent, AgentRole enum) | ADAPT | P0 | 1h | `src/schemas/attacks.py` + `src/agents/base.py` (NEW) |
| `benchmark/src/core/models.py` | REFERENCE — rename fields already covered | P1 | 30m | `src/schemas/prompts.py` |
| `benchmark/src/core/registries.py` (CORRIDOR_REGISTRY, ATTACK_REGISTRY, 846 LOC) | ADAPT — taxonomy source | P0 | 3h | `configs/classification.yaml` + `src/data/classify/taxonomy.py` |
| `benchmark/src/core/constants.py` (ILO indicators, jurisdictions) | REUSE | P0 | 15m | `src/schemas/base.py` (constants submodule) |
| `benchmark/src/core/graded_responses.py` | ADAPT | P0 | 30m | already modeled in `src/schemas/prompts.py` |

---

## 2. Data sources (architecture §4)

The framework's `SourceRegistry` pattern is already what we want — 54+
sources across 7 tiers, all behind a common protocol. We lift the pattern,
not the implementations.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/scraper/sources.py` (412 LOC, 54+ sources, 7 tiers) | ADAPT — copy structure, add our `Source` protocol | P0 | 4h | `src/data/sources/registry.py` + `configs/sources.yaml` |
| `benchmark/src/data_pipeline/source_registry.py` | REFERENCE | P2 | — | — |
| `benchmark/src/data_pipeline/downloaders/ilo_downloader.py` | ADAPT | P1 | 2h | `src/data/sources/ilo_downloader.py` |
| `benchmark/src/data_pipeline/downloaders/web_downloader.py` | REFERENCE — replaced by framework's Playwright fetcher | P2 | — | — |
| `framework/src/scraper/feed_parser.py` (289 LOC, RSS/Atom) | REUSE | P1 | 30m | `src/data/sources/feed.py` |
| `framework/src/scraper/change_detection.py` (312 LOC, version tracking) | REUSE | P1 | 1h | `src/data/sources/change_detection.py` |
| `framework/src/scraper/document_identity.py` (475 LOC, SimHash dedupe) | REUSE | P0 | 1h | `src/data/ingest/deduper.py` |

---

## 3. Scraper stack — Playwright + stealth (architecture §4)

This is the most valuable "drop-in" asset in the whole framework. 16 core
modules + 176 seed modules + stealth + proxy rotation + politeness, all
pytest-covered.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/scraper/browser.py` (285 LOC, Playwright + stealth) | REUSE | P1 | 30m | `src/data/sources/browser.py` |
| `framework/src/scraper/fetcher.py` (340 LOC, text->HTML->JS escalation) | REUSE | P1 | 30m | `src/data/sources/fetcher.py` |
| `framework/src/scraper/extractor.py` (318 LOC, 4 extraction strategies) | REUSE | P1 | 30m | `src/data/sources/extractor.py` |
| `framework/src/scraper/stealth.py` (388 LOC, 5 levels) | REUSE | P1 | 15m | `src/data/sources/stealth.py` |
| `framework/src/scraper/proxy.py` (258 LOC, proxy rotation) | REUSE | P2 | 15m | `src/data/sources/proxy.py` |
| `framework/src/scraper/politeness.py` (231 LOC, robots.txt) | REUSE | P1 | 15m | `src/data/sources/politeness.py` |
| `framework/src/scraper/retry.py` (245 LOC, exponential backoff) | REUSE | P1 | 15m | `src/data/sources/retry.py` |
| `framework/src/scraper/scheduler.py` (294 LOC, parallel scraping) | REUSE | P2 | 30m | `src/data/sources/scheduler.py` |
| `framework/src/scraper/health.py` (167 LOC, source uptime) | REUSE | P2 | 15m | `src/data/sources/health.py` |
| `framework/src/scraper/knowledge_base.py` (292 LOC, fact indexing) | ADAPT | P1 | 2h | `src/docs/store.py` |
| `framework/src/scraper/indicator_matrix.py` (364 LOC, 7x11 ILO matrix) | REUSE | P0 | 30m | `src/grading/indicators.py` |
| `framework/src/scraper/seeds/` (176 modules, 20,460+ facts) | REUSE as-is | P0 | 0 | `_reference/framework/src/scraper/seeds/` (import path only) |
| `framework/src/scraper/seed_loader.py` (287 LOC) | REUSE | P0 | 30m | `src/data/sources/seeds/loader.py` |
| `framework/src/scraper/seed_pruner.py` (256 LOC, SimHash dedupe) | REUSE | P1 | 30m | `src/data/sources/seeds/pruner.py` |

**Note on seed modules**: the 176 seed files contain 20,460+ verified facts
spanning 7 tiers of jurisdictions and sectors. Do **not** reformat them. Add
a wrapper that imports them on demand and emits them as `RawItem`s, and
leave the originals untouched so we can re-sync from upstream if the author
updates them.

**Seed module targets** (abbreviated list; full 176 are available):
- Jurisdictions & regional: `us_trafficking_cases.py`, `uk_modern_slavery_cases.py`, `ph_trafficking_cases.py`, `qatar_worldcup_gcc_construction.py`, `india_labor_cases.py`, `mexico_central_america_cases.py`, `brazil_modern_slavery.py`, `canada_tfwp_cases.py`, `gulf_state_cases.py`, `lebanon_jordan_cases.py`, `ethiopia_east_africa_cases.py`, `australia_cases.py`, `hk_trafficking_labor_cases.py`, and ~20 more
- Sector-specific: `domestic_work_global_expanded.py`, `middle_east_domestic_workers.py`, `seasonal_agriculture_programs.py`, `construction_sector_global.py`, `garment_textile_exploitation.py`, `mining_extraction_exploitation.py`, `maritime_fishing.py`, `healthcare_worker_exploitation.py`, `hospitality_tourism_exploitation.py`, `gig_economy_platform_labor.py`, `technology_electronics_exploitation.py`, `education_sector_exploitation.py`, `prison_labor_exploitation.py`, and ~29 more
- Trafficking forms: `sex_trafficking_global.py`, `child_trafficking_expanded.py`, `forced_begging_trafficking.py`, `forced_marriage_trafficking.py`, `child_soldiers_armed_groups.py`, `organ_trafficking_cases.py`, `surrogacy_exploitation.py`
- Mechanisms: `debt_bondage_mechanics.py`, `passport_confiscation.py`, `kafala_system.py`, `fee_caps.py`, `recruitment_agency_database.py`, `wage_protection.py`
- Migration corridors: `migration_corridors_database.py` (174 routes), `multi_country_transit_routes.py`, `bilateral_labor_agreements_expanded.py`
- Legal/policy: `international_instruments.py`, `ilo_reports_detailed.py`, `ilo_indicators.py`, `eu_directive_transposition.py`, `echr_cases.py`, `labor_inspection_enforcement.py`

---

## 4. Ingestion (architecture §5)

No existing component maps cleanly. The benchmark and framework both jump
directly from source to classification without a first-class staging step.
We build fresh.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| — | REWRITE | P0 | 4h | `src/data/ingest/normalizer.py`, `staging.py` |
| `framework/src/scraper/document_identity.py` | REUSE | P0 | (already above) | `src/data/ingest/deduper.py` |

---

## 5. Classification (architecture §6)

The benchmark's `CORRIDOR_REGISTRY` (26 corridors) and `ATTACK_REGISTRY`
(18 strategies) are directly reusable as the taxonomy; the classifier logic
itself needs to be written to our `Classifier` protocol.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `benchmark/src/core/registries.py` taxonomy | ADAPT | P0 | 3h | `configs/classification.yaml` + `src/data/classify/taxonomy.py` |
| `framework/src/scraper/indicator_matrix.py` (7 phases × 11 ILO indicators) | REUSE | P0 | 30m | already under grading |
| — | REWRITE | P0 | 6h | `src/data/classify/rule_based.py` |
| — | REWRITE | P1 | 4h | `src/data/classify/embedding.py` |
| — | REWRITE | P1 | 3h | `src/data/classify/llm_classifier.py` |
| — | REWRITE | P0 | 2h | `src/data/classify/ensemble.py` |

---

## 6. Anonymization (architecture §7)

**This is a new gate with no existing counterpart.** The existing framework
has anonymization logic scattered through the scraper seed modules, but
nothing centralized. This is a **P0 build from scratch**.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| — | REWRITE (use `presidio-analyzer`) | P0 | 6h | `src/data/anon/detectors/presidio_detector.py` |
| — | REWRITE | P0 | 3h | `src/data/anon/detectors/regex_detector.py` |
| — | REWRITE | P1 | 4h | `src/data/anon/detectors/ner_detector.py` |
| — | REWRITE | P0 | 3h | `src/data/anon/strategies/redactor.py`, `tokenizer.py`, `generalizer.py`, `dropper.py` |
| — | REWRITE | P0 | 2h | `src/data/anon/verifier.py` |
| — | REWRITE | P0 | 2h | `src/data/anon/audit.py` |
| — | REWRITE | P0 | 1h | `src/data/anon/quarantine.py` |

**Dependency to add**: `presidio-analyzer>=2.2.0`, `presidio-anonymizer>=2.2.0`.

---

## 7. Prompt store and generators (architecture §8)

The framework's generator system (16 domain generators, 5K LOC) is a direct
match for our `TemplateGenerator` and `FromCaseGenerator`. The benchmark's
`test_generation/` (18.9K LOC, largest subsystem) has richer templates but
uses the older models.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/generators/base_generator.py` (174 LOC) | REUSE | P0 | 30m | `src/prompts/generator/base.py` |
| `framework/src/generators/moral_religious_framing_generator.py` | REUSE | P0 | 15m | `src/prompts/generator/moral_religious.py` |
| `framework/src/generators/coercion_manipulation_generator.py` | REUSE | P0 | 15m | `src/prompts/generator/coercion.py` |
| `framework/src/generators/supply_chain_opacity_generator.py` | REUSE | P1 | 15m | `src/prompts/generator/supply_chain.py` |
| `framework/src/generators/financial_obfuscation_generator.py` | REUSE | P0 | 15m | `src/prompts/generator/financial.py` |
| `framework/src/generators/surveillance_control_generator.py` | REUSE | P1 | 15m | `src/prompts/generator/surveillance.py` |
| `framework/src/generators/law_circumvention_tool_generator.py` | REUSE | P0 | 15m | `src/prompts/generator/regulatory.py` |
| `framework/src/generators/exploitation_platform_generator.py` | REUSE | P1 | 15m | `src/prompts/generator/platform.py` |
| `framework/src/generators/historical_precedent_generator.py` | REUSE | P0 | 15m | `src/prompts/generator/from_case.py` |
| `framework/src/generators/corridors.py` | REUSE | P0 | 30m | `src/prompts/generator/corridors.py` |
| `benchmark/test_generators/mega_variation_generator.py` (894 LOC) | ADAPT | P1 | 2h | `src/prompts/generator/mega_variations.py` |
| `benchmark/test_generators/hybrid_exploitation_generator.py` (792 LOC) | ADAPT | P1 | 2h | `src/prompts/generator/hybrid.py` |
| `benchmark/src/test_generation/persona_generator.py` | ADAPT | P2 | 1h | `src/prompts/generator/persona.py` |
| `benchmark/src/test_generation/iterative_generator.py` | ADAPT | P2 | 2h | `src/prompts/generator/iterative.py` |
| — | REWRITE | P0 | 2h | `src/prompts/store.py` (SQLite CRUD) |

---

## 8. Adversarial harness (architecture §9)

The framework's prompt injection system is the crown jewel: **631 mutators
across 55 categories, 44K LOC**, plus 126 attack chains and a registry
pattern that matches our `AttackRegistry` almost exactly. Rather than
cherry-pick individual mutators, **import the entire module as a sidecar
dependency**.

### Strategy: sidecar import, not copy-paste

Because the framework is MIT-licensed and the author is the user, we can
add a dependency entry in `pyproject.toml` like:

```toml
[tool.poetry.dependencies]
llm-safety-framework = {path = "../_reference/framework", develop = true}
```

Then `import llm_safety_framework.prompt_injection as mutators` inside
`src/attacks/strategies/__init__.py`. We wrap the framework's mutator
registry with our `AttackRegistry.register(...)` calls, so the rest of
gemma4_comp doesn't know the difference.

### Which mutator modules to wire up first

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/prompt_injection/__init__.py` (337 LOC, registry) | REUSE via sidecar | P0 | 30m | wrapped in `src/attacks/registry.py` |
| `framework/src/prompt_injection/metadata_schema.py` | REUSE | P0 | 15m | `src/schemas/attacks.py` |
| `framework/src/prompt_injection/output_evasion.py` (3,953 LOC, 109 mutators) | REUSE via sidecar | P0 | 30m | `src/attacks/strategies/output_evasion.py` (thin wrapper) |
| `framework/src/prompt_injection/named_jailbreaks.py` (976 LOC, 15 jailbreaks) | REUSE via sidecar | P1 | 30m | wrapper |
| `framework/src/prompt_injection/step_decomposition.py` (1,112 LOC, 20 mutators) | REUSE via sidecar | P1 | 30m | wrapper |
| `framework/src/prompt_injection/structural_injection.py` (760 LOC, 10 mutators) | REUSE via sidecar | P0 | 30m | wrapper |
| `framework/src/prompt_injection/advanced_obfuscation.py` (842 LOC, 10 mutators) | REUSE via sidecar | P1 | 30m | wrapper |
| `framework/src/prompt_injection/multilingual_attack.py` (818 LOC, 5 language mutators) | REUSE via sidecar | P0 | 30m | wrapper |
| `framework/src/prompt_injection/moral_religious_framing_generator.py` | REUSE via sidecar | P0 | 30m | wrapper |
| `framework/src/prompt_injection/legal_persona.py` (627 LOC, 10 mutators) | REUSE via sidecar | P0 | 30m | wrapper |
| `framework/src/prompt_injection/authority_exploit.py` (637 LOC, 10 mutators) | REUSE via sidecar | P0 | 30m | wrapper |
| `framework/src/prompt_injection/instruction_override.py` (5 mutators) | REUSE via sidecar | P0 | 15m | wrapper |
| `framework/src/prompt_injection/social_engineering.py` (6 mutators) | REUSE via sidecar | P0 | 15m | wrapper |
| `framework/src/prompt_injection/combination_engine.py` (1,928 LOC, 21 compositions) | REUSE via sidecar | P1 | 1h | `src/attacks/combinator.py` |
| `framework/src/prompt_injection/coverage.py` (391 LOC) | REUSE | P1 | 30m | `src/attacks/coverage.py` |
| `framework/src/prompt_injection/fitness.py` (315 LOC) | REUSE | P2 | 30m | `src/attacks/fitness.py` |
| `framework/src/prompt_injection/attack_templates.py` (313 LOC, YAML) | REUSE | P1 | 30m | `configs/attacks.yaml` + loader |
| **The other ~40 mutator modules** | REUSE via sidecar (lazy-register) | P2 | 2h | `src/attacks/strategies/*` |

### Multi-turn chains

The framework's `chain_detection` directory has 126 chains across 16
categories. The chain test engine already has 5 test modes (direct,
incremental, contrastive, business, advisory) and a 5-grade rubric.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/chain_detection/chain_registry.py` (148 LOC) | REUSE | P0 | 30m | `src/attacks/chains/registry.py` |
| `framework/src/chain_detection/test_engine.py` (312 LOC) | ADAPT | P0 | 2h | `src/attacks/chains/engine.py` |
| `framework/src/chain_detection/prompt_builder.py` (287 LOC, 5 modes) | REUSE | P0 | 30m | `src/attacks/chains/prompt_builder.py` |
| `framework/src/chain_detection/scorer.py` (289 LOC) | ADAPT | P0 | 1h | `src/grading/chain_scorer.py` |
| `framework/src/chain_detection/models.py` (156 LOC, Pydantic v2) | REUSE | P0 | 15m | merge into `src/schemas/attacks.py` |
| `framework/src/chain_detection/seeds/` (21 modules, 150+ chains) | REUSE as-is | P0 | 0 | import path only |

### Intelligent attack (Phases 1-7)

This is the most advanced part of the framework — 49 attack classes across
embedding-space probing, Bayesian exploration, curvature analysis, Shapley
attribution, trust-region methods, etc. **Too heavy for hackathon scope.**
Reference only.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/intelligent_attack/embedder.py` + `feature_extractor.py` + `space_analyzer.py` (620 LOC) | REUSE | P2 | 1h | `src/attacks/intelligent/embedding.py` |
| Everything else in `intelligent_attack/` (23K LOC across 49 classes) | REFERENCE | — | 0 | docs only |

---

## 9. Grading and scoring (architecture §10)

The framework's grading infrastructure is the best-shaped of any piece for
direct reuse. The benchmark's evaluation module has complementary rubrics
(FATF, TIPS-style) that are worth pulling in.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/evaluation/base.py` (178 LOC, Evaluator base) | REUSE | P0 | 30m | `src/grading/base.py` (already has protocol) |
| `framework/src/evaluation/llm_judge.py` (234 LOC) | REUSE | P0 | 1h | `src/grading/llm_judge.py` |
| `framework/src/evaluation/pattern_evaluator.py` (289 LOC, regex+keyword) | REUSE | P0 | 1h | `src/grading/rule_based.py` |
| `framework/src/chain_detection/scorer.py` | ADAPT | P0 | (see §8) | `src/grading/chain_scorer.py` |
| `framework/src/dimensional_matrix/scoring.py` (289 LOC, 45 dims) | REFERENCE | P2 | — | too heavy |
| `framework/src/dimensional_matrix/debate_judge.py` (301 LOC) | ADAPT | P1 | 2h | `src/grading/llm_judge_debate.py` |
| `benchmark/src/evaluation/graded_evaluator.py` | ADAPT | P0 | 2h | `src/grading/hybrid.py` |
| `benchmark/src/evaluation/multi_layer_evaluator.py` | REFERENCE | P1 | — | inform hybrid design |
| `benchmark/src/evaluation/fatf_risk_rating.py` | REUSE | P1 | 30m | `src/grading/indicators_fatf.py` |
| `benchmark/src/evaluation/tips_style_rating.py` | REUSE | P1 | 30m | `src/grading/indicators_tips.py` |
| `benchmark/src/evaluation/rubrics/` (YAML) | REUSE | P0 | 30m | `configs/grading/rubrics/` |

---

## 10. Autonomous agents (architecture new section)

The framework ships 12 autonomous research agents + 1 coordinator, ~4,424
LOC. For the hackathon, we only need **3 of them**:

1. **`coverage_gap_agent`** — identifies under-tested scenarios, drives the
   next training iteration
2. **`technique_evolution_agent`** — genetic mutation of attack chains,
   powers evolutionary training data generation
3. **`model_benchmark_agent`** — runs standardized safety benchmarks
   against candidate models, slots directly into our eval harness

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/core/base_agent.py` (307 LOC, HarnessAgent, AgentRole) | REUSE | P0 | 30m | `src/agents/base.py` (NEW subpackage) |
| `framework/src/research/agents/coordinator.py` (369 LOC) | ADAPT | P1 | 2h | `src/agents/coordinator.py` |
| `framework/src/research/agents/coverage_gap_agent.py` (344 LOC) | ADAPT | P1 | 2h | `src/agents/coverage_gap.py` |
| `framework/src/research/agents/technique_evolution_agent.py` (294 LOC) | ADAPT | P1 | 2h | `src/agents/technique_evolution.py` |
| `framework/src/research/agents/model_benchmark_agent.py` (285 LOC) | ADAPT | P1 | 2h | `src/agents/model_benchmark.py` |
| `framework/src/research/agents/attack_surface_evolution_agent.py` (406 LOC) | REFERENCE | P2 | — | — |
| `framework/src/research/agents/technique_integration_agent.py` (360 LOC) | REFERENCE | P2 | — | — |
| `framework/src/research/agents/cross_pollination_agent.py` (252 LOC) | REFERENCE | P2 | — | — |
| `framework/src/research/agents/embedding_research_agent.py` (350 LOC) | REFERENCE | P2 | — | — |
| `framework/src/research/agents/enforcement_agent.py` (263 LOC) | REFERENCE | P2 | — | — |
| `framework/src/research/agents/ethics_boundary_agent.py` (305 LOC) | REUSE (wrap as a pre-publish gate) | P1 | 1h | `src/agents/ethics_gate.py` |
| `framework/src/research/agents/jurisdiction_agent.py` (284 LOC) | REFERENCE | P2 | — | — |
| `framework/src/research/agents/financial_crime_agent.py` (307 LOC) | REFERENCE | P2 | — | — |
| `framework/src/research/agents/github_library_agent.py` (308 LOC) | REFERENCE | P2 | — | — |
| `framework/src/research/news_monitor.py` (184 LOC) | REFERENCE | P2 | — | — |
| `benchmark/src/harness/agents/base_agent.py` (319 LOC) | REFERENCE | P2 | — | older version, framework wins |
| `benchmark/src/harness/agents/attack_generator.py` (355 LOC) | ADAPT | P1 | 2h | `src/agents/attack_generator.py` |
| `benchmark/src/autonomous/continuous_learner.py` (589 LOC) | REFERENCE | P2 | — | too ambitious for 5 weeks |
| `benchmark/autonomous_14day_research_engine.py` (885 LOC) | REFERENCE | P2 | — | — |
| `benchmark/autonomous_research_coordinator.py` (791 LOC) | REFERENCE | P2 | — | superseded by framework's coordinator |

**New subpackage to add:** `src/agents/`. Not in the current architecture
doc — add a §9b section.

---

## 11. LLM provider abstraction

Both sources have a provider abstraction. The **benchmark's is richer**
(7 providers including claude-cli and free providers) but older. The
**framework's is cleaner** (UnifiedAPIClient with Pydantic v2). Use the
framework's as the base and pull in the benchmark's extra providers.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/api_client.py` (254 LOC, UnifiedAPIClient) | ADAPT | P0 | 2h | `src/inference/providers/base.py` + `unified.py` |
| `benchmark/src/llm_engine/providers/anthropic_provider.py` (144 LOC) | ADAPT | P0 | 30m | `src/inference/providers/anthropic.py` |
| `benchmark/src/llm_engine/providers/openai_provider.py` (153 LOC) | ADAPT | P0 | 30m | `src/inference/providers/openai.py` |
| `benchmark/src/llm_engine/providers/mistral_provider.py` (175 LOC) | ADAPT | P1 | 30m | `src/inference/providers/mistral.py` |
| `benchmark/src/llm_engine/providers/ollama_provider.py` (233 LOC) | ADAPT | P1 | 30m | `src/inference/providers/ollama.py` |
| `benchmark/src/llm_engine/providers/free_providers.py` (532 LOC) | REFERENCE | P2 | — | — |
| `benchmark/src/llm_engine/providers/claude_cli_provider.py` (661 LOC) | REFERENCE | P2 | — | — |
| `benchmark/src/llm_engine/rate_limiter.py` | REUSE | P1 | 30m | `src/inference/providers/rate_limiter.py` |
| `benchmark/src/llm_engine/response_cache.py` | REUSE | P1 | 30m | `src/inference/providers/cache.py` |

**Note**: these providers are for **baseline judges** (GPT-4o, Claude,
Mistral, etc.) used in the eval harness. Our fine-tuned Gemma judge uses
a different runtime (llama.cpp) entirely.

---

## 12. Integrations with external red-team frameworks

The framework has adapters for five external tools: `garak`, `PyRIT`,
`HarmBench`, `TextAttack`, `EasyJailbreak`. **Not needed for the hackathon**
— our scope is migrant-worker safety, not general jailbreaking. Reference
only.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/integrations/garak_adapter.py` | REFERENCE | P2 | — | — |
| `framework/src/integrations/pyrit_adapter.py` | REFERENCE | P2 | — | — |
| `framework/src/integrations/harmbench_adapter.py` (18 attacks) | REFERENCE | P2 | — | — |
| `framework/src/integrations/textattack_adapter.py` (17 transforms) | REFERENCE | P2 | — | — |
| `framework/src/integrations/easyjailbreak_adapter.py` (12 methods) | REFERENCE | P2 | — | — |
| `framework/src/integrations/research_apis.py` (Semantic Scholar, arXiv, SSRN, PubMed, OpenAlex) | REUSE | P1 | 1h | `src/docs/research_apis.py` |

---

## 13. Training pipeline (architecture §11)

**All new.** The existing framework has `src/training/` with SafetyEvaluator
+ TrainingDataExporter + 4 framework exporters (HF, Axolotl, etc.), but none
of them target Unsloth specifically. We build fresh.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/training/safety_evaluator.py` | REFERENCE | P1 | — | inform `src/eval/` design |
| `framework/src/training/finetune_config.py` (4 frameworks) | REFERENCE | P2 | — | — |
| `framework/src/training/red_team_generator.py` (4 backends) | REFERENCE | P2 | — | — |
| `framework/src/local_models/model_registry.py` (12 curated models) | REFERENCE | P2 | — | — |
| `framework/src/local_models/trainer.py` (LoRA/QLoRA) | REFERENCE | P1 | — | inform our finetune.py |
| — | REWRITE | P0 | 1 day | `src/training/prepare.py` |
| — | REWRITE | P0 | 1 day | `src/training/finetune.py` |
| — | REWRITE | P0 | 4h | `src/training/dataset.py` (Unsloth chat formatter) |
| — | REWRITE | P0 | 2h | `src/training/splits.py` (hold-out by case_id) |
| — | REWRITE | P0 | 2h | `src/training/callbacks.py` |

---

## 14. Export and inference (architecture §12, §13)

**All new.** The framework has no GGUF or LiteRT export. Build from scratch.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| — | REWRITE | P0 | 2h | `src/export/merge.py` |
| — | REWRITE | P0 | 4h | `src/export/to_gguf.py` |
| — | REWRITE | P0 | 4h | `src/export/model_card.py` |
| — | REWRITE | P1 | 4h | `src/export/publish.py` (HF Hub) |
| — | REWRITE | P2 | 1 day | `src/export/to_litert.py` |
| — | REWRITE | P0 | 4h | `src/inference/llama_cpp.py` |
| — | REWRITE | P1 | 2h | `src/inference/transformers.py` (baseline) |
| — | REWRITE | P1 | 2h | `src/inference/prompt_template.py` |

---

## 15. Evaluation harness (architecture §14)

Reuses the grading protocol + LLM provider abstraction. The framework's
benchmark infrastructure is a good pattern to mimic.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/chain_detection/test_engine.py` | ADAPT | P0 | (see §8) | `src/eval/runner.py` |
| `framework/src/agent_tools/` (20 subpackages for agent improvement) | REFERENCE | P2 | — | — |
| `benchmark/src/harness/orchestrator.py` (710 LOC) | REFERENCE | P1 | — | inform `src/eval/runner.py` |
| `benchmark/src/analysis/advanced_failure_analysis.py` | ADAPT | P1 | 2h | `src/eval/failure_analysis.py` |
| `benchmark/src/analysis/vulnerability_analyzer.py` | ADAPT | P1 | 2h | `src/eval/vulnerability.py` |
| `benchmark/src/reporting/generators/interactive_html_report.py` (2,225 LOC) | REFERENCE | P2 | — | our reports are markdown |
| `benchmark/src/reporting/generators/markdown_generator.py` (207 LOC) | ADAPT | P0 | 1h | `src/eval/reports.py` |
| `benchmark/src/reporting/visualizations/charts.py` (246 LOC) | REUSE | P1 | 1h | `src/eval/plots.py` |

---

## 16. Demo application (architecture §15)

**All new.** Keep it tiny for the hackathon — one FastAPI app, one page.
Reference the framework's FastAPI + plugin pattern but don't copy the
18-plugin dashboard (too heavy).

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/web/app.py` | REFERENCE | — | — | pattern only |
| `framework/src/web/plugin_registry.py` | REFERENCE | P2 | — | — |
| `framework/src/web/plugins/chain_detection/` | REFERENCE | P2 | — | — |
| — | REWRITE | P0 | 1 day | `src/demo/app.py`, `routes.py`, `templates/` |

---

## 17. Tests and test infrastructure (architecture §18)

The framework has the most comprehensive test suite in the entire ecosystem:
**59 test files, 7,178 LOC, full Playwright E2E with Page Object Model.**
Copy the fixtures and the E2E structure; rewrite specific tests against our
own modules.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/tests/conftest.py` (391 LOC, fixtures, mocks, DB setup) | ADAPT | P0 | 2h | `tests/conftest.py` |
| `framework/tests/helpers.py` (181 LOC) | REUSE | P0 | 30m | `tests/helpers.py` |
| `framework/tests/e2e/conftest.py` (Playwright fixtures) | REUSE | P1 | 30m | `tests/e2e/conftest.py` |
| `framework/tests/e2e/pages/` (Page Object Model, 7 files) | ADAPT | P1 | 2h | `tests/e2e/pages/` (rewrite for our demo UI) |
| `framework/tests/test_scraper.py` (799 LOC) | REFERENCE | P1 | — | model for our source tests |
| `framework/tests/test_chain_detection.py` (485 LOC) | REFERENCE | P0 | — | model for our chain tests |
| `framework/tests/test_prompt_injection.py` (1,003 LOC) | REFERENCE | P0 | — | model for our attack tests |
| `framework/tests/test_training_v6.py` (1,627 LOC, synthetic dataset gen) | REFERENCE | P1 | — | model for our training prep tests |
| `framework/tests/test_api_client.py` (240 LOC) | ADAPT | P0 | 1h | `tests/unit/inference/test_providers.py` |
| `framework/tests/test_base_agent.py` (214 LOC) | ADAPT | P1 | 1h | `tests/unit/agents/test_base.py` |
| `framework/tests/test_research_agents_v2.py` (500 LOC) | ADAPT | P1 | 2h | `tests/integration/test_agents.py` |
| `benchmark/tests/conftest.py` (140 LOC) | REFERENCE | — | — | framework version wins |
| `benchmark/tests/test_models.py` (206 LOC) | REFERENCE | — | — | schemas already covered |
| — | REWRITE | P0 | 4h | unit tests for each schema |
| — | REWRITE | P0 | 4h | integration tests for the data pipeline |

### E2E test layout (lifted from framework)

```
tests/e2e/
├── conftest.py              # Playwright browser fixture
├── pages/
│   ├── base_page.py
│   ├── index_page.py        # demo landing page
│   ├── evaluate_page.py     # evaluator form
│   └── result_page.py       # result display
├── test_smoke.py            # healthcheck + basic eval flow
├── test_evaluate.py         # happy path + edge cases
└── test_rate_limit.py       # abuse mitigation
```

---

## 18. CLI (architecture §2)

Our scaffold already has `src/cli.py` with typer stubs. The framework's
CLI is nearly identical in pattern; the benchmark's is 1,987 lines and has
richer ingest/generate/run/report commands. Pull selected patterns from
both.

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/src/cli.py` (347 LOC, typer) | REFERENCE | — | — | pattern already in place |
| `benchmark/src/cli.py` (1,987 LOC) | REFERENCE | P1 | — | mine for subcommand structure |
| `benchmark/production_test_pipeline.py` (568 LOC) | REFERENCE | P1 | — | pattern for full-pipeline command |

---

## 19. Configuration

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/pyproject.toml` (v5.2.0, 221 LOC) | ADAPT | P0 | 1h | `pyproject.toml` (new) |
| `framework/Makefile` (13 targets) | ADAPT | P0 | 30m | `Makefile` (new) |
| `framework/.env.template` (99 LOC, 11 provider keys) | ADAPT | P0 | 15m | `.env.template` (new) |
| `framework/docker-compose.yml` (158 LOC) | REFERENCE | P2 | — | — |
| `framework/Dockerfile` (80 LOC, multi-stage) | ADAPT | P1 | 1h | `Dockerfile` (for demo deployment) |
| `framework/.pre-commit-config.yaml` | REUSE | P1 | 15m | `.pre-commit-config.yaml` |
| `framework/.github/workflows/ci.yml` | ADAPT | P1 | 30m | `.github/workflows/ci.yml` |

---

## 20. Documentation

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `framework/docs/CLAUDE.md` (750 LOC) | REFERENCE | — | — | already read, distilled into our CLAUDE.md |
| `framework/docs/ARCHITECTURE.md` (412 LOC) | REFERENCE | — | — | distilled into our `docs/architecture.md` |
| `framework/docs/ATTACK_TAXONOMY.md` (456 LOC, 55 categories) | REUSE | P0 | 0 | `_reference/framework/docs/` (link from integration plan) |
| `framework/docs/CHAIN_DETECTION.md` (389 LOC) | REUSE | P0 | 0 | same |
| `framework/docs/PROMPT_INJECTION.md` (512 LOC, 631 mutators) | REUSE | P0 | 0 | same |
| `framework/docs/DIMENSIONAL_MATRIX.md` (467 LOC) | REUSE | P2 | 0 | same |
| `framework/docs/MIGRATION_CORRIDORS.md` (345 LOC, 174 routes) | REUSE | P0 | 0 | same |
| `framework/docs/TEST_GENERATION.md` (234 LOC) | REUSE | P1 | 0 | same |
| `benchmark/reference_python_notebooks/llms-support-human-trafficking.ipynb` (5.5 MB) | REUSE | P0 | 0 | already in `_reference/trafficking_llm_benchmark/reference_python_notebooks/` |

---

## 21. Legacy Kaggle tests (from benchmark)

The benchmark has `legacy_kaggle_tests/` with 11 JSON files containing
red-team test cases from the prior gpt-oss-20b Red-Teaming Challenge. These
are Taylor's own prior work and are **directly reusable as evaluation
baselines** (what the existing judge scored on the previous competition).

| Source | Decision | Priority | Effort | Target |
|---|---|---|---|---|
| `benchmark/legacy_kaggle_tests/my_red_team_tests.json` (primary, 5K+ cases) | REUSE | P0 | 1h | `data/baselines/gpt_oss_red_team.jsonl` (after schema mapping) |
| `benchmark/legacy_kaggle_tests/*.json` (variant filtered sets) | REUSE | P1 | 30m | same |
| `benchmark/test_runners/multi_entity_test_runner.py` (14,349 LOC!) | REFERENCE | P2 | — | too large, use its patterns only |

---

## 22. Priority-ordered execution plan

### P0 (blocking for submission) — total ~10 days

Week 1 (Apr 14-20): foundation
- [ ] Wire framework as sidecar dependency (pyproject.toml path include)
- [ ] Adapt `framework/src/core/base_agent.py` + `api_specification.py` into our schemas
- [ ] Copy framework taxonomy (corridors, ILO indicators) into `configs/classification.yaml`
- [ ] Build `src/data/sources/local_sqlite.py` and `local_json.py` against the benchmark DB
- [ ] Build `src/data/ingest/{normalizer,deduper,staging}.py`
- [ ] Build `src/data/classify/rule_based.py` + `ensemble.py` using the framework's `indicator_matrix.py`
- [ ] **Build the anonymization gate from scratch** — detectors, strategies, verifier, audit

Week 2 (Apr 21-27): model pipeline
- [ ] Build `src/prompts/store.py` SQLite CRUD
- [ ] Wrap framework generators as `src/prompts/generator/*`
- [ ] Build `src/attacks/registry.py` wrapper around the framework's mutator registry
- [ ] Wire `framework/src/chain_detection` as our attack chain engine
- [ ] Build `src/grading/{rule_based,llm_judge,hybrid}.py` (adapt framework `evaluation/`)
- [ ] Build `src/training/prepare.py` — clean DB → Unsloth JSONL
- [ ] Build `src/training/finetune.py` — Unsloth + LoRA loop, small smoke run

Week 3 (Apr 28 - May 4): model + demo
- [ ] Full fine-tune run (4-6h on A100)
- [ ] Build `src/export/merge.py` + `to_gguf.py`
- [ ] Build `src/inference/llama_cpp.py` runtime
- [ ] Build `src/eval/runner.py` + baselines (GPT-4o-mini, Claude, stock Gemma)
- [ ] Generate initial eval report
- [ ] Build `src/demo/app.py` FastAPI + minimal UI

### P1 (strong nice-to-have) — total ~5 days

Week 4 (May 5-11): polish + evolution
- [ ] Wire 3 autonomous agents (coverage_gap, technique_evolution, model_benchmark)
- [ ] Second iteration fine-tune, informed by coverage_gap agent's gap report
- [ ] Adapt framework Playwright E2E tests for our demo
- [ ] Deploy live demo to HF Spaces
- [ ] Adapt benchmark's HTML report generator for the writeup artifacts
- [ ] Pull in FATF and TIPS indicator rubrics
- [ ] Build `src/export/publish.py` (HF Hub upload)

### P2 (stretch) — total ~5 days

- [ ] `src/export/to_litert.py` for mobile demo
- [ ] LiteRT Android demo app
- [ ] More mutator wrappers (beyond the initial 12)
- [ ] `intelligent_attack/embedder.py` wrapper for advanced eval
- [ ] Multi-turn chain evaluation in the demo
- [ ] Multilingual attack evaluation (Tagalog, Nepali, Bahasa, Arabic)
- [ ] Claude Code hooks / scheduled runs for continuous improvement

---

## 23. New subpackages to add to `src/`

Beyond the scaffold already created, these subpackages are implied by the
integration plan and should be added:

```
src/
├── agents/                   # NEW - autonomous research agents (§10)
│   ├── __init__.py
│   ├── base.py               # adapted from framework/src/core/base_agent.py
│   ├── coordinator.py
│   ├── coverage_gap.py
│   ├── technique_evolution.py
│   ├── model_benchmark.py
│   ├── attack_generator.py   # from benchmark
│   └── ethics_gate.py        # pre-publish gate
│
├── data/
│   └── sources/
│       ├── browser.py        # from framework/scraper
│       ├── fetcher.py
│       ├── extractor.py
│       ├── stealth.py
│       ├── proxy.py
│       ├── politeness.py
│       ├── retry.py
│       ├── scheduler.py
│       ├── health.py
│       ├── feed.py
│       ├── change_detection.py
│       └── seeds/
│           ├── __init__.py
│           ├── loader.py     # from framework/scraper/seed_loader.py
│           └── pruner.py     # from framework/scraper/seed_pruner.py
│
├── inference/
│   └── providers/            # NEW subpackage for baseline judges
│       ├── __init__.py
│       ├── base.py           # adapted from framework UnifiedAPIClient
│       ├── unified.py
│       ├── openai.py
│       ├── anthropic.py
│       ├── mistral.py
│       ├── ollama.py
│       ├── rate_limiter.py
│       └── cache.py
│
└── attacks/
    ├── combinator.py         # from framework/prompt_injection/combination_engine.py
    ├── coverage.py
    ├── fitness.py
    └── intelligent/          # NEW - advanced embedding-space attacks (stretch)
        ├── __init__.py
        └── embedding.py
```

I'll update `docs/architecture.md` and re-run `scripts/scaffold.py` to add
these. Or rather, a new `scripts/scaffold_v2.py` that is additive and
idempotent.

---

## 24. Open questions

1. **Sidecar vs. copy-paste for framework mutators?** Going sidecar means
   `pip install -e _reference/framework` and dynamic imports. Going
   copy-paste means we commit our own copies and diverge from upstream.
   Sidecar is lighter but adds a runtime dependency; copy-paste is
   self-contained but means we lose future upstream updates.
   **Recommendation: sidecar for now**, with a switch to copy-paste if the
   hackathon repo needs to be truly self-contained.

2. **Which 3 agents** do we actually wire up? The plan lists
   `coverage_gap`, `technique_evolution`, `model_benchmark`. This is
   bikeshed-level but needs confirmation before week-2 work.

3. **Live demo host?** HF Spaces is the default assumption. Alternatives:
   Cloud Run, Modal, Render. HF Spaces matches the audience best.

4. **Legacy Kaggle test baseline** — do we evaluate our fine-tuned judge
   against the prior gpt-oss-20b red-team tests as a baseline, to claim
   "generalizes beyond the training distribution"? I'd argue yes — it's
   the strongest external-validity story we can tell in the video.

5. **Anonymization policy for NGO partner data** — none for this hackathon
   (§19.6 of the architecture). Confirmed?

6. **E2B vs E4B** — still pending from the original planning session.
   Leaning E4B for quality, but E2B fits more devices.

7. **Unsloth experience** — still pending.
