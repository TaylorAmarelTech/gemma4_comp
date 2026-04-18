#!/usr/bin/env python3
"""Build the orientation glossary notebook for the DueCare notebook suite."""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import canonical_header_table, patch_final_print_cell
from build_index_notebook import PHASES as INDEX_PHASES
from notebook_hardening_utils import DUECARE_VERSION, harden_notebook
from _public_slugs import PUBLIC_SLUG_OVERRIDES


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"
FILENAME = "005_glossary.ipynb"
KERNEL_DIR_NAME = "duecare_005_glossary"
KERNEL_ID = "taylorsamarel/duecare-005-glossary"
KERNEL_TITLE = 'DueCare 005 Glossary'
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["gemma", "safety", "llm", "trafficking", "tutorial"]


def _md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def _code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def _kaggle_url(nb_id: str, default_slug: str) -> str:
    slug = PUBLIC_SLUG_OVERRIDES.get(nb_id, default_slug)
    return f"https://www.kaggle.com/code/taylorsamarel/{slug}"


URL_000 = _kaggle_url("000", "duecare-000-index")
URL_010 = _kaggle_url("010", "duecare-010-quickstart")
URL_099 = _kaggle_url("099", "099-duecare-orientation-and-background-and-package-setup-conclusion")
URL_100 = _kaggle_url("100", "duecare-gemma-exploration")
URL_200 = _kaggle_url("200", "duecare-200-cross-domain-proof")
URL_500 = _kaggle_url("500", "duecare-500-agent-swarm-deep-dive")
URL_600 = _kaggle_url("600", "duecare-600-results-dashboard")
URL_610 = _kaggle_url("610", "duecare-610-submission-walkthrough")
URL_620 = _kaggle_url("620", "620-duecare-demo-api-endpoint-tour")
URL_650 = _kaggle_url("650", "650-duecare-custom-domain-walkthrough")
URL_899 = _kaggle_url("899", "899-duecare-solution-surfaces-conclusion")

NOTEBOOK_LINKS = {
    "000": ("duecare-000-index", "000 Index"),
    "010": ("duecare-010-quickstart", "010 Quickstart"),
    "099": ("099-duecare-orientation-and-background-and-package-setup-conclusion", "099 Conclusion"),
    "100": ("duecare-gemma-exploration", "100 Gemma Exploration"),
    "150": ("150-duecare-free-form-gemma-playground", "150 Free Form Gemma Playground"),
    "155": ("155-duecare-tool-calling-playground", "155 Tool Calling Playground"),
    "160": ("160-duecare-image-processing-playground", "160 Image Processing Playground"),
    "180": ("duecare-180-multimodal-document-inspector", "180 Multimodal Document Inspector"),
    "200": ("duecare-200-cross-domain-proof", "200 Cross-Domain Proof"),
    "500": ("duecare-500-agent-swarm-deep-dive", "500 Agent Swarm Deep Dive"),
    "530": ("duecare-530-phase3-unsloth-finetune", "530 Phase 3 Unsloth Fine-tune"),
    "540": ("duecare-540-finetune-delta-visualizer", "540 Fine-tune Delta Visualizer"),
    "600": ("duecare-600-results-dashboard", "600 Results Dashboard"),
    "610": ("duecare-610-submission-walkthrough", "610 Submission Walkthrough"),
    "620": ("620-duecare-demo-api-endpoint-tour", "620 Demo API Endpoint Tour"),
    "650": ("650-duecare-custom-domain-walkthrough", "650 Custom Domain Walkthrough"),
    "899": ("899-duecare-solution-surfaces-conclusion", "899 Conclusion"),
}

# Why notebook IDs and section order do not line up: ID first digits reflect
# the functional band (100s exploration, 200s comparison, 300s adversarial,
# etc.) while section order reflects the reading narrative. The two are not
# the same; the reading narrative pulls notebooks from their functional
# bands into the order a reader should meet them. The section order below is
# derived directly from 000's PHASES registry so 005 cannot drift away from
# the public front-door notebook.

