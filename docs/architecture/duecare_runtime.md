# Duecare Runtime — Gemma 4 model layer

**Status: Built.** Lives in `kaggle/01-duecare-exploration-workbench/kernel.py`
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

## Output sanitizer

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
  DUECARE SELF-AUDIT  -  chat-package 0.17.0
======================================================================
    n_grep_rules       <live count>
    n_rag_docs         <live count>
    n_dimensions       <live count>
    rubric           v3.10-evaluator-quality
======================================================================
  OK all counts at or above the 0.17.0 portability minimums
```

Fails loudly if counts fall below the portability minimums (eliminates
the "old wheel still serving" phantom-bug class). The reusable contract
is exposed by `duecare.chat.portability` and `GET /api/portability`.
Override with `DUECARE_ALLOW_OLD_WHEEL=1` for intentional roll-back.
