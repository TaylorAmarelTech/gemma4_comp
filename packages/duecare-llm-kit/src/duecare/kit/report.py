# ruff: noqa: E501
"""DueCare harness-lift HTML report generator -- turn a graded panel into a shareable, offline page.

``generate_report`` reads the accumulated benchmark panel (a DataFrame, a ``panel.jsonl``, or a
``panel_grades.csv``), computes the paired baseline->harness lift exactly the way
``scripts/analyze_full_results.py`` does (mean over judges per (model, prompt_id, arm), then pair
baseline vs harness_core per prompt), and renders a SELF-CONTAINED, DueCare-styled standalone HTML
file: a hero with the headline lift / win rate / n, a cross-model board, a per-dimension (A-E) section,
and several charts rendered with :mod:`duecare.kit.viz` and embedded as base64 PNG data-URIs so the
page opens offline with no external assets.

    >>> from duecare.kit.report import generate_report
    >>> generate_report("reports/rich_lift/panel.jsonl", "duecare_report.html")

CLI:  python -m duecare.kit.report --panel reports/rich_lift/panel.jsonl --out duecare_report.html

ASCII-only.
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import json
import math
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from . import viz

_ARMS = ("baseline", "harness_core", "harness_full")
_DIM_LABELS = {
    "A": "A indicator",
    "B": "B law",
    "C": "C refuses",
    "D": "D resources",
    "E": "E privacy/safety",
}


# --------------------------------------------------------------------------- loading


def _num(value: Any) -> float | None:
    """Coerce to a finite float or return None (handles numpy scalars, strings, NaN)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Normalize a DataFrame into panel records with a nested ``components`` dict."""
    comp_cols = [c for c in ("A", "B", "C", "D", "E") if c in df.columns]
    records: list[dict] = []
    for row in df.to_dict("records"):
        comps = row.get("components")
        if isinstance(comps, str):
            try:
                comps = json.loads(comps)
            except (TypeError, ValueError):
                comps = None
        if not isinstance(comps, dict):
            comps = {k: row[k] for k in comp_cols if pd.notna(row.get(k))} if comp_cols else {}
        records.append({
            "model": row.get("model"),
            "arm": row.get("arm"),
            "prompt_id": row.get("prompt_id"),
            "judge": row.get("judge"),
            "score_0_100": row.get("score_0_100"),
            "components": comps,
        })
    return records


def _read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def load_records(panel: pd.DataFrame | str | Path) -> list[dict]:
    """Load panel records from a DataFrame, a .jsonl / .ndjson, a .json, or a .csv path."""
    if isinstance(panel, pd.DataFrame):
        return _df_to_records(panel)
    path = Path(panel)
    if not path.exists():
        raise FileNotFoundError(f"panel not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _df_to_records(pd.read_csv(path))
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else (data.get("rows") or data.get("panel") or [])
        return list(rows)
    # default: JSON lines (panel.jsonl / panel_grades.jsonl / .ndjson)
    return _read_jsonl(path)


# --------------------------------------------------------------------------- aggregation


def aggregate(records: list[dict]) -> dict:
    """Pure aggregation: mean over judges per (model, prompt_id, arm), then paired baseline->core lift.

    Returns ``{"per_model": [...], "n_rows": int, "n_models": int}``. Mirrors
    ``scripts/analyze_full_results.py`` so headline numbers match the canonical report.
    """
    sc: dict = {}
    comp: dict = {}
    for r in records:
        m, a, pid = r.get("model"), r.get("arm"), r.get("prompt_id")
        s = _num(r.get("score_0_100"))
        if not (m and a and pid) or s is None:
            continue
        sc.setdefault((m, pid, a), []).append(s)
        comps = r.get("components") or {}
        if isinstance(comps, dict):
            for k, v in comps.items():
                fv = _num(v)
                if fv is not None:
                    comp.setdefault((m, pid, a, k), []).append(fv)
    mean = {k: statistics.fmean(v) for k, v in sc.items()}
    comp_mean = {k: statistics.fmean(v) for k, v in comp.items()}

    per_model = []
    for mdl in sorted({k[0] for k in mean}):
        pids = {k[1] for k in mean if k[0] == mdl}
        bc_pids = sorted(p for p in pids
                         if (mdl, p, "baseline") in mean and (mdl, p, "harness_core") in mean)
        if not bc_pids:
            continue
        bc = [(mean[(mdl, p, "baseline")], mean[(mdl, p, "harness_core")]) for p in bc_pids]
        d = [c - b for b, c in bc]
        wins = sum(1 for x in d if x > 0)
        losses = sum(1 for x in d if x < 0)
        ties = sum(1 for x in d if x == 0)
        bf_pids = sorted(p for p in pids
                         if (mdl, p, "baseline") in mean and (mdl, p, "harness_full") in mean)
        bf = [(mean[(mdl, p, "baseline")], mean[(mdl, p, "harness_full")]) for p in bf_pids]
        comp_keys = sorted({k[3] for k in comp_mean if k[0] == mdl})
        component_baseline: dict = {}
        component_core: dict = {}
        component_lift: dict = {}
        for key in comp_keys:
            cp = [p for p in bc_pids
                  if (mdl, p, "baseline", key) in comp_mean and (mdl, p, "harness_core", key) in comp_mean]
            if cp:
                component_baseline[key] = round(statistics.fmean(comp_mean[(mdl, p, "baseline", key)] for p in cp), 2)
                component_core[key] = round(statistics.fmean(comp_mean[(mdl, p, "harness_core", key)] for p in cp), 2)
                component_lift[key] = round(component_core[key] - component_baseline[key], 2)
        per_model.append({
            "model": mdl,
            "n_pair": len(bc),
            "n_full_pair": len(bf),
            "baseline": round(statistics.fmean(b for b, c in bc), 1),
            "core": round(statistics.fmean(c for b, c in bc), 1),
            "full": round(statistics.fmean(f for b, f in bf), 1) if bf else None,
            "lift_core": round(statistics.fmean(d), 1),
            "lift_full": round(statistics.fmean(f - b for b, f in bf), 1) if bf else None,
            "helps": wins,
            "hurts": losses,
            "ties": ties,
            "win_rate": round(wins / (wins + losses), 4) if (wins + losses) else None,
            "baseline_scores": [round(b, 2) for b, c in bc],
            "core_scores": [round(c, 2) for b, c in bc],
            "component_baseline": component_baseline,
            "component_core": component_core,
            "component_lift": component_lift,
        })
    per_model.sort(key=lambda r: -r["n_pair"])
    return {"per_model": per_model, "n_rows": len(records), "n_models": len(per_model)}


def _pick_headline(agg: dict, model: str) -> dict | None:
    per_model = agg["per_model"]
    if not per_model:
        return None
    return next((r for r in per_model if r["model"] == model), per_model[0])


# --------------------------------------------------------------------------- rendering


def _fig_to_data_uri(fig) -> str:
    """Render a matplotlib Figure to a base64 PNG data-URI, then close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _img(uri: str, alt: str) -> str:
    return f'<img class="chart" src="{uri}" alt="{html.escape(alt)}" />'


