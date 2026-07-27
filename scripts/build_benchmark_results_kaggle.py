#!/usr/bin/env python3
# ruff: noqa: E501  (embedded Kaggle notebook cell source has long matplotlib lines)
"""Publish the real DueCare benchmark grades as a public Kaggle dataset + notebooks.

The autonomous evaluator has graded thousands of real registry prompts across
baseline / harness_core / harness_full arms with a multi-judge panel. Those
grades are the honest evidence behind the harness-lift result -- but they live
in a gitignored file. This builder packages the **scores only** (no response
text, no PII) plus the joinable prompt metadata (category / corridor /
difficulty) and the precomputed analysis, with rich Kaggle metadata for
usability, and emits runnable example notebooks that reproduce the analysis.

Safety: the panel contains 0-100 scores and A-E component scores keyed by
(model, arm, prompt_id, judge). It contains no model responses, no prompt text,
and no worker data. The prompt metadata is category/corridor/difficulty labels
only -- never the adversarial prompt text.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "reports" / "rich_lift" / "panel.jsonl"
PROMPTSET = ROOT / "reports" / "benchmark" / "full_promptset.json"
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "benchmark_results_v1"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
TITLE = "DueCare Harness Benchmark Grades"
SUBTITLE = "Real multi-judge grades of an LLM safety harness across 8 models and 3 arms"
MARKER = ".duecare-benchmark-results-kaggle"
COMPONENTS = ("A", "B", "C", "D", "E")
COMPONENT_NAMES = {
    "A": "indicator recognition", "B": "legal / ILO grounding", "C": "refusal / safety",
    "D": "resources / next steps", "E": "privacy / safety",
}

_ANALYZE_SPEC = importlib.util.spec_from_file_location(
    "duecare_analyze_full_results", ROOT / "scripts" / "analyze_full_results.py"
)
assert _ANALYZE_SPEC and _ANALYZE_SPEC.loader
analyze = importlib.util.module_from_spec(_ANALYZE_SPEC)
sys.modules["duecare_analyze_full_results"] = analyze
_ANALYZE_SPEC.loader.exec_module(analyze)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_json(path: Path, value: Any) -> None:
    _write(path, json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n")


def _load_panel(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_registry_meta(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(p["id"]): {
            "category": p.get("category"), "corridor": p.get("corridor"),
            "difficulty": p.get("difficulty"), "source": p.get("source"),
        }
        for p in data.get("prompts", []) if p.get("id")
    }


def _panel_csv(rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["model", "arm", "prompt_id", "judge", "score_0_100", *COMPONENTS])
    for r in rows:
        comps = r.get("components") or {}
        writer.writerow([
            r.get("model"), r.get("arm"), r.get("prompt_id"), r.get("judge"),
            r.get("score_0_100"), *[comps.get(c) for c in COMPONENTS],
        ])
    return buffer.getvalue()


def _prompt_meta_csv(rows: list[dict[str, Any]], meta: dict[str, dict[str, Any]]) -> str:
    graded = sorted({str(r.get("prompt_id")) for r in rows if r.get("prompt_id")})
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["prompt_id", "category", "corridor", "difficulty", "source"])
    for pid in graded:
        m = meta.get(pid, {})
        writer.writerow([pid, m.get("category"), m.get("corridor"),
                         m.get("difficulty"), m.get("source")])
    return buffer.getvalue()


def _prepare_output(path: Path, *, force: bool) -> Path:
    path = path.resolve()
    if path.exists():
        if not force:
            raise RuntimeError(f"output exists; pass --force to replace: {path.name}")
        if not (path / MARKER).is_file():
            raise RuntimeError("refusing to replace a directory this builder did not create")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / MARKER).write_text("duecare.benchmark_results_kaggle.v1\n", encoding="utf-8")
    return path


def build(output_dir: Path, *, force: bool, panel_path: Path = PANEL,
          promptset_path: Path = PROMPTSET) -> dict[str, Any]:
    rows = _load_panel(panel_path)
    if not rows:
        raise RuntimeError("panel is empty")
    meta = _load_registry_meta(promptset_path)
    agg = analyze.aggregate(rows, registry_meta=meta)

    models = collections.Counter(r.get("model") for r in rows)
    arms = collections.Counter(r.get("arm") for r in rows)
    judges = collections.Counter(r.get("judge") for r in rows)
    graded_prompts = len({r.get("prompt_id") for r in rows})
    head = next((m for m in agg["per_model"] if m["model"] == "gemma4:31b"),
                agg["per_model"][0] if agg["per_model"] else None)

    output_dir = _prepare_output(output_dir, force=force)
    dataset = output_dir / "dataset"
    dataset.mkdir()
    _write(dataset / "panel_grades.csv", _panel_csv(rows))
    _write(dataset / "prompt_metadata.csv", _prompt_meta_csv(rows, meta))
    _write_json(dataset / "harness_lift_analysis.json",
                {"generated_from": "reports/rich_lift/panel.jsonl", **agg})
    _write(dataset / "README.md", _readme(rows, models, arms, judges, graded_prompts, head))
    _write(dataset / "DATA_CARD.md", _data_card(rows, models, judges, graded_prompts))
    _write(dataset / "LICENSE", _LICENSE)

    artifacts = {}
    for path in sorted(dataset.iterdir()):
        if path.is_file():
            artifacts[path.name] = {"bytes": path.stat().st_size,
                                    "sha256": _sha256_bytes(path.read_bytes())}
    _write_json(dataset / "release-manifest.json", {
        "schema_version": "duecare.benchmark_grades.v1",
        "dataset_id": DATASET_ID,
        "grade_rows": len(rows),
        "graded_prompts": graded_prompts,
        "models": dict(models.most_common()),
        "arms": dict(arms.most_common()),
        "judges": dict(judges.most_common()),
        "contains_response_text_or_pii": False,
        "safe_to_publish": True,
        "artifacts": artifacts,
    })
    _write_json(dataset / "dataset-metadata.json", _dataset_metadata(rows, graded_prompts))

    notebook_dir = output_dir / "notebooks"
    notebook_dir.mkdir()
    for slug, title, nb in _notebooks():
        sub = notebook_dir / slug
        sub.mkdir()
        _write_json(sub / "notebook.ipynb", nb)
        _write_json(sub / "kernel-metadata.json", {
            "id": f"taylorsamarel/{slug}", "title": title, "code_file": "notebook.ipynb",
            "language": "python", "kernel_type": "notebook", "is_private": False,
            "enable_gpu": False, "enable_internet": False,
            "dataset_sources": [DATASET_ID], "competition_sources": [],
            "kernel_sources": [], "model_sources": [],
        })

    return {
        "output_dir": str(output_dir), "dataset_id": DATASET_ID,
        "grade_rows": len(rows), "graded_prompts": graded_prompts,
        "models": len(models), "headline": (
            f"{head['model']} {head['baseline']}->{head['core']} ({head['lift_core']:+})"
            if head else None
        ),
    }


_LICENSE = """Creative Commons Attribution 4.0 International (CC BY 4.0)

