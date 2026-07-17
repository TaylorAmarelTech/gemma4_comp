#!/usr/bin/env python3
# ruff: noqa: E501  (embedded Kaggle notebook cell source has long matplotlib lines)
"""Build a grounded "Where the harness helps most" Kaggle notebook.

This is the breakdown companion to ``build_benchmark_results_kaggle.py``. That
builder publishes the real multi-judge grades as the public Kaggle dataset
``taylorsamarel/duecare-harness-benchmark-grades`` and ships reproduce-lift /
judge-agreement notebooks. This builder emits ONE additional runnable notebook
that answers a single question from the same real grades: **where does the
harness help most?**

For the headline model it averages the judge panel to one score per
(prompt, arm), pairs the baseline arm against ``harness_core`` to get a
per-prompt lift, joins that to the prompt metadata, and reports mean lift broken
down by every available label field -- category, difficulty, and corridor -- as
sorted tables and horizontal bar charts, largest-and-smallest lift first, with
the paired-prompt count per bucket and a minimum-sample guard.

Data provenance and safety: the notebook consumes only the published dataset
(0-100 rubric scores plus A-E component scores keyed by (model, arm, prompt_id,
judge), and category/corridor/difficulty labels). It contains no model
responses, no prompt text, and no worker or personal data. To make
``--execute-local`` self-contained, ``build`` regenerates a LOCAL mirror of the
two CSVs from the real ``reports/rich_lift/panel.jsonl`` using the sibling
builder's helpers; the published Kaggle dataset remains the canonical source the
notebook attaches to.

These are rubric-scored benchmark results, not real-world trafficking-detection
metrics, and never ground truth about any person.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "reports" / "rich_lift" / "panel.jsonl"
PROMPTSET = ROOT / "reports" / "benchmark" / "full_promptset.json"
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "lift_breakdowns_v1"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
# Kaggle derives a kernel slug from its title (lowercase, spaces -> hyphens).
# TITLE must slugify to exactly SLUG or the push fails.
TITLE = "DueCare Where The Harness Helps Most"
SLUG = "duecare-where-the-harness-helps-most"
MARKER = ".duecare-lift-breakdowns-kaggle"

# Reuse the sibling builder's real-data helpers (panel loading + CSV
# serialization) so the local execution mirror shares one source of truth for
# the dataset schema instead of re-implementing it.
_REF_SPEC = importlib.util.spec_from_file_location(
    "duecare_build_benchmark_results_kaggle",
    ROOT / "scripts" / "build_benchmark_results_kaggle.py",
)
assert _REF_SPEC and _REF_SPEC.loader
ref = importlib.util.module_from_spec(_REF_SPEC)
sys.modules["duecare_build_benchmark_results_kaggle"] = ref
_REF_SPEC.loader.exec_module(ref)


def _prepare_output(path: Path, *, force: bool) -> Path:
    path = path.resolve()
    if path.exists():
        if not force:
            raise RuntimeError(f"output exists; pass --force to replace: {path.name}")
        if not (path / MARKER).is_file():
            raise RuntimeError("refusing to replace a directory this builder did not create")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / MARKER).write_text("duecare.lift_breakdowns_kaggle.v1\n", encoding="utf-8")
    return path


def build(output_dir: Path, *, force: bool, panel_path: Path = PANEL,
          promptset_path: Path = PROMPTSET) -> dict[str, Any]:
    rows = ref._load_panel(panel_path)
    if not rows:
        raise RuntimeError("panel is empty")
    meta = ref._load_registry_meta(promptset_path)
    graded_prompts = len({r.get("prompt_id") for r in rows})

    output_dir = _prepare_output(output_dir, force=force)

    # Local execution mirror of the published dataset (scores + labels only).
    dataset = output_dir / "dataset"
    dataset.mkdir()
    ref._write(dataset / "panel_grades.csv", ref._panel_csv(rows))
    ref._write(dataset / "prompt_metadata.csv", ref._prompt_meta_csv(rows, meta))
    ref._write_json(dataset / "release-manifest.json", {
        "schema_version": "duecare.benchmark_grades.v1",
        "dataset_id": DATASET_ID,
        "grade_rows": len(rows),
        "graded_prompts": graded_prompts,
        "note": (
            "Local execution mirror regenerated from reports/rich_lift/panel.jsonl "
            "so --execute-local is self-contained. The published Kaggle dataset "
            f"{DATASET_ID} is the canonical source the notebook attaches to."
        ),
    })

    notebook_dir = output_dir / "notebooks"
    notebook_dir.mkdir()
    for slug, title, nb in _notebooks():
        sub = notebook_dir / slug
        sub.mkdir()
        ref._write_json(sub / "notebook.ipynb", nb)
        ref._write_json(sub / "kernel-metadata.json", {
            "id": f"taylorsamarel/{slug}", "title": title, "code_file": "notebook.ipynb",
            "language": "python", "kernel_type": "notebook", "is_private": False,
            "enable_gpu": False, "enable_internet": False,
            "dataset_sources": [DATASET_ID], "competition_sources": [],
            "kernel_sources": [], "model_sources": [],
        })

    return {
        "output_dir": str(output_dir), "dataset_id": DATASET_ID,
        "notebook_slug": SLUG, "grade_rows": len(rows),
        "graded_prompts": graded_prompts,
        "breakdown_fields": ["category", "difficulty", "corridor"],
    }


# --- Notebook cell helpers ----------------------------------------------------

def _md(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "id": identifier, "metadata": {},
            "source": source.splitlines(True)}


def _code(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "code", "execution_count": None, "id": identifier,
            "metadata": {}, "outputs": [], "source": source.splitlines(True)}


def _wrap(cells: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4, "nbformat_minor": 5,
    }


# Copied verbatim from build_benchmark_results_kaggle.py: bind to the right
# dataset (via DUECARE_GRADES_ROOT or /kaggle/input, verified by the release
# manifest's dataset_id), load the two CSVs, and expose one canonical
# headline_model().
_SETUP = """import json, os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import Markdown, display

