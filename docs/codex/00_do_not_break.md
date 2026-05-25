# 00 — Do not break

> The protective contract every Codex improvement must honor. Created 2026-05-24. Every per-goal handoff in this directory links here.

## Why this exists

Kaggle has a **published notebook** at `kaggle/01-duecare-exploration-workbench/kernel.py` with documented run instructions. Reviewers may have:

- Bookmarked deep links to `/static/<page>.html` pages.
- Copied `kernel.py` into their own Kaggle account.
- Invoked specific `/api/...` routes from external tools.
- Run the documented "how to use" steps from the kernel README.

An improvement that renames a route, drops a DOM ID, changes a sample-artifact path, or rewrites the run instructions silently breaks the published submission. Reviewers find a broken kernel without warning.

This document enumerates exactly what's load-bearing. **If a proposed change would violate any item below, re-scope the change.** When in doubt, add a new route / new ID / new artifact next to the old one and deprecate the old one in a later goal.

---

## 1. Published kernels (DO NOT RENAME OR DELETE)

These three kernel directories are the recording-critical path per `.claude/rules/80_active_surface.md`:

| Path | Role |
|---|---|
| `kaggle/01-duecare-exploration-workbench/kernel.py` | Reviewer workbench — broadest surface |
| `kaggle/02-live-demo/kernel.py` | Focused live-demo path |
| `kaggle/A-00-omni-experiment-workbench/kernel.py` | Quantitative control plane |

Plus optional benchmarks (not part of the recording-critical path but still published):

| Path | Role |
|---|---|
| `kaggle/03-universal-llm-benchmark/kernel.py` | Arbitrary endpoint comparison |
| `kaggle/04-kaggle-community-benchmark/kernel.py` | Kaggle Community Benchmark integration |

**Allowed:** internal additions inside `kernel.py` that don't change the documented boot flow.
**Forbidden:** renaming the directory, removing `kernel.py`, changing the boot command, removing a documented entrypoint, removing dependencies from the inline `!pip install` block.

**Kernel compatibility gate:** Before committing any goal, run:

```bash
python scripts/validate_main_kaggle_kernels.py
```

This gate protects only the three active kernels above plus the two optional benchmark kernels above. Appendix notebooks, archived notebooks, and legacy notebook-era folders are not part of this check unless Taylor explicitly asks to restore them.

---

## 2. Existing API routes (DO NOT RENAME OR REMOVE)

Every route below is exposed by the live workbench app (`packages/duecare-llm-chat/src/duecare/chat/app.py` plus the harness `__init__.py` files) and is consumed by either a static page or an external integration tool.

### Knowledge (extraction harness)
- `POST /api/knowledge/source-file`
- `POST /api/knowledge/draft-envelope`
- `POST /api/knowledge/draft-envelope/start` + `/status/{job_id}` + `/cancel/{job_id}`
- `POST /api/knowledge/polish-envelope` (added 2026-05-24 in 84695fc)
- `POST /api/knowledge/promote`
- `POST /api/knowledge/import`
- `GET /api/knowledge/list`
- `GET /api/knowledge/taxonomy`

### Process (process harness)
- `POST /api/process/batch`
- `POST /api/process/batch/start` + `/status/{job_id}`
- `POST /api/process/graph-extract` + `/start` + `/status/{job_id}` + `/cancel/{job_id}`
- `POST /api/process/graph-chat`

### Templates (chat/templates.py registration)
- `GET /api/templates/list`
- `POST /api/templates/fill`
- `POST /api/templates/drafts`

### Anonymization / Share
- `POST /api/anonymize` + `/start` + `/status/{job_id}` + `/cancel/{job_id}`
- `POST /api/submit/knowledge`
- `POST /api/submit/local` (deprecated alias — keep for now)

### Search + Safety
- `POST /api/search/client`
- `POST /api/search/server`
- `POST /api/search/sanitize`
- `POST /api/search/verify-results`
- `GET /api/search/backends`
- `GET /api/search/safety-info`
- `GET /api/search/verification-info`

