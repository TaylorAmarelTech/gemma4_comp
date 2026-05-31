# Iterative branching research frontier

Use this when Taylor wants a long-running agent to keep branching from every
useful public source into more sources, more terms, more knowledge objects,
more dimensions, more tests, more prompts, and more multi-turn conversations.

This goal follows:

- `docs/codex/goal_commands/09_major_case_research_benchmark_expansion.md`
- `docs/codex/goal_commands/10_global_research_corpus_multiturn_benchmark.md`
- the public research spider artifacts in
  `configs/duecare/benchmarks/research_spider/`

It is intentionally more iterative than Goal 10. It also forces a tool/repo
discovery phase so the run keeps improving its search, spidering, fetching,
document-extraction, archival, and validation machinery instead of only adding
more prompts. The agent should not treat the first successful search, first
pack generation, first commit, or first green test run as completion. Green
tests are loop checkpoints.

## Copy-paste `/goal`

```text
/goal In C:\Users\amare\OneDrive\Documents\gemma4_comp, work on master without switching branches and follow docs/codex/goal_commands/11_iterative_branching_research_frontier.md as a 24-72 hour iterative branching research-frontier run. Start from the current public research spider artifacts and major-case aggregate pattern outputs. Spend the first several loops searching for and profiling better public search, spider, crawler, browser-automation, document-extraction, WARC/archive, dork-generation, and OSINT-adjacent Python repos/tools, then create a tool evaluation matrix and adopt only safe optional adapters behind deterministic tests. After that, repeatedly branch outward from each high-yield source candidate, tool candidate, knowledge object, source profile, failed query, and coverage gap. For each loop: extract new search terms and dorks; search official/court/immigration/justice/labour/law-enforcement/intergovernmental/nontraditional sources; profile new public documents; distill dated candidate knowledge objects; create or refine dimensions, tests, single-turn prompts, multi-turn conversations, hybrid scenario mixes, adversarial detection/refusal prompts, and long-context stress prompts; regenerate deterministic artifacts; run focused tests, leak scans, and repo gates; commit and push coherent slices; update resume state; then continue to the next highest-value branch without asking Taylor. Escalate only for credentials, destructive actions, unresolved PII/secrets risk, private-data exposure risk, or validation blockers that repeat after three genuine fix attempts. Do not stop after planning, one tool survey, one country, one source cluster, one batch of dorks, one generated corpus, one commit, or one successful validation pass.
```

## Mission

Build a durable branching research engine for DueCare capability work.

The output should make the benchmark better at:

- debt bondage
- recruitment fees and related costs
- illegal recruitment
- forced labour and forced labor
- forced criminality
- scam-compound recruitment and coercion
- passport/document control
- immigration-status coercion
- wage withholding and salary deduction control
- domestic work, fishing, construction, agriculture, hospitality, care work,
  garment, logistics, platform work, and online scam sectors
- corridor, transit, and destination-country ambiguity
- camouflage labels such as training fee, safekeeping, tourist processing,
  customer-support role, salary advance, accommodation deduction, agency loan,
  family debt, voluntary overtime, and civil labour dispute
- victim identification, referral, safe return, legal aid, non-punishment, and
  evidence preservation
- distinguishing trafficking, smuggling, labour-law violations, fraud,
  procurement risk, sanctions/import controls, and financial-crime indicators

Optimize for capability, coverage, grounded public context, and reusable
artifacts. Avoid cleanup-only work unless it is required for safety,
determinism, or validation.

## Runtime Target

Target runtime: 24-72 hours of useful work if resources are available.

Minimum loop target before calling the run complete:

- 2+ tool/repo discovery loops
- 1+ tool evaluation matrix loop
- 1+ safe optional adapter or deterministic no-network provider loop
- 6+ research-frontier loops
- 4+ source-profile and knowledge-object loops
- 3+ prompt/conversation/scenario-mixing loops
- 2+ dimension/test-strengthening loops
- 1+ final validation and handoff loop

This goal is not complete after:

- writing a plan
- creating only this file
- only surveying tools without artifact adoption or rejection notes
- adding a dependency without a safety, license, maintenance, and test review
- only running the existing spider once
- adding only one jurisdiction or source family
- adding only single-turn prompts
- adding only document links without source profiles
- adding source profiles without knowledge objects or verification notes
- adding prompts without tests
- committing without a resume state

