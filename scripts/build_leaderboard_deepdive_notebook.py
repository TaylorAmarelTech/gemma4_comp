#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the cross-model leaderboard deep-dive notebook.

A focused, richly-visual Kaggle notebook that ranks every model in the published
`duecare-harness-benchmark-grades` dataset two ways -- by **raw lift** (harness_core - baseline)
and by **normalized gain** (the fraction of the available headroom the harness captured) -- and
shows that the two rankings genuinely *reorder* the board: a model with a high baseline has less
room to grow, so a big raw lift can be a smaller ceiling-adjusted gain. It renders KPI tiles, the
board as a styled table and an interactive bar, a rank-reorder slopegraph, a headroom scatter that
explains *why* the ranking flips, a forest plot of raw lift with 95% CIs, and a win/hurt breakdown.
CPU only, no model, no internet: runs to completion on Kaggle and is verifiable line by line.

    python scripts/build_leaderboard_deepdive_notebook.py

The visuals come from the shared `scripts/_notebook_viz.py` prettify toolkit: its PALETTE + HELPERS
strings are embedded into the notebook's first code cell at build time (stat_cards, pretty_table,
ibar, slope, ...), so every DueCare benchmark notebook shares one polished theme.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _notebook_viz import HELPERS, PALETTE  # noqa: E402  (embedded into the notebook's first code cell)

DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "leaderboard_deepdive"
KERNEL_ID = "taylorsamarel/duecare-cross-model-leaderboard-deep-dive"
TITLE = "DueCare Cross Model Leaderboard Deep Dive"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
DS = f"https://www.kaggle.com/datasets/{DATASET_ID}"
INDEX = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"
MIN_N = 150

# --------------------------------------------------------------------------------------
# Notebook code cells (each becomes one executable cell). Kept as module-level strings so
# the validation harness can exec them against a real flattened dataframe. The FIRST code
# cell is (PALETTE + HELPERS + SETUP) so the shared theme + helpers are defined before use.
# --------------------------------------------------------------------------------------

SETUP = '''import glob, os
from IPython.display import display

# np, pd, plt and the DueCare paper / ink / civic-teal theme + helper functions
# (stat_cards, pretty_table, ibar, slope, ...) come from the PALETTE + HELPERS block
# embedded above this cell at build time -- do NOT redefine the palette or rcParams here.
MIN_N = 150  # a model needs this many paired prompts to earn a leaderboard row

print("mounted under /kaggle/input:", os.listdir("/kaggle/input") if os.path.exists("/kaggle/input") else "none")
csvs = glob.glob("/kaggle/input/**/panel_grades.csv", recursive=True)
if not csvs:
    raise SystemExit("attach the dataset taylorsamarel/duecare-harness-benchmark-grades (panel_grades.csv not found)")
grades = pd.read_csv(sorted(csvs)[0])
mcsv = glob.glob("/kaggle/input/**/prompt_metadata.csv", recursive=True)
meta = pd.read_csv(mcsv[0]) if mcsv else None
print(f"loaded {len(grades):,} grade rows | {grades.prompt_id.nunique():,} prompts | "
      f"{grades.model.nunique()} models | arms {sorted(grades.arm.unique())} | judges {sorted(grades.judge.unique())}")'''

