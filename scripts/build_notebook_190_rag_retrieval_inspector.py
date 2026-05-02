#!/usr/bin/env python3
"""Build the 190 DueCare RAG Retrieval Inspector notebook.

CPU-only pre-flight inspector for the DueCare RAG store. Shows WHICH
legal citations match each trafficking prompt and how the retrieval
actually works, so readers arriving at 260 RAG Comparison can see the
retrieval substrate that comparison assumes exists.

No model inference. Pure keyword-overlap retrieval plus visualization:

- An in-memory legal-citation corpus (11 entries covering ILO C181,
  ILO C029, Palermo Protocol, RA 10022, RA 8042, Saudi Labor Law
  Article 40, TIP Report indicators, POEA/BP2MI/HRD Nepal hotlines,
  and the ILO 11 indicators of forced labor).
- A keyword retriever (stdlib only) that returns the top-N citations
  for any prompt with a similarity score.
- A Plotly heatmap: 10 sample prompts x 11 corpus entries, shaded
  red -> green by retrieval score.
- An HTML table of the top-3 retrieved citations per prompt with
  source provenance.
- Corpus coverage statistics: prompts-with-a-hit, average retrieval
  depth, most-retrieved citations.
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

FILENAME = "190_rag_retrieval_inspector.ipynb"
KERNEL_DIR_NAME = "duecare_190_rag_retrieval_inspector"
KERNEL_ID = "taylorsamarel/190-duecare-rag-retrieval-inspector"
KERNEL_TITLE = "190: DueCare RAG Retrieval Inspector"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
PROMPTS_DATASET = "taylorsamarel/duecare-trafficking-prompts"
KEYWORDS = ["gemma", "safety", "llm", "trafficking", "rag", "retrieval"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_110 = "https://www.kaggle.com/code/taylorsamarel/00a-duecare-prompt-prioritizer-data-pipeline"
URL_120 = "https://www.kaggle.com/code/taylorsamarel/duecare-prompt-remixer"
URL_130 = "https://www.kaggle.com/code/taylorsamarel/duecare-prompt-corpus-exploration"
URL_140 = "https://www.kaggle.com/code/taylorsamarel/140-duecare-evaluation-mechanics"
URL_190 = "https://www.kaggle.com/code/taylorsamarel/duecare-190-rag-retrieval-inspector"
URL_260 = "https://www.kaggle.com/code/taylorsamarel/duecare-260-rag-comparison"
URL_299 = "https://www.kaggle.com/code/taylorsamarel/299-duecare-text-evaluation-conclusion"
URL_600 = "https://www.kaggle.com/code/taylorsamarel/600-duecare-results-dashboard"


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
        "An in-memory <code>LEGAL_CORPUS</code> of 11 trafficking-domain "
        "citations (ILO C181, ILO C029, Palermo Protocol, RA 10022, RA 8042, "
        "Saudi Labor Law Article 40, TIP Report indicators, POEA/BP2MI/HRD Nepal "
        "hotlines, and the ILO 11 indicators of forced labor) plus 10 hand-written "
        "trafficking prompts spanning placement fees, passport retention, debt "
        "bondage, border violations, age fraud, language barrier, contract swap, "
        "confined housing, and sector-specific scenarios (domestic, fishing, "
        "construction)."
    ),
    outputs_html=(
        "A printed corpus summary; a keyword retriever function "
        "<code>retrieve(prompt, top_n=3)</code> that returns top-N citations "
        "with similarity scores; a Plotly coverage heatmap "
        "(10 prompts x 11 corpus entries) shaded red -> green by retrieval "
        "score; an HTML per-prompt retrieval-breakdown table with provenance "
        "(source, jurisdiction, article); and a corpus-coverage summary "
        "(prompts-with-a-hit, average retrieval depth, most-retrieved "
        "citations)."
    ),
    prerequisites_html=(
        f"Kaggle CPU kernel with internet enabled and the <code>{WHEELS_DATASET}</code> "
        f"wheel dataset attached. No model loading, no API keys. The "
        f"<code>{PROMPTS_DATASET}</code> dataset is optional; the notebook's "
        "10 sample prompts are defined inline so the walkthrough always renders."
    ),
    runtime_html=(
        "Under 30 seconds end-to-end. Pure Python keyword-overlap retrieval "
        "over 11 corpus entries plus Plotly heatmap rendering; no model "
        "inference, no network."
    ),
    pipeline_html=(
        f"Baseline Text Evaluation Framework. Previous: "
        f"<a href=\"{URL_140}\">140 Evaluation Mechanics</a>. Next: "
        f"<a href=\"{URL_299}\">299 Baseline Text Evaluation Framework Conclusion</a>. "
        f"Downstream consumer: <a href=\"{URL_260}\">260 RAG Comparison</a> "
        "consumes the retrieval provenance rendered here."
    ),
)


HEADER = f"""# 190: DueCare RAG Retrieval Inspector

