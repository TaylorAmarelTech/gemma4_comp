---
description: Show the current status of all Duecare kernels on Kaggle.
---

Run `python scripts/publish_kaggle.py status-notebooks` and relay the
result for each of the 4 kernels:

- `taylorsamarel/duecare-quickstart`
- `taylorsamarel/duecare-cross-domain-proof`
- `taylorsamarel/duecare-agent-swarm-deep-dive`
- `taylorsamarel/duecare-submission-walkthrough`

Expected statuses: `queued`, `running`, `complete`, or `error`.

If a kernel is in `error` state, tell the user to check its Kaggle
page for the traceback and link to `https://www.kaggle.com/code/<id>`
(replacing `<id>` with the kernel id above).
