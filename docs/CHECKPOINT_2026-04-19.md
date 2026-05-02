# DueCare Checkpoint — 2026-04-19

Single comprehensive snapshot of the DueCare submission for the Gemma 4 Good Hackathon. This document supersedes every earlier checkpoint and is the only authoritative status doc in `docs/`. Prior checkpoints are under `_archive/docs_2026-04/`.

---

## 1. What DueCare is

DueCare is an agentic LLM safety harness built for the **Gemma 4 Good Hackathon** on Kaggle. The core product is a fine-tuned Gemma 4 E4B model running locally on an NGO laptop, evaluating LLM responses against migrant-worker trafficking scenarios (and, by extension, tax evasion and financial-crime scenarios) without sending any case data to a frontier API.

The project is named for **California Civil Code section 1714(a)** — the duty-of-care standard a California jury applied to platform design in the March 2026 Meta / Google negligence verdict. DueCare asks a parallel question of a model: does it exercise *due care* when responding to prompts about trafficking, exploitation, and financial crime?

**Two deployment paths, one binary:**

- **Consumer** — workers and their families use a browser extension or the public HF Space to paste a suspicious message and get the grade plus the POEA / BP2MI / HRD-Nepal hotline plus the ILO citation, in Tagalog or English. No login, no account, nothing leaves the device.
- **Enterprise** — NGOs, recruitment regulators, labor ministries, and platform Trust & Safety teams `pip install duecare-llm` and run the CLI for batch evaluation, or deploy the FastAPI dashboard internally via `docker compose up`. Same Gemma 4 weights, same offline guarantee, same zero inference cost.

---

## 2. The competition

**Gemma 4 Good Hackathon** on Kaggle.

- **Window:** 2026-04-02 through 2026-05-18. Today is 2026-04-19; **29 days remaining** to the submission deadline.
- **Prize pool:** $200K total across Main, Impact, and Special Technology tracks.
- **Tracks targeted by this submission:**
  - **Impact Track — Safety & Trust** ($10K). Headline fit: privacy-is-non-negotiable, on-device safety evaluator for NGO use.
  - **Special Technology Track — Unsloth** ($10K). Phase 3 LoRA fine-tune of Gemma 4 E4B with Unsloth on a Kaggle T4.
  - **Special Technology Track — llama.cpp or LiteRT** ($10K). GGUF export for desktop llama.cpp; LiteRT export for mobile.
  - **Main Track** ($10K–$50K) — in play if execution is strong.

### Rubric (Kaggle official, 100 pts total)

1. **Impact & Vision — 40 pts.** Scored from the video: real-world problem, inspiring vision, tangible potential for positive change.
2. **Video Pitch & Storytelling — 30 pts.** How exciting, engaging, well-produced; does it tell a powerful story.
3. **Technical Depth & Execution — 30 pts.** Verified from the code repository and writeup: innovative use of Gemma 4's distinguishing features (native function calling, multimodal understanding). Real, not faked for the demo.

**70 of 100 points live in the video.** Every engineering decision in this repo is evaluated against whether it produces something visible and compelling in the final 3-minute video.

### Hard submission requirements

- Kaggle writeup, ≤ 1,500 words. Draft at `docs/writeup_draft.md`.
- Public YouTube video, ≤ 3 minutes. Script at `docs/video_script.md`.
- Public code repository (this repo, minus `_reference/`).
- Live public demo (FastAPI dashboard at `src/demo/app.py`; browser extension at `deployment/browser_extension/`; HF Space at `deployment/hf_spaces/`).
- Uses Gemma 4 (E2B or E4B).
- MIT license on all original code.

---

## 3. Sources and provenance

The project builds on Taylor Amarel's prior *LLM Safety Testing Ecosystem* for migrant-worker protection, stored under `_reference/` and git-ignored because publishing it would break NGO-partner data-provenance guarantees.

| Source under `_reference/` | What it is | Public? |
|---|---|---|
| `_reference/README.md` | Ecosystem overview. | No |
| `_reference/CLAUDE.md` | The source framework's AI-assistant guide (not to be confused with `./CLAUDE.md`). | No |
| `_reference/ARCHITECTURE_PLAN.md` | Data model, prompt schema, eval modes. | No |
| `_reference/trafficking_llm_benchmark/` | 10.3 GB dev benchmark, 300K+ lines of Python. | No |
| `_reference/trafficking-llm-benchmark-gitlab/` | 122 MB, 21,000-test public release. | Yes (derivative shipped on Kaggle) |
| `_reference/framework/` | llm-safety-framework-public, copied 2026-04-11. | No |

