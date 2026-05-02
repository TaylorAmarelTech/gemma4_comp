# ClaudeCode corrective writing and publish action: post-47-kernel reconciliation

This prompt is for ClaudeCode or GPT-5.4 running inside the DueCare
repo. The job is to reconcile repo truth after recent local notebook
landings, correct stale human-facing docs and shared continuity files,
then publish and verify Kaggle state if credentials are available.

Do not stop at review. Make the edits. If publishing is unblocked, run
the publish path too.

## Who you are

Staff-level engineer and technical writer cleaning a Kaggle hackathon
submission after a partially-completed local build session. Voice:
terse, opinionated, plain English. Use notebook IDs, exact strings,
commands, and file paths when reasoning. Use cell numbers only, never
internal cell IDs. No em dash. No emojis. No filler adjectives.

Today is 2026-04-17. The Kaggle Gemma 4 Good Hackathon is due
2026-05-18.

## Primary objective

The repo has moved ahead of its own writing and publish proof.

Recent local work landed four new notebooks:

1. `170` Live Context Injection Playground
2. `190` RAG Retrieval Inspector
3. `460` Citation Verifier
4. `540` Fine-tune Delta Visualizer

The validator gate reportedly moved from 43 to 47 notebooks, and the
adversarial-validator set reportedly expanded to 13 passing checks.
But a later attempt to prove Kaggle publication was blocked because the
shell had no `KAGGLE_API_TOKEN`, and a partial next-batch wiring pass
introduced forward references to notebooks that have not been proven
landed yet.

Your job is to make the repo stop overstating reality, then publish and
verify the real Kaggle state if auth is available.

## Starting claims to verify, not trust

1. `python scripts/validate_notebooks.py` is green at `47 of 47`.
2. `170`, `190`, `460`, and `540` are real local notebooks with real
   builders and validators.
3. `29` kernels were previously live on Kaggle.
4. `130`, `140`, `150`, `155`, `160`, `170`, `190`, `460`, `540`, and
   the nine section conclusions may still be first-time creation
   candidates rather than live notebooks.
5. `180`, `335`, `620`, and `650` may have been added to shared wiring
   before their notebooks actually landed.
6. `scripts/kaggle_notebook_utils.py` may still hardcode stale URL
   verification text.
7. `docs/project_status.md`, `docs/notebook_guide.md`, checkpoint docs,
   or review docs may still describe the older 42-notebook / 29-live /
   13-pending state.

## Read these first

1. docs/prompts/README.md
2. docs/current_kaggle_notebook_state.md
3. docs/project_status.md
4. docs/notebook_guide.md
5. README.md
6. docs/writeup_draft.md
7. docs/video_script.md
8. docs/prompts/30_project_checkpoint.md
9. docs/prompts/31_project_checkpoint_v2.md
10. docs/review/31e_publish_verify_report.md
11. scripts/notebook_hardening_utils.py
12. scripts/build_index_notebook.py
13. scripts/build_section_conclusion_notebooks.py
14. scripts/kaggle_notebook_utils.py
15. scripts/generate_kaggle_notebook_inventory.py
16. scripts/verify_kaggle_urls.py
17. scripts/push_all_sequential.py
18. scripts/push_all_with_fallback.py
19. scripts/kaggle_live_slug_map.json
20. scripts/build_notebook_170_live_context_injection_playground.py
21. scripts/build_notebook_190_rag_retrieval_inspector.py
22. scripts/build_notebook_460_citation_verifier.py
23. scripts/build_notebook_540_finetune_delta_visualizer.py
24. scripts/_validate_170_adversarial.py
25. scripts/_validate_190_adversarial.py
26. scripts/_validate_460_adversarial.py
27. scripts/_validate_540_adversarial.py

Also search for `180`, `335`, `620`, and `650` across the repo before
you let any shared file keep talking about them as if they are already
part of the published curriculum.

## What to correct

Focus especially on these themes:

1. Repo-truth drift in notebook counts, live counts, and push queues.
2. Partial-batch continuity drift where shared files now reference
   `180`, `335`, `620`, or `650` as if they landed when they may only
   be planned.
3. New-notebook visibility for `170`, `190`, `460`, and `540` in the
   section recaps, status docs, and notebook guide.
4. Publish-script and inventory-helper drift, especially stale prose
   that still says `29 OK, 0 FAIL` or implies only 29 kernels exist.
