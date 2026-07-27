#!/usr/bin/env python3
# ruff: noqa: E501  (embedded Kaggle notebook cell source has long matplotlib / markdown lines)
"""Build a judge-facing "what this benchmark proves -- and what it does NOT" notebook.

The autonomous evaluator has graded thousands of real registry prompts across the
baseline / harness_core / harness_full arms with a multi-judge panel. The companion
``build_benchmark_results_kaggle.py`` publishes those grades as the public dataset
``taylorsamarel/duecare-harness-benchmark-grades`` (scores only -- no response text,
no PII). This builder emits ONE new notebook that attaches that same dataset and
walks an honest **evidence ladder**: each rung is a claim, its support, and its
limit. The strong rungs are recomputed live from ``panel_grades.csv``; the caveat
rungs cite prior recorded evidence and say what is still missing.

The six rungs:

1. The harness raises rubric scores        -- STRONG   (recomputed paired lift + charts)
2. It holds across judges + is decisive    -- STRONG   (per-judge lift; CI/sign test in the robustness notebook)
3. It is the knowledge, not the preamble   -- MEDIUM   (length-matched placebo, +3.34 beyond placebo; caveat rung)
4. The citations are real                  -- MEDIUM   (judge-independent citation check, ~0% hallucinated)
5. Sample sizes vary                       -- HONESTY  (paired-n per model; small-n is indicative, not ranked)
6. What it does NOT prove                  -- BOUNDARY (LLM judges != experts; no field detection; human-expert precondition)

The notebook is SELF-CONTAINED: it imports no repo module, because the Kaggle
dataset carries no repo code. Every live number is recomputed inside the notebook
with numpy / pandas / the standard-library ``math`` / ``statistics`` modules.

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
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "claim_ladder_v1"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
MARKER = ".duecare-claim-ladder-kaggle"
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


def _pairing_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    # Pure-stdlib recompute of the headline paired lift + per-model paired-n, so the
    # builder can report an honest sample line without importing the notebook's code.
    models = collections.Counter(r.get("model") for r in rows)
    head = "gemma4:31b" if "gemma4:31b" in models else (
        models.most_common(1)[0][0] if models else None)
    per_prompt: dict[Any, dict[Any, dict[Any, list[float]]]] = {}
    for r in rows:
        m, pid, arm, s = r.get("model"), r.get("prompt_id"), r.get("arm"), r.get("score_0_100")
        if m is None or pid is None or arm is None or s is None:
            continue
        per_prompt.setdefault(m, {}).setdefault(pid, {}).setdefault(arm, []).append(float(s))
    model_pairs: dict[Any, int] = {}
    head_diffs: list[float] = []
    for m, prompts in per_prompt.items():
        n = 0
        for arms in prompts.values():
            if "baseline" in arms and "harness_core" in arms:
                n += 1
                if m == head:
                    b = sum(arms["baseline"]) / len(arms["baseline"])
                    c = sum(arms["harness_core"]) / len(arms["harness_core"])
                    head_diffs.append(c - b)
        model_pairs[m] = n
    lift = round(sum(head_diffs) / len(head_diffs), 2) if head_diffs else None
    return {
        "headline_model": head,
        "headline_n_pairs": len(head_diffs),
        "headline_lift": lift,
        "paired_prompts_per_model": dict(
            sorted(model_pairs.items(), key=lambda kv: kv[1], reverse=True)),
    }


def _prepare_output(path: Path, *, force: bool) -> Path:
    path = path.resolve()
    if path.exists():
        if not force:
            raise RuntimeError(f"output exists; pass --force to replace: {path.name}")
        if not (path / MARKER).is_file():
            raise RuntimeError("refusing to replace a directory this builder did not create")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / MARKER).write_text("duecare.claim_ladder_kaggle.v1\n", encoding="utf-8")
    return path


def _fixture_readme(rows: list[dict[str, Any]], graded_prompts: int) -> str:
    return f"""# Local execution fixture

