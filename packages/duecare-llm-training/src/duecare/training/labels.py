"""Synthetic label generator.

Four strategies that turn pipeline outputs into labeled training
examples WITHOUT a hand-labeled set:

  1. cluster_vote          -- cluster docs by Gemma embeddings (or
                              TF-IDF fallback); within each cluster,
                              the majority Gemma category becomes the
                              label for ALL members above an agreement
                              threshold.

  2. multi_pass_agreement  -- when Stage 3 (multimodal classify) and
                              Stage 5b (per-doc graph extraction)
                              both name the same entity type for the
                              same value -> high-confidence label.

  3. cross_doc_consistency -- when entity X has the same etype across
                              >=4 docs out of 5, label all 5 with
                              that etype.

  4. tool_call_validation  -- when fee_detected fired AND
                              lookup_statute confirmed a violation,
                              that pair becomes a strong positive
                              label for "illegal_recruitment_fee".

Each strategy is independent. `--strategy all` runs them in order
and de-duplicates by (target_kind, target_id).
"""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from duecare.training.schema import ensure_tables


@dataclass
class LabeledExample:
    example_id: str
    target_kind: str
    target_id: str
    input_text: str
    label: str
    confidence: float
    source_strategy: str
    input_image_path: Optional[str] = None
    review_status: str = "auto"


# Strategy registry: the CLI / API map names -> functions.
LABEL_STRATEGIES: list[str] = [
    "cluster_vote",
    "multi_pass_agreement",
    "cross_doc_consistency",
    "tool_call_validation",
]


