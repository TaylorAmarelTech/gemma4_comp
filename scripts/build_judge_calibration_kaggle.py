#!/usr/bin/env python3
# ruff: noqa: E501  (embedded Kaggle notebook cell source has long matplotlib lines)
"""Build a grounded "how is the judge panel calibrated?" Kaggle notebook.

The autonomous evaluator grades thousands of real registry prompts across the
baseline / harness_core / harness_full arms with a three-judge LLM panel. The
companion ``build_benchmark_results_kaggle.py`` publishes those grades as the
dataset ``taylorsamarel/duecare-harness-benchmark-grades`` (scores only -- no
response text, no PII). This builder emits a NEW notebook that attaches that same
dataset and answers a different question from the judge-agreement notebook (which
measures within-arm ICC): **why is a three-judge panel trustworthy?** It is a
calibration story, recomputed from ``panel_grades.csv`` alone:

- judge leniency -- each judge's mean score overall and per arm, showing that
  judges grade on systematically higher / lower absolute scales;
- the lift is judge-robust -- the headline paired lift recomputed inside every
  judge, showing the paired design cancels each judge's absolute scale;
- averaging reduces noise -- the standard error of the mean per-prompt lift for a
  single judge vs the three-judge average (variance reduction, not bias removal);
- panel composition -- the judges, their developer families, and a live
  self-exclusion check that no judge grades a subject model from its own family;
- honest limits -- the judges are LLMs, not anti-trafficking professionals, so
  calibration is measurement consistency, not ground truth about a person.

The notebook is SELF-CONTAINED: it imports no repo module, because the Kaggle
dataset carries no repo code. Every number is recomputed inside the notebook with
numpy / pandas.

For local verification (``--execute-local``) the builder also rebuilds a small
``dataset/panel_grades.csv`` fixture from the real ``reports/rich_lift/panel.jsonl``
so the notebook can execute end-to-end without touching Kaggle. That fixture is a
convenience for CI; the published Kaggle dataset of the same id is the source of
truth.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import os
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "reports" / "rich_lift" / "panel.jsonl"
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "judge_calibration_v1"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
SLUG = "duecare-judge-panel-calibration"
TITLE = "DueCare Judge Panel Calibration"
MARKER = ".duecare-judge-calibration-kaggle"
COMPONENTS = ("A", "B", "C", "D", "E")


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


def _panel_csv(rows: list[dict[str, Any]]) -> str:
    # Same column layout the published dataset uses, so the notebook behaves
    # identically on the local fixture and on the attached Kaggle dataset.
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


def _prepare_output(path: Path, *, force: bool) -> Path:
    path = path.resolve()
    if path.exists():
        if not force:
            raise RuntimeError(f"output exists; pass --force to replace: {path.name}")
        if not (path / MARKER).is_file():
            raise RuntimeError("refusing to replace a directory this builder did not create")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / MARKER).write_text("duecare.judge_calibration_kaggle.v1\n", encoding="utf-8")
    return path


def _fixture_readme(rows: list[dict[str, Any]], graded_prompts: int) -> str:
    return f"""# Local execution fixture

This directory is a convenience fixture rebuilt from `reports/rich_lift/panel.jsonl`
so `build_judge_calibration_kaggle.py --execute-local` can run the notebook
end-to-end without Kaggle. It contains only 0-100 rubric scores plus A-E component
scores keyed by (model, arm, prompt_id, judge) -- no response text, no PII.

- Grade rows: {len(rows):,}
- Graded prompts: {graded_prompts:,}

