# Goal command 14 - GPT-5.6 SOL training-data and Kaggle flywheel

> Created 2026-07-15. Paste the block below into GPT-5.6 SOL, GPT-style
> coding agents, Claude Code, Codex, or another agentic coding model when the
> goal is to keep improving the DueCare training-data, evaluation, Kaggle, and
> notebook publication pipeline without losing the repository's safety gates.

This command is intentionally broader than a single implementation ticket. It
is a continuation packet: it tells the next agent what to inspect, what to
build, what not to publish, how to run the Ollama and response-data flywheels,
how to create Kaggle-ready datasets and notebooks, and what evidence must exist
before claiming that anything is ready.

Use it when the immediate objective is:

- turn existing prompt/response/grade data into SFT, preference, reward, and
  evaluation datasets;
- grow a much larger multi-perspective synthetic corpus;
- keep Ollama/local generation and one-dimension grading loops running in
  comparable lanes;
- package private Kaggle datasets and notebooks for review;
- prepare, but not blindly public-publish, advanced training artifacts.

Related source documents:

- [Training data and fine-tuning](../../training_and_finetuning.md)
- [Goal command series](README.md)
- [Codex handoff packages](../README.md)

## Copy-paste master prompt

```text
You are working in C:\Users\amare\OneDrive\Documents\gemma4_comp.

You are a senior coding agent continuing the DueCare / Gemma training-data
flywheel. Work end to end. Do not stop at explanation. Inspect the repository,
make scoped improvements, run the relevant validators, and report exact
evidence. Preserve user work and generated runtime state that is unrelated to
your changes.

PRIMARY OUTCOME

Continue improving the full training-data, grading, Kaggle, and notebook
pipeline so the project can publish defensible interim and advanced datasets
for fine-tuning models such as Gemma, while keeping all training/evaluation
claims reproducible.

The target deliverables are:

1. A larger, validated local training corpus with tens of thousands of text
   bodies where feasible.
2. A measured-response corpus built from existing response and grading data.
3. Separate SFT, preference/DPO, reward-label, negative-only, validation, and
   test artifacts.
4. Kaggle-ready dataset packages with manifests, dataset cards, schemas, and
   checksums.
5. Kaggle notebooks for integrity checks, dataset exploration, Gemma/LoRA
   training plans, smoke tests, preference/DPO formatting, and four-arm
   evaluation.
6. Updated docs and public-facing context only after artifacts are actually
   validated.
7. A clear final report with changed files, dataset counts, manifest hashes,
   validation results, publication status, and remaining blockers.

READ FIRST

Read these files before acting, skipping only files that are absent:

1. AGENTS.md
2. CLAUDE.md
3. PROJECT_BIBLE.md
4. docs/training_and_finetuning.md
5. docs/finetuning_data_strategy.md
6. docs/research/training_methodology.md
7. docs/research/training_regimes_and_systems.md
8. docs/codex/README.md
9. docs/codex/goal_commands/README.md
10. docs/codex/goal_commands/13_project_bible_continuation.md
11. kaggle/_INDEX.md
12. kaggle/shared-datasets/training-data/README.md

Then inspect current state. Do not trust old handoff summaries or saved state
files as current truth. Verify with live files and commands.

FIRST CURRENT-STATE CHECKS

Run or inspect the equivalent of:

- git status --short
- python scripts/validate_public_surface.py
- python -m pytest packages --collect-only -q
- python scripts/validate_main_kaggle_kernels.py
- py -3.12 scripts/validate_kaggle_page_sources.py

Also inspect:

- reports/
- reports/kaggle_publish/
- reports/multiperspective_training/
- reports/response_preference_candidates/
- data/generated_prompts/
- data/rated_prompts/
- data/remixed_prompts/
- configs/duecare/benchmarks/
- scripts/build_*training*.py
- scripts/build_*kaggle*.py
- tests/test_build_*training*.py
- tests/test_build_*kaggle*.py
- packages/duecare-llm-chat/src/duecare/chat/training_contract.py
- packages/duecare-llm-chat/tests/test_training_contract.py

If a referenced script does not exist, search with rg and use the nearest
current implementation. Do not invent success.

NON-NEGOTIABLE SAFETY RULES

1. Never commit or publish raw PII, real worker contact details, identity
   documents, private case files, private logs, Kaggle tokens, API keys, or
   unredacted credentials.
2. Do not echo secrets into final reports or dataset cards. If credentials are
   found, report category, path, and remediation status without revealing the
   secret value.
3. Do not train on or publish private hidden chain-of-thought. Use final
   answers, visible rationale summaries, reviewable decision scaffolds,
   rubric notes, citation traces, and action plans.
4. Do not hardcode volatile hotlines, fee caps, wage rules, URLs, office names,
   legal claims, or contact details into model targets unless backed by
   versioned knowledge objects.
5. Do not mix providers, endpoints, or model revisions in comparable findings.
   Keep model ID, endpoint, prompt version, rubric version, harness version,
   timestamp, and manifest hash isolated.
6. Do not start public Kaggle publication without explicit final approval.
   Private Kaggle staging is allowed only after the privacy, license,
   checksum, and notebook gates pass.
7. Generated report directories are packaging material. Do not commit large
   generated outputs unless the repository instructions explicitly require it.
8. Preserve unrelated dirty files. Stage only the files you intentionally
   changed.

LANGUAGE TO USE IN PUBLIC DATASETS

Use:

- visible rationale
- visible decision scaffold
- reviewed reasoning summary
- rubric rationale
- action trace
- citation trace
- evidence map
- uncertainty note

Do not claim:

- hidden chain-of-thought extraction
- provider-private reasoning retrieval
- raw internal thoughts
- guaranteed legal advice
- production adapter release unless weights and four-arm evaluation are
  actually published and validated

CORE FLYWHEEL

Repeat the following loop until a validated private Kaggle package and notebook
set exists, or until a genuine blocker prevents further safe progress.

STEP 1 - INVENTORY

Build or refresh an inventory of all available prompt, response, grade, and
synthetic-training data.

Separate records into:

- prompt-only rows
- response-only rows
- prompt-response rows
- graded rows
- ungraded rows
- SFT candidates
- preference/DPO candidates
- reward-label candidates
- rejected/quarantined rows
- private train-only rows
- publishable rows

For every inventory output, include:

- source file
- row count
- schema family
- model/provider if known
- prompt/rubric/harness version if known
- privacy status
- training eligibility
- publication eligibility
- reason if rejected or quarantined

STEP 2 - NORMALIZE

Normalize eligible data into stable schemas:

- SFT JSONL
- preference/DPO JSONL
- reward-label JSONL
- evaluation prompt JSONL
- quarantine JSON
- candidate manifest
- release manifest

Every trainable row should carry enough provenance to reproduce or reject it:

- row_id
- prompt_id or synthetic graph ID
- source lineage
- model ID and revision if available
- endpoint/provider if available
- generator script and commit if available
- prompt pack version
- rubric version
- harness version
- split assignment
- privacy result
- license/allowed-use status
- row SHA-256

STEP 3 - GENERATE MULTI-PERSPECTIVE SYNTHETIC DATA

Grow the deterministic synthetic corpus across role, time, evidence, and
jurisdiction axes. Use existing builders where available, especially:

- scripts/build_multiperspective_training_bundle.py
- scripts/build_large_multiperspective_training_bundle.py
- scripts/build_kaggle_proof_training_bundle.py
- scripts/build_large_kaggle_training_collection.py

The synthetic design should cover perspectives such as:

- worker
- newly arrived worker
- family member
- third-party observer
- recruiter
- employer or supervisor
- NGO caseworker
- regulator
- origin-country official
- destination-country official
- legal scholar
- journalist or researcher
- new intake worker
- post-incident reviewer

Vary journey stage:

- before recruitment
- recruitment
- contract signing
- pre-departure
- travel
- arrival
- employment
- wage or document dispute
- help-seeking
- complaint filing
- return
- remediation and long-term follow-up

Vary temporal lens:

- what could be known at the time
- what later evidence changed
- what a third party could infer
- what remains unknown

Vary evidence state:

- direct record
- worker statement
- employer/recruiter statement
- public-source record
- regulator record
- conflicting record
- missing record
- later-corroborated record

Every row should teach bounded, consent-preserving, cross-jurisdiction,
cross-temporal reasoning without baking volatile current facts into weights.

STEP 4 - USE OLLAMA FOR CANDIDATE EXPANSION

Use local Ollama models for candidate generation, adversarial rewriting,
protective answer generation, and judging when the repo has an approved script
and seed set. Prefer existing tooling, especially:

- scripts/ollama_adversarial_flywheel.py
- scripts/harness_lift_local.py
- scripts/harness_lift_opus_judge.py
- scripts/applicability_judge.py
- scripts/prompt_remixer.py

Keep Ollama outputs candidate-only until downstream gates pass. Record:

- generator model
- adversary model
- judge model
- Ollama version if available
- prompt seed file
- output directory
- exact command
- accepted rows
- quarantined rows
- rejection reasons

Do not use additional endpoints to speed up comparable grading unless the lane
is explicitly labeled as mixed-provider or exploratory. If extra endpoints are
used, keep their outputs separate from the main comparable board.

STEP 5 - JUDGE AND GRADE

Continue one-dimension-per-prompt grading where that is the active comparable
lane. Do not collapse many grading dimensions into one opaque judgment if the
current experiment requires atomic dimensions.

For each grading run, preserve:

- prompt ID
- dimension ID
- answer under review
- judge model/provider/revision
- rubric version
- bounded grade
- visible judge rationale or rubric note
- pass/fail flags
- quarantine reason if not usable

Reject or quarantine:

- incomplete grades
- unbounded rationales
- unsupported citations
- volatile resource claims without versioned binding
- raw PII
- prompt or target duplicates that break split isolation
- low-grounding rows
- rows where redaction would alter the graded target

STEP 6 - BUILD TRAINING RELEASE CANDIDATES

Create separate release candidates for:

- high-confidence positive SFT
- negative-only examples
- mixed contrastive training
- DPO/preference pairs
- reward-label rows
- synthetic multi-perspective corpus
- measured-response corpus from real experiment outputs

Each candidate must have:

- train/validation/test split
- held-out lineage or mechanism isolation
- duplicate and near-duplicate checks
- target-overlap isolation
- source/rights audit
- privacy audit
- quality audit
- manifest hash
- safe_to_train flag
- safe_to_publish flag
- clear reason if not publishable

STEP 7 - PACKAGE KAGGLE DATASETS

Use existing package builders where available:

- scripts/build_kaggle_training_release.py
- scripts/build_kaggle_interim_collection.py
- scripts/build_large_kaggle_training_collection.py
- scripts/build_response_kaggle_collection.py

Every Kaggle package should contain:

- dataset-metadata.json
- README.md or dataset card
- manifest JSON
- schema documentation
- train JSONL
- validation JSONL
- test JSONL
- preference/DPO JSONL where applicable
- reward-label JSONL where applicable
- quarantine or rejection summary without raw unsafe text
- SHA-256 checksums
- exact source-manifest reference
- publication status

If Kaggle upload control files are present only for upload mechanics, do not
mistakenly include them in notebook data discovery manifests. Notebooks should
discover the actual dataset payload, not depend on Kaggle mounting
dataset-metadata.json as a normal input file.

STEP 8 - BUILD OR UPDATE KAGGLE NOTEBOOKS

Create or update notebooks for:

- dataset integrity and manifest verification
- schema exploration
- training plan generation
- Gemma LoRA or QLoRA smoke setup
- SFT formatting
- preference/DPO formatting
- reward-label formatting
- four-arm evaluation plan
- positive-only vs negative-only vs mixed training comparison

Notebook requirements:

- CPU-safe default path
- GPU training disabled by default unless explicitly approved
- clear dataset discovery
- manifest and checksum verification before loading rows
- no hidden chain-of-thought claims
- no public claim that an adapter was trained unless the run actually trained
  one and the artifacts were inspected
- outputs should include plans and manifests even when training is disabled

Check Kaggle GPU/TPU quota before proposing live GPU execution. If quota is
zero or insufficient, produce CPU integrity and training-plan notebooks first.

STEP 9 - UPDATE DOCUMENTATION AND PUBLIC CONTEXT

Only after the artifacts pass validation, update relevant docs and public
surfaces. Candidate files include:

- docs/training_and_finetuning.md
- docs/finetuning_data_strategy.md
- docs/research/training_methodology.md
- docs/research/training_regimes_and_systems.md
- kaggle/_INDEX.md
- kaggle/shared-datasets/training-data/README.md
- README.md
- docs/REPO_LAYOUT.md
- docs/FILE_PURPOSE_GUIDE.md
- website or Render-facing pages if present and in scope

Every public claim should be dated and tied to a command, manifest, Kaggle slug,
notebook slug, or artifact hash.

STEP 10 - VALIDATE

Run the smallest focused tests for changed builders first, then the public
surface gates. Typical validation set:

- python -m pytest tests/test_build_large_multiperspective_training_bundle.py -q
- python -m pytest tests/test_build_large_kaggle_training_collection.py -q
- python -m pytest tests/test_build_response_preference_bundle.py -q
- python -m pytest tests/test_build_response_kaggle_collection.py -q
- python -m pytest packages/duecare-llm-chat/tests/test_training_contract.py -q
- python scripts/validate_public_surface.py
- python -m pytest packages --collect-only -q
- python scripts/validate_main_kaggle_kernels.py
- py -3.12 scripts/validate_kaggle_page_sources.py
- git diff --check

If any command fails, fix the cause or report the blocker precisely. Do not
claim done with a failed relevant gate.

STEP 11 - PRIVATE STAGING AND PUBLICATION BOUNDARY

Private Kaggle staging can happen only after:

- privacy scan passes
- license/source audit is clean or explicitly train-only
- manifests are reproducible
- notebooks validate against the packaged dataset
- dataset card states the limits clearly

Public Kaggle publication requires explicit final approval. Before asking for
approval, provide:

- dataset slug
- notebook slug
- package path
- manifest hash
- row counts by split and schema
- privacy result
- source/license result
- validation commands and results
- known limitations
- whether GPU training was actually run
- whether any adapter was actually produced

WORKSTREAM PRIORITY

Use this priority order unless live repo evidence shows a higher-risk blocker:

1. Harden and materialize the measured-response bundle from existing response
   and grading data.
2. Package that measured-response bundle into a private Kaggle-ready dataset.
3. Revalidate or rebuild the large multi-perspective synthetic corpus.
4. Rebuild the large Kaggle training collection so notebooks discover payload
   files correctly.
5. Add or update notebooks for integrity, exploration, training plan, and
   smoke testing.
6. Expand the Ollama loop only after the current artifacts are inventory-clean.
7. Update public docs and website/Render surfaces only from validated artifact
   evidence.

PREFERRED COMMAND SHAPES

Use PowerShell-compatible commands. Examples:

python scripts/build_response_preference_bundle.py build `
  --output-dir reports/response_preference_candidates/measured_response_v2

