---
description: Verify the Kaggle CLI is installed and credentials are in place.
---

Run `python scripts/publish_kaggle.py auth-check` and report:

- Whether `~/.kaggle/kaggle.json` exists
- Whether `KAGGLE_USERNAME` / `KAGGLE_KEY` env vars are set
- The kaggle CLI version (success → green light for publishing)

If credentials are missing, tell the user how to install them:

```bash
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

Do not attempt to push any kernels or datasets from this command.
