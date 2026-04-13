---
description: Push everything - notebooks, eval dataset, and fine-tuned model - to Kaggle.
---

This is the "ship it" command. It runs:

```bash
python scripts/publish_kaggle.py publish-all
```

which internally runs, in order:

1. `auth-check`       - credentials present
2. `push-notebooks`   - 4 forge kernels
3. `publish-dataset`  - duecare-eval-results (version first, create fallback)
4. `publish-model`    - duecare-safety-harness (create or new instance version)

The script fails fast on any step so a partial publication doesn't
leave the submission in an inconsistent state.

If `$ARGUMENTS` contains `--dry-run`, pass it through for a preview.

**Before running for real**, confirm with the user:
- The 4 notebooks have been re-executed end-to-end locally
- Eval artefacts are populated in `kaggle/datasets/forge_eval_results/`
- The fine-tuned model weights (if any) are in `kaggle/models/forge_safety_harness/`
