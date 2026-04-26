"""In-process task queue with separate GPU + CPU worker pools.

Why in-process: a Kaggle notebook is single-machine; one process owns
the GPU (and the loaded Gemma 4 weights) for the duration of the
session. We don't want a Redis hop, a Celery worker, or a second
Python process. Threads + queue.Queue is enough.

Why GPU + CPU pools: GPU work serialises on a single Gemma 4 instance
(loading two would OOM). CPU-bound work (template SQL, regex
moderation, evidence-DB ingestion) runs in parallel.

Usage
-----
    from duecare.server.task_queue import TaskQueue
    q = TaskQueue(gpu_workers=1, cpu_workers=4)

    def handle_classify(payload: dict) -> dict:
        return state.gemma_call(payload["text"], 200)
    q.register("gemma_classify", handle_classify, gpu=True)

    task_id = q.submit("gemma_classify", {"text": "..."})
    # poll: q.get(task_id).status / .result
"""
from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional


log = logging.getLogger(__name__)


@dataclass
class Task:
    task_id: str
    task_type: str
    payload: dict
    gpu: bool = False
    status: str = "pending"            # pending|running|completed|failed
    submitted_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    runtime_seconds: Optional[float] = None
    # Per-task execution trace -- filled in by handlers via add_step()
    # Each entry: {name, status, detail, elapsed_since_start, ts, ...}
    trace: list = field(default_factory=list)
    _step_lock: Any = None

    def add_step(self, name: str, status: str = "ok",
                  detail: Any = None, **fields: Any) -> None:
        """Append a trace step. Handlers call this to surface intermediate
        stages (prescan, grep, RAG, tool call, Gemma) so the UI can
        render a live timeline."""
        if self._step_lock is None:
            self._step_lock = threading.Lock()
        with self._step_lock:
            now = datetime.now()
            elapsed = (
                (now - self.started_at).total_seconds()
                if self.started_at else 0.0)
            entry: dict = {
                "name": name,
                "status": status,
                "ts": now.isoformat(timespec="milliseconds"),
                "elapsed_since_start": round(elapsed, 3),
                "detail": detail,
            }
            for k, v in fields.items():
                entry[k] = v
            self.trace.append(entry)

    def as_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "gpu": self.gpu,
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat(),
            "started_at": (self.started_at.isoformat()
                            if self.started_at else None),
            "completed_at": (self.completed_at.isoformat()
                              if self.completed_at else None),
            "result": self.result,
            "error": self.error,
            "runtime_seconds": self.runtime_seconds,
            "trace": list(self.trace),
        }


# Thread-local that points to the Task currently being processed by
# this worker thread. Handlers can call `step("name")` from anywhere
# in their call stack and the trace lands on the right task.
_current = threading.local()


def current_task() -> Optional["Task"]:
    return getattr(_current, "task", None)


def step(name: str, status: str = "ok", detail: Any = None,
          **fields: Any) -> None:
    """Module-level convenience: append a step to the currently
    running task's trace. No-op outside a worker context."""
    t = current_task()
    if t is not None:
        try:
            t.add_step(name, status=status, detail=detail, **fields)
        except Exception:
            pass


