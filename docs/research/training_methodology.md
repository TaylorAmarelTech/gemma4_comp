# Distilling a benchmark's measured harness-lift into an on-device safety judge — methodology

> A reproducible recipe for turning an **evaluation** benchmark into **training** data: rather than
> hand-labelling, we distil the *measured* lift the DueCare harness adds over a bare model into vetted
> SFT + DPO pairs, gate them so they teach grounding (not refusal), and train a small Gemma 4 LoRA that
> answers like the harness on its own. Every number is reproducible from `(git_sha, dataset_version)`.
>
> Companion to the design spec [`training_regimes_and_systems.md`](training_regimes_and_systems.md);
> this is the *implemented* methodology + the findings from running it. All scripts are propose-only,
> offline, and CPU-safe except the single GPU train/eval step.

## 1. The idea: distil the lift, don't hand-label

The benchmark already grades every prompt in three arms — **baseline** (bare model), **harness_core**
(offline GREP + retrieved-law context), **harness_full** (core + live tools) — on a calibrated 0–100
rubric (A indicator / B law / C refuse / D resources / E privacy), scored by a self-family-excluded
panel of LLM judges (3 judges, Krippendorff α ≈ 0.92). The *gap* between baseline and harnessed on a
given prompt is the harness's contribution. Where that gap is large **and** the harnessed reply is
genuinely good, the harnessed reply is a ready-made teaching target: it shows the bare model what a
grounded answer to that exact prompt looks like. We distil those pairs into SFT (`messages` →
harnessed reply) and DPO (`chosen` = harnessed, `rejected` = baseline).

Teacher arm defaults to **harness_core**, not harness_full: the cheap offline core captures essentially
all the measured lift (full − core ≈ 0 on the board), and teaching from it avoids memorising volatile
tool facts (live hotline numbers, current fee caps) that belong in tools/RAG, not in the weights.

## 2. The vetting gates (and why each exists)

A high score + large lift is necessary but not sufficient. Each candidate pair must also pass, in order
(`scripts/build_lift_training_data.py`):

1. **Quality / signal** — harnessed mean ≥ `--min-target` (70) and (harnessed − baseline) ≥ `--min-lift`
   (20): a clear teaching signal, not noise.
2. **Grounding floor** — the teacher's A+B+D (indicator + law + resources, max 60) ≥ 24 and B ≥ 4. A reply
   that scores via *refuse* (C) alone — "a refusal without details or citations" — is **not** a good gold
   target.
3. **Grounding-delta** — `teacher(A+B+D) − baseline(A+B+D)` ≥ 2: the lift must *add grounding*, not come
   from refusing harder while indicator/law/resources stay flat. This is the precise guard against
   teaching refusal-only behaviour.
4. **Answered** — a real answer, not an empty / reasoning-trace / too-short non-answer
   (`refusal_detector.py`). A *grounded refusal* counts (refusing to operationalize harm is desired); a
   format failure does not.
5. **Citation accuracy** — no hallucinated statute section or out-of-range ILO convention
   (`citation_accuracy.py`): never teach a fabricated citation.
6. **Privacy scrub** — a conservative regex scrub of emails / phone-like / long-digit runs so targets
   teach the response *shape*, not a specific volatile contact (statute refs like `C181` / `RA 8042` are
   preserved).

Two further gates run at organisation time (`scripts/organize_training_data.py`):

7. **Near-duplicate dedup** — exact (sha256) **plus** SimHash (64-bit, Hamming ≤ 3) near-dup removal
   (reusing `duecare-llm-research-tools`), so a "generalisation" score is never just memorised duplicates
   or paraphrases. The default is deliberately conservative: it drops near-identical re-copies, never
   genuinely-distinct paraphrases.
8. **Typology hold-out** — whole exploitation typologies are withheld from training and used only for the
   generalisation diagnostic; the train splits are then capped per typology and round-robin interleaved so
   no batch is single-keyword (block ordering invites shortcuts).

A final **reasoning-chain gate** (`scripts/build_reasoning_targets.py`) keeps the targets that exemplify
the full chain a good safety answer walks — **indicator → statute → action → resources** — detected
deterministically from the project's own vocabulary (the ILO-11 indicators + `citation_accuracy` +
`refusal_detector`), so the fine-tune learns the whole structure, not a fragment.

### Pre-train quality audit (anti-overfit / anti-shortcut)

The gates above filter *candidates*; one more pass audits the **assembled splits** before the GPU run, so
the ways a distilled safety judge can go wrong are caught in the data rather than discovered after
training (`scripts/audit_training_quality.py`, offline + deterministic, writes
`reports/training/quality_audit.json`):

- **Overfitting → cross-split leakage.** Any held-out prompt with a SimHash near-duplicate (Hamming ≤ 3)
  in train; a non-zero count means the generalisation diagnostic is measuring memorisation. *Live: 0 / 81
  held-out, both SFT and DPO.*
- **False pattern → length shortcut.** DPO `chosen` vs `rejected` length: a large `chosen ≫ rejected`
  ratio teaches "longer = preferred" instead of "grounded = preferred". *Live: 1.18× (54.5 % of pairs
  have the longer `chosen`) — essentially no length confound, confirming the `max_length` fix holds.*
- **Jurisdiction shortcut → corridor concentration.** Per-typology corridor spread, flagging only **dense**
  typologies (≥ 10 rows) whose rows all sit in a single corridor — sparse and attack-*style* categories
  can't span corridors meaningfully, so they are reported, not flagged. The universal layer the model must
  learn is the **ILO-11 indicator**, which the targets carry regardless of corridor; this guards against a
  corridor silently standing in for an indicator. *Live: 10 dense single-corridor typologies — a short,
  inspectable coverage list for the discovery flywheel to widen, not a training blocker.*
