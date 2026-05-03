# DueCare Project Status

> Last updated: 2026-05-02 (readiness suite + smoke test fixes)
> Deadline: 2026-05-18 (16 days remaining)
>
> **For the canonical dashboard:** see [`docs/readiness_dashboard.md`](readiness_dashboard.md).
> **For per-persona happy-path verification:** see [`docs/persona_readiness_audit.md`](persona_readiness_audit.md).
> **For pre-submit verification:** see [`docs/submission_gate_checklist.md`](submission_gate_checklist.md).

## Snapshot (2026-05-02)

- **Validator gate:** `python scripts/validate_notebooks.py` →
  `Validated 77 notebooks successfully`. Green.
- **Adversarial validators:** 42 targeted validators pass across the
  tracked suite.
- **Kaggle kernels:** 77 directories local; every tracked kernel ships
  the canonical hero banner + header table and the shared
  `canonical_hero_code` helper in `scripts/_canonical_notebook.py`.
- **Smoke test:** 24 categories run + passing on 2026-05-02; details in
  [`docs/smoke_test_report_2026-05-02.md`](smoke_test_report_2026-05-02.md).
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

Harness lift (207 prompts, harness OFF vs ON, see harness_lift_report.md):
  +87.5 pp on jurisdiction-specific rules
  +51.2 pp on ILO / international regulations
  +34.1 pp on substance-over-form analysis
  +56.5 pp mean lift across 207/207 prompts
