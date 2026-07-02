# Codex follow-up goals — safe-text / standardize / polish extensions

> Last updated: 2026-05-24. Built on top of commit `84695fc` (the safe-text / standardize / polish landing).

Ten self-contained improvement prompts you can paste into Codex (or any AI coding assistant). Each one names the files to read first, the success criteria, and a copy-paste prompt block.

Run them in any order — the prompts are designed so each one can be picked up cold. Each one is sized for a single Codex session.

---

## Goal 1 — Add the polish button to search.html drafts

**Why it matters:** When a reviewer searches the web and drafts an envelope from a result, the draft is one-shot. Promoting it without iterating means the envelope may carry vague phrasing or a non-pattern quote into the saved knowledge store. The same `POST /api/knowledge/polish-envelope` endpoint already exists and is wired into knowledge.html — search.html just needs the same UX.

**Files to read first:**
- `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` — find `kxPolishDraft` and the "Polish further" button (search for `kx-polish-btn-`)
- `packages/duecare-llm-chat/src/duecare/chat/static/search.html` — find `searchRenderDraftCard()` (line ~681)
- `docs/safe_text_layer.md` — section "Iterative polish layer"

**Success criteria:**
- Every draft card produced by a search result has a "Polish further (Gemma 4)" button next to "Save this draft"
- Clicking the button calls `POST /api/knowledge/polish-envelope` with the envelope, then renders the critique summary + per-field diff in the same teal callout style as knowledge.html
- The button is disabled while a polish is in flight
- The activity log gets a `_searchLog.net` event when the request starts and `_searchLog.ok` when it completes
- The top-bar Gemma tally bumps on real polish runs (passes > 0)

