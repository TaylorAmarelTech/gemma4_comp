<!--
  PR template — keep it short. CI runs the validator + tests on every PR;
  see .github/workflows/ci.yml.
-->

## What this PR does

<!-- One-line summary. -->

## Why

<!-- One paragraph. Especially important for legal claims, weight tuning,
     and threshold changes. Include citation/source URLs for legal facts. -->

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (wire format / API rename / dim removal)
- [ ] Curator JSON edit (signal / statute / question / weight / hint)
- [ ] Documentation only

## If this is a curator JSON edit (NGO / jurist / language expert PR)

- [ ] I ran `python scripts/validate_curator_blocks.py` and it returned 0 errors
- [ ] I added `added_by` / `added_date` / `rationale` provenance fields where the schema asks for them
- [ ] I bumped `last_updated` in the file's envelope
- [ ] (For legal additions) I included a `source_url` to an authoritative source

## If this is a code change

- [ ] I added or updated the smallest relevant tests under `packages/` or `tests/`
- [ ] `python -m pytest packages --collect-only -q` passes
- [ ] The relevant package test scope passes
- [ ] If the wire format changed, I updated the component docs and compatibility notes

## If this is a public documentation / GitHub metadata change

- [ ] I checked [`docs/DOCUMENTATION_GUIDE.md`](../docs/DOCUMENTATION_GUIDE.md)
- [ ] `python scripts/validate_public_surface.py` passes with 0 findings
- [ ] I did not claim a full test pass unless the full command actually ran
- [ ] I used readable link labels instead of raw file paths in public tables

## Reviewer

<!-- Tag the right expertise:
     - jurist for legal blocks (_authoritative_statutes, _known_statute_sections, _evaluation_questions)
     - native speaker for non-English signals (_classifier_signals.json with a `lang` field)
     - methodologist for weights (_usecase_affinity, _intent_affinity, _grader_config)
     - corridor expert for _country_hints
     - eval team for _baseline_gauge updates -->
