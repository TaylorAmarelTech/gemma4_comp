# Archived one-off scripts (2026-04)

These scripts ran once and are no longer part of the active build or
publish flow. They are archived rather than deleted so that:

- Future AI sessions stop treating them as current tooling.
- Git history still contains them.
- If a pattern comes back (e.g. another renumber pass), the prior
  implementation can be copied forward.

## What was archived and why

| Script                                | Purpose                                                                                                            | Why archived                                                                                                                     |
|---------------------------------------|--------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| `align_kaggle_kernel_metadata.py`     | Pre-publish `kernel-metadata.json` normalization.                                                                 | Superseded by the builders themselves, which emit canonical metadata.                                                            |
| `align_metadata_from_push_log.py`     | Parse `push_all_sequential.py` log and rewrite metadata ids to match live slugs.                                  | One-time reconciliation. Source-of-truth slug mapping now lives in `scripts/_public_slugs.py`.                                   |
| `align_metadata_to_slug_map.py`       | Force metadata ids to match `kaggle_live_slug_map.json`.                                                          | Same.                                                                                                                            |
| `normalize_canonical_slugs.py`        | Rewrite every kernel id to the title-derived `NNN-duecare-*` pattern.                                             | The canonical pattern is now mixed (`duecare-NNN-*` for some, `NNN-duecare-*` for others). Overrides live in `_public_slugs.py`. |
| `push_all_sequential.py`              | Sequential rate-limit-aware push of ~29 kernels.                                                                  | Superseded by targeted per-notebook pushes and `publish_kaggle.py`.                                                              |
| `push_all_with_fallback.py`           | Bulk push with fallback-slug creation on failure.                                                                 | Same.                                                                                                                            |
| `push_failed_with_rate_limit.py`      | Retry the specific kernels that hit SaveKernel rate limits.                                                       | Same.                                                                                                                            |
| `update_builders_to_canonical.py`     | Rewrite every builder's `KERNEL_ID` + `URL_NNN` constants to the `NNN-duecare-*` canonical form.                   | Applied once; canonical form has since become mixed. Keeping this would re-introduce a stale single-pattern assumption.          |
| `rename_project.py`                   | Rename the old `forge` package namespace to `duecare`.                                                            | One-time. `duecare` is the current namespace.                                                                                    |
| `migrate_to_packages.py`              | Migrate from flat `src/` layout to the 8-package `packages/duecare-llm-*` layout.                                  | One-time. Workspace is now multi-package.                                                                                        |

If you need the logic from one of these, copy it forward into a
fresh, current script rather than reviving the archived version.

## Additional one-offs archived (2026-04-18 cleanup pass)

| Script                             | Purpose                                                                                                          | Why archived                                                                                                   |
|------------------------------------|------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| `implement_component_docs.py`      | Wrote the initial component-docs scaffolding for the 7 `duecare-llm-*` packages.                                | One-time scaffolding. Docs are now hand-maintained.                                                            |
| `implement_domain_content.py`      | Wrote the initial `configs/duecare/` domain content (taxonomy/rubric/pii_spec/seed_prompts YAML).                | One-time scaffolding.                                                                                          |
| `implement_forge_agents.py`        | Wrote the initial `duecare.agents` package body.                                                                 | One-time scaffolding.                                                                                          |
| `implement_forge_core.py`          | Wrote the initial `duecare.core` + `duecare.domains` package bodies.                                             | One-time scaffolding.                                                                                          |
| `implement_forge_models.py`        | Wrote the initial `duecare.models` adapter bodies.                                                               | One-time scaffolding.                                                                                          |
| `implement_forge_rest.py`          | Wrote the initial `duecare.workflows` + `duecare.publishing` + meta package bodies.                              | One-time scaffolding.                                                                                          |
| `implement_forge_tasks.py`         | Wrote the initial `duecare.tasks` capability-test bodies.                                                        | One-time scaffolding.                                                                                          |
| `reclassify_nb00_with_v3.py`       | Applied the V3 6-band classifier to the pre-renumbering `NB 00` results.                                         | References `NB 00` (superseded by `100_gemma_exploration` after the 2026-04-17 renumber).                      |
| `ingest_google_drive_reference_material.py` | Ingestion helper that pulled the author's Google Drive reference folders into `_reference/`.               | User-specific one-off; the reference material is already copied.                                               |
| `_align_titles.py` (repo root)     | Aligned 7 kernel titles to their live Kaggle values to silence push warnings.                                    | One-time alignment. Current titles live in the builder scripts.                                                 |
| `_audit_kernels.py` (repo root)    | Cross-referenced kernel dirs against a manual mapping JSON.                                                      | One-time audit.                                                                                                 |
| `_inject_110_120.py` (repo root)   | Injected at-a-glance into 110 and 120 at the `md(PREVIEW_MD)` insertion point.                                   | One-time migration. The at-a-glance block is now part of the builder template.                                 |
| `_inject_200.py` (repo root)       | Same for 200.                                                                                                    | One-time.                                                                                                       |
| `_inject_at_a_glance.py` (repo root)| Generic injector that found `cells = [` and inserted md+code after `md(HEADER)`.                                 | One-time.                                                                                                       |
| `_inject_bulk.py` (repo root)      | Applied the injection across every direct builder.                                                               | One-time.                                                                                                       |
| `_kernel_mapping.json` (repo root) | Input JSON for the above scripts.                                                                                | One-time mapping file.                                                                                          |

