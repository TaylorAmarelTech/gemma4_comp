"""Markdown report generation used by the Historian agent."""

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

        return "\n".join(lines)

    def write(
        self,
        run: WorkflowRun,
        **kwargs: Any,
    ) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{run.run_id}.md"
        path.write_text(self.render(run, **kwargs), encoding="utf-8")
        return path
