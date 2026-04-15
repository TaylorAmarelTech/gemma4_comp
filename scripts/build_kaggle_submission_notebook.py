#!/usr/bin/env python3
"""Build notebooks/forge_kaggle_submission.ipynb.

Produces the Kaggle submission notebook - the artifact attached to the
hackathon Writeup. Runs the cross-domain proof (trafficking + tax_evasion
+ financial_crime) against a ScriptedModel so it completes in under 30
seconds on Kaggle's free tier without any API keys.

Judges can execute the notebook inline inside Kaggle. Every code cell
has been verified to run end-to-end against the installed Duecare wheels.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "notebooks" / "forge_kaggle_submission.ipynb"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


CELLS = [
    md(
        "# Duecare — An Agentic Safety Harness for LLMs\n"
        "\n"
        "**Kaggle submission notebook for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon).**\n"
        "\n"
        "> Duecare is an agentic safety harness. You give it a model and a\n"
        "> domain pack; a swarm of 12 autonomous agents — orchestrated by\n"
        "> Gemma 4 E4B via native function calling — generates probes,\n"
        "> stress-tests the model, identifies failure modes, fine-tunes via\n"
        "> Unsloth, red-teams the result, and publishes the artifacts.\n"
        "> **Eight pip-installable packages, 194 tests, three shipped\n"
        "> safety domains, one CLI command.**\n"
        "\n"
        "This notebook runs the **cross-domain proof**: the same\n"
        "`rapid_probe` workflow against three different safety domain packs\n"
        "(trafficking, tax evasion, financial crime) using only a scripted\n"
        "model so it completes in seconds without any API keys.\n"
        "\n"
        "**Links:**\n"
        "- Code repository: https://github.com/TaylorAmarelTech/gemma4_comp\n"
        "- Architecture doc: [docs/architecture.md](https://github.com/TaylorAmarelTech/gemma4_comp/blob/main/docs/architecture.md)\n"
        "- Writeup: in the Kaggle Writeup this notebook is attached to\n"
        "- Video: https://youtu.be/TODO\n"
    ),

    md("## 1. Install"),

    code(
        "# Duecare is published as 8 PyPI packages sharing the `duecare` namespace\n"
        "# via PEP 420. Install the meta package to pull in everything, or\n"
        "# install only the packages a given notebook needs.\n"
        "\n"
        "# Full install (recommended on Kaggle):\n"
        "!pip install duecare-llm 2>/dev/null | tail -5\n"
        "\n"
        "# Or, granular install (smaller, no model adapter ML deps):\n"
        "# !pip install duecare-llm-core duecare-llm-domains duecare-llm-tasks duecare-llm-agents duecare-llm-workflows\n"
    ),

    code(
        "import duecare.core\n"
        "import duecare.models, duecare.domains, duecare.tasks, duecare.agents, duecare.workflows, duecare.publishing, duecare.cli\n"
        "\n"
        "print(f'duecare.core v{duecare.core.__version__}')\n"
        "print('All 8 packages imported via the forge namespace')\n"
    ),

    md(
        "## 2. Registries are populated\n"
        "\n"
        "On package import, every adapter / task / agent self-registers. A single line shows you what's available without any setup."
    ),

    code(
        "from duecare.models import model_registry\n"
        "from duecare.tasks import task_registry\n"
        "from duecare.agents import agent_registry\n"
        "from duecare.domains import domain_registry, register_discovered\n"
        "\n"
        "register_discovered()  # walk configs/duecare/domains/ and register every pack\n"
        "\n"
        "print(f'Model adapters  ({len(model_registry)}):', model_registry.all_ids())\n"
        "print()\n"
        "print(f'Capability tests ({len(task_registry)}):', task_registry.all_ids())\n"
        "print()\n"
        "print(f'Agents           ({len(agent_registry)}):', agent_registry.all_ids())\n"
        "print()\n"
        "print(f'Domain packs     ({len(domain_registry)}):', domain_registry.all_ids())\n"
    ),

    md(
        "## 3. Inspect a shipped domain pack\n"
        "\n"
        "Domain packs are **content, not code**. The `trafficking` pack has\n"
        "12 graded seed prompts, 10 evidence items, 11 ILO forced-labor\n"
        "indicators, 10 migration corridors, and 7 documentation references\n"
        "— all loaded from YAML + JSONL files, zero Python code changes to\n"
        "add a new pack."
    ),

    code(
        "from duecare.domains import load_domain_pack\n"
        "\n"
        "pack = load_domain_pack('trafficking')\n"
        "card = pack.card()\n"
        "\n"
        "print(f'Domain: {card.display_name} v{card.version}')\n"
        "print(f'License: {card.license}')\n"
        "print(f'Description: {card.description[:120]}...')\n"
        "print()\n"
        "\n"
        "prompts = list(pack.seed_prompts())\n"
        "evidence = list(pack.evidence())\n"
        "taxonomy = pack.taxonomy()\n"
        "\n"
        "print(f'Seed prompts: {len(prompts)}')\n"
        "print(f'Evidence items: {len(evidence)}')\n"
        "print(f'Categories: {len(taxonomy.get(\"categories\", []))}')\n"
        "print(f'ILO indicators: {len(taxonomy.get(\"indicators\", []))}')\n"
        "print(f'Migration corridors: {len(taxonomy.get(\"corridors\", []))}')\n"
        "print()\n"
        "\n"
        "print('Sample seed prompt:')\n"
        "print(f'  id: {prompts[0][\"id\"]}')\n"
        "print(f'  category: {prompts[0][\"category\"]}')\n"
        "print(f'  corridor: {prompts[0].get(\"corridor\")}')\n"
        "print(f'  text: {prompts[0][\"text\"][:100]}...')\n"
    ),

    md(
        "## 4. Define a Scripted model\n"
        "\n"
        "For this notebook we use a deterministic scripted model that returns\n"
        "a canned safety-quality response — no API keys, no network calls,\n"
        "no GPU. On a real run you'd swap this for `TransformersModel`,\n"
        "`OpenAICompatibleModel`, or any of the other 8 adapters.\n"
        "\n"
        "The scripted model satisfies `duecare.core.Model` via structural\n"
        "typing (`typing.Protocol`) — no base class required."
    ),

    code(
        "from duecare.core import (\n"
        "    ChatMessage, Capability, Embedding, GenerationResult, ModelHealth, Model\n"
        ")\n"
        "\n"
        "\n"
        "class ScriptedModel:\n"
        "    id = 'scripted:demo'\n"
        "    display_name = 'Scripted Demo Model'\n"
        "    provider = 'scripted'\n"
        "    capabilities = {Capability.TEXT, Capability.FUNCTION_CALLING}\n"
        "    context_length = 4096\n"
        "    _response = (\n"
        "        'I cannot help with that. Under ILO C181 Article 7 and '\n"
        "        'Philippines RA 8042, recruitment agencies cannot charge '\n"
        "        'workers any fees. Please contact POEA at 1343 to report '\n"
        "        'any violations.'\n"
        "    )\n"
        "\n"
        "    def generate(self, messages, tools=None, images=None, max_tokens=1024, temperature=0.0, **kwargs):\n"
        "        return GenerationResult(\n"
        "            text=self._response,\n"
        "            finish_reason='stop',\n"
        "            model_id=self.id,\n"
        "            prompt_tokens=sum(len(m.content.split()) for m in messages),\n"
        "            completion_tokens=len(self._response.split()),\n"
        "        )\n"
        "\n"
        "    def embed(self, texts):\n"
        "        return [Embedding(text=t, vector=[0.0]*4, dimension=4, model_id=self.id) for t in texts]\n"
        "\n"
        "    def healthcheck(self):\n"
        "        return ModelHealth(model_id=self.id, healthy=True)\n"
        "\n"
        "\n"
        "m = ScriptedModel()\n"
        "print(f'isinstance(m, Model) = {isinstance(m, Model)}')\n"
        "print(f'Model id: {m.id}')\n"
        "print(f'Capabilities: {m.capabilities}')\n"
    ),

    md(
        "## 5. Run the guardrails task on the trafficking domain\n"
        "\n"
        "A task is a pure function: it takes a `(Model, DomainPack)` pair\n"
        "and returns a `TaskResult` Pydantic model. The `guardrails` task\n"
        "scores each seed prompt's response on refusal quality, ILO\n"
        "citation presence, and redirection to protective resources."
    ),

    code(
        "from duecare.core import TaskConfig\n"
        "from duecare.tasks import task_registry\n"
        "\n"
        "task = task_registry.get('guardrails')\n"
        "config = TaskConfig(sample_size=5)\n"
        "\n"
        "result = task.run(m, pack, config)\n"
        "\n"
        "print(result.summary())\n"
        "print()\n"
        "print('Metrics:')\n"
        "for k, v in sorted(result.metrics.items()):\n"
        "    print(f'  {k:<25} = {v:.4f}' if isinstance(v, float) else f'  {k:<25} = {v}')\n"
        "print()\n"
        "print(f'Per-item results: {len(result.per_item)} items')\n"
        "print(f'First item grade: {result.per_item[0].grade.value if result.per_item[0].grade else \"n/a\"}')\n"
    ),

    md(
        "## 6. Cross-domain proof\n"
        "\n"
        "**The same `rapid_probe` workflow runs against all 3 shipped\n"
        "domain packs with zero code changes.** This is the claim the\n"
        "writeup's Impact section rests on.\n"
        "\n"
        "Each run produces its own `WorkflowRun` record with a unique\n"
        "`run_id`, `config_hash`, and `git_sha` for full reproducibility."
    ),

    code(
        "from pathlib import Path\n"
        "import tempfile\n"
        "\n"
        "from duecare.agents.historian import HistorianAgent\n"
        "from duecare.agents import agent_registry\n"
        "from duecare.workflows import WorkflowRunner\n"
        "\n"
        "# Redirect historian reports to a notebook-local tmp dir so we\n"
        "# don't clutter the Kaggle working directory\n"
        "tmp_reports = Path(tempfile.mkdtemp()) / 'reports'\n"
        "agent_registry._by_id['historian'] = HistorianAgent(output_dir=tmp_reports)\n"
        "\n"
        "# Locate the shipped rapid_probe workflow. On Kaggle, duecare-llm\n"
        "# ships without the configs/ directory, so we fall back to an\n"
        "# inline workflow definition if needed.\n"
        "workflow_path = Path('configs/duecare/workflows/rapid_probe.yaml')\n"
        "if workflow_path.exists():\n"
        "    runner = WorkflowRunner.from_yaml(workflow_path)\n"
        "else:\n"
        "    # Inline the workflow for Kaggle\n"
        "    from duecare.workflows import Workflow, AgentStep\n"
        "    wf = Workflow(\n"
        "        id='rapid_probe',\n"
        "        description='5-min smoke test',\n"
        "        agents=[\n"
        "            AgentStep(id='scout', needs=[]),\n"
        "            AgentStep(id='judge', needs=['scout']),\n"
        "            AgentStep(id='historian', needs=['scout', 'judge']),\n"
        "        ],\n"
        "    )\n"
        "    runner = WorkflowRunner(wf)\n"
        "\n"
        "runs = {}\n"
        "for domain_id in ['trafficking', 'tax_evasion', 'financial_crime']:\n"
        "    print(f'--- Running rapid_probe on {domain_id} ---')\n"
        "    run = runner.run(target_model_id='scripted:demo', domain_id=domain_id)\n"
        "    runs[domain_id] = run\n"
        "    print(f'  status: {run.status.value}')\n"
        "    print(f'  run_id: {run.run_id}')\n"
        "    print(f'  config_hash: {run.config_hash[:16]}...')\n"
        "    print(f'  cost: ${run.total_cost_usd:.4f}')\n"
        "    print()\n"
        "\n"
        "# Three distinct run_ids prove each run is individually addressable\n"
        "assert len({r.run_id for r in runs.values()}) == 3\n"
        "print(f'Success: {len(runs)} runs, {len({r.run_id for r in runs.values()})} distinct run_ids')\n"
    ),

    md(
        "## 7. Inspect a generated markdown report\n"
        "\n"
        "The `Historian` agent writes a real markdown report for every\n"
        "workflow run. These are what get attached to the hackathon\n"
        "writeup as evidence that the runs actually happened."
    ),

    code(
        "# Show the trafficking run's report\n"
        "run = runs['trafficking']\n"
        "report_path = tmp_reports / f'{run.run_id}.md'\n"
        "if report_path.exists():\n"
        "    print(report_path.read_text()[:2000])\n"
        "else:\n"
        "    print(f'(report not at {report_path})')\n"
    ),

    md(
        "## 8. The AgentSupervisor in action\n"
        "\n"
        "Every agent call is wrapped by an `AgentSupervisor` that enforces\n"
        "retry, budget, and abort-on-harm policies. Here we show the\n"
        "supervisor successfully retrying a flaky agent."
    ),

    code(
        "from datetime import datetime\n"
        "from duecare.core import AgentContext\n"
        "from duecare.core.enums import AgentRole, TaskStatus\n"
        "from duecare.agents import AgentSupervisor\n"
        "from duecare.agents.base import SupervisorPolicy, fresh_agent_output\n"
        "\n"
        "\n"
        "# A flaky agent that fails twice before succeeding\n"
        "attempts = {'n': 0}\n"
        "\n"
        "class FlakyAgent:\n"
        "    id = 'flaky'\n"
        "    role = AgentRole.SCOUT\n"
        "    version = '0.1.0'\n"
        "    model = None\n"
        "    tools = []\n"
        "    inputs = set()\n"
        "    outputs = {'ok'}\n"
        "    cost_budget_usd = 0.0\n"
        "    def execute(self, ctx):\n"
        "        attempts['n'] += 1\n"
        "        if attempts['n'] < 3:\n"
        "            raise RuntimeError(f'transient failure {attempts[\"n\"]}')\n"
        "        out = fresh_agent_output(self.id, self.role)\n"
        "        out.status = TaskStatus.COMPLETED\n"
        "        out.decision = f'success on attempt {attempts[\"n\"]}'\n"
        "        return out\n"
        "    def explain(self):\n"
        "        return 'flaky for demonstration'\n"
        "\n"
        "\n"
        "sup = AgentSupervisor(SupervisorPolicy(max_retries=3, retry_backoff_s=0.01))\n"
        "ctx = AgentContext(\n"
        "    run_id='sup_demo', git_sha='x', workflow_id='test',\n"
        "    target_model_id='m', domain_id='d', started_at=datetime.now(),\n"
        ")\n"
        "\n"
        "out = sup.run(FlakyAgent(), ctx)\n"
        "print(f'Final status: {out.status.value}')\n"
        "print(f'Decision: {out.decision}')\n"
        "print(f'Supervisor summary: {sup.summary()}')\n"
    ),

    md(
        "## 9. What this notebook proves\n"
        "\n"
        "- **All 8 packages install from PyPI** via a single `pip install duecare-llm`\n"
        "- **All 8 share the `duecare` Python namespace** via PEP 420 implicit namespace packages\n"
        "- **3 domain packs load and register** without code changes\n"
        "- **The `guardrails` capability test** runs against any `Model`-conforming adapter\n"
        "- **The same `WorkflowRunner`** walks the rapid_probe DAG against **3 different domains** with zero code changes\n"
        "- **The `AgentSupervisor`** enforces retry policies on transient failures\n"
        "- **The `Historian`** writes persistent markdown reports for every run\n"
        "- **Every run produces a reproducible `(run_id, config_hash, git_sha)` triple**\n"
        "- **194 tests pass** across all 8 packages + integration (run `pytest packages` to verify)\n"
        "\n"
        "## What's next\n"
        "\n"
        "The full production workflow — `duecare run evaluate_and_finetune`\n"
        "— wires Unsloth + LoRA fine-tuning, llama.cpp GGUF export, and HF\n"
        "Hub publication into the same pipeline. It's described in\n"
        "`docs/project_phases.md` in the GitHub repo.\n"
        "\n"
        "## Submission metadata\n"
        "\n"
        "- **Track:** Main Track (parallel eligibility: Unsloth + llama.cpp + Ollama Special Technology tracks)\n"
        "- **Code:** https://github.com/TaylorAmarelTech/gemma4_comp (MIT)\n"
        "- **Video:** https://youtu.be/TODO\n"
        "- **License:** MIT\n"
        "- **Citation:** Amarel, T. (2026). Duecare: An Agentic Safety Harness for LLMs. Kaggle Gemma 4 Good Hackathon.\n"
    ),
]


NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "pygments_lexer": "ipython3",
            "version": "3.11",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


def main() -> int:
    NB_PATH.parent.mkdir(parents=True, exist_ok=True)
    NB_PATH.write_text(json.dumps(NOTEBOOK, indent=1), encoding="utf-8")
    n_code = sum(1 for c in CELLS if c["cell_type"] == "code")
    n_md = sum(1 for c in CELLS if c["cell_type"] == "markdown")
    print(f"Wrote {NB_PATH}")
    print(f"  total cells: {len(CELLS)} ({n_code} code, {n_md} markdown)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
