#!/usr/bin/env python3
"""implement_forge_rest.py - duecare-llm-workflows + publishing + meta/CLI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


FILES: dict[str, str] = {

    # =======================================================================
    # duecare-llm-workflows
    # =======================================================================

    "packages/duecare-llm-workflows/src/forge/workflows/__init__.py": '''"""duecare.workflows - YAML DAG orchestration for the agent swarm."""

from .loader import load_workflow, Workflow, AgentStep
from .dag import topological_sort
from .runner import WorkflowRunner

__all__ = [
    "load_workflow",
    "Workflow",
    "AgentStep",
    "topological_sort",
    "WorkflowRunner",
]
''',

    "packages/duecare-llm-workflows/src/forge/workflows/loader/__init__.py": '''"""Workflow YAML loader."""

from .loader import load_workflow, Workflow, AgentStep

__all__ = ["load_workflow", "Workflow", "AgentStep"]
''',

    "packages/duecare-llm-workflows/src/forge/workflows/loader/loader.py": '''"""Load workflow YAML into Pydantic models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AgentStep(BaseModel):
    id: str
    needs: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowBudget(BaseModel):
    max_cost_usd: float = 100.0
    max_wall_clock_hours: float = 12.0
    max_gpu_hours: float = 8.0


class RetryPolicy(BaseModel):
    max_attempts: int = 3
    backoff: str = "exponential"


class FailurePolicy(BaseModel):
    on_validator_harm_flag: str = "abort"
    on_budget_exceeded: str = "snapshot_and_stop"
    on_agent_error: str = "retry_then_skip"


class CoordinatorConfig(BaseModel):
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    failure_policy: FailurePolicy = Field(default_factory=FailurePolicy)


class Workflow(BaseModel):
    id: str
    description: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    budget: WorkflowBudget = Field(default_factory=WorkflowBudget)
    agents: list[AgentStep] = Field(default_factory=list)
    coordinator: CoordinatorConfig = Field(default_factory=CoordinatorConfig)


def load_workflow(path: Path | str) -> Workflow:
    """Parse a workflow YAML file into a Workflow model."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Workflow(**raw)
''',

    "packages/duecare-llm-workflows/src/forge/workflows/dag/__init__.py": '''"""DAG helpers."""

from .dag import topological_sort

__all__ = ["topological_sort"]
''',

    "packages/duecare-llm-workflows/src/forge/workflows/dag/dag.py": '''"""Topological sort for the agent DAG.

Pure utility - no I/O, no LLM calls.
"""

from __future__ import annotations


def topological_sort(nodes: list[tuple[str, list[str]]]) -> list[str]:
    """Return an execution order for a DAG given (node_id, deps) pairs.

    Raises ValueError on cycles or unknown dependencies.
    """
    remaining = {node: set(deps) for node, deps in nodes}
    all_ids = set(remaining.keys())

    for node, deps in remaining.items():
        unknown = deps - all_ids
        if unknown:
            raise ValueError(f"Node {node!r} depends on unknown node(s): {sorted(unknown)}")

    ordered: list[str] = []
    while remaining:
        ready = [node for node, deps in remaining.items() if not deps]
        if not ready:
            cycle = list(remaining.keys())
            raise ValueError(f"Cycle detected in DAG involving: {cycle}")
        ready.sort()  # deterministic order
        for node in ready:
            ordered.append(node)
            del remaining[node]
            for deps in remaining.values():
                deps.discard(node)
    return ordered
''',

    "packages/duecare-llm-workflows/src/forge/workflows/runner/__init__.py": '''"""Workflow runner."""

from .runner import WorkflowRunner

__all__ = ["WorkflowRunner"]
''',

    "packages/duecare-llm-workflows/src/forge/workflows/runner/runner.py": '''"""Walk a workflow DAG and invoke each agent via an AgentSupervisor."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from duecare.core.contracts import Model
