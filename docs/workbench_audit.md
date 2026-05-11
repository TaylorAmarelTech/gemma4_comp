# DueCare Workbench — UI/UX audit, rubric, and proposed architecture

> Three things in one document:
> 1. A **rubric and design principles** for what the workbench must be (and must not be).
> 2. A complete **audit** of every API endpoint, every existing static page, and every documented audience the workbench should serve.
> 3. A concrete **proposed architecture** with phased implementation steps.

---

## Part I — UI/UX rubric and design principles

These are the rules every workbench page is graded against. Print them
on a sticky note. Each principle has a "do" and a "don't" so it stays
operational, not aspirational.

### P1. One page, one job

Every page does **one** thing. The chat page chats. The grade page
grades. The import page imports.

- **Do:** make the primary action of every page describable in a single
  imperative sentence ("Score this content," "Show me the rules that
  match this text," "Upload my documents and search them").
- **Don't:** stuff secondary tools (grade, classify, import) into a
  slide-out, modal, or right-rail of an already-busy page. If a feature
  needs to exist, it gets its own URL.

### P2. Progressive disclosure beats a wall of options

A new visitor should see the *primary* action, not every knob.

- **Do:** show 1-3 prominent CTAs above the fold; hide tuning knobs
  behind a "▸ Configure" expander; collapse advanced settings into a
  Settings tab.
- **Don't:** present 6 layer toggles + 9 model variants + 4 grade modes
  + 5 retrieval knobs all at once on the chat page.

### P3. Transparency is mandatory, but it's a clickable ribbon, not a wall

Every assistant response must show *what fired*, but in a one-line
summary that expands.

- **Do:** show a single-line trace strip (`PERSONA · GREP(7) · RAG(top-5)
  · TOOLS(2) · 1.4s`) under every reply. Click → full pipeline trace.
- **Don't:** print 200 lines of raw JSON inline by default. Don't
  require a button-click to see *whether* the harness ran — only to see
  the *details*.

### P4. Citations are clickable evidence, not inline strings

When Gemma cites "ILO C181" or "POEA Circular 015," that string is a
link to the actual source text.

- **Do:** make every cited statute / convention / circular open the
  source in a side-panel slice from `/api/harness-catalog/rag`.
- **Don't:** leave citations as plain text the user has to copy-paste
  into a separate viewer page.

### P5. Audience-first, then capability

Top-level navigation reflects the **5 canonical audiences** plus the
**capability tabs**. A first-time visitor picks "I am an NGO" and gets
the right defaults. Power users skip to the capability tabs directly.

- **Do:** two-row nav — Row 1 = "Platform safety / NGO & regulator /
  Worker / Researcher / Developer", Row 2 = "Chat / Classify / Anonymize
  / Import / Grade / Layers / Logs / Models / Settings".
- **Don't:** force every audience through the same generic chat page
  hoping they'll discover the right configuration on their own.

### P6. Logs are first-class, not buried

Auditability is the project's whole proposition; the logs page must be
linkable from the top nav.

- **Do:** a top-level **Logs** tab that surfaces governance events,
  pipeline traces, and audit trail. Make every event filterable by
  time, layer, severity, audience.
- **Don't:** route the audit trail through `/api/governance` JSON only.
  If a regulator asks "show me the trail," they need a URL, not curl.

### P7. Showcase every functionality, but on its own stage

The user's point: every aspect (moderation, research, OFW chat,
anonymization, etc.) deserves a dedicated, prominent way to be
demonstrated.

- **Do:** every API capability gets a UI page even if the page is
  small. Audience showcase pages then *compose* those primitives into
  a curated demo flow.
- **Don't:** assume the chat page can stand in for all of them. A
  judge looking at a research demo shouldn't have to mentally translate
  from "free-form chat" to "this is what NGO triage looks like."

### P8. Modals must fit the viewport

Lightboxes never exceed `min(92vh, 100dvh - 48px)`. Body scrolls; chrome
stays pinned.

- **Do:** clamp every modal's max-height; lock body scroll behind
  modals; use `dvh` not `vh` for mobile.
- **Don't:** ship a modal that requires the user to guess what's hidden
  off-screen.

### P9. Mobile is not an afterthought

