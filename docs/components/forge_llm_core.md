# Component 1 — `duecare-llm-core`

> **Status: shipped.** Real code, 86 tests passing, wheel built, installed
> from the wheel, demo notebook executes end-to-end. This is the foundation
> of the DueCare multi-package distribution.

---

## What it is

`duecare-llm-core` is the first and most load-bearing of the eight packages
in the DueCare agentic safety harness. It holds the **contracts, schemas,
enums, registries, provenance helpers, and observability primitives** that
every other DueCare package depends on.

Every other package in the DueCare distribution imports from here and from
nowhere else above it:

```
              duecare-llm (meta)
                     │
                     ▼
     ┌───────────────┼───────────────┐
     │               │               │
duecare-llm-workflows  │        duecare-llm-publishing
     │               │               │
     └─────┬─────────┴─────┬─────────┘
           ▼               ▼
    duecare-llm-agents ◄── duecare-llm-tasks
           │               │
           └───────┬───────┘
                   ▼
      ┌────────────┼────────────┐
      │            │            │
duecare-llm-models   │    duecare-llm-domains
      │            │            │
      └────────────┼────────────┘
                   ▼
            ★ duecare-llm-core ★
```

---

## Install

From PyPI (once published):

```bash
pip install duecare-llm-core
```

From the workspace (right now):

```bash
pip install packages/duecare-llm-core/dist/duecare_llm_core-0.1.0-py3-none-any.whl
```

Or in editable mode for development:

```bash
pip install -e packages/duecare-llm-core
```

Via `uv` from the workspace root:

```bash
uv sync   # installs every package in the workspace in editable mode
```

---

## What's inside

### Python imports provided

```python
# Protocols (runtime-checkable)
from duecare.core import Agent, Coordinator, DomainPack, Model, Task

# Enums
from duecare.core import AgentRole, Capability, Grade, Severity, TaskStatus

# Pydantic schemas
from duecare.core import (
    AgentContext, AgentOutput,
    ChatMessage, ToolSpec, ToolCall,
    DomainCard, Issue, ResponseExample,
    Embedding, GenerationResult, ModelHealth,
    ItemResult, TaskConfig, TaskResult,
    Provenance, WorkflowRun,
)

# Registry
from duecare.core import Registry

# Provenance helpers
from duecare.core import (
    compute_checksum, generate_run_id, get_git_sha,
    get_short_sha, hash_config, simhash,
)

# Observability (separate sub-namespace)
from duecare.observability import configure_logging, get_logger
from duecare.observability import MetricsSink, AuditTrail
```

### On-disk layout (folder-per-module)

