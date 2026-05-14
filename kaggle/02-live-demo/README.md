# DueCare — Live demo (focused walkthrough) (#02 core)

> AI infrastructure to combat migrant-worker exploitation. This core kernel: focused product walkthrough proving the +56.5pp lift judges will see in the video.

<!-- duecare:lane-label -->
> **Serves lanes:** 01 Platform safety · 02 NGO & regulator · 03 Individual worker · 04 Researcher · 05 Developer / integration partner

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Focused live demonstration for judges, using the same DueCare workbench shell and public-hub story as the recorded video. |
| **What it does** | Runs the FastAPI server, the 22-slide walkthrough, and the full safety-harness pipeline from prescan through Gemma 4 verdict and audit trail. |
| **Demo path** | Run the kernel, open the cloudflared URL, and follow the deck from the human scenario into the live workbench and hub views. |
| **Audience** | Platform safety, NGO & regulator, Individual worker, Researcher, and Developer / integration partner. |
| **Inputs** | Gemma 4 IT variant (e4b-it default) + the bundled v3.16 harness corpus. No external data attachments required. |
| **Gemma 4 features** | Instruction-following at small scale (E4B IT default) plus full harness orchestration; the +56.5pp lift on compound-indicator prompts is the headline Technical Depth claim. |
| **Outputs** | Live demo page, Workbench pages, response evidence, public-hub routes, and audit-trail views. |
| **Cross-links** | Use the quick links at the bottom for the full workbench, grading appendix, and public website. |

The user-facing live URL judges click. FastAPI server + cloudflared
quick-tunnel + guided walkthrough + Workbench. Runs the **full DueCare
safety-harness pipeline**: heuristic prescan → GREP knowledge base
→ RAG retrieval → tool calls → Gemma 4 verdict → audit trail.

Built with Google's Gemma 4 (base model:
[google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)
and other IT variants). Used in accordance with the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-live-demo |
| **Title on Kaggle** | "DueCare Live Demo" |
| **Slug** | `taylorsamarel/duecare-live-demo` |
| **Wheels dataset** | `taylorsamarel/duecare-live-demo-wheels` (16 wheels, ~6.2 MB) |
| **Trafficking-prompts dataset** | not required (the live demo uses the embedded evidence DB only) |
| **Models attached** | `google/gemma-4/Transformers/{e2b,e4b,26b-a4b,31b}-it/1` (all four IT variants) |
| **GPU** | T4 ×2 (required) |
| **Internet** | ON (required for cloudflared tunnel + HF Hub auth) |
| **Secrets** | `HF_TOKEN` Kaggle Secret |
| **Expected runtime** | ~30 s for E4B; ~3-4 min for 31B (one-time install) |

## Files in this folder

```
live-demo/
├── kernel.py            ← source-of-truth (paste into Kaggle)
├── kernel-metadata.json ← built artifact (rewritten by push_kaggle_demo.py)
├── README.md            ← this file
└── wheels/              ← 16 .whl files + dataset-metadata.json
```

## Publishing options

### A. Paste-into-Kaggle (preferred — Taylor runs this)

1. Open https://www.kaggle.com/code/taylorsamarel/duecare-live-demo in
   the editor.
2. Replace the single code cell with the contents of
   [`kernel.py`](./kernel.py) (CTRL+A → paste).
3. Confirm the side panel shows: GPU T4 ×2 · Internet ON · the four
   Gemma 4 model attachments · `taylorsamarel/duecare-live-demo-wheels`
   dataset attached.
4. Save & Run All. The cloudflared URL appears within ~30 s (E4B) or
   ~3 min (31B).

### B. Script-driven push (only when explicitly approved)

```bash
# Build wheels first (writes to dist/, then copy the live-demo subset
# into kaggle/live-demo/wheels/ if not already current)
python scripts/build_all_wheels.py --no-isolation --clean

# Version the wheels dataset + push the kernel
python scripts/push_kaggle_demo.py --kernel demo --enable-gpu false
```

The script reads from `kaggle/live-demo/wheels/*.whl` for the dataset
upload (not from `dist/`), so the live-demo bundle stays curated.

## Wheels included (16)

`duecare-llm`, `duecare-llm-agents`, `duecare-llm-benchmark`,
`duecare-llm-cli`, `duecare-llm-core`, `duecare-llm-domains`,
`duecare-llm-engine`, `duecare-llm-evidence-db`,
`duecare-llm-models`, `duecare-llm-nl2sql`,
`duecare-llm-publishing`, `duecare-llm-research-tools`,
`duecare-llm-server`, `duecare-llm-tasks`, `duecare-llm-training`,
`duecare-llm-workflows`.

## What this notebook is NOT

- **Not the science write-up.** Methodology + benchmark + Unsloth SFT/DPO
   live in [`../A-07-bench-and-tune/`](../A-07-bench-and-tune/README.md).
- **Not a chat playground.** A pure Gemma 4 chat UI (no harness) lives
   in [`../A-01-chat-playground/`](../A-01-chat-playground/README.md).

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md).
- **Focused live demo:** this notebook.
- **Natural next appendix:** [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#02 core — Live demo (focused walkthrough)**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- **[#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)**
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

---

## Cross-links

- **[DueCare Exploration Workbench (#01)](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)** -- the full chat playground with all 6 harness layers, 9-variant model picker, 4 grading modes, A/B compare, and every visualization in one place.
- **[Live demo (#02)](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)** -- focused public-hub walkthrough demonstrating the +56.5pp lift on a curated set of compound-indicator prompts.
- **[Next step -> DueCare Exploration Workbench (#01)](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)** -- open the full chat playground with all 6 harness layers and 9 model variants.
- **[Public hub: duecare-ai.com](https://duecare-ai.com)** -- knowledge-pack registry, anonymized signal intake, public-source proposal intake, and the 5-lane audience showcase.
