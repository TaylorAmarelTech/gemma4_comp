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
5. **Citation accuracy + relevance** — no hallucinated statute section or out-of-range ILO convention
   (`citation_accuracy.py`), and no real-but-irrelevant ILO convention for the named exploitation signal
   (`palermo_screening.citation_coherence`): never teach a fabricated citation or citation theatre.
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
`refusal_detector` + `palermo_screening.citation_coherence`), so the fine-tune learns the whole structure,
not a fragment or a real-but-irrelevant legal citation. The default gate still checks and drops
chain-qualified rows whose cited ILO convention does not govern the named indicator; after the upstream
distillation gate rejects citation-theatre rows, the current local run keeps **960** of
1,316 organized train SFT targets and drops **0** otherwise chain-qualified rows for incoherent citation
grounding. Reproduce with `python scripts/build_reasoning_targets.py --validate`; add
`--allow-incoherent-citations` only for legacy comparisons. Custom `--out` runs write a side manifest next
to the selected output and record both paths, preserving provenance for ad hoc reasoning-target arms.

### Pre-train quality audit (anti-overfit / anti-shortcut)

The gates above filter *candidates*; one more pass audits the **assembled splits** before the GPU run, so
the ways a distilled safety judge can go wrong are caught in the data rather than discovered after
training (`scripts/audit_training_quality.py`, offline + deterministic, writes
`reports/training/quality_audit.json`):

- **Overfitting → cross-split leakage.** Any held-out prompt with a SimHash near-duplicate (Hamming ≤ 3)
  in train; a non-zero count means the generalisation diagnostic is measuring memorisation. *Live: 0 / 78
  held-out, both SFT and DPO.*
- **False pattern → length shortcut.** DPO `chosen` vs `rejected` length: a large `chosen ≫ rejected`
  ratio teaches "longer = preferred" instead of "grounded = preferred". *Live: 1.19× (55.1 % of pairs
  have the longer `chosen`) — essentially no length confound, confirming the `max_length` fix holds.*
- **Jurisdiction shortcut → corridor concentration.** Per-typology corridor spread, flagging only **dense**
  typologies (≥ 10 rows) whose rows all sit in a single corridor — sparse and attack-*style* categories
  can't span corridors meaningfully, so they are reported, not flagged. The universal layer the model must
  learn is the **ILO-11 indicator**, which the targets carry regardless of corridor; this guards against a
  corridor silently standing in for an indicator. The audit also emits a metadata-only
  `corridor_expansion_queue` with row counts, observed corridors, a `coverage_gap` label
  (`single_specific_corridor` or `generic_corridor_only`), category-specific target corridors when the
  prompt metadata contains them, a `suggestion_source` fallback label, and a privacy scan, so the
  discovery flywheel can widen coverage without copying raw prompts or answers. It also derives
  metadata-only `corridor_expansion_tasks` with safe task IDs, target corridor origin/destination fields,
  required metadata fields, scenario constraints, acceptance checks, and a separate privacy scan.
  `scripts/build_corridor_expansion_plan.py` turns those tasks into
  `reports/training/corridor_expansion_plan.json` plus a side manifest, and refuses to write if the source
  audit did not prove metadata-only/privacy-clean status. *Live: 5 dense
  generic-corridor-only typologies, with 5 metadata-only expansion queue entries and 25 metadata-only
  curation tasks currently using the
  `global_prompt_metadata` fallback because those categories are still tagged only as `various` — not a
  training blocker, but the next coverage queue to work down.*
- **Fragile-fact memorization.** Gold replies asserting volatile specifics. Phone/hotline numbers are the
  hard gate (must be ~0 — those belong in tools/RAG, and the privacy scrub should remove them); fee amounts
  and dates are informational, since a statute's enactment year (e.g. *Palermo Protocol, 2000*) is a
  **stable** fact, not a fragile one. *Live: 0 phone-like in 2,632 gold replies; the money/date hits are
  dominated by stable statute years and in-scenario amounts.*
