"""Shared hardening helpers for the DueCare notebook builders."""

from __future__ import annotations

import copy
from typing import Any


DUECARE_VERSION = "0.1.0"

INSTALL_PACKAGES: dict[str, list[str]] = {
    "000_index.ipynb": ["duecare-llm-core==0.1.0"],
    "005_glossary.ipynb": ["duecare-llm==0.1.0"],
    "010_quickstart.ipynb": ["duecare-llm==0.1.0"],
    "100_gemma_exploration.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
        "duecare-llm-tasks==0.1.0",
    ],
    "105_prompt_corpus_introduction.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "110_prompt_prioritizer.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "120_prompt_remixer.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "130_prompt_corpus_exploration.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "140_evaluation_mechanics.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "170_live_context_injection_playground.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
        "duecare-llm-models==0.1.0",
    ],
    "180_multimodal_document_inspector.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
        "duecare-llm-models==0.1.0",
    ],
    "190_rag_retrieval_inspector.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "200_cross_domain_proof.ipynb": ["duecare-llm==0.1.0"],
    "210_oss_model_comparison.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "220_ollama_cloud_comparison.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "230_mistral_family_comparison.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "240_openrouter_frontier_comparison.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "250_comparative_grading.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "260_rag_comparison.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "270_gemma_generations.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "300_adversarial_resistance.ipynb": [
        "duecare-llm-domains==0.1.0",
        "duecare-llm-tasks==0.1.0",
    ],
    "335_attack_vector_inspector.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "340_prompt_factory_visualizer.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
        "duecare-llm-tasks==0.1.0",
    ],
    "310_prompt_factory.ipynb": [
        "duecare-llm-domains==0.1.0",
        "duecare-llm-tasks==0.1.0",
    ],
    "320_supergemma_safety_gap.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "400_function_calling_multimodal.ipynb": [
        "duecare-llm-domains==0.1.0",
        "duecare-llm-tasks==0.1.0",
    ],
    "410_llm_judge_grading.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "420_conversation_testing.ipynb": [
        "duecare-llm-domains==0.1.0",
        "duecare-llm-tasks==0.1.0",
    ],
    "430_rubric_evaluation.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
        "duecare-llm-tasks==0.1.0",
    ],
    "440_per_prompt_rubric_generator.ipynb": ["duecare-llm-core==0.1.0"],
    "450_contextual_worst_response_judge.ipynb": ["duecare-llm-core==0.1.0"],
    "460_citation_verifier.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "500_agent_swarm_deep_dive.ipynb": ["duecare-llm==0.1.0"],
    "510_phase2_model_comparison.ipynb": ["duecare-llm-core==0.1.0"],
    "520_phase3_curriculum_builder.ipynb": ["duecare-llm-core==0.1.0"],
    "525_uncensored_grade_generator.ipynb": ["duecare-llm-core==0.1.0"],
    "527_uncensored_rubric_generator.ipynb": ["duecare-llm-core==0.1.0"],
    "550_ngo_partner_survey_pipeline.ipynb": ["duecare-llm-core==0.1.0"],
    "530_phase3_unsloth_finetune.ipynb": ["duecare-llm-core==0.1.0"],
    "540_finetune_delta_visualizer.ipynb": ["duecare-llm-core==0.1.0"],
    "600_results_dashboard.ipynb": ["duecare-llm-core==0.1.0"],
    "610_submission_walkthrough.ipynb": ["duecare-llm==0.1.0"],
    "620_demo_api_endpoint_tour.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
    "650_custom_domain_walkthrough.ipynb": [
        "duecare-llm-core==0.1.0",
        "duecare-llm-domains==0.1.0",
    ],
}

