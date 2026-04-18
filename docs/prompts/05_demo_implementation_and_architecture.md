# Prompt 05. Demo implementation and architecture (bands 800 to 990)

> Paste everything below the horizontal rule into Copilot. Copilot has
> filesystem access to `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.
> This prompt covers the final application tracks (enterprise
> server-side, client-side on-device, NGO public API), the suitability
> scorecard, the results dashboard, writeup companion, video
> companion, and the business model. Read
> `docs/prompts/_shared_discipline.md` first.

---

## Scope

Cover bands 800 through 990 only.

| Band | Section | What this prompt owns |
|---|---|---|
| 800 to 890 | Implementation | Enterprise server-side demo, client-side on-device demo, NGO public API demo, plus architecture rationale for each. |
| 900 to 990 | Meta and rollup | Suitability scorecard, final results dashboard, writeup companion, video companion, business model, infrastructure plan. |

Fine-tuning notebooks (band 700) must already have produced a
SuperGemma artifact that these demos can load; otherwise every demo
falls back to stock Gemma 4 E4B and says so in its header. Stock
fallback is acceptable for the hackathon submission, as long as each
demo labels its model version.

## Coverage targets (must each be satisfied across bands 800 to 990)

Band 800 to 890:

1. **Enterprise server-side demo.** Social-media platform waterfall
   detection. API ingress, queue, rubric-based quick filter, Gemma
   4 enhanced scorer, moderation-queue output, audit log. Cite
   `src/demo/app.py`, `src/demo/social_media_scorer.py`,
   `src/demo/quick_filter.py`. Container target: root
   `Dockerfile` and `docker-compose.yml`. Deployment target: HF
   Spaces for the judge-facing instance.
2. **Client-side on-device demo.** Browser extension MV3 plus
   on-device runtime (llama.cpp for desktop, LiteRT for Android).
   Cite `deployment/browser_extension/` and
   `packages/duecare-llm-models/src/duecare/models/llama_cpp_adapter/`.
   State what is shipped, what is stubbed, and what ships before
   the video.
3. **NGO public API demo.** Public FastAPI endpoint for complaint
   intake, complaint document assistance, per-corridor legal
   provision lookup, hotline routing. Cite
   `src/demo/report_generator.py`, `src/demo/rag.py`,
   `configs/duecare/legal_provisions.yaml`,
   `configs/duecare/corridors.yaml`.
4. **Architecture rationale per track.** One notebook per track
   walks the architecture decisions with code paths and
   deployment targets. Text is sparse; diagrams are plain-text
   ASCII, no decorative art.
5. **Integration regression checks.** Every demo has at least one
   end-to-end smoke test notebook that exercises it against a
   small fixture corpus. Judges reading the notebook should see a
   real response returned from a real endpoint.

Band 900 to 990:

6. **Suitability scorecard.** One notebook scoring Gemma 4 on each
   application track, with recommended architecture and honest
   gaps. Cite the evaluation headline numbers from band 490 and
   band 590.
7. **Final results dashboard.** Reads cached outputs from all
   section summary notebooks (190, 290, 390, 490, 590, 690, 790,
   890) and produces the writeup's headline chart collection.
8. **Writeup companion notebook.** Every headline number and every
   chart in `docs/writeup_draft.md` is reproduced here by a single
   cell. Judge clicks Run All and sees the writeup's numbers
   regenerate.
9. **Video companion notebook.** Every screen-capture-worthy cell
   in the video script is present here in the order the video
   shows it. Each cell has a two-line caption mirroring the
   voiceover beat.
10. **Business model notebook.** A narrative notebook stating
    payer, pricing, open-vs-closed surface, grant pathway,
    compliance posture, and defensibility. See the deliverable
    section 2 below for the full list of elements this notebook
    must contain.

## Source of truth for kernel state

`docs/current_kaggle_notebook_state.md` is authoritative. Use the
Kaggle id from that file when referring to a kernel. Legacy
directory-to-code-file aliases for kernels placed in bands 800 to
990 must be resolved by the renumber pass (for example,
`duecare_14_dashboard` contains `14_results_dashboard.ipynb`,
`duecare_21_phase3_curriculum` contains
`21_phase3_curriculum_builder.ipynb`,
`duecare_phase3_finetune` contains
`phase3_unsloth_finetune.ipynb`). Do not touch
`forge_llm_core_demo.ipynb`; that orphan is owned by prompt 01.

## Current kernels relevant to these bands

- `duecare_14_dashboard` partially maps to 910 dashboard; the
  evaluation portion (if present) belongs to the 490 summary.
  Split.
- `duecare_04_submission_walkthrough` is a judge-facing walkthrough
  and belongs in band 000 to 090 orientation, not here. Route out.
- `duecare_index` becomes `duecare_000_index` and is out of this
  band; do not respec.
- `docs/deployment_modes.md` already covers the three application
  tracks; the notebooks in band 800 import the architecture
  decisions from that doc rather than restating them.

## Deliverable, produce `docs/review/800-990_demo_and_architecture.md`

Sections 0 through 6 in order. Cite `path:line` for every factual
claim. Maximum 2,500 words.

### Section 0. Band scope and grounding (at most 200 words)

State the band's purpose in plain English. Confirm the packages vs
notebooks boundary: demo logic lives in `src/demo/`, adapters in
`packages/duecare-llm-models/`, deployment artifacts in
`deployment/`, infrastructure in `Dockerfile`, `docker-compose.yml`,
and `deployment/hf_spaces/`. Notebooks in band 800 orchestrate and
visualize; they do not re-implement demo routes, adapters, or
deployment.

Cite at least three import lines from `src/demo/*` that existing
notebooks use.

### Section 1. Application tracks, full architecture

For each of the three tracks, produce:

a. Architecture sketch (plain-text ASCII or markdown list).
b. Named container or runtime target.
c. Named deployment surface (HF Space, Fly.io, self-hosted, Chrome
   Web Store, app store, on-device sideload).
d. Plausible real-world operator.
e. Validating notebook slug(s) in band 800.
f. Today's state, the 33-day goal, the post-hackathon roadmap.

Tracks:

- Enterprise server-side.
- Client-side on-device.
- NGO public API.

### Section 2. Business model notebook spec

Produce a cell-by-cell outline (at most 30 cells) for the business
model notebook. The notebook is narrative, not live-evaluation; its
outputs are tables and small charts, not model calls.

Required content:

- Who pays per track. Enterprise may pay per API call or per seat;
  NGO track may be free and grant-funded; client-side may be free
  to the worker and bundled with enterprise.
- What is free, what is paid, what is source-available. Tie to
  the `duecare-llm-*` PyPI split and the MIT license.
- Cost drivers and gross-margin assumptions at one-number
  granularity. For example, per-1k-token cost at Gemma 4 E4B on
  llama.cpp based on the Kaggle T4 baseline in band 110. Unverified
  numbers labeled unverified.
- Grant and partnership pathway. Named NGOs (Polaris Project, IJM,
  ECPAT, POEA, BP2MI, HRD Nepal). Cite `docs/deployment_modes.md`
  and `README.md`.
- Compliance posture. Cal. Civ. Code section 1714(a) framing. GDPR
  and CCPA for the NGO API. Data-residency note.
- One-paragraph defensibility statement. Reference the 21K
  benchmark, provenance chain, fine-tuned weights on HF Hub, NGO
  relationships.

### Section 3. Infrastructure plan

- Deployment matrix: today, 33-day goal, post-hackathon.
- Observability per track: cite `duecare.observability` and name
  the metrics, logs, audit events emitted.
- CI and release per track: cite `.github/workflows/ci.yml` and
  `claude.yml`. State whether each track is in CI today and what
  must be added.
- Cost ceiling per track through submission.
- Fallback plan per track. For example, if Phase 3 does not
  converge, what ships. If HF Spaces goes down, what is the static
  fallback for judges. If the video recorder is unavailable, who
  records.

### Section 4. Writeup and video companion mapping

A two-column table.

- Left column: every number, chart, and quoted claim in
  `docs/writeup_draft.md` and `docs/video_script.md`.
- Right column: the notebook cell that reproduces it (slug plus
  cell number).

Flag any writeup or script claim that has no companion cell.

### Section 5. Full notebook table for bands 800 to 990

Columns as in shared discipline. Every coverage target 1 through
10 must appear as a row. Every current kernel placed in these
bands must be mapped, moved, or marked delete with reason.

Append:

- `git mv` block.
- `kernel-metadata.json` id edits.
- Build-script names for every gap row.

### Section 6. Ticket list for these bands

Flat, one per line, at most 120 characters, ordered P0 to P2.

```
[P0][M][Impact][Container] Build duecare_810_enterprise_demo, HF Space deployment, cite src/demo/app.py
[P0][M][Impact][Container] Build duecare_820_client_on_device, browser extension plus llama.cpp
[P0][M][Impact][Container] Build duecare_830_ngo_public_api, cite legal_provisions and corridors
[P0][S][Tech][Sep-of-Concerns] Split duecare_14_dashboard into 490 summary and 910 dashboard
[P0][L][Video][Story] Build duecare_930_video_companion mirroring docs/video_script.md beats
[P0][M][Video][Repro] Build duecare_920_writeup_companion reproducing every writeup number
[P0][M][Impact][Business] Build duecare_950_business_model narrative notebook
[P0][S][Tech][Repro] Label model version in every demo notebook header (stock or fine-tuned)
...
```

Include tickets for:

- Every demo track's container path, deployment target, and smoke
  test notebook.
- Every writeup or video claim without a companion cell.
- The 490, 590, 690, 790, 890 summary notebooks if any still need
  rollup into 910.
- The three-application architecture rationale notebooks.
- The business model notebook.
- The suitability scorecard notebook.

## Constraints specific to this prompt

- Do not re-run evaluations in these bands. Read cached outputs
  from section summaries (490, 590, 690, 790, 890).
- Every demo notebook has a container path, or states "not
  containerized" with a one-sentence reason.
- Every demo notebook labels its model version clearly (stock
  Gemma 4 E4B vs fine-tuned SuperGemma vs on-device llama.cpp vs
  LiteRT).
- Every demo notebook has a smoke-test cell that hits a real
  endpoint (local or HF Space). Judges read this first.
- Every endpoint mentioned has a rate-limit or auth posture stated.
- No notebook in this band re-implements demo routes, adapters, or
  deployment tooling.

## Read before writing, in order, stop when grounded

1. `docs/current_kaggle_notebook_state.md`.
2. `docs/prompts/_shared_discipline.md`.
3. `docs/deployment_modes.md`.
3. `docs/FOR_JUDGES.md` for the honesty bar.
4. `src/demo/app.py`, `src/demo/social_media_scorer.py`,
   `src/demo/quick_filter.py`, `src/demo/report_generator.py`,
   `src/demo/rag.py`, `src/demo/function_calling.py`,
   `src/demo/multimodal.py`.
5. `deployment/browser_extension/`,
   `deployment/telegram_bot/`,
   `deployment/discord_bot/`,
   `deployment/hf_spaces/`.
6. `Dockerfile`, `docker-compose.yml`.
7. `configs/duecare/corridors.yaml`,
   `configs/duecare/legal_provisions.yaml`,
   `configs/duecare/models.yaml`.
8. `packages/duecare-llm-models/src/duecare/models/llama_cpp_adapter/`,
   plus any LiteRT adapter if present.
9. `docs/writeup_draft.md` and `docs/video_script.md`.
10. `.github/workflows/ci.yml` and `claude.yml`.
11. `packages/duecare-llm-core/src/duecare/observability/`.

## Output

Single file at
`docs/review/800-990_demo_and_architecture.md`. Sections 0 through
6 in order. Taylor is the only reader.
