# Anonymization & Sharing harness

PII redaction + audited submission to the public hub.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/anonymize` | batch redact PII in a list of texts; optional Gemma review of already-redacted output |
| POST | `/api/submit/knowledge` | audit + HTTPS POST to the hub |
| POST | `/api/submit/local` | deprecated alias for `/api/submit/knowledge` |

## Files

- `handler.py` -- the three endpoints + audit log writer + network helper
- `detector.py` -- 5 PII regex patterns (EMAIL/PHONE/AMOUNT/ID/PERSON)
- `redactor.py` -- salted-hash placeholder builder + raw_sha256 helper

## Privacy review model

This harness is the **safety gate**. The deterministic regex pass is
mandatory and auditable -- you can prove exactly what was redacted,
what sha256 the raw value hashed to, and what placeholder replaced it.

When `gemma_review=true`, a loaded Gemma 4 model runs as a redundant
second-stage reviewer AFTER regex redaction. The prompt instructs the
model not to quote any suspected remaining personal data; it returns
categories, severities, and review guidance only. If no model is
loaded, the endpoint reports `status=no_model` and the deterministic
redaction result is still returned.

## Audit log

`/kaggle/working/audit/submit_log.jsonl` (fallback: `./.duecare-audit/submit_log.jsonl`).
No PII; sha256 only.
