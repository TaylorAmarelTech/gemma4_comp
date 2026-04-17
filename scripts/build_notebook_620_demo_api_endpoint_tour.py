#!/usr/bin/env python3
"""Build the 620 DueCare Demo API Endpoint Tour notebook.

CPU-only walkthrough of every FastAPI endpoint the DueCare demo app
exposes. The notebook is designed for judges and adopters who want to
understand the deployment surface without spinning up a server: each
endpoint gets a titled subsection with a curl example, a sample
response shape, and a Python requests snippet. An optional TestClient
path lets the notebook import the FastAPI app locally and call
endpoints in-process so the cells actually produce output without a
running server. A Plotly sankey at the bottom renders the endpoint
-> agent/tool call graph so the deployment story is visible at a
glance.
"""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import (
    canonical_header_table,
    patch_final_print_cell,
    troubleshooting_table_html,
)
from notebook_hardening_utils import harden_notebook


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"

FILENAME = "620_demo_api_endpoint_tour.ipynb"
KERNEL_DIR_NAME = "duecare_620_demo_api_endpoint_tour"
KERNEL_ID = "taylorsamarel/duecare-620-demo-api-endpoint-tour"
KERNEL_TITLE = "620: DueCare Demo API Endpoint Tour"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["gemma", "safety", "api", "demo", "fastapi"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_140 = "https://www.kaggle.com/code/taylorsamarel/duecare-140-evaluation-mechanics"
URL_260 = "https://www.kaggle.com/code/taylorsamarel/duecare-260-rag-comparison"
URL_460 = "https://www.kaggle.com/code/taylorsamarel/duecare-460-citation-verifier"
URL_600 = "https://www.kaggle.com/code/taylorsamarel/600-duecare-results-dashboard"
URL_610 = "https://www.kaggle.com/code/taylorsamarel/duecare-610-submission-walkthrough"
URL_620 = "https://www.kaggle.com/code/taylorsamarel/duecare-620-demo-api-endpoint-tour"
URL_650 = "https://www.kaggle.com/code/taylorsamarel/duecare-650-custom-domain-walkthrough"
URL_899 = "https://www.kaggle.com/code/taylorsamarel/899-duecare-solution-surfaces-conclusion"


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
        "An in-notebook <code>ENDPOINTS</code> catalog describing the 13 FastAPI "
        "routes exposed by <code>src/demo/app.py</code>, plus an optional in-process "
        "<code>fastapi.testclient.TestClient</code> bound to the real app so the "
        "calls render live output when the package is installed. No external server "
        "is required."
    ),
    outputs_html=(
        "Per-endpoint subsections with <code>curl</code>, request and response "
        "shape, and a Python <code>requests</code> snippet for seven representative "
        "routes (<code>/analyze</code>, <code>/rag-context</code>, "
        "<code>/function-call</code>, <code>/analyze-document</code>, "
        "<code>/migration-case</code>, <code>/evaluate</code>, "
        "<code>/quick-check</code>); an HTML summary table covering all 13 "
        "endpoints; and a Plotly sankey rendering the "
        "endpoint -> agent/tool call graph."
    ),
    prerequisites_html=(
        f"Kaggle CPU kernel with internet enabled and the <code>{WHEELS_DATASET}</code> "
        "wheel dataset attached. The <code>fastapi.testclient</code> path is optional; "
        "when the DueCare demo package is not importable the cells print scripted "
        "sample responses so the tour still renders end-to-end."
    ),
    runtime_html="Under 30 seconds end-to-end. No model inference; all work is catalog rendering and local TestClient calls.",
    pipeline_html=(
        f"Solution Surfaces. Previous: <a href='{URL_610}'>610 Submission "
        f"Walkthrough</a>. Next: <a href='{URL_650}'>650 Custom Domain "
        f"Walkthrough</a>. Section close: <a href='{URL_899}'>899 Solution "
        "Surfaces Conclusion</a>."
    ),
)


HEADER = f"""# 620: DueCare Demo API Endpoint Tour

**The deployment surface without a running server.** This notebook walks every FastAPI endpoint the DueCare demo app (<code>src/demo/app.py</code>) exposes: 13 routes covering single-prompt analysis, batch analysis, full rubric evaluation, native function calling, multimodal document analysis, multi-document NGO case intake, RAG retrieval, quick-check triage, metadata listings, aggregate stats, a liveness probe, and the HTML dashboard. Each endpoint gets a titled subsection with a curl example, a sample response shape, and a Python <code>requests</code> snippet. A Plotly sankey at the bottom shows which endpoints call which downstream agents and tools so the deployment story is visible at a glance.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a). This tour is the fastest way for a judge or an adopting NGO engineer to understand the demo surface without spinning up uvicorn.

{HEADER_TABLE}

### Why CPU-only

The tour never loads a model. When the demo package is installed, the notebook uses <code>fastapi.testclient.TestClient</code> to call the real app in-process; when it is not, the scripted example responses still render so the cells always produce output. Either way, no GPU, no network round-trip, no external server.

### Reading order

- **Previous step:** [610 Submission Walkthrough]({URL_610}) explains the end-to-end story this API serves.
- **Grading logic upstream:** [140 Evaluation Mechanics]({URL_140}), [260 RAG Comparison]({URL_260}), [460 Citation Verifier]({URL_460}).
- **Next step:** [650 Custom Domain Walkthrough]({URL_650}) shows adopters how to plug a new domain pack into the same endpoints.
- **Section close:** [899 Solution Surfaces Conclusion]({URL_899}).
- **Back to navigation:** [000 Index]({URL_000}).

### What this notebook does

1. Define a typed <code>ENDPOINTS</code> catalog describing all 13 routes.
2. Optionally spin up a <code>TestClient</code> against <code>duecare.demo.api.app</code>; fall back cleanly when the package is not importable.
3. Walk seven representative endpoints (<code>/analyze</code>, <code>/rag-context</code>, <code>/function-call</code>, <code>/analyze-document</code>, <code>/migration-case</code>, <code>/evaluate</code>, <code>/quick-check</code>) with curl + response + Python snippets.
4. Render an HTML summary table covering all 13 endpoints.
5. Render a Plotly sankey of the endpoint -> agent/tool call graph.
"""


STEP_1_INTRO = """---

## 1. The DueCare API at a glance

The demo app ships 12 routes under the <code>/api/v1</code> prefix plus the root HTML dashboard. The <code>ENDPOINTS</code> catalog below captures the method, path, a one-line summary, the request and response shape, a curl example, and a Python <code>requests</code> snippet for each route. Every downstream cell reads from this one source of truth so if a route signature changes, one edit propagates to every subsection.
"""


