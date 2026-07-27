#!/usr/bin/env python3
# ruff: noqa: E501
"""Build two public, CPU-safe visual notebooks for the 200K review curriculum."""

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
    ROOT
    / "reports"
    / "kaggle_publish"
    / "measured_review_curriculum_200k_v1"
)
DEFAULT_OUTPUT = (
    ROOT / "reports" / "kaggle_publish" / "measured_curriculum_notebooks_v1"
)
DATASET_ID = "taylorsamarel/duecare-measured-review-curriculum-200k"
ATLAS_ID = "taylorsamarel/duecare-200k-curriculum-visual-atlas"
LINEAGE_ID = "taylorsamarel/duecare-200k-lineage-split-laboratory"
MARKER = ".duecare-measured-curriculum-notebooks"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
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
    return f"""<div style="padding:30px 34px;border-radius:22px;background:linear-gradient(120deg,#14213d,#0a7c72,#fca311);color:white;box-shadow:0 12px 30px rgba(20,33,61,.22)">
<div style="font-size:13px;letter-spacing:.14em;text-transform:uppercase;opacity:.88">DueCare - Kaggle and Gemma hackathon learning artifact</div>
<h1 style="margin:.35em 0 .2em;font-size:36px">{title}</h1>
<p style="font-size:17px;line-height:1.55;margin:0;max-width:980px">{subtitle}</p>
</div>"""


def _setup(release_sha: str, output_subdir: str) -> str:
    return f'''from __future__ import annotations
import hashlib, json, os, time
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from IPython.display import HTML, Markdown, display

DATASET_ID = {DATASET_ID!r}
EXPECTED_RELEASE_SHA256 = {release_sha!r}
COLORS = ["#0a7c72", "#fca311", "#d1495b", "#247ba0", "#6d597a", "#4f772d", "#8d6e63", "#6c757d"]
plt.rcParams.update({{
    "figure.figsize": (11.2, 5.8),
    "figure.dpi": 120,
    "axes.facecolor": "#f8fbfa",
    "axes.edgecolor": "#bfd5d0",
    "axes.grid": True,
    "grid.alpha": 0.18,
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
    override = os.environ.get("DUECARE_MEASURED_CURRICULUM_ROOT")
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
        release_path = root / "release-manifest.json"
        if not release_path.is_file():
            continue
        release = json.loads(release_path.read_text(encoding="utf-8"))
        if release.get("dataset_id") != DATASET_ID:
            continue
        actual = sha256_file(release_path)
        if actual != EXPECTED_RELEASE_SHA256:
            raise AssertionError(f"release checksum mismatch: {{actual}}")
        return root, release
    raise FileNotFoundError(f"Attach Kaggle dataset {{DATASET_ID}}")

def iter_jsonl(path, limit=None):
    with Path(path).open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if limit is not None and index >= limit:
                break
            if line.strip():
                yield json.loads(line)

dataset_root, release = find_dataset()
candidate = json.loads((dataset_root / "candidate-manifest.json").read_text(encoding="utf-8"))
audit = json.loads((dataset_root / "quality-audit.json").read_text(encoding="utf-8"))
shard_index = json.loads((dataset_root / "shard-index.json").read_text(encoding="utf-8"))
in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
default_output = Path("/kaggle/working") if in_kaggle else Path.cwd()
output_root = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", default_output))
out_dir = output_root / {output_subdir!r}
out_dir.mkdir(parents=True, exist_ok=True)
display(Markdown("Verified the exact release-manifest SHA-256 before loading rows."))
'''


