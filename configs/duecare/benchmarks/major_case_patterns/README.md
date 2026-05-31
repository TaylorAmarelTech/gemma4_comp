# Major Case Pattern Derivatives

Purpose: privacy-preserving benchmark assets derived from sensitive casefile
collections plus public research facts. The private source evidence stays
outside the repository.

This directory intentionally contains only aggregate and synthetic artifacts:

- `summary.json`: counts, skipped extension totals, PII redaction totals, and
  hashed source references.
- `derived_dimensions.json`: candidate scoring dimensions compatible with the
  harness-lift dimension shape.
- `derived_prompts.jsonl`: synthetic benchmark prompts using placeholders such
  as `[WORKER]`, `[AGENCY]`, and `[AMOUNT]`.
- `scenario_mix_prompts.jsonl`: deterministic synthetic scenario-mixer prompts
  across perspectives, sectors, behavior families, camouflage patterns, and
  response traps.
- `knowledge_facts.jsonl`: generic facts about exploitation behaviors and
  camouflage patterns, including public-fact-derived entries without raw
  private evidence.
- `public_research_facts.jsonl`: paraphrased public research facts with source
  URLs and dated metadata.
- `source_research_manifest.jsonl`: public source metadata used by the research
  facts.
- `coverage_report.json`: generated counts and coverage checks for dimensions,
  prompts, facts, public sources, perspectives, sectors, and response traps.

Privacy rules:

- No raw source paths, filenames, snippets, emails, phone numbers, passports,
  private URLs, or case-specific names are emitted from private casefiles.
- Private source references are short SHA-256-derived hashes only.
- Public research artifacts may contain public URLs, but private-derived
  prompts and facts stay synthetic or aggregate.
- The generator is `scripts/major_case_pattern_extractor.py`.
