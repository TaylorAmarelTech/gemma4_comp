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
EXPERIMENT_CONTRACTS = ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "experiment_contracts.py"


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
        'benchmark_max_new_tokens: int = A00_BENCHMARK_MAX_NEW_TOKENS',
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


def test_a00_benchmark_response_budget_has_headroom() -> None:
    """Benchmark answer generation needs more room than the old smoke
    budget. This is separate from the 16K input context and the 2048
    structured judge output budget."""
    text = _a00_text()
    contracts = EXPERIMENT_CONTRACTS.read_text(encoding="utf-8")
    assert "BENCHMARK_RESPONSE_MAX_NEW_TOKENS = 900" in contracts
    assert '"max_new_tokens": BENCHMARK_RESPONSE_MAX_NEW_TOKENS' in contracts
    assert (
        'A00_BENCHMARK_MAX_NEW_TOKENS = int(os.environ.get('
        in text
    )
    assert '"DUECARE_A00_BENCHMARK_MAX_NEW_TOKENS"' in text
    assert "benchmark_max_new_tokens: int = A00_BENCHMARK_MAX_NEW_TOKENS" in text
    assert "max_new_tokens=req.benchmark_max_new_tokens" in text
    assert "benchmark_generation_settings" in text
    assert '"benchmark_max_new_tokens": req.benchmark_max_new_tokens' in text
    assert 'benchmark_max_new_tokens: Number("__A00_BENCHMARK_MAX_NEW_TOKENS__")' in text
    assert '.replace("__A00_BENCHMARK_MAX_NEW_TOKENS__", str(A00_BENCHMARK_MAX_NEW_TOKENS))' in text
    assert 'generation.get("max_new_tokens", 420)' not in text


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
    assert "def traced_model_call(prompt: str) -> str:" in text
    assert '"judge_prompt": prompt' in text
    assert '"judge_response": judge_response' in text
    assert 'normalised["judge_call"] = judge_call_trace' in text


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
    assert 'activity_job_id: str = ""' in text
    assert 'activity_label: str = ""' in text
    assert "def append_batch_activity(label: str, status: str, detail: dict[str, Any]) -> None:" in text
    assert 'f"{activity_label}: sending prompt {prompt_index} of {len(prompts)}"' in text
    assert 'f"{activity_label}: completed prompt {prompt_index} of {len(prompts)}"' in text
    assert 'f"{activity_label}: checkpoint saved after prompt {prompt_index} of {len(prompts)}"' in text
    assert '"generation_settings": {' in text
    assert '"raw_prompt": row.get("prompt", "")' in text
    assert '"model_prompt_sent_to_gemma": row.get("model_prompt", "")' in text
    assert '"response": row.get("response", "")' in text
    assert '"prompt_sha256": prompt_sha' in text
    assert '"response_sha256": _sha256_text(response)' in text
    assert '"requested_max_new_tokens": int(max_new_tokens)' in text
    assert '"prompt_response_pairs": pairs' in text
    assert '"model_prompt": model_prompt' in text
    assert '"sample_sft_rows": sft_rows[: min(10, len(sft_rows))]' in text
    assert 'el.textContent = `[${stamp}] ${summary}${detail}\\n\\n` + (el.textContent || "");' in text
    assert "slice(0, 18000)" not in text
    assert ".slice(-8).map" not in text


def test_a00_synthetic_generation_exposes_source_scope_and_audit() -> None:
    """Synthetic training rows must clearly say what knowledge sources
    were used. A-00 should not imply that raw IOM/UN/court/PDF corpora
    were freshly digested unless they were imported as packs/documents."""
    text = _a00_text()
    assert "GREP_RULES as _shared_grep_rules" in text
    assert "RAG_CORPUS as _shared_rag_corpus" in text
    assert "_TOOL_DISPATCH as _shared_tool_dispatch" in text
    assert "def _synthetic_source_scope() -> dict[str, Any]:" in text
    assert '"raw_publication_ingestion_by_default": False' in text
    assert "Raw IOM, UN, international human-rights, court, or jurisdictional publications are not digested" in text
    assert "def _trace_source_grounding(prompt_id: str, trace: dict[str, Any]) -> dict[str, Any]:" in text
    assert '"source_grounding": grounding' in text
    assert 'source_audit_path = TRAIN_DIR / f"{base_id}_source_audit.json"' in text
    assert '"schema_version": "duecare.a00.synthetic.source_audit.v1"' in text
    assert '"source_scope": source_scope' in text
    assert '"source_audit_summary": source_audit_summary' in text
    assert '"source_scope": _synthetic_source_scope()' in text
    assert '"source_audit": str(source_audit_path)' in text
    assert "source_audit_path, manifest_path" in text
    assert "Raw IOM, UN, court, statute, or PDF corpora influence training only after they are imported" in text
    assert "The schema is flexible enough for full documents, PDF-derived page chunks" in text


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


