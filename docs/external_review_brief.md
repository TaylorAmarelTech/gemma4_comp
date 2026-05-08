# External Review Brief — Duecare chat-package & Kaggle harness

> Paste this whole document to GPT-5.5 (or any frontier model) and ask:
>
> *"Review the Duecare chat-package's current architecture against the
> trouble areas, quality-of-life issues, and update-cost problems
> documented below. Produce a prioritized gameplan: what to refactor
> before the 2026-05-18 hackathon submission deadline, what to defer.
> Be specific with file paths and concrete code patterns. Think
> carefully about flexibility (adding a new dim / new layer / new RAG
> doc) — the goal is to make extension a one-file edit wherever
> possible. Identify any architectural smells we missed."*

---

## 1. Submission context (the deadline that shapes priorities)

- **Gemma 4 Good Hackathon** on Kaggle. **Submit by 2026-05-18 23:59 UTC**. As of writing it is **2026-05-08** — T-10 days.
- Tracks targeted: Impact → Safety & Trust ($10K), Special Tech → Unsloth ($10K), Special Tech → llama.cpp / LiteRT ($10K), Main ($10K-$50K).
- Scoring: **Impact & Vision 40 / Video Pitch 30 / Tech Depth 30**. **70 of 100 points are scored from the video.** The chat package is what judges see when they click the live demo.
- Submission deliverables: 2 core + 11 appendix Kaggle notebooks, ≤1,500-word writeup, ≤3-min video, public GitHub repo, live public demo.

This means: **shippable beats elegant.** A refactor that takes 2 days but doesn't move the visible demo is lower priority than a 2-hour viz polish that does.

## 2. Codebase shape

```
gemma4_comp/                                 -- monorepo, uv workspace
├── packages/                                -- 8 PyPI packages (PEP 420 namespace under duecare.*)
│   ├── duecare-llm-core/
│   ├── duecare-llm-models/
│   ├── duecare-llm-chat/   ★ THE PACKAGE THIS REVIEW IS ABOUT
│   │   ├── pyproject.toml                   -- version = "0.14.3"
│   │   ├── src/duecare/chat/
│   │   │   ├── __init__.py
│   │   │   ├── _brand.py            ★ NEW (v0.14.2) single source of truth
│   │   │   ├── app.py               (~3,800 lines — FastAPI app)
│   │   │   ├── harness/
│   │   │   │   ├── __init__.py      (~9,400 lines — GREP_RULES, RAG_CORPUS, graders, tools)
│   │   │   │   ├── _rubric_universal.json   (46 dims, version "v3.10-evaluator-quality")
│   │   │   │   ├── _evaluation_questions.json  (21 LLM-judge templates)
│   │   │   │   ├── _citations.json  (46 edges)
│   │   │   │   ├── _examples.json   (587 prompts across 8 audience buckets)
│   │   │   │   ├── _personas.json   (7 curated personas)
│   │   │   │   ├── _baseline_gauge.json
│   │   │   │   ├── _classifier_examples.json
│   │   │   │   └── _governance.py   (curator-block loader)
│   │   │   └── static/              ★ 10 HTML viewer pages
│   │   │       ├── index.html       (~6,100 lines — main chat UI)
│   │   │       ├── harness.html     (landing page with 6+ layer cards)
│   │   │       ├── persona.html
│   │   │       ├── grep-rules.html
│   │   │       ├── grep-tester.html ★ NEW (v0.14.3)
│   │   │       ├── rag-corpus.html
│   │   │       ├── rag-graph.html   (force-directed SVG)
│   │   │       ├── tools.html
│   │   │       ├── online.html
│   │   │       └── search.html      ★ NEW (v0.14.3)
│   ├── duecare-llm-domains/, -tasks/, -agents/, -workflows/, -publishing/, -llm/ (meta)
├── kaggle/
│   ├── 01-duecare-harness-chat/             -- THE submission core notebook
│   │   ├── kernel.py                        (~1,700 lines — orchestrator: install wheels → load model → wire harness → start FastAPI + cloudflared)
│   │   ├── notebook.ipynb                   -- single-cell wrapper
│   │   ├── README.md
│   │   └── wheels/                          -- bundled wheels + dataset-metadata.json
│   ├── 02-live-demo/, A-01..A-11/           (12 appendix kernels)
├── docs/                                    -- writeup_draft.md, FOR_KAGGLE_JUDGES.md, video_script.md, etc.
└── scripts/                                 -- v141_*.py verification + reconciliation helpers
```

