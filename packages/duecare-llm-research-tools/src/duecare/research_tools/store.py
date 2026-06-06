"""Persistent acquisition corpus store -- system of record for staged chunks,
dedup index, crawl state, and the doc graph.

SQLite by default: stdlib (no daemon, no driver, survives the corrupted-Python
box, ships to Kaggle as one file) and scales to millions of rows with WAL +
indexes. The same method surface backs Postgres for the multi-writer server
deployment (`duecare-llm-evidence-db[postgres]`) without changing callers.

The scaling win: near-dup dedup uses a PERSISTED SimHash band index (table
``bands``), so a query is O(bucket) and never re-reads the whole corpus -- the
linear ``is_near_dup`` rescan does not return as the corpus grows. JSONL stays
the interchange/bundle format, exported from accepted rows.

simhash is stored as TEXT (decimal) because a 64-bit unsigned signature can
exceed SQLite's signed-64 INTEGER range.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterator

from .dedup import band_keys, hamming

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS chunks(
  id TEXT PRIMARY KEY, doc_id TEXT, ordinal INTEGER, url TEXT, title TEXT,
  source_tier TEXT, jurisdiction TEXT, text TEXT, content_key TEXT,
  simhash TEXT, n_chars INTEGER, signals TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS ix_chunks_key ON chunks(content_key);
CREATE INDEX IF NOT EXISTS ix_chunks_doc ON chunks(doc_id);
CREATE TABLE IF NOT EXISTS seen_keys(content_key TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS bands(band_idx INTEGER, band_val INTEGER, simhash TEXT);
CREATE INDEX IF NOT EXISTS ix_bands ON bands(band_idx, band_val);
CREATE TABLE IF NOT EXISTS urls(url TEXT PRIMARY KEY, status TEXT, status_code INTEGER, ts TEXT);
CREATE TABLE IF NOT EXISTS edges(source TEXT, target TEXT, relation TEXT, weight INTEGER);
CREATE TABLE IF NOT EXISTS frontier(
  url TEXT PRIMARY KEY, host TEXT, source_tier TEXT, jurisdiction TEXT,
  signals TEXT, discovered_from TEXT, status TEXT DEFAULT 'pending', ts TEXT);
CREATE INDEX IF NOT EXISTS ix_frontier_status ON frontier(status);
CREATE TABLE IF NOT EXISTS sitemaps(url TEXT PRIMARY KEY, ts TEXT);
"""