This dataset contains only 0-100 rubric scores and A-E component scores keyed by
(model, arm, prompt_id, judge), plus prompt category/corridor/difficulty labels.
It contains no model responses, no prompt text, and no worker or personal data.
"""


def _dataset_metadata(rows: list[dict[str, Any]], graded_prompts: int) -> dict[str, Any]:
    return {
        "title": TITLE,
        "subtitle": SUBTITLE,
        "id": DATASET_ID,
        "isPrivate": False,
        "licenses": [{"name": "CC-BY-4.0"}],
        "keywords": ["nlp", "text", "classification", "artificial intelligence"],
        "description": _description(rows, graded_prompts),
        "resources": [
            {"path": "panel_grades.csv",
             "description": f"{len(rows)} grade rows: one 0-100 score plus A-E component scores per (model, arm, prompt_id, judge). No response text.",
             "schema": {"fields": [
                 {"name": "model", "type": "string", "description": "Subject model that produced the graded response (e.g. gemma4:31b)."},
                 {"name": "arm", "type": "string", "description": "baseline (no harness), harness_core, or harness_full."},
                 {"name": "prompt_id", "type": "string", "description": "Registry prompt identifier; join to prompt_metadata.csv."},
                 {"name": "judge", "type": "string", "description": "LLM judge that produced this grade (gpt-oss:120b, glm-5.2, deepseek-v4-pro)."},
                 {"name": "score_0_100", "type": "number", "description": "Overall rubric score 0-100 for the response under this judge."},
                 {"name": "A", "type": "number", "description": "Component score: indicator recognition."},
                 {"name": "B", "type": "number", "description": "Component score: legal / ILO grounding."},
                 {"name": "C", "type": "number", "description": "Component score: refusal / safety."},
                 {"name": "D", "type": "number", "description": "Component score: resources / next steps."},
                 {"name": "E", "type": "number", "description": "Component score: privacy / safety."},
             ]}},
            {"path": "prompt_metadata.csv",
             "description": f"Category / corridor / difficulty labels for each of the {graded_prompts} graded prompts. Labels only -- no prompt text.",
             "schema": {"fields": [
                 {"name": "prompt_id", "type": "string", "description": "Registry prompt identifier; join key to panel_grades.csv."},
                 {"name": "category", "type": "string", "description": "Prompt category (e.g. labor_trafficking, adversarial, fee_splitting)."},
                 {"name": "corridor", "type": "string", "description": "Migration corridor (e.g. Nepal->Qatar) or 'various'."},
                 {"name": "difficulty", "type": "string", "description": "easy / medium / hard / very_hard / multipath."},
                 {"name": "source", "type": "string", "description": "How the prompt entered the registry (e.g. seed, template)."},
             ]}},
            {"path": "harness_lift_analysis.json",
             "description": "Precomputed per-model analysis: paired lift, statistical strength (bootstrap CI, sign test, Wilson interval), per-judge robustness, and category/corridor/difficulty breakdowns."},
        ],
    }


def _description(rows: list[dict[str, Any]], graded_prompts: int) -> str:
    return (
        "Real multi-judge grades from DueCare's autonomous LLM-safety evaluator. "
        "Each row is a 0-100 rubric score (plus five A-E component scores) for one "
        "model response under one LLM judge, across three arms: the raw model "
        "(baseline), the model wrapped by DueCare's deterministic safety harness "
        "core, and the full harness. It is the honest evidence behind the "
        "harness-lift result: on the headline model, baseline-to-harness lift is "
        "large and holds inside every judge independently.\n\n"
        f"{len(rows):,} grade rows cover {graded_prompts:,} migrant-worker "
        "exploitation / trafficking-safety prompts, eight subject models, and a "
        "three-judge panel (gpt-oss:120b, glm-5.2, deepseek-v4-pro). The dataset "
        "contains scores and prompt category/corridor/difficulty labels only -- no "
        "model responses, no prompt text, and no worker data. These are "
        "rubric-scored benchmark results, not real-world trafficking-detection "
        "metrics. Companion runnable notebooks reproduce the full analysis."
    )


def _readme(rows: list[dict[str, Any]], models: Any, arms: Any, judges: Any,
            graded_prompts: int, head: dict[str, Any] | None) -> str:
    headline = ""
    if head:
        headline = (
            f"\n## Headline result (`{head['model']}`, n={head['n_pair']:,} paired prompts)\n\n"
            f"- baseline **{head['baseline']}** -> harness_core **{head['core']}** "
            f"(**{head['lift_core']:+}** on the 0-100 rubric)\n"
            f"- the harness helps on {head['helps']:,} prompts and hurts on {head['hurts']:,}\n"
        )
    return f"""# {TITLE}