def _build_charts(agg: dict, head: dict) -> dict[str, str]:
    """Build the embedded chart data-URIs. Returns a name -> <img> HTML mapping."""
    charts: dict[str, str] = {}
    board = agg["per_model"]

    # 1. Headline KPI tiles.
    lift = head["lift_core"]
    wr = head["win_rate"]
    cards = [
        (f"+{lift}", "core lift (0-100)", viz.EMBER),
        (f"{wr * 100:.1f}%" if wr is not None else "n/a", "win rate", viz.TEAL),
        (f"{head['n_pair']:,}", "paired prompts", viz.INK2),
        (f"{head['baseline']}", "baseline mean", viz.INK3),
        (f"{head['core']}", "harness core mean", viz.GOOD),
    ]
    charts["kpis"] = _img(_fig_to_data_uri(viz.stat_cards(cards, show=False)),
                          "headline KPI tiles")

    # 2. Cross-model dumbbell (baseline -> core).
    if board:
        labels = [r["model"] for r in board]
        lo = [r["baseline"] for r in board]
        hi = [r["core"] for r in board]
        fig = viz.dumbbell(labels, lo, hi, title="Cross-model paired lift (baseline -> harness core)",
                           subtitle="mean rubric score 0-100; delta labeled", xlabel="mean rubric score (0-100)",
                           xlim=(0, 106), show=False)
        charts["board"] = _img(_fig_to_data_uri(fig), "cross-model baseline to core dumbbell")

    # 3. Per-dimension radar (A-E baseline vs core) for the headline model.
    dims = [k for k in ("A", "B", "C", "D", "E") if k in head["component_core"]]
    if dims:
        labels = [_DIM_LABELS.get(k, k) for k in dims]
        base_vals = [head["component_baseline"][k] for k in dims]
        core_vals = [head["component_core"][k] for k in dims]
        rmax = math.ceil(max(base_vals + core_vals) / 5.0) * 5 or None
        fig = viz.radar(labels, [("baseline", base_vals, viz.INK3), ("harness core", core_vals, viz.TEAL)],
                        title=f"Per-dimension mean ({head['model']})",
                        subtitle="rubric components A-E; baseline vs harness core", rmax=rmax, show=False)
        charts["radar"] = _img(_fig_to_data_uri(fig), "per-dimension radar")

    # 4. Score distributions (baseline vs core) for the headline model.
    if head["baseline_scores"] and head["core_scores"]:
        bmean = statistics.fmean(head["baseline_scores"])
        cmean = statistics.fmean(head["core_scores"])
        fig = viz.kde_hist(
            [("baseline", head["baseline_scores"], viz.INK3), ("harness core", head["core_scores"], viz.TEAL)],
            title=f"Per-prompt score distribution ({head['model']})",
            subtitle="mean over judges, per paired prompt", xlabel="mean rubric score (0-100)",
            vlines=[(bmean, viz.INK3, "base"), (cmean, viz.TEAL, "core")], show=False)
        charts["dist"] = _img(_fig_to_data_uri(fig), "score distributions")

    return charts


