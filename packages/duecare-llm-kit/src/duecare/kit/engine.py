"""DueCare indicator engine.

Single source of truth: this file is kept in sync with scripts/_usecase_engine.py ENGINE
(the string embedded into the self-contained Kaggle notebooks). Representative subset of the
real GREP layer + ILO knowledge packs. Deterministic, stdlib-only. ASCII.
"""
from __future__ import annotations

import re

# --- ILO 11 forced-labour indicators (ILO, Indicators of Forced Labour, 2012) + a recruitment-fee screen ---
# Kept at exactly 12 keys: the 11 canonical ILO 2012 indicators plus recruitment_fee. Do not add keys
# here -- notebooks display len(ILO_INDICATORS) as "12 ILO indicators".
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
# Controlling instrument(s) per indicator. Enriched with specific articles so a reader can verify each
# legal claim. Keyed by the 12 indicators above; scan() looks refs up by indicator key.
ILO_REFS = {
    "document_retention": "ILO C029; ILO Indicators of Forced Labour (2012) 'retention of identity documents'; ICRMW (1990) Art. 21 (unlawful confiscation of ID/travel documents); ILO C189 Art. 9 (domestic workers keep their own documents)",
    "debt_bondage": "ILO C029 Art. 2 + P029 (2014); ILO Indicators of Forced Labour (2012) 'debt bondage'; 1956 Supplementary Slavery Convention Art. 1(a); ILO R203",
    "wage_withholding": "ILO C095 (Protection of Wages, 1949) Art. 8/9/12; ILO Indicators of Forced Labour (2012) 'withholding of wages'",
    "recruitment_fee": "ILO C181 Art. 7(1) (no fees/costs to workers), subject to Art. 7(2) exceptions; ILO General Principles & Operational Guidelines for Fair Recruitment (2016) Principle 7",
    "restriction_of_movement": "ILO C029; ILO Indicators of Forced Labour (2012) 'restriction of movement'; UN Palermo Protocol Art. 3 (confinement as a means)",
    "intimidation": "ILO C029; ILO Indicators of Forced Labour (2012) 'intimidation and threats'; UN Palermo Protocol Art. 3 (threat/coercion as a means)",
    "deception": "ILO C029; ILO C181 (accurate job terms); ILO Indicators of Forced Labour (2012) 'deception'; UN Palermo Protocol Art. 3 (deception as a means)",
    "excessive_overtime": "ILO C001/C030 (hours of work); ILO Indicators of Forced Labour (2012) 'excessive overtime'",
    "isolation": "ILO Indicators of Forced Labour (2012) 'isolation'; ILO C029",
    "abuse_of_vulnerability": "ICRMW (1990) Art. 21; ILO Indicators of Forced Labour (2012) 'abuse of vulnerability'; UN Palermo Protocol Art. 3 ('abuse of a position of vulnerability')",
    "violence": "ILO C029; ILO C190 (Violence and Harassment, 2019); ILO Indicators of Forced Labour (2012) 'physical and sexual violence'",
    "abusive_conditions": "ILO Indicators of Forced Labour (2012) 'abusive working and living conditions'; ILO C155 (OSH, 1981)",
}

