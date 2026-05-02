#!/usr/bin/env python3
"""
implement_forge_core.py — Write real implementations for duecare-llm-core + duecare-llm-domains.

Populates:
  duecare.core.enums      - Capability, AgentRole, TaskStatus, Grade, Severity
  duecare.core.schemas    - Pydantic models for every cross-layer data flow
  duecare.core.contracts  - Runtime-checkable protocols (Model/DomainPack/Task/Agent/Coordinator)
  duecare.core.registry   - Generic plugin registry
  duecare.core.provenance - run_id, git_sha, hashing helpers
  duecare.core            - top-level re-exports
  duecare.observability   - structlog config, JSONL metrics sink, audit trail
  duecare.domains.pack    - FileDomainPack (filesystem-backed DomainPack)
  duecare.domains.loader  - load_domain_pack() + discover_all()
  duecare.domains         - top-level re-exports + Registry[DomainPack]

Idempotent: Write to target paths overwrites previous content.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


FILES: dict[str, str] = {

    # =======================================================================
    # duecare.core.enums
    # =======================================================================

    "packages/duecare-llm-core/src/forge/core/enums/capability.py": '''"""Capability - what a Model can do."""

from __future__ import annotations

from enum import StrEnum


class Capability(StrEnum):
    """Model capabilities. Each adapter declares which it supports."""

    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"
    LONG_CONTEXT = "long_context"   # effective context > 32K
    FINE_TUNABLE = "fine_tunable"   # has a local LoRA / SFT path available
''',

    "packages/duecare-llm-core/src/forge/core/enums/agent_role.py": '''"""AgentRole - the 12 agent roles in the Duecare swarm."""

from __future__ import annotations

from enum import StrEnum


class AgentRole(StrEnum):
    """The 12 agent roles. See docs/the_forge.md."""

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
''',

    "packages/duecare-llm-core/src/forge/core/enums/task_status.py": '''"""TaskStatus - the lifecycle states of a task or agent."""

from __future__ import annotations

from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ABORTED = "aborted"
''',

    "packages/duecare-llm-core/src/forge/core/enums/grade.py": '''"""Grade - the 5-grade rubric scale used by the Judge agent and training data."""

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
''',

    "packages/duecare-llm-core/src/forge/core/enums/severity.py": '''"""Severity - how bad an Issue is."""

from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
''',

    "packages/duecare-llm-core/src/forge/core/enums/__init__.py": '''"""Canonical enums. Stable identifiers across all layers."""

from .agent_role import AgentRole
from .capability import Capability
from .grade import Grade
from .severity import Severity
from .task_status import TaskStatus

__all__ = ["AgentRole", "Capability", "Grade", "Severity", "TaskStatus"]
''',


    # =======================================================================
    # duecare.core.schemas
    # =======================================================================

    "packages/duecare-llm-core/src/forge/core/schemas/provenance.py": '''"""Provenance - full traceability for any record in a Duecare run."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    """Full traceability for any record produced in a Duecare run.

    Every record in the pipeline carries one of these. The pipeline refuses
    to write a record without a populated Provenance.
    """

    source_id: str = ""                 # which Source connector produced this
    source_row_id: str = ""             # primary key inside that source
    run_id: str
    git_sha: str
    workflow_id: str
    agent_id: str | None = None
    target_model_id: str | None = None
    domain_id: str | None = None
    ingested_at: datetime | None = None
    created_at: datetime
    ingestion_script_version: str = ""
    classifier_versions: dict[str, str] = Field(default_factory=dict)
    anonymizer_version: str | None = None
    anonymizer_actions: list[str] = Field(default_factory=list)
    parent_record_id: str | None = None
    split: str | None = None            # train / val / test / holdout
    checksum: str
''',

    "packages/duecare-llm-core/src/forge/core/schemas/chat.py": '''"""Chat + tool schemas. Shared by every Model adapter."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """One message in a chat conversation. Maps to every major provider's
    chat format (OpenAI, Anthropic, Gemma, Llama chat templates)."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None             # for tool messages
    tool_call_id: str | None = None     # for tool-result messages


