#!/usr/bin/env python3
"""Build a readiness bundle for the global protections sister project.

This command composes three existing non-mutating layers:

1. global protections project plan
2. developing-country worker-protections source-curation bundle
3. regulatory miss-pattern curation bundle

It emits one compact status report for the whole sister-project stack. It does
not fetch sources, verify law, create prompts, edit manifests, create domain
files, or authorize comparable scoring.

Offline + deterministic. No model, no network, no credits.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_domain_curation_bundle as domain_bundle_builder  # noqa: E402
from artifact_path_policy import handoff_artifact_path  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402
import build_regulatory_curation_bundle as regulatory_bundle_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_readiness_bundle.json"
MD_OUT = OUT_DIR / "global_protections_readiness_bundle.md"
DEFAULT_DOMAIN = "developing_country_worker_protections"


def _load_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _artifact_path(path: pathlib.Path) -> str:
    return handoff_artifact_path(path, root=_ROOT)


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def component_paths(
    *,
    output_dir: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
) -> dict[str, str]:
    """Return handoff-safe artifact paths for the composed readiness chain."""
    base = output_dir or OUT_DIR
    names = {
        "project_plan": "global_protections_project_plan",
        "domain_curation_bundle": f"{domain_id}_curation_bundle",
        "regulatory_curation_bundle": "regulatory_curation_bundle",
        "global_protections_readiness_bundle": "global_protections_readiness_bundle",
    }
    out: dict[str, str] = {}
    for key, stem in names.items():
        out[f"{key}_json"] = _artifact_path(base / f"{stem}.json")
        out[f"{key}_markdown"] = _artifact_path(base / f"{stem}.md")
    return out


def _component_file_paths(
    *,
    output_dir: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
) -> dict[str, pathlib.Path]:
    """Return writable filesystem paths for the composed readiness chain."""
    base = output_dir or OUT_DIR
    names = {
        "project_plan": "global_protections_project_plan",
        "domain_curation_bundle": f"{domain_id}_curation_bundle",
        "regulatory_curation_bundle": "regulatory_curation_bundle",
        "global_protections_readiness_bundle": "global_protections_readiness_bundle",
    }
    out: dict[str, pathlib.Path] = {}
    for key, stem in names.items():
        out[f"{key}_json"] = base / f"{stem}.json"
        out[f"{key}_markdown"] = base / f"{stem}.md"
    return out


def build_readiness_chain(
    *,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Run the non-mutating project, domain, and regulatory chains in memory."""
    project_config = _load_json(project_config_path)
    if project_config is None:
        raise ValueError(f"unreadable global protections project config: {project_config_path}")
    registry = _load_json(registry_path)
    regulatory_catalog = _load_json(regulatory_catalog_path)
    project_doc = project_plan_builder.build_project_plan(
        project_config,
        config_path=project_config_path,
        registry=registry,
        regulatory_catalog=regulatory_catalog,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )
    domain_chain = domain_bundle_builder.build_curation_chain(domain_id)
    domain_doc = domain_bundle_builder.build_curation_bundle(
        domain_id,
        chain=domain_chain,
        component_dir=component_dir,
    )
    regulatory_chain = regulatory_bundle_builder.build_regulatory_curation_chain(
        config_path=regulatory_catalog_path,
        registry_path=registry_path,
        component_dir=component_dir,
    )
    regulatory_doc = regulatory_bundle_builder.build_regulatory_curation_bundle(
        chain=regulatory_chain,
        config_path=regulatory_catalog_path,
        registry_path=registry_path,
        component_dir=component_dir,
    )
    return {
        "project_plan": project_doc,
        "domain_curation_bundle": domain_doc,
        "regulatory_curation_bundle": regulatory_doc,
        "_domain_chain": domain_chain,
        "_regulatory_chain": regulatory_chain,
    }


