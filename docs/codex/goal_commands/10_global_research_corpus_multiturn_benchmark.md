# Global research corpus and multi-turn benchmark expansion

Use this when Taylor wants the next agent to run for many hours and build a
large, source-profiled research corpus, not merely add a handful of new facts or
prompts.

This goal extends the major-case work in
`docs/codex/goal_commands/09_major_case_research_benchmark_expansion.md`.
It should be run after or alongside that goal, but it has a larger completion
standard:

- thousands of public-source search results considered, with a resumable search
  frontier and source-cluster rotation
- at least 1,000 safe source-profile documents created or refreshed
- public sources profiled for facts, jurisdictions, sectors, indicators,
  camouflage patterns, evidentiary gaps, and benchmark use
- multi-turn prompt conversations, not only single-turn prompts
- hybrid scenario mixes combining private aggregate casefile patterns, public
  case law, regulator guidance, NGO typologies, financial-crime indicators,
  platform-safety framing, and adversarial/evasion traps
- continuous improvement loops that use coverage gaps, failed tests, and source
  quality scores to choose the next batch without asking Taylor

The private files in `C:\projects\major_cases` remain pattern inspiration only.
They are never copied, quoted, uploaded, pasted into search, or exposed to remote
services.

## Copy-paste `/goal`

```text
/goal In <repo-root>, work on master without switching branches and follow docs/codex/goal_commands/10_global_research_corpus_multiturn_benchmark.md as a long no-stop autonomous research and benchmark capability run. Search broadly across public web sources and nontraditional sources, create or refresh at least 1,000 safe source-profile documents, maintain a resumable search frontier, extract source-grounded facts and verification notes, expand exploitation/camouflage dimensions, create single-turn and multi-turn benchmark prompts, build hybrid scenario mixes across public case law and private aggregate patterns from C:\projects\major_cases, regenerate artifacts, add tests, run PII/leak checks and repo validation gates, commit and push coherent slices, then continue using coverage gaps, failed tests, and source-cluster gaps to choose the next batch without asking Taylor. Escalate to Taylor only for PII/secrets risk, destructive actions, credentials, or repeated unrecoverable validation blockers. Do not stop after a plan, one scrape, one country, one prompt batch, one commit, or one successful validation pass.
```

## Mission

Build a larger research-backed capability layer for DueCare that can keep
improving over many hours:

- source-profile 1,000+ public documents
- extract paraphrased, source-grounded knowledge facts
- expand scoring dimensions and response skills
- create longer and more realistic single-turn prompts
- create multi-turn prompt conversations with state, escalation, correction,
  safety, refusal, evidence-preservation, and jurisdiction-uncertainty moves
- create hybrid scenarios that combine several public and private-aggregate
  signals without leaking private evidence
- add tests that prove determinism, source metadata, PII safety, and prompt
  structure
- leave a machine-readable resume state so the next agent can continue source
  collection, fact extraction, prompt generation, and validation without reading
  the whole chat history
- make every loop improve at least one of: source coverage, facts, dimensions,
  prompt quality, conversation quality, test strength, leak safety, or benchmark
  integration

Optimize for capability, coverage, and grounded examples. Avoid cleanup-only
work unless it is required for safe generation or verification.

## Runtime Target

Target runtime: 8-24 hours of actual work if resources are available.

The goal may run longer when resources remain and high-value coverage gaps are
still visible. A green test run is a checkpoint, not a stopping reason.

This is not complete after:

- writing this goal file
- adding a plan
- adding a few search results
- profiling fewer than 1,000 public documents unless blocked
- adding only single-turn prompts
- adding only one jurisdiction
- running only one extractor pass
- committing only docs
- asking Taylor what to do next when the next source cluster, test, or artifact
  can be selected from the coverage report

Work in repeated loops and push coherent slices. A loop means:

1. search or mine a defined source cluster
2. profile sources into safe structured documents
3. extract facts, indicators, dimensions, or prompt seeds
4. generate or update benchmark artifacts
5. run focused tests and leak checks
6. commit and push
7. continue to the next highest-value gap

Minimum loop target:

