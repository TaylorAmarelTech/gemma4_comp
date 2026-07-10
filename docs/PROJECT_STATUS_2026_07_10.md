# DueCare — project status (2026-07-10)

A single honest snapshot: what the project is, the rules and systems it runs under, what changed
recently, where coverage is thin, and what happens next — with an emphasis on training, synthetic-data
generation, and chain-of-thought. Numbers here are reproducible from the cited scripts/configs; where a
result is a proxy or small-N, it says so. This complements (does not replace) `PROJECT_BIBLE.md`,
`docs/codex/PROJECT_BIBLE.md`, and the per-topic reports under `docs/research/`.

---

## 1. What the project is

A Gemma 4 Good Hackathon submission: a local, on-device **safety harness** for migrant-worker
anti-trafficking. The harness externalises domain knowledge into layers around a small Gemma 4 model so
NGOs/regulators who cannot send sensitive case data to frontier APIs get a private evaluator that runs on
a laptop. The defensible research claim (see §6) is that this harness measurably improves the
**rubric-scored trafficking-safety quality** of the model's replies on tested prompts.

The harness layers: **GREP** (deterministic ILO-indicator rules) → **RAG** (legal grounding) →
**ILO-reasoning preamble** → **tools** (volatile facts: hotlines, fee caps, advisories) → hard safety
gates (**anonymization**, **search-safety**, **post-search verification**).

---

## 2. Operating rules & systems

### Auto-loaded rules (`.claude/rules/*.md`)
| # | Rule | Enforces |
|---|---|---|
| 00 | overarching goals | Impact(40)/Video(30)/Tech(30); every action advances ≥1 or is cut |
| 05 | project-bible pickup | long-loop handoff; engine-pause boundary |
| 10 | safety gate | **no real PII** in git/logs/training/artifacts; audit stores `sha256`, not plaintext |
| 20 | code style | Python 3.11+, Pydantic v2, Protocols, pathlib, fail-loud |
| 30 | test before commit | tests green before commit; check pytest EXIT **separately** from the commit |
| 40 | module contract | folder-per-module, auto-generated meta files |
| 50 | publish strategy | GitHub + multi-package PyPI + Kaggle |
| 60 | notebook presentation | Kaggle-safe styling, no truncation |
| 70 | workbench UI primitives | activity log, trust boundary, sample artifact per page |
| 80–83 | active surface / runtime / structure / kaggle | recording-critical kernels, `Gemma4Runtime.load()`, layout, manual Kaggle |

### Standing systems
- **Days/weeks autonomous loop** — sustained propose→gate→commit improvement. North star: a
  peer-review-grade harness-lift report, one prompt **per dimension**, honest tracking of where the harness
  **hurts**, multi-provider judge fan-out.
- **Gated enrichment loop** — research → draft → guardrails → multi-prompt convergence vet → stage/promote,
  **append-only** with reweight-on-verification. Nothing is auto-promoted to the live board or fine-tuned
  without Taylor + the review gates.
- **Fact-forcing gate (GateGuard)** — before the first edit/write per file, present importers, affected
  functions, data fields, and the verbatim instruction. Caught real mistakes this session.
- **Build-upon, never replace + reweight-on-verification** — knowledge is appended and superseded, never
  overwritten; `verification_weight` 0.6 (auto-vetted) vs 0.9 (human-verified).

---

## 3. Knowledge & corpus state

| Surface | Count | Source of truth |
|---|---:|---|
| GREP indicator rules | 451 | `verify_knowledge_surfaces.py` |
| RAG documents (trafficking) | 859 | idem |
| Multidomain corpus (kept separate) | 610 | `/api/multidomain/rag` |
| Example/showcase prompts | 652 | `_examples.json` |
| Seed prompts | 74,640 | `seed_prompts.jsonl` |
| ILO conventions | 16 | knowledge layer |
| **Vetted legal-claim library** | **33** (29 human-verified @0.9, 4 auto-vetted @0.6) | `configs/duecare/legal_claims.json` |

