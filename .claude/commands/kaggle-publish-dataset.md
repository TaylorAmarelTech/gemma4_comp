---
description: Create or version the duecare-eval-results Kaggle Dataset.
---

Run `python scripts/publish_kaggle.py publish-dataset`.

The script looks at `kaggle/datasets/forge_eval_results/`, which must
contain `dataset-metadata.json` and any data files the user wants to
publish.  It first attempts `kaggle datasets version` (the common case
once the dataset exists) and falls back to `kaggle datasets create` on
the first run.

After pushing, remind the user:
1. Kaggle datasets need a non-empty `data/` area - make sure
   `reports/`, `runs.jsonl`, and `domains.json` are populated before
   publishing or Kaggle will reject the upload.
2. Every published version is public once the dataset is marked public;
   `isPrivate` defaults to `true` during development.

If `$ARGUMENTS` contains `--dry-run`, pass it through.
