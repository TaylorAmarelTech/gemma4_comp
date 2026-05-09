# Claude Code: Execute with evidence — no shortcuts, no partial claims

You are working in the `gemma4_comp` repository.

This is not a brainstorming session. This is a careful execution session. You must think deliberately, read the current files before touching them, reason from evidence, make small focused edits, validate them, commit them, and push them. Do not summarize work you did not verify.

## Prime directive

Use your full reasoning budget. Slow down. Be logical. Treat this like a release-hardening pass for a public hackathon submission that judges will inspect.

For every claim you make, you need evidence from one of:
- a file you actually read in this session
- command output from this session
- a test/smoke check from this session
- the current git diff

If you have not verified something in this session, say "not verified yet." Do not rely on old memory, previous summaries, or assumptions.

## Non-negotiable constraints

- Do not edit `_reference/`.
- Do not run Kaggle publishing commands.
- Do not upload kernels, datasets, models, wheels, or notebooks.
- Do not commit raw PII, case narratives, real private names, emails, phone numbers, addresses, passport/visa IDs, or raw worker data.
- Do not break public route aliases or env aliases.
- Preserve the OpenClaw/server-automation compatibility pattern:
  - old routes redirect
  - old env vars are still read
  - new names are preferred in docs
- Do not overwrite user or formatter changes blindly.
- Before editing any modified file, inspect its current contents and current diff.
- If `apps/duecare-ai.com/app/data/demo_priority_examples.json` is modified, do not touch it unless the task explicitly requires it.
- Notebook presentation rules apply to `.ipynb` saved-output HTML, not the served browser app. Do not incorrectly remove browser-app CSS/JS just because Kaggle notebook HTML has restrictions.
- The Render hub is a coordination layer, not hosted Gemma GPU inference.

## Anti-shortcut rules

You must not:
- say "done" without tests or smoke checks
- mark a task complete because the code "looks right"
- edit from memory without reading the current file
- batch unrelated fixes into one commit
- leave uncommitted work unless handing off with a clear reason
- push if tests are red
- claim a page works without opening it, using a TestClient render check, or curling it locally
- claim the live Render deploy is current unless you checked the deployed version or health output
- claim a notebook exists unless you verified the file exists
- claim a doc is consistent unless you grepped for stale competing terms
- use "should," "probably," or "likely" in the final handoff for anything that should be verified

If you cannot verify something, write exactly:
> Not verified in this session.

## Required mental model

Keep these surfaces separate:

1. `kaggle/01-duecare-harness-chat/`
   - Core competition notebook.
   - Omni harness/chat playground.
   - Judge-facing.

2. `kaggle/02-live-demo/`
   - Core polished product demo.
   - Judge-facing.

3. `kaggle/A-01-*` through `kaggle/A-11-*`
   - Appendix evidence notebooks.
   - Judge-facing, but secondary.

4. `kaggle/kernels/`
   - 77-notebook research pipeline.
   - Evidence/reproducibility, not the primary submission narrative.

5. `legacy_notebooks/`
   - Local mirror for the research pipeline.
   - Not the main competition surface.

6. `skunkworks/`
   - Experimental work.
   - Not the main competition surface.

7. `apps/duecare-ai.com/`
   - Public Render coordination hub.
   - CPU-only, no raw cases, no Gemma GPU inference.

8. `packages/duecare-llm-chat/`
   - Interactive browser app/wheel runtime.
   - Browser app CSS/JS is allowed; do not apply Kaggle saved-output restrictions there.

Every edit should make this separation clearer.

## Rubric lens for every decision

Before editing, ask:

1. Does this improve Impact & Vision?
2. Does this improve Video Pitch & Storytelling?
3. Does this improve Technical Depth & Execution?
4. Does it make the demo more visible, credible, or easier for judges to follow?
5. Does it reinforce: "Privacy is non-negotiable"?

If the answer is no to all five, do not do that edit.

## Start-of-session commands