def _component_summaries(chain: dict[str, dict[str, Any]]) -> dict[str, Any]:
    project_summary = chain["project_plan"]["summary"]
    domain_summary = chain["domain_curation_bundle"]["summary"]
    regulatory_summary = chain["regulatory_curation_bundle"]["summary"]
    return {
        "project_plan": {
            "safe_for_project_planning": project_summary["safe_for_project_planning"],
            "registered_seed_domain_count": project_summary["registered_seed_domain_count"],
            "regulatory_candidates_found_count": project_summary["regulatory_candidates_found_count"],
            "ready_for_comparable_scoring": project_summary["ready_for_comparable_scoring"],
        },
        "domain_curation_bundle": {
            "consistency_ok": domain_summary["consistency_ok"],
            "prompt_count": domain_summary["prompt_count"],
            "prompts_blocked_for_comparable_run": domain_summary["prompts_blocked_for_comparable_run"],
            "verified_local_law_rows": domain_summary["verified_local_law_rows"],
            "source_object_tasks": domain_summary["source_object_tasks"],
            "scope_refinement_tasks": domain_summary["scope_refinement_tasks"],
            "ready_for_comparable_run": domain_summary["ready_for_comparable_run"],
        },
        "regulatory_curation_bundle": {
            "consistency_ok": regulatory_summary["consistency_ok"],
            "pattern_count": regulatory_summary["pattern_count"],
            "candidate_count": regulatory_summary["candidate_count"],
            "validation_accepted_domain_seed_proposals": regulatory_summary[
                "validation_accepted_domain_seed_proposals"
            ],
            "ready_for_prompt_generation": regulatory_summary["ready_for_prompt_generation"],
            "ready_for_comparable_scoring": regulatory_summary["ready_for_comparable_scoring"],
        },
    }


