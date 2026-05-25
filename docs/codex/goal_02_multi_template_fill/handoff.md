# Goal 2 — Multi-template fill from one bundle

> Status: **DONE 2026-05-24 (`1c0d3ff`)**. Created 2026-05-24.

## 1. Goal

Let a caseworker fill multiple complaint templates from the same case bundle in one batched action — Gemma orchestrates the per-template fills, the bundle excerpt is computed once and reused.

## 2. Why it matters

A reviewer triaging one bundle often needs the HK Labour Department complaint, the POEA referral, and the IOM intake all at once. Today they pick one template, click Generate (one Gemma call), save the draft, then go back and pick the next template (another Gemma call). Three separate trips through the UI for what could be one orchestrated batch. The bundle excerpt is identical each time; recomputing it three times burns context and reviewer attention.

## 3. Current state

- `POST /api/templates/fill` takes `{template_id, bundle, manual_fields, use_gemma}` and returns one filled template.
- `templates.html` shows a gallery; you click one template card, fill in manual overrides, click Generate.
- `gemma_fill_template()` in `chat/templates.py` runs a 3-pass fill (bundle_hint → manual → Gemma gaps).
- `bundle_excerpt_for_template()` builds the case-bundle JSON snippet Gemma sees. Now scrubbed for kernel paths (commit `84695fc`).
- `TEMPLATES_REGISTRY` has ~5-10 registered templates; each `TemplateSpec` has a `relevance_indicators` tuple (verify the field name when reading).

## 4. Target state

- New endpoint `POST /api/templates/fill-batch` accepts `{bundle, template_ids: [...], manual_fields: {template_id: {...}}, use_gemma: bool}` and returns `{drafts: [{template_id, rendered, field_values, provenance, used_gemma, noise_scrubbed_before_gemma}], shared_excerpt_chars: int}`.
- One Gemma call per requested template (still uses `gemma_fill_template`), but `bundle_excerpt_for_template(bundle)` is computed ONCE and reused across all calls.
- Templates.html grows a "Fill all relevant" button that:
  - Reads `bundle.intelligence.ilo_indicators`.
  - Picks templates whose `relevance_indicators` overlap with the bundle indicators.
  - Posts to `/api/templates/fill-batch`.
  - Renders the result as a stacked accordion (one section per template) with the same field-provenance highlights.
- Activity log reports per-template completion with timing.

## 5. Files to read first

1. [`docs/codex/00_do_not_break.md`](../00_do_not_break.md) — sections 2, 4, 5.
2. `packages/duecare-llm-chat/src/duecare/chat/templates.py` — `gemma_fill_template`, `bundle_excerpt_for_template`, `TEMPLATES_REGISTRY`, `TemplateSpec`, the route registrar around `POST /api/templates/fill` (~line 4496).
3. `packages/duecare-llm-chat/src/duecare/chat/static/templates.html` — `tplGenerateDraft` (~line 426), `_tplActive`, the template gallery, the `.tpl-field` class system.
4. `packages/duecare-llm-chat/tests/test_runtime_extracts.py` — find the existing `gemma_fill_template` tests (~line 640) for the test scaffolding pattern.

## 6. Files to modify