from duecare.core.enums import TaskStatus
from duecare.core.provenance import generate_run_id, get_git_sha, hash_config
from duecare.core.schemas import AgentContext, WorkflowRun
from duecare.observability.logging import get_logger

from ..dag import topological_sort
from ..loader import Workflow, load_workflow

log = get_logger("duecare.workflows.runner")


class WorkflowRunner:
    """Walks a Workflow DAG and invokes each agent in topological order.

    Uses an AgentSupervisor to enforce retries, budget caps, and abort-
    on-harm policies. Returns a WorkflowRun record with the final
    status and metrics.
    """

    def __init__(self, workflow: Workflow) -> None:
        self.workflow = workflow

    @classmethod
    def from_yaml(cls, path: Path | str) -> "WorkflowRunner":
        return cls(load_workflow(path))

    def run(
        self,
        target_model_id: str,
        domain_id: str,
        target_model_instance: Model | None = None,
    ) -> WorkflowRun:
        from duecare.agents import agent_registry, AgentSupervisor
        from duecare.agents.base import SupervisorPolicy

        run_id = generate_run_id(self.workflow.id)
        config_hash = hash_config(self.workflow.model_dump())

        ctx = AgentContext(
            run_id=run_id,
            git_sha=get_git_sha(),
            workflow_id=self.workflow.id,
            target_model_id=target_model_id,
            domain_id=domain_id,
            started_at=datetime.now(),
        )
        if target_model_instance is not None:
            ctx.record("target_model_instance", target_model_instance)

        # Topological sort
        dag = [(step.id, step.needs) for step in self.workflow.agents]
        try:
            order = topological_sort(dag)
        except ValueError as e:
            return WorkflowRun(
                run_id=run_id,
                workflow_id=self.workflow.id,
                git_sha=ctx.git_sha,
                config_hash=config_hash,
                target_model_id=target_model_id,
                domain_id=domain_id,
                started_at=ctx.started_at,
                ended_at=datetime.now(),
                status=TaskStatus.FAILED,
                error=f"DAG error: {e}",
            )

        # Execute via supervisor
        policy = SupervisorPolicy(
            max_retries=self.workflow.coordinator.retry_policy.max_attempts - 1,
            hard_budget_usd=self.workflow.budget.max_cost_usd,
        )
        supervisor = AgentSupervisor(policy)

        result_status = TaskStatus.RUNNING
        error: str | None = None

        for agent_id in order:
            if not agent_registry.has(agent_id):
                log.warning("workflow.skip unknown_agent=%s", agent_id)
                continue
            agent = agent_registry.get(agent_id)
            try:
                out = supervisor.run(agent, ctx)
                if out.status == TaskStatus.FAILED:
                    error = out.error
                    if self.workflow.coordinator.failure_policy.on_agent_error == "retry_then_skip":
                        log.warning("workflow.agent_failed agent=%s; continuing", agent_id)
                        continue
                    result_status = TaskStatus.FAILED
                    break
            except Exception as e:
                log.error("workflow.fatal agent=%s error=%s", agent_id, e)
                error = str(e)
                result_status = TaskStatus.FAILED
                break

        if result_status == TaskStatus.RUNNING:
            result_status = TaskStatus.COMPLETED

        return WorkflowRun(
            run_id=run_id,
            workflow_id=self.workflow.id,
            git_sha=ctx.git_sha,
            config_hash=config_hash,
            target_model_id=target_model_id,
            domain_id=domain_id,
            started_at=ctx.started_at,
            ended_at=datetime.now(),
            status=result_status,
            final_metrics=ctx.metrics,
            final_artifacts={k: v for k, v in ctx.artifacts.items()},
            total_cost_usd=supervisor.total_cost_usd,
            error=error,
        )
''',

    # =======================================================================
    # duecare-llm-publishing
    # =======================================================================

    "packages/duecare-llm-publishing/src/forge/publishing/__init__.py": '''"""duecare.publishing - HF Hub, Kaggle, reports, model cards."""

