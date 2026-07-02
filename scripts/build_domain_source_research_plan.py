#!/usr/bin/env python3
"""Build a source-research plan from a domain grounding queue.

This script is one step after ``build_domain_grounding_queue.py``. It turns
blocked source-object and scope-refinement queue items into curator-facing
search tasks. It does not fetch sources, validate law, or promote any manifest
row. The output is a reproducible plan for human/source review before a
developing-country or other non-trafficking domain is used as comparable
benchmark evidence.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from build_domain_grounding_queue import build_grounding_queue  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
_SAFE_DOMAIN_ID = re.compile(r"^[a-z0-9_:-]{1,80}$")

_JURISDICTION_LABELS = {
    "BD": "Bangladesh",
    "NP": "Nepal",
    "ID": "Indonesia",
    "PH": "Philippines",
    "LK": "Sri Lanka",
    "KH": "Cambodia",
    "VN": "Vietnam",
    "KE": "Kenya",
    "GH": "Ghana",
    "NG": "Nigeria",
    "ET": "Ethiopia",
    "UG": "Uganda",
    "CO": "Colombia",
    "VE": "Venezuela",
    "HK": "Hong Kong",
    "EU": "European Union",
    "cross_jurisdiction": "cross-jurisdiction",
}

_GOV_QUERY_SITES = {
    "BD": "site:gov.bd",
    "NP": "site:gov.np",
    "ID": "site:go.id",
    "PH": "site:gov.ph",
    "LK": "site:gov.lk",
    "KH": "site:gov.kh",
    "VN": "site:gov.vn",
    "KE": "site:go.ke",
    "GH": "site:gov.gh",
    "NG": "site:gov.ng",
    "ET": "site:gov.et",
    "UG": "site:go.ug",
    "CO": "site:gov.co",
    "VE": "site:gob.ve",
    "HK": "site:gov.hk",
    "EU": "site:europa.eu",
}

_SOURCE_OBJECT_FIELDS = [
    "id",
    "title",
    "jurisdiction",
    "source_type",
    "authority",
    "url",
    "verification_status",
    "verified_date",
    "coverage_tags",
    "use_limitations",
]


def _safe_domain_id(domain_id: str) -> str:
    if not _SAFE_DOMAIN_ID.fullmatch(domain_id):
        raise ValueError(f"unsafe domain id: {domain_id!r}")
    return domain_id


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").upper()
    return slug[:96] or "TASK"


def _category_phrase(category: str) -> str:
    return " ".join(str(category).replace("-", "_").split("_")).strip() or "worker protection"


def _jurisdiction_label(jurisdiction: str) -> str:
    return _JURISDICTION_LABELS.get(jurisdiction, jurisdiction)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = " ".join(str(value).split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out


def _source_queries(jurisdiction: str, category: str) -> list[str]:
    label = _jurisdiction_label(jurisdiction)
    phrase = _category_phrase(category)
    if jurisdiction == "cross_jurisdiction":
        return [
            f'"cross-border" "{phrase}" labour migration regulator',
            f'"{phrase}" migrant worker official guidance',
            f'"{phrase}" international labour standard worker rights',
            f'"{phrase}" legal aid migrant workers source',
            f'"{phrase}" archive date official notice',
        ]
    queries = [
        f'"{label}" "{phrase}" official labour law',
        f'"{label}" "{phrase}" labour ministry',
        f'"{label}" "{phrase}" government gazette',
        f'"{label}" "{phrase}" recruitment regulator complaint',
        f'"{label}" "{phrase}" legal aid worker rights',
    ]
    gov_site = _GOV_QUERY_SITES.get(jurisdiction)
    if gov_site:
        queries.append(f'"{label}" "{phrase}" {gov_site}')
    return queries


def _scope_queries(scope: str, category: str) -> list[str]:
    phrase = _category_phrase(category)
    queries = [
        f'"{scope}" "{phrase}" destination jurisdiction worker rights',
        f'"{scope}" "{phrase}" labour migration regulator',
        f'"{scope}" "{phrase}" complaint forum worker protection',
    ]
    scope_lc = scope.lower()
    if scope_lc == "gulf":
        queries.extend([
            f'"Gulf states" "{phrase}" recruitment complaint regulator',
            f'"Gulf" "{phrase}" origin destination labour ministry migrant worker',
        ])
    elif scope_lc == "distant-water fleet":
        queries.extend([
            f'"distant-water fleet" "{phrase}" flag state port state labour law',
            f'"distant-water fleet" "{phrase}" fisheries seafarer regulator',
        ])
    elif scope_lc == "export supply chain":
        queries.extend([
            f'"export supply chain" "{phrase}" buyer contractor labour regulator',
            f'"export supply chain" "{phrase}" worker housing association law',
        ])
    elif scope_lc == "overseas recruitment":
        queries.extend([
            f'"overseas recruitment" "{phrase}" origin destination regulator',
            f'"overseas recruitment" "{phrase}" recruitment agency complaint channel',
        ])
    return _dedupe(queries)


def _source_research_task(item: dict[str, Any]) -> dict[str, Any]:
    jurisdiction = str(item.get("jurisdiction") or "cross_jurisdiction")
    category = str(item.get("category") or "uncategorized")
    source_id = str(item.get("suggested_source_id") or f"LOCAL-{jurisdiction}-{_slug(category)}")
    label = _jurisdiction_label(jurisdiction)
    phrase = _category_phrase(category)
    return {
        "task_id": f"RESEARCH-{_slug(source_id)}",
        "source_id": source_id,
        "action": item.get("action"),
        "jurisdiction": jurisdiction,
        "jurisdiction_label": label,
        "category": category,
        "category_phrase": phrase,
        "current_status": item.get("current_status"),
        "blocked_prompt_ids": list(item.get("blocked_prompt_ids") or []),
        "research_objective": (
            f"Find dated, citable source objects for {label} covering {phrase}; "
            "do not assert local law until review fills the manifest row."
        ),
        "required_source_types": [
            "official statute, regulation, code, gazette, or consolidated legal text",
            "official labour, migration, recruitment, consumer, tenancy, court, or regulator guidance",
            "public-interest legal aid, union, worker-centre, NGO, or academic explainer with a citation trail",
            "archived informal notice or registry page only when corroborated by official/public-interest sources",
        ],
        "search_queries": _source_queries(jurisdiction, category),
        "curation_steps": [
            "record source title, publisher/authority, URL, access date, and archive/date evidence",
            "separate origin-state, destination-state, and cross-border responsibility when more than one forum is implicated",
            "capture complaint channel and safety caveats only when the source is current and public",
            "send the row for practitioner or domain-expert review before any benchmark scoring claim",
        ],
        "reject_if": [
            "the source has no date, authority, or stable URL/archive trail",
            "the source is only a social-media post, screenshot, chat forward, or private case file",
            "the source exposes worker names, contacts, complainant details, or other raw PII",
            "the source describes a different jurisdiction, sector, worker class, or time period without caveat",
            "the source is paywalled or licensed in a way that prevents reproducible public review",
        ],
        "manifest_fields_to_fill": _SOURCE_OBJECT_FIELDS,
        "source_queue_required_evidence": list(item.get("required_evidence") or []),
    }


def _scope_refinement_task(item: dict[str, Any]) -> dict[str, Any]:
    scope = str(item.get("scope") or "unresolved")
    category = str(item.get("category") or "uncategorized")
    phrase = _category_phrase(category)
    return {
        "task_id": f"REFINE-{_slug(item.get('suggested_scope_id') or scope + '-' + category)}",
        "scope_id": item.get("suggested_scope_id"),
        "scope": scope,
        "category": category,
        "category_phrase": phrase,
        "blocked_prompt_ids": list(item.get("blocked_prompt_ids") or []),
        "research_questions": [
            "Which concrete destination, flag, port, forum, or regulator jurisdiction is intended?",
            "Which origin-state and destination-state rules must be checked separately?",
            "Which public source can date the jurisdiction split and responsible authority?",
            "Would this broad label be unsafe as a verified local-law row, and why?",
        ],
        "search_queries": _scope_queries(scope, category),
        "acceptance_checks": [
            "at least one concrete jurisdiction or regulator forum is named for each scoring-relevant issue",
            "origin, destination, flag, port, buyer, contractor, and forum roles are separated where applicable",
            "new source-object tasks can be created for every resolved jurisdiction/category pair",
            "the broad label remains a scope note, not a local-law authority",
        ],
        "reject_if": [
            "the result keeps a regional or sector label without identifying a responsible jurisdiction",
            "the result collapses maritime, supply-chain, origin, and destination responsibility into one forum",
            "the result relies on private worker/case data rather than public-source metadata",
        ],
        "scope_queue_required_evidence": list(item.get("required_evidence") or []),
    }


def build_source_research_plan(
    domain_id: str,
    *,
    queue_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a curator-facing source-research plan for a domain queue."""
    domain_id = _safe_domain_id(domain_id)
    queue_doc = queue_doc or build_grounding_queue(domain_id)
    queue_meta = queue_doc.get("_meta", {})
    queue_summary = queue_doc.get("summary", {})
    source_tasks = [
        _source_research_task(item)
        for item in queue_doc.get("source_object_queue", [])
        if isinstance(item, dict)
    ]
    scope_tasks = [
        _scope_refinement_task(item)
        for item in queue_doc.get("scope_refinement_queue", [])
        if isinstance(item, dict)
    ]
    source_tasks.sort(key=lambda item: (item["jurisdiction"], item["category"], item["source_id"]))
    scope_tasks.sort(key=lambda item: (item["scope"], item["category"], str(item["scope_id"])))

    blocked_prompt_ids = sorted({
        prompt_id
        for task in [*source_tasks, *scope_tasks]
        for prompt_id in task.get("blocked_prompt_ids", [])
    })
    return {
        "_meta": {
            "domain": domain_id,
            "display_name": queue_meta.get("display_name"),
            "status": (
                "source-research plan; not legal advice, not source verification, "
                "and not comparable benchmark evidence"
            ),
            "source_queue_status": queue_meta.get("status"),
            "grounding_queue_inputs": {
                "scheme_pack": queue_meta.get("scheme_pack"),
                "grounding_manifest": queue_meta.get("grounding_manifest"),
            },
        },
        "summary": {
            "source_object_tasks": len(source_tasks),
            "scope_refinement_tasks": len(scope_tasks),
            "blocked_prompt_count": len(blocked_prompt_ids),
            "prompts_ready_for_comparable_run": queue_summary.get("prompts_ready_for_comparable_run"),
            "prompts_blocked_for_comparable_run": queue_summary.get("prompts_blocked_for_comparable_run"),
            "missing_verified_local_jurisdictions": queue_summary.get(
                "missing_verified_local_jurisdictions", []
            ),
            "unresolved_corridor_scopes": queue_summary.get("unresolved_corridor_scopes", []),
            "policy": (
                "Use this as a search and curation checklist only. Add or promote manifest rows "
                "only after dated source review and practitioner/domain-expert validation."
            ),
        },
        "source_research_tasks": source_tasks,
        "scope_refinement_tasks": scope_tasks,
    }


