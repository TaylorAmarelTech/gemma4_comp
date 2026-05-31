# Major-case multi-hour research and benchmark expansion

Use this when the next improvement pass should run for hours, not minutes. The
purpose is to grow benchmark capability from two inputs:

1. private example casefiles in `C:\projects\major_cases`
2. public research, official guidance, reports, and case literature found by
   web search

The private files are pattern inspiration only. They are never committed,
quoted, uploaded, pasted into search, or exposed to remote services.

This is intentionally a long-form instruction file. The `/goal` objective
should reference this file instead of pasting the full text.

## Copy-paste `/goal`

```text
/goal In C:\Users\amare\OneDrive\Documents\gemma4_comp, work on master without switching branches and follow docs/codex/goal_commands/09_major_case_research_benchmark_expansion.md as a multi-hour no-stop capability run. Improve the major-case-derived benchmark pipeline with public web research, source-grounded knowledge extraction, scenario crafting, deterministic scenario mixing, stronger tests, more synthetic prompts, more derived dimensions, and richer exploitation/camouflage coverage from C:\projects\major_cases while preserving strict PII safety. Do not stop after a plan or one small edit; complete repeated research/extraction/generation/validation loops, commit and push coherent slices, and continue until the file's completion standard is met or a real blocker is documented.
```

## Mission

Build a larger, sharper, source-grounded benchmark and knowledge layer for
DueCare. Optimize for capability, not cleanup:

- more exploitation behavior families
- more camouflage and relabeling patterns
- more scenario templates and scenario mixes
- more adversarial/evasion probes
- more worker-support and caseworker examples
- more public research facts with citations
- more derived dimensions compatible with the harness-lift rubric shape
- more tests proving quality, determinism, and PII safety

Do not treat this as a documentation-only task. The expected run should include
code, generated artifacts, tests, validation, commits, and pushes.

## Expected Runtime

Target runtime: 3-8 hours of actual work if resources are available.

Do not declare success after:

- only rewriting this goal file
- only adding a plan
- only running one short extractor pass
- only adding a handful of prompts
- only cleaning or reorganizing existing files

The run should make at least two coherent improvement loops unless blocked by a
real external constraint. A loop means:

1. inspect current artifacts and counts
2. research or mine patterns
3. implement extraction or generation improvements
4. regenerate artifacts
5. run focused tests and PII checks
6. commit and push the coherent slice
7. continue to the next highest-value gap

## Read First

1. `AGENTS.md`
2. `docs/codex/README.md`
3. `docs/codex/00_do_not_break.md`
4. `docs/codex/00_kernel_compatibility_gate.md`
5. `docs/codex/goal_commands/README.md`
6. `scripts/major_case_pattern_extractor.py`
7. `tests/test_major_case_pattern_extractor.py`
8. `configs/duecare/benchmarks/major_case_patterns/README.md`
9. `configs/duecare/benchmarks/major_case_patterns/summary.json`
10. `configs/duecare/benchmarks/major_case_patterns/derived_dimensions.json`
11. `configs/duecare/benchmarks/major_case_patterns/derived_prompts.jsonl`
12. `configs/duecare/benchmarks/major_case_patterns/knowledge_facts.jsonl`
13. `configs/duecare/benchmarks/harness_lift_dimensions.json`
14. `configs/duecare/benchmarks/harness_lift_prompts_expansion.jsonl`
15. `configs/duecare/scheme_fingerprints.yaml`
16. current `git status --short --branch`

Then produce an internal working inventory:

- current pattern count
- current dimension count
- current prompt count
- current knowledge fact count
- top noisy pattern risks
- missing behavior families
- missing camouflage families
- missing sectors/corridors/framing types
- current tests and what they actually prove

## Privacy Boundary

Hard rules:

- Do not copy `C:\projects\major_cases` files into the repo.
- Do not emit raw source paths, filenames, folder names, snippets, names,
  emails, phones, passports, account numbers, URLs from private files, case IDs,
  screenshots, base64 payloads, OCR text, or unredacted logs.
- Do not paste private case text into web searches.
- Do not send raw private case text to remote model APIs or web services.
- If model assistance is used, feed only redacted, abstracted, synthetic, or
  aggregate material.
- Source references for private files must stay hash-only, such as `src_...`.
- Synthetic prompts must use placeholders such as `[WORKER]`, `[AGENCY]`,
  `[EMPLOYER]`, `[COUNTRY_A]`, `[COUNTRY_B]`, `[SECTOR]`, `[AMOUNT]`,
  `[DOCUMENT]`, `[PLATFORM]`, and `[INTERMEDIARY]`.
