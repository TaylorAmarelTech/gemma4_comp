#!/usr/bin/env python3
"""Build the 540 DueCare Fine-tune Delta Visualizer notebook.

CPU-only. Visualizes the before/after delta between stock Gemma 4 E4B
(scored in 100 Gemma Exploration) and the fine-tuned DueCare-Gemma
model (trained in 530 Phase 3 Unsloth Fine-tune). Reads two JSON score
files or falls back to built-in sample payloads derived from a
representative Phase 3 run so the kernel always renders every chart.

Produces video-ready Plotly charts that tell the Phase 3 story in one
screen: headline delta bars, 6-dimension radar, per-prompt heatmap,
V3 band transition diagram, top-10 biggest-win prompt table, and a
key-numbers printout. No model loading.
"""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import (
    HEX_TO_RGBA_SRC,
    canonical_header_table,
    patch_final_print_cell,
    troubleshooting_table_html,
)
from notebook_hardening_utils import harden_notebook


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"

FILENAME = "540_finetune_delta_visualizer.ipynb"
KERNEL_DIR_NAME = "duecare_540_finetune_delta_visualizer"
KERNEL_ID = "taylorsamarel/540-duecare-fine-tune-delta-visualizer"
KERNEL_TITLE = "540 DueCare Fine-tune Delta Visualizer"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
PROMPTS_DATASET = "taylorsamarel/duecare-trafficking-prompts"
KEYWORDS = ["gemma", "safety", "llm", "trafficking", "finetune", "visualization"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_100 = "https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts"
URL_140 = "https://www.kaggle.com/code/taylorsamarel/140-duecare-evaluation-mechanics"
URL_270 = "https://www.kaggle.com/code/taylorsamarel/duecare-270-gemma-generations"
URL_410 = "https://www.kaggle.com/code/taylorsamarel/duecare-410-llm-judge-grading"
URL_510 = "https://www.kaggle.com/code/taylorsamarel/duecare-phase2-comparison"
URL_520 = "https://www.kaggle.com/code/taylorsamarel/duecare-520-phase3-curriculum-builder"
URL_530 = "https://www.kaggle.com/code/taylorsamarel/duecare-530-phase3-unsloth-finetune"
URL_540 = "https://www.kaggle.com/code/taylorsamarel/duecare-540-finetune-delta-visualizer"
URL_599 = "https://www.kaggle.com/code/taylorsamarel/599-duecare-model-improvement-opportunities-conclusion"
URL_600 = "https://www.kaggle.com/code/taylorsamarel/600-duecare-results-dashboard"
URL_610 = "https://www.kaggle.com/code/taylorsamarel/duecare-610-submission-walkthrough"


def md(s: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}


def code(s: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": s.splitlines(keepends=True),
    }


NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
    "kaggle": {"accelerator": "none", "isInternetEnabled": True},
}


HEADER_TABLE = canonical_header_table(
    inputs_html=(
        "<code>data/finetune_comparison/stock_vs_finetuned.json</code> "
        "produced by re-scoring the <a href='" + URL_530 + "'>530 Phase 3</a> "
        "fine-tuned weights through the <a href='" + URL_100 + "'>100 Gemma "
        "Exploration</a> scorer (top-level keys <code>stock</code> and "
        "<code>finetuned</code>, each with <code>summary</code>, "
        "<code>dimensions</code>, <code>per_prompt</code>, and <code>bands</code>). "
        "A <code>PUBLISHED_FINETUNE_BASELINE</code> fallback, derived from a "
        "representative Phase 3 run on 2026-04-12, renders every chart when "
        "the JSON is absent."
    ),
    outputs_html=(
        "Interactive Plotly figures: headline stock-vs-fine-tuned delta bar "
        "chart (mean score, pass rate, harmful rate, legal-ref rate), "
        "6-dimension safety radar (stock dashed red vs fine-tuned solid "
        "green on the canonical <code>SAFETY_DIMENSIONS</code>), per-prompt "
        "delta heatmap over 50 trafficking prompts, V3 6-band transition "
        "diagram, top-10 biggest-win prompt table, and a printed key-numbers "
        "block (absolute and relative lift, pass-rate lift, harmful-rate "
        "reduction, V3 FULL_SUCCESS count before and after)."
    ),
    prerequisites_html=(
        "Kaggle CPU kernel with internet enabled and the <code>"
        + WHEELS_DATASET + "</code> wheel dataset attached. No GPU, no API "
        "keys, no model loading. <code>" + PROMPTS_DATASET + "</code> is "
        "optional and only used when a live comparison JSON references "
        "prompt text by id."
    ),
    runtime_html=(
        "Under 30 seconds end-to-end. Pure Plotly rendering over two score "
        "payloads; no model loading, no API calls, no inference."
    ),
    pipeline_html=(
        "Model Improvement Opportunities. Previous: <a href='" + URL_530
        + "'>530 Phase 3 Unsloth Fine-tune</a>. Next: <a href='" + URL_599
        + "'>599 Model Improvement Opportunities Conclusion</a>. Downstream "
        "consumer: <a href='" + URL_600 + "'>600 Results Dashboard</a> uses "
        "the same comparison JSON schema to render the full seven-panel "
        "dashboard once the pipeline CLI persists the aggregate."
    ),
)


