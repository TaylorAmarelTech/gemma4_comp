"""Per-harness training-data logger.

Each harness's handler calls ``log_interaction`` at completion. The output
is a per-harness JSONL stream at ``/kaggle/working/training/<harness>.jsonl``
(fallback ``./.duecare-training/<harness>.jsonl``) that doubles as
production audit trail AND finetuning corpus.

The whole point: each harness is a discrete TASK in the multi-task-learning
sense. Logging at the harness boundary means every user interaction is
automatically a training example for that specific safety task, labeled
with the layer trace + applied_layers.

Privacy
-------
By default ``anonymize=True`` runs the input/output text through PII
regex BEFORE writing the JSONL row. The sha256 of the raw text is also
logged so a future re-anonymization pass can re-hash and verify.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_LOG = logging.getLogger(__name__)


def _training_dir() -> Path:
    candidate = Path("/kaggle/working/training")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except Exception:
        pass
    fallback = Path(".") / ".duecare-training"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _to_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(payload)


def _anonymize(text: str) -> str:
    """Light PII redaction over the canonical detector patterns.

    The training JSONL is the highest-consequence place for a PII leak --
    it doubles as the fine-tuning corpus. So this reuses the SAME pattern
    catalog as the anonymization harness (``anonymization/detector.py``)
    rather than maintaining a second, weaker regex set that can silently
    drift. The catalog covers EMAIL/PHONE/AMOUNT/DOB/ID (incl. PH passport,
    OFW e-card, 16-digit KTP)/PERSON. Falls back to a minimal inline set
    only if the detector module is unavailable (partial install).
    """
    try:
        from .anonymization.detector import PII_PATTERNS as _CANON

        out = text
        for label, pat in _CANON:
            out = pat.sub(f"<{label}>", out)
        return out
    except Exception:
        import re

        fallback = [
            (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<EMAIL>"),
            (re.compile(r"\+?\d[\d\-\s]{7,}\d"), "<PHONE>"),
            (re.compile(r"\b[A-Z]{1,3}-?\d{6,}\b"), "<ID>"),
            (re.compile(
                r"\b(?:Ms\.|Mr\.|Mrs\.|Dr\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
            ), "<PERSON>"),
        ]
        out = text
        for pat, placeholder in fallback:
            out = pat.sub(placeholder, out)
        return out


def log_interaction(
    harness: str,
    *,
    input_payload: Any,
    output_payload: Any,
    applied_layers: dict | None = None,
    trace: dict | None = None,
    anonymize: bool = True,
    extra: dict | None = None,
) -> Path | None:
    """Append one finetuning-grade JSONL row for the given harness.

    Returns the path of the JSONL file, or None when logging fails.
    Logging never raises -- a training-log failure must not break the
    live response path.
    """
    try:
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        in_text = _to_text(input_payload)
        out_text = _to_text(output_payload)
        in_sha = hashlib.sha256(in_text.encode("utf-8")).hexdigest()[:16]
        out_sha = hashlib.sha256(out_text.encode("utf-8")).hexdigest()[:16]
        row: dict[str, Any] = {
            "ts": ts,
            "harness": harness,
            "input": _anonymize(in_text) if anonymize else in_text,
            "output": _anonymize(out_text) if anonymize else out_text,
            "input_sha256": in_sha,
            "output_sha256": out_sha,
            "applied_layers": applied_layers or {},
            "trace": trace or {},
            "anonymized": anonymize,
        }
        if extra:
            row["extra"] = extra
        path = _training_dir() / f"{harness}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return path
    except Exception as exc:
        # Never raise (a training-log failure must not break the live response),
        # but never swallow silently either: a persistent write failure means
        # the finetuning corpus is accumulating gaps. Log the harness + error
        # type (no payload text -> no PII) so the gap is visible in the logs.
        _LOG.warning(
            "training-log write failed for harness %r: %s", harness, type(exc).__name__
        )
        return None
