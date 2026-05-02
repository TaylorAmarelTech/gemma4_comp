# Duecare Chat Playground — Jailbroken Models (Appendix Notebook A5)

**Same chat UI as core notebook 2 (chat-playground-with-grep-rag-tools)**
— same 4 toggle tiles (Persona / GREP / RAG / Tools), same Pipeline
modal, same Persona library — but loads an **abliterated, cracked, or
uncensored Gemma 4 variant** instead of Google's stock instruct model.

The point: demonstrate that the Duecare safety harness still works
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
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-jailbroken-models *(TBD — kernel needs creation)* |
| **Title on Kaggle** | "Duecare Chat Playground Jailbroken Models" |
| **Slug** | `taylorsamarel/duecare-chat-playground-jailbroken-models` |
| **Wheels dataset** | `taylorsamarel/duecare-chat-playground-jailbroken-models-wheels` *(TBD — needs upload)* |
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
2. Toggle the Duecare harness OFF — observe that the model now responds
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
├── notebook.ipynb         ← built artifact
├── kernel-metadata.json   ← Kaggle kernel config
├── README.md              ← this file
└── wheels/                ← dataset-metadata.json (3 wheels TBD)
```

## Status

**Built 2026-04-29.** Loader uses the same Unsloth FastModel pattern
as `live-demo/kernel.py`. Same shutdown infrastructure as the other
7 server kernels (red floating button + `/shutdown` page +
`/api/shutdown` POST). Yellow "JAILBROKEN MODEL LOADED — refusals
ablated" banner (top-left) reminds the user this isn't a normal
playground. Wheels dataset
(`duecare-chat-playground-jailbroken-models-wheels`) needs upload.
