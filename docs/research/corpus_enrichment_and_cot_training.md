# Corpus enrichment loop + chain-of-thought training (design)

Two linked systems, both governed by one principle Taylor set: **build upon, do not replace — append and
reweight with verification, never overwrite.** Both are propose-only and gated; nothing here touches the
live v1/h1 board or the vetted corpus without an explicit human go-ahead.

## Part A — the gated legal-corpus enrichment loop

The project already runs this pattern for benchmark *prompts* — `hermes.py` (propose-only discovery
daemon: stages, never merges) then `openclaw_daemon.py` (quality-gate daemon: accept/reject vet) then a
supervised merge. The enrichment loop applies the **same proven, gated pattern** to the legal-claim corpus
(`configs/duecare/legal_claims.json`), so more rules are researched and added over time without ungated
auto-committing.

```
research (agent + WebSearch, per loop cycle; no paid keys)
   -> draft a candidate EvidenceClaim (full schema: source_url, jurisdiction, applies_to, exceptions,
      binding_status, effective/verified dates, volatility, recheck_after)
   -> MULTI-PROMPT CONVERGENCE vet (mistral, N distinct framings; accept only on majority agreement)
   -> guardrail gate (schema valid? sourced? duplicate/challenger? plausibly current? not fabricated?)
   -> STAGE to a review queue (propose-only; reports/legal_corpus_staging.json)
   -> [HUMAN GO-AHEAD] promote: APPEND to the corpus (plus verification_weight); a claim that improves on an
      existing one is marked supersedes/superseded_by, the old record RETAINED, never deleted.
```

Guardrails (defence-in-depth — a candidate must pass ALL):