**Copy-paste prompt:**
```
Read packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html and
locate the kxPolishDraft function plus its "Polish further (Gemma 4)"
button. Then port the same UX to
packages/duecare-llm-chat/src/duecare/chat/static/search.html inside
searchRenderDraftCard() so every drafted envelope from a search result
gets the same polish button + inline critique + diff panel. Reuse
_searchLog for activity-log events. Bump window.dcGemmaStats on real
polish runs. Do not change the server endpoint. After the edit, run
`python -c "import pathlib; assert 'Polish further' in
pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/search.html').read_text(encoding='utf-8')"`
to verify the button landed.
```

---

## Goal 2 — Multi-template fill from one bundle

**Why it matters:** A caseworker reviewing one bundle often needs the HK Labour Department complaint, the POEA referral, and the IOM intake all at once. Today they pick one template, fill it, save it, then go back and pick the next. Three separate Gemma calls instead of one orchestrated batch.

**Files to read first:**
- `packages/duecare-llm-chat/src/duecare/chat/templates.py` — `gemma_fill_template`, `bundle_excerpt_for_template`, `TEMPLATES_REGISTRY`
- `packages/duecare-llm-chat/src/duecare/chat/static/templates.html` — `tplGenerateDraft`, `_tplActive`, the template gallery

**Success criteria:**
- New endpoint `POST /api/templates/fill-batch` that accepts `{bundle, template_ids: [...], manual_fields: {template_id: {...}}, use_gemma: true}` and returns `{drafts: [{template_id, rendered, field_values, provenance, used_gemma, noise_scrubbed_before_gemma}]}`
- One Gemma call per requested template (still uses `gemma_fill_template`), but the bundle excerpt is computed once and reused
- Templates.html grows a "Fill all relevant" button that picks the templates whose `relevance_indicators` overlap with the bundle's ILO indicators
- Filled templates render as a stacked accordion (one per template) with the same field-provenance highlights
- Activity log reports per-template completion with timing

**Copy-paste prompt:**
```
Read packages/duecare-llm-chat/src/duecare/chat/templates.py for
gemma_fill_template and TEMPLATES_REGISTRY structure. Add a new endpoint
POST /api/templates/fill-batch that accepts a bundle + a list of
template_ids + optional per-template manual_fields, and runs
gemma_fill_template for each requested template (sharing the
bundle_excerpt_for_template result across calls). Return
{drafts: [{template_id, rendered, field_values, provenance,
used_gemma, noise_scrubbed_before_gemma}]}. Then update
packages/duecare-llm-chat/src/duecare/chat/static/templates.html to add
a "Fill all relevant" button that auto-selects templates whose
relevance_indicators overlap with bundle.intelligence.ilo_indicators and
renders the result as a stacked accordion. Wire tplLog events for each
template. Tests: add a TestFillBatch class in
packages/duecare-llm-chat/tests/test_runtime_extracts.py covering
selection, sharing of excerpt, and per-template provenance.
```

---

## Goal 3 — Field-source preview on the template page (before generate)

**Why it matters:** Today the field-provenance highlight (green=bundle, teal=Gemma, amber=manual, missing=red) appears AFTER you click Generate. A caseworker reviewing whether the bundle is ready for a particular template can't see which fields will need manual entry until they spend a Gemma call.

**Files to read first:**
- `packages/duecare-llm-chat/src/duecare/chat/templates.py` — `bundle_field_hint`, `TemplateSpec.fields`
- `packages/duecare-llm-chat/src/duecare/chat/static/templates.html` — `tplSelectTemplate`, `.tpl-field` styles

**Success criteria:**
- New endpoint `POST /api/templates/dry-run-fill` that runs only the deterministic bundle_hint pass (no Gemma) and returns `{field_sources: {field_id: "bundle_hint" | "missing"}}`
- Templates.html: when a template is picked AND a bundle is attached, fire `dry-run-fill` and color the field cards in advance (green for bundle_hint, gray for missing). Show a banner: "If you click Generate, Gemma will fill X of Y missing fields."
- No Gemma call yet — pure deterministic preview
- Recomputes when bundle changes

**Copy-paste prompt:**
```
Read packages/duecare-llm-chat/src/duecare/chat/templates.py for
bundle_field_hint and TemplateSpec.fields, and
packages/duecare-llm-chat/src/duecare/chat/static/templates.html for
tplSelectTemplate. Add a deterministic-only endpoint POST
/api/templates/dry-run-fill that runs ONLY the bundle_hint pass (skip
Gemma entirely) and returns {field_sources: {field_id: "bundle_hint" |
"missing"}, n_bundle_hits, n_missing, n_optional, n_required}. Then
update templates.html so when a template + bundle are both selected,
fire the dry-run and color the field cards before Generate is clicked.
Show a one-line banner above Generate ("Gemma will fill X of Y missing
required fields"). Recompute on bundle change. Reuse the existing
.tpl-field.prov-* CSS classes.
```

---

## Goal 4 — Process bundle to knowledge fact: one-click promote

**Why it matters:** After Bulk File Review finishes (case brief + edges + media review), a reviewer who wants to save a knowledge fact has to manually retype or copy-paste from the bundle. The bundle's typed edges already have all the data — they should be one click away from becoming a knowledge envelope.

**Files to read first:**
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py` — find where typed edges are produced; look for `intelligence["typed_edges"]`
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py` — `_build_draft_response`, `standardize_fact_envelope`
- `packages/duecare-llm-chat/src/duecare/chat/static/process.html` — find the edges-table rendering

**Success criteria:**
- Each typed edge in process.html grows a "Draft as knowledge fact" button
- Click calls `POST /api/knowledge/draft-envelope` with the edge serialized as raw_text (or via a new helper endpoint `POST /api/knowledge/from-edge` that builds the envelope directly from a typed-edge dict)
- The returned envelope opens in a modal with the same Polish-further button as knowledge.html
- Promote-from-modal saves into the local knowledge store
- Activity log reports the round-trip

**Copy-paste prompt:**
```
Read packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py
to find where typed edges are produced and rendered. Read
packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py
for _build_draft_response. Read
packages/duecare-llm-chat/src/duecare/chat/static/process.html for the
edges-table rendering. Add a "Draft as knowledge fact" button to each
typed-edge row that calls a new endpoint POST /api/knowledge/from-edge
which builds an envelope directly from {edge_type, source_node,
target_node, evidence, indicators, corridors, journey_stage}, runs
standardize_fact_envelope, and returns the envelope. In the UI, open
the result in a modal with the existing "Polish further" + "Promote
draft" buttons (reuse the same JS from knowledge.html — extract to
_polish_modal.js if it gets large). Activity log reports the round trip.
```

---

## Goal 5 — Auto-polish queue

**Why it matters:** A reviewer reviewing 50 drafts shouldn't have to click Polish 50 times. They should be able to flip a switch and have every new draft auto-polished before it lands in the list.

**Files to read first:**
- `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` — `kxPolishDraft`, the rendering loop
- `packages/duecare-llm-chat/src/duecare/chat/static/_nav.js` — `dcGemmaStats`

**Success criteria:**
- A checkbox in knowledge.html: "Auto-polish new drafts (uses 2x Gemma calls per draft)"
- When checked, every draft produced by `/api/knowledge/draft-envelope/start` is automatically polished after rendering
- The checkbox state persists in localStorage as `duecare:auto-polish`
- Activity log clearly says "Auto-polish: X of Y drafts polished" when done
- Tally counter bumps per draft

**Copy-paste prompt:**
```
Read packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html
for kxPolishDraft and the draft-rendering loop. Add a checkbox above
the draft list: "Auto-polish new drafts (uses 2x Gemma calls per
draft)". When checked, every draft produced by the draft job is
automatically polished after rendering (call kxPolishDraft sequentially
on each new card). Persist the checkbox state in
localStorage.setItem('duecare:auto-polish', '1'). Activity log reports
"Auto-polish: X of Y drafts polished (skipped Z for OOM/error)" when
the batch completes. Bump window.dcGemmaStats.bump('chat') per
successful polish. Add an OOM-aware skip: if a polish call errors, log
the error and continue to the next draft without crashing the queue.
```

---

## Goal 6 — Sample bundle for templates.html

**Why it matters:** Templates.html has no sample artifact. A first-time reviewer can't round-trip the flow in 30s — they have to upload a bundle through process.html first. That fails the rule-7 sample-artifact requirement in `.claude/rules/70_workbench_ui_primitives.md`.

**Files to read first:**
- `scripts/build_static_samples.py` — see how other samples are built deterministically
- `packages/duecare-llm-chat/src/duecare/chat/static/samples/sample_manifest.json` — the index
- `packages/duecare-llm-chat/src/duecare/chat/static/templates.html` — find where Bundle JSON gets attached

**Success criteria:**
- New sample artifact `samples/template_bundle_sample.json` — a synthetic case bundle with intelligence, payments, journey_points, ILO indicators sufficient to exercise the HK Labour template
- Composite / synthetic only — no real names, case numbers, PII
- Templates.html grows two new buttons: "Download sample bundle" and "Use sample bundle" (loads it into the page state)
- `scripts/build_static_samples.py` regenerates it deterministically (fixed timestamps)
- Sample manifest includes it

**Copy-paste prompt:**
```
Read scripts/build_static_samples.py to understand the deterministic
sample-build pattern. Read
packages/duecare-llm-chat/src/duecare/chat/static/samples/sample_manifest.json
for the index format. Read
packages/duecare-llm-chat/src/duecare/chat/static/templates.html to
find where bundle JSON is attached. Add a new sample
samples/template_bundle_sample.json — a synthetic case bundle (no real
PII, composite Maria-style example) with intelligence.summary,
intelligence.case_brief, intelligence.people, intelligence.payments
including PHP placement fee + HKD salary deduction, intelligence.
journey_points covering recruitment through arrival, and
intelligence.ilo_indicators with fee_camouflage + passport_retention.
Build it via build_static_samples.py with fixed timestamps. Update
sample_manifest.json. Add "Download sample bundle" + "Use sample
bundle" buttons to templates.html that download / load the sample.
Activity log reports the load.
```

---

## Goal 7 — Vocabulary discovery script

**Why it matters:** STANDARD_FACT_INDICATORS is intentionally curated. Real saved knowledge will produce indicators we forgot or that arrived from a Gemma rewrite. We need visibility into "which indicators are showing up in saved envelopes that aren't in the canonical list" so we can either add them or fix the upstream rule.

**Files to read first:**
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py` — `STANDARD_FACT_INDICATORS`, `STANDARD_FACT_STAGES`
- Wherever knowledge envelopes are stored locally (look in `chat/app.py` for the knowledge-list endpoint to find the path)