READING_PATHS = [
    ("Judge fast path", ["000", "010", "600", "610", "899"], "Shortest competition path: prove the install, open the headline dashboard, then close on the capstone and solution surfaces."),
    ("Technical proof path", ["100", "200", "500", "530", "540", "600"], "Best route for a judge checking baseline behavior, cross-domain generalization, orchestration, fine-tuning, and the public charts."),
    ("Adopter path", ["010", "200", "620", "650"], "Fastest route for an NGO, regulator, or engineering team deciding whether the system is reusable in their own stack."),
    ("Interactive demos", ["150", "155", "160", "180"], "Type prompts, trigger tool-calling, upload images, and inspect multimodal recruitment documents."),
    ("Evaluation depth", ["200", "500", "530", "600", "610"], "One compact route from proof of generalization through the improvement spine into the public-facing results and capstone walkthrough."),
]


# ---- Glossary terms -------------------------------------------------------
# Columns: term, meaning, primary notebook (id, slug, label) or None
GLOSSARY_ROWS = [
    # Project framing
    ("DueCare", "The project and notebook suite: an on-device LLM safety harness for sensitive domains, named for the duty-of-care standard.", ("000", "duecare-000-index", "000 Index")),
    ("Duty of care", "The common-law standard codified in California Civil Code section 1714(a) and applied by a California jury in March 2026 when it found Meta and Google negligent for defective platform design.", ("000", "duecare-000-index", "000 Index")),
    ("Composite character", "A named but fictional worker (Maria, Ramesh) used for storytelling without exposing a real person.", None),
    ("Privacy as invariant", "Raw case data never leaves the deployment boundary; every solution surface is designed to meet this before any accuracy claim.", ("010", None, "010 Quickstart")),

    # Notation
    ("NNN prefix", "Three-digit zero-padded notebook ID. The first digit names the functional band (100s exploration, 200s comparison, 300s adversarial), not the reading order. Step of 10 between siblings leaves room for insertion.", ("000", "duecare-000-index", "000 Index")),
    ("N99 conclusion", "The section-closing notebook at the top of each 100-slot band (099, 199 through 899). Recap, key points, and the next-section handoff.", ("099", "099-duecare-orientation-and-background-and-package-setup-conclusion", "099 Conclusion")),
    ("Section map", "The 9-section reading order shown in 000 Index: Background and Package Setup, Free Form Exploration, Baseline Text Evaluation Framework, Baseline Text Comparisons, Advanced Evaluation, Advanced Prompt-Test Generation, Adversarial Prompt-Test Evaluation, Model Improvement Opportunities, Solution Surfaces.", ("000", "duecare-000-index", "000 Index")),

    # Data and grading
    ("Domain pack", "A packaged safety domain with prompts, rubric criteria, taxonomy, evidence, and deployment context.", ("200", "duecare-200-cross-domain-proof", "200 Cross-Domain Proof")),
    ("Graded response", "A reference answer on a quality ladder (worst, neutral, good, best) for the same prompt.", ("110", None, "110 Prompt Prioritizer")),
    ("Rubric", "The criterion set used to judge whether a response is safe, complete, accurate, and actionable.", ("430", None, "430 Rubric Evaluation")),
    ("Anchored grading", "Scoring by comparing against hand-written best and worst references, not against a free-floating judge.", ("250", "duecare-250-comparative-grading", "250 Comparative Grading")),
    ("LLM judge", "A model used to score another model's answer across dimensions rather than answering the task itself.", ("410", "duecare-410-llm-judge-grading", "410 LLM Judge")),
    ("Contextual judge", "A judge that evaluates the response relative to the prompt context, not in isolation.", ("450", "duecare-contextual-judge", "450 Contextual Worst-Response")),
    ("Failure taxonomy", "The categorized description of where the model fails: refusal, legality, actionability, empathy, and more.", ("440", "duecare-per-prompt-rubric-generator", "440 Per-Prompt Rubric Generator")),

    # Prompt engineering
    ("Prompt prioritizer", "The curator that selects the highest-value prompts from the seed corpus before any scored evaluation.", ("110", None, "110 Prompt Prioritizer")),
    ("Prompt remixer", "A generator that expands a curated prompt into alternative phrasings and adversarial variants.", ("120", "duecare-prompt-remixer", "120 Prompt Remixer")),
    ("Prompt factory", "The scaled pipeline that generates, validates, and ranks large volumes of test prompts by victim impact.", ("310", "duecare-310-prompt-factory", "310 Prompt Factory")),
    ("Per-prompt rubric", "A rubric synthesized for a single prompt so scoring matches the specific failure mode that prompt targets.", ("440", "duecare-per-prompt-rubric-generator", "440 Per-Prompt Rubric Generator")),

    # Evaluation
    ("Cross-domain proof", "The claim that the same harness works across trafficking, tax evasion, and financial crime.", ("200", "duecare-200-cross-domain-proof", "200 Cross-Domain Proof")),
    ("RAG", "Retrieval-augmented generation: inject domain evidence or rubric context before generating a response.", ("260", "duecare-260-rag-comparison", "260 RAG Comparison")),
    ("Function calling", "Structured tool invocation by the model using native function-call syntax rather than plain-text instructions.", ("400", "duecare-400-function-calling-multimodal", "400 Function Calling and Multimodal")),
    ("Multimodal", "Using both text and image inputs, such as document photos, in a single evaluation.", ("160", "160-duecare-image-processing-playground", "160 Image Processing Playground")),
    ("Safety line", "The measured threshold where Gemma starts to produce unsafe or uncensored output under adversarial pressure.", ("320", "duecare-finding-gemma-4-safety-line", "320 Finding Gemma 4 Safety Line")),
    ("Playground", "An interactive notebook with an ipywidgets textarea or file upload so a reader can type any prompt or upload any image and see Gemma respond live.", ("150", "150-duecare-free-form-gemma-playground", "150 Free Form Gemma Playground")),

    # Orchestration and training
    ("Agent swarm", "The set of autonomous agents coordinated to probe, grade, summarize, and publish results.", ("500", "duecare-500-agent-swarm-deep-dive", "500 Agent Swarm Deep Dive")),
    ("Coordinator", "The supervisory control layer that routes tasks, often using Gemma 4 native function calling.", ("500", "duecare-500-agent-swarm-deep-dive", "500 Agent Swarm Deep Dive")),
    ("Curriculum", "The training dataset assembled for fine-tuning, usually from graded prompts and contrastive examples.", ("520", "duecare-520-phase3-curriculum-builder", "520 Phase 3 Curriculum Builder")),
    ("Unsloth", "The fine-tuning stack used here for efficient Gemma LoRA training and export.", ("530", "duecare-530-phase3-unsloth-finetune", "530 Phase 3 Unsloth Fine-tune")),
    ("LoRA", "Low-Rank Adaptation: a parameter-efficient fine-tuning method that trains small adapters instead of the full model.", ("530", "duecare-530-phase3-unsloth-finetune", "530 Phase 3 Unsloth Fine-tune")),
    ("4-bit quantization", "Loading a model in 4-bit weights (nf4 via bitsandbytes) so a 9B Gemma fits on a single Kaggle T4.", ("150", "150-duecare-free-form-gemma-playground", "150 Free Form Gemma Playground")),
    ("SuperGemma", "Internal shorthand for the DueCare-fine-tuned Gemma 4 variant produced by the 530 Unsloth path. Not a public product name.", ("530", "duecare-530-phase3-unsloth-finetune", "530 Phase 3 Unsloth Fine-tune")),

    # Export and deployment (all four surfaces in one place)
    ("GGUF", "A quantized model format used for local inference in llama.cpp.", ("530", "duecare-530-phase3-unsloth-finetune", "530 Phase 3 Unsloth Fine-tune")),
    ("LiteRT", "A mobile-oriented runtime path for private on-device deployment.", None),
    ("Enterprise surface", "Deployment shape 1 of 4: platform-side content moderation, compliance monitoring, NGO review dashboards.", ("600", None, "600 Results Dashboard")),
    ("Client surface", "Deployment shape 2 of 4: on-device verification on a single migrant worker's laptop or phone.", ("010", None, "010 Quickstart")),
    ("NGO API surface", "Deployment shape 3 of 4: a generalized public API endpoint backed by the agent swarm orchestration layer.", ("620", "620-duecare-demo-api-endpoint-tour", "620 Demo API Endpoint Tour")),
    ("Case analysis surface", "Deployment shape 4 of 4: tool-backed, multimodal, contextual case review for victims and advocates.", ("650", "650-duecare-custom-domain-walkthrough", "650 Custom Domain Walkthrough")),

    # Safety and domain
    ("PII gate", "The anonymization boundary that strips or generalizes sensitive personal information before downstream use.", ("610", "duecare-610-submission-walkthrough", "610 Submission Walkthrough")),
    ("Migration corridor", "A worker movement pattern between countries, such as Nepal to UAE or Philippines to Hong Kong.", ("200", "duecare-200-cross-domain-proof", "200 Cross-Domain Proof")),
    ("ILO indicators", "Forced-labor and trafficking indicators defined by the International Labour Organization.", ("200", "duecare-200-cross-domain-proof", "200 Cross-Domain Proof")),
    ("Named partners", "Public organizations the project references as plausible real-world deployers: Polaris Project, IJM, ECPAT, POEA, BP2MI, HRD Nepal.", ("610", "duecare-610-submission-walkthrough", "610 Submission Walkthrough")),
]


def _section_order_table_html() -> str:
    rows = []
    for order, phase in enumerate(INDEX_PHASES, start=1):
        notebooks = ", ".join(
            f"{nb['id']} {nb['title']}" for nb in phase["notebooks"] if not nb.get("conclusion")
        )
        conclusion_nb = next(
            (nb for nb in phase["notebooks"] if nb.get("conclusion")), None
        )
        close_label = f'{conclusion_nb["id"]} Conclusion' if conclusion_nb else '(no section close)'
        rows.append(
            '    <tr>'
            f'<td style="padding: 6px 10px; white-space: nowrap; font-family: monospace;">{order}</td>'
            f'<td style="padding: 6px 10px;"><b>{phase["label"]}</b></td>'
            f'<td style="padding: 6px 10px;">{notebooks}</td>'
            f'<td style="padding: 6px 10px; white-space: nowrap;">{close_label}</td>'
            '</tr>'
        )
    return (
        '<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">\n'
        '  <thead>\n'
        '    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">\n'
        '      <th style="padding: 8px 10px; text-align: left; width: 8%;">Order</th>\n'
        '      <th style="padding: 8px 10px; text-align: left; width: 28%;">Section</th>\n'
        '      <th style="padding: 8px 10px; text-align: left; width: 50%;">Primary notebooks</th>\n'
        '      <th style="padding: 8px 10px; text-align: left; width: 14%;">Section close</th>\n'
        '    </tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        + "\n".join(rows) + "\n"
        '  </tbody>\n'
        '</table>'
    )


