"""PhaseRunner protocol and PhaseReport schema.

Every phase runner implements this contract. See architecture.md §21.5.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class PhaseReport(BaseModel):
    """Produced at the end of every phase run. Persisted to reports/."""

    phase_id: Literal["exploration", "comparison", "enhancement", "implementation"]
    started_at: datetime
    ended_at: datetime | None = None
    status: Literal["running", "completed", "failed"] = "running"

    # Artifact paths keyed by short name
    artifacts: dict[str, Path] = Field(default_factory=dict)

    # Headline metrics (per capability test + aggregate)
    metrics: dict[str, float] = Field(default_factory=dict)

    # Reproducibility
    git_sha: str = ""
    dataset_version: str = ""
    config_hash: str = ""

    # Human-readable
    summary: str = ""
    notes: list[str] = Field(default_factory=list)


@runtime_checkable
class PhaseRunner(Protocol):
    """A phase runner orchestrates components to produce a PhaseReport."""

    phase_id: str
    config_path: Path

    def run(self) -> PhaseReport:
        """Execute the phase end-to-end and return the report."""
        ...

    def summary(self) -> str:
        """One-line summary for the CLI dashboard."""
        ...