def test_a00_external_judge_factories_preserve_provider_routing_contract() -> None:
    """A-00 must keep its external judge factories alongside the local
    Gemma judge so reviewers can run Anthropic / Ollama / Ollama-cloud
    judging when credentials are present, and the privacy-note + audit
    trail must travel with the configuration step.

    Hand-rolled HTTP is acceptable today; the contract pinned here is
    the dispatch surface and privacy disclosure, not the request body.
    """
    text = _a00_text()
    for marker in (
        "def _is_ollama_judge_source(source: str) -> bool:",
        "def _is_ollama_cloud_source(source: str) -> bool:",
        "def _is_anthropic_judge_source(source: str) -> bool:",
        "def _is_external_judge_source(source: str) -> bool:",
        "def _ollama_model_call_factory(",
        "def _anthropic_model_call_factory(",
        "def _configure_ollama_judge_for_pipeline(",
        "def _configure_anthropic_judge_for_pipeline(",
        "def _configure_external_judge_for_pipeline(",
    ):
        assert marker in text, marker
    assert "Ollama Cloud judge requires Kaggle Secret or environment variable OLLAMA_API_KEY" in text
    assert "Anthropic judge requires Kaggle Secret or environment variable ANTHROPIC_API_KEY" in text
    assert "Final grading sends benchmark prompts, model responses, and harness traces to Ollama." in text
    assert "Final grading sends benchmark prompts, model responses, and harness traces to Anthropic." in text
    assert "if _is_anthropic_judge_source(req.judge_model_source):" in text
    assert "_configure_external_judge_for_pipeline(job_id, req)" in text


def test_a00_external_judge_keeps_local_default_runnable_without_credentials() -> None:
    """The competition default must not require any paid API key. Local
    Gemma judging stays the default when judge_model_source is hf or
    empty."""
    text = _a00_text()
    assert 'judge_model_source: str = "hf"' in text
    assert 'return _is_ollama_judge_source(source) or _is_anthropic_judge_source(source)' in text
    assert 'STATE["judge_model_call"] = ' in text


def test_process_and_extraction_harnesses_declare_local_gemma_default_target() -> None:
    """The chat harness has a specific model-target pin in
    test_harness_universal_model_contract.py. Process and extraction
    should be equivalently pinned so a spec drift cannot quietly drop
    their local Gemma 4 default target.

    This test imports the harness modules and walks `spec.model_targets`
    so a regression that moved `default=True` off the local Gemma
    target and onto a frontier target (a real privacy risk for the
    default proof path) would actually trip the assertion.
    """
    from duecare.chat.harnesses import extraction as extraction_module
    from duecare.chat.harnesses import process as process_module

    for module in (process_module, extraction_module):
        targets = list(module.spec.model_targets)
        assert targets, module.name
        defaults = [t for t in targets if getattr(t, "default", False)]
        assert defaults, f"{module.name} must declare a default model target"
        # The default target must be local — never a credential-required
        # external target — so the competition default stays runnable
        # without paid API keys and without raw prompts leaving the
        # kernel.
        for default_target in defaults:
            assert default_target.transport in {"gemma4_runtime", "none"}, (
                module.name,
                default_target.id,
                default_target.transport,
            )
            assert default_target.trust_boundary == "local", (
                module.name,
                default_target.id,
                default_target.trust_boundary,
            )
        # At least one local Gemma 4 target must remain available even
        # if it is not the default (e.g. extraction prefers the
        # deterministic skeleton by default but should still offer the
        # local Gemma drafter as an option).
        local_gemma_targets = [t for t in targets if t.transport == "gemma4_runtime"]
        assert local_gemma_targets, (
            f"{module.name} must keep a gemma4_runtime model target so "
            "Kernel 01 parity stays possible when a real model is loaded"
        )


