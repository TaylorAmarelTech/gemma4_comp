"""Real tests for duecare.observability.metrics.MetricsSink."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from duecare.observability.metrics import MetricsSink


@pytest.fixture
def sink_path(tmp_path: Path) -> Path:
    return tmp_path / "metrics.jsonl"


def test_write_single_metric(sink_path: Path):
    sink = MetricsSink(sink_path)
    sink.write("run_1", "grade_exact_match", 0.68)
    rows = [json.loads(line) for line in sink_path.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["run_id"] == "run_1"
    assert rows[0]["metric"] == "grade_exact_match"
    assert rows[0]["value"] == 0.68
    assert "timestamp" in rows[0]


def test_write_with_agent_and_task(sink_path: Path):
    sink = MetricsSink(sink_path)
    sink.write(
        "run_1",
        "ilo_recall",
        0.91,
        agent_id="judge",
        model_id="gemma-4-e4b",
        domain_id="trafficking",
        task_id="guardrails",
    )
    row = json.loads(sink_path.read_text().splitlines()[0])
    assert row["agent_id"] == "judge"
    assert row["model_id"] == "gemma-4-e4b"
    assert row["domain_id"] == "trafficking"
    assert row["task_id"] == "guardrails"


def test_write_with_extra(sink_path: Path):
    sink = MetricsSink(sink_path)
    sink.write("run_1", "latency_ms", 42, extra={"p95": 100})
    row = json.loads(sink_path.read_text().splitlines()[0])
    assert row["extra"]["p95"] == 100


def test_write_creates_parent_dir(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "metrics.jsonl"
    sink = MetricsSink(path)
    sink.write("r", "m", 1.0)
    assert path.exists()


def test_many_writes_append(sink_path: Path):
    sink = MetricsSink(sink_path)
    for i in range(100):
        sink.write(f"run_{i}", "score", float(i) / 100.0)
    rows = sink_path.read_text().splitlines()
    assert len(rows) == 100


def test_bulk_write(sink_path: Path):
    sink = MetricsSink(sink_path)
    sink.bulk_write([
        {"run_id": "a", "metric": "x", "value": 1.0},
        {"run_id": "b", "metric": "y", "value": 2.0},
    ])
    rows = sink_path.read_text().splitlines()
    assert len(rows) == 2
    assert json.loads(rows[0])["run_id"] == "a"
    assert json.loads(rows[1])["run_id"] == "b"


def test_float_coercion(sink_path: Path):
    sink = MetricsSink(sink_path)
    sink.write("r", "m", 42)  # int, should be coerced to float
    row = json.loads(sink_path.read_text().splitlines()[0])
    assert row["value"] == 42.0
    assert isinstance(row["value"], float)
