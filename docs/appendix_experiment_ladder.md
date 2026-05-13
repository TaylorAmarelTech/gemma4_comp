# Canonical appendix experiment ladder (locked 2026-05-11)

> **Source-of-truth for the 11 appendix kernels.** Per Taylor's
> 2026-05-11 directive, the appendices form a reproducible
> end-to-end model-improvement pipeline rather than a loose
> collection of playgrounds. **Do not regress this structure** —
> any future relabeling, reordering, or slot-merge must come from
> Taylor in writing.
>
> Companion doc: [`appendix_artifact_schema.md`](appendix_artifact_schema.md)
> defines the cross-kernel JSON/JSONL/ZIP handoff format that A-03 and
> A-08 consume from A-01/A-02/A-06/A-07.

## Hard rules — every appendix kernel

These are non-negotiable. Validate every new or edited appendix
kernel against this list before committing.

1. **GitHub-only install.** No attached Kaggle `*-wheels` datasets.
   Two-tier: GitHub Release wheels first, then
   `git+https://...@<sha>#subdirectory=packages/<pkg>` as fallback.
   Canonical reference implementation:
   `kaggle/A-08-research-graphs/kernel.py` →
   `install_duecare_from_github()`. Pin commit SHA (immutable),
   never use moving refs like `main` / `master` / `HEAD`.
2. **One model loaded per kernel run.** Cross-kernel handoff happens
   through downloadable artifacts + Kaggle Add Data, never live
   notebook-to-notebook links.
3. **Model picker.** Every kernel supports `GEMMA_MODEL_VARIANT` env
   override across `e2b-it / e4b-it / 26b-a4b-it / 31b-it`. Default
   to the smallest variant that runs the kernel's compute (typically
   `e2b-it` for smoke; `e4b-it` for production).
4. **Workbench shell UI.** Every kernel ends by calling
   `build_minimal_shell()` from `duecare.chat.kernel_shell` to serve
   a summary page with download links + dc_log streaming +
   cloudflared public URL.
5. **Artifact schema.** Batch runners emit the v1.0 contract from
   [`appendix_artifact_schema.md`](appendix_artifact_schema.md):
   `<run_id>_results.json` + `_run.jsonl` + `_metadata.json` +
   `_bundle.zip`. Run-ID format:
   `{kernel_short}_{model_variant}_{model_kind}_{iso_ts}`
   (e.g. `a01_e2b-it_stock_2026-05-11T14-32-08Z`).
6. **No `.ipynb` in active tree.** Source-of-truth is `kernel.py`.
   Notebook previews live only under
   `_archive/kaggle-notebook-previews-2026-05-11/`. Taylor copies
   `kernel.py` text into Kaggle manually.
7. **dc_log instrumentation.** Wire `set_kernel_id()` + `dc_log()`
   for batch start / progress / error / done events so the
   workbench Logs page shows live status.

## The 23 appendix slots (canonical order)

```
A-01 Stock baseline runner       — model picker, library prompts,
                                    harness OFF, emit bundle
A-02 Harnessed runner            — same model + library prompts,
                                    harness ON (persona+GREP+RAG+tools),
                                    emit bundle with harness_trace
A-03 Upload + compare            — accept A-01 + A-02 bundles, run
                                    new harness evaluator + legacy
                                    evaluator, render lift visuals,
                                    emit comparison report
A-04 Synthetic data generator    — Gemma 4 + harness produces
                                    SafetyJudge + PrivacyRedactor
                                    training material
                                    (worst/bad/neutral/good/best ladders)
A-05 Fine-tune trainer           — Unsloth LoRA on A-04 JSONL,
                                    push adapter to HF Hub
A-06 New-model baseline runner   — A-01 logic, but loads the LoRA
                                    adapter from A-05
A-07 New-model harnessed runner  — A-02 logic, but loads the LoRA
                                    adapter from A-05
A-08 New-model comparison        — A-03 logic, but compares A-06 + A-07
                                    bundles (or stock-vs-finetuned)
A-09 Abliterated test generator  — abliterated/cracked Gemma → develop
                                    legacy adversarial tests with
                                    WORST/BAD/NEUTRAL/GOOD/BEST examples
A-10 PII synthetic data generator — composite intake + gold redaction
                                     plans for PrivacyRedactor adapter
A-11 PII fine-tune + evaluation  — train + benchmark PrivacyRedactor LoRA
                                    behind deterministic PII gates
```

## Build status (live as of 2026-05-11; update on each commit)