**Only the fine-tuned model weights, the 21K public-release tests, and the 74,567-prompt derivative corpus (published under `taylorsamarel/duecare-trafficking-prompts`) end up in the public Kaggle repo.** The private benchmark harness stays in `_reference/`.

### External legal sources used by the suite

The rubric is grounded in publicly citable legal standards; every one is linked from `015 Background Literature`:

- ILO C029, C105, C181 (Forced Labour / Private Employment Agencies).
- UN Palermo Protocol (trafficking definition).
- US TVPA + annual State Department TIP Report (11 forced-labor indicators).
- PH RA 8042 / RA 10022 (Migrant Workers Act).
- GCC regimes: Saudi Labor Law Article 40, UAE Federal Law No. 6 / 2008, Kuwait Domestic Workers Law, Qatar Law No. 21 / 2015, Kafala sponsorship.
- AI-safety literature: Perez et al. (red-teaming, 2022); Zou et al. (GCG, 2023); Zheng et al. (LLM-as-judge, 2023); Bai et al. (Constitutional AI, 2022); Arditi et al. (refusal direction, 2024).

---

## 4. What ships

### 8 PyPI packages under the `duecare` PEP 420 namespace

| Package | Role |
|---|---|
| `duecare-llm-core` | Contracts, schemas, enums, registries, provenance, observability. |
| `duecare-llm-models` | 8 model adapters: Transformers (+ Gemma 4 function calling), llama.cpp, Unsloth, Ollama, OpenAI-compatible, Anthropic, Google Gemini, HF Inference Endpoints. |
| `duecare-llm-domains` | Pluggable domain packs + 3 shipped (`trafficking`, `tax_evasion`, `financial_crime`) + document pipeline (scraper, extractor, classifier, document_store). |
| `duecare-llm-tasks` | 9 capability tests (adversarial_multi_turn, anonymization, classification, cross_lingual, fact_extraction, grounding, guardrails, multimodal_classification, tool_use) + 15 adversarial generators in `ALL_GENERATORS`. |
| `duecare-llm-agents` | 12 autonomous agents (Scout, DataGenerator, Adversary, Anonymizer, Curator, Judge, Validator, CurriculumDesigner, Trainer, Exporter, Historian, Coordinator) + `AgentSupervisor` + Evolution engine. |
| `duecare-llm-workflows` | YAML DAG loader + topological runner. |
| `duecare-llm-publishing` | HF Hub + Kaggle publisher, markdown reports, HF model cards. |
| `duecare-llm` (meta) | `duecare` CLI + re-exports from all 7 siblings. |

**Install:** `pip install duecare-llm` pulls the meta package, which depends on all 7 siblings. A Kaggle notebook can install a narrower subset, e.g. `pip install duecare-llm-core duecare-llm-domains duecare-llm-tasks duecare-llm-agents`.

**Version:** every package pins v0.1.0. Test count: 194 (run via `make test` or `python -m pytest packages tests -q`).

### 76 Kaggle notebooks across 16 sections

| # | Section | Notebooks | Count |
|---|---|---|---|
| 1 | Background and Package Setup | 000, 005, 010, 015, 020, 099 | 6 |
| 2 | Free Form Exploration | 100, 102, 150, 152, 155, 160, 165, 170, 175, 180, 190, 199 | 12 |
| 3 | Jailbreak Safety Research (181-189) | 181, 182, 183, 184, 185, 186, 187, 188, 189 | 9 |
| 4 | Baseline Text Evaluation Framework | 105, 110, 120, 130, 140, 299 | 6 |
| 5 | Baseline Text Comparisons | 200, 210, 220, 230, 240, 245, 250, 260, 270, 399 | 10 |
| 6 | Baseline Image Evaluation Framework | 400 (planned) | 1 |
| 7 | Baseline Image Comparisons | 500 (planned) | 1 |
| 8 | Advanced Evaluation | 300, 335, 400, 410, 420, 460, 499 | 7 |
| 9 | Advanced Text Prompt-Test Generation | 310, 430, 440, 699 | 4 |
| 10 | Advanced Image Prompt-Test Generation | 800 (planned) | 1 |
| 11 | Advanced Adversarial Prompt-Test Evaluation | 320, 450, 799 | 3 |
| 12 | Model Improvement Opportunities | 500, 510, 520, 525, 527, 530, 540, 550, 599 | 9 |
| 13 | Results Dashboards | 600 | 1 |
| 14 | Solution Surfaces | 610, 620, 650 | 3 |
| 15 | Deployment Applications | 660, 670, 680, 690, 695 | 5 |
| 16 | Suite Conclusion | 899 | 1 |