def test_a00_external_judge_factories_compile_without_runtime_deps() -> None:
    """Static smoke: A-00 kernel.py must compile cleanly. The Anthropic
    and Ollama factories only need `requests` at call time, not at
    import time."""
    import py_compile
    target = ROOT / "kaggle" / "A-00-omni-experiment-workbench" / "kernel.py"
    py_compile.compile(str(target), doraise=True)


def test_format_shared_tool_call_dispatches_by_tool_name() -> None:
    """The tool-result renderer must surface useful fields per tool,
    not fall through to a truncated JSON dump. Each of the five
    deterministic tools from duecare.chat.harness has a distinct result
    schema; this test pins that the dispatch covers all five so a Gemma
    4 prompt sees `statute=...`, ILO indicators, NGO hotlines, and
    convention articles instead of `{...}` blobs."""
    text = _a00_text()
    pieces = text.split("def _format_shared_tool_call(call: dict[str, Any]) -> str:", 1)
    assert len(pieces) == 2, "_format_shared_tool_call not found"
    body, _rest = pieces[1].split("\ndef ", 1)
    for tool_name in (
        "lookup_corridor_fee_cap",
        "lookup_fee_camouflage",
        "lookup_ilo_indicator",
        "lookup_ngo_intake",
        "lookup_ilo_convention",
    ):
        assert f'if name == "{tool_name}":' in body, tool_name
    # The corridor-fee-cap branch must surface statute. Earlier
    # versions silently dropped this critical field.
    assert "f\"statute={result.get('statute')}\"" in body
    # ILO conventions need title + year + key articles for a citation
    # cross-check.
    assert '"title"' in body
    assert '"year"' in body
    assert "key_articles" in body
    # NGO intake must surface at least 3 contact rows, not just one.
    assert "hotlines[:3]" in body
    # Unknown tools fall through to a generic-key extractor so future
    # tools degrade gracefully.
    assert "generic_keys = (" in body


def test_a00_tools_layer_always_emits_trace_for_consistency() -> None:
    """When the tools layer is enabled, trace["tools"] must always be
    present — even when shared tools returned zero calls and the
    heuristic did not match. Otherwise a reviewer cannot distinguish a
    disabled layer from a no-op pass.

    The tools_had_error flag is tracked independently of tools_source
    so a heuristic recovery does not silently hide a shared failure.
    """
    text = _a00_text()
    pieces = text.split("def _build_harness_prompt(row: dict[str, Any], harness_profile: str) -> tuple[str, dict[str, Any]]:", 1)
    assert len(pieces) == 2, "_build_harness_prompt not found"
    body, _rest = pieces[1].split("\ndef ", 1)
    # The trace["tools"] dict is built once at the end of the tools
    # branch, not conditionally on whether notes are non-empty.
    assert "trace[\"tools\"] = tools_trace" in body
    # Source markers cover every real state, including the explicit
    # mixed state where heuristic recovered after a shared failure.
    assert 'tools_source = "skipped"' in body
    assert 'tools_source = "shared" if tool_notes else "shared_empty"' in body
    assert 'tools_source = "shared_error"' in body
    assert 'tools_source = "heuristic_after_shared_error" if tools_had_error else "heuristic"' in body
    # Independent error tracking so heuristic recovery cannot hide a
    # shared failure from step status.
    assert "tools_had_error = False" in body
    assert "tools_had_error = True" in body
    assert "if tools_had_error:" in body
    # Step status differentiates pass vs noop so reviewers can grep
    # the trace for fires. Degraded fires whenever shared raised, even
    # if the heuristic recovered.
    assert '"pass" if tool_notes else "noop"' in body
    assert '"status": "degraded"' in body


