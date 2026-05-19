# DueCare examples

This folder contains runnable examples for people integrating or deploying DueCare. It is intentionally separate from raw evidence and benchmark data.

| Folder | Purpose | Status policy |
|---|---|---|
| [`deployment/`](./deployment/) | End-to-end topology examples: local, NGO-office edge, hosted server, hybrid edge/cloud. | Keep runnable examples here; mark roadmap pieces clearly. |
| [`embedding/`](./embedding/) | Client/embed examples: web widget, React, messaging bots, platform adapters. | Keep integration examples here; planned examples must stay labeled as planned. |

## What does not belong here

- Raw worker chats, IDs, contact details, private documents, or unsanitized evidence. Those stay out of git in `evidence_raw/` until explicitly redacted.
- Large generated benchmark datasets. Those belong in `data/`, `configs/duecare/domains/`, package `_data/`, or Kaggle dataset folders depending on purpose.
- One-off historical experiments. Move those to `_archive/<date-or-purpose>/` with a manifest instead of deleting them.

## Related docs

- [Deployment topologies](../docs/deployment_topologies.md)
- [Embedding guide](../docs/embedding_guide.md)
- [Launch packaging options](../docs/launch_packaging_options.md)
- [Repository layout](../docs/REPO_LAYOUT.md)
