"""Local knowledge base for the wheel runtime.

Operator-side persistent store for ingested case files. Backs the
``/api/local-kb/*`` endpoints and the ``/static/local-*.html`` pages.
Lives entirely on the operator's machine; the public hub never sees
any of this content. The only crossover is when the operator
explicitly clicks "share aggregates", and that path goes through the
existing anonymization pipeline before any POST.

See ``apps/duecare-ai.com/docs/BULK_INGEST_PLAN.md`` for the design
rationale, the two ingestion modes (ZIP upload + folder pick / watch),
and the hard contracts.

This module is a minimum-viable scaffold:
- SQLite-backed storage (3 tables: case, entity, edge)
- Ingest one file at a time (the ZIP / folder dispatchers loop)
- Heuristic classifier + entity extractor (regex; LLM hooks ready)
- Lookup, list, and graph helpers for the viewer pages

Callers still decide what may be ingested, but this module redacts
detector-class PII from stored summaries and stores ``name_hash`` for
entities, never the raw entity name. The operator keeps the salt locally.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Literal

from .pii import detect_pii, redact_pii

DEFAULT_KB_PATH = Path(os.environ.get("DUECARE_LOCAL_KB", ".duecare/local-kb/cases.db")).resolve()
DEFAULT_SALT = os.environ.get("DUECARE_LOCAL_KB_SALT", "local-kb-default-salt")

EntityKind = Literal["employer", "recruiter", "agency", "worker_role", "jurisdiction", "other"]
EdgeKind = Literal["employed_by", "placed_by", "received_fee_from", "similar_pattern", "co_occurs_with"]
CaseStatus = Literal["new", "processed", "shared", "discarded"]


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS case_record (
    case_id           TEXT PRIMARY KEY,
    source_filename   TEXT,
    ingested_at       TEXT NOT NULL,
    corridor          TEXT,
    sector            TEXT,
    summary           TEXT,
    summary_hash      TEXT,
    pii_findings_json TEXT,
    status            TEXT NOT NULL DEFAULT 'new'
);
CREATE TABLE IF NOT EXISTS entity (
    entity_id        TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL,
    kind             TEXT NOT NULL,
    name_hash        TEXT NOT NULL,
    attributes_json  TEXT,
    FOREIGN KEY (case_id) REFERENCES case_record(case_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS edge (
    edge_id          TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL,
    from_entity_id   TEXT NOT NULL,
    to_entity_id     TEXT NOT NULL,
    kind             TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES case_record(case_id) ON DELETE CASCADE,
    FOREIGN KEY (from_entity_id) REFERENCES entity(entity_id) ON DELETE CASCADE,
    FOREIGN KEY (to_entity_id) REFERENCES entity(entity_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_entity_case ON entity(case_id);
CREATE INDEX IF NOT EXISTS idx_entity_hash ON entity(name_hash);
CREATE INDEX IF NOT EXISTS idx_edge_case ON edge(case_id);
"""


# ---------------------------------------------------------------- utilities

def name_hash(value: str, salt: str | None = None) -> str:
    """Stable hash for entity names. Same name + salt -> same hash."""
    salt = salt or DEFAULT_SALT
    return hashlib.sha256(f"{salt}::{value.strip().lower()}".encode("utf-8")).hexdigest()[:24]


# Heuristic recruiter / agency / employer detector. Real implementation
# will call the loaded Gemma; for the scaffold we use a small regex set.
_RECRUITER_RE = re.compile(r"\b(?:agency|recruiter|broker|placement)\s+(?:named?\s+)?(['\"]?)([A-Z][\w\s&.-]{3,40}?)\1", re.IGNORECASE)
_EMPLOYER_RE = re.compile(r"\b(?:employer|company|household)\s+(?:named?\s+)?(['\"]?)([A-Z][\w\s&.-]{3,40}?)\1", re.IGNORECASE)
_CORRIDOR_RE = re.compile(r"\b([A-Z]{3})[\s\-]?(?:to|->|→)[\s\-]?([A-Z]{3})\b")


# ---------------------------------------------------------------- store

