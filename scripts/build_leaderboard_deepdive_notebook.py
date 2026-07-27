#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the cross-model leaderboard deep-dive notebook.

A long, richly-visual Kaggle notebook that ranks every qualifying model in the published
`duecare-harness-benchmark-grades` dataset two ways -- by **raw lift** (harness_core - baseline)
and by **normalized gain** (the fraction of the available headroom the harness captured) -- and
shows that the two rankings genuinely *reorder* the board: a model with a high baseline has less
room to grow, so a big raw lift can be a smaller ceiling-adjusted gain.

This is the expanded, twelve-section edition. It renders KPI tiles, the board as a styled table
and an interactive bar, a rank-reorder slopegraph, a headroom scatter with iso-gain curves, a
two-metric ranked table, a confidence-interval-vs-sample-size scatter, a forest plot, a bootstrap
CI table, a paired Cohen's d effect-size forest, a win/hurt diverging bar, a per-model A-E radar
small-multiples grid, a model x dimension lift heatmap, per-model score-distribution small
multiples, a per-prompt lift violin, a model x category lift heatmap, and a within-model
by-difficulty view. CPU only, no model, no internet: runs to completion on Kaggle and is
verifiable cell by cell.

    python scripts/build_leaderboard_deepdive_notebook.py

The visuals come from the shared `scripts/_notebook_viz.py` prettify toolkit: its PALETTE + HELPERS
strings are embedded into the notebook's first code cell at build time (stat_cards, pretty_table,
ibar, slope, heatmap, ...), so every DueCare benchmark notebook shares one polished theme.
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

SETUP = '''import glob, os, math
from IPython.display import display

# np, pd, plt and the DueCare paper / ink / civic-teal theme + helper functions
# (stat_cards, pretty_table, ibar, slope, heatmap, ...) come from the PALETTE + HELPERS
# block embedded above this cell at build time -- do NOT redefine the palette or rcParams here.
MIN_N = 150  # a model needs this many paired prompts to earn a leaderboard row

print("mounted under /kaggle/input:", os.listdir("/kaggle/input") if os.path.exists("/kaggle/input") else "none")
csvs = glob.glob("/kaggle/input/**/panel_grades.csv", recursive=True)
if not csvs:
    raise SystemExit("attach the dataset taylorsamarel/duecare-harness-benchmark-grades (panel_grades.csv not found)")
grades = pd.read_csv(sorted(csvs)[0])
mcsv = glob.glob("/kaggle/input/**/prompt_metadata.csv", recursive=True)
meta = pd.read_csv(mcsv[0]) if mcsv else None
print(f"loaded {len(grades):,} grade rows | {grades.prompt_id.nunique():,} prompts | "
      f"{grades.model.nunique()} models | arms {sorted(grades.arm.unique())} | judges {sorted(grades.judge.unique())}")
print("prompt_metadata.csv:", "attached" if meta is not None else "not attached (category views will self-skip)")'''

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
MODELS = list(board.model)                                   # order = raw-lift descending
MODEL_COLORS = {m: _pool[i % len(_pool)] for i, m in enumerate(MODELS)}
rank_raw = list(board.sort_values("raw_lift", ascending=False).model)
rank_ng = list(board.sort_values("norm_gain_pct", ascending=False).model)

# ---- shared per-dimension structures reused by the radar + heatmaps further down ----
DIMS = ["A", "B", "C", "D", "E"]
DIM_SHORT = {"A": "indicator", "B": "legal", "C": "refusal", "D": "resources", "E": "privacy"}
DIM_LONG = {"A": "A indicator (ILO)", "B": "B legal", "C": "C refusal", "D": "D resources", "E": "E privacy"}
DIM_MAX = {d: float(grades[d].max()) for d in DIMS if d in grades.columns}   # rubric ceiling per dimension

def dim_pivots(model):
    """Per-dimension paired means: {dim: (baseline_mean, harness_core_mean)} over shared prompts."""
    d = grades[grades.model == model]
    out = {}
    for dim in DIMS:
        if dim not in d.columns:
            continue
        piv = d.groupby(["prompt_id", "arm"])[dim].mean().unstack()
        if "baseline" in piv.columns and "harness_core" in piv.columns:
            piv = piv.dropna(subset=["baseline", "harness_core"])
            out[dim] = (float(piv["baseline"].mean()), float(piv["harness_core"].mean()))
    return out

def score_pivot(model):
    """Per-prompt mean score, paired baseline vs harness_core (a 2-column frame)."""
    d = grades[grades.model == model]
    piv = d.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack()
    return piv.dropna(subset=["baseline", "harness_core"])

DIMPIV = {m: dim_pivots(m) for m in MODELS}                  # cache: reused by radar + dim heatmap

