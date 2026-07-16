#!/usr/bin/env python3
# ruff: noqa: E501
"""Build six public visual notebooks for the grounded Gemma adapter study."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COLLECTION = (
    ROOT / "reports" / "kaggle_publish" / "gemma4_adapter_study_collection_v2"
)
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "gemma4_study_notebooks_v2"
LEARNING_ID = "taylorsamarel/duecare-gemma4-learning-curves"
FOUR_ARM_ID = "taylorsamarel/duecare-gemma4-four-arm-before-after"
LINEAGE_ID = "taylorsamarel/duecare-grounded-lineage-and-training-receipts"
JUDGE_ID = "taylorsamarel/duecare-frontier-judge-measurement-audit"
TOOLCHAIN_ID = "taylorsamarel/duecare-training-publication-formats-and-tools"
# Kaggle's daily public-notebook creation limit blocked the clean new system
# slug. Reuse the already-public toolchain route so the integrated showcase is
# visible now; the formats-and-tools package remains ready for a later release.
SYSTEM_ID = "taylorsamarel/duecare-training-publication-toolchain"
MARKER = ".duecare-gemma4-study-notebooks"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _markdown(identifier: str, source: str) -> dict[str, Any]:
    return {
        "cell_type": "markdown",
        "id": identifier,
        "metadata": {},
        "source": source.splitlines(True),
    }


def _code(identifier: str, source: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": identifier,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(True),
    }


def _notebook(cells: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cells": list(cells),
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _banner(title: str, subtitle: str) -> str:
    return f"""<div style="padding:30px 34px;border-radius:20px;background:linear-gradient(120deg,#102a43,#136f63,#f2b134);color:white;box-shadow:0 10px 28px rgba(16,42,67,.24)">
<div style="font-size:13px;letter-spacing:.13em;text-transform:uppercase;opacity:.86">DueCare | Gemma hackathon learning study</div>
<h1 style="margin:.35em 0 .2em;font-size:36px">{title}</h1>
<p style="font-size:17px;line-height:1.55;margin:0;max-width:950px">{subtitle}</p>
</div>"""


def _setup(dataset_id: str, release_sha: str, subdirectory: str) -> str:
    return f'''from __future__ import annotations
import hashlib, json, os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from IPython.display import HTML, Markdown, display

DATASET_ID = {dataset_id!r}
EXPECTED_RELEASE_SHA256 = {release_sha!r}

COLORS = ["#136f63", "#f2b134", "#d1495b", "#247ba0", "#6d597a", "#4f772d"]
plt.rcParams.update({{
    "figure.figsize": (11, 5.8),
    "figure.dpi": 115,
    "axes.facecolor": "#f7faf9",
    "axes.edgecolor": "#bed2cc",
    "axes.grid": True,
    "grid.alpha": 0.20,
    "font.size": 11,
}})
sns.set_palette(COLORS)

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def find_dataset():
    candidates = []
    override = os.environ.get("DUECARE_ADAPTER_STUDY_ROOT")
    if override:
        candidates.append(Path(override))
    if Path("/kaggle/input").exists():
        candidates.extend(path.parent for path in Path("/kaggle/input").rglob("release-manifest.json"))
    candidates.extend(path.parent for path in Path.cwd().rglob("release-manifest.json"))
    seen = set()
    for root in candidates:
        root = root.resolve()
        if root in seen:
            continue
        seen.add(root)
        path = root / "release-manifest.json"
        if not path.is_file():
            continue
        release = json.loads(path.read_text(encoding="utf-8"))
        if release.get("dataset_id") != DATASET_ID:
            continue
        actual = sha256_file(path)
        if actual != EXPECTED_RELEASE_SHA256:
            raise AssertionError(f"release checksum mismatch: {{actual}}")
        return root, release
    raise FileNotFoundError(f"Attach the Kaggle dataset {{DATASET_ID}}")

dataset_root, release = find_dataset()
in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
default_output = Path("/kaggle/working") if in_kaggle else Path.cwd()
output_root = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", default_output))
out_dir = output_root / {subdirectory!r}
out_dir.mkdir(parents=True, exist_ok=True)
display(Markdown("**Verified:** exact release manifest checked before loading experiment data."))
'''


def _learning_notebook(dataset_id: str, release_sha: str) -> dict[str, Any]:
    cells = [
        _markdown(
            "banner",
            _banner(
                "Gemma 4 learning curves",
                "Two real adapter runs on an 8 GB graphics card: what trained, what changed, and what the curves warn us not to claim.",
            ),
        ),
        _markdown(
            "glossary",
            """
## Start here: terms in plain language

- **Low-Rank Adaptation** trains a small set of added weights while the much
  larger base model remains frozen.
- A **graphics processing unit** is the NVIDIA accelerator used for these local
  runs.
- **Training loss** measures fit to the examples shown during training. It is
  not the same as performance on unseen examples.
- **Cross-entropy** is the token-prediction error used here as training loss.
- **Perplexity** is the exponential of cross-entropy. It can be read as an
  effective number of plausible next-token choices, but only on the training
  stream represented by that loss.
- A **gradient norm** is the size of the update signal. Large spikes can signal
  instability; a tiny norm can mean the model has nearly memorized the target.
- A **learning rate** controls the size of each parameter update.

The key study question is not “did loss go down?” It is “did the adapter change
held-out behavior, and by how much?”
""",
        ),
        _code("setup", _setup(dataset_id, release_sha, "learning-curves")),
        _code(
            "load",
            '''overview = pd.read_csv(dataset_root / "run-overview.csv")
records = []
evaluations = {}
for run_name in overview["run"]:
    root = dataset_root / "runs" / run_name
    metrics = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    logs = pd.DataFrame([row for row in metrics["training"]["log_history"] if "loss" in row])
    logs["run"] = run_name
    records.append(logs)
    evaluations[run_name] = [json.loads(line) for line in (root / "evaluation.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
logs = pd.concat(records, ignore_index=True)

display(Markdown("## Experiment identity"))
display(overview[["run", "steps", "training_loss", "train_runtime_seconds", "trainable_parameters", "heldout_rows", "objective_delta", "narrow_lift"]].style.format({
    "training_loss": "{:.4f}", "train_runtime_seconds": "{:.1f}", "objective_delta": "{:.6f}"
}).background_gradient(subset=["objective_delta"], cmap="YlGn"))
''',
        ),
        _markdown(
            "loss-intro",
            """
## 1. Training loss: fast memorization, weak transfer

The logarithmic panel makes late-stage changes visible. A low training loss is
only evidence that the adapter fit these sixteen examples. The second run's
loss approached zero, while its held-out improvement stayed small—an important
overfitting signal.
""",
        ),
        _code(
            "loss",
            '''fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
for index, (name, frame) in enumerate(logs.groupby("run")):
    color = COLORS[index]
    axes[0].plot(frame["step"], frame["loss"], marker="o", ms=3, lw=1.8, label=name, color=color)
    smooth = frame["loss"].rolling(5, min_periods=1).mean()
    axes[1].plot(frame["step"], smooth, lw=2.2, label=f"{name} · 5-step mean", color=color)
axes[0].set(title="Per-step training loss", xlabel="Training step", ylabel="Loss")
axes[1].set(title="Smoothed loss on logarithmic scale", xlabel="Training step", ylabel="Loss")
axes[1].set_yscale("log")
for axis in axes:
    axis.legend(frameon=False)
fig.suptitle("Training fit improved much more than held-out behavior", fontsize=15, fontweight="bold")
fig.tight_layout()
fig.savefig(out_dir / "training_loss_curves.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "information-intro",
            """
## 2. Information study: nats, bits, and perplexity

The optimizer reports average next-token cross-entropy in **nats**, a unit
based on the natural logarithm. Dividing by the natural logarithm of two
converts the same quantity to **bits per response token**. Exponentiating it
produces perplexity.

These views describe compression of the sixteen-example training stream. They
do not measure factual accuracy, safety, or performance on independent cases.
""",
        ),
        _code(
            "information",
            '''import numpy as np

information = logs.copy()
information["bits_per_response_token"] = information["loss"] / np.log(2)
information["training_perplexity"] = np.exp(information["loss"].clip(upper=20))

fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
for index, (name, frame) in enumerate(information.groupby("run")):
    color = COLORS[index]
    axes[0].plot(frame["step"], frame["bits_per_response_token"], lw=2, color=color, label=name)
    axes[1].plot(frame["step"], frame["training_perplexity"], lw=2, color=color, label=name)
axes[0].set(title="Training cross-entropy in bits", xlabel="Training step", ylabel="Bits per response token")
axes[1].set(title="Training-stream perplexity", xlabel="Training step", ylabel="Perplexity")
axes[1].set_yscale("log")
for axis in axes:
    axis.legend(frameon=False)
fig.suptitle("Two equivalent views of training-stream compression", fontsize=15, fontweight="bold")
fig.tight_layout()
fig.savefig(out_dir / "information_content.png", bbox_inches="tight")
plt.show()

display(
    information.groupby("run")
    .agg(
        first_bits_per_token=("bits_per_response_token", "first"),
        final_bits_per_token=("bits_per_response_token", "last"),
        first_perplexity=("training_perplexity", "first"),
        final_perplexity=("training_perplexity", "last"),
    )
    .style.format("{:.6f}")
)
''',
        ),
        _markdown(
            "optimization-intro",
            """
## 3. Optimization study: update size and learning-rate schedule

The learning rate rose during two warm-up steps and then declined linearly.
Gradient norms fell as the small format was memorized, with isolated spikes
that remain visible for audit.
""",
        ),
        _code(
            "optimization",
            '''run2 = logs[logs["run"] == overview.iloc[-1]["run"]].copy()
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].plot(run2["step"], run2["grad_norm"], color=COLORS[2], lw=1.8)
axes[0].fill_between(run2["step"], run2["grad_norm"], alpha=.15, color=COLORS[2])
axes[0].set(title="Gradient norm", xlabel="Training step", ylabel="Update-signal size")
axes[1].plot(run2["step"], run2["learning_rate"], color=COLORS[3], lw=2.2)
axes[1].set(title="Learning-rate schedule", xlabel="Training step", ylabel="Learning rate")
fig.tight_layout()
fig.savefig(out_dir / "optimization_dynamics.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "phase-intro",
            """
## 4. Optimization phase portrait

The phase portrait plots learning rate against gradient norm and colors each
point by training step. This makes warm-up, decay, and unusual update spikes
visible in one view. It is a diagnostic, not a model-quality score.
""",
        ),
        _code(
            "phase-portrait",
            '''fig, ax = plt.subplots(figsize=(10.5, 6))
points = ax.scatter(
    run2["learning_rate"],
    run2["grad_norm"],
    c=run2["step"],
    cmap="viridis",
    s=55,
    alpha=.9,
    edgecolor="white",
    linewidth=.4,
)
ax.plot(run2["learning_rate"], run2["grad_norm"], color="#61727a", alpha=.35, lw=1)
ax.set(title="Optimization phase portrait", xlabel="Learning rate", ylabel="Gradient norm")
colorbar = fig.colorbar(points, ax=ax)
colorbar.set_label("Training step")
fig.tight_layout()
fig.savefig(out_dir / "optimization_phase_portrait.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "memory-intro",
            """
## 5. What fit on the 8 GB graphics card