The 4 still at 0.6 (pending human verification of volatile figures): `ph_placement_fee`,
`sa_kafala_reform_2025`, `bd_overseas_employment`, `lk_slbfe`.

The legal-claim library is an EvidenceClaim overlay: each claim carries `source_url`, `jurisdiction`,
`applies_to`, `exceptions`, `binding_status`, `effective_from`, `as_of`, `volatility`, `recheck_after`,
`supersedes`/`superseded_by`, `verification_weight`, and `provenance`. A deterministic freshness pass
(`legal_claims.py::due_for_recheck`) flags stale/volatile claims for re-verification.

---

## 4. Recent updates (this session)

- **Legal-claim layer built + audited** (commits `9e803747`→`e5e4d308`): vetted library grown 17→33 via
  gated batch enrichment; an adversarial web-audit corrected 6 real errors (a settled case shown as
  pending, a wrong reform date, a misattributed statute, an over-absolute superlative, a mislabelled
  federal/state id) and reweighted 29 claims to human-verified 0.9.
- **Deterministic legal-reasoning engine** (`legal_reasoning.py`): facts → ILO indicators → applicable law
  *with exceptions* → Palermo element analysis → uncertainty → **never a criminal finding**.
- **Red-team response taxonomy** (`redteam_classify.py`, commits `8670baae`→`ce29768a`): 9 behavioural
  classes + context-dependent severity weighting (see §8).
- **Honest findings synthesis** (`docs/research/findings_synthesis_2026_07_10.md`): the publish-ready,
  post-adversarial-review claim + limitations register.
- **8 verified code-review fixes** (`f3947b3b`): substring keyword matching, unenforced supersede
  semantics, red-team leak/ordering bugs, overbroad-guardrail evasions, crash-on-malformed-input,
  injection false-flag, digit corruption — all fixed + regression-tested (42 tests green).

---

## 5. Training & fine-tuning systems

DueCare does **not** retrain Gemma 4 base weights. It trains named LoRA adapters (Unsloth SFT→DPO) on
curated public/synthetic/composite/anonymized data — never raw worker chats.

| System | Script | Role |
|---|---|---|
| Lift → training distillation | `build_lift_training_data.py` | benchmark lift → vetted SFT/DPO (≈220 ex live) |
| Reasoning targets | `build_reasoning_targets.py` | gold reasoning traces (chain-detector gated) |
| Reasoning repairs | `build_reasoning_repairs.py` | verify-and-repair pairs |
| Reasoning SFT variant | `build_reasoning_sft_variant.py` | SFT stream over the scaffold |
| Contract DPO | `build_contract_dpo.py` | DPO chosen=contract-satisfying, rejected=violating |
| Legal CoT | `build_legal_cot_training.py` | gated legal chain-of-thought SFT/DPO (see §7) |

**Gate:** none of this is fine-tuned yet. It is propose-only, staged to `reports/training/`, pending
hidden lineage splits + direct factual grading before any GPU run.

---

## 6. Benchmark & findings (honest)

Full detail: `docs/research/findings_synthesis_2026_07_10.md`. Headline:

- **Direction is robust**; magnitude is a proxy. The harness lifts `gemma4:31b` by **~+40** on a 0-100
  rubric (harness_core, cross-family Ollama judges), but:
  - ~60/100 rubric points reward exactly what the harness injects (near-circularity),
  - the judge-independent **deterministic grader is null over a placebo** for the headline model,
  - per-dimension re-grading shows only **~+12–14 under worker-utility / faithfulness lenses**.
  - **The load-bearing publishable number is ~+12–14 ("rubric-scored quality on tested prompts"), not +40.**
- **Controls that earn the direction claim:** length-matched placebo (harness adds **~+3.3 beyond
  placebo**), incidental-dimension lift (~21/21 non-injected dimensions), ~100% in-range / ~0.1%
  hallucinated citations, cross-family judge agreement, clustering-corrected pooled run.
