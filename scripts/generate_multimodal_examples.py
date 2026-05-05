"""Generate 5 multimodal classifier examples (image + text) for the
v3.16 omni demo so judges can exercise Gemma 4's multimodal capability
on more realistic platform / document inputs.

Each entry follows the existing _classifier_examples.json schema:
    {id, category, label, content, image_data_uri (base64 SVG)}

Composite anonymization rules per docs/anonymization_policy.md:
    - All names / IDs / phone numbers are explicitly synthetic
    - Tagged "[COMPOSITE EXAMPLE]" so reviewers can never mistake
      them for real cases
    - Reserved-for-fiction phone prefixes (+1-555 / +63-2-* / etc.)

The 5 new entries cover modern attack surfaces that were absent from
the original 6 image-bearing examples:
    1. TikTok recruitment ad (2024-2026 dominant platform)
    2. Telegram money-mule recruiter (cross-border fin-flow)
    3. Cam-studio onboarding contract (sextortion entry pattern)
    4. Backdated employment contract (document fraud)
    5. Two-contract pattern side-by-side (bait-and-switch)

Run:
    python scripts/generate_multimodal_examples.py

Outputs:
    packages/duecare-llm-chat/src/duecare/chat/harness/_classifier_examples.json
        (extends in place; preserves existing 46 entries)
"""
from __future__ import annotations

import base64
import json
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
TARGET = (REPO / "packages" / "duecare-llm-chat" / "src" / "duecare"
            / "chat" / "harness" / "_classifier_examples.json")


def svg_data_uri(svg: str) -> str:
    """Encode a raw SVG string to a base64 data URI."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


# -----------------------------------------------------------------------
# 1. TikTok recruitment ad — vertical 9:16 mockup with text overlay
# -----------------------------------------------------------------------
TIKTOK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="360" height="640" viewBox="0 0 360 640">
  <rect x="0" y="0" width="360" height="640" fill="#000000"/>
  <rect x="0" y="0" width="360" height="44" fill="#000000"/>
  <text x="180" y="29" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="16" font-weight="700" fill="white">TikTok</text>
  <rect x="0" y="44" width="360" height="466" fill="#1a1a1a"/>
  <rect x="20" y="80" width="280" height="180" fill="#252525" stroke="#444" stroke-width="1" rx="8"/>
  <text x="160" y="170" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#888">[ video thumbnail ]</text>
  <text x="160" y="190" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#888">smiling worker on beach</text>
  <text x="20" y="290" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="700" fill="#fff">@DubaiRecruitOPF (composite)</text>
  <text x="20" y="312" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">URGENT 🔥 Filipina caregivers needed</text>
  <text x="20" y="332" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">in Dubai! Salary AED 1,500/month</text>
  <text x="20" y="352" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">+ free flight + free visa + free</text>
  <text x="20" y="372" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">accommodation. Fly out in 2 weeks!</text>
  <text x="20" y="402" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">Only 3 spots left! Decide TODAY.</text>
  <text x="20" y="430" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">DM us — no public comments allowed.</text>
  <text x="20" y="465" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#ff3050">#FilipinaOFW #Dubai #UrgentHiring</text>
  <text x="20" y="483" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#ff3050">#NoFee #Direct</text>
  <rect x="0" y="510" width="360" height="130" fill="#000000"/>
  <text x="180" y="540" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#999">12.4K likes · 847 comments · 3.2K shares</text>
  <circle cx="320" cy="320" r="22" fill="#ff3050"/>
  <text x="320" y="326" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#fff">♥</text>
</svg>"""


