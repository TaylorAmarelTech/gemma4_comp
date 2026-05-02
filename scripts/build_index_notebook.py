"""Build the DueCare index notebook and Kaggle kernel metadata."""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import canonical_header_table, patch_final_print_cell
from kaggle_notebook_utils import discover_kernel_notebooks
from notebook_hardening_utils import harden_notebook
from _public_slugs import PUBLIC_SLUG_OVERRIDES

ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"
SLUG_MAP_PATH = ROOT / "scripts" / "kaggle_live_slug_map.json"
FILENAME = "000_index.ipynb"
KERNEL_DIR_NAME = "duecare_000_index"
KERNEL_ID = "taylorsamarel/duecare-000-index"
KERNEL_TITLE = "DueCare 000 Index"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["gemma", "safety", "llm", "trafficking", "tutorial"]
PUBLIC_REPO_URL = "https://github.com/TaylorAmarelTech/gemma4_comp"
JUDGES_GUIDE_URL = PUBLIC_REPO_URL + "/blob/main/docs/FOR_JUDGES.md"
WRITEUP_URL = "https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups"

PHASES = [
    {
        "label": "Background and Package Setup",
        "intro": "What is DueCare, and can you run the smallest proof that it works without reading the whole suite first? This section establishes the project frame, glossary, and smallest smoke test. It ends with **099**.",
        "notebooks": [
            {"id": "000", "title": "Index", "slug": "duecare-000-index", "summary": "Entry point and reading map for the full suite."},
            {"id": "005", "title": "Glossary and Map", "slug": "duecare-005-glossary", "summary": "Define the project vocabulary and explain how the notebook sequence fits together."},
            {"id": "010", "title": "Quickstart", "slug": "duecare-010-quickstart-in-5-minutes", "summary": "Install the packages and run the smallest end-to-end smoke test."},
            {"id": "015", "title": "Background Literature", "slug": "015-duecare-background-literature", "summary": "Academic and legal grounding: ILO indicators, Palermo Protocol, migrant-worker regulatory corridors, and the AI-safety literature behind every later rubric."},
            {"id": "020", "title": "Current Events", "slug": "020-duecare-current-events", "summary": "Recent public trafficking cases, AI-safety incidents, and regulatory changes that ground the abstract rubric in today's news."},
            {"id": "099", "title": "Background and Package Setup Conclusion", "slug": "099-duecare-orientation-setup-conclusion", "summary": "Recap the project framing and confirm the environment is ready.", "conclusion": True},
        ],
    },
    {
        "label": "Free Form Exploration",
        "intro": "What does stock Gemma 4 actually do on trafficking prompts before the comparison stack formalizes anything, and what do the interactive surfaces feel like by hand? This section ends with **199**.",
        "notebooks": [
            {"id": "100", "title": "Gemma Exploration", "slug": "duecare-gemma-exploration", "summary": "First systematic stock-Gemma baseline against the prepared prompt set; inspect raw failure patterns by eye."},
            {"id": "102", "title": "Gemma 4 E2B Baseline", "slug": "102-duecare-gemma-e2b-baseline", "summary": "Dedicated E2B scored baseline so the smaller Gemma 4 checkpoint has a like-for-like readout against the main E4B baseline."},
            {"id": "150", "title": "Free Form Gemma Playground", "slug": "150-duecare-free-form-gemma-playground", "summary": "Live interactive widget: type any prompt and see Gemma respond on a T4 GPU."},
            {"id": "152", "title": "Interactive Gemma Chat", "slug": "duecare-152-interactive-gemma-chat", "summary": "Stateful chat with Gemma 4 E4B on-device via Transformers + 4-bit; live safety-score overlay on every response; three persona presets."},
            {"id": "155", "title": "Tool Calling Playground", "slug": "155-duecare-tool-calling-playground", "summary": "Live demo: Gemma picks a tool and arguments for any scenario you type."},
            {"id": "160", "title": "Image Processing Playground", "slug": "160-duecare-image-processing-playground", "summary": "Live demo: upload an image, ask a question, see the multimodal response."},
            {"id": "165", "title": "Thinking-Budget Sweep", "slug": "165-duecare-thinking-budget-sweep", "summary": "CPU-side API sweep across multiple token budgets so judges can see how longer reasoning budgets change failure rates and verbosity."},
            {"id": "170", "title": "Live Context Injection Playground", "slug": "170-duecare-live-context-injection-playground", "summary": "Type any prompt and see plain vs RAG vs guided side-by-side on a T4 GPU. The fastest interactive demo of what context does."},
            {"id": "175", "title": "Temperature Sweep", "slug": "175-duecare-temperature-sweep", "summary": "CPU-side API sweep across sampling temperatures to show how safety behavior degrades or stabilizes as randomness increases."},
            {"id": "180", "title": "Multimodal Document Inspector", "slug": "180-duecare-multimodal-document-inspector", "summary": "Upload a recruitment-contract image; Gemma 4 multimodal extracts key fields and flags trafficking indicators."},
            {"id": "190", "title": "RAG Retrieval Inspector", "slug": "190-duecare-rag-retrieval-inspector", "summary": "Show exactly which legal citations match each prompt, with provenance; this is the RAG store 260 consumes."},
            {"id": "199", "title": "Free Form Exploration Conclusion", "slug": "199-duecare-free-form-exploration-conclusion", "summary": "Recap the unscored baseline and the failure patterns seen by eye.", "conclusion": True},
        ],
    },
    {
        "label": "Jailbreak Safety Research (181-189)",
        "intro": "How does stock Gemma 4 compare to abliterated, uncensored-community, and cracked variants on the same trafficking prompt slice — and what does that gap tell us about the on-device safety judge DueCare is building? The 181-189 band is a dedicated defensive-research block. 181-184 are playgrounds and generators that do not require multiple model loads; 185 is the CPU comparator; 186-189 are the per-model artifact producers that 185 joins.",
        "notebooks": [
            {"id": "181", "title": "Jailbreak Response Viewer", "slug": "duecare-181-jailbreak-response-viewer", "summary": "Visual side-by-side viewer across stock / abliterated / uncensored / cracked slots; refusal and harmful phrases highlighted inline."},
            {"id": "182", "title": "Refusal Direction Visualizer", "slug": "duecare-182-refusal-direction-visualizer", "summary": "Per-layer PCA of Gemma 4 residual-stream activations for harmful vs benign prompts; shows where refusal becomes linearly separable."},
            {"id": "183", "title": "Red-Team Prompt Amplifier", "slug": "duecare-183-redteam-prompt-amplifier", "summary": "Persona-rotated (broker/employer/forger/recruiter) coverage-gap feedback loop using an uncensored Gemma variant; grows the corpus from ~15 seeds to ~200 prompts with provenance."},
            {"id": "184", "title": "Frontier Consultation Playground", "slug": "duecare-184-frontier-consultation-playground", "summary": "Gemma 4's native function calling exposes consult_frontier(); three gating modes (self-report, logit-entropy, always-consult) measure the accuracy/escalation tradeoff."},
            {"id": "185", "title": "Jailbroken Gemma Comparison", "slug": "duecare-185-jailbroken-gemma-comparison", "summary": "CPU comparator that joins the 186-189 per-model artifact bundles into one readout: availability grid, response metrics, generation diversity, stock-vs-variant gap."},
            {"id": "186", "title": "Jailbreak - Stock Gemma Baseline", "slug": "duecare-186-jailbreak-stock-gemma", "summary": "Stock Gemma 4 E4B under three conditions (baseline, DAN preamble, researcher roleplay) — the prompt-level-bypass floor the weight-level variants must beat."},
            {"id": "187", "title": "Jailbreak - Abliterated E4B", "slug": "duecare-187-jailbreak-abliterated-e4b", "summary": "In-kernel abliteration recipe: 30+30 calibration, mid-band layer pick, o_proj+down_proj subtraction, held-out probe. Reproducible without external uncensored weights."},
            {"id": "188", "title": "Jailbreak - Uncensored Community", "slug": "duecare-188-jailbreak-uncensored-community", "summary": "Ranked HF probe list (huihui / AEON-7 / mlabonne); NVFP4 variants excluded (Blackwell-only); writes diagnostic bundle if no candidate resolves."},
            {"id": "189", "title": "Jailbreak - Cracked 31B", "slug": "duecare-189-jailbreak-cracked-31b", "summary": "dealignai/Gemma-4-31B-JANG_4M-CRACK in 4-bit; VRAM gate skips gracefully on T4, runs on L4x4/A100 (tests whether size closes the gap — it does not)."},
        ],
    },
    {
        "label": "Baseline Text Evaluation Framework",
        "intro": "How were the prompts selected, remixed, walked through, and prepared so later scores mean something instead of reflecting a random sample? This section ends with **299**.",
        "notebooks": [
            {"id": "105", "title": "Prompt Corpus Introduction", "slug": "duecare-105-prompt-corpus-introduction", "summary": "What is the trafficking prompt corpus, what does it look like, and what does it cover? The first touchpoint before any selection or scoring."},
            {"id": "110", "title": "Prompt Prioritizer", "slug": "duecare-prompt-prioritizer", "summary": "Select the highest-value prompts from the seed corpus before any scored evaluation."},
            {"id": "120", "title": "Prompt Remixer", "slug": "duecare-prompt-remixer", "summary": "Mutate curated prompts into remixed and adversarial variants that feed every later evaluation."},
            {"id": "130", "title": "Prompt Corpus Exploration", "slug": "130-duecare-prompt-corpus-exploration", "summary": "Walk through the corpus by category, sector, corridor, and difficulty; render the 5-grade rubric; show one prompt at every grade."},
            {"id": "140", "title": "Evaluation Mechanics", "slug": "duecare-140-evaluation-mechanics", "summary": "Walk through the measurement machinery used across the suite: 5-grade rubric, anchored best/worst references, keyword scorer, 6-dimension weighted rubric, and the V3 6-band classifier."},
            {"id": "299", "title": "Baseline Text Evaluation Framework Conclusion", "slug": "299-duecare-text-evaluation-conclusion", "summary": "Recap the prompt set, the remix strategy, and the anchored-grading method.", "conclusion": True},
        ],
    },
    {
        "label": "Baseline Text Comparisons",
        "intro": "How does Gemma 4 compare with peer open models, frontier models, retrieval-augmented prompting, and earlier Gemma generations on the same safety problem? This section ends with **399**.",
        "notebooks": [
            {"id": "200", "title": "Cross-Domain Proof", "slug": "duecare-cross-domain-proof", "summary": "Show the same harness working across trafficking, tax evasion, and financial crime."},
            {"id": "210", "title": "Gemma vs OSS Comparison", "slug": "duecare-gemma-vs-oss-comparison", "summary": "Compare Gemma against peer open-source models on the same task."},
            {"id": "220", "title": "Ollama Cloud OSS Comparison", "slug": "duecare-ollama-cloud-oss-comparison", "summary": "Benchmark Gemma against OSS models exposed through Ollama Cloud."},
            {"id": "230", "title": "Mistral Family Comparison", "slug": "duecare-230-mistral-family-comparison", "summary": "Compare Gemma against the Mistral family under the same prompt slice."},
            {"id": "240", "title": "OpenRouter Frontier Comparison", "slug": "duecare-openrouter-frontier-comparison", "summary": "Contrast DueCare results with large frontier models accessed through OpenRouter."},
            {"id": "245", "title": "Gemini API Gemma 4 Comparison", "slug": "duecare-245-gemini-api-comparison", "summary": "Head-to-head comparison across the currently available Gemini-routed Gemma endpoints so API behavior can be compared against the notebook-local baselines."},
            {"id": "250", "title": "Comparative Grading", "slug": "duecare-250-comparative-grading", "summary": "Anchor comparative scores against hand-written best and worst responses."},
            {"id": "260", "title": "RAG Comparison", "slug": "duecare-260-rag-comparison", "summary": "Measure plain, retrieval-augmented, and guided prompting lift."},
            {"id": "270", "title": "Gemma Generations", "slug": "duecare-270-gemma-generations", "summary": "Summarize how Gemma 2, 3, and 4 differ on the same safety tasks."},
            {"id": "399", "title": "Baseline Text Comparisons Conclusion", "slug": "399-duecare-baseline-text-comparisons-conclusion", "summary": "Recap the cross-model and cross-strategy findings.", "conclusion": True},
        ],
    },
    {
        "label": "Baseline Image Evaluation Framework",
        "intro": "How do the text-eval machinery patterns extend to image inputs — field extraction from recruitment-contract photos, indicator-firing from visual trafficking signals, and OCR-independent multimodal scoring? This section is planned; stubs land as the image-side Gemma 4 multimodal work unfolds. Ends with **499**.",
        "notebooks": [
            {"id": "400 (planned)", "title": "Image Evaluation Framework (planned)", "slug": "duecare-000-index", "summary": "Planned. Image-side analog of the 200 Baseline Text Evaluation Framework: prompt/image pairing, rubric for visual indicators, anchored best/worst for image outputs."},
        ],
    },
    {
        "label": "Baseline Image Comparisons",
        "intro": "How does Gemma 4 multimodal compare with peer multimodal models (PaliGemma 2, LLaVA-1.6, Idefics2) on the same recruitment-contract photo set? This section is planned. Ends with **599**.",
        "notebooks": [
            {"id": "500 (planned)", "title": "Image Comparisons (planned)", "slug": "duecare-000-index", "summary": "Planned. Image-side analog of the 300 Baseline Text Comparisons: Gemma 4 multimodal versus open-source peers under the 400 rubric."},
        ],
    },
    {
        "label": "Advanced Evaluation",
        "intro": "Where does Gemma fail once you stress it with adversarial inputs, multimodal documents, tool calls, conversation escalation, and anchored grading? This section ends with **499**.",
        "notebooks": [
            {"id": "300", "title": "Adversarial Resistance", "slug": "duecare-300-adversarial-resistance", "summary": "Probe Gemma across 15 adversarial attack vectors."},
            {"id": "335", "title": "Attack Vector Inspector", "slug": "duecare-335-attack-vector-inspector", "summary": "Visualization of the 15 adversarial attack vectors from 300: taxonomy pie, per-vector severity, mitigation status."},
            {"id": "400", "title": "Function Calling and Multimodal", "slug": "duecare-400-function-calling-multimodal", "summary": "Demonstrate native tool calls and document-aware multimodal analysis."},
            {"id": "410", "title": "LLM Judge Grading", "slug": "duecare-410-llm-judge-grading", "summary": "Score responses across six safety dimensions using an LLM judge."},
            {"id": "420", "title": "Conversation Testing", "slug": "duecare-420-conversation-testing", "summary": "Detect escalation and policy drift across multi-turn conversations."},
            {"id": "460", "title": "Citation Verifier", "slug": "duecare-460-citation-verifier", "summary": "Check whether the legal citations in model outputs are real or hallucinated; evidence for the legal-accuracy claim in the writeup."},
            {"id": "499", "title": "Advanced Evaluation Conclusion", "slug": "499-duecare-advanced-evaluation-conclusion", "summary": "Recap where tools, multimodal, conversation, and anchored grading break down.", "conclusion": True},
        ],
    },
    {
        "label": "Advanced Text Prompt-Test Generation",
        "intro": "How do you convert evaluation findings into harder prompts, richer rubrics, and reusable scoring assets for the rest of the project? This section ends with **699**.",
        "notebooks": [
            {"id": "310", "title": "Prompt Factory", "slug": "duecare-310-prompt-factory", "summary": "Generate, validate, and rank new prompts by likely victim impact."},
            {"id": "430", "title": "Rubric Evaluation", "slug": "duecare-430-rubric-evaluation", "summary": "Evaluate outputs against the 54-criterion pass/fail rubric and produce reusable grading assets."},
            {"id": "440", "title": "Per-Prompt Rubric Generator", "slug": "duecare-per-prompt-rubric-generator", "summary": "Synthesize per-prompt rubrics and failure-type classifications."},
            {"id": "699", "title": "Advanced Prompt-Test Generation Conclusion", "slug": "699-duecare-advanced-prompt-test-generation-conclusion", "summary": "Recap the generated test corpus and the synthesized rubrics.", "conclusion": True},
        ],
    },
    {
        "label": "Advanced Image Prompt-Test Generation",
        "intro": "How do adversarial image prompts get generated — synthetic recruitment contracts, altered passport photos, trafficking-indicator-laden visual documents? This section is planned. Ends with **899**.",
        "notebooks": [
            {"id": "800 (planned)", "title": "Image Prompt-Test Generation (planned)", "slug": "duecare-000-index", "summary": "Planned. Image-side analog of the 700 Advanced Text Prompt-Test Generation: synthesize adversarial image-prompt pairs, visual-rubric scoring, image red-team corpus."},
        ],
    },
    {
        "label": "Advanced Adversarial Prompt-Test Evaluation",
        "intro": "What is Gemma 4's real safety line, and which failures still matter after the scoring and rubric machinery is in place? This section ends with **799**.",
        "notebooks": [
            {"id": "320", "title": "Finding Gemma 4 Safety Line", "slug": "duecare-finding-gemma-4-safety-line", "summary": "Measure the gap between safe Gemma behavior and uncensored baselines."},
            {"id": "450", "title": "Contextual Worst-Response Judge", "slug": "duecare-contextual-judge", "summary": "Review the worst responses in full context."},
            {"id": "799", "title": "Adversarial Prompt-Test Evaluation Conclusion", "slug": "799-duecare-adversarial-prompt-test-evaluation-conclusion", "summary": "Recap the adversarial findings and where the safety line shifts.", "conclusion": True},
        ],
    },
    {
        "label": "Model Improvement Opportunities",
        "intro": "How do the evaluated failures turn into orchestration choices, curriculum design, and an actual Unsloth fine-tune instead of a vague promise to improve later? This section ends with **599**.",
        "notebooks": [
            {"id": "500", "title": "Agent Swarm Deep Dive", "slug": "duecare-500-agent-swarm-deep-dive", "summary": "Walk through the orchestration layer and supervisor flow used across the system."},
            {"id": "510", "title": "Phase 2 Model Comparison", "slug": "duecare-phase2-comparison", "summary": "Compare model variants selected for the next training step."},
            {"id": "520", "title": "Phase 3 Curriculum Builder", "slug": "duecare-520-phase3-curriculum-builder", "summary": "Assemble the curriculum used to prepare fine-tuning data."},
            {"id": "525", "title": "Uncensored 5-Grade Generator", "slug": "duecare-525-uncensored-grade-generator", "summary": "Generate WORST, BAD, NEUTRAL, GOOD, and BEST responses per prompt so Phase 3 has a richer synthetic curriculum than the stock benchmark alone."},
            {"id": "527", "title": "Uncensored Rubric Generator", "slug": "duecare-527-uncensored-rubric-generator", "summary": "Generate category-level rubric YAML, five scoring dimensions, and per-grade rules that the fine-tune and judges can consume directly."},
            {"id": "530", "title": "Phase 3 Unsloth Fine-tune", "slug": "duecare-530-phase3-unsloth-finetune", "summary": "Fine-tune Gemma and export deployment artifacts."},
            {"id": "540", "title": "Fine-tune Delta Visualizer", "slug": "duecare-540-finetune-delta-visualizer", "summary": "Before/after 530 plots: stock vs fine-tuned Gemma on the 6-dimension radar, per-prompt delta heatmap, and headline pass-rate lift. Video-ready."},
            {"id": "550", "title": "NGO Partner Survey Pipeline", "slug": "duecare-550-ngo-partner-survey-pipeline", "summary": "Human-feedback intake surface that turns NGO review into survey rows, email drafts, and partner-validated training examples for the Phase 3 merge."},
            {"id": "599", "title": "Model Improvement Opportunities Conclusion", "slug": "599-duecare-model-improvement-opportunities-conclusion", "summary": "Recap the curriculum build and the fine-tune outcome.", "conclusion": True},
        ],
    },
    {
        "label": "Results Dashboards",
        "intro": "Where do the evaluation outputs show up as the actual charts a judge sees? 600 is the measured proof surface for the whole late-suite story: one `comparison.json` in, a proof snapshot plus deeper Plotly diagnostics out. The next section does not replace that proof; it turns it into concrete operator, partner, and deployment workflows.",
        "notebooks": [
            {"id": "600", "title": "Results Dashboard", "slug": "duecare-600-results-dashboard", "summary": "CPU-only results dashboard that turns one comparison JSON into the proof snapshot, diagnostic panels, and the video/writeup/live-demo charts. Fastest judge-facing proof surface."},
        ],
    },
    {
        "label": "Solution Surfaces",
        "intro": "What does the project ship for a judge who cares about deployment, not just experimentation? Together with 600, this late-suite block exposes four public notebook surfaces and five deployment shapes: 600 is the measured proof surface, 610 is the capstone stitch, 620 is the running FastAPI plus migration-case operator workflow, and 650 is the partner-adoption path. It packages work already established in 400, 450, 500, and 530 instead of pretending those notebooks do not matter. The next section then breaks those deployment claims into one plain-English notebook per application.",
        "notebooks": [
            {"id": "610", "title": "Submission Walkthrough", "slug": "duecare-610-submission-walkthrough", "summary": "Capstone narrative that stitches 600, 620, and 650 together while explicitly pointing back to the technical substrate in 400, 450, 500, and 530."},
            {"id": "620", "title": "Demo API Endpoint Tour", "slug": "620-duecare-demo-api-endpoint-tour", "summary": "Walk all 17 FastAPI endpoints, including function-calling, document analysis, upload-first case intake, the migration-case workflow, and the live catalog-vs-app drift audit."},
            {"id": "650", "title": "Custom Domain Walkthrough", "slug": "duecare-650-custom-domain-walkthrough", "summary": "Add a medical_misinformation domain pack end-to-end, the adopter story that turns the same API and evaluation stack into a reusable partner deployment path."},
        ],
    },
    {
        "label": "Deployment Applications",
        "intro": "Which concrete products does DueCare actually become once the evaluation, API, and domain-pack machinery are already in place? This section separates the five deployment applications into one notebook each so a judge can understand the product story without reverse-engineering it from 620 and 650.",
        "notebooks": [
            {"id": "660", "title": "Enterprise Moderation", "slug": "duecare-660-enterprise-moderation", "summary": "Platform-scale queueing surface for screening risky recruitment posts, ads, and recruiter outreach before they reach workers."},
            {"id": "670", "title": "Private Client-Side Checker", "slug": "duecare-670-private-client-side-checker", "summary": "Worker-side private checker for one suspicious message or document at a time, with plain-language warning and next-step guidance."},
            {"id": "680", "title": "NGO API Triage", "slug": "duecare-680-ngo-api-triage", "summary": "Software-to-software triage surface: one structured request in, one structured analysis and routing response out."},
            {"id": "690", "title": "Migration Case Workflow", "slug": "duecare-690-migration-case-workflow", "summary": "Multi-document case-bundle workflow that turns uploaded files into a timeline, grounded findings, and draft complaint materials."},
            {"id": "695", "title": "Custom Domain Adoption", "slug": "duecare-695-custom-domain-adoption", "summary": "Plain-English partner-adoption playbook showing how DueCare becomes reusable in a new safety domain without Python changes."},
        ],
    },
    {
        "label": "Suite Conclusion",
        "intro": "The final closing notebook for the DueCare public Kaggle path. This is where the suite ends; open 899 to see the implementation surfaces plus the five deployment-application notebooks tied back into one late-suite story.",
        "notebooks": [
            {"id": "899", "title": "Solution Surfaces Conclusion", "slug": "899-duecare-solution-surfaces-conclusion", "summary": "Recap the late-suite implementation surfaces plus the five deployment applications and close the public Kaggle path.", "conclusion": True},
        ],
    },
]