**Success criteria:**
- New script `scripts/audit_knowledge_vocabularies.py` that walks the local knowledge store and reports indicators / corridors / stages used in saved envelopes
- Output split into three buckets: canonical (in STANDARD_FACT_*), known-alias (in _*_ALIASES), unknown
- For each unknown, show the envelope path + the offending value so the user can decide: add to vocab, fix the source, or drop the envelope
- No file modifications — read-only

**Copy-paste prompt:**
```
Read packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py
for STANDARD_FACT_INDICATORS, STANDARD_FACT_STAGES,
_INDICATOR_ALIASES, _STAGE_ALIASES. Find where saved knowledge
envelopes live by reading the /api/knowledge/list handler in
packages/duecare-llm-chat/src/duecare/chat/app.py. Create
scripts/audit_knowledge_vocabularies.py that walks every saved
envelope, extracts content.indicators, content.applies_to_indicators,
content.risk_indicators, content.signal_types, content.corridor, content.corridors,
content.journey_stage, content.stages, and reports each token in one of
three buckets: CANONICAL, KNOWN_ALIAS, UNKNOWN. For UNKNOWN, print the
envelope path + the offending value. Pure-stdlib (no pip install). Read
only — no file modifications. Run from the repo root.
```

---

## Goal 8 — Highlight diff in the polish panel

