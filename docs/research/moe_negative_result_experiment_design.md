# Experiment design — "does fine-tuning an MoE for trafficking detection make it worse?"

> The publishability assessment + the controlled experiment that would *earn* the
> claim, scoped to the hardware we actually have. Companion to the literature synthesis
> in [`moe_finetuning_fragility_and_routing.md`](moe_finetuning_fragility_and_routing.md)
> (that doc = why it's plausible; this doc = how we'd prove it). Compiled 2026-06-08.

## 0. Honest status — what we HAVE vs what we NEED

The claim "MoE fine-tuning made trafficking detection worse" is **not yet a result we
hold.** Publishing it today would violate the project's "Real, not faked" invariant.

| Ingredient | Have? | Note |
|---|---|---|
| A high-stakes, weak-label framing | yes | trafficking probes + ILO grounding rubric |
| Baseline model behaviour (grounding gap) | yes | `model_failure_on_human_exploitation.md` (480 verdicts) |
| Harness-beats-baseline evidence | yes | harness-lift benchmark (Opus-judged) |
| MoE fragility *mechanism* (literature) | yes | ST-MoE / FLAN-MoE / SafeMoE / RASA synthesis |
| **A fine-tuned MoE measured as WORSE** | NO | never run — our default E2B/E4B are **dense+PLE**, not MoE |
| **Routing-drift analysis (expert util / entropy, before vs after)** | NO | the actual contribution; needs white-box MoE |
| **Calibration + FP/FN-harm eval on held-out + OOD** | NO | must build |

**Precision a reviewer will demand:** Gemma 4 **E2B/E4B are dense + Per-Layer
Embeddings, not MoE**; only **26B-A4B** is a true MoE. So the experiment must fine-tune
an *actual* MoE and isolate routing effects — otherwise "it got worse" = "you overfit"
(the ST-MoE critique), not an MoE result.

## 1. The claim (narrow + defensible)

> For this task, dataset, and tuning budget, **naive SFT of a Mixture-of-Experts LLM
> degraded out-of-distribution robustness and calibration on trafficking-risk
> assessment despite improving in-distribution fit; the degradation tracked uneven
> expert/router shifts; a context-first harness with recursive validation was more
> stable without touching weights.**

NOT "MoEs are bad for trafficking detection." NOT "fine-tuning is bad."

## 2. Hardware plan (measured 2026-06-08)

Local: **RTX 4060 Laptop, 8 GB VRAM**, 32 GB RAM, i7-13620H, 156 GB free.

| Run | Fits on 8 GB? | Where |
|---|---|---|
| **OLMoE-1B-7B** (6.9B total/1.3B active) QLoRA 4-bit | yes ~4 GB wt + LoRA | **local** |
| Dense control **OLMo-1B / OLMo-7B** QLoRA 4-bit | yes | **local** |
| Qwen3-MoE-small / DeepSeek-MoE-16B 4-bit | marginal/OOM | local (risky) -> Kaggle |
| **Gemma 4 26B-A4B** (true MoE) 4-bit | NO ~14-15 GB | **Kaggle 2xT4 / A100** |

**OLMoE is the ideal local core:** small enough for 8 GB, Apache-2.0, *fully* open
(data, code, router logits via `output_router_logits=True`) — so the routing analysis
is clean and reproducible. Escalate to 26B-A4B on Kaggle only if the local effect holds
and we want a headline model.

**Environment is the real blocker, not VRAM.** OneDrive corrupted the system Python, so
training deps + the HF cache MUST live outside the OneDrive tree:
- training venv at `%LOCALAPPDATA%\gemma4-trainenv\venv` (built by `scripts/setup_train_env.ps1`)
- `HF_HOME=%LOCALAPPDATA%\hf_home` (never under OneDrive — it would corrupt shards)
- plain `transformers + peft + trl + bitsandbytes` QLoRA (portable on Windows); Unsloth optional.

## 3. Arms (controlled)