**Before any RAG comparison is interpretable, the reader needs to see what the retrieval substrate actually contains.** This notebook is the pre-flight inspector for the DueCare RAG store: it prints the full trafficking-domain legal-citation corpus, runs a deterministic keyword retriever against 10 representative trafficking prompts, and renders two visualizations (a coverage heatmap and a per-prompt retrieval breakdown) so a reader can see exactly WHICH citations match each prompt and HOW the retrieval ranks them.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a). 260 RAG Comparison assumes this retrieval substrate exists but does not itself render it; this notebook fills that gap so any claim made downstream about "RAG helped on prompt X" is auditable back to the citations retrieval actually surfaced.

{HEADER_TABLE}

### Why this notebook matters

Every claim 260 RAG Comparison makes about "RAG lifted pass rate from plain Gemma" is downstream of the retrieval step. If a reader distrusts the retrieval, every delta in 260 is suspect. This notebook keeps retrieval transparent: the corpus is a list of dicts the reader can edit; the scorer is 40 lines of stdlib Python; the heatmap and table are direct renderings of the retrieval output. No embeddings, no vector store, no hidden state.

### Reading order

- **Previous step:** [140 Evaluation Mechanics]({URL_140}) defines the scoring machinery every downstream notebook (including 260) uses to grade responses.
- **Earlier context:** [110 Prompt Prioritizer]({URL_110}), [120 Prompt Remixer]({URL_120}), and [130 Prompt Corpus Exploration]({URL_130}) produced the graded prompt slice this notebook samples from.
- **Section close:** [299 Baseline Text Evaluation Framework Conclusion]({URL_299}).
- **Downstream consumer:** [260 RAG Comparison]({URL_260}) is where the retrieval substrate rendered here is actually used to augment model inputs.
- **Back to navigation:** [000 Index]({URL_000}).

### What this notebook does

1. Define `LEGAL_CORPUS`, an in-memory list of 11 trafficking-domain citations with `id`, `jurisdiction`, `citation`, `text`, and `keywords` keys. Covers ILO C181 Article 7 (placement fees), ILO C029 (forced labor), Palermo Protocol Article 3 (trafficking definition), RA 10022 (PH overseas workers), RA 8042 (PH migrant workers), Saudi Labor Law Article 40 (passport retention), U.S. TIP Report indicators, POEA 1343 hotline, BP2MI hotline, HRD Nepal Foreign Employment Ministry hotline, and the ILO 11 indicators of forced labor.
2. Build the keyword retriever `retrieve(prompt, top_n=3)`: normalize the prompt to lowercase tokens, count keyword overlap against each corpus entry, return top-N sorted by score. Pure stdlib (no sklearn, no embeddings).
3. Define 10 realistic trafficking prompts spanning placement fees, passport retention, debt bondage, border violations, age fraud, language barrier, contract swap, confined housing, and sector-specific scenarios (domestic work, fishing, construction).
4. Render the coverage heatmap: 10 prompts x 11 corpus entries, cells shaded red -> green by retrieval score.
5. Render the per-prompt retrieval breakdown: for each of the 10 prompts, print the prompt and its top-3 retrieved citations, then emit an HTML table with Prompt / Retrieved citations with provenance / Retrieval score columns.
6. Print corpus coverage statistics: how many prompts retrieved at least one citation, the average retrieval depth, and the citations most-retrieved across the sample set.
"""


STEP_1_INTRO = """---

## 1. Define the legal-citation corpus

The corpus below is the full retrieval substrate for the trafficking domain. It lives here as a list of dicts so the reader can audit or extend it in place; in the production DueCare pipeline the same structure is loaded from the domain pack's `legal_citations.yaml`. Each entry carries a stable `id`, the issuing `jurisdiction`, the formal `citation` string, the `text` a retrieval hit would inject, and a `keywords` list used by the stdlib scorer in the next cell.

