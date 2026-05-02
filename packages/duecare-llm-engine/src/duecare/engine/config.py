"""EngineConfig: maps to the env vars the pipeline script reads."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class EngineConfig(BaseModel):
    """Configuration for one engine invocation. Each field maps to one
    or more env vars consumed by `gemma4_docling_gliner_graph_v1.py`."""

    # Input / output
    input_dir: Optional[str] = Field(
        default=None,
        description="Folder of source documents. Maps to MM_IMAGES_DIR. "
                    "If None, the pipeline auto-fetches via Drive + "
                    "Wikimedia + synthetic fallback.")
    output_dir: str = Field(
        default="./multimodal_v1_output",
        description="Where the pipeline writes its JSON outputs. Maps "
                    "to MM_OUT_DIR.")

    # Model
    model: str = Field(
        default="google/gemma-4-e4b-it",
        description="HF model id or local path. Maps to MM_MODEL / "
                    "MM_MODEL_PATH.")
    max_new_tokens: int = Field(default=384)
    temperature: float = Field(default=0.0)

    # Volume caps
    max_images: int = Field(
        default=200,
        description="Hard cap on docs sent to Gemma. Maps to MM_MAX_IMAGES.")
    pdf_max_pages: int = Field(
        default=25,
        description="Per-PDF page cap. Maps to MM_PDF_MAX_PAGES.")

    # Pipeline stage toggles
    enable_tool_calling: bool = Field(default=False)
    enable_pairwise: bool = Field(default=True)
    enable_reactive: bool = Field(default=True)
    enable_consolidation: bool = Field(default=True)
    enable_doc_graph: bool = Field(default=True)
    enable_poc: bool = Field(default=True)

    # Caps for the new stages
    pairwise_per_bundle: int = Field(default=12)
    pairwise_cross_bundle: int = Field(default=12)
    pairwise_random: int = Field(default=8)
    reactive_max_findings: int = Field(default=200)
    doc_graph_cap: int = Field(default=50)

    # Runtime budget (minutes)
    total_runtime_min: int = Field(default=540)
    viz_reserve_min: int = Field(default=30)

    # Where the script lives. The runner calls it as a subprocess.
    script_path: str = Field(
        default="raw_python/gemma4_docling_gliner_graph_v1.py",
        description="Path to the pipeline script (relative to the "
                    "project root, or absolute).")

    # Optional reactive config override path
    reactive_config_path: Optional[str] = Field(default=None)

    def to_env(self) -> dict:
        """Project this config into the env-var dict the pipeline reads."""
        env = {
            "MM_OUT_DIR": self.output_dir,
            "MM_MODEL": self.model,
            "MM_MAX_NEW_TOKENS": str(self.max_new_tokens),
            "MM_TEMPERATURE": str(self.temperature),
            "MM_MAX_IMAGES": str(self.max_images),
            "MM_PDF_MAX_PAGES": str(self.pdf_max_pages),
            "MM_TOOL_CALLING": "1" if self.enable_tool_calling else "0",
            "MM_PAIRWISE_COMPARE": "1" if self.enable_pairwise else "0",
            "MM_REACTIVE_DISABLE": "0" if self.enable_reactive else "1",
            "MM_CONSOLIDATE_ENTITIES": "1" if self.enable_consolidation else "0",
            "MM_GEMMA_DOC_GRAPH": "1" if self.enable_doc_graph else "0",
            "POC_DISABLE": "0" if self.enable_poc else "1",
            "MM_PAIRWISE_PER_BUNDLE": str(self.pairwise_per_bundle),
            "MM_PAIRWISE_CROSS_BUNDLE": str(self.pairwise_cross_bundle),
            "MM_PAIRWISE_RANDOM": str(self.pairwise_random),
            "MM_REACTIVE_MAX_FINDINGS": str(self.reactive_max_findings),
            "MM_GEMMA_DOC_GRAPH_CAP": str(self.doc_graph_cap),
            "MM_TOTAL_RUNTIME_MIN": str(self.total_runtime_min),
            "MM_VIZ_RESERVE_MIN": str(self.viz_reserve_min),
        }
        if self.input_dir:
            env["MM_IMAGES_DIR"] = self.input_dir
        if self.reactive_config_path:
            env["MM_REACTIVE_CONFIG"] = self.reactive_config_path
        return env
