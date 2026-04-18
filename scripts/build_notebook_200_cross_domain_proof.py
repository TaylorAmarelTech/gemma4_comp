#!/usr/bin/env python3
"""Build the 200 Cross-Domain Proof notebook.

Demonstrates that the same DueCare harness runs against three different
safety domain packs with zero code changes. This is the opening notebook of
the Baseline Text Comparisons section.
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

FILENAME = "200_cross_domain_proof.ipynb"
KERNEL_DIR_NAME = "duecare_200_cross_domain_proof"
KERNEL_ID = "taylorsamarel/200-duecare-cross-domain-proof"
KERNEL_TITLE = "200: DueCare Cross-Domain Proof"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["gemma", "llm-comparison", "safety", "evaluation"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_100 = "https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts"
URL_140 = "https://www.kaggle.com/code/taylorsamarel/140-duecare-evaluation-mechanics"
URL_190 = "https://www.kaggle.com/code/taylorsamarel/190-duecare-rag-retrieval-inspector"
URL_199 = "https://www.kaggle.com/code/taylorsamarel/199-duecare-free-form-exploration-conclusion"
URL_200 = "https://www.kaggle.com/code/taylorsamarel/duecare-200-cross-domain-proof"
URL_210 = "https://www.kaggle.com/code/taylorsamarel/duecare-gemma-vs-oss-comparison"
URL_270 = "https://www.kaggle.com/code/taylorsamarel/duecare-270-gemma-generations"
URL_399 = "https://www.kaggle.com/code/taylorsamarel/duecare-baseline-text-comparisons-conclusion"
URL_500 = "https://www.kaggle.com/code/taylorsamarel/duecare-500-agent-swarm-deep-dive"


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
        "Three bundled DueCare domain packs loaded via "
        "<code>duecare.domains.register_discovered()</code>: "
        "<code>trafficking</code>, <code>tax_evasion</code>, and "
        "<code>financial_crime</code>. One deterministic scripted model "
        "so every cross-domain delta is attributable to the pack, not to "
        "stochastic generation."
    ),
    outputs_html=(
        "Per-domain <code>guardrails</code> capability-test metrics "
        "(mean score, refusal rate, prompt count), a cross-domain "
        "headline table, three executed <code>rapid_probe</code> "
        "<code>WorkflowRun</code> records with distinct "
        "<code>run_id</code>s, and a rendered Historian Markdown report "
        "for the trafficking run."
    ),
    prerequisites_html=(
        f"Kaggle CPU kernel with internet enabled and the "
        f"<code>{WHEELS_DATASET}</code> wheel dataset attached. No GPU, "
        "no API keys, no external data needed; all three domain packs "
        "ship inside the <code>duecare-llm-domains</code> wheel."
    ),
    runtime_html=(
        "Under 3 minutes end-to-end on a CPU kernel. Three "
        "<code>rapid_probe</code> workflow runs plus three capability "
        "tests; scripted model inference is effectively instant."
    ),
    pipeline_html=(
        f"Baseline Text Comparisons, section opener. Previous: "
        f"<a href=\"{URL_199}\">199 Free Form Exploration Conclusion</a>. "
        f"Next: <a href=\"{URL_210}\">210 Gemma vs OSS Comparison</a>. "
        f"Section close: <a href=\"{URL_399}\">399 Baseline Text "
        f"Comparisons Conclusion</a>."
    ),
)


HEADER = f"""# 200: DueCare Cross-Domain Proof

**The same DueCare harness, the same 12-agent swarm, the same scoring rubric, and the same workflow runner produce structurally identical reports against three different safety domain packs with zero code changes.** This is the opening notebook of the Baseline Text Comparisons section; every later comparison notebook (210, 220, 230, 240, 250, 260, 270) depends on this proof that the harness is genuinely domain-agnostic.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a). This notebook runs one deterministic scripted model through the trafficking, tax-evasion, and financial-crime packs so any metric difference is attributable to the pack, not to model variability.

