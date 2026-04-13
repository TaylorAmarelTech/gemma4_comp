"""CLI entry points. One command per pipeline stage.

See docs/architecture.md section 2 (scripts/) and section 20 (release checklist).
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="gemma4_comp",
    help="Gemma 4 migrant-worker safety judge pipeline.",
    no_args_is_help=True,
)


@app.command()
def ingest() -> None:
    """Run source fetch + normalize + stage."""
    typer.echo("TODO: wire up src.data.ingest pipeline")


@app.command()
def classify() -> None:
    """Run classifier ensemble over the staging DB."""
    typer.echo("TODO: wire up src.data.classify pipeline")


@app.command()
def anonymize() -> None:
    """Run the anonymization gate: detect, redact, verify, quarantine."""
    typer.echo("TODO: wire up src.data.anon pipeline")


@app.command("build-prompts")
def build_prompts() -> None:
    """Build the prompt store from the clean DB."""
    typer.echo("TODO: wire up src.prompts pipeline")


@app.command()
def prepare() -> None:
    """Build the train/val/test JSONL splits for Unsloth."""
    typer.echo("TODO: wire up src.training.prepare")


@app.command()
def finetune() -> None:
    """Run the Unsloth + LoRA fine-tune."""
    typer.echo("TODO: wire up src.training.finetune")


@app.command()
def export(
    target: str = typer.Option("gguf", help="gguf | litert | all"),
) -> None:
    """Export the fine-tuned model to GGUF and/or LiteRT."""
    typer.echo(f"TODO: wire up src.export for target={target}")


@app.command()
def evaluate(
    model: str = typer.Option(..., help="Path to the judge model or 'stock'"),
) -> None:
    """Run the evaluation harness and produce a report."""
    typer.echo(f"TODO: wire up src.eval.runner for model={model}")


@app.command()
def serve(
    port: int = typer.Option(8080, help="Port to bind"),
) -> None:
    """Run the FastAPI demo app."""
    typer.echo(f"TODO: wire up src.demo.app on port={port}")


if __name__ == "__main__":
    app()