Worker / mobile is one of the 5 canonical audiences. Touch targets ≥44px;
a single-column layout at `< 600px`; no horizontal scroll.

- **Do:** test every page at 375 × 667 (iPhone SE) before declaring
  done. Use `dvh`/`svh` units for full-screen pages.
- **Don't:** ship a 4-column tile grid that becomes 6 vertical
  paragraphs on a phone before the user can find the textarea.

### P10. Match duecare-ai.com visual language

The workbench is the same product as the public website. Same paper
backgrounds, same Inter + JetBrains Mono fonts, same civic-tech accent.

- **Do:** import `_chrome.css`; use the token system; use `var(--paper)`,
  `var(--ink)`, `var(--accent)`; match `_nav.html` from
  `apps/duecare-ai.com/app/templates/`.
- **Don't:** introduce one-off page palettes or new fonts. Don't add
  "for this page only" colour overrides.

### P11. Every claim is verifiable from the workbench

If the README says "161 GREP rules", clicking through must show all
161. If it says "46 RAG docs across 27 jurisdictions", clicking through
must show that too. The workbench is the proof of every public claim.

- **Do:** cross-link counts from README → live API → live page.
- **Don't:** leave headline numbers as static text in a doc with no
  way to verify them at runtime.

### P12. Don't break what works

The chat shell is currently the reference implementation. Every
extraction (grade panel → grade page, import slide-out → import page)
must preserve identical behaviour, just on a less-crowded page.

- **Do:** keep API contracts; reuse the same JS handlers via shared
  modules; verify the chat still works after each extraction.
- **Don't:** rewrite working logic in pursuit of a cleaner page.

---

## Part II — Audit

### A. Audiences (canonical, from `docs/canonical_use_cases_and_components.md`)

| Lane | Plain-language name | What they need to do in the workbench |
|---|---|---|
| 1 | **Platform safety** | Score recruitment posts/messages, see why a post was flagged, route high-risk items to reviewers, share anonymized abuse patterns. |
| 2 | **NGO & regulator** | Triage messages and documents, draft complaint materials, find trusted contacts, update corridor knowledge, render case bundles. |
| 3 | **Individual worker / mobile** | Privately check a suspicious offer, contract, recruiter message, fee demand; get localized warning signs and trusted next-step contacts. |
| 4 | **Researcher** | Reproduce prompts, compare model variants, run rule-based and LLM-based grading, audit every claim from source artifacts. |
| 5 | **Developer / integration partner** | Hit APIs, install wheels, validate pack schemas, version-pin, copy embed snippets. |

### B. Chat-package APIs (41 routes)

**Setup & health:** `GET /healthz`, `/api/version`, `/api/health-check`,
`/api/brand`, `/api/model-info`, `/api/harness-info`.

**Catalog (per-layer browsers):** `GET /api/harness-catalog/{persona|grep|rag|tools|online}`,
`/api/personas`, `/api/contacts`, `/api/rag/graph`, `/api/search-all?q=`.

**Layer testing:** `POST /api/grep/test`, `POST /api/online/test`,
`GET/POST /api/online/config`.

**Chat:** `POST /api/chat/send`, `/api/chat/upload-image`, `GET /api/chat/image/{sid}`.

**Evaluation / grading:** `POST /api/grade`, `/api/grade-deep`,
`/api/grade-combined`, plus streaming variants;
`/api/classify-prompt`; `GET /api/evaluation-questions`,
`/api/rubric-hints`, `/api/baseline`, `/api/examples`.

**Knowledge import:** `POST /api/import/upload`, `/api/import/snippet`;
`GET /api/import/list`, `/api/import/{doc_id}`; `DELETE /api/import/{doc_id}`,
`/api/import`.

**Retrieval tuning:** `GET/POST /api/retrieval/config`,
`POST /api/retrieval/embed-cache/clear`.

**Governance:** `GET /api/governance`, `/api/governance/{name}`,
`/api/docs/{layer}`.

### C. Server-package APIs (59 routes)

**Health & config:** `/healthz`, `/api/status`, `/api/model-info`,
`/api/config/{knowledge_base|tools|heuristics|hotlines|db_schema|handlers}`,
`/api/settings`.

