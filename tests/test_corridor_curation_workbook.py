from __future__ import annotations

import copy
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


builder = _load(
    "build_corridor_curation_workbook",
    SCRIPTS / "build_corridor_curation_workbook.py",
)
validator = _load(
    "validate_corridor_curation",
    SCRIPTS / "validate_corridor_curation.py",
)

CATEGORIES = (
    "combined_attack",
    "corridor_specific",
    "keyword_mutation",
    "labor_trafficking",
    "major_case_scenario_mix",
)
CORRIDORS = tuple(builder.LANGUAGES_BY_CORRIDOR)


def _plan() -> dict:
    tasks = []
    for category in CATEGORIES:
        for corridor in CORRIDORS:
            origin, _, destination = corridor.partition("->")
            tasks.append(
                {
                    "task_id": (
                        f"corridor-expansion-{category.replace('_', '-')}-"
                        f"{builder._slug(corridor)}"
                    ),
                    "category": category,
                    "target_corridor": corridor,
                    "origin": origin,
                    "destination": destination,
                    "recommended_rows": 3,
                }
            )
    return {"plan": tasks, "manifest": {"safe_for_curation": True}}


def _catalog() -> dict:
    return json.loads(builder.SOURCE_CATALOG.read_text(encoding="utf-8"))


def _workbook(catalog: dict | None = None) -> dict:
    return builder.build_workbook(
        _plan(),
        catalog or _catalog(),
        plan_sha256="1" * 64,
        catalog_sha256="2" * 64,
    )


def _approve_global_source(catalog: dict) -> tuple[str, str]:
    source = next(source for source in catalog["sources"] if source["id"] == "ilo_c029")
    sha = "a" * 64
    source.update(
        {
            "admission_status": "approved",
            "rights_status": "approved",
            "training_use": "allowed",
            "snapshot_sha256": sha,
        }
    )
    return source["id"], sha


def _review(role: str, *, native: bool) -> dict:
    return {
        "reviewer_role": role,
        "decision": "accept",
        "reviewed_at": "2026-07-27",
        "checks": {
            "source_verified": True,
            "rights_verified": True,
            "privacy_passed": True,
            "label_correct": True,
            "response_grounded": True,
            "volatile_claims_externalized": True,
            "benign_control_checked": True,
            "native_language_reviewed": native,
        },
    }


def _row(slot: dict, source_id: str, sha: str) -> dict:
    unique = slot["slot_id"].replace("-", " ")
    return {
        "id": slot["slot_id"],
        "slot_id": slot["slot_id"],
        "task_id": slot["task_id"],
        "category": slot["category"],
        "corridor": slot["corridor"],
        "scenario_kind": slot["scenario_kind"],
        "perspective": slot["planned_perspective"],
        "language": slot["planned_language"],
        "split": slot["planned_split"],
        "lineage_id": f"lineage:{slot['slot_id']}",
        "lineage_family_id": slot["planned_lineage_family_id"],
        "source_kind": "synthetic",
        "source_ids": [source_id],
        "source_snapshots": {source_id: sha},
        "source_retrieved_at": {source_id: "2026-07-27"},
        "transformation": (
            f"Synthetic minimum-necessary transformation for {unique} with no copied case details."
        ),
        "prompt": (
            f"Synthetic scenario for {unique}. Review the evidence boundary, the worker's "
            "agency, and the corridor-specific uncertainty before answering."
        ),
        "target_response": (
            f"Grounded response for {unique}. Identify stable forced-labour indicators, "
            "separate observations from conclusions, preserve evidence, avoid volatile legal "
            "or contact claims, and recommend verification through current authoritative sources."
        ),
        "reviews": [
            _review("curator_primary", native=slot["requires_native_language_review"]),
            _review("curator_secondary", native=False),
        ],
        "adjudication": {
            "status": "consensus",
            "final_decision": "accept",
            "resolver_role": None,
            "resolved_at": None,
        },
    }