def default_out_path(domain_id: str) -> pathlib.Path:
    return OUT_DIR / f"{_safe_domain_id(domain_id)}_source_research_plan.json"


def default_markdown_path(json_path: pathlib.Path) -> pathlib.Path:
    return json_path.with_suffix(".md")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _md_list(values: list[Any]) -> str:
    return ", ".join(_md_cell(v) for v in values) if values else "-"


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a Markdown handoff for source researchers."""
    meta = doc["_meta"]
    summary = doc["summary"]
    lines: list[str] = [
        f"# Domain Source Research Plan - {_md_cell(meta.get('display_name') or meta.get('domain'))}",
        "",
        (
            "This report is a research and curation checklist. It is not legal advice, not a source "
            "verification result, not training data, and not comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Source-object research tasks | {summary['source_object_tasks']} |",
        f"| Scope-refinement tasks | {summary['scope_refinement_tasks']} |",
        f"| Blocked prompts covered | {summary['blocked_prompt_count']} |",
        f"| Prompts ready for comparable run | {summary['prompts_ready_for_comparable_run']} |",
        f"| Prompts blocked for comparable run | {summary['prompts_blocked_for_comparable_run']} |",
        "",
        "## Coverage Targets",
        "",
        f"- Jurisdictions missing local-law coverage: {_md_list(summary['missing_verified_local_jurisdictions'])}",
        f"- Unresolved corridor scopes: {_md_list(summary['unresolved_corridor_scopes'])}",
        "",
        "## Source-Object Research Tasks",
        "",
        "| Task | Jurisdiction | Category | Current status | Blocked prompts | Query count |",
        "|---|---|---|---|---|---:|",
    ]
    for task in doc["source_research_tasks"]:
        lines.append(
            f"| `{_md_cell(task['task_id'])}` "
            f"| {_md_cell(task['jurisdiction_label'])} "
            f"| {_md_cell(task['category'])} "
            f"| {_md_cell(task['current_status'])} "
            f"| {_md_list(task['blocked_prompt_ids'])} "
            f"| {len(task['search_queries'])} |"
        )
    lines.extend([
        "",
        "## Scope-Refinement Tasks",
        "",
        "| Task | Scope | Category | Blocked prompts | Query count |",
        "|---|---|---|---|---:|",
    ])
    for task in doc["scope_refinement_tasks"]:
        lines.append(
            f"| `{_md_cell(task['task_id'])}` "
            f"| {_md_cell(task['scope'])} "
            f"| {_md_cell(task['category'])} "
            f"| {_md_list(task['blocked_prompt_ids'])} "
            f"| {len(task['search_queries'])} |"
        )
    lines.extend([
        "",
        "## Required Source Discipline",
        "",
        "- Prefer official law, regulation, gazette, regulator, court, labour ministry, or equivalent sources.",
        "- Use public-interest explainers only when they preserve a citation trail to controlling sources.",
        "- Archive and date informal notices, registry pages, or social posts before relying on them.",
        "- Reject private case files, worker contact details, and complainant-level rows.",
        "- Keep broad corridor labels out of local-law rows until concrete jurisdictions are resolved.",
        "",
        "## Example Queries",
        "",
    ])
    for task in doc["source_research_tasks"][:8]:
        lines.append(f"### `{_md_cell(task['task_id'])}`")
        lines.extend(f"- `{_md_cell(query)}`" for query in task["search_queries"])
        lines.append("")
    for task in doc["scope_refinement_tasks"][:5]:
        lines.append(f"### `{_md_cell(task['task_id'])}`")
        lines.extend(f"- `{_md_cell(query)}`" for query in task["search_queries"])
        lines.append("")
    lines.extend([
        "## Inputs",
        "",
        f"- Prompt pack: `{_md_cell(meta['grounding_queue_inputs'].get('scheme_pack'))}`",
        f"- Grounding manifest: `{_md_cell(meta['grounding_queue_inputs'].get('grounding_manifest'))}`",
        "",
    ])
    return "\n".join(lines)


def _load_queue(path: pathlib.Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"queue file must contain a JSON object: {path}")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default="developing_country_worker_protections")
    ap.add_argument("--queue", type=pathlib.Path, default=None, help="optional prebuilt grounding queue JSON")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--md-out", type=pathlib.Path, default=None, help="Markdown report path; defaults to --out with .md suffix")
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown review report")
    args = ap.parse_args(argv)

    queue_doc = _load_queue(args.queue) if args.queue else None
    doc = build_source_research_plan(args.domain, queue_doc=queue_doc)
    out_path = args.out or default_out_path(args.domain)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out or default_markdown_path(out_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        f"wrote {out_path}: {summary['source_object_tasks']} source-object tasks; "
        f"{summary['scope_refinement_tasks']} scope-refinement tasks"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