# --- International instruments referenced across the harness (module-level, additive) ---
# Instrument code -> one-line scope. Grounded in the ratified text; notebooks may surface this beside
# ILO_REFS to explain a citation. Not keyed by indicator (that is ILO_REFS' job).
ILO_CONVENTIONS = {
    "C029": "Forced Labour Convention (1930) -- defines/suppresses forced or compulsory labour; Art. 2 definition, Art. 25 penalties.",
    "P029": "2014 Protocol to C029 -- binds States to prevention, victim protection and remedy, and recruitment regulation.",
    "C105": "Abolition of Forced Labour Convention (1957) -- bans forced labour for five specified purposes (political coercion, economic development, labour discipline, strike punishment, discrimination).",
    "C095": "Protection of Wages Convention (1949) -- wages paid regularly and directly in legal tender; limits deductions (Art. 8); bars deductions to obtain/keep a job (Art. 9).",
    "C181": "Private Employment Agencies Convention (1997) -- Art. 7(1) general prohibition on charging recruitment fees/costs to workers, with narrow Art. 7(2) exceptions.",
    "C097": "Migration for Employment Convention (Revised) (1949) -- equal treatment of regular migrant workers; authorised recruitment channels.",
    "C143": "Migrant Workers (Supplementary Provisions) Convention (1975) -- basic rights of all migrant workers incl. irregular status; addresses migration in abusive conditions.",
    "ICRMW": "UN Convention on the Rights of All Migrant Workers and Members of Their Families (1990) -- Art. 21 bars unlawful confiscation/destruction of identity or travel documents.",
    "C189": "Domestic Workers Convention (2011) -- decent-work rights for domestic workers; Art. 9 right to keep travel and identity documents; free agreement to live in.",
    "C190": "Violence and Harassment Convention (2019) -- right to a world of work free from violence and harassment.",
    "R203": "Forced Labour (Supplementary Measures) Recommendation (2014) -- guidance accompanying P029 on prevention, protection, and access to remedy.",
    "R204": "Transition from the Informal to the Formal Economy Recommendation (2015) -- formalisation reduces exposure to forced-labour risk.",
    "C138": "Minimum Age Convention (1973) -- minimum age for admission to employment or work.",
    "C182": "Worst Forms of Child Labour Convention (1999) -- prohibits/eliminates the worst forms, incl. sale and trafficking of children.",
    "C188": "Work in Fishing Convention (2007) -- written work agreements; Art. 22 the vessel owner (not the fisher) bears recruitment/placement fees.",
    "C155": "Occupational Safety and Health Convention (1981) -- safe and healthy working conditions; employer bears the cost of protective measures.",
    "PALERMO": "UN Protocol to Prevent, Suppress and Punish Trafficking in Persons (2000) -- Art. 3 act/means/purpose definition of trafficking.",
    "SSC1956": "1956 Supplementary Convention on the Abolition of Slavery -- Art. 1(a) debt bondage as a servile status to be abolished.",
}