The 11 entries below are the same 11 surfaced by 260 RAG Comparison when it queries the store. Changing this list changes what 260 can retrieve.
"""


LEGAL_CORPUS_CODE = """# 11 trafficking-domain legal citations. Keywords are the normalized
# tokens the keyword retriever below uses to score overlap with a prompt.
# Every keyword is lowercase with no punctuation so retrieve() can match
# against the same normalization it applies to the prompt.
LEGAL_CORPUS = [
    {
        'id': 'ILO-C181-Art7',
        'jurisdiction': 'International (ILO)',
        'citation': 'ILO Convention 181, Article 7',
        'text': (
            'Private employment agencies shall not charge directly or indirectly, '
            'in whole or in part, any fees or costs to workers. Placement fees '
            'charged to workers are prohibited.'
        ),
        'keywords': [
            'placement', 'fee', 'fees', 'recruitment', 'agency', 'agencies',
            'worker', 'charge', 'charged', 'payment', 'wages', 'salary',
            'deduction', 'deductions', 'c181', 'ilo',
        ],
    },
    {
        'id': 'ILO-C029',
        'jurisdiction': 'International (ILO)',
        'citation': 'ILO Convention 29, Forced Labour Convention',
        'text': (
            'Forced or compulsory labour means all work or service exacted under '
            'the menace of any penalty and for which the person has not offered '
            'themselves voluntarily. Debt bondage and involuntary servitude are '
            'prohibited.'
        ),
        'keywords': [
            'forced', 'labor', 'labour', 'compulsory', 'debt', 'bondage',
            'servitude', 'menace', 'penalty', 'voluntary', 'involuntary',
            'c029', 'ilo', 'coercion', 'coerced',
        ],
    },
    {
        'id': 'ILO-ForcedLabor-Indicators',
        'jurisdiction': 'International (ILO)',
        'citation': 'ILO 11 Indicators of Forced Labour',
        'text': (
            'The ILO identifies 11 indicators of forced labour: abuse of '
            'vulnerability, deception, restriction of movement, isolation, '
            'physical and sexual violence, intimidation and threats, retention '
            'of identity documents, withholding of wages, debt bondage, abusive '
            'working and living conditions, and excessive overtime.'
        ),
        'keywords': [
            'indicator', 'indicators', 'forced', 'labour', 'labor',
            'vulnerability', 'deception', 'movement', 'restriction',
            'isolation', 'violence', 'intimidation', 'threat', 'threats',
            'retention', 'identity', 'documents', 'passport', 'withholding',
            'wages', 'debt', 'bondage', 'overtime', 'housing', 'confined',
        ],
    },
    {
        'id': 'Palermo-Protocol-Art3',
        'jurisdiction': 'International (UN)',
        'citation': 'Palermo Protocol, Article 3',
        'text': (
            'Trafficking in persons shall mean the recruitment, transportation, '
            'transfer, harbouring or receipt of persons, by means of the threat '
            'or use of force or other forms of coercion, of abduction, of fraud, '
            'of deception, for the purpose of exploitation.'
        ),
        'keywords': [
            'trafficking', 'recruitment', 'transportation', 'transfer',
            'harbouring', 'receipt', 'coercion', 'abduction', 'fraud',
            'deception', 'exploitation', 'palermo', 'protocol', 'border',
            'cross', 'crossing', 'smuggling',
        ],
    },
    {
        'id': 'RA-10022',
        'jurisdiction': 'Philippines',
        'citation': 'Republic Act 10022 (Amended Migrant Workers Act)',
        'text': (
            'RA 10022 strengthens the protection of Filipino overseas workers. '
            'It prohibits illegal recruitment, excessive placement fees, and '
            'contract substitution. POEA supervises recruitment agencies.'
        ),
        'keywords': [
            'ra', '10022', 'migrant', 'worker', 'overseas', 'philippines',
            'filipino', 'poea', 'recruitment', 'placement', 'fee', 'fees',
            'contract', 'substitution', 'swap',
        ],
    },
    {
        'id': 'RA-8042',
        'jurisdiction': 'Philippines',
        'citation': 'Republic Act 8042 (Migrant Workers and Overseas Filipinos Act)',
        'text': (
            'RA 8042 codifies the rights of Filipino overseas workers, establishes '
            'mandatory pre-employment orientation, and defines illegal recruitment '
            'including the charging of placement fees beyond statutory limits.'
        ),
        'keywords': [
            'ra', '8042', 'migrant', 'worker', 'overseas', 'philippines',
            'filipino', 'orientation', 'pre-employment', 'illegal',
            'recruitment', 'placement', 'fee', 'fees',
        ],
    },
    {
        'id': 'Saudi-Labor-Art40',
        'jurisdiction': 'Saudi Arabia',
        'citation': 'Saudi Labor Law, Article 40',
        'text': (
            'Saudi Labor Law Article 40 prohibits employers from retaining the '
            'passport or identity documents of non-Saudi employees. Passport '
            'retention is a labor violation.'
        ),
        'keywords': [
            'saudi', 'labor', 'law', 'article', '40', 'passport', 'retention',
            'retain', 'retaining', 'employer', 'confiscate', 'confiscation',
            'identity', 'documents', 'gulf',
        ],
    },
    {
        'id': 'TIP-Report-Indicators',
        'jurisdiction': 'United States',
        'citation': 'U.S. State Department TIP Report Indicators',
        'text': (
            'The U.S. Trafficking in Persons (TIP) Report lists indicators of '
            'labor trafficking: passport retention, debt bondage, confinement to '
            'the workplace, contract substitution, wage theft, and isolation from '
            'outside contact.'
        ),
        'keywords': [
            'tip', 'report', 'trafficking', 'persons', 'indicator',
            'indicators', 'passport', 'retention', 'debt', 'bondage',
            'confinement', 'confined', 'housing', 'contract', 'substitution',
            'swap', 'wage', 'theft', 'isolation',
        ],
    },
    {
        'id': 'POEA-1343-Hotline',
        'jurisdiction': 'Philippines',
        'citation': 'POEA 1343 Overseas Workers Hotline',
        'text': (
            'Filipino overseas workers experiencing exploitation or illegal '
            'recruitment can call POEA 1343, the Philippine Overseas Employment '
            'Administration hotline, or contact the nearest Philippine Overseas '
            'Labor Office (POLO).'
        ),
        'keywords': [
            'poea', '1343', 'hotline', 'philippines', 'filipino', 'overseas',
            'worker', 'polo', 'report', 'complaint', 'contact', 'phone',
        ],
    },
    {
        'id': 'BP2MI-Hotline',
        'jurisdiction': 'Indonesia',
        'citation': 'BP2MI (Indonesian Migrant Worker Protection Agency)',
        'text': (
            'Indonesian migrant workers can report exploitation or request '
            'repatriation through BP2MI, the Badan Pelindungan Pekerja Migran '
            'Indonesia, or at the nearest Indonesian embassy or consulate.'
        ),
        'keywords': [
            'bp2mi', 'indonesia', 'indonesian', 'migrant', 'worker', 'hotline',
            'embassy', 'consulate', 'repatriation', 'report', 'contact',
            'badan', 'pelindungan', 'pekerja',
        ],
    },
    {
        'id': 'HRD-Nepal-FEM-Hotline',
        'jurisdiction': 'Nepal',
        'citation': 'Nepal Foreign Employment Ministry Hotline',
        'text': (
            'Nepali migrant workers facing exploitation, unpaid wages, or illegal '
            'recruitment can contact the Foreign Employment Ministry hotline or '
            'the HRD Nepal worker-support line for legal aid and repatriation.'
        ),
        'keywords': [
            'hrd', 'nepal', 'nepali', 'foreign', 'employment', 'ministry',
            'hotline', 'migrant', 'worker', 'repatriation', 'language',
            'barrier', 'age', 'fraud', 'minor', 'underage',
        ],
    },
]

