# ruff: noqa: E501
"""Build the "How much of the benchmark do you actually need?" convergence notebook.

A grounded methodology contribution: shuffle the headline model's paired prompts with a fixed seed,
then watch the mean-lift estimate (with a bootstrap CI) and the category representativeness converge
as the random subsample grows. The estimate pins the full-panel value by a few hundred prompts --
which is exactly why the exhaustive per-dimension sweep can be read at any interim point (a shuffled
prefix is an unbiased random sample), and why randomized interim goals reduce the prompt COUNT, never
the grading resolution. Attaches to the public dataset taylorsamarel/duecare-harness-benchmark-grades.

    python scripts/build_convergence_kaggle.py
    python scripts/build_convergence_kaggle.py --execute-local --force
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "convergence_v1"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"

NB_INDEX = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here"
NB_ROBUST = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-statistical-robustness"
DS = "https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"
SITE = "https://duecare-ai.com/benchmark"


def _md(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "id": identifier, "metadata": {}, "source": source.splitlines(True)}


def _code(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "code", "execution_count": None, "id": identifier, "metadata": {}, "outputs": [], "source": source.splitlines(True)}


_SETUP = """import json, os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Markdown, display

COLORS = ["#136f63", "#f2b134", "#d1495b", "#247ba0", "#6d597a", "#4f772d"]
plt.rcParams.update({"figure.figsize": (11, 5.4), "figure.dpi": 115, "axes.facecolor": "#f7faf9",
                     "axes.edgecolor": "#bed2cc", "axes.grid": True, "grid.alpha": 0.2, "font.size": 11})

EXPECTED_DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"

def _verify_dataset(base):
    manifest = base / "release-manifest.json"
    if manifest.is_file():
        did = json.loads(manifest.read_text(encoding="utf-8")).get("dataset_id")
        if did and did != EXPECTED_DATASET_ID:
            return False
    return True

def find_dataset():
    bases = []
    if os.environ.get("DUECARE_GRADES_ROOT"):
        bases.append(Path(os.environ["DUECARE_GRADES_ROOT"]))
    bases += list(Path("/kaggle/input").glob("*")) + [Path.cwd()]
    seen = set()
    for base in bases:
        for cand in ([base] + list(base.rglob("panel_grades.csv"))):
            r = cand if cand.is_dir() else cand.parent
            if r in seen or not (r / "panel_grades.csv").is_file():
                continue
            seen.add(r)
            if _verify_dataset(r):
                return r
    raise FileNotFoundError(f"Attach {EXPECTED_DATASET_ID} (no matching dataset found)")

root = find_dataset()
grades = pd.read_csv(root / "panel_grades.csv")
prompts = pd.read_csv(root / "prompt_metadata.csv") if (root / "prompt_metadata.csv").is_file() else None

def headline_model():
    return "gemma4:31b" if "gemma4:31b" in set(grades["model"]) else grades["model"].value_counts().index[0]

in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
out_dir = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", "/kaggle/working" if in_kaggle else Path.cwd()))
out_dir.mkdir(parents=True, exist_ok=True)

