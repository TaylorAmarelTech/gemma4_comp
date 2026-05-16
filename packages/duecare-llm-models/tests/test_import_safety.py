from __future__ import annotations

import builtins
import importlib
import sys
from types import ModuleType


def test_models_import_does_not_require_ollama_http_dependency(monkeypatch) -> None:
    """Importing `duecare.models` should not require optional Ollama deps."""
    original_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict | None = None,
        locals: dict | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "httpx" or name.startswith("httpx."):
            raise ImportError("httpx intentionally blocked for import-safety test")
        return original_import(name, globals, locals, fromlist, level)

    for module_name in list(sys.modules):
        if module_name == "duecare.models" or module_name.startswith("duecare.models."):
            sys.modules.pop(module_name, None)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    models = importlib.import_module("duecare.models")

    assert models.model_registry.has("ollama")