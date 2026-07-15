#!/usr/bin/env python3
# ruff: noqa: E501
"""Build three runnable, visual Kaggle notebooks for the public training corpora.

The notebooks are deliberately distinct:

* a plain-language loading quickstart over both datasets;
* a real central-processing-unit response-quality classification baseline;
* a split-isolation and training-data-quality dashboard.

Generation does not upload anything. Notebook privacy follows the attached
release manifests, and every notebook verifies exact release checksums before
loading rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESPONSE_COLLECTION = ROOT / "reports" / "kaggle_publish" / "response_training_collection_v6"
DEFAULT_LARGE_COLLECTION = ROOT / "reports" / "kaggle_publish" / "large_training_collection_v4"
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "showcase_notebooks_v1"

QUICKSTART_ID = "taylorsamarel/duecare-training-data-loading-quickstart"
BASELINE_ID = "taylorsamarel/duecare-response-quality-baseline"
QUALITY_ID = "taylorsamarel/duecare-training-data-quality-dashboard"
QUICKSTART_OUTPUTS = (
    "loading-quickstart-summary.json",
    "quickstart_rows_by_lane.png",
    "quickstart_reproducible_flow.png",
    "quickstart_file_formats.png",
)
BASELINE_OUTPUTS = (
    "response-quality-baseline-metrics.json",
    "baseline_label_balance.png",
    "baseline_metrics.png",
    "baseline_confusion_matrices.png",
    "baseline_response_lengths.png",
    "baseline_top_features.png",
)
QUALITY_OUTPUTS = (
    "training-data-quality-summary.json",
    "quality_rows_by_split.png",
    "quality_split_overlap_heatmaps.png",
    "quality_text_lengths.png",
    "quality_shard_sizes.png",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        # Kaggle's Windows command-line client may decode notebook JSON through
        # the active ANSI code page before upload. Escaping non-ASCII code
        # points keeps the package byte-safe without changing rendered text.
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
    return f"""<div style="padding:28px 32px;border-radius:18px;background:linear-gradient(120deg,#12355b,#1d7874,#679436);color:white;box-shadow:0 8px 24px rgba(0,0,0,.16)">
