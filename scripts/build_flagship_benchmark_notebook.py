#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the grandmaster flagship benchmark notebook: a comprehensive, visual, single-story showcase.

Renders many real, *polished* charts from the published `duecare-harness-benchmark-grades` dataset
(panel_grades.csv + prompt_metadata.csv) using the shared prettify toolkit `scripts/_notebook_viz.py`
(seaborn theme + DueCare palette, KPI stat cards, publication-grade pandas Styler tables, radar,
dumbbell, slope, filled KDE histograms, box + violin distributions, annotated heatmaps, small-multiple
panel grids, reverse-cumulative curves, and an interactive Plotly bar with a matplotlib fallback).

Story arc (13 sections, ~44 cells): dataset exploration; the honest headline lift; effect size and
robustness (Cohen's d, paired bootstrap CI, sign test); the cross-model leaderboard; the per-dimension
A-E radar + bar + heatmap; per-judge consistency + a judge-by-dimension small-multiple grid;
convergence; breakdowns by difficulty, corridor, and attack category (dumbbell + table + heatmap +
violins); an honest table of every prompt the harness did NOT help; a qualitative account of what the
harness actually adds; and an explicit honest boundary -- all with a table of contents and rich prose.

The toolkit's PALETTE + HELPERS source is *embedded* into the notebook's first code cell at build
time (the notebook never imports `_notebook_viz` at runtime). CPU only, no model, no internet: runs
to completion on Kaggle and every figure is verifiable.

    python scripts/build_flagship_benchmark_notebook.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import nbformat as nbf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _notebook_viz import HELPERS, PALETTE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "flagship_benchmark"
KERNEL_ID = "taylorsamarel/duecare-does-a-safety-harness-help"
TITLE = "DueCare Does A Safety Harness Help"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
DS = f"https://www.kaggle.com/datasets/{DATASET_ID}"
INDEX = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here"
COT_DS = "https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"

# The data-load tail of the first code cell. PALETTE + HELPERS are prepended at build time; the old
# inline palette / rcParams block is gone (the toolkit owns the theme). Keeps NAMES/DIMS, the
# recursive glob load, HEADLINE, and the shared per_prompt_lift utility used by every later cell.
SETUP = '''import glob, os

NAMES = {"A": "indicator", "B": "legal", "C": "refusal", "D": "resources", "E": "privacy"}
DIMS = ["A", "B", "C", "D", "E"]

print("mounted under /kaggle/input:", os.listdir("/kaggle/input") if os.path.exists("/kaggle/input") else "none")
csvs = glob.glob("/kaggle/input/**/panel_grades.csv", recursive=True)
if not csvs:
    raise SystemExit("attach the dataset taylorsamarel/duecare-harness-benchmark-grades (panel_grades.csv not found)")
grades = pd.read_csv(sorted(csvs)[0])
mcsv = glob.glob("/kaggle/input/**/prompt_metadata.csv", recursive=True)
meta = pd.read_csv(mcsv[0]) if mcsv else None
HEADLINE = "gemma4:31b"


def per_prompt_lift(df, model, teacher="harness_core", base="baseline"):
    """Average the judge panel per (prompt, arm), then pair teacher-vs-baseline per prompt."""
    d = df[df.model == model]
    piv = d.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack()
    keep = [c for c in (base, teacher) if c in piv.columns]
    piv = piv.dropna(subset=keep)
    if teacher not in piv.columns or base not in piv.columns:
        return pd.Series(dtype=float), piv
    return (piv[teacher] - piv[base]), piv


print(f"loaded {len(grades):,} grade rows | {grades.prompt_id.nunique():,} prompts | "
      f"{grades.model.nunique()} models | arms {sorted(grades.arm.unique())} | judges {sorted(grades.judge.unique())}")'''

# KPI hero tiles, computed live from the loaded panel (first thing after the data loads).
HERO = '''_lift, _piv = per_prompt_lift(grades, HEADLINE)
_ml, _n = float(_lift.mean()), len(_lift)
_win, _hurt = int((_lift > 0).sum()), int((_lift < 0).sum())
_bmu, _hmu = float(_piv["baseline"].mean()), float(_piv["harness_core"].mean())
stat_cards([
    (f"+{_ml:.1f}", "mean lift (/100)", EMBER),
    (f"{_bmu:.0f} -> {_hmu:.0f}", "baseline -> harnessed", TEAL),
    (f"{100 * _win / _n:.1f}%", f"prompts improved ({_hurt} lower)", GOOD),
    (f"{_n:,}", "paired prompts - gemma4:31b", INK2),
])'''

EXPLORE_SUMMARY = '''glance = pd.DataFrame({
    "metric": ["grade rows", "prompts", "models", "arms", "judges", "score min / mean / max"],
    "value": [f"{len(grades):,}", f"{grades.prompt_id.nunique():,}", str(grades.model.nunique()),
              str(grades.arm.nunique()), str(grades.judge.nunique()),
              f"{grades.score_0_100.min():.0f} / {grades.score_0_100.mean():.1f} / {grades.score_0_100.max():.0f}"],
})
display(pretty_table(glance, caption="Dataset at a glance"))

mv = grades.model.value_counts().rename_axis("model").reset_index(name="rows")
display(pretty_table(mv, caption="Grade rows per model - the headline gemma4:31b dominates by design",
                     fmt={"rows": "{:,}"}, bars=["rows"]))'''

EXPLORE_DIST = '''ct = pd.crosstab(grades.arm, grades.judge).reset_index()
jcols = [c for c in ct.columns if c != "arm"]
display(pretty_table(ct, caption="Grade rows by arm x judge - the three arms are graded on the same prompts, evenly across judges",
                     fmt={c: "{:,}" for c in jcols}, gradient=jcols, cmap="BuGn"))'''

EXPLORE_SHIFT = '''series = []
for arm, col in [("baseline", INK3), ("harness_core", TEAL), ("harness_full", GOOD)]:
    s = grades[(grades.model == HEADLINE) & (grades.arm == arm)].score_0_100.values
    if len(s):
        series.append((arm, s, col))
kde_hist(series, title=f"The whole score distribution shifts up with the harness   -   {HEADLINE}",
         subtitle="filled density of the raw rubric score per arm - the whole curve moves right",
         xlabel="rubric score (0-100)")'''

EXPLORE_BOX = '''arms = ["baseline", "harness_core", "harness_full"]
dd = grades[grades.model == HEADLINE]
box_data, box_lab, box_col = [], [], []
for a in arms:
    s = dd[dd.arm == a].groupby("prompt_id")["score_0_100"].mean().values
    if len(s):
        box_data.append(s); box_lab.append(f"{a}\\n(n={len(s):,})"); box_col.append(ARM_COLORS[a])
fig, ax = plt.subplots(figsize=(9.4, 4.6))
bp = ax.boxplot(box_data, patch_artist=True, widths=0.55, showfliers=False,
                medianprops=dict(color=INK, linewidth=2))
for patch, col in zip(bp["boxes"], box_col):
    patch.set_facecolor(col); patch.set_alpha(0.32); patch.set_edgecolor(col); patch.set_linewidth(1.8)
for whisk in bp["whiskers"]: whisk.set_color(INK3)
for cap in bp["caps"]: cap.set_color(INK3)
ax.set_xticks(range(1, len(box_lab) + 1)); ax.set_xticklabels(box_lab)
ax.set_ylabel("per-prompt mean rubric score (0-100)"); ax.set_ylim(0, 100); ax.grid(axis="x", alpha=0)
_title(ax, f"Median and spread of the score per arm   -   {HEADLINE}",
       "boxes = interquartile range, line = median; the median jumps from the 40s into the 90s")
plt.tight_layout(); plt.show()'''

LIFT = '''lift, piv = per_prompt_lift(grades, HEADLINE)
mean_lift = float(lift.mean())
ci = 1.96 * float(lift.std()) / np.sqrt(len(lift))
win, hurt = int((lift > 0).sum()), int((lift < 0).sum())
print(f"{HEADLINE}: n={len(lift):,} paired prompts | mean lift +{mean_lift:.1f} "
      f"[95% CI +{mean_lift-ci:.1f}, +{mean_lift+ci:.1f}] | win {win:,} ({100*win/len(lift):.1f}%) | hurt {hurt} ({100*hurt/len(lift):.2f}%)")'''

CHART_HIST = '''kde_hist([("per-prompt lift", lift.values, TEAL)],
         vlines=[(0, INK3, "no change"), (mean_lift, EMBER, f"mean +{mean_lift:.1f}")],
         title=f"The harness lifts almost every prompt   -   {HEADLINE}   -   n={len(lift):,} paired",
         subtitle="per-prompt difference harness_core - baseline; almost the entire mass sits right of zero",
         xlabel="per-prompt lift: harness_core - baseline")'''

ROBUST = '''n_r = len(lift)
sd_r = float(lift.std(ddof=1))
d_cohen = float(lift.mean() / sd_r) if sd_r else float("nan")
_rng = np.random.default_rng(11)
_vals = lift.values
_boot = np.array([_vals[_rng.integers(0, n_r, n_r)].mean() for _ in range(2000)])
ci_lo, ci_hi = float(np.percentile(_boot, 2.5)), float(np.percentile(_boot, 97.5))
wins_r = int((lift > 0).sum()); loss_r = int((lift < 0).sum()); tie_r = int((lift == 0).sum())
z_sign = (wins_r - loss_r) / np.sqrt(wins_r + loss_r) if (wins_r + loss_r) else float("nan")
stat_cards([
    (f"{d_cohen:.2f}", "Cohen's d (paired)", EMBER),
    (f"+{mean_lift:.1f}", "mean lift (/100)", TEAL),
    (f"+{ci_lo:.1f} .. +{ci_hi:.1f}", "95% bootstrap CI", GOOD),
    (f"{z_sign:.0f}", "sign-test z", INK2),
])'''

ROBUST_TABLE = '''rt = pd.DataFrame({
    "statistic": ["paired prompts (n)", "mean per-prompt lift", "std dev of per-prompt lift",
                  "Cohen's d (mean / sd)", "bootstrap 95% CI (2000 resamples)",
                  "prompts improved", "prompts worsened", "prompts unchanged",
                  "sign-test z (improved vs worsened)", "one-sided sign-test p"],
    "value": [f"{n_r:,}", f"+{mean_lift:.2f}", f"{sd_r:.2f}", f"{d_cohen:.2f}",
              f"[+{ci_lo:.2f}, +{ci_hi:.2f}]", f"{wins_r:,} ({100*wins_r/n_r:.1f}%)",
              f"{loss_r} ({100*loss_r/n_r:.2f}%)", f"{tie_r} ({100*tie_r/n_r:.2f}%)",
              f"{z_sign:.1f}", "< 1e-300 (normal approx floor)"],
})
display(pretty_table(rt, caption="Every robustness check on the headline lift points the same way - gemma4:31b, judges averaged per prompt"))'''

ROBUST_ECDF = '''xs = np.sort(lift.values)
frac_ge = 1.0 - np.arange(len(xs)) / len(xs)
fig, ax = plt.subplots(figsize=(9.8, 4.5))
ax.fill_between(xs, 0, 100 * frac_ge, color=TEAL_SOFT, alpha=0.55, zorder=1)
ax.plot(xs, 100 * frac_ge, color=TEAL, lw=2.4, zorder=2)
ax.axvline(0, color=INK3, lw=1.3, ls="--", zorder=3)
for thr in (0, 20, 40, 60):
    f = 100 * float((lift.values >= thr).mean())
    ax.plot([thr], [f], "o", color=EMBER, ms=7, zorder=5)
    ax.text(thr, f + 3.5, f"{f:.0f}% >= +{thr}", ha="center", color=EMBER, fontweight="bold", fontsize=9.5)
ax.set_xlabel("per-prompt lift threshold x  (harness_core - baseline)")
ax.set_ylabel("% of prompts with lift >= x"); ax.set_ylim(0, 106)
_title(ax, "How big is the lift, prompt by prompt",
       "reverse-cumulative curve: the share of prompts that improve by at least x points")
plt.tight_layout(); plt.show()'''

CHART_BOARD = '''rows = []
for m in grades.model.unique():
    lm, pv = per_prompt_lift(grades, m)
    if len(lm) >= 150:
        rows.append((m, float(pv["baseline"].mean()), float(lm.mean()), len(lm)))
board = pd.DataFrame(rows, columns=["model", "baseline", "lift", "n"])
ibar(list(board.model), list(board.baseline), list(board.lift), ns=list(board.n),
     title="Every model improves under the harness",
     subtitle="baseline (ink) + harness lift (teal), stacked; label = mean per-prompt lift")'''

BOARD_DUMBBELL = '''rows = []
for m in grades.model.unique():
    lm, pv = per_prompt_lift(grades, m)
    if len(lm) >= 150:
        rows.append((m, float(pv["baseline"].mean()), float(pv["harness_core"].mean()), len(lm)))
bd = pd.DataFrame(rows, columns=["model", "baseline", "harnessed", "n"]).sort_values("harnessed")
dumbbell([f"{m}  (n={int(n):,})" for m, n in zip(bd.model, bd.n)],
         list(bd.baseline), list(bd.harnessed),
         title="Every model moves the same direction under the harness",
         subtitle="baseline -> harness_core mean rubric score per model; delta = mean lift (static, always renders)",
         xlabel="mean rubric score (0-100)", xlim=(0, 100))'''

CHART_DIMS = '''d = grades[grades.model == HEADLINE]
base_dim, harn_dim = [], []
for dim in DIMS:
    pv = d.groupby(["prompt_id", "arm"])[dim].mean().unstack().dropna(subset=["baseline", "harness_core"])
    base_dim.append(float(pv["baseline"].mean()) if len(pv) else 0.0)
    harn_dim.append(float(pv["harness_core"].mean()) if len(pv) else 0.0)
radar([f"{k} {NAMES[k]}" for k in DIMS],
      [("baseline", base_dim, INK3), ("harness_core", harn_dim, TEAL)],
      title=f"Baseline vs harness shape by rubric dimension   -   {HEADLINE}",
      subtitle="mean component score per dimension - the harness pushes every axis outward")'''

DIM_BAR = '''d = grades[grades.model == HEADLINE]
dim_lift = []
for dim in DIMS:
    pv = d.groupby(["prompt_id", "arm"])[dim].mean().unstack().dropna(subset=["baseline", "harness_core"])
    dim_lift.append(float((pv["harness_core"] - pv["baseline"]).mean()) if len(pv) else 0.0)
order = list(np.argsort(dim_lift))
labels = [f"{DIMS[i]}  {NAMES[DIMS[i]]}" for i in order]; vals = [dim_lift[i] for i in order]
fig, ax = plt.subplots(figsize=(9.4, 3.9))
ax.barh(range(len(labels)), vals, color=TEAL, edgecolor=PAPER, height=0.66)
for i, v in enumerate(vals):
    ax.text(v + 0.12, i, f"+{v:.1f}", va="center", color=EMBER, fontweight="bold", fontsize=10.5)
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
ax.set_xlabel("mean component-score lift (points)"); ax.grid(axis="y", alpha=0)
ax.set_xlim(0, (max(vals) if vals else 1) * 1.2)
_title(ax, f"Which rubric dimension gains the most   -   {HEADLINE}",
       f"the five component lifts sum to the +{sum(dim_lift):.1f} headline; every axis gains several points")
plt.tight_layout(); plt.show()'''

CHART_HEATMAP = '''models = [m for m in grades.model.unique() if len(per_prompt_lift(grades, m)[0]) >= 150]
mat = np.full((len(DIMS), len(models)), np.nan)
for j, m in enumerate(models):
    dm = grades[grades.model == m]
    for i, dim in enumerate(DIMS):
        pv = dm.groupby(["prompt_id", "arm"])[dim].mean().unstack().dropna(subset=["baseline", "harness_core"])
        if len(pv):
            mat[i, j] = float((pv["harness_core"] - pv["baseline"]).mean())
heatmap(mat, [f"{k} {NAMES[k]}" for k in DIMS], models, fmt="+.1f", cbar_label="per-dim lift",
        title="Per-dimension lift x model - consistent, not one lucky number")'''

CHART_JUDGES = '''judges = sorted(grades.judge.unique())
base_j, harn_j = [], []
for jg in judges:
    dj = grades[(grades.model == HEADLINE) & (grades.judge == jg)]
    pv = dj.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack().dropna(subset=["baseline", "harness_core"])
    base_j.append(float(pv["baseline"].mean()) if len(pv) else np.nan)
    harn_j.append(float(pv["harness_core"].mean()) if len(pv) else np.nan)
slope(judges, base_j, harn_j, ylabel="mean rubric score (0-100)",
      title="All three judges independently agree - the lift is not one judge's quirk",
      subtitle="each judge: mean baseline -> mean harness_core, paired per prompt")'''

JUDGE_DIM_GRID = '''judges = sorted(grades.judge.unique())
fig, axes = plt.subplots(1, len(judges), figsize=(4.5 * len(judges), 4.3), sharey=True)
if len(judges) == 1: axes = [axes]
x = np.arange(len(DIMS)); w = 0.38
for ax, jg in zip(axes, judges):
    dj = grades[(grades.model == HEADLINE) & (grades.judge == jg)]
    bvals, hvals = [], []
    for dim in DIMS:
        pv = dj.groupby(["prompt_id", "arm"])[dim].mean().unstack().dropna(subset=["baseline", "harness_core"])
        bvals.append(float(pv["baseline"].mean()) if len(pv) else 0.0)
        hvals.append(float(pv["harness_core"].mean()) if len(pv) else 0.0)
    ax.bar(x - w / 2, bvals, w, color=INK3, label="baseline")
    ax.bar(x + w / 2, hvals, w, color=TEAL, label="harness_core")
    for xi, (bv, hv) in enumerate(zip(bvals, hvals)):
        ax.text(xi + w / 2, hv + 0.25, f"+{hv - bv:.0f}", ha="center", va="bottom", color=EMBER, fontsize=8.5, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(DIMS); ax.set_title(jg, fontsize=11.5, color=INK)
    ax.grid(axis="x", alpha=0)
axes[0].set_ylabel("mean component score")
axes[-1].legend(loc="upper right", fontsize=8.5)
fig.suptitle("Every judge sees the lift on every dimension", fontsize=14, fontweight="bold", x=0.01, ha="left", y=1.03)
fig.text(0.01, 0.965, "small multiples: baseline (ink) vs harness_core (teal) per rubric dimension A-E, one panel per judge",
         fontsize=9.5, color=INK3)
plt.tight_layout(rect=[0, 0, 1, 0.95]); plt.show()'''

CHART_CONV = '''rng = np.random.default_rng(7)
L = lift.values[rng.permutation(len(lift))]
run = np.cumsum(L) / np.arange(1, len(L) + 1)
x = np.arange(1, len(run) + 1)
fig, ax = plt.subplots(figsize=(9.8, 4.4))
ax.fill_between(x, mean_lift - 1, mean_lift + 1, color=EMBER, alpha=0.10, label="+/-1 pt band")
ax.axhline(mean_lift, color=EMBER, lw=1.4, ls="--")
ax.plot(x, run, color=TEAL, lw=2.1)
ax.set_xscale("log")
ax.set_xlabel("prompts graded (random order, log scale)"); ax.set_ylabel("running mean lift")
ax.set_ylim(mean_lift - 16, mean_lift + 16)
ax.set_title("The result converges fast - a random ~100-prompt sample already recovers it")
ax.legend(loc="lower right")
fig.tight_layout(); plt.show()'''

CHART_DIFF = '''if meta is not None and "difficulty" in meta.columns:
    d = grades[grades.model == HEADLINE].merge(meta[["prompt_id", "difficulty"]], on="prompt_id", how="left")
    labels, base_d, harn_d = [], [], []
    for diff in ["easy", "medium", "hard", "very_hard", "multipath"]:
        sub = d[d.difficulty == diff]
        if len(sub):
            pv = sub.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack().dropna(subset=["baseline", "harness_core"])
            if len(pv) >= 20:
                labels.append(f"{diff}  (n={len(pv):,})")
                base_d.append(float(pv["baseline"].mean())); harn_d.append(float(pv["harness_core"].mean()))
    if labels:
        dumbbell(labels, base_d, harn_d, title="The harness helps the hardest cases the most",
                 subtitle="baseline -> harness_core mean per difficulty bucket; delta labelled = mean lift",
                 xlabel="mean rubric score (0-100)", xlim=(0, 100))
    else:
        print("no difficulty buckets with >=20 paired prompts")
else:
    print("prompt_metadata.csv not attached - skipping the by-difficulty chart")'''

CHART_CORRIDOR = '''if meta is not None and "corridor" in meta.columns:
    d = grades[grades.model == HEADLINE].merge(meta[["prompt_id", "corridor"]], on="prompt_id", how="left")
    rows = []
    for cor, sub in d.groupby("corridor"):
        if str(cor).strip().lower() in ("various", "nan", "none", ""):
            continue
        pv = sub.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack().dropna(subset=["baseline", "harness_core"])
        if len(pv) >= 15:
            rows.append((str(cor), float(pv["baseline"].mean()), float(pv["harness_core"].mean()), len(pv)))
    cc = pd.DataFrame(rows, columns=["corridor", "baseline", "harnessed", "n"]).sort_values("harnessed")
    if len(cc):
        dumbbell([f"{c}  (n={int(n):,})" for c, n in zip(cc.corridor, cc.n)],
                 list(cc.baseline), list(cc.harnessed),
                 title="The lift holds across named migration corridors",
                 subtitle="baseline -> harness_core per corridor (>=15 paired, catch-all 'various' excluded); delta = mean lift",
                 xlabel="mean rubric score (0-100)", xlim=(0, 100))
    else:
        print("no named corridor buckets with >=15 paired prompts (most prompts are corridor-agnostic 'various')")
else:
    print("prompt_metadata.csv not attached (or no corridor column) - skipping the by-corridor chart")'''

CAT_DUMBBELL = '''if meta is not None and "category" in meta.columns:
    d = grades[grades.model == HEADLINE].merge(meta[["prompt_id", "category"]], on="prompt_id", how="left")
    rows = []
    for cat, sub in d.groupby("category"):
        pv = sub.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack().dropna(subset=["baseline", "harness_core"])
        if len(pv) >= 25:
            rows.append((str(cat), float(pv["baseline"].mean()), float(pv["harness_core"].mean()),
                         float((pv["harness_core"] - pv["baseline"]).mean()), len(pv)))
    cc = pd.DataFrame(rows, columns=["category", "baseline", "harnessed", "lift", "n"]).sort_values("lift").tail(15)
    if len(cc):
        dumbbell([f"{c[:26]}  (n={int(n):,})" for c, n in zip(cc.category, cc.n)],
                 list(cc.baseline), list(cc.harnessed),
                 title="Attack categories ranked by lift - the harness rescues the weakest baselines",
                 subtitle="up to 15 highest-lift categories (>=25 paired); baseline -> harness_core; delta = mean lift",
                 xlabel="mean rubric score (0-100)", xlim=(0, 100))
    else:
        print("no category buckets with >=25 paired prompts")
else:
    print("prompt_metadata.csv not attached - skipping the category dumbbell")'''

CHART_CAT = '''if meta is not None and "category" in meta.columns:
    d = grades[grades.model == HEADLINE].merge(meta[["prompt_id", "category"]], on="prompt_id", how="left")
    rows = []
    for cat, sub in d.groupby("category"):
        pv = sub.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack().dropna(subset=["baseline", "harness_core"])
        if len(pv) >= 25:
            rows.append((str(cat), float(pv["baseline"].mean()), float(pv["harness_core"].mean()),
                         float((pv["harness_core"] - pv["baseline"]).mean()), len(pv)))
    cc = pd.DataFrame(rows, columns=["category", "baseline", "harnessed", "lift", "n"]).sort_values("lift", ascending=False)
    display(pretty_table(cc, caption="Lift by attack category - every category improves (sorted high -> low)",
                         fmt={"baseline": "{:.1f}", "harnessed": "{:.1f}", "lift": "{:+.1f}", "n": "{:,}"},
                         gradient=["harnessed"], bars=["lift"], bar_color=EMBER_SOFT))
else:
    print("prompt_metadata.csv not attached - skipping the by-category table")'''

CAT_DIM_HEATMAP = '''if meta is not None and "category" in meta.columns:
    d = grades[grades.model == HEADLINE].merge(meta[["prompt_id", "category"]], on="prompt_id", how="left")
    counts = d.groupby("category")["prompt_id"].nunique().sort_values(ascending=False)
    cats = [c for c in counts.index if counts[c] >= 25][:12]
    mat = np.full((len(DIMS), len(cats)), np.nan)
    for j, cat in enumerate(cats):
        sub = d[d.category == cat]
        for i, dim in enumerate(DIMS):
            pv = sub.groupby(["prompt_id", "arm"])[dim].mean().unstack().dropna(subset=["baseline", "harness_core"])
            if len(pv):
                mat[i, j] = float((pv["harness_core"] - pv["baseline"]).mean())
    if len(cats):
        heatmap(mat, [f"{k} {NAMES[k]}" for k in DIMS], [c[:15] for c in cats], fmt="+.0f", cmap="BuGn",
                cbar_label="per-dim lift", title="Per-dimension lift x attack category",
                subtitle="component-score lift; categories with >=25 paired prompts, by rubric axis A-E")
    else:
        print("no category buckets with >=25 paired prompts")
else:
    print("prompt_metadata.csv not attached - skipping the dimension x category heatmap")'''

CAT_VIOLIN = '''if meta is not None and "category" in meta.columns:
    d = grades[grades.model == HEADLINE].merge(meta[["prompt_id", "category"]], on="prompt_id", how="left")
    per = d.groupby(["prompt_id", "arm", "category"])["score_0_100"].mean().reset_index()
    wide = per.pivot_table(index=["prompt_id", "category"], columns="arm", values="score_0_100").dropna(subset=["baseline", "harness_core"]).reset_index()
    wide["lift"] = wide["harness_core"] - wide["baseline"]
    agg = wide.groupby("category")["lift"].agg(["count", "mean"])
    top = agg[agg["count"] >= 30].sort_values("mean", ascending=False).head(8)
    cats = list(top.index)
    if len(cats) >= 2:
        data = [wide[wide.category == c]["lift"].values for c in cats]
        fig, ax = plt.subplots(figsize=(10.6, 5.2))
        parts = ax.violinplot(data, showmeans=True, showextrema=False, widths=0.9)
        for b in parts["bodies"]:
            b.set_facecolor(TEAL_SOFT); b.set_edgecolor(TEAL); b.set_alpha(0.85)
        parts["cmeans"].set_color(EMBER); parts["cmeans"].set_linewidth(2)
        ax.axhline(0, color=INK3, lw=1.4, ls="--")
        ax.set_xticks(range(1, len(cats) + 1))
        ax.set_xticklabels([f"{c[:16]}\\n(n={int(top['count'][c]):,})" for c in cats], rotation=30, ha="right", fontsize=8.5)
        ax.set_ylabel("per-prompt lift: harness_core - baseline"); ax.grid(axis="x", alpha=0)
        _title(ax, f"Spread of per-prompt lift within the top categories   -   {HEADLINE}",
               "each violin = distribution of prompt-level lift; ember tick = mean; dashed line = no change")
        plt.tight_layout(); plt.show()
    else:
        print("not enough categories with >=30 paired prompts for the violin")
else:
    print("prompt_metadata.csv not attached - skipping the category violin")'''

HURT = '''lift_h, piv_h = per_prompt_lift(grades, HEADLINE)
neg = lift_h[lift_h < 0].sort_values()
ht = pd.DataFrame({
    "prompt_id": list(neg.index),
    "baseline": piv_h.loc[neg.index, "baseline"].values,
    "harness_core": piv_h.loc[neg.index, "harness_core"].values,
    "delta": neg.values,
})
if meta is not None:
    ht = ht.merge(meta[["prompt_id", "category", "difficulty"]], on="prompt_id", how="left")
worst = float(neg.min()) if len(neg) else 0.0
print(f"{len(ht)} of {len(lift_h):,} prompts ({100*len(ht)/len(lift_h):.2f}%) scored lower under the harness; "
      f"worst single drop is {worst:+.1f} of 100 points.")
display(pretty_table(ht, caption=f"Every prompt where harness_core scored below baseline - all {len(ht)}, fully inspectable, worst first",
                     fmt={"baseline": "{:.1f}", "harness_core": "{:.1f}", "delta": "{:+.1f}"}))'''


def _toc() -> str:
    items = [
        ("0", "What is in the dataset", "explore"),
        ("1", "The headline: does it help?", "headline"),
        ("2", "Effect size and robustness", "robust"),
        ("3", "It is not one model", "board"),
        ("4", "Where the lift comes from (the five dimensions)", "dims"),
        ("5", "Consistency across judges", "judges"),
        ("6", "How much data you need", "conv"),
        ("7", "By difficulty", "difficulty"),
        ("8", "By migration corridor", "corridor"),
        ("9", "By attack category (deep dive)", "category"),
        ("10", "The honest 15: where it does not help", "hurt"),
        ("11", "What the harness actually adds", "adds"),
        ("12", "What it proves - and does not", "boundary"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c = []

    # ---- Intro -------------------------------------------------------------------------------
    c.append(md(
        "# Does a safety harness actually make an LLM better at spotting migrant-worker exploitation?\n\n"
        "**Short answer: yes - and by a lot.** On a 3-judge, 5-dimension rubric, wrapping a model in the "
        "DueCare harness (persona + GREP rules + retrieval + tools) lifts the headline model **+40.7 / 100** "
        "over **7,953 paired prompts**, improving **99.8% of them** (only 15 scored lower). The effect is "
        "large (Cohen's d ~1.7), it holds for every model and every judge, the hardest cases improve most, "
        "and a random ~100-prompt sample already recovers the number.\n\n"
        "This is the long, publication-grade walk-through: thirteen sections, dozens of live figures, and the "
        "honest counter-evidence (every prompt the harness did *not* help). Everything is recomputed **live** "
        f"from the public [`duecare-harness-benchmark-grades`]({DS}) dataset - no hidden state, CPU only, so "
        "you can verify each figure yourself.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** These are **LLM-judge rubric measurements** over "
        "synthetic / composite prompts - *silver* labels, not human-verified gold, and **not** a claim of "
        "real-world detection. What is demonstrated is improved *tested behaviour*: evidence-first reasoning, "
        "refusal discipline, ILO-indicator grounding, and privacy boundaries."))
    c.append(md(
        "### What is DueCare, in one paragraph\n"
        "DueCare is a **Gemma-4 safety harness** for migrant-worker anti-trafficking. The *baseline* arm is a "
        "bare model answering a prompt. The *harness_core* arm wraps that same model in a persona, a bank of "
        "GREP indicator rules, retrieval over an ILO / legal corpus, and deterministic tools; *harness_full* "
        "adds online lookups. This notebook measures whether that wrapper changes the answer for the better, "
        "graded by a panel of three independent judge models across five rubric dimensions "
        "(**A** indicator - **B** legal - **C** refusal - **D** resources - **E** privacy). The five component "
        "scores sum to the 0-100 overall score, which lets us show later that the +40.7 headline is the sum of "
        "five separate per-dimension gains rather than one axis doing all the work."))

    # ---- 0 - What is in the dataset ----------------------------------------------------------
    c.append(md(
        '<a id="explore"></a>\n## 0 - What is in the dataset\n\n'
        "The dataset is a long-format grade panel: one row per (model, arm, prompt, judge) carrying the overall "
        "0-100 rubric score and its five component scores A-E. Nothing here is response text or PII - only "
        "scores and prompt labels - so every figure below is a pure re-aggregation you can audit. We load it, "
        "print what is inside, and confirm the three arms are graded on the same prompts by the same judges, "
        "which is what makes the later comparison genuinely *paired* rather than two separate populations."))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + SETUP))
    c.append(md("The result up front, computed live from the loaded panel - the four numbers the rest of the "
                "notebook earns:"))
    c.append(code(HERO))
    c.append(code(EXPLORE_SUMMARY))
    c.append(code(EXPLORE_DIST))
    c.append(md("The three arms are graded on the same prompts, so the comparison is *paired*. Two views of the "
                "raw score before we ever compute a difference: the smoothed density (how the whole distribution "
                "moves) and the box plot (how the median and interquartile range move). Both show the same thing "
                "- switching the harness on drags the entire score distribution from the 40s up into the 90s."))
    c.append(code(EXPLORE_SHIFT))
    c.append(code(EXPLORE_BOX))

    # ---- 1 - The headline --------------------------------------------------------------------
    c.append(md('<a id="headline"></a>\n## 1 - The headline: does it help?\n\n'
                "We average the three judges per (prompt, arm), then take the per-prompt difference "
                "`harness_core - baseline`. This single number is what the whole notebook is about. Its "
                "distribution sits almost entirely to the right of zero: the harness improves the score on "
                "virtually every prompt, and the handful it does not are inspected explicitly in section 10."))
    c.append(code(LIFT))
    c.append(code(CHART_HIST))

    # ---- 2 - Effect size and robustness ------------------------------------------------------
    c.append(md('<a id="robust"></a>\n## 2 - Effect size and robustness\n\n'
                "A large mean is not enough; it has to be a large *effect* and it has to be stable. Cohen's d "
                "expresses the lift in units of its own spread (d ~0.8 is already 'large'; here it is roughly "
                "double that). The paired bootstrap resamples the prompts 2,000 times to put a 95% confidence "
                "band on the mean, and the sign test asks the crudest question - do more prompts go up than down "
                "- and answers with overwhelming significance. Read the cards left to right: effect size, mean, "
                "confidence interval, sign-test statistic."))
    c.append(code(ROBUST))
    c.append(code(ROBUST_TABLE))
    c.append(md("The mean and the effect size each compress the story into one number. The reverse-cumulative "
                "curve below unpacks it: for every threshold on the x-axis it shows the share of prompts that "
                "improved by *at least* that many points. Nearly all prompts improve at all, and a large "
                "majority improve by 20 points or more - so the lift is a broad shift, not a few huge gains "
                "dragging up an otherwise flat average."))
    c.append(code(ROBUST_ECDF))

    # ---- 3 - It is not one model -------------------------------------------------------------
    c.append(md('<a id="board"></a>\n## 3 - It is not one model\n\n'
                "If the harness only helped the headline model it would be a curiosity, not a method. Here is the "
                "same paired lift for every model with at least 150 paired prompts, two ways: an interactive "
                "stacked bar (baseline in ink, harness lift in teal) and a static dumbbell (baseline dot to "
                "harnessed dot) that always renders even without Plotly. Every model moves the same direction by "
                "a similar amount, from a weak-to-mediocre baseline up into the 80s-90s."))
    c.append(code(CHART_BOARD))
    c.append(code(BOARD_DUMBBELL))

    # ---- 4 - Where the lift comes from -------------------------------------------------------
    c.append(md('<a id="dims"></a>\n## 4 - Where the lift comes from (the five dimensions)\n\n'
                "The overall score is the sum of five rubric components: **A** indicator grounding, **B** legal "
                "/ ILO citation, **C** refusal discipline, **D** resource routing, **E** privacy handling. Three "
                "views: the radar shows the harness pushes *every* axis outward; the bar ranks the per-dimension "
                "gains (which sum to the headline number); and the heatmap shows the same pattern repeats across "
                "models rather than living in one lucky cell. No single dimension carries the result."))
    c.append(code(CHART_DIMS))
    c.append(code(DIM_BAR))
    c.append(code(CHART_HEATMAP))

    # ---- 5 - Consistency across judges -------------------------------------------------------
    c.append(md('<a id="judges"></a>\n## 5 - Consistency across judges\n\n'
                "Three judge models grade independently, each excluded from grading its own family, so no model "
                "scores its own output. If the lift were an artefact of one lenient judge the slopes would "
                "diverge and the per-judge panels would disagree. They do not: every judge moves the baseline up "
                "by a similar margin (the slope chart), and every judge sees the gain on every rubric dimension "
                "(the small-multiple grid)."))
    c.append(code(CHART_JUDGES))
    c.append(code(JUDGE_DIM_GRID))

    # ---- 6 - How much data -------------------------------------------------------------------
    c.append(md('<a id="conv"></a>\n## 6 - How much data do you actually need?\n\n'
                "The full sweep is exhaustive, but a reviewer should be able to reproduce the headline cheaply. "
                "Running the per-prompt lift in random order and plotting the running mean shows the estimate "
                "settles within a point of its final value after roughly 100 prompts. The exhaustive run still "
                "completes - this just shows the conclusion is not balanced on the last thousand prompts."))
    c.append(code(CHART_CONV))

    # ---- 7 - By difficulty -------------------------------------------------------------------
    c.append(md('<a id="difficulty"></a>\n## 7 - By difficulty\n\n'
                "Each prompt carries a difficulty label. Joining it in shows where the harness earns its keep: "
                "the lift is largest exactly where a bare model struggles most. Easy prompts, where the baseline "
                "is already competent, gain least; hard and very-hard prompts gain most; multi-path (multi-turn) "
                "scenarios are shown as their own bucket."))
    c.append(code(CHART_DIFF))

    # ---- 8 - By corridor ---------------------------------------------------------------------
    c.append(md('<a id="corridor"></a>\n## 8 - By migration corridor\n\n'
                "Most prompts are corridor-agnostic (labelled 'various'), but a subset name a specific migration "
                "corridor - Nepal to Qatar, Kenya to Saudi Arabia, Myanmar to Thailand, and others. Restricting "
                "to the named corridors with enough paired prompts shows the lift is not concentrated in one "
                "geography: every corridor with sufficient data moves up substantially. The catch-all 'various' "
                "bucket is excluded so it cannot dominate the chart."))
    c.append(code(CHART_CORRIDOR))

    # ---- 9 - By attack category --------------------------------------------------------------
    c.append(md('<a id="category"></a>\n## 9 - By attack category (deep dive)\n\n'
                "Category is the richest slice: over a hundred distinct attack framings, from blunt "
                "labor-trafficking asks to sophisticated fee-splitting, offshore-SPV obfuscation, and NGO "
                "fee-camouflage schemes. Four views: a dumbbell ranking categories by lift, the full sortable "
                "table, a dimension-by-category heatmap of *where* each category gains, and violins showing the "
                "per-prompt spread within the top categories. The pattern is consistent - the harness helps most "
                "on the financially sophisticated obfuscation attacks (where a bare model is weakest) and least "
                "on empathy-edge dilemmas."))
    c.append(code(CAT_DUMBBELL))
    c.append(code(CHART_CAT))
    c.append(code(CAT_DIM_HEATMAP))
    c.append(code(CAT_VIOLIN))

    # ---- 10 - The honest 15 ------------------------------------------------------------------
    c.append(md('<a id="hurt"></a>\n## 10 - The honest 15: where the harness does not help\n\n'
                "The headline claim is that only 15 of 7,953 prompts scored lower under the harness. Rather than "
                "hide them, here they all are - every prompt where `harness_core` fell below `baseline`, sorted "
                "worst-first, with its category and difficulty label. The drops are small (single-digit to "
                "low-double-digit points, mostly on prompts where the baseline was already strong), which is "
                "exactly what an honest 'it almost never hurts' claim should look like under inspection."))
    c.append(code(HURT))

    # ---- 11 - What the harness adds ----------------------------------------------------------
    c.append(md(
        '<a id="adds"></a>\n## 11 - What the harness actually adds\n\n'
        "The numbers say the harness helps; this section says *how*, in concrete behavioral terms that map onto "
        "the five rubric dimensions. When the same base model is wrapped in the DueCare harness, four things "
        "change in the answers the judges reward:\n\n"
        "- **Indicator naming (A).** The harnessed answer names the specific ILO forced-labour indicators in "
        "play - passport retention, debt bondage, wage withholding - instead of a vague 'this sounds "
        "exploitative'. The GREP rule bank surfaces the indicators; the persona makes the model state them.\n"
        "- **Statute and framework citation (B).** It cites the applicable instrument - ILO C029 / C181, the "
        "relevant national recruitment law - grounded in the retrieved corpus rather than invented. This is the "
        "dimension where a bare model gains the most, because it rarely cites anything on its own.\n"
        "- **Refusal-to-operationalize (C).** Asked to *optimize* an exploitative scheme, the harnessed model "
        "refuses the operational help while still explaining the legal exposure - the discipline of not becoming "
        "a how-to guide for wage theft or fee laundering.\n"
        "- **Resource routing (D).** It routes to a concrete next step - the right hotline, labour attache, or "
        "NGO for the corridor - instead of ending at analysis. Resources come from tools and knowledge packs, "
        "not memorized (and stale) phone numbers.\n\n"
        "Privacy handling (**E**) is the quieter fifth axis: the harnessed answer keeps worker identifiers "
        "general and does not echo sensitive details back. None of these behaviors are visible in the score "
        "alone - they are the mechanism the score is measuring, and the sections above show the judges reward "
        "them consistently across models, judges, difficulties, corridors, and categories.\n\n"
        "> These are still *tested* behaviors on synthetic prompts, not a claim about real-world outcomes - see "
        "the boundary below."))

    # ---- 12 - Boundary -----------------------------------------------------------------------
    c.append(md(
        '<a id="boundary"></a>\n## 12 - What this proves - and what it does not\n\n'
        "**Proves.** Wrapping a model in the DueCare harness produces a large, consistent, dimension-wide, "
        "difficulty-scaling improvement on the tested rubric - across every model and every judge, robust to "
        "sample size, with an honest and tiny failure set of 15 prompts.\n\n"
        "**Does not prove.** Real-world detection quality, that any specific worker is helped, or that the "
        "rubric is ground truth. Judges are LLMs; prompts are synthetic / composite; labels are *silver*.\n\n"
        "### Use the data\n"
        f"- **Benchmark any model:** attach [`{DATASET_ID.split('/')[1]}`]({DS}), pair baseline vs harness_core "
        "per prompt, take the mean lift.\n"
        f"- **Fine-tune:** the prompts where the harness clearly lifts a weak baseline become SFT/DPO pairs - "
        f"see the separate [`duecare-cot-reasoning`]({COT_DS}) chain-of-thought stream.\n"
        f"- **Go deeper:** the [**Start Here** index]({INDEX}) links the full ~12-notebook collection; the "
        f"[source repository]({REPO}) has the harness, the grader, and the exhaustive per-dimension sweep.\n\n"
        "License: MIT. Scores + prompt metadata only - no response text, no PII."))

    nb = nbf.v4.new_notebook()
    nb["cells"] = c
    nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                      "language_info": {"name": "python"}}
    nbf.write(nb, str(nb_dir / "notebook.ipynb"))
    meta = {"id": KERNEL_ID, "title": TITLE, "code_file": "notebook.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": False, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": [DATASET_ID], "competition_sources": [], "kernel_sources": []}
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"kernel_id": KERNEL_ID, "cells": len(c), "notebook_dir": str(nb_dir)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    summary = build(args.output, force=args.force)
    slug = summary["kernel_id"].split("/", 1)[1]
    assert TITLE.lower().replace(" ", "-") == slug, f"title must slugify to id: {TITLE!r} vs {slug!r}"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