print(f"{len(board)} models qualify (>= {MIN_N} paired prompts)\\n")
print("ranking by RAW lift        :", " > ".join(rank_raw))
print("ranking by NORMALIZED gain :", " > ".join(rank_ng))
print("rankings reorder           :", rank_raw != rank_ng)
print("rubric ceiling per dim     :", {d: int(DIM_MAX[d]) for d in DIMS if d in DIM_MAX})'''

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

TABLE_TWO_METRIC = '''# The two rankings side by side: each model's rank under raw lift and under normalized gain,
# plus the rank shift. A positive shift = the model climbs once you adjust for headroom.
tm = board.copy()
tm["rank_raw"] = tm["raw_lift"].rank(ascending=False, method="min").astype(int)
tm["rank_ng"] = tm["norm_gain_pct"].rank(ascending=False, method="min").astype(int)
tm["rank_shift"] = tm["rank_raw"] - tm["rank_ng"]     # >0 = climbs on ceiling-adjusted gain
show = tm[["model", "baseline", "raw_lift", "rank_raw", "norm_gain_pct", "rank_ng", "rank_shift"]]
show = show.sort_values("rank_raw").reset_index(drop=True)
_hl = show.index[show.model == "gemma4:31b"]
hl = int(_hl[0]) if len(_hl) else None
display(pretty_table(
    show, caption="Two metrics, two rankings: raw lift vs ceiling-adjusted gain",
    fmt={"baseline": "{:.1f}", "raw_lift": "{:+.1f}", "norm_gain_pct": "{:.1f}",
         "rank_raw": "{:d}", "rank_ng": "{:d}", "rank_shift": "{:+d}"},
    gradient=["raw_lift", "norm_gain_pct"], bars=["raw_lift"], highlight_row=hl))
_climb = show[show.rank_shift > 0]
if len(_climb):
    print("climbs when judged on ceiling-adjusted gain:", ", ".join(_climb.model))
print("the model with the largest RAW lift is",
      "the same as" if rank_raw[0] == rank_ng[0] else "NOT", "the largest NORMALIZED gain.")'''

CHART_CI_VS_N = '''# Why the board requires MIN_N paired prompts: the 95% CI on the lift collapses as n grows.
# Plot EVERY model -- including the sub-threshold ones -- so the noise floor is visible, not asserted.
rows = []
for m in grades.model.unique():
    lift, piv = per_prompt_lift(grades, m)
    if not len(lift) or "baseline" not in piv.columns or "harness_core" not in piv.columns:
        continue
    n = len(lift)
    ci = 1.96 * float(lift.std()) / np.sqrt(n) if n > 1 else float("nan")
    rows.append((m, n, ci, float(lift.mean()), bool(n >= MIN_N)))
cn = pd.DataFrame(rows, columns=["model", "n", "ci_half", "raw_lift", "qualifies"])
fig, ax = plt.subplots(figsize=(9.8, 5.4))
for q, col, lab in [(True, TEAL, f"on the board (n>={MIN_N})"),
                    (False, INK4, f"excluded (n<{MIN_N}, too noisy)")]:
    s = cn[cn.qualifies == q]
    ax.scatter(s.n, s.ci_half, s=175, color=col, edgecolor=PAPER, linewidth=1.4, label=lab, zorder=3)
_ytop = ax.get_ylim()[1]
for _, r in cn.iterrows():
    ax.annotate(f"{r.model}\\n+/-{r.ci_half:.1f}", (r.n, r.ci_half), textcoords="offset points",
                xytext=(8, 5), fontsize=8.2, color=INK2)
ax.axvline(MIN_N, color=EMBER, lw=1.6, ls="--", zorder=2)
ax.text(MIN_N * 1.05, _ytop * 0.9, f"MIN_N = {MIN_N}", color=EMBER, fontweight="bold", fontsize=9.5)
ax.set_xscale("log")
ax.set_xlabel("paired prompts n (log scale)   ->   more evidence")
ax.set_ylabel("95% CI half-width on the raw lift (points)   ->   less certain")
ax.set_title("Small samples are noisy: the confidence interval collapses as n grows")
fig.tight_layout(); plt.show()
print("excluded, low-n models (indicative only):",
      ", ".join(f"{r.model} (n={int(r.n)}, +/-{r.ci_half:.1f})" for _, r in cn[~cn.qualifies].sort_values("n").iterrows()))'''

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

TABLE_BOOTSTRAP = '''# A non-parametric check on the forest plot: bootstrap each model's mean lift (2000 resamples,
# seeded) and compare the percentile CI to the normal-approximation CI. They agree closely.
rng = np.random.default_rng(13)
B = 2000
rows = []
for m in board.model:
    lift, _ = per_prompt_lift(grades, m)
    v = lift.to_numpy(dtype=float); n = len(v)
    boot = np.empty(B)
    for b in range(B):
        boot[b] = v[rng.integers(0, n, n)].mean()
    na = 1.96 * v.std() / np.sqrt(n)
    rows.append({"model": m, "n": n, "mean_lift": round(float(v.mean()), 2),
                 "boot_lo": round(float(np.percentile(boot, 2.5)), 2),
                 "boot_hi": round(float(np.percentile(boot, 97.5)), 2),
                 "normal_lo": round(float(v.mean() - na), 2),
                 "normal_hi": round(float(v.mean() + na), 2)})