# representative subset of the DueCare GREP indicator layer (production has 451 rules across 11+
# languages). Each tuple is (indicator_key, regex). Multiple tuples may share an indicator key: scan()
# reports the first match per indicator, so extra patterns only widen phrasing coverage. Patterns are
# bidirectional where useful and deliberately require a coercion/worker-paid/retention context so that a
# lawful arrangement (e.g. "the employer pays all fees", "my passport stays with me") does NOT fire.
PATTERNS = [
    # -- document retention (ILO 2012 indicator; ICRMW Art. 21) --
    ("document_retention", r"(passport|national id|residence permit|iqama|papers|documents?)\s+(\w+\s+){0,4}(took|takes|taken|kept|keeps|held|hold|holding|confiscat\w*|retain\w*|surrender\w*|hand(ed)?\s+over|for safekeeping)|(took|takes|taken|keeps?|kept|holding|holds|confiscat\w*|retain\w*|has|have|got)\s+(my |his |her |the |our )?(\w+\s+){0,2}(passport|national id|residence permit|iqama|papers|documents?)"),
    ("document_retention", r"(cannot|can'?t|not allowed to|won'?t let me|refuse[sd]? to (give|return)|never (got|returned))\s+(\w+\s+){0,3}(get|have|keep|access|hold|see|take)?\s*(my |our |their )?(own )?(passport|national id|residence permit|iqama|papers|documents?)"),
    ("document_retention", r"(employer|agency|agent|sponsor|boss|madam|kafeel|company|recruiter)\s+(\w+\s+){0,3}(has|have|holds?|holding|keeping|keeps|kept|took|taken|confiscat\w*|retain\w*|locked (away|up))\s+(\w+\s+){0,2}(passport|national id|residence permit|iqama|papers|documents?)"),
    # -- debt bondage (ILO C029 + P029; SSC 1956 Art. 1(a)) --
    ("debt_bondage", r"(debt|loan|advance|owe|owing|repay)\s+(\w+\s+){0,6}(work(ing)?\s+(it\s+)?off|repay|deduct\w*|paid off|cannot leave|can'?t leave|until.*paid)|work(ing)?\s+(it\s+|to pay\s+)?off\s+(the\s+)?(\w+\s+){0,3}(fee|debt|loan|advance|bond|cost)"),
    ("debt_bondage", r"(until|before)\s+(\w+\s+){0,5}(debt|loan|advance|fee|bond|balance)\s+(is\s+)?(paid|repaid|cleared|settled|worked\s+off|finished)"),
    ("debt_bondage", r"(deduct\w*|garnish\w*|withhold\w*|take[ns]?)\s+(\w+\s+){0,4}(from|out of)\s+(my |his |her |our )?(salary|wages?|pay)\s+(\w+\s+){0,5}(loan|debt|advance|recruitment|placement|agent)"),
    # -- recruitment fees charged to the worker (ILO C181 Art. 7) --
    ("recruitment_fee", r"(recruitment|placement|processing|training|mobiliz\w+|agency|service)\s*(fee|charge|bond|deposit|commission)"),
    ("recruitment_fee", r"\b(i|we|worker|workers|she|he)\b\s+(paid|had to pay|was charged|were charged|got charged|borrowed|owe)\s+(\w+\s+){0,5}(agency|recruiter|agent|broker|sponsor|manpower|for (the )?(job|placement|deployment|visa|contract))"),
    ("recruitment_fee", r"(recruitment|placement|agency|broker|agent|processing|training|deployment)\s+(fee|cost|charge|commission)\s+(of|was|is|=|:)?\s*(\$|usd|php|npr|idr|bdt|sar|aed|qar|kwd|riyal|peso|rupee|taka|dirham|rm|ringgit)?\s*[\d,]{3,}"),
    # -- withholding of wages (ILO C095 Art. 8/9/12) --
    ("wage_withholding", r"(salary|wages?|pay|payment)\s+(\w+\s+){0,4}(withheld|withhold\w*|held back|deduct\w*|not (yet )?paid|unpaid|delay\w*|kept)|(not|have not|haven.t|hasn.t|never|no)\s+(been\s+|yet\s+)?(paid|receiv\w+\s+(any |my )?(pay|wages?|salary))"),
    ("wage_withholding", r"(no|without|zero|haven'?t (had|got|received)|didn'?t (get|receive)|still no)\s+(\w+\s+){0,3}(salary|wages?|pay|payment)\s+(for|in|since)\s+(\w+\s+){0,3}(month|months|weeks?|days)"),
    ("wage_withholding", r"(salary|wages?|pay)\s+(\w+\s+){0,3}(deducted|docked|cut|reduced|slashed)\s+(\w+\s+){0,5}(fine|penalty|breakage|damage|no reason|without (my )?(consent|agreement))"),
    # -- restriction of movement (ILO C029) --
    ("restriction_of_movement", r"(cannot|can'?t|not allowed|forbidden|need(s)? permission|locked|not free)\s+(\w+\s+){0,3}(leave|go out|go outside|outside|exit|move)"),
    ("restriction_of_movement", r"(locked|confined|trapped|held|kept|stuck)\s+(in|inside|indoors|at)\s+(\w+\s+){0,2}(house|home|dorm|dormitory|compound|accommodation|room|villa|camp|site|factory)"),
    ("restriction_of_movement", r"(door|gate|windows?|room)\s+(is|are|was|were|stay|kept)?\s*(locked|barred|chained|bolted|padlocked)"),
    # -- intimidation and threats (ILO C029; Palermo Art. 3) --
    ("intimidation", r"(threat\w*|deport\w*|report (you |us )?to (the )?(police|immigration|authorities)|blacklist\w*|fired if|call the (police|embassy)|scared to)"),
    ("intimidation", r"\b(threaten\w*|warn\w*|said|says|told me|told us)\b\s+(\w+\s+){0,5}(deport|jail|prison|arrest\w*|police|immigration|kill|beat|hurt|blacklist|cancel (my |the |your )?(visa|permit|iqama|contract))"),
    ("intimidation", r"\bif\s+(i|you|we|she|he|they)\s+(leave|complain|report|refuse|run|escape|quit|tell)\b\s+(\w+\s+){0,6}(deport|fired|no pay|police|arrest\w*|blacklist\w*|punish\w*|beat\w*|hurt|cancel|send (me |us |her |him |them )?(back|home))"),
    # -- deception (ILO C181 accurate terms; Palermo Art. 3) --
    ("deception", r"(promised|told|was told|said|contract said)\s+(\w+\s+){0,6}(different|not what|changed|actually|instead|another|lied|false)"),
    ("deception", r"(contract|job|salary|work|terms|pay)\s+(\w+\s+){0,4}(not (the same|as promised|what was promised)|changed|different|switched|substituted|replaced|rewrote|torn up|less than promised)"),
    # -- excessive overtime (ILO C001/C030) --
    ("excessive_overtime", r"(\d{2,3}\s*hours|no day off|no days off|seven days a week|every day|no rest|18[- ]hour|around the clock)"),
    ("excessive_overtime", r"(never|not|no|denied|refused|without)\s+(get|getting|given|allowed|had)?\s*(a |any )?(day off|days off|rest day|rest days|weekly rest|break|holiday|leave)"),
    # -- isolation (ILO 2012 indicator) --
    ("isolation", r"(no phone|phone (was )?taken|cannot contact|not allowed to (call|leave the)|no communication|kept (me )?away|far from anyone)"),
    ("isolation", r"(took|confiscated|smashed|locked away|no access to)\s+(\w+\s+){0,3}(phone|mobile|sim|cellphone|internet)"),
    # -- abuse of vulnerability (ICRMW Art. 21; Palermo Art. 3) --
    ("abuse_of_vulnerability", r"(does not speak|do not speak|no(t)? .*language|undocument\w*|irregular status|no papers|first time abroad|owe.*family|desperate)"),
    ("abuse_of_vulnerability", r"(undocumented|irregular|expired|overstay\w*|no (valid )?)\s+(immigration\s+)?(status|visa|work permit|permit|papers?|legal status|documents?)"),
    # -- physical and sexual violence (ILO C029; C190) --
    ("violence", r"(hit|beat\w*|slap\w*|hurt|abuse\w*|assault\w*|touch(ed|ing)? me|forced (me )?to)"),
    ("violence", r"(beat\w*|hit|slap\w*|punch\w*|kick\w*|burn\w*|chok\w*|strangl\w*|whip\w*|rape\w*|molest\w*|grope\w*)\s+(me|us|her|him|the worker)|at (gun|knife)point|sexual\w*\s+(abuse|assault|harass\w*|violence)"),
    # -- abusive working and living conditions (ILO 2012 indicator; C155) --
    ("abusive_conditions", r"(no food|not enough food|sleep on the floor|no bed|crowded room|no water|unsafe|no protective|sick and)"),
    ("abusive_conditions", r"(no|not enough|denied|without)\s+(\w+\s+){0,2}(food|clean water|drinking water|medicine|medical care|rest|sleep|toilet|sanitation)"),
]
# Deceptive worker-paid-fee labels (a placement charge or control wearing a friendlier name). Matched as
# distinctive multi-word substrings by scan(); grounded in the harness FEE_CAMOUFLAGE_DICT. Any hit maps
# to the recruitment_fee indicator (ILO C181 Art. 7 / Fair Recruitment 2016 Principle 7).
FEE_CAMOUFLAGE = ["training bond", "mobilization fee", "processing fee", "service charge", "placement fee",
                  "agency commission", "medical deposit", "security deposit", "e-wallet fee",
                  "visa cost recovery", "sustainability fee", "retention incentive", "loyalty deduction",
                  "cost recovery", "orientation fee", "uniform deposit", "insurance deduction",
                  "kafala transfer fee", "exit permit fee", "release fee", "skills test fee",
                  "stamping fee", "guarantee fee", "documentation fee", "loan transfer fee",
                  "productivity bond", "mobility loan", "onboarding investment",
                  "professional services agreement", "runaway insurance", "absconding deposit",
                  "welfare fund deduction", "food and accommodation deduction", "recruitment deposit"]

