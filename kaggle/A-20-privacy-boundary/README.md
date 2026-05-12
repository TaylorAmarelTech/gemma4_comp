# A-20 — Privacy boundary visualization

<!-- duecare:lane-label -->
> **Serves lanes:** all (trust surface for every audience)

## What it does

Side-by-side visualization showing EXACTLY what stays on the
caseworker's machine vs what would leave if the operator clicks
"share aggregate". Mirrors `privacy-boundary.html` on the website.

CPU-only, zero inference. Pre-baked sample intake + redaction +
salt-hash + aggregate side-by-side, with the BOUNDARY between
local-only and outside-the-machine drawn explicitly.

## Pipeline

1. Install DueCare from GitHub (lightweight; no Unsloth needed).
2. Bundled synthetic intake (`SAMPLE_INTAKE` with fake PII).
3. Regex PII detector splits raw -> redacted + salt-hash mapping.
4. Aggregate-share preview shows exactly what JSON would leave.
5. Workbench shell renders side-by-side panels with the visual
   boundary band between them.

## Inputs

- **GPU:** NOT required
- **Internet:** ON (GitHub install only; everything else offline)
- **Kaggle Datasets:** none
- **Secrets:** none

## Outputs

To `/kaggle/working/`:

- `<RUN>_privacy_boundary_demo.json` — the side-by-side state with
  fields `local_state.{raw_intake, redacted_intake, entities[]}` +
  `aggregate_state_what_would_leave.{period_days, n_cases,
  entity_label_counts, repeat_hashes, note}`
- `<RUN>_bundle.zip` — manifest + above
- `RUN_ID` format: `a20_privacy_{ts}`
  (e.g., `a20_privacy_2026-05-12T19-30-00Z`)

## Where this slot lives

- **Canonical role:** A-20 privacy-boundary visualization
- **Folder path:** `kaggle/A-20-privacy-boundary/`
- **Sibling kernels:** A-15 (NGO local-KB — uses the same regex
  PII detector + salt-hash pattern); A-10 (PII synth) and A-11
  (PrivacyRedactor trainer) for the upstream pipeline.

See `docs/appendix_experiment_ladder.md`.