def _reading_paths_table_html() -> str:
    rows = []
    for goal, route_ids, why in READING_PATHS:
        path_html = " &rarr; ".join(
            f'<a href="{_kaggle_url(notebook_id, NOTEBOOK_LINKS[notebook_id][0])}"><b>{notebook_id}</b></a>'
            for notebook_id in route_ids
        )
        rows.append(
            '    <tr>'
            f'<td style="padding: 6px 10px; white-space: nowrap;"><b>{goal}</b></td>'
            f'<td style="padding: 6px 10px; font-family: monospace; font-size: 0.92em;">{path_html}</td>'
            f'<td style="padding: 6px 10px;">{why}</td>'
            '</tr>'
        )
    return (
        '<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">\n'
        '  <thead>\n'
        '    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">\n'
        '      <th style="padding: 8px 10px; text-align: left; width: 18%;">Goal</th>\n'
        '      <th style="padding: 8px 10px; text-align: left; width: 42%;">Path</th>\n'
        '      <th style="padding: 8px 10px; text-align: left; width: 40%;">Why this path</th>\n'
        '    </tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        + "\n".join(rows) + "\n"
        '  </tbody>\n'
        '</table>'
    )


def _glossary_table_html(rows: list[tuple]) -> str:
    body = []
    for term, meaning, primary in rows:
        if primary:
            nb_id, slug_override, label = primary
            # If an explicit slug was passed, use it; otherwise fall back to the
            # public-slug override table or the canonical duecare-NNN pattern.
            if slug_override:
                url = _kaggle_url(nb_id, slug_override)
            else:
                # Synthesize the canonical slug; PUBLIC_SLUG_OVERRIDES will
                # redirect when necessary (for example 110, 600, 420, 430).
                url = _kaggle_url(nb_id, f"duecare-{nb_id}-unused")
            primary_cell = f'<a href="{url}">{label}</a>'
        else:
            primary_cell = '<span style="color: #6a737d;">&mdash;</span>'
        body.append(
            '    <tr>'
            f'<td style="padding: 6px 10px; white-space: nowrap;"><b>{term}</b></td>'
            f'<td style="padding: 6px 10px;">{meaning}</td>'
            f'<td style="padding: 6px 10px; white-space: nowrap;">{primary_cell}</td>'
            '</tr>'
        )
    return (
        '<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">\n'
        '  <thead>\n'
        '    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">\n'
        '      <th style="padding: 8px 10px; text-align: left; width: 22%;">Term</th>\n'
        '      <th style="padding: 8px 10px; text-align: left; width: 54%;">Meaning</th>\n'
        '      <th style="padding: 8px 10px; text-align: left; width: 24%;">Primary notebook</th>\n'
        '    </tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        + "\n".join(body) + "\n"
        '  </tbody>\n'
        '</table>'
    )


