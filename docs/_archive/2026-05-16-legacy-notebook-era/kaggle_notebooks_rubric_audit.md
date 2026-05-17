# Kaggle notebooks — rubric audit (13 notebooks × 13 principles)

> Per-notebook score against the 13 design principles defined in
> `docs/workbench_audit.md`. Source for the next round of consistency
> commits. Generated 2026-05-10 against commit `2d4488c`.

## Pattern key

Three architectural patterns determine how much workbench-shell
inheritance each notebook gets for free:

- **A · chat-shell** — calls `from duecare.chat import create_app`. Auto-inherits the workbench shell when the chat-package wheel updates. Notebooks: **01, A-01, A-02, A-10**.
- **B · server-shell** — calls `from duecare.server import create_app`. Uses the duecare-llm-server's static set (already light-themed). Does **not** auto-get the chat-package's workbench `_nav.html`. Notebook: **02**.
- **C · custom-FastAPI** — defines its own `app = FastAPI(...)` with inline `_PAGE_HTML` strings. Needs explicit migration. Notebooks: **A-03, A-04, A-09**.
- **D · notebook-only** — no served web UI. Notebooks: **A-05, A-06, A-07, A-08, A-11**. Per the user's directive, these will get a minimal FastAPI shell that serves a Logs page + their notebook outputs through the workbench shell.

## Scoring legend
- ✓ pass · ⚠ partial · ✗ fail · N/A not applicable

---

## Per-notebook scoring summary

| # | Notebook | Pattern | P5 audience-nav | P10 tokens | P13 single-row | Notes |
|---|---|---|---|---|---|---|
| 01 | exploration-workbench | A | ✓ | ✓ | ✓ | Reference impl; P3+P4+P6 still pending |
| 02 | live-demo | B | ✗ | ✓ | ✓ | **Top fix:** server nav doesn't show 5-audience tabs — biggest visible inconsistency |
| A-01 | chat-playground | A | ✓ | ✓ | ✓ | Inherits everything; needs `data-nav="chat"` |
| A-02 | chat-with-grep-rag-tools | A | ✓ | ✓ | ✓ | **Deprecation candidate** — superseded by 01 |
| A-03 | classification-playground | C | ✗ | ⚠ | ⚠ | Needs migration to workbench shell |
| A-04 | knowledge-builder-playground | C | ✗ | ⚠ | ⚠ | Same as A-03 |
| A-05 | classification-evaluation | D | N/A | ⚠ | N/A | Needs minimal logs-shell |
| A-06 | prompt-generation | D | N/A | ⚠ | N/A | Needs minimal logs-shell |
| A-07 | bench-and-tune | D | N/A | ⚠ | N/A | Needs minimal logs-shell |
| A-08 | research-graphs | D | N/A | ⚠ | N/A | Needs minimal logs-shell |
| A-09 | chat-agentic-research | C | ✗ | ⚠ | ⚠ | Needs migration to workbench shell |
| A-10 | chat-jailbroken-models | A | ✓ | ✓ | ✓ | Inherits everything; needs `data-nav="chat"` |
| A-11 | grading-evaluation | D | N/A | ⚠ | N/A | Needs minimal logs-shell |

---

## Cross-cutting findings

### Inconsistency that hurts the most
**02-live-demo and 01-workbench have different top navs.** A judge clicking between them sees two different products. This is the single biggest "real, not faked for demo" credibility hit. **P-0 fix.**

### Notebook-only outputs need a minimal interface (per user directive)
The 5 notebook-only kernels (A-05, A-06, A-07, A-08, A-11) currently produce only the rendered `.ipynb` as their judge-visible artifact. The user has directed that **every notebook should have an interface, even if it just reports logs**. Plan: add a tiny FastAPI shell to each that:

1. Mounts the chat-package static directory at `/static/`
2. Serves the workbench shell at `/`
3. Serves a `Logs` page that reads from a standardized JSON-Lines log file written by the kernel's pipeline
4. Optionally surfaces the kernel's output artifacts (CSVs, plots, JSON exports) via the same shell

### Standardized JSON logging
The user has directed standardized JSON logging across all notebooks. Plan:

1. Add a `dc_log()` helper in the chat package (`duecare.chat.observability` or similar) that emits JSON Lines to:
   - stderr (for Kaggle stdout capture)
   - a rotating file at `/kaggle/working/duecare-logs.jsonl` (for the Logs page to read)
2. Standardized fields: `{ts, level, kernel, kind, layer, msg, ...payload}`
3. Build a `/api/logs` endpoint (list, filter by level/kind/layer, tail-n)
4. Build a `static/logs.html` page in the workbench shell that polls `/api/logs` and renders a filterable table

### Naming
- A-01 ... A-11 numbered slugs are stable. Keep.
- A-02 (`chat-playground-with-grep-rag-tools`) overlaps with 01. Open question: deprecate, hide, or repurpose?

### README skeleton
Currently each README is bespoke (93–224 lines). Proposed minimal skeleton:

```
# <title>
## Audience
## Primary action
## Run on Kaggle (3 steps)
## 5-minute walkthrough
## What lives where
## Cross-notebook context (this is appendix #X of 11)
## Footer (auto nav)
```

---

## Prioritized fix plan (north-star: hackathon score impact)

Each item maps to one or more hackathon rubric categories.

### P-0 — Align 02-live-demo's nav with the 5-audience workbench nav
Single biggest cross-notebook inconsistency. Fix: have the server package mount the chat-package static path so 02 gets the same `_nav.html` + `_nav.js` partials. Bumps Impact + Video Pitch.

### P-1 — Migrate the 3 custom-FastAPI apps (A-03, A-04, A-09)
Each gets:
- `app.mount("/static", StaticFiles(directory=duecare.chat.STATIC_DIR))`
- Inline `<style>` swapped for `<link rel="stylesheet" href="/static/_chrome.css">`
- `<script src="/static/_nav.js" defer>` injected
- `<body data-nav="<key>">` set per page

### P-2 — Add minimal logs-shell to the 5 notebook-only kernels (A-05, A-06, A-07, A-08, A-11)
Each gets a small FastAPI launched alongside the kernel's compute work:
- Serves the workbench shell at `/`
- Serves the kernel's primary output (the rendered notebook artifact) at `/output`
- Serves `Logs` page reading from `/kaggle/working/duecare-logs.jsonl`
- Cloudflared tunnel printed alongside the existing notebook output

This satisfies the user directive "each notebook should have an interface, even if it just reports logs."

### P-3 — Add standardized JSON-Lines logging primitive
New module: `duecare.chat.observability.dc_log` (or similar). Every kernel uses it. Schema:

```json
{"ts": "2026-05-10T12:34:56.789Z", "level": "info", "kernel": "01-workbench", "kind": "chat.send", "layer": "grep", "msg": "fired 7 rules", "rules": ["..."], "elapsed_ms": 12}
```

Add `/api/logs` endpoint to chat-package + a workbench `Logs` page that drains it.

### P-4 — Set `data-nav` defaults on chat-shell notebooks (A-01, A-02, A-10)
Trivial; just sets the active link. After A-02 deprecation question is resolved.

### P-5 — Pipeline-trace ribbon + clickable citations (P3 + P4 from audit)
The visible-transparency moves that drive Tech Depth score.

### P-6 — Build the 4 "Coming soon" capability pages
`Grade`, `Logs`, `Models`, `Import`, `Settings` — currently placeholders in `all-tools.html`.

### P-7 — Notebook-output palette re-render
A-05 / A-06 / A-07 / A-08 / A-11 outputs may still use the legacy blue palette. Re-run with the updated `_notebook_display.py` tokens.

---

## Competition framing

| Rubric category | Weight | Where these fixes land |
|---|---|---|
| Impact & Vision | 40 | P-0 (consistent demo across audiences); P-2 (every notebook has a logs view = serious tooling story); P-5 (clickable citations = rights info actionable) |
| Video Pitch & Storytelling | 30 | P-0 + P-1 (judges flip between notebooks without confusion = polished product); P-3 (live JSON logs visible = real, not faked) |
| Technical Depth & Execution | 30 | P-3 (structured logs prove the pipeline ran); P-5 (inline trace ribbon = visible harness); P-6 (every claimed API has a UI) |
