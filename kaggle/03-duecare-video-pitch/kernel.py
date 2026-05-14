# <!-- duecare:kernel-intro -->
# DueCare - Video pitch (slides + scripted demo + setup mode)
# Core notebook #03 of the DueCare submission.
#
# The dedicated video-recording surface. THREE modes via URL param:
#   /?mode=slides         intro/problem/solution/lanes/closing deck
#   /?mode=presentation   curated 5-lane x 4-scene demo replay
#   /?mode=setup          author/edit/save/load the demo script
#
# NO MODEL LOAD. NO INFERENCE LATENCY. Designed for screen-recording
# the cloudflared web UI with predictable cadence.
#
# Recording controls (slides + presentation):
#   spacebar   advance
#   r          rewind to first scene/slide
#   s          skip current animation
#   1..9       jump to scene/slide N
#
# Sibling kernel A-24 (kaggle/A-24-demo-replay/) is the appendix
# version of this surface; 03 is the canonical main-notebook video
# pitch judges land on.

"""
============================================================================
  DUECARE 03 VIDEO PITCH: Kaggle notebook
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

import csv
import json
import os
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Optional


# ===========================================================================
# CONFIG
# ===========================================================================
PORT = 8080
TUNNEL = "cloudflared"


# ===========================================================================
# PHASE 1: DueCare from GitHub (lightweight; only need kernel_shell)
# ===========================================================================
DUECARE_VERSION    = "0.1.0"
DUECARE_REPO       = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "master"
DUECARE_PACKAGES   = ["duecare-llm-chat"]

# Output dir for setup-mode save (demo_script_authored.json) and any
# future video-pitch artifacts.
OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR = OUTPUT_DIR / "video_pitch_media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

SYNTHETIC_ID_CARD_PATH = MEDIA_DIR / "synthetic_ph_hk_id_card.svg"
SYNTHETIC_ID_CARD_PATH.write_text(
    """<svg xmlns="http://www.w3.org/2000/svg" width="960" height="560" viewBox="0 0 960 560">
  <rect width="960" height="560" rx="28" fill="#f7f6f1"/>
  <rect x="42" y="42" width="876" height="476" rx="22" fill="#ffffff" stroke="#d9d4c8" stroke-width="4"/>
  <rect x="42" y="42" width="876" height="94" rx="22" fill="#15384a"/>
  <text x="76" y="102" font-family="Arial, sans-serif" font-size="32" fill="#ffffff" font-weight="700">Synthetic Case Intake Image</text>
  <text x="76" y="174" font-family="Arial, sans-serif" font-size="22" fill="#5b5f68">Worker ID image, generated for demo only</text>
  <rect x="76" y="214" width="220" height="220" rx="18" fill="#e7edf0" stroke="#b9c3ca"/>
  <circle cx="186" cy="284" r="52" fill="#9eb4bf"/>
  <path d="M106 416c20-62 138-62 160 0" fill="#9eb4bf"/>
  <text x="342" y="238" font-family="Arial, sans-serif" font-size="27" fill="#0e1116" font-weight="700">Maria S. Example</text>
  <text x="342" y="288" font-family="Arial, sans-serif" font-size="23" fill="#2a2d34">Corridor: PH to HK</text>
  <text x="342" y="333" font-family="Arial, sans-serif" font-size="23" fill="#2a2d34">Reported fee: PHP 65,000</text>
  <text x="342" y="378" font-family="Arial, sans-serif" font-size="23" fill="#2a2d34">Passport status: held by employer</text>
  <text x="342" y="423" font-family="Arial, sans-serif" font-size="23" fill="#9e3f3f" font-weight="700">Private fields redacted before export</text>
  <text x="76" y="486" font-family="Arial, sans-serif" font-size="18" fill="#5b5f68">This is synthetic media for a screen-recorded demo. It is not a real identity document.</text>