# Conservative romanised (Latin-script, ASCII) multilingual cue layer. Grounded in the harness'
# MULTILINGUAL_GREP_RULES vocabulary (Tagalog/Indonesian/Malay/Swahili + romanised Arabic/Hindi/Urdu).
# scan() folds these in as an additional substring match path with the same hit shape. Deliberately
# multi-word / high-signal so they do not fire on ordinary English text. Native-script terms live in the
# production harness, not here (ENGINE is ASCII-only). Each cue maps to a core forced-labour indicator.
MULTILINGUAL_CUES = {
    "document_retention": [  # passport/ID confiscation reported in the worker's own words
        "kinuha ang pasaporte", "hindi ibinalik ang pasaporte", "hawak ang pasaporte",
        "paspor ditahan", "paspor disita", "menahan paspor",
        "kunyang'anya pasipoti", "amechukua pasipoti",
        "iqama withheld", "confiscated iqama", "sahab al jawaz",
    ],
    "debt_bondage": [  # debt owed to the recruiter/agency (ILO indicator 4)
        "utang sa ahensya", "utang sa agent", "utang sa recruiter",
        "hutang ke agen", "potongan gaji untuk hutang", "bayar hutang dulu",
        "deni la wakala", "agent ko paisa", "dalal ko paisa",
    ],
    "recruitment_fee": [  # placement/agency fee charged to the worker (ILO C181 Art. 7)
        "bayad sa ahensya", "singil ng ahensya", "placement fee binayad",
        "biaya penempatan", "biaya agen", "bayaran ejen",
        "ada ya uajiri", "rusum al tawzif", "rusum al istiqdam",
    ],
    "wage_withholding": [  # unpaid/withheld wages (ILO C095)
        "hindi binabayaran ang sweldo", "walang sweldo", "hindi ako sinasahod",
        "gaji tidak dibayar", "belum dibayar gaji", "gaji ditahan",
        "mshahara haujalipwa", "sijalipwa mshahara", "bidun ratib", "lam yadfa al ratib",
    ],
    "restriction_of_movement": [  # confinement / cannot leave (ILO C029)
        "hindi makaalis", "bawal lumabas", "nakakulong",
        "tidak boleh keluar", "dikurung", "dilarang keluar",
        "siwezi kuondoka", "mamnu al khuruj", "mahbus",
    ],
}

