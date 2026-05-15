# Bulk File Review harness

Bulk ingest of a case bundle plus typed graph edges, local Gemma 4 edge
extraction, and graph-chat over the reviewed bundle.

The handler supports ZIP, CSV, JSONL, text, RTF/HTML/email, DOCX, simple XLSX,
images, and PDFs. Text-like files, DOCX, simple XLSX, and extractable PDF pages
are chunked locally. Scanned PDFs, legacy Office binaries, and images are
surfaced as explicit OCR and Gemma 4 vision work items so reviewers can see
what remains queued before trusting the graph.

## Local-Only Large-Bundle Design

The harness is designed to scale from one media-rich ZIP to thousands of
documents by treating every artifact as a resumable local work item:

1. `collection` / archive inventory: hash files, preserve paths, de-duplicate.
2. `document`: classify type and route to text extraction, PDF page split, or
   media queue.
3. `page`: preserve page number, text layer, OCR text, and layout metadata.
4. `page_region`: split pages into text blocks, tables, screenshots, receipts,
   signatures, stamps, images, and other detected page items.
5. `preprocess`: run local OCR/layout/ASR engines such as Tesseract, EasyOCR,
   PaddleOCR, Docling, Marker, MinerU, or Whisper-style local transcription
   when installed.
6. `deterministic edges`: emit typed edges for fees, entities, folders, dates,
   locations, journey stages, rule hits, and media work items.
7. `Gemma 4 prompt tree`: classify each document/page/page item first, then
   route into targeted prompts for receipts, chat screenshots, contracts,
   cross-document links, and knowledge-object candidates within the selected
   local runtime budget.
8. `merge`: entity resolution, duplicate-edge merging, confidence scoring,
   conflict checks, and reviewer queue.

The runnable demo does not call cloud APIs. Frontier/cloud models could improve
OCR or visual QA in a separate deployment, but the submitted workbench keeps raw
case material inside the local kernel.

## Default Review Modes

The UI defaults to `standard_review`; advanced controls are collapsed so most
users do not need to tune anything before uploading.

| Mode | Intended use | Default local budget |
|---|---|---|
| `quick_triage` | Thousands of files or years of history where the first goal is to find hot spots | 5 minutes, 20 Gemma calls, conservative edges |
| `standard_review` | Normal case-bundle review and demo path | 15 minutes, 75 Gemma calls, balanced edges |
| `exhaustive_review` | Smaller bundles or final case prep | 60 minutes, 240 Gemma calls, exploratory review queue |

The budget controls how many page items are sent to Gemma after deterministic
OCR/layout/entity extraction. Deterministic typed edges are always emitted first.
Gemma-proposed edges and knowledge candidates are marked `needs_review`.

## Page-Item Prompt Path

Every page item follows the same local-first route:

1. `page_item_classification`: classify the item and identify risk signals.
2. `receipt_payment_extraction`: run only for payment records, receipts,
   mobile-wallet screenshots, invoices, or amount-heavy pages.
3. `chat_screenshot_extraction`: run for chat exports, screenshots, emails, or
   message-like items with threats, deductions, fees, or passport language.
4. `contract_clause_extraction`: run for contracts, side letters, forms, and
   agreement clauses.
5. `cross_document_linking`: run when an agency, employer, phone, phrase,
   amount, folder, or route repeats across documents.
6. `rag_candidate_synthesis`: run when repeated, non-PII patterns are strong
   enough to become reviewable knowledge-object candidates.

Imported local KnowledgeObject envelopes are read as context for this prompt
tree when enabled. They support continuous improvement over time: a reviewer can
promote a pattern, import a knowledge file later, and the next Gemma edge/RAG
pass can use that reviewed object as local context without sending raw case data
outside the kernel.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/process/batch` | multipart upload to v1.0 bundle envelope |
| POST | `/api/process/batch/start` | acknowledge upload, start background process job, return job ID |
| GET | `/api/process/batch/status/{job_id}` | poll server-side phases and retrieve result when complete |
| POST | `/api/process/graph-extract` | local Gemma 4 typed-edge and RAG-candidate pass |
| POST | `/api/process/graph-chat` | ask Gemma 4 about the last uploaded bundle |

## Files

- `handler.py`: endpoints, queue contract, typed edge schema, journey points, and media queue
- `extractor.py`: 5 entity regex patterns
- `prompts.py`: graph-chat prompt, graph-edge prompt templates, and bundle context builder