ENDPOINTS_CODE = """ENDPOINTS = [
    {
        'method': 'POST',
        'path': '/api/v1/analyze',
        'name': 'Single-prompt safety analysis',
        'summary': 'Score one input against all loaded trafficking rubrics and return grade, action, indicators, localized warning, legal refs, and resources.',
        'request_shape': {
            'text': 'str (required)',
            'context': 'enum: job_posting | chat | contract | comment | document | other',
            'jurisdiction': 'str (optional; corridor code like PH_HK)',
            'language': 'enum: en | tl (default en)',
        },
        'response_shape': {
            'score': 'float in [0, 1]',
            'grade': 'enum: best | good | neutral | bad | worst',
            'action': 'enum: pass | warn | review | block',
            'indicators': 'list[str]',
            'warning_text': 'str',
            'legal_refs': 'list[str]',
            'resources': 'list[{name, number, url, jurisdiction}]',
            'rubric_results': 'list[{rubric_name, score, grade, criteria_results}]',
        },
        'curl_example': (
            \"curl -X POST http://localhost:8080/api/v1/analyze \\\\\\n\"
            \"  -H 'Content-Type: application/json' \\\\\\n\"
            '  -d \\'{\"text\": \"Agency wants six months of wages as placement fee\", '
            '\"context\": \"chat\", \"jurisdiction\": \"PH_HK\"}\\''
        ),
        'python_example': (
            \"import requests\\n\"
            \"r = requests.post('http://localhost:8080/api/v1/analyze', json={\\n\"
            \"    'text': 'Agency wants six months of wages as placement fee',\\n\"
            \"    'context': 'chat',\\n\"
            \"    'jurisdiction': 'PH_HK',\\n\"
            \"})\\n\"
            \"print(r.json()['grade'], r.json()['action'])\"
        ),
    },
    {
        'method': 'POST',
        'path': '/api/v1/batch',
        'name': 'Batch safety analysis',
        'summary': 'Accept up to 500 items, score each against the rubric bank, and return per-item results + aggregate grade/action distributions.',
        'request_shape': {
            'items': 'list[AnalyzeRequest] (max 500)',
        },
        'response_shape': {
            'results': 'list[AnalyzeResponse]',
            'summary': {
                'total': 'int',
                'grade_distribution': 'dict[grade, count]',
                'action_distribution': 'dict[action, count]',
                'summary': 'Accept document text (or, in production, a photo) and return structured risk, findings, indicator flags, legal refs, extracted fields, and timeline markers.',
                'flagged_count': 'int',
            },
            'batch_id': 'str (uuid-12)',
        },
        'curl_example': (
                    'document_type': 'str',
                    'risk_level': 'enum: HIGH | MEDIUM | LOW',
                    'findings': 'list[str]',
                    'indicator_flags': 'list[str]',
                    'legal_refs': 'list[str]',
                    'recommendation': 'str',
            \"curl -X POST http://localhost:8080/api/v1/batch \\\\\\n\"
                    'timeline_markers': 'list[str]',
                    'resources': 'list[{name, number, url, jurisdiction}]',
                    'confidence': 'float',
            \"import requests\\n\"
            \"r = requests.post('http://localhost:8080/api/v1/batch', json={\\n\"
            \"    'items': [\\n\"
            \"        {'text': 'Agency holds passport until fees paid'},\\n\"
            \"        {'text': 'Live-in caregiver, employer pays all fees per ILO C181'},\\n\"
            \"    ],\\n\"
            \"})\\n\"
            \"print(r.json()['summary'])\"
        ),
    },
    {
        'method': 'POST',
        'path': '/api/v1/evaluate',
                    "print(r.json().get('risk_level'), r.json().get('indicator_flags'))"
        'summary': 'Send text to Gemma 4 via Ollama and score the response. Modes: plain | rag | guided | compare (all three side-by-side).',
        'request_shape': {
            {
                'method': 'POST',
                'path': '/api/v1/migration-case',
                'name': 'NGO migration case intake',
                'summary': 'Bundle multiple migration documents into one case packet, classify each file, build a timeline, retrieve grounding context, and draft complaint text.',
                'request_shape': {
                    'case_id': 'str (optional)',
                    'corridor': 'str (optional; corridor code like PH_HK)',
                    'documents': 'list[{document_id, title, text, context, captured_at}]',
                    'include_complaint_templates': 'bool (default True)',
                    'top_k_context': 'int (default 5)',
                },
                'response_shape': {
                    'case_id': 'str',
                    'corridor': 'str',
                    'document_count': 'int',
                    'risk_level': 'enum: HIGH | MEDIUM | LOW',
                    'detected_indicators': 'list[str]',
                    'applicable_laws': 'list[str]',
                    'retrieved_context': 'str',
                    'timeline': 'list[{date, label, document_id, description}]',
                    'document_analyses': 'list[{document_id, title, risk_level, findings, indicator_flags}]',
                    'recommended_actions': 'list[str]',
                    'hotlines': 'list[{name, number, url, jurisdiction}]',
                    'tool_results': 'list[{tool, result}]',
                    'complaint_templates': 'list[{name, audience, text}]',
                },
                'curl_example': (
                    "curl -X POST http://localhost:8080/api/v1/migration-case \\\n"
                    "  -H 'Content-Type: application/json' \\\n"
                    '  -d \'{"case_id": "case-demo-001", "corridor": "PH_HK", '
                    '"documents": [{"title": "Agency receipt", "context": "receipt", '
                    '"text": "Receipt for placement fee: HKD 20000 paid by worker."}, '
                    '{"title": "Employment contract", "context": "contract", '
                    '"text": "Employer will retain passport and deduct fees over 7 months."}]}\''
                ),
                'python_example': (
                    "import requests\n"
                    "r = requests.post('http://localhost:8080/api/v1/migration-case', json={\n"
                    "    'case_id': 'case-demo-001',\n"
                    "    'corridor': 'PH_HK',\n"
                    "    'documents': [\n"
                    "        {'title': 'Agency receipt', 'context': 'receipt', 'text': 'Receipt for placement fee: HKD 20000 paid by worker.'},\n"
                    "        {'title': 'Employment contract', 'context': 'contract', 'text': 'Employer will retain passport and deduct fees over 7 months.'},\n"
                    "    ],\n"
                    "})\n"
                    "print(r.json()['risk_level'], len(r.json()['timeline']))"
                ),
            },
            'text': 'str (required)',
            'mode': 'enum: plain | rag | guided | compare (default plain)',
            'model': 'str (default gemma4:e4b)',
        },
        'response_shape': {
            'plain':   'GemmaResult (when mode=compare)',
            'rag':     'GemmaResult (when mode=compare)',
            'guided':  'GemmaResult (when mode=compare)',
            'response':    'str (when mode != compare)',
            'score':       'float',
            'grade':       'enum',
            'mode_used':   'str',
            'latency_ms':  'int',
        },
        'curl_example': (
            \"curl -X POST http://localhost:8080/api/v1/evaluate \\\\\\n\"
            \"  -H 'Content-Type: application/json' \\\\\\n\"
            '  -d \\'{\"text\": \"What should I do about my recruitment fee?\", '
            '\"mode\": \"compare\"}\\''
        ),
        'python_example': (
            \"import requests\\n\"
            \"r = requests.post('http://localhost:8080/api/v1/evaluate', json={\\n\"
            \"    'text': 'What should I do about my recruitment fee?',\\n\"
            \"    'mode': 'compare',\\n\"
            \"    'model': 'gemma4:e4b',\\n\"
            \"})\\n\"
            \"print({k: v.get('grade') for k, v in r.json().items() if isinstance(v, dict)})\"
        ),
    },
    {
        'method': 'POST',
        'path': '/api/v1/function-call',
        'name': 'Native Gemma 4 tool call',
        'summary': 'Demonstrate Gemma 4 native function calling. Gemma autonomously picks among check_fee_legality, check_legal_framework, lookup_hotline, identify_trafficking_indicators, score_exploitation_risk.',
        'request_shape': {
            'text': 'str (required)',
        },
        'response_shape': {
            'input': 'str',
            'tools_available': 'list[str]',
            'tools_called': 'int',
            'results': 'list[{tool, result}]',
        },
        'curl_example': (
            \"curl -X POST http://localhost:8080/api/v1/function-call \\\\\\n\"
            \"  -H 'Content-Type: application/json' \\\\\\n\"
            '  -d \\'{\"text\": \"PHP 50000 placement fee for Hong Kong domestic work\"}\\''
        ),
        'python_example': (
            \"import requests\\n\"
            \"r = requests.post('http://localhost:8080/api/v1/function-call', json={\\n\"
            \"    'text': 'PHP 50000 placement fee for Hong Kong domestic work',\\n\"
            \"})\\n\"
            \"for call in r.json()['results']:\\n\"
            \"    print(call['tool'])\"
        ),
    },
    {
        'method': 'POST',
        'path': '/api/v1/analyze-document',
        'name': 'Multimodal document analysis',
        'summary': 'Accept document text (or, in production, a photo) and extract exploitation indicators, monetary amounts, fee clauses, passport references.',
        'request_shape': {
            'text': 'str (required)',
            'context': 'str (optional; default "document")',
        },
        'response_shape': {
            'extracted_fields': 'dict[str, Any]',
            'indicator_flags': 'list[str]',
            'score': 'float',
            'grade': 'enum',
            'notes': 'list[str]',
        },
        'curl_example': (
            \"curl -X POST http://localhost:8080/api/v1/analyze-document \\\\\\n\"
            \"  -H 'Content-Type: application/json' \\\\\\n\"
            '  -d \\'{\"text\": \"Employer to retain passport for contract duration\", '
            '\"context\": \"contract\"}\\''
        ),
        'python_example': (
            \"import requests\\n\"
            \"r = requests.post('http://localhost:8080/api/v1/analyze-document', json={\\n\"
            \"    'text': 'Employer to retain passport for contract duration',\\n\"
            \"    'context': 'contract',\\n\"
            \"})\\n\"
            \"print(r.json().get('indicator_flags'))\"
        ),
    },
    {
        'method': 'POST',
        'path': '/api/v1/rag-context',
        'name': 'RAG retrieval for a prompt',
        'summary': 'Retrieve relevant legal provisions, corridor fingerprints, and scheme fingerprints from the DueCare knowledge base for injection into Gemma\\'s prompt.',
        'request_shape': {
            'text': 'str (required)',
            'top_k': 'int (default 5)',
        },
        'response_shape': {
            'query': 'str',
            'context': 'str (newline-joined, citation-bracketed)',
            'n_entries': 'int (size of the index)',
            'n_retrieved': 'int (entries included in context)',
        },
        'curl_example': (
            \"curl -X POST http://localhost:8080/api/v1/rag-context \\\\\\n\"
            \"  -H 'Content-Type: application/json' \\\\\\n\"
            '  -d \\'{\"text\": \"Is a placement fee legal for Filipino domestic workers?\", '
            '\"top_k\": 5}\\''
        ),
        'python_example': (
            \"import requests\\n\"
            \"r = requests.post('http://localhost:8080/api/v1/rag-context', json={\\n\"
            \"    'text': 'Is a placement fee legal for Filipino domestic workers?',\\n\"
            \"    'top_k': 5,\\n\"
            \"})\\n\"
            \"print(r.json()['n_retrieved'], 'entries retrieved')\"
        ),
    },
    {
        'method': 'POST',
        'path': '/api/v1/quick-check',
        'name': 'Fast keyword-only check',
        'summary': 'Stage 1 enterprise triage. Keyword + regex match under 1 ms. High recall; decides whether to escalate to the full rubric.',
        'request_shape': {
            'text': 'str (required)',
        },
        'response_shape': {
            'should_trigger': 'bool',
            'score': 'float in [0, 1]',
            'matched_keywords': 'list[str]',
            'matched_patterns': 'list[str]',
            'category_hints': 'list[str]',
        },
        'curl_example': (
            \"curl -X POST http://localhost:8080/api/v1/quick-check \\\\\\n\"
            \"  -H 'Content-Type: application/json' \\\\\\n\"
            '  -d \\'{\"text\": \"Agency holds passport until fees paid\"}\\''
        ),
        'python_example': (
            \"import requests\\n\"
            \"r = requests.post('http://localhost:8080/api/v1/quick-check', json={\\n\"
            \"    'text': 'Agency holds passport until fees paid',\\n\"
            \"})\\n\"
            \"print(r.json()['should_trigger'], r.json()['matched_keywords'])\"
        ),
    },
    {
        'method': 'GET',
        'path': '/api/v1/domains',
        'name': 'List available domain packs',
        'summary': 'Return metadata for every domain pack loaded in the current process. Ships with trafficking; future releases add tax_evasion and financial_crime.',
        'request_shape': {},
        'response_shape': {
            'id': 'str',
            'display_name': 'str',
            'version': 'str',
            'description': 'str',
            'n_rubrics': 'int',
            'categories': 'list[str]',
        },
        'curl_example': 'curl http://localhost:8080/api/v1/domains',
        'python_example': (
            \"import requests\\n\"
            \"r = requests.get('http://localhost:8080/api/v1/domains')\\n\"
            \"for d in r.json():\\n\"
            \"    print(d['id'], d['n_rubrics'], 'rubrics')\"
        ),
    },
    {
        'method': 'GET',
        'path': '/api/v1/rubrics',
        'name': 'List available rubrics',
        'summary': 'Return metadata for every rubric the scorer has loaded (name, category, criteria count, weight).',
        'request_shape': {},
        'response_shape': {
            'name': 'str',
            'category': 'str',
            'n_criteria': 'int',
            'weight': 'float',
        },
        'curl_example': 'curl http://localhost:8080/api/v1/rubrics',
        'python_example': (
            \"import requests\\n\"
            \"r = requests.get('http://localhost:8080/api/v1/rubrics')\\n\"
            \"print(len(r.json()), 'rubrics loaded')\"
        ),
    },
    {
        'method': 'GET',
        'path': '/api/v1/stats',
        'name': 'Aggregate usage stats',
        'summary': 'Report totals for analyses since startup: grade distribution, action distribution, top indicator frequencies, rubrics loaded, uptime.',
        'request_shape': {},
        'response_shape': {
            'total_analyses': 'int',
            'analyses_today': 'int',
            'grade_distribution': 'dict[str, int]',
            'action_distribution': 'dict[str, int]',
            'mean_score': 'float',
            'top_indicators': 'list[{indicator, count}]',
            'rubrics_loaded': 'int',
            'uptime_seconds': 'float',
        },
        'curl_example': 'curl http://localhost:8080/api/v1/stats',
        'python_example': (
            \"import requests\\n\"
            \"r = requests.get('http://localhost:8080/api/v1/stats')\\n\"
            \"print(r.json()['total_analyses'], 'analyses since startup')\"
        ),
    },
    {
        'method': 'GET',
        'path': '/api/v1/health',
        'name': 'Liveness probe',
        'summary': 'Minimal readiness + liveness check for load balancers and orchestrators.',
        'request_shape': {},
        'response_shape': {
            'status': 'str (literal "ok")',
            'version': 'str',
            'rubrics_loaded': 'int',
            'model_id': 'str',
            'uptime_seconds': 'float',
        },
        'curl_example': 'curl http://localhost:8080/api/v1/health',
        'python_example': (
            \"import requests\\n\"
            \"r = requests.get('http://localhost:8080/api/v1/health')\\n\"
            \"print(r.json()['status'], r.json()['version'])\"
        ),
    },
    {
        'method': 'GET',
        'path': '/',
        'name': 'HTML dashboard',
        'summary': 'Single-page operator dashboard: text box, rubric picker, live results, example prompts. Rendered server-side as HTML.',
        'request_shape': {},
        'response_shape': {
            'Content-Type': 'text/html',
            'body': 'HTML document (no JSON contract)',
        },
        'curl_example': 'curl http://localhost:8080/',
        'python_example': (
            \"import requests\\n\"
            \"r = requests.get('http://localhost:8080/')\\n\"
            \"print(r.headers['content-type'], len(r.text), 'bytes')\"
        ),
    },
]

print(f'{len(ENDPOINTS)} endpoints catalogued')
print()
print(f'{\"Method\":<6} {\"Path\":<34} Name')
print('-' * 90)
for ep in ENDPOINTS:
    print(f'{ep[\"method\"]:<6} {ep[\"path\"]:<34} {ep[\"name\"]}')
"""


