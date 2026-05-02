"""Natural-language -> SQL translator for the Duecare evidence DB."""
from __future__ import annotations

from duecare.nl2sql.translator import Translator, TranslationResult
from duecare.nl2sql.safety import validate_readonly, SQLSafetyError

__all__ = ["Translator", "TranslationResult", "validate_readonly",
           "SQLSafetyError"]