Gemma 4's unused vision and audio towers were moved to system memory for this
text-only run. The chart shows allocated memory at key stages and the peak
during training. The adapter updated only 817,152 parameters.
""",
        ),
        _code(
            "memory",
            '''latest_root = dataset_root / "runs" / overview.iloc[-1]["run"]
latest_metrics = json.loads((latest_root / "metrics.json").read_text(encoding="utf-8"))
memory = latest_metrics["memory"]
memory_rows = pd.DataFrame({
    "stage": ["Model load", "After modality offload", "Adapter attached", "Peak training"],
    "GiB": [
        memory["after_model_load"]["allocated_bytes"],
        memory["text_only_offload"]["allocated_bytes"],
        memory["after_adapter_attach"]["allocated_bytes"],
        memory["peak_training_allocated_bytes"],
    ],
})
memory_rows["GiB"] /= 1024 ** 3
fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
axes[0].barh(memory_rows["stage"], memory_rows["GiB"], color=COLORS[:4])
axes[0].axvline(8, color="#333", ls="--", lw=1, label="Nominal 8 GB")
axes[0].set(title="Graphics-memory allocation", xlabel="GiB")
axes[0].legend(frameon=False)
trainable = latest_metrics["training"]["trainable_parameters"]
total = latest_metrics["training"]["total_parameters"]
axes[1].bar(["Trainable adapter", "Frozen model"], [trainable, total - trainable], color=[COLORS[1], "#c9d6d2"])
axes[1].set_yscale("log")
axes[1].set(title="Parameter-efficient training", ylabel="Parameters · logarithmic scale")
for axis in axes:
    axis.tick_params(axis="x", rotation=12)
fig.tight_layout()
fig.savefig(out_dir / "memory_and_parameters.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "behavior-intro",
            """
## 6. Before and after: objective score and latency

The objective rewards requested headings and bounded review language. It does
not judge factual or legal correctness. The longer run produced a positive
aggregate change on its eight grounded-remix holdout rows; the shorter run did
not. Both estimates are small, source-dependent, and exploratory.
""",
        ),
        _code(
            "behavior",
            '''latest_name = overview.iloc[-1]["run"]
rows = evaluations[latest_name]
behavior = pd.DataFrame([
    {
        "case": row["id"][-6:],
        "family": row["source_lineage_family_id"].replace("mechanism:", ""),
        "base_score": row["base"]["score"]["objective_score"],
        "adapted_score": row["adapted"]["score"]["objective_score"],
        "base_seconds": row["base"]["seconds"],
        "adapted_seconds": row["adapted"]["seconds"],
    }
    for row in rows
])
fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
behavior.set_index("case")[["base_score", "adapted_score"]].plot(kind="bar", ax=axes[0], color=COLORS[:2])
axes[0].set(title="Held-out objective score", xlabel="Grounded-remix holdout case", ylabel="Score · 0 to 1")
behavior.set_index("case")[["base_seconds", "adapted_seconds"]].plot(kind="bar", ax=axes[1], color=COLORS[3:5])
axes[1].set(title="Generation latency", xlabel="Grounded-remix holdout case", ylabel="Seconds")
for axis in axes:
    axis.tick_params(axis="x", rotation=0)
    axis.legend(frameon=False)
fig.tight_layout()
fig.savefig(out_dir / "heldout_score_and_latency.png", bbox_inches="tight")
plt.show()
display(behavior)
''',
        ),
        _markdown(
            "gap",
            """
## 7. The most important chart: fit versus transfer

A decline in training loss and a small held-out change must be read together.
This is a successful pipeline proof with narrow, run-sensitive transfer
evidence, not a domain model release or proof of generalization.
""",
        ),
        _code(
            "gap-chart",
            '''study = overview.copy()
study["final_step_loss"] = study["run"].map(logs.groupby("run").last()["loss"])
fig, ax = plt.subplots(figsize=(10, 5.5))
for index, row in study.iterrows():
    ax.scatter(row["final_step_loss"], row["objective_delta"], s=180, color=COLORS[index], edgecolor="white", linewidth=1.5)
    ax.annotate(row["run"], (row["final_step_loss"], row["objective_delta"]), xytext=(7, 7), textcoords="offset points")
ax.set_xscale("log")
ax.set(title="Training fit does not equal held-out transfer", xlabel="Final step loss · logarithmic scale", ylabel="Held-out objective-score change")
fig.tight_layout()
fig.savefig(out_dir / "fit_vs_transfer.png", bbox_inches="tight")
plt.show()

summary = {
    "dataset_id": DATASET_ID,
    "release_manifest_sha256": EXPECTED_RELEASE_SHA256,
    "runs": overview.to_dict(orient="records"),
    "interpretation": "Training fit improved, while small grounded-remix holdouts show narrow and run-sensitive transfer.",
    "information_study": {
        "unit_of_training_loss": "nats per response token",
        "derived_units": ["bits per response token", "training-stream perplexity"],
        "boundary": "Derived only from training loss; not an independent evaluation metric.",
    },
    "chart_files": [
        "training_loss_curves.png",
        "information_content.png",
        "optimization_dynamics.png",
        "optimization_phase_portrait.png",
        "memory_and_parameters.png",
        "heldout_score_and_latency.png",
        "fit_vs_transfer.png",
    ],
    "graphics_processor_training_ran": True,
    "adapter_produced": True,
    "production_ready": False,
}
(out_dir / "learning-study-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
display(Markdown("✅ Saved seven chart files and a machine-readable study summary."))
''',
        ),
        _markdown(
            "close",
            """
## Conclusion

The study proves that a real Gemma 4 adapter can be trained and saved on this
constrained local graphics card. It also demonstrates why training curves must
be shown beside held-out behavior: optimization succeeded, but generalization
was weak. The next responsible experiment needs more parent diversity, longer
contexts, a larger locked holdout, and comparison against the deterministic
harness.
""",
        ),
    ]
    return _notebook(cells)


def _four_arm_notebook(dataset_id: str, release_sha: str) -> dict[str, Any]:
    cells = [
        _markdown(
            "banner",
            _banner(
                "Before, after, and harness ablation",
                "Four arms expose what training changed, what the deterministic harness guarantees, and where neither should be overclaimed.",
            ),
        ),
        _markdown(
            "arms",
            """
## The four arms

1. **Base model, no harness:** frozen Gemma 4 before training.
2. **Base model, with harness:** the same draft wrapped by deterministic review
   boundaries.
3. **Trained adapter, no harness:** Gemma 4 with the learned Low-Rank Adaptation
   weights.
4. **Trained adapter, with harness:** the adapted draft wrapped by the same
   deterministic boundaries.

The harness labels model text as unverified, separates unknowns, and permits
only a reversible, consent-bound next step. It does **not** validate the model's
facts. The high-severity examples later in the notebook are recorded DueCare
benchmark responses with source-artifact hashes; they are not invented here
and are excluded from training.
""",
        ),
        _code("setup", _setup(dataset_id, release_sha, "four-arm-study")),
        _code(
            "load",
            '''study_root = dataset_root / "four-arm-study"
summary = json.loads((study_root / "four-arm-summary.json").read_text(encoding="utf-8"))
rows = [json.loads(line) for line in (study_root / "four-arm-evaluation.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
failures = [json.loads(line) for line in (study_root / "recorded-egregious-examples.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
arm_labels = {
    "base_without_harness": "Base · no harness",
    "base_with_harness": "Base · harness",
    "adapter_without_harness": "Adapter · no harness",
    "adapter_with_harness": "Adapter · harness",
}
flat = []
for row in rows:
    for arm, value in row["arms"].items():
        flat.append({
            "row_id": row["id"],
            "case": row["id"][-6:],
            "family": row["source_lineage_family_id"].replace("mechanism:", ""),
            "arm": arm,
            "label": arm_labels[arm],
            "origin": value["origin"],
            "objective_score": value["score"]["objective_score"],
            "characters": value["score"]["characters"],
            "text": value["text"],
        })
frame = pd.DataFrame(flat)
display(Markdown("## Study identity"))
display(pd.DataFrame({
    "Property": ["Holdout rows", "Model", "Adapter", "Harness", "Claim boundary"],
    "Value": [len(rows), "Gemma 4 effective 2B text model", "Rank-2 Low-Rank Adaptation", "Deterministic review wrapper", summary["interpretation_boundary"]],
}))
''',
        ),
        _markdown(
            "scores-intro",
            """
## 1. Mean score by arm

The harness reaches 1.0 because the metric checks the exact boundary structure
the harness deterministically supplies. That is a control guarantee, not a
factual-quality score. The only learned-model effect is the small difference
between the two no-harness arms.
""",
        ),
        _code(
            "scores",
            '''means = frame.groupby(["arm", "label"], as_index=False)["objective_score"].mean()
order = list(arm_labels)
means["order"] = means["arm"].map({key: index for index, key in enumerate(order)})
means = means.sort_values("order")
fig, ax = plt.subplots(figsize=(11, 5.5))
bars = ax.bar(means["label"], means["objective_score"], color=COLORS[:4])
ax.bar_label(bars, fmt="%.3f", padding=4)
ax.set(title="Mean evidence-boundary objective by study arm", ylabel="Objective score · 0 to 1", ylim=(0, 1.12))
ax.tick_params(axis="x", rotation=10)
fig.tight_layout()
fig.savefig(out_dir / "four_arm_scores.png", bbox_inches="tight")
plt.show()
''',
        ),
        _code(
            "heatmap",
            '''matrix = frame.pivot_table(
    index="family", columns="label", values="objective_score", aggfunc="mean"
)
matrix = matrix[[arm_labels[key] for key in order]]
fig, ax = plt.subplots(figsize=(12, 5))
sns.heatmap(matrix, annot=True, fmt=".3f", cmap="YlGn", vmin=0, vmax=1, linewidths=.6, ax=ax)
ax.set(title="Each held-out mechanism family tells the same control story", xlabel="Study arm", ylabel="Unseen mechanism family")
fig.tight_layout()
fig.savefig(out_dir / "four_arm_case_heatmap.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "effects-intro",
            """
## 2. Effect decomposition

This separates the learned adapter effect from deterministic harness effects.
The interaction is slightly negative because the harness already saturates the
declared structural metric for both model variants. The paired table then
re-reads every contrast row by row: with eight held-out rows the smallest
achievable two-sided sign-test p-value is 0.0078, reached only when all eight
rows move in the same direction, so treat the sign tests as bounded evidence,
not proof.
""",
        ),
        _code(
            "effects",
            '''effects = pd.Series(summary["effects"]).rename_axis("effect").reset_index(name="delta")
labels = {
    "adapter_effect_without_harness": "Adapter effect · no harness",
    "harness_effect_on_base": "Harness effect · base",
    "harness_effect_on_adapter": "Harness effect · adapter",
    "adapter_harness_interaction": "Adapter x harness interaction",
}
effects["label"] = effects["effect"].map(labels)
fig, ax = plt.subplots(figsize=(11, 5.4))
colors = [COLORS[0] if value >= 0 else COLORS[2] for value in effects["delta"]]
bars = ax.barh(effects["label"], effects["delta"], color=colors)
ax.axvline(0, color="#333", lw=1)
ax.bar_label(bars, fmt="%.3f", padding=4)
ax.set(title="Learned and deterministic effects must not be conflated", xlabel="Objective-score change")
fig.tight_layout()
fig.savefig(out_dir / "four_arm_effects.png", bbox_inches="tight")
plt.show()
display(effects)

from math import comb

def exact_sign_test_two_sided_p(wins, losses):
    informative = wins + losses
    if informative == 0:
        return None
    smaller_tail = sum(comb(informative, kk) for kk in range(min(wins, losses) + 1))
    return round(min(1.0, 2.0 * smaller_tail / 2.0 ** informative), 6)

paired = frame.pivot_table(index="row_id", columns="arm", values="objective_score")
contrasts = [
    ("adapter_without_harness", "base_without_harness", "Adapter effect · no harness"),
    ("adapter_with_harness", "base_with_harness", "Adapter effect · with harness"),
    ("base_with_harness", "base_without_harness", "Harness effect · base"),
    ("adapter_with_harness", "adapter_without_harness", "Harness effect · adapter"),
]
contrast_rows = []
for treatment_arm, control_arm, contrast_label in contrasts:
    deltas = paired[treatment_arm] - paired[control_arm]
    wins = int((deltas > 0).sum())
    tie_rows = int((deltas == 0).sum())
    losses = int((deltas < 0).sum())
    contrast_rows.append({
        "contrast": contrast_label,
        "rows": int(deltas.shape[0]),
        "mean per-row delta": round(float(deltas.mean()), 6),
        "wins": wins,
        "ties": tie_rows,
        "losses": losses,
        "exact sign p (two-sided)": exact_sign_test_two_sided_p(wins, losses),
    })
paired_contrasts = pd.DataFrame(contrast_rows)
display(Markdown("### Paired per-row contrasts with exact sign tests"))
display(paired_contrasts)
''',
        ),
        _markdown(
            "examples-intro",
            """
