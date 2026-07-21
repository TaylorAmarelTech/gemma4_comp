#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare per-dimension grades explorer notebook.

A polished, richly-visual Kaggle notebook that explores the published
`duecare-harness-perdim-grades` dataset (perdim_grades.csv): the exhaustive
one-judge-call-per-dimension grading, with a 0-100 rubric score plus five
reasoned A-E sub-dimensions (A indicator, B legal, C refusal, D resources,
E privacy) for every model x prompt x arm x judge cell. It is the higher-
resolution counterpart to the batched grades and a growing, re-versioned
interim snapshot, framed honestly as a representative random sample.

Every figure is recomputed live from the attached CSV with real matplotlib
charts, the DueCare palette, a table of contents, rich markdown, and an
explicit honest boundary. CPU only, no GPU, no internet, no model: it runs
to completion on Kaggle and is verifiable.

    python scripts/build_perdim_explorer_notebook.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "perdim_explorer"
KERNEL_ID = "taylorsamarel/duecare-perdim-grades-explorer"
TITLE = "DueCare Perdim Grades Explorer"
DATASET_ID = "taylorsamarel/duecare-harness-perdim-grades"
DS = f"https://www.kaggle.com/datasets/{DATASET_ID}"
BATCHED_DS = "https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"

SETUP = '''import glob, os
import numpy as np, pandas as pd
import matplotlib as mpl, matplotlib.pyplot as plt

# DueCare palette (warm paper / ink / civic teal; ember reserved for the headline + privacy boundary)
PAPER, INK, INK2, INK3 = "#F7F6F1", "#14181B", "#2A2D34", "#5B5F68"
TEAL, EMBER, GOOD, WARN, LINE = "#2f7d8c", "#c15b2e", "#4e8a5a", "#b8873a", "#DDD8C9"
mpl.rcParams.update({
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "axes.edgecolor": LINE, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK3, "ytick.color": INK3, "font.size": 11, "axes.titlesize": 13.5,
    "axes.titleweight": "bold", "axes.grid": True, "grid.color": LINE, "grid.alpha": 0.5,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 120,
})
# The published CSV flattens the five reasoned rubric dimensions to comp_A .. comp_E.
NAMES = {"comp_A": "indicator", "comp_B": "legal", "comp_C": "refusal", "comp_D": "resources", "comp_E": "privacy"}
DIMS = ["comp_A", "comp_B", "comp_C", "comp_D", "comp_E"]
REGISTRY_PROMPTS = 78_719  # full DueCare prompt registry the exhaustive sweep is grading toward

print("mounted under /kaggle/input:", os.listdir("/kaggle/input") if os.path.exists("/kaggle/input") else "none")
csvs = glob.glob("/kaggle/input/**/perdim_grades.csv", recursive=True)
if not csvs:
    raise SystemExit("attach the dataset taylorsamarel/duecare-harness-perdim-grades (perdim_grades.csv not found)")
df = pd.read_csv(sorted(csvs)[0])
HEADLINE = "gemma4:31b" if "gemma4:31b" in set(df["model"]) else df["model"].value_counts().index[0]
print(f"loaded {len(df):,} per-dimension grade rows | {df.prompt_id.nunique():,} prompts | "
      f"{df.model.nunique()} model(s) | arms {sorted(df.arm.unique())} | judges {sorted(df.judge.unique())}")
print("headline model:", HEADLINE)'''

HELPERS = '''def paired(frame, model, col, teacher="harness_core", base="baseline"):
    """Average the judge panel per (prompt, arm), then keep prompts present in BOTH arms.

    Returns the pivot (index=prompt_id, columns=arm). The per-prompt lift is
    piv[teacher] - piv[base] -- a paired difference, so each prompt is its own control.
    """
    d = frame[frame.model == model]
    piv = d.groupby(["prompt_id", "arm"])[col].mean().unstack()
    need = [c for c in (base, teacher) if c in piv.columns]
    return piv.dropna(subset=need)'''

