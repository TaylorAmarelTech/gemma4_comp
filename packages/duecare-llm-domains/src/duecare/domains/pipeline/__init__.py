"""
DueCare document scraping and processing pipeline.

Compartmentalized modules for fetching, extracting, classifying, and
storing documents related to labor trafficking and exploitation.

Each module is independently importable and testable.  Compose them
in any order -- they communicate only through Pydantic models, never
through direct imports of each other.
"""

from __future__ import annotations

from .scraper import RawDocument, fetch_url
from .ilo_scraper import ILOConventionMeta, fetch_convention
from .extractor import ExtractedFact, extract_facts
from .classifier import ClassifiedFact, Sector, ExploitationType, classify_fact
from .document_store import DocumentStore

__all__ = [
    # scraper
    "RawDocument",
    "fetch_url",
    # ilo_scraper
    "ILOConventionMeta",
    "fetch_convention",
    # extractor
    "ExtractedFact",
    "extract_facts",
    # classifier
    "ClassifiedFact",
    "Sector",
    "ExploitationType",
    "classify_fact",
    # document_store
    "DocumentStore",
]