## 3. Read the before-and-after examples

Every row declares whether it is raw model generation or deterministic harness
transformation. Expand the table cells in Kaggle to compare language directly.
""",
        ),
        _code(
            "examples",
            '''example_rows = []
for row in rows:
    example_rows.append({
        "family": row["source_lineage_family_id"].replace("mechanism:", ""),
        "prompt": row["prompt"],
        "base · no harness": row["arms"]["base_without_harness"]["text"],
        "base · harness": row["arms"]["base_with_harness"]["text"],
        "adapter · no harness": row["arms"]["adapter_without_harness"]["text"],
        "adapter · harness": row["arms"]["adapter_with_harness"]["text"],
    })
examples = pd.DataFrame(example_rows)
display(HTML(examples.to_html(index=False, escape=True).replace("<td>", '<td style="min-width:230px;vertical-align:top;white-space:pre-wrap">')))

lengths = frame.groupby("label", as_index=False)["characters"].mean()
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(lengths["label"], lengths["characters"], color=COLORS[:4])
ax.set(title="Mean response length by arm", ylabel="Characters")
ax.tick_params(axis="x", rotation=10)
fig.tight_layout()
fig.savefig(out_dir / "four_arm_text_lengths.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "negative-intro",
            """
## 4. Recorded high-severity benchmark responses

These are complete responses retrieved from existing DueCare benchmark
artifacts, paired with the recorded harnessed response when available. Source
file, prompt, model, scorer, and content hashes preserve provenance. They are
evaluation evidence only: `training_eligible=false` prevents this notebook
from silently turning test failures into training targets.
""",
        ),
        _code(
            "negative",
'''failure_frame = pd.DataFrame(failures)
display(HTML(failure_frame[["prompt_id", "subject_model", "egregiousness_score", "prompt", "egregious_response", "bounded_rewrite", "prompt_sha256"]].to_html(index=False, escape=True).replace("<td>", '<td style="min-width:220px;vertical-align:top;white-space:pre-wrap">')))
fig, ax = plt.subplots(figsize=(11, 5))
failure_frame.assign(count=1).groupby("subject_model", as_index=False)["count"].sum().plot(kind="barh", x="subject_model", y="count", legend=False, ax=ax, color=COLORS[2])
ax.set(title="Recorded high-severity examples by source model", xlabel="Recorded examples", ylabel="")
fig.tight_layout()
fig.savefig(out_dir / "recorded_failure_models.png", bbox_inches="tight")
plt.show()
''',
        ),
        _code(
            "summary",
            '''notebook_summary = {
    "dataset_id": DATASET_ID,
    "release_manifest_sha256": EXPECTED_RELEASE_SHA256,
    "rows": len(rows),
    "mean_objective_score_by_arm": summary["mean_objective_score_by_arm"],
    "effects": summary["effects"],
    "paired_contrasts": contrast_rows,
    "small_sample_note": "With eight held-out rows the smallest achievable two-sided sign-test p-value is 0.0078; these are bounded structural results, not proof of general lift.",
    "recorded_high_severity_rows": len(failures),
    "graphics_processor_training_ran": True,
    "adapter_produced": True,
    "real_world_lift_demonstrated": False,
    "production_ready": False,
}
(out_dir / "four-arm-notebook-summary.json").write_text(json.dumps(notebook_summary, indent=2), encoding="utf-8")
display(Markdown("✅ Saved five charts and the four-arm machine-readable summary."))
''',
        ),
        _markdown(
            "close",
            """
## What we learned

- Real training changed raw held-out behavior only slightly.
- The deterministic harness reliably imposed the declared review boundary.
- A harness can constrain output form without validating the model's facts.
- Training loss and the small raw-transfer estimate argue for more diverse
  parents, larger holdouts, and stronger ablations—not a production claim.
""",
        ),
    ]
    return _notebook(cells)


def _lineage_notebook(dataset_id: str, release_sha: str) -> dict[str, Any]:
    cells = [
        _markdown(
            "banner",
            _banner(
                "Grounded lineage and training receipts",
                "Trace every compact training view to an approved DueCare parent, distinguish row volume from independent source families, and verify the adapter receipts.",
            ),
        ),
        _markdown(
            "glossary",
            """
## Terms in plain language

- A **parent row** is the approved source prompt/response record from which a
  compact view descends.
- A **descendant** is a deterministic transformation of that parent. It can
  improve coverage without becoming a new independent observation.
- **SHA-256** is a cryptographic digest used here to bind a row or file to exact
  bytes.
- A **training receipt** records the source manifest, parent hashes, split,
  transformation, model, configuration, adapter hash, and measured outputs.
- **Effective sample size** asks how much independent information a weighted
  dataset contains. The conservative visual below uses parent-family count as
  the auditable unit; it does not pretend descendants are independent people.

No free-standing fictional case generator is used in these runs. Every compact
view carries source-row and parent hashes and inherits its parent's split.
""",
        ),
        _code("setup", _setup(dataset_id, release_sha, "lineage-training-receipts")),
        _code(
            "load",
            '''source_root = dataset_root / "source-curriculum"
build_summary = json.loads((source_root / "build-summary.json").read_text(encoding="utf-8"))
quality = json.loads((source_root / "quality-audit.json").read_text(encoding="utf-8"))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

run_dirs = sorted((dataset_root / "runs").glob("run-*"))
receipts = []
micro_rows = []
for run_dir in run_dirs:
    manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
    for split, filename in (("train", "micro-curriculum-train.jsonl"), ("holdout", "micro-curriculum-holdout.jsonl")):
        for row in read_jsonl(run_dir / filename):
            micro_rows.append({
                "run": run_dir.name,
                "split": split,
                "id": row["id"],
                "parent": row["source_parent_row_sha256"],
                "source_row": row["source_row_sha256"],
                "family": row["source_lineage_family_id"],
                "task": row["source_axes"]["curriculum_task"],
                "audience": row["source_axes"]["audience"],
                "format": row["source_axes"]["presentation_format"],
                "transformation": row["synthetic_kind"],
                "independent_observation": row["independent_observation"],
            })
    receipts.append({
        "run": run_dir.name,
        "model": manifest["model"],
        "steps": manifest["training_config"]["steps"],
        "train rows": manifest["training_config"]["rows"],
        "holdout rows": manifest["evaluation_config"]["rows"],
        "source manifest SHA-256": manifest["source_candidate_manifest_sha256"],
        "adapter SHA-256": manifest["artifacts"]["adapter_files"]["adapter/adapter_model.safetensors"]["sha256"],
        "free-standing fiction": manifest["data_policy"]["free_standing_fictional_generation"],
    })

micro = pd.DataFrame(micro_rows)
receipt_frame = pd.DataFrame(receipts)
display(pd.DataFrame({
    "Property": ["Supervised training rows", "Preference pairs", "Train parent families", "Validation parent families", "Test parent families", "Quality audit clean"],
    "Value": [build_summary["counts"]["supervised_train"], build_summary["counts"]["preference_train"], build_summary["parent_counts"]["train"], build_summary["parent_counts"]["validation"], build_summary["parent_counts"]["test"], quality["clean"]],
}))
display(receipt_frame)
''',
        ),
        _markdown(
            "scale-note",
            """
## 1. Row scale is not independence

The curriculum meets the requested 200,000-row scale in both supervised and
preference lanes. Its 207,680 training rows descend from 649 train parent
families: about 320 views per train parent on average. That is useful
augmentation breadth, but the parent-family count remains the conservative
unit for split isolation and uncertainty intervals.
""",
        ),
        _code(
            "scale",
            '''counts = build_summary["counts"]
parents = build_summary["parent_counts"]
scale = pd.DataFrame([
    ("Supervised training descendants", counts["supervised_train"]),
    ("Preference training descendants", counts["preference_train"]),
    ("Train parent families", parents["train"]),
    ("Validation parent families", parents["validation"]),
    ("Test parent families", parents["test"]),
], columns=["unit", "count"])
fig, axes = plt.subplots(1, 2, figsize=(15, 5.2))
axes[0].barh(scale["unit"], scale["count"], color=COLORS[:5])
axes[0].set_xscale("log")
axes[0].set(title="Descendant rows and parent families", xlabel="Count · logarithmic scale")
ratio = counts["supervised_train"] / parents["train"]
axes[1].bar(["Parent families", "Rows per parent"], [parents["train"], ratio], color=[COLORS[0], COLORS[1]])
axes[1].set(title="Auditable train-family scale", ylabel="Count")
axes[1].text(1, ratio, f"{ratio:.1f} views / parent", ha="center", va="bottom")
fig.tight_layout()
fig.savefig(out_dir / "row_scale_vs_parent_families.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "coverage-note",
            """
## 2. Coverage comes from controlled axes

The remix compiler varies declared review task, audience, and presentation
format while retaining the source row and parent hashes. Synonym or formatting
variation is acceptable only when the transformation can be reconstructed and
does not introduce facts.
""",
        ),
        _code(
            "coverage",
            '''fig, axes = plt.subplots(1, 3, figsize=(18, 6))
for axis, key, title in zip(axes, ["task", "audience", "format"], ["Review task", "Audience", "Presentation format"]):
    values = pd.Series(quality["axis_counts"][key]).sort_values()
    axis.barh([name.replace("_", " ") for name in values.index], values.values, color=COLORS[0 if key == "task" else 1 if key == "audience" else 3])
    axis.set(title=title, xlabel="Rows")
fig.tight_layout()
fig.savefig(out_dir / "curriculum_axis_coverage.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "split-note",
            """
## 3. Split by lineage before generating descendants

All descendants of one parent family stay in the same split. The source audit
reports zero train/validation/test parent overlap; the micro-run receipts repeat
the check for the exact examples actually shown to the adapter.
""",
        ),
        _code(
            "split-audit",
            '''split_sets = {
    name: set(micro.loc[micro["split"] == name, "parent"])
    for name in ["train", "holdout"]
}
overlap = pd.DataFrame(
    [[len(split_sets[a] & split_sets[b]) for b in split_sets] for a in split_sets],
    index=split_sets,
    columns=split_sets,
)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.heatmap(overlap, annot=True, fmt="d", cmap="Blues", ax=axes[0], cbar=False)
axes[0].set(title="Micro-run parent overlap matrix")
micro.groupby(["run", "split"])["parent"].nunique().unstack(fill_value=0).plot.bar(ax=axes[1], color=COLORS[:2])
axes[1].set(title="Unique parents used by each run", ylabel="Parents", xlabel="")
axes[1].tick_params(axis="x", rotation=0)
fig.tight_layout()
fig.savefig(out_dir / "lineage_split_isolation.png", bbox_inches="tight")
plt.show()
if overlap.loc["train", "holdout"] != 0:
    raise AssertionError("Training and holdout parents overlap")
''',
        ),
        _markdown(
            "receipt-note",
            """
## 4. The receipt chain

