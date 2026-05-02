# 31e: DueCare publish plan and verification handoff

Date: 2026-04-16
Scope: stage 5 of the 31-series. Pre-flight is complete. This doc is
the exact script the user runs to push the 31b/31c/31d outputs to
Kaggle once the daily cap window is available.

Kaggle API calls are not initiated from Claude Code. This file is the
runnable handoff.

## 0. Pre-flight state (verified 2026-04-16)

| Gate | Result |
|---|---|
| `python scripts/validate_notebooks.py` | `Validated 42 notebooks successfully` |
| `python scripts/_validate_210_adversarial.py` | `ALL CHECKS PASSED` |
| `python scripts/_validate_220_adversarial.py` | `ALL CHECKS PASSED` |
| `python scripts/_validate_230_adversarial.py` | `ALL CHECKS PASSED` |
| `python scripts/_validate_240_adversarial.py` | `ALL CHECKS PASSED` |
| `python scripts/_validate_270_adversarial.py` | `ALL CHECKS PASSED` |
| Slug map | `scripts/kaggle_live_slug_map.json` matches current repo truth (29 live, 13 pending) |
| Shared helpers | `_public_slugs.py`, `_canonical_notebook.py` in place |
| 600 source of truth | `scripts/build_notebook_600_results_dashboard.py` now exists |

## 1. Environment (run once in the push shell)

```powershell
$env:PYTHONIOENCODING = "utf-8"
if (-not $env:KAGGLE_API_TOKEN) { throw "Set KAGGLE_API_TOKEN first." }

# sanity probe (read-only, does not consume push cap)
kaggle kernels status taylorsamarel/duecare-gemma-vs-oss-comparison
```

The expected response is the 210 kernel's current run status. If it
returns an HTTP error, the whole session is gated on Kaggle API
availability and the pushes below should not be attempted yet.

## 2. Push order (exact)

Push in the order listed. One push at a time. If any push returns
`400 Bad Request` or `Notebook not found`, STOP and apply the
fallback sequence in section 4.

### Batch A: update pushes on 31b/31c/31d canonicalized kernels (4)

```powershell
kaggle kernels push -p kaggle/kernels/duecare_230_mistral_family_comparison
kaggle kernels push -p kaggle/kernels/duecare_240_openrouter_frontier_comparison
kaggle kernels push -p kaggle/kernels/duecare_270_gemma_generations
kaggle kernels push -p kaggle/kernels/duecare_220_ollama_cloud_comparison
```

Each of these has a live kernel at the canonical slug; the push is a
version bump. The `Your kernel title does not resolve to the specified
id` warning is expected and harmless on 220 (title has `220:` prefix,
id has the shorter live slug).

### Batch B: update pushes on 31d shared-builder kernels (2)

```powershell
kaggle kernels push -p kaggle/kernels/duecare_250_comparative_grading
kaggle kernels push -p kaggle/kernels/duecare_260_rag_comparison
```

260 is a GPU kernel; Kaggle will only schedule its run when the GPU
slot is available. The push itself is not GPU-dependent.

### Batch C: update push on the 600 Results Dashboard (1)

```powershell
kaggle kernels push -p kaggle/kernels/duecare_600_results_dashboard
```

Metadata id was already aligned to the canonical live slug
`600-duecare-results-dashboard`. This push version-bumps the canonical
slug; the legacy `600-interactive-safety-evaluation-dashboard` redirect
continues to work untouched.

### Batch D: first-time creation on the three blocked conclusions (3)

```powershell
kaggle kernels push -p kaggle/kernels/duecare_299_baseline_text_evaluation_framework_conclusion
kaggle kernels push -p kaggle/kernels/duecare_399_baseline_text_comparisons_conclusion
kaggle kernels push -p kaggle/kernels/duecare_130_prompt_corpus_exploration
```

These three carry fallback slugs (`duecare-baseline-text-evaluation-framework-conclusion`,
`duecare-baseline-text-comparisons-conclusion`, `duecare-prompt-corpus-exploration`).
If any still fails, skip that one and move on; do not retry in the same
session.

### Batch E: section conclusions that have never been pushed (6)

These are new kernels; push after Batch D has succeeded so at least
one non-canonical-prefix first-time creation is known to work today.