Same data, same eval, same decoding for all:
1. **base-MoE** (OLMoE, no tuning)
2. **SFT-MoE** (naive full QLoRA SFT on trafficking rows — the suspected degrader)
3. **SFT-MoE (router-aware)** (freeze/low-LR router, ESFT-style selective experts) — tests whether an MoE-aware recipe recovers it
4. **base-dense control** (OLMo, same SFT) — isolates "MoE-specific" from "generic SFT"
5. **base-MoE + DueCare harness** (no weight change) — the product comparison

## 4. Data (sanitized — rule 10)

- **Train:** A-00-generated SFT rows + graded trafficking examples (synthetic/composite only).
- **Held-out (in-distribution):** unseen probes from the same generators.
- **OOD:** adjacent domains (the multidomain corpus) + paraphrased/equivocation variants (`ambiguity_probes.jsonl`) — where routing drift should bite hardest.
- **No raw ads, no PII, no evasion recipes.** Aggregate error categories only. IRB/domain-expert review before any external submission.

## 5. Metrics (NOT accuracy/F1 first)

High-stakes domain -> the headline metrics are harm-shaped:
- **Calibration** (ECE / reliability curve) — does confidence mean anything after SFT?
- **False-positive harm** (confident wrong "trafficking" flags) — a confident false accusation is worse than a miss-by-abstention.
- **False-negative harm** (missed real indicators because SFT taught shallow cues).
- **Precision @ high confidence** and **recall under triage**.
- Aggregate F1/accuracy reported but explicitly *secondary*.

## 6. The MoE analysis (the actual contribution)

Before vs after SFT, on the eval set (OLMoE exposes router logits):
- **Per-expert utilization** + **routing entropy** + **expert load imbalance**.
- **Routing drift**: do exploitation/OOD inputs route to different experts after SFT?
- Correlate routing-shift magnitude with per-example degradation.
- Worked examples (sanitized) of an input whose route — and answer — flipped.

This is what separates "MoE routing instability" from "bad hyperparameters," and what
makes it cite-alongside SafeMoE/RASA rather than a generic negative result.

## 7. Maps onto existing infra

- **Train:** the A-00 Unsloth/QLoRA path (generalized to OLMoE) in the train venv.
- **Eval (all arms):** `scripts/model_failure_loop.py` — point `--responses` at each arm's outputs; the independent judge + report already aggregate multiple inputs.
- **Harness arm:** `duecare.chat.harnesses.default_harness`.
- **Free cross-checks:** `scripts/llm_providers.py` (base MoE vs dense base on hosted free providers — a cheap pre-experiment sanity landscape).

## 8. Two-paper framing (recommended)

- **Spine paper (evidence mostly in hand):** *"Context-first validation beats
  fine-tuning for high-stakes, weak-label detection."* Backbone = harness-lift +
  grounding study + literature. **Defensible now.**
- **Negative-result section / short paper:** the MoE routing-degradation experiment
  above — earned by ONE focused OLMoE run, escalated to 26B-A4B if it holds.

Do not bet the whole paper on the MoE result before the data exists; make it a section
of the stronger argument until the experiment delivers.

## 9. Phased plan

- **P0 — environment:** `scripts/setup_train_env.ps1` (CUDA venv + HF_HOME outside OneDrive); verify `torch.cuda.is_available()` on the 4060.
- **P1 — local core:** OLMoE base vs SFT vs router-aware-SFT vs OLMo-dense; eval (calibration/FP/FN/OOD) + routing analysis. Goal: does naive SFT degrade OOD + shift routing?
- **P2 — harness arm:** base-MoE + DueCare harness vs the tuned arms.
- **P3 — escalate (optional):** Gemma 4 26B-A4B on Kaggle if the local effect is real.
- **P4 — write:** spine paper + MoE section; sanitized; domain-expert review.

## 10. Kill criteria (honesty)

If P1 shows **no** OOD degradation and **no** routing drift, we DO NOT publish a
negative result — we report "naive SFT was fine here" and pivot the paper to the
harness-lift spine. The experiment must be able to fail.
