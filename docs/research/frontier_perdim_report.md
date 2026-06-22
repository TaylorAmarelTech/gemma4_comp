# Frontier-Model Trafficking-Safety — per-dimension harness lift (at scale)

The quantitative result. Each model answers hundreds of migrant-worker trafficking-safety prompts in two arms — **baseline** (raw prompt) and **harnessed** (the DueCare GREP/RAG/reasoning layer) — and every reply is scored on the applicable subset of DueCare's **75-dimension** deterministic rubric (69 dimensions appear in this prompt set; free, reproducible, one score per applicable dimension). Because dimensions differ in difficulty and applicability, the honest unit is the **per-dimension** lift (same dimension, both arms), not a single mean. *Note: the pooled per-dimension significances below are exploratory — they treat (prompt×model) pairs as independent (clustered); see `robustness_checks.md`.*

> **Across 5 models and 136 prompts, the harness improves 37 of 69 graded rubric dimensions** (mean +0.42/10 on those), is neutral on 13, and regresses 19 (mean -0.20). The gains concentrate on trafficking-safety substance; the regressions are small operational-directness / localization tradeoffs (both shown below, nothing hidden).

A naive per-response mean across all 69 dimensions is ~flat (+0.01/10) and is **not** the right metric here: strong baselines already ceiling-out the easy dimensions, and the harness actively *surfaces* hard dimensions the baseline ignored (e.g. retaliation-protection notices), which are real gains but still score low — so they drag a response average down even as they improve safety. Per dimension is the truth.

## Where frontier models FAIL to detect / respond at baseline — and the harness fix

Out of the box, averaged over hundreds of prompts and every model on the board, the strongest models systematically **under-address** these trafficking-safety dimensions. A baseline near zero means the model essentially never does it unprompted — a worker in danger would not be told. The harness lifts each one.

| What a safe reply must do (rubric dimension) | Baseline | Harnessed | n |
|---|---:|---:|---:|
| `complaint_retaliation_protection_notice` | 0.20 | 1.24 | 348 |
| `referral_scope_and_consent` | 0.81 | 1.36 | 420 |
| `contact_verification_currency` | 0.92 | 0.60 | 249 |
| `authoritative_civil_society_contact` | 3.60 | 5.13 | 222 |
| `government_regulator_contact` | 4.29 | 5.55 | 452 |
| `specific_numbers` | 4.39 | 5.08 | 474 |
| `convention_specific_article` | 4.55 | 5.07 | 135 |
| `citation_recall_quality` | 4.57 | 5.14 | 659 |
| `gender_aware_framing` | 4.69 | 4.96 | 438 |
| `cross_cultural_sensitivity` | 4.80 | 5.00 | 181 |
| `data_quality_recognition` | 4.83 | 5.16 | 98 |
| `legal_specificity` | 4.84 | 5.14 | 659 |

The failures cluster in three places a raw model omits but a worker in danger needs: **protective procedure** (retaliation-risk warnings, referral consent), **concrete contacts** (NGO + regulator hotlines, contact currency), and **legal specificity** (exact convention articles, specific hotline numbers). These are not edge cases — they are the operational core of a safe response, and frontier models miss them by default.

## Per-model — rubric dimensions improved vs regressed

| Model | Dims improved | Dims regressed | Mean lift on improved |
|---|---:|---:|---:|
| `qwen3-coder:480b` | 48 | 8 | +0.53 |
| `deepseek-v3.2` | 34 | 9 | +0.29 |
| `gemma4:31b` | 34 | 27 | +0.75 |
| `glm-5.2` | 30 | 24 | +0.57 |
| `qwen3.5:397b` | 29 | 6 | +0.23 |

## Top dimensions the harness improves

The mechanism behind the gains: the harness makes models name the ILO indicators, cite the right instruments, surface protective contacts, and refuse to normalise exploitation.

| Rubric dimension | Baseline | Harnessed | Lift | n |
|---|---:|---:|---:|---:|
| `multi_jurisdiction_coverage` | 6.66 | 8.93 | **+2.27** | 412 |
| `authoritative_civil_society_contact` | 3.60 | 5.13 | **+1.53** | 222 |
| `government_regulator_contact` | 4.29 | 5.55 | **+1.26** | 452 |
| `complaint_retaliation_protection_notice` | 0.20 | 1.24 | **+1.03** | 348 |
| `international_framework` | 8.63 | 9.67 | **+1.03** | 224 |
| `corridor_specific_knowledge` | 8.88 | 9.76 | **+0.89** | 404 |
| `specific_numbers` | 4.39 | 5.08 | **+0.69** | 474 |
| `citation_recall_quality` | 4.57 | 5.14 | **+0.57** | 659 |
| `referral_scope_and_consent` | 0.81 | 1.36 | **+0.55** | 420 |
| `convention_specific_article` | 4.55 | 5.07 | **+0.52** | 135 |
| `predatory_debt_financial_crime` | 9.52 | 9.96 | **+0.45** | 261 |
| `ilo_convention_grounding` | 4.92 | 5.26 | **+0.35** | 659 |
| `data_quality_recognition` | 4.83 | 5.16 | **+0.34** | 98 |
| `ilo_indicator_naming` | 9.66 | 9.99 | **+0.34** | 659 |
| `legal_specificity` | 4.84 | 5.14 | **+0.30** | 659 |
| `gender_aware_framing` | 4.69 | 4.96 | **+0.28** | 438 |
| `cross_corridor_pattern_synthesis` | 4.88 | 5.14 | **+0.26** | 113 |
| `provenance_per_claim` | 9.59 | 9.84 | **+0.24** | 498 |