Run these first from the repo root. Capture the outputs in your notes.

```powershell
git status --short
git log -1 --oneline
git branch --show-current
```

Then inspect whether user changes exist:

```powershell
git diff --name-only
git status --short
```

If there are modified files, classify them:
- files you must touch
- files you must avoid
- files that need human confirmation before touching

Do not edit until this classification is clear.

## Required read-before-edit files

Read these current files before making the first edit:

- `CLAUDE.md`
- `.claude/rules/00_overarching_goals.md`
- `.claude/rules/10_safety_gate.md`
- `.claude/rules/20_code_style.md`
- `.claude/rules/30_test_before_commit.md`
- `.claude/rules/60_notebook_presentation.md`
- `docs/GPT55_HANDOFF_EXECUTION_PROMPT.md`
- `docs/GPT55_GO_NOW_FOLLOWUP.md`
- `docs/writeup_draft.md`
- `docs/video_script.md`
- `docs/FOR_PEER_REVIEW.md`
- `docs/FOR_KAGGLE_JUDGES.md`
- `docs/notebook_index.md`
- `docs/project_status.md`
- `README.md`
- `kaggle/README.md`
- `kaggle/_INDEX.md`
- `apps/duecare-ai.com/README.md`
- `render.yaml`
- `apps/duecare-ai.com/docs/RENDER.md`

For any file you plan to edit, read it top to bottom first.

## Required evidence matrix before editing

Before making edits, create a short private working matrix in your notes with these columns:

| Area | Files inspected | Current observed state | Defect/risk | Edit needed? |
|---|---|---|---|---|

Minimum rows:
- Git state
- Writeup
- Kaggle core notebooks
- Kaggle appendix notebooks
- Kaggle/research/legacy separation
- Render hub
- Website templates
- Browser wheel app
- Tests/smoke checks

Do not produce a long report to the human. This matrix is for your execution discipline. But your final handoff must reflect what you verified.

## Tier 0 execution order

Work top-down. Do not start Tier 1 until Tier 0 is done or blocked.

### T0.1 Verify local HEAD and live deploy version

Run:

```powershell
git log -1 --format="%h %s"
```

Then check the deployed health/version endpoint if available:

```powershell
curl.exe -s https://gemma4-comp.onrender.com/api/health
curl.exe -s https://duecare-ai.com/api/health
```

If the deployed version does not expose a commit/version, say that explicitly. Do not invent a version match.

If the deploy is stale, do not try to redeploy. Record it as a human/Render-dashboard issue.

### T0.2 Refresh writeup_draft.md

Goal:
- Make the writeup current.
- Keep it under 1500 words.
- Make the story judge-facing, not internal.
- Include the strongest current live evidence:
  - schema hierarchy
  - pack registry
  - 4 example packs
  - local KB
  - hub client protocol
  - server-automation rename
  - knowledge-pack filtering if implemented
  - 19 hub tests if still true after running them
  - Render public coordination hub
  - Kaggle core + appendix separation
- Use "Privacy is non-negotiable."
- Avoid overclaiming unpublished or unverified work.
- Do not add raw PII.
- Do not make the 77-notebook research pipeline sound like the main submission.

Validation:
```powershell
python - <<'PY'
from pathlib import Path
text = Path("docs/writeup_draft.md").read_text(encoding="utf-8")
words = text.split()
print(len(words))
raise SystemExit(0 if len(words) <= 1500 else 1)
PY
```

Also run the relevant docs checks if present. If no docs checker exists, say so.

Commit:
- Subject: `docs: refresh competition writeup`
- Body: explain why the writeup changed for judge clarity and current live scope.

### T0.3 Build or verify `/knowledge-packs` filter UI

First inspect:
- `apps/duecare-ai.com/app/templates/knowledge-packs.html`
- `apps/duecare-ai.com/app/templates/packages.html`
- `apps/duecare-ai.com/app/main.py`
- `apps/duecare-ai.com/app/packs.py`
- `apps/duecare-ai.com/tests/test_app.py`

