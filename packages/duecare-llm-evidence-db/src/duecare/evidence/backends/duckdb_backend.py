"""DuckDB backend (the default). In-process, fast, zero-config."""
from __future__ import annotations

from typing import Any


class DuckDBBackend:
    def __init__(self, path: str) -> None:
        import duckdb   # type: ignore
        self._duckdb = duckdb
        if path == ":memory:":
            self._conn = duckdb.connect(database=":memory:")
        else:
            self._conn = duckdb.connect(database=path)

    def execute(self, sql: str, params: tuple = ()) -> None:
        # DuckDB uses ? placeholders too -- compatible.
        if params:
            self._conn.execute(sql, params)
        else:
            self._conn.execute(sql)

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        if params:
            cur = self._conn.execute(sql, params)
        else:
            cur = self._conn.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
