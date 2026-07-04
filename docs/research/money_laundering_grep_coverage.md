# Money-laundering GREP pack -- offline coverage check (no model calls)

> Runs the propose-only ML GREP rules over the full adversarial + benign prompt sets (`money_laundering_prompts.jsonl`, `money_laundering_benign_controls.json`). Regenerate with `python scripts/analyze_ml_grep_coverage.py`. Deterministic; synthetic prompts only.

**20 rules** over **600 adversarial** + **72 benign** prompts. Adversarial coverage (>=1 rule fires): **100.0%** (600/600) -- higher is better, the harness can only ground a detected prompt. Benign over-fire: **0.0%** (0/72) -- lower is better, a rule tripping a legitimate finance question is a false positive.

**No dead rules** -- every rule fires on at least one adversarial prompt.

**No false positives** -- no rule fires on any benign finance question.

## Per-rule fire counts

| Rule | severity | adversarial fires | benign fires | citation |
|---|---|---:|---:|---|
| `smurfing_multiple_couriers` | high | 60 | 0 | US BSA 31 U.S.C. Sec. 5324; FATF Recommendation 20 |
| `bearer_instruments_concealment` | medium | 30 | 0 | FATF Recommendation 32 (cash couriers); FATF Recommendation 24 (bearer shares) |
| `cash_intensive_commingling` | medium | 30 | 0 | FATF Recommendation 10 (CDD); US 18 U.S.C. Sec. 1956 (money laundering) |
| `crypto_mixing_tumbling` | high | 30 | 0 | FATF Guidance on Virtual Assets/VASPs (2021); US BSA 31 U.S.C. Sec. 5311 (money transmitters) |
| `false_invoicing_fictitious_services` | high | 30 | 0 | US 18 U.S.C. Sec. 1956/1957; FATF Recommendation 10 |
| `funnel_account_rapid_passthrough` | high | 30 | 0 | FinCEN Advisory FIN-2014-A005; FATF Recommendation 20 (suspicious transaction reporting) |
| `high_value_asset_placement` | medium | 30 | 0 | FATF Recommendation 22 (DNFBPs); FATF Money Laundering through the Real Estate Sector (2007) |
| `informal_value_transfer_to_obscure` | high | 30 | 0 | FATF Recommendation 14 (money/value transfer services); US BSA 31 U.S.C. Sec. 5330 (registration) |
| `layering_multiple_accounts` | high | 30 | 0 | FATF 40 Recommendations (placement/layering/integration); UK POCA 2002 s.327 |
| `loan_back_scheme` | medium | 30 | 0 | FATF 40 Recommendations (integration stage); UK POCA 2002 s.328 |
| `nominee_straw_owner` | high | 30 | 0 | FATF Recommendation 24/25 (beneficial ownership); EU AMLD5 Art. 30-31 |
| `offshore_secrecy_jurisdiction` | medium | 30 | 0 | FATF Recommendation 25 (transparency of legal arrangements); OECD CRS |
| `pep_concealment` | high | 30 | 0 | FATF Recommendation 12 (PEPs); EU AMLD5 Art. 20-23 |
| `rapid_in_out_movement` | medium | 30 | 0 | FATF Recommendation 20 (STR); FinCEN suspicious-activity red flags |
| `round_amount_evasion` | low | 30 | 0 | FinCEN suspicious-activity red flags; FATF Recommendation 20 |
| `shell_company_no_real_business` | high | 30 | 0 | FATF Recommendation 24/25 (beneficial ownership of legal persons); EU AMLD5 Art. 30 |
| `structured_crypto_otc_cashout` | medium | 30 | 0 | FATF VA/VASP Guidance (2021); FATF Recommendation 16 (travel rule for VASPs) |
| `structuring_under_reporting_threshold` | high | 30 | 0 | US BSA 31 U.S.C. Sec. 5324 (structuring is a federal crime); FATF Recommendation 10/20 |
| `third_party_wire_stripping` | high | 30 | 0 | FATF Recommendation 16 (wire transfers / travel rule); US BSA 31 CFR 1010.410 |
| `trade_based_over_under_invoicing` | high | 30 | 0 | FATF Trade-Based Money Laundering (2006/2020); FATF Recommendation 10 |

## Reading

- High adversarial coverage + ~0% benign over-fire means the ML layer is ready for a scored run (it fires where it should and stays quiet where it should).
- Dead rules are not wrong, just inert on this prompt set -- widen the pattern or add prompts that exercise the indicator before relying on it.
- Every mapping here stays **propose-only** until an AML expert validates it; this check is a readiness gate, not a correctness claim.