Expected UI:
- Filter sidebar similar to `packages.html`
- Filter groups populated from API response metadata:
  - `available_kinds`
  - `available_corridors`
  - `available_jurisdictions`
  - tags/status if available
- Query endpoint:
  - `/api/hub/packs?kind=&jurisdiction=&corridor=&tag=&status_=`
- Result cards:
  - readable title
  - kind
  - jurisdiction/corridor
  - status
  - tags
  - whole-card link to `/api/hub/packs/{id}`
- Empty state:
  - clear and helpful
- Failure state:
  - clear and nontechnical
- Privacy copy:
  - no implication that raw case data goes to Render

Validation:
```powershell
$env:DUECARE_DATA_DIR = "$PWD\.duecare-smoke"
python -m pytest -q apps/duecare-ai.com/tests/
```

Smoke check locally:
```powershell
python -m uvicorn app.main:app --app-dir apps/duecare-ai.com --host 127.0.0.1 --port 8000
```

Then verify:
```powershell
curl.exe -s http://127.0.0.1:8000/api/health
curl.exe -s "http://127.0.0.1:8000/api/hub/packs"
curl.exe -s "http://127.0.0.1:8000/api/hub/packs?kind=rag"
```

Use a browser or TestClient render check for `/knowledge-packs`.

Commit:
- Subject: `hub: add knowledge-pack filters`

### T0.4 Confirm `/contribute` end-to-end

Inspect:
- `apps/duecare-ai.com/app/templates/contribute.html`
- `apps/duecare-ai.com/app/main.py`
- `apps/duecare-ai.com/app/storage.py` or the active store module
- tests that cover update proposals

Run local app and submit a safe synthetic public-source proposal. Use only invented/composite, non-PII text.

Verify:
- HTTP 202 response
- JSONL line appended under the smoke data dir
- no raw PII
- page gives visible feedback

If it already works and no code change is needed, do not commit. Record proof in handoff.

If it fails, fix with a focused commit:
- Subject: `hub: fix contribute proposal submit`

## Tier 1 execution order

Do not begin until Tier 0 is done or explicitly blocked.

### T1.1 Heading hierarchy and accessibility sweep

Inspect the files listed in `docs/GPT55_HANDOFF_EXECUTION_PROMPT.md` for T1.1.

Minimum changes:
- Add or verify global `:focus-visible`.
- Convert clickable `div`/cards with JS navigation into semantic links or buttons.
- Ensure heading levels do not skip from `h1` to `h3`.
- Ensure form controls have labels.
- Ensure buttons have accessible names.
- Do not destroy current visual design.

Validation:
- hub tests
- render checks for touched templates
- manual browser smoke for at least the changed pages

Commit:
- Subject: `hub: improve template accessibility`

### T1.2 Wheel `index.html` deeper chrome integration

Inspect:
- `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css`
- `packages/duecare-llm-chat/src/duecare/chat/static/index.html`

Goal:
- Move per-layer accent colors from inline hardcoded hex to existing CSS variables:
  - `var(--accent-persona)`
  - `var(--accent-grep)`
  - `var(--accent-rag)`
  - `var(--accent-tools)`
  - `var(--accent-online)`
  - any existing equivalent variables
- Do not rewrite layout.
- Do not remove the inline `<style>` block.
- Do not apply Kaggle saved-output HTML restrictions to this browser app.

Validation:
- grep changed file for stale hardcoded layer hex values
- if browser app tests exist, run them
- otherwise do a static sanity check and record no browser-app test exists

Commit:
- Subject: `wheel: align playground accents with chrome`

### T1.3 Apply small punch-list quick wins

Only apply quick wins that are:
- low risk
- clearly verified
- one concept per commit
- directly tied to judge clarity, design consistency, or deployment clarity

