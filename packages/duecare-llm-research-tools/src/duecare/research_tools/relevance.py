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

from .graph import extract_entities

# Curated lexicon -- one entry per concept FAMILY (distinct families that hit are
# what count as independent evidence, not raw keyword volume).
_LEXICON: dict[str, list[str]] = {
    "fees": [r"recruitment fee", r"placement fee", r"placement charge",
             r"worker-?paid", r"zero[- ]fee", r"fee[- ]free", r"no (?:worker-paid )?fees"],
    "documents": [r"passport retention", r"passport confiscat", r"identity document",
                  r"withh\w+ (?:passport|document)", r"document retention"],
    "coercion": [r"debt bondage", r"bonded labou?r", r"forced labou?r",
                 r"compulsory (?:overtime|labou?r)", r"coerc", r"involuntary servitude"],
    "wages": [r"wage (?:theft|deduction|withhold)", r"unpaid wage", r"salary deduction",
              r"non-?payment of wages?", r"unauthori[sz]ed deduction"],
    "trafficking": [r"traffick", r"human exploitation", r"modern slavery",
                    r"smuggl\w+ of (?:persons|migrants)", r"exploitation of (?:workers|persons)"],
    "migrant": [r"migrant worker", r"overseas worker", r"domestic worker", r"foreign worker",
                r"labou?r migration", r"recruitment agenc", r"manpower agenc"],
    "mobility": [r"\bkafala\b", r"sponsorship system", r"contract substitution",
                 r"freedom of movement", r"exit (?:permit|visa)"],
    "sector": [r"\bseafarer", r"fishing vessel", r"domestic servitude", r"construction worker"],
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
