"""Retriever + FAISS index for the Phase 3 RAG pipeline.

Contract:

    class Retriever(Protocol):
        def retrieve(self, query: str, k: int = 5) -> list[FactHit]: ...

    class FactHit(BaseModel):
        text: str
        source_module: str
        fact_type: str
        score: float
        citation: str

TODO: implement using sentence-transformers + FAISS.
See docs/project_phases.md Phase 3.2a.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class FactHit(BaseModel):
    text: str
    source_module: str
    fact_type: str
    score: float
    citation: str


@runtime_checkable
class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 5) -> list[FactHit]: ...