- **Where the harness HURTS** is tracked, not hidden: broad serving guards are net-negative; only the tight
  `hard_collapse` guard (baseline ≥1000ch → harnessed ≤150ch) is net-positive (`DEFAULT_GUARD_POLICY="hard"`).
  Serve **core, not full** (87.1 > 84.9; full ≤ core on every model) is the big lever.

---

## 7. Chain-of-thought generation & tuning (emphasized)

**Thesis (the core CoT bet):** a reasoning LoRA should store a **way of thinking — a procedure — not
facts.** Facts are brittle, low-rank, and go stale; a jurisdiction-independent reasoning scaffold does not.
Volatile specifics (hotlines, fee caps, dates) are forbidden in the reasoning and pushed to tools/RAG.

**The contract scaffold** (`reasoning_contract.py`):

```
indicator  →  statute  →  action  →  resources
(name the ILO  (cite the      (concrete    (route the worker
 indicator)    controlling    protective   to protective help)
               law)           step)
```

**Two hard enforcements make it a contract, not a checklist:**
1. **Citation validity** — a cited statute must not be hallucinated **and** must actually govern the
   indicator it is paired with (no real-but-irrelevant convention to satisfy the "statute" step).
2. **Fragile-fact prohibition** — the reasoning may not assert volatile specifics; those belong in
   tools/RAG. This is what keeps the LoRA storing a way of *thinking*.

**Three uses:** (1) training filter — keep only traces that satisfy the contract; (2) inference enforce —
a **verify-and-repair loop** that re-prompts with a repair directive when a step is missing/wrong;
(3) eval metric — a **judge-independent** CoT-pass-rate column alongside the LLM-panel lift.

**Why simple fine-tuning makes a model think wrong — the 8-mode failure taxonomy**
(`build_legal_cot_training.py`). For each reasoning walkthrough it emits a CHOSEN full-chain answer (gated
to pass the contract) and one REJECTED response per wrong-thinking mode:

| Failure mode | Caught by |
|---|---|
| conclusion-only ("you are a victim of trafficking") | structural contract |
| refusal-collapse | structural contract |
| fabricated citation | structural contract |
| stale/memorised fact (a specific fee/hotline) | structural contract |
| missing resources | structural contract |
| jurisdiction-blind | structural contract |
| overconfident / no uncertainty | structural contract |
| **overbroad-no-exception** (real convention cited WITHOUT its exception) | **semantic faithfulness/exception layer (the one structural gap)** |

**Measured finding:** the structural contract catches **7 of 8** modes; the 8th (overbroad-no-exception)
is exactly the specificity-overfit failure the legal-claims exception layer exists to catch — the two
layers are complementary and both necessary. This is why we run structural + semantic, not one.

**Strong/emphasised CoT tuning path (owed, gated):** distil contract-satisfying traces into SFT, then DPO
(chosen = contract-satisfying chain, rejected = each failure mode), enforce the contract at inference via
the repair loop, and report the judge-independent CoT-pass-rate as an additive board column. Not yet
fine-tuned — pending hidden lineage splits + direct factual (legal-correctness) grading.

---

## 8. Red-team response classification

`redteam_classify.py` — a deterministic screen (regex, no model) classifying a reply, or a two-turn
`(prior, current)`, into behavioural classes beyond binary refused/answered. Nine classes:
`full_refusal`, `full_comply`, `refusal_then_comply`, `comply_then_caveat`, `hedged_comply`,
`partial_comply`, `refusal_then_hedge`, `safe_redirect`, `unclear`.