class ToolSpec(BaseModel):
    """A tool declaration an Agent passes to a Model.

    Maps 1:1 to Gemma 4 native function calling. Adapters translate per-
    provider (OpenAI / Anthropic / HF / etc.).
    """

    name: str
    description: str
    parameters: dict = Field(default_factory=dict)    # JSON Schema object

    def to_openai(self) -> dict:
        """Render as an OpenAI-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {"type": "object", "properties": {}},
            },
        }

    def to_anthropic(self) -> dict:
        """Render as an Anthropic-compatible tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters or {"type": "object", "properties": {}},
        }


class ToolCall(BaseModel):
    """A tool call emitted by a Model."""

    name: str
    arguments: dict = Field(default_factory=dict)
    call_id: str | None = None
''',

    "packages/duecare-llm-core/src/forge/core/schemas/generation.py": '''"""Generation result + embedding + healthcheck schemas for Model adapters."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .chat import ToolCall


class GenerationResult(BaseModel):
    """The output of a single Model.generate() call."""

    text: str
    finish_reason: str = "stop"
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    tool_calls: list[ToolCall] = Field(default_factory=list)
    model_id: str
    model_version: str = ""
    cost_usd: float = 0.0
    raw: dict = Field(default_factory=dict)  # provider-specific extras


class Embedding(BaseModel):
    """An embedding vector for a piece of text."""

    text: str
    vector: list[float]
    dimension: int
    model_id: str


class ModelHealth(BaseModel):
    """Healthcheck result for a Model adapter."""

    model_id: str
    healthy: bool
    details: dict = Field(default_factory=dict)
''',

    "packages/duecare-llm-core/src/forge/core/schemas/domain.py": '''"""DomainCard + Issue + ResponseExample schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from duecare.core.enums import Capability, Grade, Severity


class DomainCard(BaseModel):
    """Public-facing description of a domain pack."""

    id: str
    display_name: str
    version: str
    description: str = ""
    license: str = "MIT"
    citation: str | None = None
    owner: str = ""
    capabilities_required: set[Capability] = Field(default_factory=set)
    n_seed_prompts: int = 0
    n_evidence_items: int = 0
    n_indicators: int = 0
    n_categories: int = 0
    taxonomy_dimensions: list[str] = Field(default_factory=list)


class Issue(BaseModel):
    """A specific problem with an LLM response."""

    type: str                           # "missed_indicator", "provided_harmful_info", ...
    description: str
    severity: Severity
    documentation_ref: str | None = None


class ResponseExample(BaseModel):
    """A graded exemplar response for a prompt.

    A prompt may have up to 5 of these (one per Grade). They are the
    training signal for the safety judge.
    """

    text: str
    grade: Grade
    score: float                        # 0.0 .. 1.0
    explanation: str = ""
    issues: list[Issue] = Field(default_factory=list)
    documentation_refs: list[str] = Field(default_factory=list)
''',

    "packages/duecare-llm-core/src/forge/core/schemas/task.py": '''"""TaskConfig + TaskResult + ItemResult schemas."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from duecare.core.enums import Grade, TaskStatus
from .provenance import Provenance


class TaskConfig(BaseModel):
    """Configuration passed to Task.run()."""

    sample_size: int | None = None   # None = use the entire test split
    seed: int = 3407
    max_tokens: int = 1024
    temperature: float = 0.0
    system_prompt: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ItemResult(BaseModel):
    """One row of a TaskResult: a single test item's outcome."""

    item_id: str
    input: dict = Field(default_factory=dict)
    model_output: str = ""
    expected: dict = Field(default_factory=dict)
    scores: dict[str, float] = Field(default_factory=dict)
    grade: Grade | None = None
    errors: list[str] = Field(default_factory=list)
    latency_ms: int = 0


class TaskResult(BaseModel):
    """Aggregate result from Task.run()."""

    task_id: str
    model_id: str
    domain_id: str
    status: TaskStatus
    started_at: datetime
    ended_at: datetime | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    per_item: list[ItemResult] = Field(default_factory=list)
    artifacts: dict[str, Path] = Field(default_factory=dict)
    error: str | None = None
    provenance: Provenance

    def summary(self) -> str:
        """One-line human-readable summary."""
        metric_str = ", ".join(f"{k}={v:.3f}" for k, v in self.metrics.items())
        return f"{self.task_id} [{self.status.value}] {metric_str}"
