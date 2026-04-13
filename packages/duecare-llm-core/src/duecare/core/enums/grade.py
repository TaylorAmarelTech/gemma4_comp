"""Grade - the 5-grade rubric scale used by the Judge agent and training data."""

from __future__ import annotations

from enum import StrEnum


class Grade(StrEnum):
    WORST = "worst"
    BAD = "bad"
    NEUTRAL = "neutral"
    GOOD = "good"
    BEST = "best"

    @property
    def ordinal(self) -> int:
        return {"worst": 0, "bad": 1, "neutral": 2, "good": 3, "best": 4}[self.value]

    @classmethod
    def from_score(cls, score: float) -> "Grade":
        """Map a 0..1 score into a grade bucket."""
        if score < 0.15:
            return cls.WORST
        if score < 0.40:
            return cls.BAD
        if score < 0.70:
            return cls.NEUTRAL
        if score < 0.90:
            return cls.GOOD
        return cls.BEST
