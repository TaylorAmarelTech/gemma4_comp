# DueCare data primitives — unified source-of-truth (2026-05-12)

> **Why this doc exists.** The kernels + website have been growing
> data shapes faster than the schema doc can keep up. This file is
> the single canonical reference for every data primitive that
> crosses a kernel / website / artifact boundary. It supersedes
> ad-hoc per-kernel field definitions and extends
> `docs/appendix_artifact_schema.md` (which only covered the
> A-01/02/03 batch-runner family).
>
> See also `docs/data_surface_inventory.md` (full inventory of
> every function / object / JSON / template) and
> `docs/data_compatibility_plan.md` (the unification refactor
> checklist).

## 0. Scope: two contracts, intentionally distinct

DueCare has **two** schema contracts. Do not confuse them:

| Contract | Location | Shape | Used by |
|---|---|---|---|
| **BundleEnvelope v1.0** | `duecare.appendix_primitives.envelopes` | `schema_version: "1.0"` (string) + `kernel_id`, `run_id`, `summary`, `results[]` | Every `kaggle/*/kernel.py` that writes JSON to `/kaggle/working/` |
| **KnowledgeObject envelope** | `apps/duecare-ai.com/app/schema.py` | `schema_version: 1` (integer) + `@type`, `id`, `version`, `provenance`, `content`, `extensions{}` | The website's pack-vetting workflow (ContextPack, GrepRulePack, ToolPack, ContactPack, RubricPack, EvalPromptPack, TrainingExamplePack, Submission, Run) |

The rest of this document describes the **BundleEnvelope contract
only**. The website's `KnowledgeObject` envelope is a separate
JSON-LD-style schema for vetted knowledge artifacts; see
`apps/duecare-ai.com/app/schema.py` for that contract. The audit
check `bundle_envelope_v1` only scans `kaggle/*/kernel.py`, never
the website surface.

## 1. The 7 canonical primitives

### 1.1 BundleEnvelope (top-level wrapper)

Every kernel that writes JSON to `/kaggle/working/` MUST use this
top-level envelope:

```json
{
  "schema_version": "1.0",
  "kernel_id": "<kebab-case-slug>",
  "run_id": "<RunID — see 1.6>",
  "config": { /* run-time inputs */ },
  "metadata": { /* started_at, completed_at, host */ },
  "summary": { /* aggregate stats — counts, means, deltas */ },
  "results": [ /* per-row PerRow entries — see 1.2 */ ]
}
```

Naming rules:

- `schema_version` is literal `"1.0"` for v1 of this contract.
  Bump to `"2.0"` only on an incompatible change. Avoid per-
  kernel schema_version strings like `"duecare.a04_handoff.v1"`
  (current A-04 drift — see drift table).
- `kernel_id` is the kebab-case slug `a-NN-<purpose>` for
  appendix kernels, or `NN-<purpose>` for main notebooks.
- Top-level keys `summary` and `results` are canonical names.
  Some current kernels use `aggregate` instead of `summary`, or
  `ingested[]` / `proposals[]` / `packs_built[]` instead of
  `results[]`. All are equivalent semantically; the canonical
  form is `summary` + `results`.

### 1.2 PerRow (one entry in `results[]`)

```json
{
  "row_id": "<kernel-specific stable identifier>",
  "prompt_text": "<original input — never truncated>",
  "response": "<model output — never truncated>",
  "elapsed_s": 12.34,
  "tokens_in": 245,
  "tokens_out": 412,
  "harness_trace": <HarnessTrace or null — see 1.3>,
  "citations": [ /* Citation strings — see 1.4 */ ],
  "error": null
}
```

Conventions:

- `row_id` is the kernel-specific stable key. Batch runners use
  `prompt_id`; multimodal uses `upload_id`; UGC moderator uses
  `post_id`; pack builder uses `pack_slug + version`; sentinel
  uses `diff_id`. They all serve as the row's primary key.
- `prompt_text` and `response` are NEVER truncated. Display
  truncation is a UI concern, not a data-emit concern.
- `harness_trace` is `null` when the kernel ran harness OFF
  (A-01, A-06 baseline runners); otherwise a HarnessTrace.
- `error` is `null` on success; otherwise a short string
  `"<ErrorType>: <message>"`. ALL kernels SHOULD include the
  field even if always null (signals "no error" rather than
  "field absent").

### 1.3 HarnessTrace

The runtime trace of what the harness DID for one prompt:

```json
{
  "persona": {"enabled": true, "system_prompt_chars": 1240},
  "grep": {
    "enabled": true,
    "rules_evaluated": 161,
    "rules_fired": [
      {"rule_id": "ph_hk_zero_fee", "category": "fee_camouflage",
       "severity": "high", "match_text": "no placement fee"}
    ],
    "elapsed_ms": 4.2
  },
  "rag": {
    "enabled": true,
    "top_k": 5,
    "docs_retrieved": [
      {"doc_id": "POEA_MC_14-2017", "score": 0.82,
       "title": "POEA Memorandum Circular 14-2017"}
    ],
    "elapsed_ms": 47.0
  },
  "tools": {
    "enabled": true,
    "tools_called": [
      {"tool": "fee_cap_lookup", "args": {"corridor": "PH-HK"},
       "result": {"cap": "zero", "statute": "POEA MC 14-2017"}}
    ],
    "elapsed_ms": 8.1
  },
  "online": {"enabled": false, "queries": []},
  "merged_prompt_chars": 8420
}
```

The 5 layer keys (`persona`, `grep`, `rag`, `tools`, `online`)
are always present, even when a layer is disabled (`enabled:
false`, empty arrays).

### 1.4 Citation

A single citation is just a string identifying a statute /
advisory / pack-versioned doc:

```
"POEA MC 14-2017"
"ILO C189"
"RA 8042"
"BP2MI Reg 8-2023"
"pack_hash:7e2c4a8f1b9d..."
"git_sha:e56c818"
```

When a kernel emits an array of citations, every entry is a
bare string. No nested `{label, severity, evidence}` objects —
those belong in `harness_trace.grep.rules_fired[]` (1.3), not
in the citations array.

### 1.5 ErrorEntry

When something fails inside the per-row pipeline, `error` is a
short string with the exception type + truncated message:

```
"TimeoutError: model timed out after 60s"
"ValueError: invalid corridor 'PH-XX'"
"JSONDecodeError: expecting value at line 4 col 12"
```

Never include a stack trace in the artifact; the long form goes
to stderr / dc_log. The artifact field is for downstream
filters.

### 1.6 RunID

Format: `{slot}_{purpose}_{variant}_{iso_ts}` where:

- `slot` is the kernel's 2-3-char slug (`a01`, `a02`, ..., `a20`,
  or `03` for main notebook 03)
- `purpose` is a short underscore-cased descriptor
  (`stock`, `harnessed`, `compare`, `ugc`, `synth`, `export`,
  `multimodal`, etc.)
- `variant` is optional; present for kernels where the Gemma
  variant matters (`e2b-it`, `e4b-it`) or where an adapter slug
  matters (`safetyjudge-v1`, `pii-redactor-v1`)
- `iso_ts` is ISO 8601 UTC with `:` replaced by `-`:
  `2026-05-12T19-30-00Z`

Examples:

```
a01_e2b-it_stock_2026-05-12T19-30-00Z
a02_e4b-it_stock_2026-05-12T19-30-00Z
a03_compare_e4b-it_2026-05-12T19-45-00Z
a06_e4b-it_safetyjudge-v1_2026-05-12T20-00-00Z
a11_pii_finetune_e2b-it_2026-05-12T20-15-00Z
a14_export_e2b-it_safetyjudge-v1_2026-05-12T20-30-00Z
a15_ugc_e4b-it_2026-05-12T20-45-00Z
a16_local_kb_2026-05-12T21-00-00Z
a17_pack_session_2026-05-12T21-15-00Z
a18_sentinel_2026-05-12T21-30-00Z
03_video_pitch_session_2026-05-12T21-45-00Z
```

Static-demo kernels (A-19 multilingual, A-20 privacy-boundary)
SHOULD also emit a RunID — currently they use fixed filenames
which prevents multiple recordings without collisions.

### 1.7 BundleName

Every JSON-emitting kernel writes a `<RUN_ID>_bundle.zip` to
`/kaggle/working/` containing:

```
<RUN_ID>_bundle.zip
├── manifest.json       {schema_version, run_id, kernel_id, files[]}
├── results.json        the BundleEnvelope payload
├── run.jsonl           streaming variant (one PerRow per line)
└── metadata.json       BundleEnvelope minus results[]
```

The bundle is the unit consumed by Add Data when crossing
kernels (A-03 ingests A-01 + A-02; A-08 ingests A-06 + A-07;
A-05 ingests A-04; A-11 ingests A-10).

Filename convention: `<RUN_ID>_bundle.zip`. Fixed-name bundles
like `a19_multilingual_bundle.zip` are drift.