```
packages/duecare-llm-core/
├── pyproject.toml                  # hatchling backend, wheel targets src/forge
├── README.md                       # package readme
├── tests/                          # package-level cross-module smoke test
│   ├── __init__.py
│   └── test_core_package_smoke.py
│
└── src/forge/                      # PEP 420 namespace (no __init__.py here)
    │
    ├── core/                       ← Layer "core"
    │   ├── PURPOSE/AGENTS/INPUTS_OUTPUTS/HIERARCHY/DIAGRAM/TESTS/STATUS.md
    │   ├── __init__.py             # re-exports 30+ public symbols
    │   │
    │   ├── contracts/              ← Component 1.1: Protocols
    │   │   ├── 7 meta files
    │   │   ├── __init__.py
    │   │   ├── model.py
    │   │   ├── domain_pack.py
    │   │   ├── task.py
    │   │   ├── agent.py
    │   │   ├── coordinator.py
    │   │   └── tests/test_protocols_runtime_checkable.py   ← 7 tests
    │   │
    │   ├── enums/                  ← Component 1.2: Enums
    │   │   ├── 7 meta files
    │   │   ├── __init__.py
    │   │   ├── capability.py       # Capability (8 values)
    │   │   ├── agent_role.py       # AgentRole (12 values)
    │   │   ├── task_status.py      # TaskStatus (6 values)
    │   │   ├── grade.py            # Grade + ordinal + from_score
    │   │   ├── severity.py         # Severity (4 values)
    │   │   └── tests/test_enums.py                          ← 15 tests
    │   │
    │   ├── schemas/                ← Component 1.3: Pydantic models
    │   │   ├── 7 meta files
    │   │   ├── __init__.py
    │   │   ├── chat.py             # ChatMessage, ToolSpec, ToolCall
    │   │   ├── generation.py       # GenerationResult, Embedding, ModelHealth
    │   │   ├── task.py             # TaskConfig, TaskResult, ItemResult
    │   │   ├── agent.py            # AgentContext, AgentOutput
    │   │   ├── workflow.py         # WorkflowRun
    │   │   ├── domain.py           # DomainCard, Issue, ResponseExample
    │   │   ├── provenance.py       # Provenance
    │   │   └── tests/test_schemas_roundtrip.py              ← 20 tests
    │   │
    │   ├── registry/               ← Component 1.4: Registry[T]
    │   │   ├── 7 meta files
    │   │   ├── __init__.py
    │   │   ├── registry.py
    │   │   └── tests/test_registry.py                       ← 8 tests
    │   │
    │   └── provenance/             ← Component 1.5: reproducibility
    │       ├── 7 meta files
    │       ├── __init__.py
    │       ├── git.py              # get_git_sha, get_short_sha
    │       ├── run_id.py           # generate_run_id
    │       ├── hashing.py          # hash_config, compute_checksum, simhash
    │       └── tests/test_provenance.py                     ← 16 tests
    │
    └── observability/              ← Layer "observability" (folded into core)
        ├── 7 meta files
        ├── __init__.py
        │
        ├── logging/                ← Component 1.6: logging
        │   ├── 7 meta files
        │   ├── __init__.py
        │   ├── logging.py          # configure_logging, get_logger
        │   └── tests/test_logging.py                        ← 5 tests
        │
        ├── metrics/                ← Component 1.7: metrics sink
        │   ├── 7 meta files
        │   ├── __init__.py
        │   ├── metrics.py          # MetricsSink (JSONL, thread-safe)
        │   └── tests/test_metrics.py                        ← 7 tests
        │
        └── audit/                  ← Component 1.8: audit trail
            ├── 7 meta files
            ├── __init__.py
            ├── audit.py            # AuditTrail (SQLite, hashes not plaintext)
            └── tests/test_audit.py                          ← 5 tests
```

**Every folder has 7 meta files** (PURPOSE.md, AGENTS.md, INPUTS_OUTPUTS.md,
HIERARCHY.md, DIAGRAM.md, TESTS.md, STATUS.md). **Every folder has its
own `tests/` subfolder**. Regenerate all meta files with
`python scripts/generate_forge.py`.

---

## Quick start

### 1. Install

```bash
pip install packages/duecare-llm-core/dist/duecare_llm_core-0.1.0-py3-none-any.whl
```

### 2. Use the enums

```python
from duecare.core import Capability, Grade

assert Capability.TEXT == "text"
assert Grade.from_score(0.85) == Grade.GOOD
assert Grade.BEST.ordinal == 4
```

### 3. Build a Pydantic TaskResult

```python
from duecare.core import (
    TaskResult, TaskStatus, Provenance, Grade, ItemResult,
    generate_run_id, hash_config, compute_checksum,
)
from datetime import datetime

run_id = generate_run_id("evaluate_only")
result = TaskResult(
    task_id="guardrails",
    model_id="gemma-4-e4b",
    domain_id="trafficking",
    status=TaskStatus.COMPLETED,
    started_at=datetime.now(),
    metrics={"grade_exact_match": 0.68, "grade_within_1": 0.92},
    per_item=[
        ItemResult(item_id="p001", scores={"score": 0.85}, grade=Grade.GOOD),
    ],
    provenance=Provenance(
        run_id=run_id,
        git_sha="abc123",
        workflow_id="evaluate_only",
        created_at=datetime.now(),
        checksum=compute_checksum(run_id),
    ),
)

print(result.summary())
# guardrails [completed] grade_exact_match=0.680, grade_within_1=0.920
```

### 4. Register a plugin

```python
from duecare.core import Registry

model_registry: Registry = Registry(kind="model_adapter")

@model_registry.register("transformers", provider="huggingface")
class TransformersModel:
    ...

print(model_registry.all_ids())  # ['transformers']
```

### 5. Satisfy a protocol (structural typing, no inheritance)

