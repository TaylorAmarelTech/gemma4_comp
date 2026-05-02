"""Insert an at-a-glance cell (4 stat cards + pipeline diagram) into a build
script. Surgical and reusable: takes the build script path, finds the ``cells
= [`` block, inserts md+code cells immediately after ``md(HEADER)``, and
appends AT_A_GLANCE_INTRO / AT_A_GLANCE_CODE constants above the ``def build``
line. Idempotent: if AT_A_GLANCE_INTRO is already defined, skips.
"""
from __future__ import annotations
import pathlib
import re

STAT_HELPERS_TEMPLATE = '''from IPython.display import HTML, display

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
'''


def inject(script_path: str, *, cards: list[tuple[str, str, str, str]], steps: list[tuple[str, str, str]], pipeline_title: str, intro_heading: str = "## At a glance", intro_body: str = ""):
    """
    cards: list of (value, label, sub, kind)
    steps: list of (label, sub, kind)
    """
    p = pathlib.Path(script_path)
    text = p.read_text(encoding='utf-8')

    if 'AT_A_GLANCE_INTRO' in text:
        return f'SKIP (already has AT_A_GLANCE): {script_path}'

    # Build the cell sources.
    card_lines = [f'    _stat_card({v!r}, {l!r}, {s!r}, {k!r}),' for v, l, s, k in cards]
    step_lines = [f'    _step({l!r}, {s!r}, {k!r}),' for l, s, k in steps]

    intro_str = f'''AT_A_GLANCE_INTRO = """---

{intro_heading}

{intro_body}
"""

AT_A_GLANCE_CODE = \'\'\'{STAT_HELPERS_TEMPLATE}
cards = [
{chr(10).join(card_lines)}
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
{chr(10).join(step_lines)}
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">{pipeline_title}</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
\'\'\'


'''

    # Insert before `def build`
    new_text = re.sub(
        r'(\ndef build\(\))',
        intro_str + r'\1',
        text,
        count=1,
    )

    # Insert cells after md(HEADER), in the cells list. Handle both
    # "md(HEADER)," and "_md(HEADER)," patterns.
    new_text2, n = re.subn(
        r'(_?md\(HEADER\),)',
        r"\1\n        _?md(AT_A_GLANCE_INTRO),\n        _?code(AT_A_GLANCE_CODE),",
        new_text,
        count=1,
    )
    # Replace _?md / _?code with the real prefix used in the file
    if '_md(HEADER)' in text:
        new_text2 = new_text2.replace('_?md(', '_md(').replace('_?code(', '_code(')
    else:
        new_text2 = new_text2.replace('_?md(', 'md(').replace('_?code(', 'code(')

    if n == 0:
        return f'FAILED: could not find md(HEADER) in {script_path}'

    p.write_text(new_text2, encoding='utf-8')
    return f'OK: injected AT_A_GLANCE into {script_path}'