def build_readiness_bundle(
    *,
    chain: dict[str, dict[str, Any]] | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a compact readiness bundle for the sister-project stack."""
    chain = chain or build_readiness_chain(
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    project_doc = chain["project_plan"]
    domain_doc = chain["domain_curation_bundle"]
    regulatory_doc = chain["regulatory_curation_bundle"]
    project_summary = project_doc["summary"]
    project_readiness = project_doc["readiness"]
    domain_summary = domain_doc["summary"]
    regulatory_summary = regulatory_doc["summary"]
    legal_anchor_source_channel_ids = (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )

    ready_for_prompt_generation = any((
        project_readiness["ready_for_prompt_generation"],
        regulatory_summary["ready_for_prompt_generation"],
    ))
    ready_for_training_use = project_readiness["ready_for_training_use"]
    ready_for_public_claims = project_readiness["ready_for_public_claims"]
    ready_for_worker_facing_use = project_readiness["ready_for_worker_facing_use"]
    ready_for_comparable_scoring = any((
        project_readiness["ready_for_comparable_scoring"],
        project_summary["ready_for_comparable_scoring"],
        domain_summary["ready_for_comparable_run"],
        regulatory_summary["ready_for_comparable_scoring"],
    ))
    registered_seed_domains = project_doc["existing_pipeline_links"]["registered_seed_domains"]
    regulatory_candidates_found = project_doc["existing_pipeline_links"]["regulatory_candidates_found"]
    checks = [
        _check(
            "project_plan_safe",
            project_summary["safe_for_project_planning"] is True,
            expected=True,
            actual=project_summary["safe_for_project_planning"],
        ),
        _check(
            "project_links_active_seed_domain",
            domain_id in registered_seed_domains,
            expected=domain_id,
            actual=registered_seed_domains,
        ),
        _check(
            "project_catalog_count_matches_regulatory_bundle",
            project_summary["candidate_pattern_count"] == regulatory_summary["pattern_count"],
            expected=project_summary["candidate_pattern_count"],
            actual=regulatory_summary["pattern_count"],
        ),
        _check(
            "project_candidate_links_match_catalog_count",
            len(regulatory_candidates_found) == regulatory_summary["pattern_count"],
            expected=regulatory_summary["pattern_count"],
            actual=len(regulatory_candidates_found),
        ),
        _check(
            "domain_curation_consistency_ok",
            domain_summary["consistency_ok"] is True,
            expected=True,
            actual=domain_summary["consistency_ok"],
        ),
        _check(
            "domain_comparable_run_blocked",
            domain_summary["ready_for_comparable_run"] is False,
            expected=False,
            actual=domain_summary["ready_for_comparable_run"],
        ),
        _check(
            "domain_local_law_gap_blocks_scoring",
            domain_summary["verified_local_law_rows"] == 0
            and domain_summary["prompts_blocked_for_comparable_run"] == domain_summary["prompt_count"],
            expected="0 verified local-law rows and all prompts blocked",
            actual={
                "verified_local_law_rows": domain_summary["verified_local_law_rows"],
                "prompts_blocked": domain_summary["prompts_blocked_for_comparable_run"],
                "prompt_count": domain_summary["prompt_count"],
            },
        ),
        _check(
            "regulatory_curation_consistency_ok",
            regulatory_summary["consistency_ok"] is True,
            expected=True,
            actual=regulatory_summary["consistency_ok"],
        ),
        _check(
            "regulatory_prompt_generation_blocked",
            regulatory_summary["ready_for_prompt_generation"] is False,
            expected=False,
            actual=regulatory_summary["ready_for_prompt_generation"],
        ),
        _check(
            "regulatory_comparable_scoring_blocked",
            regulatory_summary["ready_for_comparable_scoring"] is False,
            expected=False,
            actual=regulatory_summary["ready_for_comparable_scoring"],
        ),
        _check(
            "training_public_worker_and_scoring_blocked",
            not any((
                ready_for_prompt_generation,
                ready_for_training_use,
                ready_for_public_claims,
                ready_for_worker_facing_use,
                ready_for_comparable_scoring,
            )),
            expected=False,
            actual={
                "prompt_generation": ready_for_prompt_generation,
                "training_use": ready_for_training_use,
                "public_claims": ready_for_public_claims,
                "worker_facing_use": ready_for_worker_facing_use,
                "comparable_scoring": ready_for_comparable_scoring,
            },
        ),
        _check(
            "legal_claim_anchor_source_channels_match_source_matrix",
            bool(legal_anchor_source_channel_ids)
            and all(
                channel_id
                in {
                    str(channel["id"])
                    for channel in source_matrix_builder.SOURCE_CHANNELS
                    if isinstance(channel, dict) and channel.get("id")
                }
                for channel_id in legal_anchor_source_channel_ids
            ),
            expected="non-empty official legal-claim anchor source-channel allowlist",
            actual=legal_anchor_source_channel_ids,
        ),
    ]
    consistency_ok = all(item["ok"] for item in checks)
    return {
        "_meta": {
            "schema_version": "global_protections_readiness_bundle.v1",
            "project_config": _display_path(project_config_path),
            "domain": domain_id,
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "status": (
                "composed sister-project readiness bundle; not legal advice, not source "
                "verification, not prompt generation, and not comparable benchmark evidence"
            ),
        },
        "summary": {
            "consistency_ok": consistency_ok,
            "safe_for_project_planning": project_summary["safe_for_project_planning"],
            "registered_seed_domain_count": project_summary["registered_seed_domain_count"],
            "regulatory_pattern_count": regulatory_summary["pattern_count"],
            "regulatory_candidate_count": regulatory_summary["candidate_count"],
            "worker_prompt_count": domain_summary["prompt_count"],
            "worker_prompts_blocked_for_comparable_run": domain_summary[
                "prompts_blocked_for_comparable_run"
            ],
            "worker_verified_local_law_rows": domain_summary["verified_local_law_rows"],
            "worker_source_object_tasks": domain_summary["source_object_tasks"],
            "worker_scope_refinement_tasks": domain_summary["scope_refinement_tasks"],
            "regulatory_seed_scaffold_operations": regulatory_summary["seed_scaffold_operations"],
            "legal_claim_anchor_source_channel_count": len(legal_anchor_source_channel_ids),
            "legal_claim_anchor_source_channel_ids": list(legal_anchor_source_channel_ids),
            "ready_for_prompt_generation": ready_for_prompt_generation,
            "ready_for_training_use": ready_for_training_use,
            "ready_for_public_claims": ready_for_public_claims,
            "ready_for_worker_facing_use": ready_for_worker_facing_use,
            "ready_for_comparable_scoring": ready_for_comparable_scoring,
            "policy": (
                "This bundle can prove the project stack is internally consistent and safe for "
                "planning. It deliberately keeps prompt generation, training use, public claims, "
                "worker-facing use, and comparable scoring blocked until source coverage, scope "
                "resolution, privacy review, expert review, and a source-verified grounding layer pass."
            ),
        },
        "component_summaries": _component_summaries(chain),
        "checks": checks,
        "artifact_paths": component_paths(output_dir=component_dir, domain_id=domain_id),
    }


def _write_doc_pair(
    doc: dict[str, Any],
    json_path: pathlib.Path,
    markdown_path: pathlib.Path,
    markdown: str,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown + "\n", encoding="utf-8")


def write_upstream_artifacts(
    chain: dict[str, dict[str, Any]],
    *,
    output_dir: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    include_components: bool = False,
) -> dict[str, str]:
    """Write upstream bundle artifacts and optionally their component artifacts."""
    file_paths = _component_file_paths(output_dir=output_dir, domain_id=domain_id)
    paths = component_paths(output_dir=output_dir, domain_id=domain_id)
    _write_doc_pair(
        chain["project_plan"],
        file_paths["project_plan_json"],
        file_paths["project_plan_markdown"],
        project_plan_builder.build_markdown_report(chain["project_plan"]),
    )
    _write_doc_pair(
        chain["domain_curation_bundle"],
        file_paths["domain_curation_bundle_json"],
        file_paths["domain_curation_bundle_markdown"],
        domain_bundle_builder.build_markdown_report(chain["domain_curation_bundle"]),
    )
    _write_doc_pair(
        chain["regulatory_curation_bundle"],
        file_paths["regulatory_curation_bundle_json"],
        file_paths["regulatory_curation_bundle_markdown"],
        regulatory_bundle_builder.build_markdown_report(chain["regulatory_curation_bundle"]),
    )
    if include_components:
        component_paths_written = domain_bundle_builder.write_component_artifacts(
            domain_id,
            chain["_domain_chain"],
            output_dir=output_dir,
        )
        component_paths_written.update(
            regulatory_bundle_builder.write_component_artifacts(
                chain["_regulatory_chain"],
                output_dir=output_dir,
            )
        )
        paths.update(component_paths_written)
    return paths


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown readiness bundle."""
    summary = doc["summary"]
    lines: list[str] = [
        "# Global Protections Readiness Bundle",
        "",
        (
            "This bundle composes the sister-project charter, worker-protections source-curation "
            "chain, and regulatory candidate curation chain. It is not legal advice, not source "
            "verification, not prompt generation, and not comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Safe for project planning | {str(bool(summary['safe_for_project_planning'])).lower()} |",
        f"| Registered seed domains | {summary['registered_seed_domain_count']} |",
        f"| Regulatory patterns | {summary['regulatory_pattern_count']} |",
        f"| Regulatory candidate domains | {summary['regulatory_candidate_count']} |",
        f"| Worker prompts | {summary['worker_prompt_count']} |",
        f"| Worker prompts blocked for comparable run | {summary['worker_prompts_blocked_for_comparable_run']} |",
        f"| Worker verified local-law rows | {summary['worker_verified_local_law_rows']} |",
        f"| Worker source-object tasks | {summary['worker_source_object_tasks']} |",
        f"| Worker scope-refinement tasks | {summary['worker_scope_refinement_tasks']} |",
        f"| Regulatory seed scaffold operations | {summary['regulatory_seed_scaffold_operations']} |",
        (
            "| Legal-claim anchor source channels "
            f"| {summary['legal_claim_anchor_source_channel_count']} |"
        ),
        f"| Ready for prompt generation | {str(bool(summary['ready_for_prompt_generation'])).lower()} |",
        f"| Ready for training use | {str(bool(summary['ready_for_training_use'])).lower()} |",
        f"| Ready for public claims | {str(bool(summary['ready_for_public_claims'])).lower()} |",
        f"| Ready for worker-facing use | {str(bool(summary['ready_for_worker_facing_use'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ]
    for check in doc["checks"]:
        lines.append(
            f"| {_md_cell(check['id'])} "
            f"| {str(bool(check['ok'])).lower()} "
            f"| {_md_cell(check['expected'])} "
            f"| {_md_cell(check['actual'])} |"
        )
    lines.extend([
        "",
        "## Artifact Paths",
        "",
    ])
    for key, path in doc["artifact_paths"].items():
        lines.append(f"- `{_md_cell(key)}`: `{_md_cell(path)}`")
    lines.extend([
        "",
        "## Non-Scoring Rule",
        "",
        summary["policy"],
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--project-config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--md-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown bundle report")
    ap.add_argument(
        "--write-components",
        action="store_true",
        help="also write the upstream project/domain/regulatory bundle artifacts",
    )
    ap.add_argument(
        "--write-all-components",
        action="store_true",
        help="also write the lower-level domain and regulatory component artifacts",
    )
    ap.add_argument("--component-dir", type=pathlib.Path, default=OUT_DIR)
    args = ap.parse_args(argv)

    chain = build_readiness_chain(
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    doc = build_readiness_bundle(
        chain=chain,
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    if args.write_components or args.write_all_components:
        doc["artifact_paths"].update(
            write_upstream_artifacts(
                chain,
                output_dir=args.component_dir,
                domain_id=args.domain,
                include_components=args.write_all_components,
            )
        )
    doc["artifact_paths"]["global_protections_readiness_bundle_json"] = _artifact_path(args.out)
    if not args.no_md:
        doc["artifact_paths"]["global_protections_readiness_bundle_markdown"] = _artifact_path(args.md_out)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        "[global-protections-readiness-bundle] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"safe_for_project_planning={str(bool(summary['safe_for_project_planning'])).lower()}; "
        f"worker_prompts_blocked={summary['worker_prompts_blocked_for_comparable_run']}/{summary['worker_prompt_count']}; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["consistency_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
