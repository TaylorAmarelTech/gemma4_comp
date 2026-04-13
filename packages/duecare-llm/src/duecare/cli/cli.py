"""The `duecare` CLI. Typer-based.

Commands:
  duecare run            - run a workflow
  duecare runs list      - list previous runs
  duecare agents list    - list registered agents
  duecare models list    - list registered model adapters
  duecare domains list   - list available domain packs
  duecare tasks list     - list registered capability tests
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