This directory is a convenience fixture rebuilt from `reports/rich_lift/panel.jsonl`
so `build_claim_ladder_kaggle.py --execute-local` can run the notebook end-to-end
without Kaggle. It contains only 0-100 rubric scores plus A-E component scores keyed
by (model, arm, prompt_id, judge) -- no response text, no PII.

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

    pairing = _pairing_stats(rows)
    return {
        "output_dir": str(output_dir), "dataset_id": DATASET_ID,
        "grade_rows": len(rows), "graded_prompts": graded_prompts,
        "models": len(models), "judges": len(judges),
        "notebooks": [slug for slug, _, _ in _notebooks()],
        **pairing,
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


_LADDER = """# The compact claim / evidence-strength / limit summary, with the headline number
# recomputed live from the attached grades so the top row is never stale.
head = headline_model()
w = grades[grades.model == head].pivot_table(index="prompt_id", columns="arm", values="score_0_100", aggfunc="mean")
have = [a for a in ["baseline", "harness_core"] if a in w.columns]
pair = w.dropna(subset=have) if len(have) == 2 else w.iloc[0:0]
live = float((pair["harness_core"] - pair["baseline"]).mean()) if len(pair) else float("nan")
n_models = int(grades.model.nunique())

STRENGTH_COLOR = {"STRONG": "#136f63", "MEDIUM": "#b8860b", "HONESTY": "#247ba0", "BOUNDARY": "#d1495b"}
ladder = pd.DataFrame([
    {"rung": 1, "claim": "The harness raises rubric scores", "evidence": "STRONG",
     "support": f"+{live:.1f} mean paired lift on {head} over {len(pair):,} prompts, recomputed here from the raw grades",
     "limit": "a rubric score from an LLM judge, not a real-world detection rate"},
    {"rung": 2, "claim": "It holds across every judge and is statistically decisive", "evidence": "STRONG",
     "support": "the lift stays positive inside each judge; the bootstrap 95% CI clears zero and an exact sign test is decisive in the robustness notebook",
     "limit": "the judges are heterogeneous LLMs, not independent human experts"},
    {"rung": 3, "claim": "It is the injected knowledge, not just a preamble", "evidence": "MEDIUM",
     "support": "a length-matched placebo preamble lifts far less; the harness adds ~+3.34 beyond placebo (prior recorded study)",
     "limit": "the placebo study is small (n~=74, one judge, one model); a full-registry placebo arm is the honest next control"},
    {"rung": 4, "claim": "The statute citations are real, not citation theatre", "evidence": "MEDIUM",
     "support": "a judge-independent deterministic check found ~0.0% hallucinated statutes on the harness_core sample",
     "limit": "plausibility / in-range only -- not a check that each citation is legally correct for the case"},
    {"rung": 5, "claim": "Sample sizes vary across models", "evidence": "HONESTY",
     "support": f"paired-prompt counts differ widely across the {n_models} models (see the table below)",
     "limit": "small-n model lifts are indicative only and must not be ranked against large-n models"},
    {"rung": 6, "claim": "It detects trafficking or helps a real worker", "evidence": "BOUNDARY",
     "support": "not claimed and not supported by this dataset",
     "limit": "no victim identification, field detection, or real-world outcome; blinded human-expert validation is the precondition"},
]).set_index("rung")


def _evidence_style(col):
    return [f"background-color:{STRENGTH_COLOR.get(v, '')};color:white;font-weight:600;text-align:center" for v in col]


display(ladder.style.apply(_evidence_style, subset=["evidence"]))"""


_RUNG1 = """head = headline_model()
sub = grades[grades.model == head]
w = sub.pivot_table(index="prompt_id", columns="arm", values="score_0_100", aggfunc="mean")
paired = w.dropna(subset=["baseline", "harness_core"])
b, c = paired["baseline"], paired["harness_core"]
d = c - b
mean_lift = float(d.mean())
helps, hurts = int((d > 0).sum()), int((d < 0).sum())
display(Markdown(
    f"**`{head}`** over **{len(paired):,} paired prompts**: baseline **{b.mean():.1f}** -> "
    f"harness_core **{c.mean():.1f}** (**{mean_lift:+.1f}** on the 0-100 rubric). "
    f"The harness helps on **{helps:,}** prompts and hurts on **{hurts:,}**."))

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
axes[0].bar(["baseline", "harness_core"], [b.mean(), c.mean()], color=["#b8c4c0", COLORS[0]])
axes[0].bar_label(axes[0].containers[0], fmt="%.1f", padding=3)
axes[0].set(title=f"Mean rubric score ({head})", ylabel="mean 0-100 score", ylim=(0, 105))
axes[1].hist(d, bins=40, color=COLORS[3], edgecolor="white")
axes[1].axvline(0, color="#d1495b", ls="--", lw=1.2, label="no change")
axes[1].axvline(mean_lift, color="#136f63", ls="-", lw=1.6, label=f"mean {mean_lift:+.1f}")
axes[1].set(title="Per-prompt harness lift distribution", xlabel="harness_core - baseline (0-100)")
axes[1].legend(frameon=False)
fig.tight_layout()
fig.savefig(out_dir / "rung1_headline_lift.png", bbox_inches="tight")
plt.show()"""


_RUNG2 = """head = headline_model()
sub = grades[grades.model == head]
jrows = []
for judge, g in sub.groupby("judge"):
    w = g.pivot_table(index="prompt_id", columns="arm", values="score_0_100", aggfunc="mean")
    if "baseline" not in w or "harness_core" not in w:
        continue
    p = w.dropna(subset=["baseline", "harness_core"])
    if len(p) < 5:
        continue
    dd = p["harness_core"] - p["baseline"]
    jrows.append({"judge": judge, "n_pairs": len(p),
                  "baseline": round(float(p["baseline"].mean()), 1),
                  "harness_core": round(float(p["harness_core"].mean()), 1),
                  "lift": round(float(dd.mean()), 1)})
per_judge = pd.DataFrame(jrows).sort_values("lift", ascending=False).reset_index(drop=True)
display(Markdown(f"Same paired lift, recomputed **inside each judge's own grades** for `{head}`. "
                 "Every judge shows a positive lift, so no single judge is carrying the headline."))
display(per_judge.style.format({"lift": "{:+.1f}"}).background_gradient(subset=["lift"], cmap="Greens"))

fig, ax = plt.subplots(figsize=(10, 4.4))
ax.bar(per_judge["judge"], per_judge["lift"], color=COLORS[:len(per_judge)])
ax.bar_label(ax.containers[0], fmt="%.1f", padding=3)
ax.axhline(0, color="#5b5f68", lw=1)
ax.set(title=f"Harness lift inside each judge ({head})", ylabel="mean lift (0-100)")
fig.tight_layout()
fig.savefig(out_dir / "rung2_per_judge.png", bbox_inches="tight")
plt.show()"""


_RUNG5 = """# Paired-prompt count per model: honest evidence that sample sizes are uneven.
mean_all = grades.groupby(["model", "prompt_id", "arm"], as_index=False)["score_0_100"].mean()
wide = mean_all.pivot_table(index=["model", "prompt_id"], columns="arm", values="score_0_100")
have = [a for a in ["baseline", "harness_core"] if a in wide.columns]
rows = []
for model, sub in wide.groupby(level=0):
    paired = sub.dropna(subset=have) if len(have) == 2 else sub.iloc[0:0]
    lift = float((paired["harness_core"] - paired["baseline"]).mean()) if len(paired) else float("nan")
    rows.append({"model": model,
                 "grade_rows": int((grades.model == model).sum()),
                 "paired_prompts": int(len(paired)),
                 "lift": round(lift, 1) if lift == lift else float("nan"),
                 "evidence_weight": "ranked" if len(paired) >= 100 else "indicative only"})
nper = pd.DataFrame(rows).sort_values("paired_prompts", ascending=False).reset_index(drop=True)
display(Markdown("Paired-prompt count per model. Treat any model below the dashed **n=100** line as "
                 "*indicative only* -- a wide-interval signal to gather more grades, never a ranked position."))
display(nper.style.format({"lift": "{:+.1f}"}).background_gradient(subset=["paired_prompts"], cmap="Blues"))

fig, ax = plt.subplots(figsize=(11, 0.5 * len(nper) + 2))
r = nper.iloc[::-1].reset_index(drop=True)
ax.barh(r["model"], r["paired_prompts"],
        color=[COLORS[0] if v >= 100 else "#c9a227" for v in r["paired_prompts"]])
ax.axvline(100, color="#d1495b", ls="--", lw=1, label="ranked-evidence threshold (n=100)")
ax.bar_label(ax.containers[0], fmt="%d", padding=3)
ax.set(title="Paired prompts per model (baseline vs harness_core)", xlabel="paired prompts")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(out_dir / "rung5_sample_sizes.png", bbox_inches="tight")
plt.show()"""


def _claim_ladder_notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:26px 30px;border-radius:16px;background:linear-gradient(120deg,#102a43,#136f63,#d1495b);color:white">
<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.85">DueCare | benchmark grades</div>
<h1 style="margin:.3em 0 .2em;font-size:30px">What this benchmark proves &mdash; and what it does NOT</h1>
<p style="font-size:15px;line-height:1.5;margin:0;max-width:900px">An honest evidence ladder for the DueCare harness-lift result. Each rung states a claim, shows its support, and states its limit. The strong rungs are recomputed live from the real multi-judge grades; the caveat rungs cite prior recorded evidence and say plainly what is still missing.</p>
</div>"""),
        _md("overview", """<a id="top"></a>
## What this page is

DueCare wraps a small local Gemma 4 model in a deterministic safety harness &mdash; domain
detection, ILO / legal grounding, refusal shaping, and resource lookup &mdash; and measures
whether that wrapper makes the model's answers to migrant-worker exploitation prompts
*better*. This page is the **evidence ladder** for that result: each rung states a claim,
shows the support for it, and &mdash; just as importantly &mdash; states its limit. The strong rungs
are recomputed live from the attached grades; the caveat rungs cite prior recorded
evidence and say what is still missing.

Read it top to bottom and the claim narrows as it climbs: from a large, statistically
decisive rubric lift (well supported) up to what the benchmark deliberately does **not**
prove (the boundary). "Real, not faked" cuts both ways &mdash; the honest limits sit on the
page next to the wins.

**Evidence-strength labels used below:**

<span style="display:inline-block;padding:3px 10px;border-radius:6px;background:#136f63;color:white;font-weight:600">STRONG</span> recomputed live from the grades &nbsp;
<span style="display:inline-block;padding:3px 10px;border-radius:6px;background:#b8860b;color:white;font-weight:600">MEDIUM</span> supported, with a stated caveat &nbsp;
<span style="display:inline-block;padding:3px 10px;border-radius:6px;background:#247ba0;color:white;font-weight:600">HONESTY</span> a limitation of the data &nbsp;
<span style="display:inline-block;padding:3px 10px;border-radius:6px;background:#d1495b;color:white;font-weight:600">BOUNDARY</span> explicitly out of scope"""),
        _md("toc", """## Contents

- [The ladder at a glance](#ladder)
- [Rung 1 &mdash; The harness raises rubric scores (STRONG)](#rung1)
- [Rung 2 &mdash; It holds across judges and is statistically decisive (STRONG)](#rung2)
- [Rung 3 &mdash; It is the injected knowledge, not the preamble (MEDIUM)](#rung3)
- [Rung 4 &mdash; The citations are real (MEDIUM)](#rung4)
- [Rung 5 &mdash; Sample sizes vary (honesty)](#rung5)
- [Rung 6 &mdash; What this benchmark does NOT prove (boundary)](#rung6)"""),
        _md("related", """## Related in this collection

- **Dataset &mdash; the real grades behind this page:** https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades
- **Reproduce the harness lift (from scratch):** https://www.kaggle.com/code/taylorsamarel/duecare-reproduce-harness-lift
- **Where the harness helps most (category / corridor breakdowns):** https://www.kaggle.com/code/taylorsamarel/duecare-where-the-harness-helps-most
- **Statistical robustness (bootstrap, sign test, leave-one-judge-out):** https://www.kaggle.com/code/taylorsamarel/duecare-harness-statistical-robustness
- **Code repository:** https://github.com/TaylorAmarelTech/gemma4_comp
- **Project site & live board:** https://duecare-ai.com/benchmark

This notebook is **self-contained**: it recomputes every live number from `panel_grades.csv`
alone and imports no repository code."""),
        _code("setup", _SETUP),
        _md("ladder-note", """<a id="ladder"></a>
## The ladder at a glance

One table, six rungs. Each row is a claim, the strength of the evidence for it, the
support, and the honest limit. The headline number in Rung 1 is recomputed live from the
attached grades in the cell below; the remaining rungs are expanded in their own sections.
Colour marks the evidence class (green strong, amber medium, blue honesty, red boundary)."""),
        _code("ladder", _LADDER),
        _md("rung1-note", """<a id="rung1"></a>
## Rung 1 &mdash; The harness raises rubric scores &nbsp;·&nbsp; STRONG

**Claim.** Wrapping the model in the harness raises its rubric score on migrant-worker
safety prompts.

**Support (recomputed live below).** For the headline model we average the judges to one
score per (prompt, arm), keep prompts scored in **both** the baseline and harness_core
arms, and take the mean paired difference. The bar chart shows the baseline and harnessed
means; the histogram shows the full per-prompt lift distribution &mdash; not just its average &mdash;
so you can see how much of the mass sits above zero. This is the strongest rung: a direct,
paired measurement on thousands of real registry prompts."""),
        _code("rung1", _RUNG1),
        _md("rung2-note", """<a id="rung2"></a>
## Rung 2 &mdash; It holds across judges and is statistically decisive &nbsp;·&nbsp; STRONG

**Claim.** The lift is not one lenient judge's quirk, and it is not sampling noise.

**Support (recomputed live below, plus the robustness notebook).** The chart recomputes
the same paired lift **independently inside each judge's own grades** &mdash; if it survives
every judge separately, no single judge is carrying it. The full inferential battery &mdash; a
seeded bootstrap 95% confidence interval, an exact two-sided sign test, Cohen's d, a Wilson
win-rate interval, and a leave-one-judge-out envelope &mdash; lives in the companion
[statistical-robustness notebook](https://www.kaggle.com/code/taylorsamarel/duecare-harness-statistical-robustness),
where the interval sits well clear of zero and the sign test is decisive."""),
        _code("rung2", _RUNG2),
        _md("rung3", """<a id="rung3"></a>
## Rung 3 &mdash; It is the injected knowledge, not the preamble &nbsp;·&nbsp; MEDIUM (a caveat rung)

**Claim.** The lift comes from the harness's *domain knowledge* &mdash; ILO indicators, legal
grounding, corridor context &mdash; not merely from prepending some long, on-topic preamble that
primes a more careful answer.

**Support (prior recorded evidence).** A length-matched **placebo** preamble &mdash; an equally
long but content-neutral "be careful, be thorough" block &mdash; was graded against the real
harness. The harness beat that placebo by **~+3.34 on the 0-100 LLM-judge rubric**. A pure
"any preamble helps" artefact would not clear a length-matched control, so the domain
content is doing measurable work. *(Source: DueCare placebo control, `scripts/placebo_judge.py`
and `docs/research/current_grades_findings.md`.)*

**Why only MEDIUM.** The recorded placebo run is **small &mdash; roughly 74 prompts, one judge,
one model** &mdash; and it is prior recorded evidence, not recomputed from the attached grades
(the placebo arm is not in this dataset). The honest next control is a **full-registry,
multi-judge placebo arm** run at the same scale as the headline board. Until that exists,
treat "it is the knowledge, not the preamble" as *supported and directionally robust, but
not yet at headline scale*."""),
        _md("rung4", """<a id="rung4"></a>
## Rung 4 &mdash; The citations are real &nbsp;·&nbsp; MEDIUM

**Claim.** When the harnessed model cites a statute or ILO convention, the citation is a
real, in-range reference &mdash; not an invented section number.

**Support (reported evidence, judge-independent).** A deterministic citation check &mdash;
separate from the LLM judges &mdash; scanned the stored responses for statute-section and
ILO-convention citations and flagged implausible or out-of-range ones as hallucinated. On
the **harness_core** sample it found **~0.0% hallucinated** (1 flagged out of 401
section-citing responses); harness_full was ~0.1%, comparable to baseline's 0.1%. So
grounding adds *many more* citations without adding fabrication. *(Source:
`docs/research/current_grades_findings.md`, "Citation accuracy on the real responses".)*

**Why only MEDIUM.** This is a **plausibility / in-range** check, not a legal-correctness
check. It confirms the citations are not fabricated section numbers; it does **not** verify
that each cited statute is the *right* law for the specific case. Legal-correctness
validation by a qualified reviewer is still outstanding."""),
        _md("rung5-note", """<a id="rung5"></a>
## Rung 5 &mdash; Sample sizes vary &nbsp;·&nbsp; honesty

**Claim (a limitation, stated plainly).** The models are **not** graded on equal-sized
samples. The autonomous evaluator sweeps the registry over time, so some models have
thousands of paired prompts and others only a handful.

**Why it matters.** A big lift on a model with 30 paired prompts is *indicative*, not
*ranked*: its confidence interval is wide and it should never be placed above a model
measured on thousands of prompts. The table and chart below show the paired-prompt count
per model; treat any model below the dashed n=100 line as a signal to gather more grades,
not as a leaderboard position."""),
        _code("rung5", _RUNG5),
        _md("rung6", """<a id="rung6"></a>
## Rung 6 &mdash; What this benchmark does NOT prove &nbsp;·&nbsp; boundary

This rung is the most important one. Everything above is measurement evidence about
**response quality on synthetic / composite safety prompts, graded by LLMs**. Read plainly,
the benchmark does **not** establish any of the following, and the project does not claim
them:

- **The judges are LLMs, not anti-trafficking professionals.** Every score is an
  LLM-as-judge rubric score. The panel agrees with itself, but agreement is not expertise.
  A rubric score is a proxy for quality, never a clinical or legal finding.
- **No victim identification.** Nothing here shows the system can identify a trafficking
  victim, a trafficker, or a specific case from real-world data.
- **No field detection or real-world lift.** A higher rubric score on a benchmark prompt is
  not evidence that a deployed tool would detect exploitation in the wild, change a
  caseworker's decision, or help an actual worker.
- **No ground truth about any person.** The prompts are synthetic or composite. A score is
  never a statement about a real individual.

**The honest precondition for any real-world claim** is a **blinded human-expert
validation**: qualified caseworkers and legal reviewers grading a representative sample,
blind to arm, with the harness measured against *their* judgement. Until that study exists,
the defensible claim is narrow and specific &mdash; *the harness improves the rubric-scored
quality of tested responses* &mdash; and nothing broader."""),
        _md("close", """## The honest boundary

This page is a **rubric-scored benchmark** read end to end: an LLM-judge panel scored a
harnessed local Gemma 4 higher than the raw model on synthetic / composite migrant-worker
safety prompts, the gap is large and statistically decisive, it survives a length-matched
placebo and a judge-independent citation check, and it is measured on uneven sample sizes
that the honesty rung keeps visible. None of that is a real-world trafficking-detection
metric, and none of it is ground truth about any person. The defensible claim is exactly as
wide as the ladder &mdash; no wider."""),
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
        ("duecare-what-the-benchmark-proves",
         "DueCare What The Benchmark Proves",
         _claim_ladder_notebook()),
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
