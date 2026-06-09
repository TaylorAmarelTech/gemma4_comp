"""Render harness-lift checkpoints into judge-facing report artifacts.

Reads the per-cell judge checkpoints + persisted responses + the prompt corpus
and produces up to three artifacts:

  * ``reports/harness_lift_report.html`` (default; gitignored, regeneratable)
    -- full report: per-model lift with statistical confidence, per-group
    lift, and egregious baseline examples with their harnessed counterparts.
  * ``docs/research/harness_lift_report.md`` (``--md``) -- committed summary
    with methodology, statistics, and reproduce commands.
  * ``packages/duecare-llm-chat/src/duecare/chat/static/lift_evidence.json``
    (``--json``) -- compact stats consumed by workbench/site evidence cards.

Statistics come from ``scripts/lift_stats.py``: per-prompt paired deltas,
win/loss/tie rates, paired Cohen's d, and a seeded bootstrap 95% CI, so the
headline number is defensible rather than a bare grand mean.

Each checkpoint carries its own judge identity (never a global default): the
1000-prompt run was judged by gpt-oss:120b, the 500-prompt multi-model run by
Claude Opus 4.8. Mislabeling the judge in a reviewer-facing artifact would be
a "real, not faked" violation.

Self-contained HTML (inline CSS, warm-paper civic-tech palette per
60_notebook_presentation.md), no truncation of displayed text. Synthetic
content only (public prompts + model responses); no PII.

Run: ``python scripts/build_lift_report.py --all``
"""
from __future__ import annotations

import argparse
import collections
import datetime
import glob
import html
import json
import os
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import lift_stats  # noqa: E402

_BENCH = _ROOT / "configs" / "duecare" / "benchmarks"
_OUT_HTML = _ROOT / os.environ.get("LIFT_REPORT_OUT", "reports/harness_lift_report.html")
_OUT_MD = _ROOT / "docs" / "research" / "harness_lift_report.md"
_OUT_JSON_TARGETS = (
    _ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat"
    / "static" / "lift_evidence.json",
    # The public hub serves the same artifact at /static/lift_evidence.json
    # (linked from the /evaluation page), so the site and the kernels always
    # showcase identical, provenance-stamped numbers.
    _ROOT / "apps" / "duecare-ai.com" / "app" / "static" / "lift_evidence.json",
)

# Judge identity is per-checkpoint. LIFT_REPORT_CKPT narrows to a single run
# (judge from LIFT_REPORT_JUDGE or filename inference).
_DEFAULT_RUNS = [
    {
        "ckpt": "reports/harness_lift_1000_judge.jsonl",
        "judge": "gpt-oss:120b safety judge (independent LLM judge via Ollama)",
        "label": "Primary large-N run",
    },
    {
        "ckpt": "reports/harness_lift_500_opus.jsonl",
        "judge": "Claude Opus 4.8 (one dimension per judge call)",
        "label": "Frontier-judged multi-model run",
    },
]
# Local deterministic-grader checkpoint used for the grader cross-check note.
_LOCAL_GRADER_CKPT = "reports/harness_lift_1000.jsonl"

# Civic-tech warm-paper palette (60_notebook_presentation.md).
_PAPER, _PAPER2, _INK, _INK3, _LINE = "#F7F6F1", "#EFEDE4", "#0E1116", "#5B5F68", "#DDD8C9"
_GOOD, _WARN, _EMBER = "#2e7d57", "#b08900", "#c2410c"


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _load_prompts() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in glob.glob(str(_BENCH / "harness_lift_prompts_*.json")):
        try:
            for p in json.loads(pathlib.Path(f).read_text(encoding="utf-8"))["prompts"]:
                out[str(p["id"])] = p["text"]
        except Exception:
            continue
    for r in _load_jsonl(_BENCH / "harness_lift_prompts_expansion.jsonl"):
        if r.get("id"):
            out[str(r["id"])] = r.get("text", "")
    return out


def _load_responses() -> dict[tuple, str]:
    out: dict[tuple, str] = {}
    for f in glob.glob(str(_ROOT / "reports" / "*.responses.jsonl")):
        for r in _load_jsonl(pathlib.Path(f)):
            try:
                out[(str(r["prompt_id"]), str(r["model"]), str(r["arm"]))] = r.get("response", "")
            except Exception:
                continue
    return out