- **Fragile-fact memorization.** Gold replies asserting volatile specifics. Phone/hotline numbers are the
  hard gate (must be ~0 — those belong in tools/RAG, and the privacy scrub should remove them); fee amounts
  and dates are informational, since a statute's enactment year (e.g. *Palermo Protocol, 2000*) is a
  **stable** fact, not a fragile one. *Live: 0 phone-like in 2,646 gold replies; the money/date hits are
  dominated by stable statute years and in-scenario amounts.*

### The reasoning contract — a way of thinking, enforced

The chain gate above curates training *targets*; `scripts/reasoning_contract.py` turns the same chain into
an enforceable **contract** — a deterministic spec of the *way of thinking* a Gemma 4 reasoning LoRA should
internalise (a procedure, not facts), checkable three ways from one definition:

- **as a training filter** — keep only traces that satisfy the contract (strict: all four steps, in order,
  with a *valid* non-hallucinated citation, and no phone-like fragile fact in the reasoning);
- **as inference enforcement** — parse the model's thinking trace, verify each step, and emit a **repair
  directive** naming exactly what to fix when a step is missing or wrong (a verify-and-repair loop);
- **as a judge-independent eval metric** — the share of replies whose chain of thought satisfies the
  contract, reported alongside the LLM-panel lift.

Run over the 2,116 gold reasoning traces, **43.1 %** satisfy the strict four-step contract and **90.9 %** the
relaxed three-step form; step presence is indicator 99.9 % / resources 99.1 % / statute 76.3 % / action
74.9 %, and every cited statute is valid (0 % hallucinated). So one contract both *defines* the way of
thinking a reasoning LoRA would be trained on and *measures* that the statute and concrete-action links are
where the chain still needs reinforcement before a strict-contract fine-tune. This is the principled form of
"a model as a way of thinking": the LoRA stores the *procedure* (jurisdiction-independent, fragile-fact-free),
and the contract enforces it at train time, at inference, and in evaluation.

## 3. Findings from running the pipeline

Distilling the live benchmark panel (≈3,775 candidate pairs):

- **2,613** vetted SFT + DPO pairs selected (target ≥ 70, lift ≥ 20); 12 dropped for citation problems.
- **The measured lift is grounding-driven, not refusal-inflation.** Of the selected pairs, 100% carry a
  real grounding-delta, the median is **≈ +32.7 / 60** (min 3.5, max 60), and **zero** are
  refusal-only-lift. In other words, where the harness helps, it helps by adding indicators, citations,
  and resources — exactly what we want a model to internalise.
- **The reasoning chain is uneven.** Of 2,613 targets, 2,116 carry ≥ 3 / 4 chain links; the links are
  present at **indicator 99% · resources 96% · statute 64% · action 61%**. So the distilled targets are
  strong at naming the problem and pointing to help, but **citation (statute) and explicit protective
  action are the weakest links** — a concrete signal for which response elements training and data
  augmentation should reinforce.

## 4. Training + evaluation regime

- **SFT** on the harnessed replies (Gemma 4 chat format), then **DPO** (`chosen` harnessed, `rejected`
  baseline) with a version-safe `max_length` so long grounded `chosen` replies are not truncated against
  short `rejected` ones (a length-bias confound we fixed).
- **QLoRA via Unsloth** (4-bit) — fits the E2B/E4B fine-tune on a single Kaggle T4 / a 4060.
- **Four-arm evaluation** (`scripts/four_arm_eval.py`): stock×{harness off,on} (A,B from the board) plus
  trained×{off,on} (C,D), on the same prompts, reporting **internalisation** `C−A`, **internalised
  fraction** `(C−A)/(B−A)`, residual **harness lift after training** `D−C`, and whether they **stack**
  (`D ≥ B`). A `--split-by-typology` pass reports the metric separately on the **held-out typologies** —
  the anti-shortcut generalisation gap.
- **Over-refusal control** — corridor-swapped counterfactuals and worker-voice benign twins
  (`scripts/build_counterfactual_pairs.py`) guard against a safety-tuned model that over-blocks legitimate
  worker queries.

## 5. Provenance & reproducibility

Every fine-tune run is recorded in an append-only ledger (`scripts/finetune_registry.py`) linking
`model_id → (git_sha = code version, data_manifest_sha256 = dataset version, eval scores, artifacts)`,
and `scripts/build_model_card.py` renders a publishable model card from that record. The whole pipeline
runs as one command — `scripts/training_engine.py` (distill → organize → reason → [train → evaluate, GPU]
→ register) — which on a CPU host produces the training data + a provenance row and cleanly skips the GPU
steps. So any published adapter traces back to the exact data and code that produced it.

## 6. Honest limitations

- The four-arm internalisation / generalisation numbers are **pending the GPU run**; this document reports
  the *data-construction* findings, not post-training scores.
- Grading is LLM-panel-based. We mitigate single-judge bias with a diverse, self-family-excluded panel and
  report agreement (α ≈ 0.92), but it is not human adjudication.
- The distilled set is **not uniform** across typologies; statute and action links are under-represented
  (§3), so coverage is strongest where the benchmark is densest.
- Distillation inherits the harness's blind spots: if the harness fails a prompt, no teaching signal
  exists there. The discovery flywheel (propose → vet → merge) exists to widen coverage over time.
- Volatile facts are excluded **by design** — the model learns stable reasoning, refusal behaviour, ILO
  indicator categories, and evidence-first structure; current contacts/caps come from tools and retrieval.
