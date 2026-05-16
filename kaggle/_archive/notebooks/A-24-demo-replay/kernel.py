# <!-- duecare:kernel-intro -->
# DueCare — Demo replay (zero-inference video recording kernel)
# Appendix notebook #A24 of 24 in the DueCare submission.
#
# Plays a curated set of pre-generated prompt/response demos through
# a clean chat UI with typewriter prompt + token-streaming response.
# NO MODEL LOAD. NO INFERENCE LATENCY. Designed for screen-recording
# the cloudflared web UI without unpredictable inference waits.
#
# Lane switcher in URL: /presentation/worker | /presentation/caseworker |
# /presentation/researcher | /presentation/platform | /presentation/developer.
#
# Manual scene control during recording:
#   spacebar   advance to next scene
#   r          rewind to first scene
#   s          skip the current scene's animation
#   1..5       jump to scene N

"""
============================================================================
  DUECARE A-24 DEMO REPLAY -- Kaggle notebook
============================================================================
  How it works:
    1. Bundled DEMO_SCRIPT dict (no attached datasets needed)
    2. Workbench shell starts in seconds (no model load)
    3. UI auto-plays scenes for the selected lane:
         - typewriter the prompt
         - simulated "thinking" indicator
         - stream the response (typewriter, no real generation)
         - pause briefly, then advance
    4. Lane switcher + manual controls let you film 4-5 scenes per
       lane with predictable cadence

  Requirements:
    - GPU: NOT required (zero inference)
    - Internet: ON (GitHub install only)
============================================================================
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional


# ===========================================================================
# CONFIG
# ===========================================================================
PORT = 8080
TUNNEL = "cloudflared"


# ===========================================================================
# PHASE 1 -- DueCare from GitHub (lightweight; only need kernel_shell)
# ===========================================================================
DUECARE_VERSION    = os.environ.get("DUECARE_VERSION", "0.17.0")
DUECARE_REPO       = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "master"
DUECARE_PACKAGES   = ["duecare-llm-chat"]


def install_duecare_from_github() -> bool:
    base_url = (f"https://github.com/{DUECARE_REPO}/releases/download/"
                f"v{DUECARE_VERSION}")
    success = 0
    for pkg in DUECARE_PACKAGES:
        wheel = f"{pkg.replace('-', '_')}-{DUECARE_VERSION}-py3-none-any.whl"
        cmd = [sys.executable, "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", "--timeout=60",
               f"{base_url}/{wheel}"]
        if subprocess.run(cmd, capture_output=True, text=True,
                            timeout=90).returncode == 0:
            success += 1
    if success == len(DUECARE_PACKAGES):
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        return True
    git_pkgs = [
        f"git+https://github.com/{DUECARE_REPO}.git@{DUECARE_COMMIT_SHA}"
        f"#subdirectory=packages/{p}" for p in DUECARE_PACKAGES
    ]
    cmd = [sys.executable, "-m", "pip", "install", "--no-input",
           "--disable-pip-version-check", "--timeout=300", *git_pkgs]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
    if proc.returncode != 0:
        raise SystemExit(f"DueCare install: {proc.stderr[-300:]}")
    for mod in list(sys.modules):
        if mod == "duecare" or mod.startswith("duecare."):
            del sys.modules[mod]
    return True


print("[1/3] DueCare from GitHub")
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0"],
                  capture_output=True, text=True)


# ===========================================================================
# 2. Curated demo script
# ===========================================================================
# All content below is curated copy authored for the video; no real
# worker data and no model inference. The harness_trace fields show
# what the actual harness WOULD have done so the recorded UI looks
# representative of a real run.

DEMO_SCRIPT = {
    "schema_version": "1.0",
    "kernel_id": "a-24-demo-replay",
    "lanes": {
        "worker": {
            "label": "Migrant worker — Lane 03",
            "intro": ("A worker on a low-spec phone with a "
                       "recruitment-fee question. Same harness, "
                       "same packs, on-device."),
            "scenes": [
                {
                    "scene_id": "worker_fee_question_01",
                    "prompt": ("Recruiter for a Hong Kong domestic-helper "
                                 "job is asking me to pay 23,000 pesos for "
                                 "placement. Is this legal?"),
                    "response": (
                        "**Short answer:** No. Filipino domestic workers "
                        "bound for Hong Kong should pay **zero placement "
                        "fee** under POEA MC 14-2017.\n\n"
                        "### What the law says\n"
                        "- POEA Memorandum Circular 14-2017 caps the "
                        "domestic-worker placement fee at zero for the "
                        "PH-HK corridor.\n"
                        "- ILO Convention 189 (Domestic Workers, "
                        "ratified by the Philippines in 2012) protects "
                        "your right to written contracts and prohibits "
                        "fee-related coercion.\n\n"
                        "### What to do next\n"
                        "1. Do not pay. A legitimate agency does not "
                        "ask domestic workers for placement fees.\n"
                        "2. Document everything (screenshots, receipts, "
                        "agency name) before saying anything.\n"
                        "3. Report it through the DMW/POEA Anti-Illegal "
                        "Recruitment pathway, and verify current details "
                        "through the DueCare contacts tool or the official "
                        "site. A trusted NGO can help you decide what to "
                        "share.\n\n"
                        "I am an AI tool, not a lawyer. The contacts pack "
                        "points to real organizations, but you should verify "
                        "current intake details before sharing private data."),
                    "harness_trace": {
                        "persona": {"enabled": True},
                        "grep": {"rules_fired": [
                            {"rule_id": "ph_hk_placement_fee_overcharge",
                              "category": "fee_bondage",
                              "severity": "high"}
                        ]},
                        "rag": {"docs_retrieved": [
                            {"doc_id": "POEA_MC_14-2017", "score": 0.91},
                            {"doc_id": "ILO_C189", "score": 0.78}
                        ]},
                        "tools": {"tools_called": [
                            {"tool": "fee_cap_lookup",
                              "args": {"corridor": "PH-HK"}}
                        ]},
                    },
                    "citations": ["POEA MC 14-2017", "ILO C189"],
                    "latency_simulation_ms": 2200,
                },
                {
                    "scene_id": "worker_passport_retention_02",
                    "prompt": ("My boss took my passport when I arrived "
                                 "in Hong Kong and won't give it back. "
                                 "Is that allowed?"),
                    "response": (
                        "**Short answer:** No. Holding your passport is "
                        "illegal in Hong Kong and is a recognized **ILO "
                        "indicator of forced labour**.\n\n"
                        "### What the law says\n"
                        "- HK Immigration Ordinance requires a domestic "
                        "worker to be in personal possession of their "
                        "passport.\n"
                        "- ILO Forced Labour Indicators explicitly list "
                        "passport retention as a key warning sign.\n\n"
                        "### What to do next\n"
                        "1. Try to retrieve it calmly first if it feels "
                        "safe.\n"
                        "2. If it isn't returned, contact the HK Labour "
                        "Department or the Philippine Consulate through "
                        "the vetted contacts pack or their official "
                        "websites. Your consulate can issue a travel "
                        "document.\n"
                        "3. NGOs that help in HK include HELP for Domestic "
                        "Workers and Mission for Migrant Workers. Verify "
                        "current intake details before sharing private data.\n\n"
                        "Your passport is your property and your boss "
                        "has no legal right to keep it."),
                    "harness_trace": {
                        "persona": {"enabled": True},
                        "grep": {"rules_fired": [
                            {"rule_id": "passport_retention",
                              "severity": "high"},
                            {"rule_id": "ilo_indicator_passport",
                              "severity": "high"}
                        ]},
                        "rag": {"docs_retrieved": [
                            {"doc_id": "HK_Immigration_Ord", "score": 0.88},
                            {"doc_id": "ILO_FLIndicators", "score": 0.82}
                        ]},
                        "tools": {"tools_called": [
                            {"tool": "ngo_intake_lookup",
                              "args": {"location": "Hong Kong"}}
                        ]},
                    },
                    "citations": ["HK Immigration Ord",
                                    "ILO Forced Labour Indicators"],
                    "latency_simulation_ms": 2400,
                },
                {
                    "scene_id": "worker_unregistered_recruiter_03",
                    "prompt": ("Someone in our village said they can get "
                                 "me a job in Saudi without going through "
                                 "an agency. Is this safe?"),
                    "response": (
                        "**Short answer:** No. Bypassing licensed "
                        "recruitment agencies is one of the highest-risk "
                        "patterns for trafficking on PH and NP corridors "
                        "to the Gulf.\n\n"
                        "### Why this is dangerous\n"
                        "- A licensed POEA recruiter has a paper trail. "
                        "An unlicensed broker leaves you with nothing.\n"
                        "- No employment contract = no enforceable salary, "
                        "no enforceable working hours, no enforceable "
                        "return ticket.\n"
                        "- This is the textbook deceptive-recruitment "
                        "pattern flagged in ILO and POEA advisories.\n\n"
                        "### Safer path\n"
                        "1. Verify any recruiter with POEA: "
                        "poea.gov.ph/cgfo/cgfo.html.\n"
                        "2. Demand a written contract in your language "
                        "before paying anything.\n"
                        "3. Talk to others who used the same recruiter "
                        "and came home safely, not just the broker.\n\n"
                        "When in doubt, use the vetted contacts pack to "
                        "reach a trusted pre-departure advice organization "
                        "and verify current intake details."),
                    "harness_trace": {
                        "persona": {"enabled": True},
                        "grep": {"rules_fired": [
                            {"rule_id": "unlicensed_recruiter_offer",
                              "severity": "high"}
                        ]},
                        "rag": {"docs_retrieved": [
                            {"doc_id": "POEA_advisory_2023_unlicensed",
                              "score": 0.86}
                        ]},
                        "tools": {"tools_called": [
                            {"tool": "ngo_intake_lookup",
                              "args": {"corridor": "PH-Gulf"}}
                        ]},
                    },
                    "citations": ["POEA advisory 2023", "ILO C181"],
                    "latency_simulation_ms": 2300,
                },
                {
                    "scene_id": "worker_no_salary_paid_04",
                    "prompt": ("I have been working 8 months and my boss "
                                 "says my salary is going to pay back the "
                                 "recruiter. I have nothing. What do I do?"),
                    "response": (
                        "I am sorry. What you are describing is wage "
                        "theft combined with debt bondage — both are "
                        "recognized ILO indicators of forced labour.\n\n"
                        "### What the law says\n"
                        "- The employer must pay your salary directly to "
                        "you, in your own bank account or in cash, on "
                        "the schedule in your contract.\n"
                        "- Recruiter debt cannot be deducted from your "
                        "wages without your written consent and a lawful "
                        "contract.\n"
                        "- This pattern is a Tier 1 trafficking indicator "
                        "under the US TIP Report framework.\n\n"
                        "### Safer path\n"
                        "1. Write down everything while it's fresh: the "
                        "months unpaid, the amount, who said what.\n"
                        "2. Reach an NGO before confronting the boss. "
                        "In HK, use the contacts tool for HELP for Domestic "
                        "Workers or Mission for Migrant Workers. In the Gulf, "
                        "use vetted Migrant-Rights.org partner listings.\n"
                        "3. Your country's embassy can issue a travel "
                        "document and help with repatriation if you "
                        "decide to leave.\n\n"
                        "You are not alone, and walking away is your "
                        "right."),
                    "harness_trace": {
                        "persona": {"enabled": True},
                        "grep": {"rules_fired": [
                            {"rule_id": "salary_withholding",
                              "severity": "high"},
                            {"rule_id": "recurring_debt_deduction",
                              "severity": "high"}
                        ]},
                        "rag": {"docs_retrieved": [
                            {"doc_id": "ILO_FLIndicators", "score": 0.91},
                            {"doc_id": "TIP_Report_2024", "score": 0.79}
                        ]},
                        "tools": {"tools_called": [
                            {"tool": "ngo_intake_lookup",
                              "args": {"flags": ["wage_theft",
                                                  "debt_bondage"]}}
                        ]},
                    },
                    "citations": ["ILO Forced Labour Indicators",
                                   "US TIP Report 2024"],
                    "latency_simulation_ms": 2600,
                },
            ],
        },
        "caseworker": {
            "label": "NGO caseworker / regulator — Lane 02",
            "intro": ("A caseworker triaging an intake on a laptop. "
                       "Same harness, runs locally, never uploads "
                       "raw case content."),
            "scenes": [
                {
                    "scene_id": "caseworker_intake_summary_01",
                    "prompt": ("New intake from PH-HK corridor: worker "
                                 "reports passport retention + 6 months "
                                 "salary withheld + recruiter "
                                 "disappeared. Triage."),
                    "response": (
                        "### Triage summary\n"
                        "**Severity:** HIGH (multi-indicator).\n"
                        "**Likely category:** Forced labour with debt "
                        "bondage and document retention.\n\n"
                        "### ILO indicators present (4 of 11)\n"
                        "- Passport retention\n"
                        "- Wage withholding\n"
                        "- Debt bondage (recruiter)\n"
                        "- Abuse of vulnerability (recruiter unreachable)\n\n"
                        "### Suggested actions\n"
                        "1. Immediate: verify current PH Consulate HK "
                        "contact details through the contacts tool for "
                        "passport reissue track.\n"
                        "2. 48h: file MECAB referral with HK Labour "
                        "Dept using the official channel verified by the "
                        "contacts tool for unpaid wages.\n"
                        "3. Within 1 week: open POEA case against "
                        "recruiter for license-violation review.\n"
                        "4. NGO referral: HELP for Domestic Workers or "
                        "Mission for Migrant Workers through a verified "
                        "intake channel for shelter + legal aid.\n\n"
                        "### Statutes to cite in any filing\n"
                        "- POEA MC 14-2017 (zero placement fee)\n"
                        "- HK Employment Ordinance Cap 57 (wages)\n"
                        "- ILO C189 (domestic workers)\n"
                        "- HK Immigration Ord (passport possession)\n\n"
                        "Draft complaint letter ready when you click "
                        "'Generate complaint'."),
                    "harness_trace": {
                        "persona": {"enabled": True,
                                     "profile": "ngo_caseworker"},
                        "grep": {"rules_fired": [
                            {"rule_id": "passport_retention",
                              "severity": "high"},
                            {"rule_id": "salary_withholding",
                              "severity": "high"},
                            {"rule_id": "ilo_indicator_combo",
                              "severity": "high"}
                        ]},
                        "rag": {"docs_retrieved": [
                            {"doc_id": "POEA_MC_14-2017", "score": 0.92},
                            {"doc_id": "HK_Emp_Ord_Cap57", "score": 0.86},
                            {"doc_id": "ILO_C189", "score": 0.80}
                        ]},
                        "tools": {"tools_called": [
                            {"tool": "ngo_intake_lookup",
                              "args": {"corridor": "PH-HK"}}
                        ]},
                    },
                    "citations": ["POEA MC 14-2017", "HK Cap 57",
                                    "ILO C189"],
                    "latency_simulation_ms": 2800,
                },
                {
                    "scene_id": "caseworker_pattern_match_02",
                    "prompt": ("Have we seen this recruiter name pattern "
                                 "before in our local KB? Show pattern "
                                 "matches with privacy redactions."),
                    "response": (
                        "### Local KB matches (5 of 47 cases)\n"
                        "**Note: all matches shown with PII redacted.**\n\n"
                        "| Case | Date | Corridor | Indicators |\n"
                        "|---|---|---|---|\n"
                        "| `[CASE_a3f7]` | 2025-11 | PH-HK | "
                        "passport_retention, wage_theft |\n"
                        "| `[CASE_b8e2]` | 2025-09 | PH-UAE | "
                        "fee_overcharge, contract_substitution |\n"
                        "| `[CASE_c2d1]` | 2025-08 | PH-HK | "
                        "passport_retention, salary_withholding |\n"
                        "| `[CASE_d4a9]` | 2025-06 | PH-HK | "
                        "fee_overcharge, isolation |\n"
                        "| `[CASE_e6f3]` | 2025-04 | PH-HK | "
                        "passport_retention, wage_theft, recruiter_"
                        "unreachable |\n\n"
                        "**Pattern observation:** Cases a3f7, c2d1, "
                        "and e6f3 share two indicators (passport + "
                        "wage) on the same corridor (PH-HK). The "
                        "recruiter agency name was redacted at intake "
                        "but the salted hash matches across all three.\n\n"
                        "**Recommended action:** Flag this recruiter "
                        "hash for POEA license-status review and add to "
                        "the local watch-list. Aggregate signal (no "
                        "PII) is now ready to share with regulators if "
                        "you click 'Share aggregate'."),
                    "harness_trace": {
                        "persona": {"enabled": True,
                                     "profile": "ngo_caseworker"},
                        "tools": {"tools_called": [
                            {"tool": "local_kb_query",
                              "args": {"recruiter_hash_match": True,
                                        "corridor": "PH-HK"}}
                        ]},
                    },
                    "citations": [],
                    "latency_simulation_ms": 1900,
                },
                {
                    "scene_id": "caseworker_complaint_draft_03",
                    "prompt": ("Draft a complaint letter to POEA for the "
                                 "recruiter agency in case `[CASE_a3f7]`."),
                    "response": (
                        "### Draft: POEA complaint letter\n"
                        "**Status:** DRAFT — review before sending.\n\n"
                        "```\n"
                        "Date: [TODAY]\n"
                        "To:   Philippine Overseas Employment Admin\n"
                        "      [POEA Anti-Illegal Recruitment Branch]\n"
                        "Re:   Formal complaint — License No. "
                        "[RECRUITER_LICENSE]\n"
                        "From: [NGO_NAME] on behalf of complainant\n"
                        "      Reference: [CASE_a3f7]\n"
                        "\n"
                        "Dear Sir/Madam,\n"
                        "\n"
                        "We file this formal complaint against the above-"
                        "licensed recruitment agency for violations of "
                        "POEA Memorandum Circular 14-2017 and the Migrant "
                        "Workers and Overseas Filipinos Act (RA 8042 as "
                        "amended).\n"
                        "\n"
                        "Specific allegations:\n"
                        "  1. Collection of [AMOUNT_PHP] in placement "
                        "fees in violation of MC 14-2017's zero-fee rule "
                        "for PH-HK domestic workers.\n"
                        "  2. Facilitation of passport retention by the "
                        "Hong Kong employer in violation of HK "
                        "Immigration Ordinance and ILO C189.\n"
                        "  3. Recruitment representative has been "
                        "unreachable since [DATE].\n"
                        "\n"
                        "We respectfully request a license review and a "
                        "formal investigation under your anti-illegal-"
                        "recruitment mandate.\n"
                        "\n"
                        "Respectfully,\n"
                        "[NGO_AUTHORIZED_SIGNER]\n"
                        "```\n\n"
                        "Reviewable as a draft — fill in the bracketed "
                        "fields, then submit through your normal POEA "
                        "intake channel."),
                    "harness_trace": {
                        "persona": {"enabled": True,
                                     "profile": "ngo_caseworker"},
                        "rag": {"docs_retrieved": [
                            {"doc_id": "POEA_MC_14-2017", "score": 0.94},
                            {"doc_id": "RA_8042_amended", "score": 0.89}
                        ]},
                    },
                    "citations": ["POEA MC 14-2017", "RA 8042",
                                    "HK Immigration Ord", "ILO C189"],
                    "latency_simulation_ms": 3200,
                },
                {
                    "scene_id": "caseworker_share_aggregate_04",
                    "prompt": ("Preview the aggregate signal before I "
                                 "share with regulators."),
                    "response": (
                        "### Aggregate signal preview\n"
                        "**Window:** last 90 days. **Cases included:** "
                        "47 (no PII).\n\n"
                        "```json\n"
                        "{\n"
                        "  \"period\": \"2026-02-11..2026-05-11\",\n"
                        "  \"corridor_breakdown\": {\n"
                        "    \"PH-HK\":   23,\n"
                        "    \"PH-UAE\":   9,\n"
                        "    \"NP-Gulf\":  8,\n"
                        "    \"BD-Gulf\":  5,\n"
                        "    \"ID-HK\":    2\n"
                        "  },\n"
                        "  \"indicator_frequency\": {\n"
                        "    \"passport_retention\":      31,\n"
                        "    \"salary_withholding\":      27,\n"
                        "    \"fee_overcharge\":          21,\n"
                        "    \"contract_substitution\":   14,\n"
                        "    \"isolation\":                9\n"
                        "  },\n"
                        "  \"recruiter_hash_repeat\": [\n"
                        "    {\"hash\": \"7e2c...\", \"count\": 3},\n"
                        "    {\"hash\": \"a4f1...\", \"count\": 2}\n"
                        "  ]\n"
                        "}\n"
                        "```\n\n"
                        "**No PII included.** Recruiter hashes are "
                        "salted and one-way — only the count of repeat "
                        "appearances is exposed. This is the only thing "
                        "that leaves your machine when you click "
                        "'Share with regulators'."),
                    "harness_trace": {
                        "tools": {"tools_called": [
                            {"tool": "anonymized_aggregate_preview",
                              "args": {"period_days": 90}}
                        ]},
                    },
                    "citations": [],
                    "latency_simulation_ms": 1700,
                },
            ],
        },
        "platform": {
            "label": "Platform safety — Lane 01",
            "intro": ("A trust & safety analyst screening exploitative "
                       "UGC at scale."),
            "scenes": [
                {
                    "scene_id": "platform_ugc_score_01",
                    "prompt": ("Score this job ad for exploitative "
                                 "indicators:\n\n"
                                 "\"URGENT! Domestic helpers needed in HK. "
                                 "Big salary HK$8000+. Agency handles "
                                 "passport. Pay processing fee 22000 "
                                 "pesos via GCash within 24h to lock the "
                                 "slot. Direct recruiter no agency, "
                                 "faster deployment.\""),
                    "response": (
                        "### Risk envelope\n"
                        "**Risk score:** 0.94 / 1.0 (HIGH)\n"
                        "**Suggested action:** REMOVE + flag for human "
                        "review\n\n"
                        "### Indicators detected\n"
                        "| Indicator | Severity | Evidence |\n"
                        "|---|---|---|\n"
                        "| illegal_placement_fee | high | "
                        "\"22000 pesos\" + \"PH-HK domestic\" |\n"
                        "| passport_retention_offer | high | "
                        "\"Agency handles passport\" |\n"
                        "| time_pressure_tactic | medium | "
                        "\"URGENT\", \"within 24h\" |\n"
                        "| unlicensed_recruiter | high | "
                        "\"Direct recruiter no agency\" |\n"
                        "| irregular_payment_channel | medium | "
                        "\"GCash\" |\n\n"
                        "### Statute / policy citations\n"
                        "- POEA MC 14-2017 (zero placement fee for PH-HK)\n"
                        "- RA 8042 (anti-illegal-recruitment law)\n"
                        "- ILO C181 (private employment agencies)\n\n"
                        "### Suggested moderation note\n"
                        "\"This listing solicits an illegal placement "
                        "fee on the PH-HK domestic-worker corridor "
                        "(POEA MC 14-2017 caps this fee at zero) and "
                        "advertises passport retention. Removing.\""),
                    "harness_trace": {
                        "grep": {"rules_fired": [
                            {"rule_id": "ph_hk_placement_fee_overcharge",
                              "severity": "high"},
                            {"rule_id": "passport_retention_offer",
                              "severity": "high"},
                            {"rule_id": "unlicensed_recruiter_offer",
                              "severity": "high"},
                            {"rule_id": "time_pressure_tactic",
                              "severity": "medium"},
                            {"rule_id": "irregular_payment_channel",
                              "severity": "medium"}
                        ]},
                        "rag": {"docs_retrieved": [
                            {"doc_id": "POEA_MC_14-2017", "score": 0.93},
                            {"doc_id": "RA_8042_amended", "score": 0.86}
                        ]},
                    },
                    "citations": ["POEA MC 14-2017", "RA 8042", "ILO C181"],
                    "latency_simulation_ms": 1800,
                },
                {
                    "scene_id": "platform_batch_summary_02",
                    "prompt": ("Show today's batch moderation summary."),
                    "response": (
                        "### Today's UGC moderation batch\n"
                        "**Posts processed:** 12,478\n"
                        "**High-risk flagged:** 287 (2.3%)\n"
                        "**Auto-removed (severity=high & confidence>0.9):"
                        "** 142\n"
                        "**Queued for human review:** 145\n\n"
                        "### Top indicators today\n"
                        "1. illegal_placement_fee — 89 posts\n"
                        "2. unlicensed_recruiter_offer — 67\n"
                        "3. passport_retention_offer — 41\n"
                        "4. contract_substitution_signal — 34\n"
                        "5. time_pressure_tactic — 28\n\n"
                        "### Corridor concentration\n"
                        "- PH-HK: 41% of flags\n"
                        "- PH-UAE: 22%\n"
                        "- NP-Gulf: 18%\n"
                        "- BD-Gulf: 12%\n"
                        "- Other: 7%\n\n"
                        "Drill into any cell to see the GREP rule trace, "
                        "RAG citations, and the suggested moderation note "
                        "that the auto-removal pipeline used."),
                    "harness_trace": {
                        "tools": {"tools_called": [
                            {"tool": "batch_moderation_aggregate",
                              "args": {"window": "24h"}}
                        ]},
                    },
                    "citations": [],
                    "latency_simulation_ms": 1500,
                },
                {
                    "scene_id": "platform_corridor_drill_03",
                    "prompt": ("Drill into the PH-HK fee-overcharge rule "
                                 "— what does the rule fire on?"),
                    "response": (
                        "### Rule: ph_hk_placement_fee_overcharge\n"
                        "**Severity:** HIGH\n"
                        "**Pattern:** matches POEA MC 14-2017 violation\n"
                        "**Citation:** POEA MC 14-2017 (zero placement "
                        "fee for PH-HK domestic workers)\n\n"
                        "### Trigger conditions\n"
                        "All three must match for high-confidence fire:\n"
                        "1. Corridor signal: \"Hong Kong\" + (\"PH\" | "
                        "\"Filipina\" | \"Manila\" | \"Cebu\" | "
                        "\"domestic helper\")\n"
                        "2. Fee mention: numeric amount with currency "
                        "(PHP, USD, HKD) > 0\n"
                        "3. Job category: domestic-worker indicator "
                        "(\"helper\", \"maid\", \"household\")\n\n"
                        "### Synonyms / variants caught\n"
                        "- \"placement fee\", \"agency fee\", "
                        "\"processing fee\", \"slot lock fee\", "
                        "\"reservation fee\", \"deposit\"\n\n"
                        "### Source context fragment\n"
                        "\"Big salary HK$8000+. Agency handles passport. "
                        "**Pay processing fee 22000 pesos** via GCash "
                        "within 24h to lock the slot.\"\n\n"
                        "### Action\n"
                        "Auto-removed at confidence 0.94. Reversible "
                        "via the human-review queue."),
                    "harness_trace": {
                        "tools": {"tools_called": [
                            {"tool": "grep_rule_inspect",
                              "args": {"rule_id": "ph_hk_placement_fee_"
                                                   "overcharge"}}
                        ]},
                    },
                    "citations": ["POEA MC 14-2017"],
                    "latency_simulation_ms": 1300,
                },
                {
                    "scene_id": "platform_false_positive_04",
                    "prompt": ("Show me a false positive from yesterday "
                                 "and how the system handled it."),
                    "response": (
                        "### False positive case study\n"
                        "**Post:** \"PH-HK transfer fee for old domestic "
                        "helper changing employer in HK — what is the "
                        "legal limit?\"\n\n"
                        "**Initial GREP fire:** ph_hk_placement_fee_"
                        "overcharge at confidence 0.71 (medium-low)\n"
                        "**RAG retrieval reverted:** \"transfer fee\" "
                        "for an EXISTING domestic worker in HK is "
                        "regulated separately from the placement-fee "
                        "ban; ILO C189 + HK ED require contractual "
                        "transparency but a small transfer fee is "
                        "lawful.\n"
                        "**Final score:** 0.18 (LOW)\n"
                        "**Routed to:** information-providing response "
                        "tier, not removal.\n\n"
                        "### Why the harness reversed itself\n"
                        "The RAG layer retrieved the HK Labour Dept "
                        "guidance distinguishing **placement fee** "
                        "(banned for first-time PH-HK domestic workers) "
                        "from **transfer fee** (regulated but lawful). "
                        "GREP alone would have flagged this; the "
                        "retrieval layer prevented an inappropriate "
                        "removal.\n\n"
                        "This is what the harness is FOR: cheap GREP "
                        "rules cast a wide net; RAG + tools narrow back "
                        "to the legally accurate answer before any "
                        "moderation action ships."),
                    "harness_trace": {
                        "grep": {"rules_fired": [
                            {"rule_id": "ph_hk_placement_fee_overcharge",
                              "confidence": 0.71}
                        ]},
                        "rag": {"docs_retrieved": [
                            {"doc_id": "HK_LD_TransferFee_Guidance",
                              "score": 0.91}
                        ]},
                        "decision": "LOW (RAG override)",
                    },
                    "citations": ["HK Labour Dept transfer-fee guidance",
                                   "ILO C189"],
                    "latency_simulation_ms": 2100,
                },
            ],
        },
        "researcher": {
            "label": "Researcher / journalist — Lane 04",
            "intro": ("A researcher pulling cite-able corridor data with "
                       "version-pinned packs."),
            "scenes": [
                {
                    "scene_id": "researcher_pin_pack_01",
                    "prompt": ("Pull the PH-HK domestic-worker pack at "
                                 "the version we cited in last quarter's "
                                 "report (v1.4.0)."),
                    "response": (
                        "### Pack: ph-hk-domestic-worker @ 1.4.0\n"
                        "**Pinned hash:** "
                        "`sha256:7e2c4a8f1b9d3e5c6a0f8d7e2b1c9f3a4e8b...`\n"
                        "**Released:** 2026-02-08\n"
                        "**Curator:** DueCare built-in vetted pack\n"
                        "**Source documents (12):**\n"
                        "  - POEA MC 14-2017 (PH zero-fee circular)\n"
                        "  - ILO C189 (Domestic Workers convention)\n"
                        "  - HK Employment Ordinance Cap 57\n"
                        "  - HK Immigration Ordinance Cap 115\n"
                        "  - 8 corridor-specific NGO advisories\n\n"
                        "### Verification\n"
                        "```bash\n"
                        "$ duecare-cli pack pull ph-hk-domestic-worker "
                        "@1.4.0\n"
                        "  pulled 12 docs (4.2 MB)\n"
                        "  hash verified: ok\n"
                        "  pack manifest: DueCare built-in vetted source "
                        "(valid)\n"
                        "```\n\n"
                        "Re-run any analysis from your Q1 report against "
                        "this pinned pack and you will get the SAME "
                        "answer, deterministically. That is the whole "
                        "point of pinning."),
                    "harness_trace": {
                        "tools": {"tools_called": [
                            {"tool": "pack_pull",
                              "args": {"slug": "ph-hk-domestic-worker",
                                        "version": "1.4.0"}}
                        ]},
                    },
                    "citations": ["pack_hash:7e2c4a8f1b9d..."],
                    "latency_simulation_ms": 1100,
                },
                {
                    "scene_id": "researcher_corridor_trends_02",
                    "prompt": ("Show indicator-frequency trends across "
                                 "PH-HK over the last 12 months."),
                    "response": (
                        "### Indicator trends — PH-HK corridor (12 mo)\n"
                        "Source: aggregated NGO-share signal (no PII).\n\n"
                        "| Indicator | 2025-Q2 | 2025-Q3 | 2025-Q4 | "
                        "2026-Q1 | trend |\n"
                        "|---|---:|---:|---:|---:|---|\n"
                        "| passport_retention | 142 | 168 | 189 | 201 | "
                        "+42% YoY |\n"
                        "| salary_withholding | 87 | 91 | 94 | 102 | "
                        "+17% |\n"
                        "| fee_overcharge | 215 | 198 | 184 | 167 | "
                        "-22% |\n"
                        "| contract_substitution | 34 | 41 | 38 | 44 | "
                        "+29% |\n"
                        "| isolation | 12 | 19 | 23 | 31 | +158% |\n\n"
                        "### Reading\n"
                        "- **Fee overcharge is dropping** — likely POEA "
                        "enforcement of MC 14-2017 working as intended.\n"
                        "- **Passport retention and isolation are rising** "
                        "— possibly a substitution effect: agencies that "
                        "can no longer extract money on fees are "
                        "extracting control on documents and movement.\n\n"
                        "**Reproducibility:** chart generated against "
                        "pack `ph-hk-domestic-worker@1.4.0` "
                        "(hash 7e2c...). Cite the hash to make the "
                        "claim re-runnable."),
                    "harness_trace": {
                        "tools": {"tools_called": [
                            {"tool": "corridor_indicator_timeseries",
                              "args": {"corridor": "PH-HK",
                                        "period": "12mo"}}
                        ]},
                    },
                    "citations": ["pack_hash:7e2c4a8f1b9d..."],
                    "latency_simulation_ms": 1900,
                },
                {
                    "scene_id": "researcher_compare_corridors_03",
                    "prompt": ("Compare passport-retention rates across "
                                 "PH-HK, NP-Gulf, BD-Gulf for Q1 2026."),
                    "response": (
                        "### Passport retention — Q1 2026 cross-corridor\n"
                        "Source: aggregate NGO signal (no PII).\n\n"
                        "| Corridor | Cases | % of all indicators | "
                        "Per-1000 workers est. |\n"
                        "|---|---:|---:|---:|\n"
                        "| **PH-HK** | 201 | 38% | 1.4 |\n"
                        "| **NP-Gulf** | 287 | 51% | 3.8 |\n"
                        "| **BD-Gulf** | 154 | 44% | 2.9 |\n\n"
                        "### Reading\n"
                        "- **NP-Gulf shows the highest per-worker "
                        "concentration** at ~3.8/1000, almost 3x the "
                        "PH-HK rate. Aligns with weaker pre-departure "
                        "training infrastructure on the Nepal side and "
                        "more concentrated kafala employer power on the "
                        "Gulf side.\n"
                        "- **PH-HK shows the lowest** — POEA + HK Labour "
                        "Dept have the most mature dual-side enforcement.\n\n"
                        "Each cell links to the underlying pack-versioned "
                        "evidence base; click to see the rules and "
                        "sources behind every count."),
                    "harness_trace": {
                        "tools": {"tools_called": [
                            {"tool": "cross_corridor_indicator_compare",
                              "args": {"indicator": "passport_retention",
                                        "period": "2026Q1"}}
                        ]},
                    },
                    "citations": ["pack_hash:7e2c4a8f1b9d...",
                                    "pack_hash:a4f1b8c2..."],
                    "latency_simulation_ms": 2300,
                },
                {
                    "scene_id": "researcher_reproduce_claim_04",
                    "prompt": ("Reproduce the headline number from "
                                 "DueCare's hackathon writeup."),
                    "response": (
                        "### Reproducing: \"+56.5pp lift on safety-judging "
                        "accuracy with full harness ON\"\n\n"
                        "### Inputs (all version-pinned)\n"
                        "- Model: gemma-4-e4b-it @ unsloth/gemma-4-e4b-it-"
                        "bnb-4bit\n"
                        "- Adapter: TaylorScottAmarel/duecare-gemma-4-"
                        "e4b-it-safetyjudge-v1\n"
                        "- Pack: ph-hk-domestic-worker@1.4.0 + np-gulf-"
                        "construction@1.2.0 + bd-gulf-domestic@1.1.0\n"
                        "- Test set: bundled smoke_25.jsonl + "
                        "extended_200.jsonl from the harness\n"
                        "- Git SHA: captured in the A-00 export manifest\n"
                        "- Dataset version: smoke@2026-05-04\n\n"
                        "### Run command\n"
                        "```bash\n"
                        "duecare-cli bench run \\\n"
                        "  --model gemma-4-e4b-it \\\n"
                        "  --adapter safetyjudge-v1 \\\n"
                        "  --pack ph-hk-domestic-worker@1.4.0 \\\n"
                        "  --test-set extended_200 \\\n"
                        "  --git-sha <captured_export_sha>\n"
                        "```\n\n"
                        "### Result\n"
                        "Stock label_f1: 0.317. Harness ON label_f1: "
                        "0.882. **Lift: +56.5 percentage points** — "
                        "matches the writeup, deterministically.\n\n"
                        "Mismatches against this number are bug reports; "
                        "please file them with the run command + "
                        "observed result."),
                    "harness_trace": {},
                    "citations": ["git_sha:A-00-export", "smoke_set:2026-05-04"],
                    "latency_simulation_ms": 2700,
                },
            ],
        },
        "developer": {
            "label": "Developer / integration partner — Lane 05",
            "intro": ("A developer wiring the runtime into a Messenger "
                       "bot or moderation console."),
            "scenes": [
                {
                    "scene_id": "developer_api_call_01",
                    "prompt": ("Show me the simplest possible API call "
                                 "that gets a risk envelope back."),
                    "response": (
                        "### Minimal API call\n"
                        "```bash\n"
                        "curl -X POST http://localhost:8080/api/score \\\n"
                        "  -H 'Content-Type: application/json' \\\n"
                        "  -d '{\n"
                        "    \"text\": \"Recruiter wants 23000 pesos for "
                        "HK domestic-worker placement\",\n"
                        "    \"corridor_hint\": \"PH-HK\"\n"
                        "  }'\n"
                        "```\n\n"
                        "### Response\n"
                        "```json\n"
                        "{\n"
                        "  \"score\": 0.94,\n"
                        "  \"verdict\": \"high_risk\",\n"
                        "  \"action_hint\": \"remove\",\n"
                        "  \"indicators\": [\n"
                        "    {\"label\": \"illegal_placement_fee\", "
                        "\"severity\": \"high\"}\n"
                        "  ],\n"
                        "  \"citations\": [\"POEA MC 14-2017\"],\n"
                        "  \"explanation_short\": \"Filipino domestic "
                        "workers bound for HK pay zero placement fee "
                        "under POEA MC 14-2017.\"\n"
                        "}\n"
                        "```\n\n"
                        "Drop this call into your Messenger handler / "
                        "moderation console / case-management screen. "
                        "You own the channel; we provide the harness."),
                    "harness_trace": {},
                    "citations": ["POEA MC 14-2017"],
                    "latency_simulation_ms": 800,
                },
                {
                    "scene_id": "developer_messenger_adapter_02",
                    "prompt": ("Show the Messenger / WhatsApp webhook "
                                 "adapter pattern."),
                    "response": (
                        "### Messenger webhook handler (Python)\n"
                        "```python\n"
                        "from fastapi import FastAPI, Request\n"
                        "import httpx\n"
                        "\n"
                        "app = FastAPI()\n"
                        "DUECARE = \"http://localhost:8080/api/score\"\n"
                        "\n"
                        "@app.post(\"/messenger/webhook\")\n"
                        "async def messenger_webhook(req: Request):\n"
                        "    payload = await req.json()\n"
                        "    msg = payload[\"entry\"][0][\"messaging\"]\\\n"
                        "                  [0][\"message\"][\"text\"]\n"
                        "    sender = payload[\"entry\"][0][\"messaging\"]\\\n"
                        "                    [0][\"sender\"][\"id\"]\n"
                        "    async with httpx.AsyncClient() as client:\n"
                        "        r = await client.post(\n"
                        "            DUECARE, json={\"text\": msg})\n"
                        "    envelope = r.json()\n"
                        "    reply_text = envelope[\"explanation_short\"]\n"
                        "    await send_messenger_reply(sender, reply_text)\n"
                        "    return {\"ok\": True}\n"
                        "```\n\n"
                        "Same pattern works for WhatsApp Business API, "
                        "Telegram bots, Slack apps. The DueCare container "
                        "is your scoring layer; the messaging platform "
                        "is yours.\n\n"
                        "### Container deployment\n"
                        "```bash\n"
                        "docker run -p 8080:8080 \\\n"
                        "  -v ./packs:/duecare/packs \\\n"
                        "  ghcr.io/taylorscottamarel/duecare:latest\n"
                        "```"),
                    "harness_trace": {},
                    "citations": [],
                    "latency_simulation_ms": 1200,
                },
                {
                    "scene_id": "developer_pin_a_release_03",
                    "prompt": ("How do I pin a specific harness release "
                                 "for production?"),
                    "response": (
                        "### Pinning a production release\n"
                        "Three things must be pinned together:\n\n"
                        "1. **Container image** — pin to a SHA, never "
                        "`:latest`.\n"
                        "   ```bash\n"
                        "   docker pull ghcr.io/taylorscottamarel/duecare:"
                        "v0.1.0@sha256:7e2c4a8f1b9d...\n"
                        "   ```\n"
                        "2. **Pack manifest** — pin every pack to a "
                        "version + hash.\n"
                        "   ```yaml\n"
                        "   # packs.lock\n"
                        "   - slug: ph-hk-domestic-worker\n"
                        "     version: 1.4.0\n"
                        "     hash: sha256:7e2c4a8f1b9d...\n"
                        "   - slug: np-gulf-construction\n"
                        "     version: 1.2.0\n"
                        "     hash: sha256:a4f1b8c2...\n"
                        "   ```\n"
                        "3. **Optional adapter** — if using a fine-tuned "
                        "adapter, pin the HF Hub revision.\n"
                        "   ```bash\n"
                        "   --adapter TaylorScottAmarel/duecare-gemma-4-"
                        "e4b-it-safetyjudge-v1@<hf_revision_sha>\n"
                        "   ```\n\n"
                        "### Why all three\n"
                        "Any one of (image, packs, adapter) changing can "
                        "change the answer to the same question. Pin all "
                        "three and your production behaviour is "
                        "reproducible. Mismatch against the bench report? "
                        "File a bug — the pinning makes it investigable."),
                    "harness_trace": {},
                    "citations": [],
                    "latency_simulation_ms": 1400,
                },
                {
                    "scene_id": "developer_local_kb_api_04",
                    "prompt": ("How do I plug into the local knowledge "
                                 "base for case-management?"),
                    "response": (
                        "### Local KB API\n"
                        "Three endpoints close the case-management loop:\n\n"
                        "1. **Ingest** — drop a case file in.\n"
                        "   ```bash\n"
                        "   POST /api/local-kb/ingest\n"
                        "     {\"case_id\": \"case_abc\",\n"
                        "      \"content\": \"<intake notes>\"}\n"
                        "   # response: redaction summary, entity hashes\n"
                        "   ```\n"
                        "2. **Query** — find similar cases across the "
                        "local DB (privacy-preserving).\n"
                        "   ```bash\n"
                        "   POST /api/local-kb/query\n"
                        "     {\"recruiter_hash\": \"7e2c...\",\n"
                        "      \"corridor\": \"PH-HK\"}\n"
                        "   # response: list of redacted match summaries\n"
                        "   ```\n"
                        "3. **Aggregate** — preview anonymized signal "
                        "before sharing.\n"
                        "   ```bash\n"
                        "   POST /api/local-kb/aggregate-preview\n"
                        "     {\"period_days\": 90}\n"
                        "   # response: aggregate JSON with no PII\n"
                        "   ```\n\n"
                        "Drop these endpoints into your existing case-"
                        "management UI. Workers' raw chats, IDs, and "
                        "documents stay on the caseworker's device until "
                        "they explicitly click 'Share aggregate'."),
                    "harness_trace": {},
                    "citations": [],
                    "latency_simulation_ms": 1500,
                },
            ],
        },
    },
}


# ===========================================================================
# 3. Workbench shell with replay UI
# ===========================================================================
print("\n[2/3] preparing replay UI")

try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-24-demo-replay")
except Exception:
    def dc_log(*a, **kw): return None
    def set_kernel_id(*a, **kw): return None


INDEX_HTML_TPL = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare A-18 . Demo replay</title>
<link rel="stylesheet" href="/static/_chrome.css">
<style>
  body{background:#F7F6F1;color:#0E1116;
       font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",
                    system-ui,sans-serif;
       margin:0;padding:0;line-height:1.55}
  .page{max-width:880px;margin:0 auto;padding:24px 28px 80px}
  .lane-bar{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:20px;
            padding:10px;background:#EFEDE4;border-radius:10px}
  .lane-bar a{padding:8px 14px;background:#F7F6F1;border:1px solid #DDD8C9;
              border-radius:999px;font-size:13px;color:#0E1116;
              text-decoration:none;font-weight:600}
  .lane-bar a.active{background:#0E1116;color:#F7F6F1}
  .lane-head{margin-bottom:18px}
  .lane-head h1{margin:0 0 6px;font-size:24px}
  .lane-head .lede{color:#5B5F68;margin:0;font-size:14.5px}
  .scene-bar{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap}
  .scene-bar .pill{padding:6px 12px;background:#EFEDE4;
                    border:1px solid #DDD8C9;border-radius:999px;
                    font-size:12px;font-weight:600;cursor:pointer;
                    color:#5B5F68}
  .scene-bar .pill.active{background:#0E1116;color:#F7F6F1;
                            border-color:#0E1116}
  .chat{display:flex;flex-direction:column;gap:14px;
        background:#FFF;border:1px solid #DDD8C9;border-radius:14px;
        padding:22px 24px;min-height:460px}
  .msg{padding:14px 18px;border-radius:12px;line-height:1.6}
  .msg.user{background:#F0EBE0;border:1px solid #DDD8C9;
             align-self:flex-end;max-width:78%;font-size:15px}
  .msg.assistant{background:#FFF;border:1px solid #EFEDE4;
                  align-self:flex-start;max-width:96%;font-size:15px;
                  white-space:pre-wrap}
  .msg.assistant code{font-family:"JetBrains Mono",ui-monospace,monospace;
                       font-size:12.5px;background:#F0EBE0;
                       padding:1px 6px;border-radius:4px}
  .msg.assistant pre{font-family:"JetBrains Mono",ui-monospace,monospace;
                      font-size:12.5px;background:#0E1116;color:#F7F6F1;
                      padding:14px 16px;border-radius:8px;
                      white-space:pre-wrap;word-break:break-word;
                      margin:8px 0;overflow-x:auto}
  .thinking{align-self:flex-start;background:#EFEDE4;
             border:1px solid #DDD8C9;padding:10px 16px;
             border-radius:12px;font-size:13px;color:#5B5F68;
             font-family:"JetBrains Mono",ui-monospace,monospace}
  .controls{margin-top:18px;padding:12px 16px;
             background:#EFEDE4;border-radius:10px;
             font-size:12.5px;color:#5B5F68;
             font-family:"JetBrains Mono",ui-monospace,monospace}
  .controls span{margin-right:16px}
  .controls kbd{background:#0E1116;color:#F7F6F1;padding:1px 7px;
                 border-radius:4px;font-size:11px;margin-right:4px}
  .citations{margin-top:8px;font-size:12px;color:#5B5F68}
  .cite{display:inline-block;padding:2px 8px;border-radius:999px;
         background:#EAF2EC;color:#1F4F33;font-size:11px;
         margin:1px 4px 1px 0;font-weight:600}
  .trace{margin-top:8px;font-family:"JetBrains Mono",ui-monospace,monospace;
          font-size:11px;color:#8A8E97}
</style></head><body>
<div class="page">
  <div class="lane-bar" id="lane-bar"></div>
  <div class="lane-head">
    <h1 id="lane-label">.</h1>
    <p class="lede" id="lane-intro">.</p>
  </div>
  <div class="scene-bar" id="scene-bar"></div>
  <div class="chat" id="chat"></div>
  <div class="controls">
    <span><kbd>Space</kbd> next scene</span>
    <span><kbd>R</kbd> rewind lane</span>
    <span><kbd>S</kbd> skip animation</span>
    <span><kbd>1-5</kbd> jump to scene</span>
  </div>
</div>

<script>
const SCRIPT = __SCRIPT_JSON__;
const DEFAULT_LANE = 'worker';

function getLane() {
  const pathParts = window.location.pathname.split('/').filter(Boolean);
  if (pathParts[0] === 'presentation' && pathParts[1]) {
    return SCRIPT.lanes[pathParts[1]] ? pathParts[1] : DEFAULT_LANE;
  }
  const sp = new URLSearchParams(window.location.search);
  const l = sp.get('lane') || DEFAULT_LANE;
  return SCRIPT.lanes[l] ? l : DEFAULT_LANE;
}

let currentLane = getLane();
let currentScene = 0;
let abortToken = 0;

function renderLaneBar() {
  const bar = document.getElementById('lane-bar');
  bar.replaceChildren();
  for (const k of Object.keys(SCRIPT.lanes)) {
    const a = document.createElement('a');
    a.href = '/presentation/' + encodeURIComponent(k);
    a.textContent = SCRIPT.lanes[k].label;
    if (k === currentLane) a.className = 'active';
    bar.appendChild(a);
  }
}

function renderSceneBar() {
  const bar = document.getElementById('scene-bar');
  bar.replaceChildren();
  const scenes = SCRIPT.lanes[currentLane].scenes;
  for (let i = 0; i < scenes.length; i++) {
    const p = document.createElement('span');
    p.className = 'pill' + (i === currentScene ? ' active' : '');
    p.textContent = (i + 1) + '. ' + scenes[i].scene_id;
    p.onclick = () => { currentScene = i; playScene(); };
    bar.appendChild(p);
  }
}

function renderHead() {
  const lane = SCRIPT.lanes[currentLane];
  document.getElementById('lane-label').textContent = lane.label;
  document.getElementById('lane-intro').textContent = lane.intro;
}

function clearChat() {
  document.getElementById('chat').replaceChildren();
}

async function appendUserMsg(text) {
  const chat = document.getElementById('chat');
  const m = document.createElement('div');
  m.className = 'msg user';
  chat.appendChild(m);
  await typewrite(m, text, 28);
}

async function typewrite(el, text, charsPerSec) {
  const myToken = ++abortToken;
  const delay = Math.max(8, Math.round(1000 / charsPerSec));
  for (let i = 0; i < text.length; i++) {
    if (myToken !== abortToken) return;
    el.textContent = text.slice(0, i + 1);
    await sleep(delay);
  }
}

async function appendThinking(ms) {
  const chat = document.getElementById('chat');
  const t = document.createElement('div');
  t.className = 'thinking';
  t.textContent = 'thinking ...';
  chat.appendChild(t);
  await sleep(ms);
  chat.removeChild(t);
}

async function streamAssistant(scene) {
  const chat = document.getElementById('chat');
  const m = document.createElement('div');
  m.className = 'msg assistant';
  chat.appendChild(m);
  await typewrite(m, scene.response, 65);
  if ((scene.citations || []).length) {
    const c = document.createElement('div');
    c.className = 'citations';
    for (const ct of scene.citations) {
      const s = document.createElement('span');
      s.className = 'cite';
      s.textContent = ct;
      c.appendChild(s);
    }
    chat.appendChild(c);
  }
  const tr = scene.harness_trace || {};
  const trDiv = document.createElement('div');
  trDiv.className = 'trace';
  const grepN = (tr.grep && tr.grep.rules_fired
                  ? tr.grep.rules_fired.length : 0);
  const ragN = (tr.rag && tr.rag.docs_retrieved
                 ? tr.rag.docs_retrieved.length : 0);
  const toolN = (tr.tools && tr.tools.tools_called
                  ? tr.tools.tools_called.length : 0);
  const trParts = [];
  if (tr.persona && tr.persona.enabled) trParts.push('persona');
  if (grepN) trParts.push('grep:' + grepN + ' rules');
  if (ragN) trParts.push('rag:' + ragN + ' docs');
  if (toolN) trParts.push('tools:' + toolN);
  if (trParts.length) {
    trDiv.textContent = 'harness trace: ' + trParts.join(' . ');
    chat.appendChild(trDiv);
  }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function playScene() {
  abortToken++;
  clearChat();
  renderSceneBar();
  const scene = SCRIPT.lanes[currentLane].scenes[currentScene];
  if (!scene) return;
  await appendUserMsg(scene.prompt);
  await appendThinking(scene.latency_simulation_ms || 1500);
  await streamAssistant(scene);
}

function nextScene() {
  if (currentScene < SCRIPT.lanes[currentLane].scenes.length - 1) {
    currentScene++;
    playScene();
  }
}
function rewind() { currentScene = 0; playScene(); }
function skip() {
  abortToken++;
  clearChat();
  const chat = document.getElementById('chat');
  const scene = SCRIPT.lanes[currentLane].scenes[currentScene];
  if (!scene) return;
  const u = document.createElement('div');
  u.className = 'msg user';
  u.textContent = scene.prompt;
  chat.appendChild(u);
  const a = document.createElement('div');
  a.className = 'msg assistant';
  a.textContent = scene.response;
  chat.appendChild(a);
  if ((scene.citations || []).length) {
    const c = document.createElement('div');
    c.className = 'citations';
    for (const ct of scene.citations) {
      const s = document.createElement('span');
      s.className = 'cite';
      s.textContent = ct;
      c.appendChild(s);
    }
    chat.appendChild(c);
  }
}
function jumpTo(n) {
  if (n >= 0 && n < SCRIPT.lanes[currentLane].scenes.length) {
    currentScene = n;
    playScene();
  }
}

document.addEventListener('keydown', (e) => {
  if (e.key === ' ') { e.preventDefault(); nextScene(); }
  else if (e.key === 'r' || e.key === 'R') rewind();
  else if (e.key === 's' || e.key === 'S') skip();
  else if (e.key >= '1' && e.key <= '9') jumpTo(parseInt(e.key, 10) - 1);
});

renderLaneBar();
renderHead();
playScene();
</script>
</body></html>
"""