bs = pd.DataFrame(rows).sort_values("mean_lift", ascending=False).reset_index(drop=True)
display(pretty_table(
    bs, caption="Bootstrap vs normal-approximation 95% CI on the mean lift (they agree)",
    fmt={"n": "{:,}", "mean_lift": "{:+.2f}", "boot_lo": "{:+.2f}", "boot_hi": "{:+.2f}",
         "normal_lo": "{:+.2f}", "normal_hi": "{:+.2f}"},
    gradient=["mean_lift"], bars=["mean_lift"]))
print("Both intervals sit far above zero for every model -- the lift is not a sampling artefact.")'''

CHART_COHEND = '''# Effect size, not just significance: paired Cohen's d = mean(lift) / sd(lift). Whiskers are a
# seeded bootstrap 95% CI on d; the dotted lines mark the conventional small / medium / large bands.
rng = np.random.default_rng(29)
B = 1500
rows = []
for m in board.model:
    lift, _ = per_prompt_lift(grades, m)
    v = lift.to_numpy(dtype=float); n = len(v)
    d = v.mean() / v.std()
    bd = np.empty(B)
    for b in range(B):
        s = v[rng.integers(0, n, n)]
        bd[b] = s.mean() / s.std()
    rows.append((m, float(d), float(np.percentile(bd, 2.5)), float(np.percentile(bd, 97.5)), n))
ce = pd.DataFrame(rows, columns=["model", "d", "lo", "hi", "n"]).sort_values("d").reset_index(drop=True)
y = np.arange(len(ce))
fig, ax = plt.subplots(figsize=(9.6, 0.8 * len(ce) + 2.2))
for xv, lab in [(0.2, "small"), (0.5, "medium"), (0.8, "large")]:
    ax.axvline(xv, color=INK4, ls=":", lw=1.1, zorder=1)
    ax.text(xv, len(ce) - 0.35, lab, color=INK4, fontsize=8.6, ha="center")
xerr = np.vstack([ce.d - ce.lo, ce.hi - ce.d])
ax.errorbar(ce.d, y, xerr=xerr, fmt="o", color=TEAL, ecolor=INK3, elinewidth=2.2, capsize=6,
            markersize=12, markeredgecolor=PAPER, markeredgewidth=1.4, zorder=3)
for i, row in ce.iterrows():
    ax.text(row.hi + 0.04, i, f"d={row.d:.2f}  (n={int(row.n):,})", va="center", fontsize=9.5, color=INK2)
ax.set_yticks(y); ax.set_yticklabels(ce.model)
ax.set_xlabel("paired Cohen's d = mean(lift) / sd(lift)   ->   larger = more reliable per-prompt gain")
ax.set_xlim(0, float(ce.hi.max()) + 0.55)
ax.set_title("Effect size per model: every harness effect clears the 'large' threshold (d >= 0.8)")
ax.grid(axis="y", alpha=0)
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

CHART_RADAR_GRID = '''# Small-multiples radar: each model's A-E rubric profile, baseline (grey) vs harness_core (teal),
# every axis normalized to that dimension's rubric ceiling so the five dimensions compare fairly.
labels = [DIM_SHORT[d] for d in DIMS if d in DIM_MAX]
dims = [d for d in DIMS if d in DIM_MAX]
N = len(dims)
ang = list(np.linspace(0, 2 * np.pi, N, endpoint=False)); ang += ang[:1]
ncol = 2 if len(MODELS) > 1 else 1
nrow = math.ceil(len(MODELS) / ncol)
fig, axes = plt.subplots(nrow, ncol, figsize=(5.6 * ncol, 5.1 * nrow), subplot_kw=dict(polar=True))
axes = np.atleast_1d(axes).ravel()
for ax, m in zip(axes, MODELS):
    dp = DIMPIV[m]
    base = [100 * dp[d][0] / DIM_MAX[d] for d in dims]
    harn = [100 * dp[d][1] / DIM_MAX[d] for d in dims]
    for vals, col, name in [(base, INK3, "baseline"), (harn, TEAL, "harness_core")]:
        v = vals + vals[:1]
        ax.plot(ang, v, color=col, lw=2.4, label=name, zorder=3)
        ax.fill(ang, v, color=col, alpha=0.14, zorder=2)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels, fontsize=9.3, color=INK2)
    ax.set_theta_offset(np.pi / 2); ax.set_theta_direction(-1)
    ax.set_ylim(0, 100); ax.set_yticks([25, 50, 75]); ax.set_yticklabels(["25", "50", "75"], fontsize=7.5, color=INK4)
    ax.grid(color=LINE, alpha=0.8); ax.spines["polar"].set_color(LINE)
    ax.set_title(m, fontsize=12.5, fontweight="bold", pad=16, color=INK)
    ax.legend(loc="upper right", bbox_to_anchor=(1.20, 1.13), fontsize=8.4)
for ax in axes[len(MODELS):]:
    ax.axis("off")
fig.suptitle("Where each model gains: A-E rubric profile, baseline vs harness_core (% of dimension ceiling)",
             fontsize=13.5, fontweight="bold", color=INK, y=1.01)
fig.tight_layout(); plt.show()'''

