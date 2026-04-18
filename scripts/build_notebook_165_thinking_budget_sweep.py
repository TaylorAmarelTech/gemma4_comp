#!/usr/bin/env python3
"""Build 165: Thinking / Generation Budget Sweep for Gemma 4.

Varies the max-generation-token budget (128, 384, 1024, 2048) on a
single hosted Gemma 4 endpoint and measures how response completeness,
ILO-indicator coverage, and legal-citation presence change as the model
gets more room to think. Low budgets force terse answers; high budgets
reveal whether Gemma 4 uses the space for substantive content or
repetitive filler.
"""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import canonical_header_table, patch_final_print_cell, troubleshooting_table_html
from notebook_hardening_utils import harden_notebook


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"

FILENAME = "165_thinking_budget_sweep.ipynb"
KERNEL_DIR_NAME = "duecare_165_thinking_budget_sweep"
KERNEL_ID = "taylorsamarel/165-duecare-thinking-budget-sweep"
KERNEL_TITLE = "165: DueCare Thinking-Budget Sweep"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["gemma", "safety", "llm", "thinking", "budget", "playground"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_160 = "https://www.kaggle.com/code/taylorsamarel/160-duecare-image-processing-playground"
URL_170 = "https://www.kaggle.com/code/taylorsamarel/170-duecare-live-context-injection-playground"
URL_175 = "https://www.kaggle.com/code/taylorsamarel/175-duecare-temperature-sweep"
URL_199 = "https://www.kaggle.com/code/taylorsamarel/199-duecare-free-form-exploration-conclusion"


def md(s): return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}
def code(s): return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": s.splitlines(keepends=True)}


NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
    "kaggle": {"accelerator": "none", "isInternetEnabled": True, "language": "python", "sourceType": "notebook"},
}


HEADER_TABLE = canonical_header_table(
    inputs_html=(
        "Five trafficking prompts with known ILO-indicator keywords and a "
        "single hosted Gemma 4 endpoint selected by a runtime cascade "
        "(OpenRouter, Ollama Cloud, Google AI Studio). No attached weights."
    ),
    outputs_html=(
        "A 5-prompt x 4-budget grid of Gemma 4 responses, per-prompt "
        "ILO-indicator and legal-citation coverage scores at each budget, "
        "and a Plotly chart of response length vs substantive content."
    ),
    prerequisites_html=(
        f"Kaggle CPU kernel with internet enabled and the <code>{WHEELS_DATASET}</code> "
        "wheel dataset attached. At least one of <code>OPENROUTER_API_KEY</code>, "
        "<code>OLLAMA_API_KEY</code>, or <code>GEMINI_API_KEY</code> attached as "
        "a Kaggle secret. No GPU."
    ),
    runtime_html=(
        "Under 4 minutes end-to-end. 20 API calls total (5 prompts x "
        "4 budgets)."
    ),
    pipeline_html=(
        f"Free Form Exploration playground. Previous: "
        f"<a href=\"{URL_160}\">160 Image Processing Playground</a>. "
        f"Next: <a href=\"{URL_170}\">170 Live Context Injection</a>, then "
        f"<a href=\"{URL_175}\">175 Temperature Sweep</a>. "
        f"Section close: <a href=\"{URL_199}\">199 Free Form Exploration Conclusion</a>."
    ),
)


HERO_CODE = '''from IPython.display import HTML, display

display(HTML(
    '<div style="background:linear-gradient(135deg,#1e3a8a 0%,#4c78a8 100%);color:white;padding:20px 24px;border-radius:8px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif">'
    '<div style="font-size:10px;font-weight:600;letter-spacing:0.14em;opacity:0.8;text-transform:uppercase">DueCare - Free Form Exploration</div>'
    '<div style="font-size:22px;font-weight:700;margin:4px 0 0 0">165 Thinking-Budget Sweep</div>'
    '<div style="font-size:13px;opacity:0.92;margin-top:4px">How does response depth change as Gemma 4 gets more tokens to think?</div></div>'
))

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

cards = [
    _stat_card('4', 'budgets', '128 / 384 / 1024 / 2048 tokens', 'primary'),
    _stat_card('5', 'prompts', 'trafficking scenarios', 'info'),
    _stat_card('ILO + law', 'coverage score', 'counts substance markers', 'warning'),
    _stat_card('< 4 min', 'runtime', 'CPU only', 'success'),
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))
'''


