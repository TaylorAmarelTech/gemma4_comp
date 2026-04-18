# Intelligent verification, fallback paths, and phantom-problem resolution

You are working in `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.

This prompt is not a task list. It is a decision framework for any
time you think something is broken. Use it before writing new code,
before "fixing" metadata, before republishing anything to Kaggle.
Most of the work in this project over the past week chased phantom
problems. This prompt exists to prevent that from happening again.

## Core principle: measure before you fix

A fix without a verified measurement is a guess. A guess that
modifies metadata, rewrites files, or republishes to a live service
can cause real damage. Before any fix, produce one piece of
measurable evidence that the problem exists.

## The phantom-problem detection protocol

Before treating any observation as a real problem, run these four
checks in order. If any check fails, the problem is probably
phantom and you should stop, not escalate.

### Check 1. Is the measurement tool itself correct?

Every observation comes through a tool: a verifier script, a
publish report, a test output, a grep result. Before trusting the
observation, verify the tool is correct.

Known false-signal patterns in this repo:

| Tool or signal | False-signal cause | Correct measurement |
|---|---|---|
| HTTP HEAD on Kaggle URLs | Kaggle returns 404 to HEAD | Use GET with Mozilla user-agent, inspect body for soft-404 markers |
| User-agent "DueCareVerifier" | Kaggle rejects unknown UAs | Use `Mozilla/5.0 ... Chrome/120` |
| `kaggle kernels push` stdout | Charmap decode errors on Windows can hide success | Set `$env:PYTHONIOENCODING = "utf-8"` first |
| `kaggle kernels status` | Status reads wrong id when title-derived slug differs from stored id | Read the live slug from `kaggle kernels list --user taylorsamarel` first |
| `docs/review/notebook_publish_report.md` | Frozen snapshot from a specific date; may not reflect current state | Rerun verifier and regenerate the report |
| `requests.head(url, timeout=10)` | Returns 404 from Kaggle | Use `urllib.request` with GET and browser UA |
| `pytest` reporting "all pass" | Tests may not cover the failing scenario | Grep for the specific assertion that would catch the bug |

When a new tool is added to the repo, treat it like untested code.
Before using its output, test the tool against a case you already
know the answer to. If it disagrees with ground truth, the tool is
wrong, not the system.

### Check 2. Does at least one other independent source confirm?

One tool saying something is broken is a hypothesis. Two
independent tools saying the same thing is evidence. Three is
usually a real problem.

For Kaggle URLs specifically, confirm with all three before
treating a URL as dead:

1. `scripts/verify_kaggle_urls.py` (GET + Mozilla UA, body check).
2. Manual curl: `curl -A "Mozilla/5.0" -I <url>` then `curl -A "Mozilla/5.0" <url> | head`.
3. Open the URL in a real browser.

If all three show 404, the URL is dead. If one shows 404 and two
show 200, the one is broken.

### Check 3. Is the observation consistent with what just succeeded?

If `publish_kaggle.py push-notebooks` reported 7 successes and 21
failures, but `kaggle kernels list` shows 29 kernels live, the
publish parser is wrong, not Kaggle. Trust the downstream
measurement over the upstream one.

If a test was green 5 minutes ago and is red now, and you did not
change the code, the environment changed (credentials cleared,
working directory moved, file locked). Check that first.

### Check 4. Does the proposed fix make sense for the root cause?

If the fix is "add more metadata fields", "rewrite the aligner",
"regenerate all notebooks", "rebuild the builder scripts", ask:
what specific observation proves that the absence of these fields
or the current form of these files caused the failure? If you
cannot cite one, the fix is speculative and will probably create
new drift.

## Known ground truth (as of 2026-04-15, update this as it changes)

All 29 notebooks are live on Kaggle:

- Verifier: `python scripts/verify_kaggle_urls.py` exits 0.
- Count: 29 kernel directories, 29 local mirror notebooks, 29
  Kaggle URLs resolving at HTTP 200 with browser user-agent.
- Published by the last authenticated publish pass.

Do not "republish to fix" unless a specific Kaggle URL renders
broken content in a browser, AND the fix for that one notebook is
a targeted `kaggle kernels push -p <dir>` for that kernel only.

Do not relabel URLs as "pending republish" based on any publish
report. The publish report is a snapshot, the verifier is live
ground truth.

## Fallback paths for the six most likely failure modes

For each failure mode below, the prompt tells you (a) what the
false-signal pattern looks like, (b) how to distinguish false from
real, (c) what to do if the problem is real.

### Failure mode 1. A Kaggle URL appears dead

**False signal.** Verifier prints `FAIL 404 <url>`.

**Distinguish.** Run all three checks from protocol step 2:
- Rerun the verifier to rule out network flake.
- Run `curl -A "Mozilla/5.0 ... Chrome/120" <url> -o /tmp/page.html && wc -l /tmp/page.html`. A real Kaggle notebook page is thousands of lines. A 404 page is tens.
- Open in a browser.

**Real problem.** If all three confirm 404, the kernel was deleted
or never existed. Push that one kernel specifically:
`kaggle kernels push -p kaggle/kernels/<dir>`. Do NOT touch the
other 28.

### Failure mode 2. `publish_kaggle.py push-notebooks` reports failures

**False signal.** Output contains `400 Bad Request`, `409 Conflict`,
`404 Not Found`, or `charmap decode`.

**Distinguish.** Ignore the parser output. Instead, run
`scripts/verify_kaggle_urls.py` ten minutes later (Kaggle takes
time to process pushes). If the URL resolves, the push succeeded
despite the error message.

**Real problem.** If the URL still 404s after 10 minutes AND a
browser confirms 404, the push actually failed. Common real causes:

- Notebook too large (>20 MB). Trim the mega-cell notebooks: 310,
  600, 410 have 7000+ line cells per the earlier audit.
- Kaggle dataset reference is wrong. Check `dataset_sources` in
  metadata.
- Title collides with another kernel the user owns. Check
  `kaggle kernels list --user taylorsamarel` for duplicates.

### Failure mode 3. Metadata says X but Kaggle says Y

**False signal.** `kernel-metadata.json` has `id` of
`taylorsamarel/duecare-gemma-exploration` but the live URL uses
`duecare-real-gemma-4-on-50-trafficking-prompts`.

**Distinguish.** Both can be true. Kaggle remembers the original
slug forever. Pushing under a new id with a matching title creates
a new kernel; pushing under the old id updates the existing one.

**Real problem.** Only a problem if the id is wrong AND pushing
that id causes a 400. Fix by setting id to the slug Kaggle already
knows, which is the one in `kaggle kernels list` output.

### Failure mode 4. A test fails after "working" changes

**False signal.** Pytest reports a specific test failure that did
not exist before a metadata or notebook edit.

**Distinguish.** Run `git diff` for the last commit. If the test
failure points to data the test asserts about (directory names,
kernel ids, title prefixes), the test is checking the old world,
not the code.

**Real problem.** If the test asserts about behavior (a function
returning the wrong value, an integration returning an error), it
is real. Fix the code, not the test.

### Failure mode 5. Kaggle CLI can't authenticate

**False signal.** `auth-check` exits non-zero.

**Distinguish.** Check three places:

- `~/.kaggle/kaggle.json` exists and has `username` and `key`.
- `KAGGLE_USERNAME` and `KAGGLE_KEY` env vars.
- `KAGGLE_CONFIG_DIR` points somewhere with a kaggle.json.

**Real problem.** Token expired. Visit
https://www.kaggle.com/settings/account, create new token, save to
`C:\Users\amare\.kaggle\kaggle.json`.

### Failure mode 6. Notebook JSON is "invalid" per validator

**False signal.** Validator reports "metadata.language missing" or
"cell ids malformed" on a notebook that renders fine.

**Distinguish.** Open the notebook in VS Code or Jupyter. If it
renders and runs, the validator is too strict. Relax the validator.
If it fails to render, the JSON is genuinely malformed.

**Real problem.** Run
`python scripts/normalize_notebook_metadata.py <path>` to repair
structure without changing content.

## Stop conditions (do not exceed these)

Stop and ask the user before doing any of these:

- Republishing more than 2 kernels in one session.
- Rewriting more than 3 builder scripts in one session.
- Creating new scripts whose job is to verify something already
  verifiable with an existing script.
- "Regenerating all notebooks" unless a specific builder has
  changed.
- Deleting a kernel directory or a live Kaggle kernel.
- Modifying `docs/review/*.md` to make them less accurate (for
  example, labeling a live URL as "pending" without running the
  verifier first).
- Adding fields to `kernel-metadata.json` unless the Kaggle API
  documented them as required for a specific feature.

Stop and report to the user when any of these are true:

- Three tools disagree about the state of the same thing.
- A fix attempt increases the number of failures.
- Credentials are needed but not on disk.
- You have been working for 30+ minutes without a verifiable
  state improvement.

## The 60-second sanity check (run this before every session)

```
python scripts/verify_kaggle_urls.py | tail -3
```

Expected output on a healthy repo:

```
All 29 notebooks resolve.
```

If it does not say that, the verifier itself may be broken (most
common) or a real kernel is down (rare). Diagnose the verifier
first. Do not touch metadata until the verifier is confirmed
correct.

## The 10-minute incremental loop

When working a real problem, stay in this loop:

1. State the one specific thing you believe is broken, in one
   sentence, with a file path or URL.
2. Run one measurement that would confirm or refute it.
3. If confirmed, make one minimal change.
4. Rerun the same measurement.
5. If the measurement is now green, commit. If not, revert the
   change and go back to step 1.

Do not batch. Do not "while I am here also fix X". Do not "let me
also add Y." The phantom-problem loop in this repo started every
time the fix grew beyond the measurement.

## Specific guidance for the remaining hackathon days

The suite is already live. The 2026-05-18 deadline is approaching.
The remaining high-value work is:

1. **Writeup**: `docs/writeup_draft.md`. Target <= 1500 words.
2. **Video**: `docs/video_script.md`. Record 3 minutes.
3. **Demo**: The HF Spaces deployment is live. Verify once it
   still loads in a browser.

Every Kaggle notebook task is lower priority than the above. If a
specific notebook has an obvious rendering bug when a judge opens
it, fix that one notebook. Otherwise, leave them alone.

## What to do when you think this prompt is wrong

If your own measurement says the ground truth stated here is
outdated (for example, a kernel really did go dark), update the
"Known ground truth" section with the new verified state, cite the
measurement, and then proceed. Do not silently act on a belief
that contradicts this prompt.