If network, quota, package, or host instability prevents the full run, commit
and push the coherent verified slice, preserve the frontier/resume state, and
state the blocker precisely.

## Read First

1. `AGENTS.md`
2. `docs/codex/README.md`
3. `docs/codex/00_do_not_break.md`
4. `docs/codex/00_kernel_compatibility_gate.md`
5. `docs/codex/00_execution_order.md`
6. `docs/codex/goal_commands/README.md`
7. `docs/codex/goal_commands/09_major_case_research_benchmark_expansion.md`
8. `docs/codex/goal_commands/10_global_research_corpus_multiturn_benchmark.md`
9. `scripts/public_research_spider.py`
10. `tests/test_public_research_spider.py`
11. `scripts/major_case_pattern_extractor.py`
12. `tests/test_major_case_pattern_extractor.py`
13. `configs/duecare/benchmarks/research_spider/summary.json`
14. `configs/duecare/benchmarks/research_spider/source_candidates.jsonl`
15. `configs/duecare/benchmarks/research_spider/source_profiles.jsonl`
16. `configs/duecare/benchmarks/research_spider/knowledge_objects.jsonl`
17. `configs/duecare/benchmarks/research_spider/dimension_candidates.jsonl`
18. `configs/duecare/benchmarks/research_spider/deep_search_dorks.jsonl`
19. `configs/duecare/benchmarks/research_spider/second_wave_queries.jsonl`
20. `configs/duecare/benchmarks/major_case_patterns/coverage_report.json`
21. current `git status --short --branch`

Then record a baseline in the run state:

- current source candidates
- current source profiles
- current knowledge objects
- current dimension candidates
- current base queries
- current deep dorks
- current second-wave queries
- current single-turn prompts
- current multi-turn prompts or proof none exist
- current source families
- current jurisdictions
- current sectors/corridors
- current behavior-signal coverage
- current tests
- largest gaps
- next 30 autonomous branches

## Hard Privacy Boundary

Private casefiles may guide aggregate pattern extraction only.

Never:

- copy `C:\projects\major_cases` files into the repo
- commit raw private filenames, folder names, names, contact details, addresses,
  document numbers, account numbers, URLs, screenshots, OCR, chat logs, or raw
  text snippets from private files
- paste private case text into web search
- send private case text to remote models
- mix public-source facts with private facts in a way that could re-identify a
  person or case
- generate prompts that teach exploiters how to evade detection, hide debt, hide
  document control, coach victims, bypass border screening, launder recruitment
  money, or preserve coercion

Allowed:

- aggregate pattern IDs
- redacted/synthetic fixtures
- public URLs, public titles, public source metadata, and paraphrased public
  facts with provenance
- candidate knowledge objects that explicitly remain unverified until checked
- adversarial prompts only when the expected safe answer refuses operational
  concealment and converts the request into detection/remediation

## Tool Discovery And Adoption Track

The first phase of a long run is not only "search for sources." It is also
"search for better search and extraction machinery." Treat tools as frontier
branches and profile them before using them.

Create or update a tool evaluation matrix before adding any new dependency or
long-lived integration:

- `configs/duecare/benchmarks/research_spider/tool_evaluation_matrix.jsonl`
- `configs/duecare/benchmarks/research_spider/tool_adoption_notes.md`
- `configs/duecare/benchmarks/research_spider/search_provider_registry.json`
- `configs/duecare/benchmarks/research_spider/crawler_provider_registry.json`
- `configs/duecare/benchmarks/research_spider/extractor_provider_registry.json`

Use fields like:

- `tool_id`
- `tool_name`
- `repo_url`
- `docs_url`
- `category`
- `license`
- `maintenance_signal`
- `python_support`
- `network_behavior`
- `robots_or_rate_limit_support`
- `privacy_risk`
- `install_risk`
- `dependency_risk`
- `fit_score`
- `adoption_decision`
- `rejection_reason`
- `notes`
- `checked_date`

Tool categories to search and compare:

