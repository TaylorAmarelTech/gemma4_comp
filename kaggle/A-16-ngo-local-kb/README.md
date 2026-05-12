# A-15 — NGO local-KB / case-file ingestion

<!-- duecare:lane-label -->
> **Serves lanes:** 02 NGO & regulator

## Status

**Folder reserved; kernel.py pending.** This slot will:

1. Accept synthetic case files (text or a small set of files)
2. Run each through the A-11 PrivacyRedactor adapter to redact PII
3. Extract entities (PERSON, EMPLOYER, RECRUITER, AMOUNT,
   CORRIDOR) and salt-hash them for the local SQLite store
4. Build the entity graph linking cases by salted-hash overlap
5. Emit a `local_kb.sqlite` ready for a caseworker to query
6. Optional: render the "share aggregate" preview (anonymized
   signal stream) for the NGO data-share flow

Closes Lane 02 gap (the website's NGO caseworker use case +
`local-kb.html` mechanics).

See `docs/appendix_experiment_ladder.md` for the full ladder spec.