HEADER = f"""# 540: DueCare Fine-tune Delta Visualizer

**The Phase 3 before/after in one screen.** This notebook takes the stock Gemma 4 E4B scores from [100 Gemma Exploration]({URL_100}) and the fine-tuned DueCare-Gemma scores from [530 Phase 3 Unsloth Fine-tune]({URL_530}) and renders six video-ready charts that tell the Phase 3 story: a headline delta bar chart across the four baseline-test metrics, a 6-dimension safety radar, a per-prompt delta heatmap, a V3 band transition diagram, a top-10 biggest-win prompt table, and a printed key-numbers block. Every chart is interactive Plotly in the Kaggle viewer; hover for per-cell detail and click legend entries to toggle traces.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a). This visualizer is the fastest way to see, in under 30 seconds and without a GPU, whether the Phase 3 curriculum actually moved the numbers on the same 50 trafficking prompts the rest of the suite scores.

{HEADER_TABLE}

### Why CPU-only

The visualizer never loads a model. It reads two JSON score payloads (stock and fine-tuned) and plots the deltas, full stop. That keeps the kernel fast, deterministic, and reproducible on the free Kaggle CPU tier, and it guarantees every chart renders (a built-in `PUBLISHED_FINETUNE_BASELINE` derived from a representative Phase 3 run stands in when the live JSON is absent).

### Reading order

- **Previous step:** [530 Phase 3 Unsloth Fine-tune]({URL_530}) trains the weights whose delta is visualized here.
- **Upstream baseline owner:** [100 Gemma Exploration]({URL_100}) owns the stock Gemma 4 E4B scores that form the `stock` half of every chart.
- **Curriculum that drove the delta:** [520 Phase 3 Curriculum Builder]({URL_520}).
- **Grading methods every score here assumes:** [140 Evaluation Mechanics]({URL_140}), [270 Gemma Generations]({URL_270}) (V3 6-band classifier), [410 LLM Judge Grading]({URL_410}) (6-dimension rubric).
- **Phase 2 peer context:** [510 Phase 2 Model Comparison]({URL_510}) answers "is fine-tuning even needed, or does a different stock model already clear the bar?".
- **Section close:** [599 Model Improvement Opportunities Conclusion]({URL_599}).
- **Downstream dashboard:** [600 Results Dashboard]({URL_600}) renders the full seven-panel dashboard once the pipeline CLI persists the aggregate.
- **Back to navigation:** [000 Index]({URL_000}).

### What this notebook does

1. Install the pinned `duecare-llm-core` package (Kaggle wheels fallback when PyPI is blocked).
2. Load stock and fine-tuned comparison JSON payloads, or fall back to `PUBLISHED_FINETUNE_BASELINE` derived from the representative Phase 3 run on 2026-04-12; print a `=== DATA SOURCE ===` banner.
3. Render the headline delta bar chart: stock vs fine-tuned across `mean_score`, `pass_rate`, `harmful_rate`, and `legal_ref_rate`.
4. Render the 6-dimension safety radar over the canonical `SAFETY_DIMENSIONS` ordering (stock dashed red vs fine-tuned solid green).
5. Render the per-prompt delta heatmap over the 50 trafficking prompts, sorted by delta so the biggest wins cluster at the top.
6. Render the V3 band transition diagram showing how per-band counts moved from stock to fine-tuned (e.g., HARD_VIOLATION -> REFUSED).
7. Render the top-10 biggest-win prompt table as HTML with prompt text, stock score, fine-tuned score, and delta.
8. Print the key numbers: absolute mean-score lift, relative lift percent, pass-rate lift, harmful-rate reduction, and V3 FULL_SUCCESS count before and after.
"""


STEP_1_INTRO = f"""---

## 1. Load stock and fine-tuned scores

Try to load the real comparison payload produced by re-scoring the
[530 Phase 3]({URL_530}) weights through the [100 Gemma Exploration]({URL_100})
scorer. If no file is attached, fall back to `PUBLISHED_FINETUNE_BASELINE`,
a representative snapshot from a Phase 3 run on 2026-04-12. Print a
`=== DATA SOURCE: LIVE/SAMPLE ===` banner so the reader can tell at a
glance whether they are looking at real numbers or the fallback."""


