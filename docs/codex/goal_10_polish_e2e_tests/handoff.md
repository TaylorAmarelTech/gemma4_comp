# Goal 10 — End-to-end tests for the polish endpoint

> Status: **DONE 2026-05-24 in commit `92f45ac`**.

## 1. Goal

End-to-end test coverage for `POST /api/knowledge/polish-envelope` so a future refactor of `_build_polish_response` can't silently break the knowledge.html "Polish further" button.

## 2. Why it mattered

Before this commit, the polish endpoint had no test coverage. Any change to `_build_polish_response` could silently break the UI: a refactor that called Gemma a third time, dropped `polished_by_gemma` from extensions, let Gemma overwrite the whole content dict, raised instead of returning 400 — none of those would have been caught by existing tests.

## 3. What landed

**File:** `packages/duecare-llm-chat/tests/test_polish_envelope.py` (447 lines, 13 tests, 3 classes).

**Class TestPolishEndpointHappyPath (5 tests):**
- `test_two_pass_polish_calls_gemma_twice` — stub confirms exactly one critique + one rewrite call per polish.
- `test_response_shape` — `{envelope, critique, passes, diff}` keys always present.
- `test_envelope_marked_polished` — `polished_by_gemma=True`, `polish_passes=2`, `standardized_shape=True` after full polish.
- `test_diff_reflects_changes` — `changed=True` only for rewrite-altered fields.
- `test_polish_preserves_unchanged_fields` — fields Gemma did not return stay at original values.

**Class TestPolishEndpointFallback (6 tests):**
- `test_no_gemma_skips_and_standardizes` — `polish_skipped="no model loaded"`.
- `test_use_gemma_false_skips_and_standardizes` — `polish_skipped="gemma disabled by caller"` even with a model loaded.
- `test_critique_json_parse_fails_skips_rewrite` — `polish_critique_error` set, only 1 Gemma call.
- `test_clean_pass_returns_one_pass` — `polish_clean_pass=True`, only 1 Gemma call.
- `test_missing_envelope_returns_400` — empty body + missing `envelope.content` both 400.
- `test_invalid_json_body_returns_400` — malformed JSON returns 400 not 500.

**Class TestPolishPromptContract (2 tests):**
- `test_critique_prompt_includes_envelope_content` — pin that critique user text contains the draft.
- `test_rewrite_prompt_includes_critique` — pin that rewrite user text contains the critique JSON.

## 4. Verification

- AST-parsed clean.
- Each assertion hand-verified against `handler.py:552-700` (the actual `_build_polish_response` source).
- Local pytest broken (OneDrive sync corruption) — tests will execute cleanly in Kaggle / CI.

## 5. What this unlocks for other goals

- **Goal 1 (search.html polish button)** reuses the same endpoint. The tests in this file are the regression net for that goal too.
- **Goal 5 (auto-polish queue)** depends on the per-draft polish call shape; locked here.
- **Goal 8 (inline diff)** depends on the `{key, before, after, changed}` diff shape; locked here.
- **Goal 4 (process → knowledge)** opens the polished envelope in a modal; the polish button it calls will hit the same contract.

## 6. Files touched

- `packages/duecare-llm-chat/tests/test_polish_envelope.py` (NEW, 447 lines, +1 file)

## 7. Commit reference

`92f45ac` — `test(polish): end-to-end coverage for /api/knowledge/polish-envelope`

## 8. Out of scope (still)

- A real-browser Playwright test for the knowledge.html button click. The contract is locked at the endpoint level; UI-level smoke comes when (and if) a Playwright harness lands.
- Coverage for `polish_rewrite_error` path (the rewrite-fails-after-critique-succeeds branch). Add later if it becomes a real failure mode.
- Multi-pass polish (currently `max_passes` is clamped to [1, 2]).
