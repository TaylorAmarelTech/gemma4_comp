# Goal 6 — Sample bundle for templates.html

> Status: **DONE 2026-05-24** in commit `61c076e`. Created 2026-05-24.

## 1. Goal

Add a synthetic case bundle artifact + two buttons on templates.html so a first-time reviewer can round-trip the template fill flow in 30 seconds without having to first upload a bundle through process.html.

## 2. Why it matters

`.claude/rules/70_workbench_ui_primitives.md` rule 7 requires every page that accepts an artifact to ship a judge-safe sample for round-trip. Templates.html accepts a bundle JSON but ships no sample. A judge clicking into templates.html cold has no obvious next step; they have to go to process.html, upload the existing sample ZIP, wait for the pipeline, then come back. That's a five-minute detour for a one-page check.

## 3. Current state

- `process.html` ships `samples/case_files_sample.zip` with download + use buttons.
- `knowledge.html` ships `samples/knowledge_object_sample.json` and `samples/knowledge_bundle_sample.zip`.
- `templates.html` has no sample artifact.
- `scripts/build_static_samples.py` regenerates samples with fixed timestamps so the build is deterministic.
- `static/samples/sample_manifest.json` is the index.

## 4. Target state

- New sample: `samples/template_bundle_sample.json` — a synthetic case bundle (composite Maria-style; no real PII) sufficient to exercise the HK Labour Department template end-to-end.
- Templates.html grows two buttons: "Download sample bundle" and "Use sample bundle" (loads it into `_tplBundle` and triggers the dry-run preview).
- `scripts/build_static_samples.py` regenerates the new sample deterministically.
- `samples/sample_manifest.json` includes it.

## 5. Files to read first

1. [`docs/codex/00_do_not_break.md`](../00_do_not_break.md) — section 7 (sample artifacts).
2. `.claude/rules/70_workbench_ui_primitives.md` rule 7.
3. `scripts/build_static_samples.py` — see how other samples are built deterministically.
4. `packages/duecare-llm-chat/src/duecare/chat/static/samples/sample_manifest.json` — current index format.
5. `packages/duecare-llm-chat/src/duecare/chat/static/templates.html` — find where bundle JSON gets attached (`_tplBundle`).
6. `packages/duecare-llm-chat/src/duecare/chat/templates.py` — `bundle_excerpt_for_template` to understand what fields the bundle must have.

## 6. Files to modify

| Path | What changes |
|---|---|
| `scripts/build_static_samples.py` | Add a new sample-builder function for `template_bundle_sample.json` |
| `packages/duecare-llm-chat/src/duecare/chat/static/samples/sample_manifest.json` | Add entry for the new sample |
| `packages/duecare-llm-chat/src/duecare/chat/static/templates.html` | Add "Download sample bundle" + "Use sample bundle" buttons |

## 7. Files to create

| Path | Purpose |
|---|---|
| `packages/duecare-llm-chat/src/duecare/chat/static/samples/template_bundle_sample.json` | The actual sample (built by the script) |

## 8. Acceptance criteria

1. `samples/template_bundle_sample.json` is a valid JSON file (parses cleanly).
2. The sample is a case bundle with the shape `gemma_fill_template` expects:
   - `intelligence.summary` (dict with case overview)
   - `intelligence.case_brief` (string narrative)
   - `intelligence.people` (list — composite names only, e.g. "M.A." for Maria Amparo)
   - `intelligence.payments` (list with PHP placement fee + HKD salary deduction examples)
   - `intelligence.journey_points` (list covering recruitment → arrival → employment)
   - `intelligence.ilo_indicators` (list including `fee_camouflage` + `passport_retention` from `STANDARD_FACT_INDICATORS`)
   - `intelligence.entities` (dict with agency / employer / broker examples)
   - `intelligence.evidence_edges` (list with at least 3 typed edges)
3. NO real PII. All names are 1-2 letter initials. No real phone numbers, addresses, or case IDs.
4. The sample has `_meta.synthetic = true` so the page can show a banner.
5. Templates.html "Download sample bundle" button fetches `/static/samples/template_bundle_sample.json` and triggers a download.
6. Templates.html "Use sample bundle" button:
   - Fetches the JSON.
   - Sets `_tplBundle` to the parsed object.
   - Updates the bundle-display UI.
   - Triggers a dry-run preview (or post-Goal-3, fires `tplDryRunPreview()`).
   - Logs `tplLog.ok('Sample bundle loaded', 'X people, Y payments, Z indicators')`.