STEP_2_INTRO = """---

## 2. Spin up a local TestClient (optional)

When the DueCare demo package is installed, <code>fastapi.testclient.TestClient</code> imports the FastAPI app directly and calls endpoints in-process, so every subsection below renders live JSON output. When the package is missing on the Kaggle CPU kernel, the cells fall back to scripted sample responses so the tour still reads end-to-end.
"""


TESTCLIENT_CODE = """CLIENT_AVAILABLE = False
client = None
client_message = ''

try:
    from fastapi.testclient import TestClient
    try:
        from duecare.demo.api import app  # type: ignore
    except Exception:
        try:
            import sys
            from pathlib import Path as _Path
            repo_root = _Path('.').resolve()
            if (repo_root / 'src' / 'demo' / 'app.py').exists():
                sys.path.insert(0, str(repo_root))
                from src.demo.app import app  # type: ignore
            else:
                raise ImportError('demo app not on path')
        except Exception as inner_exc:
            raise inner_exc
    client = TestClient(app)
    CLIENT_AVAILABLE = bool(client)
    client_message = 'LIVE TestClient bound to the DueCare demo app (in-process, no server needed)'
except Exception as exc:
    CLIENT_AVAILABLE = False
    client = None
    client_message = (
        f'SCRIPTED fallback ({exc.__class__.__name__}: {exc}). '
        'Sample response bodies will render below; install the DueCare demo package '
        'to switch to live TestClient output.'
    )

print(client_message)
print(f'CLIENT_AVAILABLE = {CLIENT_AVAILABLE}')
"""


