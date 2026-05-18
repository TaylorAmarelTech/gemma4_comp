# DueCare AI — AI infrastructure to combat migrant-worker exploitation

**Track:** Safety & Trust (primary). Special Technology eligibility: Unsloth (LoRA fine-tuning) and llama.cpp / LiteRT (local Gemma 4 deployment).

**Live deck:** the recording-grade pitch lives at `/start` and `/slides` inside the live-demo kernel (see *Run on Kaggle* below).

## Try it in 30 seconds

Three Kaggle script kernels. Each is a single `kernel.py`: copy into a fresh Kaggle Notebook → **Accelerator: GPU T4 x2**, **Internet: On** → **+ Add Input → Models → `google/gemma-4`** → **Run All**. The kernel prints a public `https://*.trycloudflare.com` URL in ~30 seconds.

- 🟢 **DueCare App** — [`kaggle.com/code/taylorsamarel/duecare-app`](https://www.kaggle.com/code/taylorsamarel/duecare-app) — broad reviewer workbench.
- 🎬 **DueCare Live Demo** — [`kaggle.com/code/taylorsamarel/duecare-live-demo`](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) — focused demo + 21-slide pitch deck at `/start` and `/slides`.
- 📊 **DueCare Fine-tuning and Evaluation** — [`kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation) — A-00 control plane: four-arm runs, LoRA fine-tune, combined judging, exported report bundle.

Source: [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp) (MIT). Heuristic-only mode (no model) still serves `/start`, `/slides`, deterministic GREP / RAG / tools, and the cached worker-question slot.

## 1. The capability gap, named

Twenty-eight million people are in forced labor today; forced labor generates $236 billion in illicit profit a year; 169 million people work outside their country of birth and migrant workers face roughly three times the forced-labor risk (ILO, 2022 and 2024).

Despite frontier-model progress, this domain has not benefited. A useful rule of thumb is

> capability spike ≈ verifiability × training attention × data coverage × economic value

All four factors are weak for migrant-worker safety. **Verifiability** is hard because the right answer is the corridor rule, not a generic refusal. **Training attention** is small because there is no large public alignment corpus. **Data coverage** is thin because the source statutes, circulars, and corridor caps are fragmented across DMW, BP2MI, Nepal DoFE, HK Labour, SG MOM, UAE MoHRE, plus ILO conventions. **Economic value** is low for commercial providers, so this slice of the safety surface does not receive product investment.

The result is documented. A 2024 Kaggle red-team write-up evaluated leading open and closed models on migrant-worker prompts and found that frontier LLMs *consistently* produce plausible-sounding answers that are wrong in load-bearing ways. ([prior work, Kaggle 2024](https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/llm-complicity-in-modern-slavery-from-native-blind))

## 2. What goes wrong concretely

Across iterative test runs against base Gemma 4, GPT-OSS, Qwen, Llama, Mistral, and DeepSeek for this domain, the recurring failure modes are:

- **Hallucinated statute sections.** Generic models will cite `RA 8042 §99` when the act only has 42 sections, or invent corridor caps that do not exist.
- **Wrong corridor fees.** A PH-HK domestic worker placement fee is zero PHP under POEA MC 14-2017 + DMW policy. Generic models routinely propose a "normal" fee.
- **Privacy oversharing.** Asked an operational question, generic models often request the worker's name, employer, account number, and contract details before answering.
- **Vague safe-language.** Asked what to do, generic models give "consult a lawyer" rather than naming the actual labour office, complaint pathway, or refund mechanism.
- **Operational uplift.** Asked how to "structure" a fee, a generic model with no refusal head will draft the tri-party arrangement and salary-deduction language verbatim.

Each failure is correctable in isolation, but the corrections do not generalize across corridors, statutes, or recruiter tactics. A new corridor needs a new RAG pack; a new statutory amendment needs a citation update; a new fee-camouflage pattern needs a new indicator.

## 3. Why training and evaluation regimes alone don't fix this

Three reasons.

**Data scarcity at training time.** The public corpus of corridor-specific safety guidance is small. A LoRA fine-tune on 2,000 rubric-polished rows lifts behavior, but the underlying knowledge base is still thin compared to the world of corridors and statutes the model sees at deployment. Fine-tuning shifts response shape; it does not import the DMW Memorandum the worker actually needs.

**Evaluation that catches the right errors is hard.** Generic safety benchmarks (TruthfulQA, BBH, HellaSwag) test general capability, not domain correctness. A model can pass them and still get the PH-HK corridor rule wrong. Without domain-specific rubric dimensions (refusal correctness, corridor-rule grounding, contact accuracy, evidence-preservation language, no operational uplift), graders register false signal.

**Verifiability is a substrate property, not a model property.** A reviewer needs to see *which rule fired*, *which row from which file backed the claim*, and *which corridor pack the answer came from*. No model — base or fine-tuned — can produce that audit trail by itself.

## 4. How DueCare actually works — the substrate

DueCare wraps Gemma 4 with a set of inspectable, deterministic components. Each one solves a slice of the problem fine-tuning cannot. The substrate is the same across all five user-facing lanes (platform moderation, NGO casework, mobile worker guidance, research, anonymized sharing).

- **GREP rules.** ~100 deterministic patterns covering fee camouflage (training / medical / processing / orientation / insurance / deposit), wage assignment, debt novation, restricted provider choice, passport retention, document retention, contract substitution, retaliation language, corridor-cap violations. Each rule has an id, a regex, a severity, a corridor scope, and a unit test. A rule fires *before* the model generates and is part of the prompt context the model sees.
- **Knowledge packs.** Versioned RAG corpus of ILO conventions (C029, C181, C189, Forced Labour Indicators), Palermo Protocol means/acts/purpose, POEA / DMW Memorandum Circulars (esp. MC 14-2017 zero-fee for PH-HK), BP2MI Reg 9/2020, Nepal FEA 2007 §11(2), HK Cap 57 §32, HK Cap 163, SG EFMA Cap 91A §22A, UAE MoHRE Decree 765/2015, plus vetted contact pathways. Retrieved per-prompt, hashed, and cited verbatim in the response.
- **Tools.** Structured function calls Gemma 4 invokes natively: corridor fee-cap lookup, agency registry, refund pathway, contact resolver, graph query, statute-section range validator. Each tool returns typed data the model can quote.
- **Persona + context layer.** Audience-aware prompt scaffold (worker / caseworker / regulator / researcher / platform) plus official-source layer for allowlisted public-authority lookups (DMW, ILO, HK Labour).
- **Graph extraction.** Bulk File Review parses ZIP / PDF / CSV / images, extracts typed edges (`worker → paid_fee → recruiter`, `agency → restricts_choice → clinic`, `worker → seeks_remedy → regulator`), and renders an evidence graph with row citations. Optional local Gemma edge pass adds typed edges from natural-language evidence.
- **Privacy gates.** Anonymizer (PII regex + NER + audit log of `sha256(original)`), search-safety gate (generalizes outbound queries before any third-party search), post-search verification (validates result quality before injection), k-anonymity check on shared knowledge objects.
- **Combined grading.** Rubric (refusal correctness, grounding, evidence preservation, contact accuracy, safe-reporting language, statute-section validity) + optional LLM judge over the same dimensions. Row citations on every dimension.
- **Refusal head and substance-over-form.** When indicators compound (worker-paid fee + restricted choice + salary deduction), the model refuses operational help and surfaces the refund / complaint pathway instead.

## 5. How the harness composes

A request flows: prompt → persona context → GREP scan (deterministic indicators fired) → RAG retrieval (corridor rule, ILO indicator) → tools (fee-cap, registry) → Gemma 4 generation (bounded by indicators + retrieved context + refusal head) → combined grader → cited response. Every stage is logged, timed, and traceable per request. A reviewer can grep the trace to confirm exactly which rule, which pack, and which tool produced the answer.

## 6. Evidence: the A-00 control plane

`DueCare Fine-tuning and Evaluation` (the A-00 control plane) facilitates the work that makes the substrate measurable: four comparable arms (base, base+harness, fine-tuned, fine-tuned+harness) on the same prompt set under combined rule + LLM grading; rubric-polished synthetic SFT generation filtered by the same harness used at inference; LoRA fine-tune with checkpoint and resume; exported report bundle per run. Across runs, the harness consistently lifts response quality over base, and stacking fine-tune + harness compounds further. Specific lift numbers will be published with the final A-00 run alongside the submission. The point of A-00 is that any judge can re-run the same arms and reproduce the comparison.

## 7. Prior art and influences

The substrate is informed by the 2024 Kaggle red-team study, ILO's Forced Labour Indicators and conventions, the Palermo Protocol means/acts/purpose framework, POEA / DMW circulars, and the work of partner NGOs (Polaris, IJM, ECPAT, POEA, BP2MI, HRD Nepal). It also draws on a sister synthetic-evidence harness that generates fully fabricated recruitment ads, case bundles, and worker threads with closed-set indicator vocabulary and reproducible release artifacts — used for benchmarking and reviewer self-testing without exposing real case data.

## 8. Close

DueCare drafts; the user or trusted caseworker decides. The substrate is designed to be forked and reused — by NGOs that need a local copilot, regulators that need traceable evidence, researchers that need a reproducible safety benchmark on open weights, and platform teams that need to catch the recruitment-ad patterns that slip through generic moderation today.