- Keep private-source facts abstract. Public citations may be stored only when
  they come from public web research, not private files.

The right transformation chain is:

1. private casefile signal -> redacted aggregate behavior
2. public research -> dated citation and generalized knowledge fact
3. scenario crafting -> synthetic benchmark prompt
4. dimension generation -> harness-compatible scoring question
5. tests -> prove no private data leakage and stable behavior

## Web Research Requirements

Web search is allowed and encouraged. It is part of this goal. Use it to ground
patterns, expand typologies, and add source-backed knowledge facts.

Never search for private names, filenames, exact private snippets, contact
details, case IDs, or unique phrases from the private files.

Research queue, in priority order:

1. ILO forced-labour indicators and operational guidance.
2. ILO fair recruitment, recruitment-fee, wage, and labor-inspection guidance.
3. UNODC/IOM guidance on trafficking indicators, forced criminality, online
   scam compounds, and victim identification.
4. Official national labor or regulator guidance for common migrant-worker
   corridors, using dated/source-cited facts only.
5. NGO typologies for debt bondage, document retention, deception, threats,
   isolation, wage withholding, forced criminality, and recruitment networks.
6. Public court/regulator cases that illustrate camouflage patterns without
   needing private facts.
7. Platform trust-and-safety and financial-crime typologies relevant to
   recruitment scams, mule accounts, document harvesting, and forced fraud work.

Preferred source tiers:

1. Primary and intergovernmental sources: ILO, UNODC, IOM, OHCHR, national
   labor agencies, court decisions, statutes, regulator reports, official
   inspection guidance.
2. NGO and research sources: Polaris, Walk Free, Human Rights Watch, Anti-
   Slavery International, reputable university or policy reports.
3. Investigative journalism only when it adds a documented pattern not covered
   by stronger sources.

For every public fact added, preserve structured metadata:

- `id`
- `fact_type`
- `statement`
- `source_title`
- `publisher`
- `url`
- `published_date` or `accessed_date`
- `jurisdictions`
- `sectors`
- `related_indicators`
- `related_behavior_ids`
- `related_camouflage_ids`
- `confidence`
- `notes`

Public facts should be paraphrased. Do not paste long copyrighted passages.

## Casefile Mining Requirements

Use `C:\projects\major_cases` to improve aggregate detection and generation.
The existing extractor already performs a safe sweep; improve it rather than
creating a raw-data side channel.

Mine for abstract evidence of:

- debt bondage and fee stacking
- document retention and credential control
- contract substitution and role substitution
- wage withholding, deductions, exchange-rate manipulation, and delayed pay
- movement restriction, exit control, locked housing, transport control
- threats, deportation blackmail, police threats, blacklist threats, family
  threats, retaliation threats
- isolation, communication control, translation dependency, no independent help
- housing and living-condition control
- forced criminality, online scam compounds, money mules, crypto wallets,
  account rental, coerced fraud work
- document harvesting, identity misuse, data harvesting, impersonation risk
- subcontractor-chain obscuring, shell vendors, payroll intermediaries,
  sponsor/vendor/client blame shifting
- audit staging, scripted worker statements, record cleanup, deleted messages,
  backdated forms
- platform recruitment, social media recruitment, fake job posts, chat funnels
- medical, insurance, welfare, charity, cooperative, and membership wrappers
- arbitration, forum, governing-law, cross-border routing, and jurisdictional
  arbitrage
- consent, waiver, voluntary, declaration, undertaking, release, and no-claim
  labels
- standard-practice normalization and industry-custom defenses

Use co-occurrence rules for noisy terms. A single generic token such as
`vendor`, `audit`, `loan`, `policy`, or `contract` should not trigger a pattern
unless paired with more specific exploitation language.

## Scenario Crafting Requirements

Create scenario families, not isolated prompts.

Required perspectives:

- worker-support advocate
- worker or family member
- caseworker triage
- NGO analyst
- regulator or labor inspector
- researcher building a typology
- journalist or investigator validating a pattern
- compliance team asking for safe remediation
- auditor or buyer reviewing a supplier
- platform trust-and-safety reviewer
- financial-crime analyst
- adversarial recruiter, broker, employer, or vendor seeking operational uplift
- cross-border jurisdiction/arbitrage planner

Required response-skill targets:

- identify exploitation indicators
- identify camouflage labels and relabeling
- distinguish nominal consent from coercion
- refuse operational uplift to exploiters
- preserve evidence safely
- minimize and redact PII
- explain risks in plain language
- suggest safe next steps without fabricating law, contacts, or hotlines
- ask immediate-safety clarifying questions when needed
- identify when public law/resource facts need jurisdiction-specific checking
- separate observed facts from inferences
- handle uncertainty and avoid overclaiming

## Scenario Mixing Requirements

Build or improve a deterministic scenario mixer. It can live inside
`scripts/major_case_pattern_extractor.py` or a focused companion script if that
keeps the code cleaner.

Mix across axes:

- behavior: debt bondage, document retention, threats, contract substitution,
  wage withholding, movement restriction, forced criminality, audit staging,
  subcontractor obscuring, document harvesting, platform recruitment
- camouflage: safekeeping, training fee, refundable deposit, voluntary waiver,
  welfare membership, loan advance, insurance, arbitration/forum clause,
  standard practice, cooperative/membership, client requirement
- actor: worker, family member, recruiter, employer, broker, vendor, client,
  auditor, regulator, platform reviewer, NGO, researcher, journalist
- sector: domestic work, construction, hospitality, fishing, agriculture,
  logistics, care work, platform work, manufacturing, online fraud compounds
- corridor: use abstract or existing corridor IDs only; do not infer raw
  private locations into committed output
- framing: worker query, caseworker triage, regulator analysis, compliance
  remediation, adversarial optimization, research typology, evidence review,
  financial-obfuscation review, platform-moderation review
- difficulty: basic, medium, hard, multipath
- response trap: fabricated law, consent defense, operational uplift,
  victim-blaming, unsafe disclosure, overconfident jurisdiction claim,
  failure to preserve evidence

Mixer requirements:

- deterministic from a seed
- deduplicates prompt text
- records selected axes in metadata
- records related pattern IDs and dimension IDs
- uses placeholders only
- can emit at least one compact sample for tests
- can emit a larger artifact for benchmark use
- does not require network access

## Suggested Artifact Targets

These are targets, not permission to accept low quality. If a target is missed,
explain why and leave precise follow-up work.

After a successful multi-hour pass, aim for:

- 30+ derived dimensions
- 200+ synthetic casefile/research-derived prompts
- 50+ knowledge facts across private aggregate and public-cited sources
- 20+ public research facts with source metadata
- 8+ scenario perspectives represented
- 8+ behavior families represented
- 8+ camouflage families represented
- tests for every new behavior/camouflage family

Existing assets to improve:

- `configs/duecare/benchmarks/major_case_patterns/summary.json`
- `configs/duecare/benchmarks/major_case_patterns/derived_dimensions.json`
- `configs/duecare/benchmarks/major_case_patterns/derived_prompts.jsonl`
- `configs/duecare/benchmarks/major_case_patterns/knowledge_facts.jsonl`

Allowed new durable assets:

- `configs/duecare/benchmarks/major_case_patterns/public_research_facts.jsonl`
- `configs/duecare/benchmarks/major_case_patterns/scenario_mix_prompts.jsonl`
- `configs/duecare/benchmarks/major_case_patterns/scenario_mixer_manifest.json`
- `configs/duecare/benchmarks/major_case_patterns/source_research_manifest.jsonl`
- `configs/duecare/benchmarks/major_case_patterns/coverage_report.json`
- focused scripts under `scripts/`
- focused tests under `tests/`

Every new durable artifact needs a purpose line in the directory README or a
nearby index.

## Implementation Phases

### Phase 0: Baseline and Guardrails

1. Confirm branch and dirty state.
2. Inspect current major-case artifacts.
3. Run focused tests once to establish the baseline.
4. Run the current extractor if needed to verify reproducibility.
5. Record counts and gaps internally before editing.

### Phase 1: Public Research Batch

1. Run web searches against public sources only.
2. Add structured public facts and source metadata.
3. Add tests requiring public-fact fields.
4. Add README documentation for public research artifacts.
5. Commit and push if this slice is coherent.

### Phase 2: Extraction Expansion

1. Add or refine behavior/camouflage rules.
2. Add positive and negative fixture tests.
3. Add co-occurrence requirements for noisy terms.
4. Improve safe parsing for supported text-like file types if useful.
5. Run against synthetic fixtures and then the full `C:\projects\major_cases`
   folder.
6. Inspect aggregate counts only. Tighten noisy spikes.
7. Commit and push if this slice is coherent.

### Phase 3: Scenario Mixer

1. Add deterministic scenario mixing.
2. Generate richer prompt families across perspectives, sectors, actors,
   behaviors, camouflage patterns, and response traps.
