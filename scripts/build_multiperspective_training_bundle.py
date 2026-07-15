#!/usr/bin/env python3
# ruff: noqa: E501
"""Build a grounded, multi-persona synthetic reasoning training bundle.

The generator creates coherent synthetic case graphs rather than multiplying
independent labels.  Each graph has dated events, competing records, actor and
jurisdiction boundaries, and persona-specific information limits across a
worker journey.  SFT and DPO rows are two training views of the same scenario:
the DPO reject is a plausible direct response with one controlled failure, not
a critique of a hypothetical answer.

The output contains visible decision scaffolds and final answers only.  It
does not request or publish provider-private reasoning, raw worker cases,
credentials, real contacts, or volatile legal conclusions.  The build emits a
candidate bundle and an executable quality audit.  Publication approval is a
separate, explicit action bound to the finished manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from functools import cache
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHAT_SRC = ROOT / "packages" / "duecare-llm-chat" / "src"
if str(CHAT_SRC) not in sys.path:
    sys.path.insert(0, str(CHAT_SRC))

from duecare.chat.training_contract import (  # noqa: E402
    canonical_sha256,
    pii_findings,
    training_row_sha256,
    validate_training_rows,
)

SOURCE_HANDOFF_KIND = "duecare.a00.synthetic.training_bundle.v2"
APPROVAL_HANDOFF_KIND = "duecare.training.publication_approval.v1"
GENERATOR_VERSION = "duecare-grounded-multiperspective-casegraph/2.0.0"
MODEL_ID = "unsloth/gemma-4-E2B-it"
MODEL_REVISION = "4abfca14e6c6bfb5888b80288185b1243fb8d539"
MODEL_ROLE = "intended_finetuning_base_not_data_generator"
ROW_LICENSE = "CC-BY-SA-4.0"
RIGHTS_HOLDER = "DueCare project contributors"
CREATED_AT = "2026-07-14T00:00:00+00:00"
HARNESS_VERSION = "duecare-grounded-casegraph-synthetic-2026-07-14"
RUBRIC_VERSION = "duecare-visible-decision-scaffold-v2"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "multiperspective_training" / "source_bundle_v3"

DEFAULT_TRAIN_ROWS = 2048
DEFAULT_VALIDATION_ROWS = 256
DEFAULT_TEST_ROWS = 256
NEAR_DUPLICATE_THRESHOLD = 0.88

SOURCE_REFS = [
    "https://www.ilo.org/publications/ilo-indicators-forced-labour-1",
    "https://normlex.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE:C029",
    "https://www.unodc.org/e4j/en/tip-and-som/module-13/key-issues/international-legal-frameworks-and-definitions.html",
    "repo:docs/training_and_finetuning.md#answers-rationales-and-chain-of-thought",
]
KNOWLEDGE_REFS = [
    "repo:configs/duecare/legal_claims.json#c029_vs_indicators",
    "repo:configs/duecare/legal_claims.json#palermo_elements",
    "repo:packages/duecare-llm-chat/src/duecare/chat/training_contract.py",
]
RUBRIC_TARGETS = [
    "worker_centered_reasoning",
    "perspective_authority_boundary",
    "cross_persona_handoff",
    "cross_jurisdiction_actor_mapping",
    "multi_temporal_reasoning",
    "record_level_evidence_separation",
    "counterfactual_reasoning",
    "retrieval_boundary",
    "consent_preserving_action",
]


PERSONAS: tuple[dict[str, str], ...] = (
    {
        "key": "worker",
        "label": "worker directly affected",
        "view": "first-person goals, safety, document access, and practical options",
        "boundary": "the worker controls the goal and pace; the response must not assign a legal status or force escalation",
        "action": "offer a small menu of reversible options and let the worker choose the pace",
    },
    {
        "key": "newly_arrived_worker",
        "label": "worker navigating an unfamiliar destination system",
        "view": "what the worker knew when the destination system was new, even when reconstructing that moment later",
        "boundary": "explain the actor map plainly and do not assume knowledge of local institutions or later events",
        "action": "orient around document access, communication safety, and one low-exposure next step",
    },
    {
        "key": "third_party_observer",
        "label": "third-party coworker or community observer",
        "view": "direct observations separated from hearsay and from the worker's wishes",
        "boundary": "the observer cannot infer the whole case, confront a suspected controller, or act for the worker without consent",
        "action": "record only direct observations and offer a private, non-pressuring route to support",
    },
    {
        "key": "family_member",
        "label": "family member in origin Country A",
        "view": "communications received from afar and effects on the family, without worksite access",
        "boundary": "family concern and inference are not workplace proof, and support must not take over the worker's decisions",
        "action": "agree on safe contact practices and ask what help the worker wants before sharing anything",
    },
    {
        "key": "ngo_caseworker",
        "label": "NGO caseworker",
        "view": "consent-based intake, immediate needs, evidence tags, and referral boundaries",
        "boundary": "the caseworker supports and triages but does not adjudicate facts or promise an outcome",
        "action": "create a minimized evidence ledger and a consent-bound support or referral plan",
    },
    {
        "key": "origin_country_official",
        "label": "government official in origin Country A",
        "view": "origin-side recruitment records and authorized cross-border coordination",
        "boundary": "origin-country authority does not decide destination-country workplace facts or law",
        "action": "verify origin-side records and use a minimized, authorized referral trail",
    },
    {
        "key": "destination_regulator",
        "label": "labour regulator in destination Country B",
        "view": "destination-workplace records, retaliation risk, and jurisdiction-specific fact finding",
        "boundary": "the regulator must not erase recruitment or transit evidence, exceed jurisdiction, or promise adjudication",
        "action": "preserve in-scope allegations and refer out-of-scope facts without dropping their provenance",
    },
    {
        "key": "legal_scholar",
        "label": "comparative legal scholar",
        "view": "dated comparison of legal frames, evidence standards, and unresolved applicability questions",
        "boundary": "the scholar is not counsel or a fact finder and must separate stable indicators from current local doctrine",
        "action": "build a dated issue map and identify the primary sources that require current verification",
    },
)


JOURNEY_STAGES: tuple[dict[str, Any], ...] = (
    {"key": "recruitment", "label": "recruitment", "date": "2025-01-10", "focus": "the offer, recruiter identity, costs, and alternatives before commitment"},
    {"key": "pre_departure", "label": "pre-departure preparation", "date": "2025-02-01", "focus": "contract versions, charges, travel-document access, and informed choice"},
    {"key": "transit", "label": "transit or transfer", "date": "2025-02-18", "focus": "movement, communication, intermediary control, and onward travel"},
    {"key": "arrival", "label": "arrival and onboarding", "date": "2025-02-20", "focus": "differences between earlier promises and destination arrangements"},
    {"key": "active_employment", "label": "active employment", "date": "2025-04-30", "focus": "pay, deductions, workload, movement, threats, and evidence preservation"},
    {"key": "crisis_or_exit", "label": "crisis, complaint, or exit decision", "date": "2025-07-12", "focus": "immediate needs, retaliation exposure, consent, complaint, transfer, or departure choices"},
    {"key": "return_and_recovery", "label": "return and recovery", "date": "2025-09-05", "focus": "chronology, debt or family effects, evidence gaps, remedy choices, and recovery pace"},
)


TEMPORAL_LENSES: tuple[dict[str, str], ...] = (
    {
        "key": "prospective",
        "label": "prospective decision at the focal date",
        "instruction": "use only information marked available by the focal date and distinguish a warning sign from a later outcome",
    },
    {
        "key": "contemporaneous",
        "label": "current-state triage at the focal date",
        "instruction": "separate the immediate condition from earlier representations and events that had not yet occurred",
    },
    {
        "key": "retrospective",
        "label": "retrospective reconstruction on 2026-02-15",
        "instruction": "reconstruct the focal decision with later records while marking what was and was not knowable at that time",
    },
    {
        "key": "rule_change",
        "label": "cross-temporal rule comparison on 2026-02-15",
        "instruction": "keep event dates and rule-effective dates distinct and retrieve primary law for both the focal and review dates",
    },
)


EVIDENCE_STATES: tuple[dict[str, str], ...] = (
    {
        "key": "account_only",
        "label": "one bounded account",
        "selection": "a persona-specific account only; documents and other accounts remain unavailable",
    },
    {
        "key": "partial_documents",
        "label": "account plus one partial record",
        "selection": "one account and one dated record whose completeness and authenticity remain unverified",
    },
    {
        "key": "conflicting_records",
        "label": "two conflicting records",
        "selection": "an account and two dated records that disagree without resolving which account is correct",
    },
    {
        "key": "multi_worker_pattern",
        "label": "focal records plus a de-identified pattern note",
        "selection": "focal records plus an aggregate synthetic pattern that cannot substitute for the focal worker's facts or consent",
    },
)


VIEW_MODES: tuple[dict[str, str], ...] = (
    {
        "key": "single_perspective",
        "label": "single-perspective decision",
        "instruction": "reason within the primary persona's information and authority limits",
    },
    {
        "key": "two_perspective_handoff",
        "label": "two-perspective handoff",
        "instruction": "compare what the primary and counterpart can know, then design a consent-bound handoff",
    },
    {
        "key": "multi_actor_synthesis",
        "label": "multi-actor synthesis",
        "instruction": "reconcile worker, support, origin-side, and destination-side views without collapsing their authority",
    },
)


JURISDICTION_PATTERNS: tuple[dict[str, str], ...] = (
    {
        "key": "a_to_b",
        "label": "Country A to Country B",
        "actors": "worker and recruiter in Country A; sponsor, supervisor, housing actor, and worksite in Country B",
        "questions": "which origin recruitment facts and destination work or housing facts each authority can verify at the relevant date",
    },
    {
        "key": "a_via_c_to_b",
        "label": "Country A via transit Country C to Country B",
        "actors": "worker and recruiter in Country A; transit broker in Country C; sponsor, supervisor, and worksite in Country B",
        "questions": "whether transit conduct creates a separate evidence and referral path without displacing origin or destination facts",
    },
    {
        "key": "a_platform_to_b",
        "label": "Country A through a remote platform to Country B",
        "actors": "worker in Country A; remote platform and payment intermediary; sponsor, housing actor, and worksite in Country B",
        "questions": "where each platform, payment, recruitment, housing, and employment event occurred and who can verify it",
    },
)


MECHANISMS: tuple[dict[str, Any], ...] = (
    {
        "key": "fee_camouflage",
        "onset": "recruitment",
        "promise": "the offer lists no recruitment charge",
        "signal": "a separate 650-unit training invoice is marked necessary to keep the placement",
        "condition": "the recruiter links the 650-unit invoice to continued access to the job while a receipt calls it voluntary membership",
        "actor_account": "the recruiter says the payment is an optional service unrelated to job access",
        "consequence": "the worker records that the placement would be released if payment was not made by 2025-01-16",
        "indicator": "label, practical condition, beneficiary, timing, and consequence of refusal are separate facts",
        "alternative": "a genuinely optional service would be separable from the job and refusal would not risk the placement",
        "preserve": "the offer, invoice, receipt, payment destination, deadline, and response to refusal",
    },
    {
        "key": "document_control",
        "onset": "arrival",
        "promise": "travel documents remain accessible to the worker except for a documented one-day registration step",
        "signal": "the onboarding form has no return date for a travel document placed in the sponsor's cabinet",
        "condition": "ten days after arrival the worker's travel document remains in the sponsor's cabinet despite two return requests",
        "actor_account": "the sponsor describes custody as temporary processing and says access is available on request",
        "consequence": "a supervisor message says return will occur only after the current assignment ends",
        "indicator": "purpose, duration, access, return requests, and movement consequences must be recorded separately",
        "alternative": "documented processing with prompt unconditional return differs from continuing control over movement",
        "preserve": "custody receipt, storage location, return requests, responses, access attempts, and movement effects",
    },
    {
        "key": "wage_withholding",
        "onset": "active_employment",
        "promise": "the signed offer states 1,200 units monthly with housing optional and no placement-loan deduction",
        "signal": "an unsigned payroll setup sheet contains blank lines for housing and placement deductions",
        "condition": "the April pay record shows 1,200 gross, 680 net, a 300-unit housing deduction, and a 220-unit placement deduction",
        "actor_account": "payroll says all deductions were authorized during onboarding but does not identify the signed authorization",
        "consequence": "the worker says an objection was followed by a warning that the next payment could also be held",
        "indicator": "promised pay, actual pay, each deduction, authorization, payee, and pressure after objection require separate entries",
        "alternative": "a transparent deduction would be documented, reviewable, and not maintained through threats or unrelated controls",
        "preserve": "offer, payroll setup, pay records, deduction recipients, authorization evidence, objections, and responses",
    },
    {
        "key": "contract_substitution",
        "onset": "arrival",
        "promise": "the Country A contract lists warehouse work, 1,200 units monthly, and one named worksite",
        "signal": "the arrival checklist refers to a destination contract without attaching translated terms",
        "condition": "the Country B document lists cleaning work, 900 units monthly, and a different worksite and was presented after arrival",
        "actor_account": "the sponsor says the second document merely translates the first and changes no material term",
        "consequence": "the worker records being told that declining the new version would end housing and the placement",
        "indicator": "each version needs a date, actor, language, decision point, explanation, and consequence of refusal",
        "alternative": "a freely negotiated change would be understandable, voluntary, and declineable without punitive loss",
        "preserve": "all versions, translations, timestamps, signature context, change explanation, and refusal consequences",
    },
    {
        "key": "sponsor_supervisor_split",
        "onset": "arrival",
        "promise": "the recruitment pack names one sponsor as responsible for pay, housing, and work assignment",
        "signal": "the arrival form names a separate supervisor and housing company without allocating responsibilities",
        "condition": "payroll names a subcontractor, housing rules name a third company, and the supervisor and sponsor each redirect questions to the other",
        "actor_account": "each destination actor says another entity controls the disputed condition",
        "consequence": "the worker's three requests produce no actor willing to correct pay, housing, or document access",
        "indicator": "formal title and practical control are different facts and may lead to multiple accountability paths",
        "alternative": "a clear arrangement would identify who can change pay, work, housing, and document access without circular denial",
        "preserve": "contracts, sponsor record, payroll, housing rules, instructions, referrals, and who could change each condition",
    },
    {
        "key": "family_retaliation",
        "onset": "crisis_or_exit",
        "promise": "the recruiter says family contacts will be used only for voluntary emergency communication",
        "signal": "the intake form requests a family contact without explaining who can access it",
        "condition": "after the worker questions conditions, a sender linked to the recruiter demands 700 units from the family in Country A",
        "actor_account": "the recruiter describes the family message as ordinary collection unrelated to the worker's complaint",
        "consequence": "the message states that the family business will be reported if payment is not made within two days",
        "indicator": "worker safety, family safety, debt facts, communication security, and actor linkage need separate assessment",
        "alternative": "ordinary collection would not depend on threats, secrecy, job control, or punishment of relatives",
        "preserve": "dated messages, safely known sender details, demands, payment records, consent, and timing after the objection",
    },
    {
        "key": "movement_isolation",
        "onset": "arrival",
        "promise": "housing and transport are described as optional supports with independent communication and exit",
        "signal": "the housing sheet lists a curfew and transport roster without an exception or exit procedure",
        "condition": "housing, transport, and work rosters leave no independent route out and the supervisor holds the only gate pass",
        "actor_account": "management says the rules are ordinary safety controls and workers may leave whenever they wish",
        "consequence": "the worker records a denied exit request and a warning that leaving the roster would end housing",
        "indicator": "physical rules, threats, surveillance, location, resources, and the worker's assessment of safe options are distinct",
        "alternative": "proportionate safety rules would be explained and preserve independent communication and voluntary exit",
        "preserve": "rules, transport access, exit attempts, responses, gate arrangements, communications, and immediate needs",
    },
    {
        "key": "settlement_evidence_pressure",
        "onset": "crisis_or_exit",
        "promise": "the complaint process is described as allowing review without loss of documents or earned payment",
        "signal": "a draft exit form contains a broad release but no explanation of evidence handling",
        "condition": "the proposed final payment is conditioned on deleting messages and withdrawing the intake note",
        "actor_account": "the supervisor calls deletion routine closure and says the payment is not tied to silence",
        "consequence": "the offer expires in 24 hours and document return is listed only after deletion confirmation",
        "indicator": "offer, pressure, evidence request, legal effect, and immediate safety consequences must not be collapsed",
        "alternative": "a fair process would allow independent review, informed consent, and safe preservation of necessary records",
        "preserve": "the exact offer, dates, conditions, deletion request, deadline, payment terms, and retaliation concerns",
    },
    {
        "key": "post_deployment_debt",
        "onset": "active_employment",
        "promise": "the recruitment and pre-departure records state that no loan or recruitment balance is due",
        "signal": "the onboarding packet includes an unsigned blank repayment schedule",
        "condition": "a 1,800-unit debt note dated after work began is described as an earlier recruitment balance",
        "actor_account": "the payment intermediary says the note is an independent optional credit product",
        "consequence": "payroll begins a 250-unit monthly deduction and the supervisor links refusal to assignment renewal",
        "indicator": "original demand, later debt instrument, payee, deductions, pressure, and worker understanding require a dated chain",
        "alternative": "independent credit would be understandable, optional, separately documented, and unrelated to movement or job control",
        "preserve": "original and later records, payment flows, explanations, signatures, deductions, and refusal consequences",
    },
    {
        "key": "recruitment_deception",
        "onset": "arrival",
        "promise": "the advertisement and interview promise warehouse work, 1,200 units monthly, and a city worksite",
        "signal": "the pre-departure itinerary names a different region but gives no worksite explanation",
        "condition": "arrival records assign cleaning work at a remote site for 900 units monthly",
        "actor_account": "the recruiter says the advertisement was illustrative and every material term remained equivalent",
        "consequence": "the worker says declining the changed assignment would forfeit the travel payment and housing",
        "indicator": "promise, speaker, timing, reliance, later reality, and remaining choice must be recorded separately",
        "alternative": "an honest correction would be timely, understandable, and allow withdrawal without punitive loss",
        "preserve": "advertisement, messages, interview notes, contracts, itinerary, later conditions, and clarification attempts",
    },
    {
        "key": "threat_of_reporting",
        "onset": "active_employment",
        "promise": "the orientation note says workers may raise questions without retaliation",
        "signal": "a supervisor message says assignment status depends on cooperation but does not define cooperation",
        "condition": "after a wage question, the supervisor writes that the worker will be reported and blacklisted if the worker leaves",
        "actor_account": "the supervisor says the message neutrally explained possible procedures and was not a threat",
        "consequence": "the worker stays on the next shift and records fear of detention and reputational harm",
        "indicator": "words, speaker's practical power, worker understanding, surrounding controls, and resulting conduct all matter",
        "alternative": "a neutral procedural explanation would not punish questions or compel continued work",
        "preserve": "exact wording, date, speaker, witnesses, surrounding messages, relevant records, and subsequent conduct",
    },
    {
        "key": "unsafe_housing_work_link",
        "onset": "arrival",
        "promise": "housing, food, transport, and medical access are described as safe supports separable from work complaints",
        "signal": "the housing rules tie room access to the active shift roster without an emergency exception",
        "condition": "an inspection note records unsafe wiring and no drinking water while the manager conditions room access on attending shifts",
        "actor_account": "the housing company says conditions are temporary and work attendance is unrelated to basic access",
        "consequence": "a request for safer housing is followed by loss of meal access and a warning about the next assignment",
        "indicator": "living conditions, dependency, work control, payment, mobility, and complaint consequences need separate assessment",
        "alternative": "work-linked support would meet basic safety needs without conditioning necessities on silence or continued work",
        "preserve": "conditions, responsible actors, payments, rules, help requests, responses, work consequences, and immediate needs",
    },
)


FAILURE_MODES: tuple[dict[str, str], ...] = (
    {"key": "single_jurisdiction_shortcut", "error": "treat the destination regulator as the only relevant authority", "repair": "map origin, transit or platform, destination work, housing, and remedy questions separately"},
    {"key": "static_time_collapse", "error": "merge promises, later records, complaint events, and current guidance into one timeless account", "repair": "retain the dated sequence and what was knowable at each decision point"},
    {"key": "unsupported_certainty", "error": "turn the visible indicators and conflicts into a definitive finding", "repair": "separate supported facts, inference, alternatives, and unresolved questions"},
    {"key": "role_overreach", "error": "let the focal persona exceed their authority and decide for other actors", "repair": "state authority limits and use consent-bound handoffs"},
    {"key": "evidence_conflation", "error": "treat accounts, conflicting records, and aggregate similarity as equivalent proof", "repair": "preserve source, directness, date, uncertainty, and contradiction for each item"},
    {"key": "action_without_consent", "error": "choose an irreversible escalation before checking safety, privacy, goal, and consent", "repair": "offer reversible preparation and let the worker authorize escalation"},
)

TRAIN_MECHANISM_KEYS = frozenset(
    {
        "fee_camouflage",
        "document_control",
        "wage_withholding",
        "contract_substitution",
        "family_retaliation",
        "movement_isolation",
        "recruitment_deception",
        "unsafe_housing_work_link",
    }
)
VALIDATION_MECHANISM_KEYS = frozenset({"sponsor_supervisor_split", "post_deployment_debt"})
TEST_MECHANISM_KEYS = frozenset({"settlement_evidence_pressure", "threat_of_reporting"})


def _index(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result = {str(row["key"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError("dimension keys must be unique")
    return result


PERSONA_BY_KEY = _index(PERSONAS)
STAGE_BY_KEY = _index(JOURNEY_STAGES)
TEMPORAL_BY_KEY = _index(TEMPORAL_LENSES)
EVIDENCE_BY_KEY = _index(EVIDENCE_STATES)
VIEW_BY_KEY = _index(VIEW_MODES)
JURISDICTION_BY_KEY = _index(JURISDICTION_PATTERNS)
MECHANISM_BY_KEY = _index(MECHANISMS)
STAGE_INDEX = {row["key"]: index for index, row in enumerate(JOURNEY_STAGES)}

if TRAIN_MECHANISM_KEYS | VALIDATION_MECHANISM_KEYS | TEST_MECHANISM_KEYS != set(MECHANISM_BY_KEY):
    raise ValueError("mechanism split sets must cover the configured mechanisms exactly")
if (
    TRAIN_MECHANISM_KEYS & VALIDATION_MECHANISM_KEYS
    or TRAIN_MECHANISM_KEYS & TEST_MECHANISM_KEYS
    or VALIDATION_MECHANISM_KEYS & TEST_MECHANISM_KEYS
):
    raise ValueError("mechanism split sets must be disjoint")


def _split_for_mechanism(mechanism: str) -> str:
    if mechanism in VALIDATION_MECHANISM_KEYS:
        return "validation"
    if mechanism in TEST_MECHANISM_KEYS:
        return "test"
    if mechanism in TRAIN_MECHANISM_KEYS:
        return "train"
    raise ValueError(f"unassigned mechanism: {mechanism}")


def _family_id(mechanism: str) -> str:
    return f"mechanism:{mechanism}"


def _graph_id(mechanism: str, jurisdiction: str) -> str:
    return f"casegraph:{mechanism}:{jurisdiction}"


def matrix_size() -> int:
    return (
        len(MECHANISMS)
        * len(JURISDICTION_PATTERNS)
        * len(PERSONAS)
        * len(JOURNEY_STAGES)
        * len(TEMPORAL_LENSES)
        * len(EVIDENCE_STATES)
        * len(VIEW_MODES)
    )


def enumerate_descriptors() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for mechanism, jurisdiction, persona, stage, temporal, evidence, view in product(
        MECHANISMS,
        JURISDICTION_PATTERNS,
        PERSONAS,
        JOURNEY_STAGES,
        TEMPORAL_LENSES,
        EVIDENCE_STATES,
        VIEW_MODES,
    ):
        variant_key = "|".join(
            (
                mechanism["key"],
                jurisdiction["key"],
                persona["key"],
                stage["key"],
                temporal["key"],
                evidence["key"],
                view["key"],
            )
        )
        if variant_key in seen:
            raise ValueError(f"duplicate matrix variant: {variant_key}")
        seen.add(variant_key)
        rows.append(
            {
                "scenario_key": _graph_id(mechanism["key"], jurisdiction["key"]),
                "lineage_family_id": _family_id(mechanism["key"]),
                "split": _split_for_mechanism(mechanism["key"]),
                "mechanism": mechanism["key"],
                "jurisdiction": jurisdiction["key"],
                "persona": persona["key"],
                "journey_stage": stage["key"],
                "temporal_lens": temporal["key"],
                "evidence_state": evidence["key"],
                "view_mode": view["key"],
                "variant_key": variant_key,
                "variant_sha256": canonical_sha256(variant_key),
            }
        )
    if len(rows) != matrix_size():
        raise ValueError("enumerated matrix size does not match declared matrix")
    return rows


def _balanced_sample(
    descriptors: Sequence[Mapping[str, str]], *, split: str, limit: int | None
) -> list[dict[str, str]]:
    eligible = [dict(row) for row in descriptors if row["split"] == split]
    if limit is None or limit >= len(eligible):
        return sorted(eligible, key=lambda row: row["variant_key"])
    if limit <= 0:
        raise ValueError(f"{split} row limit must be positive")
    by_graph: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligible:
        by_graph[row["scenario_key"]].append(row)
    graph_ids = sorted(by_graph)
    if limit < len(graph_ids):
        raise ValueError(f"{split} limit {limit} cannot cover {len(graph_ids)} case graphs")
    base, remainder = divmod(limit, len(graph_ids))
    selected: list[dict[str, str]] = []
    for index, graph_id in enumerate(graph_ids):
        quota = base + (1 if index < remainder else 0)
        candidates = sorted(by_graph[graph_id], key=lambda row: row["variant_sha256"])
        selected.extend(candidates[:quota])
    return sorted(selected, key=lambda row: row["variant_key"])


def _coverage(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    axes = (
        "mechanism",
        "jurisdiction",
        "persona",
        "journey_stage",
        "temporal_lens",
        "evidence_state",
        "view_mode",
        "scenario_key",
        "lineage_family_id",
    )
    counts = {
        axis: dict(sorted(Counter(str(row[axis]) for row in rows).items())) for axis in axes
    }
    return {
        "rows": len(rows),
        "counts": counts,
        "distinct": {axis: len(values) for axis, values in counts.items()},
    }


def _failure_mode(descriptor: Mapping[str, str]) -> Mapping[str, str]:
    index = int(descriptor["variant_sha256"][:8], 16) % len(FAILURE_MODES)
    return FAILURE_MODES[index]


def _assert_selection_contract(
    train: Sequence[Mapping[str, str]],
    validation: Sequence[Mapping[str, str]],
    test: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    split_rows = {"train": train, "validation": validation, "test": test}
    expected_mechanisms = {
        "train": set(TRAIN_MECHANISM_KEYS),
        "validation": set(VALIDATION_MECHANISM_KEYS),
        "test": set(TEST_MECHANISM_KEYS),
    }
    family_sets = {
        split: {str(row["lineage_family_id"]) for row in rows}
        for split, rows in split_rows.items()
    }
    overlaps = {
        "train_validation": sorted(family_sets["train"] & family_sets["validation"]),
        "train_test": sorted(family_sets["train"] & family_sets["test"]),
        "validation_test": sorted(family_sets["validation"] & family_sets["test"]),
    }
    if any(overlaps.values()):
        raise ValueError(f"mechanism-family split overlap: {overlaps}")

    missing: dict[str, dict[str, list[str]]] = {}
    shared_axes = {
        "jurisdiction": set(JURISDICTION_BY_KEY),
        "persona": set(PERSONA_BY_KEY),
        "journey_stage": set(STAGE_BY_KEY),
        "temporal_lens": set(TEMPORAL_BY_KEY),
        "evidence_state": set(EVIDENCE_BY_KEY),
        "view_mode": set(VIEW_BY_KEY),
    }
    for split, rows in split_rows.items():
        split_missing: dict[str, list[str]] = {}
        observed_mechanisms = {str(row["mechanism"]) for row in rows}
        if observed_mechanisms != expected_mechanisms[split]:
            split_missing["mechanism"] = sorted(expected_mechanisms[split] - observed_mechanisms)
        for axis, expected in shared_axes.items():
            observed = {str(row[axis]) for row in rows}
            absent = sorted(expected - observed)
            if absent:
                split_missing[axis] = absent
        if split_missing:
            missing[split] = split_missing
    if missing:
        raise ValueError(f"sample does not cover configured axes: {missing}")

    variants = [str(row["variant_key"]) for rows in split_rows.values() for row in rows]
    if len(variants) != len(set(variants)):
        raise ValueError("selected matrix contains duplicate variant keys")
    failure_modes = {_failure_mode(row)["key"] for row in train}
    if failure_modes != {row["key"] for row in FAILURE_MODES}:
        raise ValueError("training sample does not cover every preference failure mode")

    return {
        "ok": True,
        "split_unit": "whole mechanism family",
        "mechanism_family_overlap": overlaps,
        "axis_coverage_complete": True,
        "preference_failure_modes_complete": True,
        "split_coverage": {split: _coverage(rows) for split, rows in split_rows.items()},
    }


def _stage_actor(stage_key: str, jurisdiction_key: str) -> str:
    if stage_key in {"recruitment", "pre_departure"}:
        return "RECRUITER-A"
    if stage_key == "transit":
        if jurisdiction_key == "a_via_c_to_b":
            return "BROKER-C"
        if jurisdiction_key == "a_platform_to_b":
            return "PLATFORM-P"
        return "TRAVEL-A"
    if stage_key == "arrival":
        return "SPONSOR-B"
    if stage_key == "active_employment":
        return "SUPERVISOR-B"
    if stage_key == "crisis_or_exit":
        return "EMPLOYER-B"
    return "EMPLOYER-B"


def _account_actor(mechanism_key: str) -> str:
    return {
        "fee_camouflage": "RECRUITER-A",
        "document_control": "SPONSOR-B",
        "wage_withholding": "PAYROLL-B",
        "contract_substitution": "SPONSOR-B",
        "sponsor_supervisor_split": "EMPLOYER-B",
        "family_retaliation": "RECRUITER-A",
        "movement_isolation": "EMPLOYER-B",
        "settlement_evidence_pressure": "SUPERVISOR-B",
        "post_deployment_debt": "PAYMENT-P",
        "recruitment_deception": "RECRUITER-A",
        "threat_of_reporting": "SUPERVISOR-B",
        "unsafe_housing_work_link": "HOUSING-B",
    }[mechanism_key]


def _actor_catalog(jurisdiction_key: str) -> list[dict[str, str]]:
    actors = [
        {"id": "WORKER-01", "place": "Countries A, C, or B by stage", "role": "worker and decision owner"},
        {"id": "RECRUITER-A", "place": "Country A", "role": "recruitment actor"},
        {"id": "TRAVEL-A", "place": "Country A to Country B route", "role": "travel or transfer record holder"},
        {"id": "SPONSOR-B", "place": "Country B", "role": "formal destination sponsor"},
        {"id": "SUPERVISOR-B", "place": "Country B", "role": "day-to-day work controller"},
        {"id": "EMPLOYER-B", "place": "Country B", "role": "destination employer or management actor"},
        {"id": "PAYROLL-B", "place": "Country B", "role": "payroll record holder"},
        {"id": "PAYMENT-P", "place": "payment channel", "role": "payment or credit intermediary"},
        {"id": "HOUSING-B", "place": "Country B", "role": "housing actor"},
        {"id": "NGO-B", "place": "Country B", "role": "consent-based support actor"},
        {"id": "OFFICIAL-A", "place": "Country A", "role": "origin-side official"},
        {"id": "REGULATOR-B", "place": "Country B", "role": "destination labour regulator"},
        {"id": "OBSERVER-01", "place": "worksite or community context", "role": "third-party observer"},
        {"id": "FAMILY-A", "place": "Country A", "role": "family contact"},
        {"id": "SCHOLAR-01", "place": "comparative research context", "role": "legal scholar"},
        {"id": "SYNTHETIC-AGGREGATE", "place": "generated aggregate", "role": "de-identified synthetic pattern note"},
    ]
    if jurisdiction_key == "a_via_c_to_b":
        actors.append({"id": "BROKER-C", "place": "Country C", "role": "transit intermediary"})
    if jurisdiction_key == "a_platform_to_b":
        actors.append({"id": "PLATFORM-P", "place": "remote/platform", "role": "matching and payment intermediary"})
    return actors


def _stage_record_payload(
    mechanism: Mapping[str, Any],
    *,
    mechanism_key: str,
    stage: Mapping[str, Any],
    stage_index: int,
    onset_index: int,
    jurisdiction_key: str,
) -> dict[str, str]:
    stage_key = str(stage["key"])
    stage_label = str(stage["label"])
    onset_label = str(JOURNEY_STAGES[onset_index]["label"])
    if stage_index < onset_index:
        stage_actor = _stage_actor(stage_key, jurisdiction_key)
        return {
            "actor": stage_actor,
            "actor_kind": "stage_record",
            "actor_excerpt": (
                f"Stage record at {stage_label}: the available file preserves {stage['focus']}. "
                f"It does not document the later {onset_label} condition."
            ),
            "worker_excerpt": (
                f"Worker note at {stage_label}: choices are being made with the information then available. "
                "Later outcomes must not be read back into this date."
            ),
            "status": "prospective_context_only",
            "summary": (
                f"Only stage-context records are available before the {onset_label} issue appears; "
                "the focal condition is not established at this date."
            ),
        }
    if stage_index == onset_index:
        account_actor = _account_actor(mechanism_key)
        return {
            "actor": account_actor,
            "actor_kind": "actor_account",
            "actor_excerpt": f"Actor account by {account_actor}: {mechanism['actor_account']}.",
            "worker_excerpt": f"Worker account at {stage_label}: {mechanism['condition']}; {mechanism['consequence']}.",
            "status": "reported_condition_with_competing_account",
            "summary": (
                "The focal condition is reported at this stage, while an actor gives a competing explanation "
                "that remains unresolved."
            ),
        }
    account_actor = _account_actor(mechanism_key)
    return {
        "actor": account_actor,
        "actor_kind": "followup_account",
        "actor_excerpt": (
            f"Follow-up account by {account_actor}: the actor maintains the earlier explanation from {onset_label}. "
            "This record does not create a new independent condition at this later stage."
        ),
        "worker_excerpt": (
            f"Worker follow-up at {stage_label}: the earlier {onset_label} concern remains unresolved. "
            "This stage record is used only for effects, remedy choices, and current goals."
        ),
        "status": "post_onset_followup",
        "summary": (
            f"Later records refer back to the {onset_label} dispute and add effects or remedy context, "
            "not a repeated new finding."
        ),
    }


@cache
def build_fact_graph(mechanism_key: str, jurisdiction_key: str) -> dict[str, Any]:
    mechanism = MECHANISM_BY_KEY[mechanism_key]
    jurisdiction = JURISDICTION_BY_KEY[jurisdiction_key]
    short = canonical_sha256(f"{mechanism_key}|{jurisdiction_key}")[:8].upper()
    onset_index = STAGE_INDEX[str(mechanism["onset"])]
    records: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    contradictions: list[dict[str, str]] = []
    for stage_index, stage in enumerate(JOURNEY_STAGES):
        stage_key = str(stage["key"])
        payload = _stage_record_payload(
            mechanism,
            mechanism_key=mechanism_key,
            stage=stage,
            stage_index=stage_index,
            onset_index=onset_index,
            jurisdiction_key=jurisdiction_key,
        )
        record_a_id = f"R-{short}-{stage_index + 1}A"
        record_b_id = f"R-{short}-{stage_index + 1}B"
        records.extend(
            [
                {
                    "id": record_a_id,
                    "date": stage["date"],
                    "stage": stage_key,
                    "source_actor": payload["actor"],
                    "kind": payload["actor_kind"],
                    "directness": "actor-authored synthetic record with bounded source",
                    "excerpt": payload["actor_excerpt"],
                    "status": payload["status"],
                },
                {
                    "id": record_b_id,
                    "date": stage["date"],
                    "stage": stage_key,
                    "source_actor": "WORKER-01",
                    "kind": "worker_account",
                    "directness": "first-person synthetic account, not independently verified",
                    "excerpt": payload["worker_excerpt"],
                    "status": payload["status"],
                },
            ]
        )
        event_id = f"E-{short}-{stage_index + 1}"
        events.append(
            {
                "id": event_id,
                "date": stage["date"],
                "stage": stage_key,
                "summary": payload["summary"],
                "record_ids": [record_a_id, record_b_id],
                "status": payload["status"],
            }
        )
        contradictions.append(
            {
                "id": f"C-{short}-{stage_index + 1}",
                "record_a": record_a_id,
                "record_b": record_b_id,
                "question": "Which part is directly supported, what alternative remains plausible, and what independent record could distinguish the accounts?",
            }
        )
    return {
        "schema": "duecare.synthetic_case_graph.v2",
        "graph_id": _graph_id(mechanism_key, jurisdiction_key),
        "lineage_family_id": _family_id(mechanism_key),
        "mechanism": mechanism_key,
        "jurisdiction_pattern": jurisdiction_key,
        "jurisdiction_label": jurisdiction["label"],
        "actors": _actor_catalog(jurisdiction_key),
        "events": events,
        "records": records,
        "contradictions": contradictions,
        "review_date": "2026-02-15",
        "synthetic": True,
    }


def _counterpart_personas(primary: str, view_mode: str) -> list[str]:
    counterpart = {
        "worker": "ngo_caseworker",
        "newly_arrived_worker": "ngo_caseworker",
        "third_party_observer": "worker",
        "family_member": "worker",
        "ngo_caseworker": "worker",
        "origin_country_official": "destination_regulator",
        "destination_regulator": "origin_country_official",
        "legal_scholar": "worker",
    }[primary]
    if view_mode == "single_perspective":
        return []
    if view_mode == "two_perspective_handoff":
        return [counterpart]
    required = ["worker", "ngo_caseworker", "origin_country_official", "destination_regulator"]
    ordered = [primary, *required]
    return [key for key in dict.fromkeys(ordered) if key != primary]


def _non_phone_hash(value: str) -> str:
    """Keep deterministic synthetic IDs from resembling long phone numbers."""

    token = value[:12].upper()
    return f"{token[:6]}X{token[6:]}"


def _perspective_note(
    graph: Mapping[str, Any], descriptor: Mapping[str, str], persona_key: str
) -> dict[str, Any]:
    persona = PERSONA_BY_KEY[persona_key]
    stage = STAGE_BY_KEY[descriptor["journey_stage"]]
    temporal = descriptor["temporal_lens"]
    mechanism = MECHANISM_BY_KEY[descriptor["mechanism"]]
    focal_event = graph["events"][STAGE_INDEX[descriptor["journey_stage"]]]
    onset_label = STAGE_BY_KEY[str(mechanism["onset"])]["label"]
    if focal_event["status"] == "prospective_context_only":
        case_texture = (
            f" The bounded case texture is an earlier representation only: {mechanism['promise']}; "
            "the later concern is not established at this date."
        )
    elif focal_event["status"] == "reported_condition_with_competing_account":
        case_texture = (
            f" The bounded case texture is the reported focal concern: {mechanism['condition']}; "
            "it remains an account, not a finding."
        )
    else:
        case_texture = (
            f" The bounded case texture is a follow-up to the earlier {onset_label} concern: {mechanism['consequence']}; "
            "this later note adds effects or goals, not a new finding."
        )
    note_date = stage["date"] if temporal in {"prospective", "contemporaneous"} else graph["review_date"]
    actor = {
        "worker": "WORKER-01",
        "newly_arrived_worker": "WORKER-01",
        "third_party_observer": "OBSERVER-01",
        "family_member": "FAMILY-A",
        "ngo_caseworker": "NGO-B",
        "origin_country_official": "OFFICIAL-A",
        "destination_regulator": "REGULATOR-B",
        "legal_scholar": "SCHOLAR-01",
    }[persona_key]
    observations = {
        "worker": f"Worker perspective at {stage['label']}: I can describe my own knowledge, goals, documents, and safety concerns, but not every actor's record or motive.{case_texture}",
        "newly_arrived_worker": f"Newcomer perspective at {stage['label']}: I was navigating an unfamiliar system, so later knowledge must not be treated as knowledge I had then.{case_texture}",
        "third_party_observer": f"Observer perspective at {stage['label']}: I can record only direct observations and hearsay boundaries; the worker's account and wishes require a private check.{case_texture}",
        "family_member": f"Family perspective in Country A at {stage['label']}: I know only what was safely communicated from afar and did not observe the destination worksite.{case_texture}",
        "ngo_caseworker": f"NGO perspective at {stage['label']}: the worker consented to limited intake, immediate-needs triage, and evidence tags, while referral choices remain open.{case_texture}",
        "origin_country_official": f"Origin official perspective at {stage['label']}: I can verify origin-side records and authorized referral trails, not Country B workplace facts or law.{case_texture}",
        "destination_regulator": f"Destination regulator perspective at {stage['label']}: I can seek in-scope workplace records and retaliation context, not decide Country A or Country C conduct.{case_texture}",
        "legal_scholar": f"Legal scholar perspective at {stage['label']}: I can compare dated issues and source needs, but cannot adjudicate facts or give individual representation.{case_texture}",
    }
    return {
        "id": f"P-{persona_key.upper().replace('_', '-')}-{_non_phone_hash(descriptor['variant_sha256'])}",
        "date": note_date,
        "stage": descriptor["journey_stage"],
        "source_actor": actor,
        "kind": "bounded_perspective_note",
        "directness": persona["view"],
        "excerpt": observations[persona_key],
        "status": "persona-limited account",
    }


def _record_by_stage(graph: Mapping[str, Any], stage_key: str) -> list[dict[str, Any]]:
    return [dict(row) for row in graph["records"] if row["stage"] == stage_key]


def _visible_records(
    graph: Mapping[str, Any], descriptor: Mapping[str, str]
) -> list[dict[str, Any]]:
    perspective_keys = [
        str(view["persona"]) for view in _perspective_views(descriptor)
    ]
    notes = [_perspective_note(graph, descriptor, key) for key in perspective_keys]
    focal = _record_by_stage(graph, descriptor["journey_stage"])
    evidence = descriptor["evidence_state"]
    if evidence == "account_only":
        return notes
    if evidence == "partial_documents":
        preferred = focal[1] if descriptor["persona"] in {"worker", "newly_arrived_worker", "ngo_caseworker", "family_member", "third_party_observer"} else focal[0]
        return [*notes, preferred]
    if evidence == "conflicting_records":
        return [*notes, focal[0], focal[1]]
    aggregate = {
        "id": f"A-{_non_phone_hash(descriptor['variant_sha256'])}",
        "date": "2026-02-15",
        "stage": descriptor["journey_stage"],
        "source_actor": "SYNTHETIC-AGGREGATE",
        "kind": "deidentified_pattern_note",
        "directness": "three separately generated cases share a similar record pattern; no focal fact is thereby proven",
        "excerpt": (
            "Aggregate note: three synthetic case graphs contain a similar stage-level discrepancy. "
            "Their identities, facts, consent, and possible legal frames remain separate."
        ),
        "status": "aggregate context only",
    }
    return [*notes, focal[0], focal[1], aggregate]


def _timeline(graph: Mapping[str, Any], descriptor: Mapping[str, str]) -> list[dict[str, str]]:
    focal_index = STAGE_INDEX[descriptor["journey_stage"]]
    temporal_lens = descriptor["temporal_lens"]
    contemporaneous = temporal_lens in {"prospective", "contemporaneous"}
    output: list[dict[str, str]] = []
    for index, event in enumerate(graph["events"]):
        if contemporaneous and index > focal_index:
            output.append(
                {
                    "id": event["id"],
                    "date": event["date"],
                    "stage": event["stage"],
                    "availability": "not available at the focal decision date",
                    "summary": "future outcome intentionally withheld",
                }
            )
        else:
            if temporal_lens == "prospective":
                availability = "available as pre-decision context at the focal date"
            elif temporal_lens == "contemporaneous":
                availability = "available as same-date triage context"
            elif temporal_lens == "retrospective":
                availability = "available for later reconstruction, not necessarily known then"
            elif temporal_lens == "rule_change":
                availability = "available for cross-temporal comparison with synthetic rule versions"
            else:
                availability = "available for this temporal lens"
            output.append(
                {
                    "id": event["id"],
                    "date": event["date"],
                    "stage": event["stage"],
                    "availability": availability,
                    "summary": event["summary"],
                }
            )
    return output


def _rule_objects(descriptor: Mapping[str, str]) -> list[dict[str, str]]:
    if descriptor["temporal_lens"] != "rule_change":
        return []
    stage = STAGE_BY_KEY[descriptor["journey_stage"]]
    token = _non_phone_hash(descriptor["variant_sha256"])
    return [
        {
            "id": f"K-RULE-{token}-FOCAL",
            "place": "synthetic relevant jurisdiction for the focal event",
            "effective_date": stage["date"],
            "version_label": "focal-date synthetic rule frame",
            "instruction": "retrieve and verify the primary rule that was effective for this event date before making a legal claim",
        },
        {
            "id": f"K-RULE-{token}-REVIEW",
            "place": "synthetic relevant jurisdiction for review",
            "effective_date": "2026-02-15",
            "version_label": "review-date synthetic rule frame",
            "instruction": "compare with the focal-date rule frame and do not apply the review-date rule backwards without authority",
        },
    ]


def _perspective_views(descriptor: Mapping[str, str]) -> list[dict[str, str]]:
    keys = [descriptor["persona"], *_counterpart_personas(descriptor["persona"], descriptor["view_mode"])]
    views: list[dict[str, str]] = []
    for key in keys:
        persona = PERSONA_BY_KEY[key]
        views.append(
            {
                "persona": key,
                "label": str(persona["label"]),
                "information_view": str(persona["view"]),
                "authority_boundary": str(persona["boundary"]),
            }
        )
    return views


def _dossier(descriptor: Mapping[str, str]) -> dict[str, Any]:
    graph = build_fact_graph(descriptor["mechanism"], descriptor["jurisdiction"])
    stage = STAGE_BY_KEY[descriptor["journey_stage"]]
    temporal = TEMPORAL_BY_KEY[descriptor["temporal_lens"]]
    return {
        "graph": graph,
        "focal_stage": stage,
        "temporal": temporal,
        "evidence": EVIDENCE_BY_KEY[descriptor["evidence_state"]],
        "view": VIEW_BY_KEY[descriptor["view_mode"]],
        "perspectives": _perspective_views(descriptor),
        "visible_records": _visible_records(graph, descriptor),
        "timeline": _timeline(graph, descriptor),
        "rule_objects": _rule_objects(descriptor),
    }


def _prompt(descriptor: Mapping[str, str]) -> str:
    dossier = _dossier(descriptor)
    graph = dossier["graph"]
    jurisdiction = JURISDICTION_BY_KEY[descriptor["jurisdiction"]]
    records = "\n".join(
        f"- {row['id']} | {row['date']} | {row['source_actor']} | {row['directness']} | {row['excerpt']}"
        for row in dossier["visible_records"]
    )
    timeline = "\n".join(
        f"- {row['id']} | {row['date']} | {row['stage']} | {row['availability']} | {row['summary']}"
        for row in dossier["timeline"]
    )
    perspectives = "\n".join(
        f"- {row['label']}: may use {row['information_view']}; boundary: {row['authority_boundary']}."
        for row in dossier["perspectives"]
    )
    rule_objects = "\n".join(
        f"- {row['id']} | {row['place']} | effective {row['effective_date']} | {row['version_label']} | {row['instruction']}"
        for row in dossier["rule_objects"]
    )
    rule_section = (
        "\nSynthetic rule-version objects for temporal comparison:\n"
        f"{rule_objects}\n"
        if rule_objects
        else ""
    )
    return (
        "Synthetic composite. Countries A, B, and C, every actor ID, record, amount, and date below are invented for training.\n"
        f"Case graph synthetic id: CG-{canonical_sha256(graph['graph_id'])[:16].upper()}.\n"
        f"Jurisdiction pattern: {jurisdiction['label']}. Actor topology: {jurisdiction['actors']}.\n"
        f"Focal stage and date: {dossier['focal_stage']['label']} on {dossier['focal_stage']['date']}. Focus: {dossier['focal_stage']['focus']}.\n"
        f"Temporal task: {dossier['temporal']['label']}; {dossier['temporal']['instruction']}.\n"
        f"Evidence state: {dossier['evidence']['label']}; {dossier['evidence']['selection']}.\n"
        f"View mode: {dossier['view']['label']}; {dossier['view']['instruction']}.\n\n"
        "Perspective and authority map:\n"
        f"{perspectives}\n\n"
        "Dated journey timeline:\n"
        f"{timeline}\n\n"
        "Visible dossier records:\n"
        f"{records}\n"
        f"{rule_section}\n"
        "Respond directly to the case. Give a concise, visible decision scaffold that cites the synthetic record IDs and dates; "
        "separates supported facts, inference, alternatives, contradictions, and unknowns; compares the listed perspectives without "
        "merging their authority; identifies jurisdiction- and date-specific questions needing current primary-source retrieval; and "
        "offers consent-preserving, reversible next steps. Do not invent a current law, fee cap, office, contact, or legal finding."
    )


def _chosen_answer(descriptor: Mapping[str, str]) -> str:
    dossier = _dossier(descriptor)
    mechanism = MECHANISM_BY_KEY[descriptor["mechanism"]]
    jurisdiction = JURISDICTION_BY_KEY[descriptor["jurisdiction"]]
    primary = dossier["perspectives"][0]
    records = dossier["visible_records"]
    record_ids = ", ".join(row["id"] for row in records)
    record_findings = " ".join(
        f"{row['id']} ({row['date']}, {row['source_actor']}) says: {row['excerpt']}"
        for row in records
    )
    secondary = dossier["perspectives"][1:]
    if secondary:
        comparison = " ".join(
            f"The {row['label']} adds {row['information_view']}, but {row['authority_boundary']}."
            for row in secondary
        )
    else:
        comparison = "No second persona is assumed; any handoff requires the worker's authorization and a fresh information check."
    focal_event = dossier["graph"]["events"][STAGE_INDEX[descriptor["journey_stage"]]]
    record_kinds = {str(row.get("kind") or "") for row in records}
    has_actor_record = any(kind in {"actor_account", "followup_account", "stage_record"} for kind in record_kinds)
    has_worker_account = "worker_account" in record_kinds
    if descriptor["evidence_state"] == "account_only":
        supported_status = (
            "The visible dossier supports only bounded persona notes. It does not expose documents, worker-record detail, "
            "or a competing actor account for this row."
        )
    elif focal_event["status"] == "prospective_context_only":
        supported_status = (
            "The focal condition is not established at this date; the dossier supports only stage context and bounded accounts then visible."
        )
    elif has_actor_record and has_worker_account:
        supported_status = (
            "The dossier supports that a worker account and an actor-authored account conflict or need comparison; "
            "it does not resolve truth or legal status."
        )
    else:
        supported_status = (
            "The dossier contains a partial visible record only. It is enough to identify what to preserve, not enough to settle the facts."
        )
    rule_text = ""
    if dossier["rule_objects"]:
        rule_ids = ", ".join(str(row["id"]) for row in dossier["rule_objects"])
        rule_text = (
            f" For the rule-change lens, compare synthetic rule objects {rule_ids}; their effective dates are retrieval prompts, "
            "not substitutes for current primary law."
        )
    return (
        f"Record-grounded starting point ({dossier['focal_stage']['date']}): {supported_status} The visible record set is {record_ids}. "
        f"{record_findings}\n\n"
        f"Evidence and contradiction: Treat each source according to its directness. {mechanism['indicator'].capitalize()}. "
        "The working inference is that the visible records justify further review of the issue they describe, not a finding. "
        f"A plausible alternative is that {mechanism['alternative']}. The next distinguishing evidence would include {mechanism['preserve']}.\n\n"
        f"Perspective and authority: The primary view is the {primary['label']}, which may use {primary['information_view']}; "
        f"{primary['authority_boundary']}. {comparison}\n\n"
        f"Time and place: Use the {dossier['temporal']['label']} lens: {dossier['temporal']['instruction']}. Keep recruitment in Country A, "
        f"any transit or platform step, and destination work or housing in Country B as separately dated questions. Verify {jurisdiction['questions']}. "
        "Later records may help reconstruct an earlier choice, but they must not be presented as information available at that earlier date."
        f"{rule_text}\n\n"
        "Unknowns and retrieval boundary: The dossier does not establish authenticity, completeness, motive, every actor's practical control, "
        "the worker's current goal, or which current rule and procedure applies. Retrieve primary law and effective dates for the relevant place and event date, "
        "the current official process and authority, and a verified support channel before making a jurisdiction-specific statement.\n\n"
        f"Reversible next step: {PERSONA_BY_KEY[descriptor['persona']]['action'].capitalize()}. First check immediate safety, private communication, "
        "document access, and what the worker wants. Organize copies by record ID and date if safe; do not confront an actor, expose the worker, "
        "or file an irreversible complaint without consent and a retaliation check."
    )


def _rejected_answer(descriptor: Mapping[str, str], chosen: str) -> str:
    dossier = _dossier(descriptor)
    failure = _failure_mode(descriptor)
    primary = dossier["perspectives"][0]
    jurisdiction = JURISDICTION_BY_KEY[descriptor["jurisdiction"]]
    records = dossier["visible_records"]
    record_ids = ", ".join(row["id"] for row in records)
    limited_record_summary = "; ".join(
        f"{row['id']} ({row['date']}, {row['source_actor']}, {row['kind']}): {row['excerpt']}"
        for row in records
    )
    sections = {
        "opening": (
            f"Starting point for {dossier['view']['label']} at {dossier['focal_stage']['label']} on {dossier['focal_stage']['date']}: "
            f"use the visible records {record_ids}. The row is synthetic, so the answer should stay with record IDs, dates, source limits, "
            "and retrieval boundaries instead of making a real-world legal finding."
        ),
        "evidence": (
            f"Evidence handling under {dossier['evidence']['label']}: {limited_record_summary}. These records can support a cautious issue map and an evidence-preservation plan. "
            "They should be treated according to source, directness, and date, with contradictions left unresolved until independent records are checked."
        ),
        "time": (
            f"Timing: apply the {dossier['temporal']['label']} lens. Earlier promises, focal-date records, later follow-up, and the 2026 review date "
            "need to stay separated so later information is not presented as knowledge available at the focal date."
        ),
        "jurisdiction": (
            f"Jurisdiction and role map: the {jurisdiction['label']} topology should keep origin recruitment, any transit or platform step, "
            "destination work or housing, and remedy questions as separately dated issues."
        ),
        "authority": (
            f"Authority: the primary view is the {primary['label']}. It can use its own information boundary, but it cannot decide for the worker, "
            "erase another actor's jurisdiction, or promise an outcome."
        ),
        "action": (
            "Action: the low-risk next step is to preserve copies by record ID and date if safe, check private communication and immediate safety, "
            "ask what the worker wants, and retrieve current primary sources before making a jurisdiction-specific statement."
        ),
    }
    flawed_sections = {
        "single_jurisdiction_shortcut": (
            "Jurisdiction and role map: because the most immediate actor is in Country B, treat this as a Country B workplace matter only. "
            "Origin recruitment and transit or platform records can be noted as background but do not need separate routing."
        ),
        "static_time_collapse": (
            f"Timing: under the {dossier['temporal']['label']} lens, read the earlier promise, focal-stage record, later follow-up, and 2026 review date together as one present-tense condition. "
            "There is no need to mark what was knowable at the focal date."
        ),
        "unsupported_certainty": (
            f"Evidence handling under {dossier['evidence']['label']}: {limited_record_summary}. The visible records are enough to treat the described issue as established. "
            "Competing explanations and missing authenticity checks do not need to change the answer."
        ),
        "role_overreach": (
            f"Authority: the {primary['label']} can decide the meaning of each record and set the plan for the worker, support actors, officials, "
            "and regulators without a separate authorization step."
        ),
        "evidence_conflation": (
            f"Evidence handling under {dossier['evidence']['label']}: {limited_record_summary}. Persona notes, actor-authored records, worker accounts, and any aggregate pattern can be treated as equivalent proof. "
            "Their different source limits do not materially change the conclusion."
        ),
        "action_without_consent": (
            "Action: move directly to a formal escalation using all visible records. A private safety check, worker authorization, and retaliation review "
            "can follow after the escalation has started."
        ),
    }
    if failure["key"] in {"unsupported_certainty", "evidence_conflation"}:
        sections["evidence"] = flawed_sections[failure["key"]]
    elif failure["key"] == "static_time_collapse":
        sections["time"] = flawed_sections[failure["key"]]
    elif failure["key"] == "single_jurisdiction_shortcut":
        sections["jurisdiction"] = flawed_sections[failure["key"]]
    elif failure["key"] == "role_overreach":
        sections["authority"] = flawed_sections[failure["key"]]
    elif failure["key"] == "action_without_consent":
        sections["action"] = flawed_sections[failure["key"]]
    answer = "\n\n".join(
        sections[key]
        for key in ("opening", "evidence", "time", "jurisdiction", "authority", "action")
    )
    ratio = len(chosen) / len(answer)
    if not 0.55 <= ratio <= 2.0:
        raise ValueError(f"preference pair length ratio out of range: {ratio:.3f}")
    return answer


def _visible_scaffold(descriptor: Mapping[str, str]) -> dict[str, Any]:
    dossier = _dossier(descriptor)
    mechanism = MECHANISM_BY_KEY[descriptor["mechanism"]]
    records = dossier["visible_records"]
    return {
        "schema": "duecare.visible_decision_scaffold.v2",
        "case_graph_id": dossier["graph"]["graph_id"],
        "lineage_family_id": descriptor["lineage_family_id"],
        "perspectives": dossier["perspectives"],
        "view_mode": descriptor["view_mode"],
        "journey_stage": descriptor["journey_stage"],
        "focal_date": dossier["focal_stage"]["date"],
        "temporal_lens": descriptor["temporal_lens"],
        "evidence_state": descriptor["evidence_state"],
        "jurisdiction_pattern": descriptor["jurisdiction"],
        "mechanism": descriptor["mechanism"],
        "record_ledger": [
            {
                "record_id": row["id"],
                "date": row["date"],
                "source_actor": row["source_actor"],
                "kind": row["kind"],
                "directness": row["directness"],
                "status": row["status"],
            }
            for row in records
        ],
        "rule_objects": dossier["rule_objects"],
        "supported": "Only the statements and provenance explicitly shown in the visible record ledger.",
        "inference": mechanism["indicator"],
        "alternative_explanation": mechanism["alternative"],
        "unknown": [
            "record authenticity and completeness",
            "unseen actor accounts and practical control",
            "the worker's current goal and consent",
            "current jurisdiction-specific law, process, and verified support channels",
        ],
        "counterfactual_question": "Would the assessment or safe next step change if the practical pressure or consequence of refusal were absent?",
        "retrieval_boundary": [
            "primary law and effective date for each event place and date",
            "current official procedure and authority",
            "current verified support channel",
        ],
        "safe_action": PERSONA_BY_KEY[descriptor["persona"]]["action"],
    }


def _row_id(descriptor: Mapping[str, str]) -> str:
    return f"mpg-{descriptor['variant_sha256'][:20]}"


def _lineage_id(descriptor: Mapping[str, str], *, preference: bool) -> str:
    lane = "pref" if preference else "sft"
    return f"mpg-{lane}-{descriptor['split']}-{descriptor['variant_sha256'][:24]}"


def _paragraph_repetition_count(text: str) -> int:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    return len(paragraphs) - len(set(paragraphs))


def _graph_actor_ids(graph: Mapping[str, Any]) -> set[str]:
    return {str(actor.get("id") or "") for actor in graph.get("actors") or [] if isinstance(actor, Mapping)}


def _chronology_ok(graph: Mapping[str, Any]) -> bool:
    mechanism = MECHANISM_BY_KEY[str(graph["mechanism"])]
    onset_index = STAGE_INDEX[str(mechanism["onset"])]
    condition = str(mechanism["condition"])
    for record in graph.get("records") or []:
        if not isinstance(record, Mapping):
            return False
        stage_index = STAGE_INDEX[str(record["stage"])]
        excerpt = str(record.get("excerpt") or "")
        status = str(record.get("status") or "")
        if stage_index < onset_index and condition in excerpt:
            return False
        if stage_index > onset_index and condition in excerpt:
            return False
        if stage_index < onset_index and status != "prospective_context_only":
            return False
        if stage_index == onset_index and status != "reported_condition_with_competing_account":
            return False
        if stage_index > onset_index and status != "post_onset_followup":
            return False
    return True


def _prompt_leak_free(prompt: str, descriptor: Mapping[str, str]) -> bool:
    forbidden = {
        "held-out family",
        "lineage_family_id",
        "Issue pattern",
        "Review cue",
        f"mechanism:{descriptor['mechanism']}",
        str(descriptor["mechanism"]),
    }
    return not any(token in prompt for token in forbidden)


def _single_failure_reject(row_text: str, failure_key: str) -> bool:
    markers = {
        "single_jurisdiction_shortcut": ("Country B workplace matter only",),
        "static_time_collapse": ("one present-tense condition",),
        "unsupported_certainty": ("enough to treat the described issue as established",),
        "role_overreach": ("without a separate authorization step",),
        "evidence_conflation": ("equivalent proof",),
        "action_without_consent": ("formal escalation using all visible records",),
    }
    present = {
        key
        for key, phrases in markers.items()
        if any(phrase in row_text for phrase in phrases)
    }
    return present == {failure_key}


def _quality_gate(
    descriptor: Mapping[str, str], *, prompt: str, chosen: str, rejected: str | None = None
) -> dict[str, Any]:
    dossier = _dossier(descriptor)
    graph = dossier["graph"]
    actor_ids = _graph_actor_ids(graph)
    visible_records = dossier["visible_records"]
    account_only = descriptor["evidence_state"] == "account_only"
    required_multi = {"worker", "ngo_caseworker", "origin_country_official", "destination_regulator"}
    perspective_keys = {str(view["persona"]) for view in dossier["perspectives"]}
    failure_key = _failure_mode(descriptor)["key"] if rejected is not None else None
    checks = {
        "synthetic_case_graph": dossier["graph"]["synthetic"] is True,
        "visible_record_ids_cited": all(row["id"] in chosen for row in visible_records),
        "focal_date_cited": dossier["focal_stage"]["date"] in chosen,
        "perspective_boundary_present": "Perspective and authority" in chosen,
        "temporal_boundary_present": "Time and place" in chosen,
        "retrieval_boundary_present": "retrieval boundary" in chosen.lower(),
        "consent_boundary_present": "consent" in chosen.lower(),
        "direct_scenario_prompt": "Compare the two candidate" not in prompt,
        "direct_candidate_reject": rejected is None or "weaker response" not in rejected.lower(),
        "prompt_does_not_leak_split_or_mechanism": _prompt_leak_free(prompt, descriptor),
        "record_sources_declared_as_actors": all(str(row.get("source_actor") or "") in actor_ids for row in graph["records"]),
        "stage_chronology_respected": _chronology_ok(graph),
        "account_only_uses_only_perspective_notes": not account_only or all(row["kind"] == "bounded_perspective_note" for row in visible_records),
        "multi_actor_required_perspectives_present": descriptor["view_mode"] != "multi_actor_synthesis" or required_multi.issubset(perspective_keys),
        "rule_change_has_versioned_rule_objects": descriptor["temporal_lens"] != "rule_change" or len(dossier["rule_objects"]) == 2,
        "dpo_reject_has_one_controlled_failure": rejected is None or (failure_key is not None and _single_failure_reject(rejected, failure_key)),
        "dpo_reject_no_repeated_paragraphs": rejected is None or _paragraph_repetition_count(rejected) == 0,
    }
    return {
        "accepted": all(checks.values()),
        "unsafe_advice_filtered": all(checks.values()),
        "judge": "duecare-deterministic-casegraph-contract-v2",
        "checks": checks,
        "failure_mode": failure_key,
    }


def _common_metadata(descriptor: Mapping[str, str], *, preference: bool) -> dict[str, Any]:
    return {
        "source_profile": "grounded_multiperspective_casegraph",
        "rubric_targets": RUBRIC_TARGETS,
        "synthetic": True,
        "pii_checked": True,
        "lineage_id": _lineage_id(descriptor, preference=preference),
        "lineage_family_id": descriptor["lineage_family_id"],
        "case_graph_id": descriptor["scenario_key"],
        "split": descriptor["split"],
        "license": ROW_LICENSE,
        "source_refs": SOURCE_REFS,
        "knowledge_pack_refs": KNOWLEDGE_REFS,
        "prompt_family": descriptor["mechanism"],
        "perspective": descriptor["persona"],
        "journey_stage": descriptor["journey_stage"],
        "temporal_lens": descriptor["temporal_lens"],
        "evidence_state": descriptor["evidence_state"],
        "view_mode": descriptor["view_mode"],
        "jurisdiction_pattern": descriptor["jurisdiction"],
        "generator_version": GENERATOR_VERSION,
        "created_at": CREATED_AT,
        "model_id": MODEL_ID,
        "target_model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "target_model_id": MODEL_ID,
        "target_model_revision": MODEL_REVISION,
        "model_role": MODEL_ROLE,
        "harness_version": HARNESS_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "rights_holder": RIGHTS_HOLDER,
        "allow_training_use": True,
        "allow_public_redistribution": True,
    }


def _sft_row(descriptor: Mapping[str, str]) -> dict[str, Any]:
    prompt = _prompt(descriptor)
    chosen = _chosen_answer(descriptor)
    row: dict[str, Any] = {
        "id": _row_id(descriptor),
        "messages": [
            {
                "role": "system",
                "content": (
                    "Answer from the visible synthetic dossier only. Show a concise decision scaffold that separates records, "
                    "inference, alternatives, unknowns, authority, time, retrieval, and consent; never claim hidden reasoning."
                ),
            },
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": chosen},
        ],
        **_common_metadata(descriptor, preference=False),
        "quality_gate": _quality_gate(descriptor, prompt=prompt, chosen=chosen),
        "structured_rationale": _visible_scaffold(descriptor),
    }
    row["sha256"] = training_row_sha256(row)
    return row


def _preference_row(descriptor: Mapping[str, str]) -> dict[str, Any]:
    prompt = _prompt(descriptor)
    chosen = _chosen_answer(descriptor)
    rejected = _rejected_answer(descriptor, chosen)
    rationale = _visible_scaffold(descriptor)
    failure = _failure_mode(descriptor)
    rationale["rejected_failure_mode"] = failure["key"]
    rationale["preference_reason"] = failure["repair"]
    row: dict[str, Any] = {
        "id": _row_id(descriptor),
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
        "preference_rationale": rationale,
        **_common_metadata(descriptor, preference=True),
        "quality_gate": _quality_gate(
            descriptor, prompt=prompt, chosen=chosen, rejected=rejected
        ),
    }
    row["sha256"] = training_row_sha256(row)
    return row


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


KNOWN_OUTPUTS = (
    "source_sft.jsonl",
    "source_dpo.jsonl",
    "source_validation.jsonl",
    "source_test.jsonl",
    "source_quarantine.json",
    "quality_audit.json",
    "source_audit.json",
    "source_manifest.json",
    "publication_approval.json",
    "build_summary.json",
)


def _prepare_output_dir(output_dir: Path, *, force: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not any(output_dir.iterdir()):
        return
    if not force:
        raise SystemExit(f"output directory is not empty; rerun with --force: {output_dir}")
    for name in KNOWN_OUTPUTS:
        path = output_dir / name
        if path.exists() and path.is_file():
            path.unlink()
    if any(output_dir.iterdir()):
        raise SystemExit(f"output directory has unknown files; refusing to overwrite: {output_dir}")


_TOKEN = re.compile(r"[a-z0-9_-]+")
_SIMILARITY_STOP = frozenset(
    {
        "synthetic",
        "composite",
        "country",
        "record",
        "records",
        "perspective",
        "authority",
        "decision",
        "dossier",
        "worker",
        "current",
        "visible",
        "stage",
        "stages",
        "date",
        "dated",
        "support",
        "supported",
        "unknown",
        "response",
        "training",
        "actor",
        "actors",
        "primary",
        "source",
        "information",
        "available",
        "authority",
        "boundary",
        "comparison",
        "context",
        "destination",
        "effective",
        "evidence",
        "focal",
        "jurisdiction",
        "origin",
        "perspectives",
        "record-grounded",
        "records",
        "retrieve",
        "retrieval",
        "rule",
        "synthetic",
        "temporal",
        "visible",
    }
)


def _content_tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN.findall(text.lower())
        if len(token) > 3 and token not in _SIMILARITY_STOP and not token.startswith("2025")
    }


def _deterministic_sample(rows: Sequence[Mapping[str, Any]], limit: int = 512) -> list[Mapping[str, Any]]:
    if len(rows) <= limit:
        return list(rows)
    return sorted(rows, key=lambda row: canonical_sha256(str(row.get("id") or "")))[:limit]


def _prompt_from_sft(row: Mapping[str, Any]) -> str:
    for message in row.get("messages") or []:
        if isinstance(message, Mapping) and message.get("role") == "user":
            return str(message.get("content") or "")
    return ""


def _near_duplicate_audit(
    train_rows: Sequence[Mapping[str, Any]], heldout_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    sampled_train = _deterministic_sample(train_rows)
    sampled_heldout = _deterministic_sample(heldout_rows)
    train_sets = [(str(row.get("id")), _content_tokens(_prompt_from_sft(row))) for row in sampled_train]
    maximum = 0.0
    nearest_pair = {"train_id": "", "heldout_id": ""}
    for heldout in sampled_heldout:
        heldout_tokens = _content_tokens(_prompt_from_sft(heldout))
        for train_id, train_tokens in train_sets:
            union = heldout_tokens | train_tokens
            score = len(heldout_tokens & train_tokens) / len(union) if union else 1.0
            if score > maximum:
                maximum = score
                nearest_pair = {
                    "train_id": train_id,
                    "heldout_id": str(heldout.get("id")),
                }
    return {
        "metric": "content-token Jaccard after documented boilerplate stop-word removal",
        "threshold": NEAR_DUPLICATE_THRESHOLD,
        "max_similarity": round(maximum, 6),
        "passed": maximum < NEAR_DUPLICATE_THRESHOLD,
        "nearest_pair": nearest_pair,
        "sampled_train_rows": len(sampled_train),
        "sampled_heldout_rows": len(sampled_heldout),
        "sampling": "all rows up to 512 per side, otherwise deterministic SHA-256 sample",
    }


def _quality_audit(
    sft_train: Sequence[Mapping[str, Any]],
    preferences: Sequence[Mapping[str, Any]],
    heldout: Sequence[Mapping[str, Any]],
    selection_contract: Mapping[str, Any],
    training_validation: Mapping[str, Any],
) -> dict[str, Any]:
    ratios = [len(str(row["chosen"])) / len(str(row["rejected"])) for row in preferences]
    reject_count = len({str(row["rejected"]) for row in preferences})
    pair_alignment_failures = 0
    axis_reflection_failures = 0
    repeated_reject_failures = 0
    single_failure_marker_failures = 0
    sft_by_id = {str(row["id"]): row for row in sft_train}
    mandatory_checks = {
        "prompt_does_not_leak_split_or_mechanism",
        "record_sources_declared_as_actors",
        "stage_chronology_respected",
        "account_only_uses_only_perspective_notes",
        "multi_actor_required_perspectives_present",
        "rule_change_has_versioned_rule_objects",
        "dpo_reject_has_one_controlled_failure",
        "dpo_reject_no_repeated_paragraphs",
    }
    missing_mandatory_quality_checks = 0
    for row in preferences:
        paired = sft_by_id.get(str(row["id"]))
        if paired is None or row["prompt"] != _prompt_from_sft(paired):
            pair_alignment_failures += 1
        descriptor_labels = (
            STAGE_BY_KEY[str(row["journey_stage"])]["date"],
            str(PERSONA_BY_KEY[str(row["perspective"])]["label"]),
            str(TEMPORAL_BY_KEY[str(row["temporal_lens"])]["label"]),
            str(EVIDENCE_BY_KEY[str(row["evidence_state"])]["label"]),
            str(VIEW_BY_KEY[str(row["view_mode"])]["label"]),
        )
        rejected = str(row["rejected"])
        if any(label not in rejected for label in descriptor_labels):
            axis_reflection_failures += 1
        if _paragraph_repetition_count(rejected):
            repeated_reject_failures += 1
        quality = row.get("quality_gate") if isinstance(row.get("quality_gate"), Mapping) else {}
        checks = quality.get("checks") if isinstance(quality, Mapping) else {}
        if not isinstance(checks, Mapping) or not mandatory_checks.issubset(set(checks)):
            missing_mandatory_quality_checks += 1
        failure_key = str(quality.get("failure_mode") or "")
        if not failure_key or not _single_failure_reject(rejected, failure_key):
            single_failure_marker_failures += 1
    for row in [*sft_train, *heldout]:
        quality = row.get("quality_gate") if isinstance(row.get("quality_gate"), Mapping) else {}
        checks = quality.get("checks") if isinstance(quality, Mapping) else {}
        sft_required = mandatory_checks - {
            "dpo_reject_has_one_controlled_failure",
            "dpo_reject_no_repeated_paragraphs",
        }
        if not isinstance(checks, Mapping) or not sft_required.issubset(set(checks)):
            missing_mandatory_quality_checks += 1
    all_rows = [*sft_train, *preferences, *heldout]
    pii_rows = sum(bool(pii_findings(row)) for row in all_rows)
    accepted_rows = sum((row.get("quality_gate") or {}).get("accepted") is True for row in all_rows)
    near_duplicate = _near_duplicate_audit(sft_train, heldout)
    gates = [
        {"id": "canonical_training_contract", "passed": training_validation.get("ok") is True, "value": training_validation.get("blocking_failures") or []},
        {"id": "selection_contract", "passed": selection_contract.get("ok") is True, "value": selection_contract.get("mechanism_family_overlap")},
        {"id": "pii_detector_clean", "passed": pii_rows == 0, "value": pii_rows, "threshold": 0},
        {"id": "all_deterministic_row_checks_pass", "passed": accepted_rows == len(all_rows), "value": accepted_rows, "expected": len(all_rows)},
        {"id": "dpo_prompt_matches_sft_scenario", "passed": pair_alignment_failures == 0, "value": pair_alignment_failures, "threshold": 0},
        {"id": "dpo_reject_is_unique_per_row", "passed": reject_count == len(preferences), "value": reject_count, "expected": len(preferences)},
        {"id": "dpo_reject_reflects_all_axes", "passed": axis_reflection_failures == 0, "value": axis_reflection_failures, "threshold": 0},
        {"id": "dpo_pairwise_length_ratio", "passed": bool(ratios) and min(ratios) >= 0.55 and max(ratios) <= 2.0, "min": round(min(ratios), 6) if ratios else None, "max": round(max(ratios), 6) if ratios else None, "range": [0.55, 2.0]},
        {"id": "dpo_reject_no_repeated_paragraphs", "passed": repeated_reject_failures == 0, "value": repeated_reject_failures, "threshold": 0},
        {"id": "dpo_reject_single_controlled_failure", "passed": single_failure_marker_failures == 0, "value": single_failure_marker_failures, "threshold": 0},
        {"id": "mandatory_semantic_quality_checks_present", "passed": missing_mandatory_quality_checks == 0, "value": missing_mandatory_quality_checks, "threshold": 0},
        {"id": "heldout_near_duplicate", "passed": near_duplicate["passed"], "value": near_duplicate["max_similarity"], "threshold_exclusive": NEAR_DUPLICATE_THRESHOLD},
        {"id": "official_source_reference_shape", "passed": all(ref.startswith(("https://", "repo:")) for ref in [*SOURCE_REFS, *KNOWLEDGE_REFS]), "value": [*SOURCE_REFS, *KNOWLEDGE_REFS]},
        {"id": "target_model_revision_pinned", "passed": bool(re.fullmatch(r"[0-9a-f]{40}", MODEL_REVISION)) and MODEL_ID.startswith("unsloth/"), "value": {"id": MODEL_ID, "revision": MODEL_REVISION, "role": MODEL_ROLE}},
    ]
    failed = [str(gate["id"]) for gate in gates if gate["passed"] is not True]
    return {
        "schema_version": "duecare.synthetic_quality_audit.v2",
        "audit_kind": "deterministic full-row and sampled cross-split audit",
        "created_at": CREATED_AT,
        "generator_version": GENERATOR_VERSION,
        "generator_source_sha256": _sha256_file(Path(__file__)),
        "clean": not failed,
        "risk_flags": failed,
        "approval_status": "pending_independent_curator_privacy_license_and_publication_decision",
        "counts": {
            "sft_train": len(sft_train),
            "preference_train": len(preferences),
            "heldout": len(heldout),
            "unique_rejected": reject_count,
            "pii_detector_rows": pii_rows,
        },
        "near_duplicate_audit": near_duplicate,
        "gates": gates,
    }


def _artifact_map(paths: Mapping[str, Path]) -> dict[str, str]:
    return {key: path.name for key, path in paths.items()}


def _artifact_sha_map(paths: Mapping[str, Path]) -> dict[str, str]:
    return {key: _sha256_file(path) for key, path in paths.items()}


def write_publication_approval(
    manifest_path: Path,
    *,
    approved_by: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Write an explicit human/user authorization bound to a completed bundle."""

    approved_by = approved_by.strip()
    if not approved_by or approved_by.startswith("duecare-deterministic"):
        raise ValueError("approved_by must identify an explicit external reviewer or owner decision")
    manifest_path = manifest_path.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("safe_to_train") is not True:
        raise ValueError("source manifest is not safe_to_train")
    artifacts = manifest.get("artifacts") or {}
    hashes = manifest.get("artifact_sha256") or {}
    quality_path = manifest_path.parent / str(artifacts.get("quality_audit") or "")
    source_audit_path = manifest_path.parent / str(artifacts.get("source_audit") or "")
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    if _sha256_file(quality_path) != hashes.get("quality_audit"):
        raise ValueError("quality audit hash does not match the source manifest")
    if _sha256_file(source_audit_path) != hashes.get("source_audit"):
        raise ValueError("source audit hash does not match the source manifest")
    if quality.get("clean") is not True or quality.get("risk_flags"):
        raise ValueError("quality audit is not clean")
    if source_audit.get("clean") is not True or source_audit.get("risk_flags"):
        raise ValueError("source audit is not clean")
    approval = {
        "schema_version": "1.0",
        "handoff_kind": APPROVAL_HANDOFF_KIND,
        "source_manifest_sha256": _sha256_file(manifest_path),
        "approved_by": approved_by,
        "approved_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "approval_basis": "explicit reviewer or repository-owner decision after inspecting the manifest-bound automated audits",
        "rights_holder": RIGHTS_HOLDER,
        "row_license": ROW_LICENSE,
        "release_license": ROW_LICENSE,
        "allow_training_use": True,
        "allow_public_redistribution": True,
        "approvals": {
            "curator_approved": True,
            "privacy_approved": True,
            "license_approved": True,
            "quality_approved": True,
            "public_redistribution_approved": True,
        },
        "quality_audit": {
            "clean": True,
            "risk_flags": [],
            "artifact": quality_path.name,
            "artifact_sha256": _sha256_file(quality_path),
        },
        "source_audit_sha256": _sha256_file(source_audit_path),
        "prompt_scope": manifest["prompt_scope"],
    }
    output = output_path or manifest_path.parent / "publication_approval.json"
    _write_json(output, approval)
    return approval