- Search APIs and metasearch: Brave Search API, SerpApi, SearXNG, DDGS or
  duckduckgo-search successors, GitHub Search API, and browser-ready manual
  fallback queues.
- General crawlers and spiders: Scrapy, Crawlee for Python, advertools spider
  and sitemap utilities, Crawl4AI, and a minimal `httpx`/`requests` plus
  `BeautifulSoup` fallback.
- Browser automation for JavaScript-heavy public pages: Playwright for Python
  behind explicit opt-in and small allowlisted fetch scopes.
- URL discovery and cleaning: sitemap parsers, robots.txt parsers, courlan, and
  deterministic URL normalization helpers.
- Text extraction from HTML: trafilatura, readability-style extractors,
  BeautifulSoup fallback extraction, and Crawl4AI Markdown output when safe.
- PDF and document extraction: PyMuPDF, pdfplumber, pypdf, Microsoft
  MarkItDown, unstructured, and any lighter extractor that handles public
  reports without sending content to remote services.
- Archival and reproducibility: warcio/WARC capture, cached HTTP responses,
  content hashes, source snapshots that exclude PII, and manifest-only replay.
- Dork generation and query expansion: deterministic dork templates, language
  variants, phrase mining from source profiles, and search-engine-specific
  operators.
- OSINT-adjacent inspiration only: pagodo, Photon, theHarvester, Metagoofil,
  and similar repos may inform query/dork/source-discovery patterns, but do not
  run broad people, email, subdomain, credential, or target-enumeration harvests
  from this repo.

Seed tool sources to inspect first, then branch from their docs, issues,
alternatives, and dependency graphs:

- Scrapy docs and `scrapy/scrapy`
- Crawlee for Python `apify/crawlee-python`
- Crawl4AI docs and `unclecode/crawl4ai`
- trafilatura docs and `adbar/trafilatura`
- advertools docs
- Playwright for Python docs
- SearXNG docs, Brave Search API docs, SerpApi docs, and DDGS/duckduckgo-search
  successor repos
- PyMuPDF docs, pdfplumber, pypdf, Microsoft MarkItDown, and unstructured
- warcio docs and `webrecorder/warcio`
- courlan and other URL-normalization helpers
- pagodo, Photon, theHarvester, and Metagoofil as cautionary OSINT-adjacent
  design references only

Adoption rules:

- Prefer deterministic, dependency-light wrappers first.
- Do not add a package dependency merely because it looks useful; profile it,
  record the license, maintenance signal, install risk, and privacy risk.
- Keep adapters optional. The repo must still generate core artifacts in a
  no-network/no-credential mode.
- Do not send private casefile content, raw extracted PII, secrets, or
  unresolved worker details to remote APIs or remote LLMs.
- Do not bypass paywalls, authentication, CAPTCHA, robots exclusions, rate
  limits, or source terms.
- Do not use stealth, evasion, proxy-rotation, browser-fingerprinting, or
  anti-bot-bypass features.
- Wrap each provider behind a small interface that can return synthetic fixture
  results in tests.
- Add tests before relying on an adapter for generated artifacts.
- Record rejected tools. Rejections are useful when the reason is privacy,
  license, maintenance, install risk, remote-data exposure, or hostile scraping
  behavior.

Minimum tool-discovery search loops:

1. Search and profile public search providers and metasearch options.
2. Search and profile crawlers/spiders, including Python repos and framework
   docs.
3. Search and profile HTML, PDF, Office, CSV, JSON, and WARC extraction tools.
4. Search and profile OSINT-adjacent dorking/source-discovery tools only for
   safe design lessons and explicit anti-patterns.
5. Prototype one low-risk optional adapter or improve the deterministic
   no-network fallback if every external option is too risky.
6. Add focused tests and update the run state with adopted, rejected, and
   deferred tools.

## Branching Algorithm

Each loop chooses branches from a frontier. A branch may be a query, source
candidate, tool candidate, source profile, knowledge object, dimension gap,
prompt gap, failed search, source-family gap, jurisdiction gap, sector gap, or
test gap.

For every branch:

1. Extract terms:
   - behavior terms
   - camouflage terms
   - sector terms
   - corridor terms
   - source-type terms
   - legal/prosecution terms
   - victim-protection terms
   - evidence terms
   - language variants
