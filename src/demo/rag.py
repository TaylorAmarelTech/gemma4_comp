"""Simple RAG (Retrieval-Augmented Generation) for DueCare.

Provides relevant legal/policy context to Gemma 4 before it answers
trafficking-related questions. This tests whether giving the model
the RIGHT information improves its safety responses.

If RAG significantly improves scores over plain Gemma, it proves:
  1. The model has the capability but lacks domain knowledge
  2. Fine-tuning will likely work (the gap is knowledge, not ability)
  3. RAG is a viable deployment strategy for NGOs without GPU budget

The RAG store uses the DueCare knowledge base (configs/duecare/) as
its source of truth. No external vector database needed — keyword
matching is sufficient for a curated KB.

Usage:
    from src.demo.rag import RAGStore

    store = RAGStore.from_configs()
    context = store.retrieve("recruitment fee domestic worker Philippines")
    # Pass context to Gemma alongside the user's question
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml


class RAGStore:
    """Simple keyword-based retrieval store for DueCare's knowledge base."""

    def __init__(self, entries: list[dict[str, Any]]) -> None:
        self._entries = entries
        # Pre-compute lowercase content for matching
        self._indexed = [
            {**e, "_lower": e.get("content", "").lower()}
            for e in entries
        ]

    @classmethod
    def from_configs(cls, configs_dir: Path | None = None) -> RAGStore:
        """Load RAG store from DueCare config files."""
        if configs_dir is None:
            configs_dir = Path(__file__).resolve().parents[2] / "configs" / "duecare"

        entries: list[dict[str, Any]] = []

        # Load legal provisions
        provisions_path = configs_dir / "legal_provisions.yaml"
        if provisions_path.exists():
            data = yaml.safe_load(provisions_path.read_text(encoding="utf-8"))
            for p in data.get("provisions", []):
                entries.append({
                    "content": f"{p.get('law', '')} {p.get('section', '')}: {p.get('description', '')}. Penalty: {p.get('penalty', 'N/A')}",
                    "type": "legal_provision",
                    "jurisdiction": p.get("jurisdiction", ""),
                    "source": "legal_provisions.yaml",
                })

        # Load corridors
        corridors_path = configs_dir / "corridors.yaml"
        if corridors_path.exists():
            data = yaml.safe_load(corridors_path.read_text(encoding="utf-8"))
            for c in data.get("corridors", []):
                entries.append({
                    "content": (
                        f"Migration corridor {c.get('id', '')}: {c.get('origin', '')} to {c.get('destination', '')}. "
                        f"Kafala: {'yes' if c.get('kafala') else 'no'}. Risk: {c.get('debt_bondage_risk', 'unknown')}. "
                        f"Typical fee: USD {c.get('typical_fee_usd', 0)}. Laws: {', '.join(c.get('laws', []))}."
                    ),
                    "type": "corridor",
                    "jurisdiction": c.get("id", ""),
                    "source": "corridors.yaml",
                })

        # Load scheme fingerprints
        schemes_path = configs_dir / "scheme_fingerprints.yaml"
        if schemes_path.exists():
            data = yaml.safe_load(schemes_path.read_text(encoding="utf-8"))
            for s in data.get("schemes", []):
                entries.append({
                    "content": (
                        f"Exploitation scheme: {s.get('name', '')} — {s.get('description', '')}. "
                        f"Key phrases: {', '.join(s.get('key_phrases', [])[:5])}. "
                        f"Laws: {', '.join(s.get('applicable_laws', []))}."
                    ),
                    "type": "scheme",
                    "source": "scheme_fingerprints.yaml",
                })

        # Load rubric criteria
        rubrics_dir = configs_dir / "domains" / "trafficking" / "rubrics"
        if rubrics_dir.exists():
            for rubric_path in rubrics_dir.glob("*.yaml"):
                data = yaml.safe_load(rubric_path.read_text(encoding="utf-8"))
                for criterion in data.get("criteria", []):
                    entries.append({
                        "content": (
                            f"Evaluation criterion: {criterion.get('id', '')} — {criterion.get('description', '')}. "
                            f"Weight: {criterion.get('weight', 1.0)}. Required: {criterion.get('required', False)}."
                        ),
                        "type": "rubric_criterion",
                        "source": rubric_path.name,
                    })

        return cls(entries)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_overlap: int = 2,
    ) -> str:
        """Retrieve relevant entries for a query. Returns formatted context string."""
        query_words = set(re.findall(r"\w{3,}", query.lower()))

        scored = []
        for entry in self._indexed:
            content_words = set(re.findall(r"\w{3,}", entry["_lower"]))
            overlap = len(query_words & content_words)
            if overlap >= min_overlap:
                scored.append((overlap, entry))

        scored.sort(reverse=True, key=lambda x: x[0])

        results = scored[:top_k]
        if not results:
            return ""

        context_parts = []
        for _, entry in results:
            context_parts.append(f"[{entry.get('type', 'info')}] {entry['content']}")

        return "\n\n".join(context_parts)

    def __len__(self) -> int:
        return len(self._entries)
