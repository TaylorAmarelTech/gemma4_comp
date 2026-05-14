# Notebook 03: DueCare Video Pitch

> Recording-first Cloudflare site for the Gemma 4 Good video. It opens on an
> introduction slide, then switches into cached product demos that can be
> screen-recorded without waiting for inference.

## Role in the Submission

- **01 Exploration Workbench:** the full product surface and live harness UI.
- **02 Live Demo:** the focused product demo with real inference and workbench
  routes.
- **03 Video Pitch:** the slide deck plus cached demo replay for recording the
  three-minute hackathon video.
- **A-00 Omni Experiment Workbench:** the technical proof surface for bulk evaluation,
  synthetic data, fine-tuning jobs, reports, and graphs.

02 and 03 are intentionally different. Use 03 to record the story cleanly. Use
02 when judges want to interact with a running product demo.

## Modes

| Mode | URL | What it shows |
|---|---|---|
| Slides | `?mode=slides` | Fifteen-slide pitch deck: problem, legal context, why normal LLMs fail, prior art, solution, why Gemma 4, validation, five use cases, ecosystem, closing. Opens by default. |
| Presentation | `?mode=presentation&lane=worker` | Cached 5-lane replay with typewriter prompt, thinking indicator, response stream, citations, and harness trace. |
| Setup | `?mode=setup` | Edit cached scenes, save script JSON, and export prompts, responses, traces, scorecards, slides, and synthetic media. |

## Recording Flow

1. Open the printed Cloudflare URL. It starts in `?mode=slides`.
2. Advance through the title, problem, legal context, LLM failure, prior art,
   solution, why Gemma 4, and validation slides.
3. Switch to `?mode=presentation&lane=worker` for the worker story.
4. Switch to `?mode=presentation&lane=caseworker` to show the synthetic media
   image and local intake workflow.
5. Optionally show platform, researcher, or developer lanes.
6. Return to slides for ecosystem, technical depth, and closing.
7. Use `?mode=setup` and click **Export evidence bundle** to create the JSON,
   CSV, Markdown, ZIP, and synthetic media artifacts.

## Cached Demo Evidence

The presentation replay is zero-inference by design. Each scene includes:

- prompt text
- cached Gemma-style response
- harness trace with persona, GREP, RAG, tools, or privacy layers
- citations
- qualitative scorecard
- optional media image

The first caseworker scene includes a synthetic ID-card style image. It is
generated inside the notebook under `/kaggle/working/video_pitch_media/` and is
included in the exported evidence ZIP.

## Controls

| Key | Slides mode | Presentation mode |
|---|---|---|
| `Space` or right arrow | next slide | next scene |
| left arrow | previous slide | previous scene |
| `R` | restart deck | restart lane |
| `S` | no action | skip animation |
| `1-9` | jump to slide | jump to scene |

## Inputs and Outputs

- GPU: not required
- Internet: on, for GitHub install and Cloudflare tunnel
- Datasets: none
- Secrets: none

Outputs from setup mode:

- `video_pitch_export_*.json`
- `video_pitch_export_*_scenes.csv`
- `video_pitch_export_*.md`
- `video_pitch_export_*.zip`
- `video_pitch_media/synthetic_ph_hk_id_card.svg`

## Related Notebooks

- `../A-00-omni-experiment-workbench/`: technical proof, prompt runs,
  reports, synthetic data, and training jobs.
- `../A-24-demo-replay/`: appendix replay surface.
- `../A-20-privacy-boundary/`: privacy-boundary visualization.
- `../A-19-multilingual-demo/`: multilingual replay.