def _md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def _kaggle_url(slug: str) -> str:
    return f"https://www.kaggle.com/code/taylorsamarel/{slug}"


def _public_url(notebook_id: str, slug: str) -> str:
    live_slug = LIVE_KERNEL_SLUGS.get(notebook_id)
    local_slug = LOCAL_KERNEL_SLUGS.get(notebook_id)
    public_slug = live_slug or PUBLIC_SLUG_OVERRIDES.get(notebook_id, local_slug or slug)
    return _kaggle_url(public_slug)


def _is_published(notebook_id: str) -> bool:
    """Return False when the notebook is not yet live on Kaggle."""
    if "(planned)" in notebook_id:
        return False
    bare = notebook_id.split()[0]
    return bare in LIVE_KERNEL_SLUGS


def _notebook_ids(phase: dict) -> str:
    return ", ".join(nb["id"] for nb in phase["notebooks"])


def _route_link(notebook_id: str, slug: str, label: str) -> str:
    if not _is_published(notebook_id):
        return f'<span style="color:#888">{label}<sup>*</sup></span>'
    return f'<a href="{_public_url(notebook_id, slug)}">{label}</a>'


def _tracked_notebook_count() -> int:
    return len(TRACKED_KERNELS)


def _live_notebook_count() -> int:
    return len(TRACKED_NOTEBOOK_IDS)


