# Contributing to Duecare's curator-block JSON files

> Guide for stakeholders — NGO partners, jurists, researchers, regulators —
> who want to PR an edit to one of the 11 curator-JSON files that drive
> the Duecare grader. **You can do this without reading any Python.**

The grader's "magic strings" — per-language signal lists, statute
allowlists, dimension multipliers, judge questions, etc. — used to be
hardcoded inline in `harness/__init__.py`. As of v3.6 they live in
versioned JSON files with provenance metadata, so any qualified
stakeholder can submit a single-file PR.

## What you can edit

| File | Curator typically | What an edit does |
|---|---|---|
| `_classifier_signals.json` | NGO caseworkers, regional language experts | Adds prompt-classification signals (e.g. "I'm scared" in Tagalog → worker_asking) |
| `_authoritative_statutes.json` | Jurists, legal researchers | Adds a statute the grader should recognize as "real and authoritative" |
| `_known_statute_sections.json` | Jurists | Updates a statute's valid section/article range (catches "RA 8042 §99" hallucinations) |
| `_evaluation_questions.json` | Curators of evaluation methodology | Refines the per-dimension yes/no question + hint sent to the LLM evaluator |
| `_usecase_affinity.json` | Methodologists | Tunes how much each rubric dim matters per audience (worker_asking weights `concrete_resources` 1.8×; lawyer_research weights `convention_specific_article` 1.6×) |
| `_intent_affinity.json` | Methodologists | Same idea, but for response-side intent (refusal vs education vs analytical) |
| `_intent_signals.json` | Methodologists | Phrases that detect response-side intent |
| `_country_hints.json` | Corridor experts | Adds a new origin/destination corridor's signal phrases |
| `_grader_config.json` | Methodologists, security reviewers | Tunes thresholds (gaming defense %, breaker limits, structure boost) |
| `_baseline_gauge.json` | Eval team | Updates the stock vs harnessed reference numbers when a new eval set is run |
| `_rubric_hints.json` | Curators of UX hints | Refines the inline "How to PASS this" examples shown in the chat UI |

All 11 files live in:

```
packages/duecare-llm-chat/src/duecare/chat/harness/
```

## How to PR an edit

### 1. Pick the right file from the table above.

### 2. Open the file. Each starts with a curator-block envelope:

```json
{
  "schema":       "duecare-X/v1",
  "version":      "1.0.0",
  "last_updated": "2026-05-06",
  "curator":      "Your name or organisation",
  "notes":        "Free-form description of what this file does and editing conventions.",
  "entries":      [...]    // or "questions" / "use_cases" / "countries", depending on file
}
```

You don't need to bump `version` for small edits, but please **update
`last_updated` and `curator`** so reviewers can see who's maintaining
the entries.

### 3. Add or modify entries.

Most entries support these provenance fields (always optional, always
preserved):

| Field | Type | Meaning |
|---|---|---|
| `added_by` | string | Who added the entry (your name, organisation, or handle) |
| `added_date` | string (YYYY-MM-DD) | When the entry was added |
| `rationale` | string | One sentence: why this signal/statute/weight is right |
| `last_amended` | string (YYYY-MM-DD) | When you last touched the entry |
| `source_url` | string | Citation URL (especially for statute updates) |

A good entry on a statute looks like:

```json
{
  "name":          "ra 11862",
  "jurisdiction":  "PH",
  "topic":         "expanded anti-trafficking",
  "added_by":      "duecare",
  "added_date":    "2026-05-04",
  "rationale":     "Expanded Anti-Trafficking Act of 2022; supersedes RA 9208 in some provisions",
  "source_url":    "https://lawphil.net/statutes/repacts/ra2022/ra_11862_2022.html"
}
```

### 4. Run the validator from the repo root:

```bash
python scripts/validate_curator_blocks.py
```

You should see all 11 files marked `[OK]` and `0 errors, 0 warnings`.
If your edit introduced an error or warning, the validator will tell
you which file + line.

For strict mode (warnings escalated to failure):

```bash
python scripts/validate_curator_blocks.py --strict
```

### 5. Open a PR.

In the PR description, briefly say:

- **What changed** (one line)
- **Why** (one paragraph — particularly important for statute updates and weight tuning)
- **Citations / sources** for legal claims, especially when adding or
  superseding a statute

A reviewer with domain expertise (jurist for legal blocks, language
expert for non-English signals, methodologist for weights) will
review.

## File-specific guidance

### `_classifier_signals.json`

This is the prompt-classifier's rule layer. Each entry maps a phrase
in the user's prompt to a use-case score. Adding signals improves the
classifier's coverage of specific audiences and languages.

**Adding a multi-lingual signal:**