- 3+ research/profile loops
- 2+ fact/dimension/prompt generation loops
- 1+ multi-turn conversation loop
- 1+ final verification loop

If quota, network, credentials, or host stability stops the long run, preserve a
clear resume state and commit/push the coherent verified slice.

## Autonomous Operating Contract

Do not ask Taylor to choose:

- which jurisdiction to search next
- which source cluster to prioritize next
- whether to create profiles, facts, dimensions, prompts, tests, or coverage
  reports
- whether to continue after a successful batch
- whether to regenerate artifacts after generator changes
- whether to run the relevant validation gates

Use these defaults:

- Prefer primary/official/court sources first.
- When a source cluster stalls, rotate to the next source cluster.
- When a jurisdiction is saturated, move to the next under-covered jurisdiction.
- When source profiles exceed fact extraction capacity, extract from high-tier
  and high-relevance profiles first.
- When prompt count is high but dimensions are thin, add dimensions and tests.
- When dimensions are high but prompts are thin, generate more single-turn and
  multi-turn prompts.
- When tests fail, fix the smallest responsible implementation or fixture issue.
- When validation fails from environment breakage, retry with the known working
  local test environment and record the environment failure.
- When a source is blocked by paywall, login, JavaScript rendering, robots, or
  rate limit, record it as `rejected` or `needs_review` and move on.

Ask Taylor only for:

- destructive actions
- credentials or paid access
- permission to use a remote model with private data, which should normally be
  refused and replaced with redacted/synthetic input
- unresolved PII/secrets risk
- a validation failure that repeated after three genuine fix attempts and needs
  a product choice

## Continuous Improvement Engine

Every loop should update machine-readable run state, for example:

- `configs/duecare/benchmarks/major_case_patterns/research_frontier.json`
- `configs/duecare/benchmarks/major_case_patterns/research_run_state.json`
- `configs/duecare/benchmarks/major_case_patterns/source_profile_coverage.json`
- `configs/duecare/benchmarks/major_case_patterns/conversation_manifest.json`

The run state should include:

- source clusters searched
- query templates used
- candidate URLs considered
- candidate URLs rejected and why
- source profiles created/refreshed
- profiles pending fact extraction
- profiles already fact-extracted
- jurisdictions, sectors, behavior families, camouflage families, and response
  skills covered or under-covered
- prompt and conversation families generated
- tests added or strengthened
- validations run and results
- next 20 autonomous actions

At the end of each loop, choose the next action by priority:

1. Fix any PII/secrets/leak issue.
2. Fix any failing focused test caused by current changes.
3. Regenerate artifacts when generator logic changed.
4. Fill required target gaps: 1,000 source profiles, 300 extracted profiles,
   500 conversations, 1,000 hybrid prompts.
5. Fill jurisdiction and sector coverage gaps.
6. Add tests for any new pattern family lacking tests.
7. Add source facts for high-tier profiles without facts.
8. Improve conversation/hybrid prompts for under-tested response skills.
9. Run validation gates and commit/push.
10. Continue with the next highest-value gap.

## Read First

1. `AGENTS.md`
2. `docs/codex/README.md`
3. `docs/codex/00_do_not_break.md`
4. `docs/codex/00_kernel_compatibility_gate.md`
5. `docs/codex/goal_commands/README.md`
6. `docs/codex/goal_commands/09_major_case_research_benchmark_expansion.md`
7. `scripts/major_case_pattern_extractor.py`
8. `tests/test_major_case_pattern_extractor.py`
9. `configs/duecare/benchmarks/major_case_patterns/README.md`
10. `configs/duecare/benchmarks/major_case_patterns/coverage_report.json`
11. `configs/duecare/benchmarks/major_case_patterns/source_research_manifest.jsonl`
12. `configs/duecare/benchmarks/major_case_patterns/public_research_facts.jsonl`
13. `configs/duecare/benchmarks/major_case_patterns/harness_lift_prompts_major_case.jsonl`
14. `configs/duecare/benchmarks/harness_lift_dimensions.json`
15. `configs/duecare/scheme_fingerprints.yaml`
16. current `git status --short --branch`

