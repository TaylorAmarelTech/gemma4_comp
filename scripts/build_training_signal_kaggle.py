# ruff: noqa: E501
"""Build the "The benchmark IS the training signal" notebook.

Closes the loop from evaluation to fine-tuning, using ONLY the scores: every prompt where the harness
clearly fixes a baseline gap becomes a training pair (SFT: the harnessed reply as the gold answer;
DPO: chosen = harnessed, rejected = baseline). This notebook applies the real distiller gate
(harness_core >= 70 AND lift >= 20, teacher arm = harness_core) to the published grades and shows how
many benchmark prompts qualify and the distribution of the lift that becomes the training signal --
without ever showing response text (that lives, PII-scrubbed, in the published training corpora).
Attaches to taylorsamarel/duecare-harness-benchmark-grades.

    python scripts/build_training_signal_kaggle.py
    python scripts/build_training_signal_kaggle.py --execute-local --force
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "training_signal_v1"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
MIN_TARGET = 70.0   # min harnessed 0-100 score to teach (build_lift_training_data.py default)
MIN_LIFT = 20.0     # min lift to include

NB_INDEX = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here"
DS = "https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades"
DS_TRAIN = "https://www.kaggle.com/datasets/taylorsamarel/duecare-proof-finetuning-data"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"
SITE = "https://duecare-ai.com/finetuning"


def _md(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "id": identifier, "metadata": {}, "source": source.splitlines(True)}


def _code(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "code", "execution_count": None, "id": identifier, "metadata": {}, "outputs": [], "source": source.splitlines(True)}


_SETUP = f"""import json, os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Markdown, display

MIN_TARGET, MIN_LIFT = {MIN_TARGET}, {MIN_LIFT}
COLORS = ["#136f63", "#f2b134", "#d1495b", "#247ba0", "#6d597a", "#4f772d"]
plt.rcParams.update({{"figure.figsize": (11, 5.4), "figure.dpi": 115, "axes.facecolor": "#f7faf9",
                     "axes.edgecolor": "#bed2cc", "axes.grid": True, "grid.alpha": 0.2, "font.size": 11}})

EXPECTED_DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"

def _verify_dataset(base):
    m = base / "release-manifest.json"
    if m.is_file():
        did = json.loads(m.read_text(encoding="utf-8")).get("dataset_id")
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
    raise FileNotFoundError(f"Attach {{EXPECTED_DATASET_ID}} (no matching dataset found)")

root = find_dataset()
grades = pd.read_csv(root / "panel_grades.csv")

def headline_model():
    return "gemma4:31b" if "gemma4:31b" in set(grades["model"]) else grades["model"].value_counts().index[0]

in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
out_dir = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", "/kaggle/working" if in_kaggle else Path.cwd()))
out_dir.mkdir(parents=True, exist_ok=True)
head = headline_model()

