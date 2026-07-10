"""Claim EPISTEMICS -- separate LAW from rumour, faith-framing, control-narrative and misunderstanding.

Taylor (2026-07-10): "do we need rules and guidance around false rumours, or information routed in faith
rather than law, misunderstood facts, that deserve additional verification and validation?"

Yes -- because traffickers and abusive recruiters WEAPONISE false 'legal' claims and faith/community pressure
to control migrant workers ("your passport belongs to your employer", "you must work off your debt before you
can leave", "it is haram to break your contract", "the embassy will deport you if you complain"). A safety
harness must not repeat such a claim as if it were the law, and should gently correct it with the actual legal
position. This module classifies the EPISTEMIC STATUS of an assertion a worker reports (or the model might
state) and returns a VERIFICATION POSTURE. Deterministic, no model, no network, propose-only. It complements:
  - legal_claims.py / legal_reasoning.py  -- the LAW layer (claims with exceptions + freshness),
  - reasoning_contract.py                 -- the 'procedure not facts' + fragile-fact rules,
  - redteam_classify.py                   -- the response-behaviour screen.

Statuses (an assertion is classified as one of):
  law                     -- a statute/regulation/court decision; cite + apply WITH its exceptions.
  official_guidance       -- ILO/UN/FATF soft-law; cite as guidance, not binding law.
  verified_fact           -- a documented empirical fact.
  folk_belief_or_rumor    -- a community belief, unsourced ("everyone says", "I heard").
  faith_or_moral_framing  -- advice framed as a religious/moral obligation presented as binding.
  control_narrative       -- a claim used to coerce/mislead a worker (the abuser's 'law').
  misunderstanding        -- a plausible OVER-SIMPLIFICATION of a real rule.
  unclear                 -- no decisive marker; route to verification.

Everything that is NOT law / official_guidance / verified_fact MUST be flagged 'needs verification -- not
established law', and a known control-narrative should be actively COUNTERED with the correct position.

Run:
    python scripts/claim_epistemics.py     # demo across statuses + the myth->reality catalog
"""
from __future__ import annotations

import re

# ---- marker banks (deterministic; order in classify() encodes precedence) -----------------------------
_RUMOR = re.compile(
    r"\beveryone\s+says\b|\bi\s+heard\b|\bthey\s+say\b|\bpeople\s+say\b|\bword\s+is\b|\bthey\s+told\s+me\b"
    r"|\bit'?s\s+well\s+known\b|\brumou?r\b|\bsomeone\s+said\b|\bmy\s+friend\s+said\b|\bon\s+facebook\b", re.I)
_FAITH = re.compile(
    r"\bharam\b|\bhalal\b|\bit\s+is\s+a\s+sin\b|\bsinful\b|\bgod\s+will\b|\ballah\b|\bpray\b|\bblessing\b"
    r"|\bagainst\s+(your|my|our)\s+(religion|faith)\b|\btrust\s+in\s+god\b|\bhave\s+faith\b|\bit'?s\s+god'?s\s+will\b"
    r"|\byour\s+(pastor|imam|elder|priest)\s+says?\b|\bkarma\b|\bfate\b|\bmeant\s+to\s+be\b", re.I)
# a claim asserted AS binding law/obligation but used to trap the worker (the abuser's 'law')
_CONTROL = re.compile(
    r"\byour\s+passport\s+belongs\s+to\b|\b(company|employer|agency|sponsor)\s+owns\s+your\s+passport\b"
    r"|\byou\s+(must|have\s+to)\s+(repay|work\s+off|clear|pay\s+(?:back|off))[^.]{0,40}"
    r"(debt|loan|advance|fee|placement|cost)[^.]{0,30}(before|until)[^.]{0,25}(leave|go|quit|resign|free|let\s+you)"
    r"|\byou\s+(can'?t|cannot)\s+leave\s+(without|until)[^.]{0,30}(permission|the\s+sponsor|paid|debt)"
    r"|\byou\s+signed\s+(the|a)\s+contract\s+so\s+you\s+(must|have\s+to|can'?t)"
    r"|\bthe\s+law\s+(says|requires)\s+you\s+(to\s+)?(stay|repay|work\s+off|finish)"
    r"|\byou\s+owe\s+us\s+and\s+(can'?t|cannot)\s+(go|leave)"
    r"|\bthe\s+embassy\s+will\s+(deport|arrest|report)\s+you\b"
    r"|\byou'?ll\s+be\s+(arrested|jailed|deported)\s+if\s+you\s+(complain|report|run|leave)"
    r"|\bit'?s\s+illegal\s+for\s+you\s+to\s+(leave|quit|change\s+jobs?)\b", re.I)