BOARD = '''def per_prompt_lift(df, model, teacher="harness_core", base="baseline"):
    """Average the judge panel per (prompt, arm), then pair teacher-vs-baseline per prompt.

    Returns the per-prompt lift series (teacher - base) and the (prompt x arm) pivot of mean scores.
    """
    d = df[df.model == model]
    piv = d.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack()
    keep = [c for c in (base, teacher) if c in piv.columns]
    piv = piv.dropna(subset=keep)
    return (piv[teacher] - piv[base]), piv

def leaderboard(df, min_n=MIN_N):
    """One row per model with >= min_n paired prompts: raw lift, normalized (ceiling-adjusted)
    gain, win/hurt rates, n, and a normal-approximation 95% CI on the raw lift."""
    rows = []
    for m in df.model.unique():
        lift, piv = per_prompt_lift(df, m)
        if len(lift) < min_n or "baseline" not in piv.columns or "harness_core" not in piv.columns:
            continue
        base, harn = piv["baseline"], piv["harness_core"]
        headroom = 100.0 - base                       # points still available above baseline
        mask = headroom > 0                           # only prompts with room to improve
        ng = ((harn[mask] - base[mask]) / headroom[mask]).clip(upper=1.0)  # fraction of headroom captured
        raw = float(lift.mean())
        ci = 1.96 * float(lift.std()) / np.sqrt(len(lift))
        rows.append({
            "model": m,
            "baseline": round(float(base.mean()), 1),
            "harnessed": round(float(harn.mean()), 1),
            "raw_lift": round(raw, 2),
            "ci_lo": round(raw - ci, 2),
            "ci_hi": round(raw + ci, 2),
            "norm_gain_pct": round(float(ng.mean()) * 100, 1),
            "win_pct": round(100 * float((lift > 0).mean()), 1),
            "hurt_pct": round(100 * float((lift < 0).mean()), 2),
            "n": int(len(lift)),
        })
    if not rows:
        raise SystemExit(f"no model has >= {min_n} paired prompts -- is the full panel attached?")
    return pd.DataFrame(rows).sort_values("raw_lift", ascending=False).reset_index(drop=True)

board = leaderboard(grades)
# a stable colour per model so the eye can track a model across every chart below
_pool = [TEAL, EMBER, GOOD, WARN, INK3, "#7b6ca6", "#3f7d5a", "#a65b7b"]
MODEL_COLORS = {m: _pool[i % len(_pool)] for i, m in enumerate(board.model)}
rank_raw = list(board.sort_values("raw_lift", ascending=False).model)
rank_ng = list(board.sort_values("norm_gain_pct", ascending=False).model)
print(f"{len(board)} models qualify (>= {MIN_N} paired prompts)\\n")
print("ranking by RAW lift        :", " > ".join(rank_raw))
print("ranking by NORMALIZED gain :", " > ".join(rank_ng))
print("rankings reorder           :", rank_raw != rank_ng)'''

KPIS = '''# KPI tiles: how many models are on the board, who leads each metric, and the headline lift.
_top_raw = board.sort_values("raw_lift", ascending=False).iloc[0]
_top_ng = board.sort_values("norm_gain_pct", ascending=False).iloc[0]
_head = board[board.model == "gemma4:31b"]
_head_lift = float(_head.raw_lift.iloc[0]) if len(_head) else float(_top_raw.raw_lift)
stat_cards([
    (len(board), "models on the board", TEAL),
    (_top_raw.model, f"top raw lift  +{_top_raw.raw_lift:.1f}", EMBER),
    (_top_ng.model, f"top ceiling-adj gain  {_top_ng.norm_gain_pct:.0f}%", GOOD),
    (f"+{_head_lift:.1f}", "gemma4:31b raw lift (0-100)", INK2),
], figsize=(13.5, 2.0))'''

BOARD_TABLE = '''# The board -- raw lift alongside the ceiling-adjusted (normalized) gain, as a styled table.
bshow = board[["model", "baseline", "harnessed", "raw_lift", "norm_gain_pct", "win_pct", "n"]].copy()
bshow["norm_gain"] = bshow.pop("norm_gain_pct") / 100.0          # fraction of headroom captured (0-1)
bshow = bshow.rename(columns={"win_pct": "win%"})
bshow = bshow[["model", "baseline", "harnessed", "raw_lift", "norm_gain", "win%", "n"]]
_hl = bshow.index[bshow.model == "gemma4:31b"]
hl = int(_hl[0]) if len(_hl) else None                            # highlight the headline model's row
display(pretty_table(
    bshow,
    caption="Cross-model board: raw lift vs ceiling-adjusted gain",
    fmt={"raw_lift": "{:+.1f}", "norm_gain": "{:.3f}", "baseline": "{:.1f}",
         "harnessed": "{:.1f}", "win%": "{:.1f}", "n": "{:,}"},
    gradient=["raw_lift", "norm_gain"], bars=["raw_lift"], highlight_row=hl))'''

CHART_IBAR = '''# The same board as a chart: baseline (grey) + harness_core lift (teal), sorted by total, n labeled.
ibar(list(board.model), list(board.baseline), list(board.raw_lift), ns=list(board.n),
     title="Cross-model board: baseline + harness_core lift",
     subtitle="each bar = mean baseline plus the paired harness_core lift; n = paired prompts")'''