SUMMARY_MESSAGES: dict[str, str] = {
    "000_index.ipynb": "Index complete. Use the table above to open the next notebook in the DueCare flow.",
    "005_glossary.ipynb": "Glossary review complete. Continue to 010 for the runnable smoke test or 100 for the baseline.",
    "010_quickstart.ipynb": "Quickstart complete. If the imports and smoke test passed, continue to 200 or 500.",
    "100_gemma_exploration.ipynb": "Evaluation complete. Baseline findings are ready in gemma_baseline_findings.json.",
    "105_prompt_corpus_introduction.ipynb": "Corpus introduction complete. Continue to 110 to see how the highest-value prompts are selected, or to 130 for the full per-grade walkthrough.",
    "110_prompt_prioritizer.ipynb": "Prompt prioritization complete. Continue to 120 or 100 with the curated prompt slice.",
    "120_prompt_remixer.ipynb": "Prompt remixing complete. Use the remixed prompts in 100 or 310.",
    "130_prompt_corpus_exploration.ipynb": "Corpus exploration complete. Continue to 140 to see how every scored claim in the suite is actually measured.",
    "140_evaluation_mechanics.ipynb": "Mechanics explainer ready. Every downstream score now has a transparent derivation; continue to 299 or to 100 to see the baseline in action.",
    "170_live_context_injection_playground.ipynb": "Context-injection playground complete. Compare plain / RAG / guided outputs above; continue to 199 or to 260 for the full cross-model RAG comparison.",
    "180_multimodal_document_inspector.ipynb": "Multimodal document inspection complete. The extracted fields + indicator flags above are the evidence for Gemma 4's multimodal claim; continue to 199 or to 400 for the full function-calling + multimodal story.",
    "190_rag_retrieval_inspector.ipynb": "RAG retrieval inspection complete. The retrieval provenance is what 260 consumes; continue to 260 for the full comparison or to 299 to close the section.",
    "200_cross_domain_proof.ipynb": "Cross-domain proof complete. Review the workflow runs above, then continue to 500.",
    "210_oss_model_comparison.ipynb": "Evaluation complete. Review the charts above for Gemma versus peer open-source models.",
    "220_ollama_cloud_comparison.ipynb": "Evaluation complete. Review the Ollama Cloud comparison above and re-run with OLLAMA_API_KEY for live results.",
    "230_mistral_family_comparison.ipynb": "Evaluation complete. Review the Mistral comparison above and re-run with MISTRAL_API_KEY for live results.",
    "240_openrouter_frontier_comparison.ipynb": "Evaluation complete. Review the frontier comparison above and re-run with OPENROUTER_API_KEY for live results.",
    "250_comparative_grading.ipynb": "Comparative grading complete. Review the anchored scores above and continue to 310 or 430.",
    "260_rag_comparison.ipynb": "Evaluation complete. Review the RAG deltas above to decide whether retrieval or fine-tuning should be prioritized.",
    "270_gemma_generations.ipynb": "Generation comparison complete. Review the stacked V3 band chart above and continue to 530 after Phase 3 outputs exist.",
    "300_adversarial_resistance.ipynb": "Adversarial resistance review complete. Continue to 310 for the full prompt factory.",
    "335_attack_vector_inspector.ipynb": "Attack vector inspection complete. The per-vector taxonomy + severity + mitigation status above drive the Phase 3 adversarial curriculum; continue to 499 or to 320 for the safety-line comparison.",
    "340_prompt_factory_visualizer.ipynb": "Prompt-factory visualization complete. The generated-prompt taxonomy, severity distribution, and victim-impact rankings above are the evidence for 310's output quality; continue to 699 or to 440 for per-prompt rubric synthesis.",
    "310_prompt_factory.ipynb": "Prompt factory complete. Review the ranked adversarial prompts above and continue to 430.",
    "320_supergemma_safety_gap.ipynb": "Safety-line analysis complete. Review the gap above before judging or fine-tuning.",
    "400_function_calling_multimodal.ipynb": "Function-calling and multimodal demo complete. Continue to 500 or 610 for the broader system story.",
    "410_llm_judge_grading.ipynb": "LLM-judge grading complete. Review the calibration and gap analysis above, then continue to 420 or 430.",
    "420_conversation_testing.ipynb": "Conversation testing complete. Review the escalation trajectories above and continue to 250.",
    "430_rubric_evaluation.ipynb": "Rubric evaluation complete. Review the failed criteria above before building the Phase 3 curriculum.",
    "440_per_prompt_rubric_generator.ipynb": "Per-prompt rubric generation complete. Review the failure bands above and continue to 450 or 520.",
    "450_contextual_worst_response_judge.ipynb": "Contextual judging complete. Review the discrepancy report above before generating corrections in 520.",
    "460_citation_verifier.ipynb": "Citation verification complete. The real-vs-hallucinated table above is the evidence for the legal-accuracy claim; continue to 499 or to 440 for per-prompt rubric synthesis.",
    "500_agent_swarm_deep_dive.ipynb": "Agent swarm walkthrough complete. Continue to 610 for the compact submission path.",
    "510_phase2_model_comparison.ipynb": "Phase 2 comparison complete. Review the side-by-side results above and decide which model advances to Phase 3.",
    "520_phase3_curriculum_builder.ipynb": "Curriculum build complete. Review phase3_curriculum.jsonl and continue to 530 for fine-tuning.",
    "525_uncensored_grade_generator.ipynb": "Uncensored 5-grade generation complete. Review /kaggle/working/generated_curriculum.jsonl and continue to 530.",
    "527_uncensored_rubric_generator.ipynb": "Uncensored rubric + dimension generation complete. Review /kaggle/working/generated_rubrics/ and continue to 530.",
    "550_ngo_partner_survey_pipeline.ipynb": "NGO survey pipeline complete. Review /kaggle/working/outbound_emails/ drafts manually before sending; ingested responses (if any) merged to ngo_feedback_training.jsonl.",
    "530_phase3_unsloth_finetune.ipynb": "Phase 3 handoff >>> 540 Fine-tune Delta Visualizer https://www.kaggle.com/code/taylorsamarel/duecare-540-finetune-delta-visualizer | 599 Model Improvement Opportunities Conclusion https://www.kaggle.com/code/taylorsamarel/599-duecare-model-improvement-opportunities-conclusion | 600 Results Dashboard https://www.kaggle.com/code/taylorsamarel/600-duecare-results-dashboard",
    "540_finetune_delta_visualizer.ipynb": "Fine-tune delta visualization complete. The before/after plots above are the video-ready Phase 3 evidence; continue to 599 for the section close or to 600 for the full dashboard.",
    "600_results_dashboard.ipynb": "Dashboard review complete. Use the charts above in the video, writeup, or live demo.",
    "610_submission_walkthrough.ipynb": "Submission walkthrough complete. Next: 620 Demo API Endpoint Tour https://www.kaggle.com/code/taylorsamarel/620-duecare-demo-api-endpoint-tour | 650 Custom Domain Walkthrough https://www.kaggle.com/code/taylorsamarel/650-duecare-custom-domain-walkthrough | 899 Solution Surfaces Conclusion https://www.kaggle.com/code/taylorsamarel/duecare-solution-surfaces-conclusion",
    "620_demo_api_endpoint_tour.ipynb": "API endpoint tour complete. The 12 endpoints above are what the FastAPI demo exposes; continue to 650 for the custom-domain walkthrough or to 899 for the section close.",
    "650_custom_domain_walkthrough.ipynb": "Custom-domain walkthrough complete. The medical_misinformation pack above is the concrete adopter story; continue to 899 for the section close or back to 000 for the index.",
}