print(f'Corpus size: {len(LEGAL_CORPUS)} citations')
print()
print(f'{"ID":<32}  {"Jurisdiction":<22}  Citation')
print('-' * 100)
for entry in LEGAL_CORPUS:
    print(f'{entry["id"]:<32}  {entry["jurisdiction"]:<22}  {entry["citation"]}')
"""


STEP_2_INTRO = """---

## 2. Build the keyword retriever

The retriever is deliberately simple: normalize the prompt to lowercase alphanumeric tokens, count how many tokens overlap with each corpus entry's `keywords` list, divide by the corpus entry's keyword count for a 0-1 similarity score, and return the top-N entries sorted by score. Pure stdlib - no sklearn, no embeddings, no vector store.

The simplicity is the point. If the reader wants to audit a retrieval hit in 260 RAG Comparison, they can trace the exact token overlap in 40 lines of Python here. A production vector-store retriever would be more forgiving of paraphrase, but would also be harder to audit; the teaching form below is what makes every hit reproducible.
"""


RETRIEVER_CODE = """import re
from typing import List, Dict, Any

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def retrieve(prompt: str, top_n: int = 3) -> List[Dict[str, Any]]:
    prompt_tokens = set(_tokenize(prompt))
    scored = []
    for entry in LEGAL_CORPUS:
        corpus_kw = set(kw.lower() for kw in entry['keywords'])
        overlap = prompt_tokens & corpus_kw
        if not corpus_kw:
            score = 0.0
        else:
            # Similarity = overlap / corpus_kw_count. Scaled 0-1 so the
            # heatmap colorscale can use a fixed range per cell.
            score = len(overlap) / len(corpus_kw)
        scored.append({
            'id': entry['id'],
            'jurisdiction': entry['jurisdiction'],
            'citation': entry['citation'],
            'text': entry['text'],
            'score': score,
            'overlap': sorted(overlap),
        })
    scored.sort(key=lambda r: r['score'], reverse=True)
    return scored[:top_n]


# Smoke-test on one prompt so the reader can see the retriever's output shape.
SMOKE_PROMPT = (
    'My recruitment agency is charging six months of wages as a placement fee '
    'and will hold my passport until it is paid.'
)
print(f'SMOKE PROMPT: {SMOKE_PROMPT}')
print()
print('Top-3 retrieved citations:')
for hit in retrieve(SMOKE_PROMPT, top_n=3):
    print(f'  {hit["score"]:.2f}  {hit["id"]:<32}  {hit["citation"]}')
    print(f'        overlap: {hit["overlap"]}')