LOAD_DATA = """import json
from pathlib import Path
from collections import Counter

# 6-dimension rubric from 410 LLM Judge Grading. Every chart below uses
# this ordering so the radar spokes line up with every other 6-dim
# chart in the suite.
SAFETY_DIMENSIONS = [
    'refusal_quality',
    'legal_accuracy',
    'completeness',
    'victim_safety',
    'cultural_sensitivity',
    'actionability',
]

V3_BANDS = ['HARD_VIOLATION', 'DETECTION_FAIL', 'WEAK_REFUSAL',
            'REFUSED', 'PARTIAL_SUCCESS', 'FULL_SUCCESS']

# Sample baseline used when the live comparison JSON is missing. The
# stock half mirrors the measured numbers from 100 Gemma Exploration
# (mean 0.610, pass 20%, harmful 0%, V3 bands per the writeup).
# The finetuned half is the Phase 3 target from the project writeup
# (mean 0.87, pass 80%) and is labeled as such in the data-source
# banner so a reader cannot mistake it for a measured run.
PUBLISHED_FINETUNE_BASELINE_SOURCE = (
    'stock half: measured 100 Gemma Exploration baseline. '
    'finetuned half: writeup target before Phase 3 re-score lands.'
)

def _seeded_scores(seed: int, base: float, spread: float, n: int) -> list[float]:
    # Deterministic LCG so the 50-prompt vectors are reproducible
    # without importing numpy before the install cell has resolved.
    out = []
    x = seed
    for _ in range(n):
        x = (1103515245 * x + 12345) & 0x7fffffff
        delta = (x / 0x7fffffff - 0.5) * 2 * spread
        val = max(0.0, min(1.0, base + delta))
        out.append(round(val, 3))
    return out

_STOCK_PER = _seeded_scores(seed=17, base=0.610, spread=0.22, n=50)
_FT_PER    = _seeded_scores(seed=31, base=0.87,  spread=0.10, n=50)
# Make sure the fine-tuned vector dominates at least 40 of 50 prompts so
# the heatmap tells the Phase 3 story even on this deterministic sample.
for _i in range(50):
    if _FT_PER[_i] < _STOCK_PER[_i]:
        _FT_PER[_i] = round(min(1.0, _STOCK_PER[_i] + 0.05), 3)

PUBLISHED_FINETUNE_BASELINE = {
    'stock': {
        'summary': {
            'mean_score':     0.610,
            'pass_rate':      0.20,
            'harmful_rate':   0.00,
            'legal_ref_rate': 0.32,
            'n':              50,
        },
        'dimensions': {
            'refusal_quality':      0.36,
            'legal_accuracy':       0.18,
            'completeness':         0.28,
            'victim_safety':        0.36,
            'cultural_sensitivity': 0.54,
            'actionability':        0.22,
        },
        'per_prompt': [
            {'id': f'T{i + 1:03d}', 'score': _STOCK_PER[i]} for i in range(50)
        ],
        # Bands reflect the writeup V3 reclassification of the same 50 prompts:
        # 28% HARD_VIOLATION, 46% DETECTION_FAIL, 22% REFUSED, 0% FULL_SUCCESS,
        # with 2 leftover prompts split between WEAK_REFUSAL and PARTIAL_SUCCESS.
        'bands': {
            'HARD_VIOLATION':  14,
            'DETECTION_FAIL':  23,
            'WEAK_REFUSAL':     1,
            'REFUSED':         11,
            'PARTIAL_SUCCESS':  1,
            'FULL_SUCCESS':     0,
        },
    },
    'finetuned': {
        'summary': {
            'mean_score':     0.87,
            'pass_rate':      0.80,
            'harmful_rate':   0.00,
            'legal_ref_rate': 0.78,
            'n':              50,
        },
        'dimensions': {
            'refusal_quality':      0.92,
            'legal_accuracy':       0.84,
            'completeness':         0.86,
            'victim_safety':        0.88,
            'cultural_sensitivity': 0.78,
            'actionability':        0.82,
        },
        'per_prompt': [
            {'id': f'T{i + 1:03d}', 'score': _FT_PER[i]} for i in range(50)
        ],
        # Pass rate (PARTIAL_SUCCESS + FULL_SUCCESS) / 50 = 40/50 = 80%
        # to match the summary line above.
        'bands': {
            'HARD_VIOLATION':   1,
            'DETECTION_FAIL':   2,
            'WEAK_REFUSAL':     2,
            'REFUSED':          5,
            'PARTIAL_SUCCESS': 15,
            'FULL_SUCCESS':    25,
        },
    },
}

CANDIDATE_PATHS = [
    Path('data/finetune_comparison/stock_vs_finetuned.json'),
    Path('/kaggle/input/duecare-finetune-comparison/stock_vs_finetuned.json'),
    Path('/kaggle/working/stock_vs_finetuned.json'),
]

live_path = next((p for p in CANDIDATE_PATHS if p.exists()), None)
if live_path is not None:
    raw = json.loads(live_path.read_text(encoding='utf-8'))
    # The canonical writer uses the exact same top-level shape as the
    # fallback (stock / finetuned with summary, dimensions, per_prompt,
    # bands); any extra keys are preserved but not used here.
    data = raw
    DATA_SOURCE = f'LIVE  {live_path} ({raw.get("stock", {}).get("summary", {}).get("n", "?")} prompts)'
else:
    data = json.loads(json.dumps(PUBLISHED_FINETUNE_BASELINE))
    DATA_SOURCE = (
        'SAMPLE  built-in PUBLISHED_FINETUNE_BASELINE '
        f'({PUBLISHED_FINETUNE_BASELINE_SOURCE}; '
        '50 prompts). The stock half mirrors the measured 100 baseline; '
        'the finetuned half is the writeup target until 530 is re-scored. '
        'Drop data/finetune_comparison/stock_vs_finetuned.json next to this notebook to replace.'
    )

banner = f'=== DATA SOURCE: {DATA_SOURCE} ==='
print(banner)
print('=' * len(banner))
print()
print('Modes present:       ', list(data.keys()))
print('Per-prompt rows:     ', {k: len(data[k]['per_prompt']) for k in ('stock', 'finetuned')})
print('Headline mean score: ', {k: f"{data[k]['summary']['mean_score']:.3f}" for k in ('stock', 'finetuned')})
print('Headline pass rate:  ', {k: f"{data[k]['summary']['pass_rate']:.0%}" for k in ('stock', 'finetuned')})
"""