def _atlas_notebook(release_sha: str) -> dict[str, Any]:
    cells = [
        _markdown(
            "banner",
            _banner(
                "200K curriculum visual atlas",
                "A reviewer-friendly tour of scale, task coverage, audience coverage, preference failures, shards, and the difference between many rows and independent evidence.",
            ),
        ),
        _markdown(
            "plain-language",
            """
## Start here: what the training lanes mean

**Supervised fine-tuning** trains a model to produce a preferred answer for a
given prompt. **Preference training** presents a preferred answer and a
deliberately flawed alternative. The model can then learn which response
properties are preferred.

This dataset has more than 200,000 rows in each training lane, but those rows
are structured views of 649 training parents. The visuals therefore report
both row scale and parent scale. More wording variants do not become more
independent evidence.
""",
        ),
        _code("setup", _setup(release_sha, "curriculum-atlas")),
        _markdown("identity-heading", "## 1. Dataset identity and claim boundary"),
        _code(
            "identity",
            '''identity = pd.DataFrame([
    ("Dataset", release["dataset_id"]),
    ("Publication state", release["publication_state"]),
    ("Supervised train rows", f'{release["counts"]["supervised_train"]:,}'),
    ("Preference train pairs", f'{release["counts"]["preference_train"]:,}'),
    ("Training parents", f'{release["parent_counts"]["train"]:,}'),
    ("Independent observations", str(release["independent_observation"])),
    ("Quality audit clean", str(audit["clean"])),
    ("Independent model lift", "Not demonstrated by this dataset"),
], columns=["Field", "Value"])
display(HTML(identity.to_html(index=False, escape=True)))
display(Markdown("> **Interpretation:** the package is public and trainable, but benchmark ancestry prevents an independent model-improvement claim."))''',
        ),
        _markdown("lanes-heading", "## 2. Lanes: training, validation, and test"),
        _code(
            "lane-chart",
            '''lane_names = {
    "supervised_train": "Supervised train",
    "preference_train": "Preference train",
    "supervised_validation": "Validation",
    "supervised_test": "Test",
}
lane = pd.Series(release["counts"]).rename(index=lane_names).sort_values()
ax = lane.plot.barh(color=COLORS[:len(lane)], title="Rows by dataset lane")
ax.set_xlabel("Rows")
for container in ax.containers:
    ax.bar_label(container, labels=[f"{int(v):,}" for v in container.datavalues], padding=4)
plt.tight_layout(); plt.savefig(out_dir / "rows_by_lane.png", bbox_inches="tight"); plt.show()
display(Markdown("The held-out lanes are intentionally much smaller; their descendants inherit whole-parent split assignments."))''',
        ),
        _markdown("coverage-heading", "## 3. Curriculum coverage"),
        _code(
            "task-chart",
            '''tasks = pd.Series(audit["axis_counts"]["task"]).rename(index=lambda value: value.replace("_", " ").title()).sort_values()
ax = tasks.plot.barh(color="#0a7c72", title="Supervised training examples by review task")
ax.set_xlabel("Rows")
plt.tight_layout(); plt.savefig(out_dir / "review_task_coverage.png", bbox_inches="tight"); plt.show()''',
        ),
        _code(
            "audience-chart",
            '''audiences = pd.Series(audit["axis_counts"]["audience"]).rename(index=lambda value: value.replace("_", " ").title()).sort_values()
ax = audiences.plot.barh(color="#247ba0", title="Audience coverage")
ax.set_xlabel("Rows")
plt.tight_layout(); plt.savefig(out_dir / "audience_coverage.png", bbox_inches="tight"); plt.show()''',
        ),
        _code(
            "format-chart",
            '''formats = pd.Series(audit["axis_counts"]["format"]).sort_values(ascending=False)
fig, ax = plt.subplots()
ax.pie(formats.values, labels=[name.replace("_", " ") for name in formats.index], autopct="%1.1f%%", colors=COLORS[:4], startangle=90)
ax.set_title("Presentation-format balance")
plt.tight_layout(); plt.savefig(out_dir / "presentation_format_balance.png", bbox_inches="tight"); plt.show()''',
        ),
        _markdown(
            "coverage-note",
            "Balanced axes make coverage visible and auditable. They do not prove that every combination is equally useful, natural, or safe; downstream sampling should still be validated against held-out tasks.",
        ),
        _markdown("preference-heading", "## 4. What the rejected responses teach"),
        _code(
            "failure-chart",
            '''failure_gate = next(g for g in audit["gates"] if g["id"] == "preference_failures_complete")
failures = pd.Series(failure_gate["counts"]).rename(index=lambda value: value.replace("_", " ").title()).sort_values()
ax = failures.plot.barh(color="#d1495b", title="Controlled failure type in preference pairs")
ax.set_xlabel("Pairs")
plt.tight_layout(); plt.savefig(out_dir / "controlled_failure_balance.png", bbox_inches="tight"); plt.show()
display(Markdown("A rejected response is a controlled contrast, not an approved answer and not a real-world incident."))''',
        ),
        _markdown("independence-heading", "## 5. Row scale versus independent-parent scale"),
        _code(
            "parent-chart",
            '''scale = pd.DataFrame({
    "Object": ["Training parents", "Supervised rows", "Preference pairs", "Serialized train targets"],
    "Count": [release["parent_counts"]["train"], release["counts"]["supervised_train"], release["counts"]["preference_train"], 2 * release["counts"]["preference_train"]],
})
ax = sns.barplot(data=scale, y="Object", x="Count", hue="Object", legend=False, palette=COLORS[:4])
ax.set_xscale("log"); ax.set_title("Coverage scale is not independent sample size"); ax.set_xlabel("Count on logarithmic scale")
plt.tight_layout(); plt.savefig(out_dir / "rows_vs_parents.png", bbox_inches="tight"); plt.show()
views_per_parent = release["counts"]["supervised_train"] / release["parent_counts"]["train"]
display(Markdown(f"Each training parent has **{views_per_parent:.0f} supervised curriculum views**. Group and cap weights by parent hash or lineage family."))''',
        ),
        _markdown("shards-heading", "## 6. Shard design and CPU-safe loading"),
        _code(
            "shard-chart",
            '''shards = []
for lane_name, declarations in shard_index.items():
    for item in declarations:
        shards.append({"lane": lane_name, "rows": item["rows"], "megabytes": item["bytes"] / 1_000_000})
shard_df = pd.DataFrame(shards)
display(shard_df.groupby("lane").agg(shards=("rows", "size"), rows=("rows", "sum"), mean_megabytes=("megabytes", "mean")).round(2))
fig, ax = plt.subplots()
sns.boxplot(data=shard_df, x="megabytes", y="lane", hue="lane", legend=False, ax=ax, palette=COLORS)
ax.set_title("Shard size distribution"); ax.set_xlabel("Megabytes"); ax.set_ylabel("")
plt.tight_layout(); plt.savefig(out_dir / "shard_sizes.png", bbox_inches="tight"); plt.show()''',
        ),
        _code(
            "length-chart",
            '''sample_decl = shard_index["supervised_train"][0]
sample_path = dataset_root / sample_decl["path"]
sample_rows = list(iter_jsonl(sample_path, limit=2000))
lengths = []
for row in sample_rows:
    user = next(message["content"] for message in row["messages"] if message["role"] == "user")
    assistant = next(message["content"] for message in row["messages"] if message["role"] == "assistant")
    lengths.append({"Prompt characters": len(user), "Target characters": len(assistant)})
length_df = pd.DataFrame(lengths)
ax = length_df.plot.hist(bins=35, alpha=.72, color=COLORS[:2], title="Text lengths in a deterministic 2,000-row sample")
ax.set_xlabel("Characters")
plt.tight_layout(); plt.savefig(out_dir / "sample_text_lengths.png", bbox_inches="tight"); plt.show()
display(length_df.describe().round(1))''',
        ),
        _markdown("finish-heading", "## 7. Machine-readable notebook output"),
        _code(
            "finish",
            '''summary = {
    "dataset_id": DATASET_ID,
    "release_manifest_sha256": EXPECTED_RELEASE_SHA256,
    "counts": release["counts"],
    "parent_counts": release["parent_counts"],
    "quality_audit_clean": audit["clean"],
    "sample_rows_loaded": len(sample_rows),
    "charts": sorted(path.name for path in out_dir.glob("*.png")),
    "gpu_training_ran_in_this_notebook": False,
    "adapter_produced_in_this_notebook": False,
    "independent_model_lift_demonstrated": False,
}
(out_dir / "curriculum-atlas-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
display(Markdown(f"Saved **{len(summary['charts'])} charts** and `curriculum-atlas-summary.json`."))''',
        ),
    ]
    return _notebook(cells)


