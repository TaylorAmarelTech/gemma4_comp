# DueCare: A Gemma 4 Safety Ecosystem for Migrant-Worker Protection

**Subtitle:** A self-hostable multi-faceted Gemma 4 implementation for content moderation, case analysis, worker support, research, and anonymized knowledge sharing.

**Tracks:** Impact - **Safety & Trust** (primary); Special Technology - **Unsloth** for Gemma 4 LoRA fine-tuning and **LiteRT** through the DueCare Journey Android app.

## 0. Quick Start

Launch the demo interfaces by forking the notebooks below into your Kaggle account. Click **Save and Run**, watch the logs until a `https://*.trycloudflare.com` URL appears, then open that URL in your browser.

- **Main workbench:** [`kaggle.com/code/taylorsamarel/duecare-app`](https://www.kaggle.com/code/taylorsamarel/duecare-app)
- **Focused live demo / slides:** [`kaggle.com/code/taylorsamarel/duecare-live-demo`](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)
- **Evaluation and benchmark:** [`kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation)
- **Android APK:** [`github.com/TaylorAmarelTech/duecare-journey-android/releases`](https://github.com/TaylorAmarelTech/duecare-journey-android/releases)
- **Source:** [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp)

Inside the main workbench, `/static/demo-recording.html` provides the recording checklist, lane order, bundled sample artifacts, and cached replay trace for the platform-moderation example.

Kernel split for recording: `duecare-app` is the operational workbench (`/static/chat.html`, `/static/process.html`, `/static/knowledge.html`, `/static/search.html`, `/static/share.html`, and `/static/demo-recording.html`); `duecare-live-demo` is the focused walkthrough and slide deck (`/start`, `/slides`, `/slides/setup`, and `/api/slides/recording-pack`); `duecare-fine-tuning-and-evaluation` is the benchmark/evaluation notebook.

## 1. The problem: migrant-worker exploitation

Migrant-worker exploitation is large, profitable, and often hidden behind paperwork. The ILO estimates 28 million people are in forced labor, forced labor generates $236 billion in illicit profit each year, and 169 million people work outside their country of birth. Migrant workers face roughly three times the forced-labor risk (ILO 2022, 2024).

The patterns are not limited to obvious abuse. They include recruitment-fee camouflage, worker-paid training and medical costs, wage deductions, passport retention, contract substitution, retaliation threats, debt bondage, jurisdiction confusion, pressure to use a recruiter-controlled training center, clinic, lender, or travel provider, and other evolving modus operandi.

## 2. Why AI has not helped enough

AI is bringing enormous progress to many industries, but it has not yet meaningfully protected migrant workers. The reason is not simply model size. This domain has weak training coverage, volatile legal facts, fragmented evidence, complex cross-jurisdiction rules, and high consequences when advice is wrong.

In early testing, frontier and open models often responded poorly to migrant-worker exploitation prompts. Common failures included poor recall of international standards, wrong corridor-fee rules, confusion about which international standards and which origin- or destination-country laws apply, vague "consult a lawyer" advice, privacy oversharing, and responses that failed to identify key indicators of human exploitation. When prompted as a business operator, models sometimes provided operational uplift for structuring prohibited fees or salary deductions.

## 3. DueCare overview

DueCare is named for **California Civil Code section 1714(a)**, the same duty-of-care standard a California jury applied in March 2026 to find Meta and Google negligent for defective platform design. The goal of DueCare is to create an effective ecosystem of tools that enterprises, civil-society organizations, regulators, and migrant workers themselves can deploy to combat migrant-worker exploitation.

The DueCare ecosystem consists of the following Gemma 4-powered modules:

| Lane | What it facilitates |
|---|---|
| Content moderation via Gemma 4 | Review recruitment ads, messages, listings, and platform posts for exploitation risk. |
| Case analysis via Gemma 4 | Turn bounded case bundles into people, payments, dates, typed edges, timelines, and graph chat. |
| Worker support via Gemma 4 | Provide plain-language rights guidance, offline knowledge pages, evidence journaling, safety planning, and trusted contacts. |
| Research via Gemma 4 | Find repeated agencies, accounts, routes, fee patterns, refund outcomes, and evidence gaps across anonymized cases. |
| Anonymized knowledge sharing via Gemma 4 | Convert reviewed, redacted facts into reusable knowledge objects without exposing workers. |
| Custom API implementations | Embed the same safety harness into platforms, NGO tools, regulator portals, hotline workflows, or case-management systems. |

## 4. Gemma 4 application

Gemma 4 is one of the newest and most capable open-weight model families, but early testing showed that plain Gemma 4 still suffered from the same domain failures as prior models: weak recall of international standards, weak detection of illicit fee camouflage, confusion over cross-border jurisdiction, and incomplete recognition of human-exploitation indicators.

To address this, DueCare wraps Gemma 4 in model harnesses and logic pipelines:

- **GREP:** 269 deterministic rules covering fee camouflage, debt novation, document retention, contract substitution, child + organ + sex trafficking, forced marriage, gig-platform exploitation, seasonal-visa abuse, refugee leverage, and AI-deepfake recruitment fraud.
- **Context:** 22 audience-aware personas (worker, NGO, regulator, clinician, survivor advocate, FIU, engineer).
- **Knowledge packs:** 191 documents — 15 ILO conventions, Palermo, regional treaties (EU 2011/36, ASEAN ACTIP, SAARC, Bali Process), 26 destination + origin statutes (POEA MC 14-2017, BP2MI 9/2020, FEA 2007, HK 57/57A, UAE 33/2021, Saudi RD M/51, Qatar 15/2017, TVPRA + UFLPA, UK MSA, EU CSDDD), 6 screening tools (HEAL, TVIT, AHTST, CSE-IT, QYIT, NRM), 15 case studies.
- **Templates:** 34 pre-filled complaint + narrative templates — citations + procedural language baked in; only worker-specific blanks remain.
- **Tools:** corridor fee-cap lookup, trusted-contact lookup, statute validation, agency/license checks, source verification, and case-graph queries.
- **Sensitive-data handling:** raw worker chats, case files, IDs, contact details, and private documents stay on the worker device or trusted NGO hardware unless an authorized user creates a sanitized submission. Local Gemma 4 and deterministic detectors anonymize sensitive PII before anything reaches the hub; the server runs a second PII detector before storage.
- **Rubric grading:** refusal correctness, legal grounding, evidence preservation, contact quality, retaliation-risk handling, privacy minimization, and statute-section validity.

These techniques significantly improved Gemma 4 outputs across the tested Gemma 4 variants. The improvement was most visible in cases where the model needed to detect substance-over-form exploitation: a "training reimbursement," "voluntary salary assignment," or "third-party service charge" that functionally shifted recruitment costs onto the worker.

## 5. What the demo shows

The live demo follows the same six-lane story as the website and slides.

**Content moderation:** a risky recruitment post moves through GREP, RAG, tools, Gemma 4 generation, and audit grading.

**Case analysis:** Bulk File Review accepts ZIP, PDF, CSV, Office, image, email, and text bundles; deterministically extracts people, agencies, employers, payments, dates, locations, document types, journey stages, and typed graph edges from parsable text and metadata; queues OCR/media review explicitly; and can run optional Gemma case-brief and edge-generation passes when a compatible model is loaded.

**Worker support:** the mobile app shows chat-style guidance, offline knowledge pages, evidence journaling, safety planning, multilingual support, local privacy, and case handoff.

**Research:** analysts can investigate repeated agencies, training centers, medical clinics, payment accounts, routes, fees, refund outcomes, and small-claim patterns.

**Anonymized knowledge sharing:** reviewed facts become privacy-safe knowledge objects that can improve future packs.

**Custom API implementations:** external teams can call DueCare through configured endpoints, webhooks, SDK blocks, and audit traces.

## 6. Evaluation

Anecdotally, the harness made Gemma 4 responses much closer to international anti-exploitation standards. To quantify that change, I built the **DueCare Fine-tuning and Evaluation** notebook. It compares four arms on the same prompt set: stock Gemma 4, stock + harness, fine-tuned Gemma 4, and fine-tuned + harness.

The 2026-05-18 smoke matrix (`e2b-full-train-eval`, combined rule + LLM judge) produced the following scores. This is a smoke run, not a final benchmark; the reproducibility artifacts are the A-00 report, CSV, JSON, and manifest bundle exported under `/kaggle/working`.

| Arm | Score |
|---|---:|
| Stock Gemma 4 2B | 29.5% |
| Stock + chat-offline harness | 35.6% |
| Fine-tuned | 26.4% |
| Fine-tuned + harness | 41.2% |

The harness added +6.1 points over stock Gemma 4. The fine-tuned + harness arm added +14.8 points over fine-tuning alone and +11.7 points over stock. The pattern was clear: fine-tuning helped response shape and refusal style, but the harness supplied the facts, citations, tools, data-minimization checks, and forced-labor indicators.

## 7. duecare-ai.com

`duecare-ai.com` is the public hub for the ecosystem. It explains the six lanes, links the Kaggle kernels, hosts the knowledge-pack and use-case story, and provides the broader product surface for information exchange. The long-term role of the hub is to help partners share reviewed, anonymized knowledge objects, propose updates to corridor packs, and keep public-facing guidance synchronized without exposing private case files. Submissions can be anonymous, pseudonymous, organization-tagged, verified-organization-tagged, region-tagged, corridor-tagged, or aggregate-only depending on consent; automatic labels can suggest metadata, but cannot silently upgrade an anonymous submission into an attributed one.

## 8. Attribution and scope

Models and frameworks include Gemma 4, Unsloth, MediaPipe LiteRT, FastAPI, Pydantic, Uvicorn, DuckDB, and Cloudflare quick tunnels. Legal and policy sources include ILO conventions and forced-labour indicators, Palermo Protocol, POEA/DMW, BP2MI, Nepal DoFE, Hong Kong Labour Department, Singapore EFMA, UAE MoHRE, and RA 8042 / RA 10022. Prior art includes my 2025 Kaggle red-teaming research on LLM complicity in modern slavery. Full per-file attribution is in `docs/CREDITS.md`.

DueCare drafts; the user or trusted caseworker decides. The system does not replace human caseworkers, does not auto-report, and does not bundle real worker case data.

## 9. Future work

Next steps are deeper federated knowledge-object exchange, on-device multimodal when LiteRT exposes the needed Gemma 4 kernels, more corridor packs, scoring-gated CI for GREP rules and LoRA adapters, and reviewer-feedback loops for misfire-driven updates.