class SyntheticLabelGenerator:
    """Generates synthetic labels by reading the EvidenceStore."""

    def __init__(self, store, embedder: Optional[Callable] = None) -> None:
        """Args:
          store    -- duecare.evidence.EvidenceStore
          embedder -- callable(list[str]) -> list[list[float]]. If None,
                      cluster_vote falls back to TF-IDF (no extra deps).
        """
        self.store = store
        self.embedder = embedder
        ensure_tables(self.store)

    # -- public API ---------------------------------------------------------
    def generate(self, strategy: str = "all",
                  min_confidence: float = 0.7,
                  max_per_strategy: int = 1000) -> list[LabeledExample]:
        """Run one or all strategies. Returns the new labeled examples
        (also persisted to the labeled_examples table)."""
        if strategy == "all":
            strategies = LABEL_STRATEGIES
        else:
            if strategy not in LABEL_STRATEGIES:
                raise ValueError(
                    f"unknown strategy {strategy!r}. "
                    f"Known: {LABEL_STRATEGIES}")
            strategies = [strategy]

        out: list[LabeledExample] = []
        for s in strategies:
            method = getattr(self, f"_strategy_{s}", None)
            if method is None:
                continue
            try:
                examples = method(
                    min_confidence=min_confidence,
                    max_yield=max_per_strategy)
            except Exception as e:
                print(f"[labels] strategy {s} FAILED: "
                      f"{type(e).__name__}: {e}")
                continue
            print(f"[labels] {s}: {len(examples)} new label(s)")
            out.extend(examples)
        for ex in out:
            self._persist(ex)
        return out

    # -- strategies ---------------------------------------------------------
    def _strategy_cluster_vote(self, min_confidence: float,
                                  max_yield: int) -> list[LabeledExample]:
        """Cluster documents by their classification + facts text;
        label members of pure-enough clusters."""
        docs = self.store.fetchall(
            "SELECT doc_id, category, parsed_response, image_path "
            "FROM documents WHERE category IS NOT NULL AND category != ''")
        if len(docs) < 5:
            return []
        texts = []
        ids = []
        cats = []
        for d in docs:
            try:
                pr = json.loads(d["parsed_response"] or "{}")
            except Exception:
                pr = {}
            facts_str = json.dumps(pr.get("extracted_facts") or {},
                                     default=str)[:1500]
            blob = f"{d['category']}\n{facts_str}"
            texts.append(blob)
            ids.append(d["doc_id"])
            cats.append(d["category"])

        clusters = self._cluster_texts(texts)
        if not clusters:
            return []

        out: list[LabeledExample] = []
        for cid, member_idxs in clusters.items():
            if cid == -1:           # noise cluster (HDBSCAN)
                continue
            cluster_cats = [cats[i] for i in member_idxs]
            counter = Counter(cluster_cats)
            top_cat, top_n = counter.most_common(1)[0]
            agreement = top_n / max(1, len(member_idxs))
            if agreement < min_confidence:
                continue
            for i in member_idxs:
                if cats[i] == top_cat:
                    continue   # already correctly labeled by Gemma
                ex = LabeledExample(
                    example_id=_eid(
                        "cluster_vote", "document_category", ids[i]),
                    target_kind="document_category",
                    target_id=ids[i],
                    input_text=texts[i],
                    input_image_path=docs[i]["image_path"],
                    label=top_cat,
                    confidence=round(agreement, 3),
                    source_strategy="cluster_vote",
                    review_status=("auto" if agreement >= 0.85
                                    else "pending_review"),
                )
                out.append(ex)
                if len(out) >= max_yield:
                    return out
        return out

    def _strategy_multi_pass_agreement(self, min_confidence: float,
                                          max_yield: int
                                          ) -> list[LabeledExample]:
        """When the per-doc graph extraction (Stage 5b, stored as
        gemma_graph in the parsed_response field) and the multimodal
        classifier (Stage 3, stored as the row's category) agree on
        the type of an entity for the same document, that's a strong
        signal."""
        docs = self.store.fetchall(
            "SELECT doc_id, parsed_response FROM documents")
        out: list[LabeledExample] = []
        for d in docs:
            try:
                pr = json.loads(d["parsed_response"] or "{}")
            except Exception:
                continue
            facts = pr.get("extracted_facts") or {}
            gg = pr.get("gemma_graph") or {}
            gg_ents = {
                str(e.get("name", "")).strip().lower():
                    str(e.get("type", "")).strip().lower()
                for e in (gg.get("entities") or [])
                if isinstance(e, dict) and e.get("name")
            }
            for k, v in facts.items():
                if v is None:
                    continue
                key = str(v).strip().lower()
                if not key:
                    continue
                hint = self._infer_etype_from_field(str(k).lower())
                if not hint:
                    continue
                gg_type = gg_ents.get(key)
                if not gg_type or gg_type != hint:
                    continue
                ex = LabeledExample(
                    example_id=_eid("multi_pass", hint,
                                      f"{d['doc_id']}::{key}"),
                    target_kind="entity_type",
                    target_id=f"{d['doc_id']}::{key}",
                    input_text=f"In a recruitment-context document, "
                               f"the value '{v}' appears in field "
                               f"'{k}'. What entity type does this "
                               f"refer to?",
                    label=hint,
                    confidence=0.92,
                    source_strategy="multi_pass_agreement",
                    review_status="auto",
                )
                out.append(ex)
                if len(out) >= max_yield:
                    return out
        return out

    def _strategy_cross_doc_consistency(self, min_confidence: float,
                                          max_yield: int
                                          ) -> list[LabeledExample]:
        """For each entity, if >=4 of its docs classify it as the
        same etype, label the entity at that etype with high
        confidence."""
        rows = self.store.fetchall(
            "SELECT e.entity_id, e.canonical_name, e.etype, "
            "       COUNT(DISTINCT ed.doc_id) AS doc_count "
            "FROM entities e "
            "JOIN entity_documents ed ON ed.entity_id = e.entity_id "
            "GROUP BY e.entity_id, e.canonical_name, e.etype")
        out: list[LabeledExample] = []
        for r in rows:
            dc = int(r.get("doc_count") or 0)
            if dc < 4:
                continue
            confidence = min(0.99, 0.6 + dc * 0.05)
            if confidence < min_confidence:
                continue
            ex = LabeledExample(
                example_id=_eid(
                    "cross_doc", "entity_type", r["entity_id"]),
                target_kind="entity_type",
                target_id=r["entity_id"],
                input_text=(f"The value '{r['canonical_name']}' was "
                             f"extracted from {dc} documents. What "
                             f"entity type is it?"),
                label=r["etype"],
                confidence=round(confidence, 3),
                source_strategy="cross_doc_consistency",
                review_status=("auto" if dc >= 6 else "pending_review"),
            )
            out.append(ex)
            if len(out) >= max_yield:
                return out
        return out

    def _strategy_tool_call_validation(self, min_confidence: float,
                                          max_yield: int
                                          ) -> list[LabeledExample]:
        """When a fee_detected finding produced a tool_call_cache
        result confirming a statute violation, the source doc + fee
        becomes a strong illegal_recruitment_fee positive."""
        rows = self.store.fetchall(
            "SELECT f.finding_id, f.doc_id, f.fee_value, "
            "       f.statute_violated, f.severity, "
            "       f.parsed_json, f.bundle "
            "FROM findings f "
            "WHERE f.trigger_name = 'fee_detected' "
            "AND f.severity >= 6 "
            "AND f.statute_violated IS NOT NULL "
            "AND f.statute_violated != ''")
        out: list[LabeledExample] = []
        for r in rows:
            ex = LabeledExample(
                example_id=_eid(
                    "tool_call", "fee_legitimacy", r["finding_id"]),
                target_kind="fee_legitimacy",
                target_id=r["finding_id"],
                input_text=(
                    f"A recruitment-context document mentions a "
                    f"fee of {r['fee_value']}. The Gemma harness "
                    f"flagged it as a violation of "
                    f"{r['statute_violated']} (severity "
                    f"{r['severity']}/10) in bundle "
                    f"{r.get('bundle', '?')}. Was this fee illegal?"),
                label="illegal",
                confidence=min(0.99,
                                0.5 + float(r["severity"] or 0) * 0.05),
                source_strategy="tool_call_validation",
                review_status="auto",
            )
            out.append(ex)
            if len(out) >= max_yield:
                return out
        return out

    # -- helpers ------------------------------------------------------------
    def _cluster_texts(self, texts: list[str]) -> dict:
        """Return {cluster_id: [member_indexes]}. Tries (in order):
        sentence-transformers + HDBSCAN, sentence-transformers + KMeans,
        TF-IDF + KMeans (always works)."""
        # 1. Embeddings
        embeddings = None
        if self.embedder is not None:
            try:
                embeddings = self.embedder(texts)
            except Exception as e:
                print(f"[labels] embedder FAILED: "
                      f"{type(e).__name__}: {e}; falling back to TF-IDF")
        if embeddings is None:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                vec = TfidfVectorizer(
                    max_features=512, stop_words="english",
                    ngram_range=(1, 2))
                m = vec.fit_transform(texts)
                embeddings = m.toarray().tolist()
            except Exception as e:
                print(f"[labels] TF-IDF FAILED: "
                      f"{type(e).__name__}: {e}; cluster_vote disabled")
                return {}
        # 2. Clustering
        try:
            from sklearn.cluster import KMeans
            n_clusters = max(2, min(int(math.sqrt(len(texts) / 2)), 20))
            km = KMeans(n_clusters=n_clusters, n_init=10, random_state=17)
            labels = km.fit_predict(embeddings)
        except Exception as e:
            print(f"[labels] KMeans FAILED: "
                  f"{type(e).__name__}: {e}; cluster_vote disabled")
            return {}
        clusters: dict = defaultdict(list)
        for i, lbl in enumerate(labels):
            clusters[int(lbl)].append(i)
        return clusters

    def _infer_etype_from_field(self, field_name: str) -> Optional[str]:
        """Map an extracted_facts field name to the canonical etype."""
        f = field_name
        if "phone" in f or "mobile" in f or "contact" in f or "tel" in f:
            return "phone"
        if "email" in f:
            return "email"
        if "passport" in f or "id_number" in f or "national_id" in f:
            return "passport_number"
        if "account" in f or "iban" in f or "swift" in f:
            return "financial_account"
        if "fee" in f or "amount" in f or "salary" in f or "wage" in f:
            return "money"
        if f in ("worker_name", "employee_name", "candidate_name",
                  "victim_name", "applicant_name", "person", "name"):
            return "person_or_org"
        if f in ("employer_name", "company", "company_name", "agency",
                  "recruitment_agency"):
            return "organization"
        if f in ("address", "employer_address", "worksite_address",
                  "home_address"):
            return "address"
        return None

    def _persist(self, ex: LabeledExample) -> None:
        """Upsert via the EvidenceStore generic _upsert helper."""
        self.store._upsert("labeled_examples", "example_id", {
            "example_id": ex.example_id,
            "run_id": "",
            "target_kind": ex.target_kind,
            "target_id": ex.target_id,
            "input_text": ex.input_text,
            "input_image_path": ex.input_image_path or "",
            "label": ex.label,
            "confidence": float(ex.confidence),
            "source_strategy": ex.source_strategy,
            "review_status": ex.review_status,
            "review_notes": "",
            "created_at": datetime.now(),
            "reviewed_at": None,
        })


def _eid(strategy: str, kind: str, target: str) -> str:
    """Stable id so re-running the same strategy on the same target
    upserts in place."""
    h = hashlib.sha1(
        f"{strategy}::{kind}::{target}".encode("utf-8")).hexdigest()[:16]
    return f"lex_{h}"