COLORS = ["#136f63", "#f2b134", "#d1495b", "#247ba0", "#6d597a", "#4f772d"]
plt.rcParams.update({"figure.figsize": (11, 5.6), "figure.dpi": 115,
                     "axes.facecolor": "#f7faf9", "axes.edgecolor": "#bed2cc",
                     "axes.grid": True, "grid.alpha": 0.2, "font.size": 11})

EXPECTED_DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"

def _verify_dataset(base):
    # Bind to the right dataset even if another DueCare dataset is also attached:
    # the release manifest must name this dataset id.
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
prompts = pd.read_csv(root / "prompt_metadata.csv")

def headline_model():
    # One canonical head across the notebook: prefer gemma4:31b, else the
    # most-paired model. (Avoids the lift/breakdown cells disagreeing.)
    if "gemma4:31b" in set(grades["model"]):
        return "gemma4:31b"
    return grades["model"].value_counts().index[0]

in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
out_dir = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", "/kaggle/working" if in_kaggle else Path.cwd()))
out_dir.mkdir(parents=True, exist_ok=True)
display(Markdown(f"Loaded **{len(grades):,} grade rows** over **{grades.prompt_id.nunique():,} prompts**, "
                 f"**{grades.model.nunique()} models**, **{grades.judge.nunique()} judges**."))"""


def _breakdowns_notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:26px 30px;border-radius:16px;background:linear-gradient(120deg,#102a43,#136f63,#247ba0);color:white">
<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.85">DueCare | benchmark grades</div>
<h1 style="margin:.3em 0 .2em;font-size:30px">Where the harness helps most</h1>
<p style="font-size:15px;line-height:1.5;margin:0;max-width:880px">Pair the baseline arm against the harness on the real multi-judge grades, join to the prompt labels, and see which prompt categories, difficulties, and corridors gain the most rubric points -- and which barely move.</p>
</div>"""),
        _md("intro", """## What this notebook does

The dataset holds a 0-100 rubric score per (model, arm, prompt_id, judge). For the
headline model this notebook:

1. averages the judge panel to one score per (prompt, arm),
2. keeps prompts that have both a **baseline** and a **harness_core** score and
   takes the per-prompt paired lift (`harness_core - baseline`),
3. joins each prompt to its category / difficulty / corridor label, and
4. reports **mean lift broken down by every available label field**, as sorted
   tables and bar charts, largest-and-smallest lift first.

Everything is recomputed from the raw grades. Small buckets are noisy, so a
minimum-sample guard drops any bucket with fewer than 20 paired prompts, and the
paired-prompt count is shown for every bucket that survives."""),
        _code("setup", _SETUP),
        _md("pair-note", """## 1. The headline pairing

Average the judges to one score per (prompt, arm), pair baseline against
`harness_core`, and take the per-prompt difference. This is the single quantity
every breakdown below slices. Positive means the harness raised the rubric score."""),
        _code("pair", """import numpy as np
head = headline_model()
mean = grades.groupby(["model", "prompt_id", "arm"], as_index=False)["score_0_100"].mean()
wide = mean.pivot_table(index=["model", "prompt_id"], columns="arm", values="score_0_100")
if head not in set(wide.index.get_level_values(0)):
    raise RuntimeError(f"headline model {head!r} has no rows in the grades")
if "baseline" not in wide.columns or "harness_core" not in wide.columns:
    raise RuntimeError("grades need both a baseline and a harness_core arm to pair")
paired = wide.loc[head].dropna(subset=["baseline", "harness_core"]).reset_index()
if len(paired) < 20:
    raise RuntimeError(f"only {len(paired)} paired prompts for {head} -- attach a fuller grades dataset")
paired["lift"] = paired["harness_core"] - paired["baseline"]
joined = paired.merge(prompts, on="prompt_id", how="left")
helps, hurts = int((joined["lift"] > 0).sum()), int((joined["lift"] < 0).sum())
display(Markdown(
    f"**`{head}`** over **{len(joined):,} paired prompts**: baseline **{joined['baseline'].mean():.1f}** "
    f"-> harness_core **{joined['harness_core'].mean():.1f}** "
    f"(mean lift **{joined['lift'].mean():+.1f}** on the 0-100 rubric). "
    f"The harness helps on **{helps:,}** prompts and hurts on **{hurts:,}**."))

fig, ax = plt.subplots(figsize=(11, 4.8))
ax.hist(joined["lift"], bins=40, color=COLORS[0], alpha=0.85)
ax.axvline(0, color=COLORS[2], lw=1.3, label="no change")
ax.axvline(joined["lift"].mean(), color="#102a43", lw=1.5, ls="--", label=f"mean {joined['lift'].mean():+.1f}")
ax.set(title=f"Per-prompt harness lift distribution ({head}, n={len(joined):,})",
       xlabel="lift  (harness_core - baseline, 0-100 rubric)", ylabel="prompts")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(out_dir / "lift_distribution.png", bbox_inches="tight")
plt.show()"""),
        _md("method-note", """## 2. How to read the breakdowns

Each breakdown groups the paired prompts by one label field, then reports:

- **n** -- paired prompts in the bucket (the sample size),
- **baseline** and **harness core** -- the mean rubric score of each arm, and
- **mean lift** -- the mean paired difference, sorted **largest lift first**.

Two honesty rules are baked in:

- **Minimum-sample guard.** Buckets with fewer than **20** paired prompts are
  dropped -- a +50 lift over three prompts is noise, not signal. When a field has
  many surviving buckets, only the largest and smallest few are charted so the
  extremes stay legible; the full set is always available in the analysis JSON.
- **What this is.** These are **rubric-scored benchmark** differences: an
  LLM-judge panel scored harnessed responses higher than raw ones on
  synthetic/composite safety prompts. They are measurement evidence about
  response quality, **not** real-world trafficking-detection rates, and never
  ground truth about any person or route."""),
        _code("breakdown-fn", """MIN_N = 20
CANDIDATE_FIELDS = ["category", "difficulty", "corridor"]
FIELDS = [f for f in CANDIDATE_FIELDS if f in prompts.columns]
display(Markdown("**Label fields available for breakdown:** " + ", ".join(f"`{f}`" for f in FIELDS) + "."))


def breakdown(field, *, min_n=MIN_N, max_buckets=20):
    \"\"\"Mean paired lift by one label field: sorted table + bar chart, guarded by min_n.\"\"\"
    if field not in joined.columns:
        display(Markdown(f"_Field `{field}` is not present in this dataset -- skipped._"))
        return None
    agg = (joined.dropna(subset=[field])
                 .groupby(field)
                 .agg(n=("lift", "size"),
                      baseline=("baseline", "mean"),
                      harness_core=("harness_core", "mean"),
                      lift=("lift", "mean")))
    kept = agg[agg["n"] >= min_n].sort_values("lift", ascending=False)
    if kept.empty:
        display(Markdown(f"_No `{field}` bucket reaches n>={min_n} yet._"))
        return None

    # "Largest-and-smallest first": with many buckets, chart only the extremes.
    shown, note = kept, ""
    if len(kept) > max_buckets:
        half = max_buckets // 2
        shown = pd.concat([kept.head(half), kept.tail(half)])
        note = f" &mdash; showing the {half} largest and {half} smallest of {len(kept)} buckets with n>={min_n}"

    disp = shown[["n", "baseline", "harness_core", "lift"]].rename(
        columns={"harness_core": "harness core", "lift": "mean lift"})
    display(Markdown(f"**Mean harness lift by `{field}`**{note} (sorted largest lift first; n = paired prompts):"))
    display(disp.style
            .format({"n": "{:,}", "baseline": "{:.1f}", "harness core": "{:.1f}", "mean lift": "{:+.1f}"})
            .background_gradient(subset=["mean lift"], cmap="RdYlGn"))

    order = shown.iloc[::-1]  # barh draws bottom-up; reverse so largest lift is on top
    colors = [COLORS[0] if v >= 0 else COLORS[2] for v in order["lift"]]
    labels = [f"{idx}  (n={int(order.loc[idx, 'n']):,})" for idx in order.index]
    fig, ax = plt.subplots(figsize=(11, max(3.2, 0.52 * len(order) + 1.2)))
    bars = ax.barh(range(len(order)), order["lift"].to_numpy(), color=colors)
    ax.bar_label(bars, fmt="%+.1f", padding=3, fontsize=9)
    ax.axvline(0, color="#5B5F68", lw=0.8)
    ax.set_yticks(range(len(order)), labels)
    ax.set(title=f"Mean harness lift by {field} ({head}, buckets with n>={min_n})",
           xlabel="mean lift  (0-100 rubric)")
    fig.tight_layout()
    fig.savefig(out_dir / f"lift_by_{field}.png", bbox_inches="tight")
    plt.show()
    return kept"""),
        _md("cat-note", """## 3. By prompt category

Category is the finest label -- adversarial attack framings, fee-camouflage
pretexts, business-framed exploitation, and so on. The harness helps most exactly
where the raw model is weakest: the most adversarial framings gain the most, and
the top bucket is where a bare model most often gets talked out of refusing."""),
        _code("cat", """cat = breakdown("category")"""),
        _md("diff-note", """## 4. By difficulty

Difficulty is the registry's own hardness label. Read this one top-to-bottom: the
harness adds the most on the hardest prompts and the least on the easy ones, where
a bare model already does fine -- the lift tracks the headroom it has to work with."""),
        _code("diff", """diff = breakdown("difficulty")"""),
        _md("corr-note", """## 5. By corridor

Corridor is the migration route a prompt is framed around. Most prompts are
route-agnostic (`various`), so that bucket dominates the sample; the named
corridors are much smaller, so read their lifts with the n column in mind -- they
are illustrative, not corridor-level detection rates."""),
        _code("corr", """corr = breakdown("corridor")"""),
        _md("close", """## The honest boundary

The harness helps most on the hardest, most adversarial prompts and least on the
easy ones -- the pattern you would want from a safety layer, and the honest
counterweight is that a handful of buckets and prompts still regress (they stay in
the tables, not hidden).

None of this is a real-world claim. Every number here is a **rubric-scored
benchmark** difference measured by an LLM-judge panel over synthetic/composite
safety prompts. It is evidence that the harness raises graded response quality,
**not** a trafficking-detection metric and never ground truth about any person or
route. Small-n buckets are noisy by construction; the minimum-sample guard limits
but does not erase that. See the companion `harness_lift_analysis.json` on the
dataset for the precomputed full read."""),
    ]
    return _wrap(cells)


