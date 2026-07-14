"""Plan-only bridge to DueCare's validated training surfaces.

Dry-run mode writes a ``TrainingPlan`` manifest. GPU training is owned by the
strict ``scripts/training_engine.py`` pipeline and the active A-00 Kaggle
workbench, which enforce dataset, quality, provenance, and held-out gates.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

DEFAULT_BASE_MODEL = "google/gemma-4-E4B-it"
CANONICAL_GPU_COMMAND = "python scripts/training_engine.py --with-gpu"
ACTIVE_KAGGLE_WORKBENCH = "kaggle/A-00-omni-experiment-workbench"


@dataclass
class TrainingPlan:
    """Manifest the validated training engine or A-00 workbench can consume."""
    training_run_id: str
    base_model: str
    dataset_train_path: str
    dataset_val_path: str
    dataset_test_path: str
    output_lora_path: str
    config: dict = field(default_factory=dict)
    notes: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "training_run_id": self.training_run_id,
            "base_model": self.base_model,
            "dataset_train_path": self.dataset_train_path,
            "dataset_val_path": self.dataset_val_path,
            "dataset_test_path": self.dataset_test_path,
            "output_lora_path": self.output_lora_path,
            "config": self.config,
            "notes": self.notes,
        }, indent=2, default=str)


class UnslothTrainer:
    """Bridge between labeled examples and the validated training surfaces.

    `kickoff()` writes a TrainingPlan manifest and persists a row in
    the training_runs table. Dry-run mode writes the manifest only
    (status='dry_run'). A for-real request is recorded as
    ``handoff_required`` and fails closed with exact handoff instructions;
    this package never bypasses the canonical training gates.
    """

    def __init__(self, store) -> None:
        self.store = store
        from duecare.training.schema import ensure_tables
        ensure_tables(self.store)

    def kickoff(self,
                  manifest_path: str,
                  base_model: str = DEFAULT_BASE_MODEL,
                  output_lora_path: str = "./duecare_lora",
                  config: dict | None = None,
                  dry_run: bool | None = None,
                  notes: str = "") -> TrainingPlan:
        """Write a plan and fail closed when a direct GPU run is requested."""
        run_id = f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}_" \
                  f"{uuid.uuid4().hex[:6]}"
        manifest_path_p = Path(manifest_path)
        if not manifest_path_p.exists():
            raise FileNotFoundError(
                "dataset manifest not found. "
                "Run `duecare train dataset --output ...` first.")
        manifest = json.loads(manifest_path_p.read_text(encoding="utf-8"))

        plan = TrainingPlan(
            training_run_id=run_id,
            base_model=base_model,
            dataset_train_path=manifest["train_path"],
            dataset_val_path=manifest["val_path"],
            dataset_test_path=manifest["test_path"],
            output_lora_path=str(Path(output_lora_path) / run_id),
            config=(config or _default_lora_config()),
            notes=notes,
        )
        plan_path = manifest_path_p.with_suffix(
            manifest_path_p.suffix + f".train_plan.{run_id}.json")
        plan_path.write_text(plan.to_json(), encoding="utf-8")

        if dry_run is None:
            dry_run = os.environ.get("MM_TRAINING_ENABLED", "0") not in (
                "1", "true", "yes")

        # Persist the run row.
        self.store._upsert("training_runs", "training_run_id", {
            "training_run_id": run_id,
            "started_at": datetime.now(),
            "completed_at": None,
            "status": ("dry_run" if dry_run else "handoff_required"),
            "base_model": base_model,
            "n_examples": manifest["n_total"],
            "n_train": manifest["n_train"],
            "n_val": manifest["n_val"],
            "n_test": manifest["n_test"],
            "dataset_path": str(manifest_path_p),
            "output_lora_path": plan.output_lora_path,
            "config_json": json.dumps(plan.config),
            "metrics_json": "{}",
            "notes": notes or "",
        })

        if dry_run:
            print("[trainer] dry-run plan written")
            print(f"[trainer] strict GPU handoff: {CANONICAL_GPU_COMMAND}")
            print(f"[trainer] Kaggle handoff: {ACTIVE_KAGGLE_WORKBENCH}")
            return plan

        raise NotImplementedError(
            "Direct package training is disabled because it would bypass "
            "required quality and provenance gates. Run "
            f"`{CANONICAL_GPU_COMMAND}` or use `{ACTIVE_KAGGLE_WORKBENCH}`.")


def _default_lora_config() -> dict:
    """Sensible defaults for a Gemma 4 E4B LoRA on a Kaggle T4."""
    return {
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "target_modules": [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        "max_seq_length": 2048,
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 4,
        "warmup_ratio": 0.03,
        "num_train_epochs": 2,
        "learning_rate": 2e-4,
        "fp16": False,
        "bf16": True,
        "logging_steps": 10,
        "save_steps": 200,
        "optim": "adamw_8bit",
        "weight_decay": 0.01,
        "lr_scheduler_type": "cosine",
        "seed": 17,
    }