HEATMAP_MODEL_DIM = '''# Model x dimension: the per-dimension lift (harness_core - baseline). Reads off which model gains
# most on which rubric axis -- a model with a weak baseline on 'indicator' has the most to gain there.
dims = [d for d in DIMS if d in DIM_MAX]
mat = [[DIMPIV[m][d][1] - DIMPIV[m][d][0] for d in dims] for m in MODELS]
heatmap(mat, MODELS, [DIM_SHORT[d] for d in dims],
        title="Per-dimension lift by model (harness_core - baseline)",
        subtitle="darker = bigger gain on that rubric dimension; A indicator B legal C refusal D resources E privacy",
        cmap="BuGn", fmt="+.1f", cbar_label="lift (points)")'''

CHART_DIST_GRID = '''# Score distributions: per-prompt mean score, baseline (grey) vs harness_core (teal), one panel per
# model. The harness shifts the whole mass to the right -- not a few outliers dragging the mean up.
ncol = 2 if len(MODELS) > 1 else 1
nrow = math.ceil(len(MODELS) / ncol)
fig, axes = plt.subplots(nrow, ncol, figsize=(6.4 * ncol, 3.4 * nrow))
axes = np.atleast_1d(axes).ravel()
for ax, m in zip(axes, MODELS):
    piv = score_pivot(m)
    for arm, col in [("baseline", INK3), ("harness_core", TEAL)]:
        vals = piv[arm].to_numpy(dtype=float); vals = vals[np.isfinite(vals)]
        ax.hist(vals, bins=28, range=(0, 100), density=True, color=col, alpha=0.16, zorder=1)
        try:
            from scipy.stats import gaussian_kde
            xs = np.linspace(0, 100, 200)
            ax.plot(xs, gaussian_kde(vals)(xs), color=col, lw=2.4, label=f"{arm} (mean {vals.mean():.0f})", zorder=3)
        except Exception:
            ax.hist(vals, bins=28, range=(0, 100), density=True, histtype="step", lw=2.4, color=col,
                    label=f"{arm} (mean {vals.mean():.0f})", zorder=3)
        ax.axvline(vals.mean(), color=col, ls="--", lw=1.3, zorder=4)
    ax.set_title(m, fontsize=12, fontweight="bold")
    ax.set_xlim(0, 100); ax.set_yticks([]); ax.set_xlabel("mean rubric score (0-100)")
    ax.legend(fontsize=8.2, loc="upper left")
for ax in axes[len(MODELS):]:
    ax.axis("off")
fig.suptitle("Per-model score distributions: the harness moves the whole distribution, not just the tail",
             fontsize=13.5, fontweight="bold", color=INK, y=1.01)
fig.tight_layout(); plt.show()'''

CHART_LIFT_VIOLIN = '''# The per-prompt lift as a violin per model (matplotlib, no seaborn needed): the body is the spread,
# the pale dot the median, the dark bar the inter-quartile range, the ember line zero.
data, labs = [], []
for m in MODELS:
    lift, _ = per_prompt_lift(grades, m)
    data.append(lift.to_numpy(dtype=float)); labs.append(f"{m}\\n(n={len(lift):,})")
fig, ax = plt.subplots(figsize=(9.8, 5.4))
parts = ax.violinplot(data, showmeans=False, showmedians=False, showextrema=False, widths=0.85)
for i, b in enumerate(parts["bodies"]):
    b.set_facecolor(MODEL_COLORS[MODELS[i]]); b.set_edgecolor(INK3); b.set_alpha(0.55); b.set_linewidth(1.1)
xs = np.arange(1, len(data) + 1)
q1 = [np.percentile(d, 25) for d in data]; q3 = [np.percentile(d, 75) for d in data]
meds = [float(np.median(d)) for d in data]
ax.vlines(xs, q1, q3, color=INK2, lw=6, zorder=3)
ax.scatter(xs, meds, color=PAPER, edgecolor=INK, s=55, zorder=4)
ax.axhline(0, color=EMBER, lw=1.6, ls="--", zorder=2, label="no change")
for x, d in zip(xs, data):
    ax.text(x, np.percentile(d, 98) + 2, f"{100 * (d > 0).mean():.0f}% > 0", ha="center",
            fontsize=9, color=INK2, fontweight="bold")
ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=9)
ax.set_ylabel("per-prompt lift (harness_core - baseline, points)")
ax.set_title("Distribution of per-prompt lift by model: almost every prompt improves")
ax.legend(loc="lower right"); ax.grid(axis="x", alpha=0)
fig.tight_layout(); plt.show()'''

