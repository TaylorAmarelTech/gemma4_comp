# Major Case Pattern Derivatives

Purpose: privacy-preserving benchmark assets derived from sensitive casefile
collections. The source evidence stays outside the repository.

This directory intentionally contains only aggregate and synthetic artifacts:

- `summary.json`: counts, skipped extension totals, PII redaction totals, and
  hashed source references.
- `derived_dimensions.json`: candidate scoring dimensions compatible with the
  harness-lift dimension shape.
- `derived_prompts.jsonl`: synthetic benchmark prompts using placeholders such
  as `[WORKER]`, `[AGENCY]`, and `[AMOUNT]`.
- `knowledge_facts.jsonl`: generic facts about exploitation behaviors and
  camouflage patterns.

Privacy rules:

- No raw source paths, filenames, snippets, emails, phone numbers, passports,
  URLs, or case-specific names are emitted.
- Source references are short SHA-256-derived hashes only.
- The generator is `scripts/major_case_pattern_extractor.py`.
