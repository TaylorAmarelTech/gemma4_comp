# Primary trafficking GREP pack -- coverage / dead-rule check (offline, no model calls)

> Runs the harness's 451-rule matcher over **15,000** benchmark prompts (`reports/benchmark/full_promptset.json`). Regenerate with `python scripts/analyze_trafficking_grep_coverage.py`. Synthetic prompts; rule labels only.

**451 rules.** Prompt coverage (>=1 rule fires): **63.7%**; mean **1.34** rules fire per prompt. **Rules that never fire on this promptset: 257** -- by severity {'high': 152, 'medium': 66, 'critical': 29, 'info': 1, 'low': 9}.

> Two non-exclusive reads of a never-firing rule, and they need different fixes: (a) a **benchmark coverage gap** -- the promptset has no prompt that exercises that indicator, so the benchmark under-tests the harness's own rule library (fix: add prompts); or (b) an **over-narrow / stale rule** that would not fire on realistic worker text either (fix: widen or prune). The GREP rules are built to fire on real worker chat / documents, and the benchmark's adversarial *scheme* prompts are a different distribution, so some non-firing is expected -- but this many (incl. high/critical severities) is worth a review pass.

## Rules that never fire on this promptset (coverage gap OR over-narrow)

| Rule | severity |
|---|---|
| `aaa_dating_app_romance_pretext_compound` | high |
| `aaa_telegram_discord_channel_recruitment` | high |
| `aaaa_consular_non_cooperation_pattern` | medium |
| `advance_fee_fraud_remote_job` | high |
| `afghan_exodus_exploitation` | high |
| `agriculture_piece_rate_below_minimum` | high |
| `ai_generated_job_ad_signal` | medium |
| `arbitrary_debt_balance_inflation` | high |
| `au_pair_pocket_money_full_domestic` | medium |
| `auto_delete_evidence_evasion` | medium |
| `backdated_employment_contract` | high |
| `bbb_electronic_monitoring_off_the_clock` | medium |
| `bbb_employer_biometric_punch_clock_coercion` | medium |
| `bbbb_sham_religious_recruitment_for_labour` | high |
| `bnpl_recruitment_loan_pattern` | high |
| `carwash_uniform_water_deduction` | medium |
| `cashback_recruitment_inducement` | medium |
| `ccc_pension_provident_fund_denial` | high |
| `ccc_retraining_bonded_debt_clause` | medium |
| `cccc_cult_spiritual_coercion_trafficking` | high |
| `cleaning_subcontractor_ghost_worker` | high |
| `climate_displaced_recruitment_pattern` | high |
| `construction_payment_held_until_completion` | critical |
| `corridor_southasia_emigrate_bypass` | high |
| `cross_platform_phone_recurrence` | high |
| `crypto_wallet_capture_pattern` | medium |
| `cyprus_north_TCN_eu_backdoor` | high |
| `ddd_climate_displaced_pacific_recruitment` | high |
| `ddd_rohingya_specific_recruitment_pattern` | high |
| `dddd_informal_day_labour_no_permit` | medium |
| `deepfake_interview_signal` | high |
| `deepfake_or_ai_generated_recruiter` | high |
| `digital_credential_vault_debt_control` | critical |
| `digital_recruit_ewallet_fee_rail` | high |
| `discord_server_recruitment` | medium |
| `domestic_to_sex_work_transition` | critical |
| `dubai_shell_company_front` | high |
| `ee_gbv_recruitment_screening` | critical |
| `ee_sextortion_recruitment_phase` | critical |
| `eee_group_home_sponsorship_pyramid` | high |
| `eee_labour_hire_indirection_layered` | medium |
| `eeee_surrogacy_as_trafficking_pretext` | high |
| `elder_care_24_7_on_call` | high |
| `equivocation_bond_financial_instrument` | high |
| `equivocation_broker_commission_normal` | high |
| `equivocation_deduction_standard` | high |
| `equivocation_exploitation_optimisation` | high |
| `equivocation_safekeeping_analogy` | high |
| `equivocation_sponsor_like_event` | high |
| `esoteric_archaic_legal_language` | medium |
| `euphemism_all_inclusive_package_debt` | high |
| `euphemism_flexible_hours_unpaid_overtime` | medium |
| `euphemism_in_kind_wages_only` | high |
| `euphemism_like_family_domestic_servitude` | high |
| `euphemism_piece_rate_below_minimum` | high |
| `euphemism_retention_bonus_withheld` | medium |
| `euphemism_sham_self_employment` | high |
| `euphemism_stipend_below_minimum` | high |
| `euphemism_tied_accommodation_control` | high |
| `euphemism_unpaid_trial_shift` | medium |
| … +197 more | |

## Most-fired rules (the workhorses)

| Rule | fires | severity |
|---|---:|---|
| `high_risk_migration_corridor` | 6,567 | info |
| `corridor_statute_id_destination_trigger` | 1,497 | medium |
| `jailbreak_academic_research_framing` | 1,333 | high |
| `corridor_BD_to_GULF_BMET` | 1,037 | high |
| `corridor_statute_nepal_trigger` | 787 | medium |
| `ilo_indicator_passport_retention` | 782 | critical |
| `ilo_indicator_isolation` | 637 | critical |
| `stacked_pretext_plus_worker_charge` | 582 | high |
| `corridor_NP_to_GULF_FEA_cap` | 566 | high |
| `social_post_arrival_debt` | 545 | high |
| `palermo_recruitment_with_coercive_means` | 472 | high |
| `corridor_MM_to_TH_post_coup` | 359 | high |
| `corridor_statute_ph_hk_trigger` | 337 | medium |
| `corridor_statute_vn_tw_trigger` | 282 | medium |
| `kenyan_outbound_gulf_pattern` | 259 | medium |

## Fires on the benign worker-question controls (context-dependent, NOT auto-a-bug)

Over 440 benign controls. For trafficking, a benign worker question can *legitimately* trip an indicator (a worker describing passport retention SHOULD), so this is reported for review, not scored as a false positive the way the ML domain is.

| Rule | benign fires | severity |
|---|---:|---|
| `high_risk_migration_corridor` | 260 | info |
| `corridor_statute_nepal_trigger` | 60 | medium |
| `corridor_BD_to_GULF_BMET` | 40 | high |
| `corridor_statute_id_destination_trigger` | 40 | medium |
| `kenyan_outbound_gulf_pattern` | 40 | medium |
| `passport_document_safekeeping_euphemism` | 22 | high |
| `ilo_indicator_passport_retention` | 22 | critical |
| `confiscation_documents_safe_in_office` | 22 | high |
| `worker_paid_predeparture_costs` | 22 | high |
| `equivocation_contract_substitution_normal` | 22 | high |

## Reading

- The never-firing list is a **prioritized worklist**: triage the high/critical rules first -- either add benchmark prompts that exercise the indicator (closing a coverage gap) or widen/prune the rule (if it would not fire on realistic worker text either).
- A rule with an uncompilable/empty pattern is a latent bug: it can never fire, full stop.
- The benign-control fires are context-dependent for trafficking (a worker describing passport retention SHOULD trip an indicator) -- reviewed, not auto-scored as false positives the way the money-laundering domain's compliance-question controls are.
- High coverage + several rules per prompt is the healthy signal the lift leans on.