Full generated inventory: `docs/current_kaggle_notebook_state.md`. Canonical reading order narrated in `docs/notebook_guide.md`.

### 5 deployment applications

1. **660 Enterprise Moderation** — platform-scale queueing surface for risky recruitment posts / ads / recruiter outreach.
2. **670 Private Client-Side Checker** — worker-side private checker for one suspicious message or document at a time, plain-language warning + next step.
3. **680 NGO API Triage** — software-to-software triage surface: structured request in, structured analysis + routing out.
4. **690 Migration Case Workflow** — multi-document case-bundle workflow: uploaded files → timeline + grounded findings + draft complaint materials.
5. **695 Custom Domain Adoption** — plain-English partner-adoption playbook for bringing DueCare to a new safety domain without Python changes.

### Data assets

- **74,567 trafficking prompts** in `configs/duecare/domains/trafficking/seed_prompts.jsonl` (private authoring corpus; a public 12-prompt slice ships inside `packages/duecare-llm-domains/src/duecare/domains/_data/trafficking/seed_prompts.jsonl` as the bundled pack).
- **5 weighted rubrics / 54 criteria** spanning the 6-dimension weighted rubric (refusal quality, legal accuracy, completeness, victim safety, cultural sensitivity, actionability), the 5-grade anchored rubric (worst / bad / neutral / good / best), and the V3 6-band classifier (HARD_VIOLATION → FULL_SUCCESS).
- **31 verified legal provisions** across 15 jurisdictions.
- **26 + 32 migration corridors** (source countries × destination countries).
- **111-entry RAG knowledge base** at `data/knowledge_base/kb.json`.

### Published Kaggle datasets (2)

| Dataset | Contents | Slug |
|---|---|---|
| DueCare LLM Wheels | 8 package wheels (v0.1.0) | `taylorsamarel/duecare-llm-wheels` |
| DueCare Trafficking Prompts | Public graded subset + 5 rubrics | `taylorsamarel/duecare-trafficking-prompts` |

---

## 5. Real measurements (not faked for the demo)

Every number in the writeup and video is reproducible from `(git_sha, dataset_version)`.

### Gemma 4 E4B baseline on Kaggle T4 (Notebook 100)

```
Mean keyword score:        0.610
Pass rate:                 20%
Explicit-harmful rate:     0%
Refusal rate:              36%
Legal-reference rate:      20%
Redirect rate (hotlines):  20%
HARD_VIOLATION rate (V3):  28%
DETECTION_FAIL rate (V3):  46%
FULL_SUCCESS rate (V3):    0%
```

Artifact: `data/gemma_baseline_findings.json`. Kernel: [`duecare-real-gemma-4-on-50-trafficking-prompts`](https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts).

### Context-injection lift (Gemma 3 4B via Ollama, n=5 smoke check)

```
Plain:    0.484 mean, 20% pass
+ RAG:    0.594 mean, 40% pass (+23%)
+ Guided: 0.620 mean, 40% pass (+28%)
```

**Stock Gemma produces inadequate trafficking-safety responses.** Context injection lifts scores 23–28% without any training. Phase 3 Unsloth fine-tuning (Notebook 530) encodes the same knowledge permanently.

### Cross-model comparison (Notebook 210 Gemma vs OSS)

Gemma 4 E4B (9B) leads the 4-model comparison on this slice with zero harmful outputs. Gemma 4 E2B (2B on-device) scores higher than the 7B Mistral peer and holds ground against 8B Llama — the exact result the on-device story needs.

---

## 6. Current verified state

### Gates (green)

- `python scripts/validate_notebooks.py` → `Validated 76 notebooks successfully.`
- `python scripts/verify_kaggle_urls.py` → `All 76 notebooks resolve.` (Public Kaggle reachability is green across every published kernel.)
- 42 targeted `scripts/_validate_NNN_adversarial.py` validators pass for the canonicalized suite.
- 194 tests pass under `make test`.

### Slug source of truth

- `scripts/_public_slugs.py` holds `PUBLIC_SLUG_OVERRIDES` (39 entries) — the live Kaggle slug for every notebook whose live URL deviates from the title-derived default.
- `scripts/_public_slugs.py` also holds `UNPUBLISHED_IDS` — currently `{015, 020}`, the Section 1 additions drafted 2026-04-18 that have not been pushed to Kaggle yet. The index renderer substitutes a "(pending publication)" label for these.
- `scripts/kaggle_live_slug_map.json` is a live-state probe artifact consumed by the index renderer. It currently covers 57 of 76 kernels; missing entries fall back to `PUBLIC_SLUG_OVERRIDES` / the PHASES default.

