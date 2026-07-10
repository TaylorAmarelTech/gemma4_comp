"""Structured legal-reasoning walkthroughs over the vetted claim library (legal thought, not a verdict).

Taylor: "run through various scenarios using legal thought processes, common law, public interest."
This applies a DETERMINISTIC, auditable chain of legal reasoning to a worker scenario over
configs/duecare/legal_claims.json -- the 'legal assessment' truth layer the external audit calls for (its
truth type 5), sitting above observed facts / indicators / normative claims. Distinct from the model-side
reasoning-training scripts (build_reasoning_*.py, reasoning_contract.py): this is deterministic legal
analysis, not SFT data. The chain, per the audit's rule that 'no legal statement reaches a user merely
because a document was retrieved':

  1. observed facts (what the scenario states)
  2. ILO indicators matched (the 2025 eleven indicators, from the worker's perspective)
  3. applicable claims (library claims whose JURISDICTION + TOPIC fit) -- with each claim's applicability,
     temporal validity, EXCEPTIONS to resolve, and a recheck flag if the claim is stale/volatile
  4. common-law / precedent (persuasive or binding authority attached by relevance)
  5. Palermo element analysis (act / means / purpose): which are supported, inferred, or missing
  6. public-interest / worker-protective posture: resolve ambiguity for the worker's safety; what they are
     generally NOT required to do; preserve evidence
  7. uncertainty + volatile-claim recheck list + next evidence to gather

It is DETERMINISTIC (rule-based over the library) so the reasoning is inspectable and reproducible, needs
no model/keys, and NEVER asserts a criminal finding -- it surfaces a risk pattern and the checks a human
must make. Propose-only.

Run:
    python scripts/legal_reasoning.py --today 2026-07-10
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from legal_claims import due_for_recheck, load_claims  # noqa: E402

OUT = _ROOT / "reports" / "legal_reasoning_walkthroughs.json"

# ILO 2025 eleven indicators -> keyword triggers (assessed from the worker's perspective). A trailing '*'
# marks a STEM (prefix match: "threat*" -> threat/threats/threatening); everything else is matched as a
# WHOLE WORD. Whole-word matching is deliberate: plain substring containment silently fired ordinary English
# ("feel" contains "fee", "however" contains "owe", "white" contains "hit"), which corrupted the downstream
# gold CoT text -- so keywords carry an explicit stem marker only where suffix matching is actually wanted.
_INDICATOR_KEYWORDS = {
    "abuse of vulnerability": ["migrant*", "foreign", "undocumented", "irregular", "dependent", "language barrier"],
    "deception": ["different contract", "switched", "substitut*", "promised", "misled", "not what i was told"],
    "restriction of movement": ["locked", "cannot leave", "can't leave", "confined", "permission to leave", "not allowed to leave"],
    "isolation": ["phone taken", "confiscated our phones", "cannot contact", "no contact", "isolated"],
    "physical or sexual violence": ["beat*", "hit", "assault*", "violence", "violent"],
    "intimidation and threats": ["threat*", "deport*", "cancel my visa", "cancel the visa", "report me"],
    "retention of identity documents": ["passport*", "took my passport", "hold my passport", "document*", "identity card"],
    "withholding of wages": ["unpaid", "not paid", "withhold*", "wages as security", "salary held", "deduct*"],
    "debt bondage": ["debt", "loan", "repay*", "placement fee", "recruitment fee", "owe", "processing fee"],
    "abusive working and living conditions": ["squalid", "poor conditions", "housing deducted", "food deducted"],
    "excessive overtime": ["overtime", "18 hours", "eighteen hours", "no rest day", "no day off", "long hours"],
}
# Topical rule/precedent claims -> keyword triggers (definitional/international claims always apply).
_CLAIM_TOPICS = {
    "c181_recruitment_fees": ["fee", "fees", "recruit*", "placement", "charg*", "commission", "processing"],
    "ph_placement_fee": ["fee", "fees", "placement", "recruit*", "charg*", "processing"],
    "c095_wage_deductions": ["wage*", "salary", "deduct*", "withhold*", "unpaid", "pay"],
    "c189_domestic_workers": ["domestic", "housemaid", "household", "maid", "kasambahay", "live-in"],
    "hk_money_lending_cap": ["loan", "interest", "apr", "money lender", "repay*"],
    "siliadin_2005": ["domestic", "housemaid", "household", "maid", "servitude", "live-in"],
    "rantsev_2010": ["trafficked", "artiste", "cabaret", "brothel", "sexual"],
    "us_tvpa_1589": ["serious harm", "psychological", "coercion", "forced labor", "forced labour"],
    "kozminski_1988": ["serious harm", "psychological", "coercion"],
}
_ALWAYS = {"c029_definition", "c029_vs_indicators", "ilo_indicators_2025", "palermo_elements"}


def _kw_pattern(kw: str) -> str:
    """Whole-word pattern for a keyword; a trailing '*' means stem/prefix match. `(?<!\\w)`/`(?!\\w)` guard
    the boundaries so a keyword never fires inside a larger word (the 'feel'->'fee' class of false match)."""
    if kw.endswith("*"):
        return r"(?<!\w)" + re.escape(kw[:-1]) + r"\w*"
    return r"(?<!\w)" + re.escape(kw) + r"(?!\w)"


def _hits(keywords: list[str], low: str) -> list[str]:
    """Keywords whose whole-word / stem pattern matches `low` (already lowercased)."""
    return [kw for kw in keywords if re.search(_kw_pattern(kw), low)]


def match_indicators(facts_text: str) -> dict[str, list[str]]:
    low = facts_text.lower()
    out: dict[str, list[str]] = {}
    for ind, kws in _INDICATOR_KEYWORDS.items():
        hits = _hits(kws, low)
        if hits:
            out[ind] = hits
    return out


def _jurisdiction_fits(claim: dict, scenario: dict) -> bool:
    cj = claim.get("jurisdiction", "")
    if cj == "international":
        return True
    scope = {scenario.get("jurisdiction", ""), scenario.get("destination", "")}
    if cj in scope:
        return True
    # ECtHR precedents are persuasive everywhere; flag rather than exclude
    return claim.get("authority_class") == "court_precedent"


def _is_historical(claim: dict) -> bool:
    """A claim that has been explicitly superseded (build-upon: it stays in the corpus for provenance but is
    no longer the CURRENT standard). Read from superseded_by or a historical/superseded binding_status."""
    bstatus = str(claim.get("binding_status", "")).lower()
    return bool(claim.get("superseded_by")) or "historical" in bstatus or "superseded" in bstatus


def applicable_claims(scenario: dict, claims: list[dict], today: date) -> list[dict]:
    low = " ".join(scenario.get("facts", [])).lower()
    due = {c["id"] for c in due_for_recheck(claims, today)}
    out = []
    for c in claims:
        cid = c["id"]
        topical = cid in _ALWAYS or bool(_hits(_CLAIM_TOPICS.get(cid, []), low))
        if not (topical and _jurisdiction_fits(c, scenario)):
            continue
        cj = c.get("jurisdiction", "")
        binds = cj == "international" or cj in {scenario.get("jurisdiction"), scenario.get("destination")}
        historical = _is_historical(c)
        superseded_by = c.get("superseded_by")
        if historical:
            binding_here = (f"historical -- superseded by {superseded_by}; cite the successor, not this"
                            if superseded_by else "historical -- superseded; do not cite as current")
        else:
            binding_here = "binds/directly relevant" if binds else "persuasive only (different jurisdiction)"
        out.append({
            "id": cid, "text": c.get("text", ""), "jurisdiction": cj,
            "binding_here": binding_here, "status": "historical" if historical else "current",
            "superseded_by": superseded_by,
            "exceptions_to_resolve": c.get("exceptions") or [],
            "recheck": (cid in due), "caveats": c.get("caveats") or [],
        })
    # current, directly-binding, jurisdiction-specific claims first; historical/superseded ones sink to the
    # bottom so a consumer that takes the first N gets the CURRENT controlling law, never a superseded one.
    out.sort(key=lambda a: (a["status"] == "historical",
                            a["binding_here"].startswith("persuasive"),
                            a["jurisdiction"] == "international"))
    return out


def palermo_elements(indicators: dict[str, list[str]], scenario: dict) -> dict:
    low = " ".join(scenario.get("facts", [])).lower()
    act = ("recruit" in low or "agency" in low or "agent" in low or "sent to" in low or "broker" in low
           or "retention of identity documents" in indicators)
    means_inds = {"abuse of vulnerability", "deception", "intimidation and threats", "restriction of movement",
                  "debt bondage", "retention of identity documents"}
    means = bool(means_inds & indicators.keys())
    purpose_inds = {"withholding of wages", "excessive overtime", "abusive working and living conditions"}
    purpose = bool(purpose_inds & indicators.keys())
    return {
        "act": {"supported": bool(act), "note": "recruitment/harbouring/receipt inferred from the facts"},
        "means": {"supported": means, "note": "coercion/deception/abuse-of-vulnerability from matched indicators"},
        "purpose": {"supported": purpose, "note": "exploitation inferred from wage/overtime/conditions indicators"},
        "reading": ("All three Palermo elements appear supported -> a risk pattern that warrants escalation and "
                    "human review. This is NOT a criminal finding; adult trafficking requires proof of act + "
                    "means + purpose to a legal standard. For a CHILD the means element is not required.")
        if (act and means and purpose) else
        ("Not all three elements are clearly supported on these facts -- report which are supported, inferred, "
         "or missing; exploitation or a single indicator alone is insufficient for an adult trafficking finding."),
    }


def analyze(scenario: dict, claims: list[dict], today: date) -> dict:
    facts_text = " ".join(scenario.get("facts", []))
    indicators = match_indicators(facts_text)
    applic = applicable_claims(scenario, claims, today)
    elements = palermo_elements(indicators, scenario)
    recheck = [a["id"] for a in applic if a["recheck"]]
    worker_protective = []
    if "retention of identity documents" in indicators:
        worker_protective.append("A worker is generally NOT required to work to reclaim their own passport; keep copies.")
    if "debt bondage" in indicators:
        worker_protective.append("Do not pay disputed 'fees' upfront; a fee tied to being unable to leave is a red flag; verify the fee rule for this occupation + destination.")
    if "withholding of wages" in indicators:
        worker_protective.append("Keep every contract and payslip; a wage claim can usually be raised with the labour ministry or a migrant-worker NGO.")
    if "intimidation and threats" in indicators:
        worker_protective.append("An employer usually cannot themselves deport you; keep written evidence of the threat.")
    worker_protective.append("Resolve ambiguity in favour of the worker's SAFETY; prioritise a human handoff; do not confront the employer without a safety plan.")
    return {
        "scenario_id": scenario.get("id"),
        "jurisdiction": scenario.get("jurisdiction"), "destination": scenario.get("destination"),
        "worker_category": scenario.get("worker_category"),
        "observed_facts": scenario.get("facts", []),
        "indicators_matched": indicators,
        "applicable_claims": applic,
        "palermo_elements": elements,
        "public_interest_worker_protective": worker_protective,
        "uncertainty_recheck": recheck,
        "next_evidence": scenario.get("next_evidence", [
            "the worker's occupation category and destination (decides which fee/wage rule applies)",
            "dates and amounts (decides temporal validity and whether a cap is exceeded)",
            "whether the destination state has ratified the relevant convention"]),
        "_disclaimer": "Structured legal REASONING for triage, not legal advice and not a criminal determination.",
    }


# Composite / synthetic scenarios (no real PII).
SCENARIOS = [
    {"id": "ph_hsw_passport_fee", "jurisdiction": "PH", "destination": "HK",
     "worker_category": "household service worker (domestic worker)",
     "facts": ["A recruitment agency charged me a placement fee of 50000 PHP for a domestic job in Hong Kong.",
               "When I arrived they took my passport and said I must repay a loan before I can leave."]},
    {"id": "sa_wage_withholding", "jurisdiction": "PH", "destination": "SA",
     "worker_category": "construction worker",
     "facts": ["My employer switched my contract to a lower salary after I arrived (a different contract).",
               "He withholds two months of wages as security and I work eighteen hours with no rest day."]},
    {"id": "hk_debt_loan", "jurisdiction": "HK", "destination": "HK",
     "worker_category": "domestic worker",
     "facts": ["A money lender charges me interest of about 68% APR on a recruitment loan.",
               "All my salary goes to repay it and the agent holds my passport as security."]},
    {"id": "us_psychological_coercion", "jurisdiction": "US", "destination": "US",
     "worker_category": "farm worker",
     "facts": ["My boss threatens to report me and says I will suffer serious harm if I stop working.",
               "There is no physical restraint but I feel I cannot leave because of the threats and my debt."]},
]


def render(a: dict) -> str:
    lines = [f"=== {a['scenario_id']}  ({a['worker_category']}; {a['jurisdiction']} -> {a['destination']}) ===",
             "OBSERVED FACTS:"]
    lines += [f"  - {f}" for f in a["observed_facts"]]
    lines.append("ILO INDICATORS MATCHED (2025, victim-perspective):")
    lines += [f"  - {ind}  (via: {', '.join(hits)})" for ind, hits in a["indicators_matched"].items()] or ["  (none)"]
    lines.append("APPLICABLE CLAIMS (each must pass applicability + temporal + exception checks):")
    for c in a["applicable_claims"]:
        flag = "  [RECHECK]" if c["recheck"] else ""
        lines.append(f"  - {c['id']} ({c['jurisdiction']}, {c['binding_here']}){flag}")
        if c["exceptions_to_resolve"]:
            lines.append(f"      exceptions to resolve: {c['exceptions_to_resolve'][0]}")
    el = a["palermo_elements"]
    lines.append("PALERMO ELEMENT ANALYSIS (risk pattern, not a finding):")
    for k in ("act", "means", "purpose"):
        lines.append(f"  - {k}: {'supported' if el[k]['supported'] else 'not clearly supported'} -- {el[k]['note']}")
    lines.append(f"  => {el['reading']}")
    lines.append("PUBLIC-INTEREST / WORKER-PROTECTIVE:")
    lines += [f"  - {w}" for w in a["public_interest_worker_protective"]]
    if a["uncertainty_recheck"]:
        lines.append(f"VERIFY (volatile/stale claims): {', '.join(a['uncertainty_recheck'])}")
    lines.append("NEXT EVIDENCE: " + "; ".join(a["next_evidence"]))
    lines.append(a["_disclaimer"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic legal-reasoning walkthroughs over the claim library.")
    ap.add_argument("--today", default=None, help="ISO date for freshness (default: today)")
    args = ap.parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else date.today()
    claims = load_claims()
    results = [analyze(s, claims, today) for s in SCENARIOS]
    for a in results:
        print(render(a)); print()
    OUT.write_text(json.dumps({"_synthetic": True, "_propose_only": True, "as_of": str(today),
                               "walkthroughs": results}, indent=2), encoding="utf-8")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