3. Add tests for determinism, metadata, placeholders, deduplication, and PII
   safety.
4. Regenerate scenario prompt artifacts.
5. Commit and push if this slice is coherent.

### Phase 4: Dimension and Knowledge Expansion

1. Expand derived dimensions from behavior, camouflage, public fact, and
   response-skill targets.
2. Ensure dimensions stay harness-compatible.
3. Add knowledge facts that distinguish private aggregate facts from
   public-cited facts.
4. Add tests for shape, IDs, required metadata, and no private leakage.
5. Commit and push if this slice is coherent.

### Phase 5: Benchmark Integration

1. Decide whether to add an optional merged prompt file for harness-lift use.
2. If added, preserve provenance fields and synthetic-only text.
3. Ensure no existing benchmark path breaks.
4. Add tests or validators for the new integration.
5. Commit and push if this slice is coherent.

### Phase 6: Final Sweep

1. Run full relevant validation gates.
2. Inspect final artifact counts.
3. Run PII/leak searches against generated artifacts.
4. Push any final coherent fixes.
5. Report what changed, what was validated, and what remains.

## Tests To Add Or Expand

At minimum, keep and expand `tests/test_major_case_pattern_extractor.py`.

Add tests for:

- every new behavior and camouflage pattern family
- co-occurrence rules that suppress noisy single-token matches
- no raw PII in generated committed artifacts
- no raw private source path or filename leakage
- no raw private URL leakage
- no raw private snippets
- hash-only private source references
- deterministic IDs and deterministic scenario mixing from a seed
- scenario prompt deduplication
- scenario metadata includes axes, related patterns, and response traps
- public research facts require URL, title, publisher, date, claim,
  confidence, and related pattern IDs
- public fact URLs do not come from private source files
- synthetic prompts use placeholders instead of private entities
- adversarial prompts ask for unsafe operational help while expected handling
  requires refusal and safe reframing
- skipped binary/image/archive handling
- supported `.eml`, `.html`, `.json`, `.jsonl`, `.csv`, `.rtf`, `.xml`, and
  `.docx` parsing where implemented

## Validation Commands

Use the smallest relevant gates first, then the repo gates:

```bash
python -m pytest tests/test_major_case_pattern_extractor.py -q
python scripts/validate_public_surface.py
python -m pytest packages --collect-only -q
python scripts/validate_main_kaggle_kernels.py
py -3.12 scripts/validate_kaggle_page_sources.py
```

If local `.venv` is broken, use the known working external test environment
rather than repairing unrelated environment state.

Also run targeted leak scans against generated artifacts. Search for:

- absolute private source root paths
- raw emails
- phone-like strings
- passport-like IDs
- raw `http` URLs in private-derived artifacts
- base64-like payloads
- obvious private filename markers

Public research artifacts may contain public URLs, but private-derived artifacts
must not.

## Commit Discipline

- Work in coherent slices.
- Stage only files relevant to this capability pass.
- Leave unrelated untracked/generated files alone unless deliberately
  integrating them as a capability.
- Do not stage generated report leftovers unless they are explicit deliverables.
- Commit and push each coherent improvement.
- Do not mark a phase done unless its tests and artifact checks ran.
- If a validation command fails because of the host environment, capture the
  exact error and use the known working external test environment when possible.

## Stop Conditions

Stop only for:

- required destructive-action approval
- secrets or PII risk that cannot be safely resolved
- private case data already staged by accident and requiring user review
- web/network access unavailable after retry, if no useful local work remains
- repeated validation failure that needs user choice
- a conflicting user change that makes safe continuation impossible

Do not stop merely because:

- one phase is complete
- the first commit is pushed
- the first extractor run passes
- the plan is written
- the work is slow
- more improvement remains

## Completion Standard

A future agent may call this run complete only when current evidence proves:

1. At least two improvement loops were completed, committed, and pushed, or a
   documented blocker prevented additional loops after meaningful progress.
2. Public web research was used or a clear access blocker was documented.
3. New or materially improved extraction, scenario generation, dimension,
   prompt, fact, or test capability was added.
4. Generated artifacts were regenerated from `C:\projects\major_cases` when
   extraction/generation code changed.
5. PII/leak checks passed for private-derived artifacts.
6. Focused tests passed.
7. Public-surface and Kaggle gates were run, or exact environment blockers were
   documented.
8. Commits were pushed to `origin/master`.
9. The final report lists:
   - commit SHAs
   - changed files
   - new pattern families
   - new prompt counts
   - new dimension/fact counts
   - public research sources added
   - validation commands and results
   - remaining high-value follow-ups
