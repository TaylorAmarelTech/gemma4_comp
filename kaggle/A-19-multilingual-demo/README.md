# A-19 — Multilingual demo

<!-- duecare:lane-label -->
> **Serves lanes:** 03 Individual worker / mobile

## What it does

Same recruitment-fee scenario answered in 5 languages relevant to
the migrant-worker corridors:

| Code | Language | Corridor |
|---|---|---|
| EN | English | (baseline) |
| TL | Tagalog / Filipino | PH-HK, PH-UAE |
| NE | Nepali | NP-Gulf |
| BN | Bengali | BD-Gulf |
| ID | Indonesian | ID-HK, ID-Gulf |

Demonstrates Gemma 4's multilingual reach per the hackathon rubric
(Tech Depth 30pts requires unique-feature demonstrations).

Mirrors the `why-gemma.html` "in their language" Lane 03 claim
on the website.

## Pipeline

1. Install DueCare from GitHub (lightweight, no Unsloth needed).
2. Bundled `MULTILINGUAL_DEMO` dict with the same scenario across
   5 languages.
3. Workbench shell with language tabs (click to switch).
4. Zero model load, zero inference — instant playback for video
   recording.

## Inputs

- **GPU:** NOT required
- **Internet:** ON (GitHub install only)
- **Kaggle Datasets:** none
- **Secrets:** none

## Outputs

To `/kaggle/working/`, via `duecare.appendix_primitives.write_v1_bundle()`
(this kernel is the reference implementation):

- `<RUN>_results.json` — v1.0 BundleEnvelope: `{schema_version,
  kernel_id, run_id, config, metadata, summary, results[]}`
- `<RUN>_run.jsonl` — one PerRow per language (EN / TL / NE /
  BN / ID), each line self-describing with envelope metadata
- `<RUN>_metadata.json` — envelope minus `results[]` (for thin
  index reads)
- `<RUN>_bundle.zip` — all three above + `manifest.json` with
  sha256 checksums per file
- `RUN_ID` format: `a19_multilingual_{ts}`
  (e.g., `a19_multilingual_2026-05-12T19-30-00Z`)

On older `duecare-llm-chat` versions without the
`appendix_primitives` module, the kernel falls back to the legacy
2-file form: `<RUN>_multilingual_demo.json` + `<RUN>_bundle.zip`
(with the JSON only, no streaming JSONL or metadata.json).

## Where this slot lives

- **Canonical role:** A-19 multilingual demo
- **Folder path:** `kaggle/A-19-multilingual-demo/`
- **Sibling kernel:** A-24 demo replay (also a video-recording
  surface; A-19 adds the language dimension).

See `docs/appendix_experiment_ladder.md`.

## Cross-links

- **Why Gemma 4 (feature showcases):** [duecare-ai.com/why-gemma](https://duecare-ai.com/why-gemma) — multilingual reach is one of the capabilities the hub names there.
- **BundleEnvelope schema:** [duecare-ai.com/technical-docs](https://duecare-ai.com/technical-docs) — A-19 is the **first reference implementation** of `duecare.appendix_primitives.write_v1_bundle()`.
- **Full kernel roster:** [duecare-ai.com/kernels](https://duecare-ai.com/kernels).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).
