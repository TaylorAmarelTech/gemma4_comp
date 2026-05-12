# A-18 — Demo replay (zero-inference video kernel)

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

## Modes

URL params switch the kernel's surface during recording:

- **`?mode=presentation&lane=worker`** (default) — auto-plays the
  selected lane's scenes in order. This is the recording target.
- **`?mode=setup`** — author / edit the DEMO_SCRIPT in-browser.
  Save writes `/kaggle/working/demo_script_authored.json` so you
  can download + commit it back into the kernel for future
  recordings. Load accepts an uploaded JSON to restore.
- **`?mode=slides`** — pre-built slide deck (title / problem /
  solution / background / lane intros / closing). Spacebar
  advances. Cleanly cuts to `?mode=presentation&lane=X` between
  slides.

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

- **Canonical role:** A-18 demo replay (extension to the 11-slot
  ladder; rubric anchor for Video Pitch & Storytelling)
- **Folder path:** `kaggle/A-18-demo-replay/` (new folder; no
  legacy slot was available)
- **Sibling kernels referenced:**
  `kaggle/A-02-chat-playground-with-grep-rag-tools/` for the
  GREP/RAG/Tools traces that the curated harness_trace tiles
  represent.

See `docs/appendix_experiment_ladder.md`.