2. Generate dorks:
   - `site:`
   - `filetype:pdf`
   - `filetype:xlsx`, `filetype:csv`, `filetype:docx`, `filetype:pptx`
   - `intitle:`
   - `inurl:`
   - `after:` and `before:`
   - exact-phrase combinations
   - negative filters for entertainment/fiction/noise
   - source-family-specific terms
3. Search or queue searches:
   - use APIs when credentials are available and safe
   - otherwise write browser-ready manual fallbacks
   - respect robots and rate limits for fetches
   - log rejected/paywalled/blocked sources instead of stalling
   - record which provider/tool produced each result
   - fall back across providers when a source family is sparse
   - preserve manual dorks when automated providers are blocked or unsafe
4. Profile candidate sources:
   - public URL
   - title
   - snippet or public abstract
   - source family
   - jurisdiction
   - sector/corridor
   - behavior signals
   - camouflage patterns
   - exploitation indicators
   - evidence type
   - source quality
   - verification needs
5. Profile candidate tools when the branch is tooling:
   - repo and documentation URLs
   - install and runtime requirements
   - license and maintenance signal
   - whether it supports polite crawling, robots, caching, and rate limits
   - whether it requires credentials, remote services, browsers, or native deps
   - privacy, PII, and secrets exposure risks
   - deterministic fixture strategy
   - adoption, rejection, or defer decision
6. Distill candidate knowledge:
   - source date or update date, when known
   - source type: court, statute, report, guidance, dataset, operation, news lead
   - paraphrased public fact candidates
   - limitations and confidence
   - corroboration links
   - privacy flags
7. Generate benchmark artifacts:
   - dimensions
   - tests
   - single-turn prompts
   - multi-turn conversations
   - hybrid scenarios
   - long-context distractor prompts
   - applicability-judge seeds
   - refusal/detection prompts for camouflage/evasion requests
8. Validate:
   - focused tests
   - deterministic regeneration checks
   - leak scans
   - relevant repo gates
9. Commit and push coherent slices.
10. Update frontier and resume state.
11. Continue to the next branch.

## Branch Scoring

Prioritize branches by this order:

1. PII/secrets or unsafe-generation issue that must be fixed.
2. Current failing test or validation caused by this work.
3. High-tier official, court, intergovernmental, prosecution, or labour
   inspectorate source.
4. Tool candidate that unlocks safer, broader, or more reproducible search,
   crawling, extraction, or archival.
5. Under-covered behavior family.
6. Under-covered jurisdiction, source language, source type, sector, or corridor.
7. Source with concrete case facts, indicators, prosecution facts, or guidance.
8. Source that can corroborate an existing candidate knowledge object.
9. Source that adds a new camouflage pattern.
10. Source that improves prompt/conversation realism.
11. Source that only duplicates already-covered context.

Suggested score fields:

- `source_tier_score`
- `relevance_score`
- `novelty_score`
- `coverage_gap_score`
- `corroboration_score`
- `recency_score`
- `artifact_value_score`
- `tool_adoption_value_score`
- `privacy_risk_penalty`
- `license_or_dependency_penalty`
- `fetch_or_access_penalty`

## Source Clusters

Rotate clusters when one stalls.

Primary official/court clusters:

- justice departments and prosecutors
- immigration departments
- labour ministries and labour inspectorates
- border, customs, and home affairs agencies
- police and anti-trafficking units
- courts and public case-law databases
- parliamentary hearings, committee reports, government auditors, ombuds offices
- national rapporteurs on trafficking or modern slavery
- sanctions, import-control, forced-labour import, procurement, and supply-chain
  due-diligence authorities

Intergovernmental and regional clusters:

- IOM
- ILO
- UNODC
- OHCHR
- UN special rapporteur pages
- World Bank and IFC labour/supply-chain material
- OECD
- FATF and financial-intelligence typologies
- INTERPOL
- Europol
- Frontex
- Eurojust
- European Commission, EMN, and Eurostat
- ASEAN, Bali Process, OSCE, Council of Europe, African Union, OAS

Civil society and research clusters:

