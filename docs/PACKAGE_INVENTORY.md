# DueCare package inventory

Generated during the 2026-05-10 readiness cleanup pass and reconciled on
2026-07-27. The workspace currently contains **18** buildable Python
packages under `packages/`, all sharing the `duecare` namespace where
applicable.

## Inventory

| Package | Version | Wheel package root | Console scripts | Extras | Purpose |
|---|---:|---|---|---|---|
| `duecare-llm` | 0.1.0 | `src/duecare` | `duecare`, `forge` | `all`, `dev` | Meta package that pulls in DueCare components and exposes CLI entry points. |
| `duecare-llm-agents` | 0.1.0 | `src/duecare` | none | `trainer` | Agent swarm layer. |
| `duecare-llm-benchmark` | 0.1.0 | `src/duecare` | none | none | Bundled benchmark test sets, scoring, and aggregation. |
| `duecare-llm-chat` | 0.17.0 | `src/duecare` | none | none | Gemma 4 workbench, harness UI, sample bundles, knowledge-file I/O, and the reusable portability contract consumed by the Kaggle notebooks. |
| `duecare-llm-cli` | 0.1.0 | `src/duecare` | `duecare` | none | Current reliable CLI package for `duecare init`, `duecare demo-stage`, and `duecare serve`. |
| `duecare-llm-core` | 0.1.0 | `src/duecare` | none | none | Core contracts, schemas, enums, registries, provenance, and observability. |
| `duecare-llm-domains` | 0.1.0 | `src/duecare` | none | none | Domain pack system with lightweight bundled data; the full 74,640-prompt trafficking corpus lives in repo config/Kaggle assets. |
| `duecare-llm-engine` | 0.1.0 | `src/duecare` | none | `otel` | Pipeline engine wrapper. |
| `duecare-llm-evidence-db` | 0.1.0 | `src/duecare` | none | `postgres`, `all` | Evidence database backends. |
| `duecare-llm-kit` | 0.1.0 | `src/duecare` | `duecare-kit-report`, `duecare-kit-corpus` | `viz`, `nlp`, `all` | Reusable indicator engine, visualization helpers, HTML reports, and corpus exports. |
| `duecare-llm-models` | 0.1.0 | `src/duecare` | none | `transformers`, `unsloth`, `llama-cpp`, `ollama`, `openai`, `anthropic`, `google`, `hf-endpoint`, `all` | Model adapters. |
| `duecare-llm-nl2sql` | 0.1.0 | `src/duecare` | none | none | Natural-language-to-SQL translator. |
| `duecare-llm-publishing` | 0.1.0 | `src/duecare` | none | `hf-hub`, `kaggle`, `all` | Publication helpers for HF Hub, Kaggle, reports, and model cards. |
| `duecare-llm-research-tools` | 0.1.0 | `src/duecare` | none | `http` | External research tool wrappers with PII filtering. |
| `duecare-llm-server` | 0.1.2 | `src/duecare` | none | `observability`, `otel` | FastAPI server and demo UI surface. |
| `duecare-llm-tasks` | 0.1.0 | `src/duecare` | none | `anonymization`, `embedding` | Capability tests. |
| `duecare-llm-training` | 0.1.0 | `src/duecare` | none | `clustering`, `unsloth` | Synthetic labeling, active learning, dataset assembly, and fine-tune kickoff. |
| `duecare-llm-workflows` | 0.1.0 | `src/duecare` | none | none | Workflow DAG orchestration. |

## Current install and registry truth

None of the 18 distributions is currently published on PyPI (verified against
the public PyPI JSON API on 2026-07-27). Bare commands such as
`pip install duecare-llm-kit` describe the intended post-release interface;
they are not a working registry path today.

For a development checkout, install the complete workspace from source:

```powershell
uv sync --all-packages
uv run duecare init
uv run duecare demo-stage
uv run duecare serve --port 8080
```

For a release-like local install, build all 18 wheels and tell pip to prefer
that local directory while resolving third-party dependencies normally:

```powershell
python scripts/build_all_wheels.py --clean
python -m pip install --find-links dist duecare-llm-cli
```

The meta-package `duecare-llm` remains the desired one-command distribution story. It was smoke-tested in an isolated `virtualenv` from the locally built wheels for `duecare --help`, `duecare domains list`, and an end-to-end `duecare run rapid_probe --target-model local_smoke --domain trafficking` workflow against a local OpenAI-compatible fake backend. Real Gemma/Ollama/API runs still require the corresponding target-model backend and credentials/model files.

The `duecare-llm-cli` path was smoke-tested in an isolated `virtualenv` from the locally built wheels: install, `duecare --help`, `duecare init`, and `duecare demo-stage` passed.

## Readiness notes

- `scripts/build_all_wheels.py` now includes all 18 package directories in its default build order.
- `.github/workflows/pypi-publish.yml` is the sole registry publisher. Generic
  `v*` tags do not publish packages, manual runs cannot target production PyPI,
  and a `package-NAME-vMAJOR.MINOR.PATCH` tag fails closed unless it selects one
  exact name/version row in `configs/duecare/package_release.toml`.
- Packages use independent SemVer. Manual release-candidate runs build all
  manifest rows in canonical dependency order by default, while a production
  tag builds and publishes only its selected package.
- `duecare-llm-chat` intentionally remains on an independent harness cadence; the current notebook portability contract is `0.17.0`, exposed through `duecare.chat.portability` and `GET /api/portability`, so synchronized `0.1.0` infrastructure package tags are not confused with the chat wheel version.
- The May readiness receipt covered the original 17 packages. The added
  `duecare-llm-kit` has its own clean wheel/sdist and isolated-install checks;
  rerun the 18-package wheel build before a whole-workspace candidate claim.
- `scripts/build_all_wheels.py` now verifies critical domain-pack files in the `duecare-llm-domains` wheel and fails on missing or duplicated entries.
- `duecare-llm-models` lazy-loads the optional Ollama HTTP dependency so importing `duecare.models` does not require `httpx` unless the Ollama adapter is used; the `ollama` extra now installs `httpx` explicitly.
- Final release readiness still needs a release-grade clean-environment build/install run before claiming PyPI readiness; a fully offline/no-index install also needs a complete third-party dependency wheelhouse.
- `duecare-llm-chat` remains `0.17.0`, `duecare-llm-server` remains `0.1.2`, and
  the other distributions remain `0.1.0`. Those versions are reconciled by the
  independent-release manifest instead of being treated as a blocker.