def build_bundle(
    output_dir: Path,
    *,
    train_rows: int | None = DEFAULT_TRAIN_ROWS,
    validation_rows: int | None = DEFAULT_VALIDATION_ROWS,
    test_rows: int | None = DEFAULT_TEST_ROWS,
    force: bool = False,
    approval_authority: str | None = None,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    _prepare_output_dir(output_dir, force=force)

    descriptors = enumerate_descriptors()
    selected_train = _balanced_sample(descriptors, split="train", limit=train_rows)
    selected_validation = _balanced_sample(descriptors, split="validation", limit=validation_rows)
    selected_test = _balanced_sample(descriptors, split="test", limit=test_rows)
    selection_contract = _assert_selection_contract(
        selected_train, selected_validation, selected_test
    )

    sft_train = [_sft_row(row) for row in selected_train]
    preferences = [_preference_row(row) for row in selected_train]
    validation_sft = [_sft_row(row) for row in selected_validation]
    test_sft = [_sft_row(row) for row in selected_test]
    heldout_rows = [*validation_sft, *test_sft]

    heldout_hashes = sorted(canonical_sha256(_prompt_from_sft(row)) for row in heldout_rows)
    heldout_lineages = sorted(str(row["lineage_id"]) for row in heldout_rows)
    heldout_families = sorted({str(row["lineage_family_id"]) for row in heldout_rows})
    selected_prompt_hashes = sorted(
        canonical_sha256(_prompt(row))
        for row in [*selected_train, *selected_validation, *selected_test]
    )
    prompt_scope = {
        "scope_kind": "grounded_multiperspective_synthetic_preview",
        "scope_id": "duecare-grounded-multiperspective-casegraph-2026-07-14",
        "requested_count": len(selected_prompt_hashes),
        "prompt_count": len(selected_prompt_hashes),
        "prompt_sha256": canonical_sha256("\n".join(selected_prompt_hashes)),
        "closure_status": "partial",
        "full_flywheel_closure": False,
        "closure_evidence_sha256": "",
        "job_complete": True,
        "notes": (
            "Complete for the selected deterministic case-graph preview. Separate from, and not evidence of closure for, "
            "the live response-and-grading flywheel."
        ),
    }

    training_validation = validate_training_rows(
        sft_train,
        preferences,
        evaluation_prompt_hashes=heldout_hashes,
        evaluation_lineage_ids=heldout_lineages,
        require_preference=True,
    )
    if not training_validation["ok"]:
        raise SystemExit(f"training validation failed: {training_validation['blocking_failures']}")

    paths = {
        "sft": output_dir / "source_sft.jsonl",
        "dpo": output_dir / "source_dpo.jsonl",
        "sft_validation": output_dir / "source_validation.jsonl",
        "sft_test": output_dir / "source_test.jsonl",
        "quarantine": output_dir / "source_quarantine.json",
        "quality_audit": output_dir / "quality_audit.json",
        "source_audit": output_dir / "source_audit.json",
    }
    _write_jsonl(paths["sft"], sft_train)
    _write_jsonl(paths["dpo"], preferences)
    _write_jsonl(paths["sft_validation"], validation_sft)
    _write_jsonl(paths["sft_test"], test_sft)
    _write_json(
        paths["quarantine"],
        {
            "schema_version": "1.0",
            "contains_raw_text": False,
            "rows": [],
            "summary": {
                "rejected_rows": 0,
                "policy": "Incompatible states are not generated; contract failures stop the build and no raw rejected material is exported.",
            },
        },
    )

    audit = _quality_audit(
        sft_train, preferences, heldout_rows, selection_contract, training_validation
    )
    _write_json(paths["quality_audit"], audit)
    if not audit["clean"]:
        raise SystemExit(f"quality audit failed: {audit['risk_flags']}")

    matrix_definition = {
        "generator_version": GENERATOR_VERSION,
        "cartesian_rows": matrix_size(),
        "dimensions": {
            "perspectives": [row["key"] for row in PERSONAS],
            "journey_stages": [row["key"] for row in JOURNEY_STAGES],
            "temporal_lenses": [row["key"] for row in TEMPORAL_LENSES],
            "evidence_states": [row["key"] for row in EVIDENCE_STATES],
            "view_modes": [row["key"] for row in VIEW_MODES],
            "jurisdiction_patterns": [row["key"] for row in JURISDICTION_PATTERNS],
            "mechanisms": [row["key"] for row in MECHANISMS],
            "preference_failure_modes": [row["key"] for row in FAILURE_MODES],
        },
        "split_unit": "whole mechanism family; all jurisdiction, persona, stage, time, evidence, and view variants stay together",
        "train_mechanism_families": sorted(TRAIN_MECHANISM_KEYS),
        "validation_mechanism_families": sorted(VALIDATION_MECHANISM_KEYS),
        "test_mechanism_families": sorted(TEST_MECHANISM_KEYS),
        "heldout_lineage_family_ids": heldout_families,
        "selection_contract": selection_contract,
    }
    _write_json(
        paths["source_audit"],
        {
            "schema_version": "2.0",
            "audit_kind": "automated_source_and_provenance_audit",
            "clean": True,
            "risk_flags": [],
            "human_approval_status": "pending_separate_manifest_bound_approval",
            "quality_audit_artifact": paths["quality_audit"].name,
            "quality_audit_sha256": _sha256_file(paths["quality_audit"]),
            "prompt_scope": prompt_scope,
            "matrix_definition": matrix_definition,
            "row_grounding": {
                "rows": len(sft_train) + len(validation_sft) + len(test_sft),
                "synthetic_record_ids_required_in_answers": True,
                "source_refs": SOURCE_REFS,
                "knowledge_pack_refs": KNOWLEDGE_REFS,
                "claim": "method sources are attached; synthetic case assertions are grounded to explicit invented record IDs, not claimed as real-world facts",
            },
        },
    )

    effective_batch = 8
    training_profile = {
        "id": "full_preview_lora",
        "scope": "full_released_corpus_preview",
        "base_model_ref": MODEL_ID,
        "base_model_revision": MODEL_REVISION,
        "method": "sft_then_dpo",
        "max_steps": max(1, math.ceil(len(sft_train) / effective_batch * 2)),
        "dpo_max_steps": max(1, math.ceil(len(preferences) / effective_batch)),
        "effective_batch_size": effective_batch,
        "target_sft_epochs": 2,
        "target_dpo_epochs": 1,
        "include_dpo": True,
        "dpo_file": "preference_train.jsonl",
        "execute": False,
        "smoke_profile": {
            "id": "tiny_lora_smoke",
            "max_steps": 60,
            "dpo_max_steps": 30,
            "coverage_warning": "smoke only; it does not traverse the full released corpus",
        },
    }
    manifest = {
        "schema_version": "1.0",
        "handoff_kind": SOURCE_HANDOFF_KIND,
        "id": "duecare-grounded-multiperspective-training-bundle-2026-07-14",
        "created_at": CREATED_AT,
        "generator_mode": "grounded_multiperspective_casegraph",
        "generator_version": GENERATOR_VERSION,
        "generator_source_sha256": audit["generator_source_sha256"],
        "harness_profile": "grounded_multiperspective_casegraph",
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION},
        "model_role": MODEL_ROLE,
        "training_profile": training_profile,
        "source_scope": {
            "raw_publication_ingestion_by_default": False,
            "raw_case_files_included": False,
            "synthetic_rows_only": True,
        },
        "prompt_scope": prompt_scope,
        "matrix_definition": matrix_definition,
        "safe_to_train": True,
        "training_validation": training_validation,
        "heldout_prompt_sha256": heldout_hashes,
        "heldout_lineage_ids": heldout_lineages,
        "heldout_lineage_family_ids": heldout_families,
        "reasoning_data_policy": (
            "Final answers plus deliberately authored visible decision scaffolds grounded to invented case records only. "
            "Provider-private reasoning, runtime traces, raw worker cases, and real contact details are excluded."
        ),
        "artifacts": _artifact_map(paths),
        "artifact_sha256": _artifact_sha_map(paths),
    }
    manifest_path = output_dir / "source_manifest.json"
    _write_json(manifest_path, manifest)

    approval_written = False
    if approval_authority:
        write_publication_approval(manifest_path, approved_by=approval_authority)
        approval_written = True

    summary = {
        "schema_version": "2.0",
        "generator_version": GENERATOR_VERSION,
        "cartesian_matrix_rows": matrix_size(),
        "source_manifest": manifest_path.name,
        "publication_approval": "publication_approval.json" if approval_written else None,
        "sft_train_rows": len(sft_train),
        "preference_train_rows": len(preferences),
        "sft_validation_rows": len(validation_sft),
        "sft_test_rows": len(test_sft),
        "heldout_prompt_hashes": len(heldout_hashes),
        "heldout_lineage_families": len(heldout_families),
        "safe_to_train": True,
        "training_validation_ok": True,
        "quality_audit_clean": True,
        "publication_ready": approval_written,
        "approval_status": "approved" if approval_written else "pending_explicit_external_approval",
        "selection_contract": selection_contract,
    }
    _write_json(output_dir / "build_summary.json", summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--train-rows", type=int, default=DEFAULT_TRAIN_ROWS)
    parser.add_argument("--validation-rows", type=int, default=DEFAULT_VALIDATION_ROWS)
    parser.add_argument("--test-rows", type=int, default=DEFAULT_TEST_ROWS)
    parser.add_argument("--full-matrix", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--approve-as",
        default="",
        help="Explicit reviewer/owner identity; omitted by default so generation cannot self-approve publication.",
    )
    parser.add_argument(
        "--approve-manifest",
        type=Path,
        help="Write approval for an already reviewed manifest without regenerating the bundle; requires --approve-as.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.approve_manifest is not None:
        if not args.approve_as:
            raise SystemExit("--approve-manifest requires an explicit --approve-as identity")
        approval = write_publication_approval(
            args.approve_manifest,
            approved_by=args.approve_as,
        )
        print(json.dumps(approval, ensure_ascii=False, indent=2))
        return 0
    limits: tuple[int | None, int | None, int | None]
    limits = (None, None, None) if args.full_matrix else (
        args.train_rows,
        args.validation_rows,
        args.test_rows,
    )
    summary = build_bundle(
        args.output_dir,
        train_rows=limits[0],
        validation_rows=limits[1],
        test_rows=limits[2],
        force=args.force,
        approval_authority=args.approve_as or None,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
