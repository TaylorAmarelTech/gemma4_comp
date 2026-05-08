# Render deployment — duecare-ai.com hub

This folder contains the lightweight CPU-only deployment path for the public Duecare hub.

The hub is separate from the Kaggle notebook showcase. It does not load Gemma 4 directly. It demonstrates the platform layer:

- anonymized safety-signal intake;
- knowledge-pack discovery;
- OpenClaw/OpenCrawl-style public-source update proposals;
- aggregate trend counters;
- public OpenAPI documentation.

## Why this matters

The Kaggle app proves the model/harness interaction. The hub proves Duecare can become shared infrastructure: NGOs, regulators, platforms, and researchers can exchange anonymized patterns, prompts, evaluations, contact updates, and RAG updates without centralizing raw worker cases.

## Deploy

1. Create a Render web service from the GitHub repo.
2. Use Docker runtime.
3. Set Dockerfile path to:

   ```text
   deployment/render/Dockerfile
   ```

4. Set health check path:

   ```text
   /healthz
   ```

5. Add custom domain:

   ```text
   duecare-ai.com
   www.duecare-ai.com
   ```

6. Configure DNS at the domain registrar using Render's shown CNAME/A records.

The blueprint in [render.yaml](render.yaml) can be copied to the repo root if using Render Blueprint deploys.

## Smoke checks

After deployment:

```text
GET https://duecare-ai.com/healthz
GET https://duecare-ai.com/api/hub/status
GET https://duecare-ai.com/api/hub/knowledge-packs
GET https://duecare-ai.com/docs
```

## Safety boundary

The hub accepts anonymized or aggregate signals only. It rejects obvious emails, phone numbers, identity-document strings, and street-address patterns in free-text summaries.

Do not use this service as a raw case-management database. Raw cases stay local with workers, NGOs, agencies, or platforms unless explicit consent and anonymization gates are in place.

Canonical rule:

> Duecare drafts; the user or trusted caseworker decides. Privacy is non-negotiable.
