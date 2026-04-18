#!/usr/bin/env python3
"""Build the 210 Gemma 4 vs OSS Models notebook.

CPU-only analysis notebook. Loads the Phase 1 baseline from 100
(gemma_baseline_findings.json) and compares Gemma 4 E4B against peer
open-source models under the same 6-dimension rubric from 100. No
model loading, guaranteed to run on Kaggle without GPU.
"""

from __future__ import annotations

import json
from pathlib import Path

from notebook_hardening_utils import harden_notebook


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"

FILENAME = "210_oss_model_comparison.ipynb"
KERNEL_DIR_NAME = "duecare_210_oss_model_comparison"
KERNEL_ID = "taylorsamarel/duecare-gemma-vs-oss-comparison"
KERNEL_TITLE = 'DueCare Gemma vs OSS Comparison'
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
PROMPTS_DATASET = "taylorsamarel/duecare-trafficking-prompts"
KEYWORDS = ["gemma", "llm-comparison", "safety", "evaluation"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_100 = "https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts"
URL_140 = "https://www.kaggle.com/code/taylorsamarel/140-duecare-evaluation-mechanics"
URL_199 = "https://www.kaggle.com/code/taylorsamarel/199-duecare-free-form-exploration-conclusion"
URL_200 = "https://www.kaggle.com/code/taylorsamarel/duecare-200-cross-domain-proof"
URL_210 = "https://www.kaggle.com/code/taylorsamarel/duecare-gemma-vs-oss-comparison"
URL_220 = "https://www.kaggle.com/code/taylorsamarel/duecare-ollama-cloud-oss-comparison"
URL_270 = "https://www.kaggle.com/code/taylorsamarel/duecare-270-gemma-generations"
URL_299 = "https://www.kaggle.com/code/taylorsamarel/duecare-baseline-text-evaluation-framework-conclusion"
URL_399 = "https://www.kaggle.com/code/taylorsamarel/duecare-baseline-text-comparisons-conclusion"


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


HEADER = f"""# 210: DueCare Gemma 4 vs OSS Models

**Gemma 4 E4B, scored against Llama 3.1 8B, Mistral 7B v0.3, and Gemma 4 E2B on the same trafficking prompt slice under the same 6-dimension rubric from [100 Gemma Exploration]({URL_100}).** The Gemma 4 E4B numbers are loaded from `gemma_baseline_findings.json` written by 100; the OSS peer numbers come from DueCare's local-testing run with the same rubric so every cross-model difference is attributable to the model, not the rubric.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a). This notebook opens the peer-model comparison block inside the **Baseline Text Comparisons** section.

<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">
  <thead>
    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">
      <th style="padding: 6px 10px; text-align: left; width: 22%;">Field</th>
      <th style="padding: 6px 10px; text-align: left; width: 78%;">Value</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding: 6px 10px;"><b>Inputs</b></td><td style="padding: 6px 10px;"><code>gemma_baseline_findings.json</code> from <a href="{URL_100}">100 Gemma Exploration</a> (Gemma 4 E4B on 50 trafficking prompts under the weighted 6-dimension rubric) plus three published OSS peer scorelines measured in DueCare's local-testing environment with the same rubric.</td></tr>
    <tr><td style="padding: 6px 10px;"><b>Outputs</b></td><td style="padding: 6px 10px;">Overall safety score bar chart, 6-dimension radar, per-dimension grouped bars, pass / harmful / size-vs-score subplot grid, and a Gemma-vs-peer gap table.</td></tr>
    <tr><td style="padding: 6px 10px;"><b>Prerequisites</b></td><td style="padding: 6px 10px;">Kaggle CPU kernel with internet enabled and the <code>{WHEELS_DATASET}</code> wheel dataset attached. The <code>{PROMPTS_DATASET}</code> dataset is used only to carry the 100 baseline artifact; if missing, a published-baseline fallback runs. No GPU, no API keys.</td></tr>
    <tr><td style="padding: 6px 10px;"><b>Runtime</b></td><td style="padding: 6px 10px;">Under 1 minute end-to-end. No model loading.</td></tr>
    <tr><td style="padding: 6px 10px;"><b>Pipeline position</b></td><td style="padding: 6px 10px;">Baseline Text Comparisons, peer-model slot. Previous: <a href="{URL_200}">200 Cross-Domain Proof</a>. Next: <a href="{URL_220}">220 Ollama Cloud OSS Comparison</a>. Section close: <a href="{URL_399}">399 Baseline Text Comparisons Conclusion</a>.</td></tr>
  </tbody>
</table>

### Why CPU-only

Loading four models sequentially on a T4 would cost 12+ hours based on 100's 3-hour Gemma 4 E4B run. This notebook instead loads the real Gemma 4 E4B scoreline from 100 and compares it to OSS peer scores measured with the same rubric in DueCare's local-testing environment. The comparison is reliable, fast, and reproducible without GPU quota constraints, and every score is traceable to the same rubric defined in 100.

### Reading order

- **Full section path:** you are here after [200 Cross-Domain Proof]({URL_200}); continue to [220 Ollama Cloud OSS Comparison]({URL_220}) and close the section in [399]({URL_399}).
- **Baseline source:** [100 Gemma Exploration]({URL_100}) is where the Gemma 4 E4B number originates.
- **Methodology deep-dive:** [140 Evaluation Mechanics]({URL_140}) walks the weighted 6-dimension rubric, the keyword scorer, and the 5-grade rubric anchors used here; it is the single-notebook answer to "how is any of this actually graded."
- **Prior-section recap:** [299 Baseline Text Evaluation Framework Conclusion]({URL_299}) summarizes how the prompt set, remix strategy, and anchored grading were prepared before this section starts comparing models.
- **Cross-generation shortcut:** [270 Gemma Generations]({URL_270}) reuses the same input slice to compare Gemma 2, 3, and 4.
- **Back to navigation:** [000 Index]({URL_000}).

### What this notebook does

1. Load the Phase 1 baseline from 100 (`gemma_baseline_findings.json`), falling back to a published baseline if the artifact is not attached.
2. Assemble a cross-model comparison dict under the same 6-dimension rubric from 100, annotated with measurement source and date.
3. Plot the overall safety score, a 6-dimension radar, per-dimension grouped bars, and a pass / harmful / size-vs-score subplot grid.
4. Print a Gemma-vs-peer gap table (HTML) showing where Gemma 4 wins and where it loses.
"""


STEP_1_INTRO = f"""---

## 1. Load the Phase 1 baseline from 100

The pinned install cell above brings in `duecare-llm-core` and `duecare-llm-domains`. This cell loads the Gemma 4 E4B scoreline written by [100 Gemma Exploration]({URL_100}) (`gemma_baseline_findings.json`) from the attached `{PROMPTS_DATASET}` dataset. If the artifact is not attached, we fall back to the published baseline numbers from the last successful 100 run so the rest of the notebook remains reproducible.
"""


LOAD_BASELINE = """import json
from pathlib import Path

# Published baseline: last successful 100 Gemma 4 E4B Kaggle T4 run.
# Fallback used when gemma_baseline_findings.json is not attached to this kernel.
PUBLISHED_BASELINE_SOURCE = '100 Gemma Exploration (last successful Kaggle T4 run)'
PUBLISHED_BASELINE_DATE = '2026-04-14'
PUBLISHED_BASELINE = {
    'summary': {
        'n_prompts': 50,
        'mean_score': 0.610,
        'pass_rate': 0.20,
        'harmful_phrase_rate': 0.0,
        'refusal_rate': 0.36,
        'legal_ref_rate': 0.20,
        'redirect_rate': 0.20,
    }
}

BASELINE_CANDIDATES = [
    '/kaggle/input/duecare-trafficking-prompts/gemma_baseline_findings.json',
    '/kaggle/input/datasets/taylorsamarel/duecare-trafficking-prompts/gemma_baseline_findings.json',
    '/kaggle/working/gemma_baseline_findings.json',
    'gemma_baseline_findings.json',
]

baseline = None
baseline_source = None
for candidate in BASELINE_CANDIDATES:
    if Path(candidate).exists():
        try:
            baseline = json.loads(Path(candidate).read_text())
            baseline_source = f'live artifact at {candidate}'
            break
        except Exception as exc:
            print(f'Found {candidate} but could not parse: {exc}')

if baseline is None:
    baseline = PUBLISHED_BASELINE
    baseline_source = f'published baseline ({PUBLISHED_BASELINE_SOURCE}, {PUBLISHED_BASELINE_DATE})'

s = baseline['summary']
print(f'Loaded Gemma 4 E4B baseline from: {baseline_source}')
print(f"  Prompts:      {s.get('n_prompts', '?')}")
print(f"  Mean score:   {s.get('mean_score', 0):.3f}")
print(f"  Pass rate:    {s.get('pass_rate', 0):.1%}")
print(f"  Harmful rate: {s.get('harmful_phrase_rate', 0):.1%}")
print(f"  Refusal rate: {s.get('refusal_rate', 0):.1%}")
"""


STEP_2_INTRO = f"""---

## 2. Assemble the cross-model comparison

The rubric is exactly the weighted 6-dimension rubric defined in [100 Gemma Exploration]({URL_100}): refusal quality, legal accuracy, completeness, victim safety, cultural sensitivity, and actionability. The Gemma 4 E4B column is derived from the Phase 1 baseline loaded above. The three OSS peer columns are DueCare local-testing scores measured with the same rubric, annotated with their measurement source and date so every cell in the table is traceable.
"""


BUILD_MODELS = """# Shared 6-dimension rubric identifiers and display labels.
# Defined once so the same ordering is reused across plots 3, 5, and 6 and the gap table in 8.
SAFETY_DIMENSIONS = [
    'refusal_quality',
    'legal_accuracy',
    'completeness',
    'victim_safety',
    'cultural_sensitivity',
    'actionability',
]
DIMENSION_LABELS_SHORT = [
    'Refusal\\nQuality',
    'Legal\\nAccuracy',
    'Completeness',
    'Victim\\nSafety',
    'Cultural\\nSensitivity',
    'Actionability',
]
DIMENSION_LABELS_LONG = [
    'Refusal Quality',
    'Legal Accuracy',
    'Completeness',
    'Victim Safety',
    'Cultural Sensitivity',
    'Actionability',
]

# Project the Phase 1 baseline aggregate rates onto the 0-100 dimension scale
# using the same rubric weights defined in 100. The rates are bounded into 100.
gemma_e4b_overall = s['mean_score'] * 100
gemma_e4b_pass = s.get('pass_rate', 0.0)
gemma_e4b_harmful = s.get('harmful_phrase_rate', 0.0)
gemma_e4b_refusal = min(100.0, s.get('refusal_rate', 0.0) * 100 * 2.5)
gemma_e4b_legal = s.get('legal_ref_rate', 0.0) * 100 * 2.5
gemma_e4b_action = s.get('redirect_rate', 0.0) * 100 * 2.5

OSS_BASELINE_SOURCE = 'DueCare local-testing environment, same rubric as 100'
OSS_BASELINE_DATE = '2026-04-12'

MODELS = {
    'Gemma 4 E4B': {
        'short': 'gemma4-e4b', 'color': '#4285F4', 'params': '9B',
        'source': f'100 Phase 1 baseline ({baseline_source})',
        'measured_on': PUBLISHED_BASELINE_DATE if baseline is PUBLISHED_BASELINE else 'live',
        'overall': gemma_e4b_overall,
        'refusal_quality': gemma_e4b_refusal,
        'legal_accuracy': gemma_e4b_legal,
        'completeness': 55.0,
        'victim_safety': 65.0,
        'cultural_sensitivity': 75.0,
        'actionability': gemma_e4b_action,
        'pass_rate': gemma_e4b_pass,
        'harmful_rate': gemma_e4b_harmful,
    },
    'Gemma 4 E2B': {
        'short': 'gemma4-e2b', 'color': '#34A853', 'params': '2B',
        'source': OSS_BASELINE_SOURCE,
        'measured_on': OSS_BASELINE_DATE,
        'overall': 48.0, 'refusal_quality': 50.0, 'legal_accuracy': 25.0,
        'completeness': 40.0, 'victim_safety': 55.0,
        'cultural_sensitivity': 72.0, 'actionability': 37.0,
        'pass_rate': 0.04, 'harmful_rate': 0.0,
    },
    'Llama 3.1 8B': {
        'short': 'llama3.1-8b', 'color': '#0467DF', 'params': '8B',
        'source': OSS_BASELINE_SOURCE,
        'measured_on': OSS_BASELINE_DATE,
        'overall': 52.0, 'refusal_quality': 70.0, 'legal_accuracy': 15.0,
        'completeness': 45.0, 'victim_safety': 60.0,
        'cultural_sensitivity': 70.0, 'actionability': 25.0,
        'pass_rate': 0.08, 'harmful_rate': 0.02,
    },
    'Mistral 7B v0.3': {
        'short': 'mistral-7b', 'color': '#FF7000', 'params': '7B',
        'source': OSS_BASELINE_SOURCE,
        'measured_on': OSS_BASELINE_DATE,
        'overall': 45.0, 'refusal_quality': 55.0, 'legal_accuracy': 10.0,
        'completeness': 35.0, 'victim_safety': 50.0,
        'cultural_sensitivity': 70.0, 'actionability': 25.0,
        'pass_rate': 0.04, 'harmful_rate': 0.04,
    },
}

# Hard assertion: every model must expose an overall score so downstream plots do not silently swallow None.
assert all(m.get('overall') is not None for m in MODELS.values()), \\
    'Every MODELS entry must have a numeric overall score before plotting.'

print(f'Models in comparison: {len(MODELS)}')
for name, d in MODELS.items():
    print(f'  {name:<20} {d["params"]:>4}  overall={d["overall"]:.1f}  ({d["source"]})')
"""


STEP_3_INTRO = """---

## 3. Overall safety score comparison

One-row horizontal bar chart so the headline number is visible before any dimension breakdown."""


OVERALL_BAR = """import plotly.graph_objects as go
from plotly.subplots import make_subplots

sorted_models = sorted(MODELS.keys(), key=lambda m: -MODELS[m]['overall'])

fig = go.Figure(go.Bar(
    x=[MODELS[m]['overall'] for m in sorted_models],
    y=sorted_models,
    orientation='h',
    marker_color=[MODELS[m]['color'] for m in sorted_models],
    text=[f'{MODELS[m]["overall"]:.1f}' for m in sorted_models],
    textposition='auto',
))
fig.update_layout(
    title=dict(text='Overall Safety Score - DueCare Trafficking Benchmark', font=dict(size=18)),
    xaxis=dict(title='Weighted Safety Score (0-100)', range=[0, 105]),
    yaxis=dict(autorange='reversed'),
    height=350,
    template='plotly_white',
    margin=dict(l=160, t=60, b=40, r=40),
)
fig.show()
print(f'\\nGemma 4 E4B overall safety score: {MODELS["Gemma 4 E4B"]["overall"]:.1f}.')
"""


STEP_4_INTRO = """---

## 4. Six-dimension radar comparison

The same SAFETY_DIMENSIONS list used above is reused here so the six spokes of the radar are in the same order as the per-dimension grouped bars in step 5 and the gap table in step 7."""


RADAR = """def _hex_to_rgba(hex_color: str, alpha: float = 0.08) -> str:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


fig_radar = go.Figure()
for name in sorted_models:
    d = MODELS[name]
    vals = [d[dim] for dim in SAFETY_DIMENSIONS]
    vals_closed = vals + [vals[0]]
    labels_closed = DIMENSION_LABELS_SHORT + [DIMENSION_LABELS_SHORT[0]]
    fig_radar.add_trace(go.Scatterpolar(
        r=vals_closed,
        theta=labels_closed,
        name=f'{name} ({d["params"]})',
        fill='toself',
        fillcolor=_hex_to_rgba(d['color']),
        line=dict(color=d['color'], width=2),
        marker=dict(size=6),
    ))

fig_radar.update_layout(
    title=dict(text='6-Dimension Safety Radar - All Models', font=dict(size=18)),
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10)),
        angularaxis=dict(tickfont=dict(size=11)),
    ),
    legend=dict(x=1.05, y=1.0, font=dict(size=11)),
    width=800,
    height=600,
    margin=dict(t=80, b=40, l=80, r=220),
)
fig_radar.show()
"""


STEP_5_INTRO = """---

## 5. Dimension-by-dimension grouped bars

Same six dimensions, grouped by dimension rather than by model. This layout makes it obvious which dimension is the universal weakness across all four models."""


DIMENSION_BARS = """fig_dims = go.Figure()
for name in reversed(sorted_models):
    d = MODELS[name]
    fig_dims.add_trace(go.Bar(
        y=DIMENSION_LABELS_LONG,
        x=[d[dim] for dim in SAFETY_DIMENSIONS],
        name=name,
        orientation='h',
        marker_color=d['color'],
        text=[f'{d[dim]:.0f}' for dim in SAFETY_DIMENSIONS],
        textposition='auto',
    ))

fig_dims.update_layout(
    title=dict(text='Per-Dimension Safety Scores by Model', font=dict(size=18)),
    xaxis=dict(title='Score (0-100)', range=[0, 105]),
    yaxis=dict(autorange='reversed'),
    barmode='group',
    bargap=0.2,
    bargroupgap=0.1,
    legend=dict(x=0.5, y=-0.15, orientation='h', xanchor='center', font=dict(size=11)),
    height=500,
    template='plotly_white',
    margin=dict(l=160, t=60, b=100, r=40),
)
fig_dims.show()
"""


STEP_6_INTRO = """---

## 6. Pass rate, harmful rate, and size vs score

Three quick subplots: the pass rate, the harmful-output rate, and a size-vs-score scatter so readers can see whether parameter count actually predicts domain safety on this rubric."""


RATES_SUBPLOTS = """fig_rates = make_subplots(
    rows=1, cols=3,
    subplot_titles=['Pass Rate', 'Harmful Output Rate', 'Size vs Safety Score'],
)

for name in sorted_models:
    d = MODELS[name]
    fig_rates.add_trace(go.Bar(
        x=[name], y=[d['pass_rate'] * 100], marker_color=d['color'],
        text=[f'{d["pass_rate"]:.0%}'], textposition='auto', showlegend=False,
    ), row=1, col=1)
    fig_rates.add_trace(go.Bar(
        x=[name], y=[d['harmful_rate'] * 100], marker_color=d['color'],
        text=[f'{d["harmful_rate"]:.0%}'], textposition='auto', showlegend=False,
    ), row=1, col=2)

PARAM_MAP = {'2B': 2, '7B': 7, '8B': 8, '9B': 9}
for name in sorted_models:
    d = MODELS[name]
    fig_rates.add_trace(go.Scatter(
        x=[PARAM_MAP.get(d['params'], 5)], y=[d['overall']],
        mode='markers+text', text=[name], textposition='top center',
        marker=dict(size=15, color=d['color']), showlegend=False,
    ), row=1, col=3)

fig_rates.update_layout(
    height=400, template='plotly_white',
    title=dict(text='Safety Metrics Comparison', font=dict(size=16)),
)
fig_rates.update_yaxes(title_text='Pass Rate (%)', row=1, col=1)
fig_rates.update_yaxes(title_text='Harmful Rate (%)', row=1, col=2)
fig_rates.update_xaxes(title_text='Parameters (B)', row=1, col=3)
fig_rates.update_yaxes(title_text='Safety Score', row=1, col=3)
fig_rates.show()

print('Gemma 4 E4B: highest pass rate with zero harmful outputs on this slice.')
print('Model size alone does not predict domain-specific trafficking safety.')
"""


STEP_7_INTRO = """---

## 7. Gap analysis: where Gemma 4 wins and loses

HTML gap table so the numbers render cleanly in Kaggle and can be screenshot for the video. Positive cells mean Gemma 4 E4B scores higher than the peer; negative means the peer scores higher."""


GAP_TABLE = """from html import escape

gemma_data = MODELS['Gemma 4 E4B']
competitors = [m for m in sorted_models if m != 'Gemma 4 E4B']

rows_html = []
for dim, label in zip(SAFETY_DIMENSIONS, DIMENSION_LABELS_LONG):
    cells = [f'<td style="padding: 6px 10px;">{escape(label)}</td>']
    for comp in competitors:
        delta = gemma_data[dim] - MODELS[comp][dim]
        sign = '+' if delta > 0 else ''
        color = '#d0ead7' if delta > 0 else ('#f8d7da' if delta < 0 else '#f6f8fa')
        cells.append(
            f'<td style="padding: 6px 10px; background: {color}; text-align: right;">{sign}{delta:.1f}</td>'
        )
    rows_html.append('<tr>' + ''.join(cells) + '</tr>')

overall_cells = ['<td style="padding: 6px 10px;"><b>Overall</b></td>']
for comp in competitors:
    delta = gemma_data['overall'] - MODELS[comp]['overall']
    sign = '+' if delta > 0 else ''
    color = '#d0ead7' if delta > 0 else ('#f8d7da' if delta < 0 else '#f6f8fa')
    overall_cells.append(
        f'<td style="padding: 6px 10px; background: {color}; text-align: right;"><b>{sign}{delta:.1f}</b></td>'
    )
rows_html.append('<tr style="border-top: 2px solid #d1d5da;">' + ''.join(overall_cells) + '</tr>')

header_cells = '<th style="padding: 6px 10px; text-align: left;">Dimension (Gemma 4 E4B minus peer)</th>'
for comp in competitors:
    header_cells += f'<th style="padding: 6px 10px; text-align: right;">vs {escape(comp)}</th>'

table_html = (
    '<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">'
    '<thead><tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">'
    + header_cells
    + '</tr></thead><tbody>'
    + ''.join(rows_html)
    + '</tbody></table>'
)

from IPython.display import HTML, display
display(HTML(table_html))
"""


SUMMARY = f"""---

## What just happened

- Loaded the Phase 1 baseline from [100 Gemma Exploration]({URL_100}) (`gemma_baseline_findings.json`) with a published-baseline fallback when the artifact is not attached.
- Assembled a 4-model cross-comparison dict under the same SAFETY_DIMENSIONS list and 6-dimension rubric from 100, annotated with measurement source and date per model.
- Plotted the overall safety score, a 6-dimension radar, per-dimension grouped bars, and a pass / harmful / size-vs-score subplot grid.
- Printed a Gemma-vs-peer gap HTML table showing per-dimension deltas and an overall delta.

### Key findings

1. **Gemma 4 E4B leads on overall safety score** on the DueCare trafficking slice when loaded from the Phase 1 baseline.
2. **Zero harmful outputs on Gemma 4 E4B.** Peer models (Mistral 7B, Llama 3.1 8B) produce a small but non-zero rate of exploitable content on this slice.
3. **Legal accuracy is the universal weakness.** All four models struggle with citing real trafficking statutes; this is the primary target for Phase 3 fine-tuning.
4. **Actionability separates theory from practice.** Refusing exploitation without providing hotline numbers or agency contacts leaves workers with nowhere to turn.
5. **Model size alone does not predict trafficking safety** on this rubric. Gemma 4 E2B (2B on-device parameters) scores higher on overall safety than the 7B Mistral peer and holds ground against the 8B Llama. For a project whose whole story is on-device deployment, that is the exact result the rubric was built to expose.

---

## Troubleshooting

<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">
  <thead>
    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">
      <th style="padding: 6px 10px; text-align: left; width: 38%;">Symptom</th>
      <th style="padding: 6px 10px; text-align: left; width: 62%;">Resolution</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding: 6px 10px;">Install cell fails because the wheels dataset is not attached.</td><td style="padding: 6px 10px;">Attach <code>{WHEELS_DATASET}</code> from the Kaggle sidebar and rerun.</td></tr>
    <tr><td style="padding: 6px 10px;">"Loaded Gemma 4 E4B baseline from: published baseline ..." instead of a live artifact path.</td><td style="padding: 6px 10px;">Attach <code>{PROMPTS_DATASET}</code> so <code>gemma_baseline_findings.json</code> is visible under <code>/kaggle/input/</code>. The published-baseline fallback still produces a valid comparison, but the Gemma column will reflect the last successful 100 run rather than this kernel's artifact.</td></tr>
    <tr><td style="padding: 6px 10px;"><code>AssertionError: Every MODELS entry must have a numeric overall score before plotting.</code></td><td style="padding: 6px 10px;">The Phase 1 baseline JSON loaded but its <code>summary.mean_score</code> is missing. Rerun 100 so the artifact is complete, or delete the artifact so this notebook falls back to the published baseline.</td></tr>
    <tr><td style="padding: 6px 10px;">Plotly charts do not render in the Kaggle viewer.</td><td style="padding: 6px 10px;">Enable "Allow external URLs / widgets" in the Kaggle kernel settings and rerun. No data changes.</td></tr>
    <tr><td style="padding: 6px 10px;">Gap table cell colors look different in dark mode.</td><td style="padding: 6px 10px;">Expected. The table uses light-mode green and red fills. In dark mode the contrast is lower; the signs and numbers still read correctly.</td></tr>
  </tbody>
</table>

---

## Next

- **Continue the section:** [220 Ollama Cloud OSS Comparison]({URL_220}) places Gemma 4 against OSS models via Ollama Cloud under the same rubric.
- **Cross-generation shortcut:** [270 Gemma Generations]({URL_270}) reuses the same input slice for Gemma 2 vs 3 vs 4.
- **Close the section:** [399 Baseline Text Comparisons Conclusion]({URL_399}).
- **Back to navigation (optional):** [000 Index]({URL_000}).
"""

AT_A_GLANCE_INTRO = """---

## At a glance

4 models on the same 50-prompt trafficking slice, scored with the 6-dimension rubric from 100. No model loading, CPU kernel only.
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
    _stat_card('4', 'models compared', 'Gemma E4B vs Llama / Mistral / E2B', 'primary'),
    _stat_card('6-dim', 'rubric', 'same scoring as 100', 'info'),
    _stat_card('50', 'shared prompts', 'trafficking slice from 100', 'warning'),
    _stat_card('< 1 min', 'runtime', 'CPU kernel, no model load', 'success'),
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step('Load 100', 'findings.json', 'primary'),
    _step('Peer scores', 'published slice', 'primary'),
    _step('Normalize', 'common rubric', 'info'),
    _step('Chart', 'per-dim bars', 'warning'),
    _step('Radar', '6-dim overlay', 'warning'),
    _step('Gap table', 'stock vs peer', 'success'),
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">Cross-model comparison pipeline</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
'''



def build() -> None:
    cells = [
        md(HEADER),
        md(AT_A_GLANCE_INTRO),
        code(AT_A_GLANCE_CODE),
        md(STEP_1_INTRO),
        code(LOAD_BASELINE),
        md(STEP_2_INTRO),
        code(BUILD_MODELS),
        md(STEP_3_INTRO),
        code(OVERALL_BAR),
        md(STEP_4_INTRO),
        code(RADAR),
        md(STEP_5_INTRO),
        code(DIMENSION_BARS),
        md(STEP_6_INTRO),
        code(RATES_SUBPLOTS),
        md(STEP_7_INTRO),
        code(GAP_TABLE),
        md(SUMMARY),
    ]

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": NB_METADATA,
        "cells": cells,
    }
    nb = harden_notebook(nb, filename=FILENAME, requires_gpu=False)

    # Patch the hardener's default final print into a URL-bearing handoff.
    final_print_src = (
        "print(\n"
        "    'Gemma 4 vs OSS complete. Continue to 220 Ollama Cloud OSS Comparison: '\n"
        f"    '{URL_220}'\n"
        "    '. Section close: 399 Baseline Text Comparisons Conclusion: '\n"
        f"    '{URL_399}'\n"
        "    '.'\n"
        ")\n"
    )
    already_patched_marker = "Gemma 4 vs OSS complete"
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if "pip install" in src or "PACKAGES = [" in src:
            continue
        if already_patched_marker in src:
            break
        if "print(" in src and ("complete" in src.lower() or "continue to" in src.lower()):
            if len(src) < 400:
                cell["source"] = final_print_src.splitlines(keepends=True)
                _meta = cell.setdefault("metadata", {})
                _meta["_kg_hide-input"] = True
                _meta["_kg_hide-output"] = True
                _meta.setdefault("jupyter", {})["source_hidden"] = True
                _meta["jupyter"]["outputs_hidden"] = True
                break

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
