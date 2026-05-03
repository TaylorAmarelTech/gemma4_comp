# Post-submission sustainability — what happens after 5/18

> **What this is.** The plan for keeping Duecare alive, useful, and
> growing after the 2026-05-18 hackathon submission lands. Whether
> Duecare wins $0 or $50K, the project continues — these are the
> commitments and the trajectory.
>
> **Generated:** 2026-05-02. Refreshed at T+30, T+90, T+180, T+365.
>
> **Audience.** Future first deployers, future contributors, NGO
> partners deciding whether to bet on this tool, and (in 12 months)
> future-Taylor figuring out what to prioritize next.

## The commitment in one sentence

**Whether or not the hackathon wins prize money, Duecare ships v1.0
in 2026 Q4 with first-deployer feedback baked in.** The hackathon
was the forcing function for v0.1.0; sustainability is what makes
the next 12 months matter.

## Phase 0 — submission week (5/18 → 5/25)

The first 7 days post-submit: **rest, observe, respond.**

| Day | Action |
|---|---|
| 5/18 | Submit. Take the rest of the day off. |
| 5/19 | Re-check that submission appears in Kaggle leaderboard / submission listing. |
| 5/20 | Open feedback intake on GitHub. Post one "submitted" tweet. |
| 5/21 | Watch GitHub stars / issue traffic. Respond to any judge or peer questions within 24h. |
| 5/22 | Author a "what we learned in 16 days" reflection post (saved to `docs/post_submission_reflection.md` — drafted post-event, not now). |
| 5/23 | Reach out to 3 NGOs from the press kit list. Send one personal email each with a link to the persona walkthrough most relevant to them. |
| 5/24 | Triage any incoming bug reports. Bump v0.1.1 if anything is broken for first deployers. |
| 5/25 | Take stock — what was the highest-signal piece of feedback? |

## Phase 1 — month 1 (5/25 → 6/25)

The first 30 days: **convert hackathon-driven attention into first
real deployers.**

### Goals

- **3 first deployers** across 3 different personas (NGO director +
  IT director + caseworker, ideally)
- **5 returned `first_deployer_feedback.md` forms** — informs the v0.2
  scope
- **HF Hub fine-tune model has ≥ 50 downloads** (ideally from research
  affiliations, not just the author)
- **GitHub repo has ≥ 50 stars** (rough proxy for "people noticed")
- **0 open P0 / security issues**

### Concrete deliverables

- [ ] Move `docs/post_submission_reflection.md` into the docs site
- [ ] First-deployer feedback compiled into `docs/deployer_feedback_2026Q3.md`
      (anonymized + thematic)
- [ ] v0.2.0 scoping doc at `docs/v0.2_scoping.md` based on the
      feedback
- [ ] First post-submission HF Hub model: a corridor-specific
      fine-tune (e.g., E4B-MX-US-H2A) if the demand exists in
      first-deployer feedback
- [ ] One academic / NGO blog post citing Duecare (not
      author-authored — earned media)

### What I (Claude / AI) can keep doing autonomously

These are autonomy-friendly and don't require user input:

- Refresh `docs/index.md` weekly with new GitHub Release notes
- Cross-reference new GREP rule additions into both Android +
  Kaggle notebooks
- Update `docs/comparison_to_alternatives.md` as competitors release
  new versions
- Add new corridor entries to `DomainKnowledge.kt` as the user
  surfaces them in real cases
- Run `make adversarial` weekly to catch regressions
- Build readiness rubric updates monthly (this dashboard)

### What only the user can do

- Reach out to NGO partners (no AI substitute for trust-building)
- Make the GitHub Pages site more visible (Twitter / LinkedIn / press)
- File any sensitive bug reports privately with NGO partners
- Decide if v0.2 should be "another corridor add" vs "language
  localization" vs "audio input" — judgement call that depends on
  what feedback says

## Phase 2 — month 2-3 (6/25 → 8/25)

The next 60 days: **ship v0.2.0 with first-deployer feedback baked
in. Set up a sustainable cadence.**