STEP_3_INTRO = """---

## 3. POST /api/v1/analyze - one-prompt safety analysis

The primary endpoint behind the video demo. One text in; a grade, an action, indicators, warning text, legal refs, and resource links out. Scored against every rubric loaded by the WeightedRubricScorer.
"""


ANALYZE_CODE = """import json
ANALYZE_REQUEST = {
    'text': 'My recruitment agency is charging me six months of wages as a placement fee and will hold my passport until it is paid.',
    'context': 'chat',
    'jurisdiction': 'PH_HK',
    'language': 'en',
}
ANALYZE_SAMPLE_RESPONSE = {
    'score': 0.12,
    'grade': 'worst',
    'action': 'block',
    'indicators': ['excessive_placement_fee', 'passport_retention', 'salary_deduction_scheme'],
    'warning_text': 'This arrangement shows multiple trafficking indicators. Do not accept.',
    'legal_refs': ['ILO C181 Article 7 (no worker-paid fees)', 'RA 8042 (PH)', 'Saudi Labor Law Art. 40'],
    'resources': [
        {'name': 'POEA Hotline', 'number': '1343', 'url': None, 'jurisdiction': 'PH'},
        {'name': 'BP2MI', 'number': None, 'url': 'https://bp2mi.go.id', 'jurisdiction': 'ID'},
    ],
    'rubric_results': [],
}

ep = next(e for e in ENDPOINTS if e['path'] == '/api/v1/analyze')
print(f'== {ep[\"method\"]} {ep[\"path\"]} ==')
print()
print('-- curl --')
print(ep['curl_example'])
print()
print('-- Python --')
print(ep['python_example'])
print()
print('-- Response --')
if CLIENT_AVAILABLE:
    try:
        resp = client.post('/api/v1/analyze', json=ANALYZE_REQUEST)
        payload = resp.json()
        print(f'[LIVE TestClient] status={resp.status_code}')
        print(json.dumps({k: payload.get(k) for k in ('score', 'grade', 'action', 'indicators')}, indent=2))
    except Exception as exc:
        print(f'[LIVE call failed: {exc.__class__.__name__}] Scripted sample below:')
        print(json.dumps(ANALYZE_SAMPLE_RESPONSE, indent=2))
else:
    print('[SCRIPTED sample]')
    print(json.dumps(ANALYZE_SAMPLE_RESPONSE, indent=2))
"""


