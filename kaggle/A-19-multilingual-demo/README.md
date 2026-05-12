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

To `/kaggle/working/`:

- `a19_multilingual_demo.json` — full payload with languages dict
- `a19_multilingual_bundle.zip` — manifest + above

## Where this slot lives

- **Canonical role:** A-19 multilingual demo
- **Folder path:** `kaggle/A-19-multilingual-demo/`
- **Sibling kernel:** A-18 demo replay (also a video-recording
  surface; A-19 adds the language dimension).

See `docs/appendix_experiment_ladder.md`.