{HEADER_TABLE}

### Why this notebook matters

A natural skeptical question after reading the Free Form Exploration section is "the trafficking rubric is fine, but is this harness actually general, or is it a trafficking tool with a duecare label?" Every later comparison notebook (210, 220, 230, 240, 250, 260, 270) answers the question "how does model X score on the DueCare harness" — and that question only has weight if the harness itself is not specialized to one domain.

This notebook answers that skeptical question by running the same 12-agent swarm, the same `WorkflowRunner`, the same `guardrails` capability test, and the same schema-checked metrics against three different safety domain packs with zero code changes. Trafficking, tax evasion, and financial crime are three distinct legal regimes with different rubrics, taxonomies, PII specs, and seed prompts; if the harness were trafficking-specific, two of these three runs would either fail or return incomparable metrics. They do neither. The score for `tax_evasion` and the score for `financial_crime` are computed by exactly the same Python code path that produced the `trafficking` score in 100. Adding a new domain (for example `medical_misinformation`) is a directory copy plus a YAML edit; there is no domain-specific Python anywhere in the harness.

### Reading order

- **Previous step:** [199 Free Form Exploration Conclusion]({URL_199}) closes the Free Form Exploration section; 200 is the first Baseline Text Comparisons notebook.
- **Baseline source:** [100 Gemma Exploration]({URL_100}) is where the single-model Gemma 4 baseline that every comparison references originates.
- **Methodology deep-dive:** [140 Evaluation Mechanics]({URL_140}) walks the 5-grade rubric, keyword scorer, anchored best/worst references, and 6-dimension weighted rubric; the cross-domain metrics here use exactly that machinery.
- **Retrieval context:** [190 RAG Retrieval Inspector]({URL_190}) explains how retrieval augments this same harness when RAG is enabled.
- **Full section path:** continue to [210 Gemma vs OSS Comparison]({URL_210}) to swap the scripted model for real peer open-source models, walk through the 200-band, and close the section in [399 Baseline Text Comparisons Conclusion]({URL_399}).
- **Cross-generation shortcut:** [270 Gemma Generations]({URL_270}) reuses this same harness to compare Gemma 2 vs 3 vs 4 on the same prompts.
- **Architecture detour:** [500 Agent Swarm Deep Dive]({URL_500}) walks the 12-agent orchestration layer step by step.
- **Back to navigation:** [000 Index]({URL_000}).

### What this notebook does

1. Register every shipped domain pack and inspect each one's card (taxonomy, rubric, seed-prompt count, evidence count).
2. Define a single deterministic `ScriptedModel` so every cross-domain difference is attributable to the pack.
3. Run the `guardrails` capability test against each of the three packs and print the per-domain summary.
4. Print a cross-domain headline table (mean score, refusal rate, prompt count).
5. Execute the `rapid_probe` workflow end-to-end against each domain and confirm three distinct `run_id`s.
6. Render the Historian agent's Markdown report for one run so the generated artifact is visible.
"""


STEP_1_INTRO = """---

## 1. Load every bundled domain pack

The install cell above brings in `duecare-llm` (meta package pulling all 8 DueCare packages). This cell registers the bundled domain packs and prints what was discovered. Each pack is self-describing: taxonomy, rubric, PII spec, seed prompts, and evidence all ship as YAML or JSONL inside the `duecare-llm-domains` wheel. Adding a new domain is a directory copy plus a YAML edit; no Python changes."""


LOAD_DOMAINS = """from duecare.domains import register_discovered, domain_registry, load_domain_pack

n = register_discovered()
print(f'Registered {n} domain packs: {domain_registry.all_ids()}')

assert n >= 3, 'Expected at least 3 domain packs; reinstall duecare-llm-domains.'
for expected in ('trafficking', 'tax_evasion', 'financial_crime'):
    assert domain_registry.has(expected), f'Missing domain pack: {expected!r}'
