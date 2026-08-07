# Security Policy

## Reporting a vulnerability

Found a bug that puts migrant workers at risk? **Please don't open a
public GitHub issue.** Email the author privately:

> **amarel.taylor.s@gmail.com** — subject line `[duecare security]`

Expected response time: 72 hours acknowledgement, 14 days for a
substantive update on remediation.

## Scope — what we consider security-relevant

The Duecare framework is built around a hard PII gate (no raw PII
leaves the local process — see [`.claude/rules/10_safety_gate.md`](./.claude/rules/10_safety_gate.md)).
Bugs in the following classes are treated as security issues, not
ordinary bugs:

| Class | Examples |
|---|---|
| **PII leakage** | A code path that sends raw victim names, passport numbers, phone numbers, financial accounts, or content tagged as "personal" to an external service (HF Hub, Tavily, Brave, Serper, browser tools, telemetry, or server automation) |
| **Bypass of the safety harness** | A prompt or input pattern that causes the harness to silently drop GREP / RAG / Tools / Persona output before Gemma sees it |
| **Audit log gaps** | An outbound network call that bypasses `_audit()` in `fast_search.py`, allowing an outbound query to leave no trace |
| **Credential exposure** | Any code path where `HF_TOKEN`, BYOK keys (Tavily/Brave/Serper), or Kaggle credentials end up in logs / git / wheel artifacts / served HTTP responses |
| **Prompt injection** | An attacker-controlled string that, if pasted into the chat playground, can override the persona / disable harness toggles / extract the system prompt |
| **Wheel supply-chain** | Tampering with `_examples.json` / `_rubrics_*.json` / harness module that ships in the wheel |

## Non-security bugs

Functional bugs (e.g. a GREP rule has a bad regex, the cloudflared
tunnel times out, a notebook cell prints garbled output) are
ordinary bugs — open a regular issue at
[github.com/TaylorAmarelTech/gemma4_comp/issues](https://github.com/TaylorAmarelTech/gemma4_comp/issues).

## Coordinated disclosure

If you've found something that affects migrant workers in production
deployments, we'd appreciate 90 days of coordinated disclosure to give
NGO partners time to update their deployments. Earlier disclosure is
fine if you believe workers are at active risk.

## Past incidents

### Credential exposure in git history — resolved 2026-08-05, remote purge completed 2026-08-07

**Both credentials below have been disabled at their providers and are no
longer valid.** They are recorded here because disclosure is more useful than
quiet deletion.

| | |
|---|---|
| What | A Google API key and a Hugging Face access token |
| Committed | 2026-05-01 |
| Removed from working tree | 2026-05-04 and 2026-05-15 |
| Revoked at the provider | 2026-08-05 — the step that actually resolved the exposure |
| History rewritten locally | 2026-08-05 |
| Purged history propagated to the public remote | 2026-08-07 (every branch and the tag; the 2026-08-05 push did not complete) |
| Status | **Revoked at the provider; strings purged from every branch and tag. Still present in GitHub's frozen `refs/pull/*` refs — see below.** |

Where the two values stood in this repository's history they now read
`REDACTED-GOOGLE-API-KEY-DISABLED-SEE-SECURITY-MD` and
`REDACTED-HF-TOKEN-DISABLED-SEE-SECURITY-MD` — the replacement is
self-documenting, so anyone reading an old commit sees that the credential was
disabled and where to read about it.

**Known remaining exposure, stated plainly:** GitHub freezes a `refs/pull/N/head`
ref for every pull request, and those refs are not writable by the repository
owner. All 17 of this repository's PR refs descend from the 2026-05-01 leak
commit, so both original strings remain fetchable from the public repository
with `git fetch origin 'refs/pull/*:refs/remotes/origin/pr/*'`. Only GitHub
Support can remove them. This is disclosed rather than glossed because **the
credentials are revoked and therefore inert** — a dead key in a frozen ref is a
meaningless string, which is precisely why revocation, not rewriting, was
treated as the remedy.

Removing a secret from the working tree does not remove it from history. Both
values stayed readable to anyone who cloned this public repository for roughly
three months. They were found by a full-history scan, not by the working-tree
scans run previously — a gap worth naming, because a clean `git grep` on HEAD
says nothing about what earlier commits contain.

**What was done, in order of importance:**

1. **Revoked at the provider.** This is the part that actually resolves the
   exposure. Anyone who cloned the repository during those three months still
   holds the strings; only revocation makes them worthless.
2. **Purged from history** with `git filter-repo`, replacing each value with a
   `REDACTED-…-DISABLED-SEE-SECURITY-MD` marker across 1,644 commits. This is
   tidiness rather than security — see
   [`docs/security/CREDENTIAL_HISTORY_PURGE.md`](docs/security/CREDENTIAL_HISTORY_PURGE.md)
   for the procedure and its costs.

**Consequence for anyone verifying this repository:** every commit SHA from
2026-05-01 onward changed. The submission snapshot cited in `RESULTS.md` moved
from `d3ab6588` to `20ccc532`; file content is identical apart from the two
replaced strings. Older clones and forks will not fast-forward and should be
re-cloned.

**Prevention:** `gitleaks` runs in pre-commit and in CI at full history depth,
`.env` is gitignored and was never committed, and
`scripts/validate_legal_hygiene.py` gates the repository on every push. GitHub
secret scanning and push protection were enabled on the repository on
2026-08-07.

## Hall of fame

Contributors who report security bugs are credited in `RESULTS.md`
(unless you'd prefer to remain anonymous).

---

> *"Raw worker chats, IDs, contact details, and private documents stay with the worker or trusted caseworker unless an authorized user creates a sanitized submission."*