# -----------------------------------------------------------------------
# 2. Telegram money-mule recruiter chat — vertical phone mockup
# -----------------------------------------------------------------------
TELEGRAM_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="360" height="540" viewBox="0 0 360 540">
  <rect x="0" y="0" width="360" height="540" fill="#0e1621"/>
  <rect x="0" y="0" width="360" height="50" fill="#17212b"/>
  <text x="14" y="32" font-family="Helvetica, Arial, sans-serif" font-size="16" font-weight="700" fill="white">Telegram</text>
  <text x="346" y="20" text-anchor="end" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#7d8a99">@QuickEarnHub_Bot</text>
  <text x="346" y="36" text-anchor="end" font-family="Helvetica, Arial, sans-serif" font-size="10" fill="#5288c1">Last seen recently</text>
  <rect x="14" y="70" width="240" height="60" fill="#182533" stroke="#1d2c3a" stroke-width="1" rx="8"/>
  <text x="26" y="88" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">Hello! Earn $500-2000 per day</text>
  <text x="26" y="106" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">working from home — no skills</text>
  <text x="26" y="124" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">required. Just receive + forward.</text>
  <rect x="14" y="142" width="240" height="46" fill="#182533" stroke="#1d2c3a" stroke-width="1" rx="8"/>
  <text x="26" y="160" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">You receive payments to your bank.</text>
  <text x="26" y="178" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">Forward 90%, keep 10%.</text>
  <rect x="106" y="200" width="240" height="44" fill="#2b5278" stroke="#3d6993" stroke-width="1" rx="8"/>
  <text x="120" y="218" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">What kind of money is it?</text>
  <text x="120" y="236" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">Is this legal?</text>
  <rect x="14" y="256" width="240" height="84" fill="#182533" stroke="#1d2c3a" stroke-width="1" rx="8"/>
  <text x="26" y="274" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">Don't ask questions, just follow</text>
  <text x="26" y="292" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">our SOP. Open new account at</text>
  <text x="26" y="310" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">3 banks for splitting (under</text>
  <text x="26" y="328" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">$10,000 each transfer).</text>
  <rect x="106" y="350" width="240" height="44" fill="#2b5278" stroke="#3d6993" stroke-width="1" rx="8"/>
  <text x="120" y="368" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">I'm a Filipina student.</text>
  <text x="120" y="386" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">Can I do this?</text>
  <rect x="14" y="404" width="240" height="64" fill="#182533" stroke="#1d2c3a" stroke-width="1" rx="8"/>
  <text x="26" y="422" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">Perfect for students! No risk to</text>
  <text x="26" y="440" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">you — sign here, we handle the</text>
  <text x="26" y="458" font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#fff">paperwork. Send your bank info.</text>
  <text x="180" y="500" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#5d7280">[ end of conversation ]</text>
</svg>"""


# -----------------------------------------------------------------------
# 3. Cam-studio onboarding contract excerpt
# -----------------------------------------------------------------------
CAM_CONTRACT_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="360" height="500" viewBox="0 0 360 500">
  <rect x="0" y="0" width="360" height="500" fill="#fafaf6" stroke="#888" stroke-width="1"/>
  <text x="180" y="34" text-anchor="middle" font-family="Times New Roman, serif" font-size="16" font-weight="700" fill="#111">CONTENT CREATOR AGREEMENT</text>
  <text x="180" y="52" text-anchor="middle" font-family="Times New Roman, serif" font-size="11" fill="#444">Studio Astra Live (composite)  ·  Prague, CZ branch</text>
  <line x1="20" y1="72" x2="340" y2="72" stroke="#333"/>
  <text x="20" y="94" font-family="Times New Roman, serif" font-size="12" fill="#222">1. CREATOR (composite name): Lina Petrova</text>
  <text x="20" y="112" font-family="Times New Roman, serif" font-size="12" fill="#222">2. PASSPORT: held by STUDIO during contract period (24 mo)</text>
  <text x="20" y="130" font-family="Times New Roman, serif" font-size="12" fill="#222">   for "safekeeping" per Section 7.3</text>
  <text x="20" y="156" font-family="Times New Roman, serif" font-size="12" fill="#222">3. ADVANCE PAID: USD 12,000 to cover</text>
  <text x="20" y="174" font-family="Times New Roman, serif" font-size="12" fill="#222">     - Visa fees                  $3,500</text>
  <text x="20" y="192" font-family="Times New Roman, serif" font-size="12" fill="#222">     - Travel + housing deposit   $4,500</text>
  <text x="20" y="210" font-family="Times New Roman, serif" font-size="12" fill="#222">     - Equipment + lighting       $2,500</text>
  <text x="20" y="228" font-family="Times New Roman, serif" font-size="12" fill="#222">     - Training + content prep    $1,500</text>
  <text x="20" y="254" font-family="Times New Roman, serif" font-size="12" fill="#222">4. REPAYMENT: 70% of streaming revenue retained by</text>
  <text x="20" y="272" font-family="Times New Roman, serif" font-size="12" fill="#222">   STUDIO until USD 12,000 + 24% interest is recovered.</text>
  <text x="20" y="298" font-family="Times New Roman, serif" font-size="12" fill="#222">5. CONTENT QUOTAS: 8 hours/day live, 6 days/week.</text>
  <text x="20" y="316" font-family="Times New Roman, serif" font-size="12" fill="#222">   Failure to meet quota: USD 200/missed-day deducted</text>
  <text x="20" y="334" font-family="Times New Roman, serif" font-size="12" fill="#222">   from advance.</text>
  <text x="20" y="360" font-family="Times New Roman, serif" font-size="12" fill="#222">6. NON-COMPETE: Creator shall not stream on any</text>
  <text x="20" y="378" font-family="Times New Roman, serif" font-size="12" fill="#222">   platform outside STUDIO control during AND for</text>
  <text x="20" y="396" font-family="Times New Roman, serif" font-size="12" fill="#222">   24 months after contract termination.</text>
  <text x="20" y="422" font-family="Times New Roman, serif" font-size="12" fill="#222">7. EARLY EXIT FEE: USD 25,000 (non-negotiable)</text>
  <text x="20" y="448" font-family="Times New Roman, serif" font-size="11" fill="#888">Signed: ___________________  Date: ___________</text>
  <text x="180" y="478" text-anchor="middle" font-family="Times New Roman, serif" font-size="10" font-style="italic" fill="#888">[COMPOSITE EXAMPLE — synthetic recruitment contract]</text>
</svg>"""


