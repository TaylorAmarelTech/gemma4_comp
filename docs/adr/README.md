# Architecture Decision Records

Each ADR captures one load-bearing decision: the context, the
options considered, the choice, and the consequences. New ADRs
land via PR; existing ADRs are immutable (a new ADR supersedes
an old one rather than mutating it).

Format follows [Michael Nygard's template](https://github.com/joelparkerhenderson/architecture-decision-record/blob/main/locales/en/templates/decision-record-template-by-michael-nygard/index.md).

## Index

| # | Title | Status |
|---|---|---|
| [001](./001-multi-package-pypi-split.md) | Multi-package PyPI split (17 wheels under `duecare.*` namespace) | Accepted |
| [002](./002-folder-per-module-pattern.md) | Folder-per-module pattern with auto-generated meta files | Accepted |
| [003](./003-on-device-default-cloud-opt-in.md) | On-device default; cloud routing opt-in for Android | Accepted |
| [004](./004-six-plus-five-notebook-shape.md) | 6 core + 5 appendix submission shape (vs single-mega-notebook) | Accepted |
| [005](./005-tenant-id-from-edge-proxy.md) | Tenant id extracted from edge proxy headers (vs in-app auth) | Accepted |

## When to write an ADR

- A decision affects more than one component
- A reasonable engineer might pick the other option
- Reversal would cost more than a day of work
- You'll need to defend the decision to a future security / compliance review

## When NOT to write an ADR

- Pure refactor (no change in observable behavior)
- Naming / file-layout decisions inside a single module
- One-time fix or workaround

## How to add a new ADR

1. Copy the template:
   ```bash
   cp docs/adr/_template.md docs/adr/00N-short-slug.md
   ```
2. Fill in: Status, Context, Decision, Consequences. Keep each
   section to a few paragraphs — long ADRs don't get re-read.
3. Add a row to the index above.
4. PR-review like any code change.

When superseding an existing ADR:

- Set the old ADR's status to "Superseded by ADR 00X"
- Don't edit the old ADR's body — superseded means superseded
- Reference the old ADR's number in the new ADR's Context section