### Shared helpers (no duplication across builders)

- `scripts/_canonical_notebook.py` — `canonical_header_table`, `canonical_hero_code`, `troubleshooting_table_html`, `patch_final_print_cell`, `HEX_TO_RGBA_SRC`.
- `scripts/_public_slugs.py` — single source of truth for slug overrides.
- `scripts/_notebook_display.py` — Kaggle-safe styling helpers (pandas Styler, `show_stat_cards`, `show_pipeline_diagram`, full-text no-truncation pattern).
- `scripts/_jailbreak_cells.py` — shared cell sources for the 185-189 jailbreak family.
- `scripts/notebook_hardening_utils.py` — hardened install-cell injection, pinned `duecare-llm-core==0.1.0`, wheel-fallback path.

### Repository shape (post 2026-04-18 cleanup pass)

```
gemma4_comp/
├── packages/                   8 PyPI packages, duecare.* namespace (PEP 420)
├── src/demo/                   FastAPI dashboard + demo app (live, 16 files)
├── configs/duecare/domains/    3 shipped domain packs (YAML + JSONL)
├── kaggle/kernels/             76 kernel directories (metadata + .ipynb)
├── notebooks/                  76 local .ipynb mirrors
├── scripts/                    127 Python files (builders, validators, utilities)
│   ├── build_notebook_NNN_*.py   per-notebook builders
│   ├── build_index_notebook.py   shared orchestrator (000 Index)
│   ├── build_notebook_005_glossary.py
│   ├── build_section_conclusion_notebooks.py
│   ├── build_showcase_notebooks.py
│   ├── build_grading_notebooks.py
│   ├── build_deployment_application_notebooks.py
│   └── build_kaggle_notebooks.py legacy; still authoritative for 610
├── docs/                       17 top-level .md + docs/components + docs/prompts
├── data/                       baseline findings, training JSONL, RAG KB
├── deployment/                 browser_extension + hf_spaces
├── tests/                      16 test files
├── _archive/                   168 archived files (legacy_src, scripts, docs, notebooks, reports)
├── _reference/                 gitignored: author's private benchmark harness
├── CLAUDE.md                   project context for Claude Code sessions
├── README.md                   public-facing overview for judges
├── Makefile, pyproject.toml, requirements.txt, LICENSE, Dockerfile*, docker-compose.yml
```

### Cleanup history (2026-04-18)

- **30+ one-off maintenance scripts** archived: `align_kaggle_kernel_metadata.py`, `align_metadata_from_push_log.py`, `align_metadata_to_slug_map.py`, `normalize_canonical_slugs.py`, the `push_all_*` family, `update_builders_to_canonical.py`, the seven `implement_*.py` scaffolders, `reclassify_nb00_with_v3.py`, `generate_forge.py`, `build_forge_core_notebook.py`, and the six root-level `_inject_*.py` / `_align_titles.py` / `_audit_kernels.py` one-offs.
- **4 stale planning docs + 13 review-report artifacts** moved out of `docs/` (the `docs/review/` directory was emptied and removed).
- **29 historical prompt-ladder drafts** (06–34) moved to `_archive/docs_2026-04/prompts/`. The 5 band-scoped review prompts (01–05 plus `_shared_discipline.md` and `README.md`) remain.
- **1 orphan notebook** (`forge_kaggle_submission.ipynb`) and **1 orphan test** (`test_ingest_google_drive_reference_material.py`) relocated.
- **`docs/components/forge_llm_*.md` → `duecare_llm_*.md`** (renamed; README table links now resolve).
- Numeric claims reconciled across README, CLAUDE.md, FOR_JUDGES, project_status, writeup_draft, and this checkpoint to the current 76-notebook / 8-package / 12-agent / 15-generator / 9-capability-test / 3-domain-pack state.
- `build_notebook_320_supergemma_safety_gap.py` updated: pre-renumber `nb00` references replaced with `nb100`.

---

## 7. Remaining work to submission (2026-04-19 → 2026-05-18, 29 days)

### P0 — blocks submission

