# Adversarial findings & improvement register (2026-07-10)

An honest ledger of how the DueCare verification/detection layers can be **defeated**, produced by an
adversarial review that ran the live code (not just read it), plus what was fixed in-session and what is
still owed, ranked by leverage. This is the "where does it break" companion to
`docs/research/findings_synthesis_2026_07_10.md`. The point is to track defeatability openly.

## Fixed this session

| Ref | Issue (verified) | Fix | Commit |
|---|---|---|---|
| A1 | Status/findings docs understated the machine-vetted fraction of the live corpus ~3× ("33 claims / 4 auto-vetted"; the file had grown). 4 precedent claims sat at 0.9 with no `provenance`. | Docs now state counts **as-of** + point to `legal_claims.py` as the live source; provenance stamped on the 4 precedent claims. | `ad390d73` |
| A2 | Docs present-tensed a "semantic faithfulness/exception layer" that catches overbroad answers — but no such **output** gate exists at inference. | Reworded: the overbroad mode is **currently unguarded at inference**; the gate is owed, not built. | `ad390d73` |
| A4 | `due_for_recheck` only flagged a past `effective_from` for `claim_type=="reform"`, so a **future-effective** rule read as fully in force. | Any future `effective_from` is now flagged "not yet in force". | `53e9a471` |
| B4 (part) | The overbroad guardrail's `_ABS_VERB` had `ban` but not `bans`, and lacked `outlaw`/`forbid`. | Extended to `ban(s\|ned)`, `outlaw(s\|ed)`, `forbid(s\|den)`; scoped claims still pass. | `4bf9a6c9` |
| new | Traffickers **impersonate** the law (control narratives), faith, and rumour to control workers — a surface none of the layers named. | New `claim_epistemics.py` classifies law / guidance / fact / rumour / faith-framing / **control-narrative** / misunderstanding / unclear + a myth→reality catalog. | `c7c37f75` |

## Owed — ranked by leverage (each verified defeatable)

1. **Multilingual coverage (CRITICAL / P0).** `legal_reasoning`, `redteam_classify`, `claim_epistemics` are
   English-only; a Tagalog report of passport confiscation fires nothing. The population writes in origin/host
   languages. Fix: per-indicator origin/host-language lexicons.
2. **Synonym / paraphrase evasion (CRITICAL).** "travel booklet"≠passport, "cash advance…earn back"≠debt
   collapses the deterministic signal (Palermo flips to False). Fix: synonym table + a paraphrase axis in
   `noise_robustness.py` (which only perturbs characters today).
3. **Output-faithfulness gate on ACTUAL answers (HIGH) — PARTLY ADDRESSED.** Controls validate
   presence/plausibility, never legal correctness; the overbroad-no-exception mode was unguarded at inference.
   The output-side analog of `_looks_overbroad` is now built + tested (`scripts/output_faithfulness_gate.py`,
   propose-only): it flags a generated answer that states an absolute legal rule without its exception and
   cross-refs the corpus. Remaining: wire it into the live inference path, and run the blinded end-to-end
   evaluation on real harness outputs.
4. **Red-team classifier unvalidated & evadable (HIGH).** A fresh-worded 29-word playbook → `unclear` not RED;
   "Sorry, that request cannot be handled here." is not detected as a refusal. Fix: a labelled set with
   precision/recall; an LLM backstop; non-"I" refusal forms.
5. **Enrichment-vet source & model weakness (HIGH).** `source_url` check is `startswith("http")`; convergence
   is 3 framings to the SAME model. Fix: authoritative-domain allowlist + ≥2 vendor-distinct models.
6. **Reasoning-contract fragile-fact gate ignores fees/dates (MEDIUM).** Only phone numbers hard-fail; an
   asserted "the max lawful fee is exactly 50,000" passes. Fix: gate money/date in the reasoning trace.
7. **Schema & referential integrity (MEDIUM).** `REQUIRED` omits `applies_to`/`authority_class`/
   `effective_from`; no `superseded_by`-target-exists check; no cross-claim dedup/consistency scan.

## How to read this

The layers are **screens and scaffolds**, not guarantees — and the highest-leverage failures (1, 2, 4) share
one shape: a determined adversary who rewords, translates, or paraphrases defeats a surface-form matcher. The
honest posture is to route anything uncertain to a judge/human, keep the deterministic layers as fast triage,
and prioritise multilingual + paraphrase robustness + an output-correctness gate. Every item is reproducible
by running the cited script against the cited input.
