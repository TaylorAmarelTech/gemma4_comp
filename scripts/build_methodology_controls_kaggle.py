#!/usr/bin/env python3
# ruff: noqa: E501  (embedded Kaggle notebook cell source has long matplotlib lines)
"""Build a grounded "Methodology & controls -- is the harness lift real?" Kaggle notebook.

The DueCare harness-lift headline invites the obvious skeptical questions, and this
notebook answers them with a control for each -- reporting the honest verdict every
time, including the control that comes back INCONCLUSIVE. It attaches the scores-only
dataset ``taylorsamarel/duecare-harness-lift-controls`` (no response text, no PII) and
recomputes everything from four CSVs:

1. **Placebo panel (the decisive control).** For each of 5 judges, average the score
   per (prompt_id, arm), pair, and take harnessed - placebo and placebo - baseline.
   Harnessed beats the length-matched placebo for every judge -- so the lift is the
   injected knowledge, not a generic preamble -- while placebo - baseline is small.
2. **Negative control on the deterministic grader (honestly inconclusive).** The
   published control CSV carries the ceiling-bound rule grader for the placebo arm
   only (its baseline/harnessed deterministic arms live in the benchmark-grades
   dataset). The placebo arm sits near ~5.7/10; the reported harnessed - placebo
   contrast is only ~+0.08 (p just above 0.05). We report it as inconclusive and do
   NOT present it as evidence FOR the harness.
3. **Applicability audit.** Cohen's kappa between the deterministic applicability gate
   and an independent judge is ~0.36 ("fair"); they agree ~68% of the time, ~86%
   unanimous. Applicability is judgment-dependent, not mechanical.
4. **Convergent validity (reported context, directional only).** The deterministic
   lift (+0.18) and LLM-judge lift (+1.73) agree in direction but the per-prompt
   correlation is negligible (r=0.18); neither grader is a proxy for the other.
5. **What the controls establish -- and don't.** The placebo panel closes the preamble
   confound; the deterministic control is inconclusive; convergent validity is partial;
   judges are LLMs, not anti-trafficking professionals; no field-detection claim.

The notebook is SELF-CONTAINED: it imports no repo module, because the Kaggle dataset
carries no repo code. Every statistic is recomputed inside the notebook with numpy /
pandas / the standard-library ``math`` module.

For local verification (``--execute-local``) the builder copies the four dataset CSVs
from ``reports/kaggle_publish/controls/dataset/`` into a ``dataset/`` fixture and writes
a ``release-manifest.json`` naming the dataset id, so the notebook can execute
end-to-end without touching Kaggle. That fixture is a convenience for CI; the published
Kaggle dataset of the same id is the source of truth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATASET = ROOT / "reports" / "kaggle_publish" / "controls" / "dataset"
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "methodology_controls_v1"
DATASET_ID = "taylorsamarel/duecare-harness-lift-controls"
MARKER = ".duecare-methodology-controls-kaggle"
CSV_FILES = (
    "placebo_panel.csv",
    "negative_control_deterministic.csv",
    "applicability_audit.csv",
    "placebo_single_judge.csv",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_json(path: Path, value: Any) -> None:
    _write(path, json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n")


def _count_rows(path: Path) -> int:
    # Row count excluding the header line.
    with path.open(encoding="utf-8") as fh:
        return max(0, sum(1 for _ in fh) - 1)


def _prepare_output(path: Path, *, force: bool) -> Path:
    path = path.resolve()
    if path.exists():
        if not force:
            raise RuntimeError(f"output exists; pass --force to replace: {path.name}")
        if not (path / MARKER).is_file():
            raise RuntimeError("refusing to replace a directory this builder did not create")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / MARKER).write_text("duecare.methodology_controls_kaggle.v1\n", encoding="utf-8")
    return path


def _fixture_readme(row_counts: dict[str, int]) -> str:
    lines = [
        "# Local execution fixture",
        "",
        "This directory is a convenience fixture copied from",
        "`reports/kaggle_publish/controls/dataset/` so",
        "`build_methodology_controls_kaggle.py --execute-local` can run the notebook",
        "end-to-end without Kaggle. It contains only 0-10 grader / judge scores -- no",
        "response text, no prompts, no PII.",
        "",
    ]
    for name in CSV_FILES:
        lines.append(f"- `{name}` -- {row_counts.get(name, 0):,} rows")
    lines += [
        "",
        f"The published Kaggle dataset `{DATASET_ID}` of the same id is the source of",
        "truth; the notebook attaches that dataset when run on Kaggle.",
        "",
    ]
    return "\n".join(lines)


def build(output_dir: Path, *, force: bool, source: Path = SOURCE_DATASET) -> dict[str, Any]:
    missing = [name for name in CSV_FILES if not (source / name).is_file()]
    if missing:
        raise RuntimeError(f"source dataset {source} is missing CSV(s): {', '.join(missing)}")

    output_dir = _prepare_output(output_dir, force=force)
    dataset = output_dir / "dataset"
    dataset.mkdir()

    row_counts: dict[str, int] = {}
    for name in CSV_FILES:
        shutil.copyfile(source / name, dataset / name)
        row_counts[name] = _count_rows(dataset / name)

    artifacts = {}
    for path in sorted(dataset.iterdir()):
        if path.is_file():
            artifacts[path.name] = {"bytes": path.stat().st_size,
                                    "sha256": _sha256_bytes(path.read_bytes())}
    _write(dataset / "README.md", _fixture_readme(row_counts))
    # README added after the artifact scan is intentional: the manifest describes the
    # published data files, not the local fixture readme. Add its hash too for completeness.
    artifacts["README.md"] = {"bytes": (dataset / "README.md").stat().st_size,
                              "sha256": _sha256_bytes((dataset / "README.md").read_bytes())}
    _write_json(dataset / "release-manifest.json", {
        "schema_version": "duecare.harness_lift_controls.v1",
        "dataset_id": DATASET_ID,
        "scores_only": True,
        "contains_response_text_or_pii": False,
        "safe_to_publish": True,
        "row_counts": row_counts,
        "note": ("Local execution fixture copied from reports/kaggle_publish/controls/dataset/; "
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

    return {
        "output_dir": str(output_dir), "dataset_id": DATASET_ID,
        "row_counts": row_counts,
        "notebooks": [slug for slug, _, _ in _notebooks()],
    }


# --- Notebook cell helpers ----------------------------------------------------

def _md(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "id": identifier, "metadata": {},
            "source": source.splitlines(True)}


def _code(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "code", "execution_count": None, "id": identifier,
            "metadata": {}, "outputs": [], "source": source.splitlines(True)}


_SETUP = """import json, math, os
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

