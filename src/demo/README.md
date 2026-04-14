# DueCare Demo — FastAPI Dashboard

Live, on-device LLM safety evaluation. No API keys, no cloud calls.

## Two ways to run

### Quickest — Python only

```bash
pip install -e packages/duecare-llm[demo]
python -m uvicorn src.demo.app:app --port 8080
# open http://localhost:8080
```

### Full stack — Docker (demo + Ollama + Gemma 4)

```bash
docker compose up
# First run: ~5 minutes to pull Gemma 4 E4B (~4 GB)
# open http://localhost:8080
```

## What you'll see

- A text input where you paste any suspicious job posting, chat message,
  contract text, or social media comment.
- A jurisdiction picker (Philippines, Hong Kong, Saudi Arabia, Malaysia,
  Nepal, Bangladesh, Indonesia, or International).
- A language picker (English, Tagalog; more can be added via the
  `warning_templates` dict in `scorer.py`).
- A one-click analysis that returns:
  - An overall safety **score** (0–1)
  - A **grade** (worst, bad, neutral, good, best)
  - A recommended **action** (block, review, warn, pass)
  - A list of matched **indicators** (e.g., `illegal_recruitment_fee`,
    `debt_bondage_risk`)
  - Per-rubric detailed criteria with pass/fail results
  - Jurisdiction-specific **resources** (hotlines, NGOs, regulators)
  - A localized **warning text** the user can copy directly

## API endpoints

All endpoints live under `/api/v1/` and are documented at `/docs`
(OpenAPI spec auto-generated from Pydantic models).

| Endpoint | Method | What it does |
|----------|--------|--------------|
| `/api/v1/health` | GET | Liveness probe |
| `/api/v1/analyze` | POST | Single-text safety evaluation |
| `/api/v1/batch` | POST | Batch evaluation (up to 500 items) |
| `/api/v1/stats` | GET | Aggregate analysis metrics |
| `/api/v1/evaluate` | POST | Full Gemma 4 evaluation (requires Ollama) |
| `/api/v1/function-call` | POST | Demonstrate Gemma 4 native function calling |
| `/api/v1/analyze-document` | POST | Multimodal document analysis |

## What it runs without a model

The deterministic `WeightedRubricScorer` in `scorer.py` scores any text
against 5 trafficking rubrics with 54 weighted criteria. **Zero LLM
inference required.** This is the production fallback for NGOs that can't
run a local model yet.

## What it runs with Gemma 4

If Ollama is running on `OLLAMA_HOST` (default: `http://localhost:11434`)
and `gemma4:e4b` is pulled, the demo also exposes:

- **Full evaluation with reasoning** — Gemma 4 judges each response with
  narrative explanation.
- **Native function calling** — 5 registered tools (`anonymize`,
  `classify`, `extract_facts`, `fact_db_query`, `check_legal`) that
  Gemma 4 can call mid-response.
- **Multimodal document analysis** — upload a recruitment contract photo
  and Gemma 4 flags illegal fee clauses.

## Deploy to HuggingFace Spaces

```bash
# Create a new Space at huggingface.co (Docker SDK)
git clone https://huggingface.co/spaces/YOUR_USERNAME/duecare-demo
cd duecare-demo

# Copy the demo layer into the Space
cp -r ../gemma4_comp/src/ .
cp -r ../gemma4_comp/packages/ .
cp -r ../gemma4_comp/configs/ .
cp ../gemma4_comp/Dockerfile.demo Dockerfile
cp ../gemma4_comp/requirements.txt .
cp ../gemma4_comp/pyproject.toml .

# The HF Spaces default port is 7860; override in the Dockerfile
sed -i 's/--port", "8080"/--port", "7860"/' Dockerfile

git add . && git commit -m "Deploy DueCare demo" && git push
# Your space is live at huggingface.co/spaces/YOUR_USERNAME/duecare-demo
```

## File layout

```
src/demo/
├── app.py                # FastAPI app — 11 endpoints + HTML dashboard
├── scorer.py             # WeightedRubricScorer — the deterministic core
├── models.py             # Pydantic request/response schemas
├── gemma_evaluator.py    # Gemma 4 via Ollama integration
├── function_calling.py   # Tool definitions + dispatch
├── multimodal.py         # Document image analysis
├── quick_filter.py       # Pre-Gemma cheap filter
├── rag.py                # Retrieval-augmented evaluation
└── chat_viewer.py        # Demo chat history UI
```

## For judges

If you're on the Gemma 4 Good Hackathon panel, `docs/FOR_JUDGES.md` at
the repo root has a focused 5-minute verification walkthrough.

**Privacy is non-negotiable.** The demo runs entirely on your machine
unless you explicitly configure an external LLM endpoint.
