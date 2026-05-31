# Major-case research and benchmark expansion

Use this when the next improvement pass should grow capability: more
casefile-derived behaviors, camouflage patterns, scenario prompts, dimensions,
knowledge facts, tests, and source-grounded research. This is intentionally a
long-form instruction file. The `/goal` objective should reference this file
instead of pasting the full text.

## Copy-paste `/goal`

```text
/goal In C:\Users\amare\OneDrive\Documents\gemma4_comp, work on master without switching branches and follow docs/codex/goal_commands/09_major_case_research_benchmark_expansion.md. Improve the major-case-derived benchmark pipeline with research, web searching, scenario crafting, scenario mixing, stronger tests, more synthetic prompts, more derived dimensions, and more real-world knowledge facts from C:\projects\major_cases while preserving strict PII safety. Do not copy raw casefiles or emit raw snippets, names, filenames, paths, contact details, case IDs, or screenshots. Commit and push scoped improvements when validation passes.
```

## Mission

Iteratively turn the example casefile collection plus public research into a
larger, sharper benchmark and knowledge layer. Optimize for capability, not
cleanup:

- broader exploitation behavior coverage
- richer camouflage and relabeling detection
- better synthetic prompts and scenario families
- scenario mixing across sectors, corridors, actors, and adversarial framings
- source-grounded knowledge facts with dated public citations where available
- stronger tests that protect both capability and PII safety

The private casefiles are pattern inspiration only. They must never become
committed evidence.

## Read first

1. `AGENTS.md`
2. `docs/codex/README.md`
3. `docs/codex/00_do_not_break.md`
4. `docs/codex/00_kernel_compatibility_gate.md`
5. `scripts/major_case_pattern_extractor.py`
6. `tests/test_major_case_pattern_extractor.py`
7. `configs/duecare/benchmarks/major_case_patterns/README.md`
8. `configs/duecare/benchmarks/major_case_patterns/summary.json`
9. `configs/duecare/benchmarks/major_case_patterns/derived_dimensions.json`
10. `configs/duecare/benchmarks/major_case_patterns/derived_prompts.jsonl`
11. `configs/duecare/benchmarks/major_case_patterns/knowledge_facts.jsonl`
12. `configs/duecare/scheme_fingerprints.yaml`
13. current `git status --short --branch`

## Privacy boundary

Hard rules:

- Do not copy `C:\projects\major_cases` files into the repo.
- Do not emit raw source paths, filenames, folder names, snippets, names,
  emails, phones, passports, account numbers, URLs from private files, case IDs,
  screenshots, base64 payloads, or unredacted logs.
- Do not paste private case text into web searches.
- Do not send raw private case text to remote model APIs or web services.
- If model assistance is used, feed only redacted, abstracted, synthetic, or
  aggregate material.
- Source references for private files must stay hash-only, such as `src_...`.
- Synthetic prompts must use placeholders such as `[WORKER]`, `[AGENCY]`,
  `[EMPLOYER]`, `[COUNTRY_A]`, `[COUNTRY_B]`, `[SECTOR]`, and `[AMOUNT]`.
- Keep private-source facts abstract. Public citations may be stored only when
  they come from public web research, not private files.

The right pattern is:

1. private casefile signal -> redacted aggregate behavior
2. public research -> dated citation and generalized knowledge fact
3. scenario crafting -> synthetic benchmark prompt

## Research and web search

Web searching is allowed and encouraged for public grounding, but it must not
leak private case details. Use web research to improve the taxonomy and facts,
not to identify people in the private files.

Preferred source tiers:

1. Primary and intergovernmental sources: ILO, UNODC, IOM, national labor
   agencies, court decisions, statutes, official guidance, regulator reports.
2. NGO and research sources: Polaris, Walk Free, Human Rights Watch, Anti-
   Slavery International, reputable university or policy reports.
3. Investigative journalism only when it adds a documented pattern not covered
   by stronger sources.

For every public fact added, preserve:

- URL
- source title
- publisher
- publication or access date
- short paraphrased claim
- related indicators
- related behavior/camouflage pattern IDs
- confidence: `high`, `medium`, or `low`

Do not hard-code volatile hotlines, office names, live fee caps, wage rules, or
URLs into model-output expectations unless they are represented as dated,
versioned knowledge facts.

## Scenario crafting

Add scenario templates that cover multiple user perspectives:

- worker-support advocate
- caseworker triage
- NGO or regulator analyst
- researcher building a typology
- journalist or investigator validating a pattern
- compliance team asking for safe remediation
- adversarial recruiter or broker seeking operational uplift
- financial obfuscation actor
- platform moderation or marketplace trust-and-safety reviewer
- cross-border jurisdiction/arbitrage planner

Each scenario should test at least one concrete behavior and one response
quality requirement, such as:

- identify exploitation indicators
- distinguish a camouflage label from genuine consent
- refuse operational uplift
- preserve evidence safely
- minimize PII
- give safe next steps without fabricating law or contacts
- ask clarifying questions when immediate safety is unknown

## Scenario mixing

Build a deterministic scenario mixer instead of hand-writing only linear
examples. Mix across axes:

- behavior: debt bondage, document retention, threats, contract substitution,
  wage withholding, movement restriction, forced criminality, audit staging,
  subcontractor obscuring
- camouflage: safekeeping, training fee, refundable deposit, voluntary waiver,
  welfare membership, loan advance, arbitration/forum clause, standard practice
- actor: worker, recruiter, employer, broker, vendor, client, auditor,
  regulator, platform reviewer, family member
- sector: domestic work, construction, hospitality, fishing, agriculture,
  logistics, care work, platform work, online fraud compounds
- corridor: use abstract or existing corridor IDs only; do not infer raw
  private locations into committed output
- framing: worker query, caseworker triage, regulator analysis, compliance
  remediation, adversarial optimization, research typology, evidence review
- difficulty: basic, medium, hard, multipath

The mixer should be deterministic from a seed and should deduplicate prompt
texts. It should emit metadata showing the selected axes and related dimensions.

## Extraction improvements

Improve `scripts/major_case_pattern_extractor.py` incrementally:

- add high-signal pattern rules with positive and negative tests
- use co-occurrence requirements where a single word is too noisy
- track skipped file types and plan safe OCR/vision hooks without committing raw
  OCR text
- improve `.eml`, `.html`, `.json`, `.jsonl`, `.csv`, `.rtf`, `.xml`, and
  `.docx` extraction where safe
- add sector and corridor tags only when abstract, normalized, and PII-safe
- separate private-case aggregate facts from public-cited knowledge facts
- keep generated artifact schemas stable or version them clearly

If a count spike looks noisy, tighten the extractor before accepting the
artifact.

## Assets to improve or create

Existing assets:

- `configs/duecare/benchmarks/major_case_patterns/summary.json`
- `configs/duecare/benchmarks/major_case_patterns/derived_dimensions.json`
- `configs/duecare/benchmarks/major_case_patterns/derived_prompts.jsonl`
- `configs/duecare/benchmarks/major_case_patterns/knowledge_facts.jsonl`

Allowed new assets if useful:

- `configs/duecare/benchmarks/major_case_patterns/public_research_facts.jsonl`
- `configs/duecare/benchmarks/major_case_patterns/scenario_mix_prompts.jsonl`
- `configs/duecare/benchmarks/major_case_patterns/scenario_mixer_manifest.json`
- `configs/duecare/benchmarks/major_case_patterns/source_research_manifest.jsonl`
- focused scripts under `scripts/` if they are reusable and tested
- focused tests under `tests/`

Every durable new artifact needs a purpose line in the directory README or a
nearby index.

## Tests to add

At minimum, keep and expand `tests/test_major_case_pattern_extractor.py`.

Add tests for:

- every new behavior and camouflage pattern family
- co-occurrence rules that suppress noisy single-token matches
- no raw PII in generated committed artifacts
- no raw private source path or filename leakage
- hash-only private source references
- deterministic IDs and deterministic scenario mixing from a seed
- public research facts requiring URL, title, publisher, date, claim,
  confidence, and related pattern IDs
- synthetic prompts using placeholders instead of private entities
- adversarial prompts asking for unsafe operational help while expected
  handling requires refusal and safe reframing
- skipped binary/image/archive handling

## Validation

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

## Commit discipline

- Stage only files relevant to this capability pass.
- Leave unrelated untracked/generated files alone unless deliberately
  integrating them as a capability.
- Do not stage generated report leftovers unless they are explicit deliverables.
- Commit and push each coherent improvement.
- In the final report, include:
  - changed files
  - new pattern families
  - new prompt counts
  - new dimension/fact counts
  - public research sources added
  - validation commands and results
  - remaining high-value follow-ups
