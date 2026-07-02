# Safe-text layer: scrub, standardize, polish

> Last updated: 2026-05-24. Lives at `packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py`.

## Why this layer exists

Every workbench page that ships a string to a reviewer — knowledge fact, shareable submission, search result, complaint template, graph-chat answer, persona preview — used to format text a slightly different way. Three problems showed up in the live tunnel:

1. **Kernel staging metadata leaked into reviewer-facing prose.** Upstream process bundles pasted summaries containing `RUN_ID: process_dad7c52a7a15`, `/kaggle/working/process-staging/`, `case_files_media_rich_sample.zip`, and synthetic case folder names like `DC-PH-HK-101_Ana_Cruz/messages.jsonl`. These showed up in saved knowledge facts and would have shown up in NGO/regulator-facing complaint drafts.
2. **Each page used different field names and vocabularies.** One page emitted `evidence_quote`, another `source_excerpt`, a third `non_pii_example`. ILO indicators arrived as `feeBondage`, `fee-bondage`, `FeeCamouflage` from different upstream sources. Corridors were sometimes `ph-hk`, sometimes `PH-HK`, sometimes `PH_HK`.
3. **A draft was a draft — no iterative refinement.** Gemma produced the envelope on first attempt; if it was vague or kept a build-log quote, the reviewer either accepted it or rewrote it manually.

`_safe_text` is the single chokepoint that addresses all three.

## The three layers

### 1. Scrub layer

Pure-Python regex pass that removes operational kernel metadata from a string. Applied to anything that will reach a reviewer.

| Helper | Use it for |
|---|---|
| `clean_for_knowledge_fact(text)` | Short labels, titles, descriptions, summaries |
| `fact_excerpt(text, limit)` | Long prose where you want clean + sentence-boundary truncation: evidence_quote, source_excerpt, non_pii_example, test_phrase |
| `smart_excerpt(text, limit)` | External content that should NOT be scrubbed but still benefit from sentence-boundary cut: web search snippets, persona previews |
| `was_scrubbed(original, cleaned)` | Boolean — drives the `noise_scrubbed_before_gemma` provenance flag |

Patterns stripped:
- `RUN_ID: <anything>` and bare `process_<hex>` job IDs
- `/kaggle/working/...`, `/kaggle/input/...`, `/tmp/...`, `/home/<user>/...` paths (and the leading slash)
- `*.zip`, `*.tar`, `*.tgz`, `*.gz`, `*.json`, `*.jsonl` filenames
- `media_rich_cases/...`, `case_files_*`, `process-staging*` synthetic-corpus paths
- `DC-XX-YY-NNN_FirstName_LastName/...` synthetic case folders

Idempotent — `clean(clean(x)) == clean(x)`. None-safe — `clean(None) == ""`.

### 2. Standardize layer

Reshapes an envelope's `content` dict so every page sees the same field names, field order, and vocabulary.

| Helper | What it does |
|---|---|
| `standardize_fact_envelope(content, target_type)` | Reorders keys per `STANDARD_FACT_KEY_ORDER`, scrubs every string, normalizes indicators/corridors/stages to canonical vocab |
| `normalize_fact_indicator(value)` | Maps one indicator alias or canonical value to `STANDARD_FACT_INDICATORS`; used by template relevance matching and envelope standardization |
| `standardize_envelope_extensions(ext, *, scrubbed, polished_passes)` | Adds the `noise_scrubbed_before_gemma` and `polished_by_gemma` + `polish_passes` provenance flags |

Canonical vocabularies (the source-of-truth tuples in `_safe_text.py`):

- `STANDARD_FACT_KEY_ORDER` — 47 fields in the order they should appear
- `STANDARD_FACT_INDICATORS` — 17 lower_snake_case ILO indicators (`fee_camouflage`, `fee_bondage`, `wage_assignment`, `passport_retention`, `debt_bondage`, …)
- `STANDARD_FACT_STAGES` — 9 journey stages (`recruitment`, `payment_and_debt`, `arrival_and_placement`, …)
- Internal alias maps map `FeeBondage`, `fee-bondage`, `feeBondage` → `fee_bondage`; `deception` / `contract substitution` → `deceptive_recruitment`; `withholding_of_wages` / `withheld wages` → `withheld_wages`; `restriction_of_movement` → `movement_restriction`; `retention_of_identity_documents` → `passport_retention`; `arrival`, `placement`, `Arrival` → `arrival_and_placement`; `ph-hk`, `PH/HK`, `ph_hk` → `PH-HK`

