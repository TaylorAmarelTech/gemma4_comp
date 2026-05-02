# Multimodal Graph POC Component Plan

> Created 2026-04-25. Captures the slate of standalone Kaggle-cell POCs that
> augment `raw_python/gemma4_multimodal_with_rag_grep_v1.py` (the working
> baseline) with better parsing, multilingual entity recognition, alternate
> graph backends, and richer edge construction. Each POC is a single-cell
> paste-into-Kaggle script that proves one capability against the same shared
> test corpus before any integration commitment is made.

---

## 1. Goal

Prove individual augmentation components work with Gemma 4 on real
trafficking case files (Philippine SEC GIS filings, Kenya/HK migration
case bundles, multilingual contracts, OCR'd hotline posters) **before**
deciding what to merge back into the main pipeline. Each POC ships a
single standalone artifact comparable to the baseline so the swap-vs-keep
decision is data-driven, not speculative.

This is a 24-day-to-deadline plan: every POC must be runnable as a single
Kaggle cell, must produce a shippable output (JSON / PNG / HTML) inside one
GPU session, and must be license-compatible with DueCare's MIT release
(Apache-2.0 OK; GPL-3.0 / AGPL-3.0 only allowed as runtime subprocesses
behind a process boundary, never `import`ed).

## 2. Baseline (what the current POC already does)

`raw_python/gemma4_multimodal_with_rag_grep_v1.py` — 9,368-line single-cell
script.

- Multimodal Gemma 4 E4B classifier (`Gemma4MultimodalBackend`, 4-bit auto-fallback for T4)
- pypdfium2 PDF→page-image rendering (~15-20 s per ~15-page PDF — current bottleneck)
- pytesseract OCR triage with multilingual langdata (Arabic / Persian / Urdu / Hindi / Bengali / Nepali / Indonesian / Tagalog / Russian / Simplified Chinese)
- `classical_extract_entities()` regex-based entity recognition (person/org, phone, email, financial_account, address, id_number, amount)
- 186-passage RAG knowledge base (sentence-transformers/all-MiniLM-L6-v2)
- Grep-based regex retrieval merged with RAG hits (`_merge_retrieval_hits`)
- Native Gemma 4 function-calling backend (5 compliance tools)
- Google Drive walker (gdown 6.x + API key + HTML scrape fallbacks + curated 442-entry embedded list)
- `build_entity_graph()` co-occurrence graph with synthetic `case_bundle` hub nodes
- Rendering: networkx + matplotlib PNG, vis-network self-contained HTML, GraphML for Gephi, CSV exports
- Community detection (`greedy_modularity_communities`) + degree/betweenness centrality
- Hypothesis-edge verification by Gemma (text-only LLM-as-judge)
- Per-bundle case briefs by Gemma (currently broken: `NameError: name 'backend' is not defined` at line 9320 — caught silently, briefs come out empty)
- GraphML / CSV / `case_briefs.md` exports

### Known weak spots the POCs target
1. **Parsing throughput.** pypdfium2 dominates Stage 1 wall-clock and is layout-blind.
2. **Entity recognition.** `classical_extract_entities()` is regex; misses non-Latin scripts entirely and produces noisy person/org candidates.
3. **Edge construction.** Co-occurrence + Gemma verification works, but linguistic edges ("X recruited Y", "Z deposited to account A") are not extracted.
4. **Graph rendering.** matplotlib PNG and vis-network HTML are functional; not video-cinematic.
5. **Comparability.** No second backend to validate the graph against.

## 3. Component slate

| # | POC | License | Replaces / augments | Cost (LOC) | Rubric value |
|---|---|---|---|---|---|
| P1 | Docling vision parser | MIT | pypdfium2 + part of OCR | ~150 | Tech depth (faster, layout-aware) |
| P2 | Multilingual NER (GLiNER / stanza) | MIT / Apache | `classical_extract_entities` | ~120 | Impact (handles non-Latin scripts in real docs) |
| P3 | Grep-edge linguistic relation extraction | n/a (custom) | adds to `build_entity_graph` | ~200 | Tech depth (richer graph, better Gemma input) |
| P4 | RAG-Anything end-to-end | MIT | side-by-side comparison | ~100 | Tech depth (defensibility) |
| P5 | neo4j-labs/llm-graph-builder + Bloom | Apache-2.0 | rendering only | ~80 | Video pitch (cinematic graph shot) |
| P6 | Gemma case-brief fix + community labeling | n/a (bug + ~30 LOC) | repairs Stage 8b in baseline | ~30 | Video pitch (named clusters in demo) |

## 4. Shared test corpus

Every POC reads the same input set so outputs are directly comparable.

- **Source folder.** `data/multimodal_test_set/` (off-Kaggle) or `/kaggle/working/duecare-multimodal-test-set/` (on Kaggle), staged by the baseline's Stage 1 fetcher.
- **Locked subset for POCs.** A 25-document subset covering the four hard cases:
  - Philippine SEC GIS filings (KingABC, Fast Coin, Omanfil, FJ-Mhark) — English, dense table layouts
  - Kenya/HK Lois case bundle — English contracts + scanned affidavits
  - NPC complaint scans — English, multi-page, low-quality scans
  - One Tagalog hotline poster + one Arabic recruitment contract (for P2 multilingual NER)
- **Locked file.** `data/poc_corpus_manifest.json` — list of (path, sha256, doc_type, expected_language) — written once by the first POC, reused by all others.

## 5. Shared output schema

Every POC that produces entities or edges writes to a normalized JSON shape
so graphs from different backends can be diffed and merged.

```jsonc
{
  "poc_id": "P1_docling | P2_multiling_ner | P3_grep_edges | P4_rag_anything | P5_neo4j",
  "run_id": "ISO8601 timestamp",
  "source_corpus_sha": "sha256 of poc_corpus_manifest.json",
  "documents": [
    {
      "doc_id": "relative path",
      "page_count": 0,
      "language": "iso639-1 or 'mixed'",
      "blocks": [{"type": "text|table|figure|heading", "bbox": [x1,y1,x2,y2], "text": "..."}],
      "entities": [
        {"type": "person_or_org", "value": "...", "raw": "...",
         "language": "...", "page": 0, "bbox": [...], "confidence": 0.0,
         "source": "regex|ner|gemma|docling"}
      ]
    }
  ],
  "edges": [
    {"a": ["type", "value"], "b": ["type", "value"],
     "relation": "co_occurred_in_doc | recruited | paid | owns | located_at | ...",
     "evidence_doc_ids": ["..."],
     "evidence_text_excerpt": "...",
     "source": "co_occur|grep_pattern|gemma_verified|llm_extracted",
     "confidence": 0.0}
  ]
}
```

This schema is a strict superset of what `build_entity_graph()` consumes, so
any POC's output can feed back into the baseline's existing rendering /
community / centrality / export code without modification.

## 6. POC details

### P1 — Docling vision parser

**Goal.** Replace pypdfium2 with `docling.document_converter.DocumentConverter`
on the locked corpus and measure (a) wall-clock parse time, (b) text recall
vs. the baseline OCR pass, (c) layout structure recovery (tables, headings,
figure regions).

**Inputs.** `data/poc_corpus_manifest.json`.
**Outputs.** `poc_outputs/P1_docling/{doc_id}.json` per document in the
shared schema (blocks populated, entities empty), plus a single
`P1_docling_summary.json` with timings.

**Why first.** Smallest scope, no Gemma needed (Gemma classifies the
parsed output downstream), removes the visible bottleneck in the live
baseline run, and produces the layout-aware input that P2 / P3 / P4
all benefit from.

**Acceptance.** Per-PDF wall-clock <50% of pypdfium2 baseline; tables in
the Philippine GIS filings round-trip as `{"type":"table"}` blocks with
recoverable cell text.

### P2 — Multilingual NER

**Goal.** Recognize person / org / location / date / money entities in
Tagalog, Arabic, Hindi, Bengali, Nepali, Indonesian, Russian, and
Simplified Chinese — the languages tesseract is already provisioned for
in the baseline.

**Tool candidates** (all MIT / Apache):
- `urchade/GLiNER` — multilingual zero-shot NER, accepts custom entity types at inference, ~200 MB
- `stanfordnlp/stanza` — pretrained NER for ~70 languages, slower but more accurate on Hindi/Bengali
- `flair` (zalandoresearch) — multilingual NER, larger
- spaCy `xx_ent_wiki_sm` — fast baseline, English-Wikipedia-trained, weaker on non-Latin

**Inputs.** P1 output (`blocks` populated).
**Outputs.** `poc_outputs/P2_multiling_ner/{doc_id}.json` with `entities`
populated, language-tagged.

**Why second.** P3 (grep-edge linguistic patterns) and P4 (RAG-Anything)
both want a richer, multilingual entity list as input. Without P2 the
graph remains regex-quality and silently drops non-English documents.

**Acceptance.** ≥80% F1 on a hand-labeled 50-entity gold set drawn from the
Tagalog poster + Arabic contract + 3 GIS filings; entities tagged with
correct ISO 639-1 language code; runs CPU-only in <2 min for the 25-doc
corpus.

### P3 — Grep-edge linguistic relation extraction

**Goal.** Extend the baseline's grep retrieval into edge construction:
when a regex pattern matches a sentence containing two known entities,
emit a typed edge between them.

**Patterns** (illustrative — full list in the script):
- `(\w+)\s+(?:recruited|hired|deployed)\s+(\w+)` → `recruited`
- `(\w+)\s+paid\s+(?:USD|PHP|HKD|\$)\s*([\d,]+)` → `paid_amount`
- `account(?:\s+number)?\s*[:#]?\s*([\d\-]+)` near a person/org → `owns_account`
- `(?:branch|office)\s+(?:at|in)\s+([A-Z][\w\s]+)` near an org → `located_at`

**Inputs.** P2 output (`entities` populated).
**Outputs.** `poc_outputs/P3_grep_edges/{doc_id}.json` with `edges`
populated; `source: "grep_pattern"`.

**Why third.** Cheap, deterministic, and produces typed edges that the
baseline's hypothesis-verification step (`verify_hypothesis_edges_with_gemma`)
can promote to confirmed edges with confidence scores. Closes the loop
between regex retrieval (already in baseline) and edge construction
(currently absent).

**Acceptance.** Recovers ≥30 typed edges from the 25-doc corpus; ≥70%
precision when spot-checked against the original sentence excerpts.

### P4 — RAG-Anything end-to-end

**Goal.** Run HKUDS/RAG-Anything (MIT, multimodal-aware via MinerU, Gemma
via Ollama) on the same corpus end-to-end and emit its entity graph in
the shared schema.

**Inputs.** Same locked corpus folder (RAG-Anything walks it directly).
**Outputs.** `poc_outputs/P4_rag_anything/graph.json` in shared schema,
plus `P4_rag_anything_native.json` in RAG-Anything's native format for
side-by-side diffing.

**Why fourth.** Defensibility for the writeup ("we evaluated the leading
multimodal KG framework on identical input"). Not a swap candidate —
strictly comparison material. Run with `LLM_BINDING=ollama
LLM_MODEL=gemma4:e4b` so Gemma 4 stays in the loop.

**Acceptance.** Produces a non-empty graph; entity overlap with baseline
output measurable (Jaccard score logged in summary); writeup gains a
"DueCare vs RAG-Anything" comparison table.

### P5 — Neo4j + llm-graph-builder + Bloom render

**Goal.** Spin up Neo4j locally, point neo4j-labs/llm-graph-builder at the
same corpus with Gemma 4 via Ollama, capture a 10-second Bloom
visualization clip for the 3-minute video.

**Inputs.** Same corpus folder.
**Outputs.** `poc_outputs/P5_neo4j/cypher_dump.cypher` +
`P5_neo4j_bloom_screenshot.png` (manual export from Bloom).

**Why fifth.** Pure video-asset play. Not part of DueCare's deployable
stack. Bloom looks dramatically better than matplotlib/vis-network for
the 10-second graph reveal in the video.

**Acceptance.** Renders ≥50 entities with community coloring; one
publishable screenshot ready for the video editor.

### P6 — Baseline repairs (Stage 8b case-brief fix + community labeling)

**Goal.** Two ~30-LOC fixes inside `gemma4_multimodal_with_rag_grep_v1.py`:

1. **Case-brief NameError fix.** `run(cfg)` constructs `backend` locally and
   unloads it at line 6852 before returning only `rows`. `main()` then
   references `backend` at lines 9270 and 9320 → `NameError`. Change
   `run(cfg)` to return `(rows, backend)` and have `main()` unload after
   Stage 8 completes. Verify Stage 8b actually generates briefs.
2. **Gemma community labeling.** After `detect_communities_and_centrality`
   populates community IDs, pass each community's top entities to Gemma
   via the existing `backend.text_only(...)` and ask for a one-line label
   ("Cluster 3: Hong Kong agency network sharing 3 phone numbers"). Save
   labels into `graph["community_labels"]` and surface them in
   `render_entity_graph_html` legend.

**Inputs.** Existing baseline run output.
**Outputs.** Patched `gemma4_multimodal_with_rag_grep_v1.py` + a
demonstration run with non-empty `case_briefs.json` and labeled
communities in `entity_graph.html`.

**Why last in the slate but actually do first.** Tiny, fixes a known bug,
makes the existing demo dramatically better in the video — but not a
"new POC component" so it sits separately in this plan. Should ship
ahead of P1-P5 as housekeeping.

## 7. Order and dependencies

```
P6 (housekeeping fix)        - do today, ~1 hr
        │
P1 (Docling parser)          - day 1-2, blocks nothing else but feeds P2/P3/P4
        │
P2 (multilingual NER)        - day 3-4, depends on P1 output shape
        │
P3 (grep-edge extraction)    - day 5-6, depends on P2 entities
        │
P4 (RAG-Anything compare)    - day 7-8, runs in parallel; uses raw corpus
        │
P5 (neo4j + Bloom)           - day 9-10, just-in-time before video shoot
```

P4 has no dependency on P1-P3 (it ingests raw documents itself); it can
run in parallel on a second Kaggle session.

## 8. License constraints

| License | Status | Examples |
|---|---|---|
| MIT | Vendor freely | Docling, RAG-Anything, LightRAG, alephdata/aleph (core) |
| Apache-2.0 | Vendor freely | neo4j-labs/llm-graph-builder, GLiNER, stanza |
| BSD | Vendor freely | spaCy |
| LGPL-3.0 | Subprocess only | (none planned) |
| GPL-3.0 | Subprocess only, never `import` | marker, surya |
| AGPL-3.0 | Subprocess only behind a process boundary; flag in writeup | MinerU (when called by RAG-Anything), ICIJ/datashare, alephdata/ingest-file |
| Custom / unclear | Skip | — |

DueCare ships under MIT (per `.claude/rules/50_publish_strategy.md` and
the hackathon requirements). Anything copyleft must stay outside the
distributed wheels — used only as a runtime tool the operator invokes
themselves.

## 9. Output directory layout

```
poc_outputs/
├── _shared/
│   ├── poc_corpus_manifest.json      # locked 25-doc list with sha256
│   └── README.md                     # how to regenerate the corpus
├── P1_docling/
│   ├── {doc_id}.json                 # one per document, shared schema
│   └── P1_docling_summary.json       # timings + acceptance metrics
├── P2_multiling_ner/
├── P3_grep_edges/
├── P4_rag_anything/
│   ├── graph.json                    # shared schema
│   └── graph_native.json             # RAG-Anything's native format
├── P5_neo4j/
│   ├── cypher_dump.cypher
│   └── bloom_screenshot.png
└── P6_baseline_fix/
    └── demo_run/                     # rerun of baseline with fix applied
```

## 10. Out of scope for this plan

- Refactoring the baseline into the `duecare-llm-*` package layout. POCs stay in `raw_python/` next to the existing baseline; integration into packages is a separate decision after POC results land.
- Replacing the existing pipeline wholesale. Every POC is comparison material until the data says swap.
- Building a unified runner that orchestrates all POCs together. Each is its own paste-into-Kaggle cell.
- LiteRT mobile export, GGUF export, fine-tuning, or anything in the Phase 3 spine — those live in NB 525/527/530 and are tracked in `docs/CHECKPOINT_2026-04-19.md`.

## 11. One-line summary

> Six standalone Kaggle-cell POCs (Docling, multilingual NER, grep-edges, RAG-Anything, Neo4j+Bloom, baseline-fix) on a locked 25-document corpus with a shared JSON schema, all license-clean for MIT redistribution, all Gemma-4-augmentable. Order: P6 housekeeping → P1 parsing → P2 NER → P3 edges → P4/P5 in parallel.