## 3. The user-facing API surface (what the frontend / kernel speaks to)

```
GET  /                                  -- static index.html
GET  /static/<page>.html                -- 10 viewer pages
GET  /api/brand                ★ NEW    -- single source for product/layer/version/counts
GET  /api/version                       -- chat_package version + harness counts + curator-block index
GET  /api/health-check                  -- wired-layer status for cold-boot smoke
GET  /api/rag/graph                     -- 46 nodes / 46 edges / jurisdiction groups
GET  /api/harness-catalog/{layer}       -- catalog data for persona|grep|rag|tools|online
POST /api/grep/test            ★ NEW    -- live regex tester payload
GET  /api/search-all?q=        ★ NEW    -- federated search across 4 layers
POST /api/chat                          -- the actual chat endpoint with SSE streaming
POST /api/grade  /api/grade-deep  /api/grade-combined  -- 4 grade modes
GET/POST /api/load-model{,/status,/logs}-- model picker
GET  /api/governance{,/<name>}          -- curator-block JSONs
GET  /api/retrieval/config + POST       -- BM25/dense/RRF tuning
```

## 4. What v0.14.0 → v0.14.3 just landed (last 8 hours of work)

**v0.14.0:** First-pass interactive RAG corpus graph viewer (force-directed SVG, ~150 lines, no D3/Cytoscape dep). New /api/rag/graph endpoint. evaluator_call hook documentation framing the Kaggle T4 VRAM constraint.

**v0.14.1:** RAG graph viewer matures — arrowheads, search, jurisdiction filter, zoom/pan, SVG export, standalone full-screen page at /static/rag-graph.html. Fixed hardcoded `"v3.10-data-evaluator"` literal in universal grader (was returning stale version even when JSON file said v3.10). Reconciled 12 appendix dataset-metadata.json files. 27 jurisdiction groups, 0 docs in "Other".

**v0.14.2:** **Single source of truth refactor** — created `_brand.py` with `LAYERS` dict, `WIRE_FORMAT_VERSION`, `chat_package_version()` function, `to_dict()` serializer. New `/api/brand` endpoint exposes everything. Frontend uses `[data-brand-count="..."]` and `[data-brand-text="..."]` attributes to fetch values dynamically — no more hardcoded "161 GREP rules" / "35-doc corpus" drift. Refactored hardcoded `"v2.0"` strings in evaluator + combined graders to read from `_brand.WIRE_FORMAT_VERSION`. **Plus** dedicated viewer pages for every harness layer + RAG retrieval overlay (rag-corpus.html shows yellow `● recent` badge on docs pulled by most-recent chat turn) + GREP fire-count leaderboard with click-to-expand regex patterns + auto-refresh every 8s. **Plus** comments/docstrings sweep — 29 stale references fixed across 14 kaggle/A-XX kernel.py + notebook.ipynb + README.md files.

**v0.14.3 (just shipped):**
- Centralized 28-entry jurisdiction prefix→(group,label,color) rules into `_brand.JURISDICTIONS` + `_brand.classify_doc()` + `_brand.jurisdiction_groups()`. Eliminated duplication between `/api/rag/graph` and `/api/harness-catalog/rag`.
- New `POST /api/grep/test` + `/static/grep-tester.html` — paste any text, see which of 161 rules fire (no LLM call). 4 quick presets including jailbreak.
- New `GET /api/search-all?q=` + `/static/search.html` — federated search across persona / GREP / RAG / tools.
- Category histogram on grep-rules.html (31 categories, click bar to filter).

## 5. Trouble areas we've witnessed (these are real, not hypothetical)

### 5a. Stale-number drift — chronic, repeatedly bites us

Every time numbers change (21→34→46 dims, 33→35→46 RAG docs, 108→111→161 GREP rules, 5→6 layers, 204→407→545→575→587 prompts), they were embedded in **dozens** of places: docstrings, comments, README sections, About-modal copy, dataset-metadata.json subtitles, chat-UI tile labels, kernel.py print() banners, notebook.ipynb cells, hardcoded literal strings in Python returns. We have written **two bulk-replacement scripts** (`scripts/v141_doc_reconciliation.py` with 80+ patterns, `scripts/v141_regenerate_appendix_metadata.py`) and still keep finding more.