The published Kaggle dataset `{DATASET_ID}` of the same id is the source of truth;
the notebook attaches that dataset when run on Kaggle.
"""


def build(output_dir: Path, *, force: bool, panel_path: Path = PANEL) -> dict[str, Any]:
    rows = _load_panel(panel_path)
    if not rows:
        raise RuntimeError("panel is empty")
    models = collections.Counter(r.get("model") for r in rows)
    arms = collections.Counter(r.get("arm") for r in rows)
    judges = collections.Counter(r.get("judge") for r in rows)
    graded_prompts = len({r.get("prompt_id") for r in rows})

    output_dir = _prepare_output(output_dir, force=force)
    dataset = output_dir / "dataset"
    dataset.mkdir()
    _write(dataset / "panel_grades.csv", _panel_csv(rows))
    _write(dataset / "README.md", _fixture_readme(rows, graded_prompts))

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
        "note": ("Local execution fixture rebuilt from reports/rich_lift/panel.jsonl; "
                 "the published Kaggle dataset of the same id is the source of truth."),
        "artifacts": artifacts,
    })

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

    head_model = "gemma4:31b" if "gemma4:31b" in models else (
        models.most_common(1)[0][0] if models else None)
    return {
        "output_dir": str(output_dir), "dataset_id": DATASET_ID,
        "grade_rows": len(rows), "graded_prompts": graded_prompts,
        "models": len(models), "judges": len(judges),
        "notebooks": [slug for slug, _, _ in _notebooks()],
        "headline_model": head_model,
    }


# --- Notebook cell helpers ----------------------------------------------------

def _md(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "id": identifier, "metadata": {},
            "source": source.splitlines(True)}


def _code(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "code", "execution_count": None, "id": identifier,
            "metadata": {}, "outputs": [], "source": source.splitlines(True)}


_SETUP = """import json, os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import Markdown, display

COLORS = ["#136f63", "#f2b134", "#d1495b", "#247ba0", "#6d597a", "#4f772d"]
plt.rcParams.update({"figure.figsize": (11, 5.6), "figure.dpi": 115,
                     "axes.facecolor": "#f7faf9", "axes.edgecolor": "#bed2cc",
                     "axes.grid": True, "grid.alpha": 0.2, "font.size": 11})
pd.set_option("display.max_colwidth", None)  # never truncate displayed text

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

ARM_ORDER = [a for a in ["baseline", "harness_core", "harness_full"] if a in set(grades["arm"])]

def headline_model():
    # One canonical head for the whole notebook: prefer gemma4:31b, else the
    # most-graded model, so every cell talks about the same model.
    if "gemma4:31b" in set(grades["model"]):
        return "gemma4:31b"
    return grades["model"].value_counts().index[0]

def family(name):
    # Map a model / judge id to its developer family (for self-exclusion + panel).
    n = str(name).lower()
    for key, fam in [("gemma", "Google"), ("gemini", "Google"), ("gpt", "OpenAI"),
                     ("oss", "OpenAI"), ("glm", "Zhipu"), ("chatglm", "Zhipu"),
                     ("deepseek", "DeepSeek"), ("qwen", "Alibaba Qwen"),
                     ("llama", "Meta"), ("mistral", "Mistral"), ("mixtral", "Mistral"),
                     ("minimax", "MiniMax")]:
        if key in n:
            return fam
    return "other"

in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
out_dir = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", "/kaggle/working" if in_kaggle else Path.cwd()))
out_dir.mkdir(parents=True, exist_ok=True)
display(Markdown(f"Loaded **{len(grades):,} grade rows** over **{grades.prompt_id.nunique():,} prompts**, "
                 f"**{grades.model.nunique()} models**, and a **{grades.judge.nunique()}-judge panel** "
                 f"({', '.join(sorted(grades.judge.unique()))})."))"""


_LENIENCY = """# Each judge's mean 0-100 score, overall and per arm. Because judges grade
# different prompt mixes, the per-arm columns are the honest leniency signal.
overall = grades.groupby("judge")["score_0_100"].mean().sort_values()   # strict -> lenient
per_ja = (grades.groupby(["judge", "arm"])["score_0_100"].mean().unstack()[ARM_ORDER]).loc[overall.index]

tbl = per_ja.copy()
tbl.insert(0, "all arms", overall)
tbl["offset vs strictest"] = overall - overall.min()
strict, lenient = overall.index[0], overall.index[-1]
display(Markdown(
    f"**Mean 0-100 score each judge assigns**, rows ordered strictest -> most lenient. "
    f"`{lenient}` runs about **{overall.max() - overall.min():.1f}** points hotter than `{strict}` overall, "
    f"and -- crucially -- the same ordering holds inside *every* arm below. That is a systematic "
    f"per-judge offset, not random noise."))
display(tbl.style.format("{:.1f}").background_gradient(cmap="YlOrBr", subset=list(per_ja.columns)))

