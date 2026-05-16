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
| Slides | `/slides` | Fifteen-slide pitch deck: problem, legal context, why normal LLMs fail, prior art, solution, why Gemma 4, validation, five use cases, ecosystem, closing. Opens by default. |
| Presentation | `/presentation/worker` | Cached 5-lane replay with typewriter prompt, thinking indicator, response stream, citations, and harness trace. |
| Setup | `/setup` | Edit cached scenes, save script JSON, and export prompts, responses, traces, scorecards, slides, and synthetic media. |

Legacy query-string links such as `?mode=slides` and
`?mode=presentation&lane=worker` still work for backward compatibility, but the
visible UI and recording checklist use clean route paths.

## Recording Flow

1. Open the printed Cloudflare URL. It starts in `/slides`.
2. Advance through the title, problem, legal context, LLM failure, prior art,
   solution, why Gemma 4, and validation slides.
3. Switch to `/presentation/worker` for the worker story.
4. Switch to `/presentation/caseworker` to show the synthetic media
   image and local intake workflow.
5. Optionally show platform, researcher, or developer lanes.
6. Return to slides for ecosystem, technical depth, and closing.
7. Use `/setup` and click **Export evidence bundle** to create the JSON,
   CSV, Markdown, ZIP, and synthetic media artifacts.

## Recording Preflight

Run this checklist once before screen capture:

1. Open `/slides` and confirm the deck starts on the problem statement.
2. Check that the validation slide points to A-00 reports rather than relying on the replay alone.
3. Open `/presentation/worker` and verify the cached response shows worker-centered, non-revictimizing guidance.
4. Open `/presentation/caseworker` and confirm the synthetic media example renders.
5. Open platform, researcher, and developer lanes at least once so stale copy or broken controls are caught.
6. Open `/setup`, export evidence, and confirm the ZIP contains scenes, traces, scorecards, slides, and media.
7. Keep the exported A-00 report URL or artifact path ready for the technical-depth slide.

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

## Reuse From Kernel 01

Notebook 03 is intentionally zero-inference, but its language and artifacts
should mirror the live workbench contract:

- Use `duecare-llm-chat >= 0.17.0` terminology and sample names.
- Keep source case bundles distinct from importable knowledge files.
- Use the same five audience lanes and the same trust-boundary vocabulary.
- Reference Kernel 01's `case_files_media_rich_sample.zip`,
  `knowledge_files_sample.zip`, and `prompt_eval_training_seed_sample.zip`
  when describing what the replay represents.
- Keep cached scenes aligned with `/api/harnesses`,
  `/api/portability`, `/api/knowledge/type-catalog`, and
  `/api/audit/workbench-inventory` so
  the video does not promise a workflow the live workbench cannot show.

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
