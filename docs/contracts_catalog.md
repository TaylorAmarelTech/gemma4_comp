# Contracts catalog — DueCare's standardized primitives

> DueCare is built from a small set of **standardized objects** with explicit contracts.
> This page is the catalog: each primitive, its shape, where it's defined, its validator,
> and the test that enforces it. The enforcement is **data-driven over the live registries**
> (`tests/test_primitives_conformance.py`), so a new instance is held to the contract with no
> hand-written test — adding a new harness, model target, or canonical-schema export
> automatically gets checked.

Design stance (reconciling Protocols + thin base classes):

- **`typing.Protocol` for cross-*layer* contracts** — `Model` / `Task` / `Agent` and the
  harness `HarnessBase` Protocol are duck-typed; no forced inheritance (rule `20_code_style`).
- **Thin base classes only *within* a layer** where there is real shared behaviour to DRY —
  e.g. `BaseHarness` (an opt-in convenience base that defaults `name`/`applied_layers`/
  `consumes`/`emits` and fans out safety layers). Thin = one level, behaviour-sharing, never
  a deep tree.

## The primitives

| Primitive | Shape / contract | Defined in | Enforced by |
|---|---|---|---|
| **Harness module** | `name: str`, `applied_layers: tuple`, `consumes: tuple`, `emits: tuple`, `register_routes(app)`, `spec: HarnessSpec` | `harnesses/base.py` (`HarnessBase` Protocol, `BaseHarness` thin base) | `test_primitives_conformance` (shape + module↔spec consistency) · `test_workbench_inventory_integrity` (spec completeness) |
| **HarnessSpec** | frozen dataclass: required `name`/`tier`/`kind`/`label`/`summary` + optional logic_paths/knowledge_packs/model_io/model_targets/… | `harnesses/base.py` | spec completeness + sub-primitive shape |
| **HarnessModelTarget** | `id`, `label`, `transport ∈ {gemma4_runtime, duecare_model_adapter, frontier_api, none, …}`, `role`, `default` (≤1 per harness) | `harnesses/base.py` | `test_every_model_target_conforms` |
| **HarnessLogicPath** | `id`, `label`, `steps`, `model_call ∈ {none, optional, required, hybrid}` | `harnesses/base.py` | `test_every_logic_path_conforms` |
| **KnowledgeObject v1.0 envelope** | wrapper `{schema_version="1.0", knowledge_object_type, id (kebab), content{…}}` + `provenance.content_sha256` | `knowledge_taxonomy.py` (`validate_envelope`, `content_sha256`, `node_id`) | `test_shipped_knowledge_object_is_a_valid_envelope` |
| **Entity edge** | `{subject_id, predicate ∈ KNOWN_PREDICATES, object_id, source, weight∈[0,1], qualifier}` | `scripts/entity_edges.py` (`normalize_edge`) | `test_entity_edge_canonical_shape_normalizes` |
| **FollowTheMoney EntityProxy** | `{id, schema∈{Company,Person,Organization,PublicBody,LegalEntity,Vessel}, properties:{prop:[values]}}` | `scripts/ftm_schema.py` (`to_ftm`) | `test_entity_record_converts_to_valid_ftm` |
| **Open Knowledge Format v0.1** | markdown + YAML frontmatter, required `type`; optional title/description/resource/tags/timestamp | `scripts/okf_export.py` (`validate_okf`) | `test_same_knowledge_object_exports_to_conformant_okf` · `test_okf_export` |
| **Bundle envelope v1.0** | Kaggle kernel output: `{schema_version, kernel_id, run_id, config, metadata, summary, results}` | `duecare.appendix_primitives` (`write_v1_bundle`) | public-surface `bundle_envelope_v1` check |
| **Registry spec** | config-driven resolver: `{id, url, format∈{html_table,json,csv,xlsx,pdf}, entity_type, jurisdiction, fields}` | `scripts/registry_spec.py` + `registry_specs.yaml` | `test_registry_spec` |
| **Model / Task / Agent** | cross-layer Protocols (duck-typed) | `duecare.core.contracts` + each package | per-package suites |

## How enforcement works

`tests/test_primitives_conformance.py` iterates the **live** registries — `all_harnesses()`,
each spec's `model_targets` / `logic_paths`, and the canonical-schema adapters — and asserts:

1. **Harness module primitive** — every harness has the six required members of the right type.
2. **Module ↔ spec consistency** — `spec.name == module.name`, `applied_layers` / `consumes`
   / `emits` match, `tier ∈ {primary, secondary}`, and tier matches PRIMARY/SECONDARY membership.
3. **Sub-primitive shape** — every model target has a non-empty id/label/role and a **registered
   transport**; ≤1 default per harness. Every logic path has id/label/steps and a known `model_call`.
4. **Canonical-schema agreement** — the same shipped KnowledgeObject validates as an envelope
   **and** exports to conformant OKF; the canonical entity edge normalises; an entity record
   converts to a valid FtM EntityProxy.

The transport and `model_call` vocabularies are **closed allowlists** in the test: adding a new
transport is a deliberate one-line registration there — which is the standardization the
contract is meant to guarantee.

## Adding a new primitive instance

- **New harness** → folder under `harnesses/<name>/` with `name`/`applied_layers`/`consumes`/
  `emits`/`register_routes`/`spec`; optionally extend `BaseHarness`. The conformance suite +
  inventory test enforce the contract automatically. Recipe: [`harness_pattern.md`](harness_pattern.md).
- **New data source / registry** → a config spec (no Python). Recipe:
  [`maintenance/entity_sources.md`](maintenance/entity_sources.md).
- **New canonical-schema export** → mirror `ftm_schema.py` / `okf_export.py`: a `render` + a
  `validate`, plus a conformance assertion here.

See also: [`harness_standard_contract.md`](harness_standard_contract.md) (HarnessSpec fields),
[`knowledge_module_schema.md`](knowledge_module_schema.md) (envelope), and
[`CONTRIBUTING.md`](../CONTRIBUTING.md).
