#!/usr/bin/env python3
"""Build a deterministic 75-slot corridor curation workbook.

The workbook contains metadata and review requirements only. It never invents
prompts, answers, sources, licenses, snapshots, or human approvals. All source
catalog entries remain candidate-only until a curator supplies an immutable
snapshot, rights decision, privacy review, and checksum.

Offline + deterministic. No model, no network, no credits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "reports" / "training" / "corridor_expansion_plan.json"
SOURCE_CATALOG = ROOT / "configs" / "duecare" / "training" / "corridor_curation_sources.json"
OUT = ROOT / "reports" / "training" / "corridor_curation_workbook.json"
MD_OUT = ROOT / "reports" / "training" / "corridor_curation_workbook.md"

SCENARIO_KINDS = ("risk_case", "benign_near_neighbor", "corridor_counterfactual")
PERSPECTIVES = ("worker", "recruiter", "employer", "platform", "investigator", "bystander")
LANGUAGES_BY_CORRIDOR: dict[str, tuple[str, str, str]] = {
    "Bangladesh->Malaysia": ("bn", "ms", "en"),
    "Bangladesh->Saudi Arabia": ("bn", "ar", "en"),
    "Ethiopia->Gulf (maritime)": ("am", "ar", "en"),
    "Ghana->Qatar": ("en", "ar", "en"),
    "India->Kuwait": ("hi", "ar", "en"),
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path.name}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return text or "unknown"


def _split_for_task(index: int) -> str:
    remainder = index % 5
    if remainder < 3:
        return "train"
    return "validation" if remainder == 3 else "test"


def _source_ids_for_corridor(catalog: dict[str, Any], corridor: str) -> list[str]:
    sources = catalog.get("sources")
    if not isinstance(sources, list):
        return []
    return sorted(
        str(source["id"])
        for source in sources
        if isinstance(source, dict)
        and isinstance(source.get("id"), str)
        and isinstance(source.get("corridors"), list)
        and ("*" in source["corridors"] or corridor in source["corridors"])
    )


def validate_source_catalog(catalog: dict[str, Any]) -> list[str]:
    """Return structural source-catalog issues without echoing source payloads."""
    issues: list[str] = []
    if catalog.get("schema") != "duecare.corridor-curation-sources.v1":
        issues.append("catalog_schema")
    policy = catalog.get("policy")
    if (
        not isinstance(policy, dict)
        or policy.get("candidate_urls_are_not_training_approval") is not True
    ):
        issues.append("catalog_policy")
    sources = catalog.get("sources")
    if not isinstance(sources, list) or not sources:
        return [*issues, "catalog_sources"]
    ids: list[str] = []
    required = {
        "id",
        "title",
        "publisher",
        "url",
        "authority_tier",
        "corridors",
        "best_use",
        "limitations",
        "url_checked_at",
        "admission_status",
        "rights_status",
        "training_use",
        "snapshot_sha256",
    }
    for source in sources:
        if not isinstance(source, dict):
            issues.append("catalog_source_shape")
            continue
        if not required.issubset(source):
            issues.append("catalog_source_fields")
        source_id = source.get("id")
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9_]+", source_id):
            issues.append("catalog_source_id")
        else:
            ids.append(source_id)
        if not isinstance(source.get("corridors"), list) or not source.get("corridors"):
            issues.append("catalog_source_corridors")
        if source.get("admission_status") not in {"candidate_only", "approved"}:
            issues.append("catalog_admission_status")
        if source.get("rights_status") not in {"review_required", "approved"}:
            issues.append("catalog_rights_status")
        if source.get("training_use") not in {"blocked", "allowed"}:
            issues.append("catalog_training_use")
        approved = source.get("training_use") == "allowed"
        sha = source.get("snapshot_sha256")
        if approved and (
            source.get("admission_status") != "approved"
            or source.get("rights_status") != "approved"
            or not isinstance(sha, str)
            or re.fullmatch(r"[0-9a-f]{64}", sha) is None
        ):
            issues.append("catalog_approved_source_incomplete")
    if len(ids) != len(set(ids)):
        issues.append("catalog_duplicate_source_id")
    return sorted(set(issues))


def build_workbook(
    plan_doc: dict[str, Any],
    catalog: dict[str, Any],
    *,
    plan_sha256: str,
    catalog_sha256: str,
) -> dict[str, Any]:
    catalog_issues = validate_source_catalog(catalog)
    manifest = plan_doc.get("manifest")
    tasks = plan_doc.get("plan")
    if not isinstance(manifest, dict) or manifest.get("safe_for_curation") is not True:
        raise ValueError("corridor expansion plan is not safe for curation")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("corridor expansion plan has no tasks")
    if catalog_issues:
        raise ValueError("source catalog failed structural validation")

    slots: list[dict[str, Any]] = []
    for task_index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError("corridor expansion task is not an object")
        recommended = task.get("recommended_rows")
        if not isinstance(recommended, int) or recommended != len(SCENARIO_KINDS):
            raise ValueError("every corridor task must request exactly three rows")
        task_id = str(task.get("task_id") or "")
        category = str(task.get("category") or "")
        corridor = str(task.get("target_corridor") or "")
        languages = LANGUAGES_BY_CORRIDOR.get(corridor)
        if not task_id or not category or languages is None:
            raise ValueError("corridor task is missing a supported id, category, or corridor")
        planned_split = _split_for_task(task_index)
        family_id = f"corridor-curation:{_slug(category)}:{_slug(corridor)}"
        candidate_source_ids = _source_ids_for_corridor(catalog, corridor)
        if not candidate_source_ids:
            raise ValueError("corridor task has no candidate official source")
        for slot_index, scenario_kind in enumerate(SCENARIO_KINDS):
            slots.append(
                {
                    "slot_id": f"{task_id}-row-{slot_index + 1:02d}",
                    "task_id": task_id,
                    "category": category,
                    "corridor": corridor,
                    "origin": task.get("origin"),
                    "destination": task.get("destination"),
                    "scenario_kind": scenario_kind,
                    "planned_perspective": PERSPECTIVES[
                        (task_index * 3 + slot_index) % len(PERSPECTIVES)
                    ],
                    "planned_language": languages[slot_index],
                    "planned_split": planned_split,
                    "planned_lineage_family_id": family_id,
                    "candidate_source_ids": candidate_source_ids,
                    "required_independent_reviews": 2,
                    "requires_native_language_review": languages[slot_index] != "en",
                    "status": "unfilled",
                    "ready_for_admission": False,
                }
            )

    def by(key: str) -> dict[str, int]:
        return dict(sorted(Counter(str(slot[key]) for slot in slots).items()))
    return {
        "schema": "duecare.corridor-curation-workbook.v1",
        "inputs": {
            "corridor_expansion_plan": "reports/training/corridor_expansion_plan.json",
            "corridor_expansion_plan_sha256": plan_sha256,
            "source_catalog": "configs/duecare/training/corridor_curation_sources.json",
            "source_catalog_sha256": catalog_sha256,
        },
        "manifest": {
            "task_count": len(tasks),
            "slot_count": len(slots),
            "minimum_rows": sum(int(task["recommended_rows"]) for task in tasks),
            "scenario_kind_counts": by("scenario_kind"),
            "category_counts": by("category"),
            "corridor_counts": by("corridor"),
            "perspective_counts": by("planned_perspective"),
            "language_counts": by("planned_language"),
            "split_counts": by("planned_split"),
            "source_catalog_issue_count": 0,
            "all_slots_unfilled": True,
            "ready_for_training": False,
            "planned_model_calls": 0,
        },
        "admission_contract": {
            "candidate_rows_path": "reports/training/corridor_curation_rows.jsonl",
            "required_reviewers": 2,
            "disagreement_requires_distinct_resolver": True,
            "non_english_requires_native_language_attestation": True,
            "lineage_family_must_stay_in_one_split": True,
            "exact_and_near_duplicates_block_admission": True,
            "source_must_be_approved_and_snapshot_bound": True,
            "privacy_findings_are_reported_by_category_and_count_only": True,
            "candidate_rows_are_not_training_rows": True,
        },
        "slots": slots,
    }


def render_markdown(workbook: dict[str, Any]) -> str:
    manifest = workbook["manifest"]
    return "\n".join(
        [
            "# Corridor Curation Workbook",
            "",
            (
                "This is a metadata-only, fail-closed curation queue. It contains no invented "
                "prompt, answer, source approval, license decision, or human review."
            ),
            "",
            f"- Tasks: **{manifest['task_count']}**",
            f"- Required row slots: **{manifest['slot_count']}**",
            f"- Planned splits: `{json.dumps(manifest['split_counts'], sort_keys=True)}`",
            f"- Planned languages: `{json.dumps(manifest['language_counts'], sort_keys=True)}`",
            "- Ready for training: **no**",
            "- Planned model calls: **0**",
            "",
            "## Curator Sequence",
            "",
            "1. Snapshot only lawful, minimum-necessary source material.",
            "2. Record rights approval, retrieval date, and SHA-256 in the source catalog.",
            "3. Fill ignored candidate rows using the exact slot contract.",
            "4. Obtain two independent reviews; resolve disagreements with a distinct role.",
            "5. Run `python scripts/validate_corridor_curation.py --require-complete`.",
            (
                "6. Only after that gate passes, regenerate training splits and the "
                "quality/provenance artifacts sequentially."
            ),
            "",
            (
                "The workbook is planning evidence, not an accepted dataset or a "
                "training-quality claim."
            ),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--sources", type=Path, default=SOURCE_CATALOG)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--markdown-out", type=Path, default=MD_OUT)
    parser.add_argument(
        "--validate", action="store_true", help="validate in memory without writing"
    )
    args = parser.parse_args(argv)
    try:
        workbook = build_workbook(
            _load_json(args.plan),
            _load_json(args.sources),
            plan_sha256=_sha256(args.plan),
            catalog_sha256=_sha256(args.sources),
        )
    except (OSError, ValueError) as exc:
        print(f"[corridor-curation-workbook] FAIL: {exc}")
        return 1
    manifest = workbook["manifest"]
    ok = manifest["task_count"] == 25 and manifest["slot_count"] == 75
    if not args.validate:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(workbook, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_markdown(workbook), encoding="utf-8")
    print(
        "[corridor-curation-workbook] "
        f"tasks={manifest['task_count']} slots={manifest['slot_count']} "
        f"sources={len(_load_json(args.sources)['sources'])} ready_for_training=false"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
