# DueCare: A Gemma 4 Safety Ecosystem for Migrant-Worker Protection

**Subtitle:** A self-hostable multi-faceted Gemma 4 implementation for content moderation, case analysis, worker support, research, and anonymized knowledge sharing.

## 0. TLDR

Launch the Kaggle interface by running the **DueCare Live Demo** kernel, opening the printed `https://*.trycloudflare.com` URL, and starting at `/start` for the slide demo or `/wb-static/process.html` for Bulk File Review. For the broader workbench, run **DueCare App**. For the evaluation matrix, run **DueCare Fine-tuning and Evaluation**. The companion phone experience can be tested by installing the DueCare Journey APK.

- **DueCare App:** [`kaggle.com/code/taylorsamarel/duecare-app`](https://www.kaggle.com/code/taylorsamarel/duecare-app)
- **DueCare Live Demo:** [`kaggle.com/code/taylorsamarel/duecare-live-demo`](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)
- **DueCare Fine-tuning and Evaluation:** [`kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation)
- **Source:** [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp)

## 1. The problem: migrant-worker exploitation

Migrant-worker exploitation is large, profitable, and often hidden behind paperwork. The ILO estimates 28 million people are in forced labor, forced labor generates $236 billion in illicit profit each year, and 169 million people work outside their country of birth. Migrant workers face roughly three times the forced-labor risk (ILO 2022, 2024).

The patterns are not limited to obvious abuse. They include recruitment-fee camouflage, worker-paid training and medical costs, wage deductions, passport retention, contract substitution, retaliation threats, debt bondage, jurisdiction confusion, and pressure to use a recruiter-controlled training center, clinic, lender, or travel provider.

## 2. Why AI has not helped enough

AI is bringing enormous progress to many industries, but it has not yet meaningfully protected migrant workers. The reason is not simply model size. This domain has weak training coverage, volatile legal facts, fragmented evidence, cross-border rules, and high consequences when advice is wrong.

In early testing, frontier and open models often responded poorly to migrant-worker exploitation prompts. Common failures included poor recall of international standards, wrong corridor-fee rules, confusion about which origin and destination laws apply, vague "consult a lawyer" advice, privacy oversharing, and responses that failed to identify key indicators of human exploitation. When prompted as a business operator, models sometimes provided operational uplift for structuring prohibited fees or salary deductions.

## 3. DueCare overview

DueCare is named for **California Civil Code section 1714(a)**, the duty-of-care standard a California jury applied in March 2026 to find Meta and Google negligent for defective platform design. DueCare applies similar standards of care to language models: does the model exercise due care when responding to prompts about trafficking, recruitment fraud, debt bondage, and financial coercion?

DueCare is an ecosystem of Gemma 4-powered modules across six lanes:

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

To address this, DueCare harnesses Gemma 4 with multiple logic pipelines:

- **GREP:** 165+ deterministic rules for fee camouflage, wage assignment, debt novation, restricted provider choice, document retention, retaliation, contract substitution, and corridor-cap violations.
- **Context:** audience-aware framing for workers, caseworkers, regulators, researchers, platform moderators, and developers.
- **Knowledge packs:** 55+ curated documents covering ILO C029 / C181 / C189, Palermo Protocol, POEA MC 14-2017, BP2MI Reg 9/2020, Nepal FEA 2007 section 11(2), HK Cap. 57 / 163 / 57A, SG EFMA Cap. 91A section 22A, UAE MoHRE Decree 765/2015, and RA 8042 / RA 10022.
- **Tools:** corridor fee-cap lookup, trusted-contact lookup, statute validation, agency/license checks, source verification, and case-graph queries.
- **Privacy gates:** PII detection, redaction, search-safety, consent boundaries, and k-anonymity checks for shared knowledge.
- **Rubric grading:** refusal correctness, legal grounding, evidence preservation, contact quality, retaliation-risk handling, privacy minimization, and statute-section validity.

These techniques significantly improved Gemma 4 outputs across the tested Gemma 4 variants. The improvement was most visible in cases where the model needed to detect substance-over-form exploitation: a "training reimbursement," "voluntary salary assignment," or "third-party service charge" that functionally shifted recruitment costs onto the worker.

## 5. What the demo shows

The live demo follows the same six-lane story as the website and slides.

**Content moderation:** a risky recruitment post moves through GREP, RAG, tools, Gemma 4 generation, and audit grading.

**Case analysis:** Bulk File Review accepts ZIP, PDF, CSV, Office, image, email, and text bundles; extracts people, agencies, employers, payments, dates, locations, document types, journey stages, and typed graph edges; then lets the reviewer ask graph questions.

**Worker support:** the mobile app shows chat-style guidance, offline knowledge pages, evidence journaling, safety planning, multilingual support, local privacy, and case handoff.

**Research:** analysts can investigate repeated agencies, training centers, medical clinics, payment accounts, routes, fees, refund outcomes, and small-claim patterns.

**Anonymized knowledge sharing:** reviewed facts become privacy-safe knowledge objects that can improve future packs.

**Custom API implementations:** external teams can call DueCare through configured endpoints, webhooks, SDK blocks, and audit traces.

## 6. Evaluation

Anecdotally, the harness made Gemma 4 responses much closer to international anti-exploitation standards. To quantify that change, I built the **DueCare Fine-tuning and Evaluation** notebook. It compares four arms on the same prompt set: stock Gemma 4, stock + harness, fine-tuned Gemma 4, and fine-tuned + harness.

The 2026-05-18 smoke matrix (`e2b-full-train-eval`, combined rule + LLM judge) produced:

| Arm | Score |
|---|---:|
| Stock Gemma 4 2B | 29.5% |
| Stock + chat-offline harness | 35.6% |
| Fine-tuned | 26.4% |
| Fine-tuned + harness | 41.2% |

The harness added +6.1 points over stock Gemma 4. The fine-tuned + harness arm added +14.8 points over fine-tuning alone and +11.7 points over stock. The pattern was clear: fine-tuning helped response shape and refusal style, but the harness supplied the facts, citations, tools, privacy boundaries, and forced-labor indicators.

## 7. duecare-ai.com

`duecare-ai.com` is the public hub for the ecosystem. It explains the six lanes, links the Kaggle kernels, hosts the knowledge-pack and use-case story, and provides the broader product surface for information exchange. The long-term role of the hub is to help partners share reviewed, anonymized knowledge objects, propose updates to corridor packs, and keep public-facing guidance synchronized without exposing private case files.

## 8. Future work

Next steps are deeper federated knowledge-object exchange, on-device multimodal when LiteRT exposes the needed Gemma 4 kernels, more corridor packs, scoring-gated CI for GREP rules and LoRA adapters, and reviewer-feedback loops for misfire-driven updates.
