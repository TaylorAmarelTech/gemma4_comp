"""Phase 4 runner - spin up the live demo + API.

In Phase 4 the "runner" doesn't run a one-shot analysis - it boots and
supervises the live demo. `run()` starts the FastAPI server and returns
a report that includes the live URL.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.phases.base import PhaseReport


class ImplementationRunner:
    phase_id = "implementation"

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def run(self) -> PhaseReport:
        report = PhaseReport(
            phase_id="implementation",
            started_at=datetime.now(),
        )
        # TODO: implement
        #   1. Load the Phase 3 GGUF via src.inference.llama_cpp
        #   2. Initialize the in-process RAG retriever from src.phases.enhancement.rag
        #   3. Mount the FastAPI app from src.phases.implementation.api + web
        #   4. Start uvicorn on the configured port
        #   5. Write the live URL into the report
        report.status = "completed"
        report.ended_at = datetime.now()
        report.notes.append("TODO: Phase 4 runner stub")
        return report

    def summary(self) -> str:
        return "Phase 4 - Implementation: stub"
