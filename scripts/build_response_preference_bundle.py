#!/usr/bin/env python3
"""Build a sharded, candidate-only training bundle from measured response lift.

The legacy lift builder proves that a useful response-distillation signal exists,
but its in-memory join and compact ``_meta`` rows are not a large-corpus release
contract.  This builder keeps the useful selection rules while adding the
properties needed for a reviewable candidate bundle:

* index the small grade panel first, then stream a byte-bound snapshot of the
  large response log;
* recover every prompt exactly from the canonical benchmark prompt set;
* align baseline and harness-core responses to the same prompt;
* retain only grounded, high-lift, citation-coherent, privacy-clean final
  answers and reject hidden reasoning/scratchpad markup;
* deduplicate exact prompt clusters before assigning group-isolated splits;
* emit sharded SFT, DPO and reward-label lanes plus a raw-text-free response
  inventory and quarantine; and
* bind the candidate to source hashes while explicitly prohibiting reuse of the
  source benchmark as independent model-improvement evidence.

The output is deliberately candidate-only.  Generation can set
``safe_to_train`` when its executable gates pass, but it can never set
``publication_ready``.  A separate manifest-bound rights, privacy, curator and
publication approval is required before redistribution.

Examples::

    python scripts/build_response_preference_bundle.py plan
    python scripts/build_response_preference_bundle.py build --dry-run
    python scripts/build_response_preference_bundle.py build \
      --output-dir reports/response_preference_candidates/run-20260715
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

ROOT = Path(__file__).resolve().parents[1]
CHAT_SRC = ROOT / "packages" / "duecare-llm-chat" / "src"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(CHAT_SRC) not in sys.path:
    sys.path.insert(0, str(CHAT_SRC))

from build_lift_training_data import (  # noqa: E402
    FORMAT_FAILURE,
    _citation_coherence,
    _citation_stats,
    _classify,
    _display_report_path,
    _safe_prompt_id,
    scrub,
)
from duecare.chat.training_contract import (  # noqa: E402
    canonical_sha256,
    pii_findings,
    training_row_sha256,
)

GENERATOR_VERSION = "duecare-measured-response-preference/1.1.0"
SCHEMA_VERSION = "duecare.response-preference-candidate-bundle.v1"
ROW_LICENSE = "CC-BY-4.0"
RIGHTS_HOLDER = "DueCare project contributors"
PROMPT_CORPUS_LICENSE = "CC-BY-4.0"
DEFAULT_PANEL = ROOT / "reports" / "rich_lift" / "panel.jsonl"
DEFAULT_RESULTS = ROOT / "reports" / "rich_lift" / "results.jsonl"
DEFAULT_PROMPTSET = ROOT / "reports" / "benchmark" / "full_promptset.json"
DEFAULT_OUTPUT = ROOT / "reports" / "response_preference_candidates" / "candidate_bundle"
DEFAULT_TEACHER_ARM = "harness_core"
BASELINE_ARM = "baseline"
DEFAULT_MODEL_LICENSES: dict[str, str] = {
    "gemma4:31b": "Apache-2.0",
    "gpt-oss:120b": "Apache-2.0",
}

RUBRIC_DIMENSIONS: dict[str, str] = {
    "A": "indicator_identification",
    "B": "legal_grounding",
    "C": "protective_refusal",
    "D": "concrete_resources_and_actions",
    "E": "safety_and_privacy",
}
RUBRIC_COMPONENT_BOUNDS: dict[str, float] = {
    "A": 25.0,
    "B": 20.0,
    "C": 25.0,
    "D": 15.0,
    "E": 15.0,
}
RUBRIC_TARGETS = list(RUBRIC_DIMENSIONS.values())
METHOD_SOURCE_REFS = [
    "https://www.ilo.org/publications/ilo-indicators-forced-labour-1",
    "https://normlex.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE:C029",
    "repo:configs/duecare/legal_claims.json",
    "repo:scripts/build_lift_training_data.py",
]

_HIDDEN_REASONING = re.compile(
    r"<\|?(?:think|thought)(?:\|?>)|"
    r"<\|?channel\|?>\s*(?:analysis|thought)|"
    r"\b(?:hidden|private)\s+chain[- ]of[- ]thought\b|"
    r"\bprivate\s+scratchpad\b|"
    r"\b(?:analysis|reasoning)\s+scratchpad\b",
    re.I,
)
_UNSAFE_OPERATIONAL = re.compile(
    r"\b(?:hide\s+the\s+fee|evade\s+(?:the\s+)?law|avoid\s+detection|"
    r"optimi[sz]e\s+(?:wage|salary|fee|collection)|automatic\s+salary\s+deduction|"
    r"disguise\s+(?:the\s+)?(?:fee|loan)|structure\s+the\s+loan\s+to)\b",
    re.I,
)
_UNSAFE_NEGATION = re.compile(
    r"\b(?:cannot|can't|do\s+not|don't|must\s+not|refuse|unsafe|illegal)\b",
    re.I,
)
_SAFE_METADATA = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+() -]{0,255}$")
_VOLATILE_URL = re.compile(
    r"(?:https?://|www\.|\b[A-Z0-9-]+\.(?:gov|org|com|net|int)(?:\.[A-Z]{2,})?(?:/|\b))",
    re.I,
)
_VOLATILE_CONTACT = re.compile(
    r"\b(?:hotline|help\s*line|contact\s+(?:number|line)|"
    r"(?:phone|telephone)\s+number)\b",
    re.I,
)
_VOLATILE_CONTACT_NUMBER = re.compile(
    r"(?<!\w)(?:\+\d(?:[\s().-]*\d){7,14}|\d{10,14}|"
    r"(?:\(\d{2,4}\)|\d{2,4})[\s.-]\d{3,4}[\s.-]\d{3,4})(?!\w)"
)
_NAMED_OFFICE_OR_AGENCY = re.compile(
    r"\b(?:department|ministry|office|agency|authority|administration|bureau|"
    r"directorate|commission|embassy|consulate)\s+(?:of|for)\s+"
    r"[A-Z][-A-Za-z&.'\u2019]*(?:\s+[A-Z][-A-Za-z&.'\u2019]*){0,6}\b|"
    r"\b(?:DMW|POEA|OWWA|DOLE|DOJ|DOL|WHD|MOHRE|MEA|MADAD|DOFE|SLBFE|"
    r"BE&OE|MIGRANT\s+WORKERS\s+OFFICE)\b",
    re.I,
)


class BundleError(RuntimeError):
    """Raised when a source or destination cannot satisfy the fail-closed contract."""


@dataclass(frozen=True)
class Thresholds:
    min_target: float = 70.0
    min_lift: float = 20.0
    min_grounding: float = 24.0
    min_cite: float = 4.0
    min_grounding_delta: float = 2.0

    def as_dict(self) -> dict[str, float]:
        return {
            "min_target": self.min_target,
            "min_lift": self.min_lift,
            "min_grounding": self.min_grounding,
            "min_cite": self.min_cite,
            "min_grounding_delta": self.min_grounding_delta,
        }


DEFAULT_THRESHOLDS = Thresholds()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _json_line(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_metadata(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or not _SAFE_METADATA.fullmatch(text):
        return None
    if pii_findings(text):
        return None
    return text


def _exact_text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_target_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _target_text_hashes(text: str) -> dict[str, str]:
    return {
        "exact": _exact_text_sha256(text),
        "canonical": canonical_sha256(_canonical_target_text(text)),
    }


def _contains_unbound_volatile_resource(*texts: str) -> bool:
    """Return whether text names a volatile resource without a knowledge binding."""

    return any(
        pattern.search(text)
        for text in texts
        for pattern in (
            _VOLATILE_URL,
            _VOLATILE_CONTACT,
            _VOLATILE_CONTACT_NUMBER,
            _NAMED_OFFICE_OR_AGENCY,
        )
    )


def _complete_bounded_components(value: Any) -> dict[str, float] | None:
    if not isinstance(value, Mapping):
        return None
    components: dict[str, float] = {}
    for component, upper_bound in RUBRIC_COMPONENT_BOUNDS.items():
        raw_score = value.get(component)
        if isinstance(raw_score, bool):
            return None
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(score) or not 0.0 <= score <= upper_bound:
            return None
        components[component] = score
    return components


def _public_identifier(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, str) else str(value or "")
    safe = _safe_prompt_id(raw)
    return {"value": safe, "sha256": canonical_sha256(raw)}


def _mean(values: Sequence[float]) -> float:
    return round(statistics.mean(values), 1)


def _file_entry(path: Path, *, rows: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
    }
    if rows is not None:
        result["rows"] = rows
    return result


def _prepare_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise BundleError("output path exists and is not a directory")
        if any(output_dir.iterdir()):
            raise BundleError("output directory must be absent or empty")
    else:
        output_dir.mkdir(parents=True)


class ShardWriter:
    """Incrementally write deterministic JSONL shards and retain only file metadata."""

    def __init__(
        self,
        output_dir: Path,
        prefix: str,
        *,
        shard_rows: int,
        enabled: bool,
    ) -> None:
        self.output_dir = output_dir
        self.prefix = prefix
        self.shard_rows = max(1, shard_rows)
        self.enabled = enabled
        self.total_rows = 0
        self._handle: BinaryIO | None = None
        self._path: Path | None = None
        self._digest: Any = None
        self._rows_in_shard = 0
        self._bytes_in_shard = 0
        self.files: dict[str, dict[str, Any]] = {}

    def _open(self) -> None:
        index = len(self.files)
        self._path = self.output_dir / f"{self.prefix}-{index:05d}.jsonl"
        self._handle = self._path.open("xb")
        self._digest = hashlib.sha256()
        self._rows_in_shard = 0
        self._bytes_in_shard = 0

    def _close_current(self) -> None:
        if self._handle is None or self._path is None:
            return
        self._handle.close()
        self.files[self._path.name] = {
            "rows": self._rows_in_shard,
            "bytes": self._bytes_in_shard,
            "sha256": self._digest.hexdigest(),
        }
        self._handle = None
        self._path = None
        self._digest = None

    def write(self, row: Mapping[str, Any]) -> None:
        self.total_rows += 1
        if not self.enabled:
            return
        if self._handle is None:
            self._open()
        elif self._rows_in_shard >= self.shard_rows:
            self._close_current()
            self._open()
        payload = _json_line(row)
        assert self._handle is not None and self._digest is not None
        self._handle.write(payload)
        self._digest.update(payload)
        self._rows_in_shard += 1
        self._bytes_in_shard += len(payload)

    def close(self) -> None:
        self._close_current()


def load_promptset(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Load the canonical prompt set and reject conflicting IDs."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleError("prompt set is missing or invalid JSON") from exc
    rows = document.get("prompts") if isinstance(document, Mapping) else document
    if not isinstance(rows, list):
        raise BundleError("prompt set must be a list or contain a prompts list")
    prompts: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise BundleError(f"prompt set row {index} is not an object")
        prompt_id = row.get("id")
        text = row.get("text")
        if not isinstance(prompt_id, str) or not prompt_id or not isinstance(text, str) or not text:
            raise BundleError(f"prompt set row {index} is missing id or text")
        normalized = {
            "id": prompt_id,
            "text": text,
            "category": _safe_metadata(row.get("category")) or "unknown",
            "corridor": _safe_metadata(row.get("corridor")) or "unknown",
            "source": _safe_metadata(row.get("source")) or "unknown",
            "difficulty": _safe_metadata(row.get("difficulty")) or "unknown",
        }
        previous = prompts.get(prompt_id)
        if previous is not None and previous != normalized:
            raise BundleError("prompt set contains conflicting duplicate IDs")
        prompts[prompt_id] = normalized
    return prompts, {
        "path": _display_report_path(path),
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
        "prompt_count": len(prompts),
    }


def index_panel(path: Path) -> tuple[dict[tuple[str, str, str], dict[str, Any]], dict[str, Any]]:
    """Index score/component evidence without loading response bodies."""

    accumulators: dict[tuple[str, str, str], dict[str, Any]] = {}
    malformed = non_object = invalid_grade = 0
    digest = hashlib.sha256()
    rows = 0
    try:
        handle = path.open("rb")
    except OSError as exc:
        raise BundleError("grade panel is missing") from exc
    with handle:
        for raw in handle:
            digest.update(raw)
            if not raw.strip():
                continue
            try:
                row = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                malformed += 1
                continue
            if not isinstance(row, Mapping):
                non_object += 1
                continue
            try:
                model = str(row["model"])
                prompt_id = str(row["prompt_id"])
                arm = str(row["arm"])
                raw_score = row["score_0_100"]
                if isinstance(raw_score, bool):
                    raise ValueError("boolean grade")
                score = float(raw_score)
            except (KeyError, TypeError, ValueError):
                invalid_grade += 1
                continue
            component_row = _complete_bounded_components(row.get("components"))
            if not math.isfinite(score) or not 0.0 <= score <= 100.0 or component_row is None:
                invalid_grade += 1
                continue
            rows += 1
            key = (model, prompt_id, arm)
            acc = accumulators.setdefault(
                key,
                {"scores": [], "components": defaultdict(list), "judges": []},
            )
            acc["scores"].append(score)
            for component, value in component_row.items():
                acc["components"][component].append(value)
            judge_identity = _public_identifier(row.get("judge"))
            acc["judges"].append(
                {
                    "judge": judge_identity["value"],
                    "judge_sha256": judge_identity["sha256"],
                    "score_0_100": score,
                    "components": component_row,
                }
            )

    grades: dict[tuple[str, str, str], dict[str, Any]] = {}
    for key, acc in accumulators.items():
        grades[key] = {
            "mean_score_0_100": _mean(acc["scores"]),
            "mean_components": {
                component: _mean(values)
                for component, values in sorted(acc["components"].items())
                if values
            },
            "judge_rows": sorted(
                acc["judges"],
                key=lambda item: (
                    str(item.get("judge") or ""),
                    str(item.get("judge_sha256") or ""),
                ),
            ),
        }
    return grades, {
        "path": _display_report_path(path),
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "valid_rows": rows,
        "malformed_rows": malformed,
        "non_object_rows": non_object,
        "invalid_grade_rows": invalid_grade,
        "graded_keys": len(grades),
    }


def _paired_grade_specs(
    grades: Mapping[tuple[str, str, str], Mapping[str, Any]],
    *,
    teacher_arm: str,
    thresholds: Thresholds,
    model_licenses: Mapping[str, str],
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_pair: dict[tuple[str, str], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for (model, prompt_id, arm), grade in grades.items():
        by_pair[(model, prompt_id)][arm] = grade
    prequalified: dict[tuple[str, str], dict[str, Any]] = {}
    rights_pending: list[dict[str, Any]] = []
    counts = Counter()
    by_model = Counter()
    for (model, prompt_id), arms in sorted(by_pair.items()):
        if BASELINE_ARM not in arms or teacher_arm not in arms:
            continue
        counts["paired"] += 1
        by_model[model] += 1
        identity = _public_identifier(prompt_id)
        if model not in model_licenses:
            counts["rights_pending"] += 1
            rights_pending.append(
                {
                    "schema_version": "duecare.response-quarantine.v1",
                    "contains_raw_text": False,
                    "model": _safe_metadata(model),
                    "model_sha256": canonical_sha256(model),
                    "prompt_id": identity["value"],
                    "prompt_id_sha256": identity["sha256"],
                    "reason_codes": ["provider_output_rights_pending"],
                    "rights_status": "pending_model_output_review",
                }
            )
            continue
        baseline = arms[BASELINE_ARM]
        target = arms[teacher_arm]
        baseline_score = float(baseline["mean_score_0_100"])
        target_score = float(target["mean_score_0_100"])
        lift = round(target_score - baseline_score, 1)
        if target_score < thresholds.min_target:
            counts["below_target"] += 1
            continue
        if lift < thresholds.min_lift:
            counts["below_lift"] += 1
            continue
        counts["score_prequalified"] += 1
        prequalified[(model, prompt_id)] = {
            "model": model,
            "prompt_id": prompt_id,
            "baseline": baseline,
            "target": target,
            "baseline_score": baseline_score,
            "target_score": target_score,
            "lift": lift,
        }
    return (
        prequalified,
        rights_pending,
        {
            "counts": dict(sorted(counts.items())),
            "paired_by_model": dict(sorted(by_model.items())),
        },
    )


def plan_bundle(
    *,
    panel_path: Path,
    promptset_path: Path,
    teacher_arm: str = DEFAULT_TEACHER_ARM,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
    model_licenses: Mapping[str, str] = DEFAULT_MODEL_LICENSES,
) -> dict[str, Any]:
    """Return a CPU-cheap plan; deliberately does not open the response log."""

    prompts, prompt_source = load_promptset(promptset_path)
    grades, panel_source = index_panel(panel_path)
    prequalified, rights_pending, summary = _paired_grade_specs(
        grades,
        teacher_arm=teacher_arm,
        thresholds=thresholds,
        model_licenses=model_licenses,
    )
    recoverable = sum(prompt_id in prompts for _, prompt_id in prequalified)
    return {
        "schema_version": "duecare.response-preference-plan.v1",
        "generator_version": GENERATOR_VERSION,
        "mode": "plan_no_results_scan",
        "arms": {"baseline": BASELINE_ARM, "teacher": teacher_arm},
        "thresholds": thresholds.as_dict(),
        "allowed_models": dict(sorted(model_licenses.items())),
        "prompt_source": prompt_source,
        "panel_source": panel_source,
        "grade_pair_summary": summary,
        "score_prequalified_pairs": len(prequalified),
        "score_prequalified_prompt_ids_recoverable": recoverable,
        "rights_pending_pairs": len(rights_pending),
        "next_step": (
            "run build or build --dry-run to stream the response snapshot and apply content gates"
        ),
        "publication_ready": False,
    }


def _inventory_status(
    *,
    key: tuple[str, str, str],
    grades: Mapping[tuple[str, str, str], Mapping[str, Any]],
    prequalified: Mapping[tuple[str, str], Mapping[str, Any]],
    model_licenses: Mapping[str, str],
    teacher_arm: str,
) -> tuple[str, str | None]:
    model, prompt_id, arm = key
    if model not in model_licenses:
        return "rights_pending", "provider_output_rights_pending"
    if key not in grades:
        return "ungraded", "ungraded_pending_panel"
    if arm not in {BASELINE_ARM, teacher_arm}:
        return "graded_auxiliary_arm", None
    if (model, prompt_id) in prequalified:
        return "score_prequalified", None
    return "graded_not_score_prequalified", None


def _inventory_row(
    *,
    row: Mapping[str, Any],
    line_number: int,
    byte_start: int,
    byte_end: int,
    prompt_metadata: Mapping[str, Any] | None,
    recovery: str,
    status: str,
    quarantine_reason: str | None,
    model_licenses: Mapping[str, str],
) -> dict[str, Any]:
    model_raw = str(row.get("model") or "")
    prompt_id_raw = str(row.get("prompt_id") or "")
    arm_raw = str(row.get("arm") or "")
    prompt = row.get("prompt_text") if isinstance(row.get("prompt_text"), str) else ""
    response = row.get("response") if isinstance(row.get("response"), str) else ""
    identity = _public_identifier(prompt_id_raw)
    result: dict[str, Any] = {
        "schema_version": "duecare.response-log-inventory.v1",
        "source_line": line_number,
        "source_byte_start": byte_start,
        "source_byte_end": byte_end,
        "model": _safe_metadata(model_raw),
        "model_sha256": canonical_sha256(model_raw),
        "model_output_license": model_licenses.get(model_raw),
        "rights_status": (
            "allowlisted_candidate_pending_publication_review"
            if model_raw in model_licenses
            else "provider_output_rights_pending"
        ),
        "prompt_id": identity["value"],
        "prompt_id_sha256": identity["sha256"],
        "arm": _safe_metadata(arm_raw),
        "prompt_sha256": canonical_sha256(prompt) if prompt else None,
        "response_sha256": canonical_sha256(response) if response else None,
        "prompt_chars": len(prompt),
        "response_chars": len(response),
        "response_nonempty": bool(response.strip()),
        "prompt_recovery": recovery,
        "grading_status": status,
        "quarantine_reason": quarantine_reason,
        "contains_raw_text": False,
    }
    if prompt_metadata is not None:
        result.update(
            {
                "prompt_category": prompt_metadata["category"],
                "corridor": prompt_metadata["corridor"],
                "prompt_source": prompt_metadata["source"],
            }
        )
    result["sha256"] = training_row_sha256(result)
    return result


def stream_results_snapshot(
    *,
    path: Path,
    prompts: Mapping[str, Mapping[str, Any]],
    grades: Mapping[tuple[str, str, str], Mapping[str, Any]],
    prequalified: Mapping[tuple[str, str], Mapping[str, Any]],
    teacher_arm: str,
    model_licenses: Mapping[str, str],
    inventory_writer: ShardWriter,
) -> tuple[dict[tuple[str, str, str], dict[str, str]], set[tuple[str, str, str]], dict[str, Any]]:
    """Stream one byte-prefix snapshot and retain bodies only for prequalified pairs."""

    try:
        stat_start = path.stat()
        handle = path.open("rb")
    except OSError as exc:
        raise BundleError("response log is missing") from exc
    snapshot_bytes = stat_start.st_size
    remaining = snapshot_bytes
    digest = hashlib.sha256()
    needed = {
        (model, prompt_id, arm)
        for model, prompt_id in prequalified
        for arm in (BASELINE_ARM, teacher_arm)
    }
    retained: dict[tuple[str, str, str], dict[str, str]] = {}
    ambiguous: set[tuple[str, str, str]] = set()
    counters = Counter()
    line_number = 0
    byte_offset = 0
    with handle:
        while remaining > 0:
            byte_start = byte_offset
            raw = handle.readline(remaining)
            if not raw:
                break
            remaining -= len(raw)
            byte_offset += len(raw)
            digest.update(raw)
            line_number += 1
            if not raw.endswith(b"\n"):
                counters["trailing_partial_rows"] += 1
                break
            if not raw.strip():
                continue
            try:
                row = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                counters["malformed_rows"] += 1
                continue
            if not isinstance(row, Mapping):
                counters["non_object_rows"] += 1
                continue
            counters["valid_object_rows"] += 1
            model = str(row.get("model") or "")
            prompt_id = str(row.get("prompt_id") or "")
            arm = str(row.get("arm") or "")
            key = (model, prompt_id, arm)
            prompt_text = row.get("prompt_text") if isinstance(row.get("prompt_text"), str) else ""
            response = row.get("response") if isinstance(row.get("response"), str) else ""
            prompt_metadata = prompts.get(prompt_id)
            if prompt_metadata is None:
                recovery = "missing_prompt_id"
                counters["prompt_id_missing"] += 1
            elif prompt_text != prompt_metadata["text"]:
                recovery = "prompt_text_mismatch"
                counters["prompt_text_mismatch"] += 1
            else:
                recovery = "exact"
                counters["prompt_recovery_exact"] += 1
            status, quarantine_reason = _inventory_status(
                key=key,
                grades=grades,
                prequalified=prequalified,
                model_licenses=model_licenses,
                teacher_arm=teacher_arm,
            )
            if recovery != "exact":
                quarantine_reason = recovery
            elif not response.strip():
                quarantine_reason = "empty_or_non_string_response"
            inventory_writer.write(
                _inventory_row(
                    row=row,
                    line_number=line_number,
                    byte_start=byte_start,
                    byte_end=byte_offset,
                    prompt_metadata=prompt_metadata,
                    recovery=recovery,
                    status=status,
                    quarantine_reason=quarantine_reason,
                    model_licenses=model_licenses,
                )
            )
            if key not in needed:
                continue
            value = {"prompt_text": prompt_text, "response": response}
            previous = retained.get(key)
            if previous is not None and previous != value:
                ambiguous.add(key)
                counters["conflicting_duplicate_keys"] += 1
                retained.pop(key, None)
                continue
            if key not in ambiguous:
                retained[key] = value
                if previous is not None:
                    counters["identical_duplicate_keys"] += 1
    stat_end = path.stat()
    return (
        retained,
        ambiguous,
        {
            "path": _display_report_path(path),
            "snapshot_kind": "immutable_byte_prefix_of_append_only_log",
            "snapshot_bytes": snapshot_bytes,
            "snapshot_sha256": digest.hexdigest(),
            "size_after_scan": stat_end.st_size,
            "changed_during_scan": stat_end.st_size != snapshot_bytes
            or stat_end.st_mtime_ns != stat_start.st_mtime_ns,
            "counters": dict(sorted(counters.items())),
            "retained_candidate_response_keys": len(retained),
            "ambiguous_candidate_response_keys": len(ambiguous),
        },
    )


def _quarantine_record(
    *,
    model: str,
    prompt_id: str,
    reasons: Sequence[str],
    prompt_sha256: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    identity = _public_identifier(prompt_id)
    row: dict[str, Any] = {
        "schema_version": "duecare.response-quarantine.v1",
        "contains_raw_text": False,
        "model": _safe_metadata(model),
        "model_sha256": canonical_sha256(model),
        "prompt_id": identity["value"],
        "prompt_id_sha256": identity["sha256"],
        "prompt_sha256": prompt_sha256,
        "reason_codes": sorted(set(reasons)),
    }
    if details:
        row["details"] = dict(details)
    row["sha256"] = training_row_sha256(row)
    return row


def _component_evidence(spec: Mapping[str, Any]) -> tuple[list[dict[str, Any]], float | None]:
    baseline = spec["baseline"].get("mean_components") or {}
    target = spec["target"].get("mean_components") or {}
    evidence: list[dict[str, Any]] = []
    for component, name in RUBRIC_DIMENSIONS.items():
        if component not in baseline or component not in target:
            continue
        before = float(baseline[component])
        after = float(target[component])
        evidence.append(
            {
                "dimension_id": component,
                "dimension": name,
                "baseline": before,
                "target": after,
                "delta": round(after - before, 1),
            }
        )
    if all(component in baseline and component in target for component in ("A", "B", "D")):
        grounding_delta = round(
            sum(float(target[component]) for component in ("A", "B", "D"))
            - sum(float(baseline[component]) for component in ("A", "B", "D")),
            1,
        )
    else:
        grounding_delta = None
    return evidence, grounding_delta


def _quality_evidence(
    spec: Mapping[str, Any],
    *,
    thresholds: Thresholds,
    teacher_arm: str,
) -> dict[str, Any]:
    component_deltas, grounding_delta = _component_evidence(spec)
    model = str(spec["model"])
    prompt_id = str(spec["prompt_id"])
    baseline_components = spec["baseline"].get("mean_components") or {}
    target_components = spec["target"].get("mean_components") or {}
    complete_bounded = (
        _complete_bounded_components(baseline_components) is not None
        and _complete_bounded_components(target_components) is not None
        and len(component_deltas) == len(RUBRIC_COMPONENT_BOUNDS)
    )
    result = {
        "gate_version": "build_lift_training_data_parity_plus_release_safety_v2",
        "baseline_arm": BASELINE_ARM,
        "teacher_arm": teacher_arm,
        "baseline_mean_score_0_100": spec["baseline_score"],
        "target_mean_score_0_100": spec["target_score"],
        "score_lift": spec["lift"],
        "component_bounds": RUBRIC_COMPONENT_BOUNDS,
        "complete_bounded_components": complete_bounded,
        "baseline_components": baseline_components,
        "target_components": target_components,
        "failure_dimension_deltas": component_deltas,
        "grounding_delta": grounding_delta,
        "source_grade_key_binding": {
            "model": model,
            "prompt_id_sha256": canonical_sha256(prompt_id),
            "baseline_arm": BASELINE_ARM,
            "teacher_arm": teacher_arm,
            "method": (
                "unique_model_prompt_arm_key_within_manifest_bound_panel_and_response_snapshot"
            ),
        },
        "judge_provenance": {
            "baseline": spec["baseline"].get("judge_rows") or [],
            "target": spec["target"].get("judge_rows") or [],
        },
        "thresholds": thresholds.as_dict(),
    }
    result["evidence_sha256"] = canonical_sha256(result)
    return result


def _has_complete_bounded_grade_evidence(candidate: Mapping[str, Any]) -> bool:
    evidence = candidate.get("quality_evidence")
    if not isinstance(evidence, Mapping) or evidence.get("complete_bounded_components") is not True:
        return False
    if _complete_bounded_components(evidence.get("baseline_components")) is None:
        return False
    if _complete_bounded_components(evidence.get("target_components")) is None:
        return False
    deltas = evidence.get("failure_dimension_deltas")
    if not isinstance(deltas, list) or {
        row.get("dimension_id") for row in deltas if isinstance(row, Mapping)
    } != set(RUBRIC_COMPONENT_BOUNDS):
        return False
    binding = evidence.get("source_grade_key_binding")
    return (
        isinstance(binding, Mapping)
        and set(binding)
        == {
            "model",
            "prompt_id_sha256",
            "baseline_arm",
            "teacher_arm",
            "method",
        }
        and binding.get("model") == candidate.get("model")
        and binding.get("prompt_id_sha256")
        == canonical_sha256(str(candidate.get("prompt_id") or ""))
        and binding.get("baseline_arm") == BASELINE_ARM
        and binding.get("teacher_arm") == candidate.get("quality_evidence", {}).get("teacher_arm")
        and binding.get("method")
        == "unique_model_prompt_arm_key_within_manifest_bound_panel_and_response_snapshot"
    )


def _has_valid_grade_evidence_binding(candidate: Mapping[str, Any]) -> bool:
    quality_evidence_sha256 = candidate.get("quality_evidence_sha256")
    source_response_sha256 = candidate.get("source_response_sha256")
    training_response_sha256 = candidate.get("training_response_sha256")
    if (
        not isinstance(quality_evidence_sha256, str)
        or len(quality_evidence_sha256) != 64
        or not isinstance(source_response_sha256, Mapping)
        or not isinstance(training_response_sha256, Mapping)
    ):
        return False
    expected = canonical_sha256(
        {
            "quality_evidence_sha256": quality_evidence_sha256,
            "source_response_sha256": source_response_sha256,
            "training_response_sha256": training_response_sha256,
        }
    )
    return candidate.get("grade_evidence_binding_sha256") == expected


def _candidate_rank(
    candidate: Mapping[str, Any], model_priority: Mapping[str, int]
) -> tuple[Any, ...]:
    quality = candidate["quality_evidence"]
    grounding = quality.get("grounding_delta")
    return (
        float(quality["target_mean_score_0_100"]),
        float(quality["score_lift"]),
        float(grounding) if grounding is not None else -1.0,
        -int(model_priority.get(str(candidate["model"]), 10_000)),
        str(candidate["model"]),
    )


def _target_fingerprints(candidate: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    fingerprints = candidate.get("target_text_sha256")
    if not isinstance(fingerprints, Mapping):
        return []
    result: list[tuple[str, str, str]] = []
    for role in ("chosen", "rejected"):
        role_hashes = fingerprints.get(role)
        if not isinstance(role_hashes, Mapping):
            continue
        for kind in ("exact", "canonical"):
            digest = role_hashes.get(kind)
            if isinstance(digest, str) and len(digest) == 64:
                result.append((kind, digest, role))
    return result


def _deduplicate_target_texts(
    candidates: Mapping[str, Mapping[str, Any]],
    *,
    model_priority: Mapping[str, int],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Retain the best candidate for every exact or canonical target body."""

    ranked = sorted(
        candidates.items(),
        key=lambda item: (_candidate_rank(item[1], model_priority), item[0]),
        reverse=True,
    )
    used: dict[tuple[str, str], tuple[str, str]] = {}
    kept: dict[str, dict[str, Any]] = {}
    dropped: list[dict[str, Any]] = []
    collision_counts = Counter()
    for cluster_id, raw_candidate in ranked:
        candidate = dict(raw_candidate)
        fingerprints = _target_fingerprints(candidate)
        collisions = [
            (kind, digest, role, *used[(kind, digest)])
            for kind, digest, role in fingerprints
            if (kind, digest) in used
        ]
        if collisions:
            collision_kinds = sorted({collision[0] for collision in collisions})
            for kind in collision_kinds:
                collision_counts[f"{kind}_candidate_drops"] += 1
            collision_counts["candidate_drops"] += 1
            dropped.append(
                {
                    "candidate": candidate,
                    "collision_kinds": collision_kinds,
                    "kept_cluster_ids": sorted({collision[3] for collision in collisions}),
                    "kept_roles": sorted({collision[4] for collision in collisions}),
                }
            )
            continue
        kept[cluster_id] = candidate
        for kind, digest, role in fingerprints:
            used[(kind, digest)] = (cluster_id, role)
    collision_counts["input_candidates"] = len(candidates)
    collision_counts["retained_candidates"] = len(kept)
    collision_counts["unique_exact_target_hashes"] = len(
        {digest for kind, digest in used if kind == "exact"}
    )
    collision_counts["unique_canonical_target_hashes"] = len(
        {digest for kind, digest in used if kind == "canonical"}
    )
    return kept, dropped, dict(sorted(collision_counts.items()))