CHART_SLOPE = '''# The reorder as a slopegraph: rank by raw lift (left) vs by ceiling-adjusted gain (right).
r_raw = list(board.sort_values("raw_lift", ascending=False).model)
r_ng = list(board.sort_values("norm_gain_pct", ascending=False).model)
pos_raw = {m: i + 1 for i, m in enumerate(r_raw)}   # 1 = best
pos_ng = {m: i + 1 for i, m in enumerate(r_ng)}
models = list(board.model)
# positive ranks + invert=True so rank 1 (best) sits at the TOP and labels stay positive
raw_rank = [pos_raw[m] for m in models]
adj_rank = [pos_ng[m] for m in models]
slope(models, raw_rank, adj_rank, left_lab="rank by raw lift",
      right_lab="rank by ceiling-adj gain", ylabel="rank (1=best)", invert=True,
      title="Same models, different winner",
      subtitle="lines that cross = the ranking reorders once you adjust for headroom")'''

CHART_HEADROOM = '''# Why the ranking flips: iso-gain curves make the headroom mechanism explicit.
fig, ax = plt.subplots(figsize=(9.8, 5.2))
xs = np.linspace(max(0, board.baseline.min() - 6), board.baseline.max() + 6, 100)
for g in (0.6, 0.75, 0.9):
    ax.plot(xs, g * (100 - xs), color=INK3, ls="--", lw=1.0, alpha=0.55, zorder=1)
    ax.text(xs[3], g * (100 - xs[3]) + 0.6, f"{int(g*100)}% of headroom", fontsize=8.5,
            color=INK3, rotation=-14)
for _, r in board.iterrows():
    ax.scatter(r.baseline, r.raw_lift, s=230, color=MODEL_COLORS[r.model], edgecolor=PAPER,
               linewidth=1.5, zorder=3)
    ax.annotate(f"{r.model}\\n+{r.raw_lift:.1f} raw - {r.norm_gain_pct:.0f}% gain",
                (r.baseline, r.raw_lift), textcoords="offset points", xytext=(10, 10),
                fontsize=9, color=INK2, fontweight="bold")
ax.set_xlabel("baseline score (0-100)   ->   higher baseline = less headroom left")
ax.set_ylabel("raw lift (points): harness_core - baseline")
ax.set_title("Why the board reorders: equal raw lift buys more normalized gain when the baseline is high")
ax.margins(x=0.12, y=0.16)
fig.tight_layout(); plt.show()'''

CHART_FOREST = '''# Forest plot: raw lift per model with a 95% CI, models on the y-axis, zero line in ember.
r = board.sort_values("raw_lift").reset_index(drop=True)      # ascending -> largest at the top
y = np.arange(len(r))
xerr = np.vstack([r.raw_lift - r.ci_lo, r.ci_hi - r.raw_lift])
fig, ax = plt.subplots(figsize=(9.4, 0.7 * len(r) + 2.0))
ax.errorbar(r.raw_lift, y, xerr=xerr, fmt="o", color=TEAL, ecolor=INK3, elinewidth=2.2,
            capsize=6, markersize=11, markeredgecolor=PAPER, markeredgewidth=1.4, zorder=3)
ax.axvline(0, color=EMBER, lw=1.6, ls="--", label="no effect")
for i, row in r.iterrows():
    ax.text(row.ci_hi + 0.6, i, f"+{row.raw_lift:.1f}  [{row.ci_lo:.1f}, {row.ci_hi:.1f}]",
            va="center", fontsize=9.5, color=INK2)
ax.set_yticks(y)
ax.set_yticklabels([f"{m}\\n(n={n:,})" for m, n in zip(r.model, r.n)])
ax.set_xlabel("raw lift: harness_core - baseline   (points / 100, with 95% CI)")
ax.set_xlim(min(0, float(r.ci_lo.min())) - 2, float(r.ci_hi.max()) + 12)
ax.set_title("Every model's lift excludes zero by a wide margin")
ax.grid(axis="y", alpha=0)
ax.legend(loc="lower right", framealpha=0.9)
fig.tight_layout(); plt.show()'''