Then create an internal baseline:

- current source-profile count
- current public source count
- current public fact count
- current dimension count
- current single-turn prompt count
- current multi-turn prompt count, if any
- current scenario-mix count
- current jurisdictions and sectors covered
- current tests and what they prove
- largest coverage gaps
- current research frontier or proof that none exists yet

If no source-profile corpus or frontier exists, create one before doing broad
manual additions.

## Hard Privacy Boundary

Private casefiles:

- Do not copy `C:\projects\major_cases` files into the repo.
- Do not commit raw names, filenames, folder names, text snippets, screenshots,
  emails, phones, passports, account numbers, URLs, OCR output, or logs from
  private files.
- Do not paste private case text into web searches.
- Do not send raw private case text to remote APIs or web services.
- Use only aggregate, redacted, synthetic, or hash-only private-derived signals.

Public sources:

- Public URLs and public case names may be stored in public-source manifests.
- Public facts must be paraphrased.
- Do not paste long copyrighted passages.
- Record source metadata and access dates.
- Treat public source facts as dated context, not live legal advice.

Synthetic prompts:

- Use placeholders such as `[WORKER]`, `[AGENCY]`, `[EMPLOYER]`,
  `[RECRUITER]`, `[HANDLER]`, `[COUNTRY_A]`, `[COUNTRY_B]`, `[SECTOR]`,
  `[AMOUNT]`, `[DOCUMENT]`, `[PLATFORM]`, `[CLIENT]`, `[AUDITOR]`,
  `[FAMILY_CONTACT]`, and `[CASEWORKER]`.
- No private names, private document numbers, private phone numbers, private
  emails, or private URLs.

## Source Search Scope

Search broadly. Prefer primary, official, or durable sources, but include
nontraditional sources when they add patterns that official sources miss.

Search strategy should be systematic, not ad hoc. Generate query templates from
jurisdiction, sector, exploitation behavior, camouflage pattern, actor type,
document type, and language or regional term.

Example query templates:

- `{jurisdiction} court forced labor trafficking debt bondage`
- `{jurisdiction} labor trafficking conviction recruitment fees`
- `{jurisdiction} anti trafficking implementation rules forced labor`
- `{jurisdiction} immigration agency scam compound trafficking workers`
- `{jurisdiction} labor inspectorate passport retention migrant workers`
- `{sector} forced labour case {jurisdiction}`
- `{sector} recruitment fee debt bondage {jurisdiction}`
- `{camouflage} migrant worker exploitation {jurisdiction}`
- `{source_site} trafficking forced labour {sector}`

Do not paste private snippets into queries. Keep queries generic and public.

Required source clusters:

1. Court decisions and public case summaries
2. Statutes, implementing rules, regulator guidance, and agency enforcement
   releases
3. ILO, IOM, UNODC, OHCHR, World Bank, FATF, Interpol, Europol, ASEAN-ACT,
   OSCE, and regional human-rights bodies
4. National labor inspectorates, immigration agencies, customs agencies, and
   procurement/supply-chain regulators
5. NGO typologies from Polaris, Anti-Slavery International, Walk Free, Human
   Rights Watch, Freedom Fund, Verite, Issara, La Strada, Hope for Justice, and
   credible local organizations
6. Academic and policy literature on forced labor, trafficking, debt bondage,
   forced criminality, recruitment fees, scam compounds, and supply chains
7. Financial-crime and platform-safety typologies: money mules, account rental,
   romance/crypto scams, fake job ads, document harvesting, KYC abuse, payroll
   intermediaries, and transaction laundering
8. Supply-chain, procurement, import-ban, Withhold Release Order, forced-labor
   enforcement, ESG, and audit-staging material
9. Nontraditional sources: court docket summaries, regulator press releases,
   parliamentary hearing notes, law-clinic reports, union reports, survivor-led
   organization materials, regional-language government pages, and public
   enforcement databases

Jurisdiction targets:

- Philippines
- Cambodia
- Thailand
- Malaysia
- Singapore
- Hong Kong
- Taiwan
- Indonesia
- Vietnam
- India
- Bangladesh
- Nepal
- Pakistan
- Gulf corridors
- United Kingdom
- France
- Greece
- Italy
- Spain
- Netherlands
- Belgium
- Canada
- United States
- Mexico
- Brazil
- Argentina
- Chile
- Peru
- Australia
- New Zealand
- South Africa
- Kenya

Prioritize jurisdictions and corridors that add new pattern families or
under-covered sectors.

Scale target:

- Consider 5,000+ candidate search results or URLs if network/time allows.
- Profile 1,000+ safe public documents.
- Extract facts from the highest-value 300+ profiles.
- Keep a backlog of at least 200 unprocessed but deduplicated candidate URLs if
  the 1,000-profile target is not reached in this run.

## Source Profile Corpus

Create or refresh a durable source-profile corpus under the existing benchmark
area, for example:

- `configs/duecare/benchmarks/major_case_patterns/source_profiles.jsonl`
- `configs/duecare/benchmarks/major_case_patterns/source_profile_manifest.json`
- `configs/duecare/benchmarks/major_case_patterns/source_profile_coverage.json`

Each source profile should be a safe structured document. Do not store the full
page text. Store only metadata, short paraphrased summaries, tags, and extraction
outputs.

Required fields:

- `id`
- `url`
- `source_title`
- `publisher`
- `source_tier`
- `published_date`
- `accessed_date`
- `language`
- `jurisdictions`
- `sectors`
- `source_cluster`
- `document_type`
- `relevance_score`
- `status`: one of `candidate`, `profiled`, `fact_extracted`, `rejected`,
  `needs_review`
- `rejection_reason`, if rejected
- `summary_paraphrase`
- `core_behaviors`
- `camouflage_patterns`
- `exploitation_indicators`
- `actor_patterns`
- `corridor_patterns`
- `evidence_patterns`
- `verification_notes`
- `related_public_fact_ids`
- `related_dimension_ids`
- `prompt_seed_ids`
- `pii_policy`
- `quality_score`
- `next_action`
- `last_profiled_at`

Targets:

- 1,000+ source profiles created or refreshed
- 300+ marked `fact_extracted`
- 100+ source profiles from primary/official/court sources
- 30+ jurisdictions represented
- 25+ sectors represented
- 20+ public source publishers represented
- 0 private-source profiles

Quality scoring:

- `5`: primary court/law/regulator source with direct exploitation relevance
- `4`: official agency, intergovernmental, or enforcement source with strong
  typology relevance
- `3`: NGO, academic, or credible research source with useful pattern detail
- `2`: investigative or media source with corroborated pattern leads
- `1`: weak, duplicate, outdated, or only tangentially relevant

Only quality `3+` profiles should normally generate public facts. Quality `1-2`
profiles can still inform search frontier expansion, but avoid using them as
standalone benchmark facts unless corroborated.

If access limits make 1,000 impossible in one run, leave a resumable frontier
with exact counts, source clusters done, source clusters remaining, and commands
or scripts to resume.

## Resumable Automation

Prefer scripts over one-off manual edits when a task will repeat:

- source-profile schema validation
- source-profile deduplication
- source-frontier loading/saving
- profile coverage reporting
- fact extraction from structured profiles
- conversation prompt generation
- hybrid prompt generation
- leak scanning

Allowed new scripts:

- `scripts/major_case_research_frontier.py`
- `scripts/major_case_source_profiler.py`
- `scripts/major_case_conversation_generator.py`
- `scripts/major_case_profile_coverage.py`

Keep scripts stdlib-only unless the repo already has the dependency and tests
prove it. Scripts should be resumable and idempotent:

- do not duplicate profiles for the same canonical URL
- do not overwrite manual verification notes unless explicitly refreshing
- use stable IDs from canonical URL hashes
- write JSONL atomically or safely enough to resume after interruption
- maintain counts and coverage in manifest files

If network tooling is blocked, create the schema, generator, tests, and a seed
frontier from already-known public sources, then document the network blocker.

## Extraction Outputs

From the source profiles, generate or update:

- `public_research_facts.jsonl`
- `source_research_manifest.jsonl`
- `derived_dimensions.json`
- `knowledge_facts.jsonl`
- `scenario_mix_prompts.jsonl`
- `harness_lift_prompts_major_case.jsonl`
- new multi-turn conversation artifacts

Public fact extraction requirements:

- facts are paraphrased
- every fact has source metadata
- every fact has confidence and notes
- every fact maps to behavior IDs, camouflage IDs, indicators, sectors, and
  jurisdictions when applicable
- facts distinguish legal holdings, allegations, official guidance, NGO
  typology, and benchmark-design observations

Dimension expansion requirements:

- add dimensions only when they test a real response capability or recurring
  pattern
- include response-skill dimensions, not only detection dimensions
- include dimensions for uncertainty, verification, source dating, refusal of
  operational uplift, multi-indicator reasoning, and remedy/safety framing
- keep harness-compatible shape

## Multi-Turn Conversation Benchmarks

Create multi-turn benchmark artifacts in a stable, documented location such as:

- `configs/duecare/benchmarks/major_case_patterns/conversation_prompts.jsonl`
- `configs/duecare/benchmarks/major_case_patterns/conversation_manifest.json`

Conversation prompt schema should include:

- `id`
- `turns`
- `expected_response_skills`
- `dimension_ids`
- `source_profile_ids`
- `public_fact_ids`
- `pattern_ids`
- `camouflage_ids`
- `jurisdictions`
- `sectors`
- `difficulty`
- `conversation_type`
- `trap_tags`
- `metadata`
- `state_checks`
- `safe_completion_criteria`
- `unsafe_failure_modes`

Each turn should include:

- `role`: `user` or `assistant_context`
- `content`
- optional `expected_behavior`
- optional `revealed_facts`
- optional `trap_tags`

Required conversation types:

- worker asks for help, then reveals document retention
- family member asks, then reveals threats and debt
- caseworker triage with missing evidence and later correction
- regulator interview plan with conflicting exhibits
- NGO analyst compares two intakes and updates risk classification
- compliance team asks for remediation, then asks for risky disclosure
- platform reviewer handles fake job ads and account-rental indicators
- financial-crime analyst handles money-mule or crypto-wallet indicators
- adversarial recruiter asks for concealment, then reframes as compliance
- legal/research analyst uses public case law but must not overclaim
- cross-border corridor case with tourist/transit cover
- survivor-support case where immediate safety questions matter

Conversation requirements:

- at least 500 multi-turn conversations if resources allow
- at least 4 turns per conversation for the main artifact
- at least 50 conversations with adversarial follow-up turns
- at least 50 conversations where the user reveals decisive facts late
- at least 50 conversations with correction or contradiction across turns
- at least 50 conversations requiring refusal plus safe alternative
- all placeholders only
- deterministic generation from seed
- tests prove structure, uniqueness, and no PII leakage
- conversations include enough state that a judge can evaluate whether the model
  remembers earlier facts, updates after correction, refuses harmful follow-up,
  and avoids fabricating jurisdiction-specific law

## Hybrid Scenario Mixing

Add or improve a hybrid mixer that can combine:

- private aggregate pattern IDs from `C:\projects\major_cases`
- public court-case facts
- regulator or agency guidance facts
- NGO typology facts
- financial-crime facts
- platform-safety facts
- supply-chain facts
- sector/corridor overlays
- multi-turn trap patterns

Hybrid prompt requirements:

- long single-turn prompts with distractors
- multi-turn conversations where facts unfold over time
- public-source anchor IDs in metadata
- private aggregate pattern IDs in metadata, never raw private snippets
- at least three dimensions per prompt
- at least one behavior pattern and one response-skill dimension per prompt
- deterministic IDs
- deduplication by normalized text

Suggested hybrid targets:

- 1,000+ single-turn hybrid prompts
- 500+ multi-turn conversations
- 200+ adversarial or evasion probes
- 200+ worker-support prompts
- 200+ caseworker/regulator/NGO prompts
- 200+ financial, platform, or supply-chain prompts

Continuous hybrid improvement:

- If a hybrid prompt has fewer than three dimensions, revise generation.
- If it lacks a response-skill dimension, revise generation.
- If it lacks a public anchor, revise generation.
- If it lacks a private aggregate pattern ID where available, revise generation.
- If it is too short to stress retrieval and routing, add controlled distractors.
- If it asks only detection and not safe action, add evidence/safety/refusal
  requirements.

## Tests To Add Or Expand

Add focused tests for:

- source profile schema
- 1,000-profile target or resumable frontier if blocked
- no private source roots in source profiles
- no raw private snippets in source profiles
- public URLs allowed only in public-source artifacts
- public fact fields and source profile linkage
- conversation schema and minimum turn count
- conversation determinism from seed
- conversation late-reveal cases
- conversation adversarial follow-up cases
- conversation contradiction/correction cases
- conversation refusal-plus-safe-alternative cases
- hybrid mixer metadata
- prompt deduplication
- dimension ID validity
- source-profile IDs referenced by facts/prompts exist
- coverage report target keys
- leak scans for emails, phones, passports, account-like IDs, private paths,
  and raw HTML/base64 payloads
- autonomous run-state schema
- source-frontier deduplication and resume behavior
- profile quality scoring
- profile status transitions
- source-profile to fact linkage
- source-profile to prompt linkage
- source-profile coverage report under-covered jurisdictions/sectors
- conversation state checks and unsafe failure modes
- hybrid prompt minimum dimension count
- hybrid prompt public/private aggregate provenance metadata

Tests are not optional. If a new artifact is introduced, add at least one shape
test and one privacy/leak test for it.

## Suggested Implementation Plan

### Phase 0: Baseline

1. Confirm branch and dirty state.
2. Inspect current major-case artifacts and counts.
3. Run focused tests.
4. Record gaps internally.

### Phase 1: Source Profile Schema And Frontier

1. Add source-profile artifact schema and writer.
2. Add a resumable frontier manifest.
3. Add tests for schema, counts, and PII safety.
4. Seed with existing public research manifest.
5. Commit and push.

Do not wait for Taylor before moving to Phase 2.

### Phase 2: Broad Public Source Collection

1. Search public sources by source cluster and jurisdiction.
2. Add source profiles without storing raw page text.
3. De-duplicate by canonical URL and normalized title.
4. Mark source status and relevance.
5. Continue until 1,000 profiles or a documented access blocker.
6. Commit and push in batches.

Batch guidance:

- Commit every 200-300 valid profiles or every coherent source-cluster slice.
- If a batch is noisy, add filters/tests before continuing.
- If a jurisdiction underperforms, record it and move on rather than blocking.

### Phase 3: Fact And Dimension Extraction

1. Extract paraphrased facts from profiled sources.
2. Add or update behavior/camouflage/response-skill dimensions.
3. Map facts to indicators, sectors, jurisdictions, and patterns.
4. Add tests for new families.
5. Regenerate artifacts.
6. Commit and push.

Then return to Phase 2 or Phase 4 based on the largest coverage gap.

### Phase 4: Multi-Turn Conversation Generation

1. Add deterministic conversation generator.
2. Generate worker, family, caseworker, regulator, NGO, compliance, platform,
   financial-crime, adversarial, legal, and corridor conversations.
3. Add tests for structure, determinism, late reveal, contradiction, refusal,
   and PII safety.
4. Commit and push.

Then generate a second batch targeting any response skills or sectors that the
conversation manifest marks under-covered.

### Phase 5: Hybrid Mixer

1. Combine source profiles, public facts, private aggregate pattern IDs, and
   response-skill dimensions.
2. Generate long single-turn and multi-turn hybrid artifacts.
3. Ensure metadata preserves provenance and synthetic status.
4. Add or update coverage report.
5. Commit and push.

Then inspect coverage and continue improving until the hybrid targets are met or
a blocker is documented.

### Phase 6: Verification Sweep

1. Run focused tests.
2. Run leak scans.
3. Run public-surface and Kaggle gates.
4. Inspect final counts and coverage.
5. Push final coherent slice.

If final verification passes but target gaps remain and no stop condition is
present, start another loop instead of ending.