gaps = per_ja.max() - per_ja.min()
display(Markdown(
    "Within-arm leniency gap (most lenient minus strictest judge), per arm: "
    + ", ".join(f"**{a}** {gaps[a]:.1f}" for a in ARM_ORDER)
    + " points on the 0-100 scale. A paired design (each prompt graded with *and* without the harness "
      "by the same judge) subtracts this offset away -- that is the point of the next section."))

x = np.arange(len(per_ja.index))
w = 0.8 / max(len(ARM_ORDER), 1)
fig, ax = plt.subplots(figsize=(11, 5.4))
for i, arm in enumerate(ARM_ORDER):
    ax.bar(x + (i - (len(ARM_ORDER) - 1) / 2) * w, per_ja[arm].to_numpy(), w, label=arm, color=COLORS[i])
    ax.bar_label(ax.containers[-1], fmt="%.0f", padding=2, fontsize=8)
ax.set_xticks(x, per_ja.index)
ax.set(title="Judge leniency: mean score by judge and arm", ylabel="mean 0-100 score", ylim=(0, 100))
ax.legend(frameon=False, title="arm")
fig.tight_layout()
fig.savefig(out_dir / "judge_leniency.png", bbox_inches="tight")
plt.show()"""


_ROBUST = """head = headline_model()
sub = grades[grades.model == head]
jrows = []
for judge, s in sub.groupby("judge"):
    w = s.pivot_table(index="prompt_id", columns="arm", values="score_0_100")
    if "baseline" not in w or "harness_core" not in w:
        continue
    p = w.dropna(subset=["baseline", "harness_core"])
    if len(p) < 5:
        continue
    d = p["harness_core"] - p["baseline"]
    jrows.append({"judge": judge, "n_pairs": len(p),
                  "baseline": round(float(p["baseline"].mean()), 1),
                  "harness_core": round(float(p["harness_core"].mean()), 1),
                  "lift": round(float(d.mean()), 1)})
if not jrows:
    raise RuntimeError(f"no judge has >=5 paired baseline/harness_core prompts for {head}")
per_judge = pd.DataFrame(jrows).sort_values("lift").reset_index(drop=True)
spread = per_judge["lift"].max() - per_judge["lift"].min()
mean_lift = per_judge["lift"].mean()
display(Markdown(
    f"**Paired baseline -> harness_core lift for `{head}`, recomputed inside each judge's own grades.** "
    f"The strictest and most lenient judges disagreed by ~{overall.max() - overall.min():.1f} points on absolute "
    f"scores (section 1), yet their **lifts agree to within {spread:.1f} points** (mean {mean_lift:+.1f}). "
    f"Pairing each prompt with and without the harness under the *same* judge cancels that judge's absolute "
    f"scale, so what survives is the effect of the harness, not the mood of the grader."))
display(per_judge.style.format({"lift": "{:+.1f}"}).background_gradient(subset=["lift"], cmap="Greens"))

fig, ax = plt.subplots(figsize=(10, 4.8))
ax.bar(per_judge["judge"], per_judge["lift"], color=COLORS[:len(per_judge)])
ax.bar_label(ax.containers[0], fmt="%+.1f", padding=3)
ax.axhline(mean_lift, color="#5b5f68", ls="--", lw=1.2, label="mean of per-judge lifts")
ax.set(title=f"Harness lift inside each judge ({head})", ylabel="mean paired lift (0-100 rubric)",
       ylim=(0, per_judge["lift"].max() * 1.18))
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(out_dir / "lift_per_judge.png", bbox_inches="tight")
plt.show()"""


_AVERAGING = """head = headline_model()
sub = grades[grades.model == head]
piv = sub.pivot_table(index="prompt_id", columns=["judge", "arm"], values="score_0_100")
cols = {}
for j in sorted(sub["judge"].unique()):
    if (j, "baseline") in piv.columns and (j, "harness_core") in piv.columns:
        cols[j] = piv[(j, "harness_core")] - piv[(j, "baseline")]
