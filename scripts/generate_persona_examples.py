"""Generate synthetic anonymized persona example content for the
chat package's bundled examples corpus.

Builds 5 personas × 5 corridors × multiple content types =
~30-40 new examples. Each entry follows the existing
_classifier_examples.json schema (id, category, label, content,
image_data_uri optional) and uses fully-synthetic composite names,
fictional IDs, and reserved-for-fiction phone prefixes per the
anonymization policy at docs/anonymization_policy.md.

All entries are explicitly tagged "[COMPOSITE EXAMPLE]" so a
reviewer can never mistake them for real cases.

Run:
    python scripts/generate_persona_examples.py

Outputs:
    packages/duecare-llm-chat/src/duecare/chat/harness/_classifier_examples.json
        (extends in place; preserves the existing 16 entries)
"""
from __future__ import annotations

import base64
import json
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
TARGET = (REPO / "packages" / "duecare-llm-chat" / "src" / "duecare"
            / "chat" / "harness" / "_classifier_examples.json")


# ---------------------------------------------------------------------
# Composite cast — explicitly synthetic, per docs/anonymization_policy
# ---------------------------------------------------------------------
PERSONAS = [
    {
        "key": "ofw_worker",
        "name": "Maria Santos (composite)",
        "from": "Cebu, Philippines",
        "role": "domestic worker",
        "voice": "first-person, Tagalog/English code-switch, scared",
    },
    {
        "key": "ngo_caseworker",
        "name": "Joana Rivera (composite)",
        "org": "Mission for Migrant Workers HK (composite caseworker)",
        "role": "intake caseworker",
        "voice": "professional, structured, evidence-focused",
    },
    {
        "key": "regulator",
        "name": "Atty. Carlos Lim (composite)",
        "org": "POEA Anti-Illegal Recruitment Branch (composite officer)",
        "role": "regulator",
        "voice": "formal, citation-heavy, procedural",
    },
    {
        "key": "lawyer",
        "name": "Amira Khan, Esq. (composite)",
        "org": "Migrant Worker Legal Aid (composite practice)",
        "role": "labour lawyer",
        "voice": "technical, statute-citing, client-advocacy",
    },
    {
        "key": "journalist",
        "name": "Sam Patel (composite)",
        "org": "Investigative reporter (composite byline)",
        "role": "investigative journalist",
        "voice": "open-ended, fact-checking, source-protective",
    },
]

CORRIDORS = [
    ("PH-HK",      "Philippines → Hong Kong",    "POEA MC 14-2017",
     "+63-2-8721-1144 (POEA AIRB)",       "+852-2522-8264 (MfMW HK)"),
    ("ID-HK",      "Indonesia → Hong Kong",      "BP2MI Reg 9/2020",
     "+62-21-2924-4800 (BP2MI Crisis)",   "+852-2997-2832 (IMWU HK)"),
    ("NP-Saudi",   "Nepal → Saudi Arabia",       "Nepal FEA 2007 §11(2)",
     "+977-1-4-433-401 (DoFE)",           "+966-50-303-7110 (Migrante Saudi)"),
    ("BD-Kuwait",  "Bangladesh → Kuwait",        "BD OEA 2013 §17",
     "+880-2-984-9925 (BMET)",            "+965-2245-3636 (Kuwait Soc HR)"),
    ("LK-Lebanon", "Sri Lanka → Lebanon",        "Lebanon Cabinet Decree 13166/2021",
     "+94-11-263-9277 (SLBFE)",           "+961-71-700-844 (ARM Beirut)"),
]


# ---------------------------------------------------------------------
# Content generators (one per persona × content type)
# ---------------------------------------------------------------------

