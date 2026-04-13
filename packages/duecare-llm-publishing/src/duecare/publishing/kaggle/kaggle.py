"""Kaggle CLI wrapper.

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
                f"kaggle command failed: {' '.join(args)}\n"
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
