"""ModelSlot: shared load/unload orchestrator for chat + judge slots.

Each slot owns its own ``app.state.<attr>`` callable, load-state
dict, lock, and event ring. Both slots need the same unload + purge
logic: drop the callable from ``app.state``, flush CUDA, reset the
state dict, optionally purge the HF safetensors cache. This class
collapses that duplication into a single ``slot.unload(app)`` call
so each FastAPI endpoint becomes a 2-line shim.

Extracted out of ``kaggle/01-duecare-exploration-workbench/kernel.py``
on 2026-05-20 as part of the kernel demonolitisation pass.

The CLASS owns the policy (what to do). The module-level state
dicts / locks / event rings are the DATA the class operates on, kept
at module level in the kernel script so legacy free functions
(``_log_load``, ``_snapshot_load_events``, ...) still work
unchanged.

Wiring:

    from duecare.chat.model_slot import ModelSlot

    _CHAT_SLOT = ModelSlot(
        name="chat",
        app_state_attr="gemma_call",
        state=_MODEL_LOAD_STATE,
        lock=_MODEL_LOAD_LOCK,
        events=_MODEL_LOAD_EVENTS,
        log_fn=_log_load,
        loaded_ref_setter=_set_chat_loaded,
        post_unload_hook=_chat_post_unload,
        purge_fn=_purge_hf_cache_for_variant,
    )

A future endpoint adding a third slot (e.g., a vision model) gets
the same behaviour by constructing another ``ModelSlot`` with its
own backing state.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from fastapi.responses import JSONResponse


class ModelSlot:
    """Shared load/unload + CUDA-flush + cache-purge orchestrator.

    Constructor parameters:

      * ``name``               -- "chat" / "judge". Used in log lines
                                  and the response payload.
      * ``app_state_attr``     -- "gemma_call" / "evaluator_call".
                                  The attribute on app.state that
                                  holds the callable; cleared to None
                                  on unload.
      * ``state``              -- backing dict that mirrors the slot's
                                  load state ("status", "variant",
                                  "phase", "completed_at", ...).
      * ``lock``               -- threading.Lock that gates concurrent
                                  loads. unload() refuses with 409 if
                                  a load is in progress.
      * ``events``             -- event ring (mutated by ``log_fn``).
      * ``log_fn``             -- function (msg, *, phase, level)
                                  that writes to the slot's log.
      * ``loaded_ref_setter``  -- callable that clears the module-
                                  level LoadedModel reference so
                                  torch tensors release.
      * ``post_unload_hook``   -- optional callable (app) -> None for
                                  slot-specific cleanup (e.g., chat
                                  slot resets app.state.model_info).
      * ``purge_fn``           -- optional callable
                                  (variant_id) -> {ok, bytes_freed,
                                  paths_deleted, ...} that purges the
                                  HF cache dir for the unloaded variant.
                                  None disables disk purge regardless
                                  of the ``purge_cache`` kwarg.
    """

    def __init__(
        self,
        name: str,
        app_state_attr: str,
        *,
        state: dict,
        lock: Any,
        events: list,
        log_fn: Callable[..., None],
        loaded_ref_setter: Callable[[Any], None],
        post_unload_hook: Optional[Callable[[Any], None]] = None,
        purge_fn: Optional[Callable[[str], dict]] = None,
    ) -> None:
        self.name = name
        self.app_state_attr = app_state_attr
        self.state = state
        self.lock = lock
        self.events = events
        self.log = log_fn
        self.loaded_ref_setter = loaded_ref_setter
        self.post_unload_hook = post_unload_hook
        self.purge_fn = purge_fn

    def is_loaded(self, app) -> bool:
        return getattr(app.state, self.app_state_attr, None) is not None

    def unload(self, app, *, purge_cache: bool = True) -> Any:
        """Atomically unload the slot.

        Steps (in order):
          1. Return idle no-op if nothing is loaded.
          2. Acquire the slot lock (refuse with 409 if a load is in
             progress -- swapping mid-load is not safe on Unsloth).
          3. Drop the callable from ``app.state.<attr>``.
          4. Clear the loaded LoadedModel reference (so torch tensors
             release).
          5. Flush ``torch.cuda.empty_cache()`` (best-effort) so the
             freed VRAM returns to the pool.
          6. Reset the slot's state dict to idle.
          7. Run the optional ``post_unload_hook`` for slot-specific
             cleanup (e.g., chat slot resets app.state.model_info).
          8. If ``purge_cache=True`` and ``purge_fn`` was provided,
             delete the HF safetensors dir for the unloaded variant.
          9. Return a structured response dict including the purge
             result (``{ok, bytes_freed, paths_deleted, ...}``).
        """
        if not self.is_loaded(app):
            return {"status": "idle",
                    "message": f"No {self.name} model loaded."}
        if not self.lock.acquire(blocking=False):
            return JSONResponse(
                {"status": "busy",
                 "message": (
                     f"A {self.name}-model load is in progress. "
                     "Wait for completion before unloading."
                 )},
                status_code=409,
            )
        try:
            current_variant = self.state.get("variant")
            self.log(f"unloading {self.name} model", phase="unloading")
            # Step 3: drop the callable.
            setattr(app.state, self.app_state_attr, None)
            # Step 4: clear the LoadedModel ref so torch can collect.
            try:
                self.loaded_ref_setter(None)
            except Exception as e:  # noqa: BLE001 -- defensive
                self.log(
                    f"loaded-ref setter raised: {type(e).__name__}: {e}",
                    phase="unloading", level="warn",
                )
            # Step 5: CUDA cache flush (best-effort).
            try:
                import torch as _torch
                _torch.cuda.empty_cache()
                try:
                    _torch.cuda.synchronize()
                except Exception:
                    pass
                self.log("CUDA cache flushed", phase="unloaded")
            except Exception as e:
                self.log(
                    f"CUDA cache flush skipped: {type(e).__name__}",
                    phase="unloaded", level="warn",
                )
            # Step 6: reset slot state.
            self.state.update({
                "status": "idle", "variant": None,
                "selected_display": None, "phase": "idle",
                "completed_at": time.time(), "error": None,
            })
            # Step 7: slot-specific cleanup (e.g., chat slot resets
            # app.state.model_info to a placeholder dict).
            if self.post_unload_hook is not None:
                try:
                    self.post_unload_hook(app)
                except Exception as e:  # noqa: BLE001
                    self.log(
                        f"post_unload_hook raised: {type(e).__name__}: {e}",
                        phase="unloaded", level="warn",
                    )
            # Step 8: optional HF disk purge.
            purged = None
            if purge_cache and current_variant and self.purge_fn is not None:
                purged = self.purge_fn(current_variant)
                if purged.get("ok"):
                    gb = purged.get("gb_freed", 0)
                    self.log(
                        (
                            f"purged HF cache for {current_variant}: "
                            f"{gb:.2f} GB freed"
                        ),
                        phase="purged",
                    )
                else:
                    self.log(
                        (
                            f"cache purge for {current_variant} hit an "
                            f"error: {purged.get('error', 'unknown')}"
                        ),
                        phase="purge-error", level="warn",
                    )
            return {
                "status":  "idle",
                "message": f"{self.name.title()} model unloaded.",
                "purged":  purged,
            }
        finally:
            self.lock.release()


__all__ = ["ModelSlot"]
