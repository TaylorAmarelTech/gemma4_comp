# A-16 — Knowledge-pack builder + verifier

<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher, 05 Developer / integration partner

## What it does

Builds versioned, content-hashed knowledge packs from public-source
URLs and files. Each pack carries a `manifest.json` with curator
metadata + a sha256 hash over content. A verifier step simulates
the researcher pull-and-verify path so a reviewer can see end-to-end
reproducibility.

Closes the "researcher reproducibility" gap — the website's
`knowledge-packs.html` + `client-connect.html` mechanics.

## Pipeline

1. Accept a list of public-source URLs / files for a corridor pack
   via the dashboard.
2. Build a versioned pack manifest with content + curator metadata.
3. Sign the pack with a deterministic content_hash (sha256 over
   content + manifest).
4. Verify pack pull: simulate a researcher running
   `duecare-cli pack pull <slug>@<version>` and verify the hash
   matches the signed manifest.
5. Emit `<pack_slug>-v<version>.tar.gz` + signed manifest entries
   in the v1.0 bundle.

## Inputs

- **GPU:** NOT required (CPU-only pack assembly)
- **Internet:** ON (public-source URL fetch)
- **Kaggle Datasets:** wheels dataset
- **Upload:** list of public-source URLs / small files via the
  dashboard's `<input type="file">` (PRIMARY input, not an
  upstream-bundle handoff)
- **Secrets:** none

## Outputs

To `/kaggle/working/`:

- `<RUN>_bundle.zip` — v1.0 envelope with `summary` + per-pack
  `results[]` (+ legacy `packs_built[]` alias). Each row carries
  `slug + version` as the primary key plus the pack `content_hash`.
- `<RUN>_results.json` / `<RUN>_run.jsonl` / `<RUN>_metadata.json`
- `<pack_slug>-v<version>.tar.gz` — one per built pack (the
  reviewer-pullable artifact)
- `RUN_ID` format: `a16_pack_session_{ts}`
  (e.g., `a16_pack_session_2026-05-12T19-30-00Z`)

The dashboard exposes `<a id="bundle-link">` populated via
`fetch('/api/state')` once a pack-session completes.

## Where this slot lives

- **Canonical role:** A-16 knowledge-pack builder + verifier
- **Folder path:** `kaggle/A-17-knowledge-pack-builder/`
- **Kernel ID:** `a-16-knowledge-pack-builder`
- **Downstream:** built packs are consumed by every harnessed
  kernel that loads packs via `duecare.publishing.packs.load(...)`.
  The pack manifest shape matches the website's `/api/packs/{slug}`
  endpoint shape so a partner can submit + retrieve packs through
  the same envelope.

See `docs/appendix_experiment_ladder.md` for the full ladder spec.
