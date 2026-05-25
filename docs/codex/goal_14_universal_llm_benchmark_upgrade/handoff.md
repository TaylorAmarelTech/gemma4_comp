# Goal 14 - Universal LLM benchmark comparison and report upgrade

> Status: **PENDING**. Created 2026-05-25 after reviewing
> `kaggle/03-universal-llm-benchmark/kernel.py`.

## 1. Goal

Upgrade the Universal LLM Benchmark from a single-target runner into a
judge-friendly comparison surface with clear target presets, stable report
schema, per-row traces, and deterministic fallback behavior.

## 2. Why it matters

This kernel can show that DueCare's prompts and rubric are not tied to one
provider. It should be easy to compare a local endpoint, an OpenAI-compatible
endpoint, an Anthropic Messages endpoint, or a raw JSON endpoint against the
same DueCare corpus and judge/fallback scoring path.

## 3. Current state

- The kernel discovers prompts from the repo or uses fallback prompts.
- It supports OpenAI-compatible, Anthropic Messages, and raw JSON style calls.
- It writes `calls.jsonl` and run outputs under
  `/kaggle/working/universal-benchmark/<run_id>/`.
- It has a minimal FastAPI UI with `/api/catalog`, `/api/run`, and job polling.

## 4. Target state

- Config supports multiple named targets in one run and writes a comparison
  table.
- API keys are referenced only by environment variable names and never echoed
  in reports.
- Reports include schema version, corpus source, prompt IDs, target metadata,
  judge mode, deterministic fallback mode, per-row latency, error class, and
  score summary.
- The UI exposes download links for JSONL, JSON summary, and HTML report.

## 5. Files to read first

1. `kaggle/03-universal-llm-benchmark/kernel.py`
2. `kaggle/03-universal-llm-benchmark/README.md`
3. `packages/duecare-llm-chat/src/duecare/chat/benchmark/`
4. `packages/duecare-llm-chat/tests/test_benchmark.py`
5. `scripts/validate_kaggle_page_sources.py`

## 6. Files to modify

Prefer keeping shared scoring logic in `duecare.chat.benchmark` and leaving
the kernel as a thin runner/UI wrapper.

## 7. Files to create

Optional focused tests for config parsing, report schema, and key redaction.

## 8. Acceptance criteria

1. Single-target config remains backward compatible.
2. Multi-target config runs each target over the same prompt rows.
3. Report schema is versioned and includes per-target aggregate summaries.
4. Failed target calls produce row-level error records instead of aborting the
   full run.
5. No API key values are written to `calls.jsonl`, summaries, HTML, or logs.

## 9. Do-not-break checklist

- Keep `/api/catalog`, `/api/run`, `/api/jobs/{job_id}`, and the Cloudflare
  tunnel behavior.
- Keep the kernel runnable as a standalone Kaggle script with Internet enabled.
- Do not require DueCare package imports for fallback mode.

## 10. Verification commands

```bash
py -3.12 -m py_compile kaggle/03-universal-llm-benchmark/kernel.py
py -3.12 scripts/validate_kaggle_page_sources.py
python scripts/validate_main_kaggle_kernels.py
python -m pytest packages/duecare-llm-chat/tests/test_benchmark.py -q
```

## 11. The Codex prompt

```
Improve kaggle/03-universal-llm-benchmark from source. Keep the current
single-target config working, then add a multi-target comparison path with
redacted config handling, stable report schema, per-row latency/errors, and
downloadable outputs. Reuse duecare.chat.benchmark for scoring where possible.
Run py_compile, validate_kaggle_page_sources, and the main-kernel gate.
```

## 12. Out of scope

- Calling live paid APIs during local verification.
- Replacing the Kaggle Community Benchmark task flow.