## Validation Commands

Use the project test environment if the system Python is broken:

```powershell
%LOCALAPPDATA%\gemma4-testenv\venv\Scripts\python.exe -m pytest tests\test_major_case_pattern_extractor.py -q
%LOCALAPPDATA%\gemma4-testenv\venv\Scripts\python.exe scripts\validate_public_surface.py
%LOCALAPPDATA%\gemma4-testenv\venv\Scripts\python.exe -m pytest packages --collect-only -q
python scripts\validate_main_kaggle_kernels.py
py -3.12 scripts\validate_kaggle_page_sources.py
```

Run explicit leak scans over generated artifacts. Search for:

- `C:\projects\major_cases`
- `/projects/major_cases`
- raw emails
- phone-like strings
- passport-like strings
- account-like IDs
- private URLs in private-derived artifacts
- base64-like payloads
- HTML pages copied into JSONL

Public research/source-profile artifacts may contain public URLs. Private-
derived prompt/fact artifacts must not.

Validation policy:

- Run focused tests after each implementation batch.
- Run leak scans after every artifact regeneration.
- Run public-surface and Kaggle gates before each commit that changes public
  docs, benchmark artifacts, scripts, or test expectations.
- Do not claim full test pass unless full tests actually ran.
- Package collection is acceptable as a broad compatibility gate for this goal.

## Commit Discipline

- Work in coherent slices.
- Stage only files relevant to this goal.
- Leave unrelated dirty or untracked files alone.
- Commit and push each coherent slice.
- Include generated safe artifacts when they are the intended benchmark output.
- Include run-state/frontier artifacts when they are designed to let the next
  agent resume.
- Do not stage raw crawls, screenshots, raw downloaded PDFs, private data, or
  generated logs unless the artifact is explicitly designed and PII-safe.
- If a validation failure is environment-only, record the exact error and use
  the known working test environment when possible.
- Prefer multiple smaller pushed commits over one huge unreviewed commit.

## Stop Conditions

Stop only for:

- PII/secrets risk that cannot be safely resolved
- destructive-action approval
- web/network access unavailable after retry and no useful local source-profile
  or generator work remains
- repeated validation failure requiring user choice
- conflicting user changes that make safe continuation impossible
- repository state where safe staging is impossible without user choice
- weekly/network quota exhaustion after all useful local resumable work is done

Do not stop merely because:

- one country is done
- the first 100 profiles are done
- one prompt artifact is generated
- one commit is pushed
- a plan exists
- the work is slow
- the current source cluster is exhausted
- the first 1,000 profiles are done if obvious fact, dimension, prompt, or
  conversation gaps remain and resources are still available

## Resume Contract

Before any stop or final report, write a concise resume state into the relevant
manifest or coverage file. It should answer:

- What batch just completed?
- What exact counts exist now?
- What validation passed?
- What failed or was skipped?
- What should the next agent do first?
- Which source clusters and jurisdictions remain high value?
- Which artifacts need regeneration?
- Which tests should be run first?

The next agent should be able to resume without reading the whole chat history.

## Completion Standard

A future agent may call this complete only when evidence shows:

1. 1,000+ source profiles were created/refreshed, or a resumable frontier
   documents the exact blocker and remaining work.
2. Thousands of public search results or candidate pages were considered across
   multiple source clusters.
3. At least 300 source profiles reached `fact_extracted`, or the blocker is
   documented.
4. New public facts, dimensions, single-turn prompts, and multi-turn
   conversation prompts were generated.
5. Hybrid prompts combine public facts, private aggregate pattern IDs, response
   skills, and scenario axes.
6. All private-derived artifacts pass PII/leak checks.
7. Focused tests pass.
8. Public-surface and Kaggle validation gates run, or exact environment blockers
   are documented.
9. Coherent commits were pushed to `origin/master`.
10. Final report lists commit SHAs, counts, source clusters, jurisdictions,
    sectors, new dimensions, new tests, validation results, and remaining gaps.
11. A resumable run state exists and names the next autonomous actions.
12. The goal only stops with high-value gaps remaining if a real stop condition
    was hit and documented.