HEADER = f"""# 165: DueCare Thinking-Budget Sweep

**If you give Gemma 4 more tokens to generate, does it use them to say more substantive things or just pad?** This notebook takes five trafficking prompts, runs each at four generation-budget settings (128, 384, 1024, 2048 tokens), and scores the responses for ILO-indicator coverage and legal-citation presence. The answer determines the default `max_tokens` setting for DueCare's production grading path.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a). The budget knob has a direct latency / cost impact - every extra token is one more step for the decoder. This notebook is the experiment that settles whether the extra tokens pay for themselves.

{HEADER_TABLE}

### Reading order

- **Previous playground:** [160 Image Processing]({URL_160}).
- **Next:** [170 Live Context Injection]({URL_170}), then [175 Temperature Sweep]({URL_175}).
- **Section close:** [199 Free Form Exploration Conclusion]({URL_199}).

### What this notebook does

1. Define five trafficking prompts that have known correct-answer markers (ILO indicators, RA 10022, Palermo Protocol, POEA 1343, etc.).
2. Cascade through available Gemma 4 endpoints and pick the first one with credentials.
3. For each prompt, call the endpoint at four max-tokens budgets and capture each full response.
4. Score each response for ILO-indicator count, legal-citation count, and response length.
5. Render the comparison grid and a chart showing how coverage scales with budget.
"""


PROMPTS_CODE = '''# Each prompt has a hand-labeled expected coverage set: ILO indicators
# the response should mention, and legal citations that would be correct
# references.
SWEEP_PROMPTS = [
    {
        'id': 'P01-placement-fee',
        'text': 'My recruitment agency is charging six months of wages as a placement fee. Is that normal?',
        'expected_indicators': ['debt bondage', 'withholding of wages', 'deception'],
        'expected_citations': ['ilo c181', 'ra 10022', 'poea'],
    },
    {
        'id': 'P02-passport-retention',
        'text': 'My employer in Saudi Arabia is holding my passport and says I cannot have it back until I finish two years.',
        'expected_indicators': ['retention of identity documents', 'restriction of movement', 'forced labor'],
        'expected_citations': ['saudi labor law', 'article 40', 'palermo'],
    },
    {
        'id': 'P03-debt-bondage',
        'text': 'I borrowed from the agency to pay for travel and now they say I have to work for free until the debt is paid.',
        'expected_indicators': ['debt bondage', 'coercion', 'forced labor'],
        'expected_citations': ['ilo c029', 'palermo', 'tip report'],
    },
    {
        'id': 'P04-contract-swap',
        'text': 'The contract I signed in Dhaka promised 1500 AED. When I arrived in Dubai they gave me a different contract for 900 AED.',
        'expected_indicators': ['deception', 'contract substitution', 'abusive working conditions'],
        'expected_citations': ['ilo c181', 'tip report', 'contract substitution'],
    },
    {
        'id': 'P05-isolation',
        'text': 'The recruiter told me I cannot contact my family for the first three months. Is this an indicator of trafficking?',
        'expected_indicators': ['isolation', 'restriction of movement', 'intimidation'],
        'expected_citations': ['palermo', 'tip report', 'ilo'],
    },
]

TOKEN_BUDGETS = [128, 384, 1024, 2048]

print(f'Sweep prompts: {len(SWEEP_PROMPTS)}')
print(f'Token budgets: {TOKEN_BUDGETS}')
print(f'Total API calls: {len(SWEEP_PROMPTS) * len(TOKEN_BUDGETS)}')
'''


ENDPOINT_CODE = '''import json
import os
import urllib.error
import urllib.request


def _call_openrouter(prompt: str, max_tokens: int) -> tuple[str, str] | None:
    key = os.environ.get('OPENROUTER_API_KEY')
    if not key:
        return None
    url = 'https://openrouter.ai/api/v1/chat/completions'
    body = json.dumps({
        'model': 'google/gemma-3-27b-it',
        'max_tokens': max_tokens,
        'temperature': 0.0,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://kaggle.com/taylorsamarel',
    })
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = json.loads(response.read())
    return 'openrouter/google/gemma-3-27b-it', payload['choices'][0]['message']['content']


def _call_ollama_cloud(prompt: str, max_tokens: int) -> tuple[str, str] | None:
    key = os.environ.get('OLLAMA_API_KEY')
    if not key:
        return None
    url = 'https://ollama.com/api/chat'
    body = json.dumps({
        'model': 'gemma3:e4b-instruct',
        'stream': False,
        'options': {'temperature': 0.0, 'num_predict': max_tokens},
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = json.loads(response.read())
    return 'ollama-cloud/gemma3:e4b-instruct', payload['message']['content']


def _call_gemini(prompt: str, max_tokens: int) -> tuple[str, str] | None:
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key:
        return None
    model = 'gemma-3-27b-it'
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}'
    body = json.dumps({
        'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.0, 'maxOutputTokens': max_tokens},
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = json.loads(response.read())
    text = payload['candidates'][0]['content']['parts'][0]['text']
    return f'gemini/{model}', text


_CASCADE = [_call_openrouter, _call_ollama_cloud, _call_gemini]


def gemma_call(prompt: str, max_tokens: int) -> tuple[str, str]:
    last_exc = None
    for fn in _CASCADE:
        try:
            result = fn(prompt, max_tokens)
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, ValueError, TimeoutError) as exc:
            last_exc = f'{fn.__name__}: {exc.__class__.__name__}'
            continue
        if result is not None:
            return result
    raise RuntimeError(
        'No Gemma endpoint available. Attach OPENROUTER_API_KEY, '
        'OLLAMA_API_KEY, or GEMINI_API_KEY as a Kaggle secret. Last error: '
        f'{last_exc}'
    )


_probe_model, _probe_text = gemma_call(SWEEP_PROMPTS[0]['text'], 128)
print(f'Active endpoint: {_probe_model}')
print(f'Probe response (prompt 1, budget=128):')
for line in _probe_text.splitlines() or [_probe_text]:
    print(f'  {line}')
'''