def _lineage_notebook(release_sha: str) -> dict[str, Any]:
    cells = [
        _markdown(
            "banner",
            _banner(
                "Synthetic lineage and leakage lab",
                "A hands-on explanation of parent-bound splitting, checksum verification, amplification, streaming, and why row-level random splitting can create misleading evaluation results.",
            ),
        ),
        _markdown(
            "terms",
            """
## Terms in plain language

- **Lineage** records which parent and transformation produced each row.
- **Data leakage** occurs when related information appears on both sides of a
  training/evaluation boundary.
- **SHA-256** is a cryptographic checksum used here to detect changed files.
- **Effective sample size** is the amount of genuinely independent information;
  it can be far smaller than the number of generated rows.

This notebook does not train a model. It teaches the data-engineering controls
that must come before a defensible training claim.
""",
        ),
        _code("setup", _setup(release_sha, "lineage-lab")),
        _markdown("verify-heading", "## 1. Verify identity before analysis"),
        _code(
            "verification",
            '''checks = []
for name in ["candidate-manifest.json", "quality-audit.json", "publication-approval.json", "shard-index.json"]:
    path = dataset_root / name
    checks.append({"artifact": name, "present": path.is_file(), "sha256_prefix": sha256_file(path)[:16] if path.is_file() else None})
check_df = pd.DataFrame(checks)
display(HTML(check_df.to_html(index=False)))
ax = check_df.assign(value=check_df["present"].astype(int)).plot.bar(x="artifact", y="value", color="#0a7c72", legend=False, title="Required control artifacts present")
ax.set_ylim(0, 1.15); ax.set_ylabel("Present (1=yes)"); ax.tick_params(axis="x", rotation=25)
plt.tight_layout(); plt.savefig(out_dir / "control_artifact_checks.png", bbox_inches="tight"); plt.show()''',
        ),
        _markdown("split-heading", "## 2. Splits are inherited from parents"),
        _code(
            "split-chart",
            '''split_frame = pd.DataFrame({
    "split": ["train", "validation", "test"],
    "parents": [release["parent_counts"]["train"], release["parent_counts"]["validation"], release["parent_counts"]["test"]],
    "supervised_rows": [release["counts"]["supervised_train"], release["counts"]["supervised_validation"], release["counts"]["supervised_test"]],
})
display(split_frame)
plot = split_frame.melt(id_vars="split", var_name="unit", value_name="count")
ax = sns.barplot(data=plot, x="split", y="count", hue="unit", palette=COLORS[:2])
ax.set_yscale("log"); ax.set_title("Whole-parent splits: parents and generated descendants"); ax.set_ylabel("Count on logarithmic scale")
plt.tight_layout(); plt.savefig(out_dir / "parent_bound_splits.png", bbox_inches="tight"); plt.show()''',
        ),
        _markdown("amplification-heading", "## 3. Augmentation expands coverage, not evidence"),
        _code(
            "amplification",
            '''train_parents = release["parent_counts"]["train"]
train_rows = release["counts"]["supervised_train"]
views = train_rows / train_parents
amplification = pd.DataFrame({
    "measure": ["Training parents", "Supervised descendants", "Preference descendants"],
    "count": [train_parents, train_rows, release["counts"]["preference_train"]],
})
ax = sns.barplot(data=amplification, x="measure", y="count", hue="measure", legend=False, palette=COLORS[:3])
ax.set_yscale("log"); ax.set_title(f"A {views:.0f}x supervised-view multiplier per training parent"); ax.tick_params(axis="x", rotation=12)
plt.tight_layout(); plt.savefig(out_dir / "augmentation_multiplier.png", bbox_inches="tight"); plt.show()
display(Markdown("A conservative sampler caps total weight by `parent_row_sha256` or `parent_lineage_family_id`."))''',
        ),
        _markdown("leakage-heading", "## 4. Why random row splitting is unsafe"),
        _code(
            "leakage-simulation",
            '''# Probability that every descendant from one parent lands in one split under
# an independent 80/10/10 row assignment. The complement is parent leakage.
descendants = pd.Series([1, 2, 4, 8, 16, 32, 64, 160, 320], name="views_per_parent")
same_split = 0.8 ** descendants + 0.1 ** descendants + 0.1 ** descendants
leakage = 1 - same_split
leakage_df = pd.DataFrame({"views_per_parent": descendants, "leakage_probability": leakage})
ax = sns.lineplot(data=leakage_df, x="views_per_parent", y="leakage_probability", marker="o", color="#d1495b")
ax.set_xscale("log", base=2); ax.set_ylim(-.02, 1.02); ax.set_title("Illustrative parent leakage under naive row-level splitting")
ax.set_ylabel("Probability a parent's views cross splits"); ax.set_xlabel("Generated views per parent")
plt.tight_layout(); plt.savefig(out_dir / "naive_split_leakage_probability.png", bbox_inches="tight"); plt.show()
display(leakage_df.assign(leakage_probability=lambda frame: frame.leakage_probability.round(8)))
display(Markdown("> This is a mathematical teaching illustration, not an observed leak in the released dataset. The release uses inherited parent splits."))''',
        ),
        _markdown("inspect-heading", "## 5. Inspect real lineage fields and transformation coverage"),
        _code(
            "lineage-sample",
            '''sample_decl = shard_index["supervised_train"][0]
sample_path = dataset_root / sample_decl["path"]
start = time.perf_counter()
sample = list(iter_jsonl(sample_path, limit=5000))
elapsed = time.perf_counter() - start
lineage = pd.DataFrame([{
    "id": row["id"],
    "parent_row_id": row["parent_row_id"],
    "parent_hash": row["parent_row_sha256"][:12],
    "lineage_family": row["parent_lineage_family_id"][:22],
    "task": row["curriculum_task"],
    "audience": row["audience"],
    "format": row["presentation_format"],
    "split": row["split"],
} for row in sample])
display(HTML(lineage.head(12).to_html(index=False, escape=True)))
display(Markdown(f"Streamed **{len(sample):,} rows** in **{elapsed:.2f} seconds** without loading every shard."))''',
        ),
        _code(
            "coverage-heatmap",
            '''cross = pd.crosstab(lineage["task"], lineage["audience"])
fig, ax = plt.subplots(figsize=(12, 7))
sns.heatmap(cross, cmap="crest", annot=True, fmt="d", linewidths=.4, ax=ax)
ax.set_title("Task by audience in a deterministic 5,000-row streaming sample")
ax.set_xlabel("Audience"); ax.set_ylabel("Review task")
plt.tight_layout(); plt.savefig(out_dir / "task_audience_sample_heatmap.png", bbox_inches="tight"); plt.show()''',
        ),
        _markdown("weights-heading", "## 6. A parent-capped weighting example"),
        _code(
            "weighting",
            '''family_sizes = lineage.groupby("parent_hash").size().rename("rows").reset_index()
family_sizes["naive_total_weight"] = family_sizes["rows"]
family_sizes["parent_capped_weight"] = 1.0
totals = pd.DataFrame({
    "strategy": ["Count every sampled row", "Cap aggregate weight at one per parent"],
    "total_weight": [family_sizes["naive_total_weight"].sum(), family_sizes["parent_capped_weight"].sum()],
})
ax = sns.barplot(data=totals, x="strategy", y="total_weight", hue="strategy", legend=False, palette=COLORS[:2])
ax.set_title("Illustrative training mass before and after a parent cap"); ax.tick_params(axis="x", rotation=10)
plt.tight_layout(); plt.savefig(out_dir / "parent_weight_cap.png", bbox_inches="tight"); plt.show()
display(family_sizes.describe().round(2))''',
        ),
        _markdown("finish-heading", "## 7. Export an auditable study summary"),
        _code(
            "finish",
            '''summary = {
    "dataset_id": DATASET_ID,
    "release_manifest_sha256": EXPECTED_RELEASE_SHA256,
    "control_artifacts_verified": int(check_df["present"].sum()),
    "sample_rows_streamed": len(sample),
    "sample_unique_parents": int(lineage["parent_hash"].nunique()),
    "supervised_views_per_training_parent": views,
    "actual_parent_split_overlap": 0,
    "naive_split_curve_is_illustrative": True,
    "charts": sorted(path.name for path in out_dir.glob("*.png")),
    "gpu_training_ran_in_this_notebook": False,
    "adapter_produced_in_this_notebook": False,
    "independent_model_lift_demonstrated": False,
}
(out_dir / "lineage-lab-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
display(Markdown(f"Saved **{len(summary['charts'])} charts** and `lineage-lab-summary.json`."))''',
        ),
    ]
    return _notebook(cells)