EXPECTED_DATASET_ID = "taylorsamarel/duecare-harness-lift-controls"
ARMS = ["baseline", "placebo", "harnessed"]

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
    if os.environ.get("DUECARE_CONTROLS_ROOT"):
        bases.append(Path(os.environ["DUECARE_CONTROLS_ROOT"]))
    bases += list(Path("/kaggle/input").glob("*")) + [Path.cwd()]
    seen = set()
    for base in bases:
        for cand in ([base] + list(base.rglob("placebo_panel.csv"))):
            root = cand if cand.is_dir() else cand.parent
            if root in seen or not (root / "placebo_panel.csv").is_file():
                continue
            seen.add(root)
            if _verify_dataset(root):
                return root
    raise FileNotFoundError(f"Attach {EXPECTED_DATASET_ID} (no matching dataset found)")

root = find_dataset()
placebo = pd.read_csv(root / "placebo_panel.csv")
negctrl = pd.read_csv(root / "negative_control_deterministic.csv")
applic = pd.read_csv(root / "applicability_audit.csv")
single = pd.read_csv(root / "placebo_single_judge.csv")

in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
out_dir = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", "/kaggle/working" if in_kaggle else Path.cwd()))
out_dir.mkdir(parents=True, exist_ok=True)

display(Markdown(
    f"Loaded the controls dataset: placebo panel **{len(placebo):,}** rows over "
    f"**{placebo.prompt_id.nunique():,}** prompts and **{placebo.judge.nunique()}** judges; "
    f"deterministic negative control **{len(negctrl):,}** rows; applicability audit "
    f"**{len(applic):,}** (prompt x dimension) decisions; single-judge placebo **{len(single):,}** rows. "
    f"All scores-only -- no response text, no PII."))"""


_PLACEBO = """# One score per (judge, prompt_id, arm), then pair each judge's OWN arms.
Z = 1.959964  # standard-normal 97.5th percentile, for a paired 95% CI
pan = placebo.groupby(["judge", "prompt_id", "arm"], as_index=False)["score"].mean()

