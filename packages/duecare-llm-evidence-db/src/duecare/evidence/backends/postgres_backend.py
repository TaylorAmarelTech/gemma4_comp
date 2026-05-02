"""PostgreSQL backend (for multi-NGO server deployments).

Requires the optional `postgres` extra: `pip install duecare-llm-evidence-db[postgres]`.
"""
from __future__ import annotations

from typing import Any


class PostgresBackend:
    def __init__(self, connection_string: str) -> None:
        try:
            import psycopg2   # type: ignore
            import psycopg2.extras  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "PostgreSQL backend requires psycopg2-binary. "
                "Install with: pip install duecare-llm-evidence-db[postgres]"
            ) from e
        self._psycopg2 = psycopg2
        self._extras = psycopg2.extras
        self._conn = psycopg2.connect(connection_string)

    def _adapt_sql(self, sql: str) -> str:
        # Postgres uses %s placeholders, not ?.
        # Crude but safe: only replace ? outside of single-quoted strings.
        out: list[str] = []
        in_str = False
        for ch in sql:
            if ch == "'":
                in_str = not in_str
                out.append(ch)
            elif ch == "?" and not in_str:
                out.append("%s")
            else:
                out.append(ch)
        return "".join(out)

    def execute(self, sql: str, params: tuple = ()) -> None:
        sql = self._adapt_sql(sql)
        # Postgres has BOOLEAN already; no swap needed.
        with self._conn.cursor() as cur:
            cur.execute(sql, params)

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        sql = self._adapt_sql(sql)
        with self._conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
