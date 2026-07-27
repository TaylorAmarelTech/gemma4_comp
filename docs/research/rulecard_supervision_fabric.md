# RuleCards and the governed supervision fabric

> Reconciles the 2026-07 harness + LLM + informed-judge fine-tuning blueprint
> with DueCare's **actual** current state. Every number here is measured from
> the real repository, not aspirational. Companion code:
> `packages/duecare-llm-chat/src/duecare/chat/rulecards.py`,
> `scripts/build_rulecards.py`. Regenerate the deck with
> `python scripts/build_rulecards.py`.

## The central thesis

Do not train a monolithic model to decide whether a person is a trafficking
victim or perpetrator. Keep four planes distinct:

```
document observation  !=  model inference  !=  legal finding  !=  operational action
```

A trafficking indicator is grounds for additional inquiry, not proof (Palermo
Protocol; UNODC indicator guidance). DueCare's hard-coded harness should not be
replaced by a fine-tune — it should become a **governed supervision fabric**
that teaches, challenges, validates, and constrains learned models while never
being mistaken for ground truth.

## What DueCare already has (measured)

| Asset | Real state (2026-07-16) | Source |
|---|---|---|
| Hard-coded GREP indicator rules | **451 rules** (critical 73, high 262, medium 101, low 12, info 3) | `scripts/build_rulecards.py` |
| Rules citing a recognized legal instrument | **390 of 451**; 61 uncited | RuleCard summary |
| RAG corpus | 859 trafficking documents + 610 multidomain (kept separate) | `docs/KNOWLEDGE_SURFACE_VERIFICATION.md` |
| Multilingual GREP layer | 11 languages (tl/id/vi/sw/hi/ne/bn/ur/ar/am/zh) | `_grep_rules_multilingual.py` |
| Recorded benchmark panel | **7,953 paired real registry prompts** graded by a 3-judge panel | `docs/research/full_results.md` |
| Measured harness lift | baseline 48.4 -> harnessed **89.1 (+40.7)**, holds within each judge | `analyze_full_results.py` |
| Fine-tune result (honest) | narrow +0.15 structural on 8 rows; frozen judge did **not** support a training-lift claim | adapter learning study |
| Judge decomposition | 5 calibrated rubric components (A-E), per-dimension grading | `rich_harness_lift.py` |

The blueprint's diagnosis matches DueCare's evidence exactly: the fine-tuned-only
condition underperformed while the harnessed condition improved but stayed
judge-sensitive. **The bottleneck is label/judge calibration and task
entanglement, not SFT volume.**

## The RuleCard layer (built)

Each GREP rule is now compilable into a typed, auditable `RuleCard` carrying its
authoritative sources, antecedent (patterns), consequence (severity + indicator),
inferred role, jurisdiction, witness family, and calibration gaps. The compiler
runs deterministically over the real rules — no model call, nothing invented.

### The correlated-witness result (the load-bearing finding)

Running the compiler over the real deck:

- **451 rules resolve to 80 correlated-witness families** (reduction ratio 0.18).
- The **single largest family holds 86 rules**; the **top five families hold 63%**
  of the entire deck.
- Rules per authoritative instrument: Palermo Protocol **153**, ILO C181 **113**,
  ILO C029 **89**, ILO C189 **59**, ILO C095 **48**.

Under the design-effect formula `m_eff = m / (1 + (m-1)*rho)` applied per witness
family, the **effective independent-witness count** is about **83 at rho=0.9,
90 at rho=0.7, and 100 at rho=0.5** — far below the 451 raw rules. The 80-family
count is the rho=1 (maximally conservative) bound; the total rule count is the
rho=0 bound.

