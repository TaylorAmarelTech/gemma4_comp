# First-deployer feedback — structured intake template

> **Audience.** You're someone who deployed Duecare somewhere
> real (an NGO office, a clinic, an enterprise pilot, a research
> environment, an Android app on your own phone). Whether the
> experience was great or a disaster, your feedback shapes the
> next release.
>
> **Format.** Open this template in your text editor or as a GitHub
> issue. Fill what you can. Skip what's not relevant. Send it back
> via the mechanism listed at the end.

## Template

Copy from here into your editor / new GitHub issue:

```markdown
---
deployer_role: ""              # NGO director / IT director / lawyer / researcher / etc.
deployment_topology: ""        # A / B / C / D / E (see docs/deployment_topologies.md)
hardware: ""                   # Mac mini M2 / NUC / cloud VM / Android phone / etc.
duecare_version: ""            # git SHA + Android APK version + Helm chart version
weeks_in_use: ""               # 1 / 4 / 12 / 26 / 52
users_supported: ""            # 1 / 5 / 20 / 100 / 1000+
date: ""                       # YYYY-MM-DD
---

## What worked

(What stuck. What stopped you from looking for an alternative.)

-

## What didn't work

(What broke. What you had to work around. What you couldn't figure out.)

-

## What you wish existed

(Features you wanted that aren't there yet. Be specific.)

-

## Setup friction

How long did Day-1 actually take? (vs the documented 90 min budget)

  Estimated:
  Actual:
  Where the time went:

What was the SINGLE biggest friction point on Day 1?

  →

## Operations friction

For an existing deployment, how often have you needed to:

  Restart the stack: ____ / month
  Restore from backup: ____ / quarter
  Re-pull a model: ____ / quarter
  Update via `git pull && make demo`: ____ / month
  Page someone outside your team for help: ____ / quarter

What's the SINGLE most common operational issue?

  →

## User-facing wins

What's the most surprising win a real user reported to you?

  →

What feature do they ASK for that doesn't exist yet?

  →

## User-facing losses

What's the most common user complaint?

  →

What feature do they MIS-USE in a way you didn't expect?

  →

## Doc gaps

Which doc did you wish existed when you needed it?

  →

Which doc was misleading or wrong?

  →

Which doc was longer than it needed to be?

  →

## Decision retrospect

If you had to pick a deployment shape today, knowing what you
know now, would you pick the same one?

  Same: yes / no
  If no, what would you pick instead and why?

If you had to recommend Duecare to a peer in your role, would you?

  Yes — with caveats: ____
  Yes — unreservedly: ____
  No — because: ____
  Maybe — depends on: ____

## Open-ended

Anything else? Rant. Praise. Story. Half-formed thought.

```

## Where to send this

Three options, in order of speed:

1. **GitHub issue** at https://github.com/TaylorAmarelTech/gemma4_comp/issues/new
   — fastest; public; gets a response within 72h. Use the
   "first-deployer-feedback" label if you can.
2. **Email**: `amarel.taylor.s [at] gmail.com`, subject
   `[duecare feedback]` — for things you don't want public.
3. **Encrypted (signal)**: contact via email for the Signal
   handle — for genuinely sensitive material (worker stories,
   security-relevant findings).

## What we do with your feedback

- **Within 72 hours**: acknowledgement + clarifying questions
- **Within 30 days**: visible response, either as a code/doc PR
  citing your feedback or as an issue we've moved into the
  backlog with reasoning
- **Within 90 days**: any P0 / P1 fix that came from your feedback
  ships in the next release; you get a notification
- **At quarterly intervals**: an aggregate "what we learned from
  deployers this quarter" post on the repo

## What's done with your identity

- **GitHub issue**: public — your handle is on the issue. If you
  want to share organizational context but stay personally
  anonymous, file from a project handle.
- **Email**: private to the maintainer. Quoted (with permission +
  attribution) in public posts only with your explicit written OK.
- **Aggregated learnings**: never personally identifiable in
  aggregate posts. Quoted with explicit permission only.

The maintainer doesn't sell, share, or use your contact info for
anything other than responding to your feedback.

## Worker / caseworker safety considerations

If your feedback includes worker case details:

- **Composite the names**: "Worker A" / "the case from intake
  2026-05-02" rather than a real name
- **Generalize the corridor**: "PH-HK domestic-worker" rather than
  a specific employer
- **Strip dates that could re-identify**: month/year is fine;
  exact day usually isn't needed
- **Encrypted if sensitive**: don't email an actionable trafficking
  case in plaintext; use the Signal handle

The maintainer treats every feedback message as confidential by
default. If you want a finding made public (a security issue, a
case study, a research result), explicitly mark it for sharing
in the email subject line.

## Why we ask for this

The walkthroughs in `docs/scenarios/` are written from research +
analogy to peer projects (Tella, MfMW, Polaris). The first real
deployer in each role discovers things the walkthroughs missed.
Your feedback closes that gap for the next deployer in your role.

Specifically, we want to learn:

- Which docs land vs which docs miss
- Which features get used vs which sit dormant
- Which failure modes happen in real environments vs only in
  pre-launch tests
- Which corridors / jurisdictions need extension packs that don't
  exist yet
- Which integration patterns are common enough to add as Helm
  values overrides vs niche enough to leave to operator scripts
- Which support questions repeat enough to need an FAQ entry

The first 10 first-deployer feedback responses become the source
material for v0.8 release prioritization. Your half-hour of
feedback shapes a release that hundreds of future users see.

## See also

- [`docs/scenarios/`](./scenarios/) — the walkthroughs your feedback
  improves
- [`SECURITY.md`](../SECURITY.md) — security-relevant findings have a
  separate path (private disclosure)
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — when you're ready to
  contribute a fix yourself
