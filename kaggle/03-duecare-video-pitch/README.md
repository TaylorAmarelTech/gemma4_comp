# Notebook 03 — DueCare Video Pitch

<!-- duecare:lane-label -->
> **Serves lanes:** all (recording surface for the hackathon video;
> serves every audience lane)

## What it is

Main notebook **03** of the DueCare submission, alongside:

- **01** `duecare-exploration-workbench` — omni playground
- **02** `live-demo` — focused live Gemma 4 demo (real inference)
- **03** `video-pitch` — slides + scripted replay + setup (THIS notebook)

Per the hackathon rubric, **70 of 100 points live in the video**
(Impact 40pts + Video Pitch 30pts). Real model inference on Kaggle
is unpredictable — sometimes 4 seconds, sometimes 40. Recording a
clean 3-minute pitch with live inference is brutal.

This kernel is the dedicated video-recording surface. Three modes
via URL param:

| Mode | URL | What it shows |
|---|---|---|
| **Slides** | `?mode=slides` | 8-slide deck: title / problem / solution / 5 lanes / before-after / privacy boundary / tech depth / closing |
| **Presentation** | `?mode=presentation&lane=worker` (default) | Curated 5-lane x 4-scene replay (typewriter prompt + thinking + token-stream response) |
| **Setup** | `?mode=setup` | Inspect the bundled DEMO_SCRIPT; copy the JSON, edit offline, paste back |

## Recording controls

| Key | Slides mode | Presentation mode |
|---|---|---|
| `Space` / `->` | next slide | next scene |
| `<-` | prev slide | (n/a) |
| `R` | rewind to slide 1 | rewind to scene 1 |
| `S` | (n/a) | skip animation |
| `P` | switch to presentation | (already there) |
| `L` | (in setup) switch to slides | (n/a) |
| `1-9` | jump to slide N | jump to scene N |

## Recording flow (3-minute video)

1. **Open `?mode=slides`** — walk through slides 1-4 (title,
   problem, solution, 5 lanes intro).
2. **Press `P` or navigate** to
   `?mode=presentation&lane=worker` — record the 4-scene worker
   lane (fee question / passport / unlicensed recruiter / no
   salary).
3. **Switch URL to `?mode=presentation&lane=platform`** — record
   2-3 platform-safety scenes.
4. **Switch URL to `?mode=presentation&lane=researcher`** —
   record the "reproduce a claim" scene.
5. **Back to `?mode=slides`** — close with slides 5-8
   (before/after, privacy boundary, tech depth, closing URL).

Total recorded length: ~3 minutes if you don't dwell.

## Lanes (5)

| Lane | Scenes | Story arc |
|---|---|---|
| **Worker** (Lane 03) | fee question -> passport retention -> unregistered recruiter -> no salary | A worker discovers exploitation and is routed to NGOs |
| **Caseworker** (Lane 02) | intake triage -> pattern match -> complaint draft -> aggregate share | An NGO closes a case end-to-end |
| **Platform safety** (Lane 01) | UGC score -> batch summary -> rule drill -> false positive | A T&S analyst sees harness in production |
| **Researcher** (Lane 04) | pin pack -> corridor trends -> cross-corridor -> reproduce claim | A researcher cites a reproducible number |
| **Developer** (Lane 05) | minimal API -> Messenger adapter -> release pinning -> local-KB API | A dev wires the runtime in 3 calls |

## Inputs

- **GPU:** NOT required (zero inference)
- **Internet:** ON (GitHub install only; playback runs offline)
- **Kaggle Datasets:** none
- **Secrets:** none

## Outputs

Nothing written during normal slides/presentation playback. Setup
mode displays the bundled DEMO_SCRIPT for offline editing.

## Sibling kernels

- `kaggle/A-24-demo-replay/` — appendix version of the same
  surface (presentation mode only; this notebook supersedes it
  as the main video-pitch surface).
- `kaggle/A-19-multilingual-demo/` — 5-language variant.
- `kaggle/A-20-privacy-boundary/` — privacy-boundary trust
  visualization (referenced in slide 6).

See `docs/appendix_experiment_ladder.md`.

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#03 core — Video pitch (in-app slides + presenter remote)**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- **[#03 core: Video pitch (in-app slides + presenter remote)](../03-duecare-video-pitch/README.md)**
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)
- [#A12 appendix: PrivacyRedactor LoRA fine-tune + eval](../A-12-pii-fine-tune-eval/README.md)
- [#A13 appendix: Multimodal document analyzer (Gemma 4 vision)](../A-13-multimodal-document-analyzer/README.md)
- [#A14 appendix: On-device export (LoRA merge -> GGUF + LiteRT)](../A-14-on-device-export/README.md)
- [#A15 appendix: UGC batch moderator (Lane 01 platform safety)](../A-15-ugc-batch-moderator/README.md)
- [#A16 appendix: NGO local-KB / case-file ingestion](../A-16-ngo-local-kb/README.md)
- [#A17 appendix: Knowledge-pack builder + verifier](../A-17-knowledge-pack-builder/README.md)
- [#A18 appendix: Sentinel / research monitor](../A-18-sentinel-research-monitor/README.md)
- [#A19 appendix: Multilingual demo (5-language playback)](../A-19-multilingual-demo/README.md)
- [#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
