"""Phase 4: Gemma 4 Use Case / Implementation.

See docs/project_phases.md section 4.

Ships:
  1. Public API endpoint (/v1/evaluate, /classify, /anonymize, /extract_facts)
  2. Web demo UI with /compare page
  3. Optional: social media monitor (Reddit) or chat monitor (Discord)
"""

from .runner import ImplementationRunner

__all__ = ["ImplementationRunner"]