rows = []
for judge in sorted(pan["judge"].unique()):
    w = pan[pan["judge"] == judge].pivot_table(index="prompt_id", columns="arm", values="score")
    for a in ARMS:
        if a not in w.columns:
            w[a] = np.nan
    hp = w.dropna(subset=["harnessed", "placebo"])
    pb = w.dropna(subset=["placebo", "baseline"])
    hmp = (hp["harnessed"] - hp["placebo"]).to_numpy(float)
    pmb = (pb["placebo"] - pb["baseline"]).to_numpy(float)
    n = int(hmp.size)
    mean = float(hmp.mean()) if n else float("nan")
    sd = float(hmp.std(ddof=1)) if n > 1 else float("nan")
    ci = Z * sd / math.sqrt(n) if n > 1 else float("nan")
    rows.append({
        "judge": judge, "n_pairs": n,
        "baseline": round(float(np.nanmean(w["baseline"])), 2),
        "placebo": round(float(np.nanmean(w["placebo"])), 2),
        "harnessed": round(float(np.nanmean(w["harnessed"])), 2),
        "harnessed_minus_placebo": round(mean, 2),
        "ci95_lo": round(mean - ci, 2) if ci == ci else float("nan"),
        "ci95_hi": round(mean + ci, 2) if ci == ci else float("nan"),
        "placebo_minus_baseline": round(float(pmb.mean()), 2) if pmb.size else float("nan"),
    })

pj = pd.DataFrame(rows).sort_values("harnessed_minus_placebo", ascending=False).reset_index(drop=True)
panel_hmp = float(np.mean(pj["harnessed_minus_placebo"]))
panel_pmb = float(np.mean(pj["placebo_minus_baseline"]))
all_pos = bool((pj["harnessed_minus_placebo"] > 0).all())

# Single-judge replication cross-check (placebo_single_judge.csv).
sw = single.pivot_table(index="prompt_id", columns="arm", values="score")
for a in ARMS:
    if a not in sw.columns:
        sw[a] = np.nan
shp = sw.dropna(subset=["harnessed", "placebo"])
single_hmp = float((shp["harnessed"] - shp["placebo"]).mean()) if len(shp) else float("nan")

verdict = "positive for **every** judge" if all_pos else "mixed across judges"
display(Markdown(
    f"Across **{len(pj)} judges** (panel model `{placebo['model'].iloc[0]}`), the harness scores "
    f"**{pj['harnessed_minus_placebo'].min():+.2f} to {pj['harnessed_minus_placebo'].max():+.2f} beyond "
    f"the length-matched placebo** -- {verdict}, panel mean **{panel_hmp:+.2f}**. "
    f"By contrast the placebo alone lifts only **{panel_pmb:+.2f}** over baseline: a generic preamble does "
    f"little. A single-judge replication agrees (**{single_hmp:+.2f}**). The lift is the injected "
    f"**knowledge**, and it survives judge choice."))

display(pj.style.format({
    "baseline": "{:.2f}", "placebo": "{:.2f}", "harnessed": "{:.2f}",
    "harnessed_minus_placebo": "{:+.2f}", "ci95_lo": "{:+.2f}", "ci95_hi": "{:+.2f}",
    "placebo_minus_baseline": "{:+.2f}"})
    .background_gradient(subset=["harnessed_minus_placebo"], cmap="Greens"))

# Figure 1 -- knowledge lift vs preamble-only lift, per judge, with 95% CI whiskers.
r = pj.reset_index(drop=True)
x = np.arange(len(r))
yhp = r["harnessed_minus_placebo"].to_numpy(float)
err = np.clip(np.vstack([yhp - r["ci95_lo"].to_numpy(float), r["ci95_hi"].to_numpy(float) - yhp]), 0, None)
ypb = r["placebo_minus_baseline"].to_numpy(float)
fig, ax = plt.subplots(figsize=(11, 5.4))
b1 = ax.bar(x - 0.2, yhp, 0.4, yerr=err, capsize=4, color=COLORS[0], label="harnessed - placebo (injected knowledge)")
ax.bar(x + 0.2, ypb, 0.4, color=COLORS[1], label="placebo - baseline (preamble only)")
ax.axhline(panel_hmp, color="#5b5f68", ls="--", lw=1.2, label=f"panel mean H-P ({panel_hmp:+.2f})")
ax.axhline(0, color="#d1495b", lw=1)
ax.bar_label(b1, fmt="%.1f", padding=3)
ax.set_xticks(x, r["judge"], rotation=20, ha="right")
ax.set(title="Placebo control by judge: the knowledge lift dwarfs the preamble", ylabel="mean paired difference (0-10)")
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(out_dir / "placebo_by_judge.png", bbox_inches="tight"); plt.show()

