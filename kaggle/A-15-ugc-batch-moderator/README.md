# A-14 — UGC batch moderator

<!-- duecare:lane-label -->
> **Serves lanes:** 01 Platform safety

## What it does

Batch-moderates inbound posts, ads, or job-listings ("user-generated
content" / UGC) at platform-safety scale. Each row goes through the
full DueCare harness (Persona + GREP + RAG + Tools) and emits a
v1.0 risk envelope: score / verdict / indicators / citations /
suggested action.

Closes the Lane 01 gap — the website's primary audience for the
"screen exploitative UGC at scale" use case.

## Pipeline

1. Accept a CSV / JSONL of inbound posts via the dashboard's file
   picker (`<input type="file">` on the homepage).
2. Run each row through Persona + GREP + RAG + Tools.
3. Produce a per-row risk envelope: `score`, `verdict`,
   `indicators[]`, `citations[]`, `suggested_action`.
4. Emit a v1.0 bundle with per-row `results[]` + canonical
   `summary` (top indicators, corridor concentration,
   false-positive examples).
5. Render the moderation queue + summary cards in the workbench
   shell with a JS-injected bundle-download link.

## Inputs

- **GPU:** T4 ×2 (Gemma 4 inference for each row)
- **Internet:** ON (cloudflared tunnel)
- **Kaggle Datasets:** wheels dataset
- **Models:** `google/gemma-4/Transformers/<variant>-it/1`
- **Upload:** CSV or JSONL of posts (uploaded via the homepage
  `<input type="file">`; this is the kernel's PRIMARY input,
  not an upstream-bundle handoff)
- **Secrets:** `HF_TOKEN`

## Outputs

To `/kaggle/working/`:

- `<RUN>_bundle.zip` — v1.0 envelope with `summary`
  (+ legacy `aggregate` alias) + per-row `results[]`
- `<RUN>_ugc_moderation.json` — full envelope payload
- `<RUN>_run.jsonl` — streaming per-row form
- `<RUN>_metadata.json` — envelope minus `results[]`
- `RUN_ID` format: `a15_ugc_{variant}_{ts}`
  (e.g., `a15_ugc_e4b-it_2026-05-12T19-30-00Z`)

The dashboard exposes `<a id="bundle-link">` populated via
`fetch('/api/state')` once the run completes.

## Where this slot lives

- **Canonical role:** A-15 UGC batch moderator
- **Folder path:** `kaggle/A-15-ugc-batch-moderator/`
- **Kernel ID:** `a-15-ugc-batch-moderator`
- **Downstream:** moderation queue feeds into A-16 NGO local-KB
  for case-file ingestion, and A-17 sentinel for trend monitoring.

See `docs/appendix_experiment_ladder.md` for the full ladder spec.
