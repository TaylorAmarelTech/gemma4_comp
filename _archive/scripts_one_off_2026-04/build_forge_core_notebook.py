#!/usr/bin/env python3
"""build_forge_core_notebook.py - Emit a Jupyter .ipynb for duecare-llm-core.

Creates `notebooks/duecare_llm_core_demo.ipynb` - a demonstration notebook
that can be opened in Jupyter or pasted into a Kaggle Notebook. The
notebook imports from duecare.core and exercises every major surface of
the package: enums, schemas, contracts, registry, provenance, and
observability.

Writes the notebook as a plain JSON file (nbformat 4, minor 5). No
dependency on nbformat.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "notebooks" / "duecare_llm_core_demo.ipynb"


def md_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


CELLS = [
    md_cell(
        "# Duecare LLM Core — Component 1 Demo\n"
        "\n"
        "**First of 8 packages** in the [Duecare](../docs/the_forge.md) agentic\n"
        "LLM safety harness. `duecare-llm-core` is the foundation: every other\n"
        "Duecare package (models, domains, tasks, agents, workflows, publishing)\n"
        "imports from here.\n"
        "\n"
        "This notebook exercises every public surface of the package:\n"
        "\n"
        "- **Enums**: `Capability`, `AgentRole`, `TaskStatus`, `Grade`, `Severity`\n"
        "- **Schemas**: Pydantic v2 models for chat, generation, tasks, agents,\n"
        "  workflows, domain cards, and provenance\n"
        "- **Protocols**: runtime-checkable `Model`, `DomainPack`, `Task`,\n"
        "  `Agent`, `Coordinator`\n"
        "- **Registry**: generic `Registry[T]` used by models / domains / agents / tasks\n"
        "- **Provenance**: `generate_run_id`, `get_git_sha`, `hash_config`,\n"
        "  `compute_checksum`, `simhash`\n"
        "- **Observability**: `configure_logging`, `MetricsSink`, `AuditTrail`\n"
        "\n"
        "## Run it anywhere\n"
        "\n"
        "This notebook installs `duecare-llm-core` from the local workspace wheel.\n"
        "When the package is published to PyPI, change the install cell to\n"
        "`!pip install duecare-llm-core`.\n"
    ),

    md_cell("## Install"),

    code_cell(
        "# On Kaggle / Colab / fresh env, uncomment the PyPI install:\n"
        "# !pip install duecare-llm-core\n"
        "\n"
        "# On the local workspace, install the built wheel:\n"
        "# !pip install --force-reinstall ../packages/duecare-llm-core/dist/duecare_llm_core-0.1.0-py3-none-any.whl\n"
        "\n"
        "import duecare.core\n"
        "import duecare.observability\n"
        "print(f'duecare.core version: {duecare.core.__version__}')\n"
    ),

    md_cell("## 1. Enums\n\n"
            "Canonical identifiers used throughout Duecare. StrEnum-based, so "
            "they compare equal to their string values and are JSON-safe."),

    code_cell(
        "from duecare.core import Capability, AgentRole, TaskStatus, Grade, Severity\n"
        "\n"
        "print(f'Capabilities ({len(list(Capability))}):')\n"
        "for c in Capability:\n"
        "    print(f'  - {c.value}')\n"
        "\n"
        "print(f'\\nAgent roles ({len(list(AgentRole))}):')\n"
        "for r in AgentRole:\n"
        "    print(f'  - {r.value}')\n"
        "\n"
        "print(f'\\nTaskStatus: {[s.value for s in TaskStatus]}')\n"
        "print(f'Severity:   {[s.value for s in Severity]}')\n"
    ),

    code_cell(
        "# Grade has an ordinal property and a from_score() helper\n"
        "print(f'Grade.BEST.ordinal = {Grade.BEST.ordinal}')\n"
        "print(f'Grade.WORST.ordinal = {Grade.WORST.ordinal}')\n"
        "\n"
        "for score in [0.05, 0.25, 0.55, 0.80, 0.95]:\n"
        "    grade = Grade.from_score(score)\n"
        "    print(f'  score={score:.2f} -> grade={grade.value} (ordinal={grade.ordinal})')\n"
    ),

    md_cell("## 2. Pydantic schemas\n\n"
            "Every cross-layer data flow uses these Pydantic v2 models. "
            "They round-trip via `.model_dump()` / `.model_validate()` for "
            "JSON-safe persistence."),

    code_cell(
        "from duecare.core import ChatMessage, ToolSpec, GenerationResult\n"
        "\n"
        "# Build a chat conversation\n"
        "messages = [\n"
        "    ChatMessage(role='system', content='You are a safety judge.'),\n"
        "    ChatMessage(role='user', content='Is this contract predatory?'),\n"
        "]\n"
        "\n"
        "# Declare a tool Gemma can call via native function calling\n"
        "anonymize_tool = ToolSpec(\n"
        "    name='anonymize',\n"
        "    description='Strip PII from a text span',\n"
        "    parameters={\n"
        "        'type': 'object',\n"
        "        'properties': {'text': {'type': 'string'}},\n"
        "        'required': ['text'],\n"
        "    },\n"
        ")\n"
        "\n"
        "# Render the tool into provider-specific formats\n"
        "print('OpenAI format:')\n"
        "print(anonymize_tool.to_openai())\n"
        "print('\\nAnthropic format:')\n"
        "print(anonymize_tool.to_anthropic())\n"
    ),

    code_cell(
        "from duecare.core import (\n"
        "    TaskResult, TaskConfig, TaskStatus, Provenance,\n"
        "    ItemResult, Grade, generate_run_id, compute_checksum\n"
        ")\n"
        "from datetime import datetime\n"
        "\n"
        "# Build a realistic TaskResult\n"
        "run_id = generate_run_id('evaluate_only')\n"
        "provenance = Provenance(\n"
        "    run_id=run_id,\n"
        "    git_sha='abc123',\n"
        "    workflow_id='evaluate_only',\n"
        "    created_at=datetime.now(),\n"
        "    checksum=compute_checksum(run_id),\n"
        ")\n"
        "\n"
        "result = TaskResult(\n"
        "    task_id='guardrails',\n"
        "    model_id='gemma-4-e4b',\n"
        "    domain_id='trafficking',\n"
        "    status=TaskStatus.COMPLETED,\n"
        "    started_at=datetime.now(),\n"
        "    metrics={\n"
        "        'grade_exact_match': 0.68,\n"
        "        'grade_within_1': 0.92,\n"
        "        'ilo_indicator_recall': 0.81,\n"
        "    },\n"
        "    per_item=[\n"
        "        ItemResult(item_id='p001', scores={'score': 0.85}, grade=Grade.GOOD),\n"
        "        ItemResult(item_id='p002', scores={'score': 0.22}, grade=Grade.BAD),\n"
        "    ],\n"
        "    provenance=provenance,\n"
        ")\n"
        "\n"
        "print(result.summary())\n"
        "print(f'\\nPer-item count: {len(result.per_item)}')\n"
        "print(f'Metrics: {result.metrics}')\n"
    ),

    md_cell("## 3. Protocols (runtime-checkable)\n\n"
            "Any class that structurally implements the protocol is accepted — "
            "no inheritance required. This is the integration boundary that "
            "lets us drop in new backends (a new model adapter, a new domain "
            "pack) without changing downstream code."),

    code_cell(
        "from duecare.core import Model, Capability, Embedding, ModelHealth, GenerationResult\n"
        "\n"
        "# Minimal class that structurally satisfies the Model protocol\n"
        "class MyStubModel:\n"
        "    id = 'stub:demo'\n"
        "    display_name = 'Demo Stub Model'\n"
        "    provider = 'stub'\n"
        "    capabilities = {Capability.TEXT}\n"
        "    context_length = 4096\n"
        "\n"
        "    def generate(self, messages, tools=None, images=None, max_tokens=1024, temperature=0.0, **kwargs):\n"
        "        return GenerationResult(text='stubbed', model_id=self.id)\n"
        "\n"
        "    def embed(self, texts):\n"
        "        return [Embedding(text=t, vector=[0.0], dimension=1, model_id=self.id) for t in texts]\n"
        "\n"
        "    def healthcheck(self):\n"
        "        return ModelHealth(model_id=self.id, healthy=True)\n"
        "\n"
        "m = MyStubModel()\n"
        "print(f'isinstance(m, Model) = {isinstance(m, Model)}')\n"
        "print(f'Result: {m.generate([])}')\n"
    ),

    md_cell("## 4. Registry\n\n"
            "Generic plugin registry. Every plugin kind (models, domains, "
            "agents, tasks) has its own Registry instance but shares this code."),

    code_cell(
        "from duecare.core import Registry\n"
        "\n"
        "model_registry: Registry = Registry(kind='model_adapter')\n"
        "\n"
        "@model_registry.register('transformers', provider='huggingface')\n"
        "class TransformersModel:\n"
        "    pass\n"
        "\n"
        "@model_registry.register('llama_cpp', provider='ggerganov')\n"
        "class LlamaCppModel:\n"
        "    pass\n"
        "\n"
        "@model_registry.register('openai_compatible', provider='openai')\n"
        "class OpenAICompatibleModel:\n"
        "    pass\n"
        "\n"
        "print(f'Registered: {model_registry.all_ids()}')\n"
        "print(f'Metadata for transformers: {model_registry.metadata(\"transformers\")}')\n"
        "print(f'Lookup llama_cpp: {model_registry.get(\"llama_cpp\").__name__}')\n"
        "print(f'Repr: {model_registry}')\n"
    ),

    md_cell("## 5. Provenance + hashing\n\n"
            "Reproducibility helpers. Every Duecare run stamps its outputs with "
            "`(run_id, git_sha, config_hash)` so results are reproducible to "
            "the byte."),

    code_cell(
        "from duecare.core import (\n"
        "    generate_run_id, get_git_sha, hash_config, compute_checksum, simhash\n"
        ")\n"
        "\n"
        "print(f'run_id:   {generate_run_id(\"evaluate_and_finetune\")}')\n"
        "print(f'git_sha:  {get_git_sha()[:12]}')\n"
        "print(f'config hash (order-invariant):')\n"
        "print(f'  hash_config({{\"a\":1,\"b\":2}}) = {hash_config({\"a\":1,\"b\":2})[:16]}...')\n"
        "print(f'  hash_config({{\"b\":2,\"a\":1}}) = {hash_config({\"b\":2,\"a\":1})[:16]}...')\n"
        "print(f'  (identical: {hash_config({\"a\":1,\"b\":2}) == hash_config({\"b\":2,\"a\":1})})')\n"
        "\n"
        "print(f'\\nSimHash — near-duplicates collide more than unrelated text:')\n"
        "a = simhash('the quick brown fox jumps over the lazy dog')\n"
        "b = simhash('the quick brown fox leaps over the lazy dog')\n"
        "c = simhash('completely unrelated financial obfuscation scheme')\n"
        "\n"
        "def hamming(x, y):\n"
        "    return bin(x ^ y).count('1')\n"
        "\n"
        "print(f'  hamming(near_dup_1, near_dup_2) = {hamming(a, b)}')\n"
        "print(f'  hamming(near_dup_1, unrelated)   = {hamming(a, c)}')\n"
    ),

    md_cell("## 6. Observability\n\n"
            "Logging (never PII), metrics sink (append-only JSONL), and audit "
            "trail (SQLite, stores hashes not plaintext)."),

    code_cell(
        "from duecare.observability import configure_logging, get_logger, MetricsSink, AuditTrail\n"
        "from pathlib import Path\n"
        "import tempfile, json\n"
        "\n"
        "configure_logging(level='INFO')\n"
        "log = get_logger('forge.demo')\n"
        "log.info('Demo notebook started')\n"
        "log.warning('This is a warning line')\n"
    ),

    code_cell(
        "# MetricsSink - append-only JSONL\n"
        "tmp = Path(tempfile.mkdtemp())\n"
        "sink = MetricsSink(tmp / 'metrics.jsonl')\n"
        "\n"
        "# Record a handful of metrics as if the Judge agent produced them\n"
        "sink.write('run_001', 'grade_exact_match', 0.68, agent_id='judge', model_id='gemma-4-e4b', domain_id='trafficking', task_id='guardrails')\n"
        "sink.write('run_001', 'grade_within_1', 0.92, agent_id='judge', model_id='gemma-4-e4b', domain_id='trafficking', task_id='guardrails')\n"
        "sink.write('run_001', 'ilo_indicator_recall', 0.81, agent_id='judge', model_id='gemma-4-e4b', domain_id='trafficking', task_id='guardrails')\n"
        "\n"
        "# Read them back\n"
        "rows = [json.loads(line) for line in (tmp / 'metrics.jsonl').read_text().splitlines()]\n"
        "print(f'Wrote {len(rows)} metric rows to {sink.path}')\n"
        "for row in rows:\n"
        "    print(f'  {row[\"metric\"]:<25} = {row[\"value\"]:.3f}  (model={row[\"model_id\"]}, task={row[\"task_id\"]})')\n"
    ),

    code_cell(
        "# AuditTrail - SQLite, stores HASHES not plaintext\n"
        "from duecare.core import compute_checksum\n"
        "\n"
        "audit = AuditTrail(tmp / 'audit.sqlite')\n"
        "\n"
        "# Simulate anonymization decisions: the original text is HASHED, never stored\n"
        "import hashlib\n"
        "for i, (category, original) in enumerate([\n"
        "    ('phone', '+966-555-0101'),\n"
        "    ('given_name', 'Maria Santos'),\n"
        "    ('passport', 'P1234567'),\n"
        "]):\n"
        "    audit.record_anonymization(\n"
        "        audit_id=f'a{i}',\n"
        "        item_id='probe_001',\n"
        "        detector_name='regex',\n"
        "        detector_version='0.1',\n"
        "        span_start=0,\n"
        "        span_end=len(original),\n"
        "        category=category,\n"
        "        original_hash=compute_checksum(original),\n"
        "        strategy='redact',\n"
        "        replacement=f'[{category.upper()}]',\n"
        "    )\n"
        "\n"
        "# Record a workflow run lifecycle\n"
        "audit.record_run_start(\n"
        "    run_id='run_001',\n"
        "    workflow_id='evaluate_only',\n"
        "    git_sha='abc123',\n"
        "    config_hash='def456',\n"
        "    target_model_id='gemma-4-e4b',\n"
        "    domain_id='trafficking',\n"
        ")\n"
        "audit.record_run_end(\n"
        "    run_id='run_001',\n"
        "    status='completed',\n"
        "    total_cost_usd=4.20,\n"
        "    final_metrics={'grade_exact_match': 0.68},\n"
        ")\n"
        "\n"
        "import sqlite3\n"
        "with sqlite3.connect(audit.db_path) as conn:\n"
        "    anon_count = conn.execute('SELECT COUNT(*) FROM anon_audit').fetchone()[0]\n"
        "    print(f'Audit trail has {anon_count} anonymization records')\n"
        "    run_status = conn.execute('SELECT status, total_cost_usd, final_metrics FROM run_audit WHERE run_id = ?', ('run_001',)).fetchone()\n"
        "    print(f'Run 001 status: {run_status}')\n"
    ),

    md_cell("## 7. End-to-end: build a reproducible run record\n\n"
            "Exercises several modules at once: run_id generation, config "
            "hashing, TaskResult construction, metric sinking, audit trailing."),

    code_cell(
        "from duecare.core import (\n"
        "    TaskResult, TaskStatus, Provenance, Grade, ItemResult,\n"
        "    generate_run_id, hash_config, compute_checksum\n"
        ")\n"
        "from duecare.observability import MetricsSink, AuditTrail\n"
        "from datetime import datetime\n"
        "\n"
        "# 1. Boot the run\n"
        "run_id = generate_run_id('rapid_probe')\n"
        "git_sha = 'abc123'\n"
        "config = {'model': 'gemma-4-e4b', 'domain': 'trafficking', 'sample_size': 100}\n"
        "config_hash = hash_config(config)\n"
        "\n"
        "print(f'run_id:       {run_id}')\n"
        "print(f'config_hash:  {config_hash[:16]}...')\n"
        "\n"
        "# 2. Start audit\n"
        "audit.record_run_start(\n"
        "    run_id=run_id,\n"
        "    workflow_id='rapid_probe',\n"
        "    git_sha=git_sha,\n"
        "    config_hash=config_hash,\n"
        "    target_model_id='gemma-4-e4b',\n"
        "    domain_id='trafficking',\n"
        ")\n"
        "\n"
        "# 3. 'Run' the task (simulated metrics)\n"
        "provenance = Provenance(\n"
        "    run_id=run_id,\n"
        "    git_sha=git_sha,\n"
        "    workflow_id='rapid_probe',\n"
        "    target_model_id='gemma-4-e4b',\n"
        "    domain_id='trafficking',\n"
        "    created_at=datetime.now(),\n"
        "    checksum=compute_checksum(f'{run_id}:guardrails'),\n"
        ")\n"
        "\n"
        "metrics = {\n"
        "    'grade_exact_match': 0.68,\n"
        "    'grade_within_1': 0.92,\n"
        "    'ilo_indicator_recall': 0.81,\n"
        "    'latency_p50_ms': 287,\n"
        "}\n"
        "\n"
        "result = TaskResult(\n"
        "    task_id='guardrails',\n"
        "    model_id='gemma-4-e4b',\n"
        "    domain_id='trafficking',\n"
        "    status=TaskStatus.COMPLETED,\n"
        "    started_at=datetime.now(),\n"
        "    ended_at=datetime.now(),\n"
        "    metrics=metrics,\n"
        "    provenance=provenance,\n"
        ")\n"
        "\n"
        "# 4. Sink metrics\n"
        "for metric, value in metrics.items():\n"
        "    sink.write(run_id, metric, value, task_id='guardrails', model_id='gemma-4-e4b', domain_id='trafficking')\n"
        "\n"
        "# 5. Close out audit\n"
        "audit.record_run_end(run_id=run_id, status='completed', final_metrics=metrics)\n"
        "\n"
        "print(f'\\n{result.summary()}')\n"
        "print(f'\\nFull result is reproducible from (run_id={run_id}, git_sha={git_sha}, config_hash={config_hash[:16]}...)')\n"
    ),

    md_cell("## What this first component unlocks\n\n"
            "Every other Duecare package imports from `duecare.core`:\n\n"
            "- `duecare-llm-models` — model adapters (8 backends)\n"
            "- `duecare-llm-domains` — pluggable safety domain packs\n"
            "- `duecare-llm-tasks` — 9 capability tests\n"
            "- `duecare-llm-agents` — 12-agent autonomous swarm\n"
            "- `duecare-llm-workflows` — DAG orchestration\n"
            "- `duecare-llm-publishing` — HF Hub + Kaggle publication\n"
            "- `duecare-llm` — the meta package + CLI\n\n"
            "All 8 packages share the `duecare` Python namespace via PEP 420, "
            "so `from duecare.core import Model` works whether you installed "
            "one package or all of them.\n\n"
            "## Next\n\n"
            "Open [the Duecare north-star doc](../docs/the_forge.md) to see the\n"
            "full 12-agent swarm, 3 domain packs, and the 4-phase execution\n"
            "plan (Exploration → Comparison → Enhancement → Implementation).\n"),
]


NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.11",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


def main() -> int:
    NB_PATH.parent.mkdir(parents=True, exist_ok=True)
    NB_PATH.write_text(json.dumps(NOTEBOOK, indent=1), encoding="utf-8")
    print(f"Wrote {NB_PATH}")
    print(f"  cells: {len(CELLS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