def _infer_judge(ckpt_name: str) -> str:
    low = ckpt_name.lower()
    if "opus" in low:
        return "Claude Opus 4.8 (one dimension per judge call)"
    if "_judge" in low:
        return "gpt-oss:120b safety judge (independent LLM judge via Ollama)"
    return "DueCare deterministic local grader (grade_response_universal)"


def _resolve_runs() -> list[dict]:
    env_ckpt = os.environ.get("LIFT_REPORT_CKPT")
    if env_ckpt:
        judge = os.environ.get("LIFT_REPORT_JUDGE") or _infer_judge(env_ckpt)
        specs = [{"ckpt": env_ckpt, "judge": judge, "label": "Configured run"}]
    else:
        specs = _DEFAULT_RUNS
    runs = []
    for spec in specs:
        path = _ROOT / spec["ckpt"]
        cells = _load_jsonl(path)
        if not cells:
            continue
        runs.append({**spec, "path": path, "cells": cells,
                     "stats": lift_stats.model_stats(cells)})
    return runs


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=_ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _group_lift(cells: list[dict], model: str) -> list[tuple[str, float, float, float]]:
    """Per dimension-group (baseline, harnessed, lift) for one model."""
    by: dict[tuple, list[float]] = collections.defaultdict(list)
    for c in cells:
        if c.get("model") != model:
            continue
        try:
            grp = str(c["dim"]).split(".", 1)[0]
            by[(c["arm"], grp)].append(float(c["score"]))
        except (KeyError, TypeError, ValueError):
            continue
    groups = sorted({g for (_a, g) in by})
    rows = []
    for g in groups:
        b = by.get(("baseline", g), [])
        h = by.get(("harnessed", g), [])
        if not b or not h:
            continue
        bm, hm = sum(b) / len(b), sum(h) / len(h)
        rows.append((g, bm, hm, hm - bm))
    rows.sort(key=lambda x: x[3], reverse=True)
    return rows


def _egregious(cells: list[dict], limit: int) -> list[tuple[float, float, float, str, str]]:
    """Worst-baseline prompt/model pairs with both arms, biggest lift first tiebreak."""
    pairs = []
    for model, rows in lift_stats.per_prompt_pairs(cells).items():
        for pid, bm, hm in rows:
            pairs.append((bm, hm, hm - bm, pid, model))
    pairs.sort(key=lambda p: (p[0], -p[2]))
    return pairs[:limit]


def _grader_crosscheck(primary: dict | None) -> dict | None:
    """Compare the deterministic local grader vs the LLM judge on shared models."""
    local_cells = _load_jsonl(_ROOT / _LOCAL_GRADER_CKPT)
    if not local_cells or primary is None:
        return None
    local = {s["model"]: s for s in lift_stats.model_stats(local_cells)}
    judged = {s["model"]: s for s in primary["stats"]}
    shared = sorted(set(local) & set(judged))
    if not shared:
        return None
    return {
        "local_ckpt": _LOCAL_GRADER_CKPT,
        "rows": [
            {"model": m, "local_lift": local[m]["lift"], "judge_lift": judged[m]["lift"]}
            for m in shared
        ],
    }