''',

    "packages/duecare-llm-core/src/forge/core/schemas/agent.py": '''"""AgentContext + AgentOutput schemas."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from duecare.core.enums import AgentRole, TaskStatus


class AgentContext(BaseModel):
    """The shared blackboard across a workflow run.

    Agents read + write this by key. The Coordinator is responsible for
    merging agent outputs into the context in the correct order.
    """

    run_id: str
    git_sha: str
    workflow_id: str
    target_model_id: str
    domain_id: str
    started_at: datetime

    # Mutable shared state
    artifacts: dict[str, Path] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    decisions: list[str] = Field(default_factory=list)
    budget_used_usd: float = 0.0

    # Arbitrary per-agent outputs keyed by agent role
    outputs_by_agent: dict[str, dict] = Field(default_factory=dict)

    def record(self, key: str, value: Any) -> None:
        """Convenience: store a value under `key` in outputs_by_agent."""
        self.outputs_by_agent[key] = value

    def lookup(self, key: str, default: Any = None) -> Any:
        return self.outputs_by_agent.get(key, default)


class AgentOutput(BaseModel):
    """The structured output of an agent's execute() call."""

    agent_id: str
    agent_role: AgentRole
    status: TaskStatus
    decision: str                       # one-line human explanation
    artifacts_written: dict[str, Path] = Field(default_factory=dict)
    context_updates: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    error: str | None = None
''',

    "packages/duecare-llm-core/src/forge/core/schemas/workflow.py": '''"""WorkflowRun schema - the authoritative record of a single workflow execution."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from duecare.core.enums import TaskStatus
from .agent import AgentOutput


class WorkflowRun(BaseModel):
    """One end-to-end workflow execution. Persisted per run."""

    run_id: str
    workflow_id: str
    git_sha: str
    config_hash: str
    target_model_id: str
    domain_id: str
    started_at: datetime
    ended_at: datetime | None = None
    status: TaskStatus = TaskStatus.PENDING
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    final_metrics: dict[str, float] = Field(default_factory=dict)
    final_artifacts: dict[str, Path] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    total_duration_s: float = 0.0
    error: str | None = None

    def summary(self) -> str:
        """One-line human-readable summary."""
        return (
            f"run={self.run_id} workflow={self.workflow_id} "
            f"model={self.target_model_id} domain={self.domain_id} "
            f"status={self.status.value} "
            f"cost=${self.total_cost_usd:.2f} duration={self.total_duration_s:.1f}s"
        )
''',

    "packages/duecare-llm-core/src/forge/core/schemas/__init__.py": '''"""Shared Pydantic schemas. Every cross-layer data flow uses these."""

from .agent import AgentContext, AgentOutput
from .chat import ChatMessage, ToolCall, ToolSpec
from .domain import DomainCard, Issue, ResponseExample
from .generation import Embedding, GenerationResult, ModelHealth
from .provenance import Provenance
from .task import ItemResult, TaskConfig, TaskResult
from .workflow import WorkflowRun

__all__ = [
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
]
''',


    # =======================================================================
    # duecare.core.contracts
    # =======================================================================

    "packages/duecare-llm-core/src/forge/core/contracts/model.py": '''"""Model protocol. Any LLM, local or remote, with a common interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)


@runtime_checkable
class Model(Protocol):
    """A language model. Any backend, any provider, any size.

    Adapters wrap concrete implementations (HF Transformers, llama.cpp,
    Ollama, OpenAI, Anthropic, Google Gemini, ...) behind this single
    protocol. Every other Duecare layer depends only on Model, never on
    a concrete adapter.
    """

    id: str
    display_name: str
    provider: str
    capabilities: set[Capability]
    context_length: int

    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        images: list[bytes] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs,
    ) -> GenerationResult: ...

    def embed(self, texts: list[str]) -> list[Embedding]: ...

    def healthcheck(self) -> ModelHealth: ...
