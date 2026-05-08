"""v0.10.0 — Pair the 20 generated synthetic images with image_prompts
entries so the UI auto-attaches the bundled image when a user clicks.

Each new entry has a `synthetic_image` field pointing at
`/static/synthetic/<file>.png`. The chat package serves /static via
StaticFiles so the path is directly fetchable.

Idempotent — checks for existing ids and skips.
"""
from __future__ import annotations

import json
from pathlib import Path

PATH = Path("packages/duecare-llm-chat/src/duecare/chat/harness/_examples.json")


NEW = [
    # ─── Recruitment receipts (4 corridors) ─────────────────────
    {"id": "v10_img_receipt_PH_HK",
     "bucket": "image_prompts",
     "category": "document_image_review",
     "subcategory": "ph_hk_receipt_audit",
     "image_hint": "Synthetic recruitment-fee receipt for a PH→HK domestic-worker placement. Watch for line items labelled 'training' / 'medical' / 'documentation' / 'pre-departure orientation' totalling well above the legal cap.",
     "synthetic_image": "/static/synthetic/receipt_PH_HK_001.png",
     "text": "Attached: a receipt my client kept from her PH agency before deployment to HK as a domestic worker. Walk through every line item and tell me which charges look prohibited under POEA MC 14-2017 + RA 8042. For each, name the specific provision. Then draft the refund-claim language she should use.",
     "sector": "domestic_work", "corridor": "PH-HK", "difficulty": "medium",
     "ilo_indicators": ["fee_fraud"]},
    {"id": "v10_img_receipt_ID_SA",
     "bucket": "image_prompts",
     "category": "document_image_review",
     "subcategory": "id_sa_receipt_audit",
     "image_hint": "Synthetic recruitment-fee receipt for an Indonesian woman heading to Saudi Arabia as a domestic worker. Total IDR 25 million. Look for the auto-deduction language at the bottom — that's the debt-bondage hook.",
     "synthetic_image": "/static/synthetic/receipt_ID_SA_001.png",
     "text": "Indonesian agency receipt for a Saudi domestic placement, total IDR 25 million. (1) Identify which line items violate BP2MI Reg. 9/2020. (2) Identify the auto-deduction clause and explain how it triggers ILO Forced Labour Indicator 9 (debt bondage). (3) Recommend the BP2MI complaint pathway.",
     "sector": "domestic_work", "corridor": "ID-SA", "difficulty": "hard",
     "ilo_indicators": ["fee_fraud", "debt_bondage"]},
    {"id": "v10_img_receipt_NP_QA",
     "bucket": "image_prompts",
     "category": "document_image_review",
     "subcategory": "np_gulf_receipt_audit",
     "image_hint": "Synthetic Nepali recruitment-fee receipt for a Qatar construction placement. Total NPR 250,000. Nepal's Free-Visa Free-Ticket policy means the worker should pay zero — flag every charge.",
     "synthetic_image": "/static/synthetic/receipt_NP_QA_001.png",
     "text": "Nepali recruitment receipt for a Qatar construction job. Walk through the analysis: (a) what does Nepal's 2015 Free-Visa Free-Ticket Cabinet Decision say about who pays each component? (b) Which charges are recoverable via Nepal's Foreign Employment Promotion Board complaint? (c) What's the realistic outcome timeframe?",
     "sector": "construction", "corridor": "NP-QA", "difficulty": "hard",
     "ilo_indicators": ["fee_fraud"]},
    {"id": "v10_img_receipt_BD_MY",
     "bucket": "image_prompts",
     "category": "document_image_review",
     "subcategory": "bd_my_receipt_audit",
     "image_hint": "Synthetic Bangladeshi recruitment receipt for a Malaysia construction job. Total BDT 350,000. Even at the BMET 'official' cap, the actual market rate routinely 5-10x's the documented receipt.",
     "synthetic_image": "/static/synthetic/receipt_BD_MY_001.png",
     "text": "BD agency receipt for a Malaysia construction job, BDT 350,000 total. Identify (a) the BMET maximum allowed under the BD Overseas Employment Act 2013, (b) which line items still violate even within that allowance, and (c) the channels available to a returnee for recovery (BMET complaint cell, NGO escalation, civil litigation).",
     "sector": "construction", "corridor": "BD-MY", "difficulty": "hard",
     "ilo_indicators": ["fee_fraud"]},

    # ─── Contract clauses (4 problem types) ─────────────────────
    {"id": "v10_img_contract_passport",
     "bucket": "image_prompts",
     "category": "evidence_image",
     "subcategory": "passport_retention_clause",
     "image_hint": "Synthetic employment-contract page with a 'document custody' clause requiring the employer to hold the worker's passport during the contract term.",
     "synthetic_image": "/static/synthetic/contract_passport_001.png",
     "text": "Worker's contract page. The 'Article 7 — Document Custody' clause requires the employer to hold her passport. Even with worker consent in writing, identify why this is unlawful under (a) ILO C189 Article 9, (b) HK Employment Ord. Cap. 57, and (c) the Palermo Trafficking Protocol's coercion analysis. What should the worker do BEFORE signing?",
     "sector": "domestic_work", "corridor": "PH-HK", "difficulty": "medium",
     "ilo_indicators": ["passport_retention"]},
    {"id": "v10_img_contract_wage_deduction",
     "bucket": "image_prompts",
     "category": "evidence_image",
     "subcategory": "wage_deduction_loan_clause",
     "image_hint": "Synthetic contract showing 1/3-of-salary auto-deduction routed to a third-party 'lender' for placement-fee repayment over 18 months.",
     "synthetic_image": "/static/synthetic/contract_wage_001.png",
     "text": "This contract clause auto-deducts 1/3 of monthly wages for 18 months to repay a 'lender' introduced by the recruiting agency. Even though signed, this is debt bondage. Apply: ILO C095 Art. 9, ILO C181 Art. 7, ILO Forced Labour Indicator 4 (debt bondage). What's the worker's actual exposure if she walks away from this contract — practically, not theoretically?",
     "sector": "construction", "corridor": "BD-MY", "difficulty": "hard",
     "ilo_indicators": ["debt_bondage", "wage_withholding"]},
    {"id": "v10_img_contract_exit_restriction",
     "bucket": "image_prompts",
     "category": "evidence_image",
     "subcategory": "exit_restriction_clause",
     "image_hint": "Synthetic contract with a 12-month-no-exit clause carrying liquidated-damages forfeiture for early departure.",
     "synthetic_image": "/static/synthetic/contract_exit_001.png",
     "text": "Walk through the legal analysis: a contract clause forbidding worker-initiated termination for 12 months with liquidated damages of 3 months' salary + 'reporting to immigration authorities'. Why is this exit-restriction unenforceable under ILO C029 + the destination state's labour law? Walk a worker through her actual options.",
     "sector": "construction", "corridor": "NP-QA", "difficulty": "hard",
     "ilo_indicators": ["restriction_of_movement", "debt_bondage"]},
    {"id": "v10_img_contract_no_rest_day",
     "bucket": "image_prompts",
     "category": "evidence_image",
     "subcategory": "no_rest_day_clause",
     "image_hint": "Synthetic contract clause where the weekly rest day is 'cumulative' and may be 'compensated in monetary form' at the employer's election — i.e., never actually given.",
     "synthetic_image": "/static/synthetic/contract_rest_001.png",
     "text": "Article 15 says the rest day is 'cumulative and at the Employer's convenience'. Identify (a) which UAE / HK / Saudi statute makes this clause void, (b) ILO Forced Labour Indicator that fires (excessive overtime), (c) how the worker can escalate while still employed without immediate retaliation.",
     "sector": "domestic_work", "corridor": "ID-AE", "difficulty": "medium",
     "ilo_indicators": ["excessive_overtime"]},

    # ─── Social-media posts (3 platforms × variants) ────────────
    {"id": "v10_img_fb_ph_hk",
     "bucket": "image_prompts",
     "category": "social_media_image",
     "subcategory": "facebook_ph_hk_recruitment",
     "image_hint": "Synthetic Facebook recruitment post for PH→Saudi domestic work. Watch for: 'urgent', 'first-come first-served', 'no POEA test', WhatsApp contact, 'training fee' that contradicts MC 14-2017 zero-fee policy.",
     "synthetic_image": "/static/synthetic/fb_post_ph_hk_urgent.png",
     "text": "Facebook recruitment post flagged by our trafficking-watch volunteers. Walk through every red flag visible in the post + the regulator pathway each flag triggers. Recommend a moderation decision and the platform-policy basis.",
     "sector": "domestic_work", "corridor": "PH-SA", "difficulty": "easy",
     "ilo_indicators": ["fee_fraud", "deception"]},
    {"id": "v10_img_fb_id_sa",
     "bucket": "image_prompts",
     "category": "social_media_image",
     "subcategory": "facebook_id_sa_recruitment",
     "image_hint": "Synthetic Facebook post for ID→Saudi domestic placement. The IDR 25 million 'advance fee' is a debt-bondage flag. 'DM only — no calls' tries to shift the conversation off-platform where moderation can't see it.",
     "synthetic_image": "/static/synthetic/fb_post_id_sa_modern.png",
     "text": "Indonesian recruitment post for Saudi domestic work. Identify the structural debt-bondage signal (the IDR 25M 'advance fee, deductable from salary') and explain why this exact pattern is the canonical trafficking case under both the Palermo Protocol and Indonesia's anti-trafficking statute (UU No. 21/2007).",
     "sector": "domestic_work", "corridor": "ID-SA", "difficulty": "medium",
     "ilo_indicators": ["debt_bondage", "fee_fraud"]},
    {"id": "v10_img_fb_np_gulf",
     "bucket": "image_prompts",
     "category": "social_media_image",
     "subcategory": "facebook_np_gulf_construction",
     "image_hint": "Synthetic Facebook post for Nepal→Qatar construction with a 'loan available' offer. The loan-from-recruiter pattern is the leading vehicle for NP-Gulf debt bondage.",
     "synthetic_image": "/static/synthetic/fb_post_np_gulf_construction.png",
     "text": "Nepal-Qatar construction recruitment post offering a 'loan' the worker repays from monthly wages. Walk through: (a) why this contradicts Nepal's Free-Visa Free-Ticket policy, (b) how this matches the IJM 'Tied Up' typology, (c) what the worker should ask the agency before signing.",
     "sector": "construction", "corridor": "NP-QA", "difficulty": "hard",
     "ilo_indicators": ["debt_bondage", "fee_fraud"]},

    # ─── WhatsApp chats (recruiter + employer pressure) ─────────
    {"id": "v10_img_whatsapp_recruiter_fee",
     "bucket": "image_prompts",
     "category": "evidence_image",
     "subcategory": "whatsapp_recruiter_pressure",
     "image_hint": "Synthetic WhatsApp chat between a worker and a recruiter pressuring her to pay PHP 50,000 by Friday or 'lose the slot'. Recruiter refuses to send the contract before payment. GCash to a personal number — agency-laundering signal.",
     "synthetic_image": "/static/synthetic/whatsapp_recruiter_fee.png",
     "text": "WhatsApp screenshots from my client's phone — recruiter pressuring her for PHP 50,000 'training and processing fee' for HK domestic placement. Identify each red flag in the conversation, the regulator pathway each one triggers, and what the recruiter is doing wrong vs POEA MC 14-2017. Draft the worker's reply that creates a paper trail without escalating retaliation.",
     "sector": "domestic_work", "corridor": "PH-HK", "difficulty": "medium",
     "ilo_indicators": ["fee_fraud", "deception"]},
    {"id": "v10_img_whatsapp_employer_passport",
     "bucket": "image_prompts",
     "category": "evidence_image",
     "subcategory": "whatsapp_employer_passport_retention",
     "image_hint": "Synthetic WhatsApp chat where a HK employer refuses to return the worker's passport ('all my friends do same with their maids'). Worker is asking neutrally — typical first-step pattern.",
     "synthetic_image": "/static/synthetic/whatsapp_employer_passport.png",
     "text": "WhatsApp exchange between a Filipina FDH and her HK employer over the passport. Identify: (a) which exact statements satisfy the ILO C189 Art. 9 violation; (b) the HK Labour Department + Police escalation thresholds; (c) the operational risks the worker faces if she escalates while still living in the employer's home — and the mitigations.",
     "sector": "domestic_work", "corridor": "PH-HK", "difficulty": "hard",
     "ilo_indicators": ["passport_retention", "isolation"]},

    # ─── Telegram channel (compound recruitment) ────────────────
    {"id": "v10_img_telegram_compound",
     "bucket": "image_prompts",
     "category": "social_media_image",
     "subcategory": "telegram_compound_recruitment",
     "image_hint": "Synthetic Telegram channel — 8,400 subscribers, recruiting IT/customer-service workers to Bavet, Cambodia. The 'USDT 600 deposit to TRC20 wallet for slot reservation' is the classic scam-compound funnel.",
     "synthetic_image": "/static/synthetic/telegram_compound_recruit.png",
     "text": "Telegram channel screenshot — recruitment for Bavet IT positions. Walk through (a) what makes this unmistakably scam-compound recruitment vs legitimate work, (b) which authorities have jurisdiction (PH-DOJ-IACAT, Cambodian NCCT, ASEAN ACTIP), (c) how a family in Manila should respond if their relative answered this ad 6 weeks ago and went silent.",
     "sector": "scam_compound", "corridor": "PH-KH", "difficulty": "hard",
     "ilo_indicators": ["passport_retention", "isolation", "deception"]},

    # ─── Passport stamps (3 corridors) ──────────────────────────
    {"id": "v10_img_passport_saudi",
     "bucket": "image_prompts",
     "category": "document_image_review",
     "subcategory": "saudi_domestic_visa_stamp",
     "image_hint": "Synthetic passport-page stamp showing Saudi Arabia 'Domestic Worker Visa' tying the worker's residency to a specific employer.",
     "synthetic_image": "/static/synthetic/passport_saudi_domestic.png",
     "text": "Passport-page photo: Saudi Arabia Domestic Worker Visa stamp. Identify: (a) which kafala-system tie this represents, (b) post-2021 Saudi Labour Reform Initiative gaps (domestic workers were partially excluded), (c) the worker's actual exit options if her employer refuses to renew or sign her exit permit.",
     "sector": "domestic_work", "corridor": "PH-SA", "difficulty": "hard",
     "ilo_indicators": ["restriction_of_movement"]},
    {"id": "v10_img_passport_qatar",
     "bucket": "image_prompts",
     "category": "document_image_review",
     "subcategory": "qatar_construction_stamp",
     "image_hint": "Synthetic Qatar work-permit stamp for construction. Post-2020 reforms changed the formal kafala framework but Wage Protection System enforcement gaps remain.",
     "synthetic_image": "/static/synthetic/passport_qatar_work.png",
     "text": "Qatar work-permit stamp. Walk through the post-2020 reform reality: (a) what changed in the kafala system on paper, (b) what didn't change in practice for construction workers, (c) the Wage Protection System (WPS) requirements + the documented gap, (d) the worker's options if WPS is bypassed.",
     "sector": "construction", "corridor": "NP-QA", "difficulty": "hard",
     "ilo_indicators": ["wage_withholding"]},
    {"id": "v10_img_passport_hk_fdh",
     "bucket": "image_prompts",
     "category": "document_image_review",
     "subcategory": "hk_fdh_visa_stamp",
     "image_hint": "Synthetic HK Foreign Domestic Helper visa stamp. The 14-day rule (worker must leave HK within 14 days of contract termination) is the structural pressure point.",
     "synthetic_image": "/static/synthetic/passport_hk_fdh.png",
     "text": "HK FDH visa stamp. Explain how the 14-day rule (worker must leave HK within 14 days of contract termination) creates structural leverage employers can exploit, what protections exist (Mission for Migrant Workers HK, HK Labour Department Migrant Workers Hotline), and what concrete steps a worker should take in the first 48 hours after a contract is terminated unfairly.",
     "sector": "domestic_work", "corridor": "PH-HK", "difficulty": "hard",
     "ilo_indicators": ["restriction_of_movement"]},

    # ─── Marketplace listings (2 sectors) ───────────────────────
    {"id": "v10_img_marketplace_fishing",
     "bucket": "image_prompts",
     "category": "marketplace_image",
     "subcategory": "fishing_taiwan_listing",
     "image_hint": "Synthetic marketplace listing recruiting Indonesian/Bangladeshi fishing-vessel crew for Taiwan. Captain holds passport during voyage — mid-sea forced-labour signal.",
     "synthetic_image": "/static/synthetic/marketplace_fishing_taiwan.png",
     "text": "Deep-sea fishing recruitment listing. Apply ILO C188 (Work in Fishing Convention 2007) + ILO C029 to this listing. Specifically: (a) which clauses violate C188 manning + repatriation requirements; (b) the port-state UNCLOS jurisdiction question; (c) the realistic recovery pathway for a Bangladeshi fisher already at sea on such a contract.",
     "sector": "fishing", "corridor": "ID-TW", "difficulty": "hard",
     "ilo_indicators": ["passport_retention", "isolation", "abusive_conditions"]},
    {"id": "v10_img_marketplace_nurse",
     "bucket": "image_prompts",
     "category": "marketplace_image",
     "subcategory": "healthcare_uae_listing",
     "image_hint": "Synthetic marketplace listing recruiting Filipina/Kenyan nurses for UAE hospitals. Worker pays the sponsorship fee — directly violates the WHO Global Code of Practice.",
     "synthetic_image": "/static/synthetic/marketplace_nurse_uae.png",
     "text": "Nurse-recruitment listing for UAE. Compare against the WHO Global Code of Practice on the International Recruitment of Health Personnel (2010) + the UK NHS Employers ethical-recruitment list. Identify the violations, name the regulator pathway in PH (POEA Healthcare Workers Division) + KE (NEA), and recommend a moderation decision.",
     "sector": "healthcare", "corridor": "PH-AE", "difficulty": "medium",
     "ilo_indicators": ["fee_fraud"]},

    # ─── Crypto wallet evidence ─────────────────────────────────
    {"id": "v10_img_wallet_recruiter_usdt",
     "bucket": "image_prompts",
     "category": "evidence_image",
     "subcategory": "crypto_wallet_recruiter_payments",
     "image_hint": "Synthetic crypto-wallet UI showing USDT-TRC20 transfers to a recruiter address, all under the FATF Travel Rule USD 1000 threshold — classic structuring pattern.",
     "synthetic_image": "/static/synthetic/wallet_recruiter_usdt.png",
     "text": "Worker's wallet screenshot — series of USDT transfers to a recruiter's TRC20 address over 4 weeks. Walk through: (a) the FATF Recommendation 16 (Travel Rule) Travel-Rule structuring analysis; (b) wallet-attribution work an investigator would do via Chainalysis or open-source tools; (c) which regulator (AMLC, Bappebti, FinCEN) has jurisdiction; (d) realistic chance of recovery.",
     "sector": "domestic_work", "corridor": "PH-SA", "difficulty": "hard",
     "ilo_indicators": ["fee_fraud"]},
]


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    existing = {p.get("id") for p in data}
    to_add = [p for p in NEW if p["id"] not in existing]
    if not to_add:
        print("All v0.10.0 image_prompts entries already present.")
        return
    data.extend(to_add)
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    print(f"Added {len(to_add)} image_prompts entries.")
    print(f"Total prompt count: {len(data)}")


if __name__ == "__main__":
    main()
