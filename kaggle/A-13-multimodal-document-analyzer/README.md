# A-12 — Multimodal document analyzer (Gemma 4 vision)

<!-- duecare:lane-label -->
> **Serves lanes:** 03 Individual worker / mobile, 02 NGO & regulator

This kernel is the load-bearing demo of Gemma 4's UNIQUE
multimodal capability per the hackathon rubric (Technical Depth
& Execution requires Gemma 4's unique features to be substrate,
not decoration).

## What it does

Upload a photo of a recruitment contract, passport notice, job
advertisement, or fee receipt; Gemma 4 vision extracts the text,
the safety harness flags risks (passport retention, illegal fees,
contract substitution), and emits a structured envelope with ILO
citations.

## Pipeline

1. Phase 0: Unsloth stack install (vision-capable Gemma 4 needs
   the same torch + transformers pin as the text variants).
2. Phase 1: DueCare from GitHub (no Kaggle wheel datasets).
3. Phase 2: Load Gemma 4 base via Unsloth FastModel
   (`unsloth/gemma-4-{variant}-bnb-4bit`; default e4b-it).
4. Phase 3: Workbench-shell upload UI: image dropzone + optional
   text question + Analyze button.
5. Phase 4: Per-upload pipeline:
   - SHA-256 of the image bytes (audit primary key)
   - Gemma 4 vision call with chat-template messages including
     image content blocks
   - GREP rule firing over the model's response text
   - Tool-call discovery (heuristic dispatcher)
   - ILO / POEA / RA / BP2MI citation extraction via regex
6. Rolling v1.0 bundle written on every upload so a mid-session
   crash still leaves usable rows.

## Inputs

- **GPU:** T4 (e4b-it default fits in 16 GB 4-bit; e2b-it is also
  vision-capable for smoke tests)
- **Internet:** ON (GitHub install + HF Hub model download)
- **Optional secret:** `HF_TOKEN` for private repo access (not
  required for `unsloth/gemma-4-*-bnb-4bit`)
- **No Kaggle Dataset attachments required**

## Outputs

To `/kaggle/working/`:

- `<run_id>_multimodal_results.json` — full per-upload results (v1.0)
- `<run_id>_metadata.json` — payload minus `results`
- `<run_id>_bundle.zip` — manifest + above

Per-row schema: `upload_id, image_sha256, image_mime, image_dims,
user_question, extracted_text, risk_flags[].{label, severity,
evidence}, citations[], tools_called[], elapsed_s, error`.

Run-ID format: `a12_multimodal_{variant}_{iso_ts}`.

## Where this slot lives

- **Canonical role:** A-12 multimodal document analyzer (extension
  to the 11-slot ladder; rubric anchor for Gemma 4 unique features)
- **Folder path:** `kaggle/A-13-multimodal-document-analyzer/`
  (new folder; no legacy slot was available)
- **Sibling kernels referenced:**
  `kaggle/A-02-chat-playground-with-grep-rag-tools/` for the
  GREP/RAG/Tools harness pattern.

See `docs/appendix_experiment_ladder.md` and
`docs/appendix_artifact_schema.md`.