## 2. Per-kernel artifact inventory (post-Tier 1+2 state)

Top-level keys shown as `canonical (+ legacy alias)` where the
kernel emits both during rollover. Legacy aliases will be removed
in a post-submission migration to `write_v1_bundle()`.

| Kernel | RunID format | Bundle name | Top-level keys | Per-row key | `error` field |
|---|---|---|---|---|---|
| A-01 baseline | `a01_{variant}_stock_{ts}` | `<RUN>_bundle.zip` | `summary` + `results[]` | `prompt_id` | yes |
| A-02 harnessed | `a02_{variant}_stock_{ts}` | `<RUN>_bundle.zip` | `summary` + `results[]` | `prompt_id` | yes |
| A-03 compare | `a03_compare_{variant}_{ts}` | `<RUN>_bundle.zip` | `summary` (+ legacy `aggregate`) + `results[]` | `prompt_id` | yes |
| A-04 synth data | (custom handoff) | `duecare_a04_to_a05_bundle.zip` | `schema_version: "1.0"` + `handoff_kind: "synth_data_to_trainer"` + `safety` + `privacy` tracks | n/a | no |
| A-05 trainer | (consumes A-04) | HF adapter dir + bench JSON | tracked separately | n/a | n/a |
| A-06 new-model baseline | `a06_{variant}_{adapter}_{ts}` | `<RUN>_bundle.zip` | `summary` + `results[]` | `prompt_id` | yes |
| A-07 new-model harnessed | `a07_{variant}_{adapter}_{ts}` | `<RUN>_bundle.zip` | `summary` + `results[]` | `prompt_id` | yes |
| A-08 new-model compare | `a08_compare_{variant}_{ts}` | `<RUN>_bundle.zip` | `summary` (+ legacy `aggregate`) + `results[]` | `prompt_id` | yes |
| A-09 abliterated ladder | `a09_{variant}_abliterated_{ts}` | `<RUN>_bundle.zip` | `summary` + `results[]` | `prompt_id` | yes |
| A-10 PII synth | `a10_pii_synth_{ts}` | `<RUN>_bundle.zip` | `summary` + `results[]` (composite rows now carry `error: null`) | `composite_id` | yes |
| A-11 PII fine-tune | `a11_pii_finetune_{variant}_{ts}` | `<RUN>_bundle.zip` | `summary` (+ legacy `aggregate`) + flat `results[]` with `condition` (+ legacy `results_by_condition.{fine_tuned, stock}`) | `composite_id` | no |
| A-12 multimodal | `a12_multimodal_{variant}_{ts}` | `<RUN>_bundle.zip` | `summary` + `results[]` | `upload_id` | yes |
| A-13 export | `a14_export_{variant}_{adapter}_{ts}` | `<RUN>_bundle.zip` | manifest only (`gguf_files`, `litert_files`) | n/a | no |
| A-14 UGC moderator | `a15_ugc_{variant}_{ts}` | `<RUN>_bundle.zip` | `summary` (+ legacy `aggregate`) + `results[]` | `post_id` | yes |
| A-16 NGO local-KB | `a16_local_kb_{ts}` | `<RUN>_bundle.zip` | `summary` (+ legacy `aggregate`) + `results[]` (+ legacy `ingested[]`); rows carry `error: null` | `case_id` | yes |
| A-16 pack builder | `a17_pack_session_{ts}` | `<RUN>_bundle.zip` | `summary` + `results[]` (+ legacy `packs_built[]`) | `slug + version` | per-doc only |
| A-17 sentinel | `a18_sentinel_{ts}` | `<RUN>_bundle.zip` | `summary` + `results[]` (+ legacy `proposals[]`) | `diff_id` | yes (`ok=false`) |
| A-24 demo replay | (no run_id; static) | (n/a — no writes) | inline `DEMO_SCRIPT` | `scene_id` | n/a |
| A-19 multilingual | `a19_multilingual_{ts}` | `<RUN>_bundle.zip` | inline `MULTILINGUAL_DEMO` (run_id-tagged) | n/a | n/a |
| A-20 privacy boundary | `a20_privacy_{ts}` | `<RUN>_bundle.zip` | inline `DEMO_PAYLOAD` (run_id-tagged) | n/a | n/a |
| A-21 long-context | `a21_long_context_{ts}` | `<RUN>_bundle.zip` (4 canonical files via `write_v1_bundle`) | `summary` + `results[]` | `qa_id` | yes |
| A-22 streaming-demo | `a22_streaming_{ts}` | `<RUN>_bundle.zip` (4 canonical files via `write_v1_bundle`) | `summary` + `results[]` | `scenario_id` | yes |
| A-23 coordinator | `a23_coordinator_{ts}` | `<RUN>_bundle.zip` (4 canonical files via `write_v1_bundle`) | `summary` + `results[]` (each row carries `tool_plan[]` + `tool_results[]` extras) | `scenario_id` | yes |
| 03 video pitch | (`demo_script_authored.json` in setup mode) | n/a | inline `DEMO_SCRIPT` | `scene_id` | n/a |

