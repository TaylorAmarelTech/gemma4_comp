# DueCare training regimes & systems — design spec

> Synthesis of a 4-thread parallel design (2026-06-26: SFT curriculum, preference optimization, the
> Unsloth/QLoRA protocol + on-device export, and the end-to-end system) for fine-tuning small Gemma 4
> (E2B/E4B) to internalise the harness's safety behaviour. Most infrastructure already exists; this spec
> records the regime decisions + the prioritized build list. Companion: `phase3_training_framework.md`,
> `training_for_understanding.md`, `benchmark_findings_and_roadmap.md`.

## The thesis (what the benchmark tells us to train)

- **Train the grounding, not the refusal.** The lift lives in **B (cite the law) + D (resources) + A
  (indicator)**, not C (models already refuse). The gold target is a *grounded* refusal; a bare refusal
  is never a target (P0 fix, `60e8a9e5`).
- **Train small models** — the equalizer effect means E2B/E4B gain the most (the on-device story).
- **Teach from the offline `harness_core` arm** — it captures ~all the lift and avoids memorising
  *volatile* facts (hotlines, fee caps) that belong in tools/RAG. Stable reasoning → weights; volatile
  facts → retrieval.
- **Prove understanding, not memorisation** — the held-out-typology **generalisation gap**
  (`four_arm_eval --split-by-typology`, `e3d59a02`) is the headline anti-shortcut metric; promote the
  smallest-gap variant, never the highest train score.

## 1. SFT regime

- **Target shape:** a deterministic `indicator → controlling law → refuse/redirect → concrete resources
  → safety` chain, built from the harness's own fired-rule `indicator`/`citation` fields (no LLM needed;
  an optional single re-gated fluency rewrite). This is the V4 "reasoning-supervised" target; it maps
  1:1 onto A–E and is the strongest anti-shortcut lever. Keep the `harness_core` teacher reply as the V0
  fluent default; **validate every target** against the per-prompt fired citations (relevance, not just
  plausibility).
- **Curriculum:** grounding-first, interleaved (not block-ordered): Phase 1 = manual worst→best seeds +
  clear-indicator distilled pairs; Phase 2 = third-party-pretext / obfuscated / very_hard (the measured
  gap is operator-voice +48 vs pretext +24). NOTE the `SFTTrainer` default RandomSampler reshuffles, so
  **shuffle-invariant organisation (balance, hold-out, dedup) carries the weight**; strict ordering is a
  later `--no-shuffle` option.
- **Data mix + breadth:** the live distilled set is stale (pre-P0) and collapses to ~98 rows / 4
  typologies — **breadth is the bottleneck, not count.** Target ≥1–2k pairs spanning ≥20 typologies,
  ≥5 held out. Make `organize_training_data.py` the single **union mixer** (distilled + manual seeds +
  counterfactual/benign twins, one shared hold-out split); add **near-dup (shingled-Jaccard) dedup** so
  twins/paraphrases can't leak train↔held-out; balance by difficulty + framing; `--cap-per-category ~40`.
- **Don't train:** volatile facts (extend `_SCRUB` to abstract fee-cap numbers, keep the statute name),
  bare refusals (gated), over-refusal (new control, below), hallucinated/irrelevant citations (gated).
  Deprecate the SFT "DO NOT…" negative preamble — route worst→best into DPO instead.

## 2. Preference-optimization regime

- **Objective:** **DPO primary** (data is natively paired; already wired; the reference KL term, β, is
  the leash against degenerate-refusal over-optimisation; ref-free under LoRA = no extra memory). Run
  **SimPO** (`CPOTrainer`, length-normalised) as the anti-verbosity A/B arm; offer **ORPO** as a
  single-stage compute-saver; **KTO** only as a fallback for unmatched over-refusal examples.