from .hf_hub import hf_hub as _hf_hub  # noqa: F401
from .kaggle import kaggle as _kaggle  # noqa: F401
from .reports import reports as _reports  # noqa: F401
from .model_card import model_card as _model_card  # noqa: F401

from .hf_hub.hf_hub import HFHubPublisher, is_hf_hub_available
from .kaggle.kaggle import KagglePublisher, is_kaggle_cli_available
from .reports.reports import MarkdownReportGenerator
from .model_card.model_card import ModelCardGenerator

__all__ = [
    "HFHubPublisher",
    "is_hf_hub_available",
    "KagglePublisher",
    "is_kaggle_cli_available",
    "MarkdownReportGenerator",
    "ModelCardGenerator",
]
''',

    "packages/duecare-llm-publishing/src/forge/publishing/hf_hub/__init__.py": '''"""HF Hub publisher."""

from .hf_hub import HFHubPublisher, is_hf_hub_available

__all__ = ["HFHubPublisher", "is_hf_hub_available"]
''',

    "packages/duecare-llm-publishing/src/forge/publishing/hf_hub/hf_hub.py": '''"""HuggingFace Hub publisher.

Thin wrapper over huggingface_hub. Lazy-imports the library; raises
ImportError with install instructions if missing.
"""

from __future__ import annotations

import os
from pathlib import Path


def is_hf_hub_available() -> bool:
    try:
        import huggingface_hub  # noqa: F401
        return True
    except ImportError:
        return False


class HFHubPublisher:
    """Publish weights, datasets, and notebooks to HF Hub."""

    def __init__(self, token_env: str = "HUGGINGFACE_TOKEN") -> None:
        self.token_env = token_env

    def _token(self) -> str:
        token = os.environ.get(self.token_env)
        if not token:
            raise RuntimeError(f"{self.token_env!r} is not set")
        return token

    def upload_folder(
        self,
        repo_id: str,
        folder_path: Path | str,
        repo_type: str = "model",
        path_in_repo: str = "",
        commit_message: str = "Upload folder",
    ) -> str:
        """Upload a folder to HF Hub. Returns the repo URL."""
        try:
            from huggingface_hub import HfApi  # type: ignore
        except ImportError as e:
            raise ImportError(
                "duecare-llm-publishing[hf-hub] is required. "
                "Install with: pip install 'duecare-llm-publishing[hf-hub]'"
            ) from e

        api = HfApi(token=self._token())
        api.upload_folder(
            repo_id=repo_id,
            folder_path=str(folder_path),
            repo_type=repo_type,
            path_in_repo=path_in_repo,
            commit_message=commit_message,
        )
        return f"https://huggingface.co/{repo_id}"

    def create_repo_if_missing(self, repo_id: str, repo_type: str = "model") -> None:
        try:
            from huggingface_hub import HfApi  # type: ignore
            api = HfApi(token=self._token())
            api.create_repo(repo_id=repo_id, repo_type=repo_type, exist_ok=True)
        except ImportError as e:
            raise ImportError("duecare-llm-publishing[hf-hub] required") from e
''',

    "packages/duecare-llm-publishing/src/forge/publishing/kaggle/__init__.py": '''"""Kaggle Datasets + Models + Kernels publisher."""

from .kaggle import KagglePublisher, is_kaggle_cli_available

