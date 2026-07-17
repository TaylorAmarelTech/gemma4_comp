#!/usr/bin/env python3
# ruff: noqa: E501  (embedded Kaggle notebook cell source has long matplotlib lines)
"""Build a grounded "how statistically solid is the harness lift?" Kaggle notebook.

The autonomous evaluator has graded thousands of real registry prompts across the
baseline / harness_core / harness_full arms with a multi-judge panel. The
companion ``build_benchmark_results_kaggle.py`` publishes those grades as the
dataset ``taylorsamarel/duecare-harness-benchmark-grades`` (scores only -- no
response text, no PII). This builder emits a NEW notebook that attaches that same
dataset and subjects the headline harness-lift claim to peer-review statistical
scrutiny, recomputed from ``panel_grades.csv`` alone:

- paired mean lift with a seeded bootstrap 95% confidence interval,
- a leave-one-judge-out lift envelope (robustness to any single judge),
- Cohen's d for the paired differences,
- an exact two-sided sign test over non-tied pairs,
- win rate with a Wilson 95% score interval,
- a cross-model summary table and a forest plot of lift with CI whiskers.

The notebook is SELF-CONTAINED: it imports no repo module, because the Kaggle
dataset carries no repo code. Every statistic is recomputed inside the notebook
with numpy / pandas / the standard-library ``math`` and ``statistics`` modules.

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
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "statistical_robustness_v1"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
MARKER = ".duecare-statistical-robustness-kaggle"
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
    (path / MARKER).write_text("duecare.statistical_robustness_kaggle.v1\n", encoding="utf-8")
    return path


def _fixture_readme(rows: list[dict[str, Any]], graded_prompts: int) -> str:
    return f"""# Local execution fixture

This directory is a convenience fixture rebuilt from `reports/rich_lift/panel.jsonl`
so `build_statistical_robustness_kaggle.py --execute-local` can run the notebook
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

def headline_model():
    # One canonical head for the whole notebook: prefer gemma4:31b, else the
    # most-graded model, so every cell talks about the same model.
    if "gemma4:31b" in set(grades["model"]):
        return "gemma4:31b"
    return grades["model"].value_counts().index[0]

in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
out_dir = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", "/kaggle/working" if in_kaggle else Path.cwd()))
out_dir.mkdir(parents=True, exist_ok=True)
display(Markdown(f"Loaded **{len(grades):,} grade rows** over **{grades.prompt_id.nunique():,} prompts**, "
                 f"**{grades.model.nunique()} models**, **{grades.judge.nunique()} judges**."))"""


_COMPUTE = """import math
import statistics

import numpy as np

MIN_PAIRS = 5          # a model needs >= 5 paired prompts to appear
BOOT_REPS = 2000       # bootstrap resamples for the mean-lift CI
SEED = 20260716        # fixed seed -> reproducible interval
Z = 1.959964           # standard-normal 97.5th percentile


def bootstrap_ci(diffs, reps=BOOT_REPS, seed=SEED):
    # Seeded nonparametric bootstrap of the mean paired difference. Resampling is
    # done in blocks so the allocation stays bounded regardless of n, while the
    # fixed seed keeps the draw sequence -- and therefore the interval -- reproducible.
    arr = np.asarray(diffs, dtype=float)
    n = arr.size
    if n == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = np.empty(reps, dtype=float)
    block = max(1, 2_000_000 // max(n, 1))
    i = 0
    while i < reps:
        b = min(block, reps - i)
        means[i:i + b] = arr[rng.integers(0, n, size=(b, n))].mean(axis=1)
        i += b
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def cohens_d(diffs):
    # Paired (within-subject) Cohen's d_z = mean(d) / sd(d), using the sample sd.
    if len(diffs) < 2:
        return float("nan"), float("nan")
    sd = statistics.stdev(diffs)
    if sd <= 0:
        return float("nan"), sd
    return statistics.fmean(diffs) / sd, sd


def sign_test_p(wins, losses):
    # Exact two-sided sign test over non-tied pairs. Exact binomial tail via
    # math.comb while it is cheap (<= 200 informative pairs); a continuity-
    # corrected normal approximation above that. Returns None when all pairs tie.
    info = wins + losses
    if info == 0:
        return None
    if info <= 200:
        tail = sum(math.comb(info, k) for k in range(min(wins, losses) + 1))
        return min(1.0, 2 * tail / 2 ** info)
    z = (abs(wins - losses) - 1) / math.sqrt(info)
    return min(1.0, math.erfc(max(0.0, z) / math.sqrt(2)))


def sign_p_display(p):
    if p is None:
        return "n/a (all tied)"
    if p == 0.0:                       # underflowed to exactly 0.0
        return "<1e-300"
    return f"{p:.2e}" if p < 1e-4 else f"{p:.4f}"


def wilson(wins, n):
    # Wilson 95% score interval for the win rate over non-tied pairs (well-behaved
    # near 100%, unlike the normal approximation). Guards the empty-pair case.
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    phat = wins / n
    denom = 1 + Z * Z / n
    center = (phat + Z * Z / (2 * n)) / denom
    half = Z * math.sqrt(phat * (1 - phat) / n + Z * Z / (4 * n * n)) / denom
    return 100 * phat, 100 * (center - half), 100 * (center + half)


def lojo_envelope(model):
    # Leave-one-judge-out: drop each judge in turn, re-average the remaining judges
    # per (prompt_id, arm), re-pair baseline vs harness_core, and take the mean lift.
    sub = grades[grades.model == model]
    lifts = {}
    for drop in sorted(sub["judge"].unique()):
        kept = sub[sub.judge != drop]
        w = kept.pivot_table(index="prompt_id", columns="arm", values="score_0_100", aggfunc="mean")
        if "baseline" not in w or "harness_core" not in w:
            continue
        pair = w.dropna(subset=["baseline", "harness_core"])
        if len(pair) >= MIN_PAIRS:
            lifts[drop] = float((pair["harness_core"] - pair["baseline"]).mean())
    return lifts


# Mean over judges -> one score per (model, prompt_id, arm); then pair the arms.
mean_all = grades.groupby(["model", "prompt_id", "arm"], as_index=False)["score_0_100"].mean()
wide = mean_all.pivot_table(index=["model", "prompt_id"], columns="arm", values="score_0_100")

records, detail = [], {}
for model in sorted(wide.index.get_level_values(0).unique()):
    if "baseline" not in wide.columns or "harness_core" not in wide.columns:
        break
    sub = wide.loc[model].dropna(subset=["baseline", "harness_core"])
    if len(sub) < MIN_PAIRS:
        continue
    b = sub["baseline"].to_numpy(dtype=float)
    c = sub["harness_core"].to_numpy(dtype=float)
    diffs = c - b
    dlist = [float(x) for x in diffs]
    wins = int((diffs > 0).sum()); losses = int((diffs < 0).sum())
    ties = int((diffs == 0).sum()); info = wins + losses
    mean_lift = statistics.fmean(dlist)
    boot_lo, boot_hi = bootstrap_ci(diffs)
    d_z, sd = cohens_d(dlist)
    p = sign_test_p(wins, losses)
    win_rate, wl, wh = wilson(wins, info)
    lojo = lojo_envelope(model)
    lvals = list(lojo.values())
    lmin = min(lvals) if lvals else float("nan")
    lmax = max(lvals) if lvals else float("nan")
    records.append({
        "model": model, "n_pairs": len(sub),
        "baseline": round(float(b.mean()), 1), "harness_core": round(float(c.mean()), 1),
        "lift": round(mean_lift, 1), "boot_lo": round(boot_lo, 1), "boot_hi": round(boot_hi, 1),
        "cohen_d": round(d_z, 2) if d_z == d_z else float("nan"),
        "sd_diff": round(sd, 1) if sd == sd else float("nan"),
        "wins": wins, "losses": losses, "ties": ties, "info": info,
        "sign_p": sign_p_display(p),
        "win_rate_%": round(win_rate, 1) if win_rate == win_rate else float("nan"),
        "wilson_lo_%": round(wl, 1) if wl == wl else float("nan"),
        "wilson_hi_%": round(wh, 1) if wh == wh else float("nan"),
        "lojo_min": round(lmin, 1) if lmin == lmin else float("nan"),
        "lojo_max": round(lmax, 1) if lmax == lmax else float("nan"),
        "lojo_spread": round(lmax - lmin, 2) if (lmin == lmin and lmax == lmax) else float("nan"),
        "n_judges": len(lojo),
    })
    detail[model] = {"diffs": dlist, "mean_lift": mean_lift,
                     "boot_lo": boot_lo, "boot_hi": boot_hi, "lojo": lojo}

if not records:
    raise RuntimeError("no model has >=5 paired baseline/harness_core prompts yet -- attach a fuller grades dataset")
robust = pd.DataFrame(records).sort_values("n_pairs", ascending=False).reset_index(drop=True)

head = headline_model()
hd = next((r for r in records if r["model"] == head), records[0])
display(Markdown(
    f"**Headline model `{hd['model']}`** over **{hd['n_pairs']:,} paired prompts**: "
    f"mean lift **{hd['lift']:+.1f}** (bootstrap 95% [{hd['boot_lo']:+.1f}, {hd['boot_hi']:+.1f}]), "
    f"Cohen's d **{hd['cohen_d']:+.2f}**, sign-test p **{hd['sign_p']}**, "
    f"win rate **{hd['win_rate_%']}%** (Wilson [{hd['wilson_lo_%']}%, {hd['wilson_hi_%']}%]), "
    f"leave-one-judge-out lift envelope **[{hd['lojo_min']:+.1f}, {hd['lojo_max']:+.1f}]**."))
display(robust[["model", "n_pairs", "baseline", "harness_core", "lift", "boot_lo", "boot_hi"]]
        .style.format({"lift": "{:+.1f}", "boot_lo": "{:+.1f}", "boot_hi": "{:+.1f}"})
        .background_gradient(subset=["lift"], cmap="Greens"))"""


_LOJO = """head = headline_model()
lojo_tbl = robust[["model", "n_judges", "lift", "lojo_min", "lojo_max", "lojo_spread"]].copy()
display(Markdown("**Envelope of the mean lift as each judge is dropped in turn.** A tight "
                 "`lojo_spread` (max minus min) means no single judge is carrying the result."))
display(lojo_tbl.style.format({"lift": "{:+.1f}", "lojo_min": "{:+.1f}", "lojo_max": "{:+.1f}", "lojo_spread": "{:.2f}"})
        .background_gradient(subset=["lojo_spread"], cmap="OrRd"))

hl = detail[head]["lojo"]
if hl:
    per = pd.DataFrame([{"judge_dropped": j, "lift_without_it": round(v, 1)} for j, v in sorted(hl.items())])
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.axhline(detail[head]["mean_lift"], color="#5b5f68", ls="--", lw=1.2, label="all-judge lift")
    ax.bar(per["judge_dropped"], per["lift_without_it"], color=COLORS[:len(per)])
    ax.bar_label(ax.containers[0], fmt="%.1f", padding=3)
    ax.set(title=f"Lift with each judge left out ({head})", ylabel="mean lift (remaining judges)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "leave_one_judge_out.png", bbox_inches="tight")
    plt.show()
    display(per)
else:
    display(Markdown(f"`{head}` has too few judges for a leave-one-out envelope."))"""


_COHEN = """def d_band(x):
    if x != x:            # nan
        return "n/a"
    a = abs(x)
    return "negligible" if a < 0.2 else "small" if a < 0.5 else "medium" if a < 0.8 else "large"

cohen_tbl = robust[["model", "n_pairs", "lift", "sd_diff", "cohen_d"]].copy()
cohen_tbl["magnitude"] = cohen_tbl["cohen_d"].map(d_band)
display(Markdown("**Cohen's d for the paired differences** = mean(d) / sd(d). Conventional bands "
                 "(Cohen 1988): 0.2 small, 0.5 medium, 0.8 large. This is a within-subject effect "
                 "size on the graded panel, not a real-world effect size."))
display(cohen_tbl.style.format({"lift": "{:+.1f}", "sd_diff": "{:.1f}", "cohen_d": "{:+.2f}"})
        .background_gradient(subset=["cohen_d"], cmap="Greens"))"""


_SIGN = """sign_tbl = robust[["model", "wins", "losses", "ties", "info", "sign_p"]].copy()
display(Markdown("**Exact two-sided sign test** over the non-tied pairs (exact binomial tail via "
                 "`math.comb` while informative pairs <= 200, else a continuity-corrected normal "
                 "approximation). `p` reads `<1e-300` when it underflows to zero, and `n/a (all tied)` "
                 "when there are no informative pairs."))
display(sign_tbl.rename(columns={"info": "informative_pairs"}))"""


_WIN = """win_tbl = robust[["model", "info", "win_rate_%", "wilson_lo_%", "wilson_hi_%"]].copy()
display(Markdown("**Win rate** = share of non-tied pairs the harness improves, with a **Wilson 95%** "
                 "score interval. The interval is guarded against the empty-pair case and stays inside "
                 "[0, 100] even when the win rate is near 100%."))
display(win_tbl.rename(columns={"info": "non_tied_pairs"})
        .style.format({"win_rate_%": "{:.1f}", "wilson_lo_%": "{:.1f}", "wilson_hi_%": "{:.1f}"})
        .background_gradient(subset=["win_rate_%"], cmap="Greens", vmin=0, vmax=100))

fig, ax = plt.subplots(figsize=(11, 0.6 * len(win_tbl) + 2))
r = win_tbl.iloc[::-1].reset_index(drop=True)
y = list(range(len(r)))
xerr = np.clip(np.vstack([r["win_rate_%"] - r["wilson_lo_%"], r["wilson_hi_%"] - r["win_rate_%"]]).astype(float), 0, None)
ax.errorbar(r["win_rate_%"], y, xerr=xerr, fmt="o", color=COLORS[0], ecolor="#9bbcb4", capsize=4, lw=0, markersize=7)
ax.axvline(50, color="#d1495b", ls="--", lw=1, label="chance (50%)")
ax.set_yticks(y, r["model"])
ax.set(title="Win rate with Wilson 95% interval, by model", xlabel="win rate (%)", xlim=(0, 105))
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(out_dir / "win_rate_wilson.png", bbox_inches="tight")
plt.show()"""


_SUMMARY = """display(Markdown("### Full robustness summary (every model with >= 5 paired prompts)"))
summary = robust[["model", "n_pairs", "baseline", "harness_core", "lift", "boot_lo", "boot_hi",
                  "cohen_d", "sign_p", "win_rate_%", "lojo_min", "lojo_max"]]
display(summary.style.format({
    "lift": "{:+.1f}", "boot_lo": "{:+.1f}", "boot_hi": "{:+.1f}", "cohen_d": "{:+.2f}",
    "win_rate_%": "{:.1f}", "lojo_min": "{:+.1f}", "lojo_max": "{:+.1f}"})
    .background_gradient(subset=["lift", "cohen_d"], cmap="Greens"))

# Forest plot: mean lift with the bootstrap 95% CI as whiskers.
r = robust.iloc[::-1].reset_index(drop=True)
y = list(range(len(r)))
xerr = np.clip(np.vstack([r["lift"] - r["boot_lo"], r["boot_hi"] - r["lift"]]).astype(float), 0, None)
fig, ax = plt.subplots(figsize=(11, 0.7 * len(r) + 2))
ax.errorbar(r["lift"], y, xerr=xerr, fmt="o", color=COLORS[0], ecolor="#9bbcb4", capsize=4, lw=0, markersize=8)
ax.axvline(0, color="#d1495b", ls="--", lw=1, label="no effect")
ax.set_yticks(y, r["model"])
lo = min(0.0, float(r["boot_lo"].min())); hi = float(r["boot_hi"].max())
for i, row in r.iterrows():
    ax.text(row["boot_hi"] + 0.4, i, f"{row['lift']:+.1f} [{row['boot_lo']:+.1f}, {row['boot_hi']:+.1f}]", va="center", fontsize=8)
ax.set(title="Forest plot: mean harness lift with bootstrap 95% CI, per model",
       xlabel="mean paired lift (0-100 rubric)", xlim=(lo - 2, hi + 0.4 * (hi - lo) + 8))
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(out_dir / "forest_lift_ci.png", bbox_inches="tight")
plt.show()"""


def _robustness_notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:26px 30px;border-radius:16px;background:linear-gradient(120deg,#102a43,#5b3f7a,#136f63);color:white">
<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.85">DueCare | benchmark grades</div>
<h1 style="margin:.3em 0 .2em;font-size:30px">How statistically solid is the harness lift?</h1>
<p style="font-size:15px;line-height:1.5;margin:0;max-width:880px">A mean can flatter. This notebook takes the real multi-judge grades and puts the baseline-to-harness lift through peer-review scrutiny: a seeded bootstrap interval, a leave-one-judge-out envelope, Cohen's d, an exact sign test, and a Wilson win-rate interval -- all recomputed from the scores, nothing on faith.</p>
</div>"""),
        _md("intro", """## What this notebook does

The dataset holds a 0-100 rubric score per (model, arm, prompt_id, judge). For
every model with at least five paired prompts, this notebook averages the judges
to one score per (prompt, arm), pairs the **baseline** arm against **harness_core**,
and then asks whether the resulting lift survives statistical scrutiny:

1. **Paired mean lift + a seeded bootstrap 95% CI** -- is the interval clear of zero?
2. **Leave-one-judge-out envelope** -- does the lift hold when any single judge is dropped?
3. **Cohen's d** for the paired differences -- how large is the effect?
4. **Exact two-sided sign test** over non-tied pairs -- is the direction near-certain?
5. **Win rate + Wilson 95% interval** -- on what share of prompts does it help?
6. A **cross-model summary** and a **forest plot** of lift with CI whiskers.

Everything is recomputed here from `panel_grades.csv` with numpy, pandas, and the
standard-library `math` / `statistics` modules -- no repo code, no hidden helpers.
These are inferential statements about a **rubric-scored panel**, not real-world
trafficking-detection claims."""),
        _code("setup", _SETUP),
        _md("compute-note", """## 1. Paired lift with a seeded bootstrap 95% CI

For each model we keep prompts scored in both the baseline and the harness_core
arm, take the mean paired difference, and bootstrap that mean 2,000 times under a
fixed seed. If the 95% interval sits well above zero, the mean lift is not an
artefact of a few lucky prompts. The cell below computes every statistic used in
the rest of the notebook once, then shows the paired lift and its interval."""),
        _code("compute", _COMPUTE),
        _md("lojo-note", """## 2. Leave-one-judge-out envelope

A three-judge panel is only reassuring if no single judge carries the headline.
Here we drop each judge in turn, re-average the remaining judges, re-pair, and
recompute the lift. The **envelope** -- the min and max lift across those drops --
shows how much the result can move when any one judge is removed. A tight envelope
is the honest evidence that the lift is a panel property, not one judge's quirk."""),
        _code("lojo", _LOJO),
        _md("cohen-note", """## 3. Cohen's d for the paired differences

The bootstrap says the mean lift is real; Cohen's d says how *big* it is relative
to the spread of the per-prompt differences. `d_z = mean(d) / sd(d)` is the paired
(within-subject) effect size -- comparable across models even when their raw score
ranges differ."""),
        _code("cohen", _COHEN),
        _md("sign-note", """## 4. Exact two-sided sign test

The bootstrap and Cohen's d both lean on the size of the differences. The sign test
throws that away and asks only: of the prompts where the harness changed the score
at all, how surprising is it that it helped on so many? It is a distribution-free
check that the *direction* is not chance."""),
        _code("sign", _SIGN),
        _md("win-note", """## 5. Win rate with a Wilson 95% interval

The win rate is the share of non-tied pairs the harness improves. Near 100% the
ordinary normal interval spills past 1.0; the **Wilson** score interval stays
inside [0, 100] and is the honest way to bound a proportion this lopsided."""),
        _code("win", _WIN),
        _md("summary-note", """## 6. Cross-model summary and forest plot

One table and one plot pull the five checks together. The forest plot draws each
model's mean lift with its bootstrap 95% CI as whiskers, against a dashed
no-effect line -- the standard way to read many effects and their uncertainty at
a glance."""),
        _code("summary", _SUMMARY),
        _md("limits", """## Two limits worth stating plainly

These statistics are honest about *sampling* uncertainty, but two structural
limits remain, and no confidence interval can fix either one:

1. **The judges are LLMs, not human experts.** Every score here comes from an
   LLM-as-judge panel. The judges agree with one another well (see the companion
   judge-agreement notebook), but agreement is not the same as expert validity. A
   panel of qualified caseworkers grading a sample would be the stronger -- and
   still-missing -- ground truth.
2. **The rubric preamble is a possible placebo confound.** The harness prepends a
   structured safety rubric to the prompt, so part of the measured lift could come
   from *any* long, on-topic preamble priming a more careful answer rather than
   from the harness's specific content. The honest next control is a
   **length-matched placebo arm**: an equally long but content-neutral preamble.
   If the harness still beats the placebo, the effect is the harness; if it does
   not, some of the lift is priming. That arm is not in this dataset yet."""),
        _md("close", """## The honest boundary

Every number above is an inferential statement about a **rubric-scored panel** of
synthetic / composite safety prompts: an LLM-judge panel scored responses higher
with the harness on than off, and that gap survives bootstrap resampling, the
leave-one-judge-out envelope, an exact sign test, and a Wilson interval. It is
measurement evidence about response quality -- not a real-world
trafficking-detection metric, and never ground truth about any person."""),
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
        ("duecare-harness-statistical-robustness",
         "DueCare Harness Statistical Robustness",
         _robustness_notebook()),
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