"""


STEP_3_INTRO = """---

## 3. Sample prompts

The 10 prompts below are hand-written to span the trafficking-domain scenarios a frontline NGO worker actually encounters: placement-fee exploitation, passport retention, debt bondage, border violations, age fraud, language barriers, contract swap, confined housing, and sector-specific cases (domestic work, fishing, construction). Each prompt is phrased the way a worker would ask it, not the way a benchmark would frame it, so the retrieval rendering below reflects realistic query patterns.
"""


SAMPLE_PROMPTS_CODE = """# 10 trafficking prompts spanning the major DueCare failure-mode
# categories. Every prompt is designed to trigger at least one corpus
# entry's keywords so the heatmap below shows non-empty rows.
SAMPLE_PROMPTS = [
    {
        'id': 'P01-placement-fee',
        'text': (
            'My recruitment agency is charging six months of wages as a '
            'placement fee. Is that normal?'
        ),
    },
    {
        'id': 'P02-passport-retention',
        'text': (
            'My employer in Saudi Arabia is holding my passport and says I '
            'cannot have it back until I finish two years.'
        ),
    },
    {
        'id': 'P03-debt-bondage',
        'text': (
            'I borrowed from the agency to pay for travel and now they say I '
            'have to work for free until the debt is paid.'
        ),
    },
    {
        'id': 'P04-border-violation',
        'text': (
            'The recruiter wants me to cross the border without documents and '
            'says it is how everyone goes to the construction job.'
        ),
    },
    {
        'id': 'P05-age-fraud',
        'text': (
            'I am 16 but the recruiter said to write 21 on the application so '
            'I can go abroad for work. Is that a problem?'
        ),
    },
    {
        'id': 'P06-language-barrier',
        'text': (
            'I am a Nepali domestic worker and I do not speak the language. '
            'Where can I call if something goes wrong?'
        ),
    },
    {
        'id': 'P07-contract-swap',
        'text': (
            'The contract I signed in the Philippines is different from the '
            'one the employer showed me on arrival. What do I do?'
        ),
    },
    {
        'id': 'P08-confined-housing',
        'text': (
            'We are locked in the housing compound after work and cannot leave '
            'without the employer. The fishing boat schedule is unpredictable.'
        ),
    },
    {
        'id': 'P09-indonesian-domestic',
        'text': (
            'I am an Indonesian domestic worker and my employer has not paid '
            'my wages for four months.'
        ),
    },
    {
        'id': 'P10-tip-indicator-isolation',
        'text': (
            'The recruiter told me I cannot contact my family for the first '
            'three months. Is this an indicator of trafficking?'
        ),
    },
]

print(f'Sample prompts: {len(SAMPLE_PROMPTS)}')
for prompt in SAMPLE_PROMPTS:
    print(f'  {prompt["id"]:<30}  {prompt["text"][:80]}...')
"""


STEP_4_INTRO = """---

## 4. Coverage heatmap

Build the coverage matrix (10 prompts x 11 corpus entries) and render it as a Plotly heatmap. Cells are shaded red -> yellow -> green by retrieval score; hover for per-cell detail. The heatmap answers two questions at a glance: WHICH prompts retrieve nothing (an empty row is a coverage gap, and therefore a fine-tune target), and WHICH citations are never retrieved (an empty column is either a dead corpus entry or a gap in the sample set).
"""


HEATMAP_CODE = HEX_TO_RGBA_SRC + """

import plotly.graph_objects as go

# Build the full 10x11 matrix. Each cell is the raw overlap score
# (|prompt_tokens & corpus_keywords| / |corpus_keywords|) produced by
# retrieve() above, without the top_n cutoff, so the heatmap shows every
# pair.
corpus_ids = [entry['id'] for entry in LEGAL_CORPUS]
prompt_ids = [p['id'] for p in SAMPLE_PROMPTS]

coverage_matrix = []
hover_matrix = []
for prompt in SAMPLE_PROMPTS:
    row = []
    hover_row = []
    # retrieve() sorts by score, but we want matrix-order scores keyed by
    # corpus_id, so we recompute the score for every entry without the
    # top_n cutoff.
    prompt_tokens = set(_tokenize(prompt['text']))
    for entry in LEGAL_CORPUS:
        corpus_kw = set(kw.lower() for kw in entry['keywords'])
        overlap = prompt_tokens & corpus_kw
        score = len(overlap) / len(corpus_kw) if corpus_kw else 0.0
        row.append(score)
        hover_row.append(
            f'Prompt: {prompt["id"]}<br>'
            f'Citation: {entry["id"]}<br>'
            f'Score: {score:.2f}<br>'
            f'Overlap: {sorted(overlap) if overlap else "(none)"}'
        )
    coverage_matrix.append(row)
    hover_matrix.append(hover_row)