### Goals

- **v0.2.0 ships with 3+ feedback-driven changes**
- **First Android v0.10 with localized chat UI strings** (es + tl as
  the first 2)
- **First open-source contribution from someone who is not the
  author** — could be a corridor addition, a translation review, a
  Helm values override, or a doc fix
- **Cross-NGO trends federation aggregator: choose hosting model.**
  Decision: ILO/Polaris/ASI hosted vs self-hosted reference impl
- **One conference talk or workshop accepted** (Strange Loop / RWOT /
  PyCon / Asia-Pacific tech-for-good / FAccT)
- **One academic-style preprint** at `docs/papers/duecare_arxiv_v1.md`
  (research-grade writeup of the 5-tier rubric system)

### Concrete deliverables

- [ ] v0.2.0 release with feedback-driven changes
- [ ] v0.10 Android APK with es + tl localized chat UI strings
- [ ] Federation aggregator design v2 (post-decision)
- [ ] arXiv preprint draft (rubric system as the technical contribution)
- [ ] Conference submission (≥1)

## Phase 3 — quarter 2 (8/25 → 11/25)

The next 90 days: **prove sustainability through compounding adoption.**

### Goals

- **10+ first deployers** across NGOs and enterprises
- **5+ academic citations** (non-author)
- **Federation aggregator: deployed somewhere** (even if it's just
  a single-org reference deployment)
- **v0.5.0 with the 5 most-requested feedback items shipped**
- **First trust-and-safety enterprise pilot signed** (could be a
  paid pilot to fund infrastructure; or a pro-bono pilot with a
  big T&S vendor that wants to test on-device LLM safety)
- **Localized worker-self-help in 5+ languages with native review**
- **Live first-deployer feedback case studies** at
  `docs/case_studies/<persona>_<month>.md`

### v1.0 scope decision

By 2026-09-30, decide v1.0 scope based on:
- Which deployer types are over-represented (concentrate there)
- Which corridors generate ≥ 5 cases per month
- Which compliance gaps remain blocking enterprise adoption
- Which Gemma 4 model sizes have proven most valuable in real use

## Phase 4 — quarter 3-4 (11/25 → 5/27)

The next 180 days: **ship Duecare v1.0.**

### Goals

- **v1.0 ships with full SemVer commitment per package** (post v1.0,
  no breaking changes without a major version bump)
- **Sustainable funding model identified** — options:
  - Grants (Open Tech Fund, Mozilla, Ford, MacArthur)
  - Enterprise pilots with revenue share to NGOs (ethical commercial
    backbone)
  - University research partnership (Berkeley CITRIS / Oxford / LSE
    Migration Studies)
  - Donations / GitHub Sponsors (least sustainable; keep small)
- **Independent security audit completed** (one of: NCC Group,
  Trail of Bits, ISE, or pro-bono via Defensive Lab Agency)
- **Independent UX research with 10+ OFW participants** (real users,
  not composites — paid for their time, IRB-approved)
- **Annual transparency report** at `docs/transparency_2027.md`

## Sustainability principles (non-negotiables)

These are the project's "can't break this" commitments through every
post-submission decision:

1. **Privacy is non-negotiable.** Same phrase from the rules. No PII
   in git, logs, artifacts, federation, model weights — ever.
2. **MIT license + public source.** No commercial fork happens without
   the same code being upstream. No proprietary closed extensions.
3. **NGOs come first.** When commercial enterprise interest conflicts
   with NGO needs, NGOs win. Concretely: if a T&S vendor asks for a
   feature that would be net-negative for an NGO worker (like
   per-tenant usage tracking that could leak), the answer is no.
4. **Real, not faked.** The discipline that landed v0.1.0 — every
   number reproducible from a git SHA + dataset version — continues
   for v1.0. CI gates this; PRs that introduce non-reproducible
   numbers don't merge.
5. **First deployer feedback shapes the roadmap, not the maintainer's
   curiosity.** The maintainer can build interesting tech (e.g., a
   multimodal graph PoC) but not at the expense of the next P0
   feedback request from a real deployer.
