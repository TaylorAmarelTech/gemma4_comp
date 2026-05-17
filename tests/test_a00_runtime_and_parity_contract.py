"""A-00 runtime + harness parity contract.

These tests pin the invariants surfaced by the 2026-05-16 review of the
A-00 omni experiment workbench:

1.  A-00 inference loads through the shared Gemma4Runtime, not via a
    direct FastModel.from_pretrained inference call. The training-script
    path is the documented exception.
2.  PipelineRequest's Pydantic defaults remain aligned with the
    preconfigured page (limit=4, harness_profile=chat_no_online,
    baseline_harness_profile=none, llm_judge=True, small Gemma path).
3.  Generation fallback (no backend) uses Gemma 4 recipe defaults
    (top_p=0.95, top_k=64) so a stale path can't silently change scores.
4.  chat_no_online layers go through duecare.chat.harness shared
    callables. A-00 keeps pack rules/facts as additive extras, not as
    the only source.
5.  Combined grading uses grade_response_combined from
    duecare.chat.harness for the LLM-judge phase.
6.  Final report title reflects the actual arms that ran (stock-only
    vs full four-arm matrix).
7.  Dead grading helpers, if retained, are intentional fallbacks rather
    than silent dead code; HARNESS_PROFILES literal is preserved as a
    documented defensive fallback for the contract import.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
A00 = ROOT / "kaggle" / "A-00-omni-experiment-workbench" / "kernel.py"
GEMMA4_RUNTIME = ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "gemma4_runtime.py"


def _a00_text() -> str:
    return A00.read_text(encoding="utf-8")


def test_a00_inference_loads_through_shared_gemma4_runtime() -> None:
    """A-00 must declare A00_MODEL_RUNTIME = Gemma4Runtime(...) and route
    every inference load through A00_MODEL_RUNTIME.load(Gemma4LoadSpec(...))."""
    text = _a00_text()
    assert "from duecare.chat.gemma4_runtime import Gemma4LoadSpec, Gemma4Runtime, resolve_model_ref" in text
    assert "A00_MODEL_RUNTIME = Gemma4Runtime(log=_a00_model_log)" in text
    assert "A00_MODEL_RUNTIME.load(Gemma4LoadSpec(" in text
    assert "A00_MODEL_RUNTIME.unload(reason)" in text


def test_a00_only_direct_fastmodel_call_is_inside_training_script() -> None:
    """Inference must not bypass Gemma4Runtime. The training-script
    string is the documented exception (Unsloth fine-tuning path); the
    only FastModel.from_pretrained occurrence in A-00 must live inside
    _training_script."""
    text = _a00_text()
    parts = text.split("def _training_script(req: TrainRequest, resolved_data_path: str, output_dir: Path) -> str:", 1)
    assert len(parts) == 2, "Expected _training_script function in A-00 kernel"
    before_training_script, after_training_script_start = parts
    assert "FastModel.from_pretrained(" not in before_training_script, (
        "Inference path must not call FastModel.from_pretrained directly; "
        "use A00_MODEL_RUNTIME.load() instead."
    )
    # The training-script block contains the documented Unsloth call.
    assert "FastModel.from_pretrained(" in after_training_script_start, (
        "Training script must keep the Unsloth FastModel.from_pretrained call."
    )


def test_a00_pipeline_request_defaults_match_proof_contract() -> None:
    """PipelineRequest's Pydantic defaults must keep the
    preconfigured-proof shape. Regression-trips if anyone edits the
    Pydantic defaults away from the UI's bound defaults."""
    text = _a00_text()
    pieces = text.split("class PipelineRequest(BaseModel):", 1)
    assert len(pieces) == 2, "PipelineRequest class not found"
    body, _rest = pieces[1].split("\n\n\nSTATE:", 1)
    expected_defaults = [
        'preset_id: str = "synthetic_train_benchmark_cycle"',
        'model_a_ref: str = A00_SMALL_MODEL_REF',
        'model_b_ref: str = A00_SMALL_MODEL_REF',
        'judge_model_source: str = "hf"',
        'judge_model_ref: str = ""',
        'judge_model_adapter_ref: str = ""',
        'harness_profile: str = A00_BULK_COMPARE_DEFAULT["treatment_harness"]',
        'baseline_harness_profile: str = A00_BULK_COMPARE_DEFAULT["baseline_harness"]',
        'limit: int = 4',
        'synthetic_count: int = 4',
        'evaluate_outputs: bool = True',
        'include_report: bool = True',
        'execute_training: bool = False',
        'llm_judge: bool = True',
        'unload_between_steps: bool = True',
    ]
    missing = [token for token in expected_defaults if token not in body]
    assert not missing, f"PipelineRequest defaults drifted: missing {missing}"
    # The small-model default ref must resolve to the proof-path Gemma.
    assert 'A00_SMALL_MODEL_REF = os.environ.get("DUECARE_A00_SMALL_MODEL_REF", "google/gemma-4-2b-it")' in text


