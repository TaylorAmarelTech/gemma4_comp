# DueCare Roadmap - forward plan

> Consolidated, cross-cutting roadmap for improvements, extensibility, agents,
> community, and knowledge refresh. This is the forward-looking plan; the
> historical/topic docs (`docs/integration_plan.md`, `docs/codex/improvement_roadmap_2026_05_29.md`,
> `docs/research/benchmark_roadmap.md`) remain as provenance. Priorities: P0 (now),
> P1 (next), P2 (later). Every item is grounded in the current state below.

## Current state (as of this plan)

- **Benchmark:** harness-lift (baseline / harness_core / harness_full), 3-model judge panel,
  5 A-E rubric dimensions; headline +40.7/100 on gemma4:31b over 7,953 paired prompts,
  99.8% improved, holds across every model tested; fact-checked (20/20 headline claims reconcile).
- **New anchor:** `duecare.kit.verify` - a deterministic, un-gameable checker that corroborates the
  lift (+1.03/5; legal-citation -> 100%, resources +35pts; 693 wins / 46 losses on 1,087 real rows).
- **Public surface:** 15 live Kaggle notebooks (analysis + applied use cases) + 6 datasets + the
  `duecare-llm-kit` package (importable engine/viz + HTML report generator + corpus exporter) + the
  website (`duecare-ai.com`) with a standardized story and a Data page.
- **Flywheel:** an Ollama-cloud self-improvement loop grading toward the full 78,719-prompt registry
  (currently parked on an external weekly limit; auto-resumes on reset).
- **Gaps to close (the "anchors"):** a human expert gold-set, a perturbation/contamination set,
  on-device measurement, and evals-as-CI.

---

## 1. Anti-regression and reliability  (P0)

The single highest-leverage theme. Make it impossible for a change to silently degrade the result.

- **Evals-as-CI.** _(DONE 2026-07-21: `scripts/run_evals_gate.py` + `.github/workflows/duecare-evals.yml` gate the gemma4:31b headline paired lift and the deterministic `verify_lift` per-criterion pass rates against committed fixtures (`packages/duecare-llm-kit/tests/fixtures/`) and a committed baseline (`configs/duecare/evals_baseline.json`), stamped with `(git_sha, dataset_version)`; exits non-zero on any regression beyond tolerance.)_ GitHub Action that, on every push, runs the kit tests + the Fact-Check recompute +
  `verify_lift` on a fixed held-out slice, and FAILS the build if the mean lift, the 20/20 claim
  checks, or the deterministic verify score regress beyond tolerance. Stamp artifacts with
  `(git_sha, dataset_version)`. Publish `generate_report()` HTML as the CI artifact.
- **Verifier as a hard gate.** `duecare.kit.verify` becomes a required check: any new harness/prompt
  change must not drop the deterministic per-criterion pass rates. This is the anchor the model
  cannot game.
- **Golden tests + frozen fixtures.** A small, frozen set of (prompt, expected-indicators,
  expected-citation) that the engine must always satisfy; a frozen held-out split the training/flywheel
  is structurally forbidden to see.
- **Human gold-set + kappa drift monitor (P1).** 50-100 prompts graded by an anti-trafficking
  professional; calibrate the judge prompt against them; track judge-human agreement (Cohen's kappa /
  ICC) over time and alert on drops. Converts "silver labels" into a defensible number.
- **Perturbation / contamination set (P1).** Auto-generate perturbed variants (swap names/numbers/
  corridors, rewrite phrasings, translate) via the existing `prompt_remixer` + multilingual layer;
  report lift on the perturbed set to prove it is not memorization; caveat the cross-model board.

## 2. Continuous improvement  (P0-P1)

- **Grounded-graph flywheel.** Wire `verify` as a *verifiable reward* alongside the LLM judge in the
  flywheel, pair the under-refusal metric with the benign-control over-refusal counter-metric, keep the
  held-out gate frozen, and treat the Fact-Check as the independent audit loop. Name it: DueCare's own
  improvement loop becomes a documented, anchored graph (see `docs/ARCHITECTURE.md`, to write).
