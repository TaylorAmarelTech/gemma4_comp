# Goal 12 - Kernel 01 workbench page polish and source gate

> Status: **PENDING**. Created 2026-05-25 after the root Kaggle cleanup and
> source review.

## 1. Goal

Clean up the main Kernel 01 workbench pages so the first-run reviewer path is
clear, source links resolve, activity logs are visible, and every primary page
has an explicit trust boundary and export/replay story.

## 2. Why it matters

Kernel 01 is the broadest proof surface. It should feel like a real local case
and safety workbench, not a collection of disconnected pages. Reviewers should
be able to start at the workbench, load a sample, see what Gemma did or did not
do, inspect evidence, export artifacts, and understand what stays local.

## 3. Current state

- Primary pages share `_chrome.css`, `_nav.js`, and `_activity_log.js`.
- Bulk File Review, Knowledge Extraction, Search, Templates, and Anonymization
  and Sharing have real source-backed flows and tests.
- `scripts/validate_kaggle_page_sources.py` now checks static references,
  primary-page markers, the `/static/chat.html` compatibility route, and
  benchmark markers.
- Visual and interaction polish still needs a dedicated source+browser pass.

## 4. Target state

- First viewport of each primary page tells the reviewer what to do next.
- Primary workflows expose progress, activity logs, replay/export artifacts,
  and local/hub trust boundaries.
- Deep links and sample buttons resolve from source without relying on live
  state.
- Page copy is specific about deterministic extraction, local Gemma calls,
  queued OCR/vision work, and reviewer confirmation.

## 5. Files to read first

1. `docs/codex/00_do_not_break.md`
2. `scripts/validate_kaggle_page_sources.py`
3. `packages/duecare-llm-chat/src/duecare/chat/static/process.html`
4. `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html`
5. `packages/duecare-llm-chat/src/duecare/chat/static/search.html`
6. `packages/duecare-llm-chat/src/duecare/chat/static/share.html`
7. `packages/duecare-llm-chat/src/duecare/chat/static/templates.html`
8. `kaggle/01-duecare-exploration-workbench/tests/README.md`

## 6. Files to modify

Modify only the active workbench source pages and focused tests needed for the
observed issue. Prefer shared primitives in `_chrome.css`, `_nav.js`,
`_activity_log.js`, and `_examples_picker.js` over page-local duplicates.

## 7. Files to create

Add focused tests or Playwright specs only when they pin a real reviewer-facing
contract.

## 8. Acceptance criteria

1. `process.html`, `knowledge.html`, `search.html`, `share.html`, and
   `templates.html` have visible progress/log/export/trust-boundary affordances.
2. No broken `/static/*` or `/wb-static/*` source references.
3. No page implies a bundle-level brief is paragraph/page/document analysis.
4. Activity-log handles named in `00_do_not_break.md` remain unchanged.
5. The Kernel 01 Playwright smoke path can load sample data and reach the
   expected result panels when browser dependencies are available.

## 9. Do-not-break checklist

- Do not rename routes, DOM IDs, log handles, sample artifact filenames, or
  kernel folders.
- Do not add per-page model-loading popovers; use the shared top chrome.
- Do not use `innerHTML` for user-derived values unless escaped and justified.

## 10. Verification commands

```bash
py -3.12 scripts/validate_kaggle_page_sources.py
python scripts/validate_main_kaggle_kernels.py
python -m pytest packages/duecare-llm-chat/tests/test_harness_workbench.py -q
python -m pytest packages/duecare-llm-chat/tests/test_workbench_inventory_integrity.py -q
```

If Playwright is installed:

```bash
npm.cmd run test:smoke --prefix kaggle/01-duecare-exploration-workbench/tests
```

## 11. The Codex prompt

```
Review and polish the active Kernel 01 workbench pages from source. Read
docs/codex/00_do_not_break.md, scripts/validate_kaggle_page_sources.py, and the
primary static pages in packages/duecare-llm-chat/src/duecare/chat/static.
Keep routes, DOM IDs, log handles, and sample filenames stable. Improve the
reviewer path only where source evidence shows a gap: progress, activity logs,
sample use, exports/replays, and trust boundaries. Run the page-source gate and
the main-kernel gate before committing.
```

## 12. Out of scope

- Hierarchical Gemma graph extraction, which is Goal 11.
- Benchmark kernel changes, which are Goals 14 and 15.
