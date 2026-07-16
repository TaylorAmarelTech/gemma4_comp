"""RuleCards: turn DueCare's hard-coded GREP indicator rules into typed, auditable
supervision objects.

This implements the central recommendation of the 2026-07 harness/finetuning
deep-research blueprint: DueCare's hard-coded intelligence should not be a black
box of regexes, and it must never be mistaken for ground truth. Each GREP rule
becomes a ``RuleCard`` -- an auditable object carrying its authoritative sources,
antecedent, consequence, inferred role, and (crucially) the *witness family* it
belongs to.

The load-bearing idea is correlated witnesses: ten rules derived from the same
legal instrument (e.g. the Palermo Protocol) are ten correlated votes, not ten
independent confirmations. ``independence_report`` measures this directly from
the real rule deck so downstream weak supervision never treats a family of
same-source rules as independent evidence.

Pure stdlib, no model calls. The compiler reads the real ``GREP_RULES`` data.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "duecare.rulecards.v1"

# --- Role taxonomy (from the blueprint) --------------------------------------
# A GREP pattern rule is a fallible vote and a fact emitter. It is never, by
# itself, a runtime invariant or a conclusion: a match is grounds for inquiry,
# not proof or action. Other roles (generator, oracle, judge criterion,
# retrieval policy) describe rule kinds GREP rules are not, and are listed here
# so a reviewer can see what a card is deliberately NOT classified as.
ROLE_LABELING_FUNCTION = "labeling_function"
ROLE_FEATURE_EXTRACTOR = "feature_extractor"
ROLE_HARD_INVARIANT = "hard_invariant"
ALL_ROLES = (
    ROLE_HARD_INVARIANT,
    ROLE_LABELING_FUNCTION,
    ROLE_FEATURE_EXTRACTOR,
    "generator",
    "evaluation_oracle",
    "judge_criterion",
    "retrieval_policy",
)

# Authoritative-instrument extraction. Ordered so specific national statutes are
# captured alongside the international instruments.
_INSTRUMENT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"ILO\s+[CRP]\d{3}", "ilo_instrument"),
    (r"Palermo(?:\s+Protocol)?", "palermo_protocol"),
    (r"ICRMW", "icrmw"),
    (r"\bTVPA\b", "us_tvpa"),
    (r"CoE\s+Warsaw|Warsaw\s+Convention|Anti-Trafficking\s+Convention", "coe_warsaw"),
    (r"RA\s+\d{4,5}", "philippines_ra"),
    (r"Cap\.\s*\d+", "hk_cap"),
    (r"OJK", "indonesia_ojk"),
    (r"POEA|DMW|BP2MI", "origin_state_labor_authority"),
    (r"UNODC", "unodc_guidance"),
)

# Jurisdiction inference from instrument tokens. Bounded + auditable: unknown
# tokens contribute no jurisdiction rather than a guess.
_JURISDICTION_HINTS: tuple[tuple[str, str], ...] = (
    (r"Cap\.\s*\d+|Hong\s*Kong|\bHK\b", "HK"),
    (r"RA\s+\d{4,5}|POEA|DMW|Philippines|\bPH\b", "PH"),
    (r"OJK|Indonesia|\bID\b", "ID"),
    (r"Singapore|\bSG\b|Moneylenders\s+Act", "SG"),
    (r"\bTVPA\b|United\s+States|\bUS\b", "US"),
    (r"Nepal|\bNP\b", "NP"),
    (r"Bangladesh|\bBD\b", "BD"),
    (r"Kuwait|\bKW\b", "KW"),
    (r"Saudi|\bKSA\b|\bSA\b", "SA"),
)

_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass(frozen=True)
class RuleCard:
    """An auditable supervision object derived from one GREP indicator rule."""

    rule_id: str
    schema_version: str
    source_rule_sha256: str
    category: str
    severity: str
    authoritative_sources: list[str]
    jurisdictions: list[str]
    antecedent: dict[str, Any]
    consequence: dict[str, Any]
    roles: list[str]
    witness_family: str
    calibration_gaps: list[str]
    candidate_invariant_review: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rule_sha256(rule: dict[str, Any]) -> str:
    payload = repr(sorted((k, repr(v)) for k, v in rule.items()))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_authoritative_sources(citation: str) -> list[str]:
    """Return the normalized set of legal instruments a citation anchors on.

    Distinct specific instruments (e.g. "ILO C029" vs "ILO C181") stay separate,
    so the count reflects distinct authorities, not raw string hits.
    """
    found: list[str] = []
    text = citation or ""
    for pattern, family in _INSTRUMENT_PATTERNS:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            token = re.sub(r"\s+", " ", match).strip()
            if family == "ilo_instrument":
                normalized = token.upper()
            elif family == "philippines_ra":
                normalized = re.sub(r"\s+", " ", token).upper()
            elif family == "hk_cap":
                normalized = "HK " + re.sub(r"\s+", " ", token)
            else:
                normalized = family
            if normalized not in found:
                found.append(normalized)
    return sorted(found)


def infer_jurisdictions(citation: str) -> list[str]:
    text = citation or ""
    hits: list[str] = []
    for pattern, code in _JURISDICTION_HINTS:
        if re.search(pattern, text, flags=re.IGNORECASE) and code not in hits:
            hits.append(code)
    return sorted(hits)


def _witness_family(sources: list[str], category: str) -> str:
    """The correlation anchor: the strongest shared authority, else the category.

    Rules that share a primary instrument are correlated witnesses. When a rule
    cites no recognized instrument it falls back to its category so it still
    joins a family rather than counting as spuriously independent.
    """
    if sources:
        return f"source:{sources[0]}"
    return f"category:{category}"


def _classify_roles(rule: dict[str, Any]) -> list[str]:
    """Every GREP rule is a fallible vote (labeling function) and a fact emitter.

    None are auto-promoted to hard invariants: a pattern match is grounds for
    inquiry, not proof or action. This deliberately conservative classification
    is the blueprint's point.
    """
    return [ROLE_LABELING_FUNCTION, ROLE_FEATURE_EXTRACTOR]


def _calibration_gaps(rule: dict[str, Any]) -> list[str]:
    """What an auditable RuleCard should carry that a raw GREP rule does not."""
    gaps = [
        "expected_precision_recall_unknown",
        "no_unit_test_counterexamples",
        "owner_and_last_validation_unrecorded",
    ]
    if not (rule.get("citation") or "").strip():
        gaps.append("missing_authoritative_source")
    return gaps


def compile_rule(rule: dict[str, Any], *, category: str) -> RuleCard:
    """Compile one raw GREP rule dict into a typed RuleCard. Pure."""
    citation = str(rule.get("citation") or "")
    sources = extract_authoritative_sources(citation)
    severity = str(rule.get("severity") or "unknown")
    antecedent = {
        "patterns": list(rule.get("patterns") or []),
        "all_required": bool(rule.get("all_required")),
        "min_capture_value": rule.get("min_capture_value"),
    }
    consequence = {
        "severity": severity,
        "indicator": str(rule.get("indicator") or "").strip(),
        "citation": citation,
    }
    return RuleCard(
        rule_id=str(rule.get("rule") or ""),
        schema_version=SCHEMA_VERSION,
        source_rule_sha256=_rule_sha256(rule),
        category=category,
        severity=severity,
        authoritative_sources=sources,
        jurisdictions=infer_jurisdictions(citation),
        antecedent=antecedent,
        consequence=consequence,
        roles=_classify_roles(rule),
        witness_family=_witness_family(sources, category),
        calibration_gaps=_calibration_gaps(rule),
        candidate_invariant_review=severity == "critical",
    )


def compile_deck(
    rules: list[dict[str, Any]], categories: list[str] | None = None
) -> list[RuleCard]:
    """Compile a full GREP rule list into a RuleCard deck.

    ``categories`` is an optional per-rule category label (same length as
    ``rules``); when absent every card is ``uncategorized``.
    """
    if categories is not None and len(categories) != len(rules):
        raise ValueError("categories length must match rules length")
    cards: list[RuleCard] = []
    for index, rule in enumerate(rules):
        category = categories[index] if categories else "uncategorized"
        cards.append(compile_rule(rule, category=category))
    return cards


def effective_witness_count(family_sizes: list[int], rho: float) -> float:
    """Design-effect effective independent-witness count over correlated families.

    Applies the blueprint's equal-correlation design effect within each witness
    family and sums across families (treated as mutually independent):

        m_eff(family) = m / (1 + (m - 1) * rho)

    ``rho`` is the assumed within-family vote correlation in [0, 1]. rho=0 means
    every rule is an independent witness (sum = total rules); rho=1 means each
    family collapses to a single witness (sum = family count). Reporting a range
    of rho is honest because rho is an assumption, not a measured constant.
    """
    rho = min(1.0, max(0.0, rho))
    total = 0.0
    for size in family_sizes:
        if size <= 0:
            continue
        total += size / (1.0 + (size - 1) * rho)
    return round(total, 2)


def independence_report(
    cards: list[RuleCard], rho_grid: tuple[float, ...] = (0.5, 0.7, 0.9)
) -> dict[str, Any]:
    """Measure how many *independent* witness families the deck really has.

    The headline is effective_independent_families vs total_rules: a large gap
    means the deck's apparent breadth is concentrated on a few shared legal
    anchors, so downstream weak supervision must down-weight correlated votes.
    ``effective_witnesses_by_rho`` applies the design-effect formula so the
    structural family count (the rho=1 bound) is shown alongside softer
    correlation assumptions.
    """
    total = len(cards)
    by_family: dict[str, list[str]] = defaultdict(list)
    by_source: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    for card in cards:
        by_family[card.witness_family].append(card.rule_id)
        by_category[card.category] += 1
        for source in card.authoritative_sources:
            by_source[source] += 1
    families = {
        name: {"rule_count": len(ids), "rule_ids": sorted(ids)}
        for name, ids in by_family.items()
    }
    family_sizes = sorted((len(ids) for ids in by_family.values()), reverse=True)
    largest = max(family_sizes) if family_sizes else 0
    top5 = sum(family_sizes[:5])
    concentration = round(top5 / total, 4) if total else 0.0
    effective_by_rho = {
        f"rho_{rho}": effective_witness_count(family_sizes, rho) for rho in rho_grid
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "total_rules": total,
        "effective_independent_families": len(by_family),
        "reduction_ratio": round(len(by_family) / total, 4) if total else 0.0,
        "largest_family_rule_count": largest,
        "top5_family_concentration": concentration,
        "effective_witnesses_by_rho": effective_by_rho,
        "effective_witnesses_note": (
            "Design-effect estimate m/(1+(m-1)*rho) per witness family summed across "
            "families. rho is an assumed within-family vote correlation; the "
            f"structural family count ({len(by_family)}) is the rho=1 lower bound and "
            f"the total rule count ({total}) is the rho=0 upper bound."
        ),
        "families": families,
        "rules_per_authoritative_source": dict(by_source.most_common()),
        "rules_per_category": dict(by_category.most_common()),
        "interpretation": (
            f"{total} rules resolve to {len(by_family)} correlated-witness families; "
            f"the largest single family holds {largest} rules and the top five hold "
            f"{int(concentration * 100)}% of the deck. Treat same-family rules as "
            "correlated votes, not independent confirmations, in weak supervision."
        ),
    }


def deck_summary(cards: list[RuleCard]) -> dict[str, Any]:
    """Aggregate roll-up over a compiled deck. Pure, aggregate-only."""
    severities = Counter(card.severity for card in cards)
    with_sources = sum(1 for card in cards if card.authoritative_sources)
    jurisdictioned = sum(1 for card in cards if card.jurisdictions)
    review_candidates = sum(1 for card in cards if card.candidate_invariant_review)
    return {
        "schema_version": SCHEMA_VERSION,
        "total_cards": len(cards),
        "severity_counts": dict(
            sorted(severities.items(), key=lambda kv: -_SEVERITY_RANK.get(kv[0], 0))
        ),
        "cards_with_authoritative_source": with_sources,
        "cards_missing_source": len(cards) - with_sources,
        "cards_with_inferred_jurisdiction": jurisdictioned,
        "candidate_invariant_review_count": review_candidates,
        "universal_calibration_gaps": [
            "expected_precision_recall_unknown",
            "no_unit_test_counterexamples",
            "owner_and_last_validation_unrecorded",
        ],
    }
