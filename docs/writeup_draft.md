# DueCare AI — AI infrastructure to combat migrant-worker exploitation

**Track:** Safety & Trust (primary). Special Technology eligibility: Unsloth (LoRA fine-tuning) and llama.cpp / LiteRT (local Gemma 4 deployment).

**Live deck:** the recording-grade pitch lives at `/start` and `/slides` inside the live-demo kernel (see *How to run on Kaggle* below). The slides also work offline.

## Try it in 30 seconds

Three Kaggle script kernels. Each is a single `kernel.py`: copy into a fresh Kaggle Notebook → **Accelerator: GPU T4 x2**, **Internet: On** → **+ Add Input → Models → `google/gemma-4`** → **Run All**. The kernel prints a public `https://*.trycloudflare.com` URL in ~30 seconds.

- 🟢 **DueCare App** — [`kaggle.com/code/taylorsamarel/duecare-app`](https://www.kaggle.com/code/taylorsamarel/duecare-app) — broad reviewer workbench.
- 🎬 **DueCare Live Demo** — [`kaggle.com/code/taylorsamarel/duecare-live-demo`](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) — focused demo + 21-slide pitch deck at `/start` and `/slides`.
- 📊 **DueCare Fine-tuning and Evaluation** — [`kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation) — four-arm benchmark + LoRA fine-tune + combined judging + exported report bundle.

Source: [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp) (MIT). Heuristic-only mode (no model) still serves `/start`, `/slides`, the deterministic GREP / RAG / tools paths, and the cached worker-question slot.

## 1. The problem at a scale generic AI is not closing

Twenty-eight million people are in forced labor today. Forced labor generates $236 billion in illicit profit a year. One hundred and sixty-nine million people work outside their country of birth, and migrant workers face roughly three times the forced-labor risk of non-migrants (ILO Global Estimates 2022; Profits and Poverty 2024; Migration Statistics 2024).

Despite frontier-model progress, this domain has not benefited. Migrant-worker safety sits at the intersection of fragmented labour law, corridor-specific recruitment patterns, scarce public training data, and low commercial pressure on model providers. A useful rule of thumb is

> capability spike ≈ verifiability × training attention × data coverage × economic value

All four factors are weak here, and the result shows up in evaluations: a 2024 Kaggle red-team write-up across leading open and closed models found that generic LLMs routinely give plausible-sounding answers that are wrong in load-bearing ways for migrant workers — wrong fees, wrong corridor rules, wrong remedies, missing privacy guidance. ([prior work, Kaggle 2024](https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/llm-complicity-in-modern-slavery-from-native-blind))

The people most exposed get the least help, and the harm compounds: an overcharged worker takes on debt, a retained passport blocks departure, a retaliation threat silences a complaint.

## 2. DueCare in one sentence

DueCare is a Gemma 4 harness ecosystem: five user-facing workflow lanes on top of one shared local substrate, designed so platforms, NGOs, regulators, individual workers, and researchers can all benefit from the same inspectable safety primitives. **Gemma 4 is not another lane — it is the local model runtime underneath every lane.**

## 3. The five lanes

| Lane | What the user does | What DueCare returns |
|---|---|---|
| Content moderation | Review ads, messages, listings, harmful compliance requests. | Risk labels, fired indicators, policy-grounded refusal or escalation notes. |
| Case analysis | Upload a bounded case bundle and confirm extracted facts. | People, payments, dates, typed edges, graph chat, complaint drafts. |
| Worker information access | Ask a short question in a phone-first local interface. | Plain-language rights, safe next steps, evidence preservation, contacts. |
| Research and enforcement | Ask cross-case questions across reviewed evidence. | Clusters, evidence rows, uncertainty notes, verification checklists. |
| Anonymized sharing | Promote reviewed, redacted facts after a privacy gate. | Knowledge objects that improve packs without uploading raw files. |

The five lanes share one substrate: local Gemma 4 runtime, deterministic GREP, RAG packs, specialized tools (fee-cap lookup, agency registry, refund pathway), graph extractors, review gates, audit traces, and combined rule + LLM rubric grading. A confirmed fact in one lane becomes a sharper signal in every other lane — a new fee-rerouting pattern caught in moderation is confirmed in case analysis, published as an anonymized indicator, and immediately makes the mobile worker answer clearer.

## 4. Why Gemma 4 specifically

- **Runs locally and cheaply.** Gemma 4 E2B fits in a Kaggle T4. 4-bit quantization stays in single-digit GBs. No GPU rental, no outbound API spend, no third-party data exposure.
- **Open weights.** Self-host on regulator hardware, NGO laptops, or a Kaggle notebook. No vendor lock-in.
- **Tool calling.** Structured function calls let the harness route GREP, knowledge packs, fee-cap lookups, and graph queries natively.
- **Fine-tunable.** LoRA adapters on filtered synthetic data; 60-step smoke runs on Kaggle T4; full runs scale linearly.
- **Worker languages.** Multilingual coverage spans the corridors that matter: Tagalog, Bahasa, Cantonese, Arabic, Hindi.
- **Aligned baseline.** Refusal behavior is trained in. The harness adds inspectable indicators, citations, and grading on top.

The combination — open weights, local inference, tool calling, fine-tunable, multilingual, aligned — is what makes the rest of the harness possible. A closed frontier API would lose the privacy boundary; a smaller open model would lose tool calling; a non-fine-tunable model would lose the corridor adaptation.

## 5. Evidence: a four-arm benchmark

`DueCare Fine-tuning and Evaluation` is the quantitative control plane. It runs the same prompt set through four arms with the same combined rule + LLM grader: base Gemma 4, base + DueCare harness, fine-tuned Gemma 4 (LoRA adapter), and fine-tuned + harness. Every score carries a row citation back to the prompt, the response, and the rule or judge dimension that fired.

The shape of the result, illustrated below, motivates the architecture: the harness substrate carries more of the lift than fine-tuning alone, and stacking the two compounds. Numbers will be back-filled from the next end-to-end A-00 run before submission; the pipeline and methodology are real today, the absolute numbers are illustrative.

| Arm | Score (illustrative) |
|---|---|
| Base Gemma 4 | 62.0% |
| + DueCare harness | 81.5% |
| Fine-tuned (LoRA) | 74.8% |
| Fine-tuned + harness | 88.2% |

A-00 also generates the synthetic SFT rows used in fine-tuning (rubric-polished, harness-filtered), saves checkpoints with resume, reloads the base model for grading, and exports a full activity log, prompts, responses, traces, charts, and HTML / Markdown / JSON reports.

## 6. Reusable safety infrastructure, not one chatbot

Three commitments make the system reusable beyond this submission.

- **Local and open.** Gemma 4 with open weights, runnable on Kaggle T4 or partner hardware. No vendor lock-in, no outbound API.
- **Inspectable by design.** GREP rules, knowledge packs, tools, graph extraction, and rubric grading make every answer auditable. A regulator can trace any verdict back to the exact rule version that fired.
- **Reinforcing across lanes.** Platform moderation, NGO casework, mobile worker guidance, research, and anonymized sharing all sharpen each other; the substrate is the same.

## 7. How to run on Kaggle

Three notebooks compose the submission. All three are **script kernels** — copy `kernel.py` into a fresh Kaggle Notebook, set **Accelerator: GPU T4 x2** and **Internet: On**, **Add Model → `google/gemma-4`** (E4B is the default; E2B fits the same path with less RAM), then **Run All**. Each kernel prints a public `https://*.trycloudflare.com` URL within roughly thirty seconds; the slide-deck and chat surfaces live under that URL.

- **DueCare App — [`taylorsamarel/duecare-app`](https://www.kaggle.com/code/taylorsamarel/duecare-app)** — the broad reviewer surface. Every harness layer (persona, GREP, RAG, tools, official-source layer, online), model picker, A/B compare, grading modes, Bulk File Review. Use this if you want to interact with the system.
- **DueCare Live Demo — [`taylorsamarel/duecare-live-demo`](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)** — focused interactive demo kernel and the pitch deck used in the video. Open `/start`, optionally pre-bake a cached row in `/slides/setup`, then open `/slides` for the recording-safe 21-slide deck.
- **DueCare Fine-tuning and Evaluation — [`taylorsamarel/duecare-fine-tuning-and-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation)** — quantitative control plane. Base vs harnessed vs LoRA-tuned vs fine-tuned + harness arms, combined rule + LLM grading, exportable artifact bundle (`/kaggle/working`).

All three kernels work in heuristic-only mode if the Gemma model attachment is missing — the deterministic GREP, knowledge packs, tools, and graph extractors still run. The 21-slide deck is fully recording-safe: only the cached worker-question slide reads from `localStorage`; the other five demo slots are pure client-side animation. Source for every kernel and the slide deck lives at [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp); license is MIT.

## 8. Close

DueCare drafts; the user or trusted caseworker decides. The architecture, substrate, benchmark harness, and deck are designed to be forked and reused — by NGOs that need a local copilot, by regulators that need traceable evidence, by researchers that need a reproducible safety benchmark on open weights, and by platform teams that need to catch the recruitment-ad patterns that slip through generic moderation today.