STEP_4_INTRO = """---

## 4. POST /api/v1/rag-context - retrieve legal and corridor context

The retrieval endpoint that feeds the guided-context mode in [260 RAG Comparison](""" + URL_260 + """). Given a query, returns up to <code>top_k</code> citation-bracketed entries from the DueCare knowledge base (ILO conventions, corridor fingerprints, scheme fingerprints) for injection into Gemma's prompt.
"""


RAG_CODE = """import json
RAG_REQUEST = {
    'text': 'Is a placement fee legal for a Filipino domestic worker going to Hong Kong?',
    'top_k': 5,
}
RAG_SAMPLE_RESPONSE = {
    'query': RAG_REQUEST['text'],
    'context': (
        '[1] ILO C181 Article 7: Private employment agencies shall not charge workers... '
        '[2] RA 8042 (PH Migrant Workers Act): Prohibits placement fees beyond one-month salary... '
        '[3] PH_HK corridor fingerprint: standard fee is HKD 0 (employer-paid)... '
        '[4] Scheme fingerprint: six-month salary deduction is a salary-skimming pattern... '
        '[5] POEA Memorandum Circular No. 02 s.2018: no worker-paid placement fees for HK deployment...'
    ),
    'n_entries': 142,
    'n_retrieved': 5,
}

ep = next(e for e in ENDPOINTS if e['path'] == '/api/v1/rag-context')
print(f'== {ep[\"method\"]} {ep[\"path\"]} ==')
print()
print('-- curl --')
print(ep['curl_example'])
print()
print('-- Python --')
print(ep['python_example'])
print()
print('-- Response --')
if CLIENT_AVAILABLE:
    try:
        resp = client.post('/api/v1/rag-context', json=RAG_REQUEST)
        payload = resp.json()
        print(f'[LIVE TestClient] status={resp.status_code}')
        print(json.dumps({k: payload.get(k) for k in ('query', 'n_entries', 'n_retrieved')}, indent=2))
        print('context preview:', (payload.get('context') or '')[:300])
    except Exception as exc:
        print(f'[LIVE call failed: {exc.__class__.__name__}] Scripted sample below:')
        print(json.dumps(RAG_SAMPLE_RESPONSE, indent=2))
else:
    print('[SCRIPTED sample]')
    print(json.dumps(RAG_SAMPLE_RESPONSE, indent=2))
"""


STEP_5_INTRO = """---

## 5. POST /api/v1/function-call - native Gemma 4 tool call

Gemma 4's native function calling exercised against the DueCare tool surface. The server registers five tools (<code>check_fee_legality</code>, <code>check_legal_framework</code>, <code>lookup_hotline</code>, <code>identify_trafficking_indicators</code>, <code>score_exploitation_risk</code>) and routes Gemma's tool choices to their Python implementations. When Ollama is not present, the endpoint still returns a deterministic tool-call trace so the demo pathway stays visible.
"""


FC_CODE = """import json
FC_REQUEST = {
    'text': 'The agency charges PHP 50000 placement fee for Hong Kong domestic work.',
}
FC_SAMPLE_RESPONSE = {
    'input': FC_REQUEST['text'],
    'tools_available': [
        'check_fee_legality',
        'check_legal_framework',
        'lookup_hotline',
        'identify_trafficking_indicators',
        'score_exploitation_risk',
    ],
    'tools_called': 5,
    'results': [
        {'tool': 'score_exploitation_risk', 'result': {'risk': 'high', 'score': 0.85}},
        {'tool': 'identify_trafficking_indicators', 'result': {'indicators': ['excessive_fee', 'PH_HK_fee_violation']}},
        {'tool': 'check_fee_legality', 'result': {'country': 'PH', 'legal': False, 'reason': 'Exceeds one-month cap per RA 8042'}},
        {'tool': 'lookup_hotline', 'result': {'country': 'PH', 'number': '1343', 'agency': 'POEA'}},
        {'tool': 'check_legal_framework', 'result': {'jurisdiction': 'PH', 'scenario': 'recruitment_fee', 'statute': 'RA 8042 section 6'}},
    ],
}

ep = next(e for e in ENDPOINTS if e['path'] == '/api/v1/function-call')
print(f'== {ep[\"method\"]} {ep[\"path\"]} ==')
print()
print('-- curl --')
print(ep['curl_example'])
print()
print('-- Python --')
print(ep['python_example'])
print()
print('-- Response --')
if CLIENT_AVAILABLE:
    try:
        resp = client.post('/api/v1/function-call', json=FC_REQUEST)
        payload = resp.json()
        print(f'[LIVE TestClient] status={resp.status_code}')
        print(json.dumps({
            'tools_available': payload.get('tools_available'),
            'tools_called': payload.get('tools_called'),
            'first_result': (payload.get('results') or [{}])[0],
        }, indent=2, default=str))
    except Exception as exc:
        print(f'[LIVE call failed: {exc.__class__.__name__}] Scripted sample below:')
        print(json.dumps(FC_SAMPLE_RESPONSE, indent=2))
else:
    print('[SCRIPTED sample]')
    print(json.dumps(FC_SAMPLE_RESPONSE, indent=2))
"""


STEP_6_INTRO = """---

## 6. POST /api/v1/analyze-document - multimodal document analysis

Evidence surface for the "Gemma 4's unique features are load-bearing" claim. In production the endpoint accepts an image; in this tour it takes OCR-extracted text and returns the same structured risk, extracted_fields, indicator_flags, and timeline markers payload so adopters can prototype against either input channel.
"""


DOC_CODE = """import json
DOC_REQUEST = {
    'text': 'Employment Contract. Employee: Maria R. (composite). Employer to retain passport for the duration of the contract period. Placement fee: HKD 20000, deducted over 7 months.',
    'context': 'contract',
}
DOC_SAMPLE_RESPONSE = {
    'document_type': 'employment_contract',
    'risk_level': 'HIGH',
    'findings': [
        'Document references worker-paid recruitment or placement fees (HKD 20000).',
        'Document describes repayment or deductions taken directly from wages.',
        'Document includes passport or identity-document retention language.',
    ],
    'indicator_flags': ['passport_retention', 'worker_paid_placement_fee', 'salary_deduction_scheme'],
    'legal_refs': ['ILO C181 Art. 7', 'RA 10022', 'Palermo Protocol'],
    'recommendation': 'Pause further payments or contract steps, preserve the document, and escalate it to a labor office or trusted NGO before proceeding.',
    'extracted_fields': {
        'document_type': 'employment_contract',
        'amounts': ['HKD 20000'],
        'dates': [],
        'countries': ['Hong Kong'],
        'corridor_candidates': ['PH_HK'],
    },
    'timeline_markers': [],
    'resources': [
        {'name': 'Immigration Department Help Desk', 'number': '2824 6111', 'jurisdiction': 'HK'},
        {'name': 'IOM Migration Health', 'number': '+41 22 717 9111', 'jurisdiction': 'INTL'},
    ],
    'confidence': 0.73,
}

ep = next(e for e in ENDPOINTS if e['path'] == '/api/v1/analyze-document')
print(f'== {ep[\"method\"]} {ep[\"path\"]} ==')
print()
print('-- curl --')
print(ep['curl_example'])
print()
print('-- Python --')
print(ep['python_example'])
print()
print('-- Response --')
if CLIENT_AVAILABLE:
    try:
        resp = client.post('/api/v1/analyze-document', json=DOC_REQUEST)
        payload = resp.json()
        print(f'[LIVE TestClient] status={resp.status_code}')
        print(json.dumps(payload, indent=2, default=str)[:900])
    except Exception as exc:
        print(f'[LIVE call failed: {exc.__class__.__name__}] Scripted sample below:')
        print(json.dumps(DOC_SAMPLE_RESPONSE, indent=2))
else:
    print('[SCRIPTED sample]')
    print(json.dumps(DOC_SAMPLE_RESPONSE, indent=2))
"""


