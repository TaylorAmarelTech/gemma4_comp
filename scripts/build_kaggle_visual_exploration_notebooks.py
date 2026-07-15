# ruff: noqa: E501
"""Build reviewer-facing Kaggle visual exploration notebooks.

The release/integrity notebooks are intentionally strict and compact.  This
script adds richer Kaggle notebooks that make the staged training
datasets easy to inspect: row-count tables, charts, text-length summaries,
grade/lift plots, axis coverage, and non-training visual summaries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESPONSE_COLLECTION = ROOT / "reports" / "kaggle_publish" / "response_training_collection_v6"
DEFAULT_LARGE_COLLECTION = ROOT / "reports" / "kaggle_publish" / "large_training_collection_v4"
RESPONSE_EXPECTED_CHARTS = (
    "response_rows_by_lane.png",
    "response_split_balance.png",
    "response_score_distribution.png",
    "response_dimension_lift.png",
    "response_component_scores.png",
    "response_prompt_category_coverage.png",
    "response_teacher_models.png",
    "response_text_lengths.png",
    "response_reward_label_balance.png",
    "response_quarantine_reasons.png",
    "response_audit_population.png",
)
LARGE_EXPECTED_CHARTS = (
    "large_rows_by_lane.png",
    "large_storage_profile.png",
    "large_perspective_coverage.png",
    "large_journey_stage_coverage.png",
    "large_evidence_state_coverage.png",
    "large_temporal_lens_coverage.png",
    "large_view_mode_coverage.png",
    "large_jurisdiction_pattern_coverage.png",
    "large_prompt_family_coverage.png",
    "large_response_style_coverage.png",
    "large_controlled_failure_coverage.png",
    "large_perspective_journey_heatmap.png",
    "large_evidence_temporal_heatmap.png",
    "large_view_jurisdiction_heatmap.png",
    "large_text_lengths.png",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Mapping[str, Any] | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _artifact_index(root: Path, *, exclude: set[str]) -> dict[str, dict[str, Any]]:
    return {
        path.relative_to(root).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in exclude
    }


def _refresh_collection_manifests(
    *,
    response_collection: Path,
    large_collection: Path,
    response_release_sha: str,
    large_release_sha: str,
    response_public: bool,
    large_public: bool,
) -> dict[str, str]:
    response_path = response_collection / "collection-manifest.json"
    response = _read_json(response_path)
    if response.get("schema_version") != "duecare.kaggle.response-training-local-collection.v1":
        raise ValueError("measured-response collection manifest schema mismatch")
    response_safe_to_publish = response.get(
        "safe_to_publish", response.get("publication_ready")
    )
    if response_safe_to_publish is not response_public:
        raise ValueError("measured-response collection and release publication states differ")
    response["safe_to_publish"] = response_public
    response["artifacts"] = _artifact_index(
        response_collection,
        exclude={"collection-manifest.json"},
    )
    response_payload = dict(response)
    response_payload.pop("manifest_payload_sha256", None)
    response["manifest_payload_sha256"] = hashlib.sha256(
        json.dumps(response_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _write_json(response_path, response)

    large_path = large_collection / "collection-manifest.json"
    large = _read_json(large_path)
    if large.get("schema_version") != "duecare.kaggle.large_training_collection.v1":
        raise ValueError("multiperspective collection manifest schema mismatch")
    if large.get("safe_to_publish") is not large_public:
        raise ValueError("multiperspective collection and release publication states differ")
    notebooks = large.setdefault("notebooks", {})
    notebooks["visual_explorer"] = {
        "id": "taylorsamarel/duecare-large-corpus-visual-explorer",
        "path": "notebooks/visual_explorer",
        "published_accelerator": "cpu",
        "training_claimed": False,
        "release_manifest_sha256": large_release_sha,
        "expected_charts": list(LARGE_EXPECTED_CHARTS),
    }
    large["safe_to_train"] = True
    large["safe_to_publish"] = large_public
    _write_json(large_path, large)

    return {
        "response": _sha256_file(response_path),
        "large": _sha256_file(large_path),
        "response_release": response_release_sha,
        "large_release": large_release_sha,
    }


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


def _notebook(cells: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


COMMON_CODE = r'''
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import Markdown, display

pd.set_option("display.max_columns", 80)
pd.set_option("display.max_colwidth", 120)
plt.rcParams["figure.figsize"] = (10, 5)
plt.rcParams["axes.grid"] = True
plt.rcParams["figure.dpi"] = 110

DATASET_ID = %%DATASET_ID%%
EXPECTED_RELEASE_MANIFEST_SHA256 = %%RELEASE_SHA%%


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_root() -> Path:
    override = os.environ.get("DUECARE_DATASET_ROOT")
    candidates = []
    if override:
        root = Path(override)
        candidates.append(root / "release-manifest.json" if root.is_dir() else root)
    if Path("/kaggle/input").exists():
        candidates.extend(Path("/kaggle/input").rglob("release-manifest.json"))
    candidates.extend(Path.cwd().rglob("release-manifest.json"))

    matches = []
    for candidate in candidates:
        try:
            doc = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        if doc.get("dataset_id") == DATASET_ID:
            matches.append(candidate.parent)
    unique = []
    for item in matches:
        if item not in unique:
            unique.append(item)
    if len(unique) != 1:
        raise RuntimeError(f"Expected one mounted dataset root for {DATASET_ID}, found {len(unique)}: {unique[:5]}")
    return unique[0]


def working_dir() -> Path:
    kaggle_working = Path("/kaggle/working")
    in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
    root = kaggle_working if in_kaggle else Path.cwd() / "duecare_visual_outputs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def iter_jsonl(path: Path, limit: int | None = None):
    seen = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            yield json.loads(line)
            seen += 1
            if limit is not None and seen >= limit:
                return


def iter_lane(root: Path, index: dict, lane: str, limit: int | None = None):
    yielded = 0
    for shard in index["lanes"][lane]["shards"]:
        remaining = None if limit is None else max(limit - yielded, 0)
        if remaining == 0:
            return
        for row in iter_jsonl(root / shard["path"], remaining):
            yield row
            yielded += 1


root = find_root()
release = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
index = json.loads((root / "shard-index.json").read_text(encoding="utf-8"))
actual_release_sha = sha256_file(root / "release-manifest.json")
assert actual_release_sha == EXPECTED_RELEASE_MANIFEST_SHA256, (actual_release_sha, EXPECTED_RELEASE_MANIFEST_SHA256)

out_dir = working_dir()
display(Markdown(f"### Loaded `{DATASET_ID}` from `{root}`"))
display(
    pd.DataFrame(
        [
            {
                "dataset_id": release.get("dataset_id"),
                "release_id": release.get("release_id"),
                "publication_state": release.get("publication_state"),
                "safe_to_train": release.get("safe_to_train"),
                "safe_to_publish": release.get("safe_to_publish"),
                "release_manifest_sha256": actual_release_sha,
                "training_completed": (release.get("claims") or {}).get("training_completed", False),
                "adapter_produced": (release.get("claims") or {}).get("adapter_produced", False),
                "model_lift_demonstrated": (release.get("claims") or {}).get("model_lift_demonstrated", False),
            }
        ]
    )
)
overview_path = root / "dataset-overview.csv"
if overview_path.is_file():
    display(Markdown("### Reviewer data map"))
    display(pd.read_csv(overview_path).fillna(""))
'''


RESPONSE_EXPLORER_CODE = r'''
lane_rows = []
for lane, info in index["lanes"].items():
    lane_rows.append(
        {
            "lane": lane,
            "kind": info.get("kind"),
            "split": info.get("split"),
            "rows": info.get("rows", 0),
            "shards": len(info.get("shards", [])),
            "bytes_mb": round(sum(shard.get("bytes", 0) for shard in info.get("shards", [])) / 1_000_000, 2),
        }
    )
lane_df = pd.DataFrame(lane_rows).sort_values(["kind", "split", "lane"])
display(Markdown("### Lane inventory"))
display(lane_df)
lane_df.to_csv(out_dir / "response-lane-summary.csv", index=False)

plot_df = lane_df.sort_values("rows")
ax = plot_df.plot.barh(x="lane", y="rows", legend=False, color="#3867d6")
ax.set_title("Measured-response corpus rows by lane")
ax.set_xlabel("rows")
plt.tight_layout()
plt.savefig(out_dir / "response_rows_by_lane.png", dpi=140)
plt.show()

split_df = (
    lane_df[lane_df["split"].notna()]
    .pivot_table(index="split", columns="kind", values="rows", aggfunc="sum", fill_value=0)
    .reindex(["train", "validation", "test"])
    .fillna(0)
)
display(Markdown("### Train, validation, and test balance"))
display(split_df)
ax = split_df.plot.bar(color=["#20bf6b", "#3867d6", "#8854d0"][: len(split_df.columns)])
ax.set_title("Governed training and diagnostic rows by split")
ax.set_ylabel("rows")
ax.set_xlabel("split")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(out_dir / "response_split_balance.png", dpi=140)
plt.show()
'''


RESPONSE_QUALITY_CODE = r'''
sample_limit_by_lane = 5000
quality_rows = []
length_rows = []
reward_counts = Counter()
component_deltas = defaultdict(list)
component_targets = defaultdict(list)
component_baselines = defaultdict(list)

for lane in index["lanes"]:
    if not lane.startswith(("sft_positive_", "dpo_preference_", "reward_labels_")):
        continue
    for row in iter_lane(root, index, lane, sample_limit_by_lane):
        quality = row.get("quality_evidence") or {}
        baseline = quality.get("baseline_mean_score_0_100")
        target = quality.get("target_mean_score_0_100")
        lift = quality.get("score_lift")
        quality_rows.append(
            {
                "lane": lane,
                "split": row.get("split"),
                "id": row.get("id"),
                "prompt_category": row.get("prompt_category"),
                "difficulty": row.get("difficulty"),
                "teacher_model": row.get("teacher_model"),
                "baseline_score": baseline,
                "target_score": target,
                "score_lift": lift,
            }
        )
        for item in quality.get("failure_dimension_deltas", []):
            dimension = f"{item.get('dimension_id')}:{item.get('dimension')}"
            component_deltas[dimension].append(item.get("delta"))
        for key, value in (quality.get("baseline_components") or {}).items():
            component_baselines[key].append(value)
        for key, value in (quality.get("target_components") or {}).items():
            component_targets[key].append(value)

        if lane.startswith("sft_positive_"):
            assistant = [msg.get("content", "") for msg in row.get("messages", []) if msg.get("role") == "assistant"][-1]
            prompt = [msg.get("content", "") for msg in row.get("messages", []) if msg.get("role") == "user"][-1]
            length_rows.append({"lane": lane, "prompt_chars": len(prompt), "response_chars": len(assistant), "kind": "sft"})
        elif lane.startswith("dpo_preference_"):
            length_rows.append(
                {
                    "lane": lane,
                    "prompt_chars": len(row.get("prompt", "")),
                    "chosen_chars": len(row.get("chosen", "")),
                    "rejected_chars": len(row.get("rejected", "")),
                    "kind": "dpo",
                }
            )
        elif lane.startswith("reward_labels_"):
            reward_counts[str(row.get("label"))] += 1
            length_rows.append(
                {
                    "lane": lane,
                    "prompt_chars": len(row.get("prompt", "")),
                    "response_chars": len(row.get("response", "")),
                    "kind": f"reward_label_{row.get('label')}",
                }
            )

quality_df = pd.DataFrame(quality_rows)
length_df = pd.DataFrame(length_rows)
display(Markdown("### Accepted-row quality sample"))
display(quality_df.head(12))
display(quality_df[["baseline_score", "target_score", "score_lift"]].describe())
quality_df[["baseline_score", "target_score", "score_lift"]].describe().T.to_csv(
    out_dir / "response-quality-summary.csv"
)

score_plot = quality_df[["baseline_score", "target_score", "score_lift"]].dropna()
ax = score_plot.plot.hist(bins=24, alpha=0.58)
ax.set_title("Measured response score distribution")
ax.set_xlabel("score / lift")
plt.tight_layout()
plt.savefig(out_dir / "response_score_distribution.png", dpi=140)
plt.show()

delta_df = pd.DataFrame(
    [{"dimension": key, "mean_delta": pd.Series(values).dropna().mean()} for key, values in component_deltas.items()]
).sort_values("mean_delta")
delta_df.to_csv(out_dir / "response-dimension-lift.csv", index=False)
display(Markdown("### Mean score lift by grading dimension"))
display(delta_df)
ax = delta_df.plot.barh(x="dimension", y="mean_delta", legend=False, color="#20bf6b")
ax.set_title("Mean chosen-vs-baseline grade lift by dimension")
ax.set_xlabel("mean delta")
plt.tight_layout()
plt.savefig(out_dir / "response_dimension_lift.png", dpi=140)
plt.show()

component_rows = []
for component in sorted(set(component_baselines) | set(component_targets)):
    component_rows.append(
        {
            "component": component,
            "baseline_mean": pd.Series(component_baselines.get(component, [])).dropna().mean(),
            "chosen_mean": pd.Series(component_targets.get(component, [])).dropna().mean(),
        }
    )
component_df = pd.DataFrame(component_rows)
if not component_df.empty:
    component_df.to_csv(out_dir / "response-component-summary.csv", index=False)
    display(Markdown("### Mean bounded component scores"))
    display(component_df)
    ax = component_df.set_index("component")[["baseline_mean", "chosen_mean"]].plot.bar(
        color=["#eb3b5a", "#20bf6b"]
    )
    ax.set_title("Baseline vs chosen mean grading components")
    ax.set_ylabel("bounded component score")
    ax.set_xlabel("component")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(out_dir / "response_component_scores.png", dpi=140)
    plt.show()

category_counts = (
    quality_df["prompt_category"].fillna("unrecorded").astype(str).value_counts().head(15).rename_axis("prompt_category").reset_index(name="sampled_rows")
)
category_counts.to_csv(out_dir / "response-category-summary.csv", index=False)
display(Markdown("### Prompt-category coverage in accepted-row sample"))
display(category_counts)
if not category_counts.empty:
    ax = category_counts.sort_values("sampled_rows").plot.barh(
        x="prompt_category", y="sampled_rows", legend=False, color="#4b7bec"
    )
    ax.set_title("Accepted-row prompt-category coverage")
    ax.set_xlabel("sampled rows")
    plt.tight_layout()
    plt.savefig(out_dir / "response_prompt_category_coverage.png", dpi=140)
    plt.show()

teacher_counts = (
    quality_df["teacher_model"].fillna("unrecorded").astype(str).value_counts().rename_axis("teacher_model").reset_index(name="sampled_rows")
)
teacher_counts.to_csv(out_dir / "response-teacher-model-summary.csv", index=False)
display(Markdown("### Teacher-model provenance in accepted-row sample"))
display(teacher_counts)
if not teacher_counts.empty:
    ax = teacher_counts.sort_values("sampled_rows").plot.barh(
        x="teacher_model", y="sampled_rows", legend=False, color="#f7b731"
    )
    ax.set_title("Accepted-row teacher-model provenance")
    ax.set_xlabel("sampled rows")
    plt.tight_layout()
    plt.savefig(out_dir / "response_teacher_models.png", dpi=140)
    plt.show()

if not length_df.empty:
    display(Markdown("### Text length sample"))
    display(length_df.describe(include="all"))
    length_df.describe(include="all").T.to_csv(out_dir / "response-text-length-summary.csv")
    value_cols = [col for col in ["prompt_chars", "response_chars", "chosen_chars", "rejected_chars"] if col in length_df]
    ax = length_df[value_cols].plot.hist(bins=35, alpha=0.5)
    ax.set_title("Prompt/response text length distribution")
    ax.set_xlabel("characters")
    plt.tight_layout()
    plt.savefig(out_dir / "response_text_lengths.png", dpi=140)
    plt.show()

reward_df = pd.DataFrame([{"label": label, "rows": rows} for label, rows in sorted(reward_counts.items())])
if not reward_df.empty:
    reward_df.to_csv(out_dir / "response-reward-label-summary.csv", index=False)
    display(Markdown("### Reward-label balance in sampled rows"))
    display(reward_df)
    ax = reward_df.plot.bar(x="label", y="rows", legend=False, color="#8854d0")
    ax.set_title("Reward labels: positive vs negative")
    ax.set_xlabel("label")
    ax.set_ylabel("sampled rows")
    plt.tight_layout()
    plt.savefig(out_dir / "response_reward_label_balance.png", dpi=140)
    plt.show()
'''


RESPONSE_QUARANTINE_CODE = r'''
quarantine_rows = []
for lane in index["lanes"]:
    if lane != "quarantine":
        continue
    for row in iter_lane(root, index, lane, 10000):
        reason = row.get("reason") or row.get("rejection_reason") or row.get("quarantine_reason")
        if not reason and isinstance(row.get("reason_codes"), list):
            reason = "; ".join(map(str, row["reason_codes"][:3]))
        if not reason and isinstance(row.get("reasons"), list):
            reason = "; ".join(map(str, row["reasons"][:3]))
        quarantine_rows.append(
            {
                "id": row.get("id") or row.get("row_id"),
                "reason": reason or "unspecified",
                "schema": row.get("schema_family") or row.get("kind") or row.get("source_kind"),
                "contains_raw_text": row.get("contains_raw_text"),
            }
        )
quarantine_df = pd.DataFrame(quarantine_rows)
if not quarantine_df.empty:
    display(Markdown("### Quarantine summary sample"))
    display(quarantine_df.head(12))
    reason_counts = quarantine_df["reason"].value_counts().head(12).reset_index()
    reason_counts.columns = ["reason", "sampled_rows"]
    reason_counts.to_csv(out_dir / "response-quarantine-summary.csv", index=False)
    display(reason_counts)
    ax = reason_counts.sort_values("sampled_rows").plot.barh(x="reason", y="sampled_rows", legend=False, color="#eb3b5a")
    ax.set_title("Top quarantine reasons in sample")
    ax.set_xlabel("sampled rows")
    plt.tight_layout()
    plt.savefig(out_dir / "response_quarantine_reasons.png", dpi=140)
    plt.show()

audit_population = pd.DataFrame(
    [
        {"population": "source response inventory", "rows": int(lane_df.loc[lane_df["lane"] == "response_inventory", "rows"].sum())},
        {"population": "accepted positive supervised fine-tuning", "rows": int(lane_df.loc[lane_df["kind"] == "sft_positive", "rows"].sum())},
        {"population": "quarantined", "rows": int(lane_df.loc[lane_df["lane"] == "quarantine", "rows"].sum())},
    ]
)
audit_population.to_csv(out_dir / "response-audit-population.csv", index=False)
display(Markdown("### Audit population context (not a sequential funnel)"))
display(audit_population)
ax = audit_population.sort_values("rows").plot.barh(x="population", y="rows", legend=False, color="#2d98da")
ax.set_title("Source inventory, accepted supervised fine-tuning, and quarantine populations")
ax.set_xlabel("rows")
plt.tight_layout()
plt.savefig(out_dir / "response_audit_population.png", dpi=140)
plt.show()
'''


RESPONSE_SUMMARY_CODE = r'''
summary = {
    "schema_version": "duecare.kaggle.response_visual_explorer.v2",
    "dataset_id": DATASET_ID,
    "release_id": release.get("release_id"),
    "release_manifest_sha256": actual_release_sha,
    "publication_state": release.get("publication_state"),
    "safe_to_train": release.get("safe_to_train"),
    "safe_to_publish": release.get("safe_to_publish"),
    "lane_rows": lane_df.astype(object).where(pd.notnull(lane_df), None).to_dict(orient="records"),
    "sampled_quality_rows": int(len(quality_df)),
    "sampled_quarantine_rows": int(len(quarantine_df)) if "quarantine_df" in globals() else 0,
    "notebook_role": "kaggle_hackathon_learning_and_dataset_review",
    "sampling_note": "Charts summarize bounded samples for review; release manifests and shard indexes remain authoritative.",
    "training_completed": False,
    "adapter_produced": False,
    "model_lift_demonstrated": False,
    "charts": sorted(path.name for path in out_dir.glob("response_*.png")),
    "tables": sorted(path.name for path in out_dir.glob("response*.csv")),
}
(out_dir / "response-visual-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
report = f"""# DueCare measured-response visual review