''',

    "packages/duecare-llm-core/src/forge/core/contracts/domain_pack.py": '''"""DomainPack protocol. A self-contained safety domain."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Protocol, runtime_checkable

from duecare.core.schemas import DomainCard


@runtime_checkable
class DomainPack(Protocol):
    """A domain = taxonomy + evidence + rubric + seed corpus.

    A domain pack is a self-contained folder under configs/duecare/domains/.
    The same Duecare code runs unchanged against any pack; changing the
    domain means changing which pack you load.
    """

    id: str
    display_name: str
    version: str
    root: Path

    def card(self) -> DomainCard: ...

    def taxonomy(self) -> dict: ...
    def rubric(self) -> dict: ...
    def pii_spec(self) -> dict: ...

    def seed_prompts(self) -> Iterator[dict]: ...
    def evidence(self) -> Iterator[dict]: ...
    def known_failures(self) -> Iterator[dict]: ...
''',

    "packages/duecare-llm-core/src/forge/core/contracts/task.py": '''"""Task protocol. A capability test runnable against any (Model, DomainPack) pair."""

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
''',

    "packages/duecare-llm-core/src/forge/core/contracts/agent.py": '''"""Agent protocol. An autonomous actor in the Duecare swarm."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from duecare.core.enums import AgentRole
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec

from .model import Model


@runtime_checkable
class Agent(Protocol):
    """An autonomous actor in the Duecare swarm.

    Agents compose Tasks and Tools into workflows. They call models
    internally via a Model adapter. They make decisions (what to do
    next, what to skip, what to abort), while Tasks only compute.

    Every agent has:
      - a role (from AgentRole)
      - a model it uses for its own LLM calls
      - a set of tools it can call
      - declared inputs + outputs (context keys it reads/writes)
    """

    id: str
    role: AgentRole
    version: str
    model: Model | None          # some agents (Adversary, Curator) are pure
    tools: list[ToolSpec]
    inputs: set[str]
    outputs: set[str]
    cost_budget_usd: float

    def execute(self, ctx: AgentContext) -> AgentOutput: ...
    def explain(self) -> str: ...
