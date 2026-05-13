"""Process Files prompts."""
from __future__ import annotations

GRAPH_CHAT_SYSTEM_PROMPT = (
    "You are DueCare's case-bundle analyst. The user has uploaded a folder "
    "of case material (chat exports, scans, recruitment ads, court filings, "
    "testimony transcripts). The kernel processed it locally and produced a "
    "structured summary you can see below. Answer the user's question using "
    "ONLY the information in the bundle summary. Cite specific row_ids and "
    "GREP rule_ids when you support a claim. If the bundle does not contain "
    "evidence for the question, say so explicitly. Do not invent rows, "
    "amounts, names, or statutes."
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