__all__ = ["KagglePublisher", "is_kaggle_cli_available"]
''',

    "packages/duecare-llm-publishing/src/forge/publishing/kaggle/kaggle.py": '''"""Kaggle CLI wrapper.

Shells out to the `kaggle` CLI for datasets / models / kernels. The CLI
must be installed and an API token placed at ~/.kaggle/kaggle.json.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def is_kaggle_cli_available() -> bool:
    return shutil.which("kaggle") is not None


class KagglePublisher:
    def __init__(self, cli_path: str = "kaggle") -> None:
        self.cli = cli_path

    def _run(self, args: list[str]) -> str:
        if not is_kaggle_cli_available() and self.cli == "kaggle":
            raise RuntimeError(
                "kaggle CLI is not on PATH. Install with: pip install kaggle"
            )
        result = subprocess.run(
            [self.cli, *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"kaggle command failed: {' '.join(args)}\\n"
                f"stderr: {result.stderr[:500]}"
            )
        return result.stdout

    def datasets_init(self, folder: Path | str) -> str:
        return self._run(["datasets", "init", "-p", str(folder)])

    def datasets_create(self, folder: Path | str) -> str:
        return self._run(["datasets", "create", "-p", str(folder)])

    def datasets_version(self, folder: Path | str, message: str) -> str:
        return self._run(["datasets", "version", "-p", str(folder), "-m", message])

    def kernels_init(self, folder: Path | str) -> str:
        return self._run(["kernels", "init", "-p", str(folder)])

    def kernels_push(self, folder: Path | str) -> str:
        return self._run(["kernels", "push", "-p", str(folder)])

    def models_init(self, folder: Path | str) -> str:
        return self._run(["models", "init", "-p", str(folder)])

    def models_create(self, folder: Path | str) -> str:
        return self._run(["models", "create", "-p", str(folder)])
''',

    "packages/duecare-llm-publishing/src/forge/publishing/reports/__init__.py": '''"""Markdown report generator."""

from .reports import MarkdownReportGenerator

__all__ = ["MarkdownReportGenerator"]
''',

    "packages/duecare-llm-publishing/src/forge/publishing/reports/reports.py": '''"""Markdown report generation used by the Historian agent."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from duecare.core.schemas import WorkflowRun


class MarkdownReportGenerator:
    """Turn a WorkflowRun (and optional metric/artifact dicts) into a
    readable markdown report."""

    def __init__(self, output_dir: Path | str = Path("reports")) -> None:
        self.output_dir = Path(output_dir)

    def render(
        self,
        run: WorkflowRun,
        extra_metrics: dict[str, float] | None = None,
        extra_artifacts: dict[str, str] | None = None,
        notes: list[str] | None = None,
    ) -> str:
        lines: list[str] = []
        lines.append(f"# Duecare Run Report — {run.run_id}")
        lines.append("")
        lines.append(f"- **workflow**: `{run.workflow_id}`")
        lines.append(f"- **target_model**: `{run.target_model_id}`")
        lines.append(f"- **domain**: `{run.domain_id}`")
        lines.append(f"- **git_sha**: `{run.git_sha}`")
        lines.append(f"- **config_hash**: `{run.config_hash[:16]}...`")
        lines.append(f"- **status**: `{run.status.value}`")
        lines.append(f"- **cost_usd**: ${run.total_cost_usd:.4f}")
        lines.append(f"- **duration_s**: {run.total_duration_s:.1f}")
        if run.started_at:
            lines.append(f"- **started_at**: {run.started_at.isoformat(timespec='seconds')}")
        if run.ended_at:
            lines.append(f"- **ended_at**: {run.ended_at.isoformat(timespec='seconds')}")
        lines.append("")

        metrics = {**run.final_metrics, **(extra_metrics or {})}
        if metrics:
            lines.append("## Metrics")
            lines.append("")
            for k, v in sorted(metrics.items()):
                lines.append(f"- `{k}` = {v}")
            lines.append("")

        artifacts = {**run.final_artifacts, **(extra_artifacts or {})}
        if artifacts:
            lines.append("## Artifacts")
            lines.append("")
            for k, v in sorted(artifacts.items()):
                lines.append(f"- `{k}`: `{v}`")
            lines.append("")

        if notes:
            lines.append("## Notes")
            lines.append("")
            for note in notes:
                lines.append(f"- {note}")
            lines.append("")

        if run.error:
            lines.append("## Error")
            lines.append("")
            lines.append("```")
            lines.append(run.error)
            lines.append("```")
            lines.append("")

        return "\\n".join(lines)

    def write(
        self,
        run: WorkflowRun,
        **kwargs: Any,
    ) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{run.run_id}.md"
        path.write_text(self.render(run, **kwargs), encoding="utf-8")
        return path
