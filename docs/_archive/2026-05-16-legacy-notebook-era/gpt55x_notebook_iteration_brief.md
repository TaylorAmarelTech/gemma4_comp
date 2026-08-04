# DueCare Kaggle Kernels â€” Iteration Brief for GPT 5.5x

> **Current workflow correction (2026-05-11).** The active submission is
> kernel-first, not notebook-first. Treat `kaggle/*/kernel.py` plus each
> folder `README.md` as source. Do not create, regenerate, or edit `.ipynb`
> files in active Kaggle folders; historical wrappers live under
> `_archive/kaggle-notebook-previews-2026-05-11/`.

> **Self-contained brief.** Paste this whole document into GPT 5.5x. No
> external file fetches required. Goal: **iterate and improve** all 27
> Kaggle script kernels (3 core + 24 appendix) toward production polish
> suitable for the 3-minute hackathon screen-recording video. Output
> concrete edits / diffs / file contents, not just recommendations.

---

## 0. Read this first

Today is **2026-05-11**. The Gemma 4 Good Hackathon submission is due
**2026-05-18** â€” T-7 days. The submission publishes **27 Kaggle kernel folders**
plus a public website plus a writeup plus a 3-minute video.

**The video is a screen recording of the live product**, not slides or
mock-ups. Every UI surface a camera might pan past must look intentional
and finished before recording begins. A re-record is expensive (Taylor's
time + GPU quota + cloudflared session continuity).

Your job is **not to redesign from scratch**. The visual system, audience
lanes, shell primitives, dashboards, and dc_log standard are all in
place and proven. Your job is to **find every remaining friction point**
across all 13 kernels, propose specific edits, and where appropriate
output the actual code/HTML to apply.

Baseline when this brief was drafted: **commit `3e3ff9e`** on `master`.
Claude Code has made follow-up edits since then, so inspect the current
working tree before proposing or applying changes. Current package pins
remain **`duecare-llm-chat 0.16.0`** (kernel-shell `homepage_html` +
`extra_routes` extension) and **`duecare-llm-server 0.1.2`**
(`/wb-static/` cross-mount) unless `pyproject.toml` says otherwise.

**2026-05-11 checkpoint:** a conservative first pass has already landed.
Do not redo it or reintroduce stale inventory assumptions. The former
`kaggle/kernels/*` inventory is archived under
`_archive/kaggle-notebook-previews-2026-05-11/`, while the judge-facing root
submission remains **13 folders** under `kaggle/`. The pass pinned the 01
workbench Git fallback, added install-policy regression tests for moving Git
refs, normalized historical preview metadata, redacted visible
demo sample identifiers, aligned A-08 sample chart colors to the design
tokens, and removed A-09 displayed `result_summary` truncation. Validation
passed for targeted Kaggle tests and the public surface audit. If
`kaggle/01-duecare-harness-chat/kernel.py` appears in an
agent report, verify the filesystem first; as of this checkpoint it does not
exist and is not tracked.

---

## 0.1 What's done (Phase 1) and what's left for you (Phase 2)

This brief was prepared in two phases. **Phase 1 has already landed
on `master`.** You're picking up Phase 2.

### 2026-05-11 direction update â€” make the appendices an experiment ladder

Taylor's latest preference is that the appendix sequence should read less
like a loose collection of playgrounds and more like a reproducible model
improvement pipeline. The current A-01 purpose is **raw interactive Gemma 4
chat with the DueCare harness off**. That is useful as a visual baseline, but
it is not yet the stronger batch-evaluation kernel Taylor wants: selected
Gemma 4 model -> shared prompt library -> harness off -> downloadable results
and metadata.

Target appendix flow to evaluate against during Phase 2:

1. **Appendix 01 â€” Stock Gemma 4 baseline runner.** User selects any Gemma 4
  model, runs the shared test-prompt library with the harness off, and
  downloads raw model responses plus run metadata.
2. **Appendix 02 â€” Harnessed Gemma 4 runner.** User selects the same Gemma 4
  model, runs the same shared prompt library with the DueCare harness on,
  and downloads harnessed responses plus trace metadata.
3. **Appendix 03 â€” Baseline vs harness comparison.** User uploads A-01 and
  A-02 artifacts. The kernel runs both the new harness evaluator and the
  legacy harness evaluator, then renders comparison visuals and exports the
  evaluation package.
4. **Appendix 04 â€” Synthetic training-data generator.** Gemma 4 + harness
  generates synthetic SafetyJudge training/test prompts and graded response
  ladders using `WORST`, `BAD`, `NEUTRAL`, `GOOD`, `BEST` labels.
5. **Appendix 05 â€” Synthetic-data fine-tune.** Trains a new Gemma 4 adapter or
  model from the A-04 synthetic training data, with small-model settings for
  quick validation and larger-model settings for final runs.
6. **Appendix 06 â€” Fine-tuned model baseline runner.** Same job as A-01, but
  using the newly trained model or adapter.
7. **Appendix 07 â€” Fine-tuned model harnessed runner.** Same job as A-02, but
  using the newly trained model or adapter plus harness.
8. **Appendix 08 â€” Fine-tuned comparison.** Same job as A-03, but comparing
  fine-tuned off/on artifacts and showing stock-vs-fine-tuned deltas.
9. **Appendix 09 â€” Abliterated adversary data generator.** Uses abliterated or
  less-aligned Gemma variants to develop harder legacy tests and response
  ladders with Worst/Bad/Neutral/Good/Best semantic examples. These rows are
  adversarial/evaluation material, not trusted Best-label SFT rows unless
  reviewed.
10. **Appendix 10+ â€” Privacy/PII fine-tuning track.** Dedicated kernels for
  generating synthetic/composite anonymization cases, training a Gemma 4
  PrivacyRedactor adapter, and evaluating leakage prevention behind
  deterministic PII gates.

Constraints for this ladder:

- Every runner should allow a Gemma 4 model selection, but default to the
  smallest viable Gemma 4 model for smoke tests to protect Kaggle memory and
  time.
- Every kernel should assume **one loaded model per run**. Cross-kernel
  handoff happens through downloadable JSONL/JSON/ZIP artifacts and Kaggle Add
  Data, not live kernel links.
- Do not physically add or rename kernels until Taylor approves the roster
  change. First review task: map the current 13 kernels onto this target
  ladder, mark which current kernels already satisfy the target, and list
  which ones need reframing, merging, or replacement.

### Phase 1 â€” completed (do not redo these)

Verify against the commit log if you doubt any item, but don't propose
them again as "edits":

