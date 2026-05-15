# Bulk File Review harness

Bulk ingest of a case bundle plus Gemma 4 graph-chat over it.

The handler supports ZIP, CSV, JSONL, text, RTF/HTML/email, DOCX, simple XLSX,
images, and PDFs. Text-like files, DOCX, simple XLSX, and extractable PDF pages
are chunked locally. Scanned PDFs, legacy Office binaries, and images are
surfaced as explicit OCR and Gemma 4 vision work items so reviewers can see
what remains queued before trusting the graph.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/process/batch` | multipart upload to v1.0 bundle envelope |
| POST | `/api/process/batch/start` | acknowledge upload, start background process job, return job ID |
| GET | `/api/process/batch/status/{job_id}` | poll server-side phases and retrieve result when complete |
| POST | `/api/process/graph-chat` | ask Gemma 4 about the last uploaded bundle |

## Files

- `handler.py`: the two endpoints, processing plan, journey points, and media queue
- `extractor.py`: 5 entity regex patterns
- `prompts.py`: graph-chat system prompt + bundle context builder
