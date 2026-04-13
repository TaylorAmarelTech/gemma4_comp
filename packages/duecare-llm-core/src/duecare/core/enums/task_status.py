"""TaskStatus - the lifecycle states of a task or agent."""

from __future__ import annotations

from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ABORTED = "aborted"