Fixed (centralized): layer keys/labels/colors/descriptions, version stamps, all 6 live counts via `/api/brand`, jurisdiction prefix rules.

**Still a smell:** Severity colors (`critical/high/medium/low` hex codes) inlined in 3+ HTML files. Demo category labels (Headline lift / Jailbreak / Online / Compare / Social-eng) hardcoded. `_baseline_gauge.json` mentions "stock 6%, harnessed 88%" — these were measured against v3.5 (19 dims, historical) and never re-measured against v3.10 (46 dims).

### 5b. The wheel-vs-deployed-kernel drift

The Kaggle kernel runs whatever wheel was last pushed via `kaggle datasets version`. The user's most recent live test showed `version: "v3.10-data-evaluator"` and only 46 dimensions — which is what the OLD wheel returns. After we ship the new wheel, the version label and dim count update. **No build-time guarantee that the running deployment matches the source.** Smoke test scripts work locally but the user has to manually push + restart the kernel.

### 5c. The `<channel|>` reasoning leak in Gemma 4 thinking-mode

Gemma 4 with `chat_template="gemma-4-thinking"` emits `<thinking>...</thinking><channel|><actual answer>` — the user's first live test showed the entire scratchpad leaking into the visible response. The kernel.py decoder now does `text.rsplit("<channel|>", 1)[1]` plus `<thinking>...</thinking>` regex strip plus `<end_of_turn>` cleanup, but this is a brittle string-level patch on a model-template behavior that could change. **Suggested deeper fix:** investigate whether the tokenizer can be told to stop at the channel-end token, or whether streaming should tee the thinking-channel into a debug log and only stream-out the answer-channel.

### 5d. The "21-dim" mystery

User saw `"version": "v3.10-data-evaluator"` and 21 dims in one test, 46 dims in another. Root cause was the OLD wheel running on a deployed kernel — once the new wheel ships, all 46 dims appear. But a parallel agent initially miss-attributed this to "dimensions 22-45 have empty applicability rules" — they don't, all 46 have valid applicability. Spent ~30 minutes chasing a phantom bug. **Lesson:** the deployment-version mismatch is the more common cause of "old behavior" than a code bug.

### 5e. Performance on E2B / E4B (the model the Android LiteRT path uses)

User's "HELLO" test on E2B took **60 seconds** for a 181-char response. The complex 5-indicator harness-fired test took **152 seconds**. Quality was good (90.9% citation grounding, 100% section verification, multiple PASS dims) but latency on E2B is borderline-acceptable for desktop and likely worse on phone via LiteRT. Two open questions:
1. Is the chat template (`gemma-4-thinking`) producing too much "thinking" content the model has to generate before the answer? Could shave time by switching to a non-thinking template for E2B.
2. Should the harness pre-context (~13K chars when fully fired) be compressed for small models? A 2B-param model spending tokens parsing a 13K context block is nontrivial.

## 6. Quality-of-life / extensibility analysis

### Adding a new harness layer: ~7 file edits

Currently requires:
1. Add entry to `_brand.LAYERS` dict (1 file)
2. Add to `LAYER_ORDER` tuple (same file)
3. Wire the call in `app.state.<layer>_call` initialization in `create_app()` (`app.py`)
4. Add the layer's processing block in the chat endpoint loop in `app.py`
5. Add `/api/harness-catalog/{layer}` branch
6. Toggle tile in `index.html` empty-state + composer
7. Optional: dedicated `/static/<layer>.html` viewer

**Idea:** A `HarnessLayerSpec` dataclass that declares everything (key, color, call_signature, catalog_extractor, formatter) and a registry that the chat loop iterates. Adding a layer becomes one Python file.

### Adding a new rubric dimension: ~3 file edits (mostly clean)

1. Append to `_rubric_universal.json` (`{id, name, description, kind, weight, base_weight, intent_mult, usecase_mult, applicability, pass_indicators, fail_indicators}`)
2. Optional: add an entry to `_evaluation_questions.json` for the LLM-judge mode (falls back to a generic question template if missing — verified)
3. If `kind` is novel (not legal_citation/recognition/refusal/harm_check/etc.) you may need to update `_score_dimension_keywords` scoring logic

`/api/version` and `/api/brand` counts auto-update. Universal grader iterates rubric dims dynamically. **This is the cleanest extension path.**

### Adding a new RAG corpus document: 2 file edits

