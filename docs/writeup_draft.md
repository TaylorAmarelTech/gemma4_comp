# DueCare: A Gemma 4 Safety Ecosystem for Migrant-Worker Protection

**Subtitle:** A self-hostable multi-module harness for content moderation, case analysis, worker support, research, and anonymized knowledge sharing.

**Tracks:** Impact — **Safety & Trust** (primary) · Special Technology — **Unsloth** (LoRA fine-tune of Gemma 4) and **LiteRT** (on-device Gemma 4 E2B in the sibling Android app).

**Live deck:** the recording-grade pitch is hosted at `/start` and `/slides` inside the live-demo kernel.

## Try it in 30 seconds

Three Kaggle script kernels. Each is a single `kernel.py`: copy into a fresh Kaggle Notebook → **Accelerator: GPU T4 x2**, **Internet: On** → **+ Add Input → Models → `google/gemma-4`** → **Run All**. The kernel prints a public `https://*.trycloudflare.com` URL in ~30 seconds.

- 🟢 **DueCare App** — [`kaggle.com/code/taylorsamarel/duecare-app`](https://www.kaggle.com/code/taylorsamarel/duecare-app)
- 🎬 **DueCare Live Demo** — [`kaggle.com/code/taylorsamarel/duecare-live-demo`](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)
- 📊 **DueCare Fine-tuning and Evaluation** — [`kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation)

Source: [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp) (MIT). Heuristic-only mode (no model attached) still serves `/start`, `/slides`, the deterministic GREP / RAG / tools paths, and the cached worker-question slot.

## 1. The problem at a scale generic AI is not closing

Twenty-eight million people are in forced labor today; forced labor generates $236 billion in illicit profit a year; 169 million people work outside their country of birth, and migrant workers face roughly three times the forced-labor risk (ILO 2022, 2024). Despite frontier-model progress, this domain has not benefited:

> capability spike ≈ verifiability × training attention × data coverage × economic value

All four factors are weak. A 2024 Kaggle red-team study found frontier LLMs producing plausible-but-wrong answers on migrant-worker prompts: hallucinated statute sections, wrong corridor fees, vague "consult a lawyer" advice, privacy oversharing, and operational uplift when asked to "structure" a fee.

## 2. Why "DueCare": the legal standard we apply to LLMs

Named for **California Civil Code §1714(a)**, the general duty-of-care standard a California jury applied in March 2026 to find Meta and Google negligent for defective platform design. DueCare applies the same standard to language models: does the model exercise *due care* when responding to prompts about trafficking, recruitment fraud, and financial coercion? The substrate makes that question answerable per-request.

## 3. Solution: five lanes, one local substrate

| Lane | What the user does | What DueCare returns |
|---|---|---|
| Content moderation | Review ads, messages, listings | Risk labels, fired indicators, policy-grounded refusal |
| Case analysis | Upload a bounded case bundle | People, payments, dates, typed edges, graph chat |
| Worker information access | Ask a short question (phone) | Plain-language rights, safe next steps, contacts |
| Research and enforcement | Cross-case questions | Clusters, evidence rows, verification checklists |
| Anonymized knowledge sharing | Promote reviewed, redacted facts | Knowledge objects that improve packs everywhere |

**Gemma 4 is the local model runtime underneath every lane — not another lane.** A sibling **Android app** (DueCare Journey v0.9.0) runs Gemma 4 E2B fully on-device via **MediaPipe LiteRT**, with bundled corridor packs and zero cloud calls.

## 4. How Gemma 4's unique features are load-bearing

**Native function calling.** Gemma 4 emits structured function calls the harness routes natively. Tool dispatch (`corridor_fee_cap_lookup(corridor)`, `agency_registry_check(license_id)`, `refund_pathway(...)`, `contact_resolver(corridor)`, `statute_section_validator(citation)`) is structured JSON the model produces, not text we string-parse. The substrate decides which tools to surface based on fired GREP indicators; Gemma decides which to call.

**Multimodal understanding.** Bulk File Review accepts ZIP / PDF / CSV / Office / image bundles. Scanned receipts, ID photos, and handwritten complaint notes enter the local Gemma vision queue and emit typed edges with row citations. The sibling Android app's roadmap puts the same vision path on the phone once MediaPipe LiteRT exposes the kernels.

**Local frontier intelligence.** Gemma 4 E2B fits in a Kaggle T4 at 4-bit quantization (< 3 GB). Raw case files never leave. No per-token spend. Self-hostable on regulator hardware or NGO laptops.

**Fine-tunable.** **Unsloth** LoRA adapters on rubric-polished synthetic data. 60-step smoke runs on Kaggle T4; full runs scale linearly. Checkpoint + resume.

## 5. The substrate — components in detail

**GREP rules (165+).** Deterministic patterns: fee camouflage (training / medical / processing / insurance / deposit), wage assignment, debt novation, restricted provider choice, passport retention, contract substitution, retaliation, corridor-cap violations. Each rule has an id, regex, severity, corridor scope, and unit test.

**Knowledge packs (55+).** Versioned RAG corpus: **ILO C029 / C181 / C189**, **Palermo Protocol**, **POEA MC 14-2017** (PH→HK zero-fee, now DMW policy), **BP2MI Reg 9/2020**, **Nepal FEA 2007 §11(2)**, **HK Cap. 57** + **Cap. 163** + **Cap. 57A**, **SG EFMA Cap. 91A §22A**, **UAE MoHRE Decree 765/2015**, **RA 8042 / RA 10022** (Migrant Workers Act). Retrieved per-prompt, hashed, cited verbatim.

**Persona + context layer + official-source layer.** Audience-aware scaffolding (worker / caseworker / regulator / researcher / platform) and allowlisted public-authority lookups (DMW, ILO, HK Labour).

**Graph extraction.** Bulk File Review extracts typed edges (`worker → paid_fee → recruiter`, `agency → restricts_choice → clinic`) with row citations. Optional local Gemma edge pass adds typed edges from natural-language evidence.

**Privacy gates.** Anonymizer (PII regex + NER + `sha256` audit log), search-safety gate (generalizes outbound queries), post-search verification, k-anonymity on shared knowledge objects.

**Refusal head + substance-over-form.** Compound indicators (worker-paid fee + restricted choice + salary deduction) trigger refusal of operational help; the response surfaces the refund / complaint pathway instead.

**Combined grading.** Rubric (refusal correctness, grounding, evidence preservation, contact accuracy, safe-reporting language, statute-section validity) plus optional LLM judge — with row citations on every dimension.

## 6. Main server architecture

`packages/duecare-llm-server` is the FastAPI runtime. `create_app(state)` mounts the static dirs, attaches the chat package at `/wb-static/`, registers `/start`, `/slides`, `/slides/setup`, `/api/slides/cached-io`, `/api/moderate`, `/api/queue/*`, plus the A-00 control-plane routes. Every harness is a self-contained module under `duecare.chat.harnesses` with a standard contract (`name`, `applied_layers`, `consumes`, `emits`, `register_routes(app)`) — enabling per-task fine-tuning data and per-task evaluation. Three Kaggle script kernels embed this server inside a **Cloudflare** tunnel and print a public `*.trycloudflare.com` URL within ~30 seconds.

## 7. Evidence and observations

`DueCare Fine-tuning and Evaluation` (A-00) facilitates side-by-side benchmarking (base / +harness / fine-tuned / fine-tuned + harness on identical prompts), synthetic SFT generation filtered by the same harness, **Unsloth** LoRA fine-tune with checkpoint and resume, and per-run report export. Any judge can re-run the same four arms.

**A-00 smoke matrix** (2026-05-18T08:51:37Z, `e2b-full-train-eval`, combined rule + LLM judge): stock Gemma 4 2B **29.5%**; stock + chat-offline harness **35.6%** (**+6.1 pp**); fine-tuned **26.4%**; fine-tuned + harness **41.2%** (**+14.8 pp** over fine-tuned; **+11.7 pp** over stock).

- The substrate carries most of the lift over base Gemma 4 — gain is from *grounding*, not raw capability. Frontier models without grounding still cite wrong statutes.
- Fine-tuning alone shifts response *shape* (refusal calibration, contact-language style) but does not import the corridor rule the worker needs.
- Stacking fine-tune + harness compounds: the fine-tune handles refusal style; the substrate handles factual grounding.
- The hardest grading dimensions are statute-section validity and contact accuracy (hotlines are volatile; static training data drifts).

## 8. Design decisions and challenges overcome

- **Local Gemma 4, not a frontier API** — privacy boundary, no per-token spend, judges can re-run for free.
- **GREP + RAG + tools, not all-LLM** — deterministic indicators are inspectable; a regulator can grep the trace.
- **Memory-budget engineering for Kaggle T4** — single-model-at-a-time default; 4-bit quantization throughout.
- **Statutory regression caught during the build** — an earlier cached-IO generator mis-cited *RA 11227* (officer-training law). Replaced with **RA 8042 / RA 10022** and pinned by a contract test.
- **Synthetic, watermarked sample artifacts** — every shipped sample bundle (`/wb-static/samples/`) is safe for any public cloud test environment.
- **Recording-safe pitch deck** embedded in the live-demo kernel (1920×1080 canvas, auto-fit, six client-side demos labelled "cached · replays in ~3s" to be honest about pre-baking).

## 9. Future work

Federated knowledge-object exchange with cryptographic provenance. On-device multimodal once LiteRT exposes Gemma 4 multimodal kernels. More corridor packs (BD, LK, LB, KW, SA, MX→US H-2A/H-2B). Scoring-gated CI for GREP rules and LoRA adapters. Reviewer-feedback loops for misfire-driven rule updates.

## 10. Prior art and attribution

**Models and frameworks:** Gemma 4 (Google DeepMind); Unsloth (LoRA fine-tuning); MediaPipe LiteRT (on-device); llama.cpp (deployment target). **Runtime:** FastAPI, Pydantic v2, Uvicorn, DuckDB, Cloudflare tunnel.

**Standards and circulars:** ILO Forced Labour Indicators and conventions C029 / C181 / C189; Palermo Protocol; POEA / DMW / BP2MI / Nepal DoFE / HK Labour Department circulars; RA 8042 / RA 10022 (Migrant Workers Act); HK Cap. 57 / 163 / 57A; SG EFMA; UAE MoHRE.

**Influences:** Cal. Civ. Code §1714(a) duty-of-care doctrine; 2024 Kaggle red-team study of frontier LLMs on migrant-worker prompts; sister synthetic-evidence harness; partner NGOs Polaris, IJM, ECPAT, POEA, BP2MI, HRD Nepal.

Full per-file attribution in `docs/CREDITS.md`.

## 11. Close

DueCare drafts; the user or trusted caseworker decides. The substrate is built to be forked and reused — by NGOs that need a local copilot, regulators that need traceable evidence, researchers that need a reproducible safety benchmark on open weights, and platform teams that need to catch the recruitment-ad patterns that slip through generic moderation today.