def _build_candidate(
    *,
    spec: Mapping[str, Any],
    responses: Mapping[tuple[str, str, str], Mapping[str, str]],
    ambiguous: set[tuple[str, str, str]],
    prompt_metadata: Mapping[str, Any] | None,
    thresholds: Thresholds,
    teacher_arm: str,
    model_license: str,
) -> tuple[dict[str, Any] | None, list[str], int]:
    model = str(spec["model"])
    prompt_id = str(spec["prompt_id"])
    baseline_key = (model, prompt_id, BASELINE_ARM)
    target_key = (model, prompt_id, teacher_arm)
    reasons: list[str] = []
    if baseline_key in ambiguous or target_key in ambiguous:
        reasons.append("ambiguous_duplicate_response_key")
    baseline = responses.get(baseline_key)
    target = responses.get(target_key)
    if baseline is None or target is None:
        reasons.append("missing_aligned_response")
        return None, reasons, 0
    if prompt_metadata is None:
        reasons.append("prompt_id_not_in_canonical_promptset")
        return None, reasons, 0
    source_prompt = str(prompt_metadata["text"])
    if baseline["prompt_text"] != source_prompt or target["prompt_text"] != source_prompt:
        reasons.append("prompt_recovery_or_same_prompt_failure")
    baseline_response = baseline["response"]
    target_response = target["response"]
    # Candidate text is always emitted byte-for-byte as graded. Scrubbing is a
    # detection pass only; any would-be modification quarantines the whole pair.
    prompt = source_prompt
    chosen = target_response
    rejected = baseline_response
    if not rejected.strip() or not chosen.strip():
        reasons.append("empty_response")
    if rejected.strip() == chosen.strip():
        reasons.append("preference_pair_identical")
    if _canonical_target_text(rejected) == _canonical_target_text(chosen):
        reasons.append("within_pair_target_text_overlap")
    if any(_HIDDEN_REASONING.search(text) for text in (prompt, chosen, rejected)):
        reasons.append("hidden_reasoning_or_scratchpad_markup")
    if chosen.strip():
        _useful, format_reason = _classify(chosen)
        if format_reason in FORMAT_FAILURE:
            reasons.append("format_failure")
    target_components = spec["target"].get("mean_components") or {}
    baseline_components = spec["baseline"].get("mean_components") or {}
    if target_components:
        grounding = sum(
            float(target_components.get(component, 0.0)) for component in ("A", "B", "D")
        )
        if (
            grounding < thresholds.min_grounding
            or float(target_components.get("B", 0.0)) < thresholds.min_cite
        ):
            reasons.append("low_grounding")
    grounding_delta: float | None = None
    if target_components and baseline_components:
        grounding_delta = round(
            sum(float(target_components.get(component, 0.0)) for component in ("A", "B", "D"))
            - sum(float(baseline_components.get(component, 0.0)) for component in ("A", "B", "D")),
            1,
        )
        if grounding_delta < thresholds.min_grounding_delta:
            reasons.append("low_grounding_delta")
    citation = _citation_stats(chosen)
    if citation["n_section_implausible"] > 0 or citation["n_conventions_implausible"] > 0:
        reasons.append("implausible_citation")
    coherence = _citation_coherence(chosen)
    if not coherence["coherent"]:
        reasons.append("irrelevant_citation")
    operational = bool(_UNSAFE_OPERATIONAL.search(chosen))
    if operational and not _UNSAFE_NEGATION.search(chosen):
        reasons.append("unsafe_operational_target")
    if _contains_unbound_volatile_resource(prompt, chosen, rejected):
        reasons.append("volatile_resource_without_versioned_object")
    _scrubbed_prompt, prompt_redactions = scrub(prompt)
    _scrubbed_chosen, chosen_redactions = scrub(chosen)
    _scrubbed_rejected, rejected_redactions = scrub(rejected)
    redactions = prompt_redactions + chosen_redactions + rejected_redactions
    if redactions:
        reasons.append("pii_redaction_required_for_graded_text")
    if pii_findings({"prompt": prompt, "chosen": chosen, "rejected": rejected}):
        reasons.append("pii_in_exact_graded_text")
    if reasons:
        return None, sorted(set(reasons)), redactions
    training_prompt_sha256 = canonical_sha256(prompt)
    source_prompt_sha256 = canonical_sha256(source_prompt)
    cluster_id = f"prompt-cluster:{training_prompt_sha256}"
    quality = _quality_evidence(spec, thresholds=thresholds, teacher_arm=teacher_arm)
    source_response_sha256 = {
        "baseline": _exact_text_sha256(baseline_response),
        "teacher": _exact_text_sha256(target_response),
    }
    training_response_sha256 = {
        "rejected": _exact_text_sha256(rejected),
        "chosen": _exact_text_sha256(chosen),
    }
    grade_evidence_binding_sha256 = canonical_sha256(
        {
            "quality_evidence_sha256": quality["evidence_sha256"],
            "source_response_sha256": source_response_sha256,
            "training_response_sha256": training_response_sha256,
        }
    )
    return (
        {
            "model": model,
            "model_license": model_license,
            "prompt_id": prompt_id,
            "prompt": prompt,
            "chosen": chosen,
            "rejected": rejected,
            "source_prompt_sha256": source_prompt_sha256,
            "training_prompt_sha256": training_prompt_sha256,
            "cluster_id": cluster_id,
            "category": prompt_metadata["category"],
            "corridor": prompt_metadata["corridor"],
            "prompt_source": prompt_metadata["source"],
            "difficulty": prompt_metadata["difficulty"],
            "quality_evidence": quality,
            "quality_evidence_sha256": quality["evidence_sha256"],
            "source_response_sha256": source_response_sha256,
            "training_response_sha256": training_response_sha256,
            "grade_evidence_binding_sha256": grade_evidence_binding_sha256,
            "target_text_sha256": {
                "chosen": _target_text_hashes(chosen),
                "rejected": _target_text_hashes(rejected),
            },
            "pii_redactions": 0,
        },
        [],
        redactions,
    )


