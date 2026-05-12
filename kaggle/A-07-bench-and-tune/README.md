# DueCare — Adapter training + new-model benchmark (#A07 appendix)
<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher · 05 Developer / integration partner

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Methodology notebook showing how DueCare turns harness and A6 synthetic data into task-specific Gemma 4 LoRA adapters. |
| **What it does** | Runs a stock benchmark, prepares SFT and DPO pairs, fine-tunes a SafetyJudge adapter, re-benchmarks the fine-tuned model, exports GGUF, and prepares HF Hub outputs. |
| **Demo path** | Attach A6 bundles with Add Data, run the pipeline, open the printed Cloudflare dashboard, review phase status, and use the A6 upload panel to stage multiple ZIP/JSONL artifacts for rerun. |
| **Audience** | Researcher and Developer / integration partner. |
| **Outputs** | Training data, stock-vs-fine-tuned evaluation deltas, SafetyJudge LoRA/fine-tuned artifacts, GGUF export path, PrivacyRedactor data pointers, and HF Hub metadata. |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, grading-lift appendix, and public website. |

Appendix-style notebook. **Not** part of the core deployment flow —
this is the methodology / science piece for advanced users who want
to fine-tune Gemma 4 on their own corpus. Smoke benchmark (stock
Gemma 4) → Unsloth SFT (LoRA on harness/A6 prompt-response pairs) →
DPO (chosen=best/harness-on, rejected=raw or harmful/incomplete) →
re-benchmark the fine-tuned adapter → GGUF export → HF Hub push of the
fine-tuned weights.

The intended model layout is **one Gemma 4 backbone with two routed
DueCare adapters**, not one blended model:

- **SafetyJudge adapter:** anti-exploitation response quality, legal
  grounding, refusal behavior, hotline/actionability. This is the default
  SFT/DPO path in this notebook.
- **PrivacyRedactor adapter:** anonymization/redaction behavior for
  server-side or local intake. A6 prepares the composite privacy rows;
  deterministic PII gates still run before and after the model.

Kaggle memory rule: A7 loads **one model** for the run. It does not call
back into A6 or load a second generator model. Instead, attach one or more
A6 output datasets via Kaggle Add Data. A7 searches `/kaggle/input` for
DueCare/A6 bundle ZIPs, extracts each bundle, and merges the contained
`graded_responses.jsonl` rows. It also watches
`/kaggle/working/a06_uploaded_bundles`, where the served dashboard can
stage multiple ZIP/JSON/JSONL uploads before a rerun. This supports a
diverse corpus without risky in-notebook model swapping: run A6 separately
with `stock_harness_teacher`, `abliterated_adversary`, and human-reviewed
profiles, then attach or upload all bundles here.

Pairs with the [`prompt-generation`](../A-06-prompt-generation/README.md) appendix
notebook (which produces the SFT/DPO training data) to form the
"extend DueCare to your own domain" workflow.

Built with Google's Gemma 4 (base model:
[google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)).
Fine-tuned weights are pushed to HF Hub under
`taylorscottamarel/duecare-gemma-4-*` slugs with the required Gemma
attribution. Used in accordance with the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune |
| **Title on Kaggle** | "DueCare Bench and Tune" |
| **Slug** | `taylorsamarel/duecare-bench-and-tune` |
| **Wheels dataset** | `taylorsamarel/duecare-bench-and-tune-wheels` (6 wheels, ~390 KB) |
| **Evaluation results dataset** | `taylorsamarel/duecare-eval-results` (write target — per-run JSON exports of stock vs SFT vs DPO deltas) |
| **Models attached** | `google/gemma-4/Transformers/{e2b,e4b,26b-a4b,31b}-it/1` (all four IT variants) |
| **GPU** | T4 ×2 (required for Unsloth fine-tune) |
| **Internet** | ON (required for HF Hub push of fine-tuned weights) |
| **Secrets** | `HF_TOKEN` Kaggle Secret with write scope |
| **Expected runtime** | ~30-50 min end-to-end (E4B SFT + DPO + GGUF + HF push) |

## A6 artifact handoff

The reliable path is still Kaggle-native:

1. Run A6 and open the printed `[workbench] https://...trycloudflare.com`
  URL.
2. Download `duecare_a06_to_a07_bundle.zip`.
3. Publish/upload that ZIP as a Kaggle Dataset and attach it to A7 with
  **Add Data before Run All**.
4. Repeat for multiple A6 profiles if needed, for example one stock/harness
  bundle and one abliterated-adversary bundle.

The A7 dashboard also includes an **A-06 bundle handoff** panel. It accepts
multiple `.zip`, `.jsonl`, and `.json` uploads and stages them in
`/kaggle/working/a06_uploaded_bundles`. Because the dashboard starts after
the compute phases finish, uploads affect training only after rerunning A7.

