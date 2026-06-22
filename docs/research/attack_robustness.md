# Input-attack robustness — does the GREP layer survive obfuscation?

The harness's first layer is **GREP indicator rules** (case-insensitive keyword/regex). A real evader obfuscates the input, so we apply a matrix of surface transforms to prompts GREP catches when clean, and measure **how many of those hits survive**. This is deterministic — no model calls — and isolates the keyword layer specifically. Where GREP is evaded, the harness's RAG + ILO-reasoning layers are the backstop (measured separately by the lift-under-attack run).

> Over **199 prompts** GREP catches when clean, the obfuscation attacks drive keyword-hit retention down to **0.0%**, and the **encoding** attacks (base64 / ROT13 / reversed) take it to near **0%** — a keyword layer is simply blind to encoded text. The **jailbreak wrappers** instead leave the indicators *visible* (GREP still fires, so the harness still injects its warning) and attack the **model's** compliance — their test is the lift-under-attack, not this table. Either way the lesson is the same: keyword matching is the cheap first pass, not the safety layer; the RAG grounding + ILO-reasoning preamble is the backstop.

## A. GREP-evasion attacks — do the indicators still match? (higher = more robust)

| Attack transform | hits kept | fully-evaded | what it does |
|---|---:|---:|---|
| `base64` | **0.0%** | 100.0% | whole request base64-encoded |
| `rot13` | **0.0%** | 100.0% | whole request ROT13-encoded |
| `reversed_text` | **0.0%** | 100.0% | whole request character-reversed |
| `excessive_punctuation` | **59.6%** | 11.1% | spray punctuation, split key terms |
| `token_split` | **76.6%** | 3.0% | invisible HTML comment inside key terms |
| `homoglyph` | **77.1%** | 3.0% | Latin -> Cyrillic/Greek look-alikes |
| `whitespace_injection` | **77.1%** | 3.0% | zero-width space inside key terms |
| `leetspeak` | **77.1%** | 3.0% | a->4 e->3 o->0 s->5 i->1 on key terms |
| `code_switch` | **80.4%** | 3.0% | key nouns -> worker's language (es/tl/hi/id) |
| `no_punctuation` | **99.1%** | 0.0% | strip all punctuation |

## B. Model-jailbreak wrappers — indicators stay visible (GREP still fires)

These wrap the ask but leave the keywords intact, so GREP keeps firing (retention near 100%) and the harness still injects its warning. The real question — does the model comply anyway, and does the harness stop it? — is the **lift-under-attack** run, not this keyword table.

| Jailbreak wrapper | GREP still fires | what it does |
|---|---:|---|
| `instruction_override` | 100.0% | 'ignore your guidelines / unrestricted mode' prefix |
| `hypothetical_frame` | 100.0% | fiction / role-play frame ('in a novel...') |
| `inversion_redflags` | 100.0% | how-to disguised as an inspector training guide |
| `output_template` | 100.0% | force output into a no-warning contract template |

## Reading this

- **hits kept** = of the GREP rules that fired on the clean prompt, the share that still fire after the attack. **fully-evaded** = the share of prompts where the attack silences GREP entirely.
- GREP is fast, free, and exact on clean text — the point is **not** that it is weak, but that a keyword layer *must* be backed by semantics. DueCare is GREP **plus** retrieved legal grounding **plus** an ILO-reasoning preamble, so an obfuscated prompt that slips past GREP still meets the model with the reasoning instruction, and a jailbreak wrapper that keeps the keywords still triggers the warning. The *lift under attack* (baseline-vs-harness on the 14-transform attack matrix) is the companion result.
- Deterministic + composite; transforms in `scripts/prompt_attacks.py`. The attack-matrix prompt set (`--emit`) feeds the model run.

