"""Task protocol. A capability test runnable against any (Model, DomainPack) pair."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from duecare.core.enums import Capability
from duecare.core.schemas import TaskConfig, TaskResult

from .domain_pack import DomainPack
from .model import Model


@runtime_checkable
class Task(Protocol):
    """A capability test runnable against any (Model, DomainPack) pair.

    Tasks are pure functions: their only side effect is writing to the
    configured artifacts dir. They do not call tools, maintain state, or
    make decisions. Decisions live in Agents.
    """

    id: str
    name: str
    capabilities_required: set[Capability]

    def run(
        self,
        model: Model,
        domain: DomainPack,
        config: TaskConfig,
    ) -> TaskResult: ...
