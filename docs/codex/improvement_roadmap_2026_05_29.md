# Surface improvement roadmap — 2026-05-29

> From a read-only survey (workflow, 4 agents) of UI/UX, notebooks/Kaggle,
> APK/phone, and the benchmarking surface, plus a live harness-lift run. Items
> are split into **DONE this session** and **archived-with-reasoning** (build
> plan + risk), so nothing is dropped silently.

## Live harness-lift result (real models, your keys)

The model-agnostic harness lift now runs against real models
(`scripts/run_harness_lift_live.py`, Ollama Cloud + Gemini, keys via env only):

- **gemini-2.5-flash**, public synthetic prompts, judge gemini-2.5-flash:
  baseline scores were already high (it is a strong model) and the harness
  produced a small but **positive** lift (e.g. fee/passport/debt 9.0 -> 10.0).
  The **new GREP rules fire correctly on real prompts** (e.g.
  `c189_domestic_worker_no_weekly_rest`, `passport_document_safekeeping_euphemism`,
  `c188_fishing_no_agreement_or_at_sea_retention`, `contract_substitution_on_arrival`).
- **Two runner bugs found + fixed** along the way: (1) gemini-2.5-flash is a
  *thinking* model — it consumed the output-token budget on reasoning and
  truncated answers/judge-JSON, so everything scored 0.0; fixed with
  `thinkingConfig.thinkingBudget=0`. (2) the judge silently returned 0.0 on an
  unparseable response; it now strips code fences and **raises** on failure so
  a judge error never masquerades as a real zero.
- **Ollama Cloud free tier hard rate-limits (HTTP 429)** even with backoff +
  pacing, so the open-model arms (gpt-oss:20b, gemma4:31b) could not complete.
  The bigger lift is expected on *weaker* models; measuring it needs adequate
  Ollama quota (paid tier) or a local Ollama server. The runner already
  supports them — `LIFT_ONLY=Ollama LIFT_PACE=20` with quota.

**Recommended next:** with Ollama paid quota (or local Ollama), run the full
table (gpt-oss:20b + gemma4:31b + gemini-2.5-flash, all arms) and publish the
lift chart — the open-model lift is the on-mission headline ("DueCare lifts a
self-hostable model toward frontier-grade safety").

## UI/UX (workbench static pages)

**DONE:** global `@media (prefers-reduced-motion: reduce)` in `_chrome.css`
(several infinite animations looped during the video — WCAG 2.2.2); modern
`clip-path: inset(50%)` on `.dc-sr-only`.

**Archived-with-reasoning:**
- **Model-load modal focus trap.** The required model gate (`_nav.js`
  `openModelPopover`) sets `aria-modal` + handles Escape/outside-click but has
  no `Tab` focus containment — keyboard users can Tab behind the overlay.
  *Build:* add a Tab-cycle keydown handler while `modelSelectorRequired`, restore
  focus to the opener on close. *Risk:* medium (must not trap focus in the
  non-required quick popover) — needs a focused, tested pass.
- **`--ink-4` (#8A8E97) fails WCAG AA (~2.6:1)** where used for real caption
  text. *Build:* darken to ~`#71757E` or repoint `.hint`/`.dc-empty-hint`
  content to `--ink-3`; keep `--ink-4` only for exempt placeholders.
- **Per-page `<style>` blocks re-hardcode palette hex** (process.html,
  index.html) and `grep-tester.html` aliases `--accent` to the privacy-reserved
  `--ember`. *Build:* replace hex with chrome tokens; stop the ember alias
  (rule 60/70: ember is the privacy boundary color only). *Risk:* medium, do
  one page at a time.
- **Chat (`index.html`) fallback activity-log renders off-screen** (no `<main>`,
  100vh shell). Inline per-message step events already satisfy rule 70, so the
  off-screen card is redundant. *Build:* suppress the auto-injected log on chat
  via a `data-suppress-autolog` attr in `_nav.js`.

## Notebooks / Kaggle

**DONE:** README-01 A-00 cross-links repointed from `_archive/notebooks/` to the
active `../A-00-omni-experiment-workbench/` and relabeled active (they
contradicted `_INDEX.md` + CLAUDE.md rule 80, routing judges into the archive).

**Archived-with-reasoning:** remaining mojibake/encoding artifacts and any
kernel/README slug drift the survey flagged — text-only cleanups; do in a
dedicated pass and re-run `scripts/validate_public_surface.py` (local_doc_links).

## APK / local-phone (on-device Gemma 4)

**Honest status (archived — external repo):** there is **zero native mobile
code in this repo** — no `.kt`/`.gradle`/`.apk`/`.tflite`/LiteRT source. The
Android app, if it exists, lives in a separate untracked repo
(`duecare-journey-android`) and is **not buildable/verifiable from here**. The
only in-repo "on-device" code (`portability.py`) just tags Gemma variants for
the *Kaggle GPU* workbench (desktop, not phone).

**CREDIBILITY hazard to fix (doc-only, do next):** the mobile-status docs
**contradict each other** — `docs/android_app_architecture.md` says "APK
skeleton" while other docs imply a shipped build. A judge who notices this
discounts every "real, not faked" claim (rubric goal 4). *Build:* reconcile the
mobile docs to ONE honest status and clearly state the on-device build lives in
the external repo (link it). Do not claim a shipped APK from this repo.

## Benchmarking surface

**DONE:** `harness_lift` module + `harness_lift_benchmark.py` orchestrator +
`run_harness_lift_live.py` (live) + sample config + `docs/benchmarking.md`.

**Archived-with-reasoning (contradiction to resolve):** `docs/benchmarking.md`
and the sample config describe an `"arms": ["baseline","harnessed"]` capability,
but `kaggle/03-universal-llm-benchmark/kernel.py` `run_benchmark` is **single-arm
only** (it calls each target once, no preamble, no lift column). A judge who
copies kernel 03 and sets `arms` gets a silent baseline-only run. *Build (pick
one):* (a) implement the harnessed arm in kernel 03 (import `build_harness_preamble`,
add the lift column) — the on-kernel reproducible path; or (b) make the docs
state plainly that the baseline-vs-harnessed lift runs via the NEW orchestrator
(`harness_lift_benchmark.py` / `run_harness_lift_live.py`), and kernel 03 stays
single-arm. Option (a) is the stronger reviewer artifact.
