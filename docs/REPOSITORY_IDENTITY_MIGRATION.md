# Repository identity migration — rename, or replace with a clean repository

**Status: drafted 2026-08-07. Non-destructive half executed 2026-08-08.
Nothing public has changed. Do not execute the remainder during grading.**

On 2026-08-08 the continuation repository `TaylorAmarelTech/duecare` was
created **private**, and the full 1,732-commit history was pushed to it with
explicit refspecs. A fresh clone of it verified 0 `refs/pull/*` refs and 0
usable credentials, so the residue described in
[`security/CREDENTIAL_HISTORY_PURGE.md`](security/CREDENTIAL_HISTORY_PURGE.md)
does not exist there.

**This repository was not modified by that work.** `gemma4_comp` was not
renamed, archived, deprecated, or redirected. It remains the live public
repository the frozen Kaggle writeup points judges at, and it stays that way
until the owner confirms grading is complete. The publication steps — making
`duecare` public, enabling its Pages site, re-pointing the Kaggle kernels, and
archiving this repository behind a pointer README — are all still pending and
are deliberately not done.

This document is gated on the same event as
[`POST_COMPETITION_HOSTING_TRANSITION.md`](POST_COMPETITION_HOSTING_TRANSITION.md):
the owner confirming that Gemma 4 Good grading is complete. It covers a
different concern — the *identity and history* of the source repository, not
where the website is hosted.

## Why anyone would want this

Two goals get bundled together in the phrase "clean repo with a new name."
They are separable, they have different costs, and only one of them is
actually pressing.

| Goal | What it means | Solved by |
|---|---|---|
| **Better name** | `gemma4_comp` is a hackathon-artifact name. The product is DueCare. | A rename |
| **Clean history** | Both revoked credentials remain fetchable through GitHub's frozen `refs/pull/*` refs (see [`security/CREDENTIAL_HISTORY_PURGE.md`](security/CREDENTIAL_HISTORY_PURGE.md)) | A fresh repository, **or** a GitHub Support request |

A rename does **not** clean history — the PR refs travel with the repository.
A fresh repository does **not** require a rename, but it is the only way to
resolve the `refs/pull/*` residue without depending on GitHub Support.

## The hard constraint: do not touch this before results

The Kaggle writeup was submitted and is **frozen**. It points judges at
`github.com/TaylorAmarelTech/gemma4_comp`, and the competition awards 30 points
for Technical Depth & Execution *as verified by the code repository*.

- A 404 at that URL is a direct scoring loss.
- An **Archived** banner reads as "abandoned" to a reviewer who does not know
  the backstory.

Neither is worth trading for tidiness. Both goals below survive waiting.

## Measured inventory (2026-08-07)

What actually pins the current name, counted rather than guessed:

| Surface | Count / state | Breaks on a fresh repo? |
|---|---|---|
| Tracked files naming `gemma4_comp` | **314** | Mechanical `sed`; most are `docs/` and archives |
| Active Kaggle kernels installing from the repo | **3** kernels, 9 refs, via `DUECARE_REPO` env default | Yes — each needs a re-push |
| Kaggle writeup link | Frozen, unchangeable | Yes — mitigated by archiving, not deleting |
| GitHub Pages docs URL | `tayloramareltech.github.io/gemma4_comp/` — derived from repo name | Yes, on **either** path |
| Helm repo URL | Same Pages host | Yes, on either path |
| CI workflows | Use `github.repository` context; only comments name the repo | No — portable as written |
| **PyPI** | **Not published** (all three package JSON APIs return 404) | No — no immutable external metadata pins the URL |
| Hugging Face adapter repo | Live; model card references the repo | Card edit, cheap |
| Stars / forks / watchers | **4 / 0 / 0** | 4 stars lost; nothing else |
| Repository size | 306 MB (`seed_prompts.jsonl` alone trips GitHub's 50 MB warning three times) | An opportunity — see below |

The absence of published PyPI packages is the single most important line in
that table. Published package metadata is immutable and would have pinned the
old URL forever. It does not exist, so migration is far cheaper than it looks.

## Path A — rename in place

```bash
gh repo rename duecare --repo TaylorAmarelTech/gemma4_comp
```

- GitHub redirects old web and git URLs to the new name, indefinitely, for
  clone, fetch, and push.
- Stars, issues, pull requests, and history are preserved.
- **Cost:** the Pages URL changes to `tayloramareltech.github.io/duecare/`.
  Documentation links and the Helm repo URL must be updated. Redirects for
  Pages are less dependable than for git.
- **Does not** remove the `refs/pull/*` residue.
- **Risk:** if anyone later creates a repository named `gemma4_comp` under the
  same account, the redirect breaks permanently.

## Path B — fresh repository, archive the old one (recommended)

This is the option that does real work: it produces a repository whose history
has never contained the credentials, in any ref, cached or otherwise.

```bash
# 1. Create the new repository (private first — verify before exposing).
gh repo create TaylorAmarelTech/duecare --private \
  --description "DueCare — an agentic LLM safety harness for migrant-worker exploitation"

# 2. Push the already-purged history. No PR refs, no cached SHAs come with it.
git remote add duecare https://github.com/TaylorAmarelTech/duecare.git
git push duecare master:master
git push duecare --tags

# 3. Prove it is clean before making it public.
git ls-remote duecare
#    Then, on a fresh clone of the new repo:
#    git fetch origin 'refs/pull/*:refs/remotes/origin/pr/*'   -> returns nothing
#    git log --all -S'<key-prefix>' | wc -l                    -> 0
```

Then, and only then:

4. Update the 314 tracked references, the 3 Kaggle kernel `DUECARE_REPO`
   defaults, the docs Pages URL, the Helm repo URL, and the HF model card.
5. Re-push the 3 active Kaggle kernels so their installs resolve.
6. Make `duecare` public.
7. **Archive — do not delete — `gemma4_comp`**, with its README replaced by a
   pointer to the new repository.

Archiving matters: an archived repository stays fully readable and clonable,
so the frozen Kaggle writeup link keeps resolving and lands a reader on a clear
signpost. Deleting it would break that link permanently, along with every
external permalink ever shared.

### What Path B also fixes

- Makes [`security/GITHUB_SUPPORT_REQUEST.md`](security/GITHUB_SUPPORT_REQUEST.md)
  unnecessary for the *new* repository — it starts clean by construction. (Send
  it anyway if the archived repository should also be scrubbed.)
- Offers a natural moment to move `configs/duecare/domains/trafficking/seed_prompts.jsonl`
  (57–63 MB across revisions) to Git LFS or a Kaggle dataset, cutting the
  306 MB clone. Do this as a deliberate, separately verified change — not
  silently during the migration, or the "file content is byte-identical"
  guarantee from the purge is lost.

## Recommendation

Wait for results. Then take **Path B**, named `duecare`, archiving the old
repository with a pointer README.

Path A is tempting because it is one command, but it buys the cosmetic half of
the problem and leaves the substantive half — and it still breaks the Pages
URL, which is most of Path B's link work anyway. If the Pages URL must change
regardless, take the option that also produces genuinely clean history.

If neither goal feels worth the work after results are in: **do nothing.** The
credentials are revoked, the residue is inert, and a working repository that
judges have already visited has real value. "Deprecate and replace" is a
preference, not a remediation.

## Do not

- Do not execute any part of this while grading is open.
- Do not delete `gemma4_comp` under any circumstance — archive it.
- Do not rename and create a fresh repository under the old name; that breaks
  the rename redirect.
- Do not bundle the LFS/large-file change into the same operation as the
  identity change.
- Do not push `refs/backup/*` to any remote. Those refs hold the original
  unpurged history.

## Acceptance gate

- [ ] competition grading completion is owner-confirmed;
- [ ] the new repository's history is verified clean on a fresh clone,
      including `refs/pull/*`;
- [ ] all 3 active Kaggle kernels install and boot from the new URL;
- [ ] the docs Pages site and Helm repo URL resolve at their new addresses;
- [ ] `gemma4_comp` is archived, readable, and carries a pointer README;
- [ ] `python scripts/validate_public_surface.py` and
      `python scripts/check_external_links.py --check` pass against the new
      URLs.
