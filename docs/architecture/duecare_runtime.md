# Duecare Runtime — Gemma 4 model layer

**Status: Built.** Lives in `kaggle/01-duecare-harness-chat/kernel.py`
+ `packages/duecare-llm-chat/src/duecare/chat/_model_output.py`.

## Responsibilities

- Generate plain-language explanations.
- Summarize case facts.
- Classify risk patterns.
- Interpret screenshots / documents (multimodal mode).
- Support local / private deployment.
- Provide different model sizes for different surfaces.

**Critical:** Runtime does not own truth. It is the language and
reasoning engine inside a deterministic safety system. Trusted data
(laws, contacts, policy) comes from the Harness / Exchange — never
from the model.

## Model tiers (current)

| Tier | Best use | HF id |
|---|---|---|
| Gemma 4 E2B | mobile / on-device / low-resource | `unsloth/gemma-4-E2B-it` |
| Gemma 4 E4B | NGO / government dashboard baseline | `unsloth/gemma-4-E4B-it` |
| Gemma 4 26B-A4B | research, server-side eval, MoE | `unsloth/gemma-4-26B-A4B-it` |
| Gemma 4 31B | flagship | `unsloth/gemma-4-31B-it` |
| Jailbroken 31B | abliterated; "real not faked" proof | `dealignai/Gemma-4-31B-JANG_4M-CRACK` |
| Jailbroken E4B | smaller abliterated | `mlabonne/Gemma-4-E4B-it-abliterated` |
| Cloud Gemini | BYOK fallback | Gemini 1.5 Flash |
| Cloud OpenAI-compat | BYOK fallback | per-deploy |
| Cloud Ollama | BYOK fallback | per-deploy |

## Output sanitizer (v0.14.5)

Single-source `_model_output.sanitize_model_output()` strips:

- Input-side template marker `<|turn>model`
- Multi-`<channel|>` thinking-mode separators (rsplit, take last)
- `<thinking>...</thinking>` and `<think>...</think>` blocks
- Turn delimiters `<turn|>`, `<end_of_turn>`
- Special tokens `<bos>`, `<eos>`, `<start_of_turn>`, `<end_of_turn>`

15-case regression suite at
`packages/duecare-llm-chat/tests/test_model_output.py` includes the
verbatim leaked string from the user's first live E2B test.

Wired into local-Gemma + cloud-Gemini + cloud-OpenAI + cloud-Ollama
paths so artifacts don't surface on a different backend.

## Deployment self-audit

After wheel install, `kernel.py` prints:

```
======================================================================
  DUECARE SELF-AUDIT  ·  chat-package 0.14.5
======================================================================
    n_grep_rules       161
    n_rag_docs         46
    n_dimensions       46
    rubric           v3.10-evaluator-quality
======================================================================
  ✓ all counts at or above v0.14.x submission minimums
```

Fails loudly if counts fall below v0.14.x minimums (eliminates the
"old wheel still serving" phantom-bug class). Override with
`DUECARE_ALLOW_OLD_WHEEL=1` for intentional roll-back.
