# Training for understanding, not shortcuts — a Phase 3 study design

> Distilling the harness into the weights (docs/phase3_training_framework.md) has a failure mode we
> must design against: a model can learn the **surface shortcut** ("a fee-splitting-shaped prompt →
> say *I cannot* and cite *C181*") without learning the **understanding** (recognise the indicator,
> reason about substance-over-form, and refuse for the right reason). A shortcut wins on the training
> distribution and collapses on anything new. This document is the study: how we generate and organise
> training materials to favour understanding, and — crucially — how we *measure* which one we got.

## 1. What a shortcut looks like here

Concrete, domain-specific shortcut hypotheses we must rule out:

- **Keyword→refusal.** The model maps trigger words (fee, deduction, passport, recruitment) to a
  canned refusal + a canned citation, regardless of whether the request is actually exploitative.
- **Over-refusal.** It learns "this *topic* → refuse," so it refuses a worker asking about their
  *rights* (a benign query) — a safety regression disguised as caution.
- **Citation parroting.** It emits "ILO C181" because the training targets did, not because the
  scenario is a recruitment-fee case (it would cite C181 for a passport case too).
- **Obfuscation blindness.** It keys off literal strings, so a base64 / homoglyph / code-switched
  version of the same scheme slips through — the meaning was never learned, only the spelling.
- **Format mimicry.** It copies the harnessed reply's *shape* (headings, "I cannot fulfil…") without
  the substantive indicator reasoning underneath.

## 2. Training MATERIALS that favour understanding

1. **Reasoning supervision, not just the verdict.** Teach the chain — *indicator identified → why it
   is the controlling law → therefore refuse/redirect* — so the target rewards the reasoning, not the
   conclusion alone. (Process supervision beats outcome-only for generalisation.)
2. **Counterfactual minimal pairs.** For each scheme prompt, a near-identical prompt with the
   exploitation removed (a genuine rights/wage/contract question) whose correct answer is *help, do
   not refuse*. Same surface, opposite label — the only way to pass both is to understand.
3. **Hard negatives (already in DPO).** The baseline's plausible-but-wrong reply as the `rejected`
   example, so the model learns the boundary, not just the positive.
4. **Paraphrase + phrasing diversity.** Many surfaces for one concept, so no single phrasing becomes
   the trigger.
5. **Obfuscated variants in TRAIN.** The benchmark's attack transforms (encoding, homoglyph,
   code-switch, jailbreak wrappers) included as training inputs with the *same* correct target — forces
   meaning-under-obfuscation.
6. **Distractor robustness.** Irrelevant-but-plausible context added that must not change the answer.
7. **Stable-vs-volatile discipline** (rule 81): targets teach the *reasoning and refusal shape*; the
   volatile specifics (a hotline number, a fee cap) stay tool-supplied so the weights can't memorise a
   number-shortcut that goes stale.

## 3. ORGANISATION of training materials

- **Held out by typology / corridor.** Entire typologies (and corridors) are withheld from training
  and used only for evaluation. Generalisation to *unseen* typologies is the headline anti-shortcut
  metric — a model that only memorised cannot do it. (`scripts/organize_training_data.py`.)
- **Balance.** Cap per-typology counts so no `typology → response` correlation is over-represented
  (the soil shortcuts grow in).
- **Interleave, don't block.** Round-robin typologies through the data so a batch is never "all one
  keyword" — block ordering invites per-batch shortcuts.
- **Curriculum (easy→hard) *within* interleaving.** Order by difficulty for a stable start, but keep
  typologies mixed at each level.
- **Leakage control.** Text-hash (and near-text) dedup across train/held-out so a "generalisation"
  score isn't memorised duplicates.

## 4. DIAGNOSTICS — measuring shortcut vs understanding

The point of the study is measurement, not faith. Each trained variant is scored on:

1. **Held-out-typology generalisation gap.** The four-arm internalisation (C−A) on *trained*
   typologies minus on *held-out* typologies. A large gap = memorisation; a small gap = understanding.
   (Built on `scripts/four_arm_eval.py` + the held-out split.)
2. **Perturbation robustness.** Re-score the eval prompts under paraphrase / obfuscation transforms;
   a big score drop = the model relied on surface form.
3. **Counterfactual consistency.** On minimal pairs, does the model correctly *flip* (help the benign
   twin, refuse the exploitative one)? Shortcuts fail one side.
4. **Over-refusal rate.** Benign control prompts (rights/wage questions); training must not raise
   refusals here. (The benchmark already separates refusals; reuse it.)
5. **Citation appropriateness.** Is the cited instrument the *right* one for the scenario, or the most
   frequent one in training? (Deterministic via `citation_accuracy.py`.)

A variant only counts as "understanding" if it holds up on held-out typologies **and** under
perturbation **and** on counterfactuals — not just on the training distribution.

## 5. The experiment (the study)

Train several variants from the same base and compare on the diagnostics above (held-out typologies):

| variant | data / organisation |
|---|---|
| V0 baseline distill | the raw SFT/DPO from `build_lift_training_data.py`, as-is |
| V1 + balance/interleave | V0 reorganised by `organize_training_data.py` (capped, interleaved) |
| V2 + counterfactual pairs | V1 + benign minimal-pair twins |
| V3 + obfuscated variants | V2 + attack-transformed inputs with the same targets |
| V4 + reasoning supervision | V3 with targets that include the indicator→law→refusal reasoning |

Selection rule: promote the variant with the **smallest held-out generalisation gap** and **no
over-refusal regression** — not the highest training-set score. Every run uses the four-arm eval and
is logged with `(git_sha, data_manifest)` for reproducibility.

## 6. Honest framing
- A small held-out gap is *evidence of* understanding, not proof; we report the gap, the perturbation
  curve, and the counterfactual rate together, and never a single headline.
- Counterfactual and obfuscated training data is synthetic and could carry its own artefacts; the
  diagnostics are run on *held-out* typologies the training never saw.
- Some lift is irreducibly volatile (facts the harness supplies); the goal is to internalise the
  *stable reasoning*, measured by C−A on held-out typologies, not to memorise facts.

## 7. First implementation step (this commit)
`scripts/organize_training_data.py` — the organisation layer: splits the distilled SFT/DPO by
**typology** (whole typologies held out for the generalisation diagnostic), **balances** (caps
per-typology to kill over-representation), **interleaves** (round-robin so no batch is single-keyword),
and **dedups** (text-hash, leakage control), writing `{sft,dpo}_{train,heldout}.jsonl` + a manifest to
the gitignored `reports/training/` store. The remaining variants (counterfactual, obfuscated,
reasoning-supervised data; the perturbation + counterfactual diagnostics) are the next steps.