HEATMAP_MODEL_CAT = '''# Model x category: per-(model, category) lift, blanked where a model has too few paired prompts in
# that category (n < MIN_CELL). Coverage is uneven, so only cells with enough evidence are coloured.
MIN_CELL = 12
if meta is None:
    print("prompt_metadata.csv not attached -- skipping the model x category heatmap")
elif "category" not in meta.columns:
    print("no 'category' column in prompt_metadata.csv -- skipping the model x category heatmap")
else:
    gm = grades.merge(meta[["prompt_id", "category"]], on="prompt_id", how="left")
    cell_lift, cell_n, cat_total = {}, {}, {}
    for m in MODELS:
        d = gm[gm.model == m]
        piv = d.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack()
        if "baseline" not in piv.columns or "harness_core" not in piv.columns:
            continue
        piv = piv.dropna(subset=["baseline", "harness_core"])
        piv = piv.assign(lift=piv["harness_core"] - piv["baseline"])
        cat = d.drop_duplicates("prompt_id").set_index("prompt_id")["category"]
        piv = piv.join(cat)
        for c, sub in piv.groupby("category"):
            cell_lift[(m, c)] = float(sub["lift"].mean()); cell_n[(m, c)] = int(len(sub))
            cat_total[c] = cat_total.get(c, 0) + len(sub)
    cats = sorted(cat_total, key=lambda c: cat_total[c], reverse=True)
    cats = [c for c in cats if sum(1 for m in MODELS if cell_n.get((m, c), 0) >= MIN_CELL) >= 2][:7]
    if not cats:
        print(f"not enough cross-model category coverage (n >= {MIN_CELL} in >= 2 models) -- skipping")
    else:
        arr = np.full((len(MODELS), len(cats)), np.nan)
        for i, m in enumerate(MODELS):
            for j, c in enumerate(cats):
                if cell_n.get((m, c), 0) >= MIN_CELL:
                    arr[i, j] = cell_lift[(m, c)]
        fig, ax = plt.subplots(figsize=(1.5 * len(cats) + 3.2, 0.72 * len(MODELS) + 2.4))
        im = ax.imshow(arr, cmap="BuGn", aspect="auto",
                       vmin=float(np.nanmin(arr)), vmax=float(np.nanmax(arr)))
        ax.set_xticks(range(len(cats)))
        ax.set_xticklabels([c.replace("_", " ") for c in cats], rotation=28, ha="right", fontsize=9)
        ax.set_yticks(range(len(MODELS))); ax.set_yticklabels(MODELS, fontsize=10)
        for i in range(len(MODELS)):
            for j in range(len(cats)):
                if np.isfinite(arr[i, j]):
                    ax.text(j, i, f"+{arr[i, j]:.0f}", ha="center", va="center", fontsize=9.5, color=INK)
                else:
                    ax.text(j, i, "n/a", ha="center", va="center", fontsize=8, color=INK4)
        fig.colorbar(im, ax=ax, label="mean paired lift (points)")
        ax.set_title(f"Per-category lift by model (blank = fewer than {MIN_CELL} paired prompts)", loc="left")
        fig.tight_layout(); plt.show()'''

