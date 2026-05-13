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

## Why regex-only (no Gemma, no GREP, no RAG)

This harness is the **safety gate**. By design, no raw PII reaches a
language model from here. The deterministic regex pass is what makes
the gate auditable -- you can prove exactly what was redacted, what
sha256 the raw value hashed to, and what placeholder replaced it.

A future Gemma 4 NER pass could be wired as a *redundant second-stage
detector* that runs AFTER regex redaction (so it only sees already-
redacted text). That would catch entities the regex missed (e.g.,
names without titles). It would NOT run before redaction; that would
defeat the purpose of the gate.

## Audit log

`/kaggle/working/audit/submit_log.jsonl` (fallback: `./.duecare-audit/submit_log.jsonl`).
No PII; sha256 only.
