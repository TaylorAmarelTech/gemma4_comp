# Duecare platform — eight components

| # | Component | Status | Purpose |
|---|---|---|---|
| 1 | [`duecare_runtime.md`](duecare_runtime.md) | **Live** | Gemma 4 model layer — local + cloud inference, model selection, output sanitizer |
| 2 | [`duecare_harness.md`](duecare_harness.md) | **Live (the Kaggle submission)** | Safety + grounding + audit trace — GREP, RAG, tools, contacts, response policy |
| 3 | [`duecare_exchange.md`](duecare_exchange.md) | **Hub scaffolded** | Privacy-preserving vetted-pack distribution between partners — public hub at [duecare-ai.com](https://duecare-ai.com) (`apps/duecare-ai.com/`) scaffolds signal intake + knowledge-pack metadata; vetted-pack format is roadmap |
| 4 | [`duecare_eval.md`](duecare_eval.md) | **Partial** | Rubrics + benchmarks + regression gate (multi-dimension rubric + adversarial suite built; CI gate post-hackathon) |
| 5 | [`duecare_trainer.md`](duecare_trainer.md) | **Prototype (A-00)** | Model adaptation / retraining via A-00 synthetic rows, Unsloth LoRA smoke training, checkpoint/resume, adapter save/load, and report exports |
| 6 | [`duecare_sentinel.md`](duecare_sentinel.md) | **Hub scaffolded** | Continuous-update agent + server with mandatory human-in-the-loop — proposal-intake endpoint live at `duecare-ai.com/api/hub/opencrawl/updates`; autonomous crawler is roadmap |
| 7 | [`duecare_channels.md`](duecare_channels.md) | Roadmap | NGO / government chatbot integrations — Messenger / WhatsApp / SMS / web / embassy portal |
| 8 | [`duecare_mobile.md`](duecare_mobile.md) | **Live (sibling repo)** | Worker-facing private checker — Duecare Journey v0.9.0 Android app |

Canonical product definition: [`../product_definition.md`](../product_definition.md).

**Live core (the Kaggle submission):** Gemma 4 Model Layer + Safety Guidance Layer + Quality Testing Framework (partial) + the deterministic Contacts directory. Live demo runs without the Fine-Tuning Module, Channel and Deployment Package, Public Information Research Monitor, or Central Knowledge Server present — those are non-load-bearing for the hackathon submission.

**Hub-scaffolded (the platform-infrastructure surface):** The public hub at [duecare-ai.com](https://duecare-ai.com) — code at [`apps/duecare-ai.com/`](../../apps/duecare-ai.com/) — exposes the *shape* of Exchange (signal + knowledge-pack endpoints) and the Public Information Research Monitor (public-source proposal-intake endpoint) without the autonomous crawler or vetted-pack format behind them yet. It is the platform-infrastructure verification path that complements the Kaggle technical-depth verification path.

## What's currently built (the Kaggle submission)

- **Runtime** (component #1, **Live**) — Gemma 4 model selector across local and cloud/BYOK targets, with output sanitizer regression coverage (`packages/duecare-llm-chat/src/duecare/chat/_model_output.py`).
- **Harness** (component #2, **Live**) — 100+ GREP rules, 50+ document RAG, function-calling tools, contacts, audit trace via `▸ View pipeline` modal, and dedicated viewer pages.
- **Eval** (component #4, **Partial**) — multi-dimension universal rubric + adversarial suite + LLM-judge mode + Combined mode; CI regression gate is post-hackathon.
- **Trainer** (component #5, **Prototype / A-00**) — Unsloth SFT smoke training, checkpoint/resume, adapter save/load, and final comparison reports live in `kaggle/A-00-omni-experiment-workbench/`; full multi-tenant Trainer service is post-hackathon.
- **Mobile** (component #8, **Live**, sibling repo) — Duecare Journey v0.9.0 with MediaPipe LiteRT on-device Gemma 4 E2B, ILO indicator packs, and corridor packs. APK at [`duecare-journey-android`](https://github.com/TaylorAmarelTech/duecare-journey-android/releases).

## What's hub-scaffolded (live but not full Exchange / Sentinel yet)

- **Exchange** (component #3, **Hub scaffolded**) — the public hub
  at [`apps/duecare-ai.com/`](../../apps/duecare-ai.com/) deploys
  to [duecare-ai.com](https://duecare-ai.com) via the repo-root
  `render.yaml`. It exposes `POST /api/hub/signals` (anonymized
  pattern-signal intake with a raw-PII rejector),
  `GET /api/hub/knowledge-packs` (knowledge-pack metadata listing),
  `GET /api/hub/trends` (aggregate counters), and
  `GET /api/hub/status`. Knowledge updates today still land via
  curator-block PRs in `harness/_*.json` reviewed by humans.
  **Roadmap:** Sigstore / cosign vetted-pack format + partner-
  discoverable index hosted on the hub.
- **Public Information Research Monitor** (component #6, **Hub scaffolded**) — the
  proposal-intake shape lives at `POST /api/hub/opencrawl/updates`
  on the hub for public-source crawler-style
  proposals. Today, contact freshness is checked manually
  (`scripts/v141_validate_contacts.py`). **Roadmap:** the
  autonomous crawler that *fills* the proposal endpoint with
  continuously-discovered candidates, plus the automated-
  validation pipeline.

## What's roadmap

- **Channels** (component #7) — NGO / government chatbot integrations on Messenger / WhatsApp / SMS / web / embassy portal. Today, the chat package's FastAPI surface is the integration surface Channels would wrap with platform-specific adapters. Live Channels deployment requires a named NGO tenant + business-account approval + Eval-gated tenant pack — not done at hackathon time.

## How the six canonical lanes map to the components

| Component | Platform safety | NGO & regulator | Individual worker / mobile | Researcher | Anonymized knowledge sharing | Developer / integration partner |
|---|---|---|---|---|---|---|
| Runtime | classify / explain posts | summarize cases | private explanations | compare models | sanitize candidate facts | embed model service |
| Harness | moderation risk trace | intake triage | warning signs | inspectable pipeline | knowledge-object review flow | reusable API layer |
| Exchange | share anonymized abuse patterns | submit field signals | receive updated packs | publish domain packs | primary lane | integrate safe submissions |
| Eval | policy QA / model QA | quality control | hidden safety guard | primary tool | PII and provenance gate | regression gate |
| Trainer | moderation adapter | agency-specific adapter | smaller local model | tuned model studies | approved sanitized examples only | BYO adapter path |
| Research monitor | track new scam patterns | update laws / contacts | keeps app current | benchmark updates | candidate source context | public-source proposal API |
| Channels | platform notices | primary deployment | Messenger / WhatsApp help | study artifact | reviewer submission surface | integration target |
| Mobile | not primary | referral companion | primary worker-owned app | deployment study | opt-in aggregate signals | app integration pattern |

## Critical separation-of-concerns rules

1. **Models do not own truth.** Gemma generates and reasons; it does not invent laws, contacts, or policy.
2. **The update agent proposes; humans approve.** The research monitor never silently mutates production safety behavior.
3. **Raw cases stay local.** Exchange shares anonymized signals, not raw worker narratives.
4. **Contacts are deterministic.** Contacts come from verified data, not model output.
5. **Evaluation gates every update.** New rules / docs / rubrics run through regression tests before release.
6. **Mobile app consumes vetted packs.** The app pulls versioned, offline-compatible safety packs.
7. **Training data teaches structure, tools supply volatile facts.** Small-model SFT/DPO should reinforce safe response shape, citation discipline, privacy boundaries, and forced-labour indicators. Phone numbers, addresses, current advisories, fee caps, wage rules, and fresh statutes should come from tools or versioned packs.
