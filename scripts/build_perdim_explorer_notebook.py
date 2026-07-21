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

Every figure is recomputed live from the attached CSV with the shared DueCare
notebook prettify toolkit (scripts/_notebook_viz.py) -- KPI stat tiles, a radar
of the five rubric dimensions, a dumbbell of the per-dimension lift, filled
density histograms, a per-judge slope chart, and publication-grade Styler
tables. The toolkit's PALETTE + HELPERS are embedded into the first code cell so
the notebook is fully self-contained (no import of _notebook_viz at runtime).
CPU only, no GPU, no internet, no model: it runs to completion on Kaggle and is
verifiable.

    python scripts/build_perdim_explorer_notebook.py
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "perdim_explorer"
KERNEL_ID = "taylorsamarel/duecare-perdim-grades-explorer"
TITLE = "DueCare Perdim Grades Explorer"
DATASET_ID = "taylorsamarel/duecare-harness-perdim-grades"
DS = f"https://www.kaggle.com/datasets/{DATASET_ID}"
BATCHED_DS = "https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"

# ---- data load: recomputed live, recursive glob (never a hard-coded mount path) ----
# The OLD inline palette + rcParams are gone; the shared toolkit PALETTE now owns the
# theme and imports numpy / pandas / matplotlib, so this block only loads the data.
SETUP_DATA = '''import glob, os

# The published CSV flattens the five reasoned rubric dimensions to comp_A .. comp_E.
NAMES = {"comp_A": "indicator", "comp_B": "legal", "comp_C": "refusal", "comp_D": "resources", "comp_E": "privacy"}
DIMS = ["comp_A", "comp_B", "comp_C", "comp_D", "comp_E"]
DIM_LABELS = ["A indicator", "B legal", "C refusal", "D resources", "E privacy"]
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

# The paired-difference primitive: this is the DATA LOGIC and is preserved verbatim.
PAIRED = '''def paired(frame, model, col, teacher="harness_core", base="baseline"):
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
piv0 = paired(df, HEADLINE, "score_0_100")
mean_lift = float((piv0["harness_core"] - piv0["baseline"]).mean())

# KPI tiles -- the four numbers a reviewer should leave with.
stat_cards([(f"{n_rows:,}", "grade rows", INK2),
            (f"{n_prompts:,}", "prompts", TEAL),
            (f"~{pct:.1f}%", "of registry", WARN),
            (f"+{mean_lift:.1f}", "0-100 lift", EMBER)])

summary = pd.DataFrame({
    "metric": ["grade rows", "distinct prompts", "models", "arms", "judges", "score min / mean / max"],
    "value": [f"{n_rows:,}", f"{n_prompts:,}", str(df.model.nunique()), str(df.arm.nunique()),
              str(df.judge.nunique()),
              f"{df.score_0_100.min():.0f} / {df.score_0_100.mean():.1f} / {df.score_0_100.max():.0f}"],
})
display(pretty_table(summary, caption=f"What is in the dataset  --  interim snapshot, ~{pct:.1f}% of the {REGISTRY_PROMPTS:,}-prompt registry"))

by_arm = df.groupby("arm").size().rename("rows").reset_index()
display(pretty_table(by_arm, caption="Grade rows per arm (each prompt graded under every arm by each judge)", bars=["rows"]))

print(f"Interim snapshot: {n_prompts:,} distinct prompts ~ {pct:.1f}% of the {REGISTRY_PROMPTS:,}-prompt registry.")
print("This file grows and is RE-VERSIONED as the one-judge-call-per-dimension sweep runs; treat it as a")
print("representative random sample of the exhaustive grading, not the final full sweep.")
print("Judges on the panel:", sorted(df.judge.unique()))'''

BY_DIM = '''d = df[df.model == HEADLINE]
means = d.groupby("arm")[DIMS].mean()
series = []
if "baseline" in means.index:
    series.append(("baseline", [float(means.loc["baseline", dim]) for dim in DIMS], INK3))
if "harness_core" in means.index:
    series.append(("harness_core", [float(means.loc["harness_core", dim]) for dim in DIMS], TEAL))

# Five rubric dimensions -> a radar. Every spoke pushes outward under the harness.
radar(DIM_LABELS, series,
      title="Every rubric dimension rises with the harness",
      subtitle=f"mean component score, {HEADLINE}")

tbl = means.loc[[a for a in ["baseline", "harness_core", "harness_full"] if a in means.index], DIMS].round(1)
tbl.columns = DIM_LABELS
display(pretty_table(tbl.reset_index(), caption=f"Mean component score by arm  --  {HEADLINE}",
                     gradient=DIM_LABELS, fmt={c: "{:.1f}" for c in DIM_LABELS}))'''

DIM_LIFT = '''base_means, harn_means = [], []
for dim in DIMS:
    piv = paired(df, HEADLINE, dim)
    base_means.append(float(piv["baseline"].mean()))
    harn_means.append(float(piv["harness_core"].mean()))
n_pairs = len(paired(df, HEADLINE, "score_0_100"))

# Dumbbell: baseline dot -> harnessed dot; the labeled gap IS the per-dimension lift.
dumbbell(DIM_LABELS, base_means, harn_means, lo_lab="baseline", hi_lab="harness_core",
         title="Where the lift comes from, dimension by dimension",
         subtitle=f"{HEADLINE}  --  paired per-prompt means, n={n_pairs:,}",
         xlabel="mean component score (paired prompts)")