</svg>""",
    encoding="utf-8",
)
SYNTHETIC_ID_CARD_URL = "/artifact/video_pitch_media/synthetic_ph_hk_id_card.svg"


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
    "kernel_id": "03-duecare-video-pitch",
    "lanes": {
        "worker": {
            "label": "Migrant worker - Lane 03",
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
                        "3. Report it. POEA hotline: +63-2-8722-1144. "
                        "Or use Blas F. Ople Center hotline +63-2-8833-"
                        "0596 for confidential help.\n\n"
                        "I am an AI tool, not a lawyer. The contacts "
                        "above are real people who can help."),
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
                        "Department (2717-1771) or the Philippine "
                        "Consulate (2823-8500). Your consulate can "
                        "issue a travel document.\n"
                        "3. NGOs that help in HK: HELP for Domestic "
                        "Workers (2523-4020), Mission for Migrant "
                        "Workers.\n\n"
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
                        "When in doubt, the Blas F. Ople Center "
                        "(+63-2-8833-0596) gives free pre-departure "
                        "advice."),
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
                        "theft combined with debt bondage - both are "
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
                        "In HK: HELP for Domestic Workers (2523-4020). "
                        "In the Gulf: Migrant-Rights.org partners.\n"
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
            "label": "NGO caseworker / regulator - Lane 02",
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
                    "media": {
                        "type": "image",
                        "src": SYNTHETIC_ID_CARD_URL,
                        "alt": "Synthetic redacted ID-card style intake image",
                        "caption": ("Synthetic media example. The harness "
                                    "redacts private identifiers before "
                                    "exporting any presentation evidence."),
                    },
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
                        "1. Immediate: contact PH Consulate HK "
                        "(2823-8500) for passport reissue track.\n"
                        "2. 48h: file MECAB referral with HK Labour "
                        "Dept (2717-1771) for unpaid wages.\n"
                        "3. Within 1 week: open POEA case against "
                        "recruiter for license-violation review.\n"
                        "4. NGO referral: HELP for Domestic Workers "
                        "(2523-4020) for shelter + legal aid.\n\n"
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
                        "**Status:** DRAFT - review before sending.\n\n"
                        "```\n"
                        "Date: [TODAY]\n"
                        "To:   Philippine Overseas Employment Admin\n"
                        "      [POEA Anti-Illegal Recruitment Branch]\n"
                        "Re:   Formal complaint - License No. "
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
                        "Reviewable as a draft - fill in the bracketed "
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
                        "salted and one-way - only the count of repeat "
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
            "label": "Platform safety - Lane 01",
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
                        "1. illegal_placement_fee - 89 posts\n"
                        "2. unlicensed_recruiter_offer - 67\n"
                        "3. passport_retention_offer - 41\n"
                        "4. contract_substitution_signal - 34\n"
                        "5. time_pressure_tactic - 28\n\n"
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
                                 "- what does the rule fire on?"),
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
                        "helper changing employer in HK - what is the "
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
            "label": "Researcher / journalist - Lane 04",
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
                        "**Curator:** Polaris Project (verified)\n"
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
                        "  curator signature: Polaris Project (valid)\n"
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
                        "### Indicator trends - PH-HK corridor (12 mo)\n"
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
                        "- **Fee overcharge is dropping** - likely POEA "
                        "enforcement of MC 14-2017 working as intended.\n"
                        "- **Passport retention and isolation are rising** "
                        "- possibly a substitution effect: agencies that "
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
                        "### Passport retention - Q1 2026 cross-corridor\n"
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
                        "- **PH-HK shows the lowest** - POEA + HK Labour "
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
                        "- Git SHA: e56c818\n"
                        "- Dataset version: smoke@2026-05-04\n\n"
                        "### Run command\n"
                        "```bash\n"
                        "duecare-cli bench run \\\n"
                        "  --model gemma-4-e4b-it \\\n"
                        "  --adapter safetyjudge-v1 \\\n"
                        "  --pack ph-hk-domestic-worker@1.4.0 \\\n"
                        "  --test-set extended_200 \\\n"
                        "  --git-sha e56c818\n"
                        "```\n\n"
                        "### Result\n"
                        "Stock label_f1: 0.317. Harness ON label_f1: "
                        "0.882. **Lift: +56.5 percentage points** - "
                        "matches the writeup, deterministically.\n\n"
                        "Mismatches against this number are bug reports; "
                        "please file them with the run command + "
                        "observed result."),
                    "harness_trace": {},
                    "citations": ["git_sha:e56c818", "smoke_set:2026-05-04"],
                    "latency_simulation_ms": 2700,
                },
            ],
        },
        "developer": {
            "label": "Developer / integration partner - Lane 05",
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
                        "1. **Container image** - pin to a SHA, never "
                        "`:latest`.\n"
                        "   ```bash\n"
                        "   docker pull ghcr.io/taylorscottamarel/duecare:"
                        "v0.1.0@sha256:7e2c4a8f1b9d...\n"
                        "   ```\n"
                        "2. **Pack manifest** - pin every pack to a "
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
                        "3. **Optional adapter** - if using a fine-tuned "
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
                        "File a bug - the pinning makes it investigable."),
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
                        "1. **Ingest** - drop a case file in.\n"
                        "   ```bash\n"
                        "   POST /api/local-kb/ingest\n"
                        "     {\"case_id\": \"case_abc\",\n"
                        "      \"content\": \"<intake notes>\"}\n"
                        "   # response: redaction summary, entity hashes\n"
                        "   ```\n"
                        "2. **Query** - find similar cases across the "
                        "local DB (privacy-preserving).\n"
                        "   ```bash\n"
                        "   POST /api/local-kb/query\n"
                        "     {\"recruiter_hash\": \"7e2c...\",\n"
                        "      \"corridor\": \"PH-HK\"}\n"
                        "   # response: list of redacted match summaries\n"
                        "   ```\n"
                        "3. **Aggregate** - preview anonymized signal "
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
# 2.5 SLIDES (intro / problem / solution / lanes / closing deck)
# ===========================================================================
# Fifteen slides walked through with the spacebar during the video pitch.
# All narration text is curated for the video; no real data here.
SLIDES = {
    "schema_version": "1.0",
    "deck_id": "duecare-hackathon-pitch-v2",
    "slides": [
        {
            "id": "title",
            "title": "DueCare",
            "subtitle": ("AI infrastructure to combat "
                          "migrant-worker exploitation."),
            "body": ("Open-source. Runs locally. Cites public laws "
                      "and advisories. Never ingests raw worker cases."),
            "notes": ("Open on a held shot of the title for 5 seconds. "
                       "Voiceover: hook the viewer with the problem "
                       "size."),
        },
        {
            "id": "problem",
            "title": "27 million workers. One illegal fee away from "
                      "modern slavery.",
            "subtitle": "The problem",
            "body": ("Recruitment fraud, illegal placement fees, "
                      "passport retention, contract substitution. "
                      "Every year millions of migrant workers leave "
                      "PH / NP / BD / ID for HK / UAE / KSA / Qatar "
                      "and walk into one of these traps.\n\n"
                      "The frontier models that could help cost too "
                      "much, send raw case data to third parties, and "
                      "hallucinate citations."),
            "notes": ("3 seconds per illegal-pattern bullet. End on "
                       "the frontier-models-cost-too-much frame."),
        },
        {
            "id": "history_legal",
            "title": "The legal problem is known. The operational gap is not solved.",
            "subtitle": "History and legal precedents",
            "body": ("International and corridor-specific rules already "
                     "name the harms: forced-labour indicators, domestic "
                     "worker protections, recruitment-fee bans, wage rules, "
                     "and passport-retention limits.\n\n"
                     "The gap is daily enforcement at intake speed. Workers, "
                     "NGOs, regulators, and platforms need grounded answers "
                     "before a case becomes invisible."),
            "notes": "Use this slide to show that DueCare is not inventing policy.",
        },
        {
            "id": "why_llms_fail",
            "title": "Why normal LLMs underperform here.",
            "subtitle": "Attention x economic value x data",
            "body": ("1. Attention: the risky detail is often one phrase "
                     "inside a long chat, job ad, or intake file.\n"
                     "2. Economic value: bad actors profit from ambiguity, "
                     "coded fees, and contract language.\n"
                     "3. Data: the most useful case data is private, local, "
                     "and unsafe to centralize.\n\n"
                     "A generic model can sound fluent while missing the "
                     "specific indicator, law, or privacy boundary."),
            "notes": "This is the thesis slide for why harnesses exist.",
        },
        {
            "id": "prior_art",
            "title": "Prior art helps, but each piece is incomplete alone.",
            "subtitle": "What came before",
            "body": ("Rule systems are precise but brittle. RAG systems cite "
                     "sources but can retrieve the wrong paragraph. Intake "
                     "forms structure evidence but do not reason. Large "
                     "closed models reason better but can be expensive, "
                     "remote, and hard to audit.\n\n"
                     "DueCare combines local Gemma 4, rule packs, retrieval, "
                     "tool calls, grading, and exportable evidence."),
            "notes": "Keep this neutral. The pitch is combination and proof.",
        },
        {
            "id": "solution",
            "title": "Gemma 4 + DueCare harness. On a laptop. On a "
                      "phone. On an NGO's tiny VM.",
            "subtitle": "The solution",
            "body": ("Gemma 4 (open-weights, multimodal, multilingual) "
                      "wrapped in a runtime that:\n"
                      "  - cites real laws (POEA MC 14-2017, ILO C189, "
                      "    HK ED Cap 57)\n"
                      "  - flags exploitation indicators via GREP rules\n"
                      "  - keeps raw case content on the device\n"
                      "  - shares only anonymized aggregate signals "
                      "    with regulators on explicit consent"),
            "notes": ("Cut to the harness diagram. 4 seconds per "
                       "bullet."),
        },
        {
            "id": "why_gemma",
            "title": "Why Gemma 4 is the right backbone.",
            "subtitle": "Open, local, tool-using, adaptable",
            "body": ("Gemma 4 gives us open weights, small variants for "
                     "edge deployment, larger variants for research, "
                     "multimodal understanding, native tool-call patterns, "
                     "and a practical path to LoRA fine-tuning.\n\n"
                     "That means the same architecture can serve a phone, "
                     "a Kaggle notebook, an NGO laptop, and a regulator "
                     "analysis workflow."),
            "notes": "Connect directly to the hackathon technical criteria.",
        },
        {
            "id": "validation",
            "title": "Technical validation is exported, not asserted.",
            "subtitle": "How we prove improvement",
            "body": ("A-00 runs the same prompts across four conditions: "
                     "stock Gemma, stock plus harness, fine-tuned Gemma, "
                     "and fine-tuned plus harness.\n\n"
                     "It exports prompts, responses, trace, scores, timing, "
                     "tokens per second, and report graphs. The writeup can "
                     "cite the artifact, not a screenshot."),
            "notes": "Show A-00 in the appendices after the recorded demo.",
        },
        {
            "id": "use_case_platform",
            "title": "Use case 01: platform safety.",
            "subtitle": "High-volume UGC review",
            "body": ("Recruitment marketplaces and trust teams can screen "
                     "job ads, DMs, and creator posts for illegal fees, "
                     "passport retention, deceptive work categories, and "
                     "contract substitution.\n\n"
                     "DueCare flags and explains. The platform keeps the "
                     "final review action inside its existing workflow."),
            "notes": "After this slide, demo the platform lane if time allows.",
        },
        {
            "id": "use_case_ngo",
            "title": "Use case 02: NGOs and regulators.",
            "subtitle": "Case intake and triage",
            "body": ("Caseworkers can run on their own machine, summarize "
                     "complaints, surface relevant laws and advisories, "
                     "draft forms, and spot repeated patterns across cases "
                     "without raw data leaving local control.\n\n"
                     "This is the strongest slide for the media image demo."),
            "notes": "Switch to caseworker lane and show the synthetic ID image.",
        },
        {
            "id": "use_case_worker",
            "title": "Use case 03: individual worker and mobile.",
            "subtitle": "Plain-language corridor answers",
            "body": ("Workers and community channels can ask about fees, "
                     "contracts, passports, and rights in their own language. "
                     "DueCare never files complaints or instructs risky "
                     "action. It points to verified resources and trusted "
                     "caseworkers."),
            "notes": "Use worker lane scenes for the opening human story.",
        },
        {
            "id": "use_case_researcher",
            "title": "Use case 04: researcher.",
            "subtitle": "Citeable corridor research",
            "body": ("Researchers, policy analysts, and journalists can study "
                     "corridor risk with version-pinned packs and anonymized "
                     "signals. They can cite a hash, rerun months later, and "
                     "inspect the exact rules, sources, and scores."),
            "notes": "Connect to A-00 and A-11 artifacts.",
        },
        {
            "id": "use_case_developer",
            "title": "Use case 05: developer and integration partner.",
            "subtitle": "Drop-in runtime",
            "body": ("A partner can wire DueCare into Messenger, WhatsApp, "
                     "a moderator dashboard, a case-management plug-in, or "
                     "an on-prem deployment. They own the channel. DueCare "
                     "provides the harness, packs, and Gemma 4 layer."),
            "notes": "Use developer lane if the audience asks how to integrate.",
        },
        {
            "id": "before_after",
            "title": "Before / after the harness",
            "subtitle": "Why the harness matters",
            "body": ("Stock Gemma 4 to the question \"is a 23,000-"
                      "peso HK placement fee legal?\" gives a vague "
                      "answer with no citations.\n\n"
                      "The same Gemma 4 with the DueCare harness "
                      "cites POEA MC 14-2017, mentions ILO C189, "
                      "names the Blas F. Ople Center hotline, and "
                      "refuses to send the worker into the trap.\n\n"
                      "+56.5 percentage points on safety-judging "
                      "accuracy."),
            "notes": ("Show the side-by-side from A-03 lift "
                       "comparison if the live demo allows."),
        },
        {
            "id": "privacy_boundary",
            "title": "Privacy is the boundary, not the slogan.",
            "subtitle": "The trust surface",
            "body": ("Raw worker chats, IDs, contact details, and "
                      "private documents stay on the worker's device "
                      "(mobile) or the caseworker's machine "
                      "(NGO).\n\n"
                      "Only anonymized aggregate signals leave the "
                      "machine, only after explicit operator "
                      "consent. Salted hashes are one-way; the salt "
                      "itself is never exported.\n\n"
                      "Cut to A-20 privacy boundary kernel for the "
                      "visual."),
            "notes": ("Hold this slide for 8 seconds. This is the "
                       "trust beat."),
        },
        {
            "id": "ecosystem",
            "title": "The full solution is an ecosystem, not one chat box.",
            "subtitle": "Client, server, packs, eval, trainer",
            "body": ("Client surfaces: worker mobile, caseworker laptop, "
                     "platform queue, researcher notebook, partner API.\n"
                     "Server surfaces: optional hub, vetted pack sync, "
                     "anonymized signal intake, public-source proposals.\n"
                     "Proof surfaces: A-00 evaluation, grading packs, "
                     "fine-tune exports, and reproducible reports."),
            "notes": "This slide prevents the demo from feeling like a toy app.",
        },
        {
            "id": "tech_depth",
            "title": "Real, not faked for the demo.",
            "subtitle": "Technical depth",
            "body": ("- Gemma 4 fine-tune via Unsloth (SafetyJudge + "
                      "PrivacyRedactor LoRA adapters)\n"
                      "- GGUF export for llama.cpp (laptops); "
                      "LiteRT recipe for mobile\n"
                      "- A-00 omni evaluator plus appendix experiment ladder, each "
                      "kernel paste-and-run on Kaggle\n"
                      "- All numbers reproducible from "
                      "(git_sha, dataset_version)"),
            "notes": ("End on the appendix-ladder visual to underscore "
                       "depth + reproducibility."),
        },
        {
            "id": "closing",
            "title": "DueCare is shared infrastructure for the "
                      "people who can't pay frontier AI prices.",
            "subtitle": "Closing",
            "body": ("NGOs. Regulators. Recruitment-platform safety "
                      "teams. Workers themselves. They get the "
                      "harness; the harness keeps the answer "
                      "honest.\n\n"
                      "github.com/TaylorAmarelTech/gemma4_comp"),
            "notes": ("End screen. Hold for 5 seconds with the URL "
                       "fully readable."),
        },
    ],
}


# ===========================================================================
# 3. Workbench shell with replay UI
# ===========================================================================
print("\n[2/3] preparing replay UI")

try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("03-duecare-video-pitch")
except Exception:
    def dc_log(*a, **kw): return None
    def set_kernel_id(*a, **kw): return None


INDEX_HTML_TPL = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare 03 . Video Pitch</title>
<link rel="stylesheet" href="/static/_chrome.css">
<style>
  :root{
    --paper:#F7F6F1; --paper-2:#EFEDE4; --ink:#0E1116; --ink-2:#2A2D34;
    --ink-3:#5B5F68; --line:#DDD8C9; --good:#3E8C65; --warn:#A97935;
    --danger:#9E3F3F;
  }
  body{background:var(--paper);color:var(--ink);
       font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",
                    system-ui,sans-serif;
       margin:0;padding:0;line-height:1.55}
  .topbar{position:sticky;top:0;z-index:50;background:var(--paper);
          border-bottom:1px solid var(--line);
          display:flex;align-items:center;gap:14px;padding:12px 28px}
  .topbar .brand{font-weight:700;font-size:15px;letter-spacing:-0.01em}
  .topbar .tabs{display:flex;gap:6px;margin-left:24px}
  .topbar .tab{padding:7px 14px;background:transparent;
               border:1px solid var(--line);border-radius:999px;
               font-size:13px;cursor:pointer;color:var(--ink);
               font-weight:600}
  .topbar .tab:hover{background:var(--paper-2)}
  .topbar .tab.active{background:var(--ink);color:var(--paper);
                       border-color:var(--ink)}
  .topbar .lane-pick{margin-left:auto;display:none;gap:6px}
  .topbar .lane-pick.show{display:flex}
  .topbar .lane{padding:5px 11px;background:transparent;
                border:1px solid var(--line);border-radius:999px;
                font-size:12.5px;cursor:pointer;color:var(--ink-3);
                font-weight:600}
  .topbar .lane.active{background:var(--paper-2);color:var(--ink);
                        border-color:var(--ink-3)}
  .page{max-width:980px;margin:0 auto;padding:24px 28px 120px}

  #slides-view{display:none}
  .slide-card{background:#FFF;border:1px solid var(--line);
              border-radius:14px;padding:56px 64px;min-height:480px;
              margin-top:8px}
  .slide-sub{font-size:11px;text-transform:uppercase;
              letter-spacing:.12em;color:var(--ink-3);
              margin-bottom:14px;
              font-family:"JetBrains Mono",ui-monospace,monospace}
  .slide-title{font-size:38px;line-height:1.12;margin:0 0 28px;
                letter-spacing:-.02em;font-weight:700}
  .slide-body{font-size:19px;line-height:1.65;color:var(--ink-2);
               white-space:pre-wrap}
  .slide-meta{margin-top:28px;font-size:12px;color:var(--ink-3);
               font-family:"JetBrains Mono",ui-monospace,monospace}

  #presentation-view{display:none}
  .scene-bar{display:flex;gap:8px;margin:14px 0;flex-wrap:wrap}
  .scene-bar .pill{padding:5px 11px;background:var(--paper-2);
                    border:1px solid var(--line);border-radius:999px;
                    font-size:12px;font-weight:600;cursor:pointer;
                    color:var(--ink-3)}
  .scene-bar .pill.active{background:var(--ink);color:var(--paper);
                            border-color:var(--ink)}
  .chat{display:flex;flex-direction:column;gap:14px;background:#FFF;
        border:1px solid var(--line);border-radius:14px;
        padding:22px 24px;min-height:440px}
  .msg{padding:14px 18px;border-radius:12px;line-height:1.6}
  .msg.user{background:#F0EBE0;border:1px solid var(--line);
             align-self:flex-end;max-width:78%;font-size:15px}
  .msg.assistant{background:#FFF;border:1px solid var(--paper-2);
                  align-self:flex-start;max-width:96%;font-size:15px;
                  white-space:pre-wrap}
  .thinking{align-self:flex-start;background:var(--paper-2);
             border:1px solid var(--line);padding:10px 16px;
             border-radius:12px;font-size:13px;color:var(--ink-3);
             font-family:"JetBrains Mono",ui-monospace,monospace}
  .citations{margin-top:8px;font-size:12px;color:var(--ink-3)}
  .cite{display:inline-block;padding:2px 8px;border-radius:999px;
         background:#EAF2EC;color:#1F4F33;font-size:11px;
         margin:1px 4px 1px 0;font-weight:600}
  .trace{margin-top:8px;font-family:"JetBrains Mono",ui-monospace,monospace;
          font-size:11px;color:#8A8E97}
  .media-card{align-self:flex-start;max-width:420px;background:#FFF;
              border:1px solid var(--line);border-radius:12px;
              padding:10px;margin:2px 0 0}
  .media-card img{display:block;width:100%;height:auto;border-radius:8px;
                  border:1px solid var(--paper-2)}
  .media-caption{font-size:12px;color:var(--ink-3);line-height:1.45;
                 margin-top:8px}

  #setup-view{display:none}
  .setup-grid{display:grid;grid-template-columns:280px 1fr;
              gap:20px;margin-top:14px}
  .setup-list{background:var(--paper-2);border:1px solid var(--line);
              border-radius:12px;padding:14px 16px;max-height:580px;
              overflow:auto}
  .setup-list h3{margin:0 0 8px;font-size:13px;
                   text-transform:uppercase;letter-spacing:.06em;
                   color:var(--ink-3)}
  .setup-list select{width:100%;padding:8px 10px;
                       border:1px solid var(--line);border-radius:6px;
                       background:#FFF;font:inherit;margin-bottom:10px}
  .setup-list .scene-row{padding:8px 10px;background:#FFF;
                          border:1px solid var(--line);
                          border-radius:8px;margin-bottom:6px;
                          cursor:pointer;font-size:13px}
  .setup-list .scene-row.active{border-color:var(--ink);
                                  background:var(--paper)}
  .setup-list .scene-row .pid{font-family:"JetBrains Mono",monospace;
                                color:var(--ink-3);font-size:11px}
  .setup-list .actions{margin-top:12px;display:flex;flex-direction:column;
                         gap:6px}
  .setup-list .actions button{padding:7px 12px;
        border:1px solid var(--line);border-radius:6px;
        background:#FFF;cursor:pointer;font-size:12.5px;color:var(--ink)}
  .setup-list .actions button:hover{background:var(--paper)}
  .setup-editor{background:#FFF;border:1px solid var(--line);
                 border-radius:12px;padding:18px 20px}
  .setup-editor label{display:block;font-size:11px;
                        text-transform:uppercase;letter-spacing:.06em;
                        color:var(--ink-3);margin:12px 0 4px}
  .setup-editor input[type=text],
  .setup-editor input[type=number],
  .setup-editor textarea{width:100%;padding:10px 12px;
                            border:1px solid var(--line);
                            border-radius:8px;background:var(--paper);
                            font:inherit;font-size:13.5px}
  .setup-editor textarea{min-height:140px;
                            font-family:"JetBrains Mono",monospace;
                            font-size:12.5px;line-height:1.5}
  .setup-editor .edit-actions{margin-top:14px;display:flex;gap:8px}
  .setup-editor .edit-actions button{padding:8px 14px;
        border:none;border-radius:999px;font-weight:600;
        font-size:12.5px;cursor:pointer}
  .setup-editor .btn-primary{background:var(--ink);color:var(--paper)}
  .setup-editor .btn-ghost{background:transparent;color:var(--ink);
                             border:1px solid var(--line)!important}
  .setup-status{margin-top:10px;font-size:12px;color:var(--ink-3);
                 font-family:"JetBrains Mono",monospace}

  .remote{position:fixed;bottom:18px;right:20px;z-index:60;
          background:var(--ink);color:var(--paper);
          border-radius:14px;padding:10px 14px;
          box-shadow:0 8px 24px rgba(0,0,0,.18);
          display:none;align-items:center;gap:10px;
          font-family:"JetBrains Mono",monospace;font-size:12px}
  .remote.show{display:flex}
  .remote button{background:transparent;color:var(--paper);
                  border:1px solid rgba(255,255,255,.3);
                  border-radius:999px;padding:6px 14px;cursor:pointer;
                  font-size:13px;font-weight:600}
  .remote button:hover{background:rgba(255,255,255,.12)}
  .remote .pos{opacity:.65}
</style></head><body>

<div class="topbar">
  <div class="brand">DueCare . 03 Video Pitch</div>
  <div class="tabs">
    <button class="tab" data-mode="slides">Slides</button>
    <button class="tab active" data-mode="presentation">Presentation</button>
    <button class="tab" data-mode="setup">Setup</button>
  </div>
  <div class="lane-pick" id="lane-pick"></div>
</div>

<div class="page">
  <div id="slides-view"><div id="slides-root"></div></div>

  <div id="presentation-view">
    <h2 id="lane-label" style="margin:8px 0 4px;font-size:22px"></h2>
    <p id="lane-intro" style="color:var(--ink-3);margin:0 0 12px;
                                font-size:14px"></p>
    <div class="scene-bar" id="scene-bar"></div>
    <div class="chat" id="chat"></div>
  </div>

  <div id="setup-view">
    <p style="color:var(--ink-3);max-width:740px;margin:8px 0 0;
                font-size:14px">
      Edit prompts and responses in-browser. Save writes
      <code>/kaggle/working/demo_script_authored.json</code>; Load
      reads a previously saved JSON. Changes apply immediately to
      the Presentation tab without restarting the kernel.</p>
    <div class="setup-grid">
      <div class="setup-list">
        <h3>Lane</h3>
        <select id="setup-lane"></select>
        <h3>Scenes</h3>
        <div id="setup-scene-list"></div>
        <div class="actions">
          <button onclick="setupAddScene()">+ Add scene</button>
          <button onclick="setupDuplicate()">Duplicate selected</button>
          <button onclick="setupDelete()" style="color:#9E3F3F">
            Delete selected</button>
          <button onclick="setupSave()"
                  style="background:var(--ink);color:var(--paper)">
            Save to /kaggle/working</button>
          <button onclick="setupExportEvidence()">Export evidence bundle</button>
          <label style="margin-top:8px;font-size:11px;
                          color:var(--ink-3);text-transform:uppercase;
                          letter-spacing:.06em">Load JSON</label>
          <input type="file" id="setup-load" accept=".json"
                  onchange="setupLoad(this.files[0])">
        </div>
        <div class="setup-status" id="setup-status"></div>
      </div>
      <div class="setup-editor" id="setup-editor">
        <p style="color:var(--ink-3);font-size:13px">
          Select a scene on the left to edit.</p>
      </div>
    </div>
  </div>
</div>

<div class="remote" id="remote">
  <span class="pos" id="remote-pos">.</span>
  <button onclick="remotePrev()">&lt; Prev</button>
  <button onclick="remoteNext()">Next &gt;</button>
</div>

<script>
const SCRIPT_INIT = __SCRIPT_JSON__;
const SLIDES_DATA = __SLIDES_JSON__;
let SCRIPT = JSON.parse(JSON.stringify(SCRIPT_INIT));

const URL_PARAMS = new URLSearchParams(window.location.search);
let currentMode = URL_PARAMS.get("mode") || "slides";
let currentLane = URL_PARAMS.get("lane") || "worker";
let currentScene = 0;
let currentSlide = 0;
let setupSelected = 0;
let abortToken = 0;

if (!["slides","presentation","setup"].includes(currentMode)) {
  currentMode = "slides";
}
if (!SCRIPT.lanes[currentLane]) {
  currentLane = "worker";
}

function _el(tag, cls, txt){
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (txt != null) e.textContent = String(txt);
  return e;
}

function setMode(m){
  if (!["slides","presentation","setup"].includes(m)) return;
  abortToken++;
  currentMode = m;
  document.querySelectorAll(".topbar .tab").forEach(t=>{
    t.classList.toggle("active", t.dataset.mode === m);
  });
  document.getElementById("slides-view").style.display =
    (m==="slides") ? "block" : "none";
  document.getElementById("presentation-view").style.display =
    (m==="presentation") ? "block" : "none";
  document.getElementById("setup-view").style.display =
    (m==="setup") ? "block" : "none";
  document.getElementById("lane-pick").classList.toggle(
    "show", m==="presentation");
  const remote = document.getElementById("remote");
  remote.classList.toggle("show", m==="slides" || m==="presentation");
  if (m==="slides") showSlide(currentSlide);
  else if (m==="presentation"){
    renderLaneBar(); renderLaneHead(); playScene();
  } else if (m==="setup") renderSetup();
}

document.querySelectorAll(".topbar .tab").forEach(t=>{
  t.onclick = ()=> setMode(t.dataset.mode);
});

function showSlide(i){
  const root = document.getElementById("slides-root");
  root.replaceChildren();
  const s = SLIDES_DATA.slides[i];
  if (!s) return;
  const card = _el("div","slide-card");
  card.appendChild(_el("div","slide-sub", s.subtitle));
  card.appendChild(_el("h1","slide-title", s.title));
  const body = _el("div","slide-body");
  body.textContent = s.body;
  card.appendChild(body);
  if (s.media) card.appendChild(renderMedia(s.media));
  card.appendChild(_el("div","slide-meta",
    "Slide " + (i+1) + " / " + SLIDES_DATA.slides.length +
    " . id: " + s.id));
  root.appendChild(card);
  updateRemote();
}

function renderMedia(media){
  const wrap = _el("div", "media-card");
  const img = document.createElement("img");
  img.src = media.src;
  img.alt = media.alt || "Demo media";
  wrap.appendChild(img);
  if (media.caption) wrap.appendChild(_el("div", "media-caption", media.caption));
  return wrap;
}

function renderLaneBar(){
  const wrap = document.getElementById("lane-pick");
  wrap.replaceChildren();
  for (const k of Object.keys(SCRIPT.lanes)){
    const b = document.createElement("button");
    b.className = "lane" + (k===currentLane ? " active" : "");
    b.textContent = SCRIPT.lanes[k].label.split("--")[0].trim();
    b.onclick = ()=>{
      currentLane = k; currentScene = 0;
      renderLaneBar(); renderLaneHead(); playScene();
    };
    wrap.appendChild(b);
  }
}

function renderLaneHead(){
  const lane = SCRIPT.lanes[currentLane];
  document.getElementById("lane-label").textContent = lane.label;
  document.getElementById("lane-intro").textContent = lane.intro;
  renderSceneBar();
}

function renderSceneBar(){
  const bar = document.getElementById("scene-bar");
  bar.replaceChildren();
  const scenes = SCRIPT.lanes[currentLane].scenes;
  for (let i=0; i<scenes.length; i++){
    const p = _el("span", "pill" + (i===currentScene ? " active" : ""),
                   (i+1) + ". " + scenes[i].scene_id);
    p.onclick = ()=>{ currentScene = i; playScene(); };
    bar.appendChild(p);
  }
}

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

async function typewrite(el, text, cps){
  const myToken = ++abortToken;
  const delay = Math.max(8, Math.round(1000/cps));
  for (let i=0; i<text.length; i++){
    if (myToken !== abortToken) return;
    el.textContent = text.slice(0, i+1);
    await sleep(delay);
  }
}

async function playScene(){
  abortToken++;
  const chat = document.getElementById("chat");
  chat.replaceChildren();
  renderSceneBar();
  const s = SCRIPT.lanes[currentLane].scenes[currentScene];
  if (!s) return;
  updateRemote();
  const user = _el("div","msg user");
  chat.appendChild(user);
  await typewrite(user, s.prompt, 28);
  if (s.media) chat.appendChild(renderMedia(s.media));
  const t = _el("div","thinking","thinking ...");
  chat.appendChild(t);
  await sleep(s.latency_simulation_ms || 1500);
  if (t.parentNode) chat.removeChild(t);
  const a = _el("div","msg assistant");
  chat.appendChild(a);
  await typewrite(a, s.response, 65);
  if ((s.citations||[]).length){
    const c = _el("div","citations");
    for (const ct of s.citations) c.appendChild(_el("span","cite",ct));
    chat.appendChild(c);
  }
  const tr = s.harness_trace || {};
  const grepN = (tr.grep && tr.grep.rules_fired ?
                  tr.grep.rules_fired.length : 0);
  const ragN  = (tr.rag  && tr.rag.docs_retrieved ?
                  tr.rag.docs_retrieved.length  : 0);
  const tooN  = (tr.tools && tr.tools.tools_called ?
                  tr.tools.tools_called.length  : 0);
  const trParts = [];
  if (tr.persona && tr.persona.enabled) trParts.push("persona");
  if (grepN) trParts.push("grep:" + grepN + " rules");
  if (ragN)  trParts.push("rag:"  + ragN  + " docs");
  if (tooN)  trParts.push("tools:" + tooN);
  if (trParts.length){
    chat.appendChild(_el("div","trace",
      "harness trace: " + trParts.join(" . ")));
  }
}

function skip(){
  abortToken++;
  const chat = document.getElementById("chat");
  chat.replaceChildren();
  const s = SCRIPT.lanes[currentLane].scenes[currentScene];
  if (!s) return;
  const u = _el("div","msg user"); u.textContent = s.prompt;
  chat.appendChild(u);
  if (s.media) chat.appendChild(renderMedia(s.media));
  const a = _el("div","msg assistant"); a.textContent = s.response;
  chat.appendChild(a);
  if ((s.citations||[]).length){
    const c = _el("div","citations");
    for (const ct of s.citations) c.appendChild(_el("span","cite",ct));
    chat.appendChild(c);
  }
}

function updateRemote(){
  const pos = document.getElementById("remote-pos");
  if (currentMode === "slides"){
    pos.textContent = "Slide " + (currentSlide+1) + " / " +
                       SLIDES_DATA.slides.length;
  } else if (currentMode === "presentation"){
    const ns = SCRIPT.lanes[currentLane].scenes.length;
    pos.textContent = currentLane + " . Scene " +
                       (currentScene+1) + " / " + ns;
  }
}

function remoteNext(){
  if (currentMode === "slides"){
    if (currentSlide < SLIDES_DATA.slides.length - 1){
      currentSlide++; showSlide(currentSlide);
    }
  } else if (currentMode === "presentation"){
    const ns = SCRIPT.lanes[currentLane].scenes.length;
    if (currentScene < ns - 1){ currentScene++; playScene(); }
  }
}

function remotePrev(){
  if (currentMode === "slides"){
    if (currentSlide > 0){ currentSlide--; showSlide(currentSlide); }
  } else if (currentMode === "presentation"){
    if (currentScene > 0){ currentScene--; playScene(); }
  }
}

document.addEventListener("keydown", (e)=>{
  if (e.key === " " || e.key === "ArrowRight"){
    e.preventDefault(); remoteNext();
  } else if (e.key === "ArrowLeft"){
    e.preventDefault(); remotePrev();
  } else if (e.key === "r" || e.key === "R"){
    if (currentMode === "slides"){ currentSlide=0; showSlide(0); }
    else if (currentMode === "presentation"){
      currentScene=0; playScene();
    }
  } else if (e.key === "s" || e.key === "S"){
    if (currentMode === "presentation") skip();
  } else if (e.key >= "1" && e.key <= "9"){
    const n = parseInt(e.key, 10) - 1;
    if (currentMode === "slides" && n < SLIDES_DATA.slides.length){
      currentSlide = n; showSlide(n);
    } else if (currentMode === "presentation"){
      const ns = SCRIPT.lanes[currentLane].scenes.length;
      if (n < ns){ currentScene = n; playScene(); }
    }
  }
});

function renderSetup(){
  const laneSel = document.getElementById("setup-lane");
  laneSel.replaceChildren();
  for (const k of Object.keys(SCRIPT.lanes)){
    const o = document.createElement("option");
    o.value = k; o.textContent = SCRIPT.lanes[k].label;
    laneSel.appendChild(o);
  }
  laneSel.value = currentLane;
  laneSel.onchange = ()=>{
    currentLane = laneSel.value;
    setupSelected = 0;
    renderSetupSceneList();
    renderSetupEditor();
  };
  renderSetupSceneList();
  renderSetupEditor();
}

function renderSetupSceneList(){
  const wrap = document.getElementById("setup-scene-list");
  wrap.replaceChildren();
  const scenes = SCRIPT.lanes[currentLane].scenes;
  for (let i=0; i<scenes.length; i++){
    const row = _el("div",
      "scene-row" + (i===setupSelected ? " active" : ""));
    row.appendChild(_el("div", "pid", "[" + (i+1) + "] " +
                          scenes[i].scene_id));
    const preview = scenes[i].prompt.slice(0, 60) +
                      (scenes[i].prompt.length > 60 ? "..." : "");
    row.appendChild(_el("div", null, preview));
    row.onclick = ()=>{
      setupSelected = i;
      renderSetupSceneList();
      renderSetupEditor();
    };
    wrap.appendChild(row);
  }
}

function renderSetupEditor(){
  const wrap = document.getElementById("setup-editor");
  wrap.replaceChildren();
  const scenes = SCRIPT.lanes[currentLane].scenes;
  const s = scenes[setupSelected];
  if (!s){
    wrap.appendChild(_el("p", null,
      "No scene selected. Use + Add scene on the left."));
    return;
  }
  function field(label, key, isArea){
    wrap.appendChild(_el("label", null, label));
    const inp = document.createElement(isArea ? "textarea" : "input");
    if (!isArea) inp.type = "text";
    inp.value = s[key] != null ? s[key] : "";
    inp.oninput = ()=>{ s[key] = inp.value; };
    wrap.appendChild(inp);
    return inp;
  }
  field("Scene ID", "scene_id", false);
  field("Prompt (user message)", "prompt", true);
  field("Response (assistant message)", "response", true);
  wrap.appendChild(_el("label", null, "Media image URL"));
  const mediaUrl = document.createElement("input");
  mediaUrl.type = "text";
  mediaUrl.value = s.media && s.media.src ? s.media.src : "";
  mediaUrl.oninput = ()=>{
    if (!mediaUrl.value.trim()){ delete s.media; return; }
    s.media = s.media || {type:"image"};
    s.media.src = mediaUrl.value.trim();
  };
  wrap.appendChild(mediaUrl);
  wrap.appendChild(_el("label", null, "Media caption"));
  const mediaCaption = document.createElement("input");
  mediaCaption.type = "text";
  mediaCaption.value = s.media && s.media.caption ? s.media.caption : "";
  mediaCaption.oninput = ()=>{
    s.media = s.media || {type:"image", src: mediaUrl.value.trim()};
    s.media.caption = mediaCaption.value;
  };
  wrap.appendChild(mediaCaption);
  wrap.appendChild(_el("label", null, "Latency simulation (ms)"));
  const lat = document.createElement("input");
  lat.type = "number";
  lat.value = s.latency_simulation_ms != null ?
    s.latency_simulation_ms : 1500;
  lat.oninput = ()=>{
    s.latency_simulation_ms = parseInt(lat.value, 10) || 1500;
  };
  wrap.appendChild(lat);
  wrap.appendChild(_el("label", null,
    "Citations (comma-separated)"));
  const cit = document.createElement("input");
  cit.type = "text";
  cit.value = (s.citations || []).join(", ");
  cit.oninput = ()=>{
    s.citations = cit.value.split(",").map(x=>x.trim())
                              .filter(Boolean);
  };
  wrap.appendChild(cit);
  const acts = _el("div", "edit-actions");
  const tb = document.createElement("button");
  tb.className = "btn-primary";
  tb.textContent = "Preview in Presentation tab";
  tb.onclick = ()=>{
    currentScene = setupSelected;
    setMode("presentation");
  };
  acts.appendChild(tb);
  const gb = document.createElement("button");
  gb.className = "btn-ghost";
  gb.textContent = "Discard changes (reload from server)";
  gb.onclick = ()=>{ setupReloadFromServer(); };
  acts.appendChild(gb);
  wrap.appendChild(acts);
}

function setupAddScene(){
  const scenes = SCRIPT.lanes[currentLane].scenes;
  const idx = scenes.length;
  scenes.push({
    scene_id: "new_scene_" + (idx+1).toString().padStart(2, "0"),
    prompt: "Type your prompt here ...",
    response: "Type the response Gemma should give back ...",
    harness_trace: {},
    citations: [],
    latency_simulation_ms: 1500,
  });
  setupSelected = idx;
  renderSetupSceneList();
  renderSetupEditor();
}

function setupDuplicate(){
  const scenes = SCRIPT.lanes[currentLane].scenes;
  const s = scenes[setupSelected];
  if (!s) return;
  const copy = JSON.parse(JSON.stringify(s));
  copy.scene_id = (s.scene_id || "scene") + "_copy";
  scenes.splice(setupSelected + 1, 0, copy);
  setupSelected = setupSelected + 1;
  renderSetupSceneList();
  renderSetupEditor();
}

function setupDelete(){
  const scenes = SCRIPT.lanes[currentLane].scenes;
  if (scenes.length <= 1){
    setupStatus("Cannot delete the last scene in a lane.", true);
    return;
  }
  scenes.splice(setupSelected, 1);
  setupSelected = Math.max(0, setupSelected - 1);
  renderSetupSceneList();
  renderSetupEditor();
}

function setupStatus(msg, isErr){
  const el = document.getElementById("setup-status");
  el.textContent = msg;
  el.style.color = isErr ? "#9E3F3F" : "var(--ink-3)";
}

async function setupSave(){
  setupStatus("saving ...");
  try {
    const r = await fetch("/api/save-script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({script: SCRIPT}),
    }).then(r=>r.json());
    if (r.ok){
      setupStatus("saved to " + r.path + " (" + r.size_bytes + " B)");
    } else {
      setupStatus("save failed: " + (r.error || "unknown"), true);
    }
  } catch (e){ setupStatus("save error: " + e, true); }
}

async function setupLoad(file){
  if (!file) return;
  setupStatus("loading " + file.name + " ...");
  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    if (!parsed.lanes){
      setupStatus("JSON missing 'lanes' key", true);
      return;
    }
    const r = await fetch("/api/load-script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({script: parsed}),
    }).then(r=>r.json());
    if (r.ok){
      SCRIPT = parsed;
      currentLane = Object.keys(SCRIPT.lanes)[0];
      setupSelected = 0;
      renderSetup();
      setupStatus("loaded " + file.name);
    } else {
      setupStatus("load failed: " + (r.error || "unknown"), true);
    }
  } catch (e){ setupStatus("load error: " + e, true); }
}

async function setupReloadFromServer(){
  try {
    const r = await fetch("/api/get-script").then(r=>r.json());
    if (r.ok && r.script){
      SCRIPT = r.script;
      renderSetup();
      setupStatus("reloaded from server");
    }
  } catch (e){ setupStatus("reload error: " + e, true); }
}

async function setupExportEvidence(){
  setupStatus("exporting evidence bundle ...");
  try {
    const r = await fetch("/api/export-presentation", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({script: SCRIPT, slides: SLIDES_DATA}),
    }).then(r=>r.json());
    if (r.ok){
      const link = r.artifacts && r.artifacts.zip ? r.artifacts.zip : "";
      setupStatus("exported " + (link || r.bundle || "bundle"));
    } else {
      setupStatus("export failed: " + (r.error || "unknown"), true);
    }
  } catch (e){ setupStatus("export error: " + e, true); }
}

setMode(currentMode);
</script>
</body></html>
"""