The compiled deck, independence report, and a visual notebook are published as a
public Kaggle dataset:
[`taylorsamarel/duecare-rulecard-supervision-fabric`](https://www.kaggle.com/datasets/taylorsamarel/duecare-rulecard-supervision-fabric)
(CC-BY-4.0, rule metadata only — no worker data or PII). Regenerate/repackage
with `python scripts/build_rulecards_kaggle.py`.

This is the blueprint's key insight, now measured from DueCare's own rules: 153
rules anchored on the Palermo Protocol are **153 correlated votes, not 153
independent confirmations**. Any weak-supervision label model built on these
rules must down-weight within-family agreement, or a single legal principle
expressed as many patterns will masquerade as many independent witnesses and
badly inflate confidence.

### Role classification (deliberately conservative)

Every GREP rule compiles to `labeling_function` (a fallible positive vote) plus
`feature_extractor` (it emits a matched fact without being a conclusion). **None
are auto-promoted to `hard_invariant`** — a pattern match is grounds for inquiry,
not proof or action. The 73 critical-severity rules are flagged
`candidate_invariant_review = true` for a human to decide, never silently.

### Calibration gaps every card records

Every card inherits three gaps from its raw GREP source, and closing them is the
roadmap:

- `expected_precision_recall_unknown` — no rule has a measured precision/recall.
- `no_unit_test_counterexamples` — no rule ships benign-lookalike counterexamples.
- `owner_and_last_validation_unrecorded` — no provenance of who owns/last checked it.

## Build order (reconciled with what exists)

The blueprint's sequence, mapped to DueCare's actual next steps:

1. **RuleCards over the real rules** — *done* (this doc + the compiler). Turns 451
   opaque regexes into an auditable, correlation-aware deck.
2. **Freeze real, temporal, multilingual, jurisdictional, hard-negative, and
   adversarial evaluation sets** — partially done: the 78,719-prompt registry +
   the multilingual GREP layer exist; hard-negative benign-lookalikes and a
   temporally-forward held-out real set are the gap.
3. **Benchmark rules-only / base-only / retrieval+model / harness+model** — the
   harness-vs-base arms exist (+40.7 measured); the rules-only and retrieval-only
   arms are the missing baselines.
4. **Correlation-aware weak supervision** — the RuleCard witness families are the
   input; a Snorkel-style label model that consumes families (not raw rule votes)
   is the next build.
5. **Fact-first synthetic generation** (`Z -> facts -> documents -> re-extract`) —
   not yet built; the current synthetic corpora are prose-grounded remixes, which
   the blueprint correctly flags as weaker than latent-graph ground truth.
6. **Verifier jury, not one judge** — the 5-component rubric is a start; the
   blueprint's decomposition (schema/citation validator, entailment judge,
   applicability judge, benign-alternative judge, safety/privacy judge, blind vs
   trace-aware judges, human adjudicator) with fatal-defect veto is the extension.
7. **Evidence-route SFT, then calibrated preference optimization** — DueCare has
   the DPO path; the blueprint's ordering (calibrate judges *before* preference
   optimization) is the discipline to keep.

## Non-negotiable safeguards (already load-bearing in DueCare)

- **Three-plane firewall:** private support, evidence processing, and
  investigation assistance stay separate; help-seeking, refusal, testimony, or
  service use can never become adverse evidence (OHCHR; CoE Anti-Trafficking
  Convention). DueCare's privacy boundary and `_safe_text` chokepoint are the
  existing substrate.
- **Base rates are decisive.** At 1% prevalence, 90% sensitivity, 95%
  specificity, positive predictive value is ~15%; at 0.1% it is ~2%. Balanced
  evaluation sets conceal an operational system where most alerts are false, so
  synthetic results stay diagnostic — promotion requires gains on untouched,
  expert-adjudicated, temporally forward real cases.
- **Correlated sources are not independent corroboration** — the same discipline
  the RuleCard witness families now enforce for rules applies to documents:
  cluster evidence by common origin before fusion.

## What not to do

Do not let the RuleCard deck, the +40.7 harness lift, or any synthetic corpus be
read as proof of real-world trafficking detection. They are measurement and
supervision evidence. The most valuable move is not replacing DueCare's
hard-coded intelligence — it is turning that intelligence into a governed
supervision fabric that can teach, challenge, validate, and constrain learned
models without ever being mistaken for ground truth.
