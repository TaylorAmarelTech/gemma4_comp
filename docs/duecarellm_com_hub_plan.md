# duecare-ai.com hub launch plan

> Goal: launch a credible public Duecare hub on Render before the hackathon deadline without destabilizing the Kaggle notebook showcase.

## 1. Thesis

A live `duecare-ai.com` hub can materially improve the prize story because it turns Duecare from a notebook demo into infrastructure:

- Kaggle shows the **model and harness**.
- `duecare-ai.com` shows the **network and update layer**.
- The public repo shows the **engineering depth**.

The hub should prove one message:

> Duecare can collect anonymized safety intelligence, update verified knowledge packs, evaluate models, tune Gemma 4, and deploy NGO/government chatbots without centralizing raw worker data.

## 2. What to build now

Build a lightweight Render service, not a GPU server.

The Render hub should run:

- FastAPI;
- static landing page;
- OpenAPI docs;
- anonymized-signal intake;
- public-source update proposal intake;
- knowledge-pack registry;
- aggregate trend counters;
- links to Kaggle, GitHub, HF Hub, docs, and the live chat demo.

It should not run:

- Gemma 4 local inference;
- Unsloth training;
- raw case storage;
- automated complaint sending;
- production Messenger/WhatsApp credentials.

## 3. Current scaffold

The current hub scaffold is now in:

- [apps/duecare-ai.com/app/main.py](../apps/duecare-ai.com/app/main.py)
- [apps/duecare-ai.com/app/templates/](../apps/duecare-ai.com/app/templates/)
- [apps/duecare-ai.com/tests/test_app.py](../apps/duecare-ai.com/tests/test_app.py)
- [render.yaml](../render.yaml)
- [apps/duecare-ai.com/docs/RENDER.md](../apps/duecare-ai.com/docs/RENDER.md)

## 4. Demo flow for the video

Use a 12-second clip:

1. Open `duecare-ai.com`.
2. Show the headline: **Prevent exploitation. Assist workers. Understand the pattern.**
3. Open `/docs` and show endpoints:
   - `/api/hub/signals`
   - `/api/hub/opencrawl/updates`
   - `/api/hub/knowledge-packs`
4. Submit a synthetic anonymized signal.
5. Show aggregate trends update.
6. Cut back to Kaggle chat and say the same knowledge packs ground the live Gemma 4 assistant.

Voiceover line:

> The notebook is not a toy. Duecare also has a public hub where partners can contribute anonymized patterns, public-source updates, prompts, and evaluations. Raw worker chats stay on the phone or tenant hardware unless a worker or partner explicitly shares a safe object.

## 5. Public-source crawler communication pattern

The crawler/update agent should never mutate production directly.

```text
Public-source crawler
  → fetch public source
  → hash content
  → summarize public change
  → POST /api/hub/opencrawl/updates
  → status = proposed
  → curator reviews
  → vetted knowledge-pack diff
  → eval gate
  → release
```

Public-source update payload:

```json
{
  "source_name": "Demo public regulator page",
  "source_url": "https://example.org/public-labor-update",
  "proposed_pack_kind": "contacts",
  "jurisdiction": "Demo",
  "change_summary": "Public-source crawler observed that a regulator complaint page changed its service hours and should be reviewed by a curator.",
  "extracted_public_facts": ["Service hours changed on the public page."],
  "content_hash": "abc123demo",
  "crawler_version": "public-source-demo-v0"
}
```

## 6. Anonymized signal pattern

Partners should send patterns, not people.

```text
NGO / regulator / platform / mobile app
  → local anonymizer
  → aggregate or synthetic-safe summary
  → hashes instead of raw evidence
  → POST /api/hub/signals
  → hub updates trend counters
  → candidate prompt/eval/RAG updates
```

Accepted signal payload:

```json
{
  "source": "synthetic_demo",
  "jurisdiction": "Philippines",
  "corridor": "Philippines to Hong Kong",
  "language": "English",
  "risk_tags": ["illegal_fee", "document_retention"],
  "summary": "Synthetic aggregate pattern: multiple recruitment messages promise placement, then mention large processing fees and document retention before travel.",
  "evidence_hashes": ["sha256:demo-pattern-001"],
  "consent_basis": "synthetic_demo",
  "pack_version": "demo"
}
```

Rejected signal examples:

- raw phone numbers;
- emails;
- passport or visa identifiers;
- home addresses;
- free-text copied from a real case.

## 7. Hub sections to add after scaffold

### P0 — before deadline if time allows

| Feature | Why | Effort |
|---|---|---|
| Landing page links to Kaggle/GitHub/HF/writeup | judges see the full ecosystem | 30 min |
| Synthetic signal submit form | visible hub demo | 1 hr |
| Trend cards on homepage | visual proof of aggregate intelligence | 1 hr |
| Knowledge-pack cards | shows RAG/GREP/contacts/rubrics as products | 1 hr |
| Public-source update demo form | proves continuous update loop | 1 hr |
| Domain DNS + HTTPS | makes it real | 30-60 min plus DNS propagation |

### P1 — useful after deadline or if ahead

| Feature | Why | Effort |
|---|---|---|
| SQLite persistence | survive restarts | half-day |
| Admin review queue | curator workflow | 1 day |
| Vetted pack manifest endpoint | real Exchange foundation | 1 day |
| Contact freshness checker integration | real Sentinel foundation | half-day |
| Basic auth for partner submission | avoid public spam | half-day |
| Rate limiting | public safety | half-day |

### P2 — post-hackathon

| Feature | Why | Effort |
|---|---|---|
| Multi-tenant partner accounts | NGO/government deployments | multi-day |
| Messenger/WhatsApp production webhooks | Duecare Channels | multi-day |
| Training job orchestration | Duecare Trainer | multi-day |
| Vetted knowledge-pack marketplace | Duecare Exchange | multi-week |
| Full caseworker dashboard | NGO workflow | multi-week |

## 8. DNS and Render checklist

1. Buy/configure `duecare-ai.com`.
2. Create Render web service from the repo.
3. Use Dockerfile path `deployment/render/Dockerfile`.
4. Add custom domains:
  - `duecare-ai.com`
  - `www.duecare-ai.com`
5. Add Render-provided DNS records at the registrar.
6. Wait for HTTPS certificate.
7. Verify:
  - `https://duecare-ai.com/healthz`
  - `https://duecare-ai.com/api/hub/status`
  - `https://duecare-ai.com/docs`
8. Record 10-15 seconds for the video.

## 9. Risk controls

| Risk | Control |
|---|---|
| Someone submits raw PII | reject obvious PII; add auth/rate limits next |
| Judges think hub stores real cases | homepage says anonymized only; docs repeat it |
| Render CPU cannot run model | do not run model on Render; link to Kaggle/HF/local runtime |
| Hub appears fake | expose live OpenAPI endpoints and accept synthetic demo payloads |
| Scope creep | hub is coordination plane, not full production backend |
| Public-source updates corrupt data | proposal-only, curator approval required |

## 10. Prize framing

The 50K story should be:

1. **Impact:** migrant-worker protection needs shared safety infrastructure, not another chatbot.
2. **Demo:** Kaggle shows Gemma 4 + harness; `duecare-ai.com` shows the coordination hub.
3. **Technical depth:** local model runtime, deterministic harness, multimodal evidence, function calling, anonymized signal exchange, update agents, evaluation manifests, and training adapters form one system.

One-line video framing:

> Duecare is not just a notebook. It is safety infrastructure: local Gemma 4 where sensitive data lives, and a public hub where only anonymized patterns, verified knowledge packs, prompts, and evaluations flow back.