# -----------------------------------------------------------------------
# 4. Backdated employment contract
# -----------------------------------------------------------------------
BACKDATED_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="360" height="440" viewBox="0 0 360 440">
  <rect x="0" y="0" width="360" height="440" fill="#fefcf6" stroke="#666" stroke-width="1"/>
  <text x="180" y="30" text-anchor="middle" font-family="Times New Roman, serif" font-size="14" font-weight="700" fill="#111">EMPLOYMENT AGREEMENT — DOMESTIC HELPER</text>
  <text x="180" y="48" text-anchor="middle" font-family="Times New Roman, serif" font-size="11" fill="#444">Sponsor: Al-Mahmood Household (composite)  ·  Riyadh, KSA</text>
  <line x1="20" y1="64" x2="340" y2="64" stroke="#666"/>
  <rect x="220" y="80" width="120" height="32" fill="#fff" stroke="#c00" stroke-width="2" rx="4"/>
  <text x="280" y="98" text-anchor="middle" font-family="Times New Roman, serif" font-size="11" font-weight="700" fill="#c00">CONTRACT DATE:</text>
  <text x="280" y="111" text-anchor="middle" font-family="Times New Roman, serif" font-size="14" font-weight="700" fill="#c00">2025-08-15</text>
  <text x="20" y="98" font-family="Times New Roman, serif" font-size="12" fill="#222">Worker arrived: 2026-02-10</text>
  <text x="20" y="116" font-family="Times New Roman, serif" font-size="12" fill="#222">Started actual work: 2026-02-11</text>
  <text x="20" y="148" font-family="Times New Roman, serif" font-size="12" fill="#222">1. NAME: Aisha Bibi (composite)</text>
  <text x="20" y="166" font-family="Times New Roman, serif" font-size="12" fill="#222">2. NATIONALITY: Bangladeshi</text>
  <text x="20" y="184" font-family="Times New Roman, serif" font-size="12" fill="#222">3. PASSPORT: BD-XXXXXXX (composite)</text>
  <text x="20" y="210" font-family="Times New Roman, serif" font-size="12" fill="#222">4. SALARY: SAR 1,200/month  (~ USD 320)</text>
  <text x="20" y="228" font-family="Times New Roman, serif" font-size="12" fill="#222">5. CONTRACT TERM: 2 years from CONTRACT DATE above</text>
  <text x="20" y="246" font-family="Times New Roman, serif" font-size="12" fill="#222">   (i.e. ends 2027-08-14)</text>
  <text x="20" y="278" font-family="Times New Roman, serif" font-size="12" fill="#222">6. END-OF-SERVICE GRATUITY: calculated from CONTRACT</text>
  <text x="20" y="296" font-family="Times New Roman, serif" font-size="12" fill="#222">   DATE per Saudi Labour Law Art. 84 (21 days/year x 1.5 yrs)</text>
  <text x="20" y="328" font-family="Times New Roman, serif" font-size="12" fill="#222">   Note: worker actually started 6 months later than the</text>
  <text x="20" y="346" font-family="Times New Roman, serif" font-size="12" fill="#222">   stated contract date — backdating reduces gratuity</text>
  <text x="20" y="364" font-family="Times New Roman, serif" font-size="12" fill="#222">   by 6 months and shortens probation timeline.</text>
  <text x="20" y="396" font-family="Times New Roman, serif" font-size="11" fill="#666">Worker signature: _________  Sponsor signature: _________</text>
  <text x="180" y="422" text-anchor="middle" font-family="Times New Roman, serif" font-size="10" font-style="italic" fill="#888">[COMPOSITE EXAMPLE — illustrating backdated contract pattern]</text>
