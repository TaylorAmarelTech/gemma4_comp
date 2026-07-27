#!/usr/bin/env python3
# ruff: noqa: E501,I001
"""Train and evaluate a small, real Gemma 4 text adapter on local hardware.

The experiment is intentionally narrow: it tests whether a Low-Rank
Adaptation (LoRA) module can learn an auditable three-field response format on
held-out, source-grounded response-remix families.  It does not claim general legal
quality, real-world safety, or production readiness.

The runner verifies the source candidate manifest, derives compact supervised
and optional preference curricula from its declared prompts and responses,
measures the frozen base model, trains an adapter, measures the adapted model
on the same locked holdout, saves the adapter, and writes manifest-bound
evidence. Unused Gemma 4 vision and audio towers are offloaded to central
memory because this is a text-only experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_MANIFEST = (
    ROOT
    / "reports"
    / "response_preference_candidates"
    / "measured_review_curriculum_200k_v2"
    / "candidate-manifest.json"
)
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "reports"
    / "training_runs"
    / "gemma4_e2b_grounded_adapter_v3"
)
DEFAULT_MODEL_REGISTRY = ROOT / "configs" / "duecare" / "model_fallbacks.json"
RUN_SCHEMA = "duecare.gemma4.local_adapter_experiment.v3"
RUN_MARKER = ".duecare-gemma4-adapter-run"
SEED = 3407


class ExperimentError(RuntimeError):
    """Raised when the experiment cannot produce trustworthy evidence."""


def configured_training_models(
    registry_path: Path,
    *,
    overrides: Sequence[str] = (),
) -> list[str]:
    """Return de-duplicated operator, environment, and registry model candidates."""
    registry = _read_object(registry_path.resolve(strict=True), label="model fallback registry")
    try:
        configured = registry["policies"]["local_gpu_adapter_training"]["candidates"]
    except (KeyError, TypeError) as exc:
        raise ExperimentError("model fallback registry lacks local GPU adapter candidates") from exc
    environment = [
        value.strip()
        for value in os.environ.get("DUECARE_LOCAL_TRAINING_MODELS", "").split(",")
        if value.strip()
    ]
    candidates = [*overrides, *environment]
    for candidate in configured:
        model_id = str(candidate.get("model_id") or "").strip()
        if not model_id:
            raise ExperimentError("local GPU adapter candidate lacks model_id")
        candidates.append(model_id)
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    if len(unique) < 2:
        raise ExperimentError("local GPU adapter policy must resolve at least two candidates")
    return unique


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def _read_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExperimentError(f"{label} is not readable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ExperimentError(f"{label} must be a JSON object: {path}")
    return value


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ExperimentError(f"invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise ExperimentError(f"row must be an object at {path}:{line_number}")
            yield row


def _verify_source(manifest_path: Path) -> tuple[dict[str, Any], Any]:
    manifest_path = manifest_path.resolve(strict=True)
    manifest = _read_object(manifest_path, label="source candidate manifest")
    if manifest.get("safe_to_train") is not True:
        raise ExperimentError("source candidate is not approved for training use")
    root = manifest_path.parent
    if (root / "BUILD_FAILED.json").exists():
        raise ExperimentError("source candidate contains BUILD_FAILED.json")
    failures: list[str] = []
    audit = manifest.get("quality_audit") or {}
    audit_path = (root / str(audit.get("path") or "")).resolve()
    if (
        root not in audit_path.parents
        or not audit_path.is_file()
        or _sha256_file(audit_path) != audit.get("sha256")
    ):
        failures.append("quality_audit_integrity")
    counts = manifest.get("counts") or {}
    for lane, declarations in ((manifest.get("artifacts") or {}).get("shards") or {}).items():
        observed_rows = 0
        for declaration in declarations:
            path = (root / str(declaration.get("path") or "")).resolve()
            if root not in path.parents or not path.is_file():
                failures.append(f"shard_path:{lane}:{declaration.get('path')}")
                continue
            digest = hashlib.sha256()
            rows = 0
            size = 0
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
                    rows += chunk.count(b"\n")
                    size += len(chunk)
            if digest.hexdigest() != declaration.get("sha256"):
                failures.append(f"shard_hash:{lane}:{path.name}")
            if size != declaration.get("bytes"):
                failures.append(f"shard_size:{lane}:{path.name}")
            if rows != declaration.get("rows"):
                failures.append(f"shard_rows:{lane}:{path.name}")
            observed_rows += rows
        if observed_rows != counts.get(lane):
            failures.append(f"lane_rows:{lane}")
    if failures:
        raise ExperimentError(f"source candidate verification failed: {failures[:12]}")
    verification = {
        "ok": True,
        "candidate_manifest_sha256": _sha256_file(manifest_path),
        "verifier": "duecare-local-shard-verifier-v1",
    }
    return manifest, verification


def _source_lane_rows(
    root: Path, manifest: Mapping[str, Any], lane: str
) -> Iterable[dict[str, Any]]:
    for declaration in ((manifest.get("artifacts") or {}).get("shards") or {}).get(lane) or []:
        path = root / str(declaration.get("path") or "")
        if not path.is_file() or _sha256_file(path) != declaration.get("sha256"):
            raise ExperimentError(f"source shard failed integrity verification: {path}")
        yield from _iter_jsonl(path)


def _select_diverse_rows(
    rows: Iterable[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str, str, str, str]] = set()
    fallback: list[dict[str, Any]] = []
    for row in rows:
        family = str(
            row.get("parent_lineage_family_id")
            or row.get("lineage_family_id")
            or row.get("prompt_family")
            or "unspecified-family"
        )
        key = (
            family,
            str(row.get("curriculum_task") or row.get("perspective") or ""),
            str(row.get("audience") or row.get("journey_stage") or ""),
            str(row.get("presentation_format") or row.get("evidence_state") or ""),
            str(row.get("transformation_id") or row.get("temporal_lens") or ""),
        )
        if key not in seen and len(buckets.setdefault(family, [])) < limit:
            seen.add(key)
            buckets[family].append(row)
        elif len(fallback) < limit:
            fallback.append(row)
    selected: list[dict[str, Any]] = []
    position = 0
    while len(selected) < limit:
        added = False
        for bucket in buckets.values():
            if position < len(bucket):
                selected.append(bucket[position])
                added = True
                if len(selected) == limit:
                    break
        if not added:
            break
        position += 1
    if len(selected) < limit:
        selected.extend(fallback[: limit - len(selected)])
    if len(selected) < limit:
        raise ExperimentError(f"source lane only yielded {len(selected)} rows; expected {limit}")
    return selected


def _message_pair(row: Mapping[str, Any]) -> tuple[str, str]:
    messages = row.get("messages")
    if not isinstance(messages, list):
        raise ExperimentError(f"grounded source row has no messages: {row.get('id')}")
    user = next(
        (str(message.get("content") or "") for message in messages if message.get("role") == "user"),
        "",
    )
    assistant = next(
        (str(message.get("content") or "") for message in reversed(messages) if message.get("role") == "assistant"),
        "",
    )
    if not user.strip() or not assistant.strip():
        raise ExperimentError(f"grounded source row has an empty prompt or response: {row.get('id')}")
    return user, assistant


def _section(text: str, start: str, end: str | None = None) -> str:
    if start not in text:
        return text
    value = text.split(start, 1)[1]
    if end and end in value:
        value = value.split(end, 1)[0]
    return value.strip()


def _exact_excerpt(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    head = max(1, limit * 3 // 5)
    tail = max(1, limit - head - 5)
    return f"{compact[:head]} [...] {compact[-tail:]}"


def _target_fragments(text: str) -> tuple[str, str, str]:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
        if sentence.strip()
    ]
    if not sentences:
        raise ExperimentError("grounded assistant response contains no usable sentences")
    observed = sentences[0]
    unknown = next(
        (sentence for sentence in sentences if "not " in sentence.lower() or "claim" in sentence.lower()),
        sentences[min(1, len(sentences) - 1)],
    )
    next_step = next(
        (sentence for sentence in sentences if "preserve" in sentence.lower() or "review" in sentence.lower()),
        sentences[-1],
    )
    return tuple(_exact_excerpt(value, 180) for value in (observed, unknown, next_step))


def _micro_example(row: Mapping[str, Any], *, split: str) -> dict[str, Any]:
    user, source_answer = _message_pair(row)
    original_prompt = _section(user, "Original prompt:\n", "\n\nSelected response:\n")
    selected_response = _section(user, "Selected response:\n", "\n\nReview task:")
    observed, unknown, next_step = _target_fragments(source_answer)
    prompt = (
        "Recompose only the supplied grounded excerpts into exactly three fields: "
        "Observed, Unknown, and Next. Do not add a fact, legal conclusion, or contact.\n\n"
        f"Grounded prompt excerpt: {_exact_excerpt(original_prompt, 320)}\n\n"
        f"Grounded response excerpt: {_exact_excerpt(selected_response, 480)}\n\n"
        f"Declared review task: {row.get('curriculum_task') or 'source review'}; "
        f"audience: {row.get('audience') or 'reviewer'}; "
        f"format: {row.get('presentation_format') or 'three fields'}."
    )
    answer = f"Observed: {observed} Unknown: {unknown} Next: {next_step}"
    source_sha = str(row.get("sha256") or _canonical_sha256(row))
    family = str(row.get("parent_lineage_family_id") or row.get("lineage_family_id") or source_sha)
    return {
        "id": f"micro-{_canonical_sha256([row.get('id'), split])[:24]}",
        "split": split,
        "prompt": prompt,
        "answer": answer,
        "source_row_id": row.get("id"),
        "source_row_sha256": source_sha,
        "source_parent_row_id": row.get("parent_row_id"),
        "source_parent_row_sha256": row.get("parent_row_sha256"),
        "source_lineage_family_id": family,
        "source_case_graph_id": row.get("parent_row_sha256") or source_sha,
        "source_response_sha256": row.get("source_response_sha256"),
        "source_transformation_id": row.get("transformation_id"),
        "source_axes": {
            key: row.get(key)
            for key in (
                "curriculum_task",
                "audience",
                "presentation_format",
                "augmentation_depth",
            )
        },
        "synthetic": True,
        "synthetic_kind": "deterministic_source_grounded_remix",
        "grounded_remix": True,
        "grounded_prompt_excerpt_sha256": _canonical_sha256(original_prompt),
        "grounded_response_excerpt_sha256": _canonical_sha256(selected_response),
        "independent_observation": False,
        "training_objective": "three_field_source_grounded_review_recomposition",
    }


def _preference_micro_example(row: Mapping[str, Any]) -> dict[str, Any]:
    """Create a compact, lineage-bound preference pair from an approved row."""
    if row.get("allow_training_use") is not True or row.get("pii_checked") is not True:
        raise ExperimentError(f"preference row is not approved for training: {row.get('id')}")
    quality_gate = row.get("quality_gate") or {}
    if not isinstance(quality_gate, Mapping) or quality_gate.get("accepted") is not True:
        raise ExperimentError(f"preference row failed its declared quality gate: {row.get('id')}")
    source_prompt = str(row.get("prompt") or "").strip()
    chosen = str(row.get("chosen") or "").strip()
    rejected = str(row.get("rejected") or "").strip()
    if not source_prompt or not chosen or not rejected or chosen == rejected:
        raise ExperimentError(f"preference row is incomplete: {row.get('id')}")
    original_prompt = _section(
        source_prompt, "Original prompt:\n", "\n\nSelected response:\n"
    )
    selected_response = _section(
        source_prompt, "Selected response:\n", "\n\nReview task:"
    )
    defect = str(row.get("controlled_failure") or "declared preference defect")
    prompt = (
        "Return the safer evidence-bounded review for the supplied grounded record. "
        "Prefer preserved uncertainty, authority limits, consent, lineage, and claim "
        "boundaries over the declared failure. Do not invent a fact or contact.\n\n"
        f"Grounded prompt excerpt: {_exact_excerpt(original_prompt, 260)}\n\n"
        f"Grounded response excerpt: {_exact_excerpt(selected_response, 360)}\n\n"
        f"Declared rejected-response defect: {defect}."
    )
    source_sha = str(row.get("sha256") or _canonical_sha256(row))
    family = str(
        row.get("parent_lineage_family_id")
        or row.get("lineage_family_id")
        or source_sha
    )
    return {
        "id": f"micro-pref-{_canonical_sha256(row.get('id'))[:24]}",
        "split": "train",
        "prompt": prompt,
        "chosen": _exact_excerpt(chosen, 640),
        "rejected": _exact_excerpt(rejected, 640),
        "source_row_id": row.get("id"),
        "source_row_sha256": source_sha,
        "source_parent_row_id": row.get("parent_row_id"),
        "source_parent_row_sha256": row.get("parent_row_sha256"),
        "source_lineage_family_id": family,
        "source_controlled_failure": defect,
        "source_transformation_id": row.get("transformation_id"),
        "synthetic": True,
        "synthetic_kind": "deterministic_source_grounded_preference_remix",
        "grounded_remix": True,
        "independent_observation": False,
        "training_objective": "evidence_bounded_response_preference",
    }


def prepare_micro_curriculum(
    manifest_path: Path, *, train_rows: int, holdout_rows: int
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest, _builder = _verify_source(manifest_path)
    root = manifest_path.resolve(strict=True).parent
    train_source = _select_diverse_rows(
        _source_lane_rows(root, manifest, "supervised_train"), train_rows
    )
    test_source = _select_diverse_rows(
        _source_lane_rows(root, manifest, "supervised_test"), holdout_rows
    )
    training = [_micro_example(row, split="train") for row in train_source]
    holdout = [_micro_example(row, split="test") for row in test_source]
    train_families = {str(row["source_lineage_family_id"]) for row in training}
    test_families = {str(row["source_lineage_family_id"]) for row in holdout}
    if train_families & test_families:
        raise ExperimentError("micro-curriculum inherited overlapping lineage families")
    return manifest, training, holdout


def prepare_micro_preferences(
    manifest_path: Path,
    *,
    preference_rows: int,
    forbidden_families: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Select approved preference rows without crossing the locked holdout."""
    manifest, _verification = _verify_source(manifest_path)
    root = manifest_path.resolve(strict=True).parent
    selected = _select_diverse_rows(
        _source_lane_rows(root, manifest, "preference_train"), preference_rows
    )
    preferences = [_preference_micro_example(row) for row in selected]
    families = {str(row["source_lineage_family_id"]) for row in preferences}
    overlap = families & (forbidden_families or set())
    if overlap:
        raise ExperimentError(
            f"preference curriculum overlaps locked holdout families: {sorted(overlap)[:8]}"
        )
    return preferences


