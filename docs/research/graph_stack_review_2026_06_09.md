# Graph stack review — 2026-06-09

A maximum-depth review of the DueCare graph stack (generation, storage,
interrogation, evaluation, augmentation, node/edge generation), with the
verified findings separated from the false positives. Reviewed surfaces:
`harnesses/process/handler.py` (case graph), `harnesses/process/prompts.py`
(edge-extraction prompts), `harness/__init__.py` + `_citations.json` (RAG
citation graph), `duecare-llm-research-tools/.../graph.py` (acquisition graph).

## The three graph systems

| System | Edge schema | Node id | Storage | Status |
|---|---|---|---|---|
| Case graph (process harness) | `duecare.process.typed_edge.v1` | `kind:slug` (`case:dc_ph_hk_101`) | `app.state.last_process_bundle` (in-memory) | live |
| RAG citation graph | `_citations.json` (`{from,to,relation,note}`) | doc id | module-load dicts | live |
| Acquisition graph (research-tools) | `mentions` / `co_mentions` | doc/entity | `reports/acquisition/` | live, offline |

The three are independent — no shared node-id format and no bridge. That is
acceptable today (different lifecycles, different consumers) but is the main
candidate if graph correlation across subsystems is ever needed.

## Verified findings

### Fixed this session

**Edge-pass vocabulary did not match what three other surfaces promise.**
The deterministic graph-chat (`_graph_chat_deterministic_answer`, handler.py
~2524) and the activity-log line (`edge_types_asked`, handler.py ~4003) both
told reviewers that `fee_camouflage_evidence`, `provider_choice_restriction`,
`affiliate_or_common_control_signal`, and `contract_clause_flag` edges "come
from the optional local Gemma edge pass." But the edge-pass prompt's
`allowed_edge_types` (prompts.py ~457) omitted all four, so Gemma could never
propose them — a "real, not faked" inconsistency between the advertised
upgrade path and the prompt. **Fixed**: those four edge types are now in the
prompt's allowed list, so the Gemma edge pass can emit exactly the explicit
edges the graph-chat layer already knows how to consume.

### False positives (claimed by the survey, refuted by the code)

- **"typed_edges are invisible to graph-chat."** Refuted. `_graph_chat_
  deterministic_answer` reads `intelligence["typed_edges"]` directly
  (handler.py:2473) and filters on `edge_type` extensively, including
  `provider_choice_restriction` and `fee_camouflage_evidence`. The survey
  conflated `_build_graph_view` (a deliberately compact, browser-renderable
  summary that uses `evidence_edges`) with the graph-chat context (the full
  bundle, including typed_edges). Both are correct as designed.
- **"No graph/edge quality dimensions exist."** Refuted. `prompts.py` defines
  `EDGE_QUALITY_DIMENSIONS` (source-grounding-per-edge, typed-relation-
  specificity, …) used in the edge-pass contract.
- **"`_build_graph_view` truncates at 220 edges with no warning."** Refuted.
  The view's `meta` carries `truncated_edges` (handler.py:1344); the data is
  present for the UI to surface.

## Tracked remaining improvements (not rushed into the 5,600-line file)

These are real but lower-urgency; recorded here rather than applied under time
pressure, because each needs its own test pass in a file this central.

1. **Rollup-edge visibility (S).** When the optional hierarchical Gemma pass
   runs, its `rollup_edges` live only in `hierarchical_gemma_graph.rollup_edges`
   and are not queryable by `_graph_chat_deterministic_answer` (which reads
   `typed_edges`). Merging rollup edges into `typed_edges` (tagged
   `extractor="hierarchical_rollup"`) would make the highest-abstraction graph
   output reachable from interrogation. Narrow: only affects runs where the
   hierarchical pass has executed.
2. **Confidence constants table (S, pure refactor).** ~12 confidence literals
   (0.50/0.68/0.70/0.72/0.74/0.76/0.78/0.82/0.86/0.92/0.98) are scattered
   across `_build_intelligence` and the media/OCR queue builders. A named
   `_CONFIDENCE` table near `_node_id`/`_edge_id` would make calibration
   legible and enable future tuning against harness-lift results. Zero
   behavior change.
3. **Dual edge vocabulary (M).** The main edge pass uses
   `charged_or_collected_fee`-style types; the hierarchical item pass uses
   `item_mentions_*`. A normalization map (`item_mentions_fee_or_debt` →
   `charged_or_collected_fee`, …) would let edges from the two passes be
   compared and aggregated.
4. **Graph-quality benchmark dimensions (M).** `EDGE_QUALITY_DIMENSIONS`
   exists for the edge-pass contract, but the 192-dim harness-lift rubric has
   no graph dimensions, so generated-graph accuracy is not measured in the
   benchmark loop. Adding a `graph_quality` group (correct typed edge from
   signal, grounded-not-invented quote, node id resolves) would close the
   feedback loop from harness-lift back to graph quality.
5. **Bundle persistence (M).** `app.state.last_process_bundle` is a single
   in-memory slot; a kernel restart loses the graph. The raw upload is staged
   to `/kaggle/working/process-staging/<run_id>/`, so persisting the computed
   bundle alongside it would survive restart for the laptop-deployment story.

## Storage + interrogation, as built

- **Generation**: parse → `_build_intelligence` produces `typed_edges`
  (full provenance: edge_id, source/target node, evidence.{file,page,chunk,
  quote}, confidence, review_status) AND `evidence_edges` (lighter, feeds the
  compact graph view). Both come from the same rule_hit / keyword_signal /
  folder_context detections.
- **Augmentation**: optional Gemma edge pass (`_gemma_edge_pass`) and
  hierarchical item pass add model edges; media/OCR work items are explicit
  (`media_requires_gemma_vision`), never pretending a file was read.
- **Interrogation**: `POST /api/process/graph-chat` →
  `_graph_chat_deterministic_answer` (keyword-routed, reads typed_edges) →
  optional Gemma synthesis on top → full Gemma fallback with GREP+RAG+Tools.
- **Promotion**: `POST /api/knowledge/from-edge` maps a typed edge to an
  `extracted_fact` envelope (the envelope contract from `knowledge_taxonomy`).
