"""Phase 2 runner - cross-model head-to-head.

See docs/project_phases.md Phase 2.

Responsibilities:
  - Run the identical 4-capability test suite against the configured
    comparison field (Gemma 4, GPT-OSS, Qwen, Llama, Mistral, DeepSeek,
    closed references)
  - Produce reports/phase2/comparison_report.md + headline_table.md +
    per_corridor_breakdown.md
  - Publish the result SQLite as a public Kaggle Dataset
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.phases.base import PhaseReport


class ComparisonRunner:
    phase_id = "comparison"

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def run(self) -> PhaseReport:
        report = PhaseReport(
            phase_id="comparison",
            started_at=datetime.now(),
        )
        # TODO: implement
        #   1. Load the comparison field from model_list.py
        #   2. For each model:
        #      - Use appropriate provider adapter (OpenAI / Anthropic / Mistral /
        #        Ollama / local-gguf)
        #      - Run the 4-capability test suite
        #      - Collect metrics
        #   3. Compute head-to-head tables and per-corridor breakdowns
        #   4. Write reports and publish Kaggle Dataset
        report.status = "completed"
        report.ended_at = datetime.now()
        report.notes.append("TODO: Phase 2 runner stub")
        return report

    def summary(self) -> str:
        return "Phase 2 - Comparison: stub"