def test_a00_generation_fallback_uses_gemma4_recipe_defaults() -> None:
    """When no backend is attached, the defensive raw-generate fallback
    must use Gemma 4 recipe defaults (top_p=0.95, top_k=64). The
    fallback path is retained so capacity is preserved if the backend
    callable ever fails to attach."""
    text = _a00_text()
    pieces = text.split("def _generate(prompt: str, *, max_new_tokens: int, temperature: float, trace: dict[str, Any], row: dict[str, Any]) -> tuple[str, dict[str, Any]]:", 1)
    assert len(pieces) == 2, "_generate function not found"
    body, _rest = pieces[1].split("\ndef ", 1)
    assert '"top_p": 0.95' in body, "fallback must use top_p=0.95 (Gemma 4 default)"
    assert '"top_k": 64' in body, "fallback must use top_k=64 (Gemma 4 default)"
    assert '"top_p": 0.9,' not in body, "fallback must not use the stale top_p=0.9"
    assert '"mode": "model_fallback_no_backend"' in body, (
        "fallback path must be labelled as the no-backend fallback so a "
        "stuck pipeline can be distinguished from the primary backend path."
    )


def test_a00_chat_no_online_uses_shared_harness_callables() -> None:
    """The chat_no_online harness profile must route through
    duecare.chat.harness._grep_call / _rag_call / _tools_call so the
    measured harness lift matches Kernel 01's compare page. A-00's
    pack rules/facts are folded in as extras (additive, not
    replacement)."""
    text = _a00_text()
    assert "_grep_call as _shared_grep_call" in text
    assert "_rag_call as _shared_rag_call" in text
    assert "_tools_call as _shared_tools_call" in text
    assert "_SHARED_HARNESS_AVAILABLE" in text
    pieces = text.split("def _build_harness_prompt(row: dict[str, Any], harness_profile: str) -> tuple[str, dict[str, Any]]:", 1)
    assert len(pieces) == 2, "_build_harness_prompt not found"
    body, _rest = pieces[1].split("\ndef ", 1)
    assert "_shared_grep_call(prompt, extra_rules=_pack_rules_as_grep_extras())" in body
    assert "_shared_rag_call(prompt, top_k=5, extra_docs=_pack_facts_as_rag_extras())" in body
    assert "_shared_tools_call(messages_for_tools)" in body
    assert "def _pack_rules_as_grep_extras() -> list[dict[str, Any]]:" in text
    assert "def _pack_facts_as_rag_extras() -> list[dict[str, Any]]:" in text
    # Pack-only fallbacks remain available for flexibility/capacity when
    # the shared harness import fails.
    assert "def _rule_hits(text: str) -> list[dict[str, Any]]:" in text
    assert "def _rag_facts(text: str, limit: int = 5) -> list[dict[str, Any]]:" in text