```json
{"use_case": "worker_asking", "signal": "tulungan mo ako", "weight": 2.0,
 "lang": "tl",
 "added_by": "your-name", "added_date": "2026-05-15",
 "rationale": "Tagalog: 'help me' — common worker-side opening"}
```

`lang` should be a BCP 47 code from the file's `supported_languages`
block. If you're adding signals for a language that isn't listed yet,
PR an addition to `supported_languages` in the same file.

**Weight scale:**
- `0.6 – 1.0` — weak signal (a single word that's only suggestive)
- `1.4 – 1.6` — moderate (a phrase that's more specific)
- `2.0` — strong (an unambiguous opening like "tulungan mo ako")

Don't go above 2.0; the classifier soft-normalises so very high weights
are mostly redundant and risk overweighting one signal.

### `_authoritative_statutes.json`

The grader uses this list to recognise legitimate statute citations
that aren't directly bundled in the 33-doc RAG corpus. Add an entry
when a model is correctly citing a statute the grader is currently
flagging as "possibly fabricated".

**Don't** add fake or proposed statutes; this list is the grader's
truth-of-record about what's real.

### `_known_statute_sections.json`

Catches model hallucinations like "RA 8042 §99" (RA 8042 only has 42
sections). When a statute is amended and a new section is added,
increase `max` here.

### `_evaluation_questions.json`

The yes/no questions sent to the LLM evaluator (the framework
academic literature calls "LLM-as-judge"). Per-dimension question +
hint. The dimension_id MUST exist in `_rubric_universal.json`. Keep
the question terse and the hint specific — generic questions get
generic answers.

### `_usecase_affinity.json`

Per-use-case dimension weight multipliers. A multiplier of 1.0 leaves
the base weight untouched; >1.0 makes the dim more important; <1.0
less. Ranges:

- `0.5 – 0.8` — reduce weight (this dim matters less for this audience)
- `1.0` — neutral
- `1.3 – 1.6` — moderately important
- `1.8` — very important (max recommended)

When you raise a weight, prefer adding a `rationale` so the next
reviewer understands the reasoning.

### `_grader_config.json`

Tunable thresholds. Don't change these casually — they're calibrated
against the 207-prompt eval set. Examples of legitimate edits:

- Loosening the gaming-defense cap (60% → 70%) when running against a
  research benchmark where bag-of-keywords gaming is rare
- Tightening the LLM-evaluator breaker (3 consecutive errors → 2) for
  a low-tolerance production deployment

### `_baseline_gauge.json`

Update when re-running the eval set against a new rubric version. Set:

- `eval_set_size`
- `eval_run_date`
- `rubric_version`
- `git_sha`
- `stock.value` and `harnessed.value`

Include a `footnote` explaining the methodology change so users see
why the numbers shifted.

## Style + formatting

- 2-space indent
- UTF-8 encoding (the supported languages span Latin, Devanagari,
  Bengali, Burmese, Arabic, etc.)
- Sort entries by `added_date` ascending OR by topic, but keep one
  order consistent within each file
- Don't reorder existing entries — git diff readability matters
- One JSON object per line for entries with simple shape (e.g.
  classifier signals); multi-line for nested ones (e.g. usecase
  affinity)

## Reviewers

Each curator-block is owned by a reviewer set with the relevant
expertise. PRs touching:

- `_authoritative_statutes.json`, `_known_statute_sections.json`,
  `_evaluation_questions.json` → at least one **legal reviewer**
- `_classifier_signals.json` (non-English) → at least one **native
  speaker** of the language being edited
- `_usecase_affinity.json`, `_intent_affinity.json`,
  `_grader_config.json` → at least one **methodologist** familiar
  with the eval set + rubric design
- `_country_hints.json` → at least one **corridor expert** (NGO with
  field experience in the corridor being edited)
- `_baseline_gauge.json` → eval team + reproducibility check (re-run
  against the cited git_sha)

## Schema versioning

If you introduce a breaking change to a curator-block schema (rename
a field, change a value type), bump the schema version:

```
"schema": "duecare-classifier-signals/v3"
```

The Python loader is permissive on unknown fields but strict on
required-field absence; your validator-script run will catch most
schema-incompat issues before merge.

## Where the data goes

After your PR is merged:

1. CI rebuilds the chat-package wheel
2. The Kaggle dataset for each notebook is bumped
3. Notebook re-runs pull the new wheel, which carries your edit
4. The change shows up live within ~5 minutes of dataset publish

Your edit is auditable through:

- Git history
- The `version` and `last_updated` fields in the curator block
- `/api/version` (returns every curator-block version + entry count)
- `/api/governance/<name>` (returns the full curator block JSON)