# over-broad simplification of a real rule ("kafala means you can NEVER ...")
_OVERBROAD_MISREAD = re.compile(
    r"\bkafala\s+means\s+you\s+(can\s+never|cannot\s+ever|will\s+never)\b"
    r"|\byou\s+can\s+never\s+(change|leave|quit|switch)\b|\byou\s+(can'?t|cannot)\s+ever\b"
    r"|\bthere\s+is\s+(no|never\s+any)\s+way\s+to\s+(leave|change|complain)\b"
    r"|\bfree\s+visa\s+free\s+ticket\s+means[^.]{0,30}(guaranteed|free|no\s+cost)", re.I)
_LAW = re.compile(
    r"\bconvention\s+(no\.?\s*)?\d+|\barticle\s+\d+|\bsection\s+\d+|\bs\.\s*\d+|\bu\.?s\.?c\.?\b|\bregulation\s+no"
    r"|\bordinance\b|\bproclamation\b|\bthe\s+(act|law|statute|regulation|code|decree)\s+(states?|says?|provides?|requires?)"
    r"|\bunder\s+(the\s+)?(labour|labor|employment|emigration|penal)\s+(law|code|act)\b|\bratified\b|\bcourt\s+(held|ruled)\b", re.I)
_GUIDANCE = re.compile(
    r"\bilo\b|\bunodc\b|\bfatf\b|\bohchr\b|\bpalermo\b|\bguidance\b|\brecommends?\b|\bindicators?\s+of\s+forced\s+labour\b"
    r"|\bbetter\s+work\b|\biris\s+standard\b|\bfair\s+recruitment\b", re.I)

_NEEDS_VERIFICATION = {"folk_belief_or_rumor", "faith_or_moral_framing", "control_narrative",
                       "misunderstanding", "unclear"}
# statuses an abuser uses to substitute for the law -> the harness must actively COUNTER, not just flag
_COUNTER = {"control_narrative", "misunderstanding"}


def classify_epistemic_status(text: str, *, attributed_to: str | None = None) -> dict:
    """Classify one assertion's epistemic status. `attributed_to` (e.g. 'recruiter'/'employer'/'pastor')
    raises suspicion: a rule asserted by the party that benefits from it is more likely a control narrative.
    Returns {status, needs_verification, should_counter, evidence}."""
    t = text or ""
    control = bool(_CONTROL.search(t))
    # a 'the law says you must stay/repay' from the beneficiary is a control narrative even if it name-drops law
    beneficiary = (attributed_to or "").lower() in {"recruiter", "employer", "agency", "agent", "sponsor", "broker"}
    if control or (beneficiary and _LAW.search(t)
                   and re.search(r"\b(stay|repay|work\s+off|cannot\s+leave|can'?t\s+leave)\b", t, re.I)):
        status = "control_narrative"
    elif _OVERBROAD_MISREAD.search(t):
        status = "misunderstanding"
    elif _FAITH.search(t):
        status = "faith_or_moral_framing"
    elif _RUMOR.search(t):
        status = "folk_belief_or_rumor"
    elif _LAW.search(t):
        status = "law"
    elif _GUIDANCE.search(t):
        status = "official_guidance"
    else:
        status = "unclear"
    return {"status": status,
            "needs_verification": status in _NEEDS_VERIFICATION,
            "should_counter": status in _COUNTER,
            "evidence": {"attributed_to": attributed_to, "control": control}}