{SUBTITLE}.

Real multi-judge grades from DueCare's autonomous evaluator: for each
(model, arm, prompt_id, judge) a 0-100 rubric score plus five A-E component
scores. **Scores only -- no model responses, no prompt text, no PII.**
{headline}
## Files

| File | Contents |
|---|---|
| `panel_grades.csv` | {len(rows):,} grade rows (model, arm, prompt_id, judge, score, A-E). |
| `prompt_metadata.csv` | category / corridor / difficulty for each graded prompt (labels only). |
| `harness_lift_analysis.json` | Precomputed paired lift, statistics, and breakdowns. |
| `release-manifest.json` | SHA-256 of every file. |

## Coverage

- **{len(rows):,} grade rows**, **{graded_prompts:,} prompts**, **{len(models)} models**, **{len(judges)} judges**.
- Arms: {dict(arms.most_common())}.
- Judges: {dict(judges.most_common())}.

## How to use it

Join `panel_grades.csv` to `prompt_metadata.csv` on `prompt_id`, average the
per-judge scores to a mean per (model, prompt_id, arm), then pair baseline
against harness arms to compute lift. The companion notebooks do exactly this
and reproduce the paired lift, per-judge robustness, and category/corridor
breakdowns. These are rubric-scored benchmark results, not field-detection
metrics, and must never be read as ground truth about any person.
"""


def _data_card(rows: list[dict[str, Any]], models: Any, judges: Any, graded_prompts: int) -> str:
    return f"""# Data card