The diagram separates approved source bytes, deterministic transformation,
optimizer evidence, relative adapter weights, and evaluation. A final response
or judge preference is never allowed to erase this chain.
""",
        ),
        _code(
            "receipt-graph",
            '''from matplotlib.patches import FancyBboxPatch

stages = [
    ("Approved DueCare\\nparent", "source + parent hashes"),
    ("Deterministic\\ngrounded remix", "task + audience + format"),
    ("Lineage-inherited\\nsplit", "no family overlap"),
    ("Optimizer run", "loss + rate + gradient"),
    ("Relative adapter", "configuration + weight hash"),
    ("Separated evaluation", "four arms + frozen judge"),
]
fig, ax = plt.subplots(figsize=(17, 4.2))
for index, (title, subtitle) in enumerate(stages):
    x = index * 2.6
    box = FancyBboxPatch((x, .55), 2.15, 1.4, boxstyle="round,pad=.08,rounding_size=.12", facecolor=COLORS[index % len(COLORS)], edgecolor="none", alpha=.92)
    ax.add_patch(box)
    ax.text(x + 1.075, 1.45, title, ha="center", va="center", color="white", weight="bold")
    ax.text(x + 1.075, .85, subtitle, ha="center", va="center", color="white", fontsize=9)
    if index < len(stages) - 1:
        ax.annotate("", xy=(x + 2.55, 1.25), xytext=(x + 2.18, 1.25), arrowprops={"arrowstyle": "->", "lw": 2, "color": "#40514e"})
ax.set(xlim=(-.2, len(stages) * 2.6 - .25), ylim=(.2, 2.35), title="Manifest-bound training receipt chain")
ax.axis("off")
fig.tight_layout()
fig.savefig(out_dir / "training_receipt_chain.png", bbox_inches="tight")
plt.show()

safe_preview = micro[["run", "split", "id", "parent", "source_row", "task", "audience", "format", "transformation", "independent_observation"]].head(16)
display(HTML(safe_preview.to_html(index=False, escape=True)))
''',
        ),
        _code(
            "summary",
            '''summary = {
    "dataset_id": DATASET_ID,
    "release_manifest_sha256": EXPECTED_RELEASE_SHA256,
    "supervised_training_rows": build_summary["counts"]["supervised_train"],
    "preference_training_pairs": build_summary["counts"]["preference_train"],
    "parent_counts": build_summary["parent_counts"],
    "train_views_per_parent": build_summary["counts"]["supervised_train"] / build_summary["parent_counts"]["train"],
    "micro_run_train_holdout_parent_overlap": int(overlap.loc["train", "holdout"]),
    "free_standing_fictional_generation": False,
    "adapter_receipts": receipts,
    "charts": ["row_scale_vs_parent_families.png", "curriculum_axis_coverage.png", "lineage_split_isolation.png", "training_receipt_chain.png"],
}
(out_dir / "lineage-training-receipt-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
display(Markdown("Saved four lineage graphics and the machine-readable training receipt summary."))
''',
        ),
        _markdown(
            "close",
            """
## What this audit establishes

It establishes traceability, deterministic remix provenance, parent-family
split isolation, and exact adapter receipts. It does not establish that 649
parents represent the world, that 207,680 descendants are independent, or that
the adapter is legally or operationally validated.
""",
        ),
    ]
    return _notebook(cells)


def _judge_notebook(dataset_id: str, release_sha: str) -> dict[str, Any]:
    cells = [
        _markdown(
            "banner",
            _banner(
                "Frontier-judge measurement audit",
                "One frozen judge, one frozen context and rubric, anonymous candidates, both presentation orders, and explicit measurement limits.",
            ),
        ),
        _markdown(
            "glossary",
            """
## Terms in plain language

- A **large language model judge** is a model used as a measurement instrument
  to compare outputs. It is not human gold-standard annotation.
- **Blinding** hides arm identities such as base, adapter, or harness from the
  judge.
- **Presentation-order bias** occurs when swapping Candidate A and Candidate B
  changes the verdict for reasons unrelated to quality.
- A **bootstrap interval** resamples parent-level comparison results to show
  uncertainty in the mean. Four parents still make this interval exploratory.
- An **exact sign test** uses only the direction of each complete pair
  (treatment favored, control favored, or tie; ties are excluded). With four
  pairs the smallest achievable two-sided p-value is 0.125, so direction can
  be suggestive but never conclusive at this scale.
- A **frozen protocol** uses the same model, context, rubric, decoding settings,
  and prompt construction for every before/after comparison.

Judge outputs have `training_eligible=false`. Recycling them into the same
training pool would contaminate this evaluation.
""",
        ),
        _code("setup", _setup(dataset_id, release_sha, "frontier-judge-audit")),
        _code(
            "load",
            '''judge_root = dataset_root / "frontier-judge-study"
judge_summary = json.loads((judge_root / "frontier-judge-summary.json").read_text(encoding="utf-8"))
judge_manifest = json.loads((judge_root / "judge-manifest.json").read_text(encoding="utf-8"))
selection_path = judge_root / "judge-model-selection.json"
selection = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.is_file() else None
requests = [json.loads(line) for line in (judge_root / "judge-requests.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
checkpoint = [json.loads(line) for line in (judge_root / "judge-verdicts.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
latest = {row["request_id"]: row for row in checkpoint}
verdicts = pd.DataFrame([latest[row["request_id"]] for row in requests])

identity = pd.DataFrame({
    "Property": ["Selected judge", "Requested verdicts", "Valid verdicts", "Same judge throughout", "Both presentation orders", "Candidates blinded", "Context SHA-256", "Rubric SHA-256", "Training eligible"],
    "Value": [judge_summary["judge_model"], judge_summary["requested_verdicts"], judge_summary["valid_verdicts"], judge_summary["same_judge_before_and_after"], judge_summary["both_presentation_orders"], judge_summary["candidate_identity_blinded"], judge_summary["context_sha256"], judge_summary["rubric_sha256"], judge_summary["training_eligible"]],
})
display(identity)
if not judge_summary["complete"]:
    raise AssertionError("The packaged frontier-judge study is incomplete")
''',
        ),
        _markdown(
            "protocol-note",
            """
## 1. Frozen protocol and model fallbacks

The registry can preflight several providers, but it freezes the first
successful judge before any comparable call. A provider change in the middle
would mix measurement instruments and invalidate before/after comparisons.
The selection receipt records rejected candidates and the chosen route.
""",
        ),
        _code(
            "protocol",
            '''protocol = pd.DataFrame([
    ("Context", judge_manifest["context_sha256"][:16], True),
    ("Rubric", judge_manifest["rubric_sha256"][:16], True),
    ("Request pack", judge_manifest["request_pack_sha256"][:16], True),
    ("Judge route", judge_manifest["judge_model"], judge_summary["same_judge_before_and_after"]),
    ("Temperature", judge_manifest["decoding_contract"]["temperature"], True),
    ("Output budget", judge_manifest["decoding_contract"]["max_tokens"], True),
], columns=["Component", "Pinned value", "Verified"])
display(protocol)
if selection:
    display(pd.DataFrame(selection["attempts"]))

fig, ax = plt.subplots(figsize=(13, 3.8))
stages = ["Model registry", "Structured-output preflight", "Freeze one judge", "Blind A/B", "Run both orders", "Reject incomplete"]
for index, stage in enumerate(stages):
    ax.scatter(index, 0, s=1150, color=COLORS[index % len(COLORS)], edgecolor="white", linewidth=2)
    ax.text(index, 0, stage.replace(" ", "\\n"), ha="center", va="center", color="white", fontsize=9, weight="bold")
    if index < len(stages) - 1:
        ax.annotate("", xy=(index + .72, 0), xytext=(index + .28, 0), arrowprops={"arrowstyle": "->", "lw": 2})
ax.set(xlim=(-.7, len(stages) - .3), ylim=(-.7, .7), title="Fallback-aware selection followed by a frozen measurement protocol")
ax.axis("off")
fig.tight_layout()
fig.savefig(out_dir / "judge_protocol.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "effect-note",
            """
## 2. Treatment deltas by comparison

A positive treatment delta means the named treatment was favored after
normalizing both candidate orders. The four comparisons isolate adapter and
harness effects. Bootstrap intervals over four parent pairs are descriptive
only, so the table also reports the exact two-sided sign test; its smallest
achievable p-value at four non-tied pairs is 0.125. These are preferences
from this judge on four grounded-remix parent rows, not a real-world
model-lift estimate.
""",
        ),
        _code(
            "effects",
            '''from math import comb

def exact_sign_test_two_sided_p(wins, losses):
    informative = wins + losses
    if informative == 0:
        return None
    smaller_tail = sum(comb(informative, kk) for kk in range(min(wins, losses) + 1))
    return round(min(1.0, 2.0 * smaller_tail / 2.0 ** informative), 6)

def evidence_scale(pair_count):
    if pair_count < 10:
        return "anecdote scale (fewer than 10 pairs)"
    if pair_count < 30:
        return "pilot scale (fewer than 30 pairs)"
    return "study scale (30 or more pairs)"

comparison_labels = {
    "training_without_harness": "Adapter effect · no harness",
    "training_with_harness": "Adapter effect · with harness",
    "harness_before_training": "Harness effect · base",
    "harness_after_training": "Harness effect · adapter",
}
effect_rows = []
for key, value in judge_summary["comparisons"].items():
    interval = value["family_bootstrap_95_percent_interval"]
    effect_rows.append({
        "comparison": key,
        "label": comparison_labels[key],
        "mean": value["mean_treatment_delta"],
        "low": interval[0],
        "high": interval[1],
        "median": value["median_treatment_delta"],
        "complete pairs": value["complete_pairs"],
        "wins": value["treatment_wins"],
        "ties": value["ties"],
        "losses": value["treatment_losses"],
        "exact sign p (two-sided)": exact_sign_test_two_sided_p(value["treatment_wins"], value["treatment_losses"]),
        "evidence scale": evidence_scale(value["complete_pairs"]),
    })
effects = pd.DataFrame(effect_rows)
fig, ax = plt.subplots(figsize=(12, 5.5))
positions = range(len(effects))
ax.errorbar(effects["mean"], list(positions), xerr=[effects["mean"] - effects["low"], effects["high"] - effects["mean"]], fmt="o", ms=9, capsize=6, color=COLORS[0], ecolor=COLORS[3])
ax.axvline(0, color="#333", lw=1)
for position, row in zip(positions, effect_rows):
    p_value = row["exact sign p (two-sided)"]
    note = "all ties" if p_value is None else f"sign test p={p_value}"
    ax.annotate(note, xy=(row["mean"], position), xytext=(0, 11), textcoords="offset points", ha="center", fontsize=8, color="#333")
ax.set_yticks(list(positions), effects["label"])
ax.set(title="Frozen-judge treatment deltas with parent bootstrap intervals", xlabel="Treatment delta · positive favors treatment")
fig.tight_layout()
fig.savefig(out_dir / "judge_treatment_deltas.png", bbox_inches="tight")
plt.show()
display(effects)
''',
        ),
        _code(
            "wins-orders",
            '''outcomes = pd.DataFrame([
    {
        "label": comparison_labels[key],
        "wins": value["treatment_wins"],
        "ties": value["ties"],
        "losses": value["treatment_losses"],
        "mean order gap": value["mean_order_gap"],
        "order sign consistency": value["order_sign_consistency"],
    }
    for key, value in judge_summary["comparisons"].items()
])
fig, axes = plt.subplots(1, 2, figsize=(16, 5.5))
outcomes.set_index("label")[["wins", "ties", "losses"]].plot.barh(stacked=True, ax=axes[0], color=[COLORS[0], "#b8c4c0", COLORS[2]])
axes[0].set(title="Parent-pair outcomes", xlabel="Complete parent pairs", ylabel="")
outcomes.plot.bar(x="label", y="mean order gap", ax=axes[1], color=COLORS[1], legend=False)
axes[1].set(title="Presentation-order sensitivity", xlabel="", ylabel="Mean absolute order gap")
axes[1].tick_params(axis="x", rotation=20)
fig.tight_layout()
fig.savefig(out_dir / "judge_outcomes_and_order_bias.png", bbox_inches="tight")
plt.show()
display(outcomes)
''',
        ),
        _markdown(
            "criteria-note",
            """
## 3. Criterion-level preferences and confidence