- legal aid and worker-support organizations
- anti-trafficking NGOs
- trade unions and migrant-worker centers
- academic repositories
- investigative journalism used only as lead material until corroborated
- public training decks/toolkits
- datasets and annual reports

Jurisdiction clusters to rotate through:

- Philippines
- Hong Kong SAR
- China
- United States
- United Kingdom
- Canada
- Australia
- New Zealand
- Singapore
- Malaysia
- Thailand
- Cambodia
- Myanmar
- Indonesia
- Vietnam
- India
- Bangladesh
- Nepal
- Sri Lanka
- Pakistan
- UAE
- Qatar
- Saudi Arabia
- Kuwait
- Bahrain
- Oman
- Jordan
- Lebanon
- Turkey
- South Africa
- Kenya
- Nigeria
- Ghana
- Brazil
- Mexico
- Colombia
- Spain
- France
- Germany
- Italy
- Netherlands
- Belgium
- Poland
- Romania
- Bulgaria
- Greece
- Ireland

## Dork Families

Use these as templates, then extend them from source profiles:

```text
site:{domain} "{behavior}" ("trafficking in persons" OR "human trafficking") filetype:pdf
site:{domain} "{behavior}" ("annual report" OR "progress report" OR "situation report") after:2020
site:{domain} "{behavior}" ("case digest" OR "case law" OR prosecution OR conviction OR sentence)
site:{domain} "{behavior}" (indicator OR indicators OR screening OR "victim identification")
site:{domain} "{behavior}" ("immigration status" OR visa OR "work permit" OR deportation)
site:{domain} "{behavior}" ("supply chain" OR procurement OR subcontractor OR "modern slavery statement")
site:{domain} "{behavior}" (filetype:xlsx OR filetype:csv OR filetype:docx OR filetype:pptx)
site:{domain} ("forced labour" OR "forced labor" OR servitude OR "debt bondage") "{sector}"
site:{domain} ("domestic work" OR fishing OR construction OR agriculture OR hospitality OR "scam compound") "{behavior}"
site:{domain} (inurl:traffick OR inurl:slavery OR inurl:forced OR inurl:recruit) "{behavior}"
site:{domain} (intitle:trafficking OR intitle:slavery OR intitle:"forced labour" OR intitle:"forced labor") "{behavior}"
site:{domain} "{behavior}" ("trafficking in persons" OR "modern slavery") -movie -fiction -lyrics -definition
```

Add language variants when useful:

- `trata de personas`
- `trabajo forzoso`
- `servidumbre`
- `traite des etres humains`
- `travail force`
- `traite des personnes`
- `Menschenhandel`
- `Zwangsarbeit`
- `tratta di esseri umani`
- `lavoro forzato`
- `trafico de pessoas`
- `trabalho forcado`

## Tool Discovery Dork Families

Use these for the tool/repo phase, then extend them from useful results:

```text
site:github.com Python crawler framework public data extraction
site:github.com Python "web scraping" "robots.txt" "rate limit"
site:github.com Python "search API" "metasearch" JSON
site:github.com Python "Google dork" OR "search dork" OSINT
site:github.com Python "PDF extraction" "table extraction" "markdown"
site:github.com Python "WARC" "web archive" crawl
site:readthedocs.io Python crawler scraping extraction documentation
site:docs.* Python "crawler" "scraper" "Markdown" "LLM"
"Scrapy" "robots.txt" "AutoThrottle" Python
"Crawlee" Python crawler Playwright BeautifulSoup
"Crawl4AI" Python Markdown crawler extraction
"trafilatura" Python text extraction crawler
"MarkItDown" Python document Markdown conversion
"PyMuPDF" OR "pdfplumber" "table extraction" "public reports"
"SearXNG" "Search API" JSON
"Brave Search API" Python web search
"SerpApi" Python Google Search API
"theHarvester" OR "Photon" OR "pagodo" OR "Metagoofil" Python OSINT crawler
```

For OSINT-adjacent tools, the output must be design lessons, rejection notes,
or safe query templates. Do not produce instructions for target enumeration,
credential discovery, exploit development, evasive scraping, or personal-data
harvesting.

## Artifacts To Create Or Extend

Prefer extending the current public research spider and major-case benchmark
artifact locations rather than creating new top-level directories.

