# Maintenance guides — per-component edit + extend instructions

> One focused guide per pluggable component. Same audience as
> `contributing_curator_blocks.md` — stakeholders (NGO partners,
> jurists, language experts, regulators) who want to extend or
> maintain a piece of Duecare without reading the whole codebase.

## Guides in this directory

| Component | What you can change | Guide |
|---|---|---|
| **Personas** | The 40-year-expert system prompt + the multi-persona library | [`personas.md`](personas.md) |
| **GREP rules** | 100+ regex KB rules with citation, severity, ILO indicator tag | [`grep_rules.md`](grep_rules.md) |
| **RAG corpus** | 50+ docs (ILO conventions, statutes, NGO briefs) — adding new statutes, refreshing amended ones, BM25 reindex | [`rag_corpus.md`](rag_corpus.md) |
| **Tool functions** | 5 function-calling lookups (corridor fee cap, fee camouflage, ILO indicator, NGO intake, ILO Convention) | [`tool_functions.md`](tool_functions.md) |
| **Online search** | Provider chain (DuckDuckGo / Brave / Tavily / Wikipedia / arbitrary URL) + BYOK config | [`online_search.md`](online_search.md) |
| **Curator-JSON blocks** | 12 versioned JSON files for stakeholder PRs | [`../contributing_curator_blocks.md`](../contributing_curator_blocks.md) |
| **Domain packs** (whole new domains) | YAML + JSONL configs for medical / financial / etc. | [`../EXTENDING.md`](../EXTENDING.md) |

## How the components fit together

See [`../component_diagram.md`](../component_diagram.md) for the
end-to-end ERD: which components live where, what API each exposes,
how data flows.

## Stakeholder workflow (general)

For any of the components above:

1. **Read the guide** for that component
2. **Make your edit** (curator JSON edit, GREP rule add, etc.)
3. **Run the validator**:
   - `python scripts/validate_curator_blocks.py` (for curator JSON)
   - `python scripts/verify.py` (for harness counts)
4. **Run the tests** that touch your component:
   - `pytest packages/duecare-llm-chat/tests/test_harness_v3_6.py`
5. **Open a PR** against `master` with:
   - One-line summary of what changed
   - One-paragraph why (especially important for legal claims +
     weight tuning + threshold changes)
   - Citations / sources for any legal updates

A reviewer with the matching expertise (jurist for legal blocks,
native speaker for non-English signals, methodologist for weights,
infosec for cryptography, eval team for thresholds) reviews and
merges.

## Versioning + release cadence

- **Curator JSON edits** ship in the next chat-package wheel
  (auto-built by CI on merge to master).
- **Code changes** to grader logic (e.g. adding a new dim, changing
  the gaming defense) require a chat-package version bump per
  semver.
- **Whole-component additions** (a new layer, a new grade mode)
  require an architecture review + an update to the deployment
  topology doc.

## Reproducibility commitment

Every grade carries a `(model, git_sha, dataset_version)` triple.
When you make a change, the next eval run will produce a
deterministic delta tied to your commit SHA. The eval-set itself
is reproducible from `scripts/remeasure_v36_lift.py`.
