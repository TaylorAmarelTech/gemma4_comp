# Frontier-Model Trafficking-Safety — per-dimension harness lift (at scale)

The quantitative result. Each model answers hundreds of migrant-worker trafficking-safety prompts in two arms — **baseline** (raw prompt) and **harnessed** (the DueCare GREP/RAG/reasoning layer) — and every reply is scored on **69 rubric dimensions** by DueCare's own deterministic grader (free, reproducible, one score per applicable dimension). Because dimensions differ in difficulty and applicability, the honest unit is the **per-dimension** lift (same dimension, both arms), not a single mean.

> **Across 5 models and 87 prompts, the harness improves 40 of 69 graded rubric dimensions** (mean +0.40/10 on those), is neutral on 13, and regresses 16 (mean -0.24). The gains concentrate on trafficking-safety substance; the regressions are small operational-directness / localization tradeoffs (both shown below, nothing hidden).

A naive per-response mean across all 69 dimensions is ~flat (-0.04/10) and is **not** the right metric here: strong baselines already ceiling-out the easy dimensions, and the harness actively *surfaces* hard dimensions the baseline ignored (e.g. retaliation-protection notices), which are real gains but still score low — so they drag a response average down even as they improve safety. Per dimension is the truth.

## Where frontier models FAIL to detect / respond at baseline — and the harness fix

Out of the box, averaged over hundreds of prompts and every model on the board, the strongest models systematically **under-address** these trafficking-safety dimensions. A baseline near zero means the model essentially never does it unprompted — a worker in danger would not be told. The harness lifts each one.

| What a safe reply must do (rubric dimension) | Baseline | Harnessed | n |
|---|---:|---:|---:|
| `complaint_retaliation_protection_notice` | 0.25 | 1.33 | 199 |
| `contact_verification_currency` | 0.55 | 0.64 | 109 |
| `referral_scope_and_consent` | 0.70 | 1.53 | 241 |
| `authoritative_civil_society_contact` | 3.81 | 5.05 | 109 |
| `specific_numbers` | 4.38 | 5.05 | 282 |
| `government_regulator_contact` | 4.38 | 5.60 | 260 |
| `convention_specific_article` | 4.54 | 5.03 | 99 |
| `citation_recall_quality` | 4.60 | 5.13 | 419 |
| `cross_cultural_sensitivity` | 4.71 | 4.99 | 112 |
| `gender_aware_framing` | 4.71 | 4.97 | 267 |
| `legal_specificity` | 4.82 | 5.10 | 419 |
| `sectoral_specificity` | 4.87 | 5.08 | 174 |

The failures cluster in three places a raw model omits but a worker in danger needs: **protective procedure** (retaliation-risk warnings, referral consent), **concrete contacts** (NGO + regulator hotlines, contact currency), and **legal specificity** (exact convention articles, specific hotline numbers). These are not edge cases — they are the operational core of a safe response, and frontier models miss them by default.

## Per-model — rubric dimensions improved vs regressed

| Model | Dims improved | Dims regressed | Mean lift on improved |
|---|---:|---:|---:|
| `qwen3-coder:480b` | 52 | 6 | +0.58 |
| `deepseek-v3.2` | 35 | 4 | +0.29 |
| `gemma4:31b` | 35 | 23 | +0.63 |
| `qwen3.5:397b` | 29 | 5 | +0.21 |
| `glm-5.2` | 26 | 26 | +0.73 |

## Top dimensions the harness improves

The mechanism behind the gains: the harness makes models name the ILO indicators, cite the right instruments, surface protective contacts, and refuse to normalise exploitation.

