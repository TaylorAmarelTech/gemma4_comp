# Appendix kernel artifact schema (v1.0)

> **Source-of-truth contract** for the cross-kernel handoff format used by
> the experiment-ladder appendices (A-01 baseline → A-02 harnessed →
> A-03 compare → A-06/A-07/A-08 same flow on the fine-tuned model).
>
> Per Taylor's 2026-05-11 directive: **one model loaded per kernel run**,
> and **cross-kernel handoff happens through downloadable artifacts**, not
> live links. This doc defines what those artifacts must look like so
> A-03 / A-08 can consume any A-01 / A-02 / A-06 / A-07 run.

> **Scope note (2026-05-12).** This file is the *batch-runner-family*
> spec for A-01 / A-02 / A-03 / A-06 / A-07 / A-08. The broader contract
> covering every appendix kernel (A-01 .. A-20 + main notebook 03) plus
> the website handoff shapes lives in
> [`docs/data_primitives.md`](data_primitives.md). The shared writer /
> reader / validator helpers live in
> [`duecare.appendix_primitives`](../packages/duecare-llm-chat/src/duecare/appendix_primitives/).
> Static enforcement runs via the `bundle_envelope_v1` check inside
> [`scripts/validate_public_surface.py`](../scripts/validate_public_surface.py).
> If you are designing a NEW kernel artifact, start from
> `data_primitives.md` -- this file is kept for the batch-runner family
> historical contract.

## Three artifacts per run

Every batch-runner kernel (A-01, A-02, A-06, A-07) emits **three files**
to `/kaggle/working/`, all with the same `run_id` prefix:

| File | Purpose | Size |
|---|---|---|
| `<run_id>_results.json` | Full per-prompt response + metadata in one file | small-medium (200 prompts × ~2KB ≈ 400KB) |
| `<run_id>_run.jsonl` | Same content, one JSON object per line for streaming/append | same |
| `<run_id>_metadata.json` | Config + run metadata only, no responses | tiny (~2KB) |

The kernel also emits a `<run_id>_bundle.zip` containing all three for
single-file Add Data attachment in A-03 / A-08.

## `<run_id>_results.json` schema

```json
{
  "schema_version": "1.0",
  "kernel_id": "a-01-baseline-runner",
  "run_id": "a01_e2b-it_stock_2026-05-11T14-32-08Z",
  "config": {
    "model_variant": "e2b-it",
    "model_path": "google/gemma-4-2b-it",
    "model_kind": "stock",
    "adapter_path": null,
    "harness_enabled": false,
    "harness_layers": [],
    "max_new_tokens": 512,
    "temperature": 0.7,
    "top_p": 0.95,
    "n_prompts": 25,
    "prompt_filter": null
  },
  "metadata": {
    "started_at": "2026-05-11T14:32:08Z",
    "completed_at": "2026-05-11T14:39:14Z",
    "duration_s": 426,
    "git_sha": "e56c818",
    "duecare_chat_version": "0.17.0",
    "torch_version": "2.8.0",
    "transformers_version": "5.5.0",
    "gpu_name": "Tesla T4",
    "gpu_memory_total_mb": 15360,
    "gpu_memory_peak_mb": 9214,
    "kaggle_kernel_id": "a-01-baseline-runner",
    "host": "kaggle"
  },
  "summary": {
    "n_completed": 25,
    "n_failed": 0,
    "mean_elapsed_s": 17.0,
    "mean_tokens_in": 245,
    "mean_tokens_out": 412,
    "total_tokens_in": 6125,
    "total_tokens_out": 10300
  },
  "results": [
    {
      "prompt_id": "rec_ph_hk_zero_fee_001",
      "prompt_text": "...full original text from the library...",
      "prompt_metadata": {
        "category": "fee_camouflage",
        "subcategory": "zero_fee_promise",
        "sector": "domestic_work",
        "corridor": "PH-HK",
        "difficulty": "medium",
        "ilo_indicators": ["debt_bondage", "deception"]
      },
      "response": "...full model response text, never truncated...",
      "elapsed_s": 12.3,
      "tokens_in": 245,
      "tokens_out": 412,
      "harness_trace": null,
      "error": null
    }
  ]
}
```

## `<run_id>_run.jsonl` schema

One JSON object per line. Each line is a `result` element from the
`results: [...]` array above, with these added top-level fields for
streaming consumers:

```json
{"schema_version": "1.0", "run_id": "a01_e2b-it_stock_...", "kernel_id": "a-01-baseline-runner", "prompt_id": "...", "prompt_text": "...", "response": "...", "elapsed_s": 12.3, "tokens_in": 245, "tokens_out": 412, "harness_trace": null, "error": null, "ts": "2026-05-11T14:32:20Z"}
```

## `<run_id>_metadata.json` schema

Just the `schema_version`, `kernel_id`, `run_id`, `config`, `metadata`,
`summary` keys from the results file. **No `results` array**, so it's
small enough to commit to git or attach to a Kaggle dataset description.

