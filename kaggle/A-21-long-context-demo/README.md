# A-21 — Long-context demo (Gemma 4 128K, zero inference)

<!-- duecare:lane-label -->
> **Serves lanes:** 02 NGO & regulator · 04 Researcher

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Closes the long-context gap surfaced in `docs/gemma4_feature_showcase.md`: a real demo of Gemma 4's 128K context window applied to migrant-worker compliance reasoning. |
| **What it does** | Loads a multi-statute corpus (POEA MC 14-2017 + RA 8042 + ILO C189 + BP2MI Reg 8-2023 + ILO C29) and answers 3 cross-statute questions that require correlating across 2-3 docs at once. |
| **Demo path** | Open the kernel, hit Save & Run All, read the corpus stats card + the 3 cached Q&A panels. Zero inference; renders in seconds. |
| **Audience** | NGO caseworkers verifying cross-jurisdiction protections; researchers documenting the long-context advantage over RAG-only. |
| **Inputs** | Bundled compliance corpus (public-source statute extracts); no GPU; no Kaggle dataset attachments; no secrets. |
| **Gemma 4 features** | **Long context (128K)** as the headline feature; cross-statute reasoning in a single thinking step; the value of long context vs separate retrieval calls. |
| **Outputs** | v1.0 BundleEnvelope via `duecare.appendix_primitives.write_v1_bundle()` — 4 files (results.json + run.jsonl + metadata.json + bundle.zip with manifest+sha256). |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, gemma4_feature_showcase.md, and public website. |

## What it does

Exercises Gemma 4's **long-context (128K)** capability on a real
DueCare-scope task: cross-statute reasoning. Each of the 3 cached
Q&A pairs requires Gemma 4 to find information across 2-3 statutes
in a single thinking step — the operational value of long context
over retrieval-only architectures.

Closes the "Long-context demonstration at 128K boundary" gap noted
in [`docs/gemma4_feature_showcase.md`](../../docs/gemma4_feature_showcase.md)
section "Where each capability is not showcased yet".

## Pipeline

1. Install DueCare from GitHub (lightweight; no Unsloth needed).
2. Load the bundled multi-statute compliance corpus into memory.
3. Compute corpus stats (n_statutes, total chars, approx tokens).
4. Emit the canonical v1.0 bundle via
   `duecare.appendix_primitives.write_v1_bundle()` (this is the
   second reference implementation after A-19 multilingual).
5. Launch the workbench shell with stats card + corpus table + 3
   cached Q&A panels.

## Inputs

- **GPU:** NOT required (cached-mode default).
- **Internet:** ON (GitHub install only).
- **Kaggle Datasets:** none required for the cached mode.
- **Secrets:** none required.
- **Bundled corpus:** 5 public-source statute extracts shipped
  in `kernel.py` as `COMPLIANCE_CORPUS`.

## Outputs

To `/kaggle/working/`, via `duecare.appendix_primitives.write_v1_bundle()`:

- `<RUN>_results.json` — v1.0 BundleEnvelope:
  `{schema_version, kernel_id, run_id, config, metadata, summary,
   results[]}`. Each row carries a `qa_id` (row_id), the full
  prompt + response, and the citation list.
- `<RUN>_run.jsonl` — one PerRow per Q&A, each line self-describing
  with envelope metadata.
- `<RUN>_metadata.json` — envelope minus `results[]`, plus corpus
  stats + the list of statute IDs used.
- `<RUN>_bundle.zip` — all three above + `manifest.json` with
  per-file sha256 checksums.
- `RUN_ID` format: `a21_long_context_{ts}`
  (e.g., `a21_long_context_2026-05-12T19-30-00Z`).

On older `duecare-llm-chat` versions without the
`appendix_primitives` module, the kernel falls back to the legacy
2-file emit: `<RUN>_long_context_demo.json` + `<RUN>_bundle.zip`
with just the JSON.

## Where this slot lives

- **Canonical role:** A-21 long-context demo
- **Folder path:** `kaggle/A-21-long-context-demo/`
- **Kernel ID:** `a-21-long-context-demo`
- **Reference for:** future kernels migrating to
  `duecare.appendix_primitives.write_v1_bundle()`. A-19 multilingual
  was the first reference; A-21 is the second, with a longer per-row
  payload and richer `summary`/`metadata` envelopes.
- **Sister kernels:** A-19 multilingual (zero-inference cached
  pattern), A-20 privacy-boundary (zero-inference cached pattern),
  03 video-pitch (zero-inference replay).

See `docs/appendix_experiment_ladder.md` for the full ladder spec.

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md).
- **Focused live demo:** [#02 core: Live demo](../02-live-demo/README.md).
- **Gemma 4 feature showcase:** [`docs/gemma4_feature_showcase.md`](../../docs/gemma4_feature_showcase.md).
- **User walkthrough:** [`docs/user_walkthrough.md`](../../docs/user_walkthrough.md).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).
