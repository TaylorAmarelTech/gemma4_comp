#!/usr/bin/env python3
"""Build an end-to-end curation bundle for regulatory-miss candidates.

This command runs the propose-only regulatory expansion chain in memory:

1. miss-pattern research plan
2. blank candidate-domain intake packet
3. intake validation gate
4. non-mutating domain-seed scaffold proposal

It emits a compact status bundle and consistency checks. It does not fetch
sources, verify law, create domain files, edit the domain registry, generate
prompts, or authorize comparable benchmark scoring.

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

import build_regulatory_domain_intake_packet as intake_builder  # noqa: E402
import build_regulatory_domain_seed_proposal as seed_proposal_builder  # noqa: E402
import build_regulatory_miss_pattern_plan as pattern_plan_builder  # noqa: E402
import validate_regulatory_domain_intake_packet as intake_validator  # noqa: E402
from artifact_path_policy import handoff_artifact_path  # noqa: E402

CONFIG = _ROOT / "configs" / "duecare" / "benchmarks" / "regulatory_miss_patterns.json"
REGISTRY = _ROOT / "configs" / "duecare" / "benchmarks" / "domains" / "registry.json"
OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "regulatory_curation_bundle.json"
MD_OUT = OUT_DIR / "regulatory_curation_bundle.md"


def _load_config(path: pathlib.Path) -> dict[str, Any] | None:
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


def component_paths(*, output_dir: pathlib.Path | None = None) -> dict[str, str]:
    """Return handoff-safe artifact paths for the regulatory curation chain."""
    base = output_dir or OUT_DIR
    names = {
        "miss_pattern_plan": "regulatory_miss_pattern_plan",
        "domain_intake_packet": "regulatory_domain_intake_packet",
        "domain_intake_validation": "regulatory_domain_intake_validation",
        "domain_seed_proposal": "regulatory_domain_seed_proposal",
        "regulatory_curation_bundle": "regulatory_curation_bundle",
    }
    out: dict[str, str] = {}
    for key, stem in names.items():
        out[f"{key}_json"] = _artifact_path(base / f"{stem}.json")
        out[f"{key}_markdown"] = _artifact_path(base / f"{stem}.md")
    return out


def _component_file_paths(*, output_dir: pathlib.Path | None = None) -> dict[str, pathlib.Path]:
    """Return writable artifact paths for the regulatory curation chain."""
    base = output_dir or OUT_DIR
    names = {
        "miss_pattern_plan": "regulatory_miss_pattern_plan",
        "domain_intake_packet": "regulatory_domain_intake_packet",
        "domain_intake_validation": "regulatory_domain_intake_validation",
        "domain_seed_proposal": "regulatory_domain_seed_proposal",
        "regulatory_curation_bundle": "regulatory_curation_bundle",
    }
    out: dict[str, pathlib.Path] = {}
    for key, stem in names.items():
        out[f"{key}_json"] = base / f"{stem}.json"
        out[f"{key}_markdown"] = base / f"{stem}.md"
    return out


def build_regulatory_curation_chain(
    *,
    config: dict[str, Any] | None = None,
    config_path: pathlib.Path = CONFIG,
    registry_path: pathlib.Path = REGISTRY,
    component_dir: pathlib.Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Run the non-mutating regulatory curation chain and return components."""
    loaded = config if config is not None else _load_config(config_path)
    if loaded is None:
        raise ValueError(f"unreadable regulatory miss-pattern config: {config_path}")
    paths = _component_file_paths(output_dir=component_dir)
    plan_doc = pattern_plan_builder.build_plan(loaded)
    intake_doc = intake_builder.build_intake_packet(loaded, config_path=config_path)
    validation_doc = intake_validator.validate_intake_packet(
        intake_doc,
        packet_path=paths["domain_intake_packet_json"],
        registry_path=registry_path,
    )
    proposal_doc = seed_proposal_builder.build_seed_proposal(
        validation_doc,
        registry_path=registry_path,
        validation_path=paths["domain_intake_validation_json"],
    )
    return {
        "miss_pattern_plan": plan_doc,
        "domain_intake_packet": intake_doc,
        "domain_intake_validation": validation_doc,
        "domain_seed_proposal": proposal_doc,
    }


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def _component_summaries(chain: dict[str, dict[str, Any]]) -> dict[str, Any]:
    plan_manifest = chain["miss_pattern_plan"]["manifest"]
    plan_coverage = chain["miss_pattern_plan"].get("coverage_summary", {})
    intake_meta = chain["domain_intake_packet"]["_meta"]
    validation_meta = chain["domain_intake_validation"]["_meta"]
    proposal_meta = chain["domain_seed_proposal"]["_meta"]
    return {
        "miss_pattern_plan": {
            "pattern_count": plan_manifest["pattern_count"],
            "active_seed_count": plan_manifest["active_seed_count"],
            "candidate_count": plan_manifest["candidate_count"],
            "defer_count": plan_manifest["defer_count"],
            "candidate_queue_count": plan_manifest["candidate_queue_count"],
            "top_candidate_id": plan_manifest["top_candidate_id"],
            "safe_for_research_planning": plan_manifest["safe_for_research_planning"],
            "ready_for_comparable_scoring": plan_manifest["ready_for_comparable_scoring"],
            "source_gate_count": plan_coverage.get("source_gate_count", 0),
            "model_miss_pattern_count": plan_coverage.get("model_miss_pattern_count", 0),
            "priority_signal_count": plan_coverage.get("priority_signal_count", 0),
        },
        "domain_intake_packet": {
            "active_seed_count": intake_meta["active_seed_count"],
            "candidate_count": intake_meta["candidate_count"],
            "candidate_queue_count": intake_meta["candidate_queue_count"],
            "top_candidate_id": intake_meta["top_candidate_id"],
            "ready_for_domain_seed_count": intake_meta["ready_for_domain_seed_count"],
            "ready_for_prompt_generation_count": intake_meta["ready_for_prompt_generation_count"],
            "ready_for_comparable_scoring_count": intake_meta["ready_for_comparable_scoring_count"],
            "safe_for_curator_intake": intake_meta["safe_for_curator_intake"],
        },
        "domain_intake_validation": {
            "candidate_count": validation_meta["candidate_count"],
            "accepted_for_domain_seed_proposal_count": validation_meta[
                "accepted_for_domain_seed_proposal_count"
            ],
            "pending_or_deferred_count": validation_meta["pending_or_deferred_count"],
            "invalid_count": validation_meta["invalid_count"],
            "ready_for_prompt_generation_count": validation_meta["ready_for_prompt_generation_count"],
            "ready_for_comparable_scoring_count": validation_meta["ready_for_comparable_scoring_count"],
            "validation_ok": validation_meta["validation_ok"],
        },
        "domain_seed_proposal": {
            "source_validation_ok": proposal_meta["source_validation_ok"],
            "accepted_validation_proposals": proposal_meta["accepted_validation_proposals"],
            "accepted_operations": proposal_meta["accepted_operations"],
            "rejected_proposals": proposal_meta["rejected_proposals"],
            "ready_for_seed_file_creation": proposal_meta["ready_for_seed_file_creation"],
            "ready_for_manual_registry_patch": proposal_meta["ready_for_manual_registry_patch"],
            "ready_for_prompt_generation": proposal_meta["ready_for_prompt_generation"],
            "ready_for_comparable_scoring": proposal_meta["ready_for_comparable_scoring"],
            "proposal_ok": proposal_meta["proposal_ok"],
        },
    }


