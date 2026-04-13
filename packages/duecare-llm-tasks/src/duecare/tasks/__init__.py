"""duecare.tasks - capability tests runnable against any (Model, DomainPack) pair."""

from duecare.core.registry import Registry
from duecare.core.contracts import Task

task_registry: Registry = Registry(kind="task")

from .base import base as _base  # noqa: F401,E402
from .guardrails import guardrails as _guardrails  # noqa: F401,E402
from .anonymization import anonymization as _anonymization  # noqa: F401,E402
from .classification import classification as _classification  # noqa: F401,E402
from .fact_extraction import fact_extraction as _fact_extraction  # noqa: F401,E402
from .grounding import grounding as _grounding  # noqa: F401,E402
from .multimodal_classification import multimodal_classification as _multimodal  # noqa: F401,E402
from .adversarial_multi_turn import adversarial_multi_turn as _multi_turn  # noqa: F401,E402
from .tool_use import tool_use as _tool_use  # noqa: F401,E402
from .cross_lingual import cross_lingual as _cross_lingual  # noqa: F401,E402

from .base.base import fresh_task_result, score_against_rubric

__all__ = [
    "task_registry",
    "Task",
    "fresh_task_result",
    "score_against_rubric",
]