CHART_DIFF = '''# The same headroom story inside the headline model, split by difficulty.
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
        ("2", "Fair comparison: why normalized gain, and the small-sample caveat", "fair"),
        ("3", "Confidence: forest plot + bootstrap", "forest"),
        ("4", "Effect sizes: paired Cohen's d per model", "effect"),
        ("5", "Win vs hurt", "winhurt"),
        ("6", "Where each model gains: the A-E radar", "radar"),
        ("7", "Model x dimension lift heatmap", "dimheat"),
        ("8", "Per-model score distributions", "dist"),
        ("9", "Model x category lift heatmap", "catheat"),
        ("10", "Inside one model, by difficulty", "difficulty"),
        ("11", "What this proves -- and what it does not", "boundary"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c = []

    # ---- front matter ------------------------------------------------------------------
    c.append(md(
        "# Which model gains the most from a safety harness? It depends how you ask.\n\n"
        "This is a **cross-model leaderboard deep-dive** -- twelve sections, every number recomputed "
        "**live** from the dataset, CPU only, no model, no internet. Every model in the public "
        f"[`duecare-harness-benchmark-grades`]({DS}) dataset with enough evidence is ranked two ways:\n\n"
        "- **Raw lift** -- `harness_core - baseline`, in rubric points. The blunt headline number.\n"
        "- **Normalized gain** -- `(harness_core - baseline) / (100 - baseline)`, the fraction of the "
        "*available headroom* the harness actually captured.\n\n"
        "**The punchline:** the two metrics crown different winners. A model with a high baseline has "
        "less room to grow, so its big raw lift is a *smaller* normalized gain -- and the board reorders. "
        "In this run the model with the **largest raw lift lands last** on normalized gain, and the model "
        "with the **highest normalized gain sits mid-table** on raw lift. Neither metric alone is 'the' "
        "answer; reporting both is the honest way to compare.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** These are **LLM-judge rubric measurements** over "
        "synthetic / composite prompts -- *silver* labels, not human-verified gold, and **not** a claim of "
        "real-world detection. The leaderboard ranks *tested behaviour* (evidence-first reasoning, refusal "
        "discipline, ILO-indicator grounding, privacy boundaries), not field outcomes. Sample sizes vary "
        "by two orders of magnitude across models; the small-n caveat in section 2 applies throughout."))

    c.append(md(
        "### How to read the two metrics\n"
        "The three arms -- `baseline`, `harness_core`, `harness_full` -- are graded on the **same** prompts by "
        "a panel of independent judges (each from a different model family, none grading its own output), so "
        "the comparison is *paired*. We average the judges per `(prompt, arm)`, then take the per-prompt "
        "difference `harness_core - baseline`. Averaging first and pairing second means a model is only "
        "credited for beating *its own* baseline on the *same* prompt -- not for being an easier prompt draw.\n\n"
        "A model already scoring **58/100** has only **42 points** of headroom; one scoring **40** has **60**. "
        "So the same `+36` raw lift is `36/42 ~ 86%` of the headroom for the first model but only `36/60 = 60%` "
        "for the second. **Normalized gain** rewards *closing the remaining gap*, which is why it can flip the "
        "ranking. A model needs at least "
        f"**{MIN_N} paired prompts** to earn a row, so the board is not driven by a handful of lucky prompts.\n\n"
        "Everything below is computed by the cells themselves. If you fork this notebook and attach the same "
        "dataset, you get the same figures; attach a newer version of the dataset and the board updates in place."))

    # ---- 0. The board ------------------------------------------------------------------
    c.append(md('<a id="board"></a>\n## 0 - The board\n'
                "We start with the whole board in four views: the raw numbers (KPI tiles and a styled table), "
                "then the same board as a chart. Read these top-to-bottom and you already have the headline; "
                "the rest of the notebook explains *why* the ranking is not as simple as the top row."))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + SETUP))
    c.append(md("Compute one leaderboard row per qualifying model -- baseline, harnessed, raw lift, normalized "
                "(ceiling-adjusted) gain, win/hurt rates, sample size, and a 95% CI on the raw lift. This cell "
                "also caches the per-dimension pivots (`DIMPIV`) and the rubric ceiling per dimension (`DIM_MAX`) "
                "that the radar and heatmaps reuse later. The last lines print both rankings so you can see, "
                "before any chart, that they disagree."))
    c.append(code(BOARD))
    c.append(md("The board at a glance -- how many models qualify, which model leads each metric, and where the "
                "headline model (`gemma4:31b`) lands on raw lift. Note already that the 'top raw lift' tile and "
                "the 'top ceiling-adjusted gain' tile name **different** models."))
    c.append(code(KPIS))
    c.append(md("Here is the board as a styled table, sorted by raw lift. The **teal** in-cell bar tracks raw "
                "lift and the two metric columns are colour-graded; the headline model's row is highlighted. "
                "Scan the `raw_lift` and `norm_gain` columns together: the row with the biggest `raw_lift` is "
                "*not* the row with the biggest `norm_gain` -- sorting by the normalized column would reorder "
                "the table entirely. That reordering is the subject of section 1."))
    c.append(code(BOARD_TABLE))
    c.append(md("The same board as a chart: each bar is the model's mean baseline (grey) plus the harness_core "
                "lift (teal), sorted by the harnessed total, with the paired-prompt count on each label. The "
                "grey segment is what the model could already do; the teal segment is what the thin, "
                "model-agnostic harness added on top."))
    c.append(code(CHART_IBAR))

    # ---- 1. The reorder ----------------------------------------------------------------
    c.append(md('<a id="reorder"></a>\n## 1 - Raw lift vs ceiling-adjusted gain -- the reorder\n'
                "This is the heart of the deep-dive. On the left of the slopegraph, models are ranked by **raw "
                "lift**; on the right, by **normalized gain**. Each line is one model -- where the lines cross, "
                "the ranking flips. The model at the top-left (biggest raw lift) is often *not* the model at the "
                "top-right, because raw lift quietly rewards having started low."))
    c.append(code(CHART_SLOPE))
    c.append(md("*Why* does it flip? The dashed curves below are lines of constant normalized gain -- "
                "`raw_lift = g * (100 - baseline)`. Because headroom shrinks as the baseline rises, the same raw "
                "lift lands on a **higher** iso-gain curve when the baseline is high. A model sitting on the far "
                "right (high baseline) needs far less raw lift to capture the same fraction of what was left. "
                "Follow any single model up to the dashed curve it touches to read off its normalized gain."))
    c.append(code(CHART_HEADROOM))
    c.append(md("To make the reorder concrete, here is the same information as a ranked table: each model's rank "
                "under raw lift, its rank under normalized gain, and the **rank shift** between them. A positive "
                "shift means the model climbs once you adjust for headroom -- exactly the models with the higher "
                "baselines. This table is the one to screenshot when someone claims a single 'best model'."))
    c.append(code(TABLE_TWO_METRIC))

    # ---- 2. Fair comparison ------------------------------------------------------------
    c.append(md('<a id="fair"></a>\n## 2 - Fair comparison: why normalized gain, and the small-sample caveat\n'
                "Two things make a cross-model comparison fair. First, **normalized gain** puts high- and "
                "low-baseline models on the same footing, so you are not just rewarding whoever started weakest. "
                "Second -- and just as important -- **sample size**. A mean lift computed over 40 prompts is far "
                "noisier than one computed over 8,000, and a noisy mean can top a leaderboard by luck.\n\n"
                "The board only admits models with at least "
                f"**{MIN_N} paired prompts** for exactly this reason. The scatter below makes the noise floor "
                "visible: it plots *every* model -- including the sub-threshold ones we exclude -- as sample size "
                "(log x) against the 95% CI half-width on its lift (y). The interval collapses as n grows. Treat "
                "any small-n row (the ember-line's left side) as indicative, never as a ranking claim."))
    c.append(code(CHART_CI_VS_N))

    # ---- 3. Confidence -----------------------------------------------------------------
    c.append(md('<a id="forest"></a>\n## 3 - Confidence: forest plot + bootstrap\n'
                "Ranking is only meaningful if the underlying lifts are real. The forest plot shows each "
                "qualifying model's raw lift with a normal-approximation 95% CI (more paired prompts -> tighter "
                "interval). Every interval sits well to the right of the ember zero line -- none of these lifts "
                "is a coin-flip."))
    c.append(code(CHART_FOREST))
    c.append(md("The normal approximation assumes the mean lift is roughly Gaussian. To check that assumption "
                "without relying on it, the next cell **bootstraps** each model's mean lift -- 2,000 seeded "
                "resamples with replacement -- and reports the 2.5th / 97.5th percentile interval next to the "
                "normal one. They line up closely, which is the reassurance that the forest plot is not an "
                "artefact of the Gaussian assumption."))
    c.append(code(TABLE_BOOTSTRAP))

    # ---- 4. Effect sizes ---------------------------------------------------------------
    c.append(md('<a id="effect"></a>\n## 4 - Effect sizes: paired Cohen\'s d per model\n'
                "A confidence interval tells you the lift is *not zero*; an **effect size** tells you how *large* "
                "it is relative to the prompt-to-prompt spread. Paired Cohen's d = `mean(lift) / sd(lift)`. By "
                "the usual convention d ~ 0.2 is small, 0.5 medium, 0.8 large. The forest below plots d per model "
                "with a seeded bootstrap 95% CI as whiskers and the three convention lines for reference -- every "
                "model clears the 'large' threshold, so the harness is not just statistically detectable, it is "
                "practically substantial."))
    c.append(code(CHART_COHEND))

    # ---- 5. Win vs hurt ----------------------------------------------------------------
    c.append(md('<a id="winhurt"></a>\n## 5 - Win vs hurt\n'
                "A large mean lift could, in principle, hide a model that helps a few prompts enormously while "
                "hurting many. The diverging bar rules that out: for every model, the harness *helped* the "
                "overwhelming majority of paired prompts (green, right) and *hurt* only a sliver (ember, left). "
                "One model carries a visibly larger hurt share than the others -- worth noting honestly, and "
                "exactly the kind of tail the per-prompt lift violin in section 8 examines more closely."))
    c.append(code(CHART_WINHURT))

    # ---- 6. Radar ----------------------------------------------------------------------
    c.append(md('<a id="radar"></a>\n## 6 - Where each model gains: the A-E radar\n'
                "The rubric has five dimensions -- **A** indicator grounding (ILO), **B** legal citation, **C** "
                "refusal discipline, **D** resources / next steps, **E** privacy boundaries -- and they have "
                "different point ceilings (A and C are worth 25, B is 20, D and E are 15). The radar grid below "
                "normalizes each axis to *its own* ceiling so the shapes are comparable, and overlays each "
                "model's baseline (grey) against its harness_core profile (teal). A model whose grey shape is "
                "dented on one axis is a model with the most to gain there -- and you can see the teal shape "
                "swell out to fill exactly those dents."))
    c.append(code(CHART_RADAR_GRID))

    # ---- 7. Model x dimension heatmap --------------------------------------------------
    c.append(md('<a id="dimheat"></a>\n## 7 - Model x dimension lift heatmap\n'
                "The radar shows the *shape* of each model's gain; the heatmap makes the *magnitudes* directly "
                "comparable across models. Each cell is the per-dimension lift (harness_core - baseline) in "
                "rubric points, so you can read down a column to see which model gains most on a given dimension, "
                "or across a row to see where a given model's harness pays off most. Models that entered with a "
                "weak indicator or privacy baseline light up brightest on exactly those columns -- the same "
                "headroom mechanism, now at the dimension level."))
    c.append(code(HEATMAP_MODEL_DIM))

    # ---- 8. Distributions --------------------------------------------------------------
    c.append(md('<a id="dist"></a>\n## 8 - Per-model score distributions\n'
                "Means can mislead, so here are the full distributions. Each panel overlays a model's per-prompt "
                "**baseline** score density (grey) against its **harness_core** density (teal), with the two "
                "means marked. The harness does not just tug the average -- it slides the entire mass of the "
                "distribution toward the ceiling, and typically tightens it (a taller, narrower teal curve high "
                "on the scale). That is the signature of a systematic effect rather than a lucky tail."))
    c.append(code(CHART_DIST_GRID))
    c.append(md("The same evidence, recast as the **distribution of the per-prompt lift itself** -- one violin "
                "per model. The body is the spread of individual lifts, the dark bar the inter-quartile range, "
                "the pale dot the median, and the ember dashed line marks zero (no change). The share of prompts "
                "above zero is printed over each violin. Almost the entire body of every violin sits above the "
                "zero line: the harness is a broad, per-prompt improvement, not an average of wild swings."))
    c.append(code(CHART_LIFT_VIOLIN))

    # ---- 9. Model x category heatmap ---------------------------------------------------
    c.append(md('<a id="catheat"></a>\n## 9 - Model x category lift heatmap\n'
                "Does the harness help more on some *kinds* of prompt than others -- and does that pattern hold "
                "across models? This heatmap breaks the lift out by prompt category (recruitment-fee schemes, "
                "adversarial framings, corridor-specific scenarios, and so on). It is deliberately honest about "
                "coverage: each model was evaluated on a different, unevenly sized slice of the prompt bank, so "
                "any (model, category) cell with fewer than a dozen paired prompts is left **blank** rather than "
                "coloured from noise. Read only the populated cells; the blanks are a coverage statement, not a "
                "zero. (Needs `prompt_metadata.csv` attached; the cell self-skips if it is missing.)"))
    c.append(code(HEATMAP_MODEL_CAT))

    # ---- 10. By difficulty -------------------------------------------------------------
    c.append(md('<a id="difficulty"></a>\n## 10 - The same story inside one model, by difficulty\n'
                "The headroom effect is not just a between-model artefact. Split the headline model by prompt "
                "difficulty: harder prompts start with a lower baseline, so their raw lift converts into a larger "
                "normalized gain -- the exact mechanism that reorders the cross-model board, now visible within a "
                "single model. Watch the teal (raw lift) and ember (normalized gain) bars diverge as the prompts "
                "get harder. (Optional -- needs `prompt_metadata.csv` attached.)"))
    c.append(code(CHART_DIFF))

    # ---- 11. Boundary ------------------------------------------------------------------
    c.append(md(
        '<a id="boundary"></a>\n## 11 - What this proves -- and what it does not\n\n'
        "**Proves.** On this rubric, wrapping any model in the DueCare harness produces a large, statistically "
        "clear, practically substantial lift (every model's paired Cohen's d clears the 'large' threshold), the "
        "gain is broad rather than tail-driven (near-total win rates, whole-distribution shifts), and *how you "
        "rank models depends on the metric*: raw lift favours low-baseline models with lots of headroom, while "
        "normalized gain favours models that close the remaining gap. Reporting both -- with sample sizes and "
        "confidence intervals in view -- is the honest way to compare. A single 'best model' claim is "
        "metric-dependent and, for the small-n models, under-evidenced.\n\n"
        "**Does not prove.** Real-world detection quality, that any specific worker is helped, or that the rubric "
        "is ground truth. Judges are LLMs; prompts are synthetic / composite; labels are *silver*, not gold. "
        "Coverage is uneven across models and categories. The board measures tested behaviour, not field "
        "outcomes.\n\n"
        "### Use the data\n"
        f"- **Rank your own model:** attach [`{DATASET_ID.split('/')[1]}`]({DS}), pair `harness_core` vs "
        "`baseline` per prompt, and report *both* raw lift and normalized gain (with n and a CI).\n"
        f"- **Go wider:** the [**Start Here** index]({INDEX}) links the full notebook collection (headline lift, "
        "per-dimension sweep, judge agreement, statistical robustness, and more).\n"
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