LEGACY_TEXT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("NB 00a", "NB 110"),
    ("NB 00b", "NB 120"),
    ("NB 00", "NB 100"),
)


def make_markdown_cell(text: str) -> dict[str, Any]:
    return {
        "cell_type": "markdown",
        "metadata": {"language": "markdown"},
        "source": text.splitlines(keepends=True),
    }


def make_code_cell(text: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"language": "python"},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def _source_text(cell: dict[str, Any]) -> str:
    source = cell.get("source", [])
    if isinstance(source, list):
        return "".join(source)
    return str(source)


def _normalize_text(text: str) -> str:
    normalized = text
    for old, new in LEGACY_TEXT_REPLACEMENTS:
        normalized = normalized.replace(old, new)
    return normalized


def _normalize_cell(cell: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(cell)
    metadata = normalized.setdefault("metadata", {})
    language = "markdown" if normalized.get("cell_type") == "markdown" else "python"
    metadata.setdefault("language", language)
    if normalized.get("cell_type") == "code":
        normalized.setdefault("execution_count", None)
        normalized.setdefault("outputs", [])
    normalized["source"] = _normalize_text(_source_text(normalized)).splitlines(keepends=True)
    return normalized


def _looks_like_install_cell(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "!pip install",
            "pip install",
            "duecare-llm-wheels",
            "import duecare.core",
            "duecare-llm==",
            "duecare-llm-core==",
        )
    )