## 3. Drift table (historical -- all entries RESOLVED in 2026-05-12 rollover)

Every entry below shipped a fix on 2026-05-12. The "Resolution"
column points at the commit that landed the change. Legacy aliases
remain emitted alongside canonical keys during the rollover so
existing readers continue to work.

| Kernel | Drift | Severity | Resolution |
|---|---|---|---|
| A-04 | `schema_version: "duecare.a04_handoff.v1"` (custom value) | MEDIUM | DONE in `c0e6f64` -- now `"1.0"` + `handoff_kind: "synth_data_to_trainer"` |
| A-04 | Tracks nested as `safety` + `privacy` (not flat `results[]`) | LOW | Accepted as-is -- A-05 trainer parses the nested shape; flatten deferred |
| A-11 | `results.{fine_tuned[], stock[]}` instead of flat | LOW | DONE in `c0e6f64` -- flat `results[]` with `condition`; nested kept as `results_by_condition` |
| A-13 | No `results[]`; only `gguf_files[]` + `litert_files[]` | LOW | Accepted -- export kernels emit asset manifests, not per-prompt results |
| A-14 | `aggregate` instead of canonical `summary` | LOW | DONE in `c0e6f64` -- canonical `summary` emitted alongside legacy `aggregate` |
| A-15 | `aggregate` + `ingested[]` instead of canonical pair | LOW | DONE in `c0e6f64` -- canonical pair emitted alongside legacy aliases |
| A-16 | `packs_built[]` instead of `results[]` | LOW | DONE in `c0e6f64` -- canonical `results[]` alongside legacy `packs_built[]` |
| A-17 | `proposals[]` instead of `results[]` | LOW | DONE in `c0e6f64` -- canonical `results[]` alongside legacy `proposals[]` |
| A-19 | No RunID; fixed bundle name | MEDIUM | DONE in `c0e6f64` -- `RUN_ID = f"a19_multilingual_{ts}"`; bundle now `<RUN>_bundle.zip` |
| A-20 | No RunID; fixed bundle name | MEDIUM | DONE in `c0e6f64` -- `RUN_ID = f"a20_privacy_{ts}"`; bundle now `<RUN>_bundle.zip` |
| A-15 | No `error` field on `ingested[]` rows | LOW | DONE in `c0e6f64` -- rows carry `error: null` default |
| A-10 | No `error` field on composite rows | LOW | DONE in `c0e6f64` -- composite rows carry `error: null` default |
| A-18 / 03 | No artifact emit (replay-only) | none | Accepted -- static demo surfaces; setup-mode `demo_script_authored.json` follows the inline `DEMO_SCRIPT` schema |

**Resolution summary:** 11 of 13 drift entries fixed in commit
`c0e6f64` via the legacy-alias rollover pattern (emit BOTH
canonical + legacy alias side-by-side). 2 entries (A-04 nested
tracks, A-13 manifest-only) deliberately accepted as-is. The
shared helper module (`duecare.appendix_primitives`, commit
`9be6b74`) and the static audit check
(`bundle_envelope_v1`, commit `9be6b74`) prevent regressions
going forward.

## 4. Website handoff shapes

### 4.1 `/api/score` (live runtime risk envelope)

The website's developer page (`client-connect.html`) documents the
runtime scoring endpoint. The envelope mirrors PerRow (1.2) plus
runtime-only fields:

```json
{
  "schema_version": "1.0",
  "score": 0.94,
  "verdict": "high_risk",
  "action_hint": "remove",
  "indicators": [
    {"label": "illegal_placement_fee",
     "severity": "high",
     "evidence": "22000 pesos + PH-HK domestic"}
  ],
  "citations": ["POEA MC 14-2017"],
  "explanation_short": "...",
  "harness_trace": <HarnessTrace>
}
```

`score` / `verdict` / `action_hint` are runtime-only. The
`indicators` array uses the same shape as
`harness_trace.grep.rules_fired[]` — these are synonyms. Future
contract: collapse to a single shape.

### 4.2 Submission flow (`/submit-information`)

