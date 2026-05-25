# Goal 13 - Kernel 02 recording-path polish and replay verification

> Status: **PENDING**. Created 2026-05-25 after reviewing `/start`,
> `/slides`, and `/slides/setup` from source.

## 1. Goal

Make Kernel 02's recording path visually stable, source-link clean, and honest
about cached replay versus live Gemma inference.

## 2. Why it matters

Kernel 02 is the focused judge/video path. It should open quickly, show the
right recording entrypoint, preload cached examples when needed, and link back
to the shared workbench without broken CSS or stale source paths.

## 3. Current state

- `kaggle/02-live-demo/kernel.py` launches `duecare.server.create_app`.
- The server serves `/start`, `/slides`, `/slides/setup`, and cross-mounts the
  Kernel 01 workbench static directory at `/wb-static`.
- `/start` and `/slides/setup` now link the correct `/static/style.css`.
- `packages/duecare-llm-server/tests/test_slides_surface.py` pins key slide
  routes and cached replay APIs.

## 4. Target state

- `/start` is a clean two-choice recording launcher.
- `/slides` is camera-safe at common desktop and laptop widths and never blocks
  on live model latency for the cached demo slide.
- `/slides/setup` clearly stores `duecare.slides.demo.pack` and
  `duecare.slides.demo.chat`, validates the selected examples, and points to
  `/slides#demo-chat`.
- All `/wb-static/*` sample links resolve from the chat package.

## 5. Files to read first

1. `docs/codex/00_do_not_break.md`
2. `scripts/validate_kaggle_page_sources.py`
3. `packages/duecare-llm-server/src/duecare/server/static/start.html`
4. `packages/duecare-llm-server/src/duecare/server/static/slides.html`
5. `packages/duecare-llm-server/src/duecare/server/static/slides-setup.html`
6. `packages/duecare-llm-server/src/duecare/server/slides_cache.py`
7. `packages/duecare-llm-server/tests/test_slides_surface.py`

## 6. Files to modify

Keep edits inside the server static pages, slides cache, and focused tests
unless a shared workbench link is broken.

## 7. Files to create

Optional: a screenshot checklist or Playwright test only if it can run without
GPU/model setup.

## 8. Acceptance criteria

1. `/start`, `/slides`, `/slides/setup`, `/static/style.css`, and required
   `/wb-static/samples/*` links serve in TestClient.
2. The recording deck labels cached replay honestly and does not claim live
   inference when replaying stored rows.
3. Canonical wording stays aligned: content moderation, worker support,
   anonymized knowledge sharing, six lanes.
4. No broken `/static/styles.css` regressions.

## 9. Do-not-break checklist

- Do not rename `/start`, `/slides`, `/slides/setup`, or the two slide localStorage keys.
- Do not remove the `/wb-static` cross-mount expectation.
- Do not add unsupported live benchmark or model-performance claims.

## 10. Verification commands

```bash
py -3.12 scripts/validate_kaggle_page_sources.py
python scripts/validate_main_kaggle_kernels.py
python -m pytest packages/duecare-llm-server/tests/test_slides_surface.py -q
```

## 11. The Codex prompt

```
Review Kernel 02 from source: /start, /slides, /slides/setup, slides_cache.py,
and test_slides_surface.py. Polish the recording path without changing public
routes or localStorage keys. Keep cached replay labels honest, verify static
assets, and run validate_kaggle_page_sources plus the main-kernel gate.
```

## 12. Out of scope

- New slide architecture.
- Live GPU/model timing claims unless measured in a fresh Kaggle run.
