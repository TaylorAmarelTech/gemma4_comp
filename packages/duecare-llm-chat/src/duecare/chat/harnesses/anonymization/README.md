# Anonymization & Sharing harness

PII redaction + audited submission to the public hub.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/anonymize` | batch redact PII in a list of texts |
| POST | `/api/submit/knowledge` | audit + HTTPS POST to the hub |
| POST | `/api/submit/local` | deprecated alias for `/api/submit/knowledge` |

## Files

- `handler.py` -- the three endpoints + audit log writer + network helper
- `detector.py` -- 5 PII regex patterns (EMAIL/PHONE/AMOUNT/ID/PERSON)
- `redactor.py` -- salted-hash placeholder builder + raw_sha256 helper

## Audit log

`/kaggle/working/audit/submit_log.jsonl` (fallback: `./.duecare-audit/submit_log.jsonl`).
No PII; sha256 only.