def _install_packages_for(filename: str) -> list[str]:
    return INSTALL_PACKAGES.get(filename, [f"duecare-llm-core=={DUECARE_VERSION}"])


def _make_install_cell(filename: str) -> dict[str, Any]:
    packages = _install_packages_for(filename)
    return make_code_cell(
        "# Install the pinned DueCare packages for this notebook.\n"
        "import glob\n"
        "import subprocess\n"
        "import sys\n"
        "\n"
        f"PACKAGES = {packages!r}\n"
        "DUECARE_PACKAGES = [package for package in PACKAGES if package.startswith('duecare-')]\n"
        "EXTRA_PACKAGES = [package for package in PACKAGES if not package.startswith('duecare-')]\n"
        "\n"
        "def _pip_install(items):\n"
        "    if items:\n"
        "        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *items])\n"
        "\n"
        "def _wheel_install():\n"
        "    wheel_patterns = [\n"
        "        '/kaggle/input/duecare-llm-wheels/*.whl',\n"
        "        '/kaggle/input/datasets/taylorsamarel/duecare-llm-wheels/*.whl',\n"
        "        '/kaggle/input/**/*.whl',\n"
        "    ]\n"
        "    wheel_files = []\n"
        "    for pattern in wheel_patterns:\n"
        "        wheel_files = sorted(glob.glob(pattern, recursive=True))\n"
        "        if wheel_files:\n"
        "            break\n"
        "    if not wheel_files:\n"
        "        return False\n"
        "    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', '--force-reinstall', '--no-deps', *wheel_files])\n"
        "    if EXTRA_PACKAGES:\n"
        "        _pip_install(EXTRA_PACKAGES)\n"
        "    print(f'Installed {len(wheel_files)} wheel files via attached Kaggle dataset.')\n"
        "    return True\n"
        "\n"
        "def _duecare_importable():\n"
        "    try:\n"
        "        import importlib\n"
        "        for mod in ('duecare.core',):\n"
        "            importlib.invalidate_caches()\n"
        "            importlib.import_module(mod)\n"
        "        return True\n"
        "    except Exception:\n"
        "        return False\n"
        "\n"
        "install_source = 'pypi'\n"
        "try:\n"
        "    _pip_install(PACKAGES)\n"
        "except Exception as exc:\n"
        "    print(f'Pinned PyPI install failed ({exc.__class__.__name__}). Falling back to Kaggle wheels for DueCare packages.')\n"
        "    if not _wheel_install() and DUECARE_PACKAGES:\n"
        "        raise RuntimeError('Could not install pinned DueCare packages from PyPI or attached wheel datasets.') from exc\n"
        "    install_source = 'kaggle_wheels'\n"
        "else:\n"
        "    # PyPI pip install returned 0 but that does not guarantee `duecare` is\n"
        "    # importable (a stub package with the same name can satisfy pip while\n"
        "    # providing none of the real modules). Verify; fall back to wheels if\n"
        "    # the import is still broken.\n"
        "    if DUECARE_PACKAGES and not _duecare_importable():\n"
        "        print('PyPI install finished but duecare.core is not importable. Falling back to Kaggle wheels.')\n"
        "        if _wheel_install():\n"
        "            install_source = 'kaggle_wheels'\n"
        "        else:\n"
        "            raise RuntimeError('duecare.core not importable after pip and wheel install. Attach taylorsamarel/duecare-llm-wheels and rerun.')\n"
        "\n"
        "import duecare.core\n"
        "print(f'DueCare version: {duecare.core.__version__} ({install_source})')\n"
        f"if duecare.core.__version__ != '{DUECARE_VERSION}':\n"
        f"    print('Expected DueCare version: {DUECARE_VERSION}')\n"
    )