# Volatile contact knowledge -- names/regulators, not memorised phone numbers. In production these come
# from a versioned contacts pack / the /api/contacts tool (see harness/_contacts.json), never from model
# memory, because numbers, URLs and intake hours change. Verify every number at deploy time.
HOTLINES = {
    "global": "IOM / ILO referral pathways; Polaris (US) 1-888-373-7888; verify the current in-country number before use",
    "US": "National Human Trafficking Hotline 1-888-373-7888 (Polaris); SMS BeFree 233733",
    "Philippines": "DMW Anti-Illegal Recruitment Branch; OWWA 24/7 OFW hotline; Blas Ople Center; verify current number via contacts pack",
    "Indonesia": "BP2MI Aduan PMI complaint portal; migrant-worker unions (e.g. SBMI); verify current number via contacts pack",
    "Nepal": "DoFE grievance desk; Foreign Employment Board; Pravasi Nepali Coordination Committee; verify current number via contacts pack",
    "Bangladesh": "BMET / Probashi Kallyan grievance desk; BNWLA legal aid; verify current number via contacts pack",
    "India": "MEA eMigrate grievance system; Indian mission labour wing at destination; verify current number via contacts pack",
    "Hong Kong": "HK Labour Department; Mission for Migrant Workers / Bethune House shelter; verify current number via contacts pack",
    "Singapore": "MOM Foreign Workforce line; TWC2 / HOME support; verify current number via contacts pack",
    "Gulf / GCC": "Home-country embassy labour attache; local labour ministry grievance line (e.g. Saudi Musaned/unified line, UAE MoHRE, Kuwait PAM); verify current number via contacts pack",
    "Lebanon": "ISF domestic-worker line; Caritas Lebanon shelter referral; verify current number via contacts pack",
    "Nigeria": "NAPTIP counter-trafficking line; verify current number via contacts pack",
    "UK": "Modern Slavery & Exploitation Helpline; NRM first responders; verify current number via contacts pack",
    "EU": "National anti-trafficking referral mechanisms and labour inspectorates; verify current number via contacts pack",
    "note": "Public hotline numbers change; in production these come from a versioned knowledge pack / tool call, not from memory. Nothing here should auto-trigger an outbound call, email, or form submission -- surface the contact and let the user act.",
}