def _split_assignments(
    cluster_ids: Iterable[str],
    *,
    validation_fraction: float,
    test_fraction: float,
    split_seed: str,
) -> dict[str, str]:
    if validation_fraction < 0 or test_fraction < 0 or validation_fraction + test_fraction >= 1:
        raise BundleError("validation/test fractions must be non-negative and sum to less than one")
    assignments: dict[str, str] = {}
    scale = float(1 << 64)
    for cluster_id in sorted(set(cluster_ids)):
        digest = hashlib.sha256(f"{split_seed}|{cluster_id}".encode()).digest()
        point = int.from_bytes(digest[:8], "big") / scale
        if point < test_fraction:
            split = "test"
        elif point < test_fraction + validation_fraction:
            split = "validation"
        else:
            split = "train"
        assignments[cluster_id] = split
    return assignments


def _common_row_fields(
    candidate: Mapping[str, Any],
    *,
    split: str,
    created_at: str,
    row_license: str,
    rights_holder: str,
) -> dict[str, Any]:
    prompt_id = str(candidate["prompt_id"])
    model = str(candidate["model"])
    cluster_id = str(candidate["cluster_id"])
    return {
        "source_profile": "measured_harness_response_distillation",
        "rubric_targets": RUBRIC_TARGETS,
        "synthetic": True,
        "pii_checked": True,
        "lineage_family_id": cluster_id,
        "split": split,
        "license": row_license,
        "rights_holder": rights_holder,
        "rights_basis": {
            "prompt_corpus_license": PROMPT_CORPUS_LICENSE,
            "response_model_license": candidate["model_license"],
            "dataset_row_license": row_license,
            "publication_status": "separate_manifest_bound_approval_required",
        },
        "allow_training_use": split == "train",
        "allow_public_redistribution": False,
        "publication_approval_required": True,
        "prompt_id": _safe_prompt_id(prompt_id),
        "prompt_id_sha256": canonical_sha256(prompt_id),
        "source_prompt_sha256": candidate["source_prompt_sha256"],
        "training_prompt_sha256": candidate["training_prompt_sha256"],
        "prompt_cluster_id": cluster_id,
        "prompt_category": candidate["category"],
        "corridor": candidate["corridor"],
        "prompt_source": candidate["prompt_source"],
        "difficulty": candidate["difficulty"],
        "teacher_model": model,
        "teacher_model_license": candidate["model_license"],
        "teacher_model_revision_status": "recorded_local_model_tag_not_immutable_revision",
        "teacher_arm": DEFAULT_TEACHER_ARM,
        "baseline_arm": BASELINE_ARM,
        "source_response_sha256": candidate["source_response_sha256"],
        "training_response_sha256": candidate["training_response_sha256"],
        "target_text_sha256": candidate["target_text_sha256"],
        "quality_evidence": candidate["quality_evidence"],
        "quality_evidence_sha256": candidate["quality_evidence_sha256"],
        "grade_evidence_binding_sha256": candidate["grade_evidence_binding_sha256"],
        "source_refs": [
            *METHOD_SOURCE_REFS,
            (
                "repo:reports/benchmark/full_promptset.json#prompt_id="
                f"{_safe_prompt_id(prompt_id) or canonical_sha256(prompt_id)}"
            ),
        ],
        "generator_version": GENERATOR_VERSION,
        "created_at": created_at,
    }


