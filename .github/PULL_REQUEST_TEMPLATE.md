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

- [ ] I added or updated tests in `packages/duecare-llm-chat/tests/`
- [ ] `python scripts/verify.py` passes
- [ ] `python -m pytest packages/duecare-llm-chat/tests/` passes
- [ ] If the wire format changed, I updated `docs/component_diagram.md` and bumped the chat package version

## Reviewer

<!-- Tag the right expertise:
     - jurist for legal blocks (_authoritative_statutes, _known_statute_sections, _evaluation_questions)
     - native speaker for non-English signals (_classifier_signals.json with a `lang` field)
     - methodologist for weights (_usecase_affinity, _intent_affinity, _grader_config)
     - corridor expert for _country_hints
     - eval team for _baseline_gauge updates -->