5. Real Kaggle proof: published, queued, blocked, complete, failed, or
   stale. Do not infer this from metadata alone.
6. Exact next commands if Kaggle auth is missing or the daily cap blocks
   the session.

## Required actions

1. Re-read the current repo truth and determine the exact current state
   of:
   - tracked local kernels
   - green local validators
   - green adversarial validators
   - definitely live Kaggle kernels
   - first-time creation candidates
   - already-live kernels whose local content is newer than Kaggle
2. Fix stale writing in source files, not just generated markdown. At a
   minimum inspect and update any stale claims in:
   - `docs/project_status.md`
   - `docs/notebook_guide.md`
   - `docs/prompts/30_project_checkpoint.md`
   - `docs/prompts/31_project_checkpoint_v2.md`
   - `docs/review/31e_publish_verify_report.md`
   - `scripts/kaggle_notebook_utils.py`
3. Correct shared continuity files that currently overstate unlanded
   notebooks. If `180`, `335`, `620`, or `650` are not yet real tracked
   notebooks with source-of-truth backing, do not leave them as the
   previous notebook, section member, or index entry in reader-facing
   flows.
4. Preserve the valid new landings. `170`, `190`, `460`, and `540`
   should stay wired anywhere they are actually real and validated.
5. Rebuild the artifacts owned by any builder you touched. If you edit
   shared continuity files, rebuild at minimum:
   - `python scripts/build_section_conclusion_notebooks.py`
   - `python scripts/build_index_notebook.py`
   - `python scripts/generate_kaggle_notebook_inventory.py`
6. Re-run validation after the corrective writing pass:
   - `python scripts/validate_notebooks.py`
   - `python scripts/_validate_170_adversarial.py`
   - `python scripts/_validate_190_adversarial.py`
   - `python scripts/_validate_460_adversarial.py`
   - `python scripts/_validate_540_adversarial.py`
7. Check whether `KAGGLE_API_TOKEN` is available in the current shell.
   If it is present, take real publishing action. If it is missing, do
   not fake publication.
8. If Kaggle auth is available:
   - use the safest real push path in the repo
   - if `scripts/push_all_sequential.py` or related tooling is stale,
     correct that first or use a safer targeted push order
   - push the affected queue
   - run `kaggle kernels status` on the newly-created or newly-updated
     kernels most affected by this corrective pass
   - run `python scripts/verify_kaggle_urls.py`
   - regenerate the inventory after the publish attempt
9. If Kaggle auth is missing:
   - complete the corrective writing pass anyway
   - state the blocker as fact, not guesswork
   - leave the exact publish commands for the current queue
10. Create or update `docs/review/34_corrective_writing_and_publish_report.md`
    with these sections only:
    - `Repo truth corrected`
    - `Publish attempts`
    - `Kernel status and URL verification`
    - `Docs refreshed`
    - `Remaining blockers`
    - `Next exact commands`

## Done definition

You are done only when all of these are true:

1. No core repo doc still claims `42` local notebooks if repo truth is
   now `47`.
2. No inventory helper still hardcodes `29 OK, 0 FAIL` as the latest
   public URL verification result.
3. Shared continuity no longer treats `180`, `335`, `620`, or `650` as
   landed unless that is proven by real files and real validation.
4. `170`, `190`, `460`, and `540` are reflected accurately across the
   status docs and section recaps.
5. The inventory has been regenerated from current metadata.
6. The full validator gate is green.
7. The relevant new adversarial validators are green.
8. If Kaggle auth exists, publish attempts and verification results are
   recorded from Kaggle, not guessed.
9. If Kaggle auth is absent, the report states that blocker plainly and
   leaves exact next commands.
10. `docs/review/34_corrective_writing_and_publish_report.md` exists.

## Constraints

1. Prefer source-of-truth edits over manual notebook JSON edits.
2. Do not rename live Kaggle slugs casually.
3. Do not claim a notebook is live just because a metadata id or URL
   exists.
4. Never ask for or print the Kaggle token value. Use the env var only
   if it is already present.
5. Keep scope on corrective writing, continuity truth, and publishing
   proof. Do not resume the `180` / `335` / `620` / `650` build batch
   unless required to repair a concrete false claim.
6. Preserve unrelated user changes outside files you must touch.
7. If the repo and an older checkpoint disagree, trust the repo and fix
   the checkpoint.

## Final response

Return a short execution summary with these sections only:

1. Repo truth corrected
2. Publish result
3. Remaining blockers