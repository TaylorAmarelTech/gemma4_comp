# Safety gate — never commit, log, or publish PII

> Auto-loaded by Claude Code at the project memory level. This rule
> applies to every file, every commit, every log line, every
> notebook, and every published artifact.

## Hard rules

1. **No raw PII in git.** Ever. Applies to source files, test
   fixtures, examples, docs, markdown, notebooks. If a draft has a real
   name, address, phone, passport number, case id, or email, redact or
   invent a composite before committing.

2. **No raw PII in logs.** The observability layer (`duecare.observability`)
   has a structlog filter that strips any line containing content flagged
   by the anonymization detectors. Do not bypass the filter.

3. **No raw PII in training data.** The Anonymizer agent is a hard
   gate (see `src/forge/agents/anonymizer/`). Downstream agents (Curator,
   Trainer) cannot read the raw probe store. If a downstream agent needs
   more context, the fix is to tag the clean data with metadata, NOT to
   route raw data around the gate.

4. **No raw PII in published artifacts.** HF Hub weights + Kaggle
   Models + Kaggle Datasets + Kaggle Notebook + Writeup + video — none
   of them may contain raw PII. The Exporter agent runs a final
   verification scan before publishing.

5. **Audit log stores hashes, not plaintext.** When the Anonymizer
   redacts something, the audit table records `sha256(original)` plus
   the action taken, never the original text.

## What counts as PII for this project

Per `configs/duecare/domains/trafficking/pii_spec.yaml`:

Critical (must be redacted):
- Given names, family names (real people)
- Passport / visa / national ID numbers
- Phone numbers (any format)
- Email addresses
- Bank account numbers, IBANs
- Home addresses
- Dates of birth (generalize to year)

Generalizable (convert to a less-specific form):
- Cities → "a city in [country]"
- Employer names → "a recruitment agency" unless in public court record

Keep:
- Country names
- Statute names and section numbers
- Case numbers **if already in public court record**

## Allowed exceptions

- **Composite character names** (Maria, Ramesh, Sita) explicitly
  labeled as composites in the writeup and video.
- **Real NGO names** (Polaris Project, IJM, POEA, BP2MI, etc.) —
  these are public organizations, not individuals, and naming them
  is a load-bearing part of the impact story.
- **Historical public court cases** where victim names have been
  published in the official court record AND the case is referenced
  with its case number so readers can verify.

## Enforcement

- Pre-commit hook: gitleaks + a custom regex check for the critical
  categories above
- Anonymizer agent runs before any data enters the clean store
- Validator agent does a pre-publish scan on all artifacts
- CI runs the same checks on every PR

If one of these checks fires, the commit / run / publish is aborted.
Do not work around it — fix the source.