def test_workbook_has_25_tasks_and_balanced_75_slot_contract():
    workbook = _workbook()
    manifest = workbook["manifest"]

    assert manifest["task_count"] == 25
    assert manifest["slot_count"] == 75
    assert manifest["minimum_rows"] == 75
    assert manifest["scenario_kind_counts"] == {
        "benign_near_neighbor": 25,
        "corridor_counterfactual": 25,
        "risk_case": 25,
    }
    assert manifest["split_counts"] == {"test": 15, "train": 45, "validation": 15}
    assert max(manifest["perspective_counts"].values()) - min(
        manifest["perspective_counts"].values()
    ) <= 1
    assert manifest["ready_for_training"] is False
    assert all(slot["status"] == "unfilled" for slot in workbook["slots"])
    assert all("prompt" not in slot and "target_response" not in slot for slot in workbook["slots"])


def test_current_source_catalog_is_valid_but_every_source_is_quarantined():
    catalog = _catalog()

    assert builder.validate_source_catalog(catalog) == []
    assert len(catalog["sources"]) >= 12
    assert all(source["training_use"] == "blocked" for source in catalog["sources"])
    assert all(source["snapshot_sha256"] is None for source in catalog["sources"])
    assert Counter(source["reachability_status"] for source in catalog["sources"]) == {
        "direct_response": 7,
        "redirect_observed": 2,
        "transient_unverified": 3,
    }


def test_validator_accepts_scaffold_and_reports_exact_incomplete_count():
    catalog = _catalog()
    workbook = _workbook(catalog)

    report = validator.validate(workbook, workbook, catalog, [])

    assert report["summary"]["valid"] is True
    assert report["summary"]["complete"] is False
    assert report["summary"]["missing_slots"] == 75
    assert report["summary"]["ready_for_training"] is False


def test_full_75_row_two_reviewer_fixture_can_pass_strict_contract():
    catalog = _catalog()
    source_id, sha = _approve_global_source(catalog)
    workbook = _workbook(catalog)
    rows = [_row(slot, source_id, sha) for slot in workbook["slots"]]

    report = validator.validate(workbook, workbook, catalog, rows)

    assert report["summary"]["valid"] is True, report["row_issue_codes"]
    assert report["summary"]["complete"] is True
    assert report["summary"]["ready_for_training"] is True
    assert report["summary"]["valid_rows"] == 75
    assert report["summary"]["cross_family_near_duplicate_pairs"] == 0


def test_validator_rejects_blocked_source_and_non_independent_reviewers():
    catalog = _catalog()
    workbook = _workbook(catalog)
    slot = workbook["slots"][0]
    source_id = slot["candidate_source_ids"][0]
    row = _row(slot, source_id, "a" * 64)
    row["reviews"][1]["reviewer_role"] = row["reviews"][0]["reviewer_role"]

    report = validator.validate(workbook, workbook, catalog, [row])
    issues = report["row_issue_codes"][slot["slot_id"]]

    assert "source_not_approved" in issues
    assert "source_catalog_snapshot" in issues
    assert "reviewer_roles_not_distinct" in issues
    assert report["summary"]["ready_for_training"] is False


def test_privacy_failure_reports_category_count_without_echoing_payload():
    catalog = _catalog()
    source_id, sha = _approve_global_source(catalog)
    workbook = _workbook(catalog)
    slot = workbook["slots"][0]
    row = _row(slot, source_id, sha)
    private_value = "worker.person@example.org"
    row["prompt"] += f" Contact {private_value} for the private case."

    report = validator.validate(workbook, workbook, catalog, [row])
    rendered = json.dumps(report)

    assert report["privacy_category_counts"] == {"email_like": 1}
    assert "privacy_scan" in report["row_issue_codes"][slot["slot_id"]]
    assert private_value not in rendered


def test_catalog_cannot_allow_training_without_approved_rights_and_snapshot():
    catalog = copy.deepcopy(_catalog())
    source = catalog["sources"][0]
    source["training_use"] = "allowed"

    assert "catalog_approved_source_incomplete" in builder.validate_source_catalog(catalog)
