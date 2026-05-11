# DueCare — Gemma generates evaluation prompts (#A06 appendix)
<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher

Appendix-style notebook. **Not** part of the core deployment flow —
this is the data-pipeline tool advanced users invoke when they want
to grow the evaluation corpus beyond the bundled 587 prompts and
25-row smoke set. The same kernel a research lab would adapt for
their own domain (medical misinformation, financial fraud, etc.).

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation *(manual publication pending)* |
| **Title on Kaggle** | "Duecare Prompt Generation" |
| **Slug** | `taylorsamarel/duecare-prompt-generation` |
| **Wheels dataset** | `taylorsamarel/duecare-prompt-generation-wheels` *(local wheels present; manual dataset publication pending)* |
| **Trafficking-prompts dataset** | `taylorsamarel/duecare-trafficking-prompts` (5 YAML rubrics — seed material) |
| **Models attached** | `google/gemma-4/Transformers/{e2b,e4b}-it/1` |
| **GPU** | T4 ×1 minimum (E4B-it default) |
| **Internet** | ON |
| **Secrets** | `HF_TOKEN` |
| **Expected runtime** | ~50-75 min for 50 prompts × 5 grades = 250 graded responses |

Built with Google's Gemma 4 (base model:
[google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)).
Used in accordance with the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).

## Why "appendix"

Three of the five core notebooks (chat-playground, chat-playground-with-grep-rag-tools,
gemma-content-classification-evaluation) are everything an end user
needs for deployment. The live-demo notebook is the user-facing live
URL judges click. **Bench-and-tune and prompt-generation are tools
for the people who want to *extend* the system** — they are
optional, not required.

This kernel sits in the appendix because:

1. Most Duecare deployments will use the bundled 587 prompts +
   smoke_25 benchmark; they won't need to generate new ones.
2. Generating prompts requires GPU + ~1 hour; the core notebooks
   load in 30 seconds.
3. The output (generated_prompts.jsonl, graded_responses.jsonl)
   feeds *into* the bench-and-tune notebook's SFT/DPO pipelines —
   so this is upstream of the (also appendix) bench-and-tune.

## What it does

End-to-end:

1. **Step 1 — Load source material.** Reads the 5 trafficking-prompts
   YAML rubrics (`business_framed_exploitation`,
   `financial_crime_blindness`, `jurisdictional_hierarchy`,
   `prompt_injection_amplification`, `victim_revictimization`).
   Falls back to a 3-scenario hardcoded list if the dataset isn't
   attached.
2. **Step 2 — Generate prompts.** For each seed scenario, prompts
   Gemma 4 to write a realistic 80-150 word adversarial test prompt
   in the voice of a perpetrator or confused intermediary. Writes
   the result in the same row shape as `smoke_25.jsonl` so the
   prompt plugs directly into the existing benchmark runner.
3. **Step 3 — Grade responses.** For each generated prompt, asks
   Gemma 4 to write five demonstration responses on a 0-4 scale
   (HARMFUL → BEST). Used as SFT/DPO training data downstream.

## Output

- `/kaggle/working/generated_prompts.jsonl` — N rows in the
  smoke_25 shape: `{id, category, locale, text, expected_verdict,
  expected_severity_min, expected_signals}`
- `/kaggle/working/graded_responses.jsonl` — N×5 rows:
  `{prompt_id, prompt_text, category, grade, grade_label,
  response}`
- `/kaggle/working/generation_log.json` — run summary

The two output JSONLs are designed to be exported back to a Kaggle
Dataset (`duecare-eval-results` or a new `duecare-generated-prompts`)
where the bench-and-tune notebook picks them up.

## Files in this folder

```
prompt-generation/
├── kernel.py            ← source-of-truth (paste into Kaggle)
├── notebook.ipynb       ← built artifact
├── kernel-metadata.json ← Kaggle kernel config
├── README.md            ← this file
└── wheels/              ← local wheels for Kaggle dataset upload
```

## Status

**Prototype appendix (2026-05-10).** The Phase 0 install + wheel
install + Gemma load paths are real and follow the same pattern as
`bench-and-tune` and `live-demo`. The two LLM-driven steps
(generation, grading) use deliberately simple starter templates —
research users should replace `PROMPT_GENERATION_TEMPLATE` and
`_grading_template` with patterns optimized for their domain.

The local wheels are present in this folder for the manual Kaggle
dataset publication step. Do not auto-push them; Taylor publishes the
kernel and wheel dataset manually.

---

<!-- duecare:kernel-footer -->

### All DueCare notebooks

You are here: **#A06 appendix — Gemma generates evaluation prompts**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Original 4-toggle subset playground](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- **[#A06 appendix: Gemma generates evaluation prompts](../A-06-prompt-generation/README.md)**
- [#A07 appendix: Unsloth fine-tune + GGUF export pipeline](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- [#A11 appendix: Grading-lift regenerator](../A-11-grading-evaluation/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
