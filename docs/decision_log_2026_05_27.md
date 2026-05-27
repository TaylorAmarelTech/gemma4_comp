# Decision log & review notes — 2026-05-27

> Companion to [`handoff_2026_05_27.md`](handoff_2026_05_27.md). The handoff says
> **what** the state is; this says **why** the recent decisions were made, what was
> deliberately deferred, and what a future reviewer (a Claude Code 4.8 pass) should
> scrutinize. Written by the Opus 4.7 session that did the 2026-05-26→27 chat /
> grading hardening + the test-env recovery.

## How to read this

Each decision lists **what** was chosen, **why**, **what was rejected**, and a
**confidence** tag:

- **Verified** — actually ran / tested it.
- **By-construction** — source-audited / reasoned, but not functionally executed.
- **Judgment** — a defensible call worth revisiting if priorities differ.

## Decisions & rationale

### 1. Per-call inference cap as a single source of truth, enforced in the SSE layer
**Chosen.** One constant `inference_queue.MAX_INFERENCE_SECONDS = 45*60`, enforced
as a watchdog in both SSE generators (chat-send + grade-stream). On exceed, emit a
structured `{type:"error", reason:"inference_timeout"|"grade_timeout", code:504}`.
**Why.** The prior `MAX_CALL_SECONDS` was a *dead constant* — no per-call bound was
enforced anywhere, so a hung generate streamed keepalives forever. The structured
timeout doubles as the "logged unsuccessful call" signal the compare flow needs.
**Rejected.** A hard server-side kill of `model.generate()` — CUDA/Unsloth generates
are not safely cancellable; the cap bounds the *client's* wait, not the kernel-side
call (stated in the code comment).
**Confidence: Verified** (full suite green; cap value pinned by a test).

### 2. Resumable grading via per-dimension model-call memoization (not row caching)
**Chosen.** Cache the raw LLM *response string* per dimension; on resume, replay it
through the identical parse/score pipeline.
**Why.** Lowest possible risk to grade correctness — the counter/aggregate/parse
logic is **untouched**; the cache only changes *whether the model is called*, never
*how the answer is graded*. Same string in → same verdict out. The dict is mutated
in place, so dimensions graded before a stream cut persist for the next attempt.
**Rejected.** Caching parsed dimension *rows* — would have required reconstructing
the inline counter logic on resume (fragile; risk of skewing the aggregate).
**Confidence: By-construction.** Source-audited and the full suite passes, but there
is **no dedicated functional test** proving "2nd run makes 0 model calls + identical
aggregate." That test was infeasible while the system Python was broken; it is now
feasible on the recovery venv. See Worth-reviewing #3.

### 3. Resume-cache key made provably non-corrupting
**Chosen.** key = hash(chat model + distinct-evaluator identity + prompt + response
+ max_new_tokens + temperature + custom_questions + custom_envelope); stored size
capped at the parser's own 64 KB; only genuine non-empty output is cached.
**Why.** Every input that *determines* a verdict is in the key → no cross-arm,
cross-dimension, cross-prompt, or stale-model replay. Matching the parser cap makes a
cached re-parse byte-identical to a fresh parse. Errors/empties are never cached, so
transient per-dim failures retry.
**Residual (Judgment).** 64-bit truncated hash (collision negligible at <10
grades/session, 2 h TTL). The evaluator-swap case is closed by the kernel publishing
`app.state.evaluator_model_info`, consumed gated on `evaluator_call is not None`.
**Confidence: By-construction** (each corruption vector audited individually).

### 4. Per-dimension grading integrity beats performance (owner correction, internalized)
**Chosen.** One dimension per isolated judge call, full token budget. **Reverted** the
448-token compare-side cap I had added.
**Why (owner).** Batching dimensions into one call **blurs the verdicts together**; a
per-dimension token cap risks truncating an envelope. Both trade grading integrity
for speed — and speed is a *hardware* artifact (a T4 is slow; an A6000 grades each
call in seconds), never a valid reason to compromise the grade. Batching may exist
only as an opt-in advanced setting, never the default.
**My error this corrected.** I initially proposed batching + a token cap as
"optimizations." That was wrong. Recorded as a standing rule (project memory
`per-dimension-grading-integrity`) so it is not repeated.
**Confidence: Verified** (reverted; integrity test pins "no cap / never the default").

