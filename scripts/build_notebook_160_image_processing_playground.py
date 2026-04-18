#!/usr/bin/env python3
"""Build the 160 Image Processing Playground notebook."""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import canonical_header_table, troubleshooting_table_html
from notebook_hardening_utils import INSTALL_PACKAGES, harden_notebook


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"

FILENAME = "160_image_processing_playground.ipynb"
KERNEL_DIR_NAME = "duecare_160_image_processing_playground"
KERNEL_ID = "taylorsamarel/160-duecare-image-processing-playground"
KERNEL_TITLE = "160: DueCare Image Processing Playground"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["gemma", "multimodal", "vision", "safety", "trafficking", "gpu"]

INSTALL_PACKAGES[FILENAME] = [
    "transformers==4.46.3",
    "accelerate==1.1.1",
    "bitsandbytes==0.44.1",
    "ipywidgets==8.1.5",
    "pillow==10.4.0",
]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_155 = "https://www.kaggle.com/code/taylorsamarel/155-duecare-tool-calling-playground"
URL_170 = "https://www.kaggle.com/code/taylorsamarel/duecare-170-live-context-injection-playground"
URL_180 = "https://www.kaggle.com/code/taylorsamarel/duecare-180-multimodal-document-inspector"
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
        "Either an uploaded image plus a free-form question, or one of three built-in "
        "sample cases that keep the notebook renderable even without a GPU. The live "
        "path uses a Gemma-family multimodal stand-in; the fallback path uses scripted "
        "sample analysis so the page still tells a coherent story in CPU-only preview."
    ),
    outputs_html=(
        "An image preview or sample-case description, a response-source banner, and a "
        "multimodal answer that focuses on trafficking or labor-exploitation signals in "
        "the uploaded material."
    ),
    prerequisites_html=(
        f"Kaggle kernel with GPU T4 x2 attached and the <code>{WHEELS_DATASET}</code> wheel "
        "dataset mounted. CPU-only preview still works with the built-in sample cases and fallback analysis."
    ),
    runtime_html=(
        "2 to 4 minutes for the first multimodal model load on T4. Built-in sample cases "
        "and CPU fallback responses render in under 1 second."
    ),
    pipeline_html=(
        f"Free Form Exploration, multimodal step. Previous: <a href=\"{URL_155}\">155 Tool "
        f"Calling Playground</a>. Next: <a href=\"{URL_170}\">170 Live Context Injection Playground</a>. "
        f"Document-focused follow-up: <a href=\"{URL_180}\">180 Multimodal Document Inspector</a>."
    ),
)


HEADER = f"""# 160: DueCare Image Processing Playground

**Ask Gemma a question about an image, or walk through one of the built-in sample cases when no GPU is attached.** This notebook is the fast multimodal bridge inside the Free Form Exploration section: less structured than notebook 180, but enough to make the visual-capability claim visible on screen.

Notebook 160 is intentionally lighter than the document inspector that follows. It is a playground, not an extraction pipeline. The goal is to show that image-aware reasoning exists at all before the notebook suite tightens into structured extraction, document indicators, and the full function-calling plus multimodal integration story.

{HEADER_TABLE}

### Why this notebook matters

The project says Gemma's multimodal understanding is load-bearing. That claim has to show up before the polished demo notebook. This page does that in the simplest possible form: image in, question in, answer out, with the notebook telling you whether the answer came from live multimodal inference or from the CPU-safe fallback path.

### Reading order

- **Previous step:** [155 Tool Calling Playground]({URL_155}) for structured JSON tool routing.
- **Immediate next step:** [170 Live Context Injection Playground]({URL_170}) returns to text prompts and varies the context conditions.
- **Document-focused follow-up:** [180 Multimodal Document Inspector]({URL_180}) turns multimodal analysis into structured field extraction and indicator flags.
- **Full integrated demo:** [400 Function Calling and Multimodal]({URL_400}).
- **Section close:** [199 Free Form Exploration Conclusion]({URL_199}).
- **Back to navigation:** [000 Index]({URL_000}).

### What this notebook does

1. Load a Gemma-family multimodal stand-in on T4, or switch to a scripted fallback path when no GPU is available.
2. Offer three built-in sample cases so the notebook remains demoable even without an uploaded image.
3. Let the reader upload an image and ask a free-form question about it.
4. Render the selected sample or uploaded image, then print the answer with an explicit source label.
5. Hand off into the text-context and structured-document notebooks that follow.
"""


