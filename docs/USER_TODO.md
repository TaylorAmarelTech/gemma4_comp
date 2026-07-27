# Owner-Only Action Checklist

Current as of 2026-07-27.

This page contains only actions that cannot be truthfully completed through a
local repository edit. The authoritative details and acceptance tests are in
[`DEFERRED_WORK.md`](DEFERRED_WORK.md); the matching item ID is shown for every
action below.

## Before Any Model Caller Resumes

- [ ] Privately reconcile provider usage from the last owner-verified receipt
  through the current cost-stop receipt. Retain billing and account details
  outside Git and record only the date, reviewer role, provider category, and
  discrepancy count. (`provider-usage-reconciliation`)
- [ ] Approve a finite run plan with immutable model IDs, maximum attempts,
  input/output token caps, cash cap, stop conditions, and a unique run ID.
  (`bounded-model-smoke`, `per-dimension-judging`, or
  `optional-kaggle-reruns`)
- [ ] Remove no sentinel and enable no scheduled task until the approved run is
  ready; restore the whole-stack cost stop immediately afterward.

## Release Disposition

- [ ] By the 2026-08-22 decision window, choose one outcome: a bounded release,
  a dated no-release deferral, or maintenance mode. Record the effective date,
  supported surfaces, security intake posture, and excluded claims in
  [`PROJECT_TRANSITION_PLAN.md`](PROJECT_TRANSITION_PLAN.md).
  (`release-disposition`)
- [ ] If a Python package will be published, select one manifest row and one
  exact package-specific tag. Let the sole trusted-publisher workflow perform
  the production write; do not use a direct credential upload.
  (`first-package-publication`)
- [ ] If a Kaggle notebook is rerun or published, require a distinct evidence
  purpose, preserve the output bundle, and reconcile its state in
  [`kaggle/_INDEX.md`](../kaggle/_INDEX.md). The current repository closeout
  does not require an additional notebook. (`optional-kaggle-reruns`)

The active source inventory remains exactly:

- `kaggle/01-duecare-exploration-workbench/`
- `kaggle/02-live-demo/`
- `kaggle/A-00-omni-experiment-workbench/`

The `03` and `04` benchmark surfaces are optional; notebook-era appendix
surfaces remain archived provenance.

## Dataset And Evaluation Review

- [ ] Assign two independent curators and the required native-language review
  capacity for the 75-row corridor workbook. Approve source rights and immutable
  snapshots before writing content. (`corridor-curation`)
- [ ] After curation passes, approve the refreshed append-only training
  provenance record. Do not rewrite the older planned-run evidence.
  (`training-provenance-refresh`)
- [ ] Recruit qualified domain reviewers for a human gold set and agreement
  study; record consent, role, rubric revision, and disagreement procedure
  privately where identities are sensitive. (`human-gold-calibration`)

## Private Access Transfer

- [ ] Name the authorized successor or private maintenance owner.
- [ ] Transfer GitHub, Kaggle, hosting, domain, package-registry, model-provider,
  monitoring, mailbox, billing-visibility, recovery, and revocation authority
  one platform at a time using
  [`PRIVATE_TRANSFER_RECEIPT_TEMPLATE.md`](PRIVATE_TRANSFER_RECEIPT_TEMPLATE.md).
- [ ] Verify least-privilege login, recovery, audit visibility, and revocation
  before removing outgoing access. (`private-platform-transfer`)

## Final Acceptance

- [ ] From a fresh shell on the exact final revision, run the
  [successor rehearsal](SUCCESSOR_REHEARSAL.md) and retain the ignored receipt.
- [ ] Confirm public website and GitHub Pages deployments show the same release
  disposition and deferred-work boundary as the repository.
- [ ] Confirm the final branch is merged, required checks are green, `master`
  matches its remote, and the local worktree is clean.

Unchecked boxes are genuine human or owner gates, not documentation
placeholders. Repository maintainers should not mark them complete without the
dated evidence specified in [`DEFERRED_WORK.md`](DEFERRED_WORK.md).
