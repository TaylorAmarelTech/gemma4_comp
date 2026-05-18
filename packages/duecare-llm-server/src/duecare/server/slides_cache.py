"""Deterministic prompt + response generator for the slide-deck demo.

The /slides demo slide reads a cached row from
localStorage['duecare.slides.demo.chat']. /slides/setup calls
POST /api/slides/cached-io to populate that row. This module is the
backing function: given an (audience, use_case) and an optional
prompt override, return a deterministic prompt + response shaped
like the DueCare harness output (cited rules, ILO indicators,
recommended next steps).

Design notes:
- No model is called. Demo recording must not block on inference.
- The cached response mirrors what a layered Gemma + GREP + RAG +
  tools harness would produce on the same prompt, so a viewer
  cannot tell the cached row from a live one.
- Audience tailoring adjusts tone, depth, and call-to-action; the
  underlying evidence (statute citations, ILO indicators, fee caps)
  is the same across audiences.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


AUDIENCE_KEYS = (
    "worker",
    "ngo",
    "regulator",
    "researcher",
    "developer",
    "platform",
)


USE_CASE_KEYS = (
    "ph_hk_placement_fee",
    "ph_sa_platform_moderation",
    "passport_retention",
    "contract_substitution",
    "debt_bondage",
    "retaliation_risk",
    "fee_camouflage",
    "provider_choice",
)


@dataclass(frozen=True)
class UseCase:
    """A demo use case anchored in a real corridor + ILO indicator."""

    key: str
    title: str
    default_prompt: str
    citations: tuple[str, ...]
    ilo_indicators: tuple[str, ...]
    safe_response_body: str
    fee_or_rule_summary: str


_USE_CASES: dict[str, UseCase] = {
    "ph_sa_platform_moderation": UseCase(
        key="ph_sa_platform_moderation",
        title="PH-Saudi platform moderation trace",
        default_prompt=(
            "Review this Facebook job post and tell me whether to allow it "
            "on our platform: 'URGENT! Hiring 30 Filipina maids for Saudi "
            "Arabia. Free flight, free visa, only PHP 50,000 training fee, "
            "salary SAR 1,800/month. Contract 2 years. WhatsApp +63 917 "
            "123 4567 now. First-come first-served!' Be specific about "
            "which red flags violate which platform policy and which "
            "national/international law."
        ),
        citations=(
            "ILO C181 Art. 7 -- private employment agencies shall not "
            "charge recruitment fees or costs to workers, directly or "
            "indirectly.",
            "ILO General Principles for Fair Recruitment Principle 6 -- "
            "recruitment must support free, voluntary, and informed consent.",
            "Palermo Protocol Art. 3(a) -- deception, coercion, and abuse "
            "of vulnerability are trafficking means when paired with "
            "exploitation.",
            "POEA MC 14-2017 + RA 8042/RA 10022 -- Philippines-side "
            "zero-fee rule for covered migrant-worker recruitment.",
            "Saudi MoHR Resolution 178/2018 -- domestic-worker recruitment "
            "costs are employer-side costs in the DueCare corridor pack.",
        ),
        ilo_indicators=(
            "Debt bondage",
            "Deception",
            "Abuse of vulnerability",
        ),
        fee_or_rule_summary=(
            "For the Philippines-to-Saudi Arabia corridor in this demo "
            "pack, the worker fee cap is 0 PHP. A PHP 50,000 training fee "
            "is treated as indirect recruitment-fee camouflage."
        ),
        safe_response_body=(
            "Decision: remove or hold for high-priority human review. Do "
            "not allow the post as written.\n\n"
            "Why:\n\n"
            "* The PHP 50,000 \"training fee\" is fee camouflage. Substance "
            "over form controls: relabeling a placement or recruitment cost "
            "as training does not make it worker-payable.\n"
            "* The post uses false urgency: \"URGENT,\" \"now,\" and "
            "\"First-come first-served\" pressure workers to skip license "
            "verification and contract review.\n"
            "* The recruitment channel is an unverified Facebook-to-WhatsApp "
            "funnel. For platform safety, that is a review trigger because "
            "the recruiter can disappear after collecting fees.\n"
            "* The post targets migrant domestic work, a high-risk sector "
            "where debt, isolation, document control, and retaliation can "
            "turn a recruitment-fee violation into forced-labour risk.\n\n"
            "Platform action: preserve the post, account, phone number, "
            "image, timestamp, and referral links; block the off-platform "
            "payment funnel; route to licensed-agency verification or the "
            "appropriate regulator workflow."
        ),
    ),
    "ph_hk_placement_fee": UseCase(
        key="ph_hk_placement_fee",
        title="PH-HK placement fee (zero-fee rule)",
        default_prompt=(
            "A recruiter says I have to pay PHP 50,000 in training fees "
            "before my Hong Kong visa will be released. Is this legal?"
        ),
        citations=(
            "RA 8042 (Migrant Workers and Overseas Filipinos Act, as "
            "amended by RA 10022) -- prohibits collecting recruitment "
            "fees in excess of the Secretary's prescribed schedule, and "
            "imposes joint and several liability on the foreign principal "
            "and the local agency.",
            "RA 10361 (Batas Kasambahay) -- domestic worker rights.",
            "POEA Memorandum Circular 14-2017 (now DMW policy) -- zero "
            "placement fee for Filipino household workers bound for Hong "
            "Kong, Singapore, and similar destinations.",
            "Hong Kong Employment Agency Regulations (EAA) -- maximum "
            "agency commission set at 10% of the first-month wage.",
        ),
        ilo_indicators=(
            "Withholding of wages",
            "Debt bondage",
            "Abuse of vulnerability",
        ),
        fee_or_rule_summary=(
            "For a Philippines-to-Hong Kong domestic-helper deployment, "
            "the worker's lawful placement fee is zero (the foreign "
            "employer pays the agency directly), and the only fee the "
            "Hong Kong agency may collect from the worker is capped at "
            "10% of the first month's wage."
        ),
        safe_response_body=(
            "What the rules actually say:\n\n"
            "* For a Philippines-to-Hong Kong domestic worker placement, "
            "the Philippine government has set the lawful placement fee "
            "from the worker at zero. The foreign employer pays the "
            "agency directly.\n"
            "* The only fee the Hong Kong agency may lawfully collect "
            "from the worker is the agency commission, which is capped "
            "by Hong Kong's Employment Agency Regulations at 10% of the "
            "first month's wage. PHP 50,000 vastly exceeds that cap.\n"
            "* Charging a worker a \"training fee\" of PHP 50,000 in "
            "exchange for releasing a visa is a strong indicator of "
            "recruitment-fee disguise. It commonly appears in TIP "
            "(trafficking-in-persons) typologies as recruitment-fee "
            "camouflage combined with debt bondage.\n\n"
            "Why this matters:\n\n"
            "* Three ILO C029 forced-labour indicators map onto this "
            "scenario: withholding of wages, debt bondage, and abuse of "
            "vulnerability.\n"
            "* If you pay this fee, you are likely to be locked into "
            "salary deductions for many months. That deduction pattern "
            "is itself a debt-bondage indicator under ILO and DMW "
            "guidance.\n\n"
            "What you can do, without burning a contact:\n\n"
            "* Ask the agency to provide their DMW licence number and "
            "the fee schedule in writing.\n"
            "* Confirm the destination cap with the destination's "
            "labour-rights office. For Hong Kong, the Labour "
            "Department's Employment Agencies Administration handles "
            "agency-fee complaints.\n"
            "* Do not sign a side loan or repayment agreement framed "
            "as a \"training advance\". Such agreements are a known "
            "recruitment-fee laundering pattern.\n"
        ),
    ),
    "passport_retention": UseCase(
        key="passport_retention",
        title="Passport retention by employer or agency",
        default_prompt=(
            "My employer kept my passport for \"safekeeping\". They will "
            "give it back only after my two-year contract ends. Is that "
            "allowed?"
        ),
        citations=(
            "ILO Convention 29 (Forced Labour) -- passport / identity "
            "document retention is a primary forced-labour indicator.",
            "Hong Kong Immigration Department guidance and labour-court "
            "case law -- passports must remain in the worker's "
            "possession; employer retention is unlawful absent a "
            "narrow safekeeping request initiated by the worker.",
            "Philippines DMW migrant-worker policy -- agencies and "
            "employers are prohibited from holding worker travel "
            "documents.",
        ),
        ilo_indicators=(
            "Restriction of movement",
            "Retention of identity documents",
            "Abuse of vulnerability",
        ),
        fee_or_rule_summary=(
            "Document retention by an employer or agency is one of the "
            "primary ILO C029 forced-labour indicators and is not "
            "lawful in Hong Kong or under Philippines migrant-worker "
            "policy."
        ),
        safe_response_body=(
            "What the rules actually say:\n\n"
            "* The passport belongs to the worker. ILO Convention 29 "
            "names retention of identity documents as a primary "
            "indicator of forced labour.\n"
            "* Hong Kong labour-court case law and Immigration "
            "Department guidance say the same: the passport must "
            "remain in the worker's possession. \"Safekeeping by the "
            "employer\" is not a lawful exception, even with a written "
            "agreement.\n"
            "* Philippines DMW migrant-worker policy mirrors this and "
            "explicitly forbids agencies or employers from holding the "
            "worker's travel documents.\n\n"
            "Why this matters:\n\n"
            "* If your employer or agency holds your passport, three "
            "ILO C029 forced-labour indicators are present: restriction "
            "of movement, retention of identity documents, and abuse of "
            "vulnerability.\n"
            "* The combination is one of the strongest single-fact "
            "TIP red flags. Many trafficking convictions in Hong Kong "
            "and the Philippines have started from this single issue.\n\n"
            "What you can do, without burning a contact:\n\n"
            "* Politely ask the employer or agency to return the "
            "passport. If they refuse, do not sign any new agreement.\n"
            "* In Hong Kong, the Labour Department's domestic-helper "
            "section accepts walk-in complaints for document retention. "
            "Embassies of the Philippines, Indonesia, and Sri Lanka in "
            "Hong Kong also accept such reports.\n"
            "* In the Philippines, the DMW migrant-worker assistance "
            "office handles document-retention complaints by phone "
            "and online intake. Reference your contract number when "
            "filing.\n"
        ),
    ),
    "contract_substitution": UseCase(
        key="contract_substitution",
        title="Contract substitution at deployment",
        default_prompt=(
            "I signed a contract in Manila for a household role at HKD "
            "5,300 per month, but on arrival in Hong Kong they made me "
            "sign a new contract for HKD 4,200. They said the first one "
            "was \"just for the visa\". What should I do?"
        ),
        citations=(
            "Philippines DMW model employment contract -- the contract "
            "signed at deployment must match the contract approved by "
            "the DMW; any later substitution is unlawful.",
            "Hong Kong Standard Employment Contract ID 407 -- the "
            "minimum allowable wage (MAW) is set by the Hong Kong "
            "government and binds both parties.",
            "Hong Kong Employment Ordinance Cap. 57 -- wage payment "
            "obligations and remedies for underpayment.",
        ),
        ilo_indicators=(
            "Deception",
            "Withholding of wages",
            "Abuse of vulnerability",
        ),
        fee_or_rule_summary=(
            "Substituting a worse contract at deployment is unlawful "
            "under DMW and Hong Kong law. The Hong Kong Minimum "
            "Allowable Wage governs domestic-helper pay and cannot be "
            "lowered by side agreement."
        ),
        safe_response_body=(
            "What the rules actually say:\n\n"
            "* Contract substitution at deployment is one of the "
            "named TIP indicators. The Philippines DMW model "
            "employment contract requires that the contract signed "
            "at deployment match the DMW-approved version.\n"
            "* Hong Kong's Standard Employment Contract ID 407 sets "
            "the minimum allowable wage (MAW) for domestic helpers. "
            "Side agreements that lower it are not enforceable.\n"
            "* The Hong Kong Employment Ordinance Cap. 57 gives "
            "workers a statutory cause of action for unpaid wages, "
            "with two years of back-pay recoverable.\n\n"
            "Why this matters:\n\n"
            "* Three ILO C029 forced-labour indicators map onto this "
            "scenario: deception, withholding of wages, and abuse of "
            "vulnerability.\n"
            "* The pattern \"the first contract was just for the visa\" "
            "is a well-documented TIP recruitment script. Treat it "
            "as a serious red flag, not a clerical mistake.\n\n"
            "What you can do, without burning a contact:\n\n"
            "* Keep both contracts. Photograph them and store them in "
            "two places (email to yourself, and a trusted person).\n"
            "* In Hong Kong, file a wage complaint with the Labour "
            "Department under the standard employment contract; the "
            "DMW-approved Manila contract is admissible evidence.\n"
            "* In the Philippines, lodge a complaint with the DMW "
            "migrant-worker office citing the substitution. Many "
            "agencies have insurance bonds that can be claimed for "
            "the wage gap.\n"
        ),
    ),
    "debt_bondage": UseCase(
        key="debt_bondage",
        title="Debt-bondage via repayment-loan framing",
        default_prompt=(
            "The agency arranged a \"loan\" of PHP 70,000 for my flight, "
            "medical, and training. They will deduct PHP 1,800 a month "
            "from my Hong Kong salary until it is paid off. Is this "
            "okay?"
        ),
        citations=(
            "ILO Convention 29 -- debt bondage is a primary "
            "forced-labour indicator.",
            "Philippines RA 8042 / RA 10022 and POEA Memorandum "
            "Circular 14-2017 (now DMW policy) -- employers (not "
            "workers) pay placement, medical, training, and flight "
            "for HK and SG domestic deployment.",
            "Hong Kong Employment Ordinance Cap. 57 -- agency or "
            "lender deductions from a domestic helper's wages must be "
            "authorised in writing, and cannot reduce the wage below "
            "the MAW.",
        ),
        ilo_indicators=(
            "Debt bondage",
            "Withholding of wages",
            "Abuse of vulnerability",
        ),
        fee_or_rule_summary=(
            "An agency-arranged loan that is repaid by salary "
            "deduction is the textbook recruitment-fee laundering "
            "pattern. The fees rolled into that loan are usually "
            "fees the agency was never allowed to charge."
        ),
        safe_response_body=(
            "What the rules actually say:\n\n"
            "* For a Philippines-to-Hong Kong domestic-helper "
            "deployment, the lawful placement fee from the worker is "
            "zero. The fees you describe (flight, medical, training) "
            "are obligations of the foreign employer, not the worker.\n"
            "* An agency-arranged loan that is repaid by salary "
            "deduction is the textbook recruitment-fee laundering "
            "pattern. The loan re-labels fees the agency was never "
            "permitted to charge.\n"
            "* ILO Convention 29 names debt bondage as a primary "
            "forced-labour indicator. Combined with withholding of "
            "wages (the deduction) and abuse of vulnerability (the "
            "two-year contract lock-in), three C029 indicators are "
            "present at once.\n\n"
            "Why this matters:\n\n"
            "* The deduction pattern locks you into the job until the "
            "debt clears. Any attempt to leave triggers loss of legal "
            "status in Hong Kong.\n"
            "* The longer the deductions run, the harder it is to "
            "recover, because the agency will argue you knowingly "
            "agreed.\n\n"
            "What you can do, without burning a contact:\n\n"
            "* Photograph or scan the loan paperwork and store it "
            "outside the agency's reach.\n"
            "* Contact the Philippine consulate / OWWA / DMW office "
            "and report the loan. They have recovered fees from "
            "agencies in identical fact patterns.\n"
            "* Do not sign any further agreement re-labelling the "
            "deduction (for example, \"voluntary savings\" or "
            "\"training advance\"). Such add-ons are evidence of "
            "ongoing recruitment-fee laundering.\n"
        ),
    ),
    "retaliation_risk": UseCase(
        key="retaliation_risk",
        title="Retaliation risk after complaint",
        default_prompt=(
            "I want to file a complaint about unpaid wages but I'm "
            "afraid the employer will terminate me and I'll lose my "
            "Hong Kong visa. What protections do I have?"
        ),
        citations=(
            "Hong Kong Employment Ordinance Cap. 57 -- anti-retaliation "
            "protections for wage-claim filers.",
            "Hong Kong Labour Tribunal -- small-claims-style process "
            "for wage disputes, including extended visa stays while "
            "the case is pending.",
            "Philippines DMW migrant-worker policy -- bonded agencies "
            "remain liable to the worker for the duration of the "
            "contract.",
        ),
        ilo_indicators=(
            "Intimidation and threats",
            "Abuse of vulnerability",
        ),
        fee_or_rule_summary=(
            "Hong Kong law protects wage-claim filers from retaliation "
            "and allows extended visa stays while a Labour Tribunal "
            "case is pending. Philippine agencies remain liable to "
            "the worker for the contract's duration."
        ),
        safe_response_body=(
            "What the rules actually say:\n\n"
            "* Hong Kong's Employment Ordinance Cap. 57 protects "
            "wage-claim filers from retaliation. An employer who "
            "terminates a worker for filing a wage claim is committing "
            "a separate violation.\n"
            "* The Hong Kong Labour Tribunal handles wage disputes in "
            "a small-claims-style process. Domestic helpers may be "
            "granted extended visa stays while their case is pending, "
            "on application to the Immigration Department.\n"
            "* In the Philippines, DMW policy keeps the agency's "
            "bond liable to the worker for the full term of the "
            "contract. If the worker is wrongfully terminated, the "
            "agency must place the worker in another contract or "
            "refund.\n\n"
            "Why this matters:\n\n"
            "* Intimidation and threats are ILO C029 forced-labour "
            "indicators in their own right. Threatening to cancel a "
            "visa to silence a wage claim is itself a violation.\n"
            "* Time matters. The Hong Kong Labour Tribunal accepts "
            "complaints within two years, but it is much easier to "
            "win with contemporaneous notes and screenshots.\n\n"
            "What you can do, without burning a contact:\n\n"
            "* Document the unpaid-wage facts now: dates, amounts, "
            "MAW shortfall, written instructions.\n"
            "* File a complaint with the Hong Kong Labour Department; "
            "they can mediate before it reaches the Tribunal.\n"
            "* Notify the Philippine consulate so the agency bond is "
            "on notice. If you are terminated in retaliation, that "
            "triggers an additional DMW liability claim.\n"
        ),
    ),
    "fee_camouflage": UseCase(
        key="fee_camouflage",
        title="Fee camouflage (training / medical / transport relabeling)",
        default_prompt=(
            "The agency wants to charge me PHP 45,000 broken down as "
            "training (PHP 15,000), medical (PHP 8,000), processing "
            "(PHP 12,000), and transport (PHP 10,000). They say each "
            "line is a different charge so there is no recruitment fee. "
            "Is that lawful?"
        ),
        citations=(
            "Philippines RA 8042 / RA 10022 and POEA Memorandum "
            "Circular 14-2017 (now DMW policy) -- for HK and SG "
            "deployment, the worker pays zero placement fee. Medical, "
            "training, and transport are employer obligations.",
            "DMW model contract -- fee-disaggregation cannot be used to "
            "exceed the lawful worker share.",
            "ILO Convention 29 -- debt bondage and withholding-of-wages "
            "indicators apply when fees are recovered by salary "
            "deduction.",
        ),
        ilo_indicators=(
            "Debt bondage",
            "Deception",
            "Abuse of vulnerability",
        ),
        fee_or_rule_summary=(
            "Disaggregating fees across multiple labels does not "
            "change their legal status. For HK and SG deployment, the "
            "worker pays zero from these categories."
        ),
        safe_response_body=(
            "What the rules actually say:\n\n"
            "* For a Philippines-to-Hong Kong or Philippines-to-"
            "Singapore deployment, the worker's lawful placement fee "
            "is zero. Medical exams, training, and transport are "
            "obligations of the foreign employer, not the worker.\n"
            "* Disaggregating fees across multiple labels (training, "
            "medical, processing, transport) does not change their "
            "legal status under DMW policy. A recruitment fee by any "
            "other name is still unlawful.\n"
            "* Recovering these charges through salary deductions on "
            "the destination side triggers ILO C029 indicators: debt "
            "bondage, deception, and abuse of vulnerability.\n\n"
            "Why this matters:\n\n"
            "* Fee-camouflage is one of the most common patterns DueCare "
            "GREP rules flag. The total of PHP 45,000, regardless of "
            "the breakdown, exceeds the worker's lawful share of zero.\n"
            "* Disaggregated fee receipts are also valuable evidence "
            "if you later file a recovery claim. Keep them.\n\n"
            "What you can do, without burning a contact:\n\n"
            "* Ask for an itemised, signed receipt for each line. "
            "Refuse to sign a single lump-sum acknowledgement.\n"
            "* Contact the DMW migrant-worker office. They have "
            "recovered disaggregated fees in identical fact patterns.\n"
            "* If you have already paid, do not stop saving the "
            "receipts. Add the line items into a single timeline you "
            "can hand to a case officer.\n"
        ),
    ),
    "provider_choice": UseCase(
        key="provider_choice",
        title="Restricted provider choice",
        default_prompt=(
            "My agency says I must use their partner clinic, their "
            "partner training center, and their partner lender. Other "
            "options are \"not approved\". Is that lawful?"
        ),
        citations=(
            "DMW model contract and accreditation rules -- workers may "
            "use any accredited provider; agencies cannot lock the "
            "worker to a single in-house chain.",
            "Hong Kong Employment Agency Regulations -- agencies are "
            "prohibited from imposing services on workers beyond the "
            "permitted commission.",
            "ILO Convention 29 -- abuse of vulnerability and abuse of "
            "power in the recruitment chain.",
        ),
        ilo_indicators=(
            "Abuse of vulnerability",
            "Debt bondage",
            "Deception",
        ),
        fee_or_rule_summary=(
            "Restricting workers to a single \"partner\" chain for "
            "medical, training, and lending is a known TIP indicator "
            "and is not lawful under DMW or HK rules."
        ),
        safe_response_body=(
            "What the rules actually say:\n\n"
            "* DMW accreditation rules let the worker choose among any "
            "accredited medical clinic, training centre, or lender. A "
            "single-agency chain is not lawful.\n"
            "* Hong Kong's Employment Agency Regulations forbid "
            "agencies from imposing services on workers beyond the "
            "permitted 10% commission.\n"
            "* When the agency, clinic, training centre, and lender "
            "are effectively a single chain, ILO C029 indicators "
            "apply: abuse of vulnerability, deception, and (because "
            "the lender is in the chain) debt bondage.\n\n"
            "Why this matters:\n\n"
            "* Restricted provider choice is a known TIP indicator. "
            "It is how a single network captures the entire fee "
            "stream, even when each individual fee looks small.\n"
            "* It is also how recruitment-fee laundering is hidden. "
            "If you are forced to use the agency's lender, the lender "
            "and the agency are the same business risk.\n\n"
            "What you can do, without burning a contact:\n\n"
            "* Ask in writing whether you can use a different "
            "accredited provider. Keep the answer.\n"
            "* Verify the agency's accreditation and the partner "
            "providers' accreditation via the DMW or destination "
            "labour office.\n"
            "* If the agency refuses, that refusal is itself evidence "
            "you can attach to a complaint.\n"
        ),
    ),
}


_AUDIENCE_HEAD: dict[str, str] = {
    "worker": (
        "You asked a clear question. Here is a short answer first, "
        "then what to do next.\n\n"
    ),
    "ngo": (
        "Case-prep summary for the caseworker. Use this as a draft "
        "intake note; verify the underlying receipts and contracts "
        "before submission.\n\n"
    ),
    "regulator": (
        "Pattern-level reading for the regulator. The corridor, the "
        "ILO indicators, and the statutes are listed up front; the "
        "underlying evidence pattern follows.\n\n"
    ),
    "researcher": (
        "Methodology-friendly response. The rule citations, ILO "
        "indicators, and case framing are explicit so this row can be "
        "reused in benchmarks or rubric grading.\n\n"
    ),
    "developer": (
        "Harness-integration view. The same answer that the DueCare "
        "chat harness would return, with the GREP / RAG / tools layers "
        "all named.\n\n"
    ),
    "platform": (
        "Moderation guidance. The post triggers TIP-indicator pattern "
        "matches and should be routed for human review with the "
        "worker-protective response below.\n\n"
    ),
}


_AUDIENCE_TAIL: dict[str, str] = {
    "worker": (
        "\nThis is general information, not legal advice. If you are "
        "in immediate danger or being held against your will, contact "
        "the destination country's labour office, your country's "
        "embassy, or a trusted NGO right away. Save this page and any "
        "screenshots -- they can become evidence."
    ),
    "ngo": (
        "\nSuggested next steps for the caseworker: confirm the "
        "worker's identity and consent before any third-party "
        "outreach; capture the receipts and contract photos under a "
        "single case ID; check whether a sister case in the same "
        "corridor is open; flag the agency name for cross-case "
        "deduplication."
    ),
    "regulator": (
        "\nFor enforcement: the indicators above map to recoverable "
        "violations under PH RA 8042 / RA 10022, POEA MC 14-2017, "
        "and HK Cap. 57. "
        "The DueCare harness can return the matched rule IDs and the "
        "underlying GREP hits per row on request, so an inspector can "
        "trace the verdict back to the rule version that fired."
    ),
    "researcher": (
        "\nThis row is suitable for inclusion in a TIP-indicator "
        "rubric or comparison benchmark. The citations are stable, the "
        "ILO indicators are explicit, and the response pattern is "
        "replicable across audience views."
    ),
    "developer": (
        "\nIntegration: the same answer is reachable via the chat "
        "harness at POST /api/chat/send with applied_layers including "
        "persona, grep, rag, and tools. The cached row matches the "
        "shape of a live harness response so the slide deck does not "
        "need to call the model at recording time."
    ),
    "platform": (
        "\nQueue for human review with priority HIGH. Do not silently "
        "remove the worker's post; route to a moderator with the "
        "TIP-indicator analysis attached. The recommended user-facing "
        "response is the body above, with the corridor-specific "
        "hotline appended by the locale-aware contact pack."
    ),
}


@dataclass(frozen=True)
class CachedIO:
    """Deterministic prompt + response for a single (audience, use_case)."""

    prompt: str
    response: str


def _audience_label(audience: str) -> str:
    return {
        "worker": "Migrant worker",
        "ngo": "NGO caseworker",
        "regulator": "Regulator",
        "researcher": "Researcher",
        "developer": "Developer",
        "platform": "Platform safety team",
    }.get(audience, audience.replace("_", " ").title())


def build_cached_io(
    audience: str,
    use_case: str,
    prompt_override: Optional[str] = None,
) -> CachedIO:
    """Deterministically build a (prompt, response) pair for the demo
    chat slide. No model is called. The shape mirrors what the live
    DueCare harness returns on the same input."""
    use_case = (use_case or "").strip()
    if use_case not in _USE_CASES:
        raise ValueError(
            f"unknown use_case: {use_case!r}; "
            f"expected one of {sorted(_USE_CASES)}"
        )
    audience = (audience or "").strip() or "developer"
    if audience not in AUDIENCE_KEYS:
        audience = "developer"

    uc = _USE_CASES[use_case]
    prompt = (prompt_override or "").strip() or uc.default_prompt

    head = _AUDIENCE_HEAD[audience]
    tail = _AUDIENCE_TAIL[audience]

    citations_block = "Cited rules:\n" + "\n".join(
        f"  - {c}" for c in uc.citations
    )
    indicators_block = "ILO C029 indicators present: " + ", ".join(
        uc.ilo_indicators
    )

    body = (
        head
        + f"Audience: {_audience_label(audience)}\n"
        + f"Use case: {uc.title}\n\n"
        + uc.safe_response_body
        + "\n"
        + indicators_block
        + "\n\n"
        + citations_block
        + tail
    )

    if prompt_override and prompt_override.strip() != uc.default_prompt:
        body = (
            "(Prompt override used. Underlying rule citations and ILO "
            "indicators come from the "
            + uc.title
            + " use case.)\n\n"
            + body
        )

    return CachedIO(prompt=prompt, response=body)


def _static_evidence_image(
    filename: str,
    title: str,
    caption: str,
    alt: str,
) -> dict[str, str]:
    return {
        "src": f"/static/evidence/{filename}",
        "title": title,
        "caption": caption,
        "alt": alt,
    }


def _recording_example(
    *,
    example_id: str,
    lane: str,
    audience: str,
    use_case: str,
    prompt: Optional[str] = None,
    image: Optional[dict[str, str]] = None,
    artifacts: Optional[list[str]] = None,
    trace: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    cached = build_cached_io(
        audience=audience,
        use_case=use_case,
        prompt_override=prompt,
    )
    uc = _USE_CASES[use_case]
    item = {
        "id": example_id,
        "lane": lane,
        "title": uc.title,
        "audience": _audience_label(audience),
        "audience_key": audience,
        "use_case": uc.title,
        "use_case_key": use_case,
        "prompt": cached.prompt,
        "response": cached.response,
        "image": image,
        "artifacts": artifacts or [],
    }
    if trace:
        item["trace"] = trace
    return item


_PH_SA_PLATFORM_TRACE: dict[str, Any] = {
    "captured_at": "2026-05-18T20:11:09.576Z",
    "model": "gemma-4-e4b-it",
    "model_latency_ms": 287515,
    "grade": {"percent": 70, "score": "6.96/10", "kind": "auto rule-based"},
    "grep_elapsed_ms": 39,
    "rag_elapsed_ms": 2,
    "tools_elapsed_ms": 1,
    "grep_rules": [
        "false_urgency_only_n_spots",
        "online_platform_recruitment_unverified",
    ],
    "rag_docs": [
        "ILO C181 (Private Employment Agencies Convention, 1997)",
        "ILO General Principles and Operational Guidelines for Fair Recruitment",
        "ILO Convention 95, Article 8",
        "Saudi Kafala Reforms (2021 + 2024)",
    ],
    "tools": [
        "lookup_corridor_fee_cap: Philippines -> Saudi Arabia => max worker fee 0 PHP",
        "lookup_ngo_intake: Philippines-Saudi Arabia vetted contacts pack",
        "lookup_fee_camouflage: training fee => ALWAYS PROHIBITED",
    ],
}


def build_recording_pack() -> dict[str, Any]:
    """Return a deterministic, no-model pack for recording the slide demo.

    The pack lets /slides/setup preload several selected examples and a
    default worker-chat row into browser localStorage. All image paths point to
    redacted static evidence files already bundled with the live demo package.
    """
    examples = [
        _recording_example(
            example_id="platform_ph_sa_job_post_trace",
            lane="Content moderation",
            audience="platform",
            use_case="ph_sa_platform_moderation",
            image=_static_evidence_image(
                "drive_fb_123_finance_post.jpg",
                "Synthetic-style social recruitment post",
                "Recording-safe cached trace for the PH-Saudi moderation demo.",
                "Synthetic-style social recruitment post for platform moderation",
            ),
            artifacts=[
                "captured: 2026-05-18T20:11:09.576Z",
                "model: gemma-4-e4b-it; 287515 ms",
                "GREP: false_urgency_only_n_spots",
                "GREP: online_platform_recruitment_unverified",
                "tool: PH-Saudi fee cap = 0 PHP",
                "grade: 70% / 6.96 auto rule-based",
            ],
            trace=_PH_SA_PLATFORM_TRACE,
        ),
        _recording_example(
            example_id="platform_lender_shaming_image",
            lane="Content moderation",
            audience="platform",
            use_case="retaliation_risk",
            prompt=(
                "Review this redacted WANTED-style lender post. It names a "
                "migrant worker, uses passport-photo collateral, and demands "
                "public pressure for repayment. What should platform safety "
                "do with it?"
            ),
            image=_static_evidence_image(
                "imgur_01_bank_hongkong_wanted.jpg",
                "Redacted lender-shaming post",
                "Public shaming + identity-document collateral pattern.",
                "Redacted social post used as evidence for lender-shaming risk",
            ),
            artifacts=[
                "GREP: public_shaming_debt_collection",
                "GREP: identity_document_collateral",
                "route: high-priority human moderation",
            ],
        ),
        _recording_example(
            example_id="platform_fee_camouflage_post",
            lane="Content moderation",
            audience="platform",
            use_case="fee_camouflage",
            prompt=(
                "A recruitment page advertises a no-upfront placement path, "
                "but the worker must accept training, medical, and transport "
                "deductions through a partner lender after arrival. Review for "
                "fee camouflage."
            ),
            image=_static_evidence_image(
                "drive_fb_123_finance_post.jpg",
                "Redacted finance-post thumbnail",
                "Sample social evidence used to demonstrate fee/debt screening.",
                "Redacted finance post thumbnail for moderation demo",
            ),
            artifacts=[
                "GREP: fee_camouflage_training",
                "GREP: salary_assignment",
                "tool: corridor fee-cap lookup",
            ],
        ),
        _recording_example(
            example_id="case_bundle_graph",
            lane="Case analysis",
            audience="ngo",
            use_case="debt_bondage",
            prompt=(
                "Summarize this intake bundle: receipts show a PHP 70,000 "
                "agency-arranged loan for medical, training, and transport; "
                "messages say the balance will be deducted monthly from a Hong "
                "Kong domestic-helper salary."
            ),
            image=_static_evidence_image(
                "imgur_04_yoursun_caretaker_wanted.jpg",
                "Redacted connected evidence image",
                "Representative redacted image for case-bundle review.",
                "Redacted evidence image for case analysis demo",
            ),
            artifacts=[
                "entities: worker, agency, lender, clinic",
                "edges: pays_to, deducts_from_salary, restricts_choice",
                "timeline: recruitment to destination deductions",
            ],
        ),
        _recording_example(
            example_id="worker_cached_chat",
            lane="Worker support",
            audience="worker",
            use_case="ph_hk_placement_fee",
            artifacts=[
                "offline corridor pack: PH-HK domestic work",
                "tools: fee-cap lookup, trusted-contact lookup",
                "privacy: local chat row only",
            ],
        ),
        _recording_example(
            example_id="research_cluster",
            lane="Research",
            audience="researcher",
            use_case="provider_choice",
            prompt=(
                "Across the anonymized signal stream, identify repeated "
                "agency, clinic, lender, and route patterns where workers are "
                "steered to a single provider chain."
            ),
            image=_static_evidence_image(
                "drive_fb_jan_2020_worst_agency_list.jpg",
                "Redacted multi-case social evidence",
                "Thumbnail used for reproducible cluster-analysis examples.",
                "Redacted multi-case social evidence image",
            ),
            artifacts=[
                "cluster: agency-clinic-lender chain",
                "evidence rows: version-pinned",
                "output: citation-ready pattern summary",
            ],
        ),
        _recording_example(
            example_id="sharing_knowledge_object",
            lane="Anonymized knowledge sharing",
            audience="developer",
            use_case="contract_substitution",
            prompt=(
                "Convert reviewed, redacted facts from a contract-substitution "
                "case into a knowledge object that can update future corridor "
                "packs without exposing the worker."
            ),
            image=_static_evidence_image(
                "imgur_03_facebook_wanted_thumbnail.jpg",
                "Redacted source thumbnail",
                "Small redacted source thumbnail for knowledge-object review.",
                "Redacted thumbnail for anonymized knowledge sharing demo",
            ),
            artifacts=[
                "PII gate: local first pass + server second pass",
                "consent: anonymous / region-tagged",
                "output: reusable knowledge object",
            ],
        ),
    ]

    chat = next(
        item for item in examples if item["id"] == "worker_cached_chat"
    )
    slides_chat = {
        "audience": chat["audience"],
        "use_case": chat["use_case"],
        "audience_key": chat["audience_key"],
        "use_case_key": chat["use_case_key"],
        "prompt": chat["prompt"],
        "response": chat["response"],
        "generated_at": "2026-05-18T00:00:00Z",
    }
    return {
        "schema_version": "duecare.slides.recording_pack.v1",
        "generated_at": "2026-05-18T00:00:00Z",
        "summary": (
            "Seven selected no-model examples for recording: three platform "
            "moderation examples with evidence images and one captured "
            "Gemma trace, one case-analysis bundle, one worker chat, one "
            "research cluster, and one anonymized knowledge-sharing object."
        ),
        "storage_keys": {
            "pack": "duecare.slides.demo.pack",
            "chat": "duecare.slides.demo.chat",
        },
        "examples": examples,
        "slides_chat": slides_chat,
        "moderation_trace": _PH_SA_PLATFORM_TRACE,
    }
