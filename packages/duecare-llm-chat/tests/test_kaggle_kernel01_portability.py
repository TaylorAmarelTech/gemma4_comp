from __future__ import annotations

import ast
import re
from pathlib import Path


REPO = Path(__file__).parents[3]
KERNEL_DIR = REPO / "kaggle" / "01-duecare-exploration-workbench"
KERNEL = KERNEL_DIR / "kernel.py"
README = KERNEL_DIR / "README.md"
PORTABILITY_AUDIT = KERNEL_DIR / "PORTABILITY_AUDIT.md"
WHEELS = KERNEL_DIR / "wheels"
A00_KERNEL = REPO / "kaggle" / "A-00-omni-experiment-workbench" / "kernel.py"
LIVE_DEMO_KERNEL = REPO / "kaggle" / "02-live-demo" / "kernel.py"
GEMMA4_RUNTIME = REPO / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "gemma4_runtime.py"
MODEL_LOADING_TRACE = REPO / "docs" / "model_loading_trace.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _main_kernel_paths() -> list[Path]:
    return [
        REPO / "kaggle" / "01-duecare-exploration-workbench" / "kernel.py",
        REPO / "kaggle" / "02-live-demo" / "kernel.py",
        *sorted((REPO / "kaggle").glob("A-*/kernel.py")),
    ]


def test_kernel01_declares_reusable_runtime_contract():
    from duecare.chat.portability import REQUIRED_APP_ENDPOINTS, REQUIRED_SAMPLE_FILES

    text = _text(KERNEL)
    assert 'DUECARE_REQUIRED_CHAT_VERSION", REQUIRED_CHAT_VERSION' in text
    assert "verify_app_contract" in text
    assert "SELF_AUDIT_MINIMUM_COUNTS" in text
    assert "_verify_portable_app_contract(app)" in text
    assert "DUECARE_REQUIRED_APP_ENDPOINTS = (" not in text
    assert "DUECARE_REQUIRED_SAMPLE_FILES = (" not in text
    assert "DUECARE_REQUIRED_KO_TYPES =" not in text

    for endpoint in [
        "/api/audit/workbench-inventory",
        "/api/portability",
        "/api/experiment-contract",
        "/api/knowledge/type-catalog",
        "/api/harnesses",
        "/api/knowledge/import",
        "/api/knowledge/export",
        "/api/process/batch/start",
        "/api/process/batch/status/{job_id}",
        "/api/process/graph-extract/start",
        "/api/process/graph-extract/status/{job_id}",
        "/api/search/sanitize",
        "/api/anonymize",
    ]:
        assert endpoint in REQUIRED_APP_ENDPOINTS
        assert endpoint not in text

    for sample in [
        "sample_manifest.json",
        "case_files_streamlined_demo.zip",
        "case_files_media_rich_sample.zip",
        "knowledge_files_sample.zip",
        "knowledge_source_examples_sample.zip",
        "search_intake_examples_sample.zip",
        "prompt_eval_training_seed_sample.zip",
    ]:
        assert sample in REQUIRED_SAMPLE_FILES
        assert sample not in text


def test_kernel01_readme_and_audit_explain_next_notebook_reuse():
    readme = _text(README)
    audit = _text(PORTABILITY_AUDIT)

    assert "Portability contract for the next notebooks" in readme
    assert "PORTABILITY_AUDIT.md" in readme
    assert "Kernel 01 Portability Audit" in audit
    assert "duecare.chat.portability" in audit
    assert "portability_contract_payload" in audit
    assert "verify_app_contract" in audit
    assert "02 Live Demo" in audit
    assert "A-00 Omni Experiment Workbench" in audit
    assert "Archived Appendix Notebooks" in audit

    for primitive in [
        "Workbench inventory endpoint",
        "Knowledge type catalog",
        "Sample manifest",
        "Harness surface contracts",
        "Async job contract",
        "Graph edge schema",
        "Model fit profile",
        "Trust-boundary vocabulary",
        "Activity log primitive",
        "Import/export envelope contract",
    ]:
        assert primitive in audit


def test_kernel01_documents_stale_fallback_wheel_risk_until_rebuilt():
    audit = _text(PORTABILITY_AUDIT).lower()
    wheel_names = [p.name for p in WHEELS.glob("duecare_llm_chat-*.whl")]
    has_required_wheel = any("duecare_llm_chat-0.17.0-" in name for name in wheel_names)

    assert has_required_wheel
    assert "publish the refreshed" in audit
    assert "0.17.0" in audit


