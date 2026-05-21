# Tax Evasion domain pack (adjacency proof)

DueCare's primary domain is **migrant-worker safety / human
trafficking** -- see `configs/duecare/domains/trafficking/`.

This pack is an **adjacency proof**: it demonstrates that the same
`FileDomainPack` implementation, harness, and rubric structure
applies to tax-evasion patterns (transfer-pricing abuse, undisclosed
offshore, false-deduction construction, treaty shopping) under the
same architecture. It is intended for partners who want to run
DueCare's detection on tax-evasion problems that are NOT routed
through a migrant-worker case. Where tax-evasion patterns DO appear
inside migrant-worker exploitation (e.g. recruitment-fee laundering,
shell-company contract structures), they're covered in the
trafficking pack itself.

The primary product narrative remains migrant-worker protection.

## Contents

- `card.yaml` - metadata
- `taxonomy.yaml` - 4 categories, 8 FATF indicators, 5 jurisdictions
- `rubric.yaml` - guardrails + classification + extraction rubrics
- `pii_spec.yaml` - PII categories
- `seed_prompts.jsonl` - 4 seed prompts with graded responses
- `evidence.jsonl` - 4 reference items (US IRC, FATCA, OECD BEPS, FATF)
