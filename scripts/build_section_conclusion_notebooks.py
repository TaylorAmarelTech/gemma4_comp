"""Build the 8 DueCare section-conclusion notebooks (099, 199, 299, 399, 499, 599, 699, 799).

Each conclusion notebook closes one section of the index curriculum. Content is
intentionally short: recap of the section, key takeaways, and a pointer to the
next section's starting notebook.
"""

from __future__ import annotations

import json
from pathlib import Path

from notebook_hardening_utils import INSTALL_PACKAGES, harden_notebook
from _public_slugs import PUBLIC_SLUG_OVERRIDES

ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["gemma", "safety", "evaluation", "summary"]


SECTIONS = [
    {
        "num": "099",
        "slug": "orientation-setup-conclusion",
        "snake": "orientation_background_package_setup_conclusion",
        "section_title": "Orientation and Background and Package Setup",
        "kaggle_title": "099: DueCare Orientation + Setup Conclusion",
        "recap": (
            "The orientation section did three things, in this order. First, 000 Index "
            "laid out the full suite as eleven sections with an explicit reading order, "
            "so a reader lands on any later notebook knowing where it sits in the "
            "narrative rather than treating it as a standalone demo. Second, 005 "
            "Glossary and Reading Map named the vocabulary the rest of the suite uses "
            "(DueCare, Gemma 4, 6-dimension weighted rubric, V3 6-band classifier, "
            "domain packs, Anonymizer gate, cross-domain proof) and gave each term a "
            "concrete pointer to the notebook that introduces it. Third, 010 Quickstart "
            "installed the 8 duecare-llm-* PyPI packages, verified the model, task, "
            "agent, and domain registries resolved with real plugins (not placeholders), "
            "and ran a minimal safety-scoring loop end-to-end on a free Kaggle CPU "
            "kernel. Together, the section converts an abstract project description "
            "into a working install that any reader can reproduce in five minutes before "
            "any GPU-bound evaluation section spends compute."
        ),
        "key_points": [
            "DueCare is named for California Civil Code section 1714(a) duty of care; the duty-of-care framing is the legal basis for why NGOs need an on-device evaluator rather than a frontier API.",
            "The project is an applied exploration of Gemma 4 as an on-device safety system; Gemma 4's native function calling and multimodal understanding are load-bearing infrastructure, not demo-only decoration.",
            "The suite ships as 8 PyPI packages under the duecare-llm-* namespace sharing the duecare Python import namespace (PEP 420), so a Kaggle notebook can pip install only the subset it needs instead of multi-GB of deps.",
            "The registries (8 model adapters, 9 capability tests, 12 agents, 3 domain packs) auto-register on import; the quickstart asserts non-empty registries so every later section has real plugins to call.",
            "The glossary and reading map are the navigation surface; a reader who lands on a single notebook via a public link can still orient themselves because every later notebook's header table names its inputs, outputs, prerequisites, runtime, and pipeline position.",
            "With the environment verified, the next section can spend GPU time on real Gemma 4 inference instead of re-proving the install path works.",
        ],
        "next_section": "Free Form Exploration",
        "next_notebook_id": "100",
        "next_notebook_title": "Gemma Exploration",
        "next_notebook_slug": "duecare-gemma-exploration",
    },
    {
        "num": "199",
        "slug": "free-form-exploration-conclusion",
        "snake": "free_form_exploration_conclusion",
        "section_title": "Free Form Exploration",
        "kaggle_title": "199: DueCare Free Form Exploration Conclusion",
        "recap": (
            "The free form exploration section did two things. First, 100 ran stock Gemma 4 "
            "against the curated and remixed prompt set with a weighted rubric applied, "
            "producing the canonical Phase 1 baseline every later improvement is measured "
            "against. Second, the three playgrounds (150 text, 155 tool-call, 160 image) "
            "gave readers direct, interactive handles on the same model surfaces so they "
            "could form their own first impression before trusting any scored claim. "
            "Taken together, the section turns the prepared input pipeline into an honest, "
            "reproducible first look at what Gemma 4 actually does on the trafficking domain."
        ),
        "key_points": [
            "Stock Gemma 4 now has a concrete scored baseline, not a hand-wave. Every later improvement is compared against this exact run.",
            "Unscored free-form interaction in the three playgrounds is the most honest first look at model behavior; it surfaces the failure shapes the rubric is then asked to measure.",
            "First-seen failure patterns (refusal, hedging, over-compliance, authority deference) shape every later rubric and test set.",
            "Interactive text, tool-call, and image playgrounds prove the four solution surfaces are not hypothetical; a reader can type into each one on a T4 kernel.",
            "The same baseline JSON feeds the cross-model comparisons in 200 through 270, so this section is also where the later comparison narrative becomes possible.",
        ],
        "next_section": "Baseline Text Evaluation Framework",
        "next_notebook_id": "105",
        "next_notebook_title": "Prompt Corpus Introduction",
        "next_notebook_slug": "duecare-105-prompt-corpus-introduction",
        "followup_notebook_id": "110",
        "followup_notebook_title": "Prompt Prioritizer",
        "followup_notebook_slug": "00a-duecare-prompt-prioritizer-data-pipeline",
    },
    {
        "num": "299",
        "slug": "text-evaluation-conclusion",
        "snake": "baseline_text_evaluation_framework_conclusion",
        "section_title": "Baseline Text Evaluation Framework",
        "kaggle_title": "299: DueCare Text Evaluation Conclusion",
        "recap": (
            "The Baseline Text Evaluation Framework section did two things, in this "
            "order. First, 110 Prompt Prioritizer narrowed the 74K-prompt corpus to a "
            "high-value, reproducible evaluation slice with graded BEST and WORST "
            "reference responses included and every primary rubric category covered. "
            "Second, 120 Prompt Remixer mutated that slice into adversarial variants "
            "(academic framing, role-play, corporate wrapping, urgency pressure, "
            "corridor swaps) so later tests measure robustness, not only direct "
            "accuracy, and every mutation carries traceability back to its base "
            "prompt and strategy. Together, 110 and 120 are the input discipline that "
            "makes every comparison from 200 through 270, and every evaluation in 300 "
            "through 450, fair and comparable; without a stable, seeded, reproducible "
            "prompt pipeline here, none of the scores below can be honestly compared."
        ),
        "key_points": [
            "Input curation in 110 determines what the benchmark can credibly claim; a biased or unbalanced slice invalidates every later score. The canonicalized 110 notebook ships the selected slice plus the selection rationale so reviewers can audit both.",
            "Remixing in 120 is what turns a prompt list into a robustness test. Without the adversarial frames (academic, role-play, corporate, urgency, corridor swap), the benchmark would only measure easy cases; the canonicalized 120 notebook surfaces each mutation strategy alongside one worked example.",
            "Every remixed variant carries provenance back to its base prompt and strategy, so a downstream evaluation failure can be diagnosed by mutation type rather than treated as generic noise.",
            "The graded BEST and WORST anchors produced here are the same anchors 250 Comparative Grading rescores against later in the suite, which is why the anchored scores in 399 are interpretable rather than arbitrary.",
            "The framework is deliberately simple and legible so cross-model comparisons in 399 are comparable run-to-run and reader-to-reader; any later churn in the comparison section has to keep this pipeline stable to remain honest.",
        ],
        "next_section": "Baseline Text Comparisons",
        "next_notebook_id": "200",
        "next_notebook_title": "Cross-Domain Proof",
        "next_notebook_slug": "duecare-cross-domain-proof",
    },
    {
        "num": "399",
        "slug": "baseline-text-comparisons-conclusion",
        "snake": "baseline_text_comparisons_conclusion",
        "section_title": "Baseline Text Comparisons",
        "kaggle_title": "399: DueCare Baseline Text Comparisons Conclusion",
        "recap": (
            "The Baseline Text Comparisons section did eight things in a fixed order, "
            "each anchored to the same graded slice and 6-dimension weighted rubric "
            "produced upstream. First, 130 Prompt Corpus Exploration rendered the "
            "curated and remixed slice directly: category and corridor tables, the "
            "5-grade rubric, and one prompt shown at every grade, so every mean "
            "score below reads as a grade, not a raw number. Second, 200 Cross-Domain "
            "Proof showed the harness is domain-agnostic across trafficking, tax "
            "evasion, and financial crime. Third, 210 Gemma vs OSS scored Gemma 4 "
            "E4B against Gemma 4 E2B, Llama 3.1 8B, and Mistral 7B v0.3 by loading "
            "the Phase 1 baseline from 100 and reapplying the rubric. Fourth, 220 "
            "Ollama Cloud widened the peer set to seven OSS models under the same "
            "rubric and proved the evaluation reruns fully on-device by flipping the "
            "base URL. Fifth, 230 Mistral Family isolated five Mistral variants "
            "(7B through 123B) as the EU-sovereign alternative. Sixth, 240 "
            "OpenRouter Frontier scored Gemma 4 against Claude 3.5, GPT-4o, Gemini "
            "1.5 Pro, Llama 3.1 405B, DeepSeek V3, and Qwen 2.5 72B so deployers see "
            "the on-device-vs-frontier trade directly. Seventh, 250 Comparative "
            "Grading anchored every score against each prompt's own BEST and WORST "
            "reference, which is what makes the numbers across 210 through 270 "
            "interpretable as grades. Eighth, 260 RAG Comparison held the model "
            "fixed and varied the input context (plain, RAG, guided) so NGO deployers "
            "see which intervention closes the gap without waiting for Phase 3, and "
            "270 Gemma Generations ran the same slice across Gemma 2 / 3 / 4 so the "
            "generation effect is isolated from the curriculum effect."
        ),
        "key_points": [
            "Every score from 200 through 270 is commensurable because the same graded slice, the same rubric, and the same BEST / WORST anchors from 110 / 120 / 130 feed every comparison; cross-provider and cross-generation numbers are directly readable side-by-side.",
            "On-device Gemma 4 E4B beats the 7-model OSS fleet in 220 on trafficking safety under the shared rubric and produces zero harmful outputs on the Phase 1 slice; 210 and 230 show the same lead against peer OSS families.",
            "Frontier cloud models in 240 lead on raw completeness but lose on actionability because they hedge instead of redirecting to real hotlines; that actionability gap is what makes an on-device deployment worth shipping for NGOs.",
            "Anchored grading in 250 replaces unbounded 0-100 scores with per-prompt BEST / WORST references, so the gap analysis (missing from best / improves over worst) is a legitimate Phase 3 curriculum signal rather than noise.",
            "260 RAG Comparison shows guidance lands cheaper than retrieval on Gemma 4 for this slice; a guided system prompt is a viable zero-cost NGO deployment today, while retrieval over the rubric store and the Phase 3 fine-tune are the higher-ceiling paths.",
            "270 Gemma Generations confirms the trafficking safety gap is domain-specific, not model-general: Gemma 2 -> 3 -> 4 modestly reduces HARD_VIOLATION rates but leaves FULL_SUCCESS single-digit across stock Gemma, which is the explicit Phase 3 target.",
        ],
        "next_section": "Advanced Evaluation",
        "next_notebook_id": "300",
        "next_notebook_title": "Adversarial Resistance",
        "next_notebook_slug": "duecare-300-adversarial-resistance",
    },
    {
        "num": "499",
        "slug": "advanced-evaluation-conclusion",
        "snake": "advanced_evaluation_conclusion",
        "section_title": "Advanced Evaluation",
        "kaggle_title": "499: DueCare Advanced Evaluation Conclusion",
        "recap": (
            "The advanced evaluation section did five things. First, 300 probed Gemma "
            "across 15 adversarial attack vectors to expose failure modes the baseline "
            "comparisons cannot surface. Second, 400 documented native function calling "
            "and multimodal document inputs as load-bearing Gemma 4 features (with the "
            "live round-trips delegated to 155, 160, and 180 on GPU). Third, 410 applied "
            "a 6-dimension weighted rubric (refusal_quality, legal_accuracy, "
            "completeness, victim_safety, cultural_sensitivity, actionability) using a "
            "deterministic heuristic judge that is swappable with an LLM judge for live "
            "runs, so scoring is reproducible on CPU. Fourth, 420 tested multi-turn "
            "conversational escalation where single-turn evaluation misses drift. "
            "Fifth, 250 re-anchored the whole grading stack against hand-written best "
            "and worst references so every score above is comparable to a known ceiling "
            "and a known floor. Together, this section is where the suite stops "
            "comparing labels and starts measuring real behavior."
        ),
        "key_points": [
            "Adversarial, tool, multimodal, and multi-turn inputs expose distinct failure classes; one rubric is not enough.",
            "Judge-based scores and rubric-based scores disagree in useful, diagnostic ways; the disagreement is a signal, not noise.",
            "Anchored grading against hand-written references is what keeps every score in this section interpretable to a judge.",
            "Multi-turn escalation surfaces failures that single-turn evaluation misses entirely, particularly around refusal drift.",
            "These findings drive the prompt and rubric generation in the next section (310, 430, 440), which in turn feed the adversarial evaluation and fine-tune.",
        ],
        "next_section": "Advanced Prompt-Test Generation",
        "next_notebook_id": "310",
        "next_notebook_title": "Prompt Factory",
        "next_notebook_slug": "duecare-310-prompt-factory",
    },
    {
        "num": "599",
        "slug": "model-improvement-opportunities-conclusion",
        "snake": "model_improvement_opportunities_conclusion",
        "section_title": "Model Improvement Opportunities",
        "kaggle_title": "599: DueCare Model Improvement Opportunities Conclusion",
        "recap": (
            "The model improvement section turned evaluation and adversarial failures into a "
            "training curriculum and fine-tuned Gemma 4 with Unsloth to produce the deployable "
            "DueCare model artifacts."
        ),
        "key_points": [
            "Curriculum construction is the most consequential step; fine-tuning just applies it.",
            "Orchestration by the agent swarm keeps training loops honest and reproducible.",
            "The exported fine-tune is the artifact every solution surface deploys.",
        ],
        "next_section": "Solution Surfaces",
        "next_notebook_id": "600",
        "next_notebook_title": "Results Dashboard",
        "next_notebook_slug": "duecare-600-results-dashboard",
    },
    {
        "num": "699",
        "slug": "advanced-prompt-test-generation-conclusion",
        "snake": "advanced_prompt_test_generation_conclusion",
        "section_title": "Advanced Prompt-Test Generation",
        "kaggle_title": "699: DueCare Advanced Prompt-Test Generation Conclusion",
        "recap": (
            "The advanced prompt-test generation section turned evaluation findings into "
            "harder prompts, richer rubrics, and reusable scoring assets. Prompt Factory "
            "generates and ranks new cases; Rubric Evaluation and Per-Prompt Rubric Generator "
            "produce the scoring assets for the adversarial pass that follows immediately in "
            "320 and 450."
        ),
        "key_points": [
            "Remixing produces surface-variant stress cases; generation produces new cases.",
            "Each generated prompt carries an impact ranking to focus evaluation attention.",
            "Per-prompt rubrics are synthesized here, not written by hand downstream.",
            "The next section attacks these exact generated prompts and rubrics; this is the handoff, not a side branch.",
        ],
        "next_section": "Adversarial Prompt-Test Evaluation",
        "next_notebook_id": "320",
        "next_notebook_title": "Finding Gemma 4 Safety Line",
        "next_notebook_slug": "duecare-finding-gemma-4-safety-line",
    },
    {
        "num": "799",
        "slug": "adversarial-prompt-test-evaluation-conclusion",
        "snake": "adversarial_prompt_test_evaluation_conclusion",
        "section_title": "Adversarial Prompt-Test Evaluation",
        "kaggle_title": "799: DueCare Adversarial Prompt-Test Evaluation Conclusion",
        "recap": (
            "The adversarial evaluation section measured Gemma's actual safety line under the "
            "generated prompts and rubrics, and reviewed the worst-case responses in full "
            "context. It isolated the failures the next section turns into orchestration, "
            "curriculum, and fine-tune decisions."
        ),
        "key_points": [
            "Adversarial probes expose failures that baseline evaluation does not surface.",
            "The safety line shifts under attack and has to be measured, not assumed.",
            "Contextual review of the worst responses is what turns metrics into training signal.",
            "500, 520, and 530 only matter because this section identifies which failures are worth fixing first.",
        ],
        "next_section": "Model Improvement Opportunities",
        "next_notebook_id": "500",
        "next_notebook_title": "Agent Swarm Deep Dive",
        "next_notebook_slug": "duecare-500-agent-swarm-deep-dive",
    },
    {
        "num": "899",
        "slug": "solution-surfaces-conclusion",
        "snake": "solution_surfaces_conclusion",
        "section_title": "Solution Surfaces",
        "kaggle_title": "899: DueCare Solution Surfaces Conclusion",
        "recap": (
            "Across the late-suite implementation and deployment-application notebooks, DueCare now translates the evaluated, fine-tuned "
            "system into five concrete uses: enterprise-wide content moderation, client-side verification, a generalized NGO API endpoint, "
            "a multi-document migration-case workflow with timelines and complaint drafts, and custom domain adoption for new safety packs."
        ),
        "key_points": [
            "The suite now separates implementation-heavy surfaces from plain-English application notebooks, so judges can see both what ships and how it is built.",
            "Privacy is non-negotiable, so on-device and public API can coexist only when the boundary around case data is explicit, even for document bundles and case timelines.",
            "The deployment-application notebooks make the five product claims explicit, while 610, 620, and 650 remain the deeper implementation companions.",
        ],
        "next_section": "(end of suite)",
        "next_notebook_id": "610",
        "next_notebook_title": "Submission Walkthrough",
        "next_notebook_slug": "duecare-610-submission-walkthrough",
    },
]