- **Workbench shell unified across 5 surfaces.** Kernel #01
  (chat-shell), #02 live-demo (server-shell with `/wb-static/`
  cross-mount), A-03 / A-04 / A-09 (custom-FastAPI kernels pulling
  `/wb-static/_chrome.css` + `/wb-static/_nav.js`), plus A-01 / A-02
  / A-10 (chat-shell).
- **5 audience showcase pages.** `showcase-platform.html`,
  `showcase-ngo.html`, `showcase-worker.html`, `showcase-researcher.html`,
  `showcase-developer.html` â€” each has 3 curated corridor-grounded
  prompts that deep-link to the chat homepage via `?prompt=&audience=`.
- **`build_minimal_shell()` extended** with `homepage_html` +
  `extra_routes` kwargs (backward-compatible). Default summary view
  stays at `/summary` for the Tools menu.
- **4 bespoke dashboards live** for the kernel-rendered dashboards:
  A-11 lift dashboard, A-08 inline Plotly viewer, A-07 9-phase
  training pipeline, A-06 corpus browser. Each exports JSON + CSV +
  domain-specific routes (`/api/lift`, `/api/charts`,
  `/api/eval-results`, `/api/prompts`).
- **`dc_log` JSON-Lines logging primitive** wired into hot paths
  (chat.send, chat.reply, grep.test, grade.run, import.upload). Logs
  page at `/static/logs.html` reads `/api/dc-logs?tail=N&level=&kind=&layer=`.
- **All 13 kernel-metadata.json IDs** match folder names (e.g.
  `taylorsamarel/duecare-exploration-workbench`). Dataset sources
  attached for each.
- **All 13 kernel.py files have a `<!-- duecare:kernel-intro -->`
  header block** â€” uniform 14-line summary at the top with the demo
  path and what-to-look-for-after-Run-All.
- **Cross-link footer added to all 13 READMEs.** Standard 4-link
  block: workbench â†’ live-demo â†’ kernel-specific "next step"
  sibling â†’ public website. The "next step" choice is curated per
  kernel to drive a 5-minute judge journey. Treat A-06 â†’ A-07 as the
  synthetic-data â†’ adapter-training path. Treat A-11 as runtime harness
  OFF/ON lift only; it does **not** verify fine-tuned-model lift.
- **28 docs / 40 references renamed** `01-duecare-harness-chat` â†’
  `01-duecare-exploration-workbench` across active markdown (READMEs,
  FOR_KAGGLE_JUDGES, REPO_LAYOUT, kaggle/_INDEX, etc.). `_archive/`
  left untouched.
- **First-pass conservative polish (also landed)**: pinned the 01
  workbench Git fallback, added install-policy regression tests for
  moving Git refs, normalized historical preview metadata, redacted
  visible demo sample identifiers, aligned A-08 sample chart colors
  to the design tokens, and removed A-09 displayed `result_summary`
  truncation.
- **Public-surface audit: 4/4 OK, 0 findings, 41 routes probed.**
- **`duecare-llm-chat 0.16.0`** + **`duecare-llm-server 0.1.2`**
  built and propagated to all 13 `kaggle/*/wheels/` folders.

### Phase 2 â€” what you (GPT 5.5x) own now

These are deliberately deferred because they need your judgment, are
higher-effort, or are stylistic preferences worth a second pair of eyes:

1. **HIGHEST PRIORITY â€” convert all 11 wheel-loading kernels to
   GitHub-only install.** Policy as of 2026-05-11: **all DueCare
   packages must install directly from GitHub. No attached Kaggle
   `*-wheels` datasets.** Notebook 01 (`kaggle/01-duecare-exploration-
   workbench/kernel.py` â€” function `install_chat_wheels()`) is the
   canonical reference. The pattern is two-tier:
     - **Method 1:** GitHub Release wheels at
       `https://github.com/TaylorAmarelTech/gemma4_comp/releases/download/v{VERSION}/{wheel_name}`.
     - **Method 2 (fallback):** GitHub source install via
       `git+https://github.com/TaylorAmarelTech/gemma4_comp.git@{COMMIT_SHA}#subdirectory=packages/{package}`.

   What's already done by Phase 1: every `kernel-metadata.json` has had
   its `*-wheels` slug stripped from `dataset_sources` (13/13). The
   `_INDEX.md` "How to run" docs now say "enable Internet" instead of
   "Add data â†’ wheels dataset".

   What's NOT done and is your job: rewrite the install function in
   each of the 11 kernels that still walk `/kaggle/input/**/*.whl`:
   A-01, A-02, A-03, A-04, A-05, A-06, A-07, A-08, A-09, A-10, A-11.
   For each kernel:
     - Remove the `DATASET_SLUG = "...-wheels"` constant.
     - Remove any `Path("/kaggle/input").rglob("*.whl")` discovery.
     - Remove any "Add Data â†’ datasets â†’ ..." error messages.
     - Replace the install function body with notebook 01's two-tier
       pattern, parameterized by the package list this kernel needs.
     - Most kernels need only `["duecare-llm-chat"]` (it transitively
       pulls in `duecare-llm-core`). A-07 also needs models for
       fine-tuning. A-11 explicitly imports core + models + chat.
     - Bump the pinned `COMMIT_SHA` to whatever the latest master
       SHA is when you run.
   Note: physical `kaggle/*/wheels/` directories can stay â€” they're
   harmless leftovers. Don't delete them as part of this pass; Taylor
   will sweep them separately. Just stop referencing them from the
   kernel.py install code.

2. **"DueCare" vs "Duecare" capitalization.** Mixed across the repo
   (22 vs 43 in `apps/`, 8 vs 8 in workbench static, 1 of 13 kernel
   titles is "DueCare", 12 are "Duecare"). The public-website nav
   says "DueCare AI" (CamelCase). Recommend a canonical pick and
   output the full replacement set as a single batch edit.

2. **Per-kernel polish review (Layer A in Â§16 below).** For each of
   the 27 (3 core + 24 appendix), output the top 5 concrete edits with
   file:line precision.
   Cover the empty/loading/error states each kernel hits before the
   model loads â€” those are camera-on moments.

3. **README skeleton uniformity.** Each README has a different last
   pre-cross-links section (Troubleshooting / Status / Publishing /
  Publishing options / What this kernel is NOT). Propose the
   canonical 6-section skeleton (Lede, What it does, Demo path,
   Audience, Outputs, Cross-links) and output the gap-fill edits.

4. **Above-the-fold homepage clarity** for each served-UI kernel â€”
   what does a judge see in the first 800 pixels before scrolling?
   Audit the 5 chat-shell kernels (01, A-01, A-02, A-10), the
   server-shell kernel (02), the 3 custom-FastAPI kernels (A-03, A-04,
  A-09), and the 4 kernel-rendered dashboards (A-06, A-07, A-08, A-11).