def _board_table_html(agg: dict, head_model: str) -> str:
    rows = []
    for r in agg["per_model"]:
        rows.append({
            "model": r["model"] + ("  *" if r["model"] == head_model else ""),
            "n pairs": r["n_pair"],
            "baseline": r["baseline"],
            "core": r["core"],
            "lift (core-base)": r["lift_core"],
            "win rate %": round(r["win_rate"] * 100, 1) if r["win_rate"] is not None else None,
            "hurts": r["hurts"],
        })
    df = pd.DataFrame(rows)
    sty = viz.pretty_table(
        df,
        caption="Per-model paired lift (baseline -> harness core). * = headline model.",
        fmt={"n pairs": "{:,}", "baseline": "{:.1f}", "core": "{:.1f}",
             "lift (core-base)": "{:+.1f}", "win rate %": "{:.1f}", "hurts": "{:,}"},
        gradient=["lift (core-base)"],
        bars=["n pairs"],
    )
    return sty.to_html()


def _dimension_table_html(head: dict) -> str:
    dims = [k for k in ("A", "B", "C", "D", "E") if k in head["component_core"]]
    rows = [{
        "dimension": _DIM_LABELS.get(k, k),
        "baseline": head["component_baseline"][k],
        "harness core": head["component_core"][k],
        "lift": head["component_lift"][k],
    } for k in dims]
    df = pd.DataFrame(rows)
    sty = viz.pretty_table(
        df,
        caption=f"Per-dimension mean ({head['model']}, core - baseline).",
        fmt={"baseline": "{:.2f}", "harness core": "{:.2f}", "lift": "{:+.2f}"},
        gradient=["lift"],
    )
    return sty.to_html()


