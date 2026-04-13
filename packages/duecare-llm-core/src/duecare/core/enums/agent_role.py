"""AgentRole - the 12 agent roles in the Duecare swarm."""

from __future__ import annotations

from enum import StrEnum


class AgentRole(StrEnum):
    """The 12 agent roles. See docs/the_duecare.md."""

    SCOUT = "scout"
    DATA_GENERATOR = "data_generator"
    ADVERSARY = "adversary"
    ANONYMIZER = "anonymizer"
    CURATOR = "curator"
    JUDGE = "judge"
    VALIDATOR = "validator"
    CURRICULUM_DESIGNER = "curriculum_designer"
    TRAINER = "trainer"
    EXPORTER = "exporter"
    HISTORIAN = "historian"
    COORDINATOR = "coordinator"