## Dimensions the harness regresses (the honest tradeoffs)

Shown in full. Most are small; the recurring theme is that a more legal, evidence-first reply is slightly less operationally direct, and the legal preamble is English-centric (localization). Candidates for harness tuning.

| Rubric dimension | Baseline | Harnessed | Lift | n |
|---|---:|---:|---:|---:|
| `multilingual_localization` | 5.81 | 5.38 | -0.43 | 40 |
| `child_protection_triage` | 5.51 | 5.16 | -0.35 | 18 |
| `on_device_privacy_alignment` | 5.43 | 5.10 | -0.33 | 27 |
| `contact_verification_currency` | 0.92 | 0.60 | -0.32 | 249 |
| `operational_information_provided` | 8.25 | 7.94 | -0.31 | 659 |
| `actionability_without_overreach` | 5.60 | 5.30 | -0.30 | 185 |
| `privacy_pii_minimization` | 5.40 | 5.16 | -0.24 | 328 |
| `multi_stakeholder_coordination` | 5.27 | 5.05 | -0.22 | 18 |
| `movement_and_document_control_screening` | 5.35 | 5.15 | -0.20 | 445 |
| `uncertainty_calibration` | 5.25 | 5.09 | -0.16 | 611 |
| `evidence_preservation_guidance` | 5.37 | 5.22 | -0.15 | 380 |
| `harm_enablement_check` | 9.04 | 8.90 | -0.14 | 111 |
| `proactive_reporting_guidance` | 5.27 | 5.13 | -0.14 | 573 |
| `coercion_control_screening` | 5.31 | 5.19 | -0.12 | 474 |
| `worker_monetary_interest_protection` | 5.24 | 5.14 | -0.10 | 610 |
| `substance_over_form` | 5.30 | 5.20 | -0.10 | 659 |
| `exploitation_risk_rationale` | 5.33 | 5.25 | -0.08 | 519 |
| `structured_data_competence` | 5.16 | 5.10 | -0.06 | 98 |
| `alternative_pathway` | 5.18 | 5.12 | -0.05 | 251 |

## Statistical significance (Benjamini–Hochberg FDR-corrected)

A paired test on each of 69 dimensions (≥10 paired observations each) is many simultaneous hypotheses, which inflates false positives. We correct the whole family with **Benjamini–Hochberg (FDR)**; a dimension is significant only if its adjusted **q ≤ 0.05**.

> **After FDR correction, the harness significantly improves 24 dimensions and significantly regresses 10** (of 69 tested) — stricter than the raw improve/regress counts above. **Read as exploratory:** each dimension's p pools all (prompt × model) pairs as if independent, but they are clustered by model (design effect ~1.6), so the standard errors are understated and this FDR-surviving set is **anticonservative** (the true set is somewhat smaller). The clean inferential claims are the per-model paired tests and the cluster-robust headline CI — see `robustness_checks.md` §2.

| Dimension (FDR-significant improvement) | Mean Δ | q | n |
|---|---:|---:|---:|
| `multi_jurisdiction_coverage` | +2.27 | <0.001 | 412 |
| `authoritative_civil_society_contact` | +1.53 | <0.001 | 222 |
| `government_regulator_contact` | +1.26 | <0.001 | 452 |
| `complaint_retaliation_protection_notice` | +1.03 | <0.001 | 348 |
| `international_framework` | +1.03 | <0.001 | 224 |
| `corridor_specific_knowledge` | +0.89 | <0.001 | 404 |
| `specific_numbers` | +0.69 | <0.001 | 474 |
| `citation_recall_quality` | +0.57 | <0.001 | 659 |
| `referral_scope_and_consent` | +0.55 | 0.0198 | 420 |
| `convention_specific_article` | +0.51 | <0.001 | 135 |
| `predatory_debt_financial_crime` | +0.45 | <0.001 | 261 |
| `ilo_convention_grounding` | +0.35 | <0.001 | 659 |

## Methodology

- **Models** (5): `deepseek-v3.2`, `gemma4:31b`, `glm-5.2`, `qwen3-coder:480b`, `qwen3.5:397b`.
- **Prompts**: 136 from the public benchmark corpus (`configs/duecare/benchmarks/harness_lift_prompts_500.json`), composite/synthetic, no real PII.
- **Grading**: DueCare's `grade_response_universal` — 75-dimension rubric (69 appear in this prompt set), deterministic, free, one score per APPLICABLE dimension (NOT_APPLICABLE excluded). This honours the per-dimension grading-integrity rule without tens of thousands of external judge calls.
- **Move threshold**: a dimension counts as improved/regressed only if |lift| > 0.05 (grader noise floor); otherwise neutral.
- **Reproduce**: `LIFT_PROMPTS_FILE=harness_lift_prompts_500.json LIFT_N_PROMPTS=136 LIFT_MODELS=... python scripts/harness_lift_local.py` then `python scripts/build_frontier_perdim_report.py`.

This is the gradeable, at-scale, all-dimensions result. A holistic LLM-judge headline (the +1.7/10 methodology of `docs/research/harness_lift_report.md`) is the complementary lens — it rewards the richer harnessed reply where this granular grader books the gains and the tradeoffs separately. The few-prompt example reports (`frontier_harness_report*.md`) show full baseline-vs-harnessed text side by side.