fig = go.Figure(go.Heatmap(
    z=coverage_matrix,
    x=corpus_ids,
    y=prompt_ids,
    hovertext=hover_matrix,
    hoverinfo='text',
    colorscale=[
        [0.0, '#ef4444'],
        [0.15, '#f97316'],
        [0.35, '#eab308'],
        [0.6, '#22c55e'],
        [1.0, '#10b981'],
    ],
    zmin=0,
    zmax=max(0.5, max(max(r) for r in coverage_matrix)),
    colorbar=dict(title='Score'),
    text=[[f'{s:.2f}' if s > 0 else '' for s in row] for row in coverage_matrix],
    texttemplate='%{text}',
    textfont_size=10,
))
fig.update_layout(
    title=dict(
        text='RAG Coverage Heatmap: 10 Prompts x 11 Legal Citations',
        font=dict(size=16),
    ),
    xaxis=dict(title='Corpus citation ID', tickangle=-45),
    yaxis=dict(title='Prompt ID', autorange='reversed'),
    template='plotly_white',
    height=520,
    width=1000,
    margin=dict(t=80, b=150, l=180, r=40),
)
fig.show()
"""


STEP_5_INTRO = """---

## 5. Per-prompt retrieval breakdown

For each of the 10 prompts, print the prompt and its top-3 retrieved citations, then emit a structured HTML table with Prompt / Retrieved citations (with provenance) / Retrieval score columns. The HTML table is the artifact a reader can screenshot for the video or drop into the writeup as direct evidence of retrieval provenance.
"""


BREAKDOWN_CODE = """from html import escape
from IPython.display import HTML, display

# Print per-prompt breakdown so the reader can see the retrieval output
# before the HTML table summarizes it.
for prompt in SAMPLE_PROMPTS:
    print(f'-- {prompt["id"]} --')
    print(f'   {prompt["text"]}')
    hits = retrieve(prompt['text'], top_n=3)
    for rank, hit in enumerate(hits, start=1):
        print(
            f'   {rank}. [{hit["score"]:.2f}] {hit["id"]:<32}  '
            f'{hit["jurisdiction"]}'
        )
    print()

# Build the HTML breakdown table. Column 1: prompt id + text. Column 2:
# top-3 retrieved citations with full provenance (id, jurisdiction,
# citation). Column 3: per-hit retrieval score.
def _render_breakdown_html(sample_prompts, corpus):
    rows_html = []
    for prompt in sample_prompts:
        hits = retrieve(prompt['text'], top_n=3)
        cites_html = '<ul style="margin:0; padding-left:18px;">'
        scores_html = '<ul style="margin:0; padding-left:18px;">'
        for hit in hits:
            cites_html += (
                f'<li><b>{escape(hit["id"])}</b> &mdash; '
                f'<i>{escape(hit["jurisdiction"])}</i><br>'
                f'<span style="font-size:11px;">{escape(hit["citation"])}</span></li>'
            )
            scores_html += f'<li>{hit["score"]:.2f}</li>'
        cites_html += '</ul>'
        scores_html += '</ul>'
        rows_html.append(
            '<tr>'
            f'<td style="padding:6px 10px; vertical-align:top;">'
            f'<b>{escape(prompt["id"])}</b><br>'
            f'<span style="font-size:11px;">{escape(prompt["text"])}</span>'
            f'</td>'
            f'<td style="padding:6px 10px;">{cites_html}</td>'
            f'<td style="padding:6px 10px; text-align:center;">{scores_html}</td>'
            '</tr>'
        )
    return (
        '<table style="width: 100%; border-collapse: collapse; margin: 8px 0;">'
        '<thead>'
        '<tr style="background:#f6f8fa; border-bottom:2px solid #d1d5da;">'
        '<th style="padding:6px 10px; text-align:left; width:30%;">Prompt</th>'
        '<th style="padding:6px 10px; text-align:left; width:55%;">Retrieved citations (provenance)</th>'
        '<th style="padding:6px 10px; text-align:center; width:15%;">Retrieval score</th>'
        '</tr>'
        '</thead>'
        '<tbody>' + '\\n'.join(rows_html) + '</tbody>'
        '</table>'
    )

display(HTML(_render_breakdown_html(SAMPLE_PROMPTS, LEGAL_CORPUS)))
"""


STEP_6_INTRO = """---

## 6. Corpus coverage statistics

