# DueCare -- external review artifacts

Raw, reproducible, **model-free** evidence for outside reviewers. Nothing here
depends on a judge model or a network call: every number is recomputed by the
deterministic `duecare.kit.verify` checker from the public response data, so a
reviewer can regenerate it end-to-end and get the same result.

## What is in here

### `deterministic_verify_<model>.csv`

One row per prompt: the deterministic 0-5 score for the **baseline** and the
**harnessed** (`harness_core`) response, their difference, and the pass/fail flag
for each of the five safety criteria on both arms.

| column | meaning |
|---|---|
| `prompt_id` | stable id (join key to the public prompt/response datasets) |
| `model` | model under test |
| `base_score_0_5`, `core_score_0_5` | deterministic 0-5 score, each arm |
| `lift_0_5` | `core - base` (positive = harness better) |
| `base_A..base_E`, `core_A..core_E` | per-criterion pass (1) / fail (0), each arm |

Criteria: **A** indicator surfaced, **B** legal citation, **C** refusal + redirect,
**D** resource routing, **E** privacy clean.

The CSV carries **no response text and no personal data** -- only prompt ids and
deterministic scores. The full (synthetic, scrubbed) prompt+response text is the
separate public `duecare-prompt-response-showcase` dataset.

## Headline finding (gemma4:31b, full registry)

The deterministic checker scores **every** generated response pair, so it gives
**full-registry coverage the rate-limited judge panel does not currently have**:

- **78,719** paired prompts scored (vs. ~5,307 judged so far).
- deterministic mean **3.97 -> 4.83 / 5** = **+0.86** lift.
- per-criterion regressions (baseline passed, harness failed): **D 2,275**,
  C 449, A 401, B 4, **E 0**.

Two things a reviewer should take from that:

1. **The lift is not a judge artifact.** An independent, un-gameable checker
   confirms the harness is better on ~97% of the full registry, at full scale.
2. **Privacy never regresses (E = 0)** and legal grounding almost never does
   (B = 4). The one real weak spot is **D (resource routing)**: on ~2.9% of
   prompts the harness demotes or drops a concrete resource cue -- see
   `docs/research/harness_hurts_review_2026_07_21.md` for the diagnosis (it is
   mostly an ordering/prominence issue, not lost content) and the proposed
   answer-first fix.

## How this reconciles with the +40.7/100 judged headline

Different instruments, same direction. The **judge panel** scores 0-100 across
reasoned dimensions and reports **+40.7** on the graded subset; the
**deterministic checker** scores 0-5 on hard yes/no criteria and reports
**+0.86/5** on the full registry. They are not the same scale and should not be
added -- the point is that a model-based judge and a model-free checker
independently agree the harness helps, which is exactly the "grounded, not just
optimized" claim.

## Reproduce it

```bash
pip install "git+https://github.com/TaylorAmarelTech/gemma4_comp.git#subdirectory=packages/duecare-llm-kit"
# from a clone of the repo, with the response data present:
python scripts/deterministic_full_registry.py --model gemma4:31b
python scripts/review_harness_hurts.py --model gemma4:31b   # the negative-lift review
```

`duecare.kit.verify` is the same checker used in the CI regression gate
(`scripts/run_evals_gate.py`), so these numbers are also what the build enforces.
