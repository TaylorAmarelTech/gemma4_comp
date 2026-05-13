"""Process Files harness handler.

Owns:
  - POST /api/process/batch -- multipart upload -> v1.0 bundle envelope
  - POST /api/process/graph-chat -- Gemma 4 query over the last bundle
"""
from __future__ import annotations

import csv as _csv
import io as _io
import json as _json
import re as _re
import zipfile
from datetime import datetime as _dt
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .extractor import ENTITY_PATTERNS
from .prompts import GRAPH_CHAT_SYSTEM_PROMPT, build_context_block


_ROW_CAP = 200


def _parse_upload(filename: str, contents: bytes) -> list[dict]:
    fname_l = filename.lower()
    rows: list[dict] = []
    if fname_l.endswith(".zip"):
        with zipfile.ZipFile(_io.BytesIO(contents)) as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                try:
                    txt = zf.read(name).decode("utf-8", errors="replace")
                except Exception:
                    continue
                rows.append({"row_id": name, "text": txt, "source": filename})
    elif fname_l.endswith(".jsonl"):
        for i, line in enumerate(contents.decode("utf-8", errors="replace").splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                obj = _json.loads(line)
                txt = obj.get("prompt") or obj.get("text") or _json.dumps(obj)
            except Exception:
                txt = line
            rows.append({"row_id": f"line_{i}", "text": txt, "source": filename})
    elif fname_l.endswith(".csv"):
        buf = _io.StringIO(contents.decode("utf-8", errors="replace"))
        reader = _csv.reader(buf)
        all_rows = list(reader)
        start = 1 if all_rows and all_rows[0] else 0
        for i, row in enumerate(all_rows[start:]):
            if not row:
                continue
            rows.append({"row_id": f"row_{i}", "text": row[0], "source": filename})
    else:
        blob = contents.decode("utf-8", errors="replace")
        for i, chunk in enumerate([c for c in blob.split("\n\n") if c.strip()]):
            rows.append({"row_id": f"chunk_{i}", "text": chunk, "source": filename})
    return rows


def _score_rows(rows: list[dict], grep_call: Any) -> tuple[list[dict], dict, dict, dict]:
    results: list[dict] = []
    agg_grep: dict[str, int] = {}
    agg_entity: dict[str, int] = {}
    agg_statute: dict[str, int] = {}

    for row in rows:
        text = row["text"] or ""
        grep_hits: list[dict] = []
        if grep_call is not None:
            try:
                try:
                    gr = grep_call(text) or {}
                except TypeError:
                    gr = grep_call(text, extra_rules=None) or {}
                for h in (gr.get("hits") or [])[:10]:
                    rid = h.get("rule_id") or h.get("id") or "?"
                    grep_hits.append({
                        "rule_id": rid,
                        "category": h.get("category"),
                        "severity": h.get("severity"),
                        "match": (h.get("match_text") or h.get("match") or "")[:120],
                    })
                    agg_grep[rid] = agg_grep.get(rid, 0) + 1
            except Exception:
                pass

        entities: dict[str, list[str]] = {}
        for ent_label, pat in ENTITY_PATTERNS.items():
            hits = pat.findall(text)
            if hits:
                seen = list(dict.fromkeys(hits))[:8]
                entities[ent_label] = seen
                agg_entity[ent_label] = agg_entity.get(ent_label, 0) + len(seen)
                if ent_label == "STATUTE":
                    for s in seen:
                        agg_statute[s] = agg_statute.get(s, 0) + 1

        results.append({
            "row_id": row["row_id"],
            "source": row["source"],
            "char_count": len(text),
            "grep_hits": grep_hits,
            "entities": entities,
        })

    return results, agg_grep, agg_entity, agg_statute


def register_routes(app: Any) -> None:
    """Attach the process routes to a FastAPI app."""

    @app.post("/api/process/batch")
    async def api_process_batch(request: Request) -> Any:
        """Multipart upload -> rows -> GREP hits + entity regex -> v1.0 bundle."""
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            raise HTTPException(400, "no `file` field in multipart upload")
        contents = await upload.read()
        filename = getattr(upload, "filename", "uploaded") or "uploaded"

        try:
            rows = _parse_upload(filename, contents)
        except Exception as e:
            raise HTTPException(400, f"parse failed: {e}")

        capped = rows[:_ROW_CAP]
        results, agg_grep, agg_entity, agg_statute = _score_rows(
            capped, getattr(app.state, "grep_call", None)
        )

        ts = _dt.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        run_id = f"01_process_{ts}"
        top_grep = sorted(agg_grep.items(), key=lambda x: -x[1])[:10]
        top_statute = sorted(agg_statute.items(), key=lambda x: -x[1])[:10]
        bundle = {
            "schema_version": "1.0",
            "kernel_id": "01-duecare-exploration-workbench",
            "run_id": run_id,
            "config": {"row_cap": _ROW_CAP, "source": filename},
            "metadata": {"started_at": ts, "completed_at": ts, "host": "kernel-01"},
            "summary": {
                "n_rows_total": len(rows),
                "n_rows_processed": len(capped),
                "n_grep_rules_fired": len(agg_grep),
                "n_entities_extracted": sum(agg_entity.values()),
                "top_grep": [{"rule_id": r, "count": c} for r, c in top_grep],
                "top_statutes": [{"statute": s, "count": c} for s, c in top_statute],
                "entity_totals": agg_entity,
                "truncated": len(rows) > _ROW_CAP,
            },
            "results": results,
        }
        app.state.last_process_bundle = bundle
        return JSONResponse(bundle)

    @app.post("/api/process/graph-chat")
    async def api_process_graph_chat(request: Request) -> Any:
        """Query Gemma 4 against the most recent bundle uploaded via /api/process/batch."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "invalid JSON body")
        question = (body.get("question") or "").strip()
        if not question:
            raise HTTPException(400, "question is required")

        bundle = getattr(app.state, "last_process_bundle", None)
        gc = getattr(app.state, "gemma_call", None)

        if bundle is None:
            return JSONResponse({
                "answer": "No bundle has been uploaded yet on this kernel. "
                "Upload a ZIP/CSV/JSONL on the Process Files tab first, then "
                "ask the question again.",
                "bundle_present": False,
                "cited_rows": [],
                "grep_hits": 0,
            })

        if gc is None:
            summary = bundle.get("summary") or {}
            top = (summary.get("top_grep") or [])[:3]
            return JSONResponse({
                "answer": (
                    "No model is loaded; cannot synthesize a narrative. "
                    f"Bundle has {summary.get('n_rows_processed', 0)} rows "
                    f"with {summary.get('n_grep_rules_fired', 0)} unique GREP "
                    f"rules fired. Top: "
                    + ", ".join(f"{t['rule_id']} ({t['count']})" for t in top)
                ),
                "bundle_present": True,
                "cited_rows": [r["row_id"] for r in (bundle.get("results") or [])[:5]],
                "grep_hits": sum(c["count"] for c in (summary.get("top_grep") or [])),
                "fallback": "no_model_loaded",
            })

        # Layer composition: GREP + RAG + Tools against the user question so
        # the answer cites legal context, not just bundle row_ids. Wired
        # layers run; missing ones skipped silently.
        from .._layers import compose_layers
        layer_out = compose_layers(app, question, layers=("grep", "rag", "tools"))
        context_block = build_context_block(bundle)
        system_text = GRAPH_CHAT_SYSTEM_PROMPT + "\n\n" + context_block
        if layer_out["grounding"]:
            system_text += "\n\nAdditional grounding:\n" + layer_out["grounding"]
        msgs = [
            {"role": "system", "content": [{"type": "text", "text": system_text}]},
            {"role": "user", "content": [{"type": "text", "text": question}]},
        ]
        try:
            model_out = gc(msgs, max_new_tokens=600, temperature=0.3)
            response_text = model_out if isinstance(model_out, str) else (
                (model_out or {}).get("text") or (model_out or {}).get("response") or ""
            )
        except Exception as e:
            return JSONResponse(
                {"answer": f"Model call failed: {str(e)[:200]}", "bundle_present": True},
                status_code=500,
            )

        results = bundle.get("results") or []
        cited_rows: list[str] = []
        for r in results:
            rid = r.get("row_id") or ""
            if rid and rid in response_text:
                cited_rows.append(rid)
        cited_rows = cited_rows[:20]

        summary = bundle.get("summary") or {}
        return JSONResponse({
            "answer": response_text,
            "bundle_present": True,
            "cited_rows": cited_rows,
            "grep_hits": summary.get("n_grep_rules_fired", 0),
            "applied_layers": layer_out["trace"],
        })
