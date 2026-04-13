"""duecare.models - pluggable adapters for every LLM backend.

Every adapter implements duecare.core.contracts.Model and registers itself
under a stable id in model_registry. Importing this package triggers all
built-in adapters to self-register.
"""

from duecare.core.registry import Registry
from duecare.core.contracts import Model

# Global model-adapter registry.
model_registry: Registry = Registry(kind="model")

# Import all built-in adapter modules so they register on import.
# Each adapter handles its own optional-dependency imports internally
# (the adapter module may raise ImportError at call time, but not at
# import time).
from .base import base as _base_module  # noqa: F401,E402
from .transformers_adapter import adapter as _transformers_adapter  # noqa: F401,E402
from .llama_cpp_adapter import adapter as _llama_cpp_adapter  # noqa: F401,E402
from .unsloth_adapter import adapter as _unsloth_adapter  # noqa: F401,E402
from .ollama_adapter import adapter as _ollama_adapter  # noqa: F401,E402
from .openai_compatible_adapter import adapter as _openai_compatible_adapter  # noqa: F401,E402
from .anthropic_adapter import adapter as _anthropic_adapter  # noqa: F401,E402
from .google_gemini_adapter import adapter as _google_gemini_adapter  # noqa: F401,E402
from .hf_inference_endpoint_adapter import adapter as _hf_inference_endpoint_adapter  # noqa: F401,E402

from .base.base import ModelAdapterBase

__all__ = ["model_registry", "Model", "ModelAdapterBase"]
