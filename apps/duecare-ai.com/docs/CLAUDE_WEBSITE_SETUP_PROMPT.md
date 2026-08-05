# Claude prompt for duecare-ai.com website setup

Copy this prompt into Claude when working on the public website repo.

---

You are working on the public website and coordination hub for Duecare AI, a Gemma 4 Good Hackathon project. The website now lives inside the main monorepo so it can share context with the Kaggle notebooks, packages, docs, and Gemma 4 harness.

Repository and deployment facts:

- Public repo: https://github.com/TaylorAmarelTech/gemma4_comp
- Website folder: apps/duecare-ai.com
- Branch to deploy: master
- Render root directory: apps/duecare-ai.com
- Domain: duecare-ai.com
- Render service name: duecare-ai-hub
- Render runtime: Docker web service, CPU-only
- Render health check: /api/health
- Persistent disk: /app/.duecare, 1 GB
- Human-readable docs: /docs
- Interactive OpenAPI docs: /api-docs

Product framing:

- Headline: Prevent exploitation. Assist workers. Understand the pattern.
- Core rule: Duecare drafts; the user or trusted caseworker decides. Raw chats and case files stay with workers or tenant deployments unless explicit consent allows a handoff.
- The hub is a coordination plane, not a raw case-management system.
- The hub must never collect raw worker case details, passport numbers, phone numbers, emails, home addresses, or other PII.
- Render does not run Gemma 4 inference. Gemma 4 runs in Kaggle, local Ollama/llama.cpp, HF Spaces, NGO edge boxes, or mobile LiteRT.
- The website demonstrates a public, working infrastructure layer around the Kaggle model demo: anonymized signals, public-source update proposals, knowledge-pack metadata, and curator review.

Current architecture:

- FastAPI application: app/main.py
- Static public dashboard: GET /
- Health checks: GET /api/health and GET /healthz
- Status: GET /api/hub/status
- Knowledge packs: GET /api/hub/knowledge-packs
- Aggregate trends: GET /api/hub/trends
- Anonymized signal intake: POST /api/hub/signals
- Public-source update proposal intake: POST /api/hub/opencrawl/updates
- Curator review feed: GET /api/hub/opencrawl/updates
- File-backed JSONL persistence on the Render disk
- Tests: tests/test_app.py
- Render blueprint: monorepo root render.yaml

Hard safety boundaries:

1. Do not add raw case intake before the hackathon deadline.
2. Do not auto-send emails, complaints, reports, or takedown notices. Draft-only handoff is acceptable; the worker, user, or trusted caseworker sends.
3. Do not add Twilio, WhatsApp, Messenger, SMS, login, Stripe, Sentry, PostHog, or GPU dependencies unless specifically requested and justified for the video.
4. Do not commit API keys, Render tokens, Cloudflare tokens, personal email addresses, or any provider credentials.
5. Do not weaken the PII rejection behavior in POST /api/hub/signals.
6. Do not make the public hub imply it is emergency service, legal counsel, or an official reporting endpoint.

Hackathon priority:

The video is the product. Prioritize visible, reliable, demo-ready changes over large refactors. A good change should improve one of these scenes:

1. A judge opens duecare-ai.com and immediately understands the story.
2. A partner submits an anonymized pattern signal and receives a safe receipt.
3. A crawler proposes a public-source update for curator review.
4. The hub shows knowledge packs and aggregate trends without exposing PII.
5. The page connects the website to the Kaggle Gemma 4 harness, notebooks, writeup, and repository.

Preferred near-term work:

- Improve homepage copy and visual hierarchy around the three-outcome story: prevent exploitation through platform safety, assist workers through NGO/regulator and mobile workflows, and understand patterns through research and shared knowledge.
- Add a clear Deployment Status / Live Demo panel with health, storage mode, privacy mode, and endpoint links.
- Add links to GitHub, Kaggle notebooks, writeup, and API docs once URLs are final.
- Add robots.txt/sitemap consistency if needed.
- Add small smoke tests for every new endpoint or homepage behavior.
- Keep dependencies minimal: FastAPI, Pydantic, Uvicorn, pytest.

Testing requirements:

Before any commit, run:

python -m pytest -q

Also smoke-test locally with:

python -m uvicorn app.main:app --reload

Then check:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/api/health
- http://127.0.0.1:8000/api/hub/status
- http://127.0.0.1:8000/api/hub/knowledge-packs
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/api-docs

If asked about domain setup:

- Create or connect a Render Docker web service from the `master` branch of `TaylorAmarelTech/gemma4_comp`.
- Set Render Root Directory to `apps/duecare-ai.com`.
- Set Dockerfile path to `./Dockerfile` relative to that root directory.
- Add duecare-ai.com and www.duecare-ai.com as custom domains in Render.
- If using Cloudflare DNS, set SSL/TLS mode to Full, add CNAME records for @ and www pointing to the Render onrender.com host, and keep them DNS only until Render verifies TLS.
- Remove AAAA records while configuring Render because Render currently expects IPv4 custom-domain routing.
- After Render certs are issued, Cloudflare proxy can optionally be enabled.

Your response style:

- Be direct and action-oriented.
- Make website changes under `apps/duecare-ai.com` in the main monorepo.
- Treat the main repo as the shared source of truth for the Kaggle/model/notebook work and the public hub/deployment work.
- Flag any change that could create PII, legal, security, or operations risk.
