# ruff: noqa: E501
"""Build the polished "Start Here" INDEX notebook for the DueCare harness-lift benchmark collection.

This is the judge-facing front door: it shows the real headline result and the cross-model board
(recomputed live from the attached grades dataset), then guides the reader through the rest of the
collection (reproduce / breakdowns / statistical-robustness / judge notebooks) in reading order,
and states the honest boundaries prominently. Attaches to the public dataset
taylorsamarel/duecare-harness-benchmark-grades. Build + optionally execute locally:

    python scripts/build_benchmark_index_kaggle.py
    python scripts/build_benchmark_index_kaggle.py --execute-local --force
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "benchmark_index_v1"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"

DS = "https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades"
NB_REPRO = "https://www.kaggle.com/code/taylorsamarel/duecare-reproduce-harness-lift"
NB_BREAK = "https://www.kaggle.com/code/taylorsamarel/duecare-where-the-harness-helps-most"
NB_ROBUST = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-statistical-robustness"
NB_JUDGE = "https://www.kaggle.com/code/taylorsamarel/duecare-judge-agreement"
NB_CLAIM = "https://www.kaggle.com/code/taylorsamarel/duecare-what-the-benchmark-proves"
NB_CALIB = "https://www.kaggle.com/code/taylorsamarel/duecare-judge-panel-calibration"
NB_CONTROLS = "https://www.kaggle.com/code/taylorsamarel/duecare-methodology-and-controls"
NB_CONVERGE = "https://www.kaggle.com/code/taylorsamarel/duecare-benchmark-convergence"
NB_IMPACT = "https://www.kaggle.com/code/taylorsamarel/duecare-impact-and-coverage"
NB_TRAIN = "https://www.kaggle.com/code/taylorsamarel/duecare-benchmark-as-training-signal"
DS_BOARD = "https://www.kaggle.com/datasets/taylorsamarel/duecare-cross-model-harness-leaderboard"
DS_CONTROLS = "https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-lift-controls"
DS_PERDIM = "https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-perdim-grades"
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
from IPython.display import Markdown, display

COLORS = ["#136f63", "#f2b134", "#d1495b", "#247ba0", "#6d597a", "#4f772d"]
import matplotlib.pyplot as plt
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
            root = cand if cand.is_dir() else cand.parent
            if root in seen or not (root / "panel_grades.csv").is_file():
                continue
            seen.add(root)
            if _verify_dataset(root):
                return root
    raise FileNotFoundError(f"Attach {EXPECTED_DATASET_ID} (no matching dataset found)")

root = find_dataset()
grades = pd.read_csv(root / "panel_grades.csv")

def headline_model():
    if "gemma4:31b" in set(grades["model"]):
        return "gemma4:31b"
    return grades["model"].value_counts().index[0]

in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
out_dir = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", "/kaggle/working" if in_kaggle else Path.cwd()))
out_dir.mkdir(parents=True, exist_ok=True)


def board():
    mean = grades.groupby(["model", "prompt_id", "arm"], as_index=False)["score_0_100"].mean()
    wide = mean.pivot_table(index=["model", "prompt_id"], columns="arm", values="score_0_100")
    rows = []
    for model, sub in wide.groupby(level=0):
        p = sub.dropna(subset=["baseline", "harness_core"])
        if len(p) < 5:
            continue
        b, c = p["baseline"], p["harness_core"]
        d = c - b
        ng = float(np.mean((c - b) / (100 - b).clip(lower=1e-9)))
        rows.append({"model": model, "n_pairs": len(p), "baseline": round(b.mean(), 1),
                     "harnessed": round(c.mean(), 1), "lift": round(d.mean(), 1),
                     "norm_gain": round(ng, 3), "win_rate_%": round(100 * (d > 0).mean(), 1)})
    return pd.DataFrame(rows).sort_values("n_pairs", ascending=False).reset_index(drop=True)

display(Markdown(f"Loaded **{len(grades):,} grade rows** over **{grades.prompt_id.nunique():,} prompts**, "
                 f"**{grades.model.nunique()} models**, **{grades.judge.nunique()} judges**."))"""