STEP_1_INTRO = """---

## 1. Load the multimodal model or switch to fallback mode

The live path tries Gemma 4 E4B (which has native multimodal understanding) first, then falls back to PaliGemma 2 if the Gemma 4 vision class is unavailable in the local Transformers version. If both loads fail or no GPU is present, the notebook stays usable by routing to built-in scripted sample analysis.
"""


MODEL_LOAD = """import os

MODEL_AVAILABLE = False
MODEL_ID = None
MODEL_SOURCE = None
processor = None
model = None

# Preference order: Kaggle Gemma 4 mount, HF Gemma 4 slug, PaliGemma 2 fallback.
KAGGLE_GEMMA_4 = '/kaggle/input/models/google/gemma-4/transformers/gemma-4-e4b-it/1'
GEMMA_4_HF = 'google/gemma-4-e4b-it'
PALIGEMMA_FALLBACK = 'google/paligemma2-3b-mix-448'

try:
    import torch
    from transformers import AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError('no CUDA device available; using scripted multimodal fallback')

    print(f'GPU detected: {torch.cuda.get_device_name(0)}')
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type='nf4',
    )

    # First try Gemma 4 via the generic image-text-to-text auto class.
    # This is the rubric-aligned path: Gemma 4 multimodal is one of the
    # explicitly-named unique features in the hackathon brief.
    last_err = None
    for candidate_id, candidate_label in (
        (KAGGLE_GEMMA_4 if os.path.isdir(KAGGLE_GEMMA_4) else GEMMA_4_HF, 'gemma-4-e4b-it'),
    ):
        try:
            from transformers import AutoModelForImageTextToText
            processor = AutoProcessor.from_pretrained(candidate_id)
            model = AutoModelForImageTextToText.from_pretrained(
                candidate_id,
                quantization_config=quant_config,
                device_map='auto',
                torch_dtype=torch.bfloat16,
            )
            model.eval()
            MODEL_ID = candidate_id
            MODEL_SOURCE = candidate_label
            MODEL_AVAILABLE = True
            print(f'Loaded multimodal model: {candidate_label}')
            break
        except Exception as exc:
            last_err = exc
            print(f'  Gemma 4 vision load failed ({exc.__class__.__name__}); trying PaliGemma 2 fallback...')

    # Fallback to PaliGemma 2 only if Gemma 4 vision class is unavailable.
    if not MODEL_AVAILABLE:
        from transformers import PaliGemmaForConditionalGeneration

        processor = AutoProcessor.from_pretrained(PALIGEMMA_FALLBACK)
        model = PaliGemmaForConditionalGeneration.from_pretrained(
            PALIGEMMA_FALLBACK,
            quantization_config=quant_config,
            device_map='auto',
            torch_dtype=torch.bfloat16,
        )
        model.eval()
        MODEL_ID = PALIGEMMA_FALLBACK
        MODEL_SOURCE = 'paligemma2-3b-mix-448 (fallback; Gemma 4 vision class unavailable)'
        MODEL_AVAILABLE = True
        print(f'Loaded fallback multimodal model: {MODEL_SOURCE}')
except Exception as exc:
    print(f'Model load skipped ({exc.__class__.__name__}: {exc}).')
    print('Using scripted fallback analysis so the playground still renders.')
"""


STEP_2_INTRO = """---

## 2. Define built-in sample cases and fallback analysis

The built-in cases are synthetic on purpose. They mimic the shape of image evidence NGO staff actually inspect: a fee-demand screenshot, a passport-retention note, and a dormitory-rules photo. The fallback path uses those cases to keep the multimodal story visible even without a live model.
"""


