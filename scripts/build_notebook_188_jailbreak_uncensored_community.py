#!/usr/bin/env python3
"""Build 188: uncensored community Gemma variant.

Community uncensored / abliterated weights churn rapidly on Hugging Face
(renames, repo deletions, gating). This notebook probes a ranked list of
candidate model ids at runtime and uses the first one that loads. A
clear error is printed if none resolve; the artifact for this slot is
still written (with ``hf_id: null``) so the 185 comparator can note the
gap instead of crashing.

NVFP4-quantized uncensored weights (e.g. ``*-NVFP4``) need a
Blackwell-class GPU (RTX 5090 / B100) and cannot run on any Kaggle
accelerator as of 2026-04. Those ids are explicitly excluded from the
probe list.
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

FILENAME = "188_jailbreak_uncensored_community.ipynb"
KERNEL_DIR_NAME = "duecare_188_jailbreak_uncensored_community"
KERNEL_ID = "taylorsamarel/duecare-188-jailbreak-uncensored-community"
KERNEL_TITLE = "188: DueCare Jailbreak - Uncensored Community"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
PROMPTS_DATASET = "taylorsamarel/duecare-trafficking-prompts"
KEYWORDS = ["gemma", "safety", "jailbreak", "uncensored"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_185 = "https://www.kaggle.com/code/taylorsamarel/duecare-185-jailbroken-gemma-comparison"
URL_187 = "https://www.kaggle.com/code/taylorsamarel/duecare-187-jailbreak-abliterated-e4b"
URL_189 = "https://www.kaggle.com/code/taylorsamarel/duecare-189-jailbreak-cracked-31b"


def md(s): return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}
def code(s): return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": s.splitlines(keepends=True)}


NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
    "kaggle": {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": True, "language": "python", "sourceType": "notebook"},
}


HEADER_TABLE = canonical_header_table(
    inputs_html=(
        "A ranked list of candidate uncensored Gemma model ids on "
        "Hugging Face, probed at runtime. The first id that resolves "
        "is loaded. The 15-prompt graded trafficking slice drives the "
        "response comparison."
    ),
    outputs_html=(
        "Artifact bundle under "
        "<code>/kaggle/working/jailbreak_out/uncensored_community/</code> "
        "with <code>responses.jsonl</code>, "
        "<code>generations.jsonl</code>, "
        "<code>generations_raw.txt</code>, and <code>meta.json</code> "
        "including the <code>hf_id</code> that actually loaded. If no "
        "candidate resolves, an empty artifact with an explanatory "
        "<code>meta.json</code> is still written so the 185 comparator "
        "can note the gap."
    ),
    prerequisites_html=(
        "Kaggle T4 kernel with internet enabled and the "
        f"<code>{WHEELS_DATASET}</code> wheel dataset attached. HF "
        "token is optional but recommended if any candidate is gated."
    ),
    runtime_html="5 to 10 minutes on T4 for the first resolvable candidate.",
    pipeline_html=(
        f"Free Form Exploration, per-model data-collection notebook. "
        f"Previous sibling: <a href=\"{URL_187}\">187 Abliterated E4B"
        f"</a>. Next sibling: <a href=\"{URL_189}\">189 Cracked 31B"
        f"</a>. Comparator: <a href=\"{URL_185}\">185 Jailbroken Gemma "
        f"Comparison</a>."
    ),
)


HEADER = f"""# 188: DueCare Jailbreak - Uncensored Community

**Pull the first resolvable uncensored / abliterated Gemma variant from Hugging Face and run it on the same benchmark the stock and in-kernel-abliterated variants saw.** This arm of the jailbreak comparison answers a different question than 187: not "can we reproduce the uncensored distribution from scratch" but "what does the uncensored distribution that other red-teamers are actually publishing look like when we judge it with the DueCare rubric". The two answers usually match qualitatively but diverge in magnitude and in the attack categories that come up easiest.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a).

{HEADER_TABLE}

### Why a probe list and not a single id

Community uncensored weights churn. Repos are renamed, pulled for policy violations, or replaced with a newer iteration; a hard-coded id fails silently if the maintainer moves the checkpoint. The probe list below is ordered by closeness to Gemma 4 E4B with a stock-size fallback to Gemma 3 4B when E4B-class uncensored variants are not yet available on HF at notebook runtime. Each candidate is tried in order and the first one that loads wins.

### NVFP4 caveat

Variants tagged `*-NVFP4` (e.g. the `AEON-7/*-NVFP4` family) are quantized with a format that requires Blackwell GPUs (RTX 5090 / B100 / H200+) and cannot run on any Kaggle accelerator as of 2026-04. They are deliberately excluded from the probe list; if a later notebook run has access to Blackwell hardware, add them to `CANDIDATES` above the fp16/nf4 fallbacks.

### Reading order

- **Parent comparator:** [185 Jailbroken Gemma Comparison]({URL_185}).
- **Previous sibling:** [187 Abliterated E4B]({URL_187}).
- **Next sibling:** [189 Cracked 31B]({URL_189}).
- **Back to navigation:** [000 Index]({URL_000}).
"""


SETUP_MD = "---\n\n## 1. Environment and prompt slice\n"
PROBE_MD = """---

