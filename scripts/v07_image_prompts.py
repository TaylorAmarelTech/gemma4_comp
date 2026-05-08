"""Append image_prompts bucket to _examples.json (v0.7.0 follow-up).

Idempotent — checks for existing image_prompts entries and skips if
they're already present. Designed to be safe to re-run.

Image prompts are TEXT prompts paired with an `image_hint` that tells
the user what kind of image to attach via the chat's upload affordance.
The Gemma 4 E4B + 31B variants are multimodal; this bucket exercises
that capability with realistic moderator / NGO / worker scenarios.
"""
from __future__ import annotations

import json
from pathlib import Path

EXAMPLES_PATH = Path(
    "packages/duecare-llm-chat/src/duecare/chat/harness/_examples.json"
)


def main() -> None:
    data = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    existing_image_ids = {
        p.get("id") for p in data
        if p.get("bucket") == "image_prompts"
    }
    new_prompts = _image_prompts()
    to_add = [p for p in new_prompts if p["id"] not in existing_image_ids]
    if not to_add:
        print("All image_prompts entries already present; nothing to add.")
        return
    data.extend(to_add)
    print(f"Added {len(to_add)} image_prompts entries.")
    print(f"Final prompt count: {len(data)}")
    EXAMPLES_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")


def _image_prompts() -> list[dict]:
    return [
        {
            "id":          "img_001",
            "bucket":      "image_prompts",
            "category":    "document_image_review",
            "subcategory": "recruitment_receipt",
            "image_hint":  "Photograph or scan of a recruitment-agency receipt. Should show line-items like 'training fee', 'medical exam', 'documentation', currency amounts, agency name + license number, and a worker signature.",
            "text":        "Attached: a recruitment-agency receipt my client kept. Walk through every line item and tell me which charges look prohibited under the controlling statute (the corridor is PH→HK domestic). For each prohibited charge name the specific law/circular that bans it.",
            "sector":      "domestic_work",
            "corridor":    "PH-HK",
            "difficulty":  "medium",
            "ilo_indicators": ["fee_fraud"],
        },
        {
            "id":          "img_002",
            "bucket":      "image_prompts",
            "category":    "document_image_review",
            "subcategory": "passport_stamp",
            "image_hint":  "Photo of a passport page showing entry stamps + visa pages. The interesting one will be a Saudi domestic-worker visa or a Qatar work-permit entry stamp.",
            "text":        "Photo of my client's passport. She's an Indonesian domestic worker. Identify her current immigration status from these stamps and tell me whether her residency is tied to her employer (and if so, what that means for her ability to leave the job).",
            "sector":      "domestic_work",
            "corridor":    "ID-SA",
            "difficulty":  "medium",
            "ilo_indicators": ["passport_retention"],
        },
        {
            "id":          "img_003",
            "bucket":      "image_prompts",
            "category":    "social_media_image",
            "subcategory": "facebook_recruitment_post",
            "image_hint":  "Screenshot of a Facebook recruitment post for domestic / construction / fishing work in a Gulf or Asian destination. Should show the ad copy, agency contact, and any reactions/comments.",
            "text":        "Screenshot of a recruitment post that's been viral in our Indonesian-Saudi corridor monitoring group. Classify it: which red flags / ILO indicators / regulatory violations are visible just from this post? What action would you recommend our enterprise content-mod team take?",
            "sector":      "domestic_work",
            "corridor":    "ID-SA",
            "difficulty":  "medium",
            "ilo_indicators": ["fee_fraud", "deception"],
        },
        {
            "id":          "img_004",
            "bucket":      "image_prompts",
            "category":    "social_media_image",
            "subcategory": "tiktok_post",
            "image_hint":  "Screenshot of a TikTok post or DM advertising overseas work. Captions in Tagalog / Bahasa / Bengali / Nepali are common.",
            "text":        "TikTok screenshot reported by a user. The caption is in Tagalog. Translate it, identify the recruiter's pitch, list the red flags, and rank how high-risk this is on a 1-5 scale with rationale.",
            "sector":      "domestic_work",
            "corridor":    "PH-HK",
            "difficulty":  "medium",
            "ilo_indicators": ["fee_fraud", "deception"],
        },
        {
            "id":          "img_005",
            "bucket":      "image_prompts",
            "category":    "evidence_image",
            "subcategory": "contract_clause",
            "image_hint":  "Photo of a printed employment contract page showing fee / wage / termination clauses. Best if low-resolution / phone photo (typical of how a worker would document their contract).",
            "text":        "Worker took this phone photo of her contract before signing. Read the visible clauses and flag any that violate the relevant origin or destination labour law. Be specific about the clause text and the violation.",
            "sector":      "domestic_work",
            "corridor":    "PH-HK",
            "difficulty":  "medium",
            "ilo_indicators": ["fee_fraud", "wage_withholding"],
        },
        {
            "id":          "img_006",
            "bucket":      "image_prompts",
            "category":    "evidence_image",
            "subcategory": "whatsapp_screenshot",
            "image_hint":  "Screenshot of a WhatsApp / Messenger / Telegram conversation between worker and recruiter or worker and employer. Often shows wage threats, fee demands, or document-retention statements.",
            "text":        "WhatsApp screenshot from my client's phone — she's an Ethiopian worker in Lebanon, this is from her employer. Read the conversation and identify whether any of the messages constitute evidence of an ILO Forced Labour indicator. Summarize each in plain language for inclusion in a case file.",
            "sector":      "domestic_work",
            "corridor":    "ET-LB",
            "difficulty":  "hard",
            "ilo_indicators": ["wage_withholding", "physical_violence", "passport_retention"],
        },
        {
            "id":          "img_007",
            "bucket":      "image_prompts",
            "category":    "marketplace_image",
            "subcategory": "fishing_recruitment_listing",
            "image_hint":  "Screenshot or photo of a marketplace / classified ad recruiting fishing-vessel crew. Often Indonesian or Bangladeshi origin to Taiwanese vessels.",
            "text":        "Marketplace listing for deep-sea fishing crew. Walk through which terms in the ad correspond to known ILO indicators (passport retention, isolation, abusive conditions). Recommend a moderation decision and cite the policy basis.",
            "sector":      "fishing",
            "corridor":    "ID-TW",
            "difficulty":  "medium",
            "ilo_indicators": ["passport_retention", "isolation", "abusive_conditions"],
        },
        {
            "id":          "img_008",
            "bucket":      "image_prompts",
            "category":    "document_image_review",
            "subcategory": "promissory_note",
            "image_hint":  "Photo of a hand-written or printed promissory note / IOU / loan agreement between a worker and a recruitment agency or third-party lender. Often shows large rupee / peso / taka amounts with monthly deduction schedules.",
            "text":        "Promissory note my client signed before deployment. Extract: total amount, repayment schedule, lender identity, governing-law clause if any. Then evaluate whether this loan structure is consistent with debt bondage and which authority would have jurisdiction over it.",
            "sector":      "construction",
            "corridor":    "BD-MY",
            "difficulty":  "hard",
            "ilo_indicators": ["debt_bondage"],
        },
    ]


if __name__ == "__main__":
    main()
