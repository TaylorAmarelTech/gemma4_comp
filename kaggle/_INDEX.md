# Kaggle kernel index — submission roster

> **Generated:** 2026-05-11. Last refreshed: 2026-05-12.
> Machine-readable companion to
> [`kaggle/README.md`](./README.md) and
> [`docs/FOR_KAGGLE_JUDGES.md`](../docs/FOR_KAGGLE_JUDGES.md).
> Every row reflects what's in this directory tree right now.

> **Roster expansion (2026-05-12):** the original "2 core + 11
> appendix = 13" lock-in expanded with website-extension slots
> (A-12 .. A-20) and a new main `03-duecare-video-pitch` notebook.
> The 23-row table below is the current truth. See
> [`docs/appendix_experiment_ladder.md`](../docs/appendix_experiment_ladder.md)
> for the slot definitions including the website-aligned extensions.

## How to run a kernel without publishing to Kaggle

These kernels are **not auto-published** right now. To run any of
the 23 locally on Kaggle yourself:

1. Open <https://kaggle.com> → New Notebook (Python) in the Kaggle UI.
2. Kernel settings → enable GPU (T4 is fine for E2B/E4B; 2×T4 or
   P100 for 31B / 26B-A4B).
3. Kernel settings → **enable Internet** (required — DueCare installs
   directly from GitHub; no Kaggle wheel datasets are used).
4. **Add model** (only if the row needs Gemma 4 weights) → search
   `google/gemma-4` and pick the variant the kernel expects.
5. Open the matching `kernel.py` from this folder, copy its full
   contents, paste into a single Kaggle code cell.
6. Run All. The kernel installs DueCare packages from GitHub
   (release wheels first, source-install fallback) — no
   `Add data → wheels dataset` step is required.

> **Policy as of 2026-05-11:** all 13 kernels install DueCare packages
> directly from `github.com/TaylorAmarelTech/gemma4_comp` (release
> wheels at `/releases/download/v{VERSION}/...whl` first, then
> `git+https://...@<commit-sha>#subdirectory=packages/<pkg>` as
> fallback). Attached `*-wheels` Kaggle datasets are deprecated and
> have been removed from every `kernel-metadata.json`'s
> `dataset_sources`. Notebook 01's `install_chat_wheels()` is the
> canonical reference implementation.

Notebook wrappers are archived under
[`../_archive/kaggle-notebook-previews-2026-05-11/`](../_archive/kaggle-notebook-previews-2026-05-11/).
The active submission folders intentionally keep `kernel.py` as the only runnable source.

**Canonical appendix structure (2026-05-11 lock-in):** the 11
appendix slots A-01…A-11 form a reproducible end-to-end
model-improvement pipeline. **Before editing any
`kaggle/A-*/kernel.py`**, read
[`../docs/appendix_experiment_ladder.md`](../docs/appendix_experiment_ladder.md)
for the slot definitions, hard rules, and build status. The
cross-kernel artifact contract that A-03 / A-08 consume is in
[`../docs/appendix_artifact_schema.md`](../docs/appendix_artifact_schema.md).

## Build status — 2 core + 11 appendix = 13 submission kernels

**Submission shape (2026-05-05):** judges land on the unified
`01-duecare-exploration-workbench` kernel to see every capability surface,
then proceed to `02-live-demo` for the focused thesis demonstration.
The 11 specialised kernels (A1-A11) remain as appendix for depth
signal. Folder names use the `01-` / `02-` / `A-01-` ... `A-11-`
numbered prefix convention so the `ls kaggle/` listing reads in the
canonical presentation order.

**Training appendix path:** `A-06 Prompt Generation -> A-07 Bench and
Tune -> A-11 Grading Evaluation` has two distinct meanings. A-06 creates
synthetic training/evaluation material in two tracks: SafetyJudge
anti-exploitation reasoning and PrivacyRedactor anonymization. A-07 trains
and benchmarks stock Gemma 4 versus the fine-tuned SafetyJudge adapter,
with privacy-redaction data kept as a separate adapter/eval track. A-11 is
not a fine-tuned-model benchmark; it holds weights constant and regenerates
the runtime harness OFF/ON lift.

**Kaggle handoff rule:** assume one loaded model per kernel run. A-06
outputs `duecare_a06_to_a07_manifest.json` and
`duecare_a06_to_a07_bundle.zip`; publish or attach those outputs as Kaggle
Datasets, then use Kaggle Add Data in A-07. The served A-06 UI tells the
reader to open the printed Cloudflare URL and download the bundle; the served
A-07 UI accepts multiple ZIP/JSONL/JSON uploads into an explicit staging
folder for rerun. A-07 never depends on a live link back to A-06 and can merge
multiple attached/staged A-06 bundles, including separate stock-teacher and
abliterated-adversary generation runs. A-06 prompt tests carry both the legacy
rubric labels (`HARMFUL` to `BEST`) and the review labels (`WORST`, `BAD`,
`NEUTRAL`, `GOOD`, `BEST`).