Likely artifacts:

- `configs/duecare/benchmarks/research_spider/research_frontier.json`
- `configs/duecare/benchmarks/research_spider/research_run_state.json`
- `configs/duecare/benchmarks/research_spider/tool_evaluation_matrix.jsonl`
- `configs/duecare/benchmarks/research_spider/tool_adoption_notes.md`
- `configs/duecare/benchmarks/research_spider/search_provider_registry.json`
- `configs/duecare/benchmarks/research_spider/crawler_provider_registry.json`
- `configs/duecare/benchmarks/research_spider/extractor_provider_registry.json`
- `configs/duecare/benchmarks/research_spider/source_profile_coverage.json`
- `configs/duecare/benchmarks/research_spider/rejected_sources.jsonl`
- `configs/duecare/benchmarks/research_spider/corroboration_links.jsonl`
- `configs/duecare/benchmarks/research_spider/verified_knowledge_objects.jsonl`
- `configs/duecare/benchmarks/research_spider/conversation_prompts.jsonl`
- `configs/duecare/benchmarks/research_spider/conversation_manifest.json`
- `configs/duecare/benchmarks/research_spider/hybrid_scenario_prompts.jsonl`
- `configs/duecare/benchmarks/research_spider/applicability_seed_tags.jsonl`
- `configs/duecare/benchmarks/research_spider/frontier_handoff.md`

Likely scripts:

- `scripts/public_research_spider.py`
- `scripts/public_tool_survey.py`
- `scripts/public_search_providers.py`
- `scripts/public_fetch_extract.py`
- `scripts/public_research_frontier.py`
- `scripts/public_source_profiler.py`
- `scripts/public_knowledge_distiller.py`
- `scripts/public_conversation_generator.py`
- `scripts/public_research_coverage.py`

Likely tests:

- `tests/test_public_research_spider.py`
- `tests/test_public_tool_survey.py`
- `tests/test_public_search_providers.py`
- `tests/test_public_fetch_extract.py`
- `tests/test_public_research_frontier.py`
- `tests/test_public_knowledge_distiller.py`
- `tests/test_public_conversation_generator.py`
- `tests/test_major_case_pattern_extractor.py`

Do not create all of these blindly. Create only what helps the next loop become
more deterministic, resumable, or testable.

## Output Targets

If resources allow, work toward:

- 50+ search/crawl/extraction/archive tools or repos considered
- 15+ tools shortlisted with license, maintenance, privacy, and fit notes
- 5+ safe optional adapters or provider wrappers prototyped or improved
- 3+ deterministic fixture suites covering provider fallbacks
- 10,000+ search/dork queries generated or considered
- 3,000+ candidate URLs considered
- 1,000+ public source profiles created or refreshed
- 300+ candidate knowledge objects distilled
- 150+ corroboration links between sources
- 100+ new or refined dimension candidates
- 1,000+ single-turn prompts
- 500+ multi-turn conversation prompts
- 500+ hybrid scenario prompts
- 100+ adversarial detection/refusal prompts
- 50+ long-context stress prompts
- 25+ regression tests or fixture assertions across the tooling

These are long-run targets, not promises for a single short session. If blocked,
record exact counts and next branches.

## Prompt And Conversation Requirements

Prompts should include:

- single-turn classification/triage prompts
- source verification prompts
- source conflict-resolution prompts
- multi-turn worker/researcher/provider conversations
- hybrid scenarios combining sector, corridor, debt, document control,
  immigration status, wage, recruitment, and financial-obfuscation signals
- confusing long-context prompts with irrelevant benign details
- prompts where jurisdiction is uncertain and the model must not hallucinate
  specific legal advice
- prompts where the user asks for concealment, coaching, evasion, or abusive
  operational help and the correct answer is refusal plus safe detection or
  remediation
- prompts that force the model to separate observed public facts, inferred
  patterns, missing verification, and safe next steps
- prompts that test whether the applicability judge catches content-derived
  dimensions absent from metadata tags

Every generated prompt must:

- use placeholders or synthetic names only
- avoid real contact details and document IDs
- avoid operational trafficking instructions
- carry source/profile metadata where applicable
- be traceable to public source profiles or aggregate private pattern IDs
  without exposing private evidence