### 5. Local test env: a clean uv-managed Python *outside* OneDrive
**Chosen.** `scripts/recover_test_env.ps1` fetches standalone uv → a uv-MANAGED
CPython (intact stdlib) → a venv in `%LOCALAPPDATA%` (never synced) → pinned deps.
**Why.** The system Python is corrupted by OneDrive sync **down to the standard
library** — discovered one hole at a time: `typing_extensions` → the compiled
`pydantic_core.pyd` → `pydantic.main` → `html.entities`. Shadowing site-packages
cannot fix a corrupted stdlib, and `pip` is broken. The venv must live outside
OneDrive or sync re-corrupts it.
**Rejected.** Shadowing individual packages (whack-a-mole, can't fix stdlib);
reusing the system interpreter as a venv base (uv's first attempt did this — still
broken because the venv inherits the corrupted base stdlib).
**Confidence: Verified** (built the env; ran the grading subset and the full 1493).

### 6. The 17 pre-existing test failures: cataloged, not rush-fixed
**Chosen.** Prove they're pre-existing (run them on a pristine `master` worktree),
document each cluster + likely fix in the handoff, hand to the 4.8 review.
**Why.** They predate this session — the broken env simply hid them. They span
*published-kernel contracts* (A-00, 04) under the do-not-break rules, and the owner
asked for "without errors" + a dedicated 4.8 review. Rushing 17 multi-domain contract
fixes is the fastest way to introduce real errors. My grading work added **zero**
failures.
**Confidence: Judgment** (defensible; revisit if the owner wants them done now —
safest-first order is in the handoff §8).
**Update (2026-05-27, `d08650a`).** On owner request, fixed the highest-value
single cluster first — the 2 forge e2e cross-domain tests (test-only wiring,
verified green). **15 pre-existing failures remain**; the rest follow §8 order.

### 7. Workflow: commit + push directly to master, no PRs
**Chosen.** Per owner direction — direct commits/pushes to master; force-push
authorized (`--force-with-lease` preferred over bare `--force`); no feature branches
or PRs. Kaggle publishing stays manual.
**Confidence: Verified** (owner-directed; auth confirmed — owner account, `repo`
scope, master has no branch protection). Saved to memory.

## Things worth reviewing in the future

1. **The remaining 15 pre-existing full-suite failures** (was 17; 2 forge e2e
   fixed 2026-05-27) — the deeper remediation (handoff §4 has the per-cluster
   catalog + likely fixes). None touch the grading layer; several touch published
   kernels — keep fixes additive + re-run the Kaggle validators.
2. **Uncommitted in-flight work** — the 6-file benchmark-surface workstream and the
   ~1001-file cache/archive purge in the working tree. Decide commit-vs-revert
   deliberately; the single working-tree-only test failure clears once the notebook
   guide is regenerated against the modified generator.
3. **A functional resumable-grading test** — assert a 2nd run makes 0 model calls and
   returns an identical aggregate. Now runnable on the recovery venv (Decision 2).
4. **The 45-min cap is client-bound** — it cannot kill a runaway kernel-side
   `generate()`; the daemon worker + slot lock run until generate returns. True
   server-side cancellation would be a separate, hard change.
5. **codegraph** is installed but activates next session (MCP loads at startup).
   Verify it actually cuts navigation cost on the next pass; `codegraph uninstall`
   if not.
6. **CLAUDE.md is ~141 lines** — a PostToolUse hook suggests splitting long content
   into `.claude/rules/` or `@docs/`. Low priority; flagged for tidiness.
7. **Website / GitHub Pages standardization** — deferred (handoff §7). No Pages
   config; the site is `apps/duecare-ai.com`. Run its tests + `validate_public_surface.py`
   before touching public copy.
8. **Heuristic constants** — 45 min cap, 64 KB store cap, 5 s keepalive, 6-session /
   2 h cache TTL, 448→full judge budget. All defensible defaults; tune against real
   A6000/Blackwell timings if data warrants.

## Cross-references

- State + failure catalog: [`handoff_2026_05_27.md`](handoff_2026_05_27.md)
- Test env: [`local_test_env.md`](local_test_env.md) · `scripts/recover_test_env.ps1`
- Do-not-break contract: [`codex/00_do_not_break.md`](codex/00_do_not_break.md)
- Grading-integrity + workflow rules live in this session's project memory.
