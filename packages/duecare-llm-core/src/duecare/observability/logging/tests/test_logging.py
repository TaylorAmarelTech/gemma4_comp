"""Real tests for duecare.observability.logging."""

from __future__ import annotations

import logging

from duecare.observability.logging import configure_logging, get_logger


def test_configure_logging_idempotent() -> None:
    configure_logging(level="INFO")
    configure_logging(level="DEBUG")  # second call is a no-op
    # Shouldn't raise


def test_get_logger_returns_logger() -> None:
    log = get_logger("duecare.test.module")
    assert isinstance(log, logging.Logger)
    assert log.name == "duecare.test.module"


def test_get_logger_auto_configures(caplog) -> None:
    log = get_logger("duecare.test.autoconfigure")
    with caplog.at_level(logging.INFO, logger="duecare.test.autoconfigure"):
        log.info("autoconfig test")
    assert any("autoconfig test" in m for m in caplog.messages)


def test_two_get_loggers_return_same_instance() -> None:
    a = get_logger("duecare.same")
    b = get_logger("duecare.same")
    assert a is b


def test_log_levels_work(caplog) -> None:
    log = get_logger("duecare.test.levels")
    with caplog.at_level(logging.DEBUG, logger="duecare.test.levels"):
        log.debug("debug msg")
        log.info("info msg")
        log.warning("warning msg")
        log.error("error msg")
    messages = caplog.messages
    assert "debug msg" in messages
    assert "info msg" in messages
    assert "warning msg" in messages
    assert "error msg" in messages
