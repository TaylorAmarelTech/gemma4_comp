# Phase 3 — the DueCare training framework (the solution beyond the harness)

> Phases 1–2 proved, robustly and reproducibly, that baseline models carry significant
> trafficking-safety gaps and that a prompt-time **harness** closes much of them — the live
> 0–100 benchmark shows **+30 to +56** lift across the flagship models, judged by a diverse,
> self-family-excluded panel. Phase 3 is the **solution**: turn those proven gaps, the harness's
> own knowledge, and vetted community materials into **training** that raises the model's *own*
> capabilities and works hand-in-hand with the harness.

## The thesis

The harness proves the knowledge is **reachable** — it makes a model reach for it at inference.
Phase 3 asks the next question: can we **train** the model to reach on its own, internalising the
**stable** behaviours (exploitation-indicator reasoning, grounded-refusal style, evidence-first
response shape, ILO framing) into the weights, while the harness keeps supplying the **volatile**
facts (current hotlines, fee caps, fresh statutes) through tools and retrieval?

A trained model and the harness should **stack**: better standalone *and* better harnessed. We do
not assume this — we **measure** it. Every trained checkpoint is scored on the *same* 0–100
benchmark in **four arms**:

| arm | model | harness |
|---|---|---|
| A | stock | off |
| B | stock | on |
| C | trained | off |
| D | trained | on |

That tells us (1) how much training internalises the harness lift (C − A vs B − A) and (2) whether
training and the harness stack (D vs B and C).

## The five subsystems

### 1. Training-data generation — gap-driven + harness-distilled
- **Gap-driven.** The benchmark's `panel.jsonl` already records *where* each model fails (low
  component scores on B "cites the specific law", D "concrete resources", E "safety/privacy"; and
  the egregious set). Those are the highest-value teaching targets.
- **Harness distillation.** Every benchmark prompt has a **baseline** reply (often weak) and a
  **harnessed** reply (graded high). `(prompt → harnessed reply)` pairs are ready-made **SFT**
  targets; `(chosen = harnessed, rejected = baseline)` are ready-made **DPO** pairs. This distils
  the harness *into* the weights.
- **Synthetic augmentation.** A-00's rubric-polisher generates extra graded examples for
  under-covered typologies / corridors.
- **Community materials.** Real, anonymised corrected responses + legal citations from NGOs and
  experts (subsystem 4).
- **Stable-vs-volatile discipline** (per `81_canonical_runtime.md`): targets teach reasoning,
  refusal, indicator, and evidence **shape** — never hardcode a volatile hotline number or fee cap
  (those stay tool-supplied, so the weights never go stale).

### 2. Data vetting — multi-gate, nothing trains unvetted
Every candidate example passes, in order:
1. **Quality gate** — the target's component-judge score ≥ threshold **and** the baseline→target
   lift ≥ threshold (a clear teaching signal, not noise).
2. **Citation accuracy** — the deterministic check (`scripts/citation_accuracy.py`) that the
   target's legal citations are real and relevant; no hallucinated statutes enter the data.
3. **PII gate** — the anonymiser / `_safe_text` scrub; no raw PII enters training data
   (`10_safety_gate.md`), always-on.
4. **OpenClaw quality vet** — the same accept/reject LLM gate that vets benchmark prompts, applied
   to `(prompt, target)` pairs.
5. **Human / community review** — a sampled queue for expert sign-off (subsystem 4), required for
   community-sourced and high-stakes examples.

Rejections are logged with reasons (auditable), exactly like the prompt discovery flywheel.

### 3. Training-data pipeline + the training flywheel
```
generate → vet → format (Unsloth SFT + DPO JSONL, train/val/test, provenance manifest)
        → train (Unsloth LoRA, duecare-llm-training) → evaluate (0–100 benchmark, 4 arms)
        → select (promote only checkpoints that raise trained-baseline toward stock-harnessed
                  with no safety regression) → loop
```
This is the **training flywheel**, parallel to the **discovery flywheel** (Hermes → OpenClaw) that
grows the benchmark. Both are resumable, propose-only into gitignored stores, and supervised at the
merge/promote step.

