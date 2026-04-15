---
title: DueCare — Migrant Worker Protection
emoji: 🛡️
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: true
license: mit
short_description: On-device LLM safety evaluator. Privacy is non-negotiable.
tags:
  - gemma
  - safety
  - trafficking
  - migrant-workers
  - ilo
---

# DueCare — HuggingFace Spaces deployment

Public, login-free demo of DueCare for the Gemma 4 Good Hackathon.

**Live demo:** `https://huggingface.co/spaces/<YOUR_HF_USERNAME>/duecare-demo`

## One-time setup

1. Create an HF account: https://huggingface.co/join
2. Create a **write-scoped token**: https://huggingface.co/settings/tokens
3. Save it to `.env` in the project root as `HF_TOKEN=hf_...`
4. Create a new Space: https://huggingface.co/new-space
   - **Name:** `duecare-demo`
   - **SDK:** Docker
   - **Visibility:** Public

## Deploy

From the project root:

```bash
# Clone the empty Space alongside the project
cd ..
git clone https://huggingface.co/spaces/<YOUR_HF_USERNAME>/duecare-demo
cd duecare-demo

# Copy the deployment bundle in
cp ../gemma4_comp/deployment/hf_spaces/Dockerfile ./Dockerfile
cp ../gemma4_comp/deployment/hf_spaces/README.md ./README.md
cp ../gemma4_comp/requirements.txt ./
cp ../gemma4_comp/pyproject.toml ./
cp -r ../gemma4_comp/packages ./
cp -r ../gemma4_comp/src ./
cp -r ../gemma4_comp/configs ./

# Push — HF Spaces builds and publishes automatically
git add .
git commit -m "Deploy DueCare demo"
git push
```

The Space will take ~5 minutes to build on first push. When it's live,
paste the URL into `docs/writeup_draft.md` under the Reproducibility
section.

## What judges will see

- Paste-and-analyze interface — no login required
- Jurisdiction + language selectors (PH→HK, PH→SA, BD→MY, NP→MY, etc.)
- Score + grade + action for every input
- Detected indicators (illegal fees, passport retention, debt bondage)
- Applicable ILO conventions + jurisdiction-specific hotlines
- Five worked example scenarios one click away

## What's NOT in this Space (deliberately)

- **Gemma 4 inference runs locally via Ollama on your machine**, not on
  the Space's free-tier RAM. The Space serves the deterministic
  WeightedRubricScorer (no GPU needed); the Gemma-powered endpoints
  (`/api/v1/evaluate`, `/api/v1/function-call`, `/api/v1/analyze-document`)
  fail over gracefully when Ollama isn't reachable.
- **No PII is logged.** Analyses go through the Anonymizer before any
  persistence path. The Space's in-memory log is capped at 100 recent
  results and cleared on restart.

## Resource profile

- **CPU:** 2 cores (free tier)
- **RAM:** 16 GB (free tier) — we use <500 MB for the scorer
- **Storage:** ephemeral; no database writes
- **Cold start:** ~15s on first request

## Alternate hosting (if HF Spaces is unavailable)

The same `Dockerfile` works on any container host:

```bash
# Modal Labs (free credits)
modal deploy deployment/hf_spaces/Dockerfile

# Render.com (free tier)
# Create a new Web Service, point at the repo, path: deployment/hf_spaces/Dockerfile

# Fly.io
fly launch --dockerfile deployment/hf_spaces/Dockerfile

# Local
docker build -f deployment/hf_spaces/Dockerfile -t duecare-demo .
docker run -p 7860:7860 duecare-demo
```