def _make_gpu_guard_cell() -> dict[str, Any]:
    return make_code_cell(
        "try:\n"
        "    import torch\n"
        "    if not torch.cuda.is_available():\n"
        "        print('This notebook requires a T4 GPU. Enable it in Kaggle settings.')\n"
        "    else:\n"
        "        device_name = torch.cuda.get_device_name(0)\n"
        "        if 'T4' in device_name or 'A100' in device_name or 'L4' in device_name:\n"
        "            print(f'GPU detected: {device_name}')\n"
        "        else:\n"
        "            print(f'This notebook requires a T4 GPU. Enable it in Kaggle settings. Current device: {device_name}')\n"
        "except Exception:\n"
        "    print('This notebook requires a T4 GPU. Enable it in Kaggle settings.')\n"
    )


def _make_summary_cell(filename: str) -> dict[str, Any]:
    message = SUMMARY_MESSAGES.get(
        filename,
        "Notebook review complete. Continue with the next linked notebook for the next stage of the DueCare pipeline.",
    )
    return make_code_cell(f"print({message!r})\n")


def _tag_hide_input(cell: dict[str, Any]) -> None:
    """Tag a code cell so Kaggle / Jupyter hides the source but shows output."""
    md = cell.setdefault("metadata", {})
    md["_kg_hide-input"] = True
    md.setdefault("jupyter", {})["source_hidden"] = True


def _tag_hide_output(cell: dict[str, Any]) -> None:
    """Tag a code cell so Kaggle / Jupyter hides the rendered output."""
    md = cell.setdefault("metadata", {})
    md["_kg_hide-output"] = True
    md.setdefault("jupyter", {})["outputs_hidden"] = True


def _tag_hide_both(cell: dict[str, Any]) -> None:
    """Tag a code cell so Kaggle / Jupyter hides both source and output."""
    _tag_hide_input(cell)
    _tag_hide_output(cell)


def _is_hero_render_cell(text: str) -> bool:
    """Heuristic: a cell whose main effect is rendering a hero banner / stat
    cards / pipeline diagram / styled HTML block. Input hidden, output visible.

    Matches Python that exists only to build an HTML string and hand it to
    ``display(HTML(...))`` - the exact duplication the user flagged.
    """
    t = text.lower()
    if "display(html(" not in t:
        return False
    if any(marker in t for marker in (
        "linear-gradient",
        "_stat_card(",
        "_pipeline_step(",
        "_step(",
        "notebook_title",
        "<div style=",
        "<table style=",
        "<tr style=",
        "<th style=",
        "background:#f6f8fa",
        "border-left:",
        "rows_html",
        "table_html",
    )):
        return True
    return False