print("Per-dimension mean lift (harness_core - baseline):",
      {NAMES[dim]: round(h - b, 2) for dim, b, h in zip(DIMS, base_means, harn_means)})'''

OVERALL = '''piv = paired(df, HEADLINE, "score_0_100")
lift = (piv["harness_core"] - piv["baseline"]).to_numpy()
mean_lift = float(np.mean(lift))
ci = 1.96 * float(np.std(lift)) / np.sqrt(max(len(lift), 1))
win, hurt = int((lift > 0).sum()), int((lift < 0).sum())
print(f"{HEADLINE}: n={len(lift):,} paired prompts | mean 0-100 lift +{mean_lift:.1f} "
      f"[95% CI +{mean_lift - ci:.1f}, +{mean_lift + ci:.1f}] | improved {win:,} ({100 * win / max(len(lift), 1):.1f}%) | "
      f"regressed {hurt} ({100 * hurt / max(len(lift), 1):.2f}%)")

# Filled density of the per-prompt lift; the mass sits to the right of zero.
kde_hist([("per-prompt lift", lift, TEAL)],
         vlines=[(0, INK3, "no change"), (mean_lift, EMBER, f"mean +{mean_lift:.1f}")],
         title=f"Overall per-prompt lift on the 0-100 rubric  --  {HEADLINE}  --  n={len(lift):,} paired",
         xlabel="per-prompt lift: harness_core - baseline")'''

JUDGES = '''d = df[df.model == HEADLINE]
pivj = d.groupby(["judge", "arm"])["score_0_100"].mean().unstack()
keep = [c for c in ["baseline", "harness_core"] if c in pivj.columns]
pivj = pivj.dropna(subset=keep)
judges = list(pivj.index)
base = [float(pivj.loc[j, "baseline"]) for j in judges]
harn = [float(pivj.loc[j, "harness_core"]) for j in judges]

# Slope chart: one line per judge, baseline -> harnessed. Every line rises.
slope(judges, base, harn, left_lab="baseline", right_lab="harness_core",
      title="Every judge scores the harness higher",
      subtitle=f"mean 0-100 rubric score per judge, {HEADLINE}",
      ylabel="mean rubric score")

show = pivj.round(1)
arm_cols = [c for c in ["baseline", "harness_core", "harness_full"] if c in show.columns]
display(pretty_table(show.reset_index(), caption=f"Mean 0-100 score per judge x arm  --  {HEADLINE}",
                     gradient=arm_cols, fmt={c: "{:.1f}" for c in arm_cols}))'''

DIST = '''d = df[df.model == HEADLINE]
series = []
for arm, col in [("baseline", INK3), ("harness_core", TEAL), ("harness_full", GOOD)]:
    s = d[d.arm == arm].score_0_100.to_numpy()
    if len(s):
        series.append((arm, s, col))

# Overlaid densities of the whole 0-100 distribution -- the entire mass shifts up.
kde_hist(series,
         title=f"The whole score distribution shifts up with the harness  --  {HEADLINE}",
         subtitle="density of the 0-100 rubric score, per arm",
         xlabel="rubric score (0-100)")'''


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
                "honest census: a row of KPI tiles, then how many rows, distinct prompts, models, arms and "
                "judges, and what fraction of the full prompt registry this interim snapshot covers."))
    # First code cell: shared prettify toolkit (PALETTE + HELPERS) embedded, then the live data load.
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + SETUP_DATA))
    c.append(code(PAIRED))
    c.append(code(OVERVIEW))

    c.append(md('<a id="bydim"></a>\n## 1 - Per-dimension score by arm\n'
                f"For the headline model `gemma4:31b`, the mean of each reasoned sub-dimension "
                "(`comp_A .. comp_E`) under `baseline` vs `harness_core`, drawn as a **radar**. The five "
                "dimensions are the reasoned building blocks of the 0-100 score; every spoke pushes "
                "outward when the harness is on."))
    c.append(code(BY_DIM))

    c.append(md('<a id="dimlift"></a>\n## 2 - Per-dimension lift\n'
                "Now the *paired* view as a **dumbbell**: average each dimension per (prompt, arm), keep "
                "prompts present in both arms, and take the mean per-prompt difference "
                "`harness_core - baseline`. The labeled gap between the two dots **is** the per-dimension "
                "lift - it isolates exactly where the harness adds the most (typically the legal grounding, "
                "resource routing, and ILO-indicator dimensions a bare model neglects)."))
    c.append(code(DIM_LIFT))

    c.append(md('<a id="overall"></a>\n## 3 - The overall 0-100 lift\n'
                "The same paired difference on the overall `score_0_100`. The density of per-prompt lift "
                "sits almost entirely to the right of zero; the printed line reports the mean and a 95% "
                "confidence interval, and the ember line marks the mean."))
    c.append(code(OVERALL))

    c.append(md('<a id="judges"></a>\n## 4 - Do the judges agree?\n'
                "Three judge models grade independently (each excluded from grading its own family). If the "
                "lift were one lenient judge's artefact, the per-judge means would diverge. Here is the mean "
                "score per judge as a **slope chart** - every line rises from `baseline` to `harness_core`."))
    c.append(code(JUDGES))

    c.append(md('<a id="dist"></a>\n## 5 - Score distribution by arm\n'
                "Finally, the full shape: overlaid **densities** of the 0-100 score for the three arms. "
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