STEP_7_CASE_INTRO = """---

## 7. POST /api/v1/migration-case - NGO case bundle workflow

This is the operator-facing NGO surface the demo was missing before this rebuild. A case worker can bundle receipts, contracts, and recruiter chats from one migration journey; the endpoint then classifies each document, orders the timeline, retrieves legal context, and drafts complaint-ready text without leaving the deployment surface.
"""


CASE_CODE = """import json
CASE_REQUEST = {
    'case_id': 'case-demo-001',
    'corridor': 'PH_HK',
    'documents': [
        {
            'document_id': 'doc-01',
            'title': 'Agency receipt',
            'context': 'receipt',
            'captured_at': '2026-01-05',
            'text': 'Receipt for placement fee: HKD 20000 paid by worker before deployment.',
        },
        {
            'document_id': 'doc-02',
            'title': 'Employment contract',
            'context': 'contract',
            'captured_at': '2026-01-12',
            'text': 'Employer will retain passport during contract period and deduct fees over 7 months.',
        },
        {
            'document_id': 'doc-03',
            'title': 'Recruiter chat',
            'context': 'chat',
            'captured_at': '2026-01-15',
            'text': 'Pay the remaining fee now or you cannot leave. We will keep your passport until the debt is cleared.',
        },
    ],
}
CASE_SAMPLE_RESPONSE = {
    'case_id': 'case-demo-001',
    'corridor': 'PH_HK',
    'document_count': 3,
    'risk_level': 'HIGH',
    'detected_indicators': ['worker_paid_placement_fee', 'passport_retention', 'debt_bondage_risk'],
    'applicable_laws': ['ILO C181 Art. 7', 'RA 10022', 'Palermo Protocol'],
    'retrieved_context': '[legal_provision] ILO C181 Art. 7 ...',
    'timeline': [
        {'date': '2026-01-05', 'label': 'Payment demand recorded', 'document_id': 'doc-01', 'description': 'Document references worker-paid recruitment or placement fees (HKD 20000).'},
        {'date': '2026-01-12', 'label': 'Contract terms recorded', 'document_id': 'doc-02', 'description': 'Document includes passport or identity-document retention language.'},
        {'date': '2026-01-15', 'label': 'Recruitment conversation captured', 'document_id': 'doc-03', 'description': 'Document creates or acknowledges a debt that could tie the worker to the job.'},
    ],
    'recommended_actions': [
        'Preserve the original files, export metadata, and keep a clean index of what each document shows.',
        'Freeze further worker-paid fees or deductions until a labor-law review confirms they are lawful.',
    ],
    'complaint_templates': [
        {'name': 'ngo_intake_summary', 'audience': 'NGO case worker', 'text': 'Case ID: case-demo-001 ...'},
    ],
}

ep = next(e for e in ENDPOINTS if e['path'] == '/api/v1/migration-case')
print(f'== {ep["method"]} {ep["path"]} ==')
print()
print('-- curl --')
print(ep['curl_example'])
print()
print('-- Python --')
print(ep['python_example'])
print()
print('-- Response --')
if CLIENT_AVAILABLE:
    try:
        resp = client.post('/api/v1/migration-case', json=CASE_REQUEST)
        payload = resp.json()
        print(f'[LIVE TestClient] status={resp.status_code}')
        print(json.dumps(payload, indent=2, default=str)[:1500])
    except Exception as exc:
        print(f'[LIVE call failed: {exc.__class__.__name__}] Scripted sample below:')
        print(json.dumps(CASE_SAMPLE_RESPONSE, indent=2))
else:
    print('[SCRIPTED sample]')
    print(json.dumps(CASE_SAMPLE_RESPONSE, indent=2))
"""


STEP_7_INTRO = """---

## 8. POST /api/v1/evaluate - full Gemma rubric evaluation

When Ollama is running locally with a Gemma 4 checkpoint pulled, the evaluate endpoint runs the full plain / RAG / guided comparison the video shows, and returns all three modes side by side. On the Kaggle CPU kernel Ollama is not available, so the scripted response below mirrors the schema a live run would emit.
"""


EVAL_CODE = """import json
EVAL_REQUEST = {
    'text': 'What should I do if my recruitment agency is charging me six months of wages?',
    'mode': 'compare',
    'model': 'gemma4:e4b',
}
EVAL_SAMPLE_RESPONSE = {
    'plain':  {'response': 'It depends on the jurisdiction...', 'score': 0.40, 'grade': 'neutral', 'mode_used': 'plain',  'latency_ms': 1280},
    'rag':    {'response': 'ILO C181 prohibits worker-paid fees...', 'score': 0.72, 'grade': 'good',    'mode_used': 'rag',    'latency_ms': 1510},
    'guided': {'response': 'I cannot recommend accepting these terms. ILO C181...', 'score': 0.88, 'grade': 'best', 'mode_used': 'guided', 'latency_ms': 1420},
}

ep = next(e for e in ENDPOINTS if e['path'] == '/api/v1/evaluate')
print(f'== {ep[\"method\"]} {ep[\"path\"]} ==')
print()
print('-- curl --')
print(ep['curl_example'])
print()
print('-- Python --')
print(ep['python_example'])
print()
print('-- Response --')
if CLIENT_AVAILABLE:
    try:
        resp = client.post('/api/v1/evaluate', json=EVAL_REQUEST)
        payload = resp.json()
        print(f'[LIVE TestClient] status={resp.status_code}')
        print(json.dumps(payload, indent=2, default=str)[:900])
    except Exception as exc:
        print(f'[LIVE call failed: {exc.__class__.__name__}] Scripted sample below:')
        print(json.dumps(EVAL_SAMPLE_RESPONSE, indent=2))
else:
    print('[SCRIPTED sample] (live run requires ollama + gemma4:e4b)')
    print(json.dumps(EVAL_SAMPLE_RESPONSE, indent=2))
"""