- **Citation relevance.** Gold replies must not teach real-but-irrelevant legal grounding. The audit runs
  the same indicator-to-convention coherence check used by `palermo_screening.py` and stores only
  structured metadata (source split, prompt ID, category, corridor, mapped signals, cited conventions,
  expected conventions), never raw answer text. It also emits a metadata-only `repair_queue` with
  `repair_queue_privacy_scan.ok=true`, so the next data pass can target the exact rows to re-ground rather
  than chasing anonymous list indexes if the upstream gate regresses. *Live: 0 incoherent rows among 1,096
  checkable gold replies (0.0%), with an empty metadata-only repair queue; reproduce with
  `python scripts/audit_training_quality.py --stdout`.*

### The reasoning contract — a way of thinking, enforced

The chain gate above curates training *targets*; `scripts/reasoning_contract.py` turns the same chain into
an enforceable **contract** — a deterministic spec of the *way of thinking* a Gemma 4 reasoning LoRA should
internalise (a procedure, not facts), checkable three ways from one definition:

- **as a training filter** — keep only traces that satisfy the contract (strict: all four steps, in order,
  with a *valid and indicator-relevant* non-hallucinated citation, and no phone-like fragile fact in the reasoning);
- **as inference enforcement** — parse the model's thinking trace, verify each step, and emit a **repair
  directive** naming exactly what to fix when a step is missing or wrong (a verify-and-repair loop);
- **as a judge-independent eval metric** — the share of replies whose chain of thought satisfies the
  contract, reported alongside the LLM-panel lift.

Run over the 960 citation-relevant train-split gold reasoning traces, **30.4 %** satisfy the strict four-step
contract and **96.8 %** the relaxed three-step form; step presence is indicator 99.9 % / resources 99.4 % /
statute 57.0 % / action 75.6 %, and **57.0 %** pass the valid-and-indicator-relevant citation
check. So one contract both *defines* the way of thinking a reasoning LoRA would be trained on and
*measures* that the statute, concrete-action, and citation-relevance links are where the chain still needs
reinforcement before a strict-contract fine-tune. This is the principled form of "a model as a way of
thinking": the LoRA stores the *procedure* (jurisdiction-independent, fragile-fact-free), and the contract
enforces it at train time, at inference, and in evaluation. Reproduce with
`python scripts/reasoning_contract.py` and `python scripts/reasoning_contract.py --min-steps 3`.
For stricter advice-completeness checks, add `--require-core-remedies`: this preserves the base
indicator/statute/action/resources contract but also requires the mandatory money-remedy and non-punishment
guarantees when the trace itself raises exploitation, forced labour, wage harm, document control, or
recruitment-fee debt. Use this mode for remedy-focused variants and repair queues rather than for comparing
older strict-contract rates.

**Sharper preference data from the contract.** The contract also generates hard-negative DPO pairs
(`scripts/build_contract_dpo.py`): `chosen` = a contract-satisfying gold trace, `rejected` = the *same*
trace with only the statute (or action) sentence deleted — verified gone. The single difference is the link
the model must not drop, isolating the two weak links into clean minimal pairs (292 eligible gold traces →
**581 unique hard negatives**: 292 statute, 289 action, after 3 duplicate pairs are skipped). The
rejected is deletion-only, so no fabricated content enters training — a much sharper signal than
chosen=harnessed / rejected=baseline. Custom `--out` runs write a side manifest next to the selected DPO
output and record both paths. The builder now fails closed with `safe_to_train=false` if no eligible gold
trace yields at least one verified hard-negative pair, and the CLI returns non-zero / refuses to write unsafe
training JSONL rather than publishing an empty contract arm. The manifest also records
`pair_integrity_issues` from a second pass over every emitted pair: `chosen` must still satisfy the contract,
`rejected` must be shorter, different, and missing the claimed statute/action link, and the rejected chain
score must drop. The GPU comparison arm can select this preference set with
`python scripts/training_engine.py --with-gpu --dpo-variant contract`;
`train_lift_distill.py --validate`
requires the adjacent contract-DPO manifest whenever contract-ablation rows are selected, then checks that
the loaded rows all carry `source=contract_ablation`, include `ablated_link`, and match the manifest's
link-count summary, `pairs>0`, empty `pair_integrity_issues`, empty `contract_manifest_issues`, and the same
text-level ablation properties before a direct contract-DPO GPU run can proceed.