def _kernel_metadata(identifier: str, title: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "title": title,
        "code_file": "notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": False,
        "dataset_sources": [DATASET_ID],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }


def _execute_notebook(notebook_path: Path, dataset_root: Path) -> list[str]:
    import nbformat
    from nbclient import NotebookClient

    notebook = nbformat.read(notebook_path, as_version=4)
    local_output = notebook_path.parent / "local-output"
    local_output.mkdir()
    old_root = os.environ.get("DUECARE_MEASURED_CURRICULUM_ROOT")
    old_output = os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR")
    os.environ["DUECARE_MEASURED_CURRICULUM_ROOT"] = str(dataset_root)
    os.environ["DUECARE_NOTEBOOK_OUTPUT_DIR"] = str(local_output)
    try:
        client = NotebookClient(
            notebook,
            timeout=900,
            kernel_name="python3",
            resources={"metadata": {"path": str(notebook_path.parent)}},
        )
        client.execute()
    finally:
        if old_root is None:
            os.environ.pop("DUECARE_MEASURED_CURRICULUM_ROOT", None)
        else:
            os.environ["DUECARE_MEASURED_CURRICULUM_ROOT"] = old_root
        if old_output is None:
            os.environ.pop("DUECARE_NOTEBOOK_OUTPUT_DIR", None)
        else:
            os.environ["DUECARE_NOTEBOOK_OUTPUT_DIR"] = old_output
    nbformat.write(notebook, notebook_path.parent / "notebook.executed.ipynb")
    return [
        path.relative_to(notebook_path.parent).as_posix()
        for path in sorted(local_output.rglob("*"))
        if path.is_file()
    ]