| Rubric dimension | Baseline | Harnessed | Lift | n |
|---|---:|---:|---:|---:|
| `multi_jurisdiction_coverage` | 6.80 | 8.94 | **+2.14** | 255 |
| `authoritative_civil_society_contact` | 3.81 | 5.05 | **+1.24** | 109 |
| `government_regulator_contact` | 4.38 | 5.60 | **+1.21** | 260 |
| `complaint_retaliation_protection_notice` | 0.25 | 1.33 | **+1.08** | 199 |
| `international_framework` | 8.62 | 9.67 | **+1.05** | 136 |
| `corridor_specific_knowledge` | 8.94 | 9.81 | **+0.88** | 255 |
| `referral_scope_and_consent` | 0.70 | 1.53 | **+0.83** | 241 |
| `specific_numbers` | 4.38 | 5.05 | **+0.68** | 282 |
| `citation_recall_quality` | 4.60 | 5.13 | **+0.54** | 419 |
| `convention_specific_article` | 4.54 | 5.03 | **+0.49** | 99 |
| `predatory_debt_financial_crime` | 9.63 | 10.00 | **+0.37** | 139 |
| `prompt_attack_resilience` | 8.85 | 9.20 | **+0.35** | 79 |
| `economic_remedy_quantification` | 4.95 | 5.28 | **+0.33** | 114 |
| `ilo_convention_grounding` | 4.94 | 5.25 | **+0.32** | 419 |
| `ilo_indicator_naming` | 9.70 | 10.00 | **+0.29** | 419 |
| `cross_cultural_sensitivity` | 4.71 | 4.99 | **+0.28** | 112 |
| `legal_specificity` | 4.82 | 5.10 | **+0.28** | 419 |
| `gender_aware_framing` | 4.71 | 4.97 | **+0.26** | 267 |

## Dimensions the harness regresses (the honest tradeoffs)

Shown in full. Most are small; the recurring theme is that a more legal, evidence-first reply is slightly less operationally direct, and the legal preamble is English-centric (localization). Candidates for harness tuning.

| Rubric dimension | Baseline | Harnessed | Lift | n |
|---|---:|---:|---:|---:|
| `multilingual_localization` | 6.00 | 5.42 | -0.58 | 20 |
| `on_device_privacy_alignment` | 5.53 | 5.08 | -0.45 | 10 |
| `multi_stakeholder_coordination` | 5.46 | 5.03 | -0.43 | 10 |
| `operational_information_provided` | 8.26 | 7.89 | -0.37 | 419 |
| `child_protection_triage` | 5.48 | 5.16 | -0.32 | 9 |
| `actionability_without_overreach` | 5.62 | 5.31 | -0.31 | 113 |
| `privacy_pii_minimization` | 5.45 | 5.14 | -0.30 | 191 |
| `movement_and_document_control_screening` | 5.39 | 5.15 | -0.24 | 238 |
| `coercion_control_screening` | 5.35 | 5.18 | -0.17 | 263 |
| `procedural_pathway` | 5.19 | 5.04 | -0.15 | 153 |
| `uncertainty_calibration` | 5.23 | 5.08 | -0.14 | 397 |
| `evidence_preservation_guidance` | 5.34 | 5.21 | -0.13 | 197 |
| `proactive_reporting_guidance` | 5.24 | 5.13 | -0.10 | 347 |
| `data_quality_recognition` | 5.16 | 5.08 | -0.08 | 38 |
| `worker_monetary_interest_protection` | 5.21 | 5.14 | -0.07 | 384 |
| `emerging_pattern_recognition` | 5.08 | 5.03 | -0.06 | 419 |

## Methodology

- **Models** (5): `deepseek-v3.2`, `gemma4:31b`, `glm-5.2`, `qwen3-coder:480b`, `qwen3.5:397b`.
- **Prompts**: 87 from the public benchmark corpus (`configs/duecare/benchmarks/harness_lift_prompts_500.json`), composite/synthetic, no real PII.
- **Grading**: DueCare's `grade_response_universal` — 69 rubric dimensions, deterministic, free, one score per APPLICABLE dimension (NOT_APPLICABLE excluded). This honours the per-dimension grading-integrity rule without tens of thousands of external judge calls.
- **Move threshold**: a dimension counts as improved/regressed only if |lift| > 0.05 (grader noise floor); otherwise neutral.
- **Reproduce**: `LIFT_PROMPTS_FILE=harness_lift_prompts_500.json LIFT_N_PROMPTS=87 LIFT_MODELS=... python scripts/harness_lift_local.py` then `python scripts/build_frontier_perdim_report.py`.

This is the gradeable, at-scale, all-dimensions result. A holistic LLM-judge headline (the +1.7/10 methodology of `docs/research/harness_lift_report.md`) is the complementary lens — it rewards the richer harnessed reply where this granular grader books the gains and the tradeoffs separately. The few-prompt example reports (`frontier_harness_report*.md`) show full baseline-vs-harnessed text side by side.

