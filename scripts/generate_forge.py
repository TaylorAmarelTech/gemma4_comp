#!/usr/bin/env python3
"""
generate_forge.py - Create the Duecare module tree with folder-per-module structure.

Every module lives in its own folder with this consistent layout:

    <module>/
    ├── PURPOSE.md          short + long description
    ├── AGENTS.md           agentic instructions for an AI inspecting this folder
    ├── INPUTS_OUTPUTS.md   what the module reads + writes (contracts, context keys)
    ├── HIERARCHY.md        parent / siblings / children / dependencies / dependents
    ├── DIAGRAM.md          local ASCII diagram of position in system
    ├── TESTS.md            how to run the tests, what each test validates
    ├── STATUS.md           stub / partial / complete + TODO list
    ├── __init__.py
    ├── <source>.py         implementation (generated as stub; dev fills in)
    └── tests/
        ├── __init__.py
        └── test_<source>.py

Consumers (the `duecare` CLI, and AI agents reading the repo) can operate
at any depth. Running `duecare review src/forge/agents/judge` produces a
complete, self-contained summary of that module. Running `duecare review
src/forge/agents` summarizes the whole agent swarm. Running `forge
review src/forge` summarizes the entire system.

Idempotent: only creates files that don't already exist. Existing source
files are never overwritten - only meta files and test stubs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent.parent


# ===========================================================================
# Layer -> package mapping (post multi-package migration)
# ===========================================================================
# Keeps the MODULES list below stable - paths in MODULES use the legacy
# `src/forge/<layer>/<module>` form and are translated at write time.
# Adding a new package = add a row here + add the layer subdir.
# ===========================================================================

LAYER_TO_PACKAGE: dict[str, str] = {
    "core": "duecare-llm-core",
    "observability": "duecare-llm-core",  # folded into core
    "models": "duecare-llm-models",
    "domains": "duecare-llm-domains",
    "tasks": "duecare-llm-tasks",
    "agents": "duecare-llm-agents",
    "workflows": "duecare-llm-workflows",
    "publishing": "duecare-llm-publishing",
}
META_PACKAGE = "duecare-llm"


def normalize_path(legacy: str) -> str:
    """Translate a legacy src/forge/... path to the new packages/... path.

    Examples:
        "src/forge"                           -> "packages/duecare-llm/src/forge"
        "src/forge/core"                      -> "packages/duecare-llm-core/src/forge/core"
        "src/forge/core/contracts"            -> "packages/duecare-llm-core/src/forge/core/contracts"
        "src/forge/agents/judge"              -> "packages/duecare-llm-agents/src/forge/agents/judge"
        "src/forge/observability/logging"     -> "packages/duecare-llm-core/src/forge/observability/logging"

    Paths that don't start with `src/forge` pass through unchanged.
    """
    if not legacy.startswith("src/forge"):
        return legacy
    rest = legacy[len("src/forge"):].lstrip("/")
    if not rest:
        return f"packages/{META_PACKAGE}/src/forge"
    parts = rest.split("/")
    layer = parts[0]
    package = LAYER_TO_PACKAGE.get(layer, META_PACKAGE)
    return f"packages/{package}/src/forge/{rest}"


# ===========================================================================
# Module descriptors
# ===========================================================================
# Each descriptor is a dict with these keys:
#   id           - dot-qualified (e.g., "duecare.agents.judge")
#   path         - filesystem path relative to repo root
#   kind         - "root" | "layer" | "module" | "adapter" | "agent" | "task" | "domain"
#   parent_id    - the parent module's id (None for root)
#   display_name - human-readable
#   one_liner    - single-line purpose
#   description  - longer description for PURPOSE.md
#   reads        - list of context keys or protocols this module consumes
#   writes       - list of context keys or protocols this module produces
#   depends_on   - list of module ids this module depends on
#   source_files - list of source .py filenames (stubs generated)
#   test_files   - list of test .py filenames (stubs generated)
#   status       - "stub" | "partial" | "complete"
#   notes        - optional free-form notes
# ===========================================================================

MODULES: list[dict] = [
    # ---------------- root ----------------
    {
        "id": "duecare",
        "path": "src/forge",
        "kind": "root",
        "parent_id": None,
        "display_name": "Duecare",
        "one_liner": "Agentic, universal LLM safety harness",
        "description": dedent("""
            Duecare is an agentic LLM safety harness. You give it a model and a
            domain pack; a swarm of autonomous agents generates synthetic probes,
            mutates them adversarially, evaluates the target model, identifies
            failure modes, generates corrective training data, fine-tunes the
            model, validates the fine-tune, and publishes the results - all
            without human intervention.

            Model-agnostic (any HF / GGUF / OpenAI-compatible).
            Domain-agnostic (pluggable domain packs).
            See docs/the_forge.md for the full architecture.

            The `forge/` directory at every package's `src/` is a PEP 420
            implicit namespace package. There is intentionally NO __init__.py
            at this level - that would make `duecare` a regular package and
            break the multi-package namespace. The CLI lives at duecare.cli
            (a regular subpackage), not at forge.__init__.
        """).strip(),
        "reads": [],
        "writes": [],
        "depends_on": [],
        "source_files": [],  # PEP 420 namespace - no files at this level
        "test_files": [],
        "status": "partial",
    },

    # ---------------- Layer 1: core ----------------
    {
        "id": "duecare.core",
        "path": "src/forge/core",
        "kind": "layer",
        "parent_id": "duecare",
        "display_name": "Core",
        "one_liner": "Contracts, schemas, enums, registries - imported by every other layer",
        "description": dedent("""
            Core holds the cross-layer contracts. No concrete implementations
            live here. Every other layer (models, domains, tasks, agents,
            workflows, publishing, observability) imports from duecare.core and
            from nothing else above it.

            If a type belongs in more than one layer, it belongs in core.
        """).strip(),
        "reads": [],
        "writes": ["Model protocol", "DomainPack protocol", "Task protocol",
                   "Agent protocol", "Coordinator protocol", "all shared schemas"],
        "depends_on": [],
        "source_files": ["__init__.py"],
        "test_files": [],
        "status": "stub",
    },
    {
        "id": "duecare.core.contracts",
        "path": "src/forge/core/contracts",
        "kind": "module",
        "parent_id": "duecare.core",
        "display_name": "Contracts",
        "one_liner": "Typing protocols for Model, DomainPack, Task, Agent, Coordinator",
        "description": dedent("""
            The five runtime-checkable protocols that define Duecare's cross-
            layer boundaries. Any class that satisfies a protocol is a valid
            plugin; no inheritance is required.

            Model - an LLM backend (local or remote)
            DomainPack - a safety domain (taxonomy + evidence + rubric)
            Task - a capability test
            Agent - an autonomous actor in the swarm
            Coordinator - the agent that orchestrates other agents
        """).strip(),
        "reads": ["duecare.core.enums", "duecare.core.schemas"],
        "writes": ["Model", "DomainPack", "Task", "Agent", "Coordinator"],
        "depends_on": ["duecare.core.enums", "duecare.core.schemas"],
        "source_files": ["__init__.py", "model.py", "domain_pack.py", "task.py", "agent.py", "coordinator.py"],
        "test_files": ["test_protocols_runtime_checkable.py"],
        "status": "stub",
    },
    {
        "id": "duecare.core.schemas",
        "path": "src/forge/core/schemas",
        "kind": "module",
        "parent_id": "duecare.core",
        "display_name": "Schemas",
        "one_liner": "Shared Pydantic models for cross-layer data flow",
        "description": dedent("""
            Every cross-layer data structure is a Pydantic v2 BaseModel living
            here. ChatMessage, ToolSpec, GenerationResult, TaskResult,
            AgentContext, AgentOutput, WorkflowRun, Provenance, DomainCard.

            No business logic in schemas - they are value objects only.
        """).strip(),
        "reads": ["duecare.core.enums"],
        "writes": ["ChatMessage", "ToolSpec", "ToolCall", "GenerationResult",
                   "Embedding", "ModelHealth", "TaskConfig", "TaskResult",
                   "ItemResult", "AgentContext", "AgentOutput", "DomainCard",
                   "WorkflowRun", "Provenance"],
        "depends_on": ["duecare.core.enums"],
        "source_files": ["__init__.py", "chat.py", "generation.py", "task.py",
                         "agent.py", "workflow.py", "domain.py", "provenance.py"],
        "test_files": ["test_schemas_roundtrip.py"],
        "status": "stub",
    },
    {
        "id": "duecare.core.enums",
        "path": "src/forge/core/enums",
        "kind": "module",
        "parent_id": "duecare.core",
        "display_name": "Enums",
        "one_liner": "Canonical enums: Capability, AgentRole, TaskStatus, Grade, Severity",
        "description": dedent("""
            StrEnum classes used as stable identifiers across all layers. Values
            are stable strings, never refactored casually - they end up in
            database rows, JSONL files, and published datasets.
        """).strip(),
        "reads": [],
        "writes": ["Capability", "AgentRole", "TaskStatus", "Grade", "Severity"],
        "depends_on": [],
        "source_files": ["__init__.py", "capability.py", "agent_role.py",
                         "task_status.py", "grade.py", "severity.py"],
        "test_files": ["test_enum_ordinals.py"],
        "status": "stub",
    },
    {
        "id": "duecare.core.registry",
        "path": "src/forge/core/registry",
        "kind": "module",
        "parent_id": "duecare.core",
        "display_name": "Registry",
        "one_liner": "Generic plugin registry used by models, domains, agents, tasks",
        "description": dedent("""
            A single generic Registry[T] class. Every plugin kind (models,
            domains, agents, tasks) has its own registry instance but shares
            the same underlying code. Plugins register themselves on import
            via @registry.register("id").
        """).strip(),
        "reads": [],
        "writes": ["Registry[T]"],
        "depends_on": [],
        "source_files": ["__init__.py", "registry.py"],
        "test_files": ["test_registry.py"],
        "status": "stub",
    },
    {
        "id": "duecare.core.provenance",
        "path": "src/forge/core/provenance",
        "kind": "module",
        "parent_id": "duecare.core",
        "display_name": "Provenance",
        "one_liner": "run_id, git_sha, config_hash - reproducibility helpers",
        "description": dedent("""
            Deterministic helpers for generating run ids, resolving git shas,
            computing config hashes, and producing content checksums. Every
            Duecare run stamps its artifacts with (run_id, git_sha,
            config_hash) so results are reproducible to the byte.
        """).strip(),
        "reads": [],
        "writes": ["generate_run_id", "get_git_sha", "hash_config", "compute_checksum"],
        "depends_on": [],
        "source_files": ["__init__.py", "run_id.py", "git.py", "hashing.py"],
        "test_files": ["test_provenance.py"],
        "status": "stub",
    },

    # ---------------- Layer 2a: models ----------------
    {
        "id": "duecare.models",
        "path": "src/forge/models",
        "kind": "layer",
        "parent_id": "duecare",
        "display_name": "Models",
        "one_liner": "Pluggable adapters for every LLM backend, local or remote",
        "description": dedent("""
            Every model backend (HF Transformers, llama.cpp, Unsloth, Ollama,
            OpenAI-compatible, Anthropic, Google Gemini, HF Inference
            Endpoints) lives here as a self-contained adapter. Each adapter
            implements duecare.core.contracts.Model and registers itself under
            a stable id in the global model_registry.

            Adding a new backend is a new folder - not a refactor.
        """).strip(),
        "reads": ["duecare.core.contracts.Model"],
        "writes": ["model_registry (Registry[Model])"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py"],
        "test_files": ["test_model_registry_populated.py"],
        "status": "stub",
    },
    {
        "id": "duecare.models.base",
        "path": "src/forge/models/base",
        "kind": "module",
        "parent_id": "duecare.models",
        "display_name": "Base",
        "one_liner": "Optional ModelAdapterBase for shared adapter behavior",
        "description": "Optional ABC for adapters that want shared logging, retry, healthcheck defaults. Not required - the Model protocol is duck-typed.",
        "reads": ["duecare.core.contracts.Model"],
        "writes": ["ModelAdapterBase"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "base.py"],
        "test_files": ["test_base.py"],
        "status": "stub",
    },
    {
        "id": "duecare.models.transformers_adapter",
        "path": "src/forge/models/transformers_adapter",
        "kind": "adapter",
        "parent_id": "duecare.models",
        "display_name": "Transformers Adapter",
        "one_liner": "HuggingFace Transformers backend (4-bit via bitsandbytes)",
        "description": "Loads any HF-hosted causal LM with optional 4-bit or 8-bit quantization. Widest model coverage.",
        "reads": ["duecare.core.contracts.Model"],
        "writes": ["TransformersModel (registered as 'transformers')"],
        "depends_on": ["duecare.core", "duecare.models.base"],
        "source_files": ["__init__.py", "adapter.py"],
        "test_files": ["test_adapter.py"],
        "status": "stub",
    },
    {
        "id": "duecare.models.llama_cpp_adapter",
        "path": "src/forge/models/llama_cpp_adapter",
        "kind": "adapter",
        "parent_id": "duecare.models",
        "display_name": "llama.cpp Adapter",
        "one_liner": "GGUF backend via llama-cpp-python for on-device inference",
        "description": "Loads a GGUF file and runs inference on CPU or GPU. Primary runtime for the fine-tuned Duecare model in the live demo.",
        "reads": ["duecare.core.contracts.Model"],
        "writes": ["LlamaCppModel (registered as 'llama_cpp')"],
        "depends_on": ["duecare.core", "duecare.models.base"],
        "source_files": ["__init__.py", "adapter.py"],
        "test_files": ["test_adapter.py"],
        "status": "stub",
    },
    {
        "id": "duecare.models.unsloth_adapter",
        "path": "src/forge/models/unsloth_adapter",
        "kind": "adapter",
        "parent_id": "duecare.models",
        "display_name": "Unsloth Adapter",
        "one_liner": "Unsloth FastLanguageModel backend for fine-tuning and fast inference",
        "description": "Wraps Unsloth's FastLanguageModel. Primary adapter used by the Trainer agent for Gemma 4 LoRA fine-tunes.",
        "reads": ["duecare.core.contracts.Model"],
        "writes": ["UnslothModel (registered as 'unsloth')"],
        "depends_on": ["duecare.core", "duecare.models.base"],
        "source_files": ["__init__.py", "adapter.py"],
        "test_files": ["test_adapter.py"],
        "status": "stub",
    },
    {
        "id": "duecare.models.ollama_adapter",
        "path": "src/forge/models/ollama_adapter",
        "kind": "adapter",
        "parent_id": "duecare.models",
        "display_name": "Ollama Adapter",
        "one_liner": "Local Ollama server backend via its HTTP API",
        "description": "Talks to a local Ollama server. Used for the Ollama Special Tech track prize.",
        "reads": ["duecare.core.contracts.Model"],
        "writes": ["OllamaModel (registered as 'ollama')"],
        "depends_on": ["duecare.core", "duecare.models.base"],
        "source_files": ["__init__.py", "adapter.py"],
        "test_files": ["test_adapter.py"],
        "status": "stub",
    },
    {
        "id": "duecare.models.openai_compatible_adapter",
        "path": "src/forge/models/openai_compatible_adapter",
        "kind": "adapter",
        "parent_id": "duecare.models",
        "display_name": "OpenAI-Compatible Adapter",
        "one_liner": "Any provider exposing the OpenAI Chat Completions schema",
        "description": "Covers OpenAI, DeepSeek, Together, Groq, Fireworks, OpenRouter, and any other provider that implements the OpenAI schema.",
        "reads": ["duecare.core.contracts.Model"],
        "writes": ["OpenAICompatibleModel (registered as 'openai_compatible')"],
        "depends_on": ["duecare.core", "duecare.models.base"],
        "source_files": ["__init__.py", "adapter.py"],
        "test_files": ["test_adapter.py"],
        "status": "stub",
    },
    {
        "id": "duecare.models.anthropic_adapter",
        "path": "src/forge/models/anthropic_adapter",
        "kind": "adapter",
        "parent_id": "duecare.models",
        "display_name": "Anthropic Adapter",
        "one_liner": "Native Claude Messages API adapter",
        "description": "Uses the native Anthropic Messages API (not an OpenAI proxy). Claude is a reference model in the comparison field.",
        "reads": ["duecare.core.contracts.Model"],
        "writes": ["AnthropicModel (registered as 'anthropic')"],
        "depends_on": ["duecare.core", "duecare.models.base"],
        "source_files": ["__init__.py", "adapter.py"],
        "test_files": ["test_adapter.py"],
        "status": "stub",
    },
    {
        "id": "duecare.models.google_gemini_adapter",
        "path": "src/forge/models/google_gemini_adapter",
        "kind": "adapter",
        "parent_id": "duecare.models",
        "display_name": "Google Gemini Adapter",
        "one_liner": "Google Gemini API adapter (separate from Gemma local adapters)",
        "description": "Hosted Gemini models via google-generativeai. Gemma runs through the Transformers/Unsloth/llama.cpp adapters locally; Gemini uses this adapter.",
        "reads": ["duecare.core.contracts.Model"],
        "writes": ["GoogleGeminiModel (registered as 'google_gemini')"],
        "depends_on": ["duecare.core", "duecare.models.base"],
        "source_files": ["__init__.py", "adapter.py"],
        "test_files": ["test_adapter.py"],
        "status": "stub",
    },
    {
        "id": "duecare.models.hf_inference_endpoint_adapter",
        "path": "src/forge/models/hf_inference_endpoint_adapter",
        "kind": "adapter",
        "parent_id": "duecare.models",
        "display_name": "HF Inference Endpoint Adapter",
        "one_liner": "HuggingFace Inference Endpoints backend",
        "description": "Calls any HF-hosted endpoint without downloading the model locally. Useful for arbitrary community models.",
        "reads": ["duecare.core.contracts.Model"],
        "writes": ["HFInferenceEndpointModel (registered as 'hf_inference_endpoint')"],
        "depends_on": ["duecare.core", "duecare.models.base"],
        "source_files": ["__init__.py", "adapter.py"],
        "test_files": ["test_adapter.py"],
        "status": "stub",
    },

    # ---------------- Layer 2b: domains ----------------
    {
        "id": "duecare.domains",
        "path": "src/forge/domains",
        "kind": "layer",
        "parent_id": "duecare",
        "display_name": "Domains",
        "one_liner": "Pluggable domain packs (taxonomy + evidence + rubric)",
        "description": dedent("""
            A domain pack is a self-contained folder of content (taxonomy.yaml,
            rubric.yaml, seed_prompts.jsonl, evidence.jsonl, pii_spec.yaml).
            This module holds the LOADER and PACK class. The actual packs
            live in configs/duecare/domains/<id>/ and are versioned like data,
            not code.
        """).strip(),
        "reads": ["duecare.core.contracts.DomainPack"],
        "writes": ["domain_registry (Registry[DomainPack])"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py"],
        "test_files": ["test_domain_loader.py"],
        "status": "stub",
    },
    {
        "id": "duecare.domains.pack",
        "path": "src/forge/domains/pack",
        "kind": "module",
        "parent_id": "duecare.domains",
        "display_name": "Pack",
        "one_liner": "FileDomainPack - a filesystem-backed DomainPack implementation",
        "description": "Reads a configs/duecare/domains/<id>/ folder and exposes it via the DomainPack protocol.",
        "reads": ["duecare.core.contracts.DomainPack", "configs/duecare/domains/*/"],
        "writes": ["FileDomainPack"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "file_domain_pack.py"],
        "test_files": ["test_file_domain_pack.py"],
        "status": "stub",
    },
    {
        "id": "duecare.domains.loader",
        "path": "src/forge/domains/loader",
        "kind": "module",
        "parent_id": "duecare.domains",
        "display_name": "Loader",
        "one_liner": "Discovery + loading of domain packs from configs/duecare/domains/",
        "description": "Walks configs/duecare/domains/, validates each pack's card.yaml, and registers them in domain_registry.",
        "reads": ["duecare.domains.pack"],
        "writes": ["load_domain_pack()", "discover_all()"],
        "depends_on": ["duecare.core", "duecare.domains.pack"],
        "source_files": ["__init__.py", "loader.py"],
        "test_files": ["test_loader.py"],
        "status": "stub",
    },

    # ---------------- Layer 3: tasks ----------------
    {
        "id": "duecare.tasks",
        "path": "src/forge/tasks",
        "kind": "layer",
        "parent_id": "duecare",
        "display_name": "Tasks",
        "one_liner": "Capability tests runnable against any (Model, DomainPack) pair",
        "description": dedent("""
            A task is a pure function: (model, domain, config) -> TaskResult.
            Tasks do not call tools, maintain state, or make decisions -
            decisions live in agents. Every task declares its required
            capabilities (text, vision, function_calling) and will refuse
            to run against a model that doesn't support them.
        """).strip(),
        "reads": ["duecare.core.contracts.Task"],
        "writes": ["task_registry (Registry[Task])"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py"],
        "test_files": ["test_task_registry_populated.py"],
        "status": "stub",
    },
    {
        "id": "duecare.tasks.base",
        "path": "src/forge/tasks/base",
        "kind": "module",
        "parent_id": "duecare.tasks",
        "display_name": "Base",
        "one_liner": "Helpers shared by all tasks (fresh_task_result, etc.)",
        "description": "Common helpers so each task file can focus on its specific logic.",
        "reads": ["duecare.core"],
        "writes": ["fresh_task_result()"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "base.py"],
        "test_files": ["test_base.py"],
        "status": "stub",
    },
    {
        "id": "duecare.tasks.guardrails",
        "path": "src/forge/tasks/guardrails",
        "kind": "task",
        "parent_id": "duecare.tasks",
        "display_name": "Guardrails Task",
        "one_liner": "Response policy guardrails - refusal quality, citations, redirects",
        "description": "Tests whether the model refuses appropriately, cites domain-specific authorities (ILO, Palermo, national labor law), and redirects to protective resources.",
        "reads": ["duecare.core.contracts.Model", "duecare.core.contracts.DomainPack"],
        "writes": ["TaskResult with grade exact-match, grade-within-1, ILO indicator recall/precision, doc ref precision"],
        "depends_on": ["duecare.core", "duecare.tasks.base"],
        "source_files": ["__init__.py", "guardrails.py"],
        "test_files": ["test_guardrails.py"],
        "status": "stub",
    },
    {
        "id": "duecare.tasks.anonymization",
        "path": "src/forge/tasks/anonymization",
        "kind": "task",
        "parent_id": "duecare.tasks",
        "display_name": "Anonymization Task",
        "one_liner": "PII detection and redaction quality",
        "description": "Tests whether the model can identify PII categories from a domain's pii_spec.yaml and redact them correctly. Scored on span-level recall + precision.",
        "reads": ["duecare.core.contracts.Model", "duecare.core.contracts.DomainPack"],
        "writes": ["TaskResult with PII span recall, precision, false positive rate"],
        "depends_on": ["duecare.core", "duecare.tasks.base"],
        "source_files": ["__init__.py", "anonymization.py"],
        "test_files": ["test_anonymization.py"],
        "status": "stub",
    },
    {
        "id": "duecare.tasks.classification",
        "path": "src/forge/tasks/classification",
        "kind": "task",
        "parent_id": "duecare.tasks",
        "display_name": "Classification Task",
        "one_liner": "Multi-label classification against the domain taxonomy",
        "description": "Tests whether the model can assign sector / corridor / indicator / attack category labels per the domain's taxonomy.yaml.",
        "reads": ["duecare.core.contracts.Model", "duecare.core.contracts.DomainPack"],
        "writes": ["TaskResult with per-label accuracy + multi-label F1"],
        "depends_on": ["duecare.core", "duecare.tasks.base"],
        "source_files": ["__init__.py", "classification.py"],
        "test_files": ["test_classification.py"],
        "status": "stub",
    },
    {
        "id": "duecare.tasks.fact_extraction",
        "path": "src/forge/tasks/fact_extraction",
        "kind": "task",
        "parent_id": "duecare.tasks",
        "display_name": "Fact Extraction Task",
        "one_liner": "Structured fact extraction (entities, amounts, dates, citations)",
        "description": "Tests whether the model can pull structured facts (person, organization, location, currency, date, citation) out of free-text source documents.",
        "reads": ["duecare.core.contracts.Model", "duecare.core.contracts.DomainPack"],
        "writes": ["TaskResult with entity-level F1 by category"],
        "depends_on": ["duecare.core", "duecare.tasks.base"],
        "source_files": ["__init__.py", "fact_extraction.py"],
        "test_files": ["test_fact_extraction.py"],
        "status": "stub",
    },
    {
        "id": "duecare.tasks.grounding",
        "path": "src/forge/tasks/grounding",
        "kind": "task",
        "parent_id": "duecare.tasks",
        "display_name": "Grounding Task",
        "one_liner": "Evidence grounding - does the model cite verified domain evidence?",
        "description": "Tests whether the model grounds its response in the domain pack's evidence.jsonl, citing verifiable sources rather than confabulating.",
        "reads": ["duecare.core.contracts.Model", "duecare.core.contracts.DomainPack"],
        "writes": ["TaskResult with citation precision + evidence hit rate"],
        "depends_on": ["duecare.core", "duecare.tasks.base"],
        "source_files": ["__init__.py", "grounding.py"],
        "test_files": ["test_grounding.py"],
        "status": "stub",
    },
    {
        "id": "duecare.tasks.multimodal_classification",
        "path": "src/forge/tasks/multimodal_classification",
        "kind": "task",
        "parent_id": "duecare.tasks",
        "display_name": "Multimodal Classification Task",
        "one_liner": "Classify a document from a photograph using the model's vision head",
        "description": "Tests Gemma 4's vision capability. Loads document images from the domain pack's images/ subfolder, classifies each, and scores against ground truth.",
        "reads": ["duecare.core.contracts.Model (requires Capability.VISION)", "duecare.core.contracts.DomainPack"],
        "writes": ["TaskResult with multimodal classification accuracy"],
        "depends_on": ["duecare.core", "duecare.tasks.base"],
        "source_files": ["__init__.py", "multimodal_classification.py"],
        "test_files": ["test_multimodal_classification.py"],
        "status": "stub",
    },
    {
        "id": "duecare.tasks.adversarial_multi_turn",
        "path": "src/forge/tasks/adversarial_multi_turn",
        "kind": "task",
        "parent_id": "duecare.tasks",
        "display_name": "Adversarial Multi-Turn Task",
        "one_liner": "Resistance to Crescendo / FITD / Role Chain multi-turn attacks",
        "description": "Runs the Adversary agent's multi-turn chains (Crescendo, FITD, RoleChain, ContextPoisoning) and measures the target model's resistance across turns.",
        "reads": ["duecare.core.contracts.Model", "duecare.core.contracts.DomainPack"],
        "writes": ["TaskResult with per-chain survival rate"],
        "depends_on": ["duecare.core", "duecare.tasks.base", "duecare.agents.adversary"],
        "source_files": ["__init__.py", "adversarial_multi_turn.py"],
        "test_files": ["test_adversarial_multi_turn.py"],
        "status": "stub",
    },
    {
        "id": "duecare.tasks.tool_use",
        "path": "src/forge/tasks/tool_use",
        "kind": "task",
        "parent_id": "duecare.tasks",
        "display_name": "Tool Use Task",
        "one_liner": "Correct use of domain tools via native function calling",
        "description": "Tests Gemma 4's native function calling on a synthetic tool set (anonymize, classify, retrieve_evidence, extract_facts). The target model must call the right tool with the right arguments in the right order.",
        "reads": ["duecare.core.contracts.Model (requires Capability.FUNCTION_CALLING)"],
        "writes": ["TaskResult with tool-call correctness score"],
        "depends_on": ["duecare.core", "duecare.tasks.base"],
        "source_files": ["__init__.py", "tool_use.py"],
        "test_files": ["test_tool_use.py"],
        "status": "stub",
    },
    {
        "id": "duecare.tasks.cross_lingual",
        "path": "src/forge/tasks/cross_lingual",
        "kind": "task",
        "parent_id": "duecare.tasks",
        "display_name": "Cross-Lingual Task",
        "one_liner": "Guardrails in non-English languages (Tagalog, Nepali, Arabic, Bahasa, Spanish)",
        "description": "Runs the guardrails test in the languages provided under the domain pack's locale/ subfolder. Measures whether refusal quality degrades across languages.",
        "reads": ["duecare.core.contracts.Model", "duecare.core.contracts.DomainPack"],
        "writes": ["TaskResult broken down per-language"],
        "depends_on": ["duecare.core", "duecare.tasks.base"],
        "source_files": ["__init__.py", "cross_lingual.py"],
        "test_files": ["test_cross_lingual.py"],
        "status": "stub",
    },

    # ---------------- Layer 4: agents ----------------
    {
        "id": "duecare.agents",
        "path": "src/forge/agents",
        "kind": "layer",
        "parent_id": "duecare",
        "display_name": "Agents",
        "one_liner": "The 12-agent Duecare swarm",
        "description": dedent("""
            Autonomous actors that compose tasks into workflows. Each agent
            has a role (from duecare.core.enums.AgentRole), a model it uses
            internally, a set of tools it can call, declared inputs/outputs,
            and a cost budget.

            Agents are the only layer that makes decisions. Tasks compute;
            agents decide; the Coordinator orchestrates.
        """).strip(),
        "reads": ["duecare.core.contracts.Agent", "duecare.tasks"],
        "writes": ["agent_registry (Registry[Agent])"],
        "depends_on": ["duecare.core", "duecare.tasks"],
        "source_files": ["__init__.py"],
        "test_files": ["test_agent_registry_populated.py"],
        "status": "stub",
    },
    {
        "id": "duecare.agents.base",
        "path": "src/forge/agents/base",
        "kind": "module",
        "parent_id": "duecare.agents",
        "display_name": "Base",
        "one_liner": "Helpers shared by all agents",
        "description": "AgentContext initialization, fresh_agent_output helpers, shared tool specs.",
        "reads": ["duecare.core"],
        "writes": ["fresh_agent_output()"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "base.py"],
        "test_files": ["test_base.py"],
        "status": "stub",
    },
    {
        "id": "duecare.agents.scout",
        "path": "src/forge/agents/scout",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "Scout Agent",
        "one_liner": "Profile the domain pack and score its completeness",
        "description": dedent("""
            First agent in every workflow. Reads the domain pack, counts
            indicators / categories / evidence items / seed prompts, and
            emits a domain_readiness_score. Uses Gemma 4 E4B (fast, cheap,
            local) to describe coverage gaps qualitatively.
        """).strip(),
        "reads": ["domain_pack (via ctx.domain_id)"],
        "writes": ["domain_readiness_score", "domain_gaps"],
        "depends_on": ["duecare.core", "duecare.agents.base", "duecare.domains"],
        "source_files": ["__init__.py", "scout.py"],
        "test_files": ["test_scout.py"],
        "status": "stub",
    },
    {
        "id": "duecare.agents.data_generator",
        "path": "src/forge/agents/data_generator",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "DataGenerator Agent",
        "one_liner": "Synthesize probes + graded response examples using a strong teacher model",
        "description": dedent("""
            Calls a strong teacher model (Claude Haiku 4.5 or Gemini Flash
            by default; configurable) to generate synthetic probes tailored
            to the domain pack's taxonomy, plus graded response examples
            (worst/bad/neutral/good/best) for each probe.

            Uses self-consistency: generate N candidate responses, let the
            Judge agent pick the best, mark the unselected as lower grades.
        """).strip(),
        "reads": ["domain_readiness_score", "domain_gaps"],
        "writes": ["synthetic_probes", "graded_examples"],
        "depends_on": ["duecare.core", "duecare.agents.base", "duecare.agents.judge"],
        "source_files": ["__init__.py", "data_generator.py"],
        "test_files": ["test_data_generator.py"],
        "status": "stub",
        "notes": "Budget-capped at $20/run by default.",
    },
    {
        "id": "duecare.agents.adversary",
        "path": "src/forge/agents/adversary",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "Adversary Agent",
        "one_liner": "Mutate probes through 631 prompt-injection mutators + 126 attack chains",
        "description": dedent("""
            Pure rule-based agent (no LLM calls) that imports the reference
            framework's prompt_injection registry and chain_detection seeds
            as a sidecar dependency. Takes probes from DataGenerator and
            produces adversarial variants stress-testing the target model.
        """).strip(),
        "reads": ["synthetic_probes"],
        "writes": ["adversarial_probes"],
        "depends_on": ["duecare.core", "duecare.agents.base", "_reference/framework/src/prompt_injection"],
        "source_files": ["__init__.py", "adversary.py"],
        "test_files": ["test_adversary.py"],
        "status": "stub",
        "notes": "Depends on the reference framework as a sidecar path dependency.",
    },
    {
        "id": "duecare.agents.anonymizer",
        "path": "src/forge/agents/anonymizer",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "Anonymizer Agent",
        "one_liner": "Hard PII gate - no raw PII passes this point",
        "description": dedent("""
            Detects PII via Presidio + regex + Gemma 4 E2B NER, applies
            anonymization strategies (redact / tokenize / generalize /
            drop), then re-scans via a verifier. Items that still contain
            PII after anonymization go to quarantine.

            This is a hard gate: downstream agents cannot read the raw
            probe store, only the clean output.
        """).strip(),
        "reads": ["synthetic_probes", "adversarial_probes"],
        "writes": ["clean_probes", "anon_audit", "quarantine"],
        "depends_on": ["duecare.core", "duecare.agents.base"],
        "source_files": ["__init__.py", "anonymizer.py"],
        "test_files": ["test_anonymizer.py"],
        "status": "stub",
        "notes": "Audit log stores SHA256 of original content, never raw PII.",
    },
    {
        "id": "duecare.agents.curator",
        "path": "src/forge/agents/curator",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "Curator Agent",
        "one_liner": "Dedupe, stratify, split into train/val/test",
        "description": "SimHash-based deduplication, stratified splitting by (category, grade, corridor), held out by source_case_id to prevent leakage.",
        "reads": ["clean_probes"],
        "writes": ["train_jsonl", "val_jsonl", "test_jsonl", "split_stats"],
        "depends_on": ["duecare.core", "duecare.agents.base"],
        "source_files": ["__init__.py", "curator.py"],
        "test_files": ["test_curator.py"],
        "status": "stub",
    },
    {
        "id": "duecare.agents.judge",
        "path": "src/forge/agents/judge",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "Judge Agent",
        "one_liner": "Score model outputs against the domain rubric in 4 modes",
        "description": dedent("""
            Scores the target model's outputs against the domain rubric
            using four modes: rule-based (fast, deterministic), embedding
            (similarity to graded examples), llm_judge (another LLM as
            rubric executor), and hybrid (weighted ensemble).

            Used both to populate graded examples for training and to
            evaluate the fine-tuned judge at benchmark time.
        """).strip(),
        "reads": ["test_jsonl"],
        "writes": ["evaluation_results", "per_category_breakdown"],
        "depends_on": ["duecare.core", "duecare.agents.base", "duecare.tasks"],
        "source_files": ["__init__.py", "judge.py"],
        "test_files": ["test_judge.py"],
        "status": "stub",
    },
    {
        "id": "duecare.agents.validator",
        "path": "src/forge/agents/validator",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "Validator Agent",
        "one_liner": "Red-team the trained model, issue the no-harm certificate",
        "description": dedent("""
            After the Trainer agent produces a fine-tuned model, Validator
            runs a held-out adversarial suite against it. Before/after
            delta per capability test. Hard stop: if the trained model is
            more harmful than the base on any category, Validator aborts
            the release and Historian writes the incident report.
        """).strip(),
        "reads": ["trained_model_path", "adversarial_probes"],
        "writes": ["validation_report", "no_harm_certificate", "regression_list"],
        "depends_on": ["duecare.core", "duecare.agents.base", "duecare.agents.adversary"],
        "source_files": ["__init__.py", "validator.py"],
        "test_files": ["test_validator.py"],
        "status": "stub",
    },
    {
        "id": "duecare.agents.curriculum_designer",
        "path": "src/forge/agents/curriculum_designer",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "CurriculumDesigner Agent",
        "one_liner": "Cluster failures, plan the next training iteration",
        "description": "Reads the Judge's evaluation results, clusters failures by category / sector / corridor / indicator, and emits a next_curriculum specification that DataGenerator uses to produce targeted training data.",
        "reads": ["evaluation_results"],
        "writes": ["next_curriculum"],
        "depends_on": ["duecare.core", "duecare.agents.base"],
        "source_files": ["__init__.py", "curriculum_designer.py"],
        "test_files": ["test_curriculum_designer.py"],
        "status": "stub",
    },
    {
        "id": "duecare.agents.trainer",
        "path": "src/forge/agents/trainer",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "Trainer Agent",
        "one_liner": "Run Unsloth + LoRA fine-tune on the curated dataset",
        "description": dedent("""
            Loads the base model via the Unsloth adapter, applies the LoRA
            config, runs SFTTrainer (or DPO as a stretch goal), checkpoints
            periodically, and saves LoRA adapters + merged fp16 weights.
        """).strip(),
        "reads": ["train_jsonl", "val_jsonl", "next_curriculum"],
        "writes": ["lora_adapters", "merged_fp16", "training_log"],
        "depends_on": ["duecare.core", "duecare.agents.base", "duecare.models.unsloth_adapter"],
        "source_files": ["__init__.py", "trainer.py"],
        "test_files": ["test_trainer.py"],
        "status": "stub",
    },
    {
        "id": "duecare.agents.exporter",
        "path": "src/forge/agents/exporter",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "Exporter Agent",
        "one_liner": "Convert, quantize, publish to HF Hub + Kaggle Models",
        "description": "Takes the merged fp16 weights, converts to GGUF (q4_k_m / q5_k_m / q8_0) and optionally LiteRT, generates the model card, and uploads to HF Hub + Kaggle Models.",
        "reads": ["merged_fp16", "no_harm_certificate"],
        "writes": ["gguf_paths", "litert_paths", "hf_hub_url", "kaggle_model_url"],
        "depends_on": ["duecare.core", "duecare.agents.base", "duecare.publishing"],
        "source_files": ["__init__.py", "exporter.py"],
        "test_files": ["test_exporter.py"],
        "status": "stub",
    },
    {
        "id": "duecare.agents.historian",
        "path": "src/forge/agents/historian",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "Historian Agent",
        "one_liner": "Narrative assembly - write the run report and the Kaggle notebook",
        "description": dedent("""
            Reads all run artifacts and metrics, then uses Gemma 4 E4B as a
            writer to produce the final markdown report and the Kaggle
            submission notebook. Last agent in every workflow.
        """).strip(),
        "reads": ["*"],
        "writes": ["run_md", "summary_md", "submission_notebook"],
        "depends_on": ["duecare.core", "duecare.agents.base", "duecare.publishing.reports"],
        "source_files": ["__init__.py", "historian.py"],
        "test_files": ["test_historian.py"],
        "status": "stub",
    },
    {
        "id": "duecare.agents.coordinator",
        "path": "src/forge/agents/coordinator",
        "kind": "agent",
        "parent_id": "duecare.agents",
        "display_name": "Coordinator Agent",
        "one_liner": "Orchestrates the 12-agent swarm via a workflow DAG",
        "description": dedent("""
            Special agent. In the default deployment, the Coordinator IS
            Gemma 4 E4B using native function calling to schedule the
            swarm - each other agent is exposed to it as a tool.

            Falls back to a rule-based DAG walker if function calling is
            not available on the configured model.
        """).strip(),
        "reads": ["workflow_yaml"],
        "writes": ["workflow_run"],
        "depends_on": ["duecare.core", "duecare.agents.base", "duecare.workflows"],
        "source_files": ["__init__.py", "coordinator.py"],
        "test_files": ["test_coordinator.py"],
        "status": "stub",
        "notes": "The Coordinator's tools are the other 11 agents.",
    },

    # ---------------- Layer 5: workflows ----------------
    {
        "id": "duecare.workflows",
        "path": "src/forge/workflows",
        "kind": "layer",
        "parent_id": "duecare",
        "display_name": "Workflows",
        "one_liner": "DAG orchestration - workflow YAML loader, runner, scheduler",
        "description": "A workflow is a YAML file under configs/duecare/workflows/ describing the agent DAG. This module loads, validates, and runs them.",
        "reads": ["configs/duecare/workflows/*.yaml"],
        "writes": ["WorkflowRun records"],
        "depends_on": ["duecare.core", "duecare.agents"],
        "source_files": ["__init__.py"],
        "test_files": ["test_workflows.py"],
        "status": "stub",
    },
    {
        "id": "duecare.workflows.loader",
        "path": "src/forge/workflows/loader",
        "kind": "module",
        "parent_id": "duecare.workflows",
        "display_name": "Loader",
        "one_liner": "YAML -> Workflow Pydantic model",
        "description": "Parses and validates a workflow YAML file into a Workflow BaseModel.",
        "reads": ["YAML files"],
        "writes": ["Workflow"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "loader.py"],
        "test_files": ["test_loader.py"],
        "status": "stub",
    },
    {
        "id": "duecare.workflows.runner",
        "path": "src/forge/workflows/runner",
        "kind": "module",
        "parent_id": "duecare.workflows",
        "display_name": "Runner",
        "one_liner": "Executes a Workflow by walking the agent DAG",
        "description": "Resolves agents from agent_registry, walks the DAG in topological order, calls each agent's execute(), merges outputs, handles retries and budget caps.",
        "reads": ["Workflow", "agent_registry"],
        "writes": ["WorkflowRun"],
        "depends_on": ["duecare.core", "duecare.agents", "duecare.workflows.loader"],
        "source_files": ["__init__.py", "runner.py"],
        "test_files": ["test_runner.py"],
        "status": "stub",
    },
    {
        "id": "duecare.workflows.dag",
        "path": "src/forge/workflows/dag",
        "kind": "module",
        "parent_id": "duecare.workflows",
        "display_name": "DAG",
        "one_liner": "Topological sort, dependency resolution, parallelism",
        "description": "Pure graph utilities. No LLM calls, no I/O. Used by the Runner.",
        "reads": ["list of AgentStep"],
        "writes": ["execution_order", "parallel_groups"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "dag.py"],
        "test_files": ["test_dag.py"],
        "status": "stub",
    },

    # ---------------- Layer 6: publishing ----------------
    {
        "id": "duecare.publishing",
        "path": "src/forge/publishing",
        "kind": "layer",
        "parent_id": "duecare",
        "display_name": "Publishing",
        "one_liner": "HF Hub, Kaggle Datasets + Models, reports, model cards",
        "description": "Everything the Exporter and Historian agents need to turn run artifacts into public deliverables.",
        "reads": ["run artifacts"],
        "writes": ["HF Hub URLs", "Kaggle URLs", "markdown reports", "model cards"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py"],
        "test_files": [],
        "status": "stub",
    },
    {
        "id": "duecare.publishing.hf_hub",
        "path": "src/forge/publishing/hf_hub",
        "kind": "module",
        "parent_id": "duecare.publishing",
        "display_name": "HF Hub",
        "one_liner": "HuggingFace Hub upload for weights + datasets",
        "description": "Thin wrapper over huggingface_hub for pushing LoRA adapters, merged weights, GGUF files, and HF Datasets.",
        "reads": ["artifact paths"],
        "writes": ["HF Hub URL"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "hf_hub.py"],
        "test_files": ["test_hf_hub.py"],
        "status": "stub",
    },
    {
        "id": "duecare.publishing.kaggle",
        "path": "src/forge/publishing/kaggle",
        "kind": "module",
        "parent_id": "duecare.publishing",
        "display_name": "Kaggle",
        "one_liner": "Kaggle Datasets + Models + Kernels publisher",
        "description": "Thin wrapper over the Kaggle CLI for pushing datasets, models, and notebooks.",
        "reads": ["artifact paths"],
        "writes": ["Kaggle Dataset URL", "Kaggle Model URL", "Kaggle Kernel URL"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "kaggle.py"],
        "test_files": ["test_kaggle.py"],
        "status": "stub",
    },
    {
        "id": "duecare.publishing.reports",
        "path": "src/forge/publishing/reports",
        "kind": "module",
        "parent_id": "duecare.publishing",
        "display_name": "Reports",
        "one_liner": "Markdown report generator used by the Historian agent",
        "description": "Templates and renderers for run reports, summaries, and the submission notebook.",
        "reads": ["run artifacts + metrics"],
        "writes": ["run.md", "summary.md", "submission.ipynb"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "reports.py"],
        "test_files": ["test_reports.py"],
        "status": "stub",
    },
    {
        "id": "duecare.publishing.model_card",
        "path": "src/forge/publishing/model_card",
        "kind": "module",
        "parent_id": "duecare.publishing",
        "display_name": "Model Card",
        "one_liner": "Generate HF Hub-compatible model cards from run metrics",
        "description": "Follows the HuggingFace model card template: intended use, out-of-scope use, training data summary, evaluation results, risks, license, citation.",
        "reads": ["run metrics + training config"],
        "writes": ["model_card.md"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "model_card.py"],
        "test_files": ["test_model_card.py"],
        "status": "stub",
    },

    # ---------------- observability ----------------
    {
        "id": "duecare.observability",
        "path": "src/forge/observability",
        "kind": "layer",
        "parent_id": "duecare",
        "display_name": "Observability",
        "one_liner": "Logging + metrics + audit trails",
        "description": "structlog-based logging (never logs PII), JSON metric sinks, and append-only audit trails.",
        "reads": [],
        "writes": ["logs/*.jsonl", "metrics/*.jsonl", "audit.sqlite"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py"],
        "test_files": [],
        "status": "stub",
    },
    {
        "id": "duecare.observability.logging",
        "path": "src/forge/observability/logging",
        "kind": "module",
        "parent_id": "duecare.observability",
        "display_name": "Logging",
        "one_liner": "structlog configuration with a PII filter",
        "description": "Configures structlog with JSON output. A filter rejects any log record whose payload contains content flagged by the anonymizer detectors.",
        "reads": [],
        "writes": ["logs/forge.jsonl"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "logging.py"],
        "test_files": ["test_logging.py"],
        "status": "stub",
    },
    {
        "id": "duecare.observability.metrics",
        "path": "src/forge/observability/metrics",
        "kind": "module",
        "parent_id": "duecare.observability",
        "display_name": "Metrics",
        "one_liner": "JSON-line metrics sink for training / eval / inference",
        "description": "Append-only metrics store. Each row: (run_id, agent_id, metric_name, value, timestamp).",
        "reads": [],
        "writes": ["metrics/*.jsonl"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "metrics.py"],
        "test_files": ["test_metrics.py"],
        "status": "stub",
    },
    {
        "id": "duecare.observability.audit",
        "path": "src/forge/observability/audit",
        "kind": "module",
        "parent_id": "duecare.observability",
        "display_name": "Audit",
        "one_liner": "Append-only audit trail for anonymization + training decisions",
        "description": "SQLite-backed audit log. Stores hashes of redacted content, never plaintext.",
        "reads": [],
        "writes": ["audit.sqlite"],
        "depends_on": ["duecare.core"],
        "source_files": ["__init__.py", "audit.py"],
        "test_files": ["test_audit.py"],
        "status": "stub",
    },
]


# Build a map by id for easy lookup
MODULE_BY_ID = {m["id"]: m for m in MODULES}


# ===========================================================================
# Meta-file templates
# ===========================================================================

def render_purpose(m: dict) -> str:
    return (
        f"# Purpose — {m['display_name']}\n"
        f"\n"
        f"> {m['one_liner']}\n"
        f"\n"
        f"## Long description\n"
        f"\n"
        f"{m['description']}\n"
        f"\n"
        f"## Module id\n"
        f"\n"
        f"`{m['id']}`\n"
        f"\n"
        f"## Kind\n"
        f"\n"
        f"{m['kind']}\n"
        f"\n"
        f"## Status\n"
        f"\n"
        f"`{m['status']}`\n"
        f"\n"
        f"See `STATUS.md` for the TODO list and completion criteria.\n"
        + (f"\n## Notes\n\n{m['notes']}\n" if m.get("notes") else "")
    )


def render_agents(m: dict) -> str:
    source_file_list = ", ".join(m.get("source_files", [])) or "(none yet)"
    return (
        f"# Agent instructions — {m['display_name']}\n"
        f"\n"
        f"> If you are an AI assistant inspecting this folder, start here.\n"
        f"\n"
        f"## What this module does\n"
        f"\n"
        f"{m['one_liner']}\n"
        f"\n"
        f"See `PURPOSE.md` for the full description.\n"
        f"\n"
        f"## How to read this folder\n"
        f"\n"
        f"- `PURPOSE.md` — short + long description\n"
        f"- `INPUTS_OUTPUTS.md` — context keys / protocols this module reads + writes\n"
        f"- `HIERARCHY.md` — parent, siblings, children, dependencies\n"
        f"- `DIAGRAM.md` — local position in the system\n"
        f"- `TESTS.md` — how to run tests, what each test validates\n"
        f"- `STATUS.md` — current completion state and TODO list\n"
        f"- Source files: {source_file_list}\n"
        f"- `tests/` — isolated tests for this module\n"
        f"\n"
        f"## How to modify this module safely\n"
        f"\n"
        f"1. Read `PURPOSE.md` and `INPUTS_OUTPUTS.md` to understand the contract.\n"
        f"2. Look at `tests/` to see what's currently verified.\n"
        f"3. Check `HIERARCHY.md` to see what depends on this module.\n"
        f"4. Make the change.\n"
        f"5. Run `duecare test {m['path']}` to verify.\n"
        f"6. If the test suite passes, the change is safe.\n"
        f"\n"
        f"## Do NOT\n"
        f"\n"
        f"- Add dependencies on concrete classes from sibling modules\n"
        f"- Break the protocols declared in `src/forge/core/contracts/`\n"
        f"- Remove or rename public symbols without updating `HIERARCHY.md`\n"
        f"- Log or persist PII under any circumstance\n"
        f"\n"
        f"## How to navigate up or down\n"
        f"\n"
        f"- Up one level: see `../AGENTS.md`\n"
        f"- Top of the tree: see `src/forge/AGENTS.md`\n"
        f"- Full system overview: see `docs/the_forge.md`\n"
    )


def render_inputs_outputs(m: dict) -> str:
    reads = m.get("reads", [])
    writes = m.get("writes", [])
    deps = m.get("depends_on", [])
    reads_block = "\n".join(f"- `{r}`" for r in reads) if reads else "- (none — leaf module)"
    writes_block = "\n".join(f"- `{w}`" for w in writes) if writes else "- (none — this is a layer root or marker)"
    deps_block = "\n".join(f"- `{d}`" for d in deps) if deps else "- (none)"
    return (
        f"# Inputs & Outputs — {m['display_name']}\n"
        f"\n"
        f"## Reads (inputs)\n"
        f"\n"
        f"{reads_block}\n"
        f"\n"
        f"## Writes (outputs)\n"
        f"\n"
        f"{writes_block}\n"
        f"\n"
        f"## Depends on (other modules)\n"
        f"\n"
        f"{deps_block}\n"
        f"\n"
        f"## Contract\n"
        f"\n"
        f"The public surface of this module (its stable contract) is defined\n"
        f"by the protocol(s) in `src/forge/core/contracts/` that it implements,\n"
        f"plus any symbols listed in its `__init__.py` under `__all__`.\n"
        f"\n"
        f"Changes that affect any of the above require updating `HIERARCHY.md`\n"
        f"on every dependent module (listed in `HIERARCHY.md`).\n"
    )


def render_hierarchy(m: dict) -> str:
    # breadcrumb
    crumbs = []
    cur = m
    while cur is not None:
        crumbs.append(cur["display_name"])
        parent_id = cur.get("parent_id")
        cur = MODULE_BY_ID.get(parent_id) if parent_id else None
    crumbs.reverse()
    breadcrumb = " / ".join(f"[{c}]" for c in crumbs)

    parent = MODULE_BY_ID.get(m.get("parent_id")) if m.get("parent_id") else None
    parent_block = (
        f"- `{parent['id']}` (`{parent['path']}`)"
        if parent else "- (none — this is the root)"
    )

    siblings = [
        other for other in MODULES
        if other.get("parent_id") == m.get("parent_id") and other["id"] != m["id"]
    ]
    siblings_block = (
        "\n".join(f"- `{s['id']}` — {s['one_liner']}" for s in siblings)
        if siblings else "- (none)"
    )

    children = [
        other for other in MODULES
        if other.get("parent_id") == m["id"]
    ]
    children_block = (
        "\n".join(f"- `{c['id']}` — {c['one_liner']}" for c in children)
        if children else "- (none — this is a leaf module)"
    )

    deps = m.get("depends_on", [])
    deps_block = "\n".join(f"- `{d}`" for d in deps) if deps else "- (none)"

    dependents = [
        other for other in MODULES
        if m["id"] in other.get("depends_on", [])
    ]
    dependents_block = (
        "\n".join(f"- `{d['id']}` — {d['one_liner']}" for d in dependents)
        if dependents else "- (none)"
    )

    return (
        f"# Hierarchy — {m['display_name']}\n"
        f"\n"
        f"## Breadcrumb\n"
        f"\n"
        f"{breadcrumb}\n"
        f"\n"
        f"## Parent\n"
        f"\n"
        f"{parent_block}\n"
        f"\n"
        f"## Siblings (same parent)\n"
        f"\n"
        f"{siblings_block}\n"
        f"\n"
        f"## Children\n"
        f"\n"
        f"{children_block}\n"
        f"\n"
        f"## Depends on\n"
        f"\n"
        f"{deps_block}\n"
        f"\n"
        f"## Depended on by\n"
        f"\n"
        f"{dependents_block}\n"
    )


def render_diagram(m: dict) -> str:
    parent = MODULE_BY_ID.get(m.get("parent_id")) if m.get("parent_id") else None
    siblings = [
        other for other in MODULES
        if other.get("parent_id") == m.get("parent_id") and other["id"] != m["id"]
    ]
    children = [
        other for other in MODULES
        if other.get("parent_id") == m["id"]
    ]

    lines = [
        f"# Diagram — {m['display_name']}",
        "",
        "## Local position",
        "",
        "```",
    ]
    if parent:
        lines.append(f"          {parent['display_name']}")
        lines.append("                │")
        lines.append("     ┌──────────┼──────────┐")
        if siblings:
            sibling_labels = [s["display_name"] for s in siblings[:3]]
            lines.append("     │          │          │")
            row = "  ".join(sibling_labels + [m["display_name"] + " *"]) if sibling_labels else m["display_name"] + " *"
            lines.append("  " + row)
        else:
            lines.append(f"                │")
            lines.append(f"         {m['display_name']} *")
    else:
        lines.append(f"{m['display_name']} *")

    if children:
        lines.append("                │")
        for c in children:
            lines.append(f"                ├── {c['display_name']}")

    lines.append("```")
    lines.append("")
    lines.append("`*` = this module.")
    lines.append("")
    lines.append("## Full-system diagram")
    lines.append("")
    lines.append("See `src/forge/DIAGRAM.md` for the whole tree.")
    return "\n".join(lines) + "\n"


def render_tests(m: dict) -> str:
    test_files = m.get("test_files", [])
    test_block = (
        "\n".join(f"- `tests/{t}`" for t in test_files)
        if test_files else "- (none yet)"
    )
    return (
        f"# Tests — {m['display_name']}\n"
        f"\n"
        f"## Run tests for this module only\n"
        f"\n"
        f"```bash\n"
        f"# via forge CLI (preferred):\n"
        f"duecare test {m['path']}\n"
        f"\n"
        f"# or directly via pytest:\n"
        f"pytest {m['path']}/tests/ -v\n"
        f"```\n"
        f"\n"
        f"## Run tests for this module plus all children\n"
        f"\n"
        f"```bash\n"
        f"duecare test {m['path']} --recursive\n"
        f"```\n"
        f"\n"
        f"## Test files\n"
        f"\n"
        f"{test_block}\n"
        f"\n"
        f"## What each test validates\n"
        f"\n"
        f"(Fill in as tests are written.)\n"
        f"\n"
        f"## Integration tests that pull in this module\n"
        f"\n"
        f"Run `duecare dependents {m['path']}` to find modules that depend on\n"
        f"this one; their tests will exercise this module via their own flows.\n"
    )


def render_status(m: dict) -> str:
    return (
        f"# Status — {m['display_name']}\n"
        f"\n"
        f"## Current state\n"
        f"\n"
        f"`{m['status']}`\n"
        f"\n"
        f"## What's done\n"
        f"\n"
        f"- [x] Folder scaffolded\n"
        f"- [x] Meta files written (PURPOSE, AGENTS, INPUTS_OUTPUTS, HIERARCHY, DIAGRAM, TESTS)\n"
        f"- [ ] Source files implemented\n"
        f"- [ ] Tests written\n"
        f"- [ ] Tests passing\n"
        f"- [ ] Integration smoke-tested\n"
        f"\n"
        f"## TODO\n"
        f"\n"
        f"- [ ] Implement the source files listed in `AGENTS.md`\n"
        f"- [ ] Write at least one non-trivial test per test file\n"
        f"- [ ] Run `duecare test {m['path']}` and see it pass\n"
        f"- [ ] Update `STATUS.md` to `partial` or `complete`\n"
    )


def render_source_stub(m: dict, filename: str) -> str:
    """Render a source file stub. Only used if the file doesn't already exist."""
    if filename == "__init__.py":
        return f'"""{m["display_name"]} - {m["one_liner"]}\n\nSee `PURPOSE.md` in this folder.\n"""\n'
    base_name = filename.removesuffix(".py")
    return (
        f'"""{m["display_name"]} - {base_name}\n'
        f'\n'
        f'{m["one_liner"]}\n'
        f'\n'
        f'See `PURPOSE.md` in this folder for details, `INPUTS_OUTPUTS.md`\n'
        f'for the contract, and `TESTS.md` for how to verify this module.\n'
        f'"""\n'
        f'\n'
        f'from __future__ import annotations\n'
        f'\n'
        f'# TODO: implement.\n'
    )