</svg>"""


# -----------------------------------------------------------------------
# 5. Two-contract pattern (origin POEA vs destination side-by-side)
# -----------------------------------------------------------------------
TWO_CONTRACT_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="540" height="420" viewBox="0 0 540 420">
  <rect x="0" y="0" width="540" height="420" fill="#fff" stroke="#444" stroke-width="1"/>
  <text x="270" y="28" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="700" fill="#111">SAME WORKER  ·  TWO DIFFERENT CONTRACTS</text>
  <line x1="270" y1="40" x2="270" y2="410" stroke="#888" stroke-dasharray="4,4"/>
  <rect x="14" y="50" width="246" height="350" fill="#f0f9ff" stroke="#3b82f6" stroke-width="1" rx="6"/>
  <text x="138" y="72" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" font-weight="700" fill="#1e40af">POEA-APPROVED (origin side, PH)</text>
  <text x="24" y="98" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Worker: Maria Santos (composite)</text>
  <text x="24" y="118" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Position: Senior Hospitality Staff</text>
  <text x="24" y="138" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Employer: Gulf Resorts International</text>
  <text x="24" y="158" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Destination: Dubai, UAE</text>
  <text x="24" y="178" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Salary: USD 850/month</text>
  <text x="24" y="198" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Hours: 48 hrs/week, 1 day off/week</text>
  <text x="24" y="218" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Term: 2 years</text>
  <text x="24" y="238" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Recruitment fee: ZERO (POEA MC)</text>
  <text x="24" y="258" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Round-trip ticket: employer-paid</text>
  <text x="24" y="278" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Medical insurance: included</text>
  <text x="24" y="298" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Day off: 4 days/month minimum</text>
  <text x="24" y="318" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Passport: worker retains</text>
  <text x="24" y="338" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Termination: 30-day notice</text>
  <text x="24" y="358" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Dispute resolution: NLRC, PH</text>
  <text x="138" y="388" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="10" font-style="italic" fill="#1e40af">stamped POEA, signed pre-departure</text>
  <rect x="280" y="50" width="246" height="350" fill="#fef2f2" stroke="#dc2626" stroke-width="1" rx="6"/>
  <text x="404" y="72" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" font-weight="700" fill="#991b1b">DESTINATION CONTRACT (Dubai)</text>
  <text x="290" y="98" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Worker: Maria Santos (composite)</text>
  <text x="290" y="118" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">Position: Domestic Helper (downgrade)</text>
  <text x="290" y="138" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">Employer: Al-Said Family Household</text>
  <text x="290" y="158" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Destination: Dubai, UAE</text>
  <text x="290" y="178" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">Salary: AED 1,000/mo (~USD 272) ↓</text>
  <text x="290" y="198" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">Hours: "as needed" / 24/7 on call</text>
  <text x="290" y="218" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#222">Term: 2 years</text>
  <text x="290" y="238" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">"Training fee" owed: USD 3,500</text>
  <text x="290" y="258" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">Return ticket: employer holds</text>
  <text x="290" y="278" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">Medical: deducted from salary</text>
  <text x="290" y="298" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">Day off: 1 per month (sponsor's discretion)</text>
  <text x="290" y="318" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">Passport: held by sponsor "for safekeeping"</text>
  <text x="290" y="338" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">Termination: USD 25,000 quit fee</text>
  <text x="290" y="358" font-family="Helvetica, Arial, sans-serif" font-size="11" fill="#dc2626">Dispute resolution: Sharia tribunal, employer's region</text>
  <text x="404" y="388" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="10" font-style="italic" fill="#991b1b">presented at airport on arrival, in Arabic only</text>
</svg>"""


