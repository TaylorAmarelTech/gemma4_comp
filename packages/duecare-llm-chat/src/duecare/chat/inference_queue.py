"""Multi-user inference queue with per-slot state machine.

Wraps the chat backend (and optional judge backend) so concurrent
callers get FIFO-ish ordering, position visibility, MAX_WAITING
backpressure, and use-after-free protection during model swaps.

Extracted out of ``kaggle/01-duecare-exploration-workbench/kernel.py``
on 2026-05-20 as part of the kernel demonolitisation pass.

Public API:

  * :class:`ModelQueue` -- per-slot Lock + ticket list + state machine.
  * :class:`QueueFull` -- raised when MAX_WAITING tickets are pending
    on a slot. HTTP 503 in the FastAPI layer.
  * :class:`QueueClosed` -- raised when a request arrives at a slot
    that is not currently accepting tickets (load/unload window).
    HTTP 503 in the FastAPI layer.

Wiring (in the kernel):

    from duecare.chat.inference_queue import (
        ModelQueue, QueueFull, QueueClosed,
    )

    MODEL_QUEUE = ModelQueue()

    def queue_wrap(backend_fn, slot_name):
        return MODEL_QUEUE.wrap(backend_fn, slot_name)

    # Then assign:
    app.state.gemma_call = queue_wrap(backend, "chat")
    MODEL_QUEUE.open_slot("chat")
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any


class QueueFull(Exception):
    """Raised when more than :attr:`ModelQueue.MAX_WAITING` tickets are
    already queued for the same slot. Surfaced as HTTP 503 so the UI
    can show "the kernel is busy" instead of timing out."""


class QueueClosed(Exception):
    """Raised when a request arrives at a slot that is not accepting
    new tickets. Happens during model unload/load transitions: while
    the operator is swapping the resident model, new requests are
    refused with HTTP 503 to prevent a crash mid-generate when the
    underlying tensors get freed."""


class ModelQueue:
    """Thread-safe inference queue manager for the chat + judge slots.

    Per-slot state machine:

      * ``closed``   -- no model loaded; new tickets are refused.
      * ``open``     -- accepting tickets normally.
      * ``draining`` -- :meth:`close_slot` was called; in-flight
                        tickets run to completion but new tickets are
                        refused.

    Transitions::

        closed --(open_slot)-->   open
        open   --(close_slot)-->  draining (then closed when active=0)
        draining --(open_slot)--> open (if a load races a re-open)

    Load/unload endpoints call :meth:`close_slot` before freeing
    tensors and :meth:`open_slot` after a fresh backend is wired, so
    concurrent users cannot trigger a use-after-free on the model
    weights.
    """

    MAX_WAITING = 5
    MAX_CALL_SECONDS = 30 * 60      # 30-minute generous cap for 31B prompts
    DRAIN_POLL_SECONDS = 0.25       # legacy fallback; Event-based drain skips this

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_DRAINING = "draining"

    def __init__(self) -> None:
        # Re-entrant because snapshot() may be called from within
        # wrap() during logging in future extensions.
        self._meta = threading.RLock()
        self._slots: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Slot state machine
    # ------------------------------------------------------------------

    def _slot(self, name: str) -> dict[str, Any]:
        """Get-or-create the per-slot bookkeeping dict."""
        with self._meta:
            if name not in self._slots:
                idle = threading.Event()
                idle.set()  # starts idle (no active tickets yet)
                self._slots[name] = {
                    "call_lock": threading.Lock(),
                    "tickets": [],
                    "served_total": 0,
                    "state": self.STATE_CLOSED,
                    "idle_event": idle,
                }
            return self._slots[name]

    def open_slot(self, name: str) -> None:
        """Mark a slot as accepting tickets. Called after a successful
        load (or after a force-cancelled drain that needs to recover)."""
        slot = self._slot(name)
        with self._meta:
            slot["state"] = self.STATE_OPEN

    def close_slot(
        self,
        name: str,
        *,
        wait_seconds: float = 0.0,
        force: bool = False,
    ) -> dict[str, Any]:
        """Refuse new tickets and (optionally) wait for in-flight
        calls to complete.

        Returns a dict describing what happened:

          * ``state``: final slot state ("closed" or "draining")
          * ``active_at_close``: how many tickets were running when
            close started
          * ``waiting_at_close``: how many tickets were waiting when
            close started
          * ``drained``: True if the active set was 0 at exit
          * ``waited_seconds``: how long the drain took
          * ``forced``: True if ``force=True`` skipped the drain

        With ``force=True``, the close happens immediately regardless
        of in-flight calls. The caller is responsible for the
        downstream effect (model.generate may raise when tensors are
        freed out from under it). With ``force=False`` and a non-zero
        ``wait_seconds``, the call blocks on the slot's
        ``idle_event`` (set by wrap() when the last active ticket
        completes) until either the event fires or the timeout
        elapses.
        """
        slot = self._slot(name)
        with self._meta:
            tickets = list(slot["tickets"])
            active_at_close = sum(1 for t in tickets if t["started_at"] is not None)
            waiting_at_close = sum(1 for t in tickets if t["started_at"] is None)
            # Mark draining FIRST so no new tickets sneak in past the
            # snapshot we just took.
            slot["state"] = self.STATE_DRAINING

        start = time.time()
        deadline = start + max(0.0, float(wait_seconds))

        if force:
            with self._meta:
                slot["state"] = self.STATE_CLOSED
            return {
                "state": self.STATE_CLOSED,
                "active_at_close": active_at_close,
                "waiting_at_close": waiting_at_close,
                "drained": active_at_close == 0,
                "waited_seconds": 0.0,
                "forced": True,
            }

        # Event-driven wait: idle_event is SET when no tickets are
        # actively running on the slot. The wrap()'s finally clause
        # sets it the moment the last active ticket completes.
        idle_event = slot["idle_event"]
        remaining = max(0.0, deadline - time.time())
        if remaining > 0:
            idle_event.wait(timeout=remaining)
        with self._meta:
            active_now = sum(
                1 for t in slot["tickets"]
                if t["started_at"] is not None
            )
            if active_now == 0:
                slot["state"] = self.STATE_CLOSED
                return {
                    "state": self.STATE_CLOSED,
                    "active_at_close": active_at_close,
                    "waiting_at_close": waiting_at_close,
                    "drained": True,
                    "waited_seconds": round(time.time() - start, 2),
                    "forced": False,
                }

        # Timed out -- slot stays in DRAINING so existing tickets can
        # still finish but no new tickets enter.
        return {
            "state": self.STATE_DRAINING,
            "active_at_close": active_at_close,
            "waiting_at_close": waiting_at_close,
            "drained": False,
            "waited_seconds": round(time.time() - start, 2),
            "forced": False,
        }

    def is_busy(self, name: str) -> bool:
        """Quick check used by load/unload endpoints to refuse a
        model switch when the slot still has work in flight."""
        with self._meta:
            slot = self._slots.get(name)
            if not slot:
                return False
            return any(slot["tickets"])

    def slot_state(self, name: str) -> str:
        """Return the current state literal of a slot, or
        ``STATE_CLOSED`` for unknown slots."""
        with self._meta:
            slot = self._slots.get(name)
            return (slot or {}).get("state", self.STATE_CLOSED)

    # ------------------------------------------------------------------
    # Wrapper + snapshot
    # ------------------------------------------------------------------

    def wrap(self, backend_fn, slot_name: str):
        """Return a queue-aware wrapper around ``backend_fn``.

        The wrapper:

          1. Enqueues a ticket with id + enqueued-at timestamp.
          2. Refuses if the slot is not OPEN (raises QueueClosed).
          3. Refuses if MAX_WAITING tickets already wait (QueueFull).
          4. Acquires the slot's call_lock, stamping started-at.
          5. Re-checks state after acquire -- if the slot transitioned
             to draining/closed during the wait, releases the lock
             and raises QueueClosed.
          6. Calls the wrapped backend with the original args.
          7. Always releases the lock + removes the ticket in finally,
             setting idle_event when no other active ticket remains.

        Raises ``QueueFull`` if too many tickets are already waiting.
        Raises ``QueueClosed`` if the slot is not accepting tickets.
        Never raises during the actual model call -- exceptions from
        the wrapped backend propagate cleanly.
        """
        slot_name = str(slot_name)

        def queued(*args, **kwargs):
            slot = self._slot(slot_name)
            ticket = {
                "id": uuid.uuid4().hex[:12],
                "slot": slot_name,
                "enqueued_at": time.time(),
                "started_at": None,
            }
            with self._meta:
                state = slot.get("state", self.STATE_CLOSED)
                if state != self.STATE_OPEN:
                    raise QueueClosed(
                        f"The {slot_name} model is not accepting new "
                        f"requests (state={state}). The operator is "
                        f"probably swapping models. Please retry in "
                        f"a few seconds."
                    )
                waiting = sum(
                    1 for t in slot["tickets"] if t["started_at"] is None
                )
                if waiting >= self.MAX_WAITING:
                    raise QueueFull(
                        f"Inference queue full: {waiting} requests are "
                        f"already waiting on the {slot_name} model. "
                        f"Please retry in a few seconds."
                    )
                slot["tickets"].append(ticket)
            try:
                slot["call_lock"].acquire()
                # Re-check state after acquire. The slot may have
                # transitioned to draining/closed while we were
                # waiting for the lock (force-unload from another
                # caller). If so, release the lock and refuse with
                # QueueClosed so the call never reaches a possibly-
                # None backend.
                with self._meta:
                    post_state = slot.get("state", self.STATE_CLOSED)
                if post_state != self.STATE_OPEN:
                    slot["call_lock"].release()
                    raise QueueClosed(
                        f"The {slot_name} model was unloaded while this "
                        f"request was waiting in line. Retry once the "
                        f"new model finishes loading."
                    )
                ticket["started_at"] = time.time()
                slot["idle_event"].clear()
                try:
                    return backend_fn(*args, **kwargs)
                finally:
                    slot["call_lock"].release()
                    with self._meta:
                        slot["served_total"] = (
                            slot.get("served_total", 0) + 1
                        )
                        any_active = any(
                            t["started_at"] is not None
                            and t is not ticket
                            for t in slot["tickets"]
                        )
                        if not any_active:
                            slot["idle_event"].set()
            finally:
                with self._meta:
                    try:
                        slot["tickets"].remove(ticket)
                    except ValueError:
                        pass

        try:
            queued.__name__ = f"queued_{slot_name}_call"
            queued.__wrapped__ = backend_fn
        except Exception:
            pass
        return queued

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-friendly snapshot of every slot's queue state."""
        now = time.time()
        with self._meta:
            slots_out: dict[str, Any] = {}
            for slot_name, slot in self._slots.items():
                tickets = list(slot["tickets"])
                active = [t for t in tickets if t["started_at"] is not None]
                waiting = [t for t in tickets if t["started_at"] is None]
                waiting.sort(key=lambda t: t["enqueued_at"])
                slots_out[slot_name] = {
                    "state": slot.get("state", self.STATE_CLOSED),
                    "n_active": len(active),
                    "n_waiting": len(waiting),
                    "served_total": int(slot.get("served_total", 0)),
                    "active": [
                        {
                            "ticket_id": t["id"],
                            "started_at": t["started_at"],
                            "elapsed_secs": round(
                                now - (t["started_at"] or now), 2
                            ),
                        }
                        for t in active
                    ],
                    "waiting": [
                        {
                            "ticket_id": t["id"],
                            "enqueued_at": t["enqueued_at"],
                            "wait_secs": round(now - t["enqueued_at"], 2),
                            "position": idx + 1,
                        }
                        for idx, t in enumerate(waiting)
                    ],
                }
            return {
                "queued_at": now,
                "max_waiting": self.MAX_WAITING,
                "slots": slots_out,
            }


__all__ = [
    "ModelQueue",
    "QueueClosed",
    "QueueFull",
]