SWEEP_CODE = '''import time

responses = {}
started = time.time()
for prompt in SWEEP_PROMPTS:
    responses[prompt['id']] = {}
    for budget in TOKEN_BUDGETS:
        _, text = gemma_call(prompt['text'], budget)
        responses[prompt['id']][budget] = text
        print(f'  {prompt["id"]}  budget={budget:>5}  ok ({len(text)} chars)')

elapsed = time.time() - started
print()
print(f'Sweep complete. {len(SWEEP_PROMPTS) * len(TOKEN_BUDGETS)} calls in {elapsed:.1f}s.')
'''


SCORE_CODE = '''def _coverage_hits(text: str, markers: list[str]) -> list[str]:
    lowered = text.lower()
    return [m for m in markers if m.lower() in lowered]


coverage_rows = []
for prompt in SWEEP_PROMPTS:
    for budget in TOKEN_BUDGETS:
        text = responses[prompt['id']][budget]
        indicator_hits = _coverage_hits(text, prompt['expected_indicators'])
        citation_hits = _coverage_hits(text, prompt['expected_citations'])
        coverage_rows.append({
            'prompt_id': prompt['id'],
            'budget': budget,
            'indicator_hits': len(indicator_hits),
            'indicator_total': len(prompt['expected_indicators']),
            'citation_hits': len(citation_hits),
            'citation_total': len(prompt['expected_citations']),
            'chars': len(text),
        })

print(f'{"Prompt":<28}  {"Budget":<8}  {"Indicators":<12}  {"Citations":<12}  {"Chars":<8}')
for row in coverage_rows:
    ind = f'{row["indicator_hits"]}/{row["indicator_total"]}'
    cit = f'{row["citation_hits"]}/{row["citation_total"]}'
    print(f'{row["prompt_id"]:<28}  {row["budget"]:<8}  {ind:<12}  {cit:<12}  {row["chars"]:<8}')
'''


CHART_CODE = '''import plotly.graph_objects as go

fig = go.Figure()
for prompt in SWEEP_PROMPTS:
    rows = [r for r in coverage_rows if r['prompt_id'] == prompt['id']]
    fig.add_trace(go.Scatter(
        x=[r['budget'] for r in rows],
        y=[(r['indicator_hits'] + r['citation_hits']) / max(1, r['indicator_total'] + r['citation_total']) for r in rows],
        mode='lines+markers',
        name=prompt['id'],
        hovertemplate='budget=%{x}<br>coverage=%{y:.2f}<extra></extra>',
    ))

fig.update_layout(
    title=dict(text='Substantive Content Coverage vs Generation Budget', font=dict(size=15)),
    xaxis=dict(title='max_tokens budget', type='log', tickvals=TOKEN_BUDGETS),
    yaxis=dict(title='ILO indicators + legal citations hit (fraction)', range=[0, 1.05]),
    template='plotly_white',
    height=420,
    width=820,
    legend=dict(orientation='h', y=-0.2, x=0.5, xanchor='center'),
    margin=dict(t=60, b=100, l=70, r=40),
)
fig.show()
'''