def _md(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }


def _kaggle_url(notebook_id: str, default_slug: str) -> str:
    slug = PUBLIC_SLUG_OVERRIDES.get(notebook_id, default_slug)
    return f"https://www.kaggle.com/code/taylorsamarel/{slug}"


# Previous-notebook pointers per section. These drive the "Previous" row in
# the pipeline-position header table of each conclusion.
PREV_NOTEBOOK = {
    "099": ("010", "Quickstart", "duecare-010-quickstart"),
    "199": ("180", "Multimodal Document Inspector", "180-duecare-multimodal-document-inspector"),
    "299": ("190", "RAG Retrieval Inspector", "duecare-190-rag-retrieval-inspector"),
    "399": ("270", "Gemma Generations", "duecare-270-gemma-generations"),
    "499": ("460", "Citation Verifier", "duecare-460-citation-verifier"),
    "599": ("540", "Fine-tune Delta Visualizer", "duecare-540-finetune-delta-visualizer"),
    "699": ("440", "Per-Prompt Rubric Generator", "duecare-per-prompt-rubric-generator"),
    "799": ("450", "Contextual Worst-Response Judge", "duecare-contextual-judge"),
    "899": ("695", "Custom Domain Adoption", "duecare-695-custom-domain-adoption"),
}

# Notebooks covered by each section (for the concrete recap row).
SECTION_MEMBERS = {
    "099": "000 Index, 005 Glossary and Reading Map, 010 Quickstart",
    "199": "100 Gemma Exploration, 150 Free Form Gemma Playground, 155 Tool Calling Playground, 160 Image Processing Playground, 170 Live Context Injection Playground, 180 Multimodal Document Inspector",
    "299": "105 Prompt Corpus Introduction, 110 Prompt Prioritizer, 120 Prompt Remixer, 130 Prompt Corpus Exploration, 140 Evaluation Mechanics, 190 RAG Retrieval Inspector",
    "399": "200 through 270 (cross-model, cross-strategy, cross-generation comparisons)",
    "499": "300 Adversarial Resistance, 335 Attack Vector Inspector, 400 Function Calling and Multimodal, 410 LLM Judge, 420 Conversation Testing, 460 Citation Verifier",
    "599": "500 Agent Swarm, 510 Phase 2 Comparison, 520 Curriculum Builder, 530 Unsloth Fine-Tune, 540 Fine-tune Delta Visualizer",
    "699": "310 Prompt Factory, 430 Rubric Evaluation, 440 Per-Prompt Rubric Generator",
    "799": "320 Finding Gemma 4 Safety Line, 450 Contextual Worst-Response Judge",
    "899": "600 Results Dashboard, 610 Submission Walkthrough, 620 Demo API Endpoint Tour, 650 Custom Domain Walkthrough, 660 Enterprise Moderation, 670 Private Client-Side Checker, 680 NGO API Triage, 690 Migration Case Workflow, 695 Custom Domain Adoption",
}