5. **Status strip API shape consistency.** Every served-UI kernel
   should return the same fields from `/api/version` + `/api/model-info`
   so the status strip renders identically. Audit, list deltas,
   propose the canonical shape.

6. **The 3-minute click path (Layer C).** Exact open-URL â†’ pause â†’ click
   â†’ cut sequence with time budgets per action.

7. **Risk register (Layer D).** Top 8 risks ranked by score impact and
   cost-to-fix.

8. **Anything I missed.** If you find a friction point that doesn't
   fit a layer, flag it as an item 9+ in Layer A or as a sidebar in
   Layer B.

### Phase 2 â€” explicit "do not" guardrails for you

- **Do not bump wheel versions on your own.** Chat is at `0.16.0`,
  server at `0.1.2`. Only bump if Taylor asks â€” propose the diff for
  approval first.
- **Do not modify `_chrome.css`, `_nav.html`, `_nav.js`, `showcase.css`,
  or `_dc_log.py`.** These are source-of-truth primitives. If you find
  a bug or alignment gap there, raise it as a sidebar item under Layer
  B (cross-kernel), not as a per-kernel edit.
- **Do not create `.ipynb` notebooks by default.** The 13 active folders are the
  script-kernel submission set. Composition-only changes unless Taylor explicitly
  approves a split. For the current training story, keep two tracks inside
  A-06/A-07 rather than adding A-12: SafetyJudge anti-exploitation data and
  PrivacyRedactor anonymization data.
- **Do not publish, push, or upload anything to Kaggle.** Taylor handles
  that manually (see Â§15). Local edits only.
- **Do not touch `_archive/`, root `legacy_notebooks/`, or `skunkworks/`.**
  Frozen historical material.
