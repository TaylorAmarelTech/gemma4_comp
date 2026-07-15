# Gemma 4 Feature Showcase

Current as of 2026-07-14. This document now describes the active Kaggle
submission path instead of the retired A-series appendix ladder.

## Features Demonstrated

| Feature | Where It Appears | Why It Matters |
|---|---|---|
| Small-model local inference | Kernels 01 and 02, with active A-00 proof artifacts | Shows Gemma 4 can be wrapped for practical safety work without a remote frontier dependency. |
| Shared Unsloth FastModel runtime | `Gemma4Runtime.load()` | Standardizes loading, generation defaults, chat template, quantization, and device mapping. |
| Harnessed generation | Kernel 01 and active A-00 | Holds the base prompt constant while adding DueCare context, rules, and tools. |
| Deterministic tool use | Kernel 01 and active A-00 `chat_no_online` | Grounds answers in fee caps, ILO indicators, convention lookups, and NGO-intake style checks. |
| Candidate SFT/preference row generation | Active A-00 source | Uses harnessed Gemma outputs to create gated training candidates; no complete advanced dataset is published. |
| LoRA fine-tuning | Active A-00 source | Demonstrates the guarded Unsloth/PEFT SFT&rarr;DPO path and adapter save/load flow; the existing smoke is not a production adapter. |
| Combined rule + LLM judging | Active A-00 source | Produces a score using deterministic rules plus a configured Gemma/frontier-style judge. |
| Evidence export | Active A-00 source | Saves reports, traces, activity logs, charts, and machine-readable artifacts for review. |

## Runtime Contract

All active local inference should load through
[`Gemma4Runtime.load()`](model_loading_trace.md). The known-good FastModel
recipe uses:

- `dtype=None`
- `load_in_4bit=True`
- `full_finetuning=False`
- `device_map="balanced"` for larger two-GPU loads, otherwise the runtime's
  selected map
- `gemma-4-thinking` chat template
- generation defaults `temperature=1.0`, `top_p=0.95`, `top_k=64`

The direct `FastModel.from_pretrained` exception is active A-00's training
script, where the model is loaded for LoRA fine-tuning rather than inference.

## Active Kernel Map

| Kernel | Feature Focus |
|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Broad harness comparison, trace inspection, knowledge extraction, search controls, and model-runtime UX. |
| `kaggle/02-live-demo/` | Focused end-user narrative and video-safe interaction path. |
| `kaggle/A-00-omni-experiment-workbench/` | Quantitative proof path: baseline vs harnessed arms, synthetic data, fine-tune, judging, and report artifacts. |

## Optional Better-Than-Demo Upgrades

These are supported directions, not requirements for the default proof path:

- Use a larger Gemma model or frontier model to generate higher-quality
  synthetic training rows.
- Use a larger Gemma model, Ollama-hosted judge, Anthropic-compatible judge, or
  other frontier judge for final grading.
- Expand knowledge packs with IOM documents, US TIP reports, court cases, and
  NGO-provided fact objects after privacy review.
- Add online grounding only behind search-safety, anonymization, and
  post-search verification harnesses.

## Related Current Docs

- [`harness_ecosystem.md`](harness_ecosystem.md)
- [`harness_standard_contract.md`](harness_standard_contract.md)
- [`model_loading_trace.md`](model_loading_trace.md)
- [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md)
