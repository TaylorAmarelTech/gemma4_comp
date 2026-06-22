# Input-attack robustness — does the GREP layer survive obfuscation?

The harness's first layer is **GREP indicator rules** (case-insensitive keyword/regex). A real evader obfuscates the input, so we apply a matrix of surface transforms to prompts GREP catches when clean, and measure **how many of those hits survive**. This is deterministic — no model calls — and isolates the keyword layer specifically. Where GREP is evaded, the harness's RAG + ILO-reasoning layers are the backstop (measured separately by the lift-under-attack run).

> Over **199 prompts** GREP catches when clean, hit-retention under attack ranges down to **59.6%** (the strongest evasion). Keyword matching alone is *not* robust to unicode/cross-lingual obfuscation — which is exactly why the harness does not rely on it alone.

## GREP hit-retention by attack (higher = more robust)

| Attack transform | hits kept | fully-evaded prompts | what it does |
|---|---:|---:|---|
| `excessive_punctuation` | **59.6%** | 11.1% | spray punctuation, split key terms |
| `homoglyph` | **77.1%** | 3.0% | Latin -> Cyrillic/Greek look-alikes |
| `whitespace_injection` | **77.1%** | 3.0% | zero-width space inside key terms |
| `leetspeak` | **77.1%** | 3.0% | a->4 e->3 o->0 s->5 i->1 on key terms |
| `code_switch` | **80.4%** | 3.0% | key nouns -> worker's language (es/tl/hi/id) |
| `no_punctuation` | **99.1%** | 0.0% | strip all punctuation |

## Reading this

- **hits kept** = of the GREP rules that fired on the clean prompt, the share that still fire after the attack. **fully-evaded** = the share of prompts where the attack silences GREP entirely.
- The point is **not** that GREP is weak — it is fast, free, and exact on clean text. The point is that a keyword layer *must* be backed by semantic layers; DueCare's harness is GREP **plus** retrieved legal grounding **plus** an ILO-reasoning preamble, so an obfuscated prompt that slips past GREP still meets the model with the reasoning instruction. The *lift under attack* (baseline-vs-harness on these perturbed prompts) is the companion result.
- Deterministic + composite; transforms in `scripts/prompt_attacks.py`. The attack-matrix prompt set (`--emit`) feeds the model run.

