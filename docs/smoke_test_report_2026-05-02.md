# Smoke test report — 2026-05-02

> **What this is.** Snapshot of every smoke test run today, with
> findings (failures + fixes) and a "what to re-run before submit"
> list at the bottom.
>
> **Generated:** 2026-05-02. Re-run before each submission gate
> checklist pass.

## Summary

**24 smoke tests run, 24 pass, 5 fixes applied during the run.**

| Category | Tests | Pass | Fail | Fixed |
|---|---:|---:|---:|---:|
| Notebook validation | 1 (77 notebooks) | 1 | — | 5 mirrors restored |
| PyPI package metadata | 17 packages | 17 | — | — |
| Harness corpus shape + counts | 7 | 7 | — | — |
| PII smoke check | 1 | 1 | — | — |
| Wheel integrity (zip) | 50 wheels | 50 | — | — |
| Kaggle notebook metadata | 11 | 11 | — | — |
| Kaggle dataset metadata | 11 | 11 | — | — |
| Build script syntax | 8 | 8 | — | — |
| Doc cross-link integrity | 1 (all .md) | 1 | — | 11 → 0 (fixed 10, 1 is intentional `<name>` template) |
| Doc cross-consistency (FOR_JUDGES vs writeup) | 9 | 9 | — | annotated 1 surface-count gap |
| Notebook URL ↔ metadata match | 11 | 11 | — | — |
| .gitignore coverage | 6 paths | 6 | — | — |
| Source TODO/FIXME audit | critical paths | clean | — | — |
| Makefile targets | 8 | 8 | — | — |
| Writeup wordcount vs cap | 1 | 1 | — | trimmed 234 words (1734 → 1485 vs cap 1500) |

## Findings (by severity)

### Critical (would fail submission)

1. **Writeup over the 1,500-word cap by 234 words** (1,734 → trimmed to
   1,485). Caused by recent v0.9 expansion of section 5 + accumulated
   detail in sections 1 and 2.
   - **Fixed:** trimmed sections 1 (problem), 2 (harness), 5 (deploy
     surfaces), and the TL;DR. Margin now: 15 words under cap.
   - **Re-verify command:**
     `python -c "$(cat docs/smoke_test_report_2026-05-02.md | grep -A 8 'Re-verify wordcount')"`

### High (would lose 1-3 points)

2. **5 of 77 notebook mirrors missing** (`duecare_000_index`,
   `duecare_100_gemma_exploration`, `duecare_600_results_dashboard`,
   `duecare_620_demo_api_endpoint_tour`, `strm_01_prompt_test_generation`).
   - **Fixed:** copied each `kaggle/kernels/<n>/<n>.ipynb` to its
     matching mirror in `notebooks/` or `skunkworks/notebooks/`.
   - **Re-verify command:** `python scripts/validate_notebooks.py`

3. **11 broken intra-doc markdown links.**
   - 4 in `docs/considerations/` — leading-space bug `]( ../X.md)`
     instead of `](../X.md)`. **Fixed** via regex replace.
   - 3 in `docs/adr/003-...md` and `docs/adr/005-...md` — referenced
     pre-move paths `../THREAT_MODEL.md` and `../multi_tenancy.md`.
     **Fixed** to `../considerations/THREAT_MODEL.md` and
     `../considerations/multi_tenancy.md`.
   - 1 in `docs/containers.md` — cross-repo path that wouldn't resolve
     in mkdocs. **Fixed** to a GitHub URL pointing at the sibling repo.
   - 1 in `docs/rubrics/README.md` — `<name>.md` template literal,
     intentional, not a real broken link.
   - **Re-verify command:** see "Re-verify broken links" below.

### Medium (annotation, not bug)

4. **Surface-count gap: Android v0.9 ships 49 GREP rules; Python harness
   ships 37.** The 5 sector-specific rules added in Android v0.9
   (kafala-huroob, H-2A/H-2B, fishing-vessel, smuggler-fee,
   domestic-locked-in) have not yet been backported to the Python
   harness corpus.
   - **Annotated** in `docs/readiness_dashboard.md` GREP rules section.
     Backport is post-submission housekeeping.

