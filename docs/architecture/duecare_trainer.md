# Duecare Trainer — model adaptation / retraining

**Status: Prototype (appendix pathway).** Lives in
[`kaggle/A-07-bench-and-tune/`](../../kaggle/A-07-bench-and-tune/)
and `packages/duecare-llm-training/`. Bench-and-tune notebook is
the reference implementation; full Trainer service is post-hackathon.

> A privacy-preserving model-adaptation pipeline that converts
> validated, anonymized case knowledge into task-specific Gemma 4
> adapters for moderation, case intake, research evaluation, and
> worker assistance.

## Why this is its own component

Fine-tuning is a separate concern from the deterministic safety
harness. The harness owns policy, citations, and contacts. Trainer
owns model behavior. They compose:

```text
Fine-tuned Gemma  =  better baseline behavior
Safety Harness    =  grounded, auditable, policy-controlled output
```

A tuned model never replaces the harness. A judge or auditor should
be able to inspect every layer regardless of which model was loaded.

## What it produces

| Adapter / tuned model | Use case | Status |
|---|---|---|
| `duecare-gemma-evaluator` | LLM-as-judge grading | Prototype (referenced in HF Hub model card draft) |
| `duecare-gemma-worker-advisor` | plain-language migrant-worker help | Roadmap |
| `duecare-gemma-case-intake` | NGO / government complaint triage | Roadmap |
| `duecare-gemma-platform-moderation` | social-media / job-platform content review | Roadmap |
| `duecare-gemma-multimodal-docs` | screenshots, contracts, receipts, IDs | Roadmap |
| `duecare-gemma-corridor-ph-hk` | corridor-specific adapter | Roadmap |
| `duecare-gemma-corridor-id-sa` | corridor-specific adapter | Roadmap |
| `duecare-gemma-research-assistant` | academic synthesis, benchmark analysis | Roadmap |

## Inputs

- Anonymized case summaries (via `harness/_governance.py` Anonymizer).
- Synthetic screenshots / documents (the 20 bundled CC0 evidence images + 13 structured-post JSONs).
- Regulator-provided FAQ material.
- NGO intake scripts (subset of `_personas.json`).
- Public laws / regulations (the 46-doc RAG corpus).
- Rubric failure cases (the 65-test adversarial suite).
- Adjudicated good / bad responses (graded outputs from `kaggle/A-11-grading-evaluation/`).
- Adversarial prompts.
- Multilingual worker questions (587 prompts × 11 languages from `_classifier_examples.json`).

## Outputs

- LoRA adapters
- Merged model weights where the license allows
- GGUF / llama.cpp exports
- LiteRT / mobile exports
- Model cards
- Benchmark reports (universal rubric v3.10 + 65-test adversarial)
- Safety regression results (gated by Duecare Eval)
- Provenance manifest pinning `(model_revision, git_sha, dataset_version)`

## Hard rule: PII gate

The training pipeline must be gated:

```text
raw data
  ↓
Anonymizer (harness/_governance.py — strip / generalize PII)
  ↓
Curator validation (single-file PR review)
  ↓
Dataset builder (Unsloth chat-format JSONL with `Provenance` stamps)
  ↓
Training (LoRA on Gemma 4 E4B baseline)
  ↓
Evaluation framework (gates the release — must pass 65-test adversarial + rubric regression)
  ↓
Release (HF Hub model card + GGUF / LiteRT artifacts)
```

**No raw PII may enter the training set.** The Anonymizer agent's
audit log stores `sha256(original)` plus the redaction action — never
the plaintext.

## Why this matters across the five canonical lanes

- **Platform safety** can adapt models to moderation policy (severity thresholds, escalation patterns).
- **NGO & regulator** can adapt models to intake workflows and local regulations (jurisdiction-specific tone, complaint-form vocabulary, corridor-specific statute citations).
- **Individual worker / mobile** can use smaller tuned models offline (E2B + LiteRT path).
- **Researcher** can reproduce stock-vs-harnessed-vs-tuned behavior with provenance.
- **Developer / integration partner** can package tuned adapters behind stable APIs and deployment templates.

## Today's bridge (what's actually built)

- **`kaggle/A-07-bench-and-tune/`** — Unsloth SFT + DPO + GGUF + HF
  Hub push pipeline. Runs end-to-end on a Kaggle T4 / dual-T4
  session. Produces `Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0`.
- **`packages/duecare-llm-training/`** — training-helper utilities:
  dataset builder, LoRA recipe templates, GGUF export wrapper.
- **`packages/duecare-llm-publishing/`** — HF Hub upload + model card
  generator with provenance manifest.

## What's roadmap

- **Trainer service** — a managed pipeline an NGO partner can submit
  anonymized case data into, get back a signed adapter pack via
  Duecare Exchange. Multi-tenant, evaluation-gated, human-approved.
- **Adapter registry** — discoverable `duecare-gemma-*` collection on
  HF Hub with status badges + benchmark cards.
- **Federated fine-tune** — partners contribute LoRA gradients without
  sharing raw data; aggregated server-side. Open research direction.

## Critical: Trainer does NOT own

- Live complaint submission.
- Contact truth (that's the deterministic Contacts directory).
- Raw case storage (Anonymizer + Exchange handle that).
- Regulator policy (humans + RAG packs own that).

Trainer's job ends at "produce a tuned adapter, gated by Eval, with a
signed provenance manifest." Everything downstream is Harness, Exchange,
Channels, or Mobile.
