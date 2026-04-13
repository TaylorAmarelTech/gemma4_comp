"""
Simple JSON-backed document store.

Save, load, search, and deduplicate documents with metadata.
No SQLite -- just a single JSON file on disk, suitable for MVP and
environments where installing database drivers is impractical.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class StoredDocument(BaseModel):
    """A document persisted in the store."""

    doc_id: str = ""
    url: str = ""
    title: str = ""
    content_hash: str = ""
    text: str = ""
    content_type: str = "text/html"
    language: str = "en"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    stored_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class DocumentStore:
    """
    Flat-file document store backed by a single JSON file.

    Usage::

        store = DocumentStore(Path("data/documents.json"))
        store.add(doc)
        results = store.search("passport retention")
        store.flush()          # persist to disk
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._docs: dict[str, StoredDocument] = {}
        if path.exists():
            self._load()

    # --- persistence -------------------------------------------------------

    def _load(self) -> None:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        for item in raw:
            doc = StoredDocument(**item)
            self._docs[doc.doc_id] = doc

    def flush(self) -> None:
        """Write the current state to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [doc.model_dump() for doc in self._docs.values()]
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # --- CRUD --------------------------------------------------------------

    @staticmethod
    def _make_id(content_hash: str, url: str) -> str:
        """Deterministic ID from content hash and URL."""
        seed = f"{content_hash}:{url}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def add(
        self,
        *,
        url: str = "",
        title: str = "",
        text: str = "",
        content_hash: str = "",
        content_type: str = "text/html",
        language: str = "en",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> StoredDocument:
        """
        Add a document.  Deduplicates on ``content_hash``.

        Returns the ``StoredDocument`` (existing or newly created).
        """
        if not content_hash and text:
            content_hash = hashlib.sha256(text.encode()).hexdigest()

        doc_id = self._make_id(content_hash, url)

        if doc_id in self._docs:
            return self._docs[doc_id]

        doc = StoredDocument(
            doc_id=doc_id,
            url=url,
            title=title,
            content_hash=content_hash,
            text=text,
            content_type=content_type,
            language=language,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._docs[doc_id] = doc
        return doc

    def get(self, doc_id: str) -> Optional[StoredDocument]:
        """Retrieve a document by ID."""
        return self._docs.get(doc_id)

    def remove(self, doc_id: str) -> bool:
        """Remove a document.  Returns ``True`` if it existed."""
        return self._docs.pop(doc_id, None) is not None

    def list_all(self) -> list[StoredDocument]:
        """Return every document in insertion order."""
        return list(self._docs.values())

    def count(self) -> int:
        """Number of documents in the store."""
        return len(self._docs)

    # --- search ------------------------------------------------------------

    def search(self, query: str, *, limit: int = 50) -> list[StoredDocument]:
        """
        Naive full-text search across title, text, and tags.

        Args:
            query: Space-separated keywords (all must match).
            limit: Maximum number of results.

        Returns:
            Matching ``StoredDocument`` instances, most-recently-stored first.
        """
        tokens = query.lower().split()
        if not tokens:
            return []

        results: list[StoredDocument] = []
        for doc in reversed(list(self._docs.values())):
            blob = f"{doc.title} {doc.text} {' '.join(doc.tags)}".lower()
            if all(t in blob for t in tokens):
                results.append(doc)
                if len(results) >= limit:
                    break
        return results

    def search_by_tag(self, tag: str) -> list[StoredDocument]:
        """Return all documents tagged with *tag*."""
        tag_lower = tag.lower()
        return [d for d in self._docs.values() if tag_lower in (t.lower() for t in d.tags)]
