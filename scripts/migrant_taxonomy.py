#!/usr/bin/env python3
"""Migrant-labour taxonomy: industries, skill levels, problems, and source ranking.

This is the categorisation + ranking layer over the licensed-entity catalogue.
It answers three questions the raw catalogue cannot:

1. **What KIND of labour is each industry?** -- skill level (unskilled /
   semi-skilled / skilled / mixed), broad sector, and a trafficking RISK TIER
   (1 severe .. 3 baseline). See ``INDUSTRY_PROFILES``.
2. **What problems do workers in it face?** -- each industry maps to the
   concrete abuses migrants report, and each abuse maps to one of the ILO's 11
   indicators of forced labour. See ``PROBLEMS`` + ``ILO_INDICATORS``.
3. **Which catalogued registries should we pull FIRST?** -- ``rank_sources``
   scores each source by (industry risk) x (data-pull readiness), so the
   highest-risk + most-pullable registries float to the top of the work queue.

Pure data + pure functions; no I/O, no network. Imported by the CLI report and
by tests. Aligns with DueCare's existing ILO-indicator vocabulary so the
taxonomy and the safety harness speak the same language.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

_ROOT = Path(__file__).resolve().parents[1]
_CATALOG = _ROOT / "configs" / "duecare" / "research_monitor" / "licensed_entity_sources.yaml"

# ---------------------------------------------------------------------------
# ILO 11 indicators of forced labour (the canonical backbone)
# ---------------------------------------------------------------------------

ILO_INDICATORS: tuple[str, ...] = (
    "abuse_of_vulnerability", "deception", "restriction_of_movement", "isolation",
    "physical_sexual_violence", "intimidation_threats", "retention_of_documents",
    "withholding_of_wages", "debt_bondage", "abusive_conditions", "excessive_overtime",
)

# ---------------------------------------------------------------------------
# The concrete problems migrant workers report, mapped onto ILO indicators
# ---------------------------------------------------------------------------

#: problem_id -> (label, ilo_indicator, severity 1-3, description)
PROBLEMS: dict[str, dict] = {
    "excessive_recruitment_fees": {
        "label": "Excessive / illegal recruitment fees",
        "ilo_indicator": "debt_bondage", "severity": 3,
        "description": "Worker charged fees beyond the legal cap (often many months' wages), creating debt before work begins."},
    "contract_substitution": {
        "label": "Contract substitution",
        "ilo_indicator": "deception", "severity": 3,
        "description": "Signed terms (wage, role, hours, location) are swapped for worse ones on or after arrival."},
    "passport_confiscation": {
        "label": "Passport / ID confiscation",
        "ilo_indicator": "retention_of_documents", "severity": 3,
        "description": "Employer or agent holds the worker's passport/identity documents, trapping them."},
    "wage_theft": {
        "label": "Wage theft / unpaid or withheld wages",
        "ilo_indicator": "withholding_of_wages", "severity": 3,
        "description": "Wages unpaid, delayed, or withheld as a retention mechanism."},
    "illegal_deductions": {
        "label": "Illegal wage deductions",
        "ilo_indicator": "withholding_of_wages", "severity": 2,
        "description": "Unlawful deductions for food, housing, tools, or 'repayment' that strip take-home pay."},
    "debt_bondage": {
        "label": "Debt bondage",
        "ilo_indicator": "debt_bondage", "severity": 3,
        "description": "Worker bonded to repay an inflated or open-ended debt to recruiter, lender, or employer."},
    "sponsorship_tie": {
        "label": "Sponsorship / kafala tie restricting exit",
        "ilo_indicator": "restriction_of_movement", "severity": 3,
        "description": "Immigration status bound to one employer who can block transfer or exit."},
    "movement_restriction": {
        "label": "Restriction of movement / confinement",
        "ilo_indicator": "restriction_of_movement", "severity": 3,
        "description": "Worker confined to site/accommodation or barred from leaving freely."},
    "isolation": {
        "label": "Isolation",
        "ilo_indicator": "isolation", "severity": 2,
        "description": "Remote worksite, confiscated phone, or language isolation cutting off help."},
    "forced_overtime": {
        "label": "Forced / excessive overtime, no rest days",
        "ilo_indicator": "excessive_overtime", "severity": 2,
        "description": "Hours far beyond legal limits, no weekly rest, under threat or coercion."},
    "substandard_housing": {
        "label": "Abusive living / working conditions",
        "ilo_indicator": "abusive_conditions", "severity": 2,
        "description": "Unsafe, overcrowded, or degrading accommodation and work environment."},
    "threats_deportation": {
        "label": "Threats / intimidation (incl. deportation)",
        "ilo_indicator": "intimidation_threats", "severity": 3,
        "description": "Threats of deportation, violence, blacklisting, or harm to family to compel work."},
    "physical_abuse": {
        "label": "Physical or sexual violence",
        "ilo_indicator": "physical_sexual_violence", "severity": 3,
        "description": "Violence or sexual abuse used to control the worker."},
    "deceptive_recruitment": {
        "label": "Deceptive recruitment",
        "ilo_indicator": "deception", "severity": 3,
        "description": "False promises about job, pay, employer, or destination to lure the worker."},
    "vulnerability_abuse": {
        "label": "Abuse of vulnerability",
        "ilo_indicator": "abuse_of_vulnerability", "severity": 2,
        "description": "Exploiting irregular status, debt, language, or isolation to coerce."},
}

# ---------------------------------------------------------------------------
# Industry profiles (the 18 catalogue industries)
# ---------------------------------------------------------------------------

SKILL_LEVELS: tuple[str, ...] = ("unskilled", "semi_skilled", "skilled", "mixed")
RISK_TIERS: dict[int, str] = {1: "severe", 2: "elevated", 3: "baseline"}


@dataclass(frozen=True)
class IndustryProfile:
    """How one catalogue industry sits in the migrant-labour risk landscape."""
    industry: str
    skill_level: str          # one of SKILL_LEVELS
    sector: str               # broad sector grouping
    risk_tier: int            # 1 severe .. 3 baseline
    problems: tuple[str, ...] # problem_ids common in this industry
    notes: str = ""


def _p(industry, skill, sector, tier, problems, notes=""):
    return IndustryProfile(industry, skill, sector, tier, tuple(problems), notes)


INDUSTRY_PROFILES: dict[str, IndustryProfile] = {p.industry: p for p in [
    _p("recruitment_agency", "mixed", "labour_intermediation", 1,
       ["excessive_recruitment_fees", "contract_substitution", "deceptive_recruitment", "debt_bondage"],
       "The gatekeeper of every corridor; where fee abuse and contract substitution originate."),
    _p("manning_agency", "mixed", "maritime", 1,
       ["excessive_recruitment_fees", "contract_substitution", "wage_theft", "deceptive_recruitment"],
       "Seafarer/fishing-crew recruiters; officers are skilled, ratings semi/unskilled."),
    _p("fishing_seafood", "unskilled", "fishing_maritime", 1,
       ["movement_restriction", "physical_abuse", "wage_theft", "passport_confiscation", "isolation", "forced_overtime"],
       "Sea-based forced labour -- among the most severe; victims isolated at sea for months."),
    _p("construction", "unskilled", "construction", 1,
       ["passport_confiscation", "wage_theft", "sponsorship_tie", "substandard_housing", "excessive_recruitment_fees"],
       "Mega-project and Gulf construction; classic passport-and-wage control."),
    _p("agriculture", "unskilled", "agriculture", 1,
       ["wage_theft", "illegal_deductions", "isolation", "substandard_housing", "debt_bondage"],
       "Plantation/farm labour and seasonal schemes; isolated rural worksites."),
    _p("domestic_worker", "unskilled", "domestic_care", 1,
       ["passport_confiscation", "sponsorship_tie", "wage_theft", "movement_restriction", "physical_abuse", "isolation"],
       "Behind closed doors; kafala/sponsorship makes exit nearly impossible."),
    _p("manufacturing", "semi_skilled", "manufacturing", 1,
       ["excessive_recruitment_fees", "contract_substitution", "forced_overtime", "illegal_deductions"],
       "Garment / electronics / footwear; fee-debt plus forced overtime."),
    _p("money_lender", "skilled", "finance", 1,
       ["debt_bondage", "excessive_recruitment_fees", "illegal_deductions"],
       "The debt rail -- recruitment debt is frequently laundered through licensed lenders."),
    _p("care_home", "semi_skilled", "domestic_care", 2,
       ["wage_theft", "contract_substitution", "forced_overtime", "sponsorship_tie"],
       "Elder/nursing care; mix of skilled nurses and semi-skilled carers."),
    _p("hotel", "semi_skilled", "hospitality", 2,
       ["wage_theft", "illegal_deductions", "contract_substitution", "forced_overtime"],
       "Hospitality housekeeping/kitchen; tipping and deduction abuse."),
    _p("security_services", "unskilled", "services", 2,
       ["wage_theft", "forced_overtime", "passport_confiscation", "illegal_deductions"],
       "Low-wage migrant guards; long shifts, withheld pay."),
    _p("facility_management", "unskilled", "services", 2,
       ["wage_theft", "illegal_deductions", "substandard_housing", "forced_overtime"],
       "Cleaning / facilities labour-supply; subcontracting hides abuse."),
    _p("remittance", "skilled", "finance", 2,
       ["illegal_deductions", "excessive_recruitment_fees"],
       "Money-transfer rail; fee skimming and a laundering channel for fee debt."),
    _p("medical_clinic", "skilled", "health_screening", 2,
       ["excessive_recruitment_fees", "deceptive_recruitment"],
       "GAMCA/GCC-approved medical-exam centres; fraud and exam-fee abuse."),
    _p("training_center", "skilled", "education_training", 2,
       ["excessive_recruitment_fees", "deceptive_recruitment", "debt_bondage"],
       "TVET/skills centres; fake certificates and training-fee debt."),
    _p("financial_services", "skilled", "finance", 3,
       ["illegal_deductions"],
       "Banks/EMIs; mostly a corroboration/laundering-screening layer."),
    _p("company_registry", "mixed", "cross_cutting", 3,
       ["deceptive_recruitment"],
       "General business registry; cross-cutting entity resolution, not a labour site itself."),
    _p("other", "mixed", "cross_cutting", 3, [], "Unclassified registry."),
]}

#: skilled vs unskilled migrant-labour SEGMENTS to keep in view even where a
#: dedicated catalogue industry does not yet exist (guides future expansion).
LABOUR_SEGMENTS: dict[str, tuple[str, ...]] = {
    "unskilled": ("construction", "agriculture", "domestic_worker", "fishing_seafood",
                  "facility_management", "security_services", "mining", "logging",
                  "brick_kiln", "waste_picking", "street_vending", "meat_processing"),
    "semi_skilled": ("manufacturing", "hotel", "care_home", "warehouse_logistics",
                     "drivers_transport", "beauty_salon"),
    "skilled": ("nursing_healthcare", "seafarer_officers", "it_engineering",
                "teaching", "oil_gas", "aviation_cabin_crew", "welding_trades"),
}

# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------

def profile(industry: str) -> IndustryProfile | None:
    """Return the IndustryProfile for ``industry`` (None if unknown)."""
    return INDUSTRY_PROFILES.get((industry or "").strip().lower())


def problem(problem_id: str) -> dict | None:
    """Return the problem record for ``problem_id`` (None if unknown)."""
    p = PROBLEMS.get(problem_id)
    return {"id": problem_id, **p} if p else None


def problems_for_industry(industry: str) -> list[dict]:
    """The concrete migrant problems common in ``industry`` (severity-sorted)."""
    prof = profile(industry)
    if not prof:
        return []
    out = [problem(pid) for pid in prof.problems]
    return sorted((p for p in out if p), key=lambda p: -p["severity"])


def industries_by_risk_tier() -> dict[int, list[str]]:
    """Map risk tier -> sorted industry list."""
    out: dict[int, list[str]] = {1: [], 2: [], 3: []}
    for prof in INDUSTRY_PROFILES.values():
        out[prof.risk_tier].append(prof.industry)
    return {t: sorted(v) for t, v in out.items()}


def industries_by_skill() -> dict[str, list[str]]:
    """Map skill level -> sorted industry list."""
    out: dict[str, list[str]] = {s: [] for s in SKILL_LEVELS}
    for prof in INDUSTRY_PROFILES.values():
        out[prof.skill_level].append(prof.industry)
    return {s: sorted(v) for s, v in out.items()}


# ---------------------------------------------------------------------------
# Source ranking: risk x pull-readiness
# ---------------------------------------------------------------------------

_RISK_WEIGHT = {1: 1.0, 2: 0.65, 3: 0.35}


def readiness_score(source: dict) -> float:
    """How ready a catalogued source is to be pulled (0..1).

    Official provenance, a confirmed-live URL, a real data endpoint, and a free
    access tier each add weight; a downloadable endpoint counts most because it
    is what turns a catalogue pointer into actual entity data.
    """
    s = 0.0
    if source.get("official"):
        s += 0.30
    if source.get("url_verified"):
        s += 0.25
    if source.get("has_data_endpoint"):
        s += 0.35
    tier = str(source.get("access_tier", "free")).lower()
    s += {"free": 0.10, "freemium": 0.05}.get(tier, 0.0)
    return round(min(1.0, s), 3)


def rank_sources(sources: Iterable[dict], *, top: int | None = None) -> list[dict]:
    """Rank catalogued sources by (industry risk) x (pull readiness), desc.

    Returns each source augmented with ``risk_tier``, ``readiness``, and the
    combined ``priority`` score -- a work queue for which registries to build a
    deterministic resolver for next.
    """
    ranked: list[dict] = []
    for src in sources:
        prof = profile(src.get("industry", ""))
        tier = prof.risk_tier if prof else 3
        readiness = readiness_score(src)
        priority = round(readiness * _RISK_WEIGHT[tier], 3)
        ranked.append({**src, "risk_tier": tier, "readiness": readiness, "priority": priority})
    ranked.sort(key=lambda r: (-r["priority"], -r["readiness"], r.get("country", ""), r.get("id", "")))
    return ranked[:top] if top else ranked


def summary() -> dict:
    """Compact taxonomy summary for reports/tests."""
    return {
        "industries": len(INDUSTRY_PROFILES),
        "problems": len(PROBLEMS),
        "ilo_indicators": len(ILO_INDICATORS),
        "by_risk_tier": {RISK_TIERS[t]: v for t, v in industries_by_risk_tier().items()},
        "by_skill": industries_by_skill(),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_catalog() -> list[dict]:
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return []
    if not _CATALOG.exists():
        return []
    return list((yaml.safe_load(_CATALOG.read_text(encoding="utf-8")) or {}).get("sources") or [])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", action="store_true", help="print the taxonomy summary")
    ap.add_argument("--rank", action="store_true", help="rank catalogue sources by pull priority")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args(argv)

    if args.rank:
        ranked = rank_sources(_load_catalog(), top=args.top)
        if args.json:
            print(json.dumps(ranked, ensure_ascii=False, indent=2))
        else:
            print(f"Top {len(ranked)} catalogue sources to pull (priority = risk x readiness):\n")
            for r in ranked:
                print(f"  {r['priority']:.2f}  tier{r['risk_tier']}  {r['industry']:18s} "
                      f"{r.get('country','??')}  {r['name'][:46]}")
        return 0

    s = summary()
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
    else:
        print(f"Industries: {s['industries']} | Problems: {s['problems']} | "
              f"ILO indicators: {s['ilo_indicators']}")
        print("\nBy risk tier:")
        for tier, inds in s["by_risk_tier"].items():
            print(f"  {tier:9s}: {', '.join(inds)}")
        print("\nBy skill level:")
        for skill, inds in s["by_skill"].items():
            print(f"  {skill:12s}: {', '.join(inds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