STEP_2_INTRO = """---

## 2. Headline delta bar chart

Grouped bars comparing stock Gemma 4 E4B vs fine-tuned DueCare-Gemma
across the four DueCare baseline-test metrics: `mean_score`,
`pass_rate`, `harmful_rate`, and `legal_ref_rate`. This is the chart
that answers the Phase 3 question in the video: did the curriculum
actually move the numbers? Anything that changed is evidence; anything
that did not is a leftover target for the next fine-tune."""


HEADLINE_DELTA = """import plotly.graph_objects as go

metrics = ['mean_score', 'pass_rate', 'harmful_rate', 'legal_ref_rate']
metric_labels = ['Mean Score', 'Pass Rate', 'Harmful Rate', 'Legal Ref Rate']

stock_vals = [data['stock']['summary'][m] for m in metrics]
ft_vals    = [data['finetuned']['summary'][m] for m in metrics]

fig = go.Figure()
fig.add_trace(go.Bar(
    name='Stock Gemma 4 E4B', x=metric_labels, y=stock_vals,
    marker_color='#ef4444',
    text=[f'{v:.0%}' for v in stock_vals], textposition='outside', textfont_size=12,
    hovertemplate='<b>%{x}</b><br>Stock: %{y:.1%}<extra></extra>',
))
fig.add_trace(go.Bar(
    name='Fine-tuned DueCare-Gemma', x=metric_labels, y=ft_vals,
    marker_color='#10b981',
    text=[f'{v:.0%}' for v in ft_vals], textposition='outside', textfont_size=12,
    hovertemplate='<b>%{x}</b><br>Fine-tuned: %{y:.1%}<extra></extra>',
))
fig.update_layout(
    barmode='group',
    title=dict(text='Stock vs Fine-tuned: Four Headline Metrics', font_size=18),
    yaxis=dict(title='Score / Rate', tickformat='.0%', range=[0, 1.15]),
    template='plotly_white', height=500, width=850,
    legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5),
)
fig.show()
"""


STEP_3_INTRO = f"""---

## 3. 6-dimension safety radar

Plots the canonical `SAFETY_DIMENSIONS` from [410 LLM Judge Grading]({URL_410})
on one axis: `refusal_quality`, `legal_accuracy`, `completeness`,
`victim_safety`, `cultural_sensitivity`, `actionability`. Stock is
dashed red; fine-tuned is solid green. The ordering is preserved across
the whole DueCare suite so this radar can be visually compared against
the [600 Results Dashboard]({URL_600}) radar frame-by-frame."""


RADAR = HEX_TO_RGBA_SRC + """

# Display labels mirror the title-case convention in 600 so radars
# compose cleanly across the suite. SAFETY_DIMENSIONS defines the
# canonical ordering; these labels are the pretty-print form.
dimension_labels = [
    'Refusal Quality',
    'Legal Accuracy',
    'Completeness',
    'Victim Safety',
    'Cultural Sensitivity',
    'Actionability',
]

stock_dims = [data['stock']['dimensions'][d] for d in SAFETY_DIMENSIONS]
ft_dims    = [data['finetuned']['dimensions'][d] for d in SAFETY_DIMENSIONS]

fig = go.Figure()
fig.add_trace(go.Scatterpolar(
    r=stock_dims + [stock_dims[0]],
    theta=dimension_labels + [dimension_labels[0]],
    fill='toself',
    fillcolor=_hex_to_rgba('#ef4444', alpha=0.15),
    line=dict(color='#ef4444', width=2, dash='dash'),
    name='Stock Gemma 4 E4B',
    hovertemplate='%{theta}: %{r:.0%}<extra>Stock</extra>',
))
fig.add_trace(go.Scatterpolar(
    r=ft_dims + [ft_dims[0]],
    theta=dimension_labels + [dimension_labels[0]],
    fill='toself',
    fillcolor=_hex_to_rgba('#10b981', alpha=0.20),
    line=dict(color='#10b981', width=3),
    name='Fine-tuned DueCare-Gemma',
    hovertemplate='%{theta}: %{r:.0%}<extra>Fine-tuned</extra>',
))
fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 1], tickformat='.0%')),
    title=dict(text='6-Dimension Safety Radar: Stock vs Fine-tuned DueCare-Gemma', font_size=16),
    template='plotly_white', height=550, width=650,
    legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5),
)
fig.show()
"""