def _title_derived_slug(kaggle_title: str) -> str:
    """Mirror Kaggle's title-to-slug algorithm so metadata id matches live."""
    import re
    slug = kaggle_title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _build_one(section: dict) -> None:
    filename = f"{section['num']}_{section['snake']}.ipynb"
    kernel_dir_name = f"duecare_{section['num']}_{section['snake']}"
    # Prefer an explicit PUBLIC_SLUG_OVERRIDES entry: some section conclusion
    # slugs that start with the NNN- prefix fail first-time Kaggle creation
    # (see checkpoint 31 section 5), so we route them through the
    # non-prefixed fallback slug.
    derived_slug = PUBLIC_SLUG_OVERRIDES.get(
        section["num"], _title_derived_slug(section["kaggle_title"])
    )
    kernel_id = f"taylorsamarel/{derived_slug}"
    packages = ["duecare-llm-core==0.1.0"]
    INSTALL_PACKAGES[filename] = packages

    next_id = section["next_notebook_id"]
    next_default_slug = section["next_notebook_slug"]
    next_link = _kaggle_url(next_id, next_default_slug)
    next_title = section["next_notebook_title"]

    followup_id = section.get("followup_notebook_id")
    followup_default_slug = section.get("followup_notebook_slug")
    followup_title = section.get("followup_notebook_title")
    followup_link = (
        _kaggle_url(followup_id, followup_default_slug)
        if followup_id and followup_default_slug
        else None
    )

    prev_id, prev_title, prev_default_slug = PREV_NOTEBOOK.get(
        section["num"], ("000", "Index", "duecare-000-index")
    )
    prev_link = _kaggle_url(prev_id, prev_default_slug)

    if section["next_section"] != "(end of suite)":
        pipeline_position_text = (
            f'{section["section_title"]} section close. Previous: '
            f'<a href="{prev_link}">{prev_id} {prev_title}</a>. Next section: '
            f'<a href="{next_link}">{next_id} {next_title}</a>.'
        )
    else:
        pipeline_position_text = (
            f'{section["section_title"]} section close. Previous: '
            f'<a href="{prev_link}">{prev_id} {prev_title}</a>. '
            f'Capstone walkthrough: <a href="{next_link}">{next_id} {next_title}</a>. '
            'End of suite after this section.'
        )

    index_link = _kaggle_url("000", "duecare-000-index")
    members = SECTION_MEMBERS.get(section["num"], "")

    bullets = "\n".join(f"- {p}" for p in section["key_points"])

    # Header block matches the canonical suite format used in 000, 005, 010.
    outputs_text = (
        "A plain-English recap, key points, and the next-section handoff."
        if section["next_section"] != "(end of suite)"
        else "A plain-English recap, key points, and the capstone/index handoff."
    )

    header_table = (
        '<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">\n'
        '  <thead>\n'
        '    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">\n'
        '      <th style="padding: 6px 10px; text-align: left; width: 22%;">Field</th>\n'
        '      <th style="padding: 6px 10px; text-align: left; width: 78%;">Value</th>\n'
        '    </tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        f'    <tr><td style="padding: 6px 10px;"><b>Inputs</b></td><td style="padding: 6px 10px;">Notebooks read in this section ({members}).</td></tr>\n'
        f'    <tr><td style="padding: 6px 10px;"><b>Outputs</b></td><td style="padding: 6px 10px;">{outputs_text}</td></tr>\n'
        '    <tr><td style="padding: 6px 10px;"><b>Prerequisites</b></td><td style="padding: 6px 10px;">Kaggle CPU kernel with internet enabled; no GPU or API keys.</td></tr>\n'
        '    <tr><td style="padding: 6px 10px;"><b>Runtime</b></td><td style="padding: 6px 10px;">Under 1 minute.</td></tr>\n'
        f'    <tr><td style="padding: 6px 10px;"><b>Pipeline position</b></td><td style="padding: 6px 10px;">{pipeline_position_text}</td></tr>\n'
        '  </tbody>\n'
        '</table>'
    )

    if section["next_section"] != "(end of suite)":
        next_lines = [
            f"- **Continue to the next section:** [{next_id} {next_title}]({next_link})."
        ]
        if followup_link and followup_title:
            next_lines.append(
                f"- **After that:** [{followup_id} {followup_title}]({followup_link})."
            )
        next_lines.append(f"- **Back to navigation (optional):** [000 Index]({index_link}).")
        next_block = "\n".join(next_lines)
        final_print_target = next_link
        final_print_label = f"{next_id} {next_title}"
    else:
        next_block = (
            f"- **Capstone walkthrough:** [{next_id} {next_title}]({next_link}).\n"
            f"- **Back to navigation:** [000 Index]({index_link})."
        )
        final_print_target = index_link
        final_print_label = "000 Index"

    body = f"""# {section['num']}: DueCare {section['section_title']} Conclusion

This notebook closes the **{section['section_title']}** section of the DueCare suite. Open it after you have worked through the section's notebooks in order. It recaps what the section established and hands off to the next narrative step.

{header_table}

---

## Recap

{section['recap']}

**Section notebooks covered:** {members}.

---

## Key points

{bullets}

---

## Where to go next

{next_block}
"""

    # Prepend hero + stat-card cell to every section conclusion.
    _title_str = section.get("kaggle_title") or section.get("label", "DueCare Conclusion")
    _hero_src = (
        f"NOTEBOOK_TITLE = {_title_str!r}\n"
        "from IPython.display import HTML, display\n"
        "display(HTML(\n"
        "    '<div style=\"background:linear-gradient(135deg,#1e3a8a 0%,#4c78a8 100%);color:white;padding:20px 24px;border-radius:8px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif\">'\n"
        "    '<div style=\"font-size:10px;font-weight:600;letter-spacing:0.14em;opacity:0.8;text-transform:uppercase\">DueCare - Section Conclusion</div>'\n"
        "    f'<div style=\"font-size:22px;font-weight:700;margin:4px 0 0 0\">{NOTEBOOK_TITLE}</div>'\n"
        "    '<div style=\"font-size:13px;opacity:0.92;margin-top:4px\">Recap, key findings, and handoff to the next section.</div></div>'\n"
        "))\n"
    )
    _hero_cell = {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": _hero_src.splitlines(keepends=True)}
    cells = [_hero_cell, _md(body)]

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11"},
            "kaggle": {"accelerator": "none", "isInternetEnabled": True},
        },
        "cells": cells,
    }
    nb = harden_notebook(nb, filename=filename, requires_gpu=False)

    # Replace the hardener's generic final print with a URL-bearing handoff.
    if followup_link and followup_title:
        final_print_src = (
            "print(\n"
            f"    'Section close complete. Continue to {final_print_label}: '\n"
            f"    '{final_print_target}. '\n"
            f"    'Then open {followup_id} {followup_title}: '\n"
            f"    '{followup_link}'\n"
            ")\n"
        )
    else:
        final_print_src = (
            "print(\n"
            f"    'Section close complete. Continue to {final_print_label}: '\n"
            f"    '{final_print_target}'\n"
            "    '.'\n"
            ")\n"
        )
    replaced_summary = False
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        # harden_notebook's default summary print; pattern-match its usual content.
        if "print(" in src and ("Continue to" in src or "Section complete" in src or "Conclusion complete" in src or "notebook" in src.lower() and "complete" in src.lower() and "print" in src.lower()):
            if "pip install" in src or "PACKAGES = [" in src:
                continue  # Do not replace the install cell.
            cell["source"] = final_print_src.splitlines(keepends=True)
            md = cell.setdefault("metadata", {})
            md["_kg_hide-input"] = True
            md["_kg_hide-output"] = True
            md.setdefault("jupyter", {})["source_hidden"] = True
            md["jupyter"]["outputs_hidden"] = True
            replaced_summary = True
            break

    if not replaced_summary:
        nb["cells"].append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {
                    "language": "python",
                    "_kg_hide-input": True,
                    "_kg_hide-output": True,
                    "jupyter": {"source_hidden": True, "outputs_hidden": True},
                },
                "outputs": [],
                "source": final_print_src.splitlines(keepends=True),
            }
        )

    NB_DIR.mkdir(parents=True, exist_ok=True)
    KAGGLE_KERNELS.mkdir(parents=True, exist_ok=True)

    nb_path = NB_DIR / filename
    nb_path.write_text(json.dumps(nb, indent=1), encoding="utf-8")

    kernel_dir = KAGGLE_KERNELS / kernel_dir_name
    kernel_dir.mkdir(parents=True, exist_ok=True)
    (kernel_dir / filename).write_text(json.dumps(nb, indent=1), encoding="utf-8")

    meta = {
        "id": kernel_id,
        "title": section["kaggle_title"],
        "code_file": filename,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [WHEELS_DATASET],
        "competition_sources": ["gemma-4-good-hackathon"],
        "kernel_sources": [],
        "keywords": KEYWORDS,
    }
    (kernel_dir / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    print(f"Wrote {nb_path}")
    print(f"Wrote {kernel_dir / filename}")


def build() -> None:
    for section in SECTIONS:
        _build_one(section)


if __name__ == "__main__":
    build()