7. `scripts/build_static_samples.py` regenerates the sample deterministically (same content + same fixed timestamps every run).
8. `samples/sample_manifest.json` lists the new sample with `{name, path, role, used_by: ["templates.html"]}`.

## 9. Do-not-break checklist

- **Section 7**: Don't rename existing samples. New file is additive.
- The new sample MUST follow rule 10's PII-free invariant: no real names, no real case numbers.
- Don't change the existing `case_files_sample.zip` or `knowledge_*_sample.*` — they're used by other pages.
- Don't change the bundle JSON shape expected by `gemma_fill_template`; this sample must match the shape today.
- The build script must STAY pure-stdlib (no new pip deps).

## 10. Verification commands

```bash
python scripts/build_static_samples.py

python -c "import json, pathlib; b = json.loads(pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/samples/template_bundle_sample.json').read_text(encoding='utf-8')); intel = b['intelligence']; assert intel.get('case_brief') and intel.get('payments') and intel.get('ilo_indicators'); print('PASS sample shape')"

python -c "import json, pathlib; m = json.loads(pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/samples/sample_manifest.json').read_text(encoding='utf-8')); samples = m.get('entries', m.get('samples', m if isinstance(m,list) else [])); assert any(s.get('path','').endswith('template_bundle_sample.json') for s in samples); print('PASS manifest')"

python -c "import pathlib; t = pathlib.Path('packages/duecare-llm-chat/src/duecare/chat/static/templates.html').read_text(encoding='utf-8'); assert 'template_bundle_sample.json' in t and ('Use sample bundle' in t or 'Use sample' in t); print('PASS UI')"
```

## 11. The Codex prompt

```
Read docs/codex/00_do_not_break.md section 7, then read:
  - scripts/build_static_samples.py for the deterministic sample-build
    pattern (look at how case_files_sample.zip is generated)
  - packages/duecare-llm-chat/src/duecare/chat/static/samples/sample_manifest.json
  - packages/duecare-llm-chat/src/duecare/chat/static/templates.html for
    where bundle JSON gets attached (_tplBundle)
  - packages/duecare-llm-chat/src/duecare/chat/templates.py for
    bundle_excerpt_for_template — that's the shape the sample must match

Create a synthetic case bundle at
packages/duecare-llm-chat/src/duecare/chat/static/samples/template_bundle_sample.json
shaped like {intelligence: {summary, case_brief, people, payments,
journey_points, ilo_indicators, entities, evidence_edges}}.

Constraints:
  - Composite Maria-style example (initials only — "M.A.", "R.S.")
  - NO real PII (no real phone, address, case id)
  - payments include PHP 50000 placement fee + HKD 4000 salary deduction
  - ilo_indicators include "fee_camouflage" + "passport_retention" from
    STANDARD_FACT_INDICATORS (in _safe_text.py)
  - journey_points cover recruitment → arrival → employment
  - evidence_edges have at least 3 typed edges
  - top-level _meta.synthetic = true

Update scripts/build_static_samples.py with a builder function that
emits this JSON deterministically (fixed _meta.created_at). Update
sample_manifest.json with the new entry.

In templates.html, add "Download sample bundle" + "Use sample bundle"
buttons. Use sample fetches /static/samples/template_bundle_sample.json,
sets _tplBundle, updates the bundle-display UI, fires the dry-run
preview if Goal 3 has landed (otherwise just sets state), logs via
tplLog.ok.

DO NOT:
  - rename or modify existing samples
  - add real PII
  - add new pip deps to the build script
  - change the bundle JSON shape expected by gemma_fill_template

Verify per commands in docs/codex/goal_06_template_sample_bundle/handoff.md section 10.
```

## 12. Out of scope

- Multiple sample bundles (one rich enough example is sufficient).
- Internationalized sample (English only for this version).
- A bundle-builder UI on templates.html (users still go through process.html for real bundles).
- Sample manifest schema evolution.
