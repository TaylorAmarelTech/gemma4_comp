#!/usr/bin/env python3
"""Model-card generator -- render a publishable card from a finetune_registry provenance record.

Reads the latest finetune_registry.py record for a model_id and renders a Hugging-Face-style model
card (YAML frontmatter + markdown): base model, the reproducibility provenance (git_sha = code version,
data_manifest_sha256 = dataset version), training-data counts, eval scores, intended use, limitations,
and the privacy boundary. So the published adapter ships with a card that lets a reviewer trace it back
to the exact data + code -- the hackathon's "real, not faked: reproducible from (git_sha, dataset_version)"
invariant, made human-readable.

Propose-only + offline: reads the registry, writes reports/training/<model_id>_model_card.md (gitignored
until a real trained model is published). Reuses finetune_registry.load/latest_by_id (DRY).

    python scripts/build_model_card.py --model-id duecare-gemma-4-e4b-safetyjudge-v0.1.0
    python scripts/build_model_card.py --model-id ... --stdout      # print instead of writing
    python scripts/build_model_card.py --model-id ... --require-verified-artifacts
Design: docs/research/training_regimes_and_systems.md
"""
from __future__ import annotations

import argparse
import hashlib
import math
import pathlib
import re
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from finetune_registry import (  # noqa: E402
    load as _load_registry,
    latest_by_id as _latest_by_id,
    verify_record_artifacts as _verify_record_artifacts,
)

OUT_DIR = _ROOT / "reports" / "training"
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(r"(?i)(?:^[A-Za-z]:[\\/]|[\\/]Users[\\/]|[\\/]home[\\/]|[\\/]tmp[\\/])")
_SAFE_RISK_FLAG_PATTERNS = (
    re.compile(r"^SFT cross-split leakage: \d+ heldout near-dups in train$"),
    re.compile(r"^DPO cross-split leakage: \d+$"),
    re.compile(r"^DPO length bias: chosen/rejected ratio \d+(?:\.\d+)?$"),
    re.compile(r"^\d+ dense single-corridor typologies \(>=\d+ rows, jurisdiction shortcut risk\)$"),
    re.compile(r"^\d+ gold replies assert phone-like fragile facts$"),
    re.compile(r"^\d+ gold replies cite real-but-irrelevant conventions$"),
)
_ARTIFACT_FILE_ORDER = [
    "data_manifest",
    "selected_sft",
    "selected_sft_manifest",
    "selected_dpo",
    "selected_dpo_manifest",
    "reasoning_gap_queue",
    "reasoning_repaired_rows",
    "reasoning_repaired_rows_manifest",
    "contract_dpo",
    "contract_dpo_manifest",
    "dpo_mix",
    "dpo_mix_manifest",
    "quality_audit",
    "corridor_expansion_plan",
    "corridor_expansion_plan_manifest",
]
_KNOWN_ARTIFACT_FILES = frozenset(_ARTIFACT_FILE_ORDER)
_SAFE_ARTIFACT_SCALAR = re.compile(r"^[A-Za-z0-9._/\-]{1,120}$")
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_MODEL_ID = re.compile(r"^[A-Za-z0-9._\-]+$")
_SAFE_METRIC_NAME = re.compile(r"^[A-Za-z0-9._/\- ]+$")
_SAFE_METRIC_VALUE = re.compile(r"^[A-Za-z0-9 ._:/%+\-()]+$")
_SAFE_HASHLIKE = re.compile(r"^[A-Fa-f0-9]{7,128}$")
_SAFE_SHA256 = re.compile(r"^[A-Fa-f0-9]{64}$")
_SAFE_CREATED_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$")
_LONG_DIGITS = re.compile(r"(?<!\d)\d{8,}(?!\d)")
_SAFE_STATUSES = frozenset({"planned", "trained", "evaluated", "exported", "published"})
_SAFE_ARTIFACT_ISSUES = frozenset({
    "fingerprint_mismatch",
    "malformed",
    "materialized_without_fingerprint",
    "missing_file",
    "unreadable_file",
    "unverifiable_path",
})


def _contains_sensitive_text(text: str) -> bool:
    return bool(_EMAIL.search(text) or _PHONE.search(text) or _LONG_DIGITS.search(text))


