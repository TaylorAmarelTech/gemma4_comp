# A-13 — On-device export (LoRA merge -> GGUF + LiteRT)

<!-- duecare:lane-label -->
> **Serves lanes:** 03 Individual worker / mobile, 05 Developer

## Status

**Folder reserved; kernel.py pending.** This slot will:

1. Load Gemma 4 base + a LoRA adapter (SafetyJudge from A-05 or
   PrivacyRedactor from A-11)
2. Merge LoRA into base via `peft.PeftModel.merge_and_unload()`
3. Build llama.cpp + convert merged HF model to GGUF (Q4_K_M default)
4. Optional: LiteRT conversion via `ai-edge-torch` for mobile target
5. Emit export manifest + downloads via the workbench shell

Closes Special Tech Track gaps:
- llama.cpp ($10K) — produces a real GGUF a judge can run on a laptop
- LiteRT ($10K) — produces a real .tflite a judge can run on a phone

See `docs/appendix_experiment_ladder.md` for the full ladder spec.
