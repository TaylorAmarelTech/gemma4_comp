# Duecare demo bundle v1 (2026-04-25)

A complete drop-in deliverable: 7 wheels + the Kaggle notebook +
6 sample documents. Total ~180 KB.

## Contents

```
release/duecare_demo_v1/
├── wheels/                      7 *.whl files (89 KB)
│   ├── duecare_llm_evidence_db-0.1.0-py3-none-any.whl
│   ├── duecare_llm_engine-0.1.0-py3-none-any.whl
│   ├── duecare_llm_nl2sql-0.1.0-py3-none-any.whl
│   ├── duecare_llm_research_tools-0.1.0-py3-none-any.whl
│   ├── duecare_llm_server-0.1.0-py3-none-any.whl
│   ├── duecare_llm_training-0.1.0-py3-none-any.whl
│   └── duecare_llm_cli-0.1.0-py3-none-any.whl
├── notebook/
│   └── duecare_demo_kernel.py   single-cell Kaggle paste
├── sample_data/                 6 demo documents (3 case bundles)
│   ├── manila_recruitment_001/
│   ├── saudi_employer_002/
│   └── hk_complaint_003/
└── README.md                    this file
```

## Live demo URL

The latest version of `notebook/duecare_demo_kernel.py` is also
published as a Kaggle kernel:

  https://www.kaggle.com/code/taylorsamarel/duecare-live-demo-app

The wheels are versioned at:

  https://www.kaggle.com/datasets/taylorsamarel/duecare-llm-wheels

## Run locally (no Kaggle)

```bash
pip install --no-input wheels/*.whl
duecare init                        # create DB + .duecarerc
duecare demo-init                   # load sample evidence
duecare serve --port 8080           # http://localhost:8080
```

## Run in Kaggle (full demo with public URL)

1. Open https://www.kaggle.com/code/taylorsamarel/duecare-live-demo-app
2. Settings (right panel):
   - Accelerator: GPU T4 x2 (or any T4)
   - Internet: ON
   - Add Data: confirm `taylorsamarel/duecare-llm-wheels` is attached
   - (optional) Add Data: Models -> search "gemma 4" -> attach for full Gemma path
   - (optional) Add-ons -> Secrets -> attach HF_TOKEN if you want HF download
3. Hit "Run All"
4. Watch for the `https://*.trycloudflare.com` URL in stage 8
5. Open that URL on your laptop

## What runs without Gemma

The cell auto-detects whether Gemma can load. Without an attached model
or HF token, it skips Gemma loading and runs in **HEURISTIC mode** with
a multi-signal scoring engine that catches:
- passport confiscation language (ILO C029)
- restriction of movement
- debt bondage
- coercion through authority figures
- excessive recruitment fees
- 13 locale-aware migrant-worker hotlines (PH, ID, NP, IN, BD, LK, HK,
  SA, AE, QA, KW, plus the ILO TIP fallback)

So `Mama-san said I must pay USD 5,000 deposit and she will keep my
passport` lands at **severity 9-10** with detailed signal breakdown.

## What's wired in

| Surface | Endpoint | File upload? |
|---|---|---|
| `/enterprise` (compliance) | `/api/moderate` (text) + `/api/moderate_file` (image/PDF/DOCX) | YES |
| `/individual` (worker chat) | `/api/worker_check` + `/api/worker_check_file` | YES |
| `/knowledge` (NL query) | `/api/query` (template + Gemma fallback) | no |
| `/settings` | `/api/settings`, `/api/runs`, `/api/research/openclaw` | no |
| Background | `/api/process` (full pipeline as background task) | no |
| Task queue | `/api/queue/submit` + `/api/queue/status/{id}` | no |

File-upload endpoints accept: `.pdf`, `.docx`, `.txt`, `.md`, plus
images (`.png`, `.jpg`, `.tiff`, `.bmp`, `.gif`, `.webp`). Image OCR via
pytesseract, PDF via pypdfium2, DOCX via stdlib zipfile + XML parse.

## Updating the bundle

Run from the project root:

```bash
python scripts/build_all_wheels.py --no-isolation --clean
# then refresh release/duecare_demo_v1/wheels/ and notebook/
python scripts/push_kaggle_demo.py    # uploads + pushes to Kaggle
```
