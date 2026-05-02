"""EvidenceStore: connection-string-driven facade over the actual backend.

Usage
-----
    store = EvidenceStore.open("duecare.duckdb")             # local
    store = EvidenceStore.open("sqlite:///path/to/file.db")  # mobile
    store = EvidenceStore.open("postgresql://...")           # remote

All four backends implement the same interface. Backends are loaded
lazily so that the heavier optional dependencies (psycopg2) only get
imported when the caller actually picks PostgreSQL.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from duecare.evidence.schema import (
    ALL_TABLES,
    SCHEMA_VERSION,
    all_ddl,
    all_indexes,
)


class EvidenceStore:
    """Backend-agnostic interface to the evidence database."""

    def __init__(self, backend: Any, connection_string: str) -> None:
        self._backend = backend
        self._cs = connection_string

    # -- construction --------------------------------------------------------
    @classmethod
    def open(cls, connection_string: str) -> "EvidenceStore":
        """Open or create the evidence store. Recognised connection-string
        forms:
          duecare.duckdb            -> DuckDB file in cwd
          ./path/to/file.duckdb     -> DuckDB at that path
          duckdb:///path/to/db.db   -> DuckDB explicit URI
          sqlite:///path/to/db.db   -> SQLite explicit URI
          postgresql://user@host/db -> PostgreSQL
          :memory:                  -> in-memory DuckDB (testing)
        """
        backend = _resolve_backend(connection_string)
        store = cls(backend, connection_string)
        store._initialise_schema()
        return store

    def close(self) -> None:
        self._backend.close()

    def __enter__(self) -> "EvidenceStore":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- schema / migration --------------------------------------------------
    def _initialise_schema(self) -> None:
        for ddl in all_ddl():
            self._backend.execute(ddl)
        for _name, ddl in all_indexes():
            try:
                self._backend.execute(ddl)
            except Exception as exc:
                # Some backends don't support `IF NOT EXISTS` on CREATE INDEX.
                if "already exists" not in str(exc).lower():
                    raise
        # Persist schema version on first init.
        rows = self._backend.fetchall(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'")
        if not rows:
            self._backend.execute(
                "INSERT INTO schema_meta (key, value) VALUES "
                "('schema_version', ?)",
                (str(SCHEMA_VERSION),))
        self._backend.commit()

    # -- raw query passthrough (used by NL->SQL layer) -----------------------
    def execute(self, sql: str, params: tuple = ()) -> None:
        self._backend.execute(sql, params)
        self._backend.commit()

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        """Return rows as a list of dicts."""
        return self._backend.fetchall(sql, params)

    def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self._backend.fetchall(sql, params)
        return rows[0] if rows else None

    # -- read helpers --------------------------------------------------------
    def list_runs(self) -> list[dict]:
        return self.fetchall(
            "SELECT * FROM runs ORDER BY started_at DESC")

    def latest_run_id(self) -> str | None:
        r = self.fetchone(
            "SELECT run_id FROM runs ORDER BY started_at DESC LIMIT 1")
        return r["run_id"] if r else None

    def get_run(self, run_id: str) -> dict | None:
        return self.fetchone(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,))

    def list_entities(self, run_id: str | None = None,
                      etype: str | None = None,
                      min_doc_count: int = 1,
                      limit: int = 200) -> list[dict]:
        sql = "SELECT * FROM entities WHERE doc_count >= ?"
        params: list = [min_doc_count]
        if run_id:
            sql += " AND run_id = ?"
            params.append(run_id)
        if etype:
            sql += " AND etype = ?"
            params.append(etype)
        sql += " ORDER BY doc_count DESC, severity_max DESC LIMIT ?"
        params.append(limit)
        return self.fetchall(sql, tuple(params))

    def list_findings(self, run_id: str | None = None,
                       trigger_name: str | None = None,
                       min_severity: float = 0,
                       limit: int = 200) -> list[dict]:
        sql = "SELECT * FROM findings WHERE severity >= ?"
        params: list = [min_severity]
        if run_id:
            sql += " AND run_id = ?"
            params.append(run_id)
        if trigger_name:
            sql += " AND trigger_name = ?"
            params.append(trigger_name)
        sql += " ORDER BY severity DESC, detected_at DESC LIMIT ?"
        params.append(limit)
        return self.fetchall(sql, tuple(params))

    # -- run template (parameterised question) -------------------------------
    def run_template(self, template_name: str,
                      params: dict | None = None) -> dict:
        from duecare.evidence.queries import QUESTION_TEMPLATES
        if template_name not in QUESTION_TEMPLATES:
            raise KeyError(
                f"unknown template {template_name!r}. "
                f"Known: {list(QUESTION_TEMPLATES.keys())}")
        tmpl = QUESTION_TEMPLATES[template_name]
        sql, ordered_params = tmpl.render(params or {})
        rows = self.fetchall(sql, ordered_params)
        return {
            "template": template_name,
            "description": tmpl.description,
            "sql": sql,
            "params": params or {},
            "rows": rows,
            "row_count": len(rows),
        }

    # -- write helpers (used by ingest module) -------------------------------
    def upsert_run(self, run: dict) -> None:
        self._upsert("runs", "run_id", run)

    def upsert_document(self, doc: dict) -> None:
        self._upsert("documents", "doc_id", doc)

    def upsert_entity(self, entity: dict) -> None:
        self._upsert("entities", "entity_id", entity)

    def upsert_edge(self, edge: dict) -> None:
        self._upsert("edges", "edge_id", edge)

    def upsert_finding(self, finding: dict) -> None:
        self._upsert("findings", "finding_id", finding)

    def upsert_pairwise_link(self, link: dict) -> None:
        self._upsert("pairwise_links", "link_id", link)

    def upsert_bundle_summary(self, summary: dict) -> None:
        self._upsert("bundle_summaries", "bundle", summary)

    def cache_tool_call(self, tool_name: str, args: dict,
                          result: dict, ttl_seconds: int = 86400) -> str:
        args_json = json.dumps(args, sort_keys=True, default=str)
        args_hash = _hash_args(args_json)
        existing = self.fetchone(
            "SELECT call_id, hit_count FROM tool_call_cache "
            "WHERE tool_name = ? AND args_hash = ?",
            (tool_name, args_hash))
        if existing:
            self._backend.execute(
                "UPDATE tool_call_cache SET hit_count = hit_count + 1, "
                "fetched_at = ? WHERE call_id = ?",
                (datetime.now(), existing["call_id"]))
            self._backend.commit()
            return existing["call_id"]
        call_id = str(uuid.uuid4())
        self._upsert("tool_call_cache", "call_id", {
            "call_id": call_id,
            "tool_name": tool_name,
            "args_hash": args_hash,
            "args_json": args_json,
            "result_json": json.dumps(result, default=str),
            "fetched_at": datetime.now(),
            "ttl_seconds": ttl_seconds,
            "hit_count": 1,
        })
        return call_id

    def get_cached_tool_call(self, tool_name: str,
                               args: dict) -> dict | None:
        args_json = json.dumps(args, sort_keys=True, default=str)
        args_hash = _hash_args(args_json)
        row = self.fetchone(
            "SELECT * FROM tool_call_cache "
            "WHERE tool_name = ? AND args_hash = ?",
            (tool_name, args_hash))
        if not row:
            return None
        try:
            return json.loads(row["result_json"])
        except Exception:
            return None

    # -- linking tables ------------------------------------------------------
    def link_entity_to_doc(self, entity_id: str, doc_id: str,
                             raw_spelling: str = "", page: int = 0,
                             confidence: float = 1.0,
                             source: str = "") -> None:
        self._upsert("entity_documents",
                     ("entity_id", "doc_id"),
                     {"entity_id": entity_id, "doc_id": doc_id,
                      "raw_spelling": raw_spelling, "page": page,
                      "confidence": confidence, "source": source})

    def link_edge_to_doc(self, edge_id: str, doc_id: str) -> None:
        self._upsert("edge_documents",
                     ("edge_id", "doc_id"),
                     {"edge_id": edge_id, "doc_id": doc_id})

    # -- ingest entry point --------------------------------------------------
    def ingest_run(self, output_dir: str | Path,
                    run_id: str | None = None,
                    pipeline_version: str = "v1") -> str:
        """Read every JSON output from a pipeline run directory and
        persist it. Returns the run_id."""
        from duecare.evidence.ingest import ingest_pipeline_outputs
        return ingest_pipeline_outputs(self, output_dir,
                                         run_id=run_id,
                                         pipeline_version=pipeline_version)

    # -- low-level upsert ----------------------------------------------------
    def _upsert(self, table: str, key: str | tuple,
                  row: dict) -> None:
        cols = list(row.keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(cols)
        if isinstance(key, str):
            key_cols = [key]
        else:
            key_cols = list(key)
        # Try INSERT first; on PK collision fall back to UPDATE. This
        # keeps the SQL portable across DuckDB / SQLite / Postgres.
        try:
            self._backend.execute(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                tuple(row[c] for c in cols))
        except Exception as exc:
            msg = str(exc).lower()
            if ("unique" in msg or "duplicate" in msg
                    or "primary key" in msg or "constraint" in msg):
                # Build UPDATE
                set_clause = ", ".join(
                    f"{c} = ?" for c in cols if c not in key_cols)
                where_clause = " AND ".join(
                    f"{c} = ?" for c in key_cols)
                update_vals = tuple(
                    row[c] for c in cols if c not in key_cols)
                where_vals = tuple(row[c] for c in key_cols)
                if set_clause:
                    self._backend.execute(
                        f"UPDATE {table} SET {set_clause} "
                        f"WHERE {where_clause}",
                        update_vals + where_vals)
            else:
                raise
        self._backend.commit()


# ---------------------------------------------------------------------------
# Backend resolution
# ---------------------------------------------------------------------------
def _resolve_backend(cs: str) -> Any:
    """Pick the right backend for a given connection string."""
    cs = cs.strip()
    if cs == ":memory:" or cs.endswith(".duckdb") or cs.startswith("duckdb://"):
        from duecare.evidence.backends.duckdb_backend import DuckDBBackend
        path = cs
        if cs.startswith("duckdb:///"):
            path = cs[len("duckdb:///"):]
        elif cs.startswith("duckdb://"):
            path = cs[len("duckdb://"):]
        return DuckDBBackend(path)
    if cs.startswith("sqlite://"):
        from duecare.evidence.backends.sqlite_backend import SQLiteBackend
        path = cs[len("sqlite:///"):] if cs.startswith("sqlite:///") else cs[len("sqlite://"):]
        return SQLiteBackend(path)
    if cs.startswith(("postgresql://", "postgres://")):
        from duecare.evidence.backends.postgres_backend import PostgresBackend
        return PostgresBackend(cs)
    # Treat as a bare path with the .duckdb extension implied.
    from duecare.evidence.backends.duckdb_backend import DuckDBBackend
    return DuckDBBackend(cs)


def _hash_args(args_json: str) -> str:
    import hashlib
    return hashlib.sha256(args_json.encode("utf-8")).hexdigest()[:16]