@dataclass(slots=True)
class LocalKB:
    """File-backed SQLite store. Defaults to ``~/.duecare/local-kb/cases.db``."""

    path: Path = DEFAULT_KB_PATH

    def ensure_ready(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA_SQL)
            conn.commit()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def ingest(
        self,
        *,
        text: str,
        source_filename: str,
        corridor: str | None = None,
        sector: str | None = None,
        salt: str | None = None,
    ) -> dict[str, Any]:
        """Process one file's content into the local KB.

        Returns the new case record + its extracted entities + edges.
        """
        self.ensure_ready()

        case_id = f"case_{uuid.uuid4().hex[:16]}"
        summary = redact_pii(text.strip())[:600]
        summary_hash = hashlib.sha256(summary.encode("utf-8")).hexdigest()
        pii_findings = sorted(detect_pii(text))
        source_filename = redact_pii(source_filename)

        # Try to detect a corridor from the text if the caller didn't supply one.
        if corridor is None:
            match = _CORRIDOR_RE.search(text)
            if match:
                corridor = f"{match.group(1)}-{match.group(2)}"

        ingested_at = datetime.now(UTC).isoformat()

        # Heuristic entity extraction (recruiter / employer; LLM hooks future).
        entities: list[dict[str, Any]] = []
        for match in _RECRUITER_RE.finditer(text):
            entities.append(self._make_entity(case_id, "recruiter", match.group(2), salt))
        for match in _EMPLOYER_RE.finditer(text):
            entities.append(self._make_entity(case_id, "employer", match.group(2), salt))

        # Build a single "co_occurs_with" edge per pair of entities in this case.
        edges: list[dict[str, Any]] = []
        for i, a in enumerate(entities):
            for b in entities[i + 1 :]:
                edges.append(
                    {
                        "edge_id": f"edge_{uuid.uuid4().hex[:16]}",
                        "case_id": case_id,
                        "from_entity_id": a["entity_id"],
                        "to_entity_id": b["entity_id"],
                        "kind": "co_occurs_with",
                    }
                )

        # Persist.
        import json as _json

        with self._conn() as conn:
            conn.execute(
                "INSERT INTO case_record (case_id, source_filename, ingested_at, corridor, sector, summary, summary_hash, pii_findings_json, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    case_id,
                    source_filename,
                    ingested_at,
                    corridor,
                    sector,
                    summary,
                    summary_hash,
                    _json.dumps(pii_findings),
                    "processed",
                ),
            )
            for entity in entities:
                conn.execute(
                    "INSERT INTO entity (entity_id, case_id, kind, name_hash, attributes_json) VALUES (?, ?, ?, ?, ?)",
                    (
                        entity["entity_id"],
                        entity["case_id"],
                        entity["kind"],
                        entity["name_hash"],
                        _json.dumps(entity.get("attributes", {})),
                    ),
                )
            for edge in edges:
                conn.execute(
                    "INSERT INTO edge (edge_id, case_id, from_entity_id, to_entity_id, kind) VALUES (?, ?, ?, ?, ?)",
                    (
                        edge["edge_id"],
                        edge["case_id"],
                        edge["from_entity_id"],
                        edge["to_entity_id"],
                        edge["kind"],
                    ),
                )
            conn.commit()

        return {
            "case_id": case_id,
            "source_filename": source_filename,
            "ingested_at": ingested_at,
            "corridor": corridor,
            "sector": sector,
            "summary": summary,
            "summary_hash": summary_hash,
            "pii_findings": pii_findings,
            "status": "processed",
            "entities": entities,
            "edges": edges,
        }

    def list_cases(
        self,
        *,
        corridor: str | None = None,
        sector: str | None = None,
        status: CaseStatus | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        self.ensure_ready()
        clauses: list[str] = []
        params: list[Any] = []
        if corridor:
            clauses.append("corridor = ?")
            params.append(corridor)
        if sector:
            clauses.append("sector = ?")
            params.append(sector)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM case_record {where} ORDER BY ingested_at DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        self.ensure_ready()
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM case_record WHERE case_id = ?", (case_id,)).fetchone()
            if row is None:
                return None
            entities = [dict(r) for r in conn.execute("SELECT * FROM entity WHERE case_id = ?", (case_id,)).fetchall()]
            edges = [dict(r) for r in conn.execute("SELECT * FROM edge WHERE case_id = ?", (case_id,)).fetchall()]
        case = dict(row)
        case["entities"] = entities
        case["edges"] = edges
        return case

    def graph(self, *, limit_cases: int = 200) -> dict[str, Any]:
        """Return a force-directed graph blob: nodes (entities) + edges."""
        self.ensure_ready()
        with self._conn() as conn:
            entities = conn.execute(
                "SELECT entity_id, case_id, kind, name_hash FROM entity LIMIT ?",
                (limit_cases * 10,),
            ).fetchall()
            edges = conn.execute(
                "SELECT edge_id, from_entity_id, to_entity_id, kind FROM edge LIMIT ?",
                (limit_cases * 20,),
            ).fetchall()
        return {
            "nodes": [dict(row) for row in entities],
            "edges": [dict(row) for row in edges],
        }

    def stats(self) -> dict[str, Any]:
        self.ensure_ready()
        with self._conn() as conn:
            n_cases = conn.execute("SELECT COUNT(*) FROM case_record").fetchone()[0]
            n_entities = conn.execute("SELECT COUNT(*) FROM entity").fetchone()[0]
            n_edges = conn.execute("SELECT COUNT(*) FROM edge").fetchone()[0]
            corridors = [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT corridor FROM case_record WHERE corridor IS NOT NULL"
                ).fetchall()
            ]
        return {
            "n_cases": n_cases,
            "n_entities": n_entities,
            "n_edges": n_edges,
            "corridors": sorted(corridors),
        }

    def forget_everything(self) -> dict[str, Any]:
        """Wipe the local KB. Operator-controlled right-to-erasure."""
        self.ensure_ready()
        with self._conn() as conn:
            conn.execute("DELETE FROM edge")
            conn.execute("DELETE FROM entity")
            conn.execute("DELETE FROM case_record")
            conn.commit()
        return {"ok": True, "wiped_at": datetime.now(UTC).isoformat()}

    def _make_entity(
        self,
        case_id: str,
        kind: EntityKind,
        raw_name: str,
        salt: str | None,
    ) -> dict[str, Any]:
        return {
            "entity_id": f"ent_{uuid.uuid4().hex[:16]}",
            "case_id": case_id,
            "kind": kind,
            "name_hash": name_hash(raw_name, salt),
            "attributes": {"name_length": len(raw_name)},
        }


__all__ = [
    "DEFAULT_KB_PATH",
    "DEFAULT_SALT",
    "EdgeKind",
    "EntityKind",
    "CaseStatus",
    "LocalKB",
    "name_hash",
]