def test_a00_inference_uses_at_least_16k_context_window() -> None:
    """The combined rule + LLM judge runs over (prompt + response +
    17-dimension rubric + harness trace + JSON instructions), which can
    easily exceed 4096 tokens for a real benchmark row. A-00 must load
    the shared Gemma 4 runtime with at least a 16K context so grading
    and full-harness benchmark prompts are not silently truncated.

    The training script keeps a separate, intentionally tighter
    max_seq_length on the smoke LoRA profile; this test only pins the
    inference loading path.
    """
    text = _a00_text()
    # The dedicated constant must exist with an env override.
    assert 'A00_INFERENCE_MAX_SEQ_LENGTH = int(os.environ.get("DUECARE_A00_INFERENCE_MAX_SEQ_LENGTH", "16384"))' in text
    # _load_model_runtime must pass the constant, not the training default.
    pieces = text.split("def _load_model_runtime(req: ModelLoadRequest) -> dict[str, Any]:", 1)
    assert len(pieces) == 2, "_load_model_runtime not found"
    body, _rest = pieces[1].split("\ndef ", 1)
    assert "max_seq_length=A00_INFERENCE_MAX_SEQ_LENGTH" in body, (
        "Inference must load at the 16K constant, not the training profile fallback."
    )
    assert 'max_seq_length=int(A00_TRAINING_DEFAULT.get("max_seq_length", 4096))' not in body, (
        "Old 4096 training fallback must not be reachable from the inference loader."
    )
    # Defensive parse: the default literal must be at least 16384 so a
    # future contributor who tweaks the constant cannot silently drop
    # below grading context needs.
    pieces2 = text.split('A00_INFERENCE_MAX_SEQ_LENGTH = int(os.environ.get("DUECARE_A00_INFERENCE_MAX_SEQ_LENGTH", "', 1)
    assert len(pieces2) == 2, "constant default literal not found"
    default_literal = pieces2[1].split('"', 1)[0]
    assert int(default_literal) >= 16384, (
        f"A00_INFERENCE_MAX_SEQ_LENGTH default {default_literal} must be at least 16384."
    )


def test_a00_combined_judge_has_structured_output_budget() -> None:
    """The combined LLM judge must have enough output budget to emit
    structured rubric JSON with per-dimension scores and rationales.
    A short generation cap can silently truncate JSON and depress
    scores, especially after the 16K input-context expansion enabled
    fuller prompts, responses, and traces.
    """
    text = _a00_text()
    assert (
        'A00_COMBINED_JUDGE_MAX_NEW_TOKENS = int(os.environ.get("DUECARE_A00_COMBINED_JUDGE_MAX_NEW_TOKENS", "2048"))'
        in text
    )
    pieces = text.split(
        'A00_COMBINED_JUDGE_MAX_NEW_TOKENS = int(os.environ.get("DUECARE_A00_COMBINED_JUDGE_MAX_NEW_TOKENS", "',
        1,
    )
    assert len(pieces) == 2, "combined judge token-budget constant not found"
    default_literal = pieces[1].split('"', 1)[0]
    assert int(default_literal) >= 2048, (
        f"A00_COMBINED_JUDGE_MAX_NEW_TOKENS default {default_literal} must be at least 2048."
    )
    assert "max_tokens=A00_COMBINED_JUDGE_MAX_NEW_TOKENS" in text
    assert "max_new_tokens=A00_COMBINED_JUDGE_MAX_NEW_TOKENS" in text
    pieces2 = text.split("def _grading_model_call(row: dict[str, Any]) -> Optional[Any]:", 1)
    assert len(pieces2) == 2, "_grading_model_call not found"
    body, _rest = pieces2[1].split("\ndef ", 1)
    assert "max_new_tokens=900" not in body


def test_a00_grep_and_rag_layers_distinguish_noop_from_evidence() -> None:
    """A zero-hit GREP/RAG pass is materially different from an
    evidence-producing pass. The activity trace should let reviewers
    and report builders tell whether a layer fired, no-oped, or
    degraded after an exception.
    """
    text = _a00_text()
    pieces = text.split("def _build_harness_prompt(row: dict[str, Any], harness_profile: str) -> tuple[str, dict[str, Any]]:", 1)
    assert len(pieces) == 2, "_build_harness_prompt not found"
    body, _rest = pieces[1].split("\ndef ", 1)

    assert '"status": "pass" if hits else "noop"' in body
    assert '"status": "pass" if facts else "noop"' in body
    assert '"layer": "grep", "status": "degraded"' in body
    assert '"layer": "rag", "status": "degraded"' in body