**Why it matters:** The polish panel today shows before / after columns. A reviewer scanning for what specifically changed has to read both sides. Word-level inline highlighting (red strike on removed words, green underline on added) would speed bulk review.

**Files to read first:**
- `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` — `kxPolishDraft`, the diff-table rendering
- Any existing diff library in the repo (search for `difflib` in JS or Python)

**Success criteria:**
- Add a tiny word-level diff to the per-field rows in the polish output
- Use semantic colors from `docs/ui_color_vocabulary.md` (red oklch(0.55 0.18 25) for removed, green oklch(0.62 0.10 155) for added)
- Render with `<del>` and `<ins>` tags so screen readers handle it
- Falls back to the existing before/after columns when text is too long for a useful word-level diff (>240 chars)

**Copy-paste prompt:**
```
Read packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html
and find kxPolishDraft + the diff-table rendering. Add a tiny
word-level diff renderer that takes the before / after pair and
produces inline <del>...</del><ins>...</ins> spans using the project's
color vocabulary: red oklch(0.55 0.18 25) for removed, green oklch(0.62
0.10 155) for added. Use the longest-common-subsequence algorithm
inline (no library import). Render the inline diff in the field row's
single "diff" column when both before and after are under 240 chars;
fall back to the existing two-column layout otherwise. Honor the
project's no-emoji rule. The diff should NOT include the raw text in
innerHTML — use createElement + textContent for every word, with
className for styling.
```

---

## Goal 9 — Standardize graph-chat synthesis output

**Why it matters:** The process page's graph-chat synthesis returns an answer composed from intelligence + deterministic table + Gemma synthesis. The synthesis text isn't passed through `standardize_fact_envelope` because it's not an envelope — but the indicator / corridor / stage references in the synthesis SHOULD use canonical vocabulary so reviewers see the same names everywhere.

**Files to read first:**
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py` — find the graph-chat synthesis function
- `packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py` — `_normalize_indicator`, `_normalize_corridor`, `_normalize_stage`

**Success criteria:**
- New helper in `_safe_text.py`: `normalize_inline_vocabulary(text)` that finds non-canonical indicator / corridor / stage tokens in free-text and rewrites them to canonical
- Applied to the graph-chat synthesis text before returning
- Doesn't break sentence flow — handle common embeddings ("the FeeBondage indicator" → "the fee_bondage indicator")
- Tests for the inline normalization

**Copy-paste prompt:**
```
Read packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py
to see _normalize_indicator, _normalize_corridor, _normalize_stage.
Read packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py
to find the graph-chat synthesis function (look for "synthesis" near
graph-chat). Add a new helper to _safe_text.py:
normalize_inline_vocabulary(text) that scans free-text for known
non-canonical indicator names (FeeBondage, fee-bondage, FeeCamouflage,
etc.), corridors (ph-hk, PH/HK), and stages (Arrival, placement,
Recruit) and rewrites them to canonical form. Preserve surrounding
words. Apply this to the graph-chat synthesis text before returning
the response. Add a TestNormalizeInlineVocabulary class to
test_knowledge_noise_scrub.py covering: case variations, hyphenated
forms, multi-word neighbors ("the FeeBondage indicator"). Idempotent.
```

---

## Goal 10 — End-to-end Playwright test for the polish flow

**Why it matters:** The polish endpoint has unit-test coverage but the knowledge.html UI button is untested. A future refactor of `kxPolishDraft` could silently break the click handler, and the unit tests wouldn't catch it.

**Files to read first:**
- `packages/duecare-llm-chat/tests/test_compare.py` or `test_harness_workbench.py` — see how existing E2E tests start a FastAPI app + drive a fake browser
- `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` — `kxPolishDraft`, the button id pattern

**Success criteria:**
- New test in `packages/duecare-llm-chat/tests/test_polish_envelope.py` that:
  1. Starts a FastAPI app with a stub `gemma_call`
  2. Posts a draft envelope via `/api/knowledge/draft-envelope`
  3. Posts that envelope to `/api/knowledge/polish-envelope`
  4. Verifies the response has the expected envelope + critique + diff shape
  5. Verifies the stub gemma_call was called exactly twice (one critique, one rewrite)
  6. Verifies `polish_skipped` path when gemma_call is None
- Skip the actual browser test — pure server-side proves the contract

**Copy-paste prompt:**
```
Read packages/duecare-llm-chat/tests/test_compare.py and
test_harness_workbench.py to see how the existing tests construct a
FastAPI app + stub a gemma_call. Read
packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py
for the _build_polish_response signature. Create
packages/duecare-llm-chat/tests/test_polish_envelope.py with two
classes:

TestPolishEndpointHappyPath:
  - test_two_pass_polish_calls_gemma_twice (stub gemma_call returns
    valid critique JSON then valid rewrite JSON, verify both called)
  - test_response_shape (verify {envelope, critique, passes, diff}
    keys present)
  - test_envelope_marked_polished (extensions.polished_by_gemma is
    True, polish_passes is 2)
  - test_diff_reflects_changes (changed=True entries match the
    fields the rewrite altered)

TestPolishEndpointFallback:
  - test_no_gemma_skips_and_standardizes (gemma_call=None still
    returns a standardized envelope with polish_skipped)
  - test_critique_json_parse_fails_skips_rewrite (Gemma returns
    garbage; verify polish_critique_error in extensions)
  - test_clean_pass_returns_one_pass (Gemma critique returns empty
    issues; verify polish_clean_pass is True)
```

---

## Suggested ordering

| Order | Goal | Why this order |
|---|---|---|
| 1 | Goal 10 (E2E tests for polish) | Lock in the contract before extending |
| 2 | Goal 1 (Polish on search.html) | Same UX pattern, immediate visible win |
| 3 | Goal 6 (Sample bundle for templates) | Unblocks reviewers' first-time-templates-flow |
| 4 | Goal 3 (Field-source preview) | Improves templates UX with no Gemma cost |
| 5 | Goal 4 (Process → knowledge one-click) | Connects two big surfaces |
| 6 | Goal 5 (Auto-polish queue) | Power-user feature, depends on Goal 1 |
| 7 | Goal 8 (Inline word diff) | Polish UX polish, depends on Goals 1 and 5 |
| 8 | Goal 2 (Multi-template fill) | Larger refactor; do after the small wins |
| 9 | Goal 9 (Inline vocab normalize) | Surface polish |
| 10 | Goal 7 (Vocab audit script) | Diagnostic tool; not urgent unless you're auditing |

## How to use these prompts

1. Pick a goal that matches what's painful right now.
2. Paste the "Copy-paste prompt" block into your Codex session.
3. Codex reads the named files first, makes the change, and runs the suggested verification command.
4. Run `python scripts/validate_main_kaggle_kernels.py` before committing so the Kaggle root layout, two active Kaggle kernels, and two optional benchmark kernels keep parsing and keep their Kaggle boot tokens.
5. Review the resulting diff before merging.
6. If you want to know the rationale (the "Why this matters" section), paste that too — it gives Codex context for judgment calls.

## What I deliberately did NOT include

- **Switching the scrub from regex to a parser** — over-engineered for the patterns we have. Regex is fine.
- **Cross-page state for the polish queue** — too much complexity. Each page owns its own queue.
- **A GUI for editing STANDARD_FACT_INDICATORS** — that's a vocabulary tuple committed to git; let humans review the PR.
- **Web-based Gemma model picker** — already exists at /static/models.html. Don't reinvent.
- **Anything that requires changes to the canonical kernel runtime contract** — outside this scope; see `.claude/rules/81_canonical_runtime.md`.
