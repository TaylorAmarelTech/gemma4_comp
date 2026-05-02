"""Ingest pipeline output JSONs into the evidence store.

The multimodal pipeline emits these files to its `MM_OUT_DIR` after a run:

    enriched_results.json            (per-document classification + facts +
                                       gemma_graph + reactive_findings)
    entity_graph.json                (bad_actor_candidates + top_edges +
                                       n_entities + n_communities + ...)
    entity_consolidation_map.json    ({etype::original: canonical} mapping)
    gemma_pairwise_findings.json     (pairwise multi-image comparison)
    reactive_findings.json           (Stage 5d trigger findings)
    case_briefs.json                 (per-bundle Gemma narrative)

`ingest_pipeline_outputs` reads everything that exists and persists it.
Missing files are silently skipped -- the caller may have disabled stages.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def ingest_pipeline_outputs(store,
                              output_dir: str | Path,
                              run_id: str | None = None,
                              pipeline_version: str = "v1") -> str:
    """Read every recognised JSON in `output_dir` and persist to the
    store. Returns the run_id."""
    outdir = Path(output_dir)
    if not outdir.exists():
        raise FileNotFoundError(f"output dir does not exist: {outdir}")

    run_id = run_id or _derive_run_id(outdir)
    started_at = datetime.now()

    # --- 1. Records up-front so foreign-key-style lookups work. -----------
    store.upsert_run({
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": None,
        "pipeline_version": pipeline_version,
        "input_root": str(outdir),
        "n_documents": 0,
        "n_entities": 0,
        "n_edges": 0,
        "n_findings": 0,
        "config_json": "{}",
    })

    n_documents = 0
    n_entities = 0
    n_edges = 0
    n_findings = 0

    # --- 2. enriched_results.json -- per-document records + reactive ------
    enriched_path = outdir / "enriched_results.json"
    rows: list = []
    if enriched_path.exists():
        try:
            rows = json.loads(enriched_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ingest] enriched_results.json parse FAIL: {e}")
            rows = []
    doc_id_by_path: dict = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        image_path = row.get("image_path") or row.get("source_pdf") or ""
        if not image_path:
            continue
        doc_id = _doc_id(run_id, image_path)
        doc_id_by_path[image_path] = doc_id
        parsed = row.get("parsed_response") or {}
        store.upsert_document({
            "doc_id": doc_id,
            "run_id": run_id,
            "image_path": image_path,
            "source_pdf": row.get("source_pdf") or "",
            "bundle": (row.get("case_bundle") or "").strip(),
            "category": parsed.get("category") or "",
            "language": _detect_lang(parsed),
            "parsed_at": datetime.now(),
            "page_count": int(row.get("page_count") or 1),
            "triage_score": _safe_float(row.get("triage_score")),
            "raw_response": json.dumps(parsed, default=str)[:50000],
            "parsed_response": json.dumps(parsed, default=str)[:50000],
        })
        n_documents += 1

        # gemma_graph entities -> entity_documents linking + flagged_findings
        gg = row.get("gemma_graph") or {}
        for ent in gg.get("entities") or []:
            if not isinstance(ent, dict):
                continue
            etype = str(ent.get("type", "")).strip().lower()
            name = str(ent.get("name", "")).strip()
            if not etype or not name:
                continue
            entity_id = _entity_id(etype, name)
            store.upsert_entity({
                "entity_id": entity_id,
                "run_id": run_id,
                "etype": etype,
                "canonical_name": name,
                "raw_spellings_json": json.dumps([name]),
                "doc_count": 0,   # recomputed below
                "bundle_count": 0,
                "severity_max": 0,
                "consolidated_from_json": "[]",
            })
            store.link_entity_to_doc(
                entity_id, doc_id,
                raw_spelling=name,
                page=int(ent.get("page") or 0),
                confidence=_safe_float(ent.get("confidence", 1.0)) or 1.0,
                source=str(ent.get("source") or "gemma_graph"))

        # flagged_findings (severity-escalated by reactive trigger handlers)
        for ff in gg.get("flagged_findings") or []:
            if not isinstance(ff, dict):
                continue
            store.upsert_finding({
                "finding_id": str(uuid.uuid4()),
                "run_id": run_id,
                "doc_id": doc_id,
                "bundle": (row.get("case_bundle") or "").strip(),
                "trigger_name": str(ff.get("trigger") or "unknown"),
                "finding_type": str(ff.get("type") or "unknown"),
                "severity": _safe_float(ff.get("severity")) or 0,
                "statute_violated": ff.get("statute_violated") or "",
                "jurisdiction": ff.get("jurisdiction") or "",
                "fee_value": ff.get("fee_value") or "",
                "scheme_pattern": ff.get("scheme_pattern") or "",
                "raw_response": "",
                "parsed_json": json.dumps(ff, default=str),
                "detected_at": datetime.now(),
            })
            n_findings += 1

        # reactive_findings (Stage 5d full records)
        for rf in row.get("reactive_findings") or []:
            if not isinstance(rf, dict):
                continue
            parsed_rf = rf.get("parsed") or {}
            assessment = (parsed_rf.get("assessment") or {}
                          if isinstance(parsed_rf, dict) else {})
            severity = _safe_float(
                assessment.get("severity") if isinstance(assessment, dict)
                else 0) or 0
            store.upsert_finding({
                "finding_id": str(uuid.uuid4()),
                "run_id": run_id,
                "doc_id": doc_id,
                "bundle": (row.get("case_bundle") or "").strip(),
                "trigger_name": str(rf.get("trigger") or "unknown"),
                "finding_type": str(rf.get("trigger") or "unknown"),
                "severity": severity,
                "statute_violated":
                    (assessment.get("statute_violated") if isinstance(assessment, dict) else "") or "",
                "jurisdiction":
                    (assessment.get("jurisdiction") if isinstance(assessment, dict) else "") or "",
                "fee_value": str((rf.get("match") or {}).get("fee_value") or ""),
                "scheme_pattern":
                    (assessment.get("scheme_pattern") if isinstance(assessment, dict) else "") or "",
                "raw_response": str(rf.get("raw_response") or "")[:50000],
                "parsed_json": json.dumps(parsed_rf, default=str)[:50000],
                "detected_at": datetime.now(),
            })
            n_findings += 1
            # Cache any tool calls Gemma asked for.
            for tc in rf.get("tool_calls_executed") or []:
                if isinstance(tc, dict):
                    store.cache_tool_call(
                        tool_name=tc.get("name", "unknown"),
                        args=tc.get("args") or {},
                        result=tc.get("result") or {})

    # --- 3. entity_graph.json -- canonical entities + edges ---------------
    egraph_path = outdir / "entity_graph.json"
    if egraph_path.exists():
        try:
            egraph = json.loads(egraph_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ingest] entity_graph.json parse FAIL: {e}")
            egraph = {}
    else:
        egraph = {}

    for cand in egraph.get("bad_actor_candidates") or []:
        if not isinstance(cand, dict):
            continue
        etype = str(cand.get("type", "")).strip().lower()
        value = str(cand.get("value", "")).strip()
        if not etype or not value:
            continue
        entity_id = _entity_id(etype, value)
        store.upsert_entity({
            "entity_id": entity_id,
            "run_id": run_id,
            "etype": etype,
            "canonical_name": value,
            "raw_spellings_json": json.dumps(cand.get("raw_values") or [value]),
            "doc_count": int(cand.get("doc_count") or 0),
            "bundle_count": int(cand.get("co_occurrence_degree") or 0),
            "severity_max": _safe_float(cand.get("severity_max")) or 0,
            "consolidated_from_json": json.dumps(
                cand.get("consolidated_from") or []),
        })
        n_entities += 1

    for edge in egraph.get("top_edges") or []:
        if not isinstance(edge, dict):
            continue
        a_type = str(edge.get("a_type", "")).strip().lower()
        a_value = str(edge.get("a_value", "")).strip()
        b_type = str(edge.get("b_type", "")).strip().lower()
        b_value = str(edge.get("b_value", "")).strip()
        if not (a_type and a_value and b_type and b_value):
            continue
        a_id = _entity_id(a_type, a_value)
        b_id = _entity_id(b_type, b_value)
        edge_id = _edge_id(a_id, b_id, edge.get("relation_type") or "co_occur")
        store.upsert_edge({
            "edge_id": edge_id,
            "run_id": run_id,
            "a_entity_id": a_id,
            "b_entity_id": b_id,
            "relation_type": str(edge.get("relation_type") or "co_occur"),
            "confidence": _safe_float(edge.get("confidence")) or 0,
            "doc_count": int(edge.get("doc_count") or 0),
            "source": str(edge.get("source") or "co_occur"),
            "evidence_text": str(edge.get("evidence") or "")[:5000],
            "gemma_confirmed": False,
            "gemma_confidence": None,
            "gemma_reasoning": "",
        })
        n_edges += 1
        # Link edges to their evidence docs
        for ed_path in edge.get("documents") or []:
            doc_id = doc_id_by_path.get(ed_path)
            if doc_id:
                store.link_edge_to_doc(edge_id, doc_id)

    # --- 4. gemma_pairwise_findings.json -- pairwise multi-image findings -
    pw_path = outdir / "gemma_pairwise_findings.json"
    if pw_path.exists():
        try:
            pairwise = json.loads(pw_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ingest] gemma_pairwise_findings.json parse FAIL: {e}")
            pairwise = []
        for pf in pairwise or []:
            if not isinstance(pf, dict):
                continue
            doc_a = doc_id_by_path.get(pf.get("doc_a", "")) or _doc_id(
                run_id, pf.get("doc_a", "unknown"))
            doc_b = doc_id_by_path.get(pf.get("doc_b", "")) or _doc_id(
                run_id, pf.get("doc_b", "unknown"))
            rel = pf.get("document_relationship") or {}
            store.upsert_pairwise_link({
                "link_id": str(uuid.uuid4()),
                "run_id": run_id,
                "doc_a_id": doc_a,
                "doc_b_id": doc_b,
                "relationship_type": str(rel.get("type", "")) if isinstance(rel, dict) else "",
                "confidence": _safe_float(
                    rel.get("confidence") if isinstance(rel, dict) else 0) or 0,
                "explanation": str(
                    rel.get("explanation") if isinstance(rel, dict) else "")[:2000],
                "visual_similarities_json": json.dumps(
                    pf.get("visual_similarities") or []),
                "shared_entities_json": json.dumps(
                    pf.get("shared_entities") or []),
            })

    # --- 5. case_briefs.json -- per-bundle Gemma briefs -------------------
    cb_path = outdir / "case_briefs.json"
    if cb_path.exists():
        try:
            briefs = json.loads(cb_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ingest] case_briefs.json parse FAIL: {e}")
            briefs = {}
        for bundle, brief in (briefs or {}).items():
            store.upsert_bundle_summary({
                "bundle": bundle,
                "run_id": run_id,
                "n_documents": 0,
                "n_entities": 0,
                "n_findings": 0,
                "severity_max": 0,
                "brief_text": str(brief)[:50000] if isinstance(brief, str) else
                              json.dumps(brief, default=str)[:50000],
                "top_actors_json": "[]",
                "generated_at": datetime.now(),
            })

    # --- 6. Update run summary --------------------------------------------
    store.upsert_run({
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": datetime.now(),
        "pipeline_version": pipeline_version,
        "input_root": str(outdir),
        "n_documents": n_documents,
        "n_entities": n_entities,
        "n_edges": n_edges,
        "n_findings": n_findings,
        "config_json": "{}",
    })

    print(f"[ingest] run_id={run_id}  docs={n_documents}  "
          f"entities={n_entities}  edges={n_edges}  "
          f"findings={n_findings}")
    return run_id


# ----- helpers ---------------------------------------------------------------
def _derive_run_id(outdir: Path) -> str:
    """Stable run id from the output dir name + a timestamp."""
    return f"{outdir.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _doc_id(run_id: str, path: str) -> str:
    h = hashlib.sha1(f"{run_id}::{path}".encode("utf-8")).hexdigest()[:16]
    return f"doc_{h}"


def _entity_id(etype: str, normalized: str) -> str:
    """Stable id so the same entity across runs reuses the same id (the
    canonical name + type is the natural key)."""
    h = hashlib.sha1(
        f"{etype}::{normalized}".encode("utf-8")).hexdigest()[:16]
    return f"ent_{h}"


def _edge_id(a_id: str, b_id: str, relation: str) -> str:
    pair = "::".join(sorted([a_id, b_id]))
    h = hashlib.sha1(
        f"{pair}::{relation}".encode("utf-8")).hexdigest()[:16]
    return f"edge_{h}"


def _safe_float(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def _detect_lang(parsed: dict) -> str:
    return (parsed.get("language") or parsed.get("doc_language")
            or "unknown")