**Moderation (Platform-safety lane):** `POST /api/moderate`,
`/api/moderate_file`, `/api/moderate_batch`, `GET /api/batch/{id}`,
`/api/batches`.

**Worker check (Worker lane):** `POST /api/worker_check`,
`/api/worker_check_file`.

**Research (Researcher lane):** `POST /api/research/openclaw`,
`/api/process`, `GET /api/jobs/{id}`, `/api/jobs`.

**Benchmark:** `GET /api/benchmark/sets`, `POST /api/benchmark/run`,
`GET /api/benchmark/status/{id}`, `/api/benchmark/export/{id}`.

**Queue:** `POST /api/queue/submit`, `GET /api/queue/status/{id}`,
`/api/queue/list`, `/api/queue/stats`.

**Knowledge / evidence (NGO lane):** `POST /api/ingest`, `GET /api/runs`,
`/api/entities`, `/api/findings`, `/api/graph`, `POST /api/query`.

**Complaints (NGO lane):** `GET /api/complaints/list`,
`POST /api/complaints/render`.

**Activity / metrics / logs:** `GET /api/stats`, `/api/activity`,
`/metrics`, `/api/logs`, `/api/logs/stats`, `POST /api/logs/clear`.

### D. Existing static pages (chat package — 12 pages)

| Page | Audience | Purpose |
|---|---|---|
| `index.html` | All | Chat (currently overloaded — does chat + harness picker + grade + pipeline + import) |
| `harness.html` | All | Layer catalog index (6 cards) |
| `persona.html` | All | Persona library |
| `grep-rules.html` | Researcher / Dev | 161 GREP rules table with citations + fire counts |
| `grep-tester.html` | All | Paste any text → see fired rules (no LLM) |
| `rag-corpus.html` | NGO / Researcher | 46 RAG docs by jurisdiction with full text + neighbours |
| `rag-graph.html` | Researcher | Force-directed citation graph |
| `tools.html` | Dev | 5 function-calling tools + backing tables |
| `online.html` | Dev | Web search provider config |
| `search.html` | All | Cross-layer "search anything" |
| `hotlines.html` | Worker / NGO | NGO/regulator/embassy directory with click-to-call |
| `anonymization-preview.html` | Worker / NGO | Paste text → see exactly what would be sent before sending |

### E. Existing static pages (server package — 18 pages, already light-themed)

| Page | Audience | Purpose |
|---|---|---|
| `index.html` | All | Hub homepage (5-card layout) |
| `enterprise.html` | Platform safety | Compliance moderation flow |
| `individual.html` | Worker | Worker chatbot |
| `knowledge.html` | NGO / Researcher | Knowledge-graph browser |
| `dashboard.html` | All | Stats / activity dashboard |
| `workspace.html` | NGO | Case workbench |
| `chat.html` | All | Bare-bones chat (debug) |
| `demo.html` | Researcher | Slideshow demo of the pipeline |
| `evidence.html` | NGO | Case evidence ingestion |
| `architecture.html` | Dev | Architecture diagrams |
| `background.html` | All | Project background |
| `credits.html` | All | Attribution |
| `queue.html` | Dev | Task queue browser |
| `logs.html` | Dev / Researcher | Audit logs |
| `settings.html` | Dev | Configuration |

### F. Auxiliary static (chat package)
- `classifier_static/index.html` — content classifier with multimodal upload + harness toggles + result history.

### G. Functional capability matrix

Cross-tabulating capabilities × audiences shows which workbench tab
each audience needs:

| Capability | Platform safety | NGO & regulator | Worker / mobile | Researcher | Developer |
|---|---|---|---|---|---|
| **Chat playground** (free-form Gemma) | ✓ moderate | ✓ triage | ✓ ask | ✓ probe | ✓ test |
| **Content classifier** (single item → score + action) | ✓ primary | ✓ for messages | ✓ check this msg | ✓ benchmark | ✓ embed |
| **Anonymization preview** | — | ✓ before submit | ✓ before submit | — | ✓ verify |
| **Knowledge import** (own docs) | ✓ corp policy | ✓ NGO briefs | ✓ contract | ✓ corpus | ✓ test data |
| **Layer browser** (persona/GREP/RAG/tools/online) | — | ✓ what we know | — | ✓ primary | ✓ schema |
| **Live GREP tester** (paste → fired rules) | ✓ rule debug | ✓ verify hit | — | ✓ tune | ✓ port |
| **Cross-layer search** | ✓ "passport" | ✓ "C181" | — | ✓ corpus | ✓ schema |
| **Citation graph** (RAG) | — | ✓ source tree | — | ✓ primary | ✓ structure |
| **Hotline directory** | — | ✓ refer | ✓ call | — | ✓ embed |
| **Pipeline trace** (per-message) | ✓ explain to mod | ✓ explain to client | — | ✓ primary | ✓ debug |
| **Grading** (4 modes) | ✓ regression | ✓ rank drafts | — | ✓ primary | ✓ CI |
| **Anonymized submission** | ✓ aggregate | ✓ pattern share | ✓ optional | — | ✓ API |
| **Logs / audit trail** | ✓ compliance | ✓ casework | — | ✓ provenance | ✓ debug |
| **Model picker + load logs** | ✓ verify model | — | ✓ which Gemma | ✓ primary | ✓ embed |
| **Settings / config** | ✓ tenant | ✓ org | — | ✓ knobs | ✓ all |

### H. Gaps (functionality not yet exposed in any UI)

These are real capabilities the API supports but no current page uses:

1. **Stand-alone grader** — `POST /api/grade` exists but only via the chat shell.
2. **Pipeline replay** — pipeline-trace data exists in the chat reply but no way to fetch it later.
3. **Submission inbox** — `anonymization-preview.html` shows what *would* be sent; nothing shows what *was* sent or accepted.
4. **Model-load workbench** — picker overlay exists but no dedicated page for available models, GPU memory, load logs.
5. **Knowledge-import workbench** — `POST /api/import/upload` exists but UI is buried in a chat slide-out; no drag-drop, no listing.
6. **Logs viewer** (chat package) — server has `/logs` page; chat package has no equivalent.
7. **Benchmark runner** — server has `/api/benchmark/run`; no UI on the chat side.
8. **Embed-snippet generator** — Developer lane needs "here's the snippet for this configuration"; doesn't exist.

---

## Part III — Proposed architecture

### Top-level navigation

**Two rows of tabs** so audience-by-role and capability-by-task both have a home, instead of cramming everything into one row:

**Row 1 — Audience showcases** (matches the 5 canonical lanes):

```
Platform safety  ·  NGO & regulator  ·  Individual worker  ·  Researcher  ·  Developer
```

Each one is a curated landing page that pre-selects the layers, picks
the model, and offers 2-3 demonstration prompts that prove the lane's
outcome. No fiddling required.

**Row 2 — Capability tabs** (transparency / auditability):

```
Chat  ·  Classify  ·  Anonymize  ·  Import  ·  Grade  ·  Layers  ·  Logs  ·  Models  ·  Settings
```

Each one is a focused workbench page for *one* capability. They share
the loaded model, the harness configuration, and the imported knowledge
across pages.

### Page-by-page ownership

| Tab | Renders | Backed by | Replaces / extracted from |
|---|---|---|---|
| **`Platform safety`** | Curated moderation demo (3 sample posts → score + action + explanation) | `/api/classify-prompt`, `/api/grep/test`, `/api/chat/send` | New page |
| **`NGO & regulator`** | Curated case-triage demo (intake msg → grounded draft + hotline + pipeline) | `/api/chat/send` + `/api/contacts` + `/api/grade` | New page |
| **`Individual worker`** | Curated mobile-style chat (single prompt → warning + rights + hotline) | `/api/chat/send`, `/api/contacts` | New page |
| **`Researcher`** | Curated A/B (baseline vs full harness on same prompt + grade table) | `/api/chat/send` ×2, `/api/grade-combined` | New page |
| **`Developer`** | Curated API tour (live curl examples for each endpoint) | All endpoints + embed snippets | New page |
| **`Chat`** | The current chat shell, slimmed | `/api/chat/send` | Current `index.html` minus picker, grade, import |
| **`Classify`** | Single-content scorer with action recommendation | `/api/classify-prompt`, `/api/grep/test` | `classifier_static/index.html` |
| **`Anonymize`** | Sanitization preview + submission draft + receipt | `/api/anonymize`, `/api/share/submit` | `anonymization-preview.html` |
| **`Import`** | Drag-drop folder/zip upload, list, delete, BM25 over imports | `/api/import/*` | New (extracted from chat slide-out) |
| **`Grade`** | Paste prompt + response → 4-mode grade panel | `/api/grade*`, `/api/evaluation-questions` | New (extracted from chat) |
| **`Layers`** | Browse persona / GREP / RAG / tools / online catalogs | `/api/harness-catalog/{layer}`, `/api/search-all` | `harness.html` + child viewers |
| **`Logs`** | Pipeline traces + governance log + audit trail | `/api/governance`, plus a new `/api/traces` endpoint | New (chat side) |
| **`Models`** | Model picker, load logs, GPU memory, variant table | `/api/load-model/*`, `/api/model-info` | New (extracted from picker overlay) |
| **`Settings`** | Retrieval config, online providers, model variant pin | `/api/retrieval/config`, `/api/online/config` | New |