- Dataset: `{DATASET_ID}`
- Release: `{release.get('release_id')}`
- Release manifest SHA-256: `{actual_release_sha}`
- Accepted-row sample: {len(quality_df):,}
- Quarantine sample: {len(quarantine_df) if 'quarantine_df' in globals() else 0:,}
- Charts written: {len(summary['charts'])}
- Training completed: false
- Adapter produced: false
- Independent model lift demonstrated: false

This is a Kaggle hackathon learning and review artifact. The source benchmark
influenced row selection, so it cannot be reused as independent improvement
evidence. See the dataset card and contamination ledger before training.
"""
(out_dir / "response-visual-report.md").write_text(report, encoding="utf-8")
display(Markdown("### Visual summary artifact"))
display(summary)
'''


LARGE_LANE_CODE = r'''
lane_rows = []
for lane, info in index["lanes"].items():
    lane_rows.append(
        {
            "lane": lane,
            "kind": info.get("kind"),
            "split": info.get("split"),
            "rows": info.get("rows", 0),
            "shards": len(info.get("shards", [])),
            "bytes_mb": round(sum(shard.get("bytes", 0) for shard in info.get("shards", [])) / 1_000_000, 2),
        }
    )
lane_df = pd.DataFrame(lane_rows).sort_values(["kind", "split", "lane"])
display(Markdown("### Lane inventory"))
display(lane_df)
ax = lane_df.sort_values("rows").plot.barh(x="lane", y="rows", legend=False, color="#3867d6")
ax.set_title("Large multiperspective corpus rows by lane")
ax.set_xlabel("rows")
plt.tight_layout()
plt.savefig(out_dir / "large_rows_by_lane.png", dpi=140)
plt.show()

lane_df.to_csv(out_dir / "large-lane-summary.csv", index=False)
size_df = lane_df[["lane", "rows", "bytes_mb"]].copy()
size_df["kb_per_row"] = (size_df["bytes_mb"] * 1000 / size_df["rows"]).round(2)
size_df.to_csv(out_dir / "large-size-summary.csv", index=False)
display(Markdown("### Storage and row-size profile"))
display(size_df)
ax = size_df.plot.scatter(x="rows", y="kb_per_row", s=90, color="#8854d0")
for _, item in size_df.iterrows():
    ax.annotate(item["lane"], (item["rows"], item["kb_per_row"]), xytext=(4, 4), textcoords="offset points")
ax.set_title("Rows and approximate storage per row by lane")
ax.set_xlabel("rows")
ax.set_ylabel("kilobytes per row")
plt.tight_layout()
plt.savefig(out_dir / "large_storage_profile.png", dpi=140)
plt.show()
'''


LARGE_AXIS_CODE = r'''
axis_keys = [
    "perspective",
    "journey_stage",
    "evidence_state",
    "temporal_lens",
    "view_mode",
    "jurisdiction_pattern",
    "prompt_family",
    "response_style",
    "controlled_failure",
]
sample_rows = []
axis_counts = {key: Counter() for key in axis_keys}
length_rows = []
sample_limit_by_lane = 7000

for lane in index["lanes"]:
    for row in iter_lane(root, index, lane, sample_limit_by_lane):
        sample_rows.append(
            {
                "lane": lane,
                "id": row.get("id"),
                "perspective": row.get("perspective"),
                "journey_stage": row.get("journey_stage"),
                "evidence_state": row.get("evidence_state"),
                "temporal_lens": row.get("temporal_lens"),
                "view_mode": row.get("view_mode"),
                "jurisdiction_pattern": row.get("jurisdiction_pattern"),
                "prompt_family": row.get("prompt_family"),
                "response_style": row.get("response_style"),
                "controlled_failure": row.get("controlled_failure"),
            }
        )
        for key in axis_keys:
            value = row.get(key)
            if value not in (None, ""):
                axis_counts[key][str(value)] += 1
        if "messages" in row:
            prompt = " ".join(msg.get("content", "") for msg in row.get("messages", []) if msg.get("role") == "user")
            assistant = " ".join(msg.get("content", "") for msg in row.get("messages", []) if msg.get("role") == "assistant")
            length_rows.append({"lane": lane, "prompt_chars": len(prompt), "answer_chars": len(assistant), "kind": "sft"})
        else:
            length_rows.append(
                {
                    "lane": lane,
                    "prompt_chars": len(row.get("prompt", "")),
                    "chosen_chars": len(row.get("chosen", "")),
                    "rejected_chars": len(row.get("rejected", "")),
                    "kind": "preference",
                }
            )

sample_df = pd.DataFrame(sample_rows)
length_df = pd.DataFrame(length_rows)
display(Markdown("### Sampled axis rows"))
display(sample_df.head(20))
display(Markdown(f"Sampled `{len(sample_df):,}` rows across lanes for visual coverage checks."))

axis_summary_rows = []
for key in axis_keys:
    rows = [{"value": value, "sampled_rows": count} for value, count in axis_counts[key].most_common(20)]
    if not rows:
        continue
    df = pd.DataFrame(rows)
    axis_summary_rows.extend({"axis": key, **row} for row in rows)
    display(Markdown(f"### `{key}` coverage"))
    display(df)
    ax = df.sort_values("sampled_rows").plot.barh(x="value", y="sampled_rows", legend=False)
    ax.set_title(f"{key} coverage in sampled rows")
    ax.set_xlabel("sampled rows")
    plt.tight_layout()
    plt.savefig(out_dir / f"large_{key}_coverage.png", dpi=140)
    plt.show()

axis_summary_df = pd.DataFrame(axis_summary_rows)
axis_summary_df.to_csv(out_dir / "large-axis-summary.csv", index=False)

def save_crosstab_heatmap(row_key, column_key, filename, title):
    frame = sample_df[[row_key, column_key]].dropna()
    if frame.empty:
        return None
    table = pd.crosstab(frame[row_key].astype(str), frame[column_key].astype(str))
    table.to_csv(out_dir / filename.replace(".png", ".csv"))
    fig_width = max(8, 0.9 * len(table.columns) + 4)
    fig_height = max(5, 0.55 * len(table.index) + 2)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    image = ax.imshow(table.values, aspect="auto", cmap="Blues")
    ax.set_xticks(range(len(table.columns)), labels=table.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(table.index)), labels=table.index)
    ax.set_xlabel(column_key)
    ax.set_ylabel(row_key)
    ax.set_title(title)
    ax.grid(False)
    fig.colorbar(image, ax=ax, label="sampled rows")
    plt.tight_layout()
    plt.savefig(out_dir / filename, dpi=140)
    plt.show()
    return table

display(Markdown("### Cross-axis balance heatmaps"))
perspective_journey = save_crosstab_heatmap(
    "perspective",
    "journey_stage",
    "large_perspective_journey_heatmap.png",
    "Perspective x journey-stage coverage",
)
evidence_temporal = save_crosstab_heatmap(
    "evidence_state",
    "temporal_lens",
    "large_evidence_temporal_heatmap.png",
    "Evidence-state x temporal-lens coverage",
)
view_jurisdiction = save_crosstab_heatmap(
    "view_mode",
    "jurisdiction_pattern",
    "large_view_jurisdiction_heatmap.png",
    "View-mode x jurisdiction-pattern coverage",
)

display(Markdown("### Text length sample"))
display(length_df.describe(include="all"))
length_df.describe(include="all").T.to_csv(out_dir / "large-text-length-summary.csv")
value_cols = [col for col in ["prompt_chars", "answer_chars", "chosen_chars", "rejected_chars"] if col in length_df]
ax = length_df[value_cols].plot.hist(bins=40, alpha=0.48)
ax.set_title("Large corpus prompt/answer length distribution")
ax.set_xlabel("characters")
plt.tight_layout()
plt.savefig(out_dir / "large_text_lengths.png", dpi=140)
plt.show()
'''


LARGE_SUMMARY_CODE = r'''
summary = {
    "schema_version": "duecare.kaggle.large_visual_explorer.v2",
    "dataset_id": DATASET_ID,
    "release_id": release.get("release_id"),
    "release_manifest_sha256": actual_release_sha,
    "publication_state": release.get("publication_state"),
    "safe_to_train": release.get("safe_to_train"),
    "safe_to_publish": release.get("safe_to_publish"),
    "lane_rows": lane_df.astype(object).where(pd.notnull(lane_df), None).to_dict(orient="records"),
    "sampled_rows": int(len(sample_df)),
    "axis_cardinality": {key: len(counter) for key, counter in axis_counts.items()},
    "notebook_role": "kaggle_hackathon_learning_and_dataset_review",
    "sampling_note": "Coverage charts use bounded lane samples; the release manifest, shard index, and quality audit remain authoritative.",
    "training_completed": False,
    "adapter_produced": False,
    "model_lift_demonstrated": False,
    "charts": sorted(path.name for path in out_dir.glob("large_*.png")),
    "tables": sorted(path.name for path in out_dir.glob("large*.csv")),
}
(out_dir / "large-visual-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
report = f"""# DueCare multiperspective corpus visual review