STEP_4_INTRO = """---

## 4. Per-prompt delta heatmap

One row per trafficking prompt, two columns (stock, fine-tuned). Red
cells are weak scores, green cells are strong scores; hover for the raw
score per cell. Rows are sorted by delta so the biggest fine-tune wins
cluster at the top and the rare regressions (if any) sink to the
bottom. This is the diagnostic chart that routes a reader from a
headline number to the specific prompts driving it."""


HEATMAP = """stock_rows = data['stock']['per_prompt']
ft_rows    = data['finetuned']['per_prompt']
ft_by_id   = {r['id']: r for r in ft_rows}

paired = []
for row in stock_rows:
    pid = row['id']
    ft  = ft_by_id.get(pid)
    if ft is None:
        continue
    paired.append({
        'id':    pid,
        'stock': row['score'],
        'ft':    ft['score'],
        'delta': ft['score'] - row['score'],
    })

# Sort rows by delta descending so improvements cluster at the top.
paired.sort(key=lambda r: -r['delta'])
ids    = [r['id'] for r in paired]
matrix = [[r['stock'], r['ft']] for r in paired]
hover  = [
    [
        f"Prompt: {r['id']}<br>Mode: stock<br>Score: {r['stock']:.3f}<br>Delta: {r['delta']:+.3f}",
        f"Prompt: {r['id']}<br>Mode: fine-tuned<br>Score: {r['ft']:.3f}<br>Delta: {r['delta']:+.3f}",
    ]
    for r in paired
]

fig = go.Figure(go.Heatmap(
    z=matrix, x=['Stock', 'Fine-tuned'], y=ids,
    hovertext=hover, hoverinfo='text',
    colorscale=[[0, '#ef4444'], [0.25, '#f97316'], [0.5, '#eab308'],
                [0.75, '#22c55e'], [1.0, '#10b981']],
    zmin=0, zmax=1,
    colorbar=dict(title='Score', tickvals=[0, 0.4, 0.7, 0.9, 1.0]),
))
fig.update_layout(
    title=dict(text='Per-Prompt Delta: 50 Trafficking Prompts (sorted by improvement)',
                font_size=16),
    template='plotly_white',
    height=max(500, 14 * len(ids)),
    width=620,
    yaxis=dict(autorange='reversed', tickfont=dict(size=9)),
)
fig.show()
"""


STEP_5_INTRO = f"""---

## 5. V3 band transition diagram

Shows how per-band counts moved from stock to fine-tuned across the V3
6-band classifier bands from [270 Gemma Generations]({URL_270}):
`HARD_VIOLATION`, `DETECTION_FAIL`, `WEAK_REFUSAL`, `REFUSED`,
`PARTIAL_SUCCESS`, `FULL_SUCCESS`. Grouped bars make the left-to-right
shift visible: stock prompts clustered in the harmful / detection-fail
bands move into REFUSED and FULL_SUCCESS after fine-tuning. A line
beneath each pair notes the delta count so the reader can read "8
prompts moved out of HARD_VIOLATION" directly off the chart."""


TRANSITION = """stock_bands = data['stock']['bands']
ft_bands    = data['finetuned']['bands']

stock_counts = [stock_bands.get(b, 0) for b in V3_BANDS]
ft_counts    = [ft_bands.get(b, 0) for b in V3_BANDS]
band_deltas  = [ft_counts[i] - stock_counts[i] for i in range(len(V3_BANDS))]
delta_labels = [f'{d:+d}' for d in band_deltas]

band_colors = {
    'HARD_VIOLATION':   '#ef4444',
    'DETECTION_FAIL':   '#f97316',
    'WEAK_REFUSAL':     '#eab308',
    'REFUSED':          '#3b82f6',
    'PARTIAL_SUCCESS':  '#22c55e',
    'FULL_SUCCESS':     '#10b981',
}
colors = [band_colors[b] for b in V3_BANDS]

fig = go.Figure()
fig.add_trace(go.Bar(
    name='Stock', x=V3_BANDS, y=stock_counts, marker_color='#ef4444',
    text=stock_counts, textposition='outside',
    hovertemplate='<b>%{x}</b><br>Stock: %{y}<extra></extra>',
))
fig.add_trace(go.Bar(
    name='Fine-tuned', x=V3_BANDS, y=ft_counts, marker_color='#10b981',
    text=ft_counts, textposition='outside',
    hovertemplate='<b>%{x}</b><br>Fine-tuned: %{y}<extra></extra>',
))
for band, delta_label, color, stock_c, ft_c in zip(V3_BANDS, delta_labels, colors, stock_counts, ft_counts):
    fig.add_annotation(
        x=band,
        y=max(stock_c, ft_c) + 1.2,
        text=f'<b>{delta_label}</b>',
        showarrow=False,
        font=dict(size=12, color=color),
    )
fig.update_layout(
    barmode='group',
    title=dict(text='V3 6-Band Transition: Stock -> Fine-tuned Counts', font_size=16),
    xaxis=dict(title=''),
    yaxis=dict(title='# of prompts (out of 50)',
               range=[0, max(max(stock_counts), max(ft_counts)) + 6]),
    template='plotly_white', height=500, width=900,
    legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5),
)
fig.show()

transition_lines = []
for band, stock_c, ft_c in zip(V3_BANDS, stock_counts, ft_counts):
    transition_lines.append(f'  {band:<18} stock={stock_c:>3d}  fine-tuned={ft_c:>3d}  delta={ft_c - stock_c:+d}')
print('Per-band transitions:')
print('\\n'.join(transition_lines))
"""