- **Where-it-hurts tracking.** The 46 verifier regressions (harness dropping a resource cue) are a
  concrete backlog; add a standing "regression triage" that turns each into a rule/test.
  - **Compact-engine recall gap (tracked 2026-07-21, CLOSED 2026-07-26).** Two independent finders (a
    notebook agent + the `examples/incoming_content/` demo) hit the same miss: `scripts/_usecase_engine.py`
    PATTERNS did not match possessive-apostrophe legalese ("the Employee's passport", "workers' passports"),
    the "passport stays with the employer" phrasing, "lakh"/"crore" fee amounts, or several romanized
    multilingual cues. All four are now covered (2 document-retention patterns, 1 South-Asian fee-amount
    pattern, 11 romanized cues incl. a new `excessive_overtime` cue set).
    _The deliberate re-grade this item was waiting on was run and is recorded here._ Measured old-vs-new
    over **15,600 real texts** (600 committed showcase fields + 15,000 responses streamed from
    `reports/rich_lift/results.jsonl`): **+442 rows gain an indicator (2.833%), 0 rows lose one (0.000%)** --
    strictly additive. `scripts/run_evals_gate.py` stayed **identical on every metric**, so
    `configs/duecare/evals_baseline.json` did **not** need re-baselining and no published notebook figure
    moves. The `examples/incoming_content/` demo now catches all 3 former boundary cases.
    **Negative result worth keeping:** a prohibition-aware guard (suppressing "no employer may retain a
    passport" as policy text rather than a report) was implemented, measured, and **reverted** -- it cut
    **979 of 15,600 rows (6.3%)**, far more than the recall it protected. `scan()` serves two roles, and on
    a model *response* a cited prohibition is the model correctly naming the indicator, which verify
    criterion A must score. Do not reintroduce it without splitting the two roles, which the pinned
    `scan(text)` API contract forbids. (The earlier precision fix -- a self-retention negation guard so
    "I keep my own passport" no longer over-flags -- shipped 2026-07-21 and remains in force.)
- **Re-versioning discipline.** Datasets grow and are re-versioned (never silently replaced); keep the
  perdim sweep growing toward the full registry; publish grade deltas, not overwrites.

## 3. Extensibility for others  (P1)

Make it trivial for an outside team to reuse, extend, and build on DueCare.

- **Publish `duecare-llm-kit` to PyPI.** _(READY 2026-07-21: `python -m build` produces the wheel + sdist,
  both `twine check`-PASS; the wheel installs into a throwaway venv on numpy/pandas/matplotlib alone, with
  `import duecare.kit` (0.1.0), `engine.scan` (12 indicators), `verify()` (5/5), and both console entry
  points all working. Verified path + the one manual `twine upload` step documented in
  `packages/duecare-llm-kit/RELEASING.md`.)_ Tag v0.1.0; real `pip install duecare-llm-kit`. `twine upload`
  needs a PyPI token so it stays Taylor's manual step (same boundary as Kaggle). This is the
  main "download and reuse" unlock.
- **Domain-pack SDK.** A documented recipe + template to add an integrity domain in N steps: define
  indicators, attach the controlling framework/knowledge pack, supply a graded prompt set, run the
  harness-lift benchmark. The cross-industry notebook already sketches 7 domains; turn that into a
  `duecare.kit.domains` plugin contract.
- **Harness plugin contract.** Stabilize the `HarnessSpec` (name / applied_layers / consumes / emits /
  register_routes) as the public extension point; a "write your own harness" tutorial.
- **Docs site.** mkdocs-material auto-generating an API reference from the (now-improved) docstrings;
  CONTRIBUTING.md; ARCHITECTURE.md; a model card when an adapter is published.

## 4. Easier impact and easier use  (P1)

- **On-device deployment.** Ship + measure the harness on QAT Gemma 4 E2B via LiteRT-LM (E2B <1GB,
  2.2x MTP); report whether the thin layer survives int4 and at what latency. The "runs on a laptop"
  claim, made real.
- **Multimodal Scout (P2).** Worker photographs a contract/ad -> on-device Gemma 4 vision reads it ->
  the harness flags indicators, all local. Extends the Bulk-File-Review harness.
- **Email-oracle for civil society.** NGOs will not learn a new UI; a proactive SMTP+IMAP oracle that
  solicits and returns analysis by email is the lowest-friction channel (already scoped in memory).
- **Integration patterns.** The developer notebook's `analyze()` + the three deployment modes
  (enterprise waterfall, on-device, NGO dashboard) become a documented, versioned integration guide.

## 5. Agents, AI workers, and pipelines (OpenClaw-style)  (P1)

DueCare already uses multi-agent orchestration to build notebooks. Formalize it as a governed pipeline.

- **Continuous knowledge-refresh pipeline.** A scheduled agent graph: (a) scout ILO / court /
  regulator / NGO sources for updates -> (b) extract + scrub candidate facts -> (c) the deterministic
  `verify`/engine + a rules gate scores them -> (d) a human review queue approves -> (e) commit as a
  new *versioned* knowledge pack (`superseded_by`, never overwrite). This is the "graph of loops with
  an anchor" applied to knowledge, not just eval.
- **OpenClaw / agent-worker fit.** Use an OpenClaw-style agent runtime for the long-running,
  scheduled arms (source scouting, benchmark re-runs, report generation) with the verifier + human
  gate as the frozen anchor nodes, so autonomy never bypasses grounding. Keep the existing
  pause-safe boundary: agents propose, gates dispose.
- **Report/corpus workers.** Scheduled `duecare.kit.report` + `export_corpus` runs that publish fresh
  HTML reports + corpus bundles as the sweep grows - continuous, auditable outputs.
- **Guardrails (P0 for any autonomy).** Every autonomous arm is fail-closed on the training contract,
  the PII gate, and the verifier; nothing publishes without passing evals-as-CI.

## 6. Community engagement  (P1-P2)

- **Host the benchmark as a public Kaggle competition/benchmark.** "Beat +40.7 while staying
  grounded." Flips DueCare from entrant to host, turns the benchmark into a field standard, and is more
  durable than any placement. Use `kaggle/04-kaggle-community-benchmark` as the seed.
- **Open the kit + datasets** with clear licenses, Croissant metadata, and a Zenodo DOI for citability.
- **Partnerships.** Anti-trafficking orgs (Polaris, IJM, POEA, BP2MI, HRD Nepal) for the human gold-set
  + real referral pathways; academic collaboration on deceptive-recruitment detection (align with the
  current arXiv work); a "contribute a corridor pack" call for the multilingual/corridor layer.
- **Narrative.** Contribute to the live "grounded vs ungrounded" AI-eval discourse with DueCare as the
  worked example (companion essay drafted; social posts drafted).

## 7. Knowledge and information refresh (updated packs)  (P1)

- **Acquisition pipeline (exists) -> productionize.** fetch -> extract -> chunk -> dedup -> scrub ->
  graph -> stage, feeding the versioned knowledge packs; wire into the section-5 refresh loop.
- **Volatile vs stable split (enforced).** Memorize stable reasoning habits, refusal behavior, ILO
  indicator categories, privacy boundaries, evidence-first shape. Get volatile facts (hotline numbers,
  fee caps, current advisories, fresh statutes) from tools / vetted packs at run time - never bake them
  into training targets.
- **Legal-claim staleness flagging (exists).** Keep `configs/duecare/legal_claims.json` current; the
  flagger surfaces stale claims for review.
- **Entity-intelligence (propose-only).** Keep the recruitment/entity-verification layer separate from
  the trafficking knowledge layer; human-gated promotion only.

---

## Prioritized next five

1. **Evals-as-CI** with the `verify` gate + Fact-Check recompute (anti-regression foundation). *P0 - DONE 2026-07-21.*
2. **PyPI release** of `duecare-llm-kit` v0.1.0 (extensibility unlock). *P1*
3. **On-device lift measurement** on QAT Gemma 4 E2B via LiteRT (impact + the LiteRT story). *P1*
4. **Human gold-set + kappa monitor** (the one anchor that makes every number defensible). *P1*
5. **Host the benchmark as a public Kaggle competition** (community + durability). *P1-P2*

Items 1, 3, and 4 also close the three open "anchor" edges - after them, DueCare is a fully grounded,
self-auditing improvement system, which is both the engineering goal and the story.