if __name__ == '__main__':
    # 210 OSS Model Comparison
    print(inject(
        'scripts/build_notebook_210_oss_model_comparison.py',
        cards=[
            ('4',        'models compared',  'Gemma E4B vs Llama / Mistral / E2B', 'primary'),
            ('6-dim',    'rubric',           'same scoring as 100',                 'info'),
            ('50',       'shared prompts',   'trafficking slice from 100',          'warning'),
            ('< 1 min',  'runtime',          'CPU kernel, no model load',           'success'),
        ],
        steps=[
            ('Load 100', 'findings.json',     'primary'),
            ('Peer scores','published slice', 'primary'),
            ('Normalize', 'common rubric',    'info'),
            ('Chart',     'per-dim bars',     'warning'),
            ('Radar',     '6-dim overlay',    'warning'),
            ('Gap table', 'stock vs peer',    'success'),
        ],
        pipeline_title='Cross-model comparison pipeline',
        intro_body='4 models on the same 50-prompt trafficking slice, scored with the 6-dimension rubric from 100. No model loading, CPU kernel only.',
    ))

    # 335 Attack Vector Inspector
    print(inject(
        'scripts/build_notebook_335_attack_vector_inspector.py',
        cards=[
            ('15',   'attack vectors',   'adversarial taxonomy',      'danger'),
            ('4',    'severity bands',   'worst -> best mitigated',   'warning'),
            ('300',  'upstream run',     'scored attacks from 300',   'info'),
            ('0',    'model loads',      'CPU-only visualization',    'success'),
        ],
        steps=[
            ('Load 300',    'findings.json',   'primary'),
            ('Taxonomy',    'pie by vector',   'info'),
            ('Severity',    'per-vector bars', 'warning'),
            ('Mitigation',  'status table',    'success'),
        ],
        pipeline_title='15-vector visualization',
        intro_body='Visualizes the 15 adversarial attack vectors from 300 by taxonomy, per-vector severity, and mitigation status.',
    ))

    # 460 Citation Verifier
    print(inject(
        'scripts/build_notebook_460_citation_verifier.py',
        cards=[
            ('40+',  'legal refs',      'ILO / TVPA / RA / Palermo',    'primary'),
            ('2',    'verification passes', 'regex + semantic',         'info'),
            ('6-dim','rubric signal',   'hallucination flag injected',  'warning'),
            ('< 2 min','runtime',       'CPU kernel',                    'success'),
        ],
        steps=[
            ('Load 100',   'responses',            'primary'),
            ('Extract',    'citation strings',     'primary'),
            ('Canon match','regex ILO / RA',       'info'),
            ('Semantic',   'embedding lookup',     'info'),
            ('Flag',       'hallucinated refs',    'warning'),
            ('Chart',      'real vs fake',         'success'),
        ],
        pipeline_title='Citation verification pipeline',
        intro_body='Every legal reference in a Gemma 4 response gets checked against a canonical statute corpus. Hallucinations are flagged.',
    ))

    # 540 Fine-tune Delta Visualizer
    print(inject(
        'scripts/build_notebook_540_finetune_delta_visualizer.py',
        cards=[
            ('stock vs FT','compared',       'same 50-prompt slice',       'primary'),
            ('6-dim',      'radar',          'before/after overlay',       'info'),
            ('per-prompt', 'heatmap',        'delta grid',                 'warning'),
            ('pass-rate',  'lift number',    'video-ready headline',       'success'),
        ],
        steps=[
            ('Load stock',  'baseline 100',         'primary'),
            ('Load FT',     'post-530 findings',    'primary'),
            ('Align',       'match by prompt_id',   'info'),
            ('Radar',       '6-dim overlay',        'warning'),
            ('Heatmap',     'per-prompt deltas',    'warning'),
            ('Headline',    'pass-rate lift',       'success'),
        ],
        pipeline_title='Before/after visualization',
        intro_body='Stock Gemma 4 vs fine-tuned Gemma 4 on the same 50 trafficking prompts, rendered as radar, heatmap, and headline lift number.',
    ))

    # 220 Ollama Cloud Comparison
    print(inject(
        'scripts/build_notebook_220_ollama_cloud_comparison.py',
        cards=[
            ('8',   'models compared',     'Gemma vs 7 OSS via Ollama Cloud', 'primary'),
            ('6-dim', 'rubric',            'same scoring as 100',              'info'),
            ('cloud','inference backend',  'no local GPU needed',              'warning'),
            ('< 3 min','runtime',          'CPU kernel with API key',          'success'),
        ],
        steps=[
            ('Load 100',       'stock baseline',   'primary'),
            ('Call Ollama',    '7 peer models',    'info'),
            ('Score responses','6-dim rubric',     'warning'),
            ('Rank',           'per-dim winner',   'success'),
        ],
        pipeline_title='Cloud-peer comparison',
        intro_body='Gemma 4 E4B vs 7 open-source peers hosted on Ollama Cloud, scored with the same 6-dimension rubric.',
    ))

    # 105 Prompt Corpus Introduction
    print(inject(
        'scripts/build_notebook_105_prompt_corpus_introduction.py',
        cards=[
            ('74,567',  'total prompts',    'trafficking domain pack',       'primary'),
            ('204',     'graded',           '5 reference responses each',    'success'),
            ('85',      'categories',       'sector / corridor / attack',    'info'),
            ('5-band',  'grade scale',      'worst -> best',                  'warning'),
        ],
        steps=[
            ('Load pack',    'seed_prompts.jsonl',  'primary'),
            ('Stats',        'count by category',    'info'),
            ('Sample',       'one per category',     'info'),
            ('Grade ladder', '5 reference levels',   'warning'),
            ('Hand-off',     'feeds 110 / 120',      'success'),
        ],
        pipeline_title='Corpus tour',
        intro_body='A walk through the 74K prompt trafficking corpus before any selection or scoring.',
    ))

    # 190 RAG Retrieval Inspector
    print(inject(
        'scripts/build_notebook_190_rag_retrieval_inspector.py',
        cards=[
            ('40+',  'legal docs indexed',     'ILO / TVPA / RA / Palermo',      'primary'),
            ('MiniLM','embedding model',       'sentence-transformers',          'info'),
            ('top-5', 'retrieval depth',       'per prompt',                     'warning'),
            ('< 1 min','runtime',              'CPU only, no model load',        'success'),
        ],
        steps=[
            ('Legal corpus', 'statute + NGO docs',   'primary'),
            ('Embed',        'MiniLM vectors',        'info'),
            ('Query',        'prompt embedding',      'info'),
            ('Retrieve',     'top-5 per prompt',      'warning'),
            ('Inspect',      'citations + excerpts',  'success'),
        ],
        pipeline_title='RAG store inspection',
        intro_body='Exactly which legal citations match each prompt, with provenance. This is the RAG store 260 consumes.',
    ))