Criterion choices are normalized to treatment/control using the recorded
candidate order. This makes style or position effects visible instead of
hiding them inside one scalar score.
""",
        ),
        _code(
            "criteria",
            '''criterion_rows = []
for row in latest.values():
    if not row["valid"]:
        continue
    for criterion, choice in (row["verdict"].get("criteria") or {}).items():
        if choice in {"tie", "indeterminate"}:
            normalized = choice
        elif (row["order"] == "control_as_a" and choice == "B") or (row["order"] == "treatment_as_a" and choice == "A"):
            normalized = "treatment"
        else:
            normalized = "control"
        criterion_rows.append({"comparison": row["comparison"], "criterion": criterion, "preference": normalized})
criteria = pd.DataFrame(criterion_rows)
criterion_counts = criteria.groupby(["criterion", "preference"]).size().unstack(fill_value=0)
for column in ["treatment", "tie", "control", "indeterminate"]:
    if column not in criterion_counts:
        criterion_counts[column] = 0
criterion_counts = criterion_counts[["treatment", "tie", "control", "indeterminate"]]
fig, axes = plt.subplots(1, 2, figsize=(17, 5.7))
criterion_counts.plot.barh(stacked=True, ax=axes[0], color=[COLORS[0], "#b8c4c0", COLORS[2], COLORS[4]])
axes[0].set(title="Criterion preferences after order normalization", xlabel="Verdicts", ylabel="")
verdicts["confidence"] = verdicts["verdict"].map(lambda value: value.get("confidence") if isinstance(value, dict) else None)
verdicts["confidence"].value_counts().reindex(["high", "medium", "low"], fill_value=0).plot.bar(ax=axes[1], color=COLORS[:3])
axes[1].set(title="Judge confidence distribution", xlabel="Confidence", ylabel="Verdicts")
axes[1].tick_params(axis="x", rotation=0)
fig.tight_layout()
fig.savefig(out_dir / "judge_criteria_and_confidence.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "criteria-pair-note",
            """
### Pair-level criterion consistency

Verdict-level counts overstate independence because both presentation orders
of one pair judge the same two responses. This view collapses each
(pair, criterion) to one outcome — treatment preferred in both orders, control
preferred in both orders, tie in both orders, or mixed/partial — and splits
harness comparisons from adapter comparisons so the two treatment kinds are
never pooled. The exact two-sided sign test uses only the both-order
outcomes; mixed and tie outcomes are excluded as direction-free.
""",
        ),
        _code(
            "criteria-pairs",
            '''pair_outcomes = {}
for row in latest.values():
    if not row["valid"]:
        continue
    group = "harness comparisons" if row["comparison"].startswith("harness") else "adapter comparisons"
    for criterion, choice in (row["verdict"].get("criteria") or {}).items():
        if choice in {"tie", "indeterminate"}:
            normalized = "tie"
        elif (row["order"] == "control_as_a" and choice == "B") or (row["order"] == "treatment_as_a" and choice == "A"):
            normalized = "treatment"
        else:
            normalized = "control"
        pair_outcomes.setdefault((group, row["pair_id"], criterion), []).append(normalized)
pair_rows = []
for (group, pair_id, criterion), choices in sorted(pair_outcomes.items()):
    if len(choices) != 2:
        continue
    if choices[0] == choices[1] and choices[0] in {"treatment", "control", "tie"}:
        outcome = choices[0] + " (both orders)"
    else:
        outcome = "mixed or partial"
    pair_rows.append({"group": group, "criterion": criterion, "outcome": outcome})
pair_level = pd.DataFrame(pair_rows)
outcome_order = ["treatment (both orders)", "tie (both orders)", "mixed or partial", "control (both orders)"]
groups = ["adapter comparisons", "harness comparisons"]
fig, axes = plt.subplots(1, 2, figsize=(17, 5.8), sharey=True)
pair_group_records = []
for ax, group in zip(axes, groups):
    table = pair_level[pair_level["group"] == group].groupby(["criterion", "outcome"]).size().unstack(fill_value=0)
    for column in outcome_order:
        if column not in table:
            table[column] = 0
    table = table[outcome_order]
    table["exact sign p (two-sided)"] = [
        exact_sign_test_two_sided_p(int(row["treatment (both orders)"]), int(row["control (both orders)"]))
        for _, row in table.iterrows()
    ]
    table[outcome_order].plot.barh(stacked=True, ax=ax, color=[COLORS[0], "#b8c4c0", COLORS[4], COLORS[2]], legend=(group == groups[-1]))
    ax.set(title=group.capitalize(), xlabel="Complete pairs", ylabel="")
    display(Markdown(f"#### {group.capitalize()}"))
    display(table)
    for criterion, row in table.iterrows():
        p_raw = row["exact sign p (two-sided)"]
        pair_group_records.append({
            "group": group,
            "criterion": criterion,
            **{column: int(row[column]) for column in outcome_order},
            "exact_sign_test_two_sided_p": None if pd.isna(p_raw) else float(p_raw),
        })
fig.suptitle("Pair-level criterion outcomes, adapter and harness treatments kept separate")
fig.tight_layout()
fig.savefig(out_dir / "judge_criterion_pair_consistency.png", bbox_inches="tight")
plt.show()
''',
        ),
        _code(
            "summary",
            '''notebook_summary = {
    "dataset_id": DATASET_ID,
    "release_manifest_sha256": EXPECTED_RELEASE_SHA256,
    "judge_model": judge_summary["judge_model"],
    "context_sha256": judge_summary["context_sha256"],
    "rubric_sha256": judge_summary["rubric_sha256"],
    "requested_verdicts": judge_summary["requested_verdicts"],
    "valid_verdicts": judge_summary["valid_verdicts"],
    "same_judge_before_and_after": judge_summary["same_judge_before_and_after"],
    "comparisons": judge_summary["comparisons"],
    "exact_sign_tests_two_sided_p": {
        key: exact_sign_test_two_sided_p(value["treatment_wins"], value["treatment_losses"])
        for key, value in judge_summary["comparisons"].items()
    },
    "criterion_pair_level": pair_group_records,
    "small_sample_note": "Bootstrap intervals over fewer than 10 pairs are descriptive only; the exact two-sided sign test is the inferential statement at this scale.",
    "training_eligible": False,
    "human_gold": False,
    "claim_boundary": judge_summary["claim_boundary"],
    "charts": ["judge_protocol.png", "judge_treatment_deltas.png", "judge_outcomes_and_order_bias.png", "judge_criteria_and_confidence.png", "judge_criterion_pair_consistency.png"],
}
(out_dir / "frontier-judge-notebook-summary.json").write_text(json.dumps(notebook_summary, indent=2), encoding="utf-8")
display(Markdown("Saved four judge-measurement graphics and a machine-readable audit summary."))
''',
        ),
        _markdown(
            "close",
            """
## Interpretation boundary

This notebook answers whether one pinned model-based evaluator preferred one
arm under one frozen rubric, and how stable that preference was to candidate
order. It does not replace blind human annotation, independent domain review,
or real-world evaluation. A second heterogeneous judge should be reported as a
separate calibrated instrument, never silently pooled.
""",
        ),
    ]
    return _notebook(cells)


def _toolchain_notebook(dataset_id: str, release_sha: str) -> dict[str, Any]:
    cells = [
        _markdown(
            "banner",
            _banner(
                "Training, evaluation, and publication toolchain",
                "A runnable map from grounded sources to typed examples, fallback-aware training, separated evaluation, adapter loading and unloading, and public release gates.",
            ),
        ),
        _markdown(
            "glossary",
            """
## Plain-language glossary

- **Supervised fine-tuning (SFT)** updates a model using input/desired-output
  examples so the desired output becomes more likely.
- **Direct Preference Optimization (DPO)** trains from a preferred and a
  rejected response without first fitting a separate reward model.
- **Low-Rank Adaptation (LoRA)** trains compact update matrices while the base
  weights stay frozen.
- **Parameter-Efficient Fine-Tuning (PEFT)** is the broader family of methods
  that update only a small part of a model; Low-Rank Adaptation is one example.
- **Retrieval-augmented generation (RAG)** retrieves current sources and gives
  them to the model at answer time rather than relying only on model memory.
- **JavaScript Object Notation Lines (JSONL)** stores one JSON object per line
  and supports streaming large datasets.
- **Parquet** is a compressed columnar format useful for analytics and selective
  loading.
- **Croissant** is a machine-readable dataset metadata format from MLCommons.
- A **jailbreak evaluation** defensively tests whether a model can be induced to
  violate its safety policy. Publishing the score and test contract does not
  require publishing operational abuse recipes.
""",
        ),
        _code("setup", _setup(dataset_id, release_sha, "training-publication-toolchain")),
        _code(
            "load",
            '''registry = json.loads((dataset_root / "model-fallback-registry.json").read_text(encoding="utf-8"))
overview = pd.read_csv(dataset_root / "run-overview.csv")
source_summary = json.loads((dataset_root / "source-curriculum" / "build-summary.json").read_text(encoding="utf-8"))
display(pd.DataFrame({
    "Property": ["Public artifact", "Supervised fine-tuning rows", "Preference pairs", "Adapter runs", "Fallback policies", "Release manifest"],
    "Value": [DATASET_ID, source_summary["counts"]["supervised_train"], source_summary["counts"]["preference_train"], len(overview), len(registry["policies"]), EXPECTED_RELEASE_SHA256],
}))
''',
        ),
        _markdown(
            "compiler-note",
            """
## 1. Typed compiler: generate evidence states before training text

The recommended compiler makes each boundary machine-checkable:

1. **WorldIR:** allowed latent facts and constraints.
2. **ObservationIR:** what the authorized documents actually expose.
3. **SelectionIR:** permitted spans, transformations, and use constraints.
4. **ExampleIR:** model input, target, preference, and lineage.
5. **DecisionIR:** evidence-bounded disposition, uncertainty, and allowed action.
6. **TrainingReceipt:** hashes, versions, split, weights, run, and evaluation.

`IR` means **intermediate representation**. An identifiability gate rejects a
target that requires hidden facts unavailable in ObservationIR. Observationally
equivalent inputs must receive equivalent evidence-bounded targets. This is
stronger than asking a fluent model to reread prose and invent an answer key.
""",
        ),
        _code(
            "compiler",
            '''from matplotlib.patches import FancyBboxPatch

stages = [
    ("WorldIR", "constrained facts"),
    ("ObservationIR", "authorized evidence"),
    ("SelectionIR", "permitted spans"),
    ("ExampleIR", "input + target"),
    ("DecisionIR", "bounded disposition"),
    ("TrainingReceipt", "hashes + versions"),
]
fig, ax = plt.subplots(figsize=(17, 4.5))
for index, (name, note) in enumerate(stages):
    x = index * 2.65
    box = FancyBboxPatch((x, .7), 2.2, 1.35, boxstyle="round,pad=.07,rounding_size=.15", facecolor=COLORS[index], edgecolor="none")
    ax.add_patch(box)
    ax.text(x + 1.1, 1.55, name, ha="center", va="center", color="white", weight="bold")
    ax.text(x + 1.1, 1.05, note, ha="center", va="center", color="white", fontsize=9)
    if index < len(stages) - 1:
        ax.annotate("", xy=(x + 2.6, 1.38), xytext=(x + 2.22, 1.38), arrowprops={"arrowstyle": "->", "lw": 2})
ax.text(7.1, .3, "identifiability + permission + privacy + lineage gates", ha="center", color="#8b2635", weight="bold")
ax.set(xlim=(-.2, 15.6), ylim=(0, 2.5), title="Typed dataset compiler and audit-certificate path")
ax.axis("off")
fig.tight_layout()
fig.savefig(out_dir / "typed_dataset_compiler.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "formats-note",
            """
## 2. Publish several useful views, not one opaque dump