# Named migration corridors (origin -> destination), grounded in the harness CORRIDOR_FEE_CAPS + the
# contacts pack. Corridor context drives which fee cap / regulator / embassy applies; volatile specifics
# (caps, statutes) belong in a versioned knowledge pack, not memorised here.
CORRIDORS = [
    "Philippines -> Hong Kong", "Philippines -> Saudi Arabia", "Philippines -> UAE",
    "Philippines -> Kuwait", "Philippines -> Qatar", "Philippines -> Singapore", "Philippines -> Taiwan",
    "Indonesia -> Malaysia", "Indonesia -> Hong Kong", "Indonesia -> Saudi Arabia", "Indonesia -> Taiwan",
    "Nepal -> Qatar", "Nepal -> Saudi Arabia", "Nepal -> UAE", "Nepal -> Malaysia",
    "Bangladesh -> Malaysia", "Bangladesh -> Saudi Arabia", "Bangladesh -> Qatar",
    "India -> UAE", "India -> Saudi Arabia",
    "Sri Lanka -> Lebanon", "Sri Lanka -> Saudi Arabia",
    "Ethiopia -> Lebanon", "Ethiopia -> Saudi Arabia",
    "Kenya -> Saudi Arabia", "Uganda -> Saudi Arabia",
    "Myanmar -> Thailand", "Vietnam -> Taiwan", "Cambodia -> Thailand",
    "Mexico -> United States (H-2A/H-2B)", "Jamaica -> Canada (SAWP)", "Nigeria -> Italy",
]
# High-risk sectors for migrant-worker exploitation (mirrors the harness GREP sector clusters).
SECTORS = [
    "domestic work / household service", "construction", "agriculture / plantation",
    "commercial fishing", "seafaring / maritime", "manufacturing / factory", "garment / textile",
    "food processing / meatpacking", "hospitality / hotels", "cleaning / janitorial",
    "care work / nursing / elder care", "security / guarding", "warehousing / logistics / delivery",
    "gig / platform work", "mining / quarrying", "forestry / logging",
    "beauty / nail salon / massage", "entertainment / hostess", "retail", "au pair / childcare",
    "scam compounds / online fraud (forced criminality)", "begging rings (forced criminality)",
]

