"""DueCare standardized JSON-Lines logging primitive.

Every kernel uses ``dc_log()`` to emit structured events to:

  1. ``stderr`` — Kaggle captures this in the cell output, so judges see
     the live log stream without leaving the notebook.
  2. A rotating JSON-Lines file at ``/kaggle/working/duecare-logs.jsonl``
     (override with ``DC_LOG_PATH``). The workbench's ``/api/dc-logs``
     endpoint drains this file so the ``Logs`` page can render it.

Schema for one line:

.. code-block:: json

    {
      "ts":         "2026-05-10T17:23:45.123Z",
      "level":      "info",
      "kernel":     "01-workbench",
      "kind":       "chat.send",
      "layer":      "grep",
      "msg":        "fired 7 rules",
      "elapsed_ms": 12,
      "rules":      ["debt_bondage", "passport_retention"]
    }

Standard event ``kind`` values:

  - ``model.load.*``   — model picker selection / load phases / completion
  - ``chat.send``      — incoming chat request
  - ``chat.reply``     — outgoing chat response with elapsed_ms
  - ``grep.fire``      — GREP layer fired N rules on this turn
  - ``rag.retrieve``   — RAG layer pulled top-K docs
  - ``tools.call``     — function-calling tool invoked
  - ``online.search``  — online search executed
  - ``import.upload``  — knowledge-import doc added
  - ``grade.run``      — grader (rule-based or LLM) executed
  - ``shutdown``       — kernel shutdown requested

The file format is append-only JSON Lines (jsonlines.org). Each line
is self-contained so partial writes do not corrupt the file.

A small ring-buffer in memory keeps the last ``RING_SIZE`` events so
``/api/dc-logs?tail=100`` is fast even if the file is multi-MB.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Iterable, Optional

# ---------------------------------------------------------------------------
# Defaults

DEFAULT_LOG_PATH = Path(os.environ.get("DC_LOG_PATH", "/kaggle/working/duecare-logs.jsonl"))
RING_SIZE = int(os.environ.get("DC_LOG_RING_SIZE", "1024"))
DEFAULT_KERNEL_ID = os.environ.get("DC_KERNEL_ID", "unknown")

_LEVELS = {"debug", "info", "warn", "warning", "error"}

# ---------------------------------------------------------------------------
# In-memory ring (so the API doesn't have to re-read the whole file)

_ring: Deque[dict[str, Any]] = deque(maxlen=RING_SIZE)
_ring_lock = threading.Lock()
_file_lock = threading.Lock()


def _now_iso() -> str:
    """ISO-8601 UTC with ms precision; suffix ``Z``."""
    now = datetime.now(timezone.utc)
    ms = now.microsecond // 1000
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"


def _normalize(level: str) -> str:
    lv = (level or "info").lower()
    if lv == "warning":
        lv = "warn"
    if lv not in _LEVELS:
        lv = "info"
    return lv


def dc_log(
    kind: str,
    msg: str = "",
    *,
    level: str = "info",
    layer: Optional[str] = None,
    kernel: Optional[str] = None,
    log_path: Optional[Path] = None,
    **payload: Any,
) -> dict[str, Any]:
    """Emit one JSON-Lines log event.

    Returns the event dict for caller convenience. Safe to call from
    any thread; the file write is locked. If the file cannot be opened
    (e.g. read-only filesystem), the event is still appended to the
    ring + stderr so the in-memory log stays consistent.
    """
    event: dict[str, Any] = {
        "ts": _now_iso(),
        "level": _normalize(level),
        "kernel": kernel or DEFAULT_KERNEL_ID,
        "kind": kind,
    }
    if layer is not None:
        event["layer"] = layer
    if msg:
        event["msg"] = msg
    event.update(payload)

    with _ring_lock:
        _ring.append(event)

    try:
        line = json.dumps(event, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        line = json.dumps({**event, "msg": "(non-serializable payload)"},
                          ensure_ascii=False)

    try:
        print(line, file=sys.stderr, flush=True)
    except Exception:
        pass

    path = log_path or DEFAULT_LOG_PATH
    try:
        with _file_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass

    return event


def tail(n: int = 100, level: Optional[str] = None,
         kind_prefix: Optional[str] = None,
         layer: Optional[str] = None,
         log_path: Optional[Path] = None) -> list[dict[str, Any]]:
    """Return the most recent ``n`` events, optionally filtered.

    Reads from the in-memory ring first (fast). Only falls back to
    re-reading the file if the ring is empty (e.g. a fresh API request
    after a kernel restart hand-off).
    """
    with _ring_lock:
        events = list(_ring)
    if not events:
        path = log_path or DEFAULT_LOG_PATH
        if path.exists():
            events = list(_read_file(path))
    if level:
        norm = _normalize(level)
        events = [e for e in events if e.get("level") == norm]
    if kind_prefix:
        events = [e for e in events if str(e.get("kind", "")).startswith(kind_prefix)]
    if layer:
        events = [e for e in events if e.get("layer") == layer]
    return events[-max(1, n):]


def _read_file(path: Path) -> Iterable[dict[str, Any]]:
    """Yield events from a JSON-Lines file. Skips malformed lines."""
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
    except OSError:
        return


def stats(log_path: Optional[Path] = None) -> dict[str, Any]:
    """Quick aggregate counts for the Logs UI header."""
    with _ring_lock:
        events = list(_ring)
    if not events:
        path = log_path or DEFAULT_LOG_PATH
        if path.exists():
            events = list(_read_file(path))
    by_level: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for e in events:
        lv = e.get("level", "?")
        by_level[lv] = by_level.get(lv, 0) + 1
        kn = e.get("kind", "?")
        by_kind[kn] = by_kind.get(kn, 0) + 1
    return {
        "total": len(events),
        "by_level": by_level,
        "by_kind": dict(sorted(by_kind.items(), key=lambda kv: -kv[1])[:20]),
        "kernel": DEFAULT_KERNEL_ID,
        "log_path": str(log_path or DEFAULT_LOG_PATH),
        "ring_size": RING_SIZE,
        "earliest_ts": events[0].get("ts") if events else None,
        "latest_ts":   events[-1].get("ts") if events else None,
    }


def clear(log_path: Optional[Path] = None) -> int:
    """Clear ring + truncate the log file. Returns the number of events
    that were dropped from the ring."""
    with _ring_lock:
        n = len(_ring)
        _ring.clear()
    path = log_path or DEFAULT_LOG_PATH
    try:
        with _file_lock:
            if path.exists():
                path.write_text("", encoding="utf-8")
    except OSError:
        pass
    return n


def set_kernel_id(kernel_id: str) -> None:
    """Set the default kernel identifier baked into every subsequent
    event. Each kernel.py should call this once near the top so that
    every dc_log() call carries the right kernel name."""
    global DEFAULT_KERNEL_ID
    DEFAULT_KERNEL_ID = kernel_id


__all__ = [
    "dc_log",
    "tail",
    "stats",
    "clear",
    "set_kernel_id",
    "DEFAULT_LOG_PATH",
    "DEFAULT_KERNEL_ID",
    "RING_SIZE",
]