Keep one canonical record and derive format-specific views. Never make a CSV
preview the source of truth if it drops nested lineage, evidence spans, or use
constraints.
""",
        ),
        _code(
            "formats",
            '''formats = pd.DataFrame([
    ("JSONL", "Canonical streaming rows", "Hugging Face Datasets, pandas chunks, jq", "Nested records remain explicit"),
    ("Parquet", "Fast analytics and selective columns", "DuckDB, Polars, pandas, PyArrow", "Derive from canonical JSONL and hash both"),
    ("CSV preview", "Kaggle landing-page preview", "Kaggle, spreadsheets", "Metadata only; truncate or omit sensitive text"),
    ("Croissant metadata", "Machine-readable discovery", "MLCommons-compatible catalogs", "Describe files, fields, license, provenance"),
    ("Safetensors adapter", "Compact learned delta", "Transformers + PEFT", "Requires exact compatible base model"),
    ("JSON run receipt", "Reproduction and claims", "Any standard JSON loader", "Bind inputs, code, model, hardware, metrics"),
], columns=["Format", "Best use", "Loaders", "Publication rule"])
display(HTML(formats.to_html(index=False, escape=True)))

fig, ax = plt.subplots(figsize=(12, 5.2))
values = [5, 5, 2, 4, 3, 5]
ax.barh(formats["Format"], values, color=COLORS)
ax.set(title="How much provenance each public view should retain", xlabel="Required provenance richness · conceptual 1 to 5", xlim=(0, 5.5))
fig.tight_layout()
fig.savefig(out_dir / "publication_formats.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "tools-note",
            """
## 3. Reuse mature tools by responsibility

The point is not to install every tool. Pick one primary and one fallback per
responsibility, pin versions, and record which implementation ran.
""",
        ),
        _code(
            "tools",
            '''tools = pd.DataFrame([
    ("Dataset loading", "Hugging Face Datasets", "Polars or DuckDB", "stream JSONL; read Parquet columns"),
    ("Large-scale preparation", "DataTrove", "Ray Data", "deduplicate, filter, shard, resume"),
    ("Weak supervision", "Snorkel", "custom abstaining label model", "retain votes and correlations"),
    ("Document parsing", "Docling", "Unstructured or GROBID", "keep original bytes and parser disagreement"),
    ("Supervised fine-tuning", "Transformers + TRL", "KerasHub", "response-only loss; grouped splits"),
    ("Adapter training", "PEFT", "Keras LoRA", "save relative weights and base-model identity"),
    ("Distributed training", "Accelerate", "PyTorch/XLA or JAX", "record topology and fallback attempt"),
    ("Fast inference", "vLLM", "Text Generation Inference or llama.cpp", "pin chat template and decoding"),
    ("Experiment tracking", "MLflow", "Weights & Biases or local receipts", "log hashes, curves, artifacts"),
    ("Safety evaluation", "Inspect AI", "garak", "defensive, versioned, non-operational test packs"),
    ("Model evaluation", "lm-evaluation-harness", "custom grouped evaluator", "separate objective, judge, and human lanes"),
    ("Publication", "KaggleHub", "Hugging Face Hub", "data card, license, Croissant, immutable version"),
], columns=["Responsibility", "Primary option", "Fallback option", "DueCare requirement"])
display(HTML(tools.to_html(index=False, escape=True).replace("<td>", '<td style="vertical-align:top;min-width:170px">')))
''',
        ),
        _markdown(
            "fallback-note",
            """
## 4. Model fallback registry without mixed measurements

Training may try full candidates in order. A judge may preflight several
providers, but once selected it is frozen for the study. A deterministic
fallback can render the notebook or validate schemas; it cannot masquerade as
model output or support an adapter-lift claim.
""",
        ),
        _code(
            "fallbacks",
            '''policy_rows = []
for policy_name, policy in registry["policies"].items():
    for order, candidate in enumerate(policy["candidates"], 1):
        policy_rows.append({
            "policy": policy_name,
            "order": order,
            "label": candidate["label"],
            "route": candidate.get("route") or candidate.get("download_handle"),
            "selection": policy["selection"],
        })
policy_frame = pd.DataFrame(policy_rows)
display(policy_frame)
policy_groups = list(policy_frame.groupby("policy", sort=False))
ncols = 2
nrows = max(1, (len(policy_groups) + ncols - 1) // ncols)
fig, axes_grid = plt.subplots(nrows, ncols, figsize=(16, 4.8 * nrows), squeeze=False)
axes = list(axes_grid.flat)
for axis, (policy, group) in zip(axes, policy_groups):
    axis.barh(group["label"], group["order"], color=COLORS[:len(group)])
    axis.invert_yaxis()
    axis.set(title=policy.replace("_", " "), xlabel="Fallback order")
for axis in axes[len(policy_groups):]:
    axis.axis("off")
fig.tight_layout()
fig.savefig(out_dir / "model_fallback_registry.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "lifecycle-note",
            """
## 5. Loading and unloading an adapter safely