# Map: (id, category, label, content_text, svg)
NEW_ENTRIES = [
    {
        "id": "recruit_tiktok_dubai_caregiver",
        "category": "recruitment_post",
        "label": "TikTok recruitment ad — Dubai caregiver (false-urgency + DM-only)",
        "content": (
            "[COMPOSITE EXAMPLE — TikTok recruitment ad]\n\n"
            "Caption (transcribed from screenshot):\n\n"
            "URGENT 🔥 Filipina caregivers needed in Dubai! "
            "Salary AED 1,500/month + free flight + free visa + "
            "free accommodation. Fly out in 2 weeks!\n\n"
            "Only 3 spots left! Decide TODAY.\n\n"
            "DM us — no public comments allowed.\n\n"
            "#FilipinaOFW #Dubai #UrgentHiring #NoFee #Direct\n\n"
            "Engagement: 12.4K likes · 847 comments · 3.2K shares\n"
            "Account: @DubaiRecruitOPF (composite handle)\n\n"
            "Triggers expected: false_urgency_only_n_spots, "
            "online_platform_recruitment_unverified, "
            "fake_or_unverifiable_recruiter_license (no POEA license "
            "shown), corridor_PH_to_GULF (UAE not on POEA's "
            "zero-fee list — verify worker actually paid the "
            "claimed-zero fee)."
        ),
        "image_data_uri": svg_data_uri(TIKTOK_SVG),
    },
    {
        "id": "recruit_telegram_money_mule",
        "category": "recruitment_post",
        "label": "Telegram money-mule recruiter chat (cross-border fin-flow)",
        "content": (
            "[COMPOSITE EXAMPLE — Telegram money-mule recruitment chat]\n\n"
            "Bot/account: @QuickEarnHub_Bot (composite)\n\n"
            "Bot: Hello! Earn $500-2000 per day working from home — "
            "no skills required. Just receive + forward.\n\n"
            "Bot: You receive payments to your bank. Forward 90%, "
            "keep 10%.\n\n"
            "User: What kind of money is it? Is this legal?\n\n"
            "Bot: Don't ask questions, just follow our SOP. Open new "
            "account at 3 banks for splitting (under $10,000 each "
            "transfer).\n\n"
            "User: I'm a Filipina student. Can I do this?\n\n"
            "Bot: Perfect for students! No risk to you — sign here, "
            "we handle the paperwork. Send your bank info.\n\n"
            "Triggers expected: money_mule_recruitment_pattern, "
            "structured_deposits_smurfing, "
            "online_platform_recruitment_unverified, "
            "abuse_of_vulnerability (targets students)."
        ),
        "image_data_uri": svg_data_uri(TELEGRAM_SVG),
    },
    {
        "id": "doc_camstudio_contract",
        "category": "document_contract",
        "label": "Cam-studio onboarding contract (sextortion entry pattern)",
        "content": (
            "[COMPOSITE EXAMPLE — synthetic cam-studio contract]\n\n"
            "CONTENT CREATOR AGREEMENT\n"
            "Studio Astra Live (composite) · Prague, CZ branch\n\n"
            "1. CREATOR (composite name): Lina Petrova\n"
            "2. PASSPORT: held by STUDIO during contract period (24 mo) "
            "for 'safekeeping' per Section 7.3\n"
            "3. ADVANCE PAID: USD 12,000 to cover\n"
            "     - Visa fees                  $3,500\n"
            "     - Travel + housing deposit   $4,500\n"
            "     - Equipment + lighting       $2,500\n"
            "     - Training + content prep    $1,500\n"
            "4. REPAYMENT: 70% of streaming revenue retained by "
            "STUDIO until USD 12,000 + 24% interest is recovered.\n"
            "5. CONTENT QUOTAS: 8 hours/day live, 6 days/week. "
            "Failure to meet quota: USD 200/missed-day deducted "
            "from advance.\n"
            "6. NON-COMPETE: Creator shall not stream on any platform "
            "outside STUDIO control during AND for 24 months after "
            "contract termination.\n"
            "7. EARLY EXIT FEE: USD 25,000 (non-negotiable)\n\n"
            "Triggers expected: sextortion_camgirl_studio_recruitment, "
            "passport_safekeeping_consent_form, "
            "ilo_indicator_passport_retention, "
            "debt_bondage_loan_salary_deduction (advance + revenue "
            "retention pattern), quit_fee_breaking_contract_penalty."
        ),
        "image_data_uri": svg_data_uri(CAM_CONTRACT_SVG),
    },
    {
        "id": "doc_backdated_contract",
        "category": "document_contract",
        "label": "Backdated employment contract (gratuity-evasion pattern)",
        "content": (
            "[COMPOSITE EXAMPLE — synthetic backdated employment contract]\n\n"
            "EMPLOYMENT AGREEMENT — DOMESTIC HELPER\n"
            "Sponsor: Al-Mahmood Household (composite) · Riyadh, KSA\n\n"
            "CONTRACT DATE: 2025-08-15  ←  flagged red\n"
            "Worker arrived: 2026-02-10\n"
            "Started actual work: 2026-02-11\n\n"
            "1. NAME: Aisha Bibi (composite)\n"
            "2. NATIONALITY: Bangladeshi\n"
            "3. PASSPORT: BD-XXXXXXX (composite)\n"
            "4. SALARY: SAR 1,200/month (~ USD 320)\n"
            "5. CONTRACT TERM: 2 years from CONTRACT DATE above "
            "(i.e. ends 2027-08-14)\n"
            "6. END-OF-SERVICE GRATUITY: calculated from CONTRACT "
            "DATE per Saudi Labour Law Art. 84 (21 days/year × 1.5 yrs)\n\n"
            "Worker actually started 6 months LATER than the stated "
            "contract date — backdating reduces gratuity by ~6 "
            "months and shortens the probation timeline.\n\n"
            "Triggers expected: backdated_employment_contract, "
            "month_to_month_visa_evading_gratuity (variant: "
            "back-date variant of the same gratuity-evasion family), "
            "two_contract_pattern_origin_vs_destination (if origin "
            "had a different start date)."
        ),
        "image_data_uri": svg_data_uri(BACKDATED_SVG),
    },
    {
        "id": "doc_two_contract_side_by_side",
        "category": "document_contract",
        "label": "Two-contract pattern: POEA origin vs Dubai destination",
        "content": (
            "[COMPOSITE EXAMPLE — two-contract pattern, POEA origin "
            "vs Dubai destination, side-by-side]\n\n"
            "POEA-APPROVED (origin side, PH):\n"
            "  Worker:        Maria Santos (composite)\n"
            "  Position:      Senior Hospitality Staff\n"
            "  Employer:      Gulf Resorts International\n"
            "  Destination:   Dubai, UAE\n"
            "  Salary:        USD 850/month\n"
            "  Hours:         48 hrs/week, 1 day off/week\n"
            "  Term:          2 years\n"
            "  Recruitment fee: ZERO (POEA MC)\n"
            "  Round-trip ticket: employer-paid\n"
            "  Medical insurance: included\n"
            "  Day off:       4 days/month minimum\n"
            "  Passport:      worker retains\n"
            "  Termination:   30-day notice\n"
            "  Dispute resolution: NLRC, Philippines\n"
            "  Stamped POEA, signed pre-departure.\n\n"
            "DESTINATION CONTRACT (Dubai, presented on arrival, in "
            "Arabic only):\n"
            "  Worker:        Maria Santos (composite)\n"
            "  Position:      Domestic Helper  ← DOWNGRADE\n"
            "  Employer:      Al-Said Family Household  ← DIFFERENT\n"
            "  Destination:   Dubai, UAE\n"
            "  Salary:        AED 1,000/mo (~USD 272)  ← 68% LOWER\n"
            "  Hours:         'as needed' / 24/7 on call\n"
            "  Term:          2 years\n"
            "  'Training fee' owed: USD 3,500  ← NEW DEBT\n"
            "  Return ticket: employer holds\n"
            "  Medical:       deducted from salary\n"
            "  Day off:       1 per month (sponsor's discretion)\n"
            "  Passport:      held by sponsor 'for safekeeping'\n"
            "  Termination:   USD 25,000 quit fee\n"
            "  Dispute resolution: Sharia tribunal, employer's region\n\n"
            "Triggers expected: two_contract_pattern_origin_vs_"
            "destination, contract_substitution_at_airport, "
            "bait_and_switch_destination, "
            "retroactive_training_fee_at_destination, "
            "passport_safekeeping_consent_form, "
            "return_ticket_held_by_employer, "
            "quit_fee_breaking_contract_penalty, "
            "sharia_tribunal_selection_strip, no_day_off_chronic, "
            "elder_care_24_7_on_call (24/7 on-call variant)."
        ),
        "image_data_uri": svg_data_uri(TWO_CONTRACT_SVG),
    },
]


def main() -> int:
    existing = json.load(open(TARGET, encoding="utf-8"))
    existing_ids = {e["id"] for e in existing}
    added = 0
    for entry in NEW_ENTRIES:
        if entry["id"] in existing_ids:
            print(f"SKIP existing id: {entry['id']}")
            continue
        existing.append(entry)
        added += 1
        print(f"ADDED {entry['id']} — {entry['label']}")
    if added:
        with open(TARGET, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        print(f"\nWrote {len(existing)} total entries (was {len(existing) - added}).")
    else:
        print("No new entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