mean = grades[grades.model == head].groupby(["prompt_id", "arm"], as_index=False)["score_0_100"].mean()
wide = mean.pivot_table(index="prompt_id", columns="arm", values="score_0_100").dropna(subset=["baseline", "harness_core"])
wide["lift"] = wide["harness_core"] - wide["baseline"]
display(Markdown(f"**`{{head}}`**: {{len(wide):,}} paired prompts loaded. Training gate: harness_core >= "
                 f"{{MIN_TARGET:.0f}} AND lift >= {{MIN_LIFT:.0f}} (teacher arm = harness_core)."))"""


def _notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:28px 32px;border-radius:16px;background:linear-gradient(120deg,#0e1116,#6d597a,#f2b134);color:white">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.85">DueCare | benchmark to fine-tuning</div>
<h1 style="margin:.3em 0 .25em;font-size:30px">The benchmark IS the training signal</h1>
<p style="font-size:15px;line-height:1.55;margin:0;max-width:900px">Every prompt where the harness clearly fixes a weak baseline answer is also a training example: the harnessed reply is the gold SFT target, and (harnessed &gt; baseline) is a DPO preference pair. This notebook shows -- from the scores alone -- how many benchmark prompts become training data, and what signal they carry. No response text is shown here; the actual rows live, PII-scrubbed, in the published training corpora.</p>
</div>"""),
        _md("toc", """## Contents

- [1. From a graded gap to a training pair](#idea)
- [2. How many prompts qualify](#gate)
- [3. What it teaches (and does not)](#teaches)

**Related:** the [Start Here index](""" + NB_INDEX + """) - the [grades dataset](""" + DS + """) - the [training corpus](""" + DS_TRAIN + """) - the [repo](""" + REPO + """) - the [fine-tuning page](""" + SITE + """)."""),
        _code("setup", _SETUP),
        _md("idea", f"""<a id="idea"></a>
## 1. From a graded gap to a training pair

The benchmark scores a baseline answer and a harnessed answer for every prompt. Where the baseline is
weak and the harnessed answer is strong, the pair is exactly what supervised and preference
fine-tuning want:

- **SFT**: the harnessed reply becomes the gold assistant answer to learn from.
- **DPO / preference**: `chosen = harnessed`, `rejected = baseline` -- the model learns to prefer the
  grounded answer over the raw one.

The distiller keeps only high-quality, clearly-improved pairs. Its gate: the harnessed score must clear
**{MIN_TARGET:.0f}** and the lift must clear **{MIN_LIFT:.0f}** (on the 0-100 rubric)."""),
        _code("gate", """q = wide[(wide["harness_core"] >= MIN_TARGET) & (wide["lift"] >= MIN_LIFT)]
n_all, n_q = len(wide), len(q)
display(Markdown(f"**{n_q:,} of {n_all:,} paired prompts** ({100*n_q/n_all:.0f}%) clear the training gate "
                 f"for `{head}` -- each is a ready SFT target and a DPO preference pair. Mean lift of the "
                 f"qualifying set: **+{q['lift'].mean():.1f}** (vs +{wide['lift'].mean():.1f} over all)."))
fig, axes = plt.subplots(1, 2, figsize=(15, 5))
axes[0].hist(wide["lift"], bins=40, color="#b8c4c0", label="all paired prompts")
axes[0].hist(q["lift"], bins=40, color=COLORS[0], label="clears training gate")
axes[0].axvline(MIN_LIFT, color=COLORS[2], ls="--", label=f"min lift {MIN_LIFT:.0f}")
axes[0].set(title="Lift distribution -- the training signal", xlabel="lift (0-100)", ylabel="prompts"); axes[0].legend(frameon=False)
axes[1].scatter(wide["baseline"], wide["harness_core"], s=6, alpha=0.25, color="#b8c4c0")
axes[1].scatter(q["baseline"], q["harness_core"], s=6, alpha=0.5, color=COLORS[0])
axes[1].axhline(MIN_TARGET, color=COLORS[2], ls="--")
axes[1].set(title="Where the training pairs come from", xlabel="baseline score", ylabel="harness_core score", xlim=(0, 100), ylim=(0, 100))
fig.tight_layout(); fig.savefig(out_dir / "training_gate.png", bbox_inches="tight"); plt.show()"""),
        _md("teaches", """<a id="teaches"></a>
## 3. What it teaches -- and what it does not

**Teaches structure, not volatile facts.** The teacher is the `harness_core` arm, so the model learns
the *habits* the harness supplies -- name the indicator, cite the controlling statute, refuse to help
the trafficker, route to help, protect privacy -- rather than a specific hotline number or fee cap that
will change. Volatile facts stay in tools and retrieval, not in the weights.

**Honest limits.** These are **judge-scored silver** labels, not human-verified gold. The pipeline is
fail-closed on quality audits and on any prompt/lineage overlap with held-out evaluation sets, keeps
provenance and licensing, and excludes hidden chain-of-thought. The actual response rows -- PII-scrubbed
-- live in the published [training corpus](""" + DS_TRAIN + """). **No trained adapter or merged model is
claimed here**: this notebook shows the *signal* the benchmark yields, not a finished model. And as
everywhere: rubric scores from an LLM judge panel, not field detection."""),
    ]
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def _kernel_metadata() -> dict[str, Any]:
    return {
        "id": "taylorsamarel/duecare-benchmark-as-training-signal",
        "title": "DueCare Benchmark As Training Signal",
        "code_file": "notebook.ipynb", "language": "python", "kernel_type": "notebook",
        "is_private": False, "enable_gpu": False, "enable_internet": False,
        "dataset_sources": [DATASET_ID], "competition_sources": [], "kernel_sources": [], "model_sources": [],
    }


def build(output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    if output_dir.exists() and force:
        import shutil
        shutil.rmtree(output_dir)
    nb_dir = output_dir / "notebooks" / "duecare-benchmark-as-training-signal"
    nb_dir.mkdir(parents=True, exist_ok=True)
    (nb_dir / "notebook.ipynb").write_text(json.dumps(_notebook(), indent=1), encoding="utf-8")
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(_kernel_metadata(), indent=2), encoding="utf-8")
    return {"notebook_slug": "duecare-benchmark-as-training-signal", "output_dir": str(output_dir)}


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