1. Append a tuple to `RAG_CORPUS` list in `harness/__init__.py` (Python literal, not JSON)
2. If the doc-id prefix doesn't match an existing jurisdiction in `_brand.JURISDICTIONS`, add a row there — otherwise it falls into Pattern Brief or Other
3. Optional: add citation edges to `_citations.json`

**Smell:** `RAG_CORPUS` and `GREP_RULES` are Python lists embedded in a 9,400-line module. Should be JSON files like `_examples.json` and `_personas.json` are. Currently a wheel rebuild is required to add a doc; a JSON file would let curator partners contribute via PR with a CI validator (we have `scripts/validate_curator_blocks.py` for the existing curator-block files — same pattern would work).

### Adding a new GREP rule: same as RAG — 1 Python list edit

Same smell as RAG. Would be much cleaner as JSON with a regex-validation step.

### Adding a new persona: 1 JSON file edit ✓

`_personas.json` is a curator-block — adding an entry, bumping `version` and `last_updated`, running `validate_curator_blocks.py`. Clean. **This is the pattern to copy for RAG and GREP.**

### Adding a new tool: ~3 file edits

1. Define the function in `harness/__init__.py`
2. Register in `_TOOL_DISPATCH` dict (same file)
3. The tool description docstring becomes the catalog entry — but the backing tables (CORRIDOR_FEE_CAPS, FEE_CAMOUFLAGE_DICT, etc.) are separate Python dicts that need their own edits

### Adding a new audience bucket: scattered

Bucket names live in `_examples.json` (per-prompt `audience_bucket` field), `_brand.COPY.audience_buckets` tuple, the chat UI's audience-filter chips (probably hardcoded in index.html), and the rubric's `usecase_mult` lookup (`_governance` curator-block). Need to verify all four agree.

## 7. Frontend specifics worth a careful look

### `index.html` is 6,100 lines

The main chat UI. Mostly well-organized but:
- Some functions are 200+ lines (e.g., `renderResponseCard`, `openPipelineModal`)
- The model picker, About modal, Grade modal, Compare modal, RAG view modal, retrieval-config modal, persona library modal, custom-rules modal, image-attachment modal, and Examples modal are all defined inline. Could split into per-modal files but the build step doesn't support that today (no bundler — single static file is intentional for cloudflared serve simplicity).
- A new `_BRAND_CACHE` and `data-brand-count`/`data-brand-text` attribute system was added in v0.14.2 — only `index.html` currently uses it. The 9 other static pages each have their own `fetch('/api/brand')` call — should they share a small `_brand_loader.js` file or stay self-contained?

### Severity color duplication

`critical: #ef4444 / high: #f59e0b / medium: #3b82f6 / low: #94a3b8` defined in CSS in `grep-rules.html`, `grep-tester.html`, `search.html`, plus inline styles in `index.html`. **Should be CSS variables exposed via `/api/brand` or just centralized in a `_brand.css` file served at `/static/_brand.css`.**

### Polling intervals

`rag-corpus.html` and `grep-rules.html` poll `/api/harness-catalog/<layer>` every 8 seconds to refresh retrieval overlays + fire-counts. This is per-tab — if a judge opens 3 tabs, that's 22.5 req/min on these endpoints. For a 1-judge demo it's fine; for a multi-user deployment we'd want server-sent events instead.

### State held in `app.state`

`app.state.grep_fire_counts: dict[rule, int]`, `app.state.rag_recent_hits: list`, `app.state.rag_recent_query: str` — all process-level. **Concurrent users would share these.** The "fire counts" leaderboard would aggregate across all users, "recent hits" would update from whoever spoke last. For the hackathon demo with one judge clicking through, fine. For production deployment, would need per-session state.

## 8. Build / deploy / test machinery

- `make test` runs `pytest packages/` — covers ~194 tests but coverage of the chat-package alone is partial
- `make adversarial` runs `scripts/adversarial_validate.py` against a live server — needs a Kaggle URL or localhost
- `scripts/v141_check_static_js.py` extracts `<script>` blocks and runs `node --check` on each — catches HTML JS syntax errors
- `scripts/v141_smoke_rag_graph_endpoint.py` uses `fastapi.TestClient` for the rag-graph endpoint
- `scripts/v141_smoke_catalog_endpoints.py` for the harness-catalog endpoints
- `scripts/v141_word_count.py` for the writeup
- **No** end-to-end Playwright test of the chat UI itself — would catch regressions like the `<channel|>` leak before they hit a judge

