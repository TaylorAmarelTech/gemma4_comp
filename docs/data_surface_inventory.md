# DueCare data surface inventory (2026-05-12)

> Companion to `docs/data_primitives.md`. That doc defines the
> **canonical primitives**; this doc lists **every concrete surface**
> (function, object, JSON, template, env-var, file path, HTTP
> endpoint) so a reviewer or refactor can see the full footprint at
> a glance.

## Reading guide

The inventory is organised by **artifact category**, not by kernel,
so an operator can answer questions like "where do all the HTTP
endpoints live?" without grepping. Each row links back to the
kernel file when the surface is kernel-local.

Severity column:
- ✓ — matches canonical (per `data_primitives.md`)
- ⚠ — drift; needs rename or shape change (see
  `data_compatibility_plan.md`)
- — — N/A (canonical doesn't apply)

## 1. JSON artifact shapes (kernel -> /kaggle/working)

| Kernel | Top-level file | Top-level keys | Per-row key | Status |
|---|---|---|---|---|
| A-01 | `<RUN>_results.json` | `schema_version, kernel_id, run_id, config, metadata, summary, results[]` | `prompt_id` | ✓ |
| A-02 | `<RUN>_results.json` | same + `harness_trace` populated per row | `prompt_id` | ✓ |
| A-03 | `<RUN>_compare.json` | `..., aggregate, results[]` | `prompt_id` | ⚠ uses `aggregate` not `summary` |
| A-04 | `duecare_a04_to_a05_*` bundle | `schema_version: "duecare.a04_handoff.v1"` + nested `safety/privacy` tracks | n/a | ⚠ custom schema_version + nested tracks |
| A-05 | `<RUN>_eval.json` + HF adapter dir | `..., aggregate, results.{fine_tuned[], stock[]}` | `composite_id` | ⚠ nested results |
| A-06 / A-07 | `<RUN>_results.json` | same as A-01 / A-02 | `prompt_id` | ✓ |
| A-08 | `<RUN>_compare.json` | same as A-03 | `prompt_id` | ⚠ same `aggregate` drift |
| A-09 | `<RUN>_ladder.json` + `.jsonl` | `..., summary, results[]` (rows carry `grade`) | `prompt_id` | ✓ |
| A-10 | `<RUN>_pii_composite.json` + `<RUN>_pii_gold.jsonl` | `..., summary, results[]` | `composite_id` | ⚠ missing `error` field |
| A-11 | `<RUN>_eval.json` | `..., aggregate, results.{fine_tuned[], stock[]}` | `composite_id` | ⚠ nested + `aggregate` |
| A-12 | `<RUN>_multimodal_results.json` | `..., summary, results[]` | `upload_id` | ✓ |
| A-13 | `<RUN>_export_manifest.json` | `..., gguf_files[], litert_files[]` | n/a | — (export manifest) |
| A-14 | `<RUN>_ugc_moderation.json` + `.jsonl` | `..., aggregate, results[]` | `post_id` | ⚠ `aggregate` not `summary` |
| A-15 | `<RUN>_local_kb.json` + `.jsonl` + `local_kb.sqlite` | `..., aggregate, ingested[]` | `case_id` | ⚠ `aggregate` + `ingested[]` |
| A-16 | `<slug>-v<ver>.tar.gz` + sidecar + `<RUN>_bundle.zip` | `..., packs_built[]` | `slug + version` | ⚠ `packs_built[]` not `results[]` |
| A-17 | `<RUN>_proposals.json` + `.jsonl` | `..., summary, proposals[]` | `diff_id` | ⚠ `proposals[]` not `results[]` |
| A-19 | `a19_multilingual_demo.json` (fixed name) | inline `MULTILINGUAL_DEMO` | n/a | ⚠ no RunID; static |
| A-20 | `a20_privacy_boundary_demo.json` (fixed name) | inline `DEMO_PAYLOAD` | n/a | ⚠ no RunID; static |
| 03 video pitch | `demo_script_authored.json` (setup mode) | inline `DEMO_SCRIPT` shape | `scene_id` | — replay surface |

## 2. Python objects (dataclasses / Pydantic / module constants)

| Symbol | File | Purpose | Status |
|---|---|---|---|
| `LoadedModel` | A-01 / A-02 / A-06 / A-07 / A-12 / A-14 | dataclass: `(backend, tokenizer, model, name, size_class, quantization, device)` | ✓ shared shape |
| `BundleState` | A-03 / A-08 | dataclass: parsed upload-bundle metadata | ✓ |
| `Scenario` | A-04 prompt-generation | trafficking-rubric source rows | local-only |
| `DEMO_SCRIPT` | A-18 + 03 video pitch | module-level dict; 5 lanes x 4 scenes | ✓ |
| `SLIDES` | 03 video pitch | module-level dict; 8 slides | — |
| `MULTILINGUAL_DEMO` | A-19 | module-level dict; 5 languages | — |
| `DEMO_PAYLOAD` | A-20 | module-level dict; local + aggregate state | — |
| `RUN_ID` | every batch-runner kernel | computed string at kernel startup | ⚠ A-19 / A-20 missing |
| `OUTPUT_DIR` | every kernel | `Path("/kaggle/working")` | ✓ |
| `BUNDLE_PATH` | every batch-runner kernel | `OUTPUT_DIR / f"{RUN_ID}_bundle.zip"` | ⚠ A-19 / A-20 drift |
| `PII_PATTERNS` | A-15 + A-20 (duplicated) | list of `(label, compiled_regex)` | duplicate — consolidate |
| `_LADDER_FRAMES` | A-09 | 5-tier prompt-frame dict | local |
| `_SCRIPT_RUNTIME` | 03 video pitch | mutable wrapper for live DEMO_SCRIPT | local |
| `PROPOSED PRIMITIVES MODULE` | `packages/duecare-llm-chat/.../appendix_primitives/` (NOT YET CREATED) | shared `BundleEnvelope`, `PerRow`, `HarnessTrace`, `make_run_id`, `write_v1_bundle` | pending |

## 3. Python functions (per kernel — only data-shape-producing)

Lists functions that produce or consume canonical-shape data — not
every helper. Format: `function_name (returns) — purpose`

### A-01 / A-02 / A-06 / A-07 (batch runners)

```
load_gemma_chat()                    -> Optional[LoadedModel]
_run_id()                            -> str   # canonical RunID
_gemma_chat_one(prompt_text)         -> (response, tokens_in, tokens_out)
_gemma_chat_one_with_harness(...)    -> (response, tokens_in, tokens_out,
                                          harness_trace)   # A-02 / A-07
_build_harness_prompt(user_text)     -> (merged_prompt, harness_trace)
_git_sha_safe()                      -> str
_pkg_version(name)                   -> str
```

### A-03 / A-08 (compare kernels)

```
parse_bundle_bytes(raw, filename)    -> BundleState
_pair_bundles(baseline, harness)     -> (paired_list, warnings_list)
_comparison_id(baseline, harness)    -> str    # uses _safe_token
_safe_token(s, default, max_len)     -> str    # path/HTML-safe
run_comparison()                     -> dict   # full lift envelope
render_lift_chart(aggregate)         -> str    # standalone HTML
```

### A-04 synth data generator

```
load_gemma()                         -> Optional[LoadedModel]
load_rubrics()                       -> list[Scenario]
generate_prompts(loaded, ...)        -> list[dict]   # smoke_25 shape
_make_prompt_record(seed_id, ...)    -> dict
_emit_handoff()                      -> dict         # writes
                                                      # duecare_a04_to_a05_*
```

### A-05 trainer

```
install_unsloth_stack()              -> bool
load_a04_bundles_from_input()        -> list[dict]
train_safetyjudge_lora(...)          -> path
benchmark_stock_vs_finetuned(...)    -> dict
```

### A-09 abliterated ladder

```
_ladder_generate_one(seed_text, frame_key) -> (response, t_in, t_out)
# Inline pipeline writes <RUN>_ladder.* directly
```

### A-10 PII synth

```
_synth_value(rnd, kind, corridor)    -> str            # template-pool draw
_render_composite(rnd, scenario)     -> dict           # composite + plan
_hash_short(s)                       -> str            # 16-hex sha256
```

### A-11 PII fine-tune

```
_find_gold_jsonl()                   -> list[Path]
_format_row(example)                 -> dict           # chat-template SFT
_generate_redaction(messages_in)     -> str
_redaction_score(predicted, gold)    -> dict           # label F1 metric
_mean(rows, key)                     -> float
```

### A-12 multimodal

```
vision_call(image, user_question)    -> str
analyze_upload(raw, mime, q)         -> dict           # PerRow shape
_flush_bundle()                      -> None           # rolling persist
```

### A-14 on-device export

```
install_duecare_from_github()        -> bool
# Inline: FastModel.from_pretrained + PeftModel.merge_and_unload +
# llama.cpp build + convert_hf_to_gguf.py subprocess
```

### A-15 UGC moderator

```
_gemma_score(post_text)              -> str            # Gemma analysis
score_post(post_id, text, meta)      -> dict           # PerRow
parse_upload(raw, filename)          -> list[dict]     # CSV/JSONL parser
_aggregate()                         -> dict
_flush()                             -> None
```

### A-16 NGO local-KB

```
_salted_hash(value)                  -> str
detect_and_redact(text)              -> (redacted_text, entities)
_open_db()                           -> sqlite3.Connection
ingest_case(case_id, content)        -> dict           # PerRow
query_by_hash(salted_hash)           -> list[dict]
aggregate_preview(period_days)       -> dict
```

### A-16 pack builder

```
_sha256_bytes(data)                  -> str
_fetch_doc(spec)                     -> (doc_id, content_bytes)
build_pack(slug, version, ...)       -> dict           # manifest + paths
verify_pack(tar_path)                -> dict
```

### A-17 sentinel

```
_fetch_url(url)                      -> str            # 8 KB cap, HTML-stripped
_gemma_assess(text, target_pack)     -> str
propose_diff(source_url, ...)        -> dict           # PerRow
```

### A-18 / 03 video pitch (replay)

```
# Pure HTML/JS playback. The only Python surface is:
build_minimal_shell(summary, kernel_id, port, homepage_html, extra_routes)
# from packages/duecare-llm-chat/src/duecare/chat/kernel_shell.py
```

### 03 video pitch — added endpoints

```
GET  /api/get-script    -> {ok, script}
POST /api/save-script   -> {ok, path, size_bytes}    # writes
                                                      # demo_script_authored.json
POST /api/load-script   -> {ok}                       # replaces in-memory
```

## 4. HTML templates (`homepage_html` strings inside kernel.py)

Every kernel that serves a workbench UI carries an inline
`INDEX_HTML` template.

| Kernel | Template name | Visual identity |
|---|---|---|
| A-03 | `INDEX_HTML` | upload + lift comparison view |
| A-08 | `INDEX_HTML` | same as A-03 |
| A-12 | `INDEX_HTML` | image upload + Gemma vision result panel |
| A-14 | `INDEX_HTML` | UGC batch upload + per-row risk rows |
| A-15 | `INDEX_HTML` | NGO ingestion + query + aggregate preview |
| A-16 | `INDEX_HTML` | pack builder form + sessions + verify panel |
| A-17 | `INDEX_HTML` | URL/text submission + verdict pills |
| A-24 demo replay | `INDEX_HTML_TPL` | 5-lane x 4-scene replay (presentation only) |
| A-19 | `_render_html()` | 5-tab language picker |
| A-20 | `_render_html()` | side-by-side local-vs-outside panels |
| 03 video pitch | `INDEX_HTML_TPL` (3-mode) | tabbed Slides / Presentation / Setup |

**Drift:** every template is hand-crafted CSS/HTML. Shared design
tokens (`--paper`, `--ink`, `--accent` oklch values from
`apps/duecare-ai.com/app/static/styles.css`) are duplicated as hex
equivalents in each kernel. **Should be consolidated** into a
shared `kernel_html.css` shipped by the chat package and referenced
via `<link rel="stylesheet" href="/static/_chrome.css">` (path is
already mounted by `build_minimal_shell`).

## 5. Prompt templates (system prompts embedded in kernel.py)

| Kernel | Constant | What it instructs |
|---|---|---|
| A-09 | `_LADDER_FRAMES` dict | 5-tier prompt-frame generator (worst → best) |
| A-10 | `_SCENARIOS` list | 10 corridor-aware intake-note templates |
| A-12 | `VISION_PROMPT` | extract verbatim text + flag exploitative clauses |
| A-14 | `SCORE_PROMPT` | 0.0-1.0 risk score; cite POEA / RA / ILO |
| A-17 | `SENTINEL_PROMPT` | curator assessment + extracted_facts + rationale |
| A-04 prompt-generation | rubric-driven via YAML | graded response examples (5 tiers) |

**Shared:** `DEFAULT_PERSONA` imported from `duecare.chat.harness`
in A-02 / A-07 / A-12 / A-14 — already canonicalised in the chat
package. ✓

## 6. HTTP endpoints (per-kernel extra_routes)

| Kernel | Endpoint | Method | Returns |
|---|---|---|---|
| A-03 / A-08 | `/api/upload-bundle?slot=baseline\|harness` | POST | `{ok, error, slot, state}` |
| A-03 / A-08 | `/api/comparison-state` | GET | `{bundles, comparison}` |
| A-03 / A-08 | `/api/run-comparison` | POST | full lift envelope |
| A-12 | `/api/analyze` | POST (multipart) | PerRow |
| A-12 | `/api/bundle-info` | GET | `{bundle_name, n_uploads, size_kb}` |
| A-14 | `/api/moderate-batch` | POST (multipart) | `{ok, n_appended, n_total}` |
| A-14 | `/api/state` | GET | `{aggregate, recent_rows, bundle_*}` |
| A-15 | `/api/ingest` | POST | PerRow |
| A-15 | `/api/query?h=<salted_hash>` | GET | `{matches[]}` |
| A-15 | `/api/aggregate` | GET | aggregate preview dict |
| A-15 | `/api/state` | GET | `{recent, bundle_*}` |
| A-16 | `/api/build` | POST | pack manifest |
| A-16 | `/api/verify?t=<tarball>` | GET | `{ok, bundled_hash, recomputed_hash, ...}` |
| A-16 | `/api/state` | GET | `{built, bundle_*}` |
| A-17 | `/api/propose` | POST | proposal envelope |
| A-17 | `/api/state` | GET | `{proposals, bundle_*}` |
| 03 video pitch | `/api/get-script` | GET | `{ok, script}` |
| 03 video pitch | `/api/save-script` | POST | `{ok, path, size_bytes}` |
| 03 video pitch | `/api/load-script` | POST | `{ok}` |

**Universal endpoints** provided by `build_minimal_shell` (every
kernel inherits):

```
GET  /                   homepage_html or summary
GET  /summary            always renders the summary view
GET  /healthz            {ok, ts, kernel}
GET  /api/version        {kernel, kind, chat_package}
GET  /api/model-info     {loaded, name}
GET  /api/dc-logs        {events[], n}
GET  /api/dc-logs/stats  {stats}
POST /api/dc-logs/clear  {ok, dropped}
GET  /api/brand          {kernel, kind, counts, layers, extras}
GET  /artifact/{name}    FileResponse from artifact_root
```

## 7. Environment variable inputs

| Variable | Default | Consuming kernels |
|---|---|---|
| `DUECARE_GEMMA_VARIANT` | varies (e2b-it / e4b-it) | A-01 … A-17 |
| `DUECARE_N_PROMPTS` | varies (25/100/200/200) | A-01 / A-02 / A-06 / A-07 |
| `DUECARE_LADDER_MODE` | `"0"` | A-09 (gate for batch ladder) |
| `DUECARE_N_PII_COMPOSITES` | `"200"` | A-10 |
| `DUECARE_PII_SEED` | `"20260511"` | A-10 |
| `DUECARE_LORA_ADAPTER_PATH` | `""` | A-06 / A-07 / A-11 / A-13 |
| `DUECARE_LORA_ADAPTER_REPO` | `TaylorScottAmarel/...-safetyjudge-v1` | A-06 / A-07 / A-11 / A-13 |
| `DUECARE_LORA_ADAPTER_SLUG` | `"safetyjudge-v1"` | A-06 / A-07 / A-13 |
| `DUECARE_SFT_MAX_STEPS` | `"200"` | A-11 |
| `DUECARE_SFT_LR` | `"2e-4"` | A-11 |
| `DUECARE_SFT_BATCH` | `"2"` | A-11 |
| `DUECARE_SFT_GRAD_ACCUM` | `"4"` | A-11 |
| `DUECARE_HOLDOUT_PCT` | `"0.2"` | A-11 |
| `DUECARE_EVAL_MAX_HOLDOUT` | `"50"` | A-11 |
| `DUECARE_HF_PUSH` | `"1"` | A-11 |
| `DUECARE_HF_REPO` | `TaylorScottAmarel/...-pii-redactor-v1` | A-11 |
| `DUECARE_GGUF_QUANTS` | `"Q4_K_M,Q5_K_M"` | A-13 |
| `DUECARE_ENABLE_LITERT` | `"1"` | A-13 |
| `DUECARE_LOCAL_KB_SALT` | random hex | A-15 |
| `HF_TOKEN` (Kaggle Secret) | (none) | A-06 / A-07 / A-11 / A-12 / A-13 / A-14 |
| `DC_KERNEL_ID` | set by `set_kernel_id` | every kernel (dc_log) |
| `DUECARE_GIT_SHA` | `"unknown"` | A-01 (metadata) |

## 8. File outputs (`/kaggle/working`)

| Path | Producer | Consumer |
|---|---|---|
| `<RUN>_results.json` | A-01 / A-02 / A-06 / A-07 / A-09 / A-12 | A-03 / A-08 |
| `<RUN>_run.jsonl` | same | streaming consumers |
| `<RUN>_metadata.json` | same | git-trackable summary |
| `<RUN>_bundle.zip` | every JSON-emitting kernel | Kaggle Add Data → downstream |
| `<RUN>_compare.json` | A-03 / A-08 | researchers, video |
| `<RUN>_report.md` | A-03 / A-08 | human reviewers |
| `<RUN>_lift_chart.html` | A-03 / A-08 | embeddable Plotly chart |
| `<RUN>_eval.json` | A-11 | downstream eval comparisons |
| `<RUN>_ladder.json` + `.jsonl` | A-09 | A-04 ingestion (adversarial) |
| `<RUN>_pii_composite.json` | A-10 | A-11 ingestion |
| `<RUN>_pii_gold.jsonl` | A-10 | A-11 SFT data loader |
| `<RUN>_multimodal_results.json` | A-12 | rolling bundle |
| `<RUN>_export_manifest.json` | A-13 | distribution to llama.cpp / LiteRT |
| `gemma-4-*.gguf` | A-13 | llama.cpp local inference |
| `*-litert-recipe.txt` | A-13 | LiteRT mobile follow-up |
| `<RUN>_ugc_moderation.json` + `.jsonl` | A-14 | platform-safety audit |
| `local_kb.sqlite` | A-15 | persistent local KB across sessions |
| `<RUN>_local_kb.json` | A-15 | session aggregate snapshot |
| `<slug>-v<ver>.tar.gz` | A-16 | researchers, downstream kernels |
| `<slug>-v<ver>-manifest.json` | A-16 | sidecar signed manifest |
| `<RUN>_proposals.json` + `.jsonl` | A-17 | curator review |
| `a19_multilingual_demo.json` | A-19 (fixed name) | video reference |
| `a20_privacy_boundary_demo.json` | A-20 (fixed name) | video reference |
| `demo_script_authored.json` | 03 video pitch (setup mode) | round-trip authoring |

## 9. Cross-kernel handoff matrix

What each kernel READS from upstream bundles:

```
A-03  <-  A-01 bundle  AND  A-02 bundle           (paired by prompt_id)
A-05  <-  A-04 bundle                             (synth -> SFT/DPO)
A-08  <-  A-06 bundle  AND  A-07 bundle           (paired by prompt_id,
                                                   SAME adapter_slug)
A-11  <-  A-10 bundle                             (PII synth -> fine-tune)
A-13  <-  A-05 adapter dir  OR  HF Hub repo
A-06  <-  A-05 adapter dir  OR  HF Hub repo       (LoRA-merged inference)
A-07  <-  A-05 adapter dir  OR  HF Hub repo
A-16  <-  public URLs  OR  inline_text per doc    (pack build)
A-17  <-  any URL                                 (sentinel research)
03 video pitch  <-  demo_script_authored.json     (setup-mode reload)
```

All handoffs work via the v1.0 bundle ZIP attached as a Kaggle
Dataset → Add Data → `/kaggle/input/` → the consumer kernel scans
for the expected filename pattern.

## 10. Where this doc lives

- **This file:** `docs/data_surface_inventory.md` — full surface list
- **Primary:** `docs/data_primitives.md` — canonical shapes (read
  first for any new kernel)
- **Action plan:** `docs/data_compatibility_plan.md` — refactor
  checklist with concrete per-kernel diffs + proposed
  `duecare.appendix_primitives` helper module API

Any future kernel MUST land:

1. Functions / objects added to sections 3 / 2 here
2. Emitted JSON shapes added to section 1
3. HTML / prompt templates added to sections 4 / 5
4. Env vars + file outputs added to sections 7 / 8
5. Cross-kernel handoff added to section 9 (if any)
6. A drift entry in `data_primitives.md` if it diverges from
   canonical
