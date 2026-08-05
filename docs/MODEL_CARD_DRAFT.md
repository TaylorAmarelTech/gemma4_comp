# Model card — DRAFT / PROPOSED

> **Status: draft. Nothing new is being released.**
>
> This card documents adapters that are **already public** inside the
> [DueCare Gemma 4 Adapter Learning Study](https://www.kaggle.com/datasets/taylorsamarel/duecare-gemma4-adapter-learning-study)
> dataset. It exists because Google's
> [Responsible GenAI Toolkit](https://ai.google.dev/responsible/docs/design)
> recommends a model card alongside a data card, and that dataset shipped with
> a data card and a limitations statement but no model card.
>
> It is written as a draft rather than a release announcement because the
> artifact it describes is a **bounded learning study, not a model anyone
> should deploy**. Publishing it as a polished model card would imply a product
> claim the evidence does not support.

Structure follows Mitchell et al., *Model Cards for Model Reporting* (2019).

## Model details

| Field | Value |
|---|---|
| Developed by | Taylor Amarel (DueCare) |
| Model type | LoRA adapter (PEFT) over a Gemma 4 base model |
| Base model | `unsloth/gemma-4-e2b-it-unsloth-bnb-4bit` (Gemma 4 **E2B**, 4-bit) |
| Adapter rank / alpha / dropout | r = 2, α = 2, dropout = 0 |
| Task type | `CAUSAL_LM` |
| Trainable parameters | **817,152 of 4,409,128,480 (0.0185%)** |
| Licence | Apache 2.0 (Derivative Work of Gemma 4); see root `NOTICE` |
| Base weights redistributed? | **No** — adapters only; obtain base weights from Google |

Two runs are published. They are **not** two versions of one model; they are
two points on a deliberately small experiment.

| | run-01 | run-02 |
|---|---|---|
| Optimizer steps | 12 | 60 |
| Epochs reached | 0.75 | 1.875 |
| Final training loss | 4.2042 | 3.2829 |
| Wall-clock training | 154.3 s | 780.6 s |
| Holdout rows evaluated | **4** | **8** |
| Peak learning rate | 2e-4, linear decay | 2e-4, linear decay |

Note on hyper-parameters: `configs/duecare/training/unsloth_e4b.yaml` describes
the project's **E4B** training recipe (3 epochs, batch 4, seq 2048,
`adamw_8bit`). These published adapters are **E2B** runs and did not run that
recipe to completion — the authoritative per-run values are the table above and
each run's own `run-manifest.json` and `metrics.json`.

## Intended use

**Intended:** reproducing and inspecting the DueCare training pipeline
end-to-end — that a grounded-remix corpus can be assembled, a LoRA attached,
training executed, an adapter saved and reloaded, and the result evaluated
against a locked holdout with the outcome recorded honestly, including when it
is null.

**Explicitly out of scope.** Do not use these adapters to:

- detect trafficking, exploitation, or any criminal conduct
- advise a worker, caseworker, lawyer, inspector, or employer
- support a legal, journalistic, or investigative determination
- claim any safety or quality improvement over base Gemma 4

The `not_demonstrated` field is recorded in both runs' own metrics files:
**general legal quality, real-world worker outcomes, independent safety
improvement, production readiness.**

## Factors

Evaluated only on English-language, synthetic/composite grounded-remix rows in
the migrant-worker exploitation domain. No disaggregation by corridor,
language, sector, or worker demographic was performed — the holdout is far too
small to support it. Nothing is known about behaviour outside that slice.

## Metrics

A deterministic structural rubric with three components — `heading_score`,
`objective_score`, `boundary_score` — plus an `overclaim_penalty`. These reward
**declared response structure and boundary terms**. They are not a human or
legal quality judgement, and a higher score does not mean a better answer to a
real worker.

## Quantitative analyses

**run-01 — no lift.**

| Metric | Base | Adapted | Δ |
|---|---|---|---|
| heading_score | 1.0 | 1.0 | 0.0 |
| objective_score | 0.666667 | 0.666667 | 0.0 |
| boundary_score | 0.166667 | 0.166667 | 0.0 |

`model_lift_demonstrated_on_locked_grounded_remix_holdout: false`. The adapted
model scored identically to the base on all four rows.

**run-02 — narrow, format-scoped lift.**

| Metric | Base | Adapted | Δ |
|---|---|---|---|
| heading_score | 0.75 | 1.0 | **+0.25** |
| objective_score | 0.516667 | 0.666667 | **+0.15** |
| boundary_score | 0.166667 | 0.166667 | 0.0 |

`model_lift_demonstrated: true`, with the run's own recorded scope: *"Observed
lift is limited to the declared three-field format objective on a tiny,
source-grounded remix holdout."*

**How to read this honestly.** n = 8. The movement is in structure and format
adherence; the boundary component — the one closest to substantive safety
behaviour — **did not move at all** in either run. A separate frozen
frontier-judge audit of the same adapter did not support a positive
training-lift claim. Treat run-02 as evidence the pipeline can teach a response
format, and as evidence of nothing else.

## Training data

Grounded-remix rows derived from the DueCare corpus, published in the same
dataset with parent hashes and lineage-family splits. Every entity is a
fabricated composite. Multiple descendants of one approved source response are
**not independent observations**, so row count materially overstates effective
sample size — stated in the dataset's own `LIMITATIONS.md`.

## Ethical considerations

- **Deployment risk is the dominant concern.** A model that looks like it
  handles worker-safety questions, deployed on the strength of a
  format-adherence delta measured on 8 rows, could cause real harm to people in
  genuine danger. That is the specific misuse this card exists to prevent.
- **Domain sensitivity.** Trained on material about labour exploitation.
  Outputs should be treated as untrusted drafts requiring human review.
- **No PII.** No real worker data, case files, or personal contacts.
- **Dual use.** The harness these adapters were trained to support is also an
  evaluation instrument for adversarial prompts; see
  [`RESPONSIBLE_USE.md`](RESPONSIBLE_USE.md).
- **Inherited constraints.** Gemma 4's
  [Prohibited Use Policy](https://ai.google.dev/gemma/prohibited_use_policy)
  applies to these derivatives.

## Caveats and recommendations

1. **Do not deploy these adapters.** They are a pipeline proof.
2. **Do not cite run-02 as a safety improvement.** Its own manifest scopes it to
   a format objective.
3. Low training loss with weak holdout transfer is evidence of overfitting, not
   generalisation — the dataset's `LIMITATIONS.md` says so directly.
4. Anyone extending this should raise holdout size by orders of magnitude, add
   blinded human adjudication, and disaggregate by corridor and language before
   making any quality claim.
5. The frontier judge is one measurement instrument, not ground truth, and its
   preferences must not be recycled into training data for this study.

## If this card is ever finalised

It would need a larger and genuinely independent holdout, disaggregated results,
blinded human adjudication on a sample, and a decision about whether the
artifact is worth presenting as a model at all rather than as the pipeline
receipt it currently is. Absent those, the honest form of this document is the
draft you are reading.