def test_a00_combined_grading_uses_shared_grade_response_combined() -> None:
    """The LLM-judge phase of the pipeline must go through
    grade_response_combined from duecare.chat.harness; this is the same
    grader Kernel 01 uses for /api/grade-combined-stream."""
    text = _a00_text()
    assert "from duecare.chat.harness import grade_response_combined, grade_response_universal" in text
    assert "grade_response_combined(" in text
    assert "def _combined_grade(row: dict[str, Any], response: str, harness_profile: str, trace: dict[str, Any], use_llm: bool) -> dict[str, Any]:" in text
    assert "_evaluate_run_for_pipeline(" in text
    assert "duecare.chat.harness.grade_response_combined" in text
    assert "duecare.chat.harness.grade_response_universal" in text


def test_a00_pipeline_report_title_conditional_on_arms_run() -> None:
    """Pipeline report title must reflect the actual arms that ran. A
    stock-only run (execute_training=False) must not be labelled as the
    four-arm matrix."""
    text = _a00_text()
    assert "A-00 pipeline stock vs stock+harness:" in text, (
        "Need a distinct title for stock-only runs"
    )
    assert "A-00 pipeline stock/fine-tuned/harness matrix:" in text, (
        "Need the full four-arm matrix title when training executed"
    )
    assert "if req.execute_training and len(run_ids) >= 4:" in text


def test_a00_harness_profiles_literal_is_defensive_fallback() -> None:
    """The HARNESS_PROFILES dict literal is intentionally retained as a
    defensive fallback so A-00 still boots if harness_profile_map()
    returns empty (e.g. during a partial wheel install). The shared
    contract remains the source of truth when available."""
    text = _a00_text()
    assert "HARNESS_PROFILES: dict[str, dict[str, Any]] = {" in text
    assert "_SHARED_PROFILES = harness_profile_map()" in text
    assert "if _SHARED_PROFILES:" in text
    assert "HARNESS_PROFILES = _SHARED_PROFILES" in text


def test_gemma4_runtime_pins_gemma4_generation_defaults() -> None:
    """The shared Gemma4Runtime.backend must default to the Gemma 4
    recipe parameters: temperature=1.0, top_p=0.95, top_k=64. These are
    load-bearing for harness parity across kernels."""
    text = GEMMA4_RUNTIME.read_text(encoding="utf-8")
    assert "temperature: float = 1.0," in text
    assert "top_p: float = 0.95," in text
    assert "top_k: int = 64," in text
    assert "dtype=None," in text
    assert 'load_in_4bit=spec.quantization.lower() in {"4bit", "nf4"},' in text
    assert "full_finetuning=False," in text


def test_a00_pack_rules_and_facts_have_pack_marked_provenance() -> None:
    """When pack rules/facts feed shared GREP/RAG via extras, the
    normalized hit/fact dicts must carry source markers so a reviewer
    can distinguish shared vs pack contributions in trace output."""
    text = _a00_text()
    assert '"citation": f"pack:{slug}@{version}" if version else f"pack:{slug}"' in text
    assert '"source": f"pack:{slug}",' in text
    assert 'str(h.get("citation", "")).startswith("pack:")' in text
    assert 'str(d.get("source", "")).startswith("pack:")' in text


def test_a00_activity_logs_full_prompts_responses_and_untruncated_buffer() -> None:
    """The preconfigured pipeline Activity log is the judge/debug trace.
    It must expose the raw prompt, the exact model prompt passed to
    Gemma, and the response for every benchmark row. The browser-side
    Activity buffer must not silently truncate earlier entries."""
    text = _a00_text()
    assert "def _run_activity_detail(bundle: dict[str, Any]) -> dict[str, Any]:" in text
    assert '"raw_prompt": row.get("prompt", "")' in text
    assert '"model_prompt_sent_to_gemma": row.get("model_prompt", "")' in text
    assert '"response": row.get("response", "")' in text
    assert '"prompt_response_pairs": pairs' in text
    assert '"model_prompt": model_prompt' in text
    assert '"sample_sft_rows": sft_rows[: min(10, len(sft_rows))]' in text
    assert 'el.textContent = `[${stamp}] ${summary}${detail}\\n\\n` + (el.textContent || "");' in text
    assert "slice(0, 18000)" not in text
    assert ".slice(-8).map" not in text


