"""Phase runners. See docs/project_phases.md.

Four phases, each a thin orchestration layer over the shared component
modules (src/data, src/attacks, src/grading, src/inference, etc.):

  1. exploration    - out-of-the-box Gemma 4 baseline
  2. comparison     - cross-model head-to-head
  3. enhancement    - RAG + fine-tune + ablation
  4. implementation - live API + UI + monitors
"""

from .base import PhaseRunner, PhaseReport

__all__ = ["PhaseRunner", "PhaseReport"]
