# Owner Decision Ledger

Current as of 2026-07-28.

The repository owner delegated the bounded closeout decisions. All 11 inherited
items now have a dated disposition in the canonical
[closeout resolution receipt](CLOSEOUT_RESOLUTIONS_2026_07_28.md), and the
[deferred-work register](DEFERRED_WORK.md) contains zero current items.

Checked here means **the decision or current maintenance cycle is recorded**.
It does not mean a declined model run, package publication, Kaggle rerun,
private transfer, training-data admission, or human study was performed.

## Final Dispositions

- [x] Historical provider usage closed with explicit retained risk. The local
  repository cannot reconstruct the pre-ledger interval and does not claim
  zero usage. (`provider-usage-reconciliation`)
- [x] Private platform and recovery authority retained by the current owner.
  No successor transfer or access revocation is claimed.
  (`private-platform-transfer`)
- [x] Maintenance mode enacted on 2026-07-28 while Render, the independent
  continuity site, MkDocs Pages, source, and existing research artifacts stay
  available. (`release-disposition`)
- [x] First PyPI package publication explicitly declined for closeout. No tag
  or registry write was created. (`first-package-publication`)
- [x] The 75-row corridor expansion closed at zero admitted rows and is
  excluded from training claims because rights, snapshots, native-language
  review, and two-person adjudication do not exist. (`corridor-curation`)
- [x] Training provenance refresh declined for unchanged candidate data; the
  strict quality/provenance lane intentionally remains red.
  (`training-provenance-refresh`)
- [x] Kimi K3 and Meta Muse Spark 1.1 availability/pricing recorded without a
  model call; the paid smoke was declined to preserve credits.
  (`bounded-model-smoke`)
- [x] Exhaustive per-dimension judging stopped as low-value partial experimental
  work and remains isolated from the default board. (`per-dimension-judging`)
- [x] Optional Kaggle reruns declined because no named evidence gap justified
  quota use. Canceled and inaccessible kernels were not relabeled as successful.
  (`optional-kaggle-reruns`)
- [x] The 364-item human-review packet is validated, but the unperformed study
  is excluded from human-agreement and field-effectiveness claims.
  (`human-gold-calibration`)
- [x] The 2026-07-28 source-freshness cycle completed; the next scheduled review
  is 2026-10-28 or earlier if a volatile fact changes.
  (`source-freshness-maintenance`)

## Standing Owner Controls

These are controls, not currently overdue tasks:

- Keep all five recurring tasks disabled, all four stop sentinels present, and
  planned model calls at zero during deterministic maintenance.
- Keep private credentials, billing details, reviewer identities, recovery
  material, and access receipts outside Git.
- Use [`PRIVATE_TRANSFER_RECEIPT_TEMPLATE.md`](PRIVATE_TRANSFER_RECEIPT_TEMPLATE.md)
  only if a named successor is later authorized and accepts access.
- Reopen work in `configs/duecare/deferred_work.json` only after a specific
  reopen condition in the dated receipt is met.
- Reverify provider IDs, access, context, modalities, and prices immediately
  before any future Kimi K3 or Meta Muse Spark 1.1 run.
- Rerun the [successor rehearsal](SUCCESSOR_REHEARSAL.md) on the exact revision
  whenever maintenance ownership changes.

No owner response is needed to close the current queue.

## Active Kaggle Source Boundary

Maintenance preserves exactly these primary source surfaces without requiring
a quota-consuming rerun:

- `kaggle/01-duecare-exploration-workbench/`
- `kaggle/02-live-demo/`
- `kaggle/A-00-omni-experiment-workbench/`

Optional `03` and `04` benchmark surfaces remain outside the primary recording
path, and notebook-era appendix material remains archived provenance.