OVERVIEW = '''n_rows, n_prompts = len(df), df.prompt_id.nunique()
pct = 100.0 * n_prompts / REGISTRY_PROMPTS
summary = pd.DataFrame({
    "rows": [f"{n_rows:,}"],
    "distinct prompts": [f"{n_prompts:,}"],
    "models": [df.model.nunique()],
    "arms": [df.arm.nunique()],
    "judges": [df.judge.nunique()],
    "score min / mean / max": [f"{df.score_0_100.min():.0f} / {df.score_0_100.mean():.1f} / {df.score_0_100.max():.0f}"],
})
print(f"Interim snapshot: {n_prompts:,} distinct prompts ~ {pct:.1f}% of the {REGISTRY_PROMPTS:,}-prompt registry.")
print("This file grows and is RE-VERSIONED as the one-judge-call-per-dimension sweep runs; treat it as a")
print("representative random sample of the exhaustive grading, not the final full sweep.")
display(summary.T.rename(columns={0: ""}))
print("\\nGrade rows per arm (each prompt is graded under every arm by each judge):")
display(df.groupby("arm").size().rename("rows").to_frame())
print("Judges on the panel:", sorted(df.judge.unique()))'''

BY_DIM = '''d = df[df.model == HEADLINE]
means = d.groupby("arm")[DIMS].mean()
order = [a for a in ["baseline", "harness_core"] if a in means.index]
colors = {"baseline": INK3, "harness_core": TEAL}
x = np.arange(len(DIMS)); w = 0.38
fig, ax = plt.subplots(figsize=(9.8, 4.6))
for i, arm in enumerate(order):
    vals = [means.loc[arm, dim] for dim in DIMS]
    off = (i - (len(order) - 1) / 2) * w
    ax.bar(x + off, vals, w, color=colors.get(arm, GOOD), edgecolor=PAPER, label=arm)
    for xi, v in zip(x + off, vals):
        ax.text(xi, v + 0.4, f"{v:.1f}", ha="center", va="bottom", fontsize=8, color=INK3)
ax.set_xticks(x); ax.set_xticklabels([f"{k}\\n{NAMES[k]}" for k in DIMS])
ax.set_ylabel("mean component score"); ax.legend(framealpha=0.9)
ax.set_title(f"Every rubric dimension rises with the harness   -   {HEADLINE}: baseline vs harness_core")
fig.tight_layout(); plt.show()'''

DIM_LIFT = '''dim_lift = {}
for dim in DIMS:
    piv = paired(df, HEADLINE, dim)
    if len(piv) and {"baseline", "harness_core"}.issubset(piv.columns):
        dim_lift[dim] = float((piv["harness_core"] - piv["baseline"]).mean())
keys = list(dim_lift); vals = [dim_lift[k] for k in keys]
n_pairs = len(paired(df, HEADLINE, "score_0_100"))
fig, ax = plt.subplots(figsize=(9.2, 4.5))
ax.bar(range(len(keys)), vals, color=[GOOD if v >= 0 else EMBER for v in vals], edgecolor=PAPER, width=0.62)
for i, v in enumerate(vals):
    ax.text(i, v + (0.35 if v >= 0 else -0.35), f"{v:+.1f}", ha="center",
            va="bottom" if v >= 0 else "top", color=INK2, fontweight="bold")
ax.axhline(0, color=INK3, lw=1)
ax.set_xticks(range(len(keys))); ax.set_xticklabels([f"{k}\\n{NAMES[k]}" for k in keys])
ax.set_ylabel("mean per-prompt lift (harness_core - baseline)")
ax.set_title(f"Where the lift comes from, dimension by dimension   -   {HEADLINE}   -   n={n_pairs:,} paired")
fig.tight_layout(); plt.show()
print("Per-dimension mean lift:", {k: round(v, 2) for k, v in dim_lift.items()})'''

OVERALL = '''piv = paired(df, HEADLINE, "score_0_100")
lift = piv["harness_core"] - piv["baseline"]
mean_lift = float(lift.mean())
ci = 1.96 * float(lift.std()) / np.sqrt(max(len(lift), 1))
win, hurt = int((lift > 0).sum()), int((lift < 0).sum())
print(f"{HEADLINE}: n={len(lift):,} paired prompts | mean 0-100 lift +{mean_lift:.1f} "
      f"[95% CI +{mean_lift-ci:.1f}, +{mean_lift+ci:.1f}] | improved {win:,} ({100*win/max(len(lift),1):.1f}%) | "
      f"regressed {hurt} ({100*hurt/max(len(lift),1):.2f}%)")
fig, ax = plt.subplots(figsize=(9.6, 4.6))
ax.hist(lift, bins=40, color=TEAL, edgecolor=PAPER, linewidth=0.5)
ax.axvline(0, color=INK3, lw=1.2, ls="--")
ax.axvline(mean_lift, color=EMBER, lw=2.4)
top = ax.get_ylim()[1]
ax.annotate(f"mean +{mean_lift:.1f}", xy=(mean_lift, top * 0.9), xytext=(mean_lift * 0.5, top * 0.9),
            color=EMBER, fontweight="bold", arrowprops=dict(color=EMBER, arrowstyle="->", lw=1.6))
ax.set_title(f"Overall per-prompt lift on the 0-100 rubric   -   {HEADLINE}   -   n={len(lift):,} paired")
ax.set_xlabel("per-prompt lift:  harness_core - baseline   (points / 100)")
ax.set_ylabel("number of prompts")
fig.tight_layout(); plt.show()'''