def _ofw_chat_msg(corridor):
    code, route, statute, origin_hot, dest_hot = corridor
    return (
        f"[COMPOSITE EXAMPLE — OFW worker first-person chat to assistant]\n\n"
        f"po, ako po si Maria Santos (composite), 24 years old, from "
        f"Cebu (composite). I came here to {route.split('→')[1].strip()} "
        f"6 months ago through 'Pacific Coast Manpower Inc' (composite). "
        f"They told me free placement pero I had to take HKD 28,400 "
        f"'salary advance' (synthetic) from their partner lender — auto "
        f"deduction HKD 1,400/month for 21 months starting day-one. "
        f"Madame keeps my passport 'for safekeeping' since arrival. "
        f"I have one day off per month, not the 4 my contract says. "
        f"Ano po dapat kong gawin? I cannot afford to lose this job, "
        f"my mother depends on me. Please tell me what's legal here, "
        f"and what I should do."
    )


def _ofw_social_post(corridor):
    code, route, statute, origin_hot, dest_hot = corridor
    return (
        f"[COMPOSITE EXAMPLE — recruiter Facebook post targeting "
        f"{route.split('→')[0].strip()} workers]\n\n"
        f"🇭🇰 URGENT HIRING for {route.split('→')[1].strip()} "
        f"DOMESTIC WORKERS! 💰\n\n"
        f"💼 Salary: HKD 5,000/month (synthetic)\n"
        f"🏥 Free medical + insurance\n"
        f"✈️ FREE flight + visa processing\n"
        f"📅 Start ASAP — interview tomorrow!\n\n"
        f"Just need ONE-TIME 'training & documentation fee' of "
        f"HKD 25,000 (synthetic) — pay in installments from your salary, "
        f"super easy lang. Most workers earn back in 6 months!\n\n"
        f"DM if interested. Limited slots. PM only — no public comments.\n\n"
        f"#PinoyOFW #HiringHK #OFWJobs #DomesticHelper"
    )


def _ngo_intake_form(corridor):
    code, route, statute, origin_hot, dest_hot = corridor
    return (
        f"[COMPOSITE EXAMPLE — NGO intake form draft]\n\n"
        f"INTAKE FORM — DRAFT (composite case file)\n\n"
        f"Case ID: MfMW-2026-04-CMPST (composite ID)\n"
        f"Caseworker: Joana Rivera (composite)\n"
        f"Date: 2026-04-{(hash(code) % 28) + 1:02d}\n\n"
        f"WORKER\n"
        f"Name: [redacted]\n"
        f"Origin: [{route.split('→')[0].strip()}]\n"
        f"Destination: [{route.split('→')[1].strip()}]\n"
        f"Sector: domestic work\n"
        f"Months at current employer: 6\n\n"
        f"PRESENTING CONCERN\n"
        f"- Recruitment fee charged to worker (HKD ~25k synthetic)\n"
        f"- Salary advance from lender, auto-deducted from wages\n"
        f"- Passport held by employer 'for safekeeping'\n"
        f"- Day-off violations (1/mo vs contracted 4/mo)\n\n"
        f"PRELIMINARY ASSESSMENT (caseworker, not legal opinion)\n"
        f"- Multiple ILO Forced Labour Indicators present:\n"
        f"  Indicator 7 (retention of identity documents)\n"
        f"  Indicator 9 (debt bondage)\n"
        f"  Indicator 8 (withholding of wages — partial deduction)\n"
        f"  Indicator 11 (excessive overtime)\n"
        f"- Possible violation: {statute}\n"
        f"- Possible violation: ILO C189 Art. 9 (DW right to "
        f"keep travel documents)\n\n"
        f"REFERRALS QUEUED\n"
        f"- {origin_hot}\n"
        f"- {dest_hot}\n\n"
        f"NEXT ACTION\n"
        f"- Schedule legal consult\n"
        f"- Request worker authorize evidence collection\n"
        f"- Determine if employer-mediated path or "
        f"complaint-direct-to-regulator"
    )


