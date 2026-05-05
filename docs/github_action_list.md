# GitHub action list — what only you can do

> Updates on actions only you (Taylor) can take in the GitHub web UI.
> Most are one-time settings; a few are recurring.
>
> **Generated:** 2026-05-03. Refresh after each settings pass.

## P0 — blocks docs site from updating (1 action)

### 1. Enable GitHub Pages → "GitHub Actions" source

**Status:** ❌ Not yet enabled. Last 2 deploy attempts (2026-05-02 8cd804ec, 2026-05-03 0a33dab) failed with `404 Not Found / Ensure GitHub Pages has been enabled`.

**What to do (~30 seconds):**
1. Open https://github.com/TaylorAmarelTech/gemma4_comp/settings/pages
2. Under **Build and deployment** → **Source** dropdown
3. Select **GitHub Actions** (not "Deploy from a branch")
4. Save (auto-saves)

**Verify:**
- Open https://github.com/TaylorAmarelTech/gemma4_comp/actions
- Find the most-recent failed "Deploy docs site" run
- Click "Re-run all jobs"
- After it completes (~2 min), https://tayloramareltech.github.io/gemma4_comp/ should load

## P1 — improves submission completeness (3 actions)

### 2. Verify CI is green on the latest pushed commit

**Status:** ⚠️ Latest push (633119d, 2026-05-03) — verify all workflows green.

**What to do (~1 minute):**
1. Open https://github.com/TaylorAmarelTech/gemma4_comp/actions?query=branch%3Amaster
2. Find the most-recent workflow run (top of the list)
3. Confirm green checkmarks for: ci, gitleaks scan, harness-lift gate, build-wheels, cleanroom, notebooks
4. If anything is red: click in, read the failure, decide whether to fix-forward or revert

**If the deploy docs site is still red after enabling Pages:** that's a separate failure mode worth investigating, not a Pages config issue.

### 3. Confirm the repo is public

**Status:** Should be public per CLAUDE.md, but verify.

**What to do (~30 seconds):**
1. Open https://github.com/TaylorAmarelTech/gemma4_comp/settings
2. Scroll to **Danger Zone** at the bottom
3. The "Change repository visibility" button should say **Make this repository private** (which means it IS currently public — the button shows the OPPOSITE of current state)

**Why:** Hackathon judges + first deployers need to be able to clone without authentication. Private = submission-blocking.

### 4. Tag v0.1.0 once submission is final

**Status:** Pending — wait until you've recorded the video and pushed all notebooks.

**What to do:**
```bash
git tag -a v0.1.0 -m "Hackathon submission 2026-05-18"
git push origin v0.1.0
```
Then on GitHub:
1. Open https://github.com/TaylorAmarelTech/gemma4_comp/releases/new
2. Choose tag `v0.1.0`
3. Title: "v0.1.0 — Gemma 4 Good Hackathon submission"
4. Body: copy from `CHANGELOG.md` v0.1.0 section
5. Attach a screenshot of the Kaggle submission confirmation
6. Publish release

## P2 — nice to have (3 actions)

### 5. Add a GitHub Sponsors button (post-submission)

**Status:** Not enabled. Worth doing post-5/18 to capture any inbound interest.

**What to do (~2 minutes):**
1. Open https://github.com/TaylorAmarelTech/gemma4_comp/settings
2. Under "Features" → check "Sponsorships"
3. Set up a `.github/FUNDING.yml` (we don't ship one yet) — add `github: TaylorAmarelTech` line

### 6. Pin the repo on your profile

**Status:** Helps for visibility during judge review.

**What to do (~30 seconds):**
1. Open https://github.com/TaylorAmarelTech (your profile)
2. Click "Customize your pins"
3. Pin `gemma4_comp` (and `duecare-journey-android`)

### 7. Set up issue templates

**Status:** Currently no templates; first-deployer feedback uses a free-form issue.

**What to do (~5 minutes, post-submission):**
1. Create `.github/ISSUE_TEMPLATE/` folder
2. Add `first-deployer-feedback.md` (copy from `docs/first_deployer_feedback.md`)
3. Add `bug_report.md` and `feature_request.md` (use GitHub's defaults)

## Recurring (after submission)

### 8. Watch + triage incoming issues

**Cadence:** Weekly first month; bi-weekly after.

**What to do:**
1. Open https://github.com/TaylorAmarelTech/gemma4_comp/issues
2. For each new issue: label it (`bug` / `enhancement` / `docs` / `first-deployer-feedback`), respond within 72h per `docs/first_deployer_feedback.md`
3. P0 fixes ship within 7 days

### 9. Review PRs (when contributors arrive)

**Cadence:** Per PR.

**What to do:**
1. Open the PR
2. Run the CI checks
3. Review the diff (use `@claude` PR review action — already wired in `.github/workflows/claude.yml`)
4. Merge or request changes

## Other repos (sibling Android repo)

### 10. duecare-journey-android — verify v0.9.0 release is published

**Status:** v0.9.0-twenty-corridors-new-rules — verify the GitHub Release is created (not just the tag).

**What to do:**
1. Open https://github.com/TaylorAmarelTech/duecare-journey-android/releases
2. If `v0.9.0-twenty-corridors-new-rules` shows "Latest" badge AND has the `.apk` artifact attached → done
3. If only the tag exists, no release: open https://github.com/TaylorAmarelTech/duecare-journey-android/releases/new, choose the v0.9 tag, attach the APK from the latest CI build artifact, publish

## What's already done in GitHub (for context)

- ✅ Repository created + public
- ✅ MIT LICENSE at root
- ✅ CITATION.cff at root (gives "Cite this repository" button)
- ✅ Issues + Discussions enabled
- ✅ Actions enabled with 7 workflows: ci, claude, docker-publish, docs-deploy, helm-publish, pypi-publish, release
- ✅ Branch protection on master (if set; otherwise consider enabling)
- ✅ Latest commits pushed (5 commits in 2 days, 633119d at HEAD)

---

## See also

- [`docs/notebook_action_list.md`](notebook_action_list.md) — Kaggle notebook test + push actions
- [`docs/submission_gate_checklist.md`](submission_gate_checklist.md) — pre-Submit verification
- [`docs/two_week_submission_plan.md`](two_week_submission_plan.md) — day-by-day plan
- [`docs/post_submission_sustainability.md`](post_submission_sustainability.md) — what happens after 5/18