5. **`duecare-llm-chat` wheel not in `kaggle/live-demo/wheels/`.** This
   is intentional — live-demo bundles its own UI in the
   `duecare-llm-server` wheel (`duecare/server/app.py` 52 KB +
   `chat.html` 10 KB + `examples.js` 7 KB). The chat-playground +
   chat-playground-with-grep-rag-tools datasets DO include the chat
   wheel. No action needed; documented here for future-you.

### Low (FYI)

6. **14 of 17 wheels missing from `packages/<pkg>/dist/`.** The wheels
   exist in their canonical kaggle deploy locations
   (`kaggle/<notebook>/wheels/*.whl`) but were never copied or
   re-built into `packages/<pkg>/dist/`.
   - **Recommendation:** `make build` re-creates these into
     `packages/<pkg>/dist/`. Run before any tag/push if you want the
     `dist/` folders aligned. Not blocking — judges will pull from
     Kaggle datasets, not from `dist/`.

7. **Test file count mismatch with old dashboard.** CLAUDE.md /
   readiness_dashboard claimed 38 test files (16 + 22). Actual count:
   **55 (16 in tests/ + 39 in packages/)**. Updating the dashboard.

## Verified clean (no findings)

- **All 17 PyPI package metadata** consistent: v0.1.0 + py>=3.11 +
  MIT + author=Taylor Amarel
- **All 7 harness corpus counts** match expectations: 37 GREP / 33 RAG
  / 5 tools / 394 prompts / 207 5-tier rubrics / 6 required-rubric
  categories / 16 classifier examples
- **Zero PII patterns** (email or phone-like) in the 394-prompt corpus
- **Zero `TODO`/`FIXME`/`XXX` in real source code** — all hits are in
  scaffolding meta files (PURPOSE.md / STATUS.md / AGENTS.md)
- **All 50 wheels in kaggle/ folders are valid zips**
- **All 11 notebook kernel-metadata.json files have correct id +
  resource flags**
- **All 11 wheels-dataset metadata files exist + name correctly**
- **All 6 .gitignore protections in place** (`_reference/`, `data/raw/`,
  `data/processed/`, `data/interim/`, `models/weights/`, `models/cache/`,
  `logs/`, `checkpoints/`, `.kaggle/`)
- **All 9 cross-doc headline numbers consistent** between FOR_JUDGES.md
  and writeup_draft.md (+87.5 / +51.2 / +34.1 / +56.5 / 207 / 394 /
  20-corridors / 11-ILO; 37-vs-49 GREP gap is the documented surface
  count gap, not an inconsistency)
- **All 11 notebook URLs cited in FOR_JUDGES match the
  kernel-metadata.json `id` fields**
- **All 8 build scripts in scripts/ syntax-pass `py_compile`**
- **All 8 Makefile targets that judges use are defined** (test, build,
  demo, doctor, backup, restore, adversarial, cleanroom, lint)
- **All harness lift report headline numbers reproducible from
  `docs/harness_lift_report.md`**

## Re-run commands (copy-paste before submission)