def _regulator_complaint(corridor):
    code, route, statute, origin_hot, dest_hot = corridor
    return (
        f"[COMPOSITE EXAMPLE — POEA complaint draft for worker]\n\n"
        f"REPUBLIC OF THE PHILIPPINES\n"
        f"DEPARTMENT OF MIGRANT WORKERS — PHILIPPINE OVERSEAS "
        f"EMPLOYMENT ADMINISTRATION (POEA)\n"
        f"ANTI-ILLEGAL RECRUITMENT BRANCH\n\n"
        f"COMPLAINT — DRAFT (composite case)\n\n"
        f"COMPLAINANT: [redacted worker name], OFW deployed to "
        f"{route.split('→')[1].strip()}\n"
        f"RESPONDENT: 'Pacific Coast Manpower Inc' (composite agency)\n"
        f"DATE: 2026-04-XX (composite)\n\n"
        f"FACTS\n"
        f"1. Complainant deployed to {route.split('→')[1].strip()} on "
        f"2025-10-XX through Respondent agency (POEA License No. "
        f"composite-XXXXX).\n"
        f"2. At time of deployment, Respondent collected fees from "
        f"Complainant in violation of {statute} (zero placement fee "
        f"for {route.replace('→', '-')} domestic worker corridor).\n"
        f"3. Respondent further arranged a HKD 28,400 (synthetic) "
        f"'salary advance' from a third-party lender, structured as "
        f"automatic salary deduction — a substance-over-form "
        f"violation of ILO C181 Art. 7.\n"
        f"4. Employer in {route.split('→')[1].strip()} retains "
        f"Complainant's passport 'for safekeeping' — violation of "
        f"ILO C189 Art. 9 + ILO Forced Labour Indicator 7 (retention "
        f"of identity documents).\n\n"
        f"VIOLATIONS ALLEGED\n"
        f"- RA 8042 §6(j): illegal recruitment via retention of "
        f"travel documents (joint and several liability of foreign "
        f"principal + local agency per RA 10022 §15)\n"
        f"- POEA Rules Part VII Rule III §1: passport retention as "
        f"ground for license suspension\n"
        f"- {statute}: zero placement fee violated by 'training fee' "
        f"camouflage\n"
        f"- ILO C029 Indicator 9 (debt bondage)\n\n"
        f"PRAYER\n"
        f"- License suspension of Respondent (RA 8042 §11)\n"
        f"- Refund of all fees collected (RA 10022 §7)\n"
        f"- Repatriation costs borne by Respondent\n"
        f"- Referral to NLRC RAB for monetary award\n\n"
        f"Filed at: {origin_hot}\n"
        f"Verified online at: https://onlineservices.poea.gov.ph/"
    )


def _lawyer_advisory(corridor):
    code, route, statute, origin_hot, dest_hot = corridor
    return (
        f"[COMPOSITE EXAMPLE — lawyer client memo]\n\n"
        f"LEGAL ADVISORY — PRIVILEGED & CONFIDENTIAL (composite)\n\n"
        f"TO:    [composite client]\n"
        f"FROM:  Amira Khan, Esq. (composite)\n"
        f"RE:    Worker recruited {route} — applicable remedies\n\n"
        f"FACTUAL SUMMARY\n"
        f"Client is a {route.split('→')[0].strip()}-national "
        f"domestic worker deployed to {route.split('→')[1].strip()} "
        f"under a contract that violates {statute}. The deployment "
        f"agreement included: (a) pre-departure 'training fee' of "
        f"~USD 850 (synthetic), (b) salary-advance loan from "
        f"third-party lender repayable via automatic wage deduction, "
        f"(c) employer retention of Client's passport 'for "
        f"safekeeping'.\n\n"
        f"APPLICABLE LAW\n"
        f"1. Origin-side: {statute}.\n"
        f"2. Destination-side: relevant national labour code + "
        f"ILO C189 (Domestic Workers Convention) Art. 9 — right to "
        f"retain travel documents — and Art. 6/7 (decent work, "
        f"writing, terms-and-conditions disclosure).\n"
        f"3. International: ILO C181 Art. 7 (no fees from workers, "
        f"any form, direct or indirect) + ILO C029 §1 + ILO Forced "
        f"Labour Protocol P029 (2014) Art. 4 (access to remedies "
        f"irrespective of immigration status) + Palermo Protocol "
        f"Art. 3(b) (worker consent does not cure trafficking "
        f"violations).\n\n"
        f"REMEDIES AVAILABLE\n"
        f"A. Origin-side complaint via {origin_hot}: license "
        f"suspension + fee refund + joint-and-several recovery from "
        f"foreign principal.\n"
        f"B. Destination-side complaint via {dest_hot}: passport "
        f"recovery + back-wages + labour-court compensation.\n"
        f"C. ILO supervisory complaint via national focal point "
        f"(slower; useful for systemic abuses).\n"
        f"D. Civil suit in Client's home jurisdiction (RA 10022 §7 "
        f"in PH context).\n\n"
        f"RECOMMENDED SEQUENCE\n"
        f"(1) Document preservation: receipt photos, contract scan, "
        f"WhatsApp messages with recruiter, salary slip showing "
        f"deduction, witness statements.\n"
        f"(2) Passport recovery via destination NGO + Embassy.\n"
        f"(3) Origin-side regulator complaint while passport is "
        f"in worker's possession.\n"
        f"(4) Civil suit only after admin remedies are exhausted "
        f"or refused.\n\n"
        f"Composite advisory — do not rely without independent "
        f"counsel."
    )