class AcquisitionStore:
    """SQLite-backed acquisition corpus + dedup index + crawl ledger."""

    def __init__(self, path: str | Path = ":memory:", *, bands: int = 4) -> None:
        self.path = str(path)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(_SCHEMA)
        self._init_fts()
        self.bands = self._resolve_bands(bands)
        self._conn.commit()

    # -- setup ---------------------------------------------------------------
    def _init_fts(self) -> None:
        self.has_fts = True
        try:
            self._conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts "
                "USING fts5(chunk_id UNINDEXED, title, text)")
        except sqlite3.OperationalError:  # FTS5 not compiled in -> degrade gracefully
            self.has_fts = False

    def _resolve_bands(self, bands: int) -> int:
        """Bands must stay constant across runs (band keys depend on it)."""
        row = self._conn.execute("SELECT value FROM meta WHERE key='bands'").fetchone()
        if row is not None:
            return int(row["value"])
        self._conn.execute("INSERT INTO meta(key, value) VALUES('bands', ?)", (str(max(2, bands)),))
        return max(2, bands)

    # -- dedup ---------------------------------------------------------------
    def has_content_key(self, key: str) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM seen_keys WHERE content_key=? LIMIT 1", (key,)).fetchone() is not None

    def seed_baseline(self, keys, sigs) -> None:
        """Seed the dedup index from the live corpus (exact keys + near-dup band
        signatures) WITHOUT adding chunk rows -- so acquired chunks dedup against
        the existing corpus while the chunks table stays acquired-only. Idempotent."""
        self._conn.executemany(
            "INSERT OR IGNORE INTO seen_keys(content_key) VALUES(?)", [(k,) for k in keys])
        for sig in sigs:
            for bi, bv in band_keys(int(sig), bands=self.bands):
                self._conn.execute(
                    "INSERT INTO bands(band_idx, band_val, simhash) VALUES(?,?,?)",
                    (bi, bv, str(int(sig))))
        self._conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('baseline_seeded','1')")
        self._conn.commit()

    def baseline_seeded(self) -> bool:
        row = self._conn.execute("SELECT value FROM meta WHERE key='baseline_seeded'").fetchone()
        return row is not None and row["value"] == "1"

    def is_near_dup(self, simhash: int, *, max_dist: int = 3) -> bool:
        """True if any stored signature is within ``max_dist`` bits -- via the
        persisted band index (exact for ``max_dist < bands``)."""
        candidates: set[int] = set()
        for bi, bv in band_keys(simhash, bands=self.bands):
            for row in self._conn.execute(
                    "SELECT simhash FROM bands WHERE band_idx=? AND band_val=?", (bi, bv)):
                candidates.add(int(row["simhash"]))
        return any(hamming(simhash, c) <= max_dist for c in candidates)

    # -- crawl ledger --------------------------------------------------------
    def url_done(self, url: str) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM urls WHERE url=? LIMIT 1", (url,)).fetchone() is not None

    def mark_url(self, url: str, *, status: str, status_code: int = 0, ts: str = "") -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO urls(url, status, status_code, ts) VALUES(?,?,?,?)",
            (url, status, status_code, ts))

    # -- frontier (URL queue for large crawls) -------------------------------
    def add_frontier_bulk(self, rows: list[dict]) -> int:
        """Insert many discovered URLs at once (INSERT OR IGNORE dedups by url).
        Returns the number of NEW rows added (via total_changes -> O(1), no COUNT
        scan). Built for million-scale harvests."""
        before = self._conn.total_changes
        self._conn.executemany(
            "INSERT OR IGNORE INTO frontier(url, host, source_tier, jurisdiction, "
            "signals, discovered_from, status, ts) VALUES(?,?,?,?,?,?, 'pending', ?)",
            [(r.get("url"), r.get("host"), r.get("source_tier"), r.get("jurisdiction"),
              json.dumps(r.get("signals") or []), r.get("discovered_from"), r.get("ts", ""))
             for r in rows if r.get("url")])
        return self._conn.total_changes - before

    def add_frontier(self, url: str, **meta) -> bool:
        return self.add_frontier_bulk([{"url": url, **meta}]) > 0

    def frontier_count(self, status: str | None = None) -> int:
        if status is None:
            return int(self._conn.execute("SELECT COUNT(*) FROM frontier").fetchone()[0])
        return int(self._conn.execute(
            "SELECT COUNT(*) FROM frontier WHERE status=?", (status,)).fetchone()[0])

    def iter_frontier(self, *, status: str = "pending", limit: int | None = None) -> Iterator[dict]:
        sql = "SELECT * FROM frontier WHERE status=? ORDER BY rowid"
        params: tuple = (status,)
        if limit:
            sql += " LIMIT ?"
            params = (status, limit)
        for row in self._conn.execute(sql, params):
            d = dict(row)
            d["signals"] = json.loads(d.get("signals") or "[]")
            d["jurisdictions"] = [d["jurisdiction"]] if d.get("jurisdiction") else []
            yield d

    def mark_frontier(self, url: str, status: str) -> None:
        self._conn.execute("UPDATE frontier SET status=? WHERE url=?", (status, url))

    def sitemap_seen(self, url: str) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM sitemaps WHERE url=? LIMIT 1", (url,)).fetchone() is not None

    def mark_sitemap(self, url: str, ts: str = "") -> None:
        self._conn.execute("INSERT OR IGNORE INTO sitemaps(url, ts) VALUES(?,?)", (url, ts))

    # -- write ---------------------------------------------------------------
    def add_chunk(self, chunk: dict, *, max_dist: int = 3) -> str:
        """Dedup-and-insert one staged chunk. Returns 'kept' | 'exact' | 'near'.
        Caller commits (per batch) for throughput + crash-safe checkpoints."""
        key = chunk.get("content_key") or ""
        sig = int(chunk.get("simhash") or 0)
        if key and self.has_content_key(key):
            return "exact"
        if self.is_near_dup(sig, max_dist=max_dist):
            return "near"
        self._conn.execute(
            "INSERT OR IGNORE INTO chunks(id, doc_id, ordinal, url, title, source_tier, "
            "jurisdiction, text, content_key, simhash, n_chars, signals, created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (chunk.get("id"), chunk.get("doc_id"), int(chunk.get("ordinal", 0)),
             chunk.get("url"), chunk.get("title"), chunk.get("source_tier"),
             chunk.get("jurisdiction") or (chunk.get("jurisdictions") or [None])[0],
             chunk.get("text", ""), key, str(sig), int(chunk.get("n_chars", 0)),
             json.dumps(chunk.get("signals") or []), chunk.get("created_at", "")))
        if key:
            self._conn.execute("INSERT OR IGNORE INTO seen_keys(content_key) VALUES(?)", (key,))
        for bi, bv in band_keys(sig, bands=self.bands):
            self._conn.execute(
                "INSERT INTO bands(band_idx, band_val, simhash) VALUES(?,?,?)", (bi, bv, str(sig)))
        if self.has_fts:
            self._conn.execute(
                "INSERT INTO chunks_fts(chunk_id, title, text) VALUES(?,?,?)",
                (chunk.get("id"), chunk.get("title") or "", chunk.get("text", "")))
        return "kept"

    def add_edges(self, edges: list[dict]) -> None:
        self._conn.executemany(
            "INSERT INTO edges(source, target, relation, weight) VALUES(?,?,?,?)",
            [(e.get("source"), e.get("target"), e.get("relation"), int(e.get("weight", 1)))
             for e in edges])

    def commit(self) -> None:
        self._conn.commit()

    # -- read ----------------------------------------------------------------
    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])

    def iter_chunks(self) -> Iterator[dict]:
        for row in self._conn.execute("SELECT * FROM chunks ORDER BY doc_id, ordinal"):
            d = dict(row)
            d["signals"] = json.loads(d.get("signals") or "[]")
            yield d

    def search(self, query: str, *, limit: int = 20) -> list[dict]:
        """Full-text search over staged chunks (FTS5); [] if FTS unavailable."""
        if not self.has_fts:
            return []
        rows = self._conn.execute(
            "SELECT chunk_id, title, snippet(chunks_fts, 2, '[', ']', '...', 12) AS snippet "
            "FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT ?", (query, limit)).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        c = self._conn
        return {
            "chunks": self.count(),
            "docs": int(c.execute("SELECT COUNT(DISTINCT doc_id) FROM chunks").fetchone()[0]),
            "urls": int(c.execute("SELECT COUNT(*) FROM urls").fetchone()[0]),
            "edges": int(c.execute("SELECT COUNT(*) FROM edges").fetchone()[0]),
            "bands": self.bands, "fts": self.has_fts, "path": self.path,
        }

    # -- lifecycle -----------------------------------------------------------
    def close(self) -> None:
        self._conn.commit()
        self._conn.close()

    def __enter__(self) -> "AcquisitionStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