### Chat
- `POST /api/chat/send` (SSE stream)

### Model + status
- `POST /api/load-model`, `POST /api/unload-model`, `GET /api/model-info`
- `GET /api/version`

**Allowed:** adding NEW routes next to old ones (e.g. `POST /api/templates/fill-batch` next to `POST /api/templates/fill`).
**Forbidden:** renaming, removing, or breaking the request/response shape of any route above. If you must change a response shape, add a new optional key — never remove or rename an existing one.

---

## 3. Static pages (DO NOT REMOVE)

Every page below is reachable by URL and may be deep-linked. The list comes from the FastAPI static mount under `packages/duecare-llm-chat/src/duecare/chat/static/`:

```
chat.html | classifier.html | compare.html | grade.html | knowledge.html
process.html | templates.html | share.html | search.html | search-safety.html
sync.html | submit.html | status.html | settings.html | models.html
persona.html | tools.html | online.html | logs.html
index.html | rag-graph.html | rag-corpus.html | upload.html | insights.html
hotlines.html | import.html | anonymization-preview.html
all-tools.html | ecosystem.html | harness.html | grep-rules.html | grep-tester.html
ui-audit.html | showcase-{platform,worker,ngo,researcher,developer}.html
use-cases.html | getting-started.html | demo-recording.html
```

**Allowed:** adding new pages.
**Forbidden:** removing any of these or moving them out of `/static/`.

---

## 4. Load-bearing DOM IDs

The JS on each page references specific element IDs. Tests pin them (`packages/duecare-llm-chat/tests/test_compare.py` is the canonical example). Renaming any ID below silently breaks the page.

**Reference test for full ID lists per page:**
- `tests/test_compare.py` — compare.html IDs
- `tests/test_harness_workbench.py` — knowledge.html / process.html IDs
- `tests/test_design_tooltip_migration.py` — tooltip data-tip attributes

**Categorical rule:** any ID that starts with `wb-`, `kx-`, `tpl-`, `cmp-`, `search-`, `graph-`, `pg-`, `pgs-`, `dc-`, `sn-` is load-bearing JS plumbing. There are ~219 such IDs across 8 active pages. If you must rename one, find every JS file that calls `document.getElementById('<id>')` first and update them in the same commit.

**Allowed:** adding new IDs.
**Forbidden:** renaming or removing existing IDs without updating every JS call site in the same commit.

---

## 5. Activity-log handles

Each page declares its own log handle. **Do not rename**:

| File | Handle name |
|---|---|
| `compare.html` | `_dcLog` (via `dcActivityLog.attach('#cmp-log')`) |
| `knowledge.html` | `_dcLog` (via `dcActivityLog.attach('#wb-log')`) |
| `process.html` | `_dcLog` (via `dcActivityLog.attach('#wb-log')`) |
| `search.html` | `_searchLog` (via `dcActivityLog.attach('#search-log')`) |
| `share.html` | `_dcLog` (via `dcActivityLog.attach('#wb-log')`) |
| `sync.html` | `_dcLog` (via `dcActivityLog.attach('#wb-log')`) |
| `templates.html` | `_tplLog` (via `dcActivityLog.attach('#tpl-log')`) |
| `status.html` | `dcActivityLog.attach('#status-log')` |
| `getting-started.html` | `dcActivityLog.attach('#gs-log')` |

`window.dcActivityLog.attach(selector, {idlePlaceholder: '...'})` returns the handle. Every page uses `.info / .ok / .warn / .err / .step / .net / .anon / .channel` methods on it. **Do not change the API surface of `dcActivityLog`.**

---

## 6. Top-bar Gemma 4 tally

`window.dcGemmaStats` (defined in `static/_nav.js`) is read by every page that calls Gemma. Its API:

- `.bump(bucket)` where bucket is one of: `brief`, `edge_pass`, `media`, `synthesis`, `rephrase`, `draft`, `template_fill`, `anonymize_review`, `chat`, `polish`, `compare`, `grade`
- `.addProposedEdges(n)`
- `.snapshot()` returns `{calls, brief, edge_pass, ..., started_at, updated_at}`
- `.reset()`

**Allowed:** adding new buckets (e.g. `polish`).
**Forbidden:** renaming existing buckets or changing the snapshot shape.

---

## 7. Sample artifacts (DO NOT MOVE OR REMOVE)

Every page that produces or accepts an artifact ships a judge-safe sample at `/static/samples/`. The list comes from `packages/duecare-llm-chat/src/duecare/chat/static/samples/sample_manifest.json`:

- `samples/case_files_sample.zip` (used by process.html)
- `samples/knowledge_object_sample.json` (used by knowledge.html)
- `samples/knowledge_bundle_sample.zip` (used by knowledge.html, sync.html)
- Plus the recording_* samples used by demo-recording.html

Reviewers click "Use sample" / "Download sample" buttons that hit these paths. **Do not move or rename existing sample files.**

**Allowed:** adding new sample files via `scripts/build_static_samples.py` and updating `sample_manifest.json`.

---

## 8. Canonical vocabularies (DO NOT RENAME ENTRIES)

These vocabulary tuples are committed to git and saved knowledge envelopes reference them by string match:

- `STANDARD_FACT_KEY_ORDER` (47 fields) — in `harnesses/_safe_text.py`
- `STANDARD_FACT_INDICATORS` (16 ILO indicators) — same file
- `STANDARD_FACT_STAGES` (9 journey stages) — same file

Renaming `fee_bondage` to `feeBondage` would break every saved envelope that referenced the old name. Same for stages and key order.

**Allowed:** appending new entries to the tuples (Codex goal #7's audit script will surface candidates).
**Forbidden:** renaming or removing existing entries.

---

## 9. Run-time invariants

These are silent contracts the codebase relies on:

- `Gemma4Runtime.load()` is the canonical model loader (`gemma4_runtime.py`). Don't replace it with a different loader. See `.claude/rules/81_canonical_runtime.md`.
- Activity-log JS uses `document.createElement` + `textContent` only — **no `innerHTML` for user-derived strings**. New code must follow the same rule.
- The shared scrub helper `clean_for_knowledge_fact` is idempotent. Any new pattern added to `_KNOWLEDGE_NOISE_PATTERNS` must preserve idempotence.
- The polish endpoint contract is pinned by `tests/test_polish_envelope.py`. Don't change the response shape `{envelope, critique, passes, diff}` without updating that test.

---

## 10. Documentation invariants

- `CLAUDE.md` is protected setup metadata, but Taylor has explicitly allowed reconciliation edits. Update it only when a completed goal, active kernel constraint, or operating brief needs to stay consistent; keep unrelated CLAUDE.md refactors out of goal commits.
- `docs/DOCUMENTATION_GUIDE.md` is the canonical public-facts policy. New docs must follow it.
- Per-rule files under `.claude/rules/` are auto-loaded. Don't add or remove files there without confirming the rule precedence chain.

---

## How to apply this contract in a goal

Every per-goal `handoff.md` has a "Do-not-break checklist" section. It should be specific to that goal — pick the items from this contract that the goal could plausibly violate, and list them.

Example (Goal 1):
> **Do-not-break checklist:**
> - Don't rename `_searchLog` (section 5).
> - Don't change the `searchRenderDraftCard()` function signature or break the existing per-card layout (section 4).
> - The new "Polish further (Gemma 4)" button must be added next to "Save this draft", not replacing it (section 3).
> - Reuse the existing `POST /api/knowledge/polish-envelope` endpoint — no schema changes (section 2).
> - Bump `window.dcGemmaStats` with an existing bucket, not a new one (section 6).
