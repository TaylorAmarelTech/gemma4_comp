# Deferred follow-ups — 2026-05-29

> Honest archive of items surfaced during the Opus 4.8 review + harness-lift /
> knowledge-expansion push. Each entry is a **suggestion with reasoning**, not a
> confirmed open bug: what it is, status (built vs archived), why, the
> recommended approach, and the risk. The bar for archiving instead of fixing
> on the spot: the item is either (a) blocked on tooling we could not reach this
> session, or (b) low-enough impact that the safe fix deserves a dedicated,
> separately-tested pass rather than an opportunistic edit.

## Built this session (not deferred — listed for completeness)

- **Model-agnostic harness lift.** `packages/duecare-llm-chat/src/duecare/chat/harness_lift.py`
  (`build_harness_preamble`, `lift_arms`) + `scripts/harness_lift_benchmark.py`
  (the multi-model meta-orchestrator) + `configs/duecare/benchmarks/harness_lift_sample.json`
  (local Gemma 4, Gemini 3.5, Claude Opus 4.8 × baseline/harnessed) + `docs/benchmarking.md`.
  Lets us measure how much the DueCare harness lifts ANY model's
  trafficking-safety score. Tested (8 unit tests, injected fakes — runs without
  API keys); wiring real frontier endpoints needs only `GEMINI_API_KEY` /
  `ANTHROPIC_API_KEY` + the existing `model_interface` adapters.
- **+7 GREP rules / +7 RAG docs** (ILO C189/C188/MLC 2006/Palermo/P029,
  contract substitution, passport-"safekeeping") — verified, 345 GREP / 242 RAG.
- **13/15 exhaustive-review findings** applied; see the `fix:` commits.

## (A) Deep esoteric-source knowledge mining — **archived (tooling-blocked)**

**What:** mine jurisdiction-specific primary sources under-represented in the
grounding — Philippines DMW/POEA Memorandum Orders, Indonesia BP2MI *Perban*,
Russia/China labour & anti-trafficking statutes, Hong Kong EA regulations +
foreign-domestic-helper court judgements — into new GREP/RAG entries.

**Status:** the automated path **failed**. Two research workflows (21 subagents)
produced **0 usable output** — the *headless workflow subagents* could not reach
web/browser tools in their sandbox (the interactive main loop and Bash *can*).

**Recommended approach:** run this from an **interactive session with browser/web
tools**, or fetch the named sources directly by URL, then put every candidate
through the same adversarial-verify gate the 2026-05-28 manual set used — (1)
real citation in a primary/authoritative public source? (2) sound, tested regex
(no catastrophic backtracking)? (3) not a duplicate of an existing rule/doc? —
adding only survivors, then re-run `scripts/verify_knowledge_surfaces.py`.

**Risk:** low for content quality *if the verify gate is honored*; the only real
risk is admitting a plausible-but-wrong citation under time pressure. A
fabricated `RAG_CORPUS` citation is worse than a missing one because the harness
presents it as grounding — so this must stay human-verified, not model-guessed.

## (B) CLI `EvidenceStore` resource leak — **archived (low impact)**

**What:** ~14 CLI commands `EvidenceStore.open(...)` and call `.close()` only on
the happy path; an exception between open and close skips the close.

**Why archived:** each is a **one-shot CLI process** — on exit the OS reclaims
the SQLite handle within microseconds regardless of `.close()`. No long-running
CLI session accumulates handles, so the practical consequence is nil. (Contrast
the long-lived server, where the `evidence-db` sqlite thread-safety fix *was*
applied this session.)

**Recommended fix (low priority):** wrap each command body in
`with EvidenceStore.open(ctx.obj["db"]) as store:` (it is already a context
manager). **Risk:** a ~14-function re-indent — mechanical but worth a dedicated,
separately-tested pass rather than an opportunistic edit during a broad sweep.

## (C) evidence-db ingest at-rest path PII — **archived (wrong layer for an at-rest scrub)**

**What:** ingest stores raw absolute paths (which can contain the operator OS
username / internal codenames) in `runs.input_root`, `documents.image_path`,
`documents.source_pdf`.

**Why archived (not a naive at-rest scrub):** `image_path`/`source_pdf` are very
likely read back to **re-open local media**, and `doc_id` is hashed from the
original path — so scrubbing the stored value at-rest risks breaking file access
and doc-id stability. It is also a **local** store (paths are on the operator's
own machine); at-rest exposure is low.

**Recommended fix:** sanitize **on export/sync** (when the store leaves the
machine), not at-rest — strip the home/username prefix while preserving the
relative path for uniqueness, and keep the real path locally for reopening. This
puts the scrub at the actual trust boundary (the existing anonymizer + hub-submit
path is the model).

**Risk:** medium if done at-rest (functional breakage); low if done at the export
boundary as recommended.