- **Pair construction — teach grounding, not refusal:** gate/weight by the **B/D/A component *delta***
  (ΔB+ΔD floor), not the total; require `ΔC ≤ ΔA+ΔB+ΔD` (refusal isn't the driver); drop inverted pairs
  where the baseline is more grounded than the teacher (the refusal-collapse catch).
- **The keystone — benign-twin / over-refusal control:** add pairs where **chosen = grounded help,
  rejected = over-refusal** on legitimate worker questions (mine the existing `*_query` benign
  categories + counterfactual twins of exploit prompts; reject = real over-refusals flagged by
  `refusal_detector`). ~30% benign : 70% exploit. This both bounds over-refusal AND breaks the
  "longer = preferred" length bias at the data level.
- **The truncation fix (do first):** `DPOConfig` sets no `max_length`/`max_prompt_length`/
  `max_completion_length` → the long grounded `chosen` is silently truncated while the short `rejected`
  isn't → a pure length-bias confound. Set them (4096/2048/2048) before any run. Expose `--dpo-lr`
  (today hardcoded 5e-6), add `rpo_alpha=1.0` (anti-degeneration), `--dpo-ref {base, sft-merged}`.

## 3. QLoRA / Unsloth protocol + on-device export

- **Recipe (train == inference, per rule 81):** `FastModel.from_pretrained(dtype=None,
  load_in_4bit=True, full_finetuning=False)` + `get_chat_template("gemma-4-thinking")` +
  `train_on_responses_only`; **no `device_map` at train time** (single-device). LoRA `r=16, alpha=32,
  dropout=0.0`, 7 target modules (attn+MLP), `use_gradient_checkpointing="unsloth"` (non-negotiable on
  T4), `adamw_8bit`, SFT lr 2e-4 / ≤2 epochs, DPO lr 5e-6 / β 0.1 / 1 epoch.
- **T4 memory:** E2B batch 2 × accum 4; E4B batch 1 × accum 8 (effective 8 both); seq 2048 (4096 on
  A100/E2B-headroom); DPO halves the batch (chosen+rejected+ref). E2B = the on-device/phone headline
  (LiteRT INT8 ~1.5 GB), E4B = the laptop/quality headline (GGUF). Train both from one manifest.
- **Budget:** validate (CPU) → smoke `--test-run` (~10 min) → E2B full (~0.5 hr) → E4B full (~1 hr) →
  export (~0.3 hr) → four-arm eval. One full cycle ≈ 3–5 GPU-hr (several/week within Kaggle quota).
- **Export:** merge LoRA into a **16-bit** base (never 4-bit) → GGUF via **llama.cpp from source** for
  real Q4_K_M/Q5_K_M (Unsloth's `save_pretrained_gguf` only reliably emits Q8_0/F16 for Gemma 4 today)
  → Q4_K_M headline + Q5_K_M quality + Q8_0 reference; **LiteRT** via ai-edge-torch → INT8 `.task` for
  Android (E2B). Round-trip verify the quantised model preserves the safety behaviour.
- **Gotchas:** chat-template parity train↔GGUF (save the templated tokenizer); thinking-channel
  masking/stripping consistency; 4-bit-merge quality loss; T4 has no bf16 (fp16, watch NaNs); OOM points
  (seq×batch, DPO 2-3×, the merge step — fresh process); the `HF_TOKEN` vs `HUGGINGFACE_TOKEN` env
  mismatch in the publisher.

## 4. The training SYSTEM

- **The DAG:** two always-on CPU flywheels — **discover** (candidate generation → quality vetting) and **grade** (engine →
  `rich_harness_lift`) — feed a propose-only **training bridge** (`build_lift_training_data` →
  `organize_training_data` → understanding variants), then a **GPU window** (`train_lift_distill` →
  `four_arm_eval --run`), then the **promote gate**, the **registry**, and **publish**. *Nothing is
  trained that wasn't first measured as a real, grounded, non-hallucinated lift on a versioned prompt set.*
- **Sources → training (one knowledge bus):** scraped corpora (`acquire`→`promote`), legal updates,
  community-vetted knowledge objects (`outreach`/`federation`, sha256 + node-id provenance), and the
  flywheel's accepted prompts all normalise through the envelope + `/api/knowledge/import`. A new source
  changes the **RAG/tool answer immediately** (no retrain) and only enters the weights as **stable
  reasoning** after the benchmark measures lift on it. Community signal also proposes new *rubric
  dimensions* (`outreach.prioritized_context`).
- **Continuous improvement — a sibling daemon, NOT the engine:** training is GPU-gated; keep the engine's
  board ownership sacred. A new `training_engine.py` (same lock/.stop/--once/.ps1 pattern, 4th agent in
  `orchestrator.py`) does all CPU-safe work each tick (re-distil → organize → four-arm `--analyze` →
  evaluate retrain triggers) and **freezes a ready-to-run GPU job spec** when enough new vetted/broad
  data accrues; a human/GPU window executes; promotion is human-gated. Triggers: +N net vetted pairs, new
  typology/corridor coverage, or a **board version bump** (rubric v2 — which *invalidates* prior gold).
- **Promote gate (mechanical verdict, human decision):** generalisation gap ≤ τ ∧ **no over-refusal
  regression** (the blocking gate to build) ∧ C−A>0 concentrated in B/D ∧ no component regression ∧
  D≥B ∧ no hallucinated citations/PII. Select the smallest-gap-no-regression variant.
- **Provenance:** `model_registry.py` threads source→prompt→panel→data→checkpoint hashes into one
  reproducible identity tag `duecare-gemma-4-{e2b|e4b}-safetyjudge-v{X.Y}+board{v1.3}+data{sha8}`;
  model card committed on promote only; weights never auto-published (rule 10 pre-publish scan).

## 5. Prioritized build list

### Safe now (CPU, offline, propose-only, no engine/GPU impact)
1. **Regenerate the stale distilled data** — re-run `build_lift_training_data.py` (now P0-gated, teacher=core).
2. **The DPO truncation fix + DPO knobs** in `train_lift_distill.py` (`max_length`/`--dpo-lr`/`rpo_alpha`/`--dpo-ref`/`--objective`). *Not running now, so safe; precondition for any real run.*
3. **Over-refusal control: the counterfactual/benign-twin generator** (new `build_counterfactual_pairs.py`) + the over-refusal diagnostic in `four_arm_eval.py` (split under-refusal lift from over-refusal rate, never merged). *The keystone.*
4. **Union mixer + near-dup dedup + difficulty/framing balance** in `organize_training_data.py`.
5. **Component-delta gating** in `build_lift_training_data.py` (ΔB+ΔD floor; `ΔC ≤ ΔA+ΔB+ΔD`; inverted-pair guard).
6. **Reasoning-chain target builder** (`build_reasoning_targets.py`, V4) + citation-relevance gate +
   metadata-only repair queue (`build_reasoning_gap_queue.py`) + proposed deterministic repair rows
   (`build_reasoning_repairs.py`) + non-duplicating repaired SFT comparison arm
   (`build_reasoning_sft_variant.py`) + corridor expansion curation plan
   (`build_corridor_expansion_plan.py`).
7. **`finetune_registry.py` + `validate_training_provenance.py`** (provenance spine) + stamp `four_arm_eval --sha`; add manifests to orchestrator backups.
8. **`training_engine.py`** (the propose-and-stage sibling daemon) + `training_engine.ps1`.
9. **`export_ondevice.py`** (merge→GGUF, lift the archived A-14 logic) + `convert_to_litert.py` (E2B INT8); model-card provenance + the HF_TOKEN env fix.

### GPU-gated (Kaggle / local RTX 4060, human window)
10. Execute the frozen spec: full E2B + E4B SFT(+DPO) → `four_arm_eval --run`; the V0–V4 understanding study; select by smallest held-out gap with no over-refusal regression.

### Human-gated (irreversible / high-stakes)
11. The promote decision + model publish (card commit + HF Hub + GGUF, rule-10 pre-publish scan); board version bumps (versioned, re-graded, never mid-sweep); **practitioner validation** (the biggest credibility unlock).

## 6. Honest limits
- **LLM-judge ≠ practitioner outcome** — every promoted model is "best by our panel," not field-validated.
- **Circularity** — training data derives from judge scores; mitigated (deterministic gates, diverse
  self-family-excluded panel, held-out typologies, human review), not eliminated.
- **A small gap is evidence, not proof** — report it with the perturbation curve + counterfactual rate.
- **Over-refusal is currently unmeasured** — a blocking gate to build before trusting any promotion.
- **Some lift is irreducibly volatile** — the target is internalising stable reasoning, not memorising facts.