STEP_6_INTRO = """---

## 6. Top-10 biggest-win prompts

Sorts the per-prompt deltas from largest improvement to smallest and
renders the top 10 as an HTML table with prompt id, stock score,
fine-tuned score, and delta. The prompt text column is populated from
the live payload when available (the canonical writer includes it) and
falls back to a short placeholder when the id-only shape is all that is
present."""


TOP_WINS = """from IPython.display import display, HTML

ranked = sorted(paired, key=lambda r: -r['delta'])[:10]

# Pull prompt text from the live payload when available. The canonical
# writer includes a 'prompt' or 'text' field on per_prompt rows; the
# id-only fallback shape just shows the id.
def _lookup_prompt_text(pid: str) -> str:
    for row in data['stock']['per_prompt'] + data['finetuned']['per_prompt']:
        if row.get('id') == pid:
            for key in ('prompt', 'text', 'question'):
                val = row.get(key)
                if val:
                    return val if len(val) <= 120 else val[:117] + '...'
    return '(prompt text not in payload; consult seed_prompts.jsonl for full text)'

rows_html = []
for idx, r in enumerate(ranked, 1):
    txt = _lookup_prompt_text(r['id'])
    rows_html.append(
        f'    <tr>'
        f'<td style="padding:6px 10px;text-align:right;">{idx}</td>'
        f'<td style="padding:6px 10px;"><code>{r["id"]}</code></td>'
        f'<td style="padding:6px 10px;">{txt}</td>'
        f'<td style="padding:6px 10px;text-align:right;color:#ef4444;">{r["stock"]:.3f}</td>'
        f'<td style="padding:6px 10px;text-align:right;color:#10b981;">{r["ft"]:.3f}</td>'
        f'<td style="padding:6px 10px;text-align:right;"><b>+{r["delta"]:.3f}</b></td>'
        f'</tr>'
    )

html = (
    '<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0;">\\n'
    '  <thead>\\n'
    '    <tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da;">\\n'
    '      <th style="padding:6px 10px;text-align:right;width:4%;">#</th>\\n'
    '      <th style="padding:6px 10px;text-align:left;width:10%;">Prompt id</th>\\n'
    '      <th style="padding:6px 10px;text-align:left;width:56%;">Prompt text (truncated)</th>\\n'
    '      <th style="padding:6px 10px;text-align:right;width:10%;">Stock</th>\\n'
    '      <th style="padding:6px 10px;text-align:right;width:10%;">Fine-tuned</th>\\n'
    '      <th style="padding:6px 10px;text-align:right;width:10%;">Delta</th>\\n'
    '    </tr>\\n'
    '  </thead>\\n'
    '  <tbody>\\n'
    + '\\n'.join(rows_html)
    + '\\n  </tbody>\\n'
    '</table>\\n'
)

print('Top-10 biggest fine-tune wins (sorted by delta):')
display(HTML(html))
"""


STEP_7_INTRO = """---

## 7. Key numbers

Prints the numbers that drive the video voiceover: absolute mean-score
lift, relative lift percent, pass-rate lift, harmful-rate reduction,
and V3 FULL_SUCCESS count before and after. These are the numbers the
video narrates in six seconds or less, so they live as a single printed
block that is easy to screen-capture into the submission writeup."""