def _section_count() -> int:
    return len(PHASES)


TRACKED_KERNELS = discover_kernel_notebooks()
LOCAL_KERNEL_SLUGS = {
    entry.notebook_number: entry.slug
    for entry in TRACKED_KERNELS
}
LIVE_SLUG_MAP = json.loads(SLUG_MAP_PATH.read_text(encoding="utf-8"))
LIVE_KERNEL_SLUGS = {
    entry.notebook_number: live_kernel_id.split("/", 1)[1]
    for entry in TRACKED_KERNELS
    if (live_kernel_id := LIVE_SLUG_MAP.get(entry.dir_name))
}
TRACKED_NOTEBOOK_IDS = set(LOCAL_KERNEL_SLUGS)


def _coverage_rows() -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    for phase in PHASES:
        notebook_ids = [nb["id"].split()[0] for nb in phase["notebooks"]]
        first_id = notebook_ids[0]
        label_suffix = phase["label"].replace(" and ", " & ")
        rows.append(
            {
                "label": f"{first_id} {label_suffix}",
                "planned": len(phase["notebooks"]),
                "published": sum(1 for notebook_id in notebook_ids if _is_published(notebook_id)),
            }
        )
    return rows


HERO_COVERAGE_ROWS = _coverage_rows()


def _coverage_table_rows() -> list[dict[str, int | float | str]]:
    rows: list[dict[str, int | float | str]] = []
    for row in HERO_COVERAGE_ROWS:
        planned = int(row["planned"])
        live = int(row["published"])
        rows.append(
            {
                "section": str(row["label"]),
                "planned": planned,
                "live": live,
                "live_pct": (live / planned) if planned else 0.0,
            }
        )
    return rows


def _recommended_routes_html() -> str:
    rows = [
        (
            "Judge fast path",
            " -> ".join(
                [
                    _route_link("000", "duecare-000-index", "000"),
                    _route_link("010", "duecare-010-quickstart", "010"),
                    _route_link("600", "duecare-600-results-dashboard", "600"),
                    _route_link("610", "duecare-610-submission-walkthrough", "610"),
                    _route_link("899", "899-duecare-solution-surfaces-conclusion", "899"),
                ]
            ),
            "Shortest competition path: install proof, headline charts, capstone walkthrough, and final solution-surfaces close.",
        ),
        (
            "Technical proof path",
            " -> ".join(
                [
                    _route_link("100", "duecare-gemma-exploration", "100"),
                    _route_link("200", "duecare-cross-domain-proof", "200"),
                    _route_link("500", "duecare-500-agent-swarm-deep-dive", "500"),
                    _route_link("530", "duecare-530-phase3-unsloth-finetune", "530"),
                    _route_link("540", "duecare-540-finetune-delta-visualizer", "540"),
                    _route_link("600", "duecare-600-results-dashboard", "600"),
                ]
            ),
            "Best path for judges who want to verify that baseline evaluation, cross-domain generalization, orchestration, fine-tuning, and the public charts all connect.",
        ),
        (
            "Adopter path",
            " -> ".join(
                [
                    _route_link("010", "duecare-010-quickstart", "010"),
                    _route_link("200", "duecare-cross-domain-proof", "200"),
                    _route_link("680", "duecare-680-ngo-api-triage", "680"),
                    _route_link("690", "duecare-690-migration-case-workflow", "690"),
                    _route_link("695", "duecare-695-custom-domain-adoption", "695"),
                ]
            ),
            "Fastest path for an NGO, regulator, or engineering team deciding what actually ships before diving into the route-level and YAML-level implementation notebooks.",
        ),
    ]
    row_html = []
    for audience, route, why in rows:
        row_html.append(
            "    <tr>"
            f'<td style="padding: 6px 10px; vertical-align: top; width: 20%;"><b>{audience}</b></td>'
            f'<td style="padding: 6px 10px; vertical-align: top; width: 30%;">{route}</td>'
            f'<td style="padding: 6px 10px; vertical-align: top; width: 50%;">{why}</td>'
            "</tr>"
        )
    return (
        '<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">\n'
        '  <thead>\n'
        '    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">\n'
        '      <th style="padding: 8px 10px; text-align: left;">Route</th>\n'
        '      <th style="padding: 8px 10px; text-align: left;">Open These Notebooks</th>\n'
        '      <th style="padding: 8px 10px; text-align: left;">Why This Route Exists</th>\n'
        '    </tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        + "\n".join(row_html)
        + '\n  </tbody>\n'
        '</table>'
    )


def _section_cell_markdown(phase: dict, next_phase: dict | None = None) -> str:
    rows = []
    for nb in phase["notebooks"]:
        is_conclusion = bool(nb.get("conclusion"))
        row_border = (
            'border-top: 2px solid #d1d5da;'
            if is_conclusion
            else ''
        )
        if _is_published(nb["id"]):
            url = _public_url(nb["id"], nb["slug"])
            label = f'<a href="{url}"><b>{nb["id"]}</b>&nbsp;&nbsp;{nb["title"]}</a>'
        else:
            # Not yet live on Kaggle — render title without a link so
            # judges do not click through to a 404. Keep the numeric id
            # visible so the index still reads as the full suite map.
            label = (
                f'<span style="color:#555"><b>{nb["id"]}</b>&nbsp;&nbsp;{nb["title"]}</span>'
                f'<br><span style="color:#888;font-size:11px">(pending publication)</span>'
            )
        rows.append(
            f'    <tr style="{row_border}">'
            f'<td style="padding: 6px 12px; vertical-align: top; white-space: nowrap;">{label}</td>'
            f'<td style="padding: 6px 12px; vertical-align: top;">{nb["summary"]}</td>'
            '</tr>'
        )
    table = (
        '<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">\n'
        '  <thead>\n'
        '    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">\n'
        '      <th style="padding: 8px 12px; text-align: left; width: 34%;">Notebook</th>\n'
        '      <th style="padding: 8px 12px; text-align: left; width: 66%;">Notebook Summary</th>\n'
        '    </tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        + "\n".join(rows) + "\n"
        '  </tbody>\n'
        '</table>'
    )
    if next_phase is None:
        next_line = "This is the final section in the suite. Open the bordered conclusion row to close the public Kaggle path."
    else:
        next_line = f"Next section is **{next_phase['label']}** ({_notebook_ids(next_phase)})."
    return (
        f"## {phase['label']}\n"
        f"\n"
        f"{phase['intro']}\n"
        f"\n"
        f"{next_line}\n"
        f"\n"
        f"{table}"
    )


def _header_markdown() -> str:
    total_notebooks = _tracked_notebook_count()
    total_sections = _section_count()
    header_table = canonical_header_table(
        inputs_html=(
            f"No external inputs. This index is generated from the notebook registry in <code>scripts/build_index_notebook.py</code> and links all <code>{total_notebooks}</code> tracked Kaggle notebooks across <code>{total_sections}</code> sections."
        ),
        outputs_html=(
            "A section-by-section navigation map, three recommended reading routes for judges and adopters, direct links to the public repository and judges guide, and a reliable handoff into the fastest proof notebooks."
        ),
        prerequisites_html=(
            "CPU-only. No model loading, no API keys, and no attached datasets required. Open linked Kaggle notebooks in new tabs as needed."
        ),
        runtime_html="Under 5 seconds. Static navigation notebook only.",
        pipeline_html=(
            "Start of the suite. Judge fast path: "
            f"<a href='{_public_url('010', 'duecare-010-quickstart')}'>010</a> -> "
            f"<a href='{_public_url('600', 'duecare-600-results-dashboard')}'>600</a> -> "
            f"<a href='{_public_url('610', 'duecare-610-submission-walkthrough')}'>610</a> -> "
            f"<a href='{_public_url('899', '899-duecare-solution-surfaces-conclusion')}'>899</a>."
        ),
    )
    return f"""# DueCare 000 Index

**The public front door for the DueCare competition submission.** DueCare tests whether Gemma 4 can act as a private, on-device safety judge for trafficking, exploitation, tax evasion, and financial crime scenarios. This notebook does not run models. Its job is to route a judge, adopter, or technical reviewer to the right proof notebook quickly and honestly.

The suite currently tracks **{total_notebooks} Kaggle notebooks** across **{total_sections} sections**. The public repository is on [GitHub]({PUBLIC_REPO_URL}). The focused five-minute verification guide for judges is [docs/FOR_JUDGES.md]({JUDGES_GUIDE_URL}). The competition writeup listing is on the [Gemma 4 Good Hackathon writeups page]({WRITEUP_URL}).

{header_table}

### Recommended reading routes

{_recommended_routes_html()}

### Why this suite exists

Platform operators, NGOs, and labor-rights investigators face a duty-of-care standard they cannot meet by sending sensitive migrant-worker case data to frontier APIs. DueCare asks whether Gemma 4 can be the local substrate for five concrete deployment applications: enterprise moderation, client-side verification, NGO-facing API triage, multi-document migration-case workflow support, and partner adoption into new safety domains. The sections below follow that story end to end: setup, baseline behavior, evaluation mechanics, model comparisons, adversarial stress, improvement, implementation surfaces, and the plain-English deployment applications.
"""