def _frontmatter(record: dict) -> str:
    base = _display_base_model(record.get("base_model", "unknown"))
    return "\n".join([
        "---",
        f"base_model: {base}",
        "license: mit",
        "library_name: peft",
        "language:",
        "- en",
        "tags:",
        "- gemma",
        "- lora",
        "- safety",
        "- migrant-worker-protection",
        "- trafficking",
        "- on-device",
        "---",
    ])


def _eval_section(record: dict) -> str:
    ev = record.get("eval") or {}
    if not ev:
        return ("_Pending the GPU four-arm evaluation_ (internalisation `C-A`, internalised fraction "
                "`(C-A)/(B-A)`, and the held-out-typology generalisation gap). Run "
                "`python scripts/training_engine.py --with-gpu`, which records the scores back into the "
                "registry; regenerate this card to fill this section.")
    rows: list[str] = []
    unknown_count = 0
    for key, value in ev.items():
        metric = _display_metric_name(key)
        if metric is None:
            unknown_count += 1
            metric = f"additional_metric_{unknown_count}"
        rows.append(f"| {metric} | `{_display_metric_value(value)}` |")
    if not rows:
        return "_Evaluation metrics were present, but no safe scalar values were publishable._"
    return "\n".join(["| metric | value |", "| --- | --- |", *rows])


def _safe_relative_artifact_path(path: pathlib.PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("/") or display.startswith("../") or "/../" in display:
        return "redacted"
    if _LOCAL_PATH_HINT.search(display):
        return "redacted"
    if _contains_sensitive_text(display):
        return "redacted"
    if not _SAFE_RELATIVE_PATH.fullmatch(display):
        return "redacted"
    return display


def _display_artifact_path(raw_path: Any) -> str:
    if not raw_path:
        return "n/a"
    raw = str(raw_path)
    try:
        path = pathlib.Path(raw)
        if path.is_absolute():
            try:
                return _safe_relative_artifact_path(path.relative_to(_ROOT))
            except ValueError:
                return "external"
        return _safe_relative_artifact_path(pathlib.PurePosixPath(pathlib.PureWindowsPath(raw).as_posix()))
    except (OSError, RuntimeError, ValueError):
        return "redacted"


def _display_model_id(model_id: Any) -> str:
    text = str(model_id or "")
    if _SAFE_MODEL_ID.fullmatch(text) and not _contains_sensitive_text(text):
        return text
    return "redacted"


def _display_base_model(base_model: Any) -> str:
    text = str(base_model or "")
    if not text:
        return "unknown"
    return _safe_relative_artifact_path(pathlib.PurePosixPath(pathlib.PureWindowsPath(text).as_posix()))


def _display_metric_name(name: Any) -> str | None:
    text = str(name or "").strip()
    if not text or len(text) > 80:
        return None
    if _contains_sensitive_text(text):
        return None
    if _LOCAL_PATH_HINT.search(text) or "\\" in text:
        return None
    if not _SAFE_METRIC_NAME.fullmatch(text):
        return None
    return text


def _display_metric_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value) if math.isfinite(value) else "redacted"
    if isinstance(value, str):
        text = value.strip()
        if not text or len(text) > 120:
            return "redacted"
        if _contains_sensitive_text(text):
            return "redacted"
        if _LOCAL_PATH_HINT.search(text) or "\\" in text:
            return "redacted"
        if not _SAFE_METRIC_VALUE.fullmatch(text):
            return "redacted"
        return text
    return "redacted"


def _display_status(status: Any) -> str:
    text = str(status or "")
    return text if text in _SAFE_STATUSES else "redacted"


def _display_hashlike(value: Any) -> str:
    if value is None:
        return "n/a"
    text = str(value or "").strip()
    if _SAFE_SHA256.fullmatch(text):
        return text
    if text.isdigit() and _LONG_DIGITS.search(text):
        return "redacted"
    return text if _SAFE_HASHLIKE.fullmatch(text) else "redacted"


def _display_sha256(value: Any) -> str:
    if value in (None, ""):
        return "missing"
    text = str(value or "").strip()
    if _SAFE_SHA256.fullmatch(text):
        return text
    if text.isdigit() and _LONG_DIGITS.search(text):
        return "redacted"
    return text if _SAFE_SHA256.fullmatch(text) else "redacted"