**Mixed DPO comparison arm.** `scripts/build_dpo_mix_variant.py` stages the pragmatic training arm that keeps
the broad harnessed-vs-baseline preference pairs and adds the strict contract-ablation pairs in a separate
`reports/training/dpo_train_plus_contract.jsonl` file. It does not mutate the organized base DPO split. The
current local run writes **1,897** pairs (1,316 base + 581 contract). The side manifest records base rows,
contract rows, duplicate-pair checks, contract row provenance checks, contract link counts,
`safe_to_train`, the upstream
`organize_manifest.json` base-DPO count, and the upstream contract-DPO manifest summary; the builder
refuses to write if either source manifest is missing, unsafe, malformed, path-mismatched, count-mismatched,
or if contract rows do not already carry `source=contract_ablation` with ablated-link counts matching the
upstream contract-DPO manifest. Select it with
`python scripts/training_engine.py --with-gpu --dpo-variant base_plus_contract`; direct trainer validation
also requires the adjacent mixed-DPO manifest, rejects any recorded source-manifest issues, and cross-checks
the embedded source summaries for base-DPO train counts, contract-DPO safety, pair counts, link counts, and
duplicate-pair status. It also verifies every loaded mixed-DPO row carries `dpo_variant.name =
base_plus_contract`, a valid `base` or `contract` component, and contract components line up with
`source=contract_ablation` and the mixed manifest's `by_ablated_link` counts before a GPU run can proceed;
the same text-level ablation checks run over the loaded contract component rows. The embedded contract-DPO
source summary must also have no `pair_integrity_issues` or `contract_manifest_issues`.

**Repair queue for the next data pass.** `scripts/build_reasoning_gap_queue.py` turns the same contract
failures into `reports/training/reasoning_gap_queue.json`: a metadata-only queue of prompt IDs, categories,
missing links, verifier booleans, citation metadata, Palermo/screening metadata, and generic repair hints.
It deliberately does **not** copy raw prompts, assistant answers, traces, phone numbers, or case text into
the report. The builder now recursively scans the generated queue and fails closed if forbidden training
fields or email/phone/long-digit-like strings appear. The queue manifest also records
`queue_manifest_issues`, `safe_for_repair`, and `actionable_for_repair`, so downstream repair steps can
distinguish an empty-but-safe queue from a queue that is unsafe to consume. The current train-split run
queues **630** repair targets from the 960 reasoning traces:
**408** missing statute and **222** missing action. Reproduce with
`python scripts/build_reasoning_gap_queue.py --validate`. For a remedy-focused next pass,
`python scripts/build_reasoning_gap_queue.py --validate --require-core-remedies` preserves the same
metadata-only privacy boundary and queues **933** targets, including core remedy omissions
(`non_punishment`, `compensation_damages`, `fee_refund`, and `unpaid_wage_recovery`) as structured
identifiers rather than raw answer text.

**Proposed deterministic repairs.** `scripts/build_reasoning_repairs.py` consumes that queue and writes a
separate gitignored proposal set, `reports/training/reasoning_repaired_sft.jsonl`, plus a metadata-only
manifest. It appends only generic statute/action repair sentences, then keeps a row only if the repaired
assistant answer satisfies the strict reasoning contract. The current default run emits **613** verified
repair rows (**398** statute additions, **215** action additions); the remaining queued rows stay in the
queue for a richer data pass, with the manifest recording the verification and deterministic-repair skip
reasons. The manifest is written beside the selected `--out` file and records
that output path, so custom repair proposal runs remain traceable. The repair CLI also refuses to write
training rows unless the source gap queue includes a matching metadata-only manifest with a passing privacy
scan, empty queue-manifest issues, and `safe_for_repair=true`, preventing ad hoc raw-text queues or
hand-edited unsafe manifests from bypassing the privacy boundary. The repair manifest now records
`repair_manifest_issues` and fails closed if the source queue is unsafe, empty, or every queued row is
skipped so no verified repaired training rows are produced. Reproduce with
`python scripts/build_reasoning_repairs.py --validate`. For the remedy-focused queue, validate with
`python scripts/build_reasoning_repairs.py --queue <core-queue.json> --require-core-remedies --validate`;
the current core-remedy validation emits **262** strict core-remedy repairs from the **933** queued targets
using only generic compensation, non-punishment, and unpaid-wage-recovery sentences. A core-remedy repair
manifest carries `require_core_remedies=true`, `by_added_core_remedy`, and source-queue
`by_core_missing` counts so downstream SFT staging can distinguish remedy-only additions from the default
statute/action repair arm.

