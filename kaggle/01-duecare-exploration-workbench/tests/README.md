# Kernel 01 Playwright test harness

Validates the live DueCare Exploration Workbench (kernel 01) against
a published cloudflared URL. Captures screenshots, runs regression
tests for known bugs, and runs an automated accessibility scan.

## When to use

- After Run All on kernel 01 in Kaggle prints a
  `https://<random>.trycloudflare.com/` URL.
- Before recording the submission video.
- After any change to `packages/duecare-llm-chat/src/duecare/chat/static/`.

## One-time setup

```powershell
cd kaggle/01-duecare-exploration-workbench/tests
npm install
npx playwright install chromium
```

## Run against a live kernel URL

```powershell
$env:KERNEL_URL = "https://<your-trycloudflare-url>"
npx playwright test
npx playwright show-report
```

Linux/macOS:

```bash
KERNEL_URL=https://<your-trycloudflare-url> npx playwright test
```

## What gets run

| Spec | What it checks |
|---|---|
| `specs/smoke.spec.ts` | Homepage 200; main nav present; model picker overlay reachable; key sample-prompt buttons render. |
| `specs/ui-bugs.spec.ts` | Regression: "This prompt expects an image" hidden by default; no "best for judges" badge overlap; Compare tab has no `alert()` popup; model picker close button visible on re-open; resolve step doesn't claim image refs on text-only turns; no duplicate nav bars after sending a message; no duplicate shutdown buttons. |
| `specs/visual.spec.ts` | Full-page screenshots at 3 viewports (desktop / tablet / mobile) + screenshots of: model picker open, harness toggle panel, examples modal, compare tab, grading modal. Saved to `test-results/`. |
| `specs/accessibility.spec.ts` | axe-core scan for WCAG 2.1 AA violations on homepage + key modals. |

## Self-diagnosis

If a test fails:

1. **HTML report** -- `npx playwright show-report` opens an interactive
   HTML report with failure traces, screenshots, video, and DOM
   snapshots at each step.
2. **Trace viewer** -- `npx playwright show-trace test-results/<...>.zip`
   for a step-through replay of the failed run.
3. **Screenshot diff** -- `test-results/<test>/<image>-diff.png` shows
   what changed when a visual baseline differs.

## Review rubric

See [`RUBRIC.md`](./RUBRIC.md) for the manual review checklist that
complements the automated tests.

## CI integration (post-hackathon)

These tests are NOT wired into the project CI yet because they need a
live cloudflared URL. Post-hackathon, add a Render preview deployment
of `apps/duecare-ai.com/` and point KERNEL_URL there for unattended
runs.
