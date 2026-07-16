#!/usr/bin/env python3
# ruff: noqa: E501
"""Build a 200,000+ row review curriculum from measured response pairs.

This builder does not pretend that deterministic descendants are independent
human judgments.  It starts from a manifest-approved measured-response release,
inherits each parent's split and lineage, and turns the response into bounded
review tasks across task, audience, and presentation axes.  Every descendant
declares its parent, transformation, and non-independence.

The generated targets are visible review briefs, not hidden chain of thought.
They teach evidence comparison, uncertainty, audience boundaries, calibration,
and publication-claim discipline.  They never promote the source benchmark as
independent evidence of model improvement or as a legal finding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, BinaryIO

ROOT = Path(__file__).resolve().parents[1]
CHAT_SRC = ROOT / "packages" / "duecare-llm-chat" / "src"
if str(CHAT_SRC) not in sys.path:
    sys.path.insert(0, str(CHAT_SRC))

from duecare.chat.training_contract import (  # noqa: E402
    canonical_sha256,
    pii_findings,
    training_row_sha256,
)

DEFAULT_SOURCE_RELEASE = (
    ROOT
    / "reports"
    / "kaggle_publish"
    / "response_training_collection_v6"
    / "dataset"
    / "release-manifest.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "response_preference_candidates"
    / "large_review_curriculum_v1"
)
DEFAULT_TRAIN_VIEWS_PER_PARENT = 320
DEFAULT_HELDOUT_VIEWS_PER_PARENT = 8
DEFAULT_SHARD_ROWS = 4_096
DEFAULT_MINIMUM_TRAIN_ROWS = 200_000
GENERATOR_VERSION = "duecare-measured-response-review-curriculum/1.0.0"
SCHEMA_VERSION = "duecare.measured_response.review_curriculum_candidate.v1"
CREATED_AT = "2026-07-15T00:00:00+00:00"
ROW_LICENSE = "CC-BY-4.0"


REVIEW_TASKS: tuple[dict[str, str], ...] = (
    {
        "key": "evidence_grounding",
        "label": "evidence grounding",
        "dimension": "A",
        "instruction": "separate directly supported observations, response inferences, counterevidence, and information that still requires retrieval",
    },
    {
        "key": "legal_applicability",
        "label": "legal applicability",
        "dimension": "B",
        "instruction": "distinguish stable indicators from jurisdiction-specific authority and require current primary-source retrieval for mutable law",
    },
    {
        "key": "protective_refusal",
        "label": "protective refusal and redirection",
        "dimension": "C",
        "instruction": "check whether harmful operational guidance was refused while a safe and useful alternative remained available",
    },
    {
        "key": "concrete_actions",
        "label": "concrete and proportional actions",
        "dimension": "D",
        "instruction": "check whether proposed steps are specific, reversible, exposure-aware, and bounded by authority and consent",
    },
    {
        "key": "safety_privacy",
        "label": "safety and privacy",
        "dimension": "E",
        "instruction": "identify privacy, retaliation, disclosure, and high-impact-action risks without turning concern into an accusation",
    },
    {
        "key": "score_calibration",
        "label": "score calibration",
        "dimension": "overall",
        "instruction": "interpret bounded scores and lift as experiment-local measurements rather than probabilities, prevalence estimates, or proof",
    },
    {
        "key": "contrastive_comparison",
        "label": "contrastive comparison",
        "dimension": "overall",
        "instruction": "explain why the selected response was preferred using declared rubric deltas while avoiding style, length, or model-family shortcuts",
    },
    {
        "key": "uncertainty_boundary",
        "label": "uncertainty and abstention boundary",
        "dimension": "overall",
        "instruction": "name what the response establishes, what it does not establish, and what missing evidence should trigger abstention or review",
    },
    {
        "key": "audience_handoff",
        "label": "audience and authority handoff",
        "dimension": "overall",
        "instruction": "adapt the review to the audience while preserving the worker's decision authority and every source limitation",
    },
    {
        "key": "publication_claim_audit",
        "label": "publication claim audit",
        "dimension": "overall",
        "instruction": "separate a reusable training candidate from an independent evaluation result, trained adapter, demonstrated lift, or production claim",
    },
)

AUDIENCES: tuple[dict[str, str], ...] = (
    {"key": "worker", "label": "worker", "boundary": "use plain language, preserve choice, and do not force disclosure or escalation"},
    {"key": "newly_arrived_worker", "label": "newly arrived worker", "boundary": "explain unfamiliar actors without assuming local-system knowledge"},
    {"key": "third_party_observer", "label": "third-party observer", "boundary": "separate direct observation from hearsay and do not act for the worker"},
    {"key": "ngo_caseworker", "label": "non-governmental organization caseworker", "boundary": "support and triage without adjudicating facts or promising an outcome"},
    {"key": "origin_country_official", "label": "origin-country official", "boundary": "limit conclusions to origin-side authority and preserve destination-side provenance"},
    {"key": "destination_regulator", "label": "destination-country regulator", "boundary": "limit conclusions to authorized fact finding and retain cross-border evidence"},
    {"key": "legal_scholar", "label": "legal scholar", "boundary": "map issues and dated authority without acting as counsel or fact finder"},
    {"key": "independent_reviewer", "label": "independent technical reviewer", "boundary": "audit reproducibility, contamination, calibration, and claim scope"},
)

PRESENTATION_FORMATS: tuple[dict[str, str], ...] = (
    {"key": "sectioned_memo", "label": "sectioned memo"},
    {"key": "compact_checklist", "label": "compact checklist"},
    {"key": "structured_record", "label": "structured record"},
    {"key": "teaching_note", "label": "teaching note"},
)

TASK_BY_KEY = {row["key"]: row for row in REVIEW_TASKS}
AUDIENCE_BY_KEY = {row["key"]: row for row in AUDIENCES}
FORMAT_BY_KEY = {row["key"]: row for row in PRESENTATION_FORMATS}
VIEW_COMBINATIONS = tuple(
    (task["key"], audience["key"], presentation["key"])
    for task in REVIEW_TASKS
    for audience in AUDIENCES
    for presentation in PRESENTATION_FORMATS
)


class CurriculumError(ValueError):
    """Raised when a source or generated release fails closed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CurriculumError(f"{label} is not readable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CurriculumError(f"{label} must be a JSON object: {path}")
    return value


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CurriculumError(f"invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise CurriculumError(f"row must be an object at {path}:{line_number}")
            yield row


def _verify_source(release_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    release_path = release_path.resolve(strict=True)
    root = release_path.parent
    release = _read_object(release_path, label="source release manifest")
    shard_index = _read_object(root / "shard-index.json", label="source shard index")
    if release.get("safe_to_train") is not True or release.get("safe_to_publish") is not True:
        raise CurriculumError("source release must be approved for training and public redistribution")
    if release.get("publication_state") != "approved_public_ready":
        raise CurriculumError("source release is not in approved_public_ready state")
    approval = release.get("publication_approval") or {}
    approvals = approval.get("approvals") or {}
    if not all(
        approvals.get(key) is True
        for key in ("curator_approved", "privacy_approved", "license_approved", "public_redistribution_approved")
    ):
        raise CurriculumError("source release approval is incomplete")
    lanes = shard_index.get("lanes") or {}
    for required in (
        "sft_positive_train",
        "sft_positive_validation",
        "sft_positive_test",
        "dpo_preference_train",
        "dpo_preference_validation",
        "dpo_preference_test",
    ):
        if required not in lanes:
            raise CurriculumError(f"source shard index is missing {required}")
        observed = 0
        for declaration in lanes[required].get("shards") or []:
            path = (root / str(declaration.get("path") or "")).resolve(strict=True)
            if root not in path.parents:
                raise CurriculumError(f"source shard escapes release root: {path}")
            if _sha256_file(path) != declaration.get("sha256"):
                raise CurriculumError(f"source shard hash mismatch: {path.name}")
            if path.stat().st_size != declaration.get("bytes"):
                raise CurriculumError(f"source shard size mismatch: {path.name}")
            rows = sum(1 for _ in _iter_jsonl(path))
            if rows != declaration.get("rows"):
                raise CurriculumError(f"source shard row-count mismatch: {path.name}")
            observed += rows
        if observed != lanes[required].get("rows"):
            raise CurriculumError(f"source lane row-count mismatch: {required}")
    return release, shard_index


def _lane_rows(root: Path, shard_index: Mapping[str, Any], lane: str) -> Iterable[dict[str, Any]]:
    declaration = (shard_index.get("lanes") or {})[lane]
    for shard in declaration.get("shards") or []:
        yield from _iter_jsonl(root / str(shard["path"]))


def _parent_rows(
    root: Path, shard_index: Mapping[str, Any], split: str
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    sft = list(_lane_rows(root, shard_index, f"sft_positive_{split}"))

    def pair_key(row: Mapping[str, Any]) -> str:
        prompt_sha = str(
            row.get("training_prompt_sha256")
            or row.get("source_prompt_sha256")
            or ""
        )
        responses = row.get("training_response_sha256") or row.get(
            "source_response_sha256"
        )
        chosen_sha = ""
        if isinstance(responses, Mapping):
            chosen_sha = str(responses.get("chosen") or responses.get("teacher") or "")
        if prompt_sha and chosen_sha:
            return f"response-pair-hash:{prompt_sha}:{chosen_sha}"
        lineage = str(row.get("lineage_id") or "")
        if lineage and ":" in lineage:
            return lineage.rsplit(":", 1)[0]
        row_id = str(row.get("id") or "")
        return row_id.replace("rsp-sft-", "rsp-pair-").replace(
            "rsp-dpo-", "rsp-pair-"
        )

    preferences = {
        pair_key(row): row
        for row in _lane_rows(root, shard_index, f"dpo_preference_{split}")
    }
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in sft:
        row_id = str(row.get("id") or "")
        preference = preferences.get(pair_key(row))
        if not preference:
            raise CurriculumError(f"missing source preference parent for {split}:{row_id}")
        if row.get("split") != split or preference.get("split") != split:
            raise CurriculumError(f"source split mismatch for {split}:{row_id}")
        if (row.get("quality_gate") or {}).get("accepted") is not True:
            raise CurriculumError(f"source parent did not pass its quality gate: {row_id}")
        if row.get("pii_checked") is not True or pii_findings(row):
            raise CurriculumError(f"source parent failed privacy verification: {row_id}")
        pairs.append((row, preference))
    if len(pairs) != len(preferences):
        raise CurriculumError(f"source parent lane mismatch for {split}")
    return sorted(pairs, key=lambda pair: str(pair[0]["id"]))


def _messages(row: Mapping[str, Any]) -> tuple[str, str]:
    messages = row.get("messages") or []
    user = [str(item.get("content") or "") for item in messages if item.get("role") == "user"]
    assistant = [str(item.get("content") or "") for item in messages if item.get("role") == "assistant"]
    if len(user) != 1 or len(assistant) != 1 or not user[0].strip() or not assistant[0].strip():
        raise CurriculumError(f"source row has invalid messages: {row.get('id')}")
    return user[0], assistant[0]


def _number(value: Any, default: float = 0.0) -> float:
    return round(float(value if value is not None else default), 1)


def _review_payload(
    parent: Mapping[str, Any], task_key: str, audience_key: str, format_key: str
) -> dict[str, Any]:
    task = TASK_BY_KEY[task_key]
    audience = AUDIENCE_BY_KEY[audience_key]
    evidence = parent.get("quality_evidence") or {}
    baseline_components = evidence.get("baseline_components") or {}
    target_components = evidence.get("target_components") or {}
    dimension = task["dimension"]
    if dimension == "overall":
        baseline = _number(evidence.get("baseline_mean_score_0_100"))
        target = _number(evidence.get("target_mean_score_0_100"))
    else:
        baseline = _number(baseline_components.get(dimension))
        target = _number(target_components.get(dimension))
    return {
        "review_task": task["label"],
        "audience": audience["label"],
        "audience_boundary": audience["boundary"],
        "presentation_format": FORMAT_BY_KEY[format_key]["label"],
        "measured_baseline": baseline,
        "measured_selected": target,
        "measured_delta": round(target - baseline, 1),
        "overall_baseline": _number(evidence.get("baseline_mean_score_0_100")),
        "overall_selected": _number(evidence.get("target_mean_score_0_100")),
        "overall_lift": _number(evidence.get("score_lift")),
        "review_method": task["instruction"],
        "claim_boundary": "The measurements describe one manifest-bound response pair. They are not a legal finding, a prevalence estimate, or independent proof that a trained model improved.",
        "next_review_step": "Preserve the parent and source hashes, keep all descendants in the inherited split, and route consequential ambiguity to blinded human review.",
        "parent_record": str(parent.get("id") or ""),
    }


def _render_target(payload: Mapping[str, Any], format_key: str) -> str:
    if format_key == "structured_record":
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    if format_key == "compact_checklist":
        return "\n".join(
            (
                f"Review task: {payload['review_task']}",
                f"Audience: {payload['audience']}",
                f"- Boundary: {payload['audience_boundary']}",
                f"- Measured comparison: {payload['measured_baseline']} -> {payload['measured_selected']} (delta {payload['measured_delta']:+.1f}); overall lift {payload['overall_lift']:+.1f}.",
                f"- Method: {payload['review_method']}.",
                f"- Claim limit: {payload['claim_boundary']}",
                f"- Next review step: {payload['next_review_step']}",
                f"- Parent record: {payload['parent_record']}",
            )
        )
    if format_key == "teaching_note":
        return (
            f"Teaching note for a {payload['audience']}: This example practices {payload['review_task']}. "
            f"The audience boundary is to {payload['audience_boundary']}. The relevant measured comparison is "
            f"{payload['measured_baseline']} to {payload['measured_selected']} (delta {payload['measured_delta']:+.1f}), "
            f"while the overall experiment-local lift is {payload['overall_lift']:+.1f}. Reviewers should {payload['review_method']}. "
            f"{payload['claim_boundary']} {payload['next_review_step']} Parent record: {payload['parent_record']}."
        )
    return "\n\n".join(
        (
            f"Review purpose: {payload['review_task']}",
            f"Audience and authority: Write for the {payload['audience']}; {payload['audience_boundary']}.",
            f"Measured evidence: The bounded comparison is {payload['measured_baseline']} to {payload['measured_selected']} (delta {payload['measured_delta']:+.1f}). The overall pair-level lift is {payload['overall_lift']:+.1f}.",
            f"Review method: {payload['review_method']}.",
            f"Claim boundary: {payload['claim_boundary']}",
            f"Review handoff: {payload['next_review_step']} Parent record: {payload['parent_record']}.",
        )
    )


def _render_rejected(chosen: str, defect_index: int) -> tuple[str, str]:
    defects = (
        (
            "independent_lift_overclaim",
            "Treat the score increase as independent proof that the underlying model improved and generalize it beyond this response pair.",
        ),
        (
            "legal_finding_overclaim",
            "Treat the selected response and its score as sufficient to establish the legal status of any person described by the prompt.",
        ),
        (
            "dimension_collapse",
            "Replace the separate rubric dimensions with one overall trust judgment and omit disagreement, uncertainty, and missing evidence.",
        ),
        (
            "authority_boundary_removed",
            "Let the named audience decide the cross-jurisdiction action and disclosure path without separate authority or consent checks.",
        ),
    )
    defect, sentence = defects[defect_index % len(defects)]
    rejected = f"{chosen}\n\nUnsupported conclusion: {sentence}"
    return rejected, defect


def _view_prompt(
    parent: Mapping[str, Any], task_key: str, audience_key: str, format_key: str
) -> str:
    source_prompt, source_response = _messages(parent)
    task = TASK_BY_KEY[task_key]
    audience = AUDIENCE_BY_KEY[audience_key]
    presentation = FORMAT_BY_KEY[format_key]
    return (
        "Review the following manifest-bound prompt and selected response. Use only the visible response and the supplied measured metadata; do not invent facts or claim hidden reasoning.\n\n"
        f"Original prompt:\n{source_prompt}\n\nSelected response:\n{source_response}\n\n"
        f"Review task: {task['label']}\nAudience: {audience['label']}\nAudience boundary: {audience['boundary']}\n"
        f"Requested presentation: {presentation['label']}\n"
        "Return an auditable review that keeps response quality, legal findings, and model-improvement claims separate."
    )


def _common_fields(
    parent: Mapping[str, Any], task_key: str, audience_key: str, format_key: str
) -> dict[str, Any]:
    view_key = f"{task_key}|{audience_key}|{format_key}"
    parent_sha = str(parent.get("sha256") or training_row_sha256(parent))
    row_key = f"{parent_sha}|{view_key}"
    return {
        "id": f"mrc-{canonical_sha256(row_key)[:24]}",
        "split": str(parent["split"]),
        "synthetic": True,
        "synthetic_augmentation": True,
        "independent_observation": False,
        "augmentation_depth": 1,
        "parent_row_id": str(parent.get("id") or ""),
        "parent_row_sha256": parent_sha,
        "parent_lineage_family_id": str(parent.get("lineage_family_id") or ""),
        "group_weight_key": str(parent.get("lineage_family_id") or parent_sha),
        "transformation_id": f"review-curriculum:{view_key}:v1",
        "transformation_type": "measured_response_review_task_recomposition",
        "curriculum_task": task_key,
        "audience": audience_key,
        "presentation_format": format_key,
        "generator_version": GENERATOR_VERSION,
        "created_at": CREATED_AT,
        "license": ROW_LICENSE,
        "rights_holder": "DueCare project contributors",
        "allow_training_use": True,
        "allow_public_redistribution": False,
        "publication_approval_required": True,
        "pii_checked": True,
        "reasoning_data_policy": "visible review brief and final answer only; no provider-private reasoning or hidden chain of thought",
        "source_response_sha256": parent.get("source_response_sha256"),
        "source_quality_evidence_sha256": parent.get("quality_evidence_sha256"),
        "source_refs": parent.get("source_refs") or [],
    }


def _curriculum_rows(
    parent: Mapping[str, Any], task_key: str, audience_key: str, format_key: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    prompt = _view_prompt(parent, task_key, audience_key, format_key)
    payload = _review_payload(parent, task_key, audience_key, format_key)
    chosen = _render_target(payload, format_key)
    common = _common_fields(parent, task_key, audience_key, format_key)
    source_gate = (parent.get("quality_gate") or {}).get("accepted") is True
    checks = {
        "source_quality_gate_passed": source_gate,
        "parent_lineage_declared": bool(common["parent_row_sha256"] and common["parent_lineage_family_id"]),
        "split_inherited": common["split"] == parent.get("split"),
        "task_axis_declared": task_key in TASK_BY_KEY,
        "audience_axis_declared": audience_key in AUDIENCE_BY_KEY,
        "format_axis_declared": format_key in FORMAT_BY_KEY,
        "claim_boundary_present": "not a legal finding" in chosen and "independent proof" in chosen,
        "hidden_reasoning_not_requested": "claim hidden reasoning" in prompt,
    }
    quality_gate = {
        "accepted": all(checks.values()),
        "unsafe_advice_filtered": all(checks.values()),
        "judge": "duecare-measured-review-curriculum-contract-v1",
        "checks": checks,
    }
    supervised: dict[str, Any] = {
        **common,
        "messages": [
            {
                "role": "system",
                "content": "Produce a concise, auditable review from visible evidence and bounded metadata. Separate observations, inferences, legal findings, and publication claims.",
            },
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": chosen},
        ],
        "quality_gate": quality_gate,
    }
    supervised["sha256"] = training_row_sha256(supervised)
    defect_index = int(canonical_sha256(common["id"])[0:8], 16)
    rejected, defect = _render_rejected(chosen, defect_index)
    preference: dict[str, Any] = {
        **common,
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
        "controlled_failure": defect,
        "negative_only": True,
        "assistant_target_allowed": False,
        "preference_rationale": {
            "preferred": "keeps experiment-local measurements, legal findings, and independent model-improvement claims separate",
            "rejected_defect": defect,
            "visible_rationale_only": True,
        },
        "quality_gate": quality_gate,
    }
    preference["sha256"] = training_row_sha256(preference)
    return supervised, preference


class ShardWriter:
    def __init__(self, root: Path, lane: str, total_rows: int, shard_rows: int) -> None:
        self.root = root
        self.lane = lane
        self.total_rows = total_rows
        self.shard_rows = shard_rows
        self.total_shards = math.ceil(total_rows / shard_rows)
        self.global_rows = 0
        self.shard_index = 0
        self.shard_count = 0
        self.handle: BinaryIO | None = None
        self.path: Path | None = None
        self.digest: Any = None
        self.bytes_written = 0
        self.artifacts: list[dict[str, Any]] = []

    def _open(self) -> None:
        self.path = self.root / f"{self.lane}-{self.shard_index:05d}-of-{self.total_shards:05d}.jsonl"
        self.handle = self.path.open("xb")
        self.digest = hashlib.sha256()
        self.shard_count = 0
        self.bytes_written = 0

    def _close(self) -> None:
        if not self.handle or not self.path:
            return
        self.handle.close()
        self.artifacts.append(
            {
                "path": self.path.name,
                "rows": self.shard_count,
                "bytes": self.bytes_written,
                "sha256": self.digest.hexdigest(),
            }
        )
        self.handle = None
        self.path = None
        self.digest = None
        self.shard_index += 1

    def write(self, row: Mapping[str, Any]) -> None:
        if self.handle is None:
            self._open()
        payload = _json_bytes(row)
        assert self.handle is not None and self.digest is not None
        self.handle.write(payload)
        self.digest.update(payload)
        self.shard_count += 1
        self.global_rows += 1
        self.bytes_written += len(payload)
        if self.shard_count == self.shard_rows:
            self._close()

    def close(self) -> list[dict[str, Any]]:
        self._close()
        if self.global_rows != self.total_rows:
            raise CurriculumError(f"{self.lane}: wrote {self.global_rows}, expected {self.total_rows}")
        return list(self.artifacts)


def _selected_views(parent_id: str, limit: int) -> list[tuple[str, str, str]]:
    if limit <= 0 or limit > len(VIEW_COMBINATIONS):
        raise CurriculumError(f"view limit must be between 1 and {len(VIEW_COMBINATIONS)}")
    ranked = sorted(
        VIEW_COMBINATIONS,
        key=lambda view: canonical_sha256(f"{parent_id}|{'|'.join(view)}"),
    )
    return ranked[:limit]


def build_plan(
    release_path: Path,
    *,
    train_views_per_parent: int = DEFAULT_TRAIN_VIEWS_PER_PARENT,
    heldout_views_per_parent: int = DEFAULT_HELDOUT_VIEWS_PER_PARENT,
    shard_rows: int = DEFAULT_SHARD_ROWS,
) -> dict[str, Any]:
    release, shard_index = _verify_source(release_path)
    lanes = shard_index["lanes"]
    parents = {
        split: int(lanes[f"sft_positive_{split}"]["rows"])
        for split in ("train", "validation", "test")
    }
    counts = {
        "supervised_train": parents["train"] * train_views_per_parent,
        "preference_train": parents["train"] * train_views_per_parent,
        "supervised_validation": parents["validation"] * heldout_views_per_parent,
        "supervised_test": parents["test"] * heldout_views_per_parent,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "plan_only_no_files_written",
        "source_dataset_id": release.get("dataset_id"),
        "source_release_manifest_sha256": _sha256_file(release_path),
        "parent_counts": parents,
        "view_matrix": {
            "review_tasks": len(REVIEW_TASKS),
            "audiences": len(AUDIENCES),
            "presentation_formats": len(PRESENTATION_FORMATS),
            "total_combinations": len(VIEW_COMBINATIONS),
        },
        "train_views_per_parent": train_views_per_parent,
        "heldout_views_per_parent": heldout_views_per_parent,
        "counts": counts,
        "shards": {lane: math.ceil(rows / shard_rows) for lane, rows in counts.items()},
        "independence_warning": "Rows are deterministic descendants of measured parents, not independent human judgments; group by parent_row_sha256 or parent_lineage_family_id.",
    }


def build_candidate(
    release_path: Path,
    output_dir: Path,
    *,
    train_views_per_parent: int = DEFAULT_TRAIN_VIEWS_PER_PARENT,
    heldout_views_per_parent: int = DEFAULT_HELDOUT_VIEWS_PER_PARENT,
    shard_rows: int = DEFAULT_SHARD_ROWS,
    minimum_train_rows: int = DEFAULT_MINIMUM_TRAIN_ROWS,
) -> dict[str, Any]:
    plan = build_plan(
        release_path,
        train_views_per_parent=train_views_per_parent,
        heldout_views_per_parent=heldout_views_per_parent,
        shard_rows=shard_rows,
    )
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"candidate output must not already exist: {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        release_path = release_path.resolve(strict=True)
        root = release_path.parent
        release, shard_index = _verify_source(release_path)
        parents = {
            split: _parent_rows(root, shard_index, split)
            for split in ("train", "validation", "test")
        }
        writers = {
            lane: ShardWriter(output_dir, lane, count, shard_rows)
            for lane, count in plan["counts"].items()
        }
        seen_ids: set[str] = set()
        axis_counts: dict[str, Counter[str]] = defaultdict(Counter)
        parent_families: dict[str, set[str]] = defaultdict(set)
        quality_failures = 0
        pii_failures = 0
        controlled_failures: Counter[str] = Counter()

        for split in ("validation", "test", "train"):
            view_limit = train_views_per_parent if split == "train" else heldout_views_per_parent
            for parent, _source_preference in parents[split]:
                parent_families[split].add(str(parent.get("lineage_family_id") or ""))
                views = _selected_views(str(parent.get("id") or ""), view_limit)
                for task_key, audience_key, format_key in views:
                    supervised, preference = _curriculum_rows(parent, task_key, audience_key, format_key)
                    if supervised["id"] in seen_ids:
                        raise CurriculumError(f"duplicate generated row id: {supervised['id']}")
                    seen_ids.add(str(supervised["id"]))
                    if supervised["sha256"] != training_row_sha256(supervised):
                        raise CurriculumError(f"supervised row hash drift: {supervised['id']}")
                    if preference["sha256"] != training_row_sha256(preference):
                        raise CurriculumError(f"preference row hash drift: {preference['id']}")
                    quality_failures += int((supervised.get("quality_gate") or {}).get("accepted") is not True)
                    pii_failures += int(bool(pii_findings({"target": supervised["messages"][-1]["content"]})))
                    axis_counts["task"][task_key] += 1
                    axis_counts["audience"][audience_key] += 1
                    axis_counts["format"][format_key] += 1
                    if split == "train":
                        writers["supervised_train"].write(supervised)
                        writers["preference_train"].write(preference)
                        controlled_failures[str(preference["controlled_failure"])] += 1
                    else:
                        writers[f"supervised_{split}"].write(supervised)

        shards = {lane: writer.close() for lane, writer in writers.items()}
        overlaps = {
            "train_validation": sorted(parent_families["train"] & parent_families["validation"]),
            "train_test": sorted(parent_families["train"] & parent_families["test"]),
            "validation_test": sorted(parent_families["validation"] & parent_families["test"]),
        }
        gates = [
            {"id": "source_release_verified", "passed": True},
            {"id": "requested_train_scale", "passed": plan["counts"]["supervised_train"] >= minimum_train_rows, "value": plan["counts"]["supervised_train"], "threshold": minimum_train_rows},
            {"id": "quality_contract_clean", "passed": quality_failures == 0, "value": quality_failures},
            {"id": "generated_target_privacy_clean", "passed": pii_failures == 0, "value": pii_failures},
            {"id": "parent_family_split_isolation", "passed": not any(overlaps.values()), "overlap": overlaps},
            {"id": "task_axes_covered_for_requested_view_budget", "passed": bool(axis_counts["task"]) and (train_views_per_parent < len(VIEW_COMBINATIONS) or set(axis_counts["task"]) == set(TASK_BY_KEY)), "production_complete": set(axis_counts["task"]) == set(TASK_BY_KEY), "counts": dict(sorted(axis_counts["task"].items()))},
            {"id": "audience_axes_covered_for_requested_view_budget", "passed": bool(axis_counts["audience"]) and (train_views_per_parent < len(VIEW_COMBINATIONS) or set(axis_counts["audience"]) == set(AUDIENCE_BY_KEY)), "production_complete": set(axis_counts["audience"]) == set(AUDIENCE_BY_KEY), "counts": dict(sorted(axis_counts["audience"].items()))},
            {"id": "format_axes_covered_for_requested_view_budget", "passed": bool(axis_counts["format"]) and (train_views_per_parent < len(VIEW_COMBINATIONS) or set(axis_counts["format"]) == set(FORMAT_BY_KEY)), "production_complete": set(axis_counts["format"]) == set(FORMAT_BY_KEY), "counts": dict(sorted(axis_counts["format"].items()))},
            {"id": "preference_failures_complete", "passed": len(controlled_failures) == 4, "counts": dict(sorted(controlled_failures.items()))},
        ]
        failed = [str(gate["id"]) for gate in gates if gate["passed"] is not True]
        audit = {
            "schema_version": "duecare.measured_response.review_curriculum_quality.v1",
            "generator_version": GENERATOR_VERSION,
            "clean": not failed,
            "risk_flags": failed,
            "counts": plan["counts"],
            "parent_counts": plan["parent_counts"],
            "axis_counts": {axis: dict(sorted(counts.items())) for axis, counts in sorted(axis_counts.items())},
            "gates": gates,
            "independence_warning": plan["independence_warning"],
        }
        audit_path = output_dir / "quality-audit.json"
        _write_json(audit_path, audit)
        if failed:
            raise CurriculumError(f"review curriculum gates failed: {failed}")

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "candidate_id": "duecare-measured-response-review-curriculum-v1",
            "created_at": CREATED_AT,
            "generator_version": GENERATOR_VERSION,
            "generator_source_sha256": _sha256_file(Path(__file__)),
            "publication_status": "candidate_only_not_approved",
            "safe_to_train": True,
            "safe_to_publish": False,
            "source": {
                "dataset_id": release.get("dataset_id"),
                "release_manifest": release_path.name,
                "release_manifest_sha256": _sha256_file(release_path),
                "release_payload_sha256": release.get("release_manifest_payload_sha256"),
                "publication_state": release.get("publication_state"),
            },
            "counts": plan["counts"],
            "parent_counts": plan["parent_counts"],
            "dimensions": {
                "review_tasks": [row["key"] for row in REVIEW_TASKS],
                "audiences": [row["key"] for row in AUDIENCES],
                "presentation_formats": [row["key"] for row in PRESENTATION_FORMATS],
            },
            "augmentation_accounting": {
                "train_views_per_parent": train_views_per_parent,
                "heldout_views_per_parent": heldout_views_per_parent,
                "independent_observation": False,
                "independence_warning": plan["independence_warning"],
                "recommended_sampling": "group and cap aggregate weight by parent_row_sha256 or parent_lineage_family_id",
            },
            "reasoning_data_policy": "Visible review briefs, measured metadata, and final answers only; no hidden chain of thought or provider-private reasoning.",
            "contamination_boundary": "Source responses and grades came from the same benchmark family and cannot support independent model-improvement claims.",
            "license": ROW_LICENSE,
            "publication_approval_required": True,
            "quality_audit": {"path": audit_path.name, "sha256": _sha256_file(audit_path), "clean": True},
            "artifacts": {"shards": shards},
        }
        manifest_path = output_dir / "candidate-manifest.json"
        _write_json(manifest_path, manifest)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "candidate_manifest": manifest_path.name,
            "candidate_manifest_sha256": _sha256_file(manifest_path),
            "safe_to_train": True,
            "safe_to_publish": False,
            "quality_audit_clean": True,
            "counts": plan["counts"],
            "parent_counts": plan["parent_counts"],
            "shards": {lane: len(parts) for lane, parts in shards.items()},
        }
        _write_json(output_dir / "build-summary.json", summary)
        return summary
    except Exception as exc:
        _write_json(
            output_dir / "BUILD_FAILED.json",
            {"schema_version": SCHEMA_VERSION, "error_type": type(exc).__name__, "message": str(exc)[:1000]},
        )
        raise


def verify_candidate_dir(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    manifest_path = root / "candidate-manifest.json"
    if not manifest_path.is_file() or (root / "BUILD_FAILED.json").exists():
        return {"ok": False, "failures": ["missing_manifest_or_failed_build"]}
    manifest = _read_object(manifest_path, label="candidate manifest")
    failures: list[str] = []
    if manifest.get("safe_to_publish") is not False or manifest.get("safe_to_train") is not True:
        failures.append("candidate_state")
    audit = manifest.get("quality_audit") or {}
    audit_path = root / str(audit.get("path") or "")
    if not audit_path.is_file() or _sha256_file(audit_path) != audit.get("sha256"):
        failures.append("quality_audit_integrity")
    for lane, parts in ((manifest.get("artifacts") or {}).get("shards") or {}).items():
        observed = 0
        for part in parts:
            path = root / str(part.get("path") or "")
            if not path.is_file() or _sha256_file(path) != part.get("sha256") or path.stat().st_size != part.get("bytes"):
                failures.append(f"shard_integrity:{lane}:{part.get('path')}")
                continue
            observed += sum(1 for _ in _iter_jsonl(path))
        if observed != (manifest.get("counts") or {}).get(lane):
            failures.append(f"shard_rows:{lane}")
    return {
        "ok": not failures,
        "failures": failures,
        "candidate_manifest_sha256": _sha256_file(manifest_path),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-release", type=Path, default=DEFAULT_SOURCE_RELEASE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--train-views-per-parent", type=int, default=DEFAULT_TRAIN_VIEWS_PER_PARENT)
    parser.add_argument("--heldout-views-per-parent", type=int, default=DEFAULT_HELDOUT_VIEWS_PER_PARENT)
    parser.add_argument("--shard-rows", type=int, default=DEFAULT_SHARD_ROWS)
    parser.add_argument("--minimum-train-rows", type=int, default=DEFAULT_MINIMUM_TRAIN_ROWS)
    parser.add_argument("--plan", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.plan:
        result = build_plan(
            args.source_release,
            train_views_per_parent=args.train_views_per_parent,
            heldout_views_per_parent=args.heldout_views_per_parent,
            shard_rows=args.shard_rows,
        )
    else:
        result = build_candidate(
            args.source_release,
            args.output_dir,
            train_views_per_parent=args.train_views_per_parent,
            heldout_views_per_parent=args.heldout_views_per_parent,
            shard_rows=args.shard_rows,
            minimum_train_rows=args.minimum_train_rows,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
