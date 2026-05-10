# Kaggle Writeup — DueCare

> **Title:** DueCare — Gemma 4 safety infrastructure for migrant-worker protection
>
> **Track:** Safety & Trust. Special Technology alignment: Gemma 4, Unsloth, llama.cpp / LiteRT deployment path.
>
> **One-line claim:** DueCare turns Gemma 4 into grounded safety infrastructure that helps platforms prevent exploitation, helps NGOs and workers act on safer guidance, and helps researchers understand what is happening and why — while keeping raw cases out of the public hub.
>
> **Status as of 2026-05-08:** 6 harness layers, 161 GREP rules, 46-doc RAG corpus, 46-edge citation graph, 46-dimension grader, 587 example prompts, 65-test adversarial validation suite, 49 public-live Kaggle notebooks, 77 tracked notebook kernels, 23 public-hub tests, 4 example knowledge packs, token-gated admin logs, server automation, operator-side local KB, Cloudflare demo app styling aligned to the public website.
>
> **Word count:** checked by `scripts/v141_word_count.py`; counted body remains under Kaggle's 1,500-word cap.

---

## TL;DR

Stock LLMs can miss coercion when abuse is hidden in ordinary recruitment language: salary deductions, document control, fee labels, contract substitution, or jurisdiction hopping. DueCare wraps Gemma 4 with deterministic rules, retrieval, function calls, multimodal inspection, and a scored evaluation harness. It does not replace an NGO caseworker or regulator. It gives them a private local assistant, reproducible evidence, and a public coordination layer that stores only anonymized signals and vetted knowledge packs.

## 1. Problem

Migrant workers often ask for help with messages, contracts, receipts, or recruitment ads that may contain exploitation indicators. The hard part is not only answering the question. It is answering safely, citing the right corridor law, avoiding victim-blaming, refusing to optimize recruiter abuse, and preserving a useful evidence trail.

The common cloud-LLM workflow breaks the trust model. NGOs, labour ministries, and worker advocates may hold case files with names, contact details, identity documents, employer information, medical records, and retaliation risks. Sending those to a frontier API is often unacceptable. DueCare is built around that constraint: worker-side and NGO-side analysis runs locally; the public hub only receives public-source updates, vetted pack metadata, and anonymized aggregate signals.

## 2. What DueCare does

DueCare has two product surfaces.

**The local runtime** is the Gemma 4 harness. A worker, moderator, researcher, or caseworker can paste a suspicious post or document into a Cloudflare-served Kaggle app, local laptop app, or future mobile build. Six optional layers can be toggled per prompt:

- **Persona:** anti-trafficking expert instructions.
- **GREP:** 161 deterministic rules for debt bondage, document retention, fee camouflage, ILO indicators, corridor caps, kafala signals, and legal-citation cues.
- **RAG:** retrieval over a 46-document public legal and NGO corpus with a 46-edge citation graph.
- **Imports:** user-provided local evidence, kept in-session.
- **Tools:** native function calls for corridor fee caps, fee labels, ILO indicators, NGO intake contacts, and convention lookup.
- **Online:** optional web search treated as candidate evidence, not ground truth.

Each response can be scored by deterministic rules, Gemma-as-judge, or a combined mode across 46 safety dimensions. The point is visible technical depth: users can see which rule fired, which document was retrieved, which tool returned a value, and how the score changed when layers are toggled.

**The public hub** is the coordination layer at duecare-ai.com. It serves a schema-backed knowledge-object hierarchy, a real pack registry with four example packs, public pack APIs, server-side automation for public-source update triage, a reference `hub_client.py`, and token-gated redacted admin logs. Legacy OpenClaw aliases remain as redirects and env-var fallbacks, but the public language is now server automation. Render deployment uses one FastAPI Docker service plus a persistent disk; raw worker case content stays in worker-controlled or tenant-controlled deployments.

## 3. Why Gemma 4 matters

Gemma 4's features are load-bearing, not decorative.

**Native function calling** powers the Tools layer. Instead of hoping the model remembers a fee cap or hotline, the harness calls a typed lookup and injects the result into the answer and trace.

**Multimodal understanding** powers document and screenshot workflows. The demo accepts recruitment flyers, contract images, and evidence screenshots, then routes findings through the same rubric and safety trace as text.

**Local deployment** is the impact story. The same architecture can run through Kaggle, a laptop, llama.cpp/GGUF, or LiteRT-style mobile packaging. The worker or NGO keeps sensitive material on-device while still benefiting from Gemma 4 reasoning and grounded public knowledge.

## 4. Evidence and notebooks

The notebook suite is intentionally broad because judges can verify different claims without trusting a video. There are 77 tracked Kaggle kernels and 49 public-live notebooks in the current guide. The priority path is:

1. **000 / 005 / 010:** index, glossary, and five-minute package smoke test.
2. **100 / 102 / 140:** stock Gemma baselines and evaluation mechanics.
3. **200-270:** cross-domain proof and model comparisons.
4. **300-460:** adversarial resistance, function calling, multimodal, judge grading, conversation testing, rubric generation, citation verification.
5. **520 / 525 / 527 / 530 / 540:** fine-tuning curriculum, uncensored five-grade response generation, rubric generation, Unsloth LoRA training, and fine-tune delta visualization.
6. **600 / 610 / 620 / 650:** results dashboard, submission walkthrough, API endpoint tour, and custom-domain adoption.

The fine-tuning story is explicit: supervised fine-tuning uses curated public, synthetic, composite, or anonymized data; raw worker chats and raw case files are excluded. Preference optimization is framed as DPO-style response ranking, not vague reinforcement learning. Every headline number should be reproducible from a git SHA, dataset version, and notebook artifact.

## 5. What is live now

- **Code:** MIT monorepo with Python packages, FastAPI apps, notebook builders, tests, and generated inventory docs.
- **Public hub:** health, status, pack registry, anonymized signal intake, public-source update proposals, client submission / retract endpoints, local-KB API, admin redaction, robots and sitemap.
- **Notebook apps:** primary chat, classifier, live demo dashboard, content classification playground, and knowledge-builder playground now share the DueCare website's fonts, brand mark, focus states, card language, and civic-teal controls while preserving dark operator workspaces where useful.
- **Tests:** hub routes, pack registry, admin redaction, PII rejection, notebook inventory, guide generation, and chat smoke tests are covered.

## 6. Impact

DueCare is not a chatbot for replacing experts. It is infrastructure for exercising due care: help a worker understand risk, help a caseworker document facts, help a platform screen recruitment posts, help a regulator audit patterns, and help researchers compare model behavior. The named downstream institutions are real — Polaris, IJM, ECPAT, POEA / DMW, BP2MI, HRD Nepal — but the demo characters and examples are composites.

If DueCare works, a small NGO can run a private safety evaluator on a laptop, a platform can hold risky recruitment content for review before workers see it, and a worker can ask for guidance without uploading their case to someone else's server.

## 7. Going deeper

[notebook guide](notebook_guide.md) · [for judges](FOR_JUDGES.md) · [architecture](architecture.md) · [deployment modes](deployment_modes.md) · [fine-tuning data strategy](finetuning_data_strategy.md) · [demo recording runbook](demo_recording_runbook.md) · [Render deployment](../apps/duecare-ai.com/docs/RENDER.md)
