"""Read-only accessor for the training_runs table."""
from __future__ import annotations

from duecare.training.schema import ensure_tables


class TrainingRunsTable:
    def __init__(self, store) -> None:
        self.store = store
        ensure_tables(self.store)

    def list(self, limit: int = 25) -> list[dict]:
        return self.store.fetchall(
            "SELECT training_run_id, started_at, completed_at, status, "
            "base_model, n_examples, n_train, n_val, n_test, "
            "output_lora_path, notes "
            "FROM training_runs ORDER BY started_at DESC LIMIT ?",
            (limit,))

    def get(self, training_run_id: str) -> dict | None:
        return self.store.fetchone(
            "SELECT * FROM training_runs WHERE training_run_id = ?",
            (training_run_id,))

    def latest(self) -> dict | None:
        return self.store.fetchone(
            "SELECT * FROM training_runs ORDER BY started_at DESC LIMIT 1")
