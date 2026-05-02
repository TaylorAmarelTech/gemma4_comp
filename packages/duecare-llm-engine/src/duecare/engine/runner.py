"""Engine: launches the pipeline as a subprocess + materialises a Run."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from duecare.engine.config import EngineConfig
from duecare.engine.results import Run


class EngineError(RuntimeError):
    pass


class Engine:
    """Process documents through the multimodal-graph pipeline."""

    def __init__(self, project_root: Optional[str] = None) -> None:
        # Project root is auto-detected: walk up from cwd until we find
        # a directory containing `raw_python/gemma4_docling_gliner_graph_v1.py`.
        self.project_root = (Path(project_root) if project_root
                              else _detect_project_root())

    def process_folder(self, cfg: EngineConfig,
                          stream_output: bool = True) -> Run:
        """Run the full pipeline against `cfg.input_dir` and return a
        materialised Run. Set `stream_output=False` for quiet mode."""
        script = self._resolve_script(cfg)
        env = os.environ.copy()
        env.update(cfg.to_env())
        Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)
        started_at = datetime.now()
        cmd = [sys.executable, str(script)]
        if stream_output:
            print(f"[engine] launching: {' '.join(cmd)}")
            print(f"[engine] env overrides: "
                  f"{ {k: v for k, v in cfg.to_env().items()} }")
        proc = subprocess.run(
            cmd,
            env=env,
            cwd=str(self.project_root),
            stdout=(None if stream_output else subprocess.PIPE),
            stderr=(None if stream_output else subprocess.PIPE),
            check=False,
        )
        if proc.returncode != 0:
            raise EngineError(
                f"pipeline exited with code {proc.returncode}. "
                f"stdout: {proc.stdout!r} stderr: {proc.stderr!r}")
        run = Run.load(cfg.output_dir)
        run.started_at = started_at
        run.completed_at = datetime.now()
        return run

    def load_run(self, output_dir: str) -> Run:
        """Materialise a Run from an existing output directory without
        re-running the pipeline."""
        return Run.load(output_dir)

    # ---- helpers ----------------------------------------------------------
    def _resolve_script(self, cfg: EngineConfig) -> Path:
        p = Path(cfg.script_path)
        if p.is_absolute() and p.exists():
            return p
        candidate = self.project_root / cfg.script_path
        if candidate.exists():
            return candidate
        raise EngineError(
            f"pipeline script not found at {p} or {candidate}. "
            f"Set EngineConfig.script_path to the absolute path of "
            f"gemma4_docling_gliner_graph_v1.py.")


def _detect_project_root() -> Path:
    """Walk up from cwd looking for raw_python/<pipeline-script>."""
    here = Path.cwd().resolve()
    needle = "raw_python/gemma4_docling_gliner_graph_v1.py"
    for parent in [here, *here.parents]:
        if (parent / needle).exists():
            return parent
    return here