class TaskQueue:
    """Two-pool task queue. GPU pool serialises Gemma calls; CPU pool
    runs everything else in parallel."""

    def __init__(self, gpu_workers: int = 1,
                  cpu_workers: int = 4,
                  max_history: int = 1000):
        self.tasks: dict[str, Task] = {}
        self.gpu_q: queue.Queue = queue.Queue()
        self.cpu_q: queue.Queue = queue.Queue()
        # task_type -> (handler, requires_gpu)
        self.handlers: dict[str, tuple[Callable, bool]] = {}
        self.max_history = max_history
        self._stop = threading.Event()
        self._workers: list[threading.Thread] = []
        self._lock = threading.Lock()
        for i in range(max(1, gpu_workers)):
            t = threading.Thread(
                target=self._worker_loop,
                args=(self.gpu_q, f"gpu-{i}"),
                daemon=True, name=f"duecare-gpu-{i}")
            t.start()
            self._workers.append(t)
        for i in range(max(1, cpu_workers)):
            t = threading.Thread(
                target=self._worker_loop,
                args=(self.cpu_q, f"cpu-{i}"),
                daemon=True, name=f"duecare-cpu-{i}")
            t.start()
            self._workers.append(t)
        log.info("TaskQueue started: %d GPU + %d CPU workers",
                  gpu_workers, cpu_workers)

    # -- registration --------------------------------------------------------
    def register(self, task_type: str, handler: Callable,
                  gpu: bool = False) -> None:
        """Register a handler. `handler(payload: dict) -> Any`."""
        self.handlers[task_type] = (handler, gpu)
        log.info("registered task type %r (gpu=%s)", task_type, gpu)

    def known_task_types(self) -> list[str]:
        return sorted(self.handlers.keys())

    # -- submit / poll -------------------------------------------------------
    def submit(self, task_type: str, payload: dict) -> str:
        if task_type not in self.handlers:
            raise ValueError(
                f"unknown task type: {task_type!r}. "
                f"Known: {self.known_task_types()}")
        _handler, gpu = self.handlers[task_type]
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = Task(task_id=task_id, task_type=task_type,
                     payload=payload or {}, gpu=gpu)
        with self._lock:
            self.tasks[task_id] = task
            self._evict_old()
        target = self.gpu_q if gpu else self.cpu_q
        target.put(task)
        return task_id

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self.tasks.get(task_id)

    def list(self, limit: int = 100,
              status: Optional[str] = None) -> list[Task]:
        with self._lock:
            items = sorted(self.tasks.values(),
                            key=lambda t: t.submitted_at,
                            reverse=True)
        if status:
            items = [t for t in items if t.status == status]
        return items[:limit]

    def stats(self) -> dict:
        with self._lock:
            counts = {"pending": 0, "running": 0,
                       "completed": 0, "failed": 0}
            for t in self.tasks.values():
                counts[t.status] = counts.get(t.status, 0) + 1
            return {
                "total": len(self.tasks),
                "by_status": counts,
                "gpu_qsize": self.gpu_q.qsize(),
                "cpu_qsize": self.cpu_q.qsize(),
                "registered_handlers": self.known_task_types(),
            }

    def shutdown(self, timeout: float = 5.0) -> None:
        self._stop.set()
        deadline = time.time() + timeout
        for w in self._workers:
            remaining = max(0.0, deadline - time.time())
            w.join(timeout=remaining)

    # -- internals -----------------------------------------------------------
    def _worker_loop(self, q: queue.Queue, worker_name: str) -> None:
        # Optional: import log_buffer lazily so this module doesn't
        # hard-depend on it. The buffer captures task lifecycle so the
        # /logs page can show every state transition.
        try:
            from duecare.server.log_buffer import LOG_BUFFER as _LB
        except Exception:
            _LB = None
        while not self._stop.is_set():
            try:
                task = q.get(timeout=1.0)
            except queue.Empty:
                continue
            handler_entry = self.handlers.get(task.task_type)
            if handler_entry is None:
                task.status = "failed"
                task.error = f"handler vanished for {task.task_type}"
                task.completed_at = datetime.now()
                if _LB:
                    _LB.add("error", "queue", "task_handler_missing",
                              task_id=task.task_id,
                              task_type=task.task_type,
                              worker=worker_name)
                q.task_done()
                continue
            handler, _ = handler_entry
            task.status = "running"
            task.started_at = datetime.now()
            if _LB:
                _LB.add("info", "queue", "task_started",
                          task_id=task.task_id,
                          task_type=task.task_type,
                          worker=worker_name,
                          gpu=task.gpu)
            # Bind this task as "current" for the duration of handler
            # execution so anything in the handler call stack can call
            # `step(...)` and have the trace land on this task.
            _current.task = task
            try:
                task.result = handler(task.payload)
                task.status = "completed"
            except Exception as e:
                task.error = f"{type(e).__name__}: {e}"
                task.status = "failed"
                log.exception("[%s] task %s FAILED",
                                worker_name, task.task_id)
                if _LB:
                    _LB.add_exception("queue", "task_failed", e,
                                        task_id=task.task_id,
                                        task_type=task.task_type,
                                        worker=worker_name)
            task.completed_at = datetime.now()
            if task.started_at:
                task.runtime_seconds = (
                    task.completed_at - task.started_at).total_seconds()
            if _LB and task.status == "completed":
                # Light-weight result preview for logs.
                rp = task.result
                preview: Any = None
                if isinstance(rp, dict):
                    preview = {k: (v[:120] + "…"
                                    if isinstance(v, str) and len(v) > 120
                                    else v)
                                for k, v in list(rp.items())[:8]}
                _LB.add("info", "queue", "task_completed",
                          task_id=task.task_id,
                          task_type=task.task_type,
                          worker=worker_name,
                          runtime_sec=task.runtime_seconds,
                          result_preview=preview,
                          n_steps=len(task.trace))
            # Clear thread-local
            _current.task = None
            q.task_done()

    def _evict_old(self) -> None:
        """Cap task history to max_history (drop oldest completed/failed)."""
        if len(self.tasks) <= self.max_history:
            return
        finished = [t for t in self.tasks.values()
                    if t.status in ("completed", "failed")]
        finished.sort(key=lambda t: t.completed_at or t.submitted_at)
        for t in finished[:len(self.tasks) - self.max_history]:
            self.tasks.pop(t.task_id, None)