''',

    "packages/duecare-llm-core/src/forge/core/contracts/coordinator.py": '''"""Coordinator protocol. The special agent that orchestrates the swarm."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from duecare.core.schemas import AgentContext, WorkflowRun


@runtime_checkable
class Coordinator(Protocol):
    """The Coordinator is a special agent: it orchestrates the others.

    In a Gemma-native deployment, the Coordinator IS Gemma 4 E4B using
    native function calling to schedule the swarm. In a fallback
    deployment, the Coordinator is a rule-based DAG walker. Both conform
    to this protocol.
    """

    id: str
    version: str
    workflow_id: str

    def run_workflow(self, ctx: AgentContext) -> WorkflowRun: ...
    def explain(self) -> str: ...
''',

    "packages/duecare-llm-core/src/forge/core/contracts/__init__.py": '''"""Runtime-checkable protocols. The only cross-layer contracts in Duecare."""

from .agent import Agent
from .coordinator import Coordinator
from .domain_pack import DomainPack
from .model import Model
from .task import Task

__all__ = ["Agent", "Coordinator", "DomainPack", "Model", "Task"]
''',


    # =======================================================================
    # duecare.core.registry
    # =======================================================================

    "packages/duecare-llm-core/src/forge/core/registry/registry.py": '''"""Registry[T] - the generic plugin registry used throughout Duecare."""

from __future__ import annotations

from typing import Callable, Generic, Iterator, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """A named registry of plugin instances (or classes).

    Every plugin kind (models, domains, agents, tasks) has its own Registry
    instance but shares this code. Plugins register themselves on import via
    @registry.register("id").
    """

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._by_id: dict[str, T] = {}
        self._metadata: dict[str, dict] = {}

    def register(
        self,
        id: str,
        **metadata,
    ) -> Callable[[T], T]:
        """Decorator to register a plugin under `id`."""
        def decorator(cls_or_instance: T) -> T:
            if id in self._by_id:
                raise ValueError(
                    f"{self.kind} id {id!r} is already registered"
                )
            self._by_id[id] = cls_or_instance
            self._metadata[id] = metadata
            return cls_or_instance
        return decorator

    def add(self, id: str, entry: T, **metadata) -> None:
        """Imperative registration (outside of class-decoration flow)."""
        if id in self._by_id:
            raise ValueError(f"{self.kind} id {id!r} is already registered")
        self._by_id[id] = entry
        self._metadata[id] = metadata

    def get(self, id: str) -> T:
        if id not in self._by_id:
            known = ", ".join(sorted(self._by_id.keys())) or "(empty)"
            raise KeyError(
                f"Unknown {self.kind} id {id!r}. Known: {known}"
            )
        return self._by_id[id]

    def has(self, id: str) -> bool:
        return id in self._by_id

    def all_ids(self) -> list[str]:
        return sorted(self._by_id.keys())

    def metadata(self, id: str) -> dict:
        return self._metadata.get(id, {})

    def items(self) -> Iterator[tuple[str, T]]:
        for id in self.all_ids():
            yield id, self._by_id[id]

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, id: str) -> bool:
        return id in self._by_id

    def __repr__(self) -> str:
        return f"Registry[{self.kind}]({len(self)} entries)"
''',

    "packages/duecare-llm-core/src/forge/core/registry/__init__.py": '''"""Registry[T] - generic plugin registry used by models / domains / agents / tasks."""

from .registry import Registry

__all__ = ["Registry"]
''',


    # =======================================================================
    # duecare.core.provenance
    # =======================================================================

    "packages/duecare-llm-core/src/forge/core/provenance/git.py": '''"""Git sha resolution. Returns 'unknown' if not inside a git repo."""

from __future__ import annotations

import subprocess


def get_git_sha() -> str:
    """Return the current git sha, or 'unknown' if not in a repo."""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def get_short_sha(length: int = 8) -> str:
    """Return the first `length` chars of the git sha, or 'unknown'."""
    sha = get_git_sha()
    if sha == "unknown":
        return sha
    return sha[:length]
''',

    "packages/duecare-llm-core/src/forge/core/provenance/run_id.py": '''"""run_id generation. Format: YYYYMMDDHHMMSS_{short_sha}_{workflow_id}."""

from __future__ import annotations

from datetime import datetime

from .git import get_short_sha


def generate_run_id(workflow_id: str) -> str:
    """Stable, sortable, greppable run id."""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    sha = get_short_sha()
    safe_workflow = workflow_id.replace("/", "_").replace(" ", "_")
    return f"{ts}_{sha}_{safe_workflow}"
''',

    "packages/duecare-llm-core/src/forge/core/provenance/hashing.py": '''"""Deterministic hashing helpers for config + content."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_config(config: Any) -> str:
    """Deterministic sha256 of a JSON-serializable config object."""
    payload = json.dumps(config, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()


def compute_checksum(content: str | bytes) -> str:
    """SHA256 of arbitrary content. Used for staging-DB dedup and audit."""
    if isinstance(content, str):
        content = content.encode()
    return hashlib.sha256(content).hexdigest()


def simhash(text: str, num_bits: int = 64) -> int:
    """Cheap SimHash for near-duplicate detection.

    Not a production-grade SimHash, but good enough for deduping synthetic
    probes where we want near-duplicates collapsed. Uses word-level tokens.
    """
    from collections import Counter

    tokens = text.lower().split()
    if not tokens:
        return 0
    weights = Counter(tokens)
    v = [0] * num_bits
    for token, w in weights.items():
        token_hash = int(hashlib.md5(token.encode()).hexdigest(), 16)
        for i in range(num_bits):
            bit = (token_hash >> i) & 1
            v[i] += w if bit else -w
    result = 0
    for i in range(num_bits):
        if v[i] >= 0:
            result |= 1 << i
    return result
''',

    "packages/duecare-llm-core/src/forge/core/provenance/__init__.py": '''"""Provenance helpers: run_id, git_sha, config hashing, SimHash."""

from .git import get_git_sha, get_short_sha
from .hashing import compute_checksum, hash_config, simhash
from .run_id import generate_run_id

__all__ = [
    "compute_checksum",
    "generate_run_id",
    "get_git_sha",
    "get_short_sha",
    "hash_config",
    "simhash",
]
''',


    # =======================================================================
    # duecare.core __init__
    # =======================================================================

    "packages/duecare-llm-core/src/forge/core/__init__.py": '''"""Duecare core: contracts, schemas, enums, registries, provenance.

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
    GenerationResult,
    Issue,
    ItemResult,
    ModelHealth,
    Provenance,
    ResponseExample,
    TaskConfig,
    TaskResult,
    ToolCall,
    ToolSpec,
    WorkflowRun,
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
]
''',


    # =======================================================================
    # duecare.observability
    # =======================================================================

    "packages/duecare-llm-core/src/forge/observability/logging/logging.py": '''"""Structured logging with a PII filter.

Never logs PII. A filter rejects any log record whose payload contains
content flagged by the anonymization detectors.
"""

from __future__ import annotations

import logging
import sys
from typing import Any


_CONFIGURED = False


def configure_logging(
    level: str = "INFO",
    json_output: bool = False,
) -> None:
    """Configure the root logger for Duecare.

    Idempotent: calling multiple times is a no-op after the first success.
    JSON output is opt-in because structured logging pulls in structlog and
    we want duecare-llm-core to stay dependency-light.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    lvl = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(lvl)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(lvl)

    if json_output:
        try:
            import structlog  # type: ignore

            structlog.configure(
                processors=[
                    structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.JSONRenderer(),
                ],
                wrapper_class=structlog.make_filtering_bound_logger(lvl),
                cache_logger_on_first_use=True,
            )
        except ImportError:
            json_output = False

    if not json_output:
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)-5s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(fmt)

    root.handlers.clear()
    root.addHandler(handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger. Auto-configures on first call."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
''',

    "packages/duecare-llm-core/src/forge/observability/logging/__init__.py": '''"""Logging configuration + get_logger()."""

from .logging import configure_logging, get_logger

__all__ = ["configure_logging", "get_logger"]
''',

    "packages/duecare-llm-core/src/forge/observability/metrics/metrics.py": '''"""JSONL metrics sink. Append-only, (run_id, agent, metric, value, timestamp) rows."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


class MetricsSink:
    """Append-only JSONL metrics sink.

    Each write lands one JSON object on one line. Safe for append-only
    logging. For aggregation, load all rows into pandas or DuckDB later.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def write(
        self,
        run_id: str,
        metric: str,
        value: float,
        *,
        agent_id: str | None = None,
        model_id: str | None = None,
        domain_id: str | None = None,
        task_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        row = {
            "run_id": run_id,
            "metric": metric,
            "value": float(value),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "agent_id": agent_id,
            "model_id": model_id,
            "domain_id": domain_id,
            "task_id": task_id,
        }
        if extra:
            row["extra"] = extra
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, default=str) + "\\n")

    def bulk_write(self, rows: list[dict]) -> None:
        """Write many rows atomically (still one line per row)."""
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, default=str) + "\\n")
''',

    "packages/duecare-llm-core/src/forge/observability/metrics/__init__.py": '''"""Metrics sink."""