# Group terms into thematic sub-tables so they are scannable
GLOSSARY_GROUPS = [
    ("Project framing", GLOSSARY_ROWS[0:4]),
    ("Notation and structure", GLOSSARY_ROWS[4:7]),
    ("Data and grading", GLOSSARY_ROWS[7:14]),
    ("Prompt engineering", GLOSSARY_ROWS[14:18]),
    ("Evaluation", GLOSSARY_ROWS[18:24]),
    ("Orchestration and training", GLOSSARY_ROWS[24:31]),
    ("Export and deployment", GLOSSARY_ROWS[31:36]),
    ("Safety and domain", GLOSSARY_ROWS[36:]),
]


def _header_markdown() -> str:
        header_table = canonical_header_table(
                inputs_html="Pinned DueCare packages only; no domain-specific data or external APIs.",
                outputs_html="Glossary tables, a route map derived from the 000 phase registry, and a live registry proof from the installed packages.",
                prerequisites_html="Kaggle CPU kernel with internet enabled. No GPU. No API keys.",
                runtime_html="Under 2 minutes end-to-end.",
                pipeline_html=(
                        f'Background and Package Setup section. Previous: <a href="{URL_000}">000 Index</a>. '
                        f'Next: <a href="{URL_010}">010 Quickstart</a>. '
                        f'Section close: <a href="{URL_099}">099 Conclusion</a>.'
                ),
        )
        return f"""# 005: DueCare Glossary and Reading Map

This notebook defines the project vocabulary and maps each term back to the notebook that demonstrates it. Open it whenever a label, route, or section order in the suite needs to be pinned down before clicking deeper.

{header_table}

This glossary is the suite's second navigation surface. [**000 Index**]({URL_000}) answers *where to click next*; 005 answers *what the notebook names and deployment-surface terms mean*, and gives you clickable routes that stay aligned with the live Kaggle slugs.

**Privacy is non-negotiable** is the project's load-bearing invariant: raw migrant-worker case data never leaves the deployment boundary. Every term on this page maps back to a notebook that either enforces that boundary (Anonymizer, AgentSupervisor, the on-device GGUF runtime) or proves the model still meets its safety rubric while doing so. The named partners who would deploy DueCare against this guarantee — Polaris, IJM, ECPAT, POEA, BP2MI, HRD Nepal, IOM — appear in the Solution Surfaces section.

This notebook is CPU-only by design. Gemma 4 inference starts in [100 Gemma Exploration]({URL_100}) on a T4 GPU.
"""


AT_A_GLANCE_INTRO = """## At a glance
"""


AT_A_GLANCE_CODE = f'''from IPython.display import HTML, display

_PALETTE = {{
    "primary": "#4c78a8", "success": "#10b981", "info": "#3b82f6",
    "warning": "#f59e0b", "muted": "#6b7280", "danger": "#ef4444",
    "bg_primary": "#eff6ff", "bg_success": "#ecfdf5",
    "bg_info": "#eff6ff", "bg_warning": "#fffbeb", "bg_danger": "#fef2f2",
}}

def _stat_card(value, label, sub, kind="primary"):
    accent = _PALETTE[kind]
    bg = _PALETTE.get(f"bg_{{kind}}", _PALETTE["bg_info"])
    return (
        f'<div style="display:inline-block;vertical-align:top;width:22%;'
        f'margin:4px 1%;padding:14px 16px;background:{{bg}};'
        f'border-left:5px solid {{accent}};border-radius:4px;'
        f'font-family:system-ui,-apple-system,sans-serif">'
        f'<div style="font-size:11px;font-weight:600;color:{{accent}};'
        f'text-transform:uppercase;letter-spacing:0.04em">{{label}}</div>'
        f'<div style="font-size:26px;font-weight:700;color:#1f2937;margin:4px 0 0 0">{{value}}</div>'
        f'<div style="font-size:12px;color:{{_PALETTE["muted"]}};margin-top:2px">{{sub}}</div>'
        f'</div>'
    )

n_terms = {len(GLOSSARY_ROWS)}
cards = [
    _stat_card(f"{{n_terms}}",  "glossary terms", "anchored to notebooks",   "primary"),
    _stat_card("8",             "topic groups",   "framing -> deployment",   "info"),
    _stat_card("9",             "sections",       "reading narrative",       "warning"),
    _stat_card("3",             "reading paths",  "judge / adopter / depth", "success"),
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))
'''


SECTION_MAP_INTRO = """## Section order

DueCare ships as 9 sections. Read them top to bottom for the full project arc. Notebook IDs do not align one-to-one with section order, because ID first digits reflect functional bands (100s exploration, 200s comparison, 300s adversarial) while section order reflects the reading narrative. The two are independent on purpose.

"""

READING_PATHS_INTRO = """## Reading paths

Paths through the suite for different reader goals. These routes complement the 000 Index and every notebook ID below is clickable.

"""


SUNBURST_INTRO = """## Suite map (sunburst)

One image showing the full suite: 14 sections at the center ring, notebooks at the outer ring, sized by relative content weight. Interactive — click a section to zoom, hover a leaf to see the title.
"""

SUNBURST_CODE = '''import subprocess, sys
try:
    import plotly.graph_objects as go  # noqa
except Exception:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'plotly'])
import plotly.graph_objects as go
import plotly.io as pio
# Ensure the figure renders inline in the Kaggle saved output viewer.
pio.renderers.default = 'notebook_connected'
from IPython.display import HTML, display

_SECTIONS = [
    ('000 Background',      ['000 Index','005 Glossary','010 Quickstart','099 Conclusion']),
    ('100 Free Form',       ['100 Gemma Exploration','150 Playground','152 Chat','155 Tool Calling','160 Image','170 Context Injection','180 Multimodal','190 RAG Inspector','199 Conclusion']),
    ('180 Jailbreak',       ['181 Viewer','182 Refusal Direction','183 Amplifier','184 Frontier Consult','185 Comparison','186 Stock','187 Abliterated','188 Uncensored','189 Cracked 31B']),
    ('200 Text Eval',       ['105 Corpus','110 Prioritizer','120 Remixer','130 Exploration','140 Mechanics','299 Conclusion']),
    ('300 Comparisons',     ['200 Cross-Domain','210 OSS','220 Ollama','230 Mistral','240 OpenRouter','250 Comparative','260 RAG','270 Generations','399 Conclusion']),
    ('400 Advanced Eval',   ['300 Adversarial','335 Attack Vectors','400 FC+Multimodal','410 LLM Judge','420 Conversation','460 Citations','499 Conclusion']),
    ('500 Prompt Gen',      ['310 Factory','430 Rubric','440 Per-Prompt','699 Conclusion']),
    ('600 Adversarial Eval',['320 Safety Line','450 Worst Response','799 Conclusion']),
    ('700 Improvement',     ['500 Agent Swarm','510 Phase 2','520 Curriculum','530 Fine-tune','540 Delta','599 Conclusion']),
    ('800 Results',         ['600 Dashboard']),
    ('900 Solution',        ['610 Submission','620 Demo API','650 Custom Domain']),
    ('999 Close',           ['899 Conclusion']),
]

labels = ['DueCare Suite']
parents = ['']
values = [0]
colors = ['#1f2937']
palette = ['#4c78a8','#59a14f','#f58518','#e45756','#b279a2','#edc948','#af7aa1','#ff9da7','#9c755f','#bab0ac','#76b7b2','#d67195']

for i, (sec, nbs) in enumerate(_SECTIONS):
    labels.append(sec); parents.append('DueCare Suite'); values.append(len(nbs)); colors.append(palette[i % len(palette)])
    for nb in nbs:
        labels.append(nb); parents.append(sec); values.append(1); colors.append(palette[i % len(palette)])

fig = go.Figure(go.Sunburst(
    labels=labels, parents=parents, values=values, branchvalues='total',
    marker=dict(colors=colors, line=dict(color='white', width=1.5)),
    hovertemplate='<b>%{label}</b><extra></extra>',
    insidetextfont=dict(size=11, color='white'),
))
fig.update_layout(
    title=dict(text='DueCare notebook suite — 14 sections, 50+ notebooks', font_size=17),
    template='plotly_white', height=620, margin=dict(t=60, l=10, r=10, b=10),
)
fig.show()

display(HTML(
    '<div style="margin:10px 0;padding:10px 14px;background:#eff6ff;border-left:4px solid #3b82f6;'
    'border-radius:3px;color:#222;font-family:system-ui,-apple-system,sans-serif;font-size:13px">'
    'Every leaf above links to a notebook in the glossary tables below. Click a section name to zoom.'
    '</div>'
))
'''


REGISTRY_INTRO = """## Registries on disk

The glossary is not just prose. The cell below imports the shipped DueCare packages and prints the live registries so you can confirm the domain packs, tasks, agents, and model adapters actually exist. A healthy run should show nonzero model, domain, task, and agent counts; the assertions below fail loudly if any of them are empty.
"""


REGISTRY_CODE = """from duecare.agents import agent_registry
from duecare.domains import domain_registry, register_discovered
from duecare.models import model_registry
from duecare.tasks import task_registry

register_discovered()

model_count = len(model_registry)
domain_count = len(domain_registry)
task_count = len(task_registry)
agent_count = len(agent_registry)

print(f'Model adapters:   {model_count}')
print(f'Domain packs:     {domain_count}')
print(f'Capability tests: {task_count}')
print(f'Agents:           {agent_count}')
print()
print('Domains:', domain_registry.all_ids())
print('Tasks:  ', task_registry.all_ids()[:8])
print('Agents: ', agent_registry.all_ids()[:8])

assert model_count > 0, 'Model registry is empty; the duecare-llm-models install likely failed.'
assert domain_count > 0, 'Domain registry is empty; run register_discovered() and confirm the domains wheel is installed.'
assert task_count > 0, 'Task registry is empty; the duecare-llm-tasks install likely failed.'
assert agent_count > 0, 'Agent registry is empty; the duecare-llm-agents install likely failed.'
"""


TROUBLESHOOTING = """## Troubleshooting

<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">
  <thead>
    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">
      <th style="padding: 6px 10px; text-align: left; width: 36%;">Symptom</th>
      <th style="padding: 6px 10px; text-align: left; width: 64%;">Resolution</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding: 6px 10px;">Pinned install fails and raises a <code>RuntimeError</code> from the fallback.</td><td style="padding: 6px 10px;">Attach the <code>taylorsamarel/duecare-llm-wheels</code> dataset from the Kaggle sidebar and rerun the install cell.</td></tr>
    <tr><td style="padding: 6px 10px;"><code>RuntimeError</code> about a version mismatch.</td><td style="padding: 6px 10px;">Restart the runtime (Run &rarr; Factory reset and clear output), then rerun the install cell so the new version fully replaces the cached one.</td></tr>
    <tr><td style="padding: 6px 10px;">An <code>assert</code> fires about an empty registry.</td><td style="padding: 6px 10px;">Confirm all 8 packages installed by running <code>!pip list | grep duecare</code>. If any are missing, rerun the install cell.</td></tr>
    <tr><td style="padding: 6px 10px;">Glossary link returns a Kaggle 404.</td><td style="padding: 6px 10px;">That notebook likely uses a legacy public slug. Rebuild this glossary from <code>scripts/build_notebook_005_glossary.py</code> and confirm the target notebook is represented in <code>scripts/_public_slugs.py</code>.</td></tr>
  </tbody>
</table>
"""


NEXT_NOTEBOOK = f"""## Next

- **Continue the section:** [010 Quickstart]({URL_010}) runs the smallest DueCare smoke test end-to-end.
- **Close the orientation section:** [099 Background and Package Setup Conclusion]({URL_099}).
- **Back to navigation:** [000 Index]({URL_000}).
"""


FINAL_PRINT = (
    f"print('Glossary handoff >>> 010 Quickstart {URL_010} | 099 Conclusion {URL_099}')\n"
)


def build() -> None:
    cells = [
        _md(_header_markdown()),
        _md(AT_A_GLANCE_INTRO),
        _code(AT_A_GLANCE_CODE),
        _md(SUNBURST_INTRO),
        _code(SUNBURST_CODE),
        _md(SECTION_MAP_INTRO + _section_order_table_html()),
        _md(READING_PATHS_INTRO + _reading_paths_table_html()),
        _md("## Glossary: " + GLOSSARY_GROUPS[0][0] + "\n\n" + _glossary_table_html(GLOSSARY_GROUPS[0][1])),
        _md("## Glossary: " + GLOSSARY_GROUPS[1][0] + "\n\n" + _glossary_table_html(GLOSSARY_GROUPS[1][1])),
        _md("## Glossary: " + GLOSSARY_GROUPS[2][0] + "\n\n" + _glossary_table_html(GLOSSARY_GROUPS[2][1])),
        _md("## Glossary: " + GLOSSARY_GROUPS[3][0] + "\n\n" + _glossary_table_html(GLOSSARY_GROUPS[3][1])),
        _md("## Glossary: " + GLOSSARY_GROUPS[4][0] + "\n\n" + _glossary_table_html(GLOSSARY_GROUPS[4][1])),
        _md("## Glossary: " + GLOSSARY_GROUPS[5][0] + "\n\n" + _glossary_table_html(GLOSSARY_GROUPS[5][1])),
        _md("## Glossary: " + GLOSSARY_GROUPS[6][0] + "\n\n" + _glossary_table_html(GLOSSARY_GROUPS[6][1])),
        _md("## Glossary: " + GLOSSARY_GROUPS[7][0] + "\n\n" + _glossary_table_html(GLOSSARY_GROUPS[7][1])),
        _md(REGISTRY_INTRO),
        _code(REGISTRY_CODE),
        _md(TROUBLESHOOTING),
        _md(NEXT_NOTEBOOK),
    ]

    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
            "kaggle": {"accelerator": "none", "isInternetEnabled": True},
        },
        "cells": cells,
    }
    notebook = harden_notebook(notebook, filename=FILENAME, requires_gpu=False)

    # Harden the install cell's soft version warning into a hard failure.
    # Keep the canonical hardener install cell intact; only replace the
    # trailing warning block so 005 still has exactly one install cell.
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        install_version_block = (
            "import duecare.core\n"
            "print(f'DueCare version: {duecare.core.__version__} ({install_source})')\n"
            f"if duecare.core.__version__ != '{DUECARE_VERSION}':\n"
            f"    print('Expected DueCare version: {DUECARE_VERSION}')\n"
        )
        hardened_version_block = (
            "import duecare.core\n"
            "print(f'DueCare version: {duecare.core.__version__} ({install_source})')\n"
            f"if duecare.core.__version__ != '{DUECARE_VERSION}':\n"
            "    raise RuntimeError(\n"
            f"        f'DueCare version {{duecare.core.__version__}} installed but this notebook was written against {DUECARE_VERSION}. Restart the runtime, rerun the install cell, and confirm the wheel dataset is current.'\n"
            "    )\n"
        )
        if (
            "Install the pinned DueCare packages for this notebook." in src
            and install_version_block in src
        ):
            cell["source"] = src.replace(
                install_version_block, hardened_version_block
            ).splitlines(keepends=True)

    patch_final_print_cell(notebook, final_print_src=FINAL_PRINT, marker="Glossary handoff >>>")

    NB_DIR.mkdir(parents=True, exist_ok=True)
    KAGGLE_KERNELS.mkdir(parents=True, exist_ok=True)

    nb_path = NB_DIR / FILENAME
    nb_path.write_text(json.dumps(notebook, indent=1), encoding="utf-8")

    kernel_dir = KAGGLE_KERNELS / KERNEL_DIR_NAME
    kernel_dir.mkdir(parents=True, exist_ok=True)
    (kernel_dir / FILENAME).write_text(json.dumps(notebook, indent=1), encoding="utf-8")

    metadata = {
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
    (kernel_dir / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Wrote {nb_path}")
    print(f"Wrote {kernel_dir / FILENAME}")
    print(f"Wrote {kernel_dir / 'kernel-metadata.json'}")


if __name__ == "__main__":
    build()
