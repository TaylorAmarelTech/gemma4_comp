# Release checklist — Duecare chat-package v0.14.7

> Run this checklist after pushing the wheel dataset to Kaggle and
> restarting the deployed kernel. Every step has an expected result.
> If a step fails, **stop** and fix before judges arrive.
>
> **Filename note:** kept as `release_checklist_v0_14_5.md` for link
> stability — content is current to v0.14.7 (wheel version per
> `pyproject.toml`). v0.14.6 and v0.14.7 were docs-only releases on
> top of the v0.14.5 P0 hardening pass.

## Phase 1 — Pre-flight (local, no Kaggle)

| # | Step | Expected | Actual |
|---|---|---|---|
| 1.1 | `py -3.10 scripts/v141_check_static_js.py` | All 11 static HTML files parse cleanly | ☐ |
| 1.2 | `py -3.10 scripts/v141_smoke_all_endpoints.py` | All ~50 endpoint checks pass; counts at or above v0.14 minimums | ☐ |
| 1.3 | `py -3.10 scripts/v141_smoke_rag_graph_endpoint.py` | 46 nodes / 46 edges / valid groups | ☐ |
| 1.4 | `py -3.10 scripts/v141_smoke_catalog_endpoints.py` | 161 grep / 46 rag / 5 tools / 7 personas / 26 contacts | ☐ |
| 1.5 | Sanitizer regression run (see test_model_output.py) | All 15 cases pass; verbatim leaked string is cleaned | ☐ |
| 1.6 | `py -3.10 scripts/v141_word_count.py` | Body ≤ 1,500 words | ☐ |

## Phase 2 — Push wheel + restart kernel

| # | Step | Expected | Actual |
|---|---|---|---|
| 2.1 | `cd kaggle/01-duecare-harness-chat/wheels && kaggle datasets version -m "v0.14.7: ..."` | New dataset version published | ☐ |
| 2.2 | Open notebook editor at https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat/edit | Latest dataset attached | ☐ |
| 2.3 | Click **Run All** | First cell runs install + self-audit | ☐ |
| 2.4 | Inspect notebook stdout for self-audit banner | Banner reads "DUECARE SELF-AUDIT · chat-package 0.14.7" with all minimums met | ☐ |
| 2.5 | If self-audit FAILS | Bump dataset version OR set `DUECARE_ALLOW_OLD_WHEEL=1` (only for intentional roll-back) | ☐ |
| 2.6 | Wait for cloudflared URL | URL printed in notebook stdout | ☐ |

## Phase 3 — Live URL verification (open from a browser with no Kaggle session)

Cloudflared URL shape: `https://<random>.trycloudflare.com`

### 3a. API endpoints (curl-able, no model load required)

| # | Endpoint | Expected |
|---|---|---|
| 3a.1 | `GET /api/version` | `chat_package: "0.14.7"`, `harness.rubric_version: "v3.10-evaluator-quality"`, n_grep_rules ≥ 150, n_rag_docs ≥ 40, n_dimensions ≥ 40 |
| 3a.2 | `GET /api/brand` | `versions.chat_package: "0.14.7"`, `counts.n_examples` ≥ 500, `layers` array of 6, `extras` array of 4, `severity_palette` dict |
| 3a.3 | `GET /api/health-check` | `package_version: "0.14.7"` (NOT "0.1.0"), all wired layers true, `harness_counts.grep_rules ≥ 150` |
| 3a.4 | `GET /api/rag/graph` | `meta.n_nodes: 46`, `meta.n_edges: 46`, no nodes in `group: "other"` |
| 3a.5 | `GET /api/harness-catalog/grep` | 161 items, each with `severity`, `citation`, `indicator`, `patterns`, `fire_count` |
| 3a.6 | `GET /api/harness-catalog/rag` | 46 items, each with `cites_out`, `cites_in`, `group_color` |
| 3a.7 | `POST /api/grep/test {"text": "passport held by employer"}` | At least one rule fires; `wired: true` |
| 3a.8 | `GET /api/search-all?q=passport` | `total > 0`, multi-layer hits |
| 3a.9 | `GET /api/contacts?country=Philippines` | 2+ entries (DMW + OWWA at minimum) |
| 3a.10 | `GET /api/governance/contacts` | Raw _contacts.json with 26 entries |

### 3b. Static viewer pages (load in browser)

