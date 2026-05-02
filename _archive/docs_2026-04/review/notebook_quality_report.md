# Notebook Quality Report

Date: 2026-04-15

## Scope

This report covers the local hardening and pre-publish validation pass for
the 29 tracked DueCare Kaggle notebooks.

## Completed

- Added a shared notebook hardening utility for standardized pinned install cells, GPU guard cells, summary cells, and stale-text cleanup.
- Improved the `000` index and `010` quickstart builders for judge-facing verification.
- Hardened the generated notebook builders and repaired the manual `600` dashboard notebook pair.
- Added API-key fallback behavior for notebooks that depend on external model APIs.
- Added `scripts/kaggle_live_slug_map.json` to track the currently known live Kaggle slugs.
- Added `scripts/align_kaggle_kernel_metadata.py` so every kernel metadata file can be normalized in one pass.
- Added `scripts/validate_notebooks.py` for non-executing notebook JSON validation.
- Added `scripts/verify_kaggle_urls.py` for post-publish URL probing.
- Added `scripts/normalize_notebook_metadata.py` to repair serialized notebook metadata when needed.

## Current Local Status

- Tracked kernels: 29
- Local mirrors: 29
- Missing mirrors: 0
- Kernel metadata now includes: `id`, `title`, `keywords`, `competition_sources`, public visibility, and the wheels dataset source.
- Builder-owned notebooks have been regenerated and mirror sync is clean.

## Validation Results

- `python scripts/validate_notebooks.py --cpu-only`: pass (`22` CPU notebooks validated)
- `python scripts/publish_kaggle.py --dry-run push-notebooks`: pass (`29` kernels listed)
- `pytest tests/test_kaggle_notebook_utils.py tests/integration/test_publish_kaggle.py -q`: pass (`11` tests)
- `python scripts/generate_kaggle_notebook_inventory.py`: pass

## Important Findings

- The root cause of the earlier Kaggle drift was metadata inconsistency, not notebook logic alone.
- Some already-live Kaggle notebooks must preserve legacy slugs even though their display titles now include improved DueCare naming.
- The `430` notebook now has local metadata that includes the DueCare name, but the public Kaggle title will not update until the correct legacy slug is republished under auth.
- URL resolution is still blocked on a fresh authenticated Kaggle pass; local metadata alignment alone does not make a notebook live.

## Remaining Work

1. Restore Kaggle auth on this machine.
2. Refresh `scripts/kaggle_live_slug_map.json` from `kaggle kernels list --user taylorsamarel --page-size 50 --csv`.
3. Republish the pending kernels using the aligned metadata.
4. Run `python scripts/verify_kaggle_urls.py` after publish and confirm resolvable public URLs.
5. Perform the manual render check for the judge-critical notebooks (`000`, `010`, `100`, `300`, `500`, `600`, `610`).