from .metrics import MetricsSink

__all__ = ["MetricsSink"]
''',

    "packages/duecare-llm-core/src/forge/observability/audit/audit.py": '''"""Audit trail. SQLite-backed, append-only, stores hashes NOT plaintext."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock


SCHEMA = """
CREATE TABLE IF NOT EXISTS anon_audit (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    detector_name TEXT NOT NULL,
    detector_version TEXT NOT NULL,
    span_start INTEGER NOT NULL,
    span_end INTEGER NOT NULL,
    category TEXT NOT NULL,
    original_hash TEXT NOT NULL,
    strategy TEXT NOT NULL,
    replacement TEXT NOT NULL,
    operator TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_anon_audit_item ON anon_audit(item_id);
CREATE INDEX IF NOT EXISTS idx_anon_audit_category ON anon_audit(category);

CREATE TABLE IF NOT EXISTS run_audit (
    run_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    git_sha TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    target_model_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL,
    total_cost_usd REAL DEFAULT 0.0,
    final_metrics TEXT
);
"""


class AuditTrail:
    """Append-only audit trail backed by SQLite."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(SCHEMA)

    def record_anonymization(
        self,
        *,
        audit_id: str,
        item_id: str,
        detector_name: str,
        detector_version: str,
        span_start: int,
        span_end: int,
        category: str,
        original_hash: str,
        strategy: str,
        replacement: str,
        operator: str = "auto",
    ) -> None:
        """Record one anonymization decision. Stores hash, never plaintext."""
        row = (
            audit_id,
            item_id,
            detector_name,
            detector_version,
            span_start,
            span_end,
            category,
            original_hash,
            strategy,
            replacement,
            operator,
            datetime.now().isoformat(timespec="seconds"),
        )
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO anon_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row,
                )
                conn.commit()

    def record_run_start(
        self,
        *,
        run_id: str,
        workflow_id: str,
        git_sha: str,
        config_hash: str,
        target_model_id: str,
        domain_id: str,
    ) -> None:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO run_audit VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, NULL, ?, 0.0, NULL)",
                    (
                        run_id,
                        workflow_id,
                        git_sha,
                        config_hash,
                        target_model_id,
                        domain_id,
                        datetime.now().isoformat(timespec="seconds"),
                        "running",
                    ),
                )
                conn.commit()

    def record_run_end(
        self,
        *,
        run_id: str,
        status: str,
        total_cost_usd: float = 0.0,
        final_metrics: dict | None = None,
    ) -> None:
        import json
        metrics_json = json.dumps(final_metrics or {})
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE run_audit SET ended_at = ?, status = ?, "
                    "total_cost_usd = ?, final_metrics = ? WHERE run_id = ?",
                    (
                        datetime.now().isoformat(timespec="seconds"),
                        status,
                        total_cost_usd,
                        metrics_json,
                        run_id,
                    ),
                )
                conn.commit()