| # | Page | Expected behavior |
|---|---|---|
| 3b.1 | `/` (chat UI) | Empty-state with 6 toggle tiles, model picker overlay, About / Compare / Harness ↗ buttons in top bar |
| 3b.2 | `/static/harness.html` | 6 layer cards + 4 extras (RAG GRAPH / LIVE TESTER / SEARCH / HOTLINES) with live counts |
| 3b.3 | `/static/grep-rules.html` | Sortable 161-rule table, severity filter, fire-count column, click-to-expand patterns, category histogram at top |
| 3b.4 | `/static/grep-tester.html` | Paste-and-run live tester. Click "5-indicator compound" preset → fires multiple rules with severity badges |
| 3b.5 | `/static/rag-corpus.html` | 46-doc list with jurisdiction chips (27 groups, 0 in "Other"), citation neighbors panel, recently-retrieved overlay (after a chat turn) |
| 3b.6 | `/static/rag-graph.html` | Force-directed 46-node graph with arrowheads, search box, jurisdiction dropdown, zoom/pan, ⬇ SVG export |
| 3b.7 | `/static/tools.html` | 5 tools + 5 backing tables (16 corridors / 25 fee labels / 11 ILO indicators / 12 NGO / 8 conventions) |
| 3b.8 | `/static/hotlines.html` | 26 contact cards, category badges, click-to-call / mailto / form-URL links, safety banner ("the user submits — we never auto-send") |
| 3b.9 | `/static/search.html` | Cross-layer search; type "passport" → multi-layer results with highlighting |

### 3c. Model load + chat

| # | Step | Expected |
|---|---|---|
| 3c.1 | Click model picker → pick **E2B** | Picker shows loading state with phase log. ≤ 60s on warm Kaggle worker |
| 3c.2 | Picker auto-enters chat | Empty-state shows 5 colored quick-action buttons |
| 3c.3 | Type "Hello" + send | Response appears WITHOUT `<channel|>` or `<thinking>...</thinking>` artifacts (sanitizer holding) |
| 3c.4 | Click `▸ View pipeline` | Pipeline modal opens; latency header reads "Harness added Xms ... Gemma generated for Yms" (NEW v0.14.5+ framing) |
| 3c.5 | Click `Grade response` (Universal) | All 46 dim rows render; version reads `v3.10-evaluator-quality` |
| 3c.6 | Open Compare tab → run "5-indicator compound" prompt | Side-by-side renders; score delta pill visible |

### 3d. Negative tests (these should NOT be visible)

| # | Probe | Should NOT see |
|---|---|---|
| 3d.1 | `/api/version` response | `chat_package: "0.1.0"` (would mean health-check fix didn't ship) |
| 3d.2 | Universal grader response | `version: "v3.6-usecase-aware"` or anything other than `v3.10-evaluator-quality` (would mean old wheel still serving) |
| 3d.3 | Any chat response | Visible `<thinking>` block, `<channel|>`, or `<end_of_turn>` token |
| 3d.4 | `/api/health-check.harness_counts.grep_rules` | < 150 (would mean stale harness data) |

## Phase 4 — Backup + freeze

| # | Step | Expected |
|---|---|---|
| 4.1 | Capture screen recording of full demo end-to-end | Video file saved locally as backup-if-URL-dies |
| 4.2 | Note Kaggle dataset version pin | Recorded in `docs/USER_TODO.md` step 11 |
| 4.3 | After T-3 days: **freeze**. Only do live verification + video capture + wording fixes | No code changes after T-3 unless P0 regression |

## Failure modes seen historically

If the **self-audit fails** with `n_dimensions < 40`:
- The OLD wheel is still serving. Bump the dataset version on Kaggle and restart the kernel.
- DO NOT set `DUECARE_ALLOW_OLD_WHEEL=1` unless you have a specific reason; it's a foot-gun for judges.

If a chat response shows `<channel|>` or `<thinking>...</thinking>`:
- The deployed kernel is older than v0.14.7. The sanitizer + tests went in v0.14.5+. Re-push.

If `/api/health-check.package_version` is `"0.1.0"`:
- The deployed kernel is older than v0.14.7. Re-push.

If `/api/contacts` returns 404:
- The contacts module landed in v0.14.4. Re-push.

If the writeup shows "35-doc corpus" anywhere:
- That's the v0.14.1 stale subtitle. Pull from `docs/writeup_draft.md` head; v0.14.5+ reads "46-doc legal corpus".

If the deployed kernel doesn't show the 8-component platform map:
- That's a v0.14.6+ feature. The platform map lives in
  `docs/product_definition.md` and `docs/architecture/`. The notebook
  itself doesn't need to render it — judges who follow the FOR_KAGGLE_JUDGES
  link reach it. Optional: a one-cell platform-map render via
  `scripts/_platform_map.py` data + `scripts/_notebook_display.py`
  helpers.
