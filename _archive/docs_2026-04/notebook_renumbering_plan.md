# Notebook renumbering plan — align IDs with the 12-section scheme

The user's 2026-04-17 direction: each section is labeled with a
hundreds-prefix (`000 Background and Package Setup`, `100 Free Form
Exploration`, …) and every notebook inside the section lives in the
matching hundreds band. The section labels are already updated in
`scripts/build_index_notebook.py`. This document is the physical
renumbering plan — what IDs move where, what cross-references break,
and the safe execution sequence.

## Target sections

| Band | Label | Current-state notes |
|---|---|---|
| 000 | Background and Package Setup | already aligned (000, 005, 010, 099) |
| 100 | Free Form Exploration | already aligned (100, 150-190, 199) |
| 200 | Baseline Text Evaluation Framework | **misaligned** — current 200s are Text Comparisons; 105/110/120/130/140/190 live here logically |
| 300 | Baseline Text Comparisons | **misaligned** — current 300s are adversarial (→900) |
| 400 | Baseline Image Evaluation Framework | **empty** — to be authored |
| 500 | Baseline Image Comparisons | **empty** — to be authored |
| 600 | Advanced Evaluation | **misaligned** — currently 400-499 (400/410/420/460/499) |
| 700 | Advanced Text Prompt-Test Generation | **misaligned** — scattered (310/430/440/699) |
| 800 | Advanced Image Prompt-Test Generation | **empty** |
| 900 | Advanced Adversarial Prompt-Test Evaluation | **misaligned** — scattered (300/320/335/450/799) |
| 1000 | Model Improvement Opportunities | **misaligned** — currently 500-599 (500/510/520/530/540/599) |
| 1100 | Results Dashboards | **misaligned** — currently 600 |
| 1200 | Solution Surfaces | **misaligned** — currently 610/620/650 and 899 |

## Proposed ID mapping

Work inside each new band alphabetically / by logical order:

### Moves into 200 Baseline Text Evaluation Framework

| Current | New | Title |
|---|---|---|
| 105 | 200 | Prompt Corpus Introduction |
| 110 | 210 | Prompt Prioritizer |
| 120 | 220 | Prompt Remixer |
| 130 | 230 | Prompt Corpus Exploration |
| 140 | 240 | Evaluation Mechanics |
| 190 | 250 | RAG Retrieval Inspector |
| 299 | 299 | conclusion (keep) |

### Moves into 300 Baseline Text Comparisons

| Current | New | Title |
|---|---|---|
| 200 | 300 | Cross-Domain Proof |
| 210 | 310 | Gemma vs OSS Comparison |
| 220 | 320 | Ollama Cloud OSS Comparison |
| 230 | 330 | Mistral Family Comparison |
| 240 | 340 | OpenRouter Frontier Comparison |
| 250 | 350 | Comparative Grading |
| 260 | 360 | RAG Comparison |
| 270 | 370 | Gemma Generations |
| 399 | 399 | conclusion (keep) |

### Moves into 600 Advanced Evaluation

| Current | New | Title |
|---|---|---|
| 400 | 600 | Function Calling and Multimodal |
| 410 | 610 | LLM Judge Grading |
| 420 | 620 | Conversation Testing |
| 460 | 640 | Citation Verifier |
| 499 | 699 | conclusion (keep band-end, new id) |

### Moves into 700 Advanced Text Prompt-Test Generation

| Current | New | Title |
|---|---|---|
| 310 | 700 | Prompt Factory |
| 430 | 710 | Rubric Evaluation |
| 440 | 720 | Per-Prompt Rubric Generator |
| 699 | 799 | conclusion (rename) |

### Moves into 900 Advanced Adversarial Prompt-Test Evaluation

| Current | New | Title |
|---|---|---|
| 300 | 900 | Adversarial Resistance |
| 320 | 910 | SuperGemma Safety Gap |
| 335 | 920 | Attack Vector Inspector |
| 450 | 930 | Contextual Worst-Response Judge |
| 799 | 999 | conclusion (keep) |

### Moves into 1000 Model Improvement Opportunities

| Current | New | Title |
|---|---|---|
| 500 | 1000 | Agent Swarm Deep Dive |
| 510 | 1010 | Phase 2 Model Comparison |
| 520 | 1020 | Phase 3 Curriculum Builder |
| 530 | 1030 | Phase 3 Unsloth Fine-tune |
| 540 | 1040 | Fine-tune Delta Visualizer |
| 599 | 1099 | conclusion |

### Moves into 1100 Results Dashboards

| Current | New | Title |
|---|---|---|
| 600 | 1100 | Results Dashboard |

### Moves into 1200 Solution Surfaces

| Current | New | Title |
|---|---|---|
| 610 | 1200 | Submission Walkthrough |
| 620 | 1210 | Demo API Endpoint Tour |
| 650 | 1250 | Custom Domain Walkthrough |
| 899 | 1299 | Solution Surfaces Conclusion |

## Execution sequence (safe order)

Renames must happen in a specific order because some new IDs collide
with old IDs in the same namespace (e.g. old 300 → new 900, but old
600 → new 1100 and new 600 is taken by ex-400). Work in two phases:

1. **Phase A — evacuate every renamed notebook to a temporary `_wip_`
   prefix.** For each renamed notebook, move its build script to
   `build_notebook_wip_<new_id>_<slug>.py`, its kernel dir to
   `kaggle/kernels/_wip_<new_id>_<slug>/`, its notebook file to
   `notebooks/_wip_<new_id>_<slug>.ipynb`. At the end of Phase A all
   old slots are free and no new slots collide.
2. **Phase B — rename `_wip_` → final `<new_id>`.** For each notebook,
   flip the directory and filename, regenerate `kernel-metadata.json`
   with the new `id` and title, and update every URL reference in
   every other build script.

The Phase B URL update is the long pole. Every `URL_XXX` constant
across ~50 build scripts has to be rewritten. A small helper script
`scripts/_renumber_urls.py` that sed-replaces the table above across
`scripts/build_notebook_*.py` and `docs/` is recommended so the
rewrite is auditable.

## What stays

- 000/005/010/099 — already aligned to 000 band.
- 100/150/155/160/170/180/181-189/199 — already aligned to 100 band.

## Risk register

- **Kaggle kernels already published.** `kaggle kernels list` shows
  which kernels are live under the old slugs. Those old slugs must
  redirect (or be manually re-pointed) since external links to
  `taylorsamarel/duecare-200-cross-domain-proof` etc. cannot be
  migrated. Strategy: leave old kernels live but mark deprecated in
  the title; new ID gets a fresh slug `duecare-<new_id>-...`.
- **URL constants across build scripts.** Every `URL_200 =` reference
  in every build script must flip. High error surface; rely on the
  helper script + a grep test that no build script still references
  an old URL after the rename.
- **The index notebook's PHASES list.** Already relabeled; the `id`
  values inside each phase must move when notebooks move. Regenerate
  the index last.
- **Daily Kaggle push rate limit.** Expect the full re-push to take
  multiple days at ~5-10 kernels per day.

## What we did in the current session

- Relabeled every `PHASES` entry in
  `scripts/build_index_notebook.py` with the new prefix.
- Added placeholder entries for 400 / 500 / 800 (Baseline Image,
  Baseline Image Comparisons, Advanced Image Prompt-Test Generation).
- Added 181-189 to the Free Form Exploration section.
- Rebuilt `notebooks/000_index.ipynb` and the matching kernel dir.

The physical renumber is left for a dedicated next session, to be
executed under the Phase A / Phase B plan above.