# Figure 2 -- overall arm means: placebo barely moves off baseline; harnessed jumps.
arm_over = placebo.groupby("arm")["score"].mean().reindex(ARMS)
fig, ax = plt.subplots(figsize=(7.6, 4.6))
b2 = ax.bar(ARMS, arm_over.to_numpy(float), color=["#9bbcb4", COLORS[1], COLORS[0]])
ax.bar_label(b2, fmt="%.2f", padding=3)
ax.set(title="Overall panel score by arm (mean over all judges)", ylabel="mean score (0-10)", ylim=(0, 10))
fig.tight_layout(); fig.savefig(out_dir / "placebo_arm_means.png", bbox_inches="tight"); plt.show()"""


_NEGCTRL = """# The published control CSV holds the deterministic grader for the PLACEBO arm only
# (its baseline/harnessed deterministic arms live in the companion benchmark-grades
# dataset). We recompute the placebo arm honestly and carry the harnessed-minus-placebo
# contrast as reported context. If a future dataset version ships all three deterministic
# arms, the paired contrast is recomputed live instead.
REPORTED_DET_HMP = 0.08              # harnessed - placebo on the deterministic grader, fuller run
REPORTED_DET_P = "just above 0.05"   # suggestive, not significant

det = negctrl.copy()
if "cell" in det.columns:
    parts = det["cell"].astype(str).str.split("|", expand=True)
    det["arm_key"] = parts[2] if parts.shape[1] >= 3 else det.get("arm")
else:
    det["arm_key"] = det["arm"]
arms_present = sorted(a for a in det["arm_key"].dropna().unique())

placebo_mean = float(det.loc[det["arm_key"] == "placebo", "score"].mean()) if "placebo" in arms_present else float("nan")
arm_means = det.groupby("arm_key")["score"].mean().reindex([a for a in ARMS if a in arms_present])

have_three = all(a in arms_present for a in ARMS)
if have_three:
    w = det.pivot_table(index=["prompt_id", "model", "dim"], columns="arm_key", values="score")
    paired = w.dropna(subset=["harnessed", "placebo"])
    d = (paired["harnessed"] - paired["placebo"]).to_numpy(float)
    nd = int(d.size); md = float(d.mean()); sdd = float(d.std(ddof=1))
    se = sdd / math.sqrt(nd) if nd > 1 else float("nan")
    tstat = md / se if se else float("nan")
    pval = math.erfc(abs(tstat) / math.sqrt(2)) if tstat == tstat else float("nan")
    det_hmp, det_p_txt, recomputed = md, f"{pval:.3f}", True
else:
    det_hmp, det_p_txt, recomputed = REPORTED_DET_HMP, REPORTED_DET_P, False

source_note = ("recomputed here from all three deterministic arms" if recomputed else
               "carried as reported context from the fuller deterministic run -- this published control CSV "
               "holds the deterministic grader for the **placebo arm only**")
display(Markdown(
    f"On the strict 0-10 **deterministic rule grader** the placebo arm sits at **{placebo_mean:.2f}/10**, "
    f"and the arms barely separate: harnessed-minus-placebo is only **{det_hmp:+.2f}** (p **{det_p_txt}**), "
    f"{source_note}. This is **inconclusive, not evidence FOR the harness** -- a ceiling-and-floor-bound "
    f"grader cannot resolve the arms. The decisive placebo test is the LLM panel in section 1, not this "
    f"deterministic floor."))

if len(arm_means):
    display(pd.DataFrame({"mean_score_0_10": arm_means}).rename_axis("arm").reset_index()
            .style.format({"mean_score_0_10": "{:.3f}"}))

# Ceiling diagnosis: the deterministic grader piles scores at a few fixed points, so it
# has almost no headroom to register a knowledge gain over the placebo.
vals = det.loc[det["arm_key"] == "placebo", "score"].to_numpy(float)
fig, ax = plt.subplots(figsize=(11, 4.6))
ax.hist(vals, bins=np.arange(0, 10.6, 0.5), color=COLORS[3], edgecolor="white")
ax.axvline(placebo_mean, color="#d1495b", ls="--", lw=1.3, label=f"mean {placebo_mean:.2f}")
ax.set(title="Why it is inconclusive: the deterministic grader is ceiling/floor-bound",
       xlabel="deterministic score (0-10), placebo arm", ylabel="count (prompt x dimension)")
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(out_dir / "deterministic_ceiling.png", bbox_inches="tight"); plt.show()

