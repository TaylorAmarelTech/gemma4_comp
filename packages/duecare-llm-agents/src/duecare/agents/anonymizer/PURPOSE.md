# Purpose — Anonymizer Agent

> Hard PII gate - no raw PII passes this point

## Long description

Detects PII via Presidio + regex + Gemma 4 E2B NER, applies
anonymization strategies (redact / tokenize / generalize /
drop), then re-scans via a verifier. Items that still contain
PII after anonymization go to quarantine.

This is a hard gate: downstream agents cannot read the raw
probe store, only the clean output.

## Module id

`duecare.agents.anonymizer`

## Kind

agent

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.

## Notes

Audit log stores SHA256 of original content, never raw PII.
