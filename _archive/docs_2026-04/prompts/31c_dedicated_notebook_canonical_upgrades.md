# 31c: DueCare dedicated notebook canonical upgrades

Date captured: 2026-04-16
Audience: Claude Code or GPT-5.4 running inside this repo.

This is stage 3 of the 31-series. Run it only after `31b` has produced
`docs/review/31b_hardening_gate_report.md` and the structural gate is
green.

This stage upgrades the remaining dedicated comparison builders with the
canonical `210` and `220` structure, adds any missing dedicated
validators, and leaves a clearly push-ready dedicated-builder batch.

## Required inputs

Read these first:

1. `docs/review/31a_repo_truth_inventory.md`
2. `docs/review/31b_hardening_gate_report.md`
3. `docs/prompts/30_project_checkpoint.md`
4. `scripts/build_notebook_210_oss_model_comparison.py`
5. `scripts/build_notebook_220_ollama_cloud_comparison.py`
6. `scripts/build_notebook_230_mistral_family_comparison.py`
7. `scripts/build_notebook_240_openrouter_frontier_comparison.py`
8. `scripts/build_notebook_270_gemma_generations.py`
9. `scripts/_validate_210_adversarial.py`
10. `scripts/_validate_220_adversarial.py`

If they already exist, also read:

1. `scripts/_validate_230_adversarial.py`
2. `scripts/_validate_240_adversarial.py`
3. `scripts/_validate_270_adversarial.py`

## Required output artifact

Create or update `docs/review/31c_dedicated_upgrades_report.md` with
these sections only:

1. `Notebook upgrades`
2. `Validators created or updated`
3. `Rebuild commands`
4. `Validation results`
5. `Push-ready dedicated kernels`
6. `Inputs for 31d`

## Execution rules

- Treat `210` and `220` as the structural template.
- Upgrade the builders, not the emitted notebooks.
- Keep `230`, `240`, and `270` in one dedicated batch unless a clear
  safety reason forces a split.
- Add dedicated validators for any touched comparison notebook that
  does not already have one.
- Preserve truthful numbers in `270`; no placeholder comparisons.

## Required tasks

1. Canonicalize `230`, `240`, and `270` to match the modern comparison
   structure:
   - canonical HTML header
   - single hardener-managed install path
   - no em-dash H1 or pseudo-table intro
   - `SAFETY_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())`
   - `_hex_to_rgba(...)` fill handling
   - troubleshooting table
   - notebook-specific URL-bearing final print
2. For `270`, load `gemma_baseline_findings.json` with a published
   fallback so the historical bands remain real.
3. Create or update the `230`, `240`, and `270` adversarial validators
   mirroring the `220` validator pattern.
4. Rebuild the notebooks, sync mirrors if needed, run the dedicated
   validators, and then run the full suite validator.
5. Write the artifact with the exact push order for the dedicated batch.

## Gate to leave 31c

- All touched dedicated validators pass.
- `python scripts/validate_notebooks.py` stays green.
- `docs/review/31c_dedicated_upgrades_report.md` exists and names the
  next shared-builder batch for `31d`.

## Final response format

Return a single markdown document with these sections only:

1. `Dedicated notebooks upgraded`
2. `Validators and validation`
3. `Push-ready dedicated batch`
4. `Shared-builder handoff`

Do not ask follow-up questions.
