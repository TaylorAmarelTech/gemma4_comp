# Lift under attack — does the harness still help when the input is obfuscated?

`attack_robustness.md` showed the GREP keyword layer is degraded by obfuscation and **fully blinded** by encoding (base64 / ROT13 / reversed → 0% hit retention). This is the question that matters: when the prompt is perturbed or jailbroken, does the **harnessed** reply still beat the **baseline** reply? Same paired design, judged by the same LLM judge; gemma4:31b.

> Over **140 paired perturbed prompts**, the harness lifts the safety score **+4.39/10** (p=<0.001) — *larger* than the +1.73 clean headline, because the baseline fails harder under attack so there is more to fix. The lift is positive for **every attack type** (+3.20 to +5.40). The decisive cell: even the **encoding** attacks that leave GREP totally blind still lift **+4.10/10** — so the RAG grounding + ILO-reasoning preamble, not the keyword layer, is carrying the safety.

## Harness lift by attack transform

| Attack transform | layer | n | harness lift | p |
|---|---|---:|---:|---:|
| `hypothetical_frame` | model | 10 | **+5.40** | <0.001 |
| `no_punctuation` | grep | 10 | **+5.20** | <0.001 |
| `token_split` | grep | 10 | **+4.80** | <0.001 |
| `excessive_punctuation` | grep | 10 | **+4.70** | <0.001 |
| `leetspeak` | grep | 10 | **+4.60** | <0.001 |
| `reversed_text` | grep | 10 | **+4.60** | <0.001 |
| `homoglyph` | grep | 10 | **+4.40** | <0.001 |
| `whitespace_injection` | grep | 10 | **+4.40** | <0.001 |
| `output_template` | model | 10 | **+4.40** | <0.001 |
| `code_switch` | grep | 10 | **+4.30** | <0.001 |
| `base64` | grep | 10 | **+3.90** | <0.001 |
| `rot13` | grep | 10 | **+3.80** | <0.001 |
| `inversion_redflags` | model | 10 | **+3.80** | <0.001 |
| `instruction_override` | model | 10 | **+3.20** | <0.001 |

## By layer

| Layer | n | mean lift |
|---|---:|---:|
| GREP-evasion (obfuscation) | 100 | **+4.47** |
| model-jailbreak wrappers | 40 | **+4.20** |

## Reading this

- **The point:** an attacker who obfuscates the input can evade the cheap keyword layer, but the harness's semantic layers (retrieved legal grounding + the evidence-first reasoning instruction) still meet the model — so the harmful answer is still less likely. The harness degrades *gracefully* under attack rather than failing open.
- **Why the lift is bigger than the clean headline:** under attack the *baseline* is more likely to produce the harmful/ungrounded answer, so there is more headroom for the harness to recover — the gap widens exactly where it is most needed.
- **Caveats:** n is modest per transform (a focused subset of the attack matrix), gemma4:31b only, and one judge model. This measures direction and rough size, not a precise magnitude. The attack transforms are in `scripts/prompt_attacks.py`; the keyword-evasion companion is `attack_robustness.md`.