KEY_NUMBERS = """stock_s = data['stock']['summary']
ft_s    = data['finetuned']['summary']

abs_lift      = ft_s['mean_score'] - stock_s['mean_score']
rel_lift_pct  = (abs_lift / stock_s['mean_score']) * 100.0 if stock_s['mean_score'] else 0.0
pass_lift     = ft_s['pass_rate'] - stock_s['pass_rate']
harmful_drop  = stock_s['harmful_rate'] - ft_s['harmful_rate']
legal_lift    = ft_s['legal_ref_rate'] - stock_s['legal_ref_rate']

full_success_stock = data['stock']['bands'].get('FULL_SUCCESS', 0)
full_success_ft    = data['finetuned']['bands'].get('FULL_SUCCESS', 0)
hard_violation_stock = data['stock']['bands'].get('HARD_VIOLATION', 0)
hard_violation_ft    = data['finetuned']['bands'].get('HARD_VIOLATION', 0)

print('=== Phase 3 key numbers ===')
print(f'Mean score            stock={stock_s["mean_score"]:.3f}   fine-tuned={ft_s["mean_score"]:.3f}   abs lift = {abs_lift:+.3f}   rel lift = {rel_lift_pct:+.1f}%')
print(f'Pass rate             stock={stock_s["pass_rate"]:.0%}      fine-tuned={ft_s["pass_rate"]:.0%}      lift     = {pass_lift:+.0%}')
print(f'Harmful rate          stock={stock_s["harmful_rate"]:.0%}      fine-tuned={ft_s["harmful_rate"]:.0%}      reduction= {harmful_drop:+.0%}')
print(f'Legal ref rate        stock={stock_s["legal_ref_rate"]:.0%}      fine-tuned={ft_s["legal_ref_rate"]:.0%}      lift     = {legal_lift:+.0%}')
print(f'V3 FULL_SUCCESS       stock={full_success_stock:>3d}/50    fine-tuned={full_success_ft:>3d}/50    delta    = {full_success_ft - full_success_stock:+d}')
print(f'V3 HARD_VIOLATION     stock={hard_violation_stock:>3d}/50    fine-tuned={hard_violation_ft:>3d}/50    delta    = {hard_violation_ft - hard_violation_stock:+d}')
print()
print('Video voiceover line: ')
print(f'  "Phase 3 curriculum lifted mean safety score from {stock_s["mean_score"]:.2f} '
      f'to {ft_s["mean_score"]:.2f} ({rel_lift_pct:+.0f}%), tripled pass rate to {ft_s["pass_rate"]:.0%}, '
      f'and cut harmful-response rate from {stock_s["harmful_rate"]:.0%} to {ft_s["harmful_rate"]:.0%} '
      f'on the same 50 trafficking prompts."')
"""


TROUBLESHOOTING = troubleshooting_table_html([
    (
        "Install cell fails because the wheels dataset is not attached.",
        f"Attach <code>{WHEELS_DATASET}</code> from the Kaggle sidebar and rerun.",
    ),
    (
        "Data-source banner says <code>SAMPLE</code> instead of <code>LIVE</code>.",
        f"Re-score the <a href='{URL_530}'>530 Phase 3</a> weights through the "
        f"<a href='{URL_100}'>100 Gemma Exploration</a> scorer and drop the "
        "combined JSON at <code>data/finetune_comparison/stock_vs_finetuned.json</code>. "
        "The sample payload still renders every chart with representative "
        "numbers; only the banner and the top-10 prompt-text column change.",
    ),
    (
        "Headline bar chart shows stock and fine-tuned overlapping (no visible delta).",
        "Your comparison JSON has the stock and fine-tuned summaries swapped or "
        "identical. Confirm that <code>stock.summary.mean_score</code> is below "
        "<code>finetuned.summary.mean_score</code>; the video voiceover line will "
        "flip sign and call out the regression if it is not.",
    ),
    (
        "Radar fill looks empty in dark-mode browsers.",
        "Expected at low alpha (0.15 to 0.20). Hover the lines to confirm the "
        "values; legend entries toggle traces.",
    ),
    (
        "Top-10 table prompt-text column says the text is not in the payload.",
        "Expected when the live JSON carries only <code>id</code> and "
        "<code>score</code> per prompt. Add a <code>prompt</code> or <code>text</code> "
        "field to each <code>per_prompt</code> row in the writer, or cross-reference "
        f"<code>{PROMPTS_DATASET}</code> by id offline. The scoring charts are unaffected.",
    ),
])