### Modal overflow fix (cross-cutting)

Every modal/lightbox capped at `min(92vh, 100dvh - 48px)` with a
scroll-locked body. Picker overlay padding clamped to
`clamp(8px, 2vh, 24px)`. Applied via shared `_chrome.css` so all
pages inherit.

### Implementation phases

| Phase | Scope | Effort | Visible payoff |
|---|---|---|---|
| **P0 Modal fix** | CSS clamp on `.modal`, `.picker-box`, `.picker-overlay` | 30 min | All current modals fit any viewport |
| **P1 Shared nav** | `_nav.html` partial + tiny inject script + add to all 12 chat pages | 2 hr | Every page links to every page; feels like one app |
| **P2 Slim the chat shell** | Move grade panel, import slide-out, classify into separate pages | 3 hr | Chat is just chat; secondary tools breathe |
| **P3 Build the 5 audience showcase pages** | Curated demo flows per lane | 1 day | Judges pick "I'm an NGO" and see the right story |
| **P4 Build the 4 new capability pages** | `Models`, `Logs`, `Import`, `Grade` standalone | 1 day | Every API capability has a UI |
| **P5 Rename + republish** | Folder + Kaggle slug + wheel rebuild + dataset push | 30 min | "Workbench" branding live |

Each phase ships independently. P0 + P1 alone gives 80% of the
perceived quality lift.

### Naming

- Folder: `kaggle/01-duecare-exploration-workbench/` → `kaggle/01-duecare-workbench/`
- Kaggle slug: `taylorsamarel/duecare-harness-chat` → `taylorsamarel/duecare-workbench`
- README title: "Migrant-worker safety playground" → "DueCare Workbench"
- Sub-title: "Verify every safety layer, every grading mode, every audience flow, every API endpoint — from one URL"

### What this audit does NOT change

- Existing API contracts (every endpoint stays at the same path)
- Existing layer counts (161 / 46 / 5 / 6 / 12 stay verbatim)
- Existing wheel format (still a chat-package wheel)
- The duecare-ai.com public website (this is the *Kaggle* notebook)
- The 02-live-demo notebook (stays the focused walkthrough)

The workbench is purely a UI re-organisation of capabilities that
already exist, plus a few small new pages that surface real APIs that
currently have no UI.

---

## Part IV — Decision checklist for every new workbench page

Before merging a new page, walk it through this checklist:

- [ ] Can the primary action be described in one imperative sentence? (P1)
- [ ] Are there ≤ 3 prominent CTAs above the fold? (P2)
- [ ] Does every assistant response show a one-line trace strip? (P3)
- [ ] Are citations clickable? (P4)
- [ ] Does the page belong on the audience row, the capability row, or both? (P5)
- [ ] Is there at least one log/audit affordance reachable in 1 click? (P6)
- [ ] Could a judge use this page in isolation to demonstrate one thing? (P7)
- [ ] Do all modals fit `min(92vh, 100dvh - 48px)`? (P8)
- [ ] Does the page work at 375 × 667 with thumb-reachable composer? (P9)
- [ ] Does it import `_chrome.css` and use the duecare-ai.com tokens? (P10)
- [ ] Does every count / claim shown link to live API verification? (P11)
- [ ] Did the chat shell keep working after this extraction? (P12)
