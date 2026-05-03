# Submission gate checklist — pre-flight before clicking Submit

> **What this is.** The single screen you walk through immediately
> before clicking the Submit button on the Kaggle competition page.
>
> **When to use.** ~24 hours before submission window closes (not
> on 5/18 itself — leave buffer for one fix cycle).
>
> **How to use.** Open this doc + a fresh browser tab + the Kaggle
> competition page. Walk every checkbox. Do not skip. Do not
> "trust me, I checked yesterday." Re-verify each one *now*.
>
> **If anything fails:** fix it, then restart the checklist from the
> top.

## Phase 1 — Kaggle competition page state (5 min)

- [ ] You are signed in to the Kaggle account that will hold the submission
- [ ] The hackathon competition page loads + you can see your team
- [ ] The "Submit" button is visible (deadline has not passed)
- [ ] Your submission has not been auto-saved with stale content
- [ ] You can read the official rules + submission requirements one
      more time, fresh — they sometimes get clarified mid-window

## Phase 2 — Code repo state (10 min)

- [ ] `git status` is clean on master (no uncommitted local changes)
- [ ] `git log -5` shows the latest commits are the ones you intend
      (no in-progress experimental commits at HEAD)
- [ ] `git tag -l` includes `v0.1.0` pointing at the submission SHA
- [ ] `git push --tags` succeeded — the v0.1.0 tag is on GitHub
- [ ] The GitHub repo is **public** (settings → General → Danger zone
      → "Change visibility" — verify it says "Make this repo private",
      meaning it is currently public)
- [ ] LICENSE file is MIT and at the repo root
- [ ] README leads with `make demo` + judge entry points
- [ ] [`docs/FOR_JUDGES.md`](FOR_JUDGES.md) is up to date with all
      11 notebook URLs, the HF Space URL, and the APK download URL
- [ ] `_reference/` is `.gitignore`d (it must NOT be in the public
      repo — proprietary)
- [ ] `data/`, `models/`, `logs/`, `checkpoints/` are `.gitignore`d
      (large binaries should not be in git)
- [ ] No real PII anywhere — search: `gitleaks detect --redact`
- [ ] CI on the latest master commit is **green** (Actions tab)
- [ ] CITATION.cff parses (GitHub shows "Cite this repository" button
      on repo home)
- [ ] CHANGELOG.md has an entry for v0.1.0

## Phase 3 — PyPI packages (5 min)

For each of the 17 packages:

- [ ] `pip install duecare-llm==0.1.0` (the meta package) succeeds in
      a fresh venv
- [ ] `pip show duecare-llm-core duecare-llm-models duecare-llm-chat
      duecare-llm-domains duecare-llm-tasks duecare-llm-benchmark
      duecare-llm-training duecare-llm-agents duecare-llm-workflows
      duecare-llm-publishing duecare-llm-cli duecare-llm-engine
      duecare-llm-evidence-db duecare-llm-nl2sql duecare-llm-research-tools
      duecare-llm-server` shows v0.1.0 for all 16
- [ ] `python -c "from duecare.cli import main; print('ok')"` succeeds
- [ ] `python -c "from duecare.core import Model, Task; print('ok')"` succeeds
- [ ] `duecare --version` returns 0.1.0

## Phase 4 — Kaggle notebooks (15 min)

For each of the 11 notebooks (6 core + 5 appendix):

- [ ] The notebook URL on Kaggle resolves (not 404, not "Notebook not found")
- [ ] The notebook is **public** (not private)
- [ ] The notebook is **runnable** (Run All button is present, not
      blocked by required-account-permissions)
- [ ] The wheels dataset attached is the v0.1.0 dataset (not a stale one)
- [ ] The first cell installs from the wheels dataset (not from PyPI),
      so the notebook works even when PyPI is rate-limited
- [ ] The README inside the notebook attributes Gemma 4 by name
- [ ] The Gemma 4 model variant is documented in the first cell
- [ ] The output cells are saved (the saved-output viewer shows results,
      not "Run this notebook to see output")

The 11 to verify:

| # | Notebook | URL |
|---|---|---|
| 1 | duecare-chat-playground | https://www.kaggle.com/code/taylorsamarel/duecare-gemma-chat-playground |
| 2 | duecare-chat-playground-with-grep-rag-tools | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools |
| 3 | duecare-content-classification-playground | https://www.kaggle.com/code/taylorsamarel/duecare-content-classification-playground |
| 4 | duecare-content-knowledge-builder-playground | https://www.kaggle.com/code/taylorsamarel/duecare-content-knowledge-builder-playground |
| 5 | duecare-gemma-content-classification-evaluation | https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation |
| 6 | duecare-live-demo | https://www.kaggle.com/code/taylorsamarel/duecare-live-demo |
| A1 | duecare-prompt-generation | https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation |
| A2 | duecare-bench-and-tune | https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune |
| A3 | duecare-research-graphs | https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs |
| A4 | duecare-chat-playground-with-agentic-research | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-agentic-research |
| A5 | duecare-chat-playground-jailbroken-models | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-jailbroken-models |

> ⚠️ **Per memory:** Kaggle derives slugs from notebook titles, not
> metadata. If a slug 404s, it's likely renamed locally vs the live
> notebook. Verify against `verify_kaggle_urls.py` output, not against
> `kernel-metadata.json`.

## Phase 5 — Hugging Face Hub (5 min)

- [ ] `taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0`
      resolves (or — if A2 didn't run — explicitly say so in the
      writeup; do not link a 404)
- [ ] The model card has: model description + intended use + training
      data summary + license + Gemma 4 attribution + reproducibility
      SHA
