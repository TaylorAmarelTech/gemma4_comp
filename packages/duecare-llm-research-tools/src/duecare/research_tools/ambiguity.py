"""Domain-sense / cross-domain-collision detection for acquired trafficking text.

The representation-loss thesis has a second branch: not only are documents
flattened into simplified text, MEANINGS are flattened into ambiguous tokens. A
word like ``bond`` collapses debt-*bondage* (our domain), a *Treasury* bond
(finance), a covalent *bond* (chemistry), and a bail *bond* (legal-surety) into
one surface form. Our acquisition pipeline scrapes arbitrary public pages, so a
finance page about "10-year bond yields" keyword-matches a debt-*bondage* corpus
and silently dilutes it -- a "cross-domain retrieval collision".

This module scores, for each genuinely-ambiguous bare term in a chunk, whether it
is used in the TARGET (trafficking / labour-rights) sense or a competing-domain
sense, by counting nearby disambiguating anchors. It is the deterministic engine
behind both a curation gate (``relevance.relevance_with_domain_sense``) and a
grading dimension (``domain_sense_resolution``).

Scope note: we only scrutinise the *bare ambiguous form* (``\bbond\b``). Unambiguous
domain forms ("bonded labour", "debt bondage") are already handled by the
relevance lexicon and are intentionally NOT collision terms here.

Deterministic, offline, stdlib only (re). Declared, auditable output -- every
verdict carries its hit counts so a curator can see why.
"""
from __future__ import annotations

import re

# Each ambiguous term maps to: the short label of its TARGET (trafficking) sense,
# the anchor tokens that evidence that sense, and the competing OFF-domain senses
# with their own anchors. Anchors are matched as lowercased substrings (so
# "recruit" catches recruiter/recruitment); terms are matched as whole words.
COLLISION_TERMS: dict[str, dict] = {
    "bond": {
        "sense": "debt_bondage",
        "target": ["debt", "bondage", "bonded", "repay", "recruit", "passport",
                   "worker", "labour", "labor", "wage", "deduct", "advance", "loan"],
        "off": {
            "finance": ["yield", "treasury", "coupon", "maturity", "issuer",
                        "investor", "interest rate", "portfolio", "securities", "bp"],
            "chemistry": ["covalent", "molecul", "atom", "hydrogen", "ionic", "electron"],
            "legal_surety": ["bail", "surety", "posted bond", "bond hearing", "defendant"],
        },
    },
    "broker": {
        "sense": "labour_broker",
        "target": ["labour", "labor", "recruit", "manpower", "agency", "worker",
                   "migrant", "placement", "informal", "middleman"],
        "off": {
            "finance": ["stock", "mortgage", "insurance", "real estate", "brokerage",
                        "shares", "trading", "commission on"],
        },
    },
    "sponsor": {
        "sense": "kafala_sponsor",
        "target": ["kafala", "employer", "visa", "exit permit", "no-objection",
                   "transfer", "domestic worker", "gulf", "tie", "permission to leave"],
        "off": {
            "events_media": ["event", "advertis", "brand", "logo", "tournament",
                             "team", "sponsorship deal", "title sponsor"],
            "research": ["clinical trial", "study sponsor", "funding agency", "grant"],
        },
    },
    "charge": {
        "sense": "recruitment_fee",
        "target": ["fee", "recruit", "placement", "worker", "deduct", "training",
                   "medical", "migrant", "applicant", "paid by"],
        "off": {
            "electrical": ["battery", "voltage", "capacitor", "coulomb", "amp", "watt"],
            "criminal": ["arrest", "indict", "prosecut", "felony", "police", "convict"],
            "military": ["cavalry", "infantry", "the hill", "bayonet"],
        },
    },
    "hold": {
        "sense": "document_withholding",
        "target": ["passport", "document", "withhold", "retain", "confiscat",
                   "identity", "wages", "salary", "until the contract"],
        "off": {
            "logistics": ["cargo", "vessel", "container", "ship's", "freight"],
            "telecom": ["on hold", "call", "phone", "line", "dial"],
            "finance": ["the stock", "shares", "position", "portfolio"],
        },
    },
    "agent": {
        "sense": "recruitment_agent",
        "target": ["recruit", "manpower", "placement", "agency", "labour", "labor",
                   "migrant", "worker", "subagent", "broker"],
        "off": {
            "software": ["ai agent", "autonomous", "llm", "tool call", "software",
                         "chatbot", "api"],
            "chemistry": ["reagent", "chemical", "cleaning", "reducing", "oxidiz"],
            "espionage": ["intelligence", "spy", "covert", "operative", "handler"],
        },
    },
    "traffick": {
        "sense": "human_trafficking",
        "target": ["human", "person", "forced", "labour", "labor", "sexual",
                   "exploit", "victim", "smuggl", "migrant", "modern slavery"],
        "off": {
            "drugs": ["drug", "narcotic", "cocaine", "heroin", "cartel", "substance"],
            "data_network": ["data", "network", "bandwidth", "web traffic", "packets"],
            "arms": ["weapon", "arms", "firearm", "ammunition", "smuggling of arms"],
        },
    },
    "exploitation": {
        "sense": "labour_exploitation",
        "target": ["labour", "labor", "worker", "forced", "sexual", "victim",
                   "traffick", "migrant", "servitude"],
        "off": {
            "resources": ["oil", "mineral", "resource extraction", "mining", "reservoir"],
            "software": ["vulnerabilit", "cve", "payload", "buffer", "zero-day"],
        },
    },
    "domestic": {
        "sense": "domestic_worker",
        "target": ["worker", "servitude", "household", "maid", "helper", "live-in",
                   "employer", "chores"],
        "off": {
            "economics": ["gdp", "domestic product", "domestic policy", "domestic market"],
            "aviation": ["flight", "airline", "terminal", "domestic route"],
        },
    },
}

