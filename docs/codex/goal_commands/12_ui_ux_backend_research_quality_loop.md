# Goal command 12 — UI/UX + backend-wiring + research/benchmark quality loop (workflow-driven, runs for hours)

> Paste the block below (from `/goal` to the end) into Claude Code as a single
> autonomous goal. It is designed to run for many hours, use **workflows** for
> parallel fan-out **and** sequential loops, and stop only on a genuine blocker.
> It folds in the reliability lessons learned the hard way (file-only subagents,
> small judge batches, no scriptPath-resume caching).

---

/goal In `<repo-root>`, work on `master`, never switch branches. Run a long, autonomous, workflow-driven implementation-quality pass across the whole DueCare / Gemma 4 project: UI/UX clarity and button/action consistency, backend wiring, workflow gating, the research-frontier tools/spiders/facts, and the harness-lift benchmark + judging stack. Do not merely audit — inspect, improve, test, leak-scan, gate, commit, push, and continue in coherent loops.

READ FIRST (in order, skip any that are absent): `AGENTS.md`; `CLAUDE.md`; `.claude/rules/*.md`; `docs/codex/README.md`, `docs/codex/00_do_not_break.md`, `docs/codex/00_kernel_compatibility_gate.md`, `docs/codex/00_execution_order.md`, `docs/codex/goal_commands/README.md`, `docs/codex/goal_commands/11_iterative_branching_research_frontier.md`; the memory file `harness-lift benchmark (generate -> judge, 500->2000 scale)` and `feedback_synthetic_pii_allowed`. Honor every route, DOM-ID, static-page, Kaggle, activity-log, sample-artifact, model-loading, and PII/privacy constraint.

== HOW TO RUN (workflows + loops, for hours) ==
- This is a HYBRID of loops and workflows. Use the **Workflow** tool to fan work out in parallel; use sequential loop iterations to chain phases and stay in the loop between them. A typical hour = several workflows in sequence, each a well-scoped fan-out, with you reading results between them.
- **Reliability lessons (apply to every workflow — these were learned the hard way):**
  1. **File-only beats schema-return for any heavy subagent.** If a subagent's real work is writing a large file (a scorecard, an improved-prompt chunk, a page rewrite), do NOT also require a `schema` return — it drops ~40–100% of agents ("completed without calling StructuredOutput"). Have the agent WRITE its file and return one short text line; the file is the deliverable; ingest the files afterward. Reserve `schema` for light agents that only return a small structured summary.
  2. **Small batches for per-dimension / per-item heavy scoring.** ~5 items/agent. "All ~162 dims × 8 items/agent" overflows the output → sparse/garbage files.
  3. **Do NOT re-invoke a workflow via `scriptPath` to "run more" — it resume-caches** completed agent calls and returns 0-token no-ops. For a genuinely fresh run, launch a NEW inline workflow.
  4. **Prefer Ollama (gpt-oss:120b / gemma4:31b) or Sonnet subagents for scale**; Opus subagents throttle after heavy session use (0-token returns). Use Opus for small high-fidelity passes.
- **Loop pacing:** after each coherent slice — commit, push, then immediately pick the next highest-impact gap. Keep going for hours. Only stop on: missing credentials, a destructive/irreversible action needing sign-off, an unresolved PII/secret risk, or a validation blocker that recurs after three genuine fix attempts. Never stop just to ask "should I continue?".

== MISSION TRACKS (rotate; each is a workflow or a loop) ==

**Track A — UI/UX clarity + action consistency (highest priority).**
Review every workbench page and major flow: chat, compare, process / Bulk File Review, knowledge extraction, templates, search, anonymization/share, sync / status / models / settings, demo-recording / getting-started / use-cases, and the active Kaggle 01/02/A-00 surfaces. Fan out one subagent per page (file-only: each writes a findings + patch-plan file), then implement.
Hunt specifically for the **gating-button problem Taylor flagged**: a required *Finalize / Polish / Confirm / Save / Attach / Generate / Promote / Submit / Use / Continue* action that is unclear, inconsistently sized/colored, in an unexpected location, below the fold, separated from the dependent next action, disabled without explanation, or silently required before the next partition/step works.
Standardize the action hierarchy WITHOUT removing functionality:
- primary next-step actions → consistent primary styling + placement;
- secondary actions → visually secondary; destructive/irreversible → clearly separated + labeled;
- disabled buttons → MUST explain the missing prerequisite (visible text / tooltip / activity log / status row);
- every multi-step flow → expose current step, next action, blocking prerequisite, progress, and result; a success state must visibly unlock/point to the next step;
- a backend error must surface in the activity log / status row, never only console or raw HTTP.
Preserve shared primitives: model loading stays in `_nav.js` / `_nav.html` / `_chrome.css`; reuse `window.dcWbModelService`, `dcActivityLog`, `dcInferenceError`, `dcGemmaStats`, trust rows, progress strips, replay/export patterns, reviewer-gated language. Reuse existing styles before inventing; additive over destructive.

**Track B — backend wiring for every UI action touched.**
For each action: verify button → JS handler → API route → response handling → activity log → status/progress → export/replay path is complete, honest, and tested. Add route tests or static contract tests wherever a UI depends on backend behavior. A Gemma-dependent action must honestly mark queued / done / skipped / unavailable.

