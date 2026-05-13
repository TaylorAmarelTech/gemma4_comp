# A-15 — NGO local-KB / case-file ingestion

<!-- duecare:lane-label -->
> **Serves lanes:** 02 NGO & regulator

## What it does

Lets an NGO caseworker ingest case files into a local SQLite
knowledge base. PII is redacted via the A-11 PrivacyRedactor
adapter; entities (PERSON, EMPLOYER, RECRUITER, AMOUNT, CORRIDOR)
are extracted and salt-hashed so the same person across cases is
linkable without ever storing the raw identifier.

Closes the Lane 02 gap — the website's NGO caseworker use case +
the `local-kb.html` mechanics.

## Pipeline

1. Accept synthetic case files (text or a small set of files) via
   the dashboard.
2. Run each through the A-11 PrivacyRedactor adapter to redact PII.
3. Extract entities and salt-hash them for the local SQLite store.
4. Build the entity graph linking cases by salted-hash overlap.
5. Emit `local_kb.sqlite` ready for a caseworker to query.
6. Optional: render the "share aggregate" preview (anonymized
   signal stream) for the NGO data-share flow.

## Inputs

- **GPU:** T4 ×2 (PrivacyRedactor adapter inference)
- **Internet:** ON (cloudflared tunnel)
- **Kaggle Datasets:** wheels dataset
- **Models:** `google/gemma-4/Transformers/<variant>-it/1`
- **Adapters:** `taylorscottamarel/duecare-gemma-4-*-PrivacyRedactor-*`
  (HF Hub)
- **Upload:** small set of case-file text via the dashboard's
  `<input type="file">` (this is the kernel's PRIMARY input,
  not an upstream-bundle handoff)
- **Secrets:** `HF_TOKEN`

## Outputs

To `/kaggle/working/`:

- `<RUN>_bundle.zip` — v1.0 envelope with canonical `summary`
  (+ legacy `aggregate`) + canonical `results[]`
  (+ legacy `ingested[]`); rows carry `error: null` defaults
- `<RUN>_local_kb.json` — full envelope payload
- `<RUN>_run.jsonl` — streaming per-row form
- `<RUN>_metadata.json` — envelope minus `results[]`
- `local_kb.sqlite` — the caseworker-queryable store
- `RUN_ID` format: `a16_local_kb_{ts}`
  (e.g., `a16_local_kb_2026-05-12T19-30-00Z`)

The dashboard exposes `<a id="bundle-link">` populated via
`fetch('/api/state')` once ingestion completes.

## Where this slot lives

- **Canonical role:** A-16 NGO local-KB / case-file ingestion
- **Folder path:** `kaggle/A-16-ngo-local-kb/`
- **Kernel ID:** `a-16-ngo-local-kb`
- **Upstream:** consumes A-11 PrivacyRedactor adapter from HF Hub
- **Downstream:** aggregate signals feed the website's
  `/submit-information` flow (`aggregate_signal` submission kind)

See `docs/appendix_experiment_ladder.md` for the full ladder spec.
