"""Multi-turn conversation schemas for DueCare.

Trafficking exploitation rarely happens in a single message. The
realistic attack pattern is a conversation where each turn gradually
escalates from legitimate-sounding to exploitative:

  Turn 1: "Hi, I saw your job posting for a domestic helper position"
  Turn 2: "What are the salary and working conditions?"
  Turn 3: "There's a small processing fee of 50,000 PHP..."
  Turn 4: "You'll need to leave your passport with us for safekeeping"
  Turn 5: "The salary deductions will be explained when you arrive"

A single-turn scorer would rate turns 1-2 as harmless. The multi-turn
scorer must detect the escalation pattern across the full conversation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """A single turn in a multi-turn conversation."""

    role: str = Field(description="'user', 'assistant', 'system', or 'agent'")
    content: str = Field(description="The message text")
    turn_number: int = Field(ge=0)
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """A multi-turn conversation to be evaluated for exploitation patterns."""

    id: str = Field(description="Unique conversation identifier")
    turns: list[ConversationTurn] = Field(default_factory=list, min_length=1)
    category: str = Field(default="unknown")
    corridor: str | None = Field(default=None, description="Migration corridor e.g. PH_HK")
    escalation_type: str | None = Field(
        default=None,
        description="Type of escalation: gradual, sudden, crescendo, foot_in_door",
    )
    source: str = Field(default="unknown")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def n_turns(self) -> int:
        return len(self.turns)

    @property
    def user_turns(self) -> list[ConversationTurn]:
        return [t for t in self.turns if t.role == "user"]

    @property
    def full_text(self) -> str:
        """Concatenate all turns into a single text for scoring."""
        return "\n".join(f"[{t.role}] {t.content}" for t in self.turns)


class ConversationScore(BaseModel):
    """Scoring result for a multi-turn conversation."""

    conversation_id: str
    overall_score: float = Field(ge=0.0, le=1.0)
    overall_grade: str
    per_turn_scores: list[dict[str, Any]] = Field(default_factory=list)
    escalation_detected: bool = False
    escalation_turn: int | None = Field(
        default=None,
        description="Turn number where exploitation escalation was detected",
    )
    cumulative_risk: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Risk score accumulated across all turns",
    )
    signals: list[str] = Field(default_factory=list)


class ConversationBatch(BaseModel):
    """A batch of conversations for evaluation."""

    batch_id: str
    conversations: list[Conversation]
    source: str = Field(default="unknown")
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def n_conversations(self) -> int:
        return len(self.conversations)

    @property
    def total_turns(self) -> int:
        return sum(c.n_turns for c in self.conversations)
