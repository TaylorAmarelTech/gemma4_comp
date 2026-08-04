# DueCare — Runtime vs weights safety study (#A10 appendix)

> AI infrastructure to combat migrant-worker exploitation. This appendix: shows that DueCare's safety behaviour comes from the runtime harness rather than the model's own refusal training, by measuring what still holds when that training is absent.

> **Defensive research, and it ships no model.** Safety-stripped derivatives of
> open-weight models exist whether or not this project acknowledges them. A
> deployment that leans on the base model's refusals is leaning on something an
> adversary can remove, so DueCare measures the case where it has been. This
> appendix names no such model, links to none, and downloads none: the operator
> supplies a checkpoint they are authorized to evaluate via
> `DUECARE_STRIPPED_MODEL`, and the kernel exits with instructions if it is unset.
> DueCare does not use, endorse, or distribute refusal-ablated Gemma weights.

<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Comparison playground for testing whether the DueCare runtime harness still helps when the underlying Gemma variant is less safety-aligned. |
| **What it does** | Runs the familiar 4-toggle chat UI against an operator-supplied Gemma-family checkpoint whose refusal training has been removed. |
| **Demo path** | Set `DUECARE_STRIPPED_MODEL`, send the same adversarial prompt with harness layers on, and compare behavior with the stock baseline. |
| **Audience** | Researcher. |
| **Inputs** | One operator-supplied checkpoint, named only in the operator's own environment. Nothing is bundled or downloaded by default. |
| **Gemma 4 features** | Side-by-side stock Gemma 4 IT vs a safety-stripped checkpoint; tests whether the lift claim survives the worst-case adversary. |
| **Outputs** | Harness-layer traces and adversarial comparison evidence. |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, grading-lift appendix, and public website. |

**Same chat UI as appendix notebook A02 (chat-playground-with-grep-rag-tools)**
— same 4 toggle tiles (Persona / GREP / RAG / Tools), same Pipeline
modal, same Persona library — but pointed at an operator-supplied
checkpoint instead of Google's stock instruct model.

The point: demonstrate that the DueCare safety harness still works even
when the underlying model's refusal training is absent. The safety isn't
in the weights — it's in the runtime (GREP/RAG/Tools fire BEFORE Gemma
sees the prompt; persona is prepended every turn). That is a claim about
DueCare's architecture, and the only way to test it is to remove the
weights-side guarantee and re-measure.

Built with Google's Gemma 4 as the underlying base architecture, used in
accordance with the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
Any third-party derivative checkpoint is supplied by the operator and is
neither distributed nor endorsed here.

| Field | Value |
|---|---|
| **Kaggle URL** | Not published. This appendix is retained in-repo as research provenance and is not part of the judge-facing submission surface. |
| **Title on Kaggle** | "DueCare A10 Runtime vs Weights Safety Study" *(if ever published; metadata is set to private)* |
| **Slug** | `taylorsamarel/duecare-a10-runtime-vs-weights-safety-study` |
| **Wheels dataset** | Local wheels present in `wheels/`; no public dataset. |
| **Models attached** | NONE. Operator supplies one via `DUECARE_STRIPPED_MODEL`; the kernel exits if unset. |
| **GPU** | T4 ×2 (default 31B variant; smaller variants run on a single T4) |
| **Internet** | ON (HF Hub download + cloudflared) |
| **Secrets** | `HF_TOKEN` recommended (HF Hub rate-limit avoidance) |
| **Expected runtime** | first run ~5-10 min (HF Hub download + load); subsequent ~30 sec |

## The 6 jailbroken variants the kernel supports

Edit the `JAILBROKEN_MODEL` constant at the top of the kernel to
switch. All loaded uniformly via Unsloth FastModel (same loader as
the live-demo's stock 31B):

| Variant | Size | HF slug |
|---|---|---|
| Operator-supplied checkpoint | any Gemma-architecture size | set via `DUECARE_STRIPPED_MODEL` |

This appendix deliberately ships **no list of safety-stripped models**. Naming
them would turn this file into a distribution index for exactly the weights the
study exists to defend against. Supply your own checkpoint, one you are
authorized to evaluate.

These variants come from your project's existing research kernels
(notebooks 185-189). They are 3rd-party derivatives of Google's
Gemma 4. Verify each repo's license and terms before re-publishing.

## What this notebook proves

1. Load a model that has been INTENTIONALLY uncensored (refusal
   directions ablated)
2. Toggle the DueCare harness OFF — observe that the model now responds
   to exploitation/trafficking scenarios with operational advice (no
   refusal, because we ablated it)
3. Toggle the harness ON — observe that the SAME model now produces
   citation-rich, NGO-referring responses
4. Conclusion: the harness's safety effect doesn't depend on the
   model's training-time refusals. Even an ablated model behaves
   safely when the runtime harness is wired.

This is the strongest possible "real, not faked" rubric demo: the
harness works on a HOSTILE input model.

## Files in this folder

```
chat-playground-jailbroken-models/
├── kernel.py              ← source-of-truth (paste into Kaggle)
├── kernel-metadata.json   ← Kaggle kernel config
├── README.md              ← this file
└── wheels/                ← dataset-metadata.json + local wheels for manual Kaggle upload
```

## Status

**Built 2026-04-29.** Loader uses the same Unsloth FastModel pattern
as `live-demo/kernel.py`. Same shutdown infrastructure as the other
7 server kernels (red floating button + `/shutdown` page +
`/api/shutdown` POST). Yellow "JAILBROKEN MODEL LOADED — refusals
ablated" banner (top-left) reminds the user this isn't a normal
playground. Wheels dataset
(`duecare-a10-runtime-vs-weights-safety-study-wheels`) is staged locally for Taylor's manual Kaggle upload.

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md).
- **Focused live demo:** [#02 core: Live demo](../02-live-demo/README.md).
- **Natural next appendix:** [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A10 appendix — Jailbroken-Gemma comparison**.

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
- **[#A10 appendix: Runtime vs weights safety study](../A-10-runtime-vs-weights-safety-study/README.md)**
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
- **[Next step -> A-11 grading-evaluation](https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation)** -- compare grading lift between stock + harnessed + jailbroken + harnessed-jailbroken.
- **[Public hub: duecare-ai.com](https://duecare-ai.com)** -- knowledge-pack registry, anonymized signal intake, public-source proposal intake, and the 5-lane audience showcase.
