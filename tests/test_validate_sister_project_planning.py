"""Tests for the sister-project planning validator."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    script = ROOT / "scripts" / "validate_sister_project_planning.py"
    spec = importlib.util.spec_from_file_location("validate_sister_project_planning", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_json(rel_path: str) -> dict:
    return json.loads((ROOT / rel_path).read_text(encoding="utf-8"))


def _load_jsonl(rel_path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (ROOT / rel_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _current_artifacts() -> tuple[dict, dict, dict, list[dict]]:
    return (
        _load_json("configs/duecare/benchmarks/sister_projects/global_protections_regulatory_benchmark.json"),
        _load_json("configs/duecare/benchmarks/sister_projects/global_protections_jurisdiction_packs.json"),
        _load_json("configs/duecare/benchmarks/domains/developing_country_worker_protections/grounding_sources.json"),
        _load_jsonl("configs/duecare/benchmarks/domains/developing_country_worker_protections/scheme_prompts.jsonl"),
    )


def _write_artifacts(
    tmp_path: Path,
    *,
    project: dict,
    packs: dict,
    grounding: dict,
    prompts: list[dict],
) -> tuple[Path, Path, Path, Path]:
    project_path = tmp_path / "project.json"
    packs_path = tmp_path / "packs.json"
    grounding_path = tmp_path / "grounding.json"
    prompts_path = tmp_path / "prompts.jsonl"
    project_path.write_text(json.dumps(project), encoding="utf-8")
    packs_path.write_text(json.dumps(packs), encoding="utf-8")
    grounding_path.write_text(json.dumps(grounding), encoding="utf-8")
    prompts_path.write_text(
        "\n".join(json.dumps(row) for row in prompts) + "\n",
        encoding="utf-8",
    )
    return project_path, packs_path, grounding_path, prompts_path


def test_sister_project_planning_validator_accepts_current_artifacts():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )

    assert report["summary"]["ok"] is True
    assert report["summary"]["project_status"] == "propose_only"
    assert report["summary"]["project_pack_id_match"] is True
    assert report["summary"]["candidate_pattern_count"] == 11
    assert report["summary"]["pilot_jurisdiction_scope_count"] == 8
    assert report["summary"]["queued_jurisdiction_scope_count"] == 5
    assert report["summary"]["local_source_jurisdiction_count"] == 12
    assert report["summary"]["local_source_jurisdictions_without_scope_count"] == 0
    assert report["summary"]["grounding_source_count"] == 17
    assert report["summary"]["source_status_counts"] == {
        "needs_source": 12,
        "unsafe_without_archive": 1,
        "verified_international_anchor": 4,
    }
    assert report["summary"]["grounding_rows_with_urls"] == 4
    assert report["summary"]["grounding_domain"] == "developing_country_worker_protections"
    assert report["summary"]["scheme_prompt_count"] == 12
    assert report["summary"]["scheme_prompt_category_count"] == 12
    assert report["summary"]["scheme_prompt_candidate_pattern_count"] == 10
    assert report["summary"]["scheme_prompt_candidate_patterns_without_project_declaration_count"] == 0
    assert report["summary"]["scheme_prompt_unresolved_scope_count"] == 12
    assert report["summary"]["scheme_prompt_not_ready_count"] == 12
    assert report["summary"]["scheme_prompt_categories_without_source_slots_count"] == 0
    assert report["summary"]["duplicate_id_issue_count"] == 0
    assert report["summary"]["readiness_gate_missing_block_concept_count"] == 0
    assert report["summary"]["source_admission_missing_concept_count"] == 0
    assert report["summary"]["scored_capability_missing_concept_count"] == 0
    assert report["summary"]["project_privacy_issue_count"] == 0
    assert report["summary"]["jurisdiction_pack_privacy_issue_count"] == 0
    assert report["summary"]["grounding_metadata_privacy_issue_count"] == 0
    assert "scheme_prompt_ids" not in report["summary"]
    rendered = json.dumps(report, ensure_ascii=False)
    assert "https://www.ilo.org" not in rendered
    assert "Synthetic composite:" not in rendered


def test_validator_accepts_custom_ids_without_copying_them():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    project = copy.deepcopy(project)
    packs = copy.deepcopy(packs)
    grounding = copy.deepcopy(grounding)
    custom_project_id = "custom_project_alpha"
    custom_domain = "custom_domain_alpha"
    project["project_id"] = custom_project_id
    packs["project_id"] = custom_project_id
    project["primary_seed_domains"] = [custom_domain]
    grounding["_meta"]["domain"] = custom_domain

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is True
    assert report["summary"]["project_id"] == "custom_or_invalid"
    assert report["summary"]["grounding_domain"] == "custom_or_invalid"
    assert custom_project_id not in rendered
    assert custom_domain not in rendered


def test_validator_sanitizes_custom_status_and_gate_values():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    project = copy.deepcopy(project)
    private_status = "private-worker@example.invalid"
    private_gate = "private-gate-worker@example.invalid"
    project["status"] = private_status
    project["readiness_gates"][0]["id"] = private_gate

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["project_status"] == "custom_or_invalid"
    assert "project_charter_is_propose_only" in report["summary"]["failed_ids"]
    assert "project_readiness_gates_cover_required_gates" in report["summary"]["failed_ids"]
    assert private_status not in rendered
    assert private_gate not in rendered


def test_validator_rejects_readiness_gates_missing_worker_use_block_without_copying_values():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    project = copy.deepcopy(project)
    custom_block = "internal curator handoff only"
    for gate in project["readiness_gates"]:
        if gate["id"] == "expert_review":
            gate["blocks"] = [
                block for block in gate["blocks"]
                if block != "worker-facing use"
            ]
            gate["blocks"].append(custom_block)

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)
    readiness_check = next(
        check for check in report["checks"]
        if check["id"] == "project_readiness_gates_block_public_training_comparable_and_worker_use"
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["readiness_gate_missing_block_concept_count"] == 1
    assert (
        "project_readiness_gates_block_public_training_comparable_and_worker_use"
        in report["summary"]["failed_ids"]
    )
    assert readiness_check["actual"] == ["worker_facing_use"]
    assert custom_block not in rendered


def test_validator_rejects_public_scoring_readiness():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    project = copy.deepcopy(project)
    private_phase_id = "private-phase-worker@example.invalid"
    project["first_build_phases"][0]["id"] = private_phase_id
    project["first_build_phases"][0]["ready_for_public_scoring"] = True

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "first_build_phases_remain_blocked" in report["summary"]["failed_ids"]
    assert private_phase_id not in rendered


def test_validator_rejects_first_build_phase_training_use():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    project = copy.deepcopy(project)
    private_phase_id = "private-training-worker@example.invalid"
    project["first_build_phases"][0]["id"] = private_phase_id
    project["first_build_phases"][0]["ready_for_training_use"] = True

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["first_build_phases_blocked"] is False
    assert "first_build_phases_remain_blocked" in report["summary"]["failed_ids"]
    assert private_phase_id not in rendered


def test_validator_rejects_private_project_and_pack_metadata_without_copying_values():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    project = copy.deepcopy(project)
    packs = copy.deepcopy(packs)
    private_email = "worker@example.invalid"
    private_path = r"C:\Users\private\case-row.json"
    private_url = "https://example.invalid/private-pack-source"
    project["source_admission_rules"].append(
        f"Use {private_email} and {private_path} for private review."
    )
    packs["pilot_policy"] = f"Review {private_url} before any pack use."

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["project_privacy_issue_count"] >= 2
    assert report["summary"]["jurisdiction_pack_privacy_issue_count"] >= 1
    assert (
        "project_and_pack_metadata_contains_no_private_identifiers"
        in report["summary"]["failed_ids"]
    )
    assert private_email not in rendered
    assert private_path not in rendered
    assert private_url not in rendered


def test_validator_rejects_weak_source_admission_rules_without_copying_rule_text():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    project = copy.deepcopy(project)
    removed_rule = project["source_admission_rules"][1]
    project["source_admission_rules"] = [
        rule for rule in project["source_admission_rules"]
        if "International instruments" not in rule
        and "Public complaint lists" not in rule
    ]

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)
    source_rule_check = next(
        check for check in report["checks"]
        if check["id"] == "source_admission_rules_cover_safety_boundaries"
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["source_admission_missing_concept_count"] == 3
    assert "source_admission_rules_cover_safety_boundaries" in report["summary"]["failed_ids"]
    assert source_rule_check["actual"] == [
        "international_anchors_cannot_substitute_for_local_law",
        "public_complaint_lists_are_rejected",
        "privacy_or_private_identifier_rejection",
    ]
    assert removed_rule not in rendered
    assert "International instruments" not in rendered
    assert "Public complaint lists" not in rendered


def test_validator_rejects_missing_scored_capability_without_copying_capability_text():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    project = copy.deepcopy(project)
    removed_capability = project["scored_capabilities"][-1]
    project["scored_capabilities"] = project["scored_capabilities"][:-1]
    project["scored_capabilities"].append(
        "Internal curator-only capability with private worker@example.invalid"
    )

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)
    capability_check = next(
        check for check in report["checks"]
        if check["id"] == "scored_capabilities_cover_regulatory_miss_patterns"
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["scored_capability_missing_concept_count"] == 1
    assert "scored_capabilities_cover_regulatory_miss_patterns" in report["summary"]["failed_ids"]
    assert capability_check["actual"] == ["refuses_to_invent_volatile_claims"]
    assert removed_capability not in rendered
    assert "worker@example.invalid" not in rendered


def test_validator_rejects_private_grounding_metadata_without_copying_values():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    grounding = copy.deepcopy(grounding)
    private_email = "grounding-worker@example.invalid"
    private_path = r"C:\Users\private\grounding-meta.json"
    grounding["_meta"]["review_note"] = f"Check {private_email} in {private_path}."

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["grounding_metadata_privacy_issue_count"] >= 2
    assert "grounding_metadata_contains_no_private_identifiers" in report["summary"]["failed_ids"]
    assert private_email not in rendered
    assert private_path not in rendered


def test_validator_rejects_promoted_local_law_rows_without_copying_url():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    grounding = copy.deepcopy(grounding)
    grounding["sources"][4]["verification_status"] = "verified_local_law"
    grounding["sources"][4]["verified_date"] = "2026-07-01"
    grounding["sources"][4]["url"] = "https://example.invalid/private-legal-row"

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )

    assert report["summary"]["ok"] is False
    assert "grounding_sources_keep_local_rows_pending" in report["summary"]["failed_ids"]
    assert "private-legal-row" not in json.dumps(report, ensure_ascii=False)


def test_validator_sanitizes_unknown_source_status_counts():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    grounding = copy.deepcopy(grounding)
    private_status = "verified_by_worker@example.invalid"
    grounding["sources"][4]["verification_status"] = private_status

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["source_status_counts"]["invalid_or_unknown"] == 1
    assert "grounding_sources_keep_local_rows_pending" in report["summary"]["failed_ids"]
    assert private_status not in rendered


def test_validator_rejects_scheme_prompt_url_or_email():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    prompts = copy.deepcopy(prompts)
    prompts[0]["text"] += " See https://example.invalid or worker@example.invalid."

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )

    assert report["summary"]["ok"] is False
    assert "scheme_prompt_text_contains_no_urls_emails_or_phones" in report["summary"]["failed_ids"]
    assert "worker@example.invalid" not in json.dumps(report, ensure_ascii=False)


def test_validator_rejects_scheme_prompt_resolved_or_ready_status():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    prompts = copy.deepcopy(prompts)
    prompts[0]["scope_resolution_status"] = "resolved"
    prompts[0]["ready_for_public_scoring"] = True

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["scheme_prompt_unresolved_scope_count"] == 11
    assert report["summary"]["scheme_prompt_not_ready_count"] == 11
    assert "scheme_prompts_are_explicitly_unresolved_and_not_ready" in report["summary"]["failed_ids"]
    assert "Synthetic composite:" not in rendered


def test_validator_rejects_undeclared_scheme_prompt_candidate_pattern():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    prompts = copy.deepcopy(prompts)
    private_pattern_id = "not_declared_worker@example.invalid"
    prompts[0]["candidate_pattern_ids"] = [private_pattern_id]

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["scheme_prompt_candidate_patterns_without_project_declaration_count"] == 1
    assert "scheme_prompt_candidate_patterns_are_declared_by_project" in report["summary"]["failed_ids"]
    assert "Synthetic composite:" not in rendered
    assert private_pattern_id not in rendered


def test_validator_rejects_missing_jurisdiction_review_gate():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    packs = copy.deepcopy(packs)
    packs["domain_lenses"][0]["review_gates"].remove("privacy_review")

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )

    assert report["summary"]["ok"] is False
    assert "domain_lenses_require_source_slots_and_review_gates" in report["summary"]["failed_ids"]


def test_validator_rejects_mismatched_project_and_jurisdiction_pack_ids():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    packs = copy.deepcopy(packs)
    packs["project_id"] = "different_project"

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )

    assert report["summary"]["ok"] is False
    assert report["summary"]["project_pack_id_match"] is False
    assert "project_and_jurisdiction_pack_ids_match" in report["summary"]["failed_ids"]


def test_validator_rejects_undeclared_domain_lens_id():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    packs = copy.deepcopy(packs)
    packs["domain_lenses"][0]["id"] = "undeclared_lens"

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )

    assert report["summary"]["ok"] is False
    assert "domain_lenses_are_declared_candidate_patterns" in report["summary"]["failed_ids"]


def test_validator_rejects_undeclared_lens_review_gate():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    packs = copy.deepcopy(packs)
    packs["domain_lenses"][0]["review_gates"].append("undocumented_review_gate")

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )

    assert report["summary"]["ok"] is False
    assert "domain_lens_review_gates_are_declared_by_project" in report["summary"]["failed_ids"]


def test_validator_rejects_undeclared_jurisdiction_family():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    packs = copy.deepcopy(packs)
    packs["pilot_jurisdiction_scopes"][0]["jurisdiction_family"] = "Unmapped family"

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )

    assert report["summary"]["ok"] is False
    assert "jurisdiction_scope_families_are_declared_by_project" in report["summary"]["failed_ids"]


def test_validator_rejects_local_grounding_jurisdiction_without_declared_scope():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    packs = copy.deepcopy(packs)
    packs["queued_jurisdiction_scopes"] = [
        scope for scope in packs["queued_jurisdiction_scopes"]
        if scope["iso3166_alpha2"] != "NG"
    ]

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["local_source_jurisdictions_without_scope_count"] == 1
    assert "local_grounding_jurisdictions_have_declared_scopes" in report["summary"]["failed_ids"]
    assert "Synthetic composite:" not in rendered


def test_validator_rejects_grounding_domain_outside_project_seed_domains():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    grounding = copy.deepcopy(grounding)
    grounding["_meta"]["domain"] = "unmapped_domain"

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )

    assert report["summary"]["ok"] is False
    assert "grounding_domain_is_project_seed_domain" in report["summary"]["failed_ids"]


def test_validator_rejects_prompt_category_without_grounding_source_slot():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    grounding = copy.deepcopy(grounding)
    target_category = prompts[0]["category"]
    for source in grounding["sources"]:
        tags = source.get("coverage_tags", [])
        if isinstance(tags, list):
            source["coverage_tags"] = [
                tag for tag in tags if tag != target_category
            ]

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["scheme_prompt_categories_without_source_slots_count"] == 1
    assert "scheme_prompt_categories_have_grounding_source_slots" in report["summary"]["failed_ids"]
    assert "Synthetic composite:" not in rendered


def test_validator_rejects_duplicate_prompt_ids_without_copying_prompt_text():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    prompts = copy.deepcopy(prompts)
    prompts[1]["id"] = prompts[0]["id"]

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["duplicate_id_issue_count"] == 1
    assert "planning_ids_are_unique_within_namespaces" in report["summary"]["failed_ids"]
    assert "Synthetic composite:" not in rendered


def test_validator_rejects_private_like_prompt_ids_without_copying_them():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    prompts = copy.deepcopy(prompts)
    private_prompt_id = "private-worker@example.invalid"
    prompts[0]["id"] = private_prompt_id
    prompts[1]["id"] = private_prompt_id

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert report["summary"]["duplicate_id_issue_count"] == 1
    assert "planning_ids_are_unique_within_namespaces" in report["summary"]["failed_ids"]
    assert "scheme_prompts_remain_synthetic_planning_rows" in report["summary"]["failed_ids"]
    assert private_prompt_id not in rendered
    assert "scheme_prompt_ids" not in rendered


def test_validator_sanitizes_supplied_prompt_parse_errors():
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    private_path = r"C:\Users\private\case-row.jsonl"
    private_error = f"JSONDecodeError in {private_path} for worker@example.invalid"

    report = validator.build_report(
        project_config=project,
        jurisdiction_packs=packs,
        grounding_sources=grounding,
        scheme_prompts=prompts,
        scheme_prompt_errors=[
            {"line": 7, "error": private_error},
            {"line": "8", "error": {"detail": private_path}},
            {"line": 9, "error": "JSONDecodeError"},
            {"line": 10, "error": "private_case_bucket"},
        ],
    )
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["summary"]["ok"] is False
    assert "scheme_prompt_jsonl_parses" in report["summary"]["failed_ids"]
    parse_check = next(
        check for check in report["checks"]
        if check["id"] == "scheme_prompt_jsonl_parses"
    )
    assert parse_check["actual"] == [
        {"line": 7, "error": "invalid_or_unknown"},
        {"line": None, "error": "invalid_or_unknown"},
        {"line": 9, "error": "JSONDecodeError"},
        {"line": 10, "error": "invalid_or_unknown"},
    ]
    assert private_path not in rendered
    assert "worker@example.invalid" not in rendered
    assert "private_case_bucket" not in rendered


def test_main_accepts_custom_artifact_paths(tmp_path, capsys):
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    project_path, packs_path, grounding_path, prompts_path = _write_artifacts(
        tmp_path,
        project=project,
        packs=packs,
        grounding=grounding,
        prompts=prompts,
    )

    rc = validator.main([
        "--project-config",
        str(project_path),
        "--jurisdiction-packs",
        str(packs_path),
        "--grounding-sources",
        str(grounding_path),
        "--scheme-prompts",
        str(prompts_path),
    ])
    printed = capsys.readouterr().out

    assert rc == 0
    assert "Sister-project planning validation - 29 checks, 0 findings" in printed
    assert "prompt_patterns=10" in printed
    assert "undeclared_prompt_patterns=0" in printed
    assert "unresolved_prompts=12" in printed
    assert "missing_source_slots=0" in printed
    assert "missing_scope_jurisdictions=0" in printed
    assert "readiness_gate_missing=0" in printed
    assert "source_admission_missing=0" in printed
    assert "scored_capability_missing=0" in printed
    assert "privacy_issues=project:0,packs:0,grounding:0" in printed


def test_main_redacts_custom_missing_path_from_json_report(tmp_path, capsys):
    validator = _load_validator()
    project, packs, grounding, prompts = _current_artifacts()
    project_path, packs_path, grounding_path, prompts_path = _write_artifacts(
        tmp_path,
        project=project,
        packs=packs,
        grounding=grounding,
        prompts=prompts,
    )
    missing_project = tmp_path / "private" / "missing_project.json"

    rc = validator.main([
        "--project-config",
        str(missing_project),
        "--jurisdiction-packs",
        str(packs_path),
        "--grounding-sources",
        str(grounding_path),
        "--scheme-prompts",
        str(prompts_path),
        "--json",
    ])
    printed = capsys.readouterr().out

    assert rc == 1
    assert "planning_artifacts_load" in printed
    assert str(tmp_path) not in printed
    assert "missing_project.json" not in printed
    assert str(project_path) not in printed