- [ ] The HF Space [`taylorscottamarel/duecare-live`](https://huggingface.co/spaces/taylorscottamarel/duecare-live)
      is **running** (not "sleeping" — wake it up if needed by
      visiting the URL)
- [ ] The HF Space matches the v0.1.0 wheels (not a stale build)

## Phase 6 — Android APK (3 min)

- [ ] The latest GitHub Release is `v0.9.0-twenty-corridors-new-rules`
      (or whatever you tagged for the submission window)
- [ ] The release page has a `.apk` artifact attached
- [ ] The direct `.apk` URL works (test in a browser; downloads, not 404)
- [ ] The APK SHA-256 matches the value in the release notes
- [ ] The release notes mention Gemma 4 + on-device + cloud routing +
      20 corridors + 42 GREP rules

## Phase 7 — Live demo (2 min)

- [ ] The HF Space (or wherever the live demo is hosted) loads
- [ ] You can submit one example prompt and get a response within 30s
- [ ] The response cites at least one GREP rule + ILO indicator (the
      headline differentiation vs raw Gemma 4)

## Phase 8 — Documentation site (3 min)

- [ ] The MkDocs site at https://tayloramareltech.github.io/gemma4_comp/
      loads
- [ ] The "Try in 2 minutes" page works (links resolve)
- [ ] Search works (search "kafala" returns hits)
- [ ] Mermaid diagrams render (visit the ecosystem overview page;
      the diagrams should be SVG, not "loading...")

## Phase 9 — The video (5 min)

> The video is the highest-leverage submission asset. Verify it
> *carefully*.

- [ ] The video file exists + is exported as MP4
- [ ] Duration is ≤ 3:00 (Kaggle hard cap)
- [ ] Video is uploaded to a **public** YouTube URL (not private,
      not unlisted)
- [ ] You can play it in an incognito window (verifies it's truly
      public)
- [ ] The video opens with a named composite character (Maria) — see
      `marias_case_end_to_end.md`
- [ ] The video closes with a named NGO (Polaris / IJM / ECPAT /
      POEA / BP2MI / HRD Nepal) — verifies real-world impact
- [ ] The phrase "privacy is non-negotiable" appears in the voice-over
      (per `00_overarching_goals.md` rule 5)
- [ ] Gemma 4 is attributed by name in voice-over OR on screen
- [ ] At least one of {function calling, multimodal} is shown as
      load-bearing, not decorative
- [ ] The video URL is captioned in the writeup
- [ ] You watched the video end-to-end *today* (not "I watched it
      yesterday") in the same browser you'll submit from

## Phase 10 — The writeup (5 min)

- [ ] Word count ≤ 1,500 (Kaggle hard cap)
- [ ] Every URL in the writeup resolves (open each one — do NOT just
      skim)
- [ ] Every number in the writeup is reproducible from `(git_sha,
      dataset_version)` — see `harness_lift_report.md`
- [ ] The writeup links to: GitHub repo + 11 notebook URLs + HF Hub
      model + HF Space + Android APK + video
- [ ] The writeup mentions Gemma 4 attribution + license + intended use
- [ ] The writeup names: 1 composite worker, 3+ NGO partners, 3+ ILO
      indicators, 3+ corridors
- [ ] No raw PII anywhere

## Phase 11 — One last paranoid check (3 min)

- [ ] Open an incognito browser window — the GitHub repo loads, the
      11 notebook URLs load, the HF Space loads, the APK downloads,
      the video plays. (Catches "I'm signed in so it works for me but
      a judge would 403.")
- [ ] The Kaggle competition deadline timer agrees with your local
      timezone calculation. (Catches timezone confusion.)
- [ ] You are about to submit ≥ 24 hours before the deadline.
      (Catches "I'm too tired to fix one bug at the last minute.")

## Phase 12 — Submit

- [ ] Click Submit
- [ ] Take a screenshot of the confirmation page
- [ ] Save the screenshot to `docs/media/submission_confirmation.png`
- [ ] Push the screenshot in a "submitted" commit
- [ ] Tag that commit `v0.1.0-submitted`
- [ ] Push the tag

## Phase 13 — Post-submit (24 hours)

- [ ] Open one feedback intake (issue) on GitHub for first-deployer
      reports: `[first-deployer] template`
- [ ] Tweet / post the submission with one screenshot + the live HF
      Space URL (only if you do social — skip if not)
- [ ] Drop a "what's next" post pointing to
      `docs/post_submission_sustainability.md`

---

## If anything fails

| Failure | Action |
|---|---|
| Kaggle notebook 404 | Push the notebook OR delete the orphan slug per `feedback_kaggle_orphan_slugs.md` and re-push |
| HF Space sleeping | Visit the URL — first request wakes it; wait 30s + retry |
| HF Hub model 404 | Either run A2 NOW (if T-24h is enough) OR remove the link from the writeup and explicitly say "fine-tune is a follow-up" |
| Video URL 403 | Re-set YouTube visibility to Public + re-test in incognito |
| Writeup over 1,500 words | Cut from the "Future work" section first; it's the lowest-impact section |
| Live demo crashed | Re-deploy: `make redeploy` to HF Space; failing that, point the demo URL at the Android APK + a Kaggle notebook |
| GitHub Pages 404 | Re-run the docs-deploy workflow manually from Actions tab |
| `make demo` broken from fresh clone | Fix the regression; do not submit until `make demo` succeeds on a clean machine |

## What NOT to do in the last 24 hours

- ❌ Do not refactor anything
- ❌ Do not bump dependency versions
- ❌ Do not "just one more feature"
- ❌ Do not delete files because they "look messy"
- ❌ Do not git push --force
- ❌ Do not change the Kaggle notebook URLs (judges may have already loaded them)
- ❌ Do not unpublish a notebook (even a "broken" one — leave it; the writeup can flag it as a known issue)

The last 24 hours are for **verification + submission**, not for
shipping new work. If something is bad enough that it must be fixed,
fix only that one thing, then restart this checklist from Phase 1.

---

## See also

- [`docs/readiness_dashboard.md`](readiness_dashboard.md) — single-screen status across all dimensions
- [`docs/notebook_qa_companion.md`](notebook_qa_companion.md) — per-notebook test plan
- [`docs/two_week_submission_plan.md`](two_week_submission_plan.md) — day-by-day plan for the 16-day window
- [`docs/post_submission_sustainability.md`](post_submission_sustainability.md) — what happens after Submit