```

**Stock Gemma produces inadequate trafficking safety responses.** The
4-layer harness (Persona / GREP / RAG / Tools) lifts mean score
+56.5 pp without any fine-tuning. Phase 3 Unsloth fine-tuning
(NB 530 / A2 bench-and-tune) encodes the same knowledge permanently.

## Component inventory

### Packages (17 PyPI)

| Package | What it has |
|---|---|
| `duecare-llm-core` | 12 Pydantic schemas, Protocol contracts, Registry, Provenance |
| `duecare-llm-models` | 8 model adapters (incl. Ollama for local Gemma) |
| `duecare-llm-chat` | The 4-layer harness: 42 GREP rules + 26 RAG docs + 4 tools + 394 prompts + 207 5-tier rubrics + 6 required-rubric categories + 16 classifier examples + chat app + classifier app |
| `duecare-llm-domains` | Domain pack loader, 3 domain packs, document pipeline (6 modules) |
| `duecare-llm-tasks` | 9 capability tests, 15 generators, 7 evaluators |
| `duecare-llm-benchmark` | Smoke benchmark + harness-OFF/ON comparison runner |
| `duecare-llm-training` | Unsloth SFT + DPO loops |
| `duecare-llm-agents` | 12 agents, `AgentSupervisor`, Evolution engine (4 modules) |
| `duecare-llm-workflows` | YAML DAG loader + topological runner |
| `duecare-llm-publishing` | HF Hub + Kaggle publisher, markdown reports |
| `duecare-llm-cli` | `duecare` CLI entry point |
| `duecare-llm-engine` | Inference orchestrator (with OTel auto-instrumentation) |
| `duecare-llm-evidence-db` | Structured journal store |
| `duecare-llm-nl2sql` | Natural-language queries over evidence-db |
| `duecare-llm-research-tools` | Tavily/Brave/Serper/DuckDuckGo/Wikipedia + browser |
| `duecare-llm-server` | FastAPI surface (with tenancy / rate-limit / metering / metrics) |
| `duecare-llm` (meta) | CLI + re-exports + installs all of the above |

### Generators (15), evaluators (7), demo app (12 API endpoints), pipeline (8 stages)

Unchanged. See `docs/architecture.md` for the canonical list.

### Data assets

- 394 example prompts (the live demo + chat playgrounds)
- 207 5-tier rubrics (per-prompt graded examples, worst → best)
- 6 required-rubric categories with 66 criteria total
- 16 classifier examples (6 with SVG document mockups)
- 42 GREP rules across 5 categories (Python harness)
- 26-doc RAG corpus (full ILO C029/C181/C095/C189 + POEA MCs +
  national statutes + Palermo + ICRMW + Saudi kafala reforms + ...)
- 11 ILO C029 forced-labour indicators
- 20 migration corridors (Asia + GCC + LATAM + West Africa kafala +
  refugee routes Syria→Germany / Ukraine→Poland)
- 4 function-calling tools (corridor fee cap, fee camouflage, ILO
  indicator, NGO intake)
- 74,567 trafficking prompts (private benchmark; public subset via
  `taylorsamarel/duecare-trafficking-prompts`)
- 5 evaluation rubrics (54 criteria) in the benchmark
- 31 verified legal provisions (15 jurisdictions)

### Tests: 55 files (16 in tests/ + 39 in packages/), ~436 cases. Total Python LOC: ~47K.

## Kaggle notebooks (77 local)

Full inventory is auto-generated at
`docs/current_kaggle_notebook_state.md`. Highlights:

- 77 notebook mirrors match 77 kernel directories locally (5 mirrors
  restored 2026-05-02 from kernel sources).
- The submission shape is **6 core + 5 appendix** (per the canonical
  `kaggle/<purpose>/` layout in [`docs/FOR_JUDGES.md`](FOR_JUDGES.md)).
- The 76-notebook research arc lives in `kaggle/kernels/` and serves
  reproducibility for the Phase 1-3 pipeline.
- Public live-state promotion should be checked against Kaggle at push
  time; the authoritative local inventory is
  `docs/current_kaggle_notebook_state.md`.

## Kaggle datasets (12)

| Dataset | Slug |
|---|---|
| DueCare LLM Wheels (legacy meta) | `taylorsamarel/duecare-llm-wheels` |
| DueCare Trafficking Prompts | `taylorsamarel/duecare-trafficking-prompts` |
| Per-notebook wheels datasets (×11) | `taylorsamarel/duecare-<purpose>-wheels` |

Per-notebook datasets cover all 11 submission notebooks (6 core +
5 appendix). The legacy meta dataset is being retired post-hackathon
in favor of the per-notebook split.

## Android sibling repo status (2026-05-02)

- **v0.9.0 APK live** at the duecare-journey-android sibling
  ([release tag](https://github.com/TaylorAmarelTech/duecare-journey-android/releases)).
- v0.9 ships: cloud Gemma 4 routing (Ollama / OpenAI-compat / HF
  Inference) + 6 on-device variants with mirror-fallback URLs + intel
  domain knowledge layer (42 GREP rules + 11 ILO indicators +
  **20 corridor profiles**) + structured Add-Fee dialog with
  auto-LegalAssessment + RefundClaim drafting + image picker for
  evidence + Reports tab with NGO intake doc generator + guided
  intake wizard + risk auto-tagging + 5 new sector-specific GREP
  rules (kafala-huroob, H-2A/H-2B, fishing-vessel, smuggler-fee,
  domestic-locked-in).
- v0.10 candidates (post-submission): localized chat UI strings (es +
  tl), photo OCR for contract/receipt/passport, per-file Tink
  encryption for journal attachments.

## Deployment topologies (5)

- `docs/deployment_topologies.md` — master selector across five
  topologies (single-component local / NGO-office edge / server +
  thin clients / on-device only / hybrid edge LLM + cloud knowledge).
- `examples/deployment/` — runnable examples for each topology
  (Docker Compose all-in-one, single-file Python CLI, Mac mini /
  NUC edge box, server + 8 client patterns, hybrid privacy contract).

## What's next (priority order)

### P0 - blocks submission

- [ ] **Record 3-minute YouTube video** per `docs/video_script.md`
  (single highest-leverage deliverable; user-only).
- [ ] **Push 8 remaining notebooks to Kaggle** (3 of 11 already live;
  push spread across 4 days due to daily rate-limit; user-only).
- [ ] **Run A2 bench-and-tune (Unsloth SFT + DPO + GGUF + HF push)**
  on Kaggle T4×2 once GPU quota resets; user-only.

### P1 - significantly improves score

- [ ] HF Hub fine-tuned model
  (`taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0`)
  uploaded with model card.
- [ ] GGUF Q8_0 export for llama.cpp Special Technology track.
- [ ] Native review of Tagalog + Spanish worker-self-help drafts.
- [x] Android v0.9 APK in production with cloud + on-device routing.
- [x] Readiness rubric suite consolidated (4 docs replacing ~10).

### P2 - nice to have

- [ ] Backport 5 Android v0.9 GREP rules into Python harness (closes
  the 37/42 surface-count gap).
- [ ] Full 74K prompt evaluation via Ollama locally.
- [ ] Browser extension prototype polish
  (`deployment/browser_extension/`).
- [ ] Additional domain pack (medical misinformation).
- [ ] DOI/Zenodo deposit for the corpus.

## Rubric mapping (latest scores)

Per [`docs/readiness_dashboard.md`](readiness_dashboard.md):

| Axis | Today | Reachable by 5/18 |
|---|---|---|
| Impact & Vision (40) | 32 / 40 (B+) | 36 / 40 (A–) |
| Video Pitch & Storytelling (30) | 5 / 30 (F) | 25 / 30 (A–) |
| Technical Depth & Execution (30) | 28 / 30 (A–) | 30 / 30 (A) |
| **Total** | **65 / 100 (D+)** | **91 / 100 (A–)** |

The fall-off from "what we built" to "what scores" is **the missing
video** (-25 to -30 points). Everything else is fixable within the
remaining 16 days.
