"""Phase 1 runner - out-of-the-box Gemma 4 baseline.

See docs/project_phases.md Phase 1.

Responsibilities:
  - Load Gemma 4 E2B and E4B via the inference protocol
  - Run the 4 capability tests against the 21K public benchmark
  - Iterate on failure-mode clusters
  - Produce reports/phase1/baseline_gemma_*.md + failure_taxonomy.md
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.phases.base import PhaseReport
from src.phases.categories import CapabilityTest


class ExplorationRunner:
    phase_id = "exploration"

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def run(self) -> PhaseReport:
        report = PhaseReport(
            phase_id="exploration",
            started_at=datetime.now(),
        )
        # TODO: implement
        #   1. Load test data from src.data.sources.local_sqlite (the 21K benchmark)
        #   2. For each model in config (Gemma E2B, E4B):
        #      - For each CapabilityTest:
        #        - Run src.inference.TransformersJudge / LlamaCppJudge
        #        - Score with src.grading.*
        #        - Aggregate metrics
        #   3. Cluster failures, write failure_taxonomy.md
        #   4. Persist to data/phase1/baselines.sqlite
        report.status = "completed"
        report.ended_at = datetime.now()
        report.notes.append("TODO: Phase 1 runner stub")
        return report

    def summary(self) -> str:
        return "Phase 1 - Exploration: stub"
