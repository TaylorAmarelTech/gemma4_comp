# DueCare Project Status

> Last updated: 2026-04-18 (post-cleanup pass)
> Deadline: 2026-05-18 (30 days remaining)

## Snapshot

- **Validator gate:** `python scripts/validate_notebooks.py` ->
  `Validated 76 notebooks successfully`. Green.
- **Adversarial validators:** 42 targeted validators pass across the
  tracked suite.
- **Kaggle kernels:** 76 directories local; every tracked kernel now
  ships the canonical hero banner + header table and the shared
  `canonical_hero_code` helper in `scripts/_canonical_notebook.py`.
- **Slug source of truth:** `scripts/_public_slugs.py` is the single
  `PUBLIC_SLUG_OVERRIDES` table. `scripts/kaggle_live_slug_map.json`
  is still consumed by the index renderer and stays as a live-state
  probe artifact.
- **Shared helpers:** `scripts/_public_slugs.py` and
  `scripts/_canonical_notebook.py` now hold the duplication that used
  to be scattered across builders.

## Local baseline (Gemma 4 E4B via Kaggle + Gemma 3 4B via Ollama)

```
Gemma 4 E4B on Kaggle T4 (50 graded prompts, NB 100):
  Mean keyword score: 0.610
  Pass rate:          20%
  Explicit-harmful rate: 0%
  HARD_VIOLATION rate (V3 reclassification): 28%
  DETECTION_FAIL rate (V3):                  46%
  FULL_SUCCESS rate (V3):                    0%

Gemma 3 4B via Ollama (n=5 smoke check):
  Plain:    0.484 mean, 20% pass
  + RAG:    0.594 mean, 40% pass (+23%)
  + Guided: 0.620 mean, 40% pass (+28%)
```

**Stock Gemma produces inadequate trafficking safety responses.**
Context injection lifts scores 23-28% without fine-tuning. Phase 3
Unsloth fine-tuning (NB 530) encodes the same knowledge permanently.

## Component inventory

### Packages (8 PyPI)

| Package | What it has |
|---|---|
| `duecare-llm-core` | 12 Pydantic schemas, Protocol contracts, Registry, Provenance |
| `duecare-llm-models` | 8 model adapters (incl. Ollama for local Gemma) |
| `duecare-llm-domains` | Domain pack loader, 3 domain packs, document pipeline (6 modules) |
| `duecare-llm-tasks` | 9 capability tests, 15 generators, 7 evaluators |
| `duecare-llm-agents` | 12 agents, `AgentSupervisor`, Evolution engine (4 modules) |
| `duecare-llm-workflows` | YAML DAG loader + topological runner |
| `duecare-llm-publishing` | HF Hub + Kaggle publisher, markdown reports |
| `duecare-llm` (meta) | CLI + re-exports |

### Generators (15), evaluators (7), demo app (12 API endpoints), pipeline (8 stages)

Unchanged from the previous status. See `docs/architecture.md` for the
canonical list.

### Data assets

- 74,567 trafficking prompts (private benchmark; public subset via
  `taylorsamarel/duecare-trafficking-prompts`).
- 5 evaluation rubrics (54 criteria).
- 31 verified legal provisions (15 jurisdictions).
- 26 + 32 migration corridors.
- 29 scheme fingerprints.
- 111-entry RAG knowledge base.

### Tests: 194 passing. Total Python LOC: 47,351.

## Kaggle notebooks (76 local)

Full inventory is auto-generated at
`docs/current_kaggle_notebook_state.md`. Highlights:

- 76 notebook mirrors currently match 76 kernel directories locally.
- 130, 140, 150, 155, 160, 170, and 180 were rebuilt from builders in
  this session and passed their targeted validators.
- 150 / 155 / 160 are no longer lightweight placeholders; they now use
  the canonical header, troubleshooting, handoff, and CPU-safe fallback
  pattern used by the stronger 170 / 180 builders.
- Public live-state promotion should be checked against Kaggle at push
  time; the authoritative local inventory is `docs/current_kaggle_notebook_state.md`.

## Kaggle datasets (2)

| Dataset | Contents | Slug |
|---|---|---|
| DueCare LLM Wheels | 8 package wheels (v0.1.0) | `taylorsamarel/duecare-llm-wheels` |
| DueCare Trafficking Prompts | Public subset + 5 rubrics | `taylorsamarel/duecare-trafficking-prompts` |

## What's next (priority order)

### P0 - blocks submission

- [ ] Push the refreshed notebook batch to Kaggle and reconcile live-state drift.
- [ ] Phase 3 Unsloth fine-tune (NB 530) actual run + HF Hub weights.
- [ ] Record 3-minute YouTube video per `docs/video_script.md`.
- [ ] Finalize `docs/writeup_draft.md` with Phase 3 numbers once in.
- [ ] Public GitHub push (repo is local; see
  `docs/prompts/30_project_checkpoint.md` release ladder).

### P1 - significantly improves score

- [ ] Phase 2 cross-model comparison results (E2B vs E4B, NB 510).
- [ ] Fine-tuned model on HF Hub
  (`TaylorScottAmarel/duecare-gemma-4-e4b-safetyjudge-v0.1.0`).
- [ ] GGUF export for llama.cpp Special Technology track.
- [ ] LiteRT export for the mobile on-device story.

### P2 - nice to have

- [ ] Full 74K prompt evaluation via Ollama locally.
- [ ] Browser extension prototype polish
  (`deployment/browser_extension/`).
- [ ] Additional domain pack (medical misinformation).
- [ ] Interactive HTML report companion to the writeup.

## Rubric mapping (unchanged)

- **Impact and Vision (40).** 130 shows the corpus concretely; 210,
  220, 230, 240 show the on-device argument; 399 closes the section
  honestly. Video opens on a named composite worker; closes on named
  NGOs.
- **Video Pitch and Storytelling (30).** 3-minute YouTube,
  `pip install duecare-llm` one-liner visible, stock-vs-fine-tuned
  side-by-side from 210 and 530.
- **Technical Depth and Execution (30).** 8 PyPI packages, typed
  Protocols, folder-per-module layout, CI-verified tests, 76 Kaggle
  notebooks with canonical titles, fine-tuned model on HF Hub,
  llama.cpp and LiteRT deployment artifacts.