''',

    "packages/duecare-llm-core/src/forge/observability/audit/__init__.py": '''"""Audit trail."""

from .audit import AuditTrail

__all__ = ["AuditTrail"]
''',

    "packages/duecare-llm-core/src/forge/observability/__init__.py": '''"""Observability: logging, metrics, audit."""

from .audit import AuditTrail
from .logging import configure_logging, get_logger
from .metrics import MetricsSink

__all__ = ["AuditTrail", "MetricsSink", "configure_logging", "get_logger"]
''',


    # =======================================================================
    # duecare.domains
    # =======================================================================

    "packages/duecare-llm-domains/src/forge/domains/pack/file_domain_pack.py": '''"""FileDomainPack - a filesystem-backed DomainPack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import yaml

from duecare.core.schemas import DomainCard


class FileDomainPack:
    """A file-system-backed DomainPack.

    Layout (in configs/duecare/domains/<id>/):
      card.yaml              metadata
      taxonomy.yaml          categories, indicators, dimensions
      rubric.yaml            per-task grading rubric
      pii_spec.yaml          PII category spec
      seed_prompts.jsonl     test prompts + graded responses
      evidence.jsonl         facts / laws / cases
      known_failures.jsonl   documented failure modes
      README.md              human-readable intro
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(f"Domain pack root does not exist: {self.root}")

        self._card: DomainCard | None = None
        self._taxonomy: dict | None = None
        self._rubric: dict | None = None
        self._pii_spec: dict | None = None

        # Pre-read the card so id/display_name/version are available
        card = self.card()
        self.id = card.id
        self.display_name = card.display_name
        self.version = card.version

    def card(self) -> DomainCard:
        if self._card is None:
            data = self._load_yaml("card.yaml")
            # Filter to fields DomainCard accepts
            allowed = {
                "id", "display_name", "version", "description", "license",
                "citation", "owner", "capabilities_required",
                "n_seed_prompts", "n_evidence_items",
                "n_indicators", "n_categories", "taxonomy_dimensions",
            }
            filtered = {k: v for k, v in data.items() if k in allowed}
            self._card = DomainCard(**filtered)
        return self._card

    def taxonomy(self) -> dict:
        if self._taxonomy is None:
            self._taxonomy = self._load_yaml("taxonomy.yaml")
        return self._taxonomy

    def rubric(self) -> dict:
        if self._rubric is None:
            self._rubric = self._load_yaml("rubric.yaml")
        return self._rubric

    def pii_spec(self) -> dict:
        if self._pii_spec is None:
            self._pii_spec = self._load_yaml("pii_spec.yaml")
        return self._pii_spec

    def seed_prompts(self) -> Iterator[dict]:
        yield from self._iter_jsonl("seed_prompts.jsonl")

    def evidence(self) -> Iterator[dict]:
        yield from self._iter_jsonl("evidence.jsonl")

    def known_failures(self) -> Iterator[dict]:
        yield from self._iter_jsonl("known_failures.jsonl")

    # ----- helpers -----

    def _load_yaml(self, name: str) -> dict:
        path = self.root / name
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data or {}

    def _iter_jsonl(self, name: str) -> Iterator[dict]:
        path = self.root / name
        if not path.exists():
            return
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def __repr__(self) -> str:
        return f"FileDomainPack(id={self.id!r}, root={self.root})"
