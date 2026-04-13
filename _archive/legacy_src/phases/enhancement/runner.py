"""Phase 3 runner - RAG + fine-tune + ablation.

See docs/project_phases.md Phase 3.

Three enhancement tracks + a 4-configuration ablation:
  A. Stock Gemma 4 E4B                       (baseline, from Phase 1)
  B. Stock + RAG                             ("RAG only")
  C. Fine-tuned Gemma 4 E4B                  ("fine-tune only")
  D. Fine-tuned + RAG                        ("hybrid")
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.phases.base import PhaseReport


class EnhancementRunner:
    phase_id = "enhancement"

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def run(self) -> PhaseReport:
        report = PhaseReport(
            phase_id="enhancement",
            started_at=datetime.now(),
        )
        # TODO: implement
        #   1. Build fact database from _reference/framework/src/scraper/seeds/
        #      via src.phases.enhancement.fact_db
        #   2. Build FAISS index via src.phases.enhancement.rag
        #   3. Prepare training splits (held out by source_case_id)
        #   4. Run Unsloth + LoRA fine-tune via src.training.finetune
        #   5. Export merged fp16 -> GGUF via src.export
        #   6. Run ablation over configs A/B/C/D via src.phases.enhancement.ablation
        #   7. Generate model card via src.export.model_card
        #   8. Publish to HF Hub via src.export.publish
        report.status = "completed"
        report.ended_at = datetime.now()
        report.notes.append("TODO: Phase 3 runner stub")
        return report

    def summary(self) -> str:
        return "Phase 3 - Enhancement: stub"
