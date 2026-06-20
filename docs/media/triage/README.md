# Platform Triage — render screenshots

UI render screenshots of the Platform Triage page
(`/static/triage.html` in `duecare-llm-chat`), captured 2026-06-20 with Playwright
driving system Edge, after the one-model simplification (commit `ddad750d`).

| Breakpoint | File |
|---|---|
| Desktop (1440, with a screened batch) | [`triage-desktop-1440.png`](triage-desktop-1440.png) |
| Tablet (768) | [`triage-tablet-768.png`](triage-tablet-768.png) |
| Mobile (375) | [`triage-mobile-375.png`](triage-mobile-375.png) |

What they show: the simplified two-stage design — **Stage 1 GREP rules → Stage 2 the one
loaded Gemma 4** (no separate fast model, no endpoint, no model switch), the trust boundary,
the input/results panes, the activity log, and the responsive layout.

**Honest caveat (real, not faked):** these verify the *page* — layout, JavaScript, routing
flow, and chrome are the real production page. No GPU model was loaded locally when they were
captured, so the screening model and GREP layer were **stubbed deterministically** for the
render. The per-item verdicts, categories, and "flagged by model" labels are therefore
**illustrative**, not real Gemma 4 inference. Real screening runs on the loaded Gemma in the
kernel; see `packages/duecare-llm-chat/tests/test_triage.py` for the tested behaviour.