def test_core_wheel_metadata_is_not_stale_v014_copy():
    for metadata_path in [
        REPO / "kaggle" / "01-duecare-exploration-workbench" / "wheels" / "dataset-metadata.json",
        REPO / "kaggle" / "02-live-demo" / "wheels" / "dataset-metadata.json",
    ]:
        text = _text(metadata_path)
        assert "v0.17.0" in text
        assert "v0.14.5 / chat-package 0.14.5" not in text
        assert "/api/portability" in text or "portability" in text.lower()


def test_appendix_kernels_default_to_current_duecare_version():
    stale: list[str] = []
    for kernel in sorted((REPO / "kaggle").glob("A-*/kernel.py")):
        text = _text(kernel)
        if 'DUECARE_VERSION = "0.1.0"' in text or 'DUECARE_VERSION    = "0.1.0"' in text:
            stale.append(str(kernel.relative_to(REPO)))
    assert stale == []


def test_a00_uses_shared_experiment_contracts():
    a00 = _text(A00_KERNEL)

    for token in [
        "experiment_contract_payload",
        "harness_profile_map",
        "quantitative_run_profile_map",
        "synthetic_generation_profile_map",
        "training_profile_map",
        "/api/a00/experiment-contract",
        "/api/a00/quantitative/run",
        "bulk_text_25",
        "tiny_lora_smoke",
        "QuantitativeProfileRequest",
    ]:
        assert token in a00


def test_live_demo_and_a00_expose_page_level_controls():
    live = _text(LIVE_DEMO_KERNEL)
    a00 = _text(A00_KERNEL)

    for token in [
        "/api/portability",
        "/api/experiment-contract",
        "/api/shutdown",
        "Entity graph (demo)",
        "/api/query",
        "/api/moderate",
        "/api/worker_check",
        "_dc-runtime-topbar",
        "runtime_model_topbar_html",
        "runtime-model-select",
        "/api/live/model-presets",
        "/api/live/model/load",
        "Gemma4Runtime",
        "load_gemma_shared",
        "load_gemma_unsloth delegates to shared Gemma4Runtime",
        "load_gemma_smart delegates to shared Gemma4Runtime",
    ]:
        assert token in live
    assert "FastModel.from_pretrained(" not in live
    assert "AutoModelForCausalLM" not in live
    assert "AutoModelForImageTextToText" not in live
    assert "p.label + ' - ' + (p.notes || p.ref || '')" not in live
    assert "p.label || p.ref || 'Gemma 4 model'" in live

    for token in [
        "Quantitative profile",
        'id="quant-profile"',
        "runQuantProfile",
        "/api/a00/quantitative/run",
        "Quality gates and notebook audit",
        "Activity",
    ]:
        assert token in a00


