# Kernel 01 review rubric

Use alongside the automated Playwright suite for things eyes catch
better than code.

## Visual quality

- [ ] No overlapping text elements (labels colliding with badges / borders)
- [ ] No browser-native `alert()` popups in any user flow
- [ ] All clickable elements have visible hover states
- [ ] All modal overlays have a visible, reachable close button
- [ ] All inline-form errors render in the page (not in the system dialog)
- [ ] No "lorem ipsum" / "TODO" / "FIXME" / placeholder text
- [ ] No duplicate nav bars after sending a message
- [ ] No duplicate "Shutdown" / power buttons in the top bar
- [ ] Brand colors consistent: civic teal accent, ember reserved for
      privacy-boundary indicators only

## Content correctness

- [ ] Contact details come from the contacts tool or vetted contacts pack,
      with current verification metadata visible when possible
- [ ] Statute IDs in citations match the canonical set:
      `POEA MC 14-2017`, `ILO C189`, `RA 8042`, `BP2MI Reg 8-2023`
- [ ] No "for judges" framing in body copy (prefer "peer review")
- [ ] No off-by-one slot labels (folder N == display N)
- [ ] No stale roster counts (current active path: 01, 02, and A-00; remaining appendix notebooks archived)

## Behavior

- [ ] Model picker auto-opens on first visit when no model is loaded
- [ ] Model picker close button always visible after a manual re-open
- [ ] "Send" button is disabled when the input is empty
- [ ] "Compare" tab gracefully handles the no-baseline case
      (inline notice, not browser alert)
- [ ] Image-required prompts surface the hint banner ONLY when a
      prompt requiring an image is loaded (never on plain text turns)
- [ ] The resolve-step trace summary reflects actual image-ref count
      (not the static "image references resolved")
- [ ] `Esc` closes any open modal
- [ ] Backdrop click closes any open modal

## Performance

- [ ] Homepage paint < 2s on a warm cloudflared connection
- [ ] First model selection -> picker close < 90s for E2B/E4B
- [ ] Subsequent chat turns < 30s on E4B / T4 (cold start excluded)
- [ ] No console errors in DevTools after Run All

## Accessibility

- [ ] All form controls have visible labels
- [ ] All images have `alt` attributes
- [ ] Tab order matches visual reading order
- [ ] Focus rings visible on all interactive elements
- [ ] Color contrast ratio >= 4.5:1 for body text, >= 3:1 for UI controls
- [ ] No reliance on color alone to convey state (e.g., status badges
      also use icons or text)

## Submission-readiness

- [ ] Bundle export downloads a valid `<RUN_ID>_bundle.zip` with
      manifest.json + results.json + run.jsonl + metadata.json
- [ ] `/api/brand` returns the expected live counts (GREP / RAG /
      live tools / current rubric / example prompts)
- [ ] `/api/health-check` returns 200 with all layers `enabled: true`
- [ ] Reviewer quick-path table in the kernel's README matches what
      the live kernel actually does