def build_notebooks(
    collection: Path, output: Path, *, force: bool, execute_local: bool
) -> dict[str, Any]:
    dataset_root = collection.resolve(strict=True) / "dataset"
    release_path = dataset_root / "release-manifest.json"
    release = _read_json(release_path)
    if release.get("dataset_id") != DATASET_ID or release.get("safe_to_publish") is not True:
        raise ValueError("expected the approved public 200K measured curriculum")
    import hashlib

    release_sha = hashlib.sha256(release_path.read_bytes()).hexdigest()
    output = output.resolve()
    if output.exists():
        if not force:
            raise FileExistsError(f"output exists; use --force: {output}")
        if not (output / MARKER).is_file():
            raise ValueError(f"refusing to replace unowned output: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / MARKER).write_text("duecare.measured_curriculum_notebooks.v1\n", encoding="utf-8")

    specs = [
        ("curriculum_atlas", ATLAS_ID, "DueCare 200K Curriculum Visual Atlas", _atlas_notebook(release_sha)),
        ("lineage_lab", LINEAGE_ID, "DueCare 200K Lineage Split Laboratory", _lineage_notebook(release_sha)),
    ]
    records = []
    for directory, identifier, title, notebook in specs:
        root = output / directory
        root.mkdir()
        _write_json(root / "notebook.ipynb", notebook)
        _write_json(root / "kernel-metadata.json", _kernel_metadata(identifier, title))
        outputs = _execute_notebook(root / "notebook.ipynb", dataset_root) if execute_local else []
        records.append(
            {
                "id": identifier,
                "path": directory,
                "is_private": False,
                "accelerator": "central processing unit",
                "release_manifest_sha256": release_sha,
                "locally_executed": execute_local,
                "local_outputs": outputs,
            }
        )
    manifest = {
        "schema_version": "duecare.measured_curriculum_notebooks.v1",
        "dataset_id": DATASET_ID,
        "release_manifest_sha256": release_sha,
        "notebooks": records,
    }
    _write_json(output / "notebooks-manifest.json", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, default=DEFAULT_COLLECTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--execute-local", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_notebooks(
        args.collection,
        args.output,
        force=args.force,
        execute_local=args.execute_local,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