## 8a. NEW direction opened during the audit (review this)

The author asked: *"In the tools / RAG / context, should we have some way of maintaining contact information and complaint channels for people wanting to report bad activities, automatically send emails reporting inappropriate social media posts, and directly route OFWs / users to official sources?"*

**My initial design (partially implemented as v0.14.4):**

1. **`harness/_contacts.json` curator-block** — ~30 entries with `{id, name, category (regulator|ngo|embassy|hotline|ilo_office|intl_org), jurisdiction, country, corridors[], languages[], phone, phone_alt, sms, email, web_form_url, web_url, social, address, what_to_report[], response_time_hours, after_hours_alternative, verified, note}`. Already shipped — covers DMW (PH), OWWA, BP2MI Aduan (ID), Nepal DoFE, Bangladesh BMET, HK Labour Dept, SG MOM, Saudi Musaned 19911, UAE MoHRE 800-60, Kuwait PAM, Lebanon ISF, IJM, Polaris (US), MfMW HK, IMWU HK, ECPAT, PNCC Nepal, NAPTIP Nigeria, ILO Bangkok, IOM, PH consulates HK + Riyadh, ID consulate HK, US State TIP, ASEAN ACTIP, INTERPOL THB.

2. **New `GET /api/contacts` endpoint** — should support `?corridor=`, `?country=`, `?category=`, `?language=`, `?what_to_report=` filter params so the chat UI can surface contextually-relevant contacts.

3. **New `/static/hotlines.html`** — searchable / filterable directory page with a phone-icon, email-icon, web-form-icon row per entry. Click-to-call (`tel:`) + click-to-email (`mailto:`) + click-to-open-form. Same `Harness ↗` landing-page card pattern as the other viewers.

4. **In-chat "Report this scenario" CTA** — when the harness fires (GREP rules + RAG docs match a recognized scenario), surface a prominent button on the response card. Click → opens a modal with the contextually-relevant contacts + a pre-filled `mailto:` body summarizing the scenario / fired indicators / suspected violations. **The user clicks send** — we never auto-send.

