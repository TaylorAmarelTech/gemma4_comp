#!/usr/bin/env python3
"""Build 189: cracked 31B Gemma variant, 4-bit, L4x4 / A100 gated.

A hard gate on free VRAM. On any T4 kernel the notebook prints a clear
skip message, writes a diagnostic ``meta.json`` with ``hf_id: null`` and
a ``skip_reason`` so the 185 comparator can render "skipped on this
accelerator" honestly, and exits cleanly. When run on L4x4 or an A100
the 31B weights load in nf4 via bitsandbytes across the available GPUs
via ``device_map='auto'`` and the standard inference path runs.
"""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import canonical_header_table, patch_final_print_cell
from notebook_hardening_utils import harden_notebook
from _jailbreak_cells import PROMPT_SLICE, INFER, LOAD_SINGLE


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"

FILENAME = "189_jailbreak_cracked_31b.ipynb"
KERNEL_DIR_NAME = "duecare_189_jailbreak_cracked_31b"
KERNEL_ID = "taylorsamarel/duecare-189-jailbreak-cracked-31b"
KERNEL_TITLE = "189: DueCare Jailbreak - Cracked Gemma 4 31B"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
PROMPTS_DATASET = "taylorsamarel/duecare-trafficking-prompts"
KEYWORDS = ["gemma", "safety", "jailbreak", "cracked", "31b"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_185 = "https://www.kaggle.com/code/taylorsamarel/duecare-185-jailbroken-gemma-comparison"
URL_188 = "https://www.kaggle.com/code/taylorsamarel/duecare-188-jailbreak-uncensored-community"


def md(s): return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}
def code(s): return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": s.splitlines(keepends=True)}


NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
    "kaggle": {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": True, "language": "python", "sourceType": "notebook"},
}


HEADER_TABLE = canonical_header_table(
    inputs_html=(
        "<code>dealignai/Gemma-4-31B-JANG_4M-CRACK</code> loaded in "
        "nf4 4-bit via bitsandbytes across all available GPUs. The "
        "15-prompt graded trafficking slice drives the response "
        "comparison."
    ),
    outputs_html=(
        "Artifact bundle under "
        "<code>/kaggle/working/jailbreak_out/cracked_31b/</code> with "
        "<code>responses.jsonl</code>, <code>generations.jsonl</code>, "
        "<code>generations_raw.txt</code>, and <code>meta.json</code>. "
        "On a T4 the notebook writes only the diagnostic "
        "<code>meta.json</code> with <code>skip_reason</code> so the "
        "185 comparator can render the gap honestly."
    ),
    prerequisites_html=(
        "Kaggle kernel with at least 22 GB free VRAM after model load "
        "(L4 x 4 or a single A100). On a single T4 the notebook skips "
        f"gracefully. The <code>{WHEELS_DATASET}</code> wheel dataset "
        "must be attached."
    ),
    runtime_html="12 to 20 minutes on L4 x 4. <30 seconds when skipped on T4.",
    pipeline_html=(
        f"Free Form Exploration, per-model data-collection notebook. "
        f"Previous sibling: <a href=\"{URL_188}\">188 Uncensored "
        f"Community</a>. Comparator: <a href=\"{URL_185}\">185 "
        f"Jailbroken Gemma Comparison</a>."
    ),
)


