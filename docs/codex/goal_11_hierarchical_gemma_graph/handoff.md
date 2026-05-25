# Goal 11 - Hierarchical Gemma graph passes for Bulk File Review

> Status: **DONE 2026-05-25 (`32f35a7`)**. Implemented a budgeted hierarchical Gemma graph pass for Bulk File Review with deterministic fallback, provenance-preserving model nodes/edges, rollup edges, UI visibility, and source gates.

## 1. Goal

Make Bulk File Review run explicit Gemma node/edge passes at every useful hierarchy level: bundle/root, folder, document, page, paragraph/chunk, table row, extracted image/media item, person, case, and cross-case pattern rollup.

## 2. Why it matters

The current activity log can look like Gemma is doing detailed document analysis, but the visible `gemma_case_brief` phase is mostly bundle-level synthesis. Deterministic parsing already produces row/page/chunk-grounded facts, and the bounded graph-edge pass can add model-proposed edges, but the product story should be stronger: Gemma should create specific evidence-level nodes and edges first, then generalized hierarchical rollups second. A single bundle-level brief must never count as the hierarchical graph pass.

## 3. Current state

- `_parse_upload()` and `_chunk_text_rows()` create file/page/chunk rows with `parent_doc`, `page_index`, `chunk_index`, `processing_level`, folder metadata, and media placeholders.
- `_build_intelligence()` creates deterministic `typed_edges` with `row_id`, `parent_doc`, `page`, `chunk_id`, quote evidence, folders, people, payments, journey stages, and risk signals.
- `_gemma_case_brief()` sends a compact bundle summary to Gemma and asks for high-level JSON fields (`case_theory`, `priority_people`, `risk_clusters`, etc.).
- `_gemma_edge_pass()` proposes extra graph edges from bounded seed context, but it is not an exhaustive per-document/per-page/per-chunk tree pass.
- `PAGE_ITEM_PROMPT_TREE` documents the intended hierarchy, but the current job logs do not clearly prove that every selected page item ran through that tree.

## 4. Target state

- Bulk File Review has a visible, budgeted "Hierarchical Gemma graph pass" separate from the bundle brief.
- The pass schedules work items by hierarchy level:
  - bundle/root context
  - folder and path context
  - document-level summary and document type
  - page-level or sheet-level facts
  - paragraph/chunk/table-row evidence
  - extracted image/media item context, with a clear split between contextual prediction and real OCR/vision evidence
  - person/case rollups
  - cross-case pattern rollups
- Each Gemma item pass returns normalized nodes and edges with local-only provenance: `level`, `source_path`, `parent_doc`, `page`, `chunk_id`, `row_id`, `quote`, `edge_type`, `source_node`, `target_node`, `confidence`, `review_status`, and `extractors`.
- Rollups are derived from lower-level edges instead of replacing them.
- Activity logs name the level being analyzed and show counts, for example: `gemma_item_pass page 4/22`, `gemma_rollup folder 2/5`, `merged 68 model edges with 214 deterministic edges`.

## 5. Files to read first

1. [`../00_do_not_break.md`](../00_do_not_break.md) - main kernel and public-surface invariants.
2. [`../00_kernel_compatibility_gate.md`](../00_kernel_compatibility_gate.md) - required main-kernel gate.
3. `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py` - `_parse_upload`, `_chunk_text_rows`, `_build_intelligence`, `_gemma_case_brief`, `_gemma_edge_pass`, process job progress, graph-extract routes.
4. `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/prompts.py` - `PAGE_ITEM_PROMPT_TREE`, `GRAPH_EDGE_PROMPT_TEMPLATES`, `build_graph_edge_extraction_prompt`.
5. `packages/duecare-llm-chat/src/duecare/chat/static/process.html` - activity log text, process settings UI, graph edge review UI.
6. `packages/duecare-llm-chat/tests/test_process_bulk_review.py` - existing process contract tests.

## 6. Files to modify

