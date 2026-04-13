# Component — `duecare-llm-domains`

> **Status: shipped.** Pack loader + 3 real domain packs, 23 tests
> passing, wheel built, installed.

## What it is

DueCare's pluggable safety domain system. A "domain pack" is a folder of
YAML + JSONL files that defines a safety domain — taxonomy, rubric,
PII spec, seed prompts, evidence base. This package holds the loader
and the `FileDomainPack` class that reads them.

**Domain packs are content, not code.** Adding a new domain is a
directory copy and some YAML editing — zero Python changes.

## Shipped domain packs

| Pack | Categories | Indicators | Seed prompts | Evidence items |
|---|---|---|---|---|
| `trafficking` | 5 | 11 ILO | 12 (with graded responses) | 10 |
| `tax_evasion` | 4 | 8 FATF | 4 | 4 |
| `financial_crime` | 4 | 10 FATF | 3 | 3 |

All three use the **same `FileDomainPack` implementation**. The loader
knows nothing about the specific domain content — that's the whole
point of the abstraction.

## Install

```bash
pip install duecare-llm-domains
```

## Quick start

```python
from duecare.domains import load_domain_pack, discover_all, domain_registry, register_discovered

# Load one pack by id
pack = load_domain_pack("trafficking")
print(pack.card().display_name)  # "Human Trafficking & Migrant-Worker Exploitation"
print(pack.card().version)       # "0.1.0"

# Iterate seed prompts + evidence
for prompt in pack.seed_prompts():
    print(prompt["id"], "-", prompt["text"][:60], "...")

# Discover all packs under configs/duecare/domains/
packs = discover_all()
print(f"Found {len(packs)} domain packs")

# Register all discovered packs in the global registry
n = register_discovered()
print(f"Registered {n} packs")
for pack_id in domain_registry.all_ids():
    print(f"  - {pack_id}")
```

## Directory layout of a domain pack

```
configs/duecare/domains/<id>/
├── card.yaml              # metadata (id, display_name, version, description, license, owner, ...)
├── taxonomy.yaml          # categories, indicators, sectors/jurisdictions, doc refs
├── rubric.yaml            # per-task grading criteria (guardrails, anon, classify, extract, grounding)
├── pii_spec.yaml          # which PII categories matter for this domain
├── seed_prompts.jsonl     # one prompt per line, with graded response examples
├── evidence.jsonl         # one fact per line (laws, statistics, cases, advisories)
├── known_failures.jsonl   # populated by the Validator agent over time
└── README.md              # human-readable intro
```

## Adding a new domain pack

```bash
mkdir -p configs/duecare/domains/medical_misinformation
cd configs/duecare/domains/medical_misinformation

# Copy templates from an existing pack
cp ../trafficking/card.yaml .
cp ../trafficking/taxonomy.yaml .
cp ../trafficking/rubric.yaml .
cp ../trafficking/pii_spec.yaml .

# Edit them for your domain
# Populate seed_prompts.jsonl with your test prompts + graded responses
# Populate evidence.jsonl with your domain's verified facts

# Verify it loads
forge domains list
# -> medical_misinformation should appear
```

Then:

```python
from duecare.domains import load_domain_pack
pack = load_domain_pack("medical_misinformation")
```

No Python code changes.

## Design decisions

### 1. File-backed by default

`FileDomainPack` reads from the filesystem on-demand. `seed_prompts.jsonl`
and `evidence.jsonl` are streamed (not fully loaded), so a pack with
100K prompts doesn't bloat memory.

### 2. YAML for configuration, JSONL for data

Taxonomy, rubric, and pii_spec are small structured configs — YAML is
human-friendly for editing. Seed prompts and evidence are append-only
lists with embedded structure — JSONL keeps diffs clean in git.

### 3. The `DomainPack` protocol is minimal

7 methods: `card()`, `taxonomy()`, `rubric()`, `pii_spec()`,
`seed_prompts()`, `evidence()`, `known_failures()`. Plus 3 attributes:
`id`, `display_name`, `version`. A custom `DomainPack` that hits an
HTTP API or a SQL database would be ~50 lines of code.

## Tests

23 tests, all passing:

- `FileDomainPack` round-trip for every shipped pack (12 tests)
- Loader + `discover_all` edge cases (9 tests)
- Package-level smoke tests verifying trafficking/tax_evasion/
  financial_crime all load correctly (2 tests)

## Status

- [x] `FileDomainPack` implementation
- [x] `discover_all` + `load_domain_pack` loaders
- [x] 3 real domain packs populated
- [x] 19 graded seed prompts across the 3 packs
- [x] 17 evidence items across the 3 packs
- [x] 23 tests passing
- [x] Wheel built + installed

## License

MIT.
