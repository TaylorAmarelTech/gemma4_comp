"""FastAPI factory + run_server entrypoint."""
from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import (FastAPI, HTTPException, Request, BackgroundTasks,
                       UploadFile, File, Form)
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from duecare.server.state import ServerState
from duecare.server.tunnel import open_tunnel
from duecare.server.log_buffer import LOG_BUFFER


# Endpoints that DO NOT require auth (homepage + healthz + status).
_PUBLIC_ENDPOINTS = {"/", "/healthz", "/api/status",
                      "/static", "/enterprise", "/individual",
                      "/knowledge", "/settings"}


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class QueryReq(BaseModel):
    question: str
    prefer_template: bool = True


class ProcessReq(BaseModel):
    input_dir: Optional[str] = None
    max_images: int = 50
    enable_pairwise: bool = True
    enable_reactive: bool = True


class ModerateReq(BaseModel):
    text: str
    locale: str = "en"


class WorkerCheckReq(BaseModel):
    text: str
    locale: str = "en"


class IngestReq(BaseModel):
    output_dir: Optional[str] = None
    pipeline_version: str = "v1"


class ResearchReq(BaseModel):
    endpoint: str = "search"
    args: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_app(state: Optional[ServerState] = None) -> FastAPI:
    state = state or ServerState()

    app = FastAPI(
        title="Duecare",
        version="0.1.0",
        description="Multimodal trafficking-safety harness with "
                    "evidence database, NL query, and pluggable tools.",
    )
    app.state.duecare = state
    # In-memory job registry for /api/process background tasks. Persists
    # for the lifetime of the server process; survives restart only via
    # the training_runs / runs tables in the DB.
    app.state.jobs = {}

    # ------ Auth middleware (DUECARE_API_TOKEN) ----------------------------
    api_token = os.environ.get("DUECARE_API_TOKEN", "").strip()
    if api_token:
        @app.middleware("http")
        async def _require_token(request: Request, call_next):
            path = request.url.path
            if any(path == p or path.startswith(p + "/")
                   for p in _PUBLIC_ENDPOINTS):
                return await call_next(request)
            if path.startswith("/api/"):
                hdr = request.headers.get("authorization", "")
                if hdr != f"Bearer {api_token}":
                    return JSONResponse(
                        {"error": "unauthorized -- set "
                                   "Authorization: Bearer <DUECARE_API_TOKEN>"},
                        status_code=401)
            return await call_next(request)
        print(f"[server] auth ENABLED via DUECARE_API_TOKEN")
    else:
        print(f"[server] auth DISABLED (set DUECARE_API_TOKEN to enable)")

    # ------ Request logger middleware (always on) ------------------------
    import time as _time

    @app.middleware("http")
    async def _log_requests(request: Request, call_next):
        path = request.url.path
        # Skip noisy poll endpoints + static so logs stay readable
        is_quiet = (
            path.startswith("/static/")
            or path.startswith("/api/queue/status/")
            or path.startswith("/api/jobs/")
            or path == "/api/queue/list"
            or path == "/api/queue/stats"
            or path == "/api/stats"
            or path == "/api/logs"
            or path == "/api/logs/stats"
            or path == "/healthz"
        )
        t0 = _time.time()
        try:
            response = await call_next(request)
            duration_ms = int((_time.time() - t0) * 1000)
            if not is_quiet:
                LOG_BUFFER.add(
                    "info" if response.status_code < 400 else "warn",
                    "api", "request_complete",
                    method=request.method, path=path,
                    status=response.status_code,
                    duration_ms=duration_ms)
            return response
        except Exception as e:
            LOG_BUFFER.add_exception(
                "api", "request_failed", e,
                method=request.method, path=path,
                duration_ms=int((_time.time() - t0) * 1000))
            raise

    # ------ healthz (separate from /api/status; no DB call) ----------------
    @app.get("/healthz")
    def healthz():
        return {"ok": True, "ts": datetime.now().isoformat()}

    # ------ Logs page ------------------------------------------------------
    @app.get("/logs", response_class=HTMLResponse)
    def logs_page():
        return _serve_html(static_dir / "logs.html")

    @app.get("/queue", response_class=HTMLResponse)
    def queue_page():
        return _serve_html(static_dir / "queue.html")

    @app.get("/chat", response_class=HTMLResponse)
    def chat_page():
        return _serve_html(static_dir / "chat.html")

    @app.get("/api/logs")
    def api_logs(limit: int = 200, level: Optional[str] = None,
                  source: Optional[str] = None,
                  since_id: Optional[str] = None):
        return LOG_BUFFER.list(limit=limit, level=level,
                                  source=source, since_id=since_id)

    @app.get("/api/logs/stats")
    def api_logs_stats():
        return LOG_BUFFER.stats()

    @app.post("/api/logs/clear")
    def api_logs_clear():
        LOG_BUFFER.clear()
        LOG_BUFFER.add("info", "api", "logs_cleared")
        return {"ok": True}

    # ------ static files ---------------------------------------------------
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)),
                   name="static")
    # Serve the pipeline output dir (entity_graph.html, PNG, etc.) at
    # /pipeline/ so the Knowledge page's iframe can load it.
    pipeline_out = Path(state.pipeline_output_dir)
    if pipeline_out.exists():
        app.mount("/pipeline",
                   StaticFiles(directory=str(pipeline_out)),
                   name="pipeline")

    # ------ Page routes ----------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def homepage():
        return _serve_html(static_dir / "index.html")

    @app.get("/enterprise", response_class=HTMLResponse)
    def enterprise_page():
        return _serve_html(static_dir / "enterprise.html")

    @app.get("/individual", response_class=HTMLResponse)
    def individual_page():
        return _serve_html(static_dir / "individual.html")

    @app.get("/knowledge", response_class=HTMLResponse)
    def knowledge_page():
        return _serve_html(static_dir / "knowledge.html")

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard_page():
        return _serve_html(static_dir / "dashboard.html")

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page():
        return _serve_html(static_dir / "settings.html")

    # ------ API: status ----------------------------------------------------
    @app.get("/api/status")
    def api_status():
        st: ServerState = app.state.duecare
        try:
            runs = st.store.list_runs()
        except Exception as e:
            runs = []
        return {
            "ok": True,
            "version": "0.1.0",
            "db_path": st.db_path,
            "pipeline_output_dir": st.pipeline_output_dir,
            "public_url": st.public_url,
            "runs_in_db": len(runs),
            "latest_run": runs[0] if runs else None,
            "now": datetime.now().isoformat(),
        }

    # ------ API: query (NL -> SQL) ----------------------------------------
    @app.post("/api/query")
    def api_query(req: QueryReq):
        st: ServerState = app.state.duecare
        result = st.translator.answer(
            req.question, prefer_template=req.prefer_template)
        return {
            "question": result.question,
            "method": result.method,
            "template_name": result.template_name,
            "sql": result.sql,
            "params": result.params,
            "rows": result.rows,
            "row_count": result.row_count,
            "error": result.error,
        }

    # ------ API: ingest ----------------------------------------------------
    @app.post("/api/ingest")
    def api_ingest(req: IngestReq):
        st: ServerState = app.state.duecare
        outdir = req.output_dir or st.pipeline_output_dir
        if not Path(outdir).exists():
            raise HTTPException(404, f"output dir not found: {outdir}")
        run_id = st.store.ingest_run(outdir,
                                       pipeline_version=req.pipeline_version)
        return {"run_id": run_id, "output_dir": outdir}

    # ------ API: list entities / findings / runs --------------------------
    @app.get("/api/runs")
    def api_runs():
        return app.state.duecare.store.list_runs()

    @app.get("/api/entities")
    def api_entities(etype: Optional[str] = None,
                       run_id: Optional[str] = None,
                       min_doc_count: int = 1,
                       limit: int = 100):
        return app.state.duecare.store.list_entities(
            run_id=run_id, etype=etype,
            min_doc_count=min_doc_count, limit=limit)

    @app.get("/api/findings")
    def api_findings(trigger: Optional[str] = None,
                       min_severity: float = 0,
                       run_id: Optional[str] = None,
                       limit: int = 100):
        return app.state.duecare.store.list_findings(
            run_id=run_id, trigger_name=trigger,
            min_severity=min_severity, limit=limit)

    # ------ API: graph (entity_graph.json passthrough) --------------------
    @app.get("/api/graph")
    def api_graph(run_id: Optional[str] = None):
        st: ServerState = app.state.duecare
        # Latest run's graph file from the configured output dir.
        graph_path = Path(st.pipeline_output_dir) / "entity_graph.json"
        if not graph_path.exists():
            raise HTTPException(404, f"entity_graph.json not found at "
                                       f"{graph_path}")
        return JSONResponse(json.loads(graph_path.read_text(encoding="utf-8")))

    # ------ API: moderate (Enterprise UC) ----------------------------------
    @app.post("/api/moderate")
    def api_moderate(req: ModerateReq):
        st: ServerState = app.state.duecare
        # Light-weight text moderation: classify with a Gemma call if
        # configured, else heuristic.
        from duecare.server.heuristics import quick_moderate
        LOG_BUFFER.add("info", "moderate", "sync_call",
                         text_chars=len(req.text), locale=req.locale,
                         has_gemma=st._gemma_call is not None)
        result = quick_moderate(req.text, locale=req.locale,
                                  gemma_call=st._gemma_call)
        LOG_BUFFER.add("info", "moderate", "sync_done",
                         verdict=result.get("verdict"),
                         severity=result.get("severity"),
                         mode=result.get("mode"))
        return result

    # ------ API: worker-check (Individual UC) -----------------------------
    @app.post("/api/worker_check")
    def api_worker_check(req: WorkerCheckReq):
        st: ServerState = app.state.duecare
        from duecare.server.heuristics import worker_check
        return worker_check(req.text, locale=req.locale,
                              gemma_call=st._gemma_call)

    # ------ API: file-upload moderation (Enterprise UC) -------------------
    @app.post("/api/moderate_file")
    async def api_moderate_file(
            file: UploadFile = File(...),
            locale: str = Form("en")):
        st: ServerState = app.state.duecare
        from duecare.server.heuristics import (quick_moderate,
                                                  extract_text_from_bytes)
        data = await file.read()
        text = extract_text_from_bytes(data, file.filename or "")
        result = quick_moderate(text, locale=locale,
                                  gemma_call=st._gemma_call)
        result["source"] = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(data),
            "extracted_text_chars": len(text),
            "extracted_text_preview": text[:500],
        }
        return result

    # ------ API: BULK / archive moderation (Enterprise UC) ----------------
    @app.post("/api/moderate_batch", status_code=202)
    async def api_moderate_batch(
            file: UploadFile = File(...),
            locale: str = Form("en"),
            kind: str = Form("moderate")):   # 'moderate' or 'worker_check'
        """Accept a zip / tar / tgz, extract every text/image/PDF/docx
        inside it, and queue one moderation task per file. Returns a
        batch_id + list of (filename, task_id) so the UI can poll
        /api/batch/{batch_id} for live aggregate status."""
        from duecare.server.heuristics import (
            extract_archive_to_files, extract_text_from_bytes)
        st: ServerState = app.state.duecare
        if kind not in ("moderate", "worker_check"):
            raise HTTPException(400,
                f"kind must be 'moderate' or 'worker_check', got {kind!r}")
        data = await file.read()
        try:
            members = extract_archive_to_files(data, file.filename or "")
        except ValueError as e:
            raise HTTPException(400, str(e))
        if not members:
            raise HTTPException(
                400, "archive contained no supported files "
                     "(.txt/.md/.pdf/.docx/.png/.jpg/etc.)")
        # Submit each member as its own queue task -- so the GPU pool
        # serializes and the UI sees per-file progress.
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        files_meta: list[dict] = []
        for path, buf in members:
            text = extract_text_from_bytes(buf, path)
            if not (text or "").strip():
                # Still record it so the UI shows "no text extracted"
                tid = tq.submit(kind, {"text": "[no text extracted]",
                                          "locale": locale})
            else:
                tid = tq.submit(kind, {"text": text, "locale": locale})
            files_meta.append({
                "path": path,
                "task_id": tid,
                "size_bytes": len(buf),
                "extracted_chars": len(text or ""),
            })
        st._batches[batch_id] = {
            "batch_id": batch_id,
            "created_at": datetime.now().isoformat(),
            "kind": kind,
            "locale": locale,
            "source_filename": file.filename or "",
            "source_size_bytes": len(data),
            "files": files_meta,
        }
        LOG_BUFFER.add("info", "batch", "batch_submitted",
                         batch_id=batch_id, kind=kind,
                         file_count=len(files_meta),
                         source=file.filename)
        return {
            "batch_id": batch_id,
            "kind": kind,
            "file_count": len(files_meta),
            "source_filename": file.filename,
            "files": [{"path": f["path"], "task_id": f["task_id"],
                       "size_bytes": f["size_bytes"]}
                       for f in files_meta],
            "poll_url": f"/api/batch/{batch_id}",
        }

    @app.get("/api/batch/{batch_id}")
    def api_batch_status(batch_id: str):
        """Aggregated batch status. For each file in the batch, look up
        the task by id and join the result. Returns rolling counts and
        per-file rows so the UI table can render live."""
        st: ServerState = app.state.duecare
        batch = st._batches.get(batch_id)
        if batch is None:
            raise HTTPException(404, f"unknown batch_id: {batch_id}")
        rows = []
        counts = {"pending": 0, "running": 0,
                   "completed": 0, "failed": 0}
        verdict_counts = {"block": 0, "review": 0, "pass": 0}
        sev_total = 0
        sev_n = 0
        for fmeta in batch["files"]:
            t = tq.get(fmeta["task_id"])
            row = {
                "path": fmeta["path"],
                "task_id": fmeta["task_id"],
                "size_bytes": fmeta["size_bytes"],
                "extracted_chars": fmeta.get("extracted_chars", 0),
                "status": "missing", "verdict": None,
                "severity": None, "runtime_seconds": None,
                "error": None, "reasoning": None,
            }
            if t is not None:
                row["status"] = t.status
                row["runtime_seconds"] = t.runtime_seconds
                row["error"] = t.error
                if (isinstance(t.result, dict)
                        and t.result.get("verdict") is not None):
                    row["verdict"] = t.result["verdict"]
                if isinstance(t.result, dict):
                    row["severity"] = t.result.get("severity")
                    row["reasoning"] = (t.result.get("reasoning")
                                          or t.result.get("advice"))
                    if isinstance(row["severity"], (int, float)):
                        sev_total += float(row["severity"])
                        sev_n += 1
                if t.status in counts:
                    counts[t.status] += 1
                if (row["verdict"] or "") in verdict_counts:
                    verdict_counts[row["verdict"]] += 1
            rows.append(row)
        return {
            "batch_id": batch_id,
            "kind": batch["kind"],
            "locale": batch.get("locale", "en"),
            "source_filename": batch.get("source_filename", ""),
            "created_at": batch.get("created_at"),
            "file_count": len(rows),
            "status_counts": counts,
            "verdict_counts": verdict_counts,
            "avg_severity": (sev_total / sev_n) if sev_n else None,
            "files": rows,
            "is_done": (counts["pending"] == 0 and counts["running"] == 0),
        }

    @app.get("/api/batches")
    def api_list_batches(limit: int = 20):
        """Recent batches (newest first)."""
        st: ServerState = app.state.duecare
        items = sorted(st._batches.values(),
                        key=lambda b: b.get("created_at", ""),
                        reverse=True)[:limit]
        return [{
            "batch_id": b["batch_id"],
            "created_at": b.get("created_at"),
            "kind": b.get("kind"),
            "source_filename": b.get("source_filename", ""),
            "file_count": len(b.get("files") or []),
        } for b in items]

    # ------ API: file-upload worker-check (Individual UC) -----------------
    @app.post("/api/worker_check_file")
    async def api_worker_check_file(
            file: UploadFile = File(...),
            locale: str = Form("en")):
        st: ServerState = app.state.duecare
        from duecare.server.heuristics import (worker_check,
                                                  extract_text_from_bytes)
        data = await file.read()
        text = extract_text_from_bytes(data, file.filename or "")
        result = worker_check(text, locale=locale,
                                gemma_call=st._gemma_call)
        result["source"] = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(data),
            "extracted_text_chars": len(text),
            "extracted_text_preview": text[:500],
        }
        return result

    # ------ API: research / OpenClaw --------------------------------------
    @app.post("/api/research/openclaw")
    def api_research_openclaw(req: ResearchReq):
        st: ServerState = app.state.duecare
        result = st.openclaw.query(endpoint=req.endpoint, **(req.args or {}))
        return {
            "tool_name": result.tool_name,
            "success": result.success,
            "items": result.items,
            "summary": result.summary,
            "error": result.error,
            "fetched_at": result.fetched_at.isoformat(),
        }

    # ------ API: process (background task; returns 202 + job_id) ----------
    @app.post("/api/process", status_code=202)
    def api_process(req: ProcessReq, bg: BackgroundTasks):
        st: ServerState = app.state.duecare
        from duecare.engine import EngineConfig
        cfg = EngineConfig(
            input_dir=req.input_dir,
            output_dir=st.pipeline_output_dir,
            max_images=req.max_images,
            enable_pairwise=req.enable_pairwise,
            enable_reactive=req.enable_reactive,
            script_path=st.pipeline_script_path,
        )
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        app.state.jobs[job_id] = {
            "job_id": job_id, "status": "pending",
            "submitted_at": datetime.now().isoformat(),
            "config": cfg.model_dump(),
        }

        def _run_job():
            app.state.jobs[job_id]["status"] = "running"
            app.state.jobs[job_id]["started_at"] = datetime.now().isoformat()
            try:
                run = st.engine.process_folder(cfg, stream_output=False)
                # Auto-ingest into the evidence DB so the demo flow is
                # one button instead of two.
                run_id = st.store.ingest_run(cfg.output_dir)
                app.state.jobs[job_id].update({
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "n_documents": run.n_documents,
                    "n_entities": run.n_entities,
                    "n_edges": run.n_edges,
                    "n_findings": len(run.findings),
                    "ingested_run_id": run_id,
                })
            except Exception as e:
                app.state.jobs[job_id].update({
                    "status": "failed",
                    "completed_at": datetime.now().isoformat(),
                    "error": f"{type(e).__name__}: {e}",
                })

        bg.add_task(_run_job)
        return {"job_id": job_id, "status": "pending",
                "poll_url": f"/api/jobs/{job_id}"}

    @app.get("/api/jobs/{job_id}")
    def api_job_status(job_id: str):
        job = app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(404, f"unknown job_id: {job_id}")
        return job

    @app.get("/api/jobs")
    def api_jobs_list():
        return list(app.state.jobs.values())

    # ------ Task queue (GPU + CPU worker pools) ---------------------------
    from duecare.server.task_queue import TaskQueue
    tq = TaskQueue(
        gpu_workers=int(os.environ.get("DUECARE_GPU_WORKERS", "1")),
        cpu_workers=int(os.environ.get("DUECARE_CPU_WORKERS", "4")))
    app.state.task_queue = tq

    # Handler registration. GPU=True for anything that calls Gemma in
    # process (so VRAM stays single-tenant). GPU=False for everything
    # the heuristic / template paths handle.
    def _h_moderate(payload: dict) -> dict:
        # Use the multi-stage orchestrator so the task trace records
        # heuristic prescan -> grep KB -> RAG KB -> tool calls -> Gemma.
        from duecare.server.pipeline_steps import orchestrate_moderate
        return orchestrate_moderate(
            payload, gemma_call=app.state.duecare._gemma_call)

    def _h_worker_check(payload: dict) -> dict:
        from duecare.server.pipeline_steps import orchestrate_worker_check
        return orchestrate_worker_check(
            payload, gemma_call=app.state.duecare._gemma_call)

    def _h_query(payload: dict) -> dict:
        result = app.state.duecare.translator.answer(
            payload.get("question", ""),
            prefer_template=payload.get("prefer_template", True))
        return {
            "method": result.method,
            "template_name": result.template_name,
            "sql": result.sql,
            "params": result.params,
            "rows": result.rows,
            "row_count": result.row_count,
            "error": result.error,
        }

    def _h_research(payload: dict) -> dict:
        r = app.state.duecare.openclaw.query(
            endpoint=payload.get("endpoint", "search"),
            **(payload.get("args") or {}))
        return {
            "tool_name": r.tool_name, "success": r.success,
            "items": r.items, "summary": r.summary,
            "error": r.error,
        }

    def _h_pipeline(payload: dict) -> dict:
        from duecare.engine import EngineConfig
        st = app.state.duecare
        cfg = EngineConfig(
            input_dir=payload.get("input_dir"),
            output_dir=st.pipeline_output_dir,
            max_images=int(payload.get("max_images") or 50),
            enable_pairwise=bool(payload.get("enable_pairwise", True)),
            enable_reactive=bool(payload.get("enable_reactive", True)),
            script_path=st.pipeline_script_path,
        )
        run = st.engine.process_folder(cfg, stream_output=False)
        run_id = st.store.ingest_run(cfg.output_dir)
        return {
            "n_documents": run.n_documents,
            "n_entities": run.n_entities,
            "n_edges": run.n_edges,
            "n_findings": len(run.findings),
            "ingested_run_id": run_id,
        }

    def _h_chat(payload: dict) -> dict:
        """Bare-bones Gemma chat for UI debugging. Takes a prompt
        string and an optional max_new_tokens, returns the raw text."""
        st = app.state.duecare
        prompt = (payload.get("prompt") or "").strip()
        if not prompt:
            return {"error": "prompt is empty",
                    "mode": "no-op", "response": ""}
        if st._gemma_call is None:
            return {"error": "Gemma not loaded -- running in heuristic mode",
                    "mode": "no-gemma", "response": ""}
        max_new = int(payload.get("max_new_tokens") or 300)
        import time as _t
        t0 = _t.time()
        try:
            text = st._gemma_call(prompt, max_new_tokens=max_new)
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}",
                    "mode": "gemma-failed", "response": ""}
        return {
            "response": text,
            "mode": "gemma",
            "prompt_chars": len(prompt),
            "response_chars": len(text),
            "elapsed_seconds": round(_t.time() - t0, 3),
        }

    # GPU-bound IF a Gemma backend is wired in; otherwise CPU-bound.
    _has_gemma = state._gemma_call is not None
    tq.register("moderate",     _h_moderate,     gpu=_has_gemma)
    tq.register("worker_check", _h_worker_check, gpu=_has_gemma)
    tq.register("query",        _h_query,        gpu=_has_gemma)
    tq.register("research",     _h_research,     gpu=False)
    tq.register("pipeline",     _h_pipeline,     gpu=True)
    tq.register("chat",         _h_chat,         gpu=_has_gemma)

    @app.post("/api/queue/submit", status_code=202)
    def api_queue_submit(req: dict):
        task_type = req.get("task_type")
        if not task_type:
            LOG_BUFFER.add("warn", "queue", "submit_rejected",
                             reason="task_type missing")
            raise HTTPException(400, "task_type is required")
        payload = req.get("payload") or {}
        try:
            tid = tq.submit(task_type, payload)
        except ValueError as e:
            LOG_BUFFER.add("warn", "queue", "submit_rejected",
                             task_type=task_type, error=str(e))
            raise HTTPException(400, str(e))
        # Light payload preview for logs (don't dump full text fields)
        preview = {k: (v[:120] + "…" if isinstance(v, str) and len(v) > 120
                       else v)
                    for k, v in payload.items()}
        LOG_BUFFER.add("info", "queue", "task_submitted",
                         task_id=tid, task_type=task_type,
                         payload_preview=preview)
        return {"task_id": tid, "status": "pending",
                "poll_url": f"/api/queue/status/{tid}"}

    @app.get("/api/queue/status/{task_id}")
    def api_queue_status(task_id: str):
        task = tq.get(task_id)
        if task is None:
            raise HTTPException(404, f"unknown task_id: {task_id}")
        return task.as_dict()

    @app.get("/api/queue/list")
    def api_queue_list(limit: int = 50, status: Optional[str] = None):
        return [t.as_dict() for t in tq.list(limit=limit, status=status)]

    @app.get("/api/queue/stats")
    def api_queue_stats():
        return tq.stats()

    # ------ API: stats (live counts for the dashboard) --------------------
    @app.get("/api/stats")
    def api_stats():
        st: ServerState = app.state.duecare
        out: dict = {"now": datetime.now().isoformat()}
        try:
            out["runs"] = len(st.store.list_runs())
        except Exception:
            out["runs"] = 0
        try:
            for tbl in ("documents", "entities", "edges", "findings",
                        "pairwise_links", "tool_call_cache"):
                r = st.store.fetchone(f"SELECT COUNT(*) AS n FROM {tbl}")
                out[tbl] = int(r["n"]) if r else 0
        except Exception:
            pass
        try:
            r = st.store.fetchall(
                "SELECT trigger_name, COUNT(*) AS n, "
                "AVG(severity) AS avg_sev FROM findings "
                "WHERE severity > 0 GROUP BY trigger_name "
                "ORDER BY n DESC")
            out["by_trigger"] = r
        except Exception:
            out["by_trigger"] = []
        try:
            r = st.store.fetchall(
                "SELECT etype, COUNT(*) AS n FROM entities "
                "GROUP BY etype ORDER BY n DESC")
            out["by_etype"] = r
        except Exception:
            out["by_etype"] = []
        try:
            r = st.store.fetchall(
                "SELECT bundle, COUNT(*) AS n_findings, "
                "MAX(severity) AS max_sev FROM findings "
                "WHERE bundle != '' GROUP BY bundle "
                "ORDER BY n_findings DESC LIMIT 10")
            out["by_bundle"] = r
        except Exception:
            out["by_bundle"] = []
        try:
            tq_stats = tq.stats()
            out["task_queue"] = tq_stats
        except Exception:
            out["task_queue"] = {}
        out["mode"] = ("gemma" if st._gemma_call else "heuristic")
        out["public_url"] = st.public_url
        return out

    # ------ API: activity (recent task-queue events) ----------------------
    @app.get("/api/activity")
    def api_activity(limit: int = 20):
        return [t.as_dict() for t in tq.list(limit=limit)]

    # ------ API: settings --------------------------------------------------
    @app.get("/api/settings")
    def api_settings_get():
        st: ServerState = app.state.duecare
        return {
            "db_path": st.db_path,
            "pipeline_output_dir": st.pipeline_output_dir,
            "public_url": st.public_url,
            "openclaw_mode": os.environ.get("OPENCLAW_MODE", "online"),
            "openclaw_configured": bool(os.environ.get("OPENCLAW_API_KEY")),
        }

    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _serve_html(path: Path) -> HTMLResponse:
    if not path.exists():
        return HTMLResponse(f"<h1>Page missing: {path.name}</h1>",
                              status_code=404)
    return HTMLResponse(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# run_server: full launch (used by the CLI)
# ---------------------------------------------------------------------------
def run_server(host: str = "0.0.0.0", port: int = 8080,
                tunnel: str = "none",
                state: Optional[ServerState] = None,
                reload: bool = False) -> None:
    """Block-launch the server. If `tunnel` is 'cloudflared' / 'ngrok',
    open the tunnel BEFORE the uvicorn process starts the event loop
    (so the public URL prints first)."""
    import uvicorn

    state = state or ServerState()

    # Kick off the tunnel in a background thread so it can print the
    # URL while uvicorn is still binding.
    if tunnel != "none":
        import threading

        def _tunnel_worker():
            try:
                url = open_tunnel(tunnel, port)
                state.public_url = url
                print(f"\n  ==> open this URL on your laptop:\n  ==> {url}\n")
            except Exception as e:
                print(f"[tunnel] FAILED: {type(e).__name__}: {e}")

        threading.Thread(target=_tunnel_worker, daemon=True).start()

    app = create_app(state)
    uvicorn.run(app, host=host, port=port, reload=reload, log_level="info")
