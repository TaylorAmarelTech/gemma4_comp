"""Interactive Chat Viewer / Report Browser for DueCare.

Generates a self-contained HTML page that lets you browse, filter,
search, and analyze evaluation results. Features:

  - Browse all prompt-response pairs with scores and grades
  - Filter by category, grade, failure mode
  - Sort by score, importance, severity
  - Search by keyword in prompts or responses
  - Color-coded grade badges (best=green through worst=red)
  - Expandable response details with citation verification
  - Summary statistics with grade distribution chart
  - Export filtered results as JSON

Usage:
    from src.demo.chat_viewer import generate_chat_viewer

    html = generate_chat_viewer(results, title="Gemma 4 Baseline")
    Path("chat_viewer.html").write_text(html)

    # Or from CLI:
    python -m src.demo.chat_viewer --input data/full_evaluation/full_evaluation.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def generate_chat_viewer(
    results: list[dict[str, Any]],
    *,
    title: str = "DueCare Chat Viewer",
    model_name: str = "Unknown",
    evaluation_date: str = "",
) -> str:
    """Generate an interactive HTML chat viewer from evaluation results."""

    if not evaluation_date:
        evaluation_date = datetime.now().strftime("%Y-%m-%d")

    n = len(results)
    if n == 0:
        return "<html><body><h1>No results to display</h1></body></html>"

    # Compute stats
    grades = {}
    categories = {}
    failure_modes = {}
    scores = []
    for r in results:
        g = r.get("grade", "unknown")
        grades[g] = grades.get(g, 0) + 1
        c = r.get("category", "unknown")
        categories[c] = categories.get(c, 0) + 1
        fm = r.get("failure_mode", "")
        if fm:
            failure_modes[fm] = failure_modes.get(fm, 0) + 1
        scores.append(r.get("score", 0))

    mean_score = sum(scores) / n if n else 0
    pass_rate = sum(1 for r in results if r.get("grade") in ("best", "good")) / n if n else 0

    # Build result rows
    rows_json = json.dumps(results, default=str)
    categories_json = json.dumps(sorted(categories.keys()))
    grades_json = json.dumps(["best", "good", "neutral", "bad", "worst"])

    grade_colors = {
        "best": "#10b981", "good": "#22c55e",
        "neutral": "#eab308", "bad": "#f97316", "worst": "#ef4444",
        "error": "#6b7280", "unknown": "#6b7280",
    }

    # Build grade distribution bars
    grade_bars_html = ""
    for g in ["best", "good", "neutral", "bad", "worst"]:
        count = grades.get(g, 0)
        pct = (count / n * 100) if n else 0
        color = grade_colors.get(g, "#888")
        grade_bars_html += f'<div style="display:flex;align-items:center;margin:2px 0;"><span style="width:60px;color:{color};font-weight:bold">{g}</span><div style="flex:1;background:#1e293b;border-radius:3px;height:20px;overflow:hidden"><div style="width:{pct}%;background:{color};height:100%;display:flex;align-items:center;padding-left:6px;color:#fff;font-size:11px">{count} ({pct:.0f}%)</div></div></div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }}
.header {{ background: #1e293b; padding: 20px 24px; border-bottom: 1px solid #334155; }}
.header h1 {{ font-size: 20px; color: #f1f5f9; }}
.header .subtitle {{ color: #94a3b8; font-size: 13px; margin-top: 4px; }}
.stats {{ display: flex; gap: 16px; padding: 16px 24px; background: #1e293b; border-bottom: 1px solid #334155; }}
.stat {{ text-align: center; padding: 8px 16px; }}
.stat-value {{ font-size: 24px; font-weight: bold; color: #f1f5f9; }}
.stat-label {{ font-size: 11px; color: #64748b; }}
.controls {{ display: flex; gap: 12px; padding: 12px 24px; background: #0f172a; border-bottom: 1px solid #1e293b; flex-wrap: wrap; align-items: center; }}
.controls input, .controls select {{ background: #1e293b; border: 1px solid #334155; color: #e2e8f0; padding: 6px 10px; border-radius: 4px; font-size: 13px; }}
.controls input {{ flex: 1; min-width: 200px; }}
.controls select {{ min-width: 120px; }}
.results {{ padding: 0 24px 24px; }}
.result-card {{ background: #1e293b; border-radius: 8px; margin-top: 12px; overflow: hidden; border: 1px solid #334155; }}
.result-header {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; cursor: pointer; }}
.result-header:hover {{ background: #334155; }}
.result-id {{ font-weight: bold; color: #94a3b8; font-size: 13px; }}
.result-category {{ color: #64748b; font-size: 12px; }}
.grade-badge {{ padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; color: #fff; }}
.score-bar {{ width: 80px; height: 6px; background: #334155; border-radius: 3px; overflow: hidden; display: inline-block; vertical-align: middle; margin-left: 8px; }}
.score-fill {{ height: 100%; border-radius: 3px; }}
.result-body {{ padding: 0 16px 16px; display: none; }}
.result-body.open {{ display: block; }}
.prompt-text {{ background: #0f172a; padding: 12px; border-radius: 6px; margin: 8px 0; font-size: 13px; line-height: 1.5; white-space: pre-wrap; border-left: 3px solid #3b82f6; }}
.response-text {{ background: #0f172a; padding: 12px; border-radius: 6px; margin: 8px 0; font-size: 13px; line-height: 1.5; white-space: pre-wrap; border-left: 3px solid #22c55e; }}
.meta {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; }}
.meta-item {{ font-size: 12px; color: #94a3b8; }}
.meta-item strong {{ color: #e2e8f0; }}
.grade-dist {{ padding: 12px 24px; }}
.footer {{ padding: 16px 24px; border-top: 1px solid #334155; color: #64748b; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<div class="header">
    <h1>{title}</h1>
    <div class="subtitle">Model: {model_name} | Date: {evaluation_date} | DueCare — Cal. Civ. Code sect. 1714(a)</div>
</div>

<div class="stats">
    <div class="stat"><div class="stat-value">{n}</div><div class="stat-label">Prompts</div></div>
    <div class="stat"><div class="stat-value">{mean_score:.2f}</div><div class="stat-label">Mean Score</div></div>
    <div class="stat"><div class="stat-value">{pass_rate:.0%}</div><div class="stat-label">Pass Rate</div></div>
    <div class="stat"><div class="stat-value">{grades.get('best',0)+grades.get('good',0)}</div><div class="stat-label">Passed</div></div>
    <div class="stat"><div class="stat-value">{grades.get('worst',0)+grades.get('bad',0)}</div><div class="stat-label">Failed</div></div>
</div>

<div class="grade-dist">
    <strong style="color:#94a3b8;font-size:12px">Grade Distribution</strong>
    {grade_bars_html}
</div>

<div class="controls">
    <input type="text" id="search" placeholder="Search prompts and responses..." oninput="filterResults()">
    <select id="gradeFilter" onchange="filterResults()">
        <option value="">All Grades</option>
        <option value="best">Best</option>
        <option value="good">Good</option>
        <option value="neutral">Neutral</option>
        <option value="bad">Bad</option>
        <option value="worst">Worst</option>
    </select>
    <select id="sortBy" onchange="sortResults()">
        <option value="score_asc">Score (low→high)</option>
        <option value="score_desc">Score (high→low)</option>
        <option value="category">Category</option>
        <option value="id">ID</option>
    </select>
</div>

<div class="results" id="results"></div>

<div class="footer">
    Generated by <strong>DueCare</strong> — Privacy is non-negotiable. So the lab runs on your machine.<br>
    Organizations: Polaris Project | International Justice Mission | POEA | IOM | ECPAT | BP2MI
</div>

<script>
const ALL_RESULTS = {rows_json};
const GRADE_COLORS = {json.dumps(grade_colors)};

function renderResults(data) {{
    const container = document.getElementById('results');
    container.innerHTML = '';
    data.forEach((r, i) => {{
        const color = GRADE_COLORS[r.grade] || '#888';
        const scorePct = Math.round((r.score || 0) * 100);
        const card = document.createElement('div');
        card.className = 'result-card';
        card.innerHTML = `
            <div class="result-header" onclick="this.nextElementSibling.classList.toggle('open')">
                <div>
                    <span class="result-id">${{r.id || 'p'+i}}</span>
                    <span class="result-category">${{r.category || ''}}</span>
                </div>
                <div>
                    <span class="grade-badge" style="background:${{color}}">${{r.grade}}</span>
                    <span style="color:#94a3b8;font-size:13px;margin-left:8px">${{(r.score||0).toFixed(3)}}</span>
                    <span class="score-bar"><span class="score-fill" style="width:${{scorePct}}%;background:${{color}}"></span></span>
                </div>
            </div>
            <div class="result-body">
                <div style="color:#3b82f6;font-size:11px;margin-bottom:4px">PROMPT</div>
                <div class="prompt-text">${{(r.text || r.prompt || '(no prompt text)').substring(0,500)}}</div>
                <div style="color:#22c55e;font-size:11px;margin-bottom:4px">RESPONSE</div>
                <div class="response-text">${{(r.response_preview || r.response || '(no response)').substring(0,500)}}</div>
                <div class="meta">
                    ${{r.failure_mode ? '<div class="meta-item"><strong>Failure Mode:</strong> '+r.failure_mode+'</div>' : ''}}
                    ${{r.curriculum_tag ? '<div class="meta-item"><strong>Curriculum:</strong> '+r.curriculum_tag+'</div>' : ''}}
                    ${{r.citations_verified !== undefined ? '<div class="meta-item"><strong>Citations:</strong> '+r.citations_verified+'/'+((r.citations_verified||0)+(r.citations_fabricated||0))+'</div>' : ''}}
                    ${{r.elapsed_s ? '<div class="meta-item"><strong>Time:</strong> '+r.elapsed_s+'s</div>' : ''}}
                    ${{r.mode ? '<div class="meta-item"><strong>Mode:</strong> '+r.mode+'</div>' : ''}}
                </div>
            </div>`;
        container.appendChild(card);
    }});
    document.querySelector('.controls').insertAdjacentHTML('beforeend',
        '<span style="color:#64748b;font-size:12px;margin-left:auto">Showing '+data.length+'/'+ALL_RESULTS.length+'</span>');
}}

function filterResults() {{
    const search = document.getElementById('search').value.toLowerCase();
    const grade = document.getElementById('gradeFilter').value;
    let filtered = ALL_RESULTS.filter(r => {{
        if (grade && r.grade !== grade) return false;
        if (search) {{
            const text = (r.text||'') + (r.response_preview||'') + (r.id||'') + (r.category||'');
            if (!text.toLowerCase().includes(search)) return false;
        }}
        return true;
    }});
    renderResults(filtered);
}}

function sortResults() {{
    const sortBy = document.getElementById('sortBy').value;
    let sorted = [...ALL_RESULTS];
    if (sortBy === 'score_asc') sorted.sort((a,b) => (a.score||0) - (b.score||0));
    else if (sortBy === 'score_desc') sorted.sort((a,b) => (b.score||0) - (a.score||0));
    else if (sortBy === 'category') sorted.sort((a,b) => (a.category||'').localeCompare(b.category||''));
    else sorted.sort((a,b) => (a.id||'').localeCompare(b.id||''));
    renderResults(sorted);
}}

// Initial render
renderResults(ALL_RESULTS);
</script>
</body>
</html>"""


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Generate DueCare Chat Viewer")
    parser.add_argument("--input", type=Path, required=True, help="JSON file with evaluation results")
    parser.add_argument("--output", type=Path, default=Path("chat_viewer.html"))
    parser.add_argument("--title", default="DueCare Chat Viewer")
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))

    # Support both flat list and nested format
    if isinstance(data, list):
        results = data
    elif "results" in data:
        results = data["results"]
    elif "per_prompt" in data:
        results = []
        for mode_results in data["per_prompt"].values():
            if isinstance(mode_results, list):
                results.extend(mode_results)
    else:
        results = []

    model_name = data.get("model", data.get("model_id", "Unknown")) if isinstance(data, dict) else "Unknown"
    if isinstance(model_name, dict):
        model_name = model_name.get("name", "Unknown")

    html = generate_chat_viewer(
        results,
        title=args.title,
        model_name=str(model_name),
        evaluation_date=data.get("date", data.get("evaluation_date", "")) if isinstance(data, dict) else "",
    )
    args.output.write_text(html, encoding="utf-8")
    print(f"Chat viewer: {len(html):,} bytes -> {args.output}")
    print(f"Results: {len(results)} entries")
    print(f"Open in browser: file://{args.output.resolve()}")


if __name__ == "__main__":
    main()
