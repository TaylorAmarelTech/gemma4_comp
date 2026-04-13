# Trafficking domain pack

Flagship domain pack for the Duecare. Covers migrant-worker trafficking,
forced labor, debt bondage, recruitment fee fraud, and kafala system abuse.

## Contents

- `card.yaml` - metadata
- `taxonomy.yaml` - 5 categories, 11 ILO indicators, 10 sectors, 10 migration corridors, 7 documentation references
- `rubric.yaml` - per-task grading criteria
- `pii_spec.yaml` - PII categories for anonymization
- `seed_prompts.jsonl` - 12 seed prompts with graded response examples
- `evidence.jsonl` - 10 verified reference items (laws, statistics, case studies, advisories)
- `known_failures.jsonl` - populated after first run

## Usage

```python
from duecare.domains import load_domain_pack

pack = load_domain_pack("trafficking")
print(pack.card().display_name)

for prompt in pack.seed_prompts():
    print(prompt["id"], "-", prompt["text"])
```

## License

MIT. See root LICENSE.
