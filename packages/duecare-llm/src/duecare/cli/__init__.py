"""duecare CLI entry point."""

from typer.main import get_command

from .cli import app, main

cli = get_command(app)

__all__ = ["app", "cli", "main"]