def _conclusion_markdown() -> str:
    return ""


FINAL_PRINT = (
    "print('Index handoff >>> 010 Quickstart https://www.kaggle.com/code/taylorsamarel/010-duecare-quickstart-in-5-minutes | 600 Results Dashboard https://www.kaggle.com/code/taylorsamarel/600-duecare-results-dashboard | 610 Submission Walkthrough https://www.kaggle.com/code/taylorsamarel/610-duecare-submission-walkthrough')\n"
)


HERO_CODE = '''from IPython.display import HTML, display

stats = [
    {"label": "Tracked notebooks", "value": "__TOTAL_NOTEBOOKS__", "accent": "#4c78a8", "bg": "#eff6ff"},
    {"label": "Sections", "value": "__TOTAL_SECTIONS__", "accent": "#10b981", "bg": "#ecfdf5"},
    {"label": "Live on Kaggle", "value": "__LIVE_NOTEBOOKS__", "accent": "#f59e0b", "bg": "#fffbeb"},
    {"label": "Deployment apps", "value": "5", "accent": "#ef4444", "bg": "#fef2f2"},
]

stat_cards = []
for stat in stats:
    stat_cards.append(
        f'<div style="display:inline-block;vertical-align:top;width:23%;margin:4px 1%;padding:14px 16px;'
        f'background:{stat["bg"]};border-left:5px solid {stat["accent"]};border-radius:4px;'
        f'font-family:system-ui,-apple-system,sans-serif">'
        f'<div style="font-size:11px;font-weight:600;color:{stat["accent"]};text-transform:uppercase;'
        f'letter-spacing:0.04em">{stat["label"]}</div>'
        f'<div style="font-size:26px;font-weight:700;color:#1f2937;margin:4px 0 0 0">{stat["value"]}</div>'
        '</div>'
    )

hero_html = (
    \'''<div style="background:linear-gradient(135deg,#1e3a8a 0%,#4c78a8 100%);color:white;\'''
    \'''padding:24px 28px;border-radius:8px;margin:10px 0 6px 0;font-family:system-ui,-apple-system,sans-serif">\'''
    \'''<div style="font-size:11px;font-weight:600;letter-spacing:0.12em;opacity:0.8;\'''
    \'''text-transform:uppercase">DueCare - Gemma 4 Good Hackathon</div>\'''
    \'''<div style="font-size:30px;font-weight:700;margin:6px 0 4px 0">Due Care for AI Safety</div>\'''
    \'''<div style="font-size:15px;opacity:0.92">Fine-tuned Gemma 4 as an on-device safety judge for migrant-worker protection.\'''
    \'''<br>__TOTAL_NOTEBOOKS__ notebooks across __TOTAL_SECTIONS__ sections. One duty-of-care standard. Five deployment applications.</div>\'''
    \'''</div>\'''
    + '<div style="margin:0 0 8px 0">' + ''.join(stat_cards) + '</div>'
)

display(HTML(hero_html))
'''.replace('__TOTAL_NOTEBOOKS__', str(_tracked_notebook_count())).replace(
    '__TOTAL_SECTIONS__',
    str(_section_count()),
).replace(
    '__LIVE_NOTEBOOKS__',
    str(_live_notebook_count()),
)