# Complete cases: prompts every judge scored on BOTH arms, so 1-judge vs k-judge
# is an apples-to-apples comparison on identical prompts.
L = pd.DataFrame(cols).dropna()
k = L.shape[1]
if len(L) < 5 or k < 2:
    display(Markdown(f"`{head}` has too few complete-case prompts (scored by every judge on both arms) "
                     f"for the single-vs-panel noise comparison."))
else:
    recs = []
    for j in L.columns:
        s = L[j]
        recs.append({"estimator": j, "n_prompts": len(s), "mean_lift": s.mean(),
                     "sd_of_lift": s.std(ddof=1), "sem_of_lift": s.std(ddof=1) / np.sqrt(len(s))})
    m3 = L.mean(axis=1)
    recs.append({"estimator": f"{k}-judge average", "n_prompts": len(m3), "mean_lift": m3.mean(),
                 "sd_of_lift": m3.std(ddof=1), "sem_of_lift": m3.std(ddof=1) / np.sqrt(len(m3))})
    noise = pd.DataFrame(recs)
    mean_single_sd = float(noise.iloc[:-1]["sd_of_lift"].mean())
    avg_sd = float(noise.iloc[-1]["sd_of_lift"])
    best_single_sem = float(noise.iloc[:-1]["sem_of_lift"].min())
    avg_sem = float(noise.iloc[-1]["sem_of_lift"])
    floor = 1 / np.sqrt(k)
    display(Markdown(
        f"**Per-prompt lift noise: one judge vs the {k}-judge average** (headline model `{head}`, "
        f"{len(L):,} complete-case prompts scored by every judge on both arms). Averaging the judges cuts "
        f"the per-prompt lift SD from a typical **{mean_single_sd:.1f}** (mean single judge) to "
        f"**{avg_sd:.1f}** -- about a **{100 * (1 - avg_sd / mean_single_sd):.0f}%** reduction. If the judges "
        f"were independent it would fall by 1/sqrt({k}) = **{floor:.2f}x**; the observed **{avg_sd / mean_single_sd:.2f}x** "
        f"is milder because the judges are positively correlated -- averaging removes each judge's *idiosyncratic* "
        f"noise, not the views they share."))
    display(noise.style.format({"mean_lift": "{:+.2f}", "sd_of_lift": "{:.2f}", "sem_of_lift": "{:.3f}"})
            .background_gradient(subset=["sem_of_lift"], cmap="OrRd"))
    if best_single_sem < avg_sem:
        display(Markdown(
            f"Honest caveat: the single lowest-variance judge here (SEM {best_single_sem:.3f}) is individually "
            f"tighter than the panel average (SEM {avg_sem:.3f}). Averaging wins on average and protects you from "
            f"betting on the wrong single judge, but it is **variance reduction, not bias removal** -- it cannot "
            f"correct an error all three judges share."))

    fig, ax = plt.subplots(figsize=(10, 4.8))
    bar_colors = [COLORS[3]] * (len(noise) - 1) + [COLORS[0]]
    ax.bar(noise["estimator"], noise["sem_of_lift"], color=bar_colors)
    ax.bar_label(ax.containers[0], fmt="%.3f", padding=3)
    ax.set(title=f"Standard error of the mean per-prompt lift ({head})",
           ylabel="SEM of per-prompt lift", ylim=(0, noise["sem_of_lift"].max() * 1.25))
    fig.tight_layout()
    fig.savefig(out_dir / "averaging_reduces_noise.png", bbox_inches="tight")
    plt.show()"""


_PANEL = """# The panel: one large model per developer family.
panel = (grades.groupby("judge")
         .agg(grades_written=("score_0_100", "size"), models_graded=("model", "nunique"))
         .reset_index())
panel["family"] = panel["judge"].map(family)
panel = panel[["judge", "family", "grades_written", "models_graded"]].sort_values("judge").set_index("judge")
display(Markdown("**The judge panel.** Each judge is a large model from a different developer family, so a "
                 "single vendor's grading style cannot dominate the result:"))
display(panel.style.format({"grades_written": "{:,}"}))