# Relative acuity weights per indicator, used by severity(). Coercion-of-liberty and violence indicators
# weigh more than fee/overtime signals. risk_level() keeps its count-based bands; severity() is an
# additional, opt-in acuity score. Weights are a triage heuristic, not a legal ranking.
indicator_weights = {
    "violence": 4,
    "document_retention": 3,
    "debt_bondage": 3,
    "restriction_of_movement": 3,
    "wage_withholding": 3,
    "intimidation": 2,
    "isolation": 2,
    "recruitment_fee": 2,
    "deception": 2,
    "abuse_of_vulnerability": 2,
    "abusive_conditions": 2,
    "excessive_overtime": 1,
}


def scan(text):
    """Return the list of ILO indicators detected in `text` (deterministic, representative).

    Each hit is a dict with exactly {indicator, label, snippet, ilo_ref}. One hit per indicator (first
    match wins). Match paths, in order: English regex PATTERNS, deceptive FEE_CAMOUFLAGE labels
    (-> recruitment_fee), then the romanised MULTILINGUAL_CUES layer.

    Args:
        text: the free text to scan (a worker account, message, or contract excerpt). None is treated
            as an empty string.

    Returns:
        A list of hit dicts, each ``{"indicator", "label", "snippet", "ilo_ref"}``; empty when nothing
        matches (absence of a hit is not evidence of safety).

    Example:
        >>> hits = scan("The agency took my passport and I have not been paid for two months.")
        >>> sorted(h["indicator"] for h in hits)
        ['document_retention', 'wage_withholding']
    """
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
    for ind, cues in MULTILINGUAL_CUES.items():
        if ind in seen:
            continue
        for cue in cues:
            if cue in t:
                seen.add(ind)
                hits.append({"indicator": ind, "label": ILO_INDICATORS.get(ind, ind),
                             "snippet": cue, "ilo_ref": ILO_REFS.get(ind, "ILO Indicators of Forced Labour (2012)")})
                break
    return hits


def severity(hits):
    """Weighted acuity score for a list of scan() hits (higher = more acute).

    Sums indicator_weights over the detected indicators (unknown indicators count as 1). This does NOT
    change risk_level's bands; it is an additional signal notebooks can surface or sort on.
    """
    return sum(indicator_weights.get(h.get("indicator"), 1) for h in (hits or []))


def risk_level(hits):
    """Map a list of scan() hits to (LEVEL, why) with LEVEL in {HIGH, ELEVATED, WATCH, LOW}.

    Bands are count-based and unchanged (monotone): 0 -> LOW, 1 -> WATCH, 2-3 -> ELEVATED, 4+ -> HIGH.
    The `why` string additionally reports the weighted severity() so callers see acuity, not just count.
    """
    n = len(hits)
    s = severity(hits)
    if n >= 4:
        return ("HIGH", "Multiple forced-labour indicators present (weighted severity " + str(s) + ")")
    if n >= 2:
        return ("ELEVATED", "Several indicators present -- warrants review (weighted severity " + str(s) + ")")
    if n == 1:
        return ("WATCH", "One indicator present -- ask follow-up questions (weighted severity " + str(s) + ")")
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
    """Generate a structured chain-of-thought by asking the ILO-indicator questions of `text`.

    Walks the situation neutrally, checks each of the 12 indicators (PRESENT with its cue + ILO
    reference, or "not evident"), steps through the migration lifecycle, applies the counterfactual
    checks, and closes with the risk level. This is the same reasoning scaffold the CoT dataset encodes.

    Args:
        text: the free text to reason over (a worker account or message).

    Returns:
        A list of ``(step_number, step_text)`` tuples, in reading order, ending on the conclusion step.

    Example:
        >>> chain = generate_chain("The agency kept my passport.")
        >>> chain[0]
        (1, 'Restate the situation in neutral, non-leading terms.')
        >>> chain[-1][1].startswith("Conclusion: risk =")
        True
    """
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