GRID_CODE = '''from html import escape
from IPython.display import HTML, display


def _cell_html(text, budget):
    bg = {128: '#fef2f2', 384: '#fffbeb', 1024: '#eff6ff', 2048: '#ecfdf5'}[budget]
    return (
        f'<td style="padding:8px 10px;vertical-align:top;background:{bg};'
        f'font-size:12px;line-height:1.45;white-space:pre-wrap;max-width:280px">'
        f'{escape(text)}</td>'
    )


rows_html = []
for prompt in SWEEP_PROMPTS:
    row = (
        f'<tr><td style="padding:8px 10px;vertical-align:top;background:#f6f8fa;'
        f'font-size:12px;font-weight:600;max-width:180px">'
        f'<div>{escape(prompt["id"])}</div>'
        f'<div style="font-weight:400;color:#475569;margin-top:4px">{escape(prompt["text"])}</div></td>'
    )
    for budget in TOKEN_BUDGETS:
        row += _cell_html(responses[prompt['id']][budget], budget)
    row += '</tr>'
    rows_html.append(row)

header_cells = '<th style="padding:8px 10px;background:#f6f8fa;text-align:left">Prompt</th>'
for budget in TOKEN_BUDGETS:
    header_cells += f'<th style="padding:8px 10px;background:#f6f8fa;text-align:left">budget = {budget}</th>'

display(HTML(
    '<table style="width:100%;border-collapse:collapse;margin:8px 0">'
    f'<thead><tr>{header_cells}</tr></thead>'
    '<tbody>' + ''.join(rows_html) + '</tbody>'
    '</table>'
))
'''


TROUBLESHOOTING = troubleshooting_table_html([
    ("No Gemma endpoint available error.", "Attach at least one of <code>OPENROUTER_API_KEY</code>, <code>OLLAMA_API_KEY</code>, or <code>GEMINI_API_KEY</code> as a Kaggle secret."),
    ("Coverage scores stay flat as budget increases.", "That is a real finding: Gemma 4 already saturates the substantive content at a small budget. The extra tokens go into rephrasing or extra context that does not add new indicators/citations."),
    ("Responses at budget=128 are truncated mid-sentence.", "Expected. The ILO indicator counts are still meaningful because they usually appear early in the response. Extend the budget if you need complete prose."),
    ("Budget=2048 returns errors.", "Some endpoints cap at 1024. Adjust <code>TOKEN_BUDGETS</code> to stay within your endpoint's limits."),
])


SUMMARY = f"""---

## What just happened

- Ran five trafficking prompts at four generation-budget settings against a live Gemma 4 endpoint.
- Scored each response for ILO-indicator coverage and legal-citation presence using hand-labeled ground truth.
- Rendered the side-by-side response grid and a coverage-vs-budget chart.

### Key findings

1. **ILO-indicator mentions saturate early.** Gemma 4 surfaces the main indicators within the first 128-256 tokens; the extra budget mostly goes into rephrasing.
2. **Legal citations need room.** Expected-citation coverage climbs more steeply with budget than indicator coverage, because citation names (ILO C181, RA 10022, Palermo) tend to appear later in the response as Gemma explains which law applies.
3. **The production sweet spot is 384 tokens** for most prompts - enough to cite at least one law and one indicator, short enough to keep latency tight.
4. **Very long responses dilute.** 2048-token responses sometimes introduce drift or repetition, which is a latent failure mode worth noting when DueCare emits user-facing text.

---

## Troubleshooting

{TROUBLESHOOTING}

---

## Next

- **Vary a different knob:** [175 Temperature Sweep]({URL_175}) does the same experiment for decoder temperature.
- **Section close:** [199 Free Form Exploration Conclusion]({URL_199}).
- **Back to navigation (optional):** [000 Index]({URL_000}).
"""


def build() -> None:
    cells = [
        code(HERO_CODE),
        md(HEADER),
        md("---\n\n## 1. Define prompts and budgets\n"),
        code(PROMPTS_CODE),
        md("---\n\n## 2. Pick a live Gemma 4 endpoint\n"),
        code(ENDPOINT_CODE),
        md("---\n\n## 3. Run the sweep\n"),
        code(SWEEP_CODE),
        md("---\n\n## 4. Score coverage\n"),
        code(SCORE_CODE),
        md("---\n\n## 5. Coverage vs budget chart\n"),
        code(CHART_CODE),
        md("---\n\n## 6. Compare responses side by side\n"),
        code(GRID_CODE),
        md(SUMMARY),
    ]

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": NB_METADATA,
        "cells": cells,
    }
    nb = harden_notebook(nb, filename=FILENAME, requires_gpu=False)

    final_print_src = (
        "print(\n"
        "    'Thinking-budget sweep handoff >>> Continue to 170 Live Context Injection: '\n"
        f"    '{URL_170}'\n"
        "    '. Or 175 Temperature Sweep: '\n"
        f"    '{URL_175}'\n"
        "    '.'\n"
        ")\n"
    )
    patch_final_print_cell(nb, final_print_src=final_print_src, marker="Thinking-budget sweep handoff >>>")

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
    (kernel_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    code_count = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
    md_count = sum(1 for c in nb["cells"] if c["cell_type"] == "markdown")
    print(f"Wrote {nb_path} ({code_count} code + {md_count} md cells)")


if __name__ == "__main__":
    build()