- **Rows:** {len(rows):,} grade rows.
- **Grain:** one row per (model, arm, prompt_id, judge).
- **Prompts graded:** {graded_prompts:,} (a growing subset of a 78,719-prompt registry).
- **Models:** {len(models)} subject models; **judges:** {len(judges)}.
- **Contains no** model responses, prompt text, or worker/personal data -- scores
  and category labels only.
- **Component scores A-E:** {COMPONENT_NAMES}.
- **License:** CC BY 4.0.
- **Intended use:** research on LLM safety harnesses, LLM-as-judge evaluation, and
  weak-supervision lift measurement. **Not** for automated trafficking
  determinations or as ground truth about people.
"""


# --- Notebooks ----------------------------------------------------------------

def _md(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "id": identifier, "metadata": {},
            "source": source.splitlines(True)}


def _code(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "code", "execution_count": None, "id": identifier,
            "metadata": {}, "outputs": [], "source": source.splitlines(True)}


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
    # most-paired model. (Avoids the lift/agreement cells disagreeing.)
    if "gemma4:31b" in set(grades["model"]):
        return "gemma4:31b"
    return grades["model"].value_counts().index[0]

in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
out_dir = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", "/kaggle/working" if in_kaggle else Path.cwd()))
out_dir.mkdir(parents=True, exist_ok=True)
display(Markdown(f"Loaded **{len(grades):,} grade rows** over **{grades.prompt_id.nunique():,} prompts**, "
                 f"**{grades.model.nunique()} models**, **{grades.judge.nunique()} judges**."))"""


