"""Typed Pydantic models for pipeline outputs."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field


class Entity(BaseModel):
    type: str
    value: str
    raw_values: list[str] = Field(default_factory=list)
    doc_count: int = 0
    bundle_count: int = 0
    severity_max: float = 0
    consolidated_from: list[str] = Field(default_factory=list)


class Edge(BaseModel):
    a_type: str
    a_value: str
    b_type: str
    b_value: str
    relation_type: str = "co_occur"
    confidence: float = 0
    doc_count: int = 0
    source: str = ""
    evidence_text: str = ""


class Finding(BaseModel):
    trigger: str
    doc: str
    bundle: str = ""
    finding_type: str = ""
    severity: float = 0
    statute_violated: str = ""
    jurisdiction: str = ""
    fee_value: str = ""
    scheme_pattern: str = ""
    raw_response: str = ""
    parsed: dict = Field(default_factory=dict)
    tool_calls_executed: list[dict] = Field(default_factory=list)


class Document(BaseModel):
    image_path: str
    source_pdf: str = ""
    bundle: str = ""
    category: str = ""
    parsed_response: dict = Field(default_factory=dict)
    gemma_graph: dict = Field(default_factory=dict)
    reactive_findings: list[dict] = Field(default_factory=list)


class PairwiseLink(BaseModel):
    doc_a: str
    doc_b: str
    bundle_a: str = ""
    bundle_b: str = ""
    shared_entities: list[dict] = Field(default_factory=list)
    document_relationship: dict = Field(default_factory=dict)
    visual_similarities: list[str] = Field(default_factory=list)


class Run(BaseModel):
    output_dir: str
    n_documents: int = 0
    n_entities: int = 0
    n_edges: int = 0
    documents: list[Document] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    pairwise_links: list[PairwiseLink] = Field(default_factory=list)
    case_briefs: dict = Field(default_factory=dict)
    consolidation_map: dict = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @classmethod
    def load(cls, output_dir: str | Path) -> "Run":
        """Load a Run from a pipeline output directory."""
        outdir = Path(output_dir)
        run = cls(output_dir=str(outdir))

        # enriched_results.json
        er = outdir / "enriched_results.json"
        if er.exists():
            try:
                rows = json.loads(er.read_text(encoding="utf-8"))
            except Exception:
                rows = []
            for r in rows or []:
                if not isinstance(r, dict):
                    continue
                doc = Document(
                    image_path=r.get("image_path") or "",
                    source_pdf=r.get("source_pdf") or "",
                    bundle=r.get("case_bundle") or "",
                    category=(r.get("parsed_response") or {}).get("category", ""),
                    parsed_response=r.get("parsed_response") or {},
                    gemma_graph=r.get("gemma_graph") or {},
                    reactive_findings=r.get("reactive_findings") or [],
                )
                run.documents.append(doc)
                # Pull findings out of reactive_findings
                for rf in (r.get("reactive_findings") or []):
                    if not isinstance(rf, dict):
                        continue
                    parsed = rf.get("parsed") or {}
                    assess = parsed.get("assessment", {}) if isinstance(parsed, dict) else {}
                    run.findings.append(Finding(
                        trigger=rf.get("trigger") or "unknown",
                        doc=r.get("image_path") or "",
                        bundle=r.get("case_bundle") or "",
                        finding_type=rf.get("trigger") or "",
                        severity=float(assess.get("severity") or 0)
                                 if isinstance(assess, dict) else 0,
                        statute_violated=str(assess.get("statute_violated") or "")
                                         if isinstance(assess, dict) else "",
                        jurisdiction=str(assess.get("jurisdiction") or "")
                                     if isinstance(assess, dict) else "",
                        raw_response=rf.get("raw_response") or "",
                        parsed=parsed if isinstance(parsed, dict) else {},
                        tool_calls_executed=rf.get("tool_calls_executed") or [],
                    ))
            run.n_documents = len(run.documents)

        # entity_graph.json
        eg = outdir / "entity_graph.json"
        if eg.exists():
            try:
                graph = json.loads(eg.read_text(encoding="utf-8"))
            except Exception:
                graph = {}
            for c in graph.get("bad_actor_candidates") or []:
                run.entities.append(Entity(
                    type=c.get("type") or "",
                    value=c.get("value") or "",
                    raw_values=c.get("raw_values") or [],
                    doc_count=int(c.get("doc_count") or 0),
                    bundle_count=int(c.get("co_occurrence_degree") or 0),
                    consolidated_from=c.get("consolidated_from") or [],
                ))
            for e in graph.get("top_edges") or []:
                run.edges.append(Edge(
                    a_type=e.get("a_type") or "",
                    a_value=e.get("a_value") or "",
                    b_type=e.get("b_type") or "",
                    b_value=e.get("b_value") or "",
                    relation_type=e.get("relation_type") or "co_occur",
                    confidence=float(e.get("confidence") or 0),
                    doc_count=int(e.get("doc_count") or 0),
                    source=e.get("source") or "",
                    evidence_text=str(e.get("evidence") or "")[:5000],
                ))
            run.n_entities = int(graph.get("n_entities") or len(run.entities))
            run.n_edges = int(graph.get("n_edges") or len(run.edges))

        # pairwise findings
        pw = outdir / "gemma_pairwise_findings.json"
        if pw.exists():
            try:
                pwd = json.loads(pw.read_text(encoding="utf-8"))
            except Exception:
                pwd = []
            for pf in pwd or []:
                run.pairwise_links.append(PairwiseLink(
                    doc_a=pf.get("doc_a") or "",
                    doc_b=pf.get("doc_b") or "",
                    bundle_a=pf.get("bundle_a") or "",
                    bundle_b=pf.get("bundle_b") or "",
                    shared_entities=pf.get("shared_entities") or [],
                    document_relationship=pf.get("document_relationship") or {},
                    visual_similarities=pf.get("visual_similarities") or [],
                ))

        # case_briefs.json
        cb = outdir / "case_briefs.json"
        if cb.exists():
            try:
                run.case_briefs = json.loads(cb.read_text(encoding="utf-8"))
            except Exception:
                run.case_briefs = {}

        # consolidation map
        cm = outdir / "entity_consolidation_map.json"
        if cm.exists():
            try:
                run.consolidation_map = json.loads(cm.read_text(encoding="utf-8"))
            except Exception:
                run.consolidation_map = {}

        return run