def _journalist_query(corridor):
    code, route, statute, origin_hot, dest_hot = corridor
    return (
        f"[COMPOSITE EXAMPLE — journalist research query]\n\n"
        f"Hi — I'm Sam Patel (composite), investigative reporter "
        f"working on a piece about the {route} domestic worker "
        f"corridor. Can you help me understand:\n\n"
        f"1. What is the controlling fee-cap statute on the origin "
        f"side? Specifically, what does {statute} require in terms "
        f"of placement fees the worker can be charged?\n\n"
        f"2. What are the documented enforcement actions in the "
        f"past 24 months by {origin_hot.split(' (')[0]}? Are there "
        f"public license-suspension records?\n\n"
        f"3. What's the standard NGO referral path for a worker "
        f"who calls today? Specifically, how do "
        f"{dest_hot.split(' (')[0]} and the origin-side regulator "
        f"coordinate on a single case?\n\n"
        f"4. Are there 2024-2025 cases I can cite where this "
        f"corridor's harness/oversight worked AS DESIGNED — i.e., "
        f"the worker was returned, the fees refunded, the agency "
        f"sanctioned? I want to balance my piece — most coverage "
        f"is failure stories.\n\n"
        f"Anything I should triple-check before publication?"
    )


CONTENT_GENERATORS = [
    ("ofw_chat",          "ofw_worker",    "OFW first-person chat: scared worker asks the assistant",            _ofw_chat_msg),
    ("ofw_social",        "ofw_worker",    "Recruiter Facebook post targeting the corridor's workers",         _ofw_social_post),
    ("ngo_intake",        "ngo_caseworker", "NGO caseworker intake form for the worker case",                   _ngo_intake_form),
    ("regulator_filing",  "regulator",     "Regulator-side complaint draft (POEA / equivalent)",                _regulator_complaint),
    ("lawyer_memo",       "lawyer",        "Privileged lawyer advisory memo to the client worker",              _lawyer_advisory),
    ("journalist_query",  "journalist",    "Investigative reporter query about the corridor",                    _journalist_query),
]


def main() -> int:
    existing = json.load(open(TARGET, encoding="utf-8"))
    existing_ids = {e["id"] for e in existing}
    new_entries = []
    for ctype, persona_key, label_template, gen in CONTENT_GENERATORS:
        for corridor in CORRIDORS:
            code = corridor[0]
            route = corridor[1]
            entry_id = f"persona_{ctype}_{code.replace('-', '_').lower()}"
            if entry_id in existing_ids:
                continue
            entry = {
                "id":         entry_id,
                "category":   f"persona_{persona_key}",
                "label":      f"{label_template} — {route}",
                "content":    gen(corridor),
            }
            new_entries.append(entry)
    if not new_entries:
        print("No new entries (all already present).")
        return 0
    existing.extend(new_entries)
    with open(TARGET, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    print(f"Added {len(new_entries)} entries; total now {len(existing)}.")
    print("Categories:")
    from collections import Counter
    cats = Counter(e.get("category", "?") for e in existing)
    for c, n in sorted(cats.items()):
        print(f"  {c}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
