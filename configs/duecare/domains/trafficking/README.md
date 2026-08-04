# Trafficking domain pack

Flagship domain pack for DueCare. Covers migrant-worker trafficking,
forced labor, debt bondage, recruitment-fee fraud, kafala-system abuse,
sex-trafficking cover patterns, and the migrant-worker / financial-crime
intersection (recruitment-fee laundering, structuring, novation,
beneficial-ownership concealment).

## Contents

| File | Purpose | Approx. count |
| --- | --- | --- |
| `card.yaml` | Pack metadata + domain card | 1 |
| `taxonomy.yaml` | Categories, ILO indicators, sectors, migration corridors, documentation references | 5 categories / 11 indicators / 10+ sectors / 10+ corridors |
| `rubric.yaml` | Per-task grading criteria | 74-dim rubric |
| `pii_spec.yaml` | PII categories for the anonymization gate | 12+ categories |
| `seed_prompts.jsonl` | Seed prompts with graded response examples + worker / agency / researcher query examples + financial-crime intersection prompts | 74,640 entries |
| `evidence.jsonl` | Verified reference items (laws, statistics, case studies, advisories) | 10+ items |
| `known_failures.jsonl` | Populated after each model-run | grows over time |
| `examples/illicit_ads.jsonl` | Composite recruitment-ad red-flag corpus (Facebook, Instagram, Telegram, WhatsApp, Zalo, Viber, religious-group channels) with statute mappings | 12 ads |
| `examples/illicit_conversations.jsonl` | Composite multi-turn recruiter / worker / caseworker / inspector / journalist exchanges with role/timestamp metadata | 10 conversations |
| `examples/text_conversation_examples.txt` | Plain-text rendering of the first 5 conversations | 5 transcripts |

## Synthetic entities, and what these corpora do and do not contain

**Every person, company, agency, licence number, registration number,
phone number, and case ID across this pack is an invented composite.**
That applies to `seed_prompts.jsonl` and to the benchmark corpora under
`configs/duecare/benchmarks/`, not only to `examples/`. Company names are
deliberately plausible, because a benchmark built from obviously-fake
names would not test anything -- but no entity in these files refers to a
real organisation, and any resemblance is coincidental. Regulator licence
numbers follow real-world *formats* with fabricated *values*. Statute
citations are the one deliberate exception: those are public record and
are meant to be verifiable.

**Prompts are adversarial by design.** Many rows are written from the
point of view of someone trying to get a model to bless an exploitative
scheme. They exist to test whether a model refuses. They are not
instructions, endorsements, or advice.

**Stored model completions are withheld.** Where a row records what a
model actually answered, the response *text* is redacted and only its
grade, outcome, and model id remain -- see
`scripts/redact_seed_prompt_responses.py`. Publishing adversarial prompts
together with their grades is standard safety-benchmark practice;
republishing the completions that succeeded is not, so those bodies stay
out of the public corpus.

The `FileDomainPack` loader does not currently scan `examples/` -- it
reads only the named files above -- so the directory is reviewer-facing
documentation and training-data scaffolding.

## Knowledge layers consumed via `duecare.chat.harness`

The full content layer that grounds DueCare's chat / process /
extraction harnesses lives under `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`:

- `GREP_RULES`: 220+ pattern-based rules across categories A-MM,
  including 7 categories added 2026-05-20 (sex-trafficking and GBV,
  vulnerability targeting, religious-cover recruitment, fishing-vessel
  document holding, compound-scam recruitment, athlete-visa abuse,
  normal worker FAQ triggers) plus 2 categories added 2026-05-21
  (LL recovery / restitution queries, MM scam-cover pretexts).
- `RAG_CORPUS`: 79+ retrievable knowledge documents covering ILO
  conventions, UN Palermo Protocol, UNODC Global Reports, ILO Global
  Estimates, corridor-specific labour regimes (POEA / DMW, BP2MI,
  BMET, FEA, EPS, TITP / Ikusei Shuro, Israel B/1), supply-chain
  transparency law, FATF cross-applied to human-trafficking finance,
  and NGO / civil-society frameworks (Polaris, GAATW, IOM IRIS).
- `_personas.json`: 15 review personas covering active caseworker,
  embassy officer, peer supporter, social worker, platform trust and
  safety, faith-community helper, labour inspector, recruiter
  compliance, and more.

## Adjacency

Financial crime (`configs/duecare/domains/financial_crime/`) and tax
evasion (`configs/duecare/domains/tax_evasion/`) are adjacency packs:
they share the same harness primitives but are not the primary product
focus. See the migrant-worker / financial-crime intersection prompts
in `seed_prompts.jsonl` (`fin_intersect_*`) for the bridging examples.

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