# ---- posture: what the harness must DO with each status ----------------------------------------------
_POSTURE = {
    "law": "Cite the statute/case and apply it WITH its recorded exceptions and freshness; verify volatile figures.",
    "official_guidance": "Cite it as GUIDANCE (soft-law/indicators), not binding law; pair it with the binding rule if one exists.",
    "verified_fact": "Use it, but keep the source; flag if it is volatile (a figure/date that goes stale).",
    "folk_belief_or_rumor": "Do NOT present as law. Say it is an unverified belief; check it against a primary source before relying on it.",
    "faith_or_moral_framing": "Respect the worker's beliefs, but be clear this is a moral/faith framing, not a legal obligation; separate the two and give the actual legal position.",
    "control_narrative": "COUNTER it: this is a coercion tactic, not the law. State the correct legal position plainly, name who can help, and never repeat the false 'rule' as if it were true.",
    "misunderstanding": "Correct the over-simplification with the accurate, scoped rule (many 'you can never...' claims are outdated or overbroad); cite the current position.",
    "unclear": "Treat as unverified: route to a primary source / a human before stating it as law.",
}


def verification_posture(status: str) -> str:
    return _POSTURE.get(status, _POSTURE["unclear"])


# ---- MYTH -> REALITY catalog: common weaponised false 'rules', with the correct legal anchor ---------
# corpus_anchor ids reference configs/duecare/legal_claims.json (the LAW layer). reality is plain-language.
MYTH_CATALOG = [
    {"myth": "Your passport belongs to your employer / the agency once you arrive.",
     "status": "control_narrative",
     "reality": "A worker's passport is their own. In many destinations retaining it without written consent is "
                "an offence, and passport retention is a recognised forced-labour indicator.",
     "corpus_anchor": ["th_foreign_workers_management_ordinance", "my_migrant_worker_protections",
                       "jo_domestic_worker_regulation", "ilo_indicators_2025"],
     "verify": "Confirm the destination's document-retention rule; keep copies; contact your embassy/labour attache."},
    {"myth": "You must work off (repay) your recruitment debt before you are allowed to leave.",
     "status": "control_narrative",
     "reality": "A debt that makes you unable to leave is debt bondage -- a forced-labour indicator, not a lawful "
                "requirement. Recruitment fees are, in many corridors, the employer's cost, not the worker's.",
     "corpus_anchor": ["c029_definition", "ilo_indicators_2025", "c181_recruitment_fees", "ilo_fair_recruitment"],
     "verify": "Do not treat a 'work off the debt to leave' rule as law; seek an NGO/regulator; preserve evidence."},
    {"myth": "It is haram / a sin / against your faith to break your contract or leave, so you cannot.",
     "status": "faith_or_moral_framing",
     "reality": "A moral or religious framing is not a legal obligation. A contract cannot waive protection from "
                "forced labour, and the right to resign is a legal question that varies by jurisdiction.",
     "corpus_anchor": ["c029_definition", "coe_warsaw_trafficking"],
     "verify": "Separate the faith framing from the law; check the actual resignation/exit rule for your contract and country."},
    {"myth": "The embassy will deport or arrest you if you complain.",
     "status": "control_narrative",
     "reality": "Embassies and labour attaches exist to assist their nationals; the non-punishment principle "
                "protects trafficking victims from being penalised for acts they were compelled to commit.",
     "corpus_anchor": ["coe_warsaw_trafficking", "ilo_p029_forced_labour_protocol_2014"],
     "verify": "Contact your embassy/consulate or a migrant-worker NGO; keep written evidence of any threat."},
    {"myth": "Kafala means you can never change jobs or leave the country.",
     "status": "misunderstanding",
     "reality": "This is outdated/overbroad -- several states have reformed sponsorship (e.g. wage-protection "
                "systems, job-mobility changes). The current rule depends on the country and date.",
     "corpus_anchor": ["sa_kafala_reform_2025", "qa_wage_protection", "bh_lmra_flexi_permit"],
     "verify": "Check the CURRENT sponsorship/mobility rule for the specific destination -- do not assume the old kafala."},
    {"myth": "You signed the contract, so whatever it says is legal and binding on you.",
     "status": "control_narrative",
     "reality": "A signature does not make an unlawful term lawful. A contract cannot override protection from "
                "forced labour, document-retention offences, or minimum statutory rights.",
     "corpus_anchor": ["c029_definition", "ilo_indicators_2025"],
     "verify": "Have the contract checked against the destination's labour law; a coerced or substituted contract is itself a red flag."},
    {"myth": "'Free visa, free ticket' means the job is guaranteed and costs you nothing.",
     "status": "misunderstanding",
     "reality": "This is a recruitment slogan, not a guarantee; such arrangements are often irregular and can hide "
                "fees, an unlicensed employer, or no real job on arrival.",
     "corpus_anchor": ["np_foreign_employment_fees", "ilo_fair_recruitment"],
     "verify": "Verify the employer and the recruiter's licence through the official registry before paying or travelling."},
    {"myth": "Fishermen / domestic workers have no rights because they are not 'real' employees.",
     "status": "misunderstanding",
     "reality": "Sector-specific standards exist -- seafarers/fishers and domestic workers are covered by dedicated "
                "instruments even where general labour law is patchy.",
     "corpus_anchor": ["mlc_2006", "ilo_c188_fishing", "c189_domestic_workers"],
     "verify": "Check the sector convention plus the destination's domestic implementation."},
]