SAMPLES_AND_FALLBACK = """SAMPLE_CASES = {
    'Recruitment fee chat': {
        'description': 'Synthetic WhatsApp screenshot where a recruiter demands a large placement fee before airport departure and warns the worker not to discuss it with officials.',
        'fallback_answer': 'The screenshot appears to show a recruitment-fee demand plus secrecy pressure. Those are trafficking-adjacent warning signs. I would avoid paying, preserve the messages, and contact an embassy, hotline, or NGO before traveling.',
    },
    'Passport retention notice': {
        'description': 'Synthetic notice posted in a dormitory saying passports will be held by management until contracts are complete and workers need written permission to leave the site.',
        'fallback_answer': 'The posted notice suggests document retention and movement control. Those are serious red flags. A worker should document the notice and seek outside help quickly.',
    },
    'Dormitory rules photo': {
        'description': 'Synthetic phone photo of dormitory rules limiting exit times, banning contact with labor inspectors, and requiring wage deductions for rule violations.',
        'fallback_answer': 'The rules imply coercive control, restricted movement, and retaliatory deductions. I would treat that as a high-risk labor-exploitation signal and escalate it for human review.',
    },
}


def _fallback_image_answer(question: str, *, sample_key: str | None = None, filename: str | None = None) -> str:
    if sample_key and sample_key in SAMPLE_CASES:
        base = SAMPLE_CASES[sample_key]['fallback_answer']
    else:
        lower_name = (filename or 'uploaded image').lower()
        if 'passport' in lower_name:
            base = 'The uploaded image filename suggests passport-related evidence. Document retention is a high-risk control signal and should be escalated.'
        elif 'contract' in lower_name or 'fee' in lower_name:
            base = 'The uploaded image filename suggests a contract or fee document. I would inspect it for placement fees, wage deductions, passport clauses, and dispute restrictions.'
        else:
            base = 'Live multimodal inference is unavailable, so this fallback can only provide a general trafficking-risk read. Focus on payment demands, document control, threats, and movement restrictions.'

    lower_question = question.lower()
    if 'extract' in lower_question or 'list' in lower_question:
        return base + ' The next step would be to extract entities, amounts, clauses, and control indicators into a structured checklist.'
    if 'red flag' in lower_question or 'risk' in lower_question:
        return base + ' The strongest red flags are payment coercion, passport control, restriction on movement, and pressure not to contact authorities.'
    return base


print(f'Sample cases available: {list(SAMPLE_CASES.keys())}')
print(f'Model available: {MODEL_AVAILABLE}')
"""


STEP_3_INTRO = """---

## 3. Define the live multimodal answer helper

When an uploaded image is available and the model is loaded, the live path asks a single question about that image. When the user chooses a built-in sample instead, the notebook intentionally keeps the answer on the scripted path because there is no real image file behind those synthetic examples.
"""


ANSWER_FN = """def answer_about_image(image, question: str) -> str:
    if not MODEL_AVAILABLE:
        raise RuntimeError('live multimodal model unavailable')

    prompt = (
        'You are DueCare, a safety-focused migration and trafficking analysis assistant. '
        'Answer the user question about the image and focus on payment demands, passport control, movement restrictions, threats, or labor-rights issues when present. '\
        f'User question: {question}'
    )
    inputs = processor(images=image, text=prompt, return_tensors='pt').to(model.device)

    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=220, do_sample=False)

    response_ids = generated[:, inputs['input_ids'].shape[-1]:]
    decoded = processor.batch_decode(response_ids, skip_special_tokens=True)
    return decoded[0].strip()


if MODEL_AVAILABLE:
    print('Multimodal helper ready. Upload an image to use the live path.')
else:
    print('Live multimodal model unavailable; use a built-in sample or upload an image for fallback analysis.')
"""


STEP_4_INTRO = """---

## 4. Interactive widget

Use a built-in sample case for a quick walkthrough, or switch the selector to <code>Upload your own image</code> and attach a screenshot or photo. The notebook always tells you whether the answer came from live multimodal inference, a built-in sample case, or the generic CPU-safe fallback path.
"""


UI = """import io

import ipywidgets as widgets
from IPython.display import Markdown, clear_output, display
from PIL import Image

sample_dropdown = widgets.Dropdown(
    options=[('Upload your own image', '__upload__')] + [(label, label) for label in SAMPLE_CASES],
    value='Recruitment fee chat',
    description='Mode:',
    layout=widgets.Layout(width='100%'),
)
uploader = widgets.FileUpload(accept='image/*', multiple=False, description='Upload image')
question_box = widgets.Textarea(
    value='What red flags do you see in this image?',
    description='Question:',
    layout=widgets.Layout(width='100%', height='120px'),
)
analyze_button = widgets.Button(description='Analyze image', button_style='primary')
output_area = widgets.Output()


def _read_upload() -> tuple[str, Image.Image] | tuple[None, None]:
    if not uploader.value:
        return None, None

    if isinstance(uploader.value, tuple):
        file_info = uploader.value[0]
    else:
        file_info = next(iter(uploader.value.values()))

    name = file_info['name']
    image = Image.open(io.BytesIO(file_info['content'])).convert('RGB')
    return name, image


def _on_analyze(_):
    with output_area:
        clear_output()
        question = question_box.value.strip()
        if not question:
            print('Type a question first.')
            return

        selected_sample = sample_dropdown.value
        if selected_sample != '__upload__':
            case = SAMPLE_CASES[selected_sample]
            display(Markdown(
                f'**Response source:** Built-in scripted sample case\\n\\n'
                f'**Sample case:** {selected_sample}\\n\\n'
                f'**Description:** {case["description"]}\\n\\n'
                f'**Question:** {question}\\n\\n'
                f'**Answer:** { _fallback_image_answer(question, sample_key=selected_sample) }'
            ))
            return

        filename, image = _read_upload()
        if image is None:
            print('Switch to a built-in sample case or upload an image first.')
            return

        display(image)
        display(Markdown(f'**Uploaded image:** {filename} ({image.width} x {image.height})'))

        if MODEL_AVAILABLE:
            try:
                answer = answer_about_image(image, question)
                source_label = 'Live multimodal model on Kaggle T4'
            except Exception as exc:
                answer = _fallback_image_answer(question, filename=filename)
                source_label = f'Fallback analysis after live error ({exc.__class__.__name__})'
        else:
            answer = _fallback_image_answer(question, filename=filename)
            source_label = 'CPU-safe fallback for uploaded image'

        display(Markdown(
            f'**Response source:** {source_label}\\n\\n'
            f'**Question:** {question}\\n\\n'
            f'**Answer:** {answer}'
        ))


analyze_button.on_click(_on_analyze)

display(widgets.VBox([
    sample_dropdown,
    uploader,
    question_box,
    analyze_button,
    output_area,
]))
"""