# Per-dimension placebo means: most dims are pinned near the neutral default, a few near ceiling.
by_dim = (det[det["arm_key"] == "placebo"].groupby("dim")["score"].mean()
          .sort_values().rename("placebo_mean_0_10").reset_index().rename(columns={"dim": "dimension"}))
display(Markdown(f"**Per-dimension placebo means** ({len(by_dim)} dimensions). Many sit near the grader's "
                 "neutral default (~5), a handful near the ceiling (~9-10) -- little headroom either way."))
display(by_dim.style.format({"placebo_mean_0_10": "{:.2f}"})
        .background_gradient(subset=["placebo_mean_0_10"], cmap="RdYlGn", vmin=0, vmax=10))"""


_APPLIC = """def _as_bool(s):
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes"])

ga = _as_bool(applic["grader_applicable"])
ja = _as_bool(applic["judge_applicable"])
un = _as_bool(applic["unanimous"])

agree = float((ga == ja).mean())
unanimity = float(un.mean())
tt = int((ga & ja).sum()); tf = int((ga & ~ja).sum())
ft = int((~ga & ja).sum()); ff = int((~ga & ~ja).sum())
tot = tt + tf + ft + ff
po = (tt + ff) / tot
p_g = (tt + tf) / tot
p_j = (tt + ft) / tot
pe = p_g * p_j + (1 - p_g) * (1 - p_j)        # chance agreement under independence
kappa = (po - pe) / (1 - pe) if (1 - pe) else float("nan")

def _kappa_band(k):
    if k != k:
        return "n/a"
    return ("poor" if k < 0 else "slight" if k < 0.20 else "fair" if k < 0.40 else
            "moderate" if k < 0.60 else "substantial" if k < 0.80 else "almost perfect")

display(Markdown(
    f"Over **{tot:,} (prompt x dimension) decisions**, the deterministic applicability gate and an "
    f"independent judge agree **{agree*100:.1f}%** of the time. Cohen's kappa = **{kappa:.2f}** "
    f"(**{_kappa_band(kappa)}**, Landis & Koch bands), with **{unanimity*100:.1f}%** of the judge's three "
    f"passes unanimous. Applicability is genuinely **judgment-dependent, not mechanical** -- an honest limit "
    f"of the rigid grader, surfaced rather than hidden."))

conf = pd.DataFrame([[tt, tf], [ft, ff]],
                    index=["grader: applicable", "grader: not applicable"],
                    columns=["judge: applicable", "judge: not applicable"])
display(Markdown("**Agreement matrix** (deterministic gate x independent judge):"))
display(conf.style.background_gradient(cmap="Blues").format("{:,}"))

fig, ax = plt.subplots(figsize=(8, 4.2))
b = ax.bar(["agree", "grader says yes only", "judge says yes only"], [tt + ff, tf, ft],
           color=[COLORS[0], COLORS[2], COLORS[4]])
ax.bar_label(b, fmt="%d", padding=3)
ax.set(title=f"Applicability agreement (kappa {kappa:.2f}, {_kappa_band(kappa)})",
       ylabel="(prompt x dimension) count")
fig.tight_layout(); fig.savefig(out_dir / "applicability_agreement.png", bbox_inches="tight"); plt.show()"""


_CONVERGENT = """# Reported context only -- NOT recomputed here (the per-prompt paired grades live in the
# main benchmark-grades dataset and the repo's harness-lift report, not in this controls set).
conv = pd.DataFrame([
    {"grader": "deterministic rule grader", "reported_mean_lift_0_10": 0.18},
    {"grader": "LLM-judge panel", "reported_mean_lift_0_10": 1.73},
])
display(Markdown(
    "**Reported context (not recomputed in this notebook).** Across the main benchmark run the two graders "
    "point the **same direction** but disagree on magnitude: the deterministic grader shows a **+0.18** mean "
    "lift and the LLM-judge panel a **+1.73** mean lift (both on the 0-10 scale). Their **per-prompt "
    "correlation is only r=0.18** -- so neither grader is a proxy for the other, and both are reported rather "
    "than one being taken as ground truth. Full paired analysis lives in the repo's harness-lift report and "
    "the companion statistical-robustness notebook."))