head = headline_model()
mean = grades[grades.model == head].groupby(["prompt_id", "arm"], as_index=False)["score_0_100"].mean()
wide = mean.pivot_table(index="prompt_id", columns="arm", values="score_0_100").dropna(subset=["baseline", "harness_core"])
paired = wide.reset_index()
paired["lift"] = paired["harness_core"] - paired["baseline"]
FULL_LIFT = float(paired["lift"].mean())
display(Markdown(f"**`{head}`**: {len(paired):,} paired prompts, full-panel mean lift **{FULL_LIFT:+.1f}**. "
                 f"The rest of this notebook asks how few of those prompts you need to recover that number."))"""


def _notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:28px 32px;border-radius:16px;background:linear-gradient(120deg,#0e1116,#247ba0,#f2b134);color:white">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.85">DueCare | benchmark methodology</div>
<h1 style="margin:.3em 0 .25em;font-size:30px">How much of the benchmark do you actually need?</h1>
<p style="font-size:15px;line-height:1.55;margin:0;max-width:900px">The full sweep is 78,719 prompts x 3 arms x 3 judges x 5 dimensions -- millions of judge calls. This notebook shows that a <b>random</b> subsample of a few hundred prompts already recovers the full-panel lift, and that the estimate + its representativeness converge as the sample grows. That is the methodological justification for reading the exhaustive sweep at any interim point.</p>
</div>"""),
        _md("toc", """## Contents

- [1. Why this matters](#why)
- [2. The estimate converges](#converge)
- [3. Representativeness converges too](#rep)
- [4. What this justifies -- and does not](#boundary)

**Related in this collection:** the [Start Here index](""" + NB_INDEX + """) - the [grades dataset](""" + DS + """) - the [statistical-robustness notebook](""" + NB_ROBUST + """) - the [repo](""" + REPO + """) - the [site](""" + SITE + """)."""),
        _code("setup", _SETUP),
        _md("why-note", """<a id="why"></a>
## 1. Why this matters

Grading every prompt with a 3-judge, 5-dimension panel is expensive. If a random subsample recovers
the same answer, then (a) the exhaustive sweep can be *read early* -- a shuffled prefix is an unbiased
random sample -- and (b) "interim goals" can reduce the prompt **count** without touching the grading
**resolution**. This section makes that concrete on the published panel."""),
        _code("converge", """rng = np.random.default_rng(20260717)
order = rng.permutation(len(paired))
d = paired["lift"].to_numpy()[order]
Ns = [n for n in (50, 100, 200, 500, 1000, 2000, 5000, len(d)) if n <= len(d)]
rows = []
for n in Ns:
    sub = d[:n]
    boot = np.sort([np.mean(rng.choice(sub, size=n, replace=True)) for _ in range(1000)])
    rows.append({"N": n, "cum_lift": round(float(sub.mean()), 2),
                 "ci_low": round(float(boot[24]), 2), "ci_high": round(float(boot[974]), 2),
                 "abs_err_vs_full": round(abs(float(sub.mean()) - FULL_LIFT), 2)})
conv = pd.DataFrame(rows)
display(conv.style.format({"cum_lift": "{:+.2f}", "ci_low": "{:+.2f}", "ci_high": "{:+.2f}"}))
fig, ax = plt.subplots(figsize=(11, 5.4))
ax.fill_between(conv["N"], conv["ci_low"], conv["ci_high"], color=COLORS[3], alpha=0.18, label="95% CI")
ax.plot(conv["N"], conv["cum_lift"], "o-", color=COLORS[3], lw=2.2, label="random-subsample lift")
ax.axhline(FULL_LIFT, color=COLORS[0], ls="--", lw=1.8, label=f"full-panel lift {FULL_LIFT:+.1f}")
ax.set(title=f"The lift estimate converges early ({head})", xlabel="random subsample size (prompts)", ylabel="mean lift")
ax.set_xscale("log"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(out_dir / "convergence.png", bbox_inches="tight"); plt.show()
first = conv[conv["abs_err_vs_full"] <= 1.0]["N"].min()
display(Markdown(f"A random **{int(first):,}**-prompt subsample already lands within **1.0 point** of the "
                 f"full-panel lift ({FULL_LIFT:+.1f}); the CI keeps tightening but the point estimate is stable."))"""),
        _md("rep-note", """<a id="rep"></a>
## 2. Representativeness converges too

Convergence of the number is only trustworthy if the random subsample also *looks like* the full set.
Here the category distribution of the growing subsample is compared to the whole panel."""),
        _code("rep", """if prompts is not None and "category" in prompts.columns:
    cat = paired.merge(prompts[["prompt_id", "category"]], on="prompt_id", how="left")
    cats = cat["category"].to_numpy()[order]
    whole = pd.Series(cats).value_counts(normalize=True)
    rows = []
    for n in Ns:
        s = pd.Series(cats[:n]).value_counts(normalize=True)
        gap = max(abs(s.get(c, 0.0) - whole[c]) for c in whole.index) * 100
        rows.append({"N": n, "categories_seen": int(pd.Series(cats[:n]).nunique()),
                     "max_category_gap_pp": round(gap, 2)})
    rep = pd.DataFrame(rows)
    display(rep)
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(rep["N"], rep["max_category_gap_pp"], "o-", color=COLORS[2], lw=2.2)
    ax.set(title="Category-distribution gap vs the full panel shrinks with N", xlabel="random subsample size", ylabel="max category share gap (pp)")
    ax.set_xscale("log"); fig.tight_layout(); fig.savefig(out_dir / "representativeness.png", bbox_inches="tight"); plt.show()
else:
    display(Markdown("_prompt_metadata.csv with a `category` column was not attached; skipping the representativeness view._"))"""),
        _md("boundary", """<a id="boundary"></a>
## 3. What this justifies -- and what it does not

**Justifies:** reading the exhaustive per-dimension sweep at any interim point. Because the grading
order is seed-shuffled, a partial read is an unbiased random sample, and (as above) the estimate is
stable by a few hundred prompts. So "randomized interim goals" reduce the prompt **count**, never the
grading **resolution** -- every sampled prompt still gets all dimensions x all judges x all arms.

**Does not justify:** the claim that a small benchmark is *enough* in general. This is convergence of
one estimate on one panel; the tail categories, rare corridors, and per-dimension detail still need the
full sweep, and small-n reads have wider CIs. This is a statement about efficient *reading* of a large
benchmark, not a licence to shrink it. And as everywhere: these are rubric scores from an LLM judge
panel over synthetic/composite prompts -- not field detection."""),
    ]
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def _kernel_metadata() -> dict[str, Any]:
    return {
        "id": "taylorsamarel/duecare-benchmark-convergence",
        "title": "DueCare Benchmark Convergence",
        "code_file": "notebook.ipynb", "language": "python", "kernel_type": "notebook",
        "is_private": False, "enable_gpu": False, "enable_internet": False,
        "dataset_sources": [DATASET_ID], "competition_sources": [], "kernel_sources": [], "model_sources": [],
    }