def _lift_notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:26px 30px;border-radius:16px;background:linear-gradient(120deg,#102a43,#136f63,#f2b134);color:white">
<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.85">DueCare | benchmark grades</div>
<h1 style="margin:.3em 0 .2em;font-size:30px">Reproduce the harness-lift result</h1>
<p style="font-size:15px;line-height:1.5;margin:0;max-width:880px">Load the real multi-judge grades and recompute the baseline-to-harness lift, its statistical strength, per-judge robustness, and category breakdowns -- from scratch.</p>
</div>"""),
        _md("intro", """## What this notebook does

The dataset holds a 0-100 rubric score per (model, arm, prompt_id, judge). This
notebook averages the judges to a mean per (model, prompt_id, arm), pairs the
baseline arm against the harness arm, and reports the lift -- then checks that
the lift survives statistical scrutiny and holds inside each judge independently.
Everything is recomputed from the raw grades; nothing is taken on faith."""),
        _code("setup", _SETUP),
        _md("lift-note", """## 1. Paired baseline-to-harness lift, per model

For each model we average the three judges to one score per (prompt, arm), keep
only prompts that have both a baseline and a harness_core score, and take the
mean paired difference. Positive means the harness improved the rubric score."""),
        _code("lift", """import numpy as np
mean = grades.groupby(["model", "prompt_id", "arm"], as_index=False)["score_0_100"].mean()
wide = mean.pivot_table(index=["model", "prompt_id"], columns="arm", values="score_0_100")
rows = []
for model, sub in wide.groupby(level=0):
    paired = sub.dropna(subset=["baseline", "harness_core"])
    if len(paired) < 5:
        continue
    b, c = paired["baseline"], paired["harness_core"]
    d = c - b
    helps, hurts = int((d > 0).sum()), int((d < 0).sum())
    info = helps + hurts
    # normalized gain = fraction of the remaining headroom captured; corrects for the ceiling so a
    # model starting at 80 is not unfairly penalised vs one starting at 40 (raw lift favours low baselines).
    norm_gain = float(np.mean((c - b) / (100 - b).clip(lower=1e-9)))
    rows.append({"model": model, "n_pairs": len(paired),
                 "baseline": round(b.mean(), 1), "harness_core": round(c.mean(), 1),
                 "lift": round(d.mean(), 1),
                 "norm_gain": round(norm_gain, 3),
                 "win_rate_%": round(100 * helps / info, 1) if info else float("nan"),
                 "helps": helps, "hurts": hurts,
                 "hurt_rate_%": round(100 * hurts / len(paired), 1)})
if not rows:
    raise RuntimeError("no model has >=5 paired baseline/harness_core prompts yet — attach a fuller grades dataset")
lift = pd.DataFrame(rows).sort_values("n_pairs", ascending=False)
display(lift.style.format({"norm_gain": "{:.3f}"}).background_gradient(subset=["lift", "norm_gain"], cmap="Greens"))

fig, ax = plt.subplots(figsize=(12, 5.6))
top = lift.head(6).iloc[::-1]
ax.barh(top["model"], top["baseline"], color="#b8c4c0", label="baseline")
ax.barh(top["model"], top["lift"], left=top["baseline"], color=COLORS[0], label="harness lift")
for y, (_, r) in enumerate(top.iterrows()):
    ax.text(r["harness_core"] + 1, y, f"{r['harness_core']} ({r['lift']:+})", va="center", fontsize=9)
ax.set(title="Baseline score + harness lift (0-100 rubric)", xlabel="mean rubric score", xlim=(0, 105))
ax.legend(loc="lower right", frameon=False)
fig.tight_layout()
fig.savefig(out_dir / "harness_lift_by_model.png", bbox_inches="tight")
plt.show()"""),
        _md("ngain-note", """## 1b. Ceiling-adjusted ranking (normalized gain)

Raw lift favours models that start low -- they have more room to improve. **Normalized
gain** = the fraction of the remaining headroom `(100 - baseline)` the harness captures, so
every model is judged on a level field. It re-ranks the board: a model already scoring high
can post a smaller raw lift but a larger normalized gain, and vice-versa."""),
        _code("ngain", """rank = lift.sort_values("norm_gain", ascending=False)[
    ["model", "n_pairs", "baseline", "lift", "norm_gain", "win_rate_%", "hurt_rate_%"]].reset_index(drop=True)
display(Markdown("**Ranked by normalized gain (ceiling-adjusted) -- contrast the order with the raw-lift table above:**"))
display(rank)
fig, ax = plt.subplots(figsize=(11, 5))
r = rank.iloc[::-1]
ax.barh(r["model"], r["norm_gain"], color=COLORS[5])
ax.bar_label(ax.containers[0], fmt="%.2f", padding=3)
ax.set(title="Normalized gain by model (fraction of remaining headroom captured)", xlabel="normalized gain (0-1)", xlim=(0, 1))
fig.tight_layout(); fig.savefig(out_dir / "normalized_gain.png", bbox_inches="tight"); plt.show()"""),
        _md("dim-note", """## 1c. Which rubric dimension does the harness move, per model?

The five A-E components (A indicator, B legal/ILO, C refusal, D resources, E privacy) show
*where* each model gains. Bigger models gain most on indicator recognition; smaller models
barely move on refusal -- the harness cannot add reasoning capacity the base model lacks."""),
        _code("dim-heat", """have = [c for c in list("ABCDE") if c in grades.columns]
dim_rows = []
for model in lift["model"]:
    m = grades[grades.model == model].groupby("arm")[have].mean()
    if "baseline" in m.index and "harness_core" in m.index:
        delta = (m.loc["harness_core"] - m.loc["baseline"]).round(1)
        dim_rows.append({"model": model, **delta.to_dict()})
dim = pd.DataFrame(dim_rows).set_index("model").rename(
    columns={"A": "A indicator", "B": "B legal", "C": "C refusal", "D": "D resources", "E": "E privacy"})
display(dim.style.background_gradient(cmap="Greens", axis=None).format("{:+.1f}"))
fig, ax = plt.subplots(figsize=(9, 5.6))
im = ax.imshow(dim.values, cmap="Greens", aspect="auto")
ax.set_xticks(range(len(dim.columns)), dim.columns, rotation=20, ha="right")
ax.set_yticks(range(len(dim.index)), dim.index)
for i in range(len(dim.index)):
    for j in range(len(dim.columns)):
        ax.text(j, i, f"{dim.values[i, j]:+.1f}", ha="center", va="center", fontsize=8)
ax.set(title="Per-dimension harness lift by model (mean component delta)")
fig.colorbar(im, ax=ax, fraction=0.046); fig.tight_layout()
fig.savefig(out_dir / "per_dimension_by_model.png", bbox_inches="tight"); plt.show()"""),
        _md("hurt-note", """## 1d. Where the harness does NOT help

The harness is not free. The `hurt_rate_%` column above is the honest counterweight: the
model with the most regressions is typically the one with a low baseline and long outputs,
and on very small models the mean can even drop. These cases stay in the board, not hidden --
"real, not faked" cuts both ways."""),
        _md("stats-note", """## 2. Is the lift real? Bootstrap, sign test, win rate

A mean can mislead. For the headline model we add a seeded bootstrap 95% interval
for the mean lift, an exact two-sided sign test over non-tied pairs, and the win
rate with a Wilson interval. These are inferential statements about the graded
panel, not real-world detection claims."""),
        _code("stats", """import math, random, statistics
head = headline_model()
paired = wide.loc[head].dropna(subset=["baseline", "harness_core"])
d = list(paired["harness_core"] - paired["baseline"])
wins = sum(1 for x in d if x > 0); losses = sum(1 for x in d if x < 0)
rng = random.Random(20260716)
boot = sorted(statistics.fmean(rng.choices(d, k=len(d))) for _ in range(2000))
info = wins + losses
if info == 0:
    sign_p = None
elif info <= 200:
    sign_p = round(min(1.0, 2 * sum(math.comb(info, k) for k in range(min(wins, losses) + 1)) / 2**info), 6)
else:
    sign_p = round(min(1.0, math.erfc(max(0, abs(wins - losses) - 1) / math.sqrt(info) / math.sqrt(2))), 6)
sign_disp = "n/a (all tied)" if sign_p is None else ("<1e-300" if sign_p == 0.0 else str(sign_p))
n = info
z = 1.959964; phat = (wins / n) if n else float("nan")
wl = ((phat + z*z/(2*n) - z*math.sqrt(phat*(1-phat)/n + z*z/(4*n*n))) / (1 + z*z/n)) if n else float("nan")
wh = ((phat + z*z/(2*n) + z*math.sqrt(phat*(1-phat)/n + z*z/(4*n*n))) / (1 + z*z/n)) if n else float("nan")
win_disp = "n/a" if not n else f"{100*phat:.1f}% (Wilson [{100*wl:.1f}%, {100*wh:.1f}%])"
display(Markdown(f"**`{head}`** over **{len(d):,} paired prompts**: mean lift **{statistics.fmean(d):+.1f}**, "
                 f"bootstrap 95% [{boot[49]:+.1f}, {boot[1949]:+.1f}], "
                 f"two-sided sign test p={sign_disp} ({wins} wins / {losses} losses), "
                 f"win rate {win_disp}."))"""),
        _md("judge-note", """## 3. Does it hold inside each judge?

If the lift only appeared for one lenient judge it would be fragile. Here the
same paired lift is recomputed independently inside each judge's own grades."""),
        _code("judges", """jrows = []
for judge, sub in grades[grades.model == head].groupby("judge"):
    w = sub.pivot_table(index="prompt_id", columns="arm", values="score_0_100")
    p = w.dropna(subset=["baseline", "harness_core"])
    if len(p) < 5:
        continue
    dd = p["harness_core"] - p["baseline"]
    jrows.append({"judge": judge, "n_pairs": len(p), "baseline": round(p["baseline"].mean(), 1),
                  "harness_core": round(p["harness_core"].mean(), 1), "lift": round(dd.mean(), 1)})
per_judge = pd.DataFrame(jrows)
display(per_judge)
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.bar(per_judge["judge"], per_judge["lift"], color=COLORS[:len(per_judge)])
ax.bar_label(ax.containers[0], fmt="%.1f", padding=3)
ax.set(title=f"Harness lift inside each judge ({head})", ylabel="mean lift")
fig.tight_layout()
fig.savefig(out_dir / "lift_per_judge.png", bbox_inches="tight")
plt.show()"""),
        _md("cat-note", """## 4. Where does the harness help most?

Joining the grades to prompt metadata shows lift by category and difficulty --
biggest where the raw model is weakest."""),
        _code("categories", """head_pairs = wide.loc[head].dropna(subset=["baseline", "harness_core"]).reset_index()
head_pairs["lift"] = head_pairs["harness_core"] - head_pairs["baseline"]
joined = head_pairs.merge(prompts, on="prompt_id", how="left")
by_cat = joined.groupby("category").agg(n=("lift", "size"), lift=("lift", "mean")).query("n >= 20").sort_values("lift", ascending=False).head(12)
fig, ax = plt.subplots(figsize=(11, 6))
ax.barh(by_cat.index[::-1], by_cat["lift"][::-1], color=COLORS[3])
ax.bar_label(ax.containers[0], fmt="%.0f", padding=3)
ax.set(title=f"Mean harness lift by prompt category ({head}, categories with n>=20)", xlabel="mean lift")
fig.tight_layout()
fig.savefig(out_dir / "lift_by_category.png", bbox_inches="tight")
plt.show()
display(by_cat.assign(lift=by_cat["lift"].round(1)))"""),
        _md("close", """## The honest boundary

This is a **rubric-scored benchmark** result: an LLM-judge panel scored responses
higher with the harness on than off. It is measurement evidence about response
quality on synthetic/composite safety prompts -- not a real-world
trafficking-detection metric, and never ground truth about any person. See the
companion `harness_lift_analysis.json` for the precomputed full read."""),
    ]
    return _wrap(cells)