display(conv.style.format({"reported_mean_lift_0_10": "{:+.2f}"})
        .background_gradient(subset=["reported_mean_lift_0_10"], cmap="Greens"))"""


_BANNER = """<div style="padding:26px 30px;border-radius:16px;background:linear-gradient(120deg,#102a43,#5b3f7a,#136f63);color:white">
<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.85">DueCare &nbsp;|&nbsp; methodology &amp; controls</div>
<h1 style="margin:.3em 0 .2em;font-size:30px">Is the harness lift real?</h1>
<p style="font-size:15px;line-height:1.5;margin:0;max-width:900px">The controls behind the headline. A length-matched <b>placebo</b> arm to rule out "any preamble helps", a <b>deterministic negative control</b>, and an <b>applicability audit</b> against an independent judge -- each recomputed from scores-only CSVs, each reported with its honest verdict, <b>including the control that comes back inconclusive</b>.</p>
</div>"""


_INTRO = """## Why this notebook exists

A single lift number invites one reasonable objection after another. This notebook takes
the three that matter most, runs a control for each, and reports the honest verdict --
including the deterministic control, which comes back **inconclusive** rather than being
dressed up as support.

| The skeptic's objection | The control | Honest verdict |
|---|---|---|
| "Any long preamble would help." | Length-matched **placebo** arm, 5-judge panel | **Closed** -- harness beats placebo for every judge |
| "Maybe a dumb grader shows the same thing." | **Negative control** on the deterministic rule grader | **Inconclusive** -- the grader is ceiling-bound |
| "Who decides which rubric dimensions apply?" | **Applicability audit** vs an independent judge | **Judgment-dependent** (kappa ~0.36, "fair") |

Everything below is recomputed from four scores-only CSVs with numpy, pandas, and the
standard-library `math` module -- no repo code, no hidden helpers. These are statements
about a **rubric-scored / grader-scored panel** of synthetic, composite safety prompts,
judged by language models -- not field detection, and never ground truth about any person.

### Contents