## Knowledge Object Requirements

Candidate knowledge objects should include:

- stable ID
- schema version
- status
- source URL
- source title
- source family
- source type
- jurisdiction
- publication/update date when known
- behavior signals
- camouflage patterns
- exploitation indicators
- paraphrased fact candidates
- verification notes
- corroboration needs
- privacy flags
- safe-use flags

Do not promote candidate knowledge objects to verified status unless:

- the public source was opened or fetched safely
- source date/type was recorded
- the claim is paraphrased rather than copied
- at least one corroborating public source or a clear single-source limitation is
  recorded
- no raw PII, private case detail, or volatile advice is embedded

## Tests And Validation

Run focused tests after each implementation slice:

```bash
C:\Users\amare\AppData\Local\gemma4-testenv\venv\Scripts\python.exe -m pytest tests/test_public_research_spider.py tests/test_major_case_pattern_extractor.py -q
```

Add and run any new focused tests created by the loop. If tool scripts are
created, expected focused tests include:

```bash
C:\Users\amare\AppData\Local\gemma4-testenv\venv\Scripts\python.exe -m pytest tests/test_public_tool_survey.py tests/test_public_search_providers.py tests/test_public_fetch_extract.py -q
```

Run leak scans over changed scripts, tests, and generated artifacts. Classify
any repo-wide hits as new-vs-pre-existing before treating them as blockers; this
repo has older synthetic fixtures and redaction-test strings that should not be
confused with newly introduced leaks.

At minimum, scan the files touched by the current loop and any newly generated
artifacts:

```bash
rg -n "C:\\projects\\major_cases|/projects/major_cases|john\.doe@example|helper@example\.org|AB1234567|\+1 202 555|AQ\.Ab8RN6|c72673292f" <changed files and generated artifact paths>
```

For a broad scan, first capture the existing baseline, then fail only on new or
unexplained hits.

Before every commit that changes public docs, benchmark surfaces, or Kaggle
surfaces, run the applicable gates:

```bash
python scripts/validate_public_surface.py
python -m pytest packages --collect-only -q
python scripts/validate_main_kaggle_kernels.py
py -3.12 scripts/validate_kaggle_page_sources.py
```

If a local Python has broken pytest dependencies, switch to the known project
test environment and record the failing interpreter separately.

## Commit Cadence

Commit and push coherent increments. Good commit boundaries:

- tool evaluation matrix and provider registry
- safe optional search/crawl/extraction adapter with synthetic fixtures
- frontier/state tooling
- source-profile generation
- knowledge-object distillation
- dork/query expansion
- conversation generator
- dimension/test expansion
- regenerated artifact pack
- validation/handoff update

Do not stage unrelated dirty files. Leave unrelated untracked data alone.

Every commit message should include:

- what was added or expanded
- generated artifact counts
- tests and leak scans run
- whether network search was live or deterministic/no-network
- privacy boundary statement when generated artifacts are involved

## Stop Conditions

Stop only when:

- a destructive action is required
- credentials or paid access are required
- unresolved PII/secrets risk exists
- a private-data exposure risk cannot be mitigated locally
- the same validation blocker repeated after three genuine fix attempts
- filesystem/network constraints prevent meaningful progress and the resume state
  has been committed or clearly reported
- Taylor explicitly stops or redirects the run

Do not stop because:

- one loop succeeded
- a test run passed
- one commit pushed
- one jurisdiction was covered
- there are many remaining branches
- the next branch requires choosing among reasonable defaults

## Final Handoff

When the run pauses or completes, report:

- commit SHA and push status
- tools/repos searched
- tool evaluation matrix count
- tools adopted, deferred, and rejected with reasons
- optional adapters created or improved
- source candidates considered
- source profiles created/refreshed
- knowledge objects created/refreshed
- dimensions created/refined
- prompt counts by family
- conversation counts by family
- tests added and run
- validation commands and outcomes
- leak scan outcome
- highest-yield sources found
- branches rejected and why
- next 30 autonomous branch actions
- blockers and residual risks

Also update the relevant summary or handoff artifact so the next Claude/Codex
session can resume without relying on chat history.