| Path | What changes |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/templates.py` | Add new `POST /api/templates/fill-batch` route + a `gemma_fill_batch(templates, bundle, manual_fields_by_id, gemma_call)` helper that shares the excerpt |
| `packages/duecare-llm-chat/src/duecare/chat/static/templates.html` | Add "Fill all relevant" button + `tplGenerateBatchDraft()` async function + accordion renderer |

## 7. Files to create

| Path | Purpose |
|---|---|
| `packages/duecare-llm-chat/tests/test_templates_batch_fill.py` | New `TestFillBatch` class: shared excerpt, per-template provenance, indicator overlap selection |

## 8. Acceptance criteria

1. `POST /api/templates/fill-batch` accepts `{bundle, template_ids, manual_fields, use_gemma}` and returns the spec'd shape.
2. `bundle_excerpt_for_template(bundle)` is computed exactly once per batch (verify via call recording in test).
3. Each draft in the response has its own `provenance`, `used_gemma`, `noise_scrubbed_before_gemma` fields — independent of the others.
4. Unknown `template_id` in the request returns 404 with `{available: [...]}` — same shape as the existing `/api/templates/fill`.
5. Templates.html "Fill all relevant" button:
   - Is disabled when no bundle is attached or `bundle.intelligence.ilo_indicators` is empty.
   - On click, selects templates with overlapping `relevance_indicators` and POSTs to fill-batch.
   - Shows a stacked accordion (`<details>`) per template, with the same `.tpl-field.prov-*` color highlights as single-template fill.
6. Activity log reports `tplLog.net('POST /api/templates/fill-batch', 'N templates')` on start and `tplLog.ok('Batch fill complete (Xms)', 'N filled, M used_gemma')` on completion.
7. Top-bar Gemma tally bumps once per template that actually used Gemma (`window.dcGemmaStats.bump('template_fill')`).
8. The existing single-template Generate button still works unchanged.
9. New `tests/test_templates_batch_fill.py` has at least 4 tests:
   - `test_shared_excerpt_computed_once` — patches `bundle_excerpt_for_template`, verifies one call for N templates
   - `test_per_template_provenance_independent`
   - `test_indicator_overlap_selection_in_helper`
   - `test_unknown_template_id_returns_404`

## 9. Do-not-break checklist

- **Section 2**: `POST /api/templates/fill` request + response unchanged. The new fill-batch is additive.
- **Section 5**: Don't rename `_tplLog` or `tplLog()` wrapper.
- **Section 4**: Don't change existing `.tpl-field`, `.tpl-field.prov-*`, `.tpl-gallery` CSS classes.
- **Section 8**: Don't add new entries to `STANDARD_FACT_INDICATORS`; if templates have `relevance_indicators` that aren't yet canonical, surface them in Goal 7's audit instead of mass-adding here.
- **Section 9**: `gemma_fill_template` itself is unchanged — the batch helper calls it once per template.
- The existing `tests/test_runtime_extracts.py::TestGemmaFillTemplate` tests must still pass unchanged.

## 10. Verification commands

```bash
python -c "import ast, pathlib; ast.parse(pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/templates.py').read_text(encoding='utf-8')); print('PASS AST')"

python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/templates.py').read_text(encoding='utf-8'); assert '/api/templates/fill-batch' in t and ('gemma_fill_batch' in t or 'fill_batch' in t); print('PASS server')"

python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/templates.html').read_text(encoding='utf-8'); assert 'Fill all relevant' in t and '/api/templates/fill-batch' in t; print('PASS UI')"

python -m pytest packages/duecare-llm-chat/tests/test_templates_batch_fill.py packages/duecare-llm-chat/tests/test_runtime_extracts.py -v
```

## 11. The Codex prompt

```
Read docs/codex/00_do_not_break.md sections 2, 4, 5, then read:
  - packages/duecare-llm-chat/src/duecare/chat/templates.py for
    gemma_fill_template, bundle_excerpt_for_template, TEMPLATES_REGISTRY,
    TemplateSpec, and the existing POST /api/templates/fill route (~line 4496)
  - packages/duecare-llm-chat/src/duecare/chat/static/templates.html for
    tplGenerateDraft (~line 426) and the gallery layout
  - packages/duecare-llm-chat/tests/test_runtime_extracts.py for the
    existing gemma_fill_template test pattern (~line 640)

Add a new endpoint POST /api/templates/fill-batch that accepts
{bundle, template_ids, manual_fields: {template_id: {...}}, use_gemma}.
Internally: compute bundle_excerpt_for_template(bundle) ONCE, then call
gemma_fill_template once per requested template, reusing the excerpt.
Return {drafts: [{template_id, rendered, field_values, provenance,
used_gemma, noise_scrubbed_before_gemma}], shared_excerpt_chars}.

Update templates.html: add a "Fill all relevant" button that:
  - Is disabled if no bundle attached or bundle has no ilo_indicators
  - On click, selects templates whose relevance_indicators overlap with
    bundle.intelligence.ilo_indicators
  - POSTs to /api/templates/fill-batch
  - Renders the result as a stacked accordion (<details>), one per
    template, with the same .tpl-field.prov-* color highlights as
    single-template fill

Use _tplLog for activity log. Bump window.dcGemmaStats.bump('template_fill')
once per template that used Gemma.

DO NOT:
  - change the existing /api/templates/fill request or response
  - rename _tplLog or break the existing tplGenerateDraft path
  - add new entries to STANDARD_FACT_INDICATORS
  - mass-promote relevance_indicators that aren't canonical (defer to Goal 7)

Create packages/duecare-llm-chat/tests/test_templates_batch_fill.py with
TestFillBatch covering: test_shared_excerpt_computed_once,
test_per_template_provenance_independent,
test_indicator_overlap_selection_in_helper,
test_unknown_template_id_returns_404.

Acceptance criteria are in docs/codex/goal_02_multi_template_fill/handoff.md section 8.
```

## 12. Out of scope

- Re-ordering templates by relevance score (just overlap presence is enough for this goal).
- New templates. Use whatever's in `TEMPLATES_REGISTRY` today.
- A "Polish all" extension for batch fills (separate follow-up).
- Changing the bundle excerpt schema. The excerpt is reused as-is.
- Cross-template field deduplication.