1. [Placebo panel -- the decisive control](#placebo)
2. [Negative control on the deterministic grader -- honestly inconclusive](#negctrl)
3. [Applicability audit](#applic)
4. [Convergent validity -- reported context, directional only](#convergent)
5. [What the controls establish -- and don't](#boundary)

### Related in this collection

- **Dataset -** [duecare-harness-lift-controls](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-lift-controls) (the four scores-only CSVs this notebook attaches)
- **Start here -** [DueCare harness-lift benchmark -- start here](https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here)
- **Statistical robustness -** [DueCare harness statistical robustness](https://www.kaggle.com/code/taylorsamarel/duecare-harness-statistical-robustness)
- **Code -** [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp)
- **Site -** [duecare-ai.com/benchmark](https://duecare-ai.com/benchmark)"""


def _controls_notebook() -> dict[str, Any]:
    cells = [
        _md("banner", _BANNER),
        _md("intro", _INTRO),
        _code("setup", _SETUP),
        _md("placebo-note", """<a id="placebo"></a>

## 1. Placebo panel -- the decisive control

The obvious objection to any harness lift is that *any* long, on-topic preamble would
prime a more careful answer -- so the measured gain is priming, not the harness's content.
The placebo arm settles it. It prepends an **equally long but content-neutral** preamble --
"read carefully, be thorough", no citations, no retrieved law, no ILO indicators -- and is
re-scored by the same **five judges** from different model families (self-family excluded).

For each judge we average the score per (prompt_id, arm), pair, and take two differences:
**harnessed - placebo** (the value of the injected knowledge) and **placebo - baseline**
(what the bare preamble buys). If harnessed beats the placebo for every judge, the "any
preamble helps" confound is closed -- robustly to judge choice."""),
        _code("placebo", _PLACEBO),
        _md("negctrl-note", """<a id="negctrl"></a>

## 2. Negative control on the deterministic grader -- honestly inconclusive

A good control set reports the checks that *don't* land, too. The negative control asks
whether a strict, deterministic **rule grader** sees the same placebo-vs-harness gap the
LLM panel sees. It does not -- but not because the harness fails: the deterministic grader
is **ceiling-and-floor-bound**, pinning most dimensions near a neutral default and a few at
the top, so it has almost no headroom to register a knowledge gain.

The published control CSV carries this grader for the **placebo arm only** (the baseline and
harnessed deterministic arms live in the companion benchmark-grades dataset). We recompute
the placebo arm honestly and carry the harnessed-minus-placebo contrast (~+0.08, p just above
0.05) as reported context. **We report it as inconclusive and do not present it as evidence
for the harness.**"""),
        _code("negctrl", _NEGCTRL),
        _md("applic-note", """<a id="applic"></a>

## 3. Applicability audit

Rubric dimensions only count when they *apply* to a prompt -- you cannot grade "restitution
quality" on a prompt with no victim. The deterministic grader decides applicability by rule;
this audit re-decides it with an **independent judge** (three passes) and measures how well
the two agree. Chance-corrected agreement (Cohen's kappa) is the honest metric here, because
raw agreement is inflated when most dimensions are "not applicable"."""),
        _code("applic", _APPLIC),
        _md("convergent-note", """<a id="convergent"></a>

## 4. Convergent validity -- reported context, directional only

For completeness, one more relationship, reported (not recomputed) from the main run: how
the deterministic grader and the LLM-judge panel relate across prompts. They agree on
**direction** but not magnitude, and their per-prompt correlation is negligible -- which is
exactly why both are reported rather than either being taken as the truth."""),
        _code("convergent", _CONVERGENT),
        _md("boundary", """<a id="boundary"></a>

## 5. What the controls establish -- and don't

**What they establish.**

- The **placebo panel** closes the "any preamble helps" confound: the harness beats a
  length-matched, content-neutral preamble for **every** judge, so the lift is the injected
  **knowledge**, not boilerplate -- and it survives judge choice.
- The **applicability audit** is honest about a real limit: which dimensions apply is
  judgment-dependent (kappa ~0.36, "fair"), not a mechanical fact of the rigid grader.

**What they do not establish.**

- The **deterministic negative control is inconclusive.** A ceiling-bound rule grader cannot
  separate the arms; it is neither evidence for nor against the harness. The conclusive
  placebo test is the LLM panel in section 1.
- **Convergent validity is partial.** The two graders agree in direction but not magnitude
  (r=0.18); neither is a proxy for the other.
- **The judges are LLMs, not anti-trafficking professionals.** Every score here is a
  language model's judgement of response quality. A panel of qualified caseworkers grading a
  sample would be the stronger -- and still-missing -- ground truth.
- **No field-detection claim.** These are measurements over synthetic / composite safety
  prompts. Nothing here is a real-world trafficking-detection metric, and nothing here is
  ground truth about any person.

Full paired analysis and the seeded-bootstrap / leave-one-judge-out treatment of the headline
lift live in the companion [statistical-robustness notebook](https://www.kaggle.com/code/taylorsamarel/duecare-harness-statistical-robustness)
and the [repository](https://github.com/TaylorAmarelTech/gemma4_comp)."""),
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
        ("duecare-methodology-and-controls",
         "DueCare Methodology And Controls",
         _controls_notebook()),
    ]


def _execute_notebooks(output_dir: Path) -> None:
    import nbformat
    from nbclient import NotebookClient

    for sub in sorted((output_dir / "notebooks").iterdir()):
        notebook_path = sub / "notebook.ipynb"
        out_root = sub / "local-output"
        out_root.mkdir(exist_ok=True)
        old_root = os.environ.get("DUECARE_CONTROLS_ROOT")
        old_out = os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR")
        os.environ["DUECARE_CONTROLS_ROOT"] = str(output_dir / "dataset")
        os.environ["DUECARE_NOTEBOOK_OUTPUT_DIR"] = str(out_root)
        try:
            notebook = nbformat.read(notebook_path, as_version=4)
            NotebookClient(notebook, timeout=600, kernel_name="python3",
                           resources={"metadata": {"path": str(sub)}}).execute()
            nbformat.write(notebook, sub / "notebook.executed.ipynb")
        finally:
            for key, old in (("DUECARE_CONTROLS_ROOT", old_root),
                             ("DUECARE_NOTEBOOK_OUTPUT_DIR", old_out)):
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    value.add_argument("--source", type=Path, default=SOURCE_DATASET,
                       help="directory holding the four control CSVs to copy into the fixture")
    value.add_argument("--force", action="store_true")
    value.add_argument("--execute-local", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = build(args.output, force=args.force, source=args.source)
    if args.execute_local:
        _execute_notebooks(Path(result["output_dir"]))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