def render_test_stub(m: dict, filename: str) -> str:
    return (
        f'"""Tests for {m["display_name"]}.\n'
        f'\n'
        f'See `TESTS.md` in the parent folder for how to run this suite.\n'
        f'"""\n'
        f'\n'
        f'from __future__ import annotations\n'
        f'\n'
        f'\n'
        f'def test_placeholder() -> None:\n'
        f'    """Placeholder test to keep pytest happy until real tests land."""\n'
        f'    assert True\n'
    )


def render_tests_init() -> str:
    return '"""Tests for this module. See the parent folder\'s TESTS.md."""\n'


# ===========================================================================
# Generator
# ===========================================================================

def write_if_missing(path: Path, content: str) -> bool:
    """Write content to path if the path does not exist. Returns True if written."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def overwrite(path: Path, content: str) -> bool:
    """Always write content (used for meta files we want to keep in sync)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def generate_module(m: dict, force_meta: bool = True) -> tuple[int, int]:
    """Generate meta + source + test stubs for one module.

    Returns (files_created, files_updated).

    Meta files are always overwritten (force_meta=True by default) so they
    stay in sync with the MODULES descriptor. Source files are never
    overwritten to preserve developer work.

    The legacy `src/forge/...` paths in MODULES are translated to the
    `packages/duecare-llm-<layer>/src/forge/...` layout via `normalize_path`.
    """
    created = 0
    updated = 0
    path = ROOT / normalize_path(m["path"])
    path.mkdir(parents=True, exist_ok=True)

    # Meta files (overwritten to stay in sync)
    meta = {
        "PURPOSE.md": render_purpose(m),
        "AGENTS.md": render_agents(m),
        "INPUTS_OUTPUTS.md": render_inputs_outputs(m),
        "HIERARCHY.md": render_hierarchy(m),
        "DIAGRAM.md": render_diagram(m),
        "TESTS.md": render_tests(m),
        "STATUS.md": render_status(m),
    }
    for filename, content in meta.items():
        fp = path / filename
        existed = fp.exists()
        if force_meta or not existed:
            overwrite(fp, content)
            if existed:
                updated += 1
            else:
                created += 1

    # Source file stubs (never overwritten)
    for src_name in m.get("source_files", []):
        fp = path / src_name
        if write_if_missing(fp, render_source_stub(m, src_name)):
            created += 1

    # Tests folder + stubs
    if m.get("test_files"):
        tests_dir = path / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        if write_if_missing(tests_dir / "__init__.py", render_tests_init()):
            created += 1
        for test_name in m["test_files"]:
            fp = tests_dir / test_name
            if write_if_missing(fp, render_test_stub(m, test_name)):
                created += 1

    return created, updated


def generate_all() -> int:
    total_created = 0
    total_updated = 0
    for m in MODULES:
        c, u = generate_module(m, force_meta=True)
        total_created += c
        total_updated += u
        print(
            f"{'CREATE' if c else 'UPDATE'} {normalize_path(m['path'])}  "
            f"(+{c} new, ~{u} updated)"
        )
    print()
    print(f"Modules processed: {len(MODULES)}")
    print(f"Files created:     {total_created}")
    print(f"Files updated:     {total_updated}")
    return 0


if __name__ == "__main__":
    sys.exit(generate_all())