**Non-duplicating repaired SFT arm.** `scripts/build_reasoning_sft_variant.py` stages those verified repairs
as a separate training variant, `reports/training/sft_train_reasoning_repaired.jsonl`, by replacing matching
base train rows by `prompt_id` instead of appending duplicate targets. The base split is not mutated. The
current default run keeps the train split at **1,316** rows and replaces **613** with strict-contract
repairs. Train the comparison arm with
`python scripts/training_engine.py --with-gpu --sft-variant reasoning_repaired` or directly with
`python scripts/train_lift_distill.py --sft reports/training/sft_train_reasoning_repaired.jsonl --dpo reports/training/dpo_train.jsonl`.
The variant manifest now fails closed with `safe_to_train=false` if prompt IDs are missing or duplicated,
if repaired rows cannot be matched uniquely back to the organized train split, if any repaired input row
lacks repair provenance metadata, or if the repaired-row source manifest is missing, unsafe,
count-mismatched, path-mismatched, tied to a failed gap-queue privacy scan, or reports non-empty
`repair_manifest_issues`. The manifest is written beside the selected SFT output path, and
`train_lift_distill.py --validate`
requires it whenever variant rows are present; it also checks the variant name, output row count, prompt-ID
count, selected SFT path, repaired-row counts, and the embedded source-repair summary's `safe_to_train`,
metadata-only, privacy-scan, queue-coverage, and empty `repair_manifest_issues` fields, so direct GPU
launches inherit the same safety check instead of trusting a hand-edited variant manifest. It also verifies
the loaded replacement rows carry `sft_variant.replacement=true`, matching prompt IDs,
`reasoning_repair.source=reasoning_gap_queue`, and at least one validated repair item. Default
statute/action rows still need non-empty `reasoning_repair.added_links`; remedy-only rows may instead
carry non-empty `reasoning_repair.added_core_remedies`, but only when the embedded repair manifest and its
source queue both prove `require_core_remedies=true`. The variant builder and trainer now share the same
safe generated prompt-ID rule, including generated IDs with spaces while rejecting contact/path-shaped IDs.
The remedy-focused comparison arm is selectable through
`python scripts/training_engine.py --with-gpu --sft-variant reasoning_repaired_core`; the engine writes the
separate `reports/training/reasoning_gap_queue_core.json`,
`reports/training/reasoning_repaired_core_sft.jsonl`, and
`reports/training/sft_train_reasoning_repaired_core.jsonl` artifacts rather than overwriting the default
repair arm. For the current core-remedy run, the validated command
`python scripts/build_reasoning_sft_variant.py --repaired reports/training/reasoning_repaired_core_sft.jsonl --out reports/training/sft_train_reasoning_repaired_core.jsonl --validate`
reports **262** replacements, `safe_to_train=true`, and core additions
(`compensation_damages`, `non_punishment`, `unpaid_wage_recovery`); the follow-up
`python scripts/train_lift_distill.py --validate --sft reports/training/sft_train_reasoning_repaired_core.jsonl --dpo reports/training/dpo_train.jsonl`
passes the CPU-safe data gate.

**Legal-rigour enrichment (Palermo + screening instruments).** The contract's analysis is strengthened
from "names an indicator" toward what a trained screener performs: the **Palermo Act–Means–Purpose triad**
(UN Protocol Art. 3 — an *act* by a *means* for an exploitative *purpose*; for minors the means element is
not required, Art. 3(c)) plus the operational **screening checklist** (IOM / ILO / Vera TVIT / Polaris:
document retention, free-to-leave, wage withholding, debt, threats, isolation, excessive hours, contract
substitution, recruitment fees). `scripts/palermo_screening.py` detects these deterministically and
`verify_reasoning(…, require_triad=True)` makes the triad an enforceable clause. Over the 960 train-split
gold traces the reasoning surfaces the act **99.0 %** and the purpose **99.1 %** of the time but the
**means only 89.6 %** (triad-complete 88.4 %) — the *means* ("how": deception, coercion, abuse of vulnerability) is the
weak leg, the Palermo analogue of the weak statute/action links and a concrete target for the next data pass.