## 2. Candidate probe list and loader

The probe list below is ordered best-match-first. If you have an HF access token for a gated repo, set the `HF_TOKEN` Kaggle secret before running the cell.
"""

PROBE = '''CANDIDATES = [
    # Best-match: E4B-class uncensored Gemma 4, nf4 or fp16-compatible.
    'huihui-ai/gemma-4-e4b-it-abliterated',
    'huihui-ai/gemma-4-A4B-it-abliterated',
    'AEON-7/Gemma-4-A4B-it-Uncensored',        # NVFP4 variants deliberately excluded
    'mlabonne/Gemma-4-E4B-it-abliterated',
    # Gemma 3 fallback (clearly labeled in meta).
    'mlabonne/gemma-3-4b-it-abliterated',
    'huihui-ai/gemma-3-4b-it-abliterated',
]

# Pull the HF_TOKEN secret if one is set.
try:
    from kaggle_secrets import UserSecretsClient
    HF_TOKEN = UserSecretsClient().get_secret('HF_TOKEN')
    os.environ['HF_TOKEN'] = HF_TOKEN
    print('HF_TOKEN: found')
except Exception:
    HF_TOKEN = os.environ.get('HF_TOKEN')
    print(f'HF_TOKEN: {\"found\" if HF_TOKEN else \"not set (gated repos will fail)\"}')

HF_ID = None
load_errs = []
tok = mdl = None

for cand in CANDIDATES:
    try:
        print(f'\\nTrying {cand} ...')
        tok, mdl = load_4bit(cand)
        HF_ID = cand
        print(f'Loaded {cand}.')
        break
    except Exception as exc:
        msg = str(exc)[:200]
        print(f'  -> failed: {msg}')
        load_errs.append((cand, msg))
        _free_gpu()

if HF_ID is None:
    print('\\nNo candidate loaded. Writing an empty artifact bundle so the 185 comparator can note the gap.')
'''


RUN_MD = "---\n\n## 3. Run benchmark and red-team generation\n"
RUN = '''RESPONSES = []
GEN_ITEMS = []
GEN_RAW = ''
CONDITION = 'uncensored_community'

if HF_ID is not None:
    print(f'Running {len(PROMPTS)} benchmark prompts on {HF_ID} ...')
    RESPONSES = respond_to_prompts(tok, mdl, PROMPTS)
    print('Running red-team generation ...')
    GEN_ITEMS, GEN_RAW = generate_redteam(tok, mdl, n=10)
    print(f'Generated {len(GEN_ITEMS)} red-team prompts.')
else:
    print('Skipped inference (no candidate loaded).')
'''


WRITE_MD = "---\n\n## 4. Write artifacts\n"
WRITE = '''OUT_DIR = Path('/kaggle/working/jailbreak_out/uncensored_community')
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
    'slot': 'uncensored_community',
    'display': f'Gemma uncensored community ({HF_ID})' if HF_ID else 'Gemma uncensored community (no candidate resolved)',
    'type': 'uncensored',
    'hf_id': HF_ID,
    'device': DEVICE_NAME,
    'n_prompts': len(RESPONSES),
    'n_generated': len(GEN_ITEMS),
    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'condition': CONDITION,
    'load_errors': load_errs,
    'candidate_list': CANDIDATES,
}
(OUT_DIR / 'meta.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
print(f'Wrote artifacts to {OUT_DIR}. hf_id={HF_ID}')
'''


SUMMARY = f"""---

## Summary and handoff

An uncensored community Gemma variant was probed from a ranked candidate list, the first-resolvable id was loaded, and its outputs were written under the standard artifact contract. If no id resolved (network issue, gated repos, all candidates removed), an empty artifact bundle with diagnostic `load_errors` was written so [185]({URL_185}) can render the gap honestly.

### Next

- **Comparator:** [185 Jailbroken Gemma Comparison]({URL_185}).
- **Previous sibling:** [187 Abliterated E4B]({URL_187}).
- **Next sibling:** [189 Cracked 31B]({URL_189}).
- **Back to navigation:** [000 Index]({URL_000}).
"""



AT_A_GLANCE_INTRO = """---

## At a glance

Load the first resolvable community uncensored Gemma variant.
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
    _stat_card('ranked', 'probe list', 'huihui / AEON-7 / mlabonne', 'primary'),
    _stat_card('first', 'that loads', 'fallback chain', 'info'),
    _stat_card('NVFP4', 'excluded', 'Blackwell-only', 'warning'),
    _stat_card('T4', 'GPU', '4-bit load', 'success')
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step('Probe candidates', 'HF hub', 'primary'),
    _step('Load first', '4-bit', 'info'),
    _step('Run benchmark', '15 prompts', 'warning'),
    _step('Gen red-team', '10 prompts', 'success')
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">Community probe</div>'
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
        md(PROBE_MD), code(LOAD_SINGLE + "\n" + PROBE),
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
            "    'Uncensored community handoff >>> Comparator: '\n"
            f"    '{URL_185}'\n"
            "    '. Next sibling: '\n"
            f"    '{URL_189}'\n"
            "    '.'\n"
            ")\n"
        ),
        marker="Uncensored community handoff >>>",
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