def build(output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    if output_dir.exists() and force:
        import shutil
        shutil.rmtree(output_dir)
    nb_dir = output_dir / "notebooks" / "duecare-benchmark-convergence"
    nb_dir.mkdir(parents=True, exist_ok=True)
    (nb_dir / "notebook.ipynb").write_text(json.dumps(_notebook(), indent=1), encoding="utf-8")
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(_kernel_metadata(), indent=2), encoding="utf-8")
    return {"notebook_slug": "duecare-benchmark-convergence", "output_dir": str(output_dir)}


def _execute_notebooks(output_dir: Path) -> None:
    import nbformat
    from nbclient import NotebookClient
    for sub in sorted((output_dir / "notebooks").iterdir()):
        nb_path = sub / "notebook.ipynb"
        out_root = sub / "local-output"
        out_root.mkdir(exist_ok=True)
        old_root, old_out = os.environ.get("DUECARE_GRADES_ROOT"), os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR")
        os.environ["DUECARE_GRADES_ROOT"] = str(output_dir.parent / "benchmark_results_v1" / "dataset")
        os.environ["DUECARE_NOTEBOOK_OUTPUT_DIR"] = str(out_root)
        try:
            nb = nbformat.read(nb_path, as_version=4)
            NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(sub)}}).execute()
            nbformat.write(nb, sub / "notebook.executed.ipynb")
        finally:
            for key, old in (("DUECARE_GRADES_ROOT", old_root), ("DUECARE_NOTEBOOK_OUTPUT_DIR", old_out)):
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--execute-local", action="store_true")
    args = ap.parse_args(argv)
    result = build(args.output, force=args.force)
    if args.execute_local:
        _execute_notebooks(Path(result["output_dir"]))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