def _is_handoff_print_cell(text: str) -> bool:
    """Terminal single-``print(...)`` summary / handoff cell.

    Matches any short cell whose only statement is a ``print(...)`` call,
    since every such cell duplicates the Markdown "Next" section above it.
    Hide both source and output.
    """
    stripped = text.strip()
    if not stripped.startswith("print("):
        return False
    if len(stripped) > 2000:
        return False
    # It must not be a debugging print inside a larger cell; the strip()
    # start check already guarantees the first char is 'p', so check that
    # after the outer print() nothing else follows (allow trailing newline).
    return stripped.endswith(")") or stripped.endswith(")\n")


def harden_cells(
    *,
    filename: str,
    cells: list[dict[str, Any]],
    requires_gpu: bool = False,
    append_summary: bool = True,
) -> list[dict[str, Any]]:
    hardened = [_normalize_cell(cell) for cell in cells]

    # User directive: any hero banner / stat-card cell is the notebook's
    # visual front door and must be cell 0. Move it ahead of any preceding
    # markdown so the banner is what the reader sees first.
    for index, cell in enumerate(hardened):
        if cell.get("cell_type") != "code":
            continue
        if _is_hero_render_cell(_source_text(cell)):
            if index > 0:
                hero = hardened.pop(index)
                hardened.insert(0, hero)
            break

    first_code_index = next(
        (index for index, cell in enumerate(hardened) if cell.get("cell_type") == "code"),
        len(hardened),
    )
    install_cell = _normalize_cell(_make_install_cell(filename))
    # Hide both the install boilerplate AND its error-log / wheel-install output.
    _tag_hide_both(install_cell)
    install_index = first_code_index

    if first_code_index == len(hardened):
        hardened.append(install_cell)
        install_index = len(hardened) - 1
    else:
        first_code_text = _source_text(hardened[first_code_index])
        if _looks_like_install_cell(first_code_text):
            hardened.insert(first_code_index, install_cell)
            install_index = first_code_index
        elif _is_hero_render_cell(first_code_text):
            # Put hero visual at the TOP; install goes immediately after so
            # a reader sees the rendered banner before any pip output.
            hardened.insert(first_code_index + 1, install_cell)
            install_index = first_code_index + 1
        else:
            hardened.insert(first_code_index, install_cell)
            install_index = first_code_index

    # Hide source for hero/stat-card rendering cells; hide both source and
    # output for handoff prints (redundant with the preceding "Next" prose).
    for cell in hardened:
        if cell.get("cell_type") != "code":
            continue
        text = _source_text(cell)
        if _is_hero_render_cell(text):
            _tag_hide_input(cell)
        elif _is_handoff_print_cell(text):
            _tag_hide_both(cell)

    if requires_gpu:
        gpu_guard_present = any(
            "This notebook requires a T4 GPU. Enable it in Kaggle settings." in _source_text(cell)
            for cell in hardened
        )
        if not gpu_guard_present:
            hardened.insert(install_index + 1, _normalize_cell(_make_gpu_guard_cell()))

    if append_summary:
        summary_message = SUMMARY_MESSAGES.get(filename)
        if summary_message:
            summary_present = any(summary_message in _source_text(cell) for cell in hardened[-2:])
            if not summary_present:
                summary_cell = _normalize_cell(_make_summary_cell(filename))
                # Always hide both source and output on the auto-appended
                # summary cell - it duplicates the preceding "Next" prose.
                _tag_hide_both(summary_cell)
                hardened.append(summary_cell)

    return hardened


def harden_notebook(
    notebook: dict[str, Any],
    *,
    filename: str,
    requires_gpu: bool = False,
    append_summary: bool = True,
) -> dict[str, Any]:
    hardened = copy.deepcopy(notebook)
    hardened["cells"] = harden_cells(
        filename=filename,
        cells=list(hardened.get("cells", [])),
        requires_gpu=requires_gpu,
        append_summary=append_summary,
    )
    metadata = hardened.setdefault("metadata", {})
    metadata.setdefault("language_info", {"name": "python"})
    return hardened