''',

    "packages/duecare-llm-publishing/src/forge/publishing/model_card/__init__.py": '''"""HF Hub model card generator."""

from .model_card import ModelCardGenerator

__all__ = ["ModelCardGenerator"]
''',

    "packages/duecare-llm-publishing/src/forge/publishing/model_card/model_card.py": '''"""Generate HF Hub-compatible model cards."""

from __future__ import annotations

from pathlib import Path
from typing import Any


CARD_TEMPLATE = """---
language: en
license: mit
tags:
  - safety
  - forge
  - gemma
  - llm-evaluation
datasets:
  - {dataset_id}
model-index:
  - name: {model_name}
    results:
      - task:
          type: safety-evaluation
        dataset:
          name: {dataset_id}
          type: trafficking-safety
        metrics:
          - type: grade_exact_match
            value: {grade_exact_match:.3f}
---

# {model_name}

> {description}

## Model details

- **Base model:** `{base_model}`
- **Fine-tuning:** Unsloth + LoRA (r={lora_r}, alpha={lora_alpha})
- **Training epochs:** {num_epochs}
- **Training data:** {n_train_samples} samples from the Duecare trafficking / tax-evasion / financial-crime domain packs

## Intended use

This model is a **safety judge** for migrant-worker trafficking and labor
exploitation scenarios. It takes a (prompt, candidate_response) pair and
returns a grade (worst / bad / neutral / good / best) with missed safety
indicators and citations to ILO Conventions / national labor law.

**Target users:** frontline NGOs, recruitment regulators, labor
ministries - organizations where sensitive case data cannot be sent to
frontier APIs.

## Out-of-scope use

- General-purpose conversation
- Legal advice for specific cases
- Autonomous enforcement (always keep a human in the loop)

## Evaluation

| Metric | Value |
|---|---|
| Grade exact match | {grade_exact_match:.3f} |
| Grade within 1 | {grade_within_1:.3f} |
| ILO indicator recall | {ilo_indicator_recall:.3f} |
| Refusal rate | {refusal_rate:.3f} |

## Limitations

- English-only in the v0.1 release; cross-lingual support pending
- Corridor coverage is strongest for PH-SA, NP-QA, ID-SA
- Not a replacement for human expert review

## Citation

```bibtex
@misc{{amarel2026forge,
  title={{Duecare: An Agentic Safety Harness for LLMs}},
  author={{Amarel, Taylor}},
  year={{2026}},
}}
```

## License

MIT
"""


class ModelCardGenerator:
    """Generate HF Hub-compatible model cards from run metrics."""

    def render(
        self,
        *,
        model_name: str,
        base_model: str,
        dataset_id: str,
        description: str,
        grade_exact_match: float = 0.0,
        grade_within_1: float = 0.0,
        ilo_indicator_recall: float = 0.0,
        refusal_rate: float = 0.0,
        lora_r: int = 16,
        lora_alpha: int = 32,
        num_epochs: int = 2,
        n_train_samples: int = 0,
        **extra: Any,
    ) -> str:
        return CARD_TEMPLATE.format(
            model_name=model_name,
            base_model=base_model,
            dataset_id=dataset_id,
            description=description,
            grade_exact_match=grade_exact_match,
            grade_within_1=grade_within_1,
            ilo_indicator_recall=ilo_indicator_recall,
            refusal_rate=refusal_rate,
            lora_r=lora_r,
            lora_alpha=lora_alpha,
            num_epochs=num_epochs,
            n_train_samples=n_train_samples,
        )

    def write(self, path: Path | str, **kwargs: Any) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(**kwargs), encoding="utf-8")
        return path
''',

    # =======================================================================
    # duecare-llm (meta) + CLI
    # =======================================================================

    "packages/duecare-llm/src/forge/cli/__init__.py": '''"""forge CLI entry point."""

from .cli import app, main