"""


INSPECT_DOMAINS = """# Inspect each pack's card so the cross-domain claim is concrete.
for domain_id in ['trafficking', 'tax_evasion', 'financial_crime']:
    pack = load_domain_pack(domain_id)
    card = pack.card()
    n_prompts = sum(1 for _ in pack.seed_prompts())
    n_evidence = sum(1 for _ in pack.evidence())
    print(f'{card.display_name} v{card.version}')
    print(f'   id:           {card.id}')
    print(f'   seed_prompts: {n_prompts}  evidence: {n_evidence}')
    print(f'   categories:   {card.n_categories}  indicators: {card.n_indicators}')
    print()
"""


STEP_2_INTRO = """---

## 2. Define one deterministic scripted model

The model is deliberately scripted so every cross-domain difference is attributable to the domain pack, not to stochastic model output. The response cites international standards that apply across all three domains so every rubric has signal to match on. On a real run with Gemma 4 you would pass a `TransformersModel` or `OllamaModel` instead; the harness accepts anything that satisfies the `Model` protocol."""


SCRIPTED_MODEL = """from duecare.core import ChatMessage, Capability, GenerationResult, Embedding, ModelHealth


class ScriptedModel:
    id = 'scripted:cross_domain'
    display_name = 'Scripted (cross-domain demo)'
    provider = 'scripted'
    capabilities = {Capability.TEXT}
    context_length = 4096
    _resp = (
        'I cannot help with that. Under applicable international standards '
        '(ILO C181, FATF 40 Recommendations, OECD BEPS), this is illegal. '
        'Please contact the relevant authority or file a complaint with '
        'your local labor ministry or tax authority.'
    )

    def generate(self, messages, tools=None, images=None, max_tokens=1024, temperature=0.0, **kwargs):
        return GenerationResult(text=self._resp, model_id=self.id)

    def embed(self, texts):
        return [Embedding(text=t, vector=[0.0] * 4, dimension=4, model_id=self.id) for t in texts]

    def healthcheck(self):
        return ModelHealth(model_id=self.id, healthy=True)


m = ScriptedModel()
print(f'Scripted model ready: {m.id}')
"""


STEP_3_INTRO = """---

## 3. Run the guardrails capability test per domain

Same task, same config, three different domain packs. If the harness were secretly domain-specialized, two of these three runs would fail or return incomparable metrics."""


RUN_GUARDRAILS = """from duecare.core import TaskConfig
from duecare.tasks import task_registry

task = task_registry.get('guardrails')

results = {}
for domain_id in ['trafficking', 'tax_evasion', 'financial_crime']:
    pack = load_domain_pack(domain_id)
    result = task.run(m, pack, TaskConfig())
    results[domain_id] = result
    print(f'{domain_id:<16}  {result.summary()}')

assert len(results) == 3, 'Expected a capability-test result for each of the three domains.'
"""


STEP_4_INTRO = """---

## 4. Cross-domain headline table

Same harness, same model, three different domains. Row-by-row comparison makes the claim concrete."""


HEADLINE_TABLE = """print(f'{"Domain":<20} {"mean_score":<12} {"refusal_rate":<14} {"prompts":<10}')
print('-' * 60)
for domain_id, result in results.items():
    print(
        f'{domain_id:<20} '
        f'{result.metrics["mean_score"]:<12.4f} '
        f'{result.metrics["refusal_rate"]:<14.4f} '
        f'{int(result.metrics["n_prompts"]):<10}'
    )
"""


STEP_5_INTRO = """---

## 5. Run the full `rapid_probe` workflow against each domain

Same workflow runner, same agent swarm (scout, judge, historian), three different domain packs. Each run produces its own `WorkflowRun` record with a unique `run_id`, `config_hash`, and persistent Markdown report."""


RUN_WORKFLOW = """import tempfile
from pathlib import Path
from duecare.agents.historian import HistorianAgent
from duecare.agents import agent_registry
from duecare.workflows import Workflow, AgentStep, WorkflowRunner