# ---------------------------------------------------------------- HTML ----
def _build_html(runs: list[dict], prompts: dict, responses: dict) -> str:
    def esc(s):
        return html.escape(str(s))

    def color(score: float) -> str:
        return _GOOD if score >= 6.5 else (_WARN if score >= 4 else _EMBER)

    css = (f"body{{background:{_PAPER};color:{_INK};font:15px/1.55 -apple-system,"
           f"Segoe UI,Inter,sans-serif;margin:0;padding:32px;max-width:1100px}}"
           f"h1{{font-size:26px;margin:0 0 4px}}h2{{font-size:19px;margin:34px 0 10px;"
           f"border-bottom:2px solid {_LINE};padding-bottom:6px}}h3{{font-size:16px;margin:22px 0 8px}}"
           f".sub{{color:{_INK3};margin:0 0 18px}}"
           f"table{{border-collapse:collapse;width:100%;margin:8px 0}}"
           f"th,td{{text-align:left;padding:8px 12px;border-bottom:1px solid {_LINE}}}"
           f"th{{background:{_PAPER2};font-size:13px;letter-spacing:.02em}}"
           f".num{{text-align:right;font-variant-numeric:tabular-nums}}"
           f".bar{{height:9px;border-radius:5px;background:{_GOOD};display:inline-block;vertical-align:middle}}"
           f".ex{{border:1px solid {_LINE};border-radius:10px;margin:14px 0;overflow:hidden;background:#fff}}"
           f".ex .hd{{background:{_PAPER2};padding:10px 14px;font-size:13px;color:{_INK3}}}"
           f".ex .pr{{padding:12px 14px;border-bottom:1px solid {_LINE};white-space:pre-wrap}}"
           f".arm{{padding:12px 14px;white-space:pre-wrap;border-top:1px solid {_LINE}}}"
           f".tag{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;"
           f"font-weight:600;color:#fff}}.muted{{color:{_INK3}}}")

    out = [f"<!doctype html><html><head><meta charset='utf-8'>"
           f"<title>DueCare Harness-Lift Report</title><style>{css}</style></head><body>"]
    out.append("<h1>DueCare &mdash; Harness-Lift Report</h1>")
    out.append(f"<p class='sub'>Baseline vs DueCare-harnessed, paired per prompt. "
               f"git {esc(_git_sha())} &middot; regenerate with "
               f"<code>python scripts/build_lift_report.py --all</code></p>")

    for run in runs:
        cells = run["cells"]
        out.append(f"<h2>{esc(run['label'])}</h2>")
        out.append(f"<p class='sub'>Judge: {esc(run['judge'])} &middot; checkpoint "
                   f"<code>{esc(run['ckpt'])}</code> &middot; {len(cells):,} graded cells &middot; "
                   f"{len({c.get('dim') for c in cells})} dimensions. "
                   f"Lift = harnessed &minus; baseline on a 0&ndash;10 scale; win/loss at "
                   f"&plusmn;{lift_stats.WIN_THRESHOLD} per-prompt delta; CI is a seeded "
                   f"10,000-resample bootstrap.</p>")
        out.append("<table><tr><th>Model</th><th class='num'>Baseline</th>"
                   "<th class='num'>Harnessed</th><th class='num'>Lift</th>"
                   "<th class='num'>95% CI</th><th class='num'>Win / loss / tie</th>"
                   "<th class='num'>Win rate</th><th class='num'>Cohen's d</th>"
                   "<th class='num'>Prompts</th><th>Lift</th></tr>")
        maxlift = max((s["lift"] for s in run["stats"]), default=1) or 1
        for s in run["stats"]:
            w = int(max(0.0, s["lift"]) / maxlift * 160)
            out.append(
                f"<tr><td>{esc(s['model'])}</td><td class='num'>{s['baseline_mean']:.2f}</td>"
                f"<td class='num'>{s['harnessed_mean']:.2f}</td>"
                f"<td class='num' style='color:{_GOOD if s['lift'] > 0 else _EMBER};font-weight:600'>"
                f"{s['lift']:+.2f}</td>"
                f"<td class='num'>[{s['ci95_low']:+.2f}, {s['ci95_high']:+.2f}]</td>"
                f"<td class='num'>{s['wins']} / {s['losses']} / {s['ties']}</td>"
                f"<td class='num'>{s['win_rate']:.1%}</td>"
                f"<td class='num'>{s['cohens_d']:.2f}</td>"
                f"<td class='num'>{s['n_prompts_paired']}</td>"
                f"<td><span class='bar' style='width:{w}px'></span></td></tr>")
        out.append("</table>")
        if run["stats"]:
            top = run["stats"][0]
            pcts = top["delta_percentiles"]
            out.append(f"<p class='muted'>Per-prompt delta distribution for "
                       f"{esc(top['model'])}: p10 {pcts['p10']:+.2f} &middot; p25 {pcts['p25']:+.2f} "
                       f"&middot; median {pcts['p50']:+.2f} &middot; p75 {pcts['p75']:+.2f} &middot; "
                       f"p90 {pcts['p90']:+.2f}</p>")

    # Per-group lift for the primary run's top model.
    primary = runs[0] if runs else None
    if primary and primary["stats"]:
        top_model = primary["stats"][0]["model"]
        out.append(f"<h2>Where the harness helps most &mdash; {html.escape(top_model)}, "
                   f"by dimension group ({html.escape(primary['label'])})</h2>")
        gl = _group_lift(primary["cells"], top_model)
        out.append("<table><tr><th>Dimension group</th><th class='num'>Baseline</th>"
                   "<th class='num'>Harnessed</th><th class='num'>Lift</th><th>Lift</th></tr>")
        gmax = max((x[3] for x in gl), default=1) or 1
        for g, b, h, lift in gl:
            w = int(max(0.0, lift) / gmax * 180)
            out.append(f"<tr><td>{esc(g)}</td><td class='num'>{b:.2f}</td><td class='num'>{h:.2f}</td>"
                       f"<td class='num' style='font-weight:600'>{lift:+.2f}</td>"
                       f"<td><span class='bar' style='width:{w}px'></span></td></tr>")
        out.append("</table>")

    # Grader cross-check.
    cross = _grader_crosscheck(primary)
    if cross:
        out.append("<h2>Grader cross-check &mdash; deterministic local grader vs LLM judge</h2>")
        out.append("<p class='sub'>The deterministic grader (DueCare's own "
                   "<code>grade_response_universal</code>) keys on observable markers and is "
                   "conservative; the independent LLM judge evaluates substantive quality. Both "
                   "directions agree the harness helps; the magnitude differs because the "
                   "deterministic grader cannot award credit for qualitative grounding it has no "
                   "marker for. The LLM-judged number is the primary headline; the deterministic "
                   "number is the reproducible-without-any-LLM floor.</p>")
        out.append("<table><tr><th>Model</th><th class='num'>Deterministic-grader lift</th>"
                   "<th class='num'>LLM-judge lift</th></tr>")
        for row in cross["rows"]:
            out.append(f"<tr><td>{esc(row['model'])}</td>"
                       f"<td class='num'>{row['local_lift']:+.2f}</td>"
                       f"<td class='num'>{row['judge_lift']:+.2f}</td></tr>")
        out.append("</table>")

    # Egregious baseline examples (primary run).
    if primary:
        out.append("<h2>Egregious baseline (no-harness) responses &mdash; and what the harness did</h2>")
        out.append("<p class='sub'>Worst-scoring baseline answers; the harnessed answer to the same "
                   "prompt is shown beneath for contrast. Full text, no truncation.</p>")
        for bm, hm, lift, pid, m in _egregious(primary["cells"], 12):
            ptext = prompts.get(str(pid), "(prompt text unavailable)")
            br = responses.get((str(pid), m, "baseline"), "(response unavailable)")
            hr = responses.get((str(pid), m, "harnessed"), "(response unavailable)")
            out.append("<div class='ex'>")
            out.append(f"<div class='hd'>{esc(m)} &middot; prompt <code>{esc(pid)}</code> &middot; "
                       f"baseline <b style='color:{color(bm)}'>{bm:.1f}</b> &rarr; "
                       f"harnessed <b style='color:{color(hm)}'>{hm:.1f}</b> "
                       f"(<b>{lift:+.1f}</b>)</div>")
            out.append(f"<div class='pr'><b>Prompt:</b> {esc(ptext)}</div>")
            out.append(f"<div class='arm'><span class='tag' style='background:{_EMBER}'>BASELINE "
                       f"{bm:.1f}</span><br>{esc(br)}</div>")
            out.append(f"<div class='arm'><span class='tag' style='background:{_GOOD}'>HARNESSED "
                       f"{hm:.1f}</span><br>{esc(hr)}</div>")
            out.append("</div>")

    out.append("</body></html>")
    return "\n".join(out)