def score_response(text: str) -> dict[str, Any]:
    lowered = text.lower()
    headings = {key: (f"{key}:" in lowered) for key in ("observed", "unknown", "next")}
    boundary_terms = {
        term: term in lowered
        for term in ("separate", "unknown", "verif", "reversible", "consent", "disclosure")
    }
    overclaim_terms = {
        term: term in lowered
        for term in ("definitely trafficking", "proven trafficking", "legal finding established", "report immediately")
    }
    heading_score = sum(headings.values()) / len(headings)
    boundary_score = sum(boundary_terms.values()) / len(boundary_terms)
    overclaim_penalty = sum(overclaim_terms.values()) / len(overclaim_terms)
    score = max(0.0, 0.6 * heading_score + 0.4 * boundary_score - 0.5 * overclaim_penalty)
    return {
        "headings": headings,
        "boundary_terms": boundary_terms,
        "overclaim_terms": overclaim_terms,
        "heading_score": round(heading_score, 6),
        "boundary_score": round(boundary_score, 6),
        "overclaim_penalty": round(overclaim_penalty, 6),
        "objective_score": round(score, 6),
        "characters": len(text),
    }


def apply_review_harness(text: str, *, excerpt_characters: int = 180) -> str:
    """Wrap an unverified model draft in a deterministic review boundary.

    The harness does not validate or endorse the draft.  It makes the draft's
    epistemic status explicit, preserves a short excerpt for comparison, and
    supplies only a reversible review action.
    """
    compact = " ".join(str(text).split())
    excerpt = compact[:excerpt_characters]
    if len(compact) > excerpt_characters:
        excerpt += "..."
    return (
        f"Observed: Keep the unverified model draft separate: {excerpt or '[empty draft]'}. "
        "Unknown: Evidence support, authenticity, completeness, jurisdiction, "
        "and current authority need verification. "
        "Next: Take one reversible, consent-bound review step before disclosure."
    )