def test_a00_training_activity_exposes_larger_log_excerpt_and_full_log_link() -> None:
    text = _a00_text()
    assert "def _tail_text(path: Path, limit: int = 20000) -> str:" in text
    assert "def _training_log_activity(job: dict[str, Any]) -> dict[str, Any]:" in text
    assert '"log_excerpt": log_excerpt' in text
    assert '"log_link": _artifact_link(str(log_path)) if log_path.exists() else ""' in text
    assert "Open log_link for the complete training log" in text
    assert '_append_job_step(pipeline_job_id, "12. Fine-tuning progress update", "running", detail)' in text


def test_a00_training_saves_and_resumes_checkpoints() -> None:
    text = _a00_text()
    assert 'resume_from_checkpoint: str = ""' in text
    assert "save_steps: int = 10" in text
    assert "training_resume_from_checkpoint: str = \"\"" in text
    assert "training_save_steps: int = 10" in text
    assert 'save_strategy="steps"' in text
    assert "save_steps=SAVE_STEPS" in text
    assert "save_total_limit=SAVE_TOTAL_LIMIT" in text
    assert "def latest_checkpoint(output_dir):" in text
    assert 'root.glob("checkpoint-*")' in text
    assert "trainer.train(resume_from_checkpoint=resume_checkpoint if resume_checkpoint else None)" in text
    assert "trainer.save_state()" in text
    assert "def _checkpoint_dirs(output_dir: str | Path) -> list[Path]:" in text
    assert '"latest_checkpoint": str(latest_checkpoint) if latest_checkpoint else ""' in text
    assert '"checkpoint_paths": [str(p) for p in checkpoints[-10:]]' in text
    assert '"resume_note": "If a Kaggle session ends before completion, rerun with the same output_dir or pass resume_from_checkpoint to continue from the latest checkpoint."' in text
    assert 'id="pipeline-resume-checkpoint"' in text
    assert 'id="pipeline-save-steps"' in text
    assert 'id="train-resume-checkpoint"' in text
    assert 'id="train-save-steps"' in text
    assert "training_resume_from_checkpoint: $(\"pipeline-resume-checkpoint\").value" in text
    assert "resume_from_checkpoint: $(\"train-resume-checkpoint\").value" in text


def test_a00_pipeline_supports_separate_judge_model() -> None:
    text = _a00_text()
    assert "def _judge_model_request(req: PipelineRequest) -> ModelLoadRequest:" in text
    assert "req.judge_model_ref or req.model_a_ref" in text
    assert 'id="preconfig-judge-model"' in text
    assert "const judgeSelected = $(\"preconfig-judge-model\")" in text
    assert "judge_model_ref: judgeModelRef" in text
    assert "judge_model_source: $(\"pipeline-judge-source\").value" in text
    assert '"18. Loading judge Gemma model for final evaluation"' in text
    assert '"experiment_model_ref": req.model_a_ref' in text
    assert '"reason": "Final grading uses the selected normal judge model; it does not reuse the fine-tuned adapter unless explicitly configured."' in text


def test_a00_judging_phase_emits_per_response_progress() -> None:
    text = _a00_text()
    assert "def _evaluate_run_for_pipeline(" in text
    assert "19. Evaluating responses using combined rule + LLM judge for run {run_index} of {total_runs}" in text
    assert "19. Judging response {row_index} of {len(rows)}" in text
    assert "19. Completed judgment {row_index} of {len(rows)}" in text
    assert '"n_responses": len(rows)' in text
    assert '"prompt_id": row.get("prompt_id")' in text
    assert '"model_prompt_sent_to_gemma": row.get("model_prompt", "")' in text
    assert '"response": row.get("response", "")' in text
    assert 'grade["judge_model"] = {' in text