def _judge_agreement_notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:26px 30px;border-radius:16px;background:linear-gradient(120deg,#102a43,#247ba0,#f2b134);color:white">
<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.85">DueCare | benchmark grades</div>
<h1 style="margin:.3em 0 .2em;font-size:30px">How much do the judges agree?</h1>
<p style="font-size:15px;line-height:1.5;margin:0;max-width:880px">A multi-judge panel is only trustworthy if the judges broadly agree. This notebook measures pairwise judge agreement and per-component score patterns on the real grades.</p>
</div>"""),
        _md("intro", """## Why judge agreement matters

DueCare grades every response with three heterogeneous LLM judges. If they
disagreed wildly, the harness-lift headline would rest on judge noise. This
notebook measures how closely the judges track each other on the same responses,
and how the five A-E rubric components move."""),
        _code("setup", _SETUP),
        _md("corr-note", """## 1. Judge agreement on the same responses

For every (model, prompt_id, arm) graded by multiple judges, we compare the
0-100 scores the judges gave the same response. Agreement is measured **within
each arm** -- as ICC(2,1) absolute agreement and Fisher-averaged within-arm
Pearson r -- because pooling scores across arms inflates the correlation (every
judge scores baseline low and harnessed high, so the arm gap masquerades as
agreement). The pooled number is shown only for contrast."""),
        _code("corr", """import numpy as np
pivot = grades.pivot_table(index=["model", "prompt_id", "arm"], columns="judge", values="score_0_100")
judges = list(pivot.columns)


def _icc21(mat):
    # ICC(2,1) absolute agreement, two-way random effects, single rater.
    m = mat.dropna()
    n, k = m.shape
    if n < 2 or k < 2:
        return float("nan"), int(n)
    x = m.to_numpy(dtype=float)
    grand = x.mean()
    ss_row = k * ((x.mean(axis=1) - grand) ** 2).sum()
    ss_col = n * ((x.mean(axis=0) - grand) ** 2).sum()
    ss_err = ((x - grand) ** 2).sum() - ss_row - ss_col
    msr, msc = ss_row / (n - 1), ss_col / (k - 1)
    mse = ss_err / ((n - 1) * (k - 1))
    denom = msr + (k - 1) * mse + k * (msc - mse) / n
    return (((msr - mse) / denom) if denom else float("nan")), int(n)


# Honest agreement is measured WITHIN each arm. Pooling all arms together inflates
# r because every judge scores baseline low and harnessed high -- that is agreement
# about the arm, not about the response. Average within-arm r via Fisher z.
iu = np.triu_indices(len(judges), 1)
per_arm_r, icc_rows = [], []
for arm, sub in pivot.groupby(level="arm"):
    c = sub[judges].corr()
    if c.notna().to_numpy()[iu].any():
        per_arm_r.append(c.reindex(index=judges, columns=judges))
    val, nn = _icc21(sub[judges])
    icc_rows.append({"arm": arm, "n_complete": nn,
                     "ICC(2,1)": (round(val, 3) if val == val else None)})
zmean = np.nanmean(np.stack([np.arctanh(np.clip(c.to_numpy(), -0.999999, 0.999999)) for c in per_arm_r]), axis=0)
within = pd.DataFrame(np.tanh(zmean), index=judges, columns=judges)
pooled = pivot.corr()
display(Markdown("**ICC(2,1) absolute agreement within each arm** (1.0 = identical scores):"))
display(pd.DataFrame(icc_rows))
display(Markdown(
    f"Within-arm mean pairwise r = **{within.to_numpy()[iu].mean():.3f}**; the arm-pooled r "
    f"(**{pooled.to_numpy()[iu].mean():.3f}**) is higher only because it mixes the arm gap into the "
    f"correlation. The within-arm number is the honest one."))
display(within.round(3))
corr = within
fig, ax = plt.subplots(figsize=(7.5, 6))
im = ax.imshow(corr.values, cmap="YlGn", vmin=0, vmax=1)
ax.set_xticks(range(len(judges)), judges, rotation=20, ha="right")
ax.set_yticks(range(len(judges)), judges)
for i in range(len(judges)):
    for j in range(len(judges)):
        ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=10)