def test_a00_uses_focused_experiment_console_not_exploration_nav():
    a00 = _text(A00_KERNEL)
    homepage = a00.split('HOMEPAGE_HTML = r"""', 1)[1].split('"""', 1)[0]

    assert "_nav.js" not in homepage
    assert 'data-nav="tools"' not in homepage
    assert "DueCare hub" not in homepage
    assert "Harness Comparison" not in homepage
    assert "Bulk File Review" not in homepage
    assert "Knowledge Extraction" not in homepage
    assert "Benchmark, generate, fine-tune, compare." in homepage
    assert "Preconfigured Harness, Training, and Evaluation" in homepage
    assert "runPreconfiguredPipeline" in homepage
    assert "preconfig-progress" in homepage
    assert "__A00_SHUTDOWN_CONTROL__" in homepage
    assert "_A00_SHUTDOWN_CONTROL_HTML" in a00
    assert "runtime_model_topbar_html" not in a00
    assert '${p.label || p.ref} | ${p.notes || ""}' not in a00
    assert "p.label || p.ref}</option>" in a00
    assert "Model: dry run" not in homepage
    assert "Start with dry-run outputs" not in homepage
    assert "body.a00-landing .a00-choice-controls" in homepage
    assert 'id="preconfig-model"' in homepage
    assert 'id="preconfig-limit" type="number" min="1" max="50" value="4"' in homepage
    assert "preconfig-synth-count" not in homepage
    assert "preconfig-execute" not in homepage
    assert 'id="preconfig-run-btn"' in homepage
    assert "Static settings used for this run" in homepage
    assert "body.a00-landing .a00-static-settings" in homepage
    assert "Combined rule-based score plus LLM judge" in homepage
    assert "openStartCard('/preconfigured'" in homepage
    assert "openStartCard('/custom'" in homepage
    assert "Open custom controls" not in homepage
    assert "Build report from selected runs" not in homepage
    assert "Load model</button>" not in homepage
    assert "unloadModel()" not in homepage
    assert "runtime-model-select" not in a00
    assert "runtime-model-modal" not in a00
    assert "runtime-model-button" not in a00
    assert "body.a00-custom .primary-grid { display: grid; }" in homepage
    assert re.search(r"(?m)^\s*\.primary-grid\s*\{\s*display:\s*grid;", homepage) is None
    assert "__A00_SMALL_MODEL_REF__" in homepage
    assert "a00-landing" in a00
    assert "A00_PRECONFIGURED_HTML" in a00
    assert '"/preconfigured"' in a00
    assert '"/custom"' in a00
    assert "normal Gemma plus rules combined mode" in homepage
    assert 'harness_profile: "chat_no_online"' in homepage
    assert 'baseline_harness_profile: "none"' in homepage
    assert 'prompt_set: $("pipeline-prompt-set").value || $("prompt-set").value' in homepage
    assert "synthetic_count: synth" in homepage
    assert 'generator_mode: "rubric_polisher"' in homepage
    assert "evaluate_outputs: true" in homepage
    assert "include_report: true" in homepage
    assert "execute_training: execute" in homepage
    assert "llm_judge: true" in homepage
    assert "no internet/import" in homepage
    assert "A guided pipeline is running, so model loading is owned by that job" in a00
    assert "Pipeline already running" in a00
    assert "lastJobStepCount" in homepage
    assert "Refresh status" not in homepage
    assert "Checking if any model is currently loaded" in a00
    assert "Evaluating responses using combined rule + LLM judge" in a00
    assert "Fine-tuning failed; review training log" in a00
    assert "torch.cuda.is_bf16_supported" in a00
    assert "The selected model loads automatically" in homepage
    assert "selectedModelPayload" in homepage
    assert "auto_load_model: bool = True" in a00
    assert "_ensure_model_loaded_for_run" in a00
    assert "Pipeline running" in homepage
    assert "not loaded:" not in homepage
    assert "a00-shutdown-control" in homepage
    assert "grade_response_combined" in a00
    assert "grade_response_universal" in a00
    assert "Advanced model-switching pipeline" in homepage
    assert "Appendix workflow registry" in homepage


def test_shared_gemma_runtime_uses_gemma4_message_content_blocks():
    runtime = _text(GEMMA4_RUNTIME)
    assert "def _normalise_messages" in runtime
    assert '"content"] = [{"type": "text", "text": content}]' in runtime
    assert "tokenizer.apply_chat_template(" in runtime
    assert "FastModel.from_pretrained(" in runtime
    assert "full_finetuning=False" in runtime
    assert "device_map = \"balanced\"" in runtime
    assert "heartbeat #" in runtime
    assert "top_p=top_p" in runtime
    assert "top_k=top_k" in runtime
    assert "dealignai/Gemma-4-31B-JANG_4M-CRACK" in runtime


def test_kernel01_delegates_local_model_loading_to_shared_fastmodel_runtime():
    text = _text(KERNEL)
    assert "from duecare.chat.gemma4_runtime import Gemma4LoadSpec, Gemma4Runtime" in text
    assert "Gemma4Runtime(log=_runtime_log).load(Gemma4LoadSpec(" in text
    assert "shared FastModel runtime FAILED" in text
    assert "FastModel.from_pretrained(" not in text.split("def load_gemma() -> Optional[LoadedModel]:", 1)[1].split("# ===========================================================================\n# 3.", 1)[0]


def test_model_loading_trace_documents_the_shared_fastmodel_path():
    doc = _text(MODEL_LOADING_TRACE)
    for token in [
        "Gemma4Runtime",
        "FastModel.from_pretrained",
        'device_map="balanced"',
        "01 exploration workbench",
        "02 live demo",
        "A-00 preconfigured experiment",
        "FastModel.get_peft_model",
        "train_on_responses_only",
        "transformers==5.5.0",
    ]:
        assert token in doc