Examples:
- stale notebook count wording
- stale "3 hackathon notebooks"
- 76 vs 77 research pipeline wording
- stale core/appendix labels
- Render hub vs old Ollama Render topology confusion
- README repo-layout drift

Validation:
- grep for the stale phrase after the edit
- run docs/notebook validation if available
- do not edit generated docs by hand if a generator owns them

Commit subjects:
- `docs: align notebook surface wording`
- `docs: clarify Render hub boundary`
- `docs: separate competition and skunkworks surfaces`

## Required baseline and validation commands

Before first code edit:
```powershell
$env:DUECARE_DATA_DIR = "$PWD\.duecare-smoke"
python -m pytest -q apps/duecare-ai.com/tests/
```

After hub/app changes:
```powershell
$env:DUECARE_DATA_DIR = "$PWD\.duecare-smoke"
python -m pytest -q apps/duecare-ai.com/tests/
python -m compileall apps/duecare-ai.com/app
```

After notebook/doc path changes:
```powershell
python scripts/validate_notebooks.py
python -m pytest -q tests/test_kaggle_notebook_utils.py
```

After Python script changes:
```powershell
python -m compileall scripts
```

Before every commit:
```powershell
git diff --check
git diff --stat
git status --short
```

After every commit:
```powershell
git status --short
git log -1 --oneline
```

Push only after tests pass:
```powershell
git push origin master
```

## Commit discipline

One commit per coherent change.

Good:
- `docs: refresh competition writeup`
- `hub: add knowledge-pack filters`
- `hub: improve template accessibility`
- `wheel: align playground accents with chrome`
- `docs: align notebook surface wording`

Bad:
- `fix stuff`
- `updates`
- one mega-commit containing writeup, UI, notebook docs, and wheel CSS

Each commit body must explain the why:
- judge clarity
- privacy boundary
- Render compatibility
- rubric alignment
- reproducibility

Do not commit unrelated modified files. If a file was already modified by the user and you did not intentionally edit it, leave it out of your commit.

## Required self-check before claiming any Tier item is done

For each completed item, answer internally:

1. What files did I read?
2. What exact defect did I fix?
3. What test or smoke check proves it?
4. What did `git diff --check` say?
5. What commit contains it?
6. Did I push it?
7. Did I avoid raw PII?
8. Did I preserve aliases/backward compatibility?

If any answer is missing, the item is not done.

## Stop conditions

Stop and hand back if:
- tests fail and two focused fix attempts fail
- a route/env rename would break compatibility
- a user-modified file must be overwritten to proceed
- Render deploy is stale and requires dashboard intervention
- Kaggle publishing is required
- a decision affects repo organization in a nontrivial way, such as moving `legacy_notebooks`
- Tier 0 and Tier 1 are complete
- you hit your time budget

If stopping due to failure, revert your partial edit unless the human explicitly asked to keep it.

## Final handoff format

Use exactly this structure:

```markdown
# Claude Code execution handoff

## Commits pushed
- `<hash>` `<subject>`
- ...

## Tier 0 status
- T0.1 deploy verification: <verified / stale / not exposed / blocked> — evidence:
- T0.2 writeup refresh: <done / not done> — word count:
- T0.3 knowledge-pack filters: <done / already present / blocked> — evidence:
- T0.4 contribute end-to-end: <done / already working / blocked> — evidence:

## Tier 1 status
- T1.1 a11y sweep: <done / partial / not started> — files:
- T1.2 wheel chrome integration: <done / partial / not started> — files:
- T1.3 quick wins: <done / partial / not started> — count:

## Tests and smoke checks
- Hub tests:
- Notebook validation:
- Compile checks:
- Browser/TestClient checks:
- Live deploy checks:

## Files intentionally not touched
- `_reference/`
- `apps/duecare-ai.com/app/data/demo_priority_examples.json` unless intentionally changed:
- Tier 2 deferred items:

## Blockers or human decisions
- ...

## Next recommended step
- ...
```

No vague language. No unsupported claims. If something was not verified, say so.