**Critical safety boundary I want the reviewer to validate:**
- Auto-sending emails on a user's behalf is unacceptable (abuse vector — anyone visiting the demo could trigger spam against POEA, legal liability, removes worker agency, strips accountability for false reports).
- The right pattern is **draft, hand off, user reviews & sends.** A `mailto:` link prefilled with `?subject=...&body=...` is the cleanest: it opens the user's mail client with a complete draft they can edit and send themselves.
- For web forms (e.g., DMW's online complaint form), open the URL in a new tab with any URL-encodable context pre-filled. Some forms don't support URL pre-fill — in that case, copy the structured complaint text to clipboard and instruct the user to paste.

**Data freshness risk:** Phone numbers, email addresses, and web form URLs change. The `_contacts.json` `verified` field is the human attestation; before submission, a curator should call/email/visit each entry to re-verify. Alternative: a lightweight cron-style validator that pings each `web_url` and `web_form_url` and flags 404s. Not a hackathon-day priority but should be in the post-hackathon plan.

**Question for the reviewer:** Is this the right pattern, or is there a better information-architecture? E.g., should the contacts directory be one layer (`Contacts`) of the harness, callable as a tool by Gemma during a chat (so the model itself selects the right hotline), or stay UI-only? Pro of model-callable: it integrates with Gemma's native function-calling and the harness story. Con: another moving part to maintain + risk of model hallucinating a wrong number.

## 9. What I'd want a fresh reviewer to investigate

1. **Is `_brand.py` doing too much?** It now owns: product copy, version stamps, layer metadata, jurisdiction grouping, copy-text for grade-mode descriptions, plus `to_dict()` serialization. Should jurisdictions be its own `_jurisdictions.py`? Should brand serialization be a Pydantic model?

2. **Should `RAG_CORPUS` and `GREP_RULES` move to JSON?** Pros: curator workflow, no wheel rebuild for content edits. Cons: regex patterns in JSON need careful escaping; the existing pattern of "Python literal with `regex_literal_string=` annotation" is more readable than `"\\b(\\d{2,3})\\s*%..."`.

3. **Is the HTML approach (10 separate static pages, no bundler) right for v1?** Bundling would let us share components but adds build complexity. Currently zero JS framework — judges browsing source see plain HTML that's easy to read.

4. **The `evaluator_call` hook story.** We document it as the architecturally-correct way to use a separate model for LLM-judge grading (frontier API or larger Gemma) but on Kaggle T4 it falls back to in-process self-grade by VRAM necessity. Is this convincing or does it look like a punt?

5. **Risk of deeper-than-string regression in `<channel|>` handling.** What's the right way to consume Gemma 4 thinking-mode output? Should we be parsing token-IDs and switching on `<channel|>` token boundaries instead of post-hoc string-splitting?

6. **The pipeline modal latency budget bar.** It shows per-layer ms (Persona 0ms, GREP 30ms, RAG 1ms — these are tiny because regex + BM25 is fast) plus Gemma-generation ms (60-150 seconds for E2B). The bar visually dominates "Gemma" — is there a way to surface that "the harness adds 0.03s; the model takes 60s" framing more clearly?

7. **What viz is missing that would be a 5-minute judge "wow"?** We added the live GREP tester and cross-layer search in v0.14.3. What about a "compare two RAG docs" diff view? A geographic corridor map? A timeline of when ILO conventions were adopted? An "adversarial probe" replay (paste a known jailbreak, see which layers caught it)?

8. **The 13 Kaggle notebooks.** 1 core (the harness-chat) gets 90% of judge attention. 02-live-demo gets some. The 11 appendix notebooks are depth-of-engineering signals. Is the appendix bloat hurting more than helping? Should we cut some?

9. **The 587 example prompts across 8 audience buckets.** Does the audience-filter chip system in the chat UI's Examples modal expose them well, or is it overwhelming?

10. **Does the writeup accurately describe what's there?** docs/writeup_draft.md is 1,490/1,500 words. Did v0.14.2/0.14.3 land features that should be mentioned (live tester, cross-layer search, single-source-of-truth refactor)?

11. **Eight-component framing — credible or scope creep?** As of v0.14.7 the platform is documented as eight components: Runtime, Harness, Exchange, Eval, **Trainer (#5)**, Sentinel, **Channels (#7)**, Mobile. Trainer ships as a *prototype* via the A-07 bench-and-tune notebook (Unsloth → GGUF → HF Hub pipeline runs end-to-end; multi-tenant Trainer service is post-hackathon). Channels is *roadmap* (Messenger / WhatsApp / SMS / web / embassy-portal adapters; the chat package's FastAPI surface is the substrate but no live channel deployment exists). **Question for the reviewer:** is the "Live core (Runtime + Harness + Eval + Contacts) + Prototype (Trainer) + Roadmap (Exchange + Sentinel + Channels) + Sibling-repo (Mobile)" status taxonomy honest enough, or does naming Trainer + Channels invite "where's the WhatsApp demo?" expectations from judges? Architecture stubs at `docs/architecture/duecare_{trainer,channels}.md`. **Critical safety property:** none of the new components are wired into the live chat critical path — `kernel.py`, `app.py`, the model picker, and the boot smoke test all run cleanly with Trainer / Channels / Sentinel / Exchange absent. We deliberately did NOT add Messenger / WhatsApp / Twilio dependencies. Is this the right balance?

## 10. What you can ignore for purposes of this review

- The 7 sibling PyPI packages other than `duecare-llm-chat`. They're stable infrastructure (model adapters, agents, workflow runner). The chat package + the Kaggle kernel is where the action is.
- The Android Journey app (sibling repo `duecare-journey-android`) — separate codebase, separate review.
- The fine-tune pipeline (kaggle/A-07-bench-and-tune) — pending real GPU run; the architecture is documented in `docs/bench_and_tune_walkthrough.md`.
- Anything under `_archive/` or `_reference/` — historical/private, not in the public submission.

---

## Output I'd like from the reviewer

A prioritized **gameplan** with three buckets:

**P0 — Must do before submission (≤ 10 days):**
- Concrete file:line refactors that close real bugs
- Visualization wins that move the 70-point video score

**P1 — Worth doing if time permits:**
- Quality-of-life refactors that reduce future drift
- Architectural cleanups that unlock easier extension

**P2 — Defer to post-hackathon:**
- Big restructures that are right but not load-bearing for the demo

For each item, give: **what to change, where (file path), why, expected effort (15-min / 1-hr / half-day / multi-day), and what risk it introduces.** Be willing to say "don't do this in 10 days." The submission is the job; refactors that don't reach the judge are zero-value.