HEADER = f"""# 189: DueCare Jailbreak - Cracked Gemma 4 31B

**Load `dealignai/Gemma-4-31B-JANG_4M-CRACK` in 4-bit on an L4 x 4 or A100 kernel and run it on the same benchmark slice. On a T4 kernel the notebook skips gracefully so the rest of the jailbreak family still renders.** This arm of the comparison answers whether the refusal gap measured on E4B persists when the base model is much larger. "Cracked" 31B weights are the upper bound of the uncensored-Gemma distribution DueCare has to protect against; if the gap shrinks at 31B it argues DueCare's judge can lean on size-independent signals.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a).

{HEADER_TABLE}

### VRAM budget

`Gemma-4-31B` in nf4 is approximately 18 to 22 GB of GPU memory for weights alone, plus a few GB for the KV cache at generation time. A single T4 (16 GB) cannot fit it. L4 x 4 (96 GB aggregate) and a single A100 (40 GB or 80 GB) both work. The cell below checks `torch.cuda.mem_get_info()` at load time and exits cleanly if the number is below 22 GB.

### Reading order

- **Parent comparator:** [185 Jailbroken Gemma Comparison]({URL_185}).
- **Previous sibling:** [188 Uncensored Community]({URL_188}).
- **Back to navigation:** [000 Index]({URL_000}).
"""


SETUP_MD = "---\n\n## 1. Environment and prompt slice\n"
GATE_MD = """---

## 2. VRAM gate and optional load

The gate decides whether the 31B cracked model fits on this accelerator. On a T4 the cell exits early and writes a diagnostic artifact; on L4 x 4 or A100 it proceeds to load.
"""

GATE = '''MIN_FREE_GB = 22.0
HF_ID = 'dealignai/Gemma-4-31B-JANG_4M-CRACK'
SKIP_REASON = None

free_gb_now = (torch.cuda.mem_get_info()[0] / 1e9) if GPU_OK else 0.0
if not GPU_OK:
    SKIP_REASON = 'no GPU'
elif free_gb_now < MIN_FREE_GB:
    SKIP_REASON = f'free VRAM {free_gb_now:.1f} GB < required {MIN_FREE_GB:.0f} GB'
else:
    print(f'VRAM ok ({free_gb_now:.1f} GB free). Loading {HF_ID} in nf4 ...')

tok = mdl = None
if SKIP_REASON is None:
    try:
        # Multi-GPU-friendly nf4 load.
        QUANT = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type='nf4',
        )
        tok = AutoTokenizer.from_pretrained(HF_ID)
        mdl = AutoModelForCausalLM.from_pretrained(
            HF_ID,
            quantization_config=QUANT,
            device_map='auto',
            torch_dtype=torch.bfloat16,
        )
        print(f'Loaded {HF_ID}')
    except Exception as exc:
        SKIP_REASON = f'load failed: {str(exc)[:300]}'
        print(SKIP_REASON)
else:
    print(f'SKIP: {SKIP_REASON}')
'''


RUN_MD = "---\n\n## 3. Run benchmark and red-team generation (only if the load succeeded)\n"
RUN = '''RESPONSES = []
GEN_ITEMS = []
GEN_RAW = ''
CONDITION = 'cracked'

if SKIP_REASON is None:
    print(f'Running {len(PROMPTS)} benchmark prompts on the 31B cracked model ...')
    RESPONSES = respond_to_prompts(tok, mdl, PROMPTS)
    print('Running red-team generation ...')
    GEN_ITEMS, GEN_RAW = generate_redteam(tok, mdl, n=10)
    print(f'Generated {len(GEN_ITEMS)} red-team prompts.')
else:
    print('Skipped inference (gate reason above).')
'''


WRITE_MD = "---\n\n## 4. Write artifacts\n"
WRITE = '''OUT_DIR = Path('/kaggle/working/jailbreak_out/cracked_31b')
OUT_DIR.mkdir(parents=True, exist_ok=True)

def _write_jsonl(path, rows):
    with open(path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\\n')

_write_jsonl(OUT_DIR / 'responses.jsonl', RESPONSES)
_write_jsonl(OUT_DIR / 'generations.jsonl', [
    {'idx': i, 'prompt': it, 'sha': sha8(it)} for i, it in enumerate(GEN_ITEMS)
])
(OUT_DIR / 'generations_raw.txt').write_text(GEN_RAW, encoding='utf-8')
meta = {
    'slot': 'cracked_31b',
    'display': 'Gemma 4 31B JANG CRACK (4-bit)',
    'type': 'cracked',
    'hf_id': HF_ID if SKIP_REASON is None else None,
    'device': DEVICE_NAME,
    'n_prompts': len(RESPONSES),
    'n_generated': len(GEN_ITEMS),
    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'condition': CONDITION,
    'skip_reason': SKIP_REASON,
    'min_free_gb': MIN_FREE_GB,
}
(OUT_DIR / 'meta.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
print(f'Wrote artifacts to {OUT_DIR}. skip_reason={SKIP_REASON}')
'''


