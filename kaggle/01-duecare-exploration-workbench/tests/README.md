# Kernel 01 Playwright test harness

Validates DueCare Exploration Workbench (kernel 01) either against the bundled
quota-free local fake workbench or a published cloudflared URL. It captures
screenshots, runs regression tests for known bugs, and runs an automated
accessibility scan.

## When to use

- Before publishing, with no model download, API call, or Kaggle quota use.
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

## Run locally without model calls

With `KERNEL_URL` unset, Playwright starts `local_fake_workbench.py`, waits for
its health endpoint, runs the browser suite, and stops it automatically:

```powershell
Remove-Item Env:KERNEL_URL -ErrorAction SilentlyContinue
npm test
```

The runner uses the repository virtual environment when it exists. Override it
with `DUECARE_TEST_PYTHON` if needed. On a host where Playwright's downloaded
Chromium cannot launch, point it at an installed Chromium-family executable:

```powershell
$env:PLAYWRIGHT_EXECUTABLE_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
npm test -- --project=desktop-chromium
```

All responses and search results in this mode are deterministic fixtures.

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

## CI integration

The local fake-workbench mode is suitable for unattended CI because it has no
external service or model dependency. Use `KERNEL_URL` only for a separate live
deployment smoke lane; a live tunnel failure should not invalidate the offline
UI contract.