CHART_WINHURT = '''# Win vs hurt: a diverging bar -- prompts the harness helped (right, green) vs hurt (left, ember).
r = board.sort_values("win_pct").reset_index(drop=True)
y = np.arange(len(r))
fig, ax = plt.subplots(figsize=(9.8, 0.7 * len(r) + 2.0))
ax.barh(y, r.win_pct, color=GOOD, edgecolor=PAPER, label="harness helped (win)")
ax.barh(y, -r.hurt_pct, color=EMBER, edgecolor=PAPER, label="harness hurt")
for i, row in r.iterrows():
    ax.text(row.win_pct + 1.0, i, f"{row.win_pct:.1f}% win", va="center", fontsize=9.5, color=INK2)
    if row.hurt_pct >= 0.05:
        ax.text(-row.hurt_pct - 1.0, i, f"{row.hurt_pct:.1f}% hurt", va="center", ha="right",
                fontsize=8.8, color=EMBER)
ax.axvline(0, color=INK3, lw=1.1)
ax.set_yticks(y); ax.set_yticklabels(r.model)
ax.set_xlim(-max(12, float(r.hurt_pct.max()) + 6), 108)
ax.set_xlabel("share of paired prompts (%)   <- hurt  |  win ->")
ax.set_title("The harness helps the vast majority of prompts and rarely hurts")
ax.grid(axis="y", alpha=0)
ax.legend(loc="lower right", framealpha=0.9)
fig.tight_layout(); plt.show()'''

CHART_DIFF = '''# Optional enrichment: the same headroom story inside the headline model, split by difficulty.
HEAD = "gemma4:31b" if "gemma4:31b" in set(board.model) else board.iloc[0].model
if meta is not None and "difficulty" in meta.columns:
    d = grades[grades.model == HEAD].merge(meta[["prompt_id", "difficulty"]], on="prompt_id", how="left")
    order = ["easy", "medium", "hard", "very_hard"]
    rows = []
    for diff in order:
        sub = d[d.difficulty == diff]
        if not len(sub):
            continue
        pv = sub.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack()
        if "baseline" not in pv.columns or "harness_core" not in pv.columns:
            continue
        pv = pv.dropna(subset=["baseline", "harness_core"])
        if len(pv) < 20:
            continue
        base, harn = pv["baseline"], pv["harness_core"]
        hr = 100.0 - base; mask = hr > 0
        ng = ((harn[mask] - base[mask]) / hr[mask]).clip(upper=1.0)
        rows.append((diff, float(base.mean()), float((harn - base).mean()), float(ng.mean()) * 100, len(pv)))
    if rows:
        dd = pd.DataFrame(rows, columns=["difficulty", "baseline", "raw_lift", "norm_gain", "n"])
        fig, ax = plt.subplots(figsize=(9.8, 4.6))
        x = np.arange(len(dd))
        ax.bar(x - 0.2, dd.raw_lift, 0.4, color=TEAL, edgecolor=PAPER, label="raw lift (points)")
        ax.bar(x + 0.2, dd.norm_gain, 0.4, color=EMBER, edgecolor=PAPER, label="normalized gain (%)")
        for i, rr in dd.iterrows():
            ax.text(i - 0.2, rr.raw_lift + 0.6, f"+{rr.raw_lift:.0f}", ha="center", fontsize=9, color=INK2, fontweight="bold")
            ax.text(i + 0.2, rr.norm_gain + 0.6, f"{rr.norm_gain:.0f}%", ha="center", fontsize=9, color=INK2, fontweight="bold")
        ax.set_xticks(x); ax.set_xticklabels([f"{r.difficulty}\\nbase {r.baseline:.0f} - n={int(r.n):,}" for _, r in dd.iterrows()], fontsize=9)
        ax.set_ylabel("lift")
        ax.set_title(f"Inside one model ({HEAD}): harder prompts start lower, so their raw lift is a bigger normalized gain")
        ax.legend(loc="upper left", framealpha=0.9)
        fig.tight_layout(); plt.show()
    else:
        print("not enough per-difficulty paired prompts for the headline model -- skipping")
else:
    print("prompt_metadata.csv not attached -- skipping the by-difficulty enrichment")'''