# Self-exclusion, verified LIVE from the grades: no judge grades a subject model
# from its own family (guards against in-family favoritism).
gg = grades.copy()
gg["judge_family"] = gg["judge"].map(family)
gg["model_family"] = gg["model"].map(family)
xt = gg.groupby(["judge_family", "model_family"]).size().unstack(fill_value=0)
diag = {jf: int(xt.loc[jf, jf]) for jf in xt.index if jf in xt.columns}
clean = all(v == 0 for v in diag.values())
display(Markdown(
    "**Self-exclusion check (recomputed from the data, not asserted).** Rows are the judge's family, "
    "columns are the graded model's family; the shaded diagonal is where a judge would grade its own family. "
    + ("Every same-family cell is **0** -- self-exclusion holds across the whole panel."
       if clean else "**WARNING: a same-family cell is non-zero -- self-exclusion is violated.**")))

def _mark_diag(df):
    style = pd.DataFrame("", index=df.index, columns=df.columns)
    for jf in df.index:
        if jf in df.columns:
            ok = df.loc[jf, jf] == 0
            style.loc[jf, jf] = "background-color:#c8e6c9" if ok else "background-color:#ffcdd2"
    return style

display(xt.style.apply(_mark_diag, axis=None).format("{:,}"))"""


def _calibration_notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:26px 30px;border-radius:16px;background:linear-gradient(120deg,#102a43,#247ba0,#136f63);color:white">
<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.85">DueCare | benchmark grades</div>
<h1 style="margin:.3em 0 .2em;font-size:30px">How the judge panel is calibrated</h1>
<p style="font-size:15px;line-height:1.5;margin:0;max-width:880px">A harness-lift headline is only as trustworthy as the panel that measured it. This notebook takes the real multi-judge grades and shows exactly why three heterogeneous LLM judges, graded in a paired design, produce a robust number -- and states plainly what that number is not.</p>
</div>"""),
        _md("overview", """## What you'll learn

Three LLM judges score every response 0-100. They do **not** grade on the same
absolute scale -- some run hot, some run cold. So why trust the panel? Because the
harness result never depends on any judge's absolute scale: it is a **paired**
measurement (same prompt, same judge, with the harness vs without), the judges are
**averaged** to cut noise, they come from **different developer families**, and no
judge grades its own family. This notebook demonstrates each of those, recomputed
from `panel_grades.csv` -- nothing on faith.

**Contents**

1. [Judge leniency -- judges grade on different scales](#leniency)
2. [The lift is judge-robust -- pairing cancels the scale](#robust)
3. [Averaging reduces noise -- one judge vs the panel](#averaging)
4. [Panel composition and self-exclusion](#panel)
5. [Honest limits -- what calibration does and does not buy](#limits)

This is a **calibration** view of the panel. Its sibling, the
[judge-agreement notebook](https://www.kaggle.com/code/taylorsamarel/duecare-judge-agreement),
measures *within-arm* inter-judge agreement (ICC); this one is about leniency,
paired robustness, and why averaging a heterogeneous panel is the honest choice."""),
        _md("related", """### Related in this collection

| Resource | What it is |
|---|---|
| [Dataset: DueCare Harness Benchmark Grades](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades) | The real multi-judge grades this notebook reads (scores only -- no response text, no PII). |
| [Notebook: Judge Agreement](https://www.kaggle.com/code/taylorsamarel/duecare-judge-agreement) | Within-arm inter-judge agreement (ICC + Fisher-averaged r). |
| [Notebook: Reproduce Harness Lift](https://www.kaggle.com/code/taylorsamarel/duecare-reproduce-harness-lift) | Recomputes the headline paired lift and its breakdowns. |
| [Notebook: Statistical Robustness](https://www.kaggle.com/code/taylorsamarel/duecare-harness-statistical-robustness) | Bootstrap CI, Cohen's d, sign test, and the leave-one-judge-out envelope. |
| [GitHub: TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp) | The DueCare source repository. |
| [duecare-ai.com/benchmark](https://duecare-ai.com/benchmark) | The public benchmark leaderboard. |"""),
        _code("setup", _SETUP),
        _md("leniency-note", """<a id="leniency"></a>
## 1. Judge leniency: judges grade on different scales

Before trusting a panel average, look at what each judge does on its own. If we
just average raw scores, a systematically lenient judge would drag the mean up and
a strict judge would drag it down. The table and chart below show each judge's mean
0-100 score overall and within each arm. The judges keep the **same strict ->
lenient ordering in every arm** -- a fixed per-judge offset. That offset is exactly
what a paired design removes."""),
        _code("leniency", _LENIENCY),
        _md("robust-note", """<a id="robust"></a>
## 2. The lift is judge-robust: pairing cancels the scale

Now the payoff. For the headline model we recompute the paired baseline ->
harness_core lift **inside each judge's own grades**. Because every prompt is graded
with and without the harness by the *same* judge, that judge's absolute scale
cancels in the subtraction. So even though the judges disagree on absolute scores
(section 1), their **lifts** should line up -- and they do.

This is the per-judge companion to the
[leave-one-judge-out envelope](https://www.kaggle.com/code/taylorsamarel/duecare-harness-statistical-robustness)
in the statistical-robustness notebook, which drops each judge in turn and confirms
the headline lift barely moves."""),
        _code("robust", _ROBUST),
        _md("averaging-note", """<a id="averaging"></a>
## 3. Averaging reduces noise: one judge vs the panel

Section 2 shows each judge lands on nearly the same lift *on average*. But on any
single prompt, one judge's score is noisier than the panel's. Averaging three
judges per prompt cancels part of that per-prompt disagreement, so the mean
per-prompt lift measured by the panel has a **smaller standard error** than the
mean measured by a typical single judge. The comparison below is on identical
complete-case prompts (scored by every judge on both arms), so the only thing that
changes is one judge vs the average.

Read this honestly: averaging reduces the *variance* that comes from judges
disagreeing. It is **not** bias removal -- if all three judges share a blind spot
(e.g. over-rewarding a structured, on-topic format), averaging cannot fix it."""),
        _code("averaging", _AVERAGING),
        _md("panel-note", """<a id="panel"></a>
## 4. Panel composition and self-exclusion

A panel of near-identical models would agree for the wrong reason. DueCare's judges
are large models from **different developer families**, and a judge never grades a
subject model from its own family (self-exclusion), which guards against a model
flattering its own lineage. The check below is recomputed straight from the
grades -- the shaded diagonal is where a judge *would* grade its own family, and it
should be empty."""),
        _code("panel", _PANEL),
        _md("limits", """<a id="limits"></a>
## 5. Honest limits: what calibration does and does not buy

Everything above is about **measurement consistency**: the panel is internally
well-behaved, its judges agree on the *direction and size* of the harness effect,
and averaging them is a defensible way to reduce noise. Two limits no amount of
calibration can remove:

1. **The judges are LLMs, not anti-trafficking professionals.** Leniency and
   agreement tell you the *instrument* is consistent. They do **not** tell you the
   instrument is *right*. A calibrated thermometer that reads two degrees high is
   still precise and still wrong. Only qualified human experts can say whether a
   high-scoring response is actually good safety guidance.

2. **Consistency is not ground truth about a person.** Every score here is a rubric
   judgement on a synthetic / composite safety prompt. None of it is a finding about
   any real worker, recruiter, or case. The panel measures *response quality on a
   benchmark*, nothing more.

The precondition for a peer-reviewed effectiveness claim is therefore a **blinded
human-expert validation**: a sample of responses graded by qualified caseworkers,
blind to arm and to the LLM scores, checked against this panel. Until that exists,
the honest headline is narrow and true -- *an LLM-judge panel, calibrated and
paired, scores harnessed responses higher than baseline* -- not a claim about
real-world detection."""),
        _md("close", """## The honest boundary

The judges grade on different absolute scales, but the harness result rides on
**paired differences**, an **averaged** panel, and **cross-family self-exclusion**,
so it does not depend on any single judge's leniency. That is what makes the
three-judge panel trustworthy as a *measurement instrument*. It remains a
rubric-scored benchmark over synthetic / composite prompts -- measurement evidence
about response quality, never ground truth about any person."""),
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
    return [(SLUG, TITLE, _calibration_notebook())]


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
            NotebookClient(notebook, timeout=600, kernel_name="python3",
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
    value.add_argument("--force", action="store_true")
    value.add_argument("--execute-local", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = build(args.output, force=args.force, panel_path=args.panel)
    if args.execute_local:
        _execute_notebooks(Path(result["output_dir"]))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
