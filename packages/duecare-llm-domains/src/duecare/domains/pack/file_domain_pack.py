"""FileDomainPack - a filesystem-backed DomainPack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import yaml

from duecare.core.schemas import DomainCard


class FileDomainPack:
    """A file-system-backed DomainPack.

    Layout (in configs/duecare/domains/<id>/):
      card.yaml              metadata
      taxonomy.yaml          categories, indicators, dimensions
      rubric.yaml            per-task grading rubric
      pii_spec.yaml          PII category spec
      seed_prompts.jsonl     test prompts + graded responses
      evidence.jsonl         facts / laws / cases
      known_failures.jsonl   documented failure modes
      README.md              human-readable intro
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(f"Domain pack root does not exist: {self.root}")

        self._card: DomainCard | None = None
        self._taxonomy: dict | None = None
        self._rubric: dict | None = None
        self._pii_spec: dict | None = None

        # Pre-read the card so id/display_name/version are available
        card = self.card()
        self.id = card.id
        self.display_name = card.display_name
        self.version = card.version

    def card(self) -> DomainCard:
        if self._card is None:
            data = self._load_yaml("card.yaml")
            # Filter to fields DomainCard accepts
            allowed = {
                "id", "display_name", "version", "description", "license",
                "citation", "owner", "capabilities_required",
                "n_seed_prompts", "n_evidence_items",
                "n_indicators", "n_categories", "taxonomy_dimensions",
            }
            filtered = {k: v for k, v in data.items() if k in allowed}
            self._card = DomainCard(**filtered)
        return self._card

    def taxonomy(self) -> dict:
        if self._taxonomy is None:
            self._taxonomy = self._load_yaml("taxonomy.yaml")
        return self._taxonomy

    def rubric(self) -> dict:
        if self._rubric is None:
            self._rubric = self._load_yaml("rubric.yaml")
        return self._rubric

    def pii_spec(self) -> dict:
        if self._pii_spec is None:
            self._pii_spec = self._load_yaml("pii_spec.yaml")
        return self._pii_spec

    def seed_prompts(self) -> Iterator[dict]:
        yield from self._iter_jsonl("seed_prompts.jsonl")

    def evidence(self) -> Iterator[dict]:
        yield from self._iter_jsonl("evidence.jsonl")

    def known_failures(self) -> Iterator[dict]:
        yield from self._iter_jsonl("known_failures.jsonl")

    # ----- helpers -----

    def _load_yaml(self, name: str) -> dict:
        path = self.root / name
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data or {}

    def _iter_jsonl(self, name: str) -> Iterator[dict]:
        path = self.root / name
        if not path.exists():
            return
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def __repr__(self) -> str:
        return f"FileDomainPack(id={self.id!r}, root={self.root})"