- Dataset: `{DATASET_ID}`
- Release: `{release.get('release_id')}`
- Release manifest SHA-256: `{actual_release_sha}`
- Sampled rows: {len(sample_df):,}
- Design axes profiled: {len(axis_counts)}
- Charts written: {len(summary['charts'])}
- Training completed: false
- Adapter produced: false
- Model lift demonstrated: false

This is a Kaggle hackathon learning and review artifact built from deterministic
synthetic case graphs. Coverage balance is a design property, not evidence of
real-world prevalence. See the dataset card and limitations before training.
"""
(out_dir / "large-visual-report.md").write_text(report, encoding="utf-8")
display(Markdown("### Visual summary artifact"))
display(summary)
'''


def _render_common(dataset_id: str, release_sha: str) -> str:
    return COMMON_CODE.replace("%%DATASET_ID%%", repr(dataset_id)).replace(
        "%%RELEASE_SHA%%", repr(release_sha)
    )


def _response_notebook(
    dataset_id: str, release_sha: str, *, public: bool
) -> dict[str, Any]:
    visibility = "public release" if public else "private candidate"
    return _notebook(
        [
            _markdown(
                "title",
                "# DueCare Measured Response Corpus: Kaggle Visual Explorer\n\n"
                f"**Gemma 4 Good Hackathon learning notebook · central processing unit (CPU) only · {visibility}**\n\n"
                "This reviewer-facing notebook verifies the exact release before loading rows, maps the "
                "supervised fine-tuning, Direct Preference Optimization, reward, and audit lanes; visualizes "
                "measured quality evidence and exclusions; and writes reusable Portable Network Graphics, "
                "comma-separated values, JavaScript Object Notation, and Markdown outputs. It uses visible rubric evidence, "
                "not hidden chain-of-thought. It does not train a model.",
            ),
            _markdown(
                "learning-route",
                "## Learning route\n\n"
                "1. Verify dataset identity and release hash.\n"
                "2. Understand which lanes can and cannot become training targets.\n"
                "3. Inspect score, component, category, model, reward, and text-length distributions.\n"
                "4. Review quarantine and contamination boundaries.\n"
                "5. Export a compact evidence bundle for later experiment planning.\n\n"
                "**Claim boundary:** no graphics processing unit training, adapter, independent lift result, or legal advice.",
            ),
            _markdown("verify", "## 1. Verify and identify the mounted dataset"),
            _code("setup", _render_common(dataset_id, release_sha)),
            _markdown("lanes", "## 2. Map the governed lanes and split balance"),
            _code("lane-inventory", RESPONSE_EXPLORER_CODE),
            _markdown("quality", "## 3. Explore accepted-row quality and provenance"),
            _code("quality-and-lengths", RESPONSE_QUALITY_CODE),
            _markdown("exclusions", "## 4. Understand exclusions and audit populations"),
            _code("quarantine", RESPONSE_QUARANTINE_CODE),
            _markdown("export", "## 5. Export the reviewer evidence bundle"),
            _code("summary", RESPONSE_SUMMARY_CODE),
        ]
    )


def _large_notebook(
    dataset_id: str, release_sha: str, *, public: bool
) -> dict[str, Any]:
    visibility = "public release" if public else "private candidate"
    return _notebook(
        [
            _markdown(
                "title",
                "# DueCare Multiperspective Corpus: Kaggle Visual Explorer\n\n"
                f"**Gemma 4 Good Hackathon learning notebook · central processing unit (CPU) only · {visibility}**\n\n"
                "This reviewer-facing notebook verifies the exact release, maps the supervised fine-tuning, preference, and holdout "
                "lanes, profiles persona, journey, evidence, temporal, jurisdiction, prompt, response, and "
                "controlled-failure axes, and writes reusable Portable Network Graphics, comma-separated "
                "values, JavaScript Object Notation, and Markdown outputs. Rows "
                "contain visible decision scaffolds—not hidden chain-of-thought or real worker cases. It "
                "does not train a model.",
            ),
            _markdown(
                "learning-route",
                "## Learning route\n\n"
                "1. Verify dataset identity and release hash.\n"
                "2. Inspect lane, shard, split, and storage structure.\n"
                "3. Measure single-axis and cross-axis synthetic coverage.\n"
                "4. Inspect prompt and answer length distributions.\n"
                "5. Export a compact evidence bundle for training and evaluation planning.\n\n"
                "**Claim boundary:** balanced synthetic coverage is not real-world prevalence; no graphics processing unit "
                "training, adapter, model lift, or legal advice is claimed.",
            ),
            _markdown("verify", "## 1. Verify and identify the mounted dataset"),
            _code("setup", _render_common(dataset_id, release_sha)),
            _markdown("lanes", "## 2. Map lanes, splits, shards, and storage"),
            _code("lane-inventory", LARGE_LANE_CODE),
            _markdown("coverage", "## 3. Explore single-axis and cross-axis coverage"),
            _code("axis-coverage", LARGE_AXIS_CODE),
            _markdown("export", "## 4. Export the reviewer evidence bundle"),
            _code("summary", LARGE_SUMMARY_CODE),
        ]
    )


def _write_notebook_dir(
    target: Path,
    *,
    notebook: dict[str, Any],
    notebook_id: str,
    title: str,
    dataset_id: str,
    is_private: bool,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    _write_json(target / "notebook.ipynb", notebook)
    _write_json(
        target / "kernel-metadata.json",
        {
            "id": notebook_id,
            "title": title,
            "code_file": "notebook.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": is_private,
            "enable_gpu": False,
            "enable_internet": False,
            "dataset_sources": [dataset_id],
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": [],
            "keywords": ["nlp"],
        },
    )


def _execute_notebook(path: Path, *, dataset_root: Path) -> None:
    import nbformat
    from nbclient import NotebookClient

    nb = nbformat.read(path, as_version=4)
    local_outputs = path.parent / "duecare_visual_outputs"
    if local_outputs.exists():
        if not local_outputs.is_dir() or local_outputs.is_symlink():
            raise ValueError("local visual-output path must be a normal directory")
        shutil.rmtree(local_outputs)
    old_root = os.environ.get("DUECARE_DATASET_ROOT")
    # Notebook kernels execute from the notebook directory, not the repository
    # root.  Use an absolute override so local execution exercises the same
    # discovery path regardless of the caller's working directory.
    os.environ["DUECARE_DATASET_ROOT"] = str(dataset_root.resolve())
    try:
        client = NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(path.parent)}})
        client.execute()
    finally:
        if old_root is None:
            os.environ.pop("DUECARE_DATASET_ROOT", None)
        else:
            os.environ["DUECARE_DATASET_ROOT"] = old_root
    nbformat.write(nb, path)


def build(
    *,
    response_collection: Path,
    large_collection: Path,
    execute_local: bool,
) -> dict[str, Any]:
    response_collection = response_collection.resolve()
    large_collection = large_collection.resolve()
    response_release = _read_json(response_collection / "dataset" / "release-manifest.json")
    large_release = _read_json(large_collection / "dataset" / "release-manifest.json")
    if response_release.get("safe_to_train") is not True:
        raise ValueError("measured-response release must explicitly set safe_to_train=true")
    if large_release.get("safe_to_train") is not True:
        raise ValueError("multiperspective release must explicitly set safe_to_train=true")
    response_dataset_id = response_release["dataset_id"]
    large_dataset_id = large_release["dataset_id"]
    response_public = response_release.get("safe_to_publish") is True
    large_public = large_release.get("safe_to_publish") is True
    response_release_sha = _sha256_file(response_collection / "dataset" / "release-manifest.json")
    large_release_sha = _sha256_file(large_collection / "dataset" / "release-manifest.json")

    response_dir = response_collection / "notebooks" / "visual_explorer"
    large_dir = large_collection / "notebooks" / "visual_explorer"
    _write_notebook_dir(
        response_dir,
        notebook=_response_notebook(
            response_dataset_id, response_release_sha, public=response_public
        ),
        notebook_id="taylorsamarel/duecare-response-dataset-visual-explorer",
        title="DueCare Response Dataset Visual Explorer",
        dataset_id=response_dataset_id,
        is_private=not response_public,
    )
    _write_notebook_dir(
        large_dir,
        notebook=_large_notebook(
            large_dataset_id, large_release_sha, public=large_public
        ),
        notebook_id="taylorsamarel/duecare-large-corpus-visual-explorer",
        title="DueCare Large Corpus Visual Explorer",
        dataset_id=large_dataset_id,
        is_private=not large_public,
    )

    if execute_local:
        _execute_notebook(response_dir / "notebook.ipynb", dataset_root=response_collection / "dataset")
        _execute_notebook(large_dir / "notebook.ipynb", dataset_root=large_collection / "dataset")
        execution_outputs = (
            (
                response_dir / "duecare_visual_outputs",
                (*RESPONSE_EXPECTED_CHARTS, "response-visual-summary.json", "response-visual-report.md"),
            ),
            (
                large_dir / "duecare_visual_outputs",
                (*LARGE_EXPECTED_CHARTS, "large-visual-summary.json", "large-visual-report.md"),
            ),
        )
        for output_dir, expected in execution_outputs:
            missing = [name for name in expected if not (output_dir / name).is_file()]
            if missing:
                raise ValueError(
                    f"local visual notebook execution did not create expected outputs: {missing}"
                )

    collection_manifest_sha256 = _refresh_collection_manifests(
        response_collection=response_collection,
        large_collection=large_collection,
        response_release_sha=response_release_sha,
        large_release_sha=large_release_sha,
        response_public=response_public,
        large_public=large_public,
    )

    manifest = {
        "schema_version": "duecare.kaggle.visual_notebooks.v2",
        "notebooks": {
            "response_visual_explorer": {
                "id": "taylorsamarel/duecare-response-dataset-visual-explorer",
                "path": str(response_dir.relative_to(ROOT)),
                "dataset_id": response_dataset_id,
                "release_manifest_sha256": response_release_sha,
                "collection_manifest_sha256": collection_manifest_sha256["response"],
                "is_private": not response_public,
                "executed_local": execute_local,
                "expected_charts": list(RESPONSE_EXPECTED_CHARTS),
                "summary_artifact": "response-visual-summary.json",
                "report_artifact": "response-visual-report.md",
            },
            "large_visual_explorer": {
                "id": "taylorsamarel/duecare-large-corpus-visual-explorer",
                "path": str(large_dir.relative_to(ROOT)),
                "dataset_id": large_dataset_id,
                "release_manifest_sha256": large_release_sha,
                "collection_manifest_sha256": collection_manifest_sha256["large"],
                "is_private": not large_public,
                "executed_local": execute_local,
                "expected_charts": list(LARGE_EXPECTED_CHARTS),
                "summary_artifact": "large-visual-summary.json",
                "report_artifact": "large-visual-report.md",
            },
        },
        "notebook_role": "kaggle_hackathon_learning_and_dataset_review",
        "training_completed": False,
        "adapter_produced": False,
        "model_lift_demonstrated": False,
    }
    _write_json(ROOT / "reports" / "kaggle_publish" / "visual_notebooks_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response-collection", type=Path, default=DEFAULT_RESPONSE_COLLECTION)
    parser.add_argument("--large-collection", type=Path, default=DEFAULT_LARGE_COLLECTION)
    parser.add_argument("--execute-local", action="store_true")
    args = parser.parse_args()
    manifest = build(
        response_collection=args.response_collection,
        large_collection=args.large_collection,
        execute_local=args.execute_local,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
