"""Duecare core: contracts, schemas, enums, registries, provenance.

Everything else in Duecare imports from here and only from here.
"""

from .contracts import Agent, Coordinator, DomainPack, Model, Task
from .enums import AgentRole, Capability, Grade, Severity, TaskStatus
from .provenance import (
    compute_checksum,
    generate_run_id,
    get_git_sha,
    get_short_sha,
    hash_config,
    simhash,
)
from .registry import Registry
from .schemas import (
    AgentContext,
    AgentOutput,
    ChatMessage,
    DomainCard,
    Embedding,
    EvaluationRubric,
    EvaluationRun,
    GenerationResult,
    Issue,
    ItemResult,
    ModelHealth,
    PromptBatch,
    Provenance,
    RawPrompt,
    ResponseExample,
    RubricCriterion,
    ScoredResponse,
    TaskConfig,
    TaskResult,
    ToolCall,
    ToolSpec,
    WorkflowRun,
)
from .schemas.conversation import (
    Conversation,
    ConversationBatch,
    ConversationScore,
    ConversationTurn,
)

__version__ = "0.1.0"

__all__ = [
    # Protocols
    "Agent",
    "Coordinator",
    "DomainPack",
    "Model",
    "Task",
    # Enums
    "AgentRole",
    "Capability",
    "Grade",
    "Severity",
    "TaskStatus",
    # Provenance helpers
    "compute_checksum",
    "generate_run_id",
    "get_git_sha",
    "get_short_sha",
    "hash_config",
    "simhash",
    # Registry
    "Registry",
    # Schemas
    "AgentContext",
    "AgentOutput",
    "ChatMessage",
    "DomainCard",
    "Embedding",
    "GenerationResult",
    "Issue",
    "ItemResult",
    "ModelHealth",
    "Provenance",
    "ResponseExample",
    "TaskConfig",
    "TaskResult",
    "ToolCall",
    "ToolSpec",
    "WorkflowRun",
    # Pipeline schemas
    "Conversation",
    "ConversationBatch",
    "ConversationScore",
    "ConversationTurn",
    "EvaluationRubric",
    "EvaluationRun",
    "PromptBatch",
    "RawPrompt",
    "RubricCriterion",
    "ScoredResponse",
]