| Guardrail | Why | Enforcement |
|---|---|---|
| Schema + ISO dates + required fields | no malformed claim enters | `legal_claims.validate_schema` |
| Real `source_url` (primary/official preferred) | no claim "because a document was retrieved" | reject if missing/low-authority |
| Exceptions + applicability present | prevents the overbroad-claim failure the audit flagged | reject bare absolute claims |
| Freshness fields (`as_of`, `recheck_after`, volatility) | nothing enters undated | required |
| Duplicate/challenger check vs corpus | build-upon-not-replace | match proposes a supersede, never overwrites |
| **Multi-prompt convergence** | no claim on one model's single say-so | N framings ("is it accurate?", "what's the strongest objection?", "which exceptions are missing?"); accept only if they converge |
| Anti-fabrication | no invented statute/number (the canary's lesson) | cross-check the cite against the source; low `verification_weight` until human-verified |
| Human promotion gate | final authority stays human | staged, never auto-merged |

Roles of the existing systems (feeders into the SAME gated pipeline, not new ungated committers):
- **Hermes** (discovery) can be pointed at "under-covered jurisdiction/topic" targets to draft candidate
  claims, exactly as it drafts benchmark prompts today; output stages, never merges.
- **The vetting daemon** (`openclaw_daemon.py`) is the natural home for the convergence + guardrail vet
  (accept/reject a candidate before it advances), mirroring how it vets prompts.
- **The agent loop** (this session's days/weeks loop) does the WebSearch research (the daemons have no
  web), drafts candidates, runs the convergence vet, stages, and asks for the promotion go-ahead.
- **`configs/duecare/legal_research_queue.json`** is the shared target queue (which jurisdictions/topics to
  enrich next), like `autonomous_engine_state.json` is for the board.

Deliberately NOT built: an unattended agent that commits new legal claims (or edits the live corpus) on
its own. That is the "issue/concern" to avoid — legal claims are high-stakes, so promotion stays a gated,
human-reviewed, append-only step.

## Part B — why simple fine-tuning makes the model think wrong, and the CoT fix

The project already holds this thesis: `reasoning_contract.py` trains "a *way of thinking* (a procedure),
jurisdiction-independent and free of volatile specifics," NOT facts, because "a LoRA that memorises facts
is brittle, low-capacity, and goes stale." The failure modes below are why, each with its mitigation. The
richer scaffold is `legal_reasoning.py` (it EXTENDS the existing INDICATOR to STATUTE to ACTION to RESOURCES
chain of `build_reasoning_targets.py` with applicability/exceptions, temporal-freshness, Palermo elements,
precedent, and explicit uncertainty).

| How simple fine-tuning makes the model think wrong | What it looks like | CoT mitigation |
|---|---|---|
| **Fact memorisation to staleness** | learns "the cap is X / the hotline is Y" as fixed tokens; wrong the day the rule changes | train the *procedure*; mark volatile facts (caps, hotlines, fee amounts) as TOOL-CALL / VERIFY slots, never memorised (rule 81) |
| **Surface-token mimicry to overbroad claims** | learns to emit "C181 prohibits all fees" because that pattern scored well (the specificity-overfit we measured) | targets must carry the exception + applicability; the faithfulness framing + fabrication canary catch bare confident cites |
| **Conclusion, not reasoning** | learns to output the verdict ("this is trafficking") without the act/means/purpose chain | target = the CHAIN (facts to indicators to applicable law with exceptions to element analysis to uncertainty), never the bare conclusion; contract-gated |
| **Catastrophic forgetting / capability regression** | fine-tuned-alone scored *below* stock in the 4-arm table | small LoRA on the procedure only; keep the harness as the fact/context layer; measure vs stock, don't assume synergy |
| **Sycophancy / shortcut** | learns to reassure or to over-refuse because that was rewarded | role-aware targets (worker vs operator vs ambiguous); benign-control over-refusal metric; "risk pattern, not a finding" is mandatory |
| **Refusal-collapse** | learns a short refusal because SFT targets were short | resilient_chat + the hard_collapse guard; targets are full grounded reasoning, length-checked |
| **Jurisdiction/time blindness** | applies one country's rule everywhere, or a repealed rule | the scaffold FORCES applicability + temporal-validity checks (Kozminski is retained but marked "not current law -> cite TVPA sec.1589") |
| **Overconfidence / no uncertainty** | states inferred facts as certain | the scaffold requires reporting supported/inferred/missing plus a recheck list |

Concrete CoT-training plan (append-only, gated; extends the existing pipeline, does not replace it):
1. Use `legal_reasoning.py` walkthroughs as **reasoning-chain SFT targets** — they are legally precise,
   exception-aware, freshness-flagged, worker-protective, and never assert a finding: the exact procedure
   we want internalised.
2. Every generated target passes `reasoning_contract.py` (the chain must be present) AND the claim library
   freshness gate (no stale/volatile fact memorised as fixed) BEFORE it can enter `build_reasoning_targets`
   / `build_reasoning_sft_variant` (staged as a NON-DESTRUCTIVE variant arm, per existing practice).
3. Prefer **DPO on reasoning quality**: chosen = full-chain-with-exceptions-and-uncertainty; rejected =
   bare-overbroad-conclusion. This teaches the model to *prefer the procedure*, directly countering the
   surface-mimicry and conclusion-not-reasoning failure modes.
4. **Multi-prompt convergence on the label**: a training pair is only accepted if multiple judge framings
   agree the chosen reply reasons correctly (not just sounds specific) — the fabrication-canary and
   faithfulness lenses are the screens.
5. Never fine-tune before hidden lineage splits + direct factual grading are in place (external-audit sec.17).

## Status
- Built: the claim library + freshness flagger + the `legal_reasoning.py` CoT scaffold + this design.
- Seeded: `configs/duecare/legal_research_queue.json` (the enrichment target queue).
- Next (gated, incremental per loop cycle): stand up the convergence-vet staging step (extend the vetting daemon),
  research queue targets via WebSearch, and stage the CoT-target DPO arm — each behind the human promotion
  gate, append-only.
