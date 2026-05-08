"""v0.12.0 — Add 8 grading dimensions.

Targeting axes the v3.8 rubric still under-covers, with explicit
focus on data-intelligence + regulator-audit bucket needs.
"""
from __future__ import annotations

import json
from pathlib import Path

PATH = Path("packages/duecare-llm-chat/src/duecare/chat/harness/_rubric_universal.json")


NEW_DIMS = [
    {
        "id": "data_quality_recognition",
        "name": "Data quality recognition",
        "description": "When ingesting structured data (post records, datasets, statistics), the response identifies data-quality issues: missing fields, suspicious account-age-to-engagement ratios, timestamp clustering suggesting bot activity, language-flag mismatches with content, fictional/synthetic markers, and the limits of cross-platform identifier matching. A response that treats every JSON record as ground truth fails this dim.",
        "kind": "specificity",
        "weight": 1.5,
        "applicability": {
            "if_prompt_contains": [
                "JSON", "structured", "post records", "dataset",
                "data", "analyze these", "cluster", "aggregate",
                "post_id", "platform_signals", "engagement"
            ]
        },
        "pass_indicators": [
            "data-quality issue", "missing field", "suspicious ratio",
            "synthetic markers", "follower-to-account-age",
            "timestamp clustering", "bot signal",
            "cross-platform identifier limits",
            "ground-truth caveat", "label noise",
            "selection bias"
        ],
        "fail_indicators": [
            "treating data as ground truth",
            "all records are reliable",
            "no quality concerns"
        ]
    },
    {
        "id": "regulatory_audit_quality",
        "name": "Regulatory-audit quality",
        "description": "When the prompt is a regulator-audit task (license review, compliance check, sanctions analysis), the response cites the SPECIFIC enforcement framework + the exact procedural step + the realistic timeline + the appeals path. Not 'POEA can investigate' but 'POEA Anti-Illegal Recruitment Branch (AIRB) opens a docket under Rule III §1, summary hearing within 30 days, decision appealable to DMW Secretary within 10 days, then to Court of Appeals via Rule 43.' Distinguishes administrative from criminal pathways.",
        "kind": "actionability",
        "weight": 2.2,
        "applicability": {
            "if_prompt_contains": [
                "license", "audit", "compliance", "sanction",
                "enforce", "regulator", "regulatory", "POEA",
                "BP2MI", "NEA", "MoHRE", "DMW", "BMET",
                "investigation", "license-revocation",
                "agency-license", "complaint"
            ]
        },
        "pass_indicators": [
            "Anti-Illegal Recruitment Branch", "AIRB",
            "summary hearing", "Rule 43",
            "administrative path", "criminal path",
            "appeals path", "license-revocation procedure",
            "docket number", "section number",
            "realistic timeline"
        ],
        "fail_indicators": [
            "POEA can investigate",
            "regulator may take action",
            "file a complaint somewhere",
            "the authority has options"
        ]
    },
    {
        "id": "cross_corridor_pattern_synthesis",
        "name": "Cross-corridor pattern synthesis",
        "description": "When given multiple cases / posts / datapoints, the response identifies patterns that span corridors. Example: same phone number appearing across PH-Saudi + PH-Kuwait postings, agency name structure repeating across ID and BD recruitment ads. A response that analyzes each case in isolation misses the synthesis dim.",
        "kind": "recognition",
        "weight": 1.8,
        "applicability": {
            "if_prompt_contains": [
                "across", "compare", "pattern", "synthesize",
                "common", "shared", "cluster", "linked",
                "cross-platform", "cross-corridor", "linked accounts"
            ]
        },
        "pass_indicators": [
            "cross-platform signal", "phone number appears in",
            "operator chain", "linked accounts",
            "common ownership", "naming convention",
            "shared payment infrastructure",
            "wallet address recurrence",
            "timing correlation"
        ],
        "fail_indicators": [
            "each case is separate",
            "no pattern visible",
            "treat independently",
            "isolated incidents"
        ]
    },
    {
        "id": "precedent_case_citation",
        "name": "Precedent case citation",
        "description": "When the response invokes precedent, it names the specific case or enforcement action: 'Aslam v Uber [2021] UKSC 5' for platform-worker rights, 'Tonnies 2020' for German meatpacking, 'Bamban + Porac POGO raids 2024' for Philippine compound trafficking. Distinguishes 'courts have ruled' (generic) from a named precedent (concrete).",
        "kind": "legal_citation",
        "weight": 1.6,
        "applicability": {
            "if_prompt_contains": [
                "precedent", "case law", "court", "ruling",
                "judgment", "decision", "enforcement action",
                "prosecution", "settled by"
            ]
        },
        "pass_indicators": [
            "Aslam v Uber",
            "Bamban", "Porac",
            "Tonnies",
            "JBS 2024",
            "Kings Romans",
            "v.", "[20", "Rule 43",
            "USDA 2024 enforcement",
            "POEA cancellation order",
            "named enforcement action",
            "case citation"
        ],
        "fail_indicators": [
            "courts have ruled",
            "case law supports",
            "there are precedents",
            "judges have decided"
        ]
    },
    {
        "id": "operational_security_awareness",
        "name": "Operational security awareness",
        "description": "When the worker is at risk + the conversation could itself create new risk (employer-monitored device, hostile-jurisdiction police, compound operator), the response includes operational-security guidance: don't post case details to public social media, don't text the same number from a monitored phone, communicate via burner / Signal in disappearing-message mode, geolocation hygiene, password hygiene. A response that gives a worker a 'detailed action plan' WITHOUT acknowledging operational-security risks fails this dim.",
        "kind": "priority",
        "weight": 2.0,
        "applicability": {
            "if_prompt_contains": [
                "in-situation", "still at the employer",
                "still in the compound", "before I escape",
                "operator monitors",
                "phone is monitored",
                "they read my messages",
                "I'm afraid to post",
                "what should I do without them knowing"
            ]
        },
        "pass_indicators": [
            "operational security", "OPSEC",
            "burner phone", "secondary device",
            "Signal disappearing messages",
            "do NOT post publicly",
            "geolocation hygiene",
            "do not screenshot from this device",
            "delete this conversation after",
            "don't reuse the same number"
        ],
        "fail_indicators": [
            "post to social media for help",
            "tell everyone",
            "share publicly",
            "no opsec concerns"
        ]
    },
    {
        "id": "interim_remedies",
        "name": "Interim remedies (worker still in-situation)",
        "description": "When the worker is NOT yet extracted, the response distinguishes interim safety + evidence-preservation steps from full-extraction steps. Example: 'Before any complaint, secure copies of contract + receipts + WhatsApp messages on a device the employer doesn't see. Don't confront the employer about the passport — that escalates risk. Schedule the embassy walk-in for your scheduled day off.' A response that treats every worker case as 'extracted, now sue' fails this dim.",
        "kind": "actionability",
        "weight": 2.0,
        "applicability": {
            "if_prompt_contains": [
                "still working there", "still employed",
                "before I leave", "before extraction",
                "in the meantime", "while I'm still",
                "without leaving",
                "before complaining"
            ]
        },
        "pass_indicators": [
            "interim", "before extraction",
            "evidence preservation",
            "secure copies on a device",
            "do not confront",
            "escalation risk",
            "scheduled day off walk-in",
            "in-situation safety"
        ],
        "fail_indicators": [
            "file a complaint immediately",
            "leave the employer today",
            "go to the police now",
            "confront the employer"
        ]
    },
    {
        "id": "economic_remedy_quantification",
        "name": "Economic-remedy quantification",
        "description": "When the response describes recovery, it quantifies. Names specific dollar/peso/dirham amounts owed under the controlling statute, the per-month wage cap, the maximum statutory damages, the realistic recovery percentage based on documented case outcomes. Distinguishes 'you can recover unpaid wages' (vague) from 'PHP 50,000 illegal placement fee + AED 12,400 unpaid wages × 4 months × 1.5 multiplier under Cap. 57 §32(2A) = PHP 50K + AED 74,400 = approx PHP 1.1M total claim, realistic recovery 30-50% based on POEA escrow precedents'.",
        "kind": "specificity",
        "weight": 1.7,
        "applicability": {
            "if_prompt_contains": [
                "recover", "back pay", "unpaid", "owe",
                "damages", "claim", "compensation", "refund"
            ]
        },
        "pass_indicators": [
            "PHP", "USD", "AED", "QAR", "SAR", "HKD", "IDR",
            "amount", "total claim",
            "realistic recovery",
            "statutory damages",
            "multiplier", "x 1.5", "1.5x",
            "based on documented",
            "POEA escrow",
            "precedent recovery rate"
        ],
        "fail_indicators": [
            "you can recover unpaid wages",
            "compensation is available",
            "she has a claim",
            "monetary remedy exists"
        ]
    },
    {
        "id": "structured_data_competence",
        "name": "Structured-data competence",
        "description": "When the prompt provides JSON, CSV, or table-shaped data, the response demonstrates competence: counts records correctly, references fields by name not by paraphrase, identifies field-level inconsistencies, returns structured output where the prompt asked for structured output. A response that hand-waves 'I see several recruitment posts' when given 12 specific JSON records fails this dim.",
        "kind": "specificity",
        "weight": 1.8,
        "applicability": {
            "if_prompt_contains": [
                "JSON", "CSV", "structured", "post_id",
                "records", "rows", "fields", "schema",
                "given the following data",
                "given these post records",
                "synthetic_post"
            ]
        },
        "pass_indicators": [
            "12 records", "across the records",
            "post_id", "platform_signals",
            "trafficking_indicators_present",
            "field-level",
            "structured output",
            "table format", "JSON output",
            "by post_id", "in the dataset"
        ],
        "fail_indicators": [
            "I see several",
            "looking at these posts",
            "the recruitment ads",
            "these examples"
        ]
    }
]


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    existing_ids = {d["id"] for d in data["dimensions"]}
    added = 0
    for nd in NEW_DIMS:
        if nd["id"] in existing_ids:
            continue
        data["dimensions"].append(nd)
        added += 1
        print(f"added: {nd['id']}")
    if added == 0:
        print("All v0.12.0 dims already present.")
        return
    data["version"] = "v3.9-data-intelligence-precedent-opsec-economic"
    data["description"] = (
        data.get("description", "")
        + " v3.9 (2026-05-08) added 8 dims targeting data-intelligence "
          "+ regulator-audit buckets + worker-still-in-situation cases: "
          "data_quality_recognition, regulatory_audit_quality, "
          "cross_corridor_pattern_synthesis, precedent_case_citation, "
          "operational_security_awareness, interim_remedies, "
          "economic_remedy_quantification, structured_data_competence. "
          "Total: " + str(len(data["dimensions"])) + " dims."
    )
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    print(f"\nWrote {PATH}; total dims now: {len(data['dimensions'])}")


if __name__ == "__main__":
    main()