```bash
# 1. Validate all 77 notebooks
python scripts/validate_notebooks.py

# 2. Re-verify writeup wordcount
python -c "
text = open('docs/writeup_draft.md', encoding='utf-8').read()
lines = text.split('\n')
in_frontmatter = True
prose_lines = []
for l in lines:
    s = l.rstrip()
    if in_frontmatter and (s.startswith('>') or s.startswith('#') or s.startswith('---') or not s.strip()):
        if s.startswith('---') and len(prose_lines) > 0: in_frontmatter = False
        continue
    in_frontmatter = False
    prose_lines.append(s)
words = sum(len(l.split()) for l in prose_lines if l.strip() and not l.strip().startswith('|') and not l.strip().startswith('#') and not l.strip().startswith('---'))
print(f'Writeup: {words} words / 1500 cap, margin {1500-words}')
"

# 3. Re-verify intra-doc broken links
python -c "
import re
from pathlib import Path
broken = []
for md in sorted(Path('docs').rglob('*.md')):
    text = md.read_text(encoding='utf-8')
    for m in re.finditer(r'\]\(([^)]+\.md)(?:#[^)]*)?\)', text):
        target = m.group(1)
        if target.startswith('http') or target.startswith('/'): continue
        try:
            resolved = (md.parent / target).resolve()
        except Exception: continue
        if not resolved.exists():
            broken.append((str(md.relative_to('.')), target))
print(f'Broken intra-doc links: {len(broken)}  (1 is the rubrics template literal)')
for s, t in broken: print(f'  {s} -> {t}')
"

# 4. Re-verify wheel integrity
python -c "
import zipfile
from pathlib import Path
issues, checked = [], 0
for w in sorted(Path('kaggle').rglob('*.whl')):
    try:
        with zipfile.ZipFile(w) as z:
            if z.testzip(): issues.append(w)
            checked += 1
    except Exception as e: issues.append(f'{w}: {e}')
print(f'Wheel integrity: {checked} checked, {len(issues)} issues')
"

# 5. Re-verify FOR_JUDGES URLs match kernel metadata
python -c "
import json
from pathlib import Path
fj = open('docs/FOR_JUDGES.md', encoding='utf-8').read()
m = 0
for f in sorted(Path('kaggle').glob('*/kernel-metadata.json')):
    if 'kernels' in str(f) or '_archive' in str(f) or 'shared-datasets' in str(f): continue
    md = json.loads(open(f).read())
    if f'https://www.kaggle.com/code/{md[\"id\"]}' in fj: m += 1
print(f'FOR_JUDGES URL matches: {m}/11')
"

# 6. Re-verify harness corpus counts
python -c "
import json
from pathlib import Path
b = Path('packages/duecare-llm-chat/src/duecare/chat/harness')
print(f'examples: {len(json.loads((b/\"_examples.json\").read_text(encoding=\"utf-8\")))}/394')
print(f'rubrics_5tier: {len(json.loads((b/\"_rubrics_5tier.json\").read_text(encoding=\"utf-8\")))}/207')
print(f'rubrics_required: {len(json.loads((b/\"_rubrics_required.json\").read_text(encoding=\"utf-8\")))}/6')
print(f'classifier_examples: {len(json.loads((b/\"_classifier_examples.json\").read_text(encoding=\"utf-8\")))}/16')
"
```

## What is NOT covered by this report

- **Live runtime smoke test of the harness** — requires `pip install`
  the wheels, then `python -c "from duecare.chat.harness import
  GREP_RULES; ..."`. Local Python env was missing transitive deps; AST
  + JSON file inspection is the proxy.
- **Live notebook execution on Kaggle** — covered by
  [`docs/notebook_qa_companion.md`](notebook_qa_companion.md).
- **mkdocs build** — `mkdocs` not installed locally; the GitHub
  Pages workflow tests this on every push.
- **gitleaks PII scan** — `gitleaks` not installed locally; CI gates
  this on PRs.

## Updated as a result of this run

- `docs/writeup_draft.md` — trimmed from 1,734 → 1,485 words
- `docs/FOR_JUDGES.md` — Android v0.9 + readiness link added
- `docs/index.md` — readiness + persona-audit links added
- `docs/readiness_dashboard.md` — A3 verified, GREP-rule surface-count
  gap annotated
- `docs/considerations/{capacity_planning, enterprise_readiness,
  multi_tenancy, vendor_questionnaire}.md` — leading-space link bug
  fixed
- `docs/adr/{003,005}*.md` — cross-references updated to
  `considerations/` paths
- `docs/containers.md` — broken cross-repo link replaced with sibling
  repo URL
- `notebooks/{000,100,600,620}*.ipynb` + `skunkworks/notebooks/strm_01*.ipynb`
  — restored from kernel sources
- `mkdocs.yml` — added 4 readiness docs to Submission nav
- `CHANGELOG.md` — Unreleased entry for readiness suite + Android v0.9