Trust policy: A7 treats `stock_harness_teacher` and `human_curated_review`
as trusted sources for **Best** SFT examples. `abliterated_adversary` rows are
kept for Bad/Worst contrast, DPO rejected rows, and evaluator stress tests;
do not promote them to Best labels without human or harness review. Only use
A6 bundles from trusted runs, because generated training bundles can poison a
fine-tune just like any other untrusted dataset.

## Files in this folder

```
bench-and-tune/
├── kernel.py            ← source-of-truth (1230 lines, paste into Kaggle)
├── kernel-metadata.json ← Kaggle kernel config (slug + dataset/model attachments)
├── README.md            ← this file
└── wheels/              ← 6 .whl files + dataset-metadata.json
```

## Status

The wheels dataset is current (uploaded 2026-04-28). The kernel
source (`kernel.py`) is built (2026-04-29) — paste-into-Kaggle ready.
End-to-end pipeline: stock benchmark → SFT (LoRA on harness-distilled
prompt/response pairs) → DPO (chosen=harness-on, rejected=harness-off)
→ re-benchmark → GGUF Q8_0 export → HF Hub push.

## Training data spine

Yes: the Persona + GREP + RAG + Tools harness traces are intended to
become training data, but through SFT + DPO-style preference
optimization rather than an online RL loop.

| Source | Used for | Shape | Privacy gate |
|---|---|---|---|
| Harness-distilled traces | SFT | bare prompt → cited harness answer | public/composite/anonymized only |
| Raw Gemma vs harness-on answers | DPO | prompt + chosen + rejected | same prompt allowlist as SFT |
| A06 stock/harness generated graded responses | SFT or DPO chosen rows | prompt + 0-4 response ladder | synthetic/composite rows |
| A06 abliterated generated rows | DPO rejected rows + adversarial eval | harmful/incomplete prompts/responses | synthetic/composite rows, review before Best use |
| A06 anonymization gold rows | PrivacyRedactor SFT/eval | composite intake + redaction plan | placeholders only, no raw PII |
| A11 grading lift outputs | Candidate mining only | OFF/ON responses + grades | benchmark prompts only |

The notebook writes `/kaggle/working/sft_dataset.jsonl` in chat format
and `/kaggle/working/dpo_dataset.jsonl` as preference pairs. If A6
artifacts are attached, those rows are used first; otherwise the notebook
falls back to bundled harness-distilled examples. This is the training
answer to the "can RAG + GREP + persona responses become reinforcement
data?" question: treat them as supervised and preference data first. Only
call it RL if a later notebook adds PPO/GRPO or another online
reward-optimization step.

## Wheels included (6)

`duecare-llm-core`, `duecare-llm-models`, `duecare-llm-domains`,
`duecare-llm-tasks`, `duecare-llm-benchmark`, `duecare-llm-training`.

Notably absent: server, engine, evidence-db, agents, workflows,
publishing — none of which are needed for benchmarking + fine-tuning.

## HF Hub push targets (planned)

When the kernel runs `model.push_to_hub_*()` it should push under these
slugs (per `reference_kaggle_naming_convention.md` memory):

- `taylorscottamarel/duecare-gemma-4-E4B-it-SafetyJudge-v0.1.0`
  (SFT LoRA adapter)
- `taylorscottamarel/duecare-gemma-4-E4B-it-SafetyJudge-DPO-v0.1.0`
  (DPO on top of SFT)
- `taylorscottamarel/duecare-gemma-4-E4B-it-PrivacyRedactor-v0.1.0`
  (separate privacy/anonymization LoRA adapter; server/local intake path)
- `taylorscottamarel/duecare-gemma-4-E4B-it-SafetyJudge-v0.1.0-GGUF`
  (Q8_0 GGUF export for llama.cpp track)

Model cards MUST include the "Built with Google's Gemma" attribution
+ a link to `huggingface.co/google/gemma-4-<variant>-it` per the
Gemma terms of use.

## Publishing options

### A. Paste-into-Kaggle (when kernel exists)

1. Open https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune
2. Replace the single code cell with [`kernel.py`](./kernel.py) once
   built.
3. Confirm side panel attachments listed in the table above.
4. Save & Run All.

### B. Script-driven push (when explicitly approved)

```bash
python scripts/push_kaggle_demo.py --kernel bench-and-tune \
    --enable-gpu false
```

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

You are here: **#A07 appendix — Adapter training + new-model benchmark**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- **[#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)**
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).

---

## Cross-links

- **[DueCare Exploration Workbench (#01)](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)** -- the full chat playground with all 6 harness layers, 9-variant model picker, 4 grading modes, A/B compare, and every visualization in one place.
- **[Live demo (#02)](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)** -- focused public-hub walkthrough demonstrating the +56.5pp lift on a curated set of compound-indicator prompts.
- **[Next step -> A-11 grading-evaluation](https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation)** -- regenerate the runtime harness OFF/ON lift with weights held constant; stock-vs-fine-tuned model deltas live in this notebook's `eval_results.json`.
- **[Public hub: duecare-ai.com](https://duecare-ai.com)** -- knowledge-pack registry, anonymized signal intake, public-source proposal intake, and the 5-lane audience showcase.