_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: %(paper)s; color: %(ink)s;
  font-family: Inter, -apple-system, system-ui, "Segoe UI", sans-serif; line-height: 1.55; }
.wrap { max-width: 1040px; margin: 0 auto; padding: 32px 24px 72px; }
.hero { background: linear-gradient(135deg, %(paper2)s 0%%, %(paper3)s 100%%);
  border: 1px solid %(line)s; border-left: 6px solid %(ember)s; border-radius: 14px;
  padding: 30px 34px; margin-bottom: 28px; }
.hero .eyebrow { font-size: 12px; letter-spacing: .12em; text-transform: uppercase;
  color: %(ink3)s; font-weight: 700; margin: 0 0 8px; }
.hero h1 { margin: 0 0 12px; font-size: 30px; line-height: 1.2; color: %(ink)s; }
.hero .lift { color: %(ember)s; font-weight: 800; }
.hero p { margin: 0; color: %(ink2)s; font-size: 15.5px; max-width: 72ch; }
h2 { margin: 40px 0 6px; font-size: 21px; color: %(ink)s;
  border-bottom: 2px solid %(teal)s; padding-bottom: 6px; }
.section-note { color: %(ink3)s; font-size: 13.5px; margin: 4px 0 14px; max-width: 74ch; }
.chart { display: block; max-width: 100%%; height: auto; margin: 14px auto;
  border: 1px solid %(line)s; border-radius: 10px; background: %(paper)s; }
.tablewrap { overflow-x: auto; margin: 12px 0; }
table { border-collapse: collapse; }
footer { margin-top: 52px; padding: 20px 22px; background: %(paper2)s;
  border: 1px solid %(line)s; border-radius: 12px; color: %(ink3)s; font-size: 12.5px; }
