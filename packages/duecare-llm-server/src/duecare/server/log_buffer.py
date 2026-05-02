"""Thread-safe ring buffer of structured log entries.

Captures every important event (API request, task lifecycle, Gemma
call, error) so the dashboard /logs page can render them as JSON.
This is a debug aid -- nothing is persisted to disk, the buffer is
in-memory only and bounded to ~2000 entries.
"""
from __future__ import annotations

import threading
import time
import traceback
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Optional


class LogBuffer:
    """A bounded, thread-safe ring of structured log records."""

    def __init__(self, max_entries: int = 2000) -> None:
        self._max = max_entries
        self._buf: deque[dict] = deque(maxlen=max_entries)
        self._lock = threading.Lock()
        self._counter = 0

    def add(self, level: str, source: str, event: str,
              **fields: Any) -> str:
        """Append a structured entry. Returns the entry's id."""
        with self._lock:
            self._counter += 1
            eid = f"log_{self._counter:06d}"
            entry = {
                "id": eid,
                "ts": datetime.now().isoformat(timespec="milliseconds"),
                "epoch": time.time(),
                "level": level,         # debug|info|warn|error
                "source": source,       # 'api', 'queue', 'gemma', 'tunnel', etc.
                "event": event,         # short snake_case event name
            }
            for k, v in fields.items():
                entry[k] = _safe_json(v)
            self._buf.append(entry)
            return eid

    def add_exception(self, source: str, event: str, exc: BaseException,
                        **fields: Any) -> str:
        return self.add("error", source, event,
                          error_type=type(exc).__name__,
                          error_msg=str(exc)[:500],
                          traceback=traceback.format_exc()[-1500:],
                          **fields)

    def list(self, limit: int = 200, level: Optional[str] = None,
              source: Optional[str] = None,
              since_id: Optional[str] = None) -> list[dict]:
        """Most-recent-first listing (default 200)."""
        with self._lock:
            items = list(self._buf)
        items.reverse()
        if since_id:
            items = [e for e in items if e["id"] > since_id]
        if level:
            items = [e for e in items if e["level"] == level]
        if source:
            items = [e for e in items if e["source"] == source]
        return items[:limit]

    def stats(self) -> dict:
        with self._lock:
            items = list(self._buf)
        out = {"total": len(items),
               "capacity": self._max,
               "by_level": {}, "by_source": {}}
        for e in items:
            out["by_level"][e["level"]] = (
                out["by_level"].get(e["level"], 0) + 1)
            out["by_source"][e["source"]] = (
                out["by_source"].get(e["source"], 0) + 1)
        return out

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()
            self._counter = 0


def _safe_json(v: Any) -> Any:
    """Coerce v into something json.dumps can handle."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, tuple)):
        return [_safe_json(x) for x in v][:50]
    if isinstance(v, dict):
        out = {}
        for k, val in list(v.items())[:50]:
            out[str(k)] = _safe_json(val)
        return out
    try:
        return str(v)[:500]
    except Exception:
        return f"<{type(v).__name__}>"


# Module-level singleton -- import via `from duecare.server.log_buffer
# import LOG_BUFFER`. Bound at import time; survives across all
# requests within the same process.
LOG_BUFFER = LogBuffer(max_entries=2000)