| # | Folder | Files | Wheels (dataset slug) | Kernel slug | Publish |
|---|---|:-:|---|---|:-:|
| **1** | [`01-duecare-exploration-workbench/`](./01-duecare-exploration-workbench/) ★ omni playground | ✓ 3 (script) | `taylorsamarel/duecare-harness-chat-wheels` ✓ live | `taylorsamarel/duecare-exploration-workbench` | pending |
| **2** | [`02-live-demo/`](./02-live-demo/) ★ focused live demo | ✓ kernel | `taylorsamarel/duecare-live-demo-wheels` ✓ live | `taylorsamarel/duecare-live-demo` | live |
| A1 | [`A-01-chat-playground/`](./A-01-chat-playground/) (baseline, harness OFF) | ✓ kernel | `taylorsamarel/duecare-chat-playground-wheels` ✓ live | `taylorsamarel/duecare-chat-playground` | live |
| A2 | [`A-02-chat-playground-with-grep-rag-tools/`](./A-02-chat-playground-with-grep-rag-tools/) (4-toggle harness) | ✓ kernel | `taylorsamarel/duecare-chat-playground-with-grep-rag-tools-wheels` ✓ live | `taylorsamarel/duecare-chat-playground-with-grep-rag-tools` | live |
| A3 | [`A-03-content-classification-playground/`](./A-03-content-classification-playground/) | ✓ kernel | `taylorsamarel/duecare-content-classification-playground-wheels` ✓ live | `taylorsamarel/duecare-content-classification-playground` | pending |
| A4 | [`A-04-content-knowledge-builder-playground/`](./A-04-content-knowledge-builder-playground/) | ✓ kernel | `taylorsamarel/duecare-content-knowledge-builder-playground-wheels` ✓ live | `taylorsamarel/duecare-content-knowledge-builder-playground` | pending |
| A5 | [`A-05-gemma-content-classification-evaluation/`](./A-05-gemma-content-classification-evaluation/) | ✓ kernel | `taylorsamarel/duecare-gemma-content-classification-evaluation-wheels` ✓ live | `taylorsamarel/duecare-gemma-content-classification-evaluation` | live |
| A6 | [`A-06-prompt-generation/`](./A-06-prompt-generation/) (two-track synthetic data) | ✓ kernel | `taylorsamarel/duecare-prompt-generation-wheels` ✓ live | `taylorsamarel/duecare-prompt-generation` | pending |
| A7 | [`A-07-bench-and-tune/`](./A-07-bench-and-tune/) (adapter trainer + new-model benchmark) | ✓ kernel | `taylorsamarel/duecare-bench-and-tune-wheels` ✓ live | `taylorsamarel/duecare-bench-and-tune` | pending |
| A8 | [`A-08-research-graphs/`](./A-08-research-graphs/) (Plotly graphs) | ✓ kernel | `taylorsamarel/duecare-research-graphs-wheels` ✓ live | `taylorsamarel/duecare-research-graphs` | pending |
| A9 | [`A-09-chat-playground-with-agentic-research/`](./A-09-chat-playground-with-agentic-research/) (Playwright web search) | ✓ kernel | `taylorsamarel/duecare-chat-playground-with-agentic-research-wheels` ✓ live | `taylorsamarel/duecare-chat-playground-with-agentic-research` | pending |
| A10 | [`A-10-chat-playground-jailbroken-models/`](./A-10-chat-playground-jailbroken-models/) (abliterated baselines) | ✓ kernel | `taylorsamarel/duecare-chat-playground-jailbroken-models-wheels` ✓ live | `taylorsamarel/duecare-chat-playground-jailbroken-models` | pending |
| A11 | [`A-11-grading-evaluation/`](./A-11-grading-evaluation/) (runtime harness lift regenerator) | ✓ kernel | `taylorsamarel/duecare-grading-evaluation-wheels` ✓ live | `taylorsamarel/duecare-grading-evaluation` | pending |
| **3** | [`03-duecare-video-pitch/`](./03-duecare-video-pitch/) ★ in-app slides + setup mode + presenter remote | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-video-pitch` | pending |
| A12 | [`A-12-pii-fine-tune-eval/`](./A-12-pii-fine-tune-eval/) (PrivacyRedactor LoRA fine-tune + eval) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-pii-fine-tune-eval` | pending |
| A13 | [`A-13-multimodal-document-analyzer/`](./A-13-multimodal-document-analyzer/) (image + document analyzer) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-multimodal-document-analyzer` | pending |
| A14 | [`A-14-on-device-export/`](./A-14-on-device-export/) (LoRA merge -> GGUF + LiteRT) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-on-device-export` | pending |
| A15 | [`A-15-ugc-batch-moderator/`](./A-15-ugc-batch-moderator/) (Lane 01 platform-safety batch moderation) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-ugc-batch-moderator` | pending |
| A16 | [`A-16-ngo-local-kb/`](./A-16-ngo-local-kb/) (Lane 02 NGO local-KB + salted-hash entity store) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-ngo-local-kb` | pending |
| A17 | [`A-17-knowledge-pack-builder/`](./A-17-knowledge-pack-builder/) (versioned pack builder + verifier) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-knowledge-pack-builder` | pending |
| A18a | [`A-18-demo-replay/`](./A-18-demo-replay/) (static demo replay, no inference) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-demo-replay` | pending |
| A18b | [`A-18-sentinel-research-monitor/`](./A-18-sentinel-research-monitor/) (sentinel pack-diff monitor) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-sentinel-research-monitor` | pending |
| A19 | [`A-19-multilingual-demo/`](./A-19-multilingual-demo/) (5-language scenario playback) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-multilingual-demo` | pending |
| A20 | [`A-20-privacy-boundary/`](./A-20-privacy-boundary/) (raw-vs-redacted visualization) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-privacy-boundary` | pending |
| A21 | [`A-21-long-context-demo/`](./A-21-long-context-demo/) (Gemma 4 128K cross-statute reasoning) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-a-21-long-context-demo` | pending |
| A22 | [`A-22-streaming-demo/`](./A-22-streaming-demo/) (Gemma 4 SSE token streaming at real latencies) | ✓ kernel | (GitHub install only) | `taylorsamarel/duecare-a-22-streaming-demo` | pending |

