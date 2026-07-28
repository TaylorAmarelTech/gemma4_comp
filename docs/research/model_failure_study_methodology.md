# Model-failure study methodology

This document defines a reproducible way to measure a capability gap, attach
the exact DueCare grounding context, and triangulate results with deterministic,
cross-family, same-family, and eventually human review. It accompanies:

- `scripts/model_failure_study.py` for baseline candidate generation and local
  deterministic grading;
- `scripts/model_failure_judge.py` for contextual automated judging;
- `scripts/model_failure_report.py` for separated aggregation and agreement;
- the frozen
  [`Kimi K3 500-item campaign`](../../configs/duecare/benchmarks/kimi_k3_500_context_judge_campaign.json).

No current Kimi K3 or Gemini 3.1 result exists. The 2026-07-28 campaign is
access-blocked and has zero completed hosted calls.

## Research questions

1. **Recognition:** does a baseline model identify exploitation and coercion?
2. **Grounding:** does it connect the facts to relevant indicators, rules, and
   evidence instead of producing generic concern?
3. **Equivocation resistance:** does benign framing obscure debt bondage,
   recruitment fees, document retention, sponsorship control, or related risk?
4. **Safety and utility:** is the response protective, appropriately bounded,
   and actionable without inventing referrals or volatile legal facts?
5. **Intervention value:** in a separately controlled arm, how much does a
   versioned harness improve these outcomes?

## Unit of analysis and selection

The unit is one `(candidate model, frozen prompt, candidate response)` tuple.
Prompts are public synthetic/composite benchmark items; raw worker cases and
private data are prohibited.

The current directional campaign selects exactly 500 prompts across 117
categories using category-balanced selection, seed `20260728`, and SHA-256
`9d4aedf042f5f9d73e8372a8f1bf5538190d9791dbc692c38ca720aed1bc48eb`.
The selection hash must be reproduced before execution. Adding, deleting, or
editing source prompts creates a new campaign rather than silently changing
this one.

## Candidate condition

Kimi K3 receives each prompt with the neutral baseline system message,
temperature zero, and no DueCare GREP, retrieval, tool, or persona context.
This isolates baseline capability. Each successful response is stored with its
prompt/model identity and receives the local deterministic grade immediately.

The campaign reserves 500 Kimi calls, 158,922 estimated input tokens, and
384,000 maximum output tokens. The answer cap is 768 tokens. The result runner
is resumable and uses response hashes so a changed answer cannot inherit an old
judge verdict.

## Fixed contextual evidence

Both automated judges receive the same `duecare-full` context assembled
offline for each prompt:

- fired deterministic GREP indicators;
- the top eight retrieved versioned RAG excerpts; and
- deterministic tool results.

The frozen 500-prompt context set contains 5,922,118 characters (5,288 minimum,
11,434 median, 16,025 maximum per prompt) and has SHA-256
`109f18c68f7b09e193bc9e2a41b55628b9267fa2c73f10ab3fcb9fad098656db`.
Judge outputs retain context evidence IDs and hashes, not a second raw copy of
the full context. The judge prompt marks candidate text and retrieved context
as untrusted evaluation material.

## Four evidence layers

| Layer | Source | Strength | Required label |
|---|---|---|---|
| Deterministic | `grade_response_universal` | Reproducible and free; keyword/rule noise remains | Screen or cross-check |
| Cross-family automated | Gemini 3.1 Pro with frozen context | Independent model family and structured rubric | Primary automated judgment |
| Same-family automated | Kimi K3 judging Kimi K3 with identical context | Reveals self-preference and rubric sensitivity | Diagnostic self-judgment |
| Human | Qualified, consented reviewers under a review protocol | Needed to calibrate consequential claims | Human validation only when actually collected |

Automated outputs are not human ratings or ground truth. The Kimi lane is not an
independent judgment. No layer should be blended into a single score without
showing its provenance and relationship.

## Rubric and judge protocols

Both automated judges assess:

- `sense_resolution`;
- `legal_grounding`;
- `harm_safety`; and
- `actionability`.