### 4. Community engagement
- The outreach **email oracle** (`apps/duecare-ai.com/app/outreach.py`) already solicits
  *knowledge* from civil society. Extend it to solicit + vet **training materials**: real corrected
  responses, case patterns, and legal citations from NGOs, labour lawyers, and regulators.
- Loop: **contribution → anonymise → vet (subsystem 2) → credit → incorporate.** Contributors see
  their material's measured effect (benchmark lift) — a feedback loop that rewards participation.
- **Email-first** (`feedback_email_only_for_civil_society`): no new login or UI for stakeholders.

### 5. Harness + trained model, hand-in-hand
- Trained weights hold the **stable substrate**; the harness supplies **volatile facts** + the
  deterministic tool layer (corridor fee caps, hotlines, fee-camouflage decode, ILO indicators).
- The four-arm evaluation quantifies the stacking. The deployment story: an NGO runs the trained
  **on-device** model (better standalone, works offline) *and* the harness (fresh facts when
  online) — robust even on stale data or no connection.

## What exists vs what is new

**Exists:** Unsloth fine-tuning (`duecare-llm-training`, A-00) + the seed-corpus SFT prep
(`scripts/prepare_training_data.py` — the 204 manually graded worst→best responses), the 0–100
benchmark + `panel.jsonl`,
the discovery flywheel (Hermes / OpenClaw), the outreach oracle, the anonymiser, `citation_accuracy`,
the KnowledgeObject taxonomy + envelopes.

**New in Phase 3:** the **gap-driven training-data builder** (`panel.jsonl` → vetted SFT/DPO), the
**multi-gate training-data vetting**, the **train → eval → select loop** (and a daemon to run it),
the **community training-material solicitation**, and the **four-arm stacking evaluation**.

## Honest framing (the same discipline as the benchmark)
- **Distillation may not fully internalise the lift.** The harness's retrieval and tools supply
  facts the weights cannot memorise without going stale; we **measure** the residual gap (arm C vs
  arm B), we do not assume it closes.
- **Circularity risk.** Training data derived from one judge's scores could teach that judge's
  preferences; we counter with deterministic gates (citation, PII), a diverse judge panel, and
  human review — and we validate on held-out prompts and the four-arm benchmark.
- **No checkpoint is promoted on a single number.** Promotion requires the four-arm benchmark plus
  regression checks (no criterion regresses, refusals still correct, no PII leakage).

## First implementation step (this commit)
`scripts/build_lift_training_data.py` — reads the benchmark's `panel.jsonl` + `results.jsonl`,
selects high-lift `(baseline, harnessed)` pairs, vets them (quality + lift threshold + PII scrub),
and emits **SFT** + **DPO** JSONL plus a provenance manifest to a gitignored `reports/training/`
store. Distinct from `prepare_training_data.py` (which converts the seed corpus's manual grades):
this distils the **benchmark's measured harness-lift** into training signal. Propose-only; the
training runner (next step) consumes it.

## Roadmap (subsequent steps)
1. **Training runner** — ✅ built: `scripts/train_lift_distill.py` runs the canonical Unsloth recipe
   (FastModel → get_peft_model → get_chat_template `gemma-4-thinking` → SFTTrainer +
   `train_on_responses_only`, then a DPO pass) over the vetted SFT/DPO JSONL, with optional GGUF
   export for on-device. CPU-safe `--validate` (data + plan check) runs anywhere; the GPU train step
   runs on Kaggle (`--test-run` smoke, or full with `--base-model unsloth/gemma-4-E4B-it`).
2. **Four-arm evaluator** — extend `rich_harness_lift.py` to grade a trained checkpoint in arms C/D
   next to the stock A/B already on the board.
3. **Train→eval→select daemon** — a durable loop (sibling to the benchmark engine) that trains,
   evaluates, and promotes only improving checkpoints.
4. **Community training-material intake** — extend the outreach oracle + a vetting queue.
5. **Paper** — "Distilling a safety harness into the weights: from a measured inference-time lift to
   a trained capability," with the four-arm results.