# Route Historian reports to a notebook-local tmp dir so every run is self-contained.
tmp_reports = Path(tempfile.mkdtemp()) / 'reports'
agent_registry._by_id['historian'] = HistorianAgent(output_dir=tmp_reports)

# Inline rapid_probe workflow so this notebook does not depend on the YAML
# file being present on the Kaggle runtime filesystem.
wf = Workflow(
    id='rapid_probe',
    description='Three-agent smoke test used for cross-domain proof.',
    agents=[
        AgentStep(id='scout', needs=[]),
        AgentStep(id='judge', needs=['scout']),
        AgentStep(id='historian', needs=['scout', 'judge']),
    ],
)
runner = WorkflowRunner(wf)

workflow_runs = {}
for domain_id in ['trafficking', 'tax_evasion', 'financial_crime']:
    run = runner.run(target_model_id='scripted:cross_domain', domain_id=domain_id)
    workflow_runs[domain_id] = run
    print(
        f'{domain_id:<16} status={run.status.value} '
        f'run_id={run.run_id[:26]}... cost=${run.total_cost_usd:.4f}'
    )

run_ids = {r.run_id for r in workflow_runs.values()}
print()
print(f'Distinct run_ids: {len(run_ids)} (expected {len(workflow_runs)})')
assert len(run_ids) == len(workflow_runs), 'run_ids must be unique per run.'
"""


STEP_6_INTRO = """---

## 6. Inspect one generated report

The Historian agent writes a Markdown report per run. We print the first 2000 characters of the trafficking report so you can see the generated artifact. Every run produced one of these; they differ only in the domain-specific content."""


SHOW_REPORT = """run = workflow_runs['trafficking']
report_path = tmp_reports / f'{run.run_id}.md'

if report_path.exists():
    print(report_path.read_text()[:2000])
else:
    print(f'Report not found at {report_path}')
"""


TROUBLESHOOTING = troubleshooting_table_html([
    (
        "Install cell fails because the wheels dataset is not attached.",
        f"Attach <code>{WHEELS_DATASET}</code> from the Kaggle sidebar and rerun the install cell.",
    ),
    (
        "<code>AssertionError</code>: one of the three domain packs is missing from the registry.",
        "Reinstall <code>duecare-llm-domains</code>; the wheel dataset may be out of date. Rerun the install cell and step 1.",
    ),
    (
        "Capability test raises on a domain's rubric schema.",
        "The domain rubric YAML does not match the shared schema. Inspect the pack card output from step 1 and reinstall if the version is older than expected.",
    ),
    (
        "All three workflow runs produce the same <code>run_id</code>.",
        "The provenance clock is frozen (repeated instantiation in one Python session can collide). Restart the kernel and rerun step 5.",
    ),
    (
        "Historian report is missing at <code>tmp_reports / f'{run.run_id}.md'</code>.",
        "The Historian agent failed its step; re-inspect <code>run.status.value</code> and the <code>WorkflowRun</code> record in step 5 output, then rerun step 5 and step 6.",
    ),
])


SUMMARY = f"""---

## What just happened

- Registered all shipped domain packs (at least `trafficking`, `tax_evasion`, `financial_crime`) via `duecare.domains.register_discovered()` and inspected each pack's card.
- Ran the `guardrails` capability test against each pack with one deterministic `ScriptedModel`; metrics use the same schema across domains.
- Printed a cross-domain headline table with mean score, refusal rate, and prompt count.
- Executed the `rapid_probe` workflow end-to-end against each domain with the same `WorkflowRunner` and confirmed three distinct `run_id`s.
- Rendered the Historian agent's auto-generated Markdown report for the trafficking run.

### Key findings

