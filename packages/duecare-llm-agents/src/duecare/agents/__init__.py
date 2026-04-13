"""duecare.agents - the 12-agent Duecare swarm + the supervisor pattern."""

from duecare.core.registry import Registry
from duecare.core.contracts import Agent

agent_registry: Registry = Registry(kind="agent")

from .base import base as _base  # noqa: F401,E402
from .scout import scout as _scout  # noqa: F401,E402
from .data_generator import data_generator as _data_generator  # noqa: F401,E402
from .adversary import adversary as _adversary  # noqa: F401,E402
from .anonymizer import anonymizer as _anonymizer  # noqa: F401,E402
from .curator import curator as _curator  # noqa: F401,E402
from .judge import judge as _judge  # noqa: F401,E402
from .validator import validator as _validator  # noqa: F401,E402
from .curriculum_designer import curriculum_designer as _curriculum_designer  # noqa: F401,E402
from .trainer import trainer as _trainer  # noqa: F401,E402
from .exporter import exporter as _exporter  # noqa: F401,E402
from .historian import historian as _historian  # noqa: F401,E402
from .coordinator import coordinator as _coordinator  # noqa: F401,E402

from .base.base import AgentSupervisor, fresh_agent_output

__all__ = [
    "agent_registry",
    "Agent",
    "AgentSupervisor",
    "fresh_agent_output",
]