```python
from duecare.core import Model, Capability, GenerationResult, Embedding, ModelHealth

class MyModel:
    id = "my:model"
    display_name = "My Model"
    provider = "custom"
    capabilities = {Capability.TEXT}
    context_length = 4096

    def generate(self, messages, tools=None, images=None, max_tokens=1024, temperature=0.0, **kwargs):
        return GenerationResult(text="...", model_id=self.id)

    def embed(self, texts):
        return [Embedding(text=t, vector=[0.0], dimension=1, model_id=self.id) for t in texts]

    def healthcheck(self):
        return ModelHealth(model_id=self.id, healthy=True)

assert isinstance(MyModel(), Model)   # True, via runtime_checkable Protocol
```

### 6. Record observability

```python
from duecare.observability import configure_logging, get_logger, MetricsSink, AuditTrail
from pathlib import Path

configure_logging(level="INFO")
log = get_logger("my.app")
log.info("Starting...")

metrics = MetricsSink(Path("metrics.jsonl"))
metrics.write("run_001", "grade_exact_match", 0.68,
              agent_id="judge", model_id="gemma-4-e4b",
              task_id="guardrails", domain_id="trafficking")

audit = AuditTrail(Path("audit.sqlite"))
audit.record_run_start(
    run_id="run_001",
    workflow_id="evaluate_only",
    git_sha="abc",
    config_hash="def",
    target_model_id="gemma-4-e4b",
    domain_id="trafficking",
)
audit.record_run_end(
    run_id="run_001",
    status="completed",
    total_cost_usd=4.20,
    final_metrics={"grade_exact_match": 0.68},
)
```

---

## Tests

**86 tests, all passing.** One test file per component, plus a
package-level cross-module smoke test.

| Test file | Component | Tests |
|---|---|---|
| `src/forge/core/enums/tests/test_enums.py` | Enums | 15 |
| `src/forge/core/schemas/tests/test_schemas_roundtrip.py` | Schemas | 20 |
| `src/forge/core/contracts/tests/test_protocols_runtime_checkable.py` | Protocols | 7 |
| `src/forge/core/registry/tests/test_registry.py` | Registry | 8 |
| `src/forge/core/provenance/tests/test_provenance.py` | Provenance + SimHash | 16 |
| `src/forge/observability/logging/tests/test_logging.py` | Logging | 5 |
| `src/forge/observability/metrics/tests/test_metrics.py` | Metrics sink | 7 |
| `src/forge/observability/audit/tests/test_audit.py` | Audit trail | 5 |
| `tests/test_core_package_smoke.py` | Package-level cross-module | 4 |
| **Total** | | **86** |

### Run them

```bash
# Whole package
python -m pytest packages/duecare-llm-core -v

# One component
python -m pytest packages/duecare-llm-core/src/forge/core/enums -v

# Package-level smoke only
python -m pytest packages/duecare-llm-core/tests -v
```

Latest run (from the `duecare-llm-core-0.1.0` wheel build):

```
================= 86 passed, 1 warning in 0.79s =================
```

---

## Built artifacts

```
packages/duecare-llm-core/dist/
├── duecare_llm_core-0.1.0-py3-none-any.whl   ← 75 KB
└── duecare_llm_core-0.1.0.tar.gz              ← 30 KB
```

The wheel contains **123 files** including:
- all `.py` source files
- all meta files (PURPOSE.md / AGENTS.md / etc. for every module folder)
- all `tests/` subfolders

Build it yourself:

```bash
cd packages/duecare-llm-core && python -m build
```

---

## Demo notebook

A runnable demonstration of every public surface of `duecare-llm-core`
lives at [`notebooks/duecare_llm_core_demo.ipynb`](../../notebooks/duecare_llm_core_demo.ipynb).

- **22 cells** (12 code, 10 markdown)
- Covers enums, schemas, protocols, registry, provenance, and all three
  observability helpers (logging, metrics, audit)
- Closes with an **end-to-end mini flow** that builds a reproducible run
  record exactly the way the DueCare workflow runner will at Phase 1
- **All 12 code cells verified to execute successfully** against the
  installed wheel

Open it in Jupyter, JupyterLab, Colab, Kaggle Notebooks, or VS Code:

```bash
jupyter notebook notebooks/duecare_llm_core_demo.ipynb
```

On Kaggle, the first cell's `!pip install` is commented out until the
package is published to PyPI. After publication, un-comment it.

---

## Design decisions

### Protocols, not ABCs

Every cross-layer contract is a `typing.Protocol` (with
`@runtime_checkable`), not an abstract base class. This lets adapters
wrap pre-existing frameworks (Transformers, llama.cpp, OpenAI client,
Anthropic client) without forcing them into an inheritance hierarchy.
Structural typing for the win.

### Pydantic v2, not v1 or dataclasses

Every data model is a Pydantic v2 `BaseModel`. Reasons:
- JSON round-trips via `.model_dump_json()` / `.model_validate_json()`
- Strict validation at every layer boundary — bad data raises loudly
- The existing author framework is Pydantic v2, so integration is clean
- Future `duecare-llm-publishing` will serialize everything through these
  models to HF Hub, Kaggle Datasets, and report markdown

### Observability folded into `duecare-llm-core`

Logging, metrics, and audit are small and every other layer depends on
them. Rather than a separate `duecare-llm-observability` package, they
live inside `duecare-llm-core` under the `duecare.observability` sub-
namespace. One fewer package to publish, no loss in modularity.

### No `__init__.py` at the `forge/` namespace level

`duecare` is a PEP 420 implicit namespace package. The `forge/` directory
inside each package's `src/` has NO `__init__.py` on purpose — otherwise
`duecare` becomes a regular package and only the first match wins. With
no `__init__.py`, Python merges every `forge/` directory on `sys.path`
into a single namespace, so all 8 packages contribute to `forge.*`
transparently.

This is verified by the smoke test:

```python
import duecare
print(forge.__path__)  # 8 portions, one per package
```

### Auto-generated meta files

The 7 meta files per module (PURPOSE.md, AGENTS.md, etc.) are generated
from `scripts/generate_forge.py`. **Do not hand-edit them** — they get
wiped on the next generator run. To change a module's purpose / inputs /
outputs / dependencies, edit the `MODULES` descriptor in the generator
and re-run.

The generator auto-computes every cross-reference (siblings, children,
dependents), so one change to a module descriptor updates every
dependent module's `HIERARCHY.md` automatically.

---

## What this unblocks

`duecare-llm-core` is the only package with zero upstream dependencies
inside the DueCare distribution. Every other package needs it:

1. **`duecare-llm-models`** — every model adapter implements
   `duecare.core.contracts.Model`
2. **`duecare-llm-domains`** — `FileDomainPack` implements
   `duecare.core.contracts.DomainPack`
3. **`duecare-llm-tasks`** — every task implements
   `duecare.core.contracts.Task` and produces `TaskResult`
4. **`duecare-llm-agents`** — every agent implements
   `duecare.core.contracts.Agent` and reads/writes `AgentContext`
5. **`duecare-llm-workflows`** — workflow runs produce `WorkflowRun`
6. **`duecare-llm-publishing`** — publishes results using `Provenance`
   for reproducibility
7. **`duecare-llm`** — meta package, pulls in all of the above

With `duecare-llm-core` shipped, the next 7 packages become pure
"implement the protocol" exercises.

---

## Status

- [x] Code — all 30+ public symbols implemented
- [x] Tests — 86 tests, all passing
- [x] Wheel built — `duecare_llm_core-0.1.0-py3-none-any.whl` (75 KB)
- [x] Sdist built — `duecare_llm_core-0.1.0.tar.gz` (30 KB)
- [x] Installable — `pip install` the wheel works with zero PYTHONPATH
- [x] Demo notebook — 22 cells, all 12 code cells execute successfully
- [x] Component doc — this file
- [ ] Published to PyPI (deferred until the other 7 packages are ready
      to release together as v0.1.0)

**Next component:** `duecare-llm-models` — 8 model adapters, same pattern.

---

## License

MIT. See `../../LICENSE`.

## Citation

```
Amarel, T. (2026). duecare-llm-core v0.1.0: Foundation package for the DueCare
agentic LLM safety harness. https://github.com/TaylorAmarelTech/gemma4_comp
```