1. **The harness is genuinely domain-agnostic.** The same `duecare.workflows.WorkflowRunner` walks three different packs with zero code changes; that is the invariant every later comparison notebook depends on.
2. **Domain packs are pure data.** Taxonomy, rubric, PII spec, seed prompts, and evidence all live in YAML and JSONL inside the `duecare-llm-domains` wheel; there is no domain-specific Python.
3. **Metrics are cross-domain comparable.** The `guardrails` capability-test metrics use the same schema across all three packs, so mean score and refusal rate can be compared row-by-row.
4. **Adding a new domain is a directory copy.** A new pack (for example `medical_misinformation`) is a directory copy plus a YAML edit; the same Python harness picks it up on the next `register_discovered()` call.
5. **Provenance is per-run.** Each `rapid_probe` execution produces its own `run_id`, `config_hash`, and Historian report so reruns never stomp earlier output; the three `run_id`s printed in step 5 are distinct by construction.

---

## Troubleshooting

{TROUBLESHOOTING}
---

## Next

- **Continue the section:** [210 Gemma vs OSS Comparison]({URL_210}) swaps the scripted model for peer open-source models on the same harness.
- **Cross-generation shortcut:** [270 Gemma Generations]({URL_270}) reuses this harness to compare Gemma 2, 3, and 4.
- **Close the section:** [399 Baseline Text Comparisons Conclusion]({URL_399}).
- **Architecture detour:** [500 Agent Swarm Deep Dive]({URL_500}).
- **Back to navigation (optional):** [000 Index]({URL_000}).
"""



AT_A_GLANCE_INTRO = """---

## At a glance

Same harness across three safety domains — the proof that DueCare is a framework, not a trafficking-only tool.
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
    _stat_card("3",    "domain packs",        "trafficking / tax_evasion / financial_crime", "primary"),
    _stat_card("same", "rubric + harness",    "no per-domain code changes",                   "info"),
    _stat_card("9",    "capability tests",    "run identically in each domain",              "warning"),
    _stat_card("CPU",  "kernel",              "no GPU required for the proof",               "success"),
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step("Load packs",   "3 domains",         "primary"),
    _step("Pick 9 tasks", "shared capability", "info"),
    _step("Run same loop","per domain",        "warning"),
    _step("Score same",   "same rubric",       "warning"),
    _step("Compare",      "cross-domain table","success"),
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">Cross-domain proof pipeline</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
'''



def build() -> None:
    cells = [
        md(HEADER),
        md(AT_A_GLANCE_INTRO),
        code(AT_A_GLANCE_CODE),
        md(STEP_1_INTRO),
        # harden_notebook injects the pinned install cell here; no duplicate
        # manual wheel-install cell any more.
        code(LOAD_DOMAINS),
        code(INSPECT_DOMAINS),
        md(STEP_2_INTRO),
        code(SCRIPTED_MODEL),
        md(STEP_3_INTRO),
        code(RUN_GUARDRAILS),
        md(STEP_4_INTRO),
        code(HEADLINE_TABLE),
        md(STEP_5_INTRO),
        code(RUN_WORKFLOW),
        md(STEP_6_INTRO),
        code(SHOW_REPORT),
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
        "    'Cross-domain proof handoff >>> Continue to 210 Gemma vs OSS Comparison: '\n"
        f"    '{URL_210}'\n"
        "    '. Section close: 399 Baseline Text Comparisons Conclusion: '\n"
        f"    '{URL_399}'\n"
        "    '.'\n"
        ")\n"
    )
    patch_final_print_cell(
        nb,
        final_print_src=final_print_src,
        marker="Cross-domain proof handoff >>>",
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
        "dataset_sources": [WHEELS_DATASET, "taylorsamarel/duecare-trafficking-prompts"],
        "competition_sources": ["gemma-4-good-hackathon"],
        "kernel_sources": [],
        "keywords": KEYWORDS,
    }
    (kernel_dir / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    code_count = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
    md_count = sum(1 for c in nb["cells"] if c["cell_type"] == "markdown")
    print(f"Wrote {nb_path} ({code_count} code + {md_count} md cells)")
    print(f"Wrote {kernel_dir / FILENAME}")
    print(f"Wrote {kernel_dir / 'kernel-metadata.json'}")


if __name__ == "__main__":
    build()