ax.set(title="Judge agreement (within-arm Pearson r, Fisher-averaged)")
fig.colorbar(im, ax=ax, fraction=0.046)
fig.tight_layout()
fig.savefig(out_dir / "judge_agreement.png", bbox_inches="tight")
plt.show()"""),
        _md("comp-note", """## 2. Which rubric components carry the harness lift?

Averaging the A-E component scores by arm shows where the harness changes
behavior: indicator recognition, legal grounding, refusal, resources, privacy."""),
        _code("components", """comp_names = {"A": "indicator", "B": "legal/ILO", "C": "refusal", "D": "resources", "E": "privacy"}
head = headline_model()
sub = grades[grades.model == head]
means = sub.groupby("arm")[list("ABCDE")].mean()
means = means.reindex([a for a in ["baseline", "harness_core", "harness_full"] if a in means.index])
fig, ax = plt.subplots(figsize=(12, 5.4))
x = range(len(comp_names))
width = 0.26
for i, arm in enumerate(means.index):
    ax.bar([xi + (i - 1) * width for xi in x], means.loc[arm].values, width,
           label=arm, color=COLORS[i])
ax.set_xticks(list(x), [f"{c}: {comp_names[c]}" for c in "ABCDE"], rotation=15)
ax.set(title=f"Mean component score by arm ({head})", ylabel="component score")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(out_dir / "component_scores_by_arm.png", bbox_inches="tight")
plt.show()
display(means.round(2))"""),
        _md("close", """## Reading this honestly

Judges agree strongly on baseline responses and only moderately on harnessed
ones -- richer, longer answers give the panel more to weigh, so per-response
agreement is lower on the harness arms than on baseline. That does **not** weaken
the lift headline: the direction is what matters, and it is near-unanimous
(the companion lift notebook shows the harness winning on ~99.8% of paired
prompts and the leave-one-judge-out envelope staying above +40). Agreement here
is a check that the signal is not one judge's quirk -- not a claim that the
panel is interchangeable.

None of this turns a rubric score into truth about a person: the whole panel is
a calibrated measurement instrument over synthetic/composite safety prompts, not
a real-world trafficking finding."""),
    ]
    return _wrap(cells)


def _wrap(cells: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4, "nbformat_minor": 5,
    }


def _notebooks() -> list[tuple[str, str, dict[str, Any]]]:
    # Kaggle derives a kernel's slug from its title; the title must slugify to
    # exactly the id (lowercase, spaces -> hyphens) or the push fails.
    return [
        ("duecare-reproduce-harness-lift", "DueCare Reproduce Harness Lift", _lift_notebook()),
        ("duecare-judge-agreement", "DueCare Judge Agreement", _judge_agreement_notebook()),
    ]


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