def _notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:28px 32px;border-radius:16px;background:linear-gradient(120deg,#0e1116,#136f63,#f2b134);color:white">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.85">DueCare | Gemma 4 safety benchmark | Start here</div>
<h1 style="margin:.3em 0 .25em;font-size:31px">Does a thin layer of legal grounding make an LLM safer for migrant workers?</h1>
<p style="font-size:15px;line-height:1.55;margin:0;max-width:900px">This is the front door to the DueCare harness-lift benchmark. It measures whether a small, model-agnostic layer -- fired indicator rules, retrieved law, and deterministic tools, added to the prompt and nothing else -- makes a model name the exploitation indicator, cite the controlling statute, refuse to operationalize the scheme, and route the worker to real help. Below: the real headline, the cross-model board, and a guided tour of the rest of the collection.</p>
</div>"""),
        _md("toc", """## What is in this collection

This notebook is the index. Read it first, then follow the guided tour.

- [1. The headline result](#headline)
- [2. The cross-model board](#board)
- [3. Guided tour of the collection](#tour)
- [4. Reproduce it yourself](#reproduce)
- [5. What this does and does NOT prove](#boundary)

All numbers are recomputed live from the attached grades dataset; nothing is hard-coded."""),
        _code("setup", _SETUP),
        _md("headline-note", """<a id="headline"></a>
## 1. The headline result

Each prompt is answered by the same model twice -- raw, then wrapped by the harness -- and a panel
of frontier judges (each from a different model family, never grading its own) scores both replies
0-100 on five reasoned safety criteria. The reported metric is the paired per-prompt lift, which
cancels each judge's absolute scale."""),
        _code("headline", """head = headline_model()
b = board()
row = b[b.model == head].iloc[0]
display(Markdown(f"**`{head}`**: baseline **{row.baseline}** -> harnessed **{row.harnessed}** "
                 f"= **+{row.lift}** on the 0-100 rubric, over **{int(row.n_pairs):,} paired prompts** "
                 f"(win rate {row['win_rate_%']}%)."))
fig, ax = plt.subplots(figsize=(9, 2.6))
ax.barh([head], [row.baseline], color="#b8c4c0", label="baseline")
ax.barh([head], [row.lift], left=[row.baseline], color=COLORS[0], label="harness lift")
ax.text(row.harnessed + 1, 0, f"{row.harnessed} (+{row.lift})", va="center", fontsize=11)
ax.set(title="Headline: baseline score + harness lift", xlabel="mean 0-100 rubric score", xlim=(0, 105))
ax.legend(loc="lower right", frameon=False)
fig.tight_layout(); fig.savefig(out_dir / "index_headline.png", bbox_inches="tight"); plt.show()"""),
        _md("board-note", """<a id="board"></a>
## 2. The cross-model board

The harness is pure prompt augmentation, so the same benchmark wraps any model. `norm_gain` is the
ceiling-adjusted score -- the fraction of the remaining headroom `(100 - baseline)` the harness
captures -- so a high-baseline model is compared fairly with a low one. It often re-ranks the board
versus raw lift (the biggest raw lift usually just had the most room)."""),
        _code("board", """b = board()
display(b.style.format({"norm_gain": "{:.3f}"}).background_gradient(subset=["lift", "norm_gain"], cmap="Greens"))
fig, ax = plt.subplots(figsize=(11, 5.2))
t = b.sort_values("lift").tail(8)
ax.barh(t["model"], t["baseline"], color="#b8c4c0", label="baseline")
ax.barh(t["model"], t["lift"], left=t["baseline"], color=COLORS[0], label="harness lift")
ax.set(title="Harness lift across models (baseline + lift, 0-100)", xlabel="mean rubric score", xlim=(0, 105))
ax.legend(loc="lower right", frameon=False)
fig.tight_layout(); fig.savefig(out_dir / "index_board.png", bbox_inches="tight"); plt.show()"""),
        _md("tour", f"""<a id="tour"></a>
## 3. Guided tour of the collection

Read in this order -- each notebook answers one question, all from the same real grades dataset.

| # | Notebook | The question it answers |
|---|---|---|
| 0 | **[Impact & coverage]({NB_IMPACT})** | *Start with the why.* Who this protects, the real trafficking typologies and recruitment corridors it covers, and what a harnessed answer gives a worker. |
| - | **[Grades dataset]({DS})** | The raw judged panel: one 0-100 score per (model, arm, prompt, judge), plus the five A-E components. Everything here is recomputed from it. |
| 1 | **[Reproduce the harness lift]({NB_REPRO})** | Recompute the headline + per-model board, the statistical strength, per-judge robustness, and the per-dimension gains -- from scratch. |
| 2 | **[Where the harness helps most]({NB_BREAK})** | Lift by prompt category, difficulty, and recruitment corridor. (It helps most where the base model is weakest.) |
| 3 | **[Statistical robustness]({NB_ROBUST})** | Leave-one-judge-out envelope, bootstrap CIs, Cohen's d, sign test, forest plot -- is the lift real? |
| 4 | **[Judge agreement]({NB_JUDGE})** | How much the judges agree (within-arm ICC), so the headline is not one judge's quirk. |
| 5 | **[What the benchmark proves]({NB_CLAIM})** | The honest evidence ladder -- what each result proves, and what it does NOT. |
| 6 | **[Judge panel calibration]({NB_CALIB})** | Judge leniency, per-judge robustness, and why a 3-judge paired design is trustworthy. |
| 7 | **[Methodology & controls]({NB_CONTROLS})** | Is the lift real? The placebo panel, negative control, and applicability audit -- with the honest, inconclusive parts kept in. |
| 8 | **[Benchmark convergence]({NB_CONVERGE})** | How much of the benchmark do you need? A random ~100-prompt subsample already recovers the full lift (yet the exhaustive sweep still runs to completion). |
| 9 | **[The benchmark is the training signal]({NB_TRAIN})** | Evaluation -> fine-tuning: ~75% of graded prompts become SFT/DPO training pairs. |

Also: the **[cross-model leaderboard dataset]({DS_BOARD})** (a citable flat CSV of the board), the
**[controls dataset]({DS_CONTROLS})** (the placebo / negative-control / applicability results), the
**[per-dimension grades dataset]({DS_PERDIM})** (the exhaustive one-judge-call-per-dimension scores, re-versioned as the sweep grows), the
**[source repository]({REPO})**, and the **[live site]({SITE})**."""),
        _md("reproduce", f"""<a id="reproduce"></a>
## 4. Reproduce it yourself

Everything is recomputed from `panel_grades.csv` in the attached dataset -- no hidden state. The
[reproduce notebook]({NB_REPRO}) walks the full computation; the [source repo]({REPO}) has the
harness, the grader, and the exhaustive per-dimension sweep that keeps growing each model's coverage
toward the full 78,719-prompt registry. The sweep grades in a seeded-shuffled order, so a partial-n
read is an unbiased random sample of the full scope."""),
        _md("boundary", """<a id="boundary"></a>
## 5. What this does -- and does NOT -- prove

**It shows:** a thin, model-agnostic grounding layer raises rubric-scored response quality on
adversarial migrant-worker-safety prompts, decisively and across every model tested, most where the
base model is weakest.

**It does NOT show:** real-world victim identification, field detection, or deployment
effectiveness. **The judges are language models, not anti-trafficking professionals** -- this is
benchmark evidence about response quality, not ground truth about any person. A blinded human-expert
validation is the honest precondition for a peer-reviewed claim, and a full-registry length-matched
placebo is the next control. These limits are kept visible on every surface, not hidden."""),
    ]
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def _kernel_metadata() -> dict[str, Any]:
    return {
        "id": "taylorsamarel/duecare-harness-lift-benchmark-start-here",
        "title": "DueCare Harness Lift Benchmark Start Here",
        "code_file": "notebook.ipynb", "language": "python", "kernel_type": "notebook",
        "is_private": False, "enable_gpu": False, "enable_internet": False,
        "dataset_sources": [DATASET_ID], "competition_sources": [], "kernel_sources": [], "model_sources": [],
    }


def build(output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    if output_dir.exists() and force:
        import shutil
        shutil.rmtree(output_dir)
    nb_dir = output_dir / "notebooks" / "duecare-harness-lift-benchmark-start-here"
    nb_dir.mkdir(parents=True, exist_ok=True)
    (nb_dir / "notebook.ipynb").write_text(json.dumps(_notebook(), indent=1), encoding="utf-8")
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(_kernel_metadata(), indent=2), encoding="utf-8")
    return {"notebook_slug": "duecare-harness-lift-benchmark-start-here", "output_dir": str(output_dir)}


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