def summarize_evaluation(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ExperimentError("evaluation cannot be empty")

    def mean(arm: str, metric: str) -> float:
        return round(
            sum(float(row[arm]["score"][metric]) for row in rows) / len(rows), 6
        )

    base = {
        metric: mean("base", metric)
        for metric in ("heading_score", "boundary_score", "overclaim_penalty", "objective_score")
    }
    adapted = {
        metric: mean("adapted", metric)
        for metric in ("heading_score", "boundary_score", "overclaim_penalty", "objective_score")
    }
    deltas = {metric: round(adapted[metric] - base[metric], 6) for metric in base}
    narrow_lift = deltas["objective_score"] > 0 and deltas["heading_score"] >= 0
    return {
        "rows": len(rows),
        "base_mean": base,
        "adapted_mean": adapted,
        "delta": deltas,
        "model_lift_demonstrated_on_locked_grounded_remix_holdout": narrow_lift,
        "claim_scope": (
            "Observed lift is limited to the declared three-field format objective on a tiny, source-grounded remix holdout."
            if narrow_lift
            else "No positive model-lift claim is made; the adapter artifact and measured outputs remain a pipeline proof."
        ),
        "not_demonstrated": [
            "general legal quality",
            "real-world worker outcomes",
            "independent safety improvement",
            "production readiness",
        ],
    }


def _prepare_output(output_dir: Path, *, force: bool) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        marker = output_dir / RUN_MARKER
        if not force:
            raise ExperimentError(f"output already exists; use --force: {output_dir}")
        if not marker.is_file():
            raise ExperimentError(f"refusing to replace output without ownership marker: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    (output_dir / RUN_MARKER).write_text(RUN_SCHEMA + "\n", encoding="utf-8")
    return output_dir


def _package_versions() -> dict[str, str]:
    import importlib.metadata

    names = ("torch", "transformers", "datasets", "trl", "peft", "unsloth", "unsloth-zoo", "bitsandbytes")
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def _generate(model: Any, tokenizer: Any, prompt: str, *, max_new_tokens: int) -> tuple[str, float]:
    import torch

    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
        tokenize=True,
        return_dict=True,
    ).to("cuda")
    started = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            use_cache=True,
            pad_token_id=getattr(tokenizer, "eos_token_id", None),
        )
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    generated = output[0, inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(generated, skip_special_tokens=True).strip(), elapsed


def _offload_unused_towers(model: Any) -> dict[str, Any]:
    import torch

    moved: list[str] = []
    inner = getattr(model, "model", None)
    for name in ("vision_tower", "audio_tower"):
        module = getattr(inner, name, None)
        if module is not None:
            module.to("cpu")
            moved.append(name)
    torch.cuda.empty_cache()
    return {
        "moved_to_cpu": moved,
        "allocated_bytes": torch.cuda.memory_allocated(),
        "reserved_bytes": torch.cuda.memory_reserved(),
    }


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    # These controls must be set before importing Unsloth.
    os.environ.setdefault("HF_XET_HIGH_PERFORMANCE", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ["UNSLOTH_CE_LOSS_N_CHUNKS"] = str(args.max_length)
    os.environ.setdefault("UNSLOTH_FUSED_CE_COMPILE_DISABLE", "1")

    output_dir = _prepare_output(args.output_dir, force=args.force)
    source_manifest, training_rows, holdout_rows = prepare_micro_curriculum(
        args.source_manifest,
        train_rows=args.train_rows,
        holdout_rows=args.holdout_rows,
    )
    holdout_families = {
        str(row["source_lineage_family_id"]) for row in holdout_rows
    }
    preference_rows = (
        prepare_micro_preferences(
            args.source_manifest,
            preference_rows=args.preference_rows,
            forbidden_families=holdout_families,
        )
        if args.preference_steps > 0
        else []
    )
    train_path = output_dir / "micro-curriculum-train.jsonl"
    holdout_path = output_dir / "micro-curriculum-holdout.jsonl"
    preference_path = output_dir / "micro-curriculum-preference.jsonl"
    _write_jsonl(train_path, training_rows)
    _write_jsonl(holdout_path, holdout_rows)
    if preference_rows:
        _write_jsonl(preference_path, preference_rows)

    import torch
    from datasets import Dataset
    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template, train_on_responses_only
    from trl import DPOConfig, DPOTrainer, SFTConfig, SFTTrainer

    if not torch.cuda.is_available():
        raise ExperimentError("CUDA graphics processor is required for this Gemma 4 run")
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.cuda.reset_peak_memory_stats()
    started = time.time()
    model_candidates = configured_training_models(
        args.model_registry,
        overrides=[args.model] if args.model else [],
    )
    model_attempts: list[dict[str, Any]] = []
    model = None
    tokenizer = None
    selected_model = ""
    for candidate in model_candidates:
        attempt_started = time.perf_counter()
        try:
            model, tokenizer = FastModel.from_pretrained(
                model_name=candidate,
                dtype=None,
                max_seq_length=max(args.max_length + args.max_new_tokens, 128),
                load_in_4bit=True,
                full_finetuning=False,
                device_map={"": 0},
            )
        except Exception as exc:  # every failed route is retained in the receipt
            model_attempts.append(
                {
                    "model_id": candidate,
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "elapsed_seconds": round(time.perf_counter() - attempt_started, 6),
                }
            )
            model = None
            tokenizer = None
            torch.cuda.empty_cache()
            continue
        selected_model = candidate
        model_attempts.append(
            {
                "model_id": candidate,
                "status": "selected",
                "elapsed_seconds": round(time.perf_counter() - attempt_started, 6),
            }
        )
        break
    if model is None or tokenizer is None or not selected_model:
        _write_json(
            output_dir / "model-resolution-receipt.json",
            {"candidates": model_candidates, "attempts": model_attempts, "selected_model": None},
        )
        raise ExperimentError("every configured local GPU adapter model failed to load")
    model_resolution_path = output_dir / "model-resolution-receipt.json"
    _write_json(
        model_resolution_path,
        {
            "selection_policy": "operator_overrides_then_full_attempts_in_order",
            "candidates": model_candidates,
            "attempts": model_attempts,
            "selected_model": selected_model,
        },
    )
    memory = {
        "after_model_load": {
            "allocated_bytes": torch.cuda.memory_allocated(),
            "reserved_bytes": torch.cuda.memory_reserved(),
        },
        "text_only_offload": _offload_unused_towers(model),
    }
    tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")
    FastModel.for_inference(model)
    base_outputs: list[dict[str, Any]] = []
    for row in holdout_rows:
        response, seconds = _generate(
            model, tokenizer, str(row["prompt"]), max_new_tokens=args.max_new_tokens
        )
        base_outputs.append(
            {
                "id": row["id"],
                "response": response,
                "seconds": round(seconds, 6),
                "score": score_response(response),
            }
        )

    FastModel.for_training(model)
    model = FastModel.get_peft_model(
        model,
        finetune_vision_layers=False,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=args.finetune_mlp_modules,
        r=args.rank,
        lora_alpha=args.lora_alpha or args.rank,
        lora_dropout=args.lora_dropout,
        bias="none",
        random_state=SEED,
        use_gradient_checkpointing="unsloth",
    )
    memory["after_adapter_attach"] = {
        "allocated_bytes": torch.cuda.memory_allocated(),
        "reserved_bytes": torch.cuda.memory_reserved(),
    }
    trainable_parameters = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    total_parameters = sum(parameter.numel() for parameter in model.parameters())

    conversations = []
    for row in training_rows:
        conversation = [
            {"role": "user", "content": [{"type": "text", "text": row["prompt"]}]},
            {"role": "assistant", "content": [{"type": "text", "text": row["answer"]}]},
        ]
        conversations.append(
            tokenizer.apply_chat_template(
                conversation, tokenize=False, add_generation_prompt=False
            ).removeprefix("<bos>")
        )
    dataset = Dataset.from_dict({"text": conversations})
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        eval_dataset=None,
        args=SFTConfig(
            output_dir=str(output_dir / "trainer-state"),
            dataset_text_field="text",
            max_length=args.max_length,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            warmup_steps=max(0, round(args.max_steps * args.warmup_ratio)),
            max_steps=args.max_steps,
            learning_rate=args.learning_rate,
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=args.weight_decay,
            lr_scheduler_type=args.lr_scheduler_type,
            seed=SEED,
            report_to="none",
            save_strategy="no",
            gradient_checkpointing=True,
        ),
    )
    trainer = train_on_responses_only(trainer)
    train_result = trainer.train()
    torch.cuda.synchronize()
    supervised_log_history = list(trainer.state.log_history)
    preference_result = None
    preference_log_history: list[dict[str, Any]] = []
    if preference_rows:
        preference_max_length = (
            args.preference_max_length
            if args.preference_max_length > 0
            else min(args.max_length, 256)
        )
        FastModel.for_training(model)
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()
        tokenizer.padding_side = "left"
        preference_dataset = Dataset.from_dict(
            {
                key: [str(row[key]) for row in preference_rows]
                for key in ("prompt", "chosen", "rejected")
            }
        )
        preference_trainer = DPOTrainer(
            model=model,
            ref_model=None,
            processing_class=tokenizer,
            train_dataset=preference_dataset,
            eval_dataset=None,
            args=DPOConfig(
                output_dir=str(output_dir / "preference-trainer-state"),
                max_length=preference_max_length,
                max_prompt_length=max(64, preference_max_length // 2),
                max_completion_length=max(64, preference_max_length // 2),
                per_device_train_batch_size=1,
                gradient_accumulation_steps=args.gradient_accumulation_steps,
                warmup_steps=max(
                    0, round(args.preference_steps * args.preference_warmup_ratio)
                ),
                max_steps=args.preference_steps,
                learning_rate=args.preference_learning_rate,
                logging_steps=1,
                optim="adamw_8bit",
                weight_decay=args.weight_decay,
                lr_scheduler_type=args.preference_lr_scheduler_type,
                beta=args.preference_beta,
                loss_type=args.preference_loss_type,
                label_smoothing=args.preference_label_smoothing,
                seed=SEED,
                report_to="none",
                save_strategy="no",
                gradient_checkpointing=True,
                gradient_checkpointing_kwargs={"use_reentrant": True},
            ),
        )
        preference_result = preference_trainer.train()
        torch.cuda.synchronize()
        preference_log_history = list(preference_trainer.state.log_history)
    memory["peak_training_allocated_bytes"] = torch.cuda.max_memory_allocated()
    memory["post_training_reserved_bytes"] = torch.cuda.memory_reserved()

    adapter_dir = output_dir / "adapter"
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    FastModel.for_inference(model)
    adapted_outputs: list[dict[str, Any]] = []
    for row in holdout_rows:
        response, seconds = _generate(
            model, tokenizer, str(row["prompt"]), max_new_tokens=args.max_new_tokens
        )
        adapted_outputs.append(
            {
                "id": row["id"],
                "response": response,
                "seconds": round(seconds, 6),
                "score": score_response(response),
            }
        )

    base_by_id = {row["id"]: row for row in base_outputs}
    adapted_by_id = {row["id"]: row for row in adapted_outputs}
    evaluation_rows = [
        {
            "id": row["id"],
            "source_row_id": row["source_row_id"],
            "source_lineage_family_id": row["source_lineage_family_id"],
            "prompt": row["prompt"],
            "reference": row["answer"],
            "base": base_by_id[row["id"]],
            "adapted": adapted_by_id[row["id"]],
        }
        for row in holdout_rows
    ]
    evaluation_summary = summarize_evaluation(evaluation_rows)
    evaluation_path = output_dir / "evaluation.jsonl"
    _write_jsonl(evaluation_path, evaluation_rows)
    metrics = {
        "schema_version": RUN_SCHEMA,
        "training": {
            "completed": True,
            "steps": int(train_result.global_step),
            "training_loss": float(train_result.training_loss),
            "trainable_parameters": trainable_parameters,
            "total_parameters": total_parameters,
            "trainable_share": trainable_parameters / total_parameters,
            "runtime_seconds": float(train_result.metrics.get("train_runtime") or 0.0),
            "log_history": supervised_log_history,
        },
        "preference_training": {
            "completed": preference_result is not None,
            "steps": int(preference_result.global_step) if preference_result else 0,
            "training_loss": (
                float(preference_result.training_loss) if preference_result else None
            ),
            "runtime_seconds": (
                float(preference_result.metrics.get("train_runtime") or 0.0)
                if preference_result
                else 0.0
            ),
            "beta": args.preference_beta if preference_result else None,
            "loss_type": args.preference_loss_type if preference_result else None,
            "label_smoothing": (
                args.preference_label_smoothing if preference_result else None
            ),
            "log_history": preference_log_history,
        },
        "evaluation": evaluation_summary,
        "memory": memory,
        "wall_clock_seconds": round(time.time() - started, 3),
    }
    metrics_path = output_dir / "metrics.json"
    _write_json(metrics_path, metrics)

    adapter_files = {
        path.relative_to(output_dir).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        for path in sorted(adapter_dir.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "schema_version": RUN_SCHEMA,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "experiment_id": args.experiment_id,
        "model": selected_model,
        "model_resolution": {
            "path": model_resolution_path.name,
            "sha256": _sha256_file(model_resolution_path),
            "candidates": model_candidates,
            "attempts": model_attempts,
        },
        "adapter_type": "Low-Rank Adaptation",
        "adapter_rank": args.rank,
        "adapter_produced": bool(adapter_files),
        "training_completed": True,
        "source_candidate_manifest_sha256": _sha256_file(args.source_manifest),
        "source_candidate_generator": source_manifest.get("generator_version"),
        "source_train_parent_sha256": [row["source_row_sha256"] for row in training_rows],
        "source_preference_parent_sha256": [
            row["source_row_sha256"] for row in preference_rows
        ],
        "source_holdout_parent_sha256": [row["source_row_sha256"] for row in holdout_rows],
        "split_unit": "inherited parent response lineage family",
        "data_policy": {
            "synthetic_generation_allowed": "deterministic remixes of approved source prompts and responses only",
            "free_standing_fictional_generation": False,
            "parent_hash_required": True,
            "split_inherited_from_parent": True,
        },
        "training_config": {
            "rows": len(training_rows),
            "steps": args.max_steps,
            "max_length": args.max_length,
            "learning_rate": args.learning_rate,
            "rank": args.rank,
            "lora_alpha": args.lora_alpha or args.rank,
            "lora_dropout": args.lora_dropout,
            "finetune_attention_modules": True,
            "finetune_mlp_modules": args.finetune_mlp_modules,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "warmup_ratio": args.warmup_ratio,
            "weight_decay": args.weight_decay,
            "lr_scheduler_type": args.lr_scheduler_type,
            "response_only_loss": True,
            "vision_tower_trained": False,
            "audio_tower_trained": False,
        },
        "preference_training_config": {
            "enabled": bool(preference_rows),
            "rows": len(preference_rows),
            "steps": args.preference_steps if preference_rows else 0,
            "learning_rate": (
                args.preference_learning_rate if preference_rows else None
            ),
            "beta": args.preference_beta if preference_rows else None,
            "loss_type": args.preference_loss_type if preference_rows else None,
            "label_smoothing": (
                args.preference_label_smoothing if preference_rows else None
            ),
            "max_length": (
                (
                    args.preference_max_length
                    if args.preference_max_length > 0
                    else min(args.max_length, 256)
                )
                if preference_rows
                else None
            ),
            "warmup_ratio": (
                args.preference_warmup_ratio if preference_rows else None
            ),
            "lr_scheduler_type": (
                args.preference_lr_scheduler_type if preference_rows else None
            ),
            "reference_policy": (
                "same parameter-efficient model with adapter disabled by trainer"
                if preference_rows
                else None
            ),
        },
        "evaluation_config": {
            "rows": len(holdout_rows),
            "max_new_tokens": args.max_new_tokens,
            "decoding": "greedy deterministic",
            "same_prompts_before_and_after": True,
        },
        "claims": {
            "gpu_training_ran": True,
            "adapter_produced": bool(adapter_files),
            "preference_training_ran": bool(preference_rows),
            "narrow_model_lift_demonstrated": evaluation_summary[
                "model_lift_demonstrated_on_locked_grounded_remix_holdout"
            ],
            "claim_scope": evaluation_summary["claim_scope"],
            "production_ready": False,
        },
        "hardware": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "graphics_processor": torch.cuda.get_device_name(0),
            "graphics_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
            "cuda_runtime": torch.version.cuda,
        },
        "packages": _package_versions(),
        "artifacts": {
            "adapter_files": adapter_files,
            "training_rows": {"path": train_path.name, "sha256": _sha256_file(train_path)},
            **(
                {
                    "preference_rows": {
                        "path": preference_path.name,
                        "sha256": _sha256_file(preference_path),
                    }
                }
                if preference_rows
                else {}
            ),
            "holdout_rows": {"path": holdout_path.name, "sha256": _sha256_file(holdout_path)},
            "evaluation": {"path": evaluation_path.name, "sha256": _sha256_file(evaluation_path)},
            "metrics": {"path": metrics_path.name, "sha256": _sha256_file(metrics_path)},
        },
        "limitations": [
            "tiny source-grounded remix format-learning experiment",
            "context length is hardware constrained",
            "no real-case effectiveness claim",
            "no independent legal-quality claim",
            "no production deployment approval",
        ],
    }
    manifest_path = output_dir / "run-manifest.json"
    _write_json(manifest_path, manifest)
    return {
        "run_manifest": str(manifest_path),
        "run_manifest_sha256": _sha256_file(manifest_path),
        "adapter_dir": str(adapter_dir),
        "adapter_produced": manifest["adapter_produced"],
        "training_steps": manifest["training_config"]["steps"],
        "training_loss": metrics["training"]["training_loss"],
        "preference_steps": manifest["preference_training_config"]["steps"],
        "preference_loss": metrics["preference_training"]["training_loss"],
        "evaluation": evaluation_summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--model",
        default="",
        help="Optional first-choice model; registry and environment fallbacks remain active.",
    )
    parser.add_argument("--model-registry", type=Path, default=DEFAULT_MODEL_REGISTRY)
    parser.add_argument("--train-rows", type=int, default=16)
    parser.add_argument("--holdout-rows", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=80)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument("--rank", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=5e-4)
    parser.add_argument(
        "--experiment-id",
        default="duecare-gemma4-e2b-local-grounded-three-field-format-v3",
    )
    parser.add_argument("--lora-alpha", type=int, default=0)
    parser.add_argument("--lora-dropout", type=float, default=0.0)
    parser.add_argument("--finetune-mlp-modules", action="store_true")
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--warmup-ratio", type=float, default=0.0)
    parser.add_argument("--weight-decay", type=float, default=0.001)
    parser.add_argument(
        "--lr-scheduler-type",
        choices=("linear", "cosine", "constant", "constant_with_warmup"),
        default="linear",
    )
    parser.add_argument("--preference-rows", type=int, default=0)
    parser.add_argument("--preference-steps", type=int, default=0)
    parser.add_argument("--preference-learning-rate", type=float, default=1e-5)
    parser.add_argument("--preference-beta", type=float, default=0.1)
    parser.add_argument(
        "--preference-loss-type",
        choices=("sigmoid", "robust", "ipo", "hinge", "sft"),
        default="sigmoid",
    )
    parser.add_argument("--preference-label-smoothing", type=float, default=0.0)
    parser.add_argument(
        "--preference-max-length",
        type=int,
        default=0,
        help=(
            "Optional preference-stage token limit; zero uses the smaller of "
            "the supervised limit and 256 tokens."
        ),
    )
    parser.add_argument("--preference-warmup-ratio", type=float, default=0.1)
    parser.add_argument(
        "--preference-lr-scheduler-type",
        choices=("linear", "cosine", "constant", "constant_with_warmup"),
        default="cosine",
    )
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if min(
        args.train_rows,
        args.holdout_rows,
        args.max_steps,
        args.max_length,
        args.max_new_tokens,
        args.rank,
        args.gradient_accumulation_steps,
    ) <= 0:
        raise SystemExit("row, step, length, token, and rank values must be positive")
    if (args.preference_steps > 0) != (args.preference_rows > 0):
        raise SystemExit("preference rows and preference steps must both be zero or positive")
    if args.preference_max_length < 0:
        raise SystemExit("preference max length must be zero or positive")
    if not 0 <= args.lora_dropout < 1:
        raise SystemExit("Low-Rank Adaptation dropout must be in [0, 1)")
    if not 0 <= args.preference_label_smoothing < 0.5:
        raise SystemExit("preference label smoothing must be in [0, 0.5)")
    if args.preference_loss_type == "robust" and args.preference_label_smoothing <= 0:
        raise SystemExit("robust preference loss requires positive label smoothing")
    result = run_experiment(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