def test_a00_report_writes_complete_writeup_evidence_bundle() -> None:
    text = _a00_text()
    assert "def _report_prompt_response_rows(selected_bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:" in text
    assert "def _write_report_svg_bar_chart(" in text
    assert "def _write_report_evidence_bundle(" in text
    assert "def _write_simple_pdf(path: Path, title: str, lines: list[str]) -> None:" in text
    assert "def _report_activity_detail(report: dict[str, Any], run_ids: list[str]) -> dict[str, Any]:" in text
    assert 'prompt_csv_path = RUN_DIR / f"{report_id}_prompt_responses.csv"' in text
    assert 'score_svg_path = RUN_DIR / f"{report_id}_score_chart.svg"' in text
    assert 'latency_svg_path = RUN_DIR / f"{report_id}_latency_chart.svg"' in text
    assert 'evidence_zip_path = RUN_DIR / f"{report_id}_evidence_bundle.zip"' in text
    assert '"prompt_response_rows": prompt_rows' in text
    assert '"writeup_ready_outputs": [' in text
    assert '"Single evidence ZIP with report and run exports"' in text
    assert '"21. Saving report and write-up evidence bundle"' in text
    assert "WeasyPrint unavailable; wrote fallback PDF summary" in text
    assert '<section class="panel evidence-panel">' in text
    assert 'id="evidence-links"' in text
    assert 'function artifactLinksHtml(links)' in text
    assert 'function updateEvidenceLinksFromObject(obj)' in text
    assert 'Download evidence ZIP' in text


def test_a00_exports_full_activity_log_and_root_output_index() -> None:
    text = _a00_text()
    assert 'ACTIVITY_DIR = OUTPUT_DIR / "a00_activity"' in text
    assert 'OUTPUT_INDEX_DIR = OUTPUT_DIR / "a00_outputs"' in text
    assert "def _write_activity_artifacts(job: dict[str, Any]) -> dict[str, str]:" in text
    assert "def _write_output_index() -> None:" in text
    assert 'job["activity_artifacts"] = _write_activity_artifacts(job)' in text
    assert '"activity_zip": str(ACTIVITY_DIR / f"{safe_id}_activity_bundle.zip")' in text
    assert '"output_manifest": str(OUTPUT_DIR / "A00_LATEST_OUTPUTS.json")' in text
    assert '"output_readme": str(OUTPUT_DIR / "A00_OUTPUTS_README.md")' in text
    assert '"output_index": str(OUTPUT_INDEX_DIR / "index.html")' in text
    assert 'A00_LATEST_OUTPUTS.json' in text
    assert 'A00_OUTPUTS_README.md' in text
    assert 'latest_activity_bundle.zip' in text
    assert 'latest_report_evidence_bundle.zip' in text
    assert '"22. Saving full Activity log and /kaggle/working output index"' in text
    assert "function downloadVisibleActivityLog()" in text
    assert "Download visible Activity" in text
    assert "function jobArtifactLinks(job)" in text
    assert "function activityArtifactLinks(job)" in text
    assert "Download activity ZIP" in text


def test_a00_batch_runs_flush_prompt_checkpoints_for_long_kaggle_runs() -> None:
    text = _a00_text()
    assert "checkpoint_every: int = 1" in text
    assert "def _load_latest_incomplete_run_checkpoint(" in text
    assert 'RUN_DIR.glob(f"a00_{run_slug}_*.json")' in text
    assert 'if bundle.get("status") == "completed":' in text
    assert "resume_bundle, resume_path = _load_latest_incomplete_run_checkpoint(run_slug, prompt_set, req.harness_profile)" in text
    assert '"status": status' in text
    assert '"completed_prompts": len(ordered_results)' in text
    assert '"resume_note": "Rerun the same run label, prompt set, and harness profile to continue an unfinished prompt batch."' in text
    assert '"prompt_index": prompt_index' in text
    assert 'if prompt_index in completed_indices:' in text
    assert 'dc_log("a00.batch.checkpoint"' in text
    assert 'bundle = checkpoint_bundle("completed", len(prompts) + 1)' in text