**Context-dependent severity weighting** — the same class flips sign by prompt type. On an adversarial
(exploiter) prompt giving substance is the harm; on a benign (worker) prompt refusing is the harm. So the
batch reports a **severity-weighted adversarial red-rate** and a **benign over-refusal severity**,
**separately, never averaged** (per the external audit's critical-negatives requirement).

Honest scope: it is an **unvalidated heuristic screen** (no precision/recall vs a labelled set yet;
English-only) that triages which replies an LLM judge reads closely — not itself a result.

---

## 9. Synthetic-data generation

- **Prompt remixing / noise** (`prompt_remixer.py`, `noise_robustness.py`): spelling typos, word
  add/subtract, char-repeat, split/merge, separator injection — to test we are not just maximising a
  semantic peak in feature space. GREP is word-level robust but character-level brittle (documented, and
  the obvious normalizer fix was tested and **honestly rejected** as net-negative — it mangles legit
  "C-181"/"3.5" tokens; digit-corruption bug fixed this session).
- **Rubric-polished SFT/DPO** (`generator_mode=rubric_polisher`): two-pass critique→rewrite.
- **Legal CoT pairs** (§7) and **lift-distilled** pairs (§5).
- **Injection probes** (`injection_defense.py`): the worker pastes third-party content; probes plant a
  hijack instruction to measure the model's robustness (propose-only, graded on the next Ollama window).

All synthetic content is composite/synthetic — **no real PII** (rule 10).

---

## 10. Areas of poor coverage / needing more review

1. **Legal-correctness of ACTUAL harness outputs is unvalidated** — every control validates the *presence
   and plausibility* of injected specifics, not legal correctness or scenario relevance. This is the single
   most publishable-against gap. The project's own "gold" replies were found legally overbroad by the audit.
2. **Red-team classifier has no precision/recall** against a labelled adversarial/benign set; English-only.
3. **Overfitting quantifications are small-N, single-judge, point-unstable**; one lens (deduction) was
   post-hoc reworded after misbehaving — a HARKing risk, flagged in our own register.
4. **Fabrication canary** is n=5 with cartoonish fakes; needs subtle-error arms ("real convention, wrong
   article") and re-measurement on the corrected (no-longer-overbroad) gold replies.
5. **Prompt set is heavily templated** — quote effective-N-adjusted CIs; the 1,595-prompt board is not
   itself cluster-corrected.
6. **4 legal claims remain auto-vetted (0.6)**, not human-verified.
7. **CoT is gated but not fine-tuned** — needs hidden lineage splits + direct factual grading before a GPU
   run; the overbroad-no-exception mode is not structurally catchable (needs the semantic layer).
8. **`evaluation.html` "Latest evaluation run" section** presents precise illustrative metrics
   (`npl-qat-construction@1.4.0-rc1`, 98.2% citation accuracy, `0/14k` PII) that should be **explicitly
   labelled illustrative** to honour the "real, not faked" invariant — a one-line copy edit still owed.

---

## 11. Next steps (the publish-strengthening queue)

- **Legal-correctness grading of real outputs, blinded to arm** — the experiment that would most strengthen
  or puncture the "cites the specific law" lift.
- **Lift-under-noise on GENERATED answers** (baseline vs harnessed on noised prompts), not just GREP fire.
- **Validate `redteam_classify`** — build a labelled adversarial/benign sample, measure its own
  precision/recall; add non-English markers.
- **Larger-N, multi-judge, cluster-corrected re-grade** of the diverse-lens headline.
- **Human-verify the 4 remaining auto-vetted legal claims**; resume the enrichment waves
  (Bahrain/Oman/Lebanon, Vietnam/Ethiopia, US §1591, FATF).
- **CoT fine-tune** once hidden lineage splits + direct factual grading are in place; then report the
  judge-independent CoT-pass-rate as an additive board column.
- **Label the `evaluation.html` illustrative metrics** (item 10.8).

---

## 12. Test & validation state

- The 8 code-review fixes this session are covered by **42 targeted tests, all green** (recovery venv:
  `%LOCALAPPDATA%\gemma4-testenv\venv`; system Python is OneDrive-corrupted — use
  `scripts/recover_test_env.ps1 -Run`).
- `scripts/validate_public_surface.py` reports **0 findings** on the current public docs/templates.
- Full suite is historically ~1,490 pass / 3 skip; rerun `python -m pytest packages --collect-only -q`
  and the full suite before making current suite-wide claims (counts in `CLAUDE.md` may be historical).

---

*Generated 2026-07-10. Reproduce any count from the cited script/config. Where a result is a proxy,
small-N, or unvalidated, this document says so — that honesty is the point.*