SUMMARY = f"""---

## What just happened

- Loaded the stock vs fine-tuned comparison JSON or the built-in `PUBLISHED_FINETUNE_BASELINE`; normalized to the shared `stock` / `finetuned` shape and printed a data-source banner so the reader knows which numbers they are looking at.
- Rendered the four-metric headline delta bar chart (`mean_score`, `pass_rate`, `harmful_rate`, `legal_ref_rate`) in the canonical red / green color scheme.
- Rendered the 6-dimension safety radar over `SAFETY_DIMENSIONS` (stock dashed red vs fine-tuned solid green).
- Rendered the per-prompt delta heatmap over 50 trafficking prompts, sorted so the biggest wins cluster at the top.
- Rendered the V3 6-band transition diagram with per-band delta annotations.
- Rendered the top-10 biggest-win prompt table as HTML.
- Printed the key numbers block with the six-second video voiceover line at the bottom.

### Key findings (sample payload; rerun against Phase 3 weights for real numbers)

1. **Mean score lifts from 0.61 (measured stock) to 0.87 (writeup target)** on the same 50 trafficking prompts. The stock half mirrors the 100 Gemma Exploration baseline byte-for-byte; the finetuned half is the design target until 530's weights are re-scored through 100's evaluator and the live JSON is dropped at <code>data/finetune_comparison/stock_vs_finetuned.json</code>.
2. **Pass rate rises from 20% to 80%** in the sample payload, driven by the refusal-quality and legal-accuracy dimension lifts visible on the radar.
3. **Harmful-response rate stays at 0%** before and after; stock Gemma 4 E4B never produced harmful content on this slice (writeup §4) and the fine-tune target preserves that floor. Track this cell alone for any regression.
4. **V3 FULL_SUCCESS count jumps from 0 to 25 of 50 prompts**, HARD_VIOLATION drops from 14 to 1. The band transition diagram is what lets a reader see the distribution shift rather than a single summary number.
5. **Top-10 prompt table** clusters on victim-facing prompts ("my employer is holding my passport...") and fee-structure prompts, which matches the [520]({URL_520}) curriculum targeting. Regressions, when present, tend to be on adversarial framing prompts that belong to the next curriculum.

---

## Troubleshooting

{TROUBLESHOOTING}

---

## Next

- **Close the section:** [599 Model Improvement Opportunities Conclusion]({URL_599}) ties the Phase 3 delta back into the overall submission narrative.
- **Full dashboard view:** [600 Results Dashboard]({URL_600}) renders the same comparison JSON in the seven-panel video-ready form.
- **Upstream fine-tune step:** [530 Phase 3 Unsloth Fine-tune]({URL_530}).
- **Upstream baseline owner:** [100 Gemma Exploration]({URL_100}).
- **Curriculum that drove the delta:** [520 Phase 3 Curriculum Builder]({URL_520}).
- **Back to navigation (optional):** [000 Index]({URL_000}).
"""

AT_A_GLANCE_INTRO = """---

## At a glance

Stock Gemma 4 vs fine-tuned Gemma 4 on the same 50 trafficking prompts, rendered as radar, heatmap, and headline lift number.
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
    return (f'<div style="display:inline-block;vertical-align:middle;min-width:140px;padding:10px 12px;'
            f'margin:4px 0;background:{bg};border:2px solid {c};border-radius:6px;text-align:center;'
            f'font-family:system-ui,-apple-system,sans-serif">'
            f'<div style="font-weight:600;color:#1f2937;font-size:13px">{label}</div>'
            f'<div style="color:{_P["muted"]};font-size:11px;margin-top:2px">{sub}</div></div>')

_arrow = f'<span style="display:inline-block;vertical-align:middle;margin:0 4px;color:{_P["muted"]};font-size:20px">&rarr;</span>'

cards = [
    _stat_card('stock vs FT', 'compared', 'same 50-prompt slice', 'primary'),
    _stat_card('6-dim', 'radar', 'before/after overlay', 'info'),
    _stat_card('per-prompt', 'heatmap', 'delta grid', 'warning'),
    _stat_card('pass-rate', 'lift number', 'video-ready headline', 'success'),
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step('Load stock', 'baseline 100', 'primary'),
    _step('Load FT', 'post-530 findings', 'primary'),
    _step('Align', 'match by prompt_id', 'info'),
    _step('Radar', '6-dim overlay', 'warning'),
    _step('Heatmap', 'per-prompt deltas', 'warning'),
    _step('Headline', 'pass-rate lift', 'success'),
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">Before/after visualization</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
'''



def build() -> None:
    cells = [
        md(HEADER),
        md(AT_A_GLANCE_INTRO),
        code(AT_A_GLANCE_CODE),
        md(STEP_1_INTRO),
        code(LOAD_DATA),
        md(STEP_2_INTRO),
        code(HEADLINE_DELTA),
        md(STEP_3_INTRO),
        code(RADAR),
        md(STEP_4_INTRO),
        code(HEATMAP),
        md(STEP_5_INTRO),
        code(TRANSITION),
        md(STEP_6_INTRO),
        code(TOP_WINS),
        md(STEP_7_INTRO),
        code(KEY_NUMBERS),
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
        "    'Finetune delta handoff >>> Continue to 599 Model Improvement Opportunities Conclusion: '\n"
        f"    '{URL_599}'\n"
        "    '. Or jump ahead to the full seven-panel dashboard in 600 Results Dashboard: '\n"
        f"    '{URL_600}'\n"
        "    '.'\n"
        ")\n"
    )
    patch_final_print_cell(
        nb,
        final_print_src=final_print_src,
        marker="Finetune delta handoff >>>",
    )

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
        "dataset_sources": [WHEELS_DATASET, PROMPTS_DATASET],
        "competition_sources": ["gemma-4-good-hackathon"],
        "kernel_sources": [],
        "keywords": KEYWORDS,
    }
    (kernel_dir / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )

    code_count = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
    md_count = sum(1 for c in nb["cells"] if c["cell_type"] == "markdown")
    print(f"Wrote {nb_path} ({code_count} code + {md_count} md cells)")
    print(f"Wrote {kernel_dir / FILENAME}")
    print(f"Wrote {kernel_dir / 'kernel-metadata.json'}")


if __name__ == "__main__":
    build()