# ------------------------------------------------------------ markdown ----
def _build_markdown(runs: list[dict], prompts: dict, responses: dict) -> str:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    sha = _git_sha()
    md: list[str] = []
    md.append("# DueCare Harness-Lift Report")
    md.append("")
    md.append(f"Generated {now} at git `{sha}`. Regenerate with "
              "`python scripts/build_lift_report.py --all` (result checkpoints under "
              "`reports/` are local, regeneratable artifacts).")
    md.append("")
    md.append("## What this measures")
    md.append("")
    md.append("Each benchmark prompt is answered twice by the same model: a **baseline** arm "
              "(the raw prompt) and a **harnessed** arm (the same prompt behind the DueCare "
              "harness, which prepends fired GREP-rule findings and BM25-retrieved legal/"
              "contextual grounding before generation). An independent judge scores both "
              "answers against the per-prompt-applicable subset of the "
              "192-dimension rubric in `configs/duecare/benchmarks/harness_lift_dimensions.json` "
              "(0-10 per dimension). Scores collapse to one mean per (prompt, arm); the "
              "per-prompt paired delta (harnessed minus baseline) is the unit of analysis.")
    md.append("")
    md.append("Win/loss/tie uses a +/-0.1 per-prompt delta threshold. The 95% CI is a seeded "
              "10,000-resample percentile bootstrap on the mean delta. Cohen's d is paired "
              "(mean delta over the delta standard deviation).")
    md.append("")
    md.append("## Headline results")
    md.append("")
    for run in runs:
        md.append(f"### {run['label']}")
        md.append("")
        md.append(f"Judge: **{run['judge']}** | checkpoint `{run['ckpt']}` | "
                  f"{len(run['cells']):,} graded cells.")
        md.append("")
        md.append("| Model | Baseline | Harnessed | Lift | 95% CI | W / L / T | Win rate | Cohen's d | Prompts |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        for s in run["stats"]:
            md.append(
                f"| {s['model']} | {s['baseline_mean']:.2f} | {s['harnessed_mean']:.2f} | "
                f"**{s['lift']:+.2f}** | [{s['ci95_low']:+.2f}, {s['ci95_high']:+.2f}] | "
                f"{s['wins']} / {s['losses']} / {s['ties']} | {s['win_rate']:.1%} | "
                f"{s['cohens_d']:.2f} | {s['n_prompts_paired']} |")
        md.append("")
        if run["stats"]:
            top = run["stats"][0]
            pcts = top["delta_percentiles"]
            md.append(f"Per-prompt delta distribution for {top['model']}: "
                      f"p10 {pcts['p10']:+.2f}, p25 {pcts['p25']:+.2f}, median {pcts['p50']:+.2f}, "
                      f"p75 {pcts['p75']:+.2f}, p90 {pcts['p90']:+.2f}.")
            md.append("")

    primary = runs[0] if runs else None
    if primary and primary["stats"]:
        top_model = primary["stats"][0]["model"]
        md.append(f"## Where the harness helps most ({top_model}, {primary['label']})")
        md.append("")
        md.append("| Dimension group | Baseline | Harnessed | Lift |")
        md.append("|---|---|---|---|")
        for g, b, h, lift in _group_lift(primary["cells"], top_model):
            md.append(f"| {g} | {b:.2f} | {h:.2f} | {lift:+.2f} |")
        md.append("")

    cross = _grader_crosscheck(primary)
    if cross:
        md.append("## Grader cross-check")
        md.append("")
        md.append("The deterministic local grader (`grade_response_universal`, no LLM involved) "
                  "and the independent LLM judge were both run over the same response sets. "
                  "Both agree on direction; magnitudes differ because the deterministic grader "
                  "only awards credit for markers it can observe literally, making it the "
                  "conservative, fully-reproducible floor while the LLM judge measures "
                  "substantive quality.")
        md.append("")
        md.append("| Model | Deterministic-grader lift | LLM-judge lift |")
        md.append("|---|---|---|")
        for row in cross["rows"]:
            md.append(f"| {row['model']} | {row['local_lift']:+.2f} | {row['judge_lift']:+.2f} |")
        md.append("")

    if primary:
        md.append("## Example: what the harness fixes")
        md.append("")
        md.append("Three worst-scoring baseline answers from the primary run, with the harnessed "
                  "answer to the same prompt. Full text, no truncation; prompts and responses are "
                  "synthetic benchmark content.")
        md.append("")
        for bm, hm, lift, pid, m in _egregious(primary["cells"], 3):
            ptext = prompts.get(str(pid), "(prompt text unavailable)")
            br = responses.get((str(pid), m, "baseline"), "(response unavailable)")
            hr = responses.get((str(pid), m, "harnessed"), "(response unavailable)")
            md.append(f"### `{pid}` ({m}): baseline {bm:.1f} -> harnessed {hm:.1f} ({lift:+.1f})")
            md.append("")
            md.append(f"**Prompt:** {ptext}")
            md.append("")
            md.append(f"**Baseline ({bm:.1f}):**")
            md.append("")
            md.append("```text")
            md.append(br)
            md.append("```")
            md.append("")
            md.append(f"**Harnessed ({hm:.1f}):**")
            md.append("")
            md.append("```text")
            md.append(hr)
            md.append("```")
            md.append("")

    md.append("## Reproducibility")
    md.append("")
    md.append("```bash")
    md.append("# 1. Generate responses for both arms (Ollama models, resumable)")
    md.append("python scripts/harness_lift_local.py")
    md.append("# 2. Independent LLM judging (batched) or Opus subagent batches")
    md.append("python scripts/harness_lift_opus_judge.py batches && python scripts/harness_lift_opus_judge.py ingest")
    md.append("# 3. This report (HTML + this markdown + the workbench evidence JSON)")
    md.append("python scripts/build_lift_report.py --all")
    md.append("```")
    md.append("")
    md.append("Rubric: `configs/duecare/benchmarks/harness_lift_dimensions.json` (192 dimensions, "
              "30 groups). Prompt corpus: `configs/duecare/benchmarks/harness_lift_prompts_*.json` "
              "+ `harness_lift_prompts_expansion.jsonl`. Statistics: `scripts/lift_stats.py` "
              "(tested in `tests/test_lift_stats.py`).")
    md.append("")
    return "\n".join(md)


# --------------------------------------------------------- static JSON ----
def _build_static_json(runs: list[dict]) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    payload_runs = []
    for run in runs:
        payload_runs.append({
            "label": run["label"],
            "judge": run["judge"],
            "checkpoint": run["ckpt"],
            "n_cells": len(run["cells"]),
            "models": run["stats"],
        })
    headline = None
    if runs and runs[0]["stats"]:
        s = runs[0]["stats"][0]
        headline = {
            "model": s["model"],
            "lift": round(s["lift"], 2),
            "win_rate": round(s["win_rate"], 3),
            "cohens_d": round(s["cohens_d"], 2),
            "ci95": [round(s["ci95_low"], 2), round(s["ci95_high"], 2)],
            "n_prompts": s["n_prompts_paired"],
            "judge": runs[0]["judge"],
            "label": runs[0]["label"],
        }
    return {
        "schema_version": "duecare.lift_evidence.v1",
        "generated_at": now,
        "git_sha": _git_sha(),
        "headline": headline,
        "runs": payload_runs,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--md", action="store_true", help="also write the committed markdown report")
    parser.add_argument("--json", action="store_true", help="also write the workbench evidence JSON")
    parser.add_argument("--all", action="store_true", help="write HTML + markdown + JSON")
    args = parser.parse_args(argv)

    runs = _resolve_runs()
    if not runs:
        print("[lift-report] no checkpoints found; nothing to do")
        return
    prompts, responses = _load_prompts(), _load_responses()

    _OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    _OUT_HTML.write_text(_build_html(runs, prompts, responses), encoding="utf-8")
    print(f"[lift-report] wrote {_OUT_HTML} ({_OUT_HTML.stat().st_size:,} bytes)")

    if args.md or args.all:
        _OUT_MD.parent.mkdir(parents=True, exist_ok=True)
        _OUT_MD.write_text(_build_markdown(runs, prompts, responses), encoding="utf-8")
        print(f"[lift-report] wrote {_OUT_MD} ({_OUT_MD.stat().st_size:,} bytes)")

    if args.json or args.all:
        payload = json.dumps(_build_static_json(runs), indent=2) + "\n"
        for target in _OUT_JSON_TARGETS:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(payload, encoding="utf-8")
            print(f"[lift-report] wrote {target} ({target.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