## `harness_trace` field (A-02, A-07 only)

When `harness_enabled = true`, each result row includes a `harness_trace`
object describing what the harness did:

```json
{
  "persona": {"enabled": true, "system_prompt_chars": 1240},
  "grep": {
    "enabled": true,
    "rules_evaluated": 161,
    "rules_fired": [
      {"rule_id": "ph_hk_zero_fee", "category": "fee_camouflage", "severity": "high", "match_text": "no placement fee"},
      {"rule_id": "domestic_no_passport", "category": "passport_retention", "severity": "high", "match_text": "passport will be safe"}
    ],
    "elapsed_ms": 4.2
  },
  "rag": {
    "enabled": true,
    "top_k": 5,
    "docs_retrieved": [
      {"doc_id": "POEA_MC_14-2017", "score": 0.82, "title": "POEA Memorandum Circular 14-2017"},
      {"doc_id": "ILO_C189", "score": 0.71, "title": "ILO Convention 189: Domestic Workers"}
    ],
    "elapsed_ms": 47.0
  },
  "tools": {
    "enabled": true,
    "tools_called": [
      {"tool": "fee_cap_lookup", "args": {"corridor": "PH-HK"}, "result": {"cap": "zero", "statute": "POEA MC 14-2017"}}
    ],
    "elapsed_ms": 8.1
  },
  "online": {"enabled": false, "queries": []},
  "merged_prompt_chars": 8420
}
```

When `harness_enabled = false`, `harness_trace` is `null`.

## Run ID convention

Format: `{kernel_short}_{model_variant}_{model_kind}_{iso_timestamp}`

Examples:
- `a01_e2b-it_stock_2026-05-11T14-32-08Z`
- `a02_e4b-it_stock_2026-05-11T15-08-22Z`
- `a06_e2b-it_safetyjudge_2026-05-12T09-14-01Z` (after A-05 finetune)
- `a07_e4b-it_safetyjudge_2026-05-12T10-22-44Z`

`model_kind` is `stock` for unmodified Gemma 4, or the LoRA adapter slug
when running fine-tuned variants (e.g. `safetyjudge`, `pii-redactor`).

## Bundle ZIP layout

```
<run_id>_bundle.zip
├── results.json       <-- the full results file
├── run.jsonl          <-- streaming variant
├── metadata.json      <-- config-only summary
└── manifest.json      <-- {"schema_version": "1.0", "run_id": "...",
                            "files": ["results.json", "run.jsonl",
                                      "metadata.json"], "checksums": {...}}
```

## Consumption pattern in A-03 / A-08

A-03 (compare stock baseline vs harness on stock model):

1. UI accepts upload of one A-01 bundle ZIP and one A-02 bundle ZIP.
2. Verifies both bundles have matching `prompt_id` sets and matching
   `model_variant` (otherwise the comparison is invalid).
3. Runs the new harness evaluator (`packages/duecare-llm-chat/src/duecare/chat/harness/grade.py`)
   on every paired (`baseline_response`, `harness_response`) tuple.
4. Runs the legacy harness evaluator alongside for cross-validation.
5. Renders side-by-side comparison: per-dimension lift, win/loss/tie,
   citation grounding delta, and a corridor-by-corridor breakdown.
6. Exports `<comparison_id>_compare.json` + `<comparison_id>_report.md`.

A-08 (compare stock vs fine-tuned, both with harness):

Same pattern as A-03 but accepts an A-02 bundle (stock + harness) and an
A-07 bundle (fine-tuned + harness). Adds a third strip: stock-vs-
finetuned delta (orthogonal to harness-on-vs-off).

## Test prompt library (the "library" in the brief)

A-01 / A-02 / A-06 / A-07 read from
`packages/duecare-llm-chat/src/duecare/chat/harness/_examples.json`:

- Prompt counts and buckets should be read from the bundled prompt/eval
  seed or from `/api/portability` + `/api/audit/workbench-inventory` for
  the current `duecare-llm-chat 0.17.0` contract.
- Schema per prompt: `{id, text, category, subcategory, sector, corridor, difficulty, ilo_indicators, bucket}`.
- Each kernel can subset by `--n-prompts N`, `--difficulty easy|medium|hard`,
  or `--corridor PH-HK,PH-UAE`.
- Default: 25 prompts (smoke) for `e2b-it`; 100 prompts for `e4b-it`;
  200 for `26b-a4b-it` and `31b-it`.

## Reproducibility guarantees

- `git_sha` in metadata pins the commit.
- `model_path` + `model_variant` pin the upstream weights.
- `adapter_path` (when fine-tuned) pins the LoRA adapter.
- `prompt_filter` (when subsetted) pins the exact subset rule.
- `temperature`, `top_p`, `max_new_tokens` pin the decoding config.

A reviewer reading the metadata.json should be able to fully reconstruct
which model + which prompts + which decoding settings produced each
response in the bundle.
