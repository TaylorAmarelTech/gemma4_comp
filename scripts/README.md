# scripts/

Orchestration scripts - one per pipeline stage. These are thin wrappers
over the src/ modules and exist to make the pipeline runnable without
memorizing module paths.

| # | Script | Stage | See |
|---|---|---|---|
| 00 | `00_ingest.py` | Source fetch + normalize + stage | `src/data/ingest/` |
| 01 | `01_classify.py` | Classify staging items | `src/data/classify/` |
| 02 | `02_anonymize.py` | PII detection + redaction + verify | `src/data/anon/` |
| 03 | `03_build_prompts.py` | Populate prompt store from clean DB | `src/prompts/` |
| 04 | `04_prepare_training_data.py` | Build Unsloth JSONL splits | `src/training/prepare.py` |
| 05 | `05_finetune.py` | Unsloth + LoRA fine-tune | `src/training/finetune.py` |
| 06 | `06_export.py` | Merge LoRA, quantize GGUF, publish | `src/export/` |
| 07 | `07_evaluate.py` | Run benchmark + generate report | `src/eval/` |
| 08 | `08_publish.py` | Push model to HF Hub, update writeup | `src/export/publish.py` |

One-shot scripts:
- `scaffold.py` - creates the src/ module tree (run once at setup)
- `scaffold.py` is idempotent and safe to re-run.
- `validate_main_kaggle_kernels.py` - static compatibility gate for the Kaggle root layout plus the four active/optional root `kernel.py` files and their `kernel-metadata.json` publish settings; appendix and archived notebooks are intentionally out of kernel compatibility.
- `validate_kaggle_page_sources.py` - static source gate for the active Kernel 01/02 HTML assets and optional benchmark kernel markers. It checks `/static/*` and `/wb-static/*` references without importing packages, starting FastAPI, or loading a model.
