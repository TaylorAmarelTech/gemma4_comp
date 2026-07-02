#!/usr/bin/env python3
"""Build a source-curation gap queue for a benchmark domain.

This is the bridge between a synthetic domain seed and a source-verified
benchmark run. It does not assert legal content. It reads the registered
prompt pack plus the domain grounding manifest and emits the missing or pending
source objects needed before a non-trafficking domain can be treated as
comparable lift evidence.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import defaultdict
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from domain_grounding import load_grounding_manifest  # noqa: E402
from domain_registry import get_domain, resolve_grounding_manifest, resolve_scheme_pack  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
_SAFE_DOMAIN_ID = re.compile(r"^[a-z0-9_:-]{1,80}$")
_JURISDICTION_TOKEN = re.compile(r"\b[A-Z]{2}\b")
_VERIFIED_LOCAL = "verified_local_law"
_PENDING_STATUSES = {"needs_source", "needs_archive", "unsafe_without_archive"}
_JURISDICTION_ALIASES = (
    (re.compile(r"\bHong Kong\b", re.IGNORECASE), "HK"),
)
_UNRESOLVED_SCOPE_PATTERNS = (
    (re.compile(r"\bGulf\b", re.IGNORECASE), "Gulf"),
    (re.compile(r"\bdistant-water fleet\b", re.IGNORECASE), "distant-water fleet"),
    (re.compile(r"\bexport supply chain\b", re.IGNORECASE), "export supply chain"),
    (re.compile(r"\boverseas recruitment\b", re.IGNORECASE), "overseas recruitment"),
)


def _safe_domain_id(domain_id: str) -> str:
    if not _SAFE_DOMAIN_ID.fullmatch(domain_id):
        raise ValueError(f"unsafe domain id: {domain_id!r}")
    return domain_id


def _load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").upper()
    return slug[:80] or "SOURCE"


def _corridor_jurisdictions(corridor: Any) -> list[str]:
    if not isinstance(corridor, str):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for token in _JURISDICTION_TOKEN.findall(corridor):
        if token not in seen:
            seen.add(token)
            out.append(token)
    for pattern, jurisdiction in _JURISDICTION_ALIASES:
        if pattern.search(corridor) and jurisdiction not in seen:
            seen.add(jurisdiction)
            out.append(jurisdiction)
    return out


def _corridor_unresolved_scopes(corridor: Any) -> list[str]:
    if not isinstance(corridor, str):
        return []
    out: list[str] = []
    for pattern, scope in _UNRESOLVED_SCOPE_PATTERNS:
        if pattern.search(corridor):
            out.append(scope)
    return out


def _source_indexes(sources: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]],
                                                           dict[str, list[dict[str, Any]]]]:
    by_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_jurisdiction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sources:
        by_jurisdiction[row["jurisdiction"]].append(row)
        for tag in row.get("coverage_tags", []):
            by_tag[tag].append(row)
    return by_tag, by_jurisdiction


def _has_verified_local_for_jurisdiction(category_rows: list[dict[str, Any]], jurisdiction: str) -> bool:
    return any(
        row["verification_status"] == _VERIFIED_LOCAL and row["jurisdiction"] == jurisdiction
        for row in category_rows
    )


def build_grounding_queue(domain_id: str) -> dict[str, Any]:
    """Return prompt-level grounding gaps and aggregate source-object queue items."""
    domain_id = _safe_domain_id(domain_id)
    spec = get_domain(domain_id)
    scheme_pack = resolve_scheme_pack(domain_id)
    manifest_path = resolve_grounding_manifest(domain_id)
    if manifest_path is None:
        raise ValueError(f"domain {domain_id!r} has no grounding_manifest in registry")
    manifest = load_grounding_manifest(manifest_path)
    prompts = _load_jsonl(scheme_pack)
    by_tag, by_jurisdiction = _source_indexes(manifest["sources"])

    prompt_gaps: list[dict[str, Any]] = []
    queue_acc: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    scope_acc: dict[tuple[str, str], dict[str, Any]] = {}
    for prompt in prompts:
        prompt_id = str(prompt.get("id", ""))
        category = str(prompt.get("category", ""))
        corridor = str(prompt.get("corridor", ""))
        jurisdictions = _corridor_jurisdictions(corridor)
        unresolved_scopes = _corridor_unresolved_scopes(corridor)
        category_rows = by_tag.get(category, [])
        verified_local = [
            row for row in category_rows
            if row["verification_status"] == _VERIFIED_LOCAL
            and (not jurisdictions or row["jurisdiction"] in jurisdictions)
        ]
        pending_rows = [
            row for row in category_rows
            if row["verification_status"] in _PENDING_STATUSES
            and (not jurisdictions or row["jurisdiction"] in jurisdictions or row["jurisdiction"] == "cross_jurisdiction")
        ]
        missing_jurisdictions = [j for j in jurisdictions if j not in by_jurisdiction]
        pending_jurisdictions = [
            j for j in jurisdictions
            if j in by_jurisdiction
            and not _has_verified_local_for_jurisdiction(category_rows, j)
        ]
        missing_verified_local_jurisdictions = [
            j for j in jurisdictions
            if not _has_verified_local_for_jurisdiction(category_rows, j)
        ]
        missing_category_source = not category_rows
        blocked = (
            missing_category_source
            or not verified_local
            or bool(missing_verified_local_jurisdictions)
            or bool(unresolved_scopes)
        )
        gap = {
            "prompt_id": prompt_id,
            "category": category,
            "corridor": corridor,
            "jurisdictions": jurisdictions,
            "unresolved_corridor_scopes": unresolved_scopes,
            "matched_source_ids": [row["id"] for row in category_rows],
            "verified_local_source_ids": [row["id"] for row in verified_local],
            "pending_source_ids": [row["id"] for row in pending_rows],
            "missing_category_source": missing_category_source,
            "missing_jurisdictions": missing_jurisdictions,
            "pending_jurisdictions": pending_jurisdictions,
            "missing_verified_local_jurisdictions": missing_verified_local_jurisdictions,
            "ready_for_comparable_run": not blocked,
        }
        prompt_gaps.append(gap)

        target_jurisdictions = jurisdictions or ["cross_jurisdiction"]
        for jurisdiction in target_jurisdictions:
            existing_pending = [
                row for row in category_rows
                if row["verification_status"] in _PENDING_STATUSES
                and row["jurisdiction"] in {jurisdiction, "cross_jurisdiction"}
            ]
            existing_id = existing_pending[0]["id"] if existing_pending else None
            action = "curate_and_promote_existing_manifest_row" if existing_id else "add_manifest_row"
            key = (jurisdiction, category, existing_id)
            item = queue_acc.setdefault(key, {
                "suggested_source_id": existing_id or f"LOCAL-{jurisdiction}-{_slug(category)}",
                "action": action,
                "jurisdiction": jurisdiction,
                "category": category,
                "current_status": existing_pending[0]["verification_status"] if existing_pending else "missing",
                "blocked_prompt_ids": [],
                "required_evidence": [
                    "dated official or public-interest source object",
                    "controlling local law/regulation or explicit no-source finding",
                    "responsible regulator, complaint channel, or safe referral source",
                    "archive/date trail for informal, social-media, scanned, or registry-screenshot sources",
                    "practitioner/expert review before public scoring or training use",
                ],
            })
            item["blocked_prompt_ids"].append(prompt_id)
        for scope in unresolved_scopes:
            key = (scope, category)
            item = scope_acc.setdefault(key, {
                "suggested_scope_id": f"SCOPE-{_slug(scope)}-{_slug(category)}",
                "action": "refine_corridor_scope_before_local_law_verification",
                "scope": scope,
                "category": category,
                "blocked_prompt_ids": [],
                "required_evidence": [
                    "identify concrete destination, flag, port, forum, or regulator jurisdiction(s)",
                    "document origin/destination/flag/port responsibility split before local-law scoring",
                    "add dated source objects for each resolved jurisdiction",
                    "keep broad regional labels out of verified_local_law rows",
                ],
            })
            item["blocked_prompt_ids"].append(prompt_id)

    ready = [g for g in prompt_gaps if g["ready_for_comparable_run"]]
    missing_category_tags = sorted({g["category"] for g in prompt_gaps if g["missing_category_source"]})
    missing_jurisdictions = sorted({j for g in prompt_gaps for j in g["missing_jurisdictions"]})
    pending_jurisdictions = sorted({j for g in prompt_gaps for j in g["pending_jurisdictions"]})
    missing_verified_local_jurisdictions = sorted({
        j for g in prompt_gaps for j in g["missing_verified_local_jurisdictions"]
    })
    unresolved_corridor_scopes = sorted({s for g in prompt_gaps for s in g["unresolved_corridor_scopes"]})
    return {
        "_meta": {
            "domain": domain_id,
            "display_name": spec.get("display_name"),
            "scheme_pack": scheme_pack.relative_to(_ROOT).as_posix(),
            "grounding_manifest": manifest_path.relative_to(_ROOT).as_posix(),
            "status": "source-curation queue; not legal advice and not comparable benchmark evidence",
        },
        "summary": {
            "prompt_count": len(prompts),
            "prompts_ready_for_comparable_run": len(ready),
            "prompts_blocked_for_comparable_run": len(prompt_gaps) - len(ready),
            "verified_local_law_rows": sum(
                1 for row in manifest["sources"] if row["verification_status"] == _VERIFIED_LOCAL
            ),
            "missing_category_tags": missing_category_tags,
            "missing_jurisdictions": missing_jurisdictions,
            "pending_jurisdictions": pending_jurisdictions,
            "missing_verified_local_jurisdictions": missing_verified_local_jurisdictions,
            "unresolved_corridor_scopes": unresolved_corridor_scopes,
            "prompts_needing_scope_refinement": sum(
                1 for g in prompt_gaps if g["unresolved_corridor_scopes"]
            ),
        },
        "source_object_queue": sorted(
            queue_acc.values(),
            key=lambda item: (item["jurisdiction"], item["category"], item["suggested_source_id"]),
        ),
        "scope_refinement_queue": sorted(
            scope_acc.values(),
            key=lambda item: (item["scope"], item["category"], item["suggested_scope_id"]),
        ),
        "prompt_gaps": prompt_gaps,
    }


def default_out_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_grounding_queue.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _md_list(values: list[Any]) -> str:
    return ", ".join(_md_cell(v) for v in values) if values else "-"


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a reviewer-facing Markdown summary for the grounding queue."""
    meta = doc["_meta"]
    summary = doc["summary"]
    queue = doc["source_object_queue"]
    scope_queue = doc.get("scope_refinement_queue", [])
    gaps = doc["prompt_gaps"]
    lines: list[str] = [
        f"# Domain Grounding Curation Queue - {_md_cell(meta.get('display_name') or meta.get('domain'))}",
        "",
        (
            "This report is a source-curation work queue. It is not legal advice, not training data, "
            "and not comparable benchmark evidence. A prompt is ready for comparable scoring only when "
            "the relevant local-law/source rows have been promoted to `verified_local_law` after dated "
            "source review."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Prompt count | {summary['prompt_count']} |",
        f"| Prompts ready for comparable run | {summary['prompts_ready_for_comparable_run']} |",
        f"| Prompts blocked for comparable run | {summary['prompts_blocked_for_comparable_run']} |",
        f"| Verified local-law rows | {summary['verified_local_law_rows']} |",
        f"| Source-object queue items | {len(queue)} |",
        f"| Prompts needing scope refinement | {summary['prompts_needing_scope_refinement']} |",
        "",
        "## Coverage Gaps",
        "",
        f"- Missing category tags: {_md_list(summary['missing_category_tags'])}",
        f"- Missing jurisdictions: {_md_list(summary['missing_jurisdictions'])}",
        f"- Pending jurisdictions: {_md_list(summary['pending_jurisdictions'])}",
        f"- Jurisdictions missing verified local law: {_md_list(summary['missing_verified_local_jurisdictions'])}",
        f"- Unresolved corridor scopes: {_md_list(summary['unresolved_corridor_scopes'])}",
        "",
        "## Required Evidence For Each Source Object",
        "",
    ]
    if queue:
        for evidence in queue[0]["required_evidence"]:
            lines.append(f"- {_md_cell(evidence)}")
    else:
        lines.append("- No source-object queue items.")
    lines.extend([
        "",
        "## Source-Object Queue",
        "",
        "| Source ID | Action | Jurisdiction | Category | Status | Blocked prompts |",
        "|---|---|---|---|---|---|",
    ])
    for item in queue:
        lines.append(
            f"| `{_md_cell(item['suggested_source_id'])}` "
            f"| {_md_cell(item['action'])} "
            f"| {_md_cell(item['jurisdiction'])} "
            f"| {_md_cell(item['category'])} "
            f"| {_md_cell(item['current_status'])} "
            f"| {_md_list(item['blocked_prompt_ids'])} |"
        )
    lines.extend([
        "",
        "## Scope Refinement Queue",
        "",
        "| Scope ID | Scope | Category | Blocked prompts |",
        "|---|---|---|---|",
    ])
    if scope_queue:
        for item in scope_queue:
            lines.append(
                f"| `{_md_cell(item['suggested_scope_id'])}` "
                f"| {_md_cell(item['scope'])} "
                f"| {_md_cell(item['category'])} "
                f"| {_md_list(item['blocked_prompt_ids'])} |"
            )
    else:
        lines.append("| - | - | - | - |")
    lines.extend([
        "",
        "## Prompt Blockers",
        "",
        "| Prompt | Corridor | Category | Jurisdictions | Unresolved scopes | Verified local sources | Pending sources | Missing verified-local jurisdictions | Missing category source | Ready |",
        "|---|---|---|---|---|---|---|---|---|---:|",
    ])
    for gap in gaps:
        lines.append(
            f"| `{_md_cell(gap['prompt_id'])}` "
            f"| {_md_cell(gap['corridor'])} "
            f"| {_md_cell(gap['category'])} "
            f"| {_md_list(gap['jurisdictions'])} "
            f"| {_md_list(gap['unresolved_corridor_scopes'])} "
            f"| {_md_list(gap['verified_local_source_ids'])} "
            f"| {_md_list(gap['pending_source_ids'])} "
            f"| {_md_list(gap['missing_verified_local_jurisdictions'])} "
            f"| {str(bool(gap['missing_category_source'])).lower()} "
            f"| {str(bool(gap['ready_for_comparable_run'])).lower()} |"
        )
    lines.extend([
        "",
        "## Inputs",
        "",
        f"- Prompt pack: `{_md_cell(meta['scheme_pack'])}`",
        f"- Grounding manifest: `{_md_cell(meta['grounding_manifest'])}`",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default="developing_country_worker_protections")
    ap.add_argument("--out", default=None)
    ap.add_argument("--md-out", default=None, help="Markdown report path; defaults to --out with .md suffix")
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown review report")
    args = ap.parse_args(argv)

    doc = build_grounding_queue(args.domain)
    out_path = pathlib.Path(args.out) if args.out else default_out_path(args.domain)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = pathlib.Path(args.md_out) if args.md_out else default_markdown_path(out_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        f"wrote {out_path}: {summary['prompts_blocked_for_comparable_run']}/"
        f"{summary['prompt_count']} prompts blocked; "
        f"{len(doc['source_object_queue'])} source-object queue items"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