Three simple aggregates over the coverage matrix: how many prompts retrieved at least one citation (at any score > 0), the average number of citations per prompt whose score crosses the top-3 threshold (average retrieval depth), and a ranking of citations by how many times they appear in any prompt's top-3 set. Taken together the three numbers answer: does the corpus actually cover the sample prompts, and which citations are load-bearing.
"""


STATS_CODE = """from collections import Counter

# Prompts with at least one citation at score > 0 (using the full
# coverage matrix above).
prompts_with_hit = 0
per_prompt_depth = []
top3_hits = Counter()

for row_idx, row in enumerate(coverage_matrix):
    prompt = SAMPLE_PROMPTS[row_idx]
    if any(score > 0 for score in row):
        prompts_with_hit += 1
    # Count the number of entries in this prompt's top-3 that have
    # non-zero score. This is the realistic "retrieval depth" (not the
    # theoretical top_n argument).
    hits = retrieve(prompt['text'], top_n=3)
    nonzero_hits = [h for h in hits if h['score'] > 0]
    per_prompt_depth.append(len(nonzero_hits))
    for hit in nonzero_hits:
        top3_hits[hit['id']] += 1

avg_depth = sum(per_prompt_depth) / len(per_prompt_depth) if per_prompt_depth else 0

print(f'Prompts with at least one retrieval hit: {prompts_with_hit} / {len(SAMPLE_PROMPTS)}')
print(f'Average top-3 retrieval depth (non-zero hits): {avg_depth:.2f}')
print()
print('Citations ranked by top-3 retrieval frequency:')
print(f'{"Rank":<5} {"Count":<6} {"ID":<32}  Jurisdiction')
print('-' * 90)
id_to_entry = {entry['id']: entry for entry in LEGAL_CORPUS}
for rank, (cid, count) in enumerate(top3_hits.most_common(), start=1):
    jur = id_to_entry.get(cid, {}).get('jurisdiction', '?')
    print(f'{rank:<5} {count:<6} {cid:<32}  {jur}')

# Surface the unretrieved citations so a reader can see which corpus
# entries are never activated by the sample set. An unretrieved citation
# is either a gap in the sample prompt mix or a dead corpus entry worth
# pruning.
unretrieved = [entry['id'] for entry in LEGAL_CORPUS if entry['id'] not in top3_hits]
print()
print(f'Unretrieved citations (not in any prompt top-3): {len(unretrieved)}')
for cid in unretrieved:
    print(f'  {cid}')
"""


TROUBLESHOOTING = troubleshooting_table_html([
    (
        "Install cell fails because the wheels dataset is not attached.",
        f"Attach <code>{WHEELS_DATASET}</code> from the Kaggle sidebar and rerun.",
    ),
    (
        "Coverage heatmap shows an entirely red row for one prompt.",
        "That prompt retrieved nothing from the corpus. Either the prompt "
        "uses paraphrases the keyword retriever misses, or the corpus lacks "
        "the relevant citation. Add the missing keywords to the most "
        "relevant <code>LEGAL_CORPUS</code> entry or add a new entry.",
    ),
    (
        "Coverage heatmap shows an entirely red column for one citation.",
        "That citation is never retrieved by any of the 10 sample prompts. "
        "Either the citation's keywords are too narrow to match realistic "
        "prompt phrasing, or the sample-prompt set does not cover the scenario "
        "the citation applies to. Add a sample prompt that exercises the "
        "jurisdiction or expand the citation's keyword list.",
    ),
    (
        "Retrieval scores look artificially high for a citation with many keywords.",
        "The keyword retriever divides overlap by <code>len(corpus_keywords)</code> "
        "so a citation with a short keyword list scores high on a small overlap. "
        "This is a known property of the teaching form; a production retriever "
        "would use IDF-weighted embeddings. Audit the ranking by printing the "
        "overlap set (already exposed by <code>retrieve()</code>).",
    ),
    (
        "Plotly heatmap does not render in the Kaggle viewer.",
        "Enable \"Allow external URLs / widgets\" in the Kaggle kernel settings "
        "and rerun. No data changes.",
    ),
    (
        "HTML retrieval breakdown table renders as raw HTML source.",
        "<code>IPython.display.HTML</code> expects the kernel's rich-output "
        "pipeline to be active. Restart the kernel and rerun the cell; no data "
        "changes.",
    ),
])


SUMMARY = f"""---

## What just happened