def build_regulatory_curation_bundle(
    *,
    chain: dict[str, dict[str, Any]] | None = None,
    config_path: pathlib.Path = CONFIG,
    registry_path: pathlib.Path = REGISTRY,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a compact end-to-end regulatory curation bundle."""
    chain = chain or build_regulatory_curation_chain(
        config_path=config_path,
        registry_path=registry_path,
        component_dir=component_dir,
    )
    plan_manifest = chain["miss_pattern_plan"]["manifest"]
    intake_meta = chain["domain_intake_packet"]["_meta"]
    validation_meta = chain["domain_intake_validation"]["_meta"]
    proposal_meta = chain["domain_seed_proposal"]["_meta"]

    ready_for_prompt_generation = any((
        intake_meta["ready_for_prompt_generation_count"],
        validation_meta["ready_for_prompt_generation_count"],
        proposal_meta["ready_for_prompt_generation"],
    ))
    ready_for_comparable_scoring = any((
        plan_manifest["ready_for_comparable_scoring"],
        intake_meta["ready_for_comparable_scoring_count"],
        validation_meta["ready_for_comparable_scoring_count"],
        proposal_meta["ready_for_comparable_scoring"],
    ))
    checks = [
        _check(
            "miss_pattern_plan_safe",
            plan_manifest["safe_for_research_planning"] is True,
            expected=True,
            actual=plan_manifest["safe_for_research_planning"],
        ),
        _check(
            "intake_packet_safe",
            intake_meta["safe_for_curator_intake"] is True,
            expected=True,
            actual=intake_meta["safe_for_curator_intake"],
        ),
        _check(
            "active_seed_count_matches",
            plan_manifest["active_seed_count"] == intake_meta["active_seed_count"],
            expected=plan_manifest["active_seed_count"],
            actual=intake_meta["active_seed_count"],
        ),
        _check(
            "candidate_count_matches",
            plan_manifest["candidate_count"] == intake_meta["candidate_count"],
            expected=plan_manifest["candidate_count"],
            actual=intake_meta["candidate_count"],
        ),
        _check(
            "candidate_queue_count_matches_candidates",
            plan_manifest["candidate_queue_count"] == plan_manifest["candidate_count"],
            expected=plan_manifest["candidate_count"],
            actual=plan_manifest["candidate_queue_count"],
        ),
        _check(
            "intake_preserves_candidate_queue",
            intake_meta["candidate_queue_count"] == plan_manifest["candidate_queue_count"],
            expected=plan_manifest["candidate_queue_count"],
            actual=intake_meta["candidate_queue_count"],
        ),
        _check(
            "candidate_queue_keeps_scoring_blocked",
            all(
                row.get("ready_for_prompt_generation") is False
                and row.get("ready_for_comparable_scoring") is False
                for row in chain["miss_pattern_plan"].get("expansion_queue", [])
            ),
            expected=True,
            actual=[
                {
                    "pattern_id": row.get("pattern_id"),
                    "ready_for_prompt_generation": row.get("ready_for_prompt_generation"),
                    "ready_for_comparable_scoring": row.get("ready_for_comparable_scoring"),
                }
                for row in chain["miss_pattern_plan"].get("expansion_queue", [])
            ],
        ),
        _check(
            "validation_candidate_count_matches_intake",
            validation_meta["candidate_count"] == intake_meta["candidate_count"],
            expected=intake_meta["candidate_count"],
            actual=validation_meta["candidate_count"],
        ),
        _check(
            "validation_ok",
            validation_meta["validation_ok"] is True,
            expected=True,
            actual=validation_meta["validation_ok"],
        ),
        _check(
            "seed_proposal_uses_validated_input",
            proposal_meta["source_validation_ok"] == validation_meta["validation_ok"],
            expected=validation_meta["validation_ok"],
            actual=proposal_meta["source_validation_ok"],
        ),
        _check(
            "seed_proposal_ok",
            proposal_meta["proposal_ok"] is True,
            expected=True,
            actual=proposal_meta["proposal_ok"],
        ),
        _check(
            "manual_registry_patch_blocked",
            proposal_meta["ready_for_manual_registry_patch"] is False,
            expected=False,
            actual=proposal_meta["ready_for_manual_registry_patch"],
        ),
        _check(
            "prompt_generation_blocked",
            ready_for_prompt_generation is False,
            expected=False,
            actual=ready_for_prompt_generation,
        ),
        _check(
            "comparable_scoring_blocked",
            ready_for_comparable_scoring is False,
            expected=False,
            actual=ready_for_comparable_scoring,
        ),
    ]
    consistency_ok = all(item["ok"] for item in checks)
    return {
        "_meta": {
            "schema_version": "regulatory_curation_bundle.v1",
            "source_catalog": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "status": (
                "end-to-end regulatory curation bundle; not legal advice, not source verification, "
                "not prompt generation, and not comparable benchmark evidence"
            ),
        },
        "summary": {
            "consistency_ok": consistency_ok,
            "pattern_count": plan_manifest["pattern_count"],
            "active_seed_count": plan_manifest["active_seed_count"],
            "candidate_count": plan_manifest["candidate_count"],
            "candidate_queue_count": plan_manifest["candidate_queue_count"],
            "top_candidate_id": plan_manifest["top_candidate_id"],
            "defer_count": plan_manifest["defer_count"],
            "candidate_intake_rows": intake_meta["candidate_count"],
            "active_seed_followups": intake_meta["active_seed_count"],
            "validation_candidate_rows": validation_meta["candidate_count"],
            "validation_pending_or_deferred_rows": validation_meta["pending_or_deferred_count"],
            "validation_accepted_domain_seed_proposals": validation_meta[
                "accepted_for_domain_seed_proposal_count"
            ],
            "validation_invalid_rows": validation_meta["invalid_count"],
            "seed_scaffold_operations": proposal_meta["accepted_operations"],
            "seed_rejected_proposals": proposal_meta["rejected_proposals"],
            "ready_for_seed_file_creation": proposal_meta["ready_for_seed_file_creation"],
            "ready_for_manual_registry_patch": proposal_meta["ready_for_manual_registry_patch"],
            "ready_for_prompt_generation": ready_for_prompt_generation,
            "ready_for_comparable_scoring": ready_for_comparable_scoring,
            "policy": (
                "This bundle proves local consistency of the regulatory expansion chain only. "
                "Candidate domains still need source objects, privacy review, expert review, "
                "curator-created seed files, and a source-verified grounding layer before scoring."
            ),
        },
        "component_summaries": _component_summaries(chain),
        "consistency_checks": checks,
        "artifact_paths": component_paths(output_dir=component_dir),
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


def write_component_artifacts(
    chain: dict[str, dict[str, Any]],
    *,
    output_dir: pathlib.Path | None = None,
) -> dict[str, str]:
    """Write component artifacts and return handoff-safe artifact paths."""
    file_paths = _component_file_paths(output_dir=output_dir)
    paths = component_paths(output_dir=output_dir)
    writers = {
        "miss_pattern_plan": (
            pattern_plan_builder.render_markdown,
            chain["miss_pattern_plan"],
        ),
        "domain_intake_packet": (
            intake_builder.render_markdown,
            chain["domain_intake_packet"],
        ),
        "domain_intake_validation": (
            intake_validator.render_markdown,
            chain["domain_intake_validation"],
        ),
        "domain_seed_proposal": (
            seed_proposal_builder.render_markdown,
            chain["domain_seed_proposal"],
        ),
    }
    for key, (markdown_fn, doc) in writers.items():
        _write_doc_pair(
            doc,
            file_paths[f"{key}_json"],
            file_paths[f"{key}_markdown"],
            markdown_fn(doc),
        )
    return paths


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown regulatory curation bundle."""
    summary = doc["summary"]
    lines: list[str] = [
        "# Regulatory Curation Bundle",
        "",
        (
            "This bundle is a deterministic, non-mutating status report for the "
            "regulatory-miss sister-benchmark chain. It is not legal advice, not "
            "source verification, not prompt generation, and not comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Pattern count | {summary['pattern_count']} |",
        f"| Active seeds | {summary['active_seed_count']} |",
        f"| Candidate domains | {summary['candidate_count']} |",
        f"| Ranked candidate queue | {summary['candidate_queue_count']} |",
        f"| Top candidate | {_md_cell(summary['top_candidate_id'])} |",
        f"| Deferred domains | {summary['defer_count']} |",
        f"| Candidate intake rows | {summary['candidate_intake_rows']} |",
        f"| Validation pending/deferred rows | {summary['validation_pending_or_deferred_rows']} |",
        f"| Validation accepted seed proposals | {summary['validation_accepted_domain_seed_proposals']} |",
        f"| Validation invalid rows | {summary['validation_invalid_rows']} |",
        f"| Seed scaffold operations | {summary['seed_scaffold_operations']} |",
        f"| Ready for seed file creation | {str(bool(summary['ready_for_seed_file_creation'])).lower()} |",
        f"| Ready for manual registry patch | {str(bool(summary['ready_for_manual_registry_patch'])).lower()} |",
        f"| Ready for prompt generation | {str(bool(summary['ready_for_prompt_generation'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Consistency Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ]
    for check in doc["consistency_checks"]:
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
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=pathlib.Path, default=CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=REGISTRY)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--md-out", type=pathlib.Path, default=MD_OUT, help="Markdown report path")
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown bundle report")
    ap.add_argument("--write-components", action="store_true", help="also write each component JSON/Markdown artifact")
    ap.add_argument("--component-dir", type=pathlib.Path, default=OUT_DIR, help="directory for --write-components outputs")
    args = ap.parse_args(argv)

    chain = build_regulatory_curation_chain(
        config_path=args.config,
        registry_path=args.registry,
        component_dir=args.component_dir,
    )
    doc = build_regulatory_curation_bundle(
        chain=chain,
        config_path=args.config,
        registry_path=args.registry,
        component_dir=args.component_dir,
    )
    if args.write_components:
        doc["artifact_paths"].update(write_component_artifacts(chain, output_dir=args.component_dir))
    doc["artifact_paths"]["regulatory_curation_bundle_json"] = _artifact_path(args.out)
    if not args.no_md:
        doc["artifact_paths"]["regulatory_curation_bundle_markdown"] = _artifact_path(args.md_out)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        "[regulatory-curation-bundle] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['candidate_count']} candidates; "
        f"{summary['validation_accepted_domain_seed_proposals']} accepted seed proposals; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["consistency_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