**Track C — research frontier (tools / spiders / facts).**
Continue the research-frontier capability: safe search providers, scrapers/spiders/crawlers, extractors, source profiles, verified knowledge objects, corroboration links. OSINT-adjacent tools are DESIGN REFERENCES ONLY — do NOT add people/email/subdomain/credential harvesting, proxy rotation, evasion, CAPTCHA/paywall/login bypass, stealth automation, or private-data upload. Keep no-network deterministic fallbacks + synthetic fixtures. Files: `scripts/public_research_spider.py`, `scripts/public_search_providers.py`, `scripts/public_fetch_extract.py`, `scripts/public_tool_survey.py`, `scripts/major_case_pattern_extractor.py` and their tests + `configs/duecare/benchmarks/research_spider/*`, `configs/duecare/benchmarks/major_case_patterns/*`.

**Track D — harness-lift benchmark + judging stack (this session's work).**
The benchmark measures DueCare-harness safety lift (baseline vs harnessed) across a 162-dim rubric. Key files: `scripts/harness_lift_local.py` (Ollama generation, both arms, persists responses), `scripts/harness_lift_opus_judge.py` (batch → judge → ingest; `make_batches` now attaches per-prompt RELEVANT `dim_ids`), `scripts/dimension_selector.py` (rule-based applicability + sector/corridor normalization), `scripts/applicability_judge.py` (model judge that augments the rules), `scripts/prompt_remixer.py` (anti-benchmark-maxing variants + held-out split), `scripts/build_lift_report.py` (HTML report with egregious examples), `scripts/setup_harness_lift_configs.py` (corpus + rubric). Corpus: `configs/duecare/benchmarks/harness_lift_prompts_*.json` + `harness_lift_prompts_expansion.jsonl`. Generated artifacts stay under `reports/` (gitignored).
Loop tasks here, in order: (1) tag the full 1,000-prompt set with the applicability judge (`applicability_judge.py`, gpt-oss:120b via Ollama, resumable) so judging uses `rules ∪ model-judge` relevant dims; (2) judge the completed 1,000-prompt gemma4 responses with a **gpt-oss:120b file-only judge in small batches** using the per-prompt `dim_ids` (scalable, independent, not Opus-throttled) → the converged 1,000-prompt with/without-harness number; (3) keep a small Opus per-dimension high-fidelity subset; (4) after each judging pass, `python scripts/build_lift_report.py` and surface the new lift table + egregious examples; (5) grow + verify+improve the corpus with file-only Sonnet workflows; never let a fixed prompt set ossify (use the remixer + held-out split). Synthetic PII IS allowed and encouraged in fixtures; only REAL PII is forbidden.

== LOOP BEHAVIOR (repeat for hours) ==
1. Baseline branch/status + artifact counts (corpus size, dims, judged cells, report freshness, page count).
2. Pick the single highest-impact gap across Tracks A–D.
3. Inspect the ACTUAL implementation before editing (read the file/route/page).
4. Implement one coherent slice (workflow fan-out where parallelizable; direct edits where not).
5. Add or update deterministic tests for every new wiring contract / artifact generator / UI contract.
6. Run focused tests + a leak scan over changed files.
7. Run the relevant repo gates (below).
8. Commit + push a coherent increment (conventional-commit message; never `--no-verify`).
9. Update handoff/run-state if research-frontier or benchmark artifacts changed.
10. Continue to the next gap without asking.

== VALIDATION (use the project testenv when local Python is broken: `%LOCALAPPDATA%\gemma4-testenv\venv\Scripts\python.exe`) ==
- Focused: `python -m pytest tests/test_templates_batch_fill.py tests/test_public_research_spider.py tests/test_public_search_providers.py tests/test_public_fetch_extract.py tests/test_public_tool_survey.py tests/test_major_case_pattern_extractor.py tests/test_dimension_selector.py tests/test_applicability_judge.py tests/test_harness_lift_*.py tests/test_prompt_remixer.py tests/test_build_lift_report.py -q`
- `python scripts/validate_public_surface.py`
- `python -m pytest packages --collect-only -q`
- `python scripts/validate_main_kaggle_kernels.py`
- `py -3.12 scripts/validate_kaggle_page_sources.py`

== PRIVACY & SAFETY (hard gates) ==
- Never copy `C:\projects\major_cases` into the repo. Never commit raw PII, private filenames, private case text/URLs, document numbers, contacts, screenshots, OCR text, logs, API keys/tokens, or raw private snippets. Do not paste private case text into web search or remote models. Public facts must be paraphrased, dated where possible, and provenance-linked. Synthetic/composite PII in test fixtures is fine.
- Before EVERY commit: `git diff --check` + a targeted leak scan for: `C:\projects\major_cases|/projects/major_cases|AQ\.Ab8RN6|c72673292f|7ee83f50|raw private filenames|unredacted emails|phone-like strings|passport-like strings|account-like IDs`. Keys belong in env only.

== FINAL HANDOFF (when you must stop) ==
Report: commit SHA(s) + push status; UI/UX flows improved (per page, with the specific gating-button fixes); backend routes/wiring fixed + tests added; research/tool/spider artifacts changed; benchmark state (corpus size, dims, prompts judged, latest with/without-harness lift table, report path); validation results; leak-scan result; remaining risks; and the next 30 autonomous branches.