def test_a00_pipeline_supports_ollama_external_judge() -> None:
    """The final LLM judge can use Ollama Cloud/local Ollama without
    loading another local Gemma model. This should affect only the
    grading call path, not the Gemma generation or fine-tuning path."""
    text = _a00_text()
    assert 'A00_OLLAMA_JUDGE_MODEL_REF = os.environ.get("DUECARE_A00_OLLAMA_JUDGE_MODEL_REF", "gpt-oss:20b")' in text
    assert "JUDGE_MODEL_PRESETS = [" in text
    assert '"source": "ollama_cloud"' in text
    assert '<option value="ollama">ollama</option>' in text
    assert '"OLLAMA_API_KEY"' in text
    assert "from duecare.chat.harnesses.model_interface import call_model_backend" in text
    assert "class _OllamaJudgeBackend:" in text
    assert "def _is_ollama_judge_source(source: str) -> bool:" in text
    assert "def _ollama_api_endpoint(source: str) -> str:" in text
    assert "https://ollama.com" in text
    assert "/api/chat" in text
    assert 'headers["Authorization"] = f"Bearer {self.api_key}"' in text
    assert '"format": "json"' in text
    assert "response = call_model_backend(" in text
    assert "_record_external_judge_response(source, model_ref, endpoint, response)" in text
    assert "def _configure_ollama_judge_for_pipeline(job_id: str, req: PipelineRequest) -> dict[str, Any]:" in text
    assert 'STATE["judge_model_call"] = _ollama_model_call_factory(' in text
    assert "external = STATE.get(\"judge_model_call\")" in text
    assert "if callable(external):" in text
    assert "if _is_external_judge_source(req.judge_model_source):" in text
    assert '"18. Configuring Ollama judge for final evaluation"' in text
    assert "External Ollama judge used only for final combined grading" in text
    assert '"ollama_cloud_ready": bool(ollama_key)' in text
    assert "const judgeOptions = (modelPresets.judge_presets || modelPresets.presets || [])" in text
    assert '<option value="ollama_cloud">ollama_cloud</option>' in text


def test_a00_pipeline_supports_anthropic_external_judge() -> None:
    """Claude/Anthropic is an optional final judge provider. It should
    plug into the same judge_model_call hook and must not affect local
    Gemma generation, harnessing, or training."""
    text = _a00_text()
    assert 'A00_ANTHROPIC_JUDGE_MODEL_REF = os.environ.get("DUECARE_A00_ANTHROPIC_JUDGE_MODEL_REF", "claude-opus-4-7")' in text
    assert 'A00_ANTHROPIC_API_URL = os.environ.get("DUECARE_A00_ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")' in text
    assert "Claude Opus 4.7 judge" in text
    assert "Claude Opus 4.6 judge" in text
    assert '"source": "anthropic"' in text
    assert "ANTHROPIC_API_KEY" in text
    assert "def _is_anthropic_judge_source(source: str) -> bool:" in text
    assert "def _is_external_judge_source(source: str) -> bool:" in text
    assert "class _AnthropicJudgeBackend:" in text
    assert "def _anthropic_model_call_factory(" in text
    assert '"x-api-key": self.api_key' in text
    assert '"anthropic-version": self.version' in text
    assert "response = call_model_backend(" in text
    assert "_record_external_judge_response(source, model_ref, endpoint, response)" in text
    assert "def _configure_anthropic_judge_for_pipeline(job_id: str, req: PipelineRequest) -> dict[str, Any]:" in text
    assert "def _configure_external_judge_for_pipeline(job_id: str, req: PipelineRequest) -> dict[str, Any]:" in text
    assert "if _is_anthropic_judge_source(req.judge_model_source):" in text
    assert "STATE[\"judge_model_call\"] = _anthropic_model_call_factory(" in text
    assert '"18. Configuring Anthropic Claude judge for final evaluation"' in text
    assert "External Anthropic Claude judge used only for final combined grading" in text
    assert '"anthropic_ready": bool(anthropic_key)' in text
    assert '<option value="anthropic">anthropic</option>' in text


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
    assert '"grade": row.get("grade", {})' in text


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
    assert "## Artifact Shortcuts" in text
    assert "ARTIFACT SHORTCUTS" in text
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


def test_a00_pipeline_failures_export_traceback_and_troubleshooting_links() -> None:
    text = _a00_text()
    assert "import traceback" in text
    assert "traceback_text = traceback.format_exc()" in text
    assert 'job["traceback"] = traceback_text' in text
    assert '"traceback": traceback_text' in text
    assert '"activity_artifacts": _artifact_links(failed_job.get("activity_artifacts", {}))' in text
    assert '"report_artifacts": _artifact_links((failed_job.get("report") or {}).get("artifacts", {}) if isinstance(failed_job.get("report"), dict) else {})' in text
    assert "Open the activity ZIP or activity JSON for the full step-by-step record." in text
    assert "If the failure happened during judging, inspect the row-level 19. Judging response Activity entry immediately before this error." in text


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