def _toc() -> str:
    items = [
        ("0", "The board", "board"),
        ("1", "Raw lift vs ceiling-adjusted gain (the reorder)", "reorder"),
        ("2", "Forest plot with 95% confidence intervals", "forest"),
        ("3", "Win vs hurt", "winhurt"),
        ("4", "Inside one model, by difficulty", "difficulty"),
        ("5", "What this proves -- and what it does not", "boundary"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c = []

    c.append(md(
        "# Which model gains the most from a safety harness? It depends how you ask.\n\n"
        "This is a **cross-model leaderboard deep-dive**. Every model in the public "
        f"[`duecare-harness-benchmark-grades`]({DS}) dataset is ranked two ways:\n\n"
        "- **Raw lift** -- `harness_core - baseline`, in rubric points. The blunt headline number.\n"
        "- **Normalized gain** -- `(harness_core - baseline) / (100 - baseline)`, the fraction of the "
        "*available headroom* the harness actually captured.\n\n"
        "**The punchline:** the two metrics crown different winners. A model with a high baseline has "
        "less room to grow, so its big raw lift is a *smaller* normalized gain -- and the board reorders. "
        "The model with the largest raw lift can finish **last** once you adjust for the ceiling. Everything "
        "below is recomputed **live** from the dataset -- CPU only, no model, no internet -- so you can check "
        "every number.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** These are **LLM-judge rubric measurements** over "
        "synthetic / composite prompts -- *silver* labels, not human-verified gold, and **not** a claim of "
        "real-world detection. The leaderboard ranks *tested behaviour* (evidence-first reasoning, refusal "
        "discipline, ILO-indicator grounding, privacy boundaries), not field outcomes."))

    c.append(md(
        "### How to read the two metrics\n"
        "The three arms -- `baseline`, `harness_core`, `harness_full` -- are graded on the **same** prompts by "
        "a panel of independent judges, so the comparison is *paired*. We average the judges per "
        "`(prompt, arm)`, then take the per-prompt difference `harness_core - baseline`.\n\n"
        "A model already scoring **58/100** has only **42 points** of headroom; one scoring **40** has **60**. "
        "So the same `+36` raw lift is `36/42 ~ 86%` of the headroom for the first model but only `36/60 = 60%` "
        "for the second. **Normalized gain** rewards *closing the remaining gap*, which is why it can flip the "
        "ranking. A model needs at least "
        f"**{MIN_N} paired prompts** to earn a row, so the board is not driven by a handful of lucky prompts."))

    c.append(md('<a id="board"></a>\n## 0 - The board'))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + SETUP))
    c.append(md("Compute one leaderboard row per qualifying model -- baseline, harnessed, raw lift, normalized "
                "(ceiling-adjusted) gain, win/hurt rates, sample size, and a 95% CI on the raw lift. The last "
                "line prints both rankings so you can see, before any chart, that they disagree."))
    c.append(code(BOARD))
    c.append(md("The board at a glance -- how many models qualify, which model leads each metric, and where the "
                "headline model (`gemma4:31b`) lands on raw lift."))
    c.append(code(KPIS))
    c.append(md("Here is the board as a styled table, sorted by raw lift. The **teal** in-cell bar tracks raw "
                "lift and the two columns are colour-graded; the headline model's row is highlighted. Notice the "
                "biggest `raw_lift` is *not* the biggest `norm_gain` -- sorting by the normalized column would "
                "reorder the rows."))
    c.append(code(BOARD_TABLE))
    c.append(md("The same board as a chart: each bar is the model's mean baseline (grey) plus the harness_core "
                "lift (teal), sorted by the harnessed total, with the paired-prompt count on each label."))
    c.append(code(CHART_IBAR))

    c.append(md('<a id="reorder"></a>\n## 1 - Raw lift vs ceiling-adjusted gain -- the reorder\n'
                "This is the heart of the deep-dive. On the left, models are ranked by **raw lift**; on the right, "
                "by **normalized gain**. Each line is one model -- where the lines cross, the ranking flips. The "
                "model at the top-left (biggest raw lift) is often *not* the model at the top-right."))
    c.append(code(CHART_SLOPE))
    c.append(md("*Why* does it flip? The dashed curves below are lines of constant normalized gain -- "
                "`raw_lift = g * (100 - baseline)`. Because headroom shrinks as the baseline rises, the same raw "
                "lift lands on a **higher** iso-gain curve when the baseline is high. A model sitting on the far "
                "right (high baseline) needs far less raw lift to capture the same fraction of what was left."))
    c.append(code(CHART_HEADROOM))

    c.append(md('<a id="forest"></a>\n## 2 - Forest plot with 95% confidence intervals\n'
                "Ranking is only meaningful if the underlying lifts are real. Here is each model's raw lift with a "
                "normal-approximation 95% CI (models with more paired prompts get tighter intervals). Every interval "
                "sits well to the right of the ember zero line -- none of these lifts is a coin-flip."))
    c.append(code(CHART_FOREST))

    c.append(md('<a id="winhurt"></a>\n## 3 - Win vs hurt\n'
                "The mean lift could, in principle, hide a model that helps a few prompts enormously while hurting "
                "many. It does not. For every model, the harness *helped* the overwhelming majority of paired "
                "prompts (green, right) and *hurt* only a sliver (ember, left)."))
    c.append(code(CHART_WINHURT))

    c.append(md('<a id="difficulty"></a>\n## 4 - The same story inside one model, by difficulty\n'
                "The headroom effect is not just a between-model artefact. Split the headline model by prompt "
                "difficulty: harder prompts start with a lower baseline, so their raw lift converts into a larger "
                "normalized gain -- the exact mechanism that reorders the cross-model board, visible within a single "
                "model. (Optional -- needs `prompt_metadata.csv` attached.)"))
    c.append(code(CHART_DIFF))

    c.append(md(
        '<a id="boundary"></a>\n## 5 - What this proves -- and what it does not\n\n'
        "**Proves.** On this rubric, wrapping any model in the DueCare harness produces a large, statistically "
        "clear lift, and *how you rank models depends on the metric*: raw lift favours low-baseline models with "
        "lots of headroom, while normalized gain favours models that close the remaining gap. Reporting both is "
        "the honest way to compare -- a single 'best model' claim is metric-dependent.\n\n"
        "**Does not prove.** Real-world detection quality, that any specific worker is helped, or that the rubric "
        "is ground truth. Judges are LLMs; prompts are synthetic / composite; labels are *silver*, not gold. The "
        "board measures tested behaviour, not field outcomes.\n\n"
        "### Use the data\n"
        f"- **Rank your own model:** attach [`{DATASET_ID.split('/')[1]}`]({DS}), pair `harness_core` vs "
        "`baseline` per prompt, and report *both* raw lift and normalized gain.\n"
        f"- **Go wider:** the [**Start Here** index]({INDEX}) links the full notebook collection (headline lift, "
        "per-dimension sweep, judge agreement, and more).\n"
        f"- **Read the code:** the [source repository]({REPO}) has the harness, the grader, and the exhaustive "
        "per-dimension benchmark.\n\n"
        "License: MIT. Scores + prompt metadata only -- no response text, no PII."))

    nb = nbf.v4.new_notebook()
    nb["cells"] = c
    nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                      "language_info": {"name": "python"}}
    nbf.write(nb, str(nb_dir / "notebook.ipynb"))

    kmeta = {"id": KERNEL_ID, "title": TITLE, "code_file": "notebook.ipynb", "language": "python",
             "kernel_type": "notebook", "is_private": False, "enable_gpu": False, "enable_tpu": False,
             "enable_internet": False, "dataset_sources": [DATASET_ID], "competition_sources": [], "kernel_sources": []}
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(kmeta, indent=2), encoding="utf-8")
    return {"kernel_id": KERNEL_ID, "cells": len(c), "notebook_dir": str(nb_dir),
            "notebook": str(nb_dir / "notebook.ipynb"), "metadata": str(nb_dir / "kernel-metadata.json")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    summary = build(args.output, force=args.force)
    slug = summary["kernel_id"].split("/", 1)[1]
    assert "DueCare Cross Model Leaderboard Deep Dive".lower().replace(" ", "-") == "duecare-cross-model-leaderboard-deep-dive"
    assert TITLE.lower().replace(" ", "-") == slug, f"title must slugify to id: {TITLE!r} vs {slug!r}"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
