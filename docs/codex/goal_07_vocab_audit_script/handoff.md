# Goal 7 — Vocabulary discovery script

> Status: **PENDING**. Created 2026-05-24.

## 1. Goal

A read-only stdlib script that walks every saved knowledge envelope and reports which indicators, corridors, and stages they reference — bucketed as CANONICAL, KNOWN_ALIAS, or UNKNOWN so the user can decide what to add to the canonical vocab tuples.

## 2. Why it matters

`STANDARD_FACT_INDICATORS` today has 16 entries. Real saved knowledge produces tokens we haven't yet catalogued (especially when Gemma rewrites use slightly different wording). Without visibility, the vocabulary drifts: drafts saved with a non-canonical indicator string become invisible to chart filters and aggregation queries.

This script gives the user a signal to either:
- Add the surfaced token to `STANDARD_FACT_INDICATORS` (after confirming it's a real indicator).
- Trace upstream and fix the source.
- Drop the offending envelope.

## 3. Current state

- Saved envelopes live in a local knowledge store (read `/api/knowledge/list` handler in `chat/app.py` to find the actual path).
- `_safe_text.py` exposes `STANDARD_FACT_INDICATORS`, `STANDARD_FACT_STAGES`, `_INDICATOR_ALIASES`, `_STAGE_ALIASES`.
- No audit visibility.

## 4. Target state

- New script `scripts/audit_knowledge_vocabularies.py` that:
  - Walks every saved knowledge envelope under the local store.
  - Extracts every `content.indicators`, `content.applies_to_indicators`, `content.signal_types`, `content.corridor`, `content.corridors`, `content.applicable_corridors`, `content.journey_stage`, `content.stages` value.
  - Bucketing per token:
    - CANONICAL — appears in `STANDARD_FACT_*`
    - KNOWN_ALIAS — appears in `_*_ALIASES`
    - UNKNOWN — neither
  - For UNKNOWN tokens, prints the envelope path + the offending value + count.
- Pure stdlib (no pip install). Runs from repo root.
- Read-only. Never modifies a file.

## 5. Files to read first

1. [`docs/codex/00_do_not_break.md`](../00_do_not_break.md) — section 8.
2. `packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py` — vocab tuples + alias maps.
3. `packages/duecare-llm-chat/src/duecare/chat/app.py` — find the `/api/knowledge/list` handler (~line 5900) and the path it walks.
4. `scripts/verify_knowledge_surfaces.py` — example of a pure-stdlib audit script (no pip imports).

## 6. Files to modify

None.

## 7. Files to create

| Path | Purpose |
|---|---|
| `scripts/audit_knowledge_vocabularies.py` | The audit script |

## 8. Acceptance criteria

1. Script runs from repo root: `python scripts/audit_knowledge_vocabularies.py`.
2. No pip imports — only stdlib. Use `ast.parse()` on `_safe_text.py` to extract the tuples without importing the package (the package import chain depends on pip-installed FastAPI/pydantic).
3. Output sections:
   - Header: total envelopes scanned, total unique tokens by class.
   - CANONICAL section: count of envelopes referencing each canonical token (descending).
   - KNOWN_ALIAS section: token → canonical mapping + count.
   - UNKNOWN section: per token, list of envelope paths (up to 10 per token) + total count.
4. Exit code 0 even when UNKNOWN tokens exist (non-blocking).
5. Optional `--strict` flag: exit code 1 if any UNKNOWN tokens found.
6. Optional `--store-path PATH` flag to override the detected knowledge-store path.
7. Read-only: no file writes, no `Path.touch()`, no `Path.write_text()`.
8. Handles missing store dir gracefully (prints "No envelopes found at <path>" and exits 0).

## 9. Do-not-break checklist

- **Section 8**: Don't rename or remove canonical vocab tuples; just read them.
- **Section 9**: The script must be stdlib-only so it works on the OneDrive-broken local Python (the same constraint `scripts/verify_knowledge_surfaces.py` honors).
- Don't import from `duecare.chat.*` directly. Parse `_safe_text.py` via `ast` to extract the tuples.

## 10. Verification commands

```bash
python scripts/audit_knowledge_vocabularies.py

python scripts/audit_knowledge_vocabularies.py --strict; echo "exit=$?"

# Confirm no pip imports
python -c "import ast, pathlib; tree = ast.parse(pathlib.Path('scripts/audit_knowledge_vocabularies.py').read_text(encoding='utf-8')); imports = [n.module or n.names[0].name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]; non_stdlib = [i for i in imports if i and not i.split('.')[0] in {'os','sys','re','json','ast','pathlib','argparse','collections','typing','dataclasses','itertools'}]; assert not non_stdlib, f'non-stdlib imports: {non_stdlib}'; print('PASS stdlib-only')"
```

## 11. The Codex prompt

```
Read docs/codex/00_do_not_break.md section 8. Then read:
  - packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py
    for STANDARD_FACT_INDICATORS, STANDARD_FACT_STAGES,
    _INDICATOR_ALIASES, _STAGE_ALIASES
  - packages/duecare-llm-chat/src/duecare/chat/app.py for the
    /api/knowledge/list handler to find the knowledge-store path
  - scripts/verify_knowledge_surfaces.py for the pure-stdlib audit
    script pattern

Create scripts/audit_knowledge_vocabularies.py that:
  1. Uses ast.parse() to extract STANDARD_FACT_INDICATORS,
     STANDARD_FACT_STAGES, _INDICATOR_ALIASES, _STAGE_ALIASES from
     _safe_text.py (don't import duecare; the package import chain is
     broken locally).
  2. Walks every saved knowledge envelope under the detected store path.
  3. Extracts every content.indicators, content.applies_to_indicators,
     content.signal_types, content.corridor, content.corridors,
     content.applicable_corridors, content.journey_stage, content.stages
     value.
  4. Bucketing per token: CANONICAL / KNOWN_ALIAS / UNKNOWN.
  5. Prints a report:
     - Header: total envelopes scanned + counts.
     - CANONICAL: count per canonical token, descending.
     - KNOWN_ALIAS: token → canonical + count.
     - UNKNOWN: per token, envelope paths (up to 10) + total count.

Support --strict (exit 1 if UNKNOWN) and --store-path PATH.

Pure stdlib. Read only. Handle missing store dir gracefully.

Acceptance criteria in docs/codex/goal_07_vocab_audit_script/handoff.md section 8.
```

## 12. Out of scope

- Auto-adding UNKNOWN tokens to the vocab tuples (humans review the PR).
- Suggesting alias mappings (just surface the raw tokens).
- A web UI for the audit.
- Walking remote stores (Hub sync etc.).
