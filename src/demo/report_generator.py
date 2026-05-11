"""Report generator for DueCare evaluation results.

Produces professional HTML reports suitable for:
  - Video demo screenshots
  - NGO/agency compliance documentation
  - Hackathon writeup evidence
  - Regulatory submissions

Usage:
    from src.demo.report_generator import generate_html_report

    report_html = generate_html_report(findings_data)
    Path("report.html").write_text(report_html)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def generate_html_report(
    findings: dict[str, Any],
    *,
    title: str = "DueCare Safety Evaluation Report",
) -> str:
    """Generate a professional HTML report from evaluation findings."""
    summary = findings.get("summary", {})
    model = findings.get("model", {})
    results = findings.get("results", [])
    n = summary.get("n_prompts", len(results))

    # Grade distribution
    grade_dist = summary.get("grade_distribution", {})
    grade_bars = ""
    for grade in ["best", "good", "neutral", "bad", "worst"]:
        count = grade_dist.get(grade, 0)
        pct = (count / n * 100) if n else 0
        colors = {"best": "#2dd4bf", "good": "#22c55e", "neutral": "#eab308", "bad": "#f97316", "worst": "#ef4444"}
        grade_bars += f"""
        <div style="display:flex;align-items:center;margin:4px 0;">
            <span style="width:70px;font-weight:bold;color:{colors.get(grade, '#888')}">{grade}</span>
            <div style="flex:1;background:#EFEDE4;border-radius:4px;overflow:hidden;height:24px;border:1px solid #DDD8C9;">
                <div style="width:{pct}%;background:{colors.get(grade, '#888')};height:100%;display:flex;align-items:center;padding-left:8px;color:#fff;font-size:12px;">
                    {count} ({pct:.0f}%)
                </div>
            </div>
        </div>"""

    # Per-prompt results table
    rows = ""
    for r in results[:50]:  # Cap at 50 for readability
        grade = r.get("grade", "?")
        score = r.get("score", 0)
        pid = r.get("id", "?")[:20]
        category = r.get("category", "?")[:25]
        grade_color = {"best": "#2dd4bf", "good": "#22c55e", "neutral": "#eab308", "bad": "#f97316", "worst": "#ef4444"}.get(grade, "#888")
        rows += f"""
        <tr>
            <td>{pid}</td>
            <td>{category}</td>
            <td style="text-align:center"><span style="background:{grade_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">{grade}</span></td>
            <td style="text-align:center">{score:.3f}</td>
            <td>{'Yes' if r.get('has_refusal') else 'No'}</td>
            <td>{'Yes' if r.get('has_legal_ref') else 'No'}</td>
        </tr>"""

    model_name = model.get("name", findings.get("model_id", "Unknown"))
    date = findings.get("evaluation_date", datetime.now().isoformat())[:10]

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #F7F6F1; color: #2A2D34; max-width: 1200px; margin: 0 auto; padding: 32px; line-height: 1.55; -webkit-font-smoothing: antialiased; }}
    h1 {{ color: #0E1116; border-bottom: 1px solid #DDD8C9; padding-bottom: 16px; font-weight: 600; letter-spacing: -0.022em; }}
    h2 {{ color: #5B5F68; margin-top: 32px; font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace; font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 24px 0; }}
    .metric {{ background: #F7F6F1; border: 1px solid #DDD8C9; border-radius: 12px; padding: 24px; text-align: center; }}
    .metric-value {{ font-size: 32px; font-weight: 600; color: #0E1116; letter-spacing: -0.022em; }}
    .metric-label {{ color: #5B5F68; font-size: 13px; margin-top: 4px; font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace; text-transform: uppercase; letter-spacing: 0.06em; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; background: #F7F6F1; border: 1px solid #DDD8C9; border-radius: 8px; overflow: hidden; }}
    th {{ background: #EFEDE4; color: #5B5F68; padding: 12px 14px; text-align: left; font-size: 11px; font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500; }}
    td {{ padding: 10px 14px; border-bottom: 1px solid #E8E4D7; font-size: 13.5px; color: #2A2D34; }}
    tr:hover td {{ background: #EFEDE4; }}
    .footer {{ margin-top: 56px; padding-top: 24px; border-top: 1px solid #DDD8C9; color: #5B5F68; font-size: 12.5px; }}
    .legal {{ background: oklch(0.94 0.04 45); border-left: 3px solid oklch(0.58 0.14 45); padding: 16px 18px; margin: 16px 0; border-radius: 0 8px 8px 0; color: oklch(0.32 0.10 45); }}
</style>
</head>
<body>
<h1>{title}</h1>

<div class="legal">
    <strong>Named for Cal. Civ. Code sect. 1714(a)</strong> — the duty of care standard.
    This evaluation ran entirely on-device; raw case data stays on the machine running the lab.
</div>

<h2>Model</h2>
<p><strong>{model_name}</strong> — evaluated on {date}</p>

<h2>Headline Metrics</h2>
<div class="metric-grid">
    <div class="metric">
        <div class="metric-value">{summary.get('mean_score', 0):.2f}</div>
        <div class="metric-label">Mean Score</div>
    </div>
    <div class="metric">
        <div class="metric-value">{summary.get('pass_rate', 0):.0%}</div>
        <div class="metric-label">Pass Rate</div>
    </div>
    <div class="metric">
        <div class="metric-value">{summary.get('refusal_rate', 0):.0%}</div>
        <div class="metric-label">Refusal Rate</div>
    </div>
    <div class="metric">
        <div class="metric-value">{n}</div>
        <div class="metric-label">Prompts Evaluated</div>
    </div>
</div>

<h2>Grade Distribution</h2>
{grade_bars}

<h2>Per-Prompt Results</h2>
<table>
<tr><th>ID</th><th>Category</th><th>Grade</th><th>Score</th><th>Refusal</th><th>Legal Ref</th></tr>
{rows}
</table>

<div class="footer">
    <p>Generated by <strong>DueCare</strong> — An agentic safety harness for LLM evaluation.</p>
    <p>Organizations: Polaris Project | International Justice Mission | POEA | IOM | ECPAT | BP2MI</p>
    <p>Raw case data stays on the machine running the lab.</p>
</div>
</body>
</html>"""
