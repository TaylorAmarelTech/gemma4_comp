# Goal 9 — Inline vocabulary normalization for graph-chat synthesis

> Status: **PENDING**. Created 2026-05-24.

## 1. Goal

When the graph-chat synthesis returns prose containing indicator / corridor / stage references, rewrite the non-canonical forms (`FeeBondage`, `ph-hk`, `Arrival`) to canonical form (`fee_bondage`, `PH-HK`, `arrival_and_placement`) so reviewers see the same vocabulary across every page.

## 2. Why it matters

`standardize_fact_envelope` normalizes vocabulary in structured envelopes, but the graph-chat synthesis answer is free prose. Gemma sometimes writes `"The recruiter was charged with FeeBondage in the PH-HK corridor at the Arrival stage."` — three non-canonical forms in one sentence. A reviewer flipping between knowledge.html (canonical) and process.html (Gemma's free-form synthesis) sees inconsistent terminology.

## 3. Current state

- `_safe_text.py` exports `_normalize_indicator`, `_normalize_corridor`, `_normalize_stage` — all private (underscore-prefixed).
- They operate on single tokens, not free text.
- The graph-chat synthesis returns whatever Gemma wrote.

## 4. Target state

- New public helper `normalize_inline_vocabulary(text)` in `_safe_text.py` that:
  - Scans free text for known non-canonical indicator names (every key in `_INDICATOR_ALIASES`), corridor variants (PH/HK, ph-hk, ph_hk), and stage variants (Arrival, placement, Recruit) using word-boundary regex.
  - Rewrites each match to canonical form, preserving surrounding words.
  - Idempotent: `normalize(normalize(x)) == normalize(x)`.
- Applied to the graph-chat synthesis text in `harnesses/process/handler.py` before returning the response.
- Tests cover word-boundary handling so we don't rewrite `"feebondage"` inside `"feebondagereport"`.

## 5. Files to read first

1. [`docs/codex/00_do_not_break.md`](../00_do_not_break.md) — section 8, section 9.
2. `packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py` — `_INDICATOR_ALIASES`, `_STAGE_ALIASES`, `_normalize_corridor`.
3. `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py` — find the graph-chat synthesis function (search for `"synthesis"` near `"graph-chat"`).
4. `packages/duecare-llm-chat/tests/test_knowledge_noise_scrub.py` — pattern for adding a `TestNormalizeInlineVocabulary` class.

## 6. Files to modify

| Path | What changes |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py` | Add public `normalize_inline_vocabulary(text)` |
| `packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py` | Apply it to the synthesis text before returning |
| `packages/duecare-llm-chat/tests/test_knowledge_noise_scrub.py` | Add `TestNormalizeInlineVocabulary` class |

## 7. Files to create

None.

## 8. Acceptance criteria

1. `normalize_inline_vocabulary(text)` exported from `_safe_text.py`.
2. Rewrites known indicator aliases with word boundaries:
   - `"the FeeBondage indicator"` → `"the fee_bondage indicator"`
   - `"FeeCamouflage and PassportRetention"` → `"fee_camouflage and passport_retention"`
3. Rewrites corridor variants:
   - `"the ph-hk corridor"` → `"the PH-HK corridor"`
   - `"PH/HK and ID-MY"` → `"PH-HK and ID-MY"`
4. Rewrites stage variants:
   - `"at the Arrival stage"` → `"at the arrival_and_placement stage"`
   - `"during placement"` → `"during arrival_and_placement"`
5. Does NOT rewrite substring matches:
   - `"feebondagereport"` stays unchanged.
6. None-safe + empty-safe: `normalize_inline_vocabulary(None) == ""`, `normalize_inline_vocabulary("") == ""`.
7. Idempotent: `normalize(normalize(x)) == normalize(x)`.
8. Applied to the graph-chat synthesis text in `process/handler.py` before returning.
9. New `TestNormalizeInlineVocabulary` class in `test_knowledge_noise_scrub.py` has at least 8 tests covering: indicator alias rewrites, corridor variants, stage variants, multi-word neighbors, no-substring-rewrite, idempotence, None/empty safety, and an end-to-end smoke that mixes all three.

## 9. Do-not-break checklist

- **Section 8**: Don't rename or remove canonical vocab tuples or alias maps. Just add a helper that reads them.
- **Section 9**: The helper must be idempotent.
- The existing `standardize_fact_envelope` is unchanged.
- The existing `clean_for_knowledge_fact` is unchanged — `normalize_inline_vocabulary` is a separate concern (vocab consistency, not noise removal).
- Process handler's existing `_fact_excerpt` calls are unchanged.

## 10. Verification commands

```bash
python -c "import ast, pathlib; ast.parse(pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py').read_text(encoding='utf-8')); print('PASS AST')"

# Standalone behavioral check (bypasses the broken import chain)
python -c "
import runpy
ns = runpy.run_path('packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py')
norm = ns['normalize_inline_vocabulary']
assert norm('the FeeBondage indicator') == 'the fee_bondage indicator', norm('the FeeBondage indicator')
assert norm('PH/HK and ID-MY') == 'PH-HK and ID-MY', norm('PH/HK and ID-MY')
assert norm('at the Arrival stage') == 'at the arrival_and_placement stage', norm('at the Arrival stage')
assert norm('feebondagereport') == 'feebondagereport', 'substring must not rewrite'
assert norm(None) == ''
assert norm('') == ''
assert norm(norm('the FeeBondage indicator')) == norm('the FeeBondage indicator'), 'idempotent'
print('PASS behavioral')
"

python -m pytest packages/duecare-llm-chat/tests/test_knowledge_noise_scrub.py -v
```

## 11. The Codex prompt

```
Read docs/codex/00_do_not_break.md sections 8 and 9, then read:
  - packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py
    for _INDICATOR_ALIASES, _STAGE_ALIASES, _normalize_corridor
  - packages/duecare-llm-chat/src/duecare/chat/harnesses/process/handler.py
    for the graph-chat synthesis function (search for "synthesis" near
    graph-chat)
  - packages/duecare-llm-chat/tests/test_knowledge_noise_scrub.py for
    the test class pattern

Add a public function normalize_inline_vocabulary(text) to _safe_text.py
that:
  - Scans free text for known non-canonical indicator names (every key
    in _INDICATOR_ALIASES), corridor variants (PH/HK, ph-hk, ph_hk),
    and stage variants (Arrival, placement, Recruit) using word-boundary
    regex.
  - Rewrites each match to canonical form, preserving surrounding words.
  - Idempotent. None-safe. Empty-safe.
  - Does NOT rewrite substring matches (use \b in the regex).

Apply it to the graph-chat synthesis text in process/handler.py before
returning the response.

Add TestNormalizeInlineVocabulary class to test_knowledge_noise_scrub.py
with at least 8 tests covering: indicator alias rewrites, corridor
variants, stage variants, multi-word neighbors, no-substring-rewrite,
idempotence, None/empty safety, end-to-end mixed smoke.

DO NOT:
  - rename or remove vocab tuples
  - change clean_for_knowledge_fact or standardize_fact_envelope
  - alter the existing synthesis logic beyond applying the helper as
    the last step

Acceptance criteria in docs/codex/goal_09_inline_vocab_normalize/handoff.md section 8.
```

## 12. Out of scope

- Casing the canonical strings differently per audience (e.g. "Fee Bondage" for human prose) — that's a render-layer concern.
- Building an aliases-CSV/JSON file (the in-code dict is the source of truth).
- Translating between languages.
- Auto-suggesting new aliases (Goal 7's audit script surfaces them).