```powershell
kaggle kernels push -p kaggle/kernels/duecare_099_orientation_background_package_setup_conclusion
kaggle kernels push -p kaggle/kernels/duecare_199_free_form_exploration_conclusion
kaggle kernels push -p kaggle/kernels/duecare_499_advanced_evaluation_conclusion
kaggle kernels push -p kaggle/kernels/duecare_599_model_improvement_opportunities_conclusion
kaggle kernels push -p kaggle/kernels/duecare_699_advanced_prompt_test_generation_conclusion
kaggle kernels push -p kaggle/kernels/duecare_799_adversarial_prompt_test_evaluation_conclusion
kaggle kernels push -p kaggle/kernels/duecare_899_solution_surfaces_conclusion
```

### Batch F: playgrounds never pushed (3)

```powershell
kaggle kernels push -p kaggle/kernels/duecare_150_free_form_gemma_playground
kaggle kernels push -p kaggle/kernels/duecare_155_tool_calling_playground
kaggle kernels push -p kaggle/kernels/duecare_160_image_processing_playground
```

These are T4 GPU kernels.

### Batch G: refresh index and glossary cross-links

After Batch A through F land, rebuild 000 and 005 so their section-map
cross-links re-resolve. Only then push them:

```powershell
$py = "c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe"
& $py scripts/build_index_notebook.py
& $py scripts/build_notebook_005_glossary.py
& $py scripts/validate_notebooks.py
kaggle kernels push -p kaggle/kernels/duecare_000_index
kaggle kernels push -p kaggle/kernels/duecare_005_glossary
```

## 3. Post-push verification

```powershell
$py = "c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe"
& $py scripts/verify_kaggle_urls.py
```

Expected: `N OK, 0 FAIL` where `N` is the number of live kernels after
Batch A through F. Any FAIL row points at a slug that is stale in one
of the cross-link builders and must be re-reconciled before the next
push session.

After verification, regenerate the inventory:

```powershell
& $py scripts/generate_kaggle_notebook_inventory.py
```

Commit the regenerated `docs/current_kaggle_notebook_state.md`,
updated `scripts/kaggle_live_slug_map.json`, and the refreshed
checkpoint.

## 4. Fallback sequence when a push fails

### Case A: `400 Bad Request` on first-time creation

The canonical `NNN-duecare-*` slug is rejected. Choose a shorter
fallback and add it to `scripts/_public_slugs.py` under the same
notebook id key. Rebuild the three builders that import
`PUBLIC_SLUG_OVERRIDES`, run the validator, then retry the push exactly
once.

### Case B: `Notebook not found` on what should be an update

Live kernel slug drifted. Read the live slug from the Kaggle UI (the
URL path after `/code/taylorsamarel/`) or from
`scripts/kaggle_live_slug_map.json` if current, then revert the builder's
`KERNEL_ID` and the local `kernel-metadata.json` id to the live slug.
Rebuild, validate, retry once.

### Case C: daily cap exhausted

Stop the session. Wait until the next Kaggle day window. Do not loop
retries.

## 5. Updating the checkpoint after the session

After the push session, append a short Section 12 addendum to
`docs/prompts/31_project_checkpoint_v2.md` listing:

- batches that succeeded (count + slugs)
- batches that failed and why (error code, notebook id)
- the resulting count of live kernels
- whether `scripts/verify_kaggle_urls.py` came back green
- the next action item (for example: "retry 130 tomorrow with fallback
  slug `duecare-130`").

## 6. What this stage did NOT do

- No pushes were attempted from Claude Code.
- No read-only status probes were run from Claude Code either.
- `scripts/verify_kaggle_urls.py` was not run during 31e preparation.
- The 13 not-yet-live kernels are still not live. They become live only
  after the user runs the commands above.

## 7. Immediate follow-ups after a clean push session

1. Rerun `scripts/validate_notebooks.py` one more time. Expect
   `Validated 42 notebooks successfully`.
2. Rerun every adversarial validator. Expect five ALL CHECKS PASSED.
3. Regenerate `docs/current_kaggle_notebook_state.md`.
4. Refresh `docs/writeup_draft.md` if the number of live kernels
   changed. The TL;DR currently reads "42 of 42 validated; 29 live /
   13 push-ready" — update to reflect the new live count.
5. Refresh `docs/prompts/31_project_checkpoint_v2.md` section 3 (live
   kernel inventory) and section 5 (open blockers).
