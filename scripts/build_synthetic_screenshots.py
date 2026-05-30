"""Generate SYNTHETIC chat-screenshot fixtures for multimodal trafficking tests.

Renders composite (fully invented) recruiter / employer / scam-center
conversations as phone-style chat screenshots so Gemma 4's vision can be tested
on "read this screenshot and identify the trafficking indicators". Grounded in
the researched modus operandi (recruitment-fee "investment" manipulation,
passport "safekeeping", debt bondage, scam-compound job lure, contract
substitution, money-mule recruitment) — see
docs/research/civil_society_intelligence_2026_05_29.md.

SAFETY (rule 10): every name, number, and detail here is INVENTED. No real
people, case numbers, phone numbers, IDs, or accounts. Output goes to the
gitignored data/ tree; the generator + the JSON manifest are the committed,
regeneratable assets. Requires Pillow:
    <python-with-Pillow> scripts/build_synthetic_screenshots.py
"""
from __future__ import annotations

import json
import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic_multimodal"

W = 760
PAD = 18
BUBBLE_MAX = 520
HEADER_H = 92
BG = (236, 229, 221)        # WhatsApp-ish paper
THEM_BG = (255, 255, 255)
ME_BG = (220, 248, 198)
INK = (17, 20, 24)
MUTE = (120, 125, 132)


def _font(size: int, bold: bool = False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f"C:\\Windows\\Fonts\\{name}", size)
        except Exception:
            continue
    return ImageFont.load_default()


F_HEAD = _font(28, bold=True)
F_SUB = _font(18)
F_MSG = _font(23)
F_TIME = _font(15)

# --- Synthetic conversations (composite; each illustrates real indicators) ---
CONVERSATIONS = [
    {
        "id": "investment_fee_ph_hk",
        "contact": "Ate Marivic (Recruiter)",
        "platform": "whatsapp",
        "scheme": "recruitment_fee_debt_bondage / fee_camouflage",
        "indicators": ["debt_bondage", "deception", "abuse_of_vulnerability"],
        "expected_detection": "Illegal placement fee reframed as an 'investment'; PH->HK domestic work has a zero-placement-fee policy. Debt-bondage + fee-camouflage indicators.",
        "messages": [
            ("them", "Sis, I know HKD 25,000 sounds like a lot, but stop thinking of it as a fee. This is an INVESTMENT in your future."),
            ("them", "In just 1-2 months of salary you recover it. After that it's pure profit for your family in Cebu."),
            ("me", "But where do I get 25,000 now? I don't have it."),
            ("them", "Don't worry, you sign a small IOU now, pay from salary. I have 5 other girls wanting this slot but I chose you."),
            ("them", "Employer needs documents by tomorrow. Don't lose this chance over a few thousand you'll make back in weeks."),
        ],
    },
    {
        "id": "passport_safekeeping_kuwait",
        "contact": "Madam (Employer)",
        "platform": "whatsapp",
        "scheme": "passport_safekeeping_euphemism",
        "indicators": ["retention_of_identity_documents", "restriction_of_movement"],
        "expected_detection": "Employer demanding passport 'for safekeeping' = document retention, an ILO forced-labour indicator. Worker has the right to keep their own passport.",
        "messages": [
            ("them", "When you arrive I will keep your passport in my safe, for safekeeping only. Everyone does this here."),
            ("me", "I would prefer to keep my own passport, ma'am."),
            ("them", "No. If you keep it you might run away. I paid a lot for you. You get it back after 2 years when contract finish."),
        ],
    },
    {
        "id": "scam_compound_job_lure",
        "contact": "GoldStar HR (Telegram)",
        "platform": "telegram",
        "scheme": "forced_criminality_recruitment",
        "indicators": ["deception", "abuse_of_vulnerability"],
        "expected_detection": "Too-good IT/customer-service offer routed via Bangkok with upfront 'training deposit' + passport copy = scam-compound recruitment lure (forced criminality).",
        "messages": [
            ("them", "Congratulations! Customer service role, USD 1,500/month + free housing, no experience needed. Office in Bangkok."),
            ("them", "Just send a copy of your passport and a USD 300 training deposit to confirm your seat. Flights arranged for you."),
            ("me", "Why do I pay a deposit before starting?"),
            ("them", "Standard. You get it back first salary. Many people waiting, reply fast or you lose the slot."),
        ],
    },
    {
        "id": "debt_bondage_cannot_leave",
        "contact": "Agency (Riyadh)",
        "platform": "messenger",
        "scheme": "debt_bondage / restriction_of_movement",
        "indicators": ["debt_bondage", "restriction_of_movement", "withholding_of_wages"],
        "expected_detection": "Worker told she cannot leave until a 42,000-peso 'debt' (ticket + fee) is repaid from withheld wages = debt bondage + restriction of movement.",
        "messages": [
            ("me", "I want to go home. The work is too much and I am not paid for 2 months."),
            ("them", "You cannot leave. You still owe 42,000 pesos for your ticket and agency fee."),
            ("them", "Once you finish paying from your salary, then you are free to go. Until then you stay."),
        ],
    },
    {
        "id": "contract_substitution_arrival",
        "contact": "Mr. Tan (Employer, Taiwan)",
        "platform": "whatsapp",
        "scheme": "contract_substitution",
        "indicators": ["deception", "abusive_working_living_conditions"],
        "expected_detection": "Contract signed at home replaced on arrival with lower pay + extra duties = contract substitution (deception). The original terms should hold.",
        "messages": [
            ("them", "Forget the contract from your agency. Here you sign new one: NT$17,000, and you also clean my mother's house next door."),
            ("me", "But my contract said NT$20,000 and only caregiving for one person."),
            ("them", "That paper is for immigration only. In my house, my rules. Sign or go back, but then you owe the agency."),
        ],
    },
    {
        "id": "money_mule_recruitment",
        "contact": "James (Online 'employer')",
        "platform": "telegram",
        "scheme": "money_mule",
        "indicators": ["deception", "abuse_of_vulnerability"],
        "expected_detection": "Stranger offering easy commission to receive money into the worker's bank account and forward it = money-mule recruitment / laundering of scam proceeds.",
        "messages": [
            ("them", "Easy part-time: I send money to your bank account, you withdraw and send to my partner, keep 10% commission."),
            ("me", "Whose money is it? Is this legal?"),
            ("them", "My business funds, totally fine. Many do this. You can earn USD 200 this week, just give me your account number."),
        ],
    },
]


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _platform_color(p):
    return {"whatsapp": (7, 94, 84), "telegram": (40, 159, 217),
            "messenger": (0, 132, 255)}.get(p, (7, 94, 84))