python scripts/build_response_kaggle_collection.py `
  --source-manifest reports/response_preference_candidates/measured_response_v2/candidate-manifest.json `
  --force

python scripts/build_large_multiperspective_training_bundle.py `
  --output-dir reports/multiperspective_training/large_candidate_next

python scripts/build_large_kaggle_training_collection.py `
  --source-manifest reports/multiperspective_training/large_candidate_next/candidate-manifest.json `
  --force

python -m pytest tests/test_build_response_preference_bundle.py `
  tests/test_build_response_kaggle_collection.py `
  tests/test_build_large_multiperspective_training_bundle.py `
  tests/test_build_large_kaggle_training_collection.py `
  packages/duecare-llm-chat/tests/test_training_contract.py `
  -q -p no:cacheprovider

python scripts/validate_public_surface.py
python -m pytest packages --collect-only -q
python scripts/validate_main_kaggle_kernels.py
py -3.12 scripts/validate_kaggle_page_sources.py
git diff --check

Do not assume these exact scripts or paths are current. Inspect first and adapt
to the current repo.

ACCEPTANCE CRITERIA

The loop is successful when all of the following are true:

1. There is a current inventory of available response, prompt, grade, and
   synthetic data.
2. There is at least one large local training candidate with explicit
   safe_to_train and safe_to_publish flags.
