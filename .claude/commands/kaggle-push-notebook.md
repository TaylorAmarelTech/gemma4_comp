---
description: Push the 4 Duecare notebooks to Kaggle as private kernels.
---

First run `python scripts/publish_kaggle.py auth-check` to confirm credentials.

Then run `python scripts/publish_kaggle.py push-notebooks` which pushes all 4:

- `kaggle/kernels/forge_01_quickstart/`
- `kaggle/kernels/forge_02_cross_domain_proof/`
- `kaggle/kernels/forge_03_agent_swarm_deep_dive/`
- `kaggle/kernels/forge_04_submission_walkthrough/`

Each directory already contains a validated `kernel-metadata.json` and
the `.ipynb` named in `code_file`.  The script fails fast on the first
kernel that fails validation so the user can see which one is broken.

After a successful push, run `python scripts/publish_kaggle.py status-notebooks`
so the user can see whether each kernel is still "running", "complete", or
"error" on Kaggle.

Before pushing, if `$ARGUMENTS` contains `--dry-run`, pass it through
so the user can preview without touching the network.