TROUBLESHOOTING = troubleshooting_table_html([
    (
        'The notebook says it is using scripted fallback analysis.',
        'Attach a <b>GPU T4 x2</b> in Kaggle settings and rerun from the top to exercise the live multimodal path.'
    ),
    (
        'You uploaded an image but only got the generic CPU-safe fallback answer.',
        'That means the live multimodal model was unavailable. The upload still renders, but attach a GPU and rerun to get real image reasoning.'
    ),
    (
        'You want a more structured document-analysis output.',
        f'Continue to <a href="{URL_180}">180 Multimodal Document Inspector</a>, which extracts fields and flags specific indicators instead of just answering a free-form question.'
    ),
    (
        'You want multimodal plus function calling together.',
        f'Jump later to <a href="{URL_400}">400 Function Calling and Multimodal</a> for the integrated demo once you finish this section.'
    ),
])


SUMMARY = f"""---

## What just happened

- Exposed a simple multimodal question-answer surface that accepts either a built-in synthetic case or an uploaded image.
- Kept the notebook renderable in CPU-only preview mode by making the fallback path explicit instead of letting the notebook fail.
- Made the multimodal claim visible before the suite moves into structured extraction and deeper context comparisons.

### Why this notebook exists alongside 180

1. **This is the fast visual proof.** It is intentionally looser and more conversational than notebook 180.
2. **The built-in sample cases keep the notebook demoable.** Even without a GPU or an uploaded image, the page still shows the intended multimodal story.
3. **The structured evidence comes next.** Notebook [180 Multimodal Document Inspector]({URL_180}) turns the same capability into extractable fields and indicator flags.

---

## Troubleshooting

{TROUBLESHOOTING}

---

## Next

- **Immediate next notebook:** [170 Live Context Injection Playground]({URL_170}) returns to text and shows how plain, RAG, and guided context change the answer.
- **Document-focused follow-up:** [180 Multimodal Document Inspector]({URL_180}) tightens multimodal analysis into structured extraction.
- **Full integration:** [400 Function Calling and Multimodal]({URL_400}) combines tool use and multimodal reasoning in one notebook.
- **Section close:** [199 Free Form Exploration Conclusion]({URL_199}).
- **Back to navigation:** [000 Index]({URL_000}).
"""


FINAL_PRINT = f"""print(
    'Multimodal handoff >>> Continue to 170 Live Context Injection Playground: '
    '{URL_170}'
    '. Document-focused follow-up: 180 Multimodal Document Inspector: '
    '{URL_180}'
    '. Section close: 199 Free Form Exploration Conclusion: '
    '{URL_199}'
    '.'
)
"""



AT_A_GLANCE_INTRO = """---

## At a glance

Upload an image, ask a question, see the multimodal response live.
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
    _stat_card('Gemma 4', 'multimodal', 'image + text', 'primary'),
    _stat_card('upload', 'image', 'any format', 'info'),
    _stat_card('question', 'text prompt', 'user-typed', 'warning'),
    _stat_card('live', 'inference', 'single GPU call', 'success')
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step('Load multimodal', '4-bit', 'primary'),
    _step('Upload image', 'widget', 'info'),
    _step('Ask', 'text prompt', 'warning'),
    _step('Render', 'response', 'success')
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">Image playground</div>'
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
        code(SAMPLES_AND_FALLBACK),
        md(STEP_3_INTRO),
        code(ANSWER_FN),
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