# configs/

Version-controlled YAML configuration files, one per component.
See `docs/architecture.md` section 17 (Cross-cutting: Configuration).

| File | Loaded by |
|---|---|
| `sources.yaml` | `src/data/sources/registry.py` |
| `classification.yaml` | `src/data/classify/*` |
| `anonymization.yaml` | `src/data/anon/*` |
| `attacks.yaml` | `src/attacks/registry.py` |
| `grading.yaml` | `src/grading/*` |
| `training_e4b.yaml` | `src/training/finetune.py` |
| `export.yaml` | `src/export/*` |
| `eval.yaml` | `src/eval/runner.py` |
| `demo.yaml` | `src/demo/app.py` |

Secrets (API keys) never live here - they come from environment variables
with the `GEMMA4_` prefix.