Loading needs the exact base model named in the run manifest. Unloading should
delete adapter, base model, processor, optimizer, and cached tensors before the
next candidate is tried. A failed fallback attempt must not leave stale weights
or metrics in the selected receipt.

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base = AutoModelForCausalLM.from_pretrained(base_id, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(base_id)
model = PeftModel.from_pretrained(base, adapter_path)

# After use:
del model, base, tokenizer
import gc, torch
gc.collect()
if torch.cuda.is_available():
    torch.cuda.empty_cache()
```

For a Tensor Processing Unit process, end the worker process between full model
attempts so PyTorch/XLA releases its compiled graphs and device state.
""",
        ),
        _markdown(
            "release-note",
            """
## 6. Publication ladder and safety or jailbreak releases

Keep these states separate: private candidate, public-safe preview, public
dataset, trained adapter, mechanism-evaluated adapter, independently
domain-evaluated adapter, and production-approved system. A mechanism-level
evaluation can show that a training or harness intervention changed a locked
format score. It is not evidence of real-world domain improvement.
For defensive jailbreak or harmful-request datasets, publish category,
expected behavior, scoring contract, aggregate results, licenses, and benign
reproductions when possible. Quarantine operational exploitation recipes,
identifying data, private system prompts, credentials, and provider-private
reasoning.
""",
        ),
        _code(
            "release-ladder",
            '''ladder = pd.DataFrame([
    ("Private candidate", "lineage + privacy + license review", True, "historical gate passed before publication"),
    ("Public-safe preview", "small metadata/text sample", True, "included in the public package"),
    ("Public dataset", "manifest + card + schema + checksums", True, "public Kaggle dataset"),
    ("Trained adapter", "actual weights + run receipt", True, "two reloadable Low-Rank Adaptation weight sets and receipts"),
    ("Mechanism-evaluated adapter", "locked structural score + frozen judge audit", True, "narrow mechanism evidence only"),
    ("Independently domain-evaluated adapter", "sealed objective + independent human-gold lanes", False, "not yet established"),
    ("Production-approved system", "governance + monitoring + rollback", False, "not claimed"),
], columns=["State", "Required evidence", "Reached by this study", "Evidence note"])
display(ladder)
fig, ax = plt.subplots(figsize=(13, 5.5))
colors = [COLORS[0] if reached else "#d7dfdc" for reached in ladder["Reached by this study"]]
ax.barh(ladder["State"], range(1, len(ladder) + 1), color=colors)
ax.invert_yaxis()
ax.set(title="Publication state is not a synonym for deployment readiness", xlabel="Increasing evidence and authority required")
fig.tight_layout()
fig.savefig(out_dir / "publication_ladder.png", bbox_inches="tight")
plt.show()

gates = pd.DataFrame([
    ("Permission and license", "veto", "rights and redistribution declared"),
    ("Privacy and sensitive data", "veto", "no raw personal data or private logs"),
    ("Lineage and split leakage", "veto", "parents assigned before descendants"),
    ("Schema and checksums", "veto", "machine-readable and manifest-bound"),
    ("Data quality and diversity", "measure", "slice coverage and family caps"),
    ("Model behavior", "measure", "base/adapter and harness ablations"),
    ("Judge calibration", "measure", "order, confidence, and human anchors"),
    ("Claim review", "veto", "no leap from training fit to real-world lift"),
], columns=["Gate", "Role", "Evidence"])
display(gates)
''',
        ),
        _markdown(
            "references",
            """
## Primary documentation to continue with

- [Hugging Face Datasets](https://huggingface.co/docs/datasets/),
  [TRL](https://huggingface.co/docs/trl/), and
  [PEFT](https://huggingface.co/docs/peft/)
- [PyTorch/XLA](https://docs.pytorch.org/xla/) and
  [KerasHub Gemma 4](https://keras.io/keras_hub/api/models/gemma4/)
- [MLCommons Croissant](https://mlcommons.org/working-groups/data/croissant/)
- [DataTrove](https://github.com/huggingface/datatrove),
  [Docling](https://github.com/docling-project/docling), and
  [GROBID](https://github.com/kermitt2/grobid)
- [Snorkel](https://snorkel.ai/),
  [Inspect AI](https://inspect.aisi.org.uk/), and
  [garak](https://github.com/NVIDIA/garak)

Tool availability does not confer permission to ingest or publish a source.
""",
        ),
        _code(
            "summary",
            '''summary = {
    "dataset_id": DATASET_ID,
    "release_manifest_sha256": EXPECTED_RELEASE_SHA256,
    "compiler_stages": [name for name, _ in stages],
    "publication_formats": formats["Format"].tolist(),
    "tool_responsibilities": tools["Responsibility"].tolist(),
    "fallback_policies": list(registry["policies"]),
    "publication_states": ladder.to_dict(orient="records"),
    "supervised_fine_tuning_spelled_out": True,
    "free_standing_fictional_generation": False,
    "charts": ["typed_dataset_compiler.png", "publication_formats.png", "model_fallback_registry.png", "publication_ladder.png"],
}
(out_dir / "training-publication-toolchain-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
display(Markdown("Saved four toolchain graphics and a machine-readable publication summary."))
''',
        ),
    ]
    return _notebook(cells)


def _system_notebook(dataset_id: str, release_sha: str) -> dict[str, Any]:
    cells = [
        _markdown(
            "banner",
            _banner(
                "Evidence-to-triage system showcase",
                "How the grounded corpus, Gemma 4 adapter, deterministic harness, recorded safety failures, frozen judge, and publication gates work together—and exactly what improved.",
            ),
        ),
        _markdown(
            "scope",
            """
## The question this notebook answers

Can DueCare make Gemma more useful for combating labor exploitation and human
trafficking without turning indicators into accusations?

This notebook separates four different claims:

1. **Training mechanism:** did optimization run and produce loadable weights?
2. **Learned behavior:** did the adapter improve a held-out task?
3. **Harness safety:** did deterministic controls improve harmful-request
   responses?
4. **Field effectiveness:** does the complete system identify real cases or
   improve worker outcomes?

The first and third now have concrete positive evidence. The second has a
narrow formatting result plus an inconclusive frontier-judge result. The
fourth remains unproven and requires independent, expert-adjudicated real data.

### Plain-language terms

- **Supervised fine-tuning** teaches a model from input and desired-output
  examples. It is often shortened to SFT; this notebook spells it out first.
- **Low-Rank Adaptation** trains small update matrices while keeping the large
  base model frozen. It is often shortened to LoRA.
- A **harness** is deterministic software around a model that enforces rules,
  retrieves evidence, validates structure, or blocks unsafe actions.
- **Evidence-to-triage** means extracting and comparing evidence so a trained
  human can prioritize review. It is not an autonomous legal finding.
- A **large language model judge** is a model-based measurement instrument. It
  is not human gold-standard annotation.
""",
        ),
        _code("setup", _setup(dataset_id, release_sha, "evidence-to-triage-showcase")),
        _code(
            "load",
            '''import numpy as np
from matplotlib.patches import FancyBboxPatch, Patch

overview = pd.read_csv(dataset_root / "run-overview.csv")
release = json.loads((dataset_root / "release-manifest.json").read_text(encoding="utf-8"))
source = json.loads((dataset_root / "source-curriculum" / "build-summary.json").read_text(encoding="utf-8"))
four_arm = json.loads((dataset_root / "four-arm-study" / "four-arm-summary.json").read_text(encoding="utf-8"))
frontier = json.loads((dataset_root / "frontier-judge-study" / "frontier-judge-summary.json").read_text(encoding="utf-8"))
safety = json.loads((dataset_root / "recorded-harmful-request-judge-study" / "recorded-harmful-request-summary.json").read_text(encoding="utf-8"))
system_evidence = json.loads((dataset_root / "system-evidence" / "system-evidence-receipt.json").read_text(encoding="utf-8"))
recorded = [json.loads(line) for line in (dataset_root / "four-arm-study" / "recorded-egregious-examples.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

identity = pd.DataFrame({
    "Evidence": ["Dataset release", "Supervised train examples", "Preference pairs", "Unique train parents", "Adapter runs", "Recorded safety pairs", "Frozen safety verdicts", "Large paired harness prompts", "Adversarial prompt pairs"],
    "Value": [EXPECTED_RELEASE_SHA256, source["counts"]["supervised_train"], source["counts"]["preference_train"], source["parent_counts"]["train"], len(overview), safety["recorded_pairs"], safety["valid_verdicts"], system_evidence["large_pairwise_model_judge"]["n_prompts_paired"], system_evidence["adversarial_robustness"]["n_overall"]],
})
display(identity)
if not safety["complete"] or not frontier["complete"]:
    raise AssertionError("A packaged judge study is incomplete")
''',
        ),
        _markdown(
            "architecture-note",
            """
## 1. System architecture: learned skills inside deterministic boundaries

Gemma is not asked to declare that a person is trafficked. It proposes
evidence-bounded observations and review steps. The harness independently
checks provenance, privacy, authority, uncertainty, and action boundaries.
Mutable law and resource information stays in retrieval rather than weights.
""",
        ),
        _code(
            "architecture",
            '''stages = [
    ("Approved sources", "hash + permission"),
    ("Grounded compiler", "parent-bound remixes"),
    ("Gemma 4 + adapter", "extract + compare"),
    ("DueCare harness", "verify + bound"),
    ("Human triage", "review + consent"),
    ("Safe support", "proportionate action"),
]
fig, ax = plt.subplots(figsize=(17, 5.0))
for i, (name, note) in enumerate(stages):
    x = i * 2.65
    box = FancyBboxPatch((x, 1.0), 2.15, 1.45, boxstyle="round,pad=.08,rounding_size=.16", facecolor=COLORS[i], edgecolor="white", linewidth=2)
    ax.add_patch(box)
    ax.text(x + 1.075, 1.88, name, ha="center", va="center", color="white", weight="bold", fontsize=10)
    ax.text(x + 1.075, 1.42, note, ha="center", va="center", color="white", fontsize=8.8)
    if i < len(stages) - 1:
        ax.annotate("", xy=(x + 2.62, 1.72), xytext=(x + 2.18, 1.72), arrowprops={"arrowstyle": "->", "lw": 2.2, "color": "#345"})
ax.text(7.2, .45, "observation ≠ inference ≠ legal finding ≠ operational action", ha="center", fontsize=13, weight="bold", color="#8b2635")
ax.set(xlim=(-.25, 15.7), ylim=(0, 3.0), title="DueCare evidence-to-triage learning and runtime path")
ax.axis("off")
fig.tight_layout()
fig.savefig(out_dir / "system_architecture.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "system-evidence-note",
            """
## 2. The broader harness result: paired response quality, not case detection

Before adapter training, DueCare evaluated the same Gemma 4 model with and
without the harness on 911 paired synthetic/composite trafficking-safety
prompts. A model judge scored the harnessed arm 1.73 points higher on a 0-to-10
scale, with 668 wins, 210 losses, and 33 ties. A deterministic grader found a
smaller positive 0.18-point change over 998 paired prompts. The instruments
agree on direction and disagree on magnitude, so both are shown.

On 140 declared adversarial transformations, the model-judged mean harness
change was +4.39 points and every transformation family was positive. These
are response-quality and robustness results on benchmark prompts. They do not
measure victim-identification sensitivity, specificity, prevalence, or field
outcomes.
""",
        ),
        _code(
            "system-evidence",
            '''judge = system_evidence["large_pairwise_model_judge"]
deterministic = system_evidence["large_pairwise_deterministic_grader"]
large_results = pd.DataFrame([
    ("Model judge", judge["baseline_mean"], judge["harnessed_mean"], judge["lift"], judge["n_prompts_paired"]),
    ("Deterministic grader", deterministic["baseline_mean"], deterministic["harnessed_mean"], deterministic["lift"], deterministic["n_prompts_paired"]),
], columns=["Instrument", "Gemma alone", "Gemma + DueCare", "Paired change", "Paired prompts"])
fig, axes = plt.subplots(1, 2, figsize=(17, 5.7))
large_results.set_index("Instrument")[["Gemma alone", "Gemma + DueCare"]].plot.bar(ax=axes[0], color=[COLORS[3], COLORS[0]])
axes[0].set(title="Paired trafficking-safety response quality", ylabel="Mean score · 0 to 10", xlabel="Measurement instrument", ylim=(0, 10))
axes[0].tick_params(axis="x", rotation=0)
axes[1].barh(large_results["Instrument"], large_results["Paired change"], color=[COLORS[0], COLORS[1]])
axes[1].axvline(0, color="#333", lw=1)
axes[1].set(title="Same direction, different magnitude", xlabel="Harnessed minus baseline")
fig.tight_layout()
fig.savefig(out_dir / "broader_harness_evidence.png", bbox_inches="tight")
plt.show()
display(large_results)

attacks = pd.DataFrame(system_evidence["adversarial_robustness"]["rows"]).sort_values("lift")
fig, ax = plt.subplots(figsize=(13, 7.2))
ax.barh(attacks["transform"].str.replace("_", " "), attacks["lift"], color=[COLORS[4] if layer == "model" else COLORS[0] for layer in attacks["layer"]])
ax.axvline(0, color="#333", lw=1)
ax.set(title="Harness response-quality change under declared prompt transformations", xlabel="Paired model-judge change · 0 to 10 scale", ylabel="Attack transformation")
ax.legend(handles=[Patch(color=COLORS[0], label="Input obfuscation / keyword stress"), Patch(color=COLORS[4], label="Model instruction / framing stress")], frameon=False, loc="lower right")
fig.tight_layout()
fig.savefig(out_dir / "adversarial_robustness.png", bbox_inches="tight")
plt.show()
display(attacks[["transform", "layer", "n", "lift"]].sort_values("lift", ascending=False))
''',
        ),
        _markdown(
            "corpus-note",
            """
## 3. Corpus scale without pretending remixes are independent cases

The training lanes each exceed 200,000 rows, but they descend from hundreds of
approved parent families. Split assignment happens at the parent-family level
before augmentation. This prevents a synonym or format variant of a training
example from leaking into validation or test.
""",
        ),
        _code(
            "corpus",
            '''corpus = pd.DataFrame([
    ("Supervised fine-tuning train", source["counts"]["supervised_train"]),
    ("Preference train", source["counts"]["preference_train"]),
    ("Validation", source["counts"]["supervised_validation"]),
    ("Test", source["counts"]["supervised_test"]),
    ("Train parent families", source["parent_counts"]["train"]),
    ("Validation parent families", source["parent_counts"]["validation"]),
    ("Test parent families", source["parent_counts"]["test"]),
], columns=["Lane", "Rows or parents"])
fig, axes = plt.subplots(1, 2, figsize=(16, 5.5))
axes[0].barh(corpus["Lane"].iloc[:4], corpus["Rows or parents"].iloc[:4], color=COLORS[:4])
axes[0].set(title="Published curriculum lanes", xlabel="Rows")
axes[1].barh(corpus["Lane"].iloc[4:], corpus["Rows or parents"].iloc[4:], color=COLORS[3:6])
axes[1].set(title="Independent lineage units", xlabel="Parent families")
for axis in axes:
    axis.ticklabel_format(axis="x", style="plain")
fig.suptitle("Row scale and lineage scale are different quantities", fontsize=15, weight="bold")
fig.tight_layout()
fig.savefig(out_dir / "corpus_rows_and_parents.png", bbox_inches="tight")
plt.show()
display(corpus)
''',
        ),
        _markdown(
            "training-note",
            """
## 4. Actual training: optimization, transfer, and overfitting

The longer run updated 817,152 adapter parameters for 60 steps on a local
graphics processing unit. Its narrow held-out structural score improved by
0.15. Training loss alone is not the result: the gap between training fit and
held-out behavior is the important diagnostic.
""",
        ),
        _code(
            "training",
            '''metrics = json.loads((dataset_root / "runs" / "run-02" / "metrics.json").read_text(encoding="utf-8"))
history = pd.DataFrame([row for row in metrics["training"]["log_history"] if "loss" in row])
fig, axes = plt.subplots(1, 2, figsize=(16, 5.3))
axes[0].plot(history["step"], history["loss"], color=COLORS[0], marker="o", ms=3, lw=1.7)
axes[0].plot(history["step"], history["loss"].rolling(5, min_periods=1).mean(), color=COLORS[1], lw=2.5, label="5-step mean")
axes[0].set(title="Real adapter training loss", xlabel="Optimizer step", ylabel="Cross-entropy loss")
axes[0].legend(frameon=False)
transfer = overview.set_index("run")[["base_objective_score", "adapted_objective_score"]]
transfer.plot.bar(ax=axes[1], color=[COLORS[3], COLORS[0]])
axes[1].set(title="Locked grounded-remix holdout", xlabel="Run", ylabel="Structural objective", ylim=(0, 1))
axes[1].tick_params(axis="x", rotation=0)
fig.tight_layout()
fig.savefig(out_dir / "training_and_transfer.png", bbox_inches="tight")
plt.show()
display(overview[["run", "steps", "training_loss", "trainable_parameters", "heldout_rows", "objective_delta", "narrow_lift"]])
''',
        ),
        _markdown(
            "arms-note",
            """
## 5. Four arms reveal a metric conflict

The deterministic structural metric rewards the harness because it guarantees
required fields and safety terms. The frozen judge penalized the first generic
wrapper because it truncated useful content. Both results are retained. This
is exactly why DueCare needs component metrics, blinded review, and ablations
instead of one impressive-looking score.
""",
        ),
        _code(
            "arms",
            '''arms = pd.Series(four_arm["mean_objective_score_by_arm"]).rename_axis("Arm").reset_index(name="Structural score")
judge_effects = pd.DataFrame([
    (name, values["mean_treatment_delta"], values["family_bootstrap_95_percent_interval"][0], values["family_bootstrap_95_percent_interval"][1])
    for name, values in frontier["comparisons"].items()
], columns=["Comparison", "Mean delta", "Low", "High"])
fig, axes = plt.subplots(1, 2, figsize=(17, 5.7))
axes[0].barh(arms["Arm"].str.replace("_", " "), arms["Structural score"], color=COLORS[:4])
axes[0].set(title="Deterministic structural metric", xlim=(0, 1.05), xlabel="Objective score")
y = np.arange(len(judge_effects))
axes[1].errorbar(judge_effects["Mean delta"], y, xerr=[judge_effects["Mean delta"] - judge_effects["Low"], judge_effects["High"] - judge_effects["Mean delta"]], fmt="o", capsize=6, color=COLORS[2])
axes[1].axvline(0, color="#333", lw=1)
axes[1].set_yticks(y, judge_effects["Comparison"].str.replace("_", " "))
axes[1].set(title="Frozen-judge deltas on the micro holdout", xlabel="Positive favors treatment")
fig.tight_layout()
fig.savefig(out_dir / "four_arm_metric_conflict.png", bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "safety-note",
            """
## 6. Direct trafficking-relevant result: harmful-request handling

The recorded safety lane contains real benchmark prompts where Gemma produced
high-severity operational guidance that could facilitate exploitation. DueCare
had already produced a bounded response for each prompt. A newly frozen study
compared those two real responses anonymously in both A/B orders.

The harness response won all six pairs. Mean delta was +9.67 on a -10 to +10
scale; the pair-bootstrap 95% interval was +9.0 to +10.0; the mean order gap
was zero. Six wins in six non-tied pairs give an exact two-sided sign-test
p-value of 0.03125, the strongest statement this small recorded lane can
support. This demonstrates better harmful-request handling on these six
recorded benchmark prompts. It does not demonstrate better victim detection.
""",
        ),
        _code(
            "safety",
            '''from math import comb

def exact_sign_test_two_sided_p(wins, losses):
    informative = wins + losses
    if informative == 0:
        return None
    smaller_tail = sum(comb(informative, kk) for kk in range(min(wins, losses) + 1))
    return round(min(1.0, 2.0 * smaller_tail / 2.0 ** informative), 6)

sign_p = exact_sign_test_two_sided_p(safety["harness_wins"], safety["harness_losses"])
safety_table = pd.DataFrame({
    "Measure": ["Recorded pairs", "Valid blinded verdicts", "Harness wins", "Harness ties", "Harness losses", "Mean harness delta", "95% interval low", "95% interval high", "Mean order gap", "Exact sign test p (two-sided)"],
    "Value": [safety["recorded_pairs"], safety["valid_verdicts"], safety["harness_wins"], safety["ties"], safety["harness_losses"], safety["mean_harness_delta"], safety["pair_bootstrap_95_percent_interval"][0], safety["pair_bootstrap_95_percent_interval"][1], safety["mean_order_gap"], sign_p],
})
fig, axes = plt.subplots(1, 2, figsize=(15, 5.2))
axes[0].bar(["Harness wins", "Ties", "Harness losses"], [safety["harness_wins"], safety["ties"], safety["harness_losses"]], color=[COLORS[0], "#b8c4c0", COLORS[2]])
axes[0].set(title="Recorded harmful-request outcomes", ylabel="Prompt pairs", ylim=(0, safety["recorded_pairs"] + 1))
axes[0].annotate(f"exact sign test p={sign_p}", xy=(0, safety["harness_wins"]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9, color="#333")
mean = safety["mean_harness_delta"]
low, high = safety["pair_bootstrap_95_percent_interval"]
axes[1].errorbar([mean], [0], xerr=[[mean-low], [high-mean]], fmt="o", ms=13, capsize=8, color=COLORS[0])
axes[1].axvline(0, color="#333", lw=1)
axes[1].set(xlim=(-10.5, 10.5), ylim=(-1, 1), yticks=[], title="Frozen-judge harness delta", xlabel="-10 favors recorded failure · +10 favors harness")
fig.tight_layout()
fig.savefig(out_dir / "recorded_harmful_request_result.png", bbox_inches="tight")
plt.show()
display(safety_table)
''',
        ),
        _markdown(
            "examples-note",
            """
## 7. Recorded examples: failure signal and bounded response

The table below uses recorded artifacts only—no invented case narrative. The
unsafe column is restricted to the scorer's short worst quote rather than
republishing the full operational recipe. The bounded excerpt shows how the
harness refuses facilitation and redirects toward protective analysis.
""",
        ),
        _code(
            "examples",
            '''example_rows = []
for row in recorded:
    example_rows.append({
        "Fixture": row["fixture_id"],
        "Failure type": row["failure_type"],
        "Severity": row["egregiousness_score"],
        "Recorded unsafe quote": row.get("worst_quote") or "[not supplied]",
        "DueCare bounded response (full)": " ".join(row["bounded_rewrite"].split()),
        "Training eligible": row["training_eligible"],
    })
examples = pd.DataFrame(example_rows)
display(HTML(examples.to_html(index=False, escape=True).replace("<td>", '<td style="min-width:230px;vertical-align:top;white-space:pre-wrap">')))
''',
        ),
        _markdown(
            "ladder-note",
            """
## 8. Claim ladder: where the system is strong and what comes next

“Combat trafficking” is a product mission, not one metric. Promotion requires
evidence at every level below; a success in refusal behavior cannot silently
become a victim-identification claim.
""",
        ),
        _code(
            "ladder",
            '''ladder = pd.DataFrame([
    ("Paired trafficking-safety response quality", True, "+1.73 model judge; +0.18 deterministic"),
    ("Adversarial response robustness", True, "+4.39 across 140 transformed prompts"),
    ("Reproducible training mechanism", True, "Two adapters + exact receipts"),
    ("Narrow held-out format transfer", True, "+0.15 on 8 grounded-remix rows"),
    ("Recorded harmful-request safety", True, "6/6 wins; mean +9.67; sign p=0.031"),
    ("Independent evidence extraction", False, "Needs expert span gold"),
    ("Independent triage improvement", False, "Needs real temporal holdout"),
    ("Worker-outcome improvement", False, "Needs governed field study"),
    ("Production approval", False, "Needs ethics, privacy, legal, red-team gates"),
], columns=["Capability level", "Demonstrated", "Evidence or next gate"])
fig, ax = plt.subplots(figsize=(13, 6))
colors = [COLORS[0] if value else "#cbd5d1" for value in ladder["Demonstrated"]]
ax.barh(ladder["Capability level"], [1] * len(ladder), color=colors)
for i, row in ladder.iterrows():
    ax.text(.03, i, row["Evidence or next gate"], va="center", color="white" if row["Demonstrated"] else "#334", weight="bold", fontsize=9)
ax.set(xlim=(0, 1), xticks=[], title="DueCare evidence ladder · green is demonstrated in released artifacts")
ax.invert_yaxis()
fig.tight_layout()
fig.savefig(out_dir / "capability_claim_ladder.png", bbox_inches="tight")
plt.show()
display(ladder)
''',
        ),
        _code(
            "summary",
            '''summary = {
    "dataset_id": DATASET_ID,
    "release_manifest_sha256": EXPECTED_RELEASE_SHA256,
    "curriculum_counts": source["counts"],
    "parent_counts": source["parent_counts"],
    "adapter_runs": len(overview),
    "broader_harness_evidence": system_evidence,
    "recorded_harmful_request_result": safety,
    "recorded_harmful_request_exact_sign_p": sign_p,
    "demonstrated": ["paired trafficking-safety response-quality improvement on synthetic/composite benchmarks", "adversarial response robustness on declared transformations", "reproducible adapter training", "narrow format transfer", "recorded harmful-request handling improvement"],
    "not_demonstrated": ["victim identification improvement", "real-world detection improvement", "legal findings", "worker-outcome improvement", "production readiness"],
    "free_standing_fictional_generation": False,
    "charts": ["system_architecture.png", "broader_harness_evidence.png", "adversarial_robustness.png", "corpus_rows_and_parents.png", "training_and_transfer.png", "four_arm_metric_conflict.png", "recorded_harmful_request_result.png", "capability_claim_ladder.png"],
}
(out_dir / "evidence-to-triage-showcase-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
display(Markdown("Saved eight system-level graphics and the machine-readable claim ledger."))
''',
        ),
        _markdown(
            "close",
            """
## Next promotion experiment

Train Gemma to select exact evidence spans, label each as observed, reported,
contradictory, or unknown, and return a proportional human-review disposition.
Evaluate on lineage-separated, expert-adjudicated, temporally held-out real
documents. Keep the harmful-request suite, privacy tests, harness-on/off
ablation, and frozen-judge audit as separate blocks. That is the shortest
credible path from this strong safety result to a defensible claim about
improved trafficking-related evidence triage.
""",
        ),
    ]
    return _notebook(cells)


def _kernel_metadata(
    identifier: str, dataset_id: str, *, title: str | None = None
) -> dict[str, Any]:
    return {
        "id": identifier,
        "title": title or identifier.split("/", 1)[1].replace("-", " ").title(),
        "code_file": "notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": False,
        "dataset_sources": [dataset_id],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }


def _prepare_output(path: Path, *, force: bool) -> Path:
    path = path.resolve()
    if path.exists():
        if not force:
            raise FileExistsError(f"output exists; use --force: {path}")
        if not (path / MARKER).is_file():
            raise ValueError(f"refusing to replace unowned output: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / MARKER).write_text("duecare.gemma4.study_notebooks.v3\n", encoding="utf-8")
    return path


def _execute_notebook(notebook_path: Path, dataset_root: Path) -> list[str]:
    import nbformat
    from nbclient import NotebookClient

    output_root = notebook_path.parent / "local-output"
    output_root.mkdir()
    old_dataset = os.environ.get("DUECARE_ADAPTER_STUDY_ROOT")
    old_output = os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR")
    os.environ["DUECARE_ADAPTER_STUDY_ROOT"] = str(dataset_root)
    os.environ["DUECARE_NOTEBOOK_OUTPUT_DIR"] = str(output_root)
    try:
        notebook = nbformat.read(notebook_path, as_version=4)
        client = NotebookClient(
            notebook,
            timeout=300,
            kernel_name="python3",
            resources={"metadata": {"path": str(notebook_path.parent)}},
        )
        client.execute()
        nbformat.write(notebook, notebook_path.parent / "notebook.executed.ipynb")
    finally:
        if old_dataset is None:
            os.environ.pop("DUECARE_ADAPTER_STUDY_ROOT", None)
        else:
            os.environ["DUECARE_ADAPTER_STUDY_ROOT"] = old_dataset
        if old_output is None:
            os.environ.pop("DUECARE_NOTEBOOK_OUTPUT_DIR", None)
        else:
            os.environ["DUECARE_NOTEBOOK_OUTPUT_DIR"] = old_output
    return [
        path.relative_to(notebook_path.parent).as_posix()
        for path in sorted(output_root.rglob("*"))
        if path.is_file()
    ]


def _validate_code_cells(notebook: dict[str, Any], identifier: str) -> None:
    for index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        compile(str(cell.get("source", "")), f"{identifier}:cell-{index}", "exec")


def build_notebooks(
    collection: Path, output: Path, *, force: bool, execute_local: bool
) -> dict[str, Any]:
    dataset_root = collection.resolve(strict=True) / "dataset"
    release_path = dataset_root / "release-manifest.json"
    release = _read_json(release_path)
    dataset_id = str(release["dataset_id"])
    import hashlib

    release_sha = hashlib.sha256(release_path.read_bytes()).hexdigest()
    output = _prepare_output(output, force=force)
    definitions = (
        ("learning_curves", LEARNING_ID, _learning_notebook(dataset_id, release_sha)),
        ("four_arm_before_after", FOUR_ARM_ID, _four_arm_notebook(dataset_id, release_sha)),
        ("lineage_training_receipts", LINEAGE_ID, _lineage_notebook(dataset_id, release_sha)),
        ("frontier_judge_audit", JUDGE_ID, _judge_notebook(dataset_id, release_sha)),
        ("training_publication_toolchain", TOOLCHAIN_ID, _toolchain_notebook(dataset_id, release_sha)),
        ("evidence_to_triage_system_showcase", SYSTEM_ID, _system_notebook(dataset_id, release_sha)),
    )
    records = []
    for folder, identifier, notebook in definitions:
        _validate_code_cells(notebook, identifier)
        root = output / folder
        root.mkdir()
        notebook_path = root / "notebook.ipynb"
        _write_json(notebook_path, notebook)
        title = (
            "DueCare Evidence-to-Triage System and Training Showcase"
            if folder == "evidence_to_triage_system_showcase"
            else None
        )
        _write_json(
            root / "kernel-metadata.json",
            _kernel_metadata(identifier, dataset_id, title=title),
        )
        local_outputs = (
            _execute_notebook(notebook_path, dataset_root) if execute_local else []
        )
        records.append(
            {
                "id": identifier,
                "path": folder,
                "is_private": False,
                "accelerator": "central processing unit",
                "release_manifest_sha256": release_sha,
                "locally_executed": execute_local,
                "code_cells_compiled": True,
                "local_outputs": local_outputs,
            }
        )
    manifest = {
        "schema_version": "duecare.gemma4.study_notebooks.v3",
        "dataset_id": dataset_id,
        "release_manifest_sha256": release_sha,
        "notebooks": records,
    }
    _write_json(output / "notebooks-manifest.json", manifest)
    return manifest


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--collection", type=Path, default=DEFAULT_COLLECTION)
    value.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    value.add_argument("--force", action="store_true")
    value.add_argument("--execute-local", action="store_true")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    print(
        json.dumps(
            build_notebooks(
                args.collection,
                args.output,
                force=args.force,
                execute_local=args.execute_local,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
