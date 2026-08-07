# GitHub Support request — purge frozen `refs/pull/*` after a credential rewrite

**Status: drafted 2026-08-07, not yet sent.** Sending it requires the
repository owner's authenticated GitHub account, so it cannot be automated.

**Priority: low.** Both credentials were revoked at their providers on
2026-08-05. What remains in the frozen refs are dead strings. Send this when
convenient; nothing is at risk while it waits.

## Why this is needed

`git filter-repo` rewrote every branch and tag in
`TaylorAmarelTech/gemma4_comp`, and the rewritten history was force-pushed on
2026-08-07. That removed both credentials from every ref the repository owner
can write.

GitHub additionally maintains one read-only `refs/pull/N/head` ref per pull
request. These are not writable by the owner — not by `git push`, not by the
REST or GraphQL API. All 17 of this repository's PR refs descend from the
2026-05-01 commit that introduced the credentials, so a single command still
recovers both values from the public repository:

```bash
git fetch origin 'refs/pull/*:refs/remotes/origin/pr/*'
```

Only GitHub Support can remove those refs and the cached by-SHA commit views.

## Where to send it

<https://support.github.com/request> — category **Account or repository
data**, or reply to any existing thread. Send from the account that owns the
repository.

## Draft message

> **Subject:** Purge stale commits from `refs/pull/*` and cached views after a
> credential history rewrite — TaylorAmarelTech/gemma4_comp
>
> Hello,
>
> I own the public repository `TaylorAmarelTech/gemma4_comp`. Two credentials —
> a Google API key and a Hugging Face token — were committed on 2026-05-01 and
> stayed in history until this month. Both have been revoked at their
> providers, so this is cleanup rather than an active incident.
>
> On 2026-08-07 I rewrote history with `git filter-repo` and force-pushed the
> result to every branch and the one tag. Those refs are clean.
>
> The pre-rewrite commits are still reachable through the read-only
> `refs/pull/N/head` refs for pull requests #1 through #17, which I cannot
> rewrite or delete myself. `git fetch origin 'refs/pull/*:refs/remotes/origin/pr/*'`
> on a fresh clone still returns the original credential strings. Old commit
> SHAs are presumably also still viewable through cached commit URLs.
>
> Could you please purge the stale pre-rewrite commits from this repository —
> the `refs/pull/*` refs and any cached commit views — so that only the
> rewritten history remains reachable?
>
> The repository has no forks. I understand the pull requests themselves may
> lose their diffs as a result, and that is acceptable.
>
> Thank you,
> Taylor Amarel

## After GitHub confirms

Re-run the probe on a fresh clone; it should return nothing:

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp.git verify-clone
cd verify-clone
git fetch origin 'refs/pull/*:refs/remotes/origin/pr/*'
git log --all --oneline -S'<google-key-prefix>' | wc -l   # expect 0
git log --all --oneline -S'<hf-token-prefix>'   | wc -l   # expect 0
```

Then update the residue section of
[`CREDENTIAL_HISTORY_PURGE.md`](CREDENTIAL_HISTORY_PURGE.md) and the status
row in the root `SECURITY.md` to record the date GitHub completed the purge.
Do not mark either document complete before that verification passes — the
2026-08-05 receipt claimed a completed purge that had not actually reached the
remote, and this file exists partly to avoid repeating that.