- **Do not introduce new dependencies** (no new pip installs, no new
  third-party libraries beyond what's in the wheels).
- **Do not refactor `kernel.py` files into modules / packages.** Each
  kernel is intentionally a single paste-able file for Kaggle.

---

## 1. Mission (one paragraph)

You are reviewing **DueCare** â€” a Gemma 4-powered safety harness for
migrant-worker protection. The harness wraps Gemma 4 with persona +
161 deterministic GREP regex rules + 46-doc RAG corpus across 27
jurisdictions + 5 function-calling tools + an optional online-search
layer, so the model produces grounded, citable, audience-appropriate
responses about labor recruitment, fee scams, passport retention, debt
bondage, and corridor-specific legal protections. The Kaggle submission
contains **3 core + 24 appendix = 27 script kernels** â€” all visible to judges.
Each has a `kernel.py` (script kernel source) and a `README.md`. The
team has unified them under a shared workbench shell built around three
primitives (`_chrome.css`, `_nav.js`, `dc_log`) plus four bespoke
dashboards (A-06/07/08/11). The remaining work: tighten every visible
surface so the screen recording goes cleanly on the first take.

---

## 2. Hackathon rubric (the scoring math)

| Weight | Axis | What it measures |
|---|---|---|
| 40 | Impact & Vision | Does this address a significant real-world problem? Is the vision inspiring and the potential change tangible? **Verified in the video.** |
| 30 | Video Pitch & Storytelling | How exciting/engaging/well-produced is the video? Does it tell a powerful story? |
| 30 | Technical Depth & Execution | Innovative use of Gemma 4's unique features (native function calling, multimodal). Real, functional, well-engineered, not faked for the demo. **Verified from code + writeup.** |

**70 of 100 points are under the video's control.** Every polish task
should be judged by: does this advance Impact, Video, or Tech-Depth?
If none, cut it.

**Tie-breaker:** Impact > Video > Tech.

---

## 3. The 5 canonical audiences (do not invent new ones)

Source-of-truth: `configs/duecare/canonical_messaging.yaml` +
`docs/canonical_use_cases_and_components.md`.

| Lane | Name | Primary need |
|---|---|---|
| 1 | **Platform safety** | Trust & safety teams scoring recruitment posts/messages, routing high-risk items to reviewers, sharing anonymized abuse patterns. |
| 2 | **NGO & regulator** | Caseworkers, legal-aid groups, consulates, labor inspectors triaging messages and documents, finding contacts, drafting complaint materials. |
| 3 | **Individual worker** | Migrant workers privately checking suspicious offers, contracts, recruiter messages, fee demands; getting localized warning signs and trusted next-step contacts. |
| 4 | **Researcher** | Academic and public-interest researchers reproducing prompts, comparing models, scoring responses, auditing claims from source artifacts. |
| 5 | **Developer / integration partner** | Devs embedding the harness into moderation tools, NGO systems, mobile clients via APIs and pinned wheels. |

Banned alternatives (these labels have been explicitly retired):
"social platforms", "enterprise", "worker-side", "NGO dashboard",
"custom integration", "activist", "media", "OFW".

---

## 4. Repo layout (the relevant slice)

```
gemma4_comp/
â”œâ”€â”€ apps/
â”‚   â””â”€â”€ duecare-ai.com/                        â† public website (deployed to Render)
â”‚       â””â”€â”€ app/
â”‚           â”œâ”€â”€ static/styles.css               â† public-site CSS (uses same tokens)
â”‚           â””â”€â”€ templates/_nav.html             â† single-row nav template
â”œâ”€â”€ packages/
â”‚   â”œâ”€â”€ duecare-llm-chat/                      â† chat package (the workbench)
â”‚   â”‚   â”œâ”€â”€ pyproject.toml                      â† version 0.16.0
â”‚   â”‚   â””â”€â”€ src/duecare/chat/
â”‚   â”‚       â”œâ”€â”€ app.py                          â† FastAPI app factory + chat endpoints
â”‚   â”‚       â”œâ”€â”€ kernel_shell.py                 â† build_minimal_shell() helper
â”‚   â”‚       â”œâ”€â”€ _dc_log.py                      â† JSON-Lines logging primitive
â”‚   â”‚       â””â”€â”€ static/
â”‚   â”‚           â”œâ”€â”€ _chrome.css                 â† design tokens + shell styles
â”‚   â”‚           â”œâ”€â”€ _nav.html                   â† status strip + single-row nav
â”‚   â”‚           â”œâ”€â”€ _nav.js                     â† auto-injects nav, polls APIs
â”‚   â”‚           â”œâ”€â”€ showcase.css                â† shared audience-page styles
â”‚   â”‚           â”œâ”€â”€ index.html                  â† chat homepage (data-nav="chat")
â”‚   â”‚           â”œâ”€â”€ showcase-*.html             â† 5 audience landing pages
â”‚   â”‚           â”œâ”€â”€ all-tools.html              â† Tools menu index
â”‚   â”‚           â”œâ”€â”€ grade.html                  â† standalone grader (data-nav="grade")
â”‚   â”‚           â”œâ”€â”€ models.html                 â† model picker (data-nav="models")
â”‚   â”‚           â”œâ”€â”€ logs.html                   â† dc_log viewer (data-nav="logs")
â”‚   â”‚           â”œâ”€â”€ import.html                 â† doc import (data-nav="import")
â”‚   â”‚           â”œâ”€â”€ settings.html               â† retrieval/online config (data-nav="settings")
â”‚   â”‚           â”œâ”€â”€ harness.html                â† layer catalog (data-nav="layers")
â”‚   â”‚           â”œâ”€â”€ persona.html                â† (data-nav="layers")
â”‚   â”‚           â”œâ”€â”€ grep-rules.html             â† (data-nav="layers")
â”‚   â”‚           â”œâ”€â”€ grep-tester.html            â† (data-nav="layers")
â”‚   â”‚           â”œâ”€â”€ rag-corpus.html             â† (data-nav="layers")
â”‚   â”‚           â”œâ”€â”€ rag-graph.html              â† (data-nav="layers")
â”‚   â”‚           â”œâ”€â”€ tools.html                  â† function-calling tools (data-nav="layers")
â”‚   â”‚           â”œâ”€â”€ online.html                 â† (data-nav="layers")
â”‚   â”‚           â”œâ”€â”€ search.html                 â† cross-layer search (data-nav="search")
â”‚   â”‚           â”œâ”€â”€ hotlines.html               â† hotline directory (data-nav="hotlines")
â”‚   â”‚           â””â”€â”€ anonymization-preview.html  â† (data-nav="anonymize")
â”‚   â””â”€â”€ duecare-llm-server/                    â† server package (the public hub)
â”‚       â”œâ”€â”€ pyproject.toml                      â† version 0.1.2
â”‚       â””â”€â”€ src/duecare/server/
â”‚           â”œâ”€â”€ app.py                          â† FastAPI app + /wb-static/ cross-mount
â”‚           â””â”€â”€ static/                         â† server-specific homepage assets
â””â”€â”€ kaggle/
    â”œâ”€â”€ 01-duecare-exploration-workbench/      <- CORE kernel #1
    â”‚   â”œâ”€â”€ kernel.py
    â”‚   â”œâ”€â”€ kernel-metadata.json
    â”‚   â”œâ”€â”€ README.md
    â”‚   â””â”€â”€ wheels/                             â† duecare-llm-chat-0.16.0.whl + deps
    â”œâ”€â”€ 02-live-demo/                          <- CORE kernel #2
    â”œâ”€â”€ A-01-chat-playground/                  â† appendix
    â”œâ”€â”€ A-02-chat-playground-with-grep-rag-tools/
    â”œâ”€â”€ A-03-content-classification-playground/
    â”œâ”€â”€ A-04-content-knowledge-builder-playground/
    â”œâ”€â”€ A-05-gemma-content-classification-evaluation/
    â”œâ”€â”€ A-06-prompt-generation/                â† has corpus-browser dashboard
    â”œâ”€â”€ A-07-bench-and-tune/                   â† has training-pipeline dashboard
    â”œâ”€â”€ A-08-research-graphs/                  â† has inline-chart dashboard
    â”œâ”€â”€ A-09-chat-playground-with-agentic-research/
    â”œâ”€â”€ A-10-runtime-vs-weights-safety-study/
    â””â”€â”€ A-11-grading-evaluation/               â† has lift dashboard
```

---

## 5. Design system (the visual source of truth)

The public website (https://duecare-ai.com) is the canonical aesthetic.
The chat package's `_chrome.css` and server package's `style.css` both
import the same tokens. Every kernel UI must match.

**Aesthetic direction:** civic-tech research lab. Warm paper backgrounds,
not stark white. Dark ink text, not gray-on-gray. Civic teal accent used
sparingly. Ember orange reserved exclusively for privacy-boundary
indicators. No generic Tailwind defaults, no dark mode (except the
intentional shutdown overlay).

**Tokens (must match exactly):**

```css
/* Surfaces (warm paper) */
--paper:        #F7F6F1;
--paper-2:      #EFEDE4;
--paper-3:      #E4E1D7;

/* Ink (text) */
--ink:    #0E1116;
--ink-2:  #2A2D34;
--ink-3:  #5B5F68;
--ink-4:  #8A8E97;

/* Lines */
--line:      #DDD8C9;
--line-soft: #E8E4D7;

/* Accent (civic teal) â€” sparingly */
--accent:      oklch(0.52 0.08 195);
--accent-soft: oklch(0.92 0.03 195);
--accent-ink:  oklch(0.32 0.07 195);

/* Ember (privacy boundary ONLY) */
--ember:      oklch(0.58 0.14 45);
--ember-soft: oklch(0.94 0.04 45);

/* Semantic */
--good: oklch(0.55 0.10 155);   /* success / passing / lift */
--warn: oklch(0.65 0.10 80);    /* warning / unchanged */

/* Typography */
--sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
--mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
```

**Banned colors (legacy palette retired in earlier sessions):**
- `#1e40af`, `#1e3a8a`, `#3b82f6`, `#2563eb`, `#0066ff` (legacy dark-blue)
  â€” only acceptable as semantic jurisdiction-flag colors in `_brand.py`.
- `#f59e0b`, `#ec4899` (legacy amber/pink) â€” replace with `--warn` /
  `--ember` / `--accent` as appropriate.
- Tailwind grays (`#f8fafc`, `#1f2937`, `#9ca3af`, `#6b7280`, `#e5e7eb`,
  `#d1d5db`) â€” replace with the paper/ink/line tokens.

---

## 6. The workbench shell (3 reusable primitives)

Every served UI page in the project uses these three primitives so they
look like part of the same product.

### 6.1 `_chrome.css` â€” the design tokens + base styles

```html
<link rel="stylesheet" href="/static/_chrome.css">
```

Provides: token system, status-strip styles, nav-row styles, button
classes (`.primary`, `.secondary`, `.danger`, `.utility`), card
styles, pill styles, focus rings, table styles. Importing this file
gives a page the entire visual system.

### 6.2 `_nav.html` + `_nav.js` â€” the shared top chrome

```html
<body data-nav="<key>">     <!-- key matches a nav-key in _nav.html -->
<script src="/static/_nav.js" defer></script>
```

`_nav.js` runs on DOMContentLoaded:
1. Fetches `/static/_nav.html` and inserts it as the first child of `<body>`.
2. Marks the active nav link by matching `<body data-nav>` against the
   nav partial's `data-nav-key` attribute.
3. Polls `/api/version` + `/api/model-info` every 10s to populate the
   status strip (model name, version, GPU memory).
4. Wires the Shutdown button.

Layout (top to bottom):

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ â— Model: gemma-4-e4b-it Â· v0.16.0 Â· 1.2GB GPU      [â» Shutdown]      â”‚  â† status strip
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ DueCare Workbench  Platform Â· NGO Â· Worker Â· Researcher Â· Developer  â”‚  â† single-row nav
â”‚                                                          [Tools â†’]   â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚  [page content]                                                      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

Valid `data-nav` keys:
- `chat` (home / playground)
- `platform`, `ngo`, `worker`, `researcher`, `developer` (5 audience tabs)
- `tools` (Tools utility link)
- `grade`, `models`, `logs`, `import`, `settings`, `layers`, `search`,
  `hotlines`, `anonymize` (sub-tools â€” won't match any nav link but the
  brand stays as the home indicator)

### 6.3 `dc_log` â€” JSON-Lines logging primitive

```python
from duecare.chat._dc_log import dc_log, set_kernel_id
set_kernel_id("a-XX-some-kernel")
dc_log("chat.send", "user sent prompt", chars=len(prompt))
dc_log("grep.test", "fired 3 rules", layer="grep", rule_ids=["a","b","c"])
dc_log("kernel.error", "model load failed", level="error", err=str(e))
```

Writes one JSON line per event to both stderr AND
`/kaggle/working/duecare-logs.jsonl`. Schema:
`{ts, level, kernel, kind, layer?, msg, ...payload}`.

The Logs page (`/static/logs.html`) reads back via `GET /api/dc-logs?
tail=200&level=warn&kind=grep&layer=rag`. Available endpoints:
- `GET /api/dc-logs` â€” events tail
- `GET /api/dc-logs/stats` â€” counts by level/kind
- `POST /api/dc-logs/clear` â€” drop the ring buffer

---

## 7. The cross-mount: `/wb-static/`

Both the server package (02-live-demo) and the three custom-FastAPI
appendix kernels (A-03, A-04, A-09) mount the chat package's static
directory at `/wb-static/` so they can pull `_chrome.css`, `_nav.js`,
and the audience showcase pages from the same source as kernel #01.

Pattern:

```python
import duecare.chat as _chat_pkg
from pathlib import Path
_wb_static = Path(_chat_pkg.__file__).parent / "static"
if _wb_static.exists():
    app.mount("/wb-static", StaticFiles(directory=str(_wb_static)), name="wb-static")
```

Then in the served HTML:

```html
<link rel="stylesheet" href="/wb-static/_chrome.css">
<script src="/wb-static/_nav.js" defer></script>
<body data-nav="tools">
```

---

## 8. The `build_minimal_shell()` helper (kernel-rendered dashboards)

For kernels that compute outputs without needing the full chat playground
(A-05, A-06, A-07, A-08, A-11), `build_minimal_shell()` gives them a
workbench-consistent web UI with one call.

Signature (chat 0.16.0):

```python
from duecare.chat.kernel_shell import build_minimal_shell

app, url = build_minimal_shell(
    summary={                        # required â€” fallback summary view
        "title": "...",
        "audience": "researcher",
        "lede": "...",
        "results": [{"label": "...", "value": "..."}],
        "artifacts": [{"name": "...", "path": "..."}],
        "links": [("Workbench (full)", "https://...")],
        "next_steps": ["..."],
    },
    kernel_id="a-XX-some-kernel",
    port=8080,
    homepage_html=my_dashboard_html, # OPTIONAL â€” overrides GET /
    extra_routes={                   # OPTIONAL â€” kernel-specific routes
        "/api/lift":        ("GET", _api_lift_handler),
        "/export/lift.csv": ("GET", _export_csv_handler),
    },
)
```

Always-available routes (the helper wires these for you):
- `GET /` â€” dashboard or summary
- `GET /summary` â€” default summary (always reachable)
- `GET /healthz`, `/api/version`, `/api/model-info`, `/api/brand`
- `GET /api/dc-logs`, `/api/dc-logs/stats`, `POST /api/dc-logs/clear`
- `GET /artifact/{name:path}` â€” downloads from `/kaggle/working/`
- `/static/*` â€” chat package static (so `_chrome.css` and `_nav.js` work)

---

## 9. The 4 bespoke dashboards (recently completed)

### 9.1 A-11 lift dashboard (`kaggle/A-11-grading-evaluation/kernel.py`)

Hero KPIs (mean lift pp, win/loss/tie tally, score beforeâ†’after,
grounding lift) + per-prompt scorecard with side-by-side score bars +
provenance footer. Exports: JSON, MD, CSV. Routes: `/api/lift`,
`/export/lift.csv`.

### 9.2 A-08 inline Plotly viewer (`kaggle/_archive/notebooks/A-08-research-graphs/kernel.py`)

All 6 charts (entity graph, corridor Sankey, benchmark bars,
fee-camouflage heatmap, ILO indicator hits, RAG sunburst) embedded as
iframes with per-chart Open â†— / Download. Routes: `/api/charts`.

### 9.3 A-07 training pipeline (`kaggle/A-07-bench-and-tune/kernel.py`)

Adapter-training visualization for one Gemma 4 backbone with routed
DueCare adapters. Default path is SafetyJudge: Load â†’ bench-stock â†’
SFT-dataset â†’ SFT â†’ DPO-dataset â†’ DPO â†’ bench-FT â†’ GGUF â†’ HF-push.
A-06 generated graded responses should be consumed first when attached;
harness-distilled prompts are the fallback. PrivacyRedactor rows from A-06
stay on a separate anonymization adapter/eval track and should not be
blended into the SafetyJudge adapter. The stock-vs-fine-tuned benchmark
artifact is A-07's `eval_results.json`, not A-11.
Routes: `/api/eval-results`, `/export/phases.csv`.

### 9.4 A-06 corpus browser (`kaggle/A-06-prompt-generation/kernel.py`)

Two-track synthetic data generator. SafetyJudge track: filterable table
(category / locale / search) over freshly generated prompts with full
graded response ladders. PrivacyRedactor track: composite anonymization
cases plus gold redaction-plan JSONLs for a separate privacy adapter/eval
path. Each Kaggle run loads one model; diversity comes from multiple A-06
runs with separate profiles (`stock_harness_teacher`,
`abliterated_adversary`, `human_curated_review`) and manifests attached to
A-07 through Kaggle Add Data. Per-row "Open in chat" deep-link. Routes:
`/api/prompts`, `/export/prompts.csv`.

**These four dashboards are the reference pattern for any future
kernel-rendered visualization.** Their HTML is inline in each kernel.py
and links `/static/_chrome.css` + `/static/_nav.js`.

---

## 10. The 5 audience showcase pages

Live at `packages/duecare-llm-chat/src/duecare/chat/static/showcase-*.html`.

Each page follows the same skeleton:
1. **Crumbs:** `Showcase Â· For <audience> teams`
2. **H1:** action-oriented sentence (~10 words)
3. **Lede:** 3-sentence problem-and-solution paragraph
4. **CTA row:** `Open the playground â†’` + secondary
5. **Curated prompts:** 3 audience-specific sample buttons that deep-link
   to `/?prompt=<URL-encoded>&audience=<lane>`
6. **Tools row:** 4 tool cards from `all-tools.html` curated to this lane

Click flow: showcase page â†’ click curated prompt â†’ chat homepage
pre-fills the input via `URLSearchParams` consumer in `index.html` line
1779. The chat homepage strips the params from the URL after consumption
so a refresh doesn't re-pre-fill.

Existing curated-prompt examples (each grounded in real corridors):
- Platform: Saudi domestic-worker recruitment ad with debt-bondage
  warning signs; UAE recruiter DM with passport-retention pattern; PH
  forum post about likely-unlicensed agency with refundable-deposit scam.
- NGO: PHâ†’HK passport-retention case; PHâ†’UAE pre-departure fee scam;
  NPâ†’KSA kafala wage-theft + complaint draft.
- Worker: PHâ†’HK placement-fee legality check; PHâ†’KSA passport-retention
  rights; recruiter-linked salary-advance loan debt-bondage signs.
- Researcher: multi-jurisdiction legal comparison; DAN-style jailbreak;
  5-indicator compound case (the headline-lift demo).
- Developer: full API tour with 8 endpoints + curl examples.

---

## 11. The 13 kernels (current architecture pattern + state)

| # | Folder | Pattern | Dashboard | Audience |
|---|---|---|---|---|
| 01 | `01-duecare-exploration-workbench` | chat-shell (`from duecare.chat import create_app`) | the full workbench | all |
| 02 | `02-live-demo` | server-shell (`from duecare.server import create_app`) | server hub homepage | all |
| A-01 | `A-01-chat-playground` | chat-shell | workbench homepage | researcher |
| A-02 | `A-02-chat-playground-with-grep-rag-tools` | chat-shell | workbench homepage | researcher |
| A-03 | `A-03-content-classification-playground` | custom-FastAPI (uses `/wb-static/`) | custom classifier page | platform |
| A-04 | `A-04-content-knowledge-builder-playground` | custom-FastAPI (uses `/wb-static/`) | custom KB-builder page | developer |
| A-05 | `A-05-gemma-content-classification-evaluation` | classifier (`from duecare.chat import create_classifier_app`) | NGO & regulator dashboard | ngo |
| A-06 | `A-06-prompt-generation` | kernel-rendered (`build_minimal_shell` + `homepage_html`) | corpus browser | researcher |
| A-07 | `A-07-bench-and-tune` | kernel-rendered | training pipeline | researcher |
| A-08 | `A-08-research-graphs` | kernel-rendered | inline Plotly viewer | researcher |
| A-09 | `A-09-chat-playground-with-agentic-research` | custom-FastAPI (uses `/wb-static/`) | custom agentic-chat page | researcher |
| A-10 | `A-10-runtime-vs-weights-safety-study` | chat-shell | workbench homepage | researcher |
| A-11 | `A-11-grading-evaluation` | kernel-rendered | lift dashboard | researcher |

**Each `kernel-metadata.json` IDs match the folder name** (e.g.
`taylorsamarel/duecare-exploration-workbench`).

---

## 12. UI/UX rubric (the 13 principles â€” apply consistently)

Source-of-truth: `docs/workbench_audit.md`.

1. **One page, one job.** Primary action describable in one sentence.
2. **Progressive disclosure.** â‰¤ 3 prominent CTAs above the fold;
   advanced knobs hidden behind expanders.
3. **Transparency is a clickable ribbon, not a wall.** Every assistant
   response shows a one-line trace strip
   (`PERSONA Â· GREP(7) Â· RAG(top-5) Â· TOOLS(2) Â· 1.4s`) that expands.
4. **Citations are clickable evidence.** Every "ILO C181" / "POEA
   Circular 015" must link to the actual source text in the RAG corpus.
5. **Audience-first nav.** 5-lane top nav reflects the canonical
   audiences; capability tabs live as `Tools â†’` index.
6. **Logs are first-class.** Audit/governance/pipeline traces reachable
   in 1 click from the top nav, not buried.
7. **Showcase every functionality on its own stage.** Every API
   capability gets a UI page even if small. Audience pages compose those
   primitives.
8. **Modals fit the viewport.** `min(92vh, 100dvh - 48px)`. Body scrolls,
   chrome stays pinned. Absolutely no overflow-hidden traps.
9. **Mobile is not an afterthought.** â‰¥ 44px touch targets;
   single-column at < 600px; no horizontal scroll.
10. **Match duecare-ai.com visual language.** Same tokens, same fonts,
    same single-row nav restraint.
11. **Every claim is verifiable from the workbench.** README counts
    cross-link to the live API and the live page.
12. **Don't break what works.** Extractions preserve identical behavior;
    only the page composition changes.
13. **Single-row top nav, 4â€“7 items max.** Brand left, utility right.
    No two-row nav, no permanent sub-tabs, no top-level dropdowns with
    multi-level nesting.

---

## 13. Hard rules (non-negotiable)

These are derived from `.claude/rules/*.md` plus durable user feedback.

### Privacy / PII
- **No raw PII anywhere a judge can see.** No real names, real phone
  numbers, real passport IDs, real emails, real bank accounts. Composite
  characters (Maria, Ramesh, Sita) must be explicitly labeled composite.
  Real NGO names (Polaris, IJM, POEA, BP2MI) are public organizations
  and load-bearing for the impact story â€” they stay.

### Truncation / placeholder content
- **Never truncate displayed text** â€” no `text[:N]...`, no `..."`
  ellipsis on responses, no `response_preview` fields. Show the full
  content. Pandas: call `pd.set_option('display.max_colwidth', None)`
  before `display()`.
- **No "Coming soon" pages, no Lorem Ipsum, no TODO/FIXME/TBD in
  user-facing surfaces.** Every page must do something real.

### Voice / copy
- **Never use "ship" or "shipping" for software releases.** Use literal
  verbs: publish, release, deploy, push, merge, finish.
- **Don't headline "Privacy is non-negotiable."** Privacy is one
  supporting boundary, not a slogan. The story is helping migrant
  workers across the 5 lanes.
- **Concrete sentences, not slogans.** Replace abstract claims with the
  actual mechanism. Example: "Sensitive PII is anonymized via Gemma 4
  before submission, then re-stripped on the server" not "your data is
  safe with us."
- **BEST tier is mixed-case bold, not ALL-CAPS.** `**Legal Violations:**`
  not `LEGAL VIOLATIONS:`.

### Kaggle viewer compatibility (archived notebook outputs only)
- **No `display: flex` / `flex-wrap`** â€” gets stripped. Use
  `pandas.Styler` tables instead.
- **No `max-height: ...; overflow: auto`** â€” overflow gets stripped,
  produces unscrollable giant blocks. Render full-height.
- **No `<script>` tags in archived notebook outputs** â€” stripped. Use Plotly's
  safe JS injection path for interactivity.
- **No `position: fixed|absolute|sticky`** â€” stripped.
- **No external stylesheets in archived notebook outputs** â€” use inline `style=`
  only.

### Web UI (served pages, not notebooks)
- The above Kaggle viewer constraints **do not apply** to served pages
  reached via cloudflared. Use `<script>`, `position: sticky`, modern
  CSS freely there.

### Code style (Python)
- **Python 3.11+**, type hints on function signatures, Pydantic v2 for
  data models, `pathlib.Path` for paths, structured logging via
  `structlog` / `dc_log` (never `print()` in library code, except
  console-orchestration scripts like `kernel.py`).
- **`from __future__ import annotations`** at the top of every
  package-level module.

### Build / wheel hygiene
- Every chat-package change bumps `pyproject.toml` version
  (`0.16.0` â†’ `0.16.1` etc.).
- After `pip wheel`, propagate the new `.whl` to all 13
  `kaggle/*/wheels/` folders. Remove the older version.

---

## 14. Validation gates (run before claiming "done")

```bash
# Public-surface audit (must show 4/4 OK, 0 findings)
.venv/Scripts/python.exe scripts/validate_public_surface.py

# Root metadata validator (active submission folders must be script kernels)
.venv/Scripts/python.exe -c "import json, pathlib; bad=[]; [bad.append(str(p)) for p in pathlib.Path('kaggle').glob('*/kernel-metadata.json') if json.loads(p.read_text()).get('code_file') != 'kernel.py' or json.loads(p.read_text()).get('kernel_type') != 'script']; assert not bad, bad"

# Package test suite (must exit 0 â€” meta-pkg CLI test fails without
# editable installs, that's expected)
.venv/Scripts/python.exe -m pytest packages/ \
    --ignore=packages/duecare-llm/tests \
    --ignore=packages/duecare-llm-agents/src/duecare/agents/anonymizer/tests \
    -q

# AST-parse every kernel.py you touched
python -c "import ast; [ast.parse(open(p).read()) for p in [...]]"
```

The audit script checks four invariants:
1. `drift_terms` â€” no banned terms / stale slugs / legacy palette
2. `hub_routes_200` â€” 41 declared routes resolve (9 nav + 19 footer)
3. `five_lane_order` â€” the 5 canonical audiences appear in correct order
4. `kaggle_lane_labels` â€” all 13 numbered Kaggle folders use canonical
   audience labels

---

## 15. Kaggle publish + kernel source-of-truth conventions

- **Source of truth is `kernel.py`**, not the `.ipynb` mirror.
- **`.ipynb` files are archived preview artifacts.** Do not regenerate or
  edit them in active Kaggle folders. Historical wrappers live under
  `_archive/kaggle-notebook-previews-2026-05-11/`.
- **Bootstrap installs must be reproducible.** Prefer attached Kaggle
  wheel datasets first, pinned PyPI packages second, and immutable
  GitHub release/tag/commit URLs only as a fallback. Never install from
  a moving branch such as `main` in a judge-facing kernel.
- **Kaggle publishing is manual.** Default agent behavior: edit source +
  validate locally + prepare paste-ready text + leave the final Kaggle
  UI step (copy/paste, Save & Run, publish) to the user.
- **Don't claim a slug is "live"** without verification. The local
  `kernel-metadata.json` declares the slug we *want*; the actual live
  URL may use an older slug.

---

## 16. What you're being asked to do

Read all 13 kernels (`kaggle/*/kernel.py`), all 13 READMEs
(`kaggle/*/README.md`), the workbench static (`packages/duecare-llm-chat/
src/duecare/chat/static/*.html`), the server static
(`packages/duecare-llm-server/src/duecare/server/static/*.html`), and
the public website templates (`apps/duecare-ai.com/app/templates/*.html`),
then propose concrete iterative improvements.

Start from the current checkpoint rather than the original draft baseline:
the remaining highest-value conservative work is README skeleton and
cross-link consistency across the 13 judge-facing folders, above-the-fold
audience clarity, and demo-recording friction. Do not spend time on the
already-fixed moving-Git-ref, preview-cell-metadata, A-08 sample-color, or
A-09 displayed-truncation issues unless a current validation command proves
they regressed.

### Output structure

Return four layers of output.

#### Layer A â€” Per-kernel polish edits (13 sections)

For each of the 13 kernels, output:

1. **Audience match.** Which lane primarily? Is that clear in the README's
   first 200 words and the kernel's homepage above-the-fold?
2. **Primary action.** Single imperative sentence ("Score a recruitment
   post and see why each rule fired" / "Compare stock Gemma against the
   harness on 5-indicator compound prompts"). Propose if missing.
3. **Top 5 concrete edits.** For each edit, output the file path, line
   range, and either the exact replacement code/HTML or a precise
   description. Examples of acceptable edits:
   - Replace a hardcoded color `#f59e0b` at `kernel.py:813` with
     `var(--warn)`.
   - Add a `data-nav="tools"` attribute to the `<body>` tag of
     `kaggle/A-XX-foo/kernel.py:625`.
   - Tighten a 4-line README headline to a single sentence.
4. **Demo-recording readiness.** Score 1-5 (where 5 = no friction during
   the 3-min recording). If <5, list the specific friction.

#### Layer B â€” Cross-kernel consistency edits

Output specific changes that align the 13 kernels as a series:

1. **README skeleton.** Propose a uniform 6-section skeleton (Lede,
   What it does, Demo path, Audience, Outputs, Cross-links) that every
   README follows. If any of the 13 don't conform, list the gap.
2. **Cross-link block.** Every README should end with a 4-link cross-link
   block: (a) workbench, (b) live-demo, (c) sibling appendix that's the
   natural next step, (d) public website. Propose the exact wording.
3. **Visual identity per appendix.** Should each appendix have a small
   distinguishing visual element (a colored top-strip, a numbered tag),
   or should they all look identical? Justify and prescribe.
4. **Status strip consistency.** Every served-UI kernel should report
   the same shape from `/api/version` + `/api/model-info`. Audit the
   13 kernels and list any inconsistencies.
5. **Naming consistency.** The 24 appendix slugs (A-01 ... A-11) â€” are
   they well-ordered for the 5-minute judge journey? If a different
   ordering would tell a better story, propose it.

#### Layer C â€” Demo-recording strategy

Output a click-by-click script for the 3-minute screen recording:

1. **The 3-minute click path.** Open at <URL>; pause on <visible
   element>; click <CTA>; show <feature>; cut to <next>. ~12-18 actions
   total, with time budget per action.
2. **Hero moments.** Which 3-4 specific UI states / dashboards make
   the strongest visual claims? Mark them.
3. **B-roll candidates.** What 5-6 supporting shots could the recorder
   capture between hero moments (e.g., the 161-rule GREP browser
   scrolling, the citation graph rotating, a Plotly chart drilling in)?
4. **Pre-record checklist.** What 8-12 verifications must Taylor run
   before hitting Record? (e.g., "Kaggle session is warm", "model is
   loaded â€” check the green dot in the status strip", "Audience pages
   all load < 1s").

#### Layer D â€” Risk register (what could embarrass us)

List the top 8 design / engineering risks that could hurt the judging
score on Impact / Video / Tech-Depth axes. For each:

- The risk (one sentence)
- How it appears in the video (concrete)
- The probability it gets caught by a judge
- The cost to fix (estimate in hours)
- Recommended mitigation

---

## 17. Format we want back

For Layer A, use this exact shape:

```markdown
## 01 exploration-workbench
- Audience match: <which lane(s)> â€” <evidence in code>
- Primary action: "<single sentence>"
- Demo-readiness: 4/5 (friction: <list>)
- Top 5 edits:
  1. `<file>:<line-range>` â€” <description or replacement>
  2. ...
  3. ...
  4. ...
  5. ...

## 02 live-demo
[same shape]

## A-01 chat-playground
[same shape]

[... through A-11 ...]
```

For Layer B/C/D, use prose + bullets + code blocks freely.

**Don't restate this brief back at us.** Jump directly to the review.
Be specific and bullet-dense. Every claim that requires verification
should cite the file path and approximate line number.

---

## 18. Out of scope (do not propose)

- Changing the 5 canonical audiences. They are partner-vetted.
- Replacing Gemma 4 with another model (hackathon rule).
- Redesigning the public website. It's the source of truth.
- Replacing the wheel-based distribution mechanism.
- Multi-row nav, sticky sub-tabs, multi-level dropdown menus.
- Adding new top-level audiences ("activist", "media", etc.).
- Renaming the `duecare-` slug prefix.
- Adding cloud-hosted dependencies (no LLM API as a hard requirement â€”
  must work fully offline on the Kaggle GPU).
- Building the actual video. Taylor will record after polish completes.
- Touching `_archive/` â€” frozen historical material.

---

## 19. Reference URLs / file paths to inspect

| What | Where |
|---|---|
| Public website | https://duecare-ai.com (deployed) / `apps/duecare-ai.com/` (source) |
| Public-site CSS (token source) | `apps/duecare-ai.com/app/static/styles.css` |
| Public-site nav | `apps/duecare-ai.com/app/templates/_nav.html` |
| Workbench audit + 13 principles | `docs/workbench_audit.md` |
| Canonical audiences + components | `docs/canonical_use_cases_and_components.md` |
| Canonical messaging | `configs/duecare/canonical_messaging.yaml` |
| Chat-package design tokens | `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css` |
| Chat-package nav partial | `packages/duecare-llm-chat/src/duecare/chat/static/_nav.html` |
| Chat-package nav loader | `packages/duecare-llm-chat/src/duecare/chat/static/_nav.js` |
| Chat-package showcase CSS | `packages/duecare-llm-chat/src/duecare/chat/static/showcase.css` |
| Server-package design tokens | `packages/duecare-llm-server/src/duecare/server/static/style.css` |
| Server-package `/wb-static/` mount | `packages/duecare-llm-server/src/duecare/server/app.py` |
| 5 audience showcase pages | `packages/duecare-llm-chat/src/duecare/chat/static/showcase-*.html` |
| Tools index | `packages/duecare-llm-chat/src/duecare/chat/static/all-tools.html` |
| Minimal-shell helper | `packages/duecare-llm-chat/src/duecare/chat/kernel_shell.py` |
| dc_log primitive | `packages/duecare-llm-chat/src/duecare/chat/_dc_log.py` |
| 13 kernel folders | `kaggle/01-...`, `kaggle/02-...`, `kaggle/A-01-...` through `kaggle/A-11-...` |
| 4 bespoke dashboards | `kaggle/A-06/07/08/11/kernel.py` (search `_build_*_dashboard_html`) |
| Audit script | `scripts/validate_public_surface.py` |
| Judge-facing entry | `docs/FOR_KAGGLE_JUDGES.md` |
| Writeup draft (1500-word cap) | `docs/writeup_draft.md` (currently ~1218 words) |
| Video script | `docs/video_script.md` |
| GitHub | https://github.com/TaylorAmarelTech/gemma4_comp |
| Latest commit | `3e3ff9e` (4 dashboards + chat 0.16.0) |

---

## 20. Why this matters for the score

The hackathon rubric weights **Impact & Vision (40)** + **Video Pitch
& Storytelling (30)** + **Technical Depth & Execution (30)**. Kernel
UX maps to all three:

- A judge who lands on the workbench and immediately understands "I'm
  an NGO, here's the demo for me" scores higher Impact (the vision
  feels concretely useful, not abstract).
- A judge who can flip between Platform / NGO / Worker / Researcher /
  Developer and see five distinct, polished demos in 3 minutes scores
  higher Video Pitch (the story is multi-stakeholder).
- A judge who can click "Pipeline trace" and see real per-layer
  latency + fired GREP rules + retrieved docs scores higher Tech Depth
  (the harness is *visible*, not asserted).

Your iteration job: surface every remaining friction point that
prevents any of those three judge-experiences from feeling polished,
and output the actual edits to fix them, ranked by expected score
impact.
