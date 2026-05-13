# Process Files harness

Bulk ingest of a case bundle + Gemma 4 graph-chat over it.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/process/batch` | multipart upload -> v1.0 bundle envelope |
| POST | `/api/process/graph-chat` | ask Gemma 4 about the last uploaded bundle |

## Files

- `handler.py` -- the two endpoints
- `extractor.py` -- 5 entity regex patterns
- `prompts.py` -- graph-chat system prompt + bundle context builder
