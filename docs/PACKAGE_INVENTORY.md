# DueCare package inventory

Generated/verified during the 2026-05-10 readiness cleanup pass. The workspace currently contains **17** publishable Python packages under `packages/`, all sharing the `duecare` namespace where applicable.

## Inventory

| Package | Version | Wheel package root | Console scripts | Extras | Purpose |
|---|---:|---|---|---|---|
| `duecare-llm` | 0.1.0 | `src/duecare` | `duecare`, `forge` | `all`, `dev` | Meta package that pulls in DueCare components and exposes CLI entry points. |
| `duecare-llm-agents` | 0.1.0 | `src/duecare` | none | `trainer` | Agent swarm layer. |
| `duecare-llm-benchmark` | 0.1.0 | `src/duecare` | none | none | Bundled benchmark test sets, scoring, and aggregation. |
| `duecare-llm-chat` | 0.17.0 | `src/duecare` | none | none | Gemma 4 workbench, harness UI, sample bundles, knowledge-file I/O, and the reusable portability contract consumed by the Kaggle notebooks. |
| `duecare-llm-cli` | 0.1.0 | `src/duecare` | `duecare` | none | Current reliable CLI package for `duecare init`, `duecare demo-stage`, and `duecare serve`. |
| `duecare-llm-core` | 0.1.0 | `src/duecare` | none | none | Core contracts, schemas, enums, registries, provenance, and observability. |
| `duecare-llm-domains` | 0.1.0 | `src/duecare` | none | none | Domain pack system with lightweight bundled data; the full 74,567-prompt trafficking corpus lives in repo config/Kaggle assets. |
| `duecare-llm-engine` | 0.1.0 | `src/duecare` | none | `otel` | Pipeline engine wrapper. |
| `duecare-llm-evidence-db` | 0.1.0 | `src/duecare` | none | `postgres`, `all` | Evidence database backends. |
| `duecare-llm-models` | 0.1.0 | `src/duecare` | none | `transformers`, `unsloth`, `llama-cpp`, `ollama`, `openai`, `anthropic`, `google`, `hf-endpoint`, `all` | Model adapters. |
| `duecare-llm-nl2sql` | 0.1.0 | `src/duecare` | none | none | Natural-language-to-SQL translator. |
| `duecare-llm-publishing` | 0.1.0 | `src/duecare` | none | `hf-hub`, `kaggle`, `all` | Publication helpers for HF Hub, Kaggle, reports, and model cards. |
| `duecare-llm-research-tools` | 0.1.0 | `src/duecare` | none | `http` | External research tool wrappers with PII filtering. |
| `duecare-llm-server` | 0.1.0 | `src/duecare` | none | `observability`, `otel` | FastAPI server and demo UI surface. |
| `duecare-llm-tasks` | 0.1.0 | `src/duecare` | none | `anonymization`, `embedding` | Capability tests. |
| `duecare-llm-training` | 0.1.0 | `src/duecare` | none | `clustering`, `unsloth` | Synthetic labeling, active learning, dataset assembly, and fine-tune kickoff. |
| `duecare-llm-workflows` | 0.1.0 | `src/duecare` | none | none | Workflow DAG orchestration. |

## Current install truth

For the local CLI/server workflow, the most reliable current path is:

```powershell
pip install duecare-llm-cli
duecare init
duecare demo-stage
duecare serve --port 8080
```

The meta-package `duecare-llm` remains the desired one-command distribution story. It was smoke-tested in an isolated `virtualenv` from the locally built wheels for `duecare --help`, `duecare domains list`, and an end-to-end `duecare run rapid_probe --target-model local_smoke --domain trafficking` workflow against a local OpenAI-compatible fake backend. Real Gemma/Ollama/API runs still require the corresponding target-model backend and credentials/model files.

The `duecare-llm-cli` path was smoke-tested in an isolated `virtualenv` from the locally built wheels: install, `duecare --help`, `duecare init`, and `duecare demo-stage` passed.

## Readiness notes

- `scripts/build_all_wheels.py` now includes all 17 package directories in its default build order.
- `duecare-llm-chat` intentionally remains on an independent harness cadence; the current notebook portability contract is `0.17.0`, exposed through `duecare.chat.portability` and `GET /api/portability`, so synchronized `0.1.0` infrastructure package tags are not confused with the chat wheel version.
- Local wheel build passed for all 17 packages with `scripts/build_all_wheels.py --dist-dir dist/readiness-wheels --no-isolation` after installing the `hatchling` build backend in the active venv.
- `scripts/build_all_wheels.py` now verifies critical domain-pack files in the `duecare-llm-domains` wheel and fails on missing or duplicated entries.
- `duecare-llm-models` lazy-loads the optional Ollama HTTP dependency so importing `duecare.models` does not require `httpx` unless the Ollama adapter is used; the `ollama` extra now installs `httpx` explicitly.
- Final release readiness still needs a release-grade clean-environment build/install run before claiming PyPI readiness; a fully offline/no-index install also needs a complete third-party dependency wheelhouse.