footer b { color: %(ink2)s; }
.meta { color: %(ink4)s; font-size: 11.5px; margin-top: 10px; }
""" % {
    "paper": viz.PAPER, "paper2": viz.PAPER2, "paper3": viz.PAPER3,
    "ink": viz.INK, "ink2": viz.INK2, "ink3": viz.INK3, "ink4": viz.INK4,
    "teal": viz.TEAL, "ember": viz.EMBER, "line": viz.LINE,
}


def render_html(agg: dict, head: dict, *, title: str, today: str) -> str:
    """Render the full self-contained HTML document string."""
    charts = _build_charts(agg, head)
    lift = head["lift_core"]
    wr = head["win_rate"]
    wr_disp = f"{wr * 100:.1f}%" if wr is not None else "n/a"
    full_clause = ""
    if head["full"] is not None:
        full_clause = (f" The fuller harness arm reaches {head['full']} "
                       f"({head['lift_full']:+} vs baseline).")
    hero_p = (f"On <b>{html.escape(head['model'])}</b>, adding the DueCare harness moves the mean rubric "
              f"score from {head['baseline']} to {head['core']} across {head['n_pair']:,} paired prompts "
              f"(mean over the judge panel). The harness helps on {head['helps']:,} prompts and hurts on "
              f"{head['hurts']:,} (win rate {wr_disp}).{full_clause}")

    parts: list[str] = []
    parts.append('<div class="wrap">')
    parts.append('<div class="hero">')
    parts.append('<p class="eyebrow">DueCare harness-lift report</p>')
    parts.append(f'<h1>{html.escape(title)}: <span class="lift">+{lift}</span> mean lift on '
                 f'{html.escape(head["model"])}</h1>')
    parts.append(f'<p>{hero_p}</p>')
    parts.append('</div>')
    if "kpis" in charts:
        parts.append(charts["kpis"])

    parts.append('<h2>Cross-model board</h2>')
    parts.append('<p class="section-note">Every model with paired baseline and harness-core prompts, '
                 'sorted by paired coverage. Lift is the mean per-prompt (core - baseline) delta.</p>')
    parts.append('<div class="tablewrap">' + _board_table_html(agg, head["model"]) + '</div>')
    if "board" in charts:
        parts.append(charts["board"])

    if head["component_core"]:
        parts.append('<h2>Per-dimension breakdown</h2>')
        parts.append('<p class="section-note">The rubric scores five dimensions: A name the indicator, '
                     'B cite the law, C refuse/redirect, D offer resources, E protect privacy and safety. '
                     'Each is shown as a mean, baseline vs harness core.</p>')
        parts.append('<div class="tablewrap">' + _dimension_table_html(head) + '</div>')
        if "radar" in charts:
            parts.append(charts["radar"])

    if "dist" in charts:
        parts.append('<h2>Score distribution</h2>')
        parts.append('<p class="section-note">Per-prompt mean scores, baseline vs harness core. '
                     'The dashed lines mark each arm mean.</p>')
        parts.append(charts["dist"])

    parts.append('<footer>')
    parts.append('<b>Honest boundary.</b> These are rubric-scored proxy results under an LLM judge panel, '
                 'not real-world detection rates. Part of the raw lift is the harness prompting the model to '
                 'name the indicator, cite the law, refuse, offer resources, and protect privacy -- the same '
                 'A-E dimensions the judges score -- so some lift is rubric-instruction-following rather than '
                 'domain value; a length-matched placebo preamble is the fair control. The grades are public '
                 'on Kaggle (scores only, no response text). This page is regenerated by '
                 '<code>duecare.kit.report</code> from the paired panel and reproduces '
                 '<code>scripts/analyze_full_results.py</code>.')
    parts.append(f'<div class="meta">Generated {html.escape(today)} from {agg["n_rows"]:,} panel rows '
                 f'across {agg["n_models"]} models. DueCare -- migrant-worker safety harness for Gemma 4.</div>')
    parts.append('</footer>')
    parts.append('</div>')

    body = "\n".join(parts)
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8" />\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            f'<title>{html.escape(title)}</title>\n<style>{_CSS}</style>\n</head>\n'
            f'<body>\n{body}\n</body>\n</html>\n')


def generate_report(panel: pd.DataFrame | str | Path, out_html: str | Path, *,
                    model: str = "gemma4:31b",
                    title: str = "DueCare Harness-Lift Report",
                    today: str | None = None) -> Path:
    """Generate a self-contained DueCare-styled HTML report from a graded panel.

    Args:
        panel: a pandas DataFrame or a path to ``panel.jsonl`` / ``panel_grades.csv`` with columns
            ``model, arm, prompt_id, judge, score_0_100, components`` (components is a per-row A-E dict).
        out_html: destination path for the ``.html`` file (parent dirs are created).
        model: the headline model to feature (falls back to the most-covered model if absent).
        title: report title (used in the hero and the ``<title>``).
        today: ISO date string for the footer; defaults to today (UTC).

    Returns:
        The written ``Path``.

    Raises:
        ValueError: if the panel has no paired baseline/harness_core rows.
    """
    records = load_records(panel)
    agg = aggregate(records)
    head = _pick_headline(agg, model)
    if head is None:
        raise ValueError("panel has no paired baseline/harness_core rows to report on")
    doc = render_html(agg, head, title=title, today=today or datetime.now(UTC).date().isoformat())
    out = Path(out_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out


def report_from_jsonl(path: str | Path, out_html: str | Path, **kwargs: Any) -> Path:
    """Convenience wrapper: generate a report directly from a ``panel.jsonl`` path."""
    return generate_report(Path(path), out_html, **kwargs)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate a self-contained DueCare harness-lift HTML report.")
    ap.add_argument("--panel", required=True, type=Path, help="panel.jsonl / panel_grades.csv path")
    ap.add_argument("--out", required=True, type=Path, help="output .html path")
    ap.add_argument("--model", default="gemma4:31b", help="headline model (default: gemma4:31b)")
    ap.add_argument("--title", default="DueCare Harness-Lift Report")
    args = ap.parse_args(argv)
    out = generate_report(args.panel, args.out, model=args.model, title=args.title)
    size = out.stat().st_size
    print(f"wrote {out} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