def _training_rows(
    candidate: Mapping[str, Any],
    *,
    split: str,
    created_at: str,
    row_license: str,
    rights_holder: str,
    teacher_arm: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    common = _common_row_fields(
        candidate,
        split=split,
        created_at=created_at,
        row_license=row_license,
        rights_holder=rights_holder,
    )
    common["teacher_arm"] = teacher_arm
    base_id = canonical_sha256(
        {
            "cluster": candidate["cluster_id"],
            "model": candidate["model"],
            "teacher_arm": teacher_arm,
        }
    )[:24]
    checks = {
        "same_prompt_pair": True,
        "canonical_prompt_recovery": True,
        "score_and_lift_thresholds": True,
        "grounding_thresholds": True,
        "complete_bounded_grade_evidence": True,
        "format_answered": True,
        "citation_plausible_and_relevant": True,
        "pii_absent_without_redaction": True,
        "graded_text_emitted_verbatim": True,
        "hidden_reasoning_absent": True,
        "unsafe_operational_target_absent": True,
        "volatile_resource_has_versioned_binding_or_is_absent": True,
        "target_text_exact_and_canonical_dedup": True,
        "provider_rights_allowlisted_for_candidate_training": True,
    }
    quality_gate = {
        "accepted": True,
        "unsafe_advice_filtered": True,
        "judge": "duecare-measured-response-gates-v2",
        "checks": checks,
    }
    sft = {
        "id": f"rsp-sft-{base_id}",
        "messages": [
            {"role": "user", "content": candidate["prompt"]},
            {"role": "assistant", "content": candidate["chosen"]},
        ],
        **common,
        "lineage_id": f"response-pair:{base_id}:sft",
        "quality_gate": quality_gate,
    }
    sft["sha256"] = training_row_sha256(sft)
    dpo = {
        "id": f"rsp-dpo-{base_id}",
        "prompt": candidate["prompt"],
        "chosen": candidate["chosen"],
        "rejected": candidate["rejected"],
        "preference_rationale": {
            "kind": "visible_grade_delta_not_hidden_reasoning",
            "reason": (
                "The chosen response passed the measured target, lift, grounding, citation, "
                "format, privacy and safety gates; the rejected response is the same "
                "model/prompt baseline."
            ),
            "failure_dimension_deltas": candidate["quality_evidence"]["failure_dimension_deltas"],
            "score_lift": candidate["quality_evidence"]["score_lift"],
        },
        **common,
        "lineage_id": f"response-pair:{base_id}:dpo",
        "quality_gate": quality_gate,
    }
    dpo["sha256"] = training_row_sha256(dpo)

    reward_common = {
        key: value for key, value in common.items() if key not in {"allow_training_use"}
    }
    positive = {
        "id": f"rsp-reward-positive-{base_id}",
        "prompt": candidate["prompt"],
        "response": candidate["chosen"],
        "label": 1,
        "label_semantics": "preferred_measured_harness_response",
        "assistant_target_allowed": split == "train",
        "training_lane": "reward_label_and_positive_target_reference",
        **reward_common,
        "allow_training_use": split == "train",
        "lineage_id": f"response-pair:{base_id}:reward-positive",
        "quality_gate": quality_gate,
    }
    positive["sha256"] = training_row_sha256(positive)
    negative = {
        "id": f"rsp-reward-negative-{base_id}",
        "prompt": candidate["prompt"],
        "response": candidate["rejected"],
        "label": 0,
        "label_semantics": "nonpreferred_same_prompt_baseline_response",
        "assistant_target_allowed": False,
        "negative_only": True,
        "training_lane": "reward_label_only_never_sft_assistant_target",
        **reward_common,
        "allow_training_use": split == "train",
        "lineage_id": f"response-pair:{base_id}:reward-negative",
        "quality_gate": {
            "accepted": True,
            "accepted_as": "negative_reward_label_only",
            "unsafe_advice_filtered": False,
            "negative_only": True,
            "judge": "duecare-measured-response-negative-label-v1",
            "checks": {
                "same_prompt_pair": True,
                "negative_never_assistant_target": True,
                "negative_only": True,
                "pii_absent_without_redaction": True,
                "graded_text_emitted_verbatim": True,
                "hidden_reasoning_absent": True,
                "volatile_resource_has_versioned_binding_or_is_absent": True,
                "target_text_exact_and_canonical_dedup": True,
            },
        },
    }
    negative["sha256"] = training_row_sha256(negative)
    return sft, dpo, positive, negative


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def build_bundle(
    *,
    panel_path: Path = DEFAULT_PANEL,
    results_path: Path = DEFAULT_RESULTS,
    promptset_path: Path = DEFAULT_PROMPTSET,
    output_dir: Path = DEFAULT_OUTPUT,
    teacher_arm: str = DEFAULT_TEACHER_ARM,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
    model_licenses: Mapping[str, str] = DEFAULT_MODEL_LICENSES,
    validation_fraction: float = 0.1,
    test_fraction: float = 0.1,
    split_seed: str = "duecare-response-pair-split-v1",
    shard_rows: int = 1000,
    inventory_shard_rows: int = 5000,
    row_license: str = ROW_LICENSE,
    rights_holder: str = RIGHTS_HOLDER,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Build or dry-run one manifest-bound response-pair candidate snapshot."""

    if not model_licenses:
        raise BundleError("at least one allowlisted model with a declared license is required")
    if not row_license.strip() or not rights_holder.strip():
        raise BundleError("row license and rights holder are required")
    if not dry_run:
        _prepare_output_dir(output_dir)
    created_at = _utc_now()
    prompts, prompt_source = load_promptset(promptset_path)
    grades, panel_source = index_panel(panel_path)
    prequalified, rights_pending, grade_summary = _paired_grade_specs(
        grades,
        teacher_arm=teacher_arm,
        thresholds=thresholds,
        model_licenses=model_licenses,
    )

    writers: dict[str, ShardWriter] = {
        "inventory": ShardWriter(
            output_dir,
            "response-inventory",
            shard_rows=inventory_shard_rows,
            enabled=not dry_run,
        ),
        "quarantine": ShardWriter(
            output_dir,
            "quarantine",
            shard_rows=inventory_shard_rows,
            enabled=not dry_run,
        ),
    }
    for lane in ("sft-positive", "dpo-preference", "reward-labels"):
        for split in ("train", "validation", "test"):
            writers[f"{lane}:{split}"] = ShardWriter(
                output_dir,
                f"{lane}-{split}",
                shard_rows=shard_rows,
                enabled=not dry_run,
            )
    for row in rights_pending:
        row = dict(row)
        row["sha256"] = training_row_sha256(row)
        writers["quarantine"].write(row)

    responses, ambiguous, results_source = stream_results_snapshot(
        path=results_path,
        prompts=prompts,
        grades=grades,
        prequalified=prequalified,
        teacher_arm=teacher_arm,
        model_licenses=model_licenses,
        inventory_writer=writers["inventory"],
    )

    model_priority = {model: index for index, model in enumerate(model_licenses)}
    candidate_by_cluster: dict[str, dict[str, Any]] = {}
    drop_reasons = Counter()
    redactions = 0
    for (model, prompt_id), spec in sorted(prequalified.items()):
        candidate, reasons, candidate_redactions = _build_candidate(
            spec=spec,
            responses=responses,
            ambiguous=ambiguous,
            prompt_metadata=prompts.get(prompt_id),
            thresholds=thresholds,
            teacher_arm=teacher_arm,
            model_license=model_licenses[model],
        )
        redactions += candidate_redactions
        if candidate is None:
            for reason in reasons:
                drop_reasons[reason] += 1
            prompt_sha = (
                canonical_sha256(prompts[prompt_id]["text"]) if prompt_id in prompts else None
            )
            writers["quarantine"].write(
                _quarantine_record(
                    model=model,
                    prompt_id=prompt_id,
                    reasons=reasons,
                    prompt_sha256=prompt_sha,
                )
            )
            continue
        cluster_id = str(candidate["cluster_id"])
        previous = candidate_by_cluster.get(cluster_id)
        if previous is None:
            candidate_by_cluster[cluster_id] = candidate
            continue
        if _candidate_rank(candidate, model_priority) > _candidate_rank(previous, model_priority):
            kept, dropped = candidate, previous
            candidate_by_cluster[cluster_id] = candidate
        else:
            kept, dropped = previous, candidate
        drop_reasons["exact_prompt_cluster_duplicate_lower_rank"] += 1
        writers["quarantine"].write(
            _quarantine_record(
                model=str(dropped["model"]),
                prompt_id=str(dropped["prompt_id"]),
                prompt_sha256=str(dropped["training_prompt_sha256"]),
                reasons=["exact_prompt_cluster_duplicate_lower_rank"],
                details={
                    "kept_model": _safe_metadata(kept["model"]),
                    "cluster_id": cluster_id,
                },
            )
        )

    prompt_deduplicated_candidates = len(candidate_by_cluster)
    candidate_by_cluster, target_dedup_drops, target_dedup_counts = _deduplicate_target_texts(
        candidate_by_cluster,
        model_priority=model_priority,
    )
    for dropped in target_dedup_drops:
        candidate = dropped["candidate"]
        drop_reasons["target_text_exact_or_canonical_duplicate_lower_rank"] += 1
        writers["quarantine"].write(
            _quarantine_record(
                model=str(candidate["model"]),
                prompt_id=str(candidate["prompt_id"]),
                prompt_sha256=str(candidate["training_prompt_sha256"]),
                reasons=["target_text_exact_or_canonical_duplicate_lower_rank"],
                details={
                    "collision_kinds": dropped["collision_kinds"],
                    "kept_cluster_ids": dropped["kept_cluster_ids"],
                    "kept_roles": dropped["kept_roles"],
                },
            )
        )

    assignments = _split_assignments(
        candidate_by_cluster,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
        split_seed=split_seed,
    )
    split_counts = Counter(assignments.values())
    split_prompt_hashes: dict[str, list[str]] = defaultdict(list)
    split_group_ids: dict[str, list[str]] = defaultdict(list)
    split_target_hashes: dict[str, dict[str, list[str]]] = {
        "exact": defaultdict(list),
        "canonical": defaultdict(list),
    }
    row_integrity_failures = 0
    emitted_models = Counter()
    negative_target_failures = 0
    incomplete_grade_evidence_failures = 0
    grade_evidence_binding_failures = 0
    accepted_redaction_failures = 0
    accepted_volatile_resource_failures = 0
    for cluster_id, candidate in sorted(candidate_by_cluster.items()):
        split = assignments[cluster_id]
        split_prompt_hashes[split].append(str(candidate["training_prompt_sha256"]))
        split_group_ids[split].append(cluster_id)
        for kind, digest, _role in _target_fingerprints(candidate):
            split_target_hashes[kind][split].append(digest)
        emitted_models[str(candidate["model"])] += 1
        if not _has_complete_bounded_grade_evidence(candidate):
            incomplete_grade_evidence_failures += 1
        if not _has_valid_grade_evidence_binding(candidate):
            grade_evidence_binding_failures += 1
        if int(candidate.get("pii_redactions", -1)) != 0:
            accepted_redaction_failures += 1
        if _contains_unbound_volatile_resource(
            str(candidate["prompt"]),
            str(candidate["chosen"]),
            str(candidate["rejected"]),
        ):
            accepted_volatile_resource_failures += 1
        sft, dpo, reward_positive, reward_negative = _training_rows(
            candidate,
            split=split,
            created_at=created_at,
            row_license=row_license,
            rights_holder=rights_holder,
            teacher_arm=teacher_arm,
        )
        for row in (sft, dpo, reward_positive, reward_negative):
            if row.get("sha256") != training_row_sha256(row):
                row_integrity_failures += 1
        if (
            reward_negative.get("assistant_target_allowed") is not False
            or "messages" in reward_negative
        ):
            negative_target_failures += 1
        writers[f"sft-positive:{split}"].write(sft)
        writers[f"dpo-preference:{split}"].write(dpo)
        writers[f"reward-labels:{split}"].write(reward_positive)
        writers[f"reward-labels:{split}"].write(reward_negative)

    for writer in writers.values():
        writer.close()

    group_sets = {split: set(values) for split, values in split_group_ids.items()}
    split_overlaps = {
        "train_validation": sorted(
            group_sets.get("train", set()) & group_sets.get("validation", set())
        ),
        "train_test": sorted(group_sets.get("train", set()) & group_sets.get("test", set())),
        "validation_test": sorted(
            group_sets.get("validation", set()) & group_sets.get("test", set())
        ),
    }
    within_split_target_overlap_counts: dict[str, dict[str, int]] = {}
    cross_split_target_overlap_counts: dict[str, dict[str, int]] = {}
    target_split_pairs = (
        ("train_validation", "train", "validation"),
        ("train_test", "train", "test"),
        ("validation_test", "validation", "test"),
    )
    for kind in ("exact", "canonical"):
        within_split_target_overlap_counts[kind] = {}
        for split in ("train", "validation", "test"):
            counts = Counter(split_target_hashes[kind].get(split, []))
            within_split_target_overlap_counts[kind][split] = sum(
                count - 1 for count in counts.values() if count > 1
            )
        cross_split_target_overlap_counts[kind] = {
            label: len(
                set(split_target_hashes[kind].get(left, []))
                & set(split_target_hashes[kind].get(right, []))
            )
            for label, left, right in target_split_pairs
        }
    within_split_target_overlap_total = sum(
        count
        for by_split in within_split_target_overlap_counts.values()
        for count in by_split.values()
    )
    cross_split_target_overlap_total = sum(
        count
        for by_pair in cross_split_target_overlap_counts.values()
        for count in by_pair.values()
    )
    contamination_ledger = {
        "schema_version": "duecare.training-contamination-ledger.v1",
        "created_at": created_at,
        "source_benchmark": prompt_source,
        "selection_uses_source_benchmark_grades": True,
        "source_benchmark_cannot_be_reused_as_model_improvement_evidence": True,
        "policy": (
            "Because benchmark prompts and their legacy panel grades selected these targets, "
            "the source benchmark cannot be cited as independent evidence of improvement for "
            "a model trained on this bundle. Internal validation/test splits are diagnostics "
            "only; promotion requires a separately authored, lineage-independent holdout."
        ),
        "independent_external_evidence_eligible": False,
        "accepted_training_prompt_sha256_by_split": {
            split: sorted(values) for split, values in sorted(split_prompt_hashes.items())
        },
        "prompt_cluster_ids_by_split": {
            split: sorted(values) for split, values in sorted(split_group_ids.items())
        },
        "prompt_cluster_overlap": split_overlaps,
        "accepted_target_sha256_by_split": {
            kind: {
                split: sorted(values) for split, values in sorted(split_target_hashes[kind].items())
            }
            for kind in ("exact", "canonical")
        },
        "within_split_target_overlap_counts": within_split_target_overlap_counts,
        "cross_split_target_overlap_counts": cross_split_target_overlap_counts,
    }
    contamination_ledger["sha256"] = canonical_sha256(contamination_ledger)

    artifact_files: dict[str, dict[str, Any]] = {}
    for writer in writers.values():
        artifact_files.update(writer.files)
    if not dry_run:
        contamination_path = output_dir / "contamination-ledger.json"
        _write_json(contamination_path, contamination_ledger)
        artifact_files[contamination_path.name] = _file_entry(contamination_path)

    source_parse_clean = (
        panel_source["malformed_rows"] == 0
        and panel_source["non_object_rows"] == 0
        and panel_source["invalid_grade_rows"] == 0
        and results_source["counters"].get("malformed_rows", 0) == 0
        and results_source["counters"].get("non_object_rows", 0) == 0
        and results_source["counters"].get("trailing_partial_rows", 0) == 0
    )
    gates = [
        {
            "id": "accepted_candidates_present",
            "blocking": True,
            "passed": bool(candidate_by_cluster),
            "value": len(candidate_by_cluster),
        },
        {
            "id": "train_split_present",
            "blocking": True,
            "passed": split_counts.get("train", 0) > 0,
            "value": split_counts.get("train", 0),
        },
        {
            "id": "diagnostic_splits_present",
            "blocking": True,
            "passed": split_counts.get("validation", 0) > 0 and split_counts.get("test", 0) > 0,
            "value": {
                "validation": split_counts.get("validation", 0),
                "test": split_counts.get("test", 0),
            },
        },
        {
            "id": "source_artifacts_parse_clean",
            "blocking": True,
            "passed": source_parse_clean,
            "value": {"panel": panel_source, "results_counters": results_source["counters"]},
        },
        {
            "id": "exact_prompt_dedup",
            "blocking": True,
            "passed": len(candidate_by_cluster) == len(set(candidate_by_cluster)),
            "value": len(candidate_by_cluster),
        },
        {
            "id": "prompt_cluster_split_isolation",
            "blocking": True,
            "passed": not any(split_overlaps.values()),
            "value": split_overlaps,
        },
        {
            "id": "target_text_exact_canonical_dedup",
            "blocking": True,
            "passed": (
                target_dedup_counts.get("unique_exact_target_hashes", 0)
                == 2 * len(candidate_by_cluster)
                and target_dedup_counts.get("unique_canonical_target_hashes", 0)
                == 2 * len(candidate_by_cluster)
            ),
            "value": target_dedup_counts,
        },
        {
            "id": "within_split_target_text_no_overlap",
            "blocking": True,
            "passed": within_split_target_overlap_total == 0,
            "value": {
                "total": within_split_target_overlap_total,
                "by_hash_kind_and_split": within_split_target_overlap_counts,
            },
        },
        {
            "id": "cross_split_target_text_no_overlap",
            "blocking": True,
            "passed": cross_split_target_overlap_total == 0,
            "value": {
                "total": cross_split_target_overlap_total,
                "by_hash_kind_and_split_pair": cross_split_target_overlap_counts,
            },
        },
        {
            "id": "response_body_split_isolation",
            "blocking": True,
            "passed": (
                within_split_target_overlap_total == 0 and cross_split_target_overlap_total == 0
            ),
            "value": {
                "within_split_total": within_split_target_overlap_total,
                "cross_split_total": cross_split_target_overlap_total,
                "hash_kinds": ["exact", "canonical"],
            },
        },
        {
            "id": "complete_bounded_grade_evidence",
            "blocking": True,
            "passed": (
                incomplete_grade_evidence_failures == 0 and grade_evidence_binding_failures == 0
            ),
            "value": {
                "component_evidence_failures": incomplete_grade_evidence_failures,
                "grade_binding_failures": grade_evidence_binding_failures,
                "component_bounds": RUBRIC_COMPONENT_BOUNDS,
            },
        },
        {
            "id": "graded_text_emitted_verbatim_without_redaction",
            "blocking": True,
            "passed": accepted_redaction_failures == 0,
            "value": accepted_redaction_failures,
        },
        {
            "id": "volatile_resources_require_versioned_binding",
            "blocking": True,
            "passed": accepted_volatile_resource_failures == 0,
            "value": accepted_volatile_resource_failures,
        },
        {
            "id": "emitted_models_rights_allowlisted",
            "blocking": True,
            "passed": set(emitted_models) <= set(model_licenses),
            "value": dict(sorted(emitted_models.items())),
        },
        {
            "id": "row_integrity",
            "blocking": True,
            "passed": row_integrity_failures == 0,
            "value": row_integrity_failures,
        },
        {
            "id": "negative_never_assistant_target",
            "blocking": True,
            "passed": negative_target_failures == 0,
            "value": negative_target_failures,
        },
        {
            "id": "publication_approval_separate",
            "blocking": False,
            "passed": False,
            "value": "absent_by_design",
        },
        {
            "id": "teacher_revision_immutable",
            "blocking": False,
            "passed": False,
            "value": "results record local model tags, not immutable weight digests",
        },
    ]
    blocking_failures = [gate["id"] for gate in gates if gate["blocking"] and not gate["passed"]]
    safe_to_train = not blocking_failures
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "created_at": created_at,
        "materialized": not dry_run,
        "mode": "dry_run" if dry_run else "build",
        "source": {
            "promptset": prompt_source,
            "panel": panel_source,
            "results": results_source,
            "generator_sha256": _sha256_file(Path(__file__)),
        },
        "arms": {"baseline": BASELINE_ARM, "teacher": teacher_arm},
        "thresholds": thresholds.as_dict(),
        "allowed_models": dict(sorted(model_licenses.items())),
        "rights": {
            "row_license": row_license,
            "rights_holder": rights_holder,
            "prompt_corpus_license": PROMPT_CORPUS_LICENSE,
            "model_output_licenses": dict(sorted(model_licenses.items())),
            "other_provider_outputs": "rights_pending_and_raw_text_free_quarantine_only",
            "allow_public_redistribution": False,
        },
        "counts": {
            "panel_paired": grade_summary["counts"].get("paired", 0),
            "score_prequalified": len(prequalified),
            "accepted_before_target_text_dedup": prompt_deduplicated_candidates,
            "accepted_after_content_gates_and_exact_dedup": len(candidate_by_cluster),
            "accepted_after_content_prompt_and_target_dedup": len(candidate_by_cluster),
            "target_text_dedup": target_dedup_counts,
            "target_overlap_counts": {
                "within_split": within_split_target_overlap_counts,
                "within_split_total": within_split_target_overlap_total,
                "cross_split": cross_split_target_overlap_counts,
                "cross_split_total": cross_split_target_overlap_total,
            },
            "split_candidates": dict(sorted(split_counts.items())),
            "sft_rows": sum(
                writers[f"sft-positive:{split}"].total_rows
                for split in ("train", "validation", "test")
            ),
            "dpo_rows": sum(
                writers[f"dpo-preference:{split}"].total_rows
                for split in ("train", "validation", "test")
            ),
            "reward_rows": sum(
                writers[f"reward-labels:{split}"].total_rows
                for split in ("train", "validation", "test")
            ),
            "response_inventory_rows": writers["inventory"].total_rows,
            "quarantine_rows": writers["quarantine"].total_rows,
            "pii_redactions_in_emitted_text": 0,
            "pii_redaction_events_detected_and_quarantined": redactions,
        },
        "grade_pair_summary": grade_summary,
        "drop_reasons": dict(sorted(drop_reasons.items())),
        "split_policy": {
            "unit": "exact_prompt_cluster",
            "method": "stable_sha256_threshold",
            "seed": split_seed,
            "validation_fraction": validation_fraction,
            "test_fraction": test_fraction,
            "cluster_overlap": split_overlaps,
            "target_overlap_counts": {
                "within_split": within_split_target_overlap_counts,
                "cross_split": cross_split_target_overlap_counts,
            },
            "assignment_sha256": canonical_sha256(assignments),
        },
        "volatile_resource_policy": (
            "URLs, hotline or contact-number references, and named office or agency references "
            "are quarantined unless a future row schema supplies an exact versioned knowledge-"
            "object binding. Generic retrieval-at-runtime language remains eligible."
        ),
        "reasoning_data_policy": (
            "Final response text and visible score/component deltas only. Hidden reasoning, "
            "scratchpads, analysis channels and provider-private chain-of-thought are rejected "
            "and never exported."
        ),
        "contamination_ledger": {
            "file": None if dry_run else "contamination-ledger.json",
            "sha256": contamination_ledger["sha256"],
            "accepted_prompt_counts_by_split": {
                split: len(values) for split, values in sorted(split_prompt_hashes.items())
            },
            "accepted_target_counts_by_hash_kind_and_split": {
                kind: {
                    split: len(values)
                    for split, values in sorted(split_target_hashes[kind].items())
                }
                for kind in ("exact", "canonical")
            },
            "target_overlap_counts": {
                "within_split": within_split_target_overlap_counts,
                "cross_split": cross_split_target_overlap_counts,
            },
            "source_benchmark_cannot_be_reused_as_model_improvement_evidence": True,
            "independent_external_evidence_eligible": False,
        },
        "gates": gates,
        "blocking_failures": blocking_failures,
        "safe_to_train": safe_to_train,
        "publication_ready": False,
        "publication_approval": {
            "required": True,
            "status": "absent",
            "note": "Generation cannot approve its own redistribution or publication.",
        },
        "files": dict(sorted(artifact_files.items())),
    }
    if not dry_run:
        manifest_path = output_dir / "candidate-manifest.json"
        _write_json(manifest_path, manifest)
    return manifest


def _model_licenses(args: argparse.Namespace) -> dict[str, str]:
    if not args.allow_model and not args.model_license:
        return dict(DEFAULT_MODEL_LICENSES)
    declared = dict(DEFAULT_MODEL_LICENSES)
    for item in args.model_license or []:
        if "=" not in item:
            raise BundleError("--model-license must use MODEL=LICENSE")
        model, license_name = item.split("=", 1)
        if not model.strip() or not license_name.strip():
            raise BundleError("--model-license must use non-empty MODEL=LICENSE")
        declared[model.strip()] = license_name.strip()
    allowed = args.allow_model or list(DEFAULT_MODEL_LICENSES)
    missing = [model for model in allowed if model not in declared]
    if missing:
        raise BundleError("every allowlisted model needs --model-license MODEL=LICENSE")
    return {model: declared[model] for model in allowed}


def _thresholds(args: argparse.Namespace) -> Thresholds:
    return Thresholds(
        min_target=args.min_target,
        min_lift=args.min_lift,
        min_grounding=args.min_grounding,
        min_cite=args.min_cite,
        min_grounding_delta=args.min_grounding_delta,
    )


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--promptset", type=Path, default=DEFAULT_PROMPTSET)
    parser.add_argument("--teacher-arm", default=DEFAULT_TEACHER_ARM)
    parser.add_argument("--min-target", type=float, default=70.0)
    parser.add_argument("--min-lift", type=float, default=20.0)
    parser.add_argument("--min-grounding", type=float, default=24.0)
    parser.add_argument("--min-cite", type=float, default=4.0)
    parser.add_argument("--min-grounding-delta", type=float, default=2.0)
    parser.add_argument("--allow-model", action="append", default=[])
    parser.add_argument("--model-license", action="append", default=[])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="index prompts and grades without opening the response log")
    _add_common_arguments(plan)
    build = sub.add_parser("build", help="stream the response snapshot and build candidate shards")
    _add_common_arguments(build)
    build.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    build.add_argument(
        "--dry-run", action="store_true", help="run every gate without writing files"
    )
    build.add_argument("--shard-rows", type=int, default=1000)
    build.add_argument("--inventory-shard-rows", type=int, default=5000)
    build.add_argument("--validation-fraction", type=float, default=0.1)
    build.add_argument("--test-fraction", type=float, default=0.1)
    build.add_argument("--split-seed", default="duecare-response-pair-split-v1")
    build.add_argument("--row-license", default=ROW_LICENSE)
    build.add_argument("--rights-holder", default=RIGHTS_HOLDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        model_licenses = _model_licenses(args)
        thresholds = _thresholds(args)
        if args.command == "plan":
            result = plan_bundle(
                panel_path=args.panel,
                promptset_path=args.promptset,
                teacher_arm=args.teacher_arm,
                thresholds=thresholds,
                model_licenses=model_licenses,
            )
        else:
            result = build_bundle(
                panel_path=args.panel,
                results_path=args.results,
                promptset_path=args.promptset,
                output_dir=args.output_dir,
                teacher_arm=args.teacher_arm,
                thresholds=thresholds,
                model_licenses=model_licenses,
                validation_fraction=args.validation_fraction,
                test_fraction=args.test_fraction,
                split_seed=args.split_seed,
                shard_rows=max(1, args.shard_rows),
                inventory_shard_rows=max(1, args.inventory_shard_rows),
                row_license=args.row_license,
                rights_holder=args.rights_holder,
                dry_run=args.dry_run,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (BundleError, OSError, ValueError) as exc:
        print(f"[response-preference-bundle] BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