- A-01 batch baseline runner — committed `13a4240`
- A-02 batch harnessed runner — committed `f4b21c0`
- A-03 upload + compare — committed `b8b7d99`
  (lives in `kaggle/A-03-content-classification-playground/`;
  folder rename pending separate cleanup pass)
- A-04 synthetic data generator — committed `26aaa24`
  (lives in `kaggle/A-06-prompt-generation/`; folder rename pending)
- A-05 fine-tune trainer — committed `ec49ca9`
  (lives in `kaggle/A-07-bench-and-tune/`; folder rename pending)
- A-06 new-model baseline runner — committed `20db869`
  (lives in `kaggle/A-04-content-knowledge-builder-playground/`)
- A-07 new-model harnessed runner — committed `7c371ad`
  (lives in `kaggle/A-05-gemma-content-classification-evaluation/`)
- A-08 new-model comparison — committed (this batch)
  (lives in `kaggle/A-11-grading-evaluation/`)
- A-09 abliterated test generator — committed `7197600` (rename) +
  `cd864a8` (batch ladder generator). Activate the
  WORST/BAD/NEUTRAL/GOOD/BEST 5-frame ladder mode by setting
  `DUECARE_LADDER_MODE=1`. Lives in
  `kaggle/A-10-chat-playground-jailbroken-models/`.
- A-10 PII synth data generator — committed `dc6a93a`. Lives in
  `kaggle/A-09-chat-playground-with-agentic-research/`.
  Template-based; 100% synthetic PII; CPU-only.
- A-11 PII fine-tune + evaluation — committed in this batch. Lives
  in NEW folder `kaggle/A-12-pii-fine-tune-eval/` (no legacy slot
  available; folder created per Taylor's "if we need more notebooks
  we can create more appendix" directive).

The 11-slot canonical ladder is now FULLY BUILT.

## Website-aligned extension slots (A-12 through A-20)

After a full website-vs-kernel coverage audit (16+ template pages
under `apps/duecare-ai.com/app/templates/`), six additional slots
were identified to close the gap between what the website
advertises and what the appendix kernels demonstrate. Two more
(A-19 / A-20) are queued for follow-up.

| Slot | Folder | Purpose | Status |
|---|---|---|---|
| A-12 | `kaggle/A-13-multimodal-document-analyzer/` | Gemma 4 vision: contract/passport photo -> risk envelope (rubric anchor for Gemma 4 unique features) | kernel + metadata + README |
| A-13 | `kaggle/A-14-on-device-export/` | LoRA merge -> GGUF + LiteRT (Special Tech Tracks) | folder + README only; kernel pending |
| A-14 | `kaggle/A-15-ugc-batch-moderator/` | CSV/JSONL of posts -> risk scores + actions (Lane 01) | folder + README only; kernel pending |
| A-15 | `kaggle/A-16-ngo-local-kb/` | Case-file ingestion + entity graph + salted-hash + SQLite (Lane 02) | folder + README only; kernel pending |
| A-16 | `kaggle/A-17-knowledge-pack-builder/` | Build + sign + verify versioned corridor packs (Lane 04 / 05) | folder + README only; kernel pending |
| A-17 | `kaggle/A-18-sentinel-research-monitor/` | URL/submission -> public-info crawl -> proposed pack diff (search/submit flow) | folder pending |
| A-18 | `kaggle/A-18-demo-replay/` | **Zero-inference video recording kernel** (5 lanes x 4 scenes; presentation mode shipped, setup + slides modes queued) | kernel + metadata + README (presentation mode) |
| A-19 | `kaggle/A-19-multilingual-demo/` | Same prompts in EN/TL/NE/BN/ID (Gemma 4 multilingual unique feature) | not yet started |
| A-20 | `kaggle/A-20-privacy-boundary/` | "What stays local vs what gets submitted" trust visualization | not yet started |

## Hackathon rubric mapping

Per `.claude/rules/00_overarching_goals.md`:

- **Impact & Vision (40 pts)** — covered by A-04 / A-05 (the model
  improvement story), A-12 (multimodal worker-side angle), A-13
  (on-device worker reach), A-15 (NGO operational impact), A-18
  (the video that shows all of this).
- **Video Pitch (30 pts)** — A-18 demo replay is the load-bearing
  kernel. Setup + slides modes are the next-priority upgrade.
- **Technical Depth (30 pts)** — A-09 abliterated test ladders,
  A-12 multimodal vision, A-13 GGUF + LiteRT export are the
  rubric-required Gemma 4 unique-features anchors.

### Folder-slot mapping (transition state until cleanup pass)

While the kernel.py contents now reflect the canonical ladder
roles, the on-disk folder names still match the pre-2026-05-11
naming. Until `git mv` rename pass, the mapping is:

| Slot | Folder containing the kernel.py |
|---|---|
| A-01 | `kaggle/A-01-chat-playground/` |
| A-02 | `kaggle/A-02-chat-playground-with-grep-rag-tools/` |
| A-03 | `kaggle/A-03-content-classification-playground/` |
| A-04 | `kaggle/A-06-prompt-generation/` |
| A-05 | `kaggle/A-07-bench-and-tune/` |
| A-06 | (pending) target: `kaggle/A-04-content-knowledge-builder-playground/` |
| A-07 | (pending) target: `kaggle/A-05-gemma-content-classification-evaluation/` |
| A-08 | (pending) target: `kaggle/A-11-grading-evaluation/` |
| A-09 | (pending) target: `kaggle/A-10-chat-playground-jailbroken-models/` |
| A-10 | (pending) target: `kaggle/A-09-chat-playground-with-agentic-research/` |
| A-11 | (pending) — new folder required (no remaining legacy slot) |

## Folder rename policy

When physically moving a slot (e.g. current
`kaggle/A-06-prompt-generation/` →
`kaggle/A-04-synthetic-data-generator/`): **adjust, don't delete**.
Use `git mv` so history is preserved. The old folder path may stay
empty until the next folder rebuild — do not `rm -rf` historical
kernel folders without Taylor's explicit approval.

## Cross-kernel artifact handoff

A-03 and A-08 consume bundles from A-01/A-02/A-06/A-07 via the v1.0
schema. Reviewers and demo viewers should never see "live link to
A-01 output" — only `Add Data → A-01 bundle dataset` followed by an
upload UI inside A-03/A-08. See
[`appendix_artifact_schema.md`](appendix_artifact_schema.md) for the
full contract.

## Reference implementations to study before edits

- **Install pattern (GitHub-only):**
  `kaggle/A-08-research-graphs/kernel.py` →
  `install_duecare_from_github()`
- **Batch baseline runner:** `kaggle/A-01-chat-playground/kernel.py`
  (after commit `13a4240`)
- **Batch harnessed runner:**
  `kaggle/A-02-chat-playground-with-grep-rag-tools/kernel.py`
  (after commit `f4b21c0`)
- **Workbench shell + summary UI:**
  `packages/duecare-llm-chat/src/duecare/chat/kernel_shell.py` →
  `build_minimal_shell()`
- **Test prompt library:**
  `packages/duecare-llm-chat/src/duecare/chat/harness/_examples.json`
  (587 corridor-grounded synthetic prompts)

## Anti-patterns to reject

- Creating `.ipynb` files in `kaggle/*/` (preview wrappers belong
  only in `_archive/kaggle-notebook-previews-2026-05-11/`).
- Adding `DATASET_SLUG = "duecare-...-wheels"` constants without the
  `# DEPRECATED 2026-05-11 (GitHub-only)` prefix.
- Walking `Path("/kaggle/input").rglob("*.whl")` for DueCare packages.
  Model weights still attach via `model_sources` in
  `kernel-metadata.json`; only the **DueCare package wheels** go via
  GitHub.
- Loading two models in a single kernel run (Kaggle T4 16GB GPU
  memory budget).
- Live cross-kernel links ("notebook A links directly to notebook
  B's output"). Use Add Data + bundle uploads instead.
- Using moving git refs (`main`, `master`, `HEAD`) in any pinned URL.
  Always pin to an immutable commit SHA, tag, or release version.

## How agents should use this doc

When a new Claude Code session opens, the auto-loaded `CLAUDE.md`
already references the conservative-pass checkpoint and the
13-folder-but-flexible roster. **Before editing any
`kaggle/A-*/kernel.py` file**, read this doc to confirm:

1. Which slot the kernel currently occupies in the canonical ladder
   (status section above).
2. Which reference implementation matches the slot's pattern
   (baseline runner / harnessed runner / upload+compare /
   synth data / trainer).
3. Which hard rules apply (all 7 always apply).
4. Whether the slot needs a folder rename (use `git mv` only with
   Taylor's approval).

Then make the edit, run validation (AST parse + public-surface
audit), and commit with a message that updates the build status
section above to flip the relevant pending slot to committed with
the new commit SHA.
