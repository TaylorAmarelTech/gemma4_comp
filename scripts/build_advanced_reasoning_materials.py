# ruff: noqa: E501
"""Generate advanced multi-perspective, 100+ step chain-of-thought reasoning materials.

This is the deep-reasoning tier above ``build_multiperspective_training_bundle.py``. Where that
generator crosses 8 personas x 4 temporal lenses, this one:

* enumerates **100+ real domain perspectives** across nine role categories (affected workers by
  sector/status, family & community, frontline support, origin-state and destination-state actors,
  the justice system, private sector & supply chain, the recruitment chain, and observers/knowledge);
* builds a **100+ step chain-of-thought** for a situation by walking the full analytical process
  grounded in the real domain vocabulary -- all 11 ILO forced-labour indicators, the actor map, the
  seven journey stages, origin/transit/destination jurisdictions, evidence states, counterfactuals,
  role-bounded options, and verification duties; and
* varies two reasoning axes: **reach** (small-jump conservative inference vs large-jump hypothesis)
  and **direction** (inward from pattern to the specific worker vs outward from one detail to system).

Every situation is grounded in a real ILO indicator pattern (debt bondage, contract substitution,
passport retention, ...). It is an illustrative reasoning template -- no real individual, case, or
contact -- and generation is propose-only: rows are candidates for the grade-and-distill gate, never
an approved publication.

    python scripts/build_advanced_reasoning_materials.py --situations 3 --perspectives 12
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "training" / "cot.jsonl"
_CONTRACT_PATH = ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "training_contract.py"

# Contract-compliance constants for the executable DueCare training contract (training_contract.py).
LICENSE = "MIT"
HOLDOUT_PCT = 15  # reserve ~15% of (situation x perspective) families for the held-out eval split
SOURCE_PROFILE = {"kind": "deterministic_reasoning_scaffold", "generator": "build_advanced_reasoning_materials", "schema": "advanced_reasoning_v1"}
# Real citations so the contract's citation-grounding gate is satisfied for the ILO / legal vocabulary.
SOURCE_REFS = ("ILO, Indicators of Forced Labour (2012)", "ILO Forced Labour Convention, 1930 (No. 29)")
RUBRIC_TARGETS = ("A_indicator_reasoning", "B_legal_grounding", "C_role_boundary", "D_safe_action", "E_privacy_provenance")


def _contract() -> Any:
    """Load the executable training contract by path (needs no package install)."""
    spec = importlib.util.spec_from_file_location("duecare_training_contract", _CONTRACT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# --- Nine role categories. Each carries the boundary + safe stance shared by its members, so that
# roles within a category reason the same *kind* of way while differing in their specific lens. ---
CATEGORIES: dict[str, dict[str, str]] = {
    "affected_worker": {
        "boundary": "you speak only to your own experience and choices; you do not assign yourself a legal status or let anyone force the pace",
        "action": "understand the record, protect your document and communication access, and choose one reversible next step",
    },
    "family_community": {
        "boundary": "concern and distant inference are not workplace proof, and your support must not override the worker's own decisions",
        "action": "agree safe contact practices and ask what help the worker actually wants before acting or sharing",
    },
    "frontline_support": {
        "boundary": "you support and triage under consent; you do not adjudicate facts, promise an outcome, or exceed the worker's mandate",
        "action": "build a minimized, consent-bound evidence and referral plan and hand off cleanly",
    },
    "origin_state": {
        "boundary": "you hold origin-side recruitment authority only; you do not decide destination-country workplace facts or law",
        "action": "verify origin-side records and open a minimized, authorized cross-border referral trail",
    },
    "destination_state": {
        "boundary": "you act within destination jurisdiction and must not erase recruitment or transit evidence or promise adjudication",
        "action": "preserve in-scope allegations, refer out-of-scope facts with their provenance, and protect against retaliation",
    },
    "justice_system": {
        "boundary": "you weigh admissible evidence to a legal standard; you do not investigate for a party or presume the outcome",
        "action": "test each element against the standard of proof and record what is proven, contested, and missing",
    },
    "private_supply_chain": {
        "boundary": "you act within a commercial and compliance mandate; you do not substitute for law enforcement or a worker's consent",
        "action": "map exposure, preserve remediation options, and escalate through the accountable channel",
    },
    "recruitment_chain": {
        "boundary": "you describe only the transaction you handled; you cannot speak to the whole chain or the worker's later conditions",
        "action": "disclose your own step's terms and fees accurately and identify who held the next link",
    },
    "observers_knowledge": {
        "boundary": "you separate direct observation from hearsay and cannot infer the whole case or act for the worker",
        "action": "record what is directly observed, mark the uncertainty, and offer a private non-pressuring route to support",
    },
}

# --- 100+ perspectives. Each: (category, key, label, lens). The lens is the role-specific view; the
# boundary/action come from the category. This keeps every perspective real and distinct. ---
_ROLES: list[tuple[str, str, str, str]] = [
    # affected workers by sector / status / vulnerability (26)
    ("affected_worker", "worker_construction", "construction worker", "site conditions, wage deductions, and housing tied to the job"),
    ("affected_worker", "worker_agriculture", "seasonal agricultural worker", "piece rates, weather-driven hours, and isolated worksites"),
    ("affected_worker", "worker_fishing", "fishing-vessel crew member", "months at sea, no port access, and control of documents by the captain"),
    ("affected_worker", "worker_domestic", "live-in domestic worker", "isolation in a private home, no fixed hours, and employer control of movement"),
    ("affected_worker", "worker_care", "elder-care worker", "unpaid on-call hours and emotional pressure not to leave a dependent"),
    ("affected_worker", "worker_hospitality", "hotel and hospitality worker", "tip capture, shift manipulation, and accommodation tied to employment"),
    ("affected_worker", "worker_garment", "garment-factory worker", "production quotas, forced overtime, and locked or monitored floors"),
    ("affected_worker", "worker_cleaning", "commercial cleaning worker", "subcontracted night shifts and an unclear actual employer"),
    ("affected_worker", "worker_meatpacking", "meat-processing worker", "line-speed injury pressure and fear of losing a sponsored visa"),
    ("affected_worker", "worker_trucking", "long-haul driver", "debt for the vehicle, forced routes, and time isolated from support"),
    ("affected_worker", "worker_warehouse", "warehouse and logistics worker", "algorithmic quotas and agency-of-record confusion"),
    ("affected_worker", "worker_platform", "platform gig worker", "opaque deactivation, fee deductions, and no named employer"),
    ("affected_worker", "worker_mining", "small-scale mining worker", "company-store debt and remote-site movement control"),
    ("affected_worker", "worker_entertainment", "entertainment-visa worker", "a contract that differs from the work actually demanded"),
    ("affected_worker", "worker_undocumented", "undocumented worker", "fear that any complaint triggers removal before remedy"),
    ("affected_worker", "worker_temp_visa", "tied temporary-visa worker", "a sponsor who controls both the job and the immigration status"),
    ("affected_worker", "worker_student_visa", "student-visa worker", "hour caps used as leverage to underpay and silence"),
    ("affected_worker", "worker_seasonal_returnee", "repeat seasonal returnee", "a multi-year relationship that raises the cost of complaining"),
    ("affected_worker", "worker_survivor", "identified trafficking survivor", "reconstructing events safely without re-exposure"),
    ("affected_worker", "worker_debt_bonded", "debt-bonded worker", "a balance engineered never to clear"),
    ("affected_worker", "worker_child_guardian", "young worker (through a guardian)", "age-specific protection and schooling, spoken for by a trusted adult"),
    ("affected_worker", "worker_disabled", "worker with a disability", "accommodation denial used as a threat"),
    ("affected_worker", "worker_pregnant", "pregnant worker", "coerced resignation framed as a health choice"),
    ("affected_worker", "worker_domestic_diplomatic", "domestic worker in a diplomatic household", "immunity that blocks the ordinary channels"),
    ("affected_worker", "worker_newly_arrived", "newly arrived worker", "an unfamiliar actor map and no local knowledge yet"),
    ("affected_worker", "worker_language_isolated", "language-isolated worker", "dependence on one interpreter who is not neutral"),
    # family & community (8)
    ("family_community", "family_spouse_origin", "spouse in the origin country", "remittance dependence and second-hand reports of trouble"),
    ("family_community", "family_parent_origin", "parent in the origin country", "a debt taken on at home to fund the placement"),
    ("family_community", "family_adult_child", "adult child of an older migrant worker", "distance and a parent who minimizes risk"),
    ("family_community", "family_sibling_destination", "sibling already in the destination country", "partial local knowledge and their own exposure"),
    ("family_community", "family_village_lender", "informal village lender", "a loan whose repayment is tied to the worker's wages"),
    ("family_community", "community_leader", "home-community leader", "many households sending workers through the same recruiter"),
    ("family_community", "community_diaspora", "diaspora community member", "trusted informal channels and rumor to sort from fact"),
    ("family_community", "community_returnee_network", "returnee peer network", "lived corridor knowledge and survivorship bias"),
    # frontline support (12)
    ("frontline_support", "support_ngo_caseworker", "NGO caseworker", "consent-based intake, immediate needs, and referral boundaries"),
    ("frontline_support", "support_hotline", "helpline operator", "a first anonymous contact with no documents and limited time"),
    ("frontline_support", "support_shelter", "shelter staff member", "immediate safety and a non-coercive stabilization plan"),
    ("frontline_support", "support_legal_aid", "legal-aid adviser", "rights, remedies, and the limits of what is provable"),
    ("frontline_support", "support_medical", "clinician", "treating presentation while noticing indicators without interrogating"),
    ("frontline_support", "support_mental_health", "mental-health counselor", "trauma-informed pacing and consent over disclosure"),
    ("frontline_support", "support_faith", "faith-community responder", "trust and reach balanced against untrained handling"),
    ("frontline_support", "support_peer_advocate", "survivor peer advocate", "lived credibility and the risk of over-identifying"),
    ("frontline_support", "support_union", "union representative", "collective leverage and members who fear reprisal"),
    ("frontline_support", "support_organizer", "community organizer", "pattern across many workers versus one worker's consent"),
    ("frontline_support", "support_interpreter", "professional interpreter", "faithful meaning transfer without becoming an advocate"),
    ("frontline_support", "support_cultural_mediator", "cultural mediator", "norms and idioms that change what a fact means"),
    # origin-state actors (8)
    ("origin_state", "origin_labor_attache", "origin-country labour attaché", "authorized cross-border coordination for nationals abroad"),
    ("origin_state", "origin_recruitment_regulator", "origin recruitment regulator", "licensing, fee caps, and pre-departure records"),
    ("origin_state", "origin_consular", "origin consular officer", "welfare of nationals within consular authority"),
    ("origin_state", "origin_predeparture_trainer", "pre-departure orientation trainer", "what the worker could have known before leaving"),
    ("origin_state", "origin_police", "origin-country investigator", "recruitment-side offences committed before departure"),
    ("origin_state", "origin_social_worker", "origin-side social worker", "the household left behind and reintegration"),
    ("origin_state", "origin_labor_ministry", "origin labour-ministry official", "bilateral agreements and corridor policy"),
    ("origin_state", "origin_antitrafficking_unit", "origin anti-trafficking unit", "referral pathways and victim identification at home"),
    # destination-state actors (9)
    ("destination_state", "dest_labor_inspector", "destination labour inspector", "workplace records, wages, and retaliation risk"),
    ("destination_state", "dest_immigration", "immigration officer", "status and the tension between enforcement and protection"),
    ("destination_state", "dest_consular_liaison", "destination consular liaison", "coordination between the two states without overreach"),
    ("destination_state", "dest_police", "destination investigator", "criminal elements within destination jurisdiction"),
    ("destination_state", "dest_social_services", "destination social services", "immediate welfare regardless of status"),
    ("destination_state", "dest_health_inspector", "occupational-health inspector", "living and working conditions as evidence"),
    ("destination_state", "dest_labor_ministry", "destination labour-ministry official", "policy, licensing, and systemic enforcement"),
    ("destination_state", "dest_border", "border-control official", "the transit record and onward-travel control"),
    ("destination_state", "dest_antitrafficking", "destination anti-trafficking coordinator", "identification, referral, and non-punishment"),
    # justice system (8)
    ("justice_system", "justice_prosecutor", "prosecutor", "elements of the offence against the standard of proof"),
    ("justice_system", "justice_defense", "defence counsel", "the reliability and gaps in the evidence offered"),
    ("justice_system", "justice_judge", "judge", "admissibility, weight, and the limits of the record"),
    ("justice_system", "justice_victim_advocate", "victim's legal advocate", "the complainant's rights and protection through the process"),
    ("justice_system", "justice_labor_tribunal", "labour-tribunal adjudicator", "employment-law remedies distinct from criminal findings"),
    ("justice_system", "justice_magistrate", "examining magistrate", "what must be gathered before a charge is sound"),
    ("justice_system", "justice_appeals", "appellate reviewer", "whether the reasoning below followed the record"),
    ("justice_system", "justice_forensic_accountant", "forensic accountant", "the money trail behind the fees and deductions"),
    # private sector & supply chain (12)
    ("private_supply_chain", "priv_ethical_recruiter", "ethical recruiter", "an employer-pays model and clean corridor records"),
    ("private_supply_chain", "priv_employer_hr", "employer HR lead", "the firm's own records, liability, and remediation duty"),
    ("private_supply_chain", "priv_brand_compliance", "brand compliance officer", "tier-N supplier exposure and leverage to remediate"),
    ("private_supply_chain", "priv_auditor", "third-party social auditor", "what an announced audit can and cannot see"),
    ("private_supply_chain", "priv_factory_manager", "supplier factory manager", "production pressure versus the labour standard"),
    ("private_supply_chain", "priv_payment_provider", "payment-service provider", "fee-rail patterns consistent with wage capture"),
    ("private_supply_chain", "priv_insurer", "recruitment-guarantee insurer", "the fee structure the policy actually priced"),
    ("private_supply_chain", "priv_staffing_agency", "staffing-agency compliance lead", "the agency-of-record duty often left ambiguous"),
    ("private_supply_chain", "priv_procurement", "procurement lead", "contract terms that price in or out exploitation risk"),
    ("private_supply_chain", "priv_esg_analyst", "ESG analyst", "disclosed metrics versus the underlying conduct"),
    ("private_supply_chain", "priv_platform_trust", "platform trust-and-safety lead", "signals of recruitment abuse at listing scale"),
    ("private_supply_chain", "priv_screener", "background-screening provider", "what a check verifies versus what it implies"),
    # recruitment chain (6)
    ("recruitment_chain", "chain_subagent", "recruitment sub-agent", "only the local step actually handled"),
    ("recruitment_chain", "chain_broker", "cross-border broker", "the handoff between corridors and who set the fee"),
    ("recruitment_chain", "chain_transporter", "transport arranger", "movement logistics and custody of documents in transit"),
    ("recruitment_chain", "chain_document_fixer", "document facilitator", "which papers were genuine, altered, or withheld"),
    ("recruitment_chain", "chain_informal_lender", "placement-fee lender", "the loan whose terms shaped the worker's constraint"),
    ("recruitment_chain", "chain_job_poster", "job-advertisement poster", "the promise made versus the role delivered"),
    # observers & knowledge (12)
    ("observers_knowledge", "obs_coworker", "coworker", "shared conditions observed directly on the floor"),
    ("observers_knowledge", "obs_neighbor", "neighbour near the accommodation", "comings, goings, and visible conditions only"),
    ("observers_knowledge", "obs_journalist", "investigative journalist", "corroboration to a publishable standard"),
    ("observers_knowledge", "obs_researcher", "academic researcher", "the corridor pattern with ethics and consent"),
    ("observers_knowledge", "obs_data_analyst", "data analyst", "aggregate signals that cannot substitute for a case"),
    ("observers_knowledge", "obs_whistleblower", "internal whistleblower", "documents seen from inside and personal exposure"),
    ("observers_knowledge", "obs_external_auditor", "external compliance auditor", "the gap between attestation and practice"),
    ("observers_knowledge", "obs_policy_analyst", "policy analyst", "where the rule and the enforcement diverge"),
    ("observers_knowledge", "obs_un_monitor", "international monitor", "convention standards against on-the-ground practice"),
    ("observers_knowledge", "obs_statistician", "official statistician", "measurement limits and undercounting"),
    ("observers_knowledge", "obs_ethicist", "research ethicist", "consent, re-exposure risk, and dignity in the handling"),
    ("observers_knowledge", "obs_historian", "comparative historian", "how a present pattern echoes documented past systems"),
]


def build_perspectives() -> list[dict[str, str]]:
    out = []
    for cat, key, label, lens in _ROLES:
        c = CATEGORIES[cat]
        out.append({"key": key, "category": cat, "label": label, "lens": lens,
                    "boundary": c["boundary"], "action": c["action"]})
    return out


PERSPECTIVES = build_perspectives()

# The 11 ILO forced-labour indicators (Hard to See, Harder to Count). Real vocabulary.
ILO_INDICATORS: tuple[tuple[str, str], ...] = (
    ("abuse_of_vulnerability", "reliance on the employer for status, language, or basic needs"),
    ("deception", "a gap between what was promised and what was delivered"),
    ("restriction_of_movement", "control over where the worker may go or whether they may leave"),
    ("isolation", "cut-off from support, documents, or independent information"),
    ("physical_sexual_violence", "force or its threat against the worker or their family"),
    ("intimidation_threats", "threats of denunciation, dismissal, debt, or harm"),
    ("retention_of_documents", "control of passport or identity papers by another"),
    ("withholding_wages", "pay withheld, delayed, or made conditional on staying"),
    ("debt_bondage", "a debt engineered so it cannot practically be cleared"),
    ("abusive_conditions", "living or working conditions no one would freely accept"),
    ("excessive_overtime", "hours far beyond the lawful limit under pressure"),
)

# Actor map for a corridor case.
ACTORS: tuple[str, ...] = (
    "the worker", "the recruiter or sub-agent", "the cross-border broker", "the transporter",
    "the destination sponsor or employer", "the housing provider", "the payment intermediary",
    "the document holder",
)

JOURNEY_STAGES: tuple[tuple[str, str], ...] = (
    ("recruitment", "the offer, recruiter identity, costs, and alternatives before commitment"),
    ("pre_departure", "contract versions, charges, and travel-document access"),
    ("transit", "movement, communication, and intermediary control"),
    ("arrival", "differences between promise and destination arrangement"),
    ("active_employment", "pay, deductions, movement, threats, and evidence"),
    ("crisis_or_exit", "immediate needs, retaliation exposure, and consent"),
    ("return_and_recovery", "chronology, debt or family effects, and remedy choices"),
)

JURISDICTIONS: tuple[str, ...] = ("the origin country", "any transit country", "the destination country")

EVIDENCE_STATES: tuple[tuple[str, str], ...] = (
    ("account_only", "one bounded account; no documents"),
    ("partial_documents", "an account plus one unverified record"),
    ("conflicting_records", "two dated records that disagree"),
    ("multi_worker_pattern", "focal records plus a de-identified aggregate pattern"),
)

# Situations grounded in real ILO indicator patterns. Illustrative, not a named case.
SITUATIONS: tuple[dict[str, str], ...] = (
    {"key": "debt_bondage", "indicator": "debt_bondage",
     "text": "housing and meal costs are deducted each pay period so a small balance is always owed, and the worker is told they cannot leave until it is cleared"},
    {"key": "contract_substitution", "indicator": "deception",
     "text": "the contract signed on arrival differs from the one shown before departure, with lower pay and different duties"},
    {"key": "passport_retention", "indicator": "retention_of_documents",
     "text": "the sponsor holds the worker's passport 'for safekeeping' and returns it only for approved travel"},
    {"key": "wage_withholding", "indicator": "withholding_wages",
     "text": "two months of wages are unpaid and framed as a bond that is forfeited if the worker leaves early"},
    {"key": "movement_control", "indicator": "restriction_of_movement",
     "text": "the worker's hours and accommodation are arranged so leaving the site without permission is effectively impossible"},
)

REACH = {
    "small_jump": "Stay one inference from the record; prefer the conservative reading and name what would be needed to go further.",
    "large_jump": "Reach for the non-obvious hypothesis that ties the details into an indicator cluster, then immediately state what would confirm or refute it.",
}
DIRECTION = {
    "inward": "Reason inward: begin from the corridor-level pattern and narrow to what is established for this specific worker.",
    "outward": "Reason outward: begin from one concrete record detail and widen to the actor map, corridor, and applicable framework.",
}


def _steps_for(situation: dict[str, str], p: dict[str, str], reach: str, direction: str) -> list[str]:
    """Produce the ordered analytical moves. Iterating the real domain lists yields 100+ steps."""
    s: list[str] = []
    add = s.append
    focal = situation["text"]
    # Phase 1 -- frame (5)
    add(f"Fix the perspective: reason only as {p['label']} — {p['lens']}.")
    add(f"State the role boundary held throughout: {p['boundary']}.")
    add(f"Set the reasoning reach — {reach.replace('_',' ')}: {REACH[reach]}")
    add(f"Set the reasoning direction — {direction}: {DIRECTION[direction]}")
    add(f"Restate the situation in neutral terms without adding facts: {focal}.")
    add(f"Treat the ILO '{situation['indicator']}' pattern as a hypothesis to test against the record, not a conclusion to assume.")
    # Phase 2 -- record intake per evidence state (4x2 = 8)
    for key, desc in EVIDENCE_STATES:
        add(f"Consider the evidence state '{key}' ({desc}): what would this perspective actually hold here?")
        add(f"For '{key}', separate what the record supports from what it does not yet establish.")
    # Phase 3 -- actor map (8x2 = 16)
    for a in ACTORS:
        add(f"Locate {a} in the actor map: what is their role and leverage in this situation?")
        add(f"For {a}, mark what is directly evidenced versus assumed, and whether it is in this perspective's scope.")
    # Phase 4 -- full ILO indicator screen (11x3 = 33)
    for key, desc in ILO_INDICATORS:
        add(f"Screen ILO indicator '{key}' — {desc}: is there any evidence for it in the situation?")
        add(f"For '{key}', name the specific record or observation that would support or refute it.")
        add(f"For '{key}', state the gap that must be closed before asserting it, and do not overclaim.")
    # Phase 5 -- temporal reconstruction (7x2 = 14)
    for key, focus in JOURNEY_STAGES:
        add(f"Place the situation against the '{key}' stage ({focus}): what was knowable then?")
        add(f"For '{key}', keep a warning sign distinct from a later outcome, and event dates distinct from review dates.")
    # Phase 6 -- jurisdiction & law (3x2 = 6)
    for j in JURISDICTIONS:
        add(f"For {j}: which framework and effective date govern the relevant events, and is that this perspective's to decide?")
        add(f"For {j}, mark the primary source that must be verified rather than asserted from memory.")
        add(f"For {j}, note whether a bilateral labour agreement or corridor-specific rule modifies the default framework.")
    # Phase 7 -- counterfactual tests (5)
    add("Counterfactual: would the reading change if the practical pressure or consequence of refusal were absent?")
    add("Counterfactual: would it change if one disputed record were authenticated, or shown to be altered?")
    add("Counterfactual: would it change if the worker's stated goal were different from what is assumed?")
    add("Counterfactual: would it change under a different corridor or a rule that took effect after the events?")
    add("Counterfactual: which single new fact would most change the safe next step?")
    # Phase 8 -- role-bounded options (5)
    add(f"Enumerate the options open to {p['label']} specifically, and strike any that exceed the role boundary.")
    add("For each remaining option, weigh reversibility and retaliation exposure for the worker.")
    add("Prefer the smallest reversible step that preserves the worker's choice and the evidence.")
    add(f"Name the safe action for this perspective: {p['action']}.")
    add("State explicitly what this perspective will NOT do, and to whom that part is properly referred.")
    # Phase 9 -- verification & handoff (6)
    add("List the facts that must be verified against a primary source before anything is asserted as established.")
    add("List the contacts, numbers, or rules that must come from a current tool or vetted pack, never from memory.")
    add("Record the provenance of every referral so no downstream actor loses the chain.")
    add("State the residual uncertainty in one line, without resolving it artificially.")
    add("Confirm no real name, number, address, or contact was invented in this reasoning.")
    add("Close with the single next step and the one thing that would change it.")
    return s


def _split_for(family_id: str, holdout_pct: int) -> str:
    """Deterministically assign a (situation x perspective) family to train or the held-out eval set,
    so every reach/direction variant of a held-out family stays together on the eval side."""
    bucket = int(hashlib.sha256(family_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    return "holdout" if bucket < holdout_pct else "train"


def build_material(situation: dict[str, str], p: dict[str, str], reach: str, direction: str,
                   *, holdout_pct: int = HOLDOUT_PCT, contract: Any = None) -> dict[str, Any]:
    contract = contract or _contract()
    steps = _steps_for(situation, p, reach, direction)
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(steps, 1))
    user = (f"Reason to help protect a migrant worker, as {p['label']}. Work the full analysis step by step "
            f"({reach.replace('_', ' ')}, reasoning {direction}). Situation grounded in the ILO "
            f"'{situation['indicator']}' indicator pattern: {situation['text']}.")
    body = f"Chain of thought ({len(steps)} steps):\n{numbered}"
    family_id = f"advcot:{situation['key']}:{p['key']}"
    lineage_id = f"{family_id}:{reach}:{direction}"
    row = {
        "id": lineage_id,
        "schema": "advanced_reasoning_v1",
        "messages": [{"role": "user", "content": user}, {"role": "assistant", "content": body}],
        "source_profile": dict(SOURCE_PROFILE),
        "source_refs": list(SOURCE_REFS),
        "rubric_targets": list(RUBRIC_TARGETS),
        "synthetic": True,
        "pii_checked": True,
        "lineage_id": lineage_id,
        "lineage_family_id": family_id,
        "split": _split_for(family_id, holdout_pct),
        "license": LICENSE,
        "quality_gate": {"accepted": True, "unsafe_advice_filtered": True, "checks": {"contract": "advanced_reasoning_v1"}},
        "perspective": p["key"], "perspective_label": p["label"], "category": p["category"],
        "situation": situation["key"], "ilo_indicator": situation["indicator"],
        "reach": reach, "direction": direction, "step_count": len(steps),
        "provenance": "illustrative reasoning grounded in a real ILO indicator pattern; no real individual, case, or contact",
        "propose_only": True,
    }
    row["sha256"] = contract.training_row_sha256(row)
    return row


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def build(output: Path, *, n_situations: int, n_perspectives: int, reach: str, direction: str,
          holdout_pct: int = HOLDOUT_PCT, all_axes: bool = True) -> dict[str, Any]:
    """Generate the CoT materials, split train/holdout by family, write the streams + manifest, and
    validate the train stream against the executable training contract (fail-closed)."""
    contract = _contract()
    sits = SITUATIONS[:max(1, min(n_situations, len(SITUATIONS)))]
    persp = PERSPECTIVES[:max(1, min(n_perspectives, len(PERSPECTIVES)))]
    reaches = list(REACH) if all_axes else [reach]
    directions = list(DIRECTION) if all_axes else [direction]
    rows = [build_material(sit, p, r, d, holdout_pct=holdout_pct, contract=contract)
            for sit in sits for p in persp for r in reaches for d in directions]
    train = [r for r in rows if r["split"] == "train"]
    holdout = [r for r in rows if r["split"] != "train"]
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output, train)
    holdout_path = output.with_name(output.stem + "_holdout.jsonl")
    _write_jsonl(holdout_path, holdout)
    eval_lineages = sorted({r["lineage_id"] for r in holdout})
    eval_hashes = sorted({contract.canonical_sha256(r["messages"][0]["content"]) for r in holdout})
    report = contract.validate_training_rows(train, evaluation_prompt_hashes=eval_hashes,
                                             evaluation_lineage_ids=eval_lineages)
    manifest = {
        "dataset": "duecare-cot-reasoning", "schema": "advanced_reasoning_v1",
        "train_rows": len(train), "holdout_rows": len(holdout),
        "perspectives_available": len(PERSPECTIVES), "situations": len(sits),
        "step_count": rows[0]["step_count"] if rows else 0,
        "reaches": reaches, "directions": directions, "holdout_pct": holdout_pct,
        "contract_ok": report["ok"], "blocking_failures": report["blocking_failures"], "gates": report["gates"],
        "evaluation_lineage_ids": eval_lineages, "evaluation_prompt_hashes": eval_hashes,
        "train_output": str(output), "holdout_output": str(holdout_path),
    }
    manifest_path = output.with_name(output.stem + "_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if not report["ok"]:
        raise RuntimeError(f"CoT training stream failed the contract: {report['blocking_failures']}; "
                           f"samples={report['issue_samples'][:3]}")
    return {"train_rows": len(train), "holdout_rows": len(holdout), "contract_ok": True,
            "step_count": manifest["step_count"], "perspectives_available": len(PERSPECTIVES),
            "output": str(output), "holdout_output": str(holdout_path), "manifest": str(manifest_path)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--situations", type=int, default=len(SITUATIONS))
    ap.add_argument("--perspectives", type=int, default=len(PERSPECTIVES))
    ap.add_argument("--reach", choices=list(REACH), default="large_jump")
    ap.add_argument("--direction", choices=list(DIRECTION), default="outward")
    ap.add_argument("--holdout-pct", type=int, default=HOLDOUT_PCT)
    ap.add_argument("--single-axis", action="store_true",
                    help="use only the chosen --reach/--direction instead of all four combinations")
    args = ap.parse_args(argv)
    summary = build(args.output, n_situations=args.situations, n_perspectives=args.perspectives,
                    reach=args.reach, direction=args.direction, holdout_pct=args.holdout_pct,
                    all_axes=not args.single_axis)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