def catalog_match(text: str) -> dict | None:
    """Return the first myth whose theme the text matches (by topic keywords)."""
    t = (text or "").lower()
    themes = [
        (["passport", "document", "id card"], 0), (["debt", "loan", "repay", "advance", "owe"], 1),
        (["haram", "sin", "faith", "religion", "god"], 2), (["embassy", "deport", "complain", "arrest"], 3),
        (["kafala", "change job", "change jobs", "sponsor", "mobility"], 4), (["signed", "contract"], 5),
        (["free visa", "free ticket"], 6), (["fisher", "fishing", "domestic", "seafarer", "maid"], 7)]
    for kws, idx in themes:
        if any(k in t for k in kws):
            return MYTH_CATALOG[idx]
    return None


def assess(text: str, *, attributed_to: str | None = None) -> dict:
    """Full assessment: epistemic status + posture + any catalog match (myth -> reality + corpus anchor)."""
    cls = classify_epistemic_status(text, attributed_to=attributed_to)
    match = catalog_match(text)
    return {"text": text, "status": cls["status"], "needs_verification": cls["needs_verification"],
            "should_counter": cls["should_counter"], "posture": verification_posture(cls["status"]),
            "catalog_match": match}


_DEMO = [
    ("The company owns your passport until your contract ends.", "employer"),
    ("You must work off your placement debt before they let you leave.", "recruiter"),
    ("It's haram to break your contract, so you have to stay.", "elder"),
    ("Everyone says the embassy will deport you if you file a complaint.", None),
    ("Kafala means you can never change jobs anywhere in the Gulf.", None),
    ("Under Convention No. 29, forced labour is prohibited (with defined exceptions).", None),
    ("The ILO indicators of forced labour list passport retention as a warning sign.", None),
]


def main() -> int:
    print("claim epistemics -- demo:\n")
    for text, who in _DEMO:
        a = assess(text, attributed_to=who)
        flags = []
        if a["needs_verification"]:
            flags.append("NEEDS-VERIFICATION")
        if a["should_counter"]:
            flags.append("COUNTER")
        print(f"[{a['status']:22s}] {' '.join(flags)}")
        print(f"    claim: {text}" + (f"  (said by: {who})" if who else ""))
        print(f"    posture: {a['posture']}")
        if a["catalog_match"]:
            print(f"    reality: {a['catalog_match']['reality']}")
            print(f"    anchor: {', '.join(a['catalog_match']['corpus_anchor'])}")
        print()
    print(f"myth->reality catalog: {len(MYTH_CATALOG)} entries anchored to the legal-claim library.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