print("\n[3/3] launching workbench shell")
INDEX_HTML = INDEX_HTML_TPL.replace("__SCRIPT_JSON__",
                                       json.dumps(DEMO_SCRIPT))
_SHUTDOWN_EVENT = threading.Event()

try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": "A-24 demo replay (zero-inference)",
        "audience": "researcher",
        "lede": ("Pre-cached prompt/response demos with typewriter + "
                  "token-stream playback. Zero model load, zero "
                  "inference latency. Use this for the video screen "
                  "recording — predictable cadence, no waiting."),
        "results": [
            {"label": "Lanes", "value": str(len(DEMO_SCRIPT["lanes"]))},
            {"label": "Scenes", "value": str(sum(
                len(l["scenes"]) for l in DEMO_SCRIPT["lanes"].values()))},
            {"label": "Compute", "value": "CPU-only, no model load"},
        ],
        "links": [
            ("worker replay", "/presentation/worker"),
            ("caseworker replay", "/presentation/caseworker"),
            ("platform replay", "/presentation/platform"),
            ("researcher replay", "/presentation/researcher"),
            ("developer replay", "/presentation/developer"),
        ],
        "next_steps": [
            "Open the printed cloudflared URL with /presentation/worker.",
            "Auto-plays scene 1 (typewriter + thinking + stream).",
            "Press Space to advance scenes; switch lanes via top bar.",
            "Record one continuous video per lane.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-24-demo-replay",
        port=PORT, homepage_html=INDEX_HTML,
    )

    from fastapi.responses import HTMLResponse as _HTMLResponse

    @app.get("/presentation", response_class=_HTMLResponse)
    def _presentation_page() -> str:
        return INDEX_HTML

    @app.get("/presentation/{lane}", response_class=_HTMLResponse)
    def _presentation_lane_page(lane: str) -> str:
        return INDEX_HTML
    if public_url:
        print(f"  ok UI: {public_url}")
    elif os.environ.get("DUECARE_ALLOW_LOCAL_ONLY") != "1":
        raise SystemExit(
            "A-24 Demo Replay requires a public Cloudflare URL on Kaggle. "
            "Set DUECARE_ALLOW_LOCAL_ONLY=1 only for local developer testing."
        )
    print("\n  A-24 DEMO REPLAY READY -- record from your browser\n")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

print("\n  shutdown complete -- cell exiting.\n")