def _display_created_utc(value: Any) -> str:
    if value is None:
        return "n/a"
    text = str(value or "").strip()
    return text if _SAFE_CREATED_UTC.fullmatch(text) else "redacted"


def _display_nonnegative_int(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "redacted"
    if isinstance(value, int):
        return str(value) if value >= 0 else "redacted"
    return "redacted"


def _model_card_filename(model_id: Any) -> str:
    display = _display_model_id(model_id)
    if display != "redacted":
        return f"{display}_model_card.md"
    digest = hashlib.sha256(str(model_id or "").encode("utf-8")).hexdigest()[:12]
    return f"model_card_{digest}.md"


def _display_artifact_name(name: str, *, unknown_index: int) -> str:
    if name in _KNOWN_ARTIFACT_FILES:
        return name
    return f"additional_artifact_{unknown_index}"


def _safe_artifact_issue(value: Any) -> str:
    issue = str(value or "issue")
    return issue if issue in _SAFE_ARTIFACT_ISSUES else "issue"


def _sanitized_artifact_issues(issues: list[Any]) -> list[dict[str, str]]:
    sanitized: list[dict[str, str]] = []
    unknown_count = 0
    for issue in issues:
        if not isinstance(issue, dict):
            unknown_count += 1
            sanitized.append({"artifact": f"additional_artifact_{unknown_count}", "issue": "issue"})
            continue
        artifact = str(issue.get("artifact") or "?")
        if artifact not in _KNOWN_ARTIFACT_FILES:
            unknown_count += 1
        sanitized.append({
            "artifact": _display_artifact_name(artifact, unknown_index=unknown_count),
            "issue": _safe_artifact_issue(issue.get("issue")),
        })
    return sanitized


def _artifact_fingerprint_section(record: dict[str, Any]) -> str:
    artifacts = record.get("artifacts") or {}
    artifact_files = artifacts.get("artifact_files") or {}
    if not artifact_files:
        return "_No per-file artifact fingerprints were recorded in this registry entry._"

    order = set(_ARTIFACT_FILE_ORDER)
    ordered = [name for name in _ARTIFACT_FILE_ORDER if name in artifact_files]
    ordered.extend(sorted(name for name in artifact_files if name not in order))
    rows: list[str] = []
    unknown_count = 0
    for name in ordered:
        entry = artifact_files.get(name)
        if not isinstance(entry, dict):
            continue
        if name not in _KNOWN_ARTIFACT_FILES:
            unknown_count += 1
        display_name = _display_artifact_name(name, unknown_index=unknown_count)
        path = _display_artifact_path(entry.get("path"))
        sha256 = _display_sha256(entry.get("sha256"))
        bytes_display = _display_nonnegative_int(entry.get("bytes"))
        if bytes_display == "n/a":
            bytes_display = "missing"
        rows.append(f"| `{display_name}` | `{path}` | `{sha256}` | {bytes_display} |")
    if not rows:
        return "_No selected artifact files were recorded for this run._"
    return "\n".join([
        "These registry fingerprints identify the exact generated files used by this run. Paths are "
        "rendered repo-relative when possible so local workstation paths are not published.",
        "",
        "| artifact | path | sha256 | bytes |",
        "| --- | --- | --- | ---: |",
        *rows,
    ])


def _safe_artifact_scalar(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "n/a"
    if _contains_sensitive_text(text):
        return "redacted"
    if _LOCAL_PATH_HINT.search(text) or "\\" in text:
        return "redacted"
    return text if _SAFE_ARTIFACT_SCALAR.fullmatch(text) else "redacted"


def _training_configuration_section(record: dict[str, Any]) -> str:
    artifacts = record.get("artifacts") or {}
    rows = [
        ("SFT arm", _safe_artifact_scalar(artifacts.get("sft_variant"))),
        ("DPO arm", _safe_artifact_scalar(artifacts.get("dpo_variant"))),
        ("Reasoning repair mode", _safe_artifact_scalar(artifacts.get("reasoning_repair_mode"))),
    ]
    return "\n".join(
        ["| field | value |", "| --- | --- |"] +
        [f"| {name} | `{value}` |" for name, value in rows]
    )


def _display_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value) if value >= 0 else "redacted"
    if isinstance(value, float):
        return str(value) if math.isfinite(value) and value >= 0 else "redacted"
    return _display_metric_value(value)


def _safe_risk_flag(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    flag = value.strip()
    if not flag or len(flag) > 220:
        return None
    if _contains_sensitive_text(flag):
        return None
    return flag if any(pattern.fullmatch(flag) for pattern in _SAFE_RISK_FLAG_PATTERNS) else None


def _risk_flag_lines(summary: dict[str, Any]) -> str:
    safe: list[str] = []
    redacted = 0
    for flag in summary.get("risk_flags") or []:
        safe_flag = _safe_risk_flag(flag)
        if safe_flag is None:
            redacted += 1
        else:
            safe.append(f"- {safe_flag}")
    if redacted:
        safe.append(
            f"- {redacted} untrusted risk flag(s) redacted; inspect the local quality-audit artifact."
        )
    return "\n".join(safe) if safe else "- None recorded."


def _quality_audit_section(record: dict[str, Any]) -> str:
    artifacts = record.get("artifacts") or {}
    summary = artifacts.get("quality_audit_summary")
    if not isinstance(summary, dict):
        return "_No structured quality-audit summary was recorded in this registry entry._"

    rows = [
        ("clean", summary.get("clean")),
        ("SFT heldout near-dup leaks", summary.get("sft_leaked")),
        ("DPO heldout near-dup leaks", summary.get("dpo_leaked")),
        ("dense single-corridor typologies", summary.get("dense_single_corridor_typologies")),
        ("corridor expansion queue targets", summary.get("corridor_expansion_queue_count")),
        ("corridor expansion curation tasks", summary.get("corridor_expansion_task_count")),
        ("corridor queue privacy scan ok", summary.get("corridor_expansion_queue_privacy_ok")),
        ("corridor task privacy scan ok", summary.get("corridor_expansion_tasks_privacy_ok")),
        ("citation-incoherent gold replies", summary.get("citation_incoherent")),
        ("citation repair queue targets", summary.get("citation_repair_queue_count")),
        ("citation queue privacy scan ok", summary.get("citation_repair_queue_privacy_ok")),
        ("gold replies with phone-like strings", summary.get("gold_phone_like")),
    ]
    table = "\n".join(
        ["| check | value |", "| --- | --- |"] +
        [f"| {name} | `{_display_value(value)}` |" for name, value in rows]
    )
    return "\n".join([
        "This metadata-only summary comes from the pre-train audit; it records counts and risk flags, not "
        "raw prompts, answers, or worker details.",
        "",
        table,
        "",
        "Risk flags:",
        "",
        _risk_flag_lines(summary),
    ])


def _verification_failure_message(result: dict[str, Any]) -> str | None:
    if result.get("legacy_without_artifact_files"):
        return "registry record has no structured artifact_files payload to verify"
    issues = []
    for issue in _sanitized_artifact_issues(result.get("issues") or []):
        issues.append(f"{issue['artifact']}:{issue['issue']}")
    if issues:
        return "; ".join(issues)
    if result.get("checked", 0) == 0:
        return "registry record has no materialized artifact fingerprints to verify"
    return None


def render_card(record: dict[str, Any]) -> str:
    """Render a full model card (str) from a finetune_registry record. Pure -- no I/O."""
    data = record.get("data") or {}
    mid = _display_model_id(record.get("model_id", "unknown"))
    base = _display_base_model(record.get("base_model", "unknown"))
    provenance = "\n".join([
        "| field | value |",
        "| --- | --- |",
        f"| model_id | `{mid}` |",
        f"| base_model | `{base}` |",
        f"| status | {_display_status(record.get('status'))} |",
        f"| git_sha (code version) | `{_display_hashlike(record.get('git_sha'))}` |",
        f"| data_manifest_sha256 (dataset version) | `{_display_hashlike(data.get('manifest_sha256'))}` |",
        f"| created_utc | {_display_created_utc(record.get('created_utc'))} |",
    ])
    sft = _display_nonnegative_int(data.get("sft_examples"))
    dpo = _display_nonnegative_int(data.get("dpo_examples"))
    return "\n".join([
        _frontmatter(record),
        "",
        f"# {mid}",
        "",
        f"A LoRA fine-tune of `{base}` into an **on-device trafficking-safety judge** for migrant-worker "
        "protection. It is trained to answer like the DueCare harness: name the exploitation **indicator**, "
        "cite the controlling **law / ILO convention**, give a clear graded **action** (refuse to "
        "operationalize harm; tell the worker what to do), and point to protective **resources** -- never a "
        "bare refusal without details or citations.",
        "",
        "## Provenance (reproducible)",
        "",
        provenance,
        "",
        "Every number here is reproducible from `(git_sha, data_manifest_sha256)` -- the project's "
        '"real, not faked" invariant. The data manifest pins the exact distilled training set.',
        "",
        "## Artifact fingerprints",
        "",
        _artifact_fingerprint_section(record),
        "",
        "## Pre-train quality audit",
        "",
        _quality_audit_section(record),
        "",
        "## Training data",
        "",
        _training_configuration_section(record),
        "",
        f"- SFT examples: **{sft}**",
        f"- DPO examples: **{dpo}**",
        "- Distilled from the DueCare harness-lift benchmark (baseline vs harnessed grades), then gated so "
        "the lift teaches grounding, not refusal: a **grounding-delta** gate (the harnessed reply must add "
        "indicator+law+resources over baseline) and a **reasoning-chain** gate "
        "(indicator -> statute -> action -> resources). Exact + SimHash near-duplicate deduped; whole "
        "typologies held out for a generalisation diagnostic.",
        "",
        "## Evaluation",
        "",
        _eval_section(record),
        "",
        "## Intended use",
        "",
        "A private, local safety evaluator for NGOs and regulators who cannot send sensitive case data to "
        "frontier APIs. Runs on a laptop (llama.cpp / LiteRT). Use it to triage suspicious recruitment "
        "messages, flag ILO forced-labour indicators, and surface the controlling statute + protective "
        "resources.",
        "",
        "## Limitations & out-of-scope",
        "",
        "- **Not legal advice.** Outputs are decision support, not a determination.",
        "- **Volatile facts** (hotline numbers, current fee caps, fresh advisories) are intentionally NOT "
        "memorized -- they come from tools / retrieval, so the weights teach stable reasoning, not "
        "stale contacts.",
        "- Trained on synthetic + public benchmark data; coverage is strongest on the corridors and "
        "typologies in the training distribution.",
        "",
        "## Privacy boundary",
        "",
        "Raw worker chats, IDs, and documents stay on the local device. Only explicitly sanitized, "
        "anonymized envelopes are ever shared. The model itself adds no telemetry.",
        "",
        "## Citation",
        "",
        f"DueCare — Gemma 4 safety judge for migrant-worker protection. Model `{mid}`, base `{base}`.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-id", required=True, help="model_id to render (latest registry record wins)")
    ap.add_argument("--stdout", action="store_true", help="print the card instead of writing a file")
    ap.add_argument("--out-dir", type=pathlib.Path, default=OUT_DIR)
    ap.add_argument("--require-verified-artifacts", action="store_true",
                    help="fail unless recorded artifact_files match the current local files")
    args = ap.parse_args(argv)

    latest = _latest_by_id(_load_registry())
    record = latest.get(args.model_id)
    display_model_id = _display_model_id(args.model_id)
    if not record:
        have = ", ".join(_display_model_id(model_id) for model_id in sorted(latest)) or "(registry empty)"
        print(f"[model-card] no registry record for {display_model_id}; known: {have}")
        return 1
    verification = None
    if args.require_verified_artifacts:
        verification = _verify_record_artifacts(record)
        failure = _verification_failure_message(verification)
        if failure:
            print(f"[model-card] artifact verification failed for {display_model_id}: {failure}", file=sys.stderr)
            return 2
    card = render_card(record)
    if args.stdout:
        print(card)
        return 0
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / _model_card_filename(args.model_id)
    out.write_text(card, encoding="utf-8")
    verified = ""
    if verification is not None:
        verified = f", artifacts_verified={verification['matched']}/{verification['checked']}"
    print(f"[model-card] wrote {len(card)} chars -> {_display_artifact_path(out)} "
          f"(status={_display_status(record.get('status'))}, "
          f"data_sha={_display_hashlike((record.get('data') or {}).get('manifest_sha256'))}{verified})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