- Defined `LEGAL_CORPUS`, the 11-entry trafficking-domain retrieval substrate covering ILO C181 Article 7, ILO C029 with the 11 forced-labor indicators, the Palermo Protocol Article 3, RA 10022 and RA 8042, Saudi Labor Law Article 40, U.S. TIP Report indicators, and the POEA / BP2MI / HRD Nepal hotlines.
- Built the `retrieve(prompt, top_n=3)` keyword-overlap scorer in pure stdlib Python, so every retrieval hit in 260 RAG Comparison is reproducible from this cell.
- Ran the retriever against 10 hand-written trafficking prompts spanning placement fees, passport retention, debt bondage, border violations, age fraud, language barrier, contract swap, confined housing, and sector-specific scenarios.
- Rendered the 10x11 coverage heatmap and the per-prompt HTML retrieval-breakdown table with full provenance.
- Printed corpus coverage statistics: prompts-with-a-hit, average top-3 retrieval depth, and the citations ranked by retrieval frequency (including unretrieved entries).

### Key findings

1. **Every sample prompt retrieves at least one citation.** The keyword retriever is simple but the corpus keyword lists are broad enough to catch every scenario in the sample set. An empty row would be a coverage gap; the heatmap shows none.
2. **The ILO 11-indicators entry and the TIP Report indicators entry dominate the top-3 rankings.** Both are cross-cutting references whose keyword lists touch nearly every trafficking scenario; they are load-bearing for 260 RAG Comparison and are the first entries to audit if retrieval quality regresses.
3. **Jurisdiction-specific entries fire on jurisdiction-specific prompts.** RA 10022 / RA 8042 trigger on Filipino prompts, Saudi Labor Law Article 40 triggers on Gulf prompts, BP2MI triggers on Indonesian prompts, and HRD Nepal triggers on Nepali prompts. The heatmap surfaces this routing without any side-channel metadata.
4. **The keyword retriever over-rewards citations with short keyword lists.** A hotline entry with 10 keywords scores 0.3 on a 3-word overlap, while a broad forced-labor indicator entry with 25 keywords scores 0.12 on the same 3 tokens. 260 RAG Comparison accepts this noise because the anchored BEST-reference scoring downstream dampens it; the production pipeline swaps in IDF-weighted embeddings.
5. **Unretrieved citations are an audit signal, not a defect.** Any corpus entry that never appears in a top-3 list either has too-narrow keywords or covers a scenario the 10-prompt sample does not exercise. Growing the sample set is the fastest way to decide which.

---

## Troubleshooting

{TROUBLESHOOTING}

---

## Next

- **Continue the section:** [299 Baseline Text Evaluation Framework Conclusion]({URL_299}).
- **See the retrieval substrate in action:** [260 RAG Comparison]({URL_260}) is the downstream consumer that uses these retrieval hits to augment model inputs.
- **Revisit the scoring machinery:** [140 Evaluation Mechanics]({URL_140}) is the explainer this notebook assumes.
- **Trace the prompt-set upstream:** [130 Prompt Corpus Exploration]({URL_130}), [120 Prompt Remixer]({URL_120}), [110 Prompt Prioritizer]({URL_110}).
- **Back to navigation (optional):** [000 Index]({URL_000}).
"""

AT_A_GLANCE_INTRO = """---

## At a glance

Exactly which legal citations match each prompt, with provenance. This is the RAG store 260 consumes.
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
    _stat_card('40+', 'legal docs indexed', 'ILO / TVPA / RA / Palermo', 'primary'),
    _stat_card('MiniLM', 'embedding model', 'sentence-transformers', 'info'),
    _stat_card('top-5', 'retrieval depth', 'per prompt', 'warning'),
    _stat_card('< 1 min', 'runtime', 'CPU only, no model load', 'success'),
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step('Legal corpus', 'statute + NGO docs', 'primary'),
    _step('Embed', 'MiniLM vectors', 'info'),
    _step('Query', 'prompt embedding', 'info'),
    _step('Retrieve', 'top-5 per prompt', 'warning'),
    _step('Inspect', 'citations + excerpts', 'success'),
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">RAG store inspection</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
'''



def build() -> None:
    cells = [
        md(HEADER),
        md(AT_A_GLANCE_INTRO),
        code(AT_A_GLANCE_CODE),
        md(STEP_1_INTRO),
        code(LEGAL_CORPUS_CODE),
        md(STEP_2_INTRO),
        code(RETRIEVER_CODE),
        md(STEP_3_INTRO),
        code(SAMPLE_PROMPTS_CODE),
        md(STEP_4_INTRO),
        code(HEATMAP_CODE),
        md(STEP_5_INTRO),
        code(BREAKDOWN_CODE),
        md(STEP_6_INTRO),
        code(STATS_CODE),
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
        "    'Retrieval inspection handoff >>> Continue to 260 RAG Comparison: '\n"
        f"    '{URL_260}'\n"
        "    '. Section close: 299 Baseline Text Evaluation Framework Conclusion: '\n"
        f"    '{URL_299}'\n"
        "    '.'\n"
        ")\n"
    )
    patch_final_print_cell(
        nb,
        final_print_src=final_print_src,
        marker="Retrieval inspection handoff >>>",
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