_TERM_RE = {t: re.compile(r"\b" + re.escape(t) + (r"\w*\b" if t == "traffick" else r"\b"), re.I)
            for t in COLLISION_TERMS}


def _count_anchors(low: str, anchors: list[str]) -> int:
    """How many distinct anchor phrases from ``anchors`` appear in ``low`` (already
    lowercased). Distinct presence, not total frequency -- breadth of evidence."""
    return sum(1 for a in anchors if a in low)


def domain_sense(text: str) -> dict:
    """Resolve the active sense of each ambiguous term present in ``text``.

    Returns a declared-loss report::

        {
          "terms": [{"term","sense","target_hits","offdomain_hits",
                     "offdomain_label","dominant"}],   # dominant: target|offdomain|unresolved
          "n_target": int, "n_offdomain": int, "n_unresolved": int,
          "net": n_target - n_offdomain,
          "offdomain_labels": [str],   # competing domains that won at least once
          "collision": bool,           # >=1 term resolves OFF-domain with zero target support
        }

    ``collision`` is the curator-facing red flag: the chunk earns a domain keyword
    only through a competing-domain meaning (e.g. a finance "bond" page), so it is
    a likely false-positive ingest into the trafficking corpus."""
    t = text or ""
    low = t.lower()
    terms: list[dict] = []
    n_target = n_off = n_unresolved = 0
    offdomain_labels: set[str] = set()
    collision = False

    for term, spec in COLLISION_TERMS.items():
        if not _TERM_RE[term].search(t):
            continue
        target_hits = _count_anchors(low, spec["target"])
        best_label, best_off = None, 0
        for label, anchors in spec["off"].items():
            h = _count_anchors(low, anchors)
            if h > best_off:
                best_label, best_off = label, h

        if target_hits > best_off:
            dominant = "target"
            n_target += 1
        elif best_off > target_hits:
            dominant = "offdomain"
            n_off += 1
            if best_label:
                offdomain_labels.add(best_label)
            if target_hits == 0:
                collision = True       # off-domain meaning with NO target support
        else:
            dominant = "unresolved"    # tie (incl. bare 0-0): genuinely ambiguous here
            n_unresolved += 1

        terms.append({
            "term": term, "sense": spec["sense"],
            "target_hits": target_hits, "offdomain_hits": best_off,
            "offdomain_label": best_label if dominant == "offdomain" else None,
            "dominant": dominant,
        })

    return {
        "terms": terms,
        "n_target": n_target, "n_offdomain": n_off, "n_unresolved": n_unresolved,
        "net": n_target - n_off,
        "offdomain_labels": sorted(offdomain_labels),
        "collision": collision,
    }


def is_offdomain(text: str) -> bool:
    """True when the text uses an ambiguous domain keyword purely in a competing
    domain's sense -- a likely cross-domain false-positive for the corpus."""
    return domain_sense(text)["collision"]
