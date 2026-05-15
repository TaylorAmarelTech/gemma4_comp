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
7. `Gemma 4 edge pass`: ask the local text model to propose additional typed
   edges from bounded OCR/text context; when a local multimodal Gemma 4 model is
   loaded, use page image + OCR + metadata to propose vision-grounded edges.
8. `merge`: entity resolution, duplicate-edge merging, confidence scoring,
   conflict checks, and reviewer queue.

The runnable demo does not call cloud APIs. Frontier/cloud models could improve
OCR or visual QA in a separate deployment, but the submitted workbench keeps raw
case material inside the local kernel.

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
