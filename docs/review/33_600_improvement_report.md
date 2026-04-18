# 33: Notebook 600 improvement report

## What changed in 600
1. Rebuilt `notebooks/600_results_dashboard.ipynb` and `kaggle/kernels/duecare_600_results_dashboard/600_results_dashboard.ipynb` from `scripts/build_notebook_600_results_dashboard.py` so the checked-in notebook now matches the stronger builder. Before this pass, the builder was already ahead of the emitted JSON.
2. Tightened section 11 in the 600 builder so the engineering boundary is explicit: failure-type classification belongs to `440 Per Prompt Rubric Generator`, while 600 stays focused on measured weak categories and curriculum priority.
3. Replaced the builder's brittle 520 link construction with an explicit canonical `URL_520` constant. The summary now links to 520 directly instead of manufacturing that URL by string replacement from the 530 slug.
4. Fixed direct 600-related continuity drift in `scripts/build_index_notebook.py`. The index no longer understates 600 as “seven interactive Plotly charts”; it now describes 600 as a proof snapshot plus deeper diagnostics, and the 600 summary row matches the current notebook more closely.
5. Fixed the same direct continuity drift in `docs/notebook_guide.md` so the guide describes 600 as the proof snapshot plus diagnostics surface instead of the older narrower summary.
6. Audited the Kaggle publish path for 600 and fixed the metadata keyword source. The original results-section tags were rejected by Kaggle during publish, so `scripts/build_notebook_600_results_dashboard.py` and `scripts/align_kaggle_kernel_metadata.py` now emit the one confirmed-valid keyword set for this notebook instead of recycling invalid tags.
7. Rebuilt the index artifacts because the continuity wording changed: `notebooks/000_index.ipynb` and `kaggle/kernels/duecare_000_index/000_index.ipynb`.

## Why each change matters
1. The rebuild is the root-cause fix. A correct builder paired with stale emitted JSON is still a broken publication path.
2. The section-11 framing matters because 600 should surface measured proof and training priority, not try to do 440's explicit failure-taxonomy job.
3. The explicit 520 URL matters because 600 is a handoff node in `530 -> 600 -> 610 -> 899`. Those links should be canonical, not derived by slug surgery.
4. The index wording matters because 000 is where a judge decides which proof surface to open. If it understates 600, the suite navigation fights the notebook's actual role.
5. The notebook-guide wording matters for the same reason: a stale human-readable guide can still steer reviewers toward the wrong mental model of 600 even when the notebook itself is fixed.
6. The keyword fix matters because publication quality is part of the notebook's real state. A push that succeeds while Kaggle silently drops metadata is still drift.
7. Rebuilding the index matters for the same reason as rebuilding 600: future builds are not enough if the checked-in artifacts stay stale.

## Validation
1. Rebuilt the touched notebook artifacts with `c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/build_notebook_600_results_dashboard.py` and `c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/build_index_notebook.py`.
2. Ran `c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/_validate_600_adversarial.py`. It passed all canonical checks, including the header table, cross-links, slice-versus-corpus distinction, proof snapshot, coverage panel, five-grade ladder, prompt-movement watchlist, curriculum-priority diagnostics, exactly one install cell, and the final URL-bearing print cell.
3. Ran `c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe scripts/validate_notebooks.py`. It passed with `Validated 52 notebooks successfully.`
4. Published `kaggle/kernels/duecare_600_results_dashboard` to Kaggle successfully. The latest push returned `Kernel version 11 successfully pushed` for `taylorsamarel/600-duecare-results-dashboard`, and the immediate remote status check reported `KernelWorkerStatus.RUNNING`.
5. 600 remains CPU-only, keeps exactly one install cell, and still ends with a single URL-bearing final print cell linking to 610 and 899.

## Remaining risks
1. 600 is only a citation-safe proof surface when a real `data/baseline_results/comparison.json` is present. The built-in sample payload is still only layout proof.
2. The radar is still partially proxy-driven when the stage-8 artifact lacks full 410-style dimension output. The notebook is honest about that, but the upstream payload is still the limiting factor.
3. The category-performance and curriculum-priority panels still depend on per-prompt category metadata in the comparison artifact. Older payloads will fall back to weaker diagnostics.
4. The notebook is published, but the current Kaggle status is still `RUNNING`, not `COMPLETE`, so the remote render pass may still surface a runtime issue that local structural validation cannot see.
5. I found no other 600-blocking continuity drift, but other suite-wide wording inconsistencies may still exist outside the direct 600 path. I did not widen scope into those.

## Forward handoff check
1. `530 -> 600` is clean. 530 still owns the improvement artifact path, and 600 now presents that score story in the current dashboard shape instead of stale notebook JSON.
2. `600 -> 610` is clean. 610 can keep treating 600 as the measured proof surface, and the index now describes that role the same way.
3. `610 -> 899` is clean. No changes were needed in 610 or 899 for 600 to hand off correctly.
4. Back-links to `260`, `410`, `430`, `530`, `610`, and `899` remain present in 600, and the `guided`/`context` naming stays internally consistent by displaying the payload's `context` key as `Guided Prompt`.
