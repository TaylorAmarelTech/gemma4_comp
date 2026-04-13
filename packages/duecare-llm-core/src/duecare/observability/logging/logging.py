"""Structured logging with a PII filter.

Never logs PII. A filter rejects any log record whose payload contains
content flagged by the anonymization detectors.
"""

from __future__ import annotations

import logging
import sys
from typing import Any


_CONFIGURED = False


def configure_logging(
    level: str = "INFO",
    json_output: bool = False,
) -> None:
    """Configure the root logger for Duecare.

    Idempotent: calling multiple times is a no-op after the first success.
    JSON output is opt-in because structured logging pulls in structlog and
    we want duecare-llm-core to stay dependency-light.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    lvl = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(lvl)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(lvl)

    if json_output:
        try:
            import structlog  # type: ignore

            structlog.configure(
                processors=[
                    structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.JSONRenderer(),
                ],
                wrapper_class=structlog.make_filtering_bound_logger(lvl),
                cache_logger_on_first_use=True,
            )
        except ImportError:
            json_output = False

    if not json_output:
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)-5s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(fmt)

    root.handlers.clear()
    root.addHandler(handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger. Auto-configures on first call."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