Idempotent. Unknown indicators / stages get dropped (don't pollute the vocabulary). Unknown corridors return empty string. Unknown target_types still get the scrub + reorder.

### 3. Iterative polish layer

Server endpoint: `POST /api/knowledge/polish-envelope`.

Two Gemma 4 passes:

1. **Critique pass.** Gemma reads the draft + returns structured JSON listing specific fixable issues across nine categories: vague_phrasing, missing_ilo_indicator, non_pattern_quote, missing_corridor, missing_stage, unsupported_claim, dangling_money, personally_identifying.
2. **Rewrite pass.** Gemma applies the critique, keeping any field the critique didn't flag.

Final step: `standardize_fact_envelope` runs once more so the rewrite can't reintroduce non-canonical shape.

Returns:
```json
{
  "envelope": {...polished envelope with extensions.polished_by_gemma=true, polish_passes=2...},
  "critique": {"issues": [...], "overall": "..."},
  "passes": 2,
  "diff": [{"key": "...", "before": "...", "after": "...", "changed": true|false}]
}
```

When Gemma is unavailable: skips both passes but still runs `standardize_fact_envelope` and returns the cleaned envelope with `extensions.polish_skipped = "no model loaded"`.

UI surface: `knowledge.html` adds a "Polish further (Gemma 4)" button between "Not promoted" and "Promote draft" on every draft card. Click → critique summary + foldable field-level diff appear inline above the JSON pre block.

## Call-site map

Every handler / page that produces reviewer-facing text now imports from `_safe_text`:

| File | Uses |
|---|---|
| `harnesses/extraction/handler.py` | `clean_for_knowledge_fact`, `fact_excerpt`, `was_scrubbed`, `standardize_fact_envelope` (every envelope on every draft path) |
| `harnesses/anonymization/handler.py` | `fact_excerpt` (text_preview when Gemma's review output won't parse) |
| `harnesses/search/backends.py` | `smart_excerpt` (SearXNG snippet — external content, no scrub) |
| `harnesses/process/handler.py` | `fact_excerpt` (4 edge-pass text_preview fields in diagnostic responses) |
| `chat/app.py` | `fact_excerpt` (knowledge listing summary), `smart_excerpt` (persona text_preview in trace) |
| `chat/classifier.py` | `smart_excerpt` (persona text_preview in classifier trace) |
| `chat/templates.py` | `clean_for_knowledge_fact`, `fact_excerpt` (bundle excerpt fed to Gemma + every bundle_hint / Gemma-derived field value in `gemma_fill_template`) |

UI surfaces:

| File | Uses |
|---|---|
| `static/knowledge.html` | `noise_scrubbed_before_gemma`, `standardized_shape`, `polished_by_gemma` pills + Polish-further button |
| `static/search.html` | Three-pill provenance row (Gemma 4 refined / Noise scrubbed / Standard shape) per draft card |
| `static/templates.html` | Activity log line when bundle scrub fires |

## Provenance flags (envelope.extensions)

After a draft passes through the layers, these flags surface in the envelope:

| Key | Set by | Meaning |
|---|---|---|
| `anonymized_before_gemma` | `_build_draft_response` | The PII redactor ran |
| `placeholders_used` | `_build_draft_response` | List of PII placeholder types substituted |
| `noise_scrubbed_before_gemma` | `_build_draft_response` | The scrub layer removed something |
| `standardized_shape` | `_build_draft_response` (post-Gemma) | `standardize_fact_envelope` ran |
| `model_call_requested` | `_build_draft_response` | Caller asked for Gemma |
| `model_call_available` | `_build_draft_response` | A model was loaded |
| `gemma_drafted` | `_build_draft_response` | Gemma drafted the content (no fallback, no error) |
| `gemma_error` | `_build_draft_response` (catch) | Gemma raised; deterministic content shown instead |
| `gemma_parse_failed` | `_build_draft_response` | Gemma's output didn't parse as JSON |
| `polished_by_gemma` | `_build_polish_response` | The polish endpoint completed both passes |
| `polish_passes` | `_build_polish_response` | 0 (skipped), 1 (critique only / clean), or 2 (full polish) |
| `polish_skipped` | `_build_polish_response` | Reason Gemma didn't run |
| `polish_critique_error` / `polish_rewrite_error` | `_build_polish_response` | Per-pass failure messages |
| `polish_clean_pass` | `_build_polish_response` | Critique found no issues; standardize-only finished the pass |

## What it doesn't do

- **PII removal** — that's `harnesses/anonymization/`. The scrub layer ASSUMES the PII detector ran first; it only removes operational metadata.
- **Translation** — quotes stay in their source language.
- **Validation** — the layer doesn't reject an envelope, it cleans it. Schema validation happens at the promote step.
- **Cross-envelope deduplication** — out of scope; that's the knowledge-list page.

## Testing

`packages/duecare-llm-chat/tests/test_knowledge_noise_scrub.py` covers ~50 cases across five test classes:

- `TestCleanForKnowledgeFact` — pattern coverage, idempotence, None-safety
- `TestFactExcerpt` — sentence-boundary truncation, pre-truncation clean
- `TestSmartExcerpt` — URL preservation, None-safety
- `TestWasScrubbed` — boolean correctness
- `TestStandardizeFactEnvelope` — indicator/corridor/stage normalization, canonical key order, idempotence, non-dict input
- `TestStandardizeEnvelopeExtensions` — provenance flag writes
- `TestDeterministicContentContract` — every target_type produces noise-free content

## How to extend

To add a new vocabulary token (e.g. a new ILO indicator):

1. Add the canonical string to `STANDARD_FACT_INDICATORS` in `_safe_text.py`.
2. Add any aliases (CamelCase / hyphenated / spaced) to `_INDICATOR_ALIASES`.
3. Run `python -c "import runpy; runpy.run_path('packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py')"` to sanity-check syntax.
4. Add a regression test in `test_knowledge_noise_scrub.py`.

To add a new scrub pattern:

1. Add a compiled regex to `_KNOWLEDGE_NOISE_PATTERNS`.
2. Add a positive test (pattern present → stripped) and a negative test (similar-but-meaningful text → preserved) in `TestCleanForKnowledgeFact`.

To add a new polish critique category:

1. Edit `_POLISH_CRITIQUE_SYSTEM` in `extraction/handler.py` to add the category to the bulleted list.
2. Update `_POLISH_REWRITE_SYSTEM` if the new category requires a new rule.

## Known limitations

- The scrub regex matches `case_files_*` and `media_rich_cases/*` greedily — useful for our synthetic demo cases, but a real NGO partner with a folder literally named "case_files_2026" would have it stripped. Acceptable in this workbench since we don't ingest partner-named folders directly.
- The polish endpoint serializes the draft as JSON and feeds it to Gemma. Very large envelopes (>3k chars) may overflow Gemma's context budget. The endpoint truncates Gemma's response at 768 new tokens.
- The corridor format assumes two-letter country codes. Regions like "ASEAN" or "GCC" aren't supported and get dropped.
