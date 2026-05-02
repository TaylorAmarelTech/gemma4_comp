"""Real tests for duecare.core.enums. No placeholders."""

from __future__ import annotations

import pytest

from duecare.core.enums import (
    AgentRole,
    Capability,
    Grade,
    Severity,
    TaskStatus,
)


class TestCapability:
    def test_all_expected_values(self) -> None:
        expected = {
            "text", "vision", "audio", "function_calling",
            "streaming", "embeddings", "long_context", "fine_tunable",
        }
        assert {c.value for c in Capability} == expected
        assert len(list(Capability)) == 8

    def test_string_comparison(self) -> None:
        # StrEnum equality with strings
        assert Capability.TEXT == "text"
        assert Capability.FUNCTION_CALLING == "function_calling"


class TestAgentRole:
    def test_all_twelve_roles(self) -> None:
        assert len(list(AgentRole)) == 12
        required = {
            "scout", "data_generator", "adversary", "anonymizer",
            "curator", "judge", "validator", "curriculum_designer",
            "trainer", "exporter", "historian", "coordinator",
        }
        assert {r.value for r in AgentRole} == required


class TestTaskStatus:
    def test_all_states(self) -> None:
        assert set(TaskStatus) == {
            TaskStatus.PENDING,
            TaskStatus.RUNNING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.SKIPPED,
            TaskStatus.ABORTED,
        }


class TestGrade:
    def test_ordinal_ordering(self) -> None:
        assert Grade.WORST.ordinal == 0
        assert Grade.BAD.ordinal == 1
        assert Grade.NEUTRAL.ordinal == 2
        assert Grade.GOOD.ordinal == 3
        assert Grade.BEST.ordinal == 4

    def test_ordinals_are_totally_ordered(self) -> None:
        grades_in_order = [Grade.WORST, Grade.BAD, Grade.NEUTRAL, Grade.GOOD, Grade.BEST]
        ordinals = [g.ordinal for g in grades_in_order]
        assert ordinals == sorted(ordinals)

    @pytest.mark.parametrize(
        "score, expected",
        [
            (0.00, Grade.WORST),
            (0.14, Grade.WORST),
            (0.15, Grade.BAD),
            (0.39, Grade.BAD),
            (0.40, Grade.NEUTRAL),
            (0.69, Grade.NEUTRAL),
            (0.70, Grade.GOOD),
            (0.89, Grade.GOOD),
            (0.90, Grade.BEST),
            (1.00, Grade.BEST),
        ],
    )
    def test_from_score(self, score: float, expected: Grade) -> None:
        assert Grade.from_score(score) is expected


class TestSeverity:
    def test_all_levels(self) -> None:
        assert set(Severity) == {
            Severity.CRITICAL,
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW,
        }
