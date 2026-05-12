# DueCare — Jailbroken-Gemma comparison (#A10 appendix)

> AI infrastructure to combat migrant-worker exploitation. This appendix: proves safety lives in the runtime, not the weights, by harnessing abliterated Gemma variants.

<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Comparison playground for testing whether the DueCare runtime harness still helps when the underlying Gemma variant is less safety-aligned. |
| **What it does** | Runs the familiar 4-toggle chat UI against configured abliterated, cracked, or uncensored Gemma-family variants. |
| **Demo path** | Load a supported variant, send the same adversarial prompt with harness layers on, and compare behavior with the stock baseline. |
| **Audience** | Researcher. |
| **Inputs** | Multiple Gemma 4 variants attached (incl. abliterated / cracked variants); one variant selected per run via env var. |
| **Outputs** | Jailbroken-model responses, harness-layer traces, and adversarial comparison evidence. |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, grading-lift appendix, and public website. |

**Same chat UI as appendix notebook A02 (chat-playground-with-grep-rag-tools)**
— same 4 toggle tiles (Persona / GREP / RAG / Tools), same Pipeline
modal, same Persona library — but loads an **abliterated, cracked, or
uncensored Gemma 4 variant** instead of Google's stock instruct model.

The point: demonstrate that the DueCare safety harness still works
even when the underlying model has had its refusal directions
ablated. The safety isn't in the weights — it's in the runtime
(GREP/RAG/Tools fire BEFORE Gemma sees the prompt; persona is
prepended every turn).

Built with Google's Gemma 4 (the underlying base architecture; the
abliterated/cracked weights are 3rd-party derivatives published on HF
Hub). Used in accordance with the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-jailbroken-models *(manual Kaggle publication target)* |
| **Title on Kaggle** | "DueCare Chat Playground Jailbroken Models" |
| **Slug** | `taylorsamarel/duecare-chat-playground-jailbroken-models` |
| **Wheels dataset** | `taylorsamarel/duecare-chat-playground-jailbroken-models-wheels` *(local wheels present; create/update dataset during manual Kaggle publish)* |
| **Models attached** | NONE (HF Hub download per JAILBROKEN_MODEL config) |
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
| **dealignai cracked 31B** *(default)* | 31B | `dealignai/Gemma-4-31B-JANG_4M-CRACK` |
| huihui-ai abliterated 26B-A4B | 26B-A4B | `huihui-ai/gemma-4-A4B-it-abliterated` |
| huihui-ai abliterated E4B | E4B | `huihui-ai/gemma-4-e4b-it-abliterated` |
| mlabonne abliterated E4B | E4B | `mlabonne/Gemma-4-E4B-it-abliterated` |
| AEON-7 uncensored 26B-A4B | 26B-A4B | `AEON-7/Gemma-4-A4B-it-Uncensored` |
| TrevorS abliteration | E4B | `TrevorS/gemma-4-abliteration` |

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
(`duecare-chat-playground-jailbroken-models-wheels`) is staged locally for Taylor's manual Kaggle upload.

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
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- **[#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)**
- [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).

---

## Cross-links

- **[DueCare Exploration Workbench (#01)](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)** -- the full chat playground with all 6 harness layers, 9-variant model picker, 4 grading modes, A/B compare, and every visualization in one place.
- **[Live demo (#02)](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)** -- focused public-hub walkthrough demonstrating the +56.5pp lift on a curated set of compound-indicator prompts.
- **[Next step -> A-11 grading-evaluation](https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation)** -- compare grading lift between stock + harnessed + jailbroken + harnessed-jailbroken.
- **[Public hub: duecare-ai.com](https://duecare-ai.com)** -- knowledge-pack registry, anonymized signal intake, public-source proposal intake, and the 5-lane audience showcase.
