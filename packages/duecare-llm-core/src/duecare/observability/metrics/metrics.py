"""JSONL metrics sink. Append-only, (run_id, agent, metric, value, timestamp) rows."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


class MetricsSink:
    """Append-only JSONL metrics sink.

    Each write lands one JSON object on one line. Safe for append-only
    logging. For aggregation, load all rows into pandas or DuckDB later.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def write(
        self,
        run_id: str,
        metric: str,
        value: float,
        *,
        agent_id: str | None = None,
        model_id: str | None = None,
        domain_id: str | None = None,
        task_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        row = {
            "run_id": run_id,
            "metric": metric,
            "value": float(value),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "agent_id": agent_id,
            "model_id": model_id,
            "domain_id": domain_id,
            "task_id": task_id,
        }
        if extra:
            row["extra"] = extra
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, default=str) + "\n")

    def bulk_write(self, rows: list[dict]) -> None:
        """Write many rows atomically (still one line per row)."""
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, default=str) + "\n")