__all__ = ["app", "main"]
''',

    "packages/duecare-llm/src/forge/cli/cli.py": '''"""The `duecare` CLI. Typer-based.

Commands:
  duecare run            - run a workflow
  duecare runs list      - list previous runs
  forge agents list    - list registered agents
  forge models list    - list registered model adapters
  forge domains list   - list available domain packs
  forge tasks list     - list registered capability tests
  duecare tree           - show the module tree
  duecare review PATH    - print meta files for a module folder
  duecare test PATH      - run tests under a path
  duecare status         - completeness report
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table


app = typer.Typer(
    name="duecare",
    help="Duecare — agentic, universal LLM safety harness",
    no_args_is_help=True,
)

# Sub-apps
agents_app = typer.Typer(help="Agent commands", no_args_is_help=True)
models_app = typer.Typer(help="Model commands", no_args_is_help=True)
domains_app = typer.Typer(help="Domain pack commands", no_args_is_help=True)
tasks_app = typer.Typer(help="Capability test commands", no_args_is_help=True)
runs_app = typer.Typer(help="Run history", no_args_is_help=True)

app.add_typer(agents_app, name="agents")
app.add_typer(models_app, name="models")
app.add_typer(domains_app, name="domains")
app.add_typer(tasks_app, name="tasks")
app.add_typer(runs_app, name="runs")

console = Console()


@app.command()
def run(
    workflow: str = typer.Argument(..., help="Workflow id (e.g., rapid_probe)"),
    target_model: str = typer.Option(..., "--target-model", help="Target model id"),
    domain: str = typer.Option(..., "--domain", help="Domain pack id"),
    workflow_dir: Path = typer.Option(
        Path("configs/duecare/workflows"),
        "--workflow-dir",
        help="Directory containing workflow YAMLs",
    ),
) -> None:
    """Run a workflow end-to-end via the WorkflowRunner."""
    from duecare.workflows import WorkflowRunner

    workflow_path = workflow_dir / f"{workflow}.yaml"
    if not workflow_path.exists():
        console.print(f"[red]Workflow YAML not found:[/red] {workflow_path}")
        raise typer.Exit(code=1)

    runner = WorkflowRunner.from_yaml(workflow_path)
    console.print(f"[bold]Running[/bold] workflow=[cyan]{workflow}[/cyan] "
                  f"model=[cyan]{target_model}[/cyan] domain=[cyan]{domain}[/cyan]")
    result = runner.run(target_model_id=target_model, domain_id=domain)

    table = Table(title="Workflow run result")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("run_id", result.run_id)
    table.add_row("status", result.status.value)
    table.add_row("git_sha", result.git_sha)
    table.add_row("config_hash", result.config_hash[:16] + "...")
    table.add_row("cost_usd", f"${result.total_cost_usd:.4f}")
    if result.error:
        table.add_row("error", result.error[:80])
    console.print(table)

    if result.final_metrics:
        m_table = Table(title="Final metrics")
        m_table.add_column("Metric")
        m_table.add_column("Value")
        for k, v in sorted(result.final_metrics.items()):
            m_table.add_row(k, f"{v:.4f}" if isinstance(v, float) else str(v))
        console.print(m_table)


@agents_app.command("list")
def agents_list() -> None:
    """List registered agents."""
    from duecare.agents import agent_registry
    table = Table(title="Registered agents")
    table.add_column("id")
    table.add_column("role")
    table.add_column("version")
    for agent_id in agent_registry.all_ids():
        agent = agent_registry.get(agent_id)
        table.add_row(agent.id, agent.role.value, agent.version)
    console.print(table)


@models_app.command("list")
def models_list() -> None:
    """List registered model adapters."""
    from duecare.models import model_registry
    table = Table(title="Registered model adapters")
    table.add_column("id")
    for model_id in model_registry.all_ids():
        table.add_row(model_id)
    console.print(table)


@domains_app.command("list")
def domains_list(
    root: Path = typer.Option(
        Path("configs/duecare/domains"),
        help="Domains root directory",
    ),
) -> None:
    """List discoverable domain packs."""
    from duecare.domains import discover_all
    packs = discover_all(root)
    if not packs:
        console.print("[yellow](no domain packs found)[/yellow]")
        return
    table = Table(title="Domain packs")
    table.add_column("id")
    table.add_column("name")
    table.add_column("version")
    for pack in packs:
        card = pack.card()
        table.add_row(card.id, card.display_name, card.version)
    console.print(table)


@tasks_app.command("list")
def tasks_list() -> None:
    """List registered capability tests."""
    from duecare.tasks import task_registry
    table = Table(title="Registered tasks")
    table.add_column("id")
    for task_id in task_registry.all_ids():
        table.add_row(task_id)
    console.print(table)


@app.command()
def tree(
    root: Path = typer.Option(Path("packages"), help="Packages root"),
) -> None:
    """Show the module tree (folder-per-module view)."""
    if not root.exists():
        console.print(f"[red]{root} does not exist[/red]")
        raise typer.Exit(1)
    for pkg in sorted(root.iterdir()):
        if not pkg.is_dir():
            continue
        console.print(f"[bold cyan]{pkg.name}[/bold cyan]")
        src = pkg / "src" / "duecare"
        if not src.exists():
            continue
        for layer in sorted(src.iterdir()):
            if not layer.is_dir():
                continue
            console.print(f"  [cyan]{layer.name}/[/cyan]")
            for mod in sorted(layer.iterdir()):
                if mod.is_dir() and mod.name != "tests":
                    console.print(f"    {mod.name}/")


@app.command()
def review(path: Path = typer.Argument(..., help="Module folder path")) -> None:
    """Print the meta files for a module folder."""
    if not path.exists():
        console.print(f"[red]{path} does not exist[/red]")
        raise typer.Exit(1)
    for meta in ("PURPOSE.md", "INPUTS_OUTPUTS.md", "HIERARCHY.md", "TESTS.md", "STATUS.md"):
        file = path / meta
        if file.exists():
            console.print(f"[bold cyan]=== {meta} ===[/bold cyan]")
            console.print(file.read_text(encoding="utf-8"))
            console.print()


@app.command()
def test(
    path: Path = typer.Argument(Path("."), help="Path to test"),
    recursive: bool = typer.Option(True, "-r/--no-recursive", help="Recursively test subtree"),
) -> None:
    """Run pytest scoped to a path."""
    import subprocess
    args = ["pytest", str(path), "-v"]
    console.print(f"[bold]Running:[/bold] {' '.join(args)}")
    result = subprocess.run(args)
    raise typer.Exit(code=result.returncode)


@app.command()
def status() -> None:
    """Show module completeness report."""
    from duecare.agents import agent_registry
    from duecare.models import model_registry
    from duecare.tasks import task_registry
    from duecare.domains import domain_registry, register_discovered

    register_discovered()

    table = Table(title="Duecare completeness")
    table.add_column("Layer")
    table.add_column("Count")
    table.add_row("models", str(len(model_registry)))
    table.add_row("tasks", str(len(task_registry)))
    table.add_row("agents", str(len(agent_registry)))
    table.add_row("domains", str(len(domain_registry)))
    console.print(table)


@runs_app.command("list")
def runs_list(
    root: Path = typer.Option(Path("reports"), help="Reports directory"),
) -> None:
    """List previous workflow runs by scanning the reports folder."""
    if not root.exists():
        console.print("[yellow](no reports yet)[/yellow]")
        return
    table = Table(title="Previous runs")
    table.add_column("run_id")
    for path in sorted(root.glob("*.md")):
        table.add_row(path.stem)
    console.print(table)


def main() -> None:
    """Entry point for the `duecare` script."""
    app()


if __name__ == "__main__":
    main()
''',
}


def main() -> int:
    created = 0
    updated = 0
    for rel, content in FILES.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        p.write_text(content, encoding="utf-8")
        if existed:
            updated += 1
        else:
            created += 1
    print(f"Created: {created}, Updated: {updated}, Total: {len(FILES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
