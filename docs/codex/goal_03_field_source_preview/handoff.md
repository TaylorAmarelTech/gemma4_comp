# Goal 3 — Field-source preview on templates.html

> Status: **DONE 2026-05-24** in commit `8294b5a`. Created 2026-05-24.

## 1. Goal

When a reviewer picks a template AND has a bundle attached, show which template fields will be auto-filled from the bundle vs. which will need Gemma vs. which will be missing — BEFORE they click Generate.

## 2. Why it matters

Today the field-provenance highlight (green=bundle, teal=Gemma, amber=manual, red=missing) only appears AFTER you click Generate and spend a Gemma call. A caseworker who wants to check "is this bundle ready for the POEA template?" has to actually fire the generate request to find out. That wastes Gemma cycles and reviewer time. The deterministic bundle-hint pass is fast (no model) — we can run it on template selection and show the user what's already covered.

## 3. Current state

- `gemma_fill_template()` runs three passes: bundle_hint → manual → Gemma gaps.
- `templates.html` calls `tplGenerateDraft()` which POSTs `/api/templates/fill`, which runs the full pipeline including Gemma.
- The provenance highlights (`.tpl-field.prov-bundle_hint` etc.) appear only after the generate response.

## 4. Target state

- New endpoint `POST /api/templates/dry-run-fill` that runs ONLY the bundle_hint pass (no Gemma) and returns `{field_sources: {field_id: "bundle_hint" | "missing"}, n_bundle_hits: int, n_missing: int, n_optional: int, n_required: int}`.
- Templates.html: when a template is picked AND a bundle is attached, fire the dry-run and color the field cards in advance (green for bundle_hint, gray for missing).
- A one-line banner above Generate: `"If you click Generate, Gemma will fill X of Y missing required fields."`.
- Banner + colors recompute on bundle change.
- Pure deterministic — no Gemma call.

## 5. Files to read first

1. [`docs/codex/00_do_not_break.md`](../00_do_not_break.md) — sections 2, 4, 5.
2. `packages/duecare-llm-chat/src/duecare/chat/templates.py` — `bundle_field_hint`, `TemplateSpec.fields`, the `gemma_fill_template` deterministic pass.
3. `packages/duecare-llm-chat/src/duecare/chat/static/templates.html` — `tplSelectTemplate`, `_tplBundle`, the `.tpl-field` CSS class system.

## 6. Files to modify

| Path | What changes |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/templates.py` | New `POST /api/templates/dry-run-fill` route + a `dry_run_fill_template(template, bundle)` helper |
| `packages/duecare-llm-chat/src/duecare/chat/static/templates.html` | Wire `tplDryRunPreview()` to fire on template select + bundle change |

## 7. Files to create

| Path | Purpose |
|---|---|
| `packages/duecare-llm-chat/tests/test_templates_dry_run.py` | Cover the dry-run helper: no Gemma call, correct bucket counts |

## 8. Acceptance criteria

1. `POST /api/templates/dry-run-fill` accepts `{template_id, bundle}` and returns the spec'd shape.
2. The dry-run path NEVER calls Gemma. Even if `app.state.gemma_call` is set, it must not be invoked.
3. `field_sources` covers every field in the template (no missing keys).
4. `n_bundle_hits + n_missing` equals the total field count.
5. `n_optional` and `n_required` are correct counts of `field.required` False / True.
6. Templates.html fires `tplDryRunPreview()`:
   - When a template card is clicked (after `_tplActive` is set).
   - When the bundle is changed (paste JSON, attach from process, etc.).
   - When the bundle is cleared (clear the colors, hide the banner).
7. The field cards get `.tpl-field.prov-bundle_hint` (green) or `.tpl-field.prov-missing` (gray) classes based on `field_sources`.
8. A banner above Generate shows: `"Gemma will fill X of Y missing required fields."`
9. Activity log: `tplLog.info('Dry-run preview', '<template_title>: bundle covers N of M fields')` on success.
10. NO regression to the existing post-Generate provenance — that still uses the actual fill response.

## 9. Do-not-break checklist

- **Section 2**: `POST /api/templates/fill` unchanged. New `dry-run-fill` is additive.
- **Section 4**: Don't rename `.tpl-field.prov-bundle_hint` or `.tpl-field.prov-missing` CSS classes; they're already wired into the existing post-Generate render.
- **Section 5**: Don't rename `_tplLog`.
- **Section 4**: Don't change `tplSelectTemplate` signature; just call the new `tplDryRunPreview()` from within it.
- Field cards' DOM IDs must keep the same naming.

## 10. Verification commands

```bash
python -c "import ast, pathlib; ast.parse(pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/templates.py').read_text(encoding='utf-8')); print('PASS AST')"

python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/templates.py').read_text(encoding='utf-8'); assert '/api/templates/dry-run-fill' in t and 'dry_run_fill_template' in t; print('PASS server')"

python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/templates.html').read_text(encoding='utf-8'); assert 'tplDryRunPreview' in t and '/api/templates/dry-run-fill' in t; print('PASS UI')"

python -m pytest packages/duecare-llm-chat/tests/test_templates_dry_run.py -v
```

## 11. The Codex prompt

```
Read docs/codex/00_do_not_break.md sections 2, 4, 5. Then read:
  - packages/duecare-llm-chat/src/duecare/chat/templates.py for
    bundle_field_hint and the deterministic pass in gemma_fill_template
  - packages/duecare-llm-chat/src/duecare/chat/static/templates.html for
    tplSelectTemplate, the .tpl-field class system, and where bundle JSON
    gets attached

Add an endpoint POST /api/templates/dry-run-fill that runs ONLY the
bundle_hint pass (no Gemma) and returns {field_sources: {field_id:
"bundle_hint" | "missing"}, n_bundle_hits, n_missing, n_optional,
n_required}. Implement via a new helper dry_run_fill_template(template,
bundle) so it's testable.

Update templates.html to fire tplDryRunPreview() when a template + bundle
are both selected and on bundle change. Color the field cards in
advance using the existing .tpl-field.prov-bundle_hint and
.tpl-field.prov-missing classes. Show a one-line banner above Generate:
"Gemma will fill X of Y missing required fields."

DO NOT:
  - call Gemma in the dry-run path (even if model is loaded)
  - rename .tpl-field.prov-* CSS classes
  - rename tplSelectTemplate or break tplGenerateDraft
  - change the existing /api/templates/fill endpoint

Create packages/duecare-llm-chat/tests/test_templates_dry_run.py with:
  - test_dry_run_does_not_call_gemma (set app.state.gemma_call to a stub
    that asserts not called)
  - test_bucket_counts_correct
  - test_unknown_template_id_returns_404

Acceptance criteria in docs/codex/goal_03_field_source_preview/handoff.md section 8.
```

## 12. Out of scope

- Reordering fields by priority. Display order stays the same.
- A "Run dry-run for all templates" extension (use the Goal 2 batch fill pattern).
- Saving the dry-run result. Each call is fresh.
- Showing which Gemma call would fill which field — Gemma fills the gaps in one shot.