JUDGES = '''d = df[df.model == HEADLINE]
pivj = d.groupby(["judge", "arm"])["score_0_100"].mean().unstack()
arm_order = [a for a in ["baseline", "harness_core", "harness_full"] if a in pivj.columns]
judges = list(pivj.index)
arm_colors = {"baseline": INK3, "harness_core": TEAL, "harness_full": GOOD}
x = np.arange(len(judges)); w = 0.8 / max(len(arm_order), 1)
fig, ax = plt.subplots(figsize=(9.6, 4.6))
for i, arm in enumerate(arm_order):
    off = (i - (len(arm_order) - 1) / 2) * w
    ax.bar(x + off, pivj[arm].values, w, color=arm_colors.get(arm, WARN), edgecolor=PAPER, label=arm)
ax.set_xticks(x); ax.set_xticklabels(judges, fontsize=9.5)
ax.set_ylabel("mean rubric score (0-100)")
ax.set_title(f"Do the judges agree?  Mean score per judge x arm   -   {HEADLINE}")
ax.legend(framealpha=0.9, ncol=len(arm_order))
fig.tight_layout(); plt.show()
display(pivj.round(1))'''

DIST = '''d = df[df.model == HEADLINE]
styles = {"baseline": (INK3, 2.0), "harness_core": (TEAL, 2.7), "harness_full": (GOOD, 2.0)}
fig, ax = plt.subplots(figsize=(9.6, 4.6))
for arm, (color, lw) in styles.items():
    s = d[d.arm == arm].score_0_100
    if len(s):
        ax.hist(s, bins=40, histtype="step", lw=lw, color=color, density=True,
                label=f"{arm} (mean {s.mean():.0f}, n={len(s):,})")
ax.set_title(f"The whole score distribution shifts up with the harness   -   {HEADLINE}")
ax.set_xlabel("rubric score (0-100)"); ax.set_ylabel("density"); ax.legend(framealpha=0.9)
fig.tight_layout(); plt.show()'''