def test_primary_kernels_bootstrap_from_github_source_with_full_package_closure():
    """Kaggle users copy/paste kernels; the kernels must not assume local
    packages or partial release wheels are already available."""
    live = _text(LIVE_DEMO_KERNEL)
    a00 = _text(A00_KERNEL)

    required_packages = [
        "duecare-llm-core",
        "duecare-llm-models",
        "duecare-llm-domains",
        "duecare-llm-tasks",
        "duecare-llm-agents",
        "duecare-llm-workflows",
        "duecare-llm-publishing",
        "duecare-llm-evidence-db",
        "duecare-llm-engine",
        "duecare-llm-nl2sql",
        "duecare-llm-research-tools",
        "duecare-llm-benchmark",
        "duecare-llm-server",
        "duecare-llm-cli",
        "duecare-llm-training",
        "duecare-llm-chat",
    ]
    required_imports = [
        "duecare.server",
        "duecare.cli",
        "duecare.training",
        "duecare.chat",
    ]

    for label, text in {"02-live-demo": live, "A-00": a00}.items():
        assert "one git clone, local package install, import verification" in text, label
        assert "git\", \"clone" in text, label
        assert "DUECARE_SOURCE_ROOT" in text, label
        assert "_duecare_source" in text, label
        assert "--disable-pip-version-check" in text, label
        assert "installed_from_github_source" in text or "installed and verified" in text, label
        for package in required_packages:
            assert package in text, f"{label} missing {package}"
        for module in required_imports:
            assert module in text, f"{label} does not verify {module}"


def test_primary_browser_kernels_fail_loudly_without_public_tunnel():
    """READY without a usable Cloudflare URL is misleading on Kaggle."""
    for path in [LIVE_DEMO_KERNEL, A00_KERNEL]:
        text = _text(path)
        rel = str(path.relative_to(REPO))
        assert "DUECARE_ALLOW_LOCAL_ONLY" in text, rel
        assert "requires a public Cloudflare URL on Kaggle" in text, rel
        assert "raise SystemExit" in text, rel


def test_next_notebooks_inherit_reusable_contracts_without_redeclaring_lists():
    appendix_kernels = sorted((REPO / "kaggle").glob("A-*/kernel.py"))
    assert appendix_kernels

    missing_runtime_contract: list[str] = []
    redeclared_contract_lists: list[str] = []
    for kernel in [LIVE_DEMO_KERNEL, *appendix_kernels]:
        text = _text(kernel)
        rel = str(kernel.relative_to(REPO))
        uses_shared_runtime = (
            "build_minimal_shell" in text
            or "duecare.chat.app import create_app" in text
            or "from duecare.server import create_app" in text
            or "/api/portability" in text
            or "reference_portability_contract_payload" in text
        )
        if not uses_shared_runtime:
            missing_runtime_contract.append(rel)
        for marker in [
            "DUECARE_REQUIRED_APP_ENDPOINTS = (",
            "DUECARE_REQUIRED_SAMPLE_FILES = (",
            "DUECARE_REQUIRED_KO_TYPES =",
        ]:
            if marker in text:
                redeclared_contract_lists.append(f"{rel}: {marker}")

    assert missing_runtime_contract == []
    assert redeclared_contract_lists == []

    shell = _text(REPO / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "kernel_shell.py")
    assert "/api/portability" in shell
    assert "/api/experiment-contract" in shell


def test_all_main_kernels_are_plain_utf8_parseable_and_repo_portable():
    local_path_pattern = re.compile(
        r"(?:C:[\\/]|OneDrive|\\Users\\|/Users/|/home/[A-Za-z0-9_.-]+|/mnt/[A-Za-z0-9_.-]+)"
    )
    failures: list[str] = []

    for kernel in _main_kernel_paths():
        rel = str(kernel.relative_to(REPO))
        raw = kernel.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            failures.append(f"{rel}: UTF-8 BOM present")
            continue
        text = raw.decode("utf-8")
        try:
            ast.parse(text, filename=rel)
        except SyntaxError as exc:
            failures.append(f"{rel}: syntax {exc.lineno}:{exc.offset} {exc.msg}")
        if local_path_pattern.search(text):
            failures.append(f"{rel}: local absolute path leaked")

    assert failures == []