| Path | What changes |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py` | Add a budgeted hierarchical Gemma item-pass scheduler, normalization/merge helpers, rollup generation, progress events, and response fields. |
| `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/prompts.py` | Add prompt builders for item-level and rollup-level graph extraction using `PAGE_ITEM_PROMPT_TREE`. |
| `packages/duecare-llm-chat/src/duecare/chat/static/process.html` | Show level-specific progress, counts, and reviewable model edges without implying the bundle brief is per-item analysis. |
| `packages/duecare-llm-chat/tests/test_process_bulk_review.py` | Add tests for hierarchy-level planning, provenance fields, budget caps, deterministic fallback, and response shape. |

## 7. Files to create

None required. If the scheduler grows too large, create a focused process submodule under `harnesses/process/` and import it from `handler.py`.

## 8. Acceptance criteria

1. The process response includes a `hierarchical_gemma_graph` object with `status`, `levels_attempted`, `n_items_considered`, `n_items_processed`, `n_model_nodes`, `n_model_edges`, `n_rollup_edges`, `budget`, and `errors`.
2. Model-created nodes/edges preserve source hierarchy fields: `level`, `source_path`, `parent_doc`, `page`, `chunk_id`, `row_id`, and evidence `quote` when available.
3. When matching material exists and budget permits, `levels_attempted` includes bundle/root, folder, document, page, paragraph/chunk, table row, extracted image/media item, person/case rollup, and cross-case rollup. Budget-capped or unavailable levels are reported in `levels_skipped` with a reason; they are not silently collapsed into `gemma_case_brief`.
4. The existing deterministic graph path still runs first and remains the fallback when no model is loaded or budget is zero.
5. Logs distinguish `gemma_case_brief` from per-item graph extraction. The UI must not imply that the brief did document, page, paragraph, table-row, image, or folder analysis.
6. The pass respects `max_gemma_calls`, `runtime_budget_minutes`, `gemma_calls_per_item`, and row caps. It must not run unbounded calls on Kaggle.
7. The four active/optional root Kaggle `kernel.py` files and the Kaggle root layout remain green under `python scripts/validate_main_kaggle_kernels.py`.
8. Public docs and CLAUDE/AGENTS context clearly describe the hierarchy-level behavior once implemented.

## 9. Do-not-break checklist

- Do not remove or weaken deterministic extraction, typed edges, graph chat, sample bundles, or existing `/api/process/*` routes.
- Do not send raw private case material to remote APIs. All Gemma passes remain local/in-kernel unless an existing cloud model route was explicitly selected by the operator.
- Do not invent evidence. Every model edge must be tied to row/page/chunk/media/folder context or marked as a rollup with source edge IDs.
- Keep media/vision honest: if pixels/OCR were not actually read, mark edges as contextual predictions needing image/OCR confirmation.
- Do not change the main kernel boot tokens or Kaggle metadata.

## 10. Verification commands

```bash
python -m pytest packages/duecare-llm-chat/tests/test_process_bulk_review.py -q
python scripts/validate_main_kaggle_kernels.py
```

If local pytest is broken by the known Pygments environment issue, record the exact import failure and run pure-stdlib static checks over the modified modules plus the main-kernel gate.

## 11. The Codex prompt

```
Read docs/codex/00_do_not_break.md, docs/codex/00_kernel_compatibility_gate.md,
packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py,
packages/duecare-llm-chat/src/duecare/chat/harnesses/process/prompts.py,
packages/duecare-llm-chat/src/duecare/chat/static/process.html, and
packages/duecare-llm-chat/tests/test_process_bulk_review.py.

Implement a budgeted hierarchical Gemma graph pass for Bulk File Review.
The current gemma_case_brief is bundle-level synthesis; keep it, but add a
separate item/rollup pass that creates reviewable nodes and edges at folder,
document, page, paragraph/chunk, table row, extracted image/media item,
person/case, and cross-case pattern
levels. Every model-created node/edge must preserve local-only provenance:
level, source_path, parent_doc, page, chunk_id, row_id, quote, confidence,
review_status, and source edge IDs for rollups. Deterministic extraction must
run first and remain the fallback. A bundle-level case brief is useful, but it
does not satisfy this goal by itself.

Update process.html activity logs so reviewers can see which hierarchy level
Gemma is analyzing. Do not imply the bundle brief is per-document or
per-paragraph analysis. Respect Kaggle budgets and run the main-kernel gate.
```

## 12. Out of scope

- Full OCR/layout engine implementation.
- Training or fine-tuning a graph-edge adapter.
- Remote batch processing outside the current local/Kaggle workbench.
- Replacing deterministic extraction with model-only extraction.
