# Runbook — purging exposed credentials from git history

**Status: EXECUTED — rewrite 2026-08-05, remote propagation 2026-08-07.**
This procedure has been run against this repository. It is retained as the
record of what was done, and as a runbook should it ever be needed again.

**Outcome:** both credential strings replaced across 1,644 commits;
full-history occurrences went from **19 to 0**; all 1,727 commits and every
branch and tag preserved; file content otherwise unchanged. The submission
snapshot moved from `d3ab6588` to `20ccc532`, and `RESULTS.md` was updated in
the same operation. A pre-purge mirror backup was taken first.

**Propagation record (2026-08-07):** the 2026-08-05 session rewrote history
locally but its force-push never reached the remote, leaving the public
repository unpurged for two further days while this document already read
"EXECUTED". On 2026-08-07 the purged history was force-pushed to every public
ref — `master`, the four remaining `agent/*` and `codex/*` branches, and the
`ui-polish-2026-05-23` tag — and a fresh full-history scan of the remote
confirmed zero credential occurrences **on every branch and tag**. A complete
bundle backup of the original remote state was retained offline first. The
repository had zero forks at purge time. GitHub secret scanning and push
protection were enabled the same day.

**Measured residue — do not describe the purge as total.** A follow-up probe on
2026-08-07 fetched the frozen `refs/pull/N/head` refs and confirmed that
**both original strings are still fetchable from the public repository**
through them. Every one of the 17 PR refs descends from the 2026-05-01 leak
commit, and GitHub does not let a repository owner rewrite or delete
`refs/pull/*`. One command recovers them:

```bash
git fetch origin 'refs/pull/*:refs/remotes/origin/pr/*'   # still serves both values
```

Only a GitHub Support request can purge those refs and the cached by-SHA commit
views; the request to send is drafted in
[`GITHUB_SUPPORT_REQUEST.md`](GITHUB_SUPPORT_REQUEST.md). The alternative that
does not depend on GitHub at all is migrating to a fresh repository, which
starts clean by construction — see
[`../REPOSITORY_IDENTITY_MIGRATION.md`](../REPOSITORY_IDENTITY_MIGRATION.md),
gated on the end of grading. Because both
credentials were revoked at their providers on 2026-08-05, this residue is
inert and the request is cleanup, not incident response. The lesson
generalises: **a branch-and-tag scan is not a repository-wide scan on a host
that keeps hidden refs.**

## Read this first: rewriting history does not secure a leaked key

This is the part that is commonly backwards. Two credentials were committed on
2026-05-01 and removed from the working tree days later, but they remained
readable in history on a public repository for roughly three months. In that
window:

- anyone who cloned or forked the repository still holds them,
- GitHub retains rewritten commits in the fork network and in cached commit
  views until you separately ask GitHub Support to purge them,
- automated scrapers harvest public commit history continuously.

A purge removes the strings from *your* copy of history. It does not
un-disclose them. **Revocation at the provider is the remedy.** Once revoked,
the strings in history are inert — a revoked key is a meaningless string — and
purging becomes optional tidiness rather than security work.

Do step 1 regardless. Steps 2 onward are optional.

## Step 1 — Revoke (required, ~2 minutes, do this first)

| Credential | Where | Action |
|---|---|---|
| Google API key `AIzaSyCJ3BJk…` | console.cloud.google.com → APIs & Services → Credentials | Delete the key |
| Hugging Face token `hf_xyZWocEk…` | huggingface.co/settings/tokens | Revoke the token |

Neither value is present in the current `.env` or in the current tree, so
revoking breaks nothing in this project. `.env` already carries a different
`HF_TOKEN`.

After revoking, enable **GitHub push protection**
(Settings → Code security → Secret scanning → Push protection). It blocks a
commit containing a recognised credential before it reaches the remote, which
is the control that would have prevented this.

## Step 2 — Understand what a purge costs here

These are measured for this repository, not generic caution.

| Fact | Value |
|---|---|
| Commits in repo | 1,725 |
| Commits rewritten (descendants of `35180e58`) | **1,644 (95%)** |
| Judge-facing submission SHA | `d3ab6588` (2026-05-18) |
| Is that SHA rewritten? | **Yes** — verified descendant of `35180e58` |

`RESULTS.md` names `d3ab6588` as the submission snapshot and instructs readers
to run `git checkout d3ab6588`. A purge changes that SHA, so **`RESULTS.md`
must be updated in the same operation** or the documented verification path
breaks. The same applies to the `(git_sha, dataset_version, model_revision)`
provenance contract in `docs/reproducibility.md`.

Do not run this while anyone is actively verifying the submission against those
SHAs.

## Step 3 — Execute the purge (optional, after revocation)

```bash
# 0. Full backup first. This is not reversible from the remote afterwards.
cd ..
git clone --mirror https://github.com/TaylorAmarelTech/gemma4_comp.git gemma4_comp-backup.git
cd gemma4_comp

# 1. Install the tool (neither filter-repo nor BFG is currently installed)
pip install git-filter-repo

# 2. Write the replacement rules. "literal:" means exact-string match.
#    Put the real values in this file; step 5 deletes it.
cat > ../purge-rules.txt <<'RULES'
literal:<GOOGLE_KEY_VALUE>==>REDACTED-GOOGLE-API-KEY
literal:<HF_TOKEN_VALUE>==>REDACTED-HF-TOKEN
RULES

# 3. Rewrite. --force is required because this repo has a configured remote.
git filter-repo --replace-text ../purge-rules.txt --force

# 4. Verify both strings are gone from every commit (expect 0).
git log --all -p | grep -c "AIzaSyCJ3BJk\|hf_xyZWocEk"

# 5. Remove the rules file — it contains the secrets in plaintext.
rm ../purge-rules.txt
```

Substitute the two real values into step 2 from the audit output; they are
deliberately not written into this tracked file, so that fixing a leak does not
create a fresh one.

## Step 4 — Repair what the rewrite broke

```bash
# filter-repo drops the remote as a safety measure. Re-add it.
git remote add origin https://github.com/TaylorAmarelTech/gemma4_comp.git

# Find the new SHA of the submission-window commit.
git log --until=2026-05-19 -1 --format="%h %ad %s" --date=short
```

Then update **both** references in `RESULTS.md` (the submission-snapshot table
row and the `git checkout` line) to the new SHA, and re-run the gates:

```bash
python scripts/validate_legal_hygiene.py
python scripts/validate_public_surface.py
python -m pytest packages tests -q
```

## Step 5 — Force-push, and the fallout you are accepting

```bash
git push --force --all origin
git push --force --tags origin
```

After this:

- **every existing clone and fork is broken.** Collaborators must re-clone;
  `git pull` will fail or produce a tangled merge.
- open pull requests referencing old SHAs may break.
- old commit SHAs remain reachable through GitHub's cache and fork network. To
  remove those, open a GitHub Support request citing this repository and the
  purged commits.
- any external permalink to a specific commit or line dies.

## Recommendation

Revoke now. Treat the purge as optional cleanup for after judging concludes,
when `d3ab6588` no longer needs to resolve. Revocation is complete security;
the purge is cosmetic once the keys are dead, and it carries all the blast
radius.

## Disclosure note

A public note in `SECURITY.md` recording this exposure should be added **only
after revocation is confirmed**. Publishing it beforehand would point readers
at credentials that still work.