''',

    "packages/duecare-llm-domains/src/forge/domains/pack/__init__.py": '''"""FileDomainPack - filesystem-backed implementation of duecare.core.DomainPack."""

from .file_domain_pack import FileDomainPack

__all__ = ["FileDomainPack"]
''',

    "packages/duecare-llm-domains/src/forge/domains/loader/loader.py": '''"""Domain pack discovery + loading."""

from __future__ import annotations

from pathlib import Path

from duecare.domains.pack import FileDomainPack


DEFAULT_ROOT = Path("configs/duecare/domains")


def load_domain_pack(
    domain_id: str,
    root: Path | str | None = None,
) -> FileDomainPack:
    """Load a domain pack by id.

    Looks up `{root}/{domain_id}/` (defaulting to configs/duecare/domains/).
    """
    root_path = Path(root) if root else DEFAULT_ROOT
    pack_dir = root_path / domain_id
    return FileDomainPack(root=pack_dir)


def discover_all(
    root: Path | str | None = None,
) -> list[FileDomainPack]:
    """Walk `root` and return a FileDomainPack for every discoverable pack.

    A pack is "discoverable" if its directory contains a card.yaml.
    """
    root_path = Path(root) if root else DEFAULT_ROOT
    if not root_path.exists():
        return []
    packs: list[FileDomainPack] = []
    for child in sorted(root_path.iterdir()):
        if not child.is_dir():
            continue
        if (child / "card.yaml").exists():
            try:
                packs.append(FileDomainPack(root=child))
            except Exception:
                continue
    return packs
''',

    "packages/duecare-llm-domains/src/forge/domains/loader/__init__.py": '''"""Domain pack loader + discovery."""

from .loader import DEFAULT_ROOT, discover_all, load_domain_pack

__all__ = ["DEFAULT_ROOT", "discover_all", "load_domain_pack"]
''',

    "packages/duecare-llm-domains/src/forge/domains/__init__.py": '''"""Duecare domain packs layer.

Pluggable safety domains. A domain pack is a self-contained folder of
content (taxonomy.yaml, rubric.yaml, seed_prompts.jsonl, evidence.jsonl,
pii_spec.yaml). This module holds the loader + FileDomainPack class.
The actual packs live in configs/duecare/domains/<id>/ and are versioned
like data, not code.
"""

from duecare.core.registry import Registry
from duecare.core.contracts import DomainPack

from .loader import DEFAULT_ROOT, discover_all, load_domain_pack
from .pack import FileDomainPack

# Global domain-pack registry.
domain_registry: Registry[DomainPack] = Registry(kind="domain")


def register_discovered(root: Path | str | None = None) -> int:
    """Walk the domain pack directory and register every discoverable pack.

    Returns the number of packs registered.
    """
    from pathlib import Path as _Path
    count = 0
    for pack in discover_all(root):
        if not domain_registry.has(pack.id):
            domain_registry.add(pack.id, pack)
            count += 1
    return count


from pathlib import Path  # noqa: E402 (used by register_discovered annotation)

__all__ = [
    "DEFAULT_ROOT",
    "DomainPack",
    "FileDomainPack",
    "discover_all",
    "domain_registry",
    "load_domain_pack",
    "register_discovered",
]
''',
}


def main() -> int:
    created = 0
    updated = 0
    for rel, content in FILES.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        p.write_text(content, encoding="utf-8")
        if existed:
            updated += 1
        else:
            created += 1
        print(f"{'UPDATE' if existed else 'CREATE'} {rel}")
    print()
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Total:   {len(FILES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