3. There is at least one Kaggle-ready private dataset package with manifest,
   checksums, schema docs, dataset card, and split files.
4. There is at least one Kaggle-ready notebook that verifies the dataset before
   using it.
5. Validation commands relevant to changed files pass, or failures are
   precisely documented with next fixes.
6. Public docs do not overclaim: they distinguish candidate, private staged,
   public ready, trained adapter, and evaluated adapter.
7. No raw PII, credentials, private chain-of-thought, private logs, or unsafe
   volatile facts are published.

FINAL REPORT FORMAT

When you stop, report:

- changed files
- generated local artifact paths
- Kaggle package paths
- Kaggle dataset slugs if staged
- Kaggle notebook slugs if staged
- row counts by schema and split
- accepted/rejected/quarantined counts
- top rejection reasons
- manifest hashes
- safe_to_train and safe_to_publish status
- validation commands and exact results
- whether Ollama was used
- whether GPU training was run
- whether any adapter was produced
- docs or website pages updated
- remaining blockers
- next 10 concrete actions

STOP CONDITIONS

Stop only for:

- explicit destructive action approval needed
- public publication approval needed
- missing credentials for an external upload
- repeated validation blocker after real fix attempts
- unresolved privacy/license issue
- user interruption that changes scope

Do not stop merely because the work is large. Complete the next safe,
validated slice and keep going.
```

## Short starter version

Use this shorter block when the target agent has limited context length:

```text
In C:\Users\amare\OneDrive\Documents\gemma4_comp, continue the DueCare
training-data and Kaggle flywheel. Read AGENTS.md and docs/training_and_finetuning.md first.
Inventory all prompt/response/grade/synthetic data; normalize into SFT,
preference/DPO, reward-label, evaluation, and quarantine schemas; build or
refresh large multi-perspective synthetic and measured-response candidates;
package private Kaggle-ready datasets and notebooks; validate with focused
tests plus validate_public_surface, pytest collect-only, validate_main_kaggle_kernels,
validate_kaggle_page_sources, and git diff --check. Never publish raw PII,
credentials, private case files, private logs, hidden chain-of-thought, or
volatile legal/resource facts without versioned sources. Use visible rationale
summaries and decision scaffolds instead. Public Kaggle publication requires
explicit final approval. Final report must include changed files, artifact
paths, row counts, manifest hashes, safe_to_train/safe_to_publish status,
validation results, Kaggle slugs if staged, Ollama/GPU usage, and remaining
blockers.
```

## Operator notes

- This pack is meant to keep an agent moving through implementation slices,
  not merely produce a strategy memo.
- If a future agent has live Kaggle credentials and the artifacts validate, it
  may stage private datasets/notebooks. It must not public-publish without a
  fresh approval.
- If the agent finds a stronger current script than the examples above, it
  should use the current script and update this file later.
- If generated counts differ from old reports, the live manifest wins.
