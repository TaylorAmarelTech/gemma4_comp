# ruff: noqa: E501
"""Shared, grounded DueCare indicator engine embedded into the use-case notebooks (NGO triage,
platform moderation, worker self-check, chain-of-thought generator).

Builders do `from _usecase_engine import ENGINE` and put it in the notebook's setup cell so the
notebook is self-contained on Kaggle. Deterministic + CPU + offline: it demonstrates the DueCare
harness's indicator/knowledge/reasoning logic without needing a GPU or model. It is a REPRESENTATIVE
subset of the real GREP layer (451 rules) + ILO knowledge packs -- production uses the full harness.
ASCII-only.
"""
from __future__ import annotations

ENGINE = r'''import re

# --- ILO 11 forced-labour indicators (ILO, Indicators of Forced Labour, 2012) ---
ILO_INDICATORS = {
    "abuse_of_vulnerability": "Abuse of vulnerability",
    "deception": "Deception",
    "restriction_of_movement": "Restriction of movement",
    "isolation": "Isolation",
    "violence": "Physical and sexual violence",
    "intimidation": "Intimidation and threats",
    "document_retention": "Retention of identity documents",
    "wage_withholding": "Withholding of wages",
    "debt_bondage": "Debt bondage",
    "abusive_conditions": "Abusive working and living conditions",
    "excessive_overtime": "Excessive overtime",
    "recruitment_fee": "Recruitment fees charged to the worker",
}
ILO_REFS = {
    "document_retention": "ILO C029; ILO Indicators of Forced Labour (2012)",
    "debt_bondage": "ILO C029 Art.2; ILO R203",
    "wage_withholding": "ILO C095 (Protection of Wages)",
    "recruitment_fee": "ILO C181 Art.7; ILO Fair Recruitment 2016 (no fees to workers)",
    "restriction_of_movement": "ILO C029; ILO Indicators of Forced Labour (2012)",
    "intimidation": "ILO C029; ILO Indicators of Forced Labour (2012)",
    "deception": "ILO C029; ILO C181 (accurate job terms)",
    "excessive_overtime": "ILO C001/C030 (hours of work)",
    "isolation": "ILO Indicators of Forced Labour (2012)",
    "abuse_of_vulnerability": "ICRMW Art.21; ILO Indicators of Forced Labour (2012)",
    "violence": "ILO C029; ILO C190 (violence and harassment)",
    "abusive_conditions": "ILO Indicators of Forced Labour (2012)",
}
# representative subset of the DueCare GREP indicator layer (production has 451 rules across 11 languages)
PATTERNS = [
    ("document_retention", r"(passport|national id|residence permit|iqama|papers|documents?)\s+(\w+\s+){0,4}(took|takes|taken|kept|keeps|held|hold|holding|confiscat\w*|retain\w*|surrender\w*|hand(ed)?\s+over|for safekeeping)"),
    ("debt_bondage", r"(debt|loan|advance|owe|owing|repay)\s+(\w+\s+){0,6}(work(ing)?\s+(it\s+)?off|repay|deduct\w*|paid off|cannot leave|can'?t leave|until.*paid)"),
    ("recruitment_fee", r"(recruitment|placement|processing|training|mobiliz\w+|agency|service)\s*(fee|charge|bond|deposit|commission)"),
    ("wage_withholding", r"(salary|wages?|pay|payment)\s+(\w+\s+){0,4}(withheld|withhold\w*|held back|deduct\w*|not (yet )?paid|unpaid|delay\w*|kept)"),
    ("restriction_of_movement", r"(cannot|can'?t|not allowed|forbidden|need(s)? permission|locked|not free)\s+(\w+\s+){0,3}(leave|go out|go outside|outside|exit|move)"),
    ("intimidation", r"(threat\w*|deport\w*|report (you |us )?to (the )?(police|immigration|authorities)|blacklist\w*|fired if|call the (police|embassy)|scared to)"),
    ("deception", r"(promised|told|was told|said|contract said)\s+(\w+\s+){0,6}(different|not what|changed|actually|instead|another|lied|false)"),
    ("excessive_overtime", r"(\d{2,3}\s*hours|no day off|no days off|seven days a week|every day|no rest|18[- ]hour|around the clock)"),
    ("isolation", r"(no phone|phone (was )?taken|cannot contact|not allowed to (call|leave the)|no communication|kept (me )?away|far from anyone)"),
    ("abuse_of_vulnerability", r"(does not speak|do not speak|no(t)? .*language|undocument\w*|irregular status|no papers|first time abroad|owe.*family|desperate)"),
    ("violence", r"(hit|beat\w*|slap\w*|hurt|abuse\w*|assault\w*|touch(ed|ing)? me|forced (me )?to)"),
    ("abusive_conditions", r"(no food|not enough food|sleep on the floor|no bed|crowded room|no water|unsafe|no protective|sick and)"),
]
FEE_CAMOUFLAGE = ["training bond", "mobilization fee", "processing fee", "service charge", "placement fee",
                  "agency commission", "medical deposit", "security deposit", "e-wallet fee",
                  "visa cost recovery", "sustainability fee", "retention incentive", "loyalty deduction"]
HOTLINES = {
    "global": "IOM / ILO referral pathways; Polaris (US) 1-888-373-7888; verify the current in-country number before use",
    "US": "National Human Trafficking Hotline 1-888-373-7888 (Polaris)",
    "Philippines": "DMW / OWWA hotlines; Blas Ople Center",
    "Nepal": "HRD Nepal; Foreign Employment Board grievance desk",
    "Gulf / GCC": "Home-country embassy labour attache; local labour ministry grievance line",
    "note": "Public hotline numbers change; in production these come from a versioned knowledge pack / tool call, not from memory.",
}

def scan(text):
    """Return the list of ILO indicators detected in `text` (deterministic, representative)."""
    t = (text or "").lower()
    hits, seen = [], set()
    for ind, pat in PATTERNS:
        m = re.search(pat, t)
        if m and ind not in seen:
            seen.add(ind)
            hits.append({"indicator": ind, "label": ILO_INDICATORS.get(ind, ind),
                         "snippet": re.sub(r"\s+", " ", m.group(0))[:90], "ilo_ref": ILO_REFS.get(ind, "ILO Indicators of Forced Labour (2012)")})
    for fee in FEE_CAMOUFLAGE:
        if fee in t and "recruitment_fee" not in seen:
            seen.add("recruitment_fee")
            hits.append({"indicator": "recruitment_fee", "label": "Recruitment fee charged to the worker (camouflaged)",
                         "snippet": fee, "ilo_ref": ILO_REFS["recruitment_fee"]})
    return hits

def risk_level(hits):
    n = len(hits)
    if n >= 4: return ("HIGH", "Multiple forced-labour indicators present")
    if n >= 2: return ("ELEVATED", "Several indicators present -- warrants review")
    if n == 1: return ("WATCH", "One indicator present -- ask follow-up questions")
    return ("LOW", "No clear indicators in this text (absence of evidence is not evidence of safety)")

# --- Chain-of-thought question framework (the structured questions the CoT dataset encodes) ---
INDICATOR_QUESTIONS = [(ind, "Is there evidence of " + lab.lower() + "?") for ind, lab in ILO_INDICATORS.items()]
LIFECYCLE = ["recruitment", "transit", "arrival", "employment", "complaint", "exit", "remedy"]
EVIDENCE_STATES = ["present", "absent", "ambiguous", "needs more information"]
COUNTERFACTUALS = [
    "Could a lawful arrangement plausibly explain this?",
    "What single fact would flip this to benign?",
    "Is any apparent consent meaningful, or is it coerced by circumstance?",
    "Is the fee/deduction lawful in this corridor, or is it a worker-paid cost?",
    "What piece of evidence is missing that would confirm or refute the concern?",
]

def generate_chain(text):
    """Generate a reasoned chain by asking the structured ILO-indicator questions of `text`.
    Returns a list of (step_number, text) reasoning steps."""
    hits = {h["indicator"]: h for h in scan(text)}
    steps, n = [], 1
    steps.append((n, "Restate the situation in neutral, non-leading terms.")); n += 1
    for ind, q in INDICATOR_QUESTIONS:
        if ind in hits:
            steps.append((n, q + " -> PRESENT [" + ILO_INDICATORS[ind] + "; " + ILO_REFS.get(ind, "ILO 2012") + "]  cue: '" + hits[ind]["snippet"] + "'"))
        else:
            steps.append((n, q + " -> not evident in this text"))
        n += 1
    for stage in LIFECYCLE:
        steps.append((n, "Lifecycle stage '" + stage + "': what to verify here and what a worker/caseworker should do next.")); n += 1
    for cf in COUNTERFACTUALS:
        steps.append((n, "Counterfactual check: " + cf)); n += 1
    lvl, why = risk_level(scan(text))
    steps.append((n, "Conclusion: risk = " + lvl + " (" + why + "). Name the indicators, cite the controlling ILO instrument, route to real help, and do NOT operationalize the scheme."))
    return steps
'''