SUMMARY = f"""---

## Summary and handoff

The 31B cracked variant is the most expensive arm of the comparison and the easiest to skip gracefully. Whether the gate fires or the full run completes, the artifact contract is the same: one folder under `/kaggle/working/jailbreak_out/cracked_31b/` with either real outputs or a `skip_reason` in `meta.json`. [185]({URL_185}) reads the folder either way.

### Next

- **Comparator:** [185 Jailbroken Gemma Comparison]({URL_185}).
- **Previous sibling:** [188 Uncensored Community]({URL_188}).
- **Back to navigation:** [000 Index]({URL_000}).
"""



AT_A_GLANCE_INTRO = """---

## At a glance

4-bit 31B cracked Gemma; skips gracefully on single T4.
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
    _stat_card('31B', 'model', 'dealignai/JANG_4M-CRACK', 'primary'),
    _stat_card('22 GB', 'VRAM required', 'gated', 'warning'),
    _stat_card('4-bit', 'nf4', 'device_map auto', 'info'),
    _stat_card('L4x4 / A100', 'GPU', 'skip on T4', 'danger')
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step('VRAM gate', '>= 22 GB', 'warning'),
    _step('Load 31B', '4-bit', 'primary'),
    _step('Run benchmark', '15 prompts', 'info'),
    _step('Gen red-team', '10 prompts', 'success')
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">31B gated run</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
'''



def build():
    cells = [
        md(HEADER),
        md(AT_A_GLANCE_INTRO),
        code(AT_A_GLANCE_CODE),
        md(SETUP_MD), code(PROMPT_SLICE),
        md("---\n\n## 1b. Inference wrappers\n"), code(INFER),
        md(GATE_MD), code(LOAD_SINGLE + "\n" + GATE),
        md(RUN_MD), code(RUN),
        md(WRITE_MD), code(WRITE),
        md(SUMMARY),
    ]
    nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": NB_METADATA, "cells": cells}
    nb = harden_notebook(nb, filename=FILENAME, requires_gpu=True)
    patch_final_print_cell(
        nb,
        final_print_src=(
            "print(\n"
            "    'Cracked 31B handoff >>> Comparator: '\n"
            f"    '{URL_185}'\n"
            "    '.'\n"
            ")\n"
        ),
        marker="Cracked 31B handoff >>>",
    )
    NB_DIR.mkdir(parents=True, exist_ok=True)
    KAGGLE_KERNELS.mkdir(parents=True, exist_ok=True)
    nb_path = NB_DIR / FILENAME
    nb_path.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    kernel_dir = KAGGLE_KERNELS / KERNEL_DIR_NAME
    kernel_dir.mkdir(parents=True, exist_ok=True)
    (kernel_dir / FILENAME).write_text(json.dumps(nb, indent=1), encoding="utf-8")
    meta = {
        "id": KERNEL_ID, "title": KERNEL_TITLE, "code_file": FILENAME,
        "language": "python", "kernel_type": "notebook", "is_private": False,
        "enable_gpu": True, "enable_tpu": False, "enable_internet": True,
        "dataset_sources": [WHEELS_DATASET, PROMPTS_DATASET],
        "competition_sources": ["gemma-4-good-hackathon"],
        "model_sources": [], "kernel_sources": [], "keywords": KEYWORDS,
    }
    (kernel_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {nb_path}")
    print(f"Wrote {kernel_dir / FILENAME}")


if __name__ == "__main__":
    build()
