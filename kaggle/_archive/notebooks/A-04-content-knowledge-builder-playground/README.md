# DueCare — Knowledge-builder sandbox + JSON export (#A04 appendix)

> AI infrastructure to combat migrant-worker exploitation. This appendix: turns public-source facts into Knowledge Pack proposals reusable downstream.

<!-- duecare:lane-label -->
> **Serves lanes:** 02 NGO & regulator · 05 Developer / integration partner

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Hands-on builder for turning public-source facts into DueCare knowledge blocks that downstream harness layers can reuse. |
| **What it does** | Lets users draft, validate, test, and export structured knowledge JSON without changing code. |
| **Demo path** | Open the builder, fill the tabs with synthetic or public-source facts, run optional Gemma testing, and export JSON. |
| **Audience** | NGO & regulator and Developer / integration partner. |
| **Inputs** | Gemma 4 IT variant + the bundled DueCare corpus (knowledge-pack rules and example prompts). |
| **Gemma 4 features** | Long-context document grounding: loads the bundled DueCare corpus into a single Gemma 4 context window without retrieval (128K window in practice). |
| **Outputs** | Validated knowledge-block JSON, optional Gemma test output, and reusable configuration material. |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, classifier dashboard, and public website. |

The HANDS-ON sandbox for **building** DueCare's knowledge base.
Pairs with `content-classification-playground`; both are
prerequisites for understanding what the polished `live-demo`
notebook does. The live-demo bundles classification AND
knowledge-building into one polished UI; these two playgrounds let
judges (and downstream NGO partners) work with each piece
independently first.

Built with Google's Gemma 4 (base model:
[google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)
and other IT variants). Used in accordance with the
[Gemma 4 license — Apache 2.0](https://ai.google.dev/gemma/apache_2).

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-content-knowledge-builder-playground *(manual Kaggle publication target)* |
| **Title on Kaggle** | "DueCare Content Knowledge Builder Playground" |
| **Slug** | `taylorsamarel/duecare-content-knowledge-builder-playground` |
| **Wheels dataset** | `taylorsamarel/duecare-content-knowledge-builder-playground-wheels` *(local wheels present; create/update dataset during manual Kaggle publish)* |
| **Models attached** | `google/gemma-4/Transformers/{e2b,e4b}-it/1` (optional) |
| **GPU** | NOT REQUIRED for the builder UI; GPU only needed if user clicks "ask Gemma" in the Test tab |
| **Internet** | ON (cloudflared tunnel) |
| **Secrets** | `HF_TOKEN` (only for the optional Gemma test) |
| **Expected runtime** | ~15 sec without Gemma; ~30 sec with E4B-it loaded |

## How this differs from `chat-playground-with-grep-rag-tools`

- **chat-playground-with-grep-rag-tools** is a CHAT UI with toggle
  tiles + Persona library + per-message custom rule additions. It's
  a CONSUMER of the harness for chat conversations. You drive it
  with messages; the knowledge base is mostly fixed.
- **THIS notebook** is a BUILDER. You don't chat — you EDIT the
  knowledge base inline. Add new GREP regex patterns; add new RAG
  documents; inspect the corridor fee caps, fee-camouflage labels,
  and NGO intake hotlines; test what fires on a sample text; export
  the full knowledge JSON for downstream use.

## The five tabs

1. **GREP rules** — add / remove regex-based detection rules.
   Fields: rule name, patterns (one regex per line), severity,
   citation, indicator, all-required-vs-any. Live table shows
   bundled + user rules with delete buttons.
2. **RAG corpus** — add / remove documents. BM25 index rebuilds
   automatically. Each doc has id, title, source, snippet (the
   chunk indexed).
3. **Tools (lookups)** — read-only view of the corridor fee caps,
   fee camouflage labels, and NGO intake hotlines. To update them,
   use Export → modify JSON → Import so the notebook keeps a clear
   audit trail for the edited knowledge pack.
4. **Test** — paste a sample text, see what fires across your
   edited knowledge base: GREP hits, RAG retrievals, the merged
   pre-context Gemma would receive. Optional "ask Gemma" button
   sends the merged prompt to Gemma 4 for a real response (requires
   GPU + HF_TOKEN).
5. **Export / Import** — download the full knowledge JSON; upload a
   modified one to override; reset to bundled built-ins.

## Minimal-deps mode

The builder logic is **pure Python** (regex matching + BM25 over
small corpora). The notebook works WITHOUT a GPU and WITHOUT loading
any LLM — perfect for downstream NGO partners who want to extend
DueCare for their corridor / domain on their laptop. Set
`ENABLE_GEMMA = False` at the top of the kernel to skip Gemma loading
entirely; the Test tab will still show GREP hits + RAG retrievals.

## Files in this folder

```
content-knowledge-builder-playground/
├── kernel.py            ← source-of-truth (paste into Kaggle)
├── kernel-metadata.json ← Kaggle kernel config
├── README.md            ← this file
└── wheels/              ← dataset-metadata.json + local wheels for manual Kaggle upload
```

## Status

**Built 2026-04-29.** Self-contained FastAPI builder UI with
cloudflared quick-tunnel auto-launch. The wheels dataset
(`duecare-content-knowledge-builder-playground-wheels`) needs 3
wheels uploaded: `duecare-llm-core`, `duecare-llm-models`,
`duecare-llm-chat`.

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md).
- **Focused live demo:** [#02 core: Live demo](../02-live-demo/README.md).
- **Natural next appendix:** [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A04 appendix — Knowledge-builder sandbox + JSON export**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#03 core: Video pitch (in-app slides + presenter remote)](../03-duecare-video-pitch/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- **[#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)**
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
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).

---

## Cross-links

- **[DueCare Exploration Workbench (#01)](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)** -- the full chat playground with all 6 harness layers, 9-variant model picker, 4 grading modes, A/B compare, and every visualization in one place.
- **[Live demo (#02)](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)** -- focused public-hub walkthrough demonstrating the +56.5pp lift on a curated set of compound-indicator prompts.
- **[Next step -> A-03 content-classification](https://www.kaggle.com/code/taylorsamarel/duecare-content-classification-playground)** -- use the knowledge base you just built to classify real recruitment content.
- **[Public hub: duecare-ai.com](https://duecare-ai.com)** -- knowledge-pack registry, anonymized signal intake, public-source proposal intake, and the 5-lane audience showcase.