Accepted submission kinds:

```json
{
  "submission_kind": "pack_diff" | "aggregate_signal" | "advisory_link",
  "payload": { /* one of the three shapes below */ }
}
```

- **pack_diff:** `{slug, version, curator, documents[]}` — consumed
  by A-16 pack builder
- **aggregate_signal:** `{period_days, n_cases,
  indicator_label_counts, repeat_hashes[]}` — emitted by A-15
  local-KB aggregate preview
- **advisory_link:** `{url, target_pack}` — consumed by A-17
  sentinel

### 4.3 Knowledge-pack manifest

```json
{
  "schema_version": "1.0",
  "slug": "ph-hk-domestic-worker",
  "version": "1.4.0",
  "released": "2026-02-08T00:00:00Z",
  "curator": "Polaris Project",
  "documents": [
    {"doc_id": "POEA_MC_14-2017",
     "source_url": "https://...",
     "sha256": "...",
     "size_bytes": 4218,
     "stored_at": "docs/POEA_MC_14-2017.txt"}
  ],
  "manifest_hash": "sha256:7e2c4a8f1b9d..."
}
```

This is the SAME shape A-16 emits.

### 4.4 Demo-replay / video-pitch script

```json
{
  "schema_version": "1.0",
  "kernel_id": "03-duecare-video-pitch",
  "lanes": {
    "<lane_key>": {
      "label": "Migrant worker — Lane 03",
      "intro": "A worker on a low-spec phone ...",
      "scenes": [
        {
          "scene_id": "worker_fee_question_01",
          "prompt": "...",
          "response": "...",
          "harness_trace": <HarnessTrace>,
          "citations": [ /* Citation strings */ ],
          "latency_simulation_ms": 2200
        }
      ]
    }
  }
}
```

When the operator clicks "Save" in 03's setup mode, this object
is written to `/kaggle/working/demo_script_authored.json` via
`POST /api/save-script`.

## 5. Unification proposal

### 5.1 Tier 1 — must fix before submission

1. **A-04 schema_version drift** — change
   `"duecare.a04_handoff.v1"` to `"1.0"`. Add `handoff_kind`
   field. Verify A-05 trainer's parser tolerates either value
   during the transition.
2. **A-19 / A-20 RunID** — add `RUN_ID = f"<slot>_<purpose>_{ts}"`
   and rename bundles to `<RUN>_bundle.zip`. Keeps multiple
   recordings collision-free.

### 5.2 Tier 2 — should fix this week

3. Rename `aggregate` -> `summary` in A-14, A-15.
4. Rename `ingested[]` -> `results[]` in A-15.
5. Rename `proposals[]` -> `results[]` in A-17.
6. Rename `packs_built[]` -> `results[]` in A-16.
7. Flatten A-11's `results.{fine_tuned, stock}` to a flat
   `results[]` with `row.condition` field.
8. Add `error: null` default to A-10 + A-15 rows.

### 5.3 Tier 3 — long-term enforcement

9. Add `duecare.appendix_primitives` helper module to
   `packages/duecare-llm-chat` exposing:

```python
from duecare.appendix_primitives import (
    make_run_id,          # canonical RunID generator
    BundleEnvelope,       # pydantic-validated top-level wrapper
    PerRow,               # pydantic per-row validator
    HarnessTrace,         # pydantic harness-trace validator
    write_v1_bundle,      # writes <RUN>_results.json + .jsonl
                          # + _metadata.json + _bundle.zip with
                          # manifest in one call
    read_v1_bundle,       # reverse: parses a bundle, returns
                          # a validated BundleEnvelope
)
```

Every future kernel imports from this module instead of hand-
rolling the bundle. Existing kernels migrate one at a time.

10. Update `scripts/validate_public_surface.py` to add a
    `bundle_envelope_v1` check that scans every kernel for
    canonical conformance.

## 6. Where this doc lives

- **This file:** `docs/data_primitives.md` — the canonical reference
- **Companion specs:**
  - `docs/appendix_artifact_schema.md` — older spec covering only
    A-01/02/03; this doc extends + supersedes
  - `docs/appendix_experiment_ladder.md` — slot definitions + rules
  - `docs/data_surface_inventory.md` — full function / object /
    JSON / template inventory (companion to this doc)
  - `docs/data_compatibility_plan.md` — the unification refactor
    checklist with concrete diffs
- **Linked from:** `kaggle/_INDEX.md`, every kernel's `README.md`
  "Outputs" section.

Any agent or contributor editing kernel artifact shapes MUST read
this doc first.
