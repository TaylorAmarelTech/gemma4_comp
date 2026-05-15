"""Bulk File Review prompts."""
from __future__ import annotations

import json as _json

GRAPH_CHAT_SYSTEM_PROMPT = (
    "You are DueCare's case-bundle analyst. The user has uploaded a folder "
    "of case material (chat exports, scans, recruitment ads, court filings, "
    "testimony transcripts). The kernel processed it locally and produced a "
    "structured summary you can see below. Answer the user's question using "
    "ONLY the information in the bundle summary. Cite specific row_ids and "
    "GREP rule_ids when you support a claim. If the bundle does not contain "
    "evidence for the question, say so explicitly. Do not invent rows, "
    "amounts, names, or statutes. Do not reveal hidden reasoning, scratchpad "
    "notes, or step-by-step internal analysis. Return only the final answer. "
    "Prefer: short answer, evidence table, caveats, next review steps."
)

GRAPH_EDGE_PROMPT_TEMPLATES: list[dict] = [
    {
        "id": "case_graph_edges",
        "label": "Extract case graph edges",
        "purpose": (
            "Ask Gemma 4 to propose typed entity, payment, document-control, "
            "folder, timeline, and journey-stage edges from local bundle facts."
        ),
        "output_keys": ["edges", "rag_candidates", "uncertainties"],
    },
    {
        "id": "cross_document_linking",
        "label": "Link repeated actors across documents",
        "purpose": (
            "Ask Gemma 4 to identify agencies, employers, recruiters, payment "
            "recipients, folders, and phrases that appear across multiple rows."
        ),
        "output_keys": ["edges", "entity_aliases", "uncertainties"],
    },
    {
        "id": "rag_candidate_synthesis",
        "label": "Draft RAG and knowledge candidates",
        "purpose": (
            "Ask Gemma 4 to turn repeated non-PII patterns into reviewable "
            "context snippets, modus-operandi notes, and extracted-fact shapes."
        ),
        "output_keys": ["rag_candidates", "knowledge_object_hints", "uncertainties"],
    },
    {
        "id": "media_page_questions",
        "label": "Plan OCR and multimodal page review",
        "purpose": (
            "Ask Gemma 4 to define local vision/OCR questions for images, scans, "
            "screenshots, receipts, and PDFs that remain queued as media assets."
        ),
        "output_keys": ["media_questions", "edges", "uncertainties"],
    },
]

GRAPH_EDGE_EXTRACTION_SYSTEM_PROMPT = (
    "You are DueCare's local graph extraction harness. You receive a compact "
    "summary of a case bundle already processed inside the Kaggle kernel. "
    "Propose additional graph edges and RAG/knowledge candidates using ONLY "
    "the supplied facts, row_ids, folder paths, OCR text if present, and media "
    "queue metadata. Do not use cloud services, external search, or private "
    "knowledge. Do not invent names, amounts, statutes, contacts, or row_ids. "
    "Return JSON only with keys: edges, rag_candidates, uncertainties. "
    "Each edge must include edge_type, source_node, target_node, confidence, "
    "evidence {file, page, chunk_id, quote}, extractors, local_only=true, "
    "and review_status='needs_review'. Prefer conservative edges with direct "
    "row evidence over speculative links."
)


def build_graph_edge_extraction_prompt(
    bundle: dict | None,
    *,
    prompt_id: str = "case_graph_edges",
    limit: int = 24,
) -> str:
    """Render a bounded prompt for the local Gemma 4 graph-edge pass."""
    if not bundle:
        return "(No bundle uploaded yet.)"
    intelligence = bundle.get("intelligence") or {}
    plan = intelligence.get("processing_plan") or {}
    template = next(
        (t for t in GRAPH_EDGE_PROMPT_TEMPLATES if t.get("id") == prompt_id),
        GRAPH_EDGE_PROMPT_TEMPLATES[0],
    )
    compact = {
        "schema_version": "duecare.process.gemma_edge_prompt.v1",
        "local_only": True,
        "remote_api_calls": False,
        "prompt_template": template,
        "bundle_summary": bundle.get("summary") or {},
        "allowed_edge_types": [
            "charged_or_collected_fee",
            "fee_amount_observed",
            "salary_deduction_signal",
            "document_control_signal",
            "threat_or_retaliation_signal",
            "rule_hit",
            "filed_under",
            "located_at",
            "dated_evidence",
            "same_actor_or_phrase",
            "media_requires_ocr",
            "media_requires_gemma_vision",
            "journey_stage_observation",
            "candidate_rag_grounding",
        ],
        "typed_edges_seed": (intelligence.get("typed_edges") or [])[:limit],
        "rag_candidates_seed": (intelligence.get("rag_candidates") or [])[:10],
        "people": (intelligence.get("people") or [])[:12],
        "critical_fee_points": (intelligence.get("critical_fee_points") or [])[:16],
        "top_risk_signals": (intelligence.get("top_risk_signals") or [])[:16],
        "folder_counts": (intelligence.get("folder_counts") or [])[:16],
        "media_assets": (plan.get("media_assets") or [])[:12],
        "sample_rows": (bundle.get("results") or [])[:12],
    }
    return (
        "Run this local Gemma 4 edge pass.\n"
        "Task: " + str(template.get("purpose") or template.get("label")) + "\n"
        "Output JSON only. Keep every claim tied to row evidence.\n\n"
        + _json.dumps(compact, ensure_ascii=False)[:28000]
    )


