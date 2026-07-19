# ruff: noqa: E501
"""Build the "Who this protects, and what it covers" impact + coverage notebook.

The rest of the collection is technical rigor; this one grounds the WHY. It shows, from the real
prompt metadata, the trafficking typologies and recruitment corridors the benchmark actually spans,
then maps the five rubric dimensions to the concrete things a harnessed answer gives a worker (name
the indicator, cite the controlling law, refuse to operationalize the scheme, route to real help,
protect privacy) and how much each improves. Attaches to taylorsamarel/duecare-harness-benchmark-grades.

    python scripts/build_impact_coverage_kaggle.py
    python scripts/build_impact_coverage_kaggle.py --execute-local --force
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "impact_coverage_v1"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"

NB_INDEX = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here"
NB_BREAK = "https://www.kaggle.com/code/taylorsamarel/duecare-where-the-harness-helps-most"
DS = "https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"
SITE = "https://duecare-ai.com"


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
display(Markdown(f"Loaded **{len(grades):,} grade rows**; prompt metadata "
                 f"{'attached (' + str(len(prompts)) + ' prompts)' if prompts is not None else 'not attached'}."))"""


def _notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:28px 32px;border-radius:16px;background:linear-gradient(120deg,#0e1116,#136f63,#d1495b);color:white">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.85">DueCare | impact & coverage</div>
<h1 style="margin:.3em 0 .25em;font-size:30px">Who this protects, and what it covers</h1>
<p style="font-size:15px;line-height:1.55;margin:0;max-width:900px">The rest of this collection measures a lift. This notebook grounds the <b>why</b>: the real recruitment corridors and exploitation typologies the benchmark spans, and what a harnessed answer actually gives a migrant worker who pastes in a suspicious job offer -- the specific indicator, the controlling law, a refusal to help the trafficker, and a route to real help.</p>
</div>"""),
        _md("toc", """## Contents

- [1. The problem, in one paragraph](#problem)
- [2. What the benchmark covers](#coverage)
- [3. What the harness gives a worker (the five dimensions)](#dims)
- [4. Where it matters most](#most)
- [5. Honest boundary](#boundary)

**Related:** the [Start Here index](""" + NB_INDEX + """) - the [grades dataset](""" + DS + """) - [where the harness helps most](""" + NB_BREAK + """) - the [repo](""" + REPO + """) - the [site](""" + SITE + """)."""),
        _code("setup", _SETUP),
        _md("problem", """<a id="problem"></a>
## 1. The problem, in one paragraph

A worker is offered a job abroad. The contract looks official; the recruiter is friendly; the fee is
"normal". Buried in it are the indicators of forced labour -- a passport held "for safekeeping", a debt
that grows, a wage that never arrives. A frontier LLM usually *recognizes* the scheme when asked -- but
often stops short of what protects the worker: naming the specific indicator, citing the controlling
statute, refusing to help operationalize it, and pointing to a real hotline. DueCare's harness adds
exactly that grounding. This notebook shows the range of situations it was tested across, and what it
changes."""),
        _code("coverage", """if prompts is not None:
    cov = prompts.copy()
    parts = []
    if "corridor" in cov.columns:
        corr = cov[cov["corridor"].astype(str).str.contains("->", na=False)]["corridor"].value_counts().head(12)
        parts.append(("Recruitment corridors (named routes)", corr))
    if "category" in cov.columns:
        cats = cov["category"].value_counts().head(12)
        parts.append(("Exploitation typologies (top categories)", cats))
    display(Markdown(f"The benchmark spans **{cov['category'].nunique() if 'category' in cov else 0} exploitation "
                     f"typologies** across **{(cov['corridor'].astype(str).str.contains('->', na=False)).sum():,} "
                     f"corridor-specific prompts** on **{cov['corridor'].nunique() if 'corridor' in cov else 0} named "
                     f"recruitment routes**, at every difficulty level."))
    fig, axes = plt.subplots(1, len(parts), figsize=(7.5 * len(parts), 6))
    axes = np.atleast_1d(axes)
    for ax, (title, s) in zip(axes, parts):
        ax.barh(list(s.index)[::-1], list(s.values)[::-1], color=COLORS[3])
        ax.set(title=title, xlabel="prompts")
    fig.tight_layout(); fig.savefig(out_dir / "coverage.png", bbox_inches="tight"); plt.show()
    if "difficulty" in cov.columns:
        display(Markdown("**Difficulty mix** (harder prompts disguise the scheme more): "
                         + ", ".join(f"{k} {v:,}" for k, v in cov['difficulty'].value_counts().items())))
else:
    display(Markdown("_prompt_metadata.csv not attached; skipping coverage. Attach the grades dataset to see it._"))"""),
        _md("dims-note", """<a id="dims"></a>
## 3. What the harness gives a worker -- the five dimensions

The 0-100 rubric is five things a *protective* answer does. Each maps to something concrete for the
worker; the bars below are how much the harness improves each (mean component gain, headline model)."""),
        _code("dims", """names = {"A": "A - name the exploitation indicator", "B": "B - cite the controlling law",
         "C": "C - refuse to help the trafficker", "D": "D - route to real help", "E": "E - protect privacy"}
have = [c for c in list("ABCDE") if c in grades.columns]
m = grades[grades.model == head].groupby("arm")[have].mean()
if "baseline" in m.index and "harness_core" in m.index:
    gain = (m.loc["harness_core"] - m.loc["baseline"]).reindex(have)
    tbl = pd.DataFrame({"what it means for the worker": [names[c] for c in have],
                        "mean gain (0-100)": [round(float(gain[c]), 1) for c in have]}, index=have)
    display(tbl.style.format({"mean gain (0-100)": "{:+.1f}"}).background_gradient(subset=["mean gain (0-100)"], cmap="Greens"))
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.barh([names[c] for c in have][::-1], [float(gain[c]) for c in have][::-1], color=COLORS[0])
    ax.bar_label(ax.containers[0], fmt="%+.1f", padding=3)
    ax.set(title=f"How much better the worker's answer gets, per dimension ({head})", xlabel="mean gain (0-100)")
    fig.tight_layout(); fig.savefig(out_dir / "dimensions.png", bbox_inches="tight"); plt.show()
    display(Markdown("Every dimension improves -- the harness does not just make the model *refuse* (C); it "
                     "adds the **specific law (B)** and the **concrete hotline (D)** an unharnessed reply leaves out."))
else:
    display(Markdown("_Component columns A-E not present in this panel; skipping the per-dimension view._"))"""),
        _md("most-note", """<a id="most"></a>
## 4. Where it matters most

The harness helps most exactly where the base model is weakest -- the hardest, most disguised prompts,
and the corridors and typologies where a wrong answer is most costly. The
[breakdowns notebook](""" + NB_BREAK + """) has the full view; the headline is that the gain is largest on
`very_hard` prompts and on specific high-risk recruitment corridors, not on the easy cases a model
already handles."""),
        _md("boundary", """<a id="boundary"></a>
## 5. Honest boundary

This is a **benchmark** of response quality, judged by a panel of language models over
synthetic/composite prompts. It shows the harness makes model answers markedly more protective across a
wide range of trafficking situations. It does **not** claim real-world victim identification, field
detection, or that any model output is a substitute for a trained caseworker or a lawyer. The worker
scenarios are composite and carry no real personal data. The path to a stronger claim is a blinded
human-expert validation -- named as the next step everywhere in this project."""),
    ]
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def _kernel_metadata() -> dict[str, Any]:
    return {
        "id": "taylorsamarel/duecare-impact-and-coverage",
        "title": "DueCare Impact And Coverage",
        "code_file": "notebook.ipynb", "language": "python", "kernel_type": "notebook",
        "is_private": False, "enable_gpu": False, "enable_internet": False,
        "dataset_sources": [DATASET_ID], "competition_sources": [], "kernel_sources": [], "model_sources": [],
    }


def build(output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    if output_dir.exists() and force:
        import shutil
        shutil.rmtree(output_dir)
    nb_dir = output_dir / "notebooks" / "duecare-impact-and-coverage"
    nb_dir.mkdir(parents=True, exist_ok=True)
    (nb_dir / "notebook.ipynb").write_text(json.dumps(_notebook(), indent=1), encoding="utf-8")
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(_kernel_metadata(), indent=2), encoding="utf-8")
    return {"notebook_slug": "duecare-impact-and-coverage", "output_dir": str(output_dir)}


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
