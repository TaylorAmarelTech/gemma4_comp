"""Trafficking-domain relevance scoring for acquired chunks -- a confidence gate
so broad harvested gov/NGO pages don't dilute the trafficking RAG corpus.

Deterministic + offline. Scores each chunk from INDEPENDENT signals that have to
agree: domain entities (ILO conventions / corridors / statutes, via the graph
gazetteer), a curated trafficking / forced-labour / migrant-protection lexicon,
and the source candidate's own signal tags. A chunk with no domain signal at all
scores 'low' (gated out by default); the rest are tiered + ranked for review.

Inferred relevance is a DRAFT, never authoritative -- the gate removes obvious
off-topic content and orders the remainder; a human still curates. (Pattern: the
"confidence from multiple agreeing signals, human confirms" idea, applied to
corpus curation rather than purpose inference.)
"""
from __future__ import annotations

import re

from .ambiguity import domain_sense
from .graph import extract_entities

# Curated lexicon -- one entry per concept FAMILY (distinct families that hit are
# what count as independent evidence, not raw keyword volume). Expanded 2026-06-06
# (research-verified canonical ILO/UNODC phrasings + employer euphemisms).
_LEXICON: dict[str, list[str]] = {
    "recruitment_fees": [r"recruitment fee", r"placement fee", r"placement charge",
                         r"recruitment cost", r"service charge", r"processing fee",
                         r"worker-?paid", r"zero[- ]fee", r"fee[- ]free", r"employer pays principle"],
    "document_retention": [r"passport (?:retention|confiscat\w+|withholding)", r"identity document",
                           r"withh\w+ (?:passport|document)", r"document retention",
                           r"safekeeping of (?:passports?|documents?)"],
    "debt_bondage": [r"debt bondage", r"bonded labou?r", r"inherited debt",
                     r"work(?:ing)? off (?:a |the )?debt"],
    "wage_theft": [r"wage (?:theft|deduction|withhold\w+)", r"unpaid wages?", r"salary deduction",
                   r"non-?payment of wages?", r"unauthori[sz]ed deduction", r"withheld (?:salary|wages?)"],
    "contract_substitution": [r"contract substitution", r"substitut\w+ contract",
                              r"double contract", r"contract switch\w+"],
    "forced_labour_coercion": [r"forced labou?r", r"compulsory labou?r", r"involuntary servitude",
                               r"menace of (?:any )?penalty", r"coerc", r"work(?:ed)? against (?:his|her|their) will"],
    "restricted_movement": [r"\bkafala\b", r"sponsorship system", r"exit (?:permit|visa)",
                            r"no[- ]objection certificate", r"freedom of movement",
                            r"unable to (?:leave|change) (?:job|employer)"],
    "excessive_overtime": [r"excessive overtime", r"forced overtime", r"compulsory overtime",
                           r"no (?:rest|weekly) day"],
    "deception": [r"deceptive recruitment", r"false promise", r"fraudulent (?:offer|recruitment)",
                  r"misled about", r"bait[- ]and[- ]switch"],
    "isolation_confinement": [r"locked (?:in|inside)", r"not (?:allowed|permitted) to leave",
                              r"confined to", r"forcibly (?:held|detained)", r"domestic servitude"],
    "threats_retaliation": [r"threat\w* of (?:deportation|violence|harm)", r"retaliat\w+",
                            r"threat\w* to report", r"intimidat\w+", r"blackmail"],
    "trafficking": [r"traffick", r"human exploitation", r"modern slavery", r"sexual exploitation",
                    r"smuggl\w+ of (?:persons|migrants)", r"migrant smuggling",
                    r"exploitation of (?:workers|persons|migrants)"],
    "migrant": [r"migrant worker", r"overseas worker", r"domestic worker", r"foreign worker",
                r"labou?r migration", r"recruitment agenc", r"manpower agenc"],
    "sector": [r"\bseafarer", r"fishing vessel", r"construction worker"],
    "remedy": [r"grievance mechanism", r"complaint mechanism", r"victim (?:protection|identification)",
               r"non-?punishment", r"hotline", r"shelter"],
}
_COMPILED = {fam: [re.compile(p, re.I) for p in pats] for fam, pats in _LEXICON.items()}

_SIGNAL_SET = {
    "debt_bondage", "forced_labor", "forced_labour", "trafficking", "recruitment_fee",
    "passport_retention", "wage_theft", "immigration_status_control",
    "worker_voice_grievance", "referral", "contract_substitution",
}

TIER_RANK = {"low": 0, "medium": 1, "high": 2}


def relevance(text: str, *, signals: list[str] | None = None) -> dict:
    """Score one chunk. Returns ``{tier, score, entities, families, signal_tags}``.
    high  = an entity + >=2 lexicon families, or >=3 families (strong agreement)
    medium= IN-TEXT domain evidence (>=1 entity or lexicon family)
    low   = no in-text domain evidence (off-topic -> gated out by default).

    Source signal tags only contribute to ``score`` (ranking within a tier), never
    to the tier itself -- a generic page from a trafficking-adjacent domain must
    earn promotion on its own text, not on an inherited tag."""
    t = text or ""
    ents = sorted(extract_entities(t))
    fams = sorted(fam for fam, pats in _COMPILED.items() if any(p.search(t) for p in pats))
    sig = sorted(set(signals or []) & _SIGNAL_SET)
    score = 2 * len(ents) + 2 * len(fams) + len(sig)
    if (ents and len(fams) >= 2) or len(fams) >= 3:
        tier = "high"
    elif ents or fams:
        tier = "medium"
    else:
        tier = "low"
    return {"tier": tier, "score": score, "entities": ents, "families": fams, "signal_tags": sig}


def passes(text: str, *, signals: list[str] | None = None, min_tier: str = "medium") -> bool:
    """True if a chunk's relevance tier is at least ``min_tier``."""
    return TIER_RANK[relevance(text, signals=signals)["tier"]] >= TIER_RANK.get(min_tier, 1)


def relevance_with_domain_sense(
    text: str, *, signals: list[str] | None = None, demote_collisions: bool = True,
) -> dict:
    """``relevance()`` augmented with cross-domain word-sense disambiguation.

    A keyword-relevance gate is blind to MEANING: a finance page about "10-year
    bond yields" matches the debt-*bondage* corpus on the bare word "bond". This
    wrapper adds the ``ambiguity.domain_sense`` verdict and:

    * attaches ``domain_sense`` (the full declared-loss report) for the curator;
    * sets ``review_flag`` when an ambiguous keyword resolves to a competing domain;
    * nudges ``score`` down by the number of off-domain senses so wrong-sense
      chunks sort below clean ones within a tier;
    * DEMOTES to ``low`` (gated out) only the conservative case: a borderline
      ``medium`` chunk with no hard entity whose domain hook is purely an
      off-domain collision word -- e.g. "freedom of movement of capital ... bond
      market" falsely hitting the movement family. Strong chunks (entity + families)
      are never demoted on a sense signal alone.

    ``relevance()`` itself is unchanged; callers opt in to sense-awareness."""
    base = relevance(text, signals=signals)
    sense = domain_sense(text)
    out = dict(base)
    out["domain_sense"] = sense
    out["review_flag"] = bool(sense["collision"])
    out["score"] = base["score"] - sense["n_offdomain"]
    demoted = bool(
        demote_collisions and sense["collision"]
        and base["tier"] == "medium" and not base["entities"]
    )
    if demoted:
        out["tier"] = "low"
    out["demoted_for_collision"] = demoted
    return out