def render(conv: dict) -> Image.Image:
    head = _platform_color(conv["platform"])
    tmp = Image.new("RGB", (W, 10))
    d = ImageDraw.Draw(tmp)
    blocks = []
    for side, text in conv["messages"]:
        lines = _wrap(d, text, F_MSG, BUBBLE_MAX - 2 * 16)
        h = len(lines) * (F_MSG.size + 6) + 28
        blocks.append((side, lines, h))
    total_h = HEADER_H + PAD + sum(h + 12 for _s, _l, h in blocks) + PAD
    img = Image.new("RGB", (W, total_h), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, HEADER_H], fill=head)
    d.ellipse([16, 20, 16 + 52, 20 + 52], fill=(255, 255, 255))
    d.text((30, 30), conv["contact"][:1].upper(), font=F_HEAD, fill=head)
    d.text((84, 22), conv["contact"], font=F_HEAD, fill=(255, 255, 255))
    d.text((84, 56), "online", font=F_SUB, fill=(225, 240, 235))
    y = HEADER_H + PAD
    for side, lines, h in blocks:
        bw = min(BUBBLE_MAX, 16 * 2 + max(d.textlength(ln, font=F_MSG) for ln in lines))
        x0 = PAD if side == "them" else W - PAD - bw
        d.rounded_rectangle([x0, y, x0 + bw, y + h], radius=16,
                            fill=THEM_BG if side == "them" else ME_BG)
        ty = y + 12
        for ln in lines:
            d.text((x0 + 16, ty), ln, font=F_MSG, fill=INK)
            ty += F_MSG.size + 6
        d.text((x0 + bw - 52, y + h - 22), "09:4" + str(len(lines)), font=F_TIME, fill=MUTE)
        y += h + 12
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for conv in CONVERSATIONS:
        img = render(conv)
        fn = f"{conv['id']}.png"
        img.save(OUT / fn)
        manifest.append({
            "id": conv["id"], "file": fn, "contact": conv["contact"],
            "platform": conv["platform"], "scheme": conv["scheme"],
            "indicators": conv["indicators"],
            "expected_detection": conv["expected_detection"],
            "messages": [{"from": s, "text": t} for s, t in conv["messages"]],
        })
    (OUT / "manifest.json").write_text(
        json.dumps({"n": len(manifest), "note": "Synthetic composite chat screenshots "
                    "for multimodal trafficking-indicator tests. No PII.",
                    "fixtures": manifest}, indent=2), encoding="utf-8")
    print(f"wrote {len(manifest)} screenshots + manifest.json to {OUT}")


if __name__ == "__main__":
    main()