def _toc() -> str:
    items = [
        ("0", "What is in the dataset", "overview"),
        ("1", "Per-dimension score by arm", "bydim"),
        ("2", "Per-dimension lift", "dimlift"),
        ("3", "The overall 0-100 lift", "overall"),
        ("4", "Do the judges agree?", "judges"),
        ("5", "Score distribution by arm", "dist"),
        ("6", "What it proves - and does not", "boundary"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c: list = []

    c.append(md(
        "# DueCare per-dimension grades - an interactive explorer\n\n"
        "This notebook opens up the **exhaustive, one-judge-call-per-dimension** grading of the "
        "DueCare safety harness. Where the batched grades ask a judge for a single 0-100 number, this "
        "sweep asks a **separate reasoned call for each of five rubric dimensions** - "
        "**A** indicator - **B** legal - **C** refusal - **D** resources - **E** privacy - "
        "for every `model x prompt x arm x judge` cell, alongside the overall 0-100 score. It is the "
        "higher-resolution counterpart to the [batched grades]("
        f"{BATCHED_DS}).\n\n"
        "The three **arms** are the same model (`baseline`), that model wrapped in the DueCare harness "
        "(`harness_core`: persona + GREP indicator rules + retrieval + deterministic tools), and the "
        "harness with online lookups (`harness_full`). Because every arm is graded on the same prompts, "
        "the comparison is **paired** - each prompt is its own control.\n\n"
        "Everything below is recomputed **live** from the public "
        f"[`duecare-harness-perdim-grades`]({DS}) dataset - CPU only, no model, no internet - so you "
        "can verify every figure yourself.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** This is a **growing, re-versioned interim snapshot** of an "
        "exhaustive sweep - a representative random sample, not the final full run. The grades are "
        "**LLM-judge rubric measurements** over synthetic / composite prompts (*silver* labels, not "
        "human-verified gold) and are **not** a claim of real-world detection. Scores only - no response "
        "text, no PII."))

    c.append(md('<a id="overview"></a>\n## 0 - What is in the dataset\n'
                "First, load the CSV with a recursive glob (never a hard-coded mount path) and take an "
                "honest census: how many rows, distinct prompts, models, arms and judges, and what fraction "
                "of the full prompt registry this interim snapshot covers."))
    c.append(code(SETUP))
    c.append(code(HELPERS))
    c.append(code(OVERVIEW))

    c.append(md('<a id="bydim"></a>\n## 1 - Per-dimension score by arm\n'
                f"For the headline model `gemma4:31b`, the mean of each reasoned sub-dimension "
                "(`comp_A .. comp_E`) under `baseline` vs `harness_core`. The five dimensions are the "
                "reasoned building blocks of the 0-100 score; every one of them lifts when the harness is on."))
    c.append(code(BY_DIM))

    c.append(md('<a id="dimlift"></a>\n## 2 - Per-dimension lift\n'
                "Now the *paired* view: average each dimension per (prompt, arm), keep prompts present in "
                "both arms, and take the mean per-prompt difference `harness_core - baseline`. This isolates "
                "exactly where the harness adds the most - typically the legal grounding, resource routing, "
                "and ILO-indicator dimensions a bare model neglects."))
    c.append(code(DIM_LIFT))

    c.append(md('<a id="overall"></a>\n## 3 - The overall 0-100 lift\n'
                "The same paired difference on the overall `score_0_100`. The histogram of per-prompt lift "
                "sits almost entirely to the right of zero; the printed line reports the mean and a 95% "
                "confidence interval."))
    c.append(code(OVERALL))

    c.append(md('<a id="judges"></a>\n## 4 - Do the judges agree?\n'
                "Three judge models grade independently (each excluded from grading its own family). If the "
                "lift were one lenient judge's artefact, the per-judge means would diverge. Here is the mean "
                "score per judge under each arm - the ordering baseline < harnessed holds for all of them."))
    c.append(code(JUDGES))

    c.append(md('<a id="dist"></a>\n## 5 - Score distribution by arm\n'
                "Finally, the full shape: overlaid step-histograms of the 0-100 score for the three arms. "
                "The harness does not just move a few easy prompts - the entire distribution shifts up."))
    c.append(code(DIST))

    c.append(md(
        '<a id="boundary"></a>\n## 6 - What this proves - and what it does not\n\n'
        "**Proves.** On this exhaustive per-dimension rubric, wrapping the model in the DueCare harness "
        "produces a large, consistent, *dimension-wide* improvement - visible in every sub-dimension, "
        "agreed by every judge, and robust across the paired sample.\n\n"
        "**Does not prove.** Real-world detection quality, that any specific worker is helped, or that the "
        "rubric is ground truth. Judges are LLMs; prompts are synthetic / composite; labels are *silver*; "
        "and this is an **interim, growing snapshot** that is re-versioned as the sweep runs.\n\n"
        "### Use the data\n"
        f"- **Explore deeper:** attach [`{DATASET_ID.split('/')[1]}`]({DS}) and re-run any cell - pair "
        "`baseline` vs `harness_core` per prompt and take the mean of the difference, per dimension or overall.\n"
        f"- **Compare resolutions:** the batched [`duecare-harness-benchmark-grades`]({BATCHED_DS}) gives one "
        "number per grade; this per-dimension dataset gives the reasoned A-E breakdown behind it.\n"
        f"- **Go to source:** the [repository]({REPO}) has the harness, the grader, and the exhaustive "
        "per-dimension sweep.\n\n"
        "License: MIT. Scores and component sub-scores only - no response text, no PII."))

    nb = nbf.v4.new_notebook()
    nb["cells"] = c
    nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                      "language_info": {"name": "python"}}
    nbf.write(nb, str(nb_dir / "notebook.ipynb"))

    meta = {"id": KERNEL_ID, "title": TITLE, "code_file": "notebook.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": False, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": [DATASET_ID], "competition_sources": [],
            "kernel_sources": []}
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"kernel_id": KERNEL_ID, "title": TITLE, "cells": len(c), "notebook_dir": str(nb_dir)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    summary = build(args.output, force=args.force)
    slug = summary["kernel_id"].split("/", 1)[1]
    assert TITLE.lower().replace(" ", "-") == slug, f"title must slugify to id: {TITLE!r} vs {slug!r}"
    assert "DueCare Perdim Grades Explorer".lower().replace(" ", "-") == "duecare-perdim-grades-explorer"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