STEP_8_INTRO = """---

## 9. POST /api/v1/quick-check - fast keyword triage

Stage 1 of the enterprise waterfall. Runs on every message to decide whether to escalate to the full rubric or the Gemma 4 analysis. Latency budget is under 1 ms; high recall is favored over precision so the downstream rubric gets to make the actual call.
"""


QUICK_CODE = """import json
QUICK_REQUEST = {'text': 'Agency holds passport until fees are paid'}
QUICK_SAMPLE_RESPONSE = {
    'should_trigger': True,
    'score': 0.62,
    'matched_keywords': ['passport', 'fees', 'holds'],
    'matched_patterns': ['passport_retention'],
    'category_hints': ['vulnerability_recruitment_violations'],
}

ep = next(e for e in ENDPOINTS if e['path'] == '/api/v1/quick-check')
print(f'== {ep[\"method\"]} {ep[\"path\"]} ==')
print()
print('-- curl --')
print(ep['curl_example'])
print()
print('-- Python --')
print(ep['python_example'])
print()
print('-- Response --')
if CLIENT_AVAILABLE:
    try:
        resp = client.post('/api/v1/quick-check', json=QUICK_REQUEST)
        payload = resp.json()
        print(f'[LIVE TestClient] status={resp.status_code}')
        print(json.dumps(payload, indent=2, default=str))
    except Exception as exc:
        print(f'[LIVE call failed: {exc.__class__.__name__}] Scripted sample below:')
        print(json.dumps(QUICK_SAMPLE_RESPONSE, indent=2))
else:
    print('[SCRIPTED sample]')
    print(json.dumps(QUICK_SAMPLE_RESPONSE, indent=2))
"""


STEP_9_INTRO = """---

## 10. HTML summary table of all 13 endpoints

The seven subsections above covered the representative slice. The table below enumerates every route the demo app exposes so adopters can see the full surface in one place.
"""


SUMMARY_TABLE_CODE = """from IPython.display import HTML, display

rows_html = []
for ep in ENDPOINTS:
    req_shape = ', '.join(f'<code>{k}</code>' for k in ep['request_shape'].keys()) or '(none)'
    resp_shape = ', '.join(f'<code>{k}</code>' for k in ep['response_shape'].keys())
    rows_html.append(
        '    <tr>'
        f'<td style=\"padding: 6px 10px;\"><code>{ep[\"method\"]}</code></td>'
        f'<td style=\"padding: 6px 10px;\"><code>{ep[\"path\"]}</code></td>'
        f'<td style=\"padding: 6px 10px;\">{ep[\"summary\"]}</td>'
        f'<td style=\"padding: 6px 10px;\">{req_shape}</td>'
        f'<td style=\"padding: 6px 10px;\">{resp_shape}</td>'
        '</tr>'
    )

table_html = (
    '<table style=\"width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;\">\\n'
    '  <thead>\\n'
    '    <tr style=\"background: #f6f8fa; border-bottom: 2px solid #d1d5da;\">\\n'
    '      <th style=\"padding: 6px 10px; text-align: left; width: 8%;\">Method</th>\\n'
    '      <th style=\"padding: 6px 10px; text-align: left; width: 22%;\">Path</th>\\n'
    '      <th style=\"padding: 6px 10px; text-align: left; width: 35%;\">Summary</th>\\n'
    '      <th style=\"padding: 6px 10px; text-align: left; width: 17%;\">Request shape</th>\\n'
    '      <th style=\"padding: 6px 10px; text-align: left; width: 18%;\">Response shape</th>\\n'
    '    </tr>\\n'
    '  </thead>\\n'
    '  <tbody>\\n'
    + '\\n'.join(rows_html)
    + '\\n  </tbody>\\n'
    '</table>'
)
display(HTML(table_html))
"""


STEP_10_INTRO = """---

## 11. Call-graph diagram (endpoint -> agent / tool)

The sankey below renders which endpoints flow into which downstream agents and tools. It is the visual restatement of the table above: every request path resolves to a concrete handler whose dependencies are named so a reader can trace a deployment feature end-to-end without opening the source.
"""


SANKEY_CODE = """import plotly.graph_objects as go

# Edges: source endpoint -> downstream agent / tool. One edge per
# canonical call. Weights are illustrative (higher = hotter path in
# the demo flow).
EDGES = [
    ('/api/v1/analyze',          'WeightedRubricScorer',    8),
    ('/api/v1/analyze',          'AnalysisLog',             4),
    ('/api/v1/batch',            'WeightedRubricScorer',    6),
    ('/api/v1/batch',            'BatchSummaryBuilder',     4),
    ('/api/v1/evaluate',         'Judge agent',             7),
    ('/api/v1/evaluate',         'Scorer agent',            5),
    ('/api/v1/evaluate',         'Ollama / Gemma 4',        6),
    ('/api/v1/function-call',    'Coordinator agent',       8),
    ('/api/v1/function-call',    'Tool: score_exploitation_risk',      4),
    ('/api/v1/function-call',    'Tool: identify_trafficking_indicators', 4),
    ('/api/v1/function-call',    'Tool: check_fee_legality',           3),
    ('/api/v1/function-call',    'Tool: lookup_hotline',               3),
    ('/api/v1/function-call',    'Tool: check_legal_framework',        3),
    ('/api/v1/analyze-document', 'DocumentAnalyzer',        6),
    ('/api/v1/analyze-document', 'Gemma 4 multimodal',      5),
    ('/api/v1/migration-case',   'Case orchestrator',       8),
    ('/api/v1/migration-case',   'DocumentAnalyzer',        6),
    ('/api/v1/migration-case',   'RAGStore',                5),
    ('/api/v1/migration-case',   'Tool: score_exploitation_risk',      4),
    ('/api/v1/migration-case',   'Tool: check_legal_framework',        3),
    ('/api/v1/migration-case',   'Tool: lookup_hotline',               3),
    ('/api/v1/rag-context',      'RAGStore',                6),
    ('/api/v1/rag-context',      'Retriever',               5),
    ('/api/v1/quick-check',      'QuickFilter',             6),
    ('/api/v1/domains',          'DomainPack registry',     3),
    ('/api/v1/rubrics',          'WeightedRubricScorer',    3),
    ('/api/v1/stats',            'AnalysisLog',             3),
    ('/api/v1/health',           'Lifespan state',          2),
    ('/',                        'HTML renderer',           3),
]

nodes = []
node_index = {}
for src_node, dst_node, _ in EDGES:
    for n in (src_node, dst_node):
        if n not in node_index:
            node_index[n] = len(nodes)
            nodes.append(n)

src_idx = [node_index[s] for s, _, _ in EDGES]
dst_idx = [node_index[d] for _, d, _ in EDGES]
values  = [v for _, _, v in EDGES]

# Color endpoints (left column) blue; downstream nodes (right column)
# green or orange depending on whether they are agents (model-backed)
# or tools / stores (deterministic).
AGENT_NODES = {'Judge agent', 'Scorer agent', 'Coordinator agent', 'Case orchestrator', 'DocumentAnalyzer', 'Ollama / Gemma 4', 'Gemma 4 multimodal'}
def _node_color(name: str) -> str:
    if name.startswith('/'):
        return '#3b82f6'
    if name in AGENT_NODES:
        return '#10b981'
    return '#f97316'

node_colors = [_node_color(n) for n in nodes]

fig = go.Figure(go.Sankey(
    arrangement='snap',
    node=dict(
        label=nodes,
        color=node_colors,
        pad=14,
        thickness=16,
        line=dict(color='#1f2937', width=0.5),
    ),
    link=dict(source=src_idx, target=dst_idx, value=values),
))
fig.update_layout(
    title=dict(text='DueCare API call graph: endpoints -> agents and tools', font_size=16),
    template='plotly_white',
    height=640,
    width=980,
    margin=dict(t=60, b=40, l=20, r=20),
)
fig.show()
"""


