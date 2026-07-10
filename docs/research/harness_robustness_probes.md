# Harness robustness probes — accidental input noise, a proposed fix, and a reviewer-critique register

This note covers the *accidental-input-noise* robustness axis (does the harness sit on a fragile semantic
peak — do a worker's real-world typos and phrasing collapse detection?) and, per the review discipline, an
explicit register of the objections a peer reviewer would raise, each with **more than one** mitigation and
always keeping the **original, unimproved method** in the comparison rather than silently swapping it.

It is deliberately complementary to the siblings, not a duplicate:

- `attack_robustness.md` — the *deliberate-evasion* axis (base64 / ROT13 / homoglyph / leetspeak /
  token-split obfuscation by an adversary). Encoding drives GREP retention to ~0%; that doc owns evasion.
- `robustness_checks.md` — *statistical* robustness (clustering/ICC, applicability confound, circularity).
- `perdim_granular_lift.md` — the *grading-side* overfitting probes (framing sensitivity, fabrication canary).

This note adds three things those do not: the **word-vs-character diagnosis** (a clean overfitting test),
a **reviewer-robust evaluation of a proposed fix** (recall *and* precision, original retained), and the
**critique register**. All probes here are deterministic, need no model calls, and are propose-only.

## What the probes found

**Noise robustness** (`scripts/noise_robustness.py`, nine techniques). On 40–80 real benchmark prompts the
GREP indicator layer is **robust to word-level noise but brittle to character-level corruption of trigger
terms**:

| Robust (word-level) | retention @20% | Brittle (character-level) | retention @20% |
|---|---:|---|---:|
| drop_stopwords (clean overfit test) | 1.00 | typo | 0.82 |
| misspell (non-trigger words) | 1.00 | char_repeat (elongation) | 0.78 |
| extra_words (filler) | 0.98 | split_merge (whitespace) | 0.67 |
| word_swap (reorder) | 0.82 | punct_inject (evasion) | 0.62 |

The `drop_stopwords` = 1.00 result is the load-bearing reassurance and the sharpest overfitting test here:
removing stopwords does not change firing, so the rules are **not** matching brittle exact multi-word
phrases — the effect is not a word/phrase-level surface artifact. The brittleness is confined to corrupting
the *characters* of a trigger term. (This meets `attack_robustness.md`'s deliberate-evasion table from the
accidental-noise side; `punct_inject` here is the same family as its `excessive_punctuation`.)

**Proposed fix, evaluated the way a reviewer would demand** (`scripts/grep_normalization.py`). A pre-GREP
normaliser, tested at four strengths with the original (`none`) kept as the baseline and **both recall and
precision** reported:

- `collapse_repeats` — a narrow **safe** win (char_repeat recall 0.78 → 0.89 at 20%, neutral elsewhere).
- `strip_separators` / `both` — **net negative**: a small punct_inject gain (0.62 → 0.71) bought at large
  losses everywhere else (char_repeat 0.78 → 0.48, typo 0.88 → 0.55, split 0.67 → 0.42), because global
  separator-stripping mangles the *legitimate* punctuation the rules use (statute "C-181" → "C181",
  corridor "IN-AE", "18-hour"). Precision stayed clean (0.00 fires on benign under every strength).

Honest verdict: adopt only `collapse_repeats`; the evasion/typo/split gaps need **surgical, trigger-anchored
or fuzzy** matching, not a blunt global normaliser. This is a case where testing multiple fixes against the
original *rejected* the obvious one — which is the point of keeping the baseline in view.

## Reviewer-critique register

Each row is an objection a reviewer could raise, with the mitigations already in place or available. The
theme: never replace the original method — report it alongside every variant so the reader judges the
trade-off.

| # | Reviewer objection | Mitigations (multiple; original always retained) |
|---|---|---|
| 1 | "GREP fire-rate is a *proxy* — noise breaking GREP ≠ noise breaking the model's safety." | (a) scope it honestly as a cheap lower-bound detection screen, not the end metric; (b) measure lift-under-noise directly (baseline vs harnessed generation on noised prompts) when Ollama resumes — the definitive test, with the GREP proxy kept as the always-available screen; (c) note the model's own reasoning catches indicators GREP misses, so GREP fragility *overstates* system fragility. |
| 2 | "The noise transforms and rates are hand-tuned / cherry-picked." | (a) report a rate **sweep** (5/10/20%), not one rate; (b) deterministic seeds + a reproducible tool so anyone re-derives it; (c) cross-check against an established library (TextAttack / NL-Augmenter) as an independent implementation; (d) retention is measured **relative to the clean original**, which anchors every number. |
| 3 | "Only ~66% of prompts fire clean — retention is on a biased subset." | (a) the base rate is reported explicitly, not hidden; (b) the sparse clean-firing is itself surfaced as a coverage finding; (c) the full promptset (vs an 80-prompt sample) tightens it. |
| 4 | "punct_inject at 20% is unrealistic for accidental typing." | (a) separate the two threat models — *accidental* noise (typo/char_repeat, read at a low 5% rate) vs *deliberate* evasion (punct_inject, valid at any rate because an adversary chooses it, and owned by `attack_robustness.md`); (b) the full sweep lets the reader pick the realistic operating point. |
| 5 | "Your normalisation fix will over-fire on benign text (false positives)." | (a) precision is measured on benign off-topic **and** near-miss prompts; (b) the original (`none`) is the baseline column in every table; (c) multiple strengths expose the precision/recall trade-off instead of asserting one fix; (d) the honest result is reported even though it *rejects* strip_separators. |
| 6 | "You recalibrated the deduction framing after seeing it was an outlier — post-hoc (HARKing)." | (a) the pre-fix number and the rationale are both reported (`perdim_granular_lift.md`); (b) a re-measurement is scheduled rather than assuming the fix worked; (c) the change is to a research tool, not the live v1/h1 board, and every framing stays available. |
| 7 | "Grading probes are single-judge (mistral), small N." | (a) bootstrap 95% CIs on every lift; (b) cross-family judge routes are wired (openai/anthropic/nvidia) and light up when a key or credit is available; (c) results are reported as a **range across lenses and judges**, not a point estimate. |

## Limitations (stated, not hidden)

- These are input-side *detection* probes on the GREP layer; they do not by themselves prove the end-to-end
  harnessed answer degrades under noise (critique 1). That measurement is queued for the next Ollama window.
- Samples are bounded (tens of prompts); the tools run at larger N on request.
- The normaliser is a propose-only prototype applied as a preprocessor in front of the black-box GREP; it is
  **not** wired into the live harness. Adopting any of this is gated to an explicit instruction and a
  versioned re-grade, so the published v1/h1 board is unaffected by these experiments.

## Reproduce

```
python scripts/noise_robustness.py --batch reports/benchmark/full_promptset.json --sample 60
python scripts/grep_normalization.py --batch reports/benchmark/full_promptset.json --sample 40
```