Two protocols are supported:

1. **Holistic directional protocol:** one structured call per answer returns an
   overall 0-100 score plus PASS/PARTIAL/FAIL and a short reason for every
   dimension. This is the 500-item campaign protocol. It minimizes cost and is
   appropriate for finding directional patterns and disagreement slices.
2. **Per-dimension protocol:** one provider call evaluates exactly one rubric
   dimension. This avoids cross-dimension coupling and is the stronger
   publication-grade automated protocol, but requires four times as many judge
   calls. It must be preregistered and budgeted separately.

Temperature is zero. Judge, candidate response, context, rubric, and final
prompt hashes bind each result. Only final successful verdicts satisfy resume
keys; ERROR and UNPARSED rows can be retried under a new reserved attempt.

## Current judge assignment

- `gemini-3.1-pro-preview` is the primary cross-family contextual judge.
- `kimi-k3` is the secondary same-family contextual self-judge.

The Gemini lane requests low reasoning effort and JSON response mode so the
bounded 768-token output budget prioritizes the structured verdict. The Kimi
lane uses provider-default reasoning and the same explicit JSON-only prompt;
provider-specific request options remain recorded rather than disguised as an
identical transport configuration.

This pairing tests both a family-independent view and the candidate family's
own critique without conflating them. A future panel may add another family,
but only for a frozen uncertainty-reduction question and a separately reviewed
budget.

## Planned analysis

Report at minimum:

- deterministic versus Gemini exact agreement;
- deterministic versus Kimi exact agreement;
- Gemini versus Kimi exact agreement;
- per-dimension PASS/PARTIAL/FAIL counts;
- category-stratified scores and failure patterns;
- invalid, missing, truncated, ERROR, and UNPARSED counts;
- the largest rule/model and model/model disagreements for blind human review;
- provider/model IDs, prompt/context hashes, protocol, date, token usage, and
  ledger receipt.

Do not average away missing rows or treat access failures as low scores. Do not
select illustrative examples only after seeing which ones support a preferred
claim.

## Cost and stopping rule

At the rates checked on 2026-07-28, the frozen holistic campaign reserves:

| Lane | Maximum calls | Worst-case cost |
|---|---:|---:|
| Kimi candidates | 500 | US$6.236766 |
| Gemini contextual judge | 500 | US$11.745660 |
| Kimi contextual self-judge | 500 | US$16.466490 |
| **Total** | **1,500** | **US$34.448916** |

The hard ceiling is US$35. Each phase must use the shared provider ledger with
finite attempt/input/output/cash caps and a reviewed pricing file. Failed calls
and retries consume reservations. Stop on any policy breach, selection/context
hash drift, provider identity drift, unexpected truncation rate, or systemic
parse failure.

Prices and access rules are volatile. Reverify them from the official provider
pages immediately before spending; the manifest records the URLs used for the
current estimate.

## Reproducibility and privacy

- Preserve the Git revision, manifest, exact CLI arguments, sanitized budget
  receipt, result hashes, and report together.
- Keep result and ledger files under ignored `reports/` until privacy and claim
  review approves a publication artifact.
- Never send raw PII, private case files, real worker contact details, or
  unreviewed entity-intelligence output to a hosted judge.
- Do not hardcode volatile hotline, fee, wage, office, or legal claims into
  prompts unless they are versioned knowledge objects.
- Keep the baseline candidate condition distinct from any future harnessed arm.

## Interpretation boundaries

The campaign can support statements about this frozen synthetic prompt sample,
these exact provider model versions, and these grading protocols. It cannot by
itself establish field effectiveness, legal correctness, safety for every
corridor or language, human agreement, or general superiority.

The historical 2026-06 open-model pilot remains useful as pipeline provenance,
but its old roster and automated judge should not be presented as current Kimi
K3/Gemini evidence. Use the
[readiness receipt](model_failure_run_readiness.md) for exact commands and live
access blockers, and the
[capability-gap blueprint](../architecture/capability_gap_blueprint.md) for the
industry-neutral architecture behind this study.
