# DueCare Package Architecture

`the_forge.md` is the stable architecture target referenced by package
READMEs and package metadata. Older drafts used the Forge name for the
multi-package DueCare workspace; the public product name is DueCare.

## Layer Model

DueCare is organized as a PEP 420 namespace-package workspace. The packages
share the `duecare` Python namespace but can be installed independently when a
deployment only needs part of the system.

| Layer | Packages | Role |
|---|---|---|
| Core contracts | `duecare-llm-core` | Schemas, enums, registries, provenance, and observability. |
| Models and domains | `duecare-llm-models`, `duecare-llm-domains` | Model adapters plus pluggable domain packs. |
| Capability tests | `duecare-llm-tasks` | Guardrails, anonymization, extraction, grounding, multimodal, tool-use, and related test surfaces. |
| Agents and workflows | `duecare-llm-agents`, `duecare-llm-workflows` | Agent orchestration, retry/budget policy, and YAML DAG execution. |
| Publication and operations | `duecare-llm-publishing`, `duecare-llm-cli` | Reports, model cards, Kaggle/HF helpers, and command-line workflows. |
| Product/runtime surfaces | `duecare-llm-chat`, `duecare-llm-server`, `duecare-llm-engine`, `duecare-llm-evidence-db`, `duecare-llm-training`, `duecare-llm-research-tools`, `duecare-llm-nl2sql` | Workbench UI, safety pipeline, evidence store, training helpers, research tools, and query surfaces. |
| Meta package | `duecare-llm` | Workspace-level install and workflow entry point. |

## Runtime Pattern

The runtime uses a deterministic-first safety harness:

1. Prescan and GREP rules identify exploitation, PII, and policy indicators.
2. RAG and knowledge packs add controlled legal and policy context.
3. Tools resolve corridor facts, contacts, fee caps, and source checks.
4. Gemma 4 generation or scoring runs only after the harness has assembled
   bounded context and safety constraints.
5. Outputs carry provenance, trace, and review metadata so they can be
   reproduced or audited.

## Canonical References

- Repository map: [REPO_LAYOUT.md](./REPO_LAYOUT.md)
- Package inventory: [PACKAGE_INVENTORY.md](./PACKAGE_INVENTORY.md)
- System map: [system_map.md](./system_map.md)
- Harness ecosystem: [harness_ecosystem.md](./harness_ecosystem.md)
- Architecture overview: [architecture.md](./architecture.md)
- Extension guide: [EXTENDING.md](./EXTENDING.md)