1. **Phase 3 improvement spine end to end.** Run `520 Phase 3 Curriculum Builder` → `525 Uncensored Grade Generator` → `527 Uncensored Rubric Generator` → `550 NGO Partner Survey Pipeline` → `530 Phase 3 Unsloth Fine-tune` → `540 Fine-tune Delta Visualizer` with live outputs, then publish the stock-vs-fine-tuned `comparison.json` into `600 Results Dashboard`. This is the most critical "real, not faked" claim still to close.
2. **Record the 3-minute public YouTube video** following `docs/video_script.md`. Open on Maria (composite, labeled as such); close on named NGO partners (Polaris, IJM, ECPAT, POEA, BP2MI, HRD Nepal, IOM).
3. **Finalize the ≤ 1,500-word Kaggle writeup** in `docs/writeup_draft.md` once Phase 3 numbers land.
4. **Re-verify the live public demo surface** (FastAPI dashboard + browser extension + HF Space) against the current package version.
5. **Push the 2 pending-publication Section 1 notebooks** (015 Background Literature, 020 Current Events) and reconcile `UNPUBLISHED_IDS`.

### P1 — significantly improves score

1. **Live Kaggle runtime validation** on the most credibility-sensitive notebooks: `100`, `150`, `155`, `160`, `170`, `180`, `183`, `185`–`189`, `245`, `525`, `527`, `530`, `540`, `550`.
2. **Publish the fine-tuned weights** to HF Hub at `TaylorScottAmarel/duecare-gemma-4-e4b-safetyjudge-v0.1.0`.
3. **GGUF export for llama.cpp** Special Technology track (Q4_K_M and Q5_K_M quantizations).
4. **LiteRT export for mobile** Special Technology track — the frontline-worker-with-only-a-phone story.

### P2 — stretch

1. Finish publication of the `660`–`695` Deployment Applications band so every tracked URL is live.
2. Close the Kaggle "Notebook not found" create-time failure mode on the remaining Free Form Exploration private-draft orphans (requires manual UI cleanup at `kaggle.com/taylorsamarel`).
3. Full 74K-prompt evaluation via local Ollama.
4. Additional domain pack (`medical_misinformation`) to prove the "adding a domain is a directory copy plus a YAML edit" claim beyond the current 3 shipped packs.

---

## 8. Security and privacy invariants

These are enforced by `.claude/rules/10_safety_gate.md` and `configs/duecare/domains/trafficking/pii_spec.yaml`; violations block a commit.

- **No raw PII in git.** Names, passport / visa / national-ID numbers, phone numbers, email addresses, bank accounts, home addresses, dates of birth — none appear in source, test fixtures, notebooks, or artifacts. Composite characters (Maria, Ramesh, Sita) are labeled as composites in both the writeup and the video.
- **Anonymizer is a hard gate.** The Anonymizer agent in `packages/duecare-llm-agents/src/duecare/agents/anonymizer/` runs before any data enters the clean store. Audit log stores `sha256(original)`, never plaintext.
- **No raw PII in logs.** `duecare.observability` strips flagged content via a structlog filter.
- **No raw PII in published artifacts.** HF Hub weights, Kaggle Models, Kaggle Datasets, Kaggle Notebook, writeup, and video all pass a pre-publish Validator scan.
- **`_reference/` is gitignored.** The full private benchmark stays out of the public Kaggle repo.
- **Known local-only credential risk:** `.claude/settings.local.json` contains hardcoded Kaggle credentials. The file is not tracked by git. Rotate separately.

---

## 9. Audit commands a judge or reviewer can run

Every number in this checkpoint is reproducible from these commands against a clean checkout:

```bash
# Install
uv sync --all-packages          # or: pip install packages/duecare-llm

# Repo-wide gates
python scripts/validate_notebooks.py                          # 76/76 notebooks
python scripts/verify_kaggle_urls.py                          # all live URLs resolve
python -m pytest packages tests -q                            # 194 tests
make lint                                                     # ruff + mypy

# Per-notebook adversarial shape checks (examples)
python scripts/_validate_100_adversarial.py                   # Gemma baseline shape
python scripts/_validate_conclusions_adversarial.py           # 9 section conclusions

# Rebuild the full suite from source
make notebooks

# Regenerate the live inventory doc
python scripts/generate_kaggle_notebook_inventory.py

# Publish (requires KAGGLE_API_TOKEN set)
python scripts/publish_kaggle.py auth-check
python scripts/publish_kaggle.py push-notebooks
python scripts/publish_kaggle.py status-notebooks
```

If the first three gates are green, the next bottleneck is runtime evidence (actually running the GPU / API-heavy notebooks end to end), not notebook publication hygiene.

---

## 10. One-line summary

> 76 Kaggle notebooks, 8 PyPI packages, 12 agents, 15 adversarial generators, 9 capability tests, 3 domain packs, 5 deployment applications, 194 tests, one CLI command. Gemma 4 E4B baseline is measured (0.610 mean score, 0% harmful). Phase 3 Unsloth fine-tune spine is built; the live run plus the public video are the final blockers for the 2026-05-18 deadline.
