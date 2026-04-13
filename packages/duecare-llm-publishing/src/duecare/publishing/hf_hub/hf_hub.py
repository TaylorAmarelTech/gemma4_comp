"""HuggingFace Hub publisher.

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