<div style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;opacity:.85">DueCare · Gemma 4 Good Hackathon learning artifact</div>
<h1 style="margin:.35em 0 .2em 0;font-size:34px">{title}</h1>
<p style="font-size:17px;line-height:1.5;margin:0;max-width:900px">{subtitle}</p>
</div>
"""


def _setup_code(
    *,
    response_dataset_id: str,
    large_dataset_id: str,
    response_sha: str,
    large_sha: str,
) -> str:
    return f'''from __future__ import annotations
import hashlib, json, os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import Markdown, display

RESPONSE_DATASET_ID = {response_dataset_id!r}
LARGE_DATASET_ID = {large_dataset_id!r}
EXPECTED_RESPONSE_SHA256 = {response_sha!r}
EXPECTED_LARGE_SHA256 = {large_sha!r}

COLORS = ["#1d7874", "#679436", "#f4a261", "#e76f51", "#457b9d", "#6d597a"]
plt.rcParams.update({{
    "figure.figsize": (10, 5.5),
    "figure.dpi": 110,
    "axes.facecolor": "#f7faf9",
    "axes.edgecolor": "#c8d5d1",
    "axes.grid": True,
    "grid.alpha": 0.22,
    "font.size": 11,
}})

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def find_dataset(dataset_id, expected_sha, environment_name):
    candidates = []
    override = os.environ.get(environment_name)
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
        manifest_path = root / "release-manifest.json"
        if not manifest_path.is_file():
            continue
        release = json.loads(manifest_path.read_text(encoding="utf-8"))
        if release.get("dataset_id") != dataset_id:
            continue
        actual = sha256_file(manifest_path)
        if actual != expected_sha:
            raise AssertionError(f"release checksum mismatch for {{dataset_id}}: {{actual}}")
        return root, release
    raise FileNotFoundError(f"attached dataset was not found: {{dataset_id}}")

response_root, response_release = find_dataset(
    RESPONSE_DATASET_ID, EXPECTED_RESPONSE_SHA256, "DUECARE_RESPONSE_DATASET_ROOT"
)
large_root, large_release = find_dataset(
    LARGE_DATASET_ID, EXPECTED_LARGE_SHA256, "DUECARE_LARGE_DATASET_ROOT"
)

in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
working = Path("/kaggle/working") if in_kaggle else Path.cwd()
out_dir = working / "duecare_showcase_outputs"
out_dir.mkdir(parents=True, exist_ok=True)
display(Markdown("✅ **Exact release manifests verified before loading data.**"))
'''


def _quickstart_notebook(
    *,
    response_dataset_id: str,
    large_dataset_id: str,
    response_sha: str,
    large_sha: str,
) -> dict[str, Any]:
    setup = _setup_code(
        response_dataset_id=response_dataset_id,
        large_dataset_id=large_dataset_id,
        response_sha=response_sha,
        large_sha=large_sha,
    )
    overview = r'''identity_rows = []
for release in (response_release, large_release):
    counts = release.get("counts", {})
    identity_rows.append({
        "dataset": release.get("title") or release.get("dataset_id"),
        "release": release.get("release_id"),
        "publication state": release.get("publication_state"),
        "safe to train": release.get("safe_to_train"),
        "safe to publish": release.get("safe_to_publish"),
        "declared lane rows": sum(value for value in counts.values() if isinstance(value, int)),
    })
identity_df = pd.DataFrame(identity_rows)
display(Markdown("### Verified dataset identity"))
display(identity_df.style.hide(axis="index").background_gradient(subset=["declared lane rows"], cmap="YlGn"))

glossary = pd.DataFrame([
    {"term": "Supervised fine-tuning", "meaning": "Training on an input paired with a reviewed desired answer."},
    {"term": "Preference optimization", "meaning": "Training from a prompt, a preferred answer, and a nonpreferred answer."},
    {"term": "Reward label", "meaning": "A bounded quality label attached to a prompt-response pair."},
    {"term": "JSON Lines", "meaning": "One complete JavaScript Object Notation object per line."},
    {"term": "Secure Hash Algorithm 256-bit checksum", "meaning": "A content fingerprint used to verify that a file has not changed."},
    {"term": "Adapter", "meaning": "Smaller task-specific weights that still depend on a base model."},
    {"term": "Contamination", "meaning": "Training or selection information overlaps an evaluation, so it is not independent evidence."},
])
display(Markdown("### Plain-language glossary"))
display(glossary.style.hide(axis="index").set_properties(subset=["meaning"], **{"text-align": "left"}))
'''
    load = r'''catalogs = []
for label, root in (("Measured response", response_root), ("Multiperspective synthetic", large_root)):
    frame = pd.read_csv(root / "dataset-overview.csv")
    frame.insert(0, "dataset", label)
    catalogs.append(frame)
catalog = pd.concat(catalogs, ignore_index=True, sort=False)
display(Markdown("### Lane and split catalog"))
display(catalog.fillna("—").style.hide(axis="index"))

chart = catalog[["dataset", "lane", "rows"]].copy()
chart["label"] = chart["dataset"] + " · " + chart["lane"]
ax = chart.sort_values("rows").plot.barh(x="label", y="rows", color=COLORS[0], legend=False, figsize=(11, 7))
ax.set_title("Rows by governed lane")
ax.set_xlabel("rows (logarithmic scale)")
ax.set_xscale("log")
plt.tight_layout()
plt.savefig(out_dir / "quickstart_rows_by_lane.png", dpi=150)
plt.show()

def first_row(root, pattern):
    shard = next(root.glob(pattern))
    with shard.open(encoding="utf-8") as handle:
        return json.loads(next(line for line in handle if line.strip()))

response_sample = first_row(response_root, "sft-positive-train-*.jsonl")
large_sample = first_row(large_root, "sft-train-*.jsonl")
sample_shape = pd.DataFrame([
    {"dataset": "Measured response", "top-level fields": len(response_sample), "message count": len(response_sample.get("messages", [])), "split": response_sample.get("split")},
    {"dataset": "Multiperspective synthetic", "top-level fields": len(large_sample), "message count": len(large_sample.get("messages", [])), "split": large_sample.get("split")},
])
display(Markdown("### Safe structural sample — no response text displayed"))
display(sample_shape.style.hide(axis="index").background_gradient(cmap="PuBu"))
'''
    map_code = r'''from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(12, 3.8))
ax.axis("off")
steps = [
    ("1", "Verify", "manifest + checksums"),
    ("2", "Choose lane", "training role + split"),
    ("3", "Stream rows", "JSON Lines"),
    ("4", "Train or inspect", "bounded purpose"),
    ("5", "Evaluate", "independent holdout"),
]
for index, (number, title, note) in enumerate(steps):
    x = 0.02 + index * 0.195
    box = FancyBboxPatch((x, .28), .16, .45, boxstyle="round,pad=.02,rounding_size=.03", facecolor=COLORS[index], edgecolor="white", linewidth=2)
    ax.add_patch(box)
    ax.text(x + .08, .61, number, ha="center", va="center", color="white", fontsize=18, weight="bold")
    ax.text(x + .08, .48, title, ha="center", va="center", color="white", fontsize=12, weight="bold")
    ax.text(x + .08, .36, note, ha="center", va="center", color="white", fontsize=9)
    if index < len(steps) - 1:
        ax.annotate("", xy=(x + .19, .5), xytext=(x + .165, .5), arrowprops={"arrowstyle": "->", "color": "#345", "lw": 2})
ax.set_title("A reproducible path from dataset to evidence", fontsize=16, pad=14)
plt.tight_layout()
plt.savefig(out_dir / "quickstart_reproducible_flow.png", dpi=150, bbox_inches="tight")
plt.show()

format_rows = []
for label, release in (("Measured response", response_release), ("Multiperspective synthetic", large_release)):
    files = release.get("artifacts") or release.get("files") or {}
    counts = {}
    for name in files:
        suffix = Path(name).suffix.lower() or "no extension"
        counts[suffix] = counts.get(suffix, 0) + 1
    format_rows.extend({"dataset": label, "format": suffix, "files": count} for suffix, count in counts.items())
format_df = pd.DataFrame(format_rows)
pivot = format_df.pivot_table(index="format", columns="dataset", values="files", fill_value=0)
display(Markdown("### Published file-format inventory"))
display(pivot.style.background_gradient(cmap="YlGnBu"))
ax = pivot.plot.bar(color=COLORS[: len(pivot.columns)])
ax.set_title("Release files by format")
ax.set_ylabel("files")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig(out_dir / "quickstart_file_formats.png", dpi=150)
plt.show()
'''
    recipes = r'''recipes = [
    (
        "Built-in Python streaming (no extra package)",
        "from pathlib import Path\nimport json\n\n"
        "with Path('sft-positive-train-00000.jsonl').open(encoding='utf-8') as handle:\n"
        "    for line in handle:\n"
        "        row = json.loads(line)\n"
        "        # train or inspect one governed row at a time",
    ),
    (
        "pandas table loading",
        "import pandas as pd\n\n"
        "frame = pd.read_json('sft-positive-train-00000.jsonl', lines=True)",
    ),
    (
        "Hugging Face Datasets streaming",
        "from datasets import load_dataset\n\n"
        "dataset = load_dataset(\n"
        "    'json',\n"
        "    data_files={'train': 'sft-positive-train-*.jsonl'},\n"
        "    streaming=True,\n"
        ")",
    ),
    (
        "Kagglehub into pandas",
        "import kagglehub\n"
        "from kagglehub import KaggleDatasetAdapter\n\n"
        "frame = kagglehub.dataset_load(\n"
        "    KaggleDatasetAdapter.PANDAS,\n"
        "    'taylorsamarel/duecare-measured-response-training-corpus',\n"
        "    'dataset-overview.csv',\n"
        ")",
    ),
    (
        "Polars lazy newline-delimited JSON scan",
        "import polars as pl\n\n"
        "lazy_rows = pl.scan_ndjson('sft-positive-train-*.jsonl')",
    ),
]
for title, snippet in recipes:
    display(Markdown(f"#### {title}\n\n```python\n{snippet}\n```"))

display(Markdown(
    "> Load the release manifest and verify its checksum first. Choose a lane by its declared "
    "training role; never treat quarantine, inventory, or nonpreferred response rows as desired answers."
))
'''
    summary = r'''summary = {
    "schema_version": "duecare.kaggle.loading_quickstart.v1",
    "response_dataset_id": RESPONSE_DATASET_ID,
    "response_release_manifest_sha256": EXPECTED_RESPONSE_SHA256,
    "large_dataset_id": LARGE_DATASET_ID,
    "large_release_manifest_sha256": EXPECTED_LARGE_SHA256,
    "datasets_verified": 2,
    "training_completed": False,
    "adapter_produced": False,
    "independent_model_lift_demonstrated": False,
    "charts": sorted(path.name for path in out_dir.glob("quickstart_*.png")),
}
(out_dir / "loading-quickstart-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(out_dir / "loading-quickstart-report.md").write_text(
    "# DueCare loading quickstart\n\nBoth exact releases were verified and loaded. "
    "This notebook did not train a model or produce an adapter.\n",
    encoding="utf-8",
)
display(Markdown("### Saved reproducibility artifacts"))
display(summary)
'''
    return _notebook(
        [
            _markdown("banner", _banner("Training Data Loading Quickstart", "Verify, understand, and load both DueCare training corpora with plain-language explanations and reusable Python patterns.")),
            _markdown("purpose", "## What this notebook teaches\n\nThis notebook verifies exact release checksums, explains the dataset lanes, loads safe structural examples, and visualizes the release layout. It does **not** train a model.\n"),
            _code("setup", setup),
            _markdown("identity", "## 1. Know what you are loading\n\nA release state, training permission, and publication permission answer different questions."),
            _code("identity-and-glossary", overview),
            _markdown("load", "## 2. Load the governed lanes\n\nUse the lane intended for your objective. Audit and quarantine lanes are not assistant targets."),
            _code("load-and-visualize", load),
            _markdown("workflow", "## 3. Connect data loading to reproducible evidence\n\nA notebook run is useful only when its exact inputs and claim boundary are visible."),
            _code("workflow-map", map_code),
            _markdown("recipes-heading", "## 4. Reuse portable loading patterns\n\nThese examples cover built-in Python, pandas, Hugging Face Datasets, Kagglehub, and Polars. Only the lightweight release inspection is executed here."),
            _code("loader-recipes", recipes),
            _markdown("save", "## 5. Save a compact run summary"),
            _code("summary", summary),
        ]
    )


def _baseline_notebook(
    *,
    response_dataset_id: str,
    response_sha: str,
) -> dict[str, Any]:
    setup = _setup_code(
        response_dataset_id=response_dataset_id,
        large_dataset_id="unused/unused",
        response_sha=response_sha,
        large_sha="0" * 64,
    )
    # The common setup's second dataset lookup is intentionally removed here.
    setup = setup.replace(
        'large_root, large_release = find_dataset(\n    LARGE_DATASET_ID, EXPECTED_LARGE_SHA256, "DUECARE_LARGE_DATASET_ROOT"\n)\n',
        "large_root = large_release = None\n",
    )
    load = r'''from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

index = json.loads((response_root / "shard-index.json").read_text(encoding="utf-8"))

def iter_lane(lane):
    for shard in index["lanes"][lane]["shards"]:
        with (response_root / shard["path"]).open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)

def load_split(split):
    rows = list(iter_lane(f"reward_labels_{split}"))
    return pd.DataFrame({
        "text": [row.get("prompt", "") + "\n\n" + row.get("response", "") for row in rows],
        "label": [int(row["label"]) for row in rows],
        "response_chars": [len(row.get("response", "")) for row in rows],
        "split": split,
    })

frames = {split: load_split(split) for split in ("train", "validation", "test")}
split_summary = pd.DataFrame([
    {"split": split, "rows": len(frame), "preferred": int(frame["label"].sum()), "nonpreferred": int((frame["label"] == 0).sum())}
    for split, frame in frames.items()
])
display(Markdown("### Loaded reward-label rows"))
display(split_summary.style.hide(axis="index").background_gradient(subset=["rows"], cmap="YlGn"))

ax = split_summary.set_index("split")[["preferred", "nonpreferred"]].plot.bar(stacked=True, color=[COLORS[0], COLORS[3]])
ax.set_title("Preferred and nonpreferred responses by split")
ax.set_ylabel("rows")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(out_dir / "baseline_label_balance.png", dpi=150)
plt.show()
'''
    train = r'''model = Pipeline([
    ("term_frequency_inverse_document_frequency", TfidfVectorizer(
        max_features=12000,
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
    )),
    ("logistic_regression", LogisticRegression(
        max_iter=800,
        class_weight="balanced",
        random_state=20260715,
    )),
])

model.fit(frames["train"]["text"], frames["train"]["label"])
length_model = LogisticRegression(
    max_iter=400,
    class_weight="balanced",
    random_state=20260715,
).fit(frames["train"][["response_chars"]], frames["train"]["label"])
display(Markdown("✅ **The small response-quality classifier finished training on the central processing unit.**"))
'''
    evaluate = r'''metric_rows = []
confusions = {}
for split in ("validation", "test"):
    frame = frames[split]
    predictions = {
        "text features": model.predict(frame["text"]),
        "response length only": length_model.predict(frame[["response_chars"]]),
    }
    for model_name, predicted in predictions.items():
        metric_rows.append({
            "model": model_name,
            "split": split,
            "accuracy": accuracy_score(frame["label"], predicted),
            "balanced accuracy": balanced_accuracy_score(frame["label"], predicted),
            "macro F1 score": f1_score(frame["label"], predicted, average="macro"),
        })
    confusions[split] = confusion_matrix(
        frame["label"], predictions["text features"], labels=[0, 1]
    )

metrics_df = pd.DataFrame(metric_rows)
display(Markdown("### Diagnostic metrics"))
display(metrics_df.style.hide(axis="index").format({"accuracy": "{:.3f}", "balanced accuracy": "{:.3f}", "macro F1 score": "{:.3f}"}).background_gradient(cmap="YlGn"))
metrics_df.to_csv(out_dir / "baseline-split-metrics.csv", index=False)

metric_plot = metrics_df.set_index(["split", "model"])[
    ["accuracy", "balanced accuracy", "macro F1 score"]
]
ax = metric_plot.plot.bar(color=COLORS[:3], ylim=(0, 1))
ax.set_title("Text-feature baseline versus a response-length shortcut")
ax.set_ylabel("score")
plt.xticks(rotation=22, ha="right")
plt.tight_layout()
plt.savefig(out_dir / "baseline_metrics.png", dpi=150)
plt.show()

fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
for axis, split in zip(axes, ("validation", "test")):
    matrix = confusions[split]
    image = axis.imshow(matrix, cmap="YlGnBu")
    for row in range(2):
        for column in range(2):
            axis.text(column, row, int(matrix[row, column]), ha="center", va="center", fontsize=15)
    axis.set_xticks([0, 1], ["nonpreferred", "preferred"], rotation=20)
    axis.set_yticks([0, 1], ["nonpreferred", "preferred"])
    axis.set_title(f"{split.title()} confusion matrix")
    axis.set_xlabel("predicted")
    axis.set_ylabel("actual")
fig.colorbar(image, ax=axes.ravel().tolist(), shrink=.78)
plt.savefig(out_dir / "baseline_confusion_matrices.png", dpi=150, bbox_inches="tight")
plt.show()

length_frame = pd.concat(frames.values(), ignore_index=True)
display(Markdown("### Response-length diagnostic"))
display(length_frame.groupby(["split", "label"])["response_chars"].agg(["count", "median", "mean", "max"]).round(1))
ax = length_frame.boxplot(column="response_chars", by=["split", "label"], showfliers=False, grid=False, figsize=(11, 5))
plt.suptitle("")
ax.set_title("Response length by split and label")
ax.set_ylabel("characters")
plt.tight_layout()
plt.savefig(out_dir / "baseline_response_lengths.png", dpi=150)
plt.show()

vectorizer = model.named_steps["term_frequency_inverse_document_frequency"]
classifier = model.named_steps["logistic_regression"]
features = vectorizer.get_feature_names_out()
weights = classifier.coef_[0]
ranked = pd.DataFrame({"feature": features, "weight": weights})
top_features = pd.concat([
    ranked.nsmallest(12, "weight").assign(direction="nonpreferred"),
    ranked.nlargest(12, "weight").assign(direction="preferred"),
]).sort_values("weight")
display(Markdown("### What surface features drive the diagnostic classifier?"))
display(top_features.style.hide(axis="index").background_gradient(subset=["weight"], cmap="RdYlGn"))
ax = top_features.plot.barh(
    x="feature",
    y="weight",
    color=[COLORS[3] if value < 0 else COLORS[0] for value in top_features["weight"]],
    legend=False,
    figsize=(10, 8),
)
ax.axvline(0, color="#334", linewidth=1)
ax.set_title("Largest text-feature weights (diagnostic, not causal)")
ax.set_xlabel("logistic-regression weight")
plt.tight_layout()
plt.savefig(out_dir / "baseline_top_features.png", dpi=150)
plt.show()

display(Markdown(
    "> **Interpretation:** a near-perfect score on these source-selected splits can reflect "
    "style, length, model-family, or grading shortcuts. The length-only comparator and feature "
    "weights help expose those risks; neither result is independent evidence of model improvement."
))
'''
    summary = r'''summary = {
    "schema_version": "duecare.kaggle.cpu_response_quality_baseline.v1",
    "dataset_id": RESPONSE_DATASET_ID,
    "release_manifest_sha256": EXPECTED_RESPONSE_SHA256,
    "model_kind": "term-frequency inverse-document-frequency plus logistic regression",
    "training_completed": True,
    "training_hardware": "central processing unit",
    "gemma_fine_tuning_completed": False,
    "adapter_produced": False,
    "independent_model_lift_demonstrated": False,
    "contamination_boundary": "The source grades selected these rows; validation and test results are diagnostics, not independent model-improvement evidence.",
    "shortcut_risk": "High diagnostic scores may reflect response style, length, model family, or grade-selection artifacts. Compare the length-only baseline and weighted features.",
    "split_rows": {row["split"]: int(row["rows"]) for row in split_summary.to_dict(orient="records")},
    "metrics": metrics_df.to_dict(orient="records"),
    "charts": sorted(path.name for path in out_dir.glob("baseline_*.png")),
}
(out_dir / "response-quality-baseline-metrics.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(out_dir / "response-quality-baseline-report.md").write_text(
    "# DueCare central-processing-unit response-quality baseline\n\n"
    "A small text classifier trained successfully. This was not Gemma fine-tuning, did not produce an adapter, "
    "and did not demonstrate independent model lift.\n",
    encoding="utf-8",
)
display(Markdown("### Honest result boundary"))
display(pd.DataFrame([
    {"claim": "Small response-quality classifier trained", "status": "yes"},
    {"claim": "Gemma fine-tuning completed", "status": "no"},
    {"claim": "Adapter produced", "status": "no"},
    {"claim": "Independent model lift demonstrated", "status": "no"},
]).style.hide(axis="index"))
display(summary)
'''
    return _notebook(
        [
            _markdown("banner", _banner("Central-Processing-Unit Response-Quality Baseline", "A real, short classification run that demonstrates loading, fitting, evaluation, charts, and honest claim tracking without pretending to fine-tune Gemma.")),
            _markdown("definitions", "## Before we train\n\n**Central processing unit (CPU)** means the ordinary processor used for this small run. **Term-frequency inverse-document-frequency** converts text into weighted word and phrase features. **Logistic regression** is the classifier. **International Labour Organization (ILO)** may appear in learned feature labels because it occurs in the corpus. This is a data-pipeline proof, not a large language model fine-tune.\n"),
            _code("setup", setup),
            _markdown("load-heading", "## 1. Load the governed reward-label lane\n\nPreferred and nonpreferred responses remain in the split assigned by the release."),
            _code("load", load),
            _markdown("fit", "## 2. Fit a compact baseline\n\nThe model is intentionally small enough to run quickly without a graphics processing unit."),
            _code("train", train),
            _markdown("evaluate-heading", "## 3. Evaluate diagnostic holdouts\n\nThese splits are isolated diagnostics but are not independent evidence because source grades influenced row selection."),
            _code("evaluate", evaluate),
            _markdown("claims", "## 4. Save metrics and state exactly what happened"),
            _code("summary", summary),
        ]
    )


def _quality_notebook(
    *,
    response_dataset_id: str,
    large_dataset_id: str,
    response_sha: str,
    large_sha: str,
) -> dict[str, Any]:
    setup = _setup_code(
        response_dataset_id=response_dataset_id,
        large_dataset_id=large_dataset_id,
        response_sha=response_sha,
        large_sha=large_sha,
    )
    audit = r'''def lane_index(root):
    return json.loads((root / "shard-index.json").read_text(encoding="utf-8"))

def iter_lane(root, index, lane):
    for shard in index["lanes"][lane]["shards"]:
        with (root / shard["path"]).open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)

def prompt_text(row):
    if isinstance(row.get("prompt"), str):
        return row["prompt"]
    return " ".join(
        item.get("content", "")
        for item in row.get("messages", [])
        if item.get("role") == "user"
    )

def answer_text(row):
    return " ".join(
        item.get("content", "")
        for item in row.get("messages", [])
        if item.get("role") == "assistant"
    )

def canonical_hash(text):
    return hashlib.sha256(" ".join(text.split()).casefold().encode("utf-8")).hexdigest()

response_index = lane_index(response_root)
large_index = lane_index(large_root)
specs = [
    ("Measured response", response_root, response_index, {"train": "sft_positive_train", "validation": "sft_positive_validation", "test": "sft_positive_test"}, "prompt_cluster_id"),
    ("Multiperspective synthetic", large_root, large_index, {"train": "sft_train", "validation": "sft_validation", "test": "sft_test"}, "lineage_family_id"),
]

audit_rows = []
length_rows = []
prompt_sets = {}
family_sets = {}
for dataset_label, root, index, lanes, family_key in specs:
    for split, lane in lanes.items():
        prompts, families = set(), set()
        rows = 0
        for row in iter_lane(root, index, lane):
            prompt = prompt_text(row)
            prompts.add(canonical_hash(prompt))
            family = row.get(family_key) or row.get("lineage_id")
            if family:
                families.add(str(family))
            if len(length_rows) < 30000:
                length_rows.append({"dataset": dataset_label, "split": split, "prompt characters": len(prompt), "answer characters": len(answer_text(row))})
            rows += 1
        prompt_sets[(dataset_label, split)] = prompts
        family_sets[(dataset_label, split)] = families
        audit_rows.append({"dataset": dataset_label, "split": split, "rows": rows, "unique prompt hashes": len(prompts), "unique families": len(families)})

audit_df = pd.DataFrame(audit_rows)
length_df = pd.DataFrame(length_rows)
display(Markdown("### Split identity and uniqueness"))
display(audit_df.style.hide(axis="index").background_gradient(subset=["rows", "unique prompt hashes", "unique families"], cmap="YlGn"))

ax = audit_df.pivot(index="split", columns="dataset", values="rows").plot.bar(color=COLORS[:2])
ax.set_title("Supervised fine-tuning rows by split")
ax.set_ylabel("rows")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(out_dir / "quality_rows_by_split.png", dpi=150)
plt.show()
'''
    overlap = r'''import numpy as np

def overlap_table(sets, dataset_label):
    splits = ["train", "validation", "test"]
    return pd.DataFrame(
        [[len(sets[(dataset_label, left)] & sets[(dataset_label, right)]) for right in splits] for left in splits],
        index=splits,
        columns=splits,
    )

overlap_results = {}
fig, axes = plt.subplots(2, 2, figsize=(13.5, 10.5))
for row_index, dataset_label in enumerate(("Measured response", "Multiperspective synthetic")):
    for column_index, (name, sets) in enumerate((("prompt hashes", prompt_sets), ("lineage families", family_sets))):
        table = overlap_table(sets, dataset_label)
        overlap_results[f"{dataset_label} {name}"] = table.to_dict()
        axis = axes[row_index, column_index]
        color_values = np.log1p(table.values)
        axis.imshow(color_values, cmap="YlGnBu")
        color_max = float(color_values.max()) or 1.0
        for row in range(3):
            for column in range(3):
                axis.text(
                    column,
                    row,
                    f"{int(table.iloc[row, column]):,}",
                    ha="center",
                    va="center",
                    color="white" if color_values[row, column] > color_max * .55 else "#15202b",
                    fontsize=13,
                    weight="bold" if row == column else "normal",
                )
        axis.set_xticks(range(3), table.columns, rotation=0)
        axis.set_yticks(range(3), table.index)
        short_label = "Multiperspective" if dataset_label.startswith("Multiperspective") else dataset_label
        axis.set_title(f"{short_label} — {name}", pad=14, fontsize=14, weight="bold")
        axis.set_xlabel("comparison split")
        axis.set_ylabel("source split")
fig.suptitle("Exact cross-split overlap audit", fontsize=19, weight="bold", y=.995)
fig.text(.5, .012, "Cell color uses log(1 + overlap); annotations show exact counts. Off-diagonal cells must be zero.", ha="center", fontsize=10, color="#43515c")
plt.tight_layout(rect=(0, .035, 1, .965), h_pad=4.0, w_pad=2.5)
plt.savefig(out_dir / "quality_split_overlap_heatmaps.png", dpi=150, bbox_inches="tight")
plt.show()

off_diagonal_failures = []
for dataset_label in ("Measured response", "Multiperspective synthetic"):
    for name, sets in (("prompt hashes", prompt_sets), ("lineage families", family_sets)):
        for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
            count = len(sets[(dataset_label, left)] & sets[(dataset_label, right)])
            if count:
                off_diagonal_failures.append({"dataset": dataset_label, "kind": name, "left": left, "right": right, "overlap": count})

if off_diagonal_failures:
    display(Markdown("⚠️ **Cross-split overlap was detected. Review before training.**"))
    display(pd.DataFrame(off_diagonal_failures))
else:
    display(Markdown("✅ **No exact prompt-hash or lineage-family overlap was found across declared splits.**"))
'''
    diagnostics = r'''display(Markdown("### Text-length profile"))
display(length_df.groupby(["dataset", "split"])[["prompt characters", "answer characters"]].agg(["count", "median", "mean", "max"]).round(1))

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
for axis, column in zip(axes, ("prompt characters", "answer characters")):
    for color, (label, group) in zip(COLORS, length_df.groupby("dataset")):
        axis.hist(group[column], bins=40, alpha=.52, label=label, color=color)
    axis.set_title(column.title())
    axis.set_xlabel("characters")
    axis.set_ylabel("sampled rows")
    axis.legend()
plt.tight_layout()
plt.savefig(out_dir / "quality_text_lengths.png", dpi=150)
plt.show()

shard_rows = []
for dataset_label, root, index, _lanes, _family_key in specs:
    for lane, details in index["lanes"].items():
        for shard in details["shards"]:
            shard_rows.append({"dataset": dataset_label, "lane": lane, "rows": shard.get("rows", 0), "megabytes": shard.get("bytes", 0) / 1_000_000})
shards_df = pd.DataFrame(shard_rows)
display(Markdown("### Shard-size profile"))
display(shards_df.groupby(["dataset", "lane"])[["rows", "megabytes"]].agg(["count", "min", "median", "max"]).round(2))
ax = shards_df.plot.scatter(x="rows", y="megabytes", c=shards_df["dataset"].map({"Measured response": COLORS[0], "Multiperspective synthetic": COLORS[1]}), alpha=.75, s=55)
ax.set_title("Shard rows and file size")
plt.tight_layout()
plt.savefig(out_dir / "quality_shard_sizes.png", dpi=150)
plt.show()

governance = pd.DataFrame([
    {"dataset": response_release["dataset_id"], "safe to train": response_release.get("safe_to_train"), "safe to publish": response_release.get("safe_to_publish"), **response_release.get("claims", {})},
    {"dataset": large_release["dataset_id"], "safe to train": large_release.get("safe_to_train"), "safe to publish": large_release.get("safe_to_publish"), **large_release.get("claims", {})},
])
display(Markdown("### Governance and claim state"))
display(governance.style.hide(axis="index"))
'''
    summary = r'''summary = {
    "schema_version": "duecare.kaggle.training_data_quality_dashboard.v1",
    "response_release_manifest_sha256": EXPECTED_RESPONSE_SHA256,
    "large_release_manifest_sha256": EXPECTED_LARGE_SHA256,
    "split_audit": audit_df.to_dict(orient="records"),
    "cross_split_overlap_failures": off_diagonal_failures,
    "cross_split_isolation_passed": not off_diagonal_failures,
    "training_completed": False,
    "adapter_produced": False,
    "independent_model_lift_demonstrated": False,
    "charts": sorted(path.name for path in out_dir.glob("quality_*.png")),
}
(out_dir / "training-data-quality-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
audit_df.to_csv(out_dir / "training-data-split-audit.csv", index=False)
(out_dir / "training-data-quality-report.md").write_text(
    "# DueCare training-data quality dashboard\n\n"
    f"Cross-split exact prompt and family isolation passed: {not off_diagonal_failures}. "
    "No model was trained by this notebook.\n",
    encoding="utf-8",
)
display(Markdown("### Saved quality evidence"))
display(summary)
assert not off_diagonal_failures
'''
    return _notebook(
        [
            _markdown("banner", _banner("Training Data Quality Dashboard", "Inspect split isolation, lineage boundaries, row lengths, shard sizes, and claim state across both public DueCare corpora.")),
            _markdown("scope", "## What this dashboard checks\n\nIt uses exact prompt fingerprints and lineage-family identifiers to test whether related examples cross training, validation, and test boundaries. It displays aggregate evidence and never exports response text.\n"),
            _code("setup", setup),
            _markdown("inventory", "## 1. Inventory each declared split"),
            _code("split-audit", audit),
            _markdown("overlap-heading", "## 2. Test exact split isolation\n\nThe diagonal shows the size of each split. Every off-diagonal cell should be zero."),
            _code("overlap", overlap),
            _markdown("diagnostics-heading", "## 3. Inspect length, shard, and governance diagnostics"),
            _code("diagnostics", diagnostics),
            _markdown("save", "## 4. Save a machine-readable audit result"),
            _code("summary", summary),
        ]
    )


def _write_kernel(
    path: Path,
    *,
    notebook: Mapping[str, Any],
    notebook_id: str,
    title: str,
    dataset_ids: Sequence[str],
    is_private: bool,
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _write_json(path / "notebook.ipynb", notebook)
    _write_json(
        path / "kernel-metadata.json",
        {
            "id": notebook_id,
            "title": title,
            "code_file": "notebook.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": is_private,
            "enable_gpu": False,
            "enable_internet": False,
            "dataset_sources": list(dataset_ids),
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": [],
            "keywords": ["nlp"],
        },
    )


def _execute(
    notebook_path: Path,
    *,
    response_root: Path,
    large_root: Path,
) -> None:
    import nbformat
    from nbclient import NotebookClient

    output = notebook_path.parent / "duecare_showcase_outputs"
    if output.exists():
        if not output.is_dir() or output.is_symlink():
            raise ValueError("showcase output path must be a normal directory")
        shutil.rmtree(output)
    notebook = nbformat.read(notebook_path, as_version=4)
    old = {
        "DUECARE_RESPONSE_DATASET_ROOT": os.environ.get("DUECARE_RESPONSE_DATASET_ROOT"),
        "DUECARE_LARGE_DATASET_ROOT": os.environ.get("DUECARE_LARGE_DATASET_ROOT"),
    }
    # Each kernel starts in its own notebook folder.  Absolute overrides keep
    # local verification independent of the repository-relative CLI paths.
    os.environ["DUECARE_RESPONSE_DATASET_ROOT"] = str(response_root.resolve())
    os.environ["DUECARE_LARGE_DATASET_ROOT"] = str(large_root.resolve())
    try:
        NotebookClient(
            notebook,
            timeout=1200,
            kernel_name="python3",
            resources={"metadata": {"path": str(notebook_path.parent)}},
        ).execute()
    finally:
        for name, value in old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    # Preserve the same ASCII-safe serialization after execution. ``nbformat``
    # otherwise rewrites rendered Unicode characters literally, which can make
    # the Windows Kaggle client fail before it reaches the remote service.
    _write_json(notebook_path, notebook)


def build(
    *,
    response_collection: Path,
    large_collection: Path,
    output: Path,
    execute_local: bool,
) -> dict[str, Any]:
    response_dataset = response_collection / "dataset"
    large_dataset = large_collection / "dataset"
    response_release_path = response_dataset / "release-manifest.json"
    large_release_path = large_dataset / "release-manifest.json"
    response_release = _read_json(response_release_path)
    large_release = _read_json(large_release_path)
    for label, release in (("measured response", response_release), ("multiperspective", large_release)):
        if release.get("safe_to_train") is not True:
            raise ValueError(f"{label} release must explicitly set safe_to_train=true")

    response_id = str(response_release["dataset_id"])
    large_id = str(large_release["dataset_id"])
    response_sha = _sha256_file(response_release_path)
    large_sha = _sha256_file(large_release_path)
    public = response_release.get("safe_to_publish") is True and large_release.get("safe_to_publish") is True

    if output.exists():
        if not output.is_dir() or output.is_symlink():
            raise ValueError("showcase output must be a normal directory")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    quickstart = output / "loading_quickstart"
    baseline = output / "cpu_response_quality_baseline"
    quality = output / "training_data_quality_dashboard"
    _write_kernel(
        quickstart,
        notebook=_quickstart_notebook(
            response_dataset_id=response_id,
            large_dataset_id=large_id,
            response_sha=response_sha,
            large_sha=large_sha,
        ),
        notebook_id=QUICKSTART_ID,
        title="DueCare Training Data Loading Quickstart",
        dataset_ids=[response_id, large_id],
        is_private=not public,
    )
    _write_kernel(
        baseline,
        notebook=_baseline_notebook(response_dataset_id=response_id, response_sha=response_sha),
        notebook_id=BASELINE_ID,
        title="DueCare Response Quality Baseline",
        dataset_ids=[response_id],
        is_private=response_release.get("safe_to_publish") is not True,
    )
    _write_kernel(
        quality,
        notebook=_quality_notebook(
            response_dataset_id=response_id,
            large_dataset_id=large_id,
            response_sha=response_sha,
            large_sha=large_sha,
        ),
        notebook_id=QUALITY_ID,
        title="DueCare Training Data Quality Dashboard",
        dataset_ids=[response_id, large_id],
        is_private=not public,
    )

    if execute_local:
        execution_cases = (
            (quickstart / "notebook.ipynb", QUICKSTART_OUTPUTS),
            (baseline / "notebook.ipynb", BASELINE_OUTPUTS),
            (quality / "notebook.ipynb", QUALITY_OUTPUTS),
        )
        for notebook_path, expected_outputs in execution_cases:
            _execute(
                notebook_path,
                response_root=response_dataset,
                large_root=large_dataset,
            )
            output_dir = notebook_path.parent / "duecare_showcase_outputs"
            missing = [
                name for name in expected_outputs if not (output_dir / name).is_file()
            ]
            if missing:
                raise ValueError(
                    f"local notebook execution did not create expected outputs: {missing}"
                )

    manifest = {
        "schema_version": "duecare.kaggle.training_showcase_notebooks.v1",
        "response_dataset_id": response_id,
        "response_release_manifest_sha256": response_sha,
        "large_dataset_id": large_id,
        "large_release_manifest_sha256": large_sha,
        "public": public,
        "notebooks": {
            "loading_quickstart": {
                "id": QUICKSTART_ID,
                "path": "loading_quickstart",
                "executed_local": execute_local,
                "purpose": "plain-language loading and release navigation",
                "expected_outputs": list(QUICKSTART_OUTPUTS),
            },
            "cpu_response_quality_baseline": {
                "id": BASELINE_ID,
                "path": "cpu_response_quality_baseline",
                "executed_local": execute_local,
                "purpose": "real small central-processing-unit classification baseline",
                "expected_outputs": list(BASELINE_OUTPUTS),
            },
            "training_data_quality_dashboard": {
                "id": QUALITY_ID,
                "path": "training_data_quality_dashboard",
                "executed_local": execute_local,
                "purpose": "split isolation, lineage, length, shard, and claim audit",
                "expected_outputs": list(QUALITY_OUTPUTS),
            },
        },
        "gemma_fine_tuning_completed": False,
        "adapter_produced": False,
        "independent_model_lift_demonstrated": False,
    }
    _write_json(output / "showcase-notebooks-manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response-collection", type=Path, default=DEFAULT_RESPONSE_COLLECTION)
    parser.add_argument("--large-collection", type=Path, default=DEFAULT_LARGE_COLLECTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--execute-local", action="store_true")
    args = parser.parse_args()
    result = build(
        response_collection=args.response_collection,
        large_collection=args.large_collection,
        output=args.output,
        execute_local=args.execute_local,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
