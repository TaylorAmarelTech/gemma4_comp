"""SQLite backend (for mobile / edge deployments)."""
from __future__ import annotations

import sqlite3
import threading
from typing import Any


class SQLiteBackend:
    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # check_same_thread=False lets the multi-threaded FastAPI server share
        # this connection, but sqlite3 connections are NOT thread-safe -- every
        # connection-touching method must serialize on this lock or concurrent
        # requests corrupt cursor/transaction state.
        self._lock = threading.Lock()

    def execute(self, sql: str, params: tuple = ()) -> None:
        # SQLite uses ? placeholders -- compatible. Strip BOOLEAN type
        # which SQLite doesn't have (it stores as INTEGER).
        sql = sql.replace("BOOLEAN", "INTEGER")
        with self._lock:
            if params:
                self._conn.execute(sql, params)
            else:
                self._conn.execute(sql)

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            if params:
                cur = self._conn.execute(sql, params)
            else:
                cur = self._conn.execute(sql)
            return [dict(row) for row in cur.fetchall()]

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass
