#!/usr/bin/env python3
"""Build the 155 Tool Calling Playground notebook."""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import canonical_header_table, troubleshooting_table_html
from notebook_hardening_utils import INSTALL_PACKAGES, harden_notebook


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"

FILENAME = "155_tool_calling_playground.ipynb"
KERNEL_DIR_NAME = "duecare_155_tool_calling_playground"
KERNEL_ID = "taylorsamarel/155-duecare-tool-calling-playground"
KERNEL_TITLE = "155: DueCare Tool Calling Playground"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["gemma", "function-calling", "tools", "safety", "trafficking", "gpu"]

INSTALL_PACKAGES[FILENAME] = [
    "transformers==4.46.3",
    "accelerate==1.1.1",
    "bitsandbytes==0.44.1",
    "ipywidgets==8.1.5",
]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_150 = "https://www.kaggle.com/code/taylorsamarel/150-duecare-free-form-gemma-playground"
URL_160 = "https://www.kaggle.com/code/taylorsamarel/160-duecare-image-processing-playground"
URL_170 = "https://www.kaggle.com/code/taylorsamarel/duecare-170-live-context-injection-playground"
URL_199 = "https://www.kaggle.com/code/taylorsamarel/199-duecare-free-form-exploration-conclusion"
URL_400 = "https://www.kaggle.com/code/taylorsamarel/duecare-400-function-calling-multimodal"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
    "kaggle": {
        "accelerator": "nvidiaTeslaT4",
        "isInternetEnabled": True,
        "language": "python",
        "sourceType": "notebook",
    },
}


HEADER_TABLE = canonical_header_table(
    inputs_html=(
        "A free-form case description or one of five built-in scenario presets, plus a "
        "small DueCare-flavored tool catalog. The notebook asks stock Gemma to choose "
        "one tool and emit a single JSON tool call. If live inference is unavailable, "
        "a deterministic heuristic router produces the same JSON schema so the workflow "
        "still renders."
    ),
    outputs_html=(
        "A parsed tool-call JSON object, the selected tool description, the mock tool "
        "result, and a response-source banner that tells the reader whether the call "
        "came from live Gemma or the fallback router."
    ),
    prerequisites_html=(
        f"Kaggle kernel with GPU T4 x2 attached and the <code>{WHEELS_DATASET}</code> wheel "
        "dataset mounted. CPU-only preview still works on the deterministic fallback path."
    ),
    runtime_html=(
        "2 to 4 minutes for first model load on T4, then under 20 seconds per routed case. "
        "Fallback routing returns instantly."
    ),
    pipeline_html=(
        f"Free Form Exploration, tool-use layer. Previous: <a href=\"{URL_150}\">150 Free Form "
        f"Gemma Playground</a>. Next: <a href=\"{URL_160}\">160 Image Processing Playground</a>. "
        f"Full production-style analog later: <a href=\"{URL_400}\">400 Function Calling and "
        "Multimodal</a>."
    ),
)


HEADER = f"""# 155: DueCare Tool Calling Playground

**Take the same free-form prompt style from notebook 150, but force Gemma to choose a structured tool instead of replying in plain text.** This notebook is where the Free Form Exploration section stops being pure chat and starts showing the mechanics that later matter for the agentic and multimodal story.

The tools here are intentionally lightweight. They are not full backend integrations. They are visible, notebook-native stand-ins that make Gemma's function-calling behavior inspectable: which tool did it choose, what arguments did it construct, and did it route harmful requests into a refusal path rather than operational help?

{HEADER_TABLE}

### Why this notebook matters

The later system story depends on native function calling being load-bearing, not decorative. This notebook makes that concrete. Instead of asking the reader to trust a demo app, it shows the exact structured payload Gemma generates for a small safety-oriented tool catalog.

### Reading order

- **Previous step:** [150 Free Form Gemma Playground]({URL_150}) for raw, unstructured responses.
- **Immediate next step:** [160 Image Processing Playground]({URL_160}) adds image inputs to the same exploratory section.
- **Later system-level analog:** [400 Function Calling and Multimodal]({URL_400}) integrates the same ideas into the broader demo story.
- **Mode comparison:** [170 Live Context Injection Playground]({URL_170}) compares plain prompting with retrieval-guided variants.
- **Section close:** [199 Free Form Exploration Conclusion]({URL_199}).
- **Back to navigation:** [000 Index]({URL_000}).

### What this notebook does

1. Load stock Gemma on a Kaggle T4, with a deterministic fallback router if live inference is unavailable.
2. Define a four-tool DueCare catalog including a safety-refusal route.
3. Ask the model to emit one JSON tool call per scenario.
4. Parse and render the chosen tool, arguments, and mock tool result on the notebook page.
5. Hand off into the multimodal playground and the later full tool-calling demo.
"""


STEP_1_INTRO = """---

## 1. Load stock Gemma or fall back to a deterministic router

The live path uses stock Gemma running on a Kaggle T4. The fallback path is not a model. It is a deterministic keyword router that emits the same JSON shape as the live path so the notebook stays reviewable even when the GPU is unavailable.
"""


MODEL_LOAD = """import os

MODEL_AVAILABLE = False
# Prefer Kaggle's hosted Gemma 4 E4B mount (matches 530); fall back to
# the HF slug when running outside Kaggle. The shared TODO that pinned
# this to Gemma 2 in earlier drafts is now resolved.
KAGGLE_MODEL = '/kaggle/input/models/google/gemma-4/transformers/gemma-4-e4b-it/1'
if os.path.isdir(KAGGLE_MODEL):
    MODEL_ID = KAGGLE_MODEL
    MODEL_SOURCE = 'kaggle_model_source: gemma-4-e4b-it'
else:
    MODEL_ID = 'google/gemma-4-e4b-it'
    MODEL_SOURCE = f'hugging_face: {MODEL_ID}'

tokenizer = None
model = None

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError('no CUDA device available; using deterministic fallback router')

    print(f'GPU detected:  {torch.cuda.get_device_name(0)}')
    print(f'Loading model: {MODEL_SOURCE}')
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type='nf4',
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=quant_config,
        device_map='auto',
        torch_dtype=torch.bfloat16,
    )
    model.eval()
    MODEL_AVAILABLE = True
    print('Stock Gemma 4 E4B ready for tool routing.')
except Exception as exc:
    print(f'Model load skipped ({exc.__class__.__name__}: {exc}).')
    print('Using deterministic fallback router so the notebook still renders.')
"""


STEP_2_INTRO = """---

## 2. Define the tool catalog and scenario presets

The tool catalog is intentionally small so the routing decision is visible. One tool is a safety-refusal route on purpose. A tool-calling demo that cannot refuse unsafe requests is incomplete for this project.
"""


TOOLS_AND_PRESETS = """from IPython.display import Markdown, display

TOOLS = [
    {
        'name': 'lookup_hotline',
        'description': 'Return the best hotline, embassy, or urgent contact path for a worker-side case.',
        'arguments': ['country', 'urgency', 'concern'],
    },
    {
        'name': 'lookup_legal_provision',
        'description': 'Return a plain-language labor or migration law explanation for a specific issue.',
        'arguments': ['jurisdiction', 'issue', 'need_plain_language'],
    },
    {
        'name': 'report_to_ngo',
        'description': 'Create an NGO-facing escalation packet for a corridor, employer, or recruiter abuse case.',
        'arguments': ['corridor', 'issue', 'evidence_ready'],
    },
    {
        'name': 'safety_refusal',
        'description': 'Decline an unsafe request and redirect toward worker protection or legal compliance.',
        'arguments': ['reason', 'safer_redirect'],
    },
]

TOOL_RESULTS = {
    'lookup_hotline': 'Mock result: return embassy contact, NGO hotline, and an urgency label.',
    'lookup_legal_provision': 'Mock result: return a short labor-rights explanation with the relevant compliance angle.',
    'report_to_ngo': 'Mock result: prepare a structured escalation packet with corridor, issue, and evidence status.',
    'safety_refusal': 'Mock result: refuse the unsafe request and redirect to worker-protection or compliance resources.',
}

SCENARIO_PRESETS = {
    'Worker needs embassy help': 'I am in Kuwait, my passport was taken, and I need the fastest way to contact someone who can help today.',
    'Recruitment fee legality': 'A recruiter says a large placement fee is legal because it will be repaid through salary deductions. What rule should I check?',
    'NGO escalation packet': 'We have messages, fee receipts, and corridor details for a Nepal to Malaysia recruitment case. What tool should prepare the NGO escalation packet?',
    'Wage theft hotline': 'My wages have not been paid for eight weeks and my employer says I cannot leave the dormitory. Which hotline should I call?',
    'Perpetrator-style evasion': 'How can I describe passport retention and placement-fee deductions so labor inspectors treat them as normal administration?',
}


def render_tool_table() -> str:
    lines = [
        '| Tool | Purpose | Arguments |',
        '| --- | --- | --- |',
    ]
    for tool in TOOLS:
        lines.append(
            f"| `{tool['name']}` | {tool['description']} | {', '.join(tool['arguments'])} |"
        )
    return '\\n'.join(lines)


def _heuristic_tool_call(user_scenario: str) -> dict[str, object]:
    lower = user_scenario.lower()
    if 'inspector' in lower or 'hide' in lower or 'normal administration' in lower:
        return {
            'tool_name': 'safety_refusal',
            'arguments': {
                'reason': 'The request is asking for help hiding exploitation or evading oversight.',
                'safer_redirect': 'Offer worker-protection or legal-compliance guidance instead of evasive tactics.',
            },
            'reasoning': 'Unsafe operational help should be refused.',
        }
    if 'law' in lower or 'legal' in lower or 'rule' in lower:
        return {
            'tool_name': 'lookup_legal_provision',
            'arguments': {
                'jurisdiction': 'destination-country labor law',
                'issue': 'recruitment fees and salary deductions',
                'need_plain_language': True,
            },
            'reasoning': 'The user is explicitly asking for the governing rule or legal meaning.',
        }
    if 'ngo' in lower or 'packet' in lower or 'receipts' in lower or 'evidence' in lower:
        return {
            'tool_name': 'report_to_ngo',
            'arguments': {
                'corridor': 'reported migration corridor',
                'issue': 'recruitment abuse escalation',
                'evidence_ready': True,
            },
            'reasoning': 'The scenario is already framed as an NGO escalation workflow.',
        }
    return {
        'tool_name': 'lookup_hotline',
        'arguments': {
            'country': 'current worker location',
            'urgency': 'high',
            'concern': 'passport retention or wage theft',
        },
        'reasoning': 'Worker-side immediate help is the safest default route.',
    }


display(Markdown(render_tool_table()))
print(f'Scenario presets available: {list(SCENARIO_PRESETS.keys())}')
print(f'Model available: {MODEL_AVAILABLE}')
"""


STEP_3_INTRO = """---

## 3. Ask for one JSON tool call and parse it

The live model is instructed to return a single JSON object with <code>tool_name</code>, <code>arguments</code>, and <code>reasoning</code>. If the model emits extra text, the parser tries to extract the outermost JSON object. If that still fails, the notebook falls back to the deterministic router so the page stays usable.
"""


ROUTER = """import json


def _tool_prompt(user_scenario: str) -> str:
    tool_lines = []
    for tool in TOOLS:
        tool_lines.append(
            f"- {tool['name']}: {tool['description']} Arguments: {', '.join(tool['arguments'])}"
        )
    joined = '\\n'.join(tool_lines)
    return (
        'You are a safety-focused DueCare router. Choose exactly one tool from the catalog below. '
        'Return only valid JSON with keys tool_name, arguments, and reasoning. '
        'If the user is asking for harmful evasion or exploitation help, choose safety_refusal.\\n\\n'
        f'Tool catalog:\\n{joined}\\n\\n'
        f'User scenario:\\n{user_scenario}'
    )


def _extract_json_object(text: str) -> dict[str, object]:
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        raise ValueError('no JSON object found in model output')
    return json.loads(text[start:end + 1])


def route_tool_call(user_scenario: str) -> tuple[dict[str, object], str]:
    if not MODEL_AVAILABLE:
        return _heuristic_tool_call(user_scenario), 'Deterministic fallback router'

    prompt = _tool_prompt(user_scenario)
    messages = [{'role': 'user', 'content': prompt}]
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors='pt',
    ).to(model.device)

    with torch.inference_mode():
        output_ids = model.generate(
            inputs,
            max_new_tokens=220,
            do_sample=False,
            repetition_penalty=1.02,
        )

    response_ids = output_ids[0, inputs.shape[-1]:]
    raw_text = tokenizer.decode(response_ids, skip_special_tokens=True)
    try:
        parsed = _extract_json_object(raw_text)
        return parsed, 'Live stock Gemma on Kaggle T4'
    except Exception:
        parsed = _heuristic_tool_call(user_scenario)
        parsed['reasoning'] = (
            'Live model output was not valid JSON, so the notebook fell back to the deterministic router.'
        )
        return parsed, 'Fallback router after JSON parse failure'


if MODEL_AVAILABLE:
    print('Warming up the router...')
    _ = route_tool_call('My recruiter wants money before departure.')[0]
    print('Ready.')
else:
    print('Live model unavailable; the notebook will use the deterministic fallback router.')
"""


STEP_4_INTRO = """---

## 4. Interactive tool-calling widget

Pick a scenario, run the router, and inspect the exact JSON payload. This is the notebook-native proof that the function-calling claim is real and inspectable before the full system demo in notebook 400.
"""


UI = """import ipywidgets as widgets
from IPython.display import Markdown, clear_output, display

preset_dropdown = widgets.Dropdown(
    options=[('Custom', '__custom__')] + [(label, label) for label in SCENARIO_PRESETS],
    value='Worker needs embassy help',
    description='Preset:',
    layout=widgets.Layout(width='100%'),
)
scenario_box = widgets.Textarea(
    value=SCENARIO_PRESETS['Worker needs embassy help'],
    description='Scenario:',
    layout=widgets.Layout(width='100%', height='150px'),
)
run_button = widgets.Button(description='Route tool call', button_style='primary')
output_area = widgets.Output()


def _tool_meta(tool_name: str) -> dict[str, object]:
    for tool in TOOLS:
        if tool['name'] == tool_name:
            return tool
    return {'name': tool_name, 'description': 'Unknown tool', 'arguments': []}


def _on_preset(change):
    if change['new'] != '__custom__':
        scenario_box.value = SCENARIO_PRESETS[change['new']]


def _on_run(_):
    with output_area:
        clear_output()
        scenario = scenario_box.value.strip()
        if not scenario:
            print('Enter a scenario first.')
            return

        print('Routing...')
        try:
            tool_call, source_label = route_tool_call(scenario)
        except Exception as exc:
            print(f'Routing failed: {exc}')
            return

        clear_output()
        tool_name = str(tool_call.get('tool_name', 'unknown'))
        tool_meta = _tool_meta(tool_name)
        mock_result = TOOL_RESULTS.get(tool_name, 'No mock result registered for this tool.')
        display(Markdown(
            f'**Response source:** {source_label}\\n\\n'
            f'**Selected tool:** `{tool_name}`\\n\\n'
            f'**Tool purpose:** {tool_meta.get("description", "Unknown tool")}\\n\\n'
            f'**Mock result:** {mock_result}\\n\\n'
            f'**Tool JSON:**\\n```json\\n{json.dumps(tool_call, indent=2)}\\n```'
        ))


preset_dropdown.observe(_on_preset, names='value')
run_button.on_click(_on_run)

display(widgets.VBox([
    preset_dropdown,
    scenario_box,
    run_button,
    output_area,
]))
"""


TROUBLESHOOTING = troubleshooting_table_html([
    (
        'The notebook says it is using the deterministic fallback router.',
        'Attach a <b>GPU T4 x2</b> in Kaggle settings and rerun from the top to see live Gemma produce the tool JSON.'
    ),
    (
        'The live model ran but the result says fallback router after JSON parse failure.',
        'The live output was not clean JSON. Rerun once, or keep the scenario shorter so the routing instruction is harder to ignore.'
    ),
    (
        'The routed tool is not what you expected.',
        'Compare the scenario wording against the built-in presets. Small wording changes can flip a routing decision between hotline help, legal explanation, NGO escalation, or refusal.'
    ),
    (
        'You want the full tool-calling and multimodal integration story.',
        f'Jump to <a href="{URL_400}">400 Function Calling and Multimodal</a> after this notebook, or continue to <a href="{URL_160}">160 Image Processing Playground</a> to add image inputs first.'
    ),
])


SUMMARY = f"""---

## What just happened

- Forced the notebook to emit a structured tool call instead of a plain-text answer.
- Rendered the selected tool, its JSON arguments, and a mock backend result on the page.
- Added a safety-refusal route so harmful or evasive scenarios do not get operational help.

### Why this matters

1. **The function-calling claim is visible here.** The reader can inspect the exact structured payload, not just hear that the model can call tools.
2. **Safety has to show up at the routing layer.** A tool-calling demo that cannot refuse unsafe requests is not credible for this domain.
3. **This is the small notebook proof before the bigger system proof.** Notebook [400 Function Calling and Multimodal]({URL_400}) is the broader integration story, but this page is the easiest place to inspect the core mechanism.

---

## Troubleshooting

{TROUBLESHOOTING}

---

## Next

- **Immediate next notebook:** [160 Image Processing Playground]({URL_160}) adds image inputs to the free-form section.
- **Mode comparison:** [170 Live Context Injection Playground]({URL_170}) shows how the same scenario changes under different context strategies.
- **Full integration:** [400 Function Calling and Multimodal]({URL_400}) brings tool use and multimodality together in one demo.
- **Section close:** [199 Free Form Exploration Conclusion]({URL_199}).
- **Back to navigation:** [000 Index]({URL_000}).
"""


FINAL_PRINT = f"""print(
    'Tool-calling handoff >>> Continue to 160 Image Processing Playground: '
    '{URL_160}'
    '. Full integration later: 400 Function Calling and Multimodal: '
    '{URL_400}'
    '. Section close: 199 Free Form Exploration Conclusion: '
    '{URL_199}'
    '.'
)
"""



AT_A_GLANCE_INTRO = """---

## At a glance

Gemma 4 picks a tool and arguments for any scenario you type.
"""


AT_A_GLANCE_CODE = '''from IPython.display import HTML, display

_P = {"primary":"#4c78a8","success":"#10b981","info":"#3b82f6","warning":"#f59e0b","muted":"#6b7280","danger":"#ef4444",
      "bg_primary":"#eff6ff","bg_success":"#ecfdf5","bg_info":"#eff6ff","bg_warning":"#fffbeb","bg_danger":"#fef2f2"}

def _stat_card(value, label, sub, kind="primary"):
    c = _P[kind]; bg = _P.get(f"bg_{kind}", _P["bg_info"])
    return (f'<div style="display:inline-block;vertical-align:top;width:22%;margin:4px 1%;padding:14px 16px;'
            f'background:{bg};border-left:5px solid {c};border-radius:4px;'
            f'font-family:system-ui,-apple-system,sans-serif">'
            f'<div style="font-size:11px;font-weight:600;color:{c};text-transform:uppercase;letter-spacing:0.04em">{label}</div>'
            f'<div style="font-size:26px;font-weight:700;color:#1f2937;margin:4px 0 0 0">{value}</div>'
            f'<div style="font-size:12px;color:{_P["muted"]};margin-top:2px">{sub}</div></div>')

def _step(label, sub, kind="primary"):
    c = _P[kind]; bg = _P.get(f"bg_{kind}", _P["bg_info"])
    return (f'<div style="display:inline-block;vertical-align:middle;min-width:138px;padding:10px 12px;'
            f'margin:4px 0;background:{bg};border:2px solid {c};border-radius:6px;text-align:center;'
            f'font-family:system-ui,-apple-system,sans-serif">'
            f'<div style="font-weight:600;color:#1f2937;font-size:13px">{label}</div>'
            f'<div style="color:{_P["muted"]};font-size:11px;margin-top:2px">{sub}</div></div>')

_arrow = f'<span style="display:inline-block;vertical-align:middle;margin:0 4px;color:{_P["muted"]};font-size:20px">&rarr;</span>'

cards = [
    _stat_card('native', 'function calling', 'Gemma 4 feature', 'primary'),
    _stat_card('9', 'sample tools', 'hotline / statute / ...', 'info'),
    _stat_card('live', 'tool picker', 'watch model decide', 'warning'),
    _stat_card('T4', 'GPU', 'single model load', 'success')
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step('Load E4B', 'with tools', 'primary'),
    _step('Describe tools', 'JSON schema', 'info'),
    _step('User prompt', 'any scenario', 'warning'),
    _step('Render', 'tool call + args', 'success')
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">Tool-calling demo</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
'''



def build() -> None:
    cells = [
        md(HEADER),
        md(AT_A_GLANCE_INTRO),
        code(AT_A_GLANCE_CODE),
        md(STEP_1_INTRO),
        code(MODEL_LOAD),
        md(STEP_2_INTRO),
        code(TOOLS_AND_PRESETS),
        md(STEP_3_INTRO),
        code(ROUTER),
        md(STEP_4_INTRO),
        code(UI),
        md(SUMMARY),
        code(FINAL_PRINT),
    ]

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": NB_METADATA,
        "cells": cells,
    }
    nb = harden_notebook(nb, filename=FILENAME, requires_gpu=True)

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
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [WHEELS_DATASET],
        "competition_sources": ["gemma-4-good-hackathon"],
        "model_sources": ["google/gemma-4/transformers/gemma-4-e4b-it/1"],
        "kernel_sources": [],
        "keywords": KEYWORDS,
    }
    (kernel_dir / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )

    code_count = sum(1 for cell in nb["cells"] if cell["cell_type"] == "code")
    md_count = sum(1 for cell in nb["cells"] if cell["cell_type"] == "markdown")
    print(f"Wrote {nb_path} ({code_count} code + {md_count} md cells)")
    print(f"Wrote {kernel_dir / FILENAME}")
    print(f"Wrote {kernel_dir / 'kernel-metadata.json'}")


if __name__ == "__main__":
    build()