6. **The Android app stays free + open + reproducible from the
   GitHub repo.** No app-store-only paid tiers. No telemetry by
   default.
7. **Cross-NGO data sharing requires Ed25519 + differential
   privacy.** No exceptions. No "trust me, this is anonymized."
8. **Gemma 4 is the on-device baseline for v1.0.** Future versions
   may add other model families; Gemma 4 stays as the on-device
   reference because of its size + license + community.

## Failure modes to prevent

Things that have killed similar projects, that this plan explicitly
guards against:

| Failure | Guard |
|---|---|
| Maintainer burnout | "Take the rest of the day off" on 5/18; "rest, observe, respond" first week; explicit deferral of stretch work in `two_week_submission_plan.md` |
| Feature drift away from NGOs | Sustainability principle #3 — written down + revisited at each release |
| Closed enterprise fork | MIT + sustainability principle #2 — no contribution requires CLA assignment to a single org |
| Stale doc site | MkDocs site auto-deploys on every push to master; no maintenance burden |
| Stale corpus | `make adversarial` runs weekly + hookable into CI; `python scripts/validate_notebooks.py` gates PRs |
| Single-person bus factor | Sustainability principle #5 — second contributor target by Phase 2 |
| Over-engineering after submission ("now I have time…") | Roadmap is feedback-driven, not curiosity-driven |
| Privacy regression | Pre-commit hooks + Anonymizer hard gate + audit log + CI checks; never weakened |
| Missing v1.0 deadline | v1.0 has scope flexibility; the 2026 Q4 commitment is a *commitment to ship*, not to ship a fixed feature set |

## Decision triggers — when to do what

Some decisions wait on signals from the world. Here's what triggers
what:

| Signal | Decision |
|---|---|
| ≥ 5 NGOs ask for the same corridor | Add it |
| ≥ 3 NGOs ask for the same language | Localize UI strings + native-review the worker doc |
| ≥ 1 enterprise asks for a feature that conflicts with NGO needs | Decline, document the request publicly with reasoning |
| ≥ 1 enterprise asks for a feature that doesn't conflict with NGO needs | Build it as a values-overridable Helm option |
| Government regulator asks to integrate with their system | Build the integration as an open-source connector, not a private one |
| ILO / Polaris / ASI offers to host the federation aggregator | Accept; use that as the canonical aggregator |
| Academic asks for a research partnership | Accept if it produces a public preprint; decline if it produces only proprietary results |
| Major Gemma 4 release (E8B or v5) | Add to model picker; don't replace v4 default until ≥ 6 months of community validation |
| Catastrophic security finding | Patch within 7 days; coordinated disclosure per `SECURITY.md` |

## How this doc gets refreshed

| Cadence | Who | What |
|---|---|---|
| Weekly | (script) | Auto-update GitHub stars + HF model downloads + open issue count |
| Monthly | Maintainer | Review goals; mark hit / missed; note pivots |
| Quarterly | Maintainer | Quarter-end retro; refresh phase deliverables |
| Annually | Maintainer | "Where Duecare is going" public post; refresh sustainability principles only if external context demands it (e.g., new privacy regulation requires updated guard) |

The doc is meant to evolve. The principles are not.

---

## See also

- [`docs/readiness_dashboard.md`](readiness_dashboard.md) — pre-submit dashboard
- [`docs/persona_readiness_audit.md`](persona_readiness_audit.md) — per-persona happy path
- [`docs/submission_gate_checklist.md`](submission_gate_checklist.md) — pre-Submit checklist
- [`docs/first_deployer_feedback.md`](first_deployer_feedback.md) — feedback intake template
- [`docs/two_week_submission_plan.md`](two_week_submission_plan.md) — pre-submit day-by-day
- [`docs/cross_ngo_trends_federation.md`](cross_ngo_trends_federation.md) — federation roadmap
- [`SECURITY.md`](../SECURITY.md) — security-relevant findings
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — how to contribute