> **Note on slugs vs folders.** The folder name (`01-duecare-exploration-workbench/`)
> is local organization. The Kaggle kernel slug is set by the `id` field
> inside `kernel-metadata.json`; for kernel #1 it is now
> `taylorsamarel/duecare-exploration-workbench`. The wheel dataset still uses
> the compatibility slug `taylorsamarel/duecare-harness-chat-wheels`; keep
> that dataset slug until the wheel dataset is deliberately republished.

**Files** column legend. Active submission folders are script kernels:
`kernel.py + kernel-metadata.json + README.md + wheels/`.

| Symbol | Meaning |
|:-:|---|
| ✓ kernel | Script kernel includes `kernel.py`, metadata, README, and wheels. |
| partial | One or more required files missing |
| — | Folder doesn't exist locally |

**Wheels**: each kernel includes a per-purpose `wheels/` subdirectory
with the wheel files it `pip install`s at kernel start. All are
present locally as of 2026-05-01.

**Publish**: `live` = the slug returned 200 on the last
`scripts/verify_kaggle_urls.py` run. `pending` = built locally,
ready to push, gated by Kaggle's daily push rate-limit.

## Per-kernel canonical files

Each submission kernel directory holds these files:

| File | Required? | Purpose |
|---|---|---|
| `kernel.py` | always | Source-of-truth Python — what runs on Kaggle |
| `kernel-metadata.json` | always | Kaggle CLI metadata (slug, title, attached datasets, GPU/CPU) |
| `README.md` | always | Per-kernel overview (purpose, runtime, what to look for) |
| `notebook.ipynb` | no | Archived preview wrapper only; not active source. |

Folders with `kernel-metadata.json` set to `kernel_type: script`
publish `kernel.py` directly to Kaggle. Active folders must not include
`notebook.ipynb`; historical wrappers live in `_archive/kaggle-notebook-previews-2026-05-11/`.

The `wheels/` subdirectory holds the wheels uploaded as a Kaggle
dataset attached to the kernel. The kernel installs from the
attached dataset path at startup.

## Other directories under kaggle/

| Path | Status | Notes |
|---|---|---|
| `kaggle/_archive/` | archived | Pre-canonical-layout legacy; superseded |
| `kaggle/kernels/` | archived | Former generated/research notebook mirrors moved to `_archive/kaggle-notebook-previews-2026-05-11/`; NOT part of the 13-folder judge-facing submission. |
| `kaggle/models/` | reference | Model card YAML + HF Hub push helpers |
| `kaggle/shared-datasets/` | reference | Shared assets pulled by multiple kernels |
| `kaggle/README.md` | live | Human-readable overview of the 2 core + 11 appendix submission shape |

## How to update this file

Re-run the audit when kernels are added, deleted, or pushed:

```bash
# Quick audit of file completeness across all 13 numbered folders
for d in kaggle/01-* kaggle/02-* kaggle/A-*; do
   count=$(ls -1 "$d" | grep -E "kernel.py|kernel-metadata.json|README.md|^wheels$" | wc -l)
  ktype=$(grep -o '"kernel_type"[[:space:]]*:[[:space:]]*"[^"]*"' "$d/kernel-metadata.json" 2>/dev/null | head -1)
  echo "$d: $count files ($ktype)"
done
# Script kernels should report 4: kernel.py, metadata, README, and wheels/.

# Verify Kaggle live URLs (manual, not part of CI)
python scripts/verify_kaggle_urls.py

# Prepare v3.16 wheel dataset actions. Keep non-dry-run publishing manual.
python scripts/push_v316_wheels.py --dry-run
```

Only run a non-dry-run Kaggle dataset/kernel command after Taylor explicitly
requests publication.

Update the **Publish** column whenever a `kaggle kernels push`
returns 200 + the corresponding `kaggle datasets create / version`
returns 200.