COVERAGE_CODE = '''import pandas as pd
from IPython.display import Markdown, display

coverage = pd.DataFrame(__COVERAGE_ROWS__)

display(Markdown('### Suite coverage by section'))
display(
    coverage.style
      .format({'planned': '{:,}', 'live': '{:,}', 'live_pct': '{:.0%}'})
      .bar(subset=['planned'], color='#e5e7eb')
      .bar(subset=['live'], color='#4c78a8')
      .bar(subset=['live_pct'], color='#10b981')
      .set_properties(subset=['section'], **{'text-align': 'left', 'white-space': 'pre-wrap'})
      .set_properties(subset=['planned', 'live', 'live_pct'], **{'text-align': 'center'})
      .set_table_styles([{'selector': 'th', 'props': [('text-align', 'left')]}])
      .hide(axis='index')
)
'''.replace(
    '__COVERAGE_ROWS__',
    json.dumps(_coverage_table_rows(), indent=2),
)


def build() -> None:
    cells = [
        # Compact hero first so the notebook front door stays tight in Kaggle's saved viewer.
        {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [],
         'source': HERO_CODE.splitlines(keepends=True)},
        _md(_header_markdown()),
        {'cell_type': 'code', 'execution_count': None,
         'metadata': {'_kg_hide-input': True, 'jupyter': {'source_hidden': True}},
         'outputs': [],
         'source': COVERAGE_CODE.splitlines(keepends=True)},
    ]
    for i, phase in enumerate(PHASES):
        next_phase = PHASES[i + 1] if i + 1 < len(PHASES) else None
        cells.append(_md(_section_cell_markdown(phase, next_phase)))

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
            "kaggle": {"accelerator": "none", "isInternetEnabled": True},
        },
        "cells": cells,
    }
    nb = harden_notebook(nb, filename=FILENAME, requires_gpu=False)
    patch_final_print_cell(nb, final_print_src=FINAL_PRINT, marker="Index handoff >>>")

    NB_DIR.mkdir(parents=True, exist_ok=True)
    KAGGLE_KERNELS.mkdir(parents=True, exist_ok=True)

    nb_path = NB_DIR / FILENAME
    nb_path.write_text(json.dumps(nb, indent=1), encoding="utf-8")

    kernel_dir = KAGGLE_KERNELS / KERNEL_DIR_NAME
    kernel_dir.mkdir(parents=True, exist_ok=True)
    (kernel_dir / FILENAME).write_text(json.dumps(nb, indent=1), encoding="utf-8")

    meta = {
        "id": KERNEL_ID,
        "title": KERNEL_TITLE,
        "code_file": FILENAME,
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
    (kernel_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Wrote {nb_path}")
    print(f"Wrote {kernel_dir / FILENAME}")
    print(f"Wrote {kernel_dir / 'kernel-metadata.json'}")


if __name__ == "__main__":
    build()