## 3. Findings from running the pipeline

Distilling the live benchmark panel (≈3,845 candidate pairs):

- **2,602** vetted SFT + DPO pairs selected (target ≥ 70, lift ≥ 20); 1 dropped for fabricated citation
  problems and 81 dropped for real-but-irrelevant ILO convention citations.
- **The measured lift is grounding-driven, not refusal-inflation.** Of the selected pairs, 100% carry a
  real grounding-delta, the median is **≈ +32.7 / 60** (min 3.5, max 60), and **zero** are
  refusal-only-lift. In other words, where the harness helps, it helps by adding indicators, citations,
  and resources — exactly what we want a model to internalise.
- **The reasoning chain is uneven.** Of 1,316 organized train targets, 960 carry ≥ 3 / 4 chain links with
  relevant citations; the links are present at **indicator 99.8% · resources 97.3% · statute 42.5% · action 56.2%**.
  So the distilled targets are
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
and `scripts/build_model_card.py` renders a publishable model card from that record. The training engine
now writes the selected SFT/DPO arms, SFT/DPO input paths, staged contract-DPO paths, mixed-DPO paths,
repaired-variant manifest path, selected reasoning gap queue / repaired-row source paths, the quality-audit
path, the corridor expansion curation-plan path, and sha256/byte fingerprints for selected files,
manifests, repair source artifacts, `quality_audit.json`, and `corridor_expansion_plan.json` into the
registry `artifacts` payload, so `reasoning_repaired`,
`reasoning_repaired_core`, `contract`, and `base_plus_contract` comparison runs are traceable back to the
exact variant files, repair source files, manifests, and pre-train audit evidence instead of only the base
data manifest. The registry artifacts and
engine run plan also capture a small metadata-only quality-audit summary (`clean`, risk flags, leakage
counts, corridor queue/task count and privacy status, citation repair count/privacy status, and phone-like hit
count), so a flagged data run leaves reviewable evidence without copying raw prompts or answers. The ledger
now validates structured `artifact_files` entries when they are supplied: file paths must be present, and
hash/byte pairs must be either complete (`sha256` = 64 hex chars plus non-negative byte count) or explicitly
empty for not-yet-materialized optional artifacts. The
model-card renderer includes those artifact fingerprints with repo-relative paths, renders the selected
SFT/DPO arms plus reasoning-repair mode, and renders the metadata-only quality-audit summary, so the public
card stays reproducible without publishing local workstation paths or raw training text. Before publishing
or citing a card, run
`python scripts/finetune_registry.py verify <model_id>` to re-hash the currently available files and fail
on missing or mismatched artifacts, or render with
`python scripts/build_model_card.py --model-id <model_id> --require-verified-artifacts` so card generation
itself refuses stale/missing artifact evidence. For the single pre-publication check, run
`python scripts/validate_training_provenance.py --model-id <model_id>`; it bundles registry fingerprint
verification, quality-audit summary consistency against the recorded `quality_audit.json`,
`corridor_expansion_plan.json` manifest/source-audit/privacy consistency, verified model-card rendering,
and selected SFT/DPO trainer validation into one CPU-safe gate. The
register step refreshes those fingerprints after the offline builders run, so the ledger captures the
current generated artifacts rather than the pre-run plan. The whole pipeline
runs as one command — `scripts/training_engine.py` (distill → organize → reason → contract → dpo_mix → gaps → repair → variant
→ audit → corridor_plan → [train → evaluate, GPU] → register) — which on a CPU host produces the training data, repair
queue, hard-negative DPO pairs, mixed-DPO arm, repaired SFT proposal, variant manifest, corridor curation
plan, and a provenance row while cleanly skipping the GPU steps. The current offline DAG inserts
`corridor_plan` immediately after `audit`, before any GPU train/evaluate step.
Use `--sft-variant reasoning_repaired_core` for the core-remedy repair queue and SFT comparison arm.
So any published adapter traces back to the exact data and code that produced it.

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