def _notebooks() -> list[tuple[str, str, dict[str, Any]]]:
    return [(SLUG, TITLE, _breakdowns_notebook())]


def _execute_notebooks(output_dir: Path) -> None:
    import nbformat
    from nbclient import NotebookClient

    for sub in sorted((output_dir / "notebooks").iterdir()):
        notebook_path = sub / "notebook.ipynb"
        out_root = sub / "local-output"
        out_root.mkdir(exist_ok=True)
        old_root = os.environ.get("DUECARE_GRADES_ROOT")
        old_out = os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR")
        os.environ["DUECARE_GRADES_ROOT"] = str(output_dir / "dataset")
        os.environ["DUECARE_NOTEBOOK_OUTPUT_DIR"] = str(out_root)
        try:
            notebook = nbformat.read(notebook_path, as_version=4)
            NotebookClient(notebook, timeout=300, kernel_name="python3",
                           resources={"metadata": {"path": str(sub)}}).execute()
            nbformat.write(notebook, sub / "notebook.executed.ipynb")
        finally:
            for key, old in (("DUECARE_GRADES_ROOT", old_root),
                             ("DUECARE_NOTEBOOK_OUTPUT_DIR", old_out)):
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    value.add_argument("--panel", type=Path, default=PANEL)
    value.add_argument("--promptset", type=Path, default=PROMPTSET)
    value.add_argument("--force", action="store_true")
    value.add_argument("--execute-local", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = build(args.output, force=args.force, panel_path=args.panel,
                   promptset_path=args.promptset)
    if args.execute_local:
        _execute_notebooks(Path(result["output_dir"]))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