TROUBLESHOOTING = troubleshooting_table_html([
    (
        "Demo module not importable (<code>CLIENT_AVAILABLE = False</code>).",
        "Expected on the Kaggle CPU kernel when <code>duecare-llm</code> is not installed. "
        "The notebook falls back to scripted sample responses automatically; install the "
        f"<code>duecare-llm</code> meta package or attach the <code>{WHEELS_DATASET}</code> "
        "wheels dataset to switch to live TestClient output.",
    ),
    (
        "An endpoint returns <code>500</code> from the TestClient.",
        "Inspect the <code>resp.text</code> body for the server-side traceback. The most "
        "common cause is a missing rubric config (<code>configs/duecare/domains/trafficking/rubrics/</code>) "
        "or an unattached knowledge base for <code>/api/v1/rag-context</code>. Fix upstream "
        "and rerun the cell.",
    ),
    (
        "A curl example hangs or times out.",
        "The curl snippets assume <code>http://localhost:8080</code>. If you are running "
        "the app on another host or port, edit the URL; if no server is running, the "
        "TestClient cells are the intended path.",
    ),
    (
        "<code>TestClient</code> raises on import.",
        "Requires <code>fastapi &gt;= 0.100</code> and <code>httpx</code>. Both come with "
        "the <code>duecare-llm</code> meta package; if you installed only <code>duecare-llm-core</code> "
        "you will need to <code>pip install httpx</code> as well.",
    ),
    (
        "Response shape does not match the table.",
        "Pydantic models evolve between releases. The <code>ENDPOINTS</code> catalog is "
        "the source of truth for this notebook; cross-check against <code>src/demo/models.py</code> "
        "and open an issue if a field disappeared or renamed without a deprecation.",
    ),
])


SUMMARY = f"""---

## What just happened

- Catalogued all 13 FastAPI endpoints the DueCare demo app exposes, with method, path, summary, request shape, response shape, curl example, and Python <code>requests</code> snippet captured in a typed <code>ENDPOINTS</code> list.
- Bound an in-process <code>fastapi.testclient.TestClient</code> when possible so seven representative endpoints returned live JSON; fell back to scripted responses otherwise so the tour always renders.
- Walked <code>/api/v1/analyze</code>, <code>/api/v1/rag-context</code>, <code>/api/v1/function-call</code>, <code>/api/v1/analyze-document</code>, <code>/api/v1/migration-case</code>, <code>/api/v1/evaluate</code>, <code>/api/v1/quick-check</code> with full curl + Python + response output.
- Rendered an HTML summary table covering the full 13-endpoint surface.
- Rendered a Plotly sankey of the endpoint -> agent / tool call graph so the deployment story is visible at a glance.

### Key findings

1. **Every deployment feature the video names resolves to one of these 13 routes.** No hidden surface; no private endpoints; nothing held back for the demo.
2. **The seven representative endpoints exercise both Gemma 4's unique features** (function-call for native tool calling, analyze-document for multimodal, migration-case for case-level orchestration) and the supporting surfaces (analyze for rubric, rag-context for retrieval, evaluate for the three-mode comparison, quick-check for waterfall stage 1).
3. **The TestClient path is the safest demo mode.** No uvicorn, no port, no firewall issues; the same app object the server mounts is the one the tests drive, so behavior stays identical between the notebook and production.
4. **The sankey makes the orchestration story legible in one chart.** /function-call flows into the Coordinator agent, /migration-case fans into the Case orchestrator plus retrieval and hotline/legal tools, /evaluate flows into Judge + Scorer agents that share the Ollama backend, and /rag-context feeds the Retriever that every guided mode depends on.

---

## Troubleshooting

{TROUBLESHOOTING}

---

## Next

- **Continue the section:** [650 Custom Domain Walkthrough]({URL_650}) shows adopters how to plug a new domain pack into these same endpoints.
- **Section close:** [899 Solution Surfaces Conclusion]({URL_899}).
- **Prior step:** [610 Submission Walkthrough]({URL_610}).
- **Dashboards the API feeds:** [600 Results Dashboard]({URL_600}).
- **Back to navigation (optional):** [000 Index]({URL_000}).
"""


def build() -> None:
    cells = [
        md(HEADER),
        md(STEP_1_INTRO),
        code(ENDPOINTS_CODE),
        md(STEP_2_INTRO),
        code(TESTCLIENT_CODE),
        md(STEP_3_INTRO),
        code(ANALYZE_CODE),
        md(STEP_4_INTRO),
        code(RAG_CODE),
        md(STEP_5_INTRO),
        code(FC_CODE),
        md(STEP_6_INTRO),
        code(DOC_CODE),
        md(STEP_7_CASE_INTRO),
        code(CASE_CODE),
        md(STEP_7_INTRO),
        code(EVAL_CODE),
        md(STEP_8_INTRO),
        code(QUICK_CODE),
        md(STEP_9_INTRO),
        code(SUMMARY_TABLE_CODE),
        md(STEP_10_INTRO),
        code(SANKEY_CODE),
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
        "    'API tour handoff >>> Continue to 650 Custom Domain Walkthrough: '\n"
        f"    '{URL_650}'\n"
        "    '. Section close: 899 Solution Surfaces Conclusion: '\n"
        f"    '{URL_899}'\n"
        "    '.'\n"
        ")\n"
    )
    patch_final_print_cell(
        nb,
        final_print_src=final_print_src,
        marker="API tour handoff >>>",
    )

    # Inject json import at the top for the live/scripted JSON pretty-printing
    # cells. harden_notebook rewrites sources; do any additional source-level
    # tweaks after the fact here if needed.

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