def build_context_block(bundle: dict | None) -> str:
    """Render the bundle summary as a compact text block for Gemma."""
    if not bundle:
        return "(No bundle uploaded yet. Tell the user to upload a bundle first.)"
    summary = bundle.get("summary") or {}
    lines = [
        "Bundle summary:",
        f"  rows total: {summary.get('n_rows_total', 0)} "
        f"(processed: {summary.get('n_rows_processed', 0)})",
        f"  unique GREP rules fired: {summary.get('n_grep_rules_fired', 0)}",
        f"  entities extracted: {summary.get('n_entities_extracted', 0)}",
    ]
    top_grep = summary.get("top_grep") or []
    if top_grep:
        lines.append("  top GREP hits:")
        for item in top_grep[:8]:
            lines.append(f"    - {item.get('rule_id')}: {item.get('count')} hits")
    top_statutes = summary.get("top_statutes") or []
    if top_statutes:
        lines.append("  top statutes:")
        for item in top_statutes[:6]:
            lines.append(f"    - {item.get('statute')}: {item.get('count')} mentions")
    entity_totals = summary.get("entity_totals") or {}
    if entity_totals:
        lines.append(
            "  entity totals: "
            + ", ".join(f"{k}={v}" for k, v in entity_totals.items())
        )
    intelligence = bundle.get("intelligence") or {}
    if intelligence:
        lines.append("Intelligence graph:")
        lines.append(f"  people detected: {intelligence.get('n_people', 0)}")
        lines.append(f"  evidence edges: {intelligence.get('n_evidence_edges', 0)}")
        lines.append(f"  typed edges: {intelligence.get('n_typed_edges', 0)}")
        doc_counts = intelligence.get("document_type_counts") or {}
        if doc_counts:
            lines.append(
                "  document types: "
                + ", ".join(f"{k}={v}" for k, v in doc_counts.items())
            )
        people = intelligence.get("people") or []
        if people:
            lines.append("  highest risk people:")
            for p in people[:8]:
                lines.append(
                    "    "
                    f"{p.get('case_id')} name={p.get('name') or 'unknown'} "
                    f"risk={p.get('risk_score')} docs={p.get('n_documents')} "
                    f"signals={', '.join((p.get('risk_signals') or [])[:4])}"
                )
        journey = intelligence.get("journey_points") or []
        if journey:
            lines.append("  critical journey points:")
            for point in [p for p in journey if p.get("is_critical")][:12]:
                payments = ", ".join(x.get("amount", "") for x in (point.get("payments") or [])[:3])
                signals = ", ".join((point.get("risk_signals") or [])[:4])
                lines.append(
                    "    "
                    f"{point.get('stage')} row_id={point.get('row_id')} "
                    f"case={point.get('case_id')} payments=[{payments}] "
                    f"signals=[{signals}]"
                )
        typed_edges = intelligence.get("typed_edges") or []
        if typed_edges:
            lines.append("  typed edge samples:")
            for edge in typed_edges[:10]:
                evidence = edge.get("evidence") or {}
                lines.append(
                    "    "
                    f"{edge.get('edge_type')} {edge.get('source_node')} -> "
                    f"{edge.get('target_node')} row_id={edge.get('row_id')} "
                    f"quote={str(evidence.get('quote') or '')[:120]}"
                )
        rag_candidates = intelligence.get("rag_candidates") or []
        if rag_candidates:
            lines.append("  reviewable RAG candidates:")
            for cand in rag_candidates[:6]:
                lines.append(
                    "    "
                    f"{cand.get('knowledge_object_type')}:{cand.get('candidate_id')} "
                    f"title={cand.get('title')}"
                )
        brief = (intelligence.get("gemma_case_brief") or {}).get("json")
        if isinstance(brief, dict):
            lines.append("  Gemma case brief:")
            for key in ("case_theory", "risk_clusters", "missing_evidence"):
                if brief.get(key):
                    lines.append(f"    {key}: {brief.get(key)}")
    results = bundle.get("results") or []
    if results:
        lines.append("Sample rows (first 10):")
        for r in results[:10]:
            hit_summary = ", ".join(
                h.get("rule_id", "?") for h in (r.get("grep_hits") or [])[:3]
            )
            lines.append(
                f"  row_id={r.get('row_id')} hits=[{hit_summary}] chars={r.get('char_count')}"
            )
    return "\n".join(lines)