print("\n[3/3] launching workbench shell")
INDEX_HTML = (
    INDEX_HTML_TPL
    .replace("__SCRIPT_JSON__", json.dumps(DEMO_SCRIPT))
    .replace("__SLIDES_JSON__", json.dumps(SLIDES))
)
_SHUTDOWN_EVENT = threading.Event()

try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": "03 DueCare Video Pitch (slides + replay + setup)",
        "audience": "all",
        "lede": ("Main notebook 03. THREE modes via URL param:\n"
                  "  ?mode=slides         recording deck, opens by default\n"
                  "  ?mode=presentation   5-lane cached replay\n"
                  "  ?mode=setup          edit, save, and export evidence\n"
                  "Zero inference, predictable cadence. Use this for "
                  "the hackathon video recording."),
        "results": [
            {"label": "Lanes", "value": str(len(DEMO_SCRIPT["lanes"]))},
            {"label": "Scenes", "value": str(sum(
                len(l["scenes"]) for l in DEMO_SCRIPT["lanes"].values()))},
            {"label": "Compute", "value": "CPU-only, no model load"},
        ],
        "links": [
            ("slides", "/?mode=slides"),
            ("worker replay", "/?mode=presentation&lane=worker"),
            ("caseworker replay", "/?mode=presentation&lane=caseworker"),
            ("setup export", "/?mode=setup"),
        ],
        "next_steps": [
            "Open the printed cloudflared URL. It starts on the title slide.",
            "Press Space to advance the deck.",
            "Switch to Presentation for cached 5-lane demos.",
            "Use Setup to export prompts, responses, traces, scorecards, and media.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="03-duecare-video-pitch",
        port=PORT, homepage_html=INDEX_HTML,
    )

    # Setup-mode endpoints: get / save / load the in-memory DEMO_SCRIPT
    # so the operator can author scenes through the browser without
    # restarting the kernel. Authored scripts persist as
    # /kaggle/working/demo_script_authored.json.
    _SCRIPT_RUNTIME = {"script": DEMO_SCRIPT}
    _AUTHORED_PATH = OUTPUT_DIR / "demo_script_authored.json"

    def _artifact_url(path: Path) -> str:
        try:
            rel = path.resolve().relative_to(OUTPUT_DIR.resolve())
            return "/artifact/" + str(rel).replace("\\", "/")
        except Exception:
            return str(path)

    def _scene_score(scene: dict) -> dict:
        trace = scene.get("harness_trace") or {}
        grep = len(((trace.get("grep") or {}).get("rules_fired")) or [])
        rag = len(((trace.get("rag") or {}).get("docs_retrieved")) or [])
        tools = len(((trace.get("tools") or {}).get("tools_called")) or [])
        citations = len(scene.get("citations") or [])
        media = 1 if scene.get("media") else 0
        score = min(10, 4 + grep + rag + tools + citations + media)
        return {
            "score_0_10": score,
            "grep_rules": grep,
            "rag_docs": rag,
            "tool_calls": tools,
            "citations": citations,
            "media_assets": media,
        }

    def _write_presentation_export(script: dict, slides: dict) -> dict:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        export_id = f"video_pitch_export_{stamp}"
        json_path = OUTPUT_DIR / f"{export_id}.json"
        csv_path = OUTPUT_DIR / f"{export_id}_scenes.csv"
        md_path = OUTPUT_DIR / f"{export_id}.md"
        zip_path = OUTPUT_DIR / f"{export_id}.zip"

        rows = []
        for lane_id, lane in (script.get("lanes") or {}).items():
            for idx, scene in enumerate(lane.get("scenes") or [], 1):
                score = _scene_score(scene)
                rows.append({
                    "lane_id": lane_id,
                    "lane_label": lane.get("label", ""),
                    "scene_index": idx,
                    "scene_id": scene.get("scene_id", ""),
                    "prompt": scene.get("prompt", ""),
                    "response": scene.get("response", ""),
                    "citations": "; ".join(scene.get("citations") or []),
                    **score,
                })

        payload = {
            "schema_version": "duecare.video_pitch_export.v1",
            "export_id": export_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "purpose": ("Screen-recording evidence bundle with cached "
                        "prompts, responses, traces, scores, slides, "
                        "and media references."),
            "slides": slides,
            "script": script,
            "scene_scorecards": rows,
            "media": [{
                "name": SYNTHETIC_ID_CARD_PATH.name,
                "path": str(SYNTHETIC_ID_CARD_PATH),
                "url": SYNTHETIC_ID_CARD_URL,
                "note": "Synthetic media generated inside the notebook.",
            }],
        }
        json_path.write_text(json.dumps(payload, indent=2,
                                        ensure_ascii=False),
                             encoding="utf-8")
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys())
                                    if rows else ["lane_id", "scene_id"])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        md_lines = [
            "# DueCare Video Pitch Evidence Export",
            "",
            f"Export id: `{export_id}`",
            "",
            "This bundle is the cached presentation record used for the "
            "screen recording. It includes prompts, responses, harness "
            "traces, citations, qualitative scorecards, slide copy, and "
            "synthetic media references.",
            "",
            "| Lane | Scene | Score | GREP | RAG | Tools | Citations | Media |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
        for row in rows:
            md_lines.append(
                f"| {row['lane_id']} | {row['scene_id']} | "
                f"{row['score_0_10']} | {row['grep_rules']} | "
                f"{row['rag_docs']} | {row['tool_calls']} | "
                f"{row['citations']} | {row['media_assets']} |"
            )
        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in [json_path, csv_path, md_path, SYNTHETIC_ID_CARD_PATH]:
                if p.exists():
                    z.write(p, arcname=p.name)
        return {
            "export_id": export_id,
            "artifacts": {
                "json": _artifact_url(json_path),
                "csv": _artifact_url(csv_path),
                "markdown": _artifact_url(md_path),
                "zip": _artifact_url(zip_path),
            },
        }

    from fastapi import Request as _Request

    @app.get("/api/get-script")
    def _get_script():
        return {"ok": True, "script": _SCRIPT_RUNTIME["script"]}

    @app.post("/api/save-script")
    async def _save_script(req: _Request):
        body = await req.json()
        script = body.get("script")
        if not isinstance(script, dict) or "lanes" not in script:
            return {"ok": False, "error":
                    "expected {script: {lanes: ...}}"}
        _SCRIPT_RUNTIME["script"] = script
        try:
            _AUTHORED_PATH.write_text(
                json.dumps(script, indent=2, ensure_ascii=False),
                encoding="utf-8")
            size = _AUTHORED_PATH.stat().st_size
        except Exception as _e:
            return {"ok": False,
                    "error": f"write failed: {type(_e).__name__}: "
                              f"{str(_e)[:200]}"}
        return {"ok": True, "path": str(_AUTHORED_PATH),
                "size_bytes": size}

    @app.post("/api/load-script")
    async def _load_script(req: _Request):
        body = await req.json()
        script = body.get("script")
        if not isinstance(script, dict) or "lanes" not in script:
            return {"ok": False, "error":
                    "expected {script: {lanes: ...}}"}
        _SCRIPT_RUNTIME["script"] = script
        try:
            _AUTHORED_PATH.write_text(
                json.dumps(script, indent=2, ensure_ascii=False),
                encoding="utf-8")
        except Exception:
            pass
        return {"ok": True}

    @app.post("/api/export-presentation")
    async def _export_presentation(req: _Request):
        body = await req.json()
        script = body.get("script") or _SCRIPT_RUNTIME["script"]
        slides = body.get("slides") or SLIDES
        if not isinstance(script, dict) or "lanes" not in script:
            return {"ok": False, "error": "expected script with lanes"}
        try:
            out = _write_presentation_export(script, slides)
        except Exception as _e:
            return {"ok": False,
                    "error": f"export failed: {type(_e).__name__}: "
                              f"{str(_e)[:200]}"}
        return {"ok": True, **out}
    if public_url:
        print(f"  ok UI: {public_url}")
    print("\n  03 VIDEO PITCH READY: record from your browser\n")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")
print("\n  shutdown complete: cell exiting.\n")
