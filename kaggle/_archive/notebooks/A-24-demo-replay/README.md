# A-24 — Demo replay (zero-inference video kernel)

<!-- duecare:lane-label -->
> **Serves lanes:** all (this is the recording surface for the
> hackathon video; every lane has a curated 4-scene flow)

## Why this kernel exists

Per the hackathon rubric, **70 of 100 points live in the video**
(40 Impact + 30 Video Pitch). Real model inference is unpredictable
on Kaggle GPUs — sometimes 4 seconds, sometimes 40, occasionally
the kernel restarts. Recording a clean 3-minute pitch with live
inference is brutal.

This kernel solves that. **Zero model load. Zero inference latency.**
A curated DEMO_SCRIPT plays prompts + responses through the same
chat UI that real kernels use, with typewriter prompt + token-stream
response cadence that LOOKS exactly like a real run, but executes
in deterministic seconds.

## Routes

Clean paths switch the replay lane during recording:

- **`/presentation/worker`** (default) - auto-plays the worker lane's scenes in order. This is the primary recording target.
- **`/presentation/caseworker`** - caseworker / regulator lane.
- **`/presentation/platform`** - platform safety lane.
- **`/presentation/researcher`** - researcher / journalist lane.
- **`/presentation/developer`** - developer / integration partner lane.

Legacy `?lane=worker` links still work for old bookmarks, but the visible navigation uses clean route paths.

## Lanes (5)

Each lane has 4 curated scenes that trace a realistic conversation
flow for that audience:

| Lane | Scenes | Story arc |
|---|---|---|
| **Worker** (Lane 03) | fee question -> passport retention -> unregistered recruiter -> no salary | A worker discovers exploitation and is routed to NGOs |
| **Caseworker** (Lane 02) | intake triage -> pattern match -> complaint draft -> aggregate share | An NGO closes a case end-to-end |
| **Platform safety** (Lane 01) | UGC score -> batch summary -> rule drill -> false positive | A T&S analyst sees harness in production |
| **Researcher** (Lane 04) | pin pack -> corridor trends -> cross-corridor -> reproduce claim | A researcher cites a reproducible number |
| **Developer** (Lane 05) | minimal API -> Messenger adapter -> release pinning -> local-KB API | A dev wires the runtime in 3 calls |

## Recording controls (presentation mode)

- `Space` — advance to next scene
- `R` — rewind to scene 1 of the current lane
- `S` — skip the typewriter animation (instant render of the
  current scene)
- `1-5` — jump to scene N

## Inputs

- **GPU:** NOT required (zero inference)
- **Internet:** ON (GitHub install only — replay runs offline once
  packages are present)
- **Kaggle Datasets:** none
- **Secrets:** none

## Outputs

In setup mode, writes
`/kaggle/working/demo_script_authored.json` with the user-edited
script. Presentation and slides modes write nothing. The bundled
DEMO_SCRIPT in `kernel.py` is the durable source of truth; the
authored.json is for round-trip iteration.

## Where this slot lives

- **Canonical role:** A-24 demo replay (extension to the 24-slot
  ladder; rubric anchor for Video Pitch & Storytelling)
- **Folder path:** `kaggle/A-24-demo-replay/` (new folder; no
  legacy slot was available)
- **Sibling kernels referenced:**
  `kaggle/A-02-chat-playground-with-grep-rag-tools/` for the
  GREP/RAG/Tools traces that the curated harness_trace tiles
  represent.

See `docs/appendix_experiment_ladder.md`.

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A24 appendix — Demo replay (zero-inference video kernel)**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#03 core: Video pitch (in-app slides + presenter remote)](../03-duecare-video-pitch/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Runtime vs weights safety study](../A-10-runtime-vs-weights-safety-study/README.md)
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
- **[#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)**